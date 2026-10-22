"""Registry-only fixtures; no network, credentials or dataset records."""
import copy
import unittest

from validate_registry_bundle import load_bundle, validate_bundle


class RegistryBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = load_bundle()

    def test_all_disabled_and_foo_only(self):
        result = validate_bundle(self.bundle)
        self.assertTrue(result["all_disabled"])
        self.assertEqual(result["source_rows"], {"structured-recipes": 26, "multilingual-recipes": 23, "menus": 31})

    def test_multilingual_enable_rejected(self):
        bundle = copy.deepcopy(self.bundle)
        bundle["multilingual-recipes"]["disabled_fetch_proposals"][0]["enabled"] = True
        with self.assertRaises(ValueError):
            validate_bundle(bundle)

    def test_menu_enable_rejected(self):
        bundle = copy.deepcopy(self.bundle)
        bundle["menus"]["sources"][0]["proposed_registry"]["production_fetch_allowed"] = True
        with self.assertRaises(ValueError):
            validate_bundle(bundle)

    def test_missing_relational_gate_rejected(self):
        bundle = copy.deepcopy(self.bundle)
        bundle["menus"]["sources"][0]["proposed_registry"]["activation_gates"].remove("all_eight_databases_relationally_fit_for_existing_data")
        with self.assertRaises(ValueError):
            validate_bundle(bundle)

    def test_other_host_rejected(self):
        bundle = copy.deepcopy(self.bundle)
        bundle["multilingual-recipes"]["production_fetch_target"] = "local"
        with self.assertRaises(ValueError):
            validate_bundle(bundle)

    def test_duplicate_source_rejected(self):
        bundle = copy.deepcopy(self.bundle)
        bundle["menus"]["sources"].append(bundle["menus"]["sources"][0])
        with self.assertRaises(ValueError):
            validate_bundle(bundle)

    def test_invented_recipe_reference_rejected(self):
        bundle = copy.deepcopy(self.bundle)
        bundle["menus"]["sources"][0]["mapping"]["recipe_reference"] = "invented"
        with self.assertRaises(ValueError):
            validate_bundle(bundle)


if __name__ == "__main__":
    unittest.main()
