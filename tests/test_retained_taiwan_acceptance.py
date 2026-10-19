"""Offline acceptance-proposal bindings; no originals or owner execution."""
from copy import deepcopy
import builtins
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('taiwan_acceptance', ROOT / 'scripts/propose-retained-taiwan-acceptance.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class AcceptanceProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = [
            (ROOT / 'tests/fixtures/retained-taiwan-third-run-summary.json').read_bytes(),
            (ROOT / 'tests/fixtures/retained-taiwan-third-run-publication-receipt.json').read_bytes(),
            (ROOT / 'docs/collection-selections/global-comprehensive-selection.json').read_bytes(),
            (ROOT / 'docs/collection-selections/global-comprehensive-manifest.json').read_bytes(),
        ]
        cls.raw = (ROOT / 'docs/collection-selections/retained-taiwan-acceptance-proposal.json').read_bytes()
        cls.value = json.loads(cls.raw)

    def reject(self, value):
        with self.assertRaises(ValueError):
            m.validate_proposal(m.canonical(value), *self.inputs)

    def test_exact_published_inputs_reproduce_the_manifest(self):
        self.assertEqual(m.build_proposal(*self.inputs), self.value)
        result = m.validate_proposal(self.raw, *self.inputs)
        self.assertEqual(result['status'], 'verified-inactive-proposal')
        for key in ['runtimeEnabled', 'dispositionApplied', 'preparationEnabled',
                    'custodyChecked', 'ownerExecutionPerformed']:
            self.assertIs(result[key], False)

    def test_exact_three_result_bound_sources(self):
        self.assertEqual([row['assetIndex'] for row in self.value['items']], [4747, 4748, 4749])
        self.assertEqual([row['validationProposal']['parser']['pageCount'] for row in self.value['items']], [8, 4, 10])
        for row in self.value['items']:
            self.assertEqual(m.sha(m.canonical(row['validationProposal'])), row['validationProposalCanonicalSHA256'])
            self.assertEqual(m.sha(m.canonical(row['sourceContract'])), row['sourceContractSHA256'])
            self.assertIsNone(row['proposedCustodyReference']['originalAcquiredAt'])
            self.assertEqual(row['preservedDownstreamHolds'], m.HOLDS)

    def test_existing_002_context_and_hold_are_preserved(self):
        context = self.value['existingOwnerContextBinding']
        self.assertEqual(context['handoffId'], 'owner-local-comprehensive-20261018-002')
        self.assertEqual(context['runtimeConfigSHA256'], '28acbde120ac7d457f24af8cd2e3203927bb770137b8ce414c0d7a082e63b4ba')
        self.assertEqual(context['dispatchHoldSHA256'], 'a78f209e2d1636cadf3ad913514d98472bf3e173b3c08c008ae573cade56ad8b')
        self.assertFalse(context['existingRuntimeChanged'])
        self.assertFalse(context['successorHandoffCreated'])
        self.assertTrue(context['progressAndOPCRemainOnExistingHandoff'])
        for key, replacement in [('handoffId', 'replacement-handoff'),
                                 ('dispatchHoldSHA256', '0' * 64),
                                 ('successorHandoffCreated', True)]:
            value = deepcopy(self.value)
            value['existingOwnerContextBinding'][key] = replacement
            self.reject(value)

    def test_builder_and_validator_have_no_external_side_effects(self):
        with (patch.object(builtins, 'open', side_effect=AssertionError('file access')),
             patch.object(Path, 'open', side_effect=AssertionError('path access')),
             patch.object(socket, 'socket', side_effect=AssertionError('network')),
             patch.object(subprocess, 'Popen', side_effect=AssertionError('parser'))):
            self.assertEqual(m.build_proposal(*self.inputs), self.value)
            self.assertEqual(m.validate_proposal(self.raw, *self.inputs)['sourceCount'], 3)

    def test_each_published_input_is_raw_byte_pinned(self):
        for index in range(4):
            with self.subTest(index=index):
                inputs = self.inputs[:]
                inputs[index] += b' '
                with self.assertRaises(ValueError):
                    m.build_proposal(*inputs)

    def test_reject_missing_extra_duplicate_or_reordered_identity(self):
        for items in [self.value['items'][:-1], self.value['items'] + self.value['items'][:1],
                      [self.value['items'][0]] * 3, list(reversed(self.value['items']))]:
            value = deepcopy(self.value)
            value['items'] = items
            self.reject(value)

    def test_no_activation_permission_or_safety_flag_can_be_upgraded(self):
        for name in ['runtimeEnabled', 'acceptanceSelected', 'dispositionApplied', 'preparationEnabled']:
            value = deepcopy(self.value)
            value[name] = True
            self.reject(value)
        for name in self.value['invariants']:
            value = deepcopy(self.value)
            value['invariants'][name] = True
            self.reject(value)

    def test_reject_timestamp_body_path_intent_or_source_changes(self):
        for path, replacement in [
            (['proposedCustodyReference', 'originalAcquiredAt'], '2026-10-18T23:00:00Z'),
            (['proposedCustodyReference', 'relativePath'], 'collection/new-original.pdf'),
            (['proposedCustodyReference', 'runtimeRoot'], '/tmp/replacement'),
            (['proposedCustodyReference', 'sha256'], '0' * 64),
            (['proposedCustodyReference', 'bytes'], 1),
            (['proposedCustodyReference', 'oldFailedIntent', 'sha256'], '0' * 64),
            (['proposedCustodyReference', 'oldFailedDetail', 'preserveBytes'], False),
            (['sourceContract', 'url'], 'https://example.invalid/other.pdf'),
            (['sourceContractSHA256'], '0' * 64),
            (['preparationEnabledByThisProposal'], True),
        ]:
            with self.subTest(path=path):
                value = deepcopy(self.value)
                target = value['items'][0]
                for name in path[:-1]:
                    target = target[name]
                target[path[-1]] = replacement
                self.reject(value)

    def test_reject_parser_outcome_mutation_even_with_rehashed_report(self):
        for name, replacement in [('status', 'blocked'), ('pageCount', 1),
                                  ('allPagesTraversed', False), ('diagnosticBytes', 1),
                                  ('encrypted', True), ('pdfinfoVersion', '25.03.0')]:
            value = deepcopy(self.value)
            row = value['items'][0]
            row['validationProposal']['parser'][name] = replacement
            row['validationProposalCanonicalSHA256'] = m.sha(m.canonical(row['validationProposal']))
            self.reject(value)

    def test_reject_downstream_hold_removal_and_permission_changes(self):
        for name in ['preservedDownstreamHolds', 'existingPreparationSelection', 'sourceContract']:
            value = deepcopy(self.value)
            if name == 'preservedDownstreamHolds':
                value['items'][0][name] = []
            else:
                value['items'][0][name]['downstreamHolds'] = []
            self.reject(value)
        value = deepcopy(self.value)
        value['items'][0]['existingPreparationSelection']['permissions']['extract'] = False
        self.reject(value)

    def test_reject_removed_review_gate_or_fabricated_approval(self):
        value = deepcopy(self.value)
        value['requiredGates'].pop()
        self.reject(value)
        value = deepcopy(self.value)
        value['requiredGates'][0]['status'] = 'approved'
        self.reject(value)

    def test_reject_duplicate_keys_nonfinite_json_and_nonobject(self):
        for raw in [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'[]', b'null']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                m.validate_proposal(raw, *self.inputs)

    def test_metadata_validation_does_not_mutate_input_objects(self):
        before = self.inputs[:]
        manifest = self.raw
        m.validate_proposal(manifest, *self.inputs)
        self.assertEqual(before, self.inputs)
        self.assertEqual(manifest, self.raw)


if __name__ == '__main__':
    unittest.main()
