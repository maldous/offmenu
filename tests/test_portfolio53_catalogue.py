"""Owned fixed-code resource checks; never inspect retained source metadata."""
import ast
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import unittest
from unittest import mock

from offmenu.refresh import portfolio53 as p

MIRROR_SHA = 'a3b3c8d2b7b4f065159dd340013774e220f95704e0312ead30d2a30f2e944c2e'


class CatalogueTests(unittest.TestCase):
    def test_exact_original_json_and_inert_literal(self):
        raw=p.CONFIG.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),MIRROR_SHA)
        self.assertEqual(p.load_catalogue(),json.loads(raw))
        path=Path(p.__file__).with_name('portfolio53_catalogue.py')
        tree=ast.parse(path.read_text())
        self.assertEqual([type(n).__name__ for n in tree.body],['Expr','Assign'])
        self.assertEqual(ast.literal_eval(tree.body[1].value),json.loads(raw))

    def test_nested_copy_cannot_mutate_next_load(self):
        first=p.load_catalogue();expected=p.load_catalogue()
        first['sources'][0]['holds'].append('authored-mutation')
        first['sources'][0]['metadata'][0]['selectors'].clear()
        first['sources'][0]['rawAssetReferences'][0]['sha256']='f'*64
        self.assertEqual(p.load_catalogue(),expected)

    def test_loader_and_default_cli_do_not_read_source_or_json_mirror(self):
        expected=p.load_catalogue();output=io.StringIO()
        def forbidden(*args,**kwargs):raise AssertionError('code catalogue attempted I/O')
        def metadata_plan_stub(bindings,**kwargs):
            self.assertEqual(bindings,expected['sources'])
            return {'codeCatalogueLoaded':True,'sourceMetadataRead':False}
        with mock.patch.object(Path,'read_bytes',side_effect=forbidden), \
             mock.patch.object(Path,'read_text',side_effect=forbidden), \
             mock.patch.object(Path,'open',side_effect=forbidden), \
             mock.patch.object(p.os,'open',side_effect=forbidden), \
             mock.patch.object(p,'plan',side_effect=metadata_plan_stub),redirect_stdout(output):
            self.assertEqual(p.load_catalogue(),expected)
            p.main(['--now','2026-10-18T00:00:00Z'])
        self.assertEqual(json.loads(output.getvalue()),
                         {'codeCatalogueLoaded':True,'sourceMetadataRead':False})


if __name__=='__main__':unittest.main()
