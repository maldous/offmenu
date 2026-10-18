"""Explicit retained-file identity verification with bounded streaming memory.

No network, source copies, payload outputs, decompression, semantic extraction or
readiness promotion. Large originals need an exact reviewed row and invocation.
"""
from pathlib import Path
import hashlib,os,re,stat,time
from .core import RefreshError,canonical,sha,safe_path
from . import media_preparation as media

SCHEMA='offmenu-retained-verification-contract/1'
RESULT_SCHEMA='offmenu-retained-verification-result/1'
ERROR_CODES=frozenset({'verification-contract-invalid','verification-read-held','verification-partial-held','verification-deadline','verification-unavailable','verification-not-regular','verification-extent-mismatch','verification-digest-mismatch','verification-original-changed','verification-media-unverified'})

def open_fixed(path):
 """Open every component no-follow, preventing parent substitution during open."""
 path=Path(path)
 if not path.is_absolute() or '..' in path.parts:raise RefreshError('verification-unavailable')
 parent=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:
  for part in path.parts[1:-1]:
   child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent);os.close(parent);parent=child
  return os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
 finally:os.close(parent)

def validate_contract(contract):
 fields={'schemaVersion','assetId','expectedSHA256','expectedBytes','expectedMediaTypes','permissions','holds','maximumReadBytes','chunkBytes','maximumSniffBytes','maximumSeconds','maximumOutputBytes','completeReadRequired','decompressionAllowed','networkRequests'}
 if (not isinstance(contract,dict) or set(contract)!=fields or contract['schemaVersion']!=SCHEMA or not isinstance(contract['assetId'],str) or not 1<=len(contract['assetId'])<=256
     or not isinstance(contract['expectedSHA256'],str) or not re.fullmatch('[a-f0-9]{64}',contract['expectedSHA256'])
     or type(contract['expectedBytes']) is not int or not 1<=contract['expectedBytes']<=1024**4 or contract['maximumReadBytes']!=contract['expectedBytes']
     or contract['chunkBytes']!=1024**2 or contract['maximumSniffBytes']!=65536 or type(contract['maximumSeconds']) is not int or not 1<=contract['maximumSeconds']<=1200
     or contract['maximumOutputBytes']!=0 or contract['completeReadRequired'] is not True or contract['decompressionAllowed'] is not False or contract['networkRequests']!=0
     or contract['permissions']!={'read':True,'copy':False,'extract':False} or not isinstance(contract['holds'],list) or len(contract['holds'])>64 or any(not isinstance(h,str) or len(h)>256 for h in contract['holds'])
     or not isinstance(contract['expectedMediaTypes'],list) or not 0<=len(contract['expectedMediaTypes'])<=16 or any(not isinstance(x,str) or len(x)>127 or not re.fullmatch(r'[a-z0-9!#$&^_.+-]+/[a-z0-9!#$&^_.+-]+',x) for x in contract['expectedMediaTypes'])):raise RefreshError('verification-contract-invalid')
 return contract

def verify_retained(contract,original,absolute_deadline):
 """Return only closed metadata. The caller binds this contract to a reviewed pin."""
 validate_contract(contract);deadline=min(absolute_deadline,time.monotonic()+contract['maximumSeconds'])
 report={'schemaVersion':RESULT_SCHEMA,'assetId':contract['assetId'],'contractSHA256':sha(canonical(contract)), 'status':'blocked','errorCode':None,'bytesRead':0,'maximumReadBytes':contract['maximumReadBytes'],
  'originalSHA256':None,'originalBytes':None,'actualMediaType':None,'integrityVerified':False,'mediaObserved':False,'nextStageReady':False,'sourceCopied':False,'extractionPerformed':False,'networkRequests':0,'payloadBytesWritten':0}
 try:
  if 'read' in contract['holds'] or 'all' in contract['holds']:raise RefreshError('verification-read-held')
  path=Path(original)
  if path.name.lower().endswith(('.part','.partial')):raise RefreshError('verification-partial-held')
  path=safe_path(path)
  def check():
   if time.monotonic()>=deadline:raise RefreshError('verification-deadline')
  check();fd=open_fixed(path)
  with os.fdopen(fd,'rb') as stream:
   before=os.fstat(stream.fileno())
   if not stat.S_ISREG(before.st_mode):raise RefreshError('verification-not-regular')
   if before.st_size!=contract['expectedBytes']:raise RefreshError('verification-extent-mismatch')
   digest=hashlib.sha256();prefix=b''
   while report['bytesRead']<contract['maximumReadBytes']:
    check();block=stream.read(min(contract['chunkBytes'],contract['maximumReadBytes']-report['bytesRead']))
    if not block:raise RefreshError('verification-extent-mismatch')
    report['bytesRead']+=len(block);digest.update(block)
    if len(prefix)<contract['maximumSniffBytes']:prefix+=block[:contract['maximumSniffBytes']-len(prefix)]
    check()
   after=os.fstat(stream.fileno())
  identity=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
  # Re-resolve every parent and reopen the complete fixed path before accepting identity.
  current_fd=open_fixed(path)
  try:current=os.fstat(current_fd)
  finally:os.close(current_fd)
  if identity(before)!=identity(after) or identity(after)!=identity(current):raise RefreshError('verification-original-changed')
  if digest.hexdigest()!=contract['expectedSHA256']:raise RefreshError('verification-digest-mismatch')
  report.update(integrityVerified=True,originalSHA256=digest.hexdigest(),originalBytes=report['bytesRead'],status='verified-retained')
  # Prefix observation is explicitly not archive validation or text parsing.
  try:
   observed,evidence=media._sniff(prefix,contract['expectedMediaTypes'],{'encoding':'utf-8'},complete=False)
   report['actualMediaType']=observed
   report['mediaObserved']=observed in contract['expectedMediaTypes'] and observed!='application/octet-stream'
  except media.PreparationError:pass
  if not report['mediaObserved']:report['errorCode']='verification-media-unverified'
 except (RefreshError,OSError,ValueError,TypeError) as failure:
  code=str(failure) if isinstance(failure,RefreshError) and str(failure) in ERROR_CODES else 'verification-unavailable'
  report.update(status='failed' if report['bytesRead'] else 'blocked',errorCode=code)
 return sanitize_report(report,contract)

def sanitize_report(report,contract):
 validate_contract(contract)
 fields={'schemaVersion','assetId','contractSHA256','status','errorCode','bytesRead','maximumReadBytes','originalSHA256','originalBytes','actualMediaType','integrityVerified','mediaObserved','nextStageReady','sourceCopied','extractionPerformed','networkRequests','payloadBytesWritten'}
 if (not isinstance(report,dict) or set(report)!=fields or report['schemaVersion']!=RESULT_SCHEMA or report['assetId']!=contract['assetId'] or report['contractSHA256']!=sha(canonical(contract))
     or report['status'] not in {'blocked','failed','verified-retained'} or report['errorCode'] not in ERROR_CODES|{None} or type(report['bytesRead']) is not int or not 0<=report['bytesRead']<=contract['maximumReadBytes']
     or report['maximumReadBytes']!=contract['maximumReadBytes'] or report['networkRequests']!=0 or report['payloadBytesWritten']!=0
     or any(report[k] is not False for k in ('nextStageReady','sourceCopied','extractionPerformed')) or any(type(report[k]) is not bool for k in ('integrityVerified','mediaObserved'))
     or report['actualMediaType'] not in media.MIMES|{None}):raise ValueError('invalid-retained-verification-summary')
 if report['status']=='verified-retained':
  if not report['integrityVerified'] or report['originalSHA256']!=contract['expectedSHA256'] or report['originalBytes']!=contract['expectedBytes'] or report['bytesRead']!=contract['expectedBytes'] or report['errorCode']!=(None if report['mediaObserved'] else 'verification-media-unverified'):raise ValueError('invalid-retained-verification-summary')
 elif report['integrityVerified'] or report['originalSHA256'] is not None or report['originalBytes'] is not None or report['actualMediaType'] is not None or report['mediaObserved'] or report['errorCode'] is None:raise ValueError('invalid-retained-verification-summary')
 return report
