"""Finite publisher-owner lifecycle; never a caller-selected privileged runner.

Production invoke() runs only as the installed UID984/GID976 custodian. Outer
observe reads the named ORIGINAL receipt and never starts a process or creates
state. The separate fixed prepare request requires a reusable Root-sealed native
policy and only creates a qualified protected admission, never an HTTP effect.
Missing preparation/terminal proof stays held. Installation, exact sudo
permission and mandatory host approval are separate; this module grants none.
"""
import base64
import csv
import ctypes
import io
import fcntl
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import sqlite3
import stat
import subprocess
import sys
import time
from uuid import UUID


INSTALL = Path('/opt/offmenu-publisher')
CONFIG = Path('/etc/offmenu-publisher/config.json')
CLAIM = Path('/var/lib/offmenu-publisher/integration')
ENTRY = INSTALL / 'tools/delivery/native_publisher_invocation.py'
PUBLISHER = INSTALL / 'tools/delivery/github-app-publisher.mjs'
PYTHON = INSTALL / 'venv/bin/python'
NODE = Path('/usr/bin/node')
CLOSURE = INSTALL / 'native-harness-closure.json'
MANIFEST_LIMIT = 16*1024*1024
PUBLIC_CA = 'venv/lib/python3.12/site-packages/certifi/cacert.pem'
LIMIT = 65536
WIRE_LIMIT = 16384
TIMEOUT = 180
ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8',
       'LANGSMITH_TRACING': 'false', 'LANGCHAIN_TRACING_V2': 'false'}
INNER = {'version', 'mode', 'operation_id', 'issue_id', 'project_id', 'owner',
         'unit_sha256', 'packet_sha256', 'source_sha256'}
STATUSES = {'ready', 'pending', 'unknown', 'verified', 'denied', 'failed'}
OWNER_SOURCE = Path('/opt/offmenu-stokowski-current/source')
OWNER_PYTHON = Path('/opt/offmenu-stokowski-current/venv/bin/python')
ACCEPTED = Path('/var/lib/offmenu-publisher/accepted-sources')


class InvocationHold(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise InvocationHold(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def wire(value, limit=LIMIT):
    try:
        raw = json.dumps(value, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=True, allow_nan=False).encode('ascii') + b'\n'
        require(len(raw) <= limit, 'json_size')
        return raw
    except (ValueError, TypeError, RecursionError, OverflowError):
        raise InvocationHold('json_encoding') from None


def fingerprint(value):
    return sha(wire(value, 1048576)[:-1])


def decode(raw, limit=LIMIT):
    require(type(raw) is bytes and 0 < len(raw) <= limit, 'json_size')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate_key')
            result[key] = value
        return result
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                          parse_constant=lambda _: require(False, 'json_number'))
    except (ValueError, UnicodeError, RecursionError):
        raise InvocationHold('json_decode') from None


def exact(value, fields):
    return type(value) is dict and set(value) == set(fields)


def hex64(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def uuid(value):
    try:
        require(type(value) is str and str(UUID(value)) == value and UUID(value).int != 0, 'uuid')
    except (ValueError, AttributeError):
        raise InvocationHold('uuid') from None


def native_policy(config):
    """One Root-sealed reusable delegation, never a packet-supplied grant."""
    p=config.get('native_policy')
    optional={'project_source'} if type(p) is dict and 'project_source' in p else set()
    require(exact(p, {'version','kind','owner','project_ids','controller_runtime',
        'source_head','source_sha256','owner_python_sha256','profiles','automatic_integration_enabled'} | optional), 'native_policy_fields')
    require(type(p['version']) is int and p['version'] == 1
        and p['kind'] == 'native-source-publication-policy-v1'
        and p['owner'] == config['logicalOwner'] and config['version'] == 1
        and p['automatic_integration_enabled'] is True,
        'native_policy_identity')
    require(type(p['project_ids']) is list and 1 <= len(p['project_ids']) <= 2
        and len(set(p['project_ids'])) == len(p['project_ids'])
        and set(p['project_ids']) <= {'ce60c1ab-a732-4a71-8471-14c9dc393886','ffb6c7d9-4eff-46eb-a805-99f0cc2edfa0'},
        'native_policy_projects')
    root=p['controller_runtime']
    require(type(root) is str and root.startswith('/home/user/src/offmenu/.delivery/stokowski/')
        and re.fullmatch(r'/[a-zA-Z0-9_./-]{1,511}',root)
        and not any(v in ('.','..') for v in root.split('/')) and '//' not in root,
        'native_policy_runtime')
    require(type(p['source_head']) is str and p['source_head'] == config['sourceHead']
        and re.fullmatch('[0-9a-f]{40}',p['source_head'])
        and hex64(p['owner_python_sha256']) and type(p['source_sha256']) is dict
        and 1 <= len(p['source_sha256']) <= 128, 'native_policy_source')
    for name,pin in p['source_sha256'].items():
        require(type(name) is str and re.fullmatch(r'(?:tools/delivery|src/offmenu/delivery)/[a-zA-Z0-9_./-]+',name)
            and not any(v in ('.','..') for v in name.split('/')) and hex64(pin), 'native_policy_source_pin')
    require(type(p['profiles']) is dict and 1 <= len(p['profiles']) <= 2, 'native_policy_profiles')
    for name,scope in p['profiles'].items():
        require(name in ('enrichment-resilience-focused','delivery-unit-focused')
            and exact(scope, {'allowed_paths'}) and type(scope['allowed_paths']) is list
            and 1 <= len(scope['allowed_paths']) <= 16
            and len(set(scope['allowed_paths'])) == len(scope['allowed_paths']), 'native_policy_profile')
        for path in scope['allowed_paths']:
            require(type(path) is str and re.fullmatch(r'(?:(?:tools/delivery|tests/delivery|src/offmenu/delivery|tests/web)/[a-zA-Z0-9_.-]+|docs/development/project-aware-intake\.md)',path),
                'native_policy_output')
            require(name != 'delivery-unit-focused' or (path.endswith('.py') or path == 'docs/development/project-aware-intake.md'),'native_policy_python_output')
    if optional:project_source(p['project_source'])
    return p


def project_source(value):
    require(exact(value,{'repository','branch','origin','source_repository','seed','accepted_facts_path'})
        and value['repository'] == 'maldous/offmenu' and value['branch'] == 'develop'
        and value['origin'] == 'git@github.com:maldous/offmenu.git'
        and value['source_repository'] == '/home/user/src/offmenu'
        and value['accepted_facts_path'] == str(ACCEPTED/'latest.json')
        and exact(value['seed'],{'head','tree'})
        and all(type(value['seed'][k]) is str and re.fullmatch('[0-9a-f]{40}',value['seed'][k])
            for k in ('head','tree')), 'accepted_source_policy')
    return value


def accepted_fact(value, *, root=ACCEPTED, claim_root=CLAIM):
    require(exact(value,{'schema','repository','branch','head','tree','parents','base','candidate_head','pr_url',
        'operation_id','unit_sha256','packet_sha256','policy_sha256','helper_receipt','previous','observed_at'})
        and value['schema'] == 'offmenu-accepted-project-source/1'
        and value['repository'] == 'maldous/offmenu' and value['branch'] == 'develop'
        and all(type(value[k]) is str and re.fullmatch('[0-9a-f]{40}',value[k])
            for k in ('head','tree','base','candidate_head'))
        and value['parents'] == [value['base'],value['candidate_head']]
        and all(hex64(value[k]) for k in ('operation_id','unit_sha256','packet_sha256','policy_sha256'))
        and type(value['pr_url']) is str and re.fullmatch(r'https://github.com/maldous/offmenu/pull/[1-9][0-9]*',value['pr_url'])
        and type(value['observed_at']) is int and value['observed_at'] > 0,'accepted_source_fact')
    ref=value['helper_receipt'];key=value['operation_id']
    require(exact(ref,{'path','sha256'}) and hex64(ref['sha256']) and type(ref['path']) is str
        and re.fullmatch(re.escape(str(claim_root/('transaction-'+key)))+r'/native-invocation-[0-9a-f-]{36}\.json',ref['path']),
        'accepted_source_receipt')
    previous=value['previous']
    if type(previous) is dict and previous.get('schema') == 'offmenu-accepted-project-source-seed/1':
        require(exact(previous,{'schema','head','tree','policy_sha256'}) and hex64(previous['policy_sha256'])
            and all(type(previous[k]) is str and re.fullmatch('[0-9a-f]{40}',previous[k]) for k in ('head','tree'))
            and previous['head'] == value['base'],'accepted_source_seed')
    else:accepted_reference(previous,root=root)
    return value


def accepted_reference(value, *, root=ACCEPTED):
    require(exact(value,{'path','sha256'}) and type(value['path']) is str and hex64(value['sha256'])
        and re.fullmatch(re.escape(str(root/'by-operation'))+r'/[0-9a-f]{64}\.json',value['path']),
        'accepted_source_reference')
    return value


def read_accepted_fact(reference, descriptor, *, root=ACCEPTED, uid=984, claim_root=CLAIM):
    """Public metadata only; each immutable hop must anchor at the Root seed."""
    project_source(descriptor);accepted_reference(reference,root=root)
    if root == ACCEPTED:
        for parent in root.parents:_directory(parent,0)
    _directory(root,uid,0o755);_directory(root/'by-operation',uid,0o755)
    first=None;current=reference;seen=set()
    for _ in range(128):
        require(current['path'] not in seen,'accepted_source_cycle');seen.add(current['path'])
        raw=_read(Path(current['path']),uid,0o444)
        require(sha(raw) == current['sha256'],'accepted_source_hash')
        fact=accepted_fact(decode(raw),root=root,claim_root=claim_root)
        require(Path(current['path']).name == fact['operation_id']+'.json','accepted_source_operation_path')
        if first is None:first=fact
        if fact['head'] == descriptor['seed']['head']:
            require(fact['tree'] == descriptor['seed']['tree'],'accepted_source_seed_tree');return first
        previous=fact['previous']
        if previous.get('schema') == 'offmenu-accepted-project-source-seed/1':
            require(previous == dict(schema='offmenu-accepted-project-source-seed/1',
                **descriptor['seed'],policy_sha256=fingerprint(descriptor)),'accepted_source_seed_pin')
            return first
        accepted_reference(previous,root=root)
        prior_raw=_read(Path(previous['path']),uid,0o444)
        require(sha(prior_raw) == previous['sha256'],'accepted_source_hash')
        prior=accepted_fact(decode(prior_raw),root=root,claim_root=claim_root)
        require(prior['head'] == fact['base'],'accepted_source_parent_chain')
        current=previous
    raise InvocationHold('accepted_source_chain_bound')


def accepted_checkpoint_json(raw):
    """Decode only JSON-compatible MessagePack from the existing saver schema.

    No pickle, extension objects, imports or arbitrary object constructors.
    Stokowski's pinned interpreter intentionally has no LangGraph dependency.
    """
    import struct
    def need(ok):require(ok, "accepted_source_checkpoint_json")
    offset = 0
    def take(n):
        nonlocal offset
        need(0 <= n <= LIMIT and offset+n <= len(raw))
        value = raw[offset:offset+n]
        offset += n
        return value
    def unpack(depth=0):
        need(depth < 64)
        tag = take(1)[0]
        if tag <= 0x7f:
            return tag
        if tag >= 0xe0:
            return tag-256
        if 0xa0 <= tag <= 0xbf:
            return take(tag & 31).decode('utf8')
        if tag in (0xc0, 0xc2, 0xc3):
            return {0xc0:None, 0xc2:False, 0xc3:True}[tag]
        formats = {0xca:'>f',0xcb:'>d',0xcc:'>B',0xcd:'>H',0xce:'>I',0xcf:'>Q',
                   0xd0:'>b',0xd1:'>h',0xd2:'>i',0xd3:'>q'}
        if tag in formats:
            fmt = formats[tag]
            return struct.unpack(fmt,take(struct.calcsize(fmt)))[0]
        if tag in (0xd9,0xda,0xdb):
            n = int.from_bytes(take({0xd9:1,0xda:2,0xdb:4}[tag]),'big')
            return take(n).decode('utf8')
        if 0x90 <= tag <= 0x9f or tag in (0xdc,0xdd):
            n = tag & 15 if tag < 0xa0 else int.from_bytes(take(2 if tag==0xdc else 4),'big')
            need(n <= LIMIT)
            return [unpack(depth+1) for _ in range(n)]
        if 0x80 <= tag <= 0x8f or tag in (0xde,0xdf):
            n = tag & 15 if tag < 0x90 else int.from_bytes(take(2 if tag==0xde else 4),'big')
            need(n <= LIMIT)
            out = {}
            for _ in range(n):
                key = unpack(depth+1)
                need(isinstance(key,str) and key not in out)
                out[key] = unpack(depth+1)
            return out
        raise InvocationHold('accepted_source_checkpoint_type')
    value = unpack()
    need(offset == len(raw))
    return value


def canonical_checkpoint(directory, inner, *, uid=984):
    """Read the actual existing Controller checkpoint, without running its graph."""
    state=decode(_read(directory/'state.json',uid,0o600))
    binding=decode(_read(directory/'binding.json',uid,0o600))
    require(fingerprint(binding) == inner['operation_id'] and binding['version'] == 2
        and 'source_projection' not in binding and state.get('binding_sha256') == inner['operation_id']
        and state.get('status') == 'merge-verified' and state.get('merge_effect') == 'verified'
        and hex64(state.get('qualification_sha256')),'accepted_source_unverified')
    database=directory/'graph.sqlite';info=database.lstat()
    require(database.resolve() == database and stat.S_ISREG(info.st_mode) and info.st_uid == uid
        and info.st_nlink == 1 and stat.S_IMODE(info.st_mode) == 0o600,'accepted_source_checkpoint_custody')
    wal=directory/'graph.sqlite-wal'
    require(not wal.exists() or (not wal.is_symlink() and wal.stat().st_size == 0),'accepted_source_checkpoint_wal')
    with sqlite3.connect(database.as_uri()+'?mode=ro&immutable=1',uri=True) as db:
        row=db.execute("SELECT type,checkpoint FROM checkpoints WHERE thread_id=? AND checkpoint_ns='' ORDER BY checkpoint_id DESC LIMIT 1",
            (inner['operation_id'],)).fetchone()
    require(row is not None and row[0] == 'msgpack' and type(row[1]) is bytes and len(row[1])<=524288,
        'accepted_source_checkpoint')
    decoded=accepted_checkpoint_json(row[1])
    channels=decoded['channel_values'];observation=channels['observation'];commit=observation.get('merge_commit',{})
    github=observation.get('github',{});pr=state.get('publication',{}).get('pr_number')
    require(channels['result'] == state and github.get('merged') is True
        and github.get('repository') == 'maldous/offmenu' and github.get('number') == pr
        and type(pr) is int and pr>0 and state.get('publication',{}).get('effect') == 'verified'
        and observation.get('develop_contains_merge') is True
        and commit.get('sha') == state.get('merge_commit_sha') == github.get('merge_commit_sha')
        and type(commit.get('sha')) is str and re.fullmatch('[0-9a-f]{40}',commit['sha'])
        and commit.get('parents') == [binding['base'],binding['head']] and commit.get('tree') == binding['tree']
        and type(observation.get('observed_at')) in (int,float) and observation['observed_at']>0,
        'accepted_source_canonical_readback')
    return binding,commit,pr,int(observation['observed_at'])


def publish_accepted_source(config, value, *, write, root=ACCEPTED, claim_root=CLAIM, uid=984):
    """Append metadata after an actual stopped verified invocation; never HTTP."""
    descriptor=project_source(native_policy(config)['project_source'])
    record=value['receipt']['body'];inner=record['intent']['request'];key=inner['operation_id']
    require(value['status'] == 'complete' and record['terminal']['child_tree_gone'] is True
        and value['response'] is not None and value['response']['status'] == 'verified'
        and record['intent']['phase'] == 'integration','accepted_source_terminal')
    directory=claim_root/('transaction-'+key);path=root/'by-operation'/(key+'.json')
    if not write:
        if not path.exists():return None
        raw=_read(path,uid,0o444);reference=dict(path=str(path),sha256=sha(raw))
        fact=read_accepted_fact(reference,descriptor,root=root,uid=uid,claim_root=claim_root)
        require(all(fact[k] == inner[k] for k in ('operation_id','unit_sha256','packet_sha256')),
            'accepted_source_identity')
        return dict(reference=reference,fact=fact)
    _directory(root,uid,0o755)
    lock=os.open(claim_root/'repository-owner.lock',os.O_RDONLY|os.O_NOFOLLOW)
    try:
        st=os.fstat(lock)
        require(stat.S_ISREG(st.st_mode) and st.st_uid == uid and st.st_nlink == 1
            and stat.S_IMODE(st.st_mode) == 0o600,'accepted_source_lock')
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        claim=decode(_read(claim_root/'active-owner.json',uid,0o600))
        require(claim == dict(binding_sha256=key,directory=str(directory),owner=inner['owner']),
            'accepted_source_current_claim')
        binding,commit,pr,observed=canonical_checkpoint(directory,inner,uid=uid)
        require(binding == config['binding'],'accepted_source_binding')
        if not (root/'by-operation').exists():
            os.mkdir(root/'by-operation',0o700)
            fd=os.open(root/'by-operation',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            try:os.fchmod(fd,0o755);os.fsync(fd)
            finally:os.close(fd)
        _directory(root/'by-operation',uid,0o755)
        pointer_path=root/'latest.json';previous=None
        if pointer_path.exists() or pointer_path.is_symlink():
            pointer=decode(_read(pointer_path,uid,0o444))
            require(exact(pointer,{'schema','latest'}) and pointer['schema'] == 'offmenu-accepted-project-source-pointer/1',
                'accepted_source_pointer')
            previous=pointer['latest'];prior=read_accepted_fact(previous,descriptor,root=root,uid=uid,claim_root=claim_root)
        else:
            prior=descriptor['seed']
            previous=dict(schema='offmenu-accepted-project-source-seed/1',**descriptor['seed'],policy_sha256=fingerprint(descriptor))
        def store(target,obj,replace=False):
            content=wire(obj);temporary=target.with_name('.'+target.name+'.'+str(os.getpid())+'.tmp') if replace else target
            fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            try:
                with os.fdopen(fd,'wb',closefd=False) as stream:stream.write(content);stream.flush()
                os.fchmod(fd,0o444);os.fsync(fd)
            finally:os.close(fd)
            if replace:os.replace(temporary,target)
            fd=os.open(target.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            try:os.fsync(fd)
            finally:os.close(fd)
        if path.exists() or path.is_symlink():
            raw=_read(path,uid,0o444);reference=dict(path=str(path),sha256=sha(raw))
            fact=read_accepted_fact(reference,descriptor,root=root,uid=uid,claim_root=claim_root)
            require(all(fact[k] == inner[k] for k in ('operation_id','unit_sha256','packet_sha256'))
                and fact['head'] == commit['sha'] and fact['tree'] == commit['tree']
                and fact['base'] == binding['base'] and fact['candidate_head'] == binding['head']
                and fact['pr_url'] == 'https://github.com/maldous/offmenu/pull/'+str(pr), 'accepted_source_existing_fact')
            if prior['head'] != fact['base']:
                return dict(reference=reference,fact=fact)  # Never rewind a later accepted pointer.
            require(fact['previous'] == previous,'accepted_source_existing_previous')
        else:
            require(prior['head'] == binding['base'],'accepted_source_not_latest_base')
            fact=dict(schema='offmenu-accepted-project-source/1',repository='maldous/offmenu',branch='develop',
                head=commit['sha'],tree=commit['tree'],parents=commit['parents'],base=binding['base'],candidate_head=binding['head'],
                pr_url='https://github.com/maldous/offmenu/pull/'+str(pr),operation_id=key,
                unit_sha256=inner['unit_sha256'],packet_sha256=inner['packet_sha256'],policy_sha256=binding['policy_sha256'],
                helper_receipt=dict(path=str(directory/('native-invocation-'+record['intent']['invocation_id']+'.json')),
                    sha256=value['receipt']['sha256']),previous=previous,observed_at=observed)
            accepted_fact(fact,root=root,claim_root=claim_root);store(path,fact)
            reference=dict(path=str(path),sha256=sha(wire(fact)))
        store(pointer_path,dict(schema='offmenu-accepted-project-source-pointer/1',latest=reference),replace=True)
        return dict(reference=reference,fact=fact)
    finally:os.close(lock)


def prepare_request(value):
    require(exact(value, {'version','mode','issue','issue_id','project_id','owner',
        'unit_sha256','packet_sha256'}) and type(value['version']) is int
        and value['version'] == 1 and value['mode'] == 'prepare', 'native_prepare_request')
    require(type(value['issue']) is str and re.fullmatch(r'UIF-[1-9][0-9]*',value['issue'])
        and type(value['owner']) is str and 0 < len(value['owner']) <= 128
        and hex64(value['unit_sha256']) and hex64(value['packet_sha256']), 'native_prepare_identity')
    uuid(value['issue_id']);uuid(value['project_id'])
    return value


def derived_config(base, value, inner):
    """Check the fixed Root template against publisher-owned admission output."""
    p=native_policy(base)
    mutable={'binding','snapshot','plan','workspace','integration_admission'}
    require(type(value) is dict and set(value) == (set(base)-{'nativeContinuation'})
        and all(value[k] == v for k,v in base.items() if k not in mutable | {'nativeContinuation'}),
        'native_prepare_template')
    n=value['snapshot']['native_runtime'];a=value['integration_admission'];b=value['binding']
    require(n['project_id'] in p['project_ids'] and n['owner'] == p['owner']
        and a['kind'] == 'native-source-reviewed-integration-v1'
        and a['native_origin']['profile'] in p['profiles']
        and set(b['outputs']) and set(b['outputs']) <= set(p['profiles'][a['native_origin']['profile']]['allowed_paths'])
        and a['permission_sha256'] == fingerprint(p), 'native_prepare_scope')
    association(value,inner)
    return value


def selected_config(base, inner, *, root=CLAIM, uid=984):
    if inner['operation_id'] == fingerprint(base['binding']):
        return base
    native_policy(base)
    path=root/('transaction-'+inner['operation_id'])/'native-config.json'
    _directory(path.parent,uid,0o700)
    return derived_config(base,decode(_read(path,uid,0o600,1048576),1048576),inner)


def native_publication_plan(repository, source, issue, *, objects=None):
    """Derive bounded Git object requests; never execute candidate code/hooks."""
    from datetime import datetime, timedelta, timezone
    root='/repos/maldous/offmenu';operations=[];seen=set();changed={}
    def git(*args):
        command=['/usr/bin/git','--no-optional-locks','-c','safe.directory='+str(repository),
            '-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-C',str(repository),*args]
        process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
            env=dict(ENV,GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null',GIT_NO_REPLACE_OBJECTS='1'))
        try:
            chunks=[];size=0;deadline=time.monotonic()+3
            with selectors.DefaultSelector() as ready:
                ready.register(process.stdout,selectors.EVENT_READ)
                while True:
                    remaining=deadline-time.monotonic()
                    require(remaining>0 and ready.select(remaining),'native_prepare_git_timeout')
                    part=os.read(process.stdout.fileno(),min(65536,1048577-size))
                    if not part:break
                    chunks.append(part);size+=len(part)
                    require(size<=1048576,'native_prepare_git_size')
            require(process.wait(timeout=max(.001,deadline-time.monotonic())) == 0,'native_prepare_git')
            return b''.join(chunks)
        finally:
            if process.poll() is None:process.kill();process.wait(timeout=3)
            process.stdout.close()
    def obj(kind,key):
        require(re.fullmatch('[0-9a-f]{40}',key),'native_prepare_git_identity')
        raw=git('cat-file',kind,key)
        require(hashlib.sha1((kind+' '+str(len(raw))+'\0').encode()+raw).hexdigest() == key,
            'native_prepare_git_object')
        if objects is not None:objects[key]=dict(type=kind,content=base64.b64encode(raw).decode())
        return raw
    def add(kind,key,body):
        if key in seen:return
        seen.add(key);collection={'blob':'blobs','tree':'trees','commit':'commits'}[kind]
        operations.append(dict(kind=kind,method='POST',path=root+'/git/'+collection,
            body=body,readPath=root+'/git/'+collection+'/'+key,expected=key))
        require(len(operations) <= 126,'native_prepare_plan_bound')
    def tree(key):
        raw=obj('tree',key);result=[];pos=0
        while pos < len(raw):
            space=raw.index(b' ',pos);end=raw.index(b'\0',space)
            mode=raw[pos:space].decode();name=raw[space+1:end].decode()
            require(mode in ('100644','100755','40000') and re.fullmatch(r'[a-zA-Z0-9_.@+-]+',name)
                and name not in ('.','..','.git'),'native_prepare_git_entry')
            result.append(dict(path=name,mode='040000' if mode == '40000' else mode,type='tree' if mode == '40000' else 'blob',
                sha=raw[end+1:end+21].hex()));pos=end+21
        require(pos == len(raw) and len({r['path'] for r in result}) == len(result),'native_prepare_git_tree')
        return result
    def trees(head,base,prefix='',depth=0):
        require(depth < 24,'native_prepare_tree_depth')
        if head == base:return
        entries=tree(head);previous={v['path']:v for v in tree(base)} if base else {}
        require(all(any(v['path'] == p and v['mode'] == old['mode'] for v in entries)
            for p,old in previous.items()),'native_prepare_deleted_output')
        for entry in entries:
            old=previous.get(entry['path'])
            if old and old['sha'] == entry['sha']:continue
            path=prefix+entry['path']
            if entry['type'] == 'tree':trees(entry['sha'],old['sha'] if old else None,path+'/',depth+1)
            else:
                raw=obj('blob',entry['sha']);local=repository/path
                require(local.resolve() == local and _read(local,os.getuid(),stat.S_IMODE(local.lstat().st_mode),1048576) == raw,
                    'native_prepare_output_drift')
                changed[path]=sha(raw);add('blob',entry['sha'],dict(content=base64.b64encode(raw).decode(),encoding='base64'))
        add('tree',head,dict(tree=entries))
    raw=obj('commit',source['head']);headers,message=raw.decode().split('\n\n',1);headers=headers.splitlines()
    require(len(headers) == 4 and headers[:2] == ['tree '+source['tree'],'parent '+source['base']]
        and message and message.endswith('\n'),'native_prepare_commit')
    def identity(line,role):
        m=re.fullmatch(role+r' ([^<>\n]+) <([^<>\s]+)> ([0-9]+) ([+-])([0-9]{2})([0-9]{2})',line)
        require(m is not None,'native_prepare_identity')
        name,email,epoch,sign,hours,minutes=m.groups();offset=int(hours)*60+int(minutes)
        require(offset <= 840 and int(minutes) < 60,'native_prepare_timezone')
        tz=timezone(timedelta(minutes=offset if sign == '+' else -offset))
        return dict(name=name,email=email,date=datetime.fromtimestamp(int(epoch),tz).isoformat(timespec='seconds'))
    base=obj('commit',source['base']);m=re.match(rb'tree ([0-9a-f]{40})\n',base)
    require(m is not None,'native_prepare_base');trees(source['tree'],m[1].decode())
    require(changed == source['outputs'],'native_prepare_changed_scope')
    add('commit',source['head'],dict(message=message,tree=source['tree'],parents=[source['base']],
        author=identity(headers[2],'author'),committer=identity(headers[3],'committer')))
    branch=source['branch']
    operations.extend([dict(kind='ref',method='POST',path=root+'/git/refs',
        body=dict(ref='refs/heads/'+branch,sha=source['head']),readPath=root+'/git/ref/heads/'+branch,expected=None),
        dict(kind='create-pr',method='POST',path=root+'/pulls',body=dict(title=issue+': qualified native unit',
        body='Original native source, validation and independent review qualified.',base='develop',head=branch),
        readPath=root+'/pulls?state=all&head=maldous:'+branch+'&base=develop',expected=source['head'])])
    plan=dict(operations=operations,changedFiles=changed);wire(plan,1048576);return plan


def qualify_native_publication(base, envelope, current):
    """Read original owner evidence under its controlled actor; no side effects."""
    from types import SimpleNamespace
    from stokowski_adapter import read_record, file_sha
    from stokowski_unit_review import qualify_native_review
    from stokowski_operations import bridge_arguments
    from symphony_capacity import digest
    from native_harness_contract import validate_handoff
    p=native_policy(base);r=prepare_request(envelope)
    require(r['owner'] == p['owner'] and r['project_id'] in p['project_ids']
        and str(current.runtime) == p['controller_runtime'] and current.owner_custody,
        'native_prepare_owner')
    current.guard();issue=SimpleNamespace(identifier=r['issue'],id=r['issue_id'])
    runtime,manifest,_=current.context(issue.identifier,review=True,observation=True)
    require('stage' not in manifest['tasks'][issue.identifier] and manifest['project_id'] == r['project_id'],
        'native_prepare_original')
    unit=current.gate_binding(issue,observation=True)
    require(fingerprint(unit) == r['unit_sha256'],'native_prepare_unit')
    path=runtime/'native-publication-packet.json';packet=read_record(current.private(str(path)))
    require(fingerprint(packet) == r['packet_sha256'] and exact(packet,{'policy','handoff','candidate','linear','release'})
        and packet['candidate'] is None and packet['release'] is None,'native_prepare_packet')
    handoff=validate_handoff(packet['handoff'],packet['policy']);source=handoff['source']
    require(source['target'] == 'develop' and handoff['origin']['kind'] == 'native-coding-v1'
        and handoff['origin']['evidence'] == dict(path=str(runtime/'attempts'/issue.identifier/'receipt.json'),
            sha256=file_sha(runtime/'attempts'/issue.identifier/'receipt.json')) and handoff['issue_id'] == issue.id
        and handoff['project_id'] == r['project_id'] and handoff['owner'] == p['owner'], 'native_prepare_handoff')
    qualified,_=current.validation_binding(issue.identifier,current.entries[issue.identifier])
    require(qualified == runtime,'native_prepare_validation_runtime')
    selected=read_record(runtime/'validation-bindings.json')['issues'][issue.identifier]
    database=runtime/'operations/operations.sqlite'
    with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as db:
        row=db.execute('SELECT spec,state FROM operations WHERE key=?',(selected['operation_key'],)).fetchone()
    require(row is not None,'native_prepare_validation_missing');spec,state=map(json.loads,row)
    require(spec['profile'] in p['profiles'] and set(spec['outputs'])
        and set(spec['outputs']) <= set(p['profiles'][spec['profile']]['allowed_paths']), 'native_prepare_profile')
    receipt=read_record(runtime/'validation-receipt.json');op=handoff['operation']
    require(state['status'] == 'succeeded' and not state.get('cancel_requested')
        and not state.get('observation_intent') and not state.get('reconcile_required')
        and state['accepted_output_sha256'] == spec['outputs'] and state['acceptance_sha256'] == spec['acceptance_sha256']
        and state['receipt_sha256'] == digest(receipt) and receipt['status'] == 'succeeded'
        and receipt['exit_code'] == 0 and receipt['child_tree_gone'] is True and receipt['reconcile_required'] is False
        and op['id'] == selected['operation_key'] and op['status'] == 'succeeded'
        and op['receipt'] == dict(path=str(runtime/'validation-receipt.json'),sha256=file_sha(runtime/'validation-receipt.json'))
        and op['job_id'] == receipt['job_id'] == state['logical_job_id']
        and op['runner_sha256'] == receipt['runner_sha256'] == spec['runner_sha256']
        and op['policy_sha256'] == receipt['capacity_policy_sha256'] == spec['policy_sha256']
        and op['command_sha256'] == receipt['command_sha256'] == sha(bridge_arguments(spec)['command'].encode())
        and all(source[k] == spec[k] for k in ('head','base','branch'))
        and {v['path']:v['sha256'] for v in handoff['outputs']} == spec['outputs'], 'native_prepare_validation')
    review=qualify_native_review(current,issue.identifier)
    require(current._check_unit_review(review) == unit and review['verdict'] == 'accept' and not review['findings'],
        'native_prepare_independent_review')
    gate=current.state['tasks'][issue.identifier].get('unit_gate',{})
    require(gate.get('binding') == unit and gate.get('disposition') == 'approved'
        and gate.get('review_sha256') == digest(review),'native_prepare_review_gate')
    reviewed=review['source'];require(all(reviewed[k] == source[k] for k in ('head','base','tree','branch'))
        and reviewed['outputs'] == spec['outputs'],'native_prepare_review_coverage')
    policy=read_record(current.private(review['policy']['path']))
    require(file_sha(review['policy']['path']) == review['policy']['sha256'],'native_prepare_review_policy')
    evidence=read_record(current.private(review['receipt']['path']))
    rr=dict(head=source['head'],base=source['base'],outputs=spec['outputs'],author=p['owner'],
        reviewer=policy['reviewer_owner'],independent=True,verdict='accept',findings=[],
        evidence_id=review['native_session_id'],evidence_source=review['receipt'],
        model='unknown',provider='unknown',requested_model=policy['model'],requested_provider=policy['provider'],
        resolved_model=evidence.get('resolved_model'),resolution_status='observed' if evidence.get('resolved_model') else 'unknown')
    rr['evidence_sha256']=fingerprint(rr)
    n=dict(issue_id=issue.id,project_id=r['project_id'],owner=p['owner'],unit_sha256=r['unit_sha256'],
        packet_sha256=r['packet_sha256'],source=source)
    b=dict(version=2,repository='maldous/offmenu',pr_number=None,owner=p['owner'],issue_id=issue.id,
        head=source['head'],base=source['base'],tree=source['tree'],head_branch=source['branch'],
        validation_operation_key=selected['operation_key'],outputs=spec['outputs'],
        policy_sha256=fingerprint(p),capacity_policy_sha256=spec['policy_sha256'])
    native_receipt=dict(path=str(runtime/'attempts'/issue.identifier/'receipt.json'),
        sha256=file_sha(runtime/'attempts'/issue.identifier/'receipt.json'))
    validation_ref=op['receipt']
    snapshot=dict(publisher_owner=p['owner'],native_runtime=n,source_tree=source['tree'],source_clean=True,
        policy_sha256=b['policy_sha256'],capacity_policy_sha256=spec['policy_sha256'],publication_triggers_actions=False,
        unresolved_findings=[],review=rr,native_receipt_source=native_receipt,validation_receipt_source=validation_ref,
        validation=dict(operation_key=selected['operation_key'],status='succeeded',head=source['head'],base=source['base'],
        outputs=spec['outputs'],capacity_policy_sha256=spec['policy_sha256'],child_tree_gone=True,reconcile_required=False))
    objects={}
    plan=native_publication_plan(Path(reviewed['root']),dict(source,outputs=spec['outputs']),issue.identifier,objects=objects)
    b['publication']=dict(plan_sha256=fingerprint(plan),qualification_sha256=fingerprint(snapshot))
    result={k:v for k,v in base.items() if k != 'nativeContinuation'}
    result.update(binding=b,snapshot=snapshot,plan=plan,workspace=str(CLAIM/('transaction-'+fingerprint(b))),integration_admission=dict(
        version=1,kind='native-source-reviewed-integration-v1',binding_sha256=fingerprint(b),unit_sha256=r['unit_sha256'],
        review_sha256=review['receipt']['sha256'],permission_sha256=fingerprint(p),
        automatic_integration_enabled=p['automatic_integration_enabled'],
        native_origin=dict(version=1,kind='native-v1',profile=spec['profile'],source_sha256=fingerprint(source),
            packet_sha256=r['packet_sha256'],validation_operation_key=selected['operation_key'],outputs=spec['outputs'],
            native_receipt=native_receipt,validation_receipt=validation_ref)))
    derived_config(base,result,dict(version=1,mode='observe',operation_id=fingerprint(b),**{k:n[k]
        for k in ('issue_id','project_id','owner','unit_sha256','packet_sha256')},source_sha256=fingerprint(source)))
    return dict(config=result,objects=objects)


def commit_native_preparation(config, request, closure, *, objects, root=CLAIM, uid=984, prepare):
    """Create once; a partial admission is a hold, never inferred success/retry."""
    key=fingerprint(config['binding']);raw=wire(config,1048576)
    _directory(root,uid,0o700)
    lock=os.open(root/'native-preparation.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        st=os.fstat(lock)
        require(stat.S_ISREG(st.st_mode) and st.st_uid == uid and st.st_nlink == 1
            and stat.S_IMODE(st.st_mode) == 0o600,'native_prepare_lock')
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        directory=root/('transaction-'+key);done=directory/'native-prepared.json'
        proof=dict(version=1,kind='native-publisher-prepared-v1',operation_id=key,
            unit_sha256=request['unit_sha256'],packet_sha256=request['packet_sha256'],
            source_sha256=fingerprint(config['snapshot']['native_runtime']['source']),
            integration_binding=config['binding'],closure_sha256=closure,
            host_confirmation_sha256=fingerprint(dict(config_sha256=sha(raw),closure_sha256=closure,
                request_sha256=fingerprint(request))))
        if directory.exists() or directory.is_symlink():
            _directory(directory,uid,0o700)
            require(_read(directory/'native-config.json',uid,0o600,1048576) == raw,
                'native_prepare_existing_config')
            require(done.exists(),'native_prepare_unknown')
            require(decode(_read(directory/'native-objects.json',uid,0o600,1048576),1048576) == objects,
                'native_prepare_existing_objects')
            require(decode(_read(done,uid,0o600,1048576),1048576) == proof,
                'native_prepare_existing_proof')
            return proof  # Existing original receipt; never reacquire a claim.
        os.mkdir(directory,0o700)
        parent=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(parent)
        finally:os.close(parent)
        def create(path,value):
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            try:
                content=wire(value,1048576)
                with os.fdopen(fd,'wb',closefd=False) as output:
                    output.write(content);output.flush();os.fsync(fd)
            finally:os.close(fd)
            fd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY)
            try:os.fsync(fd)
            finally:os.close(fd)
        create(directory/'native-objects.json',objects)
        create(directory/'native-config.json',config)
        # Existing Controller ownership acquires the repository claim under its
        # global lock, rechecking any pending/unknown predecessor before prepare.
        state=prepare()
        require(state.get('status') == 'publication-ready' and state.get('publication',{}).get('effect') == 'ready',
            'native_prepare_controller')
        create(done,proof)
        return proof
    finally:
        os.close(lock)




def continuation(value, identity):
    """Finite ROOT-sealed same-operation history grant, not invocation authority."""
    pre = isinstance(value,dict) and 'pre_admission_refusal' in value
    require(exact(value, {'version','operation_id','unit_sha256','packet_sha256','claim_sha256',
        'previous_selection_sha256','previous_capability','previous_record_sha256','receipts'} |
        ({'pre_admission_refusal'} if pre else set()))
        and type(value['version']) is int and value['version'] == 1, 'continuation_shape')
    for key in ('operation_id','unit_sha256','packet_sha256','claim_sha256',
                'previous_selection_sha256','previous_record_sha256'):
        require(hex64(value[key]), 'continuation_hash')
    require(all(value[k] == identity[k] for k in ('operation_id','unit_sha256','packet_sha256')),
            'continuation_identity')
    claim = dict(binding_sha256=identity['operation_id'],
        directory=str(CLAIM/('transaction-'+identity['operation_id'])),owner=identity['owner'])
    require(value['claim_sha256'] == fingerprint(claim), 'continuation_claim')
    cap = value['previous_capability']
    require(exact(cap, {'version','closure_sha256','host_confirmation_sha256'})
        and type(cap['version']) is int and cap['version'] == 1
        and all(hex64(cap[k]) for k in ('closure_sha256','host_confirmation_sha256')),
        'continuation_capability')
    receipts = value['receipts']
    require(type(receipts) is list and (receipts == [] if pre else 1 <= len(receipts) <= 128),
            'continuation_receipts')
    if pre:
        refused=value['pre_admission_refusal']
        require(exact(refused,{'invocation_id','request_sha256','reason','evidence_sha256'})
            and refused['reason'] == 'closure_canonical_bytes'
            and hex64(refused['request_sha256']) and hex64(refused['evidence_sha256']),
            'pre_admission_refusal')
        uuid(refused['invocation_id'])
    ids = []
    for ref in receipts:
        require(exact(ref, {'invocation_id','closure_sha256','receipt_sha256'})
            and hex64(ref['closure_sha256']) and hex64(ref['receipt_sha256']), 'continuation_receipt')
        uuid(ref['invocation_id']); ids.append(ref['invocation_id'])
    require(len(ids) == len(set(ids)), 'continuation_duplicate')
    return value


def original_receipt_closure(record, current_closure, grant):
    """Old bytes retain old closure pins only under the exact sealed whitelist."""
    intent = record['intent']
    if grant is not None:
        selected = [r for r in grant['receipts'] if r['invocation_id'] == intent['invocation_id']]
        if selected:
            ref = selected[0]
            require(sha(wire(record)) == ref['receipt_sha256']
                and intent['closure_sha256'] == ref['closure_sha256'], 'continuation_receipt_drift')
            return ref['closure_sha256']
    require(intent['closure_sha256'] == current_closure, 'unadmitted_historical_receipt')
    return current_closure


def request(raw):
    value = decode(raw, WIRE_LIMIT)
    require(exact(value, {'version', 'mode', 'invocation_id', 'request'})
            and type(value['version']) is int and value['version'] == 1
            and value['mode'] in ('invoke', 'observe', 'review'), 'outer_request')
    uuid(value['invocation_id'])
    inner = value['request']
    require(exact(inner, INNER) and type(inner['version']) is int and inner['version'] == 1
            and inner['mode'] in ('observe', 'step', 'publish'), 'inner_request')
    for key in ('operation_id', 'unit_sha256', 'packet_sha256', 'source_sha256'):
        require(hex64(inner[key]), 'request_hash')
    for key in ('issue_id', 'project_id'):
        uuid(inner[key])
    owner = inner['owner']
    require(value['mode'] != 'review' or inner['mode'] == 'observe', 'review_read_only')
    require(type(owner) is str and 0 < len(owner) <= 200 and owner == owner.strip()
            and all(ord(c) >= 32 and ord(c) != 127 for c in owner), 'request_owner')
    return value


def association(config, inner):
    """Only sealed byte association; independent127 checks remain authoritative."""
    try:
        require(type(config['version']) is int and config['version'] in (1, 2)
                and type(config['publisherUid']) is int and config['publisherUid'] == 984
                and type(config['publisherGid']) is int and config['publisherGid'] == 976, 'config_identity')
        binding, n = config['binding'], config['snapshot']['native_runtime']
        require(inner['mode'] != 'publish' or (config['version'] == 1
                and 'source_projection' not in binding
                and config.get('integration_admission', {}).get('kind') ==
                    'native-source-reviewed-integration-v1'), 'publication_only_admission')
        require(exact(n, {'issue_id', 'project_id', 'owner', 'unit_sha256', 'packet_sha256', 'source'}), 'sealed_native')
        s = n['source']
        require(exact(s, {'repository', 'branch', 'base', 'head', 'tree', 'target', 'policy_sha256'})
                and s['repository'] == binding['repository'] == 'maldous/offmenu'
                and n['owner'] == binding['owner'] == config['logicalOwner']
                and n['issue_id'] == binding['issue_id']
                and ('project_id' not in binding or n['project_id'] == binding['project_id']), 'sealed_source')
        for key in ('base', 'head', 'tree'):
            require(type(s[key]) is str and re.fullmatch('[0-9a-f]{40}', s[key]), 'source_hash')
        require(hex64(s['policy_sha256']), 'source_policy')
        if config['version'] == 2:
            require(s == binding['candidate']['source'] and s['branch'] == 'develop'
                    and s['target'] == 'main', 'release_source')
        else:
            source_base = binding['base']
            if 'source_projection' in binding:
                p = binding['source_projection']
                require(exact(p, {'version','profile','source','target','merge_tree','outputs',
                    'unit_sha256','operation_key','receipt','review_sha256'})
                    and binding.get('version') == 2
                    and type(p['version']) is int and p['version'] == 1
                    and p['profile'] == 'identity-client-focused'
                    and exact(p['source'], {'head','base','tree','branch'})
                    and exact(p['target'], {'base','tree'})
                    and p['source'] == {key:s[key] for key in ('head','base','tree','branch')}
                    and p['target']['base'] == binding['base']
                    and all(type(v) is str and re.fullmatch('[0-9a-f]{40}', v)
                            for v in (p['target']['base'],p['target']['tree'],p['merge_tree']))
                    and p['outputs'] == binding['outputs']
                    and p['unit_sha256'] == n['unit_sha256'] and hex64(p['unit_sha256'])
                    and p['operation_key'] == binding['validation_operation_key'] and hex64(p['operation_key'])
                    and hex64(p['review_sha256']) and exact(p['receipt'], {'path','sha256'})
                    and type(p['receipt']['path']) is str and p['receipt']['path'].startswith('/')
                    and hex64(p['receipt']['sha256'])
                    and hex64(config['codePins'].get('src/offmenu/delivery/identity_source_projection.py')),
                    'integration_projection')
                source_base = p['source']['base']
            require(s['base'] == source_base and all(s[key] == binding[key] for key in ('head', 'tree'))
                    and s['branch'] == binding['head_branch'] and s['target'] == 'develop', 'integration_source')
        identity = dict(operation_id=fingerprint(binding), issue_id=n['issue_id'],
                        project_id=n['project_id'], owner=n['owner'], unit_sha256=n['unit_sha256'],
                        packet_sha256=n['packet_sha256'], source_sha256=fingerprint(s))
        require(all(inner[key] == value for key, value in identity.items()), 'sealed_association')
        return 'release' if config['version'] == 2 else 'integration'
    except (KeyError, TypeError, AttributeError):
        raise InvocationHold('sealed_config') from None


def inner_response(value, inner, phase):
    fields = {'version', 'kind', 'request_sha256', 'phase', 'status'} | (INNER - {'version', 'mode'})
    require(exact(value, fields) and type(value['version']) is int and value['version'] == 1
            and value['kind'] == 'native-publisher-response-v1' and value['phase'] == phase
            and value['status'] in STATUSES and value['request_sha256'] == fingerprint(inner)
            and all(value[key] == inner[key] for key in INNER - {'version', 'mode'}), 'publisher_response')
    return value


def validate_closure(raw, source_head):
    """Shared128 canonical manifest. SHA256 is file bytes, not fingerprint()."""
    value = decode(raw, MANIFEST_LIMIT)
    require(exact(value, {'version', 'kind', 'source_head', 'source_tree', 'node_sha256', 'files'})
            and type(value['version']) is int and value['version'] == 1
            and value['kind'] == 'native-publisher-closure-v1'
            and value['source_head'] == source_head and hex64(value['node_sha256']), 'closure_shape')
    for key in ('source_head', 'source_tree'):
        require(type(value[key]) is str and re.fullmatch('[0-9a-f]{40}', value[key]), 'closure_source')
    files = value['files']
    require(type(files) is dict and 0 < len(files) <= 50000, 'closure_files')
    for name, pin in files.items():
        require(type(name) is str and 0 < len(name) <= 1024 and not name.startswith('/')
                and '\\' not in name and all(ord(c) >= 32 and ord(c) != 127 for c in name)
                and all(p not in ('', '.', '..', '.git', '.ssh', '.aws', '.codex', '.env')
                        for p in name.split('/')) and hex64(pin), 'closure_path')
        require(not name.lower().endswith('.pem') or name == PUBLIC_CA, 'private_pem_refused')
        require(name != 'native-harness-closure.json', 'closure_self_reference')
    required = {'tools/delivery/native_publisher_invocation.py', 'tools/delivery/windmill_runner.py',
                'tools/delivery/capacity-policy.json', 'tools/delivery/github-app-publisher.mjs',
                'tools/delivery/github-app-adapter.mjs', 'tools/delivery/integration-gateway.mjs',
                'src/offmenu/delivery/integration.py', 'venv/bin/python'}
    require(required <= files.keys(), 'closure_required')
    canonical = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii') + b'\n'
    require(raw == canonical, 'closure_canonical_bytes')
    return value


def _file_hash(path, uid=0, maximum=64*1024*1024):
    """Bounded streaming hash: do not materialize dependency/interpreter bodies."""
    require(path.resolve() == path, 'canonical_file')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == uid and before.st_nlink == 1
                and not before.st_mode & 0o022 and before.st_size <= maximum, 'file_custody')
        digest = hashlib.sha256(); size = 0
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            size += len(chunk); require(size <= maximum, 'file_size'); digest.update(chunk)
        after = os.fstat(fd)
        require(size == before.st_size and (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                == (after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'file_drift')
        return digest.hexdigest()
    finally:
        os.close(fd)


def _public_ca_record(root, files, uid=0):
    if PUBLIC_CA not in files:
        return
    records = [name for name in files if re.fullmatch(
        r'venv/lib/python3\.12/site-packages/certifi-[a-zA-Z0-9_.-]+\.dist-info/RECORD', name)]
    require(len(records) == 1, 'public_ca_record')
    path = root/records[0]
    require(_file_hash(path, uid) == files[records[0]], 'public_ca_record_pin')
    rows = list(csv.reader(io.StringIO(_read(path, uid, stat.S_IMODE(path.stat().st_mode), MANIFEST_LIMIT).decode('utf-8'))))
    rows = [row for row in rows if row and row[0] == 'certifi/cacert.pem']
    expected = 'sha256=' + base64.urlsafe_b64encode(bytes.fromhex(files[PUBLIC_CA])).rstrip(b'=').decode('ascii')
    require(len(rows) == 1 and len(rows[0]) == 3 and rows[0][1] == expected
            and rows[0][2].isdigit() and len(rows[0][2]) <= 12
            and int(rows[0][2]) == (root/PUBLIC_CA).stat().st_size, 'public_ca_record_pin')


def _read(path, uid, mode, maximum=LIMIT):
    require(path.resolve() == path, 'canonical_file')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        st = os.fstat(fd)
        require(stat.S_ISREG(st.st_mode) and st.st_uid == uid and st.st_nlink == 1
                and stat.S_IMODE(st.st_mode) == mode and 0 < st.st_size <= maximum, 'file_custody')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(maximum + 1)
        after = os.fstat(fd)
        require(len(raw) == st.st_size and (st.st_ino, st.st_dev, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
                == (after.st_ino, after.st_dev, after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'file_drift')
        return raw
    finally:
        os.close(fd)


def _directory(path, uid, mode=None):
    st = path.lstat()
    require(path.resolve() == path and stat.S_ISDIR(st.st_mode) and st.st_uid == uid
            and not st.st_mode & 0o022 and (mode is None or stat.S_IMODE(st.st_mode) == mode), 'directory_custody')


class _Host:
    uid = 984
    root = CLAIM
    cwd = INSTALL
    command = (str(NODE), str(PUBLISHER), '--native-rpc')
    timeout = TIMEOUT

    def prepare(self, envelope):
        base,closure=self._sealed();p=native_policy(base);r=prepare_request(envelope)
        require(r['owner'] == p['owner'] and r['project_id'] in p['project_ids'],'native_prepare_owner')
        # Fixed read-only actor boundary: private owner evidence stays private.
        # Root's one-time exact sudo rule permits only this sealed program/flag.
        for path in (*OWNER_SOURCE.parents,*OWNER_PYTHON.parents):
            _directory(path,0)
        require(_file_hash(OWNER_PYTHON,maximum=256*1024*1024) == p['owner_python_sha256'],
            'native_prepare_owner_python')
        for name,pin in p['source_sha256'].items():
            require(_file_hash(OWNER_SOURCE/name) == pin,'native_prepare_owner_source')
        require(p['source_sha256'].get('tools/delivery/native_publisher_invocation.py') ==
            _file_hash(OWNER_SOURCE/'tools/delivery/native_publisher_invocation.py'),'native_prepare_reader_pin')
        code=OWNER_SOURCE/'tools/delivery/native_publisher_invocation.py'
        child=subprocess.run(['/usr/bin/sudo','-n','-u','#1000','--',str(OWNER_PYTHON),'-I','-B',
            str(code),'--qualify-native'],input=wire(dict(config=base,request=r),1048576),
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=8,cwd=INSTALL,env=ENV)
        require(child.returncode == 0 and len(child.stdout) <= 1048576,'native_prepare_reader')
        value=decode(child.stdout,1048576)
        require(exact(value,{'config','objects'}),'native_prepare_reader_fields')
        config=value['config'];n=config['snapshot']['native_runtime'];key=fingerprint(config['binding'])
        inner=dict(version=1,mode='observe',operation_id=key,source_sha256=fingerprint(n['source']),
            **{k:n[k] for k in ('issue_id','project_id','owner','unit_sha256','packet_sha256')})
        require(all(inner[k] == r[k] for k in ('issue_id','project_id','owner','unit_sha256','packet_sha256')),
            'native_prepare_reader_identity')
        derived_config(base,config,inner)
        sys.path[:0]=[str(INSTALL/'src'),str(INSTALL/'tools/delivery')]
        from offmenu.delivery.integration import publisher_request
        return commit_native_preparation(config,r,closure,objects=value['objects'],root=CLAIM,uid=984,
            prepare=lambda:publisher_request(config,{'op':'prepare'}))

    def _sealed(self):
        require((os.getuid(), os.geteuid(), os.getgid(), os.getegid()) == (984, 984, 976, 976), 'publisher_identity')
        require(Path(__file__).resolve() == ENTRY and Path(sys.executable).resolve() == PYTHON, 'installed_entry')
        # Validate the entire import closure before importing maintained helpers.
        entries = [INSTALL]
        count = 0
        while entries:
            path = entries.pop()
            count += 1
            require(count <= 50000 and len(path.relative_to(INSTALL).parts) <= 24, 'closure_bounds')
            st = path.lstat()
            require(st.st_uid == 0 and not st.st_mode & 0o022 and not stat.S_ISLNK(st.st_mode), 'sealed_closure')
            if stat.S_ISDIR(st.st_mode):
                entries.extend(path.iterdir())
            else:
                require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1, 'sealed_file')
        for path in (*INSTALL.parents, *CONFIG.parents, *CLAIM.parents):
            _directory(path, 0)
        raw = _read(CONFIG, 0, 0o440, 1048576)
        config = decode(raw, 1048576)
        require(CONFIG.stat().st_gid == 976, 'config_group')
        manifest_raw = _read(CLOSURE, 0, 0o444, MANIFEST_LIMIT)
        manifest = validate_closure(manifest_raw, config['sourceHead'])
        files = manifest['files']
        selected = {str(path.relative_to(INSTALL)) for path in INSTALL.rglob('*')
                    if path.is_file() and path != CLOSURE}
        require(selected == set(files), 'closure_exact_files')
        _public_ca_record(INSTALL, files)  # Public CA exception requires its pinned RECORD before PEM read.
        total = 0
        for name, pin in files.items():
            path = INSTALL/name
            total += path.stat().st_size
            require(total <= 1024*1024*1024, 'closure_total_size')
            require(_file_hash(path) == pin, 'closure_byte_pin')
        for path, mode in ((ENTRY, 0o444), (PYTHON, 0o555)):
            require(stat.S_IMODE(path.stat().st_mode) == mode, 'entry_mode')
        for parent in NODE.parents:
            _directory(parent, 0)
        require(NODE.stat().st_mode & 0o111 and _file_hash(NODE, maximum=256*1024*1024)
                == manifest['node_sha256'], 'node_pin')
        require(type(config['codePins']) is dict and 0 < len(config['codePins']) <= 32, 'code_pins')
        require(all(files.get(name) == pin for name, pin in config['codePins'].items())
                and files['venv/bin/python'] == config['pythonSha256'], 'existing_code_pins')
        return config, sha(manifest_raw)

    def admit(self, inner):
        base,closure=self._sealed()
        config=selected_config(base,inner)
        self.native_config=config if config is not base else None
        phase=association(config,inner)
        # No legacy-state migration or new Controller initialization.
        _directory(CLAIM, 984, 0o700)
        directory = CLAIM / ('transaction-' + inner['operation_id'])
        require(directory.exists(), 'prepared_transaction_missing')
        _directory(directory, 984, 0o700)
        require(decode(_read(directory/'binding.json', 984, 0o600, 1048576), 1048576) == config['binding'], 'prepared_binding')
        _read(directory/'state.json', 984, 0o600, 1048576)
        claim = decode(_read(CLAIM/'active-owner.json', 984, 0o600))
        require(claim == dict(binding_sha256=inner['operation_id'], directory=str(directory), owner=inner['owner']), 'existing_owner_claim')
        self.continuation = (continuation(config['nativeContinuation'], inner)
                             if 'nativeContinuation' in config else None)
        sys.path.insert(0, str(INSTALL/'tools/delivery'))
        self.runner = importlib.import_module('windmill_runner')
        return directory, phase, closure

    def review(self, directory, inner, closure):
        """Read the original pending checkpoint; no graph setup or side receipt."""
        return pending_review(directory, inner, closure, root=CLAIM, uid=984)

    def accepted_source(self, value, *, write):
        config=getattr(self,'native_config',None)
        if (config is None or 'project_source' not in config.get('native_policy',{})
            or value['status'] != 'complete' or (value['response'] or {}).get('status') != 'verified'):
            return value
        facet=publish_accepted_source(config,value,write=write)
        return dict(value,accepted_source=facet) if facet is not None else value


def pending_review(directory, inner, closure, *, root, uid):
    # root/uid are fixed by _Host; injection is in-process synthetic tests only.
    # Recheck ownership under the original existing lock after admission.
    lock = os.open(root/'repository-owner.lock', os.O_RDONLY | os.O_NOFOLLOW)
    try:
        st = os.fstat(lock)
        require(stat.S_ISREG(st.st_mode) and st.st_uid == uid and st.st_nlink == 1
                and stat.S_IMODE(st.st_mode) == 0o600, 'review_lock')
        fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
        binding = decode(_read(directory/'binding.json', uid, 0o600, 1048576), 1048576)
        require(fingerprint(binding) == inner['operation_id'] and binding['version'] == 2
                and binding['issue_id'] == inner['issue_id'] and binding['owner'] == inner['owner'],
                'review_binding')
        claim = decode(_read(root/'active-owner.json', uid, 0o600))
        require(claim == dict(binding_sha256=inner['operation_id'], directory=str(directory),
                              owner=inner['owner']), 'review_current_claim')
        require(decode(_read(directory/'repository-claim.json', uid, 0o600)) == claim,
                'review_immutable_claim')
        state = decode(_read(directory/'state.json', uid, 0o600, 1048576), 1048576)
        if (state.get('binding_sha256') == inner['operation_id']
            and state.get('status') in ('publication-ready','publication-verified')
            and state.get('publication', {}).get('effect') in ('ready','verified')
            and not state.get('merge_effect')):
            return dict(version=1,kind='native-publisher-unit-review-v1',status='not-ready',
                        request_sha256=fingerprint(inner),closure_sha256=closure)
        require(state.get('binding_sha256') == inner['operation_id']
                and state.get('status') == 'merge-intent' and state.get('merge_effect') == 'pending'
                and not state.get('helper_consumed')
                and state.get('action', {}).get('kind') == 'merge-pr', 'review_pending')
        # Open read-only, retain typed checkpoint bytes for the existing v2 decoder.
        # Check consumed inode custody; SQLite receives no caller-supplied path.
        database = directory/'graph.sqlite'
        info = database.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_uid == uid and info.st_nlink == 1
                and stat.S_IMODE(info.st_mode) == 0o600, 'review_checkpoint_custody')
        # SQLite mode=ro alone can create WAL/SHM files. With the owner's
        # shared lock held, require a fully checkpointed database and use
        # immutable reads; never ignore an uncheckpointed WAL or repair it.
        wal = directory/'graph.sqlite-wal'
        require(not wal.exists() or (not wal.is_symlink() and wal.stat().st_size == 0),
                'review_checkpoint_wal')
        with sqlite3.connect(database.as_uri()+'?mode=ro&immutable=1', uri=True) as db:
            row = db.execute("SELECT type,checkpoint FROM checkpoints WHERE thread_id=? AND checkpoint_ns='' ORDER BY checkpoint_id DESC LIMIT 1",
                             (inner['operation_id'],)).fetchone()
        require(row is not None and row[0] == 'msgpack' and type(row[1]) is bytes
                and 0 < len(row[1]) <= 524288, 'review_checkpoint')
        return dict(version=1, kind='native-publisher-unit-review-v1',
                    request_sha256=fingerprint(inner), closure_sha256=closure,
                    binding=binding, decision=state, checkpoint=base64.b64encode(row[1]).decode('ascii'))
    finally:
        os.close(lock)


def _write(path, value):
    """Bounded same-directory write/fsync; never initializes a job runner."""
    raw = wire(value)
    # Same-dir temporary, no overwrite of any other invocation's record.
    temp = path.with_name('.' + path.name + '.tmp')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.replace(temp, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temp.exists():
            temp.unlink()


def _echild():
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
            if pid == 0:
                return False
        except ChildProcessError:
            return True


def _starttime(pid):
    try:
        text = Path('/proc', str(pid), 'stat').read_text()
        return int(text[text.rfind(')')+2:].split()[19])
    except (OSError, ValueError, IndexError):
        return None


def _supervise(inner, phase, host):
    """One fresh SAME-UID subreaper; no recovery inference in this function."""
    require(_echild(), 'preexisting_children')
    require(ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) == 0, 'subreaper_unavailable')
    subreaper = ctypes.c_int()
    require(ctypes.CDLL(None, use_errno=True).prctl(37, ctypes.byref(subreaper), 0, 0, 0) == 0
            and subreaper.value == 1, 'subreaper_readback')
    stopped = [False]
    previous = {}
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        previous[sig] = signal.signal(sig, lambda *_: stopped.__setitem__(0, True))
    proc = None
    sel = selectors.DefaultSelector()
    output = bytearray()
    outcome, response, reaped, gone = 'supervisor_error', None, False, False
    pid, start = None, None
    try:
        proc = subprocess.Popen(host.command, cwd=host.cwd, env=ENV, close_fds=True,
                                start_new_session=True, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pid, start = proc.pid, _starttime(proc.pid)
        payload = memoryview(wire(inner)); sent = 0; errors = 0
        for stream, label, events in ((proc.stdin, 'in', selectors.EVENT_WRITE),
                                       (proc.stdout, 'out', selectors.EVENT_READ),
                                       (proc.stderr, 'err', selectors.EVENT_READ)):
            os.set_blocking(stream.fileno(), False); sel.register(stream, events, label)
        deadline = time.monotonic() + host.timeout
        outcome = 'succeeded'
        while sel.get_map() or proc.poll() is None:
            if stopped[0]:
                outcome = 'cancelled'; break
            if time.monotonic() >= deadline:
                outcome = 'timed_out'; break
            for key, _ in sel.select(.02):
                stream, label = key.fileobj, key.data
                if label == 'in':
                    try:
                        sent += os.write(stream.fileno(), payload[sent:])
                    except BrokenPipeError:
                        sent = len(payload)
                    if sent == len(payload):
                        sel.unregister(stream); stream.close()
                else:
                    chunk = os.read(stream.fileno(), 4096)
                    if not chunk:
                        sel.unregister(stream); continue
                    if label == 'out':
                        output.extend(chunk)
                    else:
                        errors += len(chunk)
                    if len(output) > WIRE_LIMIT or errors > 4096:
                        outcome = 'output_limit'; break
            if outcome == 'output_limit':
                break
        if outcome == 'succeeded' and proc.poll() != 0:
            outcome = 'publisher_error'
    except Exception:
        outcome = 'supervisor_error'
    finally:
        try:
            if proc is not None:
                # Only reusable termination helpers; their census is not proof.
                host.runner.cleanup(proc)
                proc.wait(timeout=1)
                reaped = True
            gone = _echild()  # SAME subreaper, after actual direct-child reap.
        except Exception:
            gone = False
        sel.close()
        if proc is not None:
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                if stream and not stream.closed:
                    stream.close()
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    if outcome == 'succeeded':
        try:
            response = inner_response(decode(bytes(output), WIRE_LIMIT), inner, phase)
        except InvocationHold:
            outcome = 'invalid_response'
    return dict(outcome=outcome, child_started=proc is not None, child_pid=pid,
                child_starttime=start, subreaper_verified=True, direct_child_reaped=reaped,
                waitpid_echild=gone, child_tree_gone=gone and (proc is None or reaped),
                response=response, response_sha256=fingerprint(response) if response is not None else None)


def _result(envelope, record):
    terminal = record['terminal'] if record else None
    return dict(version=1, kind='native-publisher-invocation-v1',
                operation_id=envelope['request']['operation_id'], invocation_id=envelope['invocation_id'],
                request_sha256=fingerprint(envelope['request']),
                status='not-found' if record is None else ('complete' if terminal and terminal['child_tree_gone'] else 'unknown'),
                response=terminal['response'] if terminal else None,
                receipt={'sha256': sha(wire(record)), 'body': record} if record else None)


def validate_result(value, envelope, closure_sha256):
    """Pure126 boundary: a body hash alone is NOT privileged authentication."""
    envelope = request(wire(envelope))
    optional={'accepted_source'} if type(value) is dict and 'accepted_source' in value else set()
    require(exact(value, {'version', 'kind', 'operation_id', 'invocation_id', 'request_sha256',
                          'status', 'response', 'receipt'} | optional), 'outer_response')
    require(type(value['version']) is int and value['version'] == 1
            and value['kind'] == 'native-publisher-invocation-v1'
            and value['operation_id'] == envelope['request']['operation_id']
            and value['invocation_id'] == envelope['invocation_id']
            and value['request_sha256'] == fingerprint(envelope['request']), 'result_identity')
    if value['receipt'] is None:
        require(not optional and value['status'] == 'not-found' and value['response'] is None, 'missing_receipt')
        return value
    ref = value['receipt']
    require(exact(ref, {'sha256', 'body'}) and ref['sha256'] == sha(wire(ref['body'])), 'receipt_hash')
    record = ref['body']
    require(exact(record, {'version', 'kind', 'intent', 'terminal'}) and type(record['version']) is int
            and record['version'] == 1 and record['kind'] == 'native-publisher-invocation-record-v1', 'receipt_shape')
    intent = record['intent']
    require(exact(intent, {'operation_id', 'invocation_id', 'request', 'request_sha256', 'closure_sha256',
                           'phase', 'supervisor_pid', 'supervisor_starttime'})
            and intent['operation_id'] == value['operation_id'] and intent['invocation_id'] == value['invocation_id']
            and intent['request'] == envelope['request'] and intent['request_sha256'] == value['request_sha256']
            and intent['closure_sha256'] == closure_sha256 and hex64(closure_sha256)
            and intent['phase'] in ('integration', 'release')
            and type(intent['supervisor_pid']) is int and intent['supervisor_pid'] > 0
            and type(intent['supervisor_starttime']) is int and intent['supervisor_starttime'] > 0, 'receipt_intent')
    terminal = record['terminal']
    if terminal is not None:
        require(exact(terminal, {'outcome', 'child_started', 'child_pid', 'child_starttime', 'subreaper_verified',
                                 'direct_child_reaped', 'waitpid_echild', 'child_tree_gone', 'response', 'response_sha256'}), 'terminal_shape')
        require(terminal['outcome'] in ('succeeded', 'publisher_error', 'timed_out', 'cancelled',
                                        'output_limit', 'invalid_response', 'supervisor_error'), 'terminal_outcome')
        require((type(terminal['child_pid']) is int and terminal['child_pid'] > 0)
                if terminal['child_started'] else terminal['child_pid'] is None, 'terminal_child')
        require(terminal['child_starttime'] is None or
                (type(terminal['child_starttime']) is int and terminal['child_starttime'] > 0), 'terminal_child')
        for key in ('child_started', 'subreaper_verified', 'direct_child_reaped', 'waitpid_echild', 'child_tree_gone'):
            require(type(terminal[key]) is bool, 'terminal_boolean')
        proven = terminal['subreaper_verified'] and terminal['waitpid_echild'] and (
            not terminal['child_started'] or terminal['direct_child_reaped'])
        require(terminal['child_tree_gone'] == proven and value['response'] == terminal['response'], 'terminal_proof')
        if terminal['response'] is not None:
            inner_response(terminal['response'], envelope['request'], intent['phase'])
            require(terminal['response_sha256'] == fingerprint(terminal['response'])
                    and terminal['outcome'] == 'succeeded', 'terminal_response')
        else:
            require(terminal['response_sha256'] is None, 'terminal_response')
    expected = 'complete' if terminal and terminal['child_tree_gone'] else 'unknown'
    require(value['status'] == expected and (terminal is not None or value['response'] is None), 'result_status')
    if optional:
        facet=value['accepted_source'];inner=envelope['request']
        require(value['status'] == 'complete' and intent['phase'] == 'integration'
            and (value['response'] or {}).get('status') == 'verified'
            and exact(facet,{'reference','fact'}),'accepted_source_facet')
        accepted_reference(facet['reference']);fact=accepted_fact(facet['fact'])
        require(facet['reference']['path'] == str(ACCEPTED/'by-operation'/(inner['operation_id']+'.json'))
            and facet['reference']['sha256'] == sha(wire(fact))
            and all(fact[k] == inner[k] for k in ('operation_id','unit_sha256','packet_sha256')),
            'accepted_source_facet_identity')
    return value


def _invoke(raw, host):
    candidate=decode(raw,WIRE_LIMIT)
    if type(candidate) is dict and candidate.get('mode') == 'prepare':
        require(type(host) is _Host or (os.getuid() not in (0,984)
            and Path('/tmp') in host.root.resolve().parents),'synthetic_scope')
        return host.prepare(prepare_request(candidate))
    envelope = request(raw)
    if type(host) is not _Host:
        # Disposable in-process tests only; there is no executable selector.
        require(os.getuid() not in (0, 984) and Path('/tmp') in host.root.resolve().parents
                and host.root.resolve() == host.root, 'synthetic_scope')
    directory, phase, closure = host.admit(envelope['request'])
    if envelope['mode'] == 'review':
        require(phase == 'integration', 'review_phase')
        return host.review(directory, envelope['request'], closure)
    grant = getattr(host, 'continuation', None)
    if grant is not None:
        continuation(grant, envelope['request'])
        require(phase == 'integration', 'continuation_phase')
    uid = host.uid
    path = directory / ('native-invocation-' + envelope['invocation_id'] + '.json')
    def existing():
        require(not path.is_symlink(), 'receipt_symlink')
        record = decode(_read(path, uid, 0o600)) if path.exists() else None
        expected = original_receipt_closure(record, closure, grant) if record else closure
        value=validate_result(_result(envelope, record), envelope, expected)
        if hasattr(host,'accepted_source'):
            value=host.accepted_source(value,write=envelope['mode'] == 'invoke')
        return validate_result(value,envelope,expected)
    # No lock creation, mkdir, prctl, subprocess, claim or receipt mutation.
    if envelope['mode'] == 'observe':
        return existing()
    lock = os.open(directory/'native-invocation.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        st = os.fstat(lock)
        require(stat.S_ISREG(st.st_mode) and st.st_uid == uid and st.st_nlink == 1
                and stat.S_IMODE(st.st_mode) == 0o600, 'invocation_lock')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise InvocationHold('invocation_busy') from None
        if path.exists():
            return existing()  # Same id never executes twice, including terminal failures.
        entries = list(directory.iterdir())
        require(len(entries) <= 256, 'invocation_custody_bound')
        historical = set()
        for item in entries:
            if item.name.startswith('native-invocation-') and item.name.endswith('.json'):
                previous = decode(_read(item, uid, 0o600))
                require(exact(previous, {'version', 'kind', 'intent', 'terminal'})
                        and previous['intent']['operation_id'] == envelope['request']['operation_id'], 'prior_invocation')
                prior_envelope = dict(version=1, mode='observe', invocation_id=previous['intent']['invocation_id'],
                                      request=previous['intent']['request'])
                require(all(previous['intent']['request'][k] == envelope['request'][k]
                    for k in INNER - {'mode'}), 'prior_invocation_identity')
                old_closure = original_receipt_closure(previous, closure, grant)
                validate_result(_result(prior_envelope, previous), prior_envelope, old_closure)
                require(previous['terminal'] is not None and previous['terminal']['child_tree_gone'] is True,
                        'prior_invocation_unresolved')
                if grant and any(r['invocation_id'] == prior_envelope['invocation_id'] for r in grant['receipts']):
                    terminal = previous['terminal']
                    require((terminal['response'] is not None and terminal['response']['status'] not in ('pending','unknown'))
                        or (terminal['response'] is None and prior_envelope['request']['mode'] == 'observe'),
                        'continuation_unknown_effect')
                    historical.add(prior_envelope['invocation_id'])
        require(grant is None or historical == {r['invocation_id'] for r in grant['receipts']},
                'continuation_receipt_missing')
        record = dict(version=1, kind='native-publisher-invocation-record-v1', terminal=None,
                      intent=dict(operation_id=envelope['request']['operation_id'], invocation_id=envelope['invocation_id'],
                                  request=envelope['request'], request_sha256=fingerprint(envelope['request']),
                                  closure_sha256=closure, phase=phase, supervisor_pid=os.getpid(),
                                  supervisor_starttime=_starttime(os.getpid())))
        require(type(record['intent']['supervisor_starttime']) is int, 'supervisor_identity')
        _write(path, record)  # Before spawn; a crash retains an unresolved intent.
        record['terminal'] = _supervise(envelope['request'], phase, host)
        _write(path, record)  # A failed write leaves the prior intent, never a success reply.
        return existing()  # Actual durable bytes, not the in-memory proposed receipt.
    finally:
        os.close(lock)


def invoke(raw):
    """Fixed installed publisher-owner entry; no source/config/key selectors."""
    return _invoke(raw, _Host())


def main():
    if sys.argv[1:] == ['--qualify-native']:
        require(os.getuid() == os.geteuid() == 1000 and Path(__file__).resolve() ==
            OWNER_SOURCE/'tools/delivery/native_publisher_invocation.py'
            and Path(sys.executable).resolve() == OWNER_PYTHON,'native_prepare_reader_identity')
        sys.path[:0]=[str(OWNER_SOURCE/'src'),str(OWNER_SOURCE/'tools/delivery')]
        from stokowski_adapter import CurrentWork
        body=decode(sys.stdin.buffer.read(1048577),1048576)
        require(exact(body,{'config','request'}),'native_prepare_reader_fields')
        p=native_policy(body['config'])
        current=CurrentWork(Path(p['controller_runtime']),read_only=True)
        require(current.config['source_head'] == p['source_head']
            and all(current.config['source_sha256'].get(k) == v for k,v in p['source_sha256'].items()),
            'native_prepare_reader_source')
        sys.stdout.buffer.write(wire(qualify_native_publication(body['config'],body['request'],current),1048576))
        return
    require(len(sys.argv) == 1, 'arguments')
    os.umask(0o077)
    result = invoke(sys.stdin.buffer.read(WIRE_LIMIT + 1))
    sys.stdout.buffer.write(wire(result, 1048576 if result.get('kind') == 'native-publisher-unit-review-v1' else LIMIT))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        sys.stderr.write('native-invocation-held\n')
        sys.exit(1)
