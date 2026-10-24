"""Generated-only controls; no source corpus, database or runtime processing."""
import ast
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import source_recipe_product_proofs as m
from gold_builder import alternative_group_valid, relation_condition

RULES = m.AlternativeRules(relation_condition, alternative_group_valid)
SCOPE_KEYS = ("recipeId", "mentionId", "sourceKey", "sourceVersion", "recordId", "contentSha256")


def fixture(number=0):
    suffix = str(number)
    citation = {"id": "cite" + suffix, "payload": {"visibility": "public",
                "license": "generated", "attribution": "generated fixture"},
                "state": "verified", "allowedPurpose": m.PURPOSE}
    claim = {"purpose": m.PURPOSE,
             "sourceOccurrence": {"occurrenceId": "o" + suffix, "recipeId": "r" + suffix,
                 "mentionId": "m" + suffix, "sourceKey": "generated", "sourceVersion": "1",
                 "recordId": suffix, "contentSha256": "a" * 64},
             "mention": {"entityId": "physical-m" + suffix, "resourceId": "m" + suffix},
             "class": {"entityId": "physical-c" + suffix, "resourceId": "c" + suffix},
             "product": {"entityId": "physical-p" + suffix, "resourceId": "p" + suffix},
             "sourceCitations": [{"id": citation["id"],
                 "payloadSHA256": m.canonical_sha256(citation["payload"]), **citation["payload"]}]}
    def row(id_, payload):
        support = {"id": id_ + "-support", "targetId": id_, "kind": "record",
                   "state": "verified", "valueSHA256": m.canonical_sha256(payload),
                   "citationId": citation["id"]}
        return {"id": id_, "payload": payload, "state": "verified", "supports": [support],
                "requiredSupportIds": [support["id"]]}
    endpoints = []
    for role, key in (("source", "sourceOccurrence"), ("mention", "mention"),
                      ("class", "class"), ("product", "product")):
        endpoint = row(role, {"fixture": role + suffix, "binding": copy.deepcopy(claim[key])})
        endpoint.update(binding=copy.deepcopy(claim[key]), resourceState="verified",
                        occurrenceState="verified", payloadSHA256=m.canonical_sha256(endpoint["payload"]))
        endpoint["entityId"] = "physical-r" + suffix if role == "source" else claim[key]["entityId"]
        endpoint["bindingPointers"] = {k: "/binding/" + k for k in claim[key]}
        endpoints.append(endpoint)
    edges = [row("mentions" + suffix, {"subjectId": "r" + suffix, "predicateId": "mentions", "objectId": "m" + suffix}),
             row("canonical" + suffix, {"subjectId": "m" + suffix, "predicateId": "canonical_ingredient", "objectId": "c" + suffix}),
             row("represents" + suffix, {"subjectId": "p" + suffix, "predicateId": "represents", "objectId": "c" + suffix})]
    for edge in edges:
        edge["subjectEntityId"] = "physical-" + edge["payload"]["subjectId"]
        edge["objectEntityId"] = "physical-" + edge["payload"]["objectId"]
        for support in edge["supports"]:
            support["kind"] = "relationship"
    claim["relations"] = [{"relationId": r["id"], "predicate": r["payload"]["predicateId"],
                           "payloadSHA256": m.canonical_sha256(r["payload"]),
                           "citationIds": [citation["id"]]} for r in edges]
    group = [copy.deepcopy(edges[1])]
    facts = {"claim": copy.deepcopy(claim), "endpoints": endpoints, "relations": edges,
             "citations": [citation], "canonicalGroup": group, "selection": None,
             "constraints": {"historicalOnly": True, "softenedButterUnobserved": True},
             "groupQualification": {"complete": True, "memberIds": [group[0]["id"]],
                 "groupSHA256": m.canonical_sha256(group),
                 "sourceScope": {k: claim["sourceOccurrence"][k] for k in SCOPE_KEYS}}}
    request = {"claims": [{"id": "generated-" + suffix, "claim": claim}]}
    ctx = m.CallerReviewContext({"admissionSHA256": "b" * 64, "databaseSHA256": "c" * 64},
                               [], {}, {m.canonical_sha256(claim): facts}, RULES)
    return request, sign(ctx)


def sign(ctx):
    """TEST ONLY: synthetic independent review + owner custody, never real approval."""
    artifacts, accepted = {}, []
    def reference(row):
        raw = json.dumps({"rows": [row]}, ensure_ascii=False)
        sha = hashlib.sha256(raw.encode()).hexdigest()
        artifacts[sha] = raw
        return {"artifactSHA256": sha, "pointer": "/rows/0", "rowSHA256": m.canonical_sha256(row)}
    for sha, facts in ctx.facts.items():
        row = {"claimSHA256": sha, "purpose": m.PURPOSE, "snapshot": ctx.snapshot,
               "constraints": facts["constraints"], "factsSHA256": m.canonical_sha256(facts),
               "authorThreadId": "generated-author", "reviewerThreadId": "generated-reviewer",
               "disposition": "active", "conflicts": [], "revoked": False}
        review = reference(row)
        custody = reference({"review": review, "binding": row, "disposition": "accepted"})
        accepted.append({"id": "generated-proof-" + sha, "claimSHA256": sha,
                         "authorThreadId": row["authorThreadId"], "reviewerThreadId": row["reviewerThreadId"],
                         "review": review, "custody": custody})
    return replace(ctx, accepted=accepted, artifacts=artifacts)


class ProofTests(unittest.TestCase):
    def assert_result(self, request, ctx, historical):
        out = m.assess(request, trusted_context=ctx)
        self.assertEqual(out["outcome"], "assessed", out)
        result = out["results"][0]
        self.assertEqual(result["historicalCompatibility"], historical, result)
        self.assertEqual(result["actualSelection"], "unobserved")
        self.assertIsNone(result["actualRecipeComposition"])
        self.assertIsNone(result["currentStateFit"])
        self.assertIs(result["productFitAcceptance"], False)
        self.assertIsNone(result["preparedYieldG"])
        self.assertIsNone(result["servings"])
        self.assertEqual(result["compositionReadiness"], "held")
        return out

    def test_five_positive_generated_receipts_only(self):
        for n in range(5):
            with self.subTest(n=n):
                r, c = fixture(n)
                self.assert_result(r, c, "qualified")

    def test_thirteen_historical_failure_vectors(self):
        names = ["wrong-product-sibling", "wrong-source-version", "wrong-mention",
                 "wrong-class-definition", "missing-review", "self-approved-receipt",
                 "stale-or-conflicting-review", "private-wrong-purpose-citation",
                 "unsupported-variant", "unselected-alternative", "duplicate-conflicting-branch",
                 "wrong-snapshot-or-rights", "DateSoda-boundary-unrelated"]
        for name in names:
            with self.subTest(vector=name):
                r, c = fixture()
                claim = r["claims"][0]["claim"]
                facts = next(iter(c.facts.values()))
                if name in ("wrong-product-sibling", "unsupported-variant", "DateSoda-boundary-unrelated"):
                    claim["product"]["entityId"] = name
                elif name == "wrong-source-version":
                    claim["sourceOccurrence"]["sourceVersion"] = "stale"
                elif name == "wrong-mention":
                    claim["mention"]["entityId"] = "foreign"
                elif name == "wrong-class-definition":
                    claim["class"]["definitionPayloadSHA256"] = "d" * 64
                elif name == "missing-review":
                    c = replace(c, accepted=[])
                elif name == "self-approved-receipt":
                    c.accepted[0]["reviewerThreadId"] = "generated-author"
                elif name == "stale-or-conflicting-review":
                    c.accepted.append({**c.accepted[0], "id": "conflict"})
                elif name == "private-wrong-purpose-citation":
                    facts["citations"][0]["allowedPurpose"] = "other-purpose"
                    c = sign(c)
                elif name == "unselected-alternative":
                    c = alternative(c, select=False)
                    r["claims"][0]["claim"] = copy.deepcopy(next(iter(c.facts.values()))["claim"])
                elif name == "duplicate-conflicting-branch":
                    c = alternative(c, duplicate=True)
                    r["claims"][0]["claim"] = copy.deepcopy(next(iter(c.facts.values()))["claim"])
                elif name == "wrong-snapshot-or-rights":
                    c = replace(c, snapshot={**c.snapshot, "databaseSHA256": "e" * 64})
                self.assert_result(r, c, "held")

    def test_eight_composition_vectors_preserve_history(self):
        for name in ("barcode-filter-not-observed-use", "household-volume-not-mass", "count-not-mass",
                     "missing-ingredient-not-zero", "input-sum-not-yield", "source-summary-not-serving-proof",
                     "source-label-not-actual-composition", "missing-metric-partial"):
            with self.subTest(vector=name):
                r, c = fixture()
                r["compositionEvidence"] = {"case": name, "actualUseApproved": True,
                    "mass": "4 large eggs", "preparedYieldG": 90, "servings": 6,
                    "generatedCompleteMetrics": 8, "generatedPartialMetrics": 8}
                before = copy.deepcopy(r)
                self.assert_result(r, c, "qualified")
                self.assertEqual(r, before)

    def test_budget_vector_batch_rejects_without_partial_positive(self):
        r, c = fixture()
        r["claims"] *= 6
        self.assertEqual(m.assess(r, trusted_context=c)["results"], [])
        self.assertEqual(m.assess(r, trusted_context=c)["outcome"], "rejected")

    def test_omitted_held_sibling_without_new_custody_is_held(self):
        r, c = fixture()
        sibling = copy.deepcopy(next(iter(c.facts.values()))["canonicalGroup"][0])
        sibling["id"] = "held-sibling"
        sibling["state"] = "held"
        facts = next(iter(c.facts.values()))
        facts["canonicalGroup"].append(sibling)
        c = sign(c)
        facts["canonicalGroup"].pop()  # Selected triple unchanged; closure receipt is now stale.
        self.assert_result(r, c, "held")

    def test_support_endpoint_and_group_failures_even_with_generated_receipt(self):
        for failure in ("missing-support", "field-mismatch", "held-endpoint", "group-list",
                        "mixed", "stale-scope", "bad-target", "citation-payload",
                        "binding-pointer", "endpoint-payload-disconnected", "relation-endpoint"):
            with self.subTest(failure=failure):
                r, c = fixture()
                f = next(iter(c.facts.values()))
                if failure == "missing-support": f["endpoints"][0]["supports"] = []
                elif failure == "field-mismatch": f["endpoints"][0]["supports"][0].update(kind="field", pointer="/fixture", valueSHA256="0"*64)
                elif failure == "held-endpoint": f["endpoints"][1]["occurrenceState"] = "held"
                elif failure == "group-list": f["groupQualification"]["memberIds"] = []
                elif failure == "mixed":
                    c = alternative(c)
                    f = next(iter(c.facts.values()))
                    del f["canonicalGroup"][1]["payload"]["condition"]
                elif failure == "stale-scope": f["groupQualification"]["sourceScope"]["sourceVersion"] = "old"
                elif failure == "bad-target": f["relations"][0]["supports"][0]["targetId"] = "elsewhere"
                elif failure == "citation-payload": f["citations"][0]["payload"]["license"] = "changed"
                elif failure == "binding-pointer": f["endpoints"][0]["bindingPointers"] = {}
                elif failure == "endpoint-payload-disconnected":
                    endpoint = f["endpoints"][1]
                    endpoint["payload"]["binding"]["entityId"] = "foreign"
                    endpoint["payloadSHA256"] = m.canonical_sha256(endpoint["payload"])
                    endpoint["supports"][0]["valueSHA256"] = endpoint["payloadSHA256"]
                elif failure == "relation-endpoint":
                    edge = f["relations"][0]
                    edge["payload"]["objectId"] = "foreign"
                    edge["supports"][0]["valueSHA256"] = m.canonical_sha256(edge["payload"])
                    f["claim"]["relations"][0]["payloadSHA256"] = m.canonical_sha256(edge["payload"])
                    c = replace(c, facts={m.canonical_sha256(f["claim"]): f})
                c = sign(c)
                r["claims"][0]["claim"] = copy.deepcopy(next(iter(c.facts.values()))["claim"])
                self.assert_result(r, c, "held")

    def test_valid_selected_alternative_uses_existing_rules(self):
        r, c = fixture()
        c = alternative(c)
        r["claims"][0]["claim"] = copy.deepcopy(next(iter(c.facts.values()))["claim"])
        self.assert_result(r, c, "qualified")

    def test_independent_healthy_tuple_survives_other_defect(self):
        r, c = fixture(0)
        r2, c2 = fixture(1)
        r["claims"] += r2["claims"]
        c.facts.update(c2.facts)
        c = sign(c)
        r["claims"][1]["claim"]["product"]["entityId"] = "wrong"
        self.assertEqual([x["historicalCompatibility"] for x in m.assess(r, trusted_context=c)["results"]],
                         ["qualified", "held"])

    def test_untrusted_context_override_and_prose_do_not_authorize(self):
        r, c = fixture()
        r.update(trusted_context={"accepted": True}, ownerReceipt={"accepted": True},
                 reviewer="independent", semanticAssessment="accepted", verdict="accept")
        self.assert_result(r, replace(c, accepted=[]), "held")
        self.assertEqual(m.assess(r, trusted_context=r["trusted_context"])["outcome"], "rejected")

    def test_resolved_artifact_pointer_digest_and_disposition(self):
        for failure in ("raw", "pointer", "digest", "revoked", "numeric-false"):
            with self.subTest(failure=failure):
                r, c = fixture()
                proof = c.accepted[0]
                ref = proof["review"]
                if failure == "raw": c.artifacts[ref["artifactSHA256"]] += " "
                elif failure == "pointer": ref["pointer"] = "/missing"
                elif failure == "digest": ref["rowSHA256"] = "0" * 64
                else:
                    row = json.loads(c.artifacts[ref["artifactSHA256"]])["rows"][0]
                    row["revoked"] = True if failure == "revoked" else 0
                    raw = json.dumps({"rows": [row]})
                    sha = hashlib.sha256(raw.encode()).hexdigest()
                    c.artifacts[sha] = raw
                    ref.update(artifactSHA256=sha, rowSHA256=m.canonical_sha256(row))
                self.assert_result(r, c, "held")

    def test_strict_parser_and_canonical_unicode(self):
        for raw in ('{"a":1,"a":2}', '{"a":NaN}', '[' * 40 + '0' + ']' * 40):
            with self.assertRaises(m.InvalidInput): m.parse_json(raw)
        self.assertNotEqual(m.canonical_sha256("é"), m.canonical_sha256("e\u0301"))
        self.assertEqual(m.canonical_sha256({"b": 1, "a": "é"}),
                         hashlib.sha256('{"a":"é","b":1}'.encode()).hexdigest())

    def test_input_bounds_types_duplicates_and_output_cap(self):
        for kind in ("proofs", "bytes", "depth", "nodes", "nan", "cycle", "claim-id", "proof-id", "snapshot-sha", "type"):
            with self.subTest(kind=kind):
                r, c = fixture()
                if kind == "proofs": c = replace(c, accepted=c.accepted * 101)
                elif kind == "bytes": r["extra"] = "x" * 524289
                elif kind == "depth":
                    v = 0
                    for _ in range(33): v = [v]
                    r["extra"] = v
                elif kind == "nodes": r["extra"] = [None] * 100001
                elif kind == "nan": r["extra"] = float("nan")
                elif kind == "cycle": r["extra"] = r
                elif kind == "claim-id": r["claims"] *= 2
                elif kind == "proof-id": c = replace(c, accepted=c.accepted * 2)
                elif kind == "snapshot-sha": c.snapshot["admissionSHA256"] = "B" * 64
                elif kind == "type": r["extra"] = object()
                self.assertEqual(m.assess(r, trusted_context=c)["outcome"], "rejected")
        r, c = fixture()
        with patch.object(m, "MAX_OUTPUT_BYTES", 10):
            self.assertEqual(m.assess(r, trusted_context=c),
                             {"outcome": "rejected", "reason": "byte limit", "results": []})

    def test_module_purity_imports_and_no_hidden_io(self):
        tree = ast.parse(Path(m.__file__).read_text())
        imports = {n.names[0].name for n in ast.walk(tree) if isinstance(n, ast.Import)}
        imports |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        self.assertEqual(imports, {"dataclasses", "hashlib", "json", "math", "re"})
        r, c = fixture()
        with patch("builtins.open", side_effect=AssertionError("unexpected I/O")):
            self.assert_result(r, c, "qualified")

    def test_r1_distinct_namespaces_and_independent_wrong_endpoint_failures(self):
        r, c = fixture()
        self.assert_result(r, c, "qualified")
        for failure in ("logical-subject", "logical-object", "physical-subject", "physical-object",
                        "physical-endpoint-binding", "group-physical-subject"):
            with self.subTest(failure=failure):
                r, c = fixture()
                f = next(iter(c.facts.values()))
                row = f["relations"][0]
                if failure == "logical-subject": row["payload"]["subjectId"] = "foreign-logical"
                elif failure == "logical-object": row["payload"]["objectId"] = "foreign-logical"
                elif failure == "physical-subject": row["subjectEntityId"] = "foreign-physical"
                elif failure == "physical-object": row["objectEntityId"] = "foreign-physical"
                elif failure == "physical-endpoint-binding": f["endpoints"][1]["entityId"] = "foreign-physical"
                elif failure == "group-physical-subject":
                    f["canonicalGroup"][0]["subjectEntityId"] = "foreign-physical"
                    f["groupQualification"]["groupSHA256"] = m.canonical_sha256(f["canonicalGroup"])
                row["supports"][0]["valueSHA256"] = m.canonical_sha256(row["payload"])
                f["claim"]["relations"][0]["payloadSHA256"] = m.canonical_sha256(row["payload"])
                r["claims"][0]["claim"] = copy.deepcopy(f["claim"])
                c = sign(replace(c, facts={m.canonical_sha256(f["claim"]): f}))
                self.assert_result(r, c, "held")

    def test_r2_support_roles_cannot_be_interchanged(self):
        r, c = fixture()
        endpoint = next(iter(c.facts.values()))["endpoints"][0]
        endpoint["supports"][0].update(kind="field", pointer="/binding",
                                      valueSHA256=m.canonical_sha256(endpoint["payload"]["binding"]))
        self.assert_result(r, sign(c), "qualified")
        for failure in ("relation-record", "relation-field", "endpoint-relationship", "declaration-record"):
            with self.subTest(failure=failure):
                r, c = fixture()
                f = next(iter(c.facts.values()))
                row = (f["endpoints"][0] if failure == "endpoint-relationship" else
                       f["canonicalGroup"][0] if failure == "declaration-record" else f["relations"][0])
                support = row["supports"][0]
                support["kind"] = ("relationship" if failure == "endpoint-relationship" else
                                   "field" if failure == "relation-field" else "record")
                if failure == "relation-field":
                    support.update(pointer="/predicateId", valueSHA256=m.canonical_sha256(row["payload"]["predicateId"]))
                f["groupQualification"]["groupSHA256"] = m.canonical_sha256(f["canonicalGroup"])
                self.assert_result(r, sign(c), "held")

    def test_r3_qualified_output_retains_exact_audit_pins_and_constraints(self):
        r, c = fixture()
        f = next(iter(c.facts.values()))
        f["constraints"]["privatePurpose"] = {"scope": "GENERATED_PRIVATE_EXACT_VARIANT_ONLY", "transfer": False}
        c = sign(c)
        out = self.assert_result(r, c, "qualified")["results"][0]
        self.assertEqual(out["claimSHA256"], m.canonical_sha256(r["claims"][0]["claim"]))
        for key in ("snapshot", "review", "custody", "constraints"):
            expected = c.snapshot if key == "snapshot" else f["constraints"] if key == "constraints" else c.accepted[0][key]
            self.assertEqual(out[key], expected)
        self.assertEqual(out["factsSHA256"], m.canonical_sha256(f))
        self.assertEqual(out["sourceRestrictions"], f["constraints"])
        self.assertLess(len(json.dumps(out).encode()), m.MAX_OUTPUT_BYTES)
        for key in ("sourceOccurrence", "mention", "class", "product", "sourceCitations", "relations"):
            self.assertEqual(out["sourcePins"][key], r["claims"][0]["claim"][key])
        # The qualified evidence must never escape the unchanged output cap.
        f["constraints"]["largeReviewedRestriction"] = "x" * 132000
        rejected = m.assess(r, trusted_context=sign(c))
        self.assertEqual(rejected["outcome"], "rejected")
        self.assertEqual(rejected["results"], [])


def alternative(ctx, select=True, duplicate=False):
    f = copy.deepcopy(next(iter(ctx.facts.values())))
    group = f["canonicalGroup"]
    scope = f["groupQualification"]["sourceScope"]
    first = group[0]
    first["payload"]["condition"] = {"kind": "selected-alternative", "groupId": "g",
                                        "branchId": "a", "sourceScope": scope}
    second = copy.deepcopy(first)
    second["id"] = "alternative"
    second["payload"]["objectId"] = "other-class"
    second["objectEntityId"] = "physical-other-class"
    second["payload"]["condition"]["branchId"] = "a" if duplicate else "b"
    second["state"] = "held"  # Declaration retained; not a usable selected path.
    group.append(second)
    for row in group:
        row["supports"][0].update(id=row["id"]+"-support", targetId=row["id"],
                                  valueSHA256=m.canonical_sha256(row["payload"]))
        row["requiredSupportIds"] = [row["supports"][0]["id"]]
    f["relations"][1] = copy.deepcopy(first)
    f["claim"]["relations"][1]["payloadSHA256"] = m.canonical_sha256(first["payload"])
    f["selection"] = copy.deepcopy(first["payload"]["condition"]) if select else None
    f["groupQualification"].update(memberIds=sorted(r["id"] for r in group),
                                  groupSHA256=m.canonical_sha256(group))
    return sign(replace(ctx, facts={m.canonical_sha256(f["claim"]): f}))


if __name__ == "__main__":
    unittest.main()
