import contextlib
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPT=Path(__file__).resolve().parents[1]/'tools/operations/grant_selected_dataset_view_v1.py'
spec=importlib.util.spec_from_file_location('selected_grant',SCRIPT)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class GrantTests(unittest.TestCase):
    def setUp(self):
        # Production traversal intentionally rejects writable ancestors. CI's
        # conventional /tmp is1777, so place controlled fixtures under the
        # resolved checkout rather than depending on host temp-root modes.
        self.tmp=tempfile.TemporaryDirectory(prefix='.grant-test-',dir=SCRIPT.parents[2]);self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.runner=SimpleNamespace(pw_uid=99999,pw_gid=99999)
        self.owner=SimpleNamespace(pw_uid=os.geteuid(),pw_gid=os.getegid())

    def test_writable_source_ancestor_is_rejected(self):
        unsafe=self.root/'unsafe-parent';unsafe.mkdir();unsafe.chmod(0o1777)
        path=unsafe/m.FILES['NO_EN_FOODS'][0]
        path.parent.mkdir(parents=True);path.write_bytes(b'fixture');path.chmod(0o644)
        with patch.object(m,'ORIGINALS',unsafe):
            state,info=m.source_check('NO_EN_FOODS',self.runner,self.owner)
        self.assertEqual('unsafe-path',state)
        self.assertIsNone(info)
        self.assertEqual(b'fixture',path.read_bytes())

    def test_known_primary_group_writable_source_ancestor_allowed(self):
        self.source('NO_EN_FOODS');self.root.chmod(0o775)
        with patch.object(m,'ORIGINALS',self.root):
            state,info=m.source_check('NO_EN_FOODS',self.runner,self.owner)
        self.assertEqual('validated',state)
        self.assertEqual(0o775,self.root.stat().st_mode&0o777)
        self.assertEqual(0o644,info.st_mode&0o777)

    def test_named_acl_on_held_source_ancestor_rejected(self):
        self.source('NO_EN_FOODS');self.root.chmod(0o775)
        inode=self.root.stat().st_ino;original_getxattr=m.os.getxattr
        def named_acl(fd,name):
            self.assertIsInstance(fd,int)
            if os.fstat(fd).st_ino==inode:return b'named-writer-acl'
            return original_getxattr(fd,name)
        with patch.object(m,'ORIGINALS',self.root),patch.object(m.os,'getxattr',side_effect=named_acl):
            self.assertEqual('acl-requires-review',m.source_check('NO_EN_FOODS',self.runner,self.owner)[0])
        self.assertEqual(0o775,self.root.stat().st_mode&0o777)

    def test_unknown_source_ancestor_group_still_rejected(self):
        self.source('NO_EN_FOODS');self.root.chmod(0o775)
        original_fstat=m.os.fstat;inode=self.root.stat().st_ino
        def wrong_group(fd):
            info=original_fstat(fd)
            if info.st_ino==inode:
                values=list(info);values[5]=99998
                return os.stat_result(values)
            return info
        with patch.object(m,'ORIGINALS',self.root),patch.object(m.os,'fstat',side_effect=wrong_group):
            self.assertEqual('unsafe-path',m.source_check('NO_EN_FOODS',self.runner,self.owner)[0])

    def test_expected_group_writable_source_leaf_allowed(self):
        p=self.source('NO_EN_FOODS');p.chmod(0o664)
        with patch.object(m,'ORIGINALS',self.root):
            self.assertEqual('validated',m.source_check('NO_EN_FOODS',self.runner,self.owner)[0])
        self.assertEqual(0o664,p.stat().st_mode&0o777)

    def test_source_leaf_unknown_owner_or_group_rejected(self):
        p=self.source('NO_EN_FOODS');p.chmod(0o664)
        original_stat=m.os.stat
        for index in (4,5):
            def wrong_identity(path,*args,**kwargs):
                info=original_stat(path,*args,**kwargs)
                if path=='en-foods.json':
                    values=list(info);values[index]=99998
                    return os.stat_result(values)
                return info
            with patch.object(m,'ORIGINALS',self.root),patch.object(m.os,'stat',side_effect=wrong_identity):
                self.assertEqual('unsafe-file',m.source_check('NO_EN_FOODS',self.runner,self.owner)[0])

    def test_group_write_does_not_bypass_runner_read_or_world_write(self):
        p=self.source('NO_EN_FOODS')
        for mode,expected in ((0o660,'runner-read-denied'),(0o666,'unsafe-file'),(0o675,'unsafe-file')):
            p.chmod(mode)
            with patch.object(m,'ORIGINALS',self.root):
                self.assertEqual(expected,m.source_check('NO_EN_FOODS',self.runner,self.owner)[0])
            self.assertEqual(mode,p.stat().st_mode&0o777)

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

    def mocked_apply(self,fail_mount=False,active=False,preexisting_drop_dir=False,fail_stop=False,fail_readability=False):
        # Every external/privileged boundary is replaced. Only temporary fixture
        # files and real unprivileged lock descriptors exist in this test.
        commands=[];selected=list(m.GROUPS['NO']);info=(self.root/'source')
        info.write_bytes(b'fixture');observations={k:info.stat() for k in selected}
        dropdir=self.root/'drop';drop=dropdir/'grant.conf';backup=self.root/'backup'
        if preexisting_drop_dir:dropdir.mkdir()
        def ensure(path,body,mode=0o644):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
        with contextlib.ExitStack() as stack:
            mocks={'process_start_time':b'1','isolated_runtime':True,'account':(self.runner,self.owner),'preflight_sources':({k:'validated' for k in selected},selected,observations),'verify_baseline':(b'unit',False),'source_check':('validated',info.stat()),'runtime_identity':None,'create_snapshot':observations,'protected_directory':None}
            for name,value in mocks.items():stack.enter_context(patch.object(m,name,return_value=value))
            stack.enter_context(patch.object(m.os,'geteuid',return_value=0))
            stack.enter_context(patch.object(m,'DROP_DIR',dropdir));stack.enter_context(patch.object(m,'DROP_IN',drop));stack.enter_context(patch.object(m,'BACKUP',backup))
            def props(timeout=90):
                values={**m.BASE_PROPERTIES,'BindReadOnlyPaths':(m.bindings(selected)[0] if drop.exists() else m.BOOTSTRAP_BIND)+':rbind','DropInPaths':str(drop) if drop.exists() else '',
                        'ActiveState':'active','SubState':'running','Result':'success','MainPID':'123','ExecMainPID':'123','ExecMainCode':'0','ExecMainStatus':'0','StatusErrno':'0'}
                m.LAST_PROPERTIES=values
                return values
            stack.enter_context(patch.object(m,'properties',side_effect=props))
            stack.enter_context(patch.object(m,'assert_idle',side_effect=lambda *args:props()))
            def readable(pid,keys,observations,runner,report,timeout=5):
                if fail_readability:
                    report['runnerReadability']={'status':'blocked','stage':'namespace','checkedAssets':[],'failedAsset':None,'errno':errno.EPERM}
                    m.block('runner-readability-failed')
                report['runnerReadability']={'status':'verified','stage':'complete','checkedAssets':keys,'failedAsset':None,'errno':None}
            stack.enter_context(patch.object(m,'verify_runner_readability',side_effect=readable))
            stack.enter_context(patch.object(m,'ensure_file',side_effect=ensure))
            stack.enter_context(patch.object(m,'regular_bytes',side_effect=lambda p,cap:p.read_bytes()))
            def command(args,capture=False):
                commands.append(args)
                if fail_stop and args==['/usr/bin/systemctl','stop',m.SERVICE] and commands.count(args)==1:m.block('system-command-timeout')
                return ''
            stack.enter_context(patch.object(m,'command',side_effect=command))
            stack.enter_context(patch.object(m,'administrative_lock',side_effect=lambda:os.open(info,os.O_RDONLY)))
            stack.enter_context(patch.object(m,'idle_lock',side_effect=m.Blocked('job-active') if active else lambda runner:os.open(info,os.O_RDONLY)))
            stack.enter_context(patch.object(m,'verify_mounts',side_effect=m.Blocked('mounted-file-identity-mismatch') if fail_mount else lambda *a:None))
            result=m.run(True)
        return result,commands,drop,backup

    def test_apply_success_only_dedicated_service(self):
        result,commands,drop,backup=self.mocked_apply()
        self.assertEqual('applied',result['status']);self.assertTrue(result['readOnlyMountsVerified'])
        self.assertTrue(drop.exists());self.assertEqual(b'unit',(backup/'original.service').read_bytes())
        self.assertEqual([['/usr/bin/systemd-analyze','verify',str(m.UNIT)],['/usr/bin/systemctl','daemon-reload'],['/usr/bin/systemctl','stop',m.SERVICE],['/usr/bin/systemctl','start',m.SERVICE]],commands)

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
        p=self.source('NO_EN_FOODS',b'APPROVED');p.parent.chmod(0o775)
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

    def test_content_addressed_inspector_preserves_previous_private_leaf_and_retries(self):
        backup=self.root/'private';backup.mkdir(mode=0o700)
        old=backup/'approved-inspector.py';old.write_bytes(b'previous-helper-owned-inspector');old.chmod(0o600)
        old_stat=old.stat();body=(SCRIPT.parent/'inspect_selected_datasets.py').read_bytes()
        private=backup/('approved-inspector-'+m.INSPECTOR_SHA+'.py')
        regular=m.regular_bytes
        with patch.object(m,'BACKUP',backup),patch.object(m,'safe_parents'),patch.object(m,'regular_bytes',side_effect=lambda p,c:regular(p,c,owner=os.geteuid())):
            first=m.reference_parser();second=m.reference_parser()
            self.assertEqual(str(private),first['__file__'])
            self.assertEqual(str(private),second['__file__'])
            self.assertEqual(body,private.read_bytes());self.assertEqual(0o600,private.stat().st_mode&0o777)
            self.assertEqual(m.INSPECTOR_SHA,first['inspect'](str(self.root/'empty'))['inspectorSha256'])
            self.assertEqual(m.signature(old_stat),m.signature(old.stat()))
            self.assertEqual(b'previous-helper-owned-inspector',old.read_bytes())
            private.write_bytes(b'unrecognized-current-leaf')
            with self.assertRaisesRegex(m.Blocked,'versioned-file-conflict'):m.reference_parser()
            self.assertEqual(b'unrecognized-current-leaf',private.read_bytes())
        wrapper_spec=importlib.util.spec_from_file_location('retry_wrapper',SCRIPT.parent/'run_selected_dataset_grant.py')
        wrapper=importlib.util.module_from_spec(wrapper_spec);wrapper_spec.loader.exec_module(wrapper)
        self.assertEqual(hashlib.sha256(body).hexdigest(),m.INSPECTOR_SHA)
        for path,pin in wrapper.PINS.items():self.assertEqual(pin,hashlib.sha256((SCRIPT.parents[2]/path).read_bytes()).hexdigest())

    def test_previous_unsupported_stage_cleans_up_then_content_schema_retry_succeeds(self):
        selected=sorted(m.GROUPS['NO']);backup=self.root/'private';backup.mkdir(mode=0o700)
        stage=backup/'.stage';snapshot=backup/'snapshot'
        spec=importlib.util.spec_from_file_location('retry_inspector',SCRIPT.parent/'inspect_selected_datasets.py')
        inspector=importlib.util.module_from_spec(spec);spec.loader.exec_module(inspector)
        reference=vars(inspector);selection=dict(inspector.SELECTION);decl=[];records=[]
        for key in inspector.SOURCES['NO'][2]:
            body=b'raw fixture '+key.encode();self.source(key,body);digest=hashlib.sha256(body).hexdigest()
            selection[key]=(*selection[key][:2],digest if selection[key][2] else None)
            decl.append({'key':selection[key][0].split('/')[-1],'bytes':len(body),'sha256':digest})
            records.append({'file':'opaque label '+key,'bytes':len(body),'sha256':digest,'url':'https://DO-NOT-FETCH.invalid'})
        self.source('NATIONAL_ACQUISITION',json.dumps(records).encode())
        self.source('NO_PRIOR_MANIFEST',json.dumps({'schemaVersion':'offmenu-collection/1','sourceId':'matvaretabellen','releaseId':'2026','status':'normalized','license':inspector.LICENSES['NO'],'sourceFiles':decl}).encode())
        for key in ('NATIONAL_ACQUISITION','NO_PRIOR_MANIFEST'):
            selection[key]=(*selection[key][:2],hashlib.sha256((self.root/m.FILES[key][0]).read_bytes()).hexdigest())
        reference['SELECTION']=selection;observations={k:(self.root/m.FILES[k][0]).stat() for k in selected}
        parser=reference['metadata_facts']
        def legacy_parser(key,value):
            if key=='NATIONAL_ACQUISITION':raise ValueError('schema')
            return parser(key,value)
        def directory(path,runner,create=False,stage=False):
            if create:path.mkdir(mode=0o700 if stage else 0o750)
        with patch.object(m,'ORIGINALS',self.root),patch.object(m,'BACKUP',backup),patch.object(m,'STAGING',stage),patch.object(m,'SCAFFOLD',snapshot),patch.object(m,'protected_directory'),patch.object(m,'snapshot_directory',side_effect=directory),patch.object(m,'reference_parser',return_value=reference),patch.object(m,'ensure_file',side_effect=lambda path,body,mode:path.write_bytes(body)),patch.object(m.os,'chown'),patch.object(m.os,'fchown'):
            reference['metadata_facts']=legacy_parser
            failed={'sourceBytesRead':0,'snapshotBytesWritten':0,'snapshotVerified':False}
            with self.assertRaisesRegex(m.Blocked,'snapshot-no-verified-source-group'):
                m.create_snapshot(selected,self.runner,self.owner,observations,failed)
            self.assertFalse(stage.exists());self.assertFalse(snapshot.exists())
            self.assertFalse((backup/'selection.json').exists())
            self.assertEqual('unsupported-schema',failed['snapshotEvidence']['assets']['NATIONAL_ACQUISITION']['status'])
            reference['metadata_facts']=parser
            report={'sourceBytesRead':0,'snapshotBytesWritten':0,'snapshotVerified':False}
            result=m.create_snapshot(selected,self.runner,self.owner,observations,report)
        self.assertEqual(set(selected),set(result));self.assertTrue(snapshot.exists());self.assertFalse(stage.exists())
        self.assertTrue(report['snapshotVerified'])
        self.assertEqual('pinned-receipt-content',report['snapshotEvidence']['assets']['NO_EN_FOODS']['acquisitionMatchBasis'])
        self.assertFalse(report['snapshotEvidence']['completeReady'])  # staging is writable; NO-only fixture


    def ready_properties(self,selected=None,**changes):
        return {**m.expected_properties(selected),'ActiveState':'active','SubState':'running','Result':'success','MainPID':'123','ExecMainPID':'123','ExecMainCode':'0','ExecMainStatus':'0','StatusErrno':'0',**changes}

    def await_fixture(self,values,mount_effect=None,identity_effect=None):
        report={};now=[0]
        def sleep(seconds):now[0]+=seconds
        stack=contextlib.ExitStack()
        stack.enter_context(patch.object(m,'properties',side_effect=values if isinstance(values,list) else lambda timeout=90:values))
        stack.enter_context(patch.object(m,'runtime_identity',side_effect=identity_effect))
        stack.enter_context(patch.object(m,'process_start_time',return_value=b'1'))
        stack.enter_context(patch.object(m,'verify_runner_readability'))
        mounts=stack.enter_context(patch.object(m,'verify_mounts',side_effect=mount_effect))
        stack.enter_context(patch.object(m.time,'monotonic',side_effect=lambda:now[0]))
        stack.enter_context(patch.object(m.time,'sleep',side_effect=sleep))
        self.addCleanup(stack.close)
        return report,now,mounts

    def test_transient_start_converges_only_after_full_identity_and_mounts(self):
        selected=sorted(m.GROUPS['NO']);ready=self.ready_properties(selected)
        transient={**ready,'ActiveState':'activating','SubState':'start','ControlGroup':'','MainPID':'0'}
        report,now,mounts=self.await_fixture([transient,ready,ready])
        m.await_ready(selected,self.runner,{},report,'after')
        self.assertEqual(2,report['serviceDiagnostics']['afterAttempts'])
        self.assertEqual('runtime-activation',report['serviceDiagnostics']['afterLastPending'])
        mounts.assert_called_once_with(123,selected,{})
        self.assertEqual(m.READY_INTERVAL,now[0])

    def test_static_drift_and_foreign_cgroup_fail_immediately(self):
        selected=sorted(m.GROUPS['NO'])
        for key,value in [('ProtectHome','no'),('User','root'),('ControlGroup','/foreign/CANARY'),('DropInPaths','/CANARY')]:
            with self.subTest(key=key),contextlib.ExitStack() as stack:
                values=self.ready_properties(selected,**{key:value})
                stack.enter_context(patch.object(m,'properties',return_value=values))
                sleep=stack.enter_context(patch.object(m.time,'sleep'))
                mounts=stack.enter_context(patch.object(m,'verify_mounts'))
                with self.assertRaises(m.Blocked):m.await_ready(selected,self.runner,{}, {},'after')
                sleep.assert_not_called();mounts.assert_not_called()

    def test_terminal_service_state_fails_with_226_evidence(self):
        selected=sorted(m.GROUPS['NO'])
        values=self.ready_properties(selected,ActiveState='failed',SubState='failed',Result='exit-code',ExecMainCode='1',ExecMainStatus='226',MainPID='0',ControlGroup='')
        report,now,mounts=self.await_fixture(values)
        with self.assertRaisesRegex(m.Blocked,'service-start-failed'):m.await_ready(selected,self.runner,{},report,'after')
        self.assertEqual(226,report['serviceDiagnostics']['after']['numbers']['ExecMainStatus'])
        self.assertEqual(0,now[0]);mounts.assert_not_called()

    def test_readonly_mount_pending_is_bounded_and_reason_retained(self):
        selected=sorted(m.GROUPS['NO'])
        report,now,mounts=self.await_fixture(self.ready_properties(selected),m.Blocked('read-only-mount-verification-failed'))
        with self.assertRaisesRegex(m.Blocked,'service-readiness-timeout'):m.await_ready(selected,self.runner,{},report,'after')
        self.assertEqual(m.READY_SECONDS,now[0])
        self.assertLessEqual(report['serviceDiagnostics']['afterAttempts'],101)
        self.assertEqual('read-only-mount-verification-failed',report['serviceDiagnostics']['afterLastPending'])

    def test_wrong_mounted_identity_and_unexpected_uid_fail_immediately(self):
        selected=sorted(m.GROUPS['NO'])
        for boundary,code in [('verify_mounts','mounted-file-identity-mismatch'),('runtime_identity','service-process-owner-invalid')]:
            with self.subTest(boundary=boundary),contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(m,'properties',return_value=self.ready_properties(selected)))
                stack.enter_context(patch.object(m,'runtime_identity'))
                stack.enter_context(patch.object(m,'process_start_time',return_value=b'1'))
                stack.enter_context(patch.object(m,boundary,side_effect=m.Blocked(code)))
                sleep=stack.enter_context(patch.object(m.time,'sleep'))
                with self.assertRaisesRegex(m.Blocked,code):m.await_ready(selected,self.runner,{}, {},'after')
                sleep.assert_not_called()

    def test_pid_change_requires_fresh_mount_identity(self):
        selected=sorted(m.GROUPS['NO']);first=self.ready_properties(selected);second={**first,'MainPID':'456'}
        report,now,mounts=self.await_fixture([first,second,second,second])
        m.await_ready(selected,self.runner,{},report,'after')
        self.assertEqual([123,456],[call.args[0] for call in mounts.call_args_list])
        self.assertEqual('process-changed',report['serviceDiagnostics']['afterLastPending'])

    def test_property_diagnostics_never_export_free_text(self):
        values=self.ready_properties(ControlGroup='/CANARY-SECRET',ReadWritePaths='/SECRET',ActiveState='CANARY',ExecMainStatus='NaN',StatusErrno='13')
        evidence=m.property_evidence(values)
        self.assertNotIn('CANARY',json.dumps(evidence));self.assertNotIn('/SECRET',json.dumps(evidence))
        self.assertFalse(evidence['properties']['ControlGroup']['match'])
        self.assertEqual(hashlib.sha256(b'/CANARY-SECRET').hexdigest(),evidence['unexpectedValueSha256']['ControlGroup'])
        self.assertEqual('unknown',evidence['states']['ActiveState'])
        self.assertIsNone(evidence['numbers']['ExecMainStatus']);self.assertEqual(13,evidence['numbers']['StatusErrno'])

    def test_original_failure_snapshot_survives_rollback(self):
        result,commands,drop,backup=self.mocked_apply(fail_mount=True)
        diagnostics=result['serviceDiagnostics']
        self.assertEqual('mounted-file-identity-mismatch',diagnostics['failureDetail']['errorCode'])
        self.assertEqual('mounted-file-identity-mismatch',result['errorCode'])
        self.assertTrue(diagnostics['failure']['properties']['DropInPaths']['match'])
        self.assertTrue(diagnostics['rollback']['properties']['DropInPaths']['match'])
        self.assertTrue(result['rollbackRestored']);self.assertFalse(result['applied'])

    def test_command_failure_keeps_only_exit_code_or_errno(self):
        with self.assertRaisesRegex(m.Blocked,'system-command-failed'):m.command([sys.executable,'-I','-c','import sys;sys.exit(7)'])
        self.assertEqual(7,m.LAST_COMMAND['exitCode'])
        self.assertNotIn(sys.executable,json.dumps(m.LAST_COMMAND))
        with patch.object(m.subprocess,'Popen',side_effect=PermissionError(errno.EACCES,'CANARY')):
            with self.assertRaises(PermissionError):m.command(['/usr/bin/systemctl','start',m.SERVICE])
        self.assertEqual(errno.EACCES,m.LAST_COMMAND['errno']);self.assertEqual('start',m.LAST_COMMAND['operation'])
        self.assertNotIn('CANARY',json.dumps(m.LAST_COMMAND))

    def test_existing_nine_asset_snapshot_revalidated_without_expansion_or_writes(self):
        # Real inspector hashes the published files again; only root ownership
        # checks are adapted to the unprivileged test account.
        spec=importlib.util.spec_from_file_location('snapshot_inspector',SCRIPT.parent/'inspect_selected_datasets.py')
        inspector=importlib.util.module_from_spec(spec);spec.loader.exec_module(inspector)
        saved=sorted(set(m.GROUPS['NO'])|set(m.GROUPS['FR']));selected=sorted(m.FILES)
        backup=self.root/'private';backup.mkdir(mode=0o700);snapshot=backup/'snapshot';snapshot.mkdir(mode=0o750);snapshot.chmod(0o750)
        selection=dict(inspector.SELECTION);acquisition=[]
        def put(key,body):
            path=snapshot/m.FILES[key][1];path.parent.mkdir(exist_ok=True,mode=0o750);path.parent.chmod(0o750);path.write_bytes(body);path.chmod(0o440)
            selection[key]=(*selection[key][:2],hashlib.sha256(body).hexdigest())
        for key in saved:
            if m.FILES[key][2]=='raw':put(key,b'fixture '+key.encode())
        for country in ('NO','FR'):
            source,release,keys,manifest,_=inspector.SOURCES[country];decl=[]
            for key in keys:
                body=(snapshot/m.FILES[key][1]).read_bytes();digest=hashlib.sha256(body).hexdigest()
                decl.append({'key':selection[key][0].split('/')[-1],'bytes':len(body),'sha256':digest})
                acquisition.append({'key':selection[key][0],'bytes':len(body),'sha256':digest})
            put(manifest,json.dumps({'schemaVersion':'offmenu-collection/1','sourceId':source,'releaseId':release,'status':'normalized','sourceFiles':decl,'license':inspector.LICENSES[country]}).encode())
        put('NATIONAL_ACQUISITION',json.dumps(acquisition).encode())
        stored=backup/'selection.json';stored.write_text(json.dumps(saved));stored.chmod(0o600)
        old=backup/'approved-inspector.py';old.write_bytes(b'old immutable leaf');old.chmod(0o600)
        before={p:(p.read_bytes(),m.signature(p.stat())) for p in backup.rglob('*') if p.is_file()}
        report={'sourceBytesRead':0,'sourceBytesWritten':0,'snapshotBytesWritten':0,'assets':{},'sources':{}}
        runner=SimpleNamespace(pw_uid=os.getuid(),pw_gid=os.getgid())
        regular=m.regular_bytes
        def directory(path,runner,create=False,stage=False):
            self.assertFalse(create);self.assertEqual(0o750,path.stat().st_mode&0o777)
        # Adapt root ownership at the directory-entry boundary only; the real
        # inventory still enforces exact paths, directories, modes, group and links.
        original_scandir=m.os.scandir
        class Entry:
            def __init__(self,entry):self.entry=entry;self.name=entry.name
            def is_dir(self,**kwargs):return self.entry.is_dir(**kwargs)
            def stat(self,**kwargs):
                values=list(self.entry.stat(**kwargs));values[4]=0
                return os.stat_result(values)
        @contextlib.contextmanager
        def fixture_scandir(path):
            with original_scandir(path) as entries:yield (Entry(entry) for entry in entries)
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(inspector,'SELECTION',selection))
            stack.enter_context(patch.object(m,'BACKUP',backup));stack.enter_context(patch.object(m,'SCAFFOLD',snapshot))
            stack.enter_context(patch.object(m,'protected_directory'));stack.enter_context(patch.object(m,'safe_parents'))
            stack.enter_context(patch.object(m,'snapshot_directory',side_effect=directory))
            stack.enter_context(patch.object(m,'reference_parser',return_value=vars(inspector)))
            stack.enter_context(patch.object(m,'regular_bytes',side_effect=lambda path,cap:regular(path,cap,owner=os.getuid())))
            stack.enter_context(patch.object(m.os,'scandir',side_effect=fixture_scandir))
            stack.enter_context(patch.object(m,'anchored_source',side_effect=AssertionError('original read')))
            stack.enter_context(patch.object(m,'ensure_file',side_effect=AssertionError('overwrite')))
            result=m.create_snapshot(selected,runner,self.owner,{},report)
            self.assertEqual(saved,sorted(result));self.assertEqual('blocked',report['sources']['FI'])
            self.assertTrue(report['snapshotEvidence']['sources']['NO']['provenanceVerified'])
            self.assertTrue(report['snapshotEvidence']['sources']['FR']['provenanceVerified'])
            self.assertEqual(0,report['sourceBytesRead']);self.assertEqual(0,report['snapshotBytesWritten'])
            self.assertEqual(before,{p:(p.read_bytes(),m.signature(p.stat())) for p in before})
            unknown=snapshot/'metadata/unknown.json';unknown.write_bytes(b'preserve');unknown.chmod(0o440)
            with self.assertRaisesRegex(m.Blocked,'snapshot-unrecognized-file'):m.create_snapshot(selected,runner,self.owner,{},report)
            self.assertEqual(b'preserve',unknown.read_bytes());unknown.unlink()
            # A private snapshot with changed bytes must fail; prior selection alone is insufficient.
            raw=snapshot/m.FILES['NO_EN_FOODS'][1];raw.chmod(0o640);raw.write_bytes(b'drift');raw.chmod(0o440)
            with self.assertRaisesRegex(m.Blocked,'existing-snapshot-evidence-drift'):
                m.create_snapshot(selected,runner,self.owner,{},report)


    def test_failed_start_refresh_preserves_operation_and_226_state(self):
        m.LAST_PROPERTIES=self.ready_properties()
        m.LAST_COMMAND={'operation':'start','exitCode':1,'errno':None,'timedOut':False}
        failed=self.ready_properties(ActiveState='failed',SubState='failed',Result='exit-code',ExecMainStatus='226')
        def refresh(timeout):
            self.assertEqual(2,timeout)
            m.LAST_COMMAND={'operation':'show','exitCode':0,'errno':None,'timedOut':False}
            return failed
        diagnostics={}
        with patch.object(m,'properties',side_effect=refresh):
            m.record_failure(diagnostics,'failure',m.Blocked('system-command-failed'),None,refresh=True)
        self.assertEqual(226,diagnostics['failure']['numbers']['ExecMainStatus'])
        self.assertEqual('start',diagnostics['failureDetail']['command']['operation'])
        self.assertEqual(1,diagnostics['failureDetail']['command']['exitCode'])
        self.assertEqual('fresh',diagnostics['failureSample'])

    def test_failed_diagnostic_sample_never_mislabels_prior_state(self):
        for phase in ('failure','rollback'):
            m.LAST_PROPERTIES=self.ready_properties()
            m.LAST_COMMAND={'operation':'start','exitCode':1,'errno':None,'timedOut':False}
            diagnostics={phase:m.property_evidence(m.LAST_PROPERTIES)}
            with patch.object(m,'properties',side_effect=PermissionError(errno.EACCES,'CANARY')):
                m.record_failure(diagnostics,phase,m.Blocked('system-command-failed'),None,refresh=True)
            self.assertNotIn(phase,diagnostics);self.assertEqual('unavailable',diagnostics[phase+'Sample'])
            self.assertEqual(errno.EACCES,diagnostics[phase+'SampleDetail']['errno'])
            self.assertNotIn('CANARY',json.dumps(diagnostics))


    def test_systemd_vendor_parser_exact_bind_regression(self):
        tool=Path('/usr/bin/systemd-analyze')
        if not tool.is_file():self.skipTest('vendor systemd-analyze unavailable')
        runtime=self.root/'runtime';runtime.mkdir(mode=0o700)
        unit=self.root/'bind-probe.service'
        pair=m.bindings([])[0]
        observed='09e9cae237096581d641e2653aabfda7bb590581a82254d288b61acc86086149'
        for broken in (True,False):
            body='[Service]\nExecStart=/usr/bin/true\nBindReadOnlyPaths="'+pair+'"\n' if broken else '[Service]\nExecStart=/usr/bin/true\n'+m.dropin_bytes([]).decode().split('[Service]\n')[1]
            unit.write_text(body)
            result=subprocess.run([str(tool),'--user','verify','--man=no',str(unit)],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=20,
                env={'PATH':'/usr/bin:/bin','LANG':'C','XDG_RUNTIME_DIR':str(runtime),'SYSTEMD_LOG_LEVEL':'debug','SYSTEMD_LOG_TARGET':'console','SYSTEMD_COLORS':'0'})
            self.assertEqual(0,result.returncode,result.stdout[-2000:])
            parsed=[line.strip().split(': ',1)[1] for line in result.stdout.decode().splitlines() if line.strip().startswith('BindReadOnlyPaths: ')]
            expected=pair+':'+pair+':rbind' if broken else pair+':rbind'
            self.assertIn(expected,parsed)
            values=self.ready_properties([]);values['BindReadOnlyPaths']=expected
            if broken:
                self.assertEqual(observed,hashlib.sha256(expected.encode()).hexdigest())
                with self.assertRaisesRegex(m.Blocked,'service-mount-drift'):m.verify_properties(values,[])
            else:m.verify_properties(values,[])

    def test_fixed_mapping_rejects_all_quoting_and_option_variants(self):
        values=self.ready_properties([]);pair=m.bindings([])[0]
        for bad in (pair, '"'+pair+'":rbind',pair+':rbind:rbind',pair+':bind',pair+':'+pair+':rbind',pair+'\\x20:rbind',pair+':rbind '+pair+':rbind'):
            with self.subTest(bad=bad),self.assertRaisesRegex(m.Blocked,'service-mount-drift'):m.verify_properties({**values,'BindReadOnlyPaths':bad},[])
        for bad in ('/fixed path','/fixed\tpath','/fixed%path','/fixed:path','/fixed"path','/fixed\\path'):
            with patch.object(m,'CACHE',bad),self.assertRaisesRegex(m.Blocked,'invalid-fixed-path'):m.dropin_bytes([])

    def test_configured_preflight_failure_rolls_back_without_stop(self):
        original=m.configured_preflight
        def fail(selected,runner,baseline,report):
            values=m.properties();pair=m.bindings(selected)[0]
            values['BindReadOnlyPaths']=pair+':'+pair+':rbind'
            with patch.object(m,'properties',return_value=values):original(selected,runner,baseline,report)
        with patch.object(m,'configured_preflight',side_effect=fail):result,commands,drop,backup=self.mocked_apply()
        self.assertEqual('service-mount-drift',result['errorCode']);self.assertTrue(result['rollbackRestored'])
        self.assertTrue(result['serviceReady']);self.assertFalse(result['serviceRestarted']);self.assertFalse(drop.exists())
        self.assertFalse(result['readOnlyMountsVerified']);self.assertEqual([],result['effectiveMountAssets'])
        self.assertFalse(result['serviceDiagnostics']['configured']['properties']['BindReadOnlyPaths']['match'])
        self.assertFalse(result['serviceDiagnostics']['preflightSameProcess'])
        self.assertEqual([['/usr/bin/systemd-analyze','verify',str(m.UNIT)],['/usr/bin/systemctl','daemon-reload'],['/usr/bin/systemctl','daemon-reload']],commands)

    def test_configured_preflight_requires_same_pid_and_start_time(self):
        selected=sorted(m.GROUPS['NO'])
        for values,start in ((self.ready_properties(selected,MainPID='456'),b'1'),(self.ready_properties(selected),b'2')):
            report={}
            with patch.object(m,'properties',return_value=values),patch.object(m,'process_start_time',return_value=start),patch.object(m,'runtime_identity') as identity:
                with self.assertRaisesRegex(m.Blocked,'service-preflight-process-changed'):m.configured_preflight(selected,self.runner,(123,b'1'),report)
                identity.assert_not_called()
            self.assertFalse(report['serviceDiagnostics']['preflightSameProcess'])

    def test_process_start_time_parses_comm_parentheses(self):
        fields=[b'S']+[b'0']*18+[b'12345']+[b'0']*4
        with patch.object(m,'bounded_read',return_value=b'123 (strange ) comm) '+b' '.join(fields)):
            self.assertEqual(b'12345',m.process_start_time(123))

    def test_readability_uses_exact_mounted_paths_and_real_file_reads(self):
        cache=self.root/'cache';keys=sorted(m.FILES);observations={}
        for key in keys:
            path=cache/m.FILES[key][1];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'PRIVATE-DATA');observations[key]=path.stat()
        result=m.readability_record()
        with patch.object(m,'CACHE',str(cache)):
            m.read_runner_files(keys,observations,result)
        self.assertEqual(keys,result['checkedAssets']);self.assertEqual('verified',result['status'])
        self.assertEqual('complete',result['stage']);self.assertNotIn('PRIVATE-DATA',json.dumps(result))
        self.assertIn('FR_WORKBOOK',result['checkedAssets'])

    def test_readability_reports_exact_failed_asset_and_keeps_prior_checks(self):
        cache=self.root/'cache';keys=sorted(m.FILES)[:2];observations={}
        for key in keys:
            path=cache/m.FILES[key][1];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'data');observations[key]=path.stat()
        (cache/m.FILES[keys[1]][1]).unlink()
        result=m.readability_record()
        with patch.object(m,'CACHE',str(cache)),self.assertRaises(FileNotFoundError):m.read_runner_files(keys,observations,result)
        self.assertEqual([keys[0]],result['checkedAssets']);self.assertEqual(keys[1],result['failedAsset'])
        self.assertEqual('files',result['stage'])

    def test_readability_identity_and_symlink_fail_closed(self):
        key='FR_WORKBOOK';cache=self.root/'cache';path=cache/m.FILES[key][1];path.parent.mkdir(parents=True);path.write_bytes(b'first');observations={key:path.stat()}
        result=m.readability_record();path.write_bytes(b'changed')
        with patch.object(m,'CACHE',str(cache)),self.assertRaisesRegex(m.Blocked,'runner-readability-identity-mismatch'):m.read_runner_files([key],observations,result)
        path.unlink();path.symlink_to(self.root/'CANARY')
        with patch.object(m,'CACHE',str(cache)),self.assertRaises(OSError):m.read_runner_files([key],observations,result)
        self.assertEqual(key,result['failedAsset']);self.assertEqual([],result['checkedAssets'])


    def test_stop_attempt_failure_still_restores_baseline(self):
        result,commands,drop,backup=self.mocked_apply(fail_stop=True)
        self.assertEqual('system-command-timeout',result['errorCode']);self.assertTrue(result['rollbackRestored'])
        self.assertFalse(drop.exists());self.assertTrue(result['serviceReady'])
        self.assertEqual(2,commands.count(['/usr/bin/systemctl','stop',m.SERVICE]))
        self.assertEqual(1,commands.count(['/usr/bin/systemctl','start',m.SERVICE]))

    def test_namespace_preflight_failure_preserves_baseline_without_stop(self):
        result,commands,drop,backup=self.mocked_apply(fail_readability=True)
        self.assertEqual('runner-readability-failed',result['errorCode']);self.assertTrue(result['rollbackRestored'])
        self.assertFalse(drop.exists());self.assertFalse(result['serviceRestarted'])
        self.assertEqual(errno.EPERM,result['runnerReadability']['errno'])
        self.assertFalse(any(args[1] in {'stop','start'} for args in commands))

    def readability_fork_fixture(self,keys,observations,report,timeout=5,read_effect=None):
        # Real fork/pipe/deadline/reaping and file reads; all namespace/root and
        # credential mutations are replaced with checked, ordered fixtures.
        runner=SimpleNamespace(pw_uid=os.getuid(),pw_gid=os.getgid())
        calls=[]
        lib=SimpleNamespace(setns=lambda fd,kind:calls.append('setns') or 0)
        original=m.read_runner_files
        def read(selected,obs,result):
            self.assertEqual(['setns','fchdir','chroot','chdir','groups','gid','uid'],calls)
            if read_effect:return read_effect(selected,obs,result)
            return original(selected,obs,result)
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(m.ctypes,'CDLL',return_value=lib))
            for name,label in [('fchdir','fchdir'),('chroot','chroot'),('chdir','chdir'),('setgroups','groups'),('setgid','gid'),('setuid','uid')]:
                stack.enter_context(patch.object(m.os,name,side_effect=lambda *args,label=label:calls.append(label)))
            stack.enter_context(patch.object(m.os,'getgroups',return_value=[]))
            stack.enter_context(patch.object(m,'read_runner_files',side_effect=read))
            m.verify_runner_readability(os.getpid(),keys,observations,runner,report,timeout)

    def test_bounded_readability_child_proves_file_reads_after_identity_drop(self):
        key='FR_WORKBOOK';cache=self.root/'cache';path=cache/m.FILES[key][1];path.parent.mkdir(parents=True);path.write_bytes(b'DO-NOT-EXPORT')
        report={}
        with patch.object(m,'CACHE',str(cache)):
            self.readability_fork_fixture([key],{key:path.stat()},report)
        self.assertEqual({'status':'verified','stage':'complete','checkedAssets':[key],'failedAsset':None,'errno':None},report['runnerReadability'])
        self.assertNotIn('DO-NOT-EXPORT',json.dumps(report))

    def test_bounded_readability_child_reports_real_runner_permission_denial(self):
        key='NO_EN_FOODS';cache=self.root/'cache';path=cache/m.FILES[key][1];path.parent.mkdir(parents=True);path.write_bytes(b'DO-NOT-EXPORT');path.chmod(0)
        self.addCleanup(path.chmod,0o600)
        report={}
        with patch.object(m,'CACHE',str(cache)),self.assertRaisesRegex(m.Blocked,'runner-readability-failed'):
            self.readability_fork_fixture([key],{key:path.stat()},report)
        self.assertEqual('files',report['runnerReadability']['stage']);self.assertEqual(key,report['runnerReadability']['failedAsset'])
        self.assertEqual(errno.EACCES,report['runnerReadability']['errno']);self.assertEqual([],report['runnerReadability']['checkedAssets'])

    def test_bounded_readability_timeout_reaps_child(self):
        report={};waits=[];waitpid=m.os.waitpid
        def wait(child,flags):
            result=waitpid(child,flags);waits.append((child,flags,result));return result
        with patch.object(m.os,'waitpid',side_effect=wait),self.assertRaisesRegex(m.Blocked,'runner-readability-timeout'):
            self.readability_fork_fixture([],{},report,timeout=0.05,read_effect=lambda *args:m.time.sleep(10))
        self.assertTrue(waits);self.assertEqual(0,waits[-1][1]);self.assertEqual(waits[-1][0],waits[-1][2][0])
        with self.assertRaises(ChildProcessError):waitpid(waits[-1][0],os.WNOHANG)

    def test_readability_checks_never_run_for_terminal_start_failure(self):
        report,now,mounts=self.await_fixture(self.ready_properties([],ActiveState='failed',SubState='failed',Result='exit-code',MainPID='0'))
        with patch.object(m,'verify_runner_readability') as readable,self.assertRaisesRegex(m.Blocked,'service-start-failed'):
            m.await_ready([],self.runner,{},report,'after')
        readable.assert_not_called()


if __name__=='__main__':unittest.main()
