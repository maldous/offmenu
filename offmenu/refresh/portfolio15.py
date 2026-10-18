"""BD/BE/BF/BG metadata bindings; never a source-body adapter or admission.

Contracts come from the reviewed portfolio catalog, not discovery or CLI URLs.
Only pinned JSON metadata is read. Corpus paths inside it remain opaque.
"""
from copy import deepcopy
import argparse
import os
import stat
import re

from .acquisition import MIN_TTL
from .adapter_mapping import retained_adapters
from .core import RefreshError, canonical, safe_path, sha, strict_json, timestamp
from .field_provenance import field_origin_errors
from .acceptance import assess_cells
from .portfolio15_catalogue import CATALOGUE

COUNTRIES = frozenset(('BD', 'BE', 'BF', 'BG'))
TYPES = frozenset(('ingredients', 'recipes', 'nutrition', 'retailers/providers',
                   'prices/baskets', 'dietary references'))
MAX_METADATA = 1024 * 1024
MAX_METADATA_DEPTH = 64
VERSION = 'owner15-metadata-binding/1'
HEX = re.compile(r'[a-f0-9]{64}')


class _MetadataDepthExceeded(RefreshError):
    """A fixed structural bound, independent of the Python recursion limit."""


def _metadata_json(raw):
    # Bound containers before the shared recursive decoder/canonicalizer. JSON
    # syntax remains the shared decoder's job; brackets within strings do not count.
    depth, quoted, escaped = 0, False, False
    for char in raw:
        if quoted:
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                quoted = False
        elif char == 34:
            quoted = True
        elif char in (91, 123):
            depth += 1
            if depth > MAX_METADATA_DEPTH:
                raise _MetadataDepthExceeded('metadata-depth-limit-exceeded')
        elif char in (93, 125):
            depth -= 1
    return strict_json(raw)


def _pointer(value, pointer):
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise RefreshError('selector-invalid')
    for token in pointer[1:].split('/'):
        if re.search(r'~(?![01])', token):
            raise RefreshError('selector-invalid')
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', token):
                raise RefreshError('selector-invalid')
            value = value[int(token)]
        else:
            value = value[token]
    return value


def _valid_contract(binding):
    if (not isinstance(binding, dict) or binding.get('country') not in COUNTRIES
            or not isinstance(binding.get('types'), list) or not binding['types']
            or not set(binding['types']) <= TYPES
            or any(not isinstance(binding.get(k), str) or not binding[k]
                   for k in ('id', 'sourceId', 'releaseId', 'sourceRecordId'))
            or not isinstance(binding.get('sourceHolds'), list)
            or not all(isinstance(x, str) and x for x in binding['sourceHolds'])
            or type(binding.get('metadataHeld')) is not bool
            or not isinstance(binding.get('evidence'), dict) or not binding['evidence']
            or len(binding['evidence']) > 8
            or not isinstance(binding.get('fields'), dict) or not binding['fields']
            or len(binding['fields']) > 32):
        raise RefreshError('binding-contract-invalid')
    selector = binding.get('countrySelector')
    if (not isinstance(selector, dict) or selector.get('evidence') not in binding['evidence']
            or not isinstance(selector.get('pointer'), str)):
        raise RefreshError('country-selector-invalid')
    for key, item in binding['evidence'].items():
        if (not isinstance(key, str) or not re.fullmatch('[a-z][a-z0-9-]*', key)
                or not isinstance(item, dict)
                or not isinstance(item.get('sha256'), str) or not HEX.fullmatch(item['sha256'])
                or type(item.get('bytes')) is not int
                or not 1 <= item['bytes'] <= MAX_METADATA
                or not isinstance(item.get('recordedPath'), str)
                or not item['recordedPath'].endswith('.json')):
            raise RefreshError('metadata-pin-invalid')
    for name, field in binding['fields'].items():
        if not isinstance(name, str) or not re.fullmatch('[A-Za-z][A-Za-z0-9]*', name):
            raise RefreshError('field-name-invalid')
        if not isinstance(field, dict) or field.get('kind') not in ('source', 'constant'):
            raise RefreshError('field-contract-invalid')
        if (not isinstance(field.get('types'), list) or not field['types']
                or not set(field['types']) <= {'string', 'number', 'boolean', 'null'}):
            raise RefreshError('field-type-contract-invalid')
        if field['kind'] == 'source':
            if field.get('evidence') not in binding['evidence'] or not isinstance(field.get('pointer'), str):
                raise RefreshError('selector-invalid')
        elif field.get('value') is not None:
            # Only reviewed unknown markers are synthesized, never source facts.
            raise RefreshError('constant-must-be-explicit-unknown')


def load_catalog():
    """Copy packaged inert declarations; no checkout resource or metadata I/O."""
    value = deepcopy(CATALOGUE)
    if value.get('schemaVersion') != VERSION or not isinstance(value.get('bindings'), list):
        raise RefreshError('catalog-invalid')
    ids = set()
    for binding in value['bindings']:
        _valid_contract(binding)
        if binding['id'] in ids:
            raise RefreshError('binding-identity-duplicate')
        ids.add(binding['id'])
    return value


def portfolio_requirements():
    """Use the shared assessor: metadata readiness never fills country cells."""
    return assess_cells((), (), countries=sorted(COUNTRIES), domains=sorted(TYPES))


def _read_pinned_metadata(item):
    """Owned regular-file boundary: one descriptor and bounded authenticated bytes."""
    directory = descriptor = None
    try:
        path = safe_path(item['recordedPath'])
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
        directory = os.open(path.anchor, flags | os.O_DIRECTORY)
        for component in path.parts[1:-1]:
            child = os.open(component, flags | os.O_DIRECTORY, dir_fd=directory)
            os.close(directory)
            directory = child
        descriptor = os.open(path.name, flags | os.O_NONBLOCK, dir_fd=directory)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise RefreshError('metadata-regular-file-required')
        if before.st_size > MAX_METADATA:
            raise RefreshError('metadata-size-limit-exceeded')
        chunks, remaining = [], MAX_METADATA + 1
        while remaining:
            chunk = os.read(descriptor, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b''.join(chunks)
        after = os.fstat(descriptor)
        if len(raw) > MAX_METADATA:
            raise RefreshError('metadata-size-limit-exceeded')
        identity = lambda st: (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
        if identity(before) != identity(after) or len(raw) != before.st_size:
            raise RefreshError('metadata-changed-during-read')
        if len(raw) != item['bytes'] or sha(raw) != item['sha256']:
            raise RefreshError('metadata-custody-mismatch')
        return raw
    except FileNotFoundError:
        return None  # Preserve existing missing-input outcome; never substitute.
    except OSError:
        raise RefreshError('metadata-open-or-read-refused') from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory is not None:
            os.close(directory)


def read_metadata(binding, *, operation='metadata-bind'):
    """Return only bounded pinned metadata bytes; holds precede filesystem I/O."""
    _valid_contract(binding)
    if operation != 'metadata-bind' or binding['metadataHeld']:
        return {}
    result = {}
    for key, item in binding['evidence'].items():
        raw = _read_pinned_metadata(item)
        if raw is not None:
            result[key] = raw
    return result


def plan(binding, inputs, *, now, operation='metadata-bind', previous_build=None):
    """Pure bounded report. Source-body parse/transform/acquire are always held.

    ``inputs`` are JSON-metadata bytes, not corpus files. No IO/network in this
    function. A ready report is a metadata staging binding, not qualified data.
    """
    result = {'schemaVersion': VERSION, 'bindingId': None, 'status': 'MALFORMED',
              'diagnostics': [], 'record': None, 'buildKey': None, 'replay': None,
              'cache': None, 'sourceHolds': [], 'bodyOperationSelected': False,
              'sourceBodyReads': 0, 'networkRequests': 0, 'countryComplete': False,
              'goldAdmitted': False, 'sourceAccepted': False,
              'sharedCapability': {'genericPureCachePlanner': 'UNAVAILABLE_AT_ABEC',
                                   'realBodyAdapter': 'UNSUPPORTED_FOR_THIS_METADATA_SCOPE'}}

    def stop(status, *codes):
        result.update(status=status, diagnostics=sorted(set(codes)))
        return result

    try:
        _valid_contract(binding)
        result['bindingId'] = binding['id']
        result['sourceHolds'] = list(binding['sourceHolds'])
        result['applicability'] = {'country': binding['country'], 'types': binding['types'],
                                   'meaning': binding.get('applicabilityNote'),
                                   'wholeCategoryAccepted': False}
        if operation != 'metadata-bind' or binding['metadataHeld']:
            return stop('HELD', 'body-operation-not-selected' if operation != 'metadata-bind'
                        else 'metadata-source-held')
        clock = timestamp(now)
        if not isinstance(inputs, dict):
            raise RefreshError('metadata-input-map-invalid')
        missing = set(binding['evidence']) - set(inputs)
        if missing:
            return stop('MISSING', 'metadata-input-missing')
        docs = {}
        for key, item in binding['evidence'].items():
            raw = inputs[key]
            if (not isinstance(raw, bytes) or len(raw) > MAX_METADATA
                    or len(raw) != item['bytes'] or sha(raw) != item['sha256']):
                raise RefreshError('metadata-custody-mismatch')
            docs[key] = _metadata_json(raw)
            canonical(docs[key])  # Reject overflowed numbers as well as NaN.
        try:
            selector = binding['countrySelector']
            if _pointer(docs[selector['evidence']], selector['pointer']) != binding['country']:
                return stop('MALFORMED', 'metadata-country-mismatch')
        except (KeyError, IndexError):
            return stop('MISSING', 'metadata-country-field-missing')
        policy = sha(canonical({'version': VERSION, 'id': binding['id'],
                                'fields': binding['fields']}))
        data, origins = {}, {}
        for name, field in binding['fields'].items():
            if field['kind'] == 'constant':
                value = None
                origin = {'kind': 'constant', 'policySha256': policy,
                          'symbol': 'unresolved-' + name}
            else:
                try:
                    value = _pointer(docs[field['evidence']], field['pointer'])
                except (KeyError, IndexError):
                    return stop('MISSING', 'metadata-field-missing')
                if isinstance(value, (dict, list)):
                    raise RefreshError('scalar-field-required')
                evidence = binding['evidence'][field['evidence']]
                origin = {'kind': 'source', 'sourceId': binding['sourceId'],
                          'releaseId': binding['releaseId'],
                          'inputPath': field['evidence'] + '.json',
                          'inputSha256': evidence['sha256'],
                          'sourceRecordId': binding['sourceRecordId'],
                          'sourceField': field['pointer']}
            scalar_type = ('null' if value is None else 'boolean' if type(value) is bool
                           else 'string' if isinstance(value, str) else 'number'
                           if type(value) in (int, float) else 'invalid')
            if scalar_type not in field['types']:
                return stop('MALFORMED', 'metadata-field-type-mismatch')
            data[name] = deepcopy(value)
            origins['/data/' + name] = origin
        row = {'id': binding['id'], 'kind': 'source-input-metadata-binding',
               'schemaVersion': VERSION, 'data': data,
               'provenance': {'sourceId': binding['sourceId'], 'releaseId': binding['releaseId'],
                              'fieldOrigins': origins}}
        errors = field_origin_errors(row, {key + '.json': value['sha256']
                                          for key, value in binding['evidence'].items()},
                                    policy_pins=(policy,))
        if errors:
            return stop('MALFORMED', *errors)
        result['record'] = row
        result['metadataManifestPins'] = {key + '.json': {k: item[k] for k in ('bytes', 'sha256')}
                                          for key, item in binding['evidence'].items()}
        result['sourceAssetClaim'] = deepcopy(binding.get('sourceAsset'))
        result['sourceAssetVerifiedByThisPlan'] = False
        cache = binding.get('cache')
        if not isinstance(cache, dict):
            raise RefreshError('cache-contract-invalid')
        acquired_selector = cache.get('originalAcquiredAt')
        if acquired_selector is None:
            return stop('MISSING', 'original-acquisition-evidence-missing')
        try:
            acquired_value = _pointer(docs[acquired_selector['evidence']], acquired_selector['pointer'])
            validated_selector = cache.get('lastValidatedAt')
            validated_value = (_pointer(docs[validated_selector['evidence']], validated_selector['pointer'])
                               if validated_selector is not None else None)
        except (KeyError, IndexError):
            return stop('MISSING', 'cache-evidence-field-missing')
        acquired = timestamp(acquired_value)
        validated = timestamp(validated_value) if validated_value is not None else None
        if acquired > clock or (validated is not None and not acquired <= validated <= clock):
            raise RefreshError('cache-clock-invalid')
        row['provenance']['fetchedAt'] = acquired_value
        result['sharedAdapterCandidates'] = [x['sourceId'] for x in retained_adapters()
                                             if x['sourceId'] == binding['sourceId']]
        # Replay covers the binding's nonvolatile claims, not only its candidate
        # record. Planning clocks and derived ages remain outside that identity.
        key = sha(canonical({'schemaVersion': VERSION, 'record': row,
                             'applicability': result['applicability'],
                             'sourceAssetClaim': result['sourceAssetClaim'],
                             'metadataManifestPins': result['metadataManifestPins'],
                             'sourceHolds': result['sourceHolds'],
                             'sharedCapability': result['sharedCapability'],
                             'sharedAdapterCandidates': result['sharedAdapterCandidates'],
                             'cacheContract': cache}))
        result.update(buildKey=key, replay='NO_OP' if previous_build == key else 'NEW_BINDING')
        age = int((clock - acquired).total_seconds())
        result['cache'] = {'originalAcquiredAt': acquired_value,
                           'originalAcquisitionMeaning': cache['meaning'],
                           'lastValidatedAt': validated_value,
                           'validationKind': cache.get('validationKind'),
                           'acquisitionAgeSeconds': age,
                           'validationAgeSeconds': int((clock - validated).total_seconds())
                           if validated is not None else None,
                           'minimumReuseSeconds': MIN_TTL,
                           'decision': 'REUSE_METADATA_ONLY_NO_DOWNLOAD' if age < MIN_TTL
                           else 'STALE_REVIEW_REQUIRED_NO_DOWNLOAD',
                           'validationResetsOriginalAcquisition': False,
                           'bodyCacheVerified': False, 'automaticDownloadAllowed': False}
        if age >= MIN_TTL:
            return stop('STALE', 'metadata-acquisition-age-at-least-30-days')
        result['status'] = 'READY_METADATA_ONLY'
        return result
    except (_MetadataDepthExceeded, RecursionError):
        # Discard partially assembled claims if another recursive operation fails.
        for name in ('applicability', 'sourceAssetClaim', 'metadataManifestPins'):
            result.pop(name, None)
        result.update(record=None, buildKey=None, replay=None, cache=None)
        return stop('MALFORMED', 'metadata-depth-limit-exceeded')
    except (RefreshError, KeyError, TypeError, ValueError, OverflowError):
        # No source values, paths, credentials or exception text in diagnostics.
        return stop('MALFORMED', 'binding-or-metadata-invalid')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binding', help='One reviewed catalog identity; default all six.')
    parser.add_argument('--now', required=True, help='Explicit UTC planning clock, no mtime.')
    parser.add_argument('--previous-build')
    parser.add_argument('--operation', default='metadata-bind')
    parser.add_argument('--coverage', action='store_true', help='Show 24 unaccepted shared-contract cells.')
    args = parser.parse_args()
    if args.coverage:
        print(canonical(portfolio_requirements()).decode(), end='')
        return
    selected = [b for b in load_catalog()['bindings'] if args.binding is None or b['id'] == args.binding]
    if not selected:
        parser.error('unknown binding')
    for binding in selected:
        try:
            inputs = read_metadata(binding, operation=args.operation)
            result = plan(binding, inputs, now=args.now, operation=args.operation,
                          previous_build=args.previous_build)
            output = canonical(result)
        except (OSError, RefreshError, RecursionError) as error:
            result = {'bindingId': binding['id'], 'status': 'MALFORMED',
                      'diagnostics': ['metadata-depth-limit-exceeded' if isinstance(error, RecursionError)
                                      else 'metadata-read-or-custody-invalid'],
                      'sourceBodyReads': 0, 'networkRequests': 0}
            output = canonical(result)
        print(output.decode(), end='')


if __name__ == '__main__':
    main()
