"""Focused code-catalogue transport checks; no source metadata/body reads."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from offmenu.refresh.core import sha
from offmenu.refresh.portfolio41 import load_bindings


class Portfolio41CatalogueTests(unittest.TestCase):
    def test_every_literal_equals_unchanged_json_mirror(self):
        mirror = Path(__file__).resolve().parents[1]/'config/portfolios/worker41.json'
        raw = mirror.read_bytes()
        self.assertEqual(sha(raw),
            'cb20731460b1d05b8534d7bf87d896bcec8fa5912adad5787040672a5de16af8')
        self.assertEqual(load_bindings(), json.loads(raw))

    def test_loader_deepcopy_keeps_nested_pins_and_holds_independent(self):
        first = load_bindings(); original = load_bindings()
        first['bindings'][0]['metadataPin']['sha256'] = 'authored-mutation'
        first['bindings'][0]['holds'].clear()
        first['bindings'].pop()
        self.assertEqual(load_bindings(), original)

    def test_default_loader_needs_no_file_or_network_access(self):
        with patch('builtins.open', side_effect=AssertionError('unexpected file read')), \
             patch.object(Path, 'open', side_effect=AssertionError('unexpected path read')), \
             patch('socket.create_connection', side_effect=AssertionError('unexpected network')):
            data = load_bindings()
        self.assertEqual(len(data['bindings']), 4)
        self.assertTrue(all(b['holds'] and b['bodyAdapter'] is None for b in data['bindings']))


if __name__ == '__main__':
    unittest.main()
