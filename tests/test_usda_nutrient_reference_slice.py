"""Generated ZIPs only; no retained source discovery or original-file reads."""
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('worker64_usda_slice',ROOT/'offmenu/refresh/usda_nutrient_reference_slice.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
SCRATCH=ROOT/'generated-slice-test-scratch';SCRATCH.mkdir(exist_ok=True)


def fixture(root, *, nutrient_rows=None, nutrient_header=None, nutrient_count=2):
    columns=['id','name','unit_name','nutrient_nbr','rank']
    data=nutrient_rows if nutrient_rows is not None else [['2','Generated fibre-specific energy','kJ','208','1.00'],['1','Generated micronutrient','µg','999','Tr']]
    sources=[('nutrient',nutrient_header or columns,data,nutrient_count),
             ('measure_unit',['id','name'],[['10','Generated portion descriptor']],1)]
    path=root/'source.zip';specs=[]
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for table,header,rows,expected in sources:
            stream=io.StringIO(newline='');writer=csv.writer(stream);writer.writerow(header);writer.writerows(rows)
            raw=stream.getvalue().encode();member='FoodData_Central_csv_2026-04-30/'+table+'.csv';archive.writestr(member,raw)
            h=hashlib.sha256()
            for native in sorted({v[0] for v in rows},key=lambda s:s.encode()):
                h.update((json.dumps(native,ensure_ascii=False,separators=(',',':'))+'\n').encode())
            specs.append({'table':table,'member':member,'columns':columns if table=='nutrient' else ['id','name'],
                'rows':expected,'bytes':len(raw),'crc32':zlib.crc32(raw),'nativeIdSha256':h.hexdigest()})
        archive.writestr('FoodData_Central_csv_2026-04-30/food_nutrient.csv','GENERATED FORBIDDEN BODY; must not parse')
    raw=path.read_bytes()
    return path,{'expected_sha256':hashlib.sha256(raw).hexdigest(),'expected_bytes':len(raw),'specs':specs}


class SliceTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory(dir=SCRATCH);self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()

    def test_selected_members_only_single_read_descriptor_and_raw_fields(self):
        path,args=fixture(self.root);opened=[];original=zipfile.ZipFile.open
        def tracked(archive,name,*a,**kw):
            opened.append(name.filename if isinstance(name,zipfile.ZipInfo) else name)
            return original(archive,name,*a,**kw)
        with patch.object(zipfile.ZipFile,'open',tracked):rows,receipt=m.read_selected_archive(path,**args)
        self.assertEqual(opened,[x['member'] for x in args['specs']]);self.assertEqual(len(rows),3)
        self.assertEqual([x['kind'] for x in rows],['NutrientDefinition','NutrientDefinition','Unit'])
        self.assertEqual(rows[0]['sourceFields']['rank'],'1.00');self.assertEqual(rows[1]['sourceFields']['rank'],'Tr')
        self.assertEqual(rows[1]['sourceFields']['unit_name'],'µg');self.assertTrue(all(x['language']=='und' for x in rows))
        self.assertTrue(all('unitId' not in x and 'foodReferenceId' not in x and 'quantity' not in x for x in rows))
        self.assertEqual(receipt['descriptorIdentityBefore'],receipt['descriptorIdentityAfter'])
        self.assertEqual(receipt['readBytesByStage']['hash'],args['expected_bytes'])
        self.assertGreater(receipt['sourceReadBytes'],args['expected_bytes']);self.assertLess(receipt['sourceReadBytes'],m.MAX_SOURCE)
        self.assertEqual(receipt['otherMemberBodiesParsed'],0);self.assertEqual(receipt['databaseOpens'],0)
        self.assertTrue(all(x['crcValidatedByZipReader'] for x in receipt['members']))

    def test_wrong_full_hash_stops_before_member_open(self):
        path,args=fixture(self.root);args['expected_sha256']='0'*64
        with patch.object(zipfile.ZipFile,'open',side_effect=AssertionError('member opened before verified hash')):
            with self.assertRaisesRegex(ValueError,'original-sha'):m.read_selected_archive(path,**args)

    def test_symlink_original_and_oversized_budget_rejected(self):
        path,args=fixture(self.root);link=self.root/'link.zip';link.symlink_to(path)
        with self.assertRaisesRegex(ValueError,'symlink'):m.read_selected_archive(link,**args)
        with self.assertRaisesRegex(ValueError,'limits'):m.read_selected_archive(path,**args,source_read_limit=m.MAX_SOURCE+1)
        with self.assertRaisesRegex(ValueError,'source-read-limit'):m.read_selected_archive(path,**args,source_read_limit=args['expected_bytes']-1)

    def test_header_count_and_native_id_witness_fail_closed(self):
        path,args=fixture(self.root,nutrient_header=['id','wrong','unit_name','nutrient_nbr','rank'])
        with self.assertRaisesRegex(ValueError,'header'):m.read_selected_archive(path,**args)
        path,args=fixture(self.root,nutrient_count=3)
        with self.assertRaisesRegex(ValueError,'count'):m.read_selected_archive(path,**args)
        path,args=fixture(self.root);args['specs'][0]['nativeIdSha256']='0'*64
        with self.assertRaisesRegex(ValueError,'native-id-witness'):m.read_selected_archive(path,**args)

    def test_duplicate_native_ids_and_member_metadata_conflicts_rejected(self):
        path,args=fixture(self.root,nutrient_rows=[['1','Generated A','g','1','1'],['1','Generated B','g','2','2']])
        with self.assertRaisesRegex(ValueError,'duplicate-native-id'):m.read_selected_archive(path,**args)
        path,args=fixture(self.root);args['specs'][0]['crc32']^=1
        with self.assertRaisesRegex(ValueError,'member-metadata'):m.read_selected_archive(path,**args)

    def test_descriptor_change_stops_before_member_parse(self):
        path,args=fixture(self.root);original=m.identity;calls=[0]
        def changed(s):
            calls[0]+=1;value=original(s)
            if calls[0]>=3:value[-1]+=1
            return value
        with patch.object(m,'identity',changed),patch.object(zipfile.ZipFile,'open',side_effect=AssertionError('opened after source changed')):
            with self.assertRaisesRegex(ValueError,'identity'):m.read_selected_archive(path,**args)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SliceTests))
    print('GENERATED_SLICE_PROOF='+json.dumps({'testsRun':result.testsRun,'success':result.wasSuccessful(),
        'errors':len(result.errors),'failures':len(result.failures),'actualOriginalReads':0,'actualRows':0,'fixturesOnly':True,
        'fixtureScratchEmpty':not any(SCRATCH.iterdir())},sort_keys=True))
    raise SystemExit(not result.wasSuccessful())
