import gzip,json,os,stat,hashlib
root='/offmenu-corpus/common-bulk-food-semantic-final-20261014/packets'
names=sorted(e.name for e in os.scandir(root) if e.name.endswith('.jsonl.gz') and e.is_file(follow_symlinks=False))
name=names[-1];path=root+'/'+name;fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC);s=os.fstat(fd);assert stat.S_ISREG(s.st_mode) and os.fstatvfs(fd).f_flag&os.ST_RDONLY
result={'file':'packets/'+name,'bytes':s.st_size,'full_file_valid':False};h=hashlib.sha256()
with os.fdopen(fd,'rb') as raw:
 while True:
  b=raw.read(1048576)
  if not b:break
  h.update(b)
 result['sha256']=h.hexdigest();raw.seek(0);n=0
 try:
  with gzip.GzipFile(fileobj=raw,mode='rb') as gz:
   while True:
    b=gz.read(1048576)
    if not b:break
    n+=len(b)
    if n>128*1048576:raise ValueError('decoded_cap')
  result['full_file_valid']=True
 except (EOFError,OSError,ValueError) as e:result['error_class']=type(e).__name__
 after=os.fstat(raw.fileno());result['stable_metadata']=(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)
result['decoded_bytes_before_error']=n
print(json.dumps(result))
