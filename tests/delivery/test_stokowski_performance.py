"""Finite receipt projection through execute; providers/processes are always fake."""
from contextlib import ExitStack, nullcontext
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

TOOLS = Path(__file__).resolve().parents[2] / 'tools/delivery'
sys.path.insert(0, str(TOOLS))
import stokowski_performance as performance
import stokowski_worker as worker


class ProjectionTests(unittest.TestCase):
    def test_untrusted_events_are_projected_without_messages_cost_or_inferred_usage(self):
        with tempfile.TemporaryDirectory() as temporary:
            events = Path(temporary) / 'events'
            events.write_text(json.dumps(dict(
                type='turn.completed', model='gpt-observed', prompt='SECRET',
                usage=dict(input_tokens=0, cached_input_tokens=2, output_tokens=-1,
                           cost_usd=0, api_key='SECRET', messages=['SECRET']))))
            summary = worker.summarize_events(events)
        observation = performance.project_observation(dict(
            summary, requested_model=worker.MODEL, requested_effort='medium',
            provider_route='codex-chatgpt', resolved_provider='SECRET',
            observed_effort='SECRET', status='succeeded', accepted_delivery=False))
        self.assertEqual(observation['usage']['counters'], dict(
            input_tokens=0, cached_input_tokens=2, output_tokens=None))
        self.assertEqual(observation['observed'], dict(
            model='gpt-observed', provider=None, effort=None))
        self.assertFalse(observation['acceptance']['accepted_delivery'])
        self.assertEqual(observation['acceptance']['functional'], 'unknown')
        encoded = performance.serialize_observation(observation)
        for excluded in ('SECRET', 'cost_usd', 'messages', 'api_key', 'prompt'):
            self.assertNotIn(excluded, encoded)

    def test_malformed_and_oversized_data_stays_unknown_and_bounded(self):
        for invalid in (-1, True, 1.5, '0', {}, 2**64, float('nan')):
            with self.subTest(invalid=invalid):
                observed = performance.project_observation(dict(
                    turn_completed=True, resource_sample_count=1, usage=dict(input_tokens=invalid),
                    observed_resources=dict(peak_rss_bytes=invalid)))
                self.assertIsNone(observed['usage']['counters']['input_tokens'])
                self.assertIsNone(observed['sampled_resources']['peak_rss_bytes'])
        for elapsed in (float('inf'), float('nan'), -1, 10**1000, True):
            self.assertIsNone(performance.project_observation(dict(
                supervise_elapsed_seconds=elapsed))['timing']['elapsed_seconds'])
        for receipt in (None, [], dict(usage=['SECRET'], status={},
                         resolved_model='SECRET ' * 10000,
                         observed_resources=dict(cpu_affinity=list(range(257))),
                         output_sha256={'../secret': 'a'*64})):
            observed = performance.project_observation(receipt)
            self.assertIsNone(observed['observed']['model'])
            self.assertIsNone(observed['output_sha256'])
            self.assertLess(len(performance.serialize_observation(observed)), performance.MAX_BYTES)
        outputs = {('a'*230 + str(i)): 'b'*64 for i in range(32)}
        observation = performance.project_observation(dict(output_sha256=outputs))
        self.assertEqual(observation['output_sha256'], outputs)
        self.assertLess(len(performance.serialize_observation(observation)), performance.MAX_BYTES)
        self.assertEqual(performance.serialize_observation(observation),
                         performance.serialize_observation(performance.project_observation(
                             dict(output_sha256=dict(reversed(list(outputs.items())))))))
        outputs['extra'] = 'c'*64
        self.assertIsNone(performance.project_observation(dict(output_sha256=outputs))['output_sha256'])

    def test_legacy_zero_peaks_without_sample_evidence_remain_unknown(self):
        for count in (None, 0, -1, True, '1'):
            observed = performance.project_observation(dict(
                resource_sample_count=count,
                observed_resources=dict(peak_processes=0, peak_rss_bytes=0)))
            self.assertIsNone(observed['sampled_resources']['peak_processes'])
            self.assertIsNone(observed['sampled_resources']['peak_rss_bytes'])

    def test_known_zero_is_preserved_without_manufacturing_other_observations(self):
        observed = performance.project_observation(dict(
            turn_completed=True, resource_sample_count=1, usage=dict(input_tokens=0),
            observed_resources=dict(peak_processes=0, peak_rss_bytes=0),
            declared_resources=dict(output_bytes=0), output_sha256={}))
        self.assertEqual(observed['sampled_resources']['peak_rss_bytes'], 0)
        self.assertEqual(observed['declared_resources']['output_bytes'], 0)
        self.assertIsNone(observed['declared_resources']['cpu_millis'])
        self.assertEqual(observed['observed'], dict(model=None, provider=None, effort=None))
        self.assertTrue(all(value is None for value in observed['attempt_metadata'].values()))
        self.assertIsNone(observed['timing']['queue_seconds'])


class ExecuteTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.runtime = Path(temporary.name)
        self.issue = 'UIF-119'
        self.workspace = self.runtime/'workspaces'/self.issue
        self.workspace.mkdir(parents=True)
        self.head = 'a'*40
        self.resources = dict(cpu_millis=1000, memory_bytes=2**31,
                              io_slots=1, output_bytes=2**24)
        self.manifest = dict(base_revision=self.head, branch='feature/offline', tasks={
            self.issue: dict(owner='offline', allowed_paths=['result.py'],
                             resources=self.resources, purpose='Offline test')})
        self.policy = dict(symphony=dict(pool_path='unused', cpu_budget_millis=1000),
                           host=dict(cpu_reserve=0),
                           windmill=dict(computation_subprocesses_per_job=64))
        for name, value in (('manifest.json', self.manifest),
                            ('capacity-policy.json', self.policy),
                            ('provider-proof.json', {'available': True})):
            (self.runtime / name).write_text(json.dumps(value))
        self.directory = self.runtime / 'attempts' / self.issue
        self.state = 'running'
        self.pool = Mock()
        self.pool.admit.return_value = {}
        def finish(*args):
            # Receipt is durable, complete and projected before lease release.
            saved = json.loads((self.directory / 'receipt.json').read_text())
            self.assertTrue(saved['child_tree_gone'])
            self.assertIn('performance_observation', saved)
            self.state = 'finished'
        self.pool.finish.side_effect = finish
        self.process_result = dict(status='succeeded', child_tree_gone=True, exit_code=0)
        self.stack = self.enterContext(ExitStack())
        patches = dict(
            load_manifest=lambda *a, **k: self.manifest,
            git=lambda root, *a: self.head if a[-1] == 'HEAD' else 'feature/offline',
            changed_paths=lambda *a: ['result.py'] if (a[0]/'result.py').exists() else [],
            Pool=lambda *a: self.pool,
            runtime_lease_ids=lambda *a: {self.issue: 'offline-lease'},
            host_snapshot=lambda *a: {},
            isolated_codex_environment=lambda *a: nullcontext({}))
        for name, value in patches.items():
            self.stack.enter_context(patch.object(worker, name, value))
        self.stack.enter_context(patch.object(worker.os, 'sched_getaffinity', return_value={0, 1}))
        self.stack.enter_context(patch.object(worker.os, 'sched_setaffinity'))
        self.process = self.stack.enter_context(patch.object(worker, 'supervise', side_effect=self.fake_process))

    def fake_process(self, *args):
        (self.directory / 'stdout.jsonl').write_text(json.dumps(dict(
            type='turn.completed', usage=dict(input_tokens=7, secret='SECRET'))))
        return dict(self.process_result)

    def execute(self):
        return worker.execute(self.runtime, self.issue, dict(prompt='SECRET', timeout_seconds=5))

    def test_execute_consumes_bound_observation_in_actual_terminal_checkpoint(self):
        self.process_result.update(supervise_elapsed_seconds=1.25, resource_sample_count=1,
                                   observed_resources=dict(peak_processes=2, peak_rss_bytes=0))
        def completed(*args):
            (self.workspace/'result.py').write_text('# offline output\n')
            return self.fake_process(*args)
        self.process.side_effect = completed
        result = self.execute()
        saved = json.loads((self.directory / 'receipt.json').read_text())
        self.assertEqual(result, saved)
        observation = saved['performance_observation']
        self.assertEqual(observation['binding']['source_head'], self.head)
        self.assertEqual(observation['binding']['lease'], 'offline-lease')
        self.assertEqual(observation['binding']['binding_sha256'], saved['binding_sha256'])
        self.assertEqual(observation['declared_resources'], self.resources)
        self.assertEqual(observation['usage']['counters']['input_tokens'], 7)
        self.assertEqual(observation['timing']['elapsed_seconds'], 1.25)
        self.assertIsNone(observation['timing']['queue_seconds'])
        self.assertEqual(observation['sampled_resources']['peak_rss_bytes'], 0)
        self.assertEqual(observation['output_sha256'], {'result.py': hashlib.sha256(
            (self.workspace/'result.py').read_bytes()).hexdigest()})
        self.assertFalse(observation['acceptance']['accepted_delivery'])
        self.assertEqual(observation['observed'], dict(model=None, provider=None, effort=None))
        self.assertNotIn('SECRET', performance.serialize_observation(observation))
        for field, path in (('worker_sha256', TOOLS/'stokowski_worker.py'),
                            ('helper_sha256', TOOLS/'stokowski_performance.py'),
                            ('capacity_policy_sha256', self.runtime/'capacity-policy.json')):
            self.assertEqual(observation['provenance'][field], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(self.state, 'finished')

    def test_cancellation_and_uncertain_cleanup_keep_receipt_lease_invariant(self):
        self.process_result.update(status='cancelled', child_tree_gone=True)
        result = self.execute()
        self.assertTrue(result['performance_observation']['attempt_metadata']['cancelled'])
        self.assertEqual(self.state, 'finished')

    def test_uncertain_cleanup_keeps_lease(self):
        self.process_result.update(status='uncertain', child_tree_gone=False)
        result = self.execute()
        self.assertNotIn('performance_observation', result)
        self.assertEqual(self.state, 'running')
        self.pool.finish.assert_not_called()
        self.assertTrue((self.directory/'receipt.json').exists())

    def test_execute_pre_start_cancel_without_events_keeps_unknowns_and_releases_safely(self):
        self.process.side_effect = None
        self.process.return_value = dict(status='cancelled', child_tree_gone=True, exit_code=None)
        result = self.execute()
        observed = result['performance_observation']
        # Existing source/turn checks may label execution failed; cancellation
        # remains an independently known fact, without inventing elapsed/usage.
        self.assertTrue(observed['attempt_metadata']['cancelled'])
        self.assertIsNone(observed['timing']['elapsed_seconds'])
        self.assertIsNone(observed['sampled_resources']['peak_rss_bytes'])
        self.assertIsNone(observed['usage']['counters']['input_tokens'])
        self.assertEqual(self.state, 'finished')

    def test_process_exception_preserves_exact_unknown_fallback_and_lease(self):
        self.process.side_effect = OSError('SECRET process exception')
        with self.assertRaises(OSError):
            self.execute()
        saved = json.loads((self.directory/'receipt.json').read_text())
        self.assertEqual(saved, dict(status='uncertain', child_tree_gone=False))
        self.assertEqual(self.state, 'running')
        self.pool.finish.assert_not_called()

    def test_setup_exception_preserves_exact_unknown_fallback_and_lease(self):
        with patch.object(worker.os, 'sched_setaffinity', side_effect=OSError('setup')):
            with self.assertRaises(OSError):
                self.execute()
        saved = json.loads((self.directory/'receipt.json').read_text())
        self.assertEqual(saved, dict(status='uncertain', child_tree_gone=False))
        self.process.assert_not_called()
        self.pool.finish.assert_not_called()

    def test_returned_child_result_is_not_projected_before_source_binding(self):
        # The child has stopped, but qualification itself fails. Finally must
        # persist the existing result without attaching an admission-only projection.
        self.pool.finish.side_effect = None
        with patch.object(worker, 'git', side_effect=[self.head, 'feature/offline', OSError('source')]):
            with self.assertRaises(OSError):
                self.execute()
        saved = json.loads((self.directory/'receipt.json').read_text())
        self.assertTrue(saved['child_tree_gone'])
        self.assertNotIn('performance_observation', saved)
        self.assertNotIn('binding_sha256', saved)

    def test_qualified_failed_result_is_projected_without_delivery_acceptance(self):
        self.process_result.update(status='failed', exit_code=1)
        result = self.execute()
        observed = result['performance_observation']
        self.assertEqual(observed['binding']['issue'], self.issue)
        self.assertEqual(observed['execution']['status'], 'failed')
        self.assertFalse(observed['acceptance']['accepted_delivery'])


class SuperviseTimingTests(unittest.TestCase):
    def test_monotonic_elapsed_includes_cleanup_and_samples_only_when_taken(self):
        for running, processes, rss in ((True, 0, 0), (True, 2, 512), (False, 0, 0)):
            with self.subTest(running=running, rss=rss), tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
                directory = Path(temporary)/'attempts'/'UIF-119'
                directory.mkdir(parents=True)
                stdin = io.BytesIO()
                process = SimpleNamespace(stdin=stdin, returncode=0,
                                          poll=Mock(side_effect=[None, 0, 0] if running else [0, 0]))
                stack.enter_context(patch.object(worker.ctypes, 'CDLL', return_value=SimpleNamespace(prctl=lambda *a: 0)))
                stack.enter_context(patch.object(worker.signal, 'signal'))
                stack.enter_context(patch.object(worker.os, 'sched_getaffinity', return_value={1}))
                stack.enter_context(patch.object(worker.os, 'set_blocking'))
                # Empty prompt avoids writing any process input.
                stack.enter_context(patch.object(worker.subprocess, 'Popen', return_value=process))
                stack.enter_context(patch.object(worker, 'cleanup', return_value=True))
                stack.enter_context(patch.object(worker, 'capacity_usage', return_value=dict(processes=processes, rss_bytes=rss)))
                clock = stack.enter_context(patch.object(worker.time, 'monotonic', side_effect=[10, 10.1, 10.75] if running else [10, 10.75]))
                stack.enter_context(patch.object(worker.time, 'sleep'))
                # BytesIO has no OS descriptor; only the fake descriptor is passed to mocked set_blocking.
                process.stdin = Mock(wraps=stdin)
                process.stdin.closed = False
                process.stdin.fileno.return_value = 123
                result = worker.supervise([], '', directory, {}, directory, 5, dict(memory_bytes=1024))
                self.assertEqual(result['supervise_elapsed_seconds'], .75)
                self.assertEqual(result['observed_resources'], dict(
                    peak_processes=processes, peak_rss_bytes=rss, cpu_affinity=[1]))
                self.assertEqual(result['resource_sample_count'], 1 if running else 0)
                observed = performance.project_observation(result)
                self.assertEqual(observed['sampled_resources']['peak_rss_bytes'], rss if running else None)
                self.assertEqual(observed['sampled_resources']['peak_processes'], processes if running else None)
                self.assertTrue(result['child_tree_gone'])
                self.assertEqual(clock.call_count, 3 if running else 2)

    def test_pre_start_cancel_has_unknown_elapsed_and_samples(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)/'attempts'/'UIF-119'
            directory.mkdir(parents=True)
            (Path(temporary)/'cancel.json').write_text('{}')
            with patch.object(worker.subprocess, 'Popen') as process:
                result = worker.supervise([], '', directory, {}, directory, 5, {})
            process.assert_not_called()
            observed = performance.project_observation(result)
            self.assertIsNone(observed['timing']['elapsed_seconds'])
            self.assertIsNone(observed['sampled_resources']['peak_processes'])
            self.assertTrue(observed['attempt_metadata']['cancelled'])


if __name__ == '__main__':
    unittest.main()
