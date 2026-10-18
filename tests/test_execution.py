import dataclasses
import hashlib
from pathlib import Path
import tempfile
import unittest
from offmenu.refresh import execution
from offmenu.refresh.core import RefreshError

class ExecutionTests(unittest.TestCase):
    def test_no_production_admission(self):
        self.assertEqual({}, execution.ADMISSIONS)
        with self.assertRaisesRegex(RefreshError, 'execution-admission-missing'):
            execution.execute('afcd', '/missing', '/missing')

    def test_plan_exhaustive_and_deduplicated_family(self):
        release = execution._release('afcd')
        sources = [{'sourceId': str(i), 'historicalCapability': release} for i in range(1303)]
        sources[0]['holds'] = ['source-held']
        plan = execution.execution_plan({'sources': sources})
        self.assertEqual(1303, plan['sourceCount'])
        self.assertEqual(1303, len(plan['sources']))
        self.assertEqual(0, plan['productionAdmissions'])
        self.assertTrue(all(r['ttlSeconds'] >= 30 * 86400 for r in plan['sources']))
        self.assertTrue(all(r['acceptedCount'] is None for r in plan['sources']))

    def test_release_mismatch_and_missing_parser(self):
        plan = execution.execution_plan({'sources': [{'sourceId': 'cnf', 'historicalCapability': execution._release('cnf')}]})
        self.assertIn('discovery-release-mismatch', plan['sources'][0]['errors'])
        self.assertFalse(plan['sources'][0]['parserImplemented'])

    def test_contract_checks_exact_set_hash_time_and_links(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            files = execution.ADAPTERS['afcd']['files']
            for name in files:
                (root / name).write_bytes(b'fixture')
            pins = tuple((n, 7, hashlib.sha256(b'fixture').hexdigest()) for n in files)
            entry = execution.Admission('afcd', '3', pins, '2026-10-18T00:00:00Z', 'a'*64, 'b'*64, 1)
            execution.verify_contract(entry, root)
            with self.assertRaisesRegex(RefreshError, 'acquisition-time'):
                execution.verify_contract(dataclasses.replace(entry, acquired_at='unknown'), root)
            with self.assertRaisesRegex(RefreshError, 'acquisition-in-future'):
                execution.verify_contract(dataclasses.replace(entry, acquired_at='2999-01-01T00:00:00Z'), root)
            (root / files[0]).write_bytes(b'changed')
            with self.assertRaisesRegex(RefreshError, 'hash-mismatch'):
                execution.verify_contract(entry, root)
            (root / files[0]).unlink()
            (root / files[0]).symlink_to(root / files[1])
            with self.assertRaisesRegex(RefreshError, 'symlink'):
                execution.verify_contract(entry, root)

    def test_all_five_static_adapters_with_synthetic_workbooks(self):
        import openpyxl
        from unittest.mock import patch
        repository = Path(__file__).resolve().parents[1]
        if not (repository / 'scripts/import-afcd.py').exists():
            self.skipTest('requires composed repository with pinned legacy scripts')
        for source in execution.ADAPTERS:
            with self.subTest(source=source), tempfile.TemporaryDirectory() as folder:
                root = Path(folder); bundle = root / 'bundle'; bundle.mkdir()
                def book(name, sheets):
                    wb = openpyxl.Workbook(); wb.remove(wb.active)
                    for title, rows in sheets.items():
                        ws = wb.create_sheet(title)
                        for row in rows: ws.append(row)
                    wb.save(bundle / name)
                count = 1
                if source == 'afcd':
                    book('Food-Details.xlsx', {'Food details': [['Public Food Key', 'Food Description'], ['F1', 'Synthetic']]})
                    rows = [['Public Food Key', 'Class', 'Method', 'Name', 'Protein (g)'], ['F1', 'test', 'test', 'Synthetic', 1.0]]
                    book('Nutrient-profiles.xlsx', {'All solids & liquids per 100 g': rows, 'Liquids only per 100 mL': rows})
                    book('Nutrient-details.xlsx', {'Synthetic': [['metadata']]}); count = 2
                elif source == 'mext':
                    headers = [[None]*59 for _ in range(12)]
                    headers[11][6]='ENERC_KCAL'; headers[11][9]='PROT-'; headers[11][58]='VITC'
                    row=[None]*59; row[1]='00001'; row[3]='Synthetic'; row[6]=1; row[9]='Tr'; row[58]='(2)'
                    book(execution.ADAPTERS[source]['files'][0], {'main': headers+[row]})
                elif source == 'cofid':
                    rows=[['']*8, [None]*7+['PROT'], ['']*8, ['1','Synthetic','description','A',None,None,None,1.0]]
                    book('cofid2021.xlsx', {name:rows for name in ['1.3 Proximates','1.4 Inorganics','1.5 Vitamins']})
                elif source == 'germany-bls':
                    book('BLS_4_0_Daten_2025_DE.xlsx', {'main': [['id','de','en','PROT625 [g/100g]','method','reference'], ['1','Synthetic','Synthetic',1,'test','test']]})
                    book('BLS_4_0_Components_DE_EN.xlsx', {'main': [['x']*8, [None,'PROT625','protein','protein','g',None,None,None]]})
                else:
                    book('sweden-20260701.xlsx', {'main': [['2026-07-01'], ['100 gram'], ['name','id','group','Energy (kcal)','last'], ['Synthetic',1,'test',1,'x']]})
                    import json
                    path=bundle/'sweden-20260701.xlsx'
                    (bundle/'acquisition.json').write_text(json.dumps([{'key':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}]))
                pins=tuple((p.name,p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest()) for p in bundle.iterdir())
                entry=execution.Admission(source, execution._release(source)['releaseId'], pins, '2026-10-18T00:00:00Z','a'*64,'b'*64,count)
                with patch.dict(execution.ADMISSIONS,{source:entry}):
                    receipt=execution.execute(source,bundle,root/'output',repository=repository)
                if source == 'afcd':
                    # A valid timestamp/size .pyc must never replace pinned source.
                    import importlib.util, importlib._bootstrap_external, shutil
                    isolated=root/'poisoned-code'; (isolated/'scripts').mkdir(parents=True)
                    for filename in ['import-afcd.py','import-national-tables.py']:
                        codepath=isolated/'scripts'/filename
                        shutil.copyfile(repository/'scripts'/filename,codepath)
                        cache=Path(importlib.util.cache_from_source(str(codepath)));cache.parent.mkdir(exist_ok=True)
                        poison=compile("raise RuntimeError('unverified-bytecode-executed')",str(codepath),'exec')
                        cache.write_bytes(importlib._bootstrap_external._code_to_timestamp_pyc(poison,int(codepath.stat().st_mtime),codepath.stat().st_size))
                    with patch.dict(execution.ADMISSIONS,{source:entry}):
                        pinned=execution.execute(source,bundle,root/'source-only-output',repository=isolated)
                    self.assertEqual(count,pinned['normalizedRecords'])
                    from datetime import datetime, timezone, timedelta
                    from offmenu.refresh.global_run import _source, Limits
                    acquired = datetime(2026,10,18,tzinfo=timezone.utc)
                    metadata = {'sourceId':'discovery:S327'}
                    def bindings(age, output='stage-output'):
                        return execution.reviewed_bindings({source:(bundle,root/output)},repository=repository,clock=lambda: acquired+timedelta(days=age))
                    with patch.dict(execution.ADMISSIONS,{source:entry}):
                        binding=bindings(1)['discovery:S327']
                        small=_source(metadata,binding,Limits(),'reuse',False)
                        self.assertEqual('historical-parser-budget-insufficient',small['stages']['parse']['code'])
                        good=_source(metadata,binding,Limits(job_memory_bytes=1024**3),'reuse',False)
                        self.assertEqual('succeeded',good['stages']['validate']['status'])
                        self.assertIsNone(good['acceptedCount'])
                        self.assertFalse(good['selectedSourceComplete'])
                        for age, code in [(30,'historical-cache-expired'),(-1,'historical-cache-acquisition-in-future')]:
                            blocked=_source(metadata,bindings(age)['discovery:S327'],Limits(),'reuse',False)
                            self.assertEqual(code,blocked['stages']['acquire']['code'])
                        # Unsupported peers are independently diagnosed, never promoted.
                        peer=_source({'sourceId':'unmapped'},None,Limits(),'reuse',False)
                        self.assertEqual('reviewed-handler-binding-missing',peer['stages']['acquire']['code'])
                self.assertEqual(count,receipt['normalizedRecords'])
                self.assertIsNone(receipt['acceptedCount'])
                self.assertEqual('not-performed',receipt['qualification'])
                import gzip, json
                manifest=json.loads((root/'output/manifest.json').read_text())
                self.assertIsNone(manifest['counts']['accepted'])
                self.assertFalse(manifest['selectedScopeComplete'])
                self.assertNotIn('17 publisher',json.dumps(manifest))
                with gzip.open(root/'output/normalized.jsonl.gz','rb') as f:
                    self.assertEqual((root/'output/candidate.jsonl').read_bytes(),f.read())
                for line in (root/'output/candidate.jsonl').read_text().splitlines():
                    self.assertEqual(entry.acquired_at,json.loads(line)[0]['provenance']['fetchedAt'])


    def test_no_global_binding_from_parser_presence(self):
        self.assertEqual({}, execution.reviewed_bindings({'afcd':('/missing','/missing')}))
