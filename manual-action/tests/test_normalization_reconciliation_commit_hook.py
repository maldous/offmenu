"""Atomic owner-checkpoint hook tests; generated fixtures only."""
import sqlite3
import unittest
import test_normalization_reconciliation as fixtures
import normalization_reconciliation as reconciliation
from normalization_api import NormalizationError


class ReconciliationCommitHookTests(unittest.TestCase):
    setUp = fixtures.ReconciliationTests.setUp
    artifact = fixtures.ReconciliationTests.artifact
    source_cache = fixtures.ReconciliationTests.source_cache
    count = fixtures.ReconciliationTests.count

    def checkpoint_table(self):
        self.store.db.execute('CREATE TABLE owner_checkpoint(cursor TEXT PRIMARY KEY, processed INTEGER NOT NULL)')
        self.store.db.commit()

    def test_hook_commits_facts_checkpoint_and_counters_together(self):
        self.checkpoint_table()
        seen = []
        def hook(db, result):
            self.assertTrue(db.in_transaction)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM artifacts').fetchone()[0], 1)
            self.assertEqual(result['new'], 1)
            db.execute('INSERT INTO owner_checkpoint VALUES(?,?)', ('key-a', 1))
            seen.append(result.copy())
            result['new'] = 999  # Callback cannot mutate the function's receipt.
        result = self.store.ingest_artifacts([self.artifact()], before_commit=hook)
        self.assertEqual(len(seen), 1)
        self.assertEqual(result['new'], 1)
        self.assertEqual(self.store.db.execute('SELECT * FROM owner_checkpoint').fetchone(), ('key-a', 1))
        self.assertFalse(self.store.db.in_transaction)

    def test_hook_failure_rolls_back_graph_checkpoint_and_quarantine(self):
        self.checkpoint_table()
        self.store.db.execute('CREATE TABLE owner_quarantine(cache_key TEXT PRIMARY KEY, reason TEXT NOT NULL)')
        self.store.db.commit()
        def hook(db, result):
            db.execute('INSERT INTO owner_checkpoint VALUES(?,?)', ('key-a', result['new']))
            db.execute('INSERT INTO owner_quarantine VALUES(?,?)', ('bad-key', 'fixture'))
            raise NormalizationError('fixture_output_cap')
        with self.assertRaisesRegex(NormalizationError, 'fixture_output_cap'):
            self.store.ingest_artifacts([self.artifact()], before_commit=hook)
        for table in ('artifacts', 'nodes', 'aliases', 'issues', 'owner_checkpoint', 'owner_quarantine'):
            self.assertEqual(self.count(table), 0)
        self.assertFalse(self.store.db.in_transaction)
        self.assertEqual(self.store.ingest_artifacts([self.artifact()])['new'], 1)

    def test_empty_artifact_batch_still_runs_hook_transactionally(self):
        self.checkpoint_table()
        calls = []
        def hook(db, result):
            self.assertTrue(db.in_transaction)
            self.assertEqual((result['new'], result['reused']), (0, 0))
            calls.append(True)
            db.execute('INSERT INTO owner_checkpoint VALUES(?,?)', ('empty-page', 0))
        result = self.store.ingest_artifacts([], before_commit=hook)
        self.assertEqual(calls, [True])
        self.assertEqual(result['new'], 0)
        self.assertEqual(self.count('owner_checkpoint'), 1)

    def test_cache_adapter_passes_hook_even_with_no_pending_keys(self):
        artifact = self.artifact()
        self.source_cache(artifact)
        self.checkpoint_table()
        calls = []
        def hook(db, result):
            calls.append(result['new'])
            db.execute('INSERT INTO owner_checkpoint VALUES(?,?)', (str(len(calls)), result['new']))
        reconciliation.ingest_cache_keys(self.root, 'ingredients', [artifact['cache_key']], self.store, before_commit=hook)
        reconciliation.ingest_cache_keys(self.root, 'ingredients', [], self.store, before_commit=hook)
        self.assertEqual(calls, [1, 0])
        self.assertEqual(self.count('artifacts'), 1)
        self.assertEqual(self.count('owner_checkpoint'), 2)

    def test_rolled_back_sample_reads_actual_page_growth_and_restores_size(self):
        before_pages = self.store.db.execute('PRAGMA page_count').fetchone()[0]
        page_size = self.store.db.execute('PRAGMA page_size').fetchone()[0]
        before_bytes = self.store.path.stat().st_size
        sample = {}
        def sample_hook(db, result):
            sample['pages'] = db.execute('PRAGMA page_count').fetchone()[0]
            sample['free_pages'] = db.execute('PRAGMA freelist_count').fetchone()[0]
            sample['bytes'] = sample['pages'] * db.execute('PRAGMA page_size').fetchone()[0]
            sample['new'] = result['new']
            raise NormalizationError('fixture_rollback_sample')
        with self.assertRaisesRegex(NormalizationError, 'fixture_rollback_sample'):
            self.store.ingest_artifacts([self.artifact(rid=str(i)) for i in range(128)], before_commit=sample_hook)
        self.assertEqual(sample['new'], 128)
        self.assertGreater(sample['pages'], before_pages)
        self.assertGreater(sample['bytes'], before_pages * page_size)
        self.assertEqual(self.count('artifacts'), 0)
        self.assertEqual(self.store.db.execute('PRAGMA page_count').fetchone()[0], before_pages)
        self.assertEqual(self.store.path.stat().st_size, before_bytes)

    def test_nested_transaction_control_is_denied_and_nothing_commits(self):
        for action in ('COMMIT', 'ROLLBACK', 'SAVEPOINT nested', 'BEGIN', 'executescript', 'commit_method'):
            with self.subTest(action=action):
                def hook(db, result):
                    if action == 'executescript':
                        db.executescript('CREATE TABLE must_not_exist(x)')
                    elif action == 'commit_method':
                        db.commit()
                    else:
                        db.execute(action)
                with self.assertRaises(sqlite3.DatabaseError):
                    self.store.ingest_artifacts([self.artifact()], before_commit=hook)
                self.assertEqual(self.count('artifacts'), 0)
                self.assertFalse(self.store.db.in_transaction)
        # The guard is removed in finally; normal outer commits remain possible.
        self.assertEqual(self.store.ingest_artifacts([self.artifact()])['new'], 1)

    def test_interrupt_rolls_back_and_releases_hook_guard(self):
        def hook(db, result): raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.store.ingest_artifacts([self.artifact()], before_commit=hook)
        self.assertEqual(self.count('artifacts'), 0)
        self.assertEqual(self.store.ingest_artifacts([self.artifact()])['new'], 1)

    def test_noncallable_hook_refused_without_writes(self):
        with self.assertRaisesRegex(NormalizationError, 'invalid_reconciliation_commit_hook'):
            self.store.ingest_artifacts([self.artifact()], before_commit='source text is never a hook')
        self.assertEqual(self.count('artifacts'), 0)


if __name__ == '__main__': unittest.main()
