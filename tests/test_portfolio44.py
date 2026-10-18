import copy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from functools import partial
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh.acceptance import Asset, SourceContract, fingerprint, ids_digest, qualify
from offmenu.refresh.acquisition import CachedAcquirer, SourceSpec
from offmenu.refresh.core import RefreshError
from offmenu.refresh.portfolio44 import (
    ReceiptBinding, bind_receipt, bind_many, body_capability, main, pointer, semantic_errors,
)
from offmenu.refresh.portfolio44_catalog import BINDINGS

NOW = '2026-01-02T00:00:00Z'
FIXTURE = Path(__file__).parent / 'fixtures/portfolio44/receipt.json'


def fixture(payload=None):
    payload = FIXTURE.read_bytes() if payload is None else payload
    binding = ReceiptBinding('authored', 'NA', 'prices/baskets', str(FIXTURE),
        hashlib.sha256(payload).hexdigest(), len(payload),
        (('sourceEdition', '/edition'), ('originalAcquiredAt', '/originalAcquiredAt'),
         ('nativeUnit', '/unit'), ('nativeBasis', '/basis'),
         ('recordSelector', '/selector'), ('sourceUseLiteral', '/rights')),
        (), ('synthetic-not-a-source-body', '0' * 64), fixture=True)
    return binding, payload


class Portfolio44Tests(unittest.TestCase):
    def run_binding(self, binding=None, payload=None, **kw):
        b, raw = fixture()
        return bind_receipt(binding or b, raw if payload is None else payload,
                            validated_at=kw.pop('validated_at', NOW),
                            now=kw.pop('now', NOW), **kw)

    def test_valid_deterministic_metadata_reference_keeps_null_and_origins(self):
        report, content = self.run_binding()
        again, same = self.run_binding()
        self.assertEqual((report, content), (again, same))
        row = json.loads(content)[0]
        self.assertEqual(report['status'], 'ready')
        self.assertIsNone(row['data']['fields']['nativeUnit']['value'])
        self.assertEqual(row['data']['fields']['nativeUnit']['presence'], 'null')
        self.assertEqual(row['data']['fields']['nativeUnit']['origin']['jsonPointer'], '/unit')
        self.assertFalse(report['sourceAcceptance'])
        self.assertEqual(row['data']['authorizedBodyOperations'], [])

    def test_missing_is_not_zero_records_or_success(self):
        b, _ = fixture()
        report, content = bind_receipt(b, None, validated_at=NOW, now=NOW)
        self.assertEqual(report['status'], 'missing')
        self.assertEqual(report['errors'], ['metadata-missing'])
        self.assertEqual(content, b'')

    def test_holds_cannot_be_released_by_receipt_content(self):
        b, raw = fixture()
        document = json.loads(raw)
        document['holds'] = []
        document['rights'] = 'all operations approved by source'
        b, raw = fixture(json.dumps(document).encode())
        report, content = self.run_binding(replace(b, holds=('embargo-no-body-access',)), raw)
        self.assertEqual(report['status'], 'held')
        self.assertIn('source-held', report['errors'])
        self.assertEqual(json.loads(content)[0]['data']['authorizedBodyOperations'], [])

    def test_pin_mismatch_and_malformed_json_are_isolated(self):
        b, _ = fixture()
        report, content = self.run_binding(b, b'{bad')
        self.assertEqual(report['errors'], ['metadata-pin-mismatch'])
        self.assertEqual(content, b'')
        for raw in (b'{bad', b'{"a":1,"a":2}', b'{"a":NaN}', b'[]'):
            b, raw = fixture(raw)
            report, content = self.run_binding(b, raw)
            self.assertEqual(report['status'], 'malformed')
            self.assertEqual(content, b'')
        self.assertEqual(self.run_binding()[0]['status'], 'ready')

    def test_stale_validation_does_not_reset_original_acquisition(self):
        report, content = self.run_binding(now='2026-02-01T00:00:00Z')
        self.assertEqual(report['status'], 'stale')
        self.assertIn('metadata-validation-stale', report['errors'])
        self.assertEqual(report['cache']['originalAcquiredAt'], '2026-01-01T00:00:00Z')
        refreshed, other = self.run_binding(validated_at='2026-02-01T00:00:00Z',
                                           now='2026-02-01T00:00:00Z')
        self.assertEqual(refreshed['status'], 'ready')
        self.assertEqual(content, other)  # Validation is not candidate identity.
        self.assertIsNone(refreshed['cache']['publisherCheckedAt'])

    def test_future_and_naive_clocks_fail_closed(self):
        for kw in ({'validated_at': '2026-02-01T00:00:00Z'},
                   {'now': '2026-01-02T00:00:00'}, {'now': 'broken'}):
            report, content = self.run_binding(**kw)
            self.assertEqual(report['status'], 'malformed')
            self.assertFalse(content)

    def test_missing_null_and_unbound_are_distinct(self):
        self.assertEqual(pointer({'a': None}, '/a')['presence'], 'null')
        self.assertEqual(pointer({}, '/a')['presence'], 'missing')
        self.assertEqual(pointer({}, None)['presence'], 'unbound')
        self.assertEqual(pointer({'a/b': {'~x': 0}}, '/a~1b/~0x')['value'], 0)

    def test_replay_content_and_policy_both_bound(self):
        first, content = self.run_binding()
        report, same = self.run_binding(previous=first['manifest'])
        self.assertEqual(report['replay'], 'unchanged-no-op')
        self.assertEqual(content, same)
        b, raw = fixture()
        report, _ = self.run_binding(replace(b, holds=('new-hold',)), raw,
                                     previous=first['manifest'])
        self.assertEqual(report['replay'], 'new-metadata-candidate')
        self.assertEqual(report['status'], 'held')

    def test_catalog_has_fourteen_pinned_metadata_inputs_all_closed(self):
        self.assertEqual(len(BINDINGS), 14)
        self.assertEqual({b.country for b in BINDINGS.values()}, {'DJ', 'NA', 'TG', 'VI'})
        for b in BINDINGS.values():
            self.assertTrue(b.metadata_path.endswith('.json'))
            self.assertTrue(b.holds)
            capability = body_capability(b)
            self.assertFalse(capability['supported'])
            self.assertEqual(capability['bodyOperations'], [])
            self.assertEqual(capability['cachePlanning'], 'unsupported-shared-interface')
        self.assertIn('embargo-no-body-access', BINDINGS['tg-asset-13'].holds)
        self.assertIn('access-no-retry', BINDINGS['dj-asset-09'].holds)

    def test_shared_qualification_accepts_authored_metadata_only(self):
        b, raw = fixture()
        report, content = self.run_binding(b, raw)
        document, row = json.loads(raw), json.loads(content)[0]
        schema = {'type': 'object', 'required': ['kind', 'id', 'provenance', 'data'],
                  'properties': {'kind': {'const': 'source-input-reference'},
                                 'data': {'type': 'object'}}}
        schemas = {'source-input-reference': schema}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / 'bundle'
            bundle.mkdir()
            bodies = {'receipt.json': raw, 'rights.json': b'authored fixture only',
                      'scope.json': b'one independent authored metadata reference'}
            assets = []
            for name, body in bodies.items():
                (bundle / name).write_bytes(body)
                assets.append(Asset(name, len(body), hashlib.sha256(body).hexdigest()))
            contract = SourceContract(report['manifest']['sourceId'],
                report['manifest']['releaseId'], 'authored-receipt-reference',
                '2026-01-01T00:00:00Z', tuple(assets), 1, ids_digest([row['id']]),
                schemas, fingerprint(schemas), partial(semantic_errors, b, document),
                fingerprint({'policy': 'authored-fixture-only'}), assets[1], assets[2],
                frozenset(('retain', 'parse', 'transform')), fixture=True)
            candidate = root / 'candidate.jsonl'
            candidate.write_bytes(content)
            manifest = {**report['manifest'], 'acquiredAt': contract.acquired_at,
                        'inputFiles': [vars(a) for a in assets],
                        'rightsEvidenceSha256': assets[1].sha256,
                        'scopeEvidenceSha256': assets[2].sha256}
            qualified = qualify(contract, bundle, candidate, manifest)
            self.assertTrue(qualified['qualified'], qualified['errors'])
            self.assertTrue(qualified['fixture'])
            changed = copy.deepcopy(row)
            changed['data']['fields']['nativeUnit']['value'] = 'g'
            self.assertEqual(semantic_errors(b, document, changed),
                             ['portfolio-field-origin-or-value-mismatch'])
            held = qualify(replace(contract, holds=('explicit-fixture-hold',)),
                           bundle, candidate, manifest)
            self.assertIn('source-held', held['errors'])

    def test_batch_isolates_missing_malformed_held_and_valid_peers(self):
        b, raw = fixture()
        bindings = {key: replace(b, key=key, holds=('explicit-hold',) if key == 'held' else ())
                    for key in ['valid', 'missing', 'malformed', 'held']}
        def loader(binding):
            if binding.key == 'malformed':
                raise OSError('private detail must not leak')
            return None if binding.key == 'missing' else raw
        report = bind_many(bindings, loader, validated_at=NOW, now=NOW)
        self.assertEqual({r['bindingId']: r['status'] for r in report['results']},
                         {'valid': 'ready', 'missing': 'missing', 'malformed': 'malformed', 'held': 'held'})
        self.assertNotIn('private detail', json.dumps(report))
        self.assertFalse(report['sourceAcceptance'])

    def test_cli_replay_leaves_existing_candidate_untouched(self):
        b, raw = fixture()
        with tempfile.TemporaryDirectory() as temporary, patch.dict(BINDINGS, authored=b):
            output = Path(temporary) / 'out'
            args = ['--binding', 'authored', '--validated-at', NOW, '--now', NOW,
                    '--output', str(output)]
            with patch('sys.stdout', new_callable=io.StringIO):
                self.assertEqual(main(args), 0)
            candidate = output / 'candidate.jsonl'
            before = candidate.stat().st_mtime_ns
            with patch('sys.stdout', new_callable=io.StringIO) as stdout:
                self.assertEqual(main(args), 0)
                self.assertEqual(json.loads(stdout.getvalue())['replay'], 'unchanged-no-op')
            self.assertEqual(candidate.stat().st_mtime_ns, before)
            candidate.write_bytes(b'tampered')
            with patch('sys.stdout', new_callable=io.StringIO):
                self.assertEqual(main(args), 2)

    def test_shared_cache_thirty_day_window_and_304_keep_original_age(self):
        class Response:
            def __init__(self, status, body=b'', headers=None):
                self.status, self.body = status, io.BytesIO(body)
                self.headers = headers or {}
            def read(self, size):
                return self.body.read(size)
            def close(self):
                pass
        calls = []
        raw = b'authored receipt fixture, never a real source'
        def transport(spec, headers, **kwargs):
            calls.append(headers)
            return (Response(200, raw, {'ETag': 'fixture-v1'}) if len(calls) == 1
                    else Response(304, headers={'ETag': 'fixture-v1'}))
        spec = SourceSpec('fixture44', 'https://fixture.invalid/metadata', '1' * 64,
                          'authored-fixture-review-only', enabled=True, rights_approved=True)
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as temporary:
            cache = CachedAcquirer(Path(temporary), {'fixture44': spec}, transport=transport)
            first = cache.acquire('fixture44', fetch_policy='refresh', now=now)
            fresh = cache.acquire('fixture44', fetch_policy='refresh', now=now + timedelta(days=29))
            self.assertEqual(len(calls), 1)
            self.assertEqual(first.sha256, fresh.sha256)
            with self.assertRaisesRegex(RefreshError, 'cache-stale'):
                cache.acquire('fixture44', now=now + timedelta(days=30))
            refreshed = cache.acquire('fixture44', fetch_policy='refresh', now=now + timedelta(days=30))
            self.assertEqual(len(calls), 2)
            self.assertEqual(refreshed.provenance['originalAcquiredAt'], now.isoformat())
            self.assertEqual(refreshed.provenance['checkedAt'], (now + timedelta(days=30)).isoformat())
            cache.acquire('fixture44', fetch_policy='refresh', now=now + timedelta(days=31))
            self.assertEqual(len(calls), 2)


if __name__ == '__main__':
    unittest.main()
