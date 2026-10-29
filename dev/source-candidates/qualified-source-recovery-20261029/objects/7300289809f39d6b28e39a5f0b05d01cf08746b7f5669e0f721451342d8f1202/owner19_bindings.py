"""Worker19 metadata-only bindings; never an acquisition or admission route.

The checked-in catalogue is application configuration requiring review. Retained
manifests supply evidence, never execution authority. Source-body paths are opaque.
"""
import argparse
from dataclasses import dataclass
import json
from pathlib import Path

from .core import RefreshError, canonical, safe_path, sha, strict_json, timestamp
from . import core, reference_adapters

CATALOGUE = Path(__file__).with_suffix('.json')
MAX_METADATA_BYTES = 1024 * 1024
MAX_BINDINGS = 16


@dataclass(frozen=True)
class MetadataReadFailure:
    code: str


def implementation_pins():
    """Hash only the three code files this binding actually composes."""
    return {module: sha(Path(path).read_bytes()) for module, path in (
        ('owner19_bindings', __file__), ('core', core.__file__),
        ('reference_adapters', reference_adapters.__file__))}


def pointer(document, selector):
    """Resolve an explicit RFC6901 selector without searching or guessing fields."""
    if selector == '':
        return document
    if not isinstance(selector, str) or not selector.startswith('/'):
        raise RefreshError('invalid-metadata-selector')
    current = document
    for part in selector[1:].split('/'):
        # Reject malformed escapes rather than normalizing them.
        if '~' in part.replace('~0', '').replace('~1', ''):
            raise RefreshError('invalid-metadata-selector')
        part = part.replace('~1', '/').replace('~0', '~')
        if isinstance(current, list):
            if not part.isascii() or not part.isdigit() or str(int(part)) != part:
                raise RefreshError('metadata-selector-missing')
            index = int(part)
            if index >= len(current):
                raise RefreshError('metadata-selector-missing')
            current = current[index]
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise RefreshError('metadata-selector-missing')
    return current


def catalogue():
    """Only the reviewed-code catalogue is selectable by the CLI."""
    value = strict_json(CATALOGUE.read_bytes())
    if (value['schemaVersion'] != 'offmenu-owner19-bindings/1'
            or len(value['bindings']) > MAX_BINDINGS
            or len({b['id'] for b in value['bindings']}) != len(value['bindings'])):
        raise RefreshError('invalid-owner19-catalogue')
    return value


def read_metadata(binding):
    """Read exactly the configured JSON metadata files, never referenced files.

    Bytes/headers/credential contents are never included in diagnostics. This is
    an opt-in read route for retained metadata, not a generic user-supplied path.
    """
    buffers = {}
    for artifact in binding['metadata']:
        try:
            path = safe_path(artifact['path'])
            if not path.is_file():
                buffers[artifact['key']] = None
            elif path.stat().st_size > MAX_METADATA_BYTES:
                buffers[artifact['key']] = b' ' * (MAX_METADATA_BYTES + 1)
            else:
                with path.open('rb') as stream:
                    buffers[artifact['key']] = stream.read(MAX_METADATA_BYTES + 1)
        except PermissionError:
            buffers[artifact['key']] = MetadataReadFailure('metadata-read-denied')
        except RefreshError:
            buffers[artifact['key']] = MetadataReadFailure('metadata-path-rejected')
        except OSError:
            buffers[artifact['key']] = MetadataReadFailure('metadata-read-failed')
    return buffers


def inspect_binding(binding, buffers, *, now, previous_key=None):
    """Bounded metadata preflight; reads its code identity but cannot stage data.

    `binding` is trusted application configuration, not a source manifest. Tests
    may supply authored configurations. A valid metadata result is not a grant.
    """
    observed = timestamp(now)
    errors = []
    documents = {}
    states = []
    for artifact in binding['metadata']:
        key = artifact['key']
        raw = buffers.get(key)
        state = {'key': key, 'expectedSha256': artifact['sha256'],
                 'metadataBytesVerified': False}
        if isinstance(raw, MetadataReadFailure):
            errors.append({'stage': 'metadata', 'artifact': key, 'code': raw.code})
        elif raw is None:
            errors.append({'stage': 'metadata', 'artifact': key, 'code': 'missing-metadata'})
        elif not isinstance(raw, bytes) or len(raw) > MAX_METADATA_BYTES:
            errors.append({'stage': 'metadata', 'artifact': key, 'code': 'metadata-limit-or-type'})
        else:
            try:
                # Parse before pin comparison to give malformed JSON its own
                # fixed diagnostic. Values are not emitted or interpreted yet.
                doc = strict_json(raw)
                if not isinstance(doc, dict):
                    raise RefreshError('metadata-object-required')
                canonical(doc)  # Also reject floating-point overflow to infinity.
                if sha(raw) != artifact['sha256']:
                    errors.append({'stage': 'metadata', 'artifact': key, 'code': 'stale-input-pin'})
                else:
                    state['metadataBytesVerified'] = True
                    documents[key] = doc
                    for assertion in artifact['assertions']:
                        actual = pointer(doc, assertion['selector'])
                        if canonical(actual) != canonical(assertion['equals']):
                            raise RefreshError('metadata-selector-value-mismatch')
            except (RefreshError, ValueError, TypeError, RecursionError):
                # No exception strings: input may contain private response text.
                errors.append({'stage': 'metadata', 'artifact': key, 'code': 'malformed-metadata'})
        states.append(state)

    # These clocks describe metadata inspection, not record/source validation.
    clock = {'originalAcquiredAt': None, 'acquisitionAgeDays': None,
             'metadataValidatedAt': now, 'acquisitionClockStatus': 'unknown',
             'minimumReuseDays': 30, 'revalidationResetsAcquisitionAge': False,
             'cacheReuseAuthorized': False, 'refreshAuthorized': False,
             'mtimeUsed': False, 'assetBytesVerified': False}
    origin = binding.get('acquisitionClock')
    if origin and origin['artifact'] in documents:
        try:
            literal = pointer(documents[origin['artifact']], origin['selector'])
            acquired = timestamp(literal)
            age = (observed - acquired).total_seconds()
            if age < 0:
                raise RefreshError('acquisition-timestamp-in-future')
            clock.update(originalAcquiredAt=literal, acquisitionAgeDays=int(age // 86400),
                         acquisitionClockStatus=('under-minimum-revalidation-age' if age < 30 * 86400
                                                 else 'revalidation-review-required'))
        except (RefreshError, ValueError, TypeError):
            errors.append({'stage': 'clock', 'artifact': origin['artifact'],
                           'code': 'invalid-original-acquisition-clock'})
    # Times and caller replay state are observations, not build identity inputs.
    code_pins = implementation_pins()
    build_key = sha(canonical({'binding': binding, 'code': code_pins,
                              'interface': 'owner19-metadata-preflight/1'}))
    integrity = ('missing' if any(e['code'] == 'missing-metadata' for e in errors) else
                 'stale' if any(e['code'] == 'stale-input-pin' for e in errors) else
                 'malformed' if errors else 'valid')
    if any(e['code'] == 'metadata-read-denied' for e in errors):
        integrity = 'blocked-access'
    elif any(e['code'] in ('metadata-read-failed', 'metadata-path-rejected') for e in errors):
        integrity = 'blocked-filesystem'
    holds = binding['holds']
    adapter = {'status': 'not-bound', 'bodyFormat': binding['inputFormat']}
    if binding.get('sharedReferenceSource'):
        contract = reference_adapters.CONTRACTS.get(binding['sourceId'])
        adapter.update(sharedInterface='reference_adapters.normalize_reference',
                       expectedSourceFormat=contract[1] if contract else None,
                       status=('source-format-mismatch' if contract and contract[0] == binding['releaseId']
                               and contract[1] != binding['inputFormat'] else 'unreviewed-binding'))
    return {'bindingId': binding['id'], 'country': binding['country'],
            'sourceId': binding['sourceId'], 'releaseId': binding['releaseId'],
            'types': binding['types'], 'metadataIntegrity': integrity,
            'status': integrity if errors else 'held' if holds else 'valid-metadata-only',
            'metadata': states, 'diagnostics': errors, 'holds': holds,
            'nativeBasis': binding['nativeBasis'], 'fieldDeclarations': binding['fieldDeclarations'],
            'recordInventory': binding['recordInventory'], 'clock': clock,
            'cachePolicy': {'status': 'shared-pure-planner-unavailable',
                            'decision': 'unknown-no-download',
                            'dependency': 'integrator00 result5798; proposed plan_retained_input only',
                            'clockAgeIsPermission': False},
            'adapter': adapter, 'buildKey': build_key, 'implementationPins': code_pins,
            'replay': ('no-op-unchanged-metadata' if previous_key == build_key and not errors
                       else 'diagnose-only'),
            'bodyReads': 0, 'networkRequests': 0, 'recordsParsed': 0, 'recordsStaged': 0,
            'sourceAdmission': 'not-enabled', 'productionAdmission': False,
            'countryComplete': False}


def inspect_portfolio(bindings, buffers, *, now, previous_keys=None):
    """Each binding fails independently; input contents never appear in errors."""
    timestamp(now)
    if len(bindings) > MAX_BINDINGS:
        raise RefreshError('owner19-binding-limit')
    results = []
    previous_keys = previous_keys or {}
    for binding in bindings:
        try:
            result = inspect_binding(binding, buffers.get(binding['id'], {}), now=now,
                                     previous_key=previous_keys.get(binding['id']))
        except (KeyError, TypeError, ValueError, RecursionError):
            result = {'bindingId': binding.get('id'), 'status': 'malformed',
                      'diagnostics': [{'stage': 'binding', 'code': 'invalid-binding-metadata'}],
                      'bodyReads': 0, 'networkRequests': 0, 'recordsStaged': 0,
                      'productionAdmission': False, 'countryComplete': False}
        results.append(result)
    return {'schemaVersion': 'offmenu-owner19-preflight/1', 'results': results,
            'scope': 'metadata/code; no record processing or acceptance',
            'countryComplete': False, 'productionAdmission': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--now', required=True, help='Explicit UTC metadata validation time')
    parser.add_argument('--retained-metadata', action='store_true',
                        help='Read only the pinned JSON metadata paths in the application catalogue')
    args = parser.parse_args(argv)
    try:
        bindings = catalogue()['bindings']
        buffers = {b['id']: read_metadata(b) for b in bindings} if args.retained_metadata else {}
        print(canonical(inspect_portfolio(bindings, buffers, now=args.now)).decode(), end='')
    except (RefreshError, ValueError, OSError, KeyError, TypeError):
        print(json.dumps({'error': 'invalid-owner19-preflight-request'}))
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
