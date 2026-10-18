#!/usr/bin/env python3
"""Fixed owner-directed original saving. No HTTP cache or response reuse."""
from __future__ import annotations
import hashlib,http.client,importlib.util,os,re,stat,time,tempfile
from offmenu.refresh.core import fsync_directory
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
ERRORS={'private-save-contract-invalid','predecessor-evidence-mismatch','private-original-conflict','private-custody-permissions-invalid','private-save-intent-uncertain','invalid-response-headers'}
IGNORED_NON_RENDERED={'set-cookie','server-timing','content-security-policy','content-security-policy-report-only'}
POLICY_KEYS={'cacheControlPrivate','cacheControlNoStore','cacheControlNoCache','vary','contentEncoding','setCookieFields','nonRenderedCSPFields','httpResponseCached','httpCacheReuse'}

def diagnostic_module():
 spec=importlib.util.spec_from_file_location('private_save_predecessor',ROOT/'scripts/diagnose-fixed-batch.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def policy_facts(raw):
 pairs=list(raw.items()) if isinstance(raw,dict) else raw
 groups={}
 for key,value in pairs:
  if isinstance(key,str) and isinstance(value,str):groups.setdefault(key.lower(),[]).append(value)
 directives={v.strip().split('=',1)[0].lower() for value in groups.get('cache-control',[]) for v in value.split(',')}
 vary=groups.get('vary',[]);encoding=groups.get('content-encoding',[])
 return {'cacheControlPrivate':'private' in directives,'cacheControlNoStore':'no-store' in directives,'cacheControlNoCache':'no-cache' in directives,
  'vary':'absent' if not vary or vary==[''] else 'accept-encoding' if len(vary)==1 and vary[0].strip().lower()=='accept-encoding' else 'unsupported',
  'contentEncoding':'identity' if not encoding or (len(encoding)==1 and encoding[0].lower()=='identity') else 'unsupported',
  'setCookieFields':len(groups.get('set-cookie',[])),
  'nonRenderedCSPFields':len(groups.get('content-security-policy',[]))+len(groups.get('content-security-policy-report-only',[])),
  'httpResponseCached':False,'httpCacheReuse':False}

def validate_policy(value):
 if value is None:return
 if not isinstance(value,dict) or set(value)!=POLICY_KEYS:raise ValueError('invalid-private-save-policy')
 for key in ('cacheControlPrivate','cacheControlNoStore','cacheControlNoCache'):
  if type(value[key]) is not bool:raise ValueError('invalid-private-save-policy')
 for key in ('httpResponseCached','httpCacheReuse'):
  if value[key] is not False:raise ValueError('invalid-private-save-policy')
 for key in ('setCookieFields','nonRenderedCSPFields'):
  if type(value[key]) is not int or not 0<=value[key]<=100:raise ValueError('invalid-private-save-policy')
 if value['vary'] not in {'absent','accept-encoding','unsupported'} or value['contentEncoding'] not in {'identity','unsupported'}:raise ValueError('invalid-private-save-policy')

def download_headers(raw,source,a):
 if not isinstance(raw,(list,dict)):raise a.RefreshError('invalid-response-headers')
 filtered=[]
 for key,value in (raw.items() if isinstance(raw,dict) else raw):
  single=a._headers([(key,value)]);name=next(iter(single))
  if name not in IGNORED_NON_RENDERED:filtered.append((name,value))
 headers=a._headers(filtered)
 if headers.get('vary','').strip().lower() not in ('','accept-encoding'):raise a.RefreshError('unsupported-response-vary')
 if headers.get('content-encoding','identity').lower()!='identity':raise a.RefreshError('unsupported-response-encoding')
 expected=source['expectedResponse']
 if {key:headers.get(key) for key in expected}!=expected:raise a.RefreshError('source-response-contract-changed')
 length=headers.get('content-length');transfer=headers.get('transfer-encoding')
 if (length is not None and (not length.isdigit() or not 1<=int(length)<=source['hardTransferBytes'])) or (transfer is not None and (length is not None or transfer.lower()!='chunked' or source['expectedBytes'] is not None)):
  raise a.RefreshError('source-response-contract-changed')
 return headers

def private_directory(path,a):
 path=a.safe_path(path)
 try:path.mkdir(mode=0o700)
 except FileExistsError:pass
 info=path.stat()
 if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077:raise a.RefreshError('private-custody-permissions-invalid')
 fsync_directory(path);fsync_directory(path.parent)
 return path

def write_private_intent(path,value,a):
 path=a.safe_path(path)
 with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.private-intent-',delete=False) as stream:
  temporary=Path(stream.name)
  try:
   stream.write(a.canonical(value));stream.flush();os.fsync(stream.fileno())
   os.replace(temporary,path);fsync_directory(path.parent)
  finally:temporary.unlink(missing_ok=True)

def validate_mode(mode,selected,a):
 expected={'mode','diagnosticReportPin','minimumOriginalDedupSeconds','httpResponseCacheEnabled','preserveFailedIntents','predecessors'}
 if (not isinstance(mode,dict) or set(mode)!=expected or mode['mode']!='owner-directed-private-original-save/1'
     or mode['minimumOriginalDedupSeconds']!=a.TTL or mode['httpResponseCacheEnabled'] is not False or mode['preserveFailedIntents'] is not True):raise a.RefreshError('private-save-contract-invalid')
 pin=mode['diagnosticReportPin']
 if not isinstance(pin,dict) or set(pin)!={'path','sha256'} or pin['path']!='docs/collection-selections/recipe-five-recovery-observation.json' or not re.fullmatch('[a-f0-9]{64}',pin['sha256']):raise a.RefreshError('private-save-contract-invalid')
 observed=a.strict_json(a.preparation_module().pinned_bytes(ROOT,(pin['path'],pin['sha256'])))['steps'][-1]['evidence']['batchRecoveryDiagnostic']
 if observed['status']!='complete' or observed['priorGETCauseEstablished'] is not False or observed['networkBodyBytesRead']!=0:raise a.RefreshError('private-save-contract-invalid')
 if len(selected['sources'])!=5 or len(mode['predecessors'])!=5:raise a.RefreshError('private-save-contract-invalid')
 for source,prior,item in zip(selected['sources'],mode['predecessors'],observed['items']):
  if (set(prior)!={'sourceKey','sourceContractSHA256','detailSHA256','intentSHA256'} or prior['sourceKey']!=source['sourceKey'] or prior['sourceContractSHA256']!=a.sha(a.canonical(source))
      or item['sourceKey']!=source['sourceKey'] or item['priorDetailSHA256']!=prior['detailSHA256'] or item['localState']['intentSHA256']!=prior['intentSHA256']
      or item['localState']['detailSHA256Verified'] is not True or item['localState']['intentState']!='failed-no-retry'
      or any(item['localState'][key]['state']!='absent' for key in ('currentMetadata','recoveryMetadata','partialBody','sourceReservation'))
      or item['responseMetadata']['httpStatus']!=200):raise a.RefreshError('private-save-contract-invalid')
 return mode

def run_selected(source,*,adapter=None,mode,transport=None,deadline=None,batch_meter=None):
 a=adapter;contract=a.source_contract(source);fingerprint=contract['fingerprint'];maximum=contract['maxBytes'];seconds=contract['seconds']
 deadline=min(deadline if deadline is not None else float('inf'),time.monotonic()+seconds)
 prior=next(p for p in mode['predecessors'] if p['sourceKey']==source['sourceKey']);meter={'requests':0,'bodyBytesRead':0}
 report={'schemaVersion':'offmenu-private-original-save-detail/1','sourceKey':source['sourceKey'],'selectionSHA256':fingerprint,
  'status':'blocked','errorCode':None,'cacheStatus':None,'validation':None,'network':meter,'responseMetadata':None,'responsePolicy':None,
  'originalDisposition':None,'privateSaveState':'none','localBodyBytes':0,'predecessor':prior,'diagnosticReportSHA256':mode['diagnosticReportPin']['sha256'],
  'minimumOriginalDedupSeconds':a.TTL,'httpResponseCacheEnabled':False,'priorGETCauseEstablished':False,
  'receiptPersistence':'pending','downstreamHolds':source['downstreamHolds'],**a.SAFETY}
 response=None;reservation_fd=reservation_identity=None;claimed=False;folder=None;intent=None;partial_created=False;original_created=False
 try:
  root=a.owned_directory(a.OUTPUT);work=a.owned_directory(root/'collection')
  with a.writer_lock(work/'fixed-selection.lock'):
   originals=private_directory(work/'private-originals',a);folder=private_directory(originals/fingerprint,a)
   original=folder/'original.pdf';partial=folder/'original.partial';provenance=folder/'provenance.json';intent=folder/'successor-intent.json';reservation=folder/'reservation.bin'
   old_claim=work/'intents'/(a.sha(source['url'].encode())+'.json')
   report['claimCoverage']=a.inspect_runner_metadata((a.LEGACY_CACHE,work),source,intent,old_claim,deadline)
   a.read_metadata(old_claim,expected_sha256=prior['intentSHA256'])
   state=diagnostic_module().local_state(work,source,prior)
   if state['intentSHA256']!=prior['intentSHA256'] or any(state[key]['state']!='absent' for key in ('currentMetadata','recoveryMetadata','partialBody','sourceReservation')):raise a.RefreshError('predecessor-evidence-mismatch')
   base={'schemaVersion':'offmenu-private-original-successor/1','sourceKey':source['sourceKey'],'url':source['url'],'sourceContractSHA256':fingerprint,'predecessor':prior,'diagnosticReportSHA256':mode['diagnosticReportPin']['sha256'],'owner':0}
   if intent.exists():
    existing,_=a.read_metadata(intent)
    if existing.get('state')!='verified' or any(existing.get(k)!=v for k,v in base.items()):raise a.RefreshError('private-save-intent-uncertain')
    if partial.exists() or reservation.exists():raise a.RefreshError('private-original-conflict')
    saved,_=a.read_metadata(provenance,expected_sha256=existing.get('provenanceSHA256'))
    if any(saved.get(k)!=v for k,v in base.items()) or saved.get('sha256')!=existing.get('sha256') or saved.get('bytes')!=existing.get('bytes'):raise a.RefreshError('private-original-conflict')
    if original.stat().st_mode&0o077:raise a.RefreshError('private-custody-permissions-invalid')
    result=SimpleNamespace(path=original,sha256=saved['sha256'],bytes=saved['bytes'],provenance={'originalAcquiredAt':saved['originalAcquiredAt']})
    report['validation']=a.validate_original(result,source,deadline);report.update(status='verified-private-original',originalDisposition='retained-original-no-network',privateSaveState='saved-original',localBodyBytes=saved['bytes'])
   else:
    if any(p.exists() for p in (original,partial,provenance,reservation)):raise a.RefreshError('private-original-conflict')
    fd=os.open(a.safe_path(intent),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(a.canonical({**base,'state':'saving'}));stream.flush();os.fsync(stream.fileno())
    fsync_directory(folder);claimed=True
    reservation_fd,reservation_identity=a.reserve(reservation,folder,deadline,expected_bytes=contract['expectedBytes'] or maximum,max_bytes=maximum)
    if batch_meter is not None and (batch_meter['requests']>=batch_meter['maximumRequests'] or batch_meter['bodyBytesRead']>=batch_meter['maximumBytes']):raise a.RefreshError('network-request-limit')
    a.deadline_check(deadline);spec=a.source_spec(source);spec.validate();meter['requests']=1
    if batch_meter is not None:batch_meter['requests']+=1
    response=transport(spec,{'Accept-Encoding':'identity'},deadline=deadline) if transport is not None else a.HTTPSFileTransport()(spec,{'Accept-Encoding':'identity'},deadline=deadline)
    report['responseMetadata']=a.response_metadata(response.status,response.headers,request_url=source['url']);report['responsePolicy']=policy_facts(response.headers)
    if response.status!=200:raise a.RefreshError('source-response-not-permitted')
    headers=download_headers(response.headers,source,a);framed_length=int(headers['content-length']) if 'content-length' in headers else None
    digest=hashlib.sha256();fd=os.open(a.safe_path(partial),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    partial_created=True;fsync_directory(folder)
    with os.fdopen(fd,'wb') as stream:
     while True:
      a.deadline_check(deadline);remaining=maximum-meter['bodyBytesRead']
      if batch_meter is not None:remaining=min(remaining,batch_meter['maximumBytes']-batch_meter['bodyBytesRead'])
      if remaining<=0:
       framed=getattr(response,'response',None)
       if framed_length==meter['bodyBytesRead'] and (framed is None or (getattr(framed,'length',None)==0 and not getattr(framed,'chunked',True))):break
       raise a.RefreshError('network-byte-limit')
      block=response.read(min(65536,remaining));meter['bodyBytesRead']+=len(block)
      if batch_meter is not None:batch_meter['bodyBytesRead']+=len(block)
      if not block:break
      if a.capacity(folder)<a.GUARD+len(block):raise a.RefreshError('capacity-planning-bound-not-protected')
      stream.write(block);digest.update(block);report.update(privateSaveState='partial-retained',localBodyBytes=meter['bodyBytesRead']);a.deadline_check(deadline)
     stream.flush();os.fsync(stream.fileno())
    if framed_length is not None and meter['bodyBytesRead']!=framed_length:raise a.RefreshError('source-length-mismatch')
    acquired=datetime.now(timezone.utc).isoformat();result=SimpleNamespace(path=partial,sha256=digest.hexdigest(),bytes=meter['bodyBytesRead'],provenance={'originalAcquiredAt':acquired})
    validation=a.validate_original(result,source,deadline);a.deadline_check(deadline)
    os.link(a.safe_path(partial),a.safe_path(original));original_created=True;partial.unlink();fsync_directory(folder);report.update(privateSaveState='uncommitted-original',localBodyBytes=result.bytes)
    saved={**base,'sha256':result.sha256,'bytes':result.bytes,'originalAcquiredAt':acquired,'rightsReference':source['rightsReference'],'release':source['release'],
     'minimumOriginalDedupSeconds':a.TTL,'httpResponseCacheEnabled':False,'responsePolicy':report['responsePolicy'],'downstreamHolds':source['downstreamHolds']}
    a.write_immutable(provenance,saved);fsync_directory(folder);write_private_intent(intent,{**base,'state':'verified','sha256':result.sha256,'bytes':result.bytes,'provenanceSHA256':a.sha(a.canonical(saved))},a)
    report.update(status='verified-private-original',validation=validation,originalDisposition='saved-original',privateSaveState='saved-original')
 except (a.RefreshError,OSError,ValueError,TypeError,KeyError,http.client.HTTPException) as error:
  code=str(error) if isinstance(error,a.RefreshError) and str(error) in a.ERRORS|ERRORS else 'local-io-failure' if isinstance(error,OSError) else 'collector-rejected'
  report.update(status='failed' if meter['requests'] else 'blocked',errorCode=code,validation=None,originalDisposition=None)
  for candidate,owned,label in ((partial if folder else None,partial_created,'partial-retained'),(original if folder else None,original_created,'uncommitted-original')):
   if owned:
    try:
     info=a.safe_path(candidate).stat()
     if stat.S_ISREG(info.st_mode):report.update(privateSaveState=label,localBodyBytes=info.st_size)
    except FileNotFoundError:pass
    except (OSError,a.RefreshError):pass
  if claimed:
   try:write_private_intent(intent,{**base,'state':'failed-no-retry','errorCode':code,'network':dict(meter),'privateSaveState':report['privateSaveState'],'localBodyBytes':report['localBodyBytes']},a)
   except (a.RefreshError,OSError,ValueError,TypeError,KeyError):report['errorCode']='claim-state-write-failed'
 finally:
  try:
   if response is not None:response.close()
  except (OSError,http.client.HTTPException):report.update(status='failed',errorCode='local-io-failure',validation=None,originalDisposition=None)
  if reservation_fd is not None:
   try:a.release_own_reservation(reservation,reservation_fd,reservation_identity)
   except (a.RefreshError,OSError,ValueError,TypeError,KeyError):report.update(status='failed' if meter['requests'] else 'blocked',errorCode='reservation-release-failed',validation=None,originalDisposition=None)
 try:
  report['receiptPersistence']='written';work=a.owned_directory(a.owned_directory(a.OUTPUT)/'collection')
  a.write_immutable(work/('private-original-result-'+a.sha(a.canonical(report))+'.json'),report)
 except (a.RefreshError,OSError,ValueError,TypeError,KeyError):report.update(status='failed' if meter['requests'] else 'blocked',errorCode='result-write-failed',validation=None,originalDisposition=None,receiptPersistence='failed')
 return report
