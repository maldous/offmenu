# Appended after the reviewed fixed-target transport helper.
import hashlib
import os
import re
import shlex

_RUNNER = 'u/admin/foo_jobs_20261027'
_UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z')


def _query_namespace():
    ns = {'__name__': 'offmenu_query_worker'}
    exec(base64.b64decode(_QUERY_SOURCE_B64), ns)
    return ns


def _command(expression):
    program = ("import base64,json; ns={'__name__':'offmenu_query_host'}; "
               "exec(base64.b64decode(" + repr(_QUERY_SOURCE_B64) + "),ns); "
               "print(json.dumps(" + expression + ",sort_keys=True))")
    return 'python3 -I -S -B -c ' + shlex.quote(program)


def _receipt(job_id):
    ns = _query_namespace()
    if not isinstance(job_id, str) or not ns['JOB'].fullmatch(job_id):
        raise ValueError('QUERY_JOB_ID_INVALID')
    result = _confined_exec(_command("ns['read_status'](" + repr(job_id) + ")"))
    if (result.get('ok') is not True or any(result.get('truncated', {}).values())
            or len(result.get('stdout', '')) > 32000):
        raise RuntimeError('QUERY_RECEIPT_UNAVAILABLE')
    try:
        receipt = json.loads(result['stdout'])
    except (ValueError, KeyError):
        raise RuntimeError('QUERY_RECEIPT_INVALID') from None
    if receipt.get('job_id') != job_id or receipt.get('status') not in ('completed','incomplete','not_found'):
        raise RuntimeError('QUERY_RECEIPT_INVALID')
    return receipt


def main(action: str = 'plan', job_id: str = '', input_path: str = '', sql_path: str = '',
         threads: int = 4, memory_gib: int = 8, spill_gib: int = 20, result_gib: int = 2,
         timeout_seconds: int = 300, windmill_job_id: str = ''):
    """Owner-reviewed SQL only; original data stays on Foo. No implicit retries.

    plan: choose resources without running. submit: enqueue once, then inspect
    returned Windmill ID and logical ID. status/results read a bounded local
    receipt and never return query rows. cancel is an explicit user action.
    """
    if action not in ('plan','submit','status','results','cancel'):
        raise ValueError('QUERY_ACTION_INVALID')
    if os.environ.get('WM_WORKSPACE') != 'offmenu' or os.environ.get('WM_USERNAME') != 'admin':
        raise ValueError('QUERY_OWNER_REQUIRED')
    if action in ('status','results'):
        response = {'job_id': job_id, 'query': _receipt(job_id)}
        if windmill_job_id:
            if not _UUID.fullmatch(windmill_job_id):
                raise ValueError('WINDMILL_JOB_ID_INVALID')
            job = wmill.get_job(windmill_job_id)
            if job.get('script_path') != _RUNNER or job.get('args', {}).get('job_id') != job_id:
                raise ValueError('WINDMILL_JOB_ID_MISMATCH')
            state = wmill.get_job_status(windmill_job_id)
            state = getattr(state, 'value', state)
            response['windmill_status'] = str(state)
            if state == 'COMPLETED':
                response['windmill_success'] = job.get('success')
                if job.get('success') is True:
                    result = wmill.get_result(windmill_job_id)
                    if result.get('job_id') != job_id:
                        raise ValueError('WINDMILL_RESULT_ID_MISMATCH')
                    host = result.get('receipt', {})
                    response['admission'] = {'admitted':result.get('admitted'),
                                             'job_succeeded':result.get('job_succeeded'),
                                             'status':host.get('status'),
                                             'reason':host.get('reason'),
                                             'child_tree_gone':host.get('child_tree_gone')}
        if response['query']['status'] == 'completed':
            response['local_result'] = '/offmenu/data/.offmenu-platform/sql_queries/' + job_id + '/result.parquet'
            response['local_profile'] = '/offmenu/data/.offmenu-platform/sql_queries/' + job_id + '/profile.json'
        return response
    ns = _query_namespace()
    if action == 'cancel':
        if not isinstance(job_id, str) or not ns['JOB'].fullmatch(job_id):
            raise ValueError('QUERY_JOB_ID_INVALID')
        child = wmill.run_script_by_path_async(_RUNNER, args={'action':'cancel','job_id':job_id})
        return {'job_id':job_id,'cancellation_job_id':child,'terminal':False}
    plan = ns['make_plan'](job_id, input_path, sql_path, threads=threads,
                           memory_gib=memory_gib, spill_gib=spill_gib, result_gib=result_gib)
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 1800:
        raise ValueError('QUERY_TIMEOUT_INVALID')
    if action == 'plan':
        return {'plan':plan,'timeout_seconds':timeout_seconds,'submitted':False,
                'query_source_sha256':hashlib.sha256(base64.b64decode(_QUERY_SOURCE_B64)).hexdigest()}
    payload = base64.b64encode(json.dumps(plan,sort_keys=True).encode()).decode()
    command = _command("ns['run'](json.loads(base64.b64decode(" + repr(payload) + ")))")
    if len(command.encode()) > 32000:
        raise ValueError('QUERY_COMMAND_TOO_LARGE')
    child = wmill.run_script_by_path_async(_RUNNER, args={
        'action':'run','job_id':job_id,'mode':'write','timeout_seconds':timeout_seconds,
        'command':command,'resources':plan['resources']})
    return {'job_id':job_id,'windmill_job_id':child,'submitted':True,'admitted':None,
            'run_url':'https://windmill.aldous.info/run/' + child + '?workspace=offmenu',
            'resources':plan['resources'],'engine':plan['engine'],
            'next':{'action':'status','job_id':job_id,'windmill_job_id':child}}
