import hashlib
import io
from pathlib import Path
import tempfile
import json
import threading
import time
import unittest
from offmenu.refresh.coverage import COUNTRIES, DOMAINS
from offmenu.refresh.global_run import (Binding, GlobalRunError, Limits, STAGES,
                                        StageResult, compact, run, stream_report, write_report)


def coverage(ids=('a', 'b')):
    return {'countries': [{'iso2': code, 'domains': {d: {'status': 'unassessed', 'sourceIds': []}
                                                    for d in DOMAINS}}
                          for code in COUNTRIES], 'domainNames': list(DOMAINS),
            'sources': [{'sourceId': sid, 'status': 'discovery_only'} for sid in ids]}


def ok(ctx):
    return StageResult('succeeded', evidence=('a' * 64,), observed_count=3)


def binding(handler=ok):
    return Binding({s: handler for s in STAGES}, 'reviewed', True)


class GlobalTests(unittest.TestCase):
    def test_all_cells_explicit_and_unknown(self):
        report = run(coverage())
        self.assertEqual(len(report['countries']), 249)
        self.assertEqual(report['summary']['requiredCountryDomainCells'], 3237)
        self.assertFalse(report['countryCoverageComplete'])
        self.assertFalse(report['executionComplete'])
        self.assertTrue(report['assessmentComplete'])
        self.assertEqual(report['networkRequests'], 0)
        self.assertIsNone(report['sources'][0]['acceptedCount'])
        self.assertEqual(len(report['sources'][0]['stages']), len(STAGES))

    def test_success_does_not_prove_country_coverage(self):
        report = run(coverage(), bindings={'a': binding(), 'b': binding()})
        self.assertTrue(report['executionComplete'])
        self.assertFalse(report['countryCoverageComplete'])
        self.assertEqual(report['status'], 'incomplete')

    def test_independent_failure_continuation_and_sanitized_error(self):
        def bad(ctx):
            raise RuntimeError('https://secret.invalid/?token=secret /private/path')
        report = run(coverage(), bindings={'a': binding(bad), 'b': binding()})
        self.assertEqual(report['sources'][0]['stages']['acquire']['status'], 'failed')
        self.assertEqual(report['sources'][0]['stages']['parse']['status'], 'blocked')
        self.assertTrue(report['sources'][1]['selectedSourceComplete'])
        self.assertNotIn('secret', json.dumps(report))

    def test_source_hold_cannot_be_overridden_by_refresh_or_handler(self):
        data = coverage(('fi',))
        data['sources'][0]['holds'] = ['fineli-force-download-prohibited']
        def forbidden(ctx):
            self.fail('Held handler invoked')
        report = run(data, bindings={'fi': binding(forbidden)}, fetch_policy='force-download', force_rebuild=True)
        self.assertTrue(all(s['status'] == 'held' for s in report['sources'][0]['stages'].values()))

    def test_force_rebuild_is_not_network_policy(self):
        seen = []
        def handler(ctx):
            seen.append(ctx)
            return ok(ctx)
        run(coverage(('a',)), bindings={'a': binding(handler)}, force_rebuild=True)
        self.assertEqual(seen[0].fetch_policy, 'reuse')
        self.assertFalse(seen[0].force_rebuild)
        self.assertTrue(all(c.fetch_policy is None and c.force_rebuild for c in seen[1:]))

    def test_missing_stage_blocks_dependents_only(self):
        b = binding()
        b.handlers.pop('normalize')
        report = run(coverage(), bindings={'a': b, 'b': binding()})
        stages = report['sources'][0]['stages']
        self.assertEqual(stages['normalize']['status'], 'unsupported')
        self.assertEqual(stages['validate']['status'], 'blocked')
        self.assertTrue(report['sources'][1]['selectedSourceComplete'])

    def test_evidence_required_counts_do_not_default_zero(self):
        report = run(coverage(('a',)), bindings={'a': binding(lambda c: StageResult('succeeded'))})
        self.assertEqual(report['sources'][0]['stages']['acquire']['code'], 'stage-contract-invalid')
        self.assertIsNone(report['sources'][0]['acceptedCount'])

    def test_resource_boundary_gate(self):
        report = run(coverage(('a',)), bindings={'a': Binding({s: ok for s in STAGES}, 'reviewed')})
        self.assertEqual(report['sources'][0]['stages']['acquire']['code'], 'resource-boundary-unverified')

    def test_bounded_parallelism_memory_reservation_and_stable_order(self):
        active = peak = 0
        lock = threading.Lock()
        def handler(ctx):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            time.sleep(.001)
            with lock:
                active -= 1
            return ok(ctx)
        data = coverage(tuple(reversed('abcdef')))
        result = run(data, bindings={s: binding(handler) for s in 'abcdef'},
                     limits=Limits(workers=4, memory_bytes=2, job_memory_bytes=1))
        self.assertLessEqual(peak, 2)
        self.assertEqual([s['sourceId'] for s in result['sources']], list('abcdef'))
        self.assertEqual(result['parallelSourceLimit'], 2)

    def test_registry_and_limits_fail_before_callbacks(self):
        invalid = coverage()
        invalid['countries'].pop()
        with self.assertRaises(GlobalRunError):
            run(invalid)
        with self.assertRaises(GlobalRunError):
            run(coverage(), limits=Limits(max_sources=1))
        with self.assertRaises(GlobalRunError):
            run(coverage(), limits=Limits(workers=True))
        with self.assertRaises(GlobalRunError):
            run(coverage(), bindings={'missing': binding()})

    def test_compact_is_bounded_and_order_independent(self):
        data = coverage()
        first = run(data)
        data['sources'].reverse()
        data['countries'].reverse()
        second = run(data)
        self.assertEqual(compact(first), compact(second))
        self.assertLess(len(json.dumps(compact(first))), 2048)
        self.assertEqual(compact(first)['stageStatusCounts']['unsupported'], 2 * len(STAGES))

    def test_large_acquisition_budget_does_not_expand_parser_budget(self):
        limits = Limits(acquire_bytes=1024**4, acquire_wall_seconds=600)
        self.assertEqual(limits.input_bytes, 64 * 1024**2)
        self.assertEqual(limits.validate(), 4)
        with self.assertRaises(GlobalRunError):
            Limits(acquire_bytes=1024**4 + 1).validate()
        with self.assertRaises(GlobalRunError):
            Limits(input_bytes=64 * 1024**2 + 1).validate()

    def test_streamed_report_matches_canonical_hash(self):
        report = {'z': 'café', 'a': [1, 2]}
        expected = json.dumps(report, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        stream = io.BytesIO()
        digest, size = stream_report(report, stream)
        self.assertEqual(stream.getvalue(), expected)
        self.assertEqual(digest, hashlib.sha256(expected).hexdigest())
        self.assertEqual(size, len(expected))

    def test_exclusive_streamed_report_refuses_overwrite_and_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'report.json'
            write_report({'synthetic': True}, output)
            self.assertEqual(json.loads(output.read_text()), {'synthetic': True})
            with self.assertRaises(GlobalRunError):
                write_report({}, output)
            link = Path(directory) / 'link.json'
            link.symlink_to(output)
            with self.assertRaises(GlobalRunError):
                write_report({}, link)
            self.assertEqual(len(list(Path(directory).glob('.global-report-*'))), 0)

    def test_historical_capability_is_retained_without_new_acceptance(self):
        data = coverage(('a',))
        data['retainedReleases'] = [{'releaseId': 'old', 'historicalRecordClaim': 42}]
        data['capabilityEvidence'] = [{'commit': 'baseline'}]
        data['sources'][0]['historicalCapability'] = {'handler': {'path': 'old.py'}, 'executable': False}
        report = run(data)
        self.assertEqual(report['retainedReleases'], data['retainedReleases'])
        self.assertEqual(report['capabilityEvidence'], data['capabilityEvidence'])
        self.assertEqual(report['sources'][0]['historicalCapability'], data['sources'][0]['historicalCapability'])
        self.assertFalse(report['countryCoverageComplete'])

    def test_full_report_preserves_supporting_evidence_and_blockers(self):
        data = coverage(('a',))
        data['supportingHandlers'] = [{'id': 'qualification-sidecar', 'executable': False}]
        fields = {'declaredCountries': ['US'], 'globalRoute': True,
                  'blockers': ['discovery-release-differs-from-retained-handler-release'],
                  'errors': []}
        data['sources'][0].update(fields)
        report = run(data)
        self.assertEqual(report['supportingHandlers'], data['supportingHandlers'])
        for key, value in fields.items():
            self.assertEqual(report['sources'][0][key], value)
        self.assertNotIn('supportingHandlers', compact(report))
        self.assertNotIn('blockers', json.dumps(compact(report)))
        self.assertFalse(report['executionComplete'])

    def test_context_previous_evidence_is_immutable(self):
        def handler(ctx):
            if ctx.previous:
                with self.assertRaises(TypeError):
                    ctx.previous[0][1]['status'] = 'hacked'
                self.assertIsInstance(ctx.previous[0][1]['evidence'], tuple)
            return ok(ctx)
        run(coverage(('a',)), bindings={'a': binding(handler)})


if __name__ == '__main__':
    unittest.main()
