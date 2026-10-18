"""Deterministic metadata-only portfolio preflight; never opens original paths.

Shared handlers retain execution/qualification authority. A metadata-ready result
is neither SourceContract construction nor permission to parse/transform/admit.
"""
import argparse
from datetime import timedelta
import os
import stat

from offmenu.refresh.core import canonical, sha, strict_json, timestamp, RefreshError
from offmenu.refresh.field_provenance import field_origin_errors
from offmenu.refresh.national_tabular import valid_input_name
from offmenu.refresh.adapter_mapping import retained_adapters

COUNTRIES = frozenset(('HT', 'HU', 'ID', 'IE'))
TYPES = frozenset(('ingredients', 'recipes', 'nutrition', 'retailers/providers',
                   'prices/baskets', 'dietary references'))


def _pin(value):
    return (isinstance(value, dict) and isinstance(value.get('path'), str)
            and bool(value['path']) and isinstance(value.get('sha256'), str)
            and len(value['sha256']) == 64
            and all(c in '0123456789abcdef' for c in value['sha256']))


def _one(binding, snapshot, now, previous):
    diagnostics, missing = set(), set()
    source, release = binding['sourceId'], binding['releaseId']
    if (not isinstance(source, str) or not source or not isinstance(release, str)
            or not release or binding['country'] not in COUNTRIES
            or not binding['types'] or not set(binding['types']) <= TYPES):
        raise RefreshError('binding-identity-invalid')
    if not _pin(binding['receipt']) or not _pin(binding['qualification']):
        raise RefreshError('binding-evidence-pin-invalid')
    assets = binding['inputFiles']
    if not isinstance(assets, list):
        raise RefreshError('binding-inputs-invalid')
    if not assets:
        missing.add('retained-input-missing')
    inputs = {}
    for asset in assets:
        if (not _pin(asset) or not valid_input_name(asset['path'])
                or type(asset.get('bytes')) is not int or asset['bytes'] < 0
                or asset['path'] in inputs):
            raise RefreshError('binding-input-pin-invalid')
        inputs[asset['path']] = asset['sha256']
    if not isinstance(snapshot, dict):
        holds = binding['holds']
        if not isinstance(holds, list) or any(not isinstance(h, str) or not h for h in holds):
            raise RefreshError('binding-holds-invalid')
        return {'status': 'held' if holds else 'missing',
                'sourceId': source, 'releaseId': release,
                'country': binding['country'], 'types': binding['types'],
                'holds': list(holds), 'diagnostics': ['snapshot-missing'],
                'networkRequests': 0, 'bodyExecutionAllowed': False}
    # Exact source/version/pins are compared as metadata, never verified on disk.
    for field, expected in [('sourceId', source), ('releaseId', release),
                            ('inputFiles', assets), ('receipt', binding['receipt'])]:
        if canonical(snapshot.get(field)) != canonical(expected):
            diagnostics.add('snapshot-' + field + '-mismatch')
    clock = timestamp(now)
    acquired = binding['acquiredAt']
    validated = snapshot.get('validatedAt')
    policy = {'minimumReuseDays': 30, 'acquiredAt': acquired,
              'validatedAt': validated, 'networkRequests': 0,
              'freshnessUsesValidationTime': False,
              'decision': 'unknown-acquisition-time'}
    stale = False
    if acquired is None:
        missing.add('original-acquisition-time-missing')
    else:
        acquired_time = timestamp(acquired)
        if acquired_time > clock:
            diagnostics.add('acquisition-in-future')
        else:
            stale = clock - acquired_time >= timedelta(days=30)
            policy['decision'] = ('conditional-revalidation-required' if stale
                                  else 'reuse-recorded-cache-zero-download')
    if validated is not None and timestamp(validated) > clock:
        diagnostics.add('validation-in-future')
    if snapshot.get('acquiredAt') != acquired:
        diagnostics.add('snapshot-acquisition-mismatch')
    rights = binding['use']
    if not isinstance(rights, dict):
        raise RefreshError('binding-use-invalid')
    if rights.get('status') != 'reviewed-private-transform':
        missing.add('operation-specific-use-unresolved')
    if not _pin(rights.get('decision')) or not rights.get('attribution'):
        missing.add('use-decision-or-attribution-missing')
    if not binding.get('scopeEvidence') or not _pin(binding['scopeEvidence']):
        missing.add('country-type-scope-evidence-missing')
    handler = binding.get('sharedHandler')
    available = {(x['sourceId'], x['releaseId']) for x in retained_adapters()}
    if handler is None:
        missing.add('shared-handler-unbound')
    elif (not isinstance(handler, dict)
          or any(not isinstance(handler.get(key), str) or not handler[key]
                 for key in ('sourceId', 'releaseId'))):
        raise RefreshError('binding-shared-handler-invalid')
    elif (handler.get('sourceId'), handler.get('releaseId')) != (source, release):
        diagnostics.add('shared-handler-source-mismatch')
    elif (handler.get('sourceId'), handler.get('releaseId')) not in available:
        diagnostics.add('shared-handler-identity-unsupported')
    fields = binding['fields']
    if not isinstance(fields, dict):
        raise RefreshError('binding-field-declarations-invalid')
    if not fields:
        missing.add('field-declarations-missing')
    data, origins = {}, {}
    for field, declaration in fields.items():
        if not isinstance(field, str) or not field or not isinstance(declaration, dict):
            raise RefreshError('binding-field-declarations-invalid')
        # Nulls here are declaration placeholders, never manufactured data rows.
        data[field] = None
        pointer = '/data/' + field.replace('~', '~0').replace('/', '~1')
        origin = declaration.get('origin')
        if origin is None:
            missing.add('field-origin-unresolved:' + pointer)
        else:
            origins[pointer] = origin
        for key in ('nativeUnit', 'nativeBasis'):
            if declaration.get(key) is None:
                missing.add('field-' + key + '-unknown:' + pointer)
            elif not isinstance(declaration[key], str) or not declaration[key]:
                diagnostics.add('field-' + key + '-invalid:' + pointer)
    if fields and len(origins) == len(fields):
        row = {'data': data, 'provenance': {'sourceId': source,
                'releaseId': release, 'fieldOrigins': origins}}
        diagnostics.update(field_origin_errors(row, inputs))
    holds = binding['holds']
    if not isinstance(holds, list) or any(not isinstance(h, str) or not h for h in holds):
        raise RefreshError('binding-holds-invalid')
    fingerprint = sha(canonical(binding))
    # Validation age is not acquisition age and does not perturb replay identity.
    identity = sha(canonical({'binding': fingerprint, 'inputFiles': assets}))
    status = ('malformed' if diagnostics else 'held' if holds else
              'missing' if missing else 'stale-input' if stale else 'metadata-ready')
    return {'status': status, 'sourceId': source, 'releaseId': release,
            'country': binding['country'], 'types': binding['types'],
            'diagnostics': sorted(diagnostics), 'missing': sorted(missing),
            'holds': list(holds), 'fieldDeclarations': fields,
            'cache': policy, 'bindingSha256': fingerprint,
            'replayIdentity': identity,
            'artifactAction': 'no-op' if previous == identity else 'binding-changed',
            'bodyExecutionAllowed': False, 'rawAssetIntegrityChecked': False,
            'networkRequests': 0, 'stagingAccepted': False, 'goldAdmitted': False}


def assess(bindings, snapshots, *, now, previous=None):
    """Isolate each metadata binding failure; callers supply an explicit UTC clock.

    No source permissions are trusted from CLI input for execution: this API
    emits diagnostics only, even for a fully authored positive fixture.
    """
    if not isinstance(bindings, list) or len(bindings) > 32 or not isinstance(snapshots, dict):
        raise RefreshError('portfolio-envelope-invalid')
    timestamp(now)
    previous = {} if previous is None else previous
    if not isinstance(previous, dict):
        raise RefreshError('portfolio-previous-invalid')
    reports, seen = [], set()
    for i, binding in enumerate(bindings):
        try:
            canonical(binding)  # nonfinite and non-JSON metadata fail closed
            if not isinstance(binding, dict) or not isinstance(binding.get('sourceId'), str):
                raise RefreshError('binding-identity-invalid')
            key = binding['sourceId']
            if key in seen:
                raise RefreshError('binding-duplicate-source')
            seen.add(key)
            report = _one(binding, snapshots.get(key), now, previous.get(key))
        except RefreshError as exc:
            report = {'status': 'malformed', 'diagnostics': [str(exc)],
                      'bodyExecutionAllowed': False, 'networkRequests': 0}
        except (KeyError, TypeError, ValueError, OverflowError):
            report = {'status': 'malformed', 'diagnostics': ['binding-malformed'],
                      'bodyExecutionAllowed': False, 'networkRequests': 0}
        reports.append({'bindingIndex': i, **report})
    return {'schemaVersion': 'offmenu-portfolio40-binding-report/1',
            'reports': reports, 'networkRequests': 0, 'sourceBodiesRead': 0,
            'sourceOperationsSelected': False, 'acceptedRecords': 0}


def _metadata(path):
    # CLI accepts only small metadata inputs. Original locations inside JSON are
    # opaque: never traverse those paths, URLs or source selectors here.
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        # Inspect the opened object, avoiding a check/open race and FIFO waits.
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise RefreshError('metadata-regular-file-required')
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            raw = stream.read(1024 * 1024 + 1)
    finally:
        os.close(descriptor)
    if len(raw) > 1024 * 1024:
        raise RefreshError('metadata-size-limit')
    return strict_json(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bindings', required=True)
    parser.add_argument('--snapshots', required=True)
    parser.add_argument('--now', required=True)
    parser.add_argument('--previous', help='Optional sourceId to prior replayIdentity metadata map')
    args = parser.parse_args()
    try:
        report = assess(_metadata(args.bindings)['bindings'],
                        _metadata(args.snapshots), now=args.now,
                        previous=_metadata(args.previous) if args.previous else None)
    except (RefreshError, ValueError, TypeError, KeyError, OSError):
        print(canonical({'error': 'portfolio-metadata-invalid'}).decode(), end='')
        return 2
    print(canonical(report).decode(), end='')
    return 0 if all(r['status'] == 'metadata-ready' for r in report['reports']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
