"""BB/JO/PY receipt-metadata proposals; no raw-source parser or admission.

Reviewed portfolio configuration is separate from SourceContract authority.
Only exact receipt files are read by the CLI. No URL, original path, force flag,
code plugin, or acquisition API is accepted. All retained sources stay held.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import stat
import sys

from .core import RefreshError, canonical, sha, strict_json, timestamp, verify, safe_path
from .field_provenance import datum_pointers, field_origin_errors
from .serialization import encode_records
from .portfolio05_sources import CONFIGURATION

MAX_RECEIPT = 65536
MAX_PREVIOUS = 1024 * 1024
FIELDS = ('release', 'documentRole', 'acquisitionBasis')


def pointer(document, locator):
    if not isinstance(locator, str) or not locator.startswith('/'):
        raise RefreshError('metadata-selector-invalid')
    value = document
    for part in locator.split('/')[1:]:
        key = part.replace('~1', '/').replace('~0', '~')
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def configuration():
    """Owned packaged code declarations; no metadata/resource file read."""
    return copy.deepcopy(CONFIGURATION)


def bind(spec, payload, *, now, previous_candidate_sha256=None):
    """Pure proposal from supplied receipt bytes. No files, clock, or network.

    Production callers use only reviewed configuration() entries. Even a valid
    metadata proposal grants no source-body operation or acceptance. Test specs
    are authored in test code, not user inputs turned into trusted contracts.
    """
    result = {'sourceId': spec['sourceId'], 'country': spec['country'],
              'status': 'missing', 'diagnostics': [], 'candidate': None,
              'candidateSha256': None, 'unchangedContentNoOp': False,
              'sourceBodyRead': False, 'networkRequests': 0,
              'sourceOperationsAuthorized': [], 'acceptance': 'not-requested',
              'applicability': spec['applicability'], 'cache': None}
    if payload is None:
        result['diagnostics'] = ['metadata-input-missing']
        return result
    try:
        if not isinstance(payload, bytes) or len(payload) > MAX_RECEIPT:
            raise RefreshError('metadata-input-bound')
        if sha(payload) != spec['receipt']['sha256']:
            raise RefreshError('metadata-pin-mismatch')
        document = strict_json(payload)
        if not isinstance(document, dict) or pointer(document, '/country') != spec['country']:
            raise RefreshError('metadata-country-mismatch')
        now_time = timestamp(now)
        acquired = pointer(document, spec['acquisitionPointer'])
        acquired_time = timestamp(acquired)
        validated = pointer(document, spec['validationPointer'])
        if not acquired_time <= timestamp(validated) <= now_time:
            raise RefreshError('metadata-time-order-invalid')
        values = {field: pointer(document, spec['fields'][field]) for field in FIELDS}
        if any(not isinstance(value, str) or not value for value in values.values()):
            raise RefreshError('metadata-field-invalid')
        # Only timestamp observations, no copied or source-spoofed cache planner.
        # abec has no generic pure planner. Do not call the Wikibooks/fixture
        # planners or operational CachedAcquirer for these held sources.
        result['cache'] = {'minimumReuseDaysRequired': 30,
                          'acquisitionAgeDays': int((now_time - acquired_time).total_seconds() // 86400),
                          'decision': 'unsupported-real-source-cache-planner',
                          'freshness': 'unknown', 'mtimeUsedForFreshness': False,
                          'assetBytesVerifiedByThisPlan': False}
        result['cache'].update(originalAcquisitionObservedAt=acquired,
                               acquisitionTimestampMeaning=spec['acquisitionMeaning'],
                               validationObservedAt=validated,
                               validationResetsAcquisitionAge=False,
                               sourceBodyCacheVerified=False,
                               conditionalDownloadEnabled=False)
        release = values['release']
        policy_sha = sha(canonical(spec))
        path = 'metadata/receipt.json'
        data = {**values, 'country': spec['country'],
                'originalAcquisitionObservedAt': acquired,
                'validationObservedAt': validated,
                'nativeUnit': None, 'nativeBasis': None,
                'measurementStatus': 'not-a-measurement-record'}
        selectors = {**spec['fields'], 'country': '/country',
                     'originalAcquisitionObservedAt': spec['acquisitionPointer'],
                     'validationObservedAt': spec['validationPointer']}
        origins = {}
        for field in data:
            if field in selectors:
                origins['/data/' + field] = {
                    'kind': 'source', 'sourceId': spec['sourceId'], 'releaseId': release,
                    'inputPath': path, 'inputSha256': spec['receipt']['sha256'],
                    'sourceRecordId': spec['sourceId'], 'sourceField': selectors[field]}
            else:
                origins['/data/' + field] = {'kind': 'constant', 'policySha256': policy_sha,
                                            'symbol': 'metadata-only-' + field}
        row = {'schemaVersion': '1.0', 'id': spec['sourceId'] + ':receipt-metadata',
               'kind': 'document-reference-metadata', 'data': data,
               'provenance': {'sourceId': spec['sourceId'], 'releaseId': release,
                              'fetchedAt': acquired, 'fieldOrigins': origins,
                              'metadataReceiptSha256': spec['receipt']['sha256'],
                              'policySha256': policy_sha, 'authorizedOperations': []}}
        errors = field_origin_errors(row, {path: spec['receipt']['sha256']}, policy_pins=(policy_sha,))
        # Shared validator checks coverage/pins. Check actual source value and
        # selector semantics here; a coordinate string alone proves neither.
        for field, selector in selectors.items():
            if data[field] != pointer(document, selector):
                errors.append('metadata-field-origin-value-mismatch')
        if set(origins) != set(datum_pointers(data)):
            errors.append('metadata-field-origin-coverage')
        if errors:
            raise RefreshError(sorted(errors)[0])
        encoded = encode_records([row])
        result.update(candidate=row, candidateSha256=sha(encoded),
                      unchangedContentNoOp=sha(encoded) == previous_candidate_sha256,
                      inputFiles=[{'path': path, 'bytes': len(payload),
                                   'sha256': spec['receipt']['sha256']}],
                      releaseId=release, acquiredAt=acquired,
                      policySha256=policy_sha, fieldOriginErrors=[])
        if spec['holds']:
            result.update(status='held', diagnostics=sorted(spec['holds']))
        elif previous_candidate_sha256 is not None and sha(encoded) != previous_candidate_sha256:
            result.update(status='stale', diagnostics=['previous-metadata-candidate-stale'])
        else:
            result['status'] = 'valid'
    except (KeyError, IndexError):
        result.update(status='missing', diagnostics=['metadata-selector-missing'])
    except (ValueError, TypeError, AttributeError, OverflowError) as error:
        code = str(error) if isinstance(error, RefreshError) else 'metadata-malformed'
        result.update(status='malformed', diagnostics=[code], candidate=None)
    return result


def inspect_portfolio(*, now, previous=None):
    """Independent fixed diagnostics; one failing receipt cannot abort siblings.

    Reads exact allowlisted metadata only, bounded before/after pin verification.
    Original paths in receipts are never opened, stat-ed, imported or followed.
    """
    config = configuration()
    rows = []
    for spec in config['sources']:
        try:
            path = safe_path(spec['receipt']['path'])
            if not path.exists():
                payload = None
            else:
                actual = verify(path, {'bytes': spec['receipt']['bytes'],
                                       'sha256': spec['receipt']['sha256']})
                if actual['bytes'] > MAX_RECEIPT:
                    raise RefreshError('metadata-input-bound')
                payload = path.read_bytes()
                verify(path, actual)
            rows.append(bind(spec, payload, now=now,
                             previous_candidate_sha256=(previous or {}).get(spec['sourceId'])))
        except (OSError, ValueError):
            rows.append({'sourceId': spec['sourceId'], 'country': spec['country'],
                         'status': 'malformed', 'diagnostics': ['metadata-file-unavailable-or-pin-mismatch'],
                         'candidate': None, 'networkRequests': 0})
    return {'schemaVersion': 'offmenu-portfolio05-binding/1',
            'scope': 'receipt-metadata-proposals-only', 'sources': rows,
            'sourceBodiesRead': 0, 'networkRequests': 0, 'goldAdmitted': 0,
            'countryAcceptance': False, 'evidencePins': config['evidencePins']}


def previous_candidates(path):
    """Read an optional report without following links or blocking on a FIFO.

    Owned entrypoint repair only. No raw source/cache/acceptance operations.
    Validate the opened descriptor, not just a path inspected before open.
    """
    directory = descriptor = None
    try:
        path = safe_path(path)
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
        directory = os.open(path.anchor, flags | os.O_DIRECTORY)
        for part in path.parts[1:-1]:
            child = os.open(part, flags | os.O_DIRECTORY, dir_fd=directory)
            os.close(directory)
            directory = child
        descriptor = os.open(path.name, flags | os.O_NONBLOCK, dir_fd=directory)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise RefreshError('previous-report-regular-file-required')
        if before.st_size > MAX_PREVIOUS:
            raise RefreshError('previous-report-bound')
        with os.fdopen(descriptor, 'rb') as stream:
            descriptor = None
            raw = stream.read(MAX_PREVIOUS + 1)
            after = os.fstat(stream.fileno())
        identity = lambda st: (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
        if identity(before) != identity(after) or len(raw) != before.st_size:
            raise RefreshError('previous-report-changed-during-read')
        if len(raw) > MAX_PREVIOUS:
            raise RefreshError('previous-report-bound')
        report = strict_json(raw)
        if not isinstance(report, dict) or not isinstance(report.get('sources'), list):
            raise RefreshError('previous-report-malformed')
        result = {}
        for row in report['sources']:
            if not isinstance(row, dict) or not isinstance(row.get('sourceId'), str):
                raise RefreshError('previous-report-malformed')
            key, digest = row['sourceId'], row.get('candidateSha256')
            if not key or key in result or (digest is not None and
                    (not isinstance(digest, str) or len(digest) != 64 or
                     any(c not in '0123456789abcdef' for c in digest))):
                raise RefreshError('previous-report-malformed')
            result[key] = digest
        return result
    except RefreshError:
        raise
    except OSError:
        raise RefreshError('previous-report-file-unavailable') from None
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        raise RefreshError('previous-report-malformed') from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory is not None:
            os.close(directory)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--now', required=True, help='Explicit UTC evaluation time; never refreshes acquisition age')
    parser.add_argument('--previous', type=Path, help='Prior metadata diagnostic report for content no-op comparison')
    args = parser.parse_args(argv)
    timestamp(args.now)
    previous = {}
    if args.previous:
        try:
            previous = previous_candidates(args.previous)
        except RefreshError as error:
            print(canonical({'status': 'failed', 'diagnostics': [str(error)],
                             'sourceBodiesRead': 0, 'networkRequests': 0}).decode(),
                  file=sys.stderr, end='')
            return 2
    print(canonical(inspect_portfolio(now=args.now, previous=previous)).decode(), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
