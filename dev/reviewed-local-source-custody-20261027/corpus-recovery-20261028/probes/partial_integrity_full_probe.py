"""Read-only bounded diagnostic, never source equivalence or release qualification."""
import os,stat,json,gzip,hashlib,time,signal,zlib
ROOT='/offmenu-corpus'
NAMES=('common-bulk-food-semantic-final-20261014','common-places-semantic-final-20261014.partial')
MAX_FILES=4000
MAX_COMPRESSED=3200*1024*1024
MAX_DECODED=64*1024*1024*1024
MAX_FILE_DECODED=256*1024*1024
GLOBAL_DEADLINE=time.monotonic()+275
MAX_LINE=32*1024*1024
class Limit(Exception):pass
def signature(s):return(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
def opened(path):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK)
 s=os.fstat(fd)
 if not stat.S_ISREG(s.st_mode) or not os.fstatvfs(fd).f_flag&os.ST_RDONLY:
  os.close(fd);raise ValueError('unsafe_object')
 return os.fdopen(fd,'rb'),s
def scan(root,name):
 out={'package':name,'verified_files':0,'failed_files':0,'incomplete_files':0,'verified_packets':0,'verified_compressed_bytes':0,'verified_decoded_bytes':0,'failures':{},'full_package_verified':False}
 base=os.path.join(root,name)
 candidates=[]
 for folder in (base,os.path.join(base,'packets')):
  try:
   s=os.lstat(folder)
   if not stat.S_ISDIR(s.st_mode) or not os.statvfs(folder).f_flag&os.ST_RDONLY:raise ValueError('unsafe_folder')
   for e in os.scandir(folder):
    if e.name.endswith('.jsonl.gz') and e.is_file(follow_symlinks=False):candidates.append(e.path)
  except FileNotFoundError:pass
 candidates.sort();out['candidate_files']=len(candidates)
 selected=candidates[:MAX_FILES];out['selected_files']=len(selected)
 deadline=GLOBAL_DEADLINE;total_decoded=0;total_compressed=0;receipts=[]
 metadata_before=[(p,signature(os.stat(p,follow_symlinks=False))) for p in candidates]
 for path in selected:
  packets=decoded=0;stop=None
  try:
   if time.monotonic()>deadline:raise Limit('time_budget')
   raw,before=opened(path)
   with raw:
    if total_compressed+before.st_size>MAX_COMPRESSED:raise Limit('compressed_budget')
    total_compressed+=before.st_size
    h=hashlib.sha256()
    while True:
     if time.monotonic()>deadline:raise Limit('time_budget')
     block=raw.read(1024*1024)
     if not block:break
     h.update(block)
    raw.seek(0)
    with gzip.GzipFile(fileobj=raw,mode='rb') as gz:
     while True:
      if time.monotonic()>deadline:raise Limit('time_budget')
      line=gz.readline(MAX_LINE+1)
      if not line:break
      total_decoded+=len(line);decoded+=len(line)
      if len(line)>MAX_LINE:raise Limit('line_budget')
      if total_decoded>MAX_DECODED:raise Limit('decoded_budget')
      if decoded>MAX_FILE_DECODED:raise Limit('file_expansion_limit')
      if not line.strip():continue
      p=json.loads(line,parse_constant=lambda _:(_ for _ in ()).throw(ValueError("nonfinite_json")))
      if not isinstance(p,dict) or not isinstance(p.get('schemaVersion'),str) or any(not isinstance(p.get(k),list) for k in ('resources','assertions','relations','citations','translations')):raise ValueError('packet_shape')
      packets+=1
    if signature(before)!=signature(os.fstat(raw.fileno())) or signature(before)!=signature(os.stat(path,follow_symlinks=False)):raise ValueError('changed_during_read')
   out['verified_files']+=1;out['verified_packets']+=packets
   out['verified_compressed_bytes']+=before.st_size;out['verified_decoded_bytes']+=decoded
   receipts.append({'name':os.path.relpath(path,base),'sha256':h.hexdigest(),'packets':packets,'compressed_bytes':before.st_size})
  except Limit as e:
   out['incomplete_files']+=1;out['stopped_reason']=str(e)
   if str(e) in ('file_expansion_limit','line_budget'):continue
   break
  except (OSError,EOFError,ValueError,UnicodeError,RecursionError,zlib.error) as e:
   out['failed_files']+=1;code=type(e).__name__;out['failures'][code]=out['failures'].get(code,0)+1
 out['unverified_files']=len(candidates)-out['verified_files']-out['failed_files']
 out['verified_hash_receipts_sha256']=hashlib.sha256(json.dumps(receipts,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 out['read_only_payload_preserved']=True
 out['candidate_metadata_stable_at_end']=all(signature(os.stat(p,follow_symlinks=False))==sig for p,sig in metadata_before)
 after=[]
 for folder in (base,os.path.join(base,'packets')):
  if os.path.isdir(folder):after.extend(e.path for e in os.scandir(folder) if e.name.endswith('.jsonl.gz') and e.is_file(follow_symlinks=False))
 out['candidate_set_stable_at_end']=sorted(after)==candidates
 out['selected_integrity_scope_complete']=out['verified_files']==len(candidates) and out['candidate_metadata_stable_at_end'] and out['candidate_set_stable_at_end']
 return out

def checkpoint(root):
 path=os.path.join(root,NAMES[0],'checkpoint.json')
 try:
  f,s=opened(path)
  with f:
   if s.st_size>4*1024*1024:return {'exists':True,'status':'size_limit'}
   b=f.read(4*1024*1024+1)
   if signature(s)!=signature(os.fstat(f.fileno())):return {'exists':True,'status':'changed'}
  d=json.loads(b);pins=d.get('pins',{})
  return {'exists':True,'sha256':hashlib.sha256(b).hexdigest(),'expected_schema':d.get('schemaVersion')=='offmenu-bulk-repair-checkpoint/1','complete':d.get('complete') is True,'asset_receipts':len(d.get('assets',{})) if isinstance(d.get('assets'),dict) else None,'pin_keys_present':{k:isinstance(pins.get(k),str) for k in ('inputManifestByteSha256','schemaByteSha256','contractByteSha256','repairImplementationByteSha256','sourceDirectory')}}
 except FileNotFoundError:return {'exists':False}
 except (OSError,ValueError,TypeError,AttributeError):return {'status':'unreadable_or_invalid'}

def main():
 signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(Limit('hard_deadline')));signal.alarm(290)
 out={'schema':'offmenu-retained-integrity-inspection/1','source_equivalence_verified':False,'full_schema_verified':False,'qualification_established':False,'scope':'all inventoried gzip candidates, bounded CRC/JSON/basic packet shape and stable byte hashes; no source equality or semantic proof','packages':[]}
 try:
  out['bulk_checkpoint']=checkpoint(ROOT)
  for name in NAMES:out['packages'].append(scan(ROOT,name))
 except (Limit,OSError,ValueError) as e:out['stopped_reason']=type(e).__name__
 signal.alarm(0);print(json.dumps(out,sort_keys=True,separators=(',',':')))
if __name__=='__main__':main()
