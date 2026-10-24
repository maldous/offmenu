"""Bounded, pure comparison of caller-qualified historical compatibility evidence.

There is deliberately no authority loader or runtime activation path here.
See SOURCE-RECIPE-PRODUCT-PROOFS.md for the caller's trust obligations.
"""
from dataclasses import dataclass
import hashlib
import json
import math
import re

PURPOSE = "HISTORICAL_SOURCE_DECLARATION_COMPATIBILITY_ONLY"
MAX_INPUT_BYTES = 524288
MAX_OUTPUT_BYTES = 262144
MAX_DEPTH = 32
MAX_NODES = 100000
SHA = re.compile(r"[0-9a-f]{64}\Z")


class InvalidInput(ValueError):
    """Malformed or over-budget input; the entire batch is rejected."""


class Held(ValueError):
    """A claim has insufficient qualified evidence."""


def _bounded(value, byte_limit=MAX_INPUT_BYTES):
    # Inspect before serialization, including cycles, finite numbers and types.
    stack = [(value, 0, frozenset())]
    nodes = size = 0
    while stack:
        obj, depth, parents = stack.pop()
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            raise InvalidInput("node/depth limit")
        t = type(obj)
        if t in (dict, list):
            if id(obj) in parents:
                raise InvalidInput("cyclic input")
            parents = parents | {id(obj)}
            if nodes + len(stack) + len(obj) * (2 if t is dict else 1) > MAX_NODES:
                raise InvalidInput("node limit")
            size += 2 + len(obj)
            if t is dict:
                for k, v in obj.items():
                    if type(k) is not str:
                        raise InvalidInput("non-string key")
                    stack.append((k, depth + 1, parents))
                    stack.append((v, depth + 1, parents))
            else:
                stack.extend((v, depth + 1, parents) for v in obj)
        elif t is str:
            try:
                size += len(obj.encode("utf-8")) + 2
            except UnicodeError as exc:
                raise InvalidInput("invalid UTF8") from exc
        elif t is float:
            if not math.isfinite(obj):
                raise InvalidInput("non-finite number")
            size += 8
        elif t is int:
            if obj.bit_length() > byte_limit * 3:
                raise InvalidInput("oversized integer")
            size += max(1, obj.bit_length() // 4)
        elif t is bool or obj is None:
            size += 4
        else:
            raise InvalidInput("non-JSON type")
        if size > byte_limit:
            raise InvalidInput("byte limit")
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise InvalidInput("unencodable JSON") from exc
    if len(encoded) > byte_limit:
        raise InvalidInput("byte limit")
    return encoded


def canonical_sha256(value):
    return hashlib.sha256(_bounded(value)).hexdigest()


def _same(left, right):
    # Python equality conflates False/0 and True/1; receipts require JSON types.
    return _bounded(left) == _bounded(right)


def parse_json(text):
    """Strict bounded JSON boundary: duplicate keys and NaN never become facts."""
    if type(text) is not str:
        raise InvalidInput("JSON text required")
    try:
        if len(text.encode("utf-8")) > MAX_INPUT_BYTES:
            raise InvalidInput("byte limit")
        def pairs(items):
            out = {}
            for key, value in items:
                if key in out:
                    raise InvalidInput("duplicate JSON key")
                out[key] = value
            return out
        def constant(_):
            raise InvalidInput("non-finite number")
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
        _bounded(value)
        return value
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise InvalidInput(str(exc)) from exc


@dataclass(frozen=True)
class AlternativeRules:
    """Trusted existing typed-group functions, never supplied in source JSON."""
    relation_condition: object
    alternative_group_valid: object


@dataclass(frozen=True)
class CallerReviewContext:
    """Only the existing accepted-review/custody caller may construct this."""
    snapshot: dict
    accepted: list
    artifacts: dict
    facts: dict
    rules: AlternativeRules


def _require(ok, reason):
    if not ok:
        raise Held(reason)


def _digest(value):
    return type(value) is str and SHA.fullmatch(value) is not None


def _claim_pins(value):
    if type(value) is dict:
        for key, child in value.items():
            if key.lower().endswith("sha256"):
                _require(_digest(child), "malformed claim digest")
            else:
                _claim_pins(child)
    elif type(value) is list:
        for child in value:
            _claim_pins(child)


def _pointer(value, pointer):
    _require(type(pointer) is str and (pointer == "" or pointer.startswith("/")),
             "invalid evidence pointer")
    if pointer == "":
        return value
    for part in pointer[1:].split("/"):
        _require(re.search(r"~(?![01])", part) is None, "invalid pointer escape")
        part = part.replace("~1", "/").replace("~0", "~")
        if type(value) is list:
            _require(re.fullmatch(r"0|[1-9][0-9]*", part) is not None,
                     "invalid array pointer")
            value = value[int(part)]
        else:
            _require(type(value) is dict, "missing evidence row")
            value = value[part]
    return value


def _resolved(ref, artifacts):
    _require(type(ref) is dict and set(ref) == {"artifactSHA256", "pointer", "rowSHA256"},
             "invalid evidence reference")
    _require(_digest(ref["artifactSHA256"]) and _digest(ref["rowSHA256"]), "invalid digest")
    raw = artifacts[ref["artifactSHA256"]]
    _require(type(raw) is str and hashlib.sha256(raw.encode("utf-8")).hexdigest()
             == ref["artifactSHA256"], "artifact mismatch")
    row = _pointer(parse_json(raw), ref["pointer"])
    _require(canonical_sha256(row) == ref["rowSHA256"], "row mismatch")
    _require(type(row) is dict, "structured receipt required")
    return row


def _index(rows):
    _require(type(rows) is list, "row list required")
    out = {}
    for row in rows:
        _require(type(row) is dict and type(row.get("id")) is str
                 and row["id"] and row["id"] not in out, "duplicate/missing row ID")
        out[row["id"]] = row
    return out


def _supports(row, citations, purpose):
    supports = row["supports"]
    _require(type(supports) is list and supports, "missing support")
    # Every caller-qualified required support is included in the custody-bound
    # fact bundle. Do not infer its absence from a selected path.
    required = row["requiredSupportIds"]
    indexed = _index(supports)
    _require(type(required) is list and len(set(required)) == len(required)
             and set(required) == set(indexed), "incomplete support closure")
    for support in supports:
        _require(support["targetId"] == row["id"] and support["state"] == "verified",
                 "unsupported target")
        _require(support["kind"] in ("record", "field", "relationship"), "support kind")
        if support["kind"] == "field":
            actual = _pointer(row["payload"], support["pointer"])
        else:
            actual = row["payload"]
        _require(_digest(support["valueSHA256"]) and
                 canonical_sha256(actual) == support["valueSHA256"], "support value mismatch")
        citation = citations[support["citationId"]]
        _require(citation["state"] == "verified" and citation["allowedPurpose"] == purpose,
                 "citation purpose/state")
        _require(citation["payload"]["visibility"] in ("public", "private")
                 and citation["payload"].get("license") and
                 citation["payload"].get("attribution"), "citation rights missing")


def _closure(claim, facts, rules):
    _require(_same(facts["claim"], claim), "fact claim mismatch")
    purpose = claim["purpose"]
    citations = _index(facts["citations"])
    for cite in claim["sourceCitations"]:
        actual = citations[cite["id"]]
        _require(canonical_sha256(actual["payload"]) == cite["payloadSHA256"],
                 "citation payload mismatch")
        for key in ("visibility", "license", "attribution"):
            _require(actual["payload"][key] == cite[key], "citation binding mismatch")
    endpoints = _index(facts["endpoints"])
    _require(len(endpoints) == 4, "four exact endpoints required")
    for role, key in (("source", "sourceOccurrence"), ("mention", "mention"),
                      ("class", "class"), ("product", "product")):
        row = endpoints[role]
        _require(row["state"] == "verified" and _same(row["binding"], claim[key]),
                 "endpoint state/binding mismatch")
        _require(row["resourceState"] == "verified" and
                 row["occurrenceState"] == "verified", "resource/occurrence held")
        _require(_digest(row["payloadSHA256"]) and
                 canonical_sha256(row["payload"]) == row["payloadSHA256"], "endpoint payload")
        pointers = row["bindingPointers"]
        _require(type(pointers) is dict and set(pointers) == set(claim[key]),
                 "missing endpoint field binding")
        for field, expected in claim[key].items():
            _require(_same(_pointer(row["payload"], pointers[field]), expected),
                     "endpoint field value mismatch")
        _supports(row, citations, purpose)
    relations = _index(facts["relations"])
    expected_edges = {
        "mentions": (endpoints["source"]["entityId"], claim["mention"]["entityId"]),
        "canonical_ingredient": (claim["mention"]["entityId"], claim["class"]["entityId"]),
        "represents": (claim["product"]["entityId"], claim["class"]["entityId"]),
    }
    _require(len(claim["relations"]) == 3 and
             {r["predicate"] for r in claim["relations"]} == set(expected_edges),
             "exact three-edge path required")
    for edge in claim["relations"]:
        row = relations[edge["relationId"]]
        _require(row["state"] == "verified" and
                 canonical_sha256(row["payload"]) == edge["payloadSHA256"], "relation mismatch")
        _require(row["payload"]["predicateId"] == edge["predicate"], "predicate mismatch")
        _require((row["payload"]["subjectId"], row["payload"]["objectId"]) ==
                 expected_edges[edge["predicate"]], "relation endpoint mismatch")
        _require(set(edge["citationIds"]) == {s["citationId"] for s in row["supports"]},
                 "relation citation closure")
        _supports(row, citations, purpose)
    group = facts["canonicalGroup"]
    _require(type(group) is list and group, "missing complete canonical group")
    group_rows = _index(group)
    qualification = facts["groupQualification"]
    _require(qualification["complete"] is True and
             qualification["memberIds"] == sorted(group_rows) and
             qualification["groupSHA256"] == canonical_sha256(group), "group closure")
    scope = {k: claim["sourceOccurrence"][k] for k in
             ("recipeId", "mentionId", "sourceKey", "sourceVersion", "recordId", "contentSha256")}
    _require(qualification["sourceScope"] == scope, "stale group scope")
    payloads = []
    for row in group:
        payload = row["payload"]
        _require(payload["subjectId"] == claim["mention"]["entityId"] and
                 payload["predicateId"] == "canonical_ingredient", "foreign group endpoint")
        _require(row["state"] in ("verified", "held"), "unknown declaration state")
        _supports(row, citations, purpose)
        payloads.append(payload)
    _require(rules.alternative_group_valid(payloads) is True, "invalid canonical group")
    selected = [r for r in group if r["payload"]["objectId"] == claim["class"]["entityId"]]
    _require(len(selected) == 1 and selected[0]["state"] == "verified", "canonical target held")
    selected = selected[0]
    _require(selected["id"] in relations and selected == relations[selected["id"]],
             "canonical edge not in exact claim path")
    conditions = [rules.relation_condition(p) for p in payloads]
    if any(c is not None for c in conditions):
        _require(all(type(c) is dict and c["sourceScope"] == scope for c in conditions),
                 "stale conditional scope")
        choice = facts["selection"]
        condition = rules.relation_condition(selected["payload"])
        _require(type(choice) is dict and choice == condition, "unselected/conflicting branch")
    else:
        _require(len(group) == 1 and facts["selection"] is None, "ambiguous unconditional group")


def _assess(claim, ctx):
    _claim_pins(claim)
    claim_sha = canonical_sha256(claim)
    _require(claim["purpose"] == PURPOSE, "unsupported purpose")
    facts = ctx["facts"][claim_sha]
    proofs = [p for p in ctx["accepted"] if p.get("claimSHA256") == claim_sha]
    _require(len(proofs) == 1, "missing/conflicting accepted review")
    proof = proofs[0]
    row = _resolved(proof["review"], ctx["artifacts"])
    custody = _resolved(proof["custody"], ctx["artifacts"])
    expected = {"claimSHA256": claim_sha, "purpose": PURPOSE,
                "snapshot": ctx["snapshot"], "constraints": facts["constraints"],
                "factsSHA256": canonical_sha256(facts),
                "authorThreadId": proof["authorThreadId"],
                "reviewerThreadId": proof["reviewerThreadId"],
                "disposition": "active", "conflicts": [], "revoked": False}
    _require(type(expected["authorThreadId"]) is str and expected["authorThreadId"]
             and type(expected["reviewerThreadId"]) is str and expected["reviewerThreadId"]
             and expected["authorThreadId"] != expected["reviewerThreadId"], "review independence")
    _require(_same(row, expected), "review binding/disposition mismatch")
    _require(_same(custody, {"review": proof["review"], "binding": expected,
                            "disposition": "accepted"}), "custody mismatch")
    _require(type(facts["constraints"]) is dict and facts["constraints"], "missing constraints")
    _closure(claim, facts, ctx["rules"])


def assess(request, *, trusted_context):
    """Return historical comparisons only. Batch errors never return positives.

    Callers must use parse_json for external JSON; Python dicts must already
    have passed that boundary. Unknown event-shaped request keys grant nothing.
    """
    try:
        if type(trusted_context) is not CallerReviewContext:
            raise InvalidInput("caller-owned typed context required")
        if type(trusted_context.rules) is not AlternativeRules:
            raise InvalidInput("trusted existing group rules required")
        if (type(request) is dict and type(request.get("claims")) is list
                and len(request["claims"]) > 5):
            raise InvalidInput("claim limit")
        if type(trusted_context.accepted) is list and len(trusted_context.accepted) > 100:
            raise InvalidInput("proof row limit")
        raw = {"request": request, "snapshot": trusted_context.snapshot,
               "accepted": trusted_context.accepted, "artifacts": trusted_context.artifacts,
               "facts": trusted_context.facts}
        # Validate and snapshot mutable caller dictionaries in one bounded pass.
        frozen = json.loads(_bounded(raw))
        ctx = {**frozen, "rules": trusted_context.rules}
        request = frozen["request"]
        if type(request) is not dict or type(request.get("claims")) is not list:
            raise InvalidInput("claims list required")
        claims = request["claims"]
        if len(claims) > 5 or type(ctx["accepted"]) is not list or len(ctx["accepted"]) > 100:
            raise InvalidInput("claim/proof row limit")
        if type(ctx["snapshot"]) is not dict or set(ctx["snapshot"]) != {"admissionSHA256", "databaseSHA256"}:
            raise InvalidInput("snapshot pins required")
        if not all(_digest(v) for v in ctx["snapshot"].values()):
            raise InvalidInput("invalid snapshot digest")
        for rows in (claims, ctx["accepted"]):
            ids = [r.get("id") if type(r) is dict else None for r in rows]
            if any(type(i) is not str or not i for i in ids) or len(set(ids)) != len(ids):
                raise InvalidInput("duplicate/missing claim or proof ID")
        if type(ctx["facts"]) is not dict or type(ctx["artifacts"]) is not dict:
            raise InvalidInput("fact/artifact maps required")
        results = []
        for envelope in claims:
            claim = envelope.get("claim")
            result = {"id": envelope["id"], "historicalCompatibility": "held",
                      "actualSelection": "unobserved", "currentStateFit": None,
                      "actualRecipeComposition": None, "productFitAcceptance": False,
                      "existingProductFitAcceptance": False,
                      "compositionReadiness": "held", "preparedYieldG": None,
                      "servings": None,
                      "compositionGaps": {name: "unobserved" for name in
                          ("actualProductUse", "currentFormulation", "asUsedIngredientMasses",
                           "preparationStateIncludingSoftening", "processingRetention",
                           "measuredOutputMass", "measuredServings")},
                      "restrictions": ["actual use, preparation and output unobserved",
                                       "no mass inferred from volume/count or missing ingredients",
                                       "no actual composition authority in v1"]}
            try:
                _assess(claim, ctx)
                result["historicalCompatibility"] = "qualified"
                result["reason"] = "exact caller-qualified historical declaration only"
            except (Held, KeyError, IndexError, TypeError, ValueError) as exc:
                result["reason"] = str(exc)[:160]
            results.append(result)
        output = {"outcome": "assessed", "purpose": PURPOSE, "results": results}
        _bounded(output, MAX_OUTPUT_BYTES)
        return output
    except InvalidInput as exc:
        return {"outcome": "rejected", "reason": str(exc), "results": []}
