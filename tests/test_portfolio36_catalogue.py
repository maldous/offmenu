"""Owned catalogue transport checks; no retained source inputs are read."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio36
from offmenu.refresh._portfolio36_catalogue import load_catalogue


class CatalogueTransport(unittest.TestCase):
    def test_exact_json_mirror_equivalence(self):
        mirror = Path(__file__).resolve().parents[1] / 'config/source-bindings/owner36.json'
        self.assertEqual(load_catalogue(), json.loads(mirror.read_bytes()))

    def test_nested_mutations_do_not_escape_a_load(self):
        expected = load_catalogue()
        changed = load_catalogue()
        changed['sources'][0]['inputs'][0]['sha256'] = 'changed'
        changed['sources'][0]['holds'].append('test-hold')
        changed['sources'][0]['fields']['release']['expected'] = None
        self.assertEqual(load_catalogue(), expected)

    def test_default_cli_load_needs_no_metadata_or_json_read(self):
        expected = load_catalogue()
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('file read forbidden')):
            with patch.object(portfolio36, 'replay', return_value={'status': 'loader-probe'}) as replay:
                with redirect_stdout(StringIO()):
                    result = portfolio36.main(['--metadata-root', '/forbidden-metadata',
                                               '--workspace', '/unused-output',
                                               '--now', '2026-10-18T08:00:00Z'])
        self.assertEqual(result, 0)
        self.assertEqual(replay.call_args.args[0], expected)


if __name__ == '__main__':
    unittest.main()
