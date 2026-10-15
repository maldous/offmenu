#!/usr/bin/env python3
"""
Deterministic read-only verifier for the 2026-10-15 language-terminology QA
candidate review by Worker 03 (OFFMENU-REVIEW-20261015-language-terminology-W03).

Purpose: make the review receipt's findings reproducible. Runs only reads.
Exit codes: 0 = all checks produced expected outcomes; 2 = any check disagreed
with the receipt's claims; 3 = environment error (missing pinned file).

Usage:
  python3 verify-language-terminology-pins-20261015.py \
    [--pins /home/user/Documents/Codex/2026-10-15/task/freebuff-runtime-migration-20261015/language-review-pins.json]

This tool belongs to Worker 03 and must not write into the reviewed lane.
"""
from __future__ import annotations

import argparse
import json
import re
import hashlib
import sys
from pathlib import Path

LANE = Path("/home/user/src/offmenu-data/freebuff-parallel-20261015/country-coverage/language-terminology")
DEFAULT_PINS = Path("/home/user/Documents/Codex/2026-10-15/task/freebuff-runtime-migration-20261015/language-review-pins.json")

OUTCOMES: list[tuple[str, bool, str]] = []


def record(label: str, ok: bool, detail: str = "") -> bool:
    OUTCOMES.append((label, ok, detail))
    return ok


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pins", default=str(DEFAULT_PINS))
    args = ap.parse_args()

    try:
        pins = json.loads(Path(args.pins).read_text(encoding="utf-8"))
    except OSError as e:
        print(f"environment error: cannot read pins file {args.pins}: {e}", file=sys.stderr)
        return 3

    # 1. pin verification (pre-review gate)
    verified = all(sha256_file(Path(p)) == h for p, h in pins.items())
    record("pins_verified_before_review", verified, f"{sum(1 for p, h in pins.items() if sha256_file(Path(p)) == h)}/{len(pins)}")
    if not verified:
        print("pin failure: refusing to produce findings against moving artifacts", file=sys.stderr)
        return 3

    inv = json.loads((LANE / "store-language-locale-inventory.json").read_text(encoding="utf-8"))
    ext = json.loads((LANE / "store-locale-bcp47-extraction.json").read_text(encoding="utf-8"))
    contract = json.loads((LANE / "terminology-contract.json").read_text(encoding="utf-8"))
    targets = json.loads((LANE / "LANGUAGE_TARGETS.json").read_text(encoding="utf-8"))
    raw = json.loads((LANE / "_raw_language_scan.json").read_text(encoding="utf-8"))
    status = json.loads((LANE / "STATUS.json").read_text(encoding="utf-8"))
    qa_ext = json.loads((LANE / "qa/store-locale-bcp47-extraction.json").read_text(encoding="utf-8"))

    # 2. root vs qa extraction identity
    record("qa_extraction_is_byte_copy_of_root", sha256_file(LANE / "qa/store-locale-bcp47-extraction.json") == sha256_file(LANE / "store-locale-bcp47-extraction.json"), "a48639ba…")

    # 3. candidate counts
    gp_rows = ext["googlePlay"]["rows"]
    ap_rows = ext["appleAppStore"]["rows"]
    gp_tags = {r["canonicalBcp47"] for r in gp_rows}
    ap_tags = {r["canonicalBcp47"] for r in ap_rows}
    record("google_rows_86_distinct_86", len(gp_rows) == 86 and len(gp_tags) == 86, f"{len(gp_rows)}/{len(gp_tags)}")
    record("apple_rows_49_distinct_49", len(ap_rows) == 49 and len(ap_tags) == 49, f"{len(ap_rows)}/{len(ap_tags)}")
    record("combined_distinct_114", len(gp_tags | ap_tags) == 114, str(len(gp_tags | ap_tags)))
    record("overlap_21", len(gp_tags & ap_tags) == 21, str(len(gp_tags & ap_tags)))

    # 4. D1 — Apple excerpt caption count vs inventory items (silent caption drop)
    excerpt = inv["appleAppStore"]["sourceListTextExcerpt"].rstrip(".")
    capt = re.split(r",\s*(?=[A-Z(])", excerpt)
    items = inv["appleAppStore"]["items"]
    item_caps = {i["sourceCaption"] for i in items}
    dropped = [c for c in capt if c not in item_caps]
    record("D1_apple_dropped_captions_detected", len(capt) != len(items) and len(dropped) == 1, f"captions={len(capt)} items={len(items)} dropped={dropped}")

    # 5. D2 — stale apple canonical count field
    record("D2_apple_canonicalBcp47TagCount_stale_47_not_49", inv["appleAppStore"].get("canonicalBcp47TagCount") == 47 and len(items) == 49, f"field={inv['appleAppStore'].get('canonicalBcp47TagCount')}")

    # 6. D3 — contract terminologyAlignment tie-out hash staleness
    ta = contract["terminologyAlignment"]
    stale_inv = ta["storeLanguageLocaleInventorySha256"] != sha256_file(LANE / "store-language-locale-inventory.json")
    stale_ext = ta["bcp47ExtractionManifestSha256"] != sha256_file(LANE / "store-locale-bcp47-extraction.json")
    record("D3_contract_tieout_inventory_sha_stale", stale_inv, ta["storeLanguageLocaleInventorySha256"][:16])
    record("D3_contract_tieout_extraction_sha_stale", stale_ext, ta["bcp47ExtractionManifestSha256"][:16])

    # 7. D4 — union not rebuilt per unionPrinciple
    def base_of(tag: str) -> str:
        return tag.split("-")[0]

    obs = {e["tag"] for e in targets["observedDatasetLanguages"]["observedTagsFromBoundedScan"]}
    union = {x["bcp47Base"] for x in targets["unionTargetInventory"]["tags"]}
    rebuilt = {base_of(t) for t in obs} | {base_of(t) for t in gp_tags} | {base_of(t) for t in ap_tags}
    summary = targets["coverageAndGapsSummary"]
    record("D4_union_smallerso_than_principle_recompute", len(union) == 46 and len(rebuilt) == 74, f"union={len(union)} rebuilt={len(rebuilt)}")
    record("D4_summary_8_45_contradicts_86_49", summary.get("storeExtractedGoogleDistinctTagsInArtifact") == 8 and summary.get("storeExtractedAppleDistinctTagsInArtifact") == 45, "declared 8/45 vs artifacts 86/49")
    record("D4_en_x_simple_stored_as_own_base", "en-x-simple" in union, "private-use singleton stored as bcp47Base")

    # 8. D5 — fix script cannot reproduce candidate
    src = (LANE / "qa/fix-store-bcp-tags.py").read_text(encoding="utf-8")
    ns = {"__name__": "review_probe", "__file__": str(LANE / "qa/fix-store-bcp-tags.py")}
    exec(compile(src, "fix-store-bcp-tags.py", "exec"), ns)  # noqa: S102 - deliberate, read-only probe
    g_au = ns["google_parse_one"]("English (Australia)")
    a_ca = ns["apple_parse_one"]("English (Canada)")
    record("D5_google_parenthetical_caption_region_dropped", g_au["inferredTag"] == "en" and g_au["explicitTag"] is None, json.dumps(g_au, ensure_ascii=False))
    record("D5_apple_country_region_token_not_subtagged", a_ca["inferredTag"] == "en" and a_ca["regionToken"] == "Canada", json.dumps(a_ca, ensure_ascii=False))
    record("D5 DEST_targets_qa_candidate", 'DEST = Path(__file__).resolve().parent / "store-locale-bcp47-extraction.json"' in src, "line 22")

    # 9. D6 — STATUS self-hash irreproducibility
    status_actual = sha256_file(LANE / "STATUS.json")
    claimed = {
        "STATUS_sha256_after_run": status.get("STATUS_sha256_after_run"),
        "fileHashes.STATUS.json": status.get("fileHashes", {}).get("STATUS.json"),
    }
    none_match = all(v is not None and v != status_actual for v in claimed.values())
    record("D6_status_selfhashes_stale", none_match, f"actual={status_actual[:16]}")

    # 10. scan consistency (first-match rebuild)
    first = raw["top_first_tags"]
    record("first_match_counts_sum_equals_tagged_records", sum(first.values()) == raw["tagged_records"] == 25135, f"sum={sum(first.values())}")
    record("distinct_tags_32_everywhere", raw["distinct_first_tags"] == len(first) == 32, str(len(first)))

    ok_all = all(ok for _, ok, _ in OUTCOMES)
    for label, ok, detail in OUTCOMES:
        print(f"{'MATCH' if ok else 'REVIEW-DEVIATION'}  {label}  {detail}")
    print("ALL_REVIEW_CLAIMS_REPRODUCED" if ok_all else "DEVIATIONS_PRESENT")
    return 0 if ok_all else 2


if __name__ == "__main__":
    sys.exit(main())
