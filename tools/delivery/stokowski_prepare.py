"""Prepare one immutable OffMenu Stokowski execution manifest, without dispatch."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from symphony_workspace import checkpoint
from stokowski_adapter import SOURCE, PROJECT, SLUG, MODEL


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', required=True, type=Path)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--prompt', required=True, type=Path)
    args = parser.parse_args()
    from symphony_tasks import load_manifest
    head = subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip()
    manifest = load_manifest(args.manifest, expected_head=head,expected_branch=None)
    runtime = args.runtime.resolve()
    if not runtime.is_relative_to(SOURCE/'.delivery/stokowski') or runtime.exists():
        raise SystemExit('Select a new private Stokowski runtime directory')
    runtime.mkdir(parents=True, mode=0o700)
    for name in ('workspaces','requests','attempts'):
        (runtime/name).mkdir(mode=0o700)
    checkpoint(runtime/'manifest.json',manifest)
    shutil.copyfile(SOURCE/'tools/delivery/capacity-policy.json',runtime/'capacity-policy.json')
    shutil.copyfile(SOURCE/'.delivery/stokowski/installation.json',runtime/'installation.json')
    (runtime/'task.md').write_text(args.prompt.read_text())
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
    # JSON is a YAML subset, avoiding an unpinned dependency in this preparer.
    (runtime/'workflow.yaml').write_text(json.dumps(workflow,indent=2)+'\n')
    print(json.dumps({'status':'prepared','source_head':head,'project_id':PROJECT,
                      'runtime':str(runtime),'coding_ceiling':8,'model_calls':False}))


if __name__ == '__main__':
    main()
