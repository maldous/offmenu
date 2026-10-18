"""IT/IS/JE/JM metadata bindings. No body parser, downloader or admission.

The catalog is reviewed code configuration. External descriptors cannot supply
rights, remove holds or construct SourceContracts. Referenced body paths are
informational and never opened. Shared validators remain authoritative.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import stat

from .core import canonical, sha, strict_json, timestamp
from .field_provenance import field_origin_errors
from .portfolio45_catalog import CATALOG

MAX_BYTES = 32768
MAX_JSON_DEPTH = 48
KEYS = {'bindingId', 'row', 'inputSha256', 'manifestSha256',
        'originalAcquiredAt', 'validatedAt', 'priorReplayKey'}


class MetadataNestingError(ValueError):
    """Explicit ingress depth violation, independent of decoder recursion."""


def load_metadata_json(raw):
    """Bound serialized container nesting before the shared JSON decoder.

Only JSON structural bytes outside strings contribute to depth; escaped quotes
and backslashes do not end strings. Full syntax/UTF-8/duplicate-key validation
stays with strict_json. This does not depend on a Python recursion threshold.
"""
    if not isinstance(raw, bytes) or len(raw) > 16 * MAX_BYTES:
        raise ValueError('metadata-json-byte-bound')
    depth, in_string, escaped = 0, False, False
    for byte in raw:
        if in_string:
            if escaped:
                escaped = False
            elif byte == 92:  # backslash
                escaped = True
            elif byte == 34:  # quote
                in_string = False
        elif byte == 34:
            in_string = True
        elif byte in (91, 123):  # array/object open
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise MetadataNestingError('json-nesting-limit')
        elif byte in (93, 125):
            depth -= 1
    return strict_json(raw)


def read_metadata_input(path):
    """Open once through no-follow directories; read only a bounded regular FD.

No Path.stat/read_bytes check-then-reopen. Nonblocking open rejects FIFO/device
inputs before reads; ancestor descriptors prevent directory-link substitution.
The opened inode must remain regular, singly linked and unchanged throughout.
"""
    path = Path(path).absolute()
    if '..' in path.parts or not path.name:
        raise ValueError('metadata-path-invalid')
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    parent = os.open('/', flags | os.O_DIRECTORY)
    fd = None
    limit = 16 * MAX_BYTES
    try:
        for component in path.parts[1:-1]:
            child = os.open(component, flags | os.O_DIRECTORY, dir_fd=parent)
            os.close(parent)
            parent = child
        fd = os.open(path.name, flags, dir_fd=parent)
        before = os.fstat(fd)
        def identity(info):
            return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
                    info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or not 0 < before.st_size <= limit
                or identity(os.stat(path.name, dir_fd=parent, follow_symlinks=False)) != identity(before)):
            raise ValueError('metadata-inode-or-bound-invalid')
        blocks, size = [], 0
        while size <= limit:
            block = os.read(fd, min(65536, limit + 1 - size))
            if not block:
                break
            blocks.append(block)
            size += len(block)
        if (not 0 < size <= limit or size != before.st_size
                or identity(os.fstat(fd)) != identity(before)
                or identity(os.stat(path.name, dir_fd=parent, follow_symlinks=False)) != identity(before)):
            raise ValueError('metadata-input-changed-or-too-large')
        return b''.join(blocks)
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def catalog():
    return copy.deepcopy(CATALOG)


def template(binding):
    """A declaration from pinned metadata, not proof of current source bytes."""
    row = {'data': copy.deepcopy(binding['metadataValues']), 'provenance': {
        'sourceId': binding['sourceId'], 'releaseId': binding['releaseId'],
        'fieldOrigins': {}}}
    for field, selector in binding['selectors'].items():
        row['provenance']['fieldOrigins']['/data/' + field] = {
            'kind': 'source', 'sourceId': binding['sourceId'],
            'releaseId': binding['releaseId'], 'inputPath': 'evidence.json',
            'inputSha256': binding['manifest']['sha256'],
            'sourceRecordId': '/', 'sourceField': selector}
    return {'bindingId': binding['id'], 'row': row,
            'inputSha256': binding['input']['sha256'],
            'manifestSha256': binding['manifest']['sha256'],
            'originalAcquiredAt': binding['originalAcquiredAt'],
            'validatedAt': None, 'priorReplayKey': None}


def assess(binding, descriptor, *, as_of):
    """Inspect one bounded metadata envelope; errors never trigger source I/O.

Binding must come from trusted application configuration, never an input file.
This validates declarations, not the actual evidence/body bytes or all-country
completeness. A successful result is metadata-ready, never source accepted.
"""
    errors = set()
    missing = set()
    policy = {'minimumReuseDays': 30, 'acquisitionAgeDays': None,
              'decision': 'unsupported-pure-cache-planner-no-download',
              'mtimeUsedForFreshness': False, 'assetBytesVerifiedByThisPlan': False,
              'networkRequests': 0}
    replay = None
    validation_age = None
    decision = 'blocked'
    try:
        now = timestamp(as_of)
    except (ValueError, TypeError, AttributeError):
        return {'bindingId': binding['id'], 'status': 'malformed',
                'bindingReady': False, 'datasetAccepted': False,
                'diagnostics': ['invalid-clock'], 'networkRequests': 0}
    try:
        if not isinstance(descriptor, dict) or set(descriptor) != KEYS:
            raise ValueError('descriptor-shape')
        if len(canonical(descriptor)) > MAX_BYTES:
            raise ValueError('descriptor-bound')
        for key, expected in [('bindingId', binding['id']),
                              ('inputSha256', binding['input']['sha256']),
                              ('manifestSha256', binding['manifest']['sha256'])]:
            if descriptor[key] is None:
                missing.add('missing-' + key)
            elif descriptor[key] != expected:
                errors.add('stale-manifest-pin' if key == 'manifestSha256'
                           else 'mismatch-' + key)
        row = descriptor['row']
        if not isinstance(row, dict):
            raise ValueError('row-shape')
        errors.update(field_origin_errors(row, {
            'evidence.json': binding['manifest']['sha256']}))
        expected_row = template(binding)['row']
        if canonical(row.get('data')) != canonical(expected_row['data']):
            errors.add('metadata-value-mismatch')
        if row.get('provenance') != expected_row['provenance']:
            errors.add('metadata-selector-or-identity-mismatch')
        original = descriptor['originalAcquiredAt']
        # A recent validation never supplies/resets original acquisition time.
        if original is None:
            missing.add('original-acquisition-time-unknown')
        else:
            if original != binding['originalAcquiredAt']:
                errors.add('original-acquisition-time-unbound')
            age = (now - timestamp(original)).total_seconds()
            if age < 0:
                errors.add('original-acquisition-time-in-future')
            else:
                # Informational age only. No generic cache policy exists at
                # this base; do not borrow source-specific planning behavior.
                policy['acquisitionAgeDays'] = int(age // 86400)
        if descriptor['validatedAt'] is not None:
            validated = timestamp(descriptor['validatedAt'])
            if validated > now or (original is not None and validated < timestamp(original)):
                errors.add('validation-time-invalid')
            else:
                validation_age = int((now - validated).total_seconds() // 86400)
        previous = descriptor['priorReplayKey']
        if previous is not None and (not isinstance(previous, str) or len(previous) != 64
                                     or any(c not in '0123456789abcdef' for c in previous)):
            errors.add('prior-replay-key-invalid')
        replay = sha(canonical({'binding': binding,
                                'descriptor': {k: v for k, v in descriptor.items()
                                               if k not in ('validatedAt', 'priorReplayKey')}}))
        decision = 'no-op' if previous == replay else 'metadata-plan'
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        errors.add('malformed-descriptor')
    holds = binding['holds']
    if holds:
        errors.add('source-operation-held')
    all_errors = sorted(errors | missing)
    malformed = errors - {'source-operation-held', 'stale-manifest-pin'}
    status = ('malformed' if malformed else 'held' if holds else 'missing' if missing
              else 'stale' if errors else 'valid')
    return {'bindingId': binding['id'], 'sourceId': binding['sourceId'],
            'releaseId': binding['releaseId'], 'country': binding['country'],
            'dataType': binding['dataType'], 'status': status,
            'bindingReady': not all_errors, 'datasetAccepted': False,
            'diagnostics': all_errors, 'holds': holds, 'unknowns': binding['unknowns'],
            'nativeUnit': binding['nativeUnit'], 'nativeBasis': binding['nativeBasis'],
            'cache': policy, 'replayKey': replay,
            'validationAgeDays': validation_age,
            'cachePlannerSupported': False, 'stagingReady': False,
            'remainingBlockers': ['unsupported-pure-cache-planner',
                                  'reviewed-staging-scope-and-contract-required'],
            'decision': decision if not all_errors else 'blocked',
            'assetBytesVerified': False, 'networkRequests': 0}


def assess_many(descriptors, *, as_of, bindings=None):
    """Independent diagnostics per envelope; no peer failure can admit a row."""
    bindings = catalog()['bindings'] if bindings is None else bindings
    trusted = {b['id']: b for b in bindings}
    if not isinstance(descriptors, list) or len(descriptors) > 16:
        raise ValueError('descriptor-list-bound')
    results = []
    for descriptor in descriptors:
        identity = descriptor.get('bindingId') if isinstance(descriptor, dict) else None
        binding = trusted.get(identity) if isinstance(identity, str) else None
        if binding is None:
            results.append({'bindingId': identity if isinstance(identity, str) else None, 'status': 'missing',
                            'bindingReady': False, 'datasetAccepted': False,
                            'diagnostics': ['binding-not-registered'], 'networkRequests': 0})
        else:
            results.append(assess(binding, descriptor, as_of=as_of))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--templates', action='store_true')
    parser.add_argument('--input', type=Path, help='metadata envelopes only, <=512KiB')
    parser.add_argument('--as-of', help='explicit timezone-aware replay clock')
    args = parser.parse_args()
    try:
        if args.templates and args.input is None:
            result = [template(b) for b in catalog()['bindings']]
        elif args.input is not None and args.as_of and not args.templates:
            result = assess_many(load_metadata_json(read_metadata_input(args.input)), as_of=args.as_of)
        else:
            raise ValueError('select-templates-or-input-with-clock')
        print(canonical(result).decode())
    except MetadataNestingError:
        parser.exit(2, 'metadata-input-invalid: json-nesting-limit\n')
    except (ValueError, OSError, UnicodeError, TypeError, RecursionError) as error:
        parser.exit(2, 'metadata-input-invalid: ' + type(error).__name__ + '\n')


if __name__ == '__main__':
    main()
