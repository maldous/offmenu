"""Owned code-resource transport only; no actual source metadata is read."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from offmenu.refresh.worker10_bindings import CONFIG, load_config
from offmenu.refresh.worker10_catalogue import catalogue


class Worker10CatalogueTests(unittest.TestCase):
    def test_literal_exactly_matches_unchanged_json_mirror(self):
        raw = CONFIG.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         '45509d70adc62fffa325b0ca5f6682d0c881c3e4acf625785f755637f670e0cc')
        self.assertEqual(catalogue(), json.loads(raw))
        self.assertEqual(load_config(CONFIG), load_config())

    def test_each_default_load_has_independent_nested_state(self):
        first = load_config()
        expected = catalogue()
        first['bindings'][0]['fields']['releaseStatement'] = '/AUTHORED-MUTATION'
        first['bindings'][0]['prerequisites'][0]['nextAction'] = 'AUTHORED-MUTATION'
        first['bindings'][0]['types'].clear()
        first['reusedQualifications'].clear()
        self.assertEqual(load_config(), expected)

    def test_default_loader_performs_no_file_or_network_reads(self):
        with (patch('builtins.open', side_effect=AssertionError('file read')),
             patch.object(Path, 'read_bytes', side_effect=AssertionError('file read')),
             patch('os.open', side_effect=AssertionError('file read')),
             patch('socket.socket', side_effect=AssertionError('network'))):
            config = load_config()
        self.assertEqual(len(config['bindings']), 5)
        self.assertEqual(config['countries'], ['KW', 'NO', 'SA', 'UA'])


if __name__ == '__main__':
    unittest.main()
