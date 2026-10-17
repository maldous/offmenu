import copy
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
        with patch.dict(os.environ,auth),patch.object(m.subprocess,'Popen',side_effect=child):
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
        with patch.dict(os.environ,{'GITHUB_TOKEN':'CANARY_EXISTING_OWNER_TOKEN','GH_TOKEN':''}),patch.object(m.subprocess,'Popen',side_effect=token_backed_gh):
            m.verified_owner(self.root)
            self.assertEqual('posted',m.publish({'schemaVersion':m.SCHEMA},self.root))
        self.assertEqual(2,len(calls));self.assertEqual('api',calls[0][1]);self.assertEqual(['pr','comment','30'],calls[1][1:4])
        for path in self.root.iterdir():self.assertNotIn(b'CANARY_EXISTING_OWNER_TOKEN',path.read_bytes())

    def test_github_raw_echo_is_memory_only_and_never_logged(self):
        real_popen=subprocess.Popen
        def echo(*args,**kwargs):
            return real_popen([sys.executable,'-I','-c','import sys;print("TOKEN_CANARY");sys.stderr.write("TOKEN_CANARY")'],**kwargs)
        with patch.object(m.subprocess,'Popen',side_effect=echo):
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
            self.assertEqual('uncertain-no-retry',m.publish({'schemaVersion':m.SCHEMA},self.root))
        self.assertEqual(1,capture.call_count)
        args=capture.call_args.args[0]
        self.assertEqual(['/usr/bin/gh','pr','comment','30','--repo','https://github.com/maldous/offmenu','--body-file'],args[:-1])
        self.assertEqual(0o600,Path(args[-1]).stat().st_mode&0o777)

    def test_publish_rejects_over_32k_before_any_post(self):
        with patch.object(m,'capture',side_effect=AssertionError('post')),self.assertRaisesRegex(m.Invalid,'batch-report-limit'):
            m.publish({'large':'x'*32768},self.root)

    def test_auth_mismatch_prevents_sudo_and_projector(self):
        bodies={key:(ROOT/key).read_bytes() for key in m.PINS}
        with patch.object(m.sys,'flags',SimpleNamespace(isolated=1)),patch.object(m.os,'geteuid',return_value=1000),patch.object(m,'verify_checkout',return_value=bodies),patch.object(m,'verified_owner',side_effect=m.Invalid('owner-auth-mismatch')),patch.object(m,'capture',side_effect=AssertionError('child')),patch.object(m.subprocess,'run',side_effect=AssertionError('sudo')),patch.object(m,'publish',side_effect=AssertionError('post')),patch('builtins.print'):
            self.assertEqual(2,m.run('a'*40))

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
        with patch.object(m,'capture',side_effect=AssertionError('subprocess')):
            with self.assertRaises(m.Invalid):m.run('main')
            with patch.object(m.os,'geteuid',return_value=0),self.assertRaises(m.Invalid):m.run('a'*40)

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
        with patch.object(m.sys,'flags',SimpleNamespace(isolated=1)),patch.object(m.os,'geteuid',return_value=1000),patch.object(m,'verify_checkout',return_value=bodies),patch.object(m,'verified_owner'),patch.object(m,'capture',side_effect=captured),patch.object(m.sys.stdin,'isatty',return_value=True),patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=0)),patch.object(m,'publish',side_effect=lambda report,directory:posted.append(report) or 'uncertain-no-retry'),patch('builtins.print'):
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
        with patch.object(m.sys,'flags',SimpleNamespace(isolated=1)),patch.object(m.os,'geteuid',return_value=1000),patch.object(m,'verify_checkout',return_value=bodies),patch.object(m,'verified_owner'),patch.object(m,'capture',side_effect=captured),patch.object(m.sys.stdin,'isatty',return_value=True),patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=0)),patch.object(m,'publish',side_effect=lambda report,directory:posted.append(report) or 'posted'),patch('builtins.print',side_effect=lambda *args,**kwargs:messages.append(str(args))):
            self.assertEqual(124,m.run('a'*40))
        self.assertEqual('unknown-outcome',posted[0]['grant']['status']);self.assertNotIn('SECRET_CANARY',json.dumps(posted))
        self.assertTrue(any('Keep the job queue quiet' in message for message in messages))

    def test_invalid_helper_receipt_keeps_real_exit_and_no_body(self):
        code,calls,posted=self.exercise_run({'exitCode':0,'overflow':False,'stdout':b'{"SECRET_CANARY":1}','outcome':'finished'})
        self.assertEqual(0,code);self.assertEqual('unverified',posted[0]['grant']['status'])
        self.assertNotIn('SECRET_CANARY',json.dumps(posted))


if __name__=='__main__':unittest.main()
