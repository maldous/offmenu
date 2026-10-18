"""Owned catalogue transport delta only; no retained metadata/source inputs."""
import ast
from pathlib import Path
import unittest
from unittest.mock import patch

from offmenu.refresh.core import canonical, strict_json
from offmenu.refresh.portfolio15 import load_catalog
from offmenu.refresh import portfolio15_catalogue


class CatalogueTransportTests(unittest.TestCase):
    def test_exact_json_mirror_equivalence(self):
        mirror = Path(__file__).resolve().parents[1] / 'docs/source-bindings/owner15.json'
        self.assertEqual(canonical(load_catalog()), canonical(strict_json(mirror.read_bytes())))

    def test_deep_copy_and_no_resource_io(self):
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('unexpected file read')):
            first = load_catalog()
            first['bindings'][0]['sourceHolds'].append('authored-mutation')
            first['bindings'][0]['evidence'].clear()
            second = load_catalog()
        self.assertNotIn('authored-mutation', second['bindings'][0]['sourceHolds'])
        self.assertTrue(second['bindings'][0]['evidence'])

    def test_catalogue_module_is_only_inert_literal(self):
        module = ast.parse(Path(portfolio15_catalogue.__file__).read_text())
        self.assertEqual(len(module.body), 2)
        self.assertIsInstance(module.body[0], ast.Expr)
        assignment = module.body[1]
        self.assertIsInstance(assignment, ast.Assign)
        self.assertEqual([target.id for target in assignment.targets], ['CATALOGUE'])
        self.assertEqual(ast.literal_eval(assignment.value), load_catalog())
