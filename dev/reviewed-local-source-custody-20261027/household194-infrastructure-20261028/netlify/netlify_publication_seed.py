#requirements:
#paramiko==5.1.0
#wmill==1.850.0
"""Fixed-site, pinned-derived-delta digest publisher. No raw corpus inputs accepted."""
import base64, concurrent.futures, hashlib, http.client, io, json, re, shlex, ssl, tempfile, time, threading
SITE='a1df1508-4bb9-4b55-ab1f-88611e456e61'
BASE='/offmenu/data/.offmenu-platform/corpus-recovery-20261028-v1/final-common-publication'
ROOT=BASE+'/publication-delta'
DESCRIPTOR=BASE+'/publication-delta.json'
SECRET='u/admin/offmenu_netlify_api_token'
SSH_SECRET='u/admin/foo_ssh_key_20261027'
HOST_KEY='AAAAC3NzaC1lZDI1NTE5AAAAIAgv17VNww/UZBfIohmz0jg0Xmim5s8FJuPyi4L9qZ0H'
class Stop(Exception):pass

def sha(value,n=64):return isinstance(value,str) and bool(re.fullmatch('[0-9a-f]{'+str(n)+'}',value))
def valid_path(path):
    return isinstance(path,str) and path.startswith('/') and not any(p in ('','..','.') for p in path[1:].split('/')) and not any(c in path for c in ('\\','\x00','\r','\n','?','#'))
def allowed_delta(path):
    return path in ('/index.html','/recipes/manifest.json','/common-data/manifest.json','/common-data/manifest.json.sha256','/common-data/manifest-checksums.json','/common-data/schema.json','/common-data/contract.json','/common-data/source-mappings.json') or path.startswith('/common-data/releases/common-corpus-expanded-20261014/') or (path.startswith('/common-data/releases/') and path.endswith('/manifest.json.sha256'))

def api(token,method,path,body=None):
    from urllib.parse import quote
    fixed='/api/v1/sites/'+SITE
    if not (method=='GET' and (path in (fixed,fixed+'/files',fixed+'/deploys') or re.fullmatch(r'/api/v1/deploys/[0-9a-f]{24}',path)) or method=='POST' and path==fixed+'/deploys' or method=='PUT' and path.startswith('/api/v1/deploys/') and '/files/' in path):raise Stop('api_scope')
    conn=http.client.HTTPSConnection('api.netlify.com',timeout=120,context=ssl.create_default_context())
    headers={'Authorization':'Bearer '+token,'Accept':'application/json'}
    if isinstance(body,dict):body=json.dumps(body,separators=(',',':')).encode();headers['Content-Type']='application/json'
    elif body is not None:
        headers['Content-Type']='application/octet-stream'
        pos=body.tell();body.seek(0,2);headers['Content-Length']=str(body.tell()-pos);body.seek(pos)
    try:
        conn.request(method,path,body,headers);r=conn.getresponse();data=r.read(128*1024*1024+1)
        if len(data)>128*1024*1024:raise Stop('api_response_size')
        if not 200<=r.status<300:raise Stop('netlify_http_'+str(r.status))
        return json.loads(data) if data else {}
    finally:conn.close()

def ssh():
    import paramiko,wmill
    client=paramiko.SSHClient();key=paramiko.Ed25519Key(data=base64.b64decode(HOST_KEY));client.get_host_keys().add('192.168.1.3','ssh-ed25519',key);client.set_missing_host_key_policy(paramiko.RejectPolicy())
    private=paramiko.Ed25519Key.from_private_key(io.StringIO(wmill.get_variable(SSH_SECRET)))
    client.connect('192.168.1.3',port=22,username='offmenu-wm',pkey=private,allow_agent=False,look_for_keys=False,timeout=30,banner_timeout=30,auth_timeout=30)
    return client

def fetch(client,path,size,sha256,sha1=None):
    # Remote read is confined to exact pinned derived files; refuse symlinks at every component.
    code="import os,sys,stat\np="+repr(path)+"\nfd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)\ntry:\n for part in p.strip('/').split('/')[:-1]:\n  new=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=new\n f=os.open(p.rsplit('/',1)[1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)\n s=os.fstat(f);assert stat.S_ISREG(s.st_mode) and s.st_size=="+str(size)+"\n with os.fdopen(f,'rb') as source:\n  while True:\n   b=source.read(1048576)\n   if not b:break\n   sys.stdout.buffer.write(b)\nfinally:os.close(fd)"
    command='python3 -c '+shlex.quote(code)
    ch=client.get_transport().open_session(timeout=30);ch.settimeout(120);ch.exec_command('offmenu-exec-v1');ch.sendall(json.dumps({'command':command}).encode());ch.shutdown_write()
    output=tempfile.TemporaryFile();h=hashlib.sha256();h1=hashlib.sha1();count=0;deadline=time.monotonic()+1800
    try:
        while True:
            if time.monotonic()>deadline:raise Stop('derived_transfer_timeout')
            if ch.recv_ready():
                b=ch.recv(1048576);count+=len(b)
                if count>size:raise Stop('derived_size_mismatch')
                output.write(b);h.update(b);h1.update(b)
            if ch.recv_stderr_ready():ch.recv_stderr(65536) # never emit private remote diagnostics
            if ch.exit_status_ready() and not ch.recv_ready():break
            time.sleep(.001)
        if ch.recv_exit_status()!=0 or count!=size or h.hexdigest()!=sha256 or sha1 and h1.hexdigest()!=sha1:raise Stop('derived_digest_or_read_failure')
        output.seek(0);return output
    except Exception:output.close();raise
    finally:ch.close()

def validate_descriptor(d,proof_sha,assembly_sha):
    if d.get('schemaVersion')!='offmenu-netlify-derived-delta/1' or d.get('siteId')!=SITE:raise Stop('descriptor_scope')
    if d.get('qualificationSha256')!=proof_sha or d.get('assemblyManifestSha256')!=assembly_sha:raise Stop('candidate_pin_mismatch')
    if d.get('sourceCount')!=22 or d.get('sourceRecordTotal')!=22574390:raise Stop('candidate_coverage_mismatch')
    files={}
    for f in d.get('files',[]):
        p=f.get('path')
        if not valid_path(p) or not allowed_delta(p) or p in files or not sha(f.get('sha256')) or not sha(f.get('sha1'),40) or type(f.get('bytes')) is not int or f['bytes']<0:raise Stop('delta_entry_invalid')
        files[p]=f
    if not {'/index.html','/recipes/manifest.json','/common-data/manifest.json','/common-data/manifest-checksums.json'}<=files.keys():raise Stop('delta_incomplete')
    return files

def inventory(token,expected):
    site=api(token,'GET','/api/v1/sites/'+SITE)
    if site.get('id')!=SITE or site.get('name')!='offmenu-corpus' or (site.get('published_deploy') or {}).get('id')!=expected:raise Stop('base_deploy_changed')
    result={}
    for f in api(token,'GET','/api/v1/sites/'+SITE+'/files'):
        p=f.get('path');s=f.get('sha')
        if not valid_path(p) or p in result or not sha(s,40):raise Stop('inventory_invalid')
        result[p]=s
    if (api(token,'GET','/api/v1/sites/'+SITE).get('published_deploy') or {}).get('id')!=expected:raise Stop('base_deploy_changed')
    return result

def journal(client,descriptor,event,create=False,verify_deploy=None):
    if not sha(descriptor):raise Stop('journal_pin_invalid')
    path=BASE+'/.netlify-publish-'+descriptor+'.jsonl'
    record=(json.dumps(event,separators=(',',':'))+'\n').encode()
    code="import os,base64\nfd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)\nfor part in "+repr(BASE.strip('/').split('/'))+":\n new=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=new\nf=os.open("+repr(path.rsplit('/',1)[1])+",os.O_WRONLY|os.O_NOFOLLOW|os.O_NONBLOCK|"+('os.O_CREAT|os.O_EXCL' if create else 'os.O_APPEND')+",0o600,dir_fd=fd)\nb=base64.b64decode("+repr(base64.b64encode(record).decode())+");assert os.write(f,b)==len(b);os.fsync(f);os.close(f);os.fsync(fd);os.close(fd)"
    if verify_deploy is not None:
        if not re.fullmatch('[0-9a-f]{24}',verify_deploy):raise Stop('resume_deploy_invalid')
        check="r=os.open("+repr(path.rsplit('/',1)[1])+",os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)\nimport json\nwith os.fdopen(r) as stream:records=[json.loads(line) for line in stream]\nassert any(x.get('event')=='deploy_created' and x.get('deploy_id')=="+repr(verify_deploy)+" for x in records)\n"
        code=code.replace("f=os.open(",check+"f=os.open(",1)
    ch=client.get_transport().open_session(timeout=30);ch.settimeout(120);ch.exec_command('offmenu-exec-v1');ch.sendall(json.dumps({'command':'python3 -c '+shlex.quote(code)}).encode());ch.shutdown_write()
    try:
        deadline=time.monotonic()+120
        while not ch.exit_status_ready():
            if ch.recv_ready():ch.recv(65536)
            if ch.recv_stderr_ready():ch.recv_stderr(65536)
            if time.monotonic()>deadline:raise Stop('journal_outcome_ambiguous_reconcile_only')
            time.sleep(.01)
        if ch.recv_exit_status()!=0:raise Stop('journal_exists_or_failed_reconcile_only')
    finally:ch.close()


def remote_safe(client,code):
    ch=client.get_transport().open_session(timeout=30);ch.settimeout(120);ch.exec_command('offmenu-exec-v1')
    request=json.dumps({'command':'python3 -c '+shlex.quote(code)}).encode()
    if len(request)>60000:raise Stop('seed_request_limit')
    ch.sendall(request);ch.shutdown_write();deadline=time.monotonic()+120
    try:
        while not ch.exit_status_ready():
            if ch.recv_ready():ch.recv(65536)
            if ch.recv_stderr_ready():ch.recv_stderr(65536)
            if time.monotonic()>deadline:raise Stop('seed_write_timeout')
            time.sleep(.01)
        if ch.recv_exit_status()!=0:raise Stop('seed_write_failed')
    finally:ch.close()

def write_seed(client,path,data):
    # Fixed derived seed subtree only. No arbitrary filesystem writes or symlink following.
    if not valid_path(path):raise Stop('seed_path_invalid')
    parts=(BASE+'/publication-seed'+path).strip('/').split('/')
    prefix="import os,base64,hashlib,stat\nfd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)\nfor part in "+repr(parts[:-1])+":\n try:os.mkdir(part,0o700,dir_fd=fd)\n except FileExistsError:pass\n new=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=new\n"
    # Exclusive creation refuses stale seeds instead of silently replacing a candidate.
    remote_safe(client,prefix+"f=os.open("+repr(parts[-1])+",os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_NONBLOCK,0o600,dir_fd=fd);os.fsync(f);os.close(f);os.fsync(fd);os.close(fd)")
    for offset in range(0,len(data),24000):
        chunk=data[offset:offset+24000]
        code=prefix+"f=os.open("+repr(parts[-1])+",os.O_WRONLY|os.O_APPEND|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd);assert stat.S_ISREG(os.fstat(f).st_mode);assert os.fstat(f).st_size=="+str(offset)+"\nb=base64.b64decode("+repr(base64.b64encode(chunk).decode())+");assert os.write(f,b)==len(b);os.fsync(f);os.close(f);os.fsync(fd);os.close(fd)"
        remote_safe(client,code)
    remote_safe(client,prefix+"f=os.open("+repr(parts[-1])+",os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd);assert stat.S_ISREG(os.fstat(f).st_mode)\nwith os.fdopen(f,'rb') as r:assert hashlib.sha256(r.read()).hexdigest()=="+repr(hashlib.sha256(data).hexdigest())+"\nos.close(fd)")

def main(base_deploy_id:str='',qualification_sha256:str='',qualification_bytes:int=0):
    """Populate public metadata-only seed after release owner supplies final proof. Does not deploy Netlify."""
    client=None
    try:
        import wmill
        if not re.fullmatch('[0-9a-f]{24}',base_deploy_id) or not sha(qualification_sha256) or type(qualification_bytes)is not int or not 0<qualification_bytes<=128*1024*1024:raise Stop('proof_arguments')
        client=ssh()
        with fetch(client,BASE+'/global-qualification.json',qualification_bytes,qualification_sha256) as f:proof=json.load(f)
        if proof.get('status')!='all-packages-streamed-global-identities-references-and-provenance-checked' or proof.get('packageCount')!=8:raise Stop('proof_incomplete')
        token=wmill.get_variable(SECRET);current=inventory(token,base_deploy_id)
        paths=['/manifest.json','/recipes/manifest.json','/index.html']+[p for p in current if p.startswith('/common-data/releases/') and p.endswith('/manifest.json')]
        receipt={'siteId':SITE,'baseDeployId':base_deploy_id,'qualificationSha256':qualification_sha256,'files':[]}
        from urllib.parse import quote
        for path in sorted(set(paths)):
            if path not in current:raise Stop('base_metadata_missing')
            conn=http.client.HTTPSConnection('offmenu-corpus.netlify.app',timeout=120,context=ssl.create_default_context())
            try:
                conn.request('GET',quote(path,safe='/'));r=conn.getresponse();data=r.read(64*1024*1024+1)
                if r.status!=200 or len(data)>64*1024*1024 or hashlib.sha1(data).hexdigest()!=current[path]:raise Stop('public_seed_digest_mismatch')
            finally:conn.close()
            write_seed(client,path,data);receipt['files'].append({'path':path,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
        if (api(token,'GET','/api/v1/sites/'+SITE).get('published_deploy') or {}).get('id')!=base_deploy_id:raise Stop('base_deploy_changed')
        write_seed(client,'/seed-receipt.json',(json.dumps(receipt,separators=(',',':'))+'\n').encode())
        return {'status':'public_metadata_seed_prepared','site_id':SITE,'base_deploy_id':base_deploy_id,'seed_files':len(receipt['files']),'netlify_mutations':0,'credential_returned':False}
    except Stop as exc:return {'status':'blocked','reason':str(exc),'credential_returned':False}
    except Exception:return {'status':'blocked','reason':'private_seed_transport_failure','credential_returned':False}
    finally:
        if client:client.close()
