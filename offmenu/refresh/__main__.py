"""python3 -B -m offmenu.refresh --help"""
import argparse
import json
from pathlib import Path
import sys
import uuid

sys.dont_write_bytecode = True
from .core import RefreshError, cache_policy, load_manifest, replay
from .inventory import inventory


def main(argv=None):
    parser = argparse.ArgumentParser(description='Local-only OffMenu refresh pilot; no downloads or deployment.')
    commands = parser.add_subparsers(dest='command', required=True)
    scan = commands.add_parser('inventory', help='Read-only bounded metadata scan; no hashes or paths in receipt.')
    scan.add_argument('--root', type=Path, required=True)
    scan.add_argument('--max-entries', type=int, default=10000)
    scan.add_argument('--max-depth', type=int, default=4)
    plan = commands.add_parser('plan', help='Explain minimum-30-day reuse policy without reading assets or downloading.')
    plan.add_argument('--manifest', type=Path, required=True)
    plan.add_argument('--force-refresh', action='store_true')
    run = commands.add_parser('replay', help='Verify and replay one pinned local Wikibooks snapshot, offline.')
    run.add_argument('--manifest', type=Path, required=True)
    run.add_argument('--input-root', type=Path, required=True)
    run.add_argument('--workspace', type=Path, required=True)
    flags = run.add_mutually_exclusive_group()
    flags.add_argument('--resume', action='store_true')
    flags.add_argument('--force-rebuild', action='store_true', help='Repeat local transform; does not download or relax hashes.')
    flags.add_argument('--force-refresh', action='store_true', help='Reserved for acquisition; currently fails explicitly.')
    fixture_plan = commands.add_parser('plan-fixture', help='Plan one trusted packaged synthetic bundle; no downloads.')
    fixture_plan.add_argument('--fixture', required=True, choices=('norway',))
    fixture_plan.add_argument('--evidence', type=Path)
    fixture_plan.add_argument('--repin-synthetic-runtime', action='store_true')
    fixture_plan.add_argument('--force-refresh', action='store_true')
    fixture_run = commands.add_parser('replay-fixture', help='Replay only an immutable packaged synthetic bundle offline.')
    fixture_run.add_argument('--fixture', required=True, choices=('norway',))
    fixture_run.add_argument('--workspace', required=True, type=Path)
    fixture_run.add_argument('--repin-synthetic-runtime', action='store_true')
    fixture_flags = fixture_run.add_mutually_exclusive_group()
    fixture_flags.add_argument('--resume', action='store_true')
    fixture_flags.add_argument('--force-rebuild', action='store_true')
    fixture_flags.add_argument('--force-refresh', action='store_true', help='Unavailable; never downloads or overrides admission.')
    args = parser.parse_args(argv)
    operation_id = uuid.uuid4().hex
    try:
        if args.command == 'plan-fixture':
            from .policy import load_evidence, plan_fixture
            result = plan_fixture(args.fixture, load_evidence(args.evidence) if args.evidence else None,
                                  force=args.force_refresh, repin_runtime=args.repin_synthetic_runtime)
        elif args.command == 'replay-fixture':
            if args.force_refresh:
                raise RefreshError('online-acquisition-not-implemented')
            from .core import replay_fixture
            result = replay_fixture(args.fixture, args.workspace, resume=args.resume,
                                    force=args.force_rebuild, repin_runtime=args.repin_synthetic_runtime)
        elif args.command == 'inventory':
            result = inventory(args.root, max_entries=args.max_entries, max_depth=args.max_depth)
        elif args.command == 'plan':
            result = cache_policy(load_manifest(args.manifest), force=args.force_refresh)
        else:
            if args.force_refresh:
                raise RefreshError('online-acquisition-not-implemented')
            result = replay(load_manifest(args.manifest), args.input_root, args.workspace, resume=args.resume, force=args.force_rebuild)
    except RefreshError as error:
        result = {'schemaVersion': 'offmenu-refresh-error/1', 'status': 'failed', 'errorCode': str(error), 'operationId': operation_id, **getattr(error, 'refresh_context', {})}
    except (Exception, KeyboardInterrupt) as error:
        result = {'schemaVersion': 'offmenu-refresh-error/1', 'status': 'failed', 'errorCode': 'operation-failed-inspect-local-state', 'operationId': operation_id, **getattr(error, 'refresh_context', {})}
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 2 if result.get('status') == 'failed' else 0


if __name__ == '__main__':
    raise SystemExit(main())
