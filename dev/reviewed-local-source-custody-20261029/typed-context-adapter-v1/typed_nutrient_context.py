"""Pure, offline typed view over the retained source-scoped candidate caller.

No file, database, network, publication, or inference operations. Hash comparisons
bind supplied evidence; upstream reader byte verification remains a prerequisite.
"""
from copy import deepcopy
import hashlib
import json
import re
from pathlib import PurePosixPath

SCHEMA = "offmenu-typed-nutrient-context/1"
PROP = "urn:offmenu:property:"
TYPE = "urn:offmenu:type:"
REL = "urn:offmenu:relation:"
DERIVATIONS = "north-star-structural-derivations/2"
BASIS = "north-star-per-nutrient-basis-restoration/1"
CODE_PINS = {
    "source_scoped_north_star_consumer.py": "75a43f30967c2ea38606e0a1468132629a51b9c79744eed71938a5e1d146b3bc",
    "north_star_derivations.py": "fee258de07319fd19c0032701ea2731afabc1f560eb69c80f111088c65cf0509",
    "north_star_basis_restoration.py": "cae8b86cbacdbf0d81b9a52bb508dadae56e29639cfd332f87fb2b71bd18566a",
}
PIN_KEYS = {"sourceManifestByteSha256", "bulkDerivedManifestByteSha256",
            "basisDerivedManifestByteSha256"}
ALIASES = {
    ("urn:offmenu:unit:kj", "kJ", "energy"): "urn:offmenu:unit:kJ",
    ("urn:offmenu:unit:kj", "kj", "energy"): "urn:offmenu:unit:kJ",
    ("urn:offmenu:unit:ug", "mcg", "mass"): "urn:offmenu:unit:microgram",
    ("urn:offmenu:unit:ug", "µg", "mass"): "urn:offmenu:unit:microgram",
}
CONFIDENCE = {"status": "not-calibrated", "probability": None}


class EvidenceError(ValueError):
    """Reject inconsistent/ambiguous supplied evidence; never partially admit it."""


def canonical(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, RecursionError) as exc:
        raise EvidenceError("finite JSON evidence required") from exc


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def sha(value):
    require(isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value),
            "SHA256 binding required")
    return value


def text(value):
    require(isinstance(value, str) and bool(value), "nonempty identity/path required")
    return value


def unique(values, label):
    require(isinstance(values, list) and all(isinstance(v, str) and v for v in values),
            label + " identity list required")
    require(len(values) == len(set(values)), "ambiguous duplicate " + label)
    return set(values)


def selection(value, source_pin, native=False):
    expected = {"manifestByteSha256", "assetKey", "assetSha256"}
    expected |= {"assetRecordOrdinal", "lineOrdinal", "recordOrdinalInLine"} if native else {"packetOrdinal"}
    require(isinstance(value, dict) and set(value) == expected, "selection shape differs")
    sha(value["manifestByteSha256"]); sha(value["assetSha256"])
    if source_pin is not None:
        require(value["manifestByteSha256"] == source_pin, "source manifest differs")
    path = text(value["assetKey"])
    pp = PurePosixPath(path)
    require(not pp.is_absolute() and ".." not in pp.parts and str(pp) == path,
            "canonical relative asset key required")
    for key in expected - {"manifestByteSha256", "assetKey", "assetSha256"}:
        require(type(value[key]) is int and value[key] >= 0, "nonnegative source ordinal required")


def no_admission(value, *, confidence=True):
    for key in ("publicationEligible", "automaticPlanningEligible", "nutritionAggregationEligible"):
        require(value.get(key) is False, "candidate admission boundary differs")
    require(value.get("identityEffect") == "none", "identity effect differs")
    if confidence:
        require(value.get("confidence") == CONFIDENCE, "confidence must remain not-calibrated")


def derivation(value, method):
    require(isinstance(value, dict) and value.get("methodId") == method
            and value.get("reviewStatus") == "candidate", "derivation method/status differs")
    ids = unique(value.get("inputAssertionIds"), "input assertion")
    require(ids and set(value.get("inputDigests", {})) == ids,
            "assertion digest inventory differs")
    for pin in value["inputDigests"].values():
        sha(pin)
    require(value.get("inputRelationIds", []) == [], "unexpected nutrient relation inputs")
    return ids


def citation_context(item, kind, seen):
    r = item["resource"]
    require(r["type"] == TYPE + kind, "resource type differs")
    text(r["id"])
    require(r["scope"].get("visibility") == "public", "public caller context required")
    citations = item["citations"]
    require(isinstance(citations, list) and len(citations) == 1, "single source citation required")
    c = citations[0]
    require(r["citationIds"] == [c["id"]] and c["scope"] == r["scope"],
            "resource citation/scope differs")
    for key in ("id", "sourceId", "originalRecordId", "contentSha256", "license", "sourcePath"):
        text(c[key])
    require(c.get("revisionId") is not None and str(c["revisionId"]), "source release required")
    sha(c["contentSha256"])
    for obj in (r, c):
        previous = seen.setdefault(obj["id"], obj)
        require(previous == obj, "conflicting source identity")
    return r, c


def row_context(row, subject, citation, scope):
    require(row["subjectId"] == subject and row["citationIds"] == [citation]
            and row["scope"] == scope, "exact subject/citation/scope differs")
    text(row["id"]); text(row["sourcePath"])


def basis_index(side, profile, source_pin, packet_pin):
    if side is None:
        return {}
    require(side["schemaVersion"] == "offmenu-nutrient-basis-derivations/1"
            and side["rulesetVersion"] == BASIS
            and side["status"] == "candidate-not-admitted"
            and side["evidenceKind"] == "copied-same-source-per-nutrient-basis",
            "basis candidate contract differs")
    r = profile["resource"]
    require(side["subjectId"] == r["id"] and side["scope"] == r["scope"]
            and side["citationIds"] == r["citationIds"], "basis subject/citation differs")
    no_admission(side)
    require(side["profileBasisUsed"] is False and side["originalQuantityModified"] is False,
            "basis may not replace original quantity or use profile basis")
    require(side["inputNormalizedSelection"] == profile["sourceSelection"],
            "basis source selection differs")
    selection(side["inputNormalizedSelection"], source_pin)
    selection(side["inputNativeSelection"], None, native=True)
    for key in ("inputPacketCanonicalSha256", "inputNativeRecordCanonicalSha256",
                "sourceCurationCanonicalSha256", "sourceEntryCanonicalSha256"):
        sha(side[key])
    if packet_pin is not None:
        require(side["inputPacketCanonicalSha256"] == packet_pin, "sidecar packet digests differ")
    ids = derivation(side["derivation"], "urn:offmenu:method:" + BASIS)
    body = {k: v for k, v in side.items()
            if k not in ("id", "inputNativeSelection", "inputNormalizedSelection")}
    require(side["id"] == "urn:offmenu:derivation:" + digest(body), "basis candidate ID differs")
    result, group_ids = {}, set()
    for group in side["basisGroups"]:
        b = group["sourceBasis"]
        require(isinstance(b, dict) and "state" in b
                and (b["state"] is None or isinstance(b["state"], str)),
                "own preparation literal required")
        pin = sha(group["sourceBasisCanonicalSha256"])
        require(pin == digest(b) and pin not in group_ids, "ambiguous/tampered basis group")
        group_ids.add(pin)
        require(group["stateStatus"] == ("unknown" if b["state"] is None
                                        else "source-literal-not-canonicalized"),
                "basis state status differs")
        require(group["targets"], "empty basis group")
        for target in group["targets"]:
            aid = text(target["inputAssertionId"])
            require(aid in ids and aid not in result, "ambiguous/unbound basis target")
            for key in ("nativeMetricCanonicalSha256", "originalQuantityCanonicalSha256"):
                sha(target[key])
            text(target["sourcePath"])
            result[aid] = (group, target)
    require(result and type(side["matchedNutrientAssertions"]) is int
            and side["matchedNutrientAssertions"] == len(result), "basis target count differs")
    # The retained producer includes exactly one original-record assertion as well.
    require(len(ids - set(result)) == 1, "basis original-record dependency differs")
    return result


def adapt(caller_result, *, include_candidates=False, expected_source_pins=None,
          upstream_code_pins=None, expected_contract_canonical_sha256=None):
    """Return deterministic candidate records; raise EvidenceError on inconsistency.

    Bindings must come from the trusted consumer's reviewed selection, separately
    from the result. They are not signatures or fresh source-file verification.
    """
    output = {
        "schemaVersion": SCHEMA, "status": "candidate-opt-in-required",
        "verification": "caller-bound-not-independent-byte-verification",
        "acceptedIdentityJoins": 0, "publicationEligible": False,
        "automaticPlanningEligible": False, "nutritionAggregationEligible": False,
        "servedApplicationActivation": False, "identityEffect": "none",
        "confidence": deepcopy(CONFIDENCE),
        "ingredientRelationships": {"status": "not-supplied-by-this-caller", "identities": None},
        "recipeRelationships": {"status": "not-supplied-by-this-caller", "identities": None},
        "records": [], "unresolvedProfiles": [], "productEvidence": [], "profileEvidence": [],
    }
    if include_candidates is not True:
        return output
    try:
        # Finite JSON and bounded result; do not inspect any referenced files.
        require(len(canonical(caller_result)) <= 16 * 1024 * 1024, "caller result exceeds 16 MiB")
        require(isinstance(expected_source_pins, dict) and set(expected_source_pins) == PIN_KEYS,
                "separately supplied exact manifest bindings required")
        for pin in expected_source_pins.values():
            sha(pin)
        require(upstream_code_pins == CODE_PINS, "reviewed upstream code bindings required")
        sha(expected_contract_canonical_sha256)
        require(caller_result["sourcePins"] == expected_source_pins, "caller source pins differ")
        require(caller_result["schemaVersion"] == "offmenu-source-scoped-product-query/1",
                "caller schema differs")
        require(type(caller_result["acceptedIdentityJoins"]) is int
                and caller_result["acceptedIdentityJoins"] == 0, "caller identity boundary differs")
        for key in ("automaticPlanningEligible", "nutritionAggregationEligible", "servedApplicationActivation"):
            require(caller_result[key] is False, "caller admission boundary differs")
        status = caller_result["status"]
        statuses = {"source-scoped-candidate-context", "source-product-without-resolved-profile",
                    "source-key-not-found", "ambiguous-source-product-key", "candidates-not-requested"}
        require(status in statuses, "caller status differs")
        products = caller_result["products"]
        require(isinstance(products, list) and len(products) <= 1, "single source product required")
        require(bool(products) == (status in {"source-scoped-candidate-context",
                                             "source-product-without-resolved-profile"}),
                "caller status/product mismatch")
        output.update(status="candidate-only-not-serving-proof", callerStatus=status,
                      sourcePins=deepcopy(expected_source_pins), upstreamCodePins=deepcopy(upstream_code_pins),
                      contractCanonicalSha256=expected_contract_canonical_sha256)
        seen, profile_ids = {}, set()
        for product in products:
            pr, pc = citation_context(product, "FoodProduct", seen)
            selection(product["sourceSelection"], expected_source_pins["sourceManifestByteSha256"])
            identifiers = product["identifierEvidence"]
            require(identifiers, "exact product identifier evidence required")
            unique([a["id"] for a in identifiers], "identifier assertion")
            for a in identifiers:
                row_context(a, pr["id"], pc["id"], pr["scope"])
                require(a["propertyId"] == PROP + "sourceIdentifier", "identifier property differs")
                require(a["status"] in {"source-asserted", "candidate", "editor-authored", "reviewed", "verified"},
                        "identifier status differs")
                fields = a["value"]["fields"]
                text(fields["system"]["value"]); text(fields["value"]["value"])
                require(seen.setdefault(a["id"], a) == a, "conflicting identifier identity")
            output["productEvidence"].append({k: deepcopy(product[k]) for k in
                    ("resource", "citations", "identifierEvidence", "sourceSelection")})
            profiles = product["profiles"]
            require(isinstance(profiles, list) and len(profiles) <= 256, "bounded profiles required")
            require(bool(profiles) == (status == "source-scoped-candidate-context"),
                    "caller status/profile mismatch")
            for profile in profiles:
                r, c = citation_context(profile, "FoodCompositionObservation", seen)
                require(r["id"] not in profile_ids, "ambiguous duplicate profile")
                profile_ids.add(r["id"])
                require((c["sourceId"], str(c["revisionId"])) == (pc["sourceId"], str(pc["revisionId"])),
                        "product/profile source release differs")
                require(r["scope"] == pr["scope"], "product/profile scope differs")
                selection(profile["sourceSelection"], expected_source_pins["sourceManifestByteSha256"])
                edge = profile["sourceEdge"]
                row_context(edge, pr["id"], pc["id"], pr["scope"])
                require(edge["predicateId"] == REL + "hasCompositionObservation"
                        and edge["objectId"] == r["id"], "product/profile edge differs")
                require(seen.setdefault(edge["id"], edge) == edge, "conflicting profile edge identity")
                context = profile["nutrientContextCandidates"]
                basis = profile["perNutrientBasisCandidates"]
                basis_pin = digest(basis) if basis is not None else None
                targets = basis_index(basis, profile, expected_source_pins["sourceManifestByteSha256"],
                                      context["inputPacketCanonicalSha256"] if context else None)
                output["profileEvidence"].append({
                    "profileId": r["id"], "resource": deepcopy(r),
                    "citations": deepcopy(profile["citations"]),
                    "sourceSelection": deepcopy(profile["sourceSelection"]),
                    "basisDerivation": deepcopy(basis),
                    "upstreamIssues": deepcopy(context["issues"]) if context else None,
                    "contextPacketCanonicalSha256": context["inputPacketCanonicalSha256"] if context else None})
                if context is None:
                    output["unresolvedProfiles"].append({
                        "profileId": r["id"], "reason": "nutrient-context-not-supplied",
                        "basisCandidates": deepcopy(basis), "sourceSelection": deepcopy(profile["sourceSelection"]),
                        "citations": deepcopy(profile["citations"])})
                    continue
                require(context["schemaVersion"] == "offmenu-north-star-derivations/1"
                        and context["rulesetVersion"] == DERIVATIONS
                        and context["status"] == "candidate-not-admitted", "context contract differs")
                no_admission(context)
                require(context["contractCanonicalSha256"] == expected_contract_canonical_sha256,
                        "context contract pin differs")
                require(context["inputSelection"] == profile["sourceSelection"], "context source selection differs")
                sha(context["inputPacketCanonicalSha256"])
                assertions = context["assertions"]
                require(isinstance(assertions, list) and len(assertions) <= 16384, "bounded nutrient records required")
                unique([a["id"] for a in assertions], "context assertion")
                paths, consumed = set(), set()
                for a in assertions:
                    row_context(a, r["id"], c["id"], r["scope"])
                    require(a["sourcePath"] not in paths, "ambiguous duplicate nutrient path")
                    paths.add(a["sourcePath"])
                    require(a["propertyId"] == PROP + "source-field:north-star-nutrient-context"
                            and a["status"] == "candidate" and a["confidence"] == CONFIDENCE,
                            "nutrient candidate contract differs")
                    inputs = derivation(a["derivation"], "urn:offmenu:method:" + DERIVATIONS
                                        + ":exact-subject-path-nutrient-context")
                    body = {k: v for k, v in a.items() if k not in ("id", "confidence")}
                    require(a["id"] == "urn:offmenu:derivation:" + digest(
                        [DERIVATIONS, "nutrient-context", sorted(inputs), body]), "context candidate ID differs")
                    require(len(inputs) in (2, 3), "nutrient input role inventory differs")
                    require(a["value"]["kind"] == "structure", "structured nutrient context required")
                    fields = a["value"]["fields"]; q = fields["quantity"]
                    require(q["kind"] == "quantity" and "value" in q and "sourceValue" in q
                            and "sourceUnit" in q and "unitId" in q and "dimension" in q,
                            "original quantity/source measurement required")
                    require(q["value"] is None or type(q["value"]) in (int, float), "numeric or unknown quantity required")
                    require(fields["sourceMetricMetadata"]["kind"] == "structure", "source metadata structure required")
                    require(type(fields["unknownValue"]["value"]) is bool
                            and fields["unknownValue"] == {"kind": "boolean", "value": q["value"] is None},
                            "unknown quantity flag differs")
                    state_carried = bool((q.get("basis") or {}).get("preparationStateId") or [
                        v for v in (q.get("basis") or {}).get("qualifiers", []) if v.startswith("state:")])
                    require(type(fields["preparationBasisCarried"]["value"]) is bool
                            and fields["preparationBasisCarried"] == {"kind": "boolean", "value": state_carried}
                            and fields["comparability"] == {"kind": "identifier", "value": "not-qualified"},
                            "preparation/comparability flag differs")
                    alias = fields.get("canonicalUnitCandidate")
                    if alias is not None:
                        require(alias == {"kind": "identifier", "value": ALIASES.get(
                            (q["unitId"], q["sourceUnit"], q["dimension"]))}
                            and alias["value"] is not None
                            and fields.get("unitAliasRule") == {"kind": "identifier",
                                "value": "urn:offmenu:method:exact-unit-symbol-alias/1"},
                            "finite unit alias binding differs")
                    else:
                        require("unitAliasRule" not in fields, "orphan unit alias rule")
                    if "profileReportedBasis" in fields:
                        require(fields.get("profileBasisQualifiesNutrientPreparation")
                                == {"kind": "boolean", "value": False}, "profile basis may not qualify preparation")
                    matching = inputs & set(targets)
                    require(len(matching) <= 1, "ambiguous nutrient assertion basis")
                    preparation = {"status": "not-supplied", "sourceLiteral": None,
                                   "acceptedCanonicalPreparation": None}
                    matched = None
                    if matching:
                        aid = next(iter(matching)); group, target = targets[aid]
                        require(aid not in consumed, "basis target reused")
                        require(target["sourcePath"] == a["sourcePath"] + ".basis"
                                and target["originalQuantityCanonicalSha256"] == digest(q)
                                and basis["derivation"]["inputDigests"][aid] == a["derivation"]["inputDigests"][aid],
                                "exact assertion/path/quantity basis binding differs")
                        own = group["sourceBasis"]
                        denominator = q.get("basis")
                        require(isinstance(denominator, dict)
                                and denominator.get("sourceValue") == own.get("amount")
                                and denominator.get("sourceUnit") == (own.get("unit") or None),
                                "own source denominator differs")
                        require("state" not in denominator and "preparationStateId" not in denominator,
                                "restored preparation may not replace original state")
                        preparation.update(status=group["stateStatus"], sourceLiteral=own["state"])
                        matched = {"inputAssertionId": aid, "group": {k: deepcopy(v) for k, v in group.items() if k != "targets"},
                                   "target": deepcopy(target), "sidecarId": basis["id"]}
                        consumed.add(aid)
                    record = {
                        "productId": pr["id"], "profileId": r["id"], "sourcePath": a["sourcePath"],
                        "quantity": {"evidenceKind": "copied-source-assertion-value",
                                     "original": deepcopy(q),
                                     "sourceMeasurement": {"value": deepcopy(q["sourceValue"]),
                                                           "unit": deepcopy(q["sourceUnit"])},
                                     "valueStatus": "unknown" if q["value"] is None else "reported"},
                        "metricMetadata": {"evidenceKind": "copied-source-assertion-value",
                                           "original": deepcopy(fields["sourceMetricMetadata"])},
                        "unit": {"originalUnitId": q["unitId"], "originalSourceUnit": deepcopy(q["sourceUnit"]),
                                 "aliasCandidate": deepcopy(alias), "magnitudeConversionPerformed": False},
                        "denominator": deepcopy(q.get("basis")),
                        "preparation": preparation,
                        "profileReportedBasis": deepcopy(fields.get("profileReportedBasis")),
                        "profileBasisUsedForPreparation": False,
                        "evidenceStatus": "candidate-not-admitted",
                        "provenance": {
                            "scope": deepcopy(r["scope"]), "citations": deepcopy(profile["citations"]),
                            "productEvidenceId": pr["id"], "profileEvidenceId": r["id"], "sourceEdge": deepcopy(edge),
                            "productSelection": deepcopy(product["sourceSelection"]),
                            "profileSelection": deepcopy(profile["sourceSelection"]),
                            "inputPacketCanonicalSha256": context["inputPacketCanonicalSha256"],
                            "candidateAssertion": deepcopy(a), "basisMatch": matched,
                            "basisDerivation": {"id": basis["id"], "canonicalSha256": basis_pin} if matched else None,
                            "verification": "caller-bound",
                            "originalAssertionBodiesAvailable": False,
                            "originalAssertionStatus": "not-exposed-by-caller",
                        },
                    }
                    record["id"] = "urn:offmenu:typed-nutrient-context:" + digest(record)
                    output["records"].append(record)
                require(consumed == set(targets), "basis target has no exact nutrient context")
                if not assertions:
                    output["unresolvedProfiles"].append({
                        "profileId": r["id"], "reason": "no-returned-nutrient-context-assertions",
                        "upstreamIssues": deepcopy(context["issues"])})
        output["productEvidence"].sort(key=lambda item: item["resource"]["id"])
        output["profileEvidence"].sort(key=lambda item: item["profileId"])
        output["records"].sort(key=lambda row: row["id"])
        output["unresolvedProfiles"].sort(key=lambda row: row["profileId"])
        return output
    except EvidenceError:
        raise
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise EvidenceError("malformed caller evidence") from exc
