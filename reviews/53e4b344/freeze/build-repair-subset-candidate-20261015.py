#!/usr/bin/env python3
"""Build the bounded real-subset input for the worker-62 repair candidate.

Copies a DECLARED selection of real retained packet assets byte-exact from the
immutable input package into a NEW owned namespace, verifies every copy against
the authoritative manifest pins, and writes a subset manifest (entries verbatim
from the authoritative manifest) plus a subset declaration with the selection
rule and denominator.  Read-only toward the source package; the subset is a
review candidate, not a repair of the full package.

Usage: python3 scripts/build-repair-subset-candidate-20261015.py
"""
import hashlib
import json
import shutil
from pathlib import Path

SOURCE_ROOT = Path("/home/user/src/offmenu-data/common-bulk-food-20261014")
CANDIDATE_ROOT = Path("/home/user/src/offmenu-data/worker-062-repair-candidate-20261015")
SELECTED = [
    "packets/part-00000.jsonl.gz",   # source region: off
    "packets/part-05500.jsonl.gz",   # source region: usda-files
    "packets/part-09500.jsonl.gz",   # source region: prices
]
SELECTION_RULE = ("first packet file of each wanted representative source region "
                  "(off / usda-files / prices) probed one-line-per-file read-only; "
                  "covers the repair preflight's three representative sources")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def manifest_payload_digest(manifest):
    payload = {key: value for key, value in manifest.items() if key != "manifestSha256"}
    return sha(json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf8"))


def main():
    source_manifest_bytes = (SOURCE_ROOT / "manifest.json").read_bytes()
    source_manifest = json.loads(source_manifest_bytes)
    entries_by_key = {entry["key"]: entry for entry in source_manifest["files"]}
    input_root = CANDIDATE_ROOT / "input"
    packets = input_root / "packets"
    packets.mkdir(parents=True, exist_ok=True)
    subset_entries = []
    for key in SELECTED:
        entry = entries_by_key[key]
        source = SOURCE_ROOT / key
        data = source.read_bytes()
        if len(data) != entry["bytes"] or sha(data) != entry["sha256"]:
            raise SystemExit("source pin mismatch before copy: " + key)
        target = input_root / key
        shutil.copyfile(source, target)
        if target.read_bytes() != data:
            raise SystemExit("copy is not byte-exact: " + key)
        subset_entries.append(dict(entry))  # pins verbatim from the authoritative manifest
    subset_manifest = {
        "releaseId": "bulk-food-common-20261014-subset-worker-062-20261015",
        "subsetOf": {
            "releaseId": source_manifest["releaseId"],
            "manifestByteSha256": sha(source_manifest_bytes),
            "manifestFilesEntries": len(source_manifest["files"]),
            "packetAssets": sum(1 for e in source_manifest["files"] if e["key"].endswith(".jsonl.gz")),
        },
        "counts": {
            "packets": sum(entry.get("packets", 0) for entry in subset_entries),
        },
        "inputCoverage": {
            "complete": True,
            "expectedFiles": len(subset_entries),
            "observedFiles": len(subset_entries),
            "selectionRule": SELECTION_RULE,
            "scope": "declared subset review candidate; NOT a full-package repair; NOT corpus admission",
        },
        "files": subset_entries,
    }
    subset_manifest["manifestSha256"] = manifest_payload_digest(subset_manifest)
    (input_root / "manifest.json").write_text(json.dumps(subset_manifest, ensure_ascii=False, indent=2) + "\n")
    declaration = {
        "schemaVersion": "offmenu-repair-subset-declaration/1",
        "owner": "Worker 05 (worktree slot 62), coordinator lane writer",
        "namespace": str(CANDIDATE_ROOT),
        "sourcePackage": str(SOURCE_ROOT),
        "sourceManifestByteSha256": sha(source_manifest_bytes),
        "selectedAssets": [
            {"key": key, "sha256": entries_by_key[key]["sha256"], "bytes": entries_by_key[key]["bytes"],
             "packets": entries_by_key[key].get("packets")}
            for key in SELECTED
        ],
        "denominator": f"{len(SELECTED)}/9797 packet assets",
        "selectionRule": SELECTION_RULE,
        "scope": ("bounded real repair-package candidate via the unchanged pinned repair path; "
                  "per-asset checkpoint + manifest output; independent review required before any expansion; "
                  "full 9,797-asset scan and blind relaunch remain forbidden; original orphaned lock and "
                  "legacy 414-file partial untouched"),
    }
    (CANDIDATE_ROOT / "SUBSET-DECLARATION.json").write_text(json.dumps(declaration, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"input": str(input_root), "assets": len(subset_entries),
                      "packets": subset_manifest["counts"]["packets"],
                      "manifestSha256": subset_manifest["manifestSha256"]}, indent=2))


if __name__ == "__main__":
    main()
