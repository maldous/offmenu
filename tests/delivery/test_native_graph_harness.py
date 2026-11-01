"""Native finite-graph recovery against UIF-122's actual shared contract."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

from native_harness_contract import ContractError, fingerprint, load_release_policy
from offmenu.delivery.engine import DeliveryError, Engine, writer
from test_engine import DeliveryFixture


class NativeGraphTests(DeliveryFixture):
    def setUp(self):
        super().setUp()
        source = Path(__file__).resolve().parents[2]
        policy_path = self.root / 'config/delivery-release-policy.json'
        policy_path.parent.mkdir()
        policy_path.write_bytes((source / 'config/delivery-release-policy.json').read_bytes())
        standard_path = self.root / 'repository-standard.json'
        standard = json.loads(standard_path.read_text())
        standard['roots']['config'] = {}
        standard_path.write_text(json.dumps(standard))
        self.git('add', '.')
        self.git('commit', '-qm', 'Native policy fixture')
        self.task['base_revision'] = self.git('rev-parse', 'HEAD')
        self.policy = load_release_policy(policy_path)
        self.ref = {'path': '.delivery/original-evidence.json', 'sha256': 'a' * 64}
        self.task['handoff'] = {
            'version': 1, 'kind': 'delivery-handoff-v1',
            'issue_id': '11111111-1111-4111-8111-111111111111',
            'project_id': '22222222-2222-4222-8222-222222222222',
            'owner': self.task['owner'],
            'origin': {'kind': 'reviewed-source-v1', 'evidence': self.ref},
            'source': self.source(), 'outputs': self.outputs(), 'evidence': [self.ref],
        }

    def source(self, branch='feature/test', target='develop'):
        return {'repository': 'maldous/offmenu', 'branch': branch,
                'base': self.task['base_revision'], 'head': self.task['base_revision'],
                'tree': self.git('rev-parse', 'HEAD^{tree}'), 'target': target,
                'policy_sha256': fingerprint(self.policy)}

    def outputs(self):
        return [{'path': name, 'sha256': sha} for name, sha in self.task['accepted_outputs'].items()]

    def release_task(self):
        self.git('switch', '-qc', 'develop')
        self.task.pop('handoff')
        self.task['branch'] = 'develop'
        self.task['release_candidate'] = {
            'version': 1, 'kind': 'release-candidate-v1',
            'source': self.source('develop', 'main'),
            'required_profiles': ['unit'], 'artifacts': self.outputs(),
        }

    def test_shared_handoff_reopens_checkpoint_without_command_replay(self):
        first = self.run_engine('execute')
        self.assertEqual(first['native_harness']['target'], 'develop')
        result = self.run_engine()
        self.assertEqual(result['status'], 'accepted')
        again = self.run_engine()
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')
        self.assertEqual(again['native_harness']['handoff_sha256'], fingerprint(self.task['handoff']))
        self.assertEqual(again['native_harness']['accepted_outputs'], self.task['accepted_outputs'])
        self.assertNotIn('attempt', self.task['handoff'])

    def test_candidate_identity_and_release_target_survive_cli_reopen(self):
        self.release_task()
        directory = self.root / '.delivery'
        directory.mkdir()
        task_path = directory / 'task.json'
        task_path.write_text(json.dumps(self.task))
        env = {**os.environ, 'LANGCHAIN_TRACING_V2': 'false', 'LANGSMITH_TRACING': 'false'}
        argv = [sys.executable, '-m', 'offmenu.delivery', '--root', str(self.root), 'run', str(task_path)]
        first = subprocess.run([*argv, '--pause-after', 'execute'], env=env, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        resumed = subprocess.run(argv, env=env, capture_output=True, text=True)
        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        facts = json.loads(resumed.stdout)['native_harness']
        self.assertEqual(facts['candidate_sha256'], fingerprint(self.task['release_candidate']))
        self.assertEqual(facts['target'], 'main')
        self.assertEqual(facts['accepted_outputs'], self.task['accepted_outputs'])
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')

    def test_candidate_cannot_follow_advancing_develop_or_reset_budget(self):
        self.release_task()
        self.run_engine('execute')
        self.git('commit', '--allow-empty', '-qm', 'Develop advanced')
        with self.assertRaisesRegex(DeliveryError, 'Revision changed'):
            self.run_engine()
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')

    def test_handoff_output_mismatch_rejected_before_execution(self):
        self.task['handoff']['outputs'][0]['sha256'] = 'f' * 64
        with self.assertRaisesRegex(DeliveryError, 'outputs differ'):
            self.run_engine()
        self.assertFalse((self.root / 'counter.txt').exists())

    def test_handoff_source_tree_mismatch_rejected(self):
        self.task['handoff']['source']['tree'] = 'f' * 40
        with self.assertRaisesRegex(DeliveryError, 'source differs'):
            self.run_engine()

    def test_uncommitted_input_cannot_claim_committed_source_tree(self):
        (self.root / 'input.txt').write_text('uncommitted source')
        with self.assertRaisesRegex(DeliveryError, 'uncommitted input'):
            self.run_engine()

    def test_policy_drift_rejected_by_shared_validator(self):
        self.task['handoff']['source']['policy_sha256'] = 'f' * 64
        with self.assertRaises(ContractError):
            self.run_engine()

    def test_explicit_null_handoff_is_not_silently_treated_as_legacy(self):
        self.task['handoff'] = None
        with self.assertRaises(ContractError):
            self.run_engine()
        self.assertFalse((self.root / 'counter.txt').exists())

    def test_unknown_external_effect_retains_operation_owner_and_no_execution(self):
        handoff = self.task['handoff']
        handoff['operation'] = {
            'id': 'original-operation', 'backend': 'windmill', 'job_id': 'original-job',
            'status': 'unknown', 'command_sha256': 'b' * 64,
            'runner_sha256': 'c' * 64, 'policy_sha256': 'd' * 64, 'receipt': self.ref,
        }
        handoff['effect'] = {'operation_id': 'original-operation', 'status': 'unknown'}
        original = copy.deepcopy(handoff)
        for _ in range(2):
            with self.assertRaisesRegex(DeliveryError, 'blocked_reconciliation'):
                self.run_engine()
        self.assertEqual(handoff, original)
        self.assertFalse((self.root / 'counter.txt').exists())
        self.assertFalse(self.record('accepted.json').exists())

    def test_checkpoint_resume_rejects_handoff_change_without_command_replay(self):
        self.run_engine('execute')
        self.task['handoff']['evidence'][0] = {'path': '.delivery/different.json', 'sha256': 'f' * 64}
        with self.assertRaisesRegex(DeliveryError, 'already bound'):
            self.run_engine()
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')

    def test_candidate_artifacts_must_match_graph_accepted_outputs(self):
        self.release_task()
        self.task['release_candidate']['artifacts'][0]['sha256'] = 'f' * 64
        with self.assertRaisesRegex(DeliveryError, 'artifacts differ'):
            self.run_engine()
