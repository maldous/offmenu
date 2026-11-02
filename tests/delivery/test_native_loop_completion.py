"""Composition checks for the existing native poll and dispatch producer.

Custody/provider/metadata boundaries are synthetic; no live work is dispatched.
"""
import asyncio
import os
from pathlib import Path
import stat
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import stokowski_adapter as adapter
import stokowski_prepare as prepare
import stokowski_unit_review as review
import test_stokowski_current_dispatch as fixtures
from symphony_capacity import AdmissionError


class NativeLoopCompletionTests(unittest.TestCase):
    def fixture(self):
        f = fixtures.CurrentDispatchTests('runTest')
        f.setUp()
        self.addCleanup(f.doCleanups)
        return f

    def test_control_dispatch_creates_private_intent_before_spawn_and_preserves_replay_fence(self):
        f = self.fixture()
        issue, runtime = f.qualify(891)
        native, _, _ = f.adapted()
        intent = runtime/'attempts'/issue.identifier/'dispatch-intent.json'
        observed = []
        async def spawn(*args, **kwargs):
            info = intent.lstat()
            self.assertTrue(stat.S_ISREG(info.st_mode))
            self.assertEqual(stat.S_IMODE(info.st_mode), 0o600)
            self.assertEqual(info.st_uid, os.getuid())
            review.custody(intent, os.getuid(), private=True)
            observed.append(intent.read_bytes())
            f.write(intent.parent/'receipt.json', dict(status='succeeded',child_tree_gone=True))
            return SimpleNamespace(pid=98765, returncode=0, communicate=AsyncMock())
        mask = os.umask(0o002)
        try:
            with patch.object(adapter.asyncio, 'create_subprocess_exec', side_effect=spawn) as launch:
                asyncio.run(f.turn(native, issue, runtime))
                with self.assertRaisesRegex(AdmissionError, 'current_retained_effect_requires_reconciliation'):
                    asyncio.run(f.turn(native, issue, runtime))
                launch.assert_awaited_once()
        finally:
            os.umask(mask)
        self.assertEqual(intent.read_bytes(), observed[0])

    def test_native_verified_effect_waits_for_outcome_before_ephemeral_refill(self):
        f = self.fixture()
        native = f.native_harness_fixture()
        current = f.current
        selection = current._native_harness_selection(native.issue.identifier)
        current.config.pop('native_harness_boundaries')
        current.state['tasks'][native.issue.identifier]['native_publication'] = {
            'selection': {'path': str(native.selected), 'sha256': adapter.file_sha(native.selected)}}
        current.config['native_review_template'] = {'synthetic': True}
        current.config['owner_intake_policy'] = {'synthetic': True}
        helper = f.source/'tools/delivery/native_harness_linear.py'
        helper.write_text('# Explicit metadata boundary double.\n')
        current.config['source_sha256']['tools/delivery/native_harness_linear.py'] = adapter.file_sha(helper)
        review_path = current.runtime/('unit-review-'+native.issue.identifier+'.json')
        f.write(review_path, {'synthetic': 'review reference only'})
        f.write(native.sealed, current.config)
        current.config_sha = adapter.file_sha(native.sealed)
        tail = SimpleNamespace(__file__=str(helper), finalize_source_outcome=AsyncMock())
        canonical = AsyncMock(return_value={'fact': {}, 'evidence': {'path': 'synthetic', 'sha256': 'f'*64}})
        refill = AsyncMock()
        with patch.dict(sys.modules, native_harness_linear=tail), \
             patch.object(current, '_native_harness_selection', return_value=selection), \
             patch.object(prepare, 'owner_intake_policy', return_value={'synthetic': True}), \
             patch.object(prepare, 'owner_policy_contract', return_value={'source_outcome': {}}), \
             patch.object(prepare, 'owner_policy_refill', new=refill), \
             patch.object(native.module, 'verified_canonical_source', new=canonical, create=True), \
             patch.object(current, '_successor_boundary') as successor:
            tail.finalize_source_outcome.return_value = {'status': 'held', 'refill_eligible': False}
            asyncio.run(current.continue_native_harness(native.factory, linear_client=object()))
            self.assertEqual(tail.finalize_source_outcome.await_count, 1)
            refill.assert_not_awaited()
            successor.assert_not_called()
            self.assertIsNone(current._native_harness_refill)
            tail.finalize_source_outcome.return_value = {'status': 'verified', 'refill_eligible': True}
            asyncio.run(current.continue_native_harness(native.factory, linear_client=object()))
            self.assertEqual(tail.finalize_source_outcome.await_count, 2)
            refill.assert_awaited_once()
            successor.assert_called_once()
            self.assertIsNone(current._native_harness_refill)
            self.assertEqual(native.step.call_count, 1)

    def test_constructor_qualifies_original_native_context_before_refresh_or_save(self):
        f = self.fixture()
        native = f.native_harness_fixture()
        original = adapter.CurrentWork._native_harness_config
        checked = []
        def qualify(current):
            original(current)
            # The completed-continuation reader enters these actual owner and
            # original-unit readers; only its protected host boundary is double.
            current.guard()
            runtime, manifest, _ = current.context(native.issue.identifier,
                review=True, observation=True)
            self.assertEqual(current.state['references'][native.issue.identifier],
                             current.entries[native.issue.identifier])
            self.assertIn(native.issue.identifier, manifest['tasks'])
            checked.append(current.config_sha)
        before = f.current.state_path.read_bytes()
        with patch.object(adapter.CurrentWork, '_native_harness_config', new=qualify):
            opened = adapter.CurrentWork(f.runtime, read_only=True)
        self.assertEqual(checked, [opened.config_sha])
        self.assertEqual(f.current.state_path.read_bytes(), before)
        def refuse(current):
            qualify(current)
            raise AdmissionError('original-continuation-held')
        with patch.object(adapter.CurrentWork, '_native_harness_config', new=refuse), \
             patch.object(adapter.CurrentWork, 'refresh') as refresh:
            with self.assertRaisesRegex(AdmissionError, 'original-continuation-held'):
                adapter.CurrentWork(f.runtime)
        refresh.assert_not_called()
        self.assertEqual(f.current.state_path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
