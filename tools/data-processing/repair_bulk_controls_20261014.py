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
from itertools import zip_longest


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
        path = asset_path(root, entry["key"])
        data = path.read_bytes()
        if len(data) != entry["bytes"] or sha(data) != entry["sha256"]:
            raise ValueError("input asset digest mismatch: " + entry["key"])


def asset_path(root, key):
    relative = Path(key)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("unsafe asset key: " + key)
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("asset escapes root: " + key)
    return path


def checkpoint_pins(input_root):
    root = Path(__file__).resolve().parents[2]
    return {
        "inputManifestByteSha256": sha((input_root / "manifest.json").read_bytes()),
        "schemaByteSha256": sha((root / "contracts/corpus/common-data.schema.json").read_bytes()),
        "contractByteSha256": sha((root / "contracts/corpus/common-data-contract.json").read_bytes()),
        "repairImplementationByteSha256": sha(Path(__file__).read_bytes()),
        "sourceDirectory": str(input_root.resolve()),
    }


def write_checkpoint(path, value):
    temporary = path.with_name(path.name + ".writing")
    with temporary.open("w", encoding="utf8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def verify_retained_asset(input_root, output_root, entry):
    """Reconcile an atomic output against source, including unjournaled work."""
    source = asset_path(input_root, entry["key"])
    target = asset_path(output_root, entry["key"])
    changed = 0
    if not entry["key"].endswith(".jsonl.gz"):
        if source.read_bytes() != target.read_bytes():
            raise ValueError("retained auxiliary differs from original")
    else:
        with gzip.open(source, "rt", encoding="utf8") as left, gzip.open(target, "rt", encoding="utf8") as right:
            for original, retained in zip_longest(left, right):
                if original is None or retained is None:
                    raise ValueError("retained/source packet count mismatch")
                expected, _ = repair_packet(json.loads(original))
                if json.loads(retained) != expected:
                    raise ValueError("retained packet differs from authorized repair")
                changed += 1
        if changed != entry["packets"]:
            raise ValueError("retained packet count differs from input manifest")
    data = target.read_bytes()
    return {"key": entry["key"], "bytes": len(data), "sha256": sha(data), **({"packets": entry["packets"]} if "packets" in entry else {})}, changed


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
    source = asset_path(input_root, entry["key"])
    target = asset_path(output_root, entry["key"])
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
                with gzip.GzipFile(filename="", fileobj=raw, mode="wb", compresslevel=1, mtime=0) as writer:
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


def repair(input_root, output_root, workers=6, resume=False):
    """Own one repair writer; stale locks require explicit custody reconciliation."""
    if input_root.resolve() == output_root.resolve():
        raise ValueError("immutable input cannot be output")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    lock = output_root.with_name(output_root.name + ".repair.lock")
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise ValueError("repair writer lock exists; reconcile live or stale ownership explicitly: " + str(lock)) from error
    identity = os.fstat(descriptor)
    try:
        with os.fdopen(descriptor, "w", encoding="utf8") as handle:
            handle.write(json.dumps({"pid": os.getpid(), "input": str(input_root.resolve()), "output": str(output_root.resolve())}) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return repair_owned(input_root, output_root, workers, resume)
    finally:
        if lock.exists() and (lock.stat().st_dev, lock.stat().st_ino) == (identity.st_dev, identity.st_ino):
            lock.unlink()  # Only this invocation's ephemeral ownership lock.


def repair_owned(input_root, output_root, workers=6, resume=False):
    manifest = read_manifest(input_root)
    if len({entry["key"] for entry in manifest["files"]}) != len(manifest["files"]):
        raise ValueError("duplicate source asset keys")
    if input_root.resolve() == output_root.resolve():
        raise ValueError("immutable input cannot be output")
    checkpoint_path = output_root / "checkpoint.json"
    pins = checkpoint_pins(input_root)
    if output_root.exists():
        if not resume:
            raise ValueError("output already exists: " + str(output_root))
        if (output_root / "manifest.json").exists():
            raise ValueError("completed immutable output cannot be resumed")
        if not checkpoint_path.is_file():
            raise ValueError("legacy partial has no pinned checkpoint; recovery inspection required")
        checkpoint = json.loads(checkpoint_path.read_text())
        if checkpoint.get("schemaVersion") != "offmenu-bulk-repair-checkpoint/1" or checkpoint.get("pins") != pins:
            raise ValueError("checkpoint source/schema/contract/implementation pins changed")
    else:
        if resume:
            raise ValueError("resume output does not exist")
        checkpoint = {"schemaVersion": "offmenu-bulk-repair-checkpoint/1", "complete": False, "pins": pins, "assets": {}}
    verify_input(input_root, manifest)
    representatives = representative_checks(input_root, manifest)
    output_root.mkdir(parents=True, exist_ok=True)
    write_checkpoint(checkpoint_path, checkpoint)
    repaired_files = []
    changed_packets = 0
    removed_ids = 0
    entries = {entry["key"]: entry for entry in manifest["files"]}
    if any(key not in entries for key in checkpoint["assets"]):
        raise ValueError("checkpoint contains unlisted asset")
    results_by_key = {}
    task_args = []
    def record_result(result):
        asset, changed = result
        results_by_key[asset["key"]] = result
        checkpoint["assets"][asset["key"]] = {"asset": asset, "changedPackets": changed}
        write_checkpoint(checkpoint_path, checkpoint)
    # Atomic files written before a lost parent receipt are source-compared too.
    # Corrupt retained files fail closed and remain untouched for explicit recovery.
    for entry in manifest["files"]:
        key = entry["key"]
        if asset_path(output_root, key).exists():
            result = verify_retained_asset(input_root, output_root, entry)
            previous = checkpoint["assets"].get(key)
            if previous and previous != {"asset": result[0], "changedPackets": result[1]}:
                raise ValueError("checkpoint asset receipt mismatch: " + key)
            record_result(result)
        elif key in checkpoint["assets"]:
            raise ValueError("checkpoint completed asset is missing: " + key)
        else:
            task_args.append((input_root, output_root, entry))
    if workers == 1:
        for task in task_args:
            record_result(repair_asset(*task))
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for result in pool.map(repair_asset_task, task_args):
                record_result(result)
    results = [results_by_key[entry["key"]] for entry in manifest["files"]]
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
        "pinnedCheckpointVersion": checkpoint["schemaVersion"],
    }
    repaired["manifestSha256"] = manifest_payload_digest(repaired)
    write_checkpoint(output_root / "manifest.json", repaired)
    checkpoint["complete"] = True
    write_checkpoint(checkpoint_path, checkpoint)
    return repaired


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=OLD_ROOT)
    parser.add_argument("--output", type=Path, default=NEW_ROOT)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--resume", action="store_true", help="Resume only an existing pinned checkpoint; legacy partials are refused")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be positive")
    result = repair(args.input, args.output, args.workers, args.resume)
    print(json.dumps({"releaseId": result["releaseId"], "counts": result["counts"], "repair": result["repair"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
