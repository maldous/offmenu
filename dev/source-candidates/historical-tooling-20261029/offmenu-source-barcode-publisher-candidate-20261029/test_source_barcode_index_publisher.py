"""Synthetic descriptor tests only: never invoke publisher main or private APIs."""
import ast
import copy
import hashlib
import importlib.util
import pathlib
import unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parent
BASE=ROOT/'recipe_transport_exact.py'
CANDIDATE=ROOT/'netlify_source_barcode_index_publisher.py'
spec=importlib.util.spec_from_file_location('barcode_publisher_candidate',CANDIDATE)
p=importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
PROOF='a'*64
MANIFEST='b'*64
PREFIX='/common-data/derived-releases/source-barcode-index-v1-20261029/'
EXPECTED={PREFIX+'manifest.json'}|{PREFIX+'shards/'+format(i,'02x')+'.json.gz' for i in range(256)}

def descriptor():
    return {'schemaVersion':'offmenu-netlify-source-barcode-index-delta/1','siteId':p.SITE,
      'consumerProofSha256':PROOF,'producerManifestSha256':MANIFEST,'baseDeployId':'c'*24,
      'servedBaseManifestSha256':'d'*64,'semanticStatus':'candidate-not-admitted',
      'acceptedIdentityJoins':0,'servedAppQueries':0,
      'files':[{'path':path,'bytes':0,'sha1':'e'*40,'sha256':'f'*64} for path in sorted(EXPECTED)]}

class DescriptorTests(unittest.TestCase):
    def setUp(self):
        self.network=patch.object(p.http.client,'HTTPSConnection',side_effect=AssertionError('network forbidden'))
        self.network.start()
        self.addCleanup(self.network.stop)
        for name in ['ssh','api','fetch','inventory','journal','verify_served_base']:
            guard=patch.object(p,name,side_effect=AssertionError(name+' forbidden'))
            guard.start();self.addCleanup(guard.stop)
    def reject(self,d):
        with self.assertRaises(p.Stop):p.validate_descriptor(d,PROOF,MANIFEST)
    def test_complete_257_unique_files(self):
        d=descriptor();result=p.validate_descriptor(d,PROOF,MANIFEST)
        self.assertEqual(set(result),EXPECTED);self.assertEqual(len(result),257)
        self.assertIs(result[PREFIX+'manifest.json'],d['files'][0])
    def test_all_256_exact_shards(self):
        self.assertEqual({x.removeprefix(PREFIX+'shards/') for x in p.EXPECTED_PATHS if '/shards/' in x},{format(i,'02x')+'.json.gz' for i in range(256)})
        for path in EXPECTED:self.assertTrue(p.allowed_delta(path))
    def test_inventory_order_independent(self):
        d=descriptor();d['files'].reverse();self.assertEqual(set(p.validate_descriptor(d,PROOF,MANIFEST)),EXPECTED)
    def test_each_missing_entry_rejected(self):
        d=descriptor()
        for index in range(257):
            with self.subTest(missing=d['files'][index]['path']):
                q=copy.deepcopy(d);q['files'].pop(index);self.reject(q)
    def test_additional_entry_rejected(self):
        d=descriptor();d['files'].append({**d['files'][0],'path':PREFIX+'extra.json'});self.reject(d)
    def test_duplicate_path_cannot_replace_missing_shard(self):
        d=descriptor();d['files'][-1]=copy.deepcopy(d['files'][0]);self.reject(d)
    def test_duplicate_extra_entry(self):
        d=descriptor();d['files'].append(copy.deepcopy(d['files'][0]));self.reject(d)
    def test_traversal_case_suffix_and_unescaped_dot_lookalikes(self):
        bad=[PREFIX+'shards/../00.json.gz',PREFIX+'shards/./00.json.gz',PREFIX+'shards//00.json.gz',
          PREFIX+'shards/AA.json.gz',PREFIX+'shards/0A.json.gz',PREFIX+'shards/000.json.gz',
          PREFIX+'shards/00XjsonXgz',PREFIX+'shards/00.json.gz?x=1',PREFIX+'shards/00.json.gz#frag',
          PREFIX+'shards/00.json.gz/extra',PREFIX+'shards/00.json.gz\n',PREFIX+'manifestXjson',
          PREFIX+'MANIFEST.json',PREFIX+'shards/00.JSON.GZ',PREFIX+'shards/gg.json.gz',
          PREFIX+'shards/00.json',PREFIX+'shards/00.json.gzip',PREFIX+'shards\\00.json.gz',
          '/common-data/derived-releases/north-star-recipe-context-v1-20261028/manifest.json',
          'https://example.invalid'+PREFIX+'manifest.json',None,[],{}]
        for path in bad:
            with self.subTest(path=path):
                self.assertFalse(p.allowed_delta(path));d=descriptor();d['files'][-1]['path']=path;self.reject(d)
    def test_invalid_sha1(self):
        for value in ['A'*40,'e'*39,'e'*41,'g'*40,'e'*40+'\n',None,123]:
            with self.subTest(value=value):
                d=descriptor();d['files'][1]['sha1']=value;self.reject(d)
    def test_invalid_sha256(self):
        for value in ['F'*64,'f'*63,'f'*65,'g'*64,'f'*64+'\n',None,123]:
            with self.subTest(value=value):
                d=descriptor();d['files'][1]['sha256']=value;self.reject(d)
    def test_invalid_byte_metadata(self):
        for value in [-1,0.0,True,False,'0',None]:
            with self.subTest(value=value):
                d=descriptor();d['files'][1]['bytes']=value;self.reject(d)
    def test_missing_entry_metadata(self):
        for key in ['path','bytes','sha1','sha256']:
            with self.subTest(key=key):
                d=descriptor();del d['files'][1][key];self.reject(d)
    def test_invalid_file_collection(self):
        for value in [None,{},'',[],[None],['not-an-entry']]:
            with self.subTest(value=value):
                d=descriptor();d['files']=value;self.reject(d)
    def test_scope_and_pin_mismatches(self):
        for key,value in [('schemaVersion','offmenu-netlify-north-star-recipe-delta/1'),('siteId','other-site'),('consumerProofSha256','0'*64),('producerManifestSha256','0'*64)]:
            with self.subTest(key=key):
                d=descriptor();d[key]=value;self.reject(d)
        for key in ['schemaVersion','siteId','consumerProofSha256','producerManifestSha256']:
            with self.subTest(missing=key):
                d=descriptor();del d[key];self.reject(d)
    def test_semantic_mismatches(self):
        for key,value in [('semanticStatus','accepted'),('acceptedIdentityJoins',1),('servedAppQueries',1)]:
            with self.subTest(key=key):
                d=descriptor();d[key]=value;self.reject(d)
        for key in ['semanticStatus','acceptedIdentityJoins','servedAppQueries']:
            with self.subTest(missing=key):
                d=descriptor();del d[key];self.reject(d)
    def test_descriptor_must_be_object(self):
        for value in [None,[],42,'']:
            with self.subTest(value=value):self.reject(value)

class TransportPreservationTests(unittest.TestCase):
    def test_baseline_and_all_other_nodes_are_exact(self):
        base=BASE.read_bytes();candidate=CANDIDATE.read_bytes()
        self.assertEqual(hashlib.sha256(base).hexdigest(),'0bf9f679b4b6dd3643456c31387e9396073d3e97ebc7058e2ff735dd6bc70bbb')
        a=ast.parse(base);b=ast.parse(candidate)
        changes={'ROOT','DESCRIPTOR','PREFIX','EXPECTED_PATHS','allowed_delta','validate_descriptor'}
        def key(n):
            if isinstance(n,(ast.FunctionDef,ast.ClassDef)):return n.name
            if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):return n.targets[0].id
            return None
        def untouched(tree,data):
            return [(ast.dump(n,include_attributes=False),ast.get_source_segment(data.decode(),n)) for n in tree.body if key(n) not in changes]
        self.assertEqual(untouched(a,base),untouched(b,candidate))
        self.assertIn('main',[n.name for n in a.body if isinstance(n,ast.FunctionDef)])
        self.assertEqual(p.UPLOAD_WORKERS,5)
        self.assertEqual(p.ROOT,p.BASE+'/source-barcode-index-publication-delta')
        self.assertEqual(p.DESCRIPTOR,p.BASE+'/source-barcode-index-publication-delta.json')
        self.assertEqual(p.PREFIX,PREFIX)

if __name__=='__main__':unittest.main(verbosity=2)
