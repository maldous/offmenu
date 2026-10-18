"""Closed, bounded private CSV/JSON/DOCX intake and metadata-only outcome joins.

No discovery, credentials, cookies, content execution, or implicit activation.
The existing PDF adapter and immutable source fingerprints are not modified.
"""
from __future__ import annotations
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from urllib.parse import urlsplit, parse_qsl
import csv, hashlib, io, json, math, os, re, stat, time, zipfile, zlib, threading
from xml.etree import ElementTree as ET
from .core import RefreshError, canonical, sha, safe_path, strict_json
from .acquisition import SourceSpec, _headers
from .bounded_media_transport import BoundedHTTPSFileTransport

SCHEMA='offmenu-private-media-intake/1'
ERROR_CODES=frozenset({'media-intake-contract-invalid','media-intake-header-invalid','media-intake-framing-invalid','media-intake-content-invalid','media-intake-record-limit','media-intake-archive-invalid','media-intake-redirect-invalid','media-intake-redirect-expired','media-intake-successor-inactive','media-intake-join-invalid'})
MiB=1024*1024
ROOT=Path(__file__).resolve().parents[2]
SUCCESSOR_PIN=('docs/collection-selections/known-intake-successor-selection.json','cbf9ca7e3b97a4d4b971b28d6d4ae329f16eb0f1743be84beecf566e0735d998')
DOCX='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
_CSV_LOCK=threading.Lock()
SIGNED_KEYS=('X-Goog-Algorithm','X-Goog-Credential','X-Goog-Date','X-Goog-Expires','X-Goog-Signature','X-Goog-SignedHeaders')

def fail(code='media-intake-contract-invalid'):raise RefreshError(code)
def is_media_source(source):return isinstance(source,dict) and 'mediaIntake' in source
def maximum_requests(source):return source['mediaIntake']['maximumRequests'] if is_media_source(source) else 1
def original_filename(source):return source['mediaIntake']['originalFilename'] if is_media_source(source) else 'original.pdf'
def source_hosts(source):
 hosts=[urlsplit(source['url']).hostname]
 if is_media_source(source) and source['mediaIntake']['redirect']:hosts.append(source['mediaIntake']['redirect']['targetHost'])
 return tuple(sorted(set(hosts)))

def read_pinned(root,pin):
 path=Path(root)/pin['path']
 if not pin['path'].startswith('docs/collection-selections/') or '..' in Path(pin['path']).parts:fail()
 raw=path.read_bytes()
 if len(raw)>32*MiB or sha(raw)!=pin['sha256']:fail()
 return strict_json(raw)

def successor_config(root=ROOT):
 value=read_pinned(root,dict(zip(('path','sha256'),SUCCESSOR_PIN)))
 if value['schemaVersion']!='offmenu-known-intake-successor-selection/1' or value['status']!='prepared-for-review-not-active':fail()
 if value['maximumAdditionalRequests']!=7 or value['maximumAdditionalTransferBytes']!=13*MiB or value['remainingUnresolvedUnits']!=54 or len(value['intakeSources'])!=5 or len(value['reuseJoins'])!=22:fail()
 for pin in value['basePins'].values():read_pinned(root,pin)
 for pin in value['evidencePins']:read_pinned(root,pin)
 for source in value['intakeSources']:validate_source(source,check_pin=False)
 return value

def validate_source(source,*,check_pin=True):
 """Reject changed endpoints, rights, media, budgets and unknown extra fields."""
 if check_pin:
  candidates=successor_config()['intakeSources']
  if not any(source==s for s in candidates):fail()
 m=source.get('mediaIntake',{})
 if (source.get('schemaVersion')!='offmenu-fixed-source-contract/1' or m.get('schemaVersion')!=SCHEMA
     or source['privateCustodyApproved'] is not True or source['sourceAcquisitionHeld'] is not False
     or source['expectedBytes'] is not None or source['checksums']!={} or source['historicalPreparationExceptions']!=[]
     or m['method']!='GET' or m['body']!='' or m['maximumRetries']!=0 or m['maximumHeaderBytes']!=65536
     or m['permissions']['read'] is not True or m['permissions']['copy'] is not True
     or m['reviewStatus']!='prepared-for-independent-review'):fail()
 parsed=urlsplit(source['url'])
 if [list(p) for p in parse_qsl(parsed.query,keep_blank_values=True,strict_parsing=True)]!=m['exactQueryPairs']:fail()
 source_spec(source).validate()
 ext={'csv-original':'csv','json-original':'json','docx-original':'docx'}.get(source['validation']['kind'])
 if ext is None or m['originalFilename']!='original.'+ext or source['wholeOperationSeconds']!=300 or not 1<=source['hardTransferBytes']<=8*MiB:fail()
 if m['integrity']['handler']!='bounded-'+source['validation']['kind']:fail()
 if m['maximumRequests']!=(2 if ext=='docx' else 1) or m['maximumRedirects']!=(1 if ext=='docx' else 0):fail()
 if (ext=='docx')!=(m['redirect'] is not None) or m['permissions']['extract']!=(None if ext=='docx' else True):fail()
 if source['expectedResponse']!={'content-type':{'csv':'text/csv','json':'application/json','docx':DOCX}[ext]}:fail()
 return source

def source_spec(source):
 return SourceSpec(source_key=source['sourceKey'],url=source['url'],policy_fingerprint=sha(canonical(source)),rights_reference=source['rightsReference'],
  enabled=True,rights_approved=True,held=False,ttl_seconds=30*86400,max_bytes=source['hardTransferBytes'],release=source['release'],query_keys=tuple(source['queryKeys']))

def checked_headers(raw,source,*,redirect=False):
 if not isinstance(raw,(list,dict)):fail('media-intake-header-invalid')
 pairs=list(raw.items()) if isinstance(raw,dict) else raw
 if len(pairs)>100 or sum(len(k.encode('utf-8'))+len(v.encode('utf-8'))+4 for k,v in pairs if isinstance(k,str) and isinstance(v,str))>65536:fail('media-intake-header-invalid')
 # Repeated non-rendered CSP and cookies are ignored only after syntax checks.
 ignored={'set-cookie','server-timing','content-security-policy','content-security-policy-report-only'};filtered=[]
 for key,value in pairs:
  if not isinstance(key,str) or not isinstance(value,str) or not re.fullmatch(r'[!#$%&\'*+.^_`|~0-9A-Za-z-]+',key) or any(ord(c)<32 or ord(c)==127 for c in value):fail('media-intake-header-invalid')
  _headers([(key,value)])
  if key.lower() not in ignored:filtered.append((key,value))
 headers=_headers(filtered)
 if headers.get('content-encoding','identity').lower()!='identity' or headers.get('vary','').lower() not in ('','accept-encoding'):fail('media-intake-header-invalid')
 length=headers.get('content-length');transfer=headers.get('transfer-encoding')
 if length is not None and (not re.fullmatch(r'[0-9]{1,12}',length) or int(length)<(0 if redirect else 1) or int(length)>source['hardTransferBytes']):fail('media-intake-framing-invalid')
 if transfer is not None and (length is not None or transfer.lower()!='chunked'):fail('media-intake-framing-invalid')
 if redirect:return headers
 if 'location' in headers:fail('media-intake-header-invalid')
 media=headers.get('content-type','').split(';')
 if media[0].strip().lower()!=source['expectedResponse']['content-type']:fail('media-intake-header-invalid')
 if len(media)>2 or (len(media)==2 and media[1].strip().lower() not in {'charset=utf-8','charset="utf-8"'}):fail('media-intake-header-invalid')
 if source['validation']['kind']=='docx-original' and len(media)!=1:fail('media-intake-header-invalid')
 # Requiring explicit framing avoids accepting an unframed truncated connection.
 if length is None and transfer is None:fail('media-intake-framing-invalid')
 return headers

class EphemeralStorageRequest:
 """Fresh issuer capability, memory-only. Never used for cache or claim identity."""
 __slots__=('url','source_key','request_method','request_body')
 def __init__(self,url,key):self.url=url;self.source_key=key;self.request_method='GET';self.request_body=''
 def __repr__(self):return '<ephemeral-reviewed-storage-request>'

def redirect_request(source,location,*,now=None):
 rule=source['mediaIntake']['redirect']
 if rule is None or not isinstance(location,str) or len(location.encode())>rule['maxLocationBytes'] or any(ord(c)<33 or ord(c)>126 for c in location) or '\\' in location:fail('media-intake-redirect-invalid')
 try:
  parts=urlsplit(location);pairs=parse_qsl(parts.query,keep_blank_values=True,strict_parsing=True)
  if (parts.scheme!='https' or parts.netloc!=rule['targetHost'] or parts.hostname!=rule['targetHost'] or parts.path!=rule['targetPath'] or parts.fragment
      or parts.username or parts.password or parts.port is not None or len(pairs)!=6 or len(set(k for k,v in pairs))!=6 or set(k for k,v in pairs)!=set(SIGNED_KEYS)
      or any(not v or len(v)>4096 or any(ord(c)<33 or ord(c)>126 for c in v) for k,v in pairs)):fail('media-intake-redirect-invalid')
  query=dict(pairs)
  if query['X-Goog-Algorithm']!='GOOG4-RSA-SHA256' or query['X-Goog-SignedHeaders']!='host' or not re.fullmatch(r'[a-fA-F0-9]{128,2048}',query['X-Goog-Signature']):fail('media-intake-redirect-invalid')
  if not re.fullmatch(r'[0-9]{1,5}',query['X-Goog-Expires']) or not 1<=int(query['X-Goog-Expires'])<=rule['maxExpirySeconds']:fail('media-intake-redirect-invalid')
  issued=datetime.strptime(query['X-Goog-Date'],'%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
  now=now or datetime.now(timezone.utc)
  if issued>now+timedelta(seconds=300) or issued+timedelta(seconds=int(query['X-Goog-Expires']))<=now:fail('media-intake-redirect-expired')
  credential=query['X-Goog-Credential'].split('/')
  if len(credential)!=5 or credential[1]!=issued.strftime('%Y%m%d') or credential[2:]!=['auto','storage','goog4_request'] or not re.fullmatch(r'[a-zA-Z0-9._+-]+@[a-zA-Z0-9.-]+',credential[0]):fail('media-intake-redirect-invalid')
 except (ValueError,UnicodeError,OverflowError):fail('media-intake-redirect-invalid')
 return EphemeralStorageRequest(location,source['sourceKey'])

def fetch_response(source,transport,deadline,meter,batch_meter,adapter):
 """Count both requests; close but never consume publisher redirect bodies."""
 transport=transport or BoundedHTTPSFileTransport(source['mediaIntake']['maximumHeaderBytes'])
 def request(spec):
  adapter.deadline_check(deadline)
  if batch_meter is not None:
   if hasattr(batch_meter,'start_request'):batch_meter.start_request()
   else:
    if batch_meter['requests']>=batch_meter['maximumRequests']:raise RefreshError('network-request-limit')
    batch_meter['requests']+=1
  if meter['requests']>=maximum_requests(source):raise RefreshError('network-request-limit')
  meter['requests']+=1
  return transport(spec,{'Accept-Encoding':'identity'},deadline=deadline)
 response=request(source_spec(source));redirect=source['mediaIntake']['redirect']
 if redirect is None:return response
 try:
  if response.status!=redirect['requiredOriginStatus']:raise RefreshError('source-response-not-permitted')
  headers=checked_headers(response.headers,source,redirect=True)
  spec=redirect_request(source,headers.get('location'))
 finally:response.close()
 # No cookies, authorization, referer, or signed identity is reused/persisted.
 return request(spec)

def _csv_integrity(data,rule,deadline,check):
 check(deadline)
 if not _CSV_LOCK.acquire(timeout=max(0,deadline-time.monotonic())):raise RefreshError('acquisition-duration-limit-exceeded')
 previous=csv.field_size_limit()
 try:
  csv.field_size_limit(rule['maxFieldBytes'])
  return _csv_integrity_locked(data,rule,deadline,check)
 finally:
  csv.field_size_limit(previous);_CSV_LOCK.release()

def _csv_integrity_locked(data,rule,deadline,check):
 try:
  text=data.decode(rule['encoding']);reader=csv.reader(io.StringIO(text,newline=''),delimiter=',',strict=True)
  header=next(reader)
  if not header or any(not x.strip() for x in header) or len(set(header))!=len(header) or len(header)>1024:fail('media-intake-content-invalid')
  if rule.get('requiredHeader') is not None and header!=rule['requiredHeader']:fail('media-intake-content-invalid')
  for index,row in enumerate([header]):
   if any(len(field.encode('utf-8'))>rule['maxFieldBytes'] or '\x00' in field for field in row):fail('media-intake-content-invalid')
  count=0
  for row in reader:
   check(deadline);count+=1
   if count>rule['maxRecords']:fail('media-intake-record-limit')
   if len(row)!=len(header) or any(len(field.encode('utf-8'))>rule['maxFieldBytes'] or '\x00' in field for field in row):fail('media-intake-content-invalid')
  if not count:fail('media-intake-content-invalid')
 except (UnicodeError,csv.Error,StopIteration):fail('media-intake-content-invalid')

def _json_integrity(data,rule,deadline,check):
 try:
  text=data.decode(rule['encoding'])
  def pairs(items):
   result={}
   for k,v in items:
    if k in result:fail('media-intake-content-invalid')
    result[k]=v
   return result
  def constant(v):fail('media-intake-content-invalid')
  value=json.loads(text,object_pairs_hook=pairs,parse_constant=constant)
  if not isinstance(value,dict) or value.get('success') is not True or not isinstance(value.get('result'),dict) or value['result'].get('id')!=rule['expectedDatasetId']:fail('media-intake-content-invalid')
  queue=[(value,1)];count=0
  while queue:
   check(deadline);current,depth=queue.pop();count+=1
   if depth>rule['maxDepth'] or count>1000000:fail('media-intake-record-limit')
   if isinstance(current,dict):queue.extend((v,depth+1) for v in current.values())
   elif isinstance(current,list):queue.extend((v,depth+1) for v in current)
   elif isinstance(current,float) and not math.isfinite(current):fail('media-intake-content-invalid')
 except (ValueError,UnicodeError,RecursionError):fail('media-intake-content-invalid')

def _docx_integrity(data,rule,deadline,check):
 try:
  if not data.startswith(b'PK\x03\x04'):fail('media-intake-archive-invalid')
  with zipfile.ZipFile(io.BytesIO(data)) as archive:
   infos=archive.infolist();names=set();total=0
   if not 1<=len(infos)<=rule['maxArchiveMembers']:fail('media-intake-archive-invalid')
   for info in infos:
    check(deadline);name=info.filename;path=PurePosixPath(name);total+=info.file_size
    if (name in names or name.startswith('/') or '\\' in name or ':' in name or '..' in path.parts or '\x00' in name or info.flag_bits&1
        or stat.S_ISLNK(info.external_attr>>16) or info.compress_type not in {zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED}
        or info.file_size>rule['maxMemberBytes'] or total>rule['maxExpandedBytes'] or info.file_size>max(1,info.compress_size)*rule['maxCompressionRatio']
        or 'vbaproject' in name.casefold() or 'vbadata' in name.casefold() or name.casefold().endswith(('.exe','.dll','.bin'))):fail('media-intake-archive-invalid')
    names.add(name)
   if not set(rule['requireMembers'])<=names:fail('media-intake-archive-invalid')
   for info in infos:
    count=0;parts=[] if info.filename in rule['requireMembers'] else None
    with archive.open(info) as stream:
     while True:
      check(deadline);block=stream.read(min(65536,rule['maxMemberBytes']-count+1))
      if not block:break
      count+=len(block)
      if count>info.file_size or count>rule['maxMemberBytes']:fail('media-intake-archive-invalid')
      if parts is not None:parts.append(block)
    if count!=info.file_size:fail('media-intake-archive-invalid')
    if parts is not None:
     xml=b''.join(parts)
     if b'\x00' in xml or b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper() or b'MACROENABLED' in xml.upper():fail('media-intake-archive-invalid')
     document=ET.fromstring(xml)
     required='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}document' if info.filename=='word/document.xml' else '{http://schemas.openxmlformats.org/package/2006/content-types}Types'
     if document.tag!=required:fail('media-intake-archive-invalid')
     stack=[(document,1)];elements=0
     while stack:
      check(deadline);node,depth=stack.pop();elements+=1
      if depth>128 or elements>1000000:fail('media-intake-archive-invalid')
      stack.extend((child,depth+1) for child in node)
 except (zipfile.BadZipFile,zlib.error,ValueError,UnicodeError,ET.ParseError,RuntimeError,NotImplementedError,RecursionError):fail('media-intake-archive-invalid')

def validate_original(result,source,deadline,adapter):
 """Hash stable original and check bounded structure, without semantic extraction."""
 path=safe_path(result.path);maximum=source['hardTransferBytes'];fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 with os.fdopen(fd,'rb') as stream:
  before=os.fstat(stream.fileno())
  if not stat.S_ISREG(before.st_mode) or before.st_mode&0o077 or before.st_uid!=os.getuid() or not 0<before.st_size<=maximum:raise RefreshError('source-length-mismatch')
  chunks=[];count=0;digest=hashlib.sha256()
  while True:
   adapter.deadline_check(deadline);block=stream.read(min(65536,maximum-count+1))
   if not block:break
   count+=len(block)
   if count>maximum:raise RefreshError('source-length-mismatch')
   digest.update(block);chunks.append(block)
  data=b''.join(chunks);rule=source['mediaIntake']['integrity']
  {'csv-original':_csv_integrity,'json-original':_json_integrity,'docx-original':_docx_integrity}[source['validation']['kind']](data,rule,deadline,adapter.deadline_check)
  after=os.fstat(stream.fileno())
 identity=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
 if identity(before)!=identity(after) or identity(after)!=identity(path.stat()):raise RefreshError('source-changed-during-validation')
 if result.bytes!=count:raise RefreshError('source-length-mismatch')
 if result.sha256!=digest.hexdigest():raise RefreshError('source-sha256-mismatch')
 return {'bytes':count,'sha256':result.sha256,'publisherMD5Verified':False,'headerVerified':True,'originalAcquiredAt':result.provenance['originalAcquiredAt']}

def validate_successor_selection(selected,manifest,root=ROOT):
 """Bind every delta to the draft; an arbitrary reviewed-status label is insufficient."""
 successor=successor_config(root)
 base=read_pinned(root,successor['basePins']['global-original-selection.json'])
 original=read_pinned(root,successor['basePins']['global-known-assets-runtime.json'])
 expected,expected_manifest=compose_for_review(base,original,successor)
 expected['knownIntakeSuccessor']['status']='parent-reviewed-owner-manual'
 if selected!=expected or manifest!=expected_manifest:fail()
 return selected

def compose_for_review(base,manifest,successor):
 """Pure prospective composition; no activation, owner access or mutable pins."""
 selected=deepcopy(base);composed=deepcopy(manifest)
 selected['sources'].extend(deepcopy(successor['intakeSources']))
 selected['maximumRequests']+=successor['maximumAdditionalRequests'];selected['maximumTransferBytes']+=successor['maximumAdditionalTransferBytes']
 selected['privateOriginalDownload']['freshSources'].extend(s['sourceKey'] for s in successor['intakeSources'])
 selected['knownIntakeSuccessor']={'selectionSHA256':sha(canonical(successor)),'status':'prepared-for-review-not-active','reuseJoins':deepcopy(successor['reuseJoins']),'remainingUnresolvedUnits':54}
 assets={a['assetId']:a for a in composed['assets']}
 for source in successor['intakeSources']:
  asset=assets[source['mediaIntake']['assetId']]
  if asset['disposition']!='missing-contract' or asset.get('retainedOriginal') is not None:fail()
  asset['sourceKey']=source['sourceKey'];asset['disposition']='eligible'
  if source['mediaIntake']['permissions']['extract'] is True:
   selected['preparation'].append({'sourceKey':source['sourceKey'],'country':None,'type':None,'permissions':source['mediaIntake']['permissions'],'holds':[],
    'expectedMediaTypes':[source['expectedResponse']['content-type']], 'parameters':({'encoding':'utf-8-sig','delimiter':',','hasHeader':True} if source['validation']['kind']=='csv-original' else {'encoding':'utf-8-sig'}),
    'retainedOriginal':None,'downstreamHolds':source['downstreamHolds']})
 validate_joins(successor['reuseJoins'],manifest)
 return selected,composed

def validate_joins(joins,manifest,*,binding_manifest=None):
 current_assets={r['assetId']:r for r in manifest['assets']}
 assets={r['assetId']:r for r in (binding_manifest or manifest)['assets']};targets=set();allmembers=set()
 for row in joins:
  if set(row)!={'assetId','kind','memberAssetIds','byteAliasEvidence','mappingAssetSHA256','memberAssetSHA256','holdsPreserved','sourceStageHoldsPreserved'}:fail('media-intake-join-invalid')
  target=row['assetId'];members=row['memberAssetIds']
  if binding_manifest is not None:
   for key in [target,*members]:
    if key not in assets or key not in current_assets or {k:v for k,v in assets[key].items() if k!='preparationContract'}!={k:v for k,v in current_assets[key].items() if k!='preparationContract'}:fail('media-intake-join-invalid')
  if target not in assets or target in targets or row['kind'] not in {'exact-original-alias','member-family'} or not members or len(members)!=len(set(members)) or any(k not in assets or k==target for k in members):fail('media-intake-join-invalid')
  if sha(canonical(assets[target]))!=row['mappingAssetSHA256'] or [sha(canonical(assets[k])) for k in members]!=row['memberAssetSHA256']:fail('media-intake-join-invalid')
  if row['holdsPreserved']!=assets[target].get('holds',[]) or row['sourceStageHoldsPreserved']!=assets[target].get('sourceStageHolds',[]):fail('media-intake-join-invalid')
  alias=row['byteAliasEvidence']
  if row['kind']=='exact-original-alias':
   if len(members)!=1 or not isinstance(alias,dict) or alias['canonicalExistingAssetId']!=members[0] or alias['aliasAssetId']!=target:fail('media-intake-join-invalid')
   retained=assets[members[0]]['retainedOriginal']
   if retained['sha256']!=alias['expectedSHA256'] or retained['bytes']!=alias['expectedBytes'] or retained['path']!=alias['retainedPath']:fail('media-intake-join-invalid')
  elif alias is not None:fail('media-intake-join-invalid')
  targets.add(target);allmembers.update(members)
 if targets&allmembers:fail('media-intake-join-invalid')
 return joins

def join_outcomes(joins,manifest,outcomes,*,binding_manifest=None):
 """No body/stat/network callbacks. Members and every held/partial code survive."""
 validate_joins(joins,manifest,binding_manifest=binding_manifest);indices={r['assetId']:i for i,r in enumerate(manifest['assets'])};results=[]
 for row in joins:
  target=indices[row['assetId']];members=[indices[k] for k in row['memberAssetIds']]
  groups={}
  for index in members:
   state=outcomes[index];key=(state['custody'],state['stage'],state['code']);groups.setdefault(key,[]).append(index)
  stages={outcomes[i]['stage'] for i in members};own=outcomes[target]
  held=own['stage']=='held' or bool((set(row['holdsPreserved'])|set(row['sourceStageHoldsPreserved']))&{'all','read','copy','extract'})
  # Family readiness is metadata about members, never an original/hash claim.
  stage='held' if held else next((v for v in ('held','error','unsupported','unverified','missing-contract','eligible','retained','ready-nextstage') if v in stages),'unverified')
  result={'custody':own['custody'],'stage':stage,'code':own['code'] if held else (next(iter(groups))[2] if len(groups)==1 else None)}
  if row['kind']=='exact-original-alias' and not held:result=dict(outcomes[members[0]])
  outcomes[target]=result
  results.append({'assetIndex':target,'kind':row['kind'],'memberAssetIndexes':members,'metadataOnly':True,'memberOutcomeGroups':[{'custody':k[0],'stage':k[1],'code':k[2],'assetIndexes':v} for k,v in sorted(groups.items(),key=lambda x:repr(x[0]))]})
 return results
