#!/usr/bin/env python3
"""Local-only secret importer. Default dry-run; no inference or provider activation."""
import argparse
import http.client
import json
import os
import re
import ssl
import stat
import sys

HOST = 'windmill.aldous.info'
BASE = '/api/w/offmenu'
PROVIDERS = {
 'groq':['GROQ_API_KEY','GROQ_TOKEN'],
 'cerebras':['CEREBRAS_API_KEY','CEREBRAS_TOKEN','CERABRAS_TOKEN'],
 'mistral':['MISTRAL_API_KEY','MISTRAL_TOKEN'], 'cohere':['COHERE_API_KEY'],
 'gemini':['GOOGLE_GEMINI_API_KEY','GEMINI_TOKEN'],
 'openrouter':['OPENROUTER_API_KEY','OPENROUTER_TOKEN'],
 'deepseek':['DEEPSEEK_API_KEY','DEEPSEEK_TOKEN'], 'nvidia':['NVIDIA_API_KEY'],
 'sambanova':['SAMBANOVA_API_KEY','SAMBANOVA_TOKEN'], 'fireworks':['FIREWORKS_API_KEY'],
 'together':['TOGETHER_API_KEY'], 'huggingface':['HUGGING_TOKEN','HUGGING_FACE_READ_TOKEN'],
 'zai':['ZAI_API_KEY'], 'nous':['NOUS_API_KEY'], 'openai':['OPENAI_API_KEY'],
 'github_models':['GITHUB_MODELS_TOKEN'], 'ollama':['OLLAMA_API_KEY'],
 'codebuff':['CODEBUFF_API_KEY','CODEBUFF_API_KEY2','CODEBUFF_API_KEY3'],
}
class Stop(Exception): pass

def emit(**fields): print(json.dumps(fields, sort_keys=True), flush=True)

def load_token():
    if os.getuid() == 0 or os.environ.get('SUDO_USER'):
        raise Stop('Run as your normal user, not sudo/root')
    directory = os.open(os.path.expanduser('~/.windmill'), os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        ds = os.fstat(directory)
        if ds.st_uid != os.getuid() or ds.st_mode & 0o022:
            raise Stop('Token directory must be owned by current user and not group/world writable')
        fd = os.open('token', os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK, dir_fd=directory)
        try:
            s = os.fstat(fd)
            if not stat.S_ISREG(s.st_mode) or s.st_uid != os.getuid() or s.st_mode & 0o077 or s.st_nlink != 1:
                raise Stop('Token must be a private single-link regular file owned by current user (mode 600 or 400)')
            raw = os.read(fd, 8193)
        finally: os.close(fd)
    finally: os.close(directory)
    token = raw.decode('ascii').strip()
    if not re.fullmatch(r'[A-Za-z0-9._~-]{16,8192}', token): raise Stop('Invalid token file format')
    return token

def classify(status, body):
    lower = body[:65536].lower()
    return 'HTTP %s; required_scope=%s; gateway_html=%s' % (
        status, b'required scope' in lower,
        b'cloudflare' in lower or b'<html' in lower or b'<!doctype html' in lower)

class API:
    def __init__(self, token): self.token = token
    def call(self, method, path, payload=None):
        # Direct verified HTTPS; intentionally no ambient proxies or redirects.
        c = http.client.HTTPSConnection(HOST, timeout=20, context=ssl.create_default_context())
        try:
            body = None if payload is None else json.dumps(payload).encode()
            c.request(method, path, body=body, headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json'})
            r = c.getresponse(); data = r.read(65537)
            if len(data)>65536: raise Stop('Response exceeded safe limit')
            if r.status == 403: raise Stop(classify(r.status,data))
            if r.status not in (200,201,204,404): raise Stop(classify(r.status,data))
            return r.status, data
        finally: c.close()

def candidates(env):
    result=[]
    for provider, aliases in PROVIDERS.items():
        present=[(k,env[k]) for k in aliases if env.get(k)]
        if not present:
            emit(provider=provider,status='missing_environment'); continue
        distinct = len({v for _,v in present}) > 1
        groups = present if distinct else present[:1]
        for alias,value in groups:
            name = provider+'__'+alias.lower() if distinct else provider
            result.append({'provider':provider,'alias':alias,'path':'u/admin/ai_keys/'+name,
                           'value':value,'ambiguous':distinct})
    return result

def run(api, env, apply=False):
    status, body = api.call('GET',BASE+'/users/whoami')
    who=json.loads(body)
    if status!=200 or who.get('username')!='admin':
        raise Stop('Workspace identity is not admin; no namespace changes or writes attempted')
    emit(status='workspace_identity_verified',workspace='offmenu',username='admin',
         scope_verification='read preflight; write permission only proven by create')
    items=candidates(env)
    # Complete every read preflight before any write; 403 aborts the entire batch.
    for item in items:
        status, body=api.call('GET',BASE+'/variables/get/'+item['path']+'?decrypt_secret=false')
        item['exists']=status==200
        if item['exists']:
            meta=json.loads(body)
            if meta.get('is_secret') is not True: raise Stop('Existing target is not a secret; preserved without writes')
    for item in items:
        if item['exists']: state='existing_preserved'
        elif not apply: state='would_create_encrypted_secret'
        else:
            status,_=api.call('POST',BASE+'/variables/create',{
              'path':item['path'],'value':item['value'],'is_secret':True,
              'description':'OffMenu disabled AI credential candidate; source '+item['alias']+'; no provider activated; configuration pending'})
            if status not in (200,201,204): raise Stop('Create failed; earlier successful creates retained, no overwrite or automatic retry')
            status, body=api.call('GET',BASE+'/variables/get/'+item['path']+'?decrypt_secret=false')
            if status!=200 or json.loads(body).get('is_secret') is not True:
                raise Stop('Post-create secret metadata verification failed')
            state='encrypted_secret_created_verified'
        emit(provider=item['provider'],source_variable=item['alias'],path=item['path'],status=state,
             variable_reference='$var:'+item['path'],ambiguous_aliases=item['ambiguous'],
             resource_readiness='configuration_pending_disabled',provider_calls=0)
    emit(status='complete',mode='apply' if apply else 'dry_run',provider_calls=0,
         resources_created=0,note='Secret storage only; no provider endpoints guessed, no providers activated')

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--apply',action='store_true'); args=p.parse_args()
    try: run(API(load_token()),os.environ,args.apply)
    except Exception as exc:
        # Never render unexpected exception messages, response bodies or tracebacks.
        emit(status='STOP',reason=str(exc) if isinstance(exc,Stop) else type(exc).__name__,
             note='No overwrite; any earlier successful creates are retained. No inference was called.')
        return 1
    return 0
if __name__=='__main__': sys.exit(main())
