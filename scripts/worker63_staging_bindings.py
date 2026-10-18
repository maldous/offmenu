#!/usr/bin/env python3
"""Offline metadata bindings for portfolio63; never a source admission factory."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from offmenu.refresh.acquisition import MIN_TTL
from offmenu.refresh.field_provenance import datum_pointers, field_origin_errors
from offmenu.refresh.national_tabular import bundle_files
from offmenu.refresh.core import (RefreshError, atomic_json, canonical, digest,
                                 safe_path, strict_json, timestamp)

COUNTRIES = ('GW', 'PE', 'TV', 'ZM')
MAX_METADATA = 1024 * 1024
CONFIG = ROOT / 'config/staging/worker63-bindings.json'
HEX = re.compile(r'[0-9a-f]{64}')


def pointer(value, selector):
    if selector == '':
        return value
    if not isinstance(selector, str) or not selector.startswith('/'):
        raise ValueError('invalid-selector')
    for token in selector[1:].split('/'):
        if re.search(r'~(?![01])', token):
            raise ValueError('invalid-selector')
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', token):
                raise ValueError('invalid-selector')
            value = value[int(token)]
        else:
            value = value[token]
    return value


def read_metadata(path):
    path = safe_path(path)
    # This API is metadata-only. Original references are never resolved/opened.
    if path.suffix != '.json':
        raise RefreshError('metadata-json-only')
    before = digest(path, max_bytes=MAX_METADATA)
    raw = path.read_bytes()
    after = digest(path, max_bytes=MAX_METADATA)
    if before != after or hashlib.sha256(raw).hexdigest() != before['sha256']:
        raise RefreshError('metadata-changed-during-read')
    return raw, before



def metadata_record(asset, selector, selected):
    """Per-datum origins for metadata only, not a normalized source payload."""
    if not re.fullmatch(r'[a-z0-9-]+', asset['id']):
        raise ValueError('invalid-metadata-id')
    identity = 'metadata:' + asset['id']
    release = 'sha256:' + asset['sha256']
    name = 'metadata/' + asset['id'] + '.json'
    row = {'id': identity + ':' + hashlib.sha256(selector.encode()).hexdigest()[:16],
           'kind': 'referenceMetadata', 'schemaVersion': '1.0',
           'data': {'selectedMetadata': selected},
           'provenance': {'sourceId': identity, 'releaseId': release,
                          'fetchedAt': None, 'scope': 'metadata-declaration-only',
                          'fieldOrigins': {}}}
    for dest in datum_pointers(row['data']):
        suffix = dest[len('/data/selectedMetadata'):]
        row['provenance']['fieldOrigins'][dest] = {
            'kind': 'source', 'sourceId': identity, 'releaseId': release,
            'inputPath': name, 'inputSha256': asset['sha256'],
            'sourceRecordId': selector or '/', 'sourceField': selector + suffix or '/'}
    errors = field_origin_errors(row, {name: asset['sha256']})
    if errors:
        raise ValueError('metadata-field-origin-invalid')
    return row


def cache_declaration(originals, now):
    """Metadata decision only; no cache body verification, download or force mode."""
    clock = timestamp(now)
    result = []
    for item in originals:
        acquired = item.get('acquiredAt')
        if acquired is None:
            age, decision = None, 'original-acquisition-time-unknown'
        else:
            seconds = (clock - timestamp(acquired)).total_seconds()
            if seconds < 0:
                raise RefreshError('original-acquisition-in-future')
            age = int(seconds)
            decision = ('under-minimum-window-zero-download'
                        if seconds < MIN_TTL else 'conditional-refresh-eligibility-only')
        result.append({'sourceReference': item['sourceReference'],
                       'originalAcquiredAt': acquired, 'originalAgeSeconds': age,
                       'minimumReuseSeconds': MIN_TTL, 'decision': decision,
                       'bodyVerifiedThisRun': False, 'networkRequests': 0})
    return result


def evaluate(spec, *, now, previous_digest=None, loader=read_metadata):
    """Check reviewed portfolio configuration, preserving held/unknown source data.

    This emits binding metadata, NOT SourceContract/Admission from a manifest.
    Future data-stage factories must be independently reviewed trusted code.
    """
    timestamp(now)
    country = spec['country']
    if country not in COUNTRIES or not isinstance(spec.get('sourceKey'), str):
        raise ValueError('unsupported-portfolio-binding')
    issues, evidence, values, records = [], [], [], []
    assets = spec.get('metadataAssets')
    if not isinstance(assets, list) or not assets:
        raise ValueError('metadata-assets-required')
    names = [a['id'] for a in assets]
    if len(names) != len(set(names)):
        raise ValueError('duplicate-metadata-id')
    for asset in assets:
        check = {'id': asset['id'], 'path': asset['path'],
                 'expectedSHA256': asset['sha256'], 'status': 'valid'}
        if not isinstance(asset['sha256'], str) or not HEX.fullmatch(asset['sha256']):
            raise ValueError('invalid-metadata-pin')
        try:
            raw, measured = loader(asset['path'])
            check['observedSHA256'] = measured['sha256']
            check['bytes'] = measured['bytes']
            if measured['sha256'] != asset['sha256']:
                check['status'] = 'stale-input'
                issues.append({'asset': asset['id'], 'code': 'metadata-pin-mismatch'})
            else:
                obj = strict_json(raw)
                canonical(obj)  # Reject overflowed numbers as well as explicit NaN.
                for selector in asset['selectors']:
                    try:
                        selected = pointer(obj, selector)
                        values.append({'value': selected,
                                       'origin': {'metadataId': asset['id'],
                                                  'metadataSHA256': asset['sha256'],
                                                  'jsonPointer': selector}})
                        records.append(metadata_record(asset, selector, selected))
                    except (KeyError, IndexError, TypeError, ValueError):
                        check['status'] = 'malformed-input'
                        issues.append({'asset': asset['id'], 'code': 'metadata-selector-missing'})
        except FileNotFoundError:
            check['status'] = 'missing-input'
            issues.append({'asset': asset['id'], 'code': 'metadata-missing'})
        except (OSError, ValueError, UnicodeError):
            check['status'] = 'malformed-input'
            issues.append({'asset': asset['id'], 'code': 'metadata-invalid-or-unsafe'})
        evidence.append(check)
    # All real bindings remain blocked for new data processing, even if someone
    # removes config holds. Config content cannot install a source admission.
    issues.extend({'code': 'source-held', 'hold': h} for h in spec['holds'])
    issues.append({'code': 'data-stage-not-authorized-by-metadata-binding'})
    stable = {'schemaVersion': 'offmenu-portfolio63-source-binding/1',
              'country': country, 'sourceKey': spec['sourceKey'],
              'declaredIdentity': spec['declaredIdentity'],
              'countryTypeApplicability': spec['countryTypeApplicability'],
              'fieldOriginDeclarations': spec['fieldOriginDeclarations'],
              'originalReferencesOnly': spec['originalReferencesOnly'],
              'evidence': evidence, 'observations': values,
              'metadataReferenceRecords': records,
              'unknowns': spec['unknowns'], 'holds': spec['holds'],
              'newSourceProcessing': False, 'sourceAcceptance': False,
              'goldAdmitted': False}
    content_digest = hashlib.sha256(canonical(stable)).hexdigest()
    failures = [e['status'] for e in evidence if e['status'] != 'valid']
    return {'binding': stable, 'bindingContentSHA256': content_digest,
            'metadataStatus': sorted(set(failures)) or ['valid'],
            'dataStageStatus': 'held',
            'bindingContentNoOp': not failures and previous_digest == content_digest,
            'diagnostics': issues, 'validationCheckedAt': now,
            'validationDoesNotResetOriginalAcquisition': True,
            'metadataValidationAgeSeconds': 0 if not failures else None,
            'sharedPureCachePlanner': 'unsupported-at-abec; portfolio-only metadata intent',
            'metadataReferenceRecordsEmitted': len(records),
            'cacheMetadata': cache_declaration(spec['originalReferencesOnly'], now),
            'networkRequests': 0, 'newRecordsParsed': 0}


def evaluate_portfolio(config, *, now, previous=None, loader=read_metadata):
    if config.get('schemaVersion') != 'offmenu-portfolio63-bindings/1':
        raise ValueError('unsupported-binding-config')
    specs = config['bindings']
    if (len(specs) != 4 or {s['country'] for s in specs} != set(COUNTRIES)):
        raise ValueError('exact-four-country-bindings-required')
    if previous is not None and (not isinstance(previous, dict) or previous.get('schemaVersion') != 'offmenu-portfolio63-binding-report/1'):
        raise ValueError('invalid-previous-binding-report')
    prior = {r['binding']['country']: r['bindingContentSHA256']
             for r in (previous or {}).get('results', []) if isinstance(r, dict) and isinstance(r.get('binding'), dict)}
    result = []
    for spec in specs:
        try:
            result.append(evaluate(spec, now=now, previous_digest=prior.get(spec['country']), loader=loader))
        except (KeyError, TypeError, ValueError, OverflowError):
            result.append({'country': spec.get('country'), 'metadataStatus': ['malformed-input'],
                           'dataStageStatus': 'held', 'diagnostics': [{'code': 'binding-config-invalid'}],
                           'sourceAcceptance': False, 'networkRequests': 0})
    return {'schemaVersion': 'offmenu-portfolio63-binding-report/1',
            'results': result, 'productionAdmissionsInstalled': 0,
            'networkRequests': 0, 'wholeCountriesComplete': 0}


def write_if_changed(path, report):
    path = safe_path(path)
    body = canonical(report)
    if path.exists():
        if path.read_bytes() == body:
            return 'unchanged-no-op'
        raise RefreshError('binding-output-generation-conflict')
    atomic_json(path, report)
    return 'metadata-report-written'



def stage_metadata(spec, result, destination):
    """Materialize only reviewed JSON metadata references, never original assets.

    Produces portfolio declaration packets, not a qualifying source dataset.
    A different/unexpected output generation is refused, never overwritten.
    """
    if result['metadataStatus'] != ['valid']:
        raise RefreshError('metadata-stage-input-not-valid')
    files, inputs = {}, []
    for asset in spec['metadataAssets']:
        raw, pin = read_metadata(asset['path'])
        if pin['sha256'] != asset['sha256']:
            raise RefreshError('metadata-stage-input-stale')
        name = 'metadata/' + asset['id'] + '.json'
        files[name] = raw
        inputs.append({'path': name, **pin})
    # Same packet shape as the shared qualifier, but fetchedAt/rights/scope remain
    # unresolved for real data. Never construct SourceContract from this manifest.
    rows = result['binding']['metadataReferenceRecords']
    packets = b''.join(canonical([row]) for row in rows)
    files['metadata-candidate.jsonl'] = packets
    manifest = {'schemaVersion': 'offmenu-portfolio63-metadata-bundle/1',
                'country': spec['country'], 'sourceKey': spec['sourceKey'],
                'bindingContentSHA256': result['bindingContentSHA256'],
                'inputFiles': inputs, 'metadataRecords': len(rows),
                'metadataCandidateSHA256': hashlib.sha256(packets).hexdigest(),
                'sourceDataRecordsNormalized': 0, 'sourceAcceptance': False,
                'productionAdmissionInstalled': False,
                'fetchedAtMeaning': 'null means unqualified source acquisition; validation never fills it'}
    files['manifest.json'] = canonical(manifest)
    target = safe_path(destination)
    if target.exists():
        actual = bundle_files(target, set(files))
        if actual != set(files):
            raise RefreshError('metadata-stage-generation-conflict')
        for name, raw in files.items():
            if safe_path(target/name).read_bytes() != raw:
                raise RefreshError('metadata-stage-generation-conflict')
        return {'status': 'unchanged-no-op', 'metadataRecords': len(rows), 'sourceAcceptance': False}
    # Output root is a caller-owned, new generation; originals are not resolved.
    target.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        path = safe_path(target/name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    return {'status': 'metadata-declarations-staged', 'metadataRecords': len(rows), 'sourceAcceptance': False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--now', required=True, help='Explicit UTC validation clock; never acquisition age.')
    p.add_argument('--previous', type=Path, help='Previous binding-report metadata, not source data.')
    p.add_argument('--output', type=Path)
    p.add_argument('--metadata-output-root', type=Path, help='New caller-owned metadata-only bundle generation.')
    a = p.parse_args(argv)
    try:
        config = strict_json(CONFIG.read_bytes())
        previous = strict_json(read_metadata(a.previous)[0]) if a.previous else None
        report = evaluate_portfolio(config, now=a.now, previous=previous)
        if a.metadata_output_root:
            for spec, result in zip(config['bindings'], report['results']):
                try:
                    result['metadataStage'] = stage_metadata(spec, result, a.metadata_output_root/spec['country'])
                except (OSError, KeyError, ValueError):
                    result['metadataStage'] = {'status': 'metadata-stage-failed', 'code': 'metadata-stage-input-or-output-invalid', 'sourceAcceptance': False}
        if a.output:
            write_if_changed(a.output, report)
        else:
            sys.stdout.buffer.write(canonical(report))
        # Valid metadata does not clear real source holds; this is expected exit2.
        return 2
    except (OSError, ValueError, KeyError, TypeError):
        sys.stdout.write(json.dumps({'status': 'malformed-input', 'code': 'binding-request-invalid'})+'\n')
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
