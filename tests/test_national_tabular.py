import csv
import dataclasses
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from offmenu.refresh import execution
from offmenu.refresh import national_tabular as national
from offmenu.refresh.core import RefreshError


def csv_file(path, headers, rows, delimiter=',', skip=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle, delimiter=delimiter)
        if skip: writer.writerow(['Synthetic fixture'])
        writer.writerow(headers); writer.writerows(rows)


def fixture(root, source):
    if source == 'cnf':
        (root / 'cnf-2015-csv.zip').write_bytes(b'authored synthetic archive placeholder; never extracted')
        tables = {
            'FOOD NAME': (['FoodID','FoodDescription','FoodDescriptionF','FoodGroupID','FoodSourceID','ScientificName'], [['1','Synthetic','Synthetique','G','S','']]),
            'NUTRIENT NAME': (['NutrientID','NutrientCode','NutrientUnit','NutrientName','NutrientNameF'], [['P','203','g','Protein','Proteine'],['U','999','ug','Other','Autre']]),
            'NUTRIENT SOURCE': (['NutrientSourceID'], [['S']]),
            'NUTRIENT AMOUNT': (['FoodID','NutrientID','NutrientSourceID','NutrientValue','NumberofObservations','StandardError','NutrientDateOfEntry'], [['1','P','S','1.25','2','0.1','2015'],['1','U','S','','','',''],['1','UNRESOLVED','S','3','','','']]),
        }
        # Authored opaque companions exercise the historical twelve-table gate;
        # these do not assert knowledge of complete publisher companion schemas.
        for i in range(8): tables['synthetic companion '+str(i)] = (['ID'], [['1']])
        for name, (head, rows) in tables.items(): csv_file(root / 'csv' / (name+'.csv'), head, rows)
    else:
        import openpyxl
        base = root / 'nz-extracted'; base.mkdir()
        wb = openpyxl.Workbook(); ws = wb.active
        ws.append(['Synthetic FOODfiles fixture']); ws.append(['FoodID','Food Name']); ws.append(['1','Synthetic'])
        wb.save(base/'ExcelFilesNamesx'); wb.close()
        csv_file(base/'UnabridgedCodes',['Code','Description'],[['PROT','Protein'],['FA','Fatty acid'],['UNKNOWN','Unknown']], '~', True)
        headers=['FoodID','Component Identifier','Matrix Unit Code','Value','Unit Code','Source Code','Value Type Code','Acquisition Type Code','Method Type Code','Method Indicator Code']
        rows=[['1','PROT','W','1.250','g','S','V','A','M','I'],['1','FA','F','< 0.1','g','S','V','A','M','I'],['1','UNKNOWN','N','-','mg','S','V','A','M','I']]
        csv_file(base/'UnabridgedDataFT',headers,rows,'~',True)
        archive=root/'nz-foodfiles-2024.msi'; archive.write_bytes(b'authored synthetic MSI placeholder; never executed')
        (root/'acquisition.json').write_text(json.dumps([{'key':archive.name,'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}]))


class NationalTabularTests(unittest.TestCase):
    def test_names_and_nested_inventory(self):
        for name in ['../x','/x','x//y','x/./y','x/../y','x\\y','C:x','x/','']:
            self.assertFalse(national.valid_input_name(name), name)
        self.assertTrue(national.valid_input_name('csv/FOOD NAME.csv'))
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'csv').mkdir(); (root/'csv/x').write_text('x')
            self.assertEqual({'csv/x'}, national.bundle_files(root))
            (root/'csv/link').symlink_to(root/'csv/x')
            with self.assertRaisesRegex(RefreshError,'symlink'): national.bundle_files(root)

    def test_inventory_rejects_unlisted_directories_and_depth(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'unexpected').mkdir(); (root/'unexpected/x').write_text('')
            with self.assertRaisesRegex(RefreshError,'bundle-set-mismatch'):
                national.bundle_files(root, {'csv/expected.csv'})
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); deep=root
            for _ in range(17): deep=deep/'d'; deep.mkdir()
            (deep/'x').write_text('')
            with self.assertRaisesRegex(RefreshError,'inventory-limit'):
                national.bundle_files(root)

    def test_both_pinned_collectors_deterministic_and_no_admissions(self):
        self.assertEqual({}, execution.ADMISSIONS)
        repo=Path(__file__).resolve().parents[1]
        for source in ['cnf','foodfiles']:
            with self.subTest(source=source), tempfile.TemporaryDirectory() as folder:
                root=Path(folder); bundle=root/'bundle'; bundle.mkdir(); fixture(bundle,source)
                pins=tuple((n,(bundle/n).stat().st_size,hashlib.sha256((bundle/n).read_bytes()).hexdigest()) for n in sorted(national.bundle_files(bundle)))
                entry=execution.Admission(source,execution._release(source)['releaseId'],pins,'2026-10-17T00:00:00Z','a'*64,'b'*64,1)
                with patch.dict(execution.ADMISSIONS,{source:entry}):
                    first=execution.execute(source,bundle,root/'first',repository=repo)
                    second=execution.execute(source,bundle,root/'second',repository=repo)
                self.assertEqual(first,second)
                self.assertEqual((root/'first/normalized.jsonl.gz').read_bytes(),(root/'second/normalized.jsonl.gz').read_bytes())
                row=json.loads((root/'first/candidate.jsonl').read_text())[0]
                self.assertEqual(entry.release_id,row['provenance']['releaseId'])
                self.assertIsNone(first['acceptedCount'])
                nutrients=row['data']['nutrients']
                self.assertEqual(1.25,nutrients['protein']['value'])
                if source=='cnf':
                    self.assertEqual('µg',nutrients['cnf:U']['unit'])
                    self.assertIsNone(nutrients['cnf:U']['value'])
                    self.assertEqual('unknown',nutrients['cnf:UNRESOLVED']['unit'])
                    self.assertIn('discovery-release-mismatch',execution.execution_plan({'sources':[{'sourceId':'cnf','historicalCapability':execution._release('cnf')} ]})['sources'][0]['errors'])
                else:
                    self.assertEqual('1.250',nutrients['protein']['sourceValue'])
                    self.assertEqual({'amount':100,'unit':'source-matrix:F'},nutrients['foodfiles:FA']['basis'])
                    self.assertEqual('less-than',nutrients['foodfiles:FA']['qualifier'])
                    self.assertEqual(0.1,nutrients['foodfiles:FA']['limit'])
                    self.assertIn('https://foodcomposition.co.nz/terms/',row['provenance']['rights'])
                with self.assertRaisesRegex(RefreshError,'release-not-supported'):
                    execution.verify_contract(dataclasses.replace(entry,release_id='2026'),bundle)
                (bundle/'extra').write_text('not pinned')
                with self.assertRaisesRegex(RefreshError,'bundle-set-mismatch'): execution.verify_contract(entry,bundle)

    def test_cnf_preflight_blocks_silent_collisions_and_nonfinite(self):
        from types import SimpleNamespace
        module=SimpleNamespace(MAP={'203':'protein'})
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); fixture(root,'cnf')
            national.preflight('cnf',root,module)
            path=root/'csv/NUTRIENT NAME.csv'
            with path.open('a') as handle: handle.write('P,203,g,duplicate,duplicate\n')
            with self.assertRaisesRegex(RefreshError,'duplicate'): national.preflight('cnf',root,module)
            fixture(root,'cnf')
            path=root/'csv/NUTRIENT AMOUNT.csv'; path.write_text(path.read_text().replace('1.25','NaN'))
            with self.assertRaisesRegex(RefreshError,'nonfinite'): national.preflight('cnf',root,module)

    def test_semantics_preserve_unknowns_but_block_unreviewed_units(self):
        import copy
        for source in national.NATIONAL_FAMILIES:
            row={'kind':'nutrientProfile','schemaVersion':'1.0',
                 'provenance':{'sourceId':source,'releaseId':execution._release(source)['releaseId']},
                 'data':{'basis':{'amount':100,'unit':'g'},'nutrients':{'protein':{'unit':'g','value':None,'qualifier':'trace'}}}}
            original=copy.deepcopy(row)
            self.assertEqual([],national.national_semantic_errors(source,row,allowed_units=('g',),basis_units=('g',)))
            self.assertEqual(original,row)
            self.assertIn('national-reviewed-unit-contract-missing',national.national_semantic_errors(source,row))
            row['data']['nutrients']['protein']['basis']={'amount':100,'unit':'source-matrix:F'}
            self.assertIn('national-nutrient-basis-unqualified',national.national_semantic_errors(source,row,allowed_units=('g',),basis_units=('g',)))
        row['provenance']={'sourceId':'cnf','releaseId':'2015'}
        row['data']['nutrients']={'cnf:unresolved':{'unit':'unknown','name':'Unresolved CNF nutrient X','value':1,'qualifier':'source-reported'}}
        diagnostics=national.national_semantic_errors('cnf',row,allowed_units=('g','unknown'),basis_units=('g',))
        self.assertIn('national-nutrient-definition-unresolved',diagnostics)
        self.assertIn('national-nutrient-unit-unqualified',diagnostics)
        self.assertEqual(['national-source-not-supported'],national.national_semantic_errors('fineli',{}))

    def test_foodfiles_duplicate_definitions_fail_without_success_receipt(self):
        repo=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); bundle=root/'bundle'; bundle.mkdir(); fixture(bundle,'foodfiles')
            with (bundle/'nz-extracted/UnabridgedCodes').open('a') as handle:
                handle.write('PROT~Conflicting definition\n')
            pins=tuple((n,(bundle/n).stat().st_size,hashlib.sha256((bundle/n).read_bytes()).hexdigest()) for n in sorted(national.bundle_files(bundle)))
            entry=execution.Admission('foodfiles','2024-v01',pins,'2026-10-17T00:00:00Z','a'*64,'b'*64,1)
            with patch.dict(execution.ADMISSIONS,{'foodfiles':entry}):
                with self.assertRaisesRegex(RefreshError,'worker-failed'):
                    execution.execute('foodfiles',bundle,root/'bad',repository=repo)
            self.assertFalse((root/'bad/execution-receipt.json').exists())
            fixture_root=root/'valid'; fixture_root.mkdir(); fixture(fixture_root,'cnf')
            # A malformed peer cannot fabricate an admission for another family.
            with self.assertRaisesRegex(RefreshError,'admission-missing'):
                execution.execute('cnf',fixture_root,root/'other',repository=repo)

if __name__=='__main__': unittest.main()
