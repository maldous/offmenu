"""NZ/SI/SY/UG metadata bindings only. No source reader or admission path.

The caller supplies an explicit root containing permitted JSON evidence. Body
paths inside that JSON are values, never opened. Core field-origin validation,
serialization, path/time checks and retained adapter descriptors are reused.
"""
import argparse
import json
import os
import re
import stat
import tempfile
from pathlib import Path

from .acceptance import fingerprint
from .acquisition import MIN_TTL
from .adapter_mapping import retained_adapters
from .core import RefreshError, canonical, safe_path, sha, strict_json, timestamp
from .field_provenance import datum_pointers, field_origin_errors
from .national_tabular import valid_input_name

COUNTRIES = frozenset(('NZ', 'SI', 'SY', 'UG'))
TYPES = frozenset(('ingredients', 'recipes', 'nutrition', 'retailers/providers',
                   'prices/baskets', 'dietary references'))
MAX_METADATA = 1024 * 1024
MAX_METADATA_DEPTH = 64
POLICY = fingerprint({'name': 'portfolio17-metadata-binding/1',
                      'unknown': None, 'bodyOperations': False})


def pointer(value, selector):
    """Literal RFC6901 lookup; no query language, inference or default value."""
    if not isinstance(selector, str) or (selector and not selector.startswith('/')):
        raise RefreshError('selector-invalid')
    if selector == '':
        return value
    for part in selector[1:].split('/'):
        if re.search(r'~(?![01])', part):
            raise RefreshError('selector-invalid')
        part = part.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not part.isdigit() or str(int(part)) != part:
                raise RefreshError('selector-invalid')
            value = value[int(part)]
        elif isinstance(value, dict):
            value = value[part]
        else:
            raise RefreshError('selector-missing')
    return value


def _required(value, key):
    result = value[key]
    if not isinstance(result, str) or not result:
        raise RefreshError('binding-text-invalid')
    return result


def _metadata_json(raw):
    value = strict_json(raw)
    # Bound nesting before recursive provenance traversal or serialization.
    pending = [(value, 0)]
    while pending:
        node, depth = pending.pop()
        if depth > MAX_METADATA_DEPTH:
            raise RefreshError('metadata-depth-exceeded')
        children = node.values() if isinstance(node, dict) else node if isinstance(node, list) else ()
        pending.extend((child, depth + 1) for child in children)
    return value


def _entry(entry, root, now, budget):
    for key in ('bindingId', 'sourceId', 'releaseId'):
        _required(entry, key)
    if entry['country'] not in COUNTRIES or entry['type'] not in TYPES:
        raise RefreshError('portfolio-scope-invalid')
    holds = entry['holds']
    if not isinstance(holds, list) or any(not isinstance(x, str) or not x for x in holds):
        raise RefreshError('holds-invalid')
    evidence = entry['evidence']
    if not isinstance(evidence, dict) or not 1 <= len(evidence) <= 16:
        raise RefreshError('metadata-evidence-required')
    values, pins = {}, {}
    for key, asset in sorted(evidence.items()):
        name = asset['path']
        if (not valid_input_name(name) or not name.endswith('.json')
                or asset.get('metadataOnly') is not True):
            raise RefreshError('metadata-only-json-required')
        path = safe_path(root / name)
        if not path.is_file():
            raise RefreshError('metadata-input-missing')
        size = path.stat().st_size
        if size > MAX_METADATA or size > budget[0]:
            raise RefreshError('metadata-budget-exceeded')
        raw = path.read_bytes()
        budget[0] -= len(raw)
        if len(raw) > size or len(raw) > MAX_METADATA or budget[0] < 0:
            raise RefreshError('metadata-budget-exceeded')
        if sha(raw) != asset['sha256']:
            raise RefreshError('metadata-pin-mismatch')
        values[key] = _metadata_json(raw)
        pins[name] = asset['sha256']
    fields = entry['fields']
    if not isinstance(fields, dict) or not fields:
        raise RefreshError('field-bindings-required')
    data, origins = {}, {}
    for target, binding in sorted(fields.items()):
        if not isinstance(target, str) or not target or '/' in target or '~' in target:
            raise RefreshError('target-field-invalid')
        if binding == {'unknown': True}:
            data[target] = None
            origins['/data/' + target] = {
                'kind': 'constant', 'policySha256': POLICY, 'symbol': 'explicit-unknown'}
            continue
        key = binding['evidence']
        selector = binding['selector']
        value = pointer(values[key], selector)
        data[target] = value
        for suffix in datum_pointers(value, ''):
            origins['/data/' + target + suffix] = {
                'kind': 'source', 'sourceId': entry['sourceId'],
                'releaseId': entry['releaseId'],
                'inputPath': evidence[key]['path'], 'inputSha256': evidence[key]['sha256'],
                'sourceRecordId': entry['bindingId'], 'sourceField': selector + suffix or '/'}
    row = {'kind': 'sourceMetadataBinding', 'country': entry['country'],
           'type': entry['type'], 'data': data,
           'provenance': {'sourceId': entry['sourceId'], 'releaseId': entry['releaseId'],
                          'fieldOrigins': origins}}
    errors = field_origin_errors(row, pins, policy_pins=(POLICY,))
    if errors:
        raise RefreshError('shared-field-origin-validation-failed')
    diagnostics = []
    acquired = None
    time_ref = entry.get('originalAcquisition')
    if time_ref is not None:
        acquired = timestamp(pointer(values[time_ref['evidence']], time_ref['selector']))
    cache = {'minimumReuseDays': MIN_TTL // 86400, 'originalAcquiredAt': None,
             'acquisitionAgeDays': None, 'validationAt': now.isoformat(),
             'validationResetsAcquisition': False, 'mtimeUsed': False,
             'bodyBytesVerified': False, 'networkRequests': 0,
             'decision': 'acquisition-time-missing'}
    if acquired is None:
        diagnostics.append('original-acquisition-time-missing')
    else:
        age = (now - acquired).total_seconds()
        if age < 0:
            raise RefreshError('acquisition-timestamp-in-future')
        cache.update(originalAcquiredAt=acquired.isoformat(),
                     acquisitionAgeDays=int(age // 86400),
                     decision='reuse-retained-metadata-no-download' if age < MIN_TTL
                     else 'stale-input-review-required-no-download')
        if age >= MIN_TTL:
            diagnostics.append('stale-input')
    # This flag records an evidence gap; config is never a source-use grant.
    if entry.get('retentionEvidence') is None:
        diagnostics.append('source-retention-evidence-missing')
    else:
        ref = entry['retentionEvidence']
        pointer(values[ref['evidence']], ref['selector'])
    adapter = next((x for x in retained_adapters()
                    if x['sourceId'] == entry.get('adapterSourceId')
                    and x['sourceId'] == entry['sourceId']
                    and x['releaseId'] == entry['releaseId']), None)
    if adapter is None:
        diagnostics.append('shared-payload-adapter-unbound')
    if holds:
        diagnostics.append('source-processing-held')
    status = ('held' if holds else 'stale' if 'stale-input' in diagnostics
              else 'missing' if diagnostics else 'valid-metadata-binding')
    candidate = {'row': row, 'evidencePins': pins, 'policySha256': POLICY,
                 'sourceProcessingAuthorized': False, 'datasetAcceptance': False}
    return {'bindingId': entry['bindingId'], 'status': status,
            'diagnostics': sorted(diagnostics), 'holds': holds, 'cache': cache,
            'requiredInputs': entry.get('requiredInputs', []),
            'acquisitionScope': entry.get('acquisitionScope', 'unknown'),
            'candidate': candidate, 'candidateSha256': sha(canonical(candidate)),
            'sharedAdapter': adapter, 'sourceBodyOperations': 0}


def evaluate(config, metadata_root, *, now):
    """Isolate each declared source; metadata only, never run a payload adapter."""
    if config.get('schemaVersion') != 'offmenu-portfolio17-bindings/1':
        raise RefreshError('binding-config-version-invalid')
    entries = config.get('bindings')
    if not isinstance(entries, list) or not 1 <= len(entries) <= 32:
        raise RefreshError('binding-count-invalid')
    if now.tzinfo is None:
        raise RefreshError('binding-clock-must-be-aware')
    ids = [x.get('bindingId') if isinstance(x, dict) else None for x in entries]
    if any(not isinstance(x, str) or not x for x in ids) or len(set(ids)) != len(ids):
        raise RefreshError('binding-id-inventory-invalid')
    root = safe_path(metadata_root)
    outcomes, budget = [], [MAX_METADATA]
    for entry in entries:
        try:
            outcome = _entry(entry, root, now, budget)
        except (RefreshError, KeyError, IndexError, TypeError, ValueError, OSError, RecursionError) as exc:
            # Fixed diagnostics deliberately avoid paths, bodies and exception text.
            error = _error_code(exc)
            status = 'missing' if error in ('metadata-input-missing', 'selector-missing') else 'malformed'
            outcome = {'bindingId': entry['bindingId'], 'status': status,
                       'diagnostics': [error], 'sourceBodyOperations': 0}
        outcomes.append(outcome)
    return {'schemaVersion': 'offmenu-portfolio17-binding-diagnostics/1',
            'bindings': outcomes, 'metadataBytesRead': MAX_METADATA - budget[0],
            'networkRequests': 0, 'sourceBodyOperations': 0,
            'sourceStageEligible': False, 'goldAdmitted': False}


def _error_code(exc):
    if isinstance(exc, RecursionError):
        return 'metadata-depth-exceeded'
    if isinstance(exc, RefreshError):
        return str(exc)
    if isinstance(exc, (KeyError, IndexError)):
        return 'selector-missing'
    return 'binding-malformed'


def _read_binding_config(path):
    """Bound reads on the opened regular inode; a FIFO replacement cannot block."""
    descriptor = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise RefreshError('binding-config-not-regular')
        if before.st_size > MAX_METADATA:
            raise RefreshError('binding-config-too-large')
        chunks, remaining = [], MAX_METADATA
        while remaining:
            chunk = os.read(descriptor, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(descriptor)
        raw = b''.join(chunks)
        identity = lambda value: (value.st_dev, value.st_ino, value.st_size,
                                  value.st_mtime_ns, value.st_ctime_ns)
        if identity(before) != identity(after) or len(raw) != before.st_size:
            raise RefreshError('binding-config-changed-during-read')
        return raw
    except OSError:
        raise RefreshError('binding-config-read-failed') from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bindings', type=Path, required=True)
    parser.add_argument('--metadata-root', type=Path, required=True)
    parser.add_argument('--now', required=True, help='Explicit UTC validation clock')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = safe_path(args.bindings)
    result = evaluate(strict_json(_read_binding_config(source)), args.metadata_root,
                      now=timestamp(args.now))
    raw = canonical(result)
    output = safe_path(args.output)
    if output == source or output == safe_path(args.metadata_root) or safe_path(args.metadata_root) in output.parents:
        raise RefreshError('output-overlaps-metadata')
    if output.exists() and output.stat().st_nlink > 1:
        raise RefreshError('output-hardlink-not-allowed')
    unchanged = output.is_file() and output.read_bytes() == raw
    if not unchanged:
        output.parent.mkdir(parents=True, exist_ok=True)
        # Replace the output directory entry, never truncate a potentially aliased inode.
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=output.parent, prefix='.portfolio17-',
                                             delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(raw)
            os.replace(temporary, output)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    print(json.dumps({'outputSha256': sha(raw), 'unchanged': unchanged,
                      'sourceBodyOperations': 0, 'datasetAcceptance': False}))


if __name__ == '__main__':
    main()
