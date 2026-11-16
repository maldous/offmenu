import importlib.util,json,sqlite3,tempfile,unittest
from pathlib import Path
import test_resumable as t
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
migration=module('migration',ROOT/'scripts/migrate_qualification_parallel.py')
old=module('old_qualifier',ROOT.parent/'qualification-resume-20261028/scripts/qualify-common-expansion-resumable.py')
class ParallelTests(unittest.TestCase):
 def test_cross_asset_duplicate_resource(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
   p=Path(tmp);a,b=p/'a',p/'b'
   for d in (a,b): t.fixtures.make_package(d,[t.fixtures.packet(resources=[t.fixtures.resource()])])
   with self.assertRaisesRegex(t.r.q.QualificationError,'duplicate global resource'):
    t.r.qualify(p/'out',p/'db',[a,b],20)
   self.assertFalse((p/'out').exists())
 def test_cross_asset_conflicting_text(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
   p=Path(tmp);a,b=p/'a',p/'b'
   for i,d in enumerate((a,b)):
    t.fixtures.make_package(d,[t.fixtures.packet(resources=[t.fixtures.resource(f'urn:test:r{i}',t.fixtures.text(value=str(i)))])])
   with self.assertRaisesRegex(t.r.q.QualificationError,'repeated text id'):
    t.r.qualify(p/'out',p/'db',[a,b],20)
 def test_cross_asset_conflicting_citation(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
   p=Path(tmp);a,b=p/'a',p/'b'
   for i,d in enumerate((a,b)):
    packet=t.fixtures.packet(resources=[t.fixtures.resource(f'urn:test:r{i}')]);packet['citations'][0]['attribution']=str(i)
    t.fixtures.make_package(d,[packet])
   with self.assertRaisesRegex(t.r.q.QualificationError,'repeated citation id'):
    t.r.qualify(p/'out',p/'db',[a,b],20)
 def test_journaled_migration_keeps_all_committed_work(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
   p=Path(tmp);a,b=p/'a',p/'b'
   t.fixtures.make_package(a,[t.fixtures.packet(resources=[t.fixtures.resource()])])
   t.fixtures.make_package(b,[t.fixtures.packet(assertions=[t.fixtures.assertion()])])
   old.qualify(p/'out',p/'db',[a,b],20,max_steps=3)
   with sqlite3.connect(p/'db') as db:
    before=db.execute('SELECT value FROM checkpoint').fetchone()[0]
    rows=db.execute('SELECT * FROM ids').fetchall()
   self.assertFalse(migration.migrate(p/'db')['applied'])
   migration.migrate(p/'db',True,t.r.q.sha_file(ROOT/'scripts/qualify-common-expansion-resumable.py'),
                     t.r.q.sha_file(ROOT/'scripts/qualification_asset_workers.py'))
   with sqlite3.connect(p/'db') as db:
    self.assertEqual(db.execute('SELECT value FROM checkpoint').fetchone()[0],before)
    self.assertEqual(db.execute('SELECT * FROM ids').fetchall(),rows)
    self.assertEqual(db.execute('SELECT count(*) FROM implementation_migrations').fetchone()[0],1)
   result=t.r.qualify(p/'out',p/'db',[a,b],20,resume=True)
   expected=old.qualify(p/'original.json',p/'original.db',[a,b],20)
   for x in (result,expected): x.pop('seconds')
   self.assertEqual(result,expected)
 def test_migration_rejects_unknown_implementation(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
   p=Path(tmp);a=p/'a';t.fixtures.make_package(a,[t.fixtures.packet(resources=[t.fixtures.resource()])])
   t.r.qualify(p/'out',p/'db',[a],20,max_steps=1)
   with self.assertRaisesRegex(ValueError,'exact reviewed sequential'):
    migration.migrate(p/'db',True)
 def test_initializer_failure_is_bounded_no_respawn(self):
  import time
  from concurrent.futures.process import BrokenProcessPool
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
   p=Path(tmp);a=p/'a';t.fixtures.make_package(a,[t.fixtures.packet(resources=[t.fixtures.resource()])])
   entry=json.loads((a/'manifest.json').read_text())['files'][0]
   start=time.monotonic()
   pipeline=t.r.workers.Pipeline(p,[(a/entry['key'],entry)],b'invalid-schema-json',b'{}',time.monotonic()+30,1,0,1024**2,1024**2)
   try:
    with self.assertRaises(BrokenProcessPool): pipeline.take(t.r.Clock(30))
   finally:pipeline.close()
   self.assertLess(time.monotonic()-start,10)
 def test_cancel_closes_owned_workers(self):
  import time
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
   p=Path(tmp);a=p/'a';t.fixtures.make_package(a,[t.fixtures.packet(resources=[t.fixtures.resource()])])
   entry=json.loads((a/'manifest.json').read_text())['files'][0]
   pipeline=t.r.workers.Pipeline(p,[(a/entry['key'],entry)]*2,
      (ROOT/'corpus/common-data.schema.json').read_bytes(),(ROOT/'corpus/common-data-contract.json').read_bytes(),
      time.monotonic()+30,2,128*1024**2,1024**2,2*1024**2)
   processes=list(pipeline.pool._processes.values())
   try:
    with self.assertRaises(t.r.Paused):pipeline.take(t.r.Clock(0))
   finally:pipeline.close()
   self.assertTrue(all(not child.is_alive() for child in processes))
 def test_preserved_orphan_shards_count_toward_budget(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
   p=Path(tmp);db=t.r.Database(p/'db',10**8,True)
   try:
    other=p/'db.shards-old';other.mkdir();(other/'retained').write_bytes(b'x'*100)
    db.scratch_budget_bytes=(p/'db').stat().st_size+50
    with self.assertRaisesRegex(t.r.q.QualificationError,'including journal'):
     db.check_budget()
   finally:db.connection.close()
if __name__=='__main__':unittest.main()
