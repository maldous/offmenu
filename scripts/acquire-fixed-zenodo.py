#!/usr/bin/env python3
"""One reviewed private original through the existing acquisition engine."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from offmenu.refresh.acquisition import CachedAcquirer, HTTPSFileTransport, ResourceBudget, SourceSpec
from offmenu.refresh.core import RefreshError, atomic_json, canonical, safe_path, sha, strict_json, writer_lock

OUTPUT = Path('/srv/offmenu-refresh/outputs')
LEGACY_CACHE = Path('/srv/offmenu-refresh/cache')
SELECTION_PIN = ('docs/collection-selections/zenodo15169428-selection.json',
                 'fc52fa57a04e389a5ec47509d8043477312bc4de2aae78267ca13a99c10b7bfd')
SCHEMA = 'offmenu-fixed-original-summary/1'
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
        if isinstance(item, list):
            return any(walk(x) for x in item)
        return False
    return walk(value)


def owned_directory(path, *, create=False):
    path = safe_path(path)
    if create:
        path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir() or path.stat().st_uid != os.getuid():
        raise RefreshError('output-root-unavailable')
    return path


def read_metadata(path):
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


def source_spec(selected):
    return SourceSpec(source_key=SOURCE_KEY, url=URL,
        policy_fingerprint=SELECTION_PIN[1], rights_reference=selected['rightsReference'],
        enabled=True, rights_approved=True, held=False, ttl_seconds=TTL,
        max_bytes=EXPECTED_BYTES, release=selected['release'])


def validate_original(result, selected, deadline):
    path = safe_path(result.path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    count, digest256, digestmd5 = 0, hashlib.sha256(), hashlib.md5(usedforsecurity=False)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size != EXPECTED_BYTES:
            raise RefreshError('source-length-mismatch')
        header = stream.readline(8193)
        if len(header) > 8192 or header.rstrip(b'\r\n') != ';'.join(selected['headerFields']).encode('utf-8'):
            raise RefreshError('source-header-mismatch')
        stream.seek(0)
        while True:
            deadline_check(deadline)
            block = stream.read(min(1024 * 1024, EXPECTED_BYTES - count + 1))
            deadline_check(deadline)
            if not block:
                break
            count += len(block)
            if count > EXPECTED_BYTES:
                raise RefreshError('source-length-mismatch')
            digest256.update(block)
            digestmd5.update(block)
        after = os.fstat(stream.fileno())
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if identity(before) != identity(after) or identity(after) != identity(path.stat()):
        raise RefreshError('source-changed-during-validation')
    if count != EXPECTED_BYTES or result.bytes != EXPECTED_BYTES:
        raise RefreshError('source-length-mismatch')
    if digestmd5.hexdigest() != EXPECTED_MD5:
        raise RefreshError('source-md5-mismatch')
    if digest256.hexdigest() != result.sha256:
        raise RefreshError('source-sha256-mismatch')
    return {'bytes': count, 'sha256': result.sha256, 'publisherMD5Verified': True,
            'headerVerified': True, 'originalAcquiredAt': result.provenance['originalAcquiredAt']}


def capacity(path):
    value = os.statvfs(path)
    return value.f_bavail * value.f_frsize


def reserve(path, cache, deadline):
    deadline_check(deadline)
    if capacity(cache) < GUARD + MAX_BYTES + EXPECTED_BYTES:
        raise RefreshError('capacity-planning-bound-not-protected')
    try:
        fd = os.open(safe_path(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        raise RefreshError('reservation-already-present') from None
    try:
        if not hasattr(os, 'posix_fallocate'):
            raise RefreshError('physical-reservation-unavailable')
        os.posix_fallocate(fd, 0, EXPECTED_BYTES)
        os.fsync(fd)
        info = os.fstat(fd)
        if info.st_size != EXPECTED_BYTES or info.st_blocks * 512 < EXPECTED_BYTES:
            raise RefreshError('physical-reservation-insufficient')
        if capacity(cache) < GUARD + MAX_BYTES:
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
    deadline = deadline if deadline is not None else time.monotonic() + MAX_SECONDS
    root = owned_directory(OUTPUT)
    work = owned_directory(root / 'collection', create=True)
    cache = owned_directory(work / 'source-cache', create=True)
    claims = owned_directory(work / 'intents', create=True)
    if root.stat().st_dev != cache.stat().st_dev:
        raise RefreshError('output-filesystem-mismatch')
    spec = source_spec(selected)
    key = sha(canonical(spec.identity()))
    current = cache / 'requests' / key / 'current.json'
    claim_path = claims / (sha(URL.encode()) + '.json')
    reservation = work / ('reservation-' + sha(URL.encode()) + '.bin')
    meter = {'requests': 0, 'bodyBytesRead': 0}
    report = {'schemaVersion': 'offmenu-fixed-original-detail/1', 'sourceKey': SOURCE_KEY,
        'selectionSHA256': SELECTION_PIN[1], 'scope': 'global-private-original-custody',
        'status': 'blocked', 'errorCode': None, 'cacheStatus': None, 'validation': None,
        'network': meter, 'capacity': {'planningGuardBytes': GUARD, 'floorAlreadyIncluded': True,
            'sourceReservationBytes': EXPECTED_BYTES, 'physicalReservationEstablished': False},
        'downstreamHolds': selected['downstreamHolds'], 'claimCoverage': None,
        'claimFailureStatePersisted': None, 'receiptPersistence': 'pending', **SAFETY}

    class CountedResponse:
        def __init__(self, response):
            self.response = response
            self.status, self.headers = response.status, response.headers
        def read(self, size):
            deadline_check(deadline)
            remaining = MAX_BYTES - meter['bodyBytesRead']
            if remaining <= 0:
                raise RefreshError('network-byte-limit')
            block = self.response.read(min(size, remaining))
            meter['bodyBytesRead'] += len(block)
            deadline_check(deadline)
            if meter['bodyBytesRead'] > MAX_BYTES:
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
        return CountedResponse(response)

    acquirer = engine(cache, {SOURCE_KEY: spec}, transport=counted, retries=0,
        resource_budget=ResourceBudget(cache, MAX_BYTES, minimum_free_bytes=GUARD, max_seconds=MAX_SECONDS))
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
                        or type(claim.get('owner')) is not int or claim['owner'] != 0 or claim.get('url') != URL
                        or claim.get('selectionSHA256') != SELECTION_PIN[1] or claim.get('sourceKey') != SOURCE_KEY
                        or claim.get('requestIdentitySHA256') != key or claim.get('state') != 'verified'):
                    raise RefreshError('source-claim-uncertain')
            if claim is None:
                # Claim both reuse and a possible first GET before any cache action.
                # A failed/interrupted intent is never silently cleared for another GET.
                intent = {'schemaVersion': 'offmenu-fixed-source-intent/1', 'sourceKey': SOURCE_KEY,
                    'selectionSHA256': SELECTION_PIN[1], 'requestIdentitySHA256': key,
                    'url': URL, 'owner': 0, 'state': 'acquiring'}
                fd = os.open(safe_path(claim_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(canonical(intent)); stream.flush(); os.fsync(stream.fileno())
                claimed = True
            try:
                result = acquirer.acquire(SOURCE_KEY, fetch_policy='reuse', deadline=deadline)
            except RefreshError as error:
                if str(error) != 'cache-missing' or claim is not None:
                    raise
                report['capacity']['availableBeforeReservationBytes'] = capacity(cache)
                reservation_fd, reservation_identity = reserve(reservation, cache, deadline)
                report['capacity']['physicalReservationEstablished'] = True
                report['capacity']['availableAfterReservationBytes'] = capacity(cache)
                result = acquirer.acquire(SOURCE_KEY, fetch_policy='refresh', deadline=deadline)
            if claim is not None and (claim['sha256'] != result.sha256 or claim['bytes'] != result.bytes
                    or claim['originalAcquiredAt'] != result.provenance['originalAcquiredAt']):
                raise RefreshError('source-claim-uncertain')
            report['cacheStatus'] = result.status
            report['validation'] = validate_original(result, selected, deadline)
            deadline_check(deadline)
            atomic_json(claim_path, {'schemaVersion': 'offmenu-fixed-source-intent/1',
                'sourceKey': SOURCE_KEY, 'selectionSHA256': SELECTION_PIN[1],
                'requestIdentitySHA256': key, 'url': URL, 'owner': 0, 'state': 'verified',
                'sha256': result.sha256, 'bytes': result.bytes,
                'originalAcquiredAt': result.provenance['originalAcquiredAt']})
            report['status'] = 'verified-private-original'
        except (RefreshError, OSError, ValueError, TypeError, KeyError) as error:
            code = str(error) if isinstance(error, RefreshError) and str(error) in ERRORS else (
                'local-io-failure' if isinstance(error, OSError) else 'collector-rejected')
            report['errorCode'] = code
            report['validation'] = None
            report['status'] = 'failed' if meter['requests'] else 'blocked'
            if claimed:
                try:
                    atomic_json(claim_path, {'schemaVersion': 'offmenu-fixed-source-intent/1',
                    'sourceKey': SOURCE_KEY, 'selectionSHA256': SELECTION_PIN[1],
                    'requestIdentitySHA256': key, 'url': URL, 'owner': 0,
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
            write_immutable(work / ('zenodo15169428-result-' + sha(canonical(report)) + '.json'), report)
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
        'networkRequests': 0 if detail is None else detail['network']['requests'],
        'networkBytesRead': 0 if detail is None else detail['network']['bodyBytesRead'],
        'verifiedBytes': validation.get('bytes', 0), 'originalSHA256': validation.get('sha256'),
        'publisherMD5Verified': validation.get('publisherMD5Verified', False),
        'headerVerified': validation.get('headerVerified', False),
        'minimumCacheSeconds': TTL, 'wholeOperationSeconds': MAX_SECONDS, **SAFETY}
    return sanitize_report(report)


def sanitize_report(value):
    keys = {'schemaVersion','sourceKey','status','errorCode','selectionSHA256','detailSHA256','detailPersisted',
        'networkRequests','networkBytesRead','verifiedBytes','originalSHA256','publisherMD5Verified',
        'headerVerified','minimumCacheSeconds','wholeOperationSeconds'} | set(SAFETY)
    if (not isinstance(value, dict) or set(value) != keys or value['schemaVersion'] != SCHEMA
            or value['sourceKey'] != SOURCE_KEY or value['selectionSHA256'] != SELECTION_PIN[1]
            or value['status'] not in {'blocked', 'failed', 'verified-private-original'}
            or value['errorCode'] not in ERRORS | {None}):
        raise ValueError('invalid-summary')
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


def main(argv=None):
    deadline = time.monotonic() + MAX_SECONDS
    try:
        if (sys.argv[1:] if argv is None else argv):
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
