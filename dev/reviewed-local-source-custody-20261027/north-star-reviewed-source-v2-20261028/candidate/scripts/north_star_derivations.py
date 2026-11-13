#!/usr/bin/env python3
"""Additive, evidence-bearing candidates over unchanged common/1 packets.

This is NOT a common package publisher, identity resolver, recipe admission
service, or nutrition calculator. It uses only explicit, source-scoped input
edges and exact subject/path evidence joins. No network or provider calls.
"""
import copy
import hashlib
import json
from collections import Counter

VERSION = "north-star-structural-derivations/2"
REL = "urn:offmenu:relation:"
PROP = "urn:offmenu:property:"
TYPE = "urn:offmenu:type:"
USABLE = {"source-asserted", "candidate", "editor-authored", "reviewed", "verified", "unknown"}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _id(rule, inputs, value):
    return "urn:offmenu:derivation:" + digest([VERSION, rule, sorted(inputs), value])


def _index(rows, label):
    result = {}
    for row in rows:
        if row["id"] in result:
            raise ValueError("duplicate " + label + " identity")
        result[row["id"]] = row
    return result


def derive(packet, contract):
    """Return candidates; keep the input byte-equivalent as a Python value.

    Caller must supply schema-validated normalized packets, an exact selected
    contract and its own source-use authority. This operation does not confer
    publication rights. All IDs and dependency digests bind the selected input.
    Missing external endpoints remain unqualified until input-graph resolution.
    """
    if packet.get("schemaVersion") != "offmenu-common/1":
        raise ValueError("only selected common/1 packets are supported")
    resources = _index(packet["resources"], "resource")
    assertions = _index(packet["assertions"], "assertion")
    relations = _index(packet["relations"], "relation")
    citations = _index(packet["citations"], "citation")
    out = {
        "schemaVersion": "offmenu-north-star-derivations/1",
        "rulesetVersion": VERSION,
        "inputPacketCanonicalSha256": digest(packet),
        "contractCanonicalSha256": digest(contract),
        "status": "candidate-not-admitted",
        "publicationEligible": False,
        "automaticPlanningEligible": False,
        "nutritionAggregationEligible": False,
        "identityEffect": "none",
        "confidence": {"status": "not-calibrated", "probability": None},
        "assertions": [], "relations": [], "issues": [],
        "sourceCoverage": {
            "resourceTypes": dict(sorted(Counter(r["type"] for r in resources.values()).items())),
            "relationPredicates": dict(sorted(Counter(r["predicateId"] for r in relations.values()).items())),
            "servedConsumerQueries": None,
        },
    }

    def issue(code, subject, inputs):
        out["issues"].append({"code": code, "subjectId": subject,
                              "inputIds": sorted(inputs), "status": "unresolved"})

    def evidence(inputs):
        scopes = [item["scope"] for item in inputs]
        citation_ids = sorted({c for item in inputs for c in item["citationIds"]})
        if not citation_ids or any(c not in citations for c in citation_ids):
            raise ValueError("missing original citation")
        scopes.extend(citations[c]["scope"] for c in citation_ids)
        scopes.extend(resources[item["subjectId"]]["scope"] for item in inputs)
        # No widening or cross-owner combination. A policy owner can later
        # authorize a less restrictive projection; this pure layer cannot.
        if any(scope != scopes[0] for scope in scopes):
            raise ValueError("mixed citation/resource/assertion scopes")
        if scopes[0].get("visibility") == "private" and not scopes[0].get("ownerId"):
            raise ValueError("private owner required")
        return citation_ids, copy.deepcopy(scopes[0])

    def inputs_ok(inputs):
        for item in inputs:
            if item["subjectId"] not in resources:
                raise ValueError("input subject is not in selected packet")
            if item["status"] not in USABLE:
                issue("input-status-not-usable", item["subjectId"], [item["id"]])
                return False
        return True

    def derivation(rule, facts=(), edges=()):
        return {"methodId": "urn:offmenu:method:" + VERSION + ":" + rule,
                "inputAssertionIds": sorted(x["id"] for x in facts),
                "inputRelationIds": sorted(x["id"] for x in edges),
                "reviewStatus": "candidate",
                "inputDigests": {x["id"]: digest(x) for x in [*facts, *edges]}}

    # Exact predicate projection only. No text/identifier equality, sameAs,
    # culinary usability, dietary qualification or nutrient equivalence rule.
    structural_rules = {
        REL + "hasCompositionObservation": ("product-profile-edge", False, {TYPE + "FoodProduct"}),
        REL + "hasMetricObservation": ("profile-metric-edge", False, {TYPE + "FoodCompositionObservation"}),
        REL + "observesFood": ("food-profile-inverse", True, {TYPE + "FoodConcept", TYPE + "FoodPreparation"}),
    }
    for edge in relations.values():
        rule = structural_rules.get(edge["predicateId"])
        if not rule or not inputs_ok([edge]):
            continue
        name, reverse, expected_subject_types = rule
        subject, target = ((edge["objectId"], edge["subjectId"]) if reverse else
                           (edge["subjectId"], edge["objectId"]))
        citation_ids, scope = evidence([edge])
        for endpoint in (subject, target):
            if endpoint in resources and resources[endpoint]["scope"] != scope:
                raise ValueError("relation endpoint scope differs")
        target_type = resources.get(target, {}).get("type")
        subject_type = resources.get(subject, {}).get("type")
        if subject_type is not None and subject_type not in expected_subject_types:
            issue("composition-subject-type-mismatch", subject, [edge["id"]])
            continue
        if target_type is not None and target_type != TYPE + "FoodCompositionObservation":
            issue("composition-target-type-mismatch", subject, [edge["id"]])
            continue
        if subject not in resources or target not in resources:
            issue("input-graph-endpoint-resolution-required", subject, [edge["id"]])
        candidate = {"subjectId": subject, "predicateId": REL + "hasNutrientObservation",
                     "objectId": target, "status": "candidate", "citationIds": citation_ids,
                     "scope": scope, "sourcePath": edge["sourcePath"],
                     "derivation": derivation(name, edges=[edge]),
                     "expectedSubjectTypes": sorted(expected_subject_types),
                     "expectedObjectType": TYPE + "FoodCompositionObservation",
                     "endpointResolution": "packet-resolved" if subject in resources and target in resources else "input-graph-required"}
        candidate["id"] = _id(name, [edge["id"]], candidate)
        out["relations"].append(candidate)

    metadata = {}
    source_fields = {}
    for fact in assertions.values():
        if fact["propertyId"] == PROP + "sourceNutrientMetadata":
            key = (fact["subjectId"], fact["sourcePath"])
            metadata.setdefault(key, []).append(fact)
        if fact["propertyId"] == PROP + "sourceFields":
            source_fields.setdefault(fact["subjectId"], []).append(fact)

    registered_units = {u["id"] for u in contract["units"].values()}
    for fact in assertions.values():
        if fact["propertyId"] != PROP + "nutrientObservation":
            continue
        subject, path = fact["subjectId"], fact["sourcePath"]
        matches = metadata.get((subject, path + ".metadata"), [])
        if len(matches) != 1:
            issue("unique-nutrient-metadata-required", subject, [fact["id"]])
            continue
        meta = matches[0]
        if not inputs_ok([fact, meta]):
            continue
        if set(fact["citationIds"]) != set(meta["citationIds"]):
            issue("nutrient-context-source-citations-differ", subject, [fact["id"], meta["id"]])
            continue
        quantity = fact["value"]
        if quantity.get("kind") != "quantity" or meta["value"].get("kind") != "structure":
            issue("nutrient-context-shape-mismatch", subject, [fact["id"], meta["id"]])
            continue
        citation_ids, scope = evidence([fact, meta])
        basis = quantity.get("basis")
        state_markers = [v for v in (basis or {}).get("qualifiers", []) if v.startswith("state:")]
        state_known = bool((basis or {}).get("preparationStateId") or state_markers)
        if not state_known:
            issue("preparation-basis-not-carried-in-quantity", subject, [fact["id"], meta["id"]])
        if quantity.get("unitId") not in registered_units:
            issue("unit-definition-not-in-selected-contract", subject, [fact["id"]])
        # Value, null, range, trace/limit and unit/basis remain exact source
        # values. Metadata is joined, never interpreted as a calibrated claim.
        fields = {"quantity": copy.deepcopy(quantity),
                  "sourceMetricMetadata": copy.deepcopy(meta["value"]),
                  "unknownValue": {"kind": "boolean", "value": quantity.get("value") is None},
                  "preparationBasisCarried": {"kind": "boolean", "value": state_known},
                  "comparability": {"kind": "identifier", "value": "not-qualified"}}
        inputs = [fact, meta]
        profile_fields = source_fields.get(subject, [])
        if len(profile_fields) == 1:
            profile = profile_fields[0]
            profile_basis = profile["value"].get("fields", {}).get("basis")
            if profile_basis is not None and inputs_ok([profile]) and set(profile["citationIds"]) == set(fact["citationIds"]):
                evidence([fact, meta, profile])
                fields["profileReportedBasis"] = copy.deepcopy(profile_basis)
                fields["profileBasisQualifiesNutrientPreparation"] = {"kind": "boolean", "value": False}
                inputs.append(profile)
        # Exact unit-symbol alias projection, not a magnitude conversion. Keep
        # original q.unitId/sourceUnit unchanged and label the projection as a
        # candidate. A profile basis never supplies a nutrient's missing state.
        unit_aliases = {
            ("urn:offmenu:unit:kj", "kJ", "energy"): "urn:offmenu:unit:kJ",
            ("urn:offmenu:unit:kj", "kj", "energy"): "urn:offmenu:unit:kJ",
            ("urn:offmenu:unit:ug", "mcg", "mass"): "urn:offmenu:unit:microgram",
            ("urn:offmenu:unit:ug", "µg", "mass"): "urn:offmenu:unit:microgram",
        }
        alias = unit_aliases.get((quantity.get("unitId"), quantity.get("sourceUnit"), quantity.get("dimension")))
        if alias in registered_units:
            fields["canonicalUnitCandidate"] = {"kind": "identifier", "value": alias}
            fields["unitAliasRule"] = {"kind": "identifier", "value": "urn:offmenu:method:exact-unit-symbol-alias/1"}
        candidate = {"subjectId": subject,
                     "propertyId": PROP + "source-field:north-star-nutrient-context",
                     "value": {"kind": "structure", "fields": fields},
                     "status": "candidate", "citationIds": citation_ids,
                     "sourcePath": path, "scope": scope,
                     "derivation": derivation("exact-subject-path-nutrient-context", facts=inputs)}
        candidate["id"] = _id("nutrient-context", [item["id"] for item in inputs], candidate)
        out["assertions"].append(candidate)

    for row in [*out["assertions"], *out["relations"]]:
        row["confidence"] = {"status": "not-calibrated", "probability": None}
    for key in ("assertions", "relations"):
        out[key].sort(key=lambda row: row["id"])
    out["issues"].sort(key=lambda row: (row["code"], row["subjectId"], row["inputIds"]))
    return out


def query_candidates(sidecar, subject_id, *, include_candidates=False):
    """Explicit opt-in diagnostic query, never an accepted runtime lookup."""
    if include_candidates is not True:
        return {"status": "candidate-opt-in-required", "assertions": [], "relations": []}
    return {"status": "candidate-only-not-serving-proof",
            "assertions": [a for a in sidecar["assertions"] if a["subjectId"] == subject_id],
            "relations": [r for r in sidecar["relations"] if r["subjectId"] == subject_id]}
