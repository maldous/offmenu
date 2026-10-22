"""Invented mock records only; no source datasets or network calls."""
import copy
import json
import unittest
from pathlib import Path

from offline_inspection import inspect_foodista_record, inspect_themealdb_record
from validate_manifest import production_fetch, validate_manifest


class PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((Path(__file__).resolve().parents[2] / "structured-recipes.json").read_text())

    def test_manifest_disabled_and_foo_only(self):
        result = validate_manifest(self.manifest)
        self.assertEqual(result["source_count"], 26)
        self.assertTrue(result["all_disabled"])

    def test_source_enable_rejected(self):
        m = copy.deepcopy(self.manifest)
        m["sources"][0]["enabled"] = True
        with self.assertRaises(ValueError):
            validate_manifest(m)

    def test_global_enable_rejected(self):
        m = copy.deepcopy(self.manifest)
        m["production_fetch_enabled"] = True
        with self.assertRaises(ValueError):
            validate_manifest(m)

    def test_execution_elsewhere_rejected(self):
        m = copy.deepcopy(self.manifest)
        m["execution_location"] = "local"
        with self.assertRaises(ValueError):
            validate_manifest(m)

    def test_eight_ready_flags_do_not_activate(self):
        with self.assertRaises(PermissionError):
            production_fetch(location="Foo", ready=[True] * 8, files_exist=[True] * 8, enabled=True)

    def test_foodista_candidate_and_comment_exclusion(self):
        record = {"id": "mock", "created": "", "metadata": {"url": "https://foodista.com/recipe/mock/example", "license": "mock-license", "authors": ["Fixture"]}, "text": "Invented fixture\nIngredients\n2 units example ingredient\nPreparation\n1 Perform invented step.\nComments:\nDo not ingest this comment."}
        result = inspect_foodista_record(record)
        self.assertNotIn("comment", result["instructions_raw"])
        self.assertEqual(result["created_raw"], "")
        self.assertFalse(result["rights_approved"])

    def test_foodista_blog_not_recipe(self):
        with self.assertRaises(ValueError):
            inspect_foodista_record({"metadata": {"url": "https://foodista.com/blog/mock"}, "text": "Title\nIngredients\na\nPreparation\nb"})

    def test_foodista_wrong_host_rejected(self):
        with self.assertRaises(ValueError):
            inspect_foodista_record({"metadata": {"url": "https://foodista.com.evil.invalid/recipe/mock"}, "text": "Title\nIngredients\na\nPreparation\nb"})

    def test_foodista_ambiguous_or_empty_sections_rejected(self):
        for text in ["Title\nIngredients\nPreparation\nStep", "Title\nIngredients\na\nIngredients\nb\nPreparation\nStep"]:
            with self.assertRaises(ValueError):
                inspect_foodista_record({"metadata": {"url": "https://foodista.com/recipe/mock"}, "text": text})

    def test_mealdb_pairs_slots_without_invented_quantity(self):
        result = inspect_themealdb_record({"idMeal": "mock", "strMeal": "Fixture", "strInstructions": "Invented step.", "strIngredient1": "example", "strMeasure1": None, "strIngredient2": "", "strMeasure2": "", "strCreativeCommonsConfirmed": None})
        self.assertEqual(len(result["ingredients_raw"]), 1)
        self.assertIsNone(result["ingredients_raw"][0]["measure_raw"])
        self.assertFalse(result["rights_approved"])

    def test_mealdb_orphan_quantity_rejected(self):
        with self.assertRaises(ValueError):
            inspect_themealdb_record({"strMeal": "Fixture", "strInstructions": "Invented step.", "strMeasure1": "2"})


if __name__ == "__main__":
    unittest.main()
