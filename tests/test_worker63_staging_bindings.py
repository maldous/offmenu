"""Authored small metadata fixtures only; no real dataset or native parser launch."""
import copy
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh.acceptance import (Asset, SourceContract, canonical as packet_json,
                                       fingerprint, ids_digest, qualify)
from offmenu.refresh.core import canonical
from offmenu.refresh.field_provenance import field_origin_errors

PATH = Path(__file__).resolve().parents[1] / 'scripts/worker63_staging_bindings.py'
spec = importlib.util.spec_from_file_location('worker63_bindings', PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
NOW = '2026-10-18T00:00:00Z'


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.meta = self.root/'receipt.json'
        self.meta.write_bytes(canonical({'source': {'zero': 0, 'unknown': None, 'lexical': '0'}}))
        self.binding = {'country': 'GW', 'sourceKey': 'synthetic-only',
                        'declaredIdentity': {'source': 'synthetic', 'release': 'fixture-1'},
                        'countryTypeApplicability': [{'type': 'nutrition', 'applicability': 'unreviewed'}],
                        'fieldOriginDeclarations': {'nativeUnit': None, 'basis': None},
                        'metadataAssets': [{'id': 'meta', 'path': str(self.meta),
                          'sha256': hashlib.sha256(self.meta.read_bytes()).hexdigest(),
                          'selectors': ['/source/zero', '/source/unknown', '/source/lexical']}],
                        'originalReferencesOnly': [{'sourceReference': '/must-not-open/original.pdf',
                          'recordedSHA256': 'a'*64, 'acquiredAt': '2026-10-01T00:00:00Z'}],
                        'unknowns': ['basis'], 'holds': ['no-new-data-operation']}

    def run_binding(self, **kwargs):
        return m.evaluate(self.binding, now=NOW, **kwargs)

    def test_valid_metadata_preserves_zero_null_literal_and_no_admission(self):
        result = self.run_binding()
        self.assertEqual(result['metadataStatus'], ['valid'])
        self.assertEqual([x['value'] for x in result['binding']['observations']], [0, None, '0'])
        self.assertFalse(result['binding']['sourceAcceptance'])
        self.assertFalse(result['binding']['newSourceProcessing'])
        self.assertEqual(result['dataStageStatus'], 'held')
        for row in result['binding']['metadataReferenceRecords']:
            self.assertEqual(field_origin_errors(row, {'metadata/meta.json': self.binding['metadataAssets'][0]['sha256']}), [])

    def test_missing_metadata_is_typed(self):
        self.meta.unlink()
        result = self.run_binding()
        self.assertEqual(result['metadataStatus'], ['missing-input'])
        self.assertIn('metadata-missing', [x['code'] for x in result['diagnostics']])

    def test_stale_hash_is_not_relabelled_as_current(self):
        self.meta.write_bytes(b'{"new":true}')
        result = self.run_binding()
        self.assertEqual(result['metadataStatus'], ['stale-input'])
        self.assertFalse(result['bindingContentNoOp'])
        self.assertEqual(result['binding']['observations'], [])

    def test_malformed_duplicate_json_key_is_typed(self):
        self.meta.write_bytes(b'{"source":0,"source":1}')
        self.binding['metadataAssets'][0]['sha256'] = hashlib.sha256(self.meta.read_bytes()).hexdigest()
        self.assertEqual(self.run_binding()['metadataStatus'], ['malformed-input'])

    def test_missing_selector_does_not_fill_unknown(self):
        self.binding['metadataAssets'][0]['selectors'] = ['/not-present']
        r = self.run_binding()
        self.assertEqual(r['metadataStatus'], ['malformed-input'])
        self.assertEqual(r['binding']['observations'], [])

    def test_body_reference_is_never_resolved_and_network_never_called(self):
        with patch.object(socket, 'socket', side_effect=AssertionError('network not permitted')):
            r = self.run_binding()
        self.assertEqual(r['networkRequests'], 0)
        self.assertEqual(r['cacheMetadata'][0]['decision'], 'under-minimum-window-zero-download')
        self.assertFalse(r['cacheMetadata'][0]['bodyVerifiedThisRun'])

    def test_validation_does_not_reset_original_acquisition_age(self):
        self.binding['originalReferencesOnly'][0]['acquiredAt'] = '2026-08-01T00:00:00Z'
        r = self.run_binding()
        self.assertEqual(r['cacheMetadata'][0]['decision'], 'conditional-refresh-eligibility-only')
        self.assertEqual(r['validationCheckedAt'], NOW)
        self.assertEqual(r['cacheMetadata'][0]['originalAcquiredAt'], '2026-08-01T00:00:00Z')
        self.assertEqual(r['networkRequests'], 0)

    def test_thirty_day_boundary_and_unknown_age(self):
        self.binding['originalReferencesOnly'][0]['acquiredAt'] = '2026-09-18T00:00:00Z'
        self.assertEqual(self.run_binding()['cacheMetadata'][0]['decision'], 'conditional-refresh-eligibility-only')
        self.binding['originalReferencesOnly'][0]['acquiredAt'] = None
        self.assertEqual(self.run_binding()['cacheMetadata'][0]['decision'], 'original-acquisition-time-unknown')

    def test_future_acquisition_is_rejected(self):
        self.binding['originalReferencesOnly'][0]['acquiredAt'] = '2026-11-01T00:00:00Z'
        with self.assertRaises(ValueError):
            self.run_binding()

    def test_content_replay_noop_but_holds_still_apply(self):
        first = self.run_binding()
        again = self.run_binding(previous_digest=first['bindingContentSHA256'])
        self.assertTrue(again['bindingContentNoOp'])
        self.assertEqual(again['dataStageStatus'], 'held')
        self.assertEqual(first['bindingContentSHA256'], again['bindingContentSHA256'])
        out = self.root/'report.json'
        self.assertEqual(m.write_if_changed(out, again), 'metadata-report-written')
        before = out.stat().st_mtime_ns
        self.assertEqual(m.write_if_changed(out, again), 'unchanged-no-op')
        self.assertEqual(out.stat().st_mtime_ns, before)

    def test_removing_config_holds_cannot_install_admission(self):
        self.binding['holds'] = []
        r = self.run_binding()
        self.assertEqual(r['dataStageStatus'], 'held')
        self.assertIn('data-stage-not-authorized-by-metadata-binding', [x['code'] for x in r['diagnostics']])

    def test_symlink_rejected_before_content(self):
        link = self.root/'alias.json'
        link.symlink_to(self.meta)
        self.binding['metadataAssets'][0]['path'] = str(link)
        self.assertEqual(self.run_binding()['metadataStatus'], ['malformed-input'])

    def test_portfolio_errors_are_isolated(self):
        entries = []
        for country in m.COUNTRIES:
            row = copy.deepcopy(self.binding); row['country'] = country; entries.append(row)
        entries[0]['metadataAssets'][0]['path'] = str(self.root/'absent.json')
        r = m.evaluate_portfolio({'schemaVersion': 'offmenu-portfolio63-bindings/1', 'bindings': entries}, now=NOW)
        self.assertEqual(len(r['results']), 4)
        self.assertEqual(r['results'][0]['metadataStatus'], ['missing-input'])
        self.assertTrue(all(x['metadataStatus'] == ['valid'] for x in r['results'][1:]))
        self.assertEqual(r['wholeCountriesComplete'], 0)


    def test_shared_field_origins_detect_corruption_and_missing_datum(self):
        r=self.run_binding();row=copy.deepcopy(r['binding']['metadataReferenceRecords'][0])
        origins=row['provenance']['fieldOrigins'];key=next(iter(origins))
        origins[key]['inputSha256']='f'*64
        self.assertIn('field-origin-input-pin-mismatch',field_origin_errors(row,{'metadata/meta.json':self.binding['metadataAssets'][0]['sha256']}))
        origins.clear()
        self.assertIn('field-origin-inventory-mismatch',field_origin_errors(row,{'metadata/meta.json':self.binding['metadataAssets'][0]['sha256']}))

    def test_overflow_json_is_malformed_not_a_numeric_fact(self):
        self.meta.write_bytes(b'{"source":{"zero":1e999,"unknown":null,"lexical":"0"}}')
        self.binding['metadataAssets'][0]['sha256']=hashlib.sha256(self.meta.read_bytes()).hexdigest()
        r=self.run_binding()
        self.assertEqual(r['metadataStatus'],['malformed-input'])
        self.assertEqual(r['binding']['observations'],[])

    def test_different_output_generation_is_preserved(self):
        out=self.root/'report.json';m.write_if_changed(out,{'old':True})
        before=out.read_bytes()
        with self.assertRaisesRegex(ValueError,'binding-output-generation-conflict'):
            m.write_if_changed(out,{'new':True})
        self.assertEqual(before,out.read_bytes())

    def test_malformed_previous_report_is_not_silently_reused(self):
        entries=[]
        for code in m.COUNTRIES:
            x=copy.deepcopy(self.binding);x['country']=code;entries.append(x)
        with self.assertRaisesRegex(ValueError,'invalid-previous-binding-report'):
            m.evaluate_portfolio({'schemaVersion':'offmenu-portfolio63-bindings/1','bindings':entries},now=NOW,previous=['invalid'])


    def test_metadata_bundle_origin_paths_exist_and_replay_without_writes(self):
        result=self.run_binding();out=self.root/'staging'
        self.assertEqual(m.stage_metadata(self.binding,result,out)['status'],'metadata-declarations-staged')
        self.assertEqual((out/'metadata/meta.json').read_bytes(),self.meta.read_bytes())
        rows=[json.loads(line)[0] for line in (out/'metadata-candidate.jsonl').read_bytes().splitlines()]
        for row in rows:
            self.assertEqual(field_origin_errors(row,{'metadata/meta.json':self.binding['metadataAssets'][0]['sha256']}),[])
            self.assertIsNone(row['provenance']['fetchedAt'])
        before={str(p):p.stat().st_mtime_ns for p in out.rglob('*') if p.is_file()}
        self.assertEqual(m.stage_metadata(self.binding,result,out)['status'],'unchanged-no-op')
        self.assertEqual(before,{str(p):p.stat().st_mtime_ns for p in out.rglob('*') if p.is_file()})
        self.assertFalse(json.loads((out/'manifest.json').read_text())['sourceAcceptance'])

    def test_metadata_bundle_corruption_does_not_overwrite_prior_bytes(self):
        result=self.run_binding();out=self.root/'staging';m.stage_metadata(self.binding,result,out)
        damaged=out/'metadata/meta.json';damaged.write_bytes(b'preserve this conflict')
        with self.assertRaisesRegex(ValueError,'metadata-stage-generation-conflict'):
            m.stage_metadata(self.binding,result,out)
        self.assertEqual(damaged.read_bytes(),b'preserve this conflict')

    def test_metadata_bundle_rechecks_stale_input_and_refuses_missing(self):
        result=self.run_binding();self.meta.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'metadata-stage-input-stale'):
            m.stage_metadata(self.binding,result,self.root/'staging')
        self.assertFalse((self.root/'staging').exists())
        self.meta.unlink()
        with self.assertRaisesRegex(ValueError,'metadata-stage-input-not-valid'):
            m.stage_metadata(self.binding,self.run_binding(),self.root/'staging')

    def fixture_contract(self):
        """Fixed authored scope only, never creates a real admission from config."""
        bundle = self.root/'bundle'; bundle.mkdir()
        assets = []
        for name, body in [('metadata.json', canonical(self.run_binding()['binding'])),
                           ('rights.txt', b'Synthetic fixture retain parse transform only'),
                           ('scope.txt', b'One authored metadata record; no country acceptance')]:
            (bundle/name).write_bytes(body)
            assets.append(Asset(name, len(body), hashlib.sha256(body).hexdigest()))
        row = {'id': 'fixture63:a', 'kind': 'referenceMetadata', 'schemaVersion': '1.0',
               'data': {'zero': 0, 'unknown': None, 'nativeUnit': None, 'basis': None},
               'provenance': {'sourceId': 'worker63-synthetic-metadata', 'releaseId': 'fixture-1',
                              'fetchedAt': '2026-10-01T00:00:00Z'}}
        schemas = {'referenceMetadata': {'type': 'object',
                    'required': ['id', 'kind', 'schemaVersion', 'data', 'provenance'],
                    'properties': {'kind': {'const': 'referenceMetadata'},
                     'schemaVersion': {'const': '1.0'}, 'data': {'type': 'object',
                       'required': ['zero', 'unknown', 'nativeUnit', 'basis'],
                       'properties': {'zero': {'const': 0}, 'unknown': {'type': 'null'},
                                      'nativeUnit': {'type': 'null'}, 'basis': {'type': 'null'}},
                       'additionalProperties': False}}}}
        contract = SourceContract('worker63-synthetic-metadata', 'fixture-1', 'authored-binding-only',
             '2026-10-01T00:00:00Z', tuple(assets), 1, ids_digest(['fixture63:a']), schemas,
             fingerprint(schemas), lambda row: [] if row['data']['basis'] is None else ['basis-invented'],
             '1'*64, assets[1], assets[2], frozenset(('retain', 'parse', 'transform')), fixture=True)
        body = packet_json([row])+b'\n'; candidate=self.root/'candidate.jsonl'; candidate.write_bytes(body)
        manifest={'sourceId':contract.source_id,'releaseId':contract.release_id,'acquiredAt':contract.acquired_at,
                  'normalizedRecords':1,'candidateSha256':hashlib.sha256(body).hexdigest(),'candidateBytes':len(body),
                  'rightsEvidenceSha256':assets[1].sha256,'scopeEvidenceSha256':assets[2].sha256,
                  'inputFiles':[vars(a) for a in assets]}
        return contract,bundle,candidate,manifest

    def test_shared_qualification_accepts_only_authored_fixture_scope(self):
        c,b,p,mf=self.fixture_contract();r=qualify(c,b,p,mf)
        self.assertTrue(r['qualified'], r['errors'])
        self.assertTrue(r['fixture'])
        self.assertNotIn('accepted', r)
        self.assertEqual(r, qualify(c,b,p,mf))

    def test_shared_qualification_rejects_held_and_unpermitted_scope(self):
        c,b,p,mf=self.fixture_contract()
        r=qualify(replace(c, holds=('actual-source-hold',), permitted_operations=frozenset(('retain',))),b,p,mf)
        self.assertFalse(r['qualified'])
        self.assertIn('source-held',r['errors']);self.assertIn('operation-rights-missing',r['errors'])

    def test_shared_qualification_rejects_missing_and_stale_asset(self):
        c,b,p,mf=self.fixture_contract();(b/'metadata.json').write_bytes(b'changed')
        r=qualify(c,b,p,mf);self.assertFalse(r['qualified']);self.assertIn('input-custody-mismatch',r['errors'])
        (b/'metadata.json').unlink();self.assertFalse(qualify(c,b,p,mf)['qualified'])

    def test_shared_qualification_rejects_malformed_and_invented_basis(self):
        c,b,p,mf=self.fixture_contract();p.write_bytes(b'not-json\n')
        self.assertIn('record-invalid',qualify(c,b,p,mf)['errors'])
        row={'id':'fixture63:a','kind':'referenceMetadata','schemaVersion':'1.0',
             'data':{'zero':0,'unknown':None,'nativeUnit':None,'basis':'invented'},
             'provenance':{'sourceId':c.source_id,'releaseId':c.release_id,'fetchedAt':c.acquired_at}}
        body=packet_json([row])+b'\n';p.write_bytes(body)
        mf.update(candidateSha256=hashlib.sha256(body).hexdigest(),candidateBytes=len(body))
        self.assertIn('basis-invented',qualify(c,b,p,mf)['errors'])
