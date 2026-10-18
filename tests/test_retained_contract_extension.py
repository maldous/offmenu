"""Reviewed metadata composition and synthetic streaming-only verification."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import hashlib,os,tempfile,time,unittest
from offmenu.refresh import retained_contract_extension as extension
from offmenu.refresh import retained_integrity_verification as verifier
from offmenu.refresh import media_preparation as media
from offmenu.refresh.core import canonical,sha,RefreshError

class RetainedTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.path=self.root/'original.gz';self.body=b'\x1f\x8b'+b'fixture'*400000;self.path.write_bytes(self.body)
  self.identity={'path':str(self.path),'sha256':hashlib.sha256(self.body).hexdigest(),'bytes':len(self.body)}
  self.asset={'assetId':'file:fixture','disposition':'retained','retainedOriginal':self.identity,'preparationContract':None,'sourceStageHolds':[],'downstreamHolds':['normalization-unselected']}
  self.manifest={'assets':[self.asset]}
  self.contract={'schemaVersion':verifier.SCHEMA,'assetId':'file:fixture','expectedSHA256':self.identity['sha256'],'expectedBytes':len(self.body),'expectedMediaTypes':['application/gzip'],'permissions':{'read':True,'copy':False,'extract':False},'holds':[],'maximumReadBytes':len(self.body),'chunkBytes':1024**2,'maximumSniffBytes':65536,'maximumSeconds':300,'maximumOutputBytes':0,'completeReadRequired':True,'decompressionAllowed':False,'networkRequests':0}
  self.row={'assetId':'file:fixture','originalAssetSHA256':sha(canonical(self.asset)),'retainedOriginal':self.identity,'preparationContract':None,'verificationContract':self.contract,'sourceStageHolds':[],'downstreamHolds':['normalization-unselected'],'verificationMode':'streaming-integrity-only','permissionBasis':'synthetic explicit fixture','eligibility':'verification-candidate','missingFields':[],'evidenceRefs':[],'effectiveReadHolds':[]}
  self.extension={'schemaVersion':extension.SCHEMA,'status':'prepared-for-review-not-active','records':[self.row],'runtimeEnabled':False,'selectedAssetIds':[],'suggestedAssetIds':['file:fixture']}
 def tearDown(self):self.tmp.cleanup()
 def test_default_no_selection_no_io_or_permissions_created(self):
  with patch('builtins.open',side_effect=AssertionError('read forbidden')),patch.object(Path,'stat',side_effect=AssertionError('stat forbidden')):
   result=extension.compose_retained_contracts(self.manifest,self.extension);jobs=extension.select_retained_verification(self.manifest,self.extension)
  self.assertEqual(result['assets'],self.manifest['assets']);self.assertEqual(jobs,[]);self.assertEqual(result['retainedContractExtension']['selectedCount'],0)
 def test_exact_selected_verification_job_stays_inactive(self):
  result=extension.select_retained_verification(self.manifest,self.extension,selected_asset_ids=['file:fixture']);self.assertEqual(len(result),1);self.assertEqual(result[0]['status'],'prepared-for-review-not-active');self.assertEqual(result[0]['original'],self.identity)
 def test_source_identity_permissions_and_nested_read_hold_fail_closed(self):
  for field,value in [('originalAssetSHA256','0'*64),('effectiveReadHolds',['do not open body'])]:
   bad=deepcopy(self.extension);bad['records'][0][field]=value
   with self.subTest(field=field),self.assertRaises(RefreshError):extension.select_retained_verification(self.manifest,bad,selected_asset_ids=['file:fixture'])
  bad=deepcopy(self.extension);bad['records'][0]['verificationContract']['permissions']['extract']=True
  with self.assertRaises(RefreshError):extension.select_retained_verification(self.manifest,bad,selected_asset_ids=['file:fixture'])
 def test_streaming_full_integrity_no_payload_or_readiness(self):
  with patch('socket.create_connection',side_effect=AssertionError('network forbidden')):result=verifier.verify_retained(self.contract,self.path,time.monotonic()+20)
  self.assertEqual(result['status'],'verified-retained');self.assertEqual(result['bytesRead'],len(self.body));self.assertTrue(result['integrityVerified']);self.assertTrue(result['mediaObserved']);self.assertFalse(result['nextStageReady']);self.assertFalse(result['extractionPerformed']);self.assertEqual(list(self.root.iterdir()),[self.path]);self.assertEqual(media.MAX_ORIGINAL_BYTES,1024**3)
 def test_large_exact_original_has_bound_without_parser_limit_expansion(self):
  contract=deepcopy(self.contract);contract['expectedBytes']=contract['maximumReadBytes']=13132516914;contract['maximumSeconds']=1200
  self.assertIs(verifier.validate_contract(contract),contract);self.assertEqual(media.MAX_ORIGINAL_BYTES,1024**3)
  with patch.object(os,'open',side_effect=AssertionError('partial must not open')):
   result=verifier.verify_retained(contract,self.root/'planet.osm.pbf.part',time.monotonic()+1)
  self.assertEqual(result['errorCode'],'verification-partial-held');self.assertEqual(result['bytesRead'],0)
 def test_deadline_before_open_and_extent_mismatch_zero_read(self):
  with patch.object(os,'open',side_effect=AssertionError('deadline must not open')):result=verifier.verify_retained(self.contract,self.path,time.monotonic()-1)
  self.assertEqual(result['errorCode'],'verification-deadline');self.assertEqual(result['bytesRead'],0)
  contract=deepcopy(self.contract);contract['expectedBytes']+=1;contract['maximumReadBytes']+=1;result=verifier.verify_retained(contract,self.path,time.monotonic()+1);self.assertEqual(result['errorCode'],'verification-extent-mismatch');self.assertEqual(result['bytesRead'],0)
 def test_digest_mismatch_does_not_mint_identity(self):
  contract=deepcopy(self.contract);contract['expectedSHA256']='0'*64;result=verifier.verify_retained(contract,self.path,time.monotonic()+10);self.assertEqual(result['errorCode'],'verification-digest-mismatch');self.assertFalse(result['integrityVerified']);self.assertIsNone(result['originalSHA256']);self.assertEqual(result['bytesRead'],len(self.body))
 def test_read_hold_symlink_and_unknown_media_stay_explicit(self):
  contract=deepcopy(self.contract);contract['holds']=['read'];result=verifier.verify_retained(contract,self.path,time.monotonic()+1);self.assertEqual(result['errorCode'],'verification-read-held');self.assertEqual(result['bytesRead'],0)
  link=self.root/'symlink.gz';link.symlink_to(self.path);result=verifier.verify_retained(self.contract,link,time.monotonic()+1);self.assertEqual(result['errorCode'],'verification-unavailable')
  contract=deepcopy(self.contract);contract['expectedMediaTypes']=['application/json'];result=verifier.verify_retained(contract,self.path,time.monotonic()+10);self.assertTrue(result['integrityVerified']);self.assertEqual(result['errorCode'],'verification-media-unverified');self.assertFalse(result['mediaObserved']);self.assertFalse(result['nextStageReady'])
 def test_closed_sanitizer_rejects_path_or_nextstage_promotion(self):
  report=verifier.verify_retained(self.contract,self.path,time.monotonic()+10)
  for key,value in [('rawPath',str(self.path)),('nextStageReady',True),('bytesRead',True)]:
   bad={**report,key:value}
   with self.subTest(key=key),self.assertRaises(ValueError):verifier.sanitize_report(bad,self.contract)

if __name__=='__main__':unittest.main()
