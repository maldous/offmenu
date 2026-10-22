"""Full next ./run against generated retained/cache fixtures and local bare Git."""
import gzip
from contextlib import closing
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import unittest

PACKAGE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PACKAGE))
def fixture(name):
    spec=importlib.util.spec_from_file_location('final_fixture_'+name,PACKAGE/'tests'/('test_'+name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
legacy=fixture('plan_runner')
recipes=fixture('ingest_acquired_recipes')
menus=fixture('ingest_acquired_menus')
catalog_fixture=fixture('ingest_acquired_catalog')
import ingest_engine
import ingest_catalog
from receipt_branch import BRANCH as RECEIPT_BRANCH


class FinalIngestIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.case=legacy.RunnerTests('test_success_commit_push_idempotent_and_unrelated_dirty_preserved')
        self.case.setUp();self.addCleanup(self.case.tearDown)
        self.cache=catalog_fixture.AcquiredCatalogTests('test_exact_50_bindings_and_no_broad_scandir')
        self.cache.setUp();self.addCleanup(self.cache.tearDown)
        self.root=self.case.root;self.git=self.case.git_at
        self.retained=self.case.base/'retained';self.retained.mkdir()
    def write(self,name,rows):
        path=self.retained/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(''.join(json.dumps(row)+'\n' for row in rows));return path
    def cache_payload(self,source,artifact):
        sid,name=source['id'],artifact['name']
        if sid=='foodista_common_pile':
            body=json.dumps(recipes.foodista(title='Generated '+name))+'\n'
            if name.startswith('00000'):body='{malformed}\n'+body
            return gzip.compress(body.encode())
        if sid=='forkrecipe':
            memory=io.BytesIO()
            with tarfile.open(fileobj=memory,mode='w:gz') as archive:
                raw=recipes.fork().encode();info=tarfile.TarInfo('root/recipes/fixture.js');info.size=len(raw);archive.addfile(info,io.BytesIO(raw))
            return memory.getvalue()
        if sid=='medlineplus_healthy_recipes':return recipes.medline(title='Generated '+name,language=artifact.get('language','en')).encode()
        if sid=='fr_cnous_menus':return menus.cnous_xml().replace('Soupe &amp; pois','Generated '+name).encode()
        values={'met_menu_cantine.json':menus.begles_menu(),'met_plat_cantine.json':menus.begles_dish(),
            'menus.json':menus.toulouse_menu(),
            'plats-extrait-de-datameal.json':{'code_plat':'007P','libelle_plat':'Generated','code_recette':'R01'},
            'denrees-extrait-de-datameal.json':{'code_denree':'D01','libelle_denree':'Generated','code_recette':'R01','lait':True},
            'liste-des-ft-des-denrees-de-la-cc-tls.json':{'code_denree':'D01','description':'Generated','filename':'https://example.invalid/no-fetch.pdf'}}
        return json.dumps([values[name]]).encode()
    def install(self):
        for source in self.cache.manifest['sources']:
            for artifact in source['artifacts']:
                raw=self.cache_payload(source,artifact)
                artifact['expected_bytes']=len(raw);artifact['max_bytes']=max(1024*1024,len(raw))
                if artifact.get('sha256'):artifact['sha256']=hashlib.sha256(raw).hexdigest()
                self.cache.put(source,artifact,raw)
        for pattern in ('*.py','*.json','*.sql'):
            for source in PACKAGE.glob(pattern):shutil.copy(source,self.root/'manual-action'/source.name)
        plan=json.loads((self.root/'manual-action/plan.json').read_text())
        self.assertEqual(plan['receipt_transport'],'isolated-branch-v1')
        catalog=self.root/'manual-action/ingest_catalog.py'
        catalog.write_text(catalog.read_text().replace("DEFAULT_ROOT = '/home/user/src/offmenu-data'",'DEFAULT_ROOT = '+repr(str(self.retained))).replace("'/home/user/Documents/Codex/2026-10-22/worker56-recipe-retention-audit/TERMINAL-HANDOFF.json'",repr(str(self.case.base/'missing-generated-report.json'))))
        acquired=self.root/'manual-action/ingest_acquired_catalog.py'
        acquired.write_text(acquired.read_text().replace("Path('/srv/offmenu-refresh/outputs/additional-sources-20261022/source-cache')",'Path('+repr(str(self.cache.root))+')'))
        (self.root/'manual-action/fetch-sources.json').write_text(json.dumps(self.cache.manifest))
        runner=self.root/'manual-action/plan_runner.py'
        runner.write_text(runner.read_text().replace('RETURN_DIR =',f'REMOTE_URLS.add({str(self.case.remote)!r})\nRETURN_DIR =',1))
        self.git(self.root,'add','manual-action');self.git(self.root,'commit','-m','Generated full next-ingest fixture release')
        self.git(self.root,'push','origin',legacy.m.BRANCH)
    def run_command(self):
        result=subprocess.run(['./run'],cwd=self.root,capture_output=True,text=True,timeout=120)
        self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        self.assertIn('Final domain summary',result.stdout)
        return result
    def db_rows(self,state):
        result={}
        for domain in ingest_engine.DOMAINS:
            path=state/('private-household' if domain in ('user_profiles','inventory') else '.')/'staging'/(domain+'.sqlite3')
            with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
                result[domain]=db.execute('SELECT source_key,source_version,record_id,content_sha256,updated_at FROM records ORDER BY 1,2,3').fetchall()
        return result
    def test_upgrade_reuses_existing_state_ingests_all_six_families_and_returns_evidence(self):
        def recipe(name):return {'id':name,'name':name,'ingredients':['1 g generated ingredient'],'instructions':['Generated instruction']}
        completed=self.write('world-recipes-common-input-20261014/completed.jsonl',[recipe('completed')])
        partial=self.write('world-recipes-common-input-20261014/partial.jsonl',[recipe(str(i)) for i in range(3)])
        self.write('off-2026-10-12-lf/products.jsonl',[{'code':'000123','product_name':'Generated product','nutriments':{'energy':1}}])
        self.write('wikidata-businesses-20261013-native/organizations.jsonl',[{'id':'Q123','name':'Generated organization'}])
        self.write('dietary-guidelines-20261013/guidelines.jsonl',[{'id':'fixture','title':'Generated guideline','url':'https://example.invalid/fixture'}])
        state=self.root/'.git/offmenu-runner/ingest'
        discovered=ingest_catalog.discover_sources({'roots':[str(self.retained)],'project_reports':[]})
        selected=[dict(row,domains=['recipes']) for row in discovered['sources'] if row['path'] in (str(completed),str(partial))]
        first=ingest_engine.run_ingest(selected,{'state_dir':str(state),'reserve_bytes':0,'batch_size':1,'max_rows_per_source':1,'terminal_progress':False})
        old_rows=self.db_rows(state)['recipes']
        self.assertEqual(len(old_rows),2)
        # Existing v1 job's canonical v2 receipt spool must survive the same
        # upgrade as the partial/completed data cursors, byte for byte.
        old_summary=legacy.m.Runner.ingest_summary(None,{'domains':first['domains'],'pending_work':first['pending_work']})
        old_receipt={'schema':'offmenu-run-receipt/2','job_id':'retained-eight-domain-ingest',
            'job_version':1,'operation':'retained_ingest_all','job_key':'1'*64,
            'implementation_sha256':'2'*64,'input_sha256':'3'*64,
            'observed_at':'2026-10-22T00:00:00Z','outcome':'partial','ingest':old_summary}
        old_raw=legacy.m.canonical(old_receipt)
        spool=state.parent/'ingest-pending'/Path(legacy.m.receipt_relpath(old_receipt)).name
        spool.parent.mkdir(parents=True,exist_ok=True)
        spool.write_bytes(legacy.m.canonical({'sha256':legacy.m.digest(old_raw),'receipt':old_receipt}))
        self.install()
        # Any attempt to iterate the already completed v1 source is a test failure;
        # adapter/source version remains identical across this orchestration upgrade.
        adapter=self.root/'manual-action/ingest_recipes.py'
        text=adapter.read_text();marker='def iter_records(domain, source, context, stats=None):'
        if marker not in text:
            marker=next(line for line in text.splitlines() if line.startswith('def iter_records('))
        text=text.replace(marker,marker+"\n    if domain == 'recipes' and source['path'].endswith('/completed.jsonl'):\n        raise AssertionError('completed_v1_reader_reentered')",1)
        adapter.write_text(text)
        self.git(self.root,'add','manual-action/ingest_recipes.py');self.git(self.root,'commit','-m','Generated no-replay assertion')
        self.git(self.root,'push','origin',legacy.m.BRANCH)
        code_head=self.case.head()
        self.run_command()
        report=json.loads((state/'last-report.json').read_text())
        self.assertEqual(report['domains']['recipes']['error_codes'],['JSONDecodeError'])
        self.assertGreater(report['domains']['recipes']['written'],40)
        for domain in ('barcodes','ingredients','dietary','suppliers','citations'):
            self.assertGreater(report['domains'][domain]['written'],0,(domain,report['domains'][domain]))
        first_derived=json.loads((state/'relational-targets.private.json').read_text())
        final_rows=self.db_rows(state)
        self.assertTrue(set(old_rows)<=set(final_rows['recipes']))
        catalog=json.loads((state/'catalog.private.json').read_text())
        acquired=[s for s in catalog['sources'] if s.get('acquired_adapter')]
        self.assertEqual(len(acquired),50)
        self.assertEqual(len({s['acquired_adapter'] for s in acquired}),6)
        self.assertEqual(report['ingest_evidence']['phase'],'post')
        self.assertIsNotNone(report['ingest_evidence']['performance']['domains']['recipes'][0])
        self.assertEqual(report['relational_targets']['binding'],'versioned_derived_not_app_bound')
        self.assertGreater(report['relational_targets']['relations']['resolved'],0,(report['relational_targets'],[(p.name,p.stat().st_size) for p in state.rglob('*-wal')]))
        self.assertEqual(self.case.head(),code_head)
        self.assertFalse(spool.exists())
        branch='refs/heads/'+RECEIPT_BRANCH
        self.assertEqual((self.git(self.case.remote,'show',branch+':'+legacy.m.receipt_relpath(old_receipt))+'\n').encode(),old_raw)
        paths=self.git(self.case.remote,'ls-tree','-r','--name-only',branch).splitlines()
        public=[]
        for path in paths:
            raw=self.git(self.case.remote,'show',branch+':'+path);value=json.loads(raw);public.append(value)
            self.assertNotIn('Generated product',raw);self.assertNotIn(str(self.cache.root),raw)
            if value['schema']=='offmenu-run-receipt/2' and 'evidence_ref' in value['ingest']:
                ref=value['ingest']['evidence_ref'];extra_path=legacy.m.supplement_relpath(ref)
                self.assertIn(extra_path,paths)
                extra=self.git(self.case.remote,'show',branch+':'+extra_path).encode()+b'\n'
                self.assertEqual(hashlib.sha256(extra).hexdigest(),ref['sha256'])
                self.assertEqual(len(extra),ref['bytes'])
        self.assertIn('offmenu-ingest-supplement/1',{v['schema'] for v in public})
        # A code-only correction can create a new job receipt but never reread
        # any successful acquired source or rewrite any source provenance row.
        for name in ('ingest_acquired_recipes.py','ingest_acquired_menus.py'):
            path=self.root/'manual-action'/name;text=path.read_text()
            marker=next(line for line in text.splitlines() if line.startswith('def iter_records('))
            path.write_text(text.replace(marker,marker+"\n    raise AssertionError('completed_acquired_reader_reentered')",1))
        self.git(self.root,'add','manual-action');self.git(self.root,'commit','-m','Generated completed-reader guards')
        self.git(self.root,'push','origin',legacy.m.BRANCH)
        self.run_command()
        repeat=json.loads((state/'last-report.json').read_text())
        self.assertTrue(all(r['written']==0 and r['read']==0 for r in repeat['domains'].values()))
        self.assertEqual(final_rows,self.db_rows(state))
        second_derived=json.loads((state/'relational-targets.private.json').read_text())
        self.assertEqual(repeat['relational_targets']['status'],'reused',{key:(first_derived.get(key),second_derived.get(key)) for key in ('code_sha256','input_identities','selected_sources','snapshot') if first_derived.get(key)!=second_derived.get(key)})
        self.assertTrue(all(s['metadata']['acquisition']['verification_basis']=='cached_byte_hash_and_current_metadata' for s in json.loads((state/'catalog.private.json').read_text())['sources'] if s.get('acquired_adapter')))

if __name__=='__main__':unittest.main()
