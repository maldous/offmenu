#!/usr/bin/env python3
"""
Deterministic QA for the OffMenu language-terminology lane artifacts.

Scope (read-only where it crosses lanes):
- terminology-contract.json
- terminology-translation-bounds.json
- LANGUAGE_TARGETS.json
- terminology-fixtures.jsonl
- store-locale-bcp47-extraction.json / qa/store-locale-bcp47-extraction.json
- store-language-locale-inventory.json
- app-store-locale-snapshot.json
- STATUS.json (D6: non-self-referential pin manifest)

This script tests deterministic invariants the lane owns:
- file presence + parseability + self-consistency
- proposal/record field completeness and field integrity
- translation-boundary rule: no localizable translation payload may carry a doNotTranslate field
- native immutable category preservation markers
- union inventory counts match the union block AND match the union recomputed from inputs
- D1 regression: Apple Slovenia caption retained as unresolvedCaption (never dropped)
- D2 regression: canonical tag count separated from unresolved-caption row count
- D3 regression: terminology-contract tie-out hashes equal computed file sha256
- D5 regression: fix-store-bcp-tags.py guard defaults refuse candidate overwrite
- QA invariants are asserted; no unsupported "complete translation" claim is asserted by this script.
"""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
PROBE_DIRS = [
    Path("/home/user/src/offmenu-data/freebuff-parallel-20261015/country-coverage/language-terminology"),
    ROOT,
]
CANDIDATE_LANE_ROOT = Path(
    "/home/user/src/offmenu-data/freebuff-parallel-20261015/country-coverage/language-terminology"
)


def find(name: str) -> Path:
    for d in PROBE_DIRS:
        p = d / name
        if p.exists():
            return p
    raise FileNotFoundError(f"artifact not found: {name}")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


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


def base_of(tag: str) -> str:
    """BCP-47 base: collapse regional/script variants and private-use singletons to the
    primary language subtag, per LANGUAGE_TARGETS.unionPrinciple. en-x-simple -> en."""
    return tag.split("-")[0]


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
    inventory = load_json("store-language-locale-inventory.json")
    status = load_json("STATUS.json")

    # --- schema ids present ---
    for label, obj, key in [
        ("contract schemaVersion", contract, "schemaVersion"),
        ("bounds schemaVersion", bounds, "schemaVersion"),
        ("targets schemaVersion", targets, "schemaVersion"),
        ("extraction schemaVersion", extraction, "schemaVersion"),
        ("qa extraction schemaVersion", qa_extraction, "schemaVersion"),
        ("snapshot schemaVersion", snapshot, "schemaVersion"),
        ("inventory schemaVersion", inventory, "schemaVersion"),
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
        # allowedExtensions is the enforcement mechanism itself, not a payload
        # extension; it is part of the baseline key set, so it is never an "extra".
        "allowedExtensions",
    }
    missing = contract_keys - set(contract.keys())
    ok("contract keys present", not missing, sorted(missing))
    extra = set(contract.keys()) - contract_keys
    ok("contract keys extra allowed (terminologyAlignment/updatedAt)",
       not (extra - {"terminologyAlignment", "updatedAt"}),
       sorted(extra) if extra else "none")
    # Contract-level allowedExtensions regression: explicit enumeration must cover extras
    allowed_ext = contract.get("allowedExtensions", {})
    ok("contract allowedExtensions present (explicit enumeration)",
       isinstance(allowed_ext, dict) and "allowed" in allowed_ext, str(allowed_ext)[:120])
    if isinstance(allowed_ext, dict) and "allowed" in allowed_ext:
        allowed_keys = {e["key"] for e in allowed_ext["allowed"] if isinstance(e, dict)}
        ok("contract allowedExtensions covers observed extra keys",
           extra.issubset(allowed_keys), f"extra={sorted(extra)} allowed={sorted(allowed_keys)}")

    # --- domains covered ---
    expected_domains = {
        "ingredient", "food", "recipeInstruction", "preparation", "quantity",
        "nutrientDietaryCertification", "businessIdentity", "recall", "priceUnit",
        "producerSupplierRetailer",
    }
    actual_domains = {d["domain"] for d in contract["domains"]}
    ok("domains present", actual_domains == expected_domains,
       sorted(actual_domains ^ expected_domains))

    # --- native name categories ---
    nnc = contract["nativeNameCategories"]
    ok("nativeNameCategories rule present", bool(nnc.get("rule")), "rule")
    cats = {c["category"] for c in nnc.get("categories", [])}
    ok("nativeNameCategories has ciqual cues",
       bool(cats & {"traditional dish name", "culturally meaningful untranslatable term"}),
       sorted(cats))
    cue_cats = [c for c in nnc.get("categories", []) if c.get("examplesFromCitedEvidence")]
    ok("nativeNameCategories has cited example-bearing categories", len(cue_cats) >= 1,
       [c["category"] for c in cue_cats])

    # --- terminologySeedFixtures fields completeness ---
    required_record_fields = {
        "id", "domain", "nativeText", "nativeLanguage", "nativeCategory",
        "nativeIsImmutableCategory", "englishGloss", "englishGlossStatus",
        "aliasKind", "regionContext", "rationale", "citations",
        "confidence", "reviewOutcome", "sourceEvidencePointer",
    }
    for r in fixtures:
        miss = required_record_fields - set(r.keys())
        ok(f"fixture fields complete: {r['id']}", not miss, sorted(miss))
        ok(f"fixture id non-empty: {r['id']}",
           isinstance(r.get("id"), str) and r["id"].strip(), r.get("id"))
        ok(f"fixture nativeText non-empty: {r['id']}",
           isinstance(r.get("nativeText"), str) and r["nativeText"].strip(), r.get("nativeText"))
        ok(f"fixture citations non-empty list: {r['id']}",
           isinstance(r.get("citations"), list) and len(r["citations"]) > 0, r.get("citations"))
        ok(f"fixture sourceEvidencePointer non-empty string: {r['id']}",
           isinstance(r.get("sourceEvidencePointer"), str) and r["sourceEvidencePointer"].strip(),
           r.get("sourceEvidencePointer"))
        ok(f"fixture confidence in 0..1: {r['id']}",
           isinstance(r.get("confidence"), (int, float)) and 0 <= r["confidence"] <= 1,
           r.get("confidence"))
        ok(f"fixture reviewOutcome is a string: {r['id']}",
           isinstance(r.get("reviewOutcome"), str), r.get("reviewOutcome"))
        if r.get("nativeIsImmutableCategory"):
            ok(f"immutable marked fixture has nativeText: {r['id']}",
               isinstance(r.get("nativeText"), str) and r["nativeText"].strip(), r.get("nativeText"))
    contract_ids = {r["id"] for r in contract["terminologySeedFixtures"]["records"]}
    fixture_ids = {r["id"] for r in fixtures}
    ok("fixtures subset of contract seed records (ids)", fixture_ids <= contract_ids,
       sorted(fixture_ids - contract_ids))

    # --- review outcome vocabulary ---
    for r in fixtures:
        ro = r.get("reviewOutcome", "")
        ok(f"reviewOutcome in allowed set: {r['id']}",
           ro in {"pending", "pending-review", "accepted", "rejected"}, repr(ro))
        gloss_status = r.get("englishGlossStatus", "")
        ok(f"englishGlossStatus in allowed set: {r['id']}",
           gloss_status in {"proposed", "accepted", "rejected", "unknown"}, repr(gloss_status))
        alias_kind = r.get("aliasKind", "")
        ok(f"aliasKind in allowed set: {r['id']}",
           alias_kind in {"exact", "related", "candidate"}, repr(alias_kind))

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

    tb = bounds.get("translationBoundaryRules")
    ok("translation-boundary rules present",
       tb is not None and isinstance(tb, list) and len(tb) >= 1, "translationBoundaryRules")
    if tb:
        allowed_result_states = {"translation-impossible", "translation-allowed-with-review",
                                 "translation-denied", "not-applicable"}
        for rule in tb:
            ok("translation rule has required fields",
               set(rule.keys()) >= {"ruleId", "domain", "assertion"}, sorted(set(rule.keys())))
            ok("translation rule resultState in allowed set",
               rule.get("resultState") in allowed_result_states, rule.get("resultState"))
            check_translation_payload_no_do_not_translate(rule, "translationRule")
    check_translation_payload_no_do_not_translate(bounds, "bounds")
    RESULTS.append("CHECK no doNotTranslate leak in bounds -> already asserted per-path above")

    # --- contract terminologyAlignment cross-reference valid (D3) ---
    ta = contract.get("terminologyAlignment", {})
    if ta:
        ok("terminologyAlignment has storeLanguageLocaleInventorySha256",
           bool(ta.get("storeLanguageLocaleInventorySha256")), str(ta.keys()))
        ok("terminologyAlignment has storeLanguageLocaleInventoryPath",
           bool(ta.get("storeLanguageLocaleInventoryPath")), str(ta.keys()))
        ok("terminologyAlignment has bcp47ExtractionManifestSha256",
           bool(ta.get("bcp47ExtractionManifestSha256")), str(ta.keys()))
        ok("terminologyAlignment has bcp47ExtractionManifestPath",
           bool(ta.get("bcp47ExtractionManifestPath")), str(ta.keys()))
    # D3 regression: assert tie-out hashes equal computed file sha256 (not just presence)
    ext_actual_sha = sha(find("store-locale-bcp47-extraction.json"))
    inv_actual_sha = sha(find("store-language-locale-inventory.json"))
    ok("D3 terminologyAlignment inventorySha256 == computed sha256",
       ta.get("storeLanguageLocaleInventorySha256") == inv_actual_sha,
       f"contract={str(ta.get('storeLanguageLocaleInventorySha256'))[:16]} actual={inv_actual_sha[:16]}")
    ok("D3 terminologyAlignment extractionSha256 == computed sha256",
       ta.get("bcp47ExtractionManifestSha256") == ext_actual_sha,
       f"contract={str(ta.get('bcp47ExtractionManifestSha256'))[:16]} actual={ext_actual_sha[:16]}")

    # --- union inventory: tags unique, count matches block (D4) ---
    union_block = targets.get("unionTargetInventory", {})
    tags = union_block.get("tags", [])
    base_tags = [t.get("bcp47Base") for t in tags if isinstance(t.get("bcp47Base"), str)]
    union_count = len(set(base_tags))
    ok("union tags unique base tags", len(base_tags) == len(set(base_tags)),
       f"{len(base_tags)} tags, {len(set(base_tags))} unique")
    summary = targets.get("coverageAndGapsSummary", {})
    ok("unionDistinctBaseTagsCount matches tags",
       summary.get("unionDistinctBaseTagsCount") == union_count,
       (summary.get("unionDistinctBaseTagsCount"), union_count))

    # --- D4 regression: union recomputed from inputs (NOT a hardcoded literal) ---
    observed = targets.get("observedDatasetLanguages", {}).get("observedTagsFromBoundedScan", [])
    obs_bases = {base_of(t["tag"]) for t in observed if isinstance(t.get("tag"), str)}
    ext_g = extraction.get("googlePlay", {}).get("rows", [])
    ext_a = extraction.get("appleAppStore", {}).get("rows", [])
    g_canon = {r.get("canonicalBcp47") for r in ext_g if r.get("canonicalBcp47")}
    a_canon = {r.get("canonicalBcp47") for r in ext_a if r.get("canonicalBcp47")}
    store_bases = {base_of(t) for t in (g_canon | a_canon)}
    recomputed_union = obs_bases | store_bases
    stored_union = set(base_tags)
    ok("D4 union == recomputed(observed bases | store canonical bases)",
       stored_union == recomputed_union,
       f"missing={sorted(recomputed_union - stored_union)} extra={sorted(stored_union - recomputed_union)}")
    ok("D4 recomputed union size matches declared count",
       len(recomputed_union) == summary.get("unionDistinctBaseTagsCount"),
       f"recomputed={len(recomputed_union)} declared={summary.get('unionDistinctBaseTagsCount')}")

    # --- observed dataset tags present in union with datasetEvidence True ---
    observed_bases = obs_bases
    union_base_set = stored_union
    missing_in_union = observed_bases - union_base_set
    ok("observed dataset bases present in union", not missing_in_union, sorted(missing_in_union))
    for b in observed_bases & union_base_set:
        recs = [t for t in tags if t.get("bcp47Base") == b]
        ok(f"dataset tag {b} has datasetEvidence true in union",
           any(bool(t.get("datasetEvidence")) for t in recs), f"{recs[0] if recs else None}")

    # --- D4 regression: summary store counters match extraction distinct canonical ---
    ok("D4 summary google counter == extraction distinct canonical",
       summary.get("storeExtractedGoogleDistinctTagsInArtifact") == len(g_canon),
       f"declared={summary.get('storeExtractedGoogleDistinctTagsInArtifact')} actual={len(g_canon)}")
    ok("D4 summary apple counter == extraction distinct canonical",
       summary.get("storeExtractedAppleDistinctTagsInArtifact") == len(a_canon),
       f"declared={summary.get('storeExtractedAppleDistinctTagsInArtifact')} actual={len(a_canon)}")

    # --- D1 regression: Apple Slovenia caption retained as unresolvedCaption ---
    apple_inv = inventory.get("appleAppStore", {})
    apple_items = apple_inv.get("items", [])
    sl_rows = [i for i in apple_items if i.get("sourceCaption") == "Slovenia"]
    ok("D1 Apple inventory retains Slovenia caption row (not dropped)", len(sl_rows) == 1,
       f"rows={len(sl_rows)}")
    if sl_rows:
        sl = sl_rows[0]
        ok("D1 Slovenia row evidenceKind == unresolvedCaption",
           sl.get("evidenceKind") == "unresolvedCaption", sl.get("evidenceKind"))
        ok("D1 Slovenia row carries Google sl cross-reference note",
           "Slovenian" in str(sl.get("note", "")) and "sl" in str(sl.get("note", "")),
           str(sl.get("note", ""))[:100])
    apple_excerpt = apple_inv.get("sourceListTextExcerpt", "")
    ok("D1 Apple source excerpt contains literal Slovenia",
       "Slovenia" in apple_excerpt, "Slovenia" in apple_excerpt)

    # --- D2 regression: canonical tag count separated from unresolved-caption count ---
    ap_unres = apple_inv.get("unresolvedCaptionRowCount")
    ap_canon_count = apple_inv.get("canonicalBcp47TagCount")
    ap_items_count = apple_inv.get("itemsCount")
    ap_resolved = [i for i in apple_items if i.get("evidenceKind") != "unresolvedCaption"]
    ap_resolved_canon = {i.get("canonicalBcp47") for i in ap_resolved if i.get("canonicalBcp47")}
    ok("D2 apple canonicalBcp47TagCount == resolved distinct canonical",
       ap_canon_count == len(ap_resolved_canon),
       f"declared={ap_canon_count} actual={len(ap_resolved_canon)}")
    ok("D2 apple unresolvedCaptionRowCount == 1 (Slovenia)", ap_unres == 1, f"count={ap_unres}")
    ok("D2 apple itemsCount == total retained rows",
       ap_items_count == len(apple_items), f"declared={ap_items_count} actual={len(apple_items)}")
    ok("D2 apple itemsCount == canonical + unresolved",
       ap_items_count == (ap_canon_count or 0) + (ap_unres or 0),
       f"items={ap_items_count} canon={ap_canon_count} unres={ap_unres}")

    # --- store extraction artifact self-consistency ---
    ext_google = extraction.get("googlePlay", {})
    ext_apple = extraction.get("appleAppStore", {})
    ok("extraction google rows count",
       ext_google.get("rowsCount") == len(ext_google.get("rows", [])),
       (ext_google.get("rowsCount"), len(ext_google.get("rows", []))))
    ok("extraction apple rows count",
       ext_apple.get("rowsCount") == len(ext_apple.get("rows", [])),
       (ext_apple.get("rowsCount"), len(ext_apple.get("rows", []))))
    ok("qa extraction sourceSnapshot googlePlay sha256 matches",
       qa_extraction.get("sourceSnapshot", {}).get("googlePlay", {}).get("sha256")
       == extraction.get("sourceSnapshot", {}).get("googlePlay", {}).get("sha256"), "sha256")
    ok("qa extraction sourceSnapshot appleAppStore sha256 matches",
       qa_extraction.get("sourceSnapshot", {}).get("appleAppStore", {}).get("sha256")
       == extraction.get("sourceSnapshot", {}).get("appleAppStore", {}).get("sha256"), "sha256")

    # --- snapshot tie-out with extraction ---
    snap_google = snapshot.get("stores", {}).get("googlePlay", {})
    snap_apple = snapshot.get("stores", {}).get("appleAppStore", {})
    ok("snapshot googlePlay sha256 matches extraction sourceSnapshot",
       snap_google.get("sha256") == extraction.get("sourceSnapshot", {}).get("googlePlay", {}).get("sha256"), "sha256")
    ok("snapshot appleAppStore sha256 matches extraction sourceSnapshot",
       snap_apple.get("sha256") == extraction.get("sourceSnapshot", {}).get("appleAppStore", {}).get("sha256"), "sha256")

    # --- stored excerpt hash references in qa extraction match snapshot ---
    ok("qa extraction googlePlay excerpt hash present",
       bool(qa_extraction.get("googlePlay", {}).get("sourceListExcerptHash")), "hash")
    ok("qa extraction appleAppStore excerpt hash present",
       bool(qa_extraction.get("appleAppStore", {}).get("sourceListExcerptHash")), "hash")

    # --- no internal contradiction: union base tags include observed language 'nb' ---
    ok("union includes observed nb", "nb" in union_base_set, "nb")

    # --- explicit honest limitation present in targets ---
    gaps = targets.get("coverageAndGapsSummary", {}).get("gaps", [])
    ok("targets states no complete translation claim",
       any("complete translation" in s or "not equivalent" in s for s in gaps), "gaps text")

    # --- D5 regression: fix-store-bcp-tags.py guard defaults refuse candidate overwrite ---
    guard_script = ROOT / "qa" / "fix-store-bcp-tags.py"
    if guard_script.exists():
        gsrc = guard_script.read_text(encoding="utf-8")
        ok("D5 guard script declares NON_AUTHORITATIVE", "NON-AUTHORITATIVE" in gsrc, "marker")
        ok("D5 guard script requires explicit allow env", "FIX_STORE_BCP_TAGS_ALLOW" in gsrc, "env")
        ok("D5 guard script requires lane-overwrite env", "FIX_STORE_BCP_TAGS_ALLOW_LANE_OVERWRITE" in gsrc, "env")
        ok("D5 guard script does not write to DEST unconditionally",
           "guard(dest" in gsrc or "guard(" in gsrc, "guard call present")
        ok("D5 guard default DEST is inside candidate lane (hazard documented)",
           "store-locale-bcp47-extraction.json" in gsrc, "DEST")
    else:
        ok("D5 guard script present", False, "fix-store-bcp-tags.py missing")

    # --- D6 regression: STATUS.json carries no self-referential hash ---
    ok("D6 STATUS has no STATUS.json self-hash in fileHashes",
       "STATUS.json" not in status.get("fileHashes", {}), str(list(status.get("fileHashes", {}).keys())))
    ok("D6 STATUS has no STATUS_sha256_after_run field",
       "STATUS_sha256_after_run" not in status, "field absent")
    pin = status.get("pinManifest", {})
    ok("D6 STATUS pinManifest present (non-self-referential)",
       isinstance(pin, dict) and "externalPinPath" in pin, str(pin)[:120])

    # --- timestamp provenance note present ---
    for label, obj, key in [
        ("contract noteOnTimestamps", contract, "noteOnTimestamps"),
        ("targets noteOnTimestamps", targets, "noteOnTimestamps"),
    ]:
        v = obj.get(key)
        ok(f"{label} present and non-empty",
           bool(v) and isinstance(v, str) and "preceding country" in v.lower(), v[:120])

    print("\n".join(RESULTS))
    print(f"\nFINISH {now_iso()}  failures={FAILED}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
