import base64,copy,hashlib,importlib.util,json,os,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
P=Path(__file__).resolve().parents[1]/'scripts/publish-manual-global-result.py'
spec=importlib.util.spec_from_file_location('manualpub',P);p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

class Global:
    a=types.SimpleNamespace(canonical=p.canonical)
    STATES=('ready-nextstage','held','missing-contract')
    def __init__(self):
        self.manifest={'assets':[{'assetId':'asset-'+str(i),'countryHints':['AA'],'disposition':'held','holds':['rights-unapproved']} for i in range(3)],'cells':[{'country':'AA','type':'recipes','retainedStatus':'UNVERIFIED'},{'country':'BB','type':'ingredients','retainedStatus':'PARTIAL'}],'statTargets':[{'path':'/fixed/metadata/path','assetIds':['asset-0'],'recordedIdentities':[{'sha256':'1'*64,'bytes':2}]}]}
    def sanitize_report(self,r):
        if r.get('unexpected') is not None:raise ValueError('unsafe report')
        return r
    def manifest_config(self):return self.manifest
    def expand_outcomes(self,groups,count):return [{'custody':'unverified','stage':'held','code':None} for _ in range(count)]
    def run_global(self,*a,**k):raise AssertionError('publisher must never acquire')

class FakeAPI:
    def __init__(self):
        self.head='a'*40;self.tree='b'*40;self.refs={p.BRANCH:self.head};self.blobs={};self.trees={self.tree:{}};self.commits={self.head:{'sha':self.head,'tree':{'sha':self.tree},'parents':[]}};self.calls=[];self.private=True;self.owner=p.OWNER_ID;self.push=True;self.compare='ahead';self.uncertain=False;self.reject=False;self.race=False;self.bad_readback=False
    def call(self,method,path,payload=None,absent=False):
        self.calls.append((method,path,payload));base='repos/'+p.REPOSITORY
        if method=='GET' and path=='user':return {'id':self.owner}
        if method=='GET' and path==base:return {'id':p.REPOSITORY_ID,'full_name':p.REPOSITORY,'private':self.private,'owner':{'id':p.OWNER_ID},'permissions':{'push':self.push}}
        if method=='GET' and '/git/ref/heads/' in path:return {'object':{'sha':self.refs[path.split('/git/ref/heads/')[1]]}}
        if method=='GET' and '/compare/' in path:return {'status':self.compare}
        if method=='GET' and '/git/commits/' in path:return self.commits[path.rsplit('/',1)[1]]
        if method=='GET' and '/contents/' in path:
            file,commit=path.split('/contents/')[1].split('?ref=');tree=self.commits[commit]['tree']['sha'];blob=self.trees[tree].get(file)
            if blob is None:return None
            raw=self.blobs[blob]
            return {'type':'file','sha':blob,'size':len(raw),'encoding':'base64','content':base64.b64encode(raw if not self.bad_readback else b'wrong').decode()}
        if method=='POST' and path.endswith('/git/blobs'):
            raw=payload['content'].encode();key=p.blob_sha(raw);self.blobs[key]=raw;return {'sha':key}
        if method=='POST' and path.endswith('/git/trees'):
            rows=copy.deepcopy(self.trees[payload['base_tree']]);rows.update({e['path']:e['sha'] for e in payload['tree']});key=hashlib.sha1(p.canonical(rows)).hexdigest();self.trees[key]=rows;return {'sha':key}
        if method=='POST' and path.endswith('/git/commits'):
            key=hashlib.sha1(p.canonical(payload)).hexdigest();self.commits[key]={'sha':key,'tree':{'sha':payload['tree']},'parents':payload['parents']}
            if self.race:
                other='d'*40;self.commits[other]={'sha':other,'tree':{'sha':self.tree},'parents':[self.head]};self.refs[p.BRANCH]=other
            return {'sha':key}
        if method=='PATCH' and '/git/refs/heads/' in path:
            assert payload['force'] is False
            if self.reject:raise OSError('do not expose token')
            new=payload['sha'];assert self.commits[new]['parents']==[self.refs[p.BRANCH]]
            self.refs[p.BRANCH]=new
            if self.uncertain:raise OSError('response lost')
            return {'object':{'sha':new}}
        raise AssertionError((method,path))

class Tests(unittest.TestCase):
    def setUp(self):
        self.uid=patch.object(p.os,'getuid',return_value=1000);self.uid.start();self.euid=patch.object(p.os,'geteuid',return_value=1000);self.euid.start();self.home=patch.object(p.pwd,'getpwuid',return_value=types.SimpleNamespace(pw_dir='/home/test'));self.home.start();self.addCleanup(patch.stopall)
        self.g=Global();report={'status':'complete-with-errors','assetOutcomeGroups':[],'changes':[],'cellStageCounts':{'default':[0,0,1],'overrides':[[0,[0,3,0]]]},'statOutcomeGroups':[{'state':'inaccessible','pathRanges':[[0,0]]}]}
        self.envelope={'schemaVersion':'offmenu-owner-manual-global-result/1','executionContext':'owner-manual-foo','invokingUID':1000,'outputRoot':'/home/test/src/offmenu-data/owner-collection-runtime','handover':{'handoffId':p.HANDOFF,'runtimeConfigSHA256':p.RUNTIME_SHA256,'dispatchHoldSHA256':p.HOLD_SHA256,'executionContext':'owner-manual-foo','runnerResumeRequiresOutcomeImport':True},'historicalRunnerRootAccess':{'/srv/offmenu-refresh/outputs/collection':'inaccessible','/srv/offmenu-refresh/cache':'absent'},'nativeClaimsRoot':p.NATIVE_CLAIMS,'nativeCoverageExhaustive':False,'globalReportSHA256':p.sha(p.canonical(report)),'globalReport':report};self.api=FakeAPI()
    def test_complete_expansion(self):
        receipt,files,raw=p.build_payload(self.envelope,self.g)
        self.assertEqual(receipt['expandedCounts'],{'assets':3,'countryTypeCells':2,'statPaths':1});self.assertFalse(receipt['isActionsReceipt']);self.assertFalse(receipt['rawSourceBodiesPublished']);self.assertEqual(len(files),4)
        self.assertEqual(sum(len(x[1]) for x in files),receipt['totalMetadataBytes'])
    def test_success(self):
        r=p.publish_result(self.envelope,self.g,self.api);self.assertTrue(r['verified']);self.assertEqual(r['status'],'published-and-verified');self.assertNotIn('latest-receipt',str(self.api.calls));self.assertNotIn('offmenu-runner-results',str(self.api.calls))
    def test_repeat_has_no_mutation(self):
        p.publish_result(self.envelope,self.g,self.api);self.api.calls=[];r=p.publish_result(self.envelope,self.g,self.api);self.assertEqual(r['status'],'verified-existing');self.assertTrue(all(c[0]=='GET' for c in self.api.calls))
    def test_uncertain_ref_reconciles_readonly(self):
        self.api.uncertain=True;r=p.publish_result(self.envelope,self.g,self.api);self.assertEqual(r['status'],'verified-after-uncertain-write');self.assertEqual(sum(c[0]=='PATCH' for c in self.api.calls),1)
    def test_uncertain_ref_without_admission_stays_unverified(self):
        self.api.reject=True;r=p.publish_result(self.envelope,self.g,self.api);self.assertFalse(r['verified']);self.assertIsNone(r['commit']);self.assertNotIn('token',str(r));self.assertEqual(sum(c[0]=='PATCH' for c in self.api.calls),1)
        self.api.reject=False;r=p.publish_result(self.envelope,self.g,self.api);self.assertTrue(r['verified'])
    def test_concurrent_sibling_not_overwritten(self):
        self.api.race=True;r=p.publish_result(self.envelope,self.g,self.api);self.assertFalse(r['verified']);self.assertEqual(self.api.refs[p.BRANCH],'d'*40);self.assertFalse(any(c[0]=='PATCH' for c in self.api.calls))
    def test_distinct_result_retains_both_receipts(self):
        first=p.publish_result(self.envelope,self.g,self.api);self.api.calls=[];other=copy.deepcopy(self.envelope);other['historicalRunnerRootAccess']['/srv/offmenu-refresh/cache']='readable';second=p.publish_result(other,self.g,self.api)
        self.assertTrue(second['verified']);self.assertNotEqual(first['receiptPath'],second['receiptPath']);tree=self.api.commits[second['commit']]['tree']['sha'];self.assertIn(first['receiptPath'],self.api.trees[tree]);self.assertIn(second['receiptPath'],self.api.trees[tree])
        self.api.calls=[];retry=p.publish_result(other,self.g,self.api);self.assertEqual(retry['status'],'verified-existing');self.assertTrue(all(c[0]=='GET' for c in self.api.calls))
    def test_blocked_then_real_result_both_published(self):
        blocked=copy.deepcopy(self.envelope);blocked['globalReport']={'status':'blocked'};blocked['globalReportSHA256']=p.sha(p.canonical(blocked['globalReport']));first=p.publish_result(blocked,self.g,self.api);second=p.publish_result(self.envelope,self.g,self.api)
        self.assertTrue(first['verified']);self.assertTrue(second['verified']);self.assertNotEqual(first['receiptPath'],second['receiptPath']);tree=self.api.commits[second['commit']]['tree']['sha'];self.assertIn(first['receiptPath'],self.api.trees[tree])
    def test_corrupt_same_digest_receipt_is_not_overwritten(self):
        first=p.publish_result(self.envelope,self.g,self.api);tree=self.api.commits[first['commit']]['tree']['sha'];raw=b'{}';blob=p.blob_sha(raw);self.api.blobs[blob]=raw;self.api.trees[tree][first['receiptPath']]=blob;self.api.calls=[]
        result=p.publish_result(self.envelope,self.g,self.api);self.assertFalse(result['verified']);self.assertEqual(result['errorCode'],'manual-handoff-receipt-conflict');self.assertTrue(all(c[0]=='GET' for c in self.api.calls))
    def test_identity_private_and_permission_gates(self):
        for key,value in [('private',False),('owner',999),('push',False),('compare','diverged')]:
            api=FakeAPI();setattr(api,key,value);r=p.publish_result(self.envelope,self.g,api);self.assertFalse(r['verified']);self.assertTrue(all(c[0]=='GET' for c in api.calls))
    def test_extra_envelope_field_no_network(self):
        self.envelope['rawRows']=['secret'];self.assertRaises(p.PublicationError,p.publish_result,self.envelope,self.g,self.api);self.assertEqual(self.api.calls,[])
    def test_wrong_runtime_and_root_rejected(self):
        for field,value in [('outputRoot','/secret'),('nativeClaimsRoot','/other'),('globalReportSHA256','1'*64),('invokingUID',123)]:
            env=copy.deepcopy(self.envelope);env[field]=value;self.assertRaises(p.PublicationError,p.validate_envelope,env,self.g)
        self.envelope['handover']['runtimeConfigSHA256']='1'*64;self.assertRaises(p.PublicationError,p.validate_envelope,self.envelope,self.g)
    def test_root_execution_rejected(self):
        
        with patch.object(p.os,'getuid',return_value=0):self.assertRaises(p.PublicationError,p.validate_envelope,self.envelope,self.g)
    def test_chunk_size_and_all_rows(self):
        rows=[{'i':i,'safe':'x'*5000} for i in range(100)];chunks=p.chunks('assets',rows);self.assertGreater(len(chunks),1);self.assertTrue(all(len(b)<=p.MAX_CHUNK for _,b in chunks));self.assertEqual([r for _,b in chunks for r in json.loads(b)['rows']],rows)
        self.assertRaises(p.PublicationError,p.chunks,'assets',[{'oversize':'x'*p.MAX_CHUNK}])
    def test_total_size_limit(self):
        with patch.object(p,'MAX_TOTAL',20):self.assertRaises(p.PublicationError,p.build_payload,self.envelope,self.g)
    def test_budget_no_api_calls(self):
        with patch.object(p,'MAX_CALLS',0):r=p.publish_result(self.envelope,self.g,self.api)
        self.assertFalse(r['verified']);self.assertEqual(self.api.calls,[])
    def test_corrupt_remote_bytes_not_success(self):
        self.api.bad_readback=True;r=p.publish_result(self.envelope,self.g,self.api);self.assertFalse(r['verified'])
    def test_blocked_report_publishes_only_summary(self):
        self.envelope['globalReport']={'status':'blocked'};self.envelope['globalReportSHA256']=p.sha(p.canonical(self.envelope['globalReport']));receipt,files,_=p.build_payload(self.envelope,self.g);self.assertEqual(len(files),1);self.assertEqual(receipt['sourceOutcome'],'blocked')
    def test_active_handoff_readonly(self):
        raw=(Path(__file__).resolve().parent/'fixtures/manual-global-handoff-checkpoint.json').read_bytes();record=json.loads(raw);commit='c'*40;tree='e'*40;blob=p.blob_sha(raw);self.api.blobs[blob]=raw;self.api.trees[tree]={'docs/operations/global-collection-manual-handoff-20261018.json':blob};self.api.commits[commit]={'sha':commit,'tree':{'sha':tree},'parents':[]};self.api.refs['integration/runner-cutover-disposition-20261018']=commit
        contracts={x['sourceKey']:x['sourceContractSHA256'] for x in record['selectedSources']};self.g.selection_config=lambda:{'sources':[{'sourceKey':x}for x in contracts]}
        old=p.sha
        with patch.object(p,'sha',side_effect=lambda raw:contracts[json.loads(raw)['sourceKey']] if isinstance(json.loads(raw),dict) and set(json.loads(raw))=={'sourceKey'} else old(raw)):
            result=p.verify_active_handover(self.g,self.api)
        self.assertEqual(result['status'],'active-verified');self.assertTrue(all(c[0]=='GET' for c in self.api.calls))
    def test_inactive_handoff_no_network_mutation(self):
        self.api.refs['integration/runner-cutover-disposition-20261018']=self.api.head;self.assertRaises(p.PublicationError,p.verify_active_handover,self.g,self.api);self.assertTrue(all(c[0]=='GET' for c in self.api.calls))

if __name__=='__main__':unittest.main()
