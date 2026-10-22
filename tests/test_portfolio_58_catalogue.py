"""Installed code-catalogue transport only; real metadata reads are forbidden."""
import contextlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio_58
from offmenu.refresh.portfolio_58_catalogue import load_catalogue


class CatalogueTransportTests(unittest.TestCase):
    def test_exact_equivalence_with_unchanged_json_mirror(self):
        mirror = Path(__file__).resolve().parents[1] / 'config/staging/portfolio58.json'
        self.assertEqual(load_catalogue(), json.loads(mirror.read_bytes()))

    def test_deepcopy_including_nested_selectors_holds_and_unknowns(self):
        first, expected = load_catalogue(), load_catalogue()
        first['bindings'][0]['selectors'].clear()
        first['bindings'][0]['holds'].append('authored mutation')
        first['bindings'][0]['declarations']['unknowns'].append('authored unknown')
        first['countryTypeApplicability'][0]['sources'].clear()
        self.assertEqual(load_catalogue(), expected)

    def test_default_cli_loader_requires_no_repository_resource_or_source_reads(self):
        expected = load_catalogue()
        with patch.object(portfolio_58, 'CONFIG', Path('/absent-authored-checkout/config.json')), \
                patch.object(portfolio_58, 'run', return_value={'sources': []}) as runner, \
                patch.object(Path, 'read_bytes', side_effect=AssertionError('file read forbidden')), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(portfolio_58.main(['--now', '2026-10-18T06:00:00Z']), 0)
        self.assertEqual(runner.call_args.args[0], expected)


if __name__ == '__main__':
    unittest.main()
