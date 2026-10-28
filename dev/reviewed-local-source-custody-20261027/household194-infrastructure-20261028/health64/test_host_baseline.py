import fcntl
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

# Supports both the authoring sibling layout and installed scripts/windmill/storage.
local_storage=Path(__file__).resolve().parent.parent/'storage'
if local_storage.is_dir():sys.path.insert(0,str(local_storage))
import platform_check as check
import offmenu_storage as storage

class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'jobs').mkdir();(self.root/'locks').mkdir()
    def tearDown(self):self.temp.cleanup()
    def job(self,name='job1',state='succeeded',**extra):
        d=self.root/'jobs'/name;d.mkdir()
        value={'job_id':name,'status':state,'heartbeat_at':time.time(),'child_tree_gone':True,**extra}
        (d/'receipt.json').write_text(json.dumps(value));return d
    def artifact(self,size=10):
        source=self.root/'input';source.write_bytes(b'x'*size)
        store=storage.Store(self.root);a=store.publish(source,'synthetic/object')
        cp=store.checkpoint('test/part',{'run_id':'test','partition':'part','status':'completed'},[a['receipt_path']])
        return store,a,cp
    def test_health_does_not_read_logs_or_wait_on_writer(self):
        d=self.job();(d/'stdout.log').write_text('DO_NOT_RETURN_SECRET_MARKER')
        fd=os.open(self.root/'locks/execution-access.lock',os.O_CREAT|os.O_RDWR,0o600)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX)
            start=time.monotonic();r=check.audit('health',root=self.root)
            self.assertLess(time.monotonic()-start,1)
            self.assertTrue(r['ok']);self.assertEqual(r['counts']['jobs_checked'],1)
            self.assertNotIn('DO_NOT_RETURN_SECRET_MARKER',json.dumps(r))
        finally:os.close(fd)
    def test_stale_job_and_terminal_marker_reported(self):
        self.job(state='running',heartbeat_at=time.time()-60)
        (self.root/'locks/execution-slot-0.inflight.json').write_text(json.dumps({'job_id':'job1'}))
        r=check.audit('health',root=self.root)
        self.assertFalse(r['ok']);self.assertIn('STALE_ACTIVE_JOB',[f['code'] for f in r['findings']])
    def test_fresh_active_marker_is_not_failure(self):
        self.job(state='running')
        (self.root/'locks/execution-slot-0.inflight.json').write_text(json.dumps({'job_id':'job1'}))
        r=check.audit('health',root=self.root)
        self.assertTrue(r['ok']);self.assertEqual(r['counts']['markers_checked'],1)
    def test_old_failed_job_is_informational(self):
        self.job(state='failed');r=check.audit('health',root=self.root)
        self.assertTrue(r['ok']);self.assertEqual(r['findings'][0]['severity'],'info')
    def test_verify_uses_storage_hash_validation(self):
        store,a,cp=self.artifact()
        r=check.audit('verify',root=self.root)
        self.assertTrue(r['ok']);self.assertEqual(r['counts']['checkpoints_verified'],1)
        self.assertEqual(r['counts']['artifact_manifests_verified'],1)
        self.assertEqual(r['counts']['artifact_objects_hashed'],1)
        self.assertFalse(r['coverage']['full_coverage'])
    def test_corrupt_artifact_detected_without_content(self):
        store,a,cp=self.artifact()
        manifest=storage.read_json(store.path(a['receipt_path']))
        store.path(manifest['object_path']).write_bytes(b'BADSECRET!')
        r=check.audit('verify',root=self.root)
        self.assertFalse(r['ok']);self.assertNotIn('BADSECRET',json.dumps(r))
        self.assertIn('CHECKPOINT_INTEGRITY_FAILED',[f['code'] for f in r['findings']])
    def test_byte_budget_incomplete_not_success(self):
        self.artifact(100000)
        r=check.audit('verify',root=self.root,byte_limit=5000)
        self.assertFalse(r['ok']);self.assertEqual(r['status'],'incomplete')
        self.assertEqual(r['coverage']['stopped_reason'],'bytes')
        self.assertLessEqual(r['budgets']['bytes_read'],5000)
        self.assertEqual(r['counts']['artifact_objects_hashed'],0)
    def test_deadline_restores_storage_function(self):
        old=storage.read_regular
        r=check.audit('health',root=self.root,seconds=-1)
        self.assertEqual(r['coverage']['stopped_reason'],'deadline')
        self.assertIs(storage.read_regular,old)
    def test_item_and_scan_limits_explicit(self):
        for n in range(5):self.job('j'+str(n))
        r=check.audit('health',root=self.root,max_items=2)
        self.assertEqual(r['counts']['jobs_checked'],2)
        self.assertFalse(r['ok']);self.assertEqual(r['status'],'incomplete')
        with patch.object(check,'MAX_SCAN',2):
            r=check.audit('health',root=self.root)
            self.assertEqual(r['counts']['entries_scanned'],2)
            self.assertTrue(r['coverage']['selection_truncated'])
    def test_parent_symlink_refused(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.root/'artifacts').symlink_to(outside,target_is_directory=True)
            (Path(outside)/'manifests').mkdir()
            r=check.audit('verify',root=self.root)
            self.assertFalse(r['ok']);self.assertIn('UNSAFE_COLLECTION',[f['code'] for f in r['findings']])
    def test_marker_symlink_and_nan_refused(self):
        (self.root/'locks/execution-slot-0.inflight.json').symlink_to('/etc/passwd')
        self.job(state='running',heartbeat_at=float('nan'))
        r=check.audit('health',root=self.root)
        self.assertFalse(r['ok']);self.assertIn('INVALID_INFLIGHT_MARKER',[f['code'] for f in r['findings']])
        self.assertIn('INVALID_JOB_RECEIPT',[f['code'] for f in r['findings']])
    def test_readonly_no_state_change(self):
        self.artifact()
        before={str(p.relative_to(self.root)):(p.stat().st_size,p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}
        check.audit('verify',root=self.root)
        after={str(p.relative_to(self.root)):(p.stat().st_size,p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before,after)
    def test_exact_remaining_metadata_budget_is_valid(self):
        d=self.job();size=(d/'receipt.json').stat().st_size
        r=check.audit('health',root=self.root,byte_limit=size)
        self.assertTrue(r['ok']);self.assertEqual(r['budgets']['bytes_read'],size)
    def test_malformed_metadata_bytes_are_charged(self):
        for n in range(3):
            d=self.job('bad'+str(n));(d/'receipt.json').write_text('x'*100)
        r=check.audit('health',root=self.root,byte_limit=150)
        self.assertFalse(r['ok']);self.assertEqual(r['coverage']['stopped_reason'],'bytes')
        self.assertEqual(r['budgets']['bytes_read'],100)
    def test_oversized_metadata_rejected_before_read(self):
        d=self.job();(d/'receipt.json').write_text('x'*70000)
        r=check.audit('health',root=self.root)
        self.assertFalse(r['ok']);self.assertEqual(r['budgets']['bytes_read'],0)
    def test_missing_cleanup_evidence_is_not_healthy(self):
        d=self.job();value=json.loads((d/'receipt.json').read_text());del value['child_tree_gone'];(d/'receipt.json').write_text(json.dumps(value))
        r=check.audit('health',root=self.root)
        self.assertFalse(r['ok']);self.assertEqual(r['findings'][0]['code'],'UNRESOLVED_INFLIGHT_JOB')
    def test_concurrent_checkpoint_advance_is_incomplete_not_corruption(self):
        store,a,cp=self.artifact()
        original=storage.Store.verify
        def advance(selected,key,version=None):
            snapshot=original(selected,key,version)
            store.checkpoint(key,{'run_id':'test','partition':'part','status':'completed','counts':{'next':1}},[a['receipt_path']])
            return snapshot
        with patch.object(storage.Store,'verify',advance):r=check.audit('verify',root=self.root)
        self.assertFalse(r['ok']);self.assertEqual(r['status'],'incomplete')
        self.assertIn('CHECKPOINT_ADVANCED',[f['code'] for f in r['findings']])
        self.assertNotIn('CHECKPOINT_INTEGRITY_FAILED',[f['code'] for f in r['findings']])
        self.assertTrue(all(f['severity']!='error' for f in r['findings']))
    def test_invalid_pointer_advance_stays_integrity_failure(self):
        for replacement in ({'bad':True}, {'same_version_bad_hash':True}):
            with self.subTest(replacement=replacement):
                store,a,cp=self.artifact()
                original=storage.Store.verify
                def corrupt(selected,key,version=None):
                    snapshot=original(selected,key,version)
                    path=next((self.root/'checkpoints/current').glob('*.json'))
                    pointer=json.loads(path.read_text())
                    if 'same_version_bad_hash' in replacement:pointer['sha256']='0'*64
                    else:pointer=replacement
                    path.write_text(json.dumps(pointer))
                    return snapshot
                with patch.object(storage.Store,'verify',corrupt):r=check.audit('verify',root=self.root)
                self.assertIn('CHECKPOINT_INTEGRITY_FAILED',[f['code'] for f in r['findings']])
                self.assertNotIn('CHECKPOINT_ADVANCED',[f['code'] for f in r['findings']])
    def test_invalid_options(self):

        for mode,items in [('bad',100),('health',101),('verify',0),('health',True)]:
            with self.assertRaises(ValueError):check.audit(mode,items,root=self.root)

if __name__=='__main__':unittest.main()
