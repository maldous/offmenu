"""Authored receipt fixtures and shared-contract integration; no publisher bodies."""
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch
import io
import json

from offmenu.portfolio39.binding import (ReceiptBinding, bind_receipt, bindings,
    run_portfolio, read_retained_metadata, MINIMUM_REUSE_SECONDS, MAX_METADATA_BYTES)
from offmenu.refresh.core import canonical, sha, RefreshError
from offmenu.refresh.field_provenance import datum_pointers, field_origin_errors
from offmenu.refresh.acquisition import SourceSpec, CachedAcquirer

FIXTURE = Path(__file__).parent / 'fixtures/portfolio39/receipt.json'
NOW = '2026-10-18T00:00:00Z'


def fixture(raw=None):
    raw = FIXTURE.read_bytes() if raw is None else raw
    selectors = {k: '/' + k for k in ('originalAcquiredAt', 'lastValidatedAt',
        'nativeUnits', 'nativeBasis', 'originalBytes', 'zero', 'false', 'lexical')}
    binding = ReceiptBinding('SZ', 'authored-fixture39', 'authored-v1',
        'metadata/fixture.json', len(raw), sha(raw), str(FIXTURE), selectors,
        ('recipes',), (), True)
    return binding, raw


class PortfolioBindingTests(TestCase):
    def test_positive_metadata_uses_shared_origin_and_stage_contracts(self):
        binding, raw = fixture()
        result = bind_receipt(binding, raw, now=NOW)
        self.assertEqual(result['outcome'], 'valid')
        self.assertEqual(result['metadataStage']['status'], 'succeeded')
        self.assertEqual(result['sourceStage']['status'], 'held')
        self.assertEqual(result['sourceOperations'], [])
        self.assertFalse(result['datasetAccepted'])
        row = result['record']
        self.assertEqual(field_origin_errors(row, {'metadata/fixture.json': sha(raw)}), [])
        self.assertEqual(set(row['provenance']['fieldOrigins']), set(datum_pointers(row['data'])))
        self.assertEqual(row['data']['originalBytes'], 0)
        self.assertIs(row['data']['false'], False)
        self.assertIsNone(row['data']['nativeUnits'])
        self.assertIsNone(row['data']['nativeBasis'])
        self.assertEqual(row['data']['lexical'], '1,300 ml')

    def test_complete_origin_pointers_escape_nested_source_keys(self):
        _, raw = fixture(); obj = json.loads(raw)
        obj['a/b'] = {'~x': [0, False]}; raw = canonical(obj)
        binding, _ = fixture(raw)
        binding = replace(binding, selectors={**binding.selectors, 'nested': '/a~1b/~0x'})
        result = bind_receipt(binding, raw, now=NOW)
        self.assertEqual(result['outcome'], 'valid')
        origins = result['record']['provenance']['fieldOrigins']
        self.assertEqual(origins['/data/nested/0']['sourceField'], '/a~1b/~0x/0')
        self.assertEqual(origins['/data/nested/1']['sourceField'], '/a~1b/~0x/1')

    def test_policy_unknown_is_distinct_from_source_explicit_null(self):
        binding, raw = fixture()
        binding = replace(binding, selectors={**binding.selectors, 'nativeBasis': None})
        row = bind_receipt(binding, raw, now=NOW)['record']
        origins = row['provenance']['fieldOrigins']
        self.assertEqual(origins['/data/nativeBasis']['kind'], 'constant')
        self.assertEqual(origins['/data/nativeUnits']['kind'], 'source')
        self.assertEqual(row['data']['nativeBasis'], row['data']['nativeUnits'])

    def test_all_four_portfolios_and_five_real_bindings_remain_held(self):
        entries = bindings()
        self.assertEqual({x.country for x in entries}, {'CX', 'MZ', 'SZ', 'VE'})
        self.assertEqual(len(entries), 5)
        for binding in entries:
            self.assertTrue(binding.holds)
            self.assertFalse(binding.acquisition_epoch_qualified)
            self.assertTrue(binding.retained_metadata_path.endswith('/receipt.json'))

    def test_held_receipt_flags_cannot_grant_source_operations(self):
        _, raw = fixture(); obj = json.loads(raw)
        obj.update(enabled=True, rightsApproved=True, holds=[], goldAdmitted=True)
        binding, raw = fixture(canonical(obj))
        binding = replace(binding, holds=('source-use-unqualified',))
        result = bind_receipt(binding, raw, now=NOW)
        self.assertEqual(result['outcome'], 'held')
        self.assertEqual(result['diagnostics'], ['source-use-unqualified'])
        self.assertFalse(result['goldAdmitted'])
        self.assertEqual(result['sourceOperations'], [])

    def test_missing_does_not_create_record_or_touch_declared_raw_path(self):
        binding, _ = fixture()
        with patch('builtins.open', side_effect=AssertionError('unexpected file read')):
            result = bind_receipt(binding, None, now=NOW)
        self.assertEqual(result['outcome'], 'missing')
        self.assertIsNone(result['record'])

    def test_malformed_duplicate_nonfinite_and_deep_json_are_isolated(self):
        for raw in (b'{', b'{"x":0,"x":1}', b'{"x":NaN}', b'{"x":1e9999}',
                    b'{"x":' + b'[' * 1500 + b'0' + b']' * 1500 + b'}'):
            binding, _ = fixture(raw)
            result = bind_receipt(binding, raw, now=NOW)
            self.assertEqual(result['outcome'], 'malformed')
            self.assertIsNone(result['record'])

    def test_changed_input_invalidates_previous_key_instead_of_noop(self):
        binding, raw = fixture()
        old = bind_receipt(binding, raw, now=NOW)
        changed = raw.replace(b'1,300 ml', b'130 ml')
        result = bind_receipt(binding, changed, now=NOW, previous_key=old['buildKey'])
        self.assertEqual(result['outcome'], 'malformed')
        self.assertIn('binding-metadata-pin-mismatch', result['diagnostics'])

    def test_deterministic_noop_still_validates_current_input(self):
        binding, raw = fixture()
        first = bind_receipt(binding, raw, now=NOW)
        self.assertEqual(canonical(first), canonical(bind_receipt(binding, raw, now=NOW)))
        second = bind_receipt(binding, raw, now=NOW, previous_key=first['buildKey'])
        self.assertEqual(second['outcome'], 'noop')
        self.assertEqual(second['record'], first['record'])
        self.assertEqual(second['metadataStage'], first['metadataStage'])

    def test_stale_original_is_not_refreshed_by_recent_validation(self):
        binding, raw = fixture()
        result = bind_receipt(binding, raw, now='2026-10-31T00:00:00Z')
        self.assertEqual(result['outcome'], 'stale')
        self.assertEqual(result['cache']['acquisitionAgeSeconds'], MINIMUM_REUSE_SECONDS)
        self.assertLess(result['cache']['validationAgeSeconds'], MINIMUM_REUSE_SECONDS)
        self.assertFalse(result['cache']['validationResetsAcquisitionAge'])
        self.assertEqual(result['cache']['networkRequests'], 0)

    def test_unqualified_timestamp_never_establishes_freshness(self):
        binding, raw = fixture(); binding = replace(binding, acquisition_epoch_qualified=False)
        result = bind_receipt(binding, raw, now=NOW)
        self.assertEqual(result['outcome'], 'stale')
        self.assertEqual(result['cache']['decision'], 'acquisition-epoch-review-required')

    def test_missing_or_invalid_coordinate_never_invents_value(self):
        binding, raw = fixture()
        for pointer in ('/absent', '/x~2y', 'nativeUnits', '/array/01'):
            result = bind_receipt(replace(binding, selectors={**binding.selectors,
                'nativeUnits': pointer}), raw, now=NOW)
            self.assertEqual(result['outcome'], 'malformed')
            self.assertIsNone(result['record'])

    def test_bad_clocks_never_create_cache_freshness(self):
        binding, raw = fixture()
        for now in ('2026-09-30T00:00:00Z', '2026-10-18', '2026-10-18T00:00:00+01:00'):
            self.assertEqual(bind_receipt(binding, raw, now=now)['outcome'], 'malformed')
        obj = json.loads(raw);obj['lastValidatedAt'] = '2026-09-01T00:00:00Z'
        binding, raw = fixture(canonical(obj))
        self.assertEqual(bind_receipt(binding, raw, now=NOW)['outcome'], 'malformed')

    def test_metadata_size_and_symlinks_fail_closed(self):
        binding, raw = fixture(b' ' * (MAX_METADATA_BYTES + 1))
        self.assertEqual(bind_receipt(binding, raw, now=NOW)['outcome'], 'malformed')
        with TemporaryDirectory() as td:
            p = Path(td) / 'receipt.json';p.symlink_to(FIXTURE.resolve())
            with self.assertRaisesRegex(RefreshError, 'symlink-path-rejected'):
                read_retained_metadata(replace(binding, retained_metadata_path=str(p)))
            p.unlink();p = Path(td) / 'body.pdf'
            with self.assertRaisesRegex(RefreshError, 'binding-metadata-json-required'):
                read_retained_metadata(replace(binding, retained_metadata_path=str(p)))

    def test_peer_failures_do_not_hide_valid_metadata(self):
        binding, raw = fixture()
        entries = [replace(binding, source_id=str(i)) for i in range(3)]
        def provider(b):
            if b.source_id == '0': raise PermissionError('not included in diagnostics')
            return None if b.source_id == '1' else raw
        report = run_portfolio(entries, provider, now=NOW)
        self.assertEqual([x['outcome'] for x in report['bindings']], ['missing', 'missing', 'valid'])
        self.assertNotIn('not included', canonical(report).decode())
        self.assertFalse(report['countryCoverageComplete'])
        self.assertEqual(len(report['countryTypes']), 24)
        self.assertTrue(all(not cell['accepted'] for cell in report['countryTypes']))
        self.assertEqual(report['realSourceCapability'], 'unsupported-unselected')

    def test_cli_replay_and_bad_previous_metadata_are_typed(self):
        from contextlib import redirect_stdout, redirect_stderr
        from offmenu.portfolio39.__main__ import main as cli
        binding, raw = fixture()
        with TemporaryDirectory() as td, patch('offmenu.portfolio39.__main__.bindings', return_value=(binding,)), \
             patch('offmenu.portfolio39.__main__.read_retained_metadata', return_value=raw):
            output = Path(td)/'first.json'
            self.assertEqual(cli(['--now', NOW, '--output', str(output)]), 0)
            second = io.StringIO()
            with redirect_stdout(second):
                self.assertEqual(cli(['--now', NOW, '--previous', str(output)]), 0)
            self.assertEqual(json.loads(second.getvalue())['bindings'][0]['outcome'], 'noop')
            original = output.read_bytes()
            with redirect_stdout(io.StringIO()):
                self.assertEqual(cli(['--now', NOW, '--output', str(output)]), 2)
            self.assertEqual(output.read_bytes(), original)
            bad = Path(td)/'bad.json';bad.write_bytes(b'{"bindings":"secret-invalid"}')
            stream = io.StringIO()
            with redirect_stdout(stream):
                self.assertEqual(cli(['--now', NOW, '--previous', str(bad)]), 2)
            self.assertNotIn('secret-invalid', stream.getvalue())
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as stopped:
                cli(['--now', NOW, '--force-download'])
            self.assertEqual(stopped.exception.code, 2)

    def test_no_body_or_socket_calls_in_pure_binding(self):
        binding, raw = fixture()
        with patch('builtins.open', side_effect=AssertionError('file read')),\
             patch('socket.create_connection', side_effect=AssertionError('network')):
            result = bind_receipt(binding, raw, now=NOW)
        self.assertEqual(result['outcome'], 'valid')
        self.assertNotIn('unusedRawPath', result['record']['data'])

    def test_shared_acquirer_automatic_refresh_reuses_fixture_under_30days(self):
        # Shared cache implementation, authored bytes, fake transport; zero sockets.
        from datetime import datetime, timezone, timedelta
        class Response:
            status = 200
            headers = {}
            def __init__(self): self.body = io.BytesIO(b'AUTHORED FIXTURE ONLY')
            def read(self, size): return self.body.read(size)
            def close(self): pass
        calls = []
        def transport(spec, headers): calls.append(1);return Response()
        spec = SourceSpec('fixture39', 'https://example.invalid/authored', 'a'*64,
                          'authored-fixture-only', enabled=True, rights_approved=True,
                          max_bytes=1024, release='authored-v1')
        now = datetime(2026, 10, 1, tzinfo=timezone.utc)
        with TemporaryDirectory() as td:
            cache = CachedAcquirer(td, {spec.source_key: spec}, transport=transport)
            first = cache.acquire(spec.source_key, fetch_policy='refresh', now=now)
            second = cache.acquire(spec.source_key, fetch_policy='refresh', now=now+timedelta(days=29))
        self.assertEqual(len(calls), 1)
        self.assertEqual(second.status, 'reused-fresh')
        self.assertEqual(first.provenance['originalAcquiredAt'], second.provenance['originalAcquiredAt'])

    def test_shared_qualification_accepts_authored_metadata_scope_only(self):
        from offmenu.refresh.acceptance import Asset, SourceContract, qualify, fingerprint, ids_digest
        from offmenu.refresh.serialization import encode_records
        binding, raw = fixture()
        row = bind_receipt(binding, raw, now=NOW)['record']
        # Independently declared authored-fixture schema and expected identity.
        props = {'originalAcquiredAt': {'const': '2026-10-01T00:00:00Z'},
                 'lastValidatedAt': {'const': '2026-10-17T00:00:00Z'},
                 'nativeUnits': {'type': 'null'}, 'nativeBasis': {'type': 'null'},
                 'originalBytes': {'type': 'integer', 'const': 0},
                 'zero': {'type': 'integer', 'const': 0}, 'false': {'type': 'boolean', 'const': False},
                 'lexical': {'type': 'string', 'const': '1,300 ml'}}
        schemas = {'source-input-binding': {'type': 'object',
            'required': ['id', 'kind', 'schemaVersion', 'data', 'provenance'],
            'properties': {'id': {'type': 'string'}, 'kind': {'const': 'source-input-binding'},
                'schemaVersion': {'const': 'offmenu-portfolio39-binding/1'},
                'data': {'type': 'object', 'required': list(props), 'properties': props,
                         'additionalProperties': False}, 'provenance': {'type': 'object'}},
            'additionalProperties': False}}
        with TemporaryDirectory() as td:
            root = Path(td);bundle = root/'bundle';bundle.mkdir()
            (bundle/'metadata').mkdir()
            assets = []
            for name, content in [('metadata/fixture.json', raw),
                                  ('rights.json', b'{"scope":"AUTHORED FIXTURE ONLY"}\n'),
                                  ('scope.json', b'{"count":1,"scope":"metadata only"}\n')]:
                (bundle/name).write_bytes(content)
                assets.append(Asset(name, len(content), sha(content)))
            expected_id = 'authored-fixture39:metadata:' + sha(raw)
            contract = SourceContract(binding.source_id, binding.release_id,
                'authored-metadata-only', '2026-10-01T00:00:00Z', tuple(assets), 1,
                ids_digest([expected_id]), schemas, fingerprint(schemas),
                lambda record: field_origin_errors(record, {'metadata/fixture.json': sha(raw)}),
                'a'*64, assets[1], assets[2], frozenset(('retain', 'parse', 'transform')),
                fixture=True, max_input_bytes=32768, max_output_bytes=32768, max_records=1)
            payload = encode_records([row]);candidate=root/'candidate.jsonl';candidate.write_bytes(payload)
            manifest = {'sourceId': binding.source_id, 'releaseId': binding.release_id,
                'acquiredAt': contract.acquired_at, 'normalizedRecords': 1,
                'rightsEvidenceSha256': assets[1].sha256, 'scopeEvidenceSha256': assets[2].sha256,
                'inputFiles': [vars(x) for x in assets], 'candidateSha256': sha(payload),
                'candidateBytes': len(payload)}
            result = qualify(contract, bundle, candidate, manifest)
            self.assertEqual(result['errors'], [])
            self.assertTrue(result['qualified'])
            self.assertTrue(result['fixture'])
            self.assertEqual(result['scopeId'], 'authored-metadata-only')
            # Neither a caller flag nor valid bytes can remove an explicit trusted hold.
            held = qualify(replace(contract, holds=('source-use-not-qualified',)),
                           bundle, candidate, manifest)
            self.assertFalse(held['qualified'])
            self.assertIn('source-held', held['errors'])


if __name__ == '__main__':
    main()
