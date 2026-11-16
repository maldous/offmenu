import importlib.util,sqlite3,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'candidate/scripts'),str(ROOT/'candidate/tests')]
import source_scoped_north_star_consumer as C
import test_source_scoped_consumer as F
from derive_north_star_bulk import sha_file
OLD_SQL='SELECT e.object,e.source_edge_id,e.source_edge_sha FROM edges e JOIN resolved_edges r ON r.id=e.id WHERE e.subject=?'

class SubjectJoinDeltaTests(unittest.TestCase):
    def test_many_edges_same_results_and_index_search(self):
        db=sqlite3.connect(':memory:')
        db.executescript('CREATE TABLE edges(id TEXT PRIMARY KEY,subject TEXT,object TEXT,source_edge_id TEXT,source_edge_sha TEXT) WITHOUT ROWID; CREATE INDEX edge_subject ON edges(subject); CREATE TABLE resolved_edges(id TEXT,subject TEXT,object TEXT,has_context INTEGER); CREATE INDEX resolved_subject ON resolved_edges(subject);')
        for eid,subject,profile in [('a','product1','profile1'),('b','product1','profile2'),('c','product2','profile3')]:
            db.execute('INSERT INTO edges VALUES(?,?,?,?,?)',(eid,subject,profile,eid,'synthetic-pin'))
            db.execute('INSERT INTO resolved_edges VALUES(?,?,?,1)',(eid,subject,profile))
        for subject in ('product1','product2','absent'):
            self.assertEqual(sorted(db.execute(OLD_SQL,(subject,))),sorted(db.execute(C.PROFILE_EDGE_SQL,(subject,))))
            plan=[r[-1] for r in db.execute('EXPLAIN QUERY PLAN '+C.PROFILE_EDGE_SQL,(subject,))]
            self.assertTrue(any('SEARCH r USING INDEX resolved_subject' in r for r in plan),plan)
        db.close()
    def test_full_fixture_response_equal_prior_reviewed_consumer(self):
        f=F.SourceConsumerTests('test_actual_value_context_and_restored_basis');f.setUp()
        try:
            path=ROOT/'reviewed-source-v2/candidate/scripts/source_scoped_north_star_consumer.py'
            self.assertEqual(sha_file(path),'a87b2117981ffa6beba37547a23b8ee36040bb7b8bec17aaec99b22ff70322f0')
            spec=importlib.util.spec_from_file_location('prior_reviewed_consumer',path);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
            reader=old.SourceScopedConsumer(f.source,f.bulk,f.basis,sha_file(f.bulk/'manifest.json'),sha_file(f.basis/'manifest.json'))
            try:self.assertEqual(reader.lookup('off','synthetic-release','gtin','001234',include_candidates=True),f.query(include_candidates=True))
            finally:reader.close()
        finally:f.tearDown()

if __name__=='__main__':unittest.main()
