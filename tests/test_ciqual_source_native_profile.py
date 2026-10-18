import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import core, native_ciqual, survey
from offmenu.refresh.__main__ import main
from offmenu_ciqual import source_native as native
from test_ciqual_source_native import fixture

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_dispatch', ROOT / 'scripts/dispatch-foo-job.py')
jobs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jobs)


class NativeProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blobs, cls.contract = fixture()

    def receipt(self, created=True):
        count = native.contract()['survey']['reconciliation']['intersection']
        return {'schemaVersion': native_ciqual.SCHEMA, 'status': 'private-source-native-extracted',
            'buildKey': 'a' * 64, 'inputBundleSha256': core.sha(core.canonical(native._pins())),
            'counts': {'raw': count, 'extracted': count, 'accepted': None, 'sourceColumns': 84,
                'sourceQuantityColumns': 74, 'infoodsRows': 75, 'duplicates': 0, 'excluded': 0,
                'quarantined': 0, 'qualifiers': {'numeric': count * 74}},
            'created': created, 'artifacts': {name: {'bytes': 100, 'sha256': 'b' * 64} for name in native.OUTPUT_FILES},
            'inputPinsVerified': True, 'readOnlyViewVerified': True, 'sourceContentsUploaded': False,
            'sourceCopies': 0, 'downloads': 0, 'sourceWrites': 0, 'acceptance': 'not-performed',
            'publicExport': 'not-enabled', 'countryCoverageComplete': False, 'freshness': 'unknown',
            'originalAcquiredAt': None, 'minimumReuseDays': 30}

    def test_fixed_profile_and_runtime_qualified_identical_command(self):
        request = {'schemaVersion': 1, 'jobId': 'ciqual-native-test-001', 'profile': 'ciqual-source-native'}
        self.assertEqual(jobs.parse_request(json.dumps(request).encode()), request)
        steps = jobs.profile_steps(request['profile'], ROOT, 'a' * 40)
        self.assertEqual([x[0] for x in steps], ['readiness', 'ciqual-native-tests', 'ciqual-native-candidate', 'ciqual-native-retry'])
        self.assertEqual(steps[-2][2], steps[-1][2])
        self.assertEqual(steps[-1][1], ['ciqual-native-candidate'])
        first = native_ciqual.selected_output('a' * 40)
        self.assertEqual(first.parent, survey.OUTPUT)
        self.assertRegex(first.name, '^ciqual-source-native-a{40}-[0-9a-f]{16}$')
        with patch.object(native_ciqual, 'runtime', return_value={'python': 'different'}):
            self.assertNotEqual(native_ciqual.selected_output('a' * 40), first)
        with self.assertRaises(core.RefreshError):
            native_ciqual.selected_output('../private')
        with self.assertRaises(jobs.JobError):
            jobs.parse_request(json.dumps({**request, 'output': '/tmp/private'}).encode())

    def test_closed_aggregate_export_rejects_records_paths_and_false_claims(self):
        receipt = self.receipt()
        self.assertEqual(jobs.safe_evidence(core.canonical(receipt))['ciqualNative'], receipt)
        mutations = [lambda v: v.update(foodRows=['PRIVATE']),
            lambda v: v['counts'].update(raw=True),
            lambda v: v['counts']['qualifiers'].update(PRIVATE=1),
            lambda v: v['artifacts'].update({'/tmp/private': {'bytes': 1, 'sha256': 'b' * 64}}),
            lambda v: v.update(acceptance='accepted'),
            lambda v: v.update(sourceContentsUploaded=True),
            lambda v: v.update(inputBundleSha256='c' * 64)]
        for mutate in mutations:
            value = copy.deepcopy(receipt)
            mutate(value)
            clean = jobs.safe_evidence(core.canonical(value))
            self.assertNotIn('ciqualNative', clean)
            self.assertNotIn('PRIVATE', json.dumps(clean))
        self.assertLess(len(core.canonical(receipt)), 8192)

    def test_cli_source_failure_keeps_fixed_diagnostic(self):
        with patch.object(native, 'build_selected', side_effect=survey.SurveyError('selected-hash-mismatch')), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(['candidate-ciqual-selected', '--output', str(survey.OUTPUT / 'ciqual-source-native-test')]), 2)
        clean = jobs.safe_evidence(out.getvalue().encode())
        self.assertEqual(clean['errorCode'], 'selected-hash-mismatch')
        self.assertNotIn('ciqualNative', clean)

    def test_actual_fixture_build_and_identical_cli_retry_are_private(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            by_path = {entry[0]: self.blobs[name] for name, entry in survey.ASSETS.items()}
            def read(cache, relative, size, digest):
                self.assertEqual(cache, survey.CACHE)
                return by_path[relative]
            def child(command, code, timeout=240):
                if 'candidate-ciqual-selected' not in command:
                    return {'status': 'passed', 'exitCode': 0, 'durationSeconds': 0, 'evidence': {}}
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    exit_code = main(command[command.index('candidate-ciqual-selected'):])
                return {'status': 'passed' if exit_code == 0 else 'failed', 'exitCode': exit_code,
                        'durationSeconds': 0, 'evidence': jobs.safe_evidence(out.getvalue().encode())}
            with patch.object(survey, 'OUTPUT', output), patch.object(survey, '_read_asset', side_effect=read) as reads, \
                 patch.object(native, 'contract', return_value=copy.deepcopy(self.contract)), \
                 patch.object(native, '_pins', return_value=copy.deepcopy(self.contract['inputPins'])), \
                 patch.object(jobs, 'run_child', side_effect=child):
                report = jobs.run_profile({'schemaVersion': 1, 'jobId': 'native-profile-test-001', 'profile': 'ciqual-source-native'}, 'a' * 40, ROOT, '1', '1')
            self.assertEqual(report['status'], 'passed')
            self.assertEqual(reads.call_count, 18)
            first, repeated = [step['evidence']['ciqualNative'] for step in report['steps'][-2:]]
            self.assertTrue(first['created'])
            self.assertFalse(repeated['created'])
            self.assertEqual(first['artifacts'], repeated['artifacts'])
            self.assertEqual(first['buildKey'], repeated['buildKey'])
            self.assertTrue(report['candidateGenerationEnabled'])
            self.assertFalse(report['corpusAcceptanceEstablished'])
            self.assertFalse(report['countryCoverageComplete'])
            self.assertFalse(report['sourceContentsUploaded'])
            self.assertNotIn('Authored food', json.dumps(report))
            self.assertNotIn('Aliment invent', json.dumps(report))
            candidates = list(output.glob('ciqual-source-native-*'))
            self.assertEqual(len(candidates), 1)
            self.assertEqual({p.name for p in candidates[0].iterdir()}, set(native.OUTPUT_FILES))
            self.assertLess(len(jobs.canonical(report)), jobs.MAX_REPORT)

    def test_retry_must_be_noop_and_every_artifact_must_match(self):
        first = self.receipt()
        repeat = self.receipt(False)
        repeat['artifacts']['normalized.jsonl.gz']['sha256'] = 'c' * 64
        def child(command, code, timeout=240):
            if 'candidate-ciqual-selected' not in command:
                return {'status': 'passed', 'exitCode': 0, 'durationSeconds': 0, 'evidence': {}}
            value = first if not getattr(child, 'seen', False) else repeat
            child.seen = True
            return {'status': 'passed', 'exitCode': 0, 'durationSeconds': 0, 'evidence': {'ciqualNative': value}}
        with patch.object(jobs, 'run_child', side_effect=child):
            report = jobs.run_profile({'schemaVersion': 1, 'jobId': 'native-profile-test-002', 'profile': 'ciqual-source-native'}, 'a' * 40, ROOT, '1', '1')
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['steps'][-1]['errorCode'], 'native-retry-artifacts-changed')
        with patch.object(jobs, 'run_child', return_value={'status': 'passed', 'exitCode': 0, 'durationSeconds': 0, 'evidence': {'ciqualNative': first}}):
            self.assertEqual(jobs.run_step('ciqual-native-retry', [], ROOT)['errorCode'], 'native-idempotency-not-established')
        with patch.object(jobs, 'run_child', return_value={'status': 'passed', 'exitCode': 0, 'durationSeconds': 0, 'evidence': {}}):
            self.assertEqual(jobs.run_step('ciqual-native-candidate', [], ROOT)['errorCode'], 'native-candidate-not-established')


if __name__ == '__main__':
    unittest.main()
