"""Reviewer18 regressions: authored temporary files/bytes only."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import owner20_binding as binding
from offmenu.refresh.core import sha

NOW = '2026-10-18T06:00:00Z'
ROOT = Path(__file__).resolve().parents[1]
RAW = (ROOT / 'tests/fixtures/owner20-binding/authored-menu.json').read_bytes()
HELD = {'country': 'PH', 'state': 'held', 'requirements': [{'code': 'authored-hold'}]}


def profile(raw=RAW):
    return {'country': 'SB', 'state': 'derived-input-only',
            'sourceId': 'authored-source', 'releaseId': 'authored-release',
            'originalAcquiredAt': '2026-10-14T00:00:00Z',
            'metadataValidatedAt': '2026-10-17T00:00:00Z',
            'input': {'sha256': sha(raw)}, 'expectedItems': 2, 'expectedObservations': 2}


class Reviewer18Regressions(unittest.TestCase):
    def cli(self, root, path):
        source = profile()
        source['input']['path'] = str(path)
        config = root / 'authored-config.json'
        config.write_text(json.dumps({'bindings': [source, HELD]}))
        script = ('from pathlib import Path; import sys; '
                  'from offmenu.refresh import owner20_binding as m; '
                  'm.CONFIG=Path(sys.argv[1]); '
                  'sys.argv=["authored", "--now", "' + NOW + '", "--verify-retained-derived"]; '
                  'm.main()')
        run = subprocess.run([sys.executable, '-B', '-c', script, str(config)],
                             cwd=ROOT, capture_output=True, timeout=2)
        self.assertEqual(run.returncode, 0, run.stderr)
        return json.loads(run.stdout)['results']

    def test_fifo_and_directory_refused_without_losing_held_peer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fifo = root / 'input.fifo'
            os.mkfifo(fifo)
            for path in (fifo, root):
                with self.subTest(path=path.name):
                    result = self.cli(root, path)
                    self.assertEqual([r['status'] for r in result], ['malformed', 'held'])
                    self.assertEqual(result[0]['diagnostics'], ['derived-input-not-regular'])

    def test_symlink_unavailable_and_oversize_are_isolated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            regular = root / 'regular.json'
            regular.write_bytes(RAW)
            link = root / 'link.json'
            link.symlink_to(regular)
            oversize = root / 'large.json'
            with oversize.open('wb') as writer:
                writer.truncate(2 * 1024**2 + 1)
            for path in (link, root / 'missing.json', oversize):
                with self.subTest(path=path.name):
                    result = self.cli(root, path)
                    self.assertEqual([r['status'] for r in result], ['malformed', 'held'])

    def test_regular_control_and_path_replacement_refuses_changed_inode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'regular.json'
            target.write_bytes(RAW)
            self.assertEqual([r['status'] for r in self.cli(root, target)], ['valid', 'held'])
            original_read = os.read
            replaced = False
            def replace_after_open(fd, size):
                nonlocal replaced
                if not replaced:
                    target.rename(root / 'retained-inode.json')
                    target.write_bytes(b'authored replacement')
                    replaced = True
                return original_read(fd, size)
            with patch.object(os, 'read', replace_after_open):
                with self.assertRaisesRegex(binding.BindingError, 'derived-input-changed-during-read'):
                    binding.read_derived_input(target)
            self.assertEqual((root / 'retained-inode.json').read_bytes(), RAW)
            self.assertEqual(target.read_bytes(), b'authored replacement')
            self.assertTrue(replaced)

    def test_deep_json_and_non_scalar_normalization_preserve_held_peer(self):
        for depth in (200, 2000):
            raw = RAW.replace(b'"authored decimal token only"', b'[' * depth + b'0' + b']' * depth)
            with self.subTest(depth=depth):
                results = binding.assess_portfolio([profile(raw), HELD], now=NOW, inputs={'SB': raw})
                self.assertEqual([r['status'] for r in results], ['malformed', 'held'])
        value = json.loads(RAW)
        value['priceObservations'][0]['normalization'] = {'authored': 'wrong scalar type'}
        raw = json.dumps(value).encode()
        results = binding.assess_portfolio([profile(raw), HELD], now=NOW, inputs={'SB': raw})
        self.assertEqual(results[0]['diagnostics'], ['observation-normalization-invalid'])

    def test_bad_binding_country_and_shape_preserve_valid_and_held_peers(self):
        for malformed in (None, [], {'country': []}, {'country': {}}, {'country': None}):
            with self.subTest(binding=malformed):
                results = binding.assess_portfolio([malformed, profile(), HELD], now=NOW, inputs={'SB': RAW})
                self.assertEqual([r['status'] for r in results], ['malformed', 'valid', 'held'])
                self.assertIsNone(results[0]['country'])
                self.assertEqual(results[0]['diagnostics'], ['binding-country-invalid'])

    def test_positive_replay_origins_and_clock_retained(self):
        result = binding.assess_country(profile(), now=NOW, candidate_bytes=RAW)
        self.assertEqual(result['status'], 'valid')
        self.assertEqual(result['fieldOriginErrors'], 0)
        self.assertEqual(binding.assess_country(profile(), now=NOW, candidate_bytes=RAW,
                                               previous=result['replay'])['decision'], 'no-op')
        stale = profile()
        stale.update(originalAcquiredAt='2026-09-18T06:00:00Z', metadataValidatedAt=NOW)
        self.assertEqual(binding.assess_country(stale, now=NOW, candidate_bytes=b'not parsed')['status'], 'stale-input')


if __name__ == '__main__':
    unittest.main()
