from test_bulk_control_recovery import *
sys.modules['bulk_repair']=repair

class ParallelTests(BulkControlRecoveryTests):
 def test_bounded_parallel_pauses_and_finishes(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);src=self.source_fixture(root);out=root/'out'
   first=repair.repair(src,out,workers=2,max_assets=2,deadline_seconds=10)
   self.assertFalse(first['complete']);self.assertEqual(first['completedAssets'],2);self.assertFalse((out/'manifest.json').exists())
   second=repair.repair(src,out,workers=2,max_assets=2,deadline_seconds=10,resume=True)
   self.assertTrue((out/'manifest.json').exists());self.assertEqual(second['repair']['changedPackets'],3)
 def test_parallel_matches_serial_bytes(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);src=self.source_fixture(root);one=root/'one';many=root/'many'
   repair.repair(src,one,workers=1,max_assets=10);repair.repair(src,many,workers=2,max_assets=10)
   for entry in repair.read_manifest(src)['files']:self.assertEqual((one/entry['key']).read_bytes(),(many/entry['key']).read_bytes())
 def test_worker_deadline_never_publishes(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);src=self.source_fixture(root);out=root/'out';entry=repair.read_manifest(src)['files'][0]
   with self.assertRaises(repair.BudgetPause):repair.repair_asset(src,out,entry,deadline=0)
   self.assertFalse(out.exists())
 def test_parallel_capacity_does_not_finalize(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);src=self.source_fixture(root);out=root/'out'
   r=repair.repair(src,out,workers=2,max_assets=2,reserve_bytes=2**70)
   self.assertEqual(r['status'],'paused-capacity');self.assertFalse((out/'manifest.json').exists())
 def test_parallel_refuses_unreconciled_legacy_candidates(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);src=self.source_fixture(root);legacy=root/'legacy';out=root/'out';entry=repair.read_manifest(src)['files'][0]
   repair.repair_asset(src,legacy,entry)
   with self.assertRaisesRegex(ValueError,'reconciled serially'):repair.repair(src,out,workers=2,max_assets=2,recover_from=legacy)
 def test_midasset_deadline_removes_only_own_temporary(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);src=self.source_fixture(root);out=root/'out';entry=repair.read_manifest(src)['files'][0]
   data=gzip.compress(((json.dumps(packet())+'\n')*3).encode(),mtime=0);(src/entry['key']).write_bytes(data)
   entry.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),packets=3)
   with patch.object(repair.time,'monotonic',side_effect=[0,0,2]):
    with self.assertRaises(repair.BudgetPause):repair.repair_asset(src,out,entry,deadline=1)
   self.assertFalse((out/entry['key']).exists());self.assertFalse(list(out.rglob('*.tmp.*')))
 def test_parallel_orphan_reconciles_before_resume(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);src=self.source_fixture(root);out=root/'out'
   repair.repair(src,out,workers=1,max_assets=1)
   entry=repair.read_manifest(src)['files'][1];repair.repair_asset(src,out,entry)
   before=(out/entry['key']).read_bytes()
   repair.repair(src,out,workers=2,max_assets=1,resume=True)
   self.assertEqual(before,(out/entry['key']).read_bytes());self.assertTrue((out/'manifest.json').exists())
 def test_parallel_reserves_all_inflight_assets(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);src=self.source_fixture(root);out=root/'out'
   # Each asset reserves64MiB; a70MiBoutput allowance permits only one in flight.
   r=repair.repair(src,out,workers=2,max_assets=3,maximum_output_bytes=70*1024**2)
   self.assertFalse(r['complete']);self.assertEqual(r['submittedAssets'],1);self.assertEqual(r['completedAssets'],1)
   self.assertFalse((out/'manifest.json').exists())
