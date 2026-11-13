#requirements:
#wmill==1.850.0
"""Private fixed-site publisher access check; no deployment or source transfer."""
import hashlib
import http.client
import json
import re
import ssl

SITE_ID='a1df1508-4bb9-4b55-ab1f-88611e456e61'
SITE_NAME='offmenu-corpus'
SECRET_PATH='u/admin/offmenu_netlify_api_token'
HOST='api.netlify.com'

class SafeStop(Exception): pass

def get(token,path,limit=131072):
    if path not in ('/api/v1/user','/api/v1/sites/'+SITE_ID,'/api/v1/sites/'+SITE_ID+'/files'):
        raise SafeStop('unapproved_read_path')
    c=http.client.HTTPSConnection(HOST,timeout=60,context=ssl.create_default_context())
    try:
        c.request('GET',path,headers={'Authorization':'Bearer '+token,'Accept':'application/json'})
        r=c.getresponse();data=r.read(limit+1)
        if len(data)>limit: raise SafeStop('response_size_limit')
        if r.status != 200: raise SafeStop('netlify_http_'+str(r.status))
        return json.loads(data)
    finally:c.close()

def inspect(token):
    if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9._~-]{16,8192}',token):
        raise SafeStop('stored_secret_format_invalid')
    user=get(token,'/api/v1/user')
    if not isinstance(user.get('id'),str) or not user['id']:raise SafeStop('identity_unverified')
    before=get(token,'/api/v1/sites/'+SITE_ID)
    if before.get('id')!=SITE_ID or before.get('name')!=SITE_NAME:raise SafeStop('site_mismatch')
    deployed=before.get('published_deploy') or {}
    deploy_id=deployed.get('id')
    if not isinstance(deploy_id,str) or not deploy_id:raise SafeStop('published_deploy_unresolved')
    files=get(token,'/api/v1/sites/'+SITE_ID+'/files',128*1024*1024)
    if not isinstance(files,list):raise SafeStop('file_inventory_invalid')
    digests={}
    for item in files:
        path=item.get('path');sha=item.get('sha')
        if not isinstance(path,str) or not path.startswith('/') or path in digests or '..' in path.split('/'):
            raise SafeStop('file_path_invalid')
        if not isinstance(sha,str) or not re.fullmatch('[0-9a-f]{40}',sha):raise SafeStop('file_digest_invalid')
        digests[path]=sha
    after=get(token,'/api/v1/sites/'+SITE_ID)
    if after.get('id')!=SITE_ID or (after.get('published_deploy') or {}).get('id')!=deploy_id:
        raise SafeStop('publication_changed_during_inventory')
    return {'status':'fixed_site_read_access_verified','site_id':SITE_ID,'site_name':SITE_NAME,
            'published_deploy_id':deploy_id,'current_public_file_count':len(digests),
            'current_public_file_map_sha256':hashlib.sha256(json.dumps(digests,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'base_manifest_present':'/manifest.json' in digests,'recipe_manifest_present':'/recipes/manifest.json' in digests,
            'credential_returned':False,'netlify_mutations':0,'deployment_write_access':'not_tested',
            'corpus_publication':'not_started'}

def main():
    stage='sdk_import'
    try:
        import wmill
        stage='private_reference'
        token=wmill.get_variable(SECRET_PATH)
        stage='netlify_read'
        return inspect(token)
    except SafeStop as exc:
        return {'status':'blocked','reason':str(exc),'credential_returned':False,'netlify_mutations':0}
    except Exception as exc:
        # Suppress provider, SDK and transport exception text; it may include response details.
        return {'status':'blocked','reason':'private_reference_or_transport_failure','stage':stage,'error_category':next((name for cls,name in ((ImportError,'sdk_missing'),(TimeoutError,'timeout'),(ssl.SSLError,'tls'),(OSError,'transport'),(ValueError,'decode'),(AttributeError,'response_shape')) if isinstance(exc,cls)), 'other'),'credential_returned':False,'netlify_mutations':0}
