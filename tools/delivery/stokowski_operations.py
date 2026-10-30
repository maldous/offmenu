"""Durable, single-owner asynchronous handoff to the existing Windmill bridge.

This is an operation journal, not a scheduler. A Stokowski stage calls one tick;
network ambiguity never creates a new operation or retries a side effect blindly.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import sqlite3
import time
from uuid import UUID, uuid5, NAMESPACE_URL

from symphony_capacity import digest, valid_branch

BRIDGE = 'u/admin/foo_jobs_20261027'
BASE_URL = 'https://windmill.aldous.info'
POLICY = Path(__file__).with_name('capacity-policy.json')
PROFILES = {'delivery-suite':['.venv-delivery/bin/python','-m','unittest','discover','-s','tests/delivery','-q']}
TERMINAL = {'succeeded','failed','cancelled','refused','quarantined'}
# The reviewed computation timeout is 180s; allow 30s for wrapper completion.
# This only admits a status observation, never replacement computation.
WRAPPER_GRACE_SECONDS = 210


class OperationError(RuntimeError):
    pass


class TransportUnavailable(OperationError):
    pass


class RequestRefused(OperationError):
    pass


class RPCIdentityError(OperationError):
    pass


class ToolResultIncompleteError(OperationError):
    pass


class ToolResultTruncatedError(ToolResultIncompleteError):
    pass


class ObservationBindingError(OperationError):
    pass


def safe_diagnosis(error):
    # Exact types only: never serialize an arbitrary exception name or message.
    stages = {RPCIdentityError:'rpc-identity',
              ToolResultIncompleteError:'tool-result-incomplete',
              ToolResultTruncatedError:'tool-result-truncated',
              ObservationBindingError:'observation-binding',
              TransportUnavailable:'transport', RequestRefused:'refusal',
              OperationError:'protocol', TimeoutError:'transport',
              ValueError:'protocol', TypeError:'protocol'}
    kind = type(error)
    return {'stage':stages.get(kind, 'unknown'),
            'exception_class':kind.__name__ if kind in stages else 'OtherError'}


def observation_matches(remote, job_id, expected):
    if (not isinstance(remote, dict) or remote.get('id') != job_id or
        remote.get('workspace_id') != 'offmenu' or remote.get('script_path') != BRIDGE):
        return False
    if 'inspect_version' not in remote:
        return 'args_sha256' not in remote and remote.get('args') == expected
    from windmill_dispatcher import INSPECT_VERSION, compact_result
    if (remote.get('inspect_version') != INSPECT_VERSION or 'args' in remote or
        set(remote) != {'id','workspace_id','script_path','type','running','success',
                        'inspect_version','args_sha256','result'} or
        remote.get('args_sha256') != digest(expected) or
        remote.get('type') not in ('QueuedJob','CompletedJob') or
        type(remote.get('running')) is not bool or
        remote['type'] == 'CompletedJob' and
            (remote['running'] or type(remote['success']) is not bool) or
        remote['type'] == 'QueuedJob' and remote['success'] is not None):
        return False
    try:
        if compact_result(remote['result']) != remote['result']:
            return False
    except (ValueError, TypeError):
        return False
    return True


def validated(spec):
    fields = {'version','issue_id','issue','stage','head','base','owner','policy_sha256',
              'acceptance_sha256','outputs','profile','runner_sha256','executor_sha256'}
    if isinstance(spec, dict) and type(spec.get('version')) is int and spec['version'] == 2:
        return validated_v2(spec)
    if not isinstance(spec,dict) or set(spec) not in (fields,fields|{'branch'}) or type(spec['version']) is not int or spec['version'] != 1:
        raise OperationError('Invalid operation fields')
    if not valid_branch(spec.get('branch','feature/langgraph-delivery-standardization')):
        raise OperationError('Invalid exact selected branch')
    if str(UUID(spec['issue_id'])) != spec['issue_id'] or not re.fullmatch(r'UIF-[1-9][0-9]*',spec['issue']):
        raise OperationError('Invalid issue identity')
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,39}',spec['stage']):
        raise OperationError('Invalid stage')
    if not isinstance(spec['owner'],str) or not spec['owner'].strip():
        raise OperationError('Missing operation owner')
    for name,width in [('head',40),('base',40),('policy_sha256',64),('acceptance_sha256',64),
                       ('runner_sha256',64),('executor_sha256',64)]:
        if not isinstance(spec[name],str) or not re.fullmatch('[0-9a-f]{'+str(width)+'}',spec[name]):
            raise OperationError('Invalid '+name)
    if spec['profile'] not in PROFILES:
        raise OperationError('Unreviewed validation profile')
    if not isinstance(spec['outputs'],dict) or not 1 <= len(spec['outputs']) <= 64:
        raise OperationError('Missing accepted outputs')
    for name,value in spec['outputs'].items():
        path = PurePosixPath(name)
        if (not name or path.is_absolute() or '\\' in name or str(path) != name
            or any(p in ('','.','..') for p in name.split('/'))
            or path.parts[0] not in ('src','apps','tests','tools','scripts','docs','contracts','config')
            or not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value)):
            raise OperationError('Invalid output binding')
    return spec


WORKSPACES = PurePosixPath('/offmenu/data/.offmenu-platform/workspaces')
EXTRACTION_PROFILE = 'wfp-retained-mapping'
WFP_OUTPUTS = {'src/offmenu/refresh/wfp_retained.py', 'tests/test_wfp_retained.py',
               'tests/wfp-retained-authored-fixtures.json',
               'docs/operations/wfp-retained-normalization.md'}


def workspace_path(value):
    if (not isinstance(value, str) or
        not re.fullmatch(re.escape(str(WORKSPACES)) + r'/[A-Za-z0-9][A-Za-z0-9_-]{0,79}', value)):
        raise OperationError('Invalid exact workspace')
    return Path(value)


def validated_v2(spec):
    extra = {'origin', 'workspace', 'execution'}
    legacy = {k:v for k,v in spec.items() if k not in extra}
    if not extra.issubset(spec) or 'branch' not in legacy or spec.get('profile') != EXTRACTION_PROFILE:
        raise OperationError('Invalid v2 operation fields/profile')
    validated(dict(legacy, version=1, profile='delivery-suite'))
    workspace_path(spec['workspace'])
    origin = spec['origin']
    if (not isinstance(origin, dict) or set(origin) !=
        {'kind','admission_sha256','review_sha256','source_commit','mapping','author'} or
        origin['kind'] != 'reviewed-extraction' or not isinstance(origin['author'], str) or
        not origin['author'].strip()):
        raise OperationError('Invalid reviewed extraction origin')
    for name, width in [('admission_sha256',64),('review_sha256',64),('source_commit',40)]:
        if not isinstance(origin[name], str) or not re.fullmatch('[0-9a-f]{'+str(width)+'}', origin[name]):
            raise OperationError('Invalid origin pin')
    mapping = origin['mapping']
    if (not isinstance(mapping, dict) or set(mapping.values()) != WFP_OUTPUTS or
        len(mapping) != len(WFP_OUTPUTS) or set(spec['outputs']) != WFP_OUTPUTS):
        raise OperationError('Invalid retained mapping/layout')
    for name in mapping:
        if (not isinstance(name,str) or name.startswith('/') or '\\' in name or
            any(part in ('','.','..') for part in name.split('/')) or
            any(ord(char)<32 for char in name)):
            raise OperationError('Invalid retained mapping path')
    execution = spec['execution']
    if (not isinstance(execution,dict) or set(execution) !=
        {'task_fit','requested_model','requested_effort','provider_route','resolved_model','resolution_status'} or
        execution['task_fit'] != 'deterministic retained byte mapping validation' or
        execution['requested_model'] is not None or execution['requested_effort'] is not None or
        execution['provider_route'] != 'none' or execution['resolved_model'] is not None or
        execution['resolution_status'] != 'not-applicable'):
        raise OperationError('Invalid execution metadata')
    if spec['acceptance_sha256'] != origin['admission_sha256']:
        raise OperationError('Acceptance must pin extraction admission')
    return spec


def candidate_check_code(spec, candidate_root=None):
    """Identical local/remote identity, layout and retained byte checks."""
    return """import hashlib,json,pathlib,subprocess
spec=json.loads(SPEC_JSON)
root=pathlib.Path(LOCAL_SOURCE_ROOT)
assert root.resolve()==root and not any(p.is_symlink() for p in (root,*root.parents)), 'workspace alias'
def git(*args): return subprocess.check_output(['git','-C',str(root),*args])
assert git('rev-parse','--show-toplevel').decode().strip()==str(root), 'wrong checkout'
assert git('rev-parse','HEAD').decode().strip()==spec['head'], 'head drift'
assert git('branch','--show-current').decode().strip()==spec['branch'], 'branch drift'
assert not git('status','--porcelain','--untracked-files=all'), 'dirty candidate'
subprocess.run(['git','-C',str(root),'merge-base','--is-ancestor',spec['base'],spec['head']],check=True)
changed=set(filter(None,git('diff','--no-renames','--name-only','-z',spec['base'],spec['head']).decode().split('\\0')))
assert changed==set(spec['outputs']), 'extraction layout drift'
for old,new in spec['origin']['mapping'].items():
 path=root/new
 assert not any(p.is_symlink() for p in (path,*path.parents)), 'output alias'
 expected=spec['outputs'][new]
 assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==expected, 'output drift'
 assert hashlib.sha256(git('show',spec['head']+':'+new)).hexdigest()==expected, 'head output drift'
 assert git('ls-tree',spec['origin']['source_commit'],'--',old).split()[:2] in ([b'100644',b'blob'],[b'100755',b'blob']), 'nonregular retained source'
 assert hashlib.sha256(git('show',spec['origin']['source_commit']+':'+old)).hexdigest()==expected, 'mapping drift'
""".replace('LOCAL_SOURCE_ROOT',repr(
        str(candidate_root) if candidate_root is not None else spec['workspace']),1).replace(
        'SPEC_JSON',repr(json.dumps(spec,sort_keys=True)),1)


def extraction_arguments(spec):
    root = spec['workspace']
    check = '/offmenu/.venv-delivery/bin/python -c '+shlex.quote(candidate_check_code(spec))
    # Reuse accepted-base archive handling; select candidate paths explicitly and
    # keep the shared interpreter independent of that checkout's contents.
    control = shlex.split(trusted_validation_command(spec))[2]
    control = control.replace("pathlib.Path('/offmenu')", 'pathlib.Path('+repr(root)+')')
    control = control.replace("str(root/'.venv-delivery/bin/python')", "'/offmenu/.venv-delivery/bin/python'")
    control = control.replace("env=dict(os.environ,PYTHONPATH=str(root/'src')+':'+str(root))",
        "env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(root/'src')+':'+str(root)+':'+str(control/'tests/delivery'))")
    profile = ("import pathlib; import offmenu.refresh.wfp_retained as module; "
               "assert pathlib.Path(module.__file__).resolve()==pathlib.Path("+
               repr(root+'/src/offmenu/refresh/wfp_retained.py')+"); "
               "assert len(module.COLUMNS)==16 and module.POLICY['accepted'] is False")
    commands = ['cd /offmenu',
        'export PYTHONPATH=/offmenu/src GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0=/offmenu',
        'export PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0',
        'cd '+shlex.quote(root),
        'export PYTHONPATH='+shlex.quote(root+'/src:'+root+':'+root+'/tests/delivery')+
            ' GIT_CONFIG_VALUE_0='+shlex.quote(root),
        check, '/offmenu/.venv-delivery/bin/python -c '+shlex.quote(profile),
        '/offmenu/.venv-delivery/bin/python -c '+shlex.quote(control),
        '/offmenu/.venv-delivery/bin/python -m offmenu.delivery check',
        '/offmenu/.venv-delivery/bin/python scripts/check_final_layout.py', check]
    return {'action':'run','job_id':'offmenu-'+operation_key(spec)[:48],
            'command':' && '.join(commands),'mode':'read','timeout_seconds':180,
            'resources':{'workers':1,'overhead_processes':8,'cpu_millis':1000,
                         'memory_bytes':2147483648,'io_slots':1,'output_bytes':0,
                         'read_roots':['/offmenu'],'write_roots':[]}}


def operation_key(spec):
    validated(spec)
    # Changing the owner does not manufacture a different operation. The same
    # semantic operation with a different owner fails the immutable binding.
    return digest({k:v for k,v in spec.items() if k != 'owner'})


def trusted_validation_command(spec):
    """Load authoritative tests from the immutable accepted control commit.

    Only authored regular test files are materialized. Runtime imports and tool
    paths point at the candidate so old checks exercise its actual behavior.
    Candidate tests also run separately; they cannot replace this baseline.
    """
    code = """import io,os,pathlib,subprocess,tarfile,tempfile
root=pathlib.Path('/offmenu')
base=CONTROL_BASE
archive=subprocess.check_output(['git','-C',str(root),'archive',base,'tests/delivery'])
with tempfile.TemporaryDirectory(prefix='offmenu-accepted-validation-') as directory:
 control=pathlib.Path(directory)
 with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
  for member in bundle:
   path=pathlib.PurePosixPath(member.name)
   assert not path.is_absolute() and '..' not in path.parts
   if member.isdir(): continue
   assert path.parts[:2]==('tests','delivery')
   assert member.isfile(), 'nonregular accepted validator'
   target=control/path
   target.parent.mkdir(parents=True,exist_ok=True)
   target.write_bytes(bundle.extractfile(member).read())
 for child in root.iterdir():
  if child.name!='tests': (control/child.name).symlink_to(child)
 env=dict(os.environ,PYTHONPATH=str(root/'src')+':'+str(root))
 print('ACCEPTED_CONTROL_VALIDATORS '+base,flush=True)
 subprocess.run([str(root/'.venv-delivery/bin/python'),'-m','unittest','discover','-s',str(control/'tests/delivery'),'-q'],cwd=control,env=env,check=True)
""".replace('CONTROL_BASE',repr(spec['base']))
    return 'python3 -c '+shlex.quote(code)


def bridge_arguments(spec, action='run'):
    key = operation_key(spec)
    logical_id = 'offmenu-'+key[:48]
    if action != 'run':
        if action not in ('status','cancel'):
            raise OperationError('Invalid bridge action')
        return {'action':action,'job_id':logical_id}
    if spec['version'] == 2:
        return extraction_arguments(spec)
    output_code = ("import hashlib,json,pathlib; expected=json.loads("+repr(json.dumps(spec['outputs'],sort_keys=True))+
        "); root=pathlib.Path('/offmenu'); "
        "assert all(not any(x.is_symlink() for x in [root/p,*(root/p).parents]) "
        "and (root/p).resolve().is_relative_to(root.resolve()) and (root/p).is_file() and "
        "hashlib.sha256((root/p).read_bytes()).hexdigest()==h for p,h in expected.items()); "
        "print(json.dumps({'accepted_outputs':expected},sort_keys=True))")
    head = shlex.quote(spec['head'])
    held_code = ("import subprocess,json; policy=json.loads(subprocess.check_output(['git','show',"+
                 repr(spec['base']+':repository-standard.json')+
                 "])); actual=set(filter(None,subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z']).decode().split('\\0'))); "
                 "assert not actual-set(policy.get('runtime_hold_paths',[]))")
    identity = ('test "$(git rev-parse HEAD)" = '+head+
                ' && test "$(git branch --show-current)" = '+shlex.quote(spec.get('branch','feature/langgraph-delivery-standardization'))+
                ' && git diff --quiet HEAD -- && python3 -c '+shlex.quote(held_code))
    commands = ['cd /offmenu',
        'export PYTHONPATH=/offmenu/src GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0=/offmenu',
        identity, trusted_validation_command(spec), shlex.join(PROFILES[spec['profile']]),
        'python3 -c '+shlex.quote(output_code), identity]
    return {'action':'run','job_id':logical_id,'command':' && '.join(commands),
            'mode':'read','timeout_seconds':180,
            'resources':{'workers':1,'overhead_processes':8,'cpu_millis':1000,
                         'memory_bytes':2147483648,'io_slots':1,'output_bytes':0,
                         'read_roots':['/offmenu'],'write_roots':[]}}


class Journal:
    def __init__(self,root):
        self.root = Path(root)
        for part in (self.root,*self.root.parents):
            if part.is_symlink():
                raise OperationError('Symlink operation root')
        self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.path = self.root/'operations.sqlite'
        if self.path.is_symlink():
            raise OperationError('Symlink operation database')
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS operations (key TEXT PRIMARY KEY,spec TEXT NOT NULL,state TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS events (sequence INTEGER PRIMARY KEY,key TEXT NOT NULL,event TEXT NOT NULL,at REAL NOT NULL)')

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path,timeout=10)
        os.chmod(self.path,0o600)
        try:
            with db:
                yield db
        finally:
            db.close()

    @contextmanager
    def claim(self,key):
        if not re.fullmatch('[0-9a-f]{64}',key):
            raise OperationError('Invalid operation key')
        fd = os.open(self.root/(key+'.lock'),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            try:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                raise OperationError('Operation already owned by another tick') from None
            yield
        finally:
            os.close(fd)

    def prepare(self,spec):
        key = operation_key(spec)
        with self.claim(key),self.db() as db:
            existing = db.execute('SELECT spec FROM operations WHERE key=?',(key,)).fetchone()
            canonical = json.dumps(spec,sort_keys=True)
            if existing:
                if existing[0] != canonical:
                    raise OperationError('Immutable operation/owner conflict')
                return key
            state = {'status':'prepared','windmill_job_id':str(uuid5(NAMESPACE_URL,'offmenu:run:'+key)),
                     'cancel_job_id':str(uuid5(NAMESPACE_URL,'offmenu:cancel:'+key)),
                     'logical_job_id':bridge_arguments(spec)['job_id'],'cancel_requested':False}
            db.execute('INSERT INTO operations VALUES(?,?,?)',(key,canonical,json.dumps(state)))
            db.execute('INSERT INTO events(key,event,at) VALUES(?,?,?)',(key,'prepared',time.time()))
        return key

    def read(self,key):
        with self.db() as db:
            row = db.execute('SELECT spec,state FROM operations WHERE key=?',(key,)).fetchone()
            if not row:
                raise OperationError('Unknown operation')
            return json.loads(row[0]),json.loads(row[1])

    def save(self,key,state,event):
        with self.db() as db:
            db.execute('UPDATE operations SET state=? WHERE key=?',(json.dumps(state,sort_keys=True),key))
            db.execute('INSERT INTO events(key,event,at) VALUES(?,?,?)',(key,event,time.time()))

    def diagnose(self,key,state,event,error):
        state['diagnosis'] = safe_diagnosis(error)
        diagnosis = state['diagnosis']
        self.save(key,state,event+':'+diagnosis['stage']+':'+diagnosis['exception_class'])

    def cancel(self,key):
        with self.claim(key):
            _,state = self.read(key)
            if state['status'] not in TERMINAL:
                state['cancel_requested'] = True
                self.save(key,state,'cancellation-requested')

    async def tick(self,key,transport):
        with self.claim(key):
            spec,state = self.read(key)
            if state['status'] in TERMINAL:
                return state
            if (hashlib.sha256(POLICY.read_bytes()).hexdigest() != spec['policy_sha256']
                or hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != spec['executor_sha256']):
                state['status'] = 'quarantined'
                self.save(key,state,'policy-drift')
                return state
            try:
                remote = await transport.inspect(state['windmill_job_id'])
                if remote is None:
                    if state['status'] != 'prepared':
                        state['status'] = 'unknown'
                        self.diagnose(key,state,'unseen-submission-requires-reconciliation',ToolResultIncompleteError())
                        return state
                    if state['cancel_requested']:
                        state['status'] = 'cancelled'
                        self.save(key,state,'cancelled-before-submission')
                        return state
                    # Persist before network mutation. Even a crash or lost API
                    # response leaves the exact UUID available for inspection.
                    state['status'] = 'submit-intent'
                    self.save(key,state,'submit-intent')
                    await transport.submit(state['windmill_job_id'],bridge_arguments(spec))
                    state['status'] = 'submitted'
                    self.save(key,state,'submitted')
                    return state
                if not observation_matches(remote, state['windmill_job_id'], bridge_arguments(spec)):
                    state['status'] = 'quarantined'
                    self.diagnose(key,state,'remote-binding-conflict',ObservationBindingError())
                    return state
                if state['cancel_requested'] and remote.get('type','').lower() != 'completedjob':
                    control = await transport.inspect(state['cancel_job_id'])
                    if control is not None and not observation_matches(
                        control, state['cancel_job_id'], bridge_arguments(spec,'cancel')):
                        state['status'] = 'quarantined'
                        self.diagnose(key,state,'cancel-binding-conflict',ObservationBindingError())
                        return state
                    if control is None and not state.get('cancel_intent'):
                        state['cancel_intent'] = True
                        self.save(key,state,'backend-cancel-intent')
                        await transport.submit(state['cancel_job_id'],bridge_arguments(spec,'cancel'))
                    # Cancelling the API wrapper alone cannot prove the Foo
                    # subprocess stopped. Keep ownership until its receipt does.
                    state['status'] = 'cancel-requested'
                    self.save(key,state,'awaiting-backend-termination')
                    # Keep the same cancellation intent and backend identity.
                    # An old running wrapper can still mask stopped Foo work.
                if remote.get('type','').lower() != 'completedjob':
                    state['status'] = ('cancel-requested' if state['cancel_requested'] else
                                       ('running' if remote.get('running') else 'queued'))
                    now = time.time()
                    if not remote.get('running'):
                        state.pop('wrapper_observed_at', None)
                    since = state.setdefault('wrapper_observed_at', now) if remote.get('running') else now
                    self.save(key,state,'observed-'+state['status'])
                    # Queued work has not necessarily started. A grace expiry
                    # is not proof of failure, completion or permission to retry.
                    if not remote.get('running') or now - since < WRAPPER_GRACE_SECONDS:
                        return state
                    state['wrapper_stale'] = True
                    self.save(key,state,'stale-wrapper-backend-observation')
                    result = await self.backend_observation(key,spec,state,transport)
                    if result is None:
                        return state
                else:
                    result = remote.get('result')
                if (not isinstance(result,dict) or not isinstance(result.get('receipt'),dict)
                    or result['receipt'].get('status') not in ('succeeded','failed','timed_out','cancelled')):
                    # A failed Windmill wrapper may still have a fully reconciled
                    # business failure in Foo. Observe that receipt; never rerun
                    # the validation just to recover its result.
                    result = await self.backend_observation(key,spec,state,transport)
                    if result is None:
                        return state
                if not isinstance(result,dict) or result.get('job_id') != state['logical_job_id']:
                    state['status'] = 'unknown'
                    self.diagnose(key,state,'wrapper-result-not-backend-proof',ObservationBindingError())
                    return state
                receipt = result.get('receipt',{})
                status = receipt.get('status')
                expected = bridge_arguments(spec)
                bound = (receipt.get('job_id') == state['logical_job_id']
                         and receipt.get('command_sha256') == hashlib.sha256(expected['command'].encode()).hexdigest()
                         and receipt.get('runner_sha256') == spec['runner_sha256']
                         and receipt.get('capacity_policy_sha256') == spec['policy_sha256'])
                if status == 'succeeded' and (bound
                    and result.get('job_succeeded') is True and receipt.get('exit_code') == 0
                    and receipt.get('child_tree_gone') is True
                    and receipt.get('reconcile_required') is False
                    and receipt.get('capacity_policy_sha256') == spec['policy_sha256']):
                    state['status'] = 'cancelled' if state['cancel_requested'] else 'succeeded'
                elif status in ('failed','cancelled','timed_out') and bound and receipt.get('child_tree_gone') is True:
                    state['status'] = 'failed' if status == 'timed_out' else status
                else:
                    state['status'] = 'unknown'
                state['receipt_sha256'] = digest(receipt)
                state['accepted_output_sha256'] = spec['outputs'] if state['status'] == 'succeeded' else {}
                state['acceptance_sha256'] = spec['acceptance_sha256']
                if state['status'] == 'unknown':
                    error = ObservationBindingError() if not bound else ToolResultIncompleteError()
                    self.diagnose(key,state,'observed-unknown',error)
                else:
                    self.save(key,state,'observed-'+state['status'])
                return state
            except TransportUnavailable as error:
                # An observation outage changes no operation identity or intent.
                self.diagnose(key,state,'service-unavailable',error)
                return dict(state,deferred='service-unavailable')
            except RequestRefused as error:
                state['status'] = 'refused' if state['status'] in ('prepared','submit-intent') else 'unknown'
                self.diagnose(key,state,'authorization-refused-no-protocol-fallback',error)
                return state
            except Exception as error:
                state['status'] = 'unknown'
                self.diagnose(key,state,'network-or-protocol-outcome-unknown',error)
                return state

    async def backend_observation(self,key,spec,state,transport):
        sequence = state.get('observation_sequence',0)
        job_id = str(uuid5(NAMESPACE_URL,'offmenu:observe:'+key+':'+str(sequence)))
        expected = bridge_arguments(spec,'status')
        observed = await transport.inspect(job_id)
        if observed is None:
            if state.get('observation_intent'):
                state['status'] = 'unknown'
                self.diagnose(key,state,'observer-outcome-unknown',ToolResultIncompleteError())
                return None
            state['observation_intent'] = True
            self.save(key,state,'backend-observation-intent')
            await transport.submit(job_id,expected)
            return None
        if not observation_matches(observed, job_id, expected):
            state['status'] = 'quarantined'
            self.diagnose(key,state,'observer-binding-conflict',ObservationBindingError())
            return None
        if observed.get('type','').lower() != 'completedjob':
            return None
        value = observed.get('result')
        status = value.get('receipt',{}).get('status') if isinstance(value,dict) else None
        if status in ('running','starting','queued'):
            # Another pure observation may follow later; never a new business
            # submission. Persist the next observer's identity before use.
            state['observation_sequence'] = sequence+1
            state['observation_intent'] = False
            # Re-arm the finite grace rather than submit status work every tick.
            state['wrapper_observed_at'] = time.time()
            self.save(key,state,'backend-still-running')
            return None
        return value


class WindmillAPI:
    """Existing injected authentication only; no token creation or grant API."""
    def __init__(self,token,client=None):
        if not token:
            raise OperationError('Existing Windmill authentication was not injected')
        import httpx
        self.client = client or httpx.AsyncClient(base_url=BASE_URL+'/api',timeout=20,
                    headers={'Authorization':'Bearer '+token},follow_redirects=False)

    async def inspect(self,job_id):
        import httpx
        try:
            response = await self.client.get('/w/offmenu/jobs_u/get/'+str(UUID(job_id)))
        except httpx.TransportError:
            raise TransportUnavailable('Windmill observation unavailable') from None
        if response.status_code == 404:
            return None
        if response.status_code >= 500:
            raise TransportUnavailable('Windmill observation unavailable')
        if response.status_code in (401,403):
            raise RequestRefused('Windmill observation refused')
        response.raise_for_status()
        return response.json()

    async def submit(self,job_id,args):
        # v1.850.0 NewJobId is server-enforced across queued/completed jobs.
        response = await self.client.post('/w/offmenu/jobs/run/p/'+BRIDGE,
                    params={'job_id':str(UUID(job_id))},json=args)
        if response.status_code in (401,403):
            raise RequestRefused('Windmill submission refused')
        response.raise_for_status()
        if response.text.strip().strip('"') != job_id:
            raise OperationError('Unexpected Windmill job UUID')

    async def close(self):
        await self.client.aclose()

    @classmethod
    def injected(cls):
        token = os.environ.get('OFFMENU_WINDMILL_TOKEN')
        if not token and os.environ.get('WM_WORKSPACE') == 'offmenu':
            token = os.environ.get('WM_TOKEN')
        directory = os.environ.get('CREDENTIALS_DIRECTORY')
        if not token and directory and (Path(directory)/'windmill-api-token').is_file():
            token = (Path(directory)/'windmill-api-token').read_text().strip()
        return cls(token)
