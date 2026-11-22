# requirements:
# wmill==1.850.0
"""Typed OffMenu bridge dispatch using existing Windmill job-scoped SDK auth.

No credentials, schedules, infrastructure or grant APIs. This adapter never
executes locally and never cancels only an API wrapper in place of Foo cleanup.
"""
import ast
import hashlib
import json
import math
import os
import re
import shlex
from pathlib import Path, PurePosixPath
from uuid import UUID, NAMESPACE_URL, uuid5

BRIDGE = 'u/admin/foo_jobs_20261027'

# Portable qualification copied from the frozen v3 producer at 5ec30129.
# Windmill deploys this file alone: validation must not import the checkout.
REVIEWED_PROFILE = 'current-journal-focused'
PUBLISHER_PROFILE = 'protected-publisher-bootstrap'
IDENTITY_PROFILE = 'identity-client-focused'
IDENTITY_TESTS = ('tests/web/offmenu-identity-client.test.mjs',
                  'tests/edge/handler-auth-dispatch.test.mjs')
PROFILES = {'delivery-suite'}
ENRICHMENT_PROFILE = 'enrichment-resilience-focused'
ENRICHMENT_TEST = 'tests/web/enrichment-resilience.test.mjs'
PROFILES.add(ENRICHMENT_PROFILE)
ENRICHMENT_BODY_SHA256 = '489ce815134040311e8779d289bbfee59128cd85937b04b8a1340f446b9771cd'


def _reviewed_branch(value):
    return (isinstance(value,str) and bool(re.fullmatch(r'(?:feature|bugfix)/[a-z0-9][a-z0-9/-]{0,159}',value))
            and not value.endswith('/') and '//' not in value)


def _reviewed_workspace(value):
    if (not isinstance(value,str) or not re.fullmatch(
        r'/offmenu/data/\.offmenu-platform/workspaces/[A-Za-z0-9][A-Za-z0-9_-]{0,79}',value)):
        raise ValueError('Invalid exact workspace')


def _reviewed_legacy(spec):
    fields = {'version','issue_id','issue','stage','head','base','owner','policy_sha256',
              'acceptance_sha256','outputs','profile','runner_sha256','executor_sha256'}
    if not isinstance(spec,dict) or set(spec) not in (fields,fields|{'branch'}) or type(spec['version']) is not int or spec['version'] != 1:
        raise ValueError('Invalid operation fields')
    if not _reviewed_branch(spec.get('branch','feature/langgraph-delivery-standardization')):
        raise ValueError('Invalid exact selected branch')
    if str(UUID(spec['issue_id'])) != spec['issue_id'] or not re.fullmatch(r'UIF-[1-9][0-9]*',spec['issue']):
        raise ValueError('Invalid issue identity')
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,39}',spec['stage']):
        raise ValueError('Invalid stage')
    if not isinstance(spec['owner'],str) or not spec['owner'].strip():
        raise ValueError('Missing operation owner')
    for name,width in [('head',40),('base',40),('policy_sha256',64),('acceptance_sha256',64),
                       ('runner_sha256',64),('executor_sha256',64)]:
        if not isinstance(spec[name],str) or not re.fullmatch('[0-9a-f]{'+str(width)+'}',spec[name]):
            raise ValueError('Invalid '+name)
    if spec['profile'] not in PROFILES:
        raise ValueError('Unreviewed validation profile')
    if not isinstance(spec['outputs'],dict) or not 1 <= len(spec['outputs']) <= 64:
        raise ValueError('Missing accepted outputs')
    for name,value in spec['outputs'].items():
        path = PurePosixPath(name)
        if (not name or path.is_absolute() or '\\' in name or str(path) != name
            or any(p in ('','.','..') for p in name.split('/'))
            or (name not in ('AGENTS.md','repository-standard.json')
                and path.parts[0] not in ('src','apps','tests','tools','scripts','docs','contracts','config'))
            or not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value)):
            raise ValueError('Invalid output binding')
    return spec


def _canonical_derivations(provenance):
    """v3 review payload: sort by canonical JSON; reject duplicate entries.

    Object keys use sorted compact JSON (UTF-8); list order is lexical by that
    encoding. Every transformed reference contributes its exact derivation,
    excluding only review_sha256 so the prior review never hashes itself.
    """
    encoded = []
    for ref in provenance:
        if ref['derivation'] is not None:
            payload = {k:v for k,v in ref['derivation'].items() if k != 'review_sha256'}
            encoded.append(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False))
    if len(encoded) != len(set(encoded)):
        raise ValueError('Duplicate contribution derivation')
    return [json.loads(value) for value in sorted(encoded)]


def _qualified_reviewed_spec(spec):
    if not isinstance(spec,dict) or type(spec.get('version')) is not int or spec['version'] != 3:
        raise ValueError('Invalid reviewed-source version')
    extra = {'origin','workspace','local_source_root','execution','control_sha256'}
    legacy = {k:v for k,v in spec.items() if k not in extra}
    if not extra.issubset(spec) or 'branch' not in legacy or spec.get('profile') not in (REVIEWED_PROFILE, PUBLISHER_PROFILE, IDENTITY_PROFILE):
        raise ValueError('Invalid reviewed-source profile')
    _reviewed_legacy(dict(legacy, version=1, profile='delivery-suite'))
    _reviewed_workspace(spec['workspace'])
    root = Path(spec['local_source_root'])
    if not root.is_absolute() or str(root) != spec['local_source_root']:
        raise ValueError('Invalid reviewed-source mirror')
    origin = spec['origin']
    if (not isinstance(origin,dict) or set(origin) != {'kind','admission_sha256','review_sha256','author','authors','provenance'}
        or origin['kind'] != 'reviewed-source-v1' or not isinstance(origin['author'],str)
        or not origin['author'].strip() or not isinstance(origin['authors'],list)
        or not origin['authors'] or len(set(origin['authors'])) != len(origin['authors'])
        or origin['author'] not in origin['authors']
        or not all(isinstance(a,str) and a.strip() for a in origin['authors'])
        or not isinstance(origin['provenance'],list) or not origin['provenance']):
        raise ValueError('Invalid reviewed-source origin')
    for value in (origin['admission_sha256'],origin['review_sha256'],spec['control_sha256']):
        if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value):
            raise ValueError('Invalid reviewed-source pin')
    for ref in origin['provenance']:
        if (not isinstance(ref,dict) or set(ref) != {'path','sha256','author','owner','session','source_head','outputs','contribution_head','path_mapping','derivation'}
            or ref['author'] not in origin['authors'] or ref['author'] != ref['owner'] or not ref['owner'] or not ref['session']
            or not isinstance(ref['source_head'],str) or not re.fullmatch('[0-9a-f]{40}',ref['source_head'])
            or not isinstance(ref['contribution_head'],str) or not re.fullmatch('[0-9a-f]{40}',ref['contribution_head'])
            or not re.fullmatch('[0-9a-f]{64}',ref['sha256'])
            or not Path(ref['path']).is_absolute() or str(Path(ref['path'])) != ref['path']
            or not isinstance(ref['outputs'],dict) or not ref['outputs']
            or any(not isinstance(k,str) or not re.fullmatch('[0-9a-f]{64}',v) for k,v in ref['outputs'].items())):
            raise ValueError('Invalid manual provenance reference')
        mapping = ref['path_mapping']
        if (not isinstance(mapping,dict) or set(mapping) != set(ref['outputs'])
            or any(not isinstance(v,str) or v not in spec['outputs'] for v in mapping.values())
            or len(set(mapping.values())) != len(mapping)
            or any(not k or str(PurePosixPath(k)) != k or PurePosixPath(k).is_absolute()
                   or '\\' in k or any(p in ('','.','..') for p in k.split('/')) for k in mapping)):
            raise ValueError('Invalid contribution path mapping')
        derivation = ref['derivation']
        transformed = any(value != spec['outputs'][mapping[name]] for name,value in ref['outputs'].items())
        # The pinned executed oracle determines attached/detached ancestry.
        if transformed or derivation is not None:
            if (not isinstance(derivation,dict)
                or set(derivation) != {'owner','contribution_head','path_mapping','head','outputs','review_sha256','reason'}
                or derivation['owner'] != ref['owner']
                or derivation['contribution_head'] != ref['contribution_head']
                or derivation['path_mapping'] != mapping or derivation['head'] != spec['head']
                or derivation['outputs'] != {v:spec['outputs'][v] for v in mapping.values()}
                or derivation['review_sha256'] != origin['review_sha256']
                or not isinstance(derivation['reason'],str) or not derivation['reason'].strip()):
                raise ValueError('Changed contribution needs exact reviewed derivation')
        elif derivation is not None:
            raise ValueError('Unexpected contribution derivation')
    _canonical_derivations(origin['provenance'])
    if set(a['author'] for a in origin['provenance']) != set(origin['authors']):
        raise ValueError('Incomplete manual author lineage')
    if (spec['execution'] != dict(task_fit='deterministic reviewed source validation',
        requested_model=None,requested_effort=None,provider_route='none',resolved_model=None,
        resolution_status='not-applicable') or spec['acceptance_sha256'] != origin['admission_sha256']):
        raise ValueError('Invalid reviewed-source execution/admission')
    return spec


# Full immutable body templates from reviewed_check_code/reviewed_arguments.
REVIEWED_CHECK_SHA256 = '8409648a10d0224b6e450348e91e5172fe2def9c56f9520ffe8d27d36bcabb13'
REVIEWED_ORACLE_SHA256 = '688542af44b51ffb02ad5db5c9b0499e07ca660db6975fa25e8a9e38021449f2'
PUBLISHER_ORACLE_SHA256 = 'f3cb99f2dc0689dc148f1583f75e088c43ac05d9592e95407ee580ff1b2afd62'
# Frozen identity producer body from operations.py 01f50d80; literal parameters only.
IDENTITY_BODY_SHA256 = 'b6d15ead2c781c667769928815c50aefa2f16fb1a723552752783843b4378597'


def _unique_json(pairs):
    result = {}
    for key,value in pairs:
        if key in result:
            raise ValueError('Duplicate embedded spec key')
        result[key] = value
    return result


def _body_hash(body, parameters):
    lines = body.splitlines(keepends=True)
    for original,placeholder in parameters:
        line = original+'\n'
        if lines.count(line) != 1:
            raise ValueError('Noncanonical body parameter')
        lines[lines.index(line)] = placeholder+'\n'
    return hashlib.sha256(''.join(lines).encode()).hexdigest()


def _identity_command(command, logical_id, tokens):
    """Qualify the frozen single-body producer without importing or executing it."""
    body = tokens[2]
    canonical = '/offmenu/.venv-delivery/bin/python -c '+shlex.quote(body)
    if tokens[:2] != ['/offmenu/.venv-delivery/bin/python','-c'] or command != canonical:
        raise ValueError('Noncanonical identity shell')
    parsed = ast.parse(body)
    root = ast.literal_eval(parsed.body[1].value.args[0])
    oracle = ast.literal_eval(parsed.body[2].value)
    if not isinstance(root,str) or not isinstance(oracle,str):
        raise ValueError('Invalid identity literals')
    _reviewed_workspace(root)
    parsed_oracle = ast.parse(oracle)
    spec_json = ast.literal_eval(parsed_oracle.body[1].value.args[0])
    if not isinstance(spec_json,str):
        raise ValueError('Invalid embedded identity spec')
    spec = json.loads(spec_json,object_pairs_hook=_unique_json)
    _qualified_reviewed_spec(spec)
    if spec['profile'] != IDENTITY_PROFILE:
        raise ValueError('Identity body requires exact profile')
    key = hashlib.sha256(json.dumps({k:v for k,v in spec.items() if k != 'owner'},
        sort_keys=True,separators=(',', ':')).encode()).hexdigest()
    if spec['workspace'] != root or logical_id != 'offmenu-'+key[:48]:
        raise ValueError('Conflicting identity binding')
    check_hash = _body_hash(oracle,[
        ('spec=json.loads('+repr(json.dumps(spec,sort_keys=True))+')','SPEC'),
        ('root=pathlib.Path('+repr(root)+')','ROOT')])
    body_hash = _body_hash(body,[
        ('root=pathlib.Path('+repr(root)+')','ROOT'),
        ('oracle='+repr(oracle),'ORACLE'),
        ("archive=subprocess.check_output(['git','-C',str(root),'archive',"+repr(spec['base'])+",*"+repr(IDENTITY_TESTS)+"])",'ARCHIVE'),
        ("assert hashlib.sha256(archive).hexdigest()=="+repr(spec['control_sha256'])+", 'control source drift'",'CONTROL')])
    if check_hash != REVIEWED_CHECK_SHA256 or body_hash != IDENTITY_BODY_SHA256:
        raise ValueError('Unreviewed identity Python body')
    return key


def _enrichment_command(command, logical_id, tokens):
    """Recognize only the complete frozen native-v1 Node wrapper; never eval."""
    body = tokens[2]
    if (tokens[:2] != ['/offmenu/.venv-delivery/bin/python','-c']
        or command != '/offmenu/.venv-delivery/bin/python -c '+shlex.quote(body)):
        raise ValueError('Noncanonical enrichment shell')
    parsed = ast.parse(body)
    spec_json = ast.literal_eval(parsed.body[1].value.args[0])
    root = ast.literal_eval(parsed.body[2].value.args[0])
    if not isinstance(spec_json,str):
        raise ValueError('Invalid enrichment literals')
    spec = json.loads(spec_json,object_pairs_hook=_unique_json)
    _reviewed_legacy(spec)
    if spec['profile'] != ENRICHMENT_PROFILE or set(spec['outputs']) != {ENRICHMENT_TEST}:
        raise ValueError('Enrichment body requires exact native profile/output')
    _reviewed_workspace(root)
    if root != '/offmenu/data/.offmenu-platform/workspaces/enrichment-'+spec['head']:
        raise ValueError('Invalid derived enrichment root')
    key = hashlib.sha256(json.dumps({k:v for k,v in spec.items() if k != 'owner'},
        sort_keys=True,separators=(',', ':')).encode()).hexdigest()
    if logical_id != 'offmenu-'+key[:48] or _body_hash(body,[
        ('spec=json.loads('+repr(json.dumps(spec,sort_keys=True))+')','SPEC'),
        ('root=pathlib.Path('+repr(root)+')','ROOT')]) != ENRICHMENT_BODY_SHA256:
        raise ValueError('Unreviewed enrichment binding/body')
    return key


def _reviewed_command(command, logical_id):
    try:
        tokens = shlex.split(command)
        if len(tokens) == 3:
            parsed = ast.parse(tokens[2])
            if (len(parsed.body) > 1 and isinstance(parsed.body[1],ast.Assign)
                and isinstance(parsed.body[1].targets[0],ast.Name)
                and parsed.body[1].targets[0].id == 'spec'):
                return _enrichment_command(command,logical_id,tokens)
            return _identity_command(command,logical_id,tokens)
        if len(tokens) != 19 or tokens[10] != tokens[18]:
            raise ValueError('Invalid complete reviewed command')
        root,check,oracle = tokens[1],tokens[10],tokens[14]
        _reviewed_workspace(root)
        python = '/offmenu/.venv-delivery/bin/python -c '
        canonical = ' && '.join([
            'cd '+shlex.quote(root),
            'export PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 PYTHONPATH='+shlex.quote(
                root+'/tools/delivery:'+root+'/src:/offmenu/.delivery/stokowski/venv/lib/python3.12/site-packages'),
            python+shlex.quote(check),python+shlex.quote(oracle),python+shlex.quote(check)])
        if command != canonical:
            raise ValueError('Noncanonical reviewed shell')
        # Parse literals only. The complete body is subsequently pinned below.
        parsed = ast.parse(check)
        spec_json = ast.literal_eval(parsed.body[1].value.args[0])
        if not isinstance(spec_json,str):
            raise ValueError('Invalid embedded spec literal')
        spec = json.loads(spec_json,object_pairs_hook=_unique_json)
        _qualified_reviewed_spec(spec)
        if spec['profile'] not in (REVIEWED_PROFILE,PUBLISHER_PROFILE):
            raise ValueError('Legacy body requires original profile')
        key = hashlib.sha256(json.dumps({k:v for k,v in spec.items() if k != 'owner'},
            sort_keys=True,separators=(',', ':')).encode()).hexdigest()
        if spec['workspace'] != root or logical_id != 'offmenu-'+key[:48]:
            raise ValueError('Conflicting reviewed identity')
        check_hash = _body_hash(check,[
            ('spec=json.loads('+repr(json.dumps(spec,sort_keys=True))+')','SPEC'),
            ('root=pathlib.Path('+repr(root)+')','ROOT')])
        oracle_hash = _body_hash(oracle,[
            ('root=pathlib.Path('+repr(root)+')','ROOT'),
            ("archive=subprocess.check_output(['git','-C',str(root),'archive',"+repr(spec['base'])+",*files])",'ARCHIVE'),
            ("assert hashlib.sha256(archive).hexdigest()=="+repr(spec['control_sha256'])+", 'control source drift'",'CONTROL')])
        expected_oracle = (PUBLISHER_ORACLE_SHA256 if spec['profile'] == PUBLISHER_PROFILE
                           else REVIEWED_ORACLE_SHA256)
        if check_hash != REVIEWED_CHECK_SHA256 or oracle_hash != expected_oracle:
            raise ValueError('Unreviewed Python body')
        return key
    except (AttributeError,IndexError,KeyError,TypeError,SyntaxError,RecursionError) as error:
        raise ValueError('Invalid reviewed command') from error


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
    if (not isinstance(command,str) or '\0' in command or len(command.encode()) > 32000):
        raise ValueError('Unreviewed command envelope')
    if not command.startswith('cd /offmenu && export PYTHONPATH=/offmenu/src '):
        _reviewed_command(command,value['job_id'])
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
    if (request['action'] == 'run'
        and not request['command'].startswith('cd /offmenu && export PYTHONPATH=/offmenu/src ')):
        key = _reviewed_command(request['command'],request['job_id'])
        if job_id != str(uuid5(NAMESPACE_URL,'offmenu:run:'+key)):
            raise ValueError('Conflicting reserved Windmill job UUID')
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
