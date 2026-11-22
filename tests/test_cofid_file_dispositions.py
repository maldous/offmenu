"""Tiny synthetic XLSX fixtures only; no provider assets or permissions."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import openpyxl

_PATH = Path(__file__).resolve().parents[1] / 'tools/data-processing/collect_national.py'
_SPEC = importlib.util.spec_from_file_location('collect_national', _PATH)
COLLECT = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(COLLECT)

def workbook(path, rows):
    book = openpyxl.Workbook()
    book.remove(book.active)
    for name in ['1.3 Proximates', '1.4 Inorganics', '1.5 Vitamins']:
        sheet = book.create_sheet(name)
        for row in [
            ['Code', 'Food', 'Description', 'Group', None, 'References', 'Footnote', 'Protein (g)', 'Fatty acid (g)/100g FA'],
            [None] * 7 + ['PROT', 'FAFIELD'], [None] * 7 + ['Protein', 'Fatty acid'],
            *rows,
        ]:
            sheet.append(row)
    book.save(path)
    book.close()

class CoFIDDispositionTest(unittest.TestCase):
    def test_two_workbooks_report_distinct_operations_and_unchanged_native_bases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); inputs=root/'synthetic-inputs'; inputs.mkdir()
            current=inputs/'cofid2021.xlsx'; old=inputs/'cofid-old-foods.xlsx'
            workbook(current,[
                ['0007','Fictional solid','solid','A',None,'synthetic reference','synthetic note',2.1,3.2],
                ['0007','Fictional drink','drink','Q',None,'synthetic reference','synthetic note',4.3,5.4],
            ])
            workbook(old,[['0099','Fictional held',None,'A',None,None,None,9.9,8.8]])
            rows=COLLECT.national.cofid(inputs)
            paths=[root/'out-first',root/'out-second']
            manifests=[]
            for output in paths:
                COLLECT.publish_local('cofid',rows,inputs,output,'2021')
                manifests.append(json.loads((output/'cofid-2021/manifest.json').read_bytes()))
            manifest=manifests[0]
            by_name={entry['key']:entry for entry in manifest['fileDispositions']}
            self.assertEqual(set(by_name),{current.name,old.name})
            self.assertEqual(by_name[current.name]['disposition'],'processed')
            self.assertEqual(by_name[old.name]['disposition'],'held')
            for file in [current,old]:
                self.assertEqual(by_name[file.name]['sha256'],hashlib.sha256(file.read_bytes()).hexdigest())
                self.assertEqual(by_name[file.name]['bytes'],file.stat().st_size)
                self.assertTrue(by_name[file.name]['reason'])
            self.assertEqual(manifests[1]['fileDispositions'], manifest['fileDispositions'])
            self.assertEqual(manifest['normalizedRows'],2)
            with gzip.open(paths[0]/'cofid-2021/normalized.jsonl.gz','rt',encoding='utf8') as handle:
                records=[json.loads(line)[0] for line in handle]
            self.assertEqual(len({row['id'] for row in records}),2)
            facts=[row['data'] for row in records]
            self.assertEqual([f['identifiers'][0]['value'] for f in facts],['0007','0007'])
            self.assertEqual([f['foodName'] for f in facts],['Fictional solid','Fictional drink'])
            self.assertEqual([f['basis']['unit'] for f in facts],['g','ml'])
            self.assertEqual([f['nutrients']['protein']['value'] for f in facts],[2.1,4.3])
            self.assertEqual([f['nutrients']['cofid:FAFIELD']['basis']['unit'] for f in facts],['g-fatty-acids','g-fatty-acids'])
            with self.assertRaisesRegex(ValueError,'Immutable output exists'):
                COLLECT.publish_local('cofid',rows,inputs,paths[0],'2021')
            self.assertEqual(json.loads((paths[0]/'cofid-2021/manifest.json').read_bytes()),manifest)

    def test_absent_current_file_refuses_disposition(self):
        with self.assertRaisesRegex(ValueError,'current workbook is not inventoried'):
            COLLECT.cofid_file_dispositions([{'key':'cofid-old-foods.xlsx','bytes':1,'sha256':'a'*64}])

    def test_empty_or_partial_projection_leaves_no_release_and_allows_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); inputs=root/'synthetic-inputs'; inputs.mkdir()
            workbook(inputs/'cofid2021.xlsx',[
                ['0007','Fictional solid',None,'A',None,None,None,2.1,3.2],
                ['0008','Fictional drink',None,'Q',None,None,None,4.3,5.4],
            ])
            output=root/'synthetic-output'
            with self.assertRaisesRegex(ValueError,'emitted no normalized rows'):
                COLLECT.publish_local('cofid',[],inputs,output,'2021')
            self.assertFalse(output.exists())
            rows=COLLECT.national.cofid(inputs)
            broken=[rows[0],{**rows[1],'fixture-unserializable':object()}]
            with self.assertRaises(TypeError):
                COLLECT.publish_local('cofid',broken,inputs,output,'2021')
            self.assertEqual(list(output.iterdir()),[])
            COLLECT.publish_local('cofid',rows,inputs,output,'2021')
            manifest=json.loads((output/'cofid-2021/manifest.json').read_bytes())
            self.assertEqual(manifest['normalizedRows'],2)
            self.assertEqual(manifest['fileDispositions'][0]['disposition'],'processed')
            self.assertIn('was emitted',manifest['fileDispositions'][0]['reason'])
            self.assertIn('does not establish completeness',manifest['scope'])

    def test_dispositions_only_expose_allowlisted_file_metadata(self):
        entry={'key':'cofid2021.xlsx','bytes':10,'sha256':'a'*64,'private':'synthetic-not-emitted'}
        [item]=COLLECT.cofid_file_dispositions([entry])
        self.assertEqual(set(item),{'key','bytes','sha256','disposition','reason'})
