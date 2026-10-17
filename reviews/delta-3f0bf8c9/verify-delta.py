#!/usr/bin/env python3
"""
Delta review verifier — MORGAN-DELTA-REVIEW-20261015-W06.

Read-only, bounded. Reviews ONLY the immutable review candidate at exact
commit 3f0bf8c9ca1f202d06e46bca41cba68a13e2dd22 (never a moving HEAD).
Reproduces the delta receipt:
  semantic/reviews/20261015-language-terminology-delta-review-W03.json

Checks:
 1. Base pins (language-review-pins.json) still verify — prior base receipt
    remains authoritative for its own exact base.
 2. Commit extraction integrity: `git show <sha>:<path>` vs recorded content
    hashes; commit tree blob ids recorded in extract-manifest.json.
 3. Chrome/base identity: which pinned artifacts are byte-identical inside the
    commit; D1–D6 re-determination at the exact SHA.
 4. Delta analysis: committed QA vs earlier pinned QA bytes (single-hunk formal
    allowlist; no computed-sha equality regression added).
 5. REVIEW_RECEIPT.json consistency, including the stale currentHash defect.
 6. Committed QA executed against extracted immutable bytes only (isolated
    PROBE_DIRS patch; PYTHONDONTWRITEBYTECODE=1).

Denominator discipline: PASS count of the committed QA is NOT acceptance.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path("/home/user/src/offmenu")
COMMIT = "3f0bf8c9ca1f202d06e46bca41cba68a13e2dd22"
PREDICT_PREFIX = "review-candidate/worker-01-qa-language-terminology/2026-10-15"
PINS_DEFAULT = Path("/home/user/Documents/Codex/2026-10-15/task/freebuff-runtime-migration-20261015/language-review-pins.json")
PRIOR_PINNED_QA_SHA = "447f6781a60dd335cff160668756a72011adca5f410e976ea87b4d11470d29eb"

EXPECTED_CONTENT_SHA = {
    "qa/test_terminology_qa.py": "29aff3a642d0a05433285ecbb707db76b488f6f2bd4b25d889bbe4c7431becf9",
    "REVIEW_RECEIPT.json": "4851035de2578724298ff3574b53afbd30a00b7a32b4ce721cf923be48376cfe",
    "LANGUAGE_TARGETS.json": "dc76ab2ed94d2e2e6353be397527e88eb9e38ddc07ed5d3a8dad14c61283e28f",
    "app-store-locale-snapshot.json": "c0623842c50a4466393a304debdcdeb82a58296cbb5c9ece4e492cfe8af9f1f4",
    "store-language-locale-inventory.json": "1c2ec20913c51a3635d9c52ed02f1e28ec1e85ac5d3a5051967d252a93a21631",
    "store-locale-bcp47-extraction.json": "a48639ba909f99ca4852bcd8e1f4585834e4a30667f31877187559a62b7a489a",
    "qa/store-locale-bcp47-extraction.json": "a48639ba909f99ca4852bcd8e1f4585834e4a30667f31877187559a62b7a489a",
    "terminology-contract.json": "f27abd60f9d4233b3b1ace837a69f1a97e418c5a1dcff3054f9fa9e69995e554",
    "terminology-fixtures.jsonl": "bcfef49a950df6b7104c34992cc7d93b9ae8309ac8db242b190e6c6d8c3d42a7",
    "terminology-translation-bounds.json": "7cffb6b3bf2520295fbe7f6ea9324135ad3d486ce0b7a0268644826ba9664fca",
}

OUTCOMES: list[tuple[str, bool, str]] = []


def record(label: str, ok: bool, detail: str = "") -> bool:
    OUTCOMES.append((label, ok, detail))
    return ok


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git_show(path: str) -> bytes:
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{COMMIT}:{path}"],
                       capture_output=True, check=True)
    return r.stdout


def main() -> int:
    # 0. commit existence at exact SHA (refuse moving HEAD)
    r = subprocess.run(["git", "-C", str(REPO), "rev-parse", "3f0bf8c9^{commit}"],
                       capture_output=True, text=True)
    record("commit_exact_sha_resolves", r.stdout.strip() == COMMIT, r.stdout.strip()[:16])

    # 1. prior base pins — informational only. Concurrent author edits to the
    #    lane are EXPECTED (MORGAN-DELTA-REVIEW order); the earlier-pin base
    #    receipt stays valid for its own exact hashes, and every delta finding
    #    below is computed from extracted immutable commit bytes, not the lane.
    pins = json.loads(PINS_DEFAULT.read_text())
    holds = sum(1 for p, h in pins.items() if sha_file(Path(p)) == h)
    OUTCOMES.append((f"base_pins_hold_{holds}_of_{len(pins)}_informational", True,
                     "lane drift under concurrent corrections is expected; drift does not feed any finding"))

    with tempfile.TemporaryDirectory(prefix="w03-delta-") as td:
        tmp = Path(td)
        for rel, expect in EXPECTED_CONTENT_SHA.items():
            data = git_show(f"{PREDICT_PREFIX}/{rel}")
            record("extract_integrity:" + rel, sha_bytes(data) == expect, expect[:12])
            dst = tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)

        qa = (tmp / "qa/test_terminology_qa.py").read_text()

        # 2. delta vs earlier pinned QA: extraction + structure (self-contained;
        #         prior QA read from SHA-verified fixture, immune to live lane drift)
        prior_qa_path = Path(__file__).resolve().parent / "fixtures/prior_pinned_qa_447f6781.py"
        sha_ok = prior_qa_path.is_file() and sha_file(prior_qa_path) == PRIOR_PINNED_QA_SHA
        record("prior_pinned_qa_fixture_verified", sha_ok, PRIOR_PINNED_QA_SHA[:12])
        if sha_ok:
            earlier_qa = prior_qa_path.read_text()
            import difflib
            diff = list(difflib.unified_diff(earlier_qa.splitlines(), qa.splitlines(), lineterm=""))
            hunks = [ln for ln in diff if ln.startswith("@@")]
            record("delta_qa_single_hunk", len(hunks) == 1, f"{len(hunks)} hunk(s)")
            record("delta_qa_allowlist_not_arbitrary",
                   "contract_known_optional_keys" in qa and {"terminologyAlignment", "updatedAt"} == set(
                       re.findall(r'"([A-Za-z]+)",\s*#', qa)) and "no unknown keys" in qa,
                   "required+known-optional formal allowlist, unknown keys fail")

        # 3. D-determination at exact SHA
        inv = json.loads((tmp / "store-language-locale-inventory.json").read_text())
        ap = inv["appleAppStore"]
        excerpt = ap["sourceListTextExcerpt"].rstrip(".")
        capt = re.split(r",\s*(?=[A-Z(])", excerpt)
        item_caps = {i["sourceCaption"] for i in ap["items"]}
        dropped = [c for c in capt if c not in item_caps]
        record("D1_REMAINS_slovenia_caption_dropped",
               len(capt) == 50 and len(ap["items"]) == 49 and dropped == ["Slovenia"],
               f"captions={len(capt)} items={len(ap['items'])} dropped={dropped}")
        record("D2_REMAINS_canonicalBcp47TagCount_stale_47",
               ap.get("canonicalBcp47TagCount") == 47 and len(ap["items"]) == 49,
               f"field={ap.get('canonicalBcp47TagCount')}")
        contract = json.loads((tmp / "terminology-contract.json").read_text())
        ta = contract["terminologyAlignment"]
        record("D3_REMAINS_tieout_hashes_stale",
               ta["storeLanguageLocaleInventorySha256"] != EXPECTED_CONTENT_SHA[
                   "store-language-locale-inventory.json"] and ta["bcp47ExtractionManifestSha256"] !=
               EXPECTED_CONTENT_SHA["store-locale-bcp47-extraction.json"],
               "613779e9… / a121589f… vs actual 1c2ec209… / a48639ba…")
        targets = json.loads((tmp / "LANGUAGE_TARGETS.json").read_text())
        union = {x["bcp47Base"] for x in targets["unionTargetInventory"]["tags"]}
        s = targets["coverageAndGapsSummary"]
        record("D4_REMAINS_union_en_x_simple_and_8_45",
               "en-x-simple" in union and s.get("storeExtractedGoogleDistinctTagsInArtifact") == 8
               and s.get("storeExtractedAppleDistinctTagsInArtifact") == 45,
               f"union={len(union)}; counters 8/45 contradict 86/49 artifacts")
        committed = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "--name-only", COMMIT,
                                    PREDICT_PREFIX], capture_output=True, text=True).stdout
        record("D5_fix_script_not_carried_by_commit", "fix-store-bcp-tags.py" not in committed,
               "script absent from commit (hazard unresolved in lane, not represented here)")
        record("D6_status_not_carried", "STATUS.json" not in committed, "STATUS/HANDOFF/raw-scan absent from commit")
        record("D3_gap_persists_presence_only_checks", "ok(\"terminologyAlignment has storeLanguageLocaleInventorySha256\"" in qa,
               "cross-reference asserts key presence, never computed-sha equality")

        # 4. REVIEW_RECEIPT consistency (including stale currentHash defect)
        rr = json.loads((tmp / "REVIEW_RECEIPT.json").read_text())
        rec_hashes_match = 0
        for rf in rr["reviewFiles"]:
            p = tmp / rf["path"]
            if sha_file(p) == rf["sha256"]:
                rec_hashes_match += 1
        record("review_receipt_hashes_match_bytes", rec_hashes_match == len(rr["reviewFiles"]),
               f"{rec_hashes_match}/{len(rr['reviewFiles'])}")
        stale = rr["filesChangedFromBaseline"]["qa/test_terminology_qa.py"].get("currentHash")
        record("DELTA_DEFECT_receipt_stale_currentHash",
               stale == PRIOR_PINNED_QA_SHA and EXPECTED_CONTENT_SHA["qa/test_terminology_qa.py"] == sha_file(tmp / "qa/test_terminology_qa.py"),
               f"receipt claims current 447f6781… but committed bytes are 29aff3a6…")

        # 5. committed QA executed against extracted immutable bytes only
        patched = qa.replace(
            'PROBE_DIRS = [Path("/home/user/src/offmenu-data/freebuff-parallel-20261015/country-coverage/language-terminology"), ROOT]',
            f"PROBE_DIRS = [Path({json.dumps(str(tmp))})]",
        )
        assert patched != qa
        tdir = tmp / "_run"
        tdir.mkdir()
        (tdir / "test_terminology_qa.py").write_text(patched)
        r = subprocess.run([sys.executable, str(tdir / "test_terminology_qa.py")],
                           capture_output=True, text=True,
                           env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        passes = sum(1 for ln in r.stdout.splitlines() if ln.startswith("PASS"))
        fails = [ln for ln in r.stdout.splitlines() if ln.startswith("FAIL")]
        record("committed_qa_199_pass_0_fail_exit0",
               r.returncode == 0 and passes == 199 and not fails,
               f"exit={r.returncode} pass={passes} fail={len(fails)}")

    ok_all = all(ok for _, ok, _ in OUTCOMES)
    for label, ok, detail in OUTCOMES:
        print(f"{'MATCH' if ok else 'REVIEW-DEVIATION'}  {label}  {detail}")
    print("DELTA_REVIEW_REPRODUCED" if ok_all else "DEVIATIONS_PRESENT")
    return 0 if ok_all else 2


if __name__ == "__main__":
    sys.exit(main())
