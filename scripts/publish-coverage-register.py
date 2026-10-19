#!/usr/bin/env python3
"""Publish only the sanitized OffMenu coverage bundle to its private handoff branch.

This does not publish source bodies or impersonate a collector result. It is limited
to compressed coverage outputs, a sanitized checkpoint, and three reproducibility
scripts. The target repository and branch base are pinned; changes fail closed.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPOSITORY = "maldous/offmenu"
REPOSITORY_ID = 1416253963
OWNER_ID = 6347545
BRANCH = "integration/foo-owner-custody-snapshot-20261018"
ANCHOR = "4aa0976b9dc509b91f76874717f9de5e5e5529df"
EXPECTED_BASE = "c51234373964857668661e21738c98781ea3f9c4"
ROOT = Path(__file__).resolve().parents[1]
REGISTER_DIR = ROOT / "docs/coverage-register/2026-10-19"
CHECKPOINT = ROOT / "docs/handover/2026-10-19/foo-coverage-reconciliation-checkpoint.md"
MAX_TOTAL = 8 * 1024 * 1024
MAX_FILE = 4 * 1024 * 1024
GIT_RE = re.compile(r"^[a-f0-9]{40}$")
PRIVATE_PATH_RE = re.compile(r"(?<![A-Za-z0-9+.-])(?:/home/|/srv/|/workspace/)[^`\s\"']+")


class PublishError(RuntimeError):
    pass


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def gh(method: str, path: str, payload: dict | None = None, *, absent: bool = False):
    if not (path == "user" or path == f"repos/{REPOSITORY}" or path.startswith(f"repos/{REPOSITORY}/")):
        raise PublishError("github-target-rejected")
    command = ["gh", "api", "--hostname", "github.com", "--method", method, path]
    data = None
    if payload is not None:
        command += ["--input", "-"]
        data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    env = os.environ.copy()
    env.update(GH_PROMPT_DISABLED="1", GIT_TERMINAL_PROMPT="0", GH_PAGER="cat")
    try:
        proc = subprocess.run(command, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              env=env, timeout=25, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PublishError("github-call-failed") from exc
    if proc.returncode:
        error = proc.stderr.decode("utf-8", "replace")[:300]
        if absent and method == "GET" and "HTTP 404" in error:
            return None
        raise PublishError("github-call-failed: " + error)
    try:
        result = json.loads(proc.stdout)
    except (ValueError, UnicodeError) as exc:
        raise PublishError("github-response-invalid") from exc
    if not isinstance(result, dict):
        raise PublishError("github-response-invalid")
    return result


def local_files() -> list[tuple[str, bytes]]:
    files = []
    for name in ("coverage-register.json.gz", "origin-type-coverage.jsonl.gz",
                 "unique-assets.jsonl.gz", "source-blockers.jsonl.gz"):
        path = REGISTER_DIR / name
        raw = path.read_bytes()
        if len(raw) > MAX_FILE:
            raise PublishError("artifact-file-size-limit")
        try:
            gzip.decompress(raw)
        except (OSError, EOFError) as exc:
            raise PublishError("artifact-gzip-invalid") from exc
        files.append((str(path.relative_to(ROOT)), raw))
    checkpoint = CHECKPOINT.read_bytes()
    if PRIVATE_PATH_RE.search(checkpoint.decode("utf-8")):
        raise PublishError("checkpoint-private-path-detected")
    files.append((str(CHECKPOINT.relative_to(ROOT)), checkpoint))
    for name in ("build-origin-type-register.py", "reconcile-parsed-coverage.py", "publish-coverage-register.py"):
        path = ROOT / "scripts" / name
        files.append((str(path.relative_to(ROOT)), path.read_bytes()))
    if sum(len(raw) for _, raw in files) > MAX_TOTAL:
        raise PublishError("publication-total-size-limit")
    return files


def validate_bundle(files: list[tuple[str, bytes]]) -> None:
    by_path = dict(files)
    base = "docs/coverage-register/2026-10-19/"
    try:
        report = json.loads(gzip.decompress(by_path[base + "coverage-register.json.gz"]))
        rows = {
            "coverage": [json.loads(x) for x in gzip.decompress(by_path[base + "origin-type-coverage.jsonl.gz"]).splitlines()],
            "assets": [json.loads(x) for x in gzip.decompress(by_path[base + "unique-assets.jsonl.gz"]).splitlines()],
            "blockers": [json.loads(x) for x in gzip.decompress(by_path[base + "source-blockers.jsonl.gz"]).splitlines()],
        }
    except (KeyError, OSError, EOFError, ValueError, json.JSONDecodeError) as exc:
        raise PublishError("artifact-bundle-invalid") from exc
    counts = report.get("counts", {})
    if (len(report.get("origins", {})) != 250 or len(report.get("types", [])) != 13
            or len(report.get("coverage", [])) != 3250 or counts.get("originTypeEntries") != 3250
            or counts.get("entriesComplete") != 0 or len(rows["assets"]) != 6068
            or counts.get("uniqueParsedRecordLinks") != 73985):
        raise PublishError("artifact-contract-invalid")
    if rows["coverage"] != report["coverage"] or rows["assets"] != report["assets"] or rows["blockers"] != report["blockers"]:
        raise PublishError("artifact-flat-files-mismatch")
    if len({x.get("assetId") for x in rows["assets"]}) != 6068:
        raise PublishError("duplicate-asset-id")

    def scan(value):
        if isinstance(value, dict):
            for child in value.values(): scan(child)
        elif isinstance(value, list):
            for child in value: scan(child)
        elif isinstance(value, str) and PRIVATE_PATH_RE.search(value):
            raise PublishError("artifact-private-path-detected")

    scan(report)
    scan(rows)


def verify_target() -> None:
    user = gh("GET", "user")
    repo = gh("GET", f"repos/{REPOSITORY}")
    if user.get("id") != OWNER_ID or repo.get("id") != REPOSITORY_ID or repo.get("full_name") != REPOSITORY:
        raise PublishError("github-target-identity-mismatch")
    if repo.get("private") is not True or repo.get("owner", {}).get("id") != OWNER_ID or repo.get("permissions", {}).get("push") is not True:
        raise PublishError("github-private-write-access-unverified")


def head() -> str:
    ref = gh("GET", f"repos/{REPOSITORY}/git/ref/heads/{BRANCH}")
    value = ref.get("object", {}).get("sha")
    if not isinstance(value, str) or not GIT_RE.fullmatch(value):
        raise PublishError("github-branch-head-invalid")
    return value


def verify_branch(current: str) -> None:
    compared = gh("GET", f"repos/{REPOSITORY}/compare/{ANCHOR}...{current}")
    if compared.get("status") not in {"ahead", "identical"}:
        raise PublishError("github-handoff-branch-unrelated")
    if current != EXPECTED_BASE:
        raise PublishError("github-handoff-branch-head-changed")


def readback(path: str, expected: bytes, commit: str) -> bool:
    item = gh("GET", f"repos/{REPOSITORY}/contents/{path}?ref={commit}", absent=True)
    if not isinstance(item, dict) or item.get("type") != "file" or item.get("size") != len(expected):
        return False
    digest = blob_sha(expected)
    if item.get("sha") != digest:
        return False
    blob = gh("GET", f"repos/{REPOSITORY}/git/blobs/{digest}")
    if blob.get("sha") != digest or blob.get("size") != len(expected) or blob.get("encoding") != "base64":
        return False
    try:
        return base64.b64decode(blob.get("content", "").replace("\n", ""), validate=True) == expected
    except (ValueError, TypeError):
        return False


def readback_all(commit: str, files: list[tuple[str, bytes]]) -> bool:
    return all(readback(path, raw, commit) for path, raw in files)


def publish() -> dict:
    files = local_files()
    validate_bundle(files)
    verify_target()
    parent = head()
    verify_branch(parent)
    if readback_all(parent, files):
        status, commit_sha = "verified-existing", parent
    else:
        current = gh("GET", f"repos/{REPOSITORY}/git/commits/{parent}")
        tree_sha = current.get("tree", {}).get("sha")
        if current.get("sha") != parent or not isinstance(tree_sha, str) or not GIT_RE.fullmatch(tree_sha):
            raise PublishError("github-parent-invalid")
        entries = []
        for path, raw in files:
            blob = gh("POST", f"repos/{REPOSITORY}/git/blobs", {
                "encoding": "base64", "content": base64.b64encode(raw).decode("ascii")})
            if blob.get("sha") != blob_sha(raw):
                raise PublishError("github-blob-hash-mismatch")
            entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        tree = gh("POST", f"repos/{REPOSITORY}/git/trees", {"base_tree": tree_sha, "tree": entries})
        new_tree = tree.get("sha")
        if not isinstance(new_tree, str) or not GIT_RE.fullmatch(new_tree):
            raise PublishError("github-tree-invalid")
        commit = gh("POST", f"repos/{REPOSITORY}/git/commits", {
            "message": "Publish sanitized OffMenu coverage reconciliation checkpoint [skip ci]",
            "tree": new_tree, "parents": [parent]})
        new_sha = commit.get("sha")
        if not isinstance(new_sha, str) or not GIT_RE.fullmatch(new_sha):
            raise PublishError("github-commit-invalid")
        if head() != parent:
            raise PublishError("github-handoff-branch-head-changed")
        try:
            gh("PATCH", f"repos/{REPOSITORY}/git/refs/heads/{BRANCH}", {"sha": new_sha, "force": False})
        except PublishError as exc:
            # Reconcile a possibly successful update with reads only; never repeat PATCH.
            current = head()
            if current != new_sha or not readback_all(current, files):
                raise PublishError("github-ref-update-outcome-uncertain") from exc
        commit_sha = head()
        if commit_sha != new_sha or not readback_all(commit_sha, files):
            raise PublishError("github-publication-readback-mismatch")
        status = "published-and-verified"
    return {"status": status, "repository": REPOSITORY, "branch": BRANCH, "commit": commit_sha,
            "files": [{"path": path, "bytes": len(raw), "sha256": sha(raw), "gitBlobSHA": blob_sha(raw)}
                      for path, raw in files]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="validate payload and target without writing")
    args = parser.parse_args()
    try:
        files = local_files()
        validate_bundle(files)
        if args.dry_run:
            verify_target()
            current = head()
            verify_branch(current)
            print(json.dumps({"status": "ready-no-write", "repository": REPOSITORY, "branch": BRANCH,
                              "parent": current, "totalBytes": sum(len(raw) for _, raw in files),
                              "files": [{"path": path, "bytes": len(raw), "sha256": sha(raw)} for path, raw in files]}, sort_keys=True))
        else:
            print(json.dumps(publish(), sort_keys=True))
        return 0
    except (PublishError, OSError, UnicodeError) as exc:
        print(f"coverage-publication-blocked: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
