"""Synthetic-only checks built with the retained derive/native_projection/restore."""
import copy
import hashlib
import importlib.util
import pathlib
import sys
import unittest

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE / "basis-code-v1"))
sys.path.insert(0, str(HERE))
from typed_nutrient_context import adapt, canonical, digest, EvidenceError, CODE_PINS, PROP, TYPE, REL

# Verify source files before importing producer fixture helpers.
for name in ("north_star_derivations.py", "north_star_basis_restoration.py"):
    path = BASE / "basis-code-v1" / name
    if hashlib.sha256(path.read_bytes()).hexdigest() != CODE_PINS[name]:
        raise RuntimeError("retained synthetic-fixture source pin differs: " + name)
caller_path = BASE / "caller-code-v2/source_scoped_north_star_consumer.py"
if hashlib.sha256(caller_path.read_bytes()).hexdigest() != CODE_PINS[caller_path.name]:
    raise RuntimeError("retained caller source pin differs")
from north_star_derivations import derive
from north_star_basis_restoration import native_projection, restore, old_quantity, urn, SCOPE


def fixture():
    contract = {"units": {k: {"id": "urn:offmenu:unit:" + k} for k in ("g", "mg", "kJ", "microgram")}}
    pin = lambda name: digest(["synthetic-only", name])
    pins = {"sourceManifestByteSha256": pin("source"),
            "bulkDerivedManifestByteSha256": pin("bulk"),
            "basisDerivedManifestByteSha256": pin("basis")}
    select = lambda ordinal: {"manifestByteSha256": pins["sourceManifestByteSha256"],
        "assetKey": "synthetic/part-00000.jsonl.gz", "assetSha256": pin("asset"), "packetOrdinal": ordinal}
    source = "off"; rid = "synthetic-profile-1"
    record = {
        "id": rid, "kind": "nutrientProfile",
        "provenance": {"sourceId": source, "recordId": rid, "releaseId": "synthetic-release",
                       "archiveSha256": pin("archive"), "license": "synthetic-test-license",
                       "visibility": "public"},
        "curation": {"schema": "offmenu-curation/1", "policyVersion": "offmenu-curation/1",
                     "status": "selected-source-facts", "rawSourcePayloadPublished": False,
                     "automaticDietQualification": False, "sourceRecordReference": "synthetic/row/1",
                     "humanReviewed": False},
        "data": {"nutrients": {
            "energy": {"value": 0, "unit": "kJ", "basis": {"amount": 100, "unit": "g", "state": "raw"}},
            "protein": {"value": None, "unit": "mg", "basis": {"amount": 100, "unit": "g", "state": None}},
            "fibre": {"value": 3, "unit": "g", "basis": {"amount": 50, "unit": "g", "state": "cooked"}},
            "sodium": {"value": 7, "unit": "mcg", "basis": {"amount": 100, "unit": "g"}},
        }},
    }
    resource_id = urn("resource", source, rid); cid = urn("citation", source, rid)
    citation = {"id": cid, "sourceId": source, "originalRecordId": rid,
                "revisionId": "synthetic-release", "contentSha256": pin("archive"),
                "license": "synthetic-test-license", "attribution": {"text": "Synthetic attribution only"},
                "sourcePath": "synthetic/row/1", "scope": copy.deepcopy(SCOPE)}
    resource = {"id": resource_id, "type": TYPE + "FoodCompositionObservation",
                "scope": copy.deepcopy(SCOPE), "citationIds": [cid]}
    def fact(prop, path, value):
        return {"id": urn("assertion", resource_id, prop, path), "subjectId": resource_id,
                "propertyId": PROP + prop, "sourcePath": path, "value": value,
                "status": "source-asserted", "scope": copy.deepcopy(SCOPE), "citationIds": [cid]}
    facts = [fact("originalSourceRecord", "id", {"kind": "identifier", "value": rid}),
             fact("sourceFields", "data", {"kind": "structure", "fields": {
                 "basis": {"kind": "structure", "fields": {
                     "state": {"kind": "text", "value": "profile-wide-baked"}}}}})]
    for key, n in record["data"]["nutrients"].items():
        path = "data.nutrients." + key
        q = old_quantity(n["value"], n["unit"], old_quantity(n["basis"]["amount"], n["basis"]["unit"]))
        facts.extend([fact("nutrientObservation", path, q),
                      fact("sourceNutrientMetadata", path + ".metadata", {
                          "kind": "structure", "fields": {
                              "sourceMetricId": {"kind": "identifier", "value": key},
                              "definition": {"kind": "text", "value": "Synthetic exact definition " + key},
                              "method": {"kind": "text", "value": "Synthetic method; not a calibrated claim"}}})])
    packet = {"schemaVersion": "offmenu-common/1", "resources": [resource],
              "assertions": facts, "relations": [], "citations": [citation], "translations": []}
    side = derive(packet, contract); side["inputSelection"] = select(1)
    projection = native_projection(record, source, {"sourceId": source, "independentlyAccepted": False})
    restored = restore(packet, projection)
    restored["inputNormalizedSelection"] = select(1)
    restored["inputNativeSelection"] = {"manifestByteSha256": pin("native"),
        "assetKey": "synthetic/native.jsonl.gz", "assetSha256": pin("native-asset"),
        "assetRecordOrdinal": 0, "lineOrdinal": 0, "recordOrdinalInLine": 0}
    product_id = "urn:synthetic:product:1"
    pc = copy.deepcopy(citation); pc.update(id="urn:synthetic:citation:product:1",
                                          originalRecordId="synthetic-product-1", sourcePath="synthetic/product/1")
    product_resource = {"id": product_id, "type": TYPE + "FoodProduct",
                        "scope": copy.deepcopy(SCOPE), "citationIds": [pc["id"]]}
    identifier = {"id": "urn:synthetic:identifier:1", "subjectId": product_id,
                  "propertyId": PROP + "sourceIdentifier", "sourcePath": "data.code",
                  "status": "source-asserted", "scope": copy.deepcopy(SCOPE), "citationIds": [pc["id"]],
                  "value": {"kind": "structure", "fields": {
                      "system": {"kind": "identifier", "value": "synthetic-source-code"},
                      "value": {"kind": "identifier", "value": "0000000000000"}}}}
    edge = {"id": "urn:synthetic:edge:1", "subjectId": product_id,
            "objectId": resource_id, "predicateId": REL + "hasCompositionObservation",
            "sourcePath": "data.nutrientProfileId", "status": "source-asserted",
            "scope": copy.deepcopy(SCOPE), "citationIds": [pc["id"]]}
    result = {"schemaVersion": "offmenu-source-scoped-product-query/1", "sourcePins": pins,
              "acceptedIdentityJoins": 0, "automaticPlanningEligible": False,
              "nutritionAggregationEligible": False, "servedApplicationActivation": False,
              "status": "source-scoped-candidate-context",
              "products": [{"resource": product_resource, "citations": [pc], "identifierEvidence": [identifier],
                            "sourceSelection": select(0), "profiles": [{
                                "resource": resource, "citations": [citation], "sourceEdge": edge,
                                "sourceSelection": select(1), "nutrientContextCandidates": side,
                                "perNutrientBasisCandidates": restored}]}]}
    options = {"include_candidates": True, "expected_source_pins": copy.deepcopy(pins),
               "upstream_code_pins": dict(CODE_PINS), "expected_contract_canonical_sha256": digest(contract)}
    return result, options


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.result, self.options = fixture()
        self.profile = self.result["products"][0]["profiles"][0]

    def run_adapter(self):
        return adapt(self.result, **self.options)

    def records(self):
        return {r["sourcePath"].split(".")[-1]: r for r in self.run_adapter()["records"]}

    def rejected(self):
        with self.assertRaises(EvidenceError):
            self.run_adapter()

    def test_real_retained_producers_supply_four_contexts_three_own_basis_targets(self):
        rows = self.records()
        self.assertEqual(len(rows), 4)
        self.assertEqual(self.profile["perNutrientBasisCandidates"]["matchedNutrientAssertions"], 3)
        self.assertEqual({r["preparation"]["sourceLiteral"] for r in rows.values()}, {"raw", "cooked", None})

    def test_zero_unknown_and_original_source_measurements(self):
        rows = self.records()
        self.assertEqual(rows["energy"]["quantity"]["original"]["value"], 0)
        self.assertEqual(rows["energy"]["quantity"]["valueStatus"], "reported")
        self.assertIsNone(rows["protein"]["quantity"]["original"]["value"])
        self.assertEqual(rows["protein"]["quantity"]["valueStatus"], "unknown")
        self.assertEqual(rows["energy"]["quantity"]["sourceMeasurement"], {"value": 0, "unit": "kJ"})

    def test_finite_alias_candidates_never_convert_magnitude(self):
        rows = self.records()
        self.assertEqual(rows["energy"]["unit"]["originalUnitId"], "urn:offmenu:unit:kj")
        self.assertEqual(rows["energy"]["unit"]["aliasCandidate"]["value"], "urn:offmenu:unit:kJ")
        self.assertEqual(rows["sodium"]["unit"]["aliasCandidate"]["value"], "urn:offmenu:unit:microgram")
        self.assertEqual(rows["sodium"]["quantity"]["original"]["value"], 7)
        self.assertFalse(rows["sodium"]["unit"]["magnitudeConversionPerformed"])

    def test_own_missing_unknown_and_multiple_denominators(self):
        rows = self.records()
        self.assertEqual(rows["energy"]["preparation"]["status"], "source-literal-not-canonicalized")
        self.assertEqual(rows["protein"]["preparation"]["status"], "unknown")
        self.assertEqual(rows["sodium"]["preparation"]["status"], "not-supplied")
        self.assertEqual(rows["fibre"]["denominator"]["value"], 50)
        self.assertEqual(rows["energy"]["denominator"]["value"], 100)
        for row in rows.values():
            self.assertIsNone(row["preparation"]["acceptedCanonicalPreparation"])
            self.assertFalse(row["profileBasisUsedForPreparation"])
        self.assertIn("profile-wide-baked", str(rows["sodium"]["profileReportedBasis"]))

    def test_exact_original_metadata_attribution_and_candidate_status_preserved(self):
        row = self.records()["energy"]
        original = next(a for a in self.profile["nutrientContextCandidates"]["assertions"]
                        if a["sourcePath"].endswith(".energy"))
        self.assertEqual(row["metricMetadata"]["original"], original["value"]["fields"]["sourceMetricMetadata"])
        self.assertEqual(row["provenance"]["citations"], self.profile["citations"])
        self.assertEqual(row["provenance"]["candidateAssertion"], original)
        self.assertEqual(row["evidenceStatus"], "candidate-not-admitted")
        self.assertEqual(row["provenance"]["verification"], "caller-bound")

    def test_opt_in_is_literal_true(self):
        for value in (False, None, 1, "true"):
            self.assertEqual(adapt({}, include_candidates=value)["records"], [])
            self.assertEqual(adapt({}, include_candidates=value)["status"], "candidate-opt-in-required")

    def test_independent_binding_arguments_required(self):
        for key in ("expected_source_pins", "upstream_code_pins", "expected_contract_canonical_sha256"):
            options = dict(self.options); options.pop(key)
            with self.assertRaises(EvidenceError):
                adapt(self.result, **options)

    def test_manifest_code_and_contract_mismatch(self):
        self.result["sourcePins"]["sourceManifestByteSha256"] = "0" * 64
        self.rejected()
        self.setUp(); self.options["upstream_code_pins"]["source_scoped_north_star_consumer.py"] = "0" * 64
        self.rejected()
        self.setUp(); self.options["expected_contract_canonical_sha256"] = "0" * 64
        self.rejected()

    def test_source_selection_asset_and_packet_binding(self):
        for mutate in (
            lambda p: p["sourceSelection"].update(assetSha256="0" * 64),
            lambda p: p["perNutrientBasisCandidates"].update(inputPacketCanonicalSha256="0" * 64),
            lambda p: p["sourceSelection"].update(assetKey="../outside.jsonl.gz"),
        ):
            self.setUp(); mutate(self.profile); self.rejected()

    def test_exact_subject_edge_and_citation_binding(self):
        for mutate in (
            lambda p: p["sourceEdge"].update(objectId="other-profile"),
            lambda p: p["citations"][0].update(sourceId="other-source"),
            lambda p: p["nutrientContextCandidates"]["assertions"][0].update(subjectId="other-profile"),
            lambda p: p["nutrientContextCandidates"]["assertions"][0].update(citationIds=["other-citation"]),
        ):
            self.setUp(); mutate(self.profile); self.rejected()

    def test_quantity_metadata_and_basis_tampering_rejected(self):
        for mutate in (
            lambda p: p["nutrientContextCandidates"]["assertions"][0]["value"]["fields"]["quantity"].update(value=999),
            lambda p: p["nutrientContextCandidates"]["assertions"][0]["value"]["fields"]["sourceMetricMetadata"].update(kind="text"),
            lambda p: p["perNutrientBasisCandidates"]["basisGroups"][0]["sourceBasis"].update(state="invented"),
            lambda p: p["perNutrientBasisCandidates"]["basisGroups"][0]["targets"][0].update(inputAssertionId="other-assertion"),
        ):
            self.setUp(); mutate(self.profile); self.rejected()

    def test_duplicate_ambiguity_rejected(self):
        a = self.profile["nutrientContextCandidates"]["assertions"]
        a.append(copy.deepcopy(a[0])); self.rejected()
        self.setUp()
        g = self.profile["perNutrientBasisCandidates"]["basisGroups"]
        g.append(copy.deepcopy(g[0])); self.rejected()
        self.setUp()
        p = self.result["products"][0]["profiles"]
        p.append(copy.deepcopy(p[0])); self.rejected()

    def test_absent_basis_keeps_every_quantity_and_never_uses_profile_basis(self):
        self.profile["perNutrientBasisCandidates"] = None
        rows = self.records()
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r["preparation"]["status"] == "not-supplied" for r in rows.values()))
        self.assertTrue(all(r["provenance"]["basisMatch"] is None for r in rows.values()))

    def test_absent_context_is_explicitly_unresolved_and_preserves_basis_evidence(self):
        self.profile["nutrientContextCandidates"] = None
        out = self.run_adapter()
        self.assertEqual(out["records"], [])
        self.assertEqual(out["unresolvedProfiles"][0]["reason"], "nutrient-context-not-supplied")
        self.assertEqual(out["unresolvedProfiles"][0]["basisCandidates"], self.profile["perNutrientBasisCandidates"])

    def test_not_found_and_unresolved_identity_have_no_fabricated_links(self):
        self.result.update(status="source-key-not-found", products=[])
        out = self.run_adapter()
        self.assertEqual(out["records"], [])
        for key in ("ingredientRelationships", "recipeRelationships"):
            self.assertEqual(out[key], {"status": "not-supplied-by-this-caller", "identities": None})
        self.assertEqual(out["confidence"], {"status": "not-calibrated", "probability": None})
        for key in ("publicationEligible", "automaticPlanningEligible", "nutritionAggregationEligible",
                    "servedApplicationActivation"):
            self.assertIs(out[key], False)

    def test_input_immutability_and_output_isolation(self):
        original = canonical(self.result); options = canonical(self.options)
        out = self.run_adapter()
        self.assertEqual(original, canonical(self.result)); self.assertEqual(options, canonical(self.options))
        out["records"][0]["provenance"]["citations"][0]["license"] = "changed output"
        self.assertEqual(original, canonical(self.result))

    def test_determinism_under_repeat_and_context_order(self):
        first = canonical(self.run_adapter())
        self.assertEqual(first, canonical(self.run_adapter()))
        self.profile["nutrientContextCandidates"]["assertions"].reverse()
        self.assertEqual(first, canonical(self.run_adapter()))

    def test_nonfinite_and_malformed_evidence_rejected(self):
        self.profile["resource"]["untrustedExtra"] = float("nan"); self.rejected()
        self.setUp(); del self.profile["citations"]; self.rejected()


    def rehash_context(self, assertion):
        body = {k: v for k, v in assertion.items() if k not in ("id", "confidence")}
        assertion["id"] = "urn:offmenu:derivation:" + digest([
            "north-star-structural-derivations/2", "nutrient-context",
            sorted(assertion["derivation"]["inputAssertionIds"]), body])

    def rehash_basis(self):
        side = self.profile["perNutrientBasisCandidates"]
        side["id"] = "urn:offmenu:derivation:" + digest({
            k: v for k, v in side.items()
            if k not in ("id", "inputNativeSelection", "inputNormalizedSelection")})

    def test_rehashed_quantity_path_and_digest_mismatch_still_rejected(self):
        for field in ("quantity", "path", "digest"):
            self.setUp()
            a = next(a for a in self.profile["nutrientContextCandidates"]["assertions"]
                     if a["sourcePath"].endswith(".energy"))
            if field == "quantity":
                a["value"]["fields"]["quantity"]["value"] = 999
                a["value"]["fields"]["unknownValue"]["value"] = False
            elif field == "path":
                a["sourcePath"] += ".invented"
            else:
                aid = next(t["inputAssertionId"] for g in self.profile["perNutrientBasisCandidates"]["basisGroups"]
                           for t in g["targets"] if t["sourcePath"].endswith(".energy.basis"))
                a["derivation"]["inputDigests"][aid] = "0" * 64
            self.rehash_context(a)
            self.rejected()

    def test_rehashed_duplicate_target_and_denominator_mismatch_rejected(self):
        g = self.profile["perNutrientBasisCandidates"]["basisGroups"][0]
        g["targets"].append(copy.deepcopy(g["targets"][0]))
        self.rehash_basis(); self.rejected()
        self.setUp()
        g = self.profile["perNutrientBasisCandidates"]["basisGroups"][0]
        g["sourceBasis"]["amount"] = 999
        g["sourceBasisCanonicalSha256"] = digest(g["sourceBasis"])
        self.rehash_basis(); self.rejected()

    def test_rehashed_unrecognized_alias_and_false_as_zero_rejected(self):
        a = self.profile["nutrientContextCandidates"]["assertions"][0]
        a["value"]["fields"]["canonicalUnitCandidate"] = {"kind": "identifier", "value": "invented"}
        self.rehash_context(a); self.rejected()
        self.setUp()
        a = next(a for a in self.profile["nutrientContextCandidates"]["assertions"]
                 if a["value"]["fields"]["quantity"]["value"] == 0)
        a["value"]["fields"]["unknownValue"]["value"] = 0
        self.rehash_context(a); self.rejected()

    def test_basis_target_without_context_rejected_instead_of_dropped(self):
        a = self.profile["nutrientContextCandidates"]["assertions"]
        a[:] = [row for row in a if not row["sourcePath"].endswith(".energy")]
        self.rejected()

    def test_producer_candidate_identifier_status_preserved(self):
        self.result["products"][0]["identifierEvidence"][0]["status"] = "candidate"
        out = self.run_adapter()
        self.assertEqual(out["productEvidence"][0]["identifierEvidence"][0]["status"], "candidate")

    def test_upstream_authenticity_is_explicit_prerequisite_not_hash_authentication(self):
        # Coherently substituted metadata cannot be authenticated without the
        # original assertion bytes. This is intentionally a caller-bound layer.
        a = self.profile["nutrientContextCandidates"]["assertions"][0]
        a["value"]["fields"]["sourceMetricMetadata"]["fields"]["definition"]["value"] = "caller-supplied literal"
        self.rehash_context(a)
        out = self.run_adapter()
        self.assertEqual(out["verification"], "caller-bound-not-independent-byte-verification")
        self.assertTrue(all(r["provenance"]["originalAssertionBodiesAvailable"] is False
                            for r in out["records"]))


if __name__ == "__main__":
    unittest.main()
