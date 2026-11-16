from test_bulk_control_recovery import *
class BoundedTests(BulkControlRecoveryTests):
 def test_pause_resume_adoption_and_corrupt_tail(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);src=self.source_fixture(root);legacy=root/'legacy';new=root/'new'
   m=repair.read_manifest(src)
   repair.repair_asset(src,legacy,m['files'][0]);repair.repair_asset(src,legacy,m['files'][1])
   tail=legacy/m['files'][2]['key'];tail.write_bytes(b'broken')
   before={p:p.read_bytes() for p in legacy.rglob('*') if p.is_file()}
   for i in range(3):
    r=repair.repair(src,new,workers=1,resume=i>0,max_assets=1,deadline_seconds=10,recover_from=legacy)
    self.assertEqual((new/'manifest.json').exists(),i==2)
   self.assertEqual(before,{p:p.read_bytes() for p in legacy.rglob('*') if p.is_file()})
   c=json.loads((new/'checkpoint.json').read_text());self.assertTrue(c['complete']);self.assertEqual(len(c['recovery']['copied']),2);self.assertEqual(len(c['recovery']['held']),1)
 def test_capacity_pause_never_finalizes(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);src=self.source_fixture(root);out=root/'new'
   r=repair.repair(src,out,workers=1,max_assets=1,reserve_bytes=2**70)
   self.assertEqual(r['status'],'paused-capacity');self.assertFalse((out/'manifest.json').exists())
 def test_wrong_manifest_count_never_finalizes(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);src=self.source_fixture(root);out=root/'new';m=repair.read_manifest(src);m['files'][0]['packets']=2;m['manifestSha256']=repair.manifest_payload_digest(m);(src/'manifest.json').write_text(json.dumps(m))
   with self.assertRaisesRegex(ValueError,'actual repaired packet count'):
    repair.repair(src,out,workers=1,max_assets=1)
   self.assertFalse((out/'manifest.json').exists())
 def test_committed_corruption_fails_closed(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);src=self.source_fixture(root);out=root/'new';repair.repair(src,out,workers=1,max_assets=1)
   p=out/'packets/part-00000.jsonl.gz';p.write_bytes(b'changed')
   with self.assertRaisesRegex(ValueError,'committed asset bytes changed'):
    repair.repair(src,out,workers=1,max_assets=1,resume=True)
   self.assertEqual(p.read_bytes(),b'changed')
 def test_stale_temp_is_preserved_and_requires_reconciliation(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);src=self.source_fixture(root);out=root/'new';repair.repair(src,out,workers=1,max_assets=1)
   stale=out/'checkpoint.json.writing.old';stale.write_text('held')
   with self.assertRaisesRegex(ValueError,'unreconciled output'):
    repair.repair(src,out,workers=1,max_assets=1,resume=True)
   self.assertEqual(stale.read_text(),'held')
 def test_deadline_preflight_does_not_create_output(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);src=self.source_fixture(root);out=root/'new'
   r=repair.repair(src,out,workers=1,max_assets=1,deadline_seconds=0.000000001)
   self.assertEqual(r['status'],'paused-verification');self.assertFalse(out.exists())
 def test_explicit_representatives_require_all_sources(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);src=self.source_fixture(root);out=root/'new'
   with self.assertRaisesRegex(ValueError,'all three'):
    repair.repair(src,out,workers=1,max_assets=1,representative_keys=['packets/part-00000.jsonl.gz'])
   self.assertFalse(out.exists())
