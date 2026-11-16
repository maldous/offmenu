#requirements:
#wmill==1.850.0
"""Inspect or explicitly enable only the two reviewed owner-private schedules.

This setup probe is not deployed/scheduled. No force, credentials, callbacks,
run-as changes, new schedules or retries are available through this entrypoint.
"""
import os
import hashlib
import re
from datetime import datetime

DEFINITIONS = {
    'u/admin/offmenu_platform_health_15m': ('0 */15 * * * *', 'health'),
    'u/admin/offmenu_platform_verify_daily': ('0 17 3 * * *', 'verify'),
}
CHECKER_SOURCE_SHA256 = '6950fd128485fae09e20ec571021ca592bf37405a373519b44ab1849d6d7eac8'
_HASH = re.compile(r'[0-9a-f]{16}\Z')
_UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z')


class ScheduleCheckError(RuntimeError):
    pass


def _checked_schedule(client, path):
    response = client.get('/w/offmenu/schedules/get/'+path, raise_for_status=False)
    if response.status_code != 200:
        raise ScheduleCheckError('SCHEDULE_READ_REFUSED')
    s = response.json()
    cron, mode = DEFINITIONS[path]
    expected = {'workspace_id':'offmenu', 'path':path, 'edited_by':'admin',
                'extra_perms':{}, 'permissioned_as':'u/admin', 'schedule':cron,
                'timezone':'Australia/Melbourne', 'script_path':'u/admin/offmenu_platform_check',
                'is_flow':False, 'args':{'mode':mode,'max_items':100}, 'cron_version':'v2'}
    if not isinstance(s,dict) or any(s.get(k) != v for k,v in expected.items()):
        raise ScheduleCheckError('SCHEDULE_DEFINITION_MISMATCH')
    if type(s.get('enabled')) is not bool or type(s['args']['max_items']) is not int:
        raise ScheduleCheckError('SCHEDULE_DEFINITION_MISMATCH')
    if any(s.get(k) is not None for k in ('on_failure','on_recovery','on_success','retry',
             'on_failure_extra_args','on_recovery_extra_args','on_success_extra_args',
             'paused_until','dynamic_skip','tag','error')):
        raise ScheduleCheckError('SCHEDULE_UNEXPECTED_BEHAVIOR')
    if s.get('ws_error_handler_muted',False) is not False or s.get('no_flow_overlap',False) is not False:
        raise ScheduleCheckError('SCHEDULE_UNEXPECTED_BEHAVIOR')
    return dict(expected, enabled=s['enabled'])


def _checker_identity(client):
    response=client.get('/w/offmenu/scripts/get/p/u/admin/offmenu_platform_check',raise_for_status=False)
    if response.status_code != 200:
        raise ScheduleCheckError('CHECKER_READ_REFUSED')
    s=response.json()
    if (not isinstance(s,dict) or s.get('path') != 'u/admin/offmenu_platform_check'
            or s.get('workspace_id') != 'offmenu' or s.get('created_by') != 'admin'
            or s.get('extra_perms') != {} or not isinstance(s.get('content'),str)
            or hashlib.sha256(s['content'].encode()).hexdigest() != CHECKER_SOURCE_SHA256
            or not isinstance(s.get('hash'),str) or not _HASH.fullmatch(s['hash'])):
        raise ScheduleCheckError('CHECKER_IDENTITY_MISMATCH')
    return {'script_hash':s['hash'],'source_sha256':CHECKER_SOURCE_SHA256,'exact_source_verified':True}


def _queued(client,path,script_hash):
    response = client.get('/w/offmenu/jobs/queue/list', params={'schedule_path':path,'per_page':10},
                          raise_for_status=False)
    if response.status_code != 200:
        raise ScheduleCheckError('SCHEDULE_QUEUE_READ_REFUSED')
    queued = response.json()
    if not isinstance(queued,list) or len(queued)>10:
        raise ScheduleCheckError('SCHEDULE_QUEUE_SHAPE_INVALID')
    out=[]
    for j in queued:
        if not isinstance(j,dict) or j.get('schedule_path') != path:
            continue
        if not isinstance(j.get('id'),str) or not _UUID.fullmatch(j['id']):
            raise ScheduleCheckError('SCHEDULE_QUEUE_ID_INVALID')
        due=j.get('scheduled_for')
        if not isinstance(due,str) or len(due)>40 or datetime.fromisoformat(due.replace('Z','+00:00')).tzinfo is None:
            raise ScheduleCheckError('SCHEDULE_QUEUE_DATE_INVALID')
        running=j.get('running',False)
        if type(running) is not bool:
            raise ScheduleCheckError('SCHEDULE_QUEUE_STATE_INVALID')
        h=j.get('script_hash')
        if not isinstance(h,str) or not _HASH.fullmatch(h):
            raise ScheduleCheckError('SCHEDULE_QUEUE_HASH_INVALID')
        out.append({'job_id':j['id'],'scheduled_for':due,'running':running,
                    'script_hash':h,'latest_checker_hash':h==script_hash})
    return out


def inspect_or_enable(enable=False, client=None):
    try:
        if type(enable) is not bool:
            raise ScheduleCheckError('SCHEDULE_OPERATION_INVALID')
        if os.environ.get('WM_WORKSPACE') != 'offmenu' or os.environ.get('WM_USERNAME') != 'admin':
            raise ScheduleCheckError('SCHEDULE_OWNER_REQUIRED')
        if client is None:
            import wmill
            client=wmill.Windmill()
        # Validate both before any activation. Never force a fork-conflict warning.
        checker=_checker_identity(client)
        before={path:_checked_schedule(client,path) for path in DEFINITIONS}
        activated=[]
        if enable:
            for path in DEFINITIONS:
                if not before[path]['enabled']:
                    response=client.post('/w/offmenu/schedules/setenabled/'+path,
                                          json={'enabled':True},raise_for_status=False)
                    if response.status_code not in (200,201):
                        raise ScheduleCheckError('SCHEDULE_ENABLE_REFUSED')
                    activated.append(path)
        out=[]
        for path in DEFINITIONS:
            s=_checked_schedule(client,path)
            if enable and not s['enabled']:
                raise ScheduleCheckError('SCHEDULE_ENABLE_NOT_OBSERVED')
            s['next_jobs']=_queued(client,path,checker['script_hash'])
            out.append(s)
        return {'schema_version':1,'activated':activated,'checker':checker,'schedules':out}
    except ScheduleCheckError:
        raise
    except Exception:
        raise ScheduleCheckError('SCHEDULE_OPERATION_UNAVAILABLE') from None


def main(enable:bool=False):
    return inspect_or_enable(enable)
