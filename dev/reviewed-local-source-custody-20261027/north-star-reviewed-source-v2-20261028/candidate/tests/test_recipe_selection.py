import contextlib
import gzip
import hashlib
import io
import json
import sys
import sqlite3
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'candidate/scripts'));sys.path.insert(0,str(ROOT/'review'))
from test_recipe_inspector import fixture
from inspect_recipe_relations import inspect,file_sha


class RecipeSelectionTests(unittest.TestCase):
    def test_index_hash_streams_instead_of_read_bytes(self):
        class GuardedPath:
            def read_bytes(self):raise AssertionError('unbounded whole-index read')
            def open(self,mode):
                self.assert_mode=mode
                return io.BytesIO(b'chunked synthetic index')
        p=GuardedPath();self.assertEqual(file_sha(p),hashlib.sha256(b'chunked synthetic index').hexdigest());self.assertEqual(p.assert_mode,'rb')

    def test_explicit_recipe_asset_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'package';p.mkdir();(p/'recipes').mkdir();s=root/'schema';s.mkdir()
            schema=(ROOT/'selected/package-contract/common-data.schema.json').read_bytes();(s/'schema.json').write_bytes(schema)
            b=gzip.compress((json.dumps(fixture())+'\n').encode());(p/'recipes/a.jsonl.gz').write_bytes(b)
            bad=b'not a common packet';(p/'other.jsonl.gz').write_bytes(bad)
            files=[{'key':k,'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest(),'packets':1} for k,v in [('recipes/a.jsonl.gz',b),('other.jsonl.gz',bad)]]
            m=json.dumps({'releaseId':'synthetic','files':files}).encode();(p/'manifest.json').write_bytes(m)
            with contextlib.redirect_stdout(io.StringIO()):r=inspect(p,hashlib.sha256(m).hexdigest(),s,root/'output','recipes/')
            self.assertEqual(r['packetsSchemaValidated'],1);self.assertEqual(r['assetPrefix'],'recipes/')
            self.assertEqual(len(r['selectedAssets']),1)
            index=root/'output/relation-query-index.sqlite';before=file_sha(index)
            with contextlib.redirect_stdout(io.StringIO()):recovered=inspect(p,hashlib.sha256(m).hexdigest(),s,root/'recovered','recipes/',index)
            self.assertEqual(file_sha(index),before);self.assertEqual(recovered['queries'],r['queries'])
            self.assertEqual(recovered['queryIndexMode'],'exact-source-reverified-read-only-existing')
            with sqlite3.connect(index) as db:db.execute("UPDATE facts SET numeric_value=999")
            with self.assertRaisesRegex(ValueError,'projection differs'):
                inspect(p,hashlib.sha256(m).hexdigest(),s,root/'tampered','recipes/',index)
            with self.assertRaises(ValueError):inspect(p,hashlib.sha256(m).hexdigest(),s,root/'bad','../')


if __name__=='__main__':unittest.main()
