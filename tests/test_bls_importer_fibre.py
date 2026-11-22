"""Exercise the existing national importer with fictional XLSX rows only."""
from contextlib import contextmanager
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import openpyxl


def workbook(path, rows):
    with open_workbook() as book:
        for row in rows:
            book.active.append(row)
        book.save(path)




@contextmanager
def open_workbook():
    book = openpyxl.Workbook()
    try:
        yield book
    finally:
        book.close()


def importer():
    path = Path(__file__).resolve().parents[1] / "tools/data-processing/import_national_tables.py"
    spec = importlib.util.spec_from_file_location("national_workbooks", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BlsImporterFibreTests(unittest.TestCase):
    def read_fixture(self, last_headers, last_cells):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workbook(root / "BLS_4_0_Components_DE_EN.xlsx", [
                ("fixture", "component", "German", "English", "unit", "fixture", "fixture", "formula"),
                (None, "FIBT", "Fixture Gesamt", "Fixture Total", "g", None, None, None),
                (None, "FIBHMW", "Fixture Fraktion", "Fixture Fraction", "g", None, None, "Fixture dictionary descriptor"),
            ])
            workbook(root / "BLS_4_0_Daten_2025_DE.xlsx", [
                ("Code", "Name DE", "Name EN", "FIBT [g/100 g]", "FIBT origin", "FIBT reference", *last_headers),
                ("001-FIXTURE", "Fiktiv", "Fictional", 7.5, "fixture-total-origin", "fixture-total-reference", *last_cells),
            ])
            module = importer()
            # The legacy envelope supplies public policy defaults unrelated to this test.
            # Capture the parsed record before wrapping; this fixture grants no authority.
            from unittest.mock import patch
            with patch.object(module, "wrap", side_effect=lambda _s, _c, _k, data, *_: data):
                return module.bls(root)[0]["nutrients"]

    def test_total_and_fraction_preserve_their_own_provenance(self):
        values = self.read_fixture(
            ("FIBHMW [g/100 g]", "FIBHMW origin", "FIBHMW reference"),
            (2.5, "fixture-fraction-origin", "fixture-fraction-reference"),
        )
        self.assertEqual(set(values), {"fibre", "bls:FIBHMW"})
        for key, code, value, origin in (
            ("fibre", "FIBT", 7.5, "total"),
            ("bls:FIBHMW", "FIBHMW", 2.5, "fraction"),
        ):
            with self.subTest(key=key):
                observed = values[key]
                self.assertEqual(observed["sourceComponent"], code)
                self.assertEqual(observed["value"], value)
                self.assertEqual(observed["unit"], "g")
                self.assertEqual(observed["method"], f"fixture-{origin}-origin")
                self.assertEqual(observed["reference"], f"fixture-{origin}-reference")

    def test_absent_origin_or_reference_is_not_inferred_from_dictionary(self):
        variants = [
            (("FIBHMW [g/100 g]",), (2.5,), None, None),
            (("FIBHMW [g/100 g]", "FIBHMW origin"), (2.5, "fixture-origin"), "fixture-origin", None),
            (("FIBHMW [g/100 g]", "FIBHMW origin", "FIBHMW reference"),
             (2.5, None, "fixture-reference"), None, "fixture-reference"),
        ]
        for headers, cells, origin, reference in variants:
            with self.subTest(cells=cells):
                values = self.read_fixture(headers, cells)
                self.assertEqual(set(values), {"fibre", "bls:FIBHMW"})
                observed = values["bls:FIBHMW"]
                self.assertEqual(observed["value"], 2.5)
                self.assertEqual(observed["method"], origin)
                self.assertEqual(observed["reference"], reference)
                # A dictionary descriptor exists but does not establish per-row method.
                self.assertEqual(observed["formula"], "Fixture dictionary descriptor")
