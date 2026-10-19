#!/usr/bin/env python3
"""Publish one already-sanitized manual result. Never acquires or opens source bodies."""
from __future__ import annotations
import base64, hashlib, importlib.util, json, os, pwd, re, time
from pathlib import Path

REPOSITORY='maldous/offmenu'; REPOSITORY_ID=1416253963; OWNER_ID=6347545
BRANCH='integration/foo-owner-custody-snapshot-20261018'
ANCHOR='4aa0976b9dc509b91f76874717f9de5e5e5529df'
HANDOFF='owner-local-global-20261018-001'
HANDOFF_PATH='docs/operations/global-collection-manual-handoff-20261018.json'
HOLD_BLOB='edd18af68f570ce15acd83dc71323af20da46683';HOLD_BYTES=8676
HOLD_SHA256='fa87ebcb5463ffdec2f7bbfe0141da0c518b40a59c29297646b92a0644e165f1'
BASE_SOURCE='24b8bb0fa0eb7c7f6632aade4dcb6d8d9ee49793'
DEST='docs/handover/2026-10-18/foo-owner-custody/manual-global/'+HANDOFF
HELPER_SHA256='a628602ad83299f0e24f746cd36cf85df7ffc6e510200f7023f9c44f54bf1916'
RUNTIME_SHA256='8dd3372dd9c2f4f0ec5f845cdc1a97c64addf8fe12ccecc26603128bb2bf514b'
NATIVE_CLAIMS='/home/user/src/offmenu-data/originals/country-followthrough-20261015/claims'
MAX_CHUNK=128*1024; MAX_TOTAL=8*1024*1024; MAX_FILES=96; MAX_CALLS=256; MAX_SECONDS=300
SHA_RE=re.compile(r'[a-f0-9]{64}'); GIT_RE=re.compile(r'[a-f0-9]{40}')

class PublicationError(ValueError):pass

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()+b'\n'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def blob_sha(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
def require(condition,code='manual-publication-invalid'):
    if not condition:raise PublicationError(code)

def validate_envelope(envelope,g):
    """Validate before any GitHub calls; no files, runtime setup, or acquisition."""
    keys={'schemaVersion','executionContext','invokingUID','outputRoot','handover','historicalRunnerRootAccess','nativeClaimsRoot','nativeCoverageExhaustive','globalReportSHA256','globalReport'}
    require(isinstance(envelope,dict) and set(envelope)==keys,'manual-envelope-invalid')
    require(envelope['schemaVersion']=='offmenu-owner-manual-global-result/1' and envelope['executionContext']=='owner-manual-foo','manual-envelope-invalid')
    require(type(envelope['invokingUID']) is int and envelope['invokingUID']==os.getuid() and os.getuid()!=0 and os.geteuid()!=0,'manual-envelope-user-mismatch')
    handover=envelope['handover'];hk={'handoffId','runtimeConfigSHA256','dispatchHoldSHA256','executionContext','runnerResumeRequiresOutcomeImport'}
    require(isinstance(handover,dict) and set(handover)==hk and handover['handoffId']==HANDOFF and handover['dispatchHoldSHA256']==HOLD_SHA256 and handover['executionContext']=='owner-manual-foo' and handover['runnerResumeRequiresOutcomeImport'] is True,'manual-envelope-handoff-mismatch')
    require(isinstance(handover['runtimeConfigSHA256'],str) and SHA_RE.fullmatch(handover['runtimeConfigSHA256']) is not None,'manual-envelope-handoff-mismatch')
    require(handover['runtimeConfigSHA256']==RUNTIME_SHA256,'manual-envelope-runtime-mismatch')
    expected_root=str(Path(pwd.getpwuid(os.getuid()).pw_dir)/'src/offmenu-data/owner-collection-runtime')
    require(envelope['outputRoot']==expected_root and envelope['nativeClaimsRoot']==NATIVE_CLAIMS,'manual-envelope-path-mismatch')
    access=envelope['historicalRunnerRootAccess']
    require(isinstance(access,dict) and set(access)=={'/srv/offmenu-refresh/outputs/collection','/srv/offmenu-refresh/cache'} and all(v in {'readable','absent','not-directory','inaccessible','unsafe-path','io-uncertain'} for v in access.values()),'manual-envelope-access-invalid')
    require(envelope['nativeCoverageExhaustive'] is False,'manual-envelope-invalid')
    report=g.sanitize_report(envelope['globalReport'])
    require(report==envelope['globalReport'] and sha(g.a.canonical(report))==envelope['globalReportSHA256'],'manual-envelope-report-mismatch')
    require(len(canonical(envelope))<=MAX_CHUNK,'manual-envelope-size-limit')
    return envelope

def chunks(kind,rows):
    result=[];batch=[]
    for row in rows:
        candidate={'schemaVersion':'offmenu-manual-'+kind+'-chunk/1','rows':batch+[row]}
        if len(canonical(candidate))>MAX_CHUNK:
            require(bool(batch),'manual-metadata-row-size-limit')
            result.append(canonical({'schemaVersion':'offmenu-manual-'+kind+'-chunk/1','rows':batch}));batch=[row]
            require(len(canonical({'schemaVersion':'offmenu-manual-'+kind+'-chunk/1','rows':batch}))<=MAX_CHUNK,'manual-metadata-row-size-limit')
        else:batch.append(row)
    if batch:result.append(canonical({'schemaVersion':'offmenu-manual-'+kind+'-chunk/1','rows':batch}))
    return [(kind+'-'+str(i).zfill(3)+'.json',raw) for i,raw in enumerate(result)]

def build_payload(envelope,g):
    validate_envelope(envelope,g);report=envelope['globalReport'];manifest=g.manifest_config();digest=sha(canonical(envelope));prefix=DEST+'/results/'+digest
    files=[('summary.json',canonical(envelope))];counts={'assets':0,'countryTypeCells':0,'statPaths':0}
    if report['status'] in {'complete','complete-with-errors'}:
        outcomes=g.expand_outcomes(report['assetOutcomeGroups'],len(manifest['assets']));changes={x['assetIndex']:x for x in report['changes']}
        assets=[];retained_observations={}
        if 'retainedOriginalVerification' in report:retained_observations=g.retained_collection.observations(report['retainedOriginalVerification'])
        for i,(asset,outcome) in enumerate(zip(manifest['assets'],outcomes)):
            assets.append({'assetIndex':i,'assetId':asset['assetId'],'countryHints':asset.get('countryHints',[]),'sourceKey':asset.get('sourceKey'),'recordedDisposition':asset.get('disposition'),'holds':asset.get('holds',[]),'sourceStageHolds':asset.get('sourceStageHolds',[]),'outcome':outcome,'change':changes.get(i)})
        for index,state in retained_observations.items():
            original=manifest['assets'][index]['retainedOriginal'];verified=state=='completed-verified'
            assets[index]['retainedVerification']={'state':state,'integrityVerified':verified,'originalSHA256':original['sha256'] if verified else None,'originalBytes':original['bytes'] if verified else None,'networkRequests':0,'sourceIdentityInferred':False,'parserReadinessInferred':False}
        matrix=report['cellStageCounts'];overrides=dict(matrix['overrides']);cells=[]
        for i,cell in enumerate(manifest['cells']):
            cells.append({'cellIndex':i,'country':cell['country'],'type':cell['type'],'canonicalStatus':cell['retainedStatus'],'countryTypeComplete':False,'stageCounts':dict(zip(g.STATES,overrides.get(i,matrix['default'])))})
        states={i:group['state'] for group in report['statOutcomeGroups'] for low,high in group['pathRanges'] for i in range(low,high+1)}
        paths=[{'statIndex':i,'path':row['path'],'assetIds':row['assetIds'],'recordedIdentities':row.get('recordedIdentities',[]),'observation':states[i]} for i,row in enumerate(manifest.get('statTargets',[]))]
        files+=chunks('assets',assets)+chunks('country-types',cells)+chunks('custody-paths',paths)
        counts={'assets':len(assets),'countryTypeCells':len(cells),'statPaths':len(paths)}
    require(len(files)<=MAX_FILES and sum(len(b) for _,b in files)<=MAX_TOTAL,'manual-publication-size-limit')
    files=[(prefix+'/'+name,raw) for name,raw in files]
    receipt={'schemaVersion':'offmenu-owner-manual-global-receipt/1','executionContext':'owner-manual-foo','handoffId':HANDOFF,'baseReviewedSource':BASE_SOURCE,'runtimeConfigSHA256':envelope['handover']['runtimeConfigSHA256'],'dispatchHoldSHA256':HOLD_SHA256,'resultSHA256':digest,'globalReportSHA256':envelope['globalReportSHA256'],'sourceOutcome':report['status'],'expandedCounts':counts,'fileCount':len(files),'totalMetadataBytes':sum(len(b) for _,b in files),'files':[{'path':p,'bytes':len(b),'sha256':sha(b),'gitBlobSha':blob_sha(b)} for p,b in files],'rawSourceBodiesPublished':False,'checkpointBodiesPublished':False,'runnerResumeRequiresOutcomeImport':True,'isActionsReceipt':False}
    if 'executionStage' in report:receipt['executionStage']=report['executionStage']
    raw=canonical(receipt);require(len(raw)<=64*1024,'manual-receipt-size-limit')
    return receipt,files,raw

def github_api(g):
    path=Path(g.__file__).resolve().parent/'foo-owner-handover.py'
    raw=path.read_bytes();require(sha(raw)==HELPER_SHA256,'github-helper-pin-mismatch')
    spec=importlib.util.spec_from_file_location('offmenu_manual_gh',path);module=importlib.util.module_from_spec(spec);exec(compile(raw,str(path),'exec'),module.__dict__)
    class BoundedGitHub(module.GitHub):
        deadline=None
        def call(self,method,path,payload=None,absent=False):
            require(path=='user' or path=='repos/'+REPOSITORY or path.startswith('repos/'+REPOSITORY+'/'),'github-target-rejected')
            remaining=25 if self.deadline is None else min(25,self.deadline-time.monotonic())
            require(remaining>0,'manual-publication-budget-exhausted')
            command=[self.gh,'api','--hostname','github.com','--method',method,path]
            if payload is not None:command+=['--input','-']
            env=os.environ.copy();env.update(GH_PROMPT_DISABLED='1',GIT_TERMINAL_PROMPT='0',GH_PAGER='cat')
            try:
                code,stdout,_=module.bounded_process(command,None if payload is None else canonical(payload),env,timeout=remaining)
                value=module._json(stdout)
            except Exception:raise PublicationError('github-read-failed' if method=='GET' else 'github-mutation-outcome-uncertain') from None
            if code:
                if method=='GET' and absent and isinstance(value,dict) and str(value.get('status'))=='404':return None
                raise PublicationError('github-read-failed' if method=='GET' else 'github-mutation-outcome-uncertain')
            return value
    return BoundedGitHub()

class BudgetAPI:
    def __init__(self,api):self.api=api;self.calls=0;self.end=time.monotonic()+MAX_SECONDS;self.mutated=False;self.api.deadline=self.end
    def call(self,method,path,payload=None,absent=False):
        require(self.calls<MAX_CALLS and time.monotonic()<self.end,'manual-publication-budget-exhausted');self.calls+=1
        if method!='GET':self.mutated=True
        try:
            value=self.api.call(method,path,payload,absent=absent)
            require(isinstance(value,dict) or (value is None and method=='GET' and absent),'github-response-invalid')
            return value
        except PublicationError:raise
        except Exception:raise PublicationError('github-read-failed' if method=='GET' else 'github-mutation-outcome-uncertain') from None

def identity(api):
    user=api.call('GET','user');repo=api.call('GET','repos/'+REPOSITORY)
    require(user.get('id')==OWNER_ID and repo.get('id')==REPOSITORY_ID and repo.get('full_name')==REPOSITORY and repo.get('private') is True and repo.get('owner',{}).get('id')==OWNER_ID and repo.get('permissions',{}).get('push') is True,'github-private-owner-repository-verification-failed')

def head(api):
    ref=api.call('GET','repos/'+REPOSITORY+'/git/ref/heads/'+BRANCH)
    value=ref.get('object',{}).get('sha');require(isinstance(value,str) and GIT_RE.fullmatch(value),'github-head-invalid');return value

def contents(api,path,commit):
    return api.call('GET','repos/'+REPOSITORY+'/contents/'+path+'?ref='+commit,absent=True)

def same_file(item,raw):
    if not isinstance(item,dict) or item.get('type')!='file' or item.get('size')!=len(raw) or item.get('sha')!=blob_sha(raw):return False
    if item.get('encoding')!='base64':return False
    try:actual=base64.b64decode(item.get('content','').replace('\n',''),validate=True)
    except (ValueError,TypeError):return False
    return actual==raw

def receipt_path(receipt):
    return DEST+'/results/'+receipt['resultSHA256']+'/receipt.json'

def existing(api,commit,receipt_raw,files):
    item=contents(api,receipt_path(json.loads(receipt_raw)),commit)
    if item is None:return False
    require(same_file(item,receipt_raw),'manual-handoff-receipt-conflict')
    for path,raw in files:require(same_file(contents(api,path,commit),raw),'manual-publication-readback-unverified')
    return True

def outcome(status,receipt,raw,commit=None,error=None):
    return {'schemaVersion':'offmenu-owner-manual-publication/1','status':status,'errorCode':error,'executionContext':'owner-manual-foo','handoffId':HANDOFF,'repository':REPOSITORY,'branch':BRANCH,'commit':commit,'receiptPath':receipt_path(receipt),'receiptSHA256':sha(raw),'resultSHA256':receipt['resultSHA256'],'verified':status in {'published-and-verified','verified-existing','verified-after-uncertain-write'},'url':None if commit is None else 'https://github.com/'+REPOSITORY+'/blob/'+commit+'/'+receipt_path(receipt),'runnerResumeRequiresOutcomeImport':True}

def publish_result(envelope,global_module,api=None):
    """No collector call; repeated calls reconcile identical immutable metadata first."""
    receipt,files,raw=build_payload(envelope,global_module)
    try:api=BudgetAPI(api if api is not None else github_api(global_module))
    except Exception:return outcome('publication-blocked',receipt,raw,error='github-client-unavailable')
    try:
        identity(api);parent=head(api)
        compared=api.call('GET','repos/'+REPOSITORY+'/compare/'+ANCHOR+'...'+parent)
        require(compared.get('status') in {'ahead','identical'},'manual-publication-branch-unrelated')
        if existing(api,parent,raw,files):return outcome('verified-existing',receipt,raw,parent)
        commit=api.call('GET','repos/'+REPOSITORY+'/git/commits/'+parent)
        tree=commit.get('tree',{}).get('sha');require(commit.get('sha')==parent and isinstance(tree,str) and GIT_RE.fullmatch(tree),'github-parent-invalid')
        entries=[]
        for path,payload in files+[(receipt_path(receipt),raw)]:
            obj=api.call('POST','repos/'+REPOSITORY+'/git/blobs',{'encoding':'utf-8','content':payload.decode()})
            require(obj.get('sha')==blob_sha(payload),'github-blob-unverified');entries.append({'path':path,'mode':'100644','type':'blob','sha':obj['sha']})
        result=api.call('POST','repos/'+REPOSITORY+'/git/trees',{'base_tree':tree,'tree':entries});new_tree=result.get('sha');require(isinstance(new_tree,str) and GIT_RE.fullmatch(new_tree),'github-tree-unverified')
        result=api.call('POST','repos/'+REPOSITORY+'/git/commits',{'message':'Retain sanitized manual global outcome [skip ci]','tree':new_tree,'parents':[parent]});new=result.get('sha');require(isinstance(new,str) and GIT_RE.fullmatch(new),'github-commit-unverified')
        require(head(api)==parent,'manual-publication-lease-changed')
        # Single parent plus force=false rejects concurrent sibling updates.
        api.call('PATCH','repos/'+REPOSITORY+'/git/refs/heads/'+BRANCH,{'sha':new,'force':False})
        current=head(api)
        require(existing(api,current,raw,files),'manual-publication-readback-unverified')
        return outcome('published-and-verified',receipt,raw,current)
    except PublicationError as error:
        # An uncertain mutation is reconciled by read-only lookup, never repeated.
        if api.mutated:
            try:
                current=head(api)
                if existing(api,current,raw,files):return outcome('verified-after-uncertain-write',receipt,raw,current)
            except PublicationError:pass
        return outcome('publication-unverified' if api.mutated else 'publication-blocked',receipt,raw,error=str(error))


def verify_active_handover(g,api=None):
    """Read-only check of the current source-bound overlap hold before owner GETs."""
    api=BudgetAPI(api if api is not None else github_api(g));api.end=min(api.end,time.monotonic()+60);api.api.deadline=api.end;identity(api)
    branch='integration/runner-cutover-disposition-20261018'
    path=HANDOFF_PATH
    ref=api.call('GET','repos/'+REPOSITORY+'/git/ref/heads/'+branch)
    commit=ref.get('object',{}).get('sha');require(isinstance(commit,str) and GIT_RE.fullmatch(commit),'manual-handoff-current-head-invalid')
    item=contents(api,path,commit)
    require(isinstance(item,dict) and item.get('type')=='file' and item.get('sha')==HOLD_BLOB and item.get('size')==HOLD_BYTES and item.get('encoding')=='base64','manual-handoff-no-longer-active')
    try:raw=base64.b64decode(item.get('content','').replace('\n',''),validate=True);value=json.loads(raw)
    except (ValueError,TypeError):raise PublicationError('manual-handoff-no-longer-active') from None
    require(len(raw)==HOLD_BYTES and blob_sha(raw)==item['sha'] and sha(raw)==HOLD_SHA256,'manual-handoff-no-longer-active')
    require(value['handoffId']==HANDOFF and value['overlapHold']['active'] is True and value['overlapHold']['automaticRunnerSubmissionPermitted'] is False and value['source']['trustedCommit']==BASE_SOURCE,'manual-handoff-no-longer-active')
    expected={x['sourceKey']:sha(g.a.canonical(x)) for x in g.selection_config()['sources']}
    actual={x['sourceKey']:x['sourceContractSHA256'] for x in value['selectedSources']}
    require(actual==expected,'manual-handoff-contract-mismatch')
    return {'status':'active-verified','commit':commit,'checkpointPath':path,'checkpointSHA256':HOLD_SHA256,'handoffId':HANDOFF}
