"""Narrow transport checks; real source metadata and bodies are never inputs."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from offmenu.refresh._portfolio08_catalogue import catalogue, JSON_MIRROR_SHA256
from offmenu.refresh import portfolio08_bindings as binding


class CatalogueTransportTest(unittest.TestCase):
    def test_full_mirror_equivalence(self):
        raw = (Path(__file__).resolve().parents[1] /
               'config/portfolio08-source-bindings.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), JSON_MIRROR_SHA256)
        self.assertEqual(catalogue(), json.loads(raw))

    def test_nested_returns_are_detached(self):
        original = catalogue()
        changed = catalogue()
        changed['sources'][0]['holds'].append('caller-mutation')
        changed['portfolio'].clear()
        changed['sources'][0]['enabled'] = True
        policies = binding.policies()
        policies[0]['holds'].clear()
        policies[0]['enabled'] = True
        self.assertEqual(catalogue(), original)
        self.assertEqual(binding.policies(), original['sources'])

    def test_default_loader_and_cli_forbid_metadata_reads_and_network(self):
        out = io.StringIO()
        forbidden = AssertionError('external read or transport attempted')
        with patch('pathlib.Path.open', side_effect=forbidden), \
             patch('builtins.open', side_effect=forbidden), \
             patch('socket.socket', side_effect=forbidden), \
             patch.object(binding, 'load_metadata', side_effect=forbidden), \
             contextlib.redirect_stdout(out):
            self.assertEqual(len(binding.policies()), 10)
            self.assertEqual(binding.main(['--now', '2026-10-18T00:00:00Z']), 2)
        result = json.loads(out.getvalue())
        self.assertFalse(result['countryAcceptance'])
        self.assertEqual(len(result['results']), 10)
        for row in result['results']:
            self.assertEqual(row['status'], 'held')
            self.assertEqual(row['sourceBodiesRead'], 0)
            self.assertEqual(row['networkRequests'], 0)
            self.assertFalse(row['sourceAdmission'])
            self.assertFalse(row['countryComplete'])


if __name__ == '__main__':
    unittest.main()
