"""Synthetic local Git remotes only. Never imports or starts the ingest engine."""
import importlib.util
import os
from pathlib import Path
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
RUNNER_PACKAGE = PACKAGE if (PACKAGE / 'plan_runner.py').exists() else PACKAGE.parents[1] / 'offmenu-manual-action-20261022/manual-action'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


legacy = load('reconciliation_generated_fixture', RUNNER_PACKAGE / 'tests/test_plan_runner.py')
m = legacy.m
h = load('reconcile_returns', PACKAGE / 'reconcile_returns.py')


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.case = legacy.RunnerTests('test_success_commit_push_idempotent_and_unrelated_dirty_preserved')
        self.case.setUp()
        self.base = self.case.head()
        self.editor = self.case.editor()
        (self.editor / 'reviewed.txt').write_text('Reviewed code/documentation fixture\n')
        self.case.git_at(self.editor, 'add', 'reviewed.txt')
        self.case.git_at(self.editor, 'commit', '-m', 'Reviewed remote code fixture')
        self.case.git_at(self.editor, 'push', 'origin', m.BRANCH)
        self.remote = self.case.head(self.case.remote)
        self.runner = self.case.Runner(self.case.root)
        self.case.runners.append(self.runner)
        self.runner.ingest_engine = lambda: self.fail('reconciliation must not load ingestion')
        self.runner.run_plan = lambda: self.fail('reconciliation must not start a plan')

    def tearDown(self):
        self.case.tearDown()

    def receipt(self, key='a'):
        value = {'schema':m.RECEIPT_SCHEMA,'job_id':'supplier-source-inspection',
                 'job_version':2,'operation':'supplier_inspect','job_key':key*64,
                 'implementation_sha256':'b'*64,'input_sha256':None,
                 'observed_at':'2026-10-22T00:00:00Z','outcome':'blocked',
                 'supplier':{'status':'blocked','reason':'json_rows_refused','member_count':0,'transfer':'NOT_UPLOADED'},
                 'data_loads':'not_implemented','source_review':'manual_review_required','source_upload':'NOT_UPLOADED'}
        path = self.case.root / m.receipt_relpath(value)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(m.canonical(value))
        self.case.git_at(self.case.root, 'add', '-f', '--', str(path.relative_to(self.case.root)))
        self.case.git_at(self.case.root, 'commit', '-m', m.COMMIT_MESSAGE)
        return self.case.head(), path

    def reconcile(self):
        return h.reconcile(self.runner, m, self.remote, self.base)

    def close(self):
        self.case.close(self.runner)

    def test_divergence_preserves_both_parent_histories_and_private_spool(self):
        local, path = self.receipt()
        original = path.read_bytes()
        spool = self.case.root / '.git/offmenu-runner/ingest-pending/generated-sentinel'
        spool.parent.mkdir(parents=True, exist_ok=True)
        spool.write_bytes(b'private durable spool sentinel')
        self.assertEqual(self.reconcile(), 0)
        self.assertEqual(self.case.head(), self.case.head(self.case.remote))
        parents = self.case.git_at(self.case.root, 'rev-list', '--parents', '-n', '1', 'HEAD').split()[1:]
        self.assertEqual(parents, [local, self.remote])
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(spool.read_bytes(), b'private durable spool sentinel')
        self.assertTrue((self.case.root / 'reviewed.txt').exists())

    def test_fast_forward_does_not_create_merge(self):
        self.assertEqual(self.reconcile(), 0)
        self.assertEqual(self.case.head(), self.remote)

    def test_local_only_receipt_has_no_rewrite(self):
        self.case.git_at(self.case.root, 'fetch', 'origin', m.BRANCH)
        self.case.git_at(self.case.root, 'merge', '--ff-only', self.remote)
        local, _ = self.receipt()
        self.assertEqual(self.reconcile(), 0)
        self.assertEqual(self.case.head(), local)
        self.assertEqual(self.case.head(self.case.remote), local)

    def test_remote_pin_change_refuses_before_worktree_mutation(self):
        local, _ = self.receipt()
        (self.editor / 'reviewed.txt').write_text('New unreviewed remote version\n')
        self.case.git_at(self.editor, 'commit', '-am', 'Later remote commit')
        self.case.git_at(self.editor, 'push', 'origin', m.BRANCH)
        with self.assertRaisesRegex(m.Stop, 'remote_changed_since_review'):
            self.reconcile()
        self.assertEqual(self.case.head(), local)
        self.assertFalse((self.case.root / 'reviewed.txt').exists())

    def test_active_run_lock_refuses_without_fetch(self):
        active = self.case.new_runner(pull=False)
        local = self.case.head()
        with self.assertRaisesRegex(m.Stop, 'another_run_is_active'):
            self.reconcile()
        self.assertEqual(self.case.head(), local)
        self.assertFalse((self.case.root / '.git/FETCH_HEAD').exists())

    def test_dirty_tracked_worktree_preserved(self):
        path = self.case.root / 'unrelated.txt'
        path.write_text('Uncommitted user work\n')
        with self.assertRaisesRegex(m.Stop, 'clean_tracked_worktree'):
            self.reconcile()
        self.assertEqual(path.read_text(), 'Uncommitted user work\n')
        self.assertEqual(self.case.head(), self.base)

    def test_dirty_index_preserved(self):
        path = self.case.root / 'unrelated.txt'
        path.write_text('Staged user work\n')
        self.case.git_at(self.case.root, 'add', 'unrelated.txt')
        staged = self.case.git_at(self.case.root, 'diff', '--cached')
        with self.assertRaisesRegex(m.Stop, 'staged_changes'):
            self.reconcile()
        self.assertEqual(self.case.git_at(self.case.root, 'diff', '--cached'), staged)

    def test_unrelated_commit_refused_even_with_receipt_commit_message(self):
        (self.case.root / 'raw-dataset.csv').write_text('Generated synthetic row\n')
        self.case.git_at(self.case.root, 'add', 'raw-dataset.csv')
        self.case.git_at(self.case.root, 'commit', '-m', m.COMMIT_MESSAGE)
        before = self.case.head()
        with self.assertRaisesRegex(m.Stop, 'non_receipt_path'):
            self.reconcile()
        self.assertEqual(self.case.head(), before)
        self.assertEqual(self.case.head(self.case.remote), self.remote)

    def test_unrelated_commit_message_refused(self):
        self.receipt()
        self.case.git_at(self.case.root, 'commit', '--allow-empty', '-m', 'User unrelated commit')
        with self.assertRaisesRegex(m.Stop, 'unrelated_local_commit'):
            self.reconcile()

    def test_malformed_receipt_never_pushed(self):
        _, path = self.receipt()
        path.write_text('{}\n')
        self.case.git_at(self.case.root, 'add', '-f', str(path.relative_to(self.case.root)))
        self.case.git_at(self.case.root, 'commit', '-m', m.COMMIT_MESSAGE)
        before = self.case.head()
        with self.assertRaises(m.Stop):
            self.reconcile()
        self.assertEqual(self.case.head(), before)
        self.assertEqual(self.case.head(self.case.remote), self.remote)

    def test_missing_published_checkpoint_ancestry_refused(self):
        with self.assertRaisesRegex(m.Stop, 'published_checkpoint_ancestry'):
            h.reconcile(self.runner, m, self.remote, '0'*40)
        self.assertEqual(self.case.head(), self.base)

    def test_push_failure_preserves_merge_and_same_pin_retry_succeeds(self):
        local, _ = self.receipt()
        original = self.runner.git
        def fail_push(*args, **kwargs):
            if args[0] == 'push':
                raise m.Stop('git_push_failed_local_work_preserved')
            return original(*args, **kwargs)
        self.runner.git = fail_push
        with self.assertRaisesRegex(m.Stop, 'git_push_failed'):
            self.reconcile()
        merged = self.case.head()
        self.assertNotEqual(merged, local)
        self.assertEqual(self.case.head(self.case.remote), self.remote)
        self.close()
        self.runner.git = original
        self.assertEqual(self.reconcile(), 0)
        self.assertEqual(self.case.head(), merged)
        self.assertEqual(self.case.head(self.case.remote), merged)

    def test_remote_push_race_refused_preserving_local_merge(self):
        self.receipt()
        original = self.runner.git
        def advance_then_push(*args, **kwargs):
            if args[0] == 'push':
                (self.editor / 'reviewed.txt').write_text('Concurrent remote change\n')
                self.case.git_at(self.editor, 'commit', '-am', 'Concurrent remote change')
                self.case.git_at(self.editor, 'push', 'origin', m.BRANCH)
            return original(*args, **kwargs)
        self.runner.git = advance_then_push
        with self.assertRaisesRegex(m.Stop, 'git_push_failed'):
            self.reconcile()
        self.assertNotEqual(self.case.head(), self.case.head(self.case.remote))
        self.assertEqual(self.case.git_at(self.case.root, 'status', '--porcelain'), '')

    def test_merge_conflict_is_left_for_review_not_resolved_or_aborted(self):
        local, path = self.receipt()
        remote_path = self.editor / path.relative_to(self.case.root)
        remote_path.parent.mkdir(parents=True, exist_ok=True)
        remote_path.write_text('Generated conflicting remote fixture\n')
        self.case.git_at(self.editor, 'add', '-f', str(remote_path.relative_to(self.editor)))
        self.case.git_at(self.editor, 'commit', '-m', 'Generated conflicting reviewed remote')
        self.case.git_at(self.editor, 'push', 'origin', m.BRANCH)
        self.remote = self.case.head(self.case.remote)
        with self.assertRaisesRegex(m.Stop, 'git_merge_failed'):
            self.reconcile()
        self.assertEqual(self.case.head(), local)
        self.assertTrue((self.case.root / '.git/MERGE_HEAD').exists())
        self.assertEqual(self.case.head(self.case.remote), self.remote)

    def test_inherited_bootstrap_lock_is_validated_and_reused(self):
        self.receipt()
        bootstrap = self.case.new_runner(pull=False)
        inherited = bootstrap.lock
        self.assertEqual(h.reconcile(self.runner, m, self.remote, self.base, inherited_lock=inherited), 0)
        self.assertEqual(self.runner.lock, inherited)
        bootstrap.lock = None  # Ownership was transferred, not duplicated.

    def test_untracked_collision_is_preserved_and_refused(self):
        local, _ = self.receipt()
        path = self.case.root / 'reviewed.txt'
        path.write_text('Untracked user content must survive\n')
        with self.assertRaisesRegex(m.Stop, 'git_merge_failed'):
            self.reconcile()
        self.assertEqual(path.read_text(), 'Untracked user content must survive\n')
        self.assertEqual(self.case.head(), local)

    def test_counterfeit_recovery_merge_with_unrelated_tree_change_is_refused(self):
        self.receipt()
        self.case.git_at(self.case.root, 'fetch', 'origin', m.BRANCH)
        self.case.git_at(self.case.root, 'merge', '--no-ff', '--no-commit', self.remote)
        (self.case.root / 'unrelated.txt').write_text('Unauthorized merge alteration\n')
        self.case.git_at(self.case.root, 'add', 'unrelated.txt')
        self.case.git_at(self.case.root, 'commit', '-m', h.MERGE_MESSAGE)
        before = self.case.head()
        with self.assertRaisesRegex(m.Stop, 'non_receipt_local_changes'):
            self.reconcile()
        self.assertEqual(self.case.head(), before)
        self.assertEqual(self.case.head(self.case.remote), self.remote)

    def test_missing_identity_uses_runner_ephemeral_fallback(self):
        self.receipt()
        self.case.git_at(self.case.root, 'config', '--unset', 'user.name')
        self.case.git_at(self.case.root, 'config', '--unset', 'user.email')
        from unittest.mock import patch
        with patch.dict(os.environ, {'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_NOSYSTEM':'1'}):
            self.assertEqual(self.reconcile(), 0)
        self.assertEqual(self.case.git_at(self.case.root, 'show', '-s', '--format=%an', 'HEAD'), 'OffMenu Runner')


if __name__ == '__main__':
    unittest.main()
