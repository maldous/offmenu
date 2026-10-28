import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'candidate/scripts'),str(ROOT/'candidate/tests')]
from test_basis_restoration import inputs,producer
from test_basis_runner import prepare
import run_north_star_basis_restoration as R
import derive_north_star_bulk as B
from source_scoped_north_star_consumer import SourceScopedConsumer


def product_fixture():
    profile,entry,packet=inputs();product=copy.deepcopy(profile);product['id']='synthetic:product:1';product['kind']='product';product['provenance']['recordId']='source-product'
    product['data']={'name':'Synthetic product','identifiers':[{'system':'gtin','value':'001234'}],'nutritionId':profile['id']}
    return [product,profile],entry,[producer.packet(product,'off',entry),packet]


class SourceConsumerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);records,_,packets=product_fixture()
        self.native,self.source,self.basis,self.kw=prepare(self.tmp.name,records=records,packets=packets)
        manifest=json.loads((self.source/'manifest.json').read_bytes())
        for field in ['assertions','relations','translations']:manifest['counts'][field]=sum(len(p[field]) for p in packets)
        (self.source/'manifest.json').write_bytes(R.encoded(manifest));self.kw['bulk_sha']=R.sha_file(self.source/'manifest.json')
        self.bulk=self.root/'bulk-derived';B.run(self.source,self.bulk,self.kw['bulk_sha'],workers=1,seconds=60,reserve=0,schema_sha=self.kw['schema_sha'],contract_sha=self.kw['contract_sha'])
        R.run('index',self.native,self.source,self.basis,**self.kw);R.run('restore',self.native,self.source,self.basis,**self.kw)
        self.reader=SourceScopedConsumer(self.source,self.bulk,self.basis,R.sha_file(self.bulk/'manifest.json'),R.sha_file(self.basis/'manifest.json'))
    def tearDown(self):self.reader.close();self.tmp.cleanup()
    def query(self,**kw):return self.reader.lookup('off','synthetic-release','gtin','001234',**kw)
    def test_candidates_require_explicit_request(self):
        self.assertEqual(self.query()['status'],'candidates-not-requested')
        for value in (False,None,1,'false','true',[]):
            self.assertEqual(self.query(include_candidates=value)['status'],'candidates-not-requested')
    def test_actual_value_context_and_restored_basis(self):
        out=self.query(include_candidates=True);self.assertEqual(out['status'],'source-scoped-candidate-context')
        p=out['products'][0];self.assertEqual(p['identifierEvidence'][0]['value']['fields']['value']['value'],'001234')
        profile=p['profiles'][0];self.assertEqual(profile['resource']['type'],'urn:offmenu:type:FoodCompositionObservation')
        for item in (p,profile):
            self.assertEqual([c['id'] for c in item['citations']],item['resource']['citationIds'])
            self.assertEqual(item['citations'][0]['sourceId'],'off')
            self.assertEqual(item['citations'][0]['license'],'Synthetic licence')
            self.assertEqual(item['citations'][0]['attribution'],'Synthetic only')
        self.assertEqual(profile['perNutrientBasisCandidates']['basisGroups'][0]['sourceBasis']['state'],'as-sold')
        self.assertEqual(len(profile['nutrientContextCandidates']['assertions']),2)
        self.assertFalse(out['nutritionAggregationEligible']);self.assertEqual(out['acceptedIdentityJoins'],0)
    def test_unknown_source_key_has_no_external_fallback(self):
        out=self.reader.lookup('other-source','synthetic-release','gtin','001234',include_candidates=True)
        self.assertEqual(out['status'],'source-key-not-found')
    def test_leading_zero_and_namespace_are_not_canonicalized(self):
        for namespace,value in [('gtin','1234'),('ean','001234')]:
            self.assertEqual(self.reader.lookup('off','synthetic-release',namespace,value,include_candidates=True)['status'],'source-key-not-found')
    def test_source_release_is_exact(self):
        self.assertEqual(self.reader.lookup('off','other-release','gtin','001234',include_candidates=True)['status'],'source-key-not-found')
    def test_ambiguous_exact_source_key_not_arbitrarily_resolved(self):
        records,entry,packets=product_fixture();other=copy.deepcopy(records[0]);other['id']='synthetic:product:2';other['provenance']['recordId']='another-product'
        records.append(other);packets.append(producer.packet(other,'off',entry))
        with tempfile.TemporaryDirectory() as t:
            native,source,basis,kw=prepare(t,records=records,packets=packets);manifest=json.loads((source/'manifest.json').read_bytes())
            for field in ['assertions','relations','translations']:manifest['counts'][field]=sum(len(p[field]) for p in packets)
            (source/'manifest.json').write_bytes(R.encoded(manifest));kw['bulk_sha']=R.sha_file(source/'manifest.json');bulk=Path(t)/'bulk-derived'
            B.run(source,bulk,kw['bulk_sha'],workers=1,seconds=60,reserve=0,schema_sha=kw['schema_sha'],contract_sha=kw['contract_sha']);R.run('index',native,source,basis,**kw);R.run('restore',native,source,basis,**kw)
            reader=SourceScopedConsumer(source,bulk,basis,R.sha_file(bulk/'manifest.json'),R.sha_file(basis/'manifest.json'))
            try:
                result=reader.lookup('off','synthetic-release','gtin','001234',include_candidates=True)
                self.assertEqual(result['status'],'ambiguous-source-product-key');self.assertEqual(result['candidateProductCount'],2);self.assertEqual(result['products'],[])
            finally:reader.close()
    def test_original_packet_tamper_refused(self):
        (self.source/'part.jsonl.gz').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'InputAssetDigestMismatch'):self.query(include_candidates=True)
    def test_merged_source_citation_packet_refused(self):
        from unittest.mock import patch
        import gzip
        packet=json.loads(gzip.decompress((self.source/'part.jsonl.gz').read_bytes()).splitlines()[0])
        other=copy.deepcopy(packet['citations'][0]);other['id']='urn:test:other';other['sourceId']='another-source';packet['citations'].append(other)
        with patch('source_scoped_north_star_consumer.checked_asset',return_value=gzip.compress((json.dumps(packet)+'\n').encode())):
            with self.assertRaisesRegex(ValueError,'single-citation bulk packet'):self.query(include_candidates=True)
    def test_row_citation_references_must_equal_selected_source(self):
        from unittest.mock import patch
        import gzip
        packet=json.loads(gzip.decompress((self.source/'part.jsonl.gz').read_bytes()).splitlines()[0]);packet['assertions'][0]['citationIds']=[]
        with patch('source_scoped_north_star_consumer.checked_asset',return_value=gzip.compress((json.dumps(packet)+'\n').encode())):
            with self.assertRaisesRegex(ValueError,'single-citation bulk references'):self.query(include_candidates=True)
    def test_pinned_indices_not_modified(self):
        paths=[self.bulk/'consumer-index.sqlite',self.basis/'matched-proof.sqlite'];before=[R.sha_file(p) for p in paths]
        self.query(include_candidates=True);self.assertEqual(before,[R.sha_file(p) for p in paths])


if __name__=='__main__':unittest.main()
