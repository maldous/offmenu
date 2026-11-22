"""Read-only row projections for a qualified Foo producer's source-context stream.

This is not an executor. The trusted caller authenticates the queue, producer,
current operation/rights and parser digests, assigns the zero-based ordinal, and
verifies source bytes before invoking it. Row data never grants that authority.
No files, remote calls, translation, unit conversion, entity merges or promotion.
Refusals carry fixed reason codes only; do not log the refused row.
"""
import hashlib
import json
import re
import unicodedata
from copy import deepcopy

CODEC = "typed-exact-decimal-json/1; not an original byte-span hash"
PROVIDERS = {
    "off": ("2026-10-12", "96a192c8d7ec08e4116b9c7b1c8fb77da452a22820656fa43ceef1200c96cfc0"),
    "usda-files": ("2026-04-30", "e648f1d83bb1012e076d43610aa80ed6b811dfa1ff3521d028bcf274923792d9"),
}
IDENTITY = ("sourceId", "releaseId", "recordId", "nativeRecordId", "sourceObservationSha256",
            "sourceDocumentSha256", "inputDatabaseSha256", "sourceQualificationSha256")
DIGEST = re.compile(r"[a-f0-9]{64}")
STAGE = re.compile(r"offmenu:product:[a-f0-9]{24}")
SHARD = re.compile(r"cohort-([0-9]{3})/chunk-([0-9]{5})")
FORBIDDEN = {"private", "household", "restricted", "held", "denied", "blocked", "forbidden"}
NODES = ("sourceAdapterInput", "sourceProductContext", "sourceEvidence", "sourceBinding",
         "sourceProvenance", "provenance", "stageAssertionBinding", "evidenceSource",
         "adapter", "record")
PRIVATE_KEYS = {"householdId", "memberId", "privateProfile", "patientId", "healthReadings",
                "personalObservations", "privateHousehold", "healthProfile", "healthObservations"}
RIGHTS = ("sourceRights", "rights", "permissions", "sourcePermissions", "usePermissions")


class RefusedContext(ValueError):
    """Fixed public diagnostic without source payload or personal information."""


def require(ok, reason):
    if not ok:
        raise RefusedContext(reason)


def matches(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def identical(a, b):
    # Python equality considers True, 1 and 1.0 equal. Source commitments do not.
    return canonical(a) == canonical(b)


def check_restrictions(node, nested=False):
    if isinstance(node, list):
        for val in node:
            check_restrictions(val, nested)
    elif isinstance(node, dict):
        require(not PRIVATE_KEYS.intersection(node), "private-profile-not-eligible")
        for key, val in node.items():
            if key in ("visibility", "decision", "status", "dataClass", "scope") and isinstance(val, str):
                require(val.casefold() not in FORBIDDEN, "restricted")
            if key in ("private", "restricted", "privateProviderData", "held", "denied", "blocked", "accessDenied"):
                require(val is False, "restricted")
            if key in ("allowed", "permitted", "granted", "authorized", "processingAllowed", "useAllowed"):
                require(val is True, "restricted")
            if nested or key in RIGHTS:
                check_restrictions(val, True)


def metadata_nodes(root):
    yield root
    for key in NODES:
        if key in root:
            child = root[key]
            require(isinstance(child, dict), "malformed-metadata")
            yield from metadata_nodes(child)


def check_cell(ctx, literal, adapter, role, key, pointer):
    f = ctx["fields"].get(role)
    require(isinstance(f, dict), "missing-field-contract")
    state, value = f.get("state"), f.get("originalValue")
    if state in ("not-projected", "missing", "unknown"):
        require(value is None and f.get("valueSha256") is None and f.get("evidenceBytes") is None
                and f.get("projectedValueCommitmentVerified") is False, "unbacked-field")
        require(f.get("sourcePointer") in (None, pointer)
                and f.get("evidenceEncoding") in (None, CODEC), "unbound-absence-evidence")
    else:
        require(state in ("present", "null", "empty"), "bad-field-state")
        require((state == "null") == (value is None), "contradictory-null")
        is_empty = value in ("", {}, []) if value is not None else False
        require((state == "empty") == is_empty, "contradictory-empty")
        if state != "null" and key == "names":
            require(isinstance(value, dict) and all(isinstance(k, str) and isinstance(v, str)
                                                    for k, v in value.items()), "bad-language-map")
        if state != "null" and key in ("name", "ingredientsText", "dataType"):
            require(isinstance(value, str), "bad-field-type")
        # The staged full_product_build.wire commits dictionaries in input order.
        # Sorting a multilingual map here would validate different source bytes.
        require(f.get("projectedValueCommitmentVerified") is True, "unverified-projection")
        payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"),
                             allow_nan=False).encode("utf-8")
        require(f.get("sourcePointer") == pointer and f.get("evidenceEncoding") == CODEC
                and type(f.get("evidenceBytes")) is int and f["evidenceBytes"] == len(payload)
                and f.get("valueSha256") == hashlib.sha256(payload).hexdigest(), "field-commitment")
    if key in literal:
        require(identical(literal[key], value), "contradictory-literal")
    if key in adapter and key == "names":
        require(identical(adapter[key], value), "contradictory-adapter")
    if key == "name" and key in adapter:
        n = adapter[key]
        require(isinstance(n, dict) and identical(n.get("originalValue"), value)
                and n.get("state") == state and n.get("pointer") == f.get("sourcePointer"),
                "contradictory-adapter")
    return {k: deepcopy(f[k]) for k in ("state", "originalValue", "sourcePointer", "valueSha256",
                                          "evidenceBytes", "evidenceEncoding", "projectedValueCommitmentVerified") if k in f}


def check_binding(provider, row, binding):
    require(provider in PROVIDERS and isinstance(binding, dict), "unbound-provider")
    require(binding.get("provider") == provider and binding.get("release") == PROVIDERS[provider][0],
            "unbound-release")
    for key in ("queue", "assignment_sha256", "rights_sha256", "parser_sha256", "stage_wire_sha256",
                "shard_sha256", "input_database_sha256"):
        require(matches(DIGEST, binding.get(key)), "invalid-operation-pin")
    require(binding["rights_sha256"] == PROVIDERS[provider][1], "unqualified-operation")
    require(type(binding.get("row_ordinal")) is int and binding["row_ordinal"] >= 0,
            "invalid-row-ordinal")
    require(matches(SHARD, binding.get("shard")) and matches(STAGE, binding.get("stage_record_id")),
            "invalid-stage-pin")
    require(isinstance(row, dict) and row.get("stageRecordId") == binding["stage_record_id"]
            and row.get("stageRecordWireSha256") == binding["stage_wire_sha256"], "wrong-stage")
    if "schema" in row:
        require(row["schema"] not in ("offmenu-household-domain/1","offmenu-private-portable-package/1"),
                "restricted")
    rt = row.get("retainedSource")
    require(isinstance(rt, dict) and rt.get("recordShard") == binding["shard"]
            and type(rt.get("cohort")) is int and rt["cohort"] == int(SHARD.fullmatch(binding["shard"])[1])
            and rt.get("compressedShardSha256") == binding["shard_sha256"], "wrong-source-shard")
    origin = row.get("sourceBinding")
    require(isinstance(origin, dict) and all(isinstance(origin.get(k), str) and origin[k].strip()
                                            for k in IDENTITY), "incomplete-origin")
    require(all(matches(DIGEST, origin[k]) for k in IDENTITY[4:]), "invalid-origin-digest")
    require(origin["sourceId"] == provider and origin["releaseId"] == binding["release"]
            and origin["nativeRecordId"] == provider + ":product:" + origin["recordId"]
            and origin["inputDatabaseSha256"] == binding["input_database_sha256"]
            and origin["sourceQualificationSha256"] == binding["rights_sha256"], "wrong-origin")
    a = row.get("sourceAdapterInput")
    require(isinstance(a, dict), "missing-adapter")
    ctx = a.get("sourceProductContext")
    require(isinstance(ctx, dict) and ctx.get("schema") == "offmenu-source-product-context/1"
            and isinstance(ctx.get("fields"),dict), "missing-typed-context")
    for other in (a.get("sourceBinding"), ctx.get("sourceEvidence")):
        require(isinstance(other, dict) and all(other.get(k) == origin[k] for k in IDENTITY),
                "inconsistent-origin")
    if "sourceProductContext" in row:
        require(identical(row["sourceProductContext"],ctx), "contradictory-context")
    rights = row.get("sourceRights")
    require(isinstance(rights, dict) and set(rights) <= {"visibility", "license", "attribution", "rights"}
            and rights.get("visibility") == "source-staging"
            and all(isinstance(rights.get(k),str) and rights[k].strip()
                    for k in ("license","attribution")), "missing-source-rights")
    for n in metadata_nodes(row):
        check_restrictions(n)
        require(all(k not in n or n[k] == origin[k] for k in IDENTITY), "conflicting-origin")
        for key, expected in (("stageRecordId", binding["stage_record_id"]),
                              ("stageRecordWireSha256", binding["stage_wire_sha256"]),
                              ("recordWireSha256", binding["stage_wire_sha256"]),
                              ("sourceRecordReference", origin["nativeRecordId"])):
            require(key not in n or n[key] == expected, "conflicting-stage")
    return a,ctx,origin,rights


def consume_context(provider: str, row: dict, *, binding: dict) -> dict:
    """Project one bound source row; raises RefusedContext on invalid input.

    The USDA R8 family classifier is not emulated; it is a separate semantic
    review gate. Unknown means unresolved, never a translated or accepted food.
    """
    try:
        a,ctx,origin,rights = check_binding(provider,row,binding)
        literal = row.get("literalProjectedFields")
        require(isinstance(literal,dict), "missing-literal-fields")
        roles = (("name","name"),("names","names")) if provider=="off" else (
            ("name","name"),("ingredientDeclaration","ingredientsText"),("dataType","dataType"))
        fields = {}
        for role,key in roles:
            prefix = "/data/" if provider=="off" else "/0/data/"
            fields[role] = check_cell(ctx,literal,a,role,key,prefix+key)
            for owner in (row,a):
                for name in ("originalFields","literalProjectedFields"):
                    if name in owner:
                        v=owner[name]
                        require(isinstance(v,dict) and (key not in v or identical(
                            v[key],fields[role].get("originalValue"))), "conflicting-literal-copy")
                for name in ("fieldEvidence","sourceFieldStates","sourceLanguageFields"):
                    if name not in owner:continue
                    ev=owner[name]
                    if ev is None:continue
                    require(isinstance(ev,dict),"bad-secondary-evidence")
                    if name=="sourceLanguageFields":
                        ev=ev.get("names") if role=="names" else None
                    elif role=="names":
                        ev=ev.get("languages",{}).get("names")
                    elif role=="dataType":
                        ev=ev.get("categories",{}).get("dataType")
                    else:
                        ev=ev.get(role)
                    if ev is None:continue
                    cell=fields[role]
                    require(isinstance(ev,dict) and ev.get("state")==cell["state"] and
                            ev.get("pointer")==cell.get("sourcePointer"),"conflicting-secondary")
                    if cell["state"] in ("present","null","empty"):
                        require(all(identical(ev.get(k),cell.get(v)) for k,v in (
                            ("parsedValueEvidenceSha256","valueSha256"),("evidenceBytes","evidenceBytes"),
                            ("evidenceEncoding","evidenceEncoding"))),"conflicting-secondary")
                    require("sourceValue" not in ev or identical(ev["sourceValue"],cell.get("originalValue")),
                            "conflicting-secondary")
        # This is a compact projection of the existing provider result contracts,
        # not a replacement serialization of the complete historic record.
        result = {"projectionOf": "offmenu-source-language-field-selection/1" if provider=="off" else
                  "offmenu-usda-english-field-projection/1", "sourceBinding": {k:origin[k] for k in IDENTITY},
                  "sourceRights": deepcopy(rights), "fields":fields,
                  "stageRecordId":binding["stage_record_id"],"stageRecordWireSha256":binding["stage_wire_sha256"],
                  "operation":{k:binding[k] for k in ("queue","shard","row_ordinal","assignment_sha256",
                                                      "parser_sha256","rights_sha256","shard_sha256")},
                  "normalizationComplete":False,"goldAdmitted":False,"languageInferred":False,
                  "translationPerformed":False,"automaticPlanningEligible":False}
        # Per-field lineage is separate from the origin of an entire record.
        # Nonmaterialized cells are a statement about this projection, not
        # about whether the upstream publisher possesses a value.
        def origin_for(cell, method):
            return {"recordId": origin["recordId"], "sourceObservationSha256": origin["sourceObservationSha256"],
                    "stageRecordWireSha256": binding["stage_wire_sha256"], "sourcePointer": cell.get("sourcePointer"),
                    "inputValueSha256": cell.get("valueSha256"), "sourceState": cell["state"],
                    "method": method, "policySha256": binding["parser_sha256"]}
        result["fieldOrigins"] = {}
        for role, cell in fields.items():
            result["fieldOrigins"]["/fields/"+role+"/originalValue"] = origin_for(cell, "retained-source-field")
        if provider=="off":
            name,names=fields["name"],fields["names"]
            en=(names.get("originalValue") or {}).get("en")
            selected=en if names["state"]=="present" and isinstance(en,str) and en.strip() else None
            if selected is not None:
                result["fieldOrigins"]["/selectedEnglishName"] = {
                    **origin_for(names, "select-publisher-language-member"), "memberPointer": "/en"}
            result.update(selectedEnglishName=selected,selectedPointer="/data/names/en" if selected else None,
                          semanticClassificationPerformed=False,
                          disposition=("english-field-unknown" if selected is None else
                                       "english-field-present-generic-name-unknown" if name["state"]!="present" else
                                       "exact-source-agreement" if selected==name.get("originalValue") else
                                       "source-fields-disagree"))
        else:
            for role,cell in fields.items():
                text=cell.get("originalValue")
                if role!="dataType" and cell["state"]=="present":
                    cell["normalizedLexicalValue"]=" ".join(unicodedata.normalize("NFC",text).casefold().split())
                    result["fieldOrigins"]["/fields/"+role+"/normalizedLexicalValue"] = origin_for(
                        cell, "NFC+casefold+whitespace")
                else:
                    cell["normalizedLexicalValue"]=None
            result.update(disposition="source-lexical-projection", semanticResolution={
                "status":"unresolved","reason":"separate-reviewed-semantic-caller-required"},
                lexicalPolicy="NFC+casefold+whitespace")
        return result
    except (AttributeError, KeyError, TypeError, RecursionError, UnicodeError, ValueError) as exc:
        if isinstance(exc,RefusedContext):raise
        raise RefusedContext("invalid-envelope") from None
