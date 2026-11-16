
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
