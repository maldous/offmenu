"""Finite native SSH caller for the existing metadata-only publication API.

Future wiring: the existing owner/service invokes this module once with a reviewed
stdin request, installed Git blob pins and pinned config/handoff/task/claim refs.
It must separately qualify caller_association.native_route and handoff.native_route
as ROUTE below. Compose with the reviewed producer prepare_publication and its
qualified-successor dependencies; pin all installed executable blobs and the actual
reviewed source base/head/branch in context. Preserve provider, successor pending
state/review/journal locks and uncertain-effect holds in that API. Qualify the
actual owner/service process separately before adoption; no live task is completed
by this source. The MCP getProfile packet stays a separate, incompatible route.
SSH observes github.com:LOGIN, not a GitHub numeric API id; repository READ and
identity are separate observations, neither proves GitHub write permission.

The normal entrypoint imports prepare_publication and launcher provider_proof
only after source/input validation. Python callers may inject trusted adapters;
JSON cannot select adapters, commands, endpoints or principals. Accepted context
is reviewed executable configuration, not a signature or OS isolation boundary.
Same-UID hostile modification and post-check races require deployment isolation.
The CLI clears its environment before consumption; embedded normal invocations
must already have exactly ENV, so launcher children inherit no service tokens.
No service adoption, credentials, scheduler or execution admission is supplied.

An exact duplicate returns custody without replay, including uncertain outcomes.
Status inspects the exact existing prepare journal read-only. Uncertain/partial
publication remains held for its owner's existing journal reconciliation; this
caller never automatically retries an effect or writes the publication catalog.
"""
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import shlex
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass

BASE = '552a91fe228fc12cbd2fa85e39c61dfda0292213'
ROOT = Path(__file__).resolve().parents[2]
LIMIT = 65536
PROCESS_LIMIT = 262144
ROUTE = dict(service='github-ssh', host='github.com', login='maldous',
             principal_id='github.com:maldous', repository='maldous/offmenu',
             identity='fresh-ssh-success-banner', repository_access='read',
             service_qualification='required-before-adoption')
CALLER = {key: ROUTE[key] for key in ('service', 'principal_id', 'login')}
MODULES = ('stokowski_native_publication', 'stokowski_prepare', 'symphony_launch',
           'stokowski_adapter', 'stokowski_worker', 'stokowski_operations',
           'symphony_capacity', 'symphony_tasks', 'symphony_workspace',
           'symphony_codex', 'symphony_protocol', 'windmill_runner',
           'stokowski_stage', 'stokowski_refill', 'stokowski_mcp', 'windmill_dispatcher')
ENV = {'HOME': '/home/user', 'USER': 'user', 'LOGNAME': 'user',
       'LANG': 'C.UTF-8', 'PATH': '/usr/bin:/bin',
       'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
       'GIT_TERMINAL_PROMPT': '0'}
SSH = ('/usr/bin/ssh', '-F', '/dev/null', '-o', 'BatchMode=yes',
       '-o', 'StrictHostKeyChecking=yes', '-o', 'IdentityAgent=none',
       '-i', '/home/user/.ssh/id_ed25519_maldous', '-o', 'IdentitiesOnly=yes',
       '-o', 'ForwardAgent=no', '-o', 'ForwardX11=no',
       '-o', 'ClearAllForwardings=yes', '-o', 'ProxyCommand=none',
       '-o', 'ProxyJump=none', '-o', 'PermitLocalCommand=no',
       '-o', 'ConnectionAttempts=1', '-o', 'ConnectTimeout=5')


def require(ok, reason='invalid'):
    if not ok:
        raise ValueError('native_publication_' + reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    data = (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    require(len(data) <= LIMIT, 'size')
    return data


def decode(data):
    require(len(data) <= LIMIT, 'size')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate_key')
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=unique,
                      parse_constant=lambda _: require(False, 'number'))


def exact(value, keys):
    require(type(value) is dict and set(value) == set(keys), 'fields')


def canonical(value):
    require(type(value) is str, 'path')
    path = Path(value)
    require(path.is_absolute() and path == path.resolve(), 'path')
    return path


def read(path):
    with path.open('rb') as stream:
        data = stream.read(LIMIT + 1)
    require(len(data) <= LIMIT, 'size')
    return data


def pinned(ref):
    exact(ref, ('path', 'sha256'))
    data = read(canonical(ref['path']))
    require(sha(data) == ref['sha256'], 'pin')
    return decode(data)


def process(argv, *, env, timeout):
    """Bounded pipe capture; raw process output is never logged on refusal."""
    with subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          start_new_session=True) as child:
        streams = selectors.DefaultSelector()
        output = [bytearray(), bytearray()]
        for index, stream in enumerate((child.stdout, child.stderr)):
            os.set_blocking(stream.fileno(), False)
            streams.register(stream, selectors.EVENT_READ, index)
        deadline = time.monotonic() + timeout
        try:
            while streams.get_map():
                require(time.monotonic() < deadline, 'process_timeout')
                for key, _ in streams.select(min(0.1, max(0, deadline - time.monotonic()))):
                    chunk = os.read(key.fd, PROCESS_LIMIT + 1)
                    if not chunk:
                        streams.unregister(key.fileobj)
                    else:
                        output[key.data].extend(chunk)
                        require(sum(map(len, output)) <= PROCESS_LIMIT, 'process_output')
            code = child.wait(timeout=max(0.001, deadline - time.monotonic()))
            return code, bytes(output[0]), bytes(output[1])
        finally:
            streams.close()
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()


@dataclass(frozen=True)
class Adapters:
    """Trusted in-process capabilities, never constructed from request data."""
    run: object
    prepare: object
    provider: object
    now: object = time.time


def git(root, run, *args):
    code, out, err = run(('/usr/bin/git', '-C', str(root), *args),
                         env=dict(ENV), timeout=5)
    require(code == 0 and err == b'' and len(out) <= PROCESS_LIMIT, 'source_git')
    return out


def validate(context, root, run):
    exact(context, ('source_base', 'source_head', 'source_branch', 'source_sha256',
                    'python_sha256', 'handoff', 'owner_config', 'task_packet', 'claim', 'owner'))
    branch = context['source_branch']
    require(context['source_base'] == BASE and type(branch) is str
            and (branch == 'develop' or re.fullmatch(
                r'(?:feature|bugfix)/[a-z0-9][a-z0-9._/-]*', branch))
            and all(part and part[0] != '.' and not part.endswith(('.', '.lock'))
                    for part in branch.split('/'))
            and '..' not in branch, 'source_binding')
    head = context['source_head']
    require(type(head) is str and re.fullmatch('[0-9a-f]{40}', head), 'head')
    require(git(root, run, 'rev-parse', 'HEAD') == (head + '\n').encode()
            and git(root, run, 'branch', '--show-current') == (branch + '\n').encode(), 'source_drift')
    require(git(root, run, 'merge-base', BASE, head) == (BASE + '\n').encode(), 'base')
    require(sha(Path(sys.executable).resolve().read_bytes()) == context['python_sha256'], 'python')
    required = {'tools/delivery/' + name + '.py' for name in MODULES}
    pins = context['source_sha256']
    require(type(pins) is dict and required <= set(pins) and len(pins) <= 64, 'modules')
    for name, expected in pins.items():
        require(re.fullmatch(r'(tools/delivery|src/offmenu/delivery)/[a-z0-9_/-]+\.py', name)
                and '..' not in name.split('/'), 'module_path')
        with canonical(str(root / name)).open('rb') as stream:
            installed = stream.read(PROCESS_LIMIT + 1)
        # Blob size is bounded by the process adapter as well as installed size.
        require(len(installed) <= PROCESS_LIMIT and sha(installed) == expected
                and sha(git(root, run, 'show', head + ':' + name)) == expected, 'source_blob')
    private_root, runtime_root = private_namespace(root,context)
    def private_ref(ref):
        exact(ref, ('path', 'sha256'))
        require(canonical(ref['path']).is_relative_to(private_root), 'private_ref')
        return pinned(ref)
    for key in ('handoff', 'owner_config', 'task_packet', 'claim'):
        private_ref(context[key])
    handoff = pinned(context['handoff'])
    config = pinned(context['owner_config'])
    packet = pinned(context['task_packet'])
    require(config['schema'] == 'offmenu-source-owner-publication-config/1'
            and config['repository'] == ROUTE['repository'] and config['owner'] == context['owner'], 'owner')
    association = config['caller_association']
    exact(association, ('service', 'principal_id', 'login', 'authenticated_observation', 'native_route'))
    require({k: association[k] for k in CALLER} == CALLER
            and association['native_route'] == ROUTE and handoff['native_route'] == ROUTE
            and handoff['authenticated_principal'] == dict(id=CALLER['principal_id'], login=CALLER['login']), 'route')
    require(handoff['owner_config'] == context['owner_config'] == packet['owner_config']
            and handoff['task_packet'] == context['task_packet']
            and packet['owner'] == context['owner']
            and packet['source']['repository'] == ROUTE['repository'], 'references')
    claim = config['repository_claim']
    require(context['claim'] == {k: claim[k] for k in ('path', 'sha256')}, 'claim')
    pinned(context['claim'])
    private_ref(dict(path=claim['binding_path'], sha256=claim['binding_sha256']))
    private_ref(association['authenticated_observation'])  # Mapping only; never authentication.
    covered = [context['owner_config'], context['claim'],
               association['authenticated_observation'],
               dict(path=claim['binding_path'], sha256=claim['binding_sha256'])]
    for key in ('manifest', 'request', 'provider_requirements'):
        private_ref(packet[key])
        covered.append(packet[key])
    installation = packet['installation']
    installation_ref = dict(path=installation['manifest_path'], sha256=installation['manifest_sha256'])
    private_ref(installation_ref)
    covered.append(installation_ref)
    require(all(packet['inputs'].get(ref['path']) == ref['sha256'] for ref in covered), 'input_coverage')
    for name, expected in packet['inputs'].items():
        # The sole mutable input is reconciled by the original publication API.
        require(canonical(name).is_relative_to(private_root)
                or name == str(root / 'tools/delivery/capacity-policy.json'), 'input_path')
        if name != config['selected_current']['catalog_path']:
            require(sha(read(canonical(name))) == expected, 'input_pin')
    require(config['selected_current'] == packet['selected_current']
            and canonical(config['selected_current']['runtime_root']) == runtime_root, 'runtime')
    return config, packet


def private_namespace(root, context):
    if root != Path('/opt/offmenu-stokowski-current/source'):
        return root/'.delivery', root/'.delivery/stokowski'
    # Only installed root custody can map the source's separate runtime.
    from stokowski_adapter import PROTECTED_OWNER, protected_owner_bytes, current_config
    binding = decode(protected_owner_bytes(PROTECTED_OWNER/'binding.json'))
    require(binding['source_root'] == str(root), 'protected_source')
    sealed, _, custody = current_config(canonical(binding['runtime']))
    require(custody is not None and sealed['owner'] == context['owner'], 'protected_owner')
    runtime_root = canonical(sealed['runtime_root'])
    require(runtime_root.name=='stokowski' and runtime_root.parent.name=='.delivery', 'protected_runtime')
    require(packet_runtime_is_sealed(context,runtime_root,binding['runtime']), 'protected_runtime')
    return runtime_root.parent,runtime_root


def packet_runtime_is_sealed(context, runtime_root, coordinator):
    # These refs are hash-bound to the native intent before use. The sealed
    # owner supplies the allowed namespace and exact coordinator identity.
    for ref in (context['owner_config'],context['task_packet']):
        exact(ref,('path','sha256'))
        require(type(ref['sha256']) is str and re.fullmatch('[0-9a-f]{64}',ref['sha256']), 'private_ref')
        if not canonical(ref['path']).is_relative_to(runtime_root.parent):
            return False
        value = pinned(ref)
        selected = value['selected_current']
        if (selected['runtime_root'] != str(runtime_root)
            or selected['coordinator_runtime'] != coordinator):
            return False
    return True


def authenticate(run, now, binding):
    started = now()
    code, out, err = run((*SSH, '-T', 'git@github.com'), env=dict(ENV), timeout=10)
    require(code == 1 and out == b'' and err ==
            b"Hi maldous! You've successfully authenticated, but GitHub does not provide shell access.\n", 'ssh_identity')
    env = dict(ENV, GIT_SSH_COMMAND=shlex.join(SSH))
    code, out, err = run(('/usr/bin/git', 'ls-remote', '--exit-code',
                         'git@github.com:maldous/offmenu.git', 'refs/heads/develop'),
                        env=env, timeout=10)
    # Repository READ proves access to this fixed ref, independently of the
    # immutable reviewed executable source above. Develop may have advanced.
    observed = re.fullmatch(rb'([0-9a-f]{40})\trefs/heads/develop\n', out)
    require(code == 0 and err == b'' and observed is not None, 'repository_read')
    checked = now()
    require(type(started) in (int, float) and type(checked) in (int, float)
            and math.isfinite(started) and math.isfinite(checked)
            and 0 <= checked - started <= 25, 'observation_age')
    return dict(binding=binding, started_at=started, checked_at=checked,
                caller=dict(CALLER), repository_read_head=observed[1].decode('ascii'), write_permission='unproven')


def durable(path, value):
    data = encode(value)
    fd, name = tempfile.mkstemp(prefix='.native-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def invoke(request, *, adapters=None, root=ROOT):
    encode(request)
    exact(request, ('version', 'mode', 'nonce', 'operation', 'context'))
    require(request['version'] == 1 and request['mode'] in ('prepare', 'status'), 'mode')
    require(type(request['nonce']) is str and re.fullmatch('[0-9a-f]{64}', request['nonce']), 'nonce')
    require(request['operation'] == request['context']['handoff']['sha256'], 'operation')
    if adapters is None:
        require(set(os.environ) == set(ENV), 'environment')
        require(all(os.environ[key] == value for key, value in ENV.items()), 'environment')
    run = adapters.run if adapters else process
    config, packet = validate(request['context'], root, run)
    # Imports consume only the now-verified installed normal-entrypoint source.
    if adapters is None:
        from stokowski_prepare import prepare_publication
        from symphony_launch import provider_proof
        adapters = Adapters(process, prepare_publication, provider_proof)
    custody = canonical(str(root / '.delivery/native-ssh-publication'))
    custody.mkdir(mode=0o700, exist_ok=True)
    operation = request['operation']
    require(re.fullmatch('[0-9a-f]{64}', operation), 'operation')
    identity = dict(request)
    identity.pop('mode')
    binding = sha(encode(identity))
    path = custody / (operation + '.json')
    fd = os.open(custody / 'caller.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        prior = decode(read(canonical(str(path)))) if path.exists() else None
        if prior is not None:
            require(prior['binding'] == binding and prior['request'] == identity, 'immutable_conflict')
            result = prior.get('result', dict(status='uncertain', dispatches=0))
            if request['mode'] == 'status':
                runtime = canonical(config['selected_current']['task_runtime'])
                journal = canonical(str(root / '.delivery/stokowski' / (runtime.name + '-publication.json')))
                if journal.exists():
                    data = read(journal)
                    record = decode(data)
                    require(record['identity'] == dict(handoff_sha256=operation,
                        packet=request['context']['task_packet'], config=request['context']['owner_config']), 'journal_identity')
                    return dict(binding=binding, result=result, journal_sha256=sha(data),
                                reconciliation='existing-owner-required', dispatches=0)
            return dict(binding=binding, result=result, dispatches=0)
        require(request['mode'] == 'prepare', 'missing_intent')
        observation = authenticate(run, adapters.now, binding)
        prior = dict(binding=binding, request=identity, observation=observation, status='intent')
        durable(path, prior)  # Persist before calling the only publisher.
        consumed = False
        def caller():
            nonlocal consumed
            require(not consumed and 0 <= adapters.now() - observation['checked_at'] <= 30, 'callback_freshness')
            consumed = True
            return dict(CALLER)
        try:
            ref = request['context']['handoff']
            result = adapters.prepare(ref['path'], handoff_sha256=ref['sha256'],
                                      authenticated_caller=caller, provider_proof=adapters.provider)
            require(consumed and result.get('dispatches') == 0
                    and result.get('status') in ('published', 'duplicate'), 'prepare_result')
        except Exception:
            # Even an admission error can follow a partial durable effect.
            result = dict(status='uncertain', dispatches=0)
        prior.update(status=result['status'], result=result)
        durable(path, prior)
        return dict(binding=binding, result=result, dispatches=0)
    finally:
        os.close(fd)


def main():
    require(len(sys.argv) == 1, 'arguments')
    # Destructive sanitization is confined to this finite CLI process. No values
    # from inherited credential/service variables are inspected or copied.
    os.environ.clear()
    os.environ.update(ENV)
    result = invoke(decode(sys.stdin.buffer.read(LIMIT + 1)))
    sys.stdout.buffer.write(encode(result))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        sys.stderr.write('native_publication_refused_or_uncertain\n')
        sys.exit(1)
