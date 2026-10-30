"""Fixed trusted-owner stdin consumer; local bytes alone do not authenticate.

Only the authenticated gateway may supply this envelope. Same-UID malicious
actors are outside this logical boundary. Uncertain intents are held for owner
reconciliation against prepare_publication's journal, never automatically replayed.
"""
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from stokowski_prepare import prepare_publication, _publication_write, _publication_bytes
from symphony_launch import provider_proof
from symphony_capacity import AdmissionError, digest

LIMIT = 65536
ROOT = Path(__file__).resolve().parents[2]
REQUIRED = ('stokowski_publication', 'stokowski_prepare', 'symphony_launch',
            'stokowski_adapter', 'stokowski_worker', 'stokowski_operations',
            'symphony_capacity', 'symphony_tasks', 'symphony_workspace',
            'symphony_codex', 'symphony_protocol', 'windmill_runner')


def require(condition):
    if not condition:
        raise ValueError('publication_bridge_refused')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def decode(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result)
            result[key] = value
        return result
    require(len(data) <= LIMIT)
    return json.loads(data, object_pairs_hook=unique,
                      parse_constant=lambda _: require(False))


def canonical(value):
    path = Path(value)
    require(path.is_absolute() and path == path.resolve())
    return path


def pinned(ref):
    require(set(ref) == {'path', 'sha256'})
    data = canonical(ref['path']).read_bytes()
    require(sha(data) == ref['sha256'])
    return decode(data)


def validate(context):
    require(set(context) == {'source_head', 'source_branch', 'source_sha256',
                             'python_sha256', 'handoff', 'owner_config'})
    require(sha(Path(sys.executable).resolve().read_bytes()) == context['python_sha256'])
    require(re.fullmatch('[0-9a-f]{40}', context['source_head']) is not None)
    def git(*args):
        return subprocess.check_output(['/usr/bin/git', '-C', str(ROOT), *args],
                                       timeout=2, env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
    require(git('rev-parse', 'HEAD').decode().strip() == context['source_head'])
    require(git('branch', '--show-current').decode().strip() == context['source_branch'])
    required = {'tools/delivery/' + name + '.py' for name in REQUIRED}
    required.add('tools/delivery/integration-gateway.mjs')
    require(required <= set(context['source_sha256']))
    for name, expected in context['source_sha256'].items():
        require(re.fullmatch(r'(tools/delivery|src/offmenu/delivery)/[a-z0-9_./-]+', name)
                and all(p not in ('.', '..') for p in name.split('/')))
        path = canonical(str(ROOT / name))
        require(sha(path.read_bytes()) == expected
                and sha(git('show', context['source_head'] + ':' + name)) == expected)
    handoff = pinned(context['handoff'])
    config = pinned(context['owner_config'])
    require(handoff['owner_config'] == context['owner_config'])
    packet = pinned(handoff['task_packet'])
    # ROOT/context pin the installed executables, independently of task source.
    # The pinned packet binds task checkout/head/branch; prepare_publication
    # validates that exact source and manifest before any publication effects.
    require(packet['owner_config'] == context['owner_config'])
    require(config['schema'] == 'offmenu-source-owner-publication-config/1'
            and config['selected_current'] == packet['selected_current'])
    root = canonical(config['selected_current']['runtime_root'])
    require(root == ROOT / '.delivery/stokowski' and root.is_dir())
    claim_ref = config['repository_claim']
    claim = pinned({k: claim_ref[k] for k in ('path', 'sha256')})
    binding = pinned(dict(path=claim_ref['binding_path'], sha256=claim_ref['binding_sha256']))
    require(claim == dict(owner=config['owner'], directory=str(Path(claim_ref['binding_path']).parent),
                          binding_sha256=claim_ref['binding_identity_sha256'])
            and digest(binding) == claim_ref['binding_identity_sha256']
            and binding['owner'] == config['owner'] and binding['repository'] == config['repository']
            and binding['issue_id'] == packet['execution_outcome']['uuid'])
    return config, root


def consume(wire):
    require(set(wire) == {'version', 'mode', 'payload', 'request_sha256'})
    require(wire['version'] == 1 and wire['mode'] in ('prepare', 'status'))
    payload = wire['payload']
    require(isinstance(payload, str) and sha(payload.encode()) == wire['request_sha256'])
    envelope = decode(payload)
    require(set(envelope) == {'context', 'nonce', 'observed_at', 'provenance', 'principal'})
    require(re.fullmatch('[0-9a-f]{64}', envelope['nonce']) is not None)
    require(envelope['provenance'] == {'service': 'github',
            'connector_tool': 'mcp__codex_apps__github_get_profile',
            'flow': 'same-invocation-getProfile-to-fixed-stdin'})
    config, root = validate(envelope['context'])
    expected = {k: config['caller_association'][k] for k in ('service', 'principal_id', 'login')}
    observed = dict(envelope['principal'])
    require(observed == expected)
    # Configuration maps identity, but does not authenticate the stdin sender.
    operation = envelope['context']['handoff']['sha256']
    require(re.fullmatch('[0-9a-f]{64}', operation) is not None)
    journal = canonical(str(root / ('owner-bridge-' + operation + '.json')))
    fd = os.open(root / 'owner-bridge.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        prior = decode(journal.read_bytes()) if journal.exists() else None
        if wire['mode'] == 'status':
            require(prior is not None and prior['request_sha256'] == wire['request_sha256']
                    and prior['nonce'] == envelope['nonce'])
            result = prior.get('result', {'status': 'uncertain', 'dispatches': 0})
        else:
            checked = envelope['observed_at']
            require(type(checked) in (int, float) and math.isfinite(checked)
                    and -2 <= time.time() - checked <= 30)
            require(prior is None)  # New nonce does not bypass immutable handoff ownership.
            prior = dict(version=1, nonce=envelope['nonce'], request_sha256=wire['request_sha256'],
                         context=envelope['context'], status='intent')
            require(len(_publication_bytes(prior)) <= LIMIT)
            _publication_write(journal, _publication_bytes(prior))
            try:
                ref = envelope['context']['handoff']
                result = prepare_publication(ref['path'], handoff_sha256=ref['sha256'],
                    authenticated_caller=lambda: dict(observed), provider_proof=provider_proof)
                require(result.get('dispatches') == 0)
            except AdmissionError:
                result = dict(status='refused', dispatches=0)
            except Exception:
                result = dict(status='uncertain', dispatches=0)
            prior.update(status=result['status'], result=result)
            require(len(_publication_bytes(prior)) <= LIMIT)
            _publication_write(journal, _publication_bytes(prior))
        response = json.dumps(dict(nonce=envelope['nonce'], request_sha256=wire['request_sha256'],
                                   result=result), separators=(',', ':'), allow_nan=False)
        require(len(response.encode()) <= LIMIT)
        return dict(version=1, response=response, response_sha256=sha(response.encode()))
    finally:
        os.close(fd)


def main():
    require(len(sys.argv) == 1)  # No path, command, callable or principal CLI knobs.
    data = sys.stdin.buffer.read(LIMIT + 1)
    reply = consume(decode(data))
    sys.stdout.write(json.dumps(reply, separators=(',', ':')) + '\n')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        sys.stderr.write('publication_bridge_refused_or_uncertain\n')
        sys.exit(1)
