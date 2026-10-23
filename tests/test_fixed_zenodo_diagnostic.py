"""HEAD and failure metadata fixtures. Never contacts a source or reads a body."""
from contextlib import ExitStack
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
m=module('zenodo_diagnostic_fixture','acquire-fixed-zenodo.py')
dispatch=module('zenodo_diagnostic_dispatch','dispatch-foo-job.py')

class HeadResponse:
    def __init__(self,status=200,headers=None):
        self.status=status;self.headers=headers or [('Content-Type','text/plain; charset=utf-8'),('Content-Length','110013794')]
        self.closed=False
    def getheaders(self):return self.headers
    def read(self,*args):raise AssertionError('HEAD body reads forbidden')
    def close(self):self.closed=True

class HeadConnection:
    sock=None
    def __init__(self,response,fail=False):self.response=response;self.requests=[];self.closed=False;self.fail=fail
    def request(self,method,path,*,headers):
        self.requests.append((method,path,headers))
        if self.fail:raise OSError('synthetic connection failure')
    def getresponse(self):return self.response
    def close(self):self.closed=True

class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);work=self.root/'collection';work.mkdir()
        prior={'sourceKey':m.SOURCE_KEY,'status':'failed','errorCode':'source-response-not-permitted',
               'network':{'requests':1,'bodyBytesRead':0}}
        raw=m.canonical(prior);self.prior_hash=m.sha(raw)
        (work/('zenodo15169428-result-'+self.prior_hash+'.json')).write_bytes(raw)
        self.claim=work/'intents'/(m.sha(m.URL.encode())+'.json');self.claim.parent.mkdir()
        self.claim_raw=m.canonical({'sourceKey':m.SOURCE_KEY,'state':'failed-no-retry','errorCode':'source-response-not-permitted'})
        self.claim.write_bytes(self.claim_raw)
        config={'method':'HEAD','url':m.URL,'headers':{'Accept-Encoding':'identity'},'maximumRequests':1,
                'maximumBodyBytes':0,'priorGet':{'detailSHA256':self.prior_hash}}
        prep=SimpleNamespace(pinned_bytes=lambda *_:m.canonical(config))
        self.stack=ExitStack();self.stack.enter_context(patch.object(m,'OUTPUT',self.root))
        self.stack.enter_context(patch.object(m,'PRIOR_DETAIL_SHA256',self.prior_hash))
        self.stack.enter_context(patch.object(m,'preparation_module',return_value=prep))
        self.stack.enter_context(patch('socket.create_connection',side_effect=AssertionError('live network forbidden')))
    def tearDown(self):self.stack.close();self.temp.cleanup()
    def run_head(self,status=200,headers=None,fail=False):
        connection=HeadConnection(HeadResponse(status,headers),fail=fail)
        calls=[]
        def factory(*args,**kwargs):calls.append((args,kwargs));return connection
        result=m.run_diagnostic(connection_factory=factory)
        return result,connection,calls

    def test_one_head_exact_headers_zero_body_and_unchanged_failed_claim(self):
        result,connection,calls=self.run_head()
        self.assertEqual(result['status'],'observed');self.assertEqual(result['networkRequests'],1)
        self.assertEqual(connection.requests,[('HEAD','/api/records/15169428/files/dataset.csv/content',{'Accept-Encoding':'identity'})])
        self.assertEqual(calls[0][0],('zenodo.org',443));self.assertLessEqual(calls[0][1]['timeout'],30)
        self.assertTrue(connection.response.closed);self.assertTrue(connection.closed)
        self.assertEqual(self.claim.read_bytes(),self.claim_raw)
        self.assertEqual(result['networkBodyBytesRead'],0);self.assertIsNone(result['priorGETHttpStatus'])
        self.assertFalse(result['priorGETCauseEstablished']);self.assertFalse(result['acquisitionEnabledByDiagnostic'])

    def test_prior_denial_and_redirect_remain_distinct_unknown_get_history(self):
        result,connection,_=self.run_head(403)
        self.assertEqual(result['responseMetadata']['httpStatus'],403)
        self.assertEqual(result['responseMetadata']['httpStatusClass'],'denial-or-auth-required')
        self.assertTrue(result['stopAfterResponse']);self.assertFalse(result['originalGETRetried'])
        self.assertEqual(len(connection.requests),1)

    def test_redirect_reports_only_safe_classification_and_no_follow(self):
        result,connection,_=self.run_head(302,[('Location','/records/15169428/files/dataset.csv?token=SECRET#PRIVATE')])
        location=result['responseMetadata']['location']
        self.assertEqual(location['classification'],'same-host')
        self.assertTrue(location['queryOrFragmentPresent']);self.assertFalse(location['sameRequestPath'])
        encoded=json.dumps(result);self.assertNotIn('SECRET',encoded);self.assertNotIn('PRIVATE',encoded)
        self.assertNotIn('/records/15169428/files',encoded);self.assertEqual(len(connection.requests),1)

    def test_cross_host_userinfo_and_nonhttps_locations_do_not_leak(self):
        for raw,expected in [('https://other.test/secret?key=HIDDEN','cross-host'),
                              ('https://user:password@zenodo.org/secret','invalid'),
                              ('http://zenodo.org/secret','non-https')]:
            value=m.response_metadata(302,[('Location',raw)])
            self.assertEqual(value['location']['classification'],expected)
            self.assertNotIn('secret',json.dumps(value));m.validate_response_metadata(value)

    def test_content_headers_bounded_and_parameters_not_retained(self):
        value=m.response_metadata(206,[('Content-Type','text/plain; secret=HIDDEN'),('Content-Length','110013794')])
        self.assertEqual(value['contentType'],'text/plain');self.assertEqual(value['contentLength'],110013794)
        self.assertNotIn('HIDDEN',json.dumps(value));m.validate_response_metadata(value)
        value=m.response_metadata(200,[('Content-Length','9'*100),('Content-Type','x'*1000)])
        self.assertIsNone(value['contentType']);self.assertIsNone(value['contentLength'])

    def test_duplicate_headers_remain_explicit(self):
        value=m.response_metadata(302,[('Location','https://zenodo.org/a'),('Location','https://other.test/b')])
        self.assertTrue(value['duplicateMetadataHeaders']);self.assertEqual(value['location']['classification'],'invalid')

    def test_second_invocation_never_repeats_head(self):
        self.run_head();result,connection,_=self.run_head()
        self.assertEqual(result['errorCode'],'diagnostic-already-attempted')
        self.assertEqual(result['networkRequests'],0);self.assertFalse(connection.requests)
        self.assertEqual(self.claim.read_bytes(),self.claim_raw)

    def test_exception_before_response_preserves_attempt_and_unknown_status(self):
        result,connection,_=self.run_head(fail=True)
        self.assertEqual(result['networkRequests'],1);self.assertIsNone(result['responseMetadata'])
        self.assertEqual(result['errorCode'],'diagnostic-request-failed');self.assertEqual(len(connection.requests),1)

    def test_late_result_write_failure_keeps_observed_status_in_summary(self):
        with patch.object(m,'write_immutable',side_effect=OSError('synthetic write failure')):
            result,_,_=self.run_head(403)
        self.assertEqual(result['errorCode'],'diagnostic-result-write-failed')
        self.assertEqual(result['responseMetadata']['httpStatus'],403);self.assertEqual(result['networkRequests'],1)
        self.assertFalse(result['detailPersisted']);m.sanitize_diagnostic(result)

    def test_prior_detail_tamper_blocks_before_head(self):
        path=self.root/'collection'/('zenodo15169428-result-'+self.prior_hash+'.json');path.write_text('{}')
        result,connection,_=self.run_head()
        self.assertEqual(result['networkRequests'],0);self.assertFalse(connection.requests)

    def test_nonfailed_original_intent_blocks_without_changes(self):
        self.claim.write_text('{"state":"verified"}')
        result,connection,_=self.run_head()
        self.assertEqual(result['errorCode'],'prior-intent-not-held');self.assertFalse(connection.requests)
        self.assertEqual(self.claim.read_text(),'{"state":"verified"}')

    def test_closed_diagnostic_summary_forbids_acquisition_or_prior_cause_claims(self):
        result,_,_=self.run_head()
        for key,value in [('method','GET'),('networkBodyBytesRead',1),('priorGETCauseEstablished',True),
                          ('acquisitionEnabledByDiagnostic',True),('priorGETHttpStatus',403)]:
            with self.assertRaises(ValueError):m.sanitize_diagnostic(dict(result,**{key:value}))

    def test_fixed_profile_has_no_request_override_and_fixed_mode(self):
        request={'schemaVersion':1,'jobId':'fixture-head','profile':'zenodo-response-metadata'}
        self.assertEqual(dispatch.parse_request(json.dumps(request).encode()),request)
        for key in ['url','method','headers','command']:
            with self.assertRaises(dispatch.JobError):dispatch.parse_request(json.dumps(dict(request,**{key:'bad'})).encode())
        steps=dispatch.profile_steps('zenodo-response-metadata',ROOT)
        self.assertEqual([s[0] for s in steps],['readiness','zenodo-response-tests','zenodo-response-metadata'])
        self.assertEqual(steps[-1][2][-1],'--response-metadata')

    def test_head_200_cannot_clear_failed_intent_or_enable_get(self):
        self.run_head(200)
        selected={'sourceKey':m.SOURCE_KEY,'url':m.URL,'expectedMD5':m.EXPECTED_MD5,
                  'aliases':[],'release':'fixture','rightsReference':'https://example.test/rights',
                  'downstreamHolds':['private-only']}
        calls=[]
        def forbidden(*args,**kwargs): calls.append(1);raise AssertionError('GET forbidden')
        with patch.object(m,'LEGACY_CACHE',self.root/'legacy-missing'):
            result=m.run_selected(selected,transport=forbidden)
        self.assertEqual(result['errorCode'],'source-claim-uncertain')
        self.assertEqual(result['network']['requests'],0);self.assertFalse(calls)
        self.assertEqual(self.claim.read_bytes(),self.claim_raw)

    def test_dispatcher_retains_status_headers_and_location_classification(self):
        result,_,_=self.run_head(302,[('Location','/redirect?token=SECRET'),('Content-Type','text/html')])
        result['priorDetailSHA256']='81f842a01b388b3924ae56d240b5e13653daec1221eedd934a550abe2f935260'
        evidence=dispatch.safe_evidence(json.dumps(result).encode())
        self.assertEqual(evidence['fixedResponseMetadata']['responseMetadata']['httpStatus'],302)
        self.assertEqual(evidence['fixedResponseMetadata']['responseMetadata']['contentType'],'text/html')
        self.assertNotIn('SECRET',json.dumps(evidence))

    def test_failed_get_status_is_retained_before_core_rejection(self):
        from test_fixed_zenodo_original import FixedOriginalTests, Response
        fixture=FixedOriginalTests('test_one_get_existing_engine_and_complete_integrity');fixture.setUp()
        try:
            result,_=fixture.run_source(Response(b'',status=403,headers={'Content-Length':'0','Content-Type':'text/html'}))
            self.assertEqual(result['errorCode'],'source-response-not-permitted')
            self.assertEqual(result['responseMetadata']['httpStatus'],403)
            from test_fixed_zenodo_original import m as original
            summary=original.summary_report(result)
            self.assertEqual(summary['responseMetadata']['contentType'],'text/html')
        finally:fixture.tearDown()

    def test_only_explicit_diagnostic_mode_selects_head(self):
        with patch.object(m,'run_diagnostic',return_value=m.diagnostic_report()) as run,patch('sys.stdout',io.StringIO()):
            m.main(['--response-metadata']);run.assert_called_once()
        with patch.object(m,'run_diagnostic') as run,patch('sys.stdout',io.StringIO()):
            self.assertEqual(m.main(['--response-metadata','--url','bad']),2);run.assert_not_called()

if __name__=='__main__':unittest.main()
