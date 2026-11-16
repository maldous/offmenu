#!/usr/bin/env python3
"""Offline, dependency-free artifact receipts and bounded checkpoint backups.

Only for an owner-controlled local filesystem. Not a database, distributed lock,
secret store, or substitute for an independent host/metadata-database backup.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
import time
import uuid

MAX_JSON_BYTES = 64 * 1024
MAX_ARTIFACT_BYTES = 1024 * 1024 * 1024
SAFE_PART = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
VERSION = re.compile(r"[0-9]{1,24}-[0-9a-f]{16}\Z")


class StorageError(ValueError):
    pass


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_relative(value):
    if not isinstance(value, str) or not value or len(value) > 512:
        raise StorageError("Invalid relative path")
    p = PurePosixPath(value)
    if not p.parts or str(p) != value or p.is_absolute() or any(not SAFE_PART.fullmatch(x) for x in p.parts):
        raise StorageError("Path must contain safe relative components only")
    return p


def valid_key(key):
    safe_relative(key)
    if len(key) > 160:
        raise StorageError("Checkpoint key is too long")
    return key


def _no_symlink_components(path):
    for p in [path, *path.parents]:
        if p.is_symlink():
            raise StorageError("Symlink paths are not accepted")


def read_regular(path, limit=MAX_JSON_BYTES):
    path = Path(path).absolute()
    _no_symlink_components(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise StorageError("Input must be a regular file")
        value = stream.read(limit + 1)
        if len(value) > limit:
            raise StorageError("Input exceeds size limit")
        return value


def read_json(path):
    def reject_constant(_):
        raise StorageError("Non-finite JSON number")
    return json.loads(read_regular(path).decode("utf-8"), parse_constant=reject_constant)


def validate_record(record):
    """Allowlist metadata, never arbitrary records, errors, environment or secrets."""
    fields = {"run_id", "partition", "status", "cursor", "counts"}
    if not isinstance(record, dict) or set(record) - fields:
        raise StorageError("Checkpoint contains unsupported metadata fields")
    if not {"run_id", "partition", "status"}.issubset(record):
        raise StorageError("Checkpoint needs run_id, partition and status")
    for name in ("run_id", "partition"):
        valid_key(record[name])
    if record["status"] not in {"pending", "running", "completed", "failed"}:
        raise StorageError("Invalid checkpoint status")
    cursor = record.get("cursor")
    if cursor is not None and (isinstance(cursor, bool) or not isinstance(cursor, (str, int))):
        raise StorageError("Cursor must be a nonsecret string or integer")
    if isinstance(cursor, str) and (len(cursor) > 512 or cursor.startswith(("$var:", "$res:"))):
        raise StorageError("Invalid cursor")
    if isinstance(cursor, int) and not 0 <= cursor <= 2**63 - 1:
        raise StorageError("Cursor integer is outside bounds")
    counts = record.get("counts", {})
    if not isinstance(counts, dict) or len(counts) > 32:
        raise StorageError("Counts must be a bounded object")
    for name, count in counts.items():
        if not SAFE_PART.fullmatch(name) or type(count) is not int or not 0 <= count <= 2**63 - 1:
            raise StorageError("Invalid count")
    if len(canonical(record)) > 8 * 1024:
        raise StorageError("Checkpoint metadata exceeds 8 KiB")
    return record


class Store:
    def __init__(self, root):
        self.root = Path(root).absolute()
        _no_symlink_components(self.root)
        self.root = self.root.resolve()

    def path(self, relative):
        p = self.root.joinpath(*safe_relative(relative).parts)
        _no_symlink_components(p)
        return p

    def _mkdir(self, directory):
        _no_symlink_components(directory)
        missing = []
        cursor = directory
        while not cursor.exists():
            missing.append(cursor)
            cursor = cursor.parent
        for item in reversed(missing):
            item.mkdir(mode=0o700, exist_ok=True)
            self._sync_dir(item.parent)
        _no_symlink_components(directory)
        if not directory.is_dir():
            raise StorageError("Expected storage directory")
        if self.root.exists():
            st = self.root.stat()
            if st.st_uid != os.getuid() or st.st_mode & 0o077:
                raise StorageError("Storage root must be owned by this user with mode 0700")

    @staticmethod
    def _sync_dir(directory):
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def _write(self, relative, data, immutable=False):
        destination = self.path(relative)
        self._mkdir(destination.parent)
        fd, tmp = tempfile.mkstemp(prefix=".storage-", dir=destination.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            if immutable:
                try:
                    os.link(tmp, destination, follow_symlinks=False)
                except FileExistsError:
                    if read_regular(destination, max(len(data), MAX_JSON_BYTES)) != data:
                        raise StorageError("Immutable record collision or corruption")
            else:
                if destination.is_symlink():
                    raise StorageError("Refusing to replace symlink")
                os.replace(tmp, destination)
            self._sync_dir(destination.parent)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    @contextlib.contextmanager
    def _lock(self, key):
        """Local advisory serialization only; not distributed and not a lease."""
        relative = "locks/storage-" + digest(valid_key(key).encode()) + ".lock"
        lock = self.path(relative)
        self._mkdir(lock.parent)
        fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise StorageError("Lock is not a regular file")
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise StorageError("Checkpoint key already has a local writer") from exc
            yield
        finally:
            os.close(fd)  # Do not unlink: unlinking introduces lock inode races.

    def _base(self, key):
        return "checkpoints/" + digest(valid_key(key).encode())

    def publish(self, source, name, max_bytes=MAX_ARTIFACT_BYTES):
        safe_relative(name)
        if type(max_bytes) is not int or max_bytes < 1:
            raise StorageError("Artifact size budget must be positive")
        source = Path(source).absolute()
        _no_symlink_components(source)
        staging = self.path("artifacts/staging")
        self._mkdir(staging)
        fd, tmp = tempfile.mkstemp(prefix=".storage-", dir=staging)
        size = 0
        checksum = hashlib.sha256()
        try:
            with os.fdopen(fd, "wb") as out, os.fdopen(
                    os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as src:
                before = os.fstat(src.fileno())
                if not stat.S_ISREG(before.st_mode):
                    raise StorageError("Artifact source must be a regular file")
                if before.st_size > max_bytes:
                    raise StorageError("Artifact exceeds size budget")
                while chunk := src.read(1024 * 1024):
                    size += len(chunk)
                    if size > max_bytes:
                        raise StorageError("Artifact exceeds size budget")
                    checksum.update(chunk)
                    out.write(chunk)
                after = os.fstat(src.fileno())
                if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                        after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                    raise StorageError("Artifact source changed during publication")
                out.flush()
                os.fsync(out.fileno())
            sha = checksum.hexdigest()
            obj = f"artifacts/objects/sha256/{sha[:2]}/{sha}"
            target = self.path(obj)
            self._mkdir(target.parent)
            try:
                os.link(tmp, target, follow_symlinks=False)
            except FileExistsError:
                self._verify_object(obj, sha, size)
            self._sync_dir(target.parent)
            manifest = {"format": "offmenu-artifact-v1", "name": name,
                        "object_path": obj, "sha256": sha, "size_bytes": size}
            receipt = "artifacts/manifests/" + digest(canonical(manifest)) + ".json"
            self._write(receipt, canonical(manifest), immutable=True)
            return {"receipt_path": receipt, "sha256": sha, "size_bytes": size}
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def _verify_object(self, relative, sha, size):
        fd = os.open(self.path(relative), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        checksum = hashlib.sha256()
        actual_size = 0
        with os.fdopen(fd, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise StorageError("Artifact is not a regular file")
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                actual_size += len(chunk)
                if actual_size > size:
                    raise StorageError("Artifact length mismatch")
                checksum.update(chunk)
        if checksum.hexdigest() != sha or actual_size != size:
            raise StorageError("Artifact checksum or length mismatch")

    def verify_artifact(self, receipt):
        manifest = read_json(self.path(receipt))
        if not isinstance(manifest, dict) or set(manifest) != {
                "format", "name", "object_path", "sha256", "size_bytes"}:
            raise StorageError("Invalid artifact manifest")
        if manifest["format"] != "offmenu-artifact-v1" or not HEX64.fullmatch(manifest["sha256"]):
            raise StorageError("Invalid artifact format or digest")
        safe_relative(manifest["name"])
        sha = manifest["sha256"]
        expected = f"artifacts/objects/sha256/{sha[:2]}/{sha}"
        if manifest["object_path"] != expected or type(manifest["size_bytes"]) is not int or manifest["size_bytes"] < 0:
            raise StorageError("Invalid artifact location or length")
        expected_receipt = "artifacts/manifests/" + digest(canonical(manifest)) + ".json"
        if receipt != expected_receipt:
            raise StorageError("Manifest checksum mismatch")
        self._verify_object(expected, sha, manifest["size_bytes"])
        return manifest

    def _validate_snapshot(self, snapshot, key):
        if not isinstance(snapshot, dict) or set(snapshot) != {"body", "sha256"}:
            raise StorageError("Invalid checkpoint envelope")
        body = snapshot["body"]
        if snapshot["sha256"] != digest(canonical(body)):
            raise StorageError("Checkpoint checksum mismatch")
        if not isinstance(body, dict) or set(body) != {
                "format", "key", "version", "record", "artifact_receipts", "restored_from"}:
            raise StorageError("Invalid checkpoint body")
        if body["format"] != "offmenu-checkpoint-v1" or body["key"] != key or not VERSION.fullmatch(body["version"]):
            raise StorageError("Checkpoint identity mismatch")
        if body["restored_from"] is not None and not VERSION.fullmatch(body["restored_from"]):
            raise StorageError("Invalid restore reference")
        validate_record(body["record"])
        receipts = body["artifact_receipts"]
        if not isinstance(receipts, list) or len(receipts) > 64 or len(set(receipts)) != len(receipts):
            raise StorageError("Invalid artifact receipt list")
        for receipt in receipts:
            self.verify_artifact(receipt)
        return body

    def _checkpoint(self, key, record, receipts, restored_from=None):
        validate_record(record)
        if not isinstance(receipts, list) or len(receipts) > 64 or any(not isinstance(x, str) for x in receipts):
            raise StorageError("Invalid artifact receipt list")
        receipts = sorted(set(receipts))
        for receipt in receipts:
            self.verify_artifact(receipt)
        version = f"{time.time_ns()}-{uuid.uuid4().hex[:16]}"
        body = {"format": "offmenu-checkpoint-v1", "key": key, "version": version,
                "record": record, "artifact_receipts": receipts, "restored_from": restored_from}
        snapshot = {"body": body, "sha256": digest(canonical(body))}
        raw = canonical(snapshot)
        if len(raw) > MAX_JSON_BYTES:
            raise StorageError("Checkpoint exceeds size budget")
        relative = self._base(key) + f"/versions/{version}.json"
        self._write(relative, raw, immutable=True)
        pointer = {"key": key, "version": version, "sha256": snapshot["sha256"]}
        self._write(self._base(key) + "/current.json", canonical(pointer))
        return {**pointer, "checkpoint_path": relative, "artifact_count": len(receipts)}

    def checkpoint(self, key, record, receipts=()):
        with self._lock(key):
            return self._checkpoint(key, record, list(receipts))

    def verify(self, key, version=None):
        valid_key(key)
        pointer = None
        if version is None:
            pointer = read_json(self.path(self._base(key) + "/current.json"))
            if not isinstance(pointer, dict) or set(pointer) != {"key", "version", "sha256"} or pointer["key"] != key:
                raise StorageError("Invalid checkpoint pointer")
            version = pointer["version"]
        if not isinstance(version, str) or not VERSION.fullmatch(version):
            raise StorageError("Invalid checkpoint version")
        snapshot = read_json(self.path(self._base(key) + f"/versions/{version}.json"))
        body = self._validate_snapshot(snapshot, key)
        if body["version"] != version or pointer and pointer["sha256"] != snapshot["sha256"]:
            raise StorageError("Checkpoint pointer mismatch")
        return snapshot

    def backup(self, key):
        with self._lock(key):
            snapshot = self.verify(key)
            relative = f"backups/checkpoints/{digest(key.encode())}/{snapshot['body']['version']}.json"
            self._write(relative, canonical(snapshot), immutable=True)
            return {"backup_path": relative, "sha256": snapshot["sha256"], "version": snapshot["body"]["version"]}

    def restore(self, key, backup):
        valid_key(key)
        if not backup.startswith("backups/checkpoints/" + digest(key.encode()) + "/"):
            raise StorageError("Backup does not belong to checkpoint key")
        with self._lock(key):
            snapshot = read_json(self.path(backup))
            body = self._validate_snapshot(snapshot, key)
            expected = f"backups/checkpoints/{digest(key.encode())}/{body['version']}.json"
            if backup != expected:
                raise StorageError("Backup filename mismatch")
            return self._checkpoint(key, body["record"], body["artifact_receipts"], body["version"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="Approved owner-controlled local storage directory")
    sub = parser.add_subparsers(dest="command", required=True)
    pub = sub.add_parser("publish")
    pub.add_argument("--source", required=True)
    pub.add_argument("--name", required=True)
    pub.add_argument("--max-bytes", type=int, default=MAX_ARTIFACT_BYTES)
    cp = sub.add_parser("checkpoint")
    cp.add_argument("--key", required=True)
    cp.add_argument("--json-file", required=True)
    cp.add_argument("--artifact-receipt", action="append", default=[])
    verify = sub.add_parser("verify")
    verify.add_argument("--key", required=True)
    verify.add_argument("--version")
    backup = sub.add_parser("backup")
    backup.add_argument("--key", required=True)
    restore = sub.add_parser("restore")
    restore.add_argument("--key", required=True)
    restore.add_argument("--backup", required=True)
    args = parser.parse_args(argv)
    try:
        store = Store(args.root)
        if args.command == "publish":
            result = store.publish(args.source, args.name, args.max_bytes)
        elif args.command == "checkpoint":
            result = store.checkpoint(args.key, read_json(args.json_file), args.artifact_receipt)
        elif args.command == "verify":
            snap = store.verify(args.key, args.version)
            result = {"verified": True, "key": args.key, "version": snap["body"]["version"],
                      "sha256": snap["sha256"], "artifact_count": len(snap["body"]["artifact_receipts"])}
        elif args.command == "backup":
            result = store.backup(args.key)
        else:
            result = store.restore(args.key, args.backup)
        print(json.dumps(result, sort_keys=True))  # Receipts only; never file/payload contents.
        return 0
    except (StorageError, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"ok": False, "error_type": type(exc).__name__}), file=sys.stderr)
        return 2  # No arbitrary exception text: OS errors can contain sensitive paths.


if __name__ == "__main__":
    raise SystemExit(main())
