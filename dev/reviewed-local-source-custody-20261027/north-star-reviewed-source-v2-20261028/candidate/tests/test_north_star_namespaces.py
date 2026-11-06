import sys,sqlite3,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import inspect_north_star_namespace_coverage as M

class NamespaceTests(unittest.TestCase):
    def test_exact_namespaces_separate_no_lexical_egress(self):
        groups=M.summarize([('key1','source','release','barcode',1,1,1),('key2','source','release','GTIN',1,0,0)])
        self.assertEqual(len(groups),2);self.assertNotIn('key1',repr(groups));self.assertEqual(sum(x['sourceScopedKeys'] for x in groups),2)
    def test_ambiguous_product_keys_never_count_as_coverage(self):
        g=M.summarize([('key','source','release','barcode',2,1,1)])[0]
        self.assertEqual(g['ambiguousProductKeysNotMerged'],1);self.assertEqual(g.get('productProfileContextKeys',0),0)
    def test_multiple_assertions_same_product_count_one_key(self):
        db=sqlite3.connect(':memory:');db.executescript('CREATE TABLE identifiers(key_sha,source,release,namespace,subject);CREATE TABLE resolved_edges(subject,has_context);')
        db.executemany('INSERT INTO identifiers VALUES (?,?,?,?,?)',[('same','s','r','barcode','p'),('same','s','r','barcode','p')]);db.execute('INSERT INTO resolved_edges VALUES (?,?)',('p',1))
        g=M.summarize(db.execute(M.SQL))[0];db.close();self.assertEqual(g['uniqueProductKeys'],1);self.assertEqual(g['productProfileContextKeys'],1)
    def test_release_source_partition_retained(self):
        g=M.summarize([('a','source','release1','barcode',1,1,1),('b','source','release2','barcode',1,1,0),('c','other','release1','barcode',1,0,0)])
        self.assertEqual(len(g),3)

if __name__=='__main__':unittest.main()
