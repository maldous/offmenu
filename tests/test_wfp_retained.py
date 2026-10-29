"""Prepared acceptance tests for the conditionally selected WFP adapter.

Authored records only. Run after the reviewed handler candidate exists on the
selected source branch: PYTHONPATH=<checkout> python3 -m unittest discover -s <this-dir>.
No real source path is used or dereferenced by these tests.
"""
from copy import deepcopy
import gzip
import importlib
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch


class WfpRetainedContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapter = importlib.import_module('offmenu.refresh.wfp_retained')
        from offmenu.refresh.core import canonical, sha, RefreshError
        from offmenu.refresh.field_provenance import field_origin_errors
        cls.canonical, cls.sha = staticmethod(canonical), staticmethod(sha)
        cls.RefreshError = RefreshError
        cls.field_origin_errors = staticmethod(field_origin_errors)
        cls.fixture = json.loads((Path(__file__).parent / 'wfp-retained-authored-fixtures.json').read_text())

    def context(self, raw=None):
        context = deepcopy(self.fixture['context'])
        raw = raw if raw is not None else self.canonical(self.fixture['records'][0])
        context['input'] = {'name': 'retained.jsonl', 'bytes': len(raw), 'sha256': self.sha(raw)}
        return context

    def test_native_lexemes_and_constant_unknowns_have_complete_origins(self):
        candidate = deepcopy(self.fixture['records'][0])
        context = self.context()
        with patch('builtins.open', side_effect=AssertionError('unexpected I/O')), \
                patch('socket.socket', side_effect=AssertionError('unexpected network')):
            row = self.adapter.normalize_record(candidate, context=context, input_line=1)
        self.assertEqual(row['data']['native'], candidate['values'])
        self.assertEqual(row['data']['native']['price'], '0.00')
        self.assertEqual(row['data']['native']['usdprice'], '')
        self.assertTrue(all(value is None for value in row['data']['unqualified'].values()))
        self.assertEqual(row['provenance']['originalRecord'], candidate['originalRecord'])
        self.assertEqual(row['provenance']['acquiredAt'], context['originalAcquiredAt'])
        self.assertEqual(self.field_origin_errors(row, {'retained.jsonl': context['input']['sha256']},
                         policy_pins=(self.adapter.POLICY_SHA256,)), [])
        for column in candidate['values']:
            origin = row['provenance']['fieldOrigins']['/data/native/' + column]
            self.assertEqual(origin['sourceField'], '/values/' + column)
            self.assertEqual(origin['sourceRecordId'], candidate['id'])

    def test_no_food_fx_or_currency_inference(self):
        candidate = deepcopy(self.fixture['records'][1])
        context = self.context(self.canonical(candidate))
        row = self.adapter.normalize_record(candidate, context=context, input_line=1)
        self.assertEqual(row['data']['native'], candidate['values'])
        self.assertEqual(row['data']['native']['unit'], 'USD/LCU')
        self.assertIsNone(row['data']['unqualified']['foodEligibility'])
        self.assertIsNone(row['data']['unqualified']['fxOrientation'])
        self.assertFalse(row['accepted'])

    def test_wrong_source_release_shape_identity_and_prior_prefix_rejected(self):
        candidate = self.fixture['records'][0]
        for field, replacement in [('country', 'CA'), ('sourceId', 'prices'),
                                   ('release', 'wrong-release'), ('admission', True)]:
            bad = deepcopy(candidate)
            bad[field] = replacement
            with self.subTest(field=field), self.assertRaises(self.RefreshError):
                self.adapter.normalize_record(bad, context=self.context(), input_line=1)
        for change in ('missing-column', 'numeric-price', 'source-hash', 'prior-line'):
            bad = deepcopy(candidate)
            if change == 'missing-column':
                del bad['values']['unit']
            elif change == 'numeric-price':
                bad['values']['price'] = 0
            elif change == 'source-hash':
                bad['originalRecord']['sourceSHA256'] = 'f' * 64
            else:
                bad['originalRecord']['csvLine'] = 2
                bad['id'] = 'wfp-lby:' + 'a' * 64 + ':line:2'
            with self.subTest(change=change), self.assertRaises(self.RefreshError):
                self.adapter.normalize_record(bad, context=self.context(), input_line=1)

    def test_authored_stream_is_deterministic_and_retains_original_age(self):
        raw = b''.join(self.canonical(row) for row in self.fixture['records'])
        context = self.context(raw)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'retained.jsonl'
            source.write_bytes(raw)
            outputs = []
            for name in ('first', 'second'):
                destination = root / name
                result = self.adapter.normalize_retained(source, destination, context=context, expected_records=2)
                outputs.append((destination / 'normalized.jsonl.gz').read_bytes())
                self.assertEqual(result['normalizedRecords'], 2)
                self.assertFalse(result['accepted'])
                self.assertEqual(result['originalAcquiredAt'], context['originalAcquiredAt'])
                packets = gzip.decompress(outputs[-1]).splitlines()
                self.assertEqual(len(packets), 2)
                self.assertEqual(json.loads(packets[0])[0]['data']['native']['price'], '0.00')
            self.assertEqual(outputs[0], outputs[1])

    def test_changed_input_count_duplicate_and_malformed_stream_leave_no_output(self):
        first, second = self.fixture['records']
        cases = {'wrong-count': self.canonical(first),
                 'duplicate': self.canonical(first) + self.canonical(first),
                 'malformed': self.canonical(first) + b'{bad}\n',
                 'duplicate-key': self.canonical(first) + b'{"id":1,"id":2}\n'}
        for name, raw in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = root / 'retained.jsonl'
                source.write_bytes(raw)
                destination = root / 'out'
                with self.assertRaises(self.RefreshError):
                    self.adapter.normalize_retained(source, destination, context=self.context(raw), expected_records=2)
                self.assertFalse(destination.exists())
        raw = self.canonical(first) + self.canonical(second)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'retained.jsonl'
            source.write_bytes(raw + b' ')
            with self.assertRaises(self.RefreshError):
                self.adapter.normalize_retained(source, root / 'out', context=self.context(raw), expected_records=2)
            self.assertFalse((root / 'out').exists())

    def test_fifo_symlink_and_output_collision_rejected(self):
        import os
        raw = self.canonical(self.fixture['records'][0])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'retained.jsonl'
            source.write_bytes(raw)
            link = root / 'link'
            link.symlink_to(source)
            fifo = root / 'fifo'
            os.mkfifo(fifo)
            for path in (link, fifo):
                script = '''
import json,sys
from offmenu.refresh.wfp_retained import normalize_retained
from offmenu.refresh.core import RefreshError
try:
    normalize_retained(sys.argv[1],sys.argv[2],context=json.loads(sys.argv[3]),expected_records=1)
except RefreshError:
    raise SystemExit(2)
'''
                with self.subTest(path=path.name):
                    result = subprocess.run([sys.executable, '-c', script, str(path), str(root / 'out'),
                                             json.dumps(self.context(raw))], timeout=2, capture_output=True)
                    self.assertEqual(result.returncode, 2)
                self.assertFalse((root / 'out').exists())
            destination = root / 'occupied'
            destination.mkdir()
            sentinel = destination / 'keep'
            sentinel.write_text('retained')
            with self.assertRaises(self.RefreshError):
                self.adapter.normalize_retained(source, destination, context=self.context(raw), expected_records=1)
            self.assertEqual(sentinel.read_text(), 'retained')

    def test_byte_line_and_output_caps_leave_no_completed_candidate(self):
        raw = self.canonical(self.fixture['records'][0])
        for limits in (self.adapter.WfpLimits(max_input_bytes=1),
                       self.adapter.WfpLimits(max_line_bytes=1),
                       self.adapter.WfpLimits(max_output_bytes=1)):
            with self.subTest(limits=limits), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = root / 'retained.jsonl'
                source.write_bytes(raw)
                with self.assertRaises(self.RefreshError):
                    self.adapter.normalize_retained(source, root / 'out', context=self.context(raw),
                                                    expected_records=1, limits=limits)
                self.assertFalse((root / 'out').exists())

    def test_exact_receipt_noop_checks_input_output_and_keeps_mtimes(self):
        raw = b''.join(self.canonical(row) for row in self.fixture['records'])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, destination = root / 'retained.jsonl', root / 'out'
            source.write_bytes(raw)
            context = self.context(raw)
            result = self.adapter.normalize_retained(source, destination, context=context, expected_records=2)
            before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in destination.iterdir()}
            reused = self.adapter.normalize_retained(source, destination, context=context, expected_records=2,
                previous_receipt_sha256=result['normalizationReceiptSha256'])
            self.assertTrue(reused['reused'])
            self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in destination.iterdir()})
            (destination / 'normalized.jsonl.gz').write_bytes(b'changed')
            with self.assertRaises(self.RefreshError):
                self.adapter.normalize_retained(source, destination, context=context, expected_records=2,
                    previous_receipt_sha256=result['normalizationReceiptSha256'])
            self.assertEqual((destination / 'normalized.jsonl.gz').read_bytes(), b'changed')

    def test_json_depth_and_partial_commit_stop_without_overwrite(self):
        candidate = deepcopy(self.fixture['records'][0])
        candidate['rights'] = {'nested': [[[[[[[[['too deep']]]]]]]]]}
        raw = self.canonical(candidate)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, destination = root / 'retained.jsonl', root / 'out'
            source.write_bytes(raw)
            with self.assertRaises(self.RefreshError):
                self.adapter.normalize_retained(source, destination, context=self.context(raw), expected_records=1,
                                               limits=self.adapter.WfpLimits(max_json_depth=5))
            self.assertFalse(destination.exists())
            candidate = self.fixture['records'][0]
            raw = self.canonical(candidate)
            source.write_bytes(raw)
            real_rename = self.adapter.os.rename
            def interrupted(old, new):
                if Path(old).name == 'manifest.json':
                    raise OSError('authored interruption before completion marker')
                return real_rename(old, new)
            with patch.object(self.adapter.os, 'rename', side_effect=interrupted), self.assertRaises(self.RefreshError):
                self.adapter.normalize_retained(source, destination, context=self.context(raw), expected_records=1)
            partial = (destination / 'normalized.jsonl.gz').read_bytes()
            self.assertFalse((destination / 'manifest.json').exists())
            with self.assertRaises(self.RefreshError):
                self.adapter.normalize_retained(source, destination, context=self.context(raw), expected_records=1)
            self.assertEqual((destination / 'normalized.jsonl.gz').read_bytes(), partial)


if __name__ == '__main__':
    unittest.main()
