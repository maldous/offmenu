"""AO/IL/PM metadata binding seam; never downloads, opens source bodies or admits data."""
import argparse
import copy
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

from .refresh.core import RefreshError, canonical, sha, strict_json, timestamp, safe_path
from .refresh.field_provenance import field_origin_errors
from .refresh import core, field_provenance
from .refresh import serialization

SCHEMA = 'offmenu-owner02-metadata-binding/1'
TYPES = frozenset(('ingredients', 'recipes', 'nutrition', 'retailers/providers',
                   'prices/baskets', 'dietary references'))
DIGEST = re.compile(r'[0-9a-f]{64}')
MAX_METADATA_BYTES = 2 * 1024 * 1024


def _implementation_key():
    # Fingerprint executable source, never source-publication payloads.
    return sha(canonical({name: sha(Path(path).read_bytes()) for name, path in (
        ('portfolio', __file__), ('core', core.__file__),
        ('field_provenance', field_provenance.__file__),
        ('serialization', serialization.__file__))}))


def _relative(path):
    return (isinstance(path, str) and bool(path) and '\\' not in path
            and ':' not in path and not PurePosixPath(path).is_absolute()
            and '..' not in path.split('/') and path == PurePosixPath(path).as_posix())


def _pointer(document, pointer):
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise ValueError('invalid-selector')
    value = document
    for part in pointer[1:].split('/'):
        if re.search(r'~(?:[^01]|$)', part):
            raise ValueError('invalid-selector')
        key = part.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not key.isdecimal() or str(int(key)) != key:
                raise ValueError('invalid-selector')
            value = value[int(key)]
        else:
            value = value[key]
    return value


def evaluate_binding(spec, evidence, *, now, previous_key=None):
    """Bind caller-supplied *metadata* bytes only. No SourceContract is constructed.

    METADATA_READY describes a reproducible metadata candidate, never permission
    to parse/transform a publication. Real source-use/semantic acceptance belongs
    to independently reviewed shared SourceContract bindings at integration.
    """
    result = {'schemaVersion': SCHEMA, 'status': 'MALFORMED', 'diagnostics': [],
              'candidate': None, 'bindingKey': None, 'replay': 'not-produced',
              'cache': None, 'sourceProcessingAllowed': False,
              'countryAccepted': False, 'networkRequests': 0}
    errors = set()
    try:
        # Detach and enforce finite ordinary JSON, reusing shared serialization.
        spec = strict_json(canonical(spec))
        clock = timestamp(now)
        if not isinstance(spec, dict) or not isinstance(evidence, dict):
            raise ValueError('invalid-binding')
        if (spec.get('schemaVersion') != SCHEMA or spec.get('country') not in ('AO', 'IL', 'PM')
                or any(not isinstance(spec.get(k), str) or not spec[k]
                       for k in ('sourceId', 'releaseId', 'scope'))
                or not isinstance(spec.get('types'), list) or not spec['types']
                or not all(isinstance(t, str) and t in TYPES for t in spec['types'])
                or not isinstance(spec.get('fields'), dict) or not spec['fields']
                or not isinstance(spec.get('holds'), list)
                or not all(isinstance(h, str) and h for h in spec['holds'])
                or type(spec.get('scopeReady')) is not bool):
            raise ValueError('invalid-binding')
        pin = spec['metadata']
        if (not _relative(pin['logicalPath']) or not isinstance(pin['sha256'], str)
                or not DIGEST.fullmatch(pin['sha256']) or type(pin['bytes']) is not int
                or not 0 < pin['bytes'] <= MAX_METADATA_BYTES):
            raise ValueError('invalid-metadata-pin')
        raw = evidence.get(pin['logicalPath'])
        if raw is None:
            result.update(status='MISSING', diagnostics=['metadata-input-missing'])
            return result
        if not isinstance(raw, bytes) or len(raw) > MAX_METADATA_BYTES:
            raise ValueError('invalid-metadata-buffer')
        if len(raw) != pin['bytes'] or sha(raw) != pin['sha256']:
            result.update(status='STALE_INPUT', diagnostics=['metadata-input-pin-mismatch'])
            return result
        doc = strict_json(raw)
        if not isinstance(doc, dict) or doc.get('country') != spec['country']:
            raise ValueError('metadata-country-mismatch')
        # Local reviewed declaration identity, not a rights approval digest.
        policy_pin = sha(canonical(spec))
        data, origins = {}, {}
        for field, declaration in sorted(spec['fields'].items()):
            if not isinstance(field, str) or not field or not isinstance(declaration, dict):
                raise ValueError('invalid-field-declaration')
            target = '/data/' + field.replace('~', '~0').replace('/', '~1')
            if declaration.get('kind') == 'source':
                value = _pointer(doc, declaration['pointer'])
                if not (value is None or isinstance(value, (str, bool, int, float))):
                    raise ValueError('scalar-field-required')
                if 'expected' in declaration and (type(value) is not type(declaration['expected'])
                                                 or value != declaration['expected']):
                    errors.add('field-literal-mismatch')
                data[field] = value
                origins[target] = {'kind': 'source', 'sourceId': spec['sourceId'],
                    'releaseId': spec['releaseId'], 'inputPath': pin['logicalPath'],
                    'inputSha256': pin['sha256'], 'sourceRecordId': 'receipt',
                    'sourceField': declaration['pointer']}
            elif (declaration.get('kind') == 'unknown' and set(declaration) == {'kind', 'reason'}
                  and isinstance(declaration['reason'], str) and declaration['reason']):
                data[field] = None
                origins[target] = {'kind': 'constant', 'policySha256': policy_pin,
                                   'symbol': 'unknown:' + field}
            else:
                raise ValueError('invalid-field-declaration')
        acquired = (_pointer(doc, spec['acquisitionPointer'])
                    if spec.get('acquisitionPointer') is not None else None)
        candidate = {'id': spec['country'] + ':' + spec['sourceId'] + ':metadata',
            'kind': 'source-input-metadata', 'schemaVersion': SCHEMA, 'data': data,
            'provenance': {'sourceId': spec['sourceId'], 'releaseId': spec['releaseId'],
                           'fetchedAt': acquired, 'fieldOrigins': origins}}
        errors.update(field_origin_errors(candidate, {pin['logicalPath']: pin['sha256']},
                                         policy_pins=(policy_pin,)))
        cache = {'minimumReuseDays': 30, 'originalAcquiredAt': acquired,
                 'validatedAt': now, 'acquisitionAgeDays': None,
                 'decision': 'original-acquisition-unknown-no-download',
                 'metadataEvidenceBytesVerified': True, 'originalBodyBytesVerified': False,
                 'validationResetsAcquisitionAge': False, 'networkRequests': 0,
                 'retentionPermissionEstablished': False}
        if acquired is not None:
            age = (clock - timestamp(acquired)).total_seconds()
            if age < 0:
                raise ValueError('acquisition-in-future')
            cache.update(acquisitionAgeDays=int(age // 86400),
                decision='under-30days-no-download' if age < 30 * 86400
                else 'conditional-review-required-no-download')
        if not spec['scopeReady']:
            errors.add('content-selector-or-scope-not-qualified')
        if spec['holds']:
            errors.add('source-operation-held')
        if errors - {'content-selector-or-scope-not-qualified', 'source-operation-held'}:
            result.update(status='MALFORMED', diagnostics=sorted(errors))
            return result
        key = sha(canonical({'binding': spec, 'candidate': candidate,
                            'implementation': _implementation_key()}))
        result.update(status='HELD' if spec['holds'] else 'MISSING' if not spec['scopeReady']
                      else 'METADATA_READY', diagnostics=sorted(errors), candidate=candidate,
                      bindingKey=key, replay='no-op' if previous_key == key else 'metadata-candidate',
                      cache=cache, country=spec['country'], applicableTypes=copy.deepcopy(spec['types']),
                      metadataInput={k: pin[k] for k in ('logicalPath', 'sha256', 'bytes')},
                      interpretation='Metadata reference only; no body/semantic dataset acceptance.',
                      unknowns={k: v['reason'] for k, v in spec['fields'].items()
                                if v['kind'] == 'unknown'})
    except (RefreshError, ValueError, TypeError, KeyError, IndexError, UnicodeError, OverflowError):
        result.update(status='MALFORMED', diagnostics=['metadata-binding-invalid'])
    return result


def evaluate_portfolio(specs, evidence, *, now, previous_keys=None):
    """A bad source is isolated; peers still get their own typed diagnostic."""
    previous_keys = previous_keys or {}
    return [evaluate_binding(s, evidence, now=now,
                             previous_key=previous_keys.get(s['sourceId'])
                             if isinstance(s, dict) and isinstance(s.get('sourceId'), str)
                             else None)
            for s in specs]


def _read_retained_metadata(value):
    """Read one bounded regular descriptor; never reopen verified metadata."""
    path = safe_path(value)
    if path.suffix != '.json':
        raise RefreshError('metadata-json-path-required')
    # Anchor each directory before opening its child: a raced parent symlink
    # must not redirect the read after safe_path's initial checks.
    directory = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=directory)
            os.close(directory)
            directory = child
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW,
                             dir_fd=directory)
    finally:
        os.close(directory)
    with os.fdopen(descriptor, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_size > MAX_METADATA_BYTES):
            raise RefreshError('metadata-regular-bounded-file-required')
        raw = stream.read(MAX_METADATA_BYTES + 1)
        after = os.fstat(stream.fileno())
    fields = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink)
    if fields(before) != fields(after) or len(raw) != before.st_size or len(raw) > MAX_METADATA_BYTES:
        raise RefreshError('metadata-changed-or-too-large')
    return raw


def required_cells(specs):
    """Explicit contract inventory, not inferred applicability or completion."""
    return [{'country': country, 'type': kind,
             'sourceLeadIds': sorted(s['sourceId'] for s in specs
                                    if s['country'] == country and kind in s['types']),
             'applicability': 'unqualified-source-leads-only', 'accepted': False}
            for country in ('AO', 'IL', 'PM') for kind in sorted(TYPES)]


def metadata_artifact(results):
    """Shared singleton JSONL encoding of unadmitted metadata, including held leads."""
    rows = [r['candidate'] for r in results if r['candidate'] is not None]
    payload = serialization.encode_records(rows)
    return payload, {'schemaVersion': 'offmenu-owner02-metadata-artifact/1',
                     **serialization.asset(payload), 'metadataRecords': len(rows),
                     'sourceBodiesParsed': 0, 'qualification': 'unadmitted-metadata-only',
                     'inputs': [r['metadataInput'] for r in results if r['candidate'] is not None]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--now', required=True, help='Injected UTC validation time')
    parser.add_argument('--format', choices=('report', 'metadata-jsonl'), default='report')
    args = parser.parse_args(argv)
    from .portfolio_owner02_catalog import bindings
    specs = bindings()
    results = []
    for spec in specs:
        # Only pinned receipt JSON. Opaque original body paths are never opened.
        try:
            raw = _read_retained_metadata(spec['metadata']['retainedPath'])
            result = evaluate_binding(spec, {spec['metadata']['logicalPath']: raw}, now=args.now)
        except FileNotFoundError:
            result = evaluate_binding(spec, {}, now=args.now)
        except (OSError, RefreshError, ValueError, TypeError, KeyError):
            # Reuse the binding seam's fixed malformed diagnostic. An invalid
            # path never consumes another source's bytes or aborts its peers.
            result = evaluate_binding(None, {}, now=args.now)
        results.append(result)
    payload, manifest = metadata_artifact(results)
    if args.format == 'metadata-jsonl':
        print(payload.decode(), end='')
        return
    print(canonical({'schemaVersion': SCHEMA, 'countryAcceptance': False,
                     'requiredCells': required_cells(specs),
                     'metadataArtifact': manifest, 'results': results}).decode(), end='')


if __name__ == '__main__':
    main()
