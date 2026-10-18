"""Bounded, opt-in acquisition; no source is enabled by default.

The registry is a reviewed code/configuration boundary, not user-supplied URLs.
This module downloads individual representations, never interprets source bodies.
Partial transfers are restarted; only complete hash-verified objects resume.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import http.client
import os
import re
import socket
import shutil
import ssl
import time
import threading
from urllib.parse import urlsplit
from email.utils import parsedate_to_datetime

from .core import (RefreshError, atomic_json, canonical, digest, fsync_directory,
                   safe_path, sha, strict_json, timestamp, writer_lock)

MIN_TTL = 30 * 86400
MAX_BODY = 64 * 1024 * 1024  # Default only; larger sources require runner resource policy.
MAX_REVIEWED_BODY = 1024 ** 4
MAX_METADATA = 1024 * 1024
RETAINED_HEADERS = frozenset(('etag', 'last-modified', 'cache-control', 'expires', 'age', 'vary', 'content-encoding'))
POLICIES = frozenset(('reuse', 'refresh', 'revalidate', 'force-download'))


@dataclass(frozen=True)
class SourceSpec:
    source_key: str
    url: str
    policy_fingerprint: str
    rights_reference: str
    enabled: bool = False
    rights_approved: bool = False
    held: bool = False
    ttl_seconds: int = MIN_TTL
    max_bytes: int = MAX_BODY
    acquisition_version: str = 'https-file-v1'
    release: str = 'mutable'
    cache_scope: str = 'public'

    def validate(self):
        if not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,127}', self.source_key):
            raise RefreshError('invalid-source-key')
        if (type(self.enabled) is not bool or type(self.rights_approved) is not bool
                or type(self.held) is not bool):
            raise RefreshError('invalid-source-gate')
        if self.cache_scope != 'public':
            raise RefreshError('restricted-cache-scope-not-supported')
        if not self.enabled or not self.rights_approved or self.held:
            raise RefreshError('source-acquisition-gate-closed')
        parts = urlsplit(self.url)
        # Initial adapter deliberately excludes query tokens, auth, redirects,
        # nonstandard ports and custom representation headers.
        if (parts.scheme != 'https' or not parts.hostname or parts.username
                or parts.password or parts.query or parts.fragment
                or parts.port not in (None, 443) or '\\' in self.url
                or any(ord(c) < 33 or ord(c) > 126 for c in self.url)):
            raise RefreshError('unsupported-source-locator')
        if (not re.fullmatch(r'[0-9a-f]{64}', self.policy_fingerprint)
                or not self.rights_reference or not self.acquisition_version
                or not self.release):
            raise RefreshError('missing-reviewed-source-policy')
        if (type(self.ttl_seconds) is not int or self.ttl_seconds < MIN_TTL
                or type(self.max_bytes) is not int or not 1 <= self.max_bytes <= MAX_REVIEWED_BODY):
            raise RefreshError('invalid-acquisition-bounds')

    def identity(self):
        return {'sourceKey': self.source_key, 'url': self.url,
                'policyFingerprint': self.policy_fingerprint,
                'rightsReference': self.rights_reference, 'cacheScope': self.cache_scope,
                'acquisitionVersion': self.acquisition_version, 'release': self.release,
                'representation': {'Accept-Encoding': 'identity'},
                'maxBytes': self.max_bytes, 'ttlSeconds': self.ttl_seconds}


@dataclass(frozen=True)
class ResourceBudget:
    """Runner-owned verified storage/resource contract, never proof of host identity."""
    storage_root: Path
    max_transfer_bytes: int
    minimum_free_bytes: int = MAX_BODY
    max_seconds: int = 600


@dataclass(frozen=True)
class AcquisitionResult:
    path: Path
    sha256: str
    bytes: int
    status: str
    provenance: dict


class HTTPSFileTransport:
    """One HTTPS GET; no redirects, cookies, proxy discovery or credentials."""
    def __call__(self, spec, headers, *, deadline=None):
        remaining = deadline - time.monotonic() if deadline is not None else 180
        if remaining <= 0:
            raise RefreshError('acquisition-duration-limit-exceeded')
        parts = urlsplit(spec.url)
        connection = http.client.HTTPSConnection(parts.hostname, 443, timeout=min(30, remaining),
                                                 context=ssl.create_default_context())
        expired = threading.Event()
        active_socket = [None]
        def abort():
            expired.set()
            sock = connection.sock or active_socket[0]
            if sock is not None:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            connection.close()
        watchdog = threading.Timer(remaining, abort)
        watchdog.daemon = True
        watchdog.start()
        try:
            connection.request('GET', parts.path or '/', headers=headers)
            active_socket[0] = connection.sock
            response = connection.getresponse()
            if expired.is_set():
                raise TimeoutError('acquisition-deadline')
        except BaseException:
            watchdog.cancel()
            connection.close()
            raise
        return _Response(connection, response, watchdog, expired)


class _Response:
    def __init__(self, connection, response, watchdog, expired):
        self.connection, self.response = connection, response
        self.watchdog, self.expired = watchdog, expired
        self.status = response.status
        self.headers = response.getheaders()

    def read(self, size):
        if self.expired.is_set():
            raise TimeoutError('acquisition-deadline')
        block = self.response.read1(size)
        if self.expired.is_set():
            raise TimeoutError('acquisition-deadline')
        return block

    def close(self):
        self.watchdog.cancel()
        self.response.close()
        self.connection.close()


def _headers(raw):
    result = {}
    if not isinstance(raw, (dict, list)):
        raise RefreshError('invalid-response-headers')
    for key, value in (raw.items() if isinstance(raw, dict) else raw):
        if not isinstance(key, str):
            raise RefreshError('invalid-response-headers')
        key = key.lower()
        if key in result or not isinstance(value, str) or len(value) > 8192 or '\r' in value or '\n' in value:
            raise RefreshError('invalid-response-headers')
        result[key] = value
    return result


def _retention(headers):
    directives = {item.strip().split('=', 1)[0].lower()
                  for item in headers.get('cache-control', '').split(',')}
    # A publisher restriction takes precedence over a minimum reuse preference.
    if directives & {'no-store', 'private'}:
        raise RefreshError('response-retention-not-approved')
    if headers.get('vary', '').strip() not in ('', 'Accept-Encoding', 'accept-encoding'):
        raise RefreshError('unsupported-response-vary')
    if headers.get('content-encoding', 'identity').lower() != 'identity':
        raise RefreshError('unsupported-response-encoding')


def _http_fresh(headers, acquired, now):
    if any(k in headers for k in ('expires', 'age')):
        return False
    directives = [item.strip().lower() for item in headers.get('cache-control', '').split(',')]
    if 'no-cache' in directives:
        return False
    for item in directives:
        if item.startswith('max-age='):
            try:
                return (now - acquired).total_seconds() < int(item.split('=', 1)[1].strip('"'))
            except ValueError:
                return False
    # Unsupported Expires/Age semantics must not silently create a fresh cache.
    return not any(k in headers for k in ('expires', 'age'))


class CachedAcquirer:
    def __init__(self, cache_root, sources, *, transport=None, retries=2, sleep=time.sleep, resource_budget=None):
        self.root = safe_path(cache_root)
        self.sources = dict(sources)
        self.transport = transport
        self.budget = resource_budget or ResourceBudget(self.root, MAX_BODY, max_seconds=180)
        if (safe_path(self.budget.storage_root) != self.root
                or type(self.budget.max_transfer_bytes) is not int
                or not 1 <= self.budget.max_transfer_bytes <= MAX_REVIEWED_BODY
                or type(self.budget.minimum_free_bytes) is not int or self.budget.minimum_free_bytes < 0
                or type(self.budget.max_seconds) is not int or not 1 <= self.budget.max_seconds <= 86400):
            raise RefreshError('invalid-runner-resource-budget')
        if type(retries) is not int or not 0 <= retries <= 3:
            raise RefreshError('invalid-retry-bound')
        self.retries, self.sleep = retries, sleep

    def acquire(self, source_key, *, fetch_policy='reuse', now=None):
        if fetch_policy not in POLICIES:
            raise RefreshError('unsupported-fetch-policy')
        spec = self.sources.get(source_key)
        if spec is None or spec.source_key != source_key:
            raise RefreshError('source-not-allowlisted')
        spec.validate()  # Includes holds and rights on reuse, not only download.
        if spec.max_bytes > self.budget.max_transfer_bytes:
            raise RefreshError('source-exceeds-runner-byte-budget')
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None or now.utcoffset().total_seconds() != 0:
            raise RefreshError('policy-clock-must-be-utc')
        identity = spec.identity()
        key = sha(canonical(identity))
        self.root.mkdir(parents=True, exist_ok=True)
        # One global lock bounds both concurrent HTTP and duplicate acquisitions.
        with writer_lock(self.root / 'acquisition.lock'):
            directory = safe_path(self.root / 'requests' / key)
            directory.mkdir(parents=True, exist_ok=True)
            record = safe_path(directory / 'current.json')
            pending = safe_path(directory / 'recovery.json')
            if pending.exists():
                recovered = self._load(pending, identity, spec, now, recovery=True)
                self._commit(record, recovered)
            previous = self._load(record, identity, spec, now)
            if previous:
                acquired = timestamp(previous['checkedAt'])
                fresh = ((now - acquired).total_seconds() < spec.ttl_seconds
                         and _http_fresh(previous['headers'], acquired, now))
                if fresh and fetch_policy in ('reuse', 'refresh'):
                    return self._result(previous, 'reused-fresh')
            if (previous and fetch_policy == 'refresh'
                    and (now - timestamp(previous['checkedAt'])).total_seconds() < spec.ttl_seconds):
                raise RefreshError('automatic-refresh-deferred-minimum-reuse-window')
            if fetch_policy == 'reuse':
                raise RefreshError('cache-stale' if previous else 'cache-missing')
            if shutil.disk_usage(self.root).free < spec.max_bytes + self.budget.minimum_free_bytes:
                raise RefreshError('insufficient-acquisition-disk-budget')
            return self._fetch(spec, record, identity, previous, fetch_policy, now)

    def _load(self, record, identity, spec, now, *, recovery=False):
        if not record.exists():
            return None
        if not record.is_file() or record.stat().st_size > MAX_METADATA:
            raise RefreshError('invalid-acquisition-record')
        try:
            value = strict_json(record.read_bytes())
        except (ValueError, UnicodeError) as error:
            raise RefreshError('invalid-acquisition-record') from error
        if (not isinstance(value, dict) or value.get('schemaVersion') != 'offmenu-acquisition/1'
                or value.get('request') != identity):
            raise RefreshError('acquisition-record-mismatch')
        if (not isinstance(value.get('sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', value['sha256'])
                or type(value.get('bytes')) is not int or not 1 <= value['bytes'] <= spec.max_bytes):
            raise RefreshError('invalid-acquisition-record')
        expected = {'schemaVersion', 'request', 'sha256', 'bytes', 'headers',
                    'originalAcquiredAt', 'checkedAt', 'result'}
        if set(value) != expected or value['result'] not in ('downloaded-200', 'identical-body-200', 'not-modified-304'):
            raise RefreshError('invalid-acquisition-record')
        if not timestamp(value['originalAcquiredAt']) <= timestamp(value['checkedAt']) <= now:
            raise RefreshError('invalid-acquisition-time')
        if not recovery:
            evidence = safe_path(record.parent / 'evidence' / (sha(canonical(value)) + '.json'))
            if (not evidence.is_file() or evidence.stat().st_size > MAX_METADATA
                    or evidence.read_bytes() != canonical(value)):
                raise RefreshError('acquisition-evidence-missing-or-corrupt')
        headers = _headers(value['headers'])
        if not set(headers) <= RETAINED_HEADERS:
            raise RefreshError('invalid-acquisition-record')
        _retention(headers)
        if not self._body(value['sha256']).is_file():
            raise RefreshError('cached-body-missing')
        if digest(self._body(value['sha256']), max_bytes=spec.max_bytes) != {'sha256': value['sha256'], 'bytes': value['bytes']}:
            raise RefreshError('cached-body-corrupt')
        return value

    def _body(self, checksum):
        return safe_path(self.root / 'objects' / checksum)

    def _result(self, value, status):
        return AcquisitionResult(self._body(value['sha256']), value['sha256'], value['bytes'], status, value)

    def _fetch(self, spec, record, identity, previous, policy, now):
        request_headers = {'Accept-Encoding': 'identity'}
        if previous and policy != 'force-download':
            for old, new in (('etag', 'If-None-Match'), ('last-modified', 'If-Modified-Since')):
                if previous['headers'].get(old):
                    request_headers[new] = previous['headers'][old]
        deadline = time.monotonic() + self.budget.max_seconds
        transferred = 0
        for attempt in range(self.retries + 1):
            response = None
            partial = safe_path(record.parent / 'body.partial')
            try:
                if transferred >= self.budget.max_transfer_bytes:
                    raise RefreshError('cumulative-transfer-budget-exceeded')
                if time.monotonic() >= deadline:
                    raise RefreshError('acquisition-duration-limit-exceeded')
                response = (self.transport(spec, request_headers) if self.transport is not None
                            else HTTPSFileTransport()(spec, request_headers, deadline=deadline))
                if time.monotonic() >= deadline:
                    raise RefreshError('acquisition-duration-limit-exceeded')
                headers = _headers(response.headers)
                if response.status in (429, 500, 502, 503, 504):
                    if 'retry-after' in headers:
                        raw = headers['retry-after']
                        try:
                            delay = int(raw) if raw.isdigit() else max(0, (parsedate_to_datetime(raw) - now).total_seconds())
                        except (ValueError, TypeError, OverflowError):
                            raise RefreshError('invalid-retry-after') from None
                        if delay > min(4, deadline - time.monotonic()):
                            raise RefreshError('publisher-retry-deferred')
                        raise _Retryable(delay)
                    raise _Retryable()
                if response.status == 304:
                    if not previous or len(request_headers) == 1:
                        raise RefreshError('unexpected-not-modified')
                    if ('etag' in headers and previous['headers'].get('etag')
                            and headers['etag'] != previous['headers']['etag']):
                        raise RefreshError('validator-mismatch')
                    merged = {**previous['headers'], **{k: v for k, v in headers.items() if k in RETAINED_HEADERS}}
                    _retention(merged)
                    value = {**previous, 'headers': merged, 'checkedAt': now.isoformat(),
                             'result': 'not-modified-304'}
                elif response.status == 200:
                    _retention(headers)
                    length = headers.get('content-length')
                    if length is not None and (not length.isdigit() or not 1 <= int(length) <= spec.max_bytes):
                        raise RefreshError('response-size-limit-exceeded')
                    if partial.exists():
                        if not partial.is_file():
                            raise RefreshError('invalid-acquisition-partial')
                        partial.unlink()
                    hasher, count = hashlib.sha256(), 0
                    with partial.open('xb') as output:
                        while True:
                            if time.monotonic() >= deadline:
                                raise RefreshError('response-duration-limit-exceeded')
                            block = response.read(min(1024 * 1024, spec.max_bytes - count + 1,
                                                      self.budget.max_transfer_bytes - transferred + 1))
                            if time.monotonic() >= deadline:
                                raise RefreshError('response-duration-limit-exceeded')
                            if not block:
                                break
                            count += len(block)
                            transferred += len(block)
                            if transferred > self.budget.max_transfer_bytes:
                                raise RefreshError('cumulative-transfer-budget-exceeded')
                            if shutil.disk_usage(self.root).free < self.budget.minimum_free_bytes + len(block):
                                raise RefreshError('insufficient-acquisition-disk-budget')
                            if count > spec.max_bytes:
                                raise RefreshError('response-size-limit-exceeded')
                            hasher.update(block)
                            output.write(block)
                        output.flush()
                        os.fsync(output.fileno())
                    if count == 0 or (length is not None and count != int(length)):
                        raise _Retryable()
                    checksum = hasher.hexdigest()
                    target = self._body(checksum)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if target.exists():
                        if digest(target, max_bytes=spec.max_bytes) != {'sha256': checksum, 'bytes': count}:
                            raise RefreshError('cached-body-corrupt')
                    else:
                        os.replace(partial, target)
                        fsync_directory(target.parent)
                    identical = previous is not None and checksum == previous['sha256']
                    value = {'schemaVersion': 'offmenu-acquisition/1', 'request': identity,
                             'sha256': checksum, 'bytes': count, 'headers': {
                                 k: v for k, v in headers.items() if k in RETAINED_HEADERS},
                             'originalAcquiredAt': previous['originalAcquiredAt'] if identical else now.isoformat(),
                             'checkedAt': now.isoformat(),
                             'result': 'identical-body-200' if identical else 'downloaded-200'}
                else:
                    # Includes redirects, authentication, challenges and source holds.
                    raise RefreshError('source-response-not-permitted')
                self._commit(record, value)
                return self._result(value, value['result'])
            except (_Retryable, TimeoutError, socket.timeout, ConnectionError, http.client.IncompleteRead) as error:
                if attempt == self.retries:
                    raise RefreshError('acquisition-retries-exhausted') from None
                delay = max(min(2 ** attempt, 4), error.args[0] if isinstance(error, _Retryable) and error.args else 0)
                if time.monotonic() + delay >= deadline:
                    raise RefreshError('acquisition-duration-limit-exceeded') from None
                self.sleep(delay)
            finally:
                if response is not None:
                    response.close()
                if partial.exists():
                    partial.unlink()
        raise RefreshError('acquisition-retries-exhausted')

    def _commit(self, record, value):
        # Immutable acquisition evidence is committed before the mutable pointer.
        # An interrupted pointer update resumes from the last fully verified object.
        pending = safe_path(record.parent / 'recovery.json')
        atomic_json(pending, value)
        evidence = safe_path(record.parent / 'evidence' / (sha(canonical(value)) + '.json'))
        if not evidence.exists():
            atomic_json(evidence, value)
        elif evidence.read_bytes() != canonical(value):
            raise RefreshError('acquisition-evidence-corrupt')
        atomic_json(record, value)
        pending.unlink()
        fsync_directory(record.parent)


class _Retryable(Exception):
    pass
