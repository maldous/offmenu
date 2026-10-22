"""Bounded batch receipt publication against generated local Git only."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest import mock

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))
spec = importlib.util.spec_from_file_location('receipt_batch_fixture', PACKAGE / 'tests/test_receipt_branch.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
m = fixture.m
import receipt_branch as branch


class ReceiptBatchTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture.ReceiptBranchTests('test_legacy_v2_spool_migrates_without_changing_code_branch')
        self.case.setUp()
        self.runner = self.case.case.runner()
        self.original_git = self.runner.git
        self.calls = []
        self.runner.git = self.tracked_git

    def tearDown(self):
        self.case.tearDown()

    def tracked_git(self, *args, **kwargs):
        self.calls.append(args)
        return self.original_git(*args, **kwargs)

    def publisher(self):
        return branch.ReceiptBranchPublisher(self.runner, validate=m.validate_ingest_receipt,
            relpath=m.receipt_relpath, canonical=m.canonical, fail=m.Stop,
            validate_supplement=m.validate_supplement, supplement_relpath=m.supplement_relpath)

    def receipt(self, number, *, evidence=False, legacy=False):
        report = self.case.case.report('partial')
        if evidence:
            from ingest_evidence import sanitize_evidence
            report['ingest_evidence'] = sanitize_evidence({'phase': 'post'})
        summary = self.runner.ingest_summary(report)
        if legacy:
            summary.pop('pending_work')
            summary['progress_sha256'] = m.ingest_progress_digest(summary)
        value = {'schema': 'offmenu-run-receipt/2', 'job_id': 'retained-eight-domain-ingest',
            'job_version': 1, 'operation': 'retained_ingest_all', 'job_key': f'{number:064x}',
            'implementation_sha256': 'b' * 64, 'input_sha256': 'c' * 64,
            'observed_at': '2026-10-21T00:00:00Z', 'outcome': 'partial', 'ingest': summary}
        return value, m.build_supplement(report) if evidence else None

    def batch(self):
        return [self.receipt(i, evidence=i >= 10, legacy=i < 10) for i in range(20)]

    def assert_exact_blobs(self, root_ref, items):
        for receipt, supplement in items:
            self.assertEqual(self.original_git('show', root_ref + ':' + m.receipt_relpath(receipt))[1], m.canonical(receipt))
            if supplement is not None:
                path = m.supplement_relpath(receipt['ingest']['evidence_ref'])
                self.assertEqual(self.original_git('show', root_ref + ':' + path)[1], m.canonical(supplement))

    def count(self, command):
        return sum(args[0] == command for args in self.calls)

    def test_twenty_old_receipts_one_tree_commit_push_and_checkout_unchanged(self):
        root = self.case.root
        (root / 'unrelated.txt').write_text('Retain generated unstaged change\n')
        (root / 'staged.txt').write_text('Retain generated staged change\n')
        self.original_git('add', 'staged.txt')
        index = (root / '.git/index').read_bytes()
        head = self.original_git('rev-parse', 'HEAD')[1]
        status = self.original_git('status', '--porcelain')[1]
        items = self.batch()
        self.publisher().publish_batch(iter(items))
        self.assertEqual(self.count('write-tree'), 1)
        self.assertEqual(self.count('commit-tree'), 1)
        self.assertEqual(self.count('push'), 1)
        self.assertIn(('push', 'origin', branch.LOCAL_REF + ':' + branch.LOCAL_REF), self.calls)
        self.assertEqual(self.original_git('rev-list', '--count', branch.LOCAL_REF)[1].strip(), b'1')
        self.assert_exact_blobs(branch.LOCAL_REF, items)
        self.assertEqual((root / '.git/index').read_bytes(), index)
        self.assertEqual(self.original_git('rev-parse', 'HEAD')[1], head)
        self.assertEqual(self.original_git('status', '--porcelain')[1], status)
        self.assertEqual((root / 'unrelated.txt').read_text(), 'Retain generated unstaged change\n')
        self.assertEqual((root / 'staged.txt').read_text(), 'Retain generated staged change\n')

    def failure_retry(self, error):
        items = self.batch()
        spool = self.runner.state / 'ingest-pending'
        spool.mkdir(parents=True, exist_ok=True)
        for receipt, _ in items:
            (spool / Path(m.receipt_relpath(receipt)).name).write_bytes(m.canonical({'sha256': m.digest(m.canonical(receipt)), 'receipt': receipt}))
        before = {p.name: p.read_bytes() for p in spool.iterdir()}
        def fail_push(*args, **kwargs):
            if args[0] == 'push':
                self.calls.append(args)
                raise error
            return self.tracked_git(*args, **kwargs)
        self.runner.git = fail_push
        with self.assertRaises(type(error)):
            self.publisher().publish_batch(items)
        local = self.original_git('rev-parse', branch.LOCAL_REF)[1]
        self.assertEqual(self.count('commit-tree'), 1)
        self.assertEqual(before, {p.name: p.read_bytes() for p in spool.iterdir()})
        self.assertEqual(list(self.runner.state.glob('receipt-index-*')), [])
        self.assert_exact_blobs(branch.LOCAL_REF, items)
        self.runner.git = self.tracked_git
        self.calls.clear()
        self.publisher().publish_batch(items)
        self.assertEqual(self.count('commit-tree'), 0)
        self.assertEqual(self.count('write-tree'), 0)
        self.assertEqual(self.count('push'), 1)
        self.assertEqual(self.original_git('rev-parse', branch.LOCAL_REF)[1], local)
        self.assertEqual(self.case.git(self.case.case.case.remote, 'rev-parse', branch.LOCAL_REF).encode(), local.strip())
        self.assert_exact_blobs(branch.LOCAL_REF, items)
        self.assertEqual(before, {p.name: p.read_bytes() for p in spool.iterdir()})

    def test_failed_push_retry_retains_commit_spool_and_exact_blobs(self):
        self.failure_retry(m.Stop('generated_push_failure_preserved'))

    def test_interrupted_push_retry_retains_commit_spool_and_exact_blobs(self):
        self.failure_retry(KeyboardInterrupt())

    def test_invalid_final_receipt_and_supplement_precede_any_git(self):
        good = self.receipt(1)
        bad = copy.deepcopy(good)
        bad[0]['unexpected'] = 'Generated rejected field'
        with self.assertRaises(m.Stop):
            self.publisher().publish_batch([good, bad])
        self.assertEqual(self.calls, [])
        bad_supplement = self.receipt(2, evidence=True)
        bad_supplement[0]['ingest']['evidence_ref']['sha256'] = 'd' * 64
        bad_supplement[0]['ingest']['progress_sha256'] = m.ingest_progress_digest(bad_supplement[0]['ingest'])
        with self.assertRaisesRegex(m.Stop, 'required_supplement_changed'):
            self.publisher().publish_batch([good, bad_supplement])
        self.assertEqual(self.calls, [])

    def test_conflicting_same_path_batch_rejected_before_any_git(self):
        first = self.receipt(1)
        other = copy.deepcopy(first)
        other[0]['observed_at'] = '2026-10-22T00:00:00Z'
        with self.assertRaisesRegex(m.Stop, 'batch_path_conflict'):
            self.publisher().publish_batch([first, other])
        self.assertEqual(self.calls, [])

    def test_identical_duplicates_and_existing_timestamp_compatibility(self):
        first = self.receipt(1)
        self.publisher().publish_batch([first, first])
        self.assertEqual(self.count('commit-tree'), 1)
        self.calls.clear()
        other = copy.deepcopy(first)
        other[0]['observed_at'] = '2026-10-22T00:00:00Z'
        self.publisher().publish(*other)
        self.assertEqual(self.count('commit-tree'), 0)
        self.assertEqual(self.count('push'), 1)
        self.assert_exact_blobs(branch.LOCAL_REF, [first])

    def test_batch_count_and_size_limits_precede_any_git(self):
        first, second = self.receipt(1), self.receipt(2)
        with mock.patch.object(branch, 'MAX_RECEIPTS', 1):
            for items in ([first, second], [first, first], [self.receipt(1, evidence=True)]):
                with self.assertRaisesRegex(m.Stop, 'count_limit'):
                    self.publisher().publish_batch(items)
        with mock.patch.object(branch, 'MAX_TREE_BYTES', len(m.canonical(first[0]))):
            with self.assertRaisesRegex(m.Stop, 'size_limit'):
                self.publisher().publish_batch([first, second])
        self.assertEqual(self.calls, [])

    def test_empty_batch_has_no_git_side_effects(self):
        self.publisher().publish_batch(iter(()))
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
