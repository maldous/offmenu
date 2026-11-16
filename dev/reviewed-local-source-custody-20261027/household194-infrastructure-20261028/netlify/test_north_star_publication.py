import unittest
from unittest.mock import patch
import netlify_north_star_publisher as pub
import prepare_north_star_projection_reviewed as gen
class NorthStarTests(unittest.TestCase):
 def manifest(self):
  return {'schemaVersion':'offmenu-north-star-full-derivation/1','complete':True,'status':'all-selected-packets-derived-and-consumer-queries-exercised','expectedAssets':1,'completedAssets':1,'semanticStatus':'candidate-not-admitted','candidateOnly':True,'originalsModified':False,'publicationEligible':False,'publicAdmissionGranted':False,'consumerIndex':{'acceptedIdentityJoins':0,'servedAppQueries':0,'queries':{}},'confidence':{'status':'not-calibrated','probability':None},'baseDependencies':{'manifestByteSha256':'a'*64},'selection':{},'counts':{},'files':[{'key':'shards/000000/derivations.jsonl.gz','bytes':4,'sha256':'b'*64,'sidecarPackets':1}]}
 def proof(self):return {'producerManifestSha256':'c'*64,'status':'reviewed-source-scoped-consumer-proof','publicationScope':'candidate-sidecars-only','sourceRightsPreserved':True,'privatePayloadExcluded':True}
 def test_projection_preserves_candidate(self):
  r=gen.project(self.manifest(),self.proof(),'c'*64,'d'*64,'e'*64);self.assertEqual(r['semanticStatus'],'candidate-not-admitted');self.assertFalse(r['producerPublicationState']['publicAdmissionGranted']);self.assertEqual(r['servedAppQueries'],0)
 def test_no_local_artifacts(self):
  for key in ('consumer-index.sqlite','shards/000000/query-index.jsonl.gz','shards/000000/receipt.json','selection.json','../private'):
   m=self.manifest();m['files'][0]['key']=key
   with self.assertRaises(ValueError):gen.project(m,self.proof(),'c'*64,'d'*64,'e'*64)
 def test_incomplete_rejected(self):
  m=self.manifest();m['complete']=False
  with self.assertRaises(ValueError):gen.project(m,self.proof(),'c'*64,'d'*64,'e'*64)
 def test_no_unreviewed_publication(self):
  with self.assertRaises(ValueError):gen.project(self.manifest(),{},'c'*64,'d'*64,'e'*64)
 def test_no_base_aliases(self):
  for path in ('/index.html','/manifest.json','/recipes/manifest.json','/common-data/manifest.json','/common-data/releases/common-corpus-expanded-20261014/manifest.json'):self.assertFalse(pub.allowed_delta(path))
 def test_only_exact_derived_namespace(self):
  self.assertTrue(pub.allowed_delta(pub.PREFIX+'manifest.json'));self.assertTrue(pub.allowed_delta(pub.PREFIX+'shards/000000/derivations.jsonl.gz'))
  self.assertFalse(pub.allowed_delta(pub.PREFIX+'shards/000000/query-index.jsonl.gz'));self.assertFalse(pub.allowed_delta('/common-data/derived-releases/other/manifest.json'))
 def test_served_base_mismatch(self):
  with patch.object(pub.http.client,'HTTPSConnection') as c:
   c.return_value.getresponse.return_value.status=200;c.return_value.getresponse.return_value.read.return_value=b'wrong'
   with self.assertRaises(pub.Stop):pub.verify_served_base('a'*64)
