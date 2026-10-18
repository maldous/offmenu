"""Small authored metadata fixtures; never read retained country/source bodies."""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio22 as p
from offmenu.refresh import acceptance as q
from offmenu.refresh.core import canonical, sha, timestamp
from offmenu.refresh.serialization import encode_records
from offmenu.refresh.field_provenance import field_origin_errors


NOW = '2026-10-18T12:00:00Z'


def evidence():
    e = p.expected_evidence('CF')
    e['lastValidatedAt'] = '2026-10-17T12:00:00Z'
    return e


class Portfolio22BindingTests(unittest.TestCase):
    def test_valid_metadata_retains_literal_origins_and_unknowns(self):
        e = evidence(); before = deepcopy(e)
        r = p.assess('CF', e, now=NOW)
        self.assertEqual(r['state'], 'ready')
        self.assertEqual(r['stage']['status'], 'succeeded')
        self.assertEqual(r['record']['data']['nativeCurrency'], 'XAF')
        self.assertEqual(r['record']['data']['nonfoodExcluded'], 147)
        for key in ['metricBasisId','analyticalMethodId','preparationState','canonicalCurrencyId']:
            self.assertIsNone(r['record']['data'][key])
        self.assertEqual(r['record']['data']['fieldOrigins'], e['fieldOrigins'])
        self.assertFalse(r['sourceProcessingAllowed'])
        self.assertFalse(r['sourceBytesVerified'])
        self.assertFalse(r['datasetAccepted'])
        self.assertEqual(e, before)

    def test_missing_inputs_and_other_portfolio_gaps(self):
        for country in ['BY','CC','CD']:
            r = p.assess(country, p.expected_evidence(country), now=NOW)
            self.assertEqual(r['state'], 'missing')
            self.assertTrue(r['remainingBlockers'])
            self.assertIsNone(r['record'])
        for key in ['assets','fieldOrigins','lastValidatedAt']:
            e = evidence(); e[key] = [] if key=='assets' else None
            self.assertEqual(p.assess('CF',e,now=NOW)['state'], 'missing')

    def test_explicit_hold_is_never_waived_by_freshness(self):
        e = evidence(); e['held'] = True
        r = p.assess('CF',e,now=NOW)
        self.assertEqual(r['state'], 'held')
        self.assertEqual(r['stage']['code'], 'metadata-source-held')
        self.assertFalse(r['sourceProcessingAllowed'])

    def test_shared_field_origin_coverage_includes_nulls_and_catches_omission(self):
        row=p.assess('CF',evidence(),now=NOW)['record']
        pins={'portfolio22.json':sha(p.CONFIG.read_bytes())}
        self.assertEqual(field_origin_errors(row,pins),[])
        self.assertIn('/data/metricBasisId',row['provenance']['fieldOrigins'])
        self.assertEqual(row['provenance']['fieldOriginScope'],'binding-config-metadata-only')
        del row['provenance']['fieldOrigins']['/data/metricBasisId']
        self.assertIn('field-origin-inventory-mismatch',field_origin_errors(row,pins))

    def test_malformed_metadata_pins_selectors_releases_and_timestamps(self):
        variants = []
        for key,val in [('sourceId','other'),('releaseId','other'),('held','false'),('originalAcquiredAt',NOW),('lastValidatedAt','invalid')]:
            e=evidence(); e[key]=val; variants.append(e)
        e=evidence(); e['assets'][0]['sha256']='a'*64; variants.append(e)
        e=evidence(); e['fieldOrigins'][0]['sourceSelector']='csv-column:wrong'; variants.append(e)
        e=evidence(); e['extra']=1; variants.append(e)
        e=evidence(); e['assets']={}; variants.append(e)
        e=evidence(); e['lastValidatedAt']='2026-11-01T00:00:00Z'; variants.append(e)
        for e in variants:
            self.assertEqual(p.assess('CF',e,now=NOW)['state'],'malformed')
        self.assertEqual(p.assess('NO',evidence(),now=NOW)['state'],'malformed')
        self.assertEqual(p.assess('CF',evidence(),now=NOW,previous_key='wrong')['state'],'malformed')

    def test_thirty_day_boundary_and_validation_age_cannot_refresh_original(self):
        e=evidence(); acquired=timestamp(e['originalAcquiredAt'])
        before=(acquired+timedelta(days=30,seconds=-1)).isoformat()
        after=(acquired+timedelta(days=30)).isoformat()
        self.assertEqual(p.assess('CF',e,now=before)['state'],'ready')
        e['lastValidatedAt']=after
        r=p.assess('CF',e,now=after)
        self.assertEqual(r['state'],'stale')
        self.assertEqual(r['cache']['originalAcquisitionAgeDays'],30)
        self.assertEqual(r['cache']['validationAgeDays'],0)
        self.assertFalse(r['cache']['validationResetsAcquisitionAge'])
        self.assertFalse(r['cache']['automaticDownloadAllowed'])

    def test_replay_noop_key_ignores_validation_clock_but_preserves_source_identity(self):
        e=evidence(); a=p.assess('CF',e,now=NOW)
        e['lastValidatedAt']=NOW
        b=p.assess('CF',e,now=NOW,previous_key=a['bindingKey'])
        self.assertEqual(b['state'],'no-op')
        self.assertEqual(p.candidate_bytes(a),p.candidate_bytes(b))
        self.assertEqual(p.candidate_bytes(a),encode_records([a['record']]))
        self.assertEqual(json.loads(p.candidate_bytes(a)),[a['record']])

    def test_metadata_planning_does_not_read_assets_or_enable_network(self):
        with patch('socket.create_connection',side_effect=AssertionError('network forbidden')):
            r=p.assess('CF',evidence(),now=NOW)
        self.assertEqual(r['networkRequests'],0)
        self.assertFalse(r['sourceBytesVerified'])
        from offmenu.refresh.execution import ADMISSIONS
        self.assertNotIn(r['record']['provenance']['sourceId'],ADMISSIONS)
        with self.assertRaises(ValueError):
            p.candidate_bytes(p.assess('CF',{**evidence(),'held':True},now=NOW))

    def test_cli_strict_json_and_typed_exit_without_raw_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            f=Path(directory)/'evidence.json'; f.write_text('{"held":false,"held":true}')
            r=subprocess.run([sys.executable,'-m','offmenu.refresh.portfolio22','CF',str(f),'--now',NOW],capture_output=True,text=True)
            self.assertEqual(r.returncode,2)
            self.assertEqual(json.loads(r.stdout)['state'],'malformed')
            f.write_bytes(canonical(evidence()))
            r=subprocess.run([sys.executable,'-m','offmenu.refresh.portfolio22','CF',str(f),'--now',NOW],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(json.loads(r.stdout)['state'],'ready')

    def test_shared_qualifier_accepts_only_authored_metadata_fixture_scope(self):
        # Exercise the actual shared validator/framing, not a copied country validator.
        # Its fixture flag never supplies a production contract or enables ADMISSIONS.
        row={'id':'portfolio22-authored-fixture:source-input-binding:one',
             'schemaVersion':'1.0','kind':'source-input-binding',
             'provenance':{'sourceId':'portfolio22-authored-fixture',
                           'releaseId':'authored-v1','fetchedAt':'2026-10-17T00:00:00Z'},
             'data':{'metricBasisId':None,'nativeUnit':'authored-unit'}}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); bundle=root/'bundle'; bundle.mkdir()
            assets=[]
            for name,body in [('fixture.json',b'{"authoredMetadataOnly":true}'),('rights.json',b'{"fixtureOnly":true}'),('scope.json',canonical({'ids':[row['id']]}))]:
                (bundle/name).write_bytes(body); assets.append(q.Asset(name,len(body),sha(body)))
            raw=encode_records([row])
            candidate=root/'candidate.jsonl'; candidate.write_bytes(raw)
            schema={'type':'object','required':['id','kind','schemaVersion','provenance','data'],
                    'properties':{'id':{'const':row['id']},'kind':{'const':'source-input-binding'},
                                  'schemaVersion':{'const':'1.0'},'provenance':{'const':row['provenance']},
                                  'data':{'const':row['data']}},'additionalProperties':False}
            schemas={'source-input-binding':schema}
            contract=q.SourceContract(source_id=row['provenance']['sourceId'],release_id=row['provenance']['releaseId'],
                scope_id='authored-portfolio22-metadata-fixture-only',acquired_at=row['provenance']['fetchedAt'],
                inputs=tuple(assets),expected_records=1,expected_ids_sha256=q.ids_digest([row['id']]),
                schemas=schemas,schemas_sha256=q.fingerprint(schemas),semantic_validator=lambda x:(),
                policy_sha256=sha(b'authored-portfolio22-fixture-v1'),rights_evidence=assets[1],scope_evidence=assets[2],
                permitted_operations=frozenset(('retain','parse','transform')),fixture=True)
            manifest={'sourceId':contract.source_id,'releaseId':contract.release_id,'acquiredAt':contract.acquired_at,
                      'normalizedRecords':1,'candidateSha256':sha(raw),'candidateBytes':len(raw),
                      'inputFiles':[vars(x) for x in assets], 'rightsEvidenceSha256':assets[1].sha256,
                      'scopeEvidenceSha256':assets[2].sha256}
            r=q.accept(contract,bundle,candidate,manifest)
            self.assertTrue(r['accepted'],r['errors'])
            self.assertFalse(r['productionAccepted'])
            self.assertFalse(r['countryCoverageComplete'])
            r=q.qualify(replace(contract,holds=('authored-hold',)),bundle,candidate,manifest)
            self.assertIn('source-held',r['errors'])
            r=q.qualify(replace(contract,permitted_operations=frozenset(('retain',))),bundle,candidate,manifest)
            self.assertIn('operation-rights-missing',r['errors'])
            damaged=deepcopy(row); damaged['data']['metricBasisId']='invented'
            candidate.write_bytes(encode_records([damaged]))
            r=q.qualify(contract,bundle,candidate,manifest)
            self.assertFalse(r['qualified'])


if __name__=='__main__':
    unittest.main()
