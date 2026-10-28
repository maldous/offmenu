import base64
import copy
import importlib.util
import json
import multiprocessing
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('adapter', Path(__file__).with_name('offmenu_groq_public_development_20261028.py'))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
TASK = 'atomic_checkpoint_review'
OUTPUT = json.dumps({'defects': ['non-atomic write'], 'fixes': ['replace temporary file'], 'tests': ['crash before replacement']})


def response(**changes):
    result = {'status': 'completed', 'finish_reason': 'stop', 'output': OUTPUT,
              'output_truncated': False, 'accepted': True, 'inference_calls': 1,
              'prompt_tokens': 10, 'completion_tokens': 20, 'provider_cached_tokens': 4,
              'cache_hit': False, 'response_id': 'synthetic-id', 'output_is_untrusted': True}
    result.update(changes)
    return result


def run(root, **changes):
    args = dict(cache_dir=root, account_namespace='public-fixture-account', model_version='verified-epoch-1')
    args.update(changes)
    return a.run_cached({}, TASK, **args)


def process_run(root, counter, queue, reject=False, barrier=None):
    def provider(*args):
        with counter.get_lock():
            counter.value += 1
        time.sleep(.1)
        return response(status='request_failed_no_retry', error_type='TimeoutError') if reject else response()
    if barrier is not None:
        barrier.wait()
    with patch.object(a, 'main', side_effect=provider):
        queue.put(run(root))


class AcceptedReuseTests(unittest.TestCase):
    def test_exact_reuse_revalidates_and_does_not_recount_usage_or_artifacts(self):
        with tempfile.TemporaryDirectory() as root, patch.object(a, '_provider_with_deadline', return_value=response()) as provider:
            first, second = run(root), run(root)
            self.assertEqual(provider.call_count, 1)
            self.assertEqual(first['new_accepted_outputs'], 1)
            self.assertEqual(second['new_accepted_outputs'], 0)
            self.assertEqual(second['accepted_artifact_id'], first['accepted_artifact_id'])
            self.assertEqual(second['prompt_tokens'], 0)
            self.assertEqual(second['origin_usage']['provider_cached_tokens'], 4)
            self.assertEqual(second['response_id'], 'synthetic-id')
            self.assertTrue(second['output_is_untrusted'])
            self.assertNotEqual(first['receipt_id'], second['receipt_id'])
            receipt = json.loads(Path(second['receipt_path']).read_text())
            self.assertEqual(receipt['result'], second)
            with patch.object(a, 'validate', return_value=(False, 'changed_validator')):
                rejected = run(root)
            self.assertFalse(rejected['accepted'])
            self.assertEqual(provider.call_count, 2)
            self.assertEqual(len(list((Path(root)/'rejected').iterdir())), 1)

    def test_each_provenance_dimension_invalidates(self):
        original = a.provenance(TASK, 'account', 'version')
        variants = []
        for field in ('provider', 'account_namespace', 'model', 'model_version', 'source_sha256', 'input_sha256', 'task'):
            changed = copy.deepcopy(original)
            changed[field] += '-changed'
            variants.append(changed)
        for field in a.VERSIONS:
            changed = copy.deepcopy(original)
            changed['versions'][field] += '-changed'
            variants.append(changed)
        changed = copy.deepcopy(original)
        changed['generation_settings']['max_tokens'] += 1
        variants.append(changed)
        with tempfile.TemporaryDirectory() as root, patch.object(a, '_provider_with_deadline', return_value=response()) as provider:
            for prov in [original]+variants:
                with patch.object(a, 'provenance', return_value=prov):
                    self.assertFalse(run(root)['cache_hit'])
            self.assertEqual(provider.call_count, len(variants)+1)

    def test_rejections_errors_truncation_and_malformed_json_are_retained_not_cached(self):
        for result in (response(status='request_failed_no_retry', error_type='TimeoutError'),
                       response(finish_reason='length', output_truncated=True),
                       response(output='{"defects":[],"defects":[],"fixes":[],"tests":[]}'),
                       response(output='not json'), response(output=OUTPUT, finish_reason='tool_calls')):
            with self.subTest(result=result), tempfile.TemporaryDirectory() as root, patch.object(a, '_provider_with_deadline', return_value=result):
                rejected = run(root)
                self.assertFalse(rejected['accepted'])
                self.assertEqual(rejected['output'], result['output'])
                self.assertEqual(rejected['status'], result['status'])
                self.assertEqual(list((Path(root)/'accepted').iterdir()), [])
                self.assertTrue(Path(rejected['receipt_path']).exists())

    def test_cross_process_single_flight_and_unique_artifact(self):
        ctx = multiprocessing.get_context('fork')
        counter, queue = ctx.Value('i', 0), ctx.Queue()
        with tempfile.TemporaryDirectory() as root:
            workers = [ctx.Process(target=process_run, args=(root, counter, queue)) for _ in range(4)]
            for worker in workers:
                worker.start()
            results = [queue.get(timeout=5) for _ in workers]
            for worker in workers:
                worker.join(timeout=5)
                self.assertEqual(worker.exitcode, 0)
            self.assertEqual(counter.value, 1)
            self.assertEqual(sum(r['new_accepted_outputs'] for r in results), 1)
            self.assertEqual(sum(r['cache_hit'] for r in results), 3)
            self.assertEqual(sum(r['prompt_tokens'] for r in results), 10)
            self.assertEqual(len({r['accepted_artifact_id'] for r in results}), 1)

    def test_simultaneous_failures_shared_but_later_call_is_not_cached(self):
        ctx = multiprocessing.get_context('fork')
        counter, queue, barrier = ctx.Value('i', 0), ctx.Queue(), ctx.Barrier(3)
        with tempfile.TemporaryDirectory() as root:
            workers = [ctx.Process(target=process_run, args=(root, counter, queue, True, barrier)) for _ in range(3)]
            for worker in workers:
                worker.start()
            results = [queue.get(timeout=5) for _ in workers]
            for worker in workers:
                worker.join(timeout=5)
                self.assertEqual(worker.exitcode, 0)
            self.assertEqual(counter.value, 1)
            self.assertTrue(all(r['status'] == 'request_failed_no_retry' for r in results))
            self.assertTrue(all(not r['cache_hit'] for r in results))
            self.assertEqual(sum(r.get('shared_inflight', False) for r in results), 2)
            with patch.object(a, '_provider_with_deadline', return_value=response()) as provider:
                later = run(root)
            provider.assert_called_once()
            self.assertTrue(later['accepted'])

    def test_tampering_cannot_be_reused_or_duplicate_identical_artifact(self):
        with tempfile.TemporaryDirectory() as root, patch.object(a, '_provider_with_deadline', return_value=response()) as provider:
            first = run(root)
            path = Path(root)/'accepted'/(first['cache_key']+'.json')
            entry = json.loads(path.read_text())
            entry['result']['output'] = OUTPUT+' '
            path.write_text(json.dumps(entry))
            again = run(root)
            self.assertFalse(again['cache_hit'])
            self.assertEqual(again['new_accepted_outputs'], 0)
            self.assertEqual(again['accepted_artifact_id'], first['accepted_artifact_id'])
            self.assertEqual(provider.call_count, 2)

    def test_transport_records_provider_cached_tokens_only_when_present(self):
        for cached in (None, 0, 7):
            usage = {'prompt_tokens': 10, 'completion_tokens': 20}
            if cached is not None:
                usage['prompt_tokens_details'] = {'cached_tokens': cached}
            body = json.dumps({'id': 'synthetic-response', 'model': a.MODEL, 'usage': usage,
                               'choices': [{'message': {'content': OUTPUT}, 'finish_reason': 'stop'}]}).encode()
            class Transport:
                def request(self, *args, **kwargs): pass
                def getresponse(self): return self
                status = 200
                def read(self, limit): return body[:limit]
                def close(self): pass
            with patch.object(a.http.client, 'HTTPSConnection', return_value=Transport()):
                result = a.main({'api_key': 'synthetic-test-value'}, TASK)
            self.assertTrue(result['accepted'])
            self.assertEqual(result['provider_cached_tokens'], cached)
            self.assertEqual(base64.b64decode(result['response_body_base64']), body)

    def test_each_fixed_task_shape_and_strict_json(self):
        for task, setup, count in [('exact_hash_custody_test_design', 'setup_summary', 4),
                                   ('parallel_batch_test_design', 'setup', 5)]:
            output = json.dumps({'tests': [{'name': str(i), setup: 'synthetic', 'expected': 'unknown stays unknown'} for i in range(count)]})
            self.assertTrue(a.validate(task, response(output=output))[0])
            self.assertFalse(a.validate(task, response(output='{"tests":[]}'))[0])
        self.assertFalse(a.validate(TASK, response(output='{"defects":[NaN],"fixes":["x"],"tests":["y"]}'))[0])

    def test_missing_namespace_or_model_epoch_rejected_before_provider(self):
        with tempfile.TemporaryDirectory() as root, patch.object(a, 'main') as provider:
            for options in ({'account_namespace': ''}, {'model_version': ''}):
                with self.assertRaises(ValueError):
                    run(root, **options)
            provider.assert_not_called()


if __name__ == '__main__':
    unittest.main()
