import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'candidate/scripts'),str(ROOT/'candidate/tests')]
import exercise_source_scoped_consumer as P
import test_source_scoped_consumer as F
from derive_north_star_bulk import sha_file


class CallerProbeTests(unittest.TestCase):
    def setUp(self):
        self.fixture=F.SourceConsumerTests('test_actual_value_context_and_restored_basis');self.fixture.setUp()
    def tearDown(self):self.fixture.tearDown()
    def run_probe(self,**kw):
        f=self.fixture
        return P.exercise(f.source,f.bulk,f.basis,sha_file(f.bulk/'manifest.json'),sha_file(f.basis/'manifest.json'),**kw)
    def test_real_fixture_pipeline_produces_only_aggregate_caller_receipt(self):
        r=self.run_probe(max_keys=4);c=r['counts']
        self.assertEqual(c['sourceKeyQueries'],1);self.assertEqual(c['nutrientContextOccurrences'],2)
        self.assertEqual(c['zeroQuantityOccurrences'],1);self.assertEqual(c['unknownQuantityOccurrences'],0)
        self.assertEqual(c['restoredBasisTargetOccurrences'],2);self.assertEqual(c['citationOccurrences'],2)
        serialized=json.dumps(r)
        for private in ('001234','Synthetic product','source-product','Synthetic licence','as-sold'):
            self.assertNotIn(private,serialized)
        self.assertEqual(r['acceptedIdentityJoins'],0);self.assertEqual(r['servedApplicationQueries'],0)
    def test_limits_are_strict_and_bounded(self):
        for value in (0,129,True,'1'):
            with self.assertRaises(ValueError):self.run_probe(max_keys=value)
        for value in (0,1201,True,'600'):
            with self.assertRaises(ValueError):self.run_probe(seconds=value)
    def test_caller_failure_does_not_mint_success(self):
        with patch.object(P.SourceScopedConsumer,'lookup',return_value={'status':'unexpected'}):
            with self.assertRaisesRegex(ValueError,'opt-in'):self.run_probe()
    def test_read_only_indices_unchanged(self):
        f=self.fixture;paths=[f.bulk/'consumer-index.sqlite',f.basis/'matched-proof.sqlite'];before=[sha_file(p) for p in paths]
        self.run_probe();self.assertEqual(before,[sha_file(p) for p in paths])
    def test_active_writer_refused(self):
        import fcntl
        with (self.fixture.basis/'.writer.lock').open('rb') as lock:
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):self.run_probe()
    def test_durable_report_never_replaces_existing_final(self):
        path=self.fixture.root/'receipt.json';result=self.run_probe();P.publish_report(path,result);before=path.read_bytes()
        with self.assertRaises(FileExistsError):P.publish_report(path,{'foreign':'replacement'})
        self.assertEqual(path.read_bytes(),before);self.assertEqual(list(path.parent.glob('receipt.json.tmp-*')),[])


if __name__=='__main__':unittest.main()
