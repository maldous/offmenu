"""Proof-backed cgroup-v2 observations, synthetic only; no controller writes."""
from pathlib import Path
import importlib.util,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('resource_global',ROOT/'scripts/collect-fixed-global.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
class ResourceTests(unittest.TestCase):
 def files(self):
  return {'/proc/self/cgroup':'0::/user.slice/session.scope','/proc/self/mountinfo':'29 23 0:26 / /sys/fs/cgroup rw - cgroup2 cgroup rw','/proc/meminfo':'MemAvailable: 58720256 kB','/sys/fs/cgroup/user.slice/cgroup.subtree_control':'','/sys/fs/cgroup/user.slice/cpu.max':'400000 100000','/sys/fs/cgroup/user.slice/memory.max':str(16*1024**3),'/sys/fs/cgroup/user.slice/memory.current':str(4*1024**3)}
 def observe(self,files):
  def read(path):
   if path not in files:raise FileNotFoundError(path)
   value=files[path]
   if isinstance(value,Exception):raise value
   return value
  with patch.object(g.os,'cpu_count',return_value=32),patch.object(g.os,'sched_getaffinity',return_value=set(range(32))):return g.effective_resources(g.DEFAULT_PARALLELISM,read)
 def test_legitimate_disabled_leaf_uses_real_ancestor_limits(self):
  r=self.observe(self.files());self.assertFalse(r['resourceLimitsIncomplete']);self.assertEqual(r['effectiveCPUs'],4);self.assertEqual(r['effectiveMemoryBytes'],12*1024**3);self.assertEqual(r['preparationWorkers'],4)
  d=r['diagnostics'];self.assertEqual(d['disabledCPUInterfaces'],1);self.assertEqual(d['disabledMemoryInterfaces'],1);self.assertEqual(d['rootExemptInterfaces'],2);self.assertEqual(d['problemCodes'],[]);g.validate_resource_diagnostics(d)
 def test_disabled_across_two_levels_still_uses_tight_ancestor(self):
  f=self.files();f['/proc/self/cgroup']='0::/user.slice/session.scope/child';f['/sys/fs/cgroup/user.slice/session.scope/cgroup.subtree_control']='';r=self.observe(f);self.assertEqual(r['preparationWorkers'],4);self.assertEqual(r['diagnostics']['disabledCPUInterfaces'],2)
 def test_enabled_parent_missing_child_is_unknown(self):
  f=self.files();f['/sys/fs/cgroup/user.slice/cgroup.subtree_control']='cpu memory';r=self.observe(f);self.assertTrue(r['resourceLimitsIncomplete']);self.assertEqual(r['preparationWorkers'],0);self.assertEqual(r['diagnostics']['problemCodes'],['cpu-limit-unresolved','memory-limit-unresolved'])
 def test_denied_child_never_means_disabled(self):
  f=self.files();f['/sys/fs/cgroup/user.slice/session.scope/cpu.max']=PermissionError();r=self.observe(f);self.assertEqual(r['preparationWorkers'],0);self.assertIn({'interface':'cpu-limit','state':'permission-denied','count':1},r['diagnostics']['readFailures'])
 def test_denied_or_malformed_parent_is_unknown(self):
  for value in (PermissionError(),'cpu +memory','not/controller'):
   f=self.files();f['/sys/fs/cgroup/user.slice/cgroup.subtree_control']=value;r=self.observe(f);self.assertEqual(r['preparationWorkers'],0);self.assertTrue(r['resourceLimitsIncomplete'])
 def test_hidden_delegated_parent_cannot_prove_unconstrained(self):
  f=self.files();f['/proc/self/mountinfo']='29 23 0:26 /user.slice/session.scope /sys/fs/cgroup rw - cgroup2 cgroup rw';r=self.observe(f);self.assertEqual(r['preparationWorkers'],0);self.assertEqual(r['diagnostics']['rootExemptInterfaces'],0)
 def test_tight_known_ancestor_and_missing_ancestor_remain_conservative(self):
  f=self.files();f['/sys/fs/cgroup/user.slice/memory.max']=str(3*1024**3);f['/sys/fs/cgroup/user.slice/memory.current']=str(2*1024**3);r=self.observe(f);self.assertEqual(r['effectiveMemoryBytes'],1024**3);self.assertEqual(r['preparationWorkers'],0)
  f=self.files();f['/sys/fs/cgroup/user.slice/cpu.max']=PermissionError();r=self.observe(f);self.assertEqual(r['preparationWorkers'],0);self.assertTrue(r['resourceLimitsIncomplete'])
 def test_diagnostics_are_closed_and_do_not_include_paths(self):
  r=self.observe(self.files());self.assertNotIn('/sys/',repr(r['diagnostics']));d=r['diagnostics'];d['path']='/private'
  with self.assertRaises(ValueError):g.validate_resource_diagnostics(d)
 def test_invalid_unlimited_cpu_period_is_unknown(self):
  f=self.files();f['/sys/fs/cgroup/user.slice/cpu.max']='max not-a-period';r=self.observe(f);self.assertEqual(r['preparationWorkers'],0);self.assertIn('cpu-limit-unresolved',r['diagnostics']['problemCodes'])
 def test_oversized_observation_stays_unknown(self):
  f=self.files();f['/proc/self/cgroup']='x'*65537;r=self.observe(f);self.assertTrue(r['resourceLimitsIncomplete']);self.assertEqual(r['preparationWorkers'],0);self.assertIn({'interface':'membership','state':'invalid','count':1},r['diagnostics']['readFailures'])
 def test_hybrid_unresolved_v1_cpu_remains_unknown(self):
  f=self.files();f['/proc/self/cgroup']+='\n2:cpu:/group';r=self.observe(f);self.assertTrue(r['resourceLimitsIncomplete']);self.assertEqual(r['preparationWorkers'],0);self.assertIn('controller-mount-unresolved',r['diagnostics']['problemCodes'])
 def test_hybrid_resolved_v1_restrictive_limit_is_retained(self):
  f=self.files();f['/proc/self/cgroup']+='\n2:cpu:/group';f['/proc/self/mountinfo']+='\n30 23 0:27 / /sys/fs/cgroup/cpu rw - cgroup cgroup rw,cpu'
  f.update({'/sys/fs/cgroup/cpu/group/cpu.cfs_quota_us':'100000','/sys/fs/cgroup/cpu/group/cpu.cfs_period_us':'100000','/sys/fs/cgroup/cpu/cpu.cfs_quota_us':'-1','/sys/fs/cgroup/cpu/cpu.cfs_period_us':'100000'})
  r=self.observe(f);self.assertFalse(r['resourceLimitsIncomplete']);self.assertEqual(r['effectiveCPUs'],1);self.assertEqual(r['preparationWorkers'],1)
if __name__=='__main__':unittest.main()
