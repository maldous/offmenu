"""Prospective retirement on real entrypoints. All transports stubbed; no publisher data."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from dataclasses import replace
import base64
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from offmenu.refresh.acquisition import CachedAcquirer, HTTPSFileTransport, POLICIES
from offmenu.refresh.core import RefreshError
from offmenu.refresh.coverage import assess
from offmenu.refresh.global_run import run
from offmenu.refresh.source_retirement import RETIRED, REASON, active_providers, retired
from test_refresh_acquisition import SPEC
from test_refresh_global_run import coverage, binding

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools/data-processing'
DIRECT = {'discovery:S042', 'discovery:S043', 'src-dc7480cf5666'}
MAP = 'https://www.openstreetmap.org/copyright'
def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


class Retirement(unittest.TestCase):
    def test_default_collection_filters_before_submit_and_retains_other_sources(self):
        landing = module('landing', TOOLS / 'collect_source_access.py')
        records = json.loads((ROOT/'docs/source-delivery-ledger.json').read_text())['sources']
        expected = {r['sourceId'] for r in records} - DIRECT
        self.assertEqual(len(expected), 1300)
        observed = []
        def safe_stub(source, output):
            observed.append(source['sourceId'])
            return {'sourceId': source['sourceId']}
        with tempfile.TemporaryDirectory() as d, patch.object(sys, 'argv', ['collector', d]), \
             patch.object(landing, 'collect', side_effect=safe_stub), redirect_stdout(io.StringIO()):
            landing.main()
            self.assertEqual(set(observed), expected)
            self.assertEqual(len(observed), len(expected))
            self.assertEqual(json.loads((Path(d)/'report.json').read_text())['sourceCount'], 1300)

    def test_explicit_landing_rejects_before_cache_or_transport_and_blocks_redirect(self):
        landing = module('landing', TOOLS / 'collect_source_access.py')
        with tempfile.TemporaryDirectory() as d, patch.object(landing.urllib.request,'build_opener') as network:
            for key in DIRECT | {'S042', 'S043', 'new-identity'}:
                cache = Path(d)/(hashlib.sha256(key.encode()).hexdigest()[:24]+'.json')
                cache.write_text('not JSON: must not load the previous receipt')
                with self.assertRaisesRegex(ValueError, REASON):
                    landing.collect({'sourceId':key,'url':MAP if key=='new-identity' else SPEC.url}, Path(d))
            req = landing.urllib.request.Request(SPEC.url)
            with self.assertRaisesRegex(ValueError, REASON):
                landing._ActiveLandingRedirect().redirect_request(req,None,302,'',{},MAP)
            network.assert_not_called()
        self.assertEqual(set(RETIRED), DIRECT)
        other = {'sourceId':'overture','url':'https://overture.example/openstreetmap.org',
                 'attribution':MAP,'map':MAP}
        self.assertEqual(landing.active_landing_sources([other]), [other])
        self.assertFalse(retired(other['sourceId'],'https://notopenstreetmap.org/data'))
        self.assertEqual(list(active_providers([{'name':'mixed','source_ids':['S043','S404']}])),
                         [{'name':'mixed','source_ids':['S404']}])

    def test_direct_acquisition_retained_import_and_transport_are_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)/'unopened'
            for key in DIRECT | {'S042', 'S043', 'disguised'}:
                s = replace(SPEC,source_key=key,url=MAP if key=='disguised' else SPEC.url)
                network = Mock(side_effect=AssertionError('no network'))
                acq = CachedAcquirer(root,{key:s},transport=network)
                for policy in POLICIES:
                    with self.assertRaisesRegex(RefreshError, REASON):
                        acq.acquire(key, fetch_policy=policy)
                with self.assertRaisesRegex(RefreshError, REASON):
                    acq.import_retained(key, {})
                with patch('http.client.HTTPSConnection') as connection, self.assertRaisesRegex(RefreshError, REASON):
                    HTTPSFileTransport()(s,{})
                network.assert_not_called()
                connection.assert_not_called()
                self.assertFalse(root.exists())

    def test_coverage_retains_evidence_but_does_not_schedule_with_a_binding(self):
        current = assess(ROOT/'docs/country-delivery-matrix.json', ROOT/'docs/source-delivery-ledger.json')
        self.assertEqual(len(current['sources']), 1303)
        known = {row['sourceId']: row for row in current['sources']}
        for sid in DIRECT:
            self.assertEqual(known[sid]['historicalLandingEvidence']['httpStatus'], 200)
            self.assertFalse(known[sid]['globalRoute'])
            self.assertIn(REASON, known[sid]['holds'])
        self.assertTrue(all(DIRECT.isdisjoint(c['sourceIds']+c['globalSourceIds']) for c in current['countries']))
        active = 'overture'
        all_ids = sorted(DIRECT | {active})
        stale = coverage(all_ids)
        for country in stale['countries']:
            country['globalSourceIds'] = country['sourceIds'] = all_ids
            for cell in country['domains'].values():
                cell['sourceIds'] = all_ids
        submitted = []
        class Watched(ThreadPoolExecutor):
            def submit(self, fn, row, *args):
                submitted.append(row['sourceId'])
                return super().submit(fn,row,*args)
        disallowed = Mock(side_effect=AssertionError('retired callback invoked'))
        with patch('offmenu.refresh.global_run.ThreadPoolExecutor', Watched):
            result = run(stale, bindings={k: binding(disallowed) if k in DIRECT else binding() for k in all_ids},
                         fetch_policy='force-download', force_rebuild=True)
        self.assertEqual(submitted,[active])
        self.assertTrue(result['selectedScopeComplete'])
        for row in result['sources']:
            if row['sourceId'] in DIRECT:
                self.assertTrue(all(stage['status']=='held' and stage['code']==REASON for stage in row['stages'].values()))
                self.assertFalse(row['selectedSourceComplete'])
        for country in result['countries']:
            self.assertEqual(country['globalSourceIds'],[active])
            self.assertEqual(country['sourceIds'],[active])
            self.assertTrue(all(c['sourceIds']==[active] for c in country['domains'].values()))
        disallowed.assert_not_called()

    def test_rebuilt_country_report_cannot_recommend_retired_route(self):
        tool = module('country_report', ROOT/'tools/operations/report_country_execution.py')
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()):
            root=Path(d)
            path=root/'source-access-20261013'
            path.mkdir()
            (path/'report.json').write_text(json.dumps({'sources':[
                {'sourceId':s,'httpStatus':200} for s in DIRECT]}))
            target=root/'report.json'
            tool.report(root,target)
            report=json.loads(target.read_text())
            self.assertEqual(report['sourceAccessSummary']['registeredSources'],3)
            self.assertTrue(DIRECT.isdisjoint(report['globalRouteSourceIds']))
            self.assertEqual(len(report['countries']),249)
            self.assertTrue(all(DIRECT.isdisjoint(c['applicableRegisteredSourceIds']) for c in report['countries']))

    def test_regenerating_from_pinned_historical_registers_cannot_reintroduce_direct_source(self):
        # Exercise the actual CLI generators, in a temporary output tree. Only public
        # repository-held research metadata is copied; no provider payload or connection.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            current = root/'docs/research'
            shutil.copytree(ROOT/'docs/research', current,
                            ignore=lambda _,names: [x for x in names if not x.startswith('OffMenu') and x!='manifest.json'])
            old = (current/'manifest.json').read_bytes()
            (root/'tools/data-processing').mkdir(parents=True)
            for name in ['consolidate_research.py','source_territories.py']:
                script=root/'tools/data-processing'/name
                shutil.copyfile(TOOLS/name,script)
                subprocess.run([sys.executable,'-B',script],check=True,capture_output=True,
                               env={'PYTHONPATH':str(ROOT/'src')})
            self.assertEqual((current/'manifest.json').read_bytes(), old)
            self.assertEqual((current/'active-manifest.json').read_bytes(),(ROOT/'docs/research/active-manifest.json').read_bytes())
            db=sqlite3.connect(':memory:')
            db.executescript((ROOT/'apps/web/server/catalogue-schema.sql').read_text())
            db.executescript((root/'dist/catalogue.sql').read_text())
            db.executescript((root/'dist/source-territories.sql').read_text())
            rows={k for k, in db.execute("select id from catalogue where kind='source'")}
            self.assertEqual(len(rows),1300)
            self.assertTrue(DIRECT.isdisjoint(rows))
            self.assertTrue(DIRECT.isdisjoint(k for k, in db.execute("select source_id from catalogue_source_countries")))
            specs={k:json.loads(gzip.decompress(base64.b64decode(doc[3:]))) for k,doc in
                   db.execute("select id,document from catalogue where kind='specification'")}
            self.assertNotIn('OpenStreetMap',[p['name'] for p in specs['global-providers']['providers']])
            self.assertNotIn('src-dc7480cf5666',[r['source_id'] for r in specs['enrichment-recommendations']['globalSources']])
            self.assertTrue(any('Overture' in p['name'] for p in specs['global-providers']['providers']))
            db.close()
