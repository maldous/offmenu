import base64
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('foo_bootstrap', ROOT / 'scripts/bootstrap-foo-runner.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)

class BootstrapTests(unittest.TestCase):
    def setUp(self):
        p = patch.dict(os.environ, {}, clear=True); p.start(); self.addCleanup(p.stop)
    def args(self, **kw):
        result = dict(apply=True, accept_github_agreement=True, expected_head_sha='a'*40,
                      expected_job_id='foo-bootstrap-test', expected_run_id=42, wait_seconds=30)
        result.update(kw); return SimpleNamespace(**result)
    def diagnostics(self):
        return {'status':'passed','steps':[{'stepId':n,'status':'passed','exitCode':0,'durationSeconds':0} for n in ('preflight','runner-unit-tests','refresh-unit-tests')], 'adminActionsPerformed':False,'registrationAttempted':False}
    def test_default_diagnostics_only(self):
        with tempfile.TemporaryDirectory() as td, patch.object(b.batch,'run_batch',return_value=self.diagnostics()), patch.object(b,'tty_command') as tty, patch.object(b,'gh_json') as gh:
            result=b.run_all(self.args(apply=False),Path(td))
        self.assertEqual(result['status'],'passed'); tty.assert_not_called();gh.assert_not_called()
        self.assertTrue(all(s['status']=='skipped' for s in result['steps'][3:]))
    def test_mutation_failure_report_preserves_diagnostics_and_skips_dependents(self):
        with tempfile.TemporaryDirectory() as td, patch.object(b.batch,'run_batch',return_value=self.diagnostics()), patch.object(b.host,'require_host'), patch.object(b.sys.stdin,'isatty',return_value=True), patch.object(b.sys.stdout,'isatty',return_value=True), patch.object(b.shutil,'which',return_value='/bin/tool'), patch.object(b,'validate_source'), patch.object(b,'check_request',return_value={}), patch.object(b,'tty_command',return_value={}), patch.object(b,'prepare_source',side_effect=OSError('SECRET_PATH')), patch.object(b,'apply_plan') as apply:
            result=b.run_all(self.args(),Path(td))
        self.assertEqual(result['status'],'failed'); self.assertEqual(len(result['steps']),13)
        self.assertTrue(result['adminActionsPerformed']);apply.assert_not_called()
        self.assertNotIn('SECRET_PATH',json.dumps(result));self.assertEqual(result['steps'][-1]['status'],'skipped')
    def test_agreement_required_before_any_mutation(self):
        with tempfile.TemporaryDirectory() as td, patch.object(b.batch,'run_batch',return_value=self.diagnostics()), patch.object(b.host,'require_host'), patch.object(b,'prepare_source') as mutate:
            result=b.run_all(self.args(accept_github_agreement=False),Path(td))
        self.assertEqual(result['steps'][3]['errorCode'],'github-agreement-acceptance-required');mutate.assert_not_called()
    def test_runner_command_never_contains_owner_auth(self):
        with patch.dict(os.environ,{'GH_TOKEN':'DUMMY_SECRET','GITHUB_TOKEN':'DUMMY_SECRET'}):
            command=b.runner_command(b.HELPER,'install')
        self.assertIn('-i',command); self.assertNotIn('DUMMY_SECRET',str(command));self.assertNotIn('GH_TOKEN',str(command))
    def test_registration_tty_is_inherited_not_captured(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ,{'GH_TOKEN':'DUMMY_SECRET'}),patch.object(b.sys.stdin,'isatty',return_value=True),patch.object(b.sys.stdout,'isatty',return_value=True),patch.object(b.subprocess,'run',return_value=subprocess.CompletedProcess([],0)) as run:
            b.tty_command(b.runner_command(b.HELPER,'register'),Path(td),900)
        kw=run.call_args.kwargs
        for key in ('stdout','stderr','stdin','capture_output'):self.assertNotIn(key,kw)
        self.assertNotIn('GH_TOKEN',kw['env'])
    def test_queued_request_and_run_must_match_exact_identity(self):
        request={'schemaVersion':1,'jobId':'foo-bootstrap-test','profile':'smoke'}
        manifest={'encoding':'base64','content':base64.b64encode(json.dumps(request).encode()).decode()}
        run={'id':42,'head_sha':'a'*40,'head_branch':'offmenu-runner-jobs','event':'push','path':b.WORKFLOW}
        with patch.object(b,'gh_json',side_effect=[manifest,[run]]):
            self.assertTrue(b.check_request(self.args(),Path('/tmp'))['requestIdentityVerified'])
        run['head_sha']='b'*40
        with patch.object(b,'gh_json',side_effect=[manifest,[run]]),self.assertRaisesRegex(b.Blocked,'missing-or-ambiguous'):
            b.check_request(self.args(),Path('/tmp'))
    def test_smoke_success_requires_exact_runner(self):
        run={'id':42,'head_sha':'a'*40,'head_branch':'offmenu-runner-jobs','event':'push','path':b.WORKFLOW,'status':'completed','conclusion':'success'}
        with patch.object(b,'gh_json',side_effect=[{'id':7,'name':'foo-offmenu','status':'online'},run,[{'name':'run','runner_id':8,'conclusion':'success'}]]),self.assertRaisesRegex(b.Blocked,'wrong-runner'):
            b.wait_job(self.args(),Path('/tmp'),7)
    def test_gh_only_receives_owner_auth(self):
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'GH_TOKEN':'DUMMY_SECRET'}),patch.object(b.shutil,'which',return_value='/bin/gh'),patch.object(b.subprocess,'run',return_value=subprocess.CompletedProcess([],0,stdout=b'{}')) as run:
            self.assertEqual(b.gh_json('repos/maldous/offmenu/actions/runners/7','{id}',Path(td)),{})
        self.assertEqual(run.call_args.kwargs['env']['GH_TOKEN'],'DUMMY_SECRET')
        self.assertIn('GET',run.call_args.args[0]);self.assertEqual(run.call_args.kwargs['stderr'],subprocess.DEVNULL)
    def test_nonempty_bootstrap_source_refused(self):
        with tempfile.TemporaryDirectory() as td,patch.object(b,'SOURCE',Path(td)),patch.object(b.host,'validate_privileged_destination'):
            Path(td,'existing').touch()
            with self.assertRaisesRegex(b.Blocked,'must-remain-empty'):b.validate_source()
    def test_realistic_systemd_recursive_readonly_bind(self):
        properties = {'User':'offmenu-runner','Group':'offmenu-runner','NoNewPrivileges':'yes',
            'ProtectSystem':'strict','ProtectHome':'tmpfs','PrivateTmp':'yes','PrivateDevices':'yes',
            'CapabilityBoundingSet':'','AmbientCapabilities':'','DropInPaths':'','BindPaths':'',
            'FragmentPath':'/etc/systemd/system/offmenu-runner.service',
            'BindReadOnlyPaths':'/srv/offmenu-bootstrap-input:/srv/offmenu-refresh/cache:rbind',
            'ReadWritePaths':'/srv/offmenu-runner /srv/offmenu-refresh/outputs'}
        with tempfile.TemporaryDirectory() as td, patch.object(b,'tty_command'), patch.object(b,'captured',return_value={'status':'passed'}):
            output=Path(td)/'verify-systemd-properties.stdout'
            def save():output.write_text('\n'.join(k+'='+v for k,v in properties.items()))
            save(); self.assertTrue(b.verify_service(Path(td))['effectiveSandboxVerified'])
            properties['BindReadOnlyPaths']='/wrong:/srv/offmenu-refresh/cache:rbind';save()
            with self.assertRaisesRegex(b.Blocked,'sandbox-mismatch'):b.verify_service(Path(td))
            properties['BindReadOnlyPaths']='/srv/offmenu-bootstrap-input:/srv/offmenu-refresh/cache:rbind'
            properties['BindPaths']='/srv/offmenu-bootstrap-input:/srv/offmenu-refresh/cache:rbind';save()
            with self.assertRaisesRegex(b.Blocked,'sandbox-mismatch'):b.verify_service(Path(td))
    def test_official_archive_service_layout_prepared_without_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/'bin').mkdir(); source=root/'bin/runsvc.sh'
            source.write_bytes(b'#!/bin/sh\nexec ./externals/node24/bin/node ./bin/RunnerService.js\n')
            b.host.prepare_service_entrypoint(root)
            self.assertEqual((root/'runsvc.sh').read_bytes(),source.read_bytes())
            self.assertEqual((root/'runsvc.sh').stat().st_mode & 0o777,0o755)
            with self.assertRaisesRegex(b.host.SetupError,'unexpected-root'):b.host.prepare_service_entrypoint(root)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/'bin').mkdir(); (root/'actual').write_text('unsafe')
            (root/'bin/runsvc.sh').symlink_to(root/'actual')
            with self.assertRaisesRegex(b.host.SetupError,'entrypoint-missing'):b.host.prepare_service_entrypoint(root)
    def test_captured_admin_preserves_session_with_separate_group(self):
        with tempfile.TemporaryDirectory() as td:
            code='import os,json; print(json.dumps({"session":os.getsid(0),"group":os.getpgrp(),"pid":os.getpid()}))'
            result=b.captured('session-check',[os.sys.executable,'-c',code],Path(td))
            state=json.loads((Path(td)/'session-check.stdout').read_text())
        self.assertEqual(result['status'],'passed')
        self.assertEqual(state['session'],os.getsid(0))
        self.assertEqual(state['group'],state['pid'])
        self.assertNotEqual(state['group'],os.getpgrp())
    def test_official_repo_offered_version_pin(self):
        self.assertEqual(b.host.VERSION,'2.337.0')
        self.assertEqual(b.host.ASSETS['x86_64'][1],'70920811a4f8ad4328818682bca5c6469c1c942fab52448868071d0063816613')

if __name__=='__main__':unittest.main()
