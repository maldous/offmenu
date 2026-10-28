import copy,gzip,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'candidate/scripts'));sys.path.insert(0,str(ROOT/'candidate/tests'))
from test_source_scoped_consumer import SourceConsumerTests
from source_scoped_north_star_consumer import SourceScopedConsumer
import source_scoped_north_star_consumer as M

class IndependentConsumerProbes(unittest.TestCase):
    def setUp(self):self.fixture=SourceConsumerTests('test_actual_value_context_and_restored_basis');self.fixture.setUp()
    def tearDown(self):self.fixture.tearDown()
    def test_exact_true_only_and_no_query_when_not_opted_in(self):
        f=self.fixture
        with patch.object(f.reader,'_packet',side_effect=AssertionError('must not fetch')):
            for value in [None,False,1,'true','false',[],{}]:self.assertEqual(f.query(include_candidates=value)['status'],'candidates-not-requested')
    def test_locator_wrong_packet_is_not_accepted(self):
        f=self.fixture;real=f.reader.locations
        class Rows:
            def fetchone(self):return ('part.jsonl.gz',1,f.reader.files['part.jsonl.gz']['sha256'])
        class WrongLocator:
            def execute(self,*args):return Rows()
        f.reader.locations=WrongLocator()
        try:
            with self.assertRaisesRegex(ValueError,'resource identity differs'):f.query(include_candidates=True)
        finally:f.reader.locations=real
    def test_derived_packet_binding_checked_beyond_file_hash(self):
        f=self.fixture;entry=next(iter(f.reader.bulk_files.values()));path=f.bulk/entry['key'];rows=[json.loads(x) for x in gzip.decompress(path.read_bytes()).splitlines()]
        for row in rows:row['inputPacketCanonicalSha256']='0'*64
        raw=gzip.compress(('\n'.join(json.dumps(x) for x in rows)+'\n').encode());path.write_bytes(raw);entry.update(bytes=len(raw),sha256=M.sha_bytes(raw))
        with self.assertRaisesRegex(ValueError,'derived packet binding differs'):f.query(include_candidates=True)
    def test_verified_citation_payload_is_exposed_without_admission(self):
        out=self.fixture.query(include_candidates=True);p=out['products'][0]
        for record in [p,*p['profiles']]:
            citation=record['citations'][0];self.assertEqual(citation['sourceId'],'off');self.assertEqual(citation['revisionId'],'synthetic-release');self.assertEqual(citation['license'],'Synthetic licence')
        self.assertFalse(out['servedApplicationActivation']);self.assertFalse(out['nutritionAggregationEligible']);self.assertEqual(out['acceptedIdentityJoins'],0)

if __name__=='__main__':unittest.main()
