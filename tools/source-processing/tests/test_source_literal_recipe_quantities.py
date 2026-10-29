"""Generated source-literal and mixed metric contracts; no corpus/store/cache."""
import copy
import json
from pathlib import Path
import sys
import unittest
from dataclasses import replace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import gold_recipe_actions as actions
from source_literal_recipe_quantities import validate_source_literal, SourceLiteralQuantityError
from test_gold_recipe_actions import (PinnedNativeFixture, _source_literal_case,
    _record, _rules_for, _review, _connections, _span)


def mixed_case(n):
    record = _record()
    record['ingredients'][0].update(raw_text='400 g flour', source_name_text='flour', quantity='400', unit='g')
    record['ingredients'].append(dict(id='generated:line:eggs', ordinal=2,
        raw_text='4 large eggs', source_name_text='eggs', quantity='4', unit='eggs'))
    record['ingredients'].append(dict(id='generated:line:extra', ordinal=3,
        raw_text='Extra flour', source_name_text='extra flour', quantity=None, unit=None))
    record['steps'][0]['raw_text'] = 'Mix 400 g flour.'
    record['steps'][1]['raw_text'] = 'Serve 4 large eggs.'
    record['steps'].append(dict(ordinal=3, source_section='Method', raw_text='Mix extra flour.'))
    rules = _rules_for(n, record)
    review = _review(n, rules, amount='400', unit='g')
    t = review['normalized']['fields']['recipe_menu_template']
    serve = t['template_instances'][1]
    definition = t['learned_templates'][1]['definition']
    definition['pattern'] = 'Serve {count} {material}.'
    definition['slot_types']['count'] = 'quantity'
    tid = n.recipes.canonical_template_id(definition)
    t['learned_templates'][1]['template_id'] = serve['template_id'] = tid
    serve['slots']['material']['value'] = t['ingredients'][1]['ingredient_id']
    serve['slots']['count'] = dict(type='quantity', value=dict(value='4', unit='eggs', descriptor='large'),
        evidence=[_span('/steps/1/raw_text', record['steps'][1]['raw_text'], '4')], lexical_unit=None)
    extra_definition = dict(action='mix', phase='preparation', pattern='Mix {material}.',
        slot_types=dict(material='ingredient_reference'), source_locale='en', grammar_context=dict(mood='imperative', fixture=True))
    extra_id = n.recipes.canonical_template_id(extra_definition)
    t['learned_templates'].append(dict(template_id=extra_id, definition=extra_definition))
    extra_span = copy.deepcopy(t['steps'][2]['source_span'])
    t['template_instances'].append(dict(instance_id='generated:extra', template_id=extra_id,
        step_id=t['steps'][2]['step_id'], source_order=2, evidence=[extra_span],
        slots=dict(material=dict(type='ingredient_reference', value='generated:line:extra',
            evidence=[extra_span], lexical_unit=None)), depends_on=['generated:mix'],
        unknown_parameters=['extra_flour_quantity_unknown']))
    review['normalized']['fields']['translation_plan']['template_ids'] = [d['template_id'] for d in t['learned_templates']]
    connections = _connections(n, review, quantity_value='400', quantity_unit='g')
    connections['materials'] = []
    connections['material_inputs'] = []
    link = connections['ingredient_links'][1]
    link.update(source_ingredient_line_id='generated:line:eggs', ingredient_entity_id='ingredient:eggs',
                quantity=dict(value='4', unit='eggs'), quantity_slot_name='count', unit_slot_name=None)
    connections['entities'].append(dict(id='ingredient:eggs', domain='ingredients', state='verified'))
    connections['entities'].append(dict(id='ingredient:extra', domain='ingredients', state='verified'))
    connections['ingredient_links'].append(dict(instance_id='generated:extra', slot_name='material',
        source_ingredient_line_id='generated:line:extra', ingredient_entity_id='ingredient:extra',
        quantity=None, quantity_slot_name=None, unit_slot_name=None,
        citation_ids=['citation:generated'], evidence=[extra_span]))
    connections['action_citations'].append(dict(instance_id='generated:extra',
        citation_ids=['citation:generated'], evidence=[extra_span]))
    connections['source_literal_quantities'] = [dict(source_ingredient_line_id='generated:line:eggs',
        kind='item-count', value='4', unit='eggs', descriptor='large',
        evidence=[_span('/ingredients/1/raw_text', '4 large eggs', '4 large eggs')],
        citation_ids=['citation:generated'])]
    return rules, review, connections


class SourceLiteralQuantityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.n = PinnedNativeFixture().load()
        cls.native = actions.NativeRecipeHelpers(actions.NATIVE_PIN, cls.n.expected_hashes,
            cls.n.recipes.canonical_template_id, cls.n.recipes.validate_reviewed_template,
            cls.n.core.validate_and_cache_actual_review, cls.n.recipes.recipe_translation_units,
            cls.n.core.validate_and_cache_translation, cls.n.domains.normalize_quantity, cls.n.core.digest)

    @classmethod
    def tearDownClass(cls): cls.n.close()

    def connect(self, rules, review, connections, **kwargs):
        connections['qualification']['content_sha256'] = self.n.core.digest(
            {k: v for k, v in connections.items() if k != 'qualification'})
        return actions.connect_recipe_actions(rules, review, native=self.native, connections=connections, **kwargs)

    def test_literal_evidence_binds_complete_numeric_expression_in_full_source(self):
        for count, amount, phrase in ((True, '4', '4 large eggs'), (False, '2', '2 handfuls')):
            for prefix in ('1/', '1 / ', '1⁄', '1∕', '3–', '3 – ', '3—', '3-', '3‑', '3 to ',
                           '-', '- ', '−', '− ', '+', '+ ', '＋', '1.', '1,', '1, ',
                           '-(', '1/ (', '3–['):
                for suffix_only_span in (False, True):
                    with self.subTest(count=count, prefix=prefix, suffix_only_span=suffix_only_span):
                        rules, review, c = _source_literal_case(self.n, count=count)
                        ingredient = rules['normalized']['fields']['recipe_menu_template']['ingredients'][0]
                        row = c['source_literal_quantities'][0]
                        source = copy.deepcopy(rules['source_original'])
                        text = prefix + phrase
                        source['ingredients'][0]['raw_text'] = text
                        row['evidence'] = [_span('/ingredients/0/raw_text', text, phrase if suffix_only_span else text)]
                        with self.assertRaises(SourceLiteralQuantityError):
                            validate_source_literal(row, ingredient,
                                allowed_pointers={'/ingredients/0/raw_text'}, source=source,
                                citations={'citation:generated': {'state':'verified'}}, validate_evidence=actions._evidence)

    def test_full_source_token_check_preserves_standalone_literals(self):
        for count, phrase in ((True, '4 large eggs'), (False, '2 handfuls')):
            for prefix, suffix in (('', ''), ('* ', ''), ('Use ', '.'), ('(', ')'),
                                   ('[ (\t', ')]'), ('（', '）'), ('［\u00a0（', '）］')):
                with self.subTest(count=count, prefix=prefix):
                    rules, review, c = _source_literal_case(self.n, count=count)
                    ingredient = rules['normalized']['fields']['recipe_menu_template']['ingredients'][0]
                    row = c['source_literal_quantities'][0]
                    source = copy.deepcopy(rules['source_original'])
                    text = prefix + phrase + suffix
                    source['ingredients'][0]['raw_text'] = text
                    row['evidence'] = [_span('/ingredients/0/raw_text', text, phrase)]
                    result = validate_source_literal(row, ingredient,
                        allowed_pointers={'/ingredients/0/raw_text'}, source=source,
                        citations={'citation:generated': {'state':'verified'}}, validate_evidence=actions._evidence)
                    self.assertEqual(row, result)

    def test_grouped_range_endpoints_are_not_standalone_literals(self):
        for count, phrase, lower in ((True, '4 large eggs', '3'), (False, '2 handfuls', '1')):
            for opening, closing in (('(', ')'), ('[', ']'), ('([', '])'),
                                     ('\t( [', '])'), ('\u00a0(', ')'),
                                     ('（', '）'), ('［', '］'), ('｟（', '）｠')):
                for operator in (' to ', ' TO\t', '\u00a0to\u00a0', ' . ', ', ', ' – '):
                    for clipped in (False, True):
                        with self.subTest(count=count, opening=opening, operator=operator, clipped=clipped):
                            rules, review, c = _source_literal_case(self.n, count=count)
                            ingredient = rules['normalized']['fields']['recipe_menu_template']['ingredients'][0]
                            row = c['source_literal_quantities'][0]
                            source = copy.deepcopy(rules['source_original'])
                            raw = lower + operator + opening + phrase + closing
                            source['ingredients'][0]['raw_text'] = raw
                            row['evidence'] = [_span('/ingredients/0/raw_text', raw, phrase if clipped else raw)]
                            with self.assertRaises(SourceLiteralQuantityError):
                                validate_source_literal(row, ingredient,
                                    allowed_pointers={'/ingredients/0/raw_text'}, source=source,
                                    citations={'citation:generated':{'state':'verified'}}, validate_evidence=actions._evidence)

    def test_literal_and_known_metric_allocate_once_unknown_extra_stays_none(self):
        rules, review, c = mixed_case(self.n)
        out = self.connect(rules, review, c)
        self.assertEqual('ready-for-review', out['status'], out['holds'])
        self.assertEqual(['Mix 400 g flour.', 'Serve 4 large eggs.', 'Mix extra flour.'], [a['english_text'] for a in out['actions']])
        self.assertEqual('400', out['ingredient_links'][0]['allocation']['normalized']['value'])
        self.assertEqual('source-literal', out['ingredient_links'][1]['allocation']['status'])
        self.assertIsNone(review['normalized']['fields']['recipe_menu_template']['ingredients'][2]['quantity'])
        self.assertIsNone(out['ingredient_links'][2]['allocation'])
        self.assertIn('extra_flour_quantity_unknown', out['actions'][2]['unknown_parameters'])
        import jsonschema
        jsonschema.validate(out, json.loads((ROOT/'gold-recipe-actions.schema.json').read_text()))

    def test_metric_null_partial_wrong_line_duplicate_or_wrong_slot_cannot_hide_400g(self):
        for change in ('null', 'partial', 'wrong-line', 'duplicate', 'wrong-slot'):
            with self.subTest(change=change):
                rules, review, c = mixed_case(self.n)
                link = c['ingredient_links'][0]
                if change == 'null': link['quantity'] = None
                elif change == 'partial': link['quantity']['value'] = '200'
                elif change == 'wrong-line': link['source_ingredient_line_id'] = 'generated:line:extra'
                elif change == 'duplicate': c['ingredient_links'].append(copy.deepcopy(link))
                else: link['quantity_slot_name'] = 'absent'
                out = self.connect(rules, review, c)
                self.assertEqual('held', out['status'])

    def test_invalid_literal_proofs_and_no_metric_conversion_or_range(self):
        for change in ('kind', 'unit', 'descriptor', 'range', 'negative', 'float', 'zero',
                       'extra-key', 'wrong-line', 'citation', 'proof-text', 'unrelated-step'):
            with self.subTest(change=change):
                rules, review, c = _source_literal_case(self.n, count=True)
                row = c['source_literal_quantities'][0]
                if change == 'kind': row['kind'] = 'mass'
                elif change == 'unit': row['unit'] = 'g'
                elif change == 'descriptor': row['descriptor'] = 'small'
                elif change == 'range': row['value'] = '3–4'
                elif change == 'negative': row['value'] = '-4'
                elif change == 'float': row['value'] = 4.0
                elif change == 'zero': row['value'] = '0'
                elif change == 'extra-key': row['target_unit'] = 'g'
                elif change == 'wrong-line': row['source_ingredient_line_id'] = 'other'
                elif change == 'citation': row['citation_ids'] = ['absent']
                elif change == 'proof-text': row['evidence'][0]['text'] = '4 small eggs'
                else: row['evidence'][0]['pointer'] = '/title'
                out = self.connect(rules, review, c)
                self.assertEqual('held', out['status'])

    def test_method_only_measure_evidence_binds_to_ingredient_reference(self):
        rules, review, c = _source_literal_case(self.n, method_evidence=True)
        out = self.connect(rules, review, c)
        self.assertEqual('ready-for-review', out['status'], out['holds'])
        self.assertEqual('Mix 2 handfuls beans.', out['actions'][0]['english_text'])
        self.assertEqual('/steps/0/raw_text', out['ingredient_links'][0]['allocation']['evidence'][0]['pointer'])

    def test_literal_profile_does_not_replace_immutable_helper_pin(self):
        rules, review, c = _source_literal_case(self.n)
        c['qualification']['content_sha256'] = self.n.core.digest({k:v for k,v in c.items()if k!='qualification'})
        out = actions.connect_recipe_actions(rules, review,
            native=replace(self.native, source_pin='not-the-native-pin'), connections=c)
        self.assertEqual('held', out['status'])
        self.assertIn({'code':'immutable_native_dependency_mismatch','target':'recipe'}, out['holds'])

    def test_semantic_review_native_pin_and_connection_receipts_still_required(self):
        for change in ('review', 'connection', 'scaffold', 'count-slot', 'count-noun'):
            with self.subTest(change=change):
                rules, review, c = _source_literal_case(self.n, count=True)
                if change == 'review': review['artifact_sha256'] = '0'*64
                elif change == 'scaffold': review['normalized']['fields']['recipe_menu_template']['ingredients'][0]['source_quantity'] = None
                elif change == 'count-slot': review['normalized']['fields']['recipe_menu_template']['template_instances'][0]['slots']['amount']['value']['descriptor'] = None
                elif change == 'count-noun': review['normalized']['fields']['recipe_menu_template']['template_instances'][0]['slots']['material']['lexical_unit'] = dict(text='large eggs',source_locale='en',context={})
                c['qualification']['content_sha256'] = self.n.core.digest({k:v for k,v in c.items() if k!='qualification'})
                if change == 'connection': c['qualification']['content_sha256'] = '0'*64
                out = actions.connect_recipe_actions(rules, review, native=self.native, connections=c)
                self.assertEqual('held', out['status'])

    def test_non_normalized_literal_allocation_schema_and_native_quantity_unchanged(self):
        import jsonschema
        rules, review, c = _source_literal_case(self.n)
        out = self.connect(rules, review, c)
        jsonschema.validate(out, json.loads((ROOT/'gold-recipe-actions.schema.json').read_text()))
        self.assertEqual('unresolved', rules['normalized']['fields']['recipe_menu_template']['ingredients'][0]['quantity']['status'])
        self.assertNotIn('normalized', out['ingredient_links'][0]['allocation'])
        self.assertNotIn('scaled_min', out['ingredient_links'][0]['allocation'])


if __name__ == '__main__': unittest.main()
