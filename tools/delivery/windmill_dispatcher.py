# requirements:
# wmill==1.850.0
"""Typed OffMenu bridge dispatch using existing Windmill job-scoped SDK auth.

No credentials, schedules, infrastructure or grant APIs. This adapter never
executes locally and never cancels only an API wrapper in place of Foo cleanup.
"""
import hashlib
import json
import math
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


def _safe_receipt(job_id, receipt):
    if not isinstance(receipt, dict) or receipt.get("job_id") != job_id:
        raise ValueError("RECEIPT_ID_INVALID")
    states = {"starting", "running", "queued", "succeeded", "failed", "timed_out", "cancelled", "supervisor_error", "unknown", "busy", "blocked_reconciliation", "id_conflict", "request_error", "not_found", "cancellation_requested"}
    if receipt.get("status") not in states: raise ValueError("RECEIPT_STATE_INVALID")
    safe = {"job_id": job_id, "status": receipt["status"]}
    for key, value in receipt.items():
        if key in safe: continue
        valid = False
        if key in {"command_sha256", "request_sha256", "runner_sha256", "capacity_policy_sha256"}:
            valid = isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None
        elif key in {"created_at", "started_at", "finished_at", "heartbeat_at", "heartbeat_age_seconds"}:
            valid = type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 2**53
        elif key in {"reconcile_required", "child_tree_gone", "reserved", "terminal_verified"}:
            valid = type(value) is bool
        elif key == "version": valid = type(value) is int and value in (1, 3)
        elif key == "timeout_seconds": valid = type(value) is int and 1 <= value <= 1800
        elif key == "exit_code": valid = value is None or type(value) is int and -255 <= value <= 255
        elif key == "mode": valid = value in ("read", "write")
        elif key == "reason": valid = value in {"long_job_active", "incompatible_job_active", "two_slots_active", "unresolved_inflight_marker", "unresolved_long_job_marker", "no_safe_slot", "capacity_admission_busy", "capacity_pool_active", "capacity_legacy_active", "capacity_slots_active", "capacity_cpu_reserved", "capacity_memory_reserved", "capacity_processes_reserved", "capacity_disk_reserved", "capacity_io_reserved", "capacity_paths_conflict"}
        elif key == "error_class": valid = isinstance(value, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,63}", value) is not None
        elif key == "unresolved_jobs":
            valid = isinstance(value, list) and len(value) <= 64 and all(isinstance(x,str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}",x) for x in value)
        elif key == "logs":
            valid = value == {name:"/offmenu/data/.offmenu-platform/jobs/"+job_id+"/"+name+".log" for name in ("stdout","stderr")}
        elif key in {"log_bytes", "output_bytes"}:
            valid = isinstance(value,dict) and set(value)=={"stdout","stderr"} and all(type(x) is int and 0<=x<=2**63-1 for x in value.values())
        elif key == "logs_truncated":
            valid = isinstance(value,dict) and set(value)=={"stdout","stderr"} and all(type(x) is bool for x in value.values())
        else: raise ValueError("RECEIPT_FIELD_INVALID")
        if not valid: raise ValueError("RECEIPT_FIELD_INVALID")
        safe[key] = value
    return safe


# This wire version is independent of immutable operation/spec versions.
INSPECT_VERSION = 'offmenu-inspect/2'


def compact_result(value):
    # Bound parsing even for discarded wrapper errors. Never expose their text.
    if len(json.dumps(value, allow_nan=False)) > 10000:
        raise ValueError('Oversized bridge result')
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            if value.lstrip().startswith(('{', '[')):
                raise ValueError('Malformed bridge result') from None
    if value is None:
        return None
    if isinstance(value, str):
        return {'classification':'no-authoritative-receipt'}
    if not isinstance(value, dict):
        raise ValueError('Invalid bridge result')
    if 'receipt' not in value:
        if ('job_id' in value and (not isinstance(value['job_id'],str) or
            not re.fullmatch(r'offmenu-[0-9a-f]{48}',value['job_id']))):
            raise ValueError('Invalid bridge identity')
        return {'classification':'no-authoritative-receipt'}
    if set(value) - {'ok','transport_ok','job_succeeded','admitted','job_id','receipt'}:
        raise ValueError('Unexpected bridge result fields')
    job_id = value.get('job_id')
    if not isinstance(job_id, str) or not re.fullmatch(r'offmenu-[0-9a-f]{48}', job_id):
        raise ValueError('Invalid bridge identity')
    for field in ('ok','transport_ok','job_succeeded','admitted'):
        if field in value and not (type(value[field]) is bool or
                                  field == 'admitted' and value[field] is None):
            raise ValueError('Invalid bridge flag')
    result = dict(value, receipt=_safe_receipt(job_id, value['receipt']))
    if len(json.dumps(result, sort_keys=True)) > 10000:
        raise ValueError('Oversized bridge receipt')
    return result


def compact_job(remote):
    args = validate_request(remote.get('args'))
    selected = {k:remote.get(k) for k in
                ('id','workspace_id','script_path','type','running','success')}
    if selected['type'] == 'CompletedJob' and 'running' not in remote:
        selected['running'] = False
    if (selected['type'] not in ('QueuedJob','CompletedJob') or
        type(selected['running']) is not bool or
        selected['type'] == 'CompletedJob' and
            (selected['running'] or type(selected['success']) is not bool) or
        selected['type'] == 'QueuedJob' and selected['success'] is not None):
        raise ValueError('Invalid job state')
    raw_result = remote.get('result')
    result = compact_result(raw_result)
    if result is None and selected['type'] == 'CompletedJob':
        result = {'classification':'no-authoritative-receipt'}
    # Check an optional wrapper identity even when no receipt was supplied.
    if isinstance(raw_result,str):
        try:
            raw_result = json.loads(raw_result)
        except json.JSONDecodeError:
            pass
    if (isinstance(raw_result,dict) and 'job_id' in raw_result and
        raw_result['job_id'] != args['job_id']):
        raise ValueError('Conflicting backend identity')
    selected.update(inspect_version=INSPECT_VERSION,
        args_sha256=hashlib.sha256(json.dumps(args, sort_keys=True,
            separators=(',', ':')).encode()).hexdigest(),
        result=result)
    return selected


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
        selected = compact_job(remote)
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
