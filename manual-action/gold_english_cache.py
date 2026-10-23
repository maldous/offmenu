"""Local English derivation cache, explicitly invoked by the gold writer.

No provider, path discovery, filesystem connection, commit, or automatic retry.
The caller owns the supplied SQLite connection and transaction. Qualification
checks evidence bindings, not whether a cited source actually supports a claim;
the builder and independent acceptance retain that responsibility.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3

REQUEST_SCHEMA = "offmenu-gold-english-cache-request/1"
RESPONSE_SCHEMA = "offmenu-gold-english-cache-response/1"
EVIDENCE_SCHEMA = "offmenu-gold-english-cache-evidence/1"
TABLE = "gold_english_cache_entries"
MAX_BYTES = 262144
MAX_VARIANTS = 100
DOMAINS = {"barcodes", "ingredients", "recipes", "dietary", "suppliers", "citations"}
KINDS = {"translation", "correction", "inference", "estimate", "unit-normalization"}
HEX = re.compile(r"[0-9a-f]{64}\Z")


class CacheError(ValueError):
    """A bounded diagnostic, never a source body or arbitrary exception string."""


def canonical_bytes(value):
    """Exact JSON content identity, preserving Unicode and array order."""
    remaining = 10000

    def walk(x, depth=0):
        nonlocal remaining
        remaining -= 1
        if depth > 32 or remaining < 0:
            raise CacheError("content_limit")
        if x is None or isinstance(x, bool) or type(x) is int:
            return
        if type(x) is float:
            if not math.isfinite(x):
                raise CacheError("nonfinite_number")
        elif isinstance(x, str):
            if len(x) > MAX_BYTES:
                raise CacheError("content_limit")
        elif isinstance(x, list):
            if len(x) > 256:
                raise CacheError("content_limit")
            for item in x:
                walk(item, depth + 1)
        elif isinstance(x, dict):
            if len(x) > 256 or any(not isinstance(k, str) for k in x):
                raise CacheError("invalid_object")
            for key, item in x.items():
                walk(key, depth + 1)
                walk(item, depth + 1)
        else:
            raise CacheError("non_json_content")

    walk(value)
    try:
        blob = json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise CacheError("invalid_json_content") from exc
    if len(blob) > MAX_BYTES:
        raise CacheError("content_limit")
    return blob


def content_digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def request_key(request):
    """Pure identity; a key alone never establishes eligibility."""
    return content_digest(request)


def _text(x):
    return isinstance(x, str) and bool(x.strip()) and x.strip().casefold() not in {"unknown", "unavailable", "unexposed"}


def _hash(x):
    return isinstance(x, str) and HEX.fullmatch(x) is not None


def _pin(x):
    return isinstance(x, dict) and _text(x.get("id")) and _hash(x.get("sha256"))


def _unique_strings(x, nonempty=True):
    return isinstance(x, list) and (bool(x) or not nonempty) and all(_text(i) for i in x) and len(set(x)) == len(x)


def qualify_request(request):
    """Return held reasons for absent pins; never discover or copy permissions."""
    try:
        canonical_bytes(request)
        if not isinstance(request, dict) or request.get("schemaVersion") != REQUEST_SCHEMA:
            return ["request_schema"]
        source, scope, rights = request.get("source"), request.get("scope"), request.get("rights")
        if not isinstance(source, dict) or not all(_text(source.get(k)) for k in ("sourceId", "recordId", "recordSelector", "locale")):
            return ["source_binding"]
        if not all(_hash(source.get(k)) for k in ("originalSHA256", "parsedArtifactSHA256")) or not _text(source.get("releaseId")):
            return ["source_content_pin"]
        if not isinstance(scope, dict) or scope.get("domain") not in DOMAINS or not _text(scope.get("entityId")) or not _text(scope.get("fieldPointer")):
            return ["scope_binding"]
        if not _unique_strings(scope.get("observationIds"), False) or not isinstance(scope.get("context"), dict):
            return ["context_binding"]
        if request.get("operation") not in KINDS or request.get("targetLocale") != "en":
            return ["operation_locale"]
        if not isinstance(rights, dict) or rights.get("state") != "permitted" or rights.get("operation") != request["operation"] or not _pin(rights.get("evidencePin")):
            return ["operation_rights"]
        if rights.get("sourceBinding") != source or rights.get("scope") != scope:
            return ["rights_scope_mismatch"]
        if not _pin(request.get("eligibleManifestPin")):
            return ["eligibility_pin"]
        data = request.get("inputContent")
        if not isinstance(data, dict) or not isinstance(data.get("originalText"), str) or not isinstance(data.get("citations"), list):
            return ["input_content"]
        if data.get("dataClass") not in {"synthetic", "real-qualified"}:
            return ["input_data_class"]
        if content_digest(data) != request.get("inputContentSHA256"):
            return ["input_content_digest"]
        cites = data["citations"]
        if not cites or any(not isinstance(c, dict) or not _text(c.get("citationId")) or not _pin(c.get("evidencePin")) for c in cites):
            return ["citation_input"]
        if len({c["citationId"] for c in cites}) != len(cites):
            return ["duplicate_citation_id"]
        producer, prompt = request.get("producer"), request.get("prompt")
        if not isinstance(producer, dict) or producer.get("kind") not in {"ai", "deterministic", "human"} or not all(_text(producer.get(k)) for k in ("id", "version")) or not isinstance(producer.get("settings"), dict):
            return ["producer_pins"]
        if not isinstance(prompt, dict) or not _text(prompt.get("version")) or not isinstance(prompt.get("content"), str) or hashlib.sha256(prompt["content"].encode("utf-8")).hexdigest() != prompt.get("sha256"):
            return ["prompt_pins"]
        if not all(_text(request.get(k)) for k in ("adapterVersion", "outputSchemaVersion", "rulesVersion")):
            return ["version_pins"]
        tools = request.get("toolingActuallyUsed", [])
        if not isinstance(tools, list) or any(not _pin(t) for t in tools):
            return ["tooling_pin"]
        return []
    except (CacheError, UnicodeError, RecursionError):
        return ["invalid_or_overlimit_request"]


def qualify_entry(request, response, validation):
    """Plain result: qualified evidence or an explicit held result, no I/O."""
    errors = qualify_request(request)
    if errors:
        return {"state": "held", "reasons": errors}
    try:
        key, response_hash = request_key(request), content_digest(response)
        if not isinstance(response, dict) or response.get("schemaVersion") != RESPONSE_SCHEMA or response.get("kind") != request["operation"]:
            raise CacheError("response_schema_operation")
        allowed = {"schemaVersion", "kind", "originalText", "englishText", "observationIds", "context", "citationIds", "uncertainty", "derivation", "correction"}
        if set(response) != allowed or not _text(response.get("englishText")) or not isinstance(response.get("uncertainty"), str):
            raise CacheError("response_fields")
        if response["originalText"] != request["inputContent"]["originalText"] or response["observationIds"] != request["scope"]["observationIds"] or response["context"] != request["scope"]["context"]:
            raise CacheError("original_context_changed")
        ids = response["citationIds"]
        if not _unique_strings(ids) or not set(ids) <= {c["citationId"] for c in request["inputContent"]["citations"]}:
            raise CacheError("unsupported_citation")
        kind, derivation = response["kind"], response["derivation"]
        if kind in {"translation", "correction"}:
            if derivation is not None:
                raise CacheError("translation_as_fact")
        else:
            if not isinstance(derivation, dict) or derivation.get("type") != {"inference": "culinary-inference", "estimate": "derived-estimate", "unit-normalization": "unit-normalization"}[kind]:
                raise CacheError("derivation_type")
            if set(derivation) - {"type", "label", "method", "basis", "uncertainty", "inputContentSHA256", "supportingCitationIds", "assertedField", "observedFact", "value", "unit", "supportingObservationIds"}:
                raise CacheError("derivation_fields")
            if not all(_text(derivation.get(k)) for k in ("label", "method", "basis", "uncertainty")) or derivation.get("inputContentSHA256") != request["inputContentSHA256"]:
                raise CacheError("derivation_basis")
            if derivation.get("assertedField") not in ({"culinary-interpretation"} if kind == "inference" else {"nutrient-estimate"} if kind == "estimate" else {"comparable-unit"}):
                raise CacheError("unsupported_factual_inference")
            if not _unique_strings(derivation.get("supportingCitationIds")) or not set(derivation["supportingCitationIds"]) <= set(ids):
                raise CacheError("derivation_citations")
            if derivation.get("observedFact") is not False:
                raise CacheError("derivation_as_observation")
            if "supportingObservationIds" in derivation and (not _unique_strings(derivation["supportingObservationIds"]) or not set(derivation["supportingObservationIds"]) <= set(request["scope"]["observationIds"])):
                raise CacheError("derivation_observations")
            if "value" in derivation:
                value = derivation["value"]
                if kind == "inference" or not isinstance(value, str) or re.fullmatch(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?", value) is None or not _text(derivation.get("unit")):
                    raise CacheError("derived_value_unit")
        correction = response["correction"]
        if kind == "correction":
            if not isinstance(correction, dict) or not _hash(correction.get("parentResponseSHA256")) or not _text(correction.get("reason")):
                raise CacheError("correction_lineage")
        elif correction is not None:
            raise CacheError("unexpected_correction")
        canonical_bytes(validation)
        if not isinstance(validation, dict) or validation.get("state") != "passed" or validation.get("requestKey") != key or validation.get("responseSHA256") != response_hash or not _pin(validation.get("evidencePin")) or not _text(validation.get("validatorId")):
            raise CacheError("validation_binding")
        if validation.get("unsupportedFacts") is not False:
            raise CacheError("unsupported_facts_not_cleared")
        evidence = {"schemaVersion": EVIDENCE_SCHEMA, "state": "validated-cache-evidence",
                    "dataClass": request["inputContent"]["dataClass"],
                    "requestKey": key, "responseSHA256": response_hash,
                    "source": request["source"], "scope": request["scope"],
                    "rights": request["rights"], "eligibleManifestPin": request["eligibleManifestPin"],
                    "kind": kind, "targetLocale": "en", "originalText": response["originalText"],
                    "englishText": response["englishText"], "citationIds": ids,
                    "derivation": derivation, "correction": correction,
                    "producer": request["producer"], "prompt": request["prompt"],
                    "inputContentSHA256": request["inputContentSHA256"],
                    "versions": {k: request[k] for k in ("adapterVersion", "outputSchemaVersion", "rulesVersion")},
                    "uncertainty": response["uncertainty"], "validation": validation,
                    "goldAdmission": "not-assigned-by-cache"}
        # No references to mutable caller objects escape a qualified result.
        return {"state": "qualified", "reasons": [], "evidence": json.loads(canonical_bytes(evidence))}
    except (CacheError, UnicodeError, RecursionError) as exc:
        return {"state": "held", "reasons": [str(exc) if isinstance(exc, CacheError) else "invalid_entry"]}


def initialize_cache(connection):
    """Explicit writer hook. Caller chooses and owns the connection/transaction."""
    if not isinstance(connection, sqlite3.Connection):
        raise CacheError("explicit_sqlite_connection_required")
    connection.execute(f"CREATE TABLE IF NOT EXISTS {TABLE} (entry_key TEXT PRIMARY KEY, request_key TEXT NOT NULL, response_sha256 TEXT NOT NULL, request_json TEXT NOT NULL, response_json TEXT NOT NULL, validation_json TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('qualified','held')))")
    connection.execute(f"CREATE INDEX IF NOT EXISTS gold_english_cache_request_idx ON {TABLE}(request_key)")


def store_cached(connection, request, response, validation):
    """Append an immutable variant, including held attempts; never commit."""
    qualified = qualify_entry(request, response, validation)
    try:
        blobs = [canonical_bytes(v).decode("utf-8") for v in (request, response, validation)]
        key, response_hash = request_key(request), content_digest(response)
        entry_key = content_digest({"requestKey": key, "responseSHA256": response_hash,
                                    "validationSHA256": content_digest(validation)})
        connection.execute(f"INSERT OR IGNORE INTO {TABLE} VALUES (?,?,?,?,?,?,?)",
                           (entry_key, key, response_hash, *blobs, qualified["state"]))
        return {**qualified, "entryKey": entry_key, "requestKey": key}
    except CacheError:
        return {"state": "held", "reasons": ["unpersistable_attempt"]}


def _decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise CacheError("duplicate_cached_key")
            result[key] = value
        return result
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_BYTES:
        raise CacheError("cached_content_limit")
    try:
        value = json.loads(raw, object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(CacheError("nonfinite_cached_json")))
        canonical_bytes(value)
        return value
    except (ValueError, RecursionError, UnicodeError) as exc:
        raise CacheError("invalid_cached_json") from exc


def lookup_cached(connection, request, *, entry_key=None):
    """Current binding supplied independently; a miss never invokes a model."""
    errors = qualify_request(request)
    if errors:
        return {"state": "held", "reasons": errors}
    key = request_key(request)
    try:
        rows = connection.execute(f"SELECT entry_key,response_sha256,request_json,response_json,validation_json,state FROM {TABLE} WHERE request_key=? ORDER BY entry_key LIMIT ?", (key, MAX_VARIANTS + 1)).fetchall()
    except sqlite3.OperationalError as exc:
        if str(exc) == f"no such table: {TABLE}":
            return {"state": "miss", "reasons": ["cache_uninitialized"], "requestKey": key}
        return {"state": "held", "reasons": ["cache_read_error"], "requestKey": key}
    if len(rows) > MAX_VARIANTS:
        return {"state": "held", "reasons": ["variant_limit"]}
    if entry_key is not None:
        rows = [row for row in rows if row[0] == entry_key]
    if not rows:
        return {"state": "miss", "reasons": [], "requestKey": key}
    qualified, held = [], []
    for stored_key, stored_hash, rq, rs, va, state in rows:
        try:
            cached_request, response, validation = map(_decode, (rq, rs, va))
            if canonical_bytes(cached_request) != canonical_bytes(request) or content_digest(response) != stored_hash:
                raise CacheError("poisoned_binding")
            expected = content_digest({"requestKey": key, "responseSHA256": stored_hash,
                                       "validationSHA256": content_digest(validation)})
            if expected != stored_key:
                raise CacheError("poisoned_entry_key")
            result = qualify_entry(request, response, validation)
            if state == "qualified" and result["state"] == "qualified":
                qualified.append({**result, "entryKey": stored_key})
            else:
                held.append(stored_key)
        except CacheError:
            return {"state": "held", "reasons": ["poisoned_cache_entry"]}
    if not qualified:
        return {"state": "held", "reasons": ["no_qualified_variant"], "heldEntryKeys": held}
    if len({q["evidence"]["responseSHA256"] for q in qualified}) > 1:
        return {"state": "held", "reasons": ["multiple_qualified_variants"], "entryKeys": [q["entryKey"] for q in qualified]}
    chosen = qualified[0]
    return {**chosen, "state": "hit", "requestKey": key, "heldEntryKeys": held}
