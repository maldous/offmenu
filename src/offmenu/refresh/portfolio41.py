"""QA/TC/TW/VG metadata bindings, never source-body adapters or admissions.

The shared core owns JSON/time/hash/path helpers, per-datum origin validation and
stage diagnostics. No network, archive, PDF, source CSV or plugin execution path.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import os
import re
import stat

from .core import RefreshError, canonical, exact_keys, safe_path, sha, strict_json, timestamp
from .acquisition import MIN_TTL, MAX_METADATA
from .field_provenance import field_origin_errors
from .global_run import StageResult
from .portfolio41_catalogue import load_catalogue

COUNTRIES = ('QA', 'TC', 'TW', 'VG')
# Checkout mirror only; the default loader uses the owned packaged literal.
CONFIG = Path(__file__).resolve().parents[3] / 'config' / 'portfolios' / 'worker41.json'
POLICY = {'id': 'portfolio41-metadata-binding/1', 'representation': 'receipt-metadata-only',
          'unknown': 'unestablished-not-zero', 'network': 'absent', 'sourceBodies': 'closed'}
POLICY_PIN = sha(canonical(POLICY))
KEYS = ('id', 'country', 'sourceId', 'releaseId', 'releaseStatus', 'role',
        'metadataPin', 'fieldSelectors', 'originalAcquiredAtSelector', 'validatedAt',
        'maxValidationAgeDays', 'holds', 'missingInputs', 'countryTypes', 'bodyAdapter')


def pointer(document, selector):
    """Resolve a literal metadata JSON pointer; no inferred selector fallback."""
    if not isinstance(selector, str) or not selector.startswith('/'):
        raise RefreshError('metadata-selector-invalid')
    value = document
    for part in selector[1:].split('/'):
        if re.search(r'~(?![01])', part):
            raise RefreshError('metadata-selector-invalid')
        part = part.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', part):
                raise RefreshError('metadata-selector-missing')
            try:
                value = value[int(part)]
            except IndexError:
                raise RefreshError('metadata-selector-missing') from None
        elif isinstance(value, dict) and part in value:
            value = value[part]
        else:
            raise RefreshError('metadata-selector-missing')
    return value


def _validate(binding):
    exact_keys(binding, KEYS)
    if (binding['country'] not in COUNTRIES or binding['role'] != 'receipt-metadata-only'
            or binding['bodyAdapter'] is not None):
        raise RefreshError('portfolio-scope-invalid')
    for key in ('id', 'sourceId', 'releaseId', 'releaseStatus'):
        if not isinstance(binding[key], str) or not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,127}', binding[key]):
            raise RefreshError('binding-identity-invalid')
    pin = binding['metadataPin']
    exact_keys(pin, ('path', 'bytes', 'sha256'))
    if (not isinstance(pin['path'], str) or not pin['path'].endswith('.json')
            or type(pin['bytes']) is not int or not 1 <= pin['bytes'] <= MAX_METADATA
            or not isinstance(pin['sha256'], str) or not re.fullmatch('[a-f0-9]{64}', pin['sha256'])):
        raise RefreshError('metadata-pin-invalid')
    if (type(binding['maxValidationAgeDays']) is not int
            or not 1 <= binding['maxValidationAgeDays'] <= 365):
        raise RefreshError('validation-bound-invalid')
    if not isinstance(binding['fieldSelectors'], dict) or not binding['fieldSelectors']:
        raise RefreshError('field-selectors-required')
    for name, selector in binding['fieldSelectors'].items():
        if not isinstance(name, str) or not re.fullmatch('[A-Za-z][A-Za-z0-9]{0,63}', name):
            raise RefreshError('field-name-invalid')
        if not isinstance(selector, str) or not selector.startswith('/'):
            raise RefreshError('metadata-selector-invalid')
    if not isinstance(binding['originalAcquiredAtSelector'], str):
        raise RefreshError('metadata-selector-invalid')
    for field in ('holds', 'missingInputs', 'countryTypes'):
        if (not isinstance(binding[field], list) or len(binding[field]) > 32
                or any(not isinstance(x, str) or not x or len(x) > 256 for x in binding[field])):
            raise RefreshError('binding-list-invalid')
    return binding


def load_bindings():
    data = load_catalogue()
    exact_keys(data, ('schemaVersion', 'baseline', 'scope', 'bindings'))
    if (data['schemaVersion'] != 'offmenu-portfolio41-bindings/1'
            or not isinstance(data['bindings'], list) or len(data['bindings']) != 4):
        raise RefreshError('portfolio-config-invalid')
    for binding in data['bindings']:
        _validate(binding)
    if sorted(b['country'] for b in data['bindings']) != sorted(COUNTRIES):
        raise RefreshError('portfolio-config-invalid')
    return data


def assess(binding, raw, *, now, previous_build_key=None):
    """Pure offline contract assessment. raw must be the declared metadata only.

    Validation age diagnoses evidence currency; it never changes acquisition age
    or the content/build key. READY_METADATA never permits any body operation.
    """
    report = {'bindingId': binding.get('id') if isinstance(binding, dict) else None,
              'status': 'MALFORMED', 'diagnostics': [], 'metadataRecord': None,
              'buildKey': None, 'replay': 'not-ready', 'cache': None,
              'bodyOperationsAllowed': [], 'acceptedDatasetRecords': None,
              'countryComplete': False, 'networkRequests': 0}
    codes = set()
    def diag(code):
        codes.add(code)
    try:
        _validate(binding)
        if (not isinstance(now, datetime) or now.tzinfo is None
                or now.utcoffset().total_seconds() != 0):
            raise RefreshError('policy-clock-must-be-utc')
        validated = timestamp(binding['validatedAt'])
        if validated > now:
            raise RefreshError('validation-timestamp-in-future')
        if binding['holds']:
            diag('source-operation-held')
        if binding['missingInputs']:
            diag('source-input-not-supplied')
        if raw is None:
            diag('metadata-input-missing')
            report['status'] = 'HELD' if binding['holds'] else 'MISSING'
        else:
            pin = binding['metadataPin']
            if not isinstance(raw, bytes) or len(raw) != pin['bytes'] or sha(raw) != pin['sha256']:
                raise RefreshError('metadata-input-pin-mismatch')
            try:
                document = strict_json(raw)
                # JSON decoding alone can admit float overflow and lone surrogates.
                # Validate the output representation inside this source boundary.
                canonical(document)
            except (ValueError, UnicodeError, RecursionError):
                raise RefreshError('metadata-json-invalid') from None
            acquired = timestamp(pointer(document, binding['originalAcquiredAtSelector']))
            if acquired > validated:
                raise RefreshError('acquisition-after-validation')
            data, origins = {}, {}
            for name, selector in sorted(binding['fieldSelectors'].items()):
                value = pointer(document, selector)
                if not isinstance(value, (str, int, float, bool, type(None))):
                    raise RefreshError('metadata-scalar-field-required')
                data[name] = value
                origins['/data/' + name] = {
                    'kind': 'source', 'sourceId': binding['sourceId'], 'releaseId': binding['releaseId'],
                    'inputPath': 'receipt.json', 'inputSha256': pin['sha256'],
                    'sourceRecordId': 'literal-metadata-document', 'sourceField': selector}
            # These explicit unknowns are policy constants, not claimed source cells.
            for name in ('nativeUnit', 'nativeBasis'):
                if name in data:
                    raise RefreshError('reserved-metadata-field')
                data[name] = None
                origins['/data/' + name] = {'kind': 'constant', 'policySha256': POLICY_PIN,
                                           'symbol': 'unestablished-not-zero'}
            record = {'id': binding['id'], 'kind': 'source-metadata', 'schemaVersion': '1.0',
                      'data': data, 'provenance': {'sourceId': binding['sourceId'],
                      'releaseId': binding['releaseId'], 'fetchedAt': acquired.isoformat(),
                      'fieldOrigins': origins}}
            codes.update(field_origin_errors(record, {'receipt.json': pin['sha256']},
                                            policy_pins=(POLICY_PIN,)))
            report['metadataRecord'] = record
            # Stable representation identity; clock/validation events do not rebuild content.
            report['buildKey'] = sha(canonical({'record': record, 'policy': POLICY_PIN,
                                               'releaseStatus': binding['releaseStatus']}))
            report['replay'] = ('unchanged-content-no-op' if previous_build_key == report['buildKey']
                                else 'new-metadata-candidate')
            age = (now - acquired).total_seconds()
            validation_age = (now - validated).total_seconds()
            report['cache'] = {'originalAcquiredAt': acquired.isoformat(),
                'lastValidatedAt': validated.isoformat(), 'originalAgeSeconds': age,
                'validationAgeSeconds': validation_age, 'minimumReuseSeconds': MIN_TTL,
                'automaticNetworkAllowed': False, 'mtimeUsed': False,
                'under30DayDecision': ('reuse-retained-metadata-no-download' if age < MIN_TTL
                                      else 'conditional-review-required-no-download'),
                'rightsOverride': False, 'cacheBodyVerified': False}
            if validation_age >= binding['maxValidationAgeDays'] * 86400:
                diag('validation-evidence-stale')
            report['status'] = ('HELD' if binding['holds'] else 'MISSING' if binding['missingInputs']
                else 'STALE' if 'validation-evidence-stale' in codes else 'READY_METADATA')
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        code = str(error) if isinstance(error, RefreshError) else 'binding-shape-invalid'
        diag(code)
        report['status'] = 'MALFORMED'
        report.update(metadataRecord=None, buildKey=None, replay='not-ready', cache=None)
    report['diagnostics'] = sorted(codes)
    stage_status = ('succeeded' if report['status'] == 'READY_METADATA' else
                    'held' if report['status'] == 'HELD' else 'unsupported' if report['status'] in ('MISSING', 'STALE') else 'failed')
    evidence = (report['buildKey'],) if report['buildKey'] else ()
    code = report['diagnostics'][0] if report['diagnostics'] else 'metadata-only-ready'
    report['stageDiagnostic'] = StageResult(stage_status, code, evidence).receipt()
    return report


def assess_portfolio(bindings, loader, *, now, previous_build_keys=None):
    """Isolate fixed source failures; loader is trusted metadata-only code, not a plugin."""
    results = []
    for binding in bindings:
        try:
            _validate(binding)
        except (RefreshError, TypeError, RecursionError):
            results.append(assess(binding, None, now=now))
            continue
        try:
            raw = loader(binding['metadataPin'])
        except FileNotFoundError:
            raw = None
        except (OSError, RefreshError, ValueError):
            result = assess(binding, None, now=now)
            result.update(status='MALFORMED', diagnostics=['metadata-read-failed'],
                          stageDiagnostic=StageResult('failed', 'metadata-read-failed').receipt())
            results.append(result)
            continue
        results.append(assess(binding, raw, now=now,
                              previous_build_key=(previous_build_keys or {}).get(binding['id'])))
    return {'schemaVersion': 'offmenu-portfolio41-report/1', 'scope': 'metadata-only',
            'sources': results, 'countryComplete': False, 'acceptedDatasetRecords': None}


def read_metadata(pin):
    """Read one bounded regular descriptor; never reopen a verified pathname."""
    path = safe_path(pin['path'])
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise RefreshError('metadata-input-not-regular')
        if before.st_size > MAX_METADATA:
            raise RefreshError('metadata-size-limit')
        blocks, consumed = [], 0
        while consumed <= MAX_METADATA:
            block = os.read(descriptor, min(65536, MAX_METADATA + 1 - consumed))
            if not block:
                break
            blocks.append(block)
            consumed += len(block)
        if consumed > MAX_METADATA:
            raise RefreshError('metadata-size-limit')
        after = os.fstat(descriptor)
        current = safe_path(path).stat()
        snapshot = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if (snapshot(before) != snapshot(after) or snapshot(after) != snapshot(current)
                or consumed != after.st_size):
            raise RefreshError('metadata-changed-during-read')
        return b''.join(blocks)
    finally:
        os.close(descriptor)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--now', required=True, help='Explicit UTC clock for deterministic evidence')
    parser.add_argument('--output', required=True, help='New local report path; never overwrite')
    parser.add_argument('--previous-report', help='Earlier portfolio metadata report for unchanged build keys')
    args = parser.parse_args(argv)
    config = load_bindings()
    previous = {}
    if args.previous_report:
        path = safe_path(args.previous_report)
        prior = strict_json(read_metadata({'path': str(path)}))
        if (not isinstance(prior, dict) or prior.get('schemaVersion') != 'offmenu-portfolio41-report/1'
                or prior.get('scope') != 'metadata-only' or not isinstance(prior.get('sources'), list)):
            raise RefreshError('previous-report-invalid')
        for row in prior['sources']:
            if (not isinstance(row, dict) or not isinstance(row.get('bindingId'), str)
                    or row['bindingId'] in previous or not isinstance(row.get('buildKey'), (str, type(None)))):
                raise RefreshError('previous-report-invalid')
            previous[row['bindingId']] = row['buildKey']
    report = assess_portfolio(config['bindings'], read_metadata, now=timestamp(args.now),
                              previous_build_keys=previous)
    output = safe_path(args.output)
    with output.open('xb') as stream:
        stream.write(canonical(report))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
