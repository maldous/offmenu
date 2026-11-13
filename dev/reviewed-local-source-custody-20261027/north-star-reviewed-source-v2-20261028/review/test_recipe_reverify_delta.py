import contextlib,gzip,hashlib,io,json,sqlite3,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'candidate/scripts'));sys.path.insert(0,str(ROOT/'review'))
from test_recipe_inspector import fixture
from inspect_recipe_relations import inspect,file_sha

class ReverifyDeltaProbes(unittest.TestCase):
    def run_mutation(self,sql,expected):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=root/'source';p.mkdir();(p/'recipes').mkdir();s=root/'schema';s.mkdir()
            sb=(ROOT/'selected/package-contract/common-data.schema.json').read_bytes();(s/'schema.json').write_bytes(sb)
            payload=gzip.compress((json.dumps(fixture())+'\n').encode());(p/'recipes/a.jsonl.gz').write_bytes(payload)
            manifest=json.dumps({'files':[{'key':'recipes/a.jsonl.gz','bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest(),'packets':1}]}).encode();(p/'manifest.json').write_bytes(manifest);pin=hashlib.sha256(manifest).hexdigest()
            with contextlib.redirect_stdout(io.StringIO()):inspect(p,pin,s,root/'first','recipes/')
            index=root/'first/relation-query-index.sqlite'
            with sqlite3.connect(index) as db:db.execute(sql)
            before=file_sha(index)
            with self.assertRaisesRegex(ValueError,expected),contextlib.redirect_stdout(io.StringIO()):inspect(p,pin,s,root/'reverify','recipes/',index)
            self.assertEqual(file_sha(index),before);self.assertFalse((root/'reverify/report.json').exists())
    def test_extra_resource_cannot_hide_in_existing_index(self):
        self.run_mutation("INSERT INTO resources VALUES ('urn:test:extra','urn:offmenu:type:RecipeVariant','source-scoped','{}')",'extent differs')
    def test_missing_relation_cannot_survive_reverification(self):
        self.run_mutation("DELETE FROM relations WHERE predicate='urn:offmenu:relation:hasStep'",'projection differs')
    def test_preserved_numbers_do_not_hide_evidence_mutation(self):
        self.run_mutation("UPDATE facts SET evidence_sha256='different-evidence'",'projection differs')

if __name__=='__main__':unittest.main()
