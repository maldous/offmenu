import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "national_common", ROOT / "scripts" / "align-national-common.py"
)
national = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(national)


class NationalCommonTests(unittest.TestCase):
    def test_scalar_uses_parent_context_and_camel_case_for_fixed_values(self):
        citation = "urn:test:citation"
        for path, value in [
            ("record:provenance:recordId", "F001"),
            ("record:provenance:sourceId", "afcd"),
            ("record:provenance:releaseId", "3"),
            ("record:provenance:archiveSha256", "a" * 64),
            ("record:schemaVersion", "1.0"),
            ("record:data:units[0]", "g"),
            ("record:countries[0]", "AU"),
            ("record:data:qualificationStatus", "unknown"),
        ]:
            self.assertEqual(
                national.scalar(value, "und", path, citation)["kind"], "identifier", path
            )
        prose = national.scalar("free source note", "und", "record:data:note", citation)
        self.assertEqual((prose["kind"], prose["language"]), ("text", "und"))

    def test_food_names_have_source_locale_and_other_human_text_stays_und(self):
        packet = national.graph({
            "id": "fixture", "countries": ["JP"],
            "provenance": {
                "sourceId": "mext", "recordId": "01034",
                "url": "https://example.test", "license": "CC0", "attribution": "fixture",
            },
            "data": {
                "foodName": "こむぎ", "basis": {"amount": 100, "unit": "g"},
                "nutrients": {"energy": {"name": "Energy", "value": 1, "unit": "kcal"}},
            },
        })
        self.assertEqual(packet["resources"][0]["names"][0]["language"], "ja-JP")
        self.assertEqual(packet["resources"][2]["names"][0]["language"], "und")

    def test_legal_notices_portions_and_descriptive_definitions_remain_source_text(self):
        citation = "urn:test:citation"
        for path, value in [
            ("record:data:basis:portion", "source analysed edible portion"),
            ("record:provenance:license", "FSANZ Data User Licence Agreement (CC BY-SA 3.0 AU based)"),
            ("record:provenance:countryNotice", "Australian data may not be appropriate elsewhere."),
            ("record:provenance:rights", "Normalized derivative data is distributed under source terms."),
            ("record:data:nutrients:energy:definition", "AFCD-3:Energy with dietary fibre, equated"),
        ]:
            scalar = national.scalar(value, "und", path, citation)
            self.assertEqual((scalar["kind"], scalar["language"]), ("text", "und"), path)
        self.assertEqual(
            national.scalar("ciqual:energy", "und", "record:data:nutrients:energy:definition", citation)["kind"],
            "identifier",
        )
        self.assertEqual(
            national.scalar("CC-BY-4.0", "und", "record:provenance:license", citation)["kind"],
            "identifier",
        )


if __name__ == "__main__":
    unittest.main()
