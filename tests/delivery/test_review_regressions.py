"""Precise regressions for check evidence, branch identity and receipt names."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from offmenu.delivery.engine import DeliveryError, Engine, load_task
from test_engine import DeliveryFixture


class ReviewRegressionTests(DeliveryFixture):
    def observe_output_command(self):
        """Count real executions and retain what this execution actually saw."""
        return [sys.executable, '-c',
                "from pathlib import Path; p=Path('counter.txt'); "
                "p.write_text(str(int(p.read_text())+1) if p.exists() else '1'); "
                "print(Path('result.txt').read_text())"]

    def test_changed_output_after_successful_check_cannot_reuse_default_cache(self):
        (self.root / 'result.txt').write_text('wrong bytes seen by check\n')
        self.task['checks'][0]['argv'] = self.observe_output_command()
        self.run_engine('execute')
        self.assertIn('wrong bytes seen by check', self.record('counter-1.log').read_text())
        (self.root / 'result.txt').write_text('accepted bytes\n')
        with self.assertRaises(DeliveryError):
            self.run_engine()
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')
        self.assertFalse(self.record('accepted.json').exists())

    def test_explicit_safe_budget_reexecutes_checks_against_current_outputs(self):
        (self.root / 'result.txt').write_text('wrong bytes seen by check\n')
        self.task['checks'][0].update(argv=self.observe_output_command(),
                                     attempts=2, retry_safe=True)
        self.run_engine('execute')
        first = json.loads(self.record().read_text())
        self.assertEqual(first['output_state']['result.txt'],
                         hashlib.sha256(b'wrong bytes seen by check\n').hexdigest())
        (self.root / 'result.txt').write_text('accepted bytes\n')
        result = self.run_engine()
        self.assertEqual(result['status'], 'accepted')
        self.assertEqual((self.root / 'counter.txt').read_text(), '2')
        record = json.loads(self.record().read_text())
        self.assertEqual(record['attempt'], 2)
        self.assertEqual(record['output_state'], self.task['accepted_outputs'])
        self.assertRegex(record['source_sha256'], r'^[0-9a-f]{64}$')
        self.assertIn('accepted bytes', self.record('counter-2.log').read_text())

    def test_missing_output_generated_by_command_is_accepted(self):
        (self.root / 'result.txt').unlink()
        self.task['checks'][0]['argv'] = [sys.executable, '-c',
                "from pathlib import Path; Path('result.txt').write_text('accepted bytes\\n')"]
        result = self.run_engine()
        self.assertEqual(result['status'], 'accepted')
        record = json.loads(self.record().read_text())
        self.assertEqual(record['output_state'], self.task['accepted_outputs'])

    def test_sequential_producers_do_not_freeze_missing_outputs_at_start(self):
        (self.root / 'result.txt').unlink()
        self.task['accepted_outputs']['second.txt'] = hashlib.sha256(b'second accepted\n').hexdigest()
        policy_path = self.root / 'repository-standard.json'
        policy = json.loads(policy_path.read_text())
        policy['roots']['second.txt'] = {}
        policy_path.write_text(json.dumps(policy))
        self.task['checks'] = [
            {'id': 'producer-a', 'argv': [sys.executable, '-c',
                "from pathlib import Path; Path('result.txt').write_text('accepted bytes\\n')"],
             'timeout': 10},
            {'id': 'producer-b', 'argv': [sys.executable, '-c',
                "from pathlib import Path; assert Path('result.txt').read_text() == 'accepted bytes\\n'; "
                "Path('second.txt').write_text('second accepted\\n')"], 'timeout': 10}]
        result = self.run_engine()
        self.assertEqual(result['status'], 'accepted')
        first = json.loads(self.record('producer-a.json').read_text())
        last = json.loads(self.record('producer-b.json').read_text())
        self.assertEqual(first['output_state']['result.txt'], self.task['accepted_outputs']['result.txt'])
        self.assertIsNone(first['output_state']['second.txt'])
        self.assertEqual(last['output_state'], self.task['accepted_outputs'])
        accepted = json.loads(self.record('accepted.json').read_text())
        self.assertEqual(accepted['outputs'], self.task['accepted_outputs'])

    def test_failed_later_producer_retries_without_repeating_successful_prefix(self):
        self.task['accepted_outputs']['second.txt'] = hashlib.sha256(b'second accepted\n').hexdigest()
        policy_path = self.root / 'repository-standard.json'
        policy = json.loads(policy_path.read_text())
        policy['roots']['second.txt'] = {}
        policy_path.write_text(json.dumps(policy))
        self.task['checks'] = [
            {'id': 'producer-a', 'argv': [sys.executable, '-c',
                "from pathlib import Path; Path('result.txt').write_text('accepted bytes\\n')"],
             'timeout': 10},
            {'id': 'producer-b', 'argv': [sys.executable, '-c',
                "from pathlib import Path; p=Path('counter.txt'); "
                "p.write_text(str(int(p.read_text())+1) if p.exists() else '1'); "
                "Path('second.txt').write_text('partial' if p.read_text() == '1' else 'second accepted\\n'); "
                "raise SystemExit(7 if p.read_text() == '1' else 0)"],
             'timeout': 10, 'attempts': 2, 'retry_safe': True}]
        original_event = Engine.event
        def interrupt_after_record(engine, name, detail):
            original_event(engine, name, detail)
            if name == 'check-finished' and detail == {'check': 'producer-b', 'status': 'failed'}:
                raise DeliveryError('interrupted after recorded failure')
        with patch.object(Engine, 'event', interrupt_after_record):
            with self.assertRaisesRegex(DeliveryError, 'interrupted after recorded failure'):
                self.run_engine()
        self.assertEqual(self.run_engine()['status'], 'accepted')
        self.assertEqual(json.loads(self.record('producer-a.json').read_text())['attempt'], 1)
        self.assertEqual(json.loads(self.record('producer-b.json').read_text())['attempt'], 2)
        self.assertEqual((self.root / 'counter.txt').read_text(), '2')

    def test_pause_is_bound_to_exact_branch_even_at_identical_head(self):
        self.run_engine('execute')
        original_head = self.git('rev-parse', 'HEAD')
        binding = json.loads(self.record('binding.json').read_text())
        self.assertEqual(binding['branch'], 'feature/test')
        self.git('switch', '-qc', 'feature/other')
        self.assertEqual(self.git('rev-parse', 'HEAD'), original_head)
        with self.assertRaises(DeliveryError):
            self.run_engine()
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')
        self.assertFalse(self.record('accepted.json').exists())
        self.git('switch', '-q', 'feature/test')
        self.assertEqual(self.run_engine()['status'], 'accepted')
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')
        self.assertEqual(json.loads(self.record('accepted.json').read_text())['branch'], 'feature/test')

    def test_accepted_reentry_requires_original_branch_and_restores_without_replay(self):
        self.run_engine()
        original_head = self.git('rev-parse', 'HEAD')
        self.git('switch', '-qc', 'bugfix/other')
        self.assertEqual(self.git('rev-parse', 'HEAD'), original_head)
        with self.assertRaises(DeliveryError):
            self.run_engine()
        self.git('switch', '-q', 'feature/test')
        accepted = self.run_engine()
        self.assertEqual(accepted['branch'], 'feature/test')
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')
        self.assertEqual(json.loads(self.record('binding.json').read_text())['branch'], 'feature/test')

    def test_reserved_and_path_variant_check_ids_rejected_before_writes(self):
        bad_ids = ('binding', 'cancel', 'accepted', 'event-a', 'event-1',
                   '../accepted', '/cancel', 'binding.json', 'Binding', 'CANCEL', 'ACCEPTED')
        task_path = self.root / '.review-task.json'
        destination = self.root / '.delivery'
        destination.mkdir()
        for check_id in bad_ids:
            with self.subTest(check_id=check_id):
                task = copy.deepcopy(self.task)
                task['checks'][0]['id'] = check_id
                task_path.write_text(json.dumps(task))
                with self.assertRaises(DeliveryError):
                    load_task(task_path)
                before = list(destination.iterdir())
                with self.assertRaises(DeliveryError):
                    Engine(self.root, destination, task)
                self.assertEqual(list(destination.iterdir()), before)


if __name__ == '__main__':
    unittest.main()
