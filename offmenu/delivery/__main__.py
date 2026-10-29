"""CLI for private local delivery receipts and durable LangGraph runs."""
import argparse
import json
from pathlib import Path
import sys

from .engine import DeliveryError, Engine, atomic, load_task, writer
from .standards import check, discover


def main():
    parser = argparse.ArgumentParser(prog='python -m offmenu.delivery')
    parser.add_argument('--root', type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('discover')
    sub.add_parser('check')
    prepare = sub.add_parser('prepare')
    prepare.add_argument('--task-id', required=True)
    prepare.add_argument('--owner', required=True)
    for name in ('run', 'status', 'cancel', 'reconcile'):
        command = sub.add_parser(name)
        command.add_argument('task', type=Path)
        if name == 'run':
            command.add_argument('--pause-after', choices=['discovery', 'standards', 'execute', 'verify'])
        if name == 'reconcile':
            command.add_argument('--check-id', required=True)
            command.add_argument('--outcome', choices=['failed', 'succeeded'], required=True)
            command.add_argument('--evidence', type=Path, required=True,
                                 help='Private evidence JSON: observer, reason, process_tree_gone=true')
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.action == 'prepare':
            import hashlib
            from .standards import git
            from .engine import ID
            if not ID.fullmatch(args.task_id):
                raise DeliveryError('Invalid task ID')
            with writer(root) as state:
                path = state / (args.task_id + '.json')
                if path.exists():
                    raise DeliveryError('Task already exists; inspect it, do not replace it')
                outputs = ['repository-standard.json', 'package.json', 'pyproject.toml',
                           'docs/standards/repository.md']
                task = {'version': 1, 'id': args.task_id, 'owner': args.owner,
                        'purpose': 'Accept the repository standard and durable developer workflow',
                        'base_revision': git(root, 'rev-parse', 'HEAD'),
                        'checks': [{'id': 'durable-workflow', 'argv': [sys.executable, '-m', 'unittest',
                                    'discover', '-s', 'tests/delivery', '-v'], 'timeout': 60}],
                        'accepted_outputs': {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in outputs}}
                atomic(path, task)
                result = {'status': 'prepared_for_review', 'task': str(path)}
        elif args.action in ('discover', 'check'):
            result = discover(root) if args.action == 'discover' else check(root)
        else:
            task = load_task(args.task)
            if args.action == 'cancel':
                # Cancellation does not wait for the active writer's lock.
                directory = root / '.delivery' / task['id']
                if not directory.exists():
                    raise DeliveryError('Task not found; no cancellation recorded')
                binding = json.loads((directory / 'binding.json').read_text())
                from .engine import digest
                if binding['task_sha256'] != digest(task):
                    raise DeliveryError('Task binding mismatch')
                atomic(directory / 'cancel.json', {'requested': True})
                result = {'status': 'cancellation_requested', 'task_id': task['id']}
            elif args.action == 'status':
                directory = root / '.delivery' / task['id']
                from .engine import digest
                if not directory.exists():
                    result = {'status': 'not_found', 'task_id': task['id']}
                else:
                    binding = json.loads((directory / 'binding.json').read_text())
                    if binding['task_sha256'] != digest(task):
                        raise DeliveryError('Task binding mismatch')
                    accepted = directory / 'accepted.json'
                    result = json.loads(accepted.read_text()) if accepted.exists() else {
                        'status': 'not_accepted', 'task_id': task['id'],
                        'checks': [json.loads((directory / (s['id'] + '.json')).read_text())
                                   for s in task['checks'] if (directory / (s['id'] + '.json')).exists()],
                        'cancellation_requested': (directory / 'cancel.json').exists()}
            else:
                with writer(root, reconciliation=args.action == 'reconcile') as state:
                    engine = Engine(root, state, task)
                    if args.action == 'reconcile':
                        if args.check_id not in {s['id'] for s in task['checks']}:
                            raise DeliveryError('Unknown check ID')
                        evidence = json.loads(args.evidence.read_text())
                        if evidence.get('process_tree_gone') is not True or not evidence.get('observer') or not evidence.get('reason'):
                            raise DeliveryError('Evidence requires observer, reason and process_tree_gone=true')
                        receipt = engine.directory / (args.check_id + '.json')
                        record = json.loads(receipt.read_text())
                        if record['status'] not in {'running', 'uncertain', 'timed_out', 'cancelled'}:
                            raise DeliveryError('Only uncertain outcomes need reconciliation')
                        if args.outcome == 'succeeded':
                            from .engine import verify_outputs
                            verify_outputs(root, task)
                        engine.event('reconciled', {'check': args.check_id, 'outcome': args.outcome,
                                                   'evidence': evidence})
                        record.update(status=args.outcome, reconciled=True)
                        atomic(receipt, record)
                        result = {'status': 'reconciled', 'check': args.check_id, 'outcome': args.outcome}
                    else:
                        result = engine.run(args.pause_after)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 1 if result.get('status') == 'failed' else 0
    except (DeliveryError, ValueError, OSError) as exc:
        print(json.dumps({'status': 'blocked', 'reason': str(exc)}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
