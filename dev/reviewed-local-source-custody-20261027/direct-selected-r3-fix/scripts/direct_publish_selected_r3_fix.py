#!/usr/bin/env python3
"""Direct explicit reviewed source custody using existing gh authentication; no Actions.

Reads only explicit hash-pinned source requests through the reviewed helper.
Never recursively searches runtime, executes exported source, stages runner jobs,
changes permissions or creates credentials. Original Git/index/worktree stay untouched.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import types

REPOSITORY = "maldous/offmenu"
BRANCH = "integration/reviewed-local-source-custody-20261027"
PREFIX = "dev/reviewed-local-source-custody-20261027/direct-selected/"
WORKFLOWS = {
    "foo-runner.yml": "3b487342fc6fac3ec19266e1cbcf6c9d51e1294b",
    "third-party-services.yml": "c1643006a1cf375935e4b135339fa2355567b0b0",
}
HEX = re.compile(r"[0-9a-f]{64}\Z")


class Refused(Exception):
    pass


def need(value, code):
    if not value:
        raise Refused(code)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def safe_local_read(path, limit):
    path = str(Path(path).absolute())
    parts = Path(path).parts[1:]
    need(parts and all(x not in ("", ".", "..") for x in parts), "invalid-input-path")
    parent = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in parts[:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent); parent = nxt
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=parent)
    finally:
        os.close(parent)
    try:
        import stat
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= limit,
             "input-not-bounded-regular-file")
        def read():
            result = bytearray()
            while True:
                chunk = os.read(fd, min(65536, limit + 1 - len(result)))
                if not chunk: break
                result.extend(chunk)
                need(len(result) <= limit, "input-too-large")
            return bytes(result)
        raw = read(); os.lseek(fd, 0, os.SEEK_SET); second = read()
        after = os.fstat(fd)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        need(identity(before) == identity(after) and len(raw) == before.st_size and raw == second,
             "input-changed-during-read")
        return raw
    finally:
        os.close(fd)


def load_helper(path, expected):
    need(type(expected) is str and HEX.fullmatch(expected), "invalid-helper-pin")
    raw = safe_local_read(path, 1024 * 1024)
    need(sha256(raw) == expected, "helper-pin-mismatch")
    module = types.ModuleType("reviewed_source_metadata_validator")
    module.__file__ = str(Path(path).absolute())
    exec(compile(raw, module.__file__, "exec"), module.__dict__)
    return module


class GitHub:
    def __call__(self, endpoint, method="GET", payload=None):
        need(endpoint.startswith("repos/" + REPOSITORY + "/") or endpoint == "repos/" + REPOSITORY,
             "wrong-github-destination")
        command = ["gh", "api", "--method", method, endpoint]
        data = None
        if payload is not None:
            command += ["--input", "-"]
            data = json.dumps(payload, separators=(",", ":")).encode()
        env = dict(os.environ, GH_PROMPT_DISABLED="1", GH_NO_UPDATE_NOTIFIER="1")
        result = subprocess.run(command, input=data, capture_output=True, env=env, timeout=120)
        need(result.returncode == 0, "github-request-failed-no-private-details")
        try:
            return json.loads(result.stdout)
        except (ValueError, UnicodeError):
            raise Refused("github-response-invalid") from None


def current_ref(api):
    value = api("repos/" + REPOSITORY + "/git/ref/heads/" + BRANCH)
    need(value.get("ref") == "refs/heads/" + BRANCH and value.get("object", {}).get("type") == "commit",
         "unexpected-custody-ref")
    sha = value["object"]["sha"]
    need(re.fullmatch(r"[0-9a-f]{40}", sha), "invalid-custody-sha")
    return sha


def verify_safe_parent(api, parent):
    repo = api("repos/" + REPOSITORY)
    need(repo.get("full_name") == REPOSITORY and repo.get("private") is True, "destination-not-private-repository")
    workflows = api("repos/" + REPOSITORY + "/contents/.github/workflows?ref=" + parent)
    need(type(workflows) is list and len(workflows) == len(WORKFLOWS)
         and all(x.get("type") == "file" for x in workflows)
         and {x.get("name"): x.get("sha") for x in workflows} == WORKFLOWS,
         "workflow-pins-changed-stop-before-write")
    commit = api("repos/" + REPOSITORY + "/git/commits/" + parent)
    need(commit.get("sha") == parent, "parent-readback-mismatch")
    return commit["tree"]["sha"]


def tree_at(api, root_tree, path):
    current = root_tree
    for component in path.split("/"):
        data = api("repos/" + REPOSITORY + "/git/trees/" + current)
        need(data.get("truncated") is False, "truncated-remote-tree")
        matches = [x for x in data["tree"] if x["path"] == component]
        if not matches: return None
        need(len(matches) == 1 and matches[0]["type"] == "tree", "destination-prefix-conflict")
        current = matches[0]["sha"]
    result = api("repos/" + REPOSITORY + "/git/trees/" + current)
    need(result.get("truncated") is False, "truncated-remote-tree")
    return result["tree"]


def resolve_requests(path, expected_sha256, helper):
    raw = safe_local_read(path, helper.MAX_PACKET)
    need(HEX.fullmatch(expected_sha256) and sha256(raw) == expected_sha256,
         "source-requests-pin-mismatch")
    request = helper.decode(raw)
    helper.keys(request, {"schemaVersion", "evidenceCommit", "files", "landingProjection"})
    need(request["schemaVersion"] == "offmenu-reviewed-source-request/3"
         and re.fullmatch(r"[0-9a-f]{40}", request["evidenceCommit"]), "invalid-source-request")
    need(type(request["files"]) is list and request["files"], "empty-source-request")
    selection = []
    for row in request["files"]:
        helper.keys(row, {"sourcePath", "repositoryPath", "bytes", "sha256", "kind", "reviewRef"})
        helper.source_path(row["sourcePath"]); helper.relative(row["repositoryPath"])
        need(row["repositoryPath"].startswith("dev/reviewed-local-source-custody-20261027/recovered/")
             and row["kind"] in {"source", "test", "documentation"}, "outside-reviewed-source-custody")
        need(type(row["sha256"]) is str and HEX.fullmatch(row["sha256"]), "invalid-request-digest")
        need(row["bytes"] is None or type(row["bytes"]) is int and 0 <= row["bytes"] <= helper.MAX_FILE,
             "invalid-request-size")
        # Null length may only be resolved for an exact already-pinned digest.
        body, _ = helper.read_regular(row["sourcePath"], helper.MAX_FILE)
        need(sha256(body) == row["sha256"] and (row["bytes"] is None or len(body) == row["bytes"]),
             "requested-source-changed-no-upload")
        helper.check_body(body, row["kind"])
        selection.append(dict(row, bytes=len(body)))
    helper.validate_selection(selection)
    return selection, request


def prepare_directory(directory, helper, approved_selection):
    directory = str(Path(directory).absolute())
    manifest = helper.validate_packet_directory(directory)
    raw, _ = helper.read_regular(directory + "/packet-set.json", 2**63 - 1)
    need(helper.decode(raw) == manifest and raw == helper.canonical(manifest), "manifest-byte-binding-mismatch")
    records = [{"name": "packet-set.json", "path": directory + "/packet-set.json",
                "bytes": len(raw), "sha256": sha256(raw), "gitBlobSha": git_blob(raw)}]
    expected_digest = sha256(helper.canonical(approved_selection))
    for item in manifest["packets"]:
        packet_raw, _ = helper.read_regular(directory + "/" + item["jobId"] + ".json", helper.MAX_PACKET)
        packet = helper.validate_packet(helper.decode(packet_raw), item["jobId"])
        need(len(packet_raw) == item["bytes"] and sha256(packet_raw) == item["sha256"]
             and packet_raw == helper.canonical(packet)
             and all(packet[key] == item[key] for key in ("phase", "batch", "custody")),
             "packet-set-pin-changed-before-upload")
        need(packet["phase"] == "selected" and packet["selection"] == approved_selection
             and packet["custody"]["selectionSha256"] == expected_digest,
             "packet-not-explicit-approved-selection")
        records.append({"name": item["jobId"] + ".json", "path": directory + "/" + item["jobId"] + ".json",
                        "bytes": len(packet_raw), "sha256": sha256(packet_raw), "gitBlobSha": git_blob(packet_raw)})
    need(len(records) > 1, "missing-selected-packets")
    return records, sha256(raw), expected_digest


def project_landing(request, request_sha, helper, projector, projector_sha):
    spec = request["landingProjection"]
    helper.keys(spec, {"sourcePath", "sha256", "projectorSha256"})
    need(spec["sourcePath"] == projector.SOURCE_PATH and spec["sha256"] == projector.SOURCE_SHA
         and spec["projectorSha256"] == projector_sha, "landing-projection-pin-mismatch")
    helper.source_path(spec["sourcePath"])
    raw, _ = helper.read_regular(spec["sourcePath"], helper.MAX_FILE)
    need(sha256(raw) == spec["sha256"], "landing-parent-source-pin-mismatch")
    routes, bodies = projector.project(raw)
    items = []
    for digest, item in sorted(bodies.items()):
        body = item["bytes"]
        need(type(body) is bytes and sha256(body) == digest,
             "projected-body-pin-mismatch")
        helper.check_body(body, "source")
        names = sorted(item["routes"])
        need(names and all(route in routes and routes[route]["sha256"] == digest
                          and routes[route]["bytes"] == len(body) for route in names), "projected-route-identity-mismatch")
        items.append({"sha256": digest, "bytes": len(body), "routes": names,
                      "contentBase64": base64.b64encode(body).decode()})
    need(items, "no-approved-landing-source-bodies")
    return {"schemaVersion": "offmenu-landing-source-projection/1", "requestSha256": request_sha,
            "evidenceCommit": request["evidenceCommit"], "parentSourcePath": spec["sourcePath"],
            "parentSourceSha256": spec["sha256"], "parentSourceBytes": len(raw),
            "projectorSha256": projector_sha, "routeDescriptors": routes, "sourceBodies": items,
            "exclusions": "No opaque artwork or nonlanding/API/data/auth/state/corpus/product bodies; complete route descriptor metadata may remain; no full parent module or JavaScript execution"}


def publish(directory, helper, api, approved_selection, projection):
    records, manifest_digest, selection_digest = prepare_directory(directory, helper, approved_selection)
    projection_raw = helper.canonical(projection)
    projection_path = str(Path(directory) / "landing-source-projection.json")
    fd = os.open(projection_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as out: out.write(projection_raw)
    records.append({"name": "landing-source-projection.json", "path": projection_path, "bytes": len(projection_raw),
                    "sha256": sha256(projection_raw), "gitBlobSha": git_blob(projection_raw)})
    parent = current_ref(api)
    base_tree = verify_safe_parent(api, parent)
    destination = PREFIX + manifest_digest
    existing = tree_at(api, base_tree, destination)
    expected = {r["name"]: (r["gitBlobSha"], r["bytes"]) for r in records}
    if existing is not None:
        need(all(x.get("type") == "blob" and x.get("mode") == "100644" for x in existing)
             and {x["path"]: (x["sha"], x["size"]) for x in existing} == expected,
             "existing-metadata-conflict-no-overwrite")
        return {"status": "already-preserved", "commit": parent, "branch": BRANCH,
                "manifestSha256": manifest_digest, "selectionSha256": selection_digest,
                "path": destination, "actionsDispatched": 0}
    tree = []
    for record in records:
        raw, _ = helper.read_regular(record["path"], record["bytes"])
        need(len(raw) == record["bytes"] and sha256(raw) == record["sha256"], "packet-changed-before-upload")
        blob = api("repos/" + REPOSITORY + "/git/blobs", "POST",
                   {"encoding": "base64", "content": base64.b64encode(raw).decode()})
        need(blob.get("sha") == record["gitBlobSha"], "uploaded-blob-identity-mismatch")
        tree.append({"path": destination + "/" + record["name"], "mode": "100644", "type": "blob", "sha": blob["sha"]})
    created_tree = api("repos/" + REPOSITORY + "/git/trees", "POST", {"base_tree": base_tree, "tree": tree})
    commit = api("repos/" + REPOSITORY + "/git/commits", "POST", {
        "message": "Preserve explicit reviewed source packets directly; no Actions\n\nPacket-set SHA256 " + manifest_digest,
        "tree": created_tree["sha"], "parents": [parent]})
    new_sha = commit.get("sha", "")
    need(re.fullmatch(r"[0-9a-f]{40}", new_sha), "created-commit-unverified")
    need(current_ref(api) == parent, "custody-branch-moved-no-ref-update")
    try:
        api("repos/" + REPOSITORY + "/git/refs/heads/" + BRANCH, "PATCH", {"sha": new_sha, "force": False})
    except Exception:
        # Never blindly retry an uncertain ref mutation.
        need(current_ref(api) == new_sha, "ref-update-unconfirmed-readback-required")
    need(current_ref(api) == new_sha, "published-ref-readback-mismatch")
    remote = api("repos/" + REPOSITORY + "/git/commits/" + new_sha)
    need(remote.get("tree", {}).get("sha") == created_tree["sha"]
         and [x["sha"] for x in remote.get("parents", [])] == [parent], "published-ancestry-mismatch")
    final = tree_at(api, created_tree["sha"], destination)
    need(final is not None and {x["path"]: (x["sha"], x.get("size")) for x in final} == expected,
         "published-metadata-tree-mismatch")
    return {"status": "preserved", "commit": new_sha, "parent": parent, "branch": BRANCH,
            "manifestSha256": manifest_digest, "selectionSha256": selection_digest,
            "files": len(records), "bytes": sum(r["bytes"] for r in records),
            "path": destination, "actionsDispatched": 0, "applicationSourceUploaded": True, "runtimeAdopted": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--helper", required=True)
    parser.add_argument("--helper-sha256", required=True)
    parser.add_argument("--projector", required=True)
    parser.add_argument("--projector-sha256", required=True)
    parser.add_argument("--requests", required=True)
    parser.add_argument("--requests-sha256", required=True)
    parser.add_argument("--packet-directory", required=True)
    parser.add_argument("--job-prefix", required=True)
    args = parser.parse_args()
    helper = None
    stage = "load-helper"
    try:
        need(os.geteuid() != 0, "source-export-must-run-as-normal-owner")
        helper = load_helper(args.helper, args.helper_sha256)
        stage = "repository-metadata"
        repository = helper.repo_metadata(helper.CANONICAL)
        stage = "resolve-selected-files"
        selection, request = resolve_requests(args.requests, args.requests_sha256, helper)
        stage = "load-projector"
        projector = load_helper(args.projector, args.projector_sha256)
        stage = "landing-literal-projection"
        projection = project_landing(request, args.requests_sha256, helper, projector, args.projector_sha256)
        stage = "prepare-selected-packets"
        parts = helper.selected_parts(selection)
        need(helper.repo_metadata(helper.CANONICAL) == repository, "repository-head-changed-during-selection")
        helper.private_output(args.packet_directory,
              helper.packets("selected", args.job_prefix, repository, selection, parts))
        stage = "publish-reviewed-packets"
        result = publish(args.packet_directory, helper, GitHub(), selection, projection)
        result["projectedRouteDescriptors"] = len(projection["routeDescriptors"])
        result["projectedSourceBodies"] = len(projection["sourceBodies"])
        result["projectionSha256"] = sha256(helper.canonical(projection))
        result["requestsSha256"] = args.requests_sha256
        print(json.dumps(result, sort_keys=True)); return 0
    except Exception as error:
        safe_error = isinstance(error, Refused) or helper is not None and isinstance(error, helper.Rejected)
        code = str(error) if safe_error else "direct-selected-sync-failed-no-private-details"
        static_projector_errors = {"Exact source preimage mismatch", "Duplicate JSON key", "Unsupported freeze wrapper", "Invalid route descriptor", "Descriptor fields must be only sha256/bytes/mime", "Invalid descriptor pin", "Unsafe source route", "Missing literal source body", "Body pin mismatch", "Not text source", "Embedded product payload indicator"}
        static_projector_errors.update(prefix + name for prefix in ("Exactly one declaration required: ", "Initializer must be JSON object: ", "Unsupported initializer suffix: ") for name in ("ROOT14_ROUTES", "ROOT14_BODIES"))
        if stage == "landing-literal-projection" and str(error) in static_projector_errors:
            code = str(error)
        elif stage == "landing-literal-projection" and isinstance(error, json.JSONDecodeError):
            code = "landing-literal-json-decode-failed"
        print(json.dumps({"status": "stopped", "stage": stage, "exceptionClass": type(error).__name__, "errorCode": code, "errno": getattr(error, "errno", None), "actionsDispatched": 0}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
