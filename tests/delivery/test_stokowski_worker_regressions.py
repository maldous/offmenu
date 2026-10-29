"""Local restart and ownership checks: real Git/SQLite, no model or tracker calls."""
from contextlib import ExitStack, nullcontext
import asyncio
import copy
import json
import importlib.util
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

TOOLS = Path(__file__).resolve().parents[2] / 'tools/delivery'
sys.path.insert(0, str(TOOLS))
import stokowski_adapter as adapter
import stokowski_worker as worker
from symphony_capacity import AdmissionError, BRANCH, Pool, digest
from symphony_tasks import PROJECT_ID, runtime_lease_ids


class WorkerRegressions(unittest.TestCase):
    issue = 'UIF-92'

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.policy = json.loads((TOOLS / 'capacity-policy.json').read_text())
        self.policy['symphony']['pool_path'] = str(self.root / 'pool')
        # Use real host admission and leave the test process's affinity unchanged.
        self.policy['host'].update(cpu_reserve=0, memory_reserve_bytes=0,
                                   disk_reserve_bytes=0)
        self.policy['symphony']['cpu_budget_millis'] = len(os.sched_getaffinity(0)) * 1000
        self.proof = dict(route='codex-chatgpt', available=True,
                          checked_at=time.time(), session_ceiling=8)
        self.request = dict(prompt='Bounded offline test', timeout_seconds=5)
        self.runtime, self.manifest = self.make_runtime('run', 'tests/first.py')
        # These are the only execution/provider boundaries replaced in worker tests.
        self.provider = self.enterContext(patch.object(
            worker, 'isolated_codex_environment', side_effect=lambda *args: nullcontext({})))
        self.process = self.enterContext(patch.object(
            worker, 'supervise', side_effect=self.completed_process))

    def git(self, workspace, *args):
        # Ignore user Git configuration/hooks and supply only synthetic identity.
        environment = {'PATH': os.defpath, 'HOME': str(self.root),
                       'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
                       'GIT_AUTHOR_NAME': 'Regression', 'GIT_AUTHOR_EMAIL': 'test@example.invalid',
                       'GIT_COMMITTER_NAME': 'Regression',
                       'GIT_COMMITTER_EMAIL': 'test@example.invalid'}
        return subprocess.check_output(
            ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false',
             '-C', str(workspace), *args], env=environment, text=True,
            stderr=subprocess.PIPE).strip()

    def make_runtime(self, relative, allowed_path):
        runtime = self.root / relative
        workspace = runtime / 'workspaces' / self.issue
        workspace.mkdir(parents=True)
        self.git(workspace, 'init', '-b', BRANCH)
        (workspace / 'README.md').write_text('Offline source fixture\n')
        self.git(workspace, 'add', 'README.md')
        self.git(workspace, 'commit', '-m', 'Fixture')
        manifest = dict(version=1, branch=BRANCH,
                        base_revision=self.git(workspace, 'rev-parse', 'HEAD'),
                        project_id=PROJECT_ID, label='offline-regression', tasks={
            self.issue: dict(issue_id='00000000-0000-4000-8000-000000000092',
                             owner='test-owner', purpose='Offline regression',
                             allowed_paths=[allowed_path], acceptance=['Local checks'],
                             resources=dict(cpu_millis=1, memory_bytes=1024,
                                            io_slots=1, output_bytes=0), attempt_limit=1)})
        for name, value in [('manifest.json', manifest),
                            ('capacity-policy.json', self.policy),
                            ('provider-proof.json', self.proof)]:
            (runtime / name).write_text(json.dumps(value))
        return runtime, manifest

    def directory(self, runtime=None):
        return (runtime or self.runtime) / 'attempts' / self.issue

    def lease(self, runtime=None, manifest=None):
        return runtime_lease_ids(runtime or self.runtime, manifest or self.manifest)[self.issue]

    def pool(self):
        # Every observation reopens the actual durable database, as after restart.
        return Pool(self.policy['symphony']['pool_path'], self.policy)

    def rows(self):
        return {row['id']: row for row in self.pool().status()}

    def events(self):
        with sqlite3.connect(Path(self.policy['symphony']['pool_path']) / 'state.sqlite') as db:
            return db.execute('SELECT id,event FROM events ORDER BY sequence').fetchall()

    def admit(self, runtime=None, manifest=None, request=None):
        runtime = runtime or self.runtime
        manifest = manifest or self.manifest
        task = manifest['tasks'][self.issue]
        binding = dict(branch=manifest['branch'], head=manifest['base_revision'],
                       owner=task['owner'], write_roots=task['allowed_paths'],
                       resources=task['resources'], task_sha256=digest(dict(
                           runtime=str(runtime.resolve()), manifest=manifest,
                           request=request or self.request)))
        lease = self.lease(runtime, manifest)
        self.pool().admit(lease, binding, self.proof, worker.host_snapshot(runtime))
        directory = self.directory(runtime)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'intent.json').write_text(json.dumps(dict(lease=lease, binding=binding)))
        return lease

    @staticmethod
    def completed_process(command, prompt, workspace, environment, directory, *args):
        (directory / 'stdout.jsonl').write_text(
            json.dumps(dict(type='turn.completed', usage={'input_tokens': 3})) + '\n')
        return dict(status='succeeded', child_tree_gone=True, exit_code=0)

    def test_active_lease_and_intent_block_restart_without_changing_durable_state(self):
        lease = self.admit()
        before = self.events()
        intent = (self.directory() / 'intent.json').read_bytes()
        with self.assertRaisesRegex(AdmissionError, 'Existing resource lease'):
            worker.execute(self.runtime, self.issue, self.request)
        self.process.assert_not_called()
        self.provider.assert_not_called()
        self.assertEqual(self.rows()[lease]['status'], 'running')
        self.assertEqual(self.events(), before)
        self.assertEqual((self.directory() / 'intent.json').read_bytes(), intent)
        self.assertFalse((self.directory() / 'receipt.json').exists())

    def test_changed_request_cannot_rebind_an_existing_lease(self):
        lease = self.admit()
        before = self.rows()[lease]
        with self.assertRaisesRegex(AdmissionError, 'immutable_binding_conflict'):
            worker.execute(self.runtime, self.issue, dict(self.request, prompt='Different task'))
        self.process.assert_not_called()
        self.assertEqual(self.rows()[lease], before)

    def test_cancel_requested_lease_blocks_restart(self):
        lease = self.admit()
        self.pool().cancel(lease)
        with self.assertRaisesRegex(AdmissionError, 'reconcile_or_new_task_required'):
            worker.execute(self.runtime, self.issue, self.request)
        self.process.assert_not_called()
        self.assertEqual(self.rows()[lease]['status'], 'cancel_requested')

    def test_completed_receipt_blocks_replay_after_lease_release(self):
        first = worker.execute(self.runtime, self.issue, self.request)
        self.assertEqual(first['status'], 'succeeded')
        self.assertFalse(first['accepted_delivery'])
        self.assertEqual(self.rows()[self.lease()]['status'], 'finished')
        receipt = (self.directory() / 'receipt.json').read_bytes()
        before = self.events()
        self.process.reset_mock()
        with self.assertRaisesRegex(AdmissionError, 'no replay'):
            worker.execute(self.runtime, self.issue, self.request)
        self.process.assert_not_called()
        self.assertEqual((self.directory() / 'receipt.json').read_bytes(), receipt)
        self.assertEqual(self.events(), before)

    def test_uncertain_cleanup_retains_lease_and_blocks_replay(self):
        self.process.side_effect = None
        self.process.return_value = dict(status='uncertain', child_tree_gone=False)
        result = worker.execute(self.runtime, self.issue, self.request)
        self.assertFalse(result['child_tree_gone'])
        self.assertEqual(self.rows()[self.lease()]['status'], 'running')
        self.process.reset_mock()
        with self.assertRaisesRegex(AdmissionError, 'no replay'):
            worker.execute(self.runtime, self.issue, self.request)
        self.process.assert_not_called()
        self.assertEqual(self.rows()[self.lease()]['status'], 'running')

    def test_process_boundary_exception_persists_uncertainty_and_reservation(self):
        self.process.side_effect = OSError('synthetic process start failure')
        with self.assertRaisesRegex(OSError, 'synthetic process start failure'):
            worker.execute(self.runtime, self.issue, self.request)
        saved = json.loads((self.directory() / 'receipt.json').read_text())
        self.assertEqual(saved, dict(status='uncertain', child_tree_gone=False))
        self.assertEqual(self.rows()[self.lease()]['status'], 'running')
        self.process.reset_mock()
        with self.assertRaisesRegex(AdmissionError, 'no replay'):
            worker.execute(self.runtime, self.issue, self.request)
        self.process.assert_not_called()

    def test_intent_without_pool_record_must_not_start_another_process(self):
        self.admit()
        intent = (self.directory() / 'intent.json').read_bytes()
        # Simulate an intact runtime recovered with a fresh/lost pool database.
        self.policy['symphony']['pool_path'] = str(self.root / 'recovered-pool')
        (self.runtime / 'capacity-policy.json').write_text(json.dumps(self.policy))
        with self.assertRaises(AdmissionError):
            worker.execute(self.runtime, self.issue, self.request)
        self.process.assert_not_called()
        self.assertEqual((self.directory() / 'intent.json').read_bytes(), intent)

    def test_finishing_runtime_cannot_release_prefix_or_same_basename_lease(self):
        for relative in ('run-other', 'another-parent/run'):
            with self.subTest(runtime=relative):
                other, manifest = self.make_runtime(relative, 'tests/' + relative + '.py')
                lease = self.admit(other, manifest)
                before = self.rows()[lease]
                # A fresh runtime finishes while the other runtime remains active.
                if relative == 'run-other':
                    selected, selected_manifest = self.runtime, self.manifest
                else:
                    selected, selected_manifest = self.make_runtime(
                        'first-parent/run', 'tests/selected.py')
                result = worker.execute(selected, self.issue, self.request)
                self.assertEqual(result['status'], 'succeeded')
                self.assertEqual(self.rows()[self.lease(selected, selected_manifest)]['status'], 'finished')
                self.assertEqual(self.rows()[lease], before)
                self.assertEqual([event for event in self.events() if event[0] == lease],
                                 [(lease, 'admitted')])
                # Its ownership remains enforced, not merely its status string.
                conflict = copy.deepcopy(before['binding'])
                conflict['task_sha256'] = digest('competing task ' + relative)
                with self.assertRaisesRegex(AdmissionError, 'ownership_conflict'):
                    self.pool().admit('competitor-' + str(len(self.rows())), conflict,
                                      self.proof, worker.host_snapshot(other))

    def test_wrong_branch_fails_before_admission_or_coding(self):
        workspace = self.runtime / 'workspaces' / self.issue
        self.git(workspace, 'switch', '-c', 'feature/unreviewed')
        self.assert_source_rejected()

    def test_changed_head_fails_before_admission_or_coding(self):
        workspace = self.runtime / 'workspaces' / self.issue
        self.git(workspace, 'commit', '--allow-empty', '-m', 'Unselected revision')
        self.assert_source_rejected()

    def assert_source_rejected(self):
        with self.assertRaisesRegex(AdmissionError, 'Source identity changed'):
            worker.execute(self.runtime, self.issue, self.request)
        self.provider.assert_not_called()
        self.process.assert_not_called()
        self.assertFalse(self.directory().exists())
        self.assertFalse(Path(self.policy['symphony']['pool_path']).exists())


@unittest.skipUnless(importlib.util.find_spec('stokowski'), 'Run native adapter checks in the pinned Stokowski environment')
class AdapterModelGuard(unittest.TestCase):
    def test_unreviewed_model_or_runner_fails_before_request_or_worker_spawn(self):
        import stokowski.config as config
        import stokowski.linear as linear
        import stokowski.orchestrator as orchestration
        import stokowski.workspace as workspace

        # Restore every upstream adaptation after exercising the real run_turn closure.
        targets = [(config.ProjectConfig, 'agent_env'), (config.ServiceConfig, 'agent_env'),
                   (config.ProjectConfig, 'resolved_api_key'), (config.ServiceConfig, 'resolved_api_key'),
                   (workspace, 'run_hook'), (linear.LinearClient, 'fetch_candidate_issues'),
                   (orchestration, 'ensure_workspace'), (orchestration, 'remove_workspace'),
                   (workspace, 'ensure_workspace'), (workspace, 'remove_workspace'),
                   (orchestration.Orchestrator, 'stop'),
                   (orchestration.Orchestrator, 'start'),
                   (orchestration.Orchestrator, '_safe_transition'),
                   (orchestration.Orchestrator, '_publish_run_report'), (orchestration, 'run_turn')]
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            for owner, name in targets:
                stack.enter_context(patch.object(owner, name, getattr(owner, name)))
            spawn = stack.enter_context(patch.object(
                adapter.asyncio, 'create_subprocess_exec', new_callable=AsyncMock))
            runtime = Path(temporary)
            adapted = adapter.install_adapters(runtime, {'tasks': {}}, 'synthetic-key')
            for runner, model in [('codex', 'unapproved-model'), ('claude', worker.MODEL)]:
                with self.subTest(runner=runner, model=model):
                    attempt = SimpleNamespace(turn_count=0)
                    with self.assertRaisesRegex(AdmissionError, 'reviewed existing Codex'):
                        asyncio.run(adapted.run_turn(
                            runner, SimpleNamespace(model=model), SimpleNamespace(),
                            'Offline prompt', runtime, SimpleNamespace(identifier='UIF-92'), attempt))
                    self.assertEqual(attempt.turn_count, 0)
                    self.assertEqual(list(runtime.iterdir()), [])
            spawn.assert_not_called()


if __name__ == '__main__':
    unittest.main()
