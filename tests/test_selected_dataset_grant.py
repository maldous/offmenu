import contextlib
import errno
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/grant-selected-dataset-view-v1.py'
spec=importlib.util.spec_from_file_location('selected_grant',SCRIPT)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class GrantTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.runner=SimpleNamespace(pw_uid=99999,pw_gid=99999)
        self.owner=SimpleNamespace(pw_uid=os.geteuid())

    def test_exact_raw_selection_and_no_broad_mount(self):
        self.assertEqual(6,sum(v[2]=='raw' for v in m.FILES.values()))
        selected=sorted(m.FILES)
        body=m.dropin_bytes(selected).decode()
        self.assertIn('[Service]\nBindReadOnlyPaths=\n',body)
        self.assertEqual(1,len(m.bindings(selected)))
        self.assertNotIn('BindPaths=',body)
        self.assertNotIn(str(m.ORIGINALS)+':',body)
        self.assertNotIn('ReadWritePaths',body)
        self.assertNotIn('/home/user',body)
        self.assertIn('/var/lib/offmenu-selected-datasets-v1/snapshot:',body)

    def source(self,key,body=b'fixture'):
        path=self.root/m.FILES[key][0];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body);path.chmod(0o644)
        return path

    def test_source_permission_denied_without_change(self):
        p=self.source('NO_EN_FOODS');p.chmod(0o600)
        with patch.object(m,'ORIGINALS',self.root),patch.object(m,'safe_parents'):
            state,_=m.source_check('NO_EN_FOODS',self.runner,self.owner)
        self.assertEqual('runner-read-denied',state)
        self.assertEqual(0o600,p.stat().st_mode&0o777)

    def test_source_symlink_hardlink_fifo_and_exec_rejected(self):
        for case in ('symlink','hardlink','fifo','execute'):
            p=self.source('NO_EN_FOODS')
            if case=='symlink':p.unlink();p.symlink_to(self.root/'CANARY')
            if case=='hardlink':os.link(p,self.root/'hardlink')
            if case=='fifo':p.unlink();os.mkfifo(p)
            if case=='execute':p.chmod(0o755)
            with patch.object(m,'ORIGINALS',self.root),patch.object(m,'safe_parents'):
                state,_=m.source_check('NO_EN_FOODS',self.runner,self.owner)
            self.assertEqual('unsafe-file',state)
            p.unlink()
            if (self.root/'hardlink').exists():(self.root/'hardlink').unlink()

    def test_size_limit_before_any_body_open(self):
        p=self.source('NO_EN_FOODS')
        with p.open('r+b') as f:f.truncate(m.MAX_RAW+1)
        original_open=m.os.open
        def only_directories(path,flags,*args,**kwargs):
            if not flags & os.O_DIRECTORY:raise AssertionError('payload open')
            return original_open(path,flags,*args,**kwargs)
        with patch.object(m,'ORIGINALS',self.root),patch.object(m,'safe_parents'),patch.object(m.os,'open',side_effect=only_directories):
            state,_=m.source_check('NO_EN_FOODS',self.runner,self.owner)
        self.assertEqual('oversized',state)

    def test_acl_rejected_without_edits(self):
        self.source('NO_EN_FOODS')
        with patch.object(m,'ORIGINALS',self.root),patch.object(m,'safe_parents'),patch.object(m.os,'getxattr',return_value=b'ACL'):
            self.assertEqual('acl-requires-review',m.source_check('NO_EN_FOODS',self.runner,self.owner)[0])

    def test_no_fr_or_fi_required_for_no(self):
        for key in m.GROUPS['NO']:self.source(key)
        with patch.object(m,'ORIGINALS',self.root),patch.object(m,'safe_parents'):
            statuses,selected,_=m.preflight_sources(self.runner,self.owner)
        self.assertEqual(set(m.GROUPS['NO']),set(selected))
        self.assertEqual('missing',statuses['FR_WORKBOOK'])
        self.assertEqual('missing',statuses['FI_ACQUISITION'])

    def test_aggregate_limit_omits_both_sources(self):
        fake=SimpleNamespace(st_size=m.MAX_RAW)
        with patch.object(m,'source_check',return_value=('validated',fake)):
            statuses,selected,_=m.preflight_sources(self.runner,self.owner)
        self.assertEqual([],selected)
        self.assertEqual('aggregate-limit',statuses['NO_EN_FOODS'])

    def test_exact_service_properties_and_readonly_bind(self):
        values={**m.BASE_PROPERTIES,'BindReadOnlyPaths':m.BOOTSTRAP_BIND+':rbind','DropInPaths':'','ActiveState':'active','SubState':'running','MainPID':'123'}
        m.verify_properties(values)
        for key,value in [('User','root'),('BindPaths','/home:/home'),('ProtectHome','no'),('DropInPaths','/CANARY'),('ControlGroup','/system.slice/other.service')]:
            altered=dict(values);altered[key]=value
            with self.assertRaises(m.Blocked):m.verify_properties(altered)

    def test_dispatch_lock_prevents_active_job(self):
        lock=self.root/'outputs/locks/dispatcher.lock';lock.parent.mkdir(parents=True,mode=0o700);lock.parent.parent.chmod(0o700);lock.touch(mode=0o600)
        runner=SimpleNamespace(pw_uid=os.geteuid())
        with patch.object(m,'DISPATCH_LOCK',lock):
            first=m.idle_lock(runner)
            try:
                with self.assertRaisesRegex(m.Blocked,'job-active'):m.idle_lock(runner)
            finally:os.close(first)
            os.close(m.idle_lock(runner))

    def test_unprivileged_dryrun_safe_report(self):
        with patch.object(m.os,'geteuid',return_value=1000),patch.object(m,'command',side_effect=AssertionError('system command')):
            report=m.run(False)
        self.assertEqual('local-root-required',report['errorCode'])
        self.assertFalse(report['applied'])
        self.assertNotIn('/home',json.dumps(report))

    def mocked_apply(self,fail_mount=False,active=False,preexisting_drop_dir=False):
        # Every external/privileged boundary is replaced. Only temporary fixture
        # files and real unprivileged lock descriptors exist in this test.
        commands=[];selected=list(m.GROUPS['NO']);info=(self.root/'source')
        info.write_bytes(b'fixture');observations={k:info.stat() for k in selected}
        dropdir=self.root/'drop';drop=dropdir/'grant.conf';backup=self.root/'backup'
        if preexisting_drop_dir:dropdir.mkdir()
        def ensure(path,body,mode=0o644):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
        with contextlib.ExitStack() as stack:
            mocks={'isolated_runtime':True,'account':(self.runner,self.owner),'preflight_sources':({k:'validated' for k in selected},selected,observations),'verify_baseline':(b'unit',False),'source_check':('validated',info.stat()),'properties':{'MainPID':'123'},'verify_properties':None,'create_snapshot':observations,'protected_directory':None,'assert_idle':None}
            for name,value in mocks.items():stack.enter_context(patch.object(m,name,return_value=value))
            stack.enter_context(patch.object(m.os,'geteuid',return_value=0))
            stack.enter_context(patch.object(m,'DROP_DIR',dropdir));stack.enter_context(patch.object(m,'DROP_IN',drop));stack.enter_context(patch.object(m,'BACKUP',backup))
            stack.enter_context(patch.object(m,'ensure_file',side_effect=ensure))
            stack.enter_context(patch.object(m,'regular_bytes',side_effect=lambda p,cap:p.read_bytes()))
            stack.enter_context(patch.object(m,'command',side_effect=lambda args,capture=False:commands.append(args) or ''))
            stack.enter_context(patch.object(m,'administrative_lock',side_effect=lambda:os.open(info,os.O_RDONLY)))
            stack.enter_context(patch.object(m,'idle_lock',side_effect=m.Blocked('job-active') if active else lambda runner:os.open(info,os.O_RDONLY)))
            stack.enter_context(patch.object(m,'verify_mounts',side_effect=m.Blocked('read-only-mount-verification-failed') if fail_mount else lambda *a:None))
            result=m.run(True)
        return result,commands,drop,backup

    def test_apply_success_only_dedicated_service(self):
        result,commands,drop,backup=self.mocked_apply()
        self.assertEqual('applied',result['status']);self.assertTrue(result['readOnlyMountsVerified'])
        self.assertTrue(drop.exists());self.assertEqual(b'unit',(backup/'original.service').read_bytes())
        self.assertEqual([['/usr/bin/systemd-analyze','verify',str(m.UNIT)],['/usr/bin/systemctl','stop',m.SERVICE],['/usr/bin/systemctl','daemon-reload'],['/usr/bin/systemctl','start',m.SERVICE]],commands)

    def test_mount_failure_rolls_back_own_dropin_and_restarts_base(self):
        result,commands,drop,backup=self.mocked_apply(fail_mount=True)
        self.assertEqual('blocked',result['status']);self.assertTrue(result['rollbackRestored'])
        self.assertFalse(drop.exists());self.assertTrue((backup/'original.service').exists())
        self.assertEqual(2,commands.count(['/usr/bin/systemctl','stop',m.SERVICE]))
        self.assertEqual(2,commands.count(['/usr/bin/systemctl','start',m.SERVICE]))

    def test_active_job_stops_before_changes(self):
        result,commands,drop,backup=self.mocked_apply(active=True)
        self.assertEqual('job-active',result['errorCode']);self.assertEqual([],commands)
        self.assertFalse(drop.exists());self.assertFalse(backup.exists())


    def test_preserves_preexisting_empty_dropin_directory(self):
        result,commands,drop,backup=self.mocked_apply(fail_mount=True,preexisting_drop_dir=True)
        self.assertTrue(result['rollbackRestored']);self.assertTrue(drop.parent.is_dir())
        self.assertEqual([],list(drop.parent.iterdir()))

    def test_subprocess_output_is_bounded_while_reading(self):
        with self.assertRaisesRegex(m.Blocked,'system-response-oversized'):
            m.command([sys.executable,'-I','-c','import sys;sys.stdout.write("x"*1000000)'],True)

    def test_bounded_file_read(self):
        p=self.root/'large';p.write_bytes(b'a'*100)
        with self.assertRaisesRegex(m.Blocked,'bounded-read-limit'):m.bounded_read(p,10)

    def test_source_parent_replacement_uses_held_directory(self):
        p=self.source('NO_EN_FOODS',b'APPROVED')
        outside=self.root/'outside';outside.mkdir();(outside/'en-foods.json').write_bytes(b'CANARY-SECRET')
        original_open=m.os.open;swapped=False
        def replace_parent(path,flags,*args,**kwargs):
            nonlocal swapped
            if path=='en-foods.json' and not flags&os.O_DIRECTORY and not swapped:
                p.parent.rename(p.parent.with_name('held'));p.parent.symlink_to(outside,target_is_directory=True);swapped=True
            return original_open(path,flags,*args,**kwargs)
        with patch.object(m,'ORIGINALS',self.root),patch.object(m.os,'open',side_effect=replace_parent):
            fd,info=m.anchored_source('NO_EN_FOODS',self.runner,self.owner)
            try:self.assertEqual(b'APPROVED',os.read(fd,100))
            finally:os.close(fd)
        self.assertEqual(b'CANARY-SECRET',p.read_bytes())

    def test_atomic_publish_never_clobbers(self):
        source=self.root/'stage';destination=self.root/'snapshot';source.mkdir();destination.mkdir()
        (destination/'CANARY').write_text('preserve')
        with self.assertRaisesRegex(m.Blocked,'snapshot-publish-conflict'):m.rename_noreplace(source,destination)
        self.assertEqual('preserve',(destination/'CANARY').read_text())
        self.assertTrue(source.exists())

    def test_snapshot_copy_is_private_and_bounded_before_publish(self):
        selected=list(m.GROUPS['NO']);observations={}
        for key in selected:observations[key]=self.source(key,b'FIXTURE-'+key.encode()).stat()
        backup=self.root/'private';backup.mkdir(mode=0o700)
        stage=backup/'.stage';snapshot=backup/'snapshot'
        counters={'sourceBytesRead':0,'snapshotBytesWritten':0,'snapshotVerified':False}
        def directory(path,runner,create=False,stage=False):
            if create:path.mkdir(mode=0o700 if stage else 0o750)
        def inspect(path):
            self.assertEqual(0o700,Path(path).stat().st_mode&0o777)
            self.assertFalse(snapshot.exists())
            for key in selected:self.assertEqual(b'FIXTURE-'+key.encode(),(Path(path)/m.FILES[key][1]).read_bytes())
            return {'assets':{k:{'status':'inspected','historicalMatch':'match','receiptMatch':'match','acquisitionMatch':'match'} for k in selected},'sources':{'NO':{'provenanceVerified':True,'historicalRightsProfile':'test'}}}
        reference={'inspect':inspect,'SOURCES':{'NO':(None,None,None,None,'test')}}
        with patch.object(m,'ORIGINALS',self.root),patch.object(m,'BACKUP',backup),patch.object(m,'STAGING',stage),patch.object(m,'SCAFFOLD',snapshot),patch.object(m,'protected_directory'),patch.object(m,'snapshot_directory',side_effect=directory),patch.object(m,'reference_parser',return_value=reference),patch.object(m,'ensure_file',side_effect=lambda path,body,mode:path.write_bytes(body)),patch.object(m.os,'chown'),patch.object(m.os,'fchown'):
            result=m.create_snapshot(selected,self.runner,self.owner,observations,counters)
        self.assertTrue(snapshot.is_dir());self.assertFalse(stage.exists())
        total=sum(v.st_size for v in observations.values())
        self.assertEqual(total,counters['sourceBytesRead']);self.assertEqual(total,counters['snapshotBytesWritten'])
        self.assertTrue(counters['snapshotVerified']);self.assertEqual(set(selected),set(result))
        self.assertEqual(0o700,backup.stat().st_mode&0o777)
        for key in selected:self.assertEqual(0o440,(snapshot/m.FILES[key][1]).stat().st_mode&0o777)


    def test_optional_fi_and_bad_fr_do_not_block_valid_no(self):
        selected=sorted(m.FILES)
        evidence={'assets':{k:{'status':'inspected','historicalMatch':'match','receiptMatch':'match','acquisitionMatch':'match'} for k in selected},'sources':{'NO':{'provenanceVerified':True,'historicalRightsProfile':'no'},'FR':{'provenanceVerified':True,'historicalRightsProfile':'fr'}}}
        reference={'SOURCES':{'NO':(None,None,None,None,'no'),'FR':(None,None,None,None,'fr')}}
        evidence['assets']['FI_PRIOR_MANIFEST']['historicalMatch']='mismatch'
        evidence['assets']['FR_WORKBOOK']['receiptMatch']='mismatch'
        report={'assets':{},'sources':{}}
        self.assertEqual(sorted(m.GROUPS['NO']),m.evidence_selection(evidence,selected,reference,report))
        self.assertEqual('validated',report['sources']['NO'])
        self.assertEqual('blocked',report['sources']['FR']);self.assertEqual('blocked',report['sources']['FI'])
        self.assertEqual('evidence-blocked',report['assets']['FI_ACQUISITION'])

    def test_shared_receipt_failure_blocks_no_and_fr(self):
        selected=sorted(m.FILES)
        evidence={'assets':{k:{'status':'inspected','historicalMatch':'match','receiptMatch':'match','acquisitionMatch':'match'} for k in selected},'sources':{}}
        evidence['assets']['NATIONAL_ACQUISITION']['historicalMatch']='mismatch'
        with self.assertRaisesRegex(m.Blocked,'snapshot-no-verified-source-group'):
            m.evidence_selection(evidence,selected,{}, {})


if __name__=='__main__':unittest.main()
