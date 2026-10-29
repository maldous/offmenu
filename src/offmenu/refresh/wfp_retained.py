"""Bounded projection of retained WFP Libya candidates, never raw extraction.

Callers own reviewed code, exact source/use and destination qualification. This
module has no CLI, network client, admission registry or publication operation.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass
import gzip
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
import time

from .core import (BoundedReader, RefreshError, atomic_json, canonical, code_identity, digest,
                   fsync_directory, safe_path, sha, strict_json, timestamp)
from .field_provenance import field_origin_errors
from .serialization import CONTENT_POLICY, POLICY as SERIALIZATION_POLICY

SOURCE = 'wfp-food-prices-for-libya'
RELEASE = 'price-resource-modified-2026-10-11T15:38:40.693973'
COLUMNS = ('date', 'admin1', 'admin2', 'market', 'market_id', 'latitude', 'longitude',
           'category', 'commodity', 'commodity_id', 'unit', 'priceflag', 'pricetype',
           'currency', 'price', 'usdprice')
EXCLUDED_LINES = frozenset(range(2, 202)) | {327}
UNKNOWN = ('canonicalConcept', 'canonicalUnit', 'canonicalCurrency', 'canonicalMarket',
           'canonicalBasis', 'foodEligibility', 'fxOrientation')
POLICY = {'version': 'wfp-retained-native/1', 'native': 'all16strings-unchanged',
          'unqualified': dict.fromkeys(UNKNOWN), 'accepted': False,
          'originalBodyReads': 0, 'sourceOrder': 'increasing-original-physical-line'}
POLICY_SHA256 = sha(canonical(POLICY))
HEX = re.compile('[0-9a-f]{64}')


@dataclass(frozen=True)
class WfpLimits:
    max_input_bytes: int = 256 * 1024**2
    max_line_bytes: int = 64 * 1024
    max_rows: int = 100000
    max_output_bytes: int = 256 * 1024**2
    max_expanded_output_bytes: int = 1024**3
    max_json_depth: int = 32
    max_wall_seconds: int = 120

    def validate(self):
        ceilings = asdict(WfpLimits())
        if any(type(value) is not int or not 1 <= value <= ceilings[name]
               for name, value in asdict(self).items()):
            raise RefreshError('wfp-invalid-limits')


def _require(condition, code):
    if not condition:
        raise RefreshError(code)


def _hex(value):
    return isinstance(value, str) and bool(HEX.fullmatch(value))


def _context(context):
    _require(isinstance(context, dict) and set(context) == {
        'scope', 'sourceId', 'releaseId', 'originalSourceSha256', 'originalAcquiredAt',
        'validatedAt', 'rightsEvidenceSha256', 'scopeEvidenceSha256', 'license',
        'attribution', 'excludedOriginalLines', 'input'}, 'wfp-context-required')
    _require(context.get('scope') in ('authored-fixture-only', 'selected-local-staging')
             and context.get('sourceId') == SOURCE and context.get('releaseId') == RELEASE,
             'wfp-context-scope-mismatch')
    _require(all(_hex(context.get(k)) for k in
                 ('originalSourceSha256', 'rightsEvidenceSha256', 'scopeEvidenceSha256')),
             'wfp-context-evidence-required')
    _require(timestamp(context.get('originalAcquiredAt')) <= timestamp(context.get('validatedAt')),
             'wfp-validation-before-acquisition')
    _require(all(isinstance(context.get(k), str) and context[k]
                 for k in ('license', 'attribution')), 'wfp-attribution-required')
    excluded = context.get('excludedOriginalLines')
    _require(isinstance(excluded, list) and all(type(v) is int for v in excluded)
             and len(excluded) == len(EXCLUDED_LINES) and set(excluded) == EXCLUDED_LINES,
             'wfp-prior-exclusion-contract-mismatch')
    item = context.get('input')
    _require(isinstance(item, dict) and set(item) == {'name', 'bytes', 'sha256'},
             'wfp-input-contract-required')
    name = item['name']
    _require(isinstance(name, str) and bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', name))
             and name not in ('.', '..') and type(item['bytes']) is int and item['bytes'] > 0
             and _hex(item['sha256']), 'wfp-input-contract-invalid')


def normalize_record(candidate, *, context, input_line):
    """Preserve native lexical cells and declare, rather than fill, unknowns."""
    _context(context)
    _require(type(input_line) is int and input_line > 0 and isinstance(candidate, dict),
             'wfp-record-invalid')
    _require(candidate.get('country') == 'LY' and candidate.get('sourceId') == SOURCE
             and candidate.get('release') == RELEASE
             and candidate.get('admission') is False and candidate.get('canonicalEnglishGold') is False,
             'wfp-record-scope-mismatch')
    values, original = candidate.get('values'), candidate.get('originalRecord')
    _require(isinstance(values, dict) and set(values) == set(COLUMNS)
             and all(isinstance(v, str) for v in values.values()), 'wfp-native-columns-invalid')
    _require(isinstance(original, dict) and original.get('sourceSHA256') == context['originalSourceSha256']
             and _hex(original.get('lineSHA256')) and isinstance(original.get('file'), str)
             and original['file'], 'wfp-original-selector-invalid')
    _require(all(type(original.get(k)) is int and original[k] >= minimum
                 for k, minimum in (('csvLine', 2), ('byteOffset', 0), ('byteLength', 1))),
             'wfp-original-selector-invalid')
    _require(original['csvLine'] not in EXCLUDED_LINES, 'wfp-prior-prefix-excluded')
    identity = f"wfp-lby:{context['originalSourceSha256']}:line:{original['csvLine']}"
    _require(candidate.get('id') == identity, 'wfp-record-identity-mismatch')
    _require(isinstance(candidate.get('sourceURL'), str) and candidate['sourceURL']
             and isinstance(candidate.get('rights'), dict), 'wfp-source-metadata-required')
    _require(candidate['rights'].get('licence', candidate['rights'].get('license')) == context['license']
             and candidate['rights'].get('attribution') == context['attribution'],
             'wfp-source-rights-mismatch')
    for name in ('unknowns', 'issues'):
        _require(isinstance(candidate.get(name), list)
                 and all(isinstance(value, str) for value in candidate[name]), 'wfp-source-flags-invalid')

    def origin(field):
        return {'kind': 'source', 'sourceId': SOURCE, 'releaseId': RELEASE,
                'inputPath': context['input']['name'], 'inputSha256': context['input']['sha256'],
                'sourceRecordId': identity, 'sourceField': field}

    origins = {'/data/native/' + name: origin('/values/' + name) for name in COLUMNS}
    origins.update({'/data/unqualified/' + name: {'kind': 'constant',
                    'policySha256': POLICY_SHA256, 'symbol': 'unqualified-' + name} for name in UNKNOWN})
    for output, source in (('sourceUnknowns', 'unknowns'), ('sourceIssues', 'issues')):
        origins.update({f'/data/{output}/{index}': origin(f'/{source}/{index}')
                        for index in range(len(candidate[source]))})
    row = {'schemaVersion': '1.0', 'kind': 'priceObservation', 'id': identity, 'countries': ['LY'],
           'accepted': False, 'automaticPlanningEligible': False,
           'data': {'native': dict(values), 'unqualified': dict.fromkeys(UNKNOWN),
                    'sourceUnknowns': list(candidate['unknowns']), 'sourceIssues': list(candidate['issues'])},
           'provenance': {'sourceId': SOURCE, 'releaseId': RELEASE, 'recordId': identity,
                          'acquiredAt': context['originalAcquiredAt'], 'validatedAt': context['validatedAt'],
                          'inputPath': context['input']['name'], 'inputSha256': context['input']['sha256'],
                          'inputLine': input_line, 'archiveSha256': context['originalSourceSha256'],
                          'originalRecord': deepcopy(original), 'url': candidate['sourceURL'],
                          'sourceRights': deepcopy(candidate['rights']), 'license': context['license'],
                          'attribution': context['attribution'],
                          'rightsEvidenceSha256': context['rightsEvidenceSha256'],
                          'scopeEvidenceSha256': context['scopeEvidenceSha256'],
                          'originScope': 'retained-derivative-cells;original-selectors-not-dereferenced',
                          'fieldOrigins': origins}}
    _require(not field_origin_errors(row, {context['input']['name']: context['input']['sha256']},
                                    policy_pins=(POLICY_SHA256,)), 'wfp-field-origins-invalid')
    return row


def _lines(stream, total_limit, line_limit, hasher):
    reader = BoundedReader(stream, total_limit)
    pending = b''
    while True:
        block = reader.read(min(65536, line_limit + 1))
        if not block:
            break
        hasher.update(block)
        pending += block
        while b'\n' in pending:
            line, pending = pending.split(b'\n', 1)
            _require(len(line) + 1 <= line_limit, 'wfp-line-limit')
            yield line + b'\n'
        _require(len(pending) <= line_limit, 'wfp-line-limit')
    if pending:
        _require(len(pending) <= line_limit, 'wfp-line-limit')
        yield pending


def _json(raw, depth_limit):
    try:
        value = strict_json(raw)
    except RefreshError:
        raise
    except (ValueError, TypeError, RecursionError, UnicodeError):
        raise RefreshError('wfp-json-invalid') from None
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        _require(depth <= depth_limit, 'wfp-json-depth-limit')
        children = item.values() if isinstance(item, dict) else item if isinstance(item, list) else ()
        pending.extend((child, depth + 1) for child in children)
    return value


def _read_regular(path, limit, *, contents=False):
    path = safe_path(path)
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError:
        raise RefreshError('wfp-file-unavailable') from None
    try:
        before = os.fstat(descriptor)
        _require(stat.S_ISREG(before.st_mode) and before.st_size <= limit, 'wfp-file-bound-or-type')
        result, hasher, size = [], hashlib.sha256(), 0
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            reader = BoundedReader(stream, limit)
            while True:
                block = reader.read(65536)
                if not block:
                    break
                hasher.update(block)
                size += len(block)
                if contents:
                    result.append(block)
        _stable(before, os.fstat(descriptor), safe_path(path).stat())
        return b''.join(result) if contents else {'bytes': size, 'sha256': hasher.hexdigest()}
    finally:
        os.close(descriptor)


def _stable(before, after, current):
    fields = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    _require(fields(before) == fields(after) == fields(current), 'wfp-input-changed')


def normalize_retained(input_path, destination, *, context, expected_records, limits=WfpLimits(),
                       previous_receipt_sha256=None):
    """Stream a selected derivative into an exclusive, manifest-committed candidate.

    Parent directory must already be qualified and exist. This creates no volume
    or admission. Existing output requires an externally retained receipt pin;
    its exact input, handler/runtime and output identity are verified before reuse.
    """
    _context(context)
    limits.validate()
    _require(type(expected_records) is int and 1 <= expected_records <= limits.max_rows,
             'wfp-count-contract-invalid')
    _require(context['scope'] != 'selected-local-staging' or expected_records == 69273,
             'wfp-selected-extent-mismatch')
    _require(context['input']['bytes'] <= limits.max_input_bytes, 'wfp-input-limit')
    source, destination = safe_path(input_path), safe_path(destination)
    _require(destination.parent.is_dir(), 'wfp-destination-unavailable')
    started = time.monotonic()
    identity = code_identity(packaged=True)
    build = {'codeFingerprint': identity['codeFingerprint'], 'runtime': identity['runtime']}
    contract = {'context': context, 'limits': asdict(limits), 'policySha256': POLICY_SHA256,
                'expectedRecords': expected_records, 'build': build}
    if destination.exists():
        _require(_hex(previous_receipt_sha256), 'wfp-existing-destination-requires-receipt-pin')
        receipt = _read_regular(destination / 'manifest.json', 1024**2, contents=True)
        _require(sha(receipt) == previous_receipt_sha256, 'wfp-existing-receipt-mismatch')
        manifest = _json(receipt, limits.max_json_depth)
        _require(manifest.get('contract') == contract and manifest.get('normalizedRecords') == expected_records
                 and manifest.get('status') == 'normalized-candidate' and manifest.get('accepted') is False,
                 'wfp-existing-contract-mismatch')
        _require(set(p.name for p in destination.iterdir()) == {'manifest.json', 'normalized.jsonl.gz'},
                 'wfp-existing-asset-set-mismatch')
        _require(_read_regular(source, limits.max_input_bytes) ==
                 {k: context['input'][k] for k in ('bytes', 'sha256')}, 'wfp-existing-input-mismatch')
        _require(_read_regular(destination / 'normalized.jsonl.gz', limits.max_output_bytes) == manifest.get('output'),
                 'wfp-existing-output-mismatch')
        _require(time.monotonic() - started <= limits.max_wall_seconds, 'wfp-wall-limit')
        return {**manifest, 'reused': True, 'normalizationReceiptSha256': previous_receipt_sha256}
    _require(previous_receipt_sha256 is None, 'wfp-previous-destination-missing')
    try:
        descriptor = os.open(source, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError:
        raise RefreshError('wfp-input-unavailable') from None
    pending = None
    try:
        before = os.fstat(descriptor)
        _require(stat.S_ISREG(before.st_mode), 'wfp-regular-input-required')
        _require(before.st_size == context['input']['bytes'], 'wfp-input-size-mismatch')
        pending = Path(tempfile.mkdtemp(prefix='.wfp-', dir=destination.parent))
        count = expanded = last_line = 0
        hasher, content_hash = hashlib.sha256(), hashlib.sha256()
        with os.fdopen(descriptor, 'rb', closefd=False) as stream, (pending / 'normalized.jsonl.gz').open('xb') as raw:
            with gzip.GzipFile(fileobj=raw, mode='wb', **SERIALIZATION_POLICY['gzip']) as output:
                for line in _lines(stream, min(limits.max_input_bytes, context['input']['bytes']),
                                   limits.max_line_bytes, hasher):
                    _require(time.monotonic() - started <= limits.max_wall_seconds, 'wfp-wall-limit')
                    count += 1
                    _require(count <= min(expected_records, limits.max_rows), 'wfp-row-limit')
                    row = normalize_record(_json(line, limits.max_json_depth), context=context, input_line=count)
                    original_line = row['provenance']['originalRecord']['csvLine']
                    _require(original_line > last_line, 'wfp-source-order-or-duplicate')
                    last_line = original_line
                    encoded = canonical([row])
                    expanded += len(encoded)
                    _require(expanded <= limits.max_expanded_output_bytes, 'wfp-expanded-output-limit')
                    content_hash.update(encoded)
                    output.write(encoded)
                    _require(raw.tell() <= limits.max_output_bytes, 'wfp-output-limit')
            raw.flush()
            os.fsync(raw.fileno())
            _require(raw.tell() <= limits.max_output_bytes, 'wfp-output-limit')
        _require(count == expected_records, 'wfp-count-mismatch')
        _require(hasher.hexdigest() == context['input']['sha256'], 'wfp-input-hash-mismatch')
        after, current = os.fstat(descriptor), safe_path(source).stat()
        _stable(before, after, current)
        output_pin = digest(pending / 'normalized.jsonl.gz', max_bytes=limits.max_output_bytes)
        manifest = {'schemaVersion': 'offmenu-wfp-retained-candidate/1', 'status': 'normalized-candidate',
                    'sourceId': SOURCE, 'releaseId': RELEASE, 'normalizedRecords': count,
                    'originalAcquiredAt': context['originalAcquiredAt'], 'validatedAt': context['validatedAt'],
                    'context': deepcopy(context), 'limits': asdict(limits), 'policySha256': POLICY_SHA256,
                    'contract': deepcopy(contract),
                    'serializationPolicy': CONTENT_POLICY, 'normalizedCanonicalBytes': expanded,
                    'normalizedCanonicalSha256': content_hash.hexdigest(), 'output': output_pin,
                    'accepted': False, 'publicExport': False, 'sourceBodyReads': 0,
                    'inputDerivativeRead': True, 'networkRequests': 0,
                    'completionContract': 'exclusive-destination;manifest-installed-last'}
        _require(len(canonical(manifest)) <= 1024**2, 'wfp-receipt-limit')
        atomic_json(pending / 'manifest.json', manifest)
        fsync_directory(pending)
        # Reserve exclusively after full validation. Commit the manifest last;
        # consumers require it plus output hashes, never directory existence.
        safe_path(destination).mkdir()
        os.rename(pending / 'normalized.jsonl.gz', destination / 'normalized.jsonl.gz')
        fsync_directory(destination)
        os.rename(pending / 'manifest.json', destination / 'manifest.json')
        fsync_directory(destination)
        fsync_directory(destination.parent)
        return {**manifest, 'reused': False, 'normalizationReceiptSha256': sha(canonical(manifest))}
    except RefreshError:
        raise
    except (OSError, ValueError, TypeError, KeyError, RecursionError, UnicodeError):
        raise RefreshError('wfp-invalid-or-unreadable-input') from None
    finally:
        os.close(descriptor)
        if pending is not None:
            shutil.rmtree(pending, ignore_errors=True)
        # A partial final directory is retained for explicit recovery. Never
        # delete/overwrite final output, even when this call reserved it.
