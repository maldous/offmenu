import unittest,json,hashlib
from join import main
class JoinTests(unittest.TestCase):
 def doc(self,o):
  s=json.dumps(o);return {'name':'synthetic.json','text':s,'sha256':hashlib.sha256(s.encode()).hexdigest()}
 def row(self,owner=1,nextAction=''):
  return {'id':'TEST','historical':{'owner':owner,'nextAction':nextAction}}
 def test_ack_not_acceptance(self):
  d=self.doc([{'status':'fulfilled','value':{'owner':1,'path':'metadata.json','envelope':{'isError':False}}}]);r=main([self.row()],[d]);self.assertEqual(r['completed_obligations'],0);self.assertFalse(r['rows'][0]['completion_claimed'])
 def test_bad_pin(self):
  d=self.doc({});d['sha256']='0'*64
  with self.assertRaises(ValueError):main([self.row()],[d])
 def test_exact_hash_absent(self):
  r=main([self.row(nextAction='a'*64)],[self.doc({'prefix':'a'*8})]);self.assertEqual(r['rows'][0]['exact_bindings'][0]['references'],[])
 def test_null_owner_does_not_match(self):
  r=main([self.row(None)],[self.doc([{'value':{'path':'x'}}])]);self.assertEqual(r['rows'][0]['custody_recovery_pointers'],[])
 def test_immutable_reference(self):
  d=self.doc({'receipt':'b'*64});r=main([self.row(nextAction='b'*64)],[d]);x=r['rows'][0]['exact_bindings'][0];self.assertEqual(x['references'][0]['file_sha256'],d['sha256']);self.assertFalse(x['artifact_or_review_verified'])
 def test_claimed_acceptance_does_not_self_authorize(self):
  digest='a1'*32;d=self.doc({'sha256':digest,'acceptance_verified':True,'source_revision':'rev-42'})
  r=main([self.row(nextAction=digest)],[d]);self.assertFalse(r['rows'][0]['exact_bindings'][0]['artifact_or_review_verified']);self.assertEqual(r['completed_obligations'],0)
 def test_mismatched_artifact_not_bound_by_revision(self):
  expected='ab'*32;d=self.doc({'sha256':'cd'*32,'acceptance_verified':True,'source_revision':'rev-42'})
  r=main([self.row(nextAction=expected+' rev-42')],[d]);self.assertEqual(r['rows'][0]['exact_bindings'][0]['references'],[])
 def test_revision_mismatch_never_promotes_hash_reference(self):
  digest='ef'*32;d=self.doc({'sha256':digest,'source_revision':'rev-2','reviewer_acceptance':True})
  r=main([self.row(nextAction=digest+' requires rev-1')],[d]);self.assertTrue(r['rows'][0]['exact_bindings'][0]['references']);self.assertFalse(r['rows'][0]['completion_claimed'])
 def test_conflicting_receipts_both_preserved_not_accepted(self):
  digest='12'*32;d=self.doc([{'sha256':digest,'reviewer_acceptance':True},{'sha256':digest,'reviewer_acceptance':False}])
  r=main([self.row(nextAction=digest)],[d]);b=r['rows'][0]['exact_bindings'][0];self.assertEqual(len(b['references']),2);self.assertFalse(b['artifact_or_review_verified']);self.assertEqual(r['completed_obligations'],0)
if __name__=='__main__':unittest.main()
