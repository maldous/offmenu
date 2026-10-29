"""Offline metadata binding, using the shared provenance/serialization contracts.

No PDF, image, workbook, source URL, nested artifact pointer or parser is opened.
Only the installed catalog's exact metadata input may be read by the CLI.
"""
import argparse
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat

from jsonschema import Draft202012Validator

from offmenu.refresh.acceptance import fingerprint
from offmenu.refresh.acquisition import MIN_TTL
from offmenu.refresh.core import canonical, safe_path, strict_json, timestamp
from offmenu.refresh.field_provenance import datum_pointers, field_origin_errors
from offmenu.refresh.serialization import encode_records

MAX_METADATA = 16 * 1024 * 1024
DECISIONS = (
    'canonicalTarget', 'nutrientId', 'compoundUnitId', 'perDayBasisId',
    'recommendationRelationId', 'populationApplicabilityId', 'sourceUseDecision',
    'independentEquivalenceReceipt', 'admissionAuthority', 'admissionDecision',
)
FIELDS = {
    'contextId': '/contextId',
    'recordIds': '/recordIds',
    'nutrientLabel': '/nutrientSourceIdentityEvidence/label/literal',
    'unitLiteral': '/compoundUnitAndTimeBasisEvidence/compoundUnitLiteral',
    'denominatorLiteral': '/compoundUnitAndTimeBasisEvidence/denominatorSuffixLiteral',
    'physicalBasis': '/compoundUnitAndTimeBasisEvidence/physicalOrServingBasis',
    'printedPublication': '/dateAndVersionEvidence/printedPublicationLiteral',
    'currentPolicyValidity': '/dateAndVersionEvidence/currentPolicyValidity',
    'comparisonLiteral': '/relationAndMarkerEvidence/comparisonLiteral',
    'subnoteBinding': '/relationAndMarkerEvidence/existingSubnoteBinding',
    'table4VitaminDStop': '/relationAndMarkerEvidence/Table4VitaminDNullSTOP',
    **{key: '/' + key for key in DECISIONS},
}
POLICY = {
    'version': 'worker32-retained-input-binding/1',
    'fields': FIELDS,
    'meaning': 'source-literal metadata candidate; not nutrient equivalence or acceptance',
    'minimumReuseSeconds': MIN_TTL,
    'decisionsMustRemainNull': list(DECISIONS),
}
POLICY_SHA256 = fingerprint(POLICY)

DATA_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': list(FIELDS),
    'properties': {
        'contextId': {'type': 'string', 'minLength': 1},
        'recordIds': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                      'items': {'type': 'string', 'minLength': 1}},
        **{key: {'type': 'string', 'minLength': 1} for key in
           ('nutrientLabel', 'unitLiteral', 'denominatorLiteral', 'printedPublication')},
        'physicalBasis': {'type': 'null'},
        'currentPolicyValidity': {'type': 'null'},
        'comparisonLiteral': {'enum': [None, '[Less than]', '[At least]']},
        'subnoteBinding': {'type': ['object', 'array', 'string', 'null']},
        'table4VitaminDStop': {'type': 'boolean'},
        **{key: {'type': 'null'} for key in DECISIONS},
    },
}
CONTEXT_LOCATOR_SCHEMA = {
    'type': 'object',
    'required': ['cohortApplicabilityEvidence', 'sourceArtifact', 'sourceRowSelector'],
    'properties': {
        'cohortApplicabilityEvidence': {'type': 'array', 'minItems': 1,
            'items': {'type': 'object', 'required': ['recordId'],
                      'properties': {'recordId': {'type': 'string', 'minLength': 1}}}},
        'sourceRowSelector': {'type': 'string', 'pattern': '^/'},
        'sourceArtifact': {'type': 'object', 'required': ['path', 'sha256'],
            'properties': {'path': {'type': 'string', 'minLength': 1},
                           'sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}}},
    },
}
RECORD_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['id', 'kind', 'schemaVersion', 'data', 'provenance'],
    'properties': {
        'id': {'type': 'string', 'minLength': 1},
        'kind': {'const': 'retainedSourceInput'},
        'schemaVersion': {'const': 'worker32-source-input/1'},
        'data': DATA_SCHEMA,
        'provenance': {'type': 'object', 'required': [
            'sourceId', 'releaseId', 'fetchedAt', 'fieldOrigins',
            'contextSelector', 'cohortSelector', 'sourceArtifactSelector', 'sourceRowSelector',
        ]},
    },
}


@dataclass(frozen=True)
class BindingSpec:
    key: str
    country: str
    source_id: str
    release_id: str
    metadata_path: str | None
    metadata_sha256: str | None
    acquired_at: str | None
    expected_contexts: int
    expected_record_refs: int
    holds: tuple = ()


def catalog():
    """Installed portfolio configuration; never a source-provided rights contract."""
    return strict_json(Path(__file__).with_name('catalog.json').read_bytes())


def specs():
    return tuple(BindingSpec(**{**entry['binding'], 'holds': tuple(entry['binding']['holds'])})
                 for entry in catalog()['sources'])


def resolve(value, pointer):
    for token in pointer.lstrip('/').split('/'):
        token = token.replace('~1', '/').replace('~0', '~')
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def origin(spec, index, context_id, pointer):
    return {'kind': 'source', 'sourceId': spec.source_id, 'releaseId': spec.release_id,
            'inputPath': 'retained-contexts.json', 'inputSha256': spec.metadata_sha256,
            'sourceRecordId': context_id, 'sourceField': f'/bindings/{index}' + pointer}


def metadata_semantics(spec, row):
    """Shared origin validation plus the portfolio's literal/null/STOP rules."""
    errors = set(field_origin_errors(
        row, {'retained-contexts.json': spec.metadata_sha256},
        policy_pins=(POLICY_SHA256,)))
    data = row['data']
    if any(data.get(key) is not None for key in DECISIONS):
        errors.add('target-decision-mutated')
    if data.get('contextId') == 'GB-source-row-39':
        if data.get('table4VitaminDStop') is not True or data.get('subnoteBinding') is not None:
            errors.add('vitamin-d-stop-mutated')
    # No /d expansion, conversion, equality inference or clinical currentness.
    if data.get('unitLiteral', '').rsplit('/', 1)[-1] != data.get('denominatorLiteral'):
        errors.add('literal-denominator-mismatch')
    return sorted(errors)


def semantic_validator(spec, raw):
    """Supply the exact metadata-coordinate checks to shared SourceContract.

    The caller still supplies independently reviewed rights/scope/IDs and schema.
    This callback does not construct or approve that contract.
    """
    if not isinstance(raw, bytes) or len(raw) > MAX_METADATA:
        raise ValueError('metadata-byte-bound-invalid')
    if hashlib.sha256(raw).hexdigest() != spec.metadata_sha256:
        raise ValueError('metadata-pin-mismatch')
    document = strict_json(raw)
    contexts = document['bindings']
    indices = {context['contextId']: index for index, context in enumerate(contexts)}
    if len(indices) != len(contexts):
        raise ValueError('context-identity-duplicate')

    def validate(row):
        errors = set(metadata_semantics(spec, row))
        try:
            context_id = row['data']['contextId']
            index = indices[context_id]
            expected = {key: deepcopy(resolve(contexts[index], pointer))
                        for key, pointer in FIELDS.items()}
            if (canonical(row['data']) != canonical(expected)
                    or row['id'] != spec.source_id + '/' + context_id
                    or row['provenance']['contextSelector'] != f'/bindings/{index}'
                    or row['provenance']['cohortSelector'] != f'/bindings/{index}/cohortApplicabilityEvidence'
                    or row['provenance']['sourceArtifactSelector'] != f'/bindings/{index}/sourceArtifact'
                    or row['provenance']['sourceRowSelector'] != contexts[index]['sourceRowSelector']):
                errors.add('source-coordinate-or-value-mismatch')
            expected_origins = {}
            for key, pointer in FIELDS.items():
                for leaf in datum_pointers(expected[key], '/data/' + key):
                    expected_origins[leaf] = origin(
                        spec, index, context_id, pointer + leaf[len('/data/' + key):])
            if row['provenance']['fieldOrigins'] != expected_origins:
                errors.add('source-field-selector-mismatch')
        except (KeyError, TypeError, IndexError, ValueError):
            errors.add('source-coordinate-or-value-mismatch')
        return sorted(errors)

    return validate


@dataclass(frozen=True)
class Inspection:
    report: dict
    candidate: bytes | None


def inspect(spec, raw, *, observed_at, validated_at=None, previous_candidate=None):
    """Pure, bounded metadata interface. No clock, network, disk or acceptance call.

    validated_at is observation provenance only and never resets acquisition age.
    Callers own real source permission and resource isolation. A ready result means
    only that this metadata candidate can be reviewed, never that data is accepted.
    """
    report = {'schemaVersion': 'worker32-binding-diagnostic/1', 'key': spec.key,
              'country': spec.country, 'sourceId': spec.source_id,
              'releaseId': spec.release_id, 'status': 'malformed', 'diagnostics': [],
              'originalAcquiredAt': spec.acquired_at, 'validatedAt': validated_at,
              'observedAt': observed_at, 'minimumReuseDays': 30,
              'cacheDecision': 'unknown', 'acquisitionAgeDays': None,
              'candidateSha256': None, 'candidateRecords': 0,
              'policySha256': POLICY_SHA256, 'sourceProcessingAuthorized': False,
              'acceptedRecords': 0, 'countryComplete': False, 'networkRequests': 0,
              'holds': list(spec.holds),
              'cachePlannerCapability': 'portfolio-intent-only-generic-pure-planner-absent'}

    def end(status, codes):
        report.update(status=status, diagnostics=sorted(set(codes)))
        return Inspection(report, None)

    # Holds are checked before inspecting any supplied payload or filesystem input.
    if spec.holds:
        return end('held', ['source-held'])
    if raw is None:
        return end('missing', ['metadata-input-missing'])
    try:
        now = timestamp(observed_at)
        if validated_at is not None and timestamp(validated_at) > now:
            return end('malformed', ['validation-clock-invalid'])
        if spec.acquired_at is None:
            return end('missing', ['original-acquisition-evidence-missing'])
        acquired = timestamp(spec.acquired_at)
        if validated_at is not None and timestamp(validated_at) < acquired:
            return end('malformed', ['validation-clock-invalid'])
        age = (now - acquired).total_seconds()
        if age < 0:
            return end('malformed', ['acquisition-clock-invalid'])
        report['acquisitionAgeDays'] = int(age // 86400)
        if not isinstance(raw, bytes) or len(raw) > MAX_METADATA:
            return end('malformed', ['metadata-byte-bound-invalid'])
        if hashlib.sha256(raw).hexdigest() != spec.metadata_sha256:
            return end('malformed', ['metadata-pin-mismatch'])
        document = strict_json(raw)
        canonical(document)  # Also reject overflowing JSON numbers.
        if (document['schema'] != 'offmenu-gb-source-field-evidence-binding/1'
                or document['contexts'] != spec.expected_contexts
                or document['records'] != spec.expected_record_refs
                or len(document['bindings']) != spec.expected_contexts):
            return end('malformed', ['metadata-inventory-mismatch'])
        errors, rows, context_ids, record_ids = set(), [], set(), set()
        for index, context in enumerate(document['bindings']):
            try:
                if not Draft202012Validator(CONTEXT_LOCATOR_SCHEMA).is_valid(context):
                    errors.add('source-input-locator-missing')
                    continue
                data = {key: deepcopy(resolve(context, pointer))
                        for key, pointer in FIELDS.items()}
                if not Draft202012Validator(DATA_SCHEMA).is_valid(data):
                    errors.add('metadata-field-invalid')
                    continue
                if data['contextId'] in context_ids:
                    errors.add('context-identity-duplicate')
                context_ids.add(data['contextId'])
                if record_ids.intersection(data['recordIds']):
                    errors.add('record-reference-duplicate')
                cohort_ids = [item['recordId'] for item in context['cohortApplicabilityEvidence']]
                if len(cohort_ids) != len(data['recordIds']) or set(cohort_ids) != set(data['recordIds']):
                    errors.add('cohort-record-reference-mismatch')
                record_ids.update(data['recordIds'])
                origins = {}
                for key, pointer in FIELDS.items():
                    for leaf in datum_pointers(data[key], '/data/' + key):
                        suffix = leaf[len('/data/' + key):]
                        origins[leaf] = origin(spec, index, data['contextId'], pointer + suffix)
                row = {'id': spec.source_id + '/' + data['contextId'],
                       'kind': 'retainedSourceInput', 'schemaVersion': 'worker32-source-input/1',
                       'data': data, 'provenance': {
                           'sourceId': spec.source_id, 'releaseId': spec.release_id,
                           'fetchedAt': spec.acquired_at, 'fieldOrigins': origins,
                           'contextSelector': f'/bindings/{index}',
                           'cohortSelector': f'/bindings/{index}/cohortApplicabilityEvidence',
                           'sourceArtifactSelector': f'/bindings/{index}/sourceArtifact',
                           'sourceRowSelector': context['sourceRowSelector'],
                       }}
                errors.update(metadata_semantics(spec, row))
                rows.append(row)
            except (KeyError, TypeError, IndexError, ValueError):
                errors.add('metadata-field-missing')
        if len(record_ids) != spec.expected_record_refs:
            errors.add('record-reference-inventory-mismatch')
        if errors:
            return end('malformed', errors)
        # Stale metadata is diagnosable but cannot silently trigger acquisition.
        if age >= MIN_TTL:
            report['cacheDecision'] = 'revalidation-review-required-no-download'
            return end('stale-input', ['original-acquisition-age-exceeds-cache-window'])
        candidate = encode_records(rows)
        report.update(status='ready-metadata', cacheDecision='reuse-retained-metadata-no-download',
                      candidateRecords=len(rows), candidateSha256=hashlib.sha256(candidate).hexdigest(),
                      action='verified-no-op' if previous_candidate == candidate else 'metadata-candidate-built')
        return Inspection(report, candidate)
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError):
        return end('malformed', ['metadata-document-invalid'])


def inspect_many(bindings, payloads, **observation):
    """A missing/held/malformed source never suppresses another source diagnostic."""
    return [inspect(spec, payloads.get(spec.key), **observation)
            for spec in sorted(bindings, key=lambda item: item.key)]


def _read_metadata(path):
    """One bounded regular-file descriptor; never block opening a FIFO/device.

    The catalog chooses the path. Inspect the descriptor that is actually read,
    rather than checking a pathname and reopening it after a possible replacement.
    """
    path = safe_path(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_METADATA:
            raise ValueError('metadata-file-bound-or-type-invalid')
        chunks, remaining = [], MAX_METADATA + 1
        while remaining:
            chunk = os.read(descriptor, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b''.join(chunks)
        after = os.fstat(descriptor)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if len(raw) > MAX_METADATA or identity(before) != identity(after):
            raise ValueError('metadata-file-bound-or-change-invalid')
        return raw
    finally:
        os.close(descriptor)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observed-at', required=True, help='Explicit UTC clock; no wall-clock inference')
    parser.add_argument('--validated-at', help='Metadata validation observation; not acquisition')
    parser.add_argument('--key', action='append', choices=[s.key for s in specs()])
    parser.add_argument('--emit-candidate', action='store_true',
                        help='One selected ready binding to stdout as metadata JSONL; no file writes')
    args = parser.parse_args(argv)
    if args.emit_candidate and (not args.key or len(args.key) != 1):
        parser.error('--emit-candidate requires exactly one --key')
    results = []
    for spec in specs():
        if args.key and spec.key not in args.key:
            continue
        raw = None
        io_error = False
        if not spec.holds and spec.metadata_path is not None:
            try:
                # No recursive pointer resolution. Installed metadata path only.
                raw = _read_metadata(spec.metadata_path)
            except FileNotFoundError:
                pass
            except (OSError, ValueError):
                io_error = True
        item = inspect(spec, raw, observed_at=args.observed_at, validated_at=args.validated_at)
        if io_error:
            item.report.update(status='malformed', diagnostics=['metadata-input-io-invalid'])
        if args.emit_candidate and item.candidate is not None:
            print(item.candidate.decode('utf-8'), end='')
            return 0
        results.append(item.report)
    installed = catalog()
    selected = {row['key'] for row in results}
    declarations = [declaration for source in installed['sources']
                    if source['binding']['key'] in selected
                    for declaration in source['sourceInputDeclarations']]
    print(canonical({'bindings': results, 'sourceInputDeclarations': declarations,
                     'sharedCapabilityDependencies': installed['sharedCapabilityDependencies'],
                     'acceptance': 'not-performed'}).decode(), end='')
    return 0 if all(r['status'] == 'ready-metadata' for r in results) else 2


if __name__ == '__main__':
    raise SystemExit(main())
