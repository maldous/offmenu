#requirements:
#paramiko==5.1.0
#wmill==1.850.0
"""Fixed-site NorthStar additive candidate sidecars only. No base aliases or app activation."""
import base64, concurrent.futures, hashlib, http.client, io, json, re, shlex, ssl, tempfile, time, threading, queue
SITE='a1df1508-4bb9-4b55-ab1f-88611e456e61'
BASE='/offmenu/data/.offmenu-platform/corpus-recovery-20261028-v1/final-common-publication'
ROOT=BASE+'/source-barcode-index-publication-delta'
DESCRIPTOR=BASE+'/source-barcode-index-publication-delta.json'
SECRET='u/admin/offmenu_netlify_api_token'
SSH_SECRET='u/admin/foo_ssh_key_20261027'
HOST_KEY='AAAAC3NzaC1lZDI1NTE5AAAAIAgv17VNww/UZBfIohmz0jg0Xmim5s8FJuPyi4L9qZ0H'
UPLOAD_WORKERS=5
class Stop(Exception):pass

def sha(value,n=64):return isinstance(value,str) and bool(re.fullmatch('[0-9a-f]{'+str(n)+'}',value))
def valid_path(path):
    return isinstance(path,str) and path.startswith('/') and not any(p in ('','..','.') for p in path[1:].split('/')) and not any(c in path for c in ('\\','\x00','\r','\n','?','#'))
PREFIX='/common-data/derived-releases/source-barcode-index-v1-20261029/'
EXPECTED_PATHS={PREFIX+'manifest.json'}|{PREFIX+'shards/'+format(i,'02x')+'.json.gz' for i in range(256)}
BASE_MANIFEST_PATH='/common-data/releases/common-corpus-expanded-20261014/manifest.json'
def allowed_delta(path):
    return isinstance(path,str) and path in EXPECTED_PATHS

def verify_served_base(expected_sha):
    c=http.client.HTTPSConnection('offmenu-corpus.netlify.app',timeout=120,context=ssl.create_default_context())
    try:
        c.request('GET',BASE_MANIFEST_PATH);r=c.getresponse();data=r.read(128*1024*1024+1)
        if r.status!=200 or len(data)>128*1024*1024 or hashlib.sha256(data).hexdigest()!=expected_sha:raise Stop('served_base_dependency_mismatch')
    finally:c.close()

class RateLimited(Exception):
    def __init__(self,delay):self.delay=delay
_RATE_LOCK=threading.Lock()
_RATE_NEXT=0.0
_RATE_COOLDOWN=0.0

def rate_delay(response):
    from email.utils import parsedate_to_datetime
    delays=[60.0]
    value=response.getheader('Retry-After')
    if value:
        try:delays.append(float(value))
        except ValueError:
            try:delays.append(parsedate_to_datetime(value).timestamp()-time.time())
            except (ValueError,TypeError,OverflowError):pass
    value=response.getheader('X-RateLimit-Reset')
    if value:
        try:delays.append(float(value)-time.time())
        except ValueError:pass
    return max(delays)+1.0

def rate_wait():
    global _RATE_NEXT
    while True:
        with _RATE_LOCK:
            now=time.monotonic();delay=max(_RATE_NEXT,_RATE_COOLDOWN)-now
            if delay<=0:
                # Netlify documents 500 requests/minute. Retain parallel bodies,
                # but leave a small allowance for independent status readers.
                _RATE_NEXT=now+60.0/480.0
                return
        time.sleep(delay)

def api(token,method,path,body=None):
    global _RATE_COOLDOWN
    safe_retry=method=='GET' or (method=='PUT' and path.startswith('/api/v1/deploys/') and '/files/' in path)
    position=body.tell() if hasattr(body,'tell') else None
    for attempt in range(5):
        rate_wait()
        if position is not None:body.seek(position)
        try:return api_once(token,method,path,body)
        except RateLimited as exc:
            with _RATE_LOCK:_RATE_COOLDOWN=max(_RATE_COOLDOWN,time.monotonic()+exc.delay)
            if not safe_retry or attempt==4:raise Stop('netlify_http_429')
    raise Stop('netlify_http_429')

_HTTP_LOCAL=threading.local()
_HTTP_LOCK=threading.Lock()
_HTTP_CONNECTIONS=set()

def close_file_connection(conn):
    with _HTTP_LOCK:_HTTP_CONNECTIONS.discard(conn)
    conn.close()
    if getattr(_HTTP_LOCAL,'connection',None) is conn:_HTTP_LOCAL.connection=None

def file_connection():
    now=time.monotonic();conn=getattr(_HTTP_LOCAL,'connection',None)
    if conn is not None and (now-_HTTP_LOCAL.last_used>5 or now-_HTTP_LOCAL.created>120 or _HTTP_LOCAL.uses>=128):
        close_file_connection(conn);conn=None
    if conn is None:
        conn=http.client.HTTPSConnection('api.netlify.com',timeout=120,context=ssl.create_default_context())
        _HTTP_LOCAL.connection=conn;_HTTP_LOCAL.created=now;_HTTP_LOCAL.uses=0
        with _HTTP_LOCK:_HTTP_CONNECTIONS.add(conn)
    return conn

def close_http_connections():
    with _HTTP_LOCK:connections=list(_HTTP_CONNECTIONS);_HTTP_CONNECTIONS.clear()
    for conn in connections:conn.close()

def api_once(token,method,path,body=None):
    from urllib.parse import quote
    fixed='/api/v1/sites/'+SITE
    if not (method=='GET' and (path in (fixed,fixed+'/files',fixed+'/deploys') or re.fullmatch(r'/api/v1/deploys/[0-9a-f]{24}',path)) or method=='POST' and path==fixed+'/deploys' or method=='PUT' and re.fullmatch(re.escape(fixed)+r'/deploys/[0-9a-f]{24}',path) or method=='PUT' and path.startswith('/api/v1/deploys/') and '/files/' in path):raise Stop('api_scope')
    pooled=method=='PUT' and path.startswith('/api/v1/deploys/') and '/files/' in path
    conn=file_connection() if pooled else http.client.HTTPSConnection('api.netlify.com',timeout=120,context=ssl.create_default_context());keep=False
    headers={'Authorization':'Bearer '+token,'Accept':'application/json'}
    if isinstance(body,dict):body=json.dumps(body,separators=(',',':')).encode();headers['Content-Type']='application/json'
    elif body is not None:
        headers['Content-Type']='application/octet-stream'
        pos=body.tell();body.seek(0,2);headers['Content-Length']=str(body.tell()-pos);body.seek(pos)
    try:
        conn.request(method,path,body,headers);r=conn.getresponse();data=r.read(128*1024*1024+1)
        if len(data)>128*1024*1024:raise Stop('api_response_size')
        if r.status==429:
            delay=rate_delay(r)
            print(json.dumps({'event':'provider_rate_limit','endpoint_kind':'file_upload' if '/files/' in path else 'control','wait_seconds':delay,'headers':{k:r.getheader(k) for k in ('Retry-After','X-RateLimit-Limit','X-RateLimit-Remaining','X-RateLimit-Reset')}}),flush=True)
            raise RateLimited(delay)
        if not 200<=r.status<300:raise Stop('netlify_http_'+str(r.status))
        result=json.loads(data) if data else {}
        keep=pooled and not r.will_close
        if keep:_HTTP_LOCAL.last_used=time.monotonic();_HTTP_LOCAL.uses+=1
        return result
    finally:
        if not keep:
            if pooled:close_file_connection(conn)
            else:conn.close()

def ssh():
    import paramiko,wmill
    client=paramiko.SSHClient();key=paramiko.Ed25519Key(data=base64.b64decode(HOST_KEY));client.get_host_keys().add('192.168.1.3','ssh-ed25519',key);client.set_missing_host_key_policy(paramiko.RejectPolicy())
    private=paramiko.Ed25519Key.from_private_key(io.StringIO(wmill.get_variable(SSH_SECRET)))
    client.connect('192.168.1.3',port=22,username='offmenu-wm',pkey=private,allow_agent=False,look_for_keys=False,timeout=30,banner_timeout=30,auth_timeout=30)
    return client

def open_private_channel(client):
    import paramiko
    for attempt in range(7):
        try:return client.get_transport().open_session(timeout=30)
        except paramiko.ChannelException as exc:
            # SSH OPEN_FAILURE code 2 means no channel/command was created.
            # A just-closed MaxSessions=1 slot can still be retiring remotely.
            if exc.code!=2 or attempt==6:raise
            time.sleep(.1*(2**attempt))


def fetch(client,path,size,sha256,sha1=None):
    # Remote read is confined to exact pinned derived files; refuse symlinks at every component.
    code="import os,sys,stat\np="+repr(path)+"\nfd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)\ntry:\n for part in p.strip('/').split('/')[:-1]:\n  new=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=new\n f=os.open(p.rsplit('/',1)[1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)\n s=os.fstat(f);assert stat.S_ISREG(s.st_mode) and s.st_size=="+str(size)+"\n with os.fdopen(f,'rb') as source:\n  while True:\n   b=source.read(1048576)\n   if not b:break\n   sys.stdout.buffer.write(b)\nfinally:os.close(fd)"
    command='python3 -c '+shlex.quote(code)
    ch=None;output=None
    try:
        ch=open_private_channel(client);ch.settimeout(120);ch.exec_command('offmenu-exec-v1');ch.sendall(json.dumps({'command':command}).encode());ch.shutdown_write()
        output=tempfile.TemporaryFile();h=hashlib.sha256();h1=hashlib.sha1();count=0;deadline=time.monotonic()+1800
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
    except Exception:
        if output is not None:output.close()
        raise
    finally:
        if ch is not None:ch.close()

def new_read_lease():
    return {'client':ssh(),'opened':time.monotonic(),'bytes':0,'uses':0}

def fetch_leased(lease,path,size,sha256,sha1=None):
    import paramiko
    # A lease is exclusively held by one upload task. Replace before rekey-sized
    # traffic or long idle lifetimes; never change host policy or cryptography.
    for attempt in range(2):
        if lease['client'] is None or time.monotonic()-lease['opened']>=600 or lease['bytes']+size>128*1024*1024 or lease['uses']>=128:
            if lease['client'] is not None:lease['client'].close()
            lease['client']=None
            lease.update(new_read_lease())
        try:
            body=fetch(lease['client'],path,size,sha256,sha1)
            lease['bytes']+=size;lease['uses']+=1
            return body
        except paramiko.SSHException:
            lease['client'].close();lease['client']=None
            # Only an immutable, hash-checked private read is repeated. No API
            # request has been issued for this body and no write is replayed.
            if attempt:raise
    raise Stop('private_read_retry_exhausted')

def validate_descriptor(d,proof_sha,assembly_sha):
    if not isinstance(d,dict) or d.get('schemaVersion')!='offmenu-netlify-source-barcode-index-delta/1' or d.get('siteId')!=SITE:raise Stop('descriptor_scope')
    if d.get('consumerProofSha256')!=proof_sha or d.get('producerManifestSha256')!=assembly_sha:raise Stop('candidate_pin_mismatch')
    if d.get('semanticStatus')!='candidate-not-admitted' or d.get('acceptedIdentityJoins')!=0 or d.get('servedAppQueries')!=0:raise Stop('candidate_semantics_mismatch')
    if not isinstance(d.get('files'),list):raise Stop('delta_entry_invalid')
    files={}
    for f in d['files']:
        if not isinstance(f,dict):raise Stop('delta_entry_invalid')
        p=f.get('path')
        if not valid_path(p) or not allowed_delta(p) or p in files or not sha(f.get('sha256')) or not sha(f.get('sha1'),40) or type(f.get('bytes')) is not int or f['bytes']<0:raise Stop('delta_entry_invalid')
        files[p]=f
    if set(files)!=EXPECTED_PATHS:raise Stop('delta_incomplete')
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
    ch=open_private_channel(client);ch.settimeout(120);ch.exec_command('offmenu-exec-v1');ch.sendall(json.dumps({'command':'python3 -c '+shlex.quote(code)}).encode());ch.shutdown_write()
    try:
        deadline=time.monotonic()+120
        while not ch.exit_status_ready():
            if ch.recv_ready():ch.recv(65536)
            if ch.recv_stderr_ready():ch.recv_stderr(65536)
            if time.monotonic()>deadline:raise Stop('journal_outcome_ambiguous_reconcile_only')
            time.sleep(.01)
        if ch.recv_exit_status()!=0:raise Stop('journal_exists_or_failed_reconcile_only')
    finally:ch.close()

def mutation_epoch(records):
    mutations=[r for r in records if r.get('event') in ('create_intent','deploy_created','refresh_identical_map_intent','refresh_identical_map_response')]
    return hashlib.sha256(json.dumps(mutations,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def digest_set(values):
    if not isinstance(values,list) or any(not isinstance(v,str) or not re.fullmatch('[0-9a-f]{40}',v) for v in values):raise ValueError('checkpoint_digest_invalid')
    if len(values)!=len(set(values)):raise ValueError('checkpoint_duplicate_digest')
    return set(values)

def inventory_pin(values):
    return hashlib.sha256(('\n'.join(sorted(values))+'\n').encode()).hexdigest()

def checkpoint_records(required,deploy,descriptor,epoch):
    values=sorted(required);digest_set(values)
    header={'event':'required_checkpoint_start','deploy_id':deploy,'descriptor_sha256':descriptor,'mutation_epoch':epoch,'count':len(values),'inventory_sha256':inventory_pin(values)}
    yield header
    for i in range(0,len(values),1000):yield {'event':'required_checkpoint_part','offset':i,'digests':values[i:i+1000]}
    yield {'event':'required_checkpoint_complete','inventory_sha256':header['inventory_sha256']}

def recover_checkpoint(records,deploy,descriptor):
    epoch=mutation_epoch(records);start=None
    for i,r in enumerate(records):
        if r.get('event')=='required_checkpoint_start':start=i
    if start is None:return None
    h=records[start]
    if h.get('deploy_id')!=deploy or h.get('descriptor_sha256')!=descriptor or h.get('mutation_epoch')!=epoch:raise ValueError('checkpoint_generation_mismatch')
    values=[];complete=False;accepted=set()
    for r in records[start+1:]:
        event=r.get('event')
        if event=='required_checkpoint_part':
            if complete or r.get('offset')!=len(values):raise ValueError('checkpoint_part_order')
            digest_set(r.get('digests'));values.extend(r['digests'])
        elif event=='required_checkpoint_complete':
            if complete or r.get('inventory_sha256')!=h.get('inventory_sha256'):raise ValueError('checkpoint_complete_invalid')
            required=digest_set(values)
            if len(required)!=h.get('count') or inventory_pin(values)!=h.get('inventory_sha256'):raise ValueError('checkpoint_inventory_invalid')
            complete=True
        elif event=='accepted_digest_batch':
            if not complete or r.get('deploy_id')!=deploy or r.get('descriptor_sha256')!=descriptor or r.get('inventory_sha256')!=h.get('inventory_sha256'):raise ValueError('checkpoint_acceptance_binding')
            batch=digest_set(r.get('digests'))
            if not batch<=required:raise ValueError('checkpoint_acceptance_outside_inventory')
            accepted.update(batch)
    if not complete:raise ValueError('checkpoint_incomplete_reconcile_only')
    return {'required':required,'accepted':accepted,'inventory_sha256':h['inventory_sha256'],'mutation_epoch':epoch}

def read_private_journal(client,descriptor):
    if not sha(descriptor):raise Stop('journal_pin_invalid')
    name='.netlify-publish-'+descriptor+'.jsonl'
    code="import os,sys,stat\nfd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)\ntry:\n for part in "+repr(BASE.strip('/').split('/'))+":\n  new=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=new\n f=os.open("+repr(name)+",os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)\n st=os.fstat(f);assert stat.S_ISREG(st.st_mode) and st.st_size<=16*1024*1024\n with os.fdopen(f,'rb') as stream:sys.stdout.buffer.write(stream.read(16*1024*1024+1))\nfinally:os.close(fd)"
    ch=None;out=bytearray()
    try:
        ch=open_private_channel(client);ch.settimeout(120);ch.exec_command('offmenu-exec-v1');ch.sendall(json.dumps({'command':'python3 -c '+shlex.quote(code)}).encode());ch.shutdown_write();deadline=time.monotonic()+120
        while True:
            if time.monotonic()>deadline:raise Stop('journal_read_timeout')
            if ch.recv_ready():
                out.extend(ch.recv(65536))
                if len(out)>16*1024*1024:raise Stop('journal_read_size')
            if ch.recv_stderr_ready():ch.recv_stderr(65536)
            if ch.exit_status_ready() and not ch.recv_ready():break
            time.sleep(.001)
        if ch.recv_exit_status()!=0 or not out.endswith(b'\n'):raise Stop('journal_read_or_partial_record')
        records=[json.loads(line) for line in out.splitlines()]
        if any(not isinstance(r,dict) for r in records):raise Stop('journal_record_invalid')
        return records
    finally:
        if ch is not None:ch.close()

class AcceptanceWriter:
    def __init__(self,descriptor,deploy,inventory):
        self.descriptor=descriptor;self.deploy=deploy;self.inventory=inventory;self.pending=[];self.lock=threading.Lock();self.client=None;self.opened=0;self.failed=False
    def _flush(self):
        if self.failed:raise Stop('checkpoint_write_ambiguous_reconcile_only')
        if not self.pending:return
        if self.client is None or time.monotonic()-self.opened>=600:
            if self.client is not None:self.client.close()
            self.client=None;self.client=ssh();self.opened=time.monotonic()
        try:
            journal(self.client,self.descriptor,{'event':'accepted_digest_batch','deploy_id':self.deploy,'descriptor_sha256':self.descriptor,'inventory_sha256':self.inventory,'digests':list(self.pending)})
        except Exception:
            self.failed=True
            raise
        self.pending.clear()
    def accepted(self,digest):
        with self.lock:
            if self.failed:raise Stop('checkpoint_write_ambiguous_reconcile_only')
            self.pending.append(digest)
            if len(self.pending)>=25:self._flush()
    def close(self):
        try:
            with self.lock:
                if not self.failed:self._flush()
        finally:
            if self.client is not None:self.client.close();self.client=None

def run_bounded_uploads(upload,required):
    # At most UPLOAD_WORKERS bodies are in flight. Observe any failure promptly and never
    # enqueue the rest of a 24k-file inventory after an operation fails.
    pending=set();items=iter(required)
    with concurrent.futures.ThreadPoolExecutor(max_workers=UPLOAD_WORKERS) as pool:
        for digest in items:
            pending.add(pool.submit(upload,digest))
            if len(pending)==UPLOAD_WORKERS:break
        try:
            while pending:
                done,pending=concurrent.futures.wait(pending,return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:future.result()
                for _ in done:
                    try:digest=next(items)
                    except StopIteration:break
                    pending.add(pool.submit(upload,digest))
        except Exception as exc:
            print(json.dumps({'event':'upload_failure','error_type':type(exc).__name__}),flush=True)
            for future in pending:future.cancel()
            raise


def main(operation:str='prepare',descriptor_sha256:str='',descriptor_bytes:int=0,consumer_proof_sha256:str='',producer_manifest_sha256:str='',base_deploy_id:str='',deploy_id:str='',served_base_manifest_sha256:str=''):
    """Upload only after release owner accepts exact descriptor and qualification pins. prepare is read-only. status inspects one fixed-site deploy."""
    client=None;created=None;create_attempted=False;refresh_required=None;checkpoint=None
    try:
        import wmill
        token=wmill.get_variable(SECRET)
        if operation=='reconcile':
            if not sha(descriptor_sha256):raise Stop('descriptor_pin_invalid')
            items=api(token,'GET','/api/v1/sites/'+SITE+'/deploys')
            matches=[{'deploy_id':d.get('id'),'state':d.get('state')} for d in items if d.get('site_id')==SITE and d.get('title')=='OffMenu NorthStar candidate '+descriptor_sha256]
            return {'status':'reconciliation_only','matches':matches,'netlify_mutations':0,'note':'No create retry authorized by this result; inspect durable intent and matching deployment.'}
        if operation=='status':
            if not re.fullmatch('[0-9a-f]{24}',deploy_id):raise Stop('deploy_id_invalid')
            d=api(token,'GET','/api/v1/deploys/'+deploy_id)
            if d.get('site_id')!=SITE:raise Stop('deploy_site_mismatch')
            return {'site_id':SITE,'deploy_id':deploy_id,'state':d.get('state'),'required_count':len(d.get('required') or []),'credential_returned':False}
        if operation not in ('prepare','upload','resume','refresh_existing') or not all(sha(x) for x in (descriptor_sha256,consumer_proof_sha256,producer_manifest_sha256,served_base_manifest_sha256)) or type(descriptor_bytes)is not int or not 0<descriptor_bytes<=128*1024*1024 or not re.fullmatch('[0-9a-f]{24}',base_deploy_id):raise Stop('candidate_arguments_invalid')
        client=ssh()
        with fetch(client,DESCRIPTOR,descriptor_bytes,descriptor_sha256) as f:d=json.load(f)
        files=validate_descriptor(d,consumer_proof_sha256,producer_manifest_sha256)
        if d.get('baseDeployId')!=base_deploy_id:raise Stop('descriptor_base_mismatch')
        if d.get('servedBaseManifestSha256')!=served_base_manifest_sha256:raise Stop('base_pin_mismatch')
        verify_served_base(served_base_manifest_sha256)
        current=inventory(token,base_deploy_id);merged=dict(current)
        for path,f in files.items():
            if path.startswith(PREFIX) and path in current and current[path]!=f['sha1']:raise Stop('immutable_release_collision')
            merged[path]=f['sha1']
        receipt={'site_id':SITE,'base_deploy_id':base_deploy_id,'descriptor_sha256':descriptor_sha256,'preserved_current_files':len(current),'delta_files':len(files),'merged_files':len(merged),'semantic_status':'candidate-not-admitted','served_base_manifest_sha256':served_base_manifest_sha256,'accepted_identity_joins':0,'served_app_queries':0,'credential_returned':False}
        if operation=='prepare':return dict(receipt,status='prepared_no_mutation',netlify_mutations=0)
        # Every required body is checked before it reaches Netlify. Existing digest reuse preserves unrelated modules.
        if operation in ('resume','refresh_existing'):
            journal(client,descriptor_sha256,{'event':'resume_intent','deploy_id':deploy_id},verify_deploy=deploy_id)
            created=api(token,'GET','/api/v1/deploys/'+deploy_id)
        else:
            if (api(token,'GET','/api/v1/sites/'+SITE).get('published_deploy') or {}).get('id')!=base_deploy_id:raise Stop('base_deploy_changed')
            journal(client,descriptor_sha256,{'event':'create_intent','site_id':SITE,'base_deploy_id':base_deploy_id,'descriptor_sha256':descriptor_sha256},create=True)
            create_attempted=True
            created=api(token,'POST','/api/v1/sites/'+SITE+'/deploys',{'files':merged,'draft':False,'async':True,'title':'OffMenu NorthStar candidate '+descriptor_sha256})
        deploy=created.get('id')
        if not re.fullmatch('[0-9a-f]{24}',deploy or '') or created.get('site_id')!=SITE or created.get('title')!='OffMenu NorthStar candidate '+descriptor_sha256:raise Stop('created_deploy_identity')
        if operation=='upload':journal(client,descriptor_sha256,{'event':'deploy_created','deploy_id':deploy,'site_id':SITE})
        if operation=='upload' and created.get('required'):
            if not isinstance(created['required'],list) or any(not isinstance(x,str) or not re.fullmatch('[0-9a-f]{40}',x) for x in created['required']):raise Stop('created_required_invalid')
            refresh_required=created['required']
        if operation in ('resume','refresh_existing'):
            try:checkpoint=recover_checkpoint(read_private_journal(client,descriptor_sha256),deploy,descriptor_sha256)
            except ValueError as exc:raise Stop(str(exc))
            if operation=='refresh_existing' and checkpoint is not None:raise Stop('checkpoint_available_use_resume_not_refresh')
        if operation=='refresh_existing':
            if created.get('state') not in ('prepared','uploading'):raise Stop('refresh_state_not_incomplete')
            if (api(token,'GET','/api/v1/sites/'+SITE).get('published_deploy') or {}).get('id')!=base_deploy_id:raise Stop('base_deploy_changed')
            journal(client,descriptor_sha256,{'event':'refresh_identical_map_intent','deploy_id':deploy,'descriptor_sha256':descriptor_sha256},verify_deploy=deploy)
            updated=api(token,'PUT','/api/v1/sites/'+SITE+'/deploys/'+deploy,{'files':merged,'draft':False,'async':True,'title':'OffMenu NorthStar candidate '+descriptor_sha256})
            if updated.get('id')!=deploy or updated.get('site_id')!=SITE or updated.get('title')!='OffMenu NorthStar candidate '+descriptor_sha256:raise Stop('refresh_identity_mismatch')
            if updated.get('required'):
                if not isinstance(updated['required'],list) or any(not isinstance(x,str) or not re.fullmatch('[0-9a-f]{40}',x) for x in updated['required']):raise Stop('refresh_required_invalid')
                refresh_required=updated['required']
            journal(client,descriptor_sha256,{'event':'refresh_identical_map_response','deploy_id':deploy,'state':updated.get('state')})
        for _ in range(180):
            state=api(token,'GET','/api/v1/deploys/'+deploy)
            if state.get('site_id')!=SITE:raise Stop('deploy_site_mismatch')
            if state.get('state')!='preparing':break
            time.sleep(2)
        else:raise Stop('deploy_preparation_timeout')
        if state.get('state') in ('prepared','uploading') and not (state.get('required') or refresh_required or checkpoint):raise Stop('provider_required_inventory_unavailable')
        required=set(state.get('required') or refresh_required or []);bysha={f['sha1']:(p,f) for p,f in files.items()}
        previously_accepted=0
        if checkpoint is not None:
            if state.get('state') not in ('prepared','uploading','ready'):raise Stop('checkpoint_resume_provider_state')
            if required-checkpoint['required']:raise Stop('provider_inventory_changed_reconcile_only')
            if required & checkpoint['accepted']:raise Stop('provider_checkpoint_conflict_reconcile_only')
            required=checkpoint['required']-checkpoint['accepted'];previously_accepted=len(checkpoint['accepted'])
        if required-bysha.keys():raise Stop('server_requires_unavailable_retained_digest')
        if checkpoint is None:
            records=read_private_journal(client,descriptor_sha256)
            epoch=mutation_epoch(records)
            for record in checkpoint_records(required,deploy,descriptor_sha256,epoch):journal(client,descriptor_sha256,record)
            checkpoint={'inventory_sha256':inventory_pin(required),'required':required,'accepted':set()}
        acceptance=AcceptanceWriter(descriptor_sha256,deploy,checkpoint['inventory_sha256'])
        from urllib.parse import quote
        clients=[];available=queue.Queue();progress_lock=threading.Lock();progress={'accepted_digests':0,'accepted_bytes':0};started=time.monotonic()
        print(json.dumps({'event':'upload_inventory','required_digests':len(required),'previously_durably_accepted':previously_accepted,'deploy_id':deploy}),flush=True)
        try:
            # Measured 64 transport + 64 executor threads exhausted the worker's
            # thread allocation. Reuse eight pinned transports with one
            # channel each (installed MaxSessions 1); provider-default upload concurrency, no host change.
            if required:
                for _ in range(8):
                    transfer_client=new_read_lease();clients.append(transfer_client)
                    available.put(transfer_client)
            def upload(digest):
                path,meta=bysha[digest];transfer_client=available.get()
                try:body=fetch_leased(transfer_client,ROOT+path,meta['bytes'],meta['sha256'],digest)
                finally:available.put(transfer_client)
                with body:
                    api(token,'PUT','/api/v1/deploys/'+deploy+'/files/'+quote(path.lstrip('/'),safe='/')+'?size='+str(meta['bytes']),body)
                acceptance.accepted(digest)
                with progress_lock:
                    progress['accepted_digests']+=1;progress['accepted_bytes']+=meta['bytes']
                    if progress['accepted_digests']==1 or (progress['accepted_digests']<=250 and progress['accepted_digests']%25==0) or progress['accepted_digests']%250==0:print(json.dumps(dict(progress,event='upload_progress',remaining_digests=len(required)-progress['accepted_digests'],elapsed_seconds=round(time.monotonic()-started,1))),flush=True)
            run_bounded_uploads(upload,required)
        finally:
            try:acceptance.close()
            finally:
                for transfer_client in clients:
                    if transfer_client['client'] is not None:transfer_client['client'].close()
        final=api(token,'GET','/api/v1/deploys/'+deploy)
        client.close();client=None;client=ssh()
        journal(client,descriptor_sha256,{'event':'upload_completed','deploy_id':deploy,'state':final.get('state')})
        return dict(receipt,status='upload_completed_verify_serving',deploy_id=deploy,state=final.get('state'),uploaded_digests=len(required))
    except Stop as exc:return {'status':'blocked','reason':str(exc),'deploy_id':(created or {}).get('id'),'credential_returned':False}
    except Exception as exc:return {'status':'blocked','reason':'create_outcome_ambiguous_reconcile_only' if create_attempted and not created else 'private_transport_or_sdk_failure','error_type':type(exc).__name__,'deploy_id':(created or {}).get('id'),'credential_returned':False}
    finally:
        close_http_connections()
        if client:client.close()
