#!/usr/bin/env python3
"""Five fixed failed-source local metadata checks and prospective zero-body HEADs."""
from __future__ import annotations
import importlib.util,json,os,re,stat,sys,time,http.client,ssl,threading
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fixed_original_adapter',ROOT/'scripts/acquire-fixed-zenodo.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
from offmenu.refresh.acquisition import _headers,_retention
SCHEMA='offmenu-fixed-batch-recovery-diagnostic/1'
PIN=('docs/collection-selections/recipe-batch-recovery-diagnostic.json','fbfb376ebc943dc9c4e1f69ad58f6400c1c7fdbbaedbf4ac9c79c453352a82ab')
KNOWN_HEADERS=frozenset('content-length content-type content-encoding transfer-encoding connection location cache-control pragma vary expires age date etag last-modified retry-after set-cookie server-timing alt-svc content-disposition content-security-policy x-frame-options strict-transport-security x-content-type-options access-control-allow-origin access-control-allow-credentials accept-ranges server via x-cache'.split())
RETENTION_FIELDS={'cache-control','vary','content-encoding'}
ERRORS={None,'diagnostic-input-invalid','prior-failure-evidence-mismatch','prior-intent-not-held','existing-source-custody-or-partial','diagnostic-already-attempted','diagnostic-request-failed','diagnostic-deadline-exceeded','diagnostic-result-write-failed'}
SAFETY={'sourceBodiesRead':False,'sourceBodiesUploaded':False,'sourceClaimsChanged':False,'originalGETRetried':False,'priorGETCauseEstablished':False,'acquisitionEnabledByDiagnostic':False,'rawHeaderValuesPublished':False,'redirectsFollowed':0,'networkBodyBytesRead':0}


def load_selection():
 prep=a.preparation_module();config=a.strict_json(prep.pinned_bytes(ROOT,PIN))
 old=a.strict_json(prep.pinned_bytes(ROOT,tuple(config['priorSelectionPin'])))
 prior=a.strict_json(prep.pinned_bytes(ROOT,tuple(config['priorReportPin'])))
 if (config['method']!='HEAD' or config['maximumHEADs']!=5 or config['maximumGETs']!=0 or config['maximumBodyBytes']!=0
     or config['perSourceSeconds']!=30 or config['wholeOperationSeconds']!=180 or config['retries']!=0 or config['redirects']!=0
     or a.sha(a.canonical(old))!=config['priorCanonicalSelectionSHA256']
     or prior['githubRunId']!=config['priorRunId'] or prior['trustedCodeSha']!=config['priorSourceSHA']):raise a.RefreshError('diagnostic-input-invalid')
 items=prior['steps'][-1]['evidence']['fixedSourceBatch']['items'];sources=[]
 for expected in config['failedSources']:
  source=next(s for s in old['sources'] if s['sourceKey']==expected['sourceKey'])
  item=next(i for i in items if i['sourceKey']==expected['sourceKey'])
  if (a.sha(a.canonical(source))!=expected['sourceContractSHA256'] or item['detailSHA256']!=expected['detailSHA256']
      or item['status']!='failed' or item['errorCode']!='collector-rejected' or item['networkRequests']!=1
      or item['networkBytesRead']!=0 or item['responseMetadata']['httpStatus']!=200):raise a.RefreshError('diagnostic-input-invalid')
  sources.append({'source':source,'prior':expected})
 if len(sources)!=5 or len({s['source']['url'] for s in sources})!=5:raise a.RefreshError('diagnostic-input-invalid')
 return config,sources


def header_facts(headers,source):
 counts={};unknown=0;unknown_names={};oversized=set();oversized_unknown=0;invalid=False
 groups={}
 for key,value in headers:
  if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9-]{1,64}',key):invalid=True;continue
  key=key.lower();groups.setdefault(key,[]).append(value)
  if key in KNOWN_HEADERS:counts[key]=counts.get(key,0)+1
  else:unknown+=1;unknown_names[key]=unknown_names.get(key,0)+1
  if not isinstance(value,str) or len(value)>8192 or '\r' in value or '\n' in value:
   if key in KNOWN_HEADERS:oversized.add(key)
   else:oversized_unknown+=1
 try:_headers(headers);core='accepted'
 except (a.RefreshError,ValueError,TypeError):core='invalid-response-headers'
 retention='unavailable';relevant={}
 if all(len(groups.get(k,[]))<=1 for k in RETENTION_FIELDS):
  try:
   relevant=_headers([(k,v[0]) for k,v in groups.items() if k in RETENTION_FIELDS]);_retention(relevant);retention='accepted'
  except a.RefreshError as error:
   if str(error) in {'response-retention-not-approved','unsupported-response-vary','unsupported-response-encoding'}:retention=str(error)
 length=groups.get('content-length',[]);encoding=groups.get('transfer-encoding',[])
 framing=('conflicting' if length and encoding else 'invalid' if len(length)>1 or len(encoding)>1 else
          'content-length' if length and isinstance(length[0],str) and length[0].isdigit() else
          'chunked' if encoding==['chunked'] else 'invalid' if length or encoding else 'unspecified')
 expected=source['expectedResponse'];matches=all(groups.get(k)==[v] for k,v in expected.items())
 return {'recognizedNameCounts':counts,'unrecognizedHeaderCount':unknown,'duplicateUnrecognizedName':any(n>1 for n in unknown_names.values()),
  'invalidHeaderNamePresent':invalid,'oversizedOrInvalidKnownValues':sorted(oversized),'oversizedOrInvalidUnknownValues':oversized_unknown,
  'coreHeaderValidation':core,'retentionCheckOnUniqueRelevantHeaders':retention,'framing':framing,'expectedResponseContractMatches':matches}


def stat_only(path):
 try:
  info=a.safe_path(path).lstat()
  return {'state':'regular' if stat.S_ISREG(info.st_mode) else 'nonregular','bytes':info.st_size if stat.S_ISREG(info.st_mode) else None}
 except FileNotFoundError:return {'state':'absent','bytes':None}
 except (OSError,a.RefreshError):return {'state':'inaccessible','bytes':None}


def local_state(work,source,prior):
 spec=a.source_spec(source);identity=a.sha(a.canonical(spec.identity()));folder=work/'source-cache/requests'/identity
 state={'detailSHA256Verified':False,'intentSHA256':None,'intentState':None,'currentMetadata':stat_only(folder/'current.json'),
        'recoveryMetadata':stat_only(folder/'recovery.json'),'partialBody':stat_only(folder/'body.partial'),'sourceReservation':stat_only(work/('reservation-'+a.sha(source['url'].encode())+'.bin')),'acceptedObject':{'state':'unreferenced','bytes':None}}
 detail,_=a.read_metadata(work/('fixed-source-result-'+prior['detailSHA256']+'.json'),expected_sha256=prior['detailSHA256'])
 if (detail.get('sourceKey')!=source['sourceKey'] or detail.get('selectionSHA256')!=prior['sourceContractSHA256']
     or detail.get('status')!='failed' or detail.get('errorCode')!='collector-rejected'
     or detail.get('network')!={'requests':1,'bodyBytesRead':0} or detail.get('responseMetadata',{}).get('httpStatus')!=200):
  raise a.RefreshError('prior-failure-evidence-mismatch')
 state['detailSHA256Verified']=True
 claim,_=a.read_metadata(work/'intents'/(a.sha(source['url'].encode())+'.json'))
 state['intentSHA256']=a.sha(a.canonical(claim));state['intentState']=claim.get('state') if claim.get('state') in {'failed-no-retry','acquiring','verified'} else 'other'
 if (claim.get('sourceKey')!=source['sourceKey'] or claim.get('url')!=source['url'] or claim.get('owner')!=0
     or claim.get('selectionSHA256')!=prior['sourceContractSHA256'] or claim.get('requestIdentitySHA256')!=identity
     or claim.get('state')!='failed-no-retry' or claim.get('errorCode')!='collector-rejected'
     or claim.get('network')!={'requests':1,'bodyBytesRead':0}):raise a.RefreshError('prior-intent-not-held')
 if state['currentMetadata']['state']=='regular':
  current,_=a.read_metadata(folder/'current.json');checksum=current.get('sha256')
  if isinstance(checksum,str) and re.fullmatch('[a-f0-9]{64}',checksum):state['acceptedObject']=stat_only(work/'source-cache/objects'/checksum)
 return state


def item_template(entry):
 return {'sourceKey':entry['source']['sourceKey'],'priorDetailSHA256':entry['prior']['detailSHA256'],'priorGETHttpStatus':200,
         'status':'blocked','errorCode':'diagnostic-input-invalid','networkRequests':0,'localState':None,'responseMetadata':None,'headerFacts':None}


def run_one(entry,deadline,*,connection_factory=None):
 item=item_template(entry);source,prior=entry['source'],entry['prior'];connection=response=watchdog=None
 try:
  work=a.owned_directory(a.owned_directory(a.OUTPUT)/'collection')
  with a.writer_lock(work/'fixed-selection.lock'):
   item['localState']=local_state(work,source,prior)
   if any(item['localState'][k]['state']!='absent' for k in ('currentMetadata','recoveryMetadata','partialBody','sourceReservation')):raise a.RefreshError('existing-source-custody-or-partial')
   marker=work/('batch-head-'+PIN[1]+'-'+a.sha(source['url'].encode())+'.intent.json')
   try:fd=os.open(a.safe_path(marker),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
   except FileExistsError:raise a.RefreshError('diagnostic-already-attempted') from None
   with os.fdopen(fd,'wb') as stream:stream.write(a.canonical({'diagnosticSHA256':PIN[1],'method':'HEAD','maximumRequests':1}));stream.flush();os.fsync(stream.fileno())
   remaining=min(30,deadline-time.monotonic())
   if remaining<=0:raise a.RefreshError('diagnostic-deadline-exceeded')
   parts=urlsplit(source['url']);factory=connection_factory or http.client.HTTPSConnection
   connection=factory(parts.hostname,443,timeout=remaining,context=ssl.create_default_context());expired=threading.Event()
   def abort():
    expired.set();sock=connection.sock
    if sock is not None:
     try:sock.shutdown(2)
     except OSError:pass
    connection.close()
   watchdog=threading.Timer(remaining,abort);watchdog.daemon=True;watchdog.start()
   item['networkRequests']=1
   connection.request('HEAD',parts.path+('?' +parts.query if parts.query else ''),headers={'Accept-Encoding':'identity'})
   response=connection.getresponse();headers=response.getheaders()
   item['responseMetadata']=a.response_metadata(response.status,headers,request_url=source['url']);item['headerFacts']=header_facts(headers,source)
   if expired.is_set() or time.monotonic()>=deadline:raise a.RefreshError('diagnostic-deadline-exceeded')
   item.update(status='observed',errorCode=None)
 except (a.RefreshError,OSError,ValueError,TypeError,KeyError,http.client.HTTPException) as error:
  code=str(error) if isinstance(error,a.RefreshError) and str(error) in ERRORS else ('diagnostic-request-failed' if item['networkRequests'] else 'diagnostic-input-invalid')
  item.update(status='failed' if item['networkRequests'] else 'blocked',errorCode=code)
 finally:
  if watchdog is not None:watchdog.cancel()
  try:
   if response is not None:response.close()
   if connection is not None:connection.close()
  except (OSError,http.client.HTTPException):item.update(status='failed',errorCode='diagnostic-request-failed')
 return item


def report_template():
 return {'schemaVersion':SCHEMA,'diagnosticSHA256':PIN[1],'method':'HEAD','status':'blocked','errorCode':'diagnostic-input-invalid',
         'observedAt':datetime.now(timezone.utc).isoformat(),'networkRequests':0,'items':[],'detailPersisted':False,**SAFETY}


def run_diagnostics(config,entries,*,connection_factory=None):
 report=report_template();deadline=time.monotonic()+180
 report['items']=[run_one(e,deadline,connection_factory=connection_factory) for e in entries]
 report['networkRequests']=sum(i['networkRequests'] for i in report['items'])
 report.update(status='complete' if all(i['status']=='observed' for i in report['items']) else 'complete-with-errors',errorCode=None)
 try:
  work=a.owned_directory(a.owned_directory(a.OUTPUT)/'collection');report['detailPersisted']=True
  a.write_immutable(work/('batch-head-result-'+a.sha(a.canonical(report))+'.json'),report)
 except (a.RefreshError,OSError,ValueError,TypeError,KeyError):report.update(status='complete-with-errors',errorCode='diagnostic-result-write-failed',detailPersisted=False)
 return report


def sanitize_report(value):
 if not isinstance(value,dict) or set(value)!=set(report_template()) or value['schemaVersion']!=SCHEMA or value['diagnosticSHA256']!=PIN[1] or value['method']!='HEAD':raise ValueError('invalid-diagnostic')
 if any(value[k] is not v if type(v) is bool else value[k]!=v for k,v in SAFETY.items()):raise ValueError('invalid-diagnostic')
 if value['errorCode'] not in ERRORS or value['status'] not in {'blocked','complete','complete-with-errors'} or type(value['detailPersisted']) is not bool:raise ValueError('invalid-diagnostic')
 if not isinstance(value['observedAt'],str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.]+\+00:00',value['observedAt']):raise ValueError('invalid-diagnostic')
 if value['status']=='blocked':
  if value['items']!=[] or value['networkRequests']!=0 or value['errorCode'] is None:raise ValueError('invalid-diagnostic')
  return dict(value)
 config,entries=load_selection()
 if not isinstance(value['items'],list) or len(value['items'])!=5:raise ValueError('invalid-diagnostic')
 for item,entry in zip(value['items'],entries):
  if not isinstance(item,dict) or set(item)!=set(item_template(entry)) or item['sourceKey']!=entry['source']['sourceKey'] or item['priorDetailSHA256']!=entry['prior']['detailSHA256'] or item['priorGETHttpStatus']!=200:raise ValueError('invalid-diagnostic')
  if item['status'] not in {'observed','blocked','failed'} or item['errorCode'] not in ERRORS or (item['status']=='observed')!=(item['errorCode'] is None) or type(item['networkRequests']) is not int or not 0<=item['networkRequests']<=1:raise ValueError('invalid-diagnostic')
  a.validate_response_metadata(item['responseMetadata'])
  if item['status']=='observed' and (item['networkRequests']!=1 or item['responseMetadata'] is None or item['headerFacts'] is None):raise ValueError('invalid-diagnostic')
  state=item['localState']
  if state is not None:
   keys={'detailSHA256Verified','intentSHA256','intentState','currentMetadata','recoveryMetadata','partialBody','sourceReservation','acceptedObject'}
   if not isinstance(state,dict) or set(state)!=keys or state['detailSHA256Verified'] is not True or state['intentState']!='failed-no-retry' or not re.fullmatch('[a-f0-9]{64}',state['intentSHA256']):raise ValueError('invalid-diagnostic')
   for key in ('currentMetadata','recoveryMetadata','partialBody','sourceReservation','acceptedObject'):
    part=state[key]
    if not isinstance(part,dict) or set(part)!={'state','bytes'} or part['state'] not in {'absent','regular','nonregular','inaccessible','unreferenced'}:raise ValueError('invalid-diagnostic')
    if (part['state']=='regular' and (type(part['bytes']) is not int or not 0<=part['bytes']<=2**63-1)) or (part['state']!='regular' and part['bytes'] is not None):raise ValueError('invalid-diagnostic')
  facts=item['headerFacts']
  if facts is not None:
   expected=set(header_facts([],entry['source']))
   if not isinstance(facts,dict) or set(facts)!=expected or not isinstance(facts['recognizedNameCounts'],dict) or not set(facts['recognizedNameCounts'])<=KNOWN_HEADERS:raise ValueError('invalid-diagnostic')
   for count in [*facts['recognizedNameCounts'].values(),facts['unrecognizedHeaderCount'],facts['oversizedOrInvalidUnknownValues']]:
    if type(count) is not int or not 0<=count<=100:raise ValueError('invalid-diagnostic')
   if not isinstance(facts['oversizedOrInvalidKnownValues'],list) or not set(facts['oversizedOrInvalidKnownValues'])<=KNOWN_HEADERS:raise ValueError('invalid-diagnostic')
   for key in ('duplicateUnrecognizedName','invalidHeaderNamePresent','expectedResponseContractMatches'):
    if type(facts[key]) is not bool:raise ValueError('invalid-diagnostic')
   if facts['coreHeaderValidation'] not in {'accepted','invalid-response-headers'} or facts['retentionCheckOnUniqueRelevantHeaders'] not in {'accepted','unavailable','response-retention-not-approved','unsupported-response-vary','unsupported-response-encoding'} or facts['framing'] not in {'conflicting','invalid','content-length','chunked','unspecified'}:raise ValueError('invalid-diagnostic')
 if type(value['networkRequests']) is not int or value['networkRequests']!=sum(i['networkRequests'] for i in value['items']):raise ValueError('invalid-diagnostic')
 if value['status']=='complete' and (value['errorCode'] is not None or any(i['status']!='observed' for i in value['items'])):raise ValueError('invalid-diagnostic')
 return dict(value)


def main(argv=None):
 report=report_template()
 try:
  if (sys.argv[1:] if argv is None else argv):raise a.RefreshError('diagnostic-input-invalid')
  config,entries=load_selection();report=run_diagnostics(config,entries)
 except (a.RefreshError,OSError,ValueError,TypeError,KeyError):pass
 report=sanitize_report(report);print(a.canonical(report).decode(),end='')
 return 0 if report['status']=='complete' else 2
if __name__=='__main__':raise SystemExit(main())
