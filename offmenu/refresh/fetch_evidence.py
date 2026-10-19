"""Bounded, immutable sanitized fetch metadata, separate from source originals."""
from pathlib import Path
import hashlib,os,re,stat
from .core import RefreshError,canonical,sha,strict_json
from .retained_integrity_verification import open_fixed

CAPS={'metadata-reconciliation':4*1024*1024,'response-diagnostics':65536}
SCHEMA='offmenu-fetch-evidence-reference/1'

def validate_reference(ref):
 if (type(ref)is not dict or set(ref)!={'schemaVersion','kind','sha256','bytes'}
     or ref['schemaVersion']!=SCHEMA or ref['kind']not in CAPS
     or type(ref['bytes'])is not int or not 0<ref['bytes']<=CAPS[ref['kind']]
     or type(ref['sha256'])is not str or re.fullmatch('[a-f0-9]{64}',ref['sha256'])is None):raise RefreshError('fetch-evidence-invalid')
 return ref

def save(kind,value,*,output_root,adapter,validator,private_directory):
 if kind not in CAPS:raise RefreshError('fetch-evidence-invalid')
 validator(value);raw=canonical(value)
 ref=validate_reference({'schemaVersion':SCHEMA,'kind':kind,'sha256':sha(raw),'bytes':len(raw)})
 work=adapter.owned_directory(adapter.owned_directory(output_root)/'collection')
 folder=private_directory(work/'fetch-evidence',adapter)
 adapter.write_immutable(folder/(kind+'-'+ref['sha256']+'.json'),value)
 return ref

def _load(ref,*,output_root,validator):
 validate_reference(ref)
 path=Path(output_root)/'collection/fetch-evidence'/(ref['kind']+'-'+ref['sha256']+'.json')
 fd=open_fixed(path)
 try:
  before=os.fstat(fd)
  if not stat.S_ISREG(before.st_mode)or before.st_uid!=os.getuid()or before.st_mode&0o077 or before.st_nlink!=1 or before.st_size!=ref['bytes']:raise RefreshError('fetch-evidence-invalid')
  data=bytearray()
  while len(data)<ref['bytes']:
   block=os.read(fd,min(65536,ref['bytes']-len(data)))
   if not block:raise RefreshError('fetch-evidence-invalid')
   data.extend(block)
  after=os.fstat(fd)
 finally:os.close(fd)
 fd=open_fixed(path)
 try:current=os.fstat(fd)
 finally:os.close(fd)
 identity=lambda x:(x.st_dev,x.st_ino,x.st_size,x.st_mtime_ns,x.st_ctime_ns,x.st_uid,x.st_mode,x.st_nlink)
 if identity(before)!=identity(after)or identity(after)!=identity(current)or sha(data)!=ref['sha256']:raise RefreshError('fetch-evidence-invalid')
 value=strict_json(bytes(data));validator(value)
 if canonical(value)!=bytes(data):raise RefreshError('fetch-evidence-invalid')
 return value

def publication_parts(ref,value,chunks):
 validate_reference(ref)
 if sha(canonical(value))!=ref['sha256']or len(canonical(value))!=ref['bytes']:raise RefreshError('fetch-evidence-invalid')
 if ref['kind']=='metadata-reconciliation':
  control={k:v for k,v in value.items()if k!='rows'}
  control['reconstructedReportSHA256']=ref['sha256']
  return [('fetch-metadata-control.json',canonical(control))]+chunks('fetch-metadata-rows',value['rows'])
 return [('fetch-response-diagnostics.json',canonical(value))]


def load(ref,*,output_root,validator):
 try:return _load(ref,output_root=output_root,validator=validator)
 except OSError:raise RefreshError('fetch-evidence-invalid')from None
