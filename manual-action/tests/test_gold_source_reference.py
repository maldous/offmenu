"""Actual trusted SR API tests; generated inputs and in-memory SQLite only."""
import copy
import importlib.util
import json
from pathlib import Path
import sqlite3
import unittest
from contextlib import closing

import jsonschema
from source_reference_fixture_cases import (
    FOOD_RAW, FOOD_COOKED, FOOD_TYPE, NUTRIENT_TYPE,
    bind_packet, projected_cases, source_reference_fixture,
)

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gold_source_reference_tests', ROOT / 'gold_builder.py')
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)


def build(p, q):
    bind_packet(p, q)
    return g.build_source_reference_subset(p, qualifications=q)


def entity_states(r):
    return {e['resource_id']: e['state'] for e in r['rows']['gold_entities']}


def obs_state(r, native_id):
    return next(o['state'] for o in r['rows']['gold_observations']
                if o['observation_id'] == FOOD_RAW + ':observation:' + native_id)


def claim(p, native_id='1004'):
    return next(a for a in p['common']['assertions'] if a['id'] == FOOD_RAW + ':amount-' + native_id)


def basis_binding(q, native_id='1004'):
    return next(b for b in q['observation_basis_bindings'] if b['native_nutrient_id'] == native_id)


def refresh_source_record(p, q, occurrence):
    """Refresh generated evidence so tests isolate semantics, not a stale hash."""
    occurrence['content_sha256'] = g.digest(occurrence['source_original'])
    next(r for r in q['records'] if r['occurrence_id'] == occurrence['occurrence_id'])['content_sha256'] = occurrence['content_sha256']
    rid = occurrence['resource_ids'][0]
    resource = next(r for r in p['common']['resources'] if r['id'] == rid)
    identity = next(a for a in p['common']['assertions'] if a['id'] == rid + ':native-id')
    next(b for b in q['source_reference_identifier_bindings'] if b['resource_id'] == rid)['evidence_sha256'] = g.digest(
        {'resource': resource, 'identity': identity, 'occurrence': occurrence})


class GoldSourceReferenceTests(unittest.TestCase):
    def test_trusted_profile_qualifies_own_identities_and_five_source_contexts_only(self):
        p, q = source_reference_fixture(); before = copy.deepcopy((p, q)); r = build(p, q)
        self.assertEqual(before, (p, q))
        self.assertEqual('source-reference-subset/1', r['admission_profile'])
        self.assertEqual('source-reference-subset/1', json.loads(r['rows']['gold_runs'][0]['watermark_json'])['admission_profile'])
        self.assertEqual(8, r['metrics']['connectivity']['source_reference_seeds'])
        self.assertEqual(0, r['metrics']['connectivity']['core_chain_seeds'])
        self.assertEqual({'verified'}, set(entity_states(r).values()))
        self.assertEqual(5, sum(o['state'] == 'verified' for o in r['rows']['gold_observations']))
        self.assertEqual('held', obs_state(r, '1104'))
        self.assertEqual([], r['rows']['gold_edges'])
        self.assertEqual(0, r['metrics']['actual_gold_admitted'])
        self.assertEqual('NOT_CHECKED', r['metrics']['recall_coverage'])
        self.assertEqual(r, build(p, q))

    def test_identity_and_vocabulary_do_not_require_numeric_admission(self):
        for mode in ['identity-only', 'no-basis', 'range-held']:
            p, q = source_reference_fixture(identity_only=mode == 'identity-only')
            if mode == 'no-basis': q['observation_basis_bindings'] = []
            if mode == 'range-held':
                for b in q['observation_basis_bindings']: b['numeric_context_status'] = 'held-source-range-context'
            r = build(p, q)
            self.assertEqual(8, sum(s == 'verified' for s in entity_states(r).values()))
            self.assertTrue(all(t['state'] == 'verified' for t in r['rows']['gold_texts']))
            self.assertFalse(any(o['state'] == 'verified' for o in r['rows']['gold_observations']))
            quantity_ids = {a['id'] for a in p['common']['assertions'] if a['value']['kind'] == 'quantity'}
            self.assertTrue(all(c['state'] == 'held' for c in r['rows']['gold_claims'] if c['assertion_id'] in quantity_ids))

    def test_prepared_identity_counterexamples_hold_raw_food_without_reviving_it(self):
        names = {'missing-own-identifier', 'sibling-identifier-binding', 'wrong-release', 'wrong-source-kind',
                 'record-rights-unqualified', 'English-field-support-missing'}
        for c in projected_cases():
            if c['id'] not in names: continue
            with self.subTest(case=c['id']):
                r = build(c['packet'], c['qualifications']); states = entity_states(r)
                self.assertEqual('held', states[FOOD_RAW]); self.assertEqual('verified', states[FOOD_COOKED])
                self.assertEqual(7, sum(s == 'verified' for s in states.values()))
                self.assertFalse(any(o['state'] == 'verified' for o in r['rows']['gold_observations']))

    def test_missing_nutrient_own_identity_holds_only_its_numeric_context(self):
        p, q = source_reference_fixture()
        q['source_reference_identifier_bindings'] = [b for b in q['source_reference_identifier_bindings']
                                                    if b['native_id'] != '1004']
        r = build(p, q)
        self.assertEqual('held', entity_states(r)['urn:fixture:sr:nutrient:1004'])
        self.assertEqual('verified', entity_states(r)[FOOD_RAW])
        self.assertEqual('held', obs_state(r, '1004')); self.assertEqual('verified', obs_state(r, '1093'))

    def test_selected_identifier_cannot_fall_back_to_a_different_supported_claim(self):
        p, q = source_reference_fixture()
        aid = FOOD_RAW + ':native-id'; a = next(a for a in p['common']['assertions'] if a['id'] == aid)
        other = copy.deepcopy(a); other['id'] += ':other'; p['common']['assertions'].append(other)
        support = copy.deepcopy(next(s for s in q['supports'] if s['target_kind'] == 'assertion' and s['target_id'] == aid))
        support['target_id'] = other['id']; q['supports'].append(support)
        a['sourcePath'] = '/sr_legacy_food/NDB_number'
        self.assertEqual('held', entity_states(build(p, q))[FOOD_RAW])

    def test_identity_checks_native_lexeme_scope_kind_release_and_original_hash(self):
        for mutation in ['ndb-trimmed', 'native-number', 'non-source-identity', 'shared-occurrence',
                         'source-key', 'source-original', 'duplicate-binding', 'bad-pin', 'extra-binding-field']:
            p, q = source_reference_fixture(); b = q['source_reference_identifier_bindings'][0]
            o = p['occurrences'][0]; a = next(a for a in p['common']['assertions'] if a['id'] == FOOD_RAW + ':ndb-number')
            if mutation == 'ndb-trimmed': a['value']['value'] = '101'
            elif mutation == 'native-number': b['native_id'] = 101
            elif mutation == 'non-source-identity': p['common']['resources'][0]['identityStatus'] = 'curated-concept'
            elif mutation == 'shared-occurrence': o['resource_ids'].append(FOOD_COOKED)
            elif mutation == 'source-key': o['source_key'] = 'usda-files:branded_food'
            elif mutation == 'source-original': o['source_original']['food']['description'] = 'tampered'
            elif mutation == 'duplicate-binding': q['source_reference_identifier_bindings'].append(copy.deepcopy(b))
            elif mutation == 'bad-pin': b['evidence_sha256'] = 'not-a-pin'
            else: b['profile_override'] = True
            with self.subTest(mutation=mutation): self.assertEqual('held', entity_states(build(p, q))[FOOD_RAW])

    def test_missing_basis_or_branded_shape_cannot_promote_numeric_claims(self):
        for name in ['one-observation-basis-missing', 'branded-basis-shape-only', 'null-is-not-zero', 'numerator-unit-conflict']:
            c = next(c for c in projected_cases() if c['id'] == name); r = build(c['packet'], c['qualifications'])
            with self.subTest(case=name):
                self.assertEqual('verified', entity_states(r)[FOOD_RAW]); self.assertEqual('held', obs_state(r, '1004'))
                self.assertEqual('held', next(c['state'] for c in r['rows']['gold_claims'] if c['assertion_id'] == FOOD_RAW + ':amount-1004'))
                if name != 'branded-basis-shape-only': self.assertEqual('verified', obs_state(r, '1093'))

    def test_numeric_source_path_must_select_the_native_amount_leaf(self):
        for leaf in ['does_not_exist', 'nutrient_id', 'data_points', 'amount/does_not_exist']:
            with self.subTest(leaf=leaf):
                p, q = source_reference_fixture()
                a = claim(p); a['sourcePath'] = '/food_nutrient/0/' + leaf
                next(s for s in q['supports'] if s['target_kind'] == 'assertion' and s['target_id'] == a['id'])['evidence_sha256'] = g.digest(a)
                # data_points and amount both contain literal "0": equality
                # alone must not allow the wrong source field.
                r = build(p, q)
                self.assertEqual('held', obs_state(r, '1004'))
                self.assertEqual('held', next(c['state'] for c in r['rows']['gold_claims'] if c['assertion_id'] == a['id']))
                self.assertEqual('verified', entity_states(r)[FOOD_RAW])
                self.assertEqual('verified', obs_state(r, '1093'))

    def test_supported_gtin_and_other_unregistered_properties_stay_held(self):
        for prop, kind in [('usda:gtin-upc', 'identifier'), ('schema:gtin13', 'identifier'),
                           ('usda:gtin-upc', 'expression'), ('unregistered:source-property', 'identifier')]:
            with self.subTest(property=prop, kind=kind):
                p, q = source_reference_fixture()
                occurrence = p['occurrences'][0]
                occurrence['source_original']['food']['gtin_upc'] = '00012345678905'
                refresh_source_record(p, q, occurrence)
                a = copy.deepcopy(next(a for a in p['common']['assertions'] if a['id'] == FOOD_RAW + ':native-id'))
                value = {'kind': kind, 'value': '00012345678905'}
                if kind == 'expression': value['syntax'] = 'literal-source-text'
                a.update(id=FOOD_RAW + ':excluded-property', propertyId=prop,
                         value=value, sourcePath='/food/gtin_upc')
                p['common']['assertions'].append(a)
                q['supports'].append({'target_kind': 'assertion', 'target_id': a['id'],
                    'citation_id': a['citationIds'][0], 'support_scope': 'field', 'evidence_sha256': g.digest(a)})
                r = build(p, q)
                c = next(c for c in r['rows']['gold_claims'] if c['assertion_id'] == a['id'])
                self.assertEqual('held', c['state'])
                self.assertEqual(a, json.loads(c['payload_json']))
                self.assertEqual({'verified'}, set(entity_states(r).values()))
                self.assertEqual(5, sum(o['state'] == 'verified' for o in r['rows']['gold_observations']))
                self.assertEqual([], r['rows']['gold_edges'])

    def test_sr_and_food_identity_rows_must_both_name_the_selected_food(self):
        for table in ['food', 'sr_legacy_food']:
            for value in ['101', None, 102]:
                with self.subTest(table=table, value=value):
                    p, q = source_reference_fixture()
                    occurrence = next(o for o in p['occurrences'] if o['resource_ids'] == [FOOD_COOKED])
                    occurrence['source_original'][table]['fdc_id'] = value
                    refresh_source_record(p, q, occurrence)
                    r = build(p, q)
                    self.assertEqual('held', entity_states(r)[FOOD_COOKED])
                    self.assertEqual('verified', entity_states(r)[FOOD_RAW])
                    self.assertEqual(7, sum(s == 'verified' for s in entity_states(r).values()))
                    self.assertEqual('verified', obs_state(r, '1004'))

    def test_identity_claims_must_use_their_native_semantic_fields(self):
        for suffix, alias in [('native-id', 'fdc_alias'), ('ndb-number', 'ndb_alias'), ('data-type', 'type_alias')]:
            with self.subTest(claim=suffix):
                p, q = source_reference_fixture()
                a = next(a for a in p['common']['assertions'] if a['id'] == FOOD_RAW + ':' + suffix)
                occurrence = p['occurrences'][0]
                occurrence['source_original'][alias] = a['value']['value']
                a['sourcePath'] = '/' + alias
                refresh_source_record(p, q, occurrence)
                r = build(p, q)
                self.assertEqual('held', entity_states(r)[FOOD_RAW])
                self.assertEqual('verified', entity_states(r)[FOOD_COOKED])

    def test_each_row_definition_document_metric_method_and_lexeme_must_match(self):
        edits = {
            'row-hash': lambda p, b: b.update(source_row_sha256='0' * 64),
            'document': lambda p, b: b.pop('source_basis_document_sha256'),
            'definition': lambda p, b: b.update(nutrient_definition_resource_id='urn:fixture:sr:nutrient:1093'),
            'nutrient': lambda p, b: b.update(native_nutrient_id='1093'),
            'metric': lambda p, b: b.update(metric_id='legacy-protein'),
            'occurrence': lambda p, b: b.update(occurrence_id=FOOD_COOKED + ':occurrence'),
            'release': lambda p, b: b.update(source_version='other-release'),
            'method': lambda p, b: b.update(source_method='independently-reproduced-assay'),
            'derivation': lambda p, b: b.pop('native_derivation_id'),
            'lexeme': lambda p, b: b.update(source_amount_lexeme='999'),
            'numeric': lambda p, b: claim(p)['value'].update(value=999),
            'source-fields': lambda p, b: p['observations'][0]['context']['source_fields'].update(data_points='999'),
            'basis': lambda p, b: b['basis'].update(value=50),
            'boolean': lambda p, b: claim(p)['value'].update(value=True),
            'unit-object': lambda p, b: b.update(source_unit_name=[]),
            'definition-object': lambda p, b: b.update(nutrient_definition_resource_id=[]),
            'pointer-object': lambda p, b: claim(p).update(sourcePath=None),
        }
        for name, edit in edits.items():
            p, q = source_reference_fixture(); edit(p, basis_binding(q)); r = build(p, q)
            with self.subTest(mutation=name):
                self.assertEqual('held', obs_state(r, '1004'))
                self.assertEqual('verified', obs_state(r, '1093'))
                self.assertEqual('verified', entity_states(r)[FOOD_RAW])

    def test_qualified_zero_and_original_unknowns_stay_source_reports(self):
        p, q = source_reference_fixture(); r = build(p, q)
        self.assertEqual('verified', obs_state(r, '1004'))
        o = next(o for o in r['rows']['gold_observations'] if o['observation_id'].endswith(':1004'))
        context = json.loads(o['context_json']); original = json.loads(o['original_json'])
        self.assertEqual((0, '0'), (original['value'], original['sourceValue']))
        self.assertEqual('SOURCE_ASSUMED_ZERO', context['method'])
        self.assertEqual('0', context['source_fields']['data_points']); self.assertEqual('', context['source_fields']['LOQ'])
        self.assertIsNone(context['country']); self.assertIsNone(context['assay_date'])
        self.assertFalse(context['independent_assay_verified']); self.assertFalse(context['recipe_transfer_qualified'])
        self.assertTrue(context['source_reporting_only'])
        self.assertEqual('verified', obs_state(r, '1106'))  # Explicit missing derivation is not an invented assay.

    def test_physical_truth_transfer_and_origin_claims_do_not_qualify(self):
        for field, value in [('independent_assay_verified', True), ('recipe_transfer_qualified', True),
                             ('source_reporting_only', False), ('country', 'US'), ('assay_date', '2026-01-01')]:
            p, q = source_reference_fixture(); p['observations'][0]['context'][field] = value
            with self.subTest(field=field): self.assertEqual('held', obs_state(build(p, q), '1004'))

    def test_IU_cannot_be_relabelled_as_mass_or_qualified_by_status_alone(self):
        p, q = source_reference_fixture(); b = basis_binding(q, '1104')
        b['numeric_context_status'] = 'qualified-source-reference'
        a = claim(p, '1104'); a['value'].update(unitId='µg', dimension='mass')
        m = next(m for m in p['metrics'] if m['metric_id'] == b['metric_id']); m.update(canonical_unit_id='µg', dimension='mass')
        self.assertEqual('held', obs_state(build(p, q), '1104'))

    def test_definition_unit_source_field_cannot_be_replaced_by_a_label(self):
        p, q = source_reference_fixture()
        a = next(a for a in p['common']['assertions'] if a['id'] == 'urn:fixture:sr:nutrient:1004:native-unit')
        a['sourcePath'] = '/nutrient/name'
        self.assertEqual('held', obs_state(build(p, q), '1004'))

    def test_source_ids_do_not_collapse_into_legacy_metrics(self):
        p, q = source_reference_fixture(); old = 'urn:fixture:sr:nutrient:1004'
        next(m for m in p['metrics'] if m['metric_id'] == old)['metric_id'] = 'protein'
        p['observations'][0]['metric_id'] = 'protein'; claim(p)['propertyId'] = 'protein'
        basis_binding(q)['metric_id'] = 'protein'
        self.assertEqual('held', obs_state(build(p, q), '1004'))

    def test_duplicate_observations_or_unbound_typed_numbers_stay_held(self):
        p, q = source_reference_fixture(); extra = copy.deepcopy(p['observations'][0]); extra['observation_id'] += ':copy'
        p['observations'].append(extra); b = copy.deepcopy(basis_binding(q)); b['observation_id'] = extra['observation_id']; q['observation_basis_bindings'].append(b)
        r = build(p, q)
        self.assertTrue(all(o['state'] == 'held' for o in r['rows']['gold_observations'] if o['claim_id'] == next(c['claim_id'] for c in r['rows']['gold_claims'] if c['assertion_id'] == claim(p)['id'])))
        for value in [{'kind': 'number', 'value': 42}, {'kind': 'structure', 'fields': {'unqualified': {'kind': 'number', 'value': 42}}}]:
            p, q = source_reference_fixture(); a = copy.deepcopy(claim(p)); a.update(id=FOOD_RAW + ':unbound-number', value=value)
            p['common']['assertions'].append(a); s = copy.deepcopy(next(s for s in q['supports'] if s['target_kind'] == 'assertion' and s['target_id'] == claim(p)['id'])); s['target_id'] = a['id']; q['supports'].append(s)
            r = build(p, q); self.assertEqual('held', next(c['state'] for c in r['rows']['gold_claims'] if c['assertion_id'] == a['id']))

    def test_relations_comparisons_conversions_private_and_foreign_types_reject(self):
        for mutation in ['relation', 'comparison', 'conversion', 'domain', 'retail', 'ingredient', 'recipe', 'private', 'scope-missing']:
            p, q = source_reference_fixture()
            if mutation == 'relation': p['common']['relations'] = [{'predicateId': 'canonical_ingredient'}]
            elif mutation == 'comparison': q['comparisons'] = [{'disposition': 'contradiction'}]
            elif mutation == 'conversion': p['observations'][0]['comparable'] = {'value': 0}
            elif mutation == 'domain': p['watermark']['domains'][0]['domain'] = 'barcodes'
            elif mutation in {'retail', 'ingredient', 'recipe'}: p['common']['resources'][0]['type'] = {'retail': 'barcode-product', 'ingredient': 'ingredient', 'recipe': 'recipe'}[mutation]
            elif mutation == 'private': p['common']['resources'][0]['scope'] = {'visibility': 'private', 'ownerId': 'fixture'}
            else: p['common']['citations'][0]['scope'].pop('reuseScope')
            bind_packet(p, q)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): g.build_source_reference_subset(p, qualifications=q)

    def test_trusted_profile_never_changes_default_or_retail_admission(self):
        p, q = source_reference_fixture(); p['admission_profile'] = 'source-reference-subset/1'; bind_packet(p, q)
        default = g.build_gold_slice(p, qualifications=q); source = g.build_source_reference_subset(p, qualifications=q)
        self.assertTrue(all(s == 'held' for s in entity_states(default).values()))
        self.assertNotIn('admission_profile', default); self.assertNotEqual(default['slice_id'], source['slice_id'])
        with self.assertRaises(ValueError): g.build_product_source_subset(p, qualifications=q)

    def test_exact_originals_and_full_type_IRIs_roundtrip_generated_memory_DDL(self):
        p, q = source_reference_fixture(); r = build(p, q)
        with closing(sqlite3.connect(':memory:')) as db:
            db.executescript((ROOT / 'gold.schema.sql').read_text())
            for table in g.INSERT_ORDER:
                cols = g.TABLE_COLUMNS[table]
                for row in r['rows'][table]: db.execute('INSERT INTO ' + table + ' (' + ','.join(cols) + ') VALUES (' + ','.join('?' for _ in cols) + ')', [row[c] for c in cols])
            self.assertEqual([], db.execute('PRAGMA foreign_key_check').fetchall()); self.assertEqual('ok', db.execute('PRAGMA integrity_check').fetchone()[0])
            self.assertEqual(0, db.execute("SELECT COUNT(*) FROM gold_entities WHERE entity_type IN ('ingredient','barcode-product')").fetchone()[0])
            originals = {oid: json.loads(payload)['source_original'] for oid, payload in db.execute('SELECT occurrence_id,payload_json FROM gold_occurrences')}
            self.assertEqual({o['occurrence_id']: o['source_original'] for o in p['occurrences']}, originals)

    def test_application_binding_schema_accepts_exact_source_and_legacy_shapes_only(self):
        app = json.loads((ROOT / 'gold-application.schema.json').read_text()); common = json.loads((ROOT.parent / 'corpus/common-data.schema.json').read_text())
        props = app['properties']['qualifications']['properties']; p, q = source_reference_fixture()
        for key in ['source_reference_identifier_bindings', 'observation_basis_bindings']:
            schema = copy.deepcopy(props[key]); schema['$defs'] = common['$defs']
            if key == 'observation_basis_bindings': schema['items']['properties']['basis'] = {'$ref': '#/$defs/quantity'}
            validator = jsonschema.Draft202012Validator(schema); validator.validate(q[key])
            bad = copy.deepcopy(q[key]); bad[0]['unknown'] = True
            with self.assertRaises(jsonschema.ValidationError): validator.validate(bad)
            if key == 'observation_basis_bindings':
                validator.validate([{k: q[key][0][k] for k in ['observation_id', 'basis', 'evidence_sha256']}])
                bad = copy.deepcopy(q[key]); bad[0].pop('source_basis_document_sha256')
                with self.assertRaises(jsonschema.ValidationError): validator.validate(bad)

    def test_bounds_nonfinite_and_invalid_source_pointer_fail_closed(self):
        p, q = source_reference_fixture(); p['padding'] = 'x' * 4194304
        with self.assertRaisesRegex(ValueError, '4 MiB'): g.build_source_reference_subset(p, qualifications=q)
        for value in [float('nan'), float('inf'), float('-inf')]:
            p, q = source_reference_fixture(); claim(p)['value']['value'] = value
            with self.assertRaises(ValueError): g.build_source_reference_subset(p, qualifications=q)
        self.assertIsNone(g._source_pointer({'rows': ['a']}, '/rows/-1'))
        self.assertIsNone(g._source_pointer({'rows': ['a']}, '/rows/00'))
        self.assertEqual('value', g._source_pointer({'a/b': {'~': 'value'}}, '/a~1b/~0'))

    def test_source_exponent_does_not_expand_into_an_unbounded_integer(self):
        p, q = source_reference_fixture(); o = p['occurrences'][0]
        row = o['source_original']['food_nutrient'][0]; row['amount'] = '1e1000000000'
        o['content_sha256'] = g.digest(o['source_original']); q['records'][0]['content_sha256'] = o['content_sha256']
        p['observations'][0]['context']['source_fields'] = copy.deepcopy(row)
        claim(p)['value']['sourceValue'] = row['amount']
        b = basis_binding(q); b.update(source_amount_lexeme=row['amount'], source_row_sha256=g.digest(row))
        r = build(p, q)
        self.assertEqual('verified', entity_states(r)[FOOD_RAW])
        self.assertEqual('held', obs_state(r, '1004')); self.assertEqual('verified', obs_state(r, '1093'))


if __name__ == '__main__': unittest.main()
