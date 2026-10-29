"""Bind Stokowski output to one reviewed candidate and tick durable validation.

No model calls, source publication or merge authority. This stage consumes
already-admitted coding output and hands deterministic checks to Windmill.
"""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import subprocess
import time

from stokowski_adapter import SOURCE
from stokowski_operations import Journal, OperationError, TERMINAL, operation_key, validated, digest
from stokowski_mcp import WindmillMCP
from symphony_tasks import load_manifest
from symphony_workspace import checkpoint


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()


def bind(runtime,spec,derivation_reason=None):
    runtime = runtime.resolve()
    manifest = load_manifest(runtime/'manifest.json')
    validated(spec)
    issue = spec['issue']
    if issue not in manifest['tasks'] or spec['issue_id'] != manifest['tasks'][issue]['issue_id']:
        raise OperationError('Issue is not admitted to the selected Stokowski runtime')
    receipt_path = runtime/'attempts'/issue/'receipt.json'
    receipt = json.loads(receipt_path.read_text())
    workspace = runtime/'workspaces'/issue
    if (receipt.get('status') != 'succeeded' or receipt.get('child_tree_gone') is not True
        or receipt.get('scope_violations') or receipt.get('source_head') != manifest['base_revision']
        or git(workspace,'rev-parse','HEAD') != manifest['base_revision']
        or git(workspace,'branch','--show-current') != manifest['branch']):
        raise OperationError('Coding output is not reconciled against its admitted source')
    original = receipt.get('output_sha256',{})
    if not original or not set(original).issubset(spec['outputs']):
        raise OperationError('Candidate must account for every coding output')
    expected_acceptance = digest({'task':manifest['tasks'][issue],
                                  'native_receipt_sha256':file_hash(receipt_path),
                                  'profile':spec['profile']})
    if spec['acceptance_sha256'] != expected_acceptance:
        raise OperationError('Acceptance is not bound to the admitted task/output receipt')
    for name,sha in original.items():
        if file_hash(workspace/name) != sha:
            raise OperationError('Coding output changed after its receipt')
    head = git(SOURCE,'rev-parse','HEAD')
    if head != spec['head'] or git(SOURCE,'branch','--show-current') != manifest['branch']:
        raise OperationError('Candidate branch/head differs from selected publication')
    subprocess.run(['git','-C',str(SOURCE),'merge-base','--is-ancestor',
                    manifest['base_revision'],head],check=True,capture_output=True)
    if git(SOURCE,'status','--porcelain','--untracked-files=no'):
        raise OperationError('Candidate tracked source is dirty')
    accepted_policy = json.loads(git(SOURCE,'show',spec['base']+':repository-standard.json'))
    untracked = set(filter(None,git(SOURCE,'ls-files','--others','--exclude-standard','-z').split('\0')))
    if untracked-set(accepted_policy.get('runtime_hold_paths',[])):
        raise OperationError('Uncommitted maintained source needs publication before validation')
    for name,sha in spec['outputs'].items():
        if file_hash(SOURCE/name) != sha:
            raise OperationError('Candidate output hash mismatch')
    differences = {name:{'native':sha,'candidate':spec['outputs'][name]}
                   for name,sha in original.items() if sha != spec['outputs'][name]}
    if differences and (not isinstance(derivation_reason,str) or not derivation_reason.strip()):
        raise OperationError('Changed coding output needs an explicit reviewed derivation')
    journal = Journal(runtime/'operations')
    key = operation_key(spec)
    path = runtime/'validation-bindings.json'
    bindings = json.loads(path.read_text()) if path.exists() else {'version':1,'issues':{},'history':[]}
    previous = bindings['issues'].get(issue)
    if previous and previous['operation_key'] != key:
        _,state = journal.read(previous['operation_key'])
        if state['status'] not in ('succeeded','failed','cancelled'):
            raise OperationError('Previous operation must reconcile before a new candidate')
    key = journal.prepare(spec)
    selected = {'operation_key':key,'source_head':head,'native_receipt_sha256':file_hash(receipt_path),
                'native_output_sha256':original,'derivation':differences,
                'derivation_reason':derivation_reason if differences else None}
    if previous == selected:
        return key
    if previous:
        bindings['history'].append({'issue':issue,**previous})
    bindings['issues'][issue] = selected
    checkpoint(path,bindings)
    return key


async def tick(runtime,transport=None):
    bindings = json.loads((runtime/'validation-bindings.json').read_text())
    journal = Journal(runtime/'operations')
    transport = transport or WindmillMCP()
    try:
        keys = [(issue,value['operation_key']) for issue,value in bindings['issues'].items()]
        results = await asyncio.gather(*(journal.tick(key,transport) for _,key in keys))
        projection = {'version':1,
            'dispatcher_mode':'explicit-draft-test' if getattr(transport,'preview',False) else 'deployed',
            'issues':{issue:{'operation_key':key,**state,
            'stage':'validation-verified' if state['status']=='succeeded' else
                    ('repair-required' if state['status']=='failed' else 'validation-pending'),
            'merge_accepted':False} for (issue,key),state in zip(keys,results)}}
        checkpoint(runtime/'validation-stage.json',projection)
        return projection
    finally:
        await transport.close()


async def continue_stage(runtime,duration,preview=False):
    deadline = time.monotonic()+duration
    while True:
        result = await tick(runtime,WindmillMCP(preview=preview))
        result['dispatcher_mode'] = 'explicit-draft-test' if preview else 'deployed'
        if all(row['status'] in TERMINAL for row in result['issues'].values()):
            return result
        if time.monotonic() >= deadline:
            return result
        await asyncio.sleep(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['bind','tick','run','cancel','status'])
    parser.add_argument('--runtime',required=True,type=Path)
    parser.add_argument('--spec',type=Path)
    parser.add_argument('--derivation-reason')
    parser.add_argument('--issue')
    parser.add_argument('--duration',type=int,default=120)
    parser.add_argument('--preview-dispatch',action='store_true',help='Explicit draft testing; never a deployment fallback')
    args = parser.parse_args()
    runtime = args.runtime.resolve()
    if not runtime.is_relative_to(SOURCE/'.delivery/stokowski'):
        raise OperationError('Use the existing private OffMenu runtime')
    if args.action == 'bind':
        print(json.dumps({'operation_key':bind(runtime,json.loads(args.spec.read_text()),args.derivation_reason)}))
    elif args.action in ('tick','run'):
        if not 1 <= args.duration <= 600:
            raise OperationError('Invalid finite stage duration')
        result = asyncio.run(tick(runtime,WindmillMCP(preview=args.preview_dispatch))
                    if args.action=='tick' else continue_stage(runtime,args.duration,args.preview_dispatch))
        print(json.dumps(result))
    else:
        bindings = json.loads((runtime/'validation-bindings.json').read_text())
        journal = Journal(runtime/'operations')
        if args.action == 'cancel':
            journal.cancel(bindings['issues'][args.issue]['operation_key'])
        print(json.dumps({issue:journal.read(value['operation_key'])[1]
                          for issue,value in bindings['issues'].items()}))


if __name__ == '__main__':
    main()
