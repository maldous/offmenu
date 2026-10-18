"""Portable catalogue checks; actual metadata readers are forbidden."""
import ast
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu import portfolio_worker62 as w
from offmenu import portfolio_worker62_catalogue as catalogue


class Worker62CatalogueTests(unittest.TestCase):
    def test_exact_literal_equivalence_to_unchanged_json_mirror(self):
        mirror = json.loads(w.CONFIG.read_bytes())
        tree = ast.parse(Path(catalogue.__file__).read_text())
        assignment = next(node for node in tree.body if isinstance(node, ast.Assign))
        self.assertEqual(ast.literal_eval(assignment.value), mirror)
        self.assertEqual(catalogue.load_catalogue(), mirror)
        self.assertEqual(len(mirror['metadata']), 19)
        self.assertTrue(all(source['holds'] for source in mirror['sources']))

    def test_deepcopy_has_no_nested_aliases_or_filesystem_read(self):
        expected = catalogue.load_catalogue()
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('no resource read')), \
                patch.object(Path, 'read_text', side_effect=AssertionError('no resource read')):
            first = catalogue.load_catalogue()
            second = catalogue.load_catalogue()
            first['sources'][0]['holds'].clear()
            first['metadata'].clear()
            self.assertEqual(second, expected)
            self.assertEqual(catalogue.load_catalogue(), expected)

    def test_default_cli_loads_catalogue_without_docs_or_actual_metadata(self):
        expected = catalogue.load_catalogue()
        observed = []
        def forbidden_reader_boundary(config):
            observed.append(copy.deepcopy(config))
            return {}  # Deliberately no real metadata reader invocation.
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'output'
            with patch.object(w, 'load_metadata', side_effect=forbidden_reader_boundary), \
                    patch.object(w, '_read_regular', side_effect=AssertionError('actual reader forbidden')), \
                    patch.object(Path, 'read_bytes', side_effect=AssertionError('docs read forbidden')), \
                    patch('builtins.print'):
                self.assertEqual(w.main(['--now', '2026-10-18T00:00:00Z',
                                         '--output', str(output)]), 0)
            self.assertEqual(observed, [expected])
            report = json.loads((output / 'metadata-report.json').read_bytes())
            self.assertEqual(report['metadataRecords'], 0)
            self.assertTrue(all(row['status'] == 'missing' for row in report['outcomes']))
            self.assertEqual(report['bodyOperations'], 0)


if __name__ == '__main__':
    unittest.main()
