"""LV/LY/MA/MC metadata bindings over shared refresh contracts.

Only caller-supplied metadata bytes are inspected. No source paths are opened,
no parser/acquirer is invoked, and no SourceContract or admission is installed.
The optional cache planner is trusted application code, never a CLI plugin.
"""
import argparse
from copy import deepcopy
import os
from pathlib import Path
import re
import stat

from .acquisition import MIN_TTL
from .adapter_mapping import retained_adapters
from .core import RefreshError, canonical, safe_path, sha, strict_json, timestamp
from .field_provenance import datum_pointers, field_origin_errors
from .global_run import StageResult

COUNTRIES = ('LV', 'LY', 'MA', 'MC')
DATA_TYPES = ('ingredients', 'recipes', 'nutrition', 'retailers/providers',
              'prices/baskets', 'dietary references')
MAX_DOCUMENT = 256 * 1024
MAX_ENVELOPE = 2 * 1024 * 1024
DIGEST = re.compile(r'[0-9a-f]{64}')


def _pointer(document, pointer):
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise RefreshError('binding-selector-invalid')
    value = document
    for part in pointer[1:].split('/'):
        if re.search(r'~(?![01])', part):
            raise RefreshError('binding-selector-invalid')
        key = part.replace('~1', '/').replace('~0', '~')
        if isinstance(value, dict):
            value = value[key]
        elif isinstance(value, list) and re.fullmatch(r'0|[1-9][0-9]*', key):
            value = value[int(key)]
        else:
            raise KeyError(key)
    return value


def _config(config):
    if (not isinstance(config, dict)
            or config.get('schemaVersion') != 'offmenu-portfolio59-bindings/1'
            or config.get('countries') != list(COUNTRIES)
            or config.get('dataTypes') != list(DATA_TYPES)
            or not isinstance(config.get('sources'), list)
            or not 1 <= len(config['sources']) <= 8):
        raise RefreshError('portfolio59-config-invalid')
    ids = set()
    for source in config['sources']:
        if not isinstance(source, dict):
            raise RefreshError('portfolio59-source-invalid')
        for key in ('sourceId', 'releaseId', 'scope'):
            if not isinstance(source.get(key), str) or not source[key]:
                raise RefreshError('portfolio59-source-invalid')
        if source['sourceId'] in ids:
            raise RefreshError('portfolio59-source-duplicate')
        ids.add(source['sourceId'])
        if (not isinstance(source.get('sourceManifestSha256'), str)
                or not DIGEST.fullmatch(source['sourceManifestSha256'])
                or not isinstance(source.get('documents'), dict)
                or not 1 <= len(source['documents']) <= 12
                or not isinstance(source.get('fields'), dict)
                or not 1 <= len(source['fields']) <= 12
                or not isinstance(source.get('holds'), list)
                or any(not isinstance(h, str) or not h for h in source['holds'])
                or not isinstance(source.get('requiredInputs'), list)
                or any(not isinstance(h, str) or not h for h in source['requiredInputs'])
                or not isinstance(source.get('applicability'), dict)
                or not source['applicability']
                or not set(source['applicability']) <= set(COUNTRIES)):
            raise RefreshError('portfolio59-source-invalid')
        for country, types in source['applicability'].items():
            if (not isinstance(types, list) or not types
                    or any(not isinstance(t, str) for t in types) or len(types) != len(set(types))
                    or not set(types) <= set(DATA_TYPES)):
                raise RefreshError('portfolio59-applicability-invalid')
        for name, item in source['documents'].items():
            if (not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,47}\.json', name)
                    or not isinstance(item, dict)
                    or not isinstance(item.get('sha256'), str)
                    or not DIGEST.fullmatch(item['sha256'])
                    or not isinstance(item.get('path'), str)
                    or item.get('role') not in ('manifest', 'review', 'methodology')):
                raise RefreshError('portfolio59-document-invalid')
        if source['sourceManifestSha256'] not in {
                d['sha256'] for d in source['documents'].values()}:
            raise RefreshError('portfolio59-source-manifest-unbound')
        for name, declaration in source['fields'].items():
            if (not isinstance(name, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9]{0,47}', name)
                    or not isinstance(declaration, dict)
                    or declaration.get('document') not in source['documents']
                    or not isinstance(declaration.get('selector'), str)):
                raise RefreshError('portfolio59-field-invalid')
    requirements = config.get('countryRequirements', [])
    if not isinstance(requirements, list) or len(requirements) > 24:
        raise RefreshError('portfolio59-country-requirements-invalid')
    cells = set()
    for item in requirements:
        if not isinstance(item, dict):
            raise RefreshError('portfolio59-country-requirements-invalid')
        if not isinstance(item.get('country'), str) or not isinstance(item.get('dataType'), str):
            raise RefreshError('portfolio59-country-requirements-invalid')
        key = (item.get('country'), item.get('dataType'))
        evidence = item.get('evidence')
        if (key not in {(c, d) for c in COUNTRIES for d in DATA_TYPES}
                or key in cells or item.get('state') not in ('missing', 'held', 'pending')
                or not isinstance(item.get('missingInput'), str)
                or not isinstance(evidence, dict)
                or not isinstance(evidence.get('path'), str)
                or not isinstance(evidence.get('sha256'), str)
                or not DIGEST.fullmatch(evidence['sha256'])
                or not isinstance(evidence.get('selector'), str)):
            raise RefreshError('portfolio59-country-requirements-invalid')
        cells.add(key)


def _source(source, evidence, now, cache_planner, previous):
    diagnostics = set()
    documents = {}
    for name, item in sorted(source['documents'].items()):
        raw = evidence.get(item['path'])
        if raw is None:
            diagnostics.add('metadata-document-missing')
            continue
        if not isinstance(raw, bytes) or len(raw) > MAX_DOCUMENT:
            diagnostics.add('metadata-document-invalid')
            continue
        if sha(raw) != item['sha256']:
            diagnostics.add('metadata-input-stale')
            continue
        try:
            document = strict_json(raw)
            canonical(document)  # Also rejects overflowing finite-JSON exponents.
            documents[name] = document
        except (ValueError, UnicodeError, RecursionError):
            diagnostics.add('metadata-document-malformed')
    data, origins = {}, {}
    for name, declaration in sorted(source['fields'].items()):
        if declaration['document'] not in documents:
            continue
        try:
            value = _pointer(documents[declaration['document']], declaration['selector'])
        except (KeyError, IndexError, RefreshError):
            diagnostics.add('metadata-selector-missing')
            continue
        if 'expected' in declaration and value != declaration['expected']:
            diagnostics.add('metadata-declaration-mismatch')
        data[name] = deepcopy(value)
        prefix = '/data/' + name
        # These origins identify metadata cells, never previously unread raw cells.
        for pointer in datum_pointers(value, prefix):
            origins[pointer] = {
                'kind': 'source', 'sourceId': source['sourceId'],
                'releaseId': source['releaseId'], 'inputPath': declaration['document'],
                'inputSha256': source['documents'][declaration['document']]['sha256'],
                'sourceRecordId': 'retained-metadata',
                'sourceField': declaration['selector'] + pointer[len(prefix):],
            }
    row = {'id': 'portfolio59-metadata:' + source['sourceId'], 'data': data,
           'provenance': {'sourceId': source['sourceId'], 'releaseId': source['releaseId'],
                          'fieldOrigins': origins, 'originTier': 'metadata-only'}}
    if len(data) != len(source['fields']):
        diagnostics.add('metadata-field-inventory-incomplete')
    if data:
        diagnostics.update(field_origin_errors(
            row, {name: pin['sha256'] for name, pin in source['documents'].items()}))
    acquired, validated = source.get('originalAcquiredAt'), source.get('validatedAt')
    try:
        validation = timestamp(validated)
        if validation > now:
            diagnostics.add('validation-time-in-future')
        if acquired is None:
            diagnostics.add('original-acquisition-time-missing')
        else:
            acquisition = timestamp(acquired)
            if not acquisition <= validation <= now:
                diagnostics.add('acquisition-validation-order-invalid')
    except (ValueError, TypeError):
        diagnostics.add('acquisition-validation-time-invalid')
    cache = {'decision': 'shared-cache-planner-required',
             'minimumReuseSeconds': MIN_TTL, 'downloadAllowed': False,
             'originalAcquiredAt': acquired, 'validatedAt': validated,
             'validationResetsAcquisitionAge': False}
    # Source-wide identity excludes country consumption and validation age.
    identity = {k: source[k] for k in ('sourceId', 'releaseId', 'sourceManifestSha256')}
    source_key = sha(canonical(identity))
    if cache_planner is None:
        diagnostics.add('shared-cache-planner-required')
    elif acquired is not None and not diagnostics and not source['holds']:
        try:
            planned = cache_planner(deepcopy({**identity, 'sourceIdentityKey': source_key,
                                             'originalAcquiredAt': acquired,
                                             'validatedAt': validated}), now=now)
            if (not isinstance(planned, dict)
                    or set(planned) != {'decision', 'minimumReuseSeconds',
                                        'downloadAllowed', 'originalAcquiredAt'}
                    or planned.get('decision') not in ('reuse', 'revalidation-required')
                    or type(planned.get('minimumReuseSeconds')) is not int
                    or planned['minimumReuseSeconds'] < MIN_TTL
                    or planned.get('downloadAllowed') is not False
                    or planned.get('originalAcquiredAt') != acquired):
                diagnostics.add('shared-cache-planner-invalid')
            else:
                cache.update(planned)
                if planned['decision'] == 'revalidation-required':
                    diagnostics.add('cache-revalidation-required')
        except Exception:
            diagnostics.add('shared-cache-planner-failed')
    capabilities = {r['sourceId']: r for r in retained_adapters()}
    adapter = capabilities.get(source['sourceId'])
    if adapter is None:
        diagnostics.add('shared-source-adapter-unavailable')
    diagnostics.update(source['requiredInputs'])
    if source['holds']:
        diagnostics.add('source-scope-held')
    fingerprint = sha(canonical({'source': source, 'metadata': row}))
    status = ('held' if source['holds'] else 'failed' if any(
        code in diagnostics for code in ('metadata-document-invalid', 'metadata-document-malformed',
            'portfolio59-source-invalid', 'shared-cache-planner-invalid', 'shared-cache-planner-failed'))
        else 'unsupported' if diagnostics else 'succeeded')
    reused = (status == 'succeeded' and previous == fingerprint)
    receipt = StageResult('reused' if reused else status,
                          'metadata-binding-unchanged' if reused else
                          'metadata-binding-ready' if status == 'succeeded' else
                          'metadata-binding-incomplete', (fingerprint,)).receipt()
    metadata_errors = [code for code in diagnostics if code.startswith(('metadata-', 'field-origin'))]
    return {**identity, 'sourceIdentityKey': source_key, 'bindingFingerprint': fingerprint,
            'metadataBinding': {'bound': not metadata_errors and not source['holds'],
                                'diagnostics': sorted(metadata_errors),
                                'meaning': 'Metadata cells only; separate from downstream stage readiness'},
            'stage': receipt, 'diagnostics': sorted(diagnostics),
            'countryTypeApplicability': deepcopy(source['applicability']),
            'metadataRecord': row, 'fieldDeclarations': deepcopy(source['fields']),
            'metadataPins': deepcopy(source['documents']), 'cache': cache,
            'sharedAdapterDescriptor': adapter,
            'unknowns': deepcopy(source.get('unknowns', [])),
            'holds': list(source['holds']), 'dataBodyProcessingAllowed': False,
            'datasetAccepted': False}


def bind_portfolio(config, evidence, *, now, cache_planner=None, previous=None):
    """Pure metadata binding; no filesystem, source-body, AI or network callbacks.

    evidence maps declared metadata paths to exact bytes. A planner must be
    reviewed pure shared code. CLI deliberately has no planner/plugin loader.
    A successful metadata stage never means candidate normalization/acceptance.
    """
    _config(config)
    clock = timestamp(now)
    if not isinstance(evidence, dict) or (previous is not None and not isinstance(previous, dict)):
        raise RefreshError('portfolio59-evidence-invalid')
    declared = {p['path'] for s in config['sources'] for p in s['documents'].values()}
    if not set(evidence) <= declared:
        raise RefreshError('portfolio59-evidence-not-allowlisted')
    result = [_source(s, evidence, clock, cache_planner, (previous or {}).get(s['sourceId']))
              for s in sorted(config['sources'], key=lambda s: s['sourceId'])]
    requirements = {(r['country'], r['dataType']): r for r in config.get('countryRequirements', [])}
    cells = [{'country': country, 'dataType': kind,
              'sourceIds': [s['sourceId'] for s in result
                            if kind in s['countryTypeApplicability'].get(country, [])],
              'diagnostic': 'metadata-binding-only' if any(
                  kind in s['countryTypeApplicability'].get(country, []) for s in result)
                  else 'source-binding-missing',
              'retainedRequirement': deepcopy(requirements.get((country, kind))),
              'datasetAccepted': False}
             for country in COUNTRIES for kind in DATA_TYPES]
    return {'schemaVersion': 'offmenu-portfolio59-binding-report/1', 'sources': result,
            'countryTypes': cells, 'metadataOnly': True, 'sourceBodyReads': 0,
            'networkRequests': 0, 'aiCalls': 0, 'goldAdmissions': 0,
            'countryCompletion': False, 'sharedCoreChanged': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Portfolio59 metadata-only binding; no data processing.')
    parser.add_argument('--config', required=True)
    parser.add_argument('--metadata-envelope', required=True,
                        help='JSON map of declared metadata path to exact UTF-8 text; paths are never opened.')
    parser.add_argument('--now', required=True, help='Explicit UTC observation time for reproducibility.')
    args = parser.parse_args(argv)
    try:
        def load(path):
            # A FIFO must not block at open, including after a path-type race.
            descriptor = os.open(safe_path(path), os.O_RDONLY | os.O_NONBLOCK
                                 | os.O_NOFOLLOW | os.O_CLOEXEC)
            try:
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                    raise RefreshError('portfolio59-regular-metadata-required')
                with os.fdopen(descriptor, 'rb', closefd=False) as stream:
                    raw = stream.read(MAX_ENVELOPE + 1)
            finally:
                os.close(descriptor)
            if len(raw) > MAX_ENVELOPE:
                raise RefreshError('portfolio59-envelope-too-large')
            return strict_json(raw)
        config, envelope = load(args.config), load(args.metadata_envelope)
        if not isinstance(envelope, dict) or any(not isinstance(v, str) for v in envelope.values()):
            raise RefreshError('portfolio59-envelope-invalid')
        result = bind_portfolio(config, {k: v.encode('utf-8') for k, v in envelope.items()}, now=args.now)
        print(canonical(result).decode(), end='')
        return 0
    except (OSError, ValueError, TypeError, RecursionError, UnicodeError):
        print(canonical({'status': 'failed', 'diagnostics': ['portfolio59-input-invalid'],
                         'sourceBodyReads': 0, 'networkRequests': 0}).decode(), end='')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
