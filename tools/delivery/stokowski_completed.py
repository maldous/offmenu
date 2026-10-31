"""Read-only consumption of an owner-pinned, already-completed native unit.

An Engine receipt remains an Engine receipt, never a fabricated Journal row.
The authenticated integration owner selects this evidence through current.json;
JSON/UID custody alone does not authenticate that owner or isolate hostile UID
peers. No subprocess except fixed local Git observations, no writes or dispatch.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess

from symphony_capacity import AdmissionError, digest

KIND = 'completed-native-validation-v1'
LIMIT = 1024 * 1024


def require(value):
    if not value:
        raise AdmissionError('completed_native_evidence_binding')


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pinned(ref, root):
    require(type(ref) is dict and set(ref) == {'path', 'sha256'})
    p = Path(ref['path'])
    require(p.is_absolute() and p == p.resolve() and p.is_relative_to(root)
            and not any(x.is_symlink() for x in (p, *p.parents)))
    st = p.stat()
    require(p.is_file() and st.st_uid == os.getuid() and not st.st_mode & 0o077
            and st.st_size <= LIMIT and file_sha(p) == ref['sha256'])
    def unique(pairs):
        out = {}
        for k, v in pairs:
            require(k not in out)
            out[k] = v
        return out
    return json.loads(p.read_bytes(), object_pairs_hook=unique,
                      parse_constant=lambda _: require(False))


def checkpoint(ref, root, binding):
    p = Path(ref['path'])
    require(p.is_absolute() and p == p.resolve() and p.is_relative_to(root)
            and not any(x.is_symlink() for x in (p,*p.parents)))
    st=p.stat()
    require(p.is_file() and st.st_uid == os.getuid() and not st.st_mode & 0o077
            and st.st_size <= LIMIT and file_sha(p) == ref['sha256'])
    from stokowski_unit_review import checkpoint_json
    with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
        row=db.execute("SELECT type,checkpoint FROM checkpoints WHERE thread_id=? AND checkpoint_ns='' ORDER BY checkpoint_id DESC LIMIT 1",(digest(binding),)).fetchone()
    require(row is not None and row[0]=='msgpack' and len(row[1])<=LIMIT)
    return checkpoint_json(row[1])['channel_values']


def qualify(current, issue):
    """Return one truthful terminal packet; retain the native gate identity."""
    current.guard()
    require(current.config['source_sha256'].get('tools/delivery/stokowski_completed.py') == file_sha(__file__))
    pin = current.config.get('completed_native_validations', {}).get(issue)
    require(pin is not None)
    root = current.root.parent
    evidence = pinned(pin, root)
    require(type(evidence.get('version')) is int and evidence.get('version') == 1 and evidence.get('kind') == KIND
            and evidence.get('issue') == issue)
    entry = current.entries[issue]
    runtime, manifest, source = current.context(issue, review=True, observation=True)
    require('stage' not in manifest['tasks'][issue])
    task = manifest['tasks'][issue]
    from types import SimpleNamespace
    unit = current.gate_binding(SimpleNamespace(identifier=issue, id=entry['issue_id']))
    require(unit == evidence['unit_binding'])
    native_path = runtime/'attempts'/issue/'receipt.json'
    require(file_sha(native_path) == unit['native_receipt_sha256'])
    native = json.loads(native_path.read_bytes())
    require(native['status'] == 'succeeded' and native['child_tree_gone'] is True
            and native.get('exit_code') == 0 and native.get('turn_completed') is True
            and native['scope_violations'] == [] and native['source_identity_changed'] is False
            and native['final_head'] == native['source_head'] == manifest['base_revision']
            and native['final_branch'] == manifest['branch']
            and native['accepted_delivery'] is False)
    policy = json.loads((runtime/'capacity-policy.json').read_bytes())
    database = Path(policy['symphony']['pool_path'])/'state.sqlite'
    with sqlite3.connect(database.as_uri()+'?mode=ro', uri=True) as db:
        row = db.execute('SELECT status,binding,outcome FROM leases WHERE id=?', (native['lease'],)).fetchone()
    require(row is not None and row[0] == 'finished' and row[2] == 'succeeded'
            and digest(json.loads(row[1])) == native['binding_sha256'])
    b = pinned(evidence['integration_binding'], root)
    snapshot = pinned(evidence['controller_observation'], root)
    controller = pinned(evidence['controller_state'], root)
    review = pinned(evidence['independent_review'], root)
    claim = pinned(evidence['controller_claim'], root)
    directory = Path(claim['directory'])
    require(claim == dict(owner=b['owner'],directory=str(directory),binding_sha256=digest(b))
            and directory.is_relative_to(root/'integration') and directory == directory.resolve())
    channels=checkpoint(evidence['controller_checkpoint'],root,b)
    require(channels['result']==controller and channels['observation']==snapshot)

    require(b['owner'] == current.config['owner'] == task['owner']
            and b['issue_id'] == entry['issue_id'] and b['repository'] == 'maldous/offmenu'
            and b['outputs'] == native['output_sha256'] == review['reviewed_outputs']
            and set(b['outputs']) == set(task['allowed_paths'])
            and review['verdict'] == 'accepted' and review['findings'] == []
            and review['integration_head'] == b['head']
            and review['integration_base'] == b['base']
            and review['integration_tree'] == b['tree']
            and review['native_receipt_sha256'] == unit['native_receipt_sha256'])
    reviewer = review['reviewer']
    require(reviewer['identity'] and reviewer['identity'] != task['owner']
            and reviewer['role'] == 'independent source reviewer; not coding author or integration writer')
    # Keep explicitly unavailable reviewer metadata intact; never infer it from coding.
    require(all(k in reviewer for k in ('requested_model','requested_effort','requested_provider',
                                      'observed_model','observed_provider','resolution_status')))
    require(reviewer['resolution_status'] in ('unobserved','unknown','observed'))
    if reviewer['resolution_status'] != 'observed':
        require(reviewer['observed_model'] is None and reviewer['observed_provider'] is None)
    # The source checkout shares committed objects with the authenticated publisher.
    # An explicit repository pin allows a separate integration checkout; no file
    # mapping, hidden rebase or substitution of the admitted native branch/base.
    repository = Path(evidence['repository'])
    require(repository == root.parent and repository.is_absolute() and repository == repository.resolve()
            and not any(p.is_symlink() for p in (repository, *repository.parents)))
    def blob(*args):
        try:
            return subprocess.check_output(['git','-C',str(repository),*args],stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            require(False)
    require(blob('merge-base',manifest['base_revision'],b['base']).decode().strip() == manifest['base_revision'])
    require(not blob('diff','--name-only',manifest['base_revision'],b['base'],'--',*b['outputs']).strip())
    require(blob('rev-parse',b['head']+'^{tree}').decode().strip() == b['tree'])
    require(set(blob('diff','--name-only',b['base'],b['head']).decode().splitlines()) == set(b['outputs']))
    for name, expected in b['outputs'].items():
        require(hashlib.sha256(blob('show',b['head']+':'+name)).hexdigest() == expected
                and (runtime/'workspaces'/issue/name).resolve() == runtime/'workspaces'/issue/name
                and file_sha(runtime/'workspaces'/issue/name) == expected)
    merge = snapshot['merge_commit']
    require(controller['status'] in ('merge-verified','accepted')
            and controller['merge_effect'] == 'verified' and controller['action'] is None
            and controller['binding_sha256'] == digest(b)
            and controller['merge_commit_sha'] == merge['sha']
            and controller['qualification_sha256'] == digest(dict(validation=snapshot['validation'],
                review=snapshot['review'],tree=b['tree'],policy=b['policy_sha256']))
            and snapshot['publisher_owner'] == b['owner']
            and snapshot['policy_sha256'] == b['policy_sha256']
            and snapshot['capacity_policy_sha256'] == b['capacity_policy_sha256']
            and not snapshot.get('cancel_requested')
            and snapshot['develop_contains_merge'] is True
            and snapshot['github']['merged'] is True
            and snapshot['github']['merge_commit_sha'] == merge['sha']
            and snapshot['github']['head'] == b['head'] and snapshot['github']['base'] == b['base']
            and snapshot['github']['repository'] == b['repository']
            and snapshot['github']['number'] == b['pr_number']
            and snapshot['source_tree'] == b['tree'] and snapshot['source_clean'] is True
            and snapshot['publication_triggers_actions'] is False
            and snapshot['unresolved_findings'] == []
            and merge['parents'] == [b['base'],b['head']] and merge['tree'] == b['tree'])
    blob('merge-base','--is-ancestor',merge['sha'],current.config['source_head'])
    require(blob('show','-s','--format=%P',merge['sha']).decode().strip().split() == merge['parents']
            and blob('rev-parse',merge['sha']+'^{tree}').decode().strip() == b['tree'])
    validation = pinned(evidence['validation_receipt'], root)
    result = pinned(evidence['validation_result'], root)
    request = pinned(evidence['validation_request'], root)
    engine = pinned(evidence['engine_task'], root)
    require(result.get('isError') is False and len(result['content']) == 1
            and result['content'][0]['type'] == 'text')
    text = result['content'][0]['text']
    returned, _ = json.JSONDecoder().raw_decode(text[text.index('{'):])
    require(returned['receipt'] == validation and returned['admitted'] is True
            and returned['job_succeeded'] is True and returned['job_id'] == request['job_id'])
    match = re.search(r'\njob=([0-9a-f-]{36}) ', text)
    require(match is not None and match.group(1) == evidence['windmill_job_id'])
    command = hashlib.sha256(request['command'].encode()).hexdigest()
    require(validation['status'] == 'succeeded' and validation['exit_code'] == 0
            and validation['child_tree_gone'] is True and validation['reconcile_required'] is False
            and validation['job_id'] == request['job_id']
            and validation['command_sha256'] == command == b['validation_operation_key']
            and validation['runner_sha256'] == current.config['source_sha256']['tools/delivery/windmill_runner.py']
            and validation['capacity_policy_sha256'] == current.config['policy_sha256'] == b['capacity_policy_sha256'])
    expected = dict(command_sha256=command, mode=request['mode'],timeout_seconds=request['timeout_seconds'],
        runner_sha256=validation['runner_sha256'],capacity_policy_sha256=validation['capacity_policy_sha256'],resources=request['resources'])
    require(validation['request_sha256'] == hashlib.sha256(json.dumps(expected,sort_keys=True).encode()).hexdigest())
    require(engine['base_revision'] == b['head'] and engine['branch'] == b['head_branch']
            and engine['accepted_outputs'] == b['outputs']
            and len(engine['checks']) >= 2 and snapshot['validation'] == dict(operation_key=command,
                status='succeeded',head=b['head'],base=b['base'],capacity_policy_sha256=b['capacity_policy_sha256'],
                outputs=b['outputs'],child_tree_gone=True,reconcile_required=False))
    require(snapshot['review']['reviewer'] == reviewer['identity']
            and snapshot['review']['author'] == 'native Codex session '+native['session_id']
            and snapshot['review']['independent'] is True and snapshot['review']['verdict'] == 'accept'
            and snapshot['review']['findings'] == []
            and snapshot['review']['evidence_id'] == 'sha256:'+evidence['independent_review']['sha256'])
    decision = dict(version=1,kind=KIND,status='completed-native-qualified',action=None,
        merge_effect='verified',binding_sha256=digest(b),qualification_sha256=controller['qualification_sha256'],
        merge_commit_sha=merge['sha'],completed_evidence_sha256=pin['sha256'])
    return dict(issue=issue,unit_binding=unit,integration_binding=b,snapshot=snapshot,
                decision=decision,validation_receipt=validation)
