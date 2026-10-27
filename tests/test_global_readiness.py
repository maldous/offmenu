import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

census = load('global_readiness_test_subject', ROOT / 'scripts/global-readiness.py')
dispatch = load('global_readiness_dispatch_subject', ROOT / 'scripts/dispatch-foo-job.py')
OBSERVED = '2026-10-18T02:00:00Z'


class GlobalReadinessTests(unittest.TestCase):
    def setUp(self):
        # Source checkouts contain real pinned metadata on Foo. Every test must
        # start with missing synthetic inputs and an isolated output location.
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        checkout = patch.object(census, 'TRUSTED_ROOT', root / 'missing-checkout')
        output = patch.object(census, 'OUTPUT', root / 'outputs')
        checkout.start()
        output.start()
        self.addCleanup(checkout.stop)
        self.addCleanup(output.stop)

    def test_unregistered_metadata_is_truthfully_blocked(self):
        with patch.object(census, 'REGISTERED_INPUTS', None):
            value = census.sanitize_report(census.coverage(OBSERVED))
        self.assertEqual(value['status'], 'blocked')
        self.assertEqual(value['reason'], 'metadata-not-registered')
        self.assertFalse(value['metadataPinsVerified'])
        self.assertFalse(value['countryCoverageComplete'])
        self.assertIsNone(value['originalAcquiredAt'])
        self.assertEqual(value['cacheFreshness'], 'unknown')

    def test_no_paths_or_payload_fields_can_escape(self):
        value = census.coverage(OBSERVED)
        for key in ('path', 'payload', 'credentials', 'sourceUrl'):
            bad = dict(value, **{key:'private'})
            with self.assertRaises(ValueError):
                census.sanitize_report(bad)
        bad = copy.deepcopy(value)
        bad['reason'] = 'arbitrary-private-error'
        with self.assertRaises(ValueError):
            census.sanitize_report(bad)

    def test_no_network_or_accepted_country_claim(self):
        value = census.coverage(OBSERVED)
        for key, bad_value in [('downloads', 1), ('sourceWrites', 1), ('countryCoverageComplete', True), ('minimumReuseDays', 0), ('originalAcquiredAt', OBSERVED), ('mtimeUsedForFreshness', True)]:
            bad = dict(value, **{key: bad_value})
            with self.assertRaises(ValueError):
                census.sanitize_report(bad)

    def test_unavailable_roots_remain_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(census, 'CACHE', Path(temp)/'missing-cache'), patch.object(census, 'OUTPUT', Path(temp)/'missing-output'):
                value = census.sanitize_report(census.runtime(OBSERVED))
        self.assertEqual(value['status'], 'complete')
        self.assertEqual(value['reason'], 'resource-observation-partial')
        self.assertFalse(value['scopes']['selectedCache']['observed'])
        self.assertFalse(value['effectiveServiceConfigurationVerified'])
        self.assertFalse(value['wholeHostCapacityEstablished'])
        self.assertFalse(value['cgroupAncestorLimitsVerified'])

    def test_resource_nested_fields_are_closed(self):
        value = census.runtime(OBSERVED)
        value['currentCgroupLimits']['hostPath'] = '/private'
        with self.assertRaises(ValueError):
            census.sanitize_report(value)

    def test_no_root_symlink_follow(self):
        with tempfile.TemporaryDirectory() as temp:
            link = Path(temp)/'linked'
            link.symlink_to(Path(temp), target_is_directory=True)
            self.assertFalse(census.space(link)['observed'])

    def test_unregistered_binding_cannot_be_injected(self):
        with patch.object(census, 'REGISTERED_INPUTS', {'matrix':'../../private', 'ledger':'metadata/ledger'}):
            value = census.sanitize_report(census.coverage(OBSERVED))
        self.assertEqual(value['reason'], 'metadata-unavailable-or-invalid')
        self.assertFalse(value['metadataPinsVerified'])

    def test_boundaries_and_observation_are_shared(self):
        steps = dispatch.profile_steps('global-readiness', ROOT)
        commands = {name: command for name, _, command in steps}
        first = commands['global-runtime'][-1]
        second = commands['global-coverage'][-1]
        self.assertEqual(first, second)
        census.observation(first)
        self.assertNotIn('ciqual-native-candidate', commands)
        self.assertNotIn('schema-survey', commands)
        self.assertIn('selected-data-inventory', commands)
        self.assertIn('inventory', commands)
        self.assertIn('replay-idempotency', commands)

    def test_closed_request_profile(self):
        request = {'schemaVersion':1,'jobId':'global-readiness-test-001','profile':'global-readiness'}
        self.assertEqual(dispatch.parse_request(json.dumps(request).encode()), request)
        with self.assertRaises(dispatch.JobError):
            dispatch.parse_request(json.dumps(dict(request, path='/private')).encode())

    def test_blocked_census_does_not_suppress_independent_work(self):
        request = {'schemaVersion':1,'jobId':'global-readiness-test-002','profile':'global-readiness'}
        seen=[]
        def run(step, command, code):
            seen.append(step)
            return {'status':'blocked' if step=='global-coverage' else 'passed',
                    'exitCode':2 if step=='global-coverage' else 0, 'durationSeconds':0,'evidence':{}}
        dispatch.CANCEL_EVENT.clear()
        with patch.object(dispatch, 'run_step', side_effect=run):
            result = dispatch.run_profile(request, 'a'*40, ROOT, '123', '1')
        self.assertEqual(result['status'],'incomplete')
        self.assertIn('global-runtime',seen)
        self.assertIn('selected-data-inventory',seen)
        self.assertIn('inventory',seen)
        self.assertIn('replay-idempotency',seen)
        self.assertEqual(result['maximumParallelChildren'],2)
        self.assertFalse(result['countryCoverageComplete'])

    def test_real_step_normalizes_blocked_metadata(self):
        evidence = {'globalReadiness':census.coverage(OBSERVED)}
        with patch.object(dispatch,'run_child',return_value={'status':'failed','exitCode':2,'durationSeconds':0,'evidence':evidence}):
            value=dispatch.run_step('global-coverage',[],ROOT)
        self.assertEqual(value['status'],'blocked')

    def test_sanitized_evidence_rebinds(self):
        value = census.coverage(OBSERVED)
        result = dispatch.diagnostic_evidence(value)
        self.assertEqual(result['globalReadiness'],value)
        value['private']='never export'
        self.assertEqual(dispatch.diagnostic_evidence(value),{'diagnosticEvidenceError':'invalid-diagnostic-schema'})

    def test_source_profile_has_exact_fixed_step_contract(self):
        # Active-control publisher validation is a separate promotion gate.
        actual=[name for name,_,_ in dispatch.profile_steps('global-readiness',ROOT)]
        self.assertEqual(actual, [
            'readiness', 'global-readiness-tests', 'global-runtime',
            'global-registry-tests', 'global-harness-tests', 'global-coverage',
            'inventory', 'dataset-tests', 'selected-data-inventory',
            'refresh-tests', 'offline-replay', 'replay-idempotency',
        ])

    def test_source_workflow_remains_fail_closed(self):
        text=(ROOT/'.github/workflows/foo-runner.yml').read_text()
        self.assertIn('TRUSTED_CODE_SHA: REPLACE_WITH_REVIEWED_40_CHARACTER_COMMIT_SHA',text)
        self.assertIn("github.repository_id == '1416253963'",text)
        self.assertIn("github.actor_id == '6347545'",text)
        self.assertIn('permissions:\n  contents: read',text)
        # The separately reviewed hosted receipt publisher has a job-local write
        # token. It must never widen the self-hosted Foo execution job's token.
        execution, publisher = text.split('  publish_receipt:', 1)
        self.assertNotIn('contents: write',execution)
        self.assertNotIn('PROFILE_STEPS =',execution)
        choices = execution.split('options: [', 1)[1].split(']', 1)[0].split(', ')
        self.assertIn('global-readiness',choices)
        self.assertIn('runs-on: ubuntu-24.04',publisher)
        self.assertIn('needs: run',publisher)
        self.assertIn('permissions:\n      actions: read\n      contents: write\n      pull-requests: read',publisher)

    def test_incomplete_census_cannot_claim_complete(self):
        value=census.coverage(OBSERVED)
        value.update(status='complete',reason='complete')
        with self.assertRaises(ValueError):
            census.sanitize_report(value)

    def test_harness_summary_contract_and_reconciliation(self):
        from offmenu.refresh import coverage, global_run
        from test_global_coverage import inventory
        report = global_run.run(coverage._reconcile(*inventory()), limits=global_run.Limits(workers=2))
        summary = global_run.compact(report)
        census._summary(summary)
        value=census.coverage(OBSERVED)
        value.update(status='complete', reason='complete', registeredMetadata=True,
                     metadataPinsVerified=True, fullReportRetainedLocally=True, globalSummary=summary)
        self.assertEqual(census.sanitize_report(value)['globalSummary'], summary)
        broken=copy.deepcopy(value)
        broken['globalSummary']['stageStatusCounts']['blocked']+=1
        with self.assertRaises(ValueError):
            census.sanitize_report(broken)
        broken=copy.deepcopy(value)
        broken['globalSummary']['summary']['privateUrl']='never export'
        with self.assertRaises(ValueError):
            census.sanitize_report(broken)

    def test_checkout_registration_is_exact_and_missing_is_blocked(self):
        from offmenu.refresh import coverage
        self.assertEqual(coverage.PINS, {
            'matrix': {'bytes':133210,'sha256':'894e05f09744c76b790f8e5f159141bed6c308a9af3d90c3c82aa79105cf5ea8'},
            'ledger': {'bytes':1701843,'sha256':'2f3c917a6463153824b8c807b41707870e7f763c65b5ff7957ec4988cd96bfcf'},
        })
        self.assertEqual(census.REGISTERED_INPUTS, {
            'matrix':'docs/country-delivery-matrix.json',
            'ledger':'docs/source-delivery-ledger.json'})
        with tempfile.TemporaryDirectory() as directory, patch.object(census, 'TRUSTED_ROOT', Path(directory)):
            result = census.sanitize_report(census.coverage(OBSERVED))
        self.assertEqual(result['reason'], 'metadata-unavailable-or-invalid')
        self.assertEqual(result['metadataOrigin'], 'trusted-code-checkout')
        self.assertFalse(result['datasetCacheCustodyVerified'])
        self.assertIsNone(result['originalAcquiredAt'])

    def test_checkout_symlink_and_pin_mismatch_blocked(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(census, 'TRUSTED_ROOT', Path(directory)):
            docs = Path(directory)/'docs'
            docs.mkdir()
            matrix=docs/'country-delivery-matrix.json'
            ledger=docs/'source-delivery-ledger.json'
            matrix.write_text('{}')
            ledger.write_text('{}')
            mismatch = census.coverage(OBSERVED)
            self.assertEqual(mismatch['reason'], 'metadata-unavailable-or-invalid')
            self.assertFalse(mismatch['metadataPinsVerified'])
            matrix.unlink()
            matrix.symlink_to(ledger)
            with self.assertRaises(ValueError):
                census._registered_paths()
            self.assertEqual(census.coverage(OBSERVED)['reason'], 'metadata-unavailable-or-invalid')

    def test_checkout_synthetic_valid_pins_preserve_cache_unknown(self):
        import hashlib
        from offmenu.refresh import coverage
        from test_global_coverage import inventory
        matrix,ledger=inventory()
        with tempfile.TemporaryDirectory() as directory, patch.object(census,'TRUSTED_ROOT',Path(directory)):
            docs=Path(directory)/'docs'
            docs.mkdir()
            pins={}
            for kind,body,name in [('matrix',matrix,'country-delivery-matrix.json'),('ledger',ledger,'source-delivery-ledger.json')]:
                raw=json.dumps(body).encode()
                (docs/name).write_bytes(raw)
                pins[kind]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
            with patch.object(coverage,'PINS',pins), patch.object(census,'_retain',return_value=True):
                value=census.sanitize_report(census.coverage(OBSERVED))
        self.assertEqual(value['status'],'complete')
        self.assertTrue(value['metadataPinsVerified'])
        self.assertEqual(value['globalSummary']['summary']['sources'],1303)
        self.assertEqual(value['metadataOrigin'],'trusted-code-checkout')
        self.assertFalse(value['datasetCacheCustodyVerified'])
        self.assertIsNone(value['originalAcquiredAt'])
        self.assertEqual(value['cacheFreshness'],'unknown')
        bad=dict(value,datasetCacheCustodyVerified=True)
        with self.assertRaises(ValueError):
            census.sanitize_report(bad)

    def test_timestamps_do_not_accept_free_text(self):
        for invalid in ('2026-10-18', '2026-19-18T00:00:00Z', 'private', None):
            with self.assertRaises(ValueError):
                census.observation(invalid)


if __name__=='__main__':
    unittest.main()

