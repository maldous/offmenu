#!/usr/bin/env python3
"""Run independent setup diagnostics and optionally publish one sanitized report."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import pwd
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time

REPO = "maldous/offmenu"
ROOT = Path(__file__).resolve().parents[1]
LOG_LIMIT = 1024 * 1024
REPORT_LIMIT = 32768
STEP_TIMEOUT = 240


def environment(log_dir, for_github=False):
    result = {"PATH": "/usr/bin:/bin", "HOME": str(Path.home()), "LANG": "C.UTF-8",
              "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(log_dir),
              "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"}
    if for_github:
        # Reuse the owner's existing gh authentication only for gh's auth/API
        # subprocesses. Test/runner environments never receive these tokens.
        # Values remain in process memory: never print, serialize, or log them.
        for key in ("GH_CONFIG_DIR", "XDG_CONFIG_HOME", "GH_TOKEN", "GITHUB_TOKEN"):
            if os.environ.get(key):
                result[key] = os.environ[key]
    return result


def stop_group(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def run_step(step_id, command, log_dir, timeout=STEP_TIMEOUT, preserve_session=False):
    started = time.monotonic()
    stdout_path, stderr_path = log_dir / (step_id + ".stdout"), log_dir / (step_id + ".stderr")
    result = {"stepId": step_id, "status": "failed", "exitCode": None,
              "stdoutBytes": 0, "stderrBytes": 0, "logLimitExceeded": False}
    # Local sudo timestamps are scoped to the original terminal/session.
    # Bootstrap admin commands need a new process group for cleanup, but must
    # retain that session. Ordinary diagnostics retain the detached default.
    process_options = {"start_new_session": not preserve_session}
    if preserve_session:
        if sys.version_info >= (3, 11):
            process_options["process_group"] = 0
        else:
            process_options["preexec_fn"] = os.setpgrp
    try:
        process = subprocess.Popen(command, cwd=ROOT, env=environment(log_dir),
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, **process_options)
    except OSError:
        result.update(errorCode="step-could-not-start", durationSeconds=round(time.monotonic() - started, 3))
        return result
    with stdout_path.open("xb") as out, stderr_path.open("xb") as err, selectors.DefaultSelector() as selector:
        # mkdtemp plus umask keeps raw local diagnostics private. No raw log is uploaded.
        os.chmod(stdout_path, 0o600); os.chmod(stderr_path, 0o600)
        selector.register(process.stdout, selectors.EVENT_READ, (out, "stdoutBytes"))
        selector.register(process.stderr, selectors.EVENT_READ, (err, "stderrBytes"))
        finished = False
        try:
            while selector.get_map():
                if not finished and process.poll() is not None:
                    stop_group(process)
                    finished = True
                remaining = started + timeout - time.monotonic()
                if remaining <= 0:
                    result.update(status="timeout", errorCode="step-timeout")
                    break
                limit_hit = False
                for key, _ in selector.select(min(remaining, 0.2)):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    stream, counter = key.data
                    available = LOG_LIMIT - result[counter]
                    kept = chunk[:available]
                    stream.write(kept)
                    result[counter] += len(kept)
                    if len(chunk) > available:
                        result.update(status="output-limit", errorCode="local-log-limit", logLimitExceeded=True)
                        limit_hit = True
                        break
                if limit_hit:
                    break
            else:
                code = process.wait(timeout=max(0.01, started + timeout - time.monotonic()))
                result.update(status="passed" if code == 0 else "failed")
        except subprocess.TimeoutExpired:
            result.update(status="timeout", errorCode="step-timeout")
        except KeyboardInterrupt:
            result.update(status="cancelled", errorCode="step-cancelled")
        finally:
            stop_group(process)
            result["exitCode"] = process.returncode
            process.stdout.close(); process.stderr.close()
    result["durationSeconds"] = round(time.monotonic() - started, 3)
    return result


def sanitized_preflight(raw):
    value = json.loads(raw)
    if not isinstance(value, dict) or value.get("reportKind") != "offmenu-runner-host-preflight":
        raise ValueError("invalid-preflight")
    safe = {"repository": REPO, "intendedHostAlias": "foo", "hostIdentityVerified": False,
            "registrationOrServiceVerified": False}
    boolean_keys = ("linux", "pythonSupported", "systemdSupported", "dedicatedAccountExists",
                    "dedicatedAccountValid", "runnerInstalled", "runnerRegistrationPresent",
                    "serviceUnitPresent", "cacheViewPresent", "outputDirectoryPresent")
    for key in boolean_keys:
        item = value.get(key)
        if type(item) is bool or item is None:
            safe[key] = item
    for key in ("distribution", "distributionVersion", "architecture", "pythonVersion"):
        item = value.get(key)
        if isinstance(item, str) and re.fullmatch(r"[a-zA-Z0-9_.-]{1,40}", item):
            safe[key] = item
    version = value.get("systemdVersion")
    if type(version) is int and 0 <= version <= 99999:
        safe["systemdVersion"] = version
    tools = value.get("tools")
    safe["tools"] = {key: tools[key] for key in ("curl", "git", "systemctl", "sha256sum")
                     if isinstance(tools, dict) and type(tools.get(key)) is bool}
    return safe


def run_batch(log_dir):
    commands = [
        ("preflight", [sys.executable, "-B", "scripts/runner_host_setup.py", "preflight"]),
        ("runner-unit-tests", [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_foo*.py"]),
        ("refresh-unit-tests", [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_corpus_refresh.py"]),
    ]
    steps = []
    cancelled = False
    for name, command in commands:
        if cancelled:
            steps.append({"stepId": name, "status": "skipped", "exitCode": None,
                          "durationSeconds": 0, "skipReason": "operator-cancelled"})
            continue
        try:
            result = run_step(name, command, log_dir)
        except (OSError, subprocess.SubprocessError):
            result = {"stepId": name, "status": "failed", "exitCode": None,
                      "durationSeconds": 0, "errorCode": "local-diagnostic-failed"}
        if name == "preflight" and result["status"] == "passed":
            try:
                safe = sanitized_preflight((log_dir / "preflight.stdout").read_bytes())
                result["preflight"] = safe
                ready = (safe.get("linux") is True and safe.get("pythonSupported") is True
                         and safe.get("systemdSupported") is True and safe.get("architecture") in {"x86_64", "aarch64", "arm64"}
                         and all(safe["tools"].get(x) is True for x in ("curl", "git", "systemctl", "sha256sum")))
                if not ready:
                    result.update(status="failed", errorCode="host-prerequisite-missing")
            except (ValueError, OSError, TypeError):
                result.update(status="failed", errorCode="preflight-report-invalid")
        if name.endswith("unit-tests"):
            try:
                test_log = (log_dir / (name + ".stderr")).read_text(errors="replace")
                count = re.search(r"^Ran ([0-9]{1,6}) tests? in ", test_log, flags=re.MULTILINE)
                if count:
                    result["testCount"] = int(count.group(1))
                if result["status"] == "passed" and (not count or int(count.group(1)) == 0):
                    result.update(status="failed", errorCode="no-test-execution-established")
            except OSError:
                if result["status"] == "passed":
                    result.update(status="failed", errorCode="test-evidence-unavailable")
        cancelled = result["status"] == "cancelled"
        steps.append(result)
    state = "cancelled" if cancelled else ("passed" if all(s["status"] == "passed" for s in steps) else "failed")
    return {"schemaVersion": 1, "reportKind": "offmenu-setup-check-batch", "repository": REPO,
            "checkedAt": datetime.now(timezone.utc).isoformat(), "status": state, "steps": steps,
            "rawLogsUploaded": False, "datasetContentsUploaded": False,
            "adminActionsPerformed": False, "registrationAttempted": False,
            "liveRunnerOrServiceVerified": False}


def report_bytes(report):
    raw = json.dumps(report, indent=2, sort_keys=True, allow_nan=False).encode()
    if len(raw) > REPORT_LIMIT:
        raise ValueError("report-too-large")
    return raw


def publish_once(report, issue, log_dir):
    gh = shutil.which("gh")
    if not gh:
        return "not-posted-gh-unavailable"
    if os.getuid() == 0 or pwd.getpwuid(os.getuid()).pw_name == "offmenu-runner":
        return "not-posted-use-normal-user-account"
    env = environment(log_dir, for_github=True)
    try:
        auth = subprocess.run([gh, "auth", "status", "--hostname", "github.com"], env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        if auth.returncode:
            return "not-posted-existing-gh-login-required"
    except (OSError, subprocess.SubprocessError):
        return "not-posted-gh-auth-check-failed"
    body = "OffMenu foo setup checks: preflight and both test groups. Raw logs remain private on the host.\n\n```json\n" + report_bytes(report).decode() + "\n```\n"
    payload_path = log_dir / "github-report.json"
    payload_path.write_text(json.dumps({"body": body}) + "\n")
    os.chmod(payload_path, 0o600)
    # Exactly one POST attempt. Never retry an uncertain response automatically.
    try:
        result = subprocess.run([gh, "api", "--hostname", "github.com", "--method", "POST",
                                 f"repos/{REPO}/issues/{issue}/comments", "--input", str(payload_path), "--silent"],
                                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        return "posted" if result.returncode == 0 else "post-not-verified-check-github-before-retrying"
    except (OSError, subprocess.SubprocessError):
        return "post-not-verified-check-github-before-retrying"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true", help="Post exactly one sanitized combined report using existing gh login")
    parser.add_argument("--issue", type=int, default=30, help="Existing OffMenu issue/PR number (default: 30)")
    args = parser.parse_args(argv)
    if args.issue < 1:
        parser.error("--issue must be positive")
    if os.getuid() == 0 or os.geteuid() == 0:
        print("Run this diagnostic script as your normal account, without sudo.", file=sys.stderr)
        return 2
    os.umask(0o077)
    log_dir = Path(tempfile.mkdtemp(prefix="offmenu-setup-check-"))
    report = run_batch(log_dir)
    raw = report_bytes(report)
    (log_dir / "report.json").write_bytes(raw + b"\n")
    print(raw.decode())
    print("Private raw diagnostic logs: " + str(log_dir), file=sys.stderr)
    publication = "not-requested"
    if args.publish:
        publication = publish_once(report, args.issue, log_dir)
        print("GitHub report publication: " + publication)
    if publication not in {"not-requested", "posted"}:
        return 2
    return 0 if report["status"] == "passed" else (130 if report["status"] == "cancelled" else 1)


if __name__ == "__main__":
    raise SystemExit(main())
