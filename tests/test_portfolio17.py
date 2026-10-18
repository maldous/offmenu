"""Authored metadata-only fixtures; no publisher data or source grants."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh.core import RefreshError, canonical, sha, timestamp
from offmenu.refresh.portfolio17 import _read_binding_config, evaluate, pointer

NOW = timestamp('2026-10-18T00:00:00Z')


def fixture(root):
    metadata = {'release': '2024-v01', 'acquired': '2026-10-01T00:00:00Z',
                'validation': '2026-10-18T00:00:00Z',
                'retention': 'AUTHORED FIXTURE metadata only, not a source grant',
                'fields': {'null': None, 'zero': '0', 'trace': '< 0.1',
                           'unit': 'source-unit:unknown', 'basis': None,
                           'bodyPath': '/not-opened/original.pdf'}}
    raw = canonical(metadata)
    (root / 'receipt.json').write_bytes(raw)
    entry = {'bindingId': 'fixture-nz', 'country': 'NZ', 'type': 'nutrition',
             'sourceId': 'foodfiles', 'releaseId': '2024-v01',
             'adapterSourceId': 'foodfiles', 'holds': [],
             'evidence': {'receipt': {'path': 'receipt.json', 'sha256': sha(raw),
                                      'metadataOnly': True}},
             'fields': {'release': {'evidence': 'receipt', 'selector': '/release'},
                        'literal': {'evidence': 'receipt', 'selector': '/fields'},
                        'unresolved': {'unknown': True}},
             'originalAcquisition': {'evidence': 'receipt', 'selector': '/acquired'},
             'retentionEvidence': {'evidence': 'receipt', 'selector': '/retention'}}
    return {'schemaVersion': 'offmenu-portfolio17-bindings/1', 'bindings': [entry]}


class Portfolio17Tests(unittest.TestCase):
    def test_cli_bindings_reject_nonregular_and_preserve_previous_output(self):
        for kind in ('fifo', 'directory'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); metadata = root / 'permitted'; metadata.mkdir()
                source = root / 'bindings.json'
                if kind == 'fifo':
                    os.mkfifo(source)
                else:
                    source.mkdir()
                output = root / 'result.json'; previous = b'authored prior output\n'
                output.write_bytes(previous)
                command = [sys.executable, '-B', '-m', 'offmenu.refresh.portfolio17',
                           '--bindings', str(source), '--metadata-root', str(metadata),
                           '--now', '2026-10-18T00:00:00Z', '--output', str(output)]
                result = subprocess.run(command, capture_output=True, text=True, timeout=2)
                self.assertNotEqual(0, result.returncode)
                self.assertIn('binding-config-not-regular', result.stderr)
                self.assertEqual(previous, output.read_bytes())

    def test_bindings_regular_reader_bounds_open_race_and_read_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / 'bindings.json'; raw = b'{"x":0}'
            source.write_bytes(raw)
            self.assertEqual(raw, _read_binding_config(source))
            with patch('offmenu.refresh.portfolio17.MAX_METADATA', 4):
                with self.assertRaisesRegex(RefreshError, '^binding-config-too-large$'):
                    _read_binding_config(source)
            real_read = os.read
            def changed_read(descriptor, count):
                chunk = real_read(descriptor, count)
                if chunk:
                    source.write_bytes(b'{"x":11}')
                return chunk
            with patch('offmenu.refresh.portfolio17.os.read', side_effect=changed_read):
                with self.assertRaisesRegex(RefreshError, '^binding-config-changed-during-read$'):
                    _read_binding_config(source)
            source.write_bytes(raw)
            real_open = os.open
            def swap_before_open(path, flags):
                self.assertTrue(flags & os.O_NONBLOCK)
                self.assertTrue(flags & os.O_NOFOLLOW)
                source.rename(root / 'retained.json')
                os.mkfifo(source)
                return real_open(path, flags)
            with patch('offmenu.refresh.portfolio17.os.open', side_effect=swap_before_open):
                with patch('offmenu.refresh.portfolio17.os.read', side_effect=AssertionError('nonregular read')):
                    with self.assertRaisesRegex(RefreshError, '^binding-config-not-regular$'):
                        _read_binding_config(source)
            self.assertEqual(raw, (root / 'retained.json').read_bytes())

    def test_nested_metadata_is_bounded_and_valid_peer_survives(self):
        for depth in (80, sys.getrecursionlimit() + 100):
            with self.subTest(depth=depth), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); config = fixture(root)
                raw = b'{"x":' * depth + b'0' + b'}' * depth
                (root / 'deep.json').write_bytes(raw)
                nested = copy.deepcopy(config['bindings'][0])
                nested['bindingId'] = 'deep-first'
                nested['evidence']['receipt'] = {
                    'path': 'deep.json', 'sha256': sha(raw), 'metadataOnly': True}
                nested['fields'] = {'nested': {'evidence': 'receipt', 'selector': '/x'}}
                config['bindings'].insert(0, nested)
                result = evaluate(config, root, now=NOW)
                self.assertEqual(['malformed', 'valid-metadata-binding'],
                                 [x['status'] for x in result['bindings']])
                self.assertEqual(['metadata-depth-exceeded'], result['bindings'][0]['diagnostics'])
                self.assertNotIn('candidate', result['bindings'][0])
                self.assertEqual(0, result['sourceBodyOperations'])

    def test_cli_rejects_output_hardlinks_to_metadata_and_config(self):
        for target in ('receipt', 'config'):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); metadata = root / 'permitted'; metadata.mkdir()
                config = fixture(metadata)
                source = root / 'bindings.json'; source.write_bytes(canonical(config))
                receipt = metadata / 'receipt.json'
                before = {p: p.read_bytes() for p in (source, receipt)}
                output = root / 'result.json'
                os.link(receipt if target == 'receipt' else source, output)
                command = [sys.executable, '-B', '-m', 'offmenu.refresh.portfolio17',
                           '--bindings', str(source), '--metadata-root', str(metadata),
                           '--now', '2026-10-18T00:00:00Z', '--output', str(output)]
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(before, {p: p.read_bytes() for p in before})
                self.assertNotEqual(0, result.returncode)
                self.assertIn('output-hardlink-not-allowed', result.stderr)

    def test_valid_literal_lineage_shared_adapter_and_no_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); config = fixture(root)
            with patch('socket.socket', side_effect=AssertionError('network forbidden')):
                result = evaluate(config, root, now=NOW)
            row = result['bindings'][0]
            self.assertEqual('valid-metadata-binding', row['status'])
            self.assertEqual('foodfiles', row['sharedAdapter']['sourceId'])
            self.assertEqual('reuse-retained-metadata-no-download', row['cache']['decision'])
            self.assertEqual(17, row['cache']['acquisitionAgeDays'])
            self.assertFalse(result['sourceStageEligible'])
            self.assertFalse(row['candidate']['datasetAcceptance'])
            literal = row['candidate']['row']['data']['literal']
            self.assertEqual((None, '0', '< 0.1'), (literal['null'], literal['zero'], literal['trace']))
            origins = row['candidate']['row']['provenance']['fieldOrigins']
            self.assertEqual('/fields/zero', origins['/data/literal/zero']['sourceField'])
            self.assertEqual('constant', origins['/data/unresolved']['kind'])
            self.assertEqual(config, fixture(root))

    def test_missing_held_malformed_and_peer_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); config = fixture(root); base = config['bindings'][0]
            missing = copy.deepcopy(base); missing['bindingId'] = 'missing'
            missing['evidence']['receipt']['path'] = 'absent.json'
            held = copy.deepcopy(base); held['bindingId'] = 'held'; held['holds'] = ['private-extraction-held']
            malformed = copy.deepcopy(base); malformed['bindingId'] = 'bad'
            malformed['evidence']['receipt']['sha256'] = '0' * 64
            config['bindings'] += [missing, held, malformed]
            result = evaluate(config, root, now=NOW)
            self.assertEqual(['valid-metadata-binding', 'missing', 'held', 'malformed'],
                             [x['status'] for x in result['bindings']])
            self.assertEqual(['metadata-pin-mismatch'], result['bindings'][3]['diagnostics'])
            self.assertFalse(result['bindings'][2]['candidate']['sourceProcessingAuthorized'])

    def test_stale_acquisition_ignores_recent_validation_and_stable_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); config = fixture(root)
            first = evaluate(config, root, now=NOW)['bindings'][0]
            later = evaluate(config, root, now=timestamp('2026-11-01T00:00:00Z'))['bindings'][0]
            self.assertEqual('stale', later['status'])
            self.assertEqual('stale-input-review-required-no-download', later['cache']['decision'])
            self.assertEqual(31, later['cache']['acquisitionAgeDays'])
            self.assertEqual(first['candidateSha256'], later['candidateSha256'])
            self.assertFalse(later['cache']['validationResetsAcquisition'])

    def test_metadata_only_paths_no_symlinks_and_literal_pointers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); config = fixture(root)
            for name in ['../receipt.json', 'body.pdf', 'x/../receipt.json', '/receipt.json']:
                bad = copy.deepcopy(config); bad['bindings'][0]['evidence']['receipt']['path'] = name
                self.assertEqual(['metadata-only-json-required'], evaluate(bad, root, now=NOW)['bindings'][0]['diagnostics'])
            (root / 'link.json').symlink_to(root / 'receipt.json')
            config['bindings'][0]['evidence']['receipt']['path'] = 'link.json'
            self.assertEqual('malformed', evaluate(config, root, now=NOW)['bindings'][0]['status'])
        self.assertEqual(2, pointer({'a/b': {'~x': [1, 2]}}, '/a~1b/~0x/1'))

    def test_bad_json_missing_selector_future_and_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); config = fixture(root)
            config['bindings'][0]['fields']['release']['selector'] = '/absent'
            self.assertEqual('missing', evaluate(config, root, now=NOW)['bindings'][0]['status'])
            config = fixture(root)
            self.assertEqual(['acquisition-timestamp-in-future'], evaluate(config, root, now=timestamp('2026-09-01T00:00:00Z'))['bindings'][0]['diagnostics'])
            raw = b'{"x":1,"x":2}'
            (root / 'receipt.json').write_bytes(raw)
            config['bindings'][0]['evidence']['receipt']['sha256'] = sha(raw)
            self.assertEqual(['duplicate-json-key'], evaluate(config, root, now=NOW)['bindings'][0]['diagnostics'])
            with patch('offmenu.refresh.portfolio17.MAX_METADATA', 1):
                self.assertEqual(['metadata-budget-exceeded'], evaluate(config, root, now=NOW)['bindings'][0]['diagnostics'])

    def test_cli_repeat_is_noop_and_never_opens_body_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); metadata = root / 'permitted'; metadata.mkdir()
            config = fixture(metadata)
            path = root / 'bindings.json'; path.write_text(json.dumps(config))
            output = root / 'out/result.json'
            command = [sys.executable, '-B', '-m', 'offmenu.refresh.portfolio17',
                       '--bindings', str(path), '--metadata-root', str(metadata),
                       '--now', '2026-10-18T00:00:00Z', '--output', str(output)]
            first = json.loads(subprocess.check_output(command))
            before = output.stat().st_mtime_ns
            second = json.loads(subprocess.check_output(command))
            self.assertFalse(first['unchanged']); self.assertTrue(second['unchanged'])
            self.assertEqual(before, output.stat().st_mtime_ns)
            self.assertEqual(first['outputSha256'], second['outputSha256'])

    def test_body_values_never_dereferenced_and_bad_pointer_isolated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); config = fixture(root)
            original = Path.read_bytes
            def permitted(path):
                if path.suffix != '.json':
                    raise AssertionError('body opened')
                return original(path)
            with patch.object(Path, 'read_bytes', permitted):
                self.assertEqual('valid-metadata-binding', evaluate(config, root, now=NOW)['bindings'][0]['status'])
            config['bindings'][0]['fields']['release']['selector'] = '/bad~2escape'
            self.assertEqual(['selector-invalid'], evaluate(config, root, now=NOW)['bindings'][0]['diagnostics'])

    def test_named_adapter_cannot_relabel_an_unrelated_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); config = fixture(root)
            config['bindings'][0]['sourceId'] = 'unrelated-publisher'
            result = evaluate(config, root, now=NOW)['bindings'][0]
            self.assertIsNone(result['sharedAdapter'])
            self.assertIn('shared-payload-adapter-unbound', result['diagnostics'])


if __name__ == '__main__':
    unittest.main()
