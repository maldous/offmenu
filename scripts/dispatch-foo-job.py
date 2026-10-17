#!/usr/bin/env python3
"""Fixed-profile execution. Request JSON is data, never executable shell text."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import selectors
import signal
import subprocess
import sys
import tempfile
import time

CACHE = Path("/srv/offmenu-refresh/cache")
OUTPUT = Path("/srv/offmenu-refresh/outputs")
REPOSITORY_ID = "1416253963"
PROFILES = {"readiness", "inventory", "offline-replay", "smoke"}
MAX_REQUEST = 1024
MAX_CHILD_OUTPUT = 1024 * 1024
MAX_REPORT = 32768
ACTIVE_LOCK_FD = None
INVENTORY_COUNT_KEYS = {"entries", "files", "directories", "bytesObserved", "symlinksSkipped",
                        "privateOrRuntimeEntriesSkipped", "depthLimitedDirectories",
                        "specialFilesSkipped", "unreadableEntries", "unreadableDirectories"}


class JobError(Exception):
    pass


class Cancelled(BaseException):
    pass


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise JobError("duplicate-request-key")
        result[key] = value
    return result


def parse_request(raw):
    if len(raw) > MAX_REQUEST:
        raise JobError("request-too-large")
    try:
        request = json.loads(raw, object_pairs_hook=strict_object)
    except (ValueError, UnicodeError):
        raise JobError("invalid-request-json") from None
    if not isinstance(request, dict) or set(request) != {"schemaVersion", "jobId", "profile"}:
        raise JobError("request-keys-invalid")
    if type(request["schemaVersion"]) is not int or request["schemaVersion"] != 1:
        raise JobError("request-version-invalid")
    if not isinstance(request["jobId"], str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{7,63}", request["jobId"]):
        raise JobError("job-id-invalid")
    if not isinstance(request["profile"], str) or request["profile"] not in PROFILES:
        raise JobError("profile-not-allowlisted")
    return request


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def atomic_json(path, value):
    payload = canonical(value) + b"\n"
    if len(payload) > MAX_REPORT:
        raise JobError("report-limit-exceeded")
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".receipt-", delete=False) as f:
        temp = Path(f.name)
        try:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)


def verify_context(sha, code):
    if os.getuid() == 0 or os.geteuid() == 0:
        raise JobError("root-runtime-forbidden")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise JobError("trusted-code-sha-not-configured")
    if os.environ.get("GITHUB_REPOSITORY_ID") != REPOSITORY_ID:
        raise JobError("repository-identity-mismatch")
    actual = subprocess.check_output(["git", "-C", str(code), "rev-parse", "HEAD"],
                                     stderr=subprocess.DEVNULL, text=True, timeout=10).strip()
    if actual != sha:
        raise JobError("trusted-code-revision-mismatch")
    if subprocess.check_output(["git", "-C", str(code), "status", "--porcelain", "--untracked-files=no"],
                               stderr=subprocess.DEVNULL, timeout=10).strip():
        raise JobError("trusted-code-checkout-dirty")


def terminate_group(process):
    # Also terminates descendants left behind after their direct parent exits.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def safe_evidence(raw):
    evidence = {"stdoutBytes": len(raw), "stdoutSha256": hashlib.sha256(raw).hexdigest()}
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError):
        return evidence
    if not isinstance(value, dict):
        return evidence
    if value.get("schemaVersion") == "offmenu-refresh-inventory/1" and isinstance(value.get("counts"), dict):
        evidence["inventoryCounts"] = {k: v for k, v in value.get("counts", {}).items()
                                       if k in INVENTORY_COUNT_KEYS and type(v) is int and 0 <= v <= 2**63 - 1}
        for key in ("boundedScanComplete", "scopeComplete", "contentsRead", "assetHashesVerified", "pathsIncluded", "coverageEstablished"):
            if type(value.get(key)) is bool:
                evidence[key] = value[key]
    if isinstance(value.get("status"), str) and value.get("status") in {"complete", "failed"}:
        evidence["resultStatus"] = value["status"]
    if isinstance(value.get("action"), str) and value.get("action") in {"replayed", "verified-no-op", "force-rebuilt", "resumed"}:
        evidence["resultAction"] = value["action"]
    if isinstance(value.get("errorCode"), str) and value.get("errorCode") in {"unfinished-run-requires-resume", "writer-lock-held", "no-matching-run-to-resume",
                                  "online-acquisition-not-implemented", "operation-failed-inspect-local-state"}:
        evidence["errorCode"] = value["errorCode"]
    return evidence


def run_child(command, code, timeout=240):
    started = time.monotonic()
    env = {"PATH": "/usr/bin:/bin", "HOME": "/srv/offmenu-runner", "LANG": "C.UTF-8",
           "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(OUTPUT / "tmp")}
    # GitHub uses this non-secret marker to identify orphan processes at job end.
    if os.environ.get("RUNNER_TRACKING_ID"):
        env["RUNNER_TRACKING_ID"] = os.environ["RUNNER_TRACKING_ID"]
    # Drain bounded pipes instead of lowering RLIMIT_FSIZE: the refresh adapter
    # has a separate 256 MiB dataset-output limit that must remain compatible.
    process = subprocess.Popen(command, cwd=code, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True,
                               pass_fds=(() if ACTIVE_LOCK_FD is None else (ACTIVE_LOCK_FD,)))
    raw = bytearray()
    stderr_bytes = 0
    status = None
    group_closed = False
    deadline = started + timeout
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        try:
            while selector.get_map() and status is None:
                if not group_closed and process.poll() is not None:
                    # A detached descendant can keep the pipe open after the
                    # requested command exits. Do not let it run until timeout.
                    terminate_group(process)
                    group_closed = True
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    status, exit_code = "timeout", 124
                    break
                for key, _ in selector.select(min(remaining, 0.2)):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    if key.data == "stdout":
                        available = MAX_CHILD_OUTPUT - len(raw)
                        raw.extend(chunk[:available])
                        exceeded = len(chunk) > available
                    else:
                        stderr_bytes += len(chunk)
                        exceeded = stderr_bytes > MAX_CHILD_OUTPUT
                    if exceeded:
                        status, exit_code = "output-limit", 125
                        break
            if status is None:
                exit_code = process.wait(timeout=max(0.01, deadline - time.monotonic()))
                status = "passed" if exit_code == 0 else "failed"
        except subprocess.TimeoutExpired:
            status, exit_code = "timeout", 124
        except Cancelled:
            status, exit_code = "cancelled", 130
        finally:
            terminate_group(process)
            process.stdout.close()
            process.stderr.close()
    raw = bytes(raw)
    evidence = safe_evidence(raw)
    evidence["stderrBytes"] = stderr_bytes
    return {"status": status, "exitCode": exit_code, "durationSeconds": round(time.monotonic() - started, 3),
            "evidence": evidence}


def profile_steps(profile, code):
    python = sys.executable
    replay = [python, "-B", "-m", "offmenu.refresh", "replay",
              "--manifest", "tests/fixtures/corpus-refresh/input-manifest.json",
              "--input-root", "tests/fixtures/corpus-refresh", "--workspace", str(OUTPUT / "pilot")]
    steps = [("readiness", [], [python, "-B", "-c", "import sys, fcntl, resource, offmenu.refresh; assert sys.version_info >= (3, 10)"])]
    if profile in {"inventory", "smoke"}:
        steps.append(("inventory", ["readiness"], [python, "-B", "-m", "offmenu.refresh", "inventory",
                                                  "--root", str(CACHE), "--max-entries", "10000", "--max-depth", "4"]))
    if profile in {"offline-replay", "smoke"}:
        steps += [("refresh-tests", ["readiness"], [python, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_corpus_refresh.py"]),
                  ("offline-replay", ["readiness", "refresh-tests"], replay),
                  ("replay-idempotency", ["offline-replay"], replay)]
    return steps


def run_profile(request, sha, code, run_id, attempt):
    results = []
    by_id = {}
    cancelled = False
    for step_id, dependencies, command in profile_steps(request["profile"], code):
        blocked = [dep for dep in dependencies if by_id[dep]["status"] != "passed"]
        if cancelled or blocked:
            result = {"status": "skipped", "exitCode": None, "durationSeconds": 0,
                      "skipReason": "job-cancelled" if cancelled else "dependency-failed", "blockedBy": blocked}
        else:
            try:
                result = run_child(command, code)
                if result["status"] == "failed" and result["evidence"].get("errorCode") == "unfinished-run-requires-resume" and step_id == "offline-replay":
                    previous = result
                    result = run_child(command + ["--resume"], code)
                    result["resumeAttempt"] = True
                    result["durationSeconds"] += previous["durationSeconds"]
                if step_id == "replay-idempotency" and result["status"] == "passed" and result["evidence"].get("resultAction") != "verified-no-op":
                    result.update(status="failed", exitCode=3, errorCode="idempotency-not-established")
            except Cancelled:
                result = {"status": "cancelled", "exitCode": 130, "durationSeconds": 0}
            except (OSError, subprocess.SubprocessError):
                result = {"status": "failed", "exitCode": 1, "durationSeconds": 0, "errorCode": "step-launch-failed"}
            cancelled = result["status"] == "cancelled"
        result.update(stepId=step_id, dependsOn=dependencies)
        by_id[step_id] = result
        results.append(result)
    state = "cancelled" if cancelled else ("passed" if all(x["status"] == "passed" for x in results) else "failed")
    return {"schemaVersion": 1, "reportKind": "offmenu-foo-job", "jobId": request["jobId"],
            "profile": request["profile"], "trustedCodeSha": sha, "githubRunId": run_id,
            "githubRunAttempt": attempt, "status": state, "steps": results,
            "sourceContentsUploaded": False, "externalPublication": False}


def safe_dir(path):
    if path.is_symlink():
        raise JobError("output-directory-symlink-forbidden")
    path.mkdir(mode=0o700, exist_ok=True)
    if not path.is_dir() or path.stat().st_uid != os.getuid():
        raise JobError("output-directory-owner-invalid")


def execute(request, sha, code, run_id, attempt):
    global ACTIVE_LOCK_FD
    # A kernel lock has no stale-file problem and is released on process death.
    safe_dir(OUTPUT)
    for name in ("locks", "job-receipts", "tmp"):
        safe_dir(OUTPUT / name)
    fd = os.open(OUTPUT / "locks" / "dispatcher.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "r+") as held:
        try:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise JobError("another-job-is-running-retry-later") from None
        receipt = OUTPUT / "job-receipts" / (request["jobId"] + ".json")
        identity = hashlib.sha256(canonical({"request": request, "trustedCodeSha": sha})).hexdigest()
        if receipt.is_symlink():
            raise JobError("receipt-symlink-forbidden")
        if receipt.exists():
            if receipt.stat().st_size > MAX_REPORT:
                raise JobError("previous-receipt-invalid")
            previous = json.loads(receipt.read_bytes())
            if previous.get("requestIdentity") != identity:
                raise JobError("job-id-reused-for-different-request")
            if previous.get("status") in {"passed", "failed", "cancelled"}:
                return previous | {"delivery": "existing-receipt-no-execution"}
            # An interrupted coordinator may retry. The downstream replay handles resumable checkpoints.
        atomic_json(receipt, {"status": "running", "requestIdentity": identity})
        # The active direct child inherits custody of this flock. If the
        # coordinator dies abruptly, a second coordinator remains blocked until
        # that child exits. The refresh worker additionally retains its own lock.
        ACTIVE_LOCK_FD = held.fileno()
        try:
            report = run_profile(request, sha, code, run_id, attempt)
        finally:
            ACTIVE_LOCK_FD = None
        report["requestIdentity"] = identity
        atomic_json(receipt, report)
        return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--trusted-code-sha", required=True)
    args = parser.parse_args(argv)
    os.umask(0o077)
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(Cancelled()))
    signal.signal(signal.SIGINT, lambda *_: (_ for _ in ()).throw(Cancelled()))
    try:
        if args.request.is_symlink() or not args.request.is_file() or args.request.stat().st_size > MAX_REQUEST:
            raise JobError("request-file-invalid")
        request = parse_request(args.request.read_bytes())
        code = Path(__file__).resolve().parent.parent
        verify_context(args.trusted_code_sha, code)
        run_id, attempt = os.environ.get("GITHUB_RUN_ID", ""), os.environ.get("GITHUB_RUN_ATTEMPT", "")
        if not re.fullmatch(r"[0-9]{1,20}", run_id) or not re.fullmatch(r"[0-9]{1,5}", attempt):
            raise JobError("github-run-identity-invalid")
        report = execute(request, args.trusted_code_sha, code, run_id, attempt)
    except JobError as error:
        report = {"schemaVersion": 1, "status": "blocked", "errorCode": str(error)}
    except Cancelled:
        report = {"schemaVersion": 1, "status": "cancelled", "errorCode": "coordinator-cancelled"}
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        report = {"schemaVersion": 1, "status": "failed", "errorCode": "coordinator-failed"}
    payload = canonical(report)
    print("OFFMENU_JOB_REPORT " + payload.decode())
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as stream:
            stream.write("OffMenu foo job report\n\n```json\n" + json.dumps(report, indent=2, sort_keys=True) + "\n```\n")
    return 0 if report["status"] == "passed" else (130 if report["status"] == "cancelled" else 1)


if __name__ == "__main__":
    raise SystemExit(main())
