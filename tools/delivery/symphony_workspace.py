"""Reviewed multi-task native workspace hooks with durable resource admission."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
try:
    from .symphony_capacity import AdmissionError, BRANCH, Pool, host_snapshot, overlap
    from .symphony_tasks import load_manifest, task_for_workspace, manifest_digest, runtime_lease_ids
except ImportError:
    from symphony_capacity import AdmissionError, BRANCH, Pool, host_snapshot, overlap
    from symphony_tasks import load_manifest, task_for_workspace, manifest_digest, runtime_lease_ids

ISSUE='UIF-90'  # Compatibility hook only; manifest mode has no fixed issue limit.


def git(*args):return subprocess.check_output(['git',*args],text=True).strip()


def checkpoint(path,value):
    temporary=path.with_suffix('.pending')
    with temporary.open('w') as f:
        os.fchmod(f.fileno(),0o600);json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    temporary.replace(path)


def workspace_processes(workspace):
    """Same-owner process paths only, no command/environment inspection."""
    found=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit() or int(p.name) in (os.getpid(),os.getppid()):continue
        try:
            if p.stat().st_uid!=os.getuid():continue
            cwd=(p/'cwd').resolve()
            if cwd==workspace or workspace in cwd.parents:found.append(int(p.name))
        except (FileNotFoundError,PermissionError,ProcessLookupError):continue
    return found


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['create','admit','finish'])
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--head',required=True)
    parser.add_argument('--attempt-limit',type=int,default=2)
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--runtime',type=Path)
    args=parser.parse_args();workspace=Path.cwd().resolve()
    if not args.manifest:
        if workspace.name!=ISSUE:raise SystemExit('Only UIF-90 is admitted by legacy hooks')
        task={'allowed_paths':['tests/delivery/test_cli.py','src/offmenu/delivery/__main__.py'],'attempt_limit':args.attempt_limit}
        manifest=None
    else:
        if not args.runtime or workspace.parent!=args.runtime.resolve()/'workspaces':raise SystemExit('Workspace outside admitted runtime')
        manifest=load_manifest(args.manifest,expected_head=args.head)
        task=task_for_workspace(manifest,workspace.name)
    runtime=args.runtime.resolve() if args.runtime else workspace.parent.parent
    if args.action=='create':
        if any(workspace.iterdir()):raise SystemExit('Refusing to overwrite a non-empty workspace')
        subprocess.run(['git','clone','--shared','--single-branch','--branch',BRANCH,str(args.source),'.'],check=True)
    if git('branch','--show-current')!=BRANCH or git('rev-parse','HEAD')!=args.head:raise SystemExit('Source branch/head mismatch; reconcile before retry')
    marker=workspace.parent/(workspace.name.lower()+'-attempts.json')
    finished=workspace.parent/(workspace.name.lower()+'-run-finished.json')
    if args.action=='finish':
        changed=[x for x in git('diff','--name-only','HEAD','-z').split('\0') if x]
        changed += [x for x in git('ls-files','--others','--exclude-standard','-z').split('\0') if x]
        outside=[p for p in changed if not any(p==a or p.startswith(a+'/') for a in task['allowed_paths'])]
        processes=workspace_processes(workspace)
        result={'issue':workspace.name,'source_head':args.head,'attempt_ended':True,'accepted_delivery':False,'scope_violations':outside,'process_tree_gone':not processes}
        if manifest:
            pool=Pool(json.loads((runtime/'capacity-policy.json').read_text())['symphony']['pool_path'],json.loads((runtime/'capacity-policy.json').read_text()))
            lease=runtime_lease_ids(runtime,manifest)[workspace.name]
            if json.loads(marker.read_text())['lease_id'] != lease:raise AdmissionError('Runtime lease identity mismatch; reconcile')
            if not processes:pool.finish(lease,True,'failed' if outside else 'stopped')
            else:result['reconcile_required']=True
        checkpoint(finished,result);return
    if args.action=='admit':
        if finished.exists():raise SystemExit('Completed task cannot be automatically replayed')
        old=json.loads(marker.read_text()) if marker.exists() else {};count=old.get('attempts',0)
        if count>=task['attempt_limit']:raise SystemExit('Finite attempt budget exhausted')
        if (runtime/'cancel.json').exists():raise SystemExit('Runtime cancellation requested')
        if manifest:
            policy=json.loads((runtime/'capacity-policy.json').read_text());provider=json.loads((runtime/'provider-proof.json').read_text());pool=Pool(policy['symphony']['pool_path'],policy)
            lease=runtime_lease_ids(runtime,manifest)[workspace.name]
            binding={'branch':BRANCH,'head':args.head,'owner':task['owner'],'write_roots':task['allowed_paths'],'resources':task['resources'],'task_sha256':manifest_digest(dict(runtime=str(runtime),manifest_sha256=manifest_digest(manifest),task=task))}
            admitted=pool.admit(lease,binding,provider,host_snapshot(runtime))
            if admitted.get('reused'):raise SystemExit('Existing lease requires outcome reconciliation before another coding attempt')
            old['lease_id']=lease
            checkpoint(runtime/(workspace.name+'-task.json'),dict(task,issue=workspace.name,manifest_sha256=manifest_digest(manifest)))
        checkpoint(marker,dict(old,issue=workspace.name,source_head=args.head,attempts=count+1))


if __name__=='__main__':
    try:main()
    except (AdmissionError,ValueError,OSError) as error:raise SystemExit(str(error))
