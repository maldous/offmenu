#!/usr/bin/env python3
"""Bounded new-media successor to private-original saving; never selected by default.

Shares existing claim, writer lease, capacity, provenance and failure retention
primitives. New sources use exact pinned contracts and distinct original suffixes.
"""
from __future__ import annotations
import hashlib,http.client,importlib.util,os,re,stat,time,tempfile
from contextlib import nullcontext
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
from offmenu.refresh.core import fsync_directory
from offmenu.refresh import known_asset_intake as intake
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('media_original_legacy_primitives',ROOT/'scripts/save-private-original.py')
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
ERRORS=legacy.ERRORS|intake.ERROR_CODES
private_directory=legacy.private_directory
write_private_intent=legacy.write_private_intent
policy_facts=legacy.policy_facts
diagnostic_module=legacy.diagnostic_module

def run_selected(source,*,adapter=None,mode,transport=None,deadline=None,batch_meter=None,coordinator=None,owner_runtime=None):
 a=adapter;intake.validate_source(source);contract=a.source_contract(source);fingerprint=contract['fingerprint'];maximum=contract['maxBytes'];seconds=contract['seconds']
 deadline=min(deadline if deadline is not None else float('inf'),time.monotonic()+seconds)
 prior=next((p for p in mode['predecessors'] if p['sourceKey']==source['sourceKey']),None);diagnostic_sha=(mode['diagnosticReportPin'] or {}).get('sha256');meter={'requests':0,'bodyBytesRead':0}
 report={'schemaVersion':'offmenu-private-media-original-save-detail/1','sourceKey':source['sourceKey'],'selectionSHA256':fingerprint,
  'status':'blocked','errorCode':None,'cacheStatus':None,'validation':None,'network':meter,'responseMetadata':None,'responsePolicy':None,
  'originalDisposition':None,'privateSaveState':'none','localBodyBytes':0,'predecessor':prior,'diagnosticReportSHA256':diagnostic_sha,
  'minimumOriginalDedupSeconds':a.TTL,'httpResponseCacheEnabled':False,'priorGETCauseEstablished':False,
  'receiptPersistence':'pending','downstreamHolds':source['downstreamHolds'],**a.SAFETY}
 response=None;reservation_fd=reservation_identity=None;claimed=False;folder=None;intent=None;partial_created=False;original_created=False
 try:
  root=a.owned_directory(a.OUTPUT);work=a.owned_directory(root/'collection')
  with (coordinator.source_session(work) if coordinator is not None else a.writer_lock(work/'fixed-selection.lock')):
   originals=private_directory(work/'private-originals',a);folder=private_directory(originals/fingerprint,a)
   original=folder/intake.original_filename(source);partial=folder/'original.partial';provenance=folder/'provenance.json';intent=folder/'successor-intent.json';reservation=folder/'reservation.bin'
   old_claim=work/'intents'/(a.sha(source['url'].encode())+'.json')
   if owner_runtime is not None:
    report['claimCoverage']=owner_runtime.admit(work,source,intent,old_claim,prior,deadline)
   else:report['claimCoverage']=a.inspect_runner_metadata((a.LEGACY_CACHE,work),source,intent,old_claim,deadline)
   if prior is not None and owner_runtime is None:
    a.read_metadata(old_claim,expected_sha256=prior['intentSHA256'])
    state=diagnostic_module().local_state(work,source,prior)
    if state['intentSHA256']!=prior['intentSHA256'] or any(state[key]['state']!='absent' for key in ('currentMetadata','recoveryMetadata','partialBody','sourceReservation')):raise a.RefreshError('predecessor-evidence-mismatch')
   elif prior is None:
    if source['sourceKey'] not in mode.get('freshSources',[]):raise a.RefreshError('private-save-contract-invalid')
    cached=work/'source-cache/requests'/a.sha(a.canonical(a.source_spec(source).identity()))
    if old_claim.exists() or any((cached/name).exists() for name in ('current.json','recovery.json','body.partial')) or (work/('reservation-'+a.sha(source['url'].encode())+'.bin')).exists():raise a.RefreshError('source-claim-uncertain')
   base={'schemaVersion':'offmenu-private-original-successor/1','sourceKey':source['sourceKey'],'url':source['url'],'sourceContractSHA256':fingerprint,'predecessor':prior,'diagnosticReportSHA256':diagnostic_sha,'owner':0 if owner_runtime is None else owner_runtime.uid}
   if owner_runtime is not None:base['ownerHandover']=owner_runtime.provenance()
   if intent.exists():
    existing,_=a.read_metadata(intent)
    if existing.get('state')!='verified' or any(existing.get(k)!=v for k,v in base.items()):raise a.RefreshError('private-save-intent-uncertain')
    if partial.exists() or reservation.exists():raise a.RefreshError('private-original-conflict')
    saved,_=a.read_metadata(provenance,expected_sha256=existing.get('provenanceSHA256'))
    if any(saved.get(k)!=v for k,v in base.items()) or saved.get('sha256')!=existing.get('sha256') or saved.get('bytes')!=existing.get('bytes'):raise a.RefreshError('private-original-conflict')
    if original.stat().st_mode&0o077:raise a.RefreshError('private-custody-permissions-invalid')
    result=SimpleNamespace(path=original,sha256=saved['sha256'],bytes=saved['bytes'],provenance={'originalAcquiredAt':saved['originalAcquiredAt']})
    report['validation']=intake.validate_original(result,source,deadline,a);report.update(status='verified-private-original',originalDisposition='retained-original-no-network',privateSaveState='saved-original',localBodyBytes=saved['bytes'])
   else:
    if any(p.exists() for p in (original,partial,provenance,reservation)):raise a.RefreshError('private-original-conflict')
    fd=os.open(a.safe_path(intent),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(a.canonical({**base,'state':'saving'}));stream.flush();os.fsync(stream.fileno())
    fsync_directory(folder);claimed=True
    reservation_fd,reservation_identity=(coordinator.reserve(source['sourceKey'],reservation,folder,deadline,contract['expectedBytes'] or maximum,maximum) if coordinator is not None else a.reserve(reservation,folder,deadline,expected_bytes=contract['expectedBytes'] or maximum,max_bytes=maximum))
    a.deadline_check(deadline)
    if coordinator is not None:coordinator.transfer_start()
    response=intake.fetch_response(source,transport,deadline,meter,batch_meter,a)
    report['responseMetadata']=a.response_metadata(response.status,response.headers,request_url=source['url']);report['responsePolicy']=policy_facts(response.headers)
    if response.status!=200:raise a.RefreshError('source-response-not-permitted')
    headers=intake.checked_headers(response.headers,source);framed_length=int(headers['content-length']) if 'content-length' in headers else None
    digest=hashlib.sha256();fd=os.open(a.safe_path(partial),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    partial_created=True;fsync_directory(folder)
    with os.fdopen(fd,'wb') as stream:
     while True:
      a.deadline_check(deadline);remaining=maximum-meter['bodyBytesRead']
      if batch_meter is not None:remaining=min(remaining,batch_meter.remaining_bytes() if hasattr(batch_meter,'remaining_bytes') else batch_meter['maximumBytes']-batch_meter['bodyBytesRead'])
      if remaining<=0:
       framed=getattr(response,'response',None)
       if framed_length==meter['bodyBytesRead'] and (framed is None or (getattr(framed,'length',None)==0 and not getattr(framed,'chunked',True))):break
       raise a.RefreshError('network-byte-limit')
      block=response.read(min(65536,remaining));meter['bodyBytesRead']+=len(block)
      if batch_meter is not None:
       if hasattr(batch_meter,'record_bytes'):batch_meter.record_bytes(len(block))
       else:batch_meter['bodyBytesRead']+=len(block)
      if not block:break
      if a.capacity(folder)<a.GUARD+len(block):raise a.RefreshError('capacity-planning-bound-not-protected')
      if coordinator is not None:coordinator.write(source['sourceKey'],stream,block,folder)
      else:stream.write(block)
      digest.update(block);report.update(privateSaveState='partial-retained',localBodyBytes=meter['bodyBytesRead']);a.deadline_check(deadline)
     stream.flush();os.fsync(stream.fileno())
    if framed_length is not None and meter['bodyBytesRead']!=framed_length:raise a.RefreshError('source-length-mismatch')
    acquired=datetime.now(timezone.utc).isoformat();result=SimpleNamespace(path=partial,sha256=digest.hexdigest(),bytes=meter['bodyBytesRead'],provenance={'originalAcquiredAt':acquired})
    validation=intake.validate_original(result,source,deadline,a);a.deadline_check(deadline)
    os.link(a.safe_path(partial),a.safe_path(original));original_created=True;partial.unlink();fsync_directory(folder);report.update(privateSaveState='uncommitted-original',localBodyBytes=result.bytes)
    saved={**base,'sha256':result.sha256,'bytes':result.bytes,'originalAcquiredAt':acquired,'rightsReference':source['rightsReference'],'release':source['release'],
     'minimumOriginalDedupSeconds':a.TTL,'httpResponseCacheEnabled':False,'responsePolicy':report['responsePolicy'],'downstreamHolds':source['downstreamHolds'],
     'intakeContractSHA256':a.sha(a.canonical(source['mediaIntake'])),'sourceRevisionUnproven':True,'attributionReference':source['mediaIntake']['attributionReference'],
     'responseValidatorSHA256':{k:a.sha(headers[k].encode()) for k in ('etag','last-modified') if k in headers}}
    a.write_immutable(provenance,saved);fsync_directory(folder)
    with (coordinator.intent_write() if coordinator is not None else nullcontext()):write_private_intent(intent,{**base,'state':'verified','sha256':result.sha256,'bytes':result.bytes,'provenanceSHA256':a.sha(a.canonical(saved))},a)
    report.update(status='verified-private-original',validation=validation,originalDisposition='saved-original',privateSaveState='saved-original')
 except (a.RefreshError,OSError,ValueError,TypeError,KeyError,http.client.HTTPException) as error:
  code=str(error) if isinstance(error,a.RefreshError) and str(error) in a.ERRORS|ERRORS|intake.ERROR_CODES else 'local-io-failure' if isinstance(error,OSError) else 'collector-rejected'
  report.update(status='failed' if meter['requests'] else 'blocked',errorCode=code,validation=None,originalDisposition=None)
  for candidate,owned,label in ((partial if folder else None,partial_created,'partial-retained'),(original if folder else None,original_created,'uncommitted-original')):
   if owned:
    try:
     info=a.safe_path(candidate).stat()
     if stat.S_ISREG(info.st_mode):report.update(privateSaveState=label,localBodyBytes=info.st_size)
    except FileNotFoundError:pass
    except (OSError,a.RefreshError):pass
  if claimed:
   try:
    with (coordinator.intent_write() if coordinator is not None else nullcontext()):write_private_intent(intent,{**base,'state':'failed-no-retry','errorCode':code,'network':dict(meter),'privateSaveState':report['privateSaveState'],'localBodyBytes':report['localBodyBytes']},a)
   except (a.RefreshError,OSError,ValueError,TypeError,KeyError):report['errorCode']='claim-state-write-failed'
 finally:
  try:
   if response is not None:response.close()
  except (OSError,http.client.HTTPException):report.update(status='failed',errorCode='local-io-failure',validation=None,originalDisposition=None)
  if reservation_fd is not None:
   try:
    if coordinator is not None:coordinator.release(source['sourceKey'],reservation,reservation_fd,reservation_identity)
    else:a.release_own_reservation(reservation,reservation_fd,reservation_identity)
   except (a.RefreshError,OSError,ValueError,TypeError,KeyError):report.update(status='failed' if meter['requests'] else 'blocked',errorCode='reservation-release-failed',validation=None,originalDisposition=None)
 try:
  report['receiptPersistence']='written';work=a.owned_directory(a.owned_directory(a.OUTPUT)/'collection')
  a.write_immutable(work/('private-original-result-'+a.sha(a.canonical(report))+'.json'),report)
 except (a.RefreshError,OSError,ValueError,TypeError,KeyError):report.update(status='failed' if meter['requests'] else 'blocked',errorCode='result-write-failed',validation=None,originalDisposition=None,receiptPersistence='failed')
 return report
