#!/usr/bin/env python3
"""Import only the existing exported Netlify token to a private Windmill secret. Default dry-run; no deployment."""
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
SITE_ID = 'a1df1508-4bb9-4b55-ab1f-88611e456e61'
SITE_NAME = 'offmenu-corpus'
SECRET_PATH = 'u/admin/offmenu_netlify_api_token'
NETLIFY_HOST = 'api.netlify.com'
ENV_NAME = 'NETLIFY_API_TOKEN'
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
    def __init__(self, token, host=HOST):
        if host not in (HOST, NETLIFY_HOST): raise Stop('Unapproved HTTPS destination')
        self.token, self.host = token, host
    def call(self, method, path, payload=None):
        if self.host == NETLIFY_HOST:
            if method != 'GET' or path not in ('/api/v1/user', '/api/v1/sites/'+SITE_ID):
                raise Stop('Netlify importer is fixed-site read-only')
        elif (method,path) not in (
            ('GET',BASE+'/users/whoami'),
            ('GET',BASE+'/variables/get/'+SECRET_PATH+'?decrypt_secret=false'),
            ('POST',BASE+'/variables/create')):
            raise Stop('Unapproved Windmill operation')
        c = http.client.HTTPSConnection(self.host, timeout=20, context=ssl.create_default_context())
        try:
            body = None if payload is None else json.dumps(payload).encode()
            c.request(method,path,body=body,headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json'})
            r=c.getresponse(); data=r.read(65537)
            if len(data)>65536: raise Stop('Response exceeded safe limit')
            # No redirects, retries, proxy discovery, or response-body logging.
            if r.status not in (200,201,204,404): raise Stop(classify(r.status,data))
            return r.status,data
        finally: c.close()

def secret_metadata(api):
    status,body=api.call('GET',BASE+'/variables/get/'+SECRET_PATH+'?decrypt_secret=false')
    if status == 404: return False
    if status != 200: raise Stop('Secret metadata unavailable')
    meta=json.loads(body)
    if meta.get('is_secret') is not True or meta.get('extra_perms',{}) != {}:
        raise Stop('Existing target is not a private encrypted secret; preserved without writes')
    if meta.get('path',SECRET_PATH) != SECRET_PATH:
        raise Stop('Secret metadata path mismatch')
    return True

def exported_token(env):
    value=env.get(ENV_NAME,'')
    if not re.fullmatch(r'[A-Za-z0-9._~-]{16,8192}',value):
        raise Stop('NETLIFY_API_TOKEN must already be exported with a valid nonempty token; no shell profile is sourced')
    return value

def run(windmill,netlify,value,apply=False):
    status,body=windmill.call('GET',BASE+'/users/whoami')
    who=json.loads(body)
    if status!=200 or who.get('username')!='admin':
        raise Stop('Workspace identity is not admin; no writes attempted')
    exists=secret_metadata(windmill)
    status,body=netlify.call('GET','/api/v1/user')
    user=json.loads(body)
    if status!=200 or not isinstance(user.get('id'),str) or not user['id']:
        raise Stop('Netlify token identity preflight failed')
    status,body=netlify.call('GET','/api/v1/sites/'+SITE_ID)
    site=json.loads(body)
    if status!=200 or site.get('id')!=SITE_ID or site.get('name')!=SITE_NAME:
        raise Stop('Netlify fixed-site qualification failed')
    emit(status='read_preflight_verified',workspace='offmenu',username='admin',site_id=SITE_ID,
         token_identity_verified=True,site_name=SITE_NAME,netlify_write_permission='not_tested')
    if exists: state='existing_private_secret_preserved'
    elif not apply: state='would_create_private_encrypted_secret'
    else:
        status,_=windmill.call('POST',BASE+'/variables/create',{
            'path':SECRET_PATH,'value':value,'is_secret':True,
            'description':'Approved existing Netlify token for private fixed-site OffMenu publisher only; site '+SITE_ID+'. Never return the value; no automatic credential rotation.'})
        if status not in (200,201,204): raise Stop('Create failed; no overwrite or automatic retry')
        if not secret_metadata(windmill): raise Stop('Post-create secret metadata verification failed')
        state='private_encrypted_secret_created_verified'
    emit(status=state,mode='apply' if apply else 'dry_run',path=SECRET_PATH,
         variable_reference='$var:'+SECRET_PATH,netlify_mutations=0,
         note='No deployment performed. Existing secret is never overwritten; worker must verify its own stored-reference access.')

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--apply',action='store_true'); args=p.parse_args()
    try:
        wm=API(load_token()); value=exported_token(os.environ)
        run(wm,API(value,NETLIFY_HOST),value,args.apply)
    except Exception as exc:
        # Never render unexpected exception messages, response bodies or tracebacks.
        emit(status='STOP',reason=str(exc) if isinstance(exc,Stop) else type(exc).__name__,
             note='No overwrite or retry. Any successful create is retained. No Netlify deployment was called.')
        return 1
    return 0
if __name__=='__main__': sys.exit(main())
