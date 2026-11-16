"""CI/CK/CL/CM metadata staging bindings. Never opens or executes source bodies.

The installed configuration is application code pending independent review, not
a runtime permission file. No source contract, acceptance or GLOBAL binding is
installed. All public functions are deterministic for explicit inputs and clock.
"""
import argparse
from contextlib import ExitStack
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import stat

from .. import core, field_provenance
from ..acceptance import fingerprint

MAX_METADATA_BYTES = 256 * 1024
MIN_REUSE_SECONDS = 30 * 86400
CONFIG = Path(__file__).with_suffix('.json')
HEX = re.compile('[0-9a-f]{64}')


def registry():
    return core.strict_json(CONFIG.read_bytes())


def runtime_pins():
    """Bind replay identity to the portfolio and reused validator code bytes."""
    return {name: core.sha(Path(module).read_bytes()) for name, module in (
        ('worker23', __file__), ('core', core.__file__),
        ('field_provenance', field_provenance.__file__),
        ('acceptance', str(Path(__file__).parents[1] / 'acceptance.py')))}


def pointer(document, selector):
    """Resolve an RFC6901 object/array pointer, without expression evaluation."""
    if not isinstance(selector, str) or not selector.startswith('/'):
        raise ValueError('selector-invalid')
    value = document
    for part in selector[1:].split('/'):
        if re.search(r'~(?![01])', part):
            raise ValueError('selector-invalid')
        part = part.replace('~1', '/').replace('~0', '~')
        if isinstance(value, dict):
            value = value[part]
        elif isinstance(value, list) and re.fullmatch(r'0|[1-9][0-9]*', part):
            value = value[int(part)]
        else:
            raise ValueError('selector-invalid')
    if isinstance(value, (dict, list)):
        raise ValueError('selector-must-be-scalar')
    return value


def cache_plan(original_acquired_at, validated_at, *, now):
    """Metadata plan only; validation never refreshes original acquisition age."""
    clock = core.timestamp(now)
    result = {'originalAcquiredAt': original_acquired_at,
              'metadataValidatedAt': validated_at, 'acquisitionAgeSeconds': None,
              'validationAgeSeconds': None, 'evaluatedAt': now,
              'minimumReuseDays': 30, 'networkRequests': 0,
              'validationResetsAcquisitionAge': False,
              'bodyCacheVerified': False, 'refreshAuthorized': False}
    acquired = core.timestamp(original_acquired_at) if original_acquired_at else None
    validated = core.timestamp(validated_at) if validated_at else None
    if acquired and acquired > clock or validated and validated > clock:
        raise ValueError('timestamp-in-future')
    if acquired and validated and validated < acquired:
        raise ValueError('validation-before-acquisition')
    if validated is not None:
        result['validationAgeSeconds'] = int((clock - validated).total_seconds())
    if acquired is None:
        result.update(status='missing', decision='original-acquisition-evidence-missing')
    else:
        age = int((clock - acquired).total_seconds())
        result.update(acquisitionAgeSeconds=age,
                      status='valid' if age < MIN_REUSE_SECONDS else 'stale-input',
                      decision='reuse-retained-no-download' if age < MIN_REUSE_SECONDS
                      else 'conditional-review-required-no-download')
    return result


def assess(spec, raw, *, now, operation='metadata', previous_key=None, code_pins=None,
           acquisition_raw=None):
    """One isolated source result; raw is exact retained METADATA bytes only.

    Holds concern payload operations and never erase a valid metadata projection.
    Freshness alone is never evidence that retained source bodies are verified.
    """
    result = {'bindingId': spec['id'], 'country': spec['country'],
              'status': None, 'diagnostics': [], 'packet': None,
              'contentKey': None, 'replay': 'none', 'networkRequests': 0,
              'payloadOperationAuthorized': False, 'acceptedRecords': 0,
              'countryComplete': False, 'payloadHolds': list(spec['payloadHolds'])}
    try:
        if operation not in ('metadata', 'payload-stage'):
            raise ValueError('operation-invalid')
        if previous_key is not None and not HEX.fullmatch(previous_key):
            raise ValueError('previous-key-invalid')
        if raw is None:
            result.update(status='missing', diagnostics=['metadata-input-missing'])
            return result
        asset = spec['metadataAsset']
        if (not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_METADATA_BYTES
                or asset['role'] != 'retained-metadata'):
            raise ValueError('metadata-input-invalid')
        if len(raw) != asset['bytes'] or core.sha(raw) != asset['sha256']:
            raise ValueError('metadata-pin-mismatch')
        document = core.strict_json(raw)
        if not isinstance(document, dict):
            raise ValueError('metadata-object-required')
        if document.get('country') != spec['country']:
            raise ValueError('metadata-country-mismatch')
        evidence = spec.get('acquisitionEvidence')
        if evidence:
            acquisition_raw = raw if evidence['path'] == asset['path'] else acquisition_raw
            if acquisition_raw is None:
                result.update(status='missing', diagnostics=['acquisition-metadata-missing'])
                return result
            if (not isinstance(acquisition_raw, bytes)
                    or len(acquisition_raw) > MAX_METADATA_BYTES
                    or core.sha(acquisition_raw) != evidence['sha256']):
                raise ValueError('acquisition-evidence-pin-mismatch')
            acquisition_doc = core.strict_json(acquisition_raw)
            actual = pointer(acquisition_doc, evidence['selector'])
            if core.timestamp(actual) != core.timestamp(spec['originalAcquiredAt']):
                raise ValueError('acquisition-timestamp-mismatch')
        data = {key: pointer(document, selector)
                for key, selector in spec['selectors'].items()}
        alias = 'retained-metadata.json'
        origins = {'/data/' + key.replace('~', '~0').replace('/', '~1'): {
            'kind': 'source', 'sourceId': spec['sourceId'],
            'releaseId': spec['releaseId'], 'inputPath': alias,
            'inputSha256': asset['sha256'], 'sourceRecordId': spec['id'],
            'sourceField': selector} for key, selector in spec['selectors'].items()}
        packet = {'id': spec['id'], 'kind': 'retained-source-metadata',
                  'schemaVersion': 'offmenu-worker23-metadata/1', 'data': data,
                  'provenance': {'sourceId': spec['sourceId'],
                                 'releaseId': spec['releaseId'],
                                 'fetchedAt': spec['originalAcquiredAt'],
                                 'fieldOrigins': origins},
                  'nativeSemantics': deepcopy(spec['nativeSemantics']),
                  'scope': 'retained-metadata-only'}
        errors = field_provenance.field_origin_errors(packet, {alias: asset['sha256']})
        if errors:
            result.update(status='malformed', diagnostics=errors)
            return result
        cache = cache_plan(spec['originalAcquiredAt'], spec['metadataValidatedAt'], now=now)
        content_spec = {key: value for key, value in spec.items() if key != 'metadataValidatedAt'}
        key = fingerprint({'packet': packet, 'binding': content_spec,
                           'codePins': code_pins if code_pins is not None else runtime_pins()})
        result.update(packet=packet, cache=cache, contentKey=key,
                      replay='no-op' if previous_key == key else 'metadata-packet-ready',
                      emitPacket=previous_key != key,
                      status='valid')
        if operation == 'payload-stage':
            if spec['payloadHolds']:
                result.update(status='held', diagnostics=['payload-operation-held'])
            elif cache['status'] != 'valid':
                result.update(status=cache['status'], diagnostics=[cache['decision']])
            else:
                # Metadata-only code can never manufacture a payload adapter.
                result.update(status='missing', diagnostics=['payload-adapter-not-bound'])
        return result
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError):
        # Never expose parser messages, response bodies, credentials or paths.
        result.update(status='malformed', diagnostics=['metadata-contract-invalid'])
        return result


def _read_metadata(path):
    """Bound a read to no-follow directory/file descriptors on the local filesystem.

    Nonblocking open prevents a replacement FIFO from hanging before fstat.
    Name/descriptor custody is checked around the same bounded descriptor read;
    no stat-then-path-open or verify-then-reopen read is used.
    """
    path = Path(os.path.abspath(path))
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    file_flags = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC

    def identity(value):
        return (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
                value.st_size, value.st_mtime_ns, value.st_ctime_ns)

    def inode(value):
        return value.st_dev, value.st_ino, value.st_mode

    with ExitStack() as descriptors:
        def opened(name, flags, *, parent=None):
            descriptor = os.open(name, flags, dir_fd=parent)
            descriptors.callback(os.close, descriptor)
            return descriptor

        parent = opened(path.anchor, directory_flags)
        ancestors = []
        for part in path.parts[1:-1]:
            before = os.stat(part, dir_fd=parent, follow_symlinks=False)
            child = opened(part, directory_flags, parent=parent)
            current = os.fstat(child)
            if inode(before) != inode(current):
                raise core.RefreshError('metadata-directory-changed')
            ancestors.append((parent, part, inode(current)))
            parent = child
        before = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        descriptor = opened(path.name, file_flags, parent=parent)
        current = os.fstat(descriptor)
        if (not stat.S_ISREG(current.st_mode) or identity(before) != identity(current)
                or current.st_size > MAX_METADATA_BYTES):
            raise core.RefreshError('metadata-input-invalid')
        chunks = []
        size = 0
        while size <= MAX_METADATA_BYTES:
            chunk = os.read(descriptor, min(65536, MAX_METADATA_BYTES + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        after = os.fstat(descriptor)
        name_now = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        if (size > MAX_METADATA_BYTES or size != current.st_size
                or identity(current) != identity(after)
                or identity(after) != identity(name_now)):
            raise core.RefreshError('metadata-changed-during-read')
        for directory, name, expected in ancestors:
            if inode(os.stat(name, dir_fd=directory, follow_symlinks=False)) != expected:
                raise core.RefreshError('metadata-directory-changed')
        return b''.join(chunks)


def run(*, now, operation='metadata', previous_keys=None):
    """Read only the fixed installed metadata allowlist, not upstream paths.

    Never follows embedded source-body pointers or discovers neighbouring files.
    Independent file/parse failures do not prevent peer source results.
    """
    specs = registry()['sources']
    loaded = {}
    results = []
    def read(path):
        if path not in loaded:
            try:
                loaded[path] = (_read_metadata(path), None)
            except FileNotFoundError:
                loaded[path] = (None, None)
            except (OSError, core.RefreshError):
                loaded[path] = (None, 'metadata-read-failed')
        return loaded[path]

    for spec in sorted(specs, key=lambda item: item['id']):
        raw, failure = read(spec['metadataAsset']['path'])
        acquisition_raw = None
        if spec.get('acquisitionEvidence'):
            acquisition_raw, acquisition_failure = read(spec['acquisitionEvidence']['path'])
            failure = failure or acquisition_failure
        row = assess(spec, raw, now=now, operation=operation,
                     previous_key=(previous_keys or {}).get(spec['id']),
                     acquisition_raw=acquisition_raw)
        if failure:
            row.update(status='malformed', diagnostics=[failure])
        results.append(row)
    return {'schemaVersion': 'offmenu-worker23-binding-report/1',
            'scope': 'retained-metadata-only', 'operation': operation,
            'sources': results, 'networkRequests': 0, 'acceptedRecords': 0,
            'countryComplete': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--now', required=True, help='Explicit UTC ISO timestamp')
    parser.add_argument('--operation', choices=('metadata', 'payload-stage'), default='metadata')
    parser.add_argument('--previous-key', action='append', default=[], metavar='BINDING_ID=SHA256',
                        help='Prior exact content key, not a file or permission')
    args = parser.parse_args(argv)
    previous = {}
    ids = {row['id'] for row in registry()['sources']}
    for value in args.previous_key:
        binding_id, separator, key = value.partition('=')
        if not separator or binding_id not in ids or binding_id in previous or not HEX.fullmatch(key):
            parser.error('invalid-previous-key')
        previous[binding_id] = key
    report = run(now=args.now, operation=args.operation, previous_keys=previous)
    print(json.dumps(report, sort_keys=True, ensure_ascii=False, allow_nan=False))
    return 0 if all(row['status'] == 'valid' for row in report['sources']) else 2


if __name__ == '__main__':
    raise SystemExit(main())
