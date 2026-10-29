"""CO/MP/ST/UZ metadata bindings; no dataset reader or production admission.

Only the checked-in portfolio configuration is exposed by the CLI. Shared JSON,
pin, timestamp, field-origin and stage-receipt validators do the generic work.
No configuration value can register an execution adapter or SourceContract.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import stat

from .acquisition import MIN_TTL
from .acceptance import fingerprint
from .core import RefreshError, canonical, safe_path, sha, strict_json, timestamp
from .field_provenance import field_origin_errors
from .global_run import StageResult
from .portfolio31_catalogue import load_catalogue

# Retained source-checkout mirror; the installed default uses inert code literals.
CONFIG = Path(__file__).resolve().parents[2] / 'docs/portfolios/worker31-input-bindings.json'
COUNTRIES = ('CO', 'MP', 'ST', 'UZ')
TYPES = ('ingredients', 'recipes', 'nutrition', 'retailers/providers',
         'prices/baskets', 'dietary references')
HEX = re.compile(r'[0-9a-f]{64}')
METADATA_LIMIT = 1024 * 1024


def pointer(document, selector):
    """Resolve an evidenced JSON pointer, never a guessed source coordinate."""
    if selector == '':
        return document
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
            raise ValueError('selector-invalid')
    return value


def read_json_bytes(path):
    """Bound one nonblocking regular-file descriptor; never reopen its path."""
    path = safe_path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('metadata-regular-file-required')
        if info.st_size > METADATA_LIMIT:
            raise ValueError('metadata-size-limit')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(METADATA_LIMIT + 1)
        if len(raw) > METADATA_LIMIT:
            raise ValueError('metadata-size-limit')
        return raw
    finally:
        os.close(fd)


def read_metadata(reference):
    """Exact metadata pin only. Never follow asset paths found in its payload."""
    if (not isinstance(reference, dict) or not isinstance(reference.get('path'), str)
            or not isinstance(reference.get('sha256'), str)
            or not HEX.fullmatch(reference['sha256'])):
        raise ValueError('metadata-reference-invalid')
    path = safe_path(reference['path'])
    if path.suffix != '.json':
        raise ValueError('metadata-json-required')
    raw = read_json_bytes(path)
    if sha(raw) != reference['sha256']:
        raise ValueError('metadata-pin-mismatch')
    return strict_json(raw)


def diagnose_binding(spec, *, now, previous=None):
    """Return isolated fixed diagnostics and a metadata-only declaration.

    `succeeded` means this metadata declaration is complete for review, not that
    a dataset is qualified. Holds and unknown semantics remain independent of
    freshness. A metadata validation time never refreshes original acquisition.
    """
    errors = set()
    key = spec.get('key') if isinstance(spec, dict) else None
    result = {'key': key, 'errors': [], 'status': 'failed', 'fieldOrigins': {},
              'data': {}, 'cache': None, 'replay': 'not-established',
              'stagingActivated': False, 'normalizedRecords': 0,
              'datasetAccepted': False, 'countryComplete': False}
    if not isinstance(spec, dict) or not all(isinstance(spec.get(k), str) and spec[k]
            for k in ('key', 'country', 'sourceId', 'releaseId')):
        errors.add('binding-identity-invalid')
        return {**result, 'errors': sorted(errors)}
    if spec['country'] not in COUNTRIES:
        errors.add('portfolio-country-invalid')
    result.update(country=spec['country'], sourceId=spec['sourceId'], releaseId=spec['releaseId'],
                  nativeUnit=spec.get('unit'), nativeBasis=spec.get('basis'),
                  sourceAssetDeclarations=spec.get('sourceAssetDeclarations', []))
    holds = spec.get('holds')
    if not isinstance(holds, list) or any(not isinstance(h, str) or not h for h in holds):
        errors.add('binding-holds-invalid')
    elif holds:
        errors.add('source-held')
    for field in ('rightsDecision', 'custodyAcceptance', 'semanticSelectorEvidence'):
        if not spec.get(field):
            errors.add({'rightsDecision': 'source-use-decision-missing',
                        'custodyAcceptance': 'source-custody-unconfirmed',
                        'semanticSelectorEvidence': 'semantic-selector-evidence-missing'}[field])
    if spec.get('unit') is None:
        errors.add('native-unit-unknown')
    if spec.get('basis') is None:
        errors.add('native-basis-unknown')
    try:
        if now.tzinfo is None:
            raise ValueError()
        acquired = timestamp(spec.get('originalAcquiredAt'))
        age = (now - acquired).total_seconds()
        if age < 0:
            raise ValueError()
        validated = spec.get('validatedAt')
        if validated is not None and not acquired <= timestamp(validated) <= now:
            raise ValueError()
        stale = age >= MIN_TTL
        result['cache'] = {'originalAcquiredAt': spec['originalAcquiredAt'],
                           'validatedAt': validated, 'minimumReuseSeconds': MIN_TTL,
                           'acquisitionAgeSeconds': age,
                           'decision': 'stale-input-review-no-download' if stale else 'reuse-no-download',
                           'networkRequests': 0, 'mtimeUsed': False,
                           'scope': 'metadata-age-diagnostic-not-operational-cache-plan',
                           'sharedGenericCachePlanner': 'unsupported-at-selected-base',
                           'validationResetsAcquisition': False}
        if stale:
            errors.add('stale-input-review-required')
    except (ValueError, TypeError, AttributeError, RefreshError):
        errors.add('acquisition-validation-time-invalid')
    metadata = None
    try:
        metadata = read_metadata(spec.get('metadata'))
    except FileNotFoundError:
        errors.add('metadata-input-missing')
    except Exception:
        # Never echo source values, paths, credentials or arbitrary exceptions.
        errors.add('metadata-input-invalid')
    if metadata is not None:
        try:
            recorded_acquisition = timestamp(pointer(metadata, spec['acquisitionSelector']))
            if recorded_acquisition != timestamp(spec['originalAcquiredAt']):
                errors.add('acquisition-origin-mismatch')
        except (KeyError, IndexError, TypeError, ValueError, RefreshError):
            errors.add('acquisition-origin-missing')
        declaration_evidence = spec.get('fieldDeclarationEvidence')
        if declaration_evidence is not None:
            try:
                pointer(read_metadata(declaration_evidence), declaration_evidence['selector'])
            except Exception:
                errors.add('field-declaration-evidence-invalid')
        for label, name in (('unit', 'nativeUnitSelector'), ('basis', 'nativeBasisSelector')):
            if spec.get(label) is not None:
                try:
                    if pointer(metadata, spec[name]) != spec[label]:
                        errors.add('native-' + label + '-declaration-mismatch')
                except (KeyError, IndexError, TypeError, ValueError):
                    errors.add('native-' + label + '-selector-missing')
        fields = spec.get('fields')
        if not isinstance(fields, dict) or not fields:
            errors.add('field-declarations-missing')
        else:
            for name, declaration in sorted(fields.items()):
                try:
                    if not isinstance(name, str) or not name:
                        raise ValueError()
                    selector = declaration['selector']
                    value = pointer(metadata, selector)
                    # The binding is for scalar metadata declarations only.
                    if isinstance(value, (dict, list)):
                        errors.add('field-selector-not-scalar')
                        continue
                    result['data'][name] = value
                    escaped = name.replace('~', '~0').replace('/', '~1')
                    result['fieldOrigins']['/data/' + escaped] = {
                        'kind': 'source', 'sourceId': spec['sourceId'],
                        'releaseId': spec['releaseId'], 'inputPath': 'metadata.json',
                        'inputSha256': spec['metadata']['sha256'],
                        'sourceRecordId': spec['key'], 'sourceField': selector}
                except (KeyError, IndexError, ValueError, TypeError):
                    errors.add('field-selector-missing-or-invalid')
            if result['data']:
                row = {'data': result['data'], 'provenance': {
                    'sourceId': spec['sourceId'], 'releaseId': spec['releaseId'],
                    'fieldOrigins': result['fieldOrigins']}}
                errors.update(field_origin_errors(row, {'metadata.json': spec['metadata']['sha256']}))
    # Replaying does not skip any pin or diagnostic checks. It describes an
    # unchanged declaration, never permission to reuse a stale/held dataset.
    content = {k: v for k, v in spec.items() if k != 'validatedAt'}
    result['inputStateSha256'] = fingerprint(content)
    if errors:
        result['replay'] = 'blocked-not-reusable'
    elif isinstance(previous, dict) and previous.get('inputStateSha256') == result['inputStateSha256']:
        result['replay'] = 'unchanged-declaration-no-op'
    else:
        result['replay'] = 'new-or-changed-declaration'
    result['errors'] = sorted(errors)
    result['status'] = ('failed' if errors & {'binding-holds-invalid', 'portfolio-country-invalid',
        'metadata-input-invalid', 'acquisition-validation-time-invalid',
        'field-selector-missing-or-invalid', 'field-selector-not-scalar'} else 'held' if errors else 'succeeded')
    result['stageReceipt'] = StageResult(result['status'],
        'metadata-binding-diagnostics' if errors else 'metadata-binding-ready-for-review',
        (fingerprint({'key': key, 'data': result['data'], 'errors': result['errors']}),), 0).receipt()
    return result


def plan_portfolio(config, *, now, previous=None):
    """Bind only the selected portfolio; each source failure is isolated."""
    if (not isinstance(config, dict)
            or config.get('schemaVersion') != 'offmenu-worker31-input-bindings/1'
            or config.get('sourceProcessingEnabled') is not False
            or config.get('minimumReuseSeconds') != MIN_TTL
            or tuple(config.get('portfolio', ())) != COUNTRIES):
        raise ValueError('portfolio-contract-invalid')
    specs = config.get('bindings')
    if not isinstance(specs, list) or any(not isinstance(s, dict) for s in specs):
        raise ValueError('portfolio-bindings-invalid')
    keys = [s.get('key') for s in specs]
    if any(not isinstance(k, str) or not k for k in keys) or len(set(keys)) != len(keys):
        raise ValueError('portfolio-bindings-invalid')
    prior, replay_errors = {}, set()
    if previous is not None:
        if (not isinstance(previous, dict)
                or not isinstance(previous.get('sources', []), list)
                or previous.get('schemaVersion', 'offmenu-worker31-binding-plan/1')
                != 'offmenu-worker31-binding-plan/1'):
            replay_errors.add('prior-state-invalid')
        else:
            seen, rejected = set(), set()
            for entry in previous.get('sources', []):
                if (not isinstance(entry, dict) or not isinstance(entry.get('key'), str)
                        or entry['key'] not in keys):
                    replay_errors.add('prior-state-entry-invalid')
                    continue
                key = entry['key']
                if (key in seen or not isinstance(entry.get('inputStateSha256'), str)
                        or not HEX.fullmatch(entry['inputStateSha256'])):
                    replay_errors.add('prior-state-entry-invalid')
                    rejected.add(key)
                else:
                    prior[key] = entry
                seen.add(key)
            for key in rejected:
                prior.pop(key, None)
    results = []
    for spec in sorted(specs, key=lambda s: s['key']):
        try:
            results.append(diagnose_binding(spec, now=now, previous=prior.get(spec['key'])))
        except Exception:
            results.append({'key': spec['key'], 'status': 'failed',
                            'errors': ['metadata-binding-contract-invalid'],
                            'stagingActivated': False, 'normalizedRecords': 0,
                            'datasetAccepted': False, 'countryComplete': False})
    requirements = config.get('requirements')
    expected = {(c, t) for c in COUNTRIES for t in TYPES}
    if (not isinstance(requirements, list) or len(requirements) != len(expected)
            or {(r.get('country'), r.get('dataType')) for r in requirements} != expected
            or any(not isinstance(r.get('bindings'), list)
                   or any(k not in keys for k in r['bindings']) for r in requirements)):
        raise ValueError('portfolio-requirements-invalid')
    cells = [{'country': r['country'], 'dataType': r['dataType'],
              'bindings': r['bindings'], 'applicability': r.get('applicability'),
              'status': 'unaccepted', 'countryComplete': False,
              'missingInput': r.get('missingInput')}
             for r in sorted(requirements, key=lambda r: (r['country'], r['dataType']))]
    evidence_results = {}
    def evidence_status(evidence):
        identity = fingerprint(evidence)
        if identity not in evidence_results:
            try:
                pointer(read_metadata(evidence), evidence['selector'])
                evidence_results[identity] = 'verified-metadata-pin'
            except Exception:
                evidence_results[identity] = 'requirement-evidence-invalid'
        return evidence_results[identity]

    for requirement, cell in zip(sorted(requirements, key=lambda r: (r['country'], r['dataType'])), cells):
        evidence = requirement.get('evidence')
        if evidence is not None:
            cell['evidenceStatus'] = evidence_status(evidence)
    portfolio_evidence = [{'metadata': e, 'status': evidence_status(e)}
                          for e in config.get('evidence', [])]
    return {**({'replayDiagnostics': sorted(replay_errors)} if replay_errors else {}),
            'schemaVersion': 'offmenu-worker31-binding-plan/1',
            'selectedBase': config.get('selectedBase'), 'sources': results, 'requirements': cells,
            'portfolioEvidence': portfolio_evidence,
            'stagingActivated': False, 'normalizedRecords': 0, 'goldAdmissions': 0,
            'networkRequests': 0, 'countryCoverageComplete': False,
            'sharedInterfaceLimits': ['generic-pure-cache-planner-absent',
                                      'reviewed-real-source-adapter-binding-missing',
                                      'production-admissions-not-installed'],
            'scope': 'metadata-declarations-only-not-source-record-qualification'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--now', required=True, help='Explicit UTC evaluation time')
    parser.add_argument('--previous', type=Path, help='Prior metadata plan, never a permission grant')
    args = parser.parse_args(argv)
    try:
        config = load_catalogue()
        previous = strict_json(read_json_bytes(args.previous)) if args.previous else None
        result = plan_portfolio(config, now=timestamp(args.now), previous=previous)
    except (ValueError, OSError, TypeError, KeyError, RecursionError):
        print(canonical({'status': 'failed', 'errors': ['metadata-request-invalid']}).decode(), end='')
        return 2
    print(canonical(result).decode(), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
