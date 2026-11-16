import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import test_common_expansion_qualification as fixtures
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('resumable',ROOT/'scripts/qualify-common-expansion-resumable.py')
r=importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
r.q.QualificationError=fixtures.qualification.QualificationError

class OriginalChecksResumed(fixtures.CommonExpansionQualificationTests):
    def run_qualification(self,root,*packages):
        while True:
            result=r.qualify(root/'evidence.json',root/'scratch.sqlite',list(packages),20,
                             resume=True,max_steps=1,hash_workers=256,page_rows=1)
            if result['status']!='qualification-paused': return result

class ResumeTests(unittest.TestCase):
    def fixture(self,root):
        a,b=root/'a',root/'b'
        fixtures.make_package(a,[fixtures.packet(resources=[fixtures.resource()])])
        fixtures.make_package(b,[fixtures.packet(assertions=[fixtures.assertion()])])
        return [a,b]
    def test_exact_evidence_except_elapsed(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); dirs=self.fixture(p)
            expected=fixtures.qualification.qualify(p/'original.json',p/'original.sqlite',dirs,20)
            for _ in range(100):
                actual=r.qualify(p/'new.json',p/'new.sqlite',dirs,20,resume=True,max_steps=1,page_rows=1)
                if actual['status']!='qualification-paused': break
                self.assertFalse((p/'new.json').exists())
            expected.pop('seconds'); actual.pop('seconds')
            self.assertEqual(expected,actual)
            result=r.qualify(p/'new.json',p/'new.sqlite',dirs,20,resume=True)
            self.assertEqual(json.loads((p/'new.json').read_text()),result)
    def test_mid_asset_rollback_and_resume(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); dirs=self.fixture(p)
            # first hash then transition into packet phase
            r.qualify(p/'out',p/'db',dirs,20,max_steps=2)
            original=r.workers.merge
            def interrupted(*args):
                original(*args)
                raise r.Paused()
            with patch.object(r.workers,'merge',interrupted):
                self.assertEqual(r.qualify(p/'out',p/'db',dirs,20,resume=True)['status'],'qualification-paused')
            with sqlite3.connect(p/'db') as db:
                self.assertEqual(db.execute('select count(*) from ids').fetchone()[0],0)
                self.assertEqual(db.execute('select count(*) from texts').fetchone()[0],0)
            self.assertEqual(r.qualify(p/'out',p/'db',dirs,20,resume=True)['aggregateObservedCounts']['packets'],2)
    def test_hard_kill_recovers_uncommitted_asset(self):
        import subprocess, sys
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); dirs=self.fixture(p)
            r.qualify(p/'out',p/'db',dirs,20,max_steps=2)
            code = """
import importlib.util,os,signal,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('resume',sys.argv[1])
r=importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
original=r.workers.merge
def kill(*args):
    original(*args)
    os.kill(os.getpid(),signal.SIGKILL)
r.workers.merge=kill
p=Path(sys.argv[2])
r.qualify(p/'out',p/'db',[p/'a',p/'b'],20,resume=True)
"""
            killed=subprocess.run([sys.executable,'-c',code,str(ROOT/'scripts/qualify-common-expansion-resumable.py'),str(p)])
            self.assertEqual(killed.returncode,-9)
            result=r.qualify(p/'out',p/'db',dirs,20,resume=True)
            self.assertEqual(result['database']['ids'],2)
    def test_interrupted_global_page_replayed(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); dirs=self.fixture(p)
            original=r.page
            def interrupted(*args):
                original(*args)
                raise r.Paused()
            with patch.object(r,'page',interrupted):
                result=r.qualify(p/'out',p/'db',dirs,20,page_rows=1)
            self.assertEqual(result['status'],'qualification-paused')
            self.assertFalse((p/'out').exists())
            result=r.qualify(p/'out',p/'db',dirs,20,resume=True,page_rows=1)
            self.assertEqual(result['database']['referencesRecorded'],1)
    def test_runtime_pin_changed(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); dirs=self.fixture(p)
            r.qualify(p/'out',p/'db',dirs,20,max_steps=1)
            with patch.object(r.importlib.metadata,'version',return_value='different'):
                with self.assertRaisesRegex(r.q.QualificationError,'pins changed'):
                    r.qualify(p/'out',p/'db',dirs,20,resume=True)
    def test_unknown_evidence_pending_file_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); dirs=self.fixture(p)
            sentinel=p/'out.pending'; sentinel.write_text('preserve unrelated pending bytes')
            result=r.qualify(p/'out',p/'db',dirs,20)
            self.assertEqual(result['packageCount'],2)
            self.assertEqual(sentinel.read_text(),'preserve unrelated pending bytes')
    def test_pin_changes_fail_closed(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); dirs=self.fixture(p)
            r.qualify(p/'out',p/'db',dirs,20,max_steps=1)
            target=dirs[0]/'manifest.json'; target.write_text(target.read_text()+' ')
            with self.assertRaisesRegex(r.q.QualificationError,'pins changed'):
                r.qualify(p/'out',p/'db',dirs,20,resume=True)
            self.assertFalse((p/'out').exists())
    def test_packet_tamper_after_commit_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); dirs=self.fixture(p)
            r.qualify(p/'out',p/'db',dirs,20,max_steps=3)
            target=dirs[0]/'arbitrary/packet-stream.jsonl.gz'
            with target.open('ab') as f: f.write(b'x')
            with self.assertRaisesRegex(r.q.QualificationError,'pins changed'):
                r.qualify(p/'out',p/'db',dirs,20,resume=True)
    def test_one_coordinator(self):
        import fcntl
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); dirs=self.fixture(p)
            with open(str(p/'db')+'.lock','a+') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with self.assertRaisesRegex(r.q.QualificationError,'another qualification'):
                    r.qualify(p/'out',p/'db',dirs)
    def test_budget_counts_journal(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); db=r.Database(p/'db',10**8,True)
            try:
                Path(str(p/'db')+'-journal').write_bytes(b'x'*100)
                db.scratch_budget_bytes=(p/'db').stat().st_size+50
                with self.assertRaisesRegex(r.q.QualificationError,'including journal'):
                    db.check_budget()
            finally: db.connection.close()
if __name__=='__main__': unittest.main()
