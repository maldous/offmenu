"""New contract tests only; all recipe packets and package trees are synthetic."""
from copy import deepcopy
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import recipe_component_consumer as r

# Exact selected schema is source code/contract metadata, not a corpus packet.
SCHEMA_PATH = HERE.parent.parent / "bulk-parallel/schema.json"
schema_bytes = SCHEMA_PATH.read_bytes()
assert hashlib.sha256(schema_bytes).hexdigest() == r.SCHEMA
import jsonschema
validator = jsonschema.Draft202012Validator(json.loads(schema_bytes),
                                           format_checker=jsonschema.FormatChecker())


def quantity(value):
    return {"kind": "quantity", "value": value, "unitId": "urn:offmenu:unit:g",
            "dimension": "mass", "sourceValue": value, "sourceUnit": "g", "qualifiers": []}


def fixture():
    scope = {"visibility": "public", "reuseScope": "Synthetic source rights only"}
    cid = "urn:synthetic:citation:recipe:0001"
    def resource(identity, kind):
        return {"id": identity, "type": r.T + kind, "identityStatus": "source-scoped",
                "names": [], "citationIds": [cid], "scope": deepcopy(scope)}
    recipe = resource("urn:synthetic:recipe:0001", "RecipeVariant")
    components = [resource("urn:synthetic:component:1", "IngredientMention"),
                  resource("urn:synthetic:component:2", "IngredientMention")]
    def fact(identity, subject, prop, value):
        return {"id": identity, "subjectId": subject, "propertyId": r.P + prop,
                "value": value, "status": "source-asserted", "citationIds": [cid],
                "sourcePath": "synthetic.components." + identity.rsplit(":", 1)[-1],
                "scope": deepcopy(scope)}
    facts = [fact("urn:synthetic:quantity:1", components[0]["id"], "requiredQuantity", quantity(0)),
             fact("urn:synthetic:quantity:2", components[1]["id"], "requiredQuantity", quantity(None)),
             fact("urn:synthetic:yield:1", recipe["id"], "yield", quantity(None))]
    facts[1].update(status="candidate", derivation={
        "methodId": "urn:synthetic:source-normalization", "inputAssertionIds": ["urn:synthetic:raw-field:2"],
        "reviewStatus": "candidate"})
    facts[1]["value"].update(sourceValue="a pinch", sourceUnit=None, unitId=None,
                            dimension="unknown", qualifiers=["source-quantity-unresolved", "state:unknown"])
    edges = [{"id": "urn:synthetic:edge:" + str(i), "subjectId": recipe["id"],
              "predicateId": r.R + "usesIngredient", "objectId": component["id"],
              "status": "source-asserted" if i == 1 else "candidate", "citationIds": [cid],
              "sourcePath": "synthetic.recipe.components." + str(i), "scope": deepcopy(scope)}
             for i, component in enumerate(components, 1)]
    citation = {"id": cid, "sourceId": "synthetic-recipes", "revisionId": "synthetic-release",
                "originalRecordId": "0001", "originalUrl": "https://example.invalid/synthetic/0001",
                "license": "synthetic-test-license", "attribution": "Synthetic original attribution",
                "contentSha256": r.digest("synthetic source only"), "sourcePath": "synthetic/recipe/0001",
                "scope": deepcopy(scope)}
    packet = {"schemaVersion": "offmenu-common/1", "resources": [recipe] + components,
              "assertions": facts, "relations": edges, "citations": [citation], "translations": []}
    validator.validate(packet)
    key = (recipe["id"], citation["sourceId"], citation["revisionId"])
    locator = {"manifestByteSha256": r.CORE_MANIFEST, "assetKey": "recipes/synthetic.jsonl.gz",
               "assetSha256": r.digest("synthetic gzip"), "packetOrdinal": 0,
               "schemaByteSha256": r.SCHEMA, "sourceContractByteSha256": r.CORE_CONTRACT,
               "selectedContractByteSha256": r.CONTRACT, "retainedCoreProofSha256": r.CORE_PROOF}
    return packet, key, locator


class RecipeComponentTests(unittest.TestCase):
    def setUp(self):
        self.packet, self.key, self.locator = fixture()

    def adapt(self, **kwargs):
        return r.adapt_recipe(self.packet, *self.key, self.locator, include_candidates=True, **kwargs)

    def test_explicit_recipe_component_quantity_path_is_consumed(self):
        out = self.adapt()
        self.assertEqual(len(out["records"]), 2)
        for row in out["records"]:
            self.assertEqual(row["sourceEdge"]["subjectId"], self.key[0])
            self.assertEqual(row["sourceEdge"]["objectId"], row["sourceComponent"]["id"])
            self.assertEqual(row["quantityAssertion"]["subjectId"], row["componentId"])
            self.assertEqual(row["sourceEdgeCanonicalSha256"], r.digest(row["sourceEdge"]))
            self.assertEqual(row["quantityAssertionCanonicalSha256"], r.digest(row["quantityAssertion"]))

    def test_zero_unknown_source_units_range_and_yield_not_defaulted(self):
        self.packet["assertions"][0]["value"]["range"] = {"min": 0, "max": 1}
        out = self.adapt()
        self.assertEqual(out["records"][0]["quantity"]["value"], 0)
        self.assertIsNone(out["records"][1]["quantity"]["value"])
        self.assertEqual(out["records"][1]["quantity"]["sourceValue"], "a pinch")
        self.assertIsNone(out["records"][1]["quantity"]["unitId"])
        self.assertEqual(out["records"][0]["quantity"]["range"], {"min": 0, "max": 1})
        self.assertIsNone(out["recipeYield"]["assertions"][0]["value"]["value"])
        self.packet["assertions"][-1]["value"]["value"] = 0
        self.assertEqual(self.adapt()["recipeYield"]["assertions"][0]["value"]["value"], 0)
        self.packet["assertions"].pop()
        self.assertEqual(self.adapt()["recipeYield"]["status"], "not-supplied")

    def test_asserted_candidate_derivation_and_original_citation_preserved(self):
        out = self.adapt()
        self.assertEqual(out["records"][0]["sourceEdge"]["status"], "source-asserted")
        self.assertEqual(out["records"][1]["sourceEdge"]["status"], "candidate")
        self.assertEqual(out["records"][1]["quantityAssertion"], self.packet["assertions"][1])
        self.assertEqual(out["citations"], self.packet["citations"])
        self.assertEqual(out["sourceSelection"], self.locator)

    def test_preparation_markers_remain_unqualified_and_not_guessed(self):
        rows = self.adapt()["records"]
        self.assertEqual(rows[0]["preparation"]["status"], "not-supplied")
        self.assertEqual(rows[1]["preparation"]["status"], "source-carried-not-qualified")
        self.assertIn("state:unknown", rows[1]["preparation"]["sourceQualifiers"])
        self.assertTrue(all(x["preparation"]["acceptedCanonicalPreparation"] is None for x in rows))
        self.assertTrue(all(x["ingredientIdentity"]["canonicalIngredientId"] is None for x in rows))

    def test_literal_opt_in_required_by_adapter_and_reader(self):
        for value in (False, None, 1, "true"):
            out = r.adapt_recipe({}, "", "", "", {}, include_candidates=value)
            self.assertEqual(out["status"], "candidate-opt-in-required")
            consumer = r.RecipeComponentConsumer()
            with patch.object(consumer, "_prepare") as prepare:
                self.assertEqual(consumer.lookup("", 0, "", "", "", include_candidates=value)["records"], [])
                prepare.assert_not_called()

    def test_exact_missing_recipe_or_source_release_remains_empty(self):
        for key in (("urn:synthetic:missing", self.key[1], self.key[2]),
                    (self.key[0], "other-source", self.key[2]),
                    (self.key[0], self.key[1], "other-release")):
            out = r.adapt_recipe(self.packet, *key, self.locator, include_candidates=True)
            self.assertEqual(out["records"], [])

    def test_labels_never_create_membership_or_identity(self):
        self.packet["relations"].clear()
        self.assertEqual(self.adapt()["status"], "no-source-declared-component-edge")
        self.assertEqual(self.adapt()["records"], [])

    def test_missing_wrong_endpoint_or_quantity_is_not_synthesized(self):
        self.packet["relations"][0]["objectId"] = "urn:synthetic:missing"
        self.assertEqual(self.adapt()["status"], "declared-component-endpoint-unresolved")
        self.setUp(); self.packet["resources"][1]["type"] = r.T + "FoodConcept"
        self.assertEqual(self.adapt()["status"], "declared-component-endpoint-unresolved")
        self.setUp(); self.packet["assertions"].pop(0)
        self.assertEqual(self.adapt()["status"], "required-quantity-not-supplied")

    def test_duplicate_rows_edges_and_quantities_are_ambiguous(self):
        self.packet["resources"].append(deepcopy(self.packet["resources"][1]))
        with self.assertRaises(r.EvidenceError): self.adapt()
        self.setUp()
        duplicate = deepcopy(self.packet["relations"][0]); duplicate["id"] += ":duplicate"
        self.packet["relations"].append(duplicate)
        self.assertEqual(self.adapt()["status"], "ambiguous-component-edge")
        self.setUp()
        duplicate = deepcopy(self.packet["assertions"][0]); duplicate["id"] += ":duplicate"
        self.packet["assertions"].append(duplicate)
        self.assertEqual(self.adapt()["status"], "ambiguous-component-quantity")

    def test_cross_scope_and_citation_stitching_rejected(self):
        for mutate in (lambda p: p["relations"][0].update(citationIds=["urn:synthetic:other-citation"]),
                       lambda p: p["resources"][1].update(scope={"visibility": "private", "ownerId": "synthetic"}),
                       lambda p: p["assertions"][0].update(citationIds=[])):
            self.setUp(); mutate(self.packet)
            with self.assertRaises(r.EvidenceError): self.adapt()

    def test_unusable_edge_or_quantity_keeps_empty_typed_status(self):
        self.packet["relations"][0]["status"] = "unknown"
        self.assertEqual(self.adapt()["status"], "declared-component-edge-unresolved")
        self.setUp(); self.packet["assertions"][0]["status"] = "conflicting"
        self.assertEqual(self.adapt()["status"], "required-quantity-unresolved")

    def test_immutability_determinism_and_output_isolation(self):
        original = r.canonical(self.packet)
        first = self.adapt()
        self.assertEqual(original, r.canonical(self.packet))
        self.assertEqual(r.canonical(first), r.canonical(self.adapt()))
        self.packet["relations"].reverse(); self.packet["assertions"].reverse()
        reordered = self.adapt()
        self.assertEqual(first["records"], reordered["records"])
        self.assertNotEqual(first["inputPacketCanonicalSha256"], reordered["inputPacketCanonicalSha256"])
        first["records"][0]["quantity"]["value"] = 999
        self.assertNotEqual(self.adapt()["records"][0]["quantity"]["value"], 999)

    def test_no_nutrition_planning_or_step_membership_admission(self):
        out = self.adapt()
        for key in ("nutritionAggregationEligible", "automaticPlanningEligible", "servedApplicationActivation",
                    "publicationEligible", "portionScalingPerformed", "magnitudeConversionPerformed",
                    "inferredStepIngredientMembership"):
            self.assertIs(out[key], False)
        self.assertEqual(out["acceptedIngredientIdentityJoins"], 0)
        self.assertEqual(out["confidence"], {"status": "not-calibrated", "probability": None})

    def synthetic_reader(self, directory):
        # Reuse selected schema validator but mock only metadata preparation;
        # selected packet bytes and locator still traverse the actual reader.
        root = Path(directory); asset = root / "recipes/synthetic.jsonl.gz"; asset.parent.mkdir()
        payload = r.canonical(self.packet) + b"\n"
        data = gzip.compress(payload, mtime=0); asset.write_bytes(data)
        entry = {"key": "recipes/synthetic.jsonl.gz", "bytes": len(data),
                 "sha256": hashlib.sha256(data).hexdigest(), "packets": 1}
        c = r.RecipeComponentConsumer(root, root)
        c.entries = {entry["key"]: entry}; c.validator = validator
        return c, entry

    def test_manifest_locator_reader_invokes_real_adapter(self):
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            c, entry = self.synthetic_reader(directory)
            out = c.lookup(entry["key"], 0, *self.key, include_candidates=True)
            self.assertEqual(len(out["records"]), 2)
            self.assertEqual(out["sourceSelection"]["assetSha256"], entry["sha256"])
            self.assertEqual(out["inputPacketCanonicalSha256"], r.digest(self.packet))

    def test_asset_hash_missing_locator_ordinal_and_size_limits(self):
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            c, entry = self.synthetic_reader(directory)
            for key, ordinal in (("../outside", 0), (entry["key"], 1), (entry["key"], True)):
                with self.assertRaises(r.EvidenceError): c._packet(key, ordinal)
            (Path(directory) / entry["key"]).write_bytes(b"changed")
            with self.assertRaises(r.EvidenceError): c._packet(entry["key"], 0)

    def test_packet_limit_and_schema_are_enforced(self):
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            c, entry = self.synthetic_reader(directory)
            with patch.object(r, "MAX_PACKET", 8), self.assertRaises(r.EvidenceError):
                c._packet(entry["key"], 0)
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            del self.packet["resources"][0]["identityStatus"]
            c, entry = self.synthetic_reader(directory)
            with self.assertRaises(jsonschema.ValidationError): c._packet(entry["key"], 0)

    def test_duplicate_json_keys_and_symlink_input_refused(self):
        with self.assertRaises(r.EvidenceError): r.decode(b'{"id":1,"id":2}')
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            c, entry = self.synthetic_reader(directory)
            alias = Path(directory) / "alias"; alias.symlink_to(Path(directory) / "recipes")
            bad = dict(entry, key="alias/synthetic.jsonl.gz")
            with self.assertRaises(r.EvidenceError): r.checked(Path(directory), bad, r.MAX_ASSET)

    def test_first_locator_exercise_exports_only_aggregate_counts(self):
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            c, entry = self.synthetic_reader(directory)
            out = r.exercise_one(c)
            self.assertEqual(out["recipeQueries"], 1)
            self.assertEqual(out["componentQuantityRecords"], 2)
            self.assertEqual(out["unknownQuantityCount"], 1)
            self.assertEqual(out["zeroQuantityCount"], 1)
            self.assertNotIn("urn:synthetic:recipe", r.canonical(out).decode())
            self.assertNotIn("a pinch", r.canonical(out).decode())
            self.assertFalse(out["rawRowsExported"])

    def test_ambiguous_or_unknown_release_locator_not_selected(self):
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            self.packet["citations"][0]["revisionId"] = None
            c, entry = self.synthetic_reader(directory)
            self.assertIsNone(c._first_packet_locator())


    def metadata_fixture(self):
        assets = [{"key": "recipes/synthetic-%04d.jsonl.gz" % i, "bytes": 1,
                   "sha256": "0" * 64, "packets": 500} for i in range(51)]
        source = {"files": assets + [
            {"key": "schema.json", "bytes": len(schema_bytes), "sha256": r.SCHEMA},
            {"key": "contract.json", "bytes": 1, "sha256": r.CORE_CONTRACT}]}
        selected = {"files": [
            {"key": "schema.json", "bytes": len(schema_bytes), "sha256": r.SCHEMA},
            {"key": "contract.json", "bytes": 1, "sha256": r.CONTRACT}]}
        proof = {"manifestByteSha256": r.CORE_MANIFEST, "sourceCodeSha256": r.INSPECTOR_CODE,
                 "selectedSchemaSha256": r.SCHEMA, "identityAdmissionGranted": False,
                 "selectedAssets": assets}
        contract = {"types": {"RecipeVariant": {"id": r.T + "RecipeVariant"},
                               "IngredientMention": {"id": r.T + "IngredientMention"}},
                    "relationshipVocabulary": {"usesIngredient": {"id": r.R + "usesIngredient"}},
                    "sharedProperties": {"requiredQuantity": {"id": r.P + "requiredQuantity"},
                                         "yield": {"id": r.P + "yield"}}}
        return source, selected, proof, contract

    def test_preparation_checks_selected_manifest_proof_and_both_contracts(self):
        source, selected, proof, contract = self.metadata_fixture()
        def metadata(path, pin):
            if path.name == "report.json":
                self.assertEqual(pin, r.CORE_PROOF); return proof
            if path.parent.name == "bulk-parallel":
                self.assertEqual(pin, r.SELECTED_MANIFEST); return selected
            self.assertEqual(pin, r.CORE_MANIFEST); return source
        def asset(root, entry, cap):
            return schema_bytes if entry["key"] == "schema.json" else r.canonical(contract)
        with patch.object(r, "pinned_json", side_effect=metadata), patch.object(r, "checked", side_effect=asset):
            consumer = r.RecipeComponentConsumer()
            consumer._prepare()
            self.assertEqual(len(consumer.entries), 51)
            consumer._prepare()

    def test_changed_proof_or_source_contract_pin_is_refused(self):
        for target in ("proof", "contract"):
            source, selected, proof, contract = self.metadata_fixture()
            if target == "proof": proof["identityAdmissionGranted"] = True
            else: source["files"][-1]["sha256"] = "0" * 64
            def metadata(path, pin):
                return proof if path.name == "report.json" else selected if path.parent.name == "bulk-parallel" else source
            def asset(root, entry, cap):
                return schema_bytes if entry["key"] == "schema.json" else r.canonical(contract)
            with patch.object(r, "pinned_json", side_effect=metadata), patch.object(r, "checked", side_effect=asset), \
                 self.assertRaises(r.EvidenceError):
                r.RecipeComponentConsumer()._prepare()

    def test_changed_relevant_contract_definition_is_not_substituted(self):
        source, selected, proof, contract = self.metadata_fixture()
        def metadata(path, pin):
            return proof if path.name == "report.json" else selected if path.parent.name == "bulk-parallel" else source
        def asset(root, entry, cap):
            if entry["key"] == "schema.json": return schema_bytes
            value = deepcopy(contract)
            if root.name == "bulk-parallel":
                value["relationshipVocabulary"]["usesIngredient"]["id"] = "urn:synthetic:different"
            return r.canonical(value)
        with patch.object(r, "pinned_json", side_effect=metadata), patch.object(r, "checked", side_effect=asset), \
             self.assertRaises(r.EvidenceError):
            r.RecipeComponentConsumer()._prepare()

    def test_pinned_manifest_metadata_byte_hash_checked(self):
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            p = Path(directory) / "manifest.json"; p.write_bytes(b'{"synthetic":true}')
            pin = hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertEqual(r.pinned_json(p, pin), {"synthetic": True})
            with self.assertRaises(r.EvidenceError): r.pinned_json(p, "0" * 64)


if __name__ == "__main__":
    unittest.main()
