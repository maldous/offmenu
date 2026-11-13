import unittest,tempfile,hashlib,importlib.util,contextlib,io,os,resource
from unittest.mock import patch
from pathlib import Path
s=importlib.util.spec_from_file_location('adapter',Path(__file__).with_name('qualifier_job_adapter.py'));a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
ARGS=['--workers','256','--worker-memory-bytes',str(128*a.MIB),'--tracker-memory-bytes',str(128*a.MIB)]
class Tests(unittest.TestCase):
 def fixture(self,src):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);p=Path(t.name)/'q.py';p.write_text(src);return p,hashlib.sha256(p.read_bytes()).hexdigest()
 def run_source(self,src,args=ARGS):
  p,h=self.fixture(src)
  return a.execute(p,h,args,lambda cap:{'memory_bytes':cap})
 def test_pause(self):
  out=io.StringIO()
  with contextlib.redirect_stdout(out):self.assertEqual(self.run_source('raise SystemExit(75)'),0)
  self.assertIn('EXPECTED_PAUSE',out.getvalue());self.assertIn('false',out.getvalue())
 def test_failures_and_success_preserved(self):
  for n in [0,1,2,74,76]:
   with self.assertRaises(SystemExit)as c:self.run_source(f'raise SystemExit({n})')
   self.assertEqual(c.exception.code,n)
 def test_exception_preserved(self):
  with self.assertRaises(MemoryError):self.run_source('raise MemoryError()')
 def test_pin(self):
  p,h=self.fixture('raise SystemExit(75)')
  with self.assertRaises(ValueError):a.execute(p,'0'*64,ARGS)
 def test_string75_not_mapped(self):
  with self.assertRaises(SystemExit):self.run_source('raise SystemExit("75")')
 def test_translation(self):
  got,tracker=a.translate(ARGS+['--resume','evidence','scratch','package'])
  self.assertEqual(got,['--resume','evidence','scratch','package','--packet-workers','256','--worker-memory-mib','128'])
  self.assertEqual(tracker,128*a.MIB)
 def test_ambiguous_flags_refused(self):
  for extra in [['--workers','2'],['--workers=2'],['--work','2'],['--worker-memory-bytes=134217728'],['--packet-workers','1'],['--packet-w','1'],['--worker-memory-mib','128'],['--tracker-m','134217728']]:
   with self.assertRaises(ValueError):a.translate(ARGS+extra)
 def test_missing_or_bad_budgets(self):
  for args in [[],ARGS[:-2],['--workers','257',*ARGS[2:]],['--workers','1','--worker-memory-bytes','1',*ARGS[4:]]]:
   with self.assertRaises(ValueError):a.translate(args)
 def test_actual_own_tracker_cap(self):
  receipt=a.bound_tracker(128*a.MIB)
  self.assertGreater(receipt['pid'],0)
  self.assertEqual(resource.prlimit(receipt['pid'],resource.RLIMIT_AS),(128*a.MIB,)*2)
 def test_no_foreign_or_current_process_cap(self):
  for pid in (None,-1,os.getpid()):
   with patch.object(a.resource_tracker,'ensure_running'),patch.object(a.resource_tracker._resource_tracker,'_pid',pid),patch.object(a.resource,'prlimit')as cap:
    with self.assertRaises(ValueError):a.bound_tracker(128*a.MIB)
    cap.assert_not_called()
 def test_foreign_or_oversized_pid_refused(self):
  a.resource_tracker.ensure_running()
  for txt in ('PPid:\t1\nState:\tS\nVmSize:\t1000 kB\n',f'PPid:\t{os.getpid()}\nState:\tS\nVmSize:\t9999999 kB\n'):
   with patch('builtins.open',return_value=io.StringIO(txt)),patch.object(a.resource,'prlimit')as cap:
    with self.assertRaises(ValueError):a.bound_tracker(128*a.MIB)
    cap.assert_not_called()
if __name__=='__main__':unittest.main()
