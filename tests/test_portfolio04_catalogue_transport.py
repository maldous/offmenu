"""Owned installed-code catalogue delta; no actual source metadata reads."""
import ast
from pathlib import Path
import unittest
from unittest.mock import patch

from offmenu.refresh.acceptance import canonical
from offmenu.refresh.core import strict_json
from offmenu.refresh import portfolio04_binding as b
from offmenu.refresh import portfolio04_catalogue


class CatalogueTransportTests(unittest.TestCase):
    def test_exact_json_mirror_equivalence(self):
        self.assertEqual(canonical(b.load_catalogue()), canonical(strict_json(b.PROFILE.read_bytes())))

    def test_deepcopy_and_default_loader_has_no_file_io(self):
        with patch.object(Path, 'open', side_effect=AssertionError('no source/resource I/O')), \
                patch.object(b.os, 'open', side_effect=AssertionError('no metadata I/O')):
            first = b.load_catalogue()
            first['bindings'][0]['holds'].append('authored-mutation')
            first['evidence'].clear()
            second = b.load_catalogue()
        self.assertNotIn('authored-mutation', second['bindings'][0]['holds'])
        self.assertEqual(17, len(second['evidence']))

    def test_catalogue_module_is_only_docstring_and_literal(self):
        tree = ast.parse(Path(portfolio04_catalogue.__file__).read_text())
        self.assertEqual(2, len(tree.body))
        self.assertIsInstance(tree.body[0], ast.Expr)
        assignment = tree.body[1]
        self.assertIsInstance(assignment, ast.Assign)
        self.assertEqual(['CATALOGUE'], [target.id for target in assignment.targets])
        self.assertEqual(ast.literal_eval(assignment.value), b.load_catalogue())


if __name__ == '__main__':
    unittest.main()
