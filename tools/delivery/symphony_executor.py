"""Native Codex app-server with per-workspace state; existing auth route only."""
import argparse
import os
from pathlib import Path
try:
    from .symphony_protocol import BINARY
except ImportError:
    from symphony_protocol import BINARY


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',required=True,type=Path)
    parser.add_argument('--model',required=True)
    args=parser.parse_args()
    workspace=Path.cwd().resolve()
    runtime=args.runtime.resolve()
    if workspace.parent != runtime/'workspaces':raise SystemExit('Workspace outside admitted runtime')
    state=runtime/'codex-state'/workspace.name
    if state.is_symlink():raise SystemExit('Unsafe session state')
    state.mkdir(parents=True,exist_ok=True,mode=0o700)
    policy=__import__('json').loads((runtime/'capacity-policy.json').read_text())
    reserved=policy['host']['cpu_reserve']
    width=(policy['symphony']['cpu_budget_millis']+999)//1000
    cpus=sorted(os.sched_getaffinity(0))[reserved:reserved+width]
    if not cpus:raise SystemExit('No native coding CPUs available')
    os.sched_setaffinity(0,cpus)
    environment=dict(os.environ,CODEX_SQLITE_HOME=str(state))
    os.execvpe(BINARY,[BINARY,'-c','model='+__import__('json').dumps(args.model),'-c','model_reasoning_effort="medium"','app-server'],environment)


if __name__=='__main__':main()
