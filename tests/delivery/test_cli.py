"""Offline CLI contracts exercised across real process/checkpoint boundaries."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from offmenu.delivery.engine import writer


class CliTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='offmenu-cli-test-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.git('init', '-q', '-b', 'feature/cli-test')
        self.git('config', 'user.name', 'CLI Test')
        self.git('config', 'user.email', 'cli@example.invalid')
        files = {
            '.gitignore': '.delivery/\ncounter.txt\n',
            'result.txt': 'accepted bytes\n',
            'package.json': '{}\n',
            'pyproject.toml': '[project]\nname = "cli-fixture"\n',
            'docs/standards/repository.md': 'Fixture standard\n',
        }
        policy = {'version': '1.1.0', 'legacy_paths': [],
                  'roots': {name.split('/')[0]: {} for name in files}}
        policy['roots']['repository-standard.json'] = {}
        files['repository-standard.json'] = json.dumps(policy)
        for name, content in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        self.git('add', '.')
        self.git('commit', '-qm', 'Offline CLI fixture')
        self.task = {
            'version': 1, 'id': 'cli-test', 'owner': 'cli-test-owner',
            'purpose': 'Verify CLI lifecycle offline',
            'base_revision': self.git('rev-parse', 'HEAD'),
            'checks': [{'id': 'counter', 'timeout': 10, 'argv': [
                sys.executable, '-c',
                "from pathlib import Path; p=Path('counter.txt'); "
                "p.write_text(str(int(p.read_text()) + 1) if p.exists() else '1')"]}],
            'accepted_outputs': {'result.txt': hashlib.sha256(
                (self.root / 'result.txt').read_bytes()).hexdigest()},
        }
        (self.root / '.delivery').mkdir()
        self.task_path = self.root / '.delivery' / 'task.json'
        self.save_task()
        source = Path(__file__).resolve().parents[2]
        self.env = {**os.environ, 'PYTHONPATH': str(source),
                    'LANGCHAIN_TRACING_V2': 'false', 'LANGSMITH_TRACING': 'false'}

    def git(self, *args):
        return subprocess.check_output(
            ['git', '-C', str(self.root), *args], text=True).strip()

    def save_task(self):
        self.task_path.write_text(json.dumps(self.task))

    def cli(self, *args, code=0):
        process = subprocess.run(
            [sys.executable, '-m', 'offmenu.delivery', '--root', str(self.root),
             *map(str, args)], cwd=self.root.parent, env=self.env,
            capture_output=True, text=True, timeout=30)
        self.assertEqual(process.returncode, code, process.stdout + process.stderr)
        self.assertEqual(process.stderr, '')
        result = json.loads(process.stdout)
        self.assertIsInstance(result, dict)
        return result

    def receipt(self, name):
        return self.root / '.delivery' / self.task['id'] / name

    def assert_blocked(self, *args, reason):
        result = self.cli(*args, code=2)
        self.assertEqual(result['status'], 'blocked')
        self.assertIn(reason, result['reason'])

    def uncertain_receipt(self):
        self.cli('run', self.task_path, '--pause-after', 'standards')
        record = {'status': 'running', 'attempt': 1, 'argv_sha256': 'fixture'}
        self.receipt('counter.json').write_text(json.dumps(record))
        evidence = self.root / '.delivery' / 'evidence.json'
        evidence.write_text(json.dumps({'observer': 'offline-test',
                                       'reason': 'Synthetic stopped process',
                                       'process_tree_gone': True}))
        return evidence

    def test_discover_and_check_use_selected_root_and_report_violations(self):
        result = self.cli('discover')
        self.assertEqual(result['revision'], self.task['base_revision'])
        self.assertEqual(result['branch'], 'feature/cli-test')
        self.assertEqual(result['untracked_count'], 0)
        self.assertEqual(result['manifests']['package.json'], hashlib.sha256(
            (self.root / 'package.json').read_bytes()).hexdigest())
        self.assertEqual(self.cli('check')['status'], 'passed')
        (self.root / 'BadName.py').write_text('')
        result = self.cli('check', code=1)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['standard_version'], '1.1.0')
        self.assertEqual({error['rule'] for error in result['errors']},
                         {'filename', 'unclassified-root'})

    def test_prepare_records_reviewable_task_and_refuses_overwrite(self):
        result = self.cli('prepare', '--task-id', 'review-task', '--owner', 'reviewer')
        self.assertEqual(result['status'], 'prepared_for_review')
        path = Path(result['task'])
        self.assertEqual(path, self.root / '.delivery' / 'review-task.json')
        original = path.read_bytes()
        task = json.loads(original)
        self.assertEqual(task['base_revision'], self.task['base_revision'])
        self.assertEqual(task['owner'], 'reviewer')
        self.assertEqual(task['branch'], 'feature/cli-test')
        self.assertEqual(task['checks'][0]['argv'], [sys.executable, '-m',
                         'unittest', 'discover', '-s', 'tests/delivery', '-v'])
        self.assertEqual(set(task['accepted_outputs']), {
            'repository-standard.json', 'package.json', 'pyproject.toml',
            'docs/standards/repository.md'})
        for name, expected in task['accepted_outputs'].items():
            self.assertEqual(expected, hashlib.sha256((self.root / name).read_bytes()).hexdigest())
        self.assertFalse((self.root / '.delivery' / 'review-task').exists())
        self.assert_blocked('prepare', '--task-id', 'review-task', '--owner', 'other',
                            reason='Task already exists')
        self.assertEqual(path.read_bytes(), original)

    def test_prepare_rejects_invalid_id_before_creating_task(self):
        self.assert_blocked('prepare', '--task-id', '../escape', '--owner', 'reviewer',
                            reason='Invalid task ID')
        self.assertEqual(list((self.root / '.delivery').iterdir()), [self.task_path])

    def test_status_and_cancel_of_unknown_task_do_not_create_run(self):
        self.assertEqual(self.cli('status', self.task_path),
                         {'status': 'not_found', 'task_id': self.task['id']})
        self.assert_blocked('cancel', self.task_path, reason='Task not found')
        self.assertFalse(self.receipt('binding.json').exists())

    def test_pause_resume_and_status_survive_process_exit_without_replay(self):
        paused = self.cli('run', self.task_path, '--pause-after', 'execute')
        self.assertEqual(paused['status'], 'checked')
        self.assertEqual(paused['next'], ['verify'])
        self.assertTrue(self.receipt('graph.sqlite').is_file())
        status = self.cli('status', self.task_path)
        self.assertEqual(status['status'], 'not_accepted')
        self.assertEqual(status['checks'][0]['status'], 'succeeded')
        self.assertEqual(status['checks'][0]['returncode'], 0)
        self.assertFalse(status['cancellation_requested'])
        self.assertEqual(self.cli('run', self.task_path)['status'], 'accepted')
        accepted = self.cli('status', self.task_path)
        self.assertEqual(accepted['outputs'], self.task['accepted_outputs'])
        self.assertEqual(accepted['owner'], self.task['owner'])
        self.assertEqual(accepted['revision'], self.task['base_revision'])
        self.assertEqual(self.cli('run', self.task_path), accepted)
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')
        (self.root / 'result.txt').write_text('changed after acceptance')
        self.assertEqual(self.cli('status', self.task_path), accepted)
        self.assert_blocked('run', self.task_path, reason='hash mismatch')
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')

    def test_cancel_bypasses_writer_lock_and_prevents_resume(self):
        self.cli('run', self.task_path, '--pause-after', 'standards')
        with writer(self.root):
            self.assertEqual(self.cli('cancel', self.task_path), {
                'status': 'cancellation_requested', 'task_id': self.task['id']})
            self.assertTrue(self.cli('status', self.task_path)['cancellation_requested'])
        self.assert_blocked('run', self.task_path, reason='cancelled')
        self.assertFalse((self.root / 'counter.txt').exists())
        self.assertFalse(self.receipt('accepted.json').exists())

    def test_changed_task_cannot_read_cancel_or_resume_original_binding(self):
        self.cli('run', self.task_path, '--pause-after', 'standards')
        self.task['owner'] = 'different-owner'
        self.save_task()
        for action in ('status', 'cancel', 'run'):
            with self.subTest(action=action):
                self.assert_blocked(action, self.task_path,
                                    reason='already bound' if action == 'run' else 'binding mismatch')
        self.assertFalse(self.receipt('cancel.json').exists())
        self.assertFalse((self.root / 'counter.txt').exists())

    def test_failed_command_reports_blocked_and_cannot_spend_another_attempt(self):
        self.task['checks'][0]['argv'] = [sys.executable, '-c', 'raise SystemExit(7)']
        self.save_task()
        self.assert_blocked('run', self.task_path, reason='Check failed')
        record = self.cli('status', self.task_path)['checks'][0]
        self.assertEqual((record['status'], record['returncode'], record['attempt']),
                         ('failed', 7, 1))
        self.assert_blocked('run', self.task_path, reason='attempts exhausted')
        self.assertEqual(self.cli('status', self.task_path)['checks'][0], record)
        self.assertFalse(self.receipt('accepted.json').exists())

    def test_reconcile_requires_evidence_and_does_not_replay_exhausted_check(self):
        evidence = self.uncertain_receipt()
        self.assert_blocked('run', self.task_path, reason='blocked_reconciliation')
        evidence.write_text(json.dumps({'observer': 'test', 'reason': 'not proven',
                                       'process_tree_gone': False}))
        args = ('reconcile', self.task_path, '--check-id', 'counter',
                '--outcome', 'failed', '--evidence', evidence)
        self.assert_blocked(*args, reason='Evidence requires')
        self.assertEqual(json.loads(self.receipt('counter.json').read_text())['status'], 'running')
        evidence.write_text(json.dumps({'observer': 'test', 'reason': 'inspected',
                                       'process_tree_gone': True}))
        self.assertEqual(self.cli(*args), {
            'status': 'reconciled', 'check': 'counter', 'outcome': 'failed'})
        record = json.loads(self.receipt('counter.json').read_text())
        self.assertTrue(record['reconciled'])
        self.assertEqual(record['status'], 'failed')
        self.assert_blocked('run', self.task_path, reason='attempts exhausted')
        self.assert_blocked(*args, reason='Only uncertain outcomes')
        self.assertFalse((self.root / 'counter.txt').exists())

    def test_successful_reconciliation_requires_output_proof(self):
        evidence = self.uncertain_receipt()
        args = ('reconcile', self.task_path, '--check-id', 'counter',
                '--outcome', 'succeeded', '--evidence', evidence)
        (self.root / 'result.txt').write_text('unproven bytes')
        self.assert_blocked(*args, reason='hash mismatch')
        self.assertEqual(json.loads(self.receipt('counter.json').read_text())['status'], 'running')
        (self.root / 'result.txt').write_text('accepted bytes\n')
        self.assertEqual(self.cli(*args)['outcome'], 'succeeded')
        self.assertEqual(self.cli('run', self.task_path)['status'], 'accepted')
        self.assertFalse((self.root / 'counter.txt').exists())

    def test_invalid_task_is_blocked_before_run_directory_creation(self):
        self.task['checks'][0]['attempts'] = 2
        self.save_task()
        self.assert_blocked('run', self.task_path, reason='retry_safe')
        self.assertFalse(self.receipt('binding.json').exists())

    def test_retry_safe_failure_can_succeed_without_replaying_on_reentry(self):
        step = self.task['checks'][0]
        step.update(attempts=2, retry_safe=True)
        step['argv'][2] += "; raise SystemExit(7 if p.read_text() == '1' else 0)"
        self.save_task()
        self.assertEqual(self.cli('run', self.task_path)['status'], 'accepted')
        record = json.loads(self.receipt('counter.json').read_text())
        self.assertEqual((record['status'], record['returncode'], record['attempt']),
                         ('succeeded', 0, 2))
        events = [json.loads(path.read_text())
                  for path in self.receipt('binding.json').parent.glob('event-*.json')]
        self.assertEqual(sorted(event['attempt'] for event in events
                                if event['event'] == 'check-started'), [1, 2])
        accepted = self.cli('status', self.task_path)
        self.assertEqual(self.cli('run', self.task_path), accepted)
        self.assertEqual((self.root / 'counter.txt').read_text(), '2')
        self.assertEqual(json.loads(self.receipt('counter.json').read_text()), record)

    def test_timeout_holds_all_writers_until_reconciled_then_uses_safe_retry(self):
        step = self.task['checks'][0]
        step.update(timeout=1, attempts=2, retry_safe=True)
        step['argv'][2] += "; import time; time.sleep(10 if p.read_text() == '1' else 0)"
        self.save_task()
        self.assert_blocked('run', self.task_path, reason='timed_out')
        record = self.cli('status', self.task_path)['checks'][0]
        self.assertEqual((record['status'], record['attempt']), ('timed_out', 1))
        self.assertNotEqual(record['returncode'], 0)
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')

        other_path = self.root / '.delivery' / 'other.json'
        other_path.write_text(json.dumps({**self.task, 'id': 'other-task'}))
        for path in (self.task_path, other_path):
            with self.subTest(task=path.name):
                self.assert_blocked('run', path, reason='blocked_reconciliation')
        self.assert_blocked('prepare', '--task-id', 'review-task', '--owner', 'reviewer',
                            reason='blocked_reconciliation')
        self.assertFalse((self.root / '.delivery' / 'other-task').exists())
        self.assertFalse((self.root / '.delivery' / 'review-task.json').exists())
        self.assertEqual(self.cli('status', self.task_path)['checks'][0], record)
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')

        evidence = self.root / '.delivery' / 'timeout-evidence.json'
        evidence.write_text(json.dumps({
            'observer': 'offline-test', 'reason': 'Local timeout receipt after child reap',
            'process_tree_gone': True}))
        self.assertEqual(self.cli('reconcile', self.task_path, '--check-id', 'counter',
                                 '--outcome', 'failed', '--evidence', evidence), {
            'status': 'reconciled', 'check': 'counter', 'outcome': 'failed'})
        self.assertEqual(self.cli('run', self.task_path)['status'], 'accepted')
        final = json.loads(self.receipt('counter.json').read_text())
        self.assertEqual((final['status'], final['attempt']), ('succeeded', 2))
        self.cli('run', self.task_path)
        self.assertEqual((self.root / 'counter.txt').read_text(), '2')

    def test_writer_contention_blocks_run_and_prepare_without_binding_tasks(self):
        with writer(self.root):
            self.assert_blocked('run', self.task_path, reason='busy')
            self.assert_blocked('prepare', '--task-id', 'review-task', '--owner', 'reviewer',
                                reason='busy')
            self.assertEqual(self.cli('status', self.task_path)['status'], 'not_found')
            self.assertFalse(self.receipt('binding.json').parent.exists())
            self.assertFalse((self.root / '.delivery' / 'review-task.json').exists())
            self.assertFalse((self.root / 'counter.txt').exists())
        self.assertEqual(self.cli('run', self.task_path)['status'], 'accepted')
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')

    def test_source_drift_blocks_cross_process_resume_without_replaying_checks(self):
        self.cli('run', self.task_path, '--pause-after', 'execute')
        binding = self.receipt('binding.json').read_bytes()
        record = self.receipt('counter.json').read_bytes()
        source = self.root / 'package.json'
        original = source.read_bytes()
        source.write_text('{"changed": true}\n')
        self.assert_blocked('run', self.task_path, reason='already bound')
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.task['base_revision'])
        self.assertEqual(self.receipt('binding.json').read_bytes(), binding)
        self.assertEqual(self.receipt('counter.json').read_bytes(), record)
        self.assertFalse(self.receipt('accepted.json').exists())
        source.write_bytes(original)
        self.assertEqual(self.cli('run', self.task_path)['status'], 'accepted')
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')

    def test_accept_revalidates_outputs_after_verify_process_exits(self):
        paused = self.cli('run', self.task_path, '--pause-after', 'verify')
        self.assertEqual(paused['next'], ['accept'])
        self.assertFalse(self.receipt('accepted.json').exists())
        (self.root / 'result.txt').write_text('changed after verification\n')
        self.assert_blocked('run', self.task_path, reason='hash mismatch')
        self.assertFalse(self.receipt('accepted.json').exists())
        self.assertEqual(self.cli('status', self.task_path)['status'], 'not_accepted')
        (self.root / 'result.txt').write_text('accepted bytes\n')
        self.assertEqual(self.cli('run', self.task_path)['status'], 'accepted')
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')

    def test_checked_output_cannot_be_replaced_before_cross_process_acceptance(self):
        (self.root / 'result.txt').write_text('wrong bytes seen by command\n')
        self.task['checks'][0]['argv'][2] += "; print(Path('result.txt').read_text())"
        self.save_task()
        self.cli('run', self.task_path, '--pause-after', 'execute')
        (self.root / 'result.txt').write_text('accepted bytes\n')
        self.assert_blocked('run', self.task_path, reason='cached check evidence differs')
        self.assertFalse(self.receipt('accepted.json').exists())
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')

    def test_output_drift_consumes_only_declared_safe_recheck_budget(self):
        (self.root / 'result.txt').write_text('wrong bytes seen by command\n')
        self.task['checks'][0].update(attempts=2, retry_safe=True)
        self.task['checks'][0]['argv'][2] += "; print(Path('result.txt').read_text())"
        self.save_task()
        self.cli('run', self.task_path, '--pause-after', 'execute')
        (self.root / 'result.txt').write_text('accepted bytes\n')
        self.assertEqual(self.cli('run', self.task_path)['status'], 'accepted')
        self.assertEqual((self.root / 'counter.txt').read_text(), '2')
        receipt = json.loads(self.receipt('counter.json').read_text())
        self.assertEqual(receipt['attempt'], 2)
        self.assertEqual(receipt['output_state'], self.task['accepted_outputs'])
        self.assertIn('accepted bytes', self.receipt('counter-2.log').read_text())
        self.cli('run', self.task_path)
        self.assertEqual((self.root / 'counter.txt').read_text(), '2')

    def test_same_head_other_branch_cannot_resume_or_reuse_acceptance(self):
        self.cli('run', self.task_path, '--pause-after', 'execute')
        self.git('switch', '-qc', 'feature/other-cli')
        self.assert_blocked('run', self.task_path, reason='already bound')
        self.assertFalse(self.receipt('accepted.json').exists())
        self.git('switch', '-q', 'feature/cli-test')
        self.assertEqual(self.cli('run', self.task_path)['status'], 'accepted')
        accepted = self.cli('status', self.task_path)
        self.assertEqual(accepted['branch'], 'feature/cli-test')
        self.git('switch', '-q', 'feature/other-cli')
        self.assert_blocked('run', self.task_path, reason='already bound')
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')


if __name__ == '__main__':
    unittest.main()
