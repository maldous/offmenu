"""Authored metadata fixtures only; never open retained source bodies."""
import copy
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.portfolio50.bindings import (
    Binding, POLICY, assess_many, inspect, read_receipt, stage_interface)
from offmenu.portfolio50.profiles import bindings
from offmenu.refresh.core import RefreshError, canonical, sha
from offmenu.refresh.field_provenance import field_origin_errors
from offmenu.refresh.acceptance import Asset, SourceContract, fingerprint, ids_digest, qualify

NOW = '2026-10-18T00:00:00Z'


def fixture(country='MV', acquired='2026-10-01T00:00:00Z'):
    value = {'country': country, 'release': 'authored-fixture-v1',
             'acquiredAt': acquired, 'originalBytes': 12,
             'originalSHA256': 'a' * 64, 'nativeUnit': 'authored-index',
             'nativeBasis': 'authored-base=100', 'selector': 'authored!A1:B2'}
    raw = canonical(value)
    fields = tuple((name, '/' + name) for name in value)
    return Binding(country, 'authored-owner50', value['release'], 'receipt.json',
                   sha(raw), fields, (), (), fixture=True), raw


class Portfolio50BindingTests(unittest.TestCase):
    def test_fifo_receipt_does_not_block_valid_peer_cli(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fifo = root / 'first' / 'receipt.json'
            fifo.parent.mkdir()
            os.mkfifo(fifo)
            peer = root / 'second' / 'receipt.json'
            peer.parent.mkdir()
            _, raw = fixture(country='PR')
            peer.write_bytes(raw)
            script = '''
import sys
from dataclasses import replace
from unittest.mock import patch
sys.path.insert(0, 'tests')
from test_portfolio50_bindings import fixture
from offmenu.portfolio50.bindings import main
first, _ = fixture()
second, _ = fixture(country='PR')
with patch('offmenu.portfolio50.profiles.bindings', return_value=(
        replace(first, receipt_path=sys.argv[1]),
        replace(second, receipt_path=sys.argv[2]))):
    raise SystemExit(main(['--now', '2026-10-18T00:00:00Z']))
'''
            result = subprocess.run([sys.executable, '-B', '-c', script, str(fifo), str(peer)],
                                    capture_output=True, text=True, timeout=3)
            self.assertEqual(result.returncode, 2, result.stderr)
            reports = json.loads(result.stdout)['bindings']
            self.assertEqual([r['status'] for r in reports], ['missing-input', 'metadata-ready'])
            self.assertEqual(reports[0]['diagnostics'], ['receipt-unavailable-or-unsafe'])
            self.assertEqual(reports[1]['diagnostics'], [])

    def test_module_cli_uses_canonical_binding_type_with_authored_input(self):
        # Exercise the real -m/runpy boundary, without reading actual receipts.
        script = '''
import runpy, sys, tempfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, 'tests')
from test_portfolio50_bindings import fixture
binding, raw = fixture()
sys.argv = ['bindings', '--now', '2026-10-18T00:00:00Z']
with tempfile.TemporaryDirectory() as td:
    receipt = Path(td) / 'receipt.json'
    receipt.write_bytes(raw)
    binding = replace(binding, receipt_path=str(receipt))
    with patch('offmenu.portfolio50.profiles.bindings', return_value=(binding,)):
        runpy.run_module('offmenu.portfolio50.bindings', run_name='__main__')
'''
        r = subprocess.run([sys.executable, '-B', '-c', script],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertEqual(json.loads(r.stdout)['bindings'][0]['status'], 'metadata-ready')

    def test_valid_metadata_and_complete_shared_field_origins(self):
        binding, raw = fixture()
        r = inspect(binding, raw, now=NOW)
        self.assertEqual(r['status'], 'metadata-ready')
        self.assertEqual(r['diagnostics'], [])
        self.assertEqual(field_origin_errors(r['record'], {'receipt.json': sha(raw)},
                                            policy_pins=(POLICY,)), [])
        self.assertFalse(r['stagingAccepted'])
        self.assertFalse(r['countryComplete'])

    def test_missing_receipt_is_typed(self):
        binding, _ = fixture()
        r = inspect(binding, None, now=NOW)
        self.assertEqual(r['status'], 'missing-input')
        self.assertEqual(r['diagnostics'], ['receipt-missing'])

    def test_hold_cannot_be_overridden_by_receipt_claim(self):
        binding, raw = fixture()
        binding = replace(binding, holds=('source-use-not-qualified',))
        r = inspect(binding, raw, now=NOW)
        self.assertEqual(r['status'], 'held')
        self.assertIn('source-use-not-qualified', r['diagnostics'])
        self.assertEqual(r['replay'], 'blocked')

    def test_stale_original_not_reset_by_new_validation(self):
        binding, raw = fixture(acquired='2026-09-01T00:00:00Z')
        r = inspect(binding, raw, now=NOW, validated_at=NOW)
        self.assertEqual(r['status'], 'stale-input')
        self.assertEqual(r['acquisitionAgeDays'], 47)
        self.assertEqual(r['validationAgeDays'], 0)
        self.assertFalse(r['cache']['revalidationResetsAcquisitionAge'])
        self.assertEqual(r['networkRequests'], 0)

    def test_exact_thirty_day_boundary(self):
        binding, raw = fixture(acquired='2026-09-18T00:00:00Z')
        self.assertEqual(inspect(binding, raw, now=NOW)['status'], 'stale-input')

    def test_replay_key_ignores_validation_clock_and_noop(self):
        binding, raw = fixture()
        first = inspect(binding, raw, now=NOW)
        second = inspect(binding, raw, now='2026-10-19T00:00:00Z',
                         previous_key=first['bindingKey'])
        self.assertEqual(first['bindingKey'], second['bindingKey'])
        self.assertEqual(second['replay'], 'unchanged-no-op')
        self.assertEqual(second['originalAcquiredAt'], '2026-10-01T00:00:00Z')

    def test_changed_receipt_pin_changes_key(self):
        binding, raw = fixture()
        original = inspect(binding, raw, now=NOW)
        value = copy.deepcopy(original['record']['data'])
        value['nativeBasis'] = 'authored-other-base'
        changed = canonical(value)
        binding = replace(binding, receipt_sha256=sha(changed))
        r = inspect(binding, changed, now=NOW, previous_key=original['bindingKey'])
        self.assertNotEqual(r['bindingKey'], original['bindingKey'])
        self.assertEqual(r['replay'], 'metadata-projection-ready')

    def test_pin_mismatch_malformed_and_no_values_echoed(self):
        binding, _ = fixture()
        r = inspect(binding, b'private-source-value', now=NOW)
        self.assertEqual(r['status'], 'malformed')
        self.assertIn('receipt-pin-mismatch', r['diagnostics'])
        self.assertNotIn('private-source-value', str(r))

    def test_duplicate_json_and_nonfinite_are_rejected(self):
        binding, _ = fixture()
        for raw in [b'{"country":"MV","country":"PR"}', b'{"value":NaN}']:
            with self.subTest(raw=raw):
                r = inspect(replace(binding, receipt_sha256=sha(raw)), raw, now=NOW)
                self.assertEqual(r['status'], 'malformed')

    def test_missing_coordinates_are_explicit_unknowns(self):
        binding, raw = fixture()
        fields = tuple((k, None if k in ('nativeUnit', 'nativeBasis') else p)
                       for k, p in binding.fields)
        r = inspect(replace(binding, fields=fields), raw, now=NOW)
        self.assertEqual(r['status'], 'missing-input')
        self.assertIsNone(r['record']['data']['nativeUnit'])
        self.assertIn('metadata-field-unresolved-nativebasis', r['diagnostics'])
        origin = r['record']['provenance']['fieldOrigins']['/data/nativeUnit']
        self.assertEqual(origin['kind'], 'constant')
        self.assertEqual(origin['symbol'], 'unresolved-not-imputed')

    def test_malformed_pin_dimensions_or_times(self):
        binding, raw = fixture()
        from offmenu.refresh.core import strict_json
        for field, bad in [('originalBytes', True), ('originalSHA256', 'bad'),
                           ('acquiredAt', 'not-a-time')]:
            value = strict_json(raw)
            value[field] = bad
            altered = canonical(value)
            with self.subTest(field=field):
                r = inspect(replace(binding, receipt_sha256=sha(altered)), altered, now=NOW)
                self.assertEqual(r['status'], 'malformed')

    def test_country_and_release_drift_fail_closed(self):
        binding, raw = fixture()
        for changed in [replace(binding, country='PR'), replace(binding, release_id='foreign')]:
            r = inspect(changed, raw, now=NOW)
            self.assertIn('source-release-or-country-mismatch', r['diagnostics'])
            self.assertNotEqual(r['status'], 'metadata-ready')

    def test_peer_diagnostics_are_isolated(self):
        one, raw1 = fixture()
        two, raw2 = fixture(country='PR')
        reports = assess_many([one, two], {'MV': b'malformed', 'PR': raw2}, now=NOW)
        self.assertEqual([r['status'] for r in reports], ['malformed', 'metadata-ready'])

    def test_no_network_or_adapter_execution(self):
        binding, raw = fixture()
        with patch('offmenu.refresh.acquisition.HTTPSFileTransport.__call__',
                   side_effect=AssertionError('network forbidden')):
            r = inspect(binding, raw, now=NOW)
        stage = stage_interface(r).receipt()
        self.assertEqual(stage['status'], 'unsupported')
        self.assertEqual(stage['observedCount'], None)
        self.assertEqual(stage['code'], 'portfolio-metadata-only')
        self.assertEqual(r['interfaces']['pureSharedCachePlanner'], 'unsupported')

    def test_receipt_loader_only_metadata_and_symlink_rejected(self):
        binding, raw = fixture()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            receipt = root / 'receipt.json'
            receipt.write_bytes(raw)
            self.assertEqual(read_receipt(replace(binding, receipt_path=str(receipt))), raw)
            missing = root / 'missing' / 'receipt.json'
            self.assertIsNone(read_receipt(replace(binding, receipt_path=str(missing))))
            link = root / 'alias'
            link.symlink_to(root, target_is_directory=True)
            with self.assertRaises(RefreshError):
                read_receipt(replace(binding, receipt_path=str(link / 'receipt.json')))

    def test_receipt_loader_rejects_directory_and_oversized_metadata(self):
        binding, _ = fixture()
        with tempfile.TemporaryDirectory() as td:
            receipt = Path(td) / 'receipt.json'
            bound = replace(binding, receipt_path=str(receipt))
            receipt.mkdir()
            with self.assertRaisesRegex(RefreshError, 'portfolio-receipt-not-regular'):
                read_receipt(bound)
            receipt.rmdir()
            receipt.write_bytes(b' ' * (1024 * 1024 + 1))
            with self.assertRaisesRegex(RefreshError, 'portfolio-metadata-limit'):
                read_receipt(bound)

    def test_all_real_profiles_are_held_not_fixture_or_admitted(self):
        portfolio = bindings()
        self.assertEqual([b.country for b in portfolio], ['MV', 'PR', 'SD', 'SM'])
        for b in portfolio:
            self.assertFalse(b.fixture)
            self.assertTrue(b.data_types)
            self.assertIn('source-body-operation-not-selected', b.holds)
            self.assertIn('source-use-not-qualified', b.holds)

    def test_shared_qualification_consumes_authored_metadata_fixture(self):
        # This trusted test contract is not built from a real source manifest.
        binding, raw = fixture()
        report = inspect(binding, raw, now=NOW)
        row = report['record']
        schema = {'type': 'object', 'required': ['id', 'kind', 'schemaVersion', 'data', 'provenance'],
                  'properties': {'kind': {'const': 'sourceInputMetadata'},
                                 'data': {'type': 'object', 'required': list(row['data']),
                                          'properties': {k: {'const': v} for k, v in row['data'].items()},
                                          'additionalProperties': False}}}
        schemas = {'sourceInputMetadata': schema}
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundle = root / 'bundle'
            bundle.mkdir()
            values = {'receipt.json': raw,
                      'rights.json': canonical({'scope': 'authored-test-only'}),
                      'scope.json': canonical({'count': 1, 'kind': 'authored-metadata'})}
            assets = []
            for name, data in values.items():
                (bundle / name).write_bytes(data)
                assets.append(Asset(name, len(data), sha(data)))
            candidate = root / 'candidate.jsonl'
            candidate.write_bytes(canonical([row]))
            contract = SourceContract(
                binding.source_id, binding.release_id, 'authored-metadata-only',
                row['provenance']['fetchedAt'], tuple(assets), 1, ids_digest([row['id']]),
                schemas, fingerprint(schemas),
                lambda r: field_origin_errors(r, {'receipt.json': sha(raw)}, policy_pins=(POLICY,)),
                POLICY, assets[1], assets[2], frozenset(('retain', 'parse', 'transform')),
                fixture=True, max_records=1, max_input_bytes=4096, max_output_bytes=16384)
            manifest = {'sourceId': contract.source_id, 'releaseId': contract.release_id,
                        'acquiredAt': contract.acquired_at, 'normalizedRecords': 1,
                        'rightsEvidenceSha256': assets[1].sha256, 'scopeEvidenceSha256': assets[2].sha256,
                        'inputFiles': [vars(a) for a in assets],
                        'candidateBytes': candidate.stat().st_size,
                        'candidateSha256': sha(candidate.read_bytes())}
            result = qualify(contract, bundle, candidate, manifest)
            self.assertTrue(result['qualified'], result['errors'])
            self.assertTrue(result['fixture'])
            self.assertEqual(result['normalizedRecords'], 1)


if __name__ == '__main__':
    unittest.main()
