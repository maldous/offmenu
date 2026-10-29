# requirements:
# wmill==1.850.0
"""Typed OffMenu bridge dispatch using existing Windmill job-scoped SDK auth.

No credentials, schedules, infrastructure or grant APIs. This adapter never
executes locally and never cancels only an API wrapper in place of Foo cleanup.
"""
import json
import os
import re
from uuid import UUID

BRIDGE = 'u/admin/foo_jobs_20261027'


def validate_request(value):
    if not isinstance(value,dict) or value.get('action') not in ('run','status','cancel'):
        raise ValueError('Invalid bridge operation')
    if not re.fullmatch(r'offmenu-[0-9a-f]{48}',str(value.get('job_id',''))):
        raise ValueError('Invalid immutable backend ID')
    if value['action'] in ('status','cancel'):
        if set(value) != {'action','job_id'}:
            raise ValueError('Unexpected control fields')
        return value
    if set(value) != {'action','job_id','command','mode','timeout_seconds','resources'}:
        raise ValueError('Unexpected execution fields')
    if value['mode'] != 'read' or value['timeout_seconds'] != 180:
        raise ValueError('Unreviewed mode or timeout')
    command = value['command']
    if (not isinstance(command,str) or not command.startswith('cd /offmenu && export PYTHONPATH=/offmenu/src ')
        or '\0' in command or len(command.encode()) > 32000):
        raise ValueError('Unreviewed command envelope')
    expected = {'workers':1,'overhead_processes':8,'cpu_millis':1000,
                'memory_bytes':2147483648,'io_slots':1,'output_bytes':0,
                'read_roots':['/offmenu'],'write_roots':[]}
    if value['resources'] != expected:
        raise ValueError('Unreviewed resource envelope')
    return value


def dispatch(client,action,job_id,request=None):
    if str(UUID(job_id)) != job_id:
        raise ValueError('Noncanonical Windmill job UUID')
    endpoint = '/w/offmenu/jobs_u/get/'+job_id
    if action == 'inspect':
        response = client.get(endpoint,raise_for_status=False)
        if response.status_code == 404:
            return {'found':False,'credential_exported':False}
        if response.status_code != 200:
            return {'error':'unavailable' if response.status_code >= 500 else 'refused',
                    'http_status':response.status_code,'credential_exported':False}
        remote = response.json()
        if (remote.get('workspace_id') != 'offmenu' or remote.get('script_path') != BRIDGE
            or remote.get('id') != job_id):
            return {'error':'foreign-job','credential_exported':False}
        # Results are already bounded bridge receipts, never raw test logs.
        selected = {k:remote.get(k) for k in ('id','workspace_id','script_path','args',
                                             'type','running','success','result')}
        validate_request(selected['args'])
        if isinstance(selected['result'],str):
            try:
                selected['result'] = json.loads(selected['result'])
            except ValueError:
                selected['result'] = None
        if not isinstance(selected['result'],dict) or 'receipt' not in selected['result']:
            selected['result'] = None
        return {'found':True,'job':selected,'credential_exported':False}
    if action != 'submit':
        raise ValueError('Only typed submit/inspect are supported')
    request = validate_request(request)
    response = client.post('/w/offmenu/jobs/run/p/'+BRIDGE,
                           params={'job_id':job_id},json=request,raise_for_status=False)
    if response.status_code in (200,201):
        if response.text.strip().strip('"') != job_id:
            return {'error':'unexpected-job-id','credential_exported':False}
        return {'submitted':True,'job_id':job_id,'credential_exported':False}
    if response.status_code in (400,409):
        # Could be the existing UUID after a lost response. Reconciliation owns
        # the next step; never silently choose a fresh server-side UUID.
        return {'error':'reconcile','job_id':job_id,'credential_exported':False}
    return {'error':'refused' if response.status_code in (401,403) else 'unknown',
            'http_status':response.status_code,'credential_exported':False}


def main(action: str, job_id: str, request: dict = None):
    if os.environ.get('WM_WORKSPACE') != 'offmenu' or os.environ.get('WM_USERNAME') != 'admin':
        raise ValueError('Run as the existing OffMenu owner')
    import wmill
    return dispatch(wmill.Windmill(),action,job_id,request)
