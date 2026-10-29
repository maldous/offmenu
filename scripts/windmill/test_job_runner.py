import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

RUNNER = Path(__file__).with_name('job_runner.py').resolve()

class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()
    def start(self, job, command, mode='write', timeout=8):
        p = subprocess.Popen([sys.executable,str(RUNNER),'--root',str(self.root/'state'),'run','--job-id',job,'--mode',mode,'--timeout',str(timeout)],cwd=self.root,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        p.stdin.write(json.dumps({'command':command}));p.stdin.close();p.stdin=None
        return p
    def finish(self,p):
        out,err=p.communicate(timeout=15)
        self.assertEqual(p.returncode,0,err)
        return json.loads(out)
    def run_job(self,*a,**kw): return self.finish(self.start(*a,**kw))
    def control(self,action,job):
        return json.loads(subprocess.check_output([sys.executable,str(RUNNER),'--root',str(self.root/'state'),action,'--job-id',job],text=True))
    def test_duplicate_once_and_conflict(self):
        r=self.run_job('once','echo x >> count')
        self.assertEqual(r['status'],'succeeded')
        self.assertEqual(self.run_job('once','echo x >> count')['request_sha256'],r['request_sha256'])
        self.assertEqual((self.root/'count').read_text(),'x\n')
        self.assertEqual(self.run_job('once','echo y >> count')['status'],'id_conflict')
    def test_duplicate_running_not_replayed(self):
        p=self.start('live','echo x >> count; sleep 1')
        time.sleep(.2)
        r=self.run_job('live','echo x >> count; sleep 1')
        self.assertIn(r['status'],('starting','running'))
        self.finish(p)
        self.assertEqual((self.root/'count').read_text(),'x\n')
    def test_writers_serialized(self):
        command='mkdir guard || exit 44; sleep .3; rmdir guard'
        a=self.start('writer-a',command);b=self.start('writer-b',command)
        results=[self.finish(a),self.finish(b)]
        self.assertEqual(sorted(r['status'] for r in results),['busy','succeeded'])
        busy=next(r for r in results if r['status']=='busy')
        self.assertFalse(busy['reserved'])
        self.assertEqual(self.run_job(busy['job_id'],command)['status'],'succeeded')
    def test_two_readers_overlap(self):
        a=self.start('reader-a','sleep 1.5','read');b=self.start('reader-b','sleep 1.5','read')
        ar=self.finish(a);br=self.finish(b)
        self.assertLess(max(ar['started_at'],br['started_at']),min(ar['finished_at'],br['finished_at']))
    def test_timeout_detached_descendant_gone(self):
        command="python3 -c 'import os,time; os.setsid(); open(\"child.pid\",\"w\").write(str(os.getpid())); time.sleep(30)' & wait"
        r=self.run_job('timeout',command,timeout=1)
        self.assertEqual(r['status'],'timed_out');self.assertTrue(r['child_tree_gone'])
        pid=int((self.root/'child.pid').read_text())
        with self.assertRaises(ProcessLookupError): os.kill(pid,0)
    def test_cancel_descendant_gone(self):
        p=self.start('cancel','sleep 30 & echo $! > child.pid; wait',timeout=8)
        deadline=time.monotonic()+3
        while not (self.root/'child.pid').exists() and time.monotonic()<deadline:time.sleep(.02)
        self.assertEqual(self.control('cancel','cancel')['status'],'cancellation_requested')
        r=self.finish(p);self.assertEqual(r['status'],'cancelled');self.assertTrue(r['child_tree_gone'])
        pid=int((self.root/'child.pid').read_text())
        with self.assertRaises(ProcessLookupError):os.kill(pid,0)
    def test_bounded_logs(self):
        r=self.run_job('logs',"python3 -c 'import sys;sys.stdout.write(\"x\"*1500000);sys.stderr.write(\"y\"*1500000)'")
        self.assertEqual(r['status'],'succeeded');self.assertTrue(all(r['logs_truncated'].values()))
        self.assertEqual(r['log_bytes'],{'stdout':1048576,'stderr':1048576})
    def test_stale_marker_blocks_writer(self):
        locks=self.root/'state/locks';locks.mkdir(parents=True)
        (locks/'execution-slot-0.inflight.json').write_text(json.dumps({'job_id':'crashed','mode':'write','timeout_seconds':45}))
        r=self.run_job('new','echo no > bad')
        self.assertEqual(r['status'],'blocked_reconciliation')
        self.assertFalse((self.root/'bad').exists())
        self.assertFalse((self.root/'state/jobs/new').exists())
    def test_long_admission_busy_preserves_control(self):
        p=self.start('long','sleep 1.0','read',timeout=60)
        time.sleep(.2)
        began=time.monotonic();r=self.run_job('long2','sleep 1','read',timeout=60)
        self.assertLess(time.monotonic()-began,.8)
        self.assertEqual(r['status'],'busy');self.assertFalse(r['reserved'])
        self.assertIn(self.control('status','long')['status'],('starting','running'))
        self.finish(p)
    def test_unknown_not_replayed(self):
        (self.root/'state/jobs/unknown').mkdir(parents=True)
        r=self.run_job('unknown','echo oops > should-not-exist')
        self.assertEqual(r['status'],'unknown');self.assertFalse((self.root/'should-not-exist').exists())

if __name__=='__main__':unittest.main()
