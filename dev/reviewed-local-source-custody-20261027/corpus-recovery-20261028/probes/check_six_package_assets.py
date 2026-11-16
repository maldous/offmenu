import os,stat,json,hashlib,re,signal,time
PINS={"common-data-reviewed-package-20261014":"c15005b224ae18c1e660837c6ac9fab88beb0b4d53ce34db6a5a87f12f6d919d","common-reference-delivery-final-20261014":"bec93ffedf4d80eef10ec11000c18161024a3c30999697ad1f3db5f3318ff3e7","common-national-semantic-final-20261014":"c129dd58a917cf98721856f9094c724923f35ed14cefe2d9206c03db1fc6fcbb","measurement-terminology-final-qualified-20261014":"75c33340f1ee25c4121c57d8fc124621b4455412717fc6d9dd01bfb162351679","recipe-expansion-final-qualified-20261014/common-graph":"6f035cbe1303554cb59e6d3ee82f0e49bfa577e8d3844c2266df3241a4e328d5","historical-recipe-quality-final-corrected-20261014":"e4c06a1d4a2fcb492529c37c6245a595dd104061ef1a63427cbe9d65e7e2241f"}
ROOT='/offmenu-corpus'
START=time.monotonic();TOTAL_READ=0
class Budget(Exception):pass
class Refused(Exception):pass
def check():
    if time.monotonic()-START>25:raise Budget('time_budget')
def open_below(fd,key,directory=False):
    if not isinstance(key,str) or key.startswith('/') or '\x00' in key or any(p in ('','..','.') for p in key.split('/')):raise Refused('unsafe_asset_key')
    current=os.dup(fd)
    try:
        parts=key.split('/')
        for i,p in enumerate(parts):
            f=os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK
            if i<len(parts)-1 or directory:f|=os.O_DIRECTORY
            nxt=os.open(p,f,dir_fd=current);os.close(current);current=nxt
        if not os.fstatvfs(current).f_flag&os.ST_RDONLY:raise Refused('not_readonly')
        return current
    except BaseException:os.close(current);raise
def digest_fd(fd,expected_size,maxsize):
    global TOTAL_READ
    st=os.fstat(fd)
    if not stat.S_ISREG(st.st_mode):raise Refused('not_regular')
    if st.st_size!=expected_size:raise Refused('size_mismatch')
    if st.st_size>maxsize:raise Budget('byte_budget')
    digest=hashlib.sha256();n=0
    while True:
        check();b=os.read(fd,1024*1024)
        if not b:break
        n+=len(b);TOTAL_READ+=len(b)
        if n>expected_size or TOTAL_READ>1024**3:raise Budget('byte_budget_or_growth')
        digest.update(b)
    after=os.fstat(fd)
    if (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise Refused('changed_during_read')
    if n!=expected_size:raise Refused('short_read')
    return digest.hexdigest()
def main():
    out={'schema':'offmenu-six-package-asset-checks/1','qualification_rerun':False,'payloads_exported':False,'stopped_reason':None,'packages':[]}
    root=None
    try:
        root=os.open(ROOT,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
        for name,pin in PINS.items():
            check();row={'package':name,'manifest_sha256':pin,'listed':0,'checked':0,'matched':0,'mismatched':0,'bytes_hashed':0,'errors':[],'complete':False};out['packages'].append(row)
            dfd=open_below(root,name,True)
            try:
                fd=open_below(dfd,'manifest.json')
                try:
                    st=os.fstat(fd)
                    if not stat.S_ISREG(st.st_mode) or st.st_size>4*1024**2:raise Refused('manifest_size_type')
                    raw=os.read(fd,st.st_size+1)
                    if len(raw)!=st.st_size or hashlib.sha256(raw).hexdigest()!=pin:raise Refused('manifest_pin_mismatch')
                finally:os.close(fd)
                m=json.loads(raw);files=m.get('files')
                if not isinstance(files,list) or not 1<=len(files)<=20000:raise Refused('manifest_files_schema')
                seen=set();planned=0
                for f in files:
                    if not isinstance(f,dict) or not isinstance(f.get('key'),str) or type(f.get('bytes'))is not int or f['bytes']<0 or not isinstance(f.get('sha256'),str) or not re.fullmatch('[0-9a-f]{64}',f['sha256']):raise Refused('manifest_asset_schema')
                    if f['key'] in seen:raise Refused('duplicate_asset_key')
                    seen.add(f['key']);planned+=f['bytes']
                if planned>1024**3:raise Budget('planned_byte_budget')
                row['listed']=len(files);row['planned_bytes']=planned
                for i,f in enumerate(files):
                    check();fd=None
                    try:
                        fd=open_below(dfd,f['key']);h=digest_fd(fd,f['bytes'],1024**3-TOTAL_READ)
                        row['checked']+=1;row['bytes_hashed']+=f['bytes']
                        if h==f['sha256']:row['matched']+=1
                        else:
                            row['mismatched']+=1
                            if len(row['errors'])<10:row['errors'].append({'asset_index':i,'asset_key_sha256':hashlib.sha256(f['key'].encode()).hexdigest(),'reason':'sha256_mismatch'})
                    except (OSError,Refused) as exc:
                        row['mismatched']+=1
                        if len(row['errors'])<10:row['errors'].append({'asset_index':i,'asset_key_sha256':hashlib.sha256(f['key'].encode()).hexdigest(),'reason':str(exc) if isinstance(exc,Refused) else 'open_or_read_error','errno':exc.errno if isinstance(exc,OSError) else None})
                    finally:
                        if fd is not None:os.close(fd)
                row['complete']=True
            finally:os.close(dfd)
    except Budget as e:out['stopped_reason']=str(e)
    except (OSError,ValueError,Refused) as e:
        out['stopped_reason']=str(e) if isinstance(e,Refused) else type(e).__name__
    finally:
        if root is not None:os.close(root)
    out['all_declared_assets_match']=len(out['packages'])==6 and all(p['complete'] and p['matched']==p['listed'] and p['mismatched']==0 for p in out['packages'])
    out['total_assets_checked']=sum(p['checked'] for p in out['packages']);out['total_assets_matched']=sum(p['matched'] for p in out['packages']);out['total_bytes_read']=TOTAL_READ
    out['elapsed_seconds']=round(time.monotonic()-START,3)
    return out
if __name__=='__main__':
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(Budget('hard_time_budget')));signal.alarm(28)
    result=main();signal.alarm(0);print(json.dumps(result,sort_keys=True,separators=(',',':')))
