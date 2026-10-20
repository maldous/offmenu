from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh.core import RefreshError, canonical
from offmenu.refresh.off_partition_witness import PartitionLimits, partition_stream


class PartitionWitnessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.limits=PartitionLimits(10000,65536,4*1024**2,8*1024**2,8*1024**2,30)
        self.rows=[{'code':'0001','name':'first payload'}, {'code':'0002','x':0},
                   {'code':1234},{'code':'0001','name':'other payload'},
                   {'code':'9999'}, {'code':'0001','name':'other payload'}]

    def run_rows(self,rows=None,name='output',limits=None):
        rows=self.rows if rows is None else rows
        return partition_stream((canonical(r) for r in rows),self.root/name,
            original_sha256='a'*64,expected_rows=len(rows),limits=self.limits if limits is None else limits)

    def assert_retained(self,error):
        state=error.partition_retained_state
        self.assertIs(state['automaticDeletion'],False)
        self.assertIs(state['resourceObligationActive'],True)
        self.assertTrue(Path(state['stageLocation']).is_dir())
        if state['databaseLocation'] is not None:
            p=Path(state['databaseLocation']);self.assertTrue(p.is_file())
            self.assertEqual(tuple(state['databaseIdentity']),(p.stat().st_dev,p.stat().st_ino))
        return state

    def file(self,name,output='output'):
        return [json.loads(l) for l in (self.root/output/name).read_bytes().splitlines()]

    def test_full_ordinal_partition_holds_first_and_all_members(self):
        r=self.run_rows();self.assertEqual(r['counts'],{'S':2,'C':3,'Q':1})
        self.assertEqual(r['repeatedKeyGroups'],1)
        occ=self.file('occurrences.jsonl');self.assertEqual([x['ordinal'] for x in occ],list(range(1,7)))
        self.assertEqual([x['status'] for x in occ],['C','S','Q','C','S','C'])
        self.assertEqual([x['ordinal'] for x in self.file('members.jsonl')],[1,4,6])
        group=self.file('groups.jsonl')[0];self.assertIsNone(group['selectedPrimary'])
        h=hashlib.sha256()
        for x in self.file('members.jsonl'):
            h.update(canonical({k:v for k,v in x.items() if k!='code'}))
        self.assertEqual(group['orderedMembersSha256'],h.hexdigest())

    def test_singletons_and_paired_id_digest_are_independent_candidates_only(self):
        r=self.run_rows();self.assertEqual([x['code'] for x in self.file('singletons.jsonl')],['0002','9999'])
        h=hashlib.sha256()
        for kind in ('nutrientProfile','product'):
            for code in ('0002','9999'):h.update(canonical('off:'+kind+':'+code))
        self.assertEqual(r['candidateSingletonProductProfileIdsSha256'],h.hexdigest())
        self.assertEqual(r['candidateSingletonProductProfileCount'],4)
        for key in ('sourceCustodyVerified','eligibleCleanScopeWitness','accepted','productSemanticsQualified','realScopeOrResourcesAdmitted'):
            self.assertIs(r[key],False)

    def test_late_conflict_and_identical_repeats_never_choose_primary(self):
        rows=[{'code':'0001'}]+[{'code':str(10000+i)} for i in range(100)]+[{'code':'0001'}]
        def stream():
            for row in rows:
                self.assertFalse((self.root/'output').exists())
                yield canonical(row)
        r=partition_stream(stream(),self.root/'output',original_sha256='a'*64,expected_rows=len(rows),limits=self.limits)
        self.assertEqual(r['counts'],{'S':100,'C':2,'Q':0})
        self.assertIsNone(self.file('groups.jsonl')[0]['selectedPrimary'])

    def test_classification_independent_of_input_order_but_ordinals_preserved(self):
        a=self.run_rows();b=self.run_rows(list(reversed(self.rows)),name='reverse')
        self.assertEqual(a['counts'],b['counts'])
        self.assertEqual([x['code'] for x in self.file('groups.jsonl')],[x['code'] for x in self.file('groups.jsonl','reverse')])
        self.assertNotEqual(self.file('members.jsonl'),self.file('members.jsonl','reverse'))

    def test_no_coercion_and_no_raw_payload_copy_or_semantic_admission(self):
        rows=[{'code':code,'private':'DO_NOT_COPY_PAYLOAD'} for code in
              ('0001','00001',1234,' 1234','１２３４','123','1'*33,True,None)]
        r=self.run_rows(rows);self.assertEqual(r['counts'],{'S':2,'C':0,'Q':7})
        for path in (self.root/'output').iterdir():self.assertNotIn(b'DO_NOT_COPY_PAYLOAD',path.read_bytes())
        self.assertFalse((self.root/'output/index.sqlite').exists())
        retained=r['retainedScratch'];db=Path(retained['databaseLocation'])
        self.assertTrue(db.is_file());self.assertIs(retained['automaticDeletion'],False)
        self.assertIs(retained['resourceObligationActive'],True)
        self.assertEqual(tuple(retained['databaseIdentity']),(db.stat().st_dev,db.stat().st_ino))
        self.assertEqual(db.stat().st_size,r['measurements']['databaseBytes'])
        self.assertNotIn(b'DO_NOT_COPY_PAYLOAD',db.read_bytes())
        q=self.file('occurrences.jsonl')[2];self.assertIsNone(q['code']);self.assertEqual(q['reason'],'native-code-invalid')

    def test_line_hash_and_canonical_hash_have_explicit_different_domains(self):
        line=b'{ "code": "0001" }\n'
        partition_stream([line],self.root/'output',original_sha256='a'*64,expected_rows=1,limits=self.limits)
        row=self.file('occurrences.jsonl')[0]
        self.assertEqual(row['rawLineSha256'],hashlib.sha256(line).hexdigest())
        self.assertEqual(row['canonicalBodySha256'],hashlib.sha256(canonical({'code':'0001'})).hexdigest())
        self.assertNotEqual(row['rawLineSha256'],row['canonicalBodySha256'])

    def test_invalid_json_framing_truncation_and_extra_rows_publish_nothing(self):
        cases=[([b'bad\n'],1),([b'{"code":"0001"}'],1),([b'[]\n'],1),
               ([b'{"a":1,"a":2}\n'],1),([b'{"x":NaN}\n'],1),
               ([canonical({'code':'0001'})],2),([canonical({'code':'0001'})]*2,1)]
        for lines,count in cases:
            with self.assertRaises(RefreshError) as failure:
                partition_stream(lines,self.root/'output',original_sha256='a'*64,expected_rows=count,limits=self.limits)
            self.assertFalse((self.root/'output').exists());self.assert_retained(failure.exception)

    def test_explicit_resource_caps_fail_closed_without_published_success(self):
        for limits in (replace(self.limits,max_rows=1),replace(self.limits,max_line_bytes=1),
                       replace(self.limits,max_expanded_bytes=1),replace(self.limits,max_output_bytes=1)):
            with self.assertRaises(RefreshError) as failure:self.run_rows(limits=limits)
            self.assertFalse((self.root/'output').exists())
            if hasattr(failure.exception,'partition_retained_state'):self.assert_retained(failure.exception)
            else:self.assertEqual(str(failure.exception),'partition-contract-invalid')
        rows=[{'code':str(100000+i)} for i in range(1000)]
        with self.assertRaises(RefreshError) as failure:self.run_rows(rows,limits=replace(self.limits,max_database_bytes=65536))
        self.assert_retained(failure.exception);self.assertFalse((self.root/'output').exists())

    def test_deadline_and_bad_contracts_fail_without_source_activation(self):
        with patch('offmenu.refresh.off_partition_witness.time.monotonic',side_effect=range(0,10000,100)):
            with self.assertRaises(RefreshError):self.run_rows()
        for limits in (replace(self.limits,max_rows=True),replace(self.limits,max_database_bytes=1),None):
            with self.assertRaises(RefreshError):
                partition_stream([],self.root/'output',original_sha256='a'*64,expected_rows=1,limits=limits)

    def test_no_overwrite_or_destination_race_cleanup(self):
        self.run_rows()
        with self.assertRaises(RefreshError):self.run_rows()
        self.assertTrue((self.root/'output/result.json').exists())
        def race():
            (self.root/'race').mkdir();(self.root/'race/keep').write_text('keep')
            yield canonical({'code':'0001'})
        with self.assertRaises(OSError):
            partition_stream(race(),self.root/'race',original_sha256='a'*64,expected_rows=1,limits=self.limits)
        self.assertEqual((self.root/'race/keep').read_text(),'keep')

    def test_parent_replacement_cannot_publish_unrelated_stage(self):
        parent=self.root/'parent';parent.mkdir();moved=self.root/'moved'
        def stream():
            yield canonical({'code':'0001'})
            stage=next(parent.glob('.off-partition-*'))
            parent.rename(moved);parent.mkdir()
            fake=parent/stage.name;fake.mkdir();(fake/'KEEP').write_text('unrelated')
            (fake/'index.sqlite').write_bytes(b'not the original db')
        with self.assertRaises(RefreshError) as failure:
            partition_stream(stream(),parent/'output',original_sha256='a'*64,expected_rows=1,limits=self.limits)
        fake=next(parent.glob('.off-partition-*'))
        self.assertEqual((fake/'KEEP').read_text(),'unrelated')
        self.assertFalse((parent/'output').exists())
        self.assertTrue(list(moved.iterdir()));self.assert_retained(failure.exception)

    def test_replaced_stage_is_not_recursively_deleted_on_iterator_failure(self):
        def stream():
            stage=next(self.root.glob('.off-partition-*'))
            stage.rename(self.root/'saved-owned')
            stage.mkdir();(stage/'KEEP').write_text('unrelated')
            raise RuntimeError('fixture failure')
            yield
        with self.assertRaisesRegex(RuntimeError,'fixture failure') as failure:
            partition_stream(stream(),self.root/'output',original_sha256='a'*64,expected_rows=1,limits=self.limits)
        replacement=list(self.root.glob('.off-partition-*'))
        self.assertEqual(len(replacement),1)
        self.assertEqual((replacement[0]/'KEEP').read_text(),'unrelated')
        state=self.assert_retained(failure.exception)
        saved=self.root/'saved-owned'
        self.assertTrue((saved/'index.sqlite').exists())
        self.assertEqual(state['stageIdentity'],(saved.stat().st_dev,saved.stat().st_ino))
        self.assertEqual(state['stageLocation'],str(saved))

    def test_parent_replacement_failure_cleanup_uses_original_parent_descriptor(self):
        parent=self.root/'parent';parent.mkdir();moved=self.root/'moved'
        def stream():
            stage=next(parent.glob('.off-partition-*'))
            parent.rename(moved);parent.mkdir()
            fake=parent/stage.name;fake.mkdir();(fake/'KEEP').write_text('unrelated')
            raise RuntimeError('fixture failure')
            yield
        with self.assertRaisesRegex(RuntimeError,'fixture failure') as failure:
            partition_stream(stream(),parent/'output',original_sha256='a'*64,expected_rows=1,limits=self.limits)
        self.assertTrue(list(moved.iterdir()));self.assert_retained(failure.exception)
        self.assertEqual((next(parent.glob('.off-partition-*'))/'KEEP').read_text(),'unrelated')

    def test_stage_replacement_at_eof_refuses_publication_and_reports_owned_relocation(self):
        def stream():
            yield canonical({'code':'0001'})
            stage=next(self.root.glob('.off-partition-*'));stage.rename(self.root/'saved-owned')
            stage.mkdir();(stage/'KEEP').write_text('unrelated');(stage/'index.sqlite').write_bytes(b'fake')
        with self.assertRaisesRegex(RefreshError,'partition-stage-custody-changed') as failure:
            partition_stream(stream(),self.root/'output',original_sha256='a'*64,expected_rows=1,limits=self.limits)
        self.assertFalse((self.root/'output').exists())
        self.assertTrue((self.root/'saved-owned/index.sqlite').exists());self.assert_retained(failure.exception)
        self.assertEqual((next(self.root.glob('.off-partition-*'))/'KEEP').read_text(),'unrelated')

    def test_actual_rename_swapped_source_never_returns_success(self):
        from offmenu.refresh import off_partition_witness as m
        real=m._rename_noreplace
        def swap(srcfd,src,dstfd,dst):
            os.rename(src,'saved-owned',src_dir_fd=srcfd,dst_dir_fd=srcfd)
            os.mkdir(src,dir_fd=srcfd)
            fd=os.open(src+'/KEEP',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600,dir_fd=srcfd)
            os.write(fd,b'unrelated');os.close(fd)
            return real(srcfd,src,dstfd,dst)
        with patch.object(m,'_rename_noreplace',side_effect=swap):
            with self.assertRaisesRegex(RefreshError,'partition-published-identity-mismatch') as failure:
                self.run_rows()
        # The syscall moved the replacement. Do not delete/rollback that entry
        # or call it a valid publication; the owned evidence remains retained.
        self.assertEqual((self.root/'output/KEEP').read_bytes(),b'unrelated')
        self.assertFalse((self.root/'output/result.json').exists())
        state=self.assert_retained(failure.exception)
        evidence=Path(state['evidenceLocation'])
        self.assertEqual(evidence.name,'saved-owned')
        self.assertTrue((evidence/'result.json').exists())
        self.assertEqual(tuple(state['evidenceIdentity']),(evidence.stat().st_dev,evidence.stat().st_ino))
        self.assertEqual(failure.exception.preserved_publication_location,str(self.root/'output'))

    def test_core_never_calls_pathname_deletion_on_success_or_failure(self):
        # Exit patches before TemporaryDirectory performs fixture-owner cleanup.
        from offmenu.refresh import off_partition_witness as m
        with patch.object(m.os,'unlink',side_effect=AssertionError('unsafe unlink')) as unlink, \
             patch.object(m.os,'rmdir',side_effect=AssertionError('unsafe rmdir')) as rmdir:
            r=self.run_rows()
            self.assertTrue(Path(r['retainedScratch']['databaseLocation']).exists())
            def broken():
                raise RuntimeError('generated iterator failure')
                yield
            with self.assertRaisesRegex(RuntimeError,'generated iterator failure') as failure:
                partition_stream(broken(),self.root/'failed',original_sha256='a'*64,expected_rows=1,limits=self.limits)
            self.assert_retained(failure.exception)
            unlink.assert_not_called();rmdir.assert_not_called()

    def test_replaced_database_leaf_preserves_both_inodes(self):
        def stream():
            yield canonical({'code':'0001'})
            stage=next(self.root.glob('.off-partition-*'))
            (stage/'index.sqlite').rename(stage/'relocated-owned-db')
            (stage/'index.sqlite').write_bytes(b'UNRELATED_REPLACEMENT')
        with self.assertRaisesRegex(RefreshError,'partition-stage-custody-changed') as failure:
            partition_stream(stream(),self.root/'output',original_sha256='a'*64,expected_rows=1,limits=self.limits)
        state=self.assert_retained(failure.exception)
        stage=Path(state['stageLocation'])
        self.assertEqual((stage/'index.sqlite').read_bytes(),b'UNRELATED_REPLACEMENT')
        self.assertEqual(state['databaseLocation'],str(stage/'relocated-owned-db'))
        self.assertTrue((stage/'relocated-owned-db').exists())
        self.assertFalse((self.root/'output').exists())

    def test_stage_open_failure_reports_created_but_unverified_retained_entry(self):
        from offmenu.refresh import off_partition_witness as m
        real=m.os.open
        def fail_stage_open(name,*args,**kwargs):
            if isinstance(name,str) and name.startswith('.off-partition-'):
                raise OSError('generated stage open failure')
            return real(name,*args,**kwargs)
        with patch.object(m.os,'open',side_effect=fail_stage_open):
            with self.assertRaisesRegex(OSError,'generated stage open failure') as failure:
                self.run_rows()
        state=failure.exception.partition_retained_state
        self.assertIsNone(state['stageIdentity']);self.assertIsNone(state['stageLocation'])
        self.assertIs(state['resourceObligationActive'],True)
        self.assertIs(state['automaticDeletion'],False)
        self.assertEqual([p.name for p in self.root.iterdir()],[state['createdStageEntry']])
        self.assertFalse((self.root/'output').exists())

    def test_sqlite_open_substitution_and_restoration_reports_actual_open_inode(self):
        from offmenu.refresh import off_partition_witness as m
        real=m.sqlite3.connect;actual=None;original=None
        def swap_open(path,*args,**kwargs):
            nonlocal actual,original
            path=Path(path);stage=path.parent.resolve()
            path.rename(stage/'held-original');path.write_bytes(b'')
            db=real(path,*args,**kwargs);db.execute('PRAGMA user_version').fetchone()
            path.rename(stage/'actual-sqlite-db');(stage/'held-original').rename(path)
            actual=stage/'actual-sqlite-db';original=stage/'index.sqlite'
            return db
        before=len(os.listdir('/proc/self/fd'))
        with patch.object(m.sqlite3,'connect',side_effect=swap_open):
            with self.assertRaisesRegex(RefreshError,'partition-sqlite-inode-mismatch') as failure:
                self.run_rows()
        state=self.assert_retained(failure.exception)
        self.assertFalse(state['databaseConnectionVerified'])
        self.assertEqual(state['databaseLocation'],str(actual))
        self.assertEqual(state['createdDatabaseLocation'],str(original))
        self.assertNotEqual(state['databaseIdentity'],state['createdDatabaseIdentity'])
        self.assertEqual(state['databaseBytes'],actual.stat().st_size)
        self.assertTrue(original.is_file());self.assertTrue(actual.is_file())
        self.assertFalse((self.root/'output').exists())
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_ambiguous_connect_descriptors_fail_closed_and_preserve_files(self):
        from offmenu.refresh import off_partition_witness as m
        real=m.sqlite3.connect;extra=None
        def extra_open(path,*args,**kwargs):
            nonlocal extra
            db=real(path,*args,**kwargs);db.execute('PRAGMA user_version').fetchone()
            extra=os.open(self.root/'unrelated',os.O_RDWR|os.O_CREAT|os.O_EXCL,0o600)
            os.write(extra,b'KEEP');return db
        before=len(os.listdir('/proc/self/fd'))
        try:
            with patch.object(m.sqlite3,'connect',side_effect=extra_open):
                with self.assertRaisesRegex(RefreshError,'partition-sqlite-descriptor-ambiguous') as failure:
                    self.run_rows()
            state=self.assert_retained(failure.exception)
            self.assertFalse(state['databaseConnectionVerified'])
            self.assertEqual(len(state['ambiguousConnectionFiles']),2)
            self.assertEqual((self.root/'unrelated').read_bytes(),b'KEEP')
            self.assertFalse((self.root/'output').exists())
        finally:
            if extra is not None:os.close(extra)
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_concurrent_setup_refused_and_success_bytes_use_bound_descriptor(self):
        from offmenu.refresh import off_partition_witness as m
        with patch.object(m.threading,'active_count',return_value=2):
            with self.assertRaisesRegex(RefreshError,'partition-sqlite-serialized-setup-required') as failure:
                self.run_rows()
        self.assert_retained(failure.exception)
        self.assertFalse(failure.exception.partition_retained_state['databaseConnectionVerified'])
        result=self.run_rows();state=result['retainedScratch']
        self.assertTrue(state['databaseConnectionVerified'])
        self.assertEqual(state['databaseIdentity'],state['createdDatabaseIdentity'])
        self.assertGreater(state['databaseBytes'],0)
        self.assertEqual(result['measurements']['databaseBytes'],state['databaseBytes'])


if __name__=='__main__':unittest.main()
