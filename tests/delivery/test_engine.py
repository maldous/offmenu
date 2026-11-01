"""Contract tests for durable delivery, not a live Windmill deployment."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from offmenu.delivery.engine import (
    DeliveryError, Engine, atomic, load_task, verify_outputs, writer,
)


class DeliveryFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='offmenu-delivery-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.git('init', '-q', '-b', 'feature/test')
        self.git('config', 'user.name', 'Delivery Test')
        self.git('config', 'user.email', 'delivery-test@example.invalid')
        (self.root / '.gitignore').write_text('.delivery/\ncounter.txt\n')
        (self.root / 'result.txt').write_text('accepted bytes\n')
        policy = {'version': '1.0.0', 'roots': {
            '.gitignore': {}, 'repository-standard.json': {}, 'result.txt': {}},
            'legacy_paths': []}
        (self.root / 'repository-standard.json').write_text(json.dumps(policy))
        self.git('add', '.gitignore', 'repository-standard.json', 'result.txt')
        self.git('commit', '-qm', 'Fixture')
        self.task = {'version': 1, 'id': 'durable-test', 'owner': 'test-owner',
                     'purpose': 'Verify durable execution with explicit outputs',
                     'base_revision': self.git('rev-parse', 'HEAD'),
                     'checks': [{'id': 'counter', 'argv': [sys.executable, '-c',
                        "from pathlib import Path; p=Path('counter.txt'); p.write_text(str(int(p.read_text())+1) if p.exists() else '1')"],
                        'timeout': 10}],
                     'accepted_outputs': {'result.txt': hashlib.sha256(b'accepted bytes\n').hexdigest()}}

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True).strip()

    def run_engine(self, pause_after=None, task=None):
        with writer(self.root) as directory:
            return Engine(self.root, directory, task or self.task).run(pause_after)

    def record(self, name='counter.json'):
        return self.root / '.delivery' / self.task['id'] / name


class EngineTests(DeliveryFixture):
    def test_caller_cannot_enlarge_open_engines_attempt_budget(self):
        self.task['checks'][0]['argv'] = [sys.executable, '-c', 'raise SystemExit(7)']
        with writer(self.root) as directory:
            engine = Engine(self.root, directory, self.task)
            self.task['checks'][0].update(attempts=3, retry_safe=True)
            with self.assertRaisesRegex(DeliveryError, 'failed'):
                engine.execute({})
            self.assertEqual(json.loads(self.record().read_text())['attempt'], 1)
            with self.assertRaisesRegex(DeliveryError, 'exhausted'):
                engine.execute({})
            engine.task['checks'][0].update(attempts=3, retry_safe=True)
            with self.assertRaisesRegex(DeliveryError, 'Task binding changed'):
                engine.execute({})

    def test_reopen_cannot_enlarge_original_attempt_budget(self):
        self.task['checks'][0]['argv'] = [sys.executable, '-c', 'raise SystemExit(7)']
        with self.assertRaisesRegex(DeliveryError, 'failed'):
            self.run_engine()
        changed = copy.deepcopy(self.task)
        changed['checks'][0].update(attempts=3, retry_safe=True)
        with self.assertRaisesRegex(DeliveryError, 'already bound'):
            self.run_engine(task=changed)
        self.assertEqual(json.loads(self.record().read_text())['attempt'], 1)

    def test_failure_after_completed_command_before_graph_checkpoint_does_not_replay(self):
        from unittest.mock import patch
        original = Engine.execute

        def interrupted(engine, state):
            original(engine, state)
            raise RuntimeError('lost graph checkpoint after command receipt')

        with patch.object(Engine, 'execute', interrupted):
            with self.assertRaisesRegex(RuntimeError, 'lost graph checkpoint'):
                self.run_engine()
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')
        self.assertEqual(self.run_engine()['status'], 'accepted')
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')

    def test_invalid_pause_boundary_does_not_execute(self):
        with self.assertRaisesRegex(DeliveryError, 'Invalid graph pause'):
            self.run_engine('unknown-boundary')
        self.assertFalse((self.root / 'counter.txt').exists())

    def test_durable_resume_uses_new_engine_and_does_not_reexecute(self):
        paused = self.run_engine('execute')
        self.assertEqual(paused['status'], 'checked')
        self.assertEqual(paused['next'], ['verify'])
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')
        accepted = self.run_engine()
        self.assertEqual(accepted['status'], 'accepted')
        again = self.run_engine()
        self.assertEqual(again['status'], 'accepted')
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')
        receipt = json.loads(self.record('accepted.json').read_text())
        self.assertEqual(receipt['outputs'], self.task['accepted_outputs'])
        self.assertEqual(receipt['owner'], 'test-owner')

    def test_accepted_outputs_are_reverified_on_reentry(self):
        self.run_engine()
        (self.root / 'result.txt').write_text('tampered')
        with self.assertRaisesRegex(DeliveryError, 'hash mismatch'):
            self.run_engine()

    def test_accepted_receipt_rejects_head_drift_without_reexecuting(self):
        self.run_engine()
        self.git('commit', '--allow-empty', '-qm', 'Different immutable revision')
        self.assertNotEqual(self.git('rev-parse', 'HEAD'), self.task['base_revision'])
        with self.assertRaisesRegex(DeliveryError, 'Revision changed'):
            self.run_engine()
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')

    def test_dirty_source_blocks_cached_checks_at_same_head(self):
        with writer(self.root) as directory:
            engine = Engine(self.root, directory, self.task)
            engine.run('execute')
            original_head = self.git('rev-parse', 'HEAD')
            with (self.root / '.gitignore').open('a') as stream:
                stream.write('additional-runtime-file\n')
            self.assertEqual(self.git('rev-parse', 'HEAD'), original_head)
            with self.assertRaisesRegex(DeliveryError, 'Source changed'):
                engine.run()
            # A fresh process/Engine cannot silently rebind the same task ID.
            with self.assertRaisesRegex(DeliveryError, 'already bound'):
                Engine(self.root, directory, self.task)
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')
        self.assertFalse(self.record('accepted.json').exists())

    def test_accepted_receipt_requires_feature_or_bugfix_branch(self):
        self.run_engine()
        self.git('switch', '-qc', 'develop')
        with self.assertRaisesRegex(DeliveryError, 'feature/ or bugfix/'):
            self.run_engine()
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')

    def test_process_output_is_drained_but_log_is_bounded(self):
        self.task['checks'][0]['argv'] = [sys.executable, '-c',
            "import sys; sys.stdout.buffer.write(b'x' * (2 * 1048576))"]
        with writer(self.root) as directory:
            engine = Engine(self.root, directory, self.task)
            result = engine.execute({})
            record = result['checks']['counter']
            log = engine.directory / 'counter-1.log'
            self.assertEqual(record['status'], 'succeeded')
            self.assertTrue(record['log_truncated'])
            self.assertEqual(log.stat().st_size, 1048576)
            self.assertEqual(record['log_sha256'], hashlib.sha256(log.read_bytes()).hexdigest())

    def test_output_symlink_cannot_escape_checkout(self):
        outside = self.root.parent / (self.root.name + '-outside.txt')
        outside.write_text('accepted bytes\n')
        self.addCleanup(outside.unlink)
        (self.root / 'result.txt').unlink()
        (self.root / 'result.txt').symlink_to(outside)
        with self.assertRaisesRegex(DeliveryError, 'outside checkout'):
            verify_outputs(self.root, self.task)

    def test_accept_rechecks_outputs_after_verify_checkpoint(self):
        self.run_engine('verify')
        (self.root / 'result.txt').write_text('changed after verification')
        with self.assertRaisesRegex(DeliveryError, 'hash mismatch'):
            self.run_engine()
        self.assertFalse(self.record('accepted.json').exists())

    def test_unresolved_command_blocks_other_task_admission(self):
        with writer(self.root) as directory:
            engine = Engine(self.root, directory, self.task)
            atomic(engine.directory / 'counter.json', {
                'status': 'running', 'attempt': 1, 'argv_sha256': 'known-command'})
        with self.assertRaisesRegex(DeliveryError, 'blocked_reconciliation'):
            with writer(self.root):
                self.fail('admitted writer despite unresolved prior command')
        with writer(self.root, reconciliation=True):
            record = json.loads(self.record().read_text())
            record['status'] = 'failed'
            atomic(self.record(), record)
        with writer(self.root):
            pass

    def test_same_id_cannot_change_owner_or_input(self):
        with writer(self.root) as directory:
            Engine(self.root, directory, self.task)
            changed = copy.deepcopy(self.task)
            changed['owner'] = 'different-owner'
            with self.assertRaisesRegex(DeliveryError, 'already bound'):
                Engine(self.root, directory, changed)

    def test_running_receipt_blocks_replay_after_uncertain_shutdown(self):
        with writer(self.root) as directory:
            engine = Engine(self.root, directory, self.task)
            atomic(engine.directory / 'counter.json', {'status': 'running', 'attempt': 1})
            with self.assertRaisesRegex(DeliveryError, 'blocked_reconciliation'):
                engine.execute({})
        self.assertFalse((self.root / 'counter.txt').exists())

    def test_timeout_is_uncertain_and_is_not_retried(self):
        step = self.task['checks'][0]
        step.update(argv=[sys.executable, '-c', 'import time; time.sleep(5)'],
                    timeout=1, attempts=3, retry_safe=True)
        with writer(self.root) as directory:
            engine = Engine(self.root, directory, self.task)
            with self.assertRaisesRegex(DeliveryError, 'timed_out'):
                engine.execute({})
            record = json.loads((engine.directory / 'counter.json').read_text())
            self.assertEqual(record['status'], 'timed_out')
            self.assertEqual(record['attempt'], 1)
            with self.assertRaisesRegex(DeliveryError, 'blocked_reconciliation'):
                engine.execute({})

    def test_failed_retry_safe_checks_obey_attempt_budget(self):
        step = self.task['checks'][0]
        step.update(argv=[sys.executable, '-c', 'raise SystemExit(7)'],
                    attempts=2, retry_safe=True)
        with writer(self.root) as directory:
            engine = Engine(self.root, directory, self.task)
            with self.assertRaisesRegex(DeliveryError, 'failed'):
                engine.execute({})
            record = json.loads((engine.directory / 'counter.json').read_text())
            self.assertEqual(record['attempt'], 2)
            self.assertEqual(record['returncode'], 7)
            with self.assertRaisesRegex(DeliveryError, 'exhausted'):
                engine.execute({})

    def test_writer_admission_fails_without_waiting(self):
        with writer(self.root):
            with self.assertRaisesRegex(DeliveryError, 'busy'):
                with writer(self.root):
                    self.fail('second writer admitted')

    def test_cancelled_task_never_starts_check(self):
        with writer(self.root) as directory:
            engine = Engine(self.root, directory, self.task)
            atomic(engine.directory / 'cancel.json', {'requested': True})
            with self.assertRaisesRegex(DeliveryError, 'cancelled'):
                engine.execute({})
        self.assertFalse((self.root / 'counter.txt').exists())

    def test_revision_drift_rejects_discovery(self):
        self.task['base_revision'] = '0' * 40
        with writer(self.root) as directory:
            engine = Engine(self.root, directory, self.task)
            with self.assertRaisesRegex(DeliveryError, 'Revision changed'):
                engine.discovery({})

    def test_task_validation_rejects_retry_without_declared_safety(self):
        self.task['checks'][0]['attempts'] = 2
        path = self.root / '.delivery-task.json'
        path.write_text(json.dumps(self.task))
        with self.assertRaisesRegex(DeliveryError, 'retry_safe'):
            load_task(path)

    def test_task_validation_rejects_output_parent_traversal(self):
        self.task['accepted_outputs'] = {'../outside': '0' * 64}
        path = self.root / '.delivery-task.json'
        path.write_text(json.dumps(self.task))
        with self.assertRaisesRegex(DeliveryError, 'path/hash'):
            load_task(path)


if __name__ == '__main__':
    unittest.main()
