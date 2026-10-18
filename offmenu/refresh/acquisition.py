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
from urllib.parse import urlsplit, parse_qsl
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
    query_keys: tuple = ()
    request_method: str = 'GET'
    request_body: str = ''
    public_read_only_post: bool = False

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
        # Only reviewed exact public query keys and canonical read-only JSON POST.
        # Credentials, redirect discovery and arbitrary request headers stay closed.
        if (parts.scheme != 'https' or not parts.hostname or parts.username
                or parts.password or parts.fragment
                or parts.port not in (None, 443) or '\\' in self.url
                or any(ord(c) < 33 or ord(c) > 126 for c in self.url)):
            raise RefreshError('unsupported-source-locator')
        if (not isinstance(self.query_keys, (tuple, list))
                or any(not isinstance(k, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', k)
                       or re.search(r'token|key|secret|pass|auth|credential|signature', k, re.I)
                       for k in self.query_keys)
                or len(set(self.query_keys)) != len(self.query_keys)):
            raise RefreshError('invalid-reviewed-query-contract')
        query = parse_qsl(parts.query, keep_blank_values=True, strict_parsing=True)
        if (len({k for k, v in query}) != len(query)
                or set(k for k, v in query) != set(self.query_keys)
                or any(any(ord(c) < 32 or ord(c) == 127 for c in k + v) for k, v in query)):
            raise RefreshError('unsupported-source-locator-query')
        if type(self.public_read_only_post) is not bool or not isinstance(self.request_body, str):
            raise RefreshError('invalid-reviewed-request-contract')
        if self.request_method == 'GET':
            if self.request_body or self.public_read_only_post:
                raise RefreshError('invalid-reviewed-request-contract')
        elif self.request_method == 'POST':
            if not self.public_read_only_post or not 1 <= len(self.request_body.encode('utf-8')) <= 65536:
                raise RefreshError('read-only-public-post-not-approved')
            try:
                body = strict_json(self.request_body.encode('utf-8'))
                if not isinstance(body, dict) or canonical(body) != self.request_body.encode('utf-8'):
                    raise ValueError()
                def public_fields(value):
                    if isinstance(value, dict):
                        for key, item in value.items():
                            if re.search(r'token|api.?key|secret|password|authorization|credential|signature', key, re.I):
                                raise ValueError()
                            public_fields(item)
                    elif isinstance(value, list):
                        for item in value:
                            public_fields(item)
                public_fields(body)
            except (ValueError, UnicodeError, RecursionError):
                raise RefreshError('invalid-public-json-post-body') from None
        else:
            raise RefreshError('unsupported-source-method')
        if (not re.fullmatch(r'[0-9a-f]{64}', self.policy_fingerprint)
                or not self.rights_reference or not self.acquisition_version
                or not self.release):
            raise RefreshError('missing-reviewed-source-policy')
        if (type(self.ttl_seconds) is not int or self.ttl_seconds < MIN_TTL
                or type(self.max_bytes) is not int or not 1 <= self.max_bytes <= MAX_REVIEWED_BODY):
            raise RefreshError('invalid-acquisition-bounds')

    def identity(self):
        identity = {'sourceKey': self.source_key, 'url': self.url,
                'policyFingerprint': self.policy_fingerprint,
                'rightsReference': self.rights_reference, 'cacheScope': self.cache_scope,
                'acquisitionVersion': self.acquisition_version, 'release': self.release,
                'representation': {'Accept-Encoding': 'identity'},
                'maxBytes': self.max_bytes, 'ttlSeconds': self.ttl_seconds}
        if self.query_keys:
            identity['queryKeys'] = sorted(self.query_keys)
        if self.request_method != 'GET':
            identity['request'] = {'method': self.request_method, 'contentType': 'application/json',
                                   'body': self.request_body, 'publicReadOnly': self.public_read_only_post}
        return identity


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
            target = (parts.path or '/') + ('?' + parts.query if parts.query else '')
            if spec.request_method == 'POST':
                connection.request('POST', target, body=spec.request_body.encode('utf-8'),
                                   headers={**headers, 'Content-Type': 'application/json'})
            else:
                connection.request('GET', target, headers=headers)
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
        if 'retainedOrigin' in value:
            expected.add('retainedOrigin')
            origin = value['retainedOrigin']
            if (not isinstance(origin, dict) or set(origin) != {'path', 'evidence', 'verifiedAt'}
                    or not isinstance(origin['path'], str)
                    or not isinstance(origin['evidence'], dict)
                    or set(origin['evidence']) != {'path', 'sha256'}
                    or not isinstance(origin['evidence']['sha256'], str)
                    or not re.fullmatch(r'[0-9a-f]{64}', origin['evidence']['sha256'])
                    or not timestamp(value['originalAcquiredAt']) <= timestamp(origin['verifiedAt']) <= now):
                raise RefreshError('invalid-retained-origin')
        if (set(value) != expected or value['result'] not in
                ('downloaded-200', 'identical-body-200', 'not-modified-304', 'retained-import')
                or (value['result'] == 'retained-import' and 'retainedOrigin' not in value)):
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

    def import_retained(self, source_key, retained, *, now=None):
        """Copy an exact reviewed original, preserving acquisition time. No network.

        `retained` is trusted operation configuration, not discovered metadata.
        Its evidence pin binds custody/source-use; it grants no permission itself.
        Completed objects recover normally; interrupted copies restart from zero.
        """
        spec = self.sources.get(source_key)
        if spec is None or spec.source_key != source_key:
            raise RefreshError('source-not-allowlisted')
        spec.validate()
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None or now.utcoffset().total_seconds() != 0:
            raise RefreshError('policy-clock-must-be-utc')
        if (not isinstance(retained, dict) or set(retained) !=
                {'path', 'sha256', 'bytes', 'originalAcquiredAt', 'headers', 'evidence'}
                or type(retained['bytes']) is not int
                or not 1 <= retained['bytes'] <= spec.max_bytes
                or not isinstance(retained['sha256'], str)
                or not re.fullmatch(r'[0-9a-f]{64}', retained['sha256'])):
            raise RefreshError('invalid-retained-contract')
        if spec.max_bytes > self.budget.max_transfer_bytes:
            raise RefreshError('source-exceeds-runner-byte-budget')
        acquired = timestamp(retained['originalAcquiredAt'])
        if acquired > now:
            raise RefreshError('invalid-acquisition-time')
        pin = retained['evidence']
        if (not isinstance(pin, dict) or set(pin) != {'path', 'sha256'}
                or digest(pin['path'], max_bytes=MAX_METADATA)['sha256'] != pin['sha256']):
            raise RefreshError('retained-evidence-mismatch')
        headers = _headers(retained['headers'])
        if not set(headers) <= RETAINED_HEADERS:
            raise RefreshError('invalid-retained-headers')
        _retention(headers)
        original = safe_path(retained['path'])
        expected = {k: retained[k] for k in ('sha256', 'bytes')}
        identity = spec.identity()
        self.root.mkdir(parents=True, exist_ok=True)
        with writer_lock(self.root / 'acquisition.lock'):
            directory = safe_path(self.root / 'requests' / sha(canonical(identity)))
            directory.mkdir(parents=True, exist_ok=True)
            record = safe_path(directory / 'current.json')
            pending = safe_path(directory / 'recovery.json')
            if pending.exists():
                self._commit(record, self._load(pending, identity, spec, now, recovery=True))
            previous = self._load(record, identity, spec, now)
            if previous:
                # Never overwrite a previously acquired different representation.
                if {k: previous[k] for k in expected} != expected:
                    raise RefreshError('retained-cache-conflict')
                return self._result(previous, 'retained-already-cached')
            if digest(original, max_bytes=spec.max_bytes) != expected:
                raise RefreshError('retained-original-mismatch')
            target = self._body(retained['sha256'])
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = safe_path(directory / 'body.partial')
            deadline = time.monotonic() + self.budget.max_seconds
            try:
                if target.exists():
                    if digest(target, max_bytes=spec.max_bytes) != expected:
                        raise RefreshError('cached-body-corrupt')
                else:
                    if shutil.disk_usage(self.root).free < retained['bytes'] + self.budget.minimum_free_bytes:
                        raise RefreshError('insufficient-acquisition-disk-budget')
                    if partial.exists():
                        partial.unlink()
                    count, hasher = 0, hashlib.sha256()
                    with original.open('rb') as source, partial.open('xb') as output:
                        while True:
                            if time.monotonic() >= deadline:
                                raise RefreshError('acquisition-duration-limit-exceeded')
                            block = source.read(min(1024 * 1024, retained['bytes'] - count + 1))
                            if not block:
                                break
                            count += len(block)
                            if count > retained['bytes']:
                                raise RefreshError('retained-original-mismatch')
                            if shutil.disk_usage(self.root).free < len(block) + self.budget.minimum_free_bytes:
                                raise RefreshError('insufficient-acquisition-disk-budget')
                            hasher.update(block)
                            output.write(block)
                        output.flush()
                        os.fsync(output.fileno())
                    if {'sha256': hasher.hexdigest(), 'bytes': count} != expected:
                        raise RefreshError('retained-original-mismatch')
                    # Hard-link promotion is no-overwrite even if another writer appears.
                    os.link(partial, target)
                    fsync_directory(target.parent)
                value = {'schemaVersion': 'offmenu-acquisition/1', 'request': identity,
                         **expected, 'headers': headers,
                         'originalAcquiredAt': retained['originalAcquiredAt'],
                         'checkedAt': retained['originalAcquiredAt'], 'result': 'retained-import',
                         'retainedOrigin': {'path': str(original), 'evidence': pin,
                                            'verifiedAt': now.isoformat()}}
                self._commit(record, value)
                return self._result(value, 'retained-import')
            finally:
                if partial.exists():
                    partial.unlink()

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
                        os.link(partial, target)  # Never replace an existing object.
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


def collect_registry(registry_path, registry_sha256, output, *, transport=None, now=None):
    """Run a pinned reviewed acquisition selection, not the discovery registry.

    Bindings are evidence-backed applicability edges, never country completion.
    One source/release representation runs once regardless of its consumers.
    Each source checkpoints independently; a failed source cannot hide others.
    The caller must qualify actual host, source rights and competing claims.
    """
    raw_path = safe_path(registry_path)
    if digest(raw_path, max_bytes=8 * MAX_METADATA)['sha256'] != registry_sha256:
        raise RefreshError('collection-registry-pin-mismatch')
    registry = strict_json(raw_path.read_bytes())
    version = registry.get('schemaVersion') if isinstance(registry, dict) else None
    expected = {'schemaVersion', 'resources', 'sources', 'bindings', 'evidence'}
    if version == 'offmenu-acquisition-selection/2':
        expected.add('assetCatalog')
        describe_collection_registry(registry)
    if (not isinstance(registry, dict) or set(registry) != expected
            or version not in ('offmenu-acquisition-selection/1', 'offmenu-acquisition-selection/2')
            or not isinstance(registry['sources'], list)
            or not isinstance(registry['bindings'], list)):
        raise RefreshError('invalid-collection-registry')

    def verify_pin(pin):
        if (not isinstance(pin, dict) or set(pin) != {'path', 'sha256'}
                or digest(pin['path'], max_bytes=8 * MAX_METADATA)['sha256'] != pin['sha256']):
            raise RefreshError('collection-evidence-pin-mismatch')

    if not isinstance(registry['evidence'], list) or not registry['evidence']:
        raise RefreshError('collection-evidence-required')
    for pin in registry['evidence']:
        verify_pin(pin)
    resources = registry['resources']
    if (not isinstance(resources, dict) or set(resources) !=
            {'storageRoot', 'maxTransferBytes', 'minimumFreeBytes', 'maxSeconds'}):
        raise RefreshError('invalid-runner-resource-budget')
    root = safe_path(resources['storageRoot'])
    budget = ResourceBudget(root, resources['maxTransferBytes'],
                            resources['minimumFreeBytes'], resources['maxSeconds'])
    # Validate the aggregate budget before any source reads or requests.
    CachedAcquirer(root, {}, resource_budget=budget)
    output = safe_path(output)
    output.mkdir(parents=True, exist_ok=True)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset().total_seconds() != 0:
        raise RefreshError('policy-clock-must-be-utc')
    keys, representations = set(), set()
    for entry in registry['sources']:
        if not isinstance(entry, dict) or not isinstance(entry.get('spec'), dict):
            raise RefreshError('invalid-collection-source')
        spec = SourceSpec(**entry['spec'])
        representation = (spec.url, spec.release, spec.acquisition_version, spec.cache_scope,
                          spec.request_method, spec.request_body)
        if spec.source_key in keys or representation in representations:
            raise RefreshError('duplicate-source-release-use-bindings')
        keys.add(spec.source_key)
        representations.add(representation)
    bindings, edges = {}, set()
    for binding in registry['bindings']:
        if (not isinstance(binding, dict) or set(binding) != {'sourceKey', 'country', 'type', 'evidence'}
                or binding['sourceKey'] not in keys
                or not isinstance(binding['country'], str)
                or not re.fullmatch(r'[A-Z]{2}', binding['country'])
                or not isinstance(binding['type'], str) or not binding['type']):
            raise RefreshError('invalid-source-country-type-binding')
        verify_pin(binding['evidence'])
        edge = (binding['sourceKey'], binding['country'], binding['type'])
        if edge in edges:
            raise RefreshError('duplicate-source-country-type-binding')
        edges.add(edge)
        bindings.setdefault(binding['sourceKey'], []).append(binding)
    if set(bindings) != keys:
        raise RefreshError('unmapped-collection-source')
    meter = {'requests': 0, 'bodyBytesRead': 0}
    deadline = time.monotonic() + budget.max_seconds

    class MeteredResponse:
        def __init__(self, response):
            self.response = response
            self.status, self.headers = response.status, response.headers
        def read(self, size):
            if time.monotonic() >= deadline:
                raise RefreshError('batch-duration-limit-exceeded')
            remaining = budget.max_transfer_bytes - meter['bodyBytesRead']
            if remaining <= 0:
                # Never read one byte beyond the selected aggregate allowance.
                # Without an EOF already observed, completeness stays unverified.
                raise RefreshError('batch-transfer-budget-exceeded')
            block = self.response.read(min(size, remaining))
            meter['bodyBytesRead'] += len(block)
            if time.monotonic() >= deadline:
                raise RefreshError('batch-duration-limit-exceeded')
            if meter['bodyBytesRead'] > budget.max_transfer_bytes:
                raise RefreshError('batch-transfer-budget-exceeded')
            return block
        def close(self):
            self.response.close()

    def metered(spec, headers):
        if time.monotonic() >= deadline:
            raise RefreshError('batch-duration-limit-exceeded')
        if meter['bodyBytesRead'] >= budget.max_transfer_bytes:
            raise RefreshError('batch-transfer-budget-exceeded')
        meter['requests'] += 1
        response = (transport(spec, headers) if transport is not None else
                    HTTPSFileTransport()(spec, headers, deadline=deadline))
        return MeteredResponse(response)

    report = {'schemaVersion': 'offmenu-raw-collection-report/1',
              'registry': {'path': str(raw_path), 'sha256': registry_sha256},
              'observedAt': now.isoformat(), 'resources': resources, 'sources': [],
              'network': meter, 'scope': 'selected raw originals only',
              'parsed': 0, 'normalized': 0, 'goldAdmitted': 0,
              'countryComplete': False}
    if version == 'offmenu-acquisition-selection/2':
        report['assetCatalogSummary'] = {k: v for k, v in describe_collection_registry(registry).items()
                                         if k != 'unresolved'}

    def checkpoint():
        evidence = output / 'evidence' / (sha(canonical(report)) + '.json')
        if evidence.exists():
            if evidence.read_bytes() != canonical(report):
                raise RefreshError('collection-report-evidence-corrupt')
        else:
            atomic_json(evidence, report)
        atomic_json(output / 'collection-report.json', report)

    # One owned batch at a time in this output; acquirer also locks shared cache.
    with writer_lock(output / 'collection.lock'):
        for entry in sorted(registry['sources'], key=lambda item: item['spec']['source_key']):
            spec = SourceSpec(**entry['spec'])
            row = {'sourceKey': spec.source_key, 'release': spec.release,
                   'bindings': sorted(bindings[spec.source_key], key=lambda x: (x['country'], x['type'])),
                   'outcome': 'failed', 'networkRequests': 0, 'networkBytesRead': 0}
            before = dict(meter)
            try:
                if set(entry) != {'spec', 'operation', 'claim', 'holds', 'retained'}:
                    raise RefreshError('invalid-collection-source-contract')
                claim = entry['claim']
                if (not isinstance(claim, dict) or set(claim) != {'owner', 'state', 'evidence'}
                        or type(claim['owner']) is not int or claim['owner'] != 0
                        or claim['state'] != 'selected'):
                    raise RefreshError('collection-claim-not-selected')
                verify_pin(claim['evidence'])
                if not isinstance(entry['holds'], list) or entry['holds']:
                    raise RefreshError('collection-source-held')
                spec.validate()
                if time.monotonic() >= deadline:
                    raise RefreshError('batch-duration-limit-exceeded')
                acquirer = CachedAcquirer(root, {spec.source_key: spec}, transport=metered,
                                          resource_budget=budget)
                if entry['operation'] == 'retained-copy':
                    imported = acquirer.import_retained(spec.source_key, entry['retained'], now=now)
                    row['retainedImportStatus'] = imported.status
                    result = acquirer.acquire(spec.source_key, fetch_policy='reuse', now=now)
                elif entry['operation'] == 'https-refresh' and entry['retained'] is None:
                    result = acquirer.acquire(spec.source_key, fetch_policy='refresh', now=now)
                else:
                    raise RefreshError('unsupported-collection-operation')
                row.update(outcome='verified-local-original', status=result.status,
                           path=str(result.path), sha256=result.sha256, bytes=result.bytes,
                           provenance=result.provenance)
            except (RefreshError, OSError, ValueError, TypeError, KeyError) as error:
                # Never echo an arbitrary provider error/locator/header into a report.
                row['error'] = str(error) if isinstance(error, RefreshError) else type(error).__name__
            row['networkRequests'] = meter['requests'] - before['requests']
            row['networkBytesRead'] = meter['bodyBytesRead'] - before['bodyBytesRead']
            report['sources'].append(row)
            checkpoint()
        report['verifiedSources'] = sum(r['outcome'] == 'verified-local-original' for r in report['sources'])
        report['failedSources'] = len(report['sources']) - report['verifiedSources']
        checkpoint()
    return report


def describe_collection_registry(registry):
    """Metadata-only inventory qualification; never opens a dataset original.

    Catalog descriptors retain unknown provenance and desired citations. Only
    reviewed `sources` entries are executable; catalog presence never enables one.
    Country requirements are owned evidence from57, not inferred type coverage.
    """
    if (not isinstance(registry, dict)
            or registry.get('schemaVersion') != 'offmenu-acquisition-selection/2'):
        raise RefreshError('collection-catalog-v2-required')
    catalog = registry.get('assetCatalog')
    if (not isinstance(catalog, dict) or set(catalog) !=
            {'version', 'assets', 'requirements', 'evidence', 'qualification'}
            or not isinstance(catalog['version'], str) or not catalog['version']
            or not isinstance(catalog['evidence'], list) or not catalog['evidence']
            or not isinstance(catalog['assets'], list)
            or not isinstance(catalog['requirements'], list)):
        raise RefreshError('invalid-collection-catalog')
    for pin in catalog['evidence']:
        if (not isinstance(pin, dict) or set(pin) != {'path', 'sha256'}
                or digest(pin['path'], max_bytes=16 * MAX_METADATA)['sha256'] != pin['sha256']):
            raise RefreshError('collection-catalog-evidence-mismatch')
    assets, locators, origins, local, desired, unresolved = {}, set(), set(), set(), set(), []
    for asset in catalog['assets']:
        fields = {'assetId', 'kind', 'publisherCitation', 'request', 'release', 'datatype',
                  'format', 'destination', 'integrity', 'budget', 'holds', 'reuse', 'purpose',
                  'actualScope', 'localEvidence', 'provenance', 'sourceKeys', 'unresolved'}
        if (not isinstance(asset, dict) or set(asset) != fields
                or not isinstance(asset['assetId'], str) or not asset['assetId']
                or asset['assetId'] in assets or not isinstance(asset['sourceKeys'], list)
                or not isinstance(asset['unresolved'], list)):
            raise RefreshError('invalid-collection-asset-descriptor')
        key = asset['assetId']
        assets[key] = asset
        if asset['request'] and asset['request'].get('url'):
            locators.add(key)
        if asset['publisherCitation']:
            origins.add(key)
        if asset['localEvidence']:
            local.add(key)
        if asset['kind'] == 'desired-source-citation':
            desired.add(key)
        if asset['unresolved']:
            unresolved.append({'assetId': key, 'kind': asset['kind'],
                               'missing': asset['unresolved'], 'provenance': asset['provenance']})
    source_keys = {entry['spec']['source_key'] for entry in registry['sources']}
    catalog_keys = [key for asset in assets.values() for key in asset['sourceKeys']]
    if set(catalog_keys) != source_keys or len(catalog_keys) != len(source_keys):
        raise RefreshError('collection-selected-asset-binding-mismatch')
    selected = {entry['spec']['source_key']: entry['spec'] for entry in registry['sources']}
    for asset in assets.values():
        for key in asset['sourceKeys']:
            spec = SourceSpec(**selected[key])
            request = asset['request']
            if (not isinstance(request, dict) or request.get('url') != spec.url
                    or request.get('method') != spec.request_method
                    or (spec.request_method == 'POST' and request.get('body') != spec.request_body)
                    or asset['release'] != spec.release
                    or asset['destination'] != registry['resources']['storageRoot']
                    or asset['budget'] != registry['resources']):
                raise RefreshError('collection-selected-asset-contract-mismatch')
    rows, countries, mapped = set(), set(), 0
    for row in catalog['requirements']:
        if (not isinstance(row, dict) or set(row) !=
                {'country', 'type', 'assetIds', 'status', 'coverageQualification', 'evidence'}
                or not re.fullmatch(r'[A-Z]{2}', row['country'])
                or not isinstance(row['type'], str) or not row['type']
                or not isinstance(row['assetIds'], list)
                or not set(row['assetIds']) <= assets.keys()
                or row['evidence'] not in catalog['evidence']):
            raise RefreshError('invalid-collection-requirement')
        key = (row['country'], row['type'])
        if key in rows:
            raise RefreshError('duplicate-collection-requirement')
        rows.add(key)
        countries.add(row['country'])
        mapped += bool(row['assetIds'])
    return {'catalogVersion': catalog['version'], 'assetDescriptors': len(assets),
            'knownRecordedLocatorDescriptors': len(locators),
            'publisherCitationDescriptors': len(origins), 'unresolvedDescriptors': len(unresolved),
            'declaredLocalDescriptors': len(local), 'desiredSourceCitations': len(desired),
            'selectedExecutableSources': len(source_keys), 'countriesRepresented': len(countries),
            'countryTypeRequirements': len(rows), 'requirementsWithDeclaredAssetEdges': mapped,
            'requirementsWithoutDeclaredAssetEdges': len(rows) - mapped,
            'mappingComplete': False, 'countryComplete': False,
            'qualification': catalog['qualification'], 'unresolved': unresolved}
