"""DJ/NA/TG/VI receipt bindings, never source-body parsers or admissions.

The catalog is reviewed application configuration. Source receipts cannot grant
operations, supply executable adapters, or change the catalog's holds.
"""
import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat

from .acceptance import fingerprint
from .acquisition import MIN_TTL
from .core import RefreshError, safe_path, strict_json, timestamp
from .field_provenance import datum_pointers, field_origin_errors
from .reference_adapters import candidate_bytes

MAX_METADATA = 64 * 1024
MAX_SELECTED_DEPTH = 64
COUNTRIES = frozenset(('DJ', 'NA', 'TG', 'VI'))


@dataclass(frozen=True)
class ReceiptBinding:
    key: str
    country: str
    domain: str
    metadata_path: str
    metadata_sha256: str
    metadata_bytes: int
    fields: tuple  # (field name, JSON pointer); None means explicitly unbound.
    holds: tuple
    artifact: tuple  # reported source path/hash, not a file to open
    role: str = 'receipt-metadata-only'
    fixture: bool = False


def binding_policy(binding):
    return fingerprint({'binding': binding.key, 'fields': binding.fields,
                        'holds': binding.holds, 'country': binding.country,
                        'domain': binding.domain, 'artifact': binding.artifact,
                        'role': binding.role})


def field_origins(binding, data, source_id, release_id):
    policy = binding_policy(binding)
    origins = {p: {'kind': 'constant', 'policySha256': policy,
                   'symbol': 'reviewed-receipt-binding:' + p}
               for p in datum_pointers(data)}
    for name, locator in binding.fields:
        field = data['fields'][name]
        if locator is None or field['presence'] not in ('value', 'null'):
            continue
        prefix = '/data/fields/' + name.replace('~', '~0').replace('/', '~1') + '/value'
        for path in datum_pointers(field['value'], prefix):
            origins[path] = {'kind': 'source', 'sourceId': source_id,
                             'releaseId': release_id, 'inputPath': 'receipt.json',
                             'inputSha256': binding.metadata_sha256,
                             'sourceRecordId': binding.key,
                             'sourceField': locator + path[len(prefix):] or '/'}
    return origins


def pointer(document, locator):
    """Preserve missing versus explicit null; RFC6901 literals, no expressions."""
    if locator is None:
        return {'presence': 'unbound', 'value': None}
    value = document
    try:
        if locator != '':
            if not locator.startswith('/'):
                raise ValueError()
            for token in locator[1:].split('/'):
                token = token.replace('~1', '/').replace('~0', '~')
                if isinstance(value, list):
                    if not token.isdigit() or str(int(token)) != token:
                        raise KeyError()
                    value = value[int(token)]
                elif isinstance(value, dict):
                    value = value[token]
                else:
                    raise KeyError()
    except (KeyError, IndexError):
        return {'presence': 'missing', 'value': None}
    return {'presence': 'null' if value is None else 'value', 'value': value}


def _bounded_selected(value):
    """Bound selected values before shared recursive origin/JSON traversal."""
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > MAX_SELECTED_DEPTH:
            raise ValueError('selected-metadata-depth-exceeded')
        if isinstance(item, dict):
            pending.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            pending.extend((child, depth + 1) for child in item)


def bind_receipt(binding, payload, *, validated_at, now, previous=None):
    """Pure bounded metadata binding; diagnostics are isolated from other inputs.

    validated_at is this metadata-pin check, not publisher validation or a new
    acquisition. Candidate identity deliberately excludes validation age.
    """
    errors = set()
    result = {'bindingId': binding.key, 'country': binding.country,
              'domain': binding.domain, 'status': 'malformed', 'errors': [],
              'candidateSha256': None, 'candidateBytes': 0,
              'normalizedRecords': 0, 'recordProcessingAuthorized': False,
              'recordBlockers': [],
              'sourceAcceptance': False, 'countryComplete': False,
              'networkRequests': 0, 'fixture': binding.fixture}
    try:
        checked, clock = timestamp(validated_at), timestamp(now)
        if checked > clock:
            raise ValueError('clock')
        if (binding.country not in COUNTRIES or not binding.key
                or type(binding.metadata_bytes) is not int
                or not 0 < binding.metadata_bytes <= MAX_METADATA
                or len({k for k, _ in binding.fields}) != len(binding.fields)):
            raise ValueError('binding')
        result['cache'] = {'originalAcquiredAt': None,
                           'metadataValidatedAt': validated_at,
                           'publisherCheckedAt': None,
                           'minimumReuseDays': MIN_TTL // 86400,
                           'validationAgeSeconds': int((clock - checked).total_seconds()),
                           'bodyCacheDecision': 'not-selected-no-body-access',
                           'acquisitionMeaning': 'reported-response-only-not-dataset-or-validation',
                           'mtimeUsed': False}
        if payload is None:
            result.update(status='missing', errors=['metadata-missing'])
            return result, b''
        if not isinstance(payload, bytes) or len(payload) > MAX_METADATA:
            raise ValueError('metadata')
        if (len(payload) != binding.metadata_bytes
                or hashlib.sha256(payload).hexdigest() != binding.metadata_sha256):
            result['errors'] = ['metadata-pin-mismatch']
            return result, b''
        document = strict_json(payload)
        if not isinstance(document, dict):
            raise ValueError('metadata')
        fields = {}
        for name, locator in binding.fields:
            field = pointer(document, locator)
            _bounded_selected(field['value'])
            fields[name] = {**field, 'origin': {
                'artifactSha256': binding.metadata_sha256, 'jsonPointer': locator}}
        acquired = fields.get('originalAcquiredAt', {}).get('value')
        if acquired is None:
            errors.add('original-acquisition-time-unknown')
        else:
            if timestamp(acquired) > clock:
                raise ValueError('acquisition')
        result['cache']['originalAcquiredAt'] = acquired
        result['cache']['publisherCheckedAt'] = fields.get('publisherCheckedAt', {}).get('value')
        stale = (clock - checked).total_seconds() >= MIN_TTL
        if stale:
            errors.add('metadata-validation-stale')
        for name in ('sourceEdition', 'recordSelector', 'nativeUnit', 'nativeBasis'):
            if fields.get(name, {}).get('presence') != 'value':
                result['recordBlockers'].append(name.replace('sourceEdition', 'source-edition')
                           .replace('recordSelector', 'record-selector')
                           .replace('nativeUnit', 'native-unit')
                           .replace('nativeBasis', 'native-basis') + '-unbound')
        if binding.holds:
            errors.add('source-held')
        # Applicability is this reviewed metadata context, never food coverage.
        release = 'receipt-' + binding.metadata_sha256[:16]
        policy = binding_policy(binding)
        record = {'schemaVersion': '1.0', 'id': 'portfolio44:' + binding.key,
                  'kind': 'source-input-reference', 'countries': [binding.country],
                  'provenance': {'sourceId': 'portfolio44:' + binding.key,
                                 'releaseId': release,
                                 'fetchedAt': acquired,
                                 'metadataSha256': binding.metadata_sha256,
                                 'policySha256': policy},
                  'data': {'scope': 'receipt-metadata-only', 'domain': binding.domain,
                           'role': binding.role,
                           'fields': fields, 'reportedArtifact': list(binding.artifact),
                           'holds': list(binding.holds),
                           'authorizedBodyOperations': [],
                           'automaticPlanningEligible': False}}
        record['provenance']['fieldOrigins'] = field_origins(
            binding, record['data'], record['provenance']['sourceId'], release)
        content = candidate_bytes([record])
        checksum = hashlib.sha256(content).hexdigest()
        manifest = {'sourceId': record['provenance']['sourceId'], 'releaseId': release,
                    'scope': 'receipt-metadata-only', 'candidateSha256': checksum,
                    'candidateBytes': len(content), 'normalizedRecords': 1,
                    'metadataSha256': binding.metadata_sha256, 'policySha256': policy,
                    'originalAcquiredAt': acquired, 'fixture': binding.fixture,
                    'bodyOperations': [], 'productionAdmission': False}
        same = isinstance(previous, dict) and all(previous.get(k) == manifest[k] for k in
            ('candidateSha256', 'metadataSha256', 'policySha256', 'scope'))
        result.update(status='held' if binding.holds else 'stale' if stale else 'ready',
                      errors=sorted(errors), candidateSha256=checksum,
                      candidateBytes=len(content), normalizedRecords=1,
                      manifest=manifest, replay='unchanged-no-op' if same else 'new-metadata-candidate')
        return result, content
    except (ValueError, TypeError, KeyError, UnicodeError, OverflowError, RecursionError):
        result['errors'] = ['metadata-or-binding-malformed']
        return result, b''


def bind_many(bindings, loader, *, validated_at, now):
    """Isolate metadata IO/format failures; a peer can still report its result."""
    results = []
    for key in sorted(bindings):
        binding = bindings[key]
        try:
            payload = loader(binding)
            report, _ = bind_receipt(binding, payload, validated_at=validated_at, now=now)
        except (OSError, ValueError, RecursionError):
            report = {'bindingId': key, 'country': binding.country,
                      'status': 'malformed', 'errors': ['metadata-io-invalid'],
                      'sourceAcceptance': False, 'recordProcessingAuthorized': False}
        results.append(report)
    return {'schemaVersion': 'portfolio44-metadata-diagnostics/1', 'results': results,
            'sourceAcceptance': False, 'countryComplete': False, 'networkRequests': 0}


def body_capability(binding):
    """No generic pure cache planner/body adapter is installed by this package."""
    return {'supported': False, 'bodyOperations': [], 'networkRequests': 0,
            'holds': list(binding.holds), 'cachePlanning': 'unsupported-shared-interface',
            'dependency': 'Morgan/00 source-neutral pure planner proposal; not selected here'}


def semantic_errors(binding, document, record):
    """Shared SourceContract callback for an independently selected metadata scope.

    Caller supplies the already permitted receipt document; this does not open a
    body or install a production contract. In particular, a receipt cannot supply
    permitted_operations to SourceContract.
    """
    errors = []
    try:
        data, provenance = record['data'], record['provenance']
        if (record['kind'] != 'source-input-reference'
                or record['id'] != 'portfolio44:' + binding.key
                or record['countries'] != [binding.country]
                or data['scope'] != 'receipt-metadata-only'
                or data['domain'] != binding.domain
                or data['role'] != binding.role
                or data['authorizedBodyOperations'] != []
                or data['automaticPlanningEligible'] is not False
                or data['holds'] != list(binding.holds)
                or data['reportedArtifact'] != list(binding.artifact)
                or provenance['metadataSha256'] != binding.metadata_sha256):
            errors.append('portfolio-metadata-scope-mismatch')
        expected = {name: {**pointer(document, locator), 'origin': {
                    'artifactSha256': binding.metadata_sha256, 'jsonPointer': locator}}
                    for name, locator in binding.fields}
        if data['fields'] != expected:
            errors.append('portfolio-field-origin-or-value-mismatch')
        if provenance.get('policySha256') != binding_policy(binding):
            errors.append('portfolio-policy-mismatch')
        errors.extend(field_origin_errors(record, {'receipt.json': binding.metadata_sha256},
                                          policy_pins=(binding_policy(binding),)))
        if provenance.get('fieldOrigins') != field_origins(
                binding, data, 'portfolio44:' + binding.key,
                'receipt-' + binding.metadata_sha256[:16]):
            errors.append('portfolio-field-origin-or-value-mismatch')
    except (KeyError, TypeError, ValueError, RecursionError):
        errors.append('portfolio-record-malformed')
    return sorted(set(errors))


def _read_regular(path, limit):
    """Read the same bounded nonblocking, nofollow regular-file descriptor.

    Path checks alone cannot protect a later reopen from replacement by a FIFO.
    Nonregular files are rejected before any read, including after a swap.
    """
    path = safe_path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise RefreshError('metadata-file-bound-or-type-invalid')
        chunks, size = [], 0
        while True:
            block = os.read(fd, min(65536, limit - size + 1))
            if not block:
                break
            chunks.append(block)
            size += len(block)
            if size > limit:
                raise RefreshError('metadata-file-bound-or-type-invalid')
        after = os.fstat(fd)
        current = os.stat(path, follow_symlinks=False)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if identity(before) != identity(after) or identity(after) != identity(current):
            raise RefreshError('metadata-changed-during-read')
        return b''.join(chunks)
    finally:
        os.close(fd)


def read_metadata(binding):
    """Only the code-pinned receipt path; never follow source body locators."""
    try:
        return _read_regular(binding.metadata_path, MAX_METADATA)
    except FileNotFoundError:
        return None


def main(argv=None):
    from .portfolio44_catalog import BINDINGS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binding', required=True, choices=sorted(BINDINGS))
    parser.add_argument('--validated-at', required=True)
    parser.add_argument('--now', required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    binding = BINDINGS[args.binding]
    try:
        payload = read_metadata(binding)
        prior = None
        if args.output:
            output = safe_path(args.output)
            old = output / 'manifest.json'
            if old.exists():
                prior = strict_json(_read_regular(old, MAX_METADATA))
        result, content = bind_receipt(binding, payload, validated_at=args.validated_at,
                                       now=args.now, previous=prior)
        if args.output and content:
            output.mkdir(parents=True, exist_ok=True)
            candidate = safe_path(output / 'candidate.jsonl')
            manifest = safe_path(output / 'manifest.json')
            if candidate.exists() or manifest.exists():
                if (_read_regular(candidate, len(content)) != content
                        or strict_json(_read_regular(manifest, MAX_METADATA)) != result['manifest']):
                    raise RefreshError('output-exists-use-new-directory')
            else:
                with candidate.open('xb') as stream:
                    stream.write(content)
                with manifest.open('xb') as stream:
                    stream.write(json.dumps(result['manifest'], sort_keys=True).encode() + b'\n')
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0 if result['status'] == 'ready' else 2
    except (OSError, ValueError, RecursionError):
        print(json.dumps({'status': 'malformed', 'errors': ['metadata-io-or-output-invalid'],
                          'bindingId': binding.key, 'sourceAcceptance': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
