#!/usr/bin/env python3
"""Audit final-layout path metadata offline; never open discovered file contents."""

import argparse
import json
import os
import re
import subprocess
from pathlib import Path


POLICY = "repository-standard.json"
PRIVATE_DIRECTORIES = {
    "node_modules", ".delivery", ".venv-delivery", "data", "output", "dist",
    "__pycache__",
}


class AuditError(Exception):
    def __init__(self, rule, path=POLICY):
        self.rule = rule
        self.path = path


def valid_path(value):
    return (
        isinstance(value, str) and bool(value)
        and not any(c in value for c in "\\\x00\r\n*?[")
        and all(part not in ("", ".", "..") for part in value.split("/"))
    )


def load_policy(root):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise AuditError("contract.duplicate_key")
            result[key] = value
        return result

    try:
        # The contract is the only file whose contents this audit reads.
        if (root / POLICY).is_symlink():
            raise AuditError("contract.symlink")
        policy = json.loads((root / POLICY).read_text(encoding="utf-8"),
                            object_pairs_hook=unique_object)
    except (OSError, UnicodeError, ValueError, RecursionError):
        raise AuditError("contract.unreadable_or_invalid_json") from None
    if not isinstance(policy, dict):
        raise AuditError("contract.object_required")
    if type(policy.get("schema_version")) is not int or policy["schema_version"] != 1:
        raise AuditError("contract.schema_version")
    if not isinstance(policy.get("version"), str) or not re.fullmatch(
        r"\d+\.\d+\.\d+", policy["version"]
    ):
        raise AuditError("contract.version")
    for field in ("retired_roots", "required_paths", "runtime_hold_paths"):
        values = policy.get(field)
        if (not isinstance(values, list) or not all(valid_path(p) for p in values)
                or len(set(values)) != len(values)):
            raise AuditError("contract." + field)
    roots = policy.get("roots")
    if not isinstance(roots, dict) or not roots:
        raise AuditError("contract.roots")
    for name, classification in roots.items():
        if (not valid_path(name) or "/" in name or not isinstance(classification, dict)
                or any(not isinstance(classification.get(key), str)
                       or not classification[key].strip() for key in ("kind", "owner"))):
            raise AuditError("contract.roots")
    return policy


def git(root, *args):
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args], stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise AuditError("git.unavailable_or_timeout", ".") from None
    if result.returncode:
        raise AuditError("git.command_failed", ".")
    return result.stdout


def private_artifact(path):
    parts = path.split("/")
    return (
        any(p in PRIVATE_DIRECTORIES or p.endswith(".egg-info") for p in parts)
        or any(p == ".env" or p.startswith(".env.")
               or p.endswith((".key", ".pem")) for p in parts)
    )


def audit(root):
    """Return a deterministic report containing only rules, paths and counts."""
    counts = {"tracked": 0, "untracked": 0, "checked": 0,
              "excluded_holds": 0, "excluded_missing": 0}
    violations = []
    try:
        # A subdirectory must not silently audit only part of its enclosing repo.
        if git(root, "rev-parse", "--is-inside-work-tree").strip() != b"true":
            raise AuditError("git.worktree_required", ".")
        if git(root, "rev-parse", "--show-prefix").strip():
            raise AuditError("git.repository_root_required", ".")
        policy = load_policy(root)
        tracked = set(os.fsdecode(p) for p in git(root, "ls-files", "--cached", "-z").split(b"\0") if p)
        untracked = set(os.fsdecode(p) for p in git(
            root, "ls-files", "--others", "--exclude-standard", "-z"
        ).split(b"\0") if p) - tracked
        counts.update(tracked=len(tracked), untracked=len(untracked))
        holds = set(policy["runtime_hold_paths"])
        retired = set(policy["retired_roots"])
        for path in sorted(tracked | untracked):
            if not os.path.lexists(root / path):
                counts["excluded_missing"] += 1
                continue
            if path in untracked and path in holds:
                counts["excluded_holds"] += 1
                continue
            counts["checked"] += 1
            top = path.split("/", 1)[0]
            if path in tracked and private_artifact(path):
                violations.append({"rule": "tracked_private_artifact", "path": path})
            if any(path == old or path.startswith(old + "/") for old in retired):
                violations.append({"rule": "retired_root", "path": path})
            elif top not in policy["roots"]:
                violations.append({"rule": "unclassified_root", "path": path})
        for path in policy["required_paths"]:
            if not (root / path).exists():
                violations.append({"rule": "missing_required_path", "path": path})
    except AuditError as error:
        violations.append({"rule": error.rule, "path": error.path})
    except (OSError, ValueError):
        violations.append({"rule": "audit.path_error", "path": "."})
    violations.sort(key=lambda item: (item["path"], item["rule"]))
    counts["violations"] = len(violations)
    return {"counts": counts, "violations": violations}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = audit(args.root)
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True))
    return int(bool(report["violations"]))


if __name__ == "__main__":
    raise SystemExit(main())
