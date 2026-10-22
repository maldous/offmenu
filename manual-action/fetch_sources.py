#!/usr/bin/env python3
"""Finite Foo-only acquisition into a private cache; never import, ingest or upload data.

Standard library only. Network calls are GETs for exact reviewed manifest URLs.
Downloaded JavaScript is inert archive data and is never imported or executed.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import fcntl
import gzip
import hashlib
import http.client
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import socket
import ssl
import stat
import tarfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import uuid
import xml.etree.ElementTree as ET

MANIFEST = Path(__file__).with_name('fetch-sources.json')
DEFAULT_CACHE = Path('/srv/offmenu-refresh/outputs/additional-sources-20261022/source-cache')
DEFAULT_RECEIPT = DEFAULT_CACHE.parent / 'receipts' / 'fetch-summary.json'
CHUNK = 64 * 1024
SCHEMA = 'offmenu-source-fetch/1'
ID = re.compile(r'^[a-z0-9][a-z0-9_-]{0,79}$')
SHA = re.compile(r'^[a-f0-9]{64}$')
STATUSES = {'complete', 'reused', 'partial', 'blocked', 'disabled'}
CODES = {'none', 'disabled', 'disk_reserve', 'wall_time_limit', 'cancelled',
         'byte_budget', 'source_byte_limit', 'size_mismatch', 'checksum_mismatch',
         'invalid_payload', 'html_or_auth_payload', 'http_auth_denied',
         'http_not_found', 'http_error', 'rate_limit_deferred', 'network_error',
         'redirect_refused', 'range_invalid', 'source_changed', 'unsafe_path',
         'cache_conflict', 'checkpoint_invalid', 'unexpected_error'}


def utc():
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode()


class Refusal(Exception):
    def __init__(self, code):
        self.code = code if code in CODES else 'unexpected_error'
        super().__init__(self.code)


def safe_path(path, create=False):
    """Reject symlinks in every component, including pre-existing output names."""
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise Refusal('unsafe_path')
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        try:
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise Refusal('unsafe_path')
        except FileNotFoundError:
            if create:
                current.mkdir(mode=0o700)
    return path


def regular(path):
    safe_path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise Refusal('unsafe_path')
    return os.fdopen(fd, 'rb')


def read_json(path, limit=1024 * 1024):
    with regular(path) as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise Refusal('checkpoint_invalid')
    return json.loads(raw)


def atomic_json(path, value):
    path = safe_path(path)
    safe_path(path.parent, create=True)
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(canonical(value) + b'\n')
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary.exists():
            temporary.unlink()


def digest_file(path, budget=None):
    digest = hashlib.sha256()
    with regular(path) as stream:
        while True:
            if budget:
                budget.check()
            block = stream.read(CHUNK)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def checked_url(url, hosts, http_exception=None):
    parsed = urllib.parse.urlsplit(url)
    http_allowed = (http_exception is not None and url == http_exception and parsed.scheme == 'http')
    if ((parsed.scheme != 'https' and not http_allowed) or parsed.username or parsed.password or parsed.fragment
            or (parsed.port not in (None, 443) and not (http_allowed and parsed.port == 8080)) or parsed.hostname not in hosts
            or any(c in url for c in '\r\n\x00')):
        raise Refusal('redirect_refused')
    return url


def clean_url(url):
    """Never persist signed redirect queries or credentials."""
    p = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((p.scheme, (p.hostname or '') + (':' + str(p.port) if p.port is not None else ''), p.path, '', ''))


class RestrictedRedirect(urllib.request.HTTPRedirectHandler):
    max_redirections = 5
    max_repeats = 2

    def __init__(self, hosts):
        self.hosts = hosts
        self.chain = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        checked_url(newurl, self.hosts)
        self.chain.append({'status': code, 'url': clean_url(newurl)})
        if len(self.chain) > 5:
            raise Refusal('redirect_refused')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Transport:
    def __call__(self, artifact, headers, timeout):
        redirect = RestrictedRedirect(set(artifact['allowed_hosts']))
        opener = urllib.request.build_opener(redirect, urllib.request.HTTPSHandler(context=ssl.create_default_context()))
        # No CookieProcessor, password manager, bearer token, browser session or auth.
        request = urllib.request.Request(checked_url(artifact['url'], set(artifact['allowed_hosts']), artifact.get('http_exception')), headers=headers, method='GET')
        result = opener.open(request, timeout=timeout)
        checked_url(result.geturl(), set(artifact['allowed_hosts']), artifact.get('http_exception'))
        result.redirect_chain = redirect.chain
        return result


def validate_manifest(value):
    if (value.get('schema') != 'offmenu-fetch-sources/1' or value.get('execution_host') != 'Foo'
            or value.get('operation') != 'acquisition_only' or value.get('ingestion_enabled') is not False
            or value.get('production_enabled') is not True):
        raise ValueError('invalid_manifest_boundary')
    seen, families = set(), set()
    sources = value.get('sources')
    if not isinstance(sources, list) or not 1 <= len(sources) <= 100:
        raise ValueError('invalid_sources')
    for source in sources:
        sid = source.get('id', '')
        if not ID.fullmatch(sid) or sid in seen or type(source.get('production_enabled')) is not bool:
            raise ValueError('invalid_source')
        seen.add(sid)
        if not source['production_enabled']:
            if not source.get('disabled_reason'):
                raise ValueError('missing_disabled_reason')
            continue
        if (source.get('already_retained') is not False or source.get('rights_status') != 'verified_open_content'
                or source.get('access_status') != 'public_no_registration' or not source.get('license')
                or not source.get('license_evidence') or not source.get('attribution')):
            raise ValueError('source_not_cleared')
        family = source.get('lineage_family')
        if not family or family in families:
            raise ValueError('duplicate_lineage')
        families.add(family)
        artifacts = source.get('artifacts')
        if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= 50:
            raise ValueError('invalid_artifacts')
        files = set()
        for artifact in artifacts:
            name = artifact.get('name', '')
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,150}', name) or name in files:
                raise ValueError('invalid_artifact_name')
            files.add(name)
            hosts = artifact.get('allowed_hosts', [])
            if not isinstance(hosts, list) or not hosts or len(hosts) > 10:
                raise ValueError('invalid_hosts')
            checked_url(artifact['url'], hosts, artifact.get('http_exception'))
            if artifact.get('http_exception') and (artifact['format'] not in {'xml', 'csv', 'json'} or artifact.get('transport_integrity') != 'unverified_http'):
                raise ValueError('invalid_http_exception')
            if type(artifact.get('max_bytes')) is not int or not 1 <= artifact['max_bytes'] <= 512 * 1024**2:
                raise ValueError('invalid_max_bytes')
            if artifact.get('expected_bytes') is not None and (type(artifact['expected_bytes']) is not int or not 1 <= artifact['expected_bytes'] <= artifact['max_bytes']):
                raise ValueError('invalid_expected_bytes')
            if artifact.get('sha256') is not None and not SHA.fullmatch(artifact['sha256']):
                raise ValueError('invalid_sha256')
            if artifact.get('format') not in {'jsonl.gz', 'tar.gz', 'xml', 'csv', 'json', 'html_recipe'}:
                raise ValueError('invalid_format')
            if not 1 <= artifact.get('max_expanded_bytes', 0) <= 1024**3:
                raise ValueError('invalid_expansion_limit')
    if not any(s['production_enabled'] for s in sources):
        raise ValueError('no_enabled_source')
    return value


class Budget:
    def __init__(self, root, seconds=1200, reserve=10 * 1024**3, max_bytes=256 * 1024**2,
                 cancelled=None, clock=time.monotonic, sleep=time.sleep):
        self.root, self.seconds, self.reserve, self.max_bytes = Path(root), seconds, reserve, max_bytes
        self.clock, self.sleep = clock, sleep
        self.deadline = clock() + seconds
        self.cancelled = cancelled or threading.Event()
        self.transferred = 0
        self.lock = threading.Lock()
        self.next_host = {}
        self.next_bytes_at = clock()
        self.cooldowns = {}
        self.cooldown_path = self.root / 'host-rate-limits.private.json'
        if self.cooldown_path.exists():
            data = read_json(self.cooldown_path)
            if not isinstance(data, dict) or any(not isinstance(k, str) or not isinstance(v, (float, int)) or not math.isfinite(v) for k, v in data.items()):
                raise Refusal('checkpoint_invalid')
            self.cooldowns = data

    def check(self):
        if self.cancelled.is_set():
            raise Refusal('cancelled')
        if self.clock() >= self.deadline:
            raise Refusal('wall_time_limit')

    def consume(self, count):
        self.check()
        with self.lock:
            if self.transferred + count > self.max_bytes:
                raise Refusal('byte_budget')
            # Reserve applies to the shared filesystem, independent of this run.
            if shutil.disk_usage(self.root).free < self.reserve + count + 2 * CHUNK:
                raise Refusal('disk_reserve')
            self.transferred += count
            at = max(self.clock(), self.next_bytes_at)
            self.next_bytes_at = at + count / (2 * 1024**2)
        self.delay(max(0, at - self.clock()))

    def delay(self, seconds):
        if seconds > max(0, self.deadline - self.clock()):
            raise Refusal('rate_limit_deferred')
        end = self.clock() + seconds
        while self.clock() < end:
            self.check()
            self.sleep(min(1, end - self.clock()))

    def defer_host(self, host, seconds):
        with self.lock:
            self.cooldowns[host] = max(self.cooldowns.get(host, 0), time.time() + seconds)
            atomic_json(self.cooldown_path, self.cooldowns)

    def throttle(self, host, interval=1):
        self.delay(max(0, self.cooldowns.get(host, 0) - time.time()))
        with self.lock:
            now = self.clock()
            at = max(now, self.next_host.get(host, now))
            self.next_host[host] = at + interval
        self.delay(max(0, at - self.clock()))


def retry_delay(header, attempt):
    if header:
        try:
            seconds = float(header)
            if math.isfinite(seconds) and seconds >= 0:
                return seconds
        except ValueError:
            try:
                when = parsedate_to_datetime(header)
                return max(0, when.timestamp() - time.time())
            except (ValueError, TypeError, OverflowError):
                pass
    return min(60, 2**attempt)


class LimitedReader:
    """Bound total decompression and any single metadata allocation in tarfile."""
    def __init__(self, stream, limit, budget):
        self.stream, self.remaining, self.budget = stream, limit, budget

    def read(self, size=-1):
        self.budget.check()
        if size < 0 or size > self.remaining or size > 8 * 1024**2:
            raise Refusal('invalid_payload')
        data = self.stream.read(size)
        self.remaining -= len(data)
        return data


def validate_payload(path, artifact, budget):
    """Data-only bounded integrity checks. Archives are inspected, never extracted."""
    with regular(path) as stream:
        prefix = stream.read(4096).lstrip(b'\xef\xbb\xbf \t\r\n').lower()
    if artifact['format'] != 'html_recipe' and prefix.startswith((b'<!doctype html', b'<html', b'<head', b'<body')):
        raise Refusal('html_or_auth_payload')
    kind, cap = artifact['format'], artifact['max_expanded_bytes']
    try:
        if kind == 'jsonl.gz':
            expanded = 0
            count = 0
            with regular(path) as raw, gzip.GzipFile(fileobj=raw) as stream:
                while True:
                    budget.check()
                    line = stream.readline(4 * 1024**2 + 1)
                    if not line:
                        break
                    expanded += len(line)
                    if len(line) > 4 * 1024**2 or expanded > cap or not isinstance(json.loads(line), dict):
                        raise Refusal('invalid_payload')
                    count += 1
            if count == 0:
                raise Refusal('invalid_payload')
        elif kind == 'tar.gz':
            expanded, count, names = 0, 0, set()
            # Streaming decode plus explicit member/byte caps; no extraction call exists.
            with regular(path) as raw, gzip.GzipFile(fileobj=raw) as decoded:
                limited = LimitedReader(decoded, cap, budget)
                archive = tarfile.open(fileobj=limited, mode='r|')
                with archive:
                    for member in archive:
                        budget.check()
                        name = PurePosixPath(member.name)
                        normalized = str(name)
                        count += 1
                        if (count > 10000 or name.is_absolute() or '..' in name.parts or '\\' in member.name
                                or normalized in names or member.issym() or member.islnk()
                                or not (member.isfile() or member.isdir()) or member.issparse()
                                or member.size < 0 or member.size > 8 * 1024**2):
                            raise Refusal('invalid_payload')
                        names.add(normalized)
                        expanded += member.size
                        if expanded > cap:
                            raise Refusal('invalid_payload')
                        if member.isfile():
                            stream = archive.extractfile(member)
                            while stream.read(CHUNK):
                                budget.check()
                while limited.read(min(CHUNK, limited.remaining)):
                    budget.check()
                if limited.remaining == 0 and decoded.read(1):
                    raise Refusal('invalid_payload')
            if count == 0:
                raise Refusal('invalid_payload')
        elif kind == 'xml':
            with regular(path) as stream:
                body = stream.read(cap + 1)
            if len(body) > cap or re.search(br'<!\s*(?:DOCTYPE|ENTITY)', body, re.I):
                raise Refusal('invalid_payload')
            class NoDoctype(ET.TreeBuilder):
                def doctype(self, name, pubid, system):
                    raise Refusal('invalid_payload')
            root = ET.fromstring(body, parser=ET.XMLParser(target=NoDoctype()))
            if root.tag.lower().split('}')[-1] in {'html', 'error', 'errors'}:
                raise Refusal('html_or_auth_payload')
        elif kind == 'json':
            with regular(path) as stream:
                body = stream.read(cap + 1)
            if len(body) > cap:
                raise Refusal('invalid_payload')
            data = json.loads(body)
            if not isinstance(data, list) or not data or not all(isinstance(row, dict) for row in data):
                raise Refusal('invalid_payload')
        elif kind == 'html_recipe':
            with regular(path) as stream:
                body = stream.read(cap + 1)
            if len(body) > cap or not re.search(br'<html(?:\s|>)', body, re.I):
                raise Refusal('invalid_payload')
            # Exact reviewed pages only. Retain HTML inertly; no browser/render/import.
            if not all(marker.encode() in body for marker in artifact.get('required_markers', [])):
                raise Refusal('html_or_auth_payload')
        elif kind == 'csv':
            if prefix.startswith((b'{', b'[', b'<?xml', b'<error')) or not prefix:
                raise Refusal('invalid_payload')
            if path.stat().st_size > cap or b'\x00' in prefix:
                raise Refusal('invalid_payload')
    except (ValueError, UnicodeError, gzip.BadGzipFile, EOFError, tarfile.TarError, ET.ParseError, OSError) as error:
        raise Refusal('invalid_payload') from error


def artifact_key(source, artifact):
    return hashlib.sha256(canonical({'source': source['id'], 'revision': source['revision'], 'artifact': artifact})).hexdigest()


def artifact_paths(directory, artifact):
    name = artifact['name']
    return directory / name, directory / (name + '.part'), directory / (name + '.checkpoint.json'), directory / (name + '.receipt.json')


def fetch_artifact(source, artifact, directory, budget, transport=None, attempts=3):
    transport = transport or Transport()
    final, part, checkpoint, receipt_path = artifact_paths(directory, artifact)
    for p in (final, part, checkpoint, receipt_path):
        safe_path(p)
    key = artifact_key(source, artifact)
    common = {'schema': SCHEMA, 'source_id': source['id'], 'artifact': artifact['name'], 'artifact_key': key,
              'source_revision': source['revision'], 'origin_url': artifact['url'], 'license': source['license'],
              'license_evidence': source['license_evidence'], 'attribution': source['attribution'],
              'license_scope_note': source.get('license_scope_note'),
              'artifact_metadata_evidence': source.get('artifact_metadata_evidence'),
              'catalog_resource_id': artifact.get('resource_id'),
              'artifact_license_evidence': artifact.get('license_evidence'),
              'transport_integrity': artifact.get('transport_integrity', 'https'), 'acquisition_only': True,
              'ingested': False, 'raw_data_uploaded': False}
    if final.exists():
        if not receipt_path.exists():
            raise Refusal('cache_conflict')
        receipt = read_json(receipt_path)
        if receipt.get('artifact_key') != key or receipt.get('status') != 'complete':
            raise Refusal('cache_conflict')
        if final.stat().st_size != receipt.get('bytes') or digest_file(final, budget) != receipt.get('sha256'):
            raise Refusal('cache_conflict')
        return {'name': artifact['name'], 'status': 'reused', 'bytes': receipt['bytes'], 'sha256': receipt['sha256'], 'error_code': 'none'}
    if receipt_path.exists() and part.exists():
        # Recover the receipt-first atomic-rename crash window without another GET.
        orphan = read_json(receipt_path)
        if (orphan.get('artifact_key') == key and orphan.get('status') == 'complete'
                and part.stat().st_size == orphan.get('bytes')
                and digest_file(part, budget) == orphan.get('sha256')):
            validate_payload(part, artifact, budget)
            os.replace(part, final)
            checkpoint.unlink(missing_ok=True)
            return {'name': artifact['name'], 'status': 'complete', 'bytes': orphan['bytes'], 'sha256': orphan['sha256'], 'error_code': 'none'}
    state = {'artifact_key': key, 'url': artifact['url'], 'bytes': 0, 'etag': None, 'last_modified': None,
             'expected_total': artifact.get('expected_bytes'), 'redirects': [], 'final_url': None}
    if checkpoint.exists():
        previous = read_json(checkpoint)
        if previous.get('artifact_key') != key:
            raise Refusal('cache_conflict')
        state.update(previous)
    elif part.exists():
        raise Refusal('checkpoint_invalid')
    last_code = 'network_error'
    for attempt in range(attempts):
        budget.check()
        offset = part.stat().st_size if part.exists() else 0
        committed = state.get('bytes', 0)
        if type(committed) is not int or committed < 0 or offset < committed:
            raise Refusal('checkpoint_invalid')
        if offset > committed:
            # After a crash, trust only durably checkpointed bytes/identity.
            with open(part, 'r+b') as owned:
                owned.truncate(committed); owned.flush(); os.fsync(owned.fileno())
            offset = committed
        if offset > artifact['max_bytes']:
            raise Refusal('source_byte_limit')
        validator = state.get('etag')
        if validator and validator.startswith('W/'):
            validator = None
        validator = validator or state.get('last_modified')
        if offset and not (validator or artifact.get('sha256')):
            state['bytes'] = 0
            atomic_json(checkpoint, state)
            # Restart only this owned incomplete temporary, never a final artifact.
            with open(part, 'wb') as owned:
                owned.flush(); os.fsync(owned.fileno())
            offset = 0
            state['restarted_without_validator'] = True
        state['bytes'] = offset
        atomic_json(checkpoint, state)
        headers = {'User-Agent': 'OffMenu-Acquisition/1.0 (bounded public-source archival)', 'Accept-Encoding': 'identity'}
        if offset:
            headers['Range'] = f'bytes={offset}-'
            if validator:
                headers['If-Range'] = validator
        budget.throttle(urllib.parse.urlsplit(artifact['url']).hostname, source.get('request_interval_seconds', 1))
        response = None
        try:
            response = transport(artifact, headers, min(30, max(1, budget.deadline - budget.clock())))
            code = response.status
            if code not in (200, 206):
                raise Refusal('http_error')
            content_type = response.headers.get('Content-Type', '').split(';')[0].lower()
            if artifact['format'] != 'html_recipe' and content_type in {'text/html', 'application/xhtml+xml'}:
                raise Refusal('html_or_auth_payload')
            if response.headers.get('Content-Encoding', 'identity').lower() not in {'identity', ''}:
                raise Refusal('invalid_payload')
            length = response.headers.get('Content-Length')
            if length is not None and not re.fullmatch(r'\d+', length):
                raise Refusal('size_mismatch')
            length = int(length) if length is not None else None
            if code == 206:
                match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('Content-Range', ''))
                if not offset or not match or int(match[1]) != offset or int(match[2]) + 1 != int(match[3]):
                    raise Refusal('range_invalid')
                total = int(match[3])
                if length is not None and length != total - offset:
                    raise Refusal('range_invalid')
                if validator and state.get('etag') and not state['etag'].startswith('W/') and response.headers.get('ETag') != state['etag']:
                    raise Refusal('source_changed')
            else:
                # Discard old bytes durably BEFORE checkpointing any new entity identity.
                if offset:
                    state['bytes'] = 0
                    atomic_json(checkpoint, state)
                    with open(part, 'wb') as owned:
                        owned.flush(); os.fsync(owned.fileno())
                offset = 0
                total = length
            if total is not None and (total > artifact['max_bytes'] or (artifact.get('expected_bytes') is not None and total != artifact['expected_bytes'])):
                raise Refusal('size_mismatch')
            state.update(bytes=offset, content_type=content_type, response_observed_at=utc(), etag=response.headers.get('ETag'), last_modified=response.headers.get('Last-Modified'),
                         expected_total=total or artifact.get('expected_bytes'), final_url=clean_url(response.geturl()),
                         redirects=getattr(response, 'redirect_chain', []))
            atomic_json(checkpoint, state)
            flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | (os.O_APPEND if offset else os.O_TRUNC)
            fd = os.open(part, flags, 0o600)
            received = offset
            try:
                with os.fdopen(fd, 'wb') as out:
                    checkpoint_at = budget.clock()
                    try:
                        while True:
                            budget.check()
                            block = response.read1(CHUNK) if hasattr(response, 'read1') else response.read(CHUNK)
                            if not block:
                                break
                            if received + len(block) > artifact['max_bytes']:
                                raise Refusal('source_byte_limit')
                            budget.consume(len(block))
                            out.write(block)
                            received += len(block)
                            if budget.clock() - checkpoint_at >= 3:
                                out.flush(); os.fsync(out.fileno())
                                state.update(bytes=received, updated_at=utc())
                                atomic_json(checkpoint, state)
                                checkpoint_at = budget.clock()
                    finally:
                        out.flush(); os.fsync(out.fileno())
                        state.update(bytes=received, updated_at=utc())
                        atomic_json(checkpoint, state)
            finally:
                response.close()
                response = None
            if state['expected_total'] is not None and received != state['expected_total']:
                raise Refusal('size_mismatch')
            observed = digest_file(part, budget)
            if artifact.get('sha256') and observed != artifact['sha256']:
                raise Refusal('checksum_mismatch')
            validate_payload(part, artifact, budget)
            receipt = {**common, **{k: state.get(k) for k in ('etag', 'last_modified', 'final_url', 'redirects', 'content_type', 'response_observed_at')},
                       'status': 'complete', 'bytes': received, 'sha256': observed, 'completed_at': utc(),
                       'expected_sha256': artifact.get('sha256'), 'expected_bytes': artifact.get('expected_bytes'),
                       'checksum_basis': 'publisher_sha256_verified' if artifact.get('sha256') else 'locally_observed_not_publisher_authenticated'}
            # Receipt-first crash recovery: an orphan receipt with .part is safe to revalidate.
            atomic_json(receipt_path, receipt)
            safe_path(final)
            if final.exists():
                raise Refusal('cache_conflict')
            os.replace(part, final)
            checkpoint.unlink(missing_ok=True)
            return {'name': artifact['name'], 'status': 'complete', 'bytes': received, 'sha256': observed, 'error_code': 'none'}
        except Refusal as error:
            if error.code in {'checksum_mismatch', 'invalid_payload', 'html_or_auth_payload'} and part.exists():
                # Keep at most one owned rejected temporary; it is never promoted or run.
                rejected = safe_path(directory / (artifact['name'] + '.rejected'))
                state.update(bytes=0, etag=None, last_modified=None, rejection_code=error.code)
                atomic_json(checkpoint, state)
                os.replace(part, rejected)
                if attempt + 1 < attempts and error.code != 'html_or_auth_payload':
                    budget.delay(2**attempt)
                    continue
            raise
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                raise Refusal('http_auth_denied') from None
            if error.code == 404:
                raise Refusal('http_not_found') from None
            if error.code == 416:
                # May be a fully downloaded partial after interruption: verify locally.
                if part.exists() and artifact.get('expected_bytes') == part.stat().st_size and artifact.get('sha256') == digest_file(part, budget):
                    validate_payload(part, artifact, budget)
                    atomic_json(receipt_path, {**common, 'status': 'complete', 'bytes': part.stat().st_size,
                        'sha256': artifact['sha256'], 'completed_at': utc(), 'expected_sha256': artifact['sha256'],
                        'expected_bytes': artifact['expected_bytes'], 'checksum_basis': 'publisher_sha256_verified'})
                    os.replace(part, final)
                    checkpoint.unlink(missing_ok=True)
                    return {'name': artifact['name'], 'status': 'complete', 'bytes': final.stat().st_size, 'sha256': artifact['sha256'], 'error_code': 'none'}
                raise Refusal('range_invalid') from None
            if error.code not in (429, 500, 502, 503, 504):
                raise Refusal('http_error') from None
            delay = retry_delay(error.headers.get('Retry-After'), attempt)
            budget.defer_host(urllib.parse.urlsplit(artifact['url']).hostname, delay)
            state['retry_not_before'] = time.time() + delay
            atomic_json(checkpoint, state)
            if attempt + 1 == attempts:
                raise Refusal('rate_limit_deferred' if error.code == 429 else 'http_error') from None
            budget.delay(delay)
            last_code = 'http_error'
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException, ssl.SSLError) as error:
            last_code = 'network_error'
            if attempt + 1 < attempts:
                budget.delay(2**attempt)
        finally:
            if response is not None:
                response.close()
    raise Refusal(last_code)


def check_robots(source, directory, budget, transport):
    url = source.get('robots_url')
    if not url:
        return
    host = urllib.parse.urlsplit(url).hostname
    checked_url(url, [host])
    artifact = {'url': url, 'allowed_hosts': [host]}
    budget.throttle(host, source.get('request_interval_seconds', 1))
    response = None
    try:
        response = (transport or Transport())(artifact, {'User-Agent': 'OffMenu-Acquisition/1.0', 'Accept-Encoding': 'identity'}, 30)
        if response.status != 200:
            raise Refusal('http_auth_denied')
        data = bytearray()
        while True:
            budget.check()
            block = response.read1(CHUNK) if hasattr(response, 'read1') else response.read(CHUNK)
            if not block:
                break
            if len(data) + len(block) > 256 * 1024:
                raise Refusal('invalid_payload')
            budget.consume(len(block)); data.extend(block)
        text = data.decode('utf-8')
        if '<html' in text.lower():
            raise Refusal('html_or_auth_payload')
        policy = urllib.robotparser.RobotFileParser(url)
        policy.parse(text.splitlines())
        if not all(policy.can_fetch('OffMenu-Acquisition', a['url']) for a in source['artifacts']):
            raise Refusal('http_auth_denied')
        atomic_json(directory / 'robots-policy.receipt.json', {'url': url, 'observed_at': utc(), 'sha256': hashlib.sha256(data).hexdigest(), 'exact_urls_permitted': True})
    except urllib.error.HTTPError as error:
        if error.code in (429, 503):
            budget.defer_host(host, retry_delay(error.headers.get('Retry-After'), 0))
            raise Refusal('rate_limit_deferred') from None
        raise Refusal('http_auth_denied' if error.code in (401, 403) else 'http_error') from None
    finally:
        if response is not None:
            response.close()


def fetch_source(source, root, budget, transport=None):
    result = {'source_id': source['id'], 'status': 'disabled', 'artifacts': [], 'error_code': 'disabled'}
    if not source['production_enabled']:
        return result
    directory = safe_path(root / source['id'], create=True)
    try:
        check_robots(source, directory, budget, transport)
    except Exception as error:
        result.update(status='blocked', error_code=error.code if isinstance(error, Refusal) else 'network_error')
        atomic_json(directory / 'status.json', result)
        return result
    for artifact in source['artifacts']:
        try:
            checkpoint = artifact_paths(directory, artifact)[2]
            if checkpoint.exists():
                retry_at = read_json(checkpoint).get('retry_not_before', 0)
                budget.delay(max(0, retry_at - time.time()))
            row = fetch_artifact(source, artifact, directory, budget, transport)
        except Refusal as error:
            row = {'name': artifact['name'], 'status': 'blocked', 'bytes': 0, 'sha256': None, 'error_code': error.code}
        except Exception:
            row = {'name': artifact['name'], 'status': 'blocked', 'bytes': 0, 'sha256': None, 'error_code': 'unexpected_error'}
        result['artifacts'].append(row)
        atomic_json(directory / 'status.json', {**result, 'status': 'running', 'updated_at': utc()})
    statuses = [r['status'] for r in result['artifacts']]
    result['status'] = 'reused' if all(s == 'reused' for s in statuses) else 'complete' if all(s in {'complete', 'reused'} for s in statuses) else 'partial' if any(s in {'complete', 'reused'} for s in statuses) else 'blocked'
    result['error_code'] = next((r['error_code'] for r in result['artifacts'] if r['error_code'] != 'none'), 'none')
    atomic_json(directory / 'status.json', {**result, 'updated_at': utc()})
    return result


def sanitized_summary(value):
    """Independent fixed projection: never expose payloads, local paths or redirects."""
    sources = []
    for source in value.get('sources', []):
        if source.get('status') == 'disabled':
            continue
        sid = source.get('source_id', '')
        if not ID.fullmatch(sid):
            raise ValueError('invalid_source_id')
        items = source.get('artifacts', [])
        sources.append({'source_id': sid, 'status': source['status'] if source.get('status') in STATUSES else 'blocked',
                        'files_complete': sum(r.get('status') in {'complete', 'reused'} for r in items),
                        'files_reused': sum(r.get('status') == 'reused' for r in items),
                        'files_blocked': sum(r.get('status') == 'blocked' for r in items),
                        'bytes_retained': sum(r['bytes'] for r in items if r.get('status') in {'complete', 'reused'} and type(r.get('bytes')) is int and r['bytes'] >= 0),
                        'sha256': [r['sha256'] for r in items if isinstance(r.get('sha256'), str) and SHA.fullmatch(r['sha256'])],
                        'error_code': source.get('error_code') if source.get('error_code') in CODES else 'unexpected_error'})
    return {'schema': 'offmenu-source-fetch-summary/1', 'schemaVersion': 'offmenu-source-fetch-summary/1', 'execution_host': 'Foo', 'operation': 'acquisition_only',
            'manifest_sha256': value['manifest_sha256'], 'status': value['status'], 'sources': sources,
            'database_mutations': 0, 'raw_data_uploaded': False, 'downloaded_code_executed': False,
            'disabled_source_count': sum(s.get('status') == 'disabled' for s in value.get('sources', [])),
            'recipe_or_menu_record_count': None, 'counts_are': 'files_and_bytes_not_records', 'updated_at': value['updated_at']}


def sanitize_report(value):
    """Strict projector for dispatcher-returned summary, excluding any extra data."""
    if value.get('schema') == 'offmenu-source-fetch-failure/1':
        if (value.get('schemaVersion') != 'offmenu-source-fetch-failure/1' or value.get('status') != 'blocked'
                or value.get('error_code') not in CODES or value.get('database_mutations') != 0 or value.get('raw_data_uploaded') is not False):
            raise ValueError('invalid_fetch_failure')
        return {key: value[key] for key in ('schema', 'schemaVersion', 'status', 'error_code', 'database_mutations', 'raw_data_uploaded')}
    if (value.get('schema') != 'offmenu-source-fetch-summary/1' or value.get('schemaVersion') != 'offmenu-source-fetch-summary/1'
            or value.get('operation') != 'acquisition_only' or value.get('execution_host') != 'Foo'
            or value.get('database_mutations') != 0 or value.get('raw_data_uploaded') is not False
            or value.get('downloaded_code_executed') is not False or value.get('recipe_or_menu_record_count') is not None):
        raise ValueError('invalid_fetch_summary')
    if value.get('status') not in {'complete', 'partial'} or not SHA.fullmatch(value.get('manifest_sha256', '')):
        raise ValueError('invalid_fetch_summary')
    rows = value.get('sources')
    if not isinstance(rows, list) or len(rows) > 100:
        raise ValueError('invalid_fetch_summary')
    clean = []
    for row in rows:
        if not ID.fullmatch(row.get('source_id', '')) or row.get('status') not in STATUSES or row.get('error_code') not in CODES:
            raise ValueError('invalid_fetch_source_summary')
        item = {key: row[key] for key in ('source_id', 'status', 'error_code')}
        for key in ('files_complete', 'files_reused', 'files_blocked', 'bytes_retained'):
            number = row.get(key)
            if type(number) is not int or number < 0:
                raise ValueError('invalid_fetch_count')
            item[key] = number
        hashes = row.get('sha256')
        if not isinstance(hashes, list) or len(hashes) > 50 or any(not isinstance(h, str) or not SHA.fullmatch(h) for h in hashes):
            raise ValueError('invalid_fetch_checksum')
        item['sha256'] = hashes
        clean.append(item)
    if value['status'] == 'complete' and (not clean or any(r['status'] not in {'complete', 'reused'} or r['files_blocked'] or not r['files_complete'] for r in clean)):
        raise ValueError('contradictory_complete_summary')
    disabled = value.get('disabled_source_count', 0)
    if type(disabled) is not int or not 0 <= disabled <= 100:
        raise ValueError('invalid_disabled_count')
    timestamp = value.get('updated_at', '')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', timestamp):
        raise ValueError('invalid_fetch_timestamp')
    return {'schema': 'offmenu-source-fetch-summary/1', 'schemaVersion': 'offmenu-source-fetch-summary/1', 'execution_host': 'Foo', 'operation': 'acquisition_only',
            'manifest_sha256': value['manifest_sha256'], 'status': value['status'], 'sources': clean,
            'database_mutations': 0, 'raw_data_uploaded': False, 'downloaded_code_executed': False,
            'disabled_source_count': disabled,
            'recipe_or_menu_record_count': None, 'counts_are': 'files_and_bytes_not_records', 'updated_at': timestamp}


def run_fetch(manifest, root, receipt_path, workers=2, seconds=1200, reserve=10 * 1024**3,
              max_bytes=256 * 1024**2, transport=None, cancelled=None):
    validate_manifest(manifest)
    root = safe_path(root, create=True)
    if not 1 <= workers <= 2 or not 1 <= seconds <= 1200 or not 0 <= reserve or not 1 <= max_bytes <= 512 * 1024**2:
        raise ValueError('invalid_resource_limit')
    lock = os.open(root / '.fetch.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        budget = Budget(root, seconds, reserve, max_bytes, cancelled)
        budget.consume(0)
        result = {'manifest_sha256': hashlib.sha256(canonical(manifest)).hexdigest(), 'status': 'running', 'sources': [], 'updated_at': utc()}
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='offmenu-fetch') as pool:
            jobs = {pool.submit(fetch_source, source, root, budget, transport): source['id'] for source in manifest['sources']}
            for job in as_completed(jobs):
                try:
                    row = job.result()
                except Exception:
                    row = {'source_id': jobs[job], 'status': 'blocked', 'artifacts': [], 'error_code': 'unexpected_error'}
                result['sources'].append(row)
                result['sources'].sort(key=lambda row: row['source_id'])
                result['updated_at'] = utc()
                atomic_json(root / 'fetch-status.private.json', result)
        result['status'] = 'complete' if all(s['status'] in {'complete', 'reused', 'disabled'} for s in result['sources']) else 'partial'
        result['updated_at'] = utc()
        atomic_json(root / 'fetch-status.private.json', result)
        summary = sanitized_summary(result)
        atomic_json(receipt_path, summary)
        return summary
    finally:
        os.close(lock)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-root', type=Path, default=DEFAULT_CACHE)
    parser.add_argument('--receipt-output', type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument('--workers', type=int, choices=(1, 2), default=2)
    parser.add_argument('--seconds', type=int, default=1200)
    parser.add_argument('--disk-reserve-gib', type=int, default=10)
    parser.add_argument('--max-transfer-mib', type=int, default=256)
    parser.add_argument('--validate-only', action='store_true', help='Offline manifest validation, no cache/network writes')
    args = parser.parse_args(argv)
    manifest = validate_manifest(read_json(MANIFEST))
    if args.validate_only:
        print(json.dumps({'schema': manifest['schema'], 'enabled_sources': sum(s['production_enabled'] for s in manifest['sources']), 'network': 'none'}))
        return 0
    if socket.gethostname().split('.')[0].lower() != 'foo':
        parser.error('production acquisition is Foo-only; this host is not Foo')
    if os.environ.get('RUNNER_NAME') and os.environ['RUNNER_NAME'] != 'foo-offmenu':
        parser.error('wrong runner identity')
    if args.cache_root != DEFAULT_CACHE or args.receipt_output != DEFAULT_RECEIPT:
        parser.error('use the reviewed isolated Foo cache and receipt paths')
    if args.disk_reserve_gib < 10:
        parser.error('shared-disk reserve must be at least 10 GiB')
    cancelled = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: cancelled.set())
    signal.signal(signal.SIGINT, lambda *_: cancelled.set())
    try:
        summary = run_fetch(manifest, args.cache_root, args.receipt_output, workers=args.workers,
                            seconds=args.seconds, reserve=args.disk_reserve_gib * 1024**3,
                            max_bytes=args.max_transfer_mib * 1024**2, cancelled=cancelled)
    except (Refusal, OSError, ValueError) as error:
        print(json.dumps({'schema': 'offmenu-source-fetch-failure/1', 'schemaVersion': 'offmenu-source-fetch-failure/1', 'status': 'blocked', 'error_code': error.code if isinstance(error, Refusal) else 'unexpected_error', 'database_mutations': 0, 'raw_data_uploaded': False}))
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary['status'] == 'complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())
