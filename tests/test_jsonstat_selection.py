import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'src/offmenu/jsonstat_selection.py'
spec = importlib.util.spec_from_file_location('selection', MODULE)
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)


class SelectionTests(unittest.TestCase):
    def setUp(self):
        # Reversed insertion order tests position order, not dict order.
        self.doc = {'class': 'dataset', 'version': '2.0', 'id': ['category', 'time'],
                    'size': [2, 3], 'dimension': {
                        'category': {'category': {'index': {'B': 1, 'A': 0}, 'label': {'A': 'Alpha', 'B': 'Beta'}}},
                        'time': {'category': {'index': ['t0', 't1', 't2'], 'label': {'t0': 'Zero', 't1': 'One', 't2': 'Two'}}}},
                    'value': {'3': 0, '4': None}, 'status': {'4': 'e'}}
        self.provenance = {k: 'test' for k in ['publisher', 'dataset', 'sourceURL',
            'originalCaptureUTC', 'modificationNotice', 'disclaimer', 'rightsEvidence', 'scopeEvidence']}
        self.selectors = {'category': ['B'], 'time': None}

    def selected(self, document=None, **kwargs):
        return s.select(json.dumps(document or self.doc).encode(), self.selectors, self.provenance, **kwargs)

    def test_numeric_zero_null_absent_and_status(self):
        rows, manifest = self.selected()
        self.assertEqual([r['flatIndex'] for r in rows], [3, 4, 5])
        self.assertEqual([r['valueState'] for r in rows], ['numeric', 'explicit-null', 'absent'])
        self.assertEqual(rows[0]['value'], 0)
        self.assertTrue(rows[1]['valueOrigin']['present'])
        self.assertFalse(rows[2]['valueOrigin']['present'])
        self.assertEqual(rows[1]['statusOrigin'], {'pointer': '/status/4', 'present': True})
        self.assertEqual(rows[0]['coordinates']['category']['label'], 'Beta')
        self.assertEqual(manifest['counts'], {'numeric': 1, 'explicit-null': 1, 'absent': 1,
                                             'coordinates': 3, 'statusPresent': 1})

    def test_dense_and_constant_status(self):
        d = copy.deepcopy(self.doc); d['value'] = [9, 8, 7, -2.5, None]; d['status'] = 'e'
        rows, _ = self.selected(d)
        self.assertEqual(rows[0]['value'], -2.5)
        self.assertEqual(rows[0]['statusOrigin']['pointer'], '/status')
        self.assertEqual(rows[2]['valueState'], 'absent')

    def test_number_lexical_preserved(self):
        payload = json.dumps(self.doc).replace('"3": 0', '"3": 1.2300e-2').encode()
        rows, _ = s.select(payload, self.selectors, self.provenance)
        self.assertEqual(rows[0]['valueLexical'], '1.2300e-2')
        self.assertEqual(rows[0]['value'], 0.0123)

    def test_source_position_order_and_escaped_pointer(self):
        d = copy.deepcopy(self.doc);d['dimension']['category']['category']['index'] = {'B': 0, 'A': 1}
        rows, _ = self.selected(d)
        self.assertEqual([r['flatIndex'] for r in rows], [0, 1, 2])
        self.assertEqual(s.escape('a~/b'), 'a~0~1b')

    def test_fail_closed_selection_and_bad_values(self):
        with self.assertRaisesRegex(s.SelectionError, 'coordinate-limit'):
            self.selected(max_coordinates=2)
        for value in [True, '12', float('inf')]:
            d = copy.deepcopy(self.doc);d['value']['3'] = value
            with self.subTest(value=value), self.assertRaises(s.SelectionError):
                self.selected(d)
        self.selectors['category'] = ['unknown']
        with self.assertRaisesRegex(s.SelectionError, 'selector-code-absent'):
            self.selected()

    def test_duplicate_json_and_index_rejected(self):
        with self.assertRaisesRegex(s.SelectionError, 'duplicate-json-key'):
            s.decode(b'{"value":1,"value":2}')
        self.doc['dimension']['category']['category']['index']['B'] = 0
        with self.assertRaisesRegex(s.SelectionError, 'category-index'):
            self.selected()

    def test_materialization_noop_replay_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);source = root / 'input.json';source.write_bytes(json.dumps(self.doc).encode())
            sha = hashlib.sha256(source.read_bytes()).hexdigest()
            def run(output):
                return s.materialize(source, sha, source.stat().st_size, self.selectors, self.provenance, output)
            output = root / 'out';self.assertEqual(run(output)['writes'], 2)
            before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in output.iterdir()}
            self.assertEqual(run(output)['writes'], 0)
            self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in output.iterdir()})
            replay = root / 'replay';run(replay)
            self.assertEqual({p.name: p.read_bytes() for p in replay.iterdir()}, {k: v[0] for k, v in before.items()})
            (output / 'manifest.json').write_text('{}')
            with self.assertRaisesRegex(s.SelectionError, 'existing-output-conflict'):
                run(output)
            with self.assertRaisesRegex(s.SelectionError, 'source-pin-mismatch'):
                s.materialize(source, '0' * 64, source.stat().st_size, self.selectors, self.provenance, root / 'bad')
            self.assertFalse((root / 'bad').exists())


if __name__ == '__main__':
    unittest.main()
