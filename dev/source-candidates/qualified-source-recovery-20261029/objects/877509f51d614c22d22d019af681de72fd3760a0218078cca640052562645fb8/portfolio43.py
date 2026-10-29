"""Worker43 metadata bindings; never reads assets named by provenance pins.

This is not a parser, SourceContract factory, acquisition registry or admission.
Shared field-origin validation, serialization, cache bounds and StageResult are
reused. A passing result means only the small binding document is consistent.
"""
import argparse
from datetime import timedelta
import errno
import os
from pathlib import Path
import re
import stat
import sys

from .refresh.acquisition import MIN_TTL, SourceSpec
from .refresh.core import RefreshError, canonical, sha, strict_json, timestamp
from .refresh.field_provenance import field_origin_errors
from .refresh.global_run import StageResult

CONFIG = Path(__file__).resolve().parents[1] / 'config/portfolio43.json'
MAX_METADATA = 262144
UNKNOWN_POLICY = sha(canonical({'policy': 'worker43-explicit-unknown', 'version': 1}))
DIGEST = re.compile(r'[0-9a-f]{64}')
KEY = re.compile(r'[a-z][a-z0-9-]{0,63}')
COUNTRIES = ('BZ', 'FJ', 'RO', 'SR')
TYPES = ('ingredients', 'recipes', 'nutrition', 'retailers/providers',
         'prices/baskets', 'dietary references')


def read_metadata(path):
    """Only the explicitly selected small metadata document is opened."""
    parts = Path(os.path.abspath(path)).parts
    parent = descriptor = None
    try:
        # Walk anchored directory descriptors, never verify a pathname and then
        # reopen it. NOFOLLOW also applies if a component is replaced mid-walk.
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        parent = os.open(parts[0], directory_flags)
        for name in parts[1:-1]:
            child = os.open(name, directory_flags, dir_fd=parent)
            os.close(parent)
            parent = child
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NONBLOCK |
                             os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise RefreshError('metadata-regular-file-required')
        if before.st_size > MAX_METADATA:
            raise RefreshError('metadata-size-limit')
        chunks, remaining = [], MAX_METADATA + 1
        while remaining:
            block = os.read(descriptor, remaining)
            if not block:
                break
            chunks.append(block)
            remaining -= len(block)
        raw = b''.join(chunks)
        after = os.fstat(descriptor)
        if len(raw) > MAX_METADATA:
            raise RefreshError('metadata-size-limit')
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if identity(before) != identity(after) or len(raw) != before.st_size:
            raise RefreshError('metadata-changed-during-read')
    except OSError as error:
        if error.errno in (errno.ELOOP, errno.ENOTDIR):
            raise RefreshError('metadata-path-invalid') from None
        raise
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if parent is not None:
            os.close(parent)
    return strict_json(raw)


def declaration(spec):
    """Compile known metadata fields; explicit nulls have code-policy origins."""
    data = {k: v['value'] for k, v in spec['fields'].items()}
    origins = {}
    for name, field in spec['fields'].items():
        origins['/data/' + name] = (
            {'kind': 'source', 'sourceId': spec['sourceId'],
             'releaseId': spec['releaseId'], 'inputPath': 'manifest.json',
             'inputSha256': spec['manifest']['sha256'],
             'sourceRecordId': field['record'], 'sourceField': field['selector']}
            if field.get('selector') else
            {'kind': 'constant', 'policySha256': UNKNOWN_POLICY,
             'symbol': field['constant']})
    return {'data': data, 'provenance': {'sourceId': spec['sourceId'],
            'releaseId': spec['releaseId'], 'fieldOrigins': origins}}


def disabled_acquisition_spec(spec):
    """Integration descriptor only. validate() MUST refuse every real source."""
    return SourceSpec(source_key=spec['key'], url=spec['publisherURL'],
                      policy_fingerprint=sha(canonical(spec)),
                      rights_reference=spec['manifest']['sha256'],
                      enabled=False, rights_approved=False, held=True,
                      release=spec['releaseId'], ttl_seconds=MIN_TTL)


def assess(spec, evidence, *, now, previous_key=None):
    """Pure metadata preflight. No asset access, transport, writes or AI."""
    result = {'key': spec.get('key'), 'status': 'malformed', 'diagnostics': [],
              'staging': 'not-executed', 'sourceAcceptance': None,
              'countryComplete': False, 'networkRequests': 0,
              'assetBytesVerified': False, 'metadataKey': None,
              'holds': list(spec.get('holds', [])),
              'minimumReuseDays': MIN_TTL // 86400,
              'originalAcquisitionAgeDays': None, 'validationAgeDays': None,
              'cacheDecision': 'no-download', 'replay': 'not-ready'}
    errors = set()
    try:
        if (not KEY.fullmatch(spec['key']) or not spec['sourceId']
                or not spec['releaseId'] or not DIGEST.fullmatch(spec['manifest']['sha256'])
                or not isinstance(spec['holds'], list)):
            raise ValueError()
        clock = timestamp(now)
        result['declaredRecord'] = declaration(spec)
        if evidence is None:
            result.update(status='missing', diagnostics=['metadata-evidence-missing'])
            return result
        if (not isinstance(evidence, dict) or set(evidence) != {
                'schemaVersion', 'manifestSha256', 'originalAcquiredAt',
                'validatedAt', 'declaration'} or evidence['schemaVersion'] != 'worker43-evidence/1'):
            raise ValueError()
        if evidence['manifestSha256'] != spec['manifest']['sha256']:
            errors.add('manifest-pin-mismatch')
        if evidence['declaration'] != result['declaredRecord']:
            errors.add('field-declaration-mismatch')
        errors.update(field_origin_errors(evidence['declaration'],
                      {'manifest.json': spec['manifest']['sha256']},
                      policy_pins=(UNKNOWN_POLICY,)))
        acquired_value = evidence['originalAcquiredAt']
        if acquired_value != spec['originalAcquiredAt']:
            errors.add('original-acquisition-binding-mismatch')
        if acquired_value is None:
            errors.add('original-acquisition-time-unknown')
            acquired = None
        else:
            acquired = timestamp(acquired_value)
        validated = timestamp(evidence['validatedAt'])
        if validated > clock or (acquired and not acquired <= validated <= clock):
            errors.add('metadata-time-order-invalid')
        result['validationAgeDays'] = (clock - validated).days
        if acquired:
            result['originalAcquisitionAgeDays'] = (clock - acquired).days
            result['cacheDecision'] = ('under-30-days-zero-download' if
                clock - acquired < timedelta(seconds=MIN_TTL) else
                'stale-review-required-no-download')
        # Content identity deliberately excludes clock and validation time.
        result['metadataKey'] = sha(canonical({
            'sourceId': spec['sourceId'], 'releaseId': spec['releaseId'],
            'manifest': spec['manifest'], 'declaration': result['declaredRecord'],
            'originalAcquiredAt': acquired_value, 'holds': spec['holds']}))
        if errors:
            result['status'] = 'missing' if errors == {'original-acquisition-time-unknown'} else 'malformed'
        elif spec['holds']:
            result['status'] = 'held'
            errors.add('source-operation-held')
        elif result['cacheDecision'] == 'stale-review-required-no-download':
            result['status'] = 'stale'
            errors.add('stale-input-review-required')
        else:
            result['status'] = 'valid-metadata'
            result['replay'] = 'no-op' if previous_key == result['metadataKey'] else 'binding-ready'
        result['diagnostics'] = sorted(errors)
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError):
        result.update(status='malformed', diagnostics=['metadata-contract-invalid'])
    return result


def stage_result(result):
    """Shared typed interface for the metadata check, never accept-stage wiring."""
    status = {'valid-metadata': 'succeeded', 'held': 'held', 'malformed': 'failed',
              'missing': 'unsupported', 'stale': 'unsupported'}[result['status']]
    code = 'metadata-binding-only' if status == 'succeeded' else 'metadata-' + result['status']
    return StageResult(status, code, (sha(canonical(result)),)).receipt()


def assess_portfolio(specs, evidence, *, now, previous_keys=None):
    """Bad/missing peers cannot suppress independent source diagnostics."""
    rows = []
    previous_keys = {} if previous_keys is None else previous_keys
    if (not isinstance(previous_keys, dict) or any(
            not isinstance(k, str) or not KEY.fullmatch(k)
            or not isinstance(v, str) or not DIGEST.fullmatch(v)
            for k, v in previous_keys.items())):
        raise RefreshError('previous-keys-invalid')
    for spec in sorted(specs, key=lambda s: s['key']):
        value = evidence.get(spec['key'])
        row = assess(spec, value, now=now, previous_key=previous_keys.get(spec['key']))
        row['interface'] = stage_result(row)
        row['countries'] = spec['countries']
        row['types'] = spec['types']
        row['manifest'] = spec['manifest']
        row['adapterBinding'] = spec.get('adapterBinding')
        rows.append(row)
    cells = [{'country': country, 'type': kind,
              'metadataBindings': [r['key'] for r in rows
                                   if country in r['countries'] and kind in r['types']],
              'accepted': False}
             for country in COUNTRIES for kind in TYPES]
    return {'schemaVersion': 'worker43-metadata-plan/1', 'sources': rows,
            'countryTypeBindings': cells,
            'datasetProcessing': False, 'acceptedRecords': 0, 'goldAdmissions': 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-directory', required=True)
    parser.add_argument('--now', required=True, help='Explicit UTC clock, not filesystem mtime')
    parser.add_argument('--previous-keys', help='Small metadata key map for replay comparison')
    args = parser.parse_args(argv)
    try:
        config = read_metadata(CONFIG)
        evidence = {}
        # No referenced manifest/original path is followed. Filenames are fixed
        # by reviewed configuration, with no arbitrary source/plugin discovery.
        for spec in config['sources']:
            if not KEY.fullmatch(spec['key']):
                raise RefreshError('invalid-binding-key')
            try:
                evidence[spec['key']] = read_metadata(Path(args.evidence_directory) / (spec['key'] + '.json'))
            except FileNotFoundError:
                evidence[spec['key']] = None
            except (ValueError, OSError, RecursionError):
                evidence[spec['key']] = {'invalid': True}
        previous = read_metadata(args.previous_keys) if args.previous_keys else {}
        result = assess_portfolio(config['sources'], evidence, now=args.now, previous_keys=previous)
        sys.stdout.buffer.write(canonical(result))
        return 0
    except (ValueError, OSError, KeyError, TypeError, RecursionError):
        sys.stdout.buffer.write(canonical({'status': 'malformed', 'diagnostics': ['metadata-request-invalid']}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
