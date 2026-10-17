import copy
import contextlib
import errno
import stat
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
m=module('owner_batch',ROOT/'scripts/run-selected-dataset-grant.py')
grant=module('grant_fixture',ROOT/m.HELPER)
inspector=module('inspector_fixture',ROOT/m.INSPECTOR)
projector=module('projector_fixture',ROOT/m.PROJECTOR)


class OwnerBatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        with patch.object(grant.os,'geteuid',return_value=1000):self.report=grant.run(False)
        self.errors=m.grant_error_codes((ROOT/m.HELPER).read_bytes())
        self.inspect={'sanitize_report':inspector.sanitize_report}
        self.tools={name:{'status':'ready','path':path} for name,path in [('git','/usr/bin/git'),('python','/usr/bin/python3'),('sudo','/usr/bin/sudo'),('gh','/usr/bin/gh')]}

    def test_real_controlled_failure_sanitizes(self):
        result=m.sanitize_grant(self.report,self.inspect,self.errors)
        self.assertEqual('blocked',result['status'])
        self.assertEqual('local-root-required',result['errorCode'])

    def test_sanitizer_canary_unknown_fields_and_values(self):
        changes=[('extra','SECRET_CANARY'),('errorCode','SECRET_CANARY'),('status','SECRET_CANARY'),('sources',{'NO':'SECRET_CANARY','FR':'blocked','FI':'blocked'}),('assets',{'NO_EN_FOODS':'SECRET_CANARY'}),('sourceBytesRead',10**50),('grantVersion',True),('selectedAssets',['SECRET_CANARY']),('snapshotBytesWritten',1),('rollbackRestored','yes'),('snapshotEvidence',{'schemaVersion':'SECRET_CANARY'})]
        for key,value in changes:
            changed=copy.deepcopy(self.report);changed[key]=value
            with self.subTest(key=key),self.assertRaises((m.Invalid,ValueError)):
                m.sanitize_grant(changed,self.inspect,self.errors)

    def test_nested_bad_types_fail(self):
        for key,value in [('assets',[]),('sources',None),('selectedAssets',[[]]),('status',[]),('credentialsRead',1)]:
            changed=copy.deepcopy(self.report);changed[key]=value
            with self.subTest(key=key),self.assertRaises((m.Invalid,ValueError,TypeError)):
                m.sanitize_grant(changed,self.inspect,self.errors)

    def test_service_diagnostics_accept_exact_schema_and_reject_canaries(self):
        props={**grant.BASE_PROPERTIES,'BindReadOnlyPaths':grant.BOOTSTRAP_BIND,'DropInPaths':'','ActiveState':'failed','SubState':'failed','Result':'exit-code','MainPID':'0','ExecMainPID':'123','ExecMainCode':'1','ExecMainStatus':'226','StatusErrno':'13'}
        props['ControlGroup']='/CANARY-SECRET'
        sample=grant.property_evidence(props)
        diagnostic={'failure':sample,'failureSample':'fresh','afterAttempts':2,'afterLastPending':'runtime-activation','afterErrno':2,
                    'failureDetail':{'errorCode':'system-command-failed','errno':None,'command':{'operation':'start','exitCode':1,'errno':None,'timedOut':False}}}
        changed=copy.deepcopy(self.report);changed['serviceDiagnostics']=diagnostic
        self.assertNotIn('CANARY',json.dumps(m.sanitize_grant(changed,self.inspect,self.errors)))
        mutations=[lambda d:d.update(unexpected='CANARY'),
          lambda d:d['failure']['states'].update(Result='CANARY'),
          lambda d:d['failure']['numbers'].update(ExecMainStatus='CANARY'),
          lambda d:d['failure']['numbers'].update(ExecMainStatus=True),
          lambda d:d['failure']['unexpectedValueSha256'].update(ControlGroup='/CANARY'),
          lambda d:d['failure']['properties']['User'].update(match=1),
          lambda d:d['failureDetail']['command'].update(stderr='CANARY'),
          lambda d:d['failureDetail']['command'].update(exitCode=999),
          lambda d:d['failureDetail'].update(errno=True),
          lambda d:d.update(afterAttempts=129),
          lambda d:d.update(afterLastPending='CANARY'),
          lambda d:d.update(failureSample='unavailable')]
        for mutate in mutations:
            bad=copy.deepcopy(diagnostic);mutate(bad)
            with self.assertRaises(m.Invalid):m.sanitize_service_diagnostics(bad,self.errors)

    def test_maximum_service_evidence_stays_within_existing_report_cap(self):
        # Size bound covers four complete snapshots with every checked value
        # unexpected, plus the largest real selected-data evidence shape.
        values={name:'CANARY' for name in grant.PROPERTY_NAMES}
        sample=grant.property_evidence(values)
        changed=copy.deepcopy(self.report)
        changed['serviceDiagnostics']={phase:sample for phase in ('before','after','failure','rollback')}
        fixtures=module('maximum_evidence_fixture',ROOT/'tests/test_selected_dataset_metadata.py')
        fixture=fixtures.SelectedMetadataTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        selection=fixture.fixture()
        with patch.object(inspector,'SELECTION',selection):changed['snapshotEvidence']=inspector.inspect(str(fixture.root))
        detail={'errorCode':'system-command-failed','errno':4096,'command':{'operation':'start','exitCode':255,'errno':4096,'timedOut':True}}
        changed['serviceDiagnostics'].update(afterAttempts=128,rollbackAttempts=128,afterLastPending='read-only-mount-verification-failed',rollbackLastPending='read-only-mount-verification-failed',afterErrno=4096,rollbackErrno=4096,failureDetail=detail,rollbackDetail=detail,failureSample='fresh',rollbackSample='fresh')
        sanitized=m.sanitize_grant(changed,self.inspect,self.errors)
        self.assertLess(len(json.dumps(sanitized).encode()),16384)


    def test_strict_json_duplicate_nonfinite_overflow(self):
        for body in (b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":{"n":1e9999}}'):
            with self.assertRaises(m.Invalid):m.strict_json(body)

    def test_environment_ignores_host_repo_git_token_overrides(self):
        with patch.dict(os.environ,{'GH_HOST':'evil.invalid','GH_REPO':'evil/repo','GH_TOKEN':'SECRET_CANARY','GIT_DIR':'/wrong','PYTHONPATH':'/evil'}):
            env=m.environment()
        self.assertEqual('github.com',env['GH_HOST']);self.assertNotIn('GH_TOKEN',env)
        self.assertNotIn('GH_REPO',env);self.assertNotIn('GIT_DIR',env);self.assertNotIn('PYTHONPATH',env)

    def test_existing_token_auth_only_reaches_fixed_github_child(self):
        real_popen=subprocess.Popen;seen=[]
        def child(args,**kwargs):
            seen.append(kwargs['env'])
            return real_popen([sys.executable,'-I','-c','pass'],**kwargs)
        auth={'GH_TOKEN':'CANARY_GH','GITHUB_TOKEN':'CANARY_GITHUB','GH_CONFIG_DIR':'/owner/config','XDG_CONFIG_HOME':'/owner/xdg','GH_HOST':'evil.invalid','GH_REPO':'evil/repo'}
        with patch.dict(os.environ,auth),patch.object(m.subprocess,'Popen',side_effect=child),patch.object(m,'verify_gh',side_effect=lambda path:path):
            m.capture(['/usr/bin/gh','api','user'],self.root,'gh-env')
            m.capture(['/usr/bin/sudo','-n','true'],self.root,'sudo-env',privileged=True)
            m.capture(['/usr/bin/python3','-I','-S','-B','fixture'],self.root,'projector-env')
            m.capture(['/usr/bin/git','status'],self.root,'git-env')
        for key in ('GH_TOKEN','GITHUB_TOKEN','GH_CONFIG_DIR','XDG_CONFIG_HOME'):
            self.assertEqual(auth[key],seen[0][key])
            self.assertNotIn(key,seen[1]);self.assertNotIn(key,seen[2]);self.assertNotIn(key,seen[3])
        for env in seen:
            self.assertEqual('github.com',env['GH_HOST']);self.assertNotIn('GH_REPO',env)
        for path in self.root.iterdir():self.assertNotIn(b'CANARY',path.read_bytes())

    def test_token_backed_owner_lookup_and_single_post_succeed(self):
        real_popen=subprocess.Popen;calls=[]
        def token_backed_gh(args,**kwargs):
            self.assertEqual('/usr/bin/gh',args[0]);calls.append(args)
            program='import os,json;assert os.environ.get("GITHUB_TOKEN")=="CANARY_EXISTING_OWNER_TOKEN";print(json.dumps({"login":"maldous","id":6347545}))'
            return real_popen([sys.executable,'-I','-c',program],**kwargs)
        with patch.dict(os.environ,{'GITHUB_TOKEN':'CANARY_EXISTING_OWNER_TOKEN','GH_TOKEN':''}),patch.object(m.subprocess,'Popen',side_effect=token_backed_gh),patch.object(m,'verify_gh',side_effect=lambda path:path):
            m.verified_owner(self.root)
            self.assertEqual('posted',m.publish({'schemaVersion':m.SCHEMA},self.root)['status'])
        self.assertEqual(2,len(calls));self.assertEqual('api',calls[0][1]);self.assertEqual(['pr','comment','30'],calls[1][1:4])
        for path in self.root.iterdir():self.assertNotIn(b'CANARY_EXISTING_OWNER_TOKEN',path.read_bytes())

    def test_github_raw_echo_is_memory_only_and_never_logged(self):
        real_popen=subprocess.Popen
        def echo(*args,**kwargs):
            return real_popen([sys.executable,'-I','-c','import sys;print("TOKEN_CANARY");sys.stderr.write("TOKEN_CANARY")'],**kwargs)
        with patch.object(m.subprocess,'Popen',side_effect=echo),patch.object(m,'verify_gh',side_effect=lambda path:path):
            result=m.capture(['/usr/bin/gh','api','user'],self.root,'secret-echo')
        self.assertEqual(b'TOKEN_CANARY\n',result['stdout']);self.assertEqual([],list(self.root.iterdir()))

    def test_owner_login_and_immutable_id_required(self):
        for value,ok in [({'login':'maldous','id':6347545},True),({'login':'maldous','id':1},False),({'login':'other','id':6347545},False)]:
            with patch.object(m,'capture',return_value={'exitCode':0,'overflow':False,'stdout':json.dumps(value).encode()}) as call:
                if ok:m.verified_owner(self.root)
                else:
                    with self.assertRaises(m.Invalid):m.verified_owner(self.root)
                self.assertEqual(['/usr/bin/gh','api','--hostname','github.com','user','--jq','{login: .login, id: .id}'],call.call_args.args[0])

    def test_capture_bounds_private_logs(self):
        result=m.capture([sys.executable,'-I','-c','import sys;sys.stdout.write("x"*100000);sys.stderr.write("y"*100000)'],self.root,'bound',cap=128)
        self.assertEqual(0,result['exitCode']);self.assertTrue(result['overflow'])
        self.assertEqual(128,len(result['stdout']))
        for path in self.root.iterdir():
            self.assertEqual(128,path.stat().st_size);self.assertEqual(0o600,path.stat().st_mode&0o777)

    def test_privileged_capture_preserves_session_with_separate_group(self):
        code='import os,json;print(json.dumps({"session":os.getsid(0),"group":os.getpgrp(),"pid":os.getpid()}))'
        result=m.capture([sys.executable,'-I','-c',code],self.root,'session',privileged=True)
        state=json.loads(result['stdout'])
        self.assertEqual(0,result['exitCode']);self.assertEqual(os.getsid(0),state['session'])
        self.assertEqual(state['pid'],state['group']);self.assertNotEqual(os.getpgrp(),state['group'])

    def test_capture_timeout_nonprivileged_unknown(self):
        result=m.capture([sys.executable,'-I','-c','import time;time.sleep(2)'],self.root,'timeout',timeout=0.02)
        self.assertEqual('unknown',result['outcome']);self.assertIsNone(result['exitCode'])

    def test_pinned_loader_executes_only_matching_bytes_and_arguments(self):
        path=self.root/'small.py';path.write_text('import sys;print(sys.argv[1:])')
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        cmd=[sys.executable,'-I','-B','-c',m.ROOT_LOADER,str(path),digest,'--apply']
        result=subprocess.run(cmd,capture_output=True)
        self.assertEqual(0,result.returncode);self.assertEqual(b"['--apply']\n",result.stdout)
        cmd[-2]='0'*64
        result=subprocess.run(cmd,capture_output=True)
        self.assertNotEqual(0,result.returncode);self.assertEqual(b'',result.stdout)

    def test_privileged_log_write_error_is_unknown_and_child_not_killed(self):
        real_popen=subprocess.Popen;children=[]
        def child(*args,**kwargs):
            proc=real_popen(*args,**kwargs);children.append(proc);return proc
        try:
            with patch.object(m.subprocess,'Popen',side_effect=child),patch.object(m.os,'write',side_effect=OSError('SECRET_CANARY')):
                result=m.capture([sys.executable,'-I','-c','import time;print(1,flush=True);time.sleep(2)'],self.root,'diskfull',privileged=True)
            self.assertEqual('unknown',result['outcome']);self.assertIsNone(result['exitCode']);self.assertIsNone(children[0].poll())
        finally:
            for proc in children:
                if proc.poll() is None:proc.kill()
                proc.wait()

    def test_publish_fixed_target_once_with_private_body(self):
        with patch.object(m,'capture',return_value={'exitCode':None,'overflow':False}) as capture:
            self.assertEqual('uncertain-no-retry',m.publish({'schemaVersion':m.SCHEMA},self.root)['status'])
        self.assertEqual(1,capture.call_count)
        args=capture.call_args.args[0]
        self.assertEqual(['/usr/bin/gh','pr','comment','30','--repo','https://github.com/maldous/offmenu','--body-file'],args[:-1])
        self.assertEqual(0o600,Path(args[-1]).stat().st_mode&0o777)

    def test_publish_rejects_over_32k_before_any_post(self):
        with patch.object(m,'capture',side_effect=AssertionError('post')),self.assertRaisesRegex(m.Invalid,'batch-report-limit'):
            m.publish({'large':'x'*32768},self.root)

    def test_auth_mismatch_prevents_sudo_and_publication(self):
        bodies={key:(ROOT/key).read_bytes() for key in m.PINS}
        with patch.object(m.sys,'flags',SimpleNamespace(isolated=1)),patch.object(m.os,'geteuid',return_value=1000),patch.object(m,'tool_preflight',return_value=self.tools),patch.object(m,'verify_checkout',return_value=bodies),patch.object(m,'verified_owner',side_effect=m.Invalid('owner-auth-mismatch')),patch.object(m,'capture',return_value={'exitCode':2,'overflow':False,'stdout':b'{}','outcome':'finished'}) as captured,patch.object(m.subprocess,'run',side_effect=AssertionError('sudo')),patch.object(m,'publish',side_effect=AssertionError('post')),patch('builtins.print'):
            self.assertEqual(2,m.run('a'*40))
        self.assertEqual(1,captured.call_count);self.assertEqual('/usr/bin/python3',captured.call_args.args[0][0])

    def test_unknown_privileged_child_is_never_killed(self):
        real_popen=subprocess.Popen;children=[];settings=[]
        def child(*args,**kwargs):
            settings.append(kwargs);proc=real_popen(*args,**kwargs);children.append(proc);return proc
        try:
            with patch.object(m.subprocess,'Popen',side_effect=child):
                result=m.capture([sys.executable,'-I','-c','import time;time.sleep(2)'],self.root,'rootlike',timeout=0.02,privileged=True)
            self.assertEqual('unknown',result['outcome']);self.assertIsNone(children[0].poll())
            self.assertFalse(settings[0]['start_new_session'])
            if sys.version_info>=(3,11):self.assertEqual(0,settings[0]['process_group'])
            else:self.assertIs(os.setpgrp,settings[0]['preexec_fn'])
        finally:
            # This is our unprivileged synthetic test process, outside capture.
            for proc in children:
                if proc.poll() is None:proc.kill()
                proc.wait()

    def test_invalid_commit_and_root_block_before_subprocess(self):
        with patch.object(m,'capture',side_effect=AssertionError('subprocess')) as child,patch('builtins.print'):
            self.assertEqual(2,m.run('main'))
            with patch.object(m.os,'geteuid',return_value=0):self.assertEqual(2,m.run('a'*40))
        child.assert_not_called()

    def test_checkout_pins_and_git_tree_bytes(self):
        bodies={key:(ROOT/key).read_bytes() for key in [m.SELF,*m.PINS]}
        for key,body in bodies.items():
            path=self.root/key;path.parent.mkdir(exist_ok=True);path.write_bytes(body)
        def capture(args,*unused,**kwargs):
            body=b'a'*40+b'\n' if args[-1]=='HEAD' else bodies[args[-1].split(':',1)[1]]
            return {'exitCode':0,'overflow':False,'stdout':body}
        with patch.object(m,'capture',side_effect=capture):
            self.assertEqual(bodies,m.verify_checkout(self.root,'a'*40,self.root))
        (self.root/m.HELPER).write_bytes(b'altered')
        with patch.object(m,'capture',side_effect=capture),self.assertRaisesRegex(m.Invalid,'artifact-pin-mismatch'):
            m.verify_checkout(self.root,'a'*40,self.root)

    def exercise_run(self,result):
        bodies={key:(ROOT/key).read_bytes() for key in m.PINS}
        evidence=projector.inspect() if hasattr(projector,'inspect') else projector.inventory()
        calls=[];posted=[]
        def captured(args,*a,**kwargs):
            calls.append(args)
            if args[0]=='/usr/bin/sudo':return result
            return {'exitCode':2,'overflow':False,'stdout':json.dumps(evidence).encode(),'outcome':'finished'}
        with patch.object(m.sys,'flags',SimpleNamespace(isolated=1)),patch.object(m.os,'geteuid',return_value=1000),patch.object(m,'tool_preflight',return_value=self.tools),patch.object(m,'verify_checkout',return_value=bodies),patch.object(m,'verified_owner'),patch.object(m,'capture',side_effect=captured),patch.object(m.sys.stdin,'isatty',return_value=True),patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=0)),patch.object(m,'publish',side_effect=lambda report,directory,gh:posted.append(report) or {'status':'uncertain-no-retry'}),patch('builtins.print'):
            code=m.run('a'*40)
        return code,calls,posted

    def test_independent_projector_runs_and_helper_exit_preserved(self):
        result={'exitCode':2,'overflow':False,'stdout':json.dumps(self.report).encode(),'outcome':'finished'}
        code,calls,posted=self.exercise_run(result)
        self.assertEqual(2,code);self.assertEqual(2,len(calls));self.assertEqual(1,len(posted))
        self.assertEqual('reported',posted[0]['projector']['status']);self.assertEqual('reported',posted[0]['grant']['status'])
        self.assertEqual('/usr/bin/python3',calls[0][0]);self.assertEqual('/usr/bin/sudo',calls[1][0])
        self.assertEqual(['-I','-S','-B','-c'],calls[0][1:5]);self.assertIn('RLIMIT_AS',calls[0][5]);self.assertIn('RLIMIT_CPU',calls[0][5])

    def test_unknown_helper_outcome_not_fabricated_and_no_retry(self):
        code,calls,posted=self.exercise_run({'exitCode':None,'overflow':False,'stdout':b'SECRET_CANARY','outcome':'unknown'})
        self.assertEqual(124,code);self.assertEqual(2,len(calls));self.assertEqual(1,len(posted))
        self.assertEqual('unknown-outcome',posted[0]['grant']['status']);self.assertNotIn('SECRET_CANARY',json.dumps(posted))

    def test_capture_error_after_grant_attempt_stays_unknown(self):
        bodies={key:(ROOT/key).read_bytes() for key in m.PINS};posted=[];messages=[]
        evidence=projector.inspect() if hasattr(projector,'inspect') else projector.inventory()
        def captured(args,*a,**kwargs):
            if args[0]=='/usr/bin/sudo':raise OSError('SECRET_CANARY')
            return {'exitCode':2,'overflow':False,'stdout':json.dumps(evidence).encode(),'outcome':'finished'}
        with patch.object(m.sys,'flags',SimpleNamespace(isolated=1)),patch.object(m.os,'geteuid',return_value=1000),patch.object(m,'tool_preflight',return_value=self.tools),patch.object(m,'verify_checkout',return_value=bodies),patch.object(m,'verified_owner'),patch.object(m,'capture',side_effect=captured),patch.object(m.sys.stdin,'isatty',return_value=True),patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=0)),patch.object(m,'publish',side_effect=lambda report,directory,gh:posted.append(report) or {'status':'posted'}),patch('builtins.print',side_effect=lambda *args,**kwargs:messages.append(str(args))):
            self.assertEqual(124,m.run('a'*40))
        self.assertEqual('unknown-outcome',posted[0]['grant']['status']);self.assertNotIn('SECRET_CANARY',json.dumps(posted))
        self.assertTrue(any('Keep the job queue quiet' in message for message in messages))

    def test_invalid_helper_receipt_keeps_real_exit_and_no_body(self):
        code,calls,posted=self.exercise_run({'exitCode':0,'overflow':False,'stdout':b'{"SECRET_CANARY":1}','outcome':'finished'})
        self.assertEqual(0,code);self.assertEqual('unverified',posted[0]['grant']['status'])
        self.assertNotIn('SECRET_CANARY',json.dumps(posted))


    def invoke(self,**overrides):
        bodies={key:(ROOT/key).read_bytes() for key in m.PINS}
        evidence=projector.inspect() if hasattr(projector,'inspect') else projector.inventory()
        result={'exitCode':2,'overflow':False,'stdout':json.dumps(self.report).encode(),'outcome':'finished','launched':True}
        calls=[];posted=[];messages=[]
        real_mkdtemp=tempfile.mkdtemp
        def captured(args,*a,**kwargs):
            calls.append(args)
            if args[0]=='/usr/bin/sudo':return overrides.get('grant_result',result)
            return {'exitCode':2,'overflow':False,'stdout':json.dumps(evidence).encode(),'outcome':'finished'}
        settings={'tool_preflight':{'return_value':self.tools},'verify_checkout':{'return_value':bodies},
                  'verified_owner':{'return_value':None},'capture':{'side_effect':captured},
                  'publish':{'side_effect':lambda report,directory,gh:posted.append(copy.deepcopy(report)) or {'status':'posted'}}}
        for key in settings:
            if key in overrides:settings[key]=overrides[key]
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(m.sys,'flags',SimpleNamespace(isolated=1)))
            stack.enter_context(patch.object(m.os,'geteuid',return_value=overrides.get('euid',1000)))
            stack.enter_context(patch.object(m.tempfile,'mkdtemp',side_effect=lambda **kw:real_mkdtemp(prefix='batch-',dir=self.root)))
            stack.enter_context(patch.object(m.sys.stdin,'isatty',return_value=overrides.get('tty',True)))
            auth=stack.enter_context(patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=overrides.get('sudo_exit',0))))
            stack.enter_context(patch('builtins.print',side_effect=lambda *a,**kw:messages.append((a,kw))))
            mocks={key:stack.enter_context(patch.object(m,key,**value)) for key,value in settings.items()}
            if 'persist_report' in overrides:stack.enter_context(patch.object(m,'persist_report',**overrides['persist_report']))
            code=m.run(overrides.get('commit','a'*40))
        outcome=json.loads(next(args[0] for args,kw in messages if not kw.get('file')))
        record=next((args[0].removeprefix('Private batch records: ') for args,kw in messages if args[0].startswith('Private batch records: ')),None)
        path=Path(record)/'sanitized-report.json' if record else None
        local=json.loads(path.read_bytes()) if path and path.exists() else None
        self.assertNotIn('SECRET_CANARY',json.dumps([outcome,local,posted,messages],default=str))
        return SimpleNamespace(code=code,outcome=outcome,local=local,calls=calls,posted=posted,auth=auth,mocks=mocks)

    def test_every_runtime_blocker_keeps_sanitized_report(self):
        for kwargs,expected in [({'commit':'SECRET_CANARY'},'invalid-commit'),({'euid':0},'normal-user-isolated-python-required')]:
            with self.subTest(expected=expected):
                got=self.invoke(**kwargs)
                self.assertEqual(2,got.code);self.assertEqual(expected,got.outcome['errorCode'])
                self.assertEqual(expected,got.local['batchBlocker']);self.assertEqual('saved',got.outcome['localReportStatus'])
                got.mocks['verify_checkout'].assert_not_called();got.auth.assert_not_called()

    def test_checkout_failure_keeps_report_and_stops_all_following_children(self):
        got=self.invoke(verify_checkout={'side_effect':OSError(errno.ENOENT,'SECRET_CANARY')})
        self.assertEqual('checkout',got.outcome['phase']);self.assertEqual('io-error',got.outcome['errorCode']);self.assertEqual(errno.ENOENT,got.outcome['errno'])
        self.assertIsNotNone(got.local);got.mocks['capture'].assert_not_called();got.mocks['verified_owner'].assert_not_called();got.auth.assert_not_called();got.mocks['publish'].assert_not_called()

    def test_missing_gh_keeps_independent_projector_and_never_authenticates(self):
        self.tools['gh']={'status':'blocked','path':None,'candidates':[{'path':'/usr/bin/gh','status':'blocked','errorCode':'tool-missing','errno':errno.ENOENT}]}
        got=self.invoke(tty=False)
        self.assertFalse(got.outcome['runtime']['interactiveTerminal'])
        self.assertEqual('gh-unavailable',got.outcome['errorCode']);self.assertEqual('reported',got.local['projector']['status'])
        self.assertEqual('/usr/bin/python3',got.calls[0][0]);self.assertEqual(1,len(got.calls))
        got.mocks['verified_owner'].assert_not_called();got.auth.assert_not_called();got.mocks['publish'].assert_not_called()

    def test_auth_failures_keep_projector_and_sanitized_diagnostics(self):
        for error,expected,number in [(m.Invalid('owner-auth-mismatch'),'owner-auth-mismatch',None),
                                      (m.Invalid('SECRET_CANARY'),'batch-unverified',None),
                                      (OSError(errno.EACCES,'SECRET_CANARY'),'io-error',errno.EACCES)]:
            with self.subTest(expected=expected):
                got=self.invoke(verified_owner={'side_effect':error})
                self.assertEqual(expected,got.outcome['errorCode']);self.assertEqual(number,got.outcome['errno']);self.assertEqual('github-owner',got.outcome['phase'])
                self.assertEqual('reported',got.local['projector']['status']);got.auth.assert_not_called();got.mocks['publish'].assert_not_called()

    def test_noninteractive_and_sudo_auth_failure_keep_report_and_one_publication(self):
        for kwargs,expected in [({'tty':False},'interactive-sudo-required'),({'sudo_exit':1},'sudo-auth-unavailable')]:
            with self.subTest(expected=expected):
                got=self.invoke(**kwargs)
                self.assertEqual(expected,got.outcome['errorCode']);self.assertEqual('not-started',got.local['grant']['status'])
                self.assertEqual('posted',got.local['publication']['status']);self.assertEqual(1,len(got.calls));self.assertEqual(1,len(got.posted))

    def test_projector_invalid_receipt_does_not_block_grant(self):
        results=[{'exitCode':0,'overflow':False,'stdout':b'SECRET_CANARY','outcome':'finished'},
                 {'exitCode':2,'overflow':False,'stdout':json.dumps(self.report).encode(),'outcome':'finished'}]
        got=self.invoke(capture={'side_effect':results})
        self.assertEqual('unverified',got.local['projector']['status']);self.assertEqual('reported',got.local['grant']['status'])
        self.assertEqual('blocked',got.outcome['helperReportStatus']);self.assertEqual('local-root-required',got.outcome['helperErrorCode']);self.assertEqual('grant-blocked',got.outcome['errorCode'])
        self.assertEqual(2,got.mocks['capture'].call_count);self.assertEqual('posted',got.outcome['publication'])

    def test_grant_not_launched_distinguished_from_unknown(self):
        got=self.invoke(grant_result={'exitCode':None,'overflow':False,'stdout':b'','outcome':'not-started','launched':False,'errorCode':'command-launch-failed','errno':errno.ENOENT})
        self.assertEqual(2,got.code);self.assertEqual('not-started',got.local['grant']['status']);self.assertEqual(errno.ENOENT,got.outcome['errno'])
        self.assertEqual('command-launch-failed',got.outcome['errorCode']);self.assertEqual(2,len(got.calls));self.assertEqual(1,len(got.posted))

    def test_successful_applied_receipt_and_real_exit_unchanged(self):
        receipt=copy.deepcopy(self.report)
        receipt.update(status='applied',applied=True,snapshotVerified=True,serviceReady=True,readOnlyMountsVerified=True)
        receipt.pop('errorCode',None)
        got=self.invoke(grant_result={'exitCode':0,'overflow':False,'stdout':json.dumps(receipt).encode(),'outcome':'finished'})
        self.assertEqual(0,got.code);self.assertEqual('reported',got.outcome['grantStatus']);self.assertEqual('applied',got.local['grant']['report']['status'])
        self.assertEqual('posted',got.local['publication']['status']);self.assertEqual(2,len(got.calls));self.assertEqual(1,len(got.posted))

    def test_publication_preparation_failure_keeps_real_grant_and_local_report(self):
        got=self.invoke(publish={'side_effect':OSError(errno.ENOSPC,'SECRET_CANARY')})
        self.assertEqual(2,got.code);self.assertEqual('reported',got.outcome['grantStatus']);self.assertEqual('not-attempted',got.local['publication']['status'])
        self.assertEqual(errno.ENOSPC,got.local['publication']['diagnostic']['errno']);got.mocks['publish'].assert_called_once()

    def test_publication_capture_unknown_is_never_retried(self):
        with patch.object(m,'capture',side_effect=OSError(errno.EIO,'SECRET_CANARY')) as child:
            result=m.publish({'schemaVersion':m.SCHEMA},self.root)
        self.assertEqual('uncertain-no-retry',result['status']);self.assertEqual(errno.EIO,result['diagnostic']['errno']);child.assert_called_once()
        self.assertNotIn('SECRET_CANARY',json.dumps(result))

    def test_publication_proved_not_launched_is_not_attempted(self):
        with patch.object(m,'capture',return_value={'exitCode':None,'overflow':False,'outcome':'not-started','errorCode':'command-launch-failed','errno':errno.ENOENT}) as child:
            result=m.publish({'schemaVersion':m.SCHEMA},self.root)
        self.assertEqual('not-attempted',result['status']);child.assert_called_once()

    def test_persistence_failure_is_explicit_and_does_not_grant(self):
        got=self.invoke(persist_report={'side_effect':OSError(errno.ENOSPC,'SECRET_CANARY')})
        self.assertIsNone(got.local);self.assertEqual('write-failed',got.outcome['localReportStatus']);self.assertEqual('local-report-write-failed',got.outcome['errorCode'])
        self.assertEqual(errno.ENOSPC,got.outcome['errno']);got.auth.assert_not_called();got.mocks['capture'].assert_not_called();got.mocks['publish'].assert_not_called()

    def test_report_final_update_failure_never_repeats_actions(self):
        real=m.persist_report;count=0
        def save(report,directory):
            nonlocal count
            count+=1
            if count==4:raise OSError(errno.ENOSPC,'SECRET_CANARY')
            return real(report,directory)
        got=self.invoke(persist_report={'side_effect':save})
        self.assertEqual('write-failed',got.outcome['localReportStatus']);self.assertEqual('reported',got.outcome['grantStatus']);self.assertEqual('posted',got.outcome['publication'])
        self.assertEqual(2,len(got.calls));self.assertEqual(1,len(got.posted));self.assertEqual('not-attempted',got.local['publication']['status'])

    def test_private_atomic_report_permissions(self):
        m.persist_report({'schemaVersion':m.SCHEMA},self.root)
        path=self.root/'sanitized-report.json'
        self.assertEqual(0o600,stat.S_IMODE(path.stat().st_mode))
        m.persist_report({'schemaVersion':m.SCHEMA,'replacement':True},self.root)
        self.assertTrue(json.loads(path.read_bytes())['replacement']);self.assertEqual([path],list(self.root.iterdir()))

    def test_gh_full_ancestry_ownership_mode_and_symlink_checks(self):
        def trusted(path):
            leaf=str(path).endswith('/gh')
            return SimpleNamespace(st_uid=0,st_mode=(stat.S_IFREG if leaf else stat.S_IFDIR)|0o755,st_nlink=1)
        for bad_path in ('/','/usr','/usr/local','/usr/local/bin','/usr/local/bin/gh'):
            for change in ({'st_uid':1000},{'st_mode':stat.S_IFDIR|0o777},{'st_mode':stat.S_IFLNK|0o755}):
                def info(path):
                    result=trusted(path)
                    if str(path)==bad_path:result.__dict__.update(change)
                    return result
                with self.subTest(path=bad_path,change=change),patch.object(Path,'lstat',info),patch.object(m.os,'access',return_value=True),self.assertRaises(m.Invalid):m.verify_gh('/usr/local/bin/gh')
        with patch.object(Path,'lstat',trusted),patch.object(m.os,'access',return_value=True):
            self.assertEqual('/usr/local/bin/gh',m.verify_gh('/usr/local/bin/gh'))
            with self.assertRaises(m.Invalid):m.verify_gh('/untrusted/gh')

    def test_tool_preflight_fixed_order_fallback_and_no_subprocess(self):
        def gh(path):
            if path=='/usr/bin/gh':raise FileNotFoundError(errno.ENOENT,'SECRET_CANARY')
            return path
        regular=SimpleNamespace(st_mode=stat.S_IFREG|0o755)
        with patch.object(m,'verify_gh',side_effect=gh) as verify,patch.object(m.os,'stat',return_value=regular),patch.object(m.os,'access',return_value=True),patch.object(m.subprocess,'Popen',side_effect=AssertionError('unexpected child')):
            result=m.tool_preflight()
        self.assertEqual(['/usr/bin/gh','/usr/local/bin/gh'],[call.args[0] for call in verify.call_args_list])
        self.assertEqual('/usr/local/bin/gh',result['gh']['path']);self.assertEqual(errno.ENOENT,result['gh']['candidates'][0]['errno']);self.assertNotIn('SECRET_CANARY',json.dumps(result))

    def test_both_gh_paths_use_same_auth_isolation_and_no_raw_files(self):
        real_popen=subprocess.Popen;seen=[]
        def child(args,**kwargs):
            seen.append((args,kwargs['env']))
            return real_popen([sys.executable,'-I','-c','import sys;print("SECRET_CANARY");sys.stderr.write("SECRET_CANARY")'],**kwargs)
        with patch.dict(os.environ,{'GH_TOKEN':'SECRET_CANARY','PATH':'/untrusted'}),patch.object(m,'verify_gh',side_effect=lambda path:path),patch.object(m.subprocess,'Popen',side_effect=child):
            for index,path in enumerate(m.GH_CANDIDATES):m.capture([path,'api','--hostname','github.com','user'],self.root,'gh-'+str(index))
        self.assertEqual(2,len(seen));self.assertEqual([],list(self.root.iterdir()))
        for args,env in seen:self.assertEqual('SECRET_CANARY',env['GH_TOKEN']);self.assertEqual('github.com',env['GH_HOST']);self.assertEqual('/usr/bin:/bin',env['PATH'])

    def test_gh_unsafe_at_launch_never_receives_credentials(self):
        with patch.dict(os.environ,{'GH_TOKEN':'SECRET_CANARY'}),patch.object(m,'verify_gh',side_effect=m.Invalid('tool-unsafe')),patch.object(m.subprocess,'Popen') as child:
            result=m.capture(['/usr/local/bin/gh','api','user'],self.root,'unsafe')
        child.assert_not_called();self.assertEqual('not-started',result['outcome']);self.assertEqual('tool-unsafe',result['errorCode']);self.assertEqual([],list(self.root.iterdir()))

    def test_capture_spawn_error_is_sanitized_and_not_unknown(self):
        with patch.object(m.subprocess,'Popen',side_effect=FileNotFoundError(errno.ENOENT,'SECRET_CANARY')):
            result=m.capture(['/usr/bin/missing'],self.root,'missing')
        self.assertFalse(result['launched']);self.assertEqual('not-started',result['outcome']);self.assertEqual(errno.ENOENT,result['errno'])
        self.assertNotIn('SECRET_CANARY',json.dumps(result,default=str))

    def test_directory_creation_failure_and_invalid_arguments_are_sanitized(self):
        messages=[]
        with patch.object(m.tempfile,'mkdtemp',side_effect=OSError(errno.EACCES,'SECRET_CANARY')),patch('builtins.print',side_effect=lambda *a,**kw:messages.append(a[0])):
            self.assertEqual(2,m.run('a'*40))
        outcome=json.loads(messages[0]);self.assertEqual('local-records-unavailable',outcome['errorCode']);self.assertFalse(outcome['privateLogsRetained']);self.assertEqual('write-failed',outcome['localReportStatus'])
        with patch.object(m.sys,'argv',['wrapper','--SECRET_CANARY']),patch.object(m,'run',return_value=2) as run:
            self.assertEqual(2,m.main())
        run.assert_called_once_with(None,argument_error=True)


    def test_interrupted_constructor_never_claims_no_launch(self):
        real_popen=subprocess.Popen;children=[]
        def interrupted(*args,**kwargs):
            children.append(real_popen([sys.executable,'-I','-c','import time;time.sleep(3)'],**kwargs))
            raise KeyboardInterrupt()
        try:
            with patch.object(m.subprocess,'Popen',side_effect=interrupted):
                result=m.capture(['/usr/bin/sudo','fixture'],self.root,'constructor',privileged=True)
            self.assertEqual('unknown',result['outcome']);self.assertIsNone(result['launched']);self.assertIsNone(result['exitCode']);self.assertIsNone(children[0].poll())
            with patch.object(m,'verify_gh',side_effect=lambda path:path),patch.object(m.subprocess,'Popen',side_effect=interrupted):
                result=m.publish({'schemaVersion':m.SCHEMA},self.root)
            self.assertEqual('uncertain-no-retry',result['status']);self.assertEqual(2,len(children))
        finally:
            for child in children:
                if child.poll() is None:child.kill()
                child.wait()
                for pipe in (child.stdout,child.stderr):
                    if pipe is not None:pipe.close()


    def test_projector_cancellation_never_proceeds_to_auth_or_grant(self):
        for setting in ({'side_effect':KeyboardInterrupt()},
                        {'return_value':{'exitCode':None,'overflow':False,'stdout':b'','outcome':'unknown','errorCode':'command-interrupted'}}):
            with self.subTest(setting=setting):
                got=self.invoke(capture=setting)
                self.assertEqual('interrupted',got.outcome['errorCode']);self.assertEqual('projector',got.outcome['phase'])
                self.assertEqual('unverified',got.local['projector']['status']);self.assertEqual('not-started',got.outcome['grantStatus'])
                got.mocks['verified_owner'].assert_not_called();got.auth.assert_not_called();got.mocks['publish'].assert_not_called();got.mocks['capture'].assert_called_once()


    def test_capture_cleanup_cannot_erase_cancellation(self):
        real_close=os.close
        def close_then_fail(fd):
            real_close(fd)
            raise OSError(errno.EIO,'SECRET_CANARY')
        with patch.object(m.subprocess,'Popen',side_effect=KeyboardInterrupt()),patch.object(m.os,'close',side_effect=close_then_fail):
            result=m.capture(['/usr/bin/python3','fixture'],self.root,'cancel-cleanup')
        self.assertEqual('command-interrupted',result['errorCode']);self.assertEqual('unknown',result['outcome']);self.assertIsNone(result['launched'])
        self.assertNotIn('SECRET_CANARY',json.dumps(result,default=str))


if __name__=='__main__':unittest.main()
