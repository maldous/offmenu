"""Synthetic source-reference packet preparation, not a Gold admission API.

These projected identity/basis bindings are generated fixtures for the SR
profile. Legacy builders do not grant these source-reference seeds.
No retained corpus, source database, cache, network or filesystem is accessed.
"""
import copy
import hashlib
import json

FOOD_TYPE = 'urn:offmenu:type:FoodPreparation'
NUTRIENT_TYPE = 'urn:offmenu:type:NutrientDefinition'
RELEASE = 'generated-sr-fixture-release-1'
PURPOSE = 'Synthetic private-purpose source-reference fixture only; no real source facts or admission.'
FOOD_RAW = 'urn:fixture:sr:food:101'
FOOD_COOKED = 'urn:fixture:sr:food:102'
UNITS = (
    ('1004', 'G', 'g', 'mass', '0', 'SOURCE_ASSUMED_ZERO'),
    ('1093', 'MG', 'mg', 'mass', '2.50', 'SOURCE_CALCULATED'),
    ('1106', 'UG', 'µg', 'mass', '0.020', 'DERIVATION_NOT_SUPPLIED'),
    ('1008', 'KCAL', 'kcal', 'energy', '60', 'SOURCE_REPORTED_ANALYTICAL'),
    ('1062', 'kJ', 'kJ', 'energy', '251', 'SOURCE_CALCULATED'),
    ('1104', 'IU', 'usda:IU', 'unknown', '30', 'SOURCE_REPORTED_ANALYTICAL'),
)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def bind_packet(packet, qualification):
    qualification['packet_sha256'] = digest(packet)


def source_reference_fixture(*, identity_only=False):
    """Return detached generated Common/packet/qualification projections.

    Qualification hashes stand for synthetic reviewer decisions. They are not
    independently reviewed real-source permissions, unit mappings or documents.
    """
    manifest = digest(['generated-source-reference-fixture', 1])
    policy = digest(['generated-independent-review-placeholder', 1])
    packet = {
        'schema_version': 'offmenu.gold-input/1', 'data_class': 'synthetic',
        'watermark': {'eligible_manifest_sha256': manifest, 'domains': [{
            'domain': 'ingredients', 'snapshot_id': RELEASE,
            'committed_watermark': RELEASE, 'manifest_sha256': manifest}]},
        'common': {'schemaVersion': 'offmenu-common/1', 'resources': [],
                   'assertions': [], 'relations': [], 'citations': [], 'translations': []},
        'occurrences': [], 'metrics': [], 'observations': [], 'english_bindings': [],
    }
    q = {'schema_version': 'offmenu.gold-qualification/1', 'policy_sha256': policy,
         'records': [], 'supports': [], 'cache_entries': [], 'comparisons': [],
         'source_reference_identifier_bindings': [], 'observation_basis_bindings': []}
    scope = {'visibility': 'public', 'reuseScope': PURPOSE}

    def support(kind, target, cid, support_scope, evidence):
        q['supports'].append({'target_kind': kind, 'target_id': target,
                              'citation_id': cid, 'support_scope': support_scope,
                              'evidence_sha256': digest(evidence)})

    def assertion(rid, suffix, property_id, value, cid, pointer):
        a = {'id': rid + ':' + suffix, 'subjectId': rid, 'propertyId': property_id,
             'value': value, 'status': 'source-asserted', 'citationIds': [cid],
             'sourcePath': pointer, 'scope': copy.deepcopy(scope)}
        packet['common']['assertions'].append(a)
        support('assertion', a['id'], cid, 'field', a)
        return a

    def resource(rid, typ, native_id, kind, original, source_name, label):
        cid = rid + ':citation'; oid = rid + ':occurrence'
        packet['common']['citations'].append({
            'id': cid, 'sourceId': 'generated-source-reference',
            'originalRecordId': native_id, 'originalUrl': 'https://example.invalid/generated-sr/' + native_id,
            'sourcePath': '/' + kind + '/' + native_id, 'sourceDate': 'generated-date-unknown',
            'license': 'Synthetic test data', 'attribution': 'Generated fixture, no real USDA data',
            'scope': copy.deepcopy(scope)})
        names = []
        for suffix, value in [('source-description', source_name), ('editorial-concept', label)]:
            text = {'kind': 'text', 'id': rid + ':' + suffix, 'language': 'en', 'value': value,
                    'sourceTextSha256': hashlib.sha256(value.encode()).hexdigest(),
                    'status': 'reviewed', 'citationIds': [cid]}
            names.append(text); support('text', text['id'], cid, 'field', text)
        r = {'id': rid, 'type': typ, 'identityStatus': 'source-scoped', 'names': names,
             'citationIds': [cid], 'scope': copy.deepcopy(scope)}
        packet['common']['resources'].append(r)
        occurrence = {'occurrence_id': oid, 'domain': 'ingredients',
                      'source_key': 'usda-files:' + kind, 'source_version': RELEASE,
                      'record_id': native_id, 'content_sha256': digest(original),
                      'normalized_artifact_sha256': digest(['generated-artifact', original]),
                      'committed_watermark': RELEASE, 'resource_ids': [rid],
                      'citation_ids': [cid], 'source_original': original}
        packet['occurrences'].append(occurrence)
        q['records'].append({k: occurrence[k] for k in ['occurrence_id', 'content_sha256',
                            'normalized_artifact_sha256', 'committed_watermark']} |
                           {'rights_state': 'permitted', 'operation_evidence_sha256': manifest,
                            'review_evidence_sha256': policy, 'reason': 'Synthetic fixture only'})
        support('resource', rid, cid, 'record', occurrence)
        prop = 'usda:fdc-id' if kind == 'sr_legacy_food' else 'usda:nutrient-id'
        a = assertion(rid, 'native-id', prop, {'kind': 'identifier', 'value': native_id}, cid,
                      '/food/fdc_id' if kind == 'sr_legacy_food' else '/nutrient/id')
        q['source_reference_identifier_bindings'].append({
            'resource_id': rid, 'assertion_id': a['id'], 'occurrence_id': oid,
            'source_kind': kind, 'identifier_system': 'USDA-FDC' if kind == 'sr_legacy_food' else 'USDA-nutrient',
            'native_id': native_id, 'source_version': RELEASE,
            'evidence_sha256': digest({'resource': r, 'identity': a, 'occurrence': occurrence})})
        return cid, oid

    native_rows = []
    for native_id, source_unit, unit, dimension, amount, method in UNITS:
        native_rows.append({'id': 'generated-row-' + native_id, 'fdc_id': '101',
                            'nutrient_id': native_id, 'amount': amount,
                            'data_points': '0', 'min': '', 'max': '', 'median': '', 'LOQ': '',
                            'footnote': '', 'min_year_acquired': '', 'percent_daily_value': '',
                            'derivation_id': '' if method == 'DERIVATION_NOT_SUPPLIED' else 'generated-' + native_id,
                            'assay_date': None, 'country': None})
    for fid, rid, description in [
            ('101', FOOD_RAW, 'Synthetic carrots, raw'),
            ('102', FOOD_COOKED, 'Synthetic carrots, cooked, boiled, drained, without salt')]:
        original = {'synthetic': True, 'food': {'fdc_id': fid, 'data_type': 'sr_legacy_food',
                    'description': description, 'publication_date': 'generated-publication-date'},
                    'sr_legacy_food': {'fdc_id': fid, 'NDB_number': '00' + fid},
                    'food_nutrient': copy.deepcopy(native_rows) if fid == '101' else [],
                    'source_country': None, 'source_language': None}
        cid, oid = resource(rid, FOOD_TYPE, fid, 'sr_legacy_food', original, description, 'Carrot')
        assertion(rid, 'ndb-number', 'usda:ndb-number', {'kind': 'identifier', 'value': '00' + fid},
                  cid, '/sr_legacy_food/NDB_number')
        assertion(rid, 'data-type', 'usda:data-type',
                  {'kind': 'expression', 'syntax': 'literal-source-text', 'value': 'sr_legacy_food'},
                  cid, '/food/data_type')

    for native_id, source_unit, unit, dimension, amount, method in UNITS:
        rid = 'urn:fixture:sr:nutrient:' + native_id
        original = {'synthetic': True, 'nutrient': {'id': native_id,
                    'name': 'Synthetic nutrient ' + native_id, 'unit_name': source_unit,
                    'nutrient_nbr': 'generated-' + native_id}}
        cid, _ = resource(rid, NUTRIENT_TYPE, native_id, 'nutrient', original,
                          original['nutrient']['name'], 'Synthetic ' + source_unit + ' reference term')
        assertion(rid, 'native-unit', 'usda:nutrient-unit',
                  {'kind': 'expression', 'syntax': 'literal-source-text', 'value': source_unit}, cid,
                  '/nutrient/unit_name')
        if identity_only:
            continue
        metric = rid
        packet['metrics'].append({'metric_id': metric, 'name_en': 'Synthetic metric ' + native_id,
                                 'dimension': dimension, 'canonical_unit_id': unit, 'citation_ids': [cid]})
        support('metric', metric, cid, 'definition', original)
        basis = {'kind': 'quantity', 'value': 100, 'unitId': 'g', 'dimension': 'mass',
                 'sourceValue': '100', 'sourceUnit': 'g', 'qualifiers': []}
        value = {'kind': 'quantity', 'value': float(amount), 'unitId': unit, 'dimension': dimension,
                 'sourceValue': amount, 'sourceUnit': source_unit, 'qualifiers': [], 'basis': basis}
        a = assertion(FOOD_RAW, 'amount-' + native_id, metric, value, FOOD_RAW + ':citation',
                      '/food_nutrient/' + str(len(packet['observations'])) + '/amount')
        row = next(r for r in native_rows if r['nutrient_id'] == native_id)
        obs = {'observation_id': FOOD_RAW + ':observation:' + native_id, 'assertion_id': a['id'],
               'metric_id': metric, 'kind': 'observed', 'comparable': None,
               'context': {'basis': copy.deepcopy(basis), 'method': method, 'source_fields': copy.deepcopy(row),
                           'source_reporting_only': True, 'independent_assay_verified': False,
                           'recipe_transfer_qualified': False,
                           'country': None, 'source_date': None, 'assay_date': None,
                           'source_publication_date': 'generated-publication-date',
                           'source_archive_release': RELEASE, 'source_origin_vintage': 'generated-origin-vintage',
                           'uncertainty': 'SOURCE_REPORTED_ONLY_NOT_REPRODUCED_ASSAY'},
               'input_assertion_ids': [], 'cache_request_key': None}
        packet['observations'].append(obs)
        q['observation_basis_bindings'].append({
            'observation_id': obs['observation_id'], 'occurrence_id': FOOD_RAW + ':occurrence',
            'source_kind': 'sr_legacy_food', 'source_version': RELEASE, 'metric_id': metric,
            'nutrient_definition_resource_id': rid, 'source_method': method,
            'native_derivation_id': row['derivation_id'],
            'native_nutrient_id': native_id, 'source_amount_lexeme': amount,
            'source_unit_name': source_unit, 'source_row_sha256': digest(row),
            'basis': copy.deepcopy(basis), 'source_basis_document_sha256': digest(['generated-document', 'per100g']),
            'numeric_context_status': 'held-IU-activity-semantics' if source_unit == 'IU' else 'qualified-source-reference',
            'evidence_sha256': digest({'observation': obs, 'native_row': row, 'definition': original})})
    bind_packet(packet, q)
    return packet, q


def projected_cases():
    """Finite reusable counterexamples, not assertions of unimplemented behavior."""
    cases = []
    def add(name, edit, expected):
        p, q = source_reference_fixture(); edit(p, q); bind_packet(p, q)
        cases.append({'id': name, 'packet': p, 'qualifications': q,
                      'future_required_disposition': expected,
                      'future_profile_behavior_verified': False, 'actual_gold_admitted': 0})
    add('source-contexts-with-IU-held', lambda p, q: None,
        'Own source identities may qualify independently; five source numeric contexts require exact review, IU remains held. No relationships or real data.')
    add('missing-own-identifier', lambda p, q: q['source_reference_identifier_bindings'].pop(0),
        'Raw food identity held; cooked food and vocabulary cannot seed the missing raw identity.')
    add('sibling-identifier-binding', lambda p, q: q['source_reference_identifier_bindings'][0].update(
        assertion_id=FOOD_COOKED + ':native-id', occurrence_id=FOOD_COOKED + ':occurrence'),
        'Cross-resource assertion/occurrence must not seed raw food.')
    add('wrong-release', lambda p, q: q['source_reference_identifier_bindings'][0].update(source_version='other-release'),
        'Mismatched source release held; no label-based identity fallback.')
    add('wrong-source-kind', lambda p, q: q['source_reference_identifier_bindings'][0].update(source_kind='nutrient'),
        'FoodPreparation cannot acquire a nutrient definition identity.')
    add('record-rights-unqualified', lambda p, q: q['records'][0].update(rights_state='unknown'),
        'Raw source record and its dependent observations held; independent siblings preserved.')
    def missing_english_support(p, q):
        q['supports'] = [s for s in q['supports'] if s['target_id'] != FOOD_RAW + ':editorial-concept']
    add('English-field-support-missing', missing_english_support,
        'An unsupported editorial English label cannot be covered by source-description support.')
    add('one-observation-basis-missing', lambda p, q: q['observation_basis_bindings'].pop(0),
        'Affected observation held; independently qualified literal identity/other observations remain separate.')
    add('branded-basis-shape-only', lambda p, q: q.__setitem__('observation_basis_bindings', [{
        'observation_id': b['observation_id'], 'basis': b['basis'], 'evidence_sha256': b['evidence_sha256']}
        for b in q['observation_basis_bindings']]),
        'Legacy branded basis shape alone cannot establish an SR-specific row/document/unit context.')
    def null_amount(p, q):
        a = next(a for a in p['common']['assertions'] if a['id'] == FOOD_RAW + ':amount-1004')
        a['value']['value'] = None
    add('null-is-not-zero', null_amount, 'Unknown numeric amount held; literal source lexeme remains original, never imputed as zero.')
    def wrong_unit(p, q):
        a = next(a for a in p['common']['assertions'] if a['id'] == FOOD_RAW + ':amount-1004')
        a['value']['unitId'] = 'mg'
    add('numerator-unit-conflict', wrong_unit, 'Unreviewed numerator alias/metric unit mismatch held; no implicit rescaling.')
    add('packet-cannot-select-profile', lambda p, q: p.__setitem__('admission_profile', 'source-reference-subset/1'),
        'A packet field cannot choose a trusted caller profile or elevate legacy admission.')
    return cases
