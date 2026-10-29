"""RU/NC/NF/PG retained-metadata bindings; never open originals or enable sources.

Selectors describe already retained inspection evidence, not verified source cells.
The shared validator verifies origin coverage. Semantic acceptance is separate.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import stat

from .core import canonical, sha, strict_json, timestamp, safe_path, RefreshError
from .field_provenance import datum_pointers, field_origin_errors
from .acquisition import MIN_TTL

CONFIG = Path(__file__).resolve().parents[2] / 'config/staging/portfolio58.json'
MAX_METADATA = 256 * 1024
MAX_PREVIOUS = 1024 * 1024
COUNTRIES = ('RU', 'NC', 'NF', 'PG')


def pointer(document, selector):
    """Strict JSON pointer into metadata only; missing differs from explicit null."""
    if not isinstance(selector, str) or not selector.startswith('/'):
        raise ValueError('selector-invalid')
    value = document
    for token in selector[1:].split('/'):
        if re.search(r'~(?![01])', token):
            raise ValueError('selector-invalid')
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', token):
                raise ValueError('selector-invalid')
            value = value[int(token)]
        elif isinstance(value, dict):
            value = value[token]
        else:
            raise KeyError(token)
    return value


def assess(binding, raw, *, now, previous_key=None, cache_planner=None):
    """Pure bounded metadata assessment. Trusted binding is reviewed config/code.

An optional shared pure planner takes the returned cacheRequest dictionary and
returns decision/minimumReuseDays/networkRequests. No acquirer is called. This
interface remains explicitly missing until integrator00 selects its shared code.
"""
    codes = set()
    result = {'sourceId': binding['sourceId'], 'releaseId': binding['releaseId'],
              'country': binding['country'], 'status': 'malformed', 'diagnostics': [],
              'metadataRow': None, 'cacheRequest': None, 'replayKey': None,
              'datasetAccepted': False, 'networkRequests': 0, 'originalReads': 0}
    if raw is None:
        result.update(status='missing', diagnostics=['metadata-input-missing'])
        return result
    if not isinstance(raw, bytes) or len(raw) > MAX_METADATA:
        result['diagnostics'] = ['metadata-input-bound-or-type']
        return result
    if sha(raw) != binding['metadata']['sha256']:
        result['diagnostics'] = ['metadata-pin-mismatch']
        return result
    try:
        document = strict_json(raw)
        acquired = (timestamp(binding['originalAcquiredAt'])
                    if binding['originalAcquiredAt'] is not None else None)
        clock = timestamp(now)
        validated = (timestamp(binding['validationObservedAt'])
                     if binding['validationObservedAt'] is not None else None)
        if (acquired is not None and acquired > clock
                or validated is not None and (validated > clock
                    or acquired is not None and validated < acquired)):
            raise ValueError('metadata-time-order-invalid')
        if acquired is None:
            codes.add('original-acquisition-evidence-missing')
        data, origins = {}, {}
        for name, selector in binding['selectors'].items():
            value = pointer(document, selector)
            data[name] = value
            for target in datum_pointers(value, '/data/' + name):
                suffix = target[len('/data/' + name):]
                origins[target] = {'kind': 'source', 'sourceId': binding['sourceId'],
                    'releaseId': binding['releaseId'], 'inputPath': 'metadata/evidence.json',
                    'inputSha256': sha(raw), 'sourceRecordId': 'retained-inspection-metadata',
                    'sourceField': selector + suffix}
        policy = sha(canonical(binding))
        for name, value in binding['declarations'].items():
            if name in data:
                raise ValueError('declaration-selector-collision')
            data[name] = value
            for target in datum_pointers(value, '/data/' + name):
                origins[target] = {'kind': 'constant', 'policySha256': policy,
                                   'symbol': 'portfolio58:' + name}
        row = {'id': binding['sourceId'] + ':retained-metadata',
               'kind': 'source-input-metadata', 'schemaVersion': 'offmenu-portfolio58-binding/1',
               'data': data, 'provenance': {'sourceId': binding['sourceId'],
                   'releaseId': binding['releaseId'], 'fetchedAt': binding['originalAcquiredAt'],
                   'fieldOrigins': origins}}
        codes.update(field_origin_errors(row, {'metadata/evidence.json': sha(raw)},
                                         policy_pins=(policy,)))
        # Stage identity excludes validation clock: revalidation cannot reset acquisition
        # age or force a new transform for identical source/config/selected data.
        key = sha(canonical({'sourceId': binding['sourceId'],
            'releaseId': binding['releaseId'], 'original': binding['original'],
            'selectors': binding['selectors'], 'data': data,
            'holds': binding['holds'], 'scope': binding['scope'],
            'evidencePins': binding['evidencePins']}))
        request = {'sourceId': binding['sourceId'], 'releaseId': binding['releaseId'],
            'originalAcquiredAt': binding['originalAcquiredAt'],
            'validationObservedAt': binding['validationObservedAt'], 'now': now,
            'minimumReuseDays': MIN_TTL // 86400, 'inputSha256': binding['original']['sha256'],
            'holds': binding['holds'], 'scope': binding['scope'],
            'requestedOperation': 'metadata-binding', 'networkAllowed': False}
        result.update(metadataRow=row, replayKey=key, cacheRequest=request)
        if binding['holds']:
            codes.update(binding['holds'])
        if binding['holds']:
            result['cachePlan'] = {'decision': 'held-no-planner-invocation',
                                   'networkRequests': 0, 'minimumReuseDays': MIN_TTL // 86400}
            decision = None
        elif cache_planner is None:
            codes.add('shared-pure-cache-planner-not-bound')
            decision = None
        else:
            try:
                plan = cache_planner(dict(request))
            except Exception:
                result.update(status='blocked', diagnostics=sorted(codes | {'cache-planner-failed'}))
                return result
            if (not isinstance(plan, dict) or plan.get('networkRequests') != 0
                    or type(plan.get('minimumReuseDays')) is not int
                    or plan['minimumReuseDays'] < MIN_TTL // 86400
                    or plan.get('decision') not in
                    ('reuse-retained-metadata', 'review-required-no-download')):
                raise ValueError('cache-planner-contract-invalid')
            result['cachePlan'] = plan
            decision = plan['decision']
            if decision == 'review-required-no-download':
                codes.add('stale-input-review-required')
        result['diagnostics'] = sorted(codes)
        result['status'] = ('held' if binding['holds'] else
            'stale' if 'stale-input-review-required' in codes else
            'blocked' if codes else 'noop' if previous_key == key else 'ready-metadata')
        return result
    except (ValueError, TypeError, KeyError, IndexError, OverflowError):
        result.update(status='malformed', metadataRow=None,
                      diagnostics=sorted(codes | {'metadata-shape-selector-or-clock-invalid'}))
        return result


def run(config, *, now, previous_keys=None, cache_planner=None):
    """Read only exact allowlisted metadata files; isolate each input failure."""
    rows = []
    for binding in config['bindings']:
        try:
            path = safe_path(binding['metadata']['path'])
            if not path.exists():
                raw = None
            elif not path.is_file() or path.stat().st_size > MAX_METADATA:
                raw = b''  # Fail closed without reading an oversized input.
            else:
                with path.open('rb') as stream:
                    raw = stream.read(MAX_METADATA + 1)
            rows.append(assess(binding, raw, now=now,
                previous_key=(previous_keys or {}).get(binding['sourceId']),
                cache_planner=cache_planner))
        except (OSError, ValueError):
            rows.append({'sourceId': binding['sourceId'], 'status': 'malformed',
                         'diagnostics': ['metadata-file-unavailable-or-unsafe'],
                         'datasetAccepted': False})
    return {'schemaVersion': 'offmenu-portfolio58-report/1', 'scope': 'metadata-only',
            'countryTypeApplicability': config['countryTypeApplicability'],
            'sources': rows, 'originalReads': 0, 'networkRequests': 0,
            'datasetAccepted': False}


def _previous_keys(path):
    """Read only a bounded regular opened descriptor; never wait for a FIFO."""
    path = safe_path(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise ValueError('previous-report-not-regular')
        if opened.st_size > MAX_PREVIOUS:
            raise ValueError('previous-report-too-large')
        raw = bytearray()
        while len(raw) <= MAX_PREVIOUS:
            block = os.read(descriptor, min(65536, MAX_PREVIOUS + 1 - len(raw)))
            if not block:
                break
            raw.extend(block)
        if len(raw) > MAX_PREVIOUS:
            raise ValueError('previous-report-too-large')
    finally:
        os.close(descriptor)
    old = strict_json(bytes(raw))
    return {row['sourceId']: row.get('replayKey') for row in old['sources']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--now', required=True, help='Explicit UTC clock for deterministic diagnostics')
    parser.add_argument('--previous', type=Path, help='Prior metadata report; never an admission')
    args = parser.parse_args(argv)
    previous = {}
    if args.previous:
        try:
            previous = _previous_keys(args.previous)
        except (OSError, ValueError, TypeError, KeyError, RecursionError) as error:
            code = str(error) if str(error) in (
                'previous-report-not-regular', 'previous-report-too-large') else 'previous-report-invalid-or-unavailable'
            parser.error(code)
    report = run(strict_json(CONFIG.read_bytes()), now=args.now, previous_keys=previous)
    print(canonical(report).decode(), end='')
    return 0 if all(r['status'] in ('ready-metadata', 'noop') for r in report['sources']) else 2


if __name__ == '__main__':
    raise SystemExit(main())
