"""Executable preparation and legacy-profile checks, not real SR admission."""
import copy
import importlib.util
import json
from pathlib import Path
import sqlite3
import unittest

import jsonschema
from source_reference_fixture_cases import (
    FOOD_TYPE, NUTRIENT_TYPE, FOOD_RAW, FOOD_COOKED, RELEASE,
    bind_packet, projected_cases, source_reference_fixture,
)

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('source_reference_preparation_gold', ROOT / 'gold_builder.py')
gold = importlib.util.module_from_spec(spec); spec.loader.exec_module(gold)
COMMON = json.loads((ROOT.parent.parent / 'corpus/common-data.schema.json').read_text())


class SourceReferenceFixtureContractTests(unittest.TestCase):
    def test_all_prepared_packets_are_generated_bounded_and_Common_valid(self):
        cases = projected_cases()
        self.assertEqual(12, len(cases))
        self.assertEqual(12, len({c['id'] for c in cases}))
        for c in cases:
            with self.subTest(case=c['id']):
                p, q = c['packet'], c['qualifications']
                self.assertEqual('synthetic', p['data_class'])
                jsonschema.Draft202012Validator(COMMON).validate(p['common'])
                self.assertEqual(gold.digest(p), q['packet_sha256'])
                for item in [p, q]:
                    gold._bound(item)
                    self.assertLess(len(gold._json(item).encode()), 4194304)
                self.assertFalse(c['future_profile_behavior_verified'])
                self.assertEqual(0, c['actual_gold_admitted'])

    def test_native_identity_and_full_type_IRIs_have_own_occurrences(self):
        p, q = source_reference_fixture()
        resources = {r['id']: r for r in p['common']['resources']}
        assertions = {a['id']: a for a in p['common']['assertions']}
        occurrences = {o['occurrence_id']: o for o in p['occurrences']}
        self.assertEqual(8, len(resources))
        self.assertEqual({FOOD_TYPE, NUTRIENT_TYPE}, {r['type'] for r in resources.values()})
        for b in q['source_reference_identifier_bindings']:
            a, o = assertions[b['assertion_id']], occurrences[b['occurrence_id']]
            self.assertEqual(b['resource_id'], a['subjectId'])
            self.assertEqual([b['resource_id']], o['resource_ids'])
            self.assertEqual(b['native_id'], a['value']['value'])
            self.assertEqual(b['native_id'], o['record_id'])
            self.assertEqual(RELEASE, b['source_version'])
            self.assertEqual(o['source_version'], b['source_version'])
            self.assertEqual(gold.digest(o['source_original']), o['content_sha256'])
        ndb = [a['value']['value'] for a in assertions.values() if a['propertyId'] == 'usda:ndb-number']
        self.assertEqual(['00101', '00102'], ndb)

    def test_same_editorial_noun_does_not_erase_raw_cooked_source_qualifiers(self):
        p, _ = source_reference_fixture()
        raw, cooked = [next(r for r in p['common']['resources'] if r['id'] == rid) for rid in [FOOD_RAW, FOOD_COOKED]]
        self.assertEqual('Carrot', raw['names'][1]['value'])
        self.assertEqual('Carrot', cooked['names'][1]['value'])
        self.assertNotEqual(raw['id'], cooked['id'])
        self.assertIn(', raw', raw['names'][0]['value'])
        self.assertIn(', cooked, boiled, drained, without salt', cooked['names'][0]['value'])
        self.assertFalse(p['common']['relations'])
        self.assertFalse(any(a['propertyId'] in {'usda:gtin-upc', 'canonical_ingredient'} for a in p['common']['assertions']))

    def test_literal_zero_missing_methods_dates_and_original_lexemes_survive(self):
        p, _ = source_reference_fixture()
        amounts = {a['id'].rsplit('-', 1)[-1]: a['value'] for a in p['common']['assertions'] if ':amount-' in a['id']}
        self.assertEqual(0, amounts['1004']['value'])
        self.assertEqual('0', amounts['1004']['sourceValue'])
        self.assertEqual('2.50', amounts['1093']['sourceValue'])
        self.assertEqual('0.020', amounts['1106']['sourceValue'])
        by_nutrient = {o['context']['source_fields']['nutrient_id']: o for o in p['observations']}
        self.assertEqual('SOURCE_ASSUMED_ZERO', by_nutrient['1004']['context']['method'])
        self.assertEqual('DERIVATION_NOT_SUPPLIED', by_nutrient['1106']['context']['method'])
        for o in p['observations']:
            context = o['context']
            self.assertIsNone(context['country']); self.assertIsNone(context['assay_date'])
            self.assertIsNone(context['source_date'])
            self.assertEqual('0', context['source_fields']['data_points'])
            self.assertEqual('', context['source_fields']['LOQ'])
            self.assertNotEqual(context['source_origin_vintage'], context['source_archive_release'])
        originals = [o['source_original'] for o in p['occurrences'] if o['source_key'].endswith(':sr_legacy_food')]
        self.assertTrue(all(o['source_country'] is None and o['source_language'] is None for o in originals))

    def test_Sr_basis_row_document_and_native_units_are_separate_from_branded_basis(self):
        p, q = source_reference_fixture()
        rows = next(o['source_original']['food_nutrient'] for o in p['occurrences'] if o['resource_ids'] == [FOOD_RAW])
        self.assertEqual({'G', 'MG', 'UG', 'KCAL', 'kJ', 'IU'}, {b['source_unit_name'] for b in q['observation_basis_bindings']})
        for b in q['observation_basis_bindings']:
            self.assertEqual('sr_legacy_food', b['source_kind'])
            self.assertEqual(FOOD_RAW + ':occurrence', b['occurrence_id'])
            self.assertEqual(RELEASE, b['source_version'])
            row = next(r for r in rows if r['nutrient_id'] == b['native_nutrient_id'])
            self.assertEqual(gold.digest(row), b['source_row_sha256'])
            self.assertEqual(row['amount'], b['source_amount_lexeme'])
            self.assertTrue(gold._pin(b['source_basis_document_sha256']))
            self.assertEqual((100, 'g', 'mass'), (b['basis']['value'], b['basis']['unitId'], b['basis']['dimension']))
        iu = next(b for b in q['observation_basis_bindings'] if b['source_unit_name'] == 'IU')
        self.assertEqual('held-IU-activity-semantics', iu['numeric_context_status'])
        metric = next(m for m in p['metrics'] if m['metric_id'] == iu['metric_id'])
        self.assertEqual('unknown', metric['dimension'])
        self.assertEqual('usda:IU', metric['canonical_unit_id'])

    def test_legacy_default_never_uses_prototype_bindings_as_admission_seeds(self):
        for identity_only in [False, True]:
            p, q = source_reference_fixture(identity_only=identity_only)
            before = copy.deepcopy((p, q)); r = gold.build_gold_slice(p, qualifications=q)
            self.assertEqual(before, (p, q))
            self.assertTrue(r['rows']['gold_entities'])
            self.assertTrue(all(e['state'] == 'held' for e in r['rows']['gold_entities']))
            self.assertTrue(all(o['state'] == 'held' for o in r['rows']['gold_observations']))
            self.assertEqual(0, r['metrics']['actual_gold_admitted'])
            self.assertEqual(0, r['metrics']['connectivity']['core_chain_seeds'])
            self.assertEqual([], r['rows']['gold_edges'])

    def test_packet_profile_spoof_cannot_activate_a_trusted_source_profile(self):
        c = next(c for c in projected_cases() if c['id'] == 'packet-cannot-select-profile')
        r = gold.build_gold_slice(c['packet'], qualifications=c['qualifications'])
        self.assertNotIn('admission_profile', r)
        self.assertNotIn('admission_profile', json.loads(r['rows']['gold_runs'][0]['watermark_json']))
        self.assertTrue(all(e['state'] == 'held' for e in r['rows']['gold_entities']))

    def test_existing_retail_and_recipe_source_apis_reject_reference_resources(self):
        p, q = source_reference_fixture(identity_only=True)
        for api in [gold.build_product_source_subset, gold.build_recipe_source_subset]:
            with self.subTest(api=api.__name__), self.assertRaises(ValueError):
                api(p, qualifications=q)

    def test_held_observation_lookup_preserves_originals_without_preference_or_averaging(self):
        p, q = source_reference_fixture(); r = gold.build_gold_slice(p, qualifications=q)
        result = gold.select_observations(r, metric_id='urn:fixture:sr:nutrient:1004')
        self.assertEqual([], result['preferred_ids']); self.assertEqual('none', result['aggregation'])
        self.assertEqual(1, len(result['alternatives']))
        row = result['alternatives'][0]['observation']
        self.assertEqual('held', row['state'])
        self.assertEqual('0', json.loads(row['original_json'])['sourceValue'])
        self.assertEqual('SOURCE_ASSUMED_ZERO', json.loads(row['context_json'])['method'])

    def test_existing_DDL_roundtrips_full_type_IRIs_and_originals_in_memory_only(self):
        p, q = source_reference_fixture(); r = gold.build_gold_slice(p, qualifications=q)
        with sqlite3.connect(':memory:') as db:
            db.executescript((ROOT / 'gold.schema.sql').read_text())
            for table in gold.INSERT_ORDER:
                cols = gold.TABLE_COLUMNS[table]
                for row in r['rows'][table]:
                    db.execute('INSERT INTO ' + table + ' (' + ','.join(cols) + ') VALUES (' + ','.join('?' for _ in cols) + ')', [row[c] for c in cols])
            self.assertEqual([], db.execute('PRAGMA foreign_key_check').fetchall())
            self.assertEqual('ok', db.execute('PRAGMA integrity_check').fetchone()[0])
            self.assertEqual(8, db.execute('SELECT COUNT(*) FROM gold_entities').fetchone()[0])
            self.assertEqual(0, db.execute("SELECT COUNT(*) FROM gold_entities WHERE entity_type IN ('ingredient','barcode-product')").fetchone()[0])
            self.assertEqual(8, db.execute("SELECT COUNT(*) FROM gold_entities WHERE state='held'").fetchone()[0])
            actual = {oid: json.loads(payload)['source_original'] for oid, payload in db.execute('SELECT occurrence_id,payload_json FROM gold_occurrences')}
            self.assertEqual({o['occurrence_id']: o['source_original'] for o in p['occurrences']}, actual)

    def test_fixture_construction_and_case_export_are_deterministic_and_detached(self):
        self.assertEqual(projected_cases(), projected_cases())
        p, q = source_reference_fixture(); p2, q2 = source_reference_fixture()
        p['common']['resources'][0]['names'][0]['value'] = 'changed'
        q['source_reference_identifier_bindings'].clear()
        self.assertNotEqual(p, p2); self.assertEqual(8, len(q2['source_reference_identifier_bindings']))
        for c in projected_cases():
            self.assertEqual(0, c['actual_gold_admitted'])
            self.assertFalse(c['future_profile_behavior_verified'])

    def test_boolean_quantity_and_nonfinite_numbers_are_not_valid_numeric_evidence(self):
        p, q = source_reference_fixture()
        claim = next(a for a in p['common']['assertions'] if a['id'] == FOOD_RAW + ':amount-1004')
        claim['value']['value'] = True
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(COMMON).validate(p['common'])
        for value in [float('inf'), float('-inf'), float('nan')]:
            claim['value']['value'] = value
            with self.assertRaises(ValueError):
                bind_packet(p, q)


if __name__ == '__main__':
    unittest.main()
