from dataclasses import replace
import hashlib
import json
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
            with self.assertRaises(RefreshError):
                partition_stream(lines,self.root/'output',original_sha256='a'*64,expected_rows=count,limits=self.limits)
            self.assertFalse((self.root/'output').exists());self.assertEqual(list(self.root.iterdir()),[])

    def test_explicit_resource_caps_fail_closed_without_published_success(self):
        for limits in (replace(self.limits,max_rows=1),replace(self.limits,max_line_bytes=1),
                       replace(self.limits,max_expanded_bytes=1),replace(self.limits,max_output_bytes=1)):
            with self.assertRaises(RefreshError):self.run_rows(limits=limits)
            self.assertEqual(list(self.root.iterdir()),[])
        rows=[{'code':str(100000+i)} for i in range(1000)]
        with self.assertRaises(RefreshError):self.run_rows(rows,limits=replace(self.limits,max_database_bytes=65536))
        self.assertEqual(list(self.root.iterdir()),[])

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
        with self.assertRaises(RefreshError):
            partition_stream(stream(),parent/'output',original_sha256='a'*64,expected_rows=1,limits=self.limits)
        fake=next(parent.glob('.off-partition-*'))
        self.assertEqual((fake/'KEEP').read_text(),'unrelated')
        self.assertFalse((parent/'output').exists())
        self.assertEqual(list(moved.iterdir()),[])

    def test_replaced_stage_is_not_recursively_deleted_on_iterator_failure(self):
        def stream():
            stage=next(self.root.glob('.off-partition-*'))
            stage.rename(self.root/'saved-owned')
            stage.mkdir();(stage/'KEEP').write_text('unrelated')
            raise RuntimeError('fixture failure')
            yield
        with self.assertRaisesRegex(RefreshError,'partition-owned-stage-cleanup-incomplete') as failure:
            partition_stream(stream(),self.root/'output',original_sha256='a'*64,expected_rows=1,limits=self.limits)
        replacement=list(self.root.glob('.off-partition-*'))
        self.assertEqual(len(replacement),1)
        self.assertEqual((replacement[0]/'KEEP').read_text(),'unrelated')
        self.assertEqual(list((self.root/'saved-owned').iterdir()),[])
        self.assertEqual(failure.exception.retained_stage_identity,
                         ((self.root/'saved-owned').stat().st_dev,(self.root/'saved-owned').stat().st_ino))
        self.assertEqual(failure.exception.retained_stage_location,str(self.root/'saved-owned'))

    def test_parent_replacement_failure_cleanup_uses_original_parent_descriptor(self):
        parent=self.root/'parent';parent.mkdir();moved=self.root/'moved'
        def stream():
            stage=next(parent.glob('.off-partition-*'))
            parent.rename(moved);parent.mkdir()
            fake=parent/stage.name;fake.mkdir();(fake/'KEEP').write_text('unrelated')
            raise RuntimeError('fixture failure')
            yield
        with self.assertRaisesRegex(RuntimeError,'fixture failure'):
            partition_stream(stream(),parent/'output',original_sha256='a'*64,expected_rows=1,limits=self.limits)
        self.assertEqual(list(moved.iterdir()),[])
        self.assertEqual((next(parent.glob('.off-partition-*'))/'KEEP').read_text(),'unrelated')

    def test_stage_replacement_at_eof_refuses_publication_and_reports_owned_relocation(self):
        def stream():
            yield canonical({'code':'0001'})
            stage=next(self.root.glob('.off-partition-*'));stage.rename(self.root/'saved-owned')
            stage.mkdir();(stage/'KEEP').write_text('unrelated');(stage/'index.sqlite').write_bytes(b'fake')
        with self.assertRaisesRegex(RefreshError,'partition-owned-stage-cleanup-incomplete'):
            partition_stream(stream(),self.root/'output',original_sha256='a'*64,expected_rows=1,limits=self.limits)
        self.assertFalse((self.root/'output').exists())
        self.assertEqual(list((self.root/'saved-owned').iterdir()),[])
        self.assertEqual((next(self.root.glob('.off-partition-*'))/'KEEP').read_text(),'unrelated')


if __name__=='__main__':unittest.main()
