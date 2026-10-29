"""OffMenu-only native Symphony workspace hooks; no CIX dependencies."""
import argparse
import json
from pathlib import Path
import subprocess

BRANCH = 'feature/langgraph-delivery-standardization'
ISSUE = 'UIF-90'


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['create', 'admit', 'finish'])
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--head', required=True)
    parser.add_argument('--attempt-limit', type=int, default=2)
    args = parser.parse_args()
    workspace = Path.cwd()
    if workspace.name != ISSUE:
        raise SystemExit('Only UIF-90 is admitted')
    if args.action == 'create':
        if any(workspace.iterdir()):
            raise SystemExit('Refusing to overwrite a non-empty workspace')
        subprocess.run(['git', 'clone', '--shared', '--single-branch', '--branch', BRANCH, str(args.source), '.'], check=True)
    if git('branch', '--show-current') != BRANCH or git('rev-parse', 'HEAD') != args.head:
        raise SystemExit('Source branch/head mismatch; reconcile before retry')
    # Native Symphony may remove terminal issue workspaces. Preserve attempt count
    # outside that workspace and never infer remote cancellation from a local exit.
    if args.action == 'finish':
        (workspace.parent/'uif-90-run-finished.json').write_text(json.dumps({'issue': ISSUE, 'workspace': str(workspace), 'source_head': args.head, 'attempt_ended': True, 'accepted_delivery': False})+'\n')
        return
    marker = workspace.parent / 'uif-90-attempts.json'
    if args.action == 'admit':
        count = json.loads(marker.read_text())['attempts'] if marker.exists() else 0
        if count >= args.attempt_limit:
            raise SystemExit('Finite attempt budget exhausted')
        marker.write_text(json.dumps({'issue': ISSUE, 'source_head': args.head, 'attempts': count+1})+'\n')


if __name__ == '__main__':
    main()
