#!/usr/bin/env python3
"""One-command per-worker launcher; no scheduler, hook installation or owner handoff."""
import os
from pathlib import Path
import re
import subprocess
import sys


def main():
    repo = Path.cwd().resolve()
    match = re.fullmatch(r'worker-(0[1-9]|[12][0-9]|3[0-2])', repo.name)
    if not match:
        print('Run from an existing permanent worker-01..worker-32 path.', file=sys.stderr)
        return 2
    args = sys.argv[1:]
    options = [a.split('=', 1)[0] for a in args]
    if any(a in ('--', '--?') or (a.startswith('--') and
           any(forbidden.startswith(a) for forbidden in ('--repo', '--worker'))) for a in options):
        print('Launcher binds --repo and --worker to the current permanent path.', file=sys.stderr)
        return 2
    helper = Path(__file__).with_name('offmenu-gitflow.py').resolve()
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    p = subprocess.run([sys.executable, '-B', str(helper), '--repo', str(repo), *args,
                        '--worker', str(int(match.group(1)))], env=env)
    return p.returncode


if __name__ == '__main__':
    sys.exit(main())
