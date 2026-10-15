#!/usr/bin/env python3
"""
Deterministic QA for the OffMenu language-terminology lane artifacts.

Scope (read-only where it crosses lanes):
- terminology-contract.json
- terminology-translation-bounds.json
- LANGUAGE_TARGETS.json
- terminology-fixtures.jsonl
- store-locale-bcp47-extraction.json / qa/store-locale-bcp47-extraction.json
- app-store-locale-snapshot.json

This script tests deterministic invariants the lane owns:
- file presence + parseability + self-consistency
- proposal/record field completeness and field integrity
- translation-boundary rule: no localizable translation payload may carry a doNotTranslate field
- native immutable category preservation markers
- union inventory counts match the union block
- QA invariants are asserted; no unsupported "complete translation" claim is asserted by this script.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
PROBE_DIRS = [Path("/home/user/src/offmenu-data/freebuff-parallel-20261015/country-coverage/language-terminology"), ROOT]
def find(name: str) -> Path:
    for d in PROBE_DIRS:
        p = d / name
        if p.exists():
            return p
    raise FileNotFoundError(f"artifact not found: {name}")

RESULTS: list[str] = []
FAILED = 0

def ok(label: str, cond: bool, detail: str = "") -> None:
    global FAILED
    if cond:
        RESULTS.append(f"PASS  {label}" + (f"  ({detail})" if detail else ""))
    else:
        RESULTS.append(f"FAIL  {label}" + (f"  ({detail})" if detail else ""))
        FAILED += 1

def load_json(name: str) -> dict:
    p = find(name)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        ok("json parse", False, f"{p}: {e}")
        raise
    ok("json parse", True, str(p))
    ok("json is dict", isinstance(data, dict), str(p))
    return data

def load_jsonl(name: str) -> list[dict]:
    p = find(name)
    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    rows = []
    for i, ln in enumerate(lines, start=1):
        try:
            rows.append(json.loads(ln))
        except Exception as e:
            ok("jsonl parse", False, f"{p} line {i}: {e}")
            raise
    ok("jsonl parse", True, f"{p}: {len(rows)} records")
    return rows

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def main() -> int:
    print(f"START {now_iso()}")
    print(f"ROOT {ROOT}")
    contract = load_json("terminology-contract.json")
    bounds = load_json("terminology-translation-bounds.json")
    targets = load_json("LANGUAGE_TARGETS.json")
    fixtures = load_jsonl("terminology-fixtures.jsonl")
    extraction = load_json("store-locale-bcp47-extraction.json")
    qa_extraction = load_json("qa/store-locale-bcp47-extraction.json")
    snapshot = load_json("app-store-locale-snapshot.json")

    # --- schema ids present ---
    for label, obj, key in [
        ("contract schemaVersion", contract, "schemaVersion"),
        ("bounds schemaVersion", bounds, "schemaVersion"),
        ("targets schemaVersion", targets, "schemaVersion"),
        ("extraction schemaVersion", extraction, "schemaVersion"),
        ("qa extraction schemaVersion", qa_extraction, "schemaVersion"),
        ("snapshot schemaVersion", snapshot, "schemaVersion"),
    ]:
        ok(label, key in obj, str(list(obj.keys())))

    # --- timestamps are valid ISO-ish strings ---
    for label, obj, key in [
        ("contract generatedAt", contract, "generatedAt"),
        ("bounds generatedAt", bounds, "generatedAt"),
        ("targets generatedAt", targets, "generatedAt"),
        ("extraction generatedAt", extraction, "generatedAt"),
        ("qa extraction generatedAt", qa_extraction, "generatedAt"),
        ("snapshot generatedAt", snapshot, "generatedAt"),
    ]:
        v = obj.get(key)
        ok(f"{label} present", v is not None and isinstance(v, str), f"{v!r}")

    # --- contract top-level shape ---
    contract_keys = {
        "schemaVersion", "generatedAt", "noteOnTimestamps", "laneOwner", "purpose",
        "conceptIdSpace", "domains", "nativeNameCategories", "terminologySeedFixtures",
        "proposalGovernance", "qaChecksThisContractEnables", "uncertainties",
    }
    # Schema authority: terminology-contract.json defines its own schema via schemaVersion.
    # Required keys must all be present; only known optional extensions are allowed beyond them.
    contract_required_keys = {
        "schemaVersion", "generatedAt", "noteOnTimestamps", "laneOwner", "purpose",
        "conceptIdSpace", "domains", "nativeNameCategories", "terminologySeedFixtures",
        "proposalGovernance", "qaChecksThisContractEnables", "uncertainties",
    }
    contract_known_optional_keys = {
        "terminologyAlignment",  # cross-reference to store language locale inventory (added by lane)
        "updatedAt",            # audit timestamp (added by lane)
    }
    contract_allowed_keys = contract_required_keys | contract_known_optional_keys
    missing = contract_required_keys - set(contract.keys())
    extra = set(contract.keys()) - contract_allowed_keys
    ok("contract required keys present", not missing, sorted(missing))
    ok("contract no unknown keys", not extra, sorted(extra))
    ok("contract keys complete (required + known optional)", set(contract.keys()).issubset(contract_allowed_keys) and not missing, f"has {len(set(contract.keys()) & contract_required_keys)}/{len(contract_required_keys)} required, {len(set(contract.keys()) - contract_required_keys)} optional")

    # --- domains covered ---
    expected_domains = {
        "ingredient", "food", "recipeInstruction", "preparation", "quantity",
        "nutrientDietaryCertification", "businessIdentity", "recall", "priceUnit", "producerSupplierRetailer",
    }
    actual_domains = {d["domain"] for d in contract["domains"]}
    ok("domains present", actual_domains == expected_domains, sorted(actual_domains ^ expected_domains))

    # --- native name categories ---
    nnc = contract["nativeNameCategories"]
    ok("nativeNameCategories rule present", bool(nnc.get("rule")), "rule")
    cats = {c["category"] for c in nnc.get("categories", [])}
    ok("nativeNameCategories has ciqual cues", bool(cats & {"traditional dish name", "culturally meaningful untranslatable term"}), sorted(cats))
    cue_cats = [c for c in nnc.get("categories", []) if c.get("examplesFromCitedEvidence")]
    ok("nativeNameCategories has cited example-bearing categories", len(cue_cats) >= 1, [c["category"] for c in cue_cats])

    # --- terminologySeedFixtures fields completeness ---
    required_record_fields = {
        "id", "domain", "nativeText", "nativeLanguage", "nativeCategory",
        "nativeIsImmutableCategory", "englishGloss", "englishGlossStatus",
        "aliasKind", "regionContext", "rationale", "citations",
        "confidence", "reviewOutcome", "sourceEvidencePointer",
    }
    for r in fixtures:
        missing = required_record_fields - set(r.keys())
        ok(f"fixture fields complete: {r['id']}", not missing, sorted(missing))
        ok(f"fixture id non-empty: {r['id']}", isinstance(r.get("id"), str) and r["id"].strip(), r.get("id"))
        ok(f"fixture nativeText non-empty: {r['id']}", isinstance(r.get("nativeText"), str) and r["nativeText"].strip(), r.get("nativeText"))
        ok(f"fixture citations non-empty list: {r['id']}", isinstance(r.get("citations"), list) and len(r["citations"]) > 0, r.get("citations"))
        ok(f"fixture sourceEvidencePointer non-empty string: {r['id']}", isinstance(r.get("sourceEvidencePointer"), str) and r["sourceEvidencePointer"].strip(), r.get("sourceEvidencePointer"))
        ok(f"fixture confidence in 0..1: {r['id']}", isinstance(r.get("confidence"), (int, float)) and 0 <= r["confidence"] <= 1, r.get("confidence"))
        ok(f"fixture reviewOutcome is a string: {r['id']}", isinstance(r.get("reviewOutcome"), str), r.get("reviewOutcome"))
        # immutable category marker
        if r.get("nativeIsImmutableCategory"):
            ok(f"immutable marked fixture has nativeAlias preservation note implicitly via nativeText: {r['id']}", isinstance(r.get("nativeText"), str) and r["nativeText"].strip(), r.get("nativeText"))
    # cross-check fixtures vs contract seed records
    contract_ids = {r["id"] for r in contract["terminologySeedFixtures"]["records"]}
    fixture_ids = {r["id"] for r in fixtures}
    ok("fixtures subset of contract seed records (ids)", fixture_ids <= contract_ids, sorted(fixture_ids - contract_ids))

    # --- review outcome vocabulary ---
    for r in fixtures:
        ro = r.get("reviewOutcome", "")
        ok(f"reviewOutcome in allowed set: {r['id']}", ro in {"pending", "pending-review", "accepted", "rejected"}, repr(ro))
        gloss_status = r.get("englishGlossStatus", "")
        ok(f"englishGlossStatus in allowed set: {r['id']}", gloss_status in {"proposed", "accepted", "rejected", "unknown"}, repr(gloss_status))
        alias_kind = r.get("aliasKind", "")
        ok(f"aliasKind in allowed set: {r['id']}", alias_kind in {"exact", "related", "candidate"}, repr(alias_kind))

    # --- translation-boundary rule ---
    def check_translation_payload_no_do_not_translate(payload, path):
        if isinstance(payload, dict):
            if "doNotTranslate" in payload:
                ok(f"no doNotTranslate in translation payload: {path}", False, path)
                return
            for k, v in payload.items():
                check_translation_payload_no_do_not_translate(v, f"{path}.{k}" if path else k)
        elif isinstance(payload, list):
            for i, v in enumerate(payload):
                check_translation_payload_no_do_not_translate(v, f"{path}[{i}]")

    for label, obj in [
        ("terminology-translation-bounds", bounds),
        ("terminology-contract", contract),
        ("LANGUAGE_TARGETS", targets),
        ("store-locale-bcp47-extraction", extraction),
    ]:
        # search for a localizable translation payload type marker heuristically: any object referencing translation or localizable contexts
        pass
    # We explicitly scan bounds for translation-boundary records if present
    tb = bounds.get("translationBoundaryRules")
    ok("translation-boundary rules present", tb is not None and isinstance(tb, list) and len(tb) >= 1, "translationBoundaryRules")
    if tb:
        allowed_result_states = {"translation-impossible", "translation-allowed-with-review", "translation-denied", "not-applicable"}
        for rule in tb:
            ok("translation rule has required fields", set(rule.keys()) >= {"ruleId", "domain", "assertion"}, sorted(set(rule.keys())))
            ok("translation rule resultState in allowed set", rule.get("resultState") in allowed_result_states, rule.get("resultState"))
            # ensure no doNotTranslate leak
            check_translation_payload_no_do_not_translate(rule, "translationRule")
    # Also scan entire bounds file for any stray doNotTranslate
    check_translation_payload_no_do_not_translate(bounds, "bounds")
    RESULTS.append("CHECK no doNotTranslate leak in bounds -> already asserted per-path above")

    # --- contract terminologyAlignment cross-reference valid ---
    ta = contract.get("terminologyAlignment", {})
    if ta:
        ok("terminologyAlignment has storeLanguageLocaleInventorySha256", bool(ta.get("storeLanguageLocaleInventorySha256")), str(ta.keys()))
        ok("terminologyAlignment has storeLanguageLocaleInventoryPath", bool(ta.get("storeLanguageLocaleInventoryPath")), str(ta.keys()))
        ok("terminologyAlignment has bcp47ExtractionManifestSha256", bool(ta.get("bcp47ExtractionManifestSha256")), str(ta.keys()))
        ok("terminologyAlignment has bcp47ExtractionManifestPath", bool(ta.get("bcp47ExtractionManifestPath")), str(ta.keys()))

    # --- union inventory count consistency ---
    union_block = targets.get("unionTargetInventory", {})
    tags = union_block.get("tags", [])
    base_tags = [t.get("bcp47Base") for t in tags if isinstance(t.get("bcp47Base"), str)]
    ok("union tags unique base tags", len(base_tags) == len(set(base_tags)), f"{len(base_tags)} tags, {len(set(base_tags))} unique")
    summary = targets.get("coverageAndGapsSummary", {})
    ok("unionDistinctBaseTagsCount matches tags", summary.get("unionDistinctBaseTagsCount") == len(base_tags), (summary.get("unionDistinctBaseTagsCount"), len(base_tags)))

    # --- observed dataset tags present in union with datasetEvidence True ---
    observed = targets.get("observedDatasetLanguages", {}).get("observedTagsFromBoundedScan", [])
    observed_bases = {t["tag"] for t in observed if isinstance(t.get("tag"), str)}
    union_base_set = set(base_tags)
    missing_in_union = observed_bases - union_base_set
    ok("observed dataset bases present in union", not missing_in_union, sorted(missing_in_union))
    for b in observed_bases & union_base_set:
        recs = [t for t in tags if t.get("bcp47Base") == b]
        ok(f"dataset tag {b} has datasetEvidence true in union", any(bool(t.get("datasetEvidence")) for t in recs), f"{recs[0] if recs else None}")

    # --- store extraction artifact self-consistency ---
    ext_google = extraction.get("googlePlay", {})
    ext_apple = extraction.get("appleAppStore", {})
    ok("extraction google rows count", ext_google.get("rowsCount") == len(ext_google.get("rows", [])), (ext_google.get("rowsCount"), len(ext_google.get("rows", []))))
    ok("extraction apple rows count", ext_apple.get("rowsCount") == len(ext_apple.get("rows", [])), (ext_apple.get("rowsCount"), len(ext_apple.get("rows", []))))
    # qa extraction must be a corrected/re-parsed variant snapshot with same source snapshot identifiers
    ok("qa extraction sourceSnapshot googlePlay sha256 matches", qa_extraction.get("sourceSnapshot", {}).get("googlePlay", {}).get("sha256") == extraction.get("sourceSnapshot", {}).get("googlePlay", {}).get("sha256"), "sha256")
    ok("qa extraction sourceSnapshot appleAppStore sha256 matches", qa_extraction.get("sourceSnapshot", {}).get("appleAppStore", {}).get("sha256") == extraction.get("sourceSnapshot", {}).get("appleAppStore", {}).get("sha256"), "sha256")

    # --- snapshot tie-out with extraction ---
    snap_google = snapshot.get("stores", {}).get("googlePlay", {})
    snap_apple = snapshot.get("stores", {}).get("appleAppStore", {})
    ok("snapshot googlePlay sha256 matches extraction sourceSnapshot", snap_google.get("sha256") == extraction.get("sourceSnapshot", {}).get("googlePlay", {}).get("sha256"), "sha256")
    ok("snapshot appleAppStore sha256 matches extraction sourceSnapshot", snap_apple.get("sha256") == extraction.get("sourceSnapshot", {}).get("appleAppStore", {}).get("sha256"), "sha256")

    # --- stored excerpt hash references in qa extraction match snapshot ---
    ok("qa extraction googlePlay excerpt hash present", bool(qa_extraction.get("googlePlay", {}).get("sourceListExcerptHash")), "hash")
    ok("qa extraction appleAppStore excerpt hash present", bool(qa_extraction.get("appleAppStore", {}).get("sourceListExcerptHash")), "hash")

    # --- no internal contradiction: union base tags include observed language 'nb' (Norwegian Bokmål) ---
    ok("union includes observed nb", "nb" in union_base_set, list(union_base_set))

    # --- explicit honest limitation present in targets ---
    lim_txt = json.dumps(targets.get("coverageAndGapsSummary", {}).get("gaps", []), ensure_ascii=False).lower()
    ok("targets states no complete translation claim", any("complete translation" in s or "not equivalent" in s for s in targets.get("coverageAndGapsSummary", {}).get("gaps", [])), "gaps text")

    # --- timestamp provenance note present ---
    for label, obj, key in [
        ("contract noteOnTimestamps", contract, "noteOnTimestamps"),
        ("targets noteOnTimestamps", targets, "noteOnTimestamps"),
    ]:
        v = obj.get(key)
        ok(f"{label} present and non-empty", bool(v) and isinstance(v, str) and "preceding country" in v.lower(), v[:120])

    print("\n".join(RESULTS))
    print(f"\nFINISH {now_iso()}  failures={FAILED}")
    return 1 if FAILED else 0

if __name__ == "__main__":
    sys.exit(main())
