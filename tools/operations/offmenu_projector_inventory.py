#!/usr/bin/env python3
"""Read six exact pinned Python sources as the normal user; never execute them."""
from __future__ import annotations

import ast
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

SCHEMA = "offmenu-projector-inventory/1"
MAX_FILE_BYTES = 512 * 1024
MAX_REPORT_BYTES = 12288
MAX_IMPORTS = 12
MAX_FUNCTIONS = 16
MAX_CLASSES = 8
MODULES = {
    "LEDGER_ADAPTER": ("/home/user/Documents/Codex/2026-10-16/worker64-permanent-ledger-adoption/ledger.py",
                       "2f926b35a052a3ed8d96220e8d9a5554480d2a84684ae22d91691596509fca29"),
    "BACKLOG": ("/home/user/Documents/Codex/2026-10-16/worker64-permanent-ledger-adoption/backlog.py",
                "ba1b94b3d596344a1dd8c719c516abe52e78a39f2b513c05abd372a3e38d1596"),
    "MANAGEMENT_ACTIONS": ("/home/user/Documents/Codex/2026-10-16/worker64-ledger-completion-intake/management_actions.py",
                           "08c93fd9e67da5a212fea2873bd0ff2b5bc9bba97d5cf5566e9957e69f0ff10a"),
    "FOLLOWTHROUGH": ("/home/user/Documents/Codex/2026-10-16/worker64-ledger-completion-intake/followthrough.py",
                      "72cb4025914d88af54e9ca6898f72e31e7d29874dac25a71f51c33d7bebebc46"),
    "SESSION_ACTIONS": ("/home/user/Documents/Codex/2026-10-16/worker64-ledger-completion-intake/session_actions.py",
                        "4b75f6122d2652d19a6f3a6e9013fb0256902b1e3a471ac3f2ab4a0a6c9ce669"),
    "COUNTRY_MANAGEMENT": ("/home/user/Documents/Codex/2026-10-16/worker64-ledger-completion-intake/country_management.py",
                           "51db58180e01e6d08cd3f7ae505e35c1e00c529503f1e20f7b6517db33cc4d85"),
}
STATUSES = {"verified", "missing", "unreadable", "unsafe-path", "not-regular", "oversize",
            "changed-during-read", "hash-mismatch", "syntax-invalid", "inspection-failed"}
TYPES = {"regular", "directory", "symlink", "special", "missing", "unknown"}
# Unknown source identifiers may themselves contain secrets. Export only these
# reviewed structural/dependency names; count all other names without copying.
SAFE_IMPORTS = {"argparse", "ast", "collections", "collections.abc", "contextlib", "copy", "csv",
                "dataclasses", "datetime", "decimal", "enum", "fcntl", "functools", "hashlib",
                "importlib", "importlib.util", "io", "itertools", "json", "math", "os", "pathlib",
                "re", "shutil", "signal", "stat", "subprocess", "sys", "tempfile", "threading",
                "time", "traceback", "typing", "unittest", "uuid", "ledger", "backlog",
                "management_actions", "followthrough", "session_actions", "country_management"}
SAFE_SYMBOLS = {"Ledger", "LedgerError", "ValidationError", "ConflictError", "main", "run", "safe",
                "view", "summary", "read", "write", "load", "save", "append", "record", "apply",
                "replay", "project", "validate", "parse_args", "read_json", "write_json", "read_events",
                "load_events", "append_event", "record_event", "apply_event", "project_events",
                "validate_event", "load_base", "load_authority", "load_journal", "read_journal",
                "write_summary", "build_summary", "management_summary", "project_backlog",
                "project_management_actions", "project_session_actions", "project_country_management",
                "canonical", "canonical_json", "sha256", "digest", "utcnow", "now_utc", "atomic_write",
                "atomic_json", "locked", "acquire_lock", "release_lock", "ensure_store", "init_store",
                "get_state", "get_task", "get_obligation", "state_counts", "source_pins", "check_source",
                "validate_source", "select", "claim", "pickup", "result", "disposition", "followthrough"}


class InventoryError(Exception):
    def __init__(self, status, file_type="unknown", present=None):
        self.status, self.file_type, self.present = status, file_type, present


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def safe_name(value, dotted=False):
    return isinstance(value, str) and value in (SAFE_IMPORTS if dotted else SAFE_SYMBOLS)


def syntax_summary(raw):
    try:
        # Decode without a source-selected codec. Parsing a Unicode string does
        # not interpret source coding cookies or import a declared codec.
        source = raw.decode("utf-8-sig", errors="strict")
        tree = ast.parse(source, filename="pinned-projector", mode="exec")
    except (SyntaxError, UnicodeError, ValueError, RecursionError, MemoryError):
        raise InventoryError("syntax-invalid", "regular", True) from None
    values = {"imports": set(), "functions": set(), "classes": set()}
    omitted = {"imports": 0, "functions": 0, "classes": 0}
    relative_imports = 0
    for node in ast.walk(tree):
        name = None
        if isinstance(node, ast.Import):
            for alias in node.names:
                if safe_name(alias.name, dotted=True):
                    values["imports"].add(alias.name)
                else:
                    omitted["imports"] += 1
        elif isinstance(node, ast.ImportFrom):
            relative_imports += int(bool(node.level))
            # Relative `from . import sibling` dependencies live in alias names.
            names = [node.module] if node.module else [item.name for item in node.names]
            for name in names:
                if safe_name(name, dotted=True):
                    values["imports"].add(name)
                else:
                    omitted["imports"] += 1
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name, category = node.name, "functions"
        elif isinstance(node, ast.ClassDef):
            name, category = node.name, "classes"
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if safe_name(name):
                values[category].add(name)
            else:
                omitted[category] += 1
    result = {"syntax": "valid", "staticOnly": True, "relativeImportStatements": relative_imports}
    for key, cap in (("imports", MAX_IMPORTS), ("functions", MAX_FUNCTIONS), ("classes", MAX_CLASSES)):
        result[key] = sorted(values[key])[:cap]
        result[key + "Omitted"] = omitted[key] + max(0, len(values[key]) - cap)
    return result


def file_type(info):
    if stat.S_ISREG(info.st_mode):
        return "regular"
    if stat.S_ISDIR(info.st_mode):
        return "directory"
    if stat.S_ISLNK(info.st_mode):
        return "symlink"
    return "special"


def identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def inspect_file(path, expected_hash):
    """Open each ancestor by directory descriptor, refusing every symlink."""
    parent_fd = file_fd = None
    directory_fds, ancestors = [], []
    base = {"status": "inspection-failed", "present": None, "type": "unknown", "bytes": None,
            "sha256": None, "sha256Match": None, "syntax": "not-inspected"}
    try:
        parts = Path(path).parts
        if parts[0] != "/" or ".." in parts:
            raise InventoryError("unsafe-path")
        parent_fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        directory_fds.append(parent_fd)
        for component in parts[1:-1]:
            try:
                entry = os.stat(component, dir_fd=parent_fd, follow_symlinks=False)
                if not stat.S_ISDIR(entry.st_mode):
                    raise InventoryError("unsafe-path", file_type(entry), None)
                next_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
                directory_fds.append(next_fd)
                opened = os.fstat(next_fd)
                if (opened.st_dev, opened.st_ino) != (entry.st_dev, entry.st_ino):
                    raise InventoryError("changed-during-read")
            except FileNotFoundError:
                raise InventoryError("missing", "missing", False) from None
            ancestors.append((parent_fd, component, entry.st_dev, entry.st_ino))
            parent_fd = next_fd
        leaf = parts[-1]
        entry = os.stat(leaf, dir_fd=parent_fd, follow_symlinks=False)
        kind = file_type(entry)
        base.update(present=True, type=kind)
        if kind == "symlink":
            raise InventoryError("unsafe-path", kind, True)
        if kind != "regular":
            raise InventoryError("not-regular", kind, True)
        base["bytes"] = entry.st_size
        if entry.st_size > MAX_FILE_BYTES:
            raise InventoryError("oversize", "regular", True)
        file_fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
        before = os.fstat(file_fd)
        if identity(before) != identity(entry):
            raise InventoryError("changed-during-read", "regular", True)
        raw = bytearray()
        while True:
            block = os.read(file_fd, min(65536, MAX_FILE_BYTES + 1 - len(raw)))
            if not block:
                break
            raw.extend(block)
            if len(raw) > MAX_FILE_BYTES:
                raise InventoryError("oversize", "regular", True)
        after = os.fstat(file_fd)
        current = os.stat(leaf, dir_fd=parent_fd, follow_symlinks=False)
        if identity(before) != identity(after) or identity(before) != identity(current) or len(raw) != before.st_size:
            raise InventoryError("changed-during-read", "regular", True)
        for ancestor_fd, name, device, inode in ancestors:
            current = os.stat(name, dir_fd=ancestor_fd, follow_symlinks=False)
            if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != (device, inode):
                raise InventoryError("changed-during-read", "regular", True)
        digest = hashlib.sha256(raw).hexdigest()
        base.update(sha256=digest, sha256Match=digest == expected_hash)
        if digest != expected_hash:
            raise InventoryError("hash-mismatch", "regular", True)
        base.update(syntax="valid", structure=syntax_summary(bytes(raw)), status="verified")
    except InventoryError as error:
        base.update(status=error.status, present=error.present, type=error.file_type)
        if error.status == "syntax-invalid":
            base["syntax"] = "invalid"
    except FileNotFoundError:
        base.update(status="missing", present=False, type="missing")
    except PermissionError:
        base["status"] = "unreadable"
    except OSError as error:
        base["status"] = "unsafe-path" if error.errno in {errno.ELOOP, errno.ENOTDIR} else "inspection-failed"
    finally:
        for fd in [file_fd, *reversed(directory_fds)]:
            if fd is not None:
                os.close(fd)
    return base


def inventory():
    files = {key: inspect_file(path, digest) for key, (path, digest) in MODULES.items()}
    result = {"schemaVersion": SCHEMA, "status": "complete" if all(x["status"] == "verified" for x in files.values()) else "incomplete",
              "files": files, "sourceCodeExecuted": False, "sourceCodeUploaded": False,
              "sourcePathsIncluded": False, "sourceBodiesIncluded": False, "filesWritten": 0,
              "maximumFileBytes": MAX_FILE_BYTES, "summaryTruncated": False}
    if len(canonical(result)) > MAX_REPORT_BYTES:
        # Preserve file availability/hash results even if the identifier summary
        # is unexpectedly large. No partial raw source is ever a fallback.
        for record in files.values():
            record.pop("structure", None)
        result["summaryTruncated"] = True
    return result


def sanitize_report(value):
    """Validate the complete fixed public contract for the owner wrapper."""
    def require(condition):
        if not condition:
            raise ValueError("invalid-projector-inventory-report")

    def nonnegative(number):
        require(type(number) is int and 0 <= number <= 2**53 - 1)

    require(isinstance(value, dict) and len(canonical(value)) <= MAX_REPORT_BYTES)
    require(value.get("schemaVersion") == SCHEMA)
    require(value.get("status") in {"complete", "incomplete", "blocked"})
    boundary_keys = {"sourceCodeExecuted", "sourceCodeUploaded", "sourcePathsIncluded", "sourceBodiesIncluded"}
    require(all(value.get(key) is False for key in boundary_keys))
    require(type(value.get("filesWritten")) is int and value["filesWritten"] == 0)
    common = {"schemaVersion", "status", "filesWritten"} | boundary_keys
    if value["status"] == "blocked":
        require(set(value) == common | {"errorCode"})
        require(value["errorCode"] in {"normal-user-required", "no-arguments-allowed", "inventory-failed", "report-limit-exceeded"})
        return value
    require(set(value) == common | {"files", "maximumFileBytes", "summaryTruncated"})
    require(type(value["summaryTruncated"]) is bool and type(value["maximumFileBytes"]) is int and value["maximumFileBytes"] == MAX_FILE_BYTES)
    require(isinstance(value["files"], dict) and set(value["files"]) == set(MODULES))
    required_record = {"status", "present", "type", "bytes", "sha256", "sha256Match", "syntax"}
    for module_id, record in value["files"].items():
        require(isinstance(record, dict) and required_record <= set(record) <= required_record | {"structure"})
        require(record["status"] in STATUSES and record["type"] in TYPES)
        require(record["present"] is None or type(record["present"]) is bool)
        require(record["sha256Match"] is None or type(record["sha256Match"]) is bool)
        if record["bytes"] is not None:
            nonnegative(record["bytes"])
        require(record["sha256"] is None or isinstance(record["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", record["sha256"]) is not None)
        if record["sha256"] is None:
            require(record["sha256Match"] is None)
        else:
            require(type(record["sha256Match"]) is bool and record["sha256Match"] == (record["sha256"] == MODULES[module_id][1]))
            require(record["status"] in {"verified", "syntax-invalid", "hash-mismatch"})
        if record["status"] in {"verified", "syntax-invalid", "hash-mismatch"}:
            require(record["present"] is True and record["type"] == "regular")
            require(type(record["bytes"]) is int and record["bytes"] <= MAX_FILE_BYTES and record["sha256"] is not None)
        else:
            require(record["sha256"] is None and record["sha256Match"] is None and record["syntax"] == "not-inspected")
        if record["status"] == "hash-mismatch":
            require(record["sha256Match"] is False and record["syntax"] == "not-inspected")
        if record["status"] == "syntax-invalid":
            require(record["sha256Match"] is True and record["syntax"] == "invalid")
        require(record["syntax"] in {"valid", "invalid", "not-inspected"})
        if "structure" in record:
            require(record["status"] == "verified" and record["sha256Match"] is True and record["syntax"] == "valid")
            structure = record["structure"]
            require(isinstance(structure, dict) and set(structure) == {"syntax", "staticOnly", "relativeImportStatements", "imports", "functions", "classes", "importsOmitted", "functionsOmitted", "classesOmitted"})
            require(structure["syntax"] == "valid" and structure["staticOnly"] is True)
            nonnegative(structure["relativeImportStatements"])
            for key, limit in (("imports", MAX_IMPORTS), ("functions", MAX_FUNCTIONS), ("classes", MAX_CLASSES)):
                require(isinstance(structure[key], list) and len(structure[key]) <= limit)
                require(all(safe_name(name, dotted=key == "imports") for name in structure[key]))
                require(len(set(structure[key])) == len(structure[key]))
                nonnegative(structure[key + "Omitted"])
        if record["status"] == "verified":
            require(record["present"] is True and record["type"] == "regular" and record["sha256Match"] is True and record["syntax"] == "valid")
            require(type(record["bytes"]) is int and record["bytes"] <= MAX_FILE_BYTES and record["sha256"] is not None)
            require(value["summaryTruncated"] or "structure" in record)
    require((value["status"] == "complete") == all(record["status"] == "verified" for record in value["files"].values()))
    return value


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if arguments or os.getuid() == 0 or os.geteuid() == 0:
        result = {"schemaVersion": SCHEMA, "status": "blocked",
                  "errorCode": "no-arguments-allowed" if arguments else "normal-user-required",
                  "sourceCodeExecuted": False, "sourceCodeUploaded": False,
                  "sourcePathsIncluded": False, "sourceBodiesIncluded": False, "filesWritten": 0}
    else:
        try:
            result = sanitize_report(inventory())
        except (OSError, ValueError, TypeError, RecursionError, MemoryError):
            result = {"schemaVersion": SCHEMA, "status": "blocked", "errorCode": "inventory-failed",
                      "sourceCodeExecuted": False, "sourceCodeUploaded": False,
                      "sourcePathsIncluded": False, "sourceBodiesIncluded": False, "filesWritten": 0}
    payload = canonical(result)
    if len(payload) > MAX_REPORT_BYTES:
        result = {"schemaVersion": SCHEMA, "status": "blocked", "errorCode": "report-limit-exceeded",
                  "sourceCodeExecuted": False, "sourceCodeUploaded": False,
                  "sourcePathsIncluded": False, "sourceBodiesIncluded": False, "filesWritten": 0}
        payload = canonical(result)
    print(payload.decode("ascii"))
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
