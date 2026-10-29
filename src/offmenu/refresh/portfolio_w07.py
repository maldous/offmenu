"""AQ/AR/AS/AT metadata bindings only; never open or authorize source bodies.

Shared SourceContract acceptance remains an independently reviewed caller boundary.
This module supplies metadata candidates and diagnostics, not SourceContracts.
"""
import argparse
import copy
import json
import os
import stat
from pathlib import Path

from .acquisition import MIN_TTL
from .core import RefreshError, canonical, safe_path, sha, strict_json, timestamp
from .field_provenance import datum_pointers, field_origin_errors
from .national_tabular import valid_input_name
from .reference_adapters import candidate_bytes

COUNTRIES = frozenset(('AQ', 'AR', 'AS', 'AT'))
TYPES = frozenset(('ingredients', 'recipes', 'nutrition', 'retailers/providers',
                   'prices/baskets', 'dietary references'))
MAX_METADATA = 262144
MAX_BINDINGS = 32


def read_metadata(path, *, limit=MAX_METADATA):
    """Bounded regular-file read through anchored, nonblocking no-follow handles."""
    path = safe_path(path)
    handles, ancestry = [], []
    signature = lambda st: (st.st_dev, st.st_ino, st.st_mode, st.st_size,
                            st.st_mtime_ns, st.st_ctime_ns)
    try:
        parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        handles.append(parent)
        for component in path.parts[1:-1]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=parent)
            handles.append(child)
            ancestry.append((parent, component, os.fstat(child)))
            parent = child
        before = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or not 0 <= before.st_size <= limit:
            raise RefreshError('w07-metadata-not-regular-or-bounded')
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        handles.append(fd)
        if signature(os.fstat(fd)) != signature(before):
            raise RefreshError('w07-metadata-changed-during-read')
        body = bytearray()
        while len(body) <= before.st_size:
            chunk = os.read(fd, min(65536, before.st_size - len(body) + 1))
            if not chunk:
                break
            body.extend(chunk)
        if (len(body) != before.st_size or signature(os.fstat(fd)) != signature(before)
                or signature(os.stat(path.name, dir_fd=parent, follow_symlinks=False)) != signature(before)):
            raise RefreshError('w07-metadata-changed-during-read')
        for ancestor, component, original in ancestry:
            current = os.stat(component, dir_fd=ancestor, follow_symlinks=False)
            if (current.st_dev, current.st_ino, current.st_mode) != (original.st_dev, original.st_ino, original.st_mode):
                raise RefreshError('w07-metadata-path-changed')
        return bytes(body)
    except OSError:
        raise RefreshError('w07-metadata-unavailable') from None
    finally:
        for fd in reversed(handles):
            os.close(fd)


def bounded_declaration(spec):
    # Iterative depth/node checks run before recursive copying or serialization,
    # including unknown fields. Cycles also hit this fixed depth bound.
    stack, nodes = [(spec, 0)], 0
    while stack:
        value, depth = stack.pop()
        nodes += 1
        if depth > 32 or nodes > 8192:
            raise RefreshError('w07-declaration-bounds-invalid')
        if isinstance(value, dict):
            if len(value) > 8192 or any(not isinstance(k, str) for k in value):
                raise RefreshError('w07-declaration-shape-invalid')
            stack.extend((v, depth + 1) for v in value.values())
        elif isinstance(value, list):
            if len(value) > 8192:
                raise RefreshError('w07-declaration-bounds-invalid')
            stack.extend((v, depth + 1) for v in value)
        elif value is not None and type(value) not in (str, bool, int, float):
            raise RefreshError('w07-declaration-shape-invalid')
    if len(canonical(spec)) > MAX_METADATA:
        raise RefreshError('w07-declaration-bounds-invalid')


def pointer(document, path):
    if not isinstance(path, str) or not path.startswith('/'):
        raise RefreshError('w07-selector-invalid')
    value = document
    for token in path[1:].split('/'):
        if '~' in token.replace('~0', '').replace('~1', ''):
            raise RefreshError('w07-selector-invalid')
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, dict):
            value = value[token]
        elif isinstance(value, list) and token.isascii() and token.isdecimal() and str(int(token)) == token:
            value = value[int(token)]
        else:
            raise KeyError(path)
    return value


def portable(spec):
    bounded_declaration(spec)
    result = copy.deepcopy(spec)
    if isinstance(result.get('manifest'), dict):
        result['manifest'].pop('localPath', None)
    return result


def validate_spec(spec):
    bounded_declaration(spec)
    if (not isinstance(spec, dict) or spec.get('country') not in COUNTRIES
            or spec.get('dataType') not in TYPES):
        raise RefreshError('w07-portfolio-scope-invalid')
    for key in ('bindingId', 'sourceId', 'releaseId', 'sourceRole'):
        if not isinstance(spec.get(key), str) or not spec[key] or len(spec[key]) > 512:
            raise RefreshError('w07-binding-identity-invalid')
    manifest = spec.get('manifest')
    if (not isinstance(manifest, dict) or not valid_input_name(manifest.get('path'))
            or type(manifest.get('bytes')) is not int or not 0 < manifest['bytes'] <= MAX_METADATA
            or not isinstance(manifest.get('sha256'), str)
            or len(manifest['sha256']) != 64
            or any(c not in '0123456789abcdef' for c in manifest['sha256'])):
        raise RefreshError('w07-metadata-pin-invalid')
    if spec.get('operation') != 'stage-retained-metadata' or spec.get('sourceDataOperations', []) != []:
        raise RefreshError('w07-source-body-operation-forbidden')
    fields = spec.get('fields')
    if not isinstance(fields, list) or not 1 <= len(fields) <= 32:
        raise RefreshError('w07-field-declarations-required')
    names = [f.get('name') for f in fields if isinstance(f, dict)]
    if (len(names) != len(fields) or len(set(names)) != len(names)
            or any(not isinstance(n, str) or not n or len(n) > 128 for n in names)):
        raise RefreshError('w07-field-declarations-invalid')
    if (spec.get('acquisitionKind') not in ('metadata-response', 'original-response-receipt')
            or spec.get('metadataUse') != 'permitted-retained-metadata'
            or spec.get('applicability') not in ('source-context-only', 'unknown', 'not-applicable-to-type')
            or not isinstance(spec.get('holds'), list)
            or any(not isinstance(x, str) or not x for x in spec['holds'])):
        raise RefreshError('w07-metadata-scope-invalid')
    return spec


def bind_one(spec, raw, *, now):
    """Pure bounded evaluation; raw must be the selected metadata, never data files."""
    result = {'bindingId': spec.get('bindingId') if isinstance(spec, dict) else None,
              'outcome': 'malformed', 'diagnostics': [], 'candidate': None,
              'countryDataAdmission': False, 'networkRequests': 0}
    try:
        validate_spec(spec)
        at = timestamp(now)
        pin = spec['manifest']
        if raw is None:
            result.update(outcome='missing', diagnostics=['w07-metadata-not-supplied'])
            return result
        if not isinstance(raw, bytes) or len(raw) > MAX_METADATA:
            raise RefreshError('w07-metadata-size-or-type-invalid')
        if len(raw) != pin['bytes'] or sha(raw) != pin['sha256']:
            result.update(outcome='stale-input', diagnostics=['w07-metadata-pin-changed'])
            return result
        document = strict_json(raw)
        if not isinstance(document, dict):
            raise RefreshError('w07-metadata-object-required')
        acquired_text = pointer(document, spec['acquiredAtSelector'])
        if acquired_text is None:
            raise KeyError('acquisition-unknown')
        acquired = timestamp(acquired_text)
        if acquired > at:
            raise RefreshError('w07-acquisition-in-future')
        policy = sha(canonical(portable(spec)))
        data, origins = {}, {}
        for field in spec['fields']:
            name = field['name']
            escaped = name.replace('~', '~0').replace('/', '~1')
            data[name] = {}
            for target, selector in [('value', field['selector']), ('unit', field.get('unitSelector')),
                                     ('basis', field.get('basisSelector'))]:
                value = pointer(document, selector) if selector is not None else None
                data[name][target] = value
                prefix = '/data/' + escaped + '/' + target
                for dest in datum_pointers(value, prefix):
                    origins[dest] = ({'kind': 'source', 'sourceId': spec['sourceId'],
                        'releaseId': spec['releaseId'], 'inputPath': pin['path'],
                        'inputSha256': pin['sha256'], 'sourceRecordId': spec['bindingId'],
                        'sourceField': selector + dest[len(prefix):]} if selector is not None else
                        {'kind': 'constant', 'policySha256': policy, 'symbol': 'explicit-unknown-' + target})
        row = {'id': 'w07:' + spec['bindingId'], 'kind': 'sourceInputBinding', 'schemaVersion': '1.0',
               'data': data, 'provenance': {'sourceId': spec['sourceId'], 'releaseId': spec['releaseId'],
                   'fetchedAt': acquired_text, 'fieldOrigins': origins}}
        errors = field_origin_errors(row, {pin['path']: pin['sha256']}, policy_pins=(policy,))
        if errors:
            raise RefreshError('w07-shared-field-origin-validation-failed')
        age = (at - acquired).total_seconds()
        holds = list(spec['holds'])
        if spec['applicability'] != 'source-context-only':
            holds.append('w07-country-type-applicability-unqualified')
        result.update(candidate=row, outcome='held' if holds else 'valid', diagnostics=sorted(set(holds)),
                      country=spec['country'], dataType=spec['dataType'], sourceRole=spec['sourceRole'],
                      policySha256=policy, manifest={k: pin[k] for k in ('path', 'bytes', 'sha256')},
                      cache={'originalAcquiredAt': acquired_text, 'acquisitionKind': spec['acquisitionKind'],
                          'validatedAt': now, 'acquisitionAgeSeconds': age, 'minimumReuseSeconds': MIN_TTL,
                          'decision': 'reuse-retained-metadata-no-download' if age < MIN_TTL else
                                      'revalidation-evidence-required-no-download',
                          'mtimeUsed': False, 'validationResetsAcquisitionAge': False,
                          'sourceBodyReuseApproved': False})
        if age >= MIN_TTL:
            result['diagnostics'] = sorted(set(result['diagnostics'] + ['w07-metadata-validation-stale']))
            if not holds:
                result['outcome'] = 'stale-input'
    except (KeyError, IndexError):
        result.update(outcome='missing', diagnostics=['w07-declared-selector-missing'], candidate=None)
    except (ValueError, TypeError, OverflowError, RecursionError):
        # No exception text, file contents or arbitrary source identifiers leak.
        result.update(outcome='malformed', diagnostics=['w07-invalid-binding-or-metadata'], candidate=None)
    return result


def plan(bindings, evidence, *, now):
    if not isinstance(bindings, list) or not 1 <= len(bindings) <= MAX_BINDINGS:
        raise RefreshError('w07-binding-count-invalid')
    ids = [s.get('bindingId') for s in bindings if isinstance(s, dict)]
    if (len(ids) != len(bindings) or any(not isinstance(x, str) or not 1 <= len(x) <= 512 for x in ids)
            or len(set(ids)) != len(ids)):
        raise RefreshError('w07-duplicate-or-invalid-binding-id')
    results = [bind_one(s, evidence.get(s['bindingId']), now=now) for s in bindings]
    rows = [r['candidate'] for r in results if r['candidate'] is not None]
    content = candidate_bytes(rows)
    projections = []
    for spec in bindings:
        try:
            validate_spec(spec)
            projections.append(portable(spec))
        except (ValueError, TypeError, OverflowError, RecursionError):
            projections.append({'bindingId': spec['bindingId'], 'malformed': True})
    identity = sha(canonical({'bindings': projections, 'candidateSha256': sha(content)}))
    return {'schemaVersion': 'offmenu-w07-metadata-staging/1', 'bindingFingerprint': identity,
            'candidateJsonl': content.decode(), 'candidateSha256': sha(content), 'candidateBytes': len(content),
            'metadataRecords': len(rows), 'sourceDataRecords': 0, 'goldAdmitted': 0,
            'results': results, 'networkRequests': 0, 'countryAcceptance': False}


def write_metadata_stage(result, directory):
    """Immutable metadata output; replay verifies exact bytes before no-op."""
    directory = safe_path(directory)
    content = result['candidateJsonl'].encode()
    manifest = {'schemaVersion': result['schemaVersion'], 'bindingFingerprint': result['bindingFingerprint'],
                'candidateSha256': sha(content), 'candidateBytes': len(content),
                'metadataRecords': result['metadataRecords'], 'sourceDataRecords': 0, 'goldAdmitted': 0}
    if directory.exists():
        if not directory.is_dir() or {p.name for p in directory.iterdir()} != {'candidate.jsonl', 'manifest.json'}:
            raise RefreshError('w07-existing-stage-conflict')
        old = strict_json(read_metadata(directory / 'manifest.json'))
        if old != manifest:
            raise RefreshError('w07-existing-stage-conflict')
        actual = read_metadata(directory / 'candidate.jsonl', limit=len(content))
        if len(actual) != len(content) or sha(actual) != sha(content):
            raise RefreshError('w07-existing-stage-candidate-changed')
        return 'verified-metadata-no-op'
    directory.mkdir(parents=True)
    with (directory / 'candidate.jsonl').open('xb') as f:
        f.write(content)
    with (directory / 'manifest.json').open('xb') as f:
        f.write(canonical(manifest))
    return 'metadata-stage-created'


def _main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--now', required=True, help='explicit UTC validation time')
    parser.add_argument('--output', type=Path, help='new private metadata-only stage directory')
    args = parser.parse_args(argv)
    config_path = safe_path(args.config)
    config = strict_json(read_metadata(config_path))
    if not isinstance(config, dict) or config.get('schemaVersion') != 'offmenu-w07-bindings/1':
        raise RefreshError('w07-config-version-invalid')
    bindings = config['bindings']
    # Validate the bounded envelope before any metadata I/O.
    plan(bindings, {}, now=args.now)
    evidence, load_errors, protected = {}, {}, [config_path]
    for spec in bindings:
        try:
            validate_spec(spec)
            path = safe_path(spec['manifest']['localPath'])
            protected.append(path)
            if path.suffix != '.json':
                raise RefreshError('w07-json-metadata-only')
            evidence[spec['bindingId']] = read_metadata(path) if path.exists() else None
        except (KeyError, ValueError, TypeError, OSError):
            load_errors[spec['bindingId']] = 'w07-metadata-load-invalid'
    # Only selected bounded metadata is read; no downloader or source engine.
    result = plan(bindings, evidence, now=args.now)
    for item in result['results']:
        if item['bindingId'] in load_errors:
            item.update(outcome='malformed', diagnostics=[load_errors[item['bindingId']]])
    if args.output:
        out = safe_path(args.output)
        if any(p == out or p.is_relative_to(out) for p in protected):
            raise RefreshError('w07-input-output-overlap')
        result['stageAction'] = write_metadata_stage(result, out)
    print(canonical(result).decode(), end='')
    return 2 if any(r['outcome'] != 'valid' for r in result['results']) else 0


def main(argv=None):
    try:
        return _main(argv)
    except (KeyError, ValueError, TypeError, OSError, OverflowError, RecursionError):
        print(canonical({'schemaVersion': 'offmenu-w07-metadata-staging/1',
                         'outcome': 'malformed', 'diagnostics': ['w07-cli-input-or-stage-invalid'],
                         'sourceDataRecords': 0, 'goldAdmitted': 0,
                         'countryAcceptance': False, 'networkRequests': 0}).decode(), end='')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
