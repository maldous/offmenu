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
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from pathlib import Path
from itertools import zip_longest


OLD_ROOT = Path("/home/user/src/offmenu-data/common-bulk-food-20261014")
NEW_ROOT = Path("/home/user/src/offmenu-data/common-bulk-food-semantic-final-20261014")
CONTROL_PATH = (
    "value", "fields", "provenance", "fields", "transform"
)
CONTROL_VALUE = "offmenu-curation/1"


class BudgetPause(Exception):
    pass


def check_deadline(deadline):
    if deadline is not None and time.monotonic() >= deadline:
        raise BudgetPause()


def stable_identity(path):
    s = path.stat()
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def verify_source_asset(path, entry):
    before = stable_identity(path)
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    if before != stable_identity(path) or before[2] != entry["bytes"] or h.hexdigest() != entry["sha256"]:
        raise ValueError("source asset changed or checksum mismatch")
    return before


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


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


def verify_input(root, manifest, deadline=None):
    """Verify every pre-repair asset before any repaired file is made."""
    for entry in manifest["files"]:
        check_deadline(deadline)
        verify_source_asset(asset_path(root, entry["key"]), entry)


def asset_path(root, key):
    relative = Path(key)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("unsafe asset key: " + key)
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("asset escapes root: " + key)
    return path


def checkpoint_pins(input_root):
    root = Path(__file__).resolve().parents[1]
    return {
        "inputManifestByteSha256": sha((input_root / "manifest.json").read_bytes()),
        "schemaByteSha256": sha((root / "corpus/common-data.schema.json").read_bytes()),
        "contractByteSha256": sha((root / "corpus/common-data-contract.json").read_bytes()),
        "repairImplementationByteSha256": sha(Path(__file__).read_bytes()),
        "sourceDirectory": str(input_root.resolve()),
    }


def write_checkpoint(path, value):
    temporary = path.with_name(path.name + ".writing." + uuid.uuid4().hex)
    with temporary.open("x", encoding="utf8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    sync_directory(path.parent)


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


def representative_checks(root, manifest, deadline=None):
    """Inspect a real row from each input before the full streaming repair."""
    wanted = {"off", "usda-files", "prices"}
    found = {}
    for entry in manifest["files"]:
        if len(found) == len(wanted):
            break
        if not entry["key"].endswith(".jsonl.gz"):
            continue
        check_deadline(deadline)
        verify_source_asset(asset_path(root, entry["key"]), entry)
        with gzip.open(root / entry["key"], "rt", encoding="utf8") as handle:
            for line in handle:
                check_deadline(deadline)
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


def repair_asset(input_root, output_root, entry, deadline=None):
    """Repair one immutable asset through an atomic sibling temporary file."""
    check_deadline(deadline)
    source = asset_path(input_root, entry["key"])
    target = asset_path(output_root, entry["key"])
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp." + uuid.uuid4().hex)
    source_identity = verify_source_asset(source, entry)
    changed = 0
    try:
        if not entry["key"].endswith(".jsonl.gz"):
            with source.open("rb") as reader, temporary.open("xb") as writer:
                shutil.copyfileobj(reader, writer, 1024 * 1024)
                writer.flush(); os.fsync(writer.fileno())
        else:
            with gzip.open(source, "rt", encoding="utf8") as reader, temporary.open("xb") as raw:
                with gzip.GzipFile(filename="", fileobj=raw, mode="wb", compresslevel=1, mtime=0) as writer:
                    for line in reader:
                        check_deadline(deadline)
                        packet = json.loads(line)
                        repaired, _ = repair_packet(packet)
                        writer.write((compact(repaired) + "\n").encode("utf8"))
                        changed += 1
                raw.flush(); os.fsync(raw.fileno())
        if source_identity != stable_identity(source):
            raise ValueError("source asset changed while repairing")
        if entry["key"].endswith(".jsonl.gz") and changed != entry["packets"]:
            raise ValueError("actual repaired packet count differs from manifest")
        data = temporary.read_bytes()
        result = {
            "key": entry["key"], "bytes": len(data), "sha256": sha(data),
            **({"packets": entry["packets"]} if "packets" in entry else {}),
        }
        check_deadline(deadline)
        os.replace(temporary, target)
        sync_directory(target.parent)
        return result, changed
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def repair_asset_task(task):
    return repair_asset(*task)


def repair(input_root, output_root, workers=6, resume=False, **options):
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
        return repair_owned(input_root, output_root, workers, resume, **options)
    finally:
        if lock.exists() and (lock.stat().st_dev, lock.stat().st_ino) == (identity.st_dev, identity.st_ino):
            lock.unlink()  # Only this invocation's ephemeral ownership lock.


def repair_owned(input_root, output_root, workers=6, resume=False, max_assets=None,
                 deadline_seconds=None, recover_from=None, reserve_bytes=0,
                 maximum_output_bytes=None, representative_keys=None):
    started = time.monotonic()
    deadline = started + deadline_seconds if deadline_seconds is not None else None
    bounded = max_assets is not None or deadline_seconds is not None
    if type(workers) is not int or not 1 <= workers <= 16:
        raise ValueError("worker count must be 1..16")
    if max_assets is not None and max_assets < 1 or deadline_seconds is not None and deadline_seconds <= 0:
        raise ValueError("invalid bounded work budget")
    if recover_from is not None:
        recover_from = Path(recover_from).resolve()
        if not recover_from.is_dir() or output_root.resolve().is_relative_to(recover_from) or recover_from.is_relative_to(output_root.resolve()):
            raise ValueError("recovery input and new output must be disjoint")
    manifest = read_manifest(input_root)
    if len({entry["key"] for entry in manifest["files"]}) != len(manifest["files"]):
        raise ValueError("duplicate source asset keys")
    if input_root.resolve() == output_root.resolve():
        raise ValueError("immutable input cannot be output")
    checkpoint_path = output_root / "checkpoint.json"
    pins = checkpoint_pins(input_root)
    if recover_from is not None:
        pins = dict(pins, recoveryDirectory=str(recover_from), recoveryOutputDirectory=str(output_root.resolve()))
    if output_root.exists():
        if not resume:
            raise ValueError("output already exists: " + str(output_root))
        if (output_root / "manifest.json").exists():
            raise ValueError("completed immutable output cannot be resumed")
        if not checkpoint_path.is_file():
            raise ValueError("legacy partial has no pinned checkpoint; recovery inspection required")
        allowed = {entry["key"] for entry in manifest["files"]} | {"checkpoint.json"}
        if any(str(p.relative_to(output_root)) not in allowed for p in output_root.rglob("*") if p.is_file()):
            raise ValueError("unreconciled output temporary or unexpected file; preserve and inspect")
        checkpoint = json.loads(checkpoint_path.read_text())
        if checkpoint.get("schemaVersion") != "offmenu-bulk-repair-checkpoint/1" or checkpoint.get("pins") != pins:
            raise ValueError("checkpoint source/schema/contract/implementation pins changed")
    else:
        if resume:
            raise ValueError("resume output does not exist")
        checkpoint = {"schemaVersion": "offmenu-bulk-repair-checkpoint/1", "complete": False, "pins": pins, "assets": {}}
        if recover_from is not None:
            checkpoint["recovery"] = {"kind": "new-run-source-verified-copy", "copied": [], "held": []}
    try:
        verify_input(input_root, manifest, deadline)
        representative_manifest = manifest
        if representative_keys is not None:
            requested = set(representative_keys)
            selected = [e for e in manifest["files"] if e["key"] in requested]
            if len(selected) != len(requested):
                raise ValueError("representative selector absent from accepted manifest")
            representative_manifest = {"files": selected}
        representatives = representative_checks(input_root, representative_manifest, deadline)
    except BudgetPause:
        return {"status": "paused-verification", "complete": False, "completedAssets": len(checkpoint["assets"]), "totalAssets": len(manifest["files"])}
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
        entry = entries[asset["key"]]
        if asset["key"].endswith(".jsonl.gz") and changed != entry["packets"]:
            raise ValueError("actual repaired packet count differs from manifest")
        results_by_key[asset["key"]] = result
        checkpoint["assets"][asset["key"]] = {"asset": asset, "changedPackets": changed}
        write_checkpoint(checkpoint_path, checkpoint)
    # Atomic files written before a lost parent receipt are source-compared too.
    # Corrupt retained files fail closed and remain untouched for explicit recovery.
    for entry in manifest["files"]:
        key = entry["key"]
        if deadline_seconds is not None and time.monotonic() - started >= deadline_seconds:
            return {"status": "paused", "complete": False, "completedAssets": len(checkpoint["assets"]), "totalAssets": len(entries)}
        if asset_path(output_root, key).exists():
            previous = checkpoint["assets"].get(key)
            if bounded and previous:
                # Exact byte receipts established by this pinned implementation;
                # all source bytes were reverified above. Never metadata-only trust.
                target = asset_path(output_root, key)
                before = target.stat()
                data = target.read_bytes()
                after = target.stat()
                asset = previous["asset"]
                if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) or asset["key"] != key or len(data) != asset["bytes"] or sha(data) != asset["sha256"]:
                    raise ValueError("checkpoint committed asset bytes changed")
                result = (asset, previous["changedPackets"])
            else:
                identity = verify_source_asset(asset_path(input_root, key), entry)
                result = verify_retained_asset(input_root, output_root, entry)
                if identity != stable_identity(asset_path(input_root, key)):
                    raise ValueError("source changed while reconciling output")
            if previous and previous != {"asset": result[0], "changedPackets": result[1]}:
                raise ValueError("checkpoint asset receipt mismatch: " + key)
            if previous is None:
                record_result(result)
            else:
                if key.endswith(".jsonl.gz") and result[1] != entry["packets"]:
                    raise ValueError("checkpoint packet count mismatch")
                results_by_key[key] = result
        elif key in checkpoint["assets"]:
            raise ValueError("checkpoint completed asset is missing: " + key)
        else:
            task_args.append((input_root, output_root, entry))
    processed = 0
    for task in task_args if workers == 1 else []:
        if (max_assets is not None and processed >= max_assets) or (deadline_seconds is not None and time.monotonic() - started >= deadline_seconds):
            return {"status": "paused", "complete": False, "completedAssets": len(checkpoint["assets"]), "totalAssets": len(entries)}
        entry = task[2]
        if shutil.disk_usage(output_root).free < reserve_bytes + max(entry["bytes"] * 2, 64 * 1024 * 1024):
            return {"status": "paused-capacity", "complete": False, "completedAssets": len(checkpoint["assets"]), "totalAssets": len(entries)}
        used = sum(r["asset"]["bytes"] for r in checkpoint["assets"].values())
        if maximum_output_bytes is not None and used + max(entry["bytes"] * 2, 64 * 1024 * 1024) > maximum_output_bytes:
            return {"status": "paused-output-budget", "complete": False, "completedAssets": len(checkpoint["assets"]), "totalAssets": len(entries)}
        result = None
        if recover_from is not None and asset_path(recover_from, entry["key"]).is_file():
            retained = asset_path(recover_from, entry["key"])
            before = retained.stat()
            source_identity = verify_source_asset(asset_path(input_root, entry["key"]), entry)
            try:
                candidate = verify_retained_asset(input_root, recover_from, entry)
            except (EOFError, OSError, ValueError, KeyError, StopIteration) as error:
                checkpoint["recovery"]["held"].append({"key": entry["key"], "errorClass": type(error).__name__})
            else:
                if source_identity != stable_identity(asset_path(input_root, entry["key"])):
                    raise ValueError("source changed during adoption")
                target = asset_path(output_root, entry["key"])
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_name(target.name + ".recovery-pending")
                with retained.open("rb") as reader, temporary.open("xb") as writer:
                    shutil.copyfileobj(reader, writer, 1024 * 1024)
                    writer.flush(); os.fsync(writer.fileno())
                after = retained.stat()
                if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) or sha(temporary.read_bytes()) != candidate[0]["sha256"]:
                    raise ValueError("recovery asset changed during source comparison/copy")
                os.replace(temporary, target)
                sync_directory(target.parent)
                checkpoint["recovery"]["copied"].append(entry["key"])
                result = candidate
        if result is None:
            result = repair_asset(*task)
        record_result(result)
        processed += 1
    if workers != 1:
        # Reviewed current-run assets only: never adopt or reinterpret a legacy
        # asset in a worker. Legacy adoption/rejection must first be committed by
        # the serial coordinator. Every worker writes a unique immutable key.
        if recover_from is not None and any(asset_path(recover_from,t[2]["key"]).exists() for t in task_args):
            raise ValueError("parallel batch requires legacy candidates reconciled serially first")
        pending = {}
        submitted = 0
        position = 0
        pause_reason = None
        used = sum(r["asset"]["bytes"] for r in checkpoint["assets"].values())
        with ProcessPoolExecutor(max_workers=workers) as pool:
            while position < len(task_args) or pending:
                while position < len(task_args) and len(pending) < workers and pause_reason is None:
                    if max_assets is not None and submitted >= max_assets:
                        pause_reason = "paused"; break
                    if deadline is not None and time.monotonic() >= deadline:
                        pause_reason = "paused"; break
                    task = task_args[position]
                    # Reserve ALL in-flight asset budgets, not the same space
                    # independently per worker. Per-asset allowance is conservative;
                    # global free-space and output ceilings are also checked after results.
                    allowance = max(task[2]["bytes"]*2,64*1024*1024)
                    reserved = sum(value[1] for value in pending.values())
                    if shutil.disk_usage(output_root).free < reserve_bytes + reserved + allowance:
                        pause_reason = "paused-capacity"; break
                    if maximum_output_bytes is not None and used + reserved + allowance > maximum_output_bytes:
                        pause_reason = "paused-output-budget"; break
                    future = pool.submit(repair_asset_task,(*task,deadline))
                    pending[future]=(task[2]["key"],allowance)
                    submitted+=1; position+=1
                if not pending: break
                done,_=wait(pending,timeout=.1,return_when=FIRST_COMPLETED)
                for future in done:
                    pending.pop(future)
                    try: result=future.result()
                    except BudgetPause:
                        pause_reason="paused"; continue
                    record_result(result)
                    used+=result[0]["bytes"]
                    if maximum_output_bytes is not None and used>maximum_output_bytes:
                        pause_reason="paused-output-budget"
                    if shutil.disk_usage(output_root).free<reserve_bytes:
                        pause_reason="paused-capacity"
                # Already running workers drain cooperatively and publish only
                # complete atomic assets; there are never unbounded queued tasks.
            if pause_reason is not None or len(results_by_key)!=len(entries):
                return {"status":pause_reason or "paused","complete":False,
                        "completedAssets":len(checkpoint["assets"]),"totalAssets":len(entries),
                        "parallelWorkers":workers,"submittedAssets":submitted}
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
    parser.add_argument("--representative-key", action="append")
    parser.add_argument("--max-assets", type=int)
    parser.add_argument("--deadline-seconds", type=float)
    parser.add_argument("--recover-from", type=Path)
    parser.add_argument("--reserve-bytes", type=int, default=0)
    parser.add_argument("--maximum-output-bytes", type=int)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be positive")
    result = repair(args.input, args.output, args.workers, args.resume, max_assets=args.max_assets, deadline_seconds=args.deadline_seconds, recover_from=args.recover_from, reserve_bytes=args.reserve_bytes, maximum_output_bytes=args.maximum_output_bytes, representative_keys=args.representative_key)
    if result.get("complete") is False and "completedAssets" in result:
        print(json.dumps(result)); return
    print(json.dumps({"releaseId": result["releaseId"], "counts": result["counts"], "repair": result["repair"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
