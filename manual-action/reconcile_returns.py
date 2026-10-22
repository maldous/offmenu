#!/usr/bin/env python3
"""One-shot receipt-history reconciliation; never starts ingestion.

Reviewed for the fixed branch and fixed remote revision below. Run only after
./run has exited. Uses the runner's existing nonblocking lock and validators.
No reset, rebase, stash, clean, force push, payload logging, or spool deletion.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True

BRANCH = 'integration/manual-actions-20261022'
REVIEWED_REMOTE = 'c792d3b71bc7907e96b6688242e090ede100b6ab'
PUBLISHED_CHECKPOINT = '01c9c63bc6a7bdbdf66b971fe804c83845450939'
MERGE_MESSAGE = 'Reconcile reviewed code and sanitized receipts [skip ci]'
MAX_COMMITS = 4096
MAX_RECEIPT_BYTES = 65536


def load_runner(root):
    path = root / 'manual-action/plan_runner.py'
    spec = importlib.util.spec_from_file_location('offmenu_reconciliation_runner', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def merge_identity(runner):
    # git merge --no-commit still checks identity. This helper has no workers;
    # apply the existing runner fallback only to this one child command.
    fallback = runner.commit_identity_env()
    previous = {key: os.environ.get(key) for key in fallback}
    try:
        os.environ.update(fallback)
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def require_clean(runner, module):
    # Stricter than normal ./run: do not merge with ANY tracked edits or index
    # entries, including an otherwise recoverable staged runner receipt.
    if runner.git('diff', '--no-ext-diff', '--no-textconv', '--cached', '--name-only', '-z')[1]:
        raise module.Stop('reconciliation_requires_clean_index_preserved')
    if runner.git('diff', '--no-ext-diff', '--no-textconv', '--name-only', '-z')[1]:
        raise module.Stop('reconciliation_requires_clean_tracked_worktree_preserved')
    runner.preconditions()


def validate_receipt_delta(runner, module, before, after):
    raw = runner.git('diff-tree', '--no-ext-diff', '--no-textconv', '--no-renames',
                     '--no-commit-id', '--name-status', '-r', '-z', before, after)[1]
    fields = raw.split(b'\0')
    if fields[-1:] != [b'']:
        raise module.Stop('invalid_local_delta_preserved')
    fields.pop()
    if len(fields) % 2 or len(fields) > 2 * MAX_COMMITS:
        raise module.Stop('invalid_local_delta_preserved')
    for status, encoded_path in zip(fields[::2], fields[1::2]):
        if status != b'A':
            raise module.Stop('non_receipt_local_changes_preserved')
        path = encoded_path.decode('utf-8', errors='strict')
        module.validate_return_path(path)
        if not runner.regular_receipt_mode(path, after):
            raise module.Stop('non_regular_receipt_commit_preserved')
        object_name = after + ':' + path
        size = int(runner.textgit('cat-file', '-s', object_name))
        if not 0 < size <= MAX_RECEIPT_BYTES:
            raise module.Stop('local_receipt_size_limit_preserved')
        body = runner.git('show', object_name)[1]
        receipt = module.validate_receipt(json.loads(body))
        if module.receipt_relpath(receipt) != path or module.canonical(receipt) != body:
            raise module.Stop('non_sanitized_commit_pending_preserved')
    return len(fields) // 2


def validate_local_history(runner, module, remote, head='HEAD'):
    commits = runner.textgit('rev-list', '--max-count=' + str(MAX_COMMITS + 1),
                            remote + '..' + head).splitlines()
    if len(commits) > MAX_COMMITS:
        raise module.Stop('local_history_limit_preserved')
    for commit in commits:
        if int(runner.textgit('cat-file', '-s', commit)) > MAX_RECEIPT_BYTES:
            raise module.Stop('local_commit_size_limit_preserved')
        message = runner.textgit('show', '-s', '--format=%B', commit)
        parents = runner.textgit('rev-list', '--parents', '-n', '1', commit).split()[1:]
        if len(parents) == 1 and message in (module.COMMIT_MESSAGE, module.INGEST_COMMIT_MESSAGE):
            if not validate_receipt_delta(runner, module, parents[0], commit):
                raise module.Stop('empty_non_runner_commit_preserved')
        elif len(parents) == 2 and message == MERGE_MESSAGE and parents[1] == remote:
            # Allows safe retry after our merge succeeded but its non-force push
            # failed. An arbitrary merge edit cannot pass this receipt-only delta.
            validate_receipt_delta(runner, module, remote, commit)
        else:
            raise module.Stop('unrelated_local_commit_preserved')
    return bool(commits)


def reconcile(runner, module, reviewed_remote=REVIEWED_REMOTE,
              published_checkpoint=PUBLISHED_CHECKPOINT, inherited_lock=None):
    if module.BRANCH != BRANCH:
        raise module.Stop('unexpected_runner_branch_preserved')
    if not all(re.fullmatch(r'[0-9a-f]{40}', value) for value in (reviewed_remote, published_checkpoint)):
        raise module.Stop('full_reviewed_revisions_required')
    runner.acquire(inherited_lock)  # Nonblocking; validates any inherited lock FD.
    require_clean(runner, module)
    local_before = runner.textgit('rev-parse', 'HEAD')
    runner.git('fetch', '--no-tags', '--no-recurse-submodules', 'origin',
               'refs/heads/' + BRANCH)
    remote = runner.textgit('rev-parse', 'FETCH_HEAD')
    if remote != reviewed_remote:
        raise module.Stop('remote_changed_since_review_no_merge_or_push')
    for tip in (local_before, remote):
        if runner.git('merge-base', '--is-ancestor', published_checkpoint, tip, check=False)[0]:
            raise module.Stop('published_checkpoint_ancestry_required')
    validate_local_history(runner, module, remote)
    require_clean(runner, module)
    # Prevent unnoticed concurrent edits by a person or a tool not honoring the
    # runner lock. Git index locking remains the final protection during merge.
    if runner.textgit('rev-parse', 'HEAD') != local_before:
        raise module.Stop('checkout_changed_before_merge_preserved')
    if runner.git('merge-base', '--is-ancestor', remote, 'HEAD', check=False)[0]:
        if not runner.git('merge-base', '--is-ancestor', 'HEAD', remote, check=False)[0]:
            runner.git('merge', '--ff-only', '--no-edit', '--no-autostash', remote)
        else:
            # --no-commit guarantees a merge conflict leaves work available for
            # review. No automatic resolution or abort is attempted.
            with merge_identity(runner):
                runner.git('merge', '--no-ff', '--no-commit', '--no-edit',
                           '--no-autostash', '-s', 'ort', remote)
            # Merge has only exact approved remote changes and validated receipt
            # additions. Commit uses runner's per-command missing-identity fallback.
            runner.git('commit', '-m', MERGE_MESSAGE)
    require_clean(runner, module)
    final_head = runner.textgit('rev-parse', 'HEAD')
    if runner.git('merge-base', '--is-ancestor', local_before, final_head, check=False)[0]:
        raise module.Stop('original_local_history_not_preserved')
    if runner.git('merge-base', '--is-ancestor', remote, final_head, check=False)[0]:
        raise module.Stop('reviewed_remote_history_not_preserved')
    validate_local_history(runner, module, remote, final_head)
    validate_receipt_delta(runner, module, remote, final_head)
    # Fetch-to-push races are handled by a normal non-force push rejection.
    # No automatic refetch/merge/retry against an unreviewed new revision.
    runner.git('push', 'origin', final_head + ':refs/heads/' + BRANCH)
    module.announce('Reconciled and pushed sanitized receipt history. No ingestion was started; local data and pending receipt spool were untouched.')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, default=Path.cwd())
    args = parser.parse_args()
    module = None
    runner = None
    try:
        root = args.repository.absolute()
        module = load_runner(root)
        runner = module.Runner(root)
        return reconcile(runner, module, inherited_lock=os.environ.pop('OFFMENU_RECONCILE_FD', None))
    except Exception as error:
        reason = str(error) if module is not None and isinstance(error, module.Stop) else 'local_reconciliation_error'
        print('STOP: ' + reason + '. Local work preserved; no ingestion, reset, rebase, stash, clean or force push.', flush=True)
        return 2
    finally:
        if runner is not None and runner.lock is not None:
            os.close(runner.lock)
            runner.lock = None


if __name__ == '__main__':
    raise SystemExit(main())
