"""Prepare one immutable OffMenu Stokowski execution manifest, without dispatch."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from symphony_workspace import checkpoint
from stokowski_adapter import SOURCE, PROJECT, SLUG, MODEL, file_sha, CurrentWork


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', required=True, type=Path)
    parser.add_argument('--current', action='store_true', help='Prepare caller-owned current polling root; never starts a process. Example: --current --runtime /repo/.delivery/stokowski/current --runtime-root /repo/.delivery/stokowski --catalog /repo/.delivery/stokowski/catalog.json --owner existing-owner')
    parser.add_argument('--runtime-root', type=Path, help='Existing canonical private .delivery/stokowski root')
    parser.add_argument('--catalog', type=Path, help='Existing owner-qualified v1 catalog; see CurrentWork schema')
    parser.add_argument('--owner')
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--prompt', type=Path)
    args = parser.parse_args()
    if args.current:
        if not args.runtime_root or not args.catalog or not args.owner or args.manifest or args.prompt:
            parser.error('--current requires --runtime-root, --catalog, --owner; task manifest/request stay in qualified task runtimes')
        root = args.runtime_root
        if (root != root.resolve() or not root.is_dir() or root.name != 'stokowski'
            or root.parent.name != '.delivery' or args.catalog != args.catalog.resolve()
            or not args.catalog.is_relative_to(root) or not args.catalog.is_file()):
            parser.error('Current references must be canonical under existing private Stokowski root')
    elif not args.manifest or not args.prompt:
        parser.error('Finite mode requires --manifest and --prompt')
    from symphony_tasks import load_manifest
    head = subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip()
    manifest = None if args.current else load_manifest(args.manifest, expected_head=head,expected_branch=None)
    runtime = args.runtime.resolve()
    root = args.runtime_root if args.current else SOURCE/'.delivery/stokowski'
    if not runtime.is_relative_to(root) or runtime == root or runtime.exists() or (args.current and args.runtime != runtime):
        raise SystemExit('Select a new private Stokowski runtime directory')
    runtime.mkdir(parents=True, mode=0o700)
    for name in ('workspaces','requests','attempts'):
        (runtime/name).mkdir(mode=0o700)
    if not args.current:
        checkpoint(runtime/'manifest.json',manifest)
    shutil.copyfile(SOURCE/'tools/delivery/capacity-policy.json',runtime/'capacity-policy.json')
    shutil.copyfile((root if args.current else SOURCE/'.delivery/stokowski')/'installation.json',
                    runtime/'installation.json')
    (runtime/'task.md').write_text('Qualified immutable request is supplied by the existing owner.\n' if args.current else args.prompt.read_text())
    workflow = {
        'tracker':{'kind':'linear','project_slug':SLUG,'api_key':'$OFFMENU_LINEAR_API_KEY'},
        'workspace':{'root':str(runtime/'workspaces')},
        'polling':{'interval_ms':5000}, 'agent':{'max_concurrent_agents':8,'max_retry_backoff_ms':10000},
        'claude':{'model':MODEL,'turn_timeout_ms':180000,'stall_timeout_ms':90000},
        'linear_states':{'todo':'Todo','active':'In Progress','review':'In Review',
                         'gate_approved':'OffMenu Verified','rework':'OffMenu Rework',
                         'terminal':['Done','Canceled','Duplicate']},
        'states':{
            'implement':{'type':'agent','runner':'codex','model':MODEL,'prompt':'task.md',
                         'linear_state':'active','transitions':{'complete':'evidence-pending'}},
            'evidence-pending':{'type':'gate','linear_state':'review','rework_to':'implement',
                                'transitions':{'approve':'accepted'}},
            'accepted':{'type':'terminal','linear_state':'terminal'}},
        'server':{'host':'127.0.0.1'}
    }
    if args.current:
        # A qualified unit is only part of its parent outcome. Parent acceptance
        # remains with the existing integration/full-parent contract.
        workflow['states']['evidence-pending']['transitions'] = {'approve':'evidence-pending'}
        # The pinned schema requires a terminal definition; it is unreachable
        # in current mode, and the adapter independently blocks terminal effects.
    # JSON is a YAML subset, avoiding an unpinned dependency in this preparer.
    (runtime/'workflow.yaml').write_text(json.dumps(workflow,indent=2)+'\n')
    if args.current:
        names = ('stokowski_adapter.py','stokowski_worker.py','stokowski_prepare.py',
                 'symphony_capacity.py','symphony_tasks.py','symphony_workspace.py',
                 'symphony_codex.py','symphony_protocol.py','windmill_runner.py')
        checkpoint(runtime/'current.json', {
            'version':1, 'owner':args.owner, 'runtime_root':str(root),
            'catalog':str(args.catalog), 'source_head':head,
            'source_sha256':{'tools/delivery/'+name:file_sha(SOURCE/'tools/delivery'/name) for name in names},
            'workflow_sha256':file_sha(runtime/'workflow.yaml'),
            'installation_sha256':file_sha(runtime/'installation.json'),
            'policy_sha256':file_sha(runtime/'capacity-policy.json')})
        CurrentWork(runtime)
    print(json.dumps({'status':'prepared','source_head':head,'project_id':PROJECT,
                      'runtime':str(runtime),'coding_ceiling':8,'model_calls':False}))


if __name__ == '__main__':
    main()
