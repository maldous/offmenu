import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("north_star", ROOT / "scripts/north_star_derivations.py")
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)
CONTRACT = json.loads((ROOT.parent / "selected/corpus/common-data-contract.json").read_text())
SCOPE = {"visibility": "public", "reuseScope": "Synthetic fixture only"}


def resource(identifier, kind):
    return {"id": identifier, "type": MOD.TYPE + kind, "identityStatus": "source-scoped",
            "names": [], "scope": copy.deepcopy(SCOPE), "citationIds": ["urn:test:citation"]}


def fixture(value=0):
    quantity = {"kind": "quantity", "value": value, "unitId": "urn:offmenu:unit:mg",
                "dimension": "mass", "sourceValue": value, "sourceUnit": "mg", "qualifiers": [],
                "basis": {"kind": "quantity", "value": 100, "unitId": "urn:offmenu:unit:g",
                          "dimension": "mass", "sourceValue": 100, "sourceUnit": "g", "qualifiers": []}}
    base = {"subjectId": "urn:test:profile", "status": "source-asserted",
            "citationIds": ["urn:test:citation"], "scope": copy.deepcopy(SCOPE)}
    return {"schemaVersion": "offmenu-common/1",
            "resources": [resource("urn:test:product", "FoodProduct"), resource("urn:test:profile", "FoodCompositionObservation")],
            "assertions": [
                dict(base, id="urn:test:quantity", propertyId=MOD.PROP + "nutrientObservation", sourcePath="data.nutrients.sodium", value=quantity),
                dict(base, id="urn:test:metadata", propertyId=MOD.PROP + "sourceNutrientMetadata", sourcePath="data.nutrients.sodium.metadata",
                     value={"kind": "structure", "fields": {"definition": {"kind": "identifier", "value": "SOURCE:123"},
                            "qualifier": {"kind": "identifier", "value": "less-than"}}}),
            ],
            "relations": [{"id": "urn:test:edge", "subjectId": "urn:test:product",
                           "predicateId": MOD.REL + "hasCompositionObservation", "objectId": "urn:test:profile",
                           "status": "source-asserted", "citationIds": ["urn:test:citation"],
                           "scope": copy.deepcopy(SCOPE), "sourcePath": "data.nutritionId"}],
            "citations": [{"id": "urn:test:citation", "sourceId": "fixture", "originalRecordId": "000001",
                           "originalUrl": "https://example.test/fixture", "revisionId": "test-1", "license": "CC0",
                           "attribution": "Synthetic", "scope": copy.deepcopy(SCOPE)}], "translations": []}


class DerivationTests(unittest.TestCase):
    def derive(self, p=None):
        return MOD.derive(p or fixture(), CONTRACT)

    def test_deterministic_immutable_addition(self):
        p = fixture(); before = copy.deepcopy(p)
        a = self.derive(p); b = self.derive(p)
        self.assertEqual(a, b); self.assertEqual(p, before)
        self.assertEqual(a["inputPacketCanonicalSha256"], MOD.digest(p))

    def test_relationship_has_versioned_exact_evidence(self):
        edge = self.derive()["relations"][0]
        self.assertEqual(edge["predicateId"], MOD.REL + "hasNutrientObservation")
        self.assertEqual(edge["derivation"]["inputRelationIds"], ["urn:test:edge"])
        self.assertIn(MOD.VERSION, edge["derivation"]["methodId"])
        self.assertEqual(edge["status"], "candidate")

    def test_zero_is_not_unknown(self):
        fields = self.derive()["assertions"][0]["value"]["fields"]
        self.assertEqual(fields["quantity"]["value"], 0)
        self.assertFalse(fields["unknownValue"]["value"])

    def test_unknown_is_not_zero(self):
        fields = self.derive(fixture(None))["assertions"][0]["value"]["fields"]
        self.assertIsNone(fields["quantity"]["value"])
        self.assertTrue(fields["unknownValue"]["value"])

    def test_trace_limit_and_exact_definition_are_not_equivalence(self):
        fields = self.derive()["assertions"][0]["value"]["fields"]
        self.assertEqual(fields["sourceMetricMetadata"]["fields"]["qualifier"]["value"], "less-than")
        self.assertEqual(fields["sourceMetricMetadata"]["fields"]["definition"]["value"], "SOURCE:123")
        self.assertEqual(fields["comparability"]["value"], "not-qualified")

    def test_no_missing_preparation_invention(self):
        out = self.derive()
        self.assertIn("preparation-basis-not-carried-in-quantity", [i["code"] for i in out["issues"]])
        self.assertFalse(out["assertions"][0]["value"]["fields"]["preparationBasisCarried"]["value"])

    def test_preparation_and_range_preserved(self):
        p = fixture(); q = p["assertions"][0]["value"]
        q["basis"]["qualifiers"] = ["state:prepared"]; q["range"] = {"min": 0, "max": 0.1}
        fields = self.derive(p)["assertions"][0]["value"]["fields"]
        self.assertEqual(fields["quantity"], q); self.assertTrue(fields["preparationBasisCarried"]["value"])

    def test_unregistered_unit_not_silently_fixed(self):
        p = fixture(); p["assertions"][0]["value"]["unitId"] = "urn:offmenu:unit:ug"
        out = self.derive(p)
        self.assertIn("unit-definition-not-in-selected-contract", [i["code"] for i in out["issues"]])
        self.assertEqual(out["assertions"][0]["value"]["fields"]["quantity"]["unitId"], "urn:offmenu:unit:ug")

    def test_exact_energy_alias_is_candidate_not_mutation(self):
        p=fixture(); q=p["assertions"][0]["value"]
        q.update(unitId="urn:offmenu:unit:kj",sourceUnit="kJ",dimension="energy")
        fields=self.derive(p)["assertions"][0]["value"]["fields"]
        self.assertEqual(fields["canonicalUnitCandidate"]["value"],"urn:offmenu:unit:kJ")
        self.assertEqual(fields["quantity"],q)
        q["dimension"]="mass"
        self.assertNotIn("canonicalUnitCandidate",self.derive(p)["assertions"][0]["value"]["fields"])

    def test_profile_basis_is_exposed_not_used_as_nutrient_state(self):
        p=fixture(); source=copy.deepcopy(p["assertions"][1]); source.update(id="urn:test:source-fields",propertyId=MOD.PROP+"sourceFields",sourcePath="data")
        source["value"]={"kind":"structure","fields":{"basis":{"kind":"structure","fields":{"state":{"kind":"identifier","value":"raw"}}}}}
        p["assertions"].append(source); fact=self.derive(p)["assertions"][0];fields=fact["value"]["fields"]
        self.assertEqual(fields["profileReportedBasis"]["fields"]["state"]["value"],"raw")
        self.assertFalse(fields["preparationBasisCarried"]["value"])
        self.assertFalse(fields["profileBasisQualifiesNutrientPreparation"]["value"])
        self.assertIn(source["id"],fact["derivation"]["inputAssertionIds"])

    def test_exact_subject_path_join_not_metric_name_join(self):
        p = fixture(); p["assertions"][1]["sourcePath"] = "data.nutrients.salt.metadata"
        self.assertEqual(self.derive(p)["assertions"], [])

    def test_ambiguous_metadata_does_not_select_first(self):
        p = fixture(); other = copy.deepcopy(p["assertions"][1]); other["id"] = "urn:test:other"; p["assertions"].append(other)
        self.assertEqual(self.derive(p)["assertions"], [])

    def test_cross_owner_scope_is_rejected(self):
        p = fixture(); p["assertions"][1]["scope"] = {"visibility": "private", "ownerId": "someone"}
        with self.assertRaisesRegex(ValueError, "mixed"): self.derive(p)

    def test_disjoint_source_records_not_joined_by_subject_path(self):
        p = fixture(); citation = copy.deepcopy(p["citations"][0])
        citation.update(id="urn:test:other-citation", sourceId="another-source", originalRecordId="another-record")
        p["citations"].append(citation); p["assertions"][1]["citationIds"] = [citation["id"]]
        out = self.derive(p)
        self.assertEqual(out["assertions"], [])
        self.assertIn("nutrient-context-source-citations-differ", [i["code"] for i in out["issues"]])

    def test_held_or_revoked_input_not_promoted(self):
        p = fixture(); p["assertions"][0]["status"] = "superseded"; p["relations"][0]["status"] = "conflicting"
        out = self.derive(p)
        self.assertEqual(out["assertions"], []); self.assertEqual(out["relations"], [])

    def test_missing_citation_rejected(self):
        p = fixture(); p["citations"] = []
        with self.assertRaisesRegex(ValueError, "citation"): self.derive(p)

    def test_duplicate_identity_rejected(self):
        p = fixture(); p["assertions"].append(p["assertions"][0])
        with self.assertRaisesRegex(ValueError, "duplicate"): self.derive(p)

    def test_missing_endpoint_remains_explicit(self):
        p = fixture(); p["relations"][0]["objectId"] = "urn:test:not-in-packet"
        self.assertEqual(self.derive(p)["relations"][0]["endpointResolution"], "input-graph-required")

    def test_wrong_composition_target_type_not_promoted(self):
        p = fixture(); p["resources"][1]["type"] = MOD.TYPE + "FoodIngredient"
        self.assertEqual(self.derive(p)["relations"], [])

    def test_no_identity_recipe_or_admission_inference(self):
        out = self.derive()
        self.assertFalse(out["automaticPlanningEligible"]); self.assertFalse(out["publicationEligible"])
        self.assertFalse(out["nutritionAggregationEligible"]); self.assertEqual(out["identityEffect"], "none")
        self.assertIsNone(out["confidence"]["probability"])
        self.assertIsNone(out["sourceCoverage"]["servedConsumerQueries"])
        self.assertFalse(any(e["predicateId"].endswith(("exactMatch", "candidateMatch")) for e in out["relations"]))

    def test_consumer_must_opt_in_to_candidates(self):
        out = self.derive()
        self.assertEqual(MOD.query_candidates(out, "urn:test:product")["relations"], [])
        self.assertEqual(len(MOD.query_candidates(out, "urn:test:product", include_candidates=True)["relations"]), 1)

    def test_selected_common_value_schema_compatible(self):
        import jsonschema
        schema = json.loads((ROOT.parent / "selected/corpus/common-data.schema.json").read_text())
        checker = jsonschema.Draft202012Validator({"$defs": schema["$defs"], "$ref": "#/$defs/value"})
        checker.validate(self.derive()["assertions"][0]["value"])


if __name__ == "__main__":
    unittest.main()
