"""Synthetic existing qualification/claim/witness objects; never actual mapping."""
import copy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh.acceptance import canonical, fingerprint
from offmenu.refresh.deterministic_association import (
    CATEGORIES, INVENTORIES, VERSION, SelectionPolicy, select_association, uncertainty_metrics)
from offmenu.refresh.english_extension import _Check, ReviewedWitness, EvidenceError
from test_english_extension import Fixture as NativeFixture, WORK, encode


class Fixture(NativeFixture):
    def __init__(self, root):
        super().__init__(root)
        self.binding = {'sourceId': self.original_contract.source_id,
            'releaseId': self.original_contract.release_id, 'sourceRecordId': 'invented-source-record',
            'originalSHA256': self.original.sha256, 'qualificationSha256': 'a'*64,
            'fieldOriginsSha256': 'b'*64, 'fieldPointer': '/data/ingredientsText',
            'textSha256': 'c'*64, 'candidateSha256': 'd'*64, 'candidateLine': 1}
        self.dictionary = {'version': 'dictionary-1', 'entries': []}
        self.rules = {'version': 'rules-1', 'entries': []}
        self.adjudications = {'version': 'adjudications-1', 'entries': []}
        self.add_rule('r1', 'I')
        self.seal()

    def witness(self, name, expected, authority='synthetic-reviewer'):
        scope = {**copy.deepcopy(expected), 'reviewAuthority': authority}
        return ReviewedWitness(self.pin(name+'.json', encode(scope)), scope, authority)

    def version(self, claim, role):
        return _Check(self.policy, self).claim_context(claim, role)

    def add_rule(self, rule_id, ingredient, specificity='specific'):
        entry_id = 'entry-'+rule_id
        data, version = self.version(ingredient, 'ingredient-identity')
        self.dictionary['entries'].append({'entryId': entry_id,
            'ingredientIdentityClaimId': ingredient, 'ingredientVersion': version,
            'specificity': specificity})
        assertion = {'assertionId': 'assertion-'+rule_id, 'productIdentityClaimId': 'P',
            'ingredientIdentityClaimId': ingredient, 'relation': 'declares-ingredient',
            'state': 'reviewed', 'evidence': [self.ext['policies']['identity']]}
        self.rules['entries'].append({'ruleId': rule_id, 'inputSha256': fingerprint(self.binding),
                                     'entryId': entry_id, 'assertion': assertion})
        product, product_version = self.version('P', 'source-product-assignment')
        self.relationships[assertion['assertionId']] = self.witness('relationship-'+rule_id,
            {'type': 'product-ingredient-relationship', 'assertionId': assertion['assertionId'],
             'assertionSha256': fingerprint(assertion), 'relation': assertion['relation'],
             'inputBinding': self.binding, 'decisionState': 'affirmed', 'reviewStatus': 'reviewed',
             'product': product_version, 'ingredient': version,
             'productContext': {k: product[k] for k in
                               ('foodProduct', 'formulation', 'package', 'market', 'effectivePeriod')},
             'foodForm': data['foodForm']})

    def second_outcome(self):
        data = copy.deepcopy(self.ingredient_data); data['graphIri'] += '-other'
        self.set_claim('J', data); self.add_rule('r2', 'J'); self.seal()

    def adjudicate(self, chosen, state='affirmed'):
        self.adjudications['entries'] = [{'adjudicationId': 'a1',
            'inputSha256': fingerprint(self.binding),
            'candidateRuleIds': [r['ruleId'] for r in self.rules['entries']],
            'selectedRuleId': chosen, 'state': state, 'evidence': [self.ext['policies']['identity']]}]
        self.seal()

    def seal(self):
        pins = {k: self.pin(k+'.json', encode(getattr(self, k))) for k in INVENTORIES}
        versions = {k: getattr(self, k)['version'] for k in INVENTORIES}
        self.selection_policy = SelectionPolicy(self.original_contract, copy.deepcopy(self.binding), 'P',
            pins, versions, review_authorities=frozenset(['synthetic-reviewer']))
        inp = self.witness('input-review', {'type': 'deterministic-association-input',
            'inputBinding': self.binding, 'purpose': 'private-relationship-selection',
            'decisionState': 'affirmed', 'reviewStatus': 'reviewed'})
        inv = self.witness('inventory-review', {'type': 'deterministic-association-inventories',
            'methodVersion': VERSION, 'inputBinding': self.binding, 'productClaimId': 'P',
            'inventories': {k: {'pin': pins[k], 'version': versions[k]} for k in INVENTORIES},
            'decisionState': 'affirmed', 'reviewStatus': 'reviewed'})
        self.selection_policy = replace(self.selection_policy, input_witness=inp, inventory_witness=inv)

    def select(self, policy=None):
        return select_association(self.binding, policy or self.selection_policy, self)


class SelectionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=WORK); self.addCleanup(self.temp.cleanup)
        self.f = Fixture(Path(self.temp.name))

    def test_supported_existing_assertion_replay_and_no_mutation(self):
        f = self.f; before = copy.deepcopy((f.binding, f.dictionary, f.rules, f.adjudications))
        a = f.select(); b = f.select()
        self.assertEqual(canonical(a), canonical(b))
        self.assertEqual(a['category'], 'confirmed-specific'); self.assertEqual(a['state'], 'reviewed')
        self.assertEqual(a['selectedAssertions'], [f.rules['entries'][0]['assertion']])
        self.assertEqual(before, (f.binding, f.dictionary, f.rules, f.adjudications))
        a['selectedAssertions'][0]['state'] = 'changed'
        self.assertEqual(f.select(), b)

    def test_default_and_missing_authority_refuse(self):
        self.assertEqual(select_association({})['reasons'], ['selection-unbound'])
        self.assertEqual(self.f.select(replace(self.f.selection_policy, review_authorities=frozenset()))
                         ['selectedAssertions'], [])

    def test_wrong_input_scope_refuses_before_matching(self):
        f = self.f; f.binding['candidateLine'] = 2
        self.assertEqual(f.select()['reasons'], ['selection-input-scope-mismatch'])

    def test_absent_or_foreign_input_review_refuses(self):
        f = self.f
        for witness in [None, replace(f.selection_policy.input_witness, authority='foreign')]:
            self.assertEqual(f.select(replace(f.selection_policy, input_witness=witness))['reasons'],
                             ['selection-input-unqualified'])

    def test_stale_input_qualification_cannot_reuse_selected_review(self):
        f = self.f; f.binding['qualificationSha256'] = 'e'*64
        p = replace(f.selection_policy, expected_input=copy.deepcopy(f.binding))
        self.assertEqual(f.select(p)['reasons'], ['selection-input-unqualified'])

    def test_stale_inventory_version_or_authority_refuses(self):
        f = self.f
        p = replace(f.selection_policy, inventory_versions={**f.selection_policy.inventory_versions,
                                                           'dictionary': 'dictionary-2'})
        self.assertEqual(f.select(p)['reasons'], ['selection-inventory-unqualified'])
        p = replace(f.selection_policy, inventory_witness=replace(f.selection_policy.inventory_witness,
                                                                 authority='foreign'))
        self.assertEqual(f.select(p)['reasons'], ['selection-inventory-unqualified'])

    def test_explicit_empty_adjudication_inventory_required(self):
        f = self.f; self.assertEqual(f.select()['category'], 'confirmed-specific')
        p = replace(f.selection_policy, inventory_pins={k:v for k,v in
                    f.selection_policy.inventory_pins.items() if k != 'adjudications'})
        self.assertEqual(f.select(p)['selectedAssertions'], [])
        f.blobs['adjudications.json'] = b'not the selected empty inventory'
        self.assertEqual(f.select()['selectedAssertions'], [])

    def test_broader_stays_broader_not_specific(self):
        f = self.f; f.dictionary['entries'][0]['specificity'] = 'broader'; f.seal()
        self.assertEqual(f.select()['category'], 'broader-only')

    def test_no_applicable_rule_is_missing_not_absence(self):
        f = self.f; f.rules['entries'][0]['inputSha256'] = 'e'*64; f.seal()
        self.assertEqual(f.select()['category'], 'unmapped/missing-evidence')
        self.assertEqual(f.select()['reasons'], ['selection-no-applicable-rule'])

    def test_qualified_endpoints_need_relationship_witness(self):
        f = self.f; f.relationships.clear()
        a = f.select(); self.assertEqual(a['selectedAssertions'], [])
        self.assertEqual(a['alternatives'][0]['reasons'], ['english-relationship-unqualified'])

    def test_nonaffirmative_or_foreign_relationship_never_selected(self):
        f = self.f; witness = f.relationships['assertion-r1']
        for replacement in [replace(witness, authority='foreign'),
                            f.witness('rejected-relation', {**{k:v for k,v in witness.scope.items()
                                if k != 'reviewAuthority'}, 'decisionState': 'rejected'})]:
            f.relationships['assertion-r1'] = replacement
            self.assertEqual(f.select()['selectedAssertions'], [])

    def test_changed_dictionary_bytes_need_fresh_inventory_review(self):
        f = self.f; f.dictionary['entries'][0]['specificity'] = 'broader'
        pin = f.pin('dictionary.json', encode(f.dictionary))
        p = replace(f.selection_policy, inventory_pins={**f.selection_policy.inventory_pins,
                                                      'dictionary': pin})
        self.assertEqual(f.select(p)['reasons'], ['selection-inventory-unqualified'])

    def test_changed_endpoint_version_refuses(self):
        f = self.f; f.dictionary['entries'][0]['ingredientVersion']['dataSha256'] = 'f'*64; f.seal()
        self.assertEqual(f.select()['alternatives'][0]['reasons'], ['selection-endpoint-version'])

    def test_product_context_and_input_contract_hold_refuse(self):
        f = self.f; product = copy.deepcopy(f.product_data); product['formulation']['snapshotId'] = None
        f.set_claim('P', product)
        self.assertEqual(f.select()['reasons'], ['english-formulation-unresolved'])
        p = replace(f.selection_policy, input_contract=replace(f.original_contract, holds=('held',)))
        self.assertEqual(f.select(p)['reasons'], ['english-source-operation-unqualified'])

    def test_competing_outcomes_no_majority_vote(self):
        f = self.f; f.second_outcome()
        f.add_rule('r3', 'I'); f.add_rule('r4', 'I'); f.seal()
        a = f.select(); self.assertEqual(a['category'], 'ambiguous/conflicting')
        self.assertEqual(a['selectedAssertions'], []); self.assertEqual(len(a['alternatives']), 4)

    def test_same_concept_multiple_rules_retains_all_source_assertions(self):
        f = self.f; f.add_rule('r0', 'I'); f.seal()
        a = f.select(); self.assertEqual(len(a['selectedAssertions']), 2)
        self.assertEqual([r['ruleId'] for r in a['alternatives']], ['r0', 'r1'])

    def test_inventory_reordering_preserves_semantic_order_new_pins_retained(self):
        f = self.f; f.add_rule('r0', 'I'); f.seal(); a = f.select()
        f.dictionary['entries'].reverse(); f.rules['entries'].reverse(); f.seal(); b = f.select()
        self.assertNotEqual(a['inventories'], b['inventories'])
        for k in ['category', 'state', 'selectedAssertions', 'alternatives', 'reasons']:
            self.assertEqual(a[k], b[k])

    def test_exact_accepted_adjudication_selects_and_retains_alternatives(self):
        f = self.f; f.second_outcome(); f.adjudicate('r2')
        a = f.select(); self.assertEqual(a['category'], 'confirmed-specific')
        self.assertEqual(a['selectedAssertions'][0]['ingredientIdentityClaimId'], 'J')
        self.assertEqual(len(a['alternatives']), 2); self.assertEqual(a['adjudicationIds'], ['a1'])

    def test_stale_or_unresolved_adjudication_never_promotes(self):
        f = self.f; f.second_outcome(); f.adjudicate(None, 'unresolved')
        self.assertEqual(f.select()['category'], 'ambiguous/conflicting')
        f.adjudicate('r1'); f.adjudications['entries'][0]['candidateRuleIds'] = ['r1']; f.seal()
        result = f.select()
        self.assertEqual(result['reasons'], ['selection-adjudication-stale'])
        self.assertEqual(len(result['alternatives']), 2)
        self.assertEqual(result['inputBinding'], f.binding)
        self.assertEqual(result['inventories']['adjudications']['pin'],
                         f.selection_policy.inventory_pins['adjudications'])

    def test_competing_adjudications_are_not_last_writer_wins(self):
        f = self.f; f.second_outcome(); f.adjudicate('r1')
        second = copy.deepcopy(f.adjudications['entries'][0]); second.update(adjudicationId='a2', selectedRuleId='r2')
        f.adjudications['entries'].append(second); f.seal()
        self.assertEqual(f.select()['category'], 'ambiguous/conflicting')

    def test_unknown_candidate_does_not_silently_lose(self):
        f = self.f; f.second_outcome(); del f.claims['J']
        self.assertEqual(f.select()['category'], 'unmapped/missing-evidence')
        self.assertEqual(f.select()['selectedAssertions'], [])

    def test_proposed_assertion_not_rewritten_to_reviewed(self):
        f = self.f; f.rules['entries'][0]['assertion']['state'] = 'proposed'; f.seal()
        self.assertEqual(f.select()['selectedAssertions'], [])

    def test_work_bounds_and_fixed_exception_diagnostics(self):
        f = self.f; f.second_outcome()
        self.assertEqual(f.select(replace(f.selection_policy, max_entries=1))['selectedAssertions'], [])
        with patch.object(f, 'evidence', side_effect=EvidenceError('private source literal')):
            self.assertEqual(f.select()['reasons'], ['selection-invalid-evidence'])

    def test_supported_call_does_not_open_files_database_or_network(self):
        with patch('builtins.open', side_effect=AssertionError('file IO')), \
             patch('sqlite3.connect', side_effect=AssertionError('DB IO')), \
             patch('socket.socket', side_effect=AssertionError('network IO')):
            self.assertEqual(self.f.select()['category'], 'confirmed-specific')


class MetricsTest(unittest.TestCase):
    def test_explicit_partition_and_unclear_categories(self):
        counts = dict(zip(CATEGORIES, [4, 2, 1, 3]))
        m = uncertainty_metrics(counts, assessed_denominator=10, unassessed=5, excluded=2)
        self.assertEqual(m['unclearNumerator'], 6); self.assertEqual(m['unclearPercent'], 60)
        self.assertEqual(m['unassessed'], 5); self.assertEqual(m['excluded'], 2)

    def test_unknown_and_zero_denominators_never_zero_percent(self):
        counts = dict.fromkeys(CATEGORIES, 0); counts[CATEGORIES[3]] = 1
        a = uncertainty_metrics(counts, assessed_denominator=None)
        self.assertEqual(a['observedUnclearCount'], 1)
        self.assertIsNone(a['unclearNumerator']); self.assertIsNone(a['unclearPercent'])
        self.assertIsNone(a['unassessed']); self.assertIsNone(a['excluded'])
        b = uncertainty_metrics(dict.fromkeys(CATEGORIES, 0), assessed_denominator=0)
        self.assertEqual(b['unclearNumerator'], 0); self.assertIsNone(b['unclearPercent'])

    def test_invalid_count_or_denominator_rejected(self):
        for counts, n in [(dict.fromkeys(CATEGORIES, 0), 1), (dict.fromkeys(CATEGORIES, True), 4),
                          (dict.fromkeys(CATEGORIES, -1), None), ({}, None)]:
            with self.assertRaisesRegex(ValueError, 'selection-metrics-invalid'):
                uncertainty_metrics(counts, assessed_denominator=n)


if __name__ == '__main__':
    unittest.main()
