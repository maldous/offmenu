import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

P=Path(__file__).resolve().parents[1]/'scripts/run-owner-manifest-metadata.py'
spec=importlib.util.spec_from_file_location('owner_batch',P)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def answer(value,code=0):
    return {'exitCode':code,'outcome':'finished','overflow':False,'errno':None,'stdout':json.dumps(value).encode()}

class BatchTests(unittest.TestCase):
    def harness(self,tmp):
        from contextlib import ExitStack
        stack=ExitStack(); self.addCleanup(stack.close)
        for name in ('getuid','geteuid'):stack.enter_context(patch.object(m.os,name,return_value=1000))
        stack.enter_context(patch.object(m.pwd,'getpwnam',return_value=SimpleNamespace(pw_uid=1000)))
        stack.enter_context(patch.object(m.sys,'flags',SimpleNamespace(isolated=1)))
        stack.enter_context(patch.object(m.tempfile,'mkdtemp',return_value=tmp))
        stack.enter_context(patch.object(m,'read_collector',return_value=lambda:{'status':'collected','metadata':{}}))
        stack.enter_context(patch.object(m,'discover_gh',return_value='/usr/local/bin/gh'))
        return stack

    def test_pinned_collector_loads(self):
        self.assertTrue(callable(m.read_collector()))

    def test_success_private_receipt_and_exact_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            stack=self.harness(tmp)
            capture=stack.enter_context(patch.object(m,'capture',side_effect=[
                answer({'login':'maldous','id':6347545}),answer({'full_name':'maldous/offmenu','private':True}),
                answer({'id':1,'html_url':'https://github.com/maldous/offmenu/pull/30#issuecomment-1'})]))
            report,directory=m.run('a'*40)
            self.assertEqual(report['publication']['status'],'posted')
            self.assertFalse(report['actionsCompletionSignal'])
            self.assertEqual(capture.call_count,3)
            self.assertEqual(capture.call_args.args[0][4],m.COMMENT)
            self.assertEqual(os.stat(directory/'receipt.json').st_mode&0o777,0o600)
            self.assertEqual(os.stat(directory).st_mode&0o777,0o700)
            self.assertEqual(json.loads((directory/'receipt.json').read_bytes())['reportId'],report['reportId'])

    def test_uncertain_publication_never_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            stack=self.harness(tmp)
            bad={'exitCode':None,'outcome':'unknown','overflow':False,'errno':None,'stdout':b'SECRET'}
            capture=stack.enter_context(patch.object(m,'capture',side_effect=[answer({'login':'maldous','id':6347545}),answer({'full_name':'maldous/offmenu','private':True}),bad]))
            report,directory=m.run('a'*40)
            self.assertEqual(report['publication']['status'],'uncertain-no-retry')
            self.assertEqual(capture.call_count,3)
            self.assertNotIn('SECRET',(directory/'receipt.json').read_text())

    def test_owner_mismatch_preserves_collection_without_post(self):
        with tempfile.TemporaryDirectory() as tmp:
            stack=self.harness(tmp)
            capture=stack.enter_context(patch.object(m,'capture',return_value=answer({'login':'other','id':2})))
            report,directory=m.run('a'*40)
            self.assertEqual(report['errorCode'],'owner-auth-mismatch')
            self.assertTrue((directory/'collection.json').exists())
            self.assertEqual(capture.call_count,1)
            self.assertEqual(report['publication']['status'],'not-attempted')

    def test_public_repository_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            stack=self.harness(tmp)
            capture=stack.enter_context(patch.object(m,'capture',side_effect=[answer({'login':'maldous','id':6347545}),answer({'full_name':'maldous/offmenu','private':False})]))
            report,directory=m.run('a'*40)
            self.assertEqual(report['errorCode'],'repository-identity-mismatch')
            self.assertEqual(capture.call_count,2)

    def test_missing_gh_still_preserves_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            stack=self.harness(tmp)
            stack.enter_context(patch.object(m,'discover_gh',side_effect=m.Blocked('gh-unavailable')))
            report,directory=m.run('a'*40)
            self.assertEqual(report['errorCode'],'gh-unavailable')
            self.assertTrue((directory/'collection.json').exists()); self.assertTrue((directory/'receipt.json').exists())

    def test_invalid_commit_rejected(self):
        for value in ('main','a'*39,'../secret','A'*40):
            with self.assertRaises(m.Blocked):m.run(value)

    def test_capture_real_command_bounds_and_stderr_suppression(self):
        # Only local, non-privileged Python fixtures; never gh or networking.
        import sys
        with patch.object(m,'environment',return_value={'PATH':'/usr/bin:/bin'}):
            result=m.capture([sys.executable,'-c','import sys; print("ok"); print("secret",file=sys.stderr)'])
            self.assertEqual(result['exitCode'],0); self.assertEqual(result['stdout'],b'ok\n')
            result=m.capture([sys.executable,'-c','print("x"*10000)'],cap=100)
            self.assertTrue(result['overflow']); self.assertEqual(len(result['stdout']),100)
            result=m.capture([sys.executable,'-c','import time;time.sleep(10)'],timeout=0.01)
            self.assertEqual(result['outcome'],'unknown'); self.assertIsNone(result['exitCode'])

if __name__=='__main__':unittest.main()
