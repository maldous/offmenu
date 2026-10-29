"""Owned PRODUCT evidence adapter; no source discovery, file reader or admission.

The caller supplies already-parsed, operation-selected records. Generated fixtures
exercise this adapter while real source selection remains with00. Canonical serialization and source-key suffixes retain the frozen56 semantics;
contracts are repository-local or injected, and protection is caller-injected.
No canonical ingredient/category concepts, accepted matches or first56 objects
are created or changed by this adapter.
"""
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import types
from urllib.parse import quote

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_SHA = 'b4fa5afb2f8cc77326299b55ccd75b93f121e807317fdc1f9953709e98faa0aa'
SCHEMA_SHA = 'f1968889c5e1500e841517bd7546af9c223bf97dce40bb68a3f584e93559298c'
SHARED_MODULE_VERSION = 'offmenu.ingredient-vocabulary-generation/1'
SHARED_CURATION_VERSION = 'english-pivot-selected-source-rules/1'
ADAPTER_VERSION = 'offmenu.product-generation2-adapter/1'
CANDIDATE_PREFIX = 'urn:offmenu:candidate:generation2:worker57:'
MAX_INPUT = 262144
MAX_RECORDS = 64
MAX_RESOURCES = 128
MAX_RELATIONS = 256
MAX_OUTPUT = 16 * 1024 * 1024


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return sha256(canonical(value)).hexdigest()


def _id(kind, key):
    return 'urn:offmenu:vocabulary:' + kind + ':' + key


def _escape_pointer(key):
    return key.replace('~', '~0').replace('/', '~1')


def load_shared_contract(*, protected_ids, contract_raw=None, schema_raw=None):
    """Resolve qualified repository code-data only; never read a worker root.

    The caller supplies the current protected-ID snapshot for this operation.
    Only its count/digest enter the candidate; no copied registry is emitted.
    """
    if type(protected_ids) not in (tuple, list) or len(protected_ids) > 16384:
        raise ValueError('explicit bounded protected IDs required')
    if any(type(x) is not str or not x.startswith('urn:offmenu:') for x in protected_ids):
        raise ValueError('protected ID shape')
    if contract_raw is None:
        contract_raw = (REPO_ROOT / 'contracts/corpus/common-data-contract.json').read_bytes()
    if schema_raw is None:
        schema_raw = (REPO_ROOT / 'contracts/corpus/common-data.schema.json').read_bytes()
    for raw, expected in ((contract_raw, CONTRACT_SHA), (schema_raw, SCHEMA_SHA)):
        if type(raw) is not bytes or len(raw) > 131072 or sha256(raw).hexdigest() != expected:
            raise ValueError('shared contract/schema pin changed')
    contract, schema = json.loads(contract_raw), json.loads(schema_raw)
    receipt = {'commonSchemaVersion': 'offmenu-common/1',
        'moduleVersion': SHARED_MODULE_VERSION, 'curationVersion': SHARED_CURATION_VERSION,
        'allGeneration1ObjectIdsExcludedFromMutation': sorted(set(protected_ids))}
    shared = types.SimpleNamespace(canonical=canonical, digest=digest, _id=_id, _pointer=_escape_pointer)
    return receipt, shared, contract, schema


def _string(value, label, maximum=4096):
    if type(value) is not str or not value.strip() or len(value) > maximum:
        raise ValueError(label)
    return value


def _pointer(value):
    if type(value) is not str or len(value) > 4096 or not value.startswith('/'):
        raise ValueError('explicit source pointer required')
    return value


def build_product_generation(records, *, generation_version, actor_reference,
                             operation_reference, protected_ids, reference_ids=(),
                             input_kind='synthetic-fixture', contract_raw=None, schema_raw=None):
    """Preserve source records/fields and proposed links; never grant body access.

    operation_reference records caller authority provenance, not a permission
    assertion manufactured by this function. A real invocation requires00's
    selected data operation outside this pure adapter.
    """
    receipt, shared, contract, _ = load_shared_contract(protected_ids=protected_ids, contract_raw=contract_raw, schema_raw=schema_raw)
    canonical, digest = shared.canonical, shared.digest
    _string(generation_version, 'generation version required', 256)
    _string(actor_reference, 'actor required', 2048)
    _string(operation_reference, 'operation reference required', 2048)
    if input_kind not in ('synthetic-fixture', 'selected-parsed-source'):
        raise ValueError('explicit input kind')
    if type(records) is not list or len(records) > MAX_RECORDS:
        raise ValueError('record bound')
    if len(canonical(records)) > MAX_INPUT:
        raise ValueError('input byte bound')
    if type(reference_ids) not in (list, tuple) or len(reference_ids) > 512:
        raise ValueError('bounded reference IDs required')
    references = set(reference_ids)
    if any(type(x) is not str or not x.startswith('urn:offmenu:') for x in references):
        raise ValueError('explicit reference ID')
    excluded = set(receipt['allGeneration1ObjectIdsExcludedFromMutation'])
    scope = {'visibility': 'private', 'ownerId': actor_reference,
             'reuseScope': 'worker57-source-evidence-candidate; independent review and00 adoption separate'}
    common = {'schemaVersion': receipt['commonSchemaVersion'], 'resources': [],
              'assertions': [], 'relations': [], 'citations': [], 'translations': []}
    definitions, seen_records, joins, conflicts = {}, {}, [], []
    component_count = field_count = duplicate_count = 0

    def identifier(kind, key):
        # Reuse56's source-key suffix construction, with this disjoint candidate
        # namespace. These IDs are never accepted vocabulary/registry identities.
        suffix = shared._id(kind, digest(key)).removeprefix('urn:offmenu:vocabulary:')
        return CANDIDATE_PREFIX + suffix

    def register(obj):
        ident = obj['id']
        if ident in excluded:
            raise ValueError('first-generation object mutation excluded')
        if ident in definitions and definitions[ident] != obj:
            raise ValueError('conflicting object identity')
        definitions[ident] = deepcopy(obj)
        return obj

    def text(value, language, citation, key):
        if type(value) is not str or len(value) > 4096:
            raise ValueError('bounded source text')
        if type(language) is not str or not re.fullmatch(r'[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*', language):
            raise ValueError('source language or und required')
        return register({'kind': 'text', 'id': identifier('text', key),
            'language': language, 'value': value,
            'sourceTextSha256': sha256(value.encode('utf-8')).hexdigest(),
            'status': 'source-asserted', 'citationIds': [citation]})

    def value(raw, citation, key, depth=0):
        if depth > 8:
            raise ValueError('source value depth')
        if raw is None:
            return {'kind': 'null', 'value': None}
        if type(raw) is bool:
            return {'kind': 'boolean', 'value': raw}
        if type(raw) in (int, float):
            if not math.isfinite(raw):
                raise ValueError('nonfinite source value')
            return {'kind': 'number', 'value': raw}
        if type(raw) is str:
            return text(raw, 'und', citation, key)
        if type(raw) is list and len(raw) <= 64:
            return {'kind': 'list', 'items': [value(x, citation, [key, i], depth + 1) for i, x in enumerate(raw)]}
        if type(raw) is dict and len(raw) <= 64 and all(type(k) is str and len(k) <= 256 for k in raw):
            return {'kind': 'structure', 'fields': {k: value(raw[k], citation, [key, k], depth + 1) for k in sorted(raw)}}
        raise ValueError('bounded typed source value required')

    def resource(ident, names, citation):
        obj = register({'id': ident, 'type': contract['types']['SourceRecord']['id'],
            'identityStatus': 'source-scoped', 'names': names,
            'citationIds': [citation], 'scope': deepcopy(scope)})
        common['resources'].append(obj)

    def relation(subject, predicate, target, citation, pointer):
        obj = register({'id': identifier('relation', [subject, predicate, target, pointer]),
            'subjectId': subject, 'predicateId': contract['relationshipVocabulary'][predicate]['id'],
            'objectId': target, 'status': 'candidate', 'citationIds': [citation],
            'sourcePath': pointer, 'scope': deepcopy(scope)})
        common['relations'].append(obj)

    allowed = {'sourceId', 'sourceVersion', 'sourceRecordId', 'assetSha256',
               'originalUrl', 'license', 'attribution', 'sourcePath', 'names',
               'fields', 'components', 'crosswalks'}
    for row in records:
        if type(row) is not dict or set(row) - allowed:
            raise ValueError('selected product evidence envelope')
        for k in ('sourceId', 'sourceVersion', 'sourceRecordId', 'originalUrl', 'license', 'attribution'):
            _string(row.get(k), 'explicit source provenance:' + k)
        if not re.fullmatch('[a-f0-9]{64}', row.get('assetSha256', '')):
            raise ValueError('selected source asset digest')
        pointer = _pointer(row.get('sourcePath'))
        key = [row['sourceId'], row['sourceVersion'], row['assetSha256'], row['sourceRecordId'], pointer]
        key_sha = digest(key)
        if key_sha in seen_records:
            if seen_records[key_sha] != row:
                raise ValueError('conflicting repeated source record')
            duplicate_count += 1
            continue
        seen_records[key_sha] = deepcopy(row)
        cid = identifier('citation', key)
        common['citations'].append(register({'id': cid, 'sourceId': row['sourceId'],
            'originalRecordId': row['sourceRecordId'], 'originalUrl': row['originalUrl'],
            'revisionId': row['sourceVersion'], 'contentSha256': row['assetSha256'],
            'license': row['license'], 'attribution': row['attribution'],
            'sourcePath': pointer, 'scope': deepcopy(scope)}))
        product_id = identifier('product-observation', key)
        names = row.get('names', [])
        if type(names) is not list or len(names) > 8:
            raise ValueError('bounded source names')
        out_names = []
        for i, name in enumerate(names):
            if type(name) is not dict or set(name) != {'value', 'language'}:
                raise ValueError('source name language must be explicit')
            out_names.append(text(name['value'], name['language'], cid, [key, 'name', i]))
        resource(product_id, out_names, cid)
        subjects_by_pointer = {pointer: product_id}
        fields = row.get('fields', {})
        if type(fields) is not dict or len(fields) > 32:
            raise ValueError('selected source fields bound')
        for field in sorted(fields):
            _string(field, 'source field key', 256)
            fp = pointer + '/' + shared._pointer(field)
            common['assertions'].append(register({'id': identifier('assertion', [key, field]),
                'subjectId': product_id,
                'propertyId': contract['sourcePropertyExtensions']['namespace'] + quote(field, safe=''),
                'value': value(fields[field], cid, [key, field]), 'status': 'source-asserted',
                'citationIds': [cid], 'sourcePath': fp, 'scope': deepcopy(scope)}))
            field_count += 1
        components = row.get('components', [])
        if type(components) is not list or len(components) > 32:
            raise ValueError('component bound')
        for component in components:
            if type(component) is not dict or set(component) != {'text', 'language', 'sourcePath'}:
                raise ValueError('source component evidence only; no canonical class or fraction')
            cp = _pointer(component['sourcePath'])
            _string(component['text'], 'source component text')
            if cp == pointer or not cp.startswith(pointer + '/'):
                raise ValueError('component source pointer outside product record')
            component_id = identifier('component-observation', [key, cp])
            if component_id in definitions:
                raise ValueError('duplicate component pointer')
            resource(component_id, [text(component['text'], component['language'], cid, [key, cp])], cid)
            subjects_by_pointer[cp] = component_id
            relation(component_id, 'partOf', product_id, cid, cp)
            component_count += 1
        crosswalks = row.get('crosswalks', [])
        if type(crosswalks) is not list or len(crosswalks) > 8:
            raise ValueError('crosswalk bound')
        seen_proposals = set()
        for proposal in crosswalks:
            if type(proposal) is not dict or set(proposal) != {'targetId', 'sourcePath', 'subjectSourcePath', 'reason'}:
                raise ValueError('explicit crosswalk subjectSourcePath required; no acceptance flags')
            if proposal['targetId'] not in references:
                raise ValueError('crosswalk target requires caller-selected read-only reference')
            subject_pointer = _pointer(proposal['subjectSourcePath'])
            subject_id = subjects_by_pointer.get(subject_pointer)
            if subject_id is None:
                raise ValueError('crosswalk subject must be an explicit product/component occurrence')
            pp = _pointer(proposal['sourcePath'])
            if pp != subject_pointer and not pp.startswith(subject_pointer + '/'):
                raise ValueError('crosswalk evidence outside selected subject occurrence')
            evidence_subject = max((q for q in subjects_by_pointer if pp == q or pp.startswith(q + '/')), key=len)
            if evidence_subject != subject_pointer:
                raise ValueError('component-local evidence cannot support a different or whole-product subject')
            _string(proposal['reason'], 'crosswalk evidence reason')
            proposal_key = (subject_id, proposal['targetId'], pp)
            if proposal_key in seen_proposals:
                raise ValueError('duplicate crosswalk evidence requires explicit reconciliation')
            seen_proposals.add(proposal_key)
            relation(subject_id, 'candidateMatch', proposal['targetId'], cid, pp)
            joins.append({'sourceResourceId': subject_id, 'productResourceId': product_id, **deepcopy(proposal),
                          'state': 'proposed-unreviewed', 'acceptedSemanticMatch': False})
        conflicts.append({'sourceResourceId': product_id, 'state': 'ambiguous-unknown',
            'reason': 'NO_QUALIFIED_SHARED_CATEGORY_MAPPING', 'compositionQualified': False,
            'ingredientClassificationRequiredForLookup': False})
    if len(common['resources']) > MAX_RESOURCES or len(common['relations']) > MAX_RELATIONS:
        raise ValueError('output resource/relation bound')
    packet = {'common': common, 'curation': {
        'generationVersion': generation_version, 'moduleVersion': ADAPTER_VERSION,
        'sharedModuleVersion': receipt['moduleVersion'], 'curationVersion': receipt['curationVersion'],
        'commonSHA256': digest(common), 'actorReference': actor_reference,
        'operationReference': operation_reference, 'inputKind': input_kind,
        'state': 'synthetic-fixture-only' if input_kind == 'synthetic-fixture' else 'private-source-evidence-author-candidate',
        'accepted': False, 'requiresIndependentReviewAnd00Adoption': True,
        'sources': [{'sourceId': k[0], 'sourceVersion': k[1], 'assetSha256': k[2]} for k in sorted({tuple([r['sourceId'], r['sourceVersion'], r['assetSha256']]) for r in records})],
        'readOnlyReferenceIds': sorted(references), 'proposedCrosswalks': joins,
        'categoryDispositions': conflicts,
        'counts': {'inputRecords': len(records), 'uniqueSourceRecords': len(seen_records),
            'duplicateSourceRecords': duplicate_count, 'sourceFieldsPreserved': field_count,
            'componentObservations': component_count, 'proposedCrosswalks': len(joins),
            'resources': len(common['resources']), 'relations': len(common['relations']),
            'realSourceRows': 0 if input_kind == 'synthetic-fixture' else len(seen_records),
            'syntheticFixtureRecords': len(records) if input_kind == 'synthetic-fixture' else 0,
            'canonicalConceptsMinted': 0, 'acceptedSemanticMappings': 0,
            'independentlyReviewed': 0, 'goldAdmitted': 0},
        'sharedContractSha256': CONTRACT_SHA, 'sharedSchemaSha256': SCHEMA_SHA,
        'protectedDefinitionCount': len(excluded), 'protectedDefinitionIdsDigest': digest(sorted(excluded))}}
    if len(canonical(packet)) > MAX_OUTPUT:
        raise ValueError('output byte bound')
    return packet


def inspect_product_generation(packet, source_record_id=None, *, protected_ids, contract_raw=None, schema_raw=None):
    """Pure readback of a NEW candidate object, no store or source lookup."""
    receipt, shared, contract, _ = load_shared_contract(protected_ids=protected_ids, contract_raw=contract_raw, schema_raw=schema_raw)
    if shared.digest(packet['common']) != packet['curation']['commonSHA256']:
        raise ValueError('candidate changed')
    common, curation = packet['common'], packet['curation']
    counts = curation['counts']
    if (curation.get('accepted') is not False
            or curation.get('requiresIndependentReviewAnd00Adoption') is not True
            or curation.get('moduleVersion') != ADAPTER_VERSION
            or curation.get('protectedDefinitionIdsDigest') != shared.digest(sorted(set(protected_ids)))
            or curation.get('protectedDefinitionCount') != len(set(protected_ids))
            or any(counts.get(k) != 0 for k in ('canonicalConceptsMinted', 'acceptedSemanticMappings', 'independentlyReviewed', 'goldAdmitted'))
            or counts.get('resources') != len(common['resources'])
            or counts.get('relations') != len(common['relations'])):
        raise ValueError('candidate admission/count boundary changed')
    local = {r['id'] for r in common['resources']}
    refs = set(curation['readOnlyReferenceIds'])
    citations = {x['id'] for x in common['citations']}
    allowed_predicates = {contract['relationshipVocabulary'][k]['id'] for k in ('partOf', 'candidateMatch')}
    if (local.intersection(receipt['allGeneration1ObjectIdsExcludedFromMutation'])
            or any(not ident.startswith(CANDIDATE_PREFIX) for ident in local)
            or any(r['type'] != contract['types']['SourceRecord']['id'] or r['identityStatus'] != 'source-scoped' for r in common['resources'])
            or any(a['status'] != 'source-asserted' or a['subjectId'] not in local for a in common['assertions'])
            or any(r['status'] != 'candidate' or r['predicateId'] not in allowed_predicates
                   or r['subjectId'] not in local or r['objectId'] not in local | refs for r in common['relations'])
            or any(not set(x['citationIds']) <= citations for k in ('resources', 'assertions', 'relations') for x in common[k])):
        raise ValueError('candidate source/reference boundary changed')
    if source_record_id is None:
        return deepcopy(packet['curation']['counts'])
    citations = {c['id'] for c in packet['common']['citations'] if c['originalRecordId'] == source_record_id}
    resources = [r for r in packet['common']['resources'] if citations.intersection(r['citationIds'])]
    ids = {r['id'] for r in resources}
    return {'resources': deepcopy(resources),
            'sourceAssertions': deepcopy([a for a in packet['common']['assertions'] if a['subjectId'] in ids]),
            'relations': deepcopy([r for r in packet['common']['relations'] if r['subjectId'] in ids]),
            'acceptedSemanticMappings': 0, 'actualProductFit': False}


def persist_owned_candidate(owned_root, name, packet, *, protected_ids, contract_raw=None, schema_raw=None):
    """Exclusive/idempotent private child of57's root; no external writes."""
    _, shared, _, _ = load_shared_contract(protected_ids=protected_ids, contract_raw=contract_raw, schema_raw=schema_raw)
    inspect_product_generation(packet, protected_ids=protected_ids, contract_raw=contract_raw, schema_raw=schema_raw)
    if not re.fullmatch(r'(?:fixture|candidate)-[a-z0-9][a-z0-9-]{0,80}', name):
        raise ValueError('owned candidate child name required')
    root = Path(owned_root)
    if not root.is_absolute() or root.is_symlink() or root.resolve(strict=True) != root or not root.is_dir():
        raise ValueError('explicit existing exclusively-owned root required')
    directory = root / name
    if directory.is_symlink():
        raise ValueError('owned output must not be a symlink')
    raw = shared.canonical(packet) + b'\n'
    if len(raw) > MAX_OUTPUT:
        raise ValueError('output byte bound')
    manifest = {'generationVersion': packet['curation']['generationVersion'],
        'generationSHA256': sha256(raw).hexdigest(), 'commonSHA256': shared.digest(packet['common']),
        'state': packet['curation']['state'], 'inputKind': packet['curation']['inputKind'],
        'accepted': False, 'counts': deepcopy(packet['curation']['counts'])}
    if directory.exists():
        if (directory / 'generation.json').is_symlink() or (directory / 'manifest.json').is_symlink():
            raise ValueError('owned output file symlink')
        if (directory / 'generation.json').read_bytes() != raw or json.loads((directory / 'manifest.json').read_text()) != manifest:
            raise FileExistsError('owned immutable candidate differs')
        return {**manifest, 'reusedIdenticalOwnedOutput': True}
    directory.mkdir(mode=0o700)
    with (directory / 'generation.json').open('xb') as handle:
        handle.write(raw)
    with (directory / 'manifest.json').open('x') as handle:
        json.dump(manifest, handle, sort_keys=True, indent=2)
        handle.write('\n')
    return {**manifest, 'reusedIdenticalOwnedOutput': False}
