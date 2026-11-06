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

def main(operation:str='prepare',descriptor_sha256:str='',descriptor_bytes:int=0,qualification_sha256:str='',assembly_manifest_sha256:str='',base_deploy_id:str='',deploy_id:str=''):
    """Upload only after release owner accepts exact descriptor and qualification pins. prepare is read-only. status inspects one fixed-site deploy."""
    client=None;created=None;create_attempted=False
    try:
        import wmill
        token=wmill.get_variable(SECRET)
        if operation=='reconcile':
            if not sha(descriptor_sha256):raise Stop('descriptor_pin_invalid')
            items=api(token,'GET','/api/v1/sites/'+SITE+'/deploys')
            matches=[{'deploy_id':d.get('id'),'state':d.get('state')} for d in items if d.get('site_id')==SITE and d.get('title')=='OffMenu qualified corpus '+descriptor_sha256]
            return {'status':'reconciliation_only','matches':matches,'netlify_mutations':0,'note':'No create retry authorized by this result; inspect durable intent and matching deployment.'}
        if operation=='status':
            if not re.fullmatch('[0-9a-f]{24}',deploy_id):raise Stop('deploy_id_invalid')
            d=api(token,'GET','/api/v1/deploys/'+deploy_id)
            if d.get('site_id')!=SITE:raise Stop('deploy_site_mismatch')
            return {'site_id':SITE,'deploy_id':deploy_id,'state':d.get('state'),'required_count':len(d.get('required') or []),'credential_returned':False}
        if operation not in ('prepare','upload','resume') or not all(sha(x) for x in (descriptor_sha256,qualification_sha256,assembly_manifest_sha256)) or type(descriptor_bytes)is not int or not 0<descriptor_bytes<=128*1024*1024 or not re.fullmatch('[0-9a-f]{24}',base_deploy_id):raise Stop('candidate_arguments_invalid')
        client=ssh()
        with fetch(client,DESCRIPTOR,descriptor_bytes,descriptor_sha256) as f:d=json.load(f)
        files=validate_descriptor(d,qualification_sha256,assembly_manifest_sha256)
        if d.get('baseDeployId')!=base_deploy_id:raise Stop('descriptor_base_mismatch')
        current=inventory(token,base_deploy_id);merged=dict(current)
        for path,f in files.items():
            if path.startswith('/common-data/releases/') and path in current and current[path]!=f['sha1']:raise Stop('immutable_release_collision')
            merged[path]=f['sha1']
        receipt={'site_id':SITE,'base_deploy_id':base_deploy_id,'descriptor_sha256':descriptor_sha256,'preserved_current_files':len(current),'delta_files':len(files),'merged_files':len(merged),'source_count':22,'source_records':22574390,'credential_returned':False}
        if operation=='prepare':return dict(receipt,status='prepared_no_mutation',netlify_mutations=0)
        # Every required body is checked before it reaches Netlify. Existing digest reuse preserves unrelated modules.
        if operation=='resume':
            journal(client,descriptor_sha256,{'event':'resume_intent','deploy_id':deploy_id},verify_deploy=deploy_id)
            created=api(token,'GET','/api/v1/deploys/'+deploy_id)
        else:
            if (api(token,'GET','/api/v1/sites/'+SITE).get('published_deploy') or {}).get('id')!=base_deploy_id:raise Stop('base_deploy_changed')
            journal(client,descriptor_sha256,{'event':'create_intent','site_id':SITE,'base_deploy_id':base_deploy_id,'descriptor_sha256':descriptor_sha256},create=True)
            create_attempted=True
            created=api(token,'POST','/api/v1/sites/'+SITE+'/deploys',{'files':merged,'draft':False,'async':True,'title':'OffMenu qualified corpus '+descriptor_sha256})
        deploy=created.get('id')
        if not re.fullmatch('[0-9a-f]{24}',deploy or '') or created.get('site_id')!=SITE or created.get('title')!='OffMenu qualified corpus '+descriptor_sha256:raise Stop('created_deploy_identity')
        if operation=='upload':journal(client,descriptor_sha256,{'event':'deploy_created','deploy_id':deploy,'site_id':SITE})
        for _ in range(180):
            state=api(token,'GET','/api/v1/deploys/'+deploy)
            if state.get('site_id')!=SITE:raise Stop('deploy_site_mismatch')
            if state.get('state')!='preparing':break
            time.sleep(2)
        else:raise Stop('deploy_preparation_timeout')
        required=set(state.get('required') or []);bysha={f['sha1']:(p,f) for p,f in files.items()}
        if required-bysha.keys():raise Stop('server_requires_unavailable_retained_digest')
        from urllib.parse import quote
        local=threading.local();clients=[];auth_lock=threading.Lock()
        def init_transfer():
            # Separate authenticated transports avoid SSH MaxSessions per-connection limits.
            # Serialize only authentication, not file transfer or HTTP uploads.
            with auth_lock:
                local.client=ssh();clients.append(local.client)
        def upload(digest):
            path,meta=bysha[digest]
            with fetch(local.client,ROOT+path,meta['bytes'],meta['sha256'],digest) as body:
                api(token,'PUT','/api/v1/deploys/'+deploy+'/files/'+quote(path.lstrip('/'),safe='/')+'?size='+str(meta['bytes']),body)
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=64,initializer=init_transfer) as pool:list(pool.map(upload,required))
        finally:
            for transfer_client in clients:transfer_client.close()
        final=api(token,'GET','/api/v1/deploys/'+deploy)
        journal(client,descriptor_sha256,{'event':'upload_completed','deploy_id':deploy,'state':final.get('state')})
        return dict(receipt,status='upload_completed_verify_serving',deploy_id=deploy,state=final.get('state'),uploaded_digests=len(required))
    except Stop as exc:return {'status':'blocked','reason':str(exc),'deploy_id':(created or {}).get('id'),'credential_returned':False}
    except Exception:return {'status':'blocked','reason':'create_outcome_ambiguous_reconcile_only' if create_attempted and not created else 'private_transport_or_sdk_failure','deploy_id':(created or {}).get('id'),'credential_returned':False}
    finally:
        if client:client.close()
