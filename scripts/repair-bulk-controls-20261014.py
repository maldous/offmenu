#!/usr/bin/env python3
"""Make the narrowly-scoped semantic repair for the bulk-food common graph.

The original package is immutable input.  This program verifies every listed
asset before opening an output directory, then streams each gzip member to its
replacement.  The only graph mutation is the curation control
``provenance.transform``: it is a fixed identifier, not localisable text.
"""
import argparse
import copy
import gzip
import hashlib
import json
import os
import shutil
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


OLD_ROOT = Path("/home/user/src/offmenu-data/common-bulk-food-20261014")
NEW_ROOT = Path("/home/user/src/offmenu-data/common-bulk-food-semantic-final-20261014")
CONTROL_PATH = (
    "value", "fields", "provenance", "fields", "transform"
)
CONTROL_VALUE = "offmenu-curation/1"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def manifest_payload_digest(manifest):
    payload = {key: value for key, value in manifest.items() if key != "manifestSha256"}
    return sha(json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf8"))


def read_manifest(root):
    data = (root / "manifest.json").read_bytes()
    manifest = json.loads(data)
    if manifest_payload_digest(manifest) != manifest.get("manifestSha256"):
        raise ValueError("input manifest payload digest mismatch")
    return manifest


def verify_input(root, manifest):
    """Verify every pre-repair asset before any repaired file is made."""
    for entry in manifest["files"]:
        path = root / entry["key"]
        data = path.read_bytes()
        if len(data) != entry["bytes"] or sha(data) != entry["sha256"]:
            raise ValueError("input asset digest mismatch: " + entry["key"])


def control_node(packet):
    assertion = next(
        item for item in packet["assertions"]
        if item["propertyId"] == "urn:offmenu:property:curatedRecordContext"
    )
    node = assertion
    for key in CONTROL_PATH:
        node = node[key]
    return node


def contains_string(value, needle):
    if isinstance(value, str):
        return value == needle
    if isinstance(value, list):
        return any(contains_string(item, needle) for item in value)
    if isinstance(value, dict):
        return any(contains_string(item, needle) for item in value.values())
    return False


def repair_packet(packet):
    """Return a copy with exactly the control node changed and prove it."""
    result = copy.deepcopy(packet)
    old = control_node(result)
    if not (
        isinstance(old, dict)
        and old.get("kind") == "text"
        and old.get("value") == CONTROL_VALUE
        and isinstance(old.get("id"), str)
    ):
        raise ValueError("unexpected provenance.transform control shape")
    old_id = old["id"]
    old_value = copy.deepcopy(old)
    replacement = {"kind": "identifier", "value": CONTROL_VALUE}
    assertion = next(
        item for item in result["assertions"]
        if item["propertyId"] == "urn:offmenu:property:curatedRecordContext"
    )
    parent = assertion
    for key in CONTROL_PATH[:-1]:
        parent = parent[key]
    parent[CONTROL_PATH[-1]] = replacement
    if contains_string(result, old_id):
        raise ValueError("removed text id remains referenced in packet: " + old_id)
    restored = copy.deepcopy(result)
    restore_assertion = next(
        item for item in restored["assertions"]
        if item["propertyId"] == "urn:offmenu:property:curatedRecordContext"
    )
    restore_parent = restore_assertion
    for key in CONTROL_PATH[:-1]:
        restore_parent = restore_parent[key]
    restore_parent[CONTROL_PATH[-1]] = old_value
    if restored != packet:
        raise ValueError("repair attempted to change data outside provenance.transform")
    return result, old_id


def representative_checks(root, manifest):
    """Inspect a real row from each input before the full streaming repair."""
    wanted = {"off", "usda-files", "prices"}
    found = {}
    for entry in manifest["files"]:
        if len(found) == len(wanted):
            break
        if not entry["key"].endswith(".jsonl.gz"):
            continue
        with gzip.open(root / entry["key"], "rt", encoding="utf8") as handle:
            for line in handle:
                packet = json.loads(line)
                source = packet["citations"][0]["sourceId"]
                if source not in wanted or source in found:
                    continue
                node = control_node(packet)
                if node.get("kind") != "text" or node.get("value") != CONTROL_VALUE:
                    raise ValueError("representative control is not the known faulty value")
                nutrient_metadata = sum(
                    1 for assertion in packet["assertions"]
                    if assertion["propertyId"] == "urn:offmenu:property:sourceNutrientMetadata"
                )
                found[source] = {
                    "packetFile": entry["key"],
                    "control": {"kind": node["kind"], "value": node["value"]},
                    "nutrientMetadataAssertions": nutrient_metadata,
                }
                break
    if set(found) != wanted:
        raise ValueError("could not find all three representative sources")
    return found


def normalize_input_coverage(value):
    """Retain per-source evidence while adding current admission aggregate fields."""
    if value.get("complete") is True:
        return value
    source_entries = value
    if not all(isinstance(item, dict) for item in source_entries.values()):
        raise ValueError("unexpected inputCoverage shape")
    return {
        "complete": all(item.get("complete") is True for item in source_entries.values()),
        "expectedFiles": sum(item["expectedFiles"] for item in source_entries.values()),
        "observedFiles": sum(item["observedFiles"] for item in source_entries.values()),
        "sources": source_entries,
    }


def repair_asset(input_root, output_root, entry):
    """Repair one immutable asset through an atomic sibling temporary file."""
    source = input_root / entry["key"]
    target = output_root / entry["key"]
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp." + str(os.getpid()))
    if temporary.exists():
        temporary.unlink()
    changed = 0
    try:
        if not entry["key"].endswith(".jsonl.gz"):
            shutil.copyfile(source, temporary)
        else:
            with gzip.open(source, "rt", encoding="utf8") as reader, temporary.open("wb") as raw:
                with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=1, mtime=0) as writer:
                    for line in reader:
                        packet = json.loads(line)
                        repaired, _ = repair_packet(packet)
                        writer.write((compact(repaired) + "\n").encode("utf8"))
                        changed += 1
        data = temporary.read_bytes()
        result = {
            "key": entry["key"], "bytes": len(data), "sha256": sha(data),
            **({"packets": entry["packets"]} if "packets" in entry else {}),
        }
        os.replace(temporary, target)
        return result, changed
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def repair_asset_task(task):
    return repair_asset(*task)


def repair(input_root, output_root, workers=6):
    manifest = read_manifest(input_root)
    verify_input(input_root, manifest)
    representatives = representative_checks(input_root, manifest)
    if output_root.exists():
        raise ValueError("output already exists: " + str(output_root))
    output_root.mkdir(parents=True)
    repaired_files = []
    changed_packets = 0
    removed_ids = 0
    task_args = [(input_root, output_root, entry) for entry in manifest["files"]]
    if workers == 1:
        results = [repair_asset(*task) for task in task_args]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            # executor.map returns input order, making the final asset manifest
            # deterministic even though files finish independently.
            results = list(pool.map(repair_asset_task, task_args))
    for asset, changed in results:
        repaired_files.append(asset)
        changed_packets += changed
        removed_ids += changed
    repaired = {key: value for key, value in manifest.items() if key not in {"files", "manifestSha256", "releaseId", "status", "inputCoverage"}}
    repaired["releaseId"] = "bulk-food-common-semantic-final-20261014"
    repaired["status"] = "full-schema-identity-citation-public-scope-checked-semantic-control-repaired"
    repaired["inputCoverage"] = normalize_input_coverage(manifest["inputCoverage"])
    repaired["files"] = repaired_files
    repaired["repair"] = {
        "repairOf": {"releaseId": manifest["releaseId"], "manifestSha256": manifest["manifestSha256"], "directory": str(input_root)},
        "rule": "curatedRecordContext.fields.provenance.fields.transform text to identifier",
        "preservedValue": CONTROL_VALUE,
        "changedPackets": changed_packets,
        "removedUnusedTextIds": removed_ids,
        "representativePreflight": representatives,
        "inputAssetsVerified": len(manifest["files"]),
        "streaming": True,
    }
    repaired["manifestSha256"] = manifest_payload_digest(repaired)
    (output_root / "manifest.json").write_text(json.dumps(repaired, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    return repaired


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=OLD_ROOT)
    parser.add_argument("--output", type=Path, default=NEW_ROOT)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be positive")
    result = repair(args.input, args.output, args.workers)
    print(json.dumps({"releaseId": result["releaseId"], "counts": result["counts"], "repair": result["repair"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
