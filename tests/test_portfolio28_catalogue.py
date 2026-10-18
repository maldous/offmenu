"""Owned code catalogue transport checks; never source metadata reads."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio28 as p


class Portfolio28CatalogueTests(unittest.TestCase):
    def test_exact_json_mirror(self):
        mirror = Path(__file__).resolve().parents[1] / 'config/portfolio28-staging.json'
        self.assertEqual(p.portfolio_config(), json.loads(mirror.read_bytes()))

    def test_default_loader_is_io_free_and_deeply_independent(self):
        with patch('builtins.open', side_effect=AssertionError('forbidden metadata read')), \
             patch.object(Path, 'open', side_effect=AssertionError('forbidden metadata read')), \
             patch('socket.create_connection', side_effect=AssertionError('forbidden network')):
            original = p.portfolio_config()
            changed = p.portfolio_config()
            changed['bindings'][0]['metadataInputs'][0]['sha256'] = 'mutated'
            changed['bindings'][0]['holds'].clear()
            changed['bindings'][0]['selectors'][0]['expected'] = 'mutated'
            self.assertEqual(p.portfolio_config(), original)
            self.assertNotEqual(changed, original)
            self.assertEqual(len(p.bindings()), 6)


if __name__ == '__main__':
    unittest.main()
