"""Bounded, read-only source comparison for retained bulk repair files.

This produces a recovery inspection receipt, never an admission manifest. It
does not resume jobs, modify a partial, or silently accept a truncated file.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
from itertools import zip_longest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("offmenu_bulk_repair", ROOT / "scripts/repair-bulk-controls-20261014.py")
REPAIR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPAIR)


def digest_file(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safe_path(root, key):
    relative = Path(key)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("unsafe asset key: " + key)
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("asset escapes retained root: " + key)
    return path


def verify_asset(source_root, retained_root, entry):
    key = entry["key"]
    original = safe_path(source_root, key)
    retained = safe_path(retained_root, key)
    # A corrupt original is an inspection blocker, never just a held output.
    if original.stat().st_size != entry["bytes"] or digest_file(original) != entry["sha256"]:
        raise ValueError("original asset checksum mismatch: " + key)
    result = {"key": key, "inputByteSha256": entry["sha256"], "status": "missing", "verifiedPackets": 0}
    if not retained.exists():
        return result
    result.update({"retainedBytes": retained.stat().st_size, "retainedByteSha256": digest_file(retained)})
    try:
        if not key.endswith(".jsonl.gz"):
            if result["retainedByteSha256"] != entry["sha256"]:
                raise ValueError("copied auxiliary asset differs from original")
        else:
            with gzip.open(original, "rt", encoding="utf8") as left, gzip.open(retained, "rt", encoding="utf8") as right:
                for input_line, output_line in zip_longest(left, right):
                    if input_line is None or output_line is None:
                        raise ValueError("input/output packet count mismatch")
                    expected, _ = REPAIR.repair_packet(json.loads(input_line))
                    if expected != json.loads(output_line):
                        raise ValueError("retained packet differs from exact authorized repair")
                    result["verifiedPackets"] += 1
            if result["verifiedPackets"] != entry["packets"]:
                raise ValueError("packet count differs from source manifest")
        result["status"] = "source-compared-complete-asset"
    except (EOFError, OSError, ValueError, KeyError, StopIteration) as error:
        result["status"] = "held-not-reusable"
        result["error"] = type(error).__name__ + ": " + str(error)
    return result


def inspect(source_root, retained_root, keys, limit):
    if not 1 <= limit <= 100 or len(keys) > limit or len(set(keys)) != len(keys):
        raise ValueError("inspection requires 1..100 files and unique selectors within limit")
    manifest = REPAIR.read_manifest(source_root)
    entries = {entry["key"]: entry for entry in manifest["files"]}
    if len(entries) != len(manifest["files"]):
        raise ValueError("duplicate source asset keys")
    if not keys:
        keys = [entry["key"] for entry in manifest["files"] if entry["key"].endswith(".jsonl.gz")][:limit]
    if any(key not in entries for key in keys):
        raise ValueError("selected file is absent from input manifest")
    assets = [verify_asset(source_root, retained_root, entries[key]) for key in keys]
    return {
        "schemaVersion": "offmenu-bulk-recovery-inspection/1",
        "status": "bounded-source-comparison-not-package-qualification",
        "complete": False,
        "limit": limit,
        "sourceDirectory": str(source_root.resolve()),
        "retainedDirectory": str(retained_root.resolve()),
        "inputManifestByteSha256": digest_file(source_root / "manifest.json"),
        "repairImplementationByteSha256": digest_file(ROOT / "scripts/repair-bulk-controls-20261014.py"),
        "schemaByteSha256": digest_file(ROOT / "corpus/common-data.schema.json"),
        "contractByteSha256": digest_file(ROOT / "corpus/common-data-contract.json"),
        "assets": assets,
        "usableAssets": sum(item["status"] == "source-compared-complete-asset" for item in assets),
        "rule": "Only inspected complete files match the original source under the single authorized transform repair. All uninspected assets remain unresolved. Full schema/identity/reference/source coverage qualification is still required; no file was changed or job resumed.",
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=REPAIR.OLD_ROOT)
    p.add_argument("--retained", type=Path, default=REPAIR.NEW_ROOT)
    p.add_argument("--file-limit", type=int, default=3)
    p.add_argument("--key", action="append", default=[])
    p.add_argument("--receipt", type=Path, required=True)
    a = p.parse_args()
    if a.receipt.resolve().is_relative_to(a.input.resolve()) or a.receipt.resolve().is_relative_to(a.retained.resolve()):
        p.error("receipt must be outside immutable source and retained partial directories")
    result = inspect(a.input, a.retained, a.key, a.file_limit)
    # Exclusive creation preserves earlier inspection receipts.
    with a.receipt.open("x", encoding="utf8") as handle:
        handle.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "inspected": len(result["assets"]), "usableAssets": result["usableAssets"]}))
