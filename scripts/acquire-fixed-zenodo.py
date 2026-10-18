#!/usr/bin/env python3
"""One reviewed private original through the existing acquisition engine."""
from __future__ import annotations
import hashlib
import http.client
import ssl
import threading
from datetime import datetime, timezone
from urllib.parse import urlsplit, urljoin
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from offmenu.refresh.acquisition import CachedAcquirer, HTTPSFileTransport, ResourceBudget, SourceSpec, _headers
from offmenu.refresh.core import RefreshError, atomic_json, canonical, safe_path, sha, strict_json, writer_lock

OUTPUT = Path('/srv/offmenu-refresh/outputs')
LEGACY_CACHE = Path('/srv/offmenu-refresh/cache')
SELECTION_PIN = ('docs/collection-selections/zenodo15169428-selection.json',
                 'fc52fa57a04e389a5ec47509d8043477312bc4de2aae78267ca13a99c10b7bfd')
SCHEMA = 'offmenu-fixed-original-summary/1'
DIAGNOSTIC_SCHEMA = 'offmenu-fixed-response-metadata/1'
DIAGNOSTIC_PIN = ('docs/collection-selections/zenodo15169428-head-diagnostic.json',
                  '1bfe2d00a02353e92bcf9c7177865ba4e1153380e5a2cb35eed0f4515646af79')
PRIOR_DETAIL_SHA256 = '81f842a01b388b3924ae56d240b5e13653daec1221eedd934a550abe2f935260'
SOURCE_KEY = 'global.zenodo15169428.datasetcsv.v1'
EXPECTED_BYTES = 110013794
EXPECTED_MD5 = '986efafad65c7969fde13a46d2defba0'
URL = 'https://zenodo.org/api/records/15169428/files/dataset.csv/content'
MAX_BYTES = 134217728
MAX_SECONDS = 900
GUARD = 88418025472
TTL = 30 * 86400
MAX_SCAN = 10000
MAX_METADATA = 2 * 1024 * 1024
MAX_SCAN_BYTES = 32 * 1024 * 1024
SAFETY = {'sourceContentsUploaded': False, 'nativeClaimCoverageExhaustive': False,
          'unknownClaimsAssumedEmpty': False, 'countryCoverageComplete': False,
          'semanticParsingPerformed': False, 'commercialReuseApproved': False,
          'normalizedOrGoldAdmitted': False, 'otherReservationsReleased': False}
ERRORS = {'unexpected-arguments', 'fixed-selection-invalid', 'fixed-evidence-invalid',
          'known-exact-source-observed', 'runner-metadata-scan-incomplete',
          'known-exact-source-alternate-cache', 'source-claim-uncertain',
          'source-partial-or-recovery-present', 'output-root-unavailable',
          'output-filesystem-mismatch', 'physical-reservation-unavailable',
          'physical-reservation-insufficient', 'reservation-already-present',
          'capacity-planning-bound-not-protected', 'operation-deadline-exceeded',
          'source-length-mismatch', 'source-md5-mismatch', 'source-sha256-mismatch',
          'source-header-mismatch', 'source-changed-during-validation',
          'source-response-contract-changed', 'source-xlsx-invalid',
          'network-request-limit', 'request-contract-mismatch',
          'network-byte-limit', 'collector-rejected', 'local-io-failure',
          'claim-state-write-failed', 'reservation-release-failed', 'result-write-failed',
          'cache-missing', 'cache-stale', 'cached-body-corrupt', 'cached-body-missing',
          'acquisition-record-mismatch', 'invalid-acquisition-record',
          'acquisition-evidence-missing-or-corrupt', 'response-retention-not-approved',
          'unsupported-response-vary', 'unsupported-response-encoding',
          'source-response-not-permitted', 'response-size-limit-exceeded',
          'insufficient-acquisition-disk-budget', 'acquisition-retries-exhausted',
          'acquisition-duration-limit-exceeded', 'response-duration-limit-exceeded',
          'publisher-retry-deferred', 'automatic-refresh-deferred-minimum-reuse-window'}


def deadline_check(deadline):
    if time.monotonic() >= deadline:
        raise RefreshError('operation-deadline-exceeded')


def preparation_module():
    path = ROOT / 'scripts/prepare-fixed-collection.py'
    spec = importlib.util.spec_from_file_location('fixed_custody_preparation', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_selection():
    prep = preparation_module()
    selected = strict_json(prep.pinned_bytes(ROOT, SELECTION_PIN))
    if (selected.get('schemaVersion') != 'offmenu-fixed-private-original-selection/1'
            or selected.get('sourceKey') != SOURCE_KEY or selected.get('url') != URL
            or selected.get('expectedBytes') != EXPECTED_BYTES or selected.get('expectedMD5') != EXPECTED_MD5
            or selected.get('hardTransferBytes') != MAX_BYTES or selected.get('wholeOperationSeconds') != MAX_SECONDS
            or selected.get('planningGuardBytes') != GUARD or selected.get('minimumCacheSeconds') != TTL
            or selected.get('floorAlreadyIncluded') is not True):
        raise RefreshError('fixed-selection-invalid')
    for pin in selected['evidence']:
        prep.pinned_bytes(ROOT, (pin['path'], pin['sha256']))
    snapshot = prep.imported_snapshot(ROOT)
    adopted = strict_json(prep.pinned_bytes(ROOT, prep.SUMMARY_PIN))
    # Exact-source adverse evidence wins. Missing matches do not establish global
    # absence: the selected coordinator explicitly accepts the recorded limits.
    if exact_source_match(snapshot, selected) or exact_source_match(adopted, selected):
        raise RefreshError('known-exact-source-observed')
    return selected


def exact_source_match(value, selected):
    if selected.get('schemaVersion') == 'offmenu-fixed-source-contract/1':
        aliases = {x.casefold() for x in (selected['sourceKey'], selected['url'], *selected['aliases'])}
        for algorithm, digest in selected['checksums'].items():
            aliases.update((digest, algorithm + ':' + digest))
        def walk(item):
            if isinstance(item, str): return item.casefold() in aliases
            if isinstance(item, dict): return any(walk(k) or walk(v) for k,v in item.items())
            if isinstance(item, list): return any(walk(v) for v in item)
            return False
        return walk(value)
    aliases = {x.casefold() for x in (selected['sourceKey'], selected['url'], selected['expectedMD5'],
               '15169428', *selected['aliases'])}
    def walk(item):
        if isinstance(item, str):
            item = item.casefold()
            return (item in aliases or item.removeprefix('md5:') == selected['expectedMD5']
                    or '10.5281/zenodo.15169428' in item
                    or bool(re.search(r'https://zenodo\.org/(?:api/)?records/15169428(?:/|$|[?#])', item)))
        if isinstance(item, dict):
            return any((key in {'recordId','record_id','zenodoRecordId'} and str(x) == '15169428')
                       or walk(key) or walk(x) for key, x in item.items())
        if isinstance(item, list): return any(walk(x) for x in item)
        return False
    return walk(value)


def owned_directory(path, *, create=False):
    path = safe_path(path)
    if create:
        path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir() or path.stat().st_uid != os.getuid():
        raise RefreshError('output-root-unavailable')
    return path


def read_metadata(path, *, expected_sha256=None):
    path = safe_path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_METADATA:
            raise RefreshError('runner-metadata-scan-incomplete')
        raw = stream.read(MAX_METADATA + 1)
        after = os.fstat(stream.fileno())
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if len(raw) > MAX_METADATA or identity(before) != identity(after) or identity(after) != identity(path.stat()):
        raise RefreshError('runner-metadata-scan-incomplete')
    if expected_sha256 is not None and sha(raw) != expected_sha256:
        raise RefreshError('fixed-evidence-invalid')
    return strict_json(raw), len(raw)


def inspect_runner_metadata(roots, selected, own_current, own_claim, deadline):
    """Read bounded runner metadata only. Never read native user trees or bodies."""
    scanned, metadata_bytes, metadata_files, missing = 0, 0, 0, 0
    for root in roots:
        root = safe_path(root)
        if not root.exists():
            missing += 1
            continue
        queue = [(root, 0)]
        while queue:
            directory, depth = queue.pop()
            deadline_check(deadline)
            with os.scandir(directory) as entries:
                for entry in entries:
                    scanned += 1
                    if scanned > MAX_SCAN or entry.is_symlink():
                        raise RefreshError('runner-metadata-scan-incomplete')
                    path = Path(entry.path)
                    if entry.is_dir(follow_symlinks=False):
                        if depth >= 6:
                            raise RefreshError('runner-metadata-scan-incomplete')
                        queue.append((path, depth + 1))
                    elif (entry.is_file(follow_symlinks=False) and path.suffix == '.json'
                          and (path.name in {'current.json', 'recovery.json', 'claim.json'}
                               or re.search(r'(?:^|[-_])(?:claims?|intents?)(?:[-_]|\.json$)', path.name)
                               or 'claims' in path.parts or 'intents' in path.parts)):
                        if path == own_claim:
                            continue  # Validated separately, including its exact intent.
                        value, size = read_metadata(path)
                        metadata_files += 1
                        metadata_bytes += size
                        if metadata_bytes > MAX_SCAN_BYTES:
                            raise RefreshError('runner-metadata-scan-incomplete')
                        if exact_source_match(value, selected) and path != own_current:
                            raise RefreshError('known-exact-source-alternate-cache')
    return {'entriesExamined': scanned, 'metadataFilesRead': metadata_files,
            'metadataBytesRead': metadata_bytes, 'missingRoots': missing,
            'nativeCoverageExhaustive': False}


def source_contract(selected):
    if selected.get('schemaVersion') == 'offmenu-fixed-source-contract/1':
        return {'key':selected['sourceKey'], 'url':selected['url'], 'fingerprint':sha(canonical(selected)),
                'expectedBytes':selected['expectedBytes'], 'maxBytes':selected['hardTransferBytes'],
                'seconds':selected['wholeOperationSeconds'], 'checksums':selected['checksums'],
                'validation':selected['validation']}
    return {'key':SOURCE_KEY, 'url':URL, 'fingerprint':SELECTION_PIN[1],
            'expectedBytes':EXPECTED_BYTES, 'maxBytes':MAX_BYTES, 'seconds':MAX_SECONDS,
            'checksums':{'md5':EXPECTED_MD5},
            'validation':{'kind':'csv-header','delimiter':';','fields':selected.get('headerFields',[])}}


def source_spec(selected):
    contract = source_contract(selected)
    return SourceSpec(source_key=contract['key'], url=contract['url'],
        policy_fingerprint=contract['fingerprint'], rights_reference=selected['rightsReference'],
        enabled=True, rights_approved=True, held=False, ttl_seconds=TTL,
        max_bytes=contract['expectedBytes'] or contract['maxBytes'], release=selected['release'])


def validate_original(result, selected, deadline):
    contract = source_contract(selected)
    expected, maximum, validation = contract['expectedBytes'], contract['maxBytes'], contract['validation']
    path = safe_path(result.path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    count, digest256, digestmd5 = 0, hashlib.sha256(), hashlib.md5(usedforsecurity=False)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if (not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= maximum
                or (expected is not None and before.st_size != expected)):
            raise RefreshError('source-length-mismatch')
        if validation['kind'] == 'csv-header':
            header = stream.readline(8193)
            if len(header) > 8192 or header.rstrip(b'\r\n') != validation['delimiter'].join(validation['fields']).encode('utf-8'):
                raise RefreshError('source-header-mismatch')
        elif validation['kind'] == 'prefix':
            prefix=bytes.fromhex(validation['hex'])
            if stream.read(len(prefix)) != prefix: raise RefreshError('source-header-mismatch')
        elif validation['kind'] != 'xlsx':
            raise RefreshError('fixed-selection-invalid')
        stream.seek(0)
        while True:
            deadline_check(deadline)
            block = stream.read(min(1024 * 1024, maximum - count + 1))
            deadline_check(deadline)
            if not block: break
            count += len(block)
            if count > maximum: raise RefreshError('source-length-mismatch')
            digest256.update(block); digestmd5.update(block)
        if validation['kind'] == 'xlsx':
            stream.seek(0)
            validate_xlsx(stream, deadline)
        after = os.fstat(stream.fileno())
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if identity(before) != identity(after) or identity(after) != identity(path.stat()):
        raise RefreshError('source-changed-during-validation')
    if (expected is not None and count != expected) or result.bytes != count:
        raise RefreshError('source-length-mismatch')
    if 'md5' in contract['checksums'] and digestmd5.hexdigest() != contract['checksums']['md5']:
        raise RefreshError('source-md5-mismatch')
    if (digest256.hexdigest() != result.sha256 or
            ('sha256' in contract['checksums'] and digest256.hexdigest() != contract['checksums']['sha256'])):
        raise RefreshError('source-sha256-mismatch')
    return {'bytes': count, 'sha256': result.sha256, 'publisherMD5Verified': 'md5' in contract['checksums'],
            'headerVerified': validation['kind'] in {'csv-header','prefix','xlsx'},
            'originalAcquiredAt': result.provenance['originalAcquiredAt']}


def validate_xlsx(original, deadline):
    """Validate bounded OOXML container and every ZIP CRC, without extraction/execution."""
    try:
        with zipfile.ZipFile(original) as archive:
            members=archive.infolist(); names=[m.filename for m in members]
            if (not 1<=len(members)<=256 or len(set(names))!=len(names)
                    or not {'[Content_Types].xml','_rels/.rels','xl/workbook.xml'}<=set(names)
                    or not any(re.fullmatch(r'xl/worksheets/sheet[0-9]+\.xml',n) for n in names)
                    or sum(m.file_size for m in members)>32*1024*1024):
                raise ValueError()
            total=0
            for member in members:
                deadline_check(deadline)
                name=member.filename
                if (name.startswith('/') or '\\' in name or '..' in Path(name).parts
                        or member.flag_bits&1 or name.lower().endswith('vbaproject.bin')
                        or member.file_size>max(1,member.compress_size)*200): raise ValueError()
                with archive.open(member) as stream:
                    while True:
                        deadline_check(deadline)
                        block=stream.read(65536)
                        deadline_check(deadline)
                        if not block: break
                        total+=len(block)
                        if total>32*1024*1024: raise ValueError()
    except (zipfile.BadZipFile,NotImplementedError,RuntimeError,ValueError,EOFError):
        raise RefreshError('source-xlsx-invalid') from None


def capacity(path):
    value = os.statvfs(path)
    return value.f_bavail * value.f_frsize


def reserve(path, cache, deadline, *, expected_bytes=None, max_bytes=None):
    expected_bytes = EXPECTED_BYTES if expected_bytes is None else expected_bytes
    max_bytes = MAX_BYTES if max_bytes is None else max_bytes
    deadline_check(deadline)
    if capacity(cache) < GUARD + max_bytes + expected_bytes:
        raise RefreshError('capacity-planning-bound-not-protected')
    try:
        fd = os.open(safe_path(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        raise RefreshError('reservation-already-present') from None
    try:
        if not hasattr(os, 'posix_fallocate'):
            raise RefreshError('physical-reservation-unavailable')
        os.posix_fallocate(fd, 0, expected_bytes)
        os.fsync(fd)
        info = os.fstat(fd)
        if info.st_size != expected_bytes or info.st_blocks * 512 < expected_bytes:
            raise RefreshError('physical-reservation-insufficient')
        if capacity(cache) < GUARD + max_bytes:
            raise RefreshError('capacity-planning-bound-not-protected')
        deadline_check(deadline)
        return fd, (info.st_dev, info.st_ino)
    except BaseException:
        info = os.fstat(fd)
        os.close(fd)
        current = path.stat()
        if (current.st_dev, current.st_ino) == (info.st_dev, info.st_ino):
            path.unlink()
        raise


def release_own_reservation(path, fd, identity):
    os.close(fd)
    info = safe_path(path).stat()
    if (info.st_dev, info.st_ino) != identity:
        raise RefreshError('reservation-already-present')
    path.unlink()


def run_selected(selected, *, engine=CachedAcquirer, transport=None, deadline=None):
    contract = source_contract(selected)
    source_key, source_url, fingerprint = contract['key'], contract['url'], contract['fingerprint']
    maximum, reservation_bytes, seconds = contract['maxBytes'], contract['expectedBytes'] or contract['maxBytes'], contract['seconds']
    deadline = min(deadline if deadline is not None else float('inf'), time.monotonic() + seconds)
    root = owned_directory(OUTPUT)
    work = owned_directory(root / 'collection', create=True)
    cache = owned_directory(work / 'source-cache', create=True)
    claims = owned_directory(work / 'intents', create=True)
    if root.stat().st_dev != cache.stat().st_dev:
        raise RefreshError('output-filesystem-mismatch')
    spec = source_spec(selected)
    key = sha(canonical(spec.identity()))
    current = cache / 'requests' / key / 'current.json'
    claim_path = claims / (sha(source_url.encode()) + '.json')
    reservation = work / ('reservation-' + sha(source_url.encode()) + '.bin')
    meter = {'requests': 0, 'bodyBytesRead': 0}
    report = {'schemaVersion': 'offmenu-fixed-original-detail/1', 'sourceKey': source_key,
        'selectionSHA256': fingerprint, 'scope': 'global-private-original-custody',
        'status': 'blocked', 'errorCode': None, 'cacheStatus': None, 'validation': None,
        'network': meter, 'responseMetadata': None, 'capacity': {'planningGuardBytes': GUARD, 'floorAlreadyIncluded': True,
            'sourceReservationBytes': reservation_bytes, 'physicalReservationEstablished': False},
        'downstreamHolds': selected['downstreamHolds'], 'claimCoverage': None,
        'claimFailureStatePersisted': None, 'receiptPersistence': 'pending', **SAFETY}

    class CountedResponse:
        def __init__(self, response, normalized):
            self.response = response
            self.status, self.headers = response.status, response.headers
            length = normalized.get('content-length', '')
            self.framed_length = int(length) if length.isdigit() and 'transfer-encoding' not in normalized else None
        def read(self, size):
            deadline_check(deadline)
            remaining = maximum - meter['bodyBytesRead']
            if remaining <= 0:
                # HTTP Content-Length ends this body exactly; never read an extra byte.
                # Real HTTPSFileTransport exposes the stdlib framing state as well.
                framed = getattr(self.response, 'response', None)
                if (self.framed_length == meter['bodyBytesRead']
                        and (framed is None or (getattr(framed, 'length', None) == 0
                                              and not getattr(framed, 'chunked', True)))):
                    return b''
                raise RefreshError('network-byte-limit')
            block = self.response.read(min(size, remaining))
            meter['bodyBytesRead'] += len(block)
            deadline_check(deadline)
            if meter['bodyBytesRead'] > maximum:
                raise RefreshError('network-byte-limit')
            return block
        def close(self):
            self.response.close()

    def counted(source, headers):
        if meter['requests']:
            raise RefreshError('network-request-limit')
        if source.identity() != spec.identity() or headers != {'Accept-Encoding': 'identity'}:
            raise RefreshError('request-contract-mismatch')
        deadline_check(deadline)
        meter['requests'] += 1
        response = (transport(source, headers, deadline=deadline) if transport is not None
                    else HTTPSFileTransport()(source, headers, deadline=deadline))
        report['responseMetadata'] = response_metadata(response.status, response.headers, request_url=source_url)
        try:
            headers_seen = _headers(response.headers)
            expected=selected.get('expectedResponse')
            if expected is not None and response.status == 200:
                actual={key:headers_seen.get(key) for key in expected}
                if actual != expected or 'transfer-encoding' in headers_seen:
                    raise RefreshError('source-response-contract-changed')
        except (RefreshError,ValueError,TypeError):
            response.close()
            raise
        return CountedResponse(response, headers_seen)

    acquirer = engine(cache, {source_key: spec}, transport=counted, retries=0,
        resource_budget=ResourceBudget(cache, maximum, minimum_free_bytes=GUARD, max_seconds=seconds))
    claimed, reservation_fd, reservation_identity = False, None, None
    with writer_lock(work / 'fixed-selection.lock'):
        try:
            report['claimCoverage'] = inspect_runner_metadata((LEGACY_CACHE, work), selected, current, claim_path, deadline)
            if reservation.exists():
                raise RefreshError('reservation-already-present')
            if (current.parent / 'body.partial').exists() or (current.parent / 'recovery.json').exists():
                raise RefreshError('source-partial-or-recovery-present')
            claim = None
            if claim_path.exists():
                claim, _ = read_metadata(claim_path)
                if (not isinstance(claim,dict) or set(claim) != {'schemaVersion','sourceKey','selectionSHA256','requestIdentitySHA256',
                                   'url','owner','state','sha256','bytes','originalAcquiredAt'}
                        or claim.get('schemaVersion') != 'offmenu-fixed-source-intent/1'
                        or type(claim.get('owner')) is not int or claim['owner'] != 0 or claim.get('url') != source_url
                        or claim.get('selectionSHA256') != fingerprint or claim.get('sourceKey') != source_key
                        or claim.get('requestIdentitySHA256') != key or claim.get('state') != 'verified'):
                    raise RefreshError('source-claim-uncertain')
            if claim is None:
                # Claim both reuse and a possible first GET before any cache action.
                # A failed/interrupted intent is never silently cleared for another GET.
                intent = {'schemaVersion': 'offmenu-fixed-source-intent/1', 'sourceKey': source_key,
                    'selectionSHA256': fingerprint, 'requestIdentitySHA256': key,
                    'url': source_url, 'owner': 0, 'state': 'acquiring'}
                fd = os.open(safe_path(claim_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(canonical(intent)); stream.flush(); os.fsync(stream.fileno())
                claimed = True
            try:
                result = acquirer.acquire(source_key, fetch_policy='reuse', deadline=deadline)
            except RefreshError as error:
                if str(error) != 'cache-missing' or claim is not None:
                    raise
                report['capacity']['availableBeforeReservationBytes'] = capacity(cache)
                reservation_fd, reservation_identity = reserve(reservation, cache, deadline, expected_bytes=reservation_bytes, max_bytes=maximum)
                report['capacity']['physicalReservationEstablished'] = True
                report['capacity']['availableAfterReservationBytes'] = capacity(cache)
                result = acquirer.acquire(source_key, fetch_policy='refresh', deadline=deadline)
            if claim is not None and (claim['sha256'] != result.sha256 or claim['bytes'] != result.bytes
                    or claim['originalAcquiredAt'] != result.provenance['originalAcquiredAt']):
                raise RefreshError('source-claim-uncertain')
            report['cacheStatus'] = result.status
            report['validation'] = validate_original(result, selected, deadline)
            deadline_check(deadline)
            atomic_json(claim_path, {'schemaVersion': 'offmenu-fixed-source-intent/1',
                'sourceKey': source_key, 'selectionSHA256': fingerprint,
                'requestIdentitySHA256': key, 'url': source_url, 'owner': 0, 'state': 'verified',
                'sha256': result.sha256, 'bytes': result.bytes,
                'originalAcquiredAt': result.provenance['originalAcquiredAt']})
            report['status'] = 'verified-private-original'
        except (RefreshError, OSError, ValueError, TypeError, KeyError, http.client.HTTPException) as error:
            code = str(error) if isinstance(error, RefreshError) and str(error) in ERRORS else (
                'local-io-failure' if isinstance(error, OSError) else 'collector-rejected')
            report['errorCode'] = code
            report['validation'] = None
            report['status'] = 'failed' if meter['requests'] else 'blocked'
            if claimed:
                try:
                    atomic_json(claim_path, {'schemaVersion': 'offmenu-fixed-source-intent/1',
                    'sourceKey': source_key, 'selectionSHA256': fingerprint,
                    'requestIdentitySHA256': key, 'url': source_url, 'owner': 0,
                    'state': 'failed-no-retry', 'errorCode': code, 'network': dict(meter)})
                    report['claimFailureStatePersisted'] = True
                except (OSError, ValueError, TypeError, KeyError):
                    report['claimFailureStatePersisted'] = False
                    report['errorCode'] = 'claim-state-write-failed'
        finally:
            if reservation_fd is not None:
                try:
                    release_own_reservation(reservation, reservation_fd, reservation_identity)
                except (OSError, ValueError, TypeError, KeyError):
                    report.update(status='failed' if meter['requests'] else 'blocked',
                                  errorCode='reservation-release-failed', validation=None)
        report['receiptPersistence'] = 'written'
        try:
            write_immutable(work / (('fixed-source-result-' if selected.get('schemaVersion') == 'offmenu-fixed-source-contract/1' else 'zenodo15169428-result-') + sha(canonical(report)) + '.json'), report)
        except (OSError, ValueError, TypeError, KeyError):
            report.update(status='failed' if meter['requests'] else 'blocked',
                          errorCode='result-write-failed', validation=None, receiptPersistence='failed')
    return report


def write_immutable(path, value):
    raw = canonical(value)
    path = safe_path(path)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.zenodo-receipt-', delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                if path.read_bytes() != raw:
                    raise RefreshError('fixed-evidence-invalid') from None
        finally:
            temporary.unlink(missing_ok=True)


def summary_report(detail=None, error=None):
    validation = (detail or {}).get('validation') or {}
    report = {'schemaVersion': SCHEMA, 'sourceKey': SOURCE_KEY,
        'status': 'blocked' if detail is None else detail['status'],
        'errorCode': error if detail is None else detail['errorCode'],
        'selectionSHA256': SELECTION_PIN[1], 'detailSHA256': None if detail is None else sha(canonical(detail)),
        'detailPersisted': bool(detail is not None and detail['receiptPersistence'] == 'written'),
        'responseMetadata': None if detail is None else detail.get('responseMetadata'),
        'networkRequests': 0 if detail is None else detail['network']['requests'],
        'networkBytesRead': 0 if detail is None else detail['network']['bodyBytesRead'],
        'verifiedBytes': validation.get('bytes', 0), 'originalSHA256': validation.get('sha256'),
        'publisherMD5Verified': validation.get('publisherMD5Verified', False),
        'headerVerified': validation.get('headerVerified', False),
        'minimumCacheSeconds': TTL, 'wholeOperationSeconds': MAX_SECONDS, **SAFETY}
    return sanitize_report(report)


def sanitize_report(value):
    if isinstance(value,dict) and value.get('schemaVersion') == DIAGNOSTIC_SCHEMA:
        return sanitize_diagnostic(value)
    keys = {'schemaVersion','sourceKey','status','errorCode','selectionSHA256','detailSHA256','detailPersisted','responseMetadata',
        'networkRequests','networkBytesRead','verifiedBytes','originalSHA256','publisherMD5Verified',
        'headerVerified','minimumCacheSeconds','wholeOperationSeconds'} | set(SAFETY)
    if (not isinstance(value, dict) or set(value) != keys or value['schemaVersion'] != SCHEMA
            or value['sourceKey'] != SOURCE_KEY or value['selectionSHA256'] != SELECTION_PIN[1]
            or value['status'] not in {'blocked', 'failed', 'verified-private-original'}
            or value['errorCode'] not in ERRORS | {None}):
        raise ValueError('invalid-summary')
    validate_response_metadata(value['responseMetadata'])
    if type(value['detailPersisted']) is not bool:
        raise ValueError('invalid-summary')
    success = value['status'] == 'verified-private-original'
    if success != (value['errorCode'] is None):
        raise ValueError('invalid-summary')
    for key in ('detailSHA256','originalSHA256'):
        if value[key] is not None and (not isinstance(value[key],str) or not re.fullmatch('[a-f0-9]{64}',value[key])):
            raise ValueError('invalid-summary')
    for key, limit in [('networkRequests',1),('networkBytesRead',MAX_BYTES),('verifiedBytes',EXPECTED_BYTES)]:
        if type(value[key]) is not int or not 0 <= value[key] <= limit:
            raise ValueError('invalid-summary')
    if (value['publisherMD5Verified'] is not success or value['headerVerified'] is not success
            or (success and (value['verifiedBytes'] != EXPECTED_BYTES or value['originalSHA256'] is None
                             or value['detailSHA256'] is None or not value['detailPersisted']))
            or (not success and (value['verifiedBytes'] != 0 or value['originalSHA256'] is not None))):
        raise ValueError('invalid-summary')
    for key, expected in SAFETY.items():
        if value[key] is not expected: raise ValueError('invalid-summary')
    for key, expected in [('minimumCacheSeconds',TTL),('wholeOperationSeconds',MAX_SECONDS)]:
        if type(value[key]) is not int or value[key] != expected: raise ValueError('invalid-summary')
    return dict(value)



def status_class(status):
    if status is None: return 'unavailable'
    if status in (401,403,407): return 'denial-or-auth-required'
    if status == 429: return 'rate-limited'
    return ('informational' if status < 200 else 'success' if status < 300 else
            'redirect' if status < 400 else 'client-error' if status < 500 else 'server-error')


def response_metadata(status, headers, *, request_url=URL):
    """Keep bounded response facts, never Location values, queries or parameters."""
    status = status if type(status) is int and 100 <= status <= 599 else None
    selected = {'content-type': [], 'content-length': [], 'location': []}
    for key, value in (headers.items() if isinstance(headers,dict) else headers):
        if isinstance(key,str) and key.lower() in selected:
            selected[key.lower()].append(value)
    def single(key):
        values=selected[key]
        return values[0] if len(values)==1 and isinstance(values[0],str) else None
    rawtype=single('content-type'); content_type=None
    if rawtype is not None:
        media=rawtype.split(';',1)[0].strip().lower()
        if len(media)<=127 and re.fullmatch(r'[a-z0-9!#$&^_.+-]+/[a-z0-9!#$&^_.+-]+',media):
            content_type=media
    rawlength=single('content-length'); length=None
    if rawlength is not None and len(rawlength)<=20 and re.fullmatch(r'[0-9]+',rawlength):
        candidate=int(rawlength)
        if candidate <= 2**63-1: length=candidate
    location={'present':bool(selected['location']),'classification':'absent',
              'sameRequestPath':None,'queryOrFragmentPresent':False}
    rawlocation=single('location')
    if selected['location']:
        location['classification']='invalid'
        if rawlocation is not None and len(rawlocation)<=2048 and not any(ord(c)<32 or ord(c)==127 for c in rawlocation):
            try:
                parsed=urlsplit(urljoin(request_url,rawlocation)); original=urlsplit(request_url)
                location['queryOrFragmentPresent']=bool(parsed.query or parsed.fragment)
                if parsed.username is None and parsed.password is None and parsed.hostname:
                    if parsed.scheme != 'https': location['classification']='non-https'
                    elif parsed.hostname.lower()==original.hostname and parsed.port in (None,443):
                        location['classification']='same-host'
                        location['sameRequestPath']=parsed.path==original.path
                    else: location['classification']='cross-host'
            except ValueError:
                pass
    return {'httpStatus':status,'httpStatusClass':status_class(status),
            'contentTypePresent':bool(selected['content-type']),'contentType':content_type,
            'contentLengthPresent':bool(selected['content-length']),'contentLength':length,
            'location':location,'duplicateMetadataHeaders':any(len(v)>1 for v in selected.values())}


def validate_response_metadata(value):
    if value is None: return
    keys={'httpStatus','httpStatusClass','contentTypePresent','contentType',
          'contentLengthPresent','contentLength','location','duplicateMetadataHeaders'}
    if not isinstance(value,dict) or set(value)!=keys: raise ValueError('invalid-response-metadata')
    status=value['httpStatus']
    if status is not None and (type(status) is not int or not 100<=status<=599): raise ValueError('invalid-response-metadata')
    if value['httpStatusClass']!=status_class(status): raise ValueError('invalid-response-metadata')
    media=value['contentType']
    if media is not None and (not isinstance(media,str) or len(media)>127 or not re.fullmatch(r'[a-z0-9!#$&^_.+-]+/[a-z0-9!#$&^_.+-]+',media)):
        raise ValueError('invalid-response-metadata')
    length=value['contentLength']
    if length is not None and (type(length) is not int or not 0<=length<=2**63-1): raise ValueError('invalid-response-metadata')
    for key in ('contentTypePresent','contentLengthPresent','duplicateMetadataHeaders'):
        if type(value[key]) is not bool: raise ValueError('invalid-response-metadata')
    loc=value['location']
    if (not isinstance(loc,dict) or set(loc)!={'present','classification','sameRequestPath','queryOrFragmentPresent'}
            or loc['classification'] not in {'absent','invalid','same-host','cross-host','non-https'}
            or type(loc['present']) is not bool or type(loc['queryOrFragmentPresent']) is not bool
            or (loc['sameRequestPath'] is not None and type(loc['sameRequestPath']) is not bool)):
        raise ValueError('invalid-response-metadata')


DIAGNOSTIC_ERRORS={None,'diagnostic-input-invalid','prior-failure-evidence-mismatch',
    'prior-intent-not-held','diagnostic-already-attempted','diagnostic-request-failed',
    'diagnostic-result-write-failed','diagnostic-deadline-exceeded'}
DIAGNOSTIC_FALSE={'sourceContentsRead':False,'sourceContentsUploaded':False,
    'sourceClaimsChanged':False,'originalGETRetried':False,'acquisitionEnabledByDiagnostic':False,
    'priorGETStatusRecovered':False,'priorGETCauseEstablished':False}


def diagnostic_report():
    return {'schemaVersion':DIAGNOSTIC_SCHEMA,'sourceKey':SOURCE_KEY,'method':'HEAD',
        'diagnosticSHA256':DIAGNOSTIC_PIN[1],'priorDetailSHA256':PRIOR_DETAIL_SHA256,
        'priorGETHttpStatus':None,'status':'blocked','errorCode':'diagnostic-input-invalid',
        'observedAt':datetime.now(timezone.utc).isoformat(),'networkRequests':0,'networkBodyBytesRead':0,
        'redirectsFollowed':0,'responseMetadata':None,'detailPersisted':False,
        'stopAfterResponse':True,'bodyChallengeNotInspected':True,**DIAGNOSTIC_FALSE}


def sanitize_diagnostic(value):
    if not isinstance(value,dict) or set(value)!=set(diagnostic_report()): raise ValueError('invalid-diagnostic')
    expected={'schemaVersion':DIAGNOSTIC_SCHEMA,'sourceKey':SOURCE_KEY,'method':'HEAD',
        'diagnosticSHA256':DIAGNOSTIC_PIN[1],'priorDetailSHA256':PRIOR_DETAIL_SHA256}
    if any(value[k]!=v for k,v in expected.items()): raise ValueError('invalid-diagnostic')
    if value['status'] not in {'observed','blocked','failed'} or value['errorCode'] not in DIAGNOSTIC_ERRORS:
        raise ValueError('invalid-diagnostic')
    if (value['status']=='observed')!=(value['errorCode'] is None): raise ValueError('invalid-diagnostic')
    if type(value['networkRequests']) is not int or not 0<=value['networkRequests']<=1: raise ValueError('invalid-diagnostic')
    for key in ('networkBodyBytesRead','redirectsFollowed'):
        if type(value[key]) is not int or value[key]!=0: raise ValueError('invalid-diagnostic')
    for key,expected in {**DIAGNOSTIC_FALSE,'stopAfterResponse':True,'bodyChallengeNotInspected':True}.items():
        if value[key] is not expected: raise ValueError('invalid-diagnostic')
    if value['priorGETHttpStatus'] is not None or type(value['detailPersisted']) is not bool:
        raise ValueError('invalid-diagnostic')
    if not isinstance(value['observedAt'],str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.]+\+00:00',value['observedAt']):
        raise ValueError('invalid-diagnostic')
    validate_response_metadata(value['responseMetadata'])
    if value['status']=='observed' and (value['responseMetadata'] is None or value['networkRequests']!=1):
        raise ValueError('invalid-diagnostic')
    return dict(value)


def run_diagnostic(*, connection_factory=None):
    """One prospective HEAD. Never read body, clear claims, or authorize a GET."""
    report=diagnostic_report(); connection=None; watchdog=None; response=None
    deadline=time.monotonic()+30
    try:
        prep=preparation_module()
        selected=strict_json(prep.pinned_bytes(ROOT,DIAGNOSTIC_PIN))
        if (selected.get('method')!='HEAD' or selected.get('url')!=URL
                or selected.get('headers')!={'Accept-Encoding':'identity'}
                or selected.get('maximumRequests')!=1 or selected.get('maximumBodyBytes')!=0
                or selected.get('priorGet',{}).get('detailSHA256')!=PRIOR_DETAIL_SHA256):
            raise RefreshError('diagnostic-input-invalid')
        work=owned_directory(owned_directory(OUTPUT)/'collection')
        with writer_lock(work/'fixed-selection.lock'):
            prior,_=read_metadata(work/('zenodo15169428-result-'+PRIOR_DETAIL_SHA256+'.json'),expected_sha256=PRIOR_DETAIL_SHA256)
            if (prior.get('sourceKey')!=SOURCE_KEY or prior.get('status')!='failed'
                    or prior.get('errorCode')!='source-response-not-permitted'
                    or prior.get('network')!={'requests':1,'bodyBytesRead':0}):
                raise RefreshError('prior-failure-evidence-mismatch')
            claim_path=work/'intents'/(sha(URL.encode())+'.json')
            claim,_=read_metadata(claim_path)
            if (claim.get('sourceKey')!=SOURCE_KEY or claim.get('state')!='failed-no-retry'
                    or claim.get('errorCode')!='source-response-not-permitted'):
                raise RefreshError('prior-intent-not-held')
            marker=safe_path(work/('zenodo-head-'+DIAGNOSTIC_PIN[1]+'.intent.json'))
            try:
                fd=os.open(marker,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            except FileExistsError:
                raise RefreshError('diagnostic-already-attempted') from None
            with os.fdopen(fd,'wb') as stream:
                stream.write(canonical({'diagnosticSHA256':DIAGNOSTIC_PIN[1],'method':'HEAD','maximumRequests':1}))
                stream.flush();os.fsync(stream.fileno())
            remaining=deadline-time.monotonic()
            if remaining<=0: raise RefreshError('diagnostic-deadline-exceeded')
            parts=urlsplit(URL)
            factory=connection_factory or http.client.HTTPSConnection
            connection=factory(parts.hostname,443,timeout=min(30,remaining),context=ssl.create_default_context())
            expired=threading.Event()
            def abort():
                expired.set()
                sock=connection.sock
                if sock is not None:
                    try: sock.shutdown(2)
                    except OSError: pass
                connection.close()
            watchdog=threading.Timer(remaining,abort);watchdog.daemon=True;watchdog.start()
            report['networkRequests']=1
            connection.request('HEAD',parts.path,headers={'Accept-Encoding':'identity'})
            response=connection.getresponse()
            report['responseMetadata']=response_metadata(response.status,response.getheaders())
            if expired.is_set() or time.monotonic()>=deadline:
                raise RefreshError('diagnostic-deadline-exceeded')
            report.update(status='observed',errorCode=None)
            # No response.read(), redirects, challenge parsing or acquisition call.
    except (RefreshError,OSError,ValueError,TypeError,KeyError,http.client.HTTPException) as error:
        code=str(error) if isinstance(error,RefreshError) and str(error) in DIAGNOSTIC_ERRORS else (
            'diagnostic-request-failed' if report['networkRequests'] else 'diagnostic-input-invalid')
        report.update(status='failed' if report['networkRequests'] else 'blocked',errorCode=code)
    finally:
        if watchdog is not None: watchdog.cancel()
        try:
            if response is not None: response.close()
            if connection is not None: connection.close()
        except (OSError,http.client.HTTPException):
            report.update(status='failed' if report['networkRequests'] else 'blocked',errorCode='diagnostic-request-failed')
    try:
        report['detailPersisted']=True
        work=owned_directory(owned_directory(OUTPUT)/'collection')
        write_immutable(work/('zenodo-head-result-'+sha(canonical(report))+'.json'),report)
    except (OSError,ValueError,TypeError,KeyError):
        report.update(status='failed' if report['networkRequests'] else 'blocked',
                      errorCode='diagnostic-result-write-failed',detailPersisted=False)
    return sanitize_diagnostic(report)

def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args == ['--response-metadata']:
        report = run_diagnostic()
        print(canonical(report).decode(), end='')
        return 0 if report['status'] == 'observed' else 2
    deadline = time.monotonic() + MAX_SECONDS
    try:
        if args:
            raise RefreshError('unexpected-arguments')
        selected = load_selection()
        deadline_check(deadline)
        report = summary_report(run_selected(selected, deadline=deadline))
    except (RefreshError, OSError, ValueError, TypeError, KeyError) as error:
        code = str(error) if isinstance(error, RefreshError) and str(error) in ERRORS else 'fixed-evidence-invalid'
        report = summary_report(error=code)
    print(canonical(report).decode(), end='')
    return 0 if report['status'] == 'verified-private-original' else 2


if __name__ == '__main__':
    raise SystemExit(main())
