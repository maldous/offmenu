"""Bind Stokowski output to one reviewed candidate and tick durable validation.

No model calls, source publication or merge authority. This stage consumes
already-admitted coding output and hands deterministic checks to Windmill.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from stokowski_adapter import SOURCE
from stokowski_operations import Journal, OperationError, TERMINAL, operation_key, validated, digest, candidate_check_code, workspace_path
from stokowski_mcp import WindmillMCP
from symphony_tasks import load_manifest
from symphony_workspace import checkpoint


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()


def bind(runtime,spec,derivation_reason=None):
    runtime = runtime.resolve()
    manifest = load_manifest(runtime/'manifest.json',expected_branch=None)
    validated(spec)
    if spec['version'] != 1:
        raise OperationError('Reviewed extraction requires bind_extraction')
    if spec.get('branch','feature/langgraph-delivery-standardization') != manifest['branch']:
        raise OperationError('Validation branch differs from admitted coding branch')
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


def bind_extraction(runtime, spec, admission_path, candidate_root=None):
    """Consume an owner-provisioned immutable admission; never create coding proof.

    admission_path is a trusted owner input, not a candidate-controlled report.
    Its exact bytes are pinned by acceptance_sha256. Review hashes use digest().
    """
    validated(spec)
    if spec['version'] != 2:
        raise OperationError('Extraction binding requires v2')
    runtime = Path(runtime).resolve()
    if admission_path is None:
        raise OperationError('Missing trusted extraction admission')
    path = Path(admission_path)
    if any(p.is_symlink() for p in (path,*path.parents)) or not path.is_file():
        raise OperationError('Admission must be a regular trusted owner file')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != spec['origin']['admission_sha256']:
        raise OperationError('Extraction admission hash mismatch')
    def unique(pairs):
        result = {}
        for key,value in pairs:
            if key in result:
                raise OperationError('Duplicate admission field')
            result[key] = value
        return result
    admission = json.loads(raw, object_pairs_hook=unique)
    fields = {'version','issue','issue_id','owner','head','base','branch','workspace',
              'source_commit','mapping','outputs','author','review'}
    if not isinstance(admission,dict) or set(admission) != fields or type(admission['version']) is not int or admission['version'] != 1:
        raise OperationError('Invalid extraction admission')
    for name in ('issue','issue_id','owner','head','base','branch','workspace','outputs'):
        if admission[name] != spec[name]:
            raise OperationError('Extraction admission differs: '+name)
    for name in ('source_commit','mapping','author'):
        if admission[name] != spec['origin'][name]:
            raise OperationError('Extraction origin differs: '+name)
    review = admission['review']
    if (not isinstance(review,dict) or set(review) != {'record','reviewer','decision','head','base'} or
        not isinstance(review['record'],str) or not review['record'].strip() or
        not isinstance(review['reviewer'],str) or not review['reviewer'].strip() or
        review['reviewer'] == admission['author'] or review['decision'] != 'accepted' or
        review['head'] != spec['head'] or review['base'] != spec['base'] or
        digest(review) != spec['origin']['review_sha256']):
        raise OperationError('Missing, stale or rejected independent review')
    remote_root = workspace_path(spec['workspace'])
    root = Path(candidate_root) if candidate_root is not None else remote_root
    if (not root.is_absolute() or str(root) != str(candidate_root if candidate_root is not None else remote_root) or
        root.resolve() != root or any(p.is_symlink() for p in (root,*root.parents)) or
        not root.is_dir()):
        raise OperationError('Local source root must be an absolute canonical non-symlink directory')
    if any(path.resolve().is_relative_to(candidate) for candidate in (root,remote_root)):
        raise OperationError('Admission must be provided outside local and remote candidate source')
    try:
        subprocess.run([sys.executable,'-c',candidate_check_code(spec,root)],check=True,
                       env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True)
    except subprocess.CalledProcessError as error:
        raise OperationError('Exact candidate identity/mapping/output check failed') from error
    journal = Journal(runtime/'operations')
    key = operation_key(spec)
    path = runtime/'validation-bindings.json'
    bindings = json.loads(path.read_text()) if path.exists() else {'version':1,'issues':{},'history':[]}
    previous = bindings['issues'].get(spec['issue'])
    if previous and previous['operation_key'] != key:
        _,state = journal.read(previous['operation_key'])
        if state['status'] not in ('succeeded','failed','cancelled'):
            raise OperationError('Previous operation must reconcile before a new candidate')
    key = journal.prepare(spec)
    selected = {'operation_key':key,'source_head':spec['head'],
                'origin':'reviewed-extraction','admission_sha256':spec['origin']['admission_sha256'],
                'review_sha256':spec['origin']['review_sha256'],'workspace':str(remote_root),
                'local_source_root':str(root),
                'execution':spec['execution'],'merge_accepted':False}
    if previous != selected:
        if previous:
            bindings['history'].append({'issue':spec['issue'],**previous})
        bindings['issues'][spec['issue']] = selected
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
            'origin':bindings['issues'][issue].get('origin','native-coding'),
            'execution':bindings['issues'][issue].get('execution'),
            'stage':'validation-verified' if state['status']=='succeeded' else
                    ('repair-required' if state['status']=='failed' else 'validation-pending'),
            'merge_accepted':False} for (issue,key),state in zip(keys,results)}}
        from stokowski_refill import observe_refill
        boundary = digest({issue:{k:row.get(k) for k in ('operation_key','status','stage')}
                           for issue,row in projection['issues'].items()})
        prior_path = runtime/'validation-stage.json'
        prior = json.loads(prior_path.read_text()) if prior_path.exists() else {}
        projection['refill_boundary'] = boundary
        projection['refill'] = (prior['refill'] if prior.get('refill_boundary') == boundary
                                and 'refill' in prior else observe_refill(runtime, projection['issues']))
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
    parser.add_argument('action',choices=['bind','bind-extraction','tick','run','cancel','status'])
    parser.add_argument('--runtime',required=True,type=Path)
    parser.add_argument('--spec',type=Path)
    parser.add_argument('--derivation-reason')
    parser.add_argument('--admission',type=Path)
    parser.add_argument('--candidate-root',type=Path)
    parser.add_argument('--issue')
    parser.add_argument('--duration',type=int,default=120)
    parser.add_argument('--preview-dispatch',action='store_true',help='Explicit draft testing; never a deployment fallback')
    args = parser.parse_args()
    runtime = args.runtime.resolve()
    if not runtime.is_relative_to(SOURCE/'.delivery/stokowski'):
        raise OperationError('Use the existing private OffMenu runtime')
    if args.action == 'bind-extraction':
        print(json.dumps({'operation_key':bind_extraction(runtime,json.loads(args.spec.read_text()),args.admission,args.candidate_root)}))
    elif args.action == 'bind':
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
