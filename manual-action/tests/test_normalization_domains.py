"""Generated synthetic cases only; no real corpus or household input."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from normalization_domains import (RULE_IDS, RULE_VERSION, exact_identifier_links,
    normalize_gtin, normalize_nutrient, normalize_payload, normalize_quantity, normalize_url,
    translation_text_paths)


class Quantities(unittest.TestCase):
    def test_exact_units_and_precision(self):
        for value, unit, expected, canonical in [('1.250', 'kg', '1250', 'g'),
                ('.001', 'g', '0.001', 'g'), ('125', 'µg', '0.000125', 'g'),
                ('1.5', 'L', '1500', 'mL'), ('2', 'cm³', '2', 'mL'),
                ('1.25', 'hours', '4500', 's'), ('2', 'kJ', '2000', 'J')]:
            with self.subTest(value=value, unit=unit):
                result = normalize_quantity(value, unit)
                self.assertEqual((result['value'], result['unit']), (expected, canonical))
                self.assertEqual(result['original'], {'value': value, 'unit': unit})
                self.assertEqual(result['issues'], [])
                self.assertTrue(result['exact'])

    def test_ranges(self):
        for value in ('1.20–2.5', '1.20 to 2.5', {'min': '1.20', 'max': '2.5'}):
            result = normalize_quantity(value, 'kg')
            self.assertEqual((result['min'], result['max']), ('1200', '2500'))
        self.assertEqual(normalize_quantity('3–2', 'g')['status'], 'unresolved')
        self.assertEqual(normalize_quantity('-5--2', '°C')['min'], '-5')

    def test_temperature_exact_not_rounded(self):
        self.assertEqual(normalize_quantity('273.15', 'K')['value'], '0')
        self.assertEqual(normalize_quantity('212', '°F')['value'], '100')
        value = normalize_quantity('350', '°F')
        self.assertEqual((value['value'], value['number_type']), ('530/3', 'rational'))
        self.assertEqual(normalize_quantity('18', '°F', temperature_kind='interval')['value'], '10')
        self.assertEqual(normalize_quantity('1', 'K', temperature_kind='interval')['value'], '1')
        self.assertEqual(normalize_quantity('-1', 'K')['status'], 'unresolved')

    def test_density_is_explicit_and_requested(self):
        self.assertEqual(normalize_quantity('2', 'g', target_unit='mL')['status'], 'unresolved')
        value = normalize_quantity('2', 'g', density_g_per_ml='3', target_unit='mL')
        self.assertEqual((value['value'], value['number_type']), ('2/3', 'rational'))
        self.assertEqual(normalize_quantity('20', 'mL', density_g_per_ml='0.5', target_unit='g')['value'], '10')
        self.assertEqual(normalize_quantity('20', 'mL', density_g_per_ml='0.5')['unit'], 'mL')
        self.assertEqual(normalize_quantity('20', 'mL', density_g_per_ml='0', target_unit='g')['status'], 'unresolved')

    def test_uncertain_numbers_and_locale_units_remain_unresolved(self):
        for value, unit in [('1,000', 'g'), ('1,5', 'g'), ('about 2', 'g'), ('NaN', 'g'),
                            (True, 'g'), (0.1, 'g'), ('-1', 'g'), ('1', 'ML'), ('1e99999', 'g'),
                            ('1', 'cup'), ('1', 'tbsp'), ('1', 'tsp'), ('1', 'oz'), ('1', 'kcal')]:
            with self.subTest(value=value, unit=unit):
                result = normalize_quantity(value, unit, locale='en-US')
                self.assertEqual(result['status'], 'unresolved')
                self.assertNotIn('value', result)
                self.assertTrue(result['issues'])

    def test_no_input_mutation(self):
        value = {'min': '1', 'max': '2', 'unit': 'g'}
        before = copy.deepcopy(value)
        normalize_quantity(value)
        self.assertEqual(value, before)


class Identifiers(unittest.TestCase):
    def test_known_gs1_example_and_padding(self):
        value = normalize_gtin('6291041500213', 'synthetic-provider')
        self.assertEqual(value['gtin14'], '06291041500213')
        self.assertEqual(value['source_namespace'], 'synthetic-provider')
        self.assertEqual(value['status'], 'syntax_valid_not_registry_verified')
        self.assertEqual(normalize_gtin('00012345600012')['gtin14'], '00012345600012')

    def test_all_supported_lengths(self):
        for code in ('96385074', '012345678905', '6291041500213', '00012345600012'):
            with self.subTest(code=code):
                self.assertTrue(normalize_gtin(code)['aliases'])

    def test_invalid_syntax_never_gets_alias(self):
        for code in ('6291041500214', '1234567', '000000000000000', ' 6291041500213',
                     '６２９１０４１５００２１３', 6291041500213, '0123-4567'):
            result = normalize_gtin(code)
            self.assertEqual(result['aliases'], [])
            self.assertNotIn('gtin14', result)
            self.assertEqual(result['original'], code)

    def test_different_valid_codes_are_conflict(self):
        result = normalize_payload({'code': '012345678905', 'gtin': '6291041500213'}, 'barcode')
        self.assertIn('barcode_identifier_conflict', [i['code'] for i in result['issues']])

    def test_authoritative_exact_link_only_no_names_or_namespace_collision(self):
        a = {'namespace': 'registry-a', 'value': '001', 'authoritative': True}
        self.assertEqual(len(exact_identifier_links([a], [a])), 1)
        for b in ({**a, 'namespace': 'registry-b'}, {**a, 'value': '1'},
                  {**a, 'authoritative': False}, {'name': 'same name'}):
            self.assertEqual(exact_identifier_links([a], [b]), [])
        self.assertEqual(exact_identifier_links([a], [a])[0]['status'], 'link_candidate_not_merge')

    def test_private_link_scope_must_agree(self):
        a = {'namespace': 'private', 'value': '001', 'authoritative': True, 'household_scope': 'synthetic-a'}
        self.assertEqual(exact_identifier_links([a], [{**a, 'household_scope': 'synthetic-b'}]), [])
        self.assertEqual(exact_identifier_links([a], [{k: v for k, v in a.items() if k != 'household_scope'}]), [])
        self.assertEqual(len(exact_identifier_links([a], [a])), 1)
        self.assertEqual(exact_identifier_links([{**a, 'user_scope': 'generated-user-a'}],
                                                [{**a, 'user_scope': 'generated-user-b'}]), [])
        self.assertEqual(exact_identifier_links([{**a, 'user_scope': 'generated-user-a'}], [a]), [])
        self.assertEqual(exact_identifier_links([{**a, 'household_scope': ''}], [{**a, 'household_scope': ''}]), [])
        self.assertEqual(exact_identifier_links([{**a, 'user_scope': ''}], [{**a, 'user_scope': ''}]), [])


class Domains(unittest.TestCase):
    def test_translation_paths_are_lexical_not_identifiers_or_symbols(self):
        result = normalize_payload({'provider': 'synthetic', 'code': '6291041500213',
                                    'product_name': 'Synthetic food'}, 'barcode')
        self.assertEqual(translation_text_paths(result['normalized']), ['/fields/product_name', '/title'])
        result = normalize_payload({'name': 'cilantro', 'aliases': [{'text': 'coriander leaf', 'id': 'synthetic-id'}],
            'quantity': '1', 'unit': 'g', 'source_native_id': 'source-id'}, 'ingredient')
        paths = translation_text_paths(result['normalized'])
        self.assertIn('/fields/aliases_original/0/text', paths)
        self.assertFalse(any('/id' in p or '/unit' in p or '/quantity' in p or '/identity' in p for p in paths))
        result = normalize_payload({'url': 'https://example.org/a#part', 'title': 'Synthetic reference',
                                    'license': 'CC0-1.0', 'evidence_fragment': 'Synthetic words'}, 'citation')
        paths = translation_text_paths(result['normalized'])
        self.assertIn('/fields/evidence_fragment', paths)
        self.assertFalse(any('/url' in p or '/license' in p for p in paths))

    def test_registry_and_generated_fixture_versions(self):
        registry = json.loads((ROOT / 'normalization-rules.json').read_text())
        fixture = json.loads((ROOT / 'tests/fixtures/normalization_domains.synthetic.json').read_text())
        self.assertEqual(registry['rule_version'], RULE_VERSION)
        self.assertEqual(fixture['rule_version'], RULE_VERSION)
        self.assertEqual(set(RULE_IDS), {rule['id'] for rule in registry['rules']})
        self.assertFalse(registry['automatic_gold_eligibility'])
        for case in fixture['cases']:
            with self.subTest(domain=case['record_type']):
                payload = copy.deepcopy(case['payload'])
                result = normalize_payload(payload, case['record_type'])
                self.assertEqual(payload, case['payload'])
                self.assertEqual(result, normalize_payload(payload, case['record_type']))
                self.assertTrue(result['required_review'])
                self.assertEqual(set(result['normalized']), {'title', 'language', 'fields', 'relations', 'field_lineage'})
                self.assertNotIn('gold_eligible', result)
                json.dumps(result, allow_nan=False)
                for entry in result['normalized']['field_lineage']:
                    self.assertEqual(entry['rule_version'], RULE_VERSION)
                    self.assertIn(entry['rule_id'], RULE_IDS)
                    for pointer in entry['source_paths']:
                        cursor = payload
                        if pointer:
                            for token in pointer[1:].split('/'):
                                token = token.replace('~1', '/').replace('~0', '~')
                                cursor = cursor[int(token)] if isinstance(cursor, list) else cursor[token]

    def test_ingredient_aliases_and_parts_not_collapsed(self):
        results = [normalize_payload({'name': name, 'language': 'en', 'aliases': ['coriander'], 'preparation': part}, 'ingredient')
                   for name, part in [('cilantro', 'leaf'), ('coriander', 'seed')]]
        for result in results:
            fields = result['normalized']['fields']
            self.assertEqual(fields['name_match_status'], 'unresolved_no_lexical_equivalence')
            self.assertNotIn('canonical_ingredient_id', fields)
            self.assertEqual(fields['aliases_original'], ['coriander'])
        self.assertNotEqual(results[0]['normalized']['fields'], results[1]['normalized']['fields'])

    def test_native_ingredient_wrapper_preserves_raw_language_and_preparation(self):
        result = normalize_payload({'kind': 'ingredient_source_entity', 'name': 'coriandre',
            'raw_source': {'language': 'fr', 'preparation': 'graines', 'aliases': ['synthetic alias']}}, 'ingredient')
        self.assertEqual(result['normalized']['language'], 'fr')
        self.assertEqual(result['normalized']['fields']['preparation_original'], 'graines')

    def test_nutrient_bases_never_unified_or_derived(self):
        for basis in ('per_100g', 'per_100mL', 'per_serving'):
            result = normalize_nutrient({'name': 'sodium', 'amount': '12', 'unit': 'mg', 'basis': basis})
            self.assertEqual(result['basis'], basis)
            self.assertEqual(result['quantity']['value'], '0.012')
            self.assertNotIn('salt', result)
            self.assertNotIn('serving_weight', result)
            self.assertNotIn('energy', result)
        result = normalize_nutrient({'name': 'protein', 'amount': '2', 'unit': 'g'})
        self.assertIsNone(result['basis'])
        self.assertIn('nutrient_basis_unresolved', [item['code'] for item in result['issues']])

    def test_native_dietary_lexical_decimal_survives_float_serialization(self):
        payload = {'record_type': 'nutrition_reference', 'source_fields': {'data': {'name': 'Synthetic',
            'basis': 'per_100g', 'nutrients': [{'name': 'protein', 'amount': 0.12345678901234568, 'unit': 'g'}]}},
            'source_numeric_lexemes': {'/data/nutrients/0/amount': '0.123456789012345678901'}}
        result = normalize_payload(payload, 'dietary_assertion')
        nutrient = result['normalized']['fields']['nutrient_observations'][0]
        self.assertEqual(nutrient['quantity']['value'], '0.123456789012345678901')
        self.assertEqual(nutrient['source_assertion'], payload['source_fields']['data']['nutrients'][0])

    def test_native_single_nutrient_and_conflicting_lexeme(self):
        payload = {'record_type': 'usda_nutrient_observation', 'source_fields': {
            'nutrient_id': 'synthetic', 'amount': 0.125, 'unit': 'g', 'basis': 'per_100g'},
            'source_numeric_lexemes': {'/amount': '0.1250'}}
        result = normalize_payload(payload, 'dietary_assertion')
        self.assertEqual(result['normalized']['fields']['nutrient_observations'][0]['quantity']['value'], '0.125')
        payload['source_numeric_lexemes']['/amount'] = '999'
        result = normalize_payload(payload, 'dietary_assertion')
        self.assertIn('nutrient_numeric_lexeme_conflict', result['uncertainty'])
        self.assertTrue(any(i['severity'] == 'error' for i in result['issues']))

    def test_all_nonrecipe_domains_use_core_identity_and_review_gates(self):
        from normalization_core import NormalizationStore, digest, gold_readiness, run_rules
        domains = {'barcode': 'barcodes', 'ingredient': 'ingredients', 'dietary_assertion': 'dietary',
                   'supplier': 'suppliers', 'citation': 'citations', 'profile': 'user_profiles', 'inventory': 'inventory'}
        fixture = json.loads((ROOT / 'tests/fixtures/normalization_domains.synthetic.json').read_text())
        with tempfile.TemporaryDirectory() as directory, NormalizationStore(directory) as store:
            for index, case in enumerate(fixture['cases']):
                record = {'domain': domains[case['record_type']], 'record_type': case['record_type'],
                          'source_key': 'synthetic-source', 'source_version': 'synthetic-v1',
                          'record_id': 'synthetic-' + str(index), 'content_sha256': digest(case['payload']),
                          'payload': copy.deepcopy(case['payload'])}
                artifact = run_rules(record, store=store)
                self.assertEqual(artifact, run_rules(record, store=store))
                self.assertEqual(artifact['source_original'], case['payload'])
                self.assertEqual(artifact['versions']['domain_rule_version'], RULE_VERSION)
                self.assertEqual(artifact['review']['status'], 'pendingreview')
                self.assertFalse(gold_readiness(artifact, 'en', store)['ready'])

    def test_unmapped_nutrient_columns_preserved_not_guessed(self):
        result = normalize_payload({'name': 'Synthetic', 'nutriments': {'salt_100g': 2}}, 'dietary_assertion')
        fields = result['normalized']['fields']
        self.assertEqual(fields['nutrients_unmapped'], {'salt_100g': 2})
        self.assertEqual(fields['nutrient_observations'], [])
        self.assertFalse(fields['automatic_diet_qualification'])

    def test_supplier_places_and_ownership_stay_source_claims(self):
        for kind in ('place', 'organization', 'company_ownership', 'supplier_entity'):
            result = normalize_payload({'type': kind, 'name': 'Synthetic name', 'country': 'ZZ',
                'relations': [{'kind': 'owned_by', 'target_id': 'synthetic-owner'}]}, 'supplier')
            fields = result['normalized']['fields']
            self.assertEqual(fields['entity_kind'], kind)
            self.assertEqual(fields['relationship_status'], 'source_claims_not_verified_business_relationships')
            self.assertNotIn('country_of_origin', fields)
            self.assertEqual(result['normalized']['relations'][0]['status'], 'unresolved_source_claim')

    def test_urls_nonlossy(self):
        for url, expected in [('HTTPS://EXAMPLE.ORG:443/A%2fb?b=2&a=1&a=0#Exact', 'https://example.org:443/A%2fb?b=2&a=1&a=0#Exact'),
                              ('https://example.org/path?', 'https://example.org/path?'),
                              ('https://example.org/path#', 'https://example.org/path#')]:
            result = normalize_url(url)
            self.assertEqual(result['canonical'], expected)
            self.assertEqual(result['original'], url)
        self.assertNotEqual(normalize_url('https://example.org')['canonical'], normalize_url('https://example.org/')['canonical'])

    def test_unsafe_or_unresolved_urls_not_promoted(self):
        for url in ('javascript:alert(1)', '//example.org/path', 'https://example.org/\ntext',
                    'https://example.org:bogus/', 'https://example.org\\evil/path'):
            self.assertIsNone(normalize_url(url)['canonical'])

    def test_citation_parent_digest_not_child_and_fragment_retained(self):
        result = normalize_payload({'reference': {'url': 'https://example.org/a#section', 'evidence_fragment': 'Synthetic quote'},
                                    'parent_reference': {'sha256': 'synthetic-digest'}}, 'citation')
        fields = result['normalized']['fields']
        self.assertEqual(fields['evidence_fragment'], 'Synthetic quote')
        self.assertNotIn('sha256', fields)
        self.assertEqual(fields['rights_status'], 'source_claims_not_rights_clearance')

    def test_household_scope_not_inferred_from_names(self):
        for kind in ('profile', 'inventory'):
            result = normalize_payload({'name': 'Same synthetic name', 'household_id': 'a'}, kind)
            self.assertIn('household_scope_missing', [item['code'] for item in result['issues']])
            self.assertFalse(result['normalized']['fields']['cross_household_merge_allowed'])
            a = normalize_payload({'namespace': 'synthetic', 'household_id': 'a', 'user_id': '1'}, kind)
            b = normalize_payload({'namespace': 'synthetic', 'household_id': 'b', 'user_id': '1'}, kind)
            self.assertNotEqual(a['normalized']['fields']['identity_scope'], b['normalized']['fields']['identity_scope'])

    def test_readonly_barcode_reference_not_invented_product(self):
        result = normalize_payload({'kind': 'readonly_source_reference', 'binding_status': 'verified', 'tables': []}, 'barcode')
        self.assertTrue(result['normalized']['fields']['reference_only'])
        self.assertNotIn('barcodes', result['normalized']['fields'])

    def test_malformed_and_unsupported_types_are_review_errors(self):
        for payload, kind in (('not-object', 'barcode'), ({'name': 'synthetic'}, 'unknown')):
            result = normalize_payload(payload, kind)
            self.assertTrue(result['required_review'])
            self.assertTrue(any(i['severity'] == 'error' for i in result['issues']))


if __name__ == '__main__':
    unittest.main()
