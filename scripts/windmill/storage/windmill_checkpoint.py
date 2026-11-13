#requirements:
#wmill==1.850.0
"""Windmill-side checkpoint reference adapter; never import this in the SSH jail.

Existing job-scoped SDK authentication only. No credentials, network changes,
distributed lock, CAS, raw datasets, or metadata-DB backup are provided here.
Caller must serialize writes to each key across the whole job, not only the API
request. Use separate per-run/per-partition keys. Publish artifact + checkpoint
and its local backup first; then commit this small reference. Retry idempotently.
"""
import hashlib
import os
import re

PREFIX = "u/admin/offmenu_platform/checkpoints/"
KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}(?:/[A-Za-z0-9][A-Za-z0-9_.-]{0,127})*\Z")
VERSION = re.compile(r"[0-9]{1,24}-[0-9a-f]{16}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class CheckpointError(ValueError):
    pass


def resource_path(key):
    if not isinstance(key, str) or len(key) > 160 or not KEY.fullmatch(key):
        raise CheckpointError("Invalid checkpoint key")
    return PREFIX + hashlib.sha256(key.encode()).hexdigest()


def _sdk(client=None):
    if client is not None:
        return client
    if os.environ.get("WM_WORKSPACE") != "offmenu" or os.environ.get("WM_USERNAME") != "admin":
        raise CheckpointError("Run as existing admin owner in the offmenu Windmill workspace")
    import wmill
    return wmill.Windmill()  # Existing job auth; do not read/copy WM_TOKEN.


def _read(client, path):
    response = client.get(f"/w/offmenu/resources/get/{path}", raise_for_status=False)
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise CheckpointError(f"Resource read refused with HTTP {response.status_code}")
    meta = response.json()
    if (meta.get("path") != path or meta.get("workspace_id") != "offmenu"
            or meta.get("resource_type") != "state" or meta.get("extra_perms") != {}
            or meta.get("created_by") != "admin"):
        raise CheckpointError("Resource is not the expected owner-private native state")
    if not isinstance(meta.get("value"), dict):
        raise CheckpointError("Existing resource has no checkpoint reference object")
    return meta["value"]


def _reference(key, checkpoint_receipt, backup_receipt):
    path = resource_path(key)
    cp, backup = checkpoint_receipt, backup_receipt
    if not isinstance(cp, dict) or set(cp) != {"key", "version", "sha256", "checkpoint_path", "artifact_count"}:
        raise CheckpointError("Invalid checkpoint receipt")
    if not isinstance(backup, dict) or set(backup) != {"version", "sha256", "backup_path"}:
        raise CheckpointError("Invalid backup receipt")
    version, sha = cp["version"], cp["sha256"]
    if not isinstance(version, str) or not VERSION.fullmatch(version) or not isinstance(sha, str) or not HEX64.fullmatch(sha):
        raise CheckpointError("Invalid checkpoint receipt digest/version")
    if cp["key"] != key or backup["version"] != version or backup["sha256"] != sha:
        raise CheckpointError("Checkpoint and backup receipts do not match")
    keyhash = path.removeprefix(PREFIX)
    if cp["checkpoint_path"] != f"checkpoints/{keyhash}/versions/{version}.json":
        raise CheckpointError("Invalid checkpoint location")
    if backup["backup_path"] != f"backups/checkpoints/{keyhash}/{version}.json":
        raise CheckpointError("Invalid backup location")
    if type(cp["artifact_count"]) is not int or not 0 <= cp["artifact_count"] <= 64:
        raise CheckpointError("Invalid artifact count")
    return {"format": "offmenu-checkpoint-reference-v1", "schema_version": 1,
            "key": key, "version": version, "sha256": sha,
            "checkpoint_path": cp["checkpoint_path"], "backup_path": backup["backup_path"],
            "artifact_count": cp["artifact_count"], "concurrency": "single_writer_per_key"}


def _validate_reference(key, value):
    fields = {"format", "schema_version", "key", "version", "sha256", "checkpoint_path",
              "backup_path", "artifact_count", "concurrency"}
    if not isinstance(value, dict) or set(value) != fields or type(value["schema_version"]) is not int:
        raise CheckpointError("Existing state is not a valid checkpoint reference")
    cp = {field: value[field] for field in ("key", "version", "sha256", "checkpoint_path", "artifact_count")}
    backup = {field: value[field] for field in ("version", "sha256", "backup_path")}
    if value != _reference(key, cp, backup):
        raise CheckpointError("Existing checkpoint reference has invalid metadata")
    return value


def inspect_reference(key, client=None):
    path = resource_path(key)
    value = _read(_sdk(client), path)
    if value is not None:
        _validate_reference(key, value)
    return {"resource_path": path, "present": value is not None,
            "version": value.get("version") if value else None,
            "sha256": value.get("sha256") if value else None}


def commit_reference(key, checkpoint_receipt, backup_receipt, client=None):
    client = _sdk(client)
    path = resource_path(key)
    desired = _reference(key, checkpoint_receipt, backup_receipt)
    current = _read(client, path)
    if current is not None:
        _validate_reference(key, current)
    if current != desired:
        if current is None:
            # No update_if_exists: create-only server endpoint rejects a race.
            response = client.post("/w/offmenu/resources/create", raise_for_status=False,
                                   json={"path": path, "resource_type": "state", "value": desired,
                                         "description": "Nonsecret OffMenu checkpoint reference; single writer per key"})
        else:
            # Whole-value set, NOT compare-and-swap. Caller single-writer contract is required.
            response = client.post(f"/w/offmenu/resources/update_value/{path}",
                                   raise_for_status=False, json={"value": desired})
        if response.status_code not in (200, 201):
            raise CheckpointError(f"Checkpoint write refused with HTTP {response.status_code}")
    if _read(client, path) != desired:
        raise CheckpointError("Checkpoint read-back mismatch; possible competing writer")
    return {"verified": True, "resource_path": path, "version": desired["version"],
            "sha256": desired["sha256"], "changed": current != desired}


def main(key: str, operation: str = "inspect", checkpoint_receipt: dict | None = None,
         backup_receipt: dict | None = None):
    if operation == "inspect":
        return inspect_reference(key)
    if operation == "commit":
        return commit_reference(key, checkpoint_receipt, backup_receipt)
    raise CheckpointError("Operation must be inspect or commit")
