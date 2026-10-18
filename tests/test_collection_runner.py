"""Acquisition orchestration tests; no live network or country acceptance."""
from dataclasses import asdict, replace
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest

from offmenu.refresh.acquisition import collect_registry
from offmenu.refresh.core import RefreshError, canonical, sha
from test_refresh_acquisition import SPEC, NOW, Response, Transport


class CollectionRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.evidence = self.root / 'review.json'
        self.evidence.write_bytes(b'{"fixtureReview":true}')
        self.pin = {'path': str(self.evidence), 'sha256': sha(self.evidence.read_bytes())}
        self.registry = {
            'schemaVersion': 'offmenu-acquisition-selection/1',
            'resources': {'storageRoot': str(self.root / 'cache'), 'maxTransferBytes': 1024,
                          'minimumFreeBytes': 0, 'maxSeconds': 30},
            'sources': [self.entry(SPEC)],
            'bindings': [self.binding(SPEC.source_key, 'AU', 'foods'),
                         self.binding(SPEC.source_key, 'BE', 'foods'),
                         self.binding(SPEC.source_key, 'AU', 'nutrients')],
            'evidence': [self.pin]}

    def tearDown(self):
        self.temp.cleanup()

    def entry(self, spec):
        return {'spec': asdict(spec), 'operation': 'https-refresh', 'retained': None,
                'claim': {'owner': 0, 'state': 'selected', 'evidence': self.pin}, 'holds': []}

    def binding(self, key, country, kind):
        return {'sourceKey': key, 'country': country, 'type': kind, 'evidence': self.pin}

    def run_batch(self, transport, now=NOW):
        path = self.root / 'registry.json'
        path.write_bytes(canonical(self.registry))
        return collect_registry(path, sha(path.read_bytes()), self.root / 'reports',
                                transport=transport, now=now)

    def retained(self):
        body = self.root / 'original.csv'
        body.write_bytes(b'original untouched bytes\n')
        self.registry['sources'][0].update(operation='retained-copy', retained={
            'path': str(body), 'sha256': sha(body.read_bytes()), 'bytes': body.stat().st_size,
            'originalAcquiredAt': NOW.isoformat(), 'headers': {'etag': 'validator-not-checksum'},
            'evidence': self.pin})
        return body

    def test_many_to_many_once_then_repeat_zero_network(self):
        t = Transport(Response())
        first = self.run_batch(t)
        second = self.run_batch(t, NOW + timedelta(days=29))
        self.assertEqual(len(t.calls), 1)
        self.assertEqual(first['network'], {'requests': 1, 'bodyBytesRead': 7})
        self.assertEqual(second['network'], {'requests': 0, 'bodyBytesRead': 0})
        self.assertEqual(len(second['sources'][0]['bindings']), 3)
        self.assertFalse(second['countryComplete'])
        self.assertEqual(second['normalized'], 0)

    def test_due_conditional_refresh_preserves_original(self):
        t = Transport(Response(headers={'etag': 'version'}), Response(304))
        self.run_batch(t)
        result = self.run_batch(t, NOW + timedelta(days=30))
        self.assertEqual(t.calls[-1][1]['If-None-Match'], 'version')
        self.assertEqual(result['sources'][0]['provenance']['originalAcquiredAt'], NOW.isoformat())
        self.assertEqual(result['network']['bodyBytesRead'], 0)

    def test_held_source_isolated_and_not_requested(self):
        self.registry['sources'][0]['holds'] = ['source-use restriction']
        other = replace(SPEC, source_key='z-independent', url='https://publisher.example/other')
        self.registry['sources'].append(self.entry(other))
        self.registry['bindings'].append(self.binding(other.source_key, 'LY', 'prices'))
        t = Transport(Response())
        result = self.run_batch(t)
        self.assertEqual(result['failedSources'], 1)
        self.assertEqual(result['verifiedSources'], 1)
        self.assertEqual(t.calls[0][0].source_key, 'z-independent')

    def test_forbidden_not_retried_and_remaining_source_runs(self):
        other = replace(SPEC, source_key='z-independent', url='https://publisher.example/other')
        self.registry['sources'].append(self.entry(other))
        self.registry['bindings'].append(self.binding(other.source_key, 'LY', 'prices'))
        t = Transport(Response(403), Response())
        result = self.run_batch(t)
        self.assertEqual(len(t.calls), 2)
        self.assertEqual(result['failedSources'], 1)
        self.assertEqual(result['verifiedSources'], 1)

    def test_retained_import_repeat_preserves_original_and_evidence(self):
        original = self.retained()
        before = original.read_bytes(), original.stat().st_mtime_ns
        t = Transport()
        first = self.run_batch(t)
        cached = Path(first['sources'][0]['path'])
        mtime = cached.stat().st_mtime_ns
        repeat = self.run_batch(t, NOW + timedelta(days=1))
        self.assertEqual(t.calls, [])
        self.assertEqual(cached.stat().st_mtime_ns, mtime)
        self.assertEqual((original.read_bytes(), original.stat().st_mtime_ns), before)
        provenance = repeat['sources'][0]['provenance']
        self.assertEqual(provenance['result'], 'retained-import')
        self.assertEqual(provenance['originalAcquiredAt'], NOW.isoformat())
        self.assertEqual(provenance['checkedAt'], NOW.isoformat())
        self.assertEqual(provenance['retainedOrigin']['evidence'], self.pin)

    def test_corrupt_original_and_corrupt_cache_fail_closed(self):
        original = self.retained()
        original.write_bytes(b'changed')
        bad = self.run_batch(Transport())
        self.assertEqual(bad['sources'][0]['error'], 'retained-original-mismatch')
        original.write_bytes(b'original untouched bytes\n')
        good = self.run_batch(Transport())
        Path(good['sources'][0]['path']).write_bytes(b'corrupt')
        again = self.run_batch(Transport())
        self.assertEqual(again['sources'][0]['error'], 'cached-body-corrupt')

    def test_missing_or_other_owner_claim_blocks_without_network(self):
        self.registry['sources'][0]['claim']['owner'] = 22
        t = Transport()
        self.assertEqual(self.run_batch(t)['sources'][0]['error'], 'collection-claim-not-selected')
        self.assertEqual(t.calls, [])

    def test_registry_and_binding_evidence_fail_before_source_request(self):
        path = self.root / 'registry.json'
        path.write_bytes(canonical(self.registry))
        with self.assertRaisesRegex(RefreshError, 'registry-pin-mismatch'):
            collect_registry(path, '0' * 64, self.root / 'reports', transport=Transport(), now=NOW)
        self.evidence.write_bytes(b'changed review')
        with self.assertRaisesRegex(RefreshError, 'evidence-pin-mismatch'):
            self.run_batch(Transport())

    def test_duplicate_release_must_use_bindings_not_alias_download(self):
        self.registry['sources'].append(self.entry(replace(SPEC, source_key='alias')))
        with self.assertRaisesRegex(RefreshError, 'duplicate-source-release'):
            self.run_batch(Transport())

    def test_stale_retained_does_not_reset_age_or_download(self):
        self.retained()
        t = Transport()
        result = self.run_batch(t, NOW + timedelta(days=30))
        self.assertEqual(result['sources'][0]['error'], 'cache-stale')
        self.assertEqual(t.calls, [])

    def test_interrupted_copy_is_restarted_not_appended(self):
        self.retained()
        from offmenu.refresh.acquisition import SourceSpec
        identity = SourceSpec(**self.registry['sources'][0]['spec']).identity()
        directory = self.root / 'cache' / 'requests' / sha(canonical(identity))
        directory.mkdir(parents=True)
        (directory / 'body.partial').write_bytes(b'never append this')
        result = self.run_batch(Transport())
        self.assertEqual(result['verifiedSources'], 1)
        self.assertEqual(Path(result['sources'][0]['path']).read_bytes(), b'original untouched bytes\n')
        self.assertFalse((directory / 'body.partial').exists())

    def test_cumulative_batch_budget_counts_discarded_and_success_bytes(self):
        self.registry['resources']['maxTransferBytes'] = 128
        other = replace(SPEC, source_key='z-independent', url='https://publisher.example/other')
        self.registry['sources'].append(self.entry(other))
        self.registry['bindings'].append(self.binding(other.source_key, 'LY', 'prices'))
        t = Transport(Response(body=b'a' * 100), Response(body=b'b' * 40))
        result = self.run_batch(t)
        self.assertEqual(result['verifiedSources'], 1)
        self.assertEqual(result['sources'][1]['error'], 'batch-transfer-budget-exceeded')
        self.assertEqual(result['network']['bodyBytesRead'], 128)


if __name__ == '__main__':
    unittest.main()
