"""Keep the documented handoff compatible with actual validators; never dispatch."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/delivery'))
from stokowski_operations import OperationError, bridge_arguments, operation_key, validated


class RoutingExampleTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads((ROOT / 'examples/validation-handoff.json').read_text())

    def test_example_binds_one_issue_branch_and_finite_resource_profile(self):
        validated(self.spec)
        args = bridge_arguments(self.spec)
        self.assertEqual(args['job_id'], 'offmenu-' + operation_key(self.spec)[:48])
        self.assertEqual(args['mode'], 'read')
        self.assertGreater(args['timeout_seconds'], 0)
        self.assertLessEqual(args['timeout_seconds'], 600)
        policy = json.loads((ROOT / 'tools/delivery/capacity-policy.json').read_text())
        self.assertLessEqual(args['resources']['workers'], policy['windmill']['computation_subprocesses_per_job'])
        self.assertEqual(args['resources']['read_roots'], ['/offmenu'])
        self.assertEqual(args['resources']['write_roots'], [])

    def test_owner_change_cannot_create_a_new_operation_but_candidate_change_does(self):
        key = operation_key(self.spec)
        changed = {**self.spec, 'owner': 'other-owner'}
        self.assertEqual(operation_key(changed), key)
        changed['head'] = '6' * 40
        self.assertNotEqual(operation_key(changed), key)
        for action in ('status', 'cancel'):
            self.assertEqual(bridge_arguments(self.spec, action),
                             {'action': action, 'job_id': 'offmenu-' + key[:48]})

    def test_unbound_fields_and_unreviewed_profile_are_rejected(self):
        changed = copy.deepcopy(self.spec)
        changed['profile'] = 'arbitrary-command'
        with self.assertRaises(OperationError):
            validated(changed)
        changed = {**self.spec, 'command': 'unreviewed command'}
        with self.assertRaises(OperationError):
            validated(changed)
