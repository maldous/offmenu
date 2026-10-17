import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from offmenu.refresh import survey


class SurveyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def asset(self, raw=b'{"test":1}'):
        path = self.root / 'country' / 'file.json'
        path.parent.mkdir()
        path.write_bytes(raw)
        return path, raw

    def readonly(self):
        return mock.patch.object(survey.os, 'fstatvfs', return_value=SimpleNamespace(f_flag=os.ST_RDONLY))

    def test_exact_nine_asset_selection_excludes_finland_and_has_observed_total(self):
        self.assertEqual(len(survey.ASSETS), 9)
        self.assertFalse(any(key.startswith('FI') for key in survey.ASSETS))
        self.assertEqual(sum(item[1] for item in survey.ASSETS.values()), 30623126)
        self.assertEqual(set(survey.COUNTRIES), {'NO', 'FR'})
        self.assertEqual(survey.BOUNDARIES['originalAcquiredAt'], None)
        self.assertEqual(survey.BOUNDARIES['freshness'], 'unknown')
        self.assertEqual(survey.BOUNDARIES['minimumReuseDays'], 30)

    def test_anchored_pinned_read_and_hash_size_rejection(self):
        _, raw = self.asset()
        with self.readonly():
            self.assertEqual(survey._read_asset(self.root, 'country/file.json', len(raw), survey.sha(raw)), raw)
            with self.assertRaisesRegex(survey.SurveyError, 'selected-hash-mismatch'):
                survey._read_asset(self.root, 'country/file.json', len(raw), '0'*64)
            with self.assertRaisesRegex(survey.SurveyError, 'selected-size-mismatch'):
                survey._read_asset(self.root, 'country/file.json', len(raw)+1, survey.sha(raw))

    def test_writable_mount_rejected_before_payload_read(self):
        _, raw = self.asset()
        with mock.patch.object(survey.os, 'fstatvfs', return_value=SimpleNamespace(f_flag=0)), mock.patch.object(survey.os, 'read') as read:
            with self.assertRaisesRegex(survey.SurveyError, 'selected-view-not-read-only'):
                survey._read_asset(self.root, 'country/file.json', len(raw), survey.sha(raw))
            read.assert_not_called()

    def test_symlinks_hardlinks_and_parent_traversal_are_rejected(self):
        path, raw = self.asset()
        (self.root / 'alias').symlink_to(path.parent, target_is_directory=True)
        with self.readonly():
            with self.assertRaisesRegex(survey.SurveyError, 'selected-path-unsafe'):
                survey._read_asset(self.root, 'alias/file.json', len(raw), survey.sha(raw))
            with self.assertRaises(survey.SurveyError):
                survey._read_asset(self.root, '../country/file.json', len(raw), survey.sha(raw))
            os.link(path, self.root/'hardlink')
            with self.assertRaisesRegex(survey.SurveyError, 'selected-multiple-links'):
                survey._read_asset(self.root, 'country/file.json', len(raw), survey.sha(raw))

    def test_changed_path_after_read_is_rejected(self):
        path, raw = self.asset()
        original = survey.os.read
        changed = False
        def read(fd, count):
            nonlocal changed
            value = original(fd, count)
            if not changed:
                changed = True
                path.write_bytes(raw+b' ')
            return value
        with self.readonly(), mock.patch.object(survey.os, 'read', side_effect=read):
            with self.assertRaisesRegex(survey.SurveyError, 'selected-changed'):
                survey._read_asset(self.root, 'country/file.json', len(raw), survey.sha(raw))

    def test_worker_receipt_gate_precedes_source_and_parser(self):
        with mock.patch.object(survey.os, 'getuid', return_value=1000), mock.patch.object(survey.os, 'geteuid', return_value=1000), mock.patch.object(survey, '_read_asset', side_effect=survey.SurveyError('selected-hash-mismatch')) as read, mock.patch.object(survey, '_module') as module:
            value = survey._worker('NO')
        self.assertEqual(read.call_count, 1)
        self.assertEqual(read.call_args.args[1], 'metadata/national-acquisition.json')
        module.assert_not_called()
        self.assertEqual(value['sourceBodiesSubmitted'], 0)
        self.assertEqual(value['status'], 'held')

    def test_all_pins_verified_before_any_parse_and_no_extra_files_discovered(self):
        value = {'status':'surveyed', 'evidenceComplete': True}
        module = SimpleNamespace(survey=mock.Mock(return_value=value), sanitize_report=lambda x:x)
        with mock.patch.object(survey.os, 'getuid', return_value=1000), mock.patch.object(survey.os, 'geteuid', return_value=1000), mock.patch.object(survey, '_read_asset', return_value=b'{}') as read, mock.patch.object(survey, '_module', return_value=module):
            result = survey._worker('FR')
        self.assertEqual(read.call_count, 4)
        self.assertEqual(set(module.survey.call_args.args[0]), {'Table Ciqual 2025_ENG_2025_11_03.xlsx','alim_2025_11_03.xml'})
        self.assertTrue(result['inputPinsVerified'])
        self.assertEqual(result['sourceBodiesSubmitted'], 2)

    def test_internal_parser_failure_does_not_falsely_report_no_source_read(self):
        module = SimpleNamespace(survey=mock.Mock(side_effect=RuntimeError('private food value')), sanitize_report=lambda x:x)
        with mock.patch.object(survey.os, 'getuid', return_value=1000), mock.patch.object(survey.os, 'geteuid', return_value=1000), mock.patch.object(survey, '_read_asset', return_value=b'{}'), mock.patch.object(survey, '_module', return_value=module):
            result = survey._worker('FR')
        self.assertTrue(result['inputPinsVerified'])
        self.assertEqual(result['sourceBodiesSubmitted'], 2)
        self.assertNotIn('private food value', json.dumps(result))
        self.assertEqual(result['errorCode'], 'survey-internal-error')

    def test_both_country_failures_persist_independently_and_final_is_atomic(self):
        # Test-only output-root and process-result substitution; CLI exposes no
        # source path, input lock, privilege bypass or mock option.
        current_uid = os.getuid()
        def run(country, fd):
            self.assertGreaterEqual(fd, 0)
            return survey._error_country(country, 'selected-hash-mismatch', submitted=0)
        with mock.patch.object(survey, 'OUTPUT', self.root), mock.patch.object(survey.os, 'getuid', return_value=current_uid or 1000), mock.patch.object(survey.os, 'geteuid', return_value=1000), mock.patch.object(survey, '_safe_directory', side_effect=lambda p: (Path(p).mkdir(parents=True, exist_ok=True) or Path(p))), mock.patch.object(survey, '_run_worker', side_effect=run) as worker:
            result = survey.survey_selected(self.root/'runs')
        self.assertEqual([x.args[0] for x in worker.call_args_list], ['NO', 'FR'])
        runpath = self.root/'runs'/result['operationId']
        self.assertTrue((runpath/'NO.json').is_file())
        self.assertTrue((runpath/'FR.json').is_file())
        self.assertEqual(json.loads((runpath/'report.json').read_text()), result)
        self.assertEqual(result['status'], 'held')
        self.assertFalse(result['surveyComplete'])
        self.assertEqual(survey.sanitize_report(result), result)
        changed=copy.deepcopy(result);changed['countries']['NO']['sourceFood']='private'
        with self.assertRaises(ValueError):survey.sanitize_report(changed)
        changed=copy.deepcopy(result);changed['boundaries']['candidateGenerationEnabled']=True
        with self.assertRaises(ValueError):survey.sanitize_report(changed)

    def test_output_is_immutable_and_temp_is_cleaned(self):
        p=self.root/'receipt.json'
        survey._write_new(p, {'safe':1})
        before=p.read_bytes()
        with self.assertRaises(FileExistsError):survey._write_new(p, {'safe':2})
        self.assertEqual(p.read_bytes(), before)
        self.assertEqual(list(self.root.glob('.survey-*')), [])

    def test_cli_cannot_override_source_root_or_lock(self):
        from offmenu.refresh.__main__ import main
        for args in (['survey-selected','--workspace',str(self.root),'--input-root','/tmp'], ['survey-selected','--workspace',str(self.root),'--lock','/tmp/test'], ['survey-selected','--workspace',str(self.root),'--force-refresh']):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):main(args)
        # Foo sets TMPDIR beneath OUTPUT; a temporary directory is not proof
        # that a workspace is outside the allowed output root.
        outside = Path('/offmenu-schema-survey-outside-output-root')
        with mock.patch.object(survey, '_run_worker') as worker, mock.patch.object(survey, '_safe_directory') as directory:
            with self.assertRaisesRegex(survey.SurveyError, 'outside-output-root'):
                survey.survey_selected(outside)
            worker.assert_not_called()
            directory.assert_not_called()

    def test_audit_guard_denies_network_process_and_writes_but_allows_reads(self):
        for event,args in [('socket.connect',()),('subprocess.Popen',()),('ctypes.dlopen',()),('os.mkdir',()),('open',('/tmp','w',os.O_WRONLY)),('open',('/tmp',None,os.O_CREAT))]:
            with self.assertRaises(RuntimeError):survey._audit_guard(event,args)
        survey._audit_guard('open',('/tmp','r',os.O_RDONLY))

    def test_worker_invocation_requires_isolated_fixed_country(self):
        p=Path(survey.__file__)
        for args in (['-B',str(p),'--worker','NO'],['-I','-B',str(p),'--worker','FI'],['-I','-B',str(p),'--worker','NO','/tmp']):
            r=subprocess.run([sys.executable,*args],capture_output=True,timeout=5)
            self.assertEqual(r.returncode,2)
            self.assertEqual(r.stdout,b'')
            self.assertEqual(r.stderr,b'')

    def test_worker_missing_foo_read_only_inputs_returns_safe_held(self):
        # The cloud task has no Foo dataset; do not open source bodies here.
        if survey.CACHE.exists(): self.skipTest('Foo cache exists; test intentionally never reads it')
        r=subprocess.run([sys.executable,'-I','-B',survey.__file__,'--worker','FR'],capture_output=True,timeout=5)
        self.assertEqual(r.returncode,0)
        value=json.loads(r.stdout)
        self.assertEqual(value['status'],'held')
        self.assertIsNone(value['survey'])
        self.assertEqual(r.stderr,b'')
        self.assertNotIn(str(self.root),r.stdout.decode())

    def test_import_parse_and_sanitize_failures_have_distinct_safe_phases(self):
        cases = [
            ('source-import', ModuleNotFoundError('private import path'), None),
            ('source-parse', None, SimpleNamespace(survey=mock.Mock(side_effect=ValueError('private food')), sanitize_report=lambda x:x)),
            ('source-sanitize', None, SimpleNamespace(survey=lambda x:{}, sanitize_report=mock.Mock(side_effect=TypeError('private schema')))),
        ]
        for phase, error, module in cases:
            with self.subTest(phase=phase), mock.patch.object(survey.os,'getuid',return_value=1000), mock.patch.object(survey.os,'geteuid',return_value=1000), mock.patch.object(survey,'_read_asset',return_value=b'{}'), mock.patch.object(survey,'_module',side_effect=error,return_value=module):
                result=survey._worker('FR')
            self.assertEqual(result['diagnostics']['phase'],phase)
            self.assertTrue(result['inputPinsVerified'])
            self.assertNotIn('private',json.dumps(result))
            self.assertEqual(survey.sanitize_country(result,'FR'),result)

    def test_resource_setup_failure_emits_fixed_diagnostic_in_isolated_process(self):
        code = "import sys, resource; sys.path.insert(0, %r); from offmenu.refresh import survey; resource.setrlimit=lambda *a: (_ for _ in ()).throw(ValueError('private resource detail')); sys.argv=[survey.__file__, '--worker', 'FR']; raise SystemExit(survey._worker_main())" % str(survey.ROOT)
        result=subprocess.run([sys.executable,'-I','-B','-c',code],capture_output=True,timeout=5)
        self.assertEqual(result.returncode,2)
        value=json.loads(result.stdout)
        self.assertEqual(value['diagnostics']['phase'],'resource-limits')
        self.assertEqual(value['diagnostics']['exceptionClass'],'ValueError')
        self.assertIsNotNone(value['diagnostics']['resourceLimitsBefore'])
        self.assertEqual(result.stderr,b'')
        self.assertNotIn('private',result.stdout.decode())
        self.assertEqual(survey.sanitize_country(value,'FR'),value)

    def test_parent_preserves_nonzero_exit_and_bounded_transport_counts(self):
        value=survey._error_country('FR','worker-failed',diagnostics=survey._diagnostics('resource-limits',PermissionError(13,'private path')))
        raw=survey.canonical(value)
        code='import os; os.write(1, %r); os.write(2, b"private stderr"); raise SystemExit(7)' % raw
        original=subprocess.Popen
        def launch(command, **kwargs):
            return original([sys.executable,'-I','-B','-c',code],**kwargs)
        with tempfile.TemporaryFile() as lock, mock.patch.object(survey.subprocess,'Popen',side_effect=launch):
            result=survey._run_worker('FR',lock.fileno())
        self.assertEqual(result['diagnostics']['exitCode'],7)
        self.assertEqual(result['diagnostics']['stdoutBytes'],len(raw))
        self.assertEqual(result['diagnostics']['stderrBytes'],len(b'private stderr'))
        self.assertEqual(result['diagnostics']['phase'],'resource-limits')
        self.assertEqual(result['diagnostics']['errno'],13)
        self.assertNotIn('private',json.dumps(result))

    def test_parent_retains_blank_worker_exit_diagnostics(self):
        original=subprocess.Popen
        def launch(command, **kwargs):
            return original([sys.executable,'-I','-B','-c','import os; os.write(2,b"private"); raise SystemExit(9)'],**kwargs)
        with tempfile.TemporaryFile() as lock, mock.patch.object(survey.subprocess,'Popen',side_effect=launch):
            result=survey._run_worker('NO',lock.fileno())
        self.assertEqual(result['diagnostics']['exitCode'],9)
        self.assertEqual(result['diagnostics']['stdoutBytes'],0)
        self.assertEqual(result['diagnostics']['stderrBytes'],7)
        self.assertEqual(result['diagnostics']['phase'],'parent-decode')
        self.assertNotIn('private',json.dumps(result))


if __name__ == '__main__': unittest.main()
