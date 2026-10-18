#!/usr/bin/env python3
"""Fixed-profile execution. Request JSON is data, never executable shell text."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import resource
import selectors
import signal
import subprocess
import sys
import tempfile
import threading
import time

CACHE = Path("/srv/offmenu-refresh/cache")
OUTPUT = Path("/srv/offmenu-refresh/outputs")
REPOSITORY_ID = "1416253963"
PROFILES = {"readiness", "inventory", "offline-replay", "smoke", "delivery-diagnostics", "national-schema-survey", "ciqual-source-native", "global-readiness", "offline-reconciliation", "collection-prepare", "zenodo-private-original"}
MAX_REQUEST = 1024
MAX_CHILD_OUTPUT = 1024 * 1024
MAX_REPORT = 32768
MAX_SURVEY_EVIDENCE = 96 * 1024
MAX_SURVEY_REPORT = 128 * 1024
ACTIVE_LOCK_FD = None
CANCEL_EVENT = threading.Event()
MAX_DIAGNOSTIC_EVIDENCE = 12 * 1024
LEDGER_SOURCE_SHA = "8c25c6d76088c958d17f7adc4a3c0af7aab5c298"
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


def report_limit(value):
    return MAX_SURVEY_REPORT if value.get('profile') == 'national-schema-survey' else MAX_REPORT


def atomic_json(path, value):
    payload = canonical(value) + b"\n"
    if len(payload) > report_limit(value):
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


def finite_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("nonfinite-child-evidence")
    return result


def diagnostic_evidence(value):
    """Rebind child reports through pinned, closed-schema sanitizers."""
    schemas = {
        "offmenu-global-readiness/1": ("global-readiness.py", "globalReadiness"),
        "offmenu-fixed-original-summary/1": ("acquire-fixed-zenodo.py", "fixedOriginal"),
        "offmenu-collection-preparation-summary/1": ("prepare-fixed-collection.py", "collectionPreparation"),
        "offmenu-offline-reconciliation/1": ("offline-reconciliation.py", "offlineReconciliation"),
        "offmenu-ledger-structural-audit/1": ("offmenu_ledger_audit.py", "ledgerAudit"),
        "offmenu-selected-data-inventory/1": ("inspect-selected-datasets.py", "selectedDataInventory"),
    }
    schema = value.get("schemaVersion")
    if schema == 'offmenu-selected-schema-survey/1':
        try:
            # Resolve only this trusted checkout's known diagnostic package.
            root = str(Path(__file__).resolve().parent.parent)
            if root not in sys.path:
                sys.path.insert(0, root)
            from offmenu.refresh.survey import sanitize_report
            clean = sanitize_report(value)
            if len(canonical(clean)) > MAX_SURVEY_EVIDENCE:
                return {"diagnosticEvidenceError": "diagnostic-evidence-limit-exceeded"}
            return {"schemaSurvey": clean}
        except Exception:
            return {"diagnosticEvidenceError": "invalid-diagnostic-schema"}
    if schema == 'offmenu-ciqual-source-native-receipt/1':
        try:
            root = str(Path(__file__).resolve().parent.parent)
            if root not in sys.path:
                sys.path.insert(0, root)
            from offmenu.refresh.native_ciqual import sanitize_receipt
            return {'ciqualNative': sanitize_receipt(value)}
        except Exception:
            return {'diagnosticEvidenceError': 'invalid-diagnostic-schema'}
    if not isinstance(schema, str) or schema not in schemas:
        return {}
    filename, key = schemas[schema]
    path = Path(__file__).resolve().parent / filename
    try:
        spec = importlib.util.spec_from_file_location("offmenu_diagnostic_sanitizer_" + key, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        try:
            sanitized = module.sanitize_report(value)
        except Exception:
            # Validation errors are private and never enter published evidence.
            return {"diagnosticEvidenceError": "invalid-diagnostic-schema"}
        if not isinstance(sanitized, dict) or sanitized.get("schemaVersion") != schema:
            return {"diagnosticEvidenceError": "invalid-diagnostic-schema"}
        if len(canonical(sanitized)) > MAX_DIAGNOSTIC_EVIDENCE:
            return {"diagnosticEvidenceError": "diagnostic-evidence-limit-exceeded"}
        return {key: sanitized}
    except (OSError, ValueError, TypeError, KeyError, AttributeError, ImportError, RecursionError):
        return {"diagnosticEvidenceError": "invalid-diagnostic-schema"}


def safe_evidence(raw):
    evidence = {"stdoutBytes": len(raw), "stdoutSha256": hashlib.sha256(raw).hexdigest()}
    try:
        value = json.loads(raw, object_pairs_hook=strict_object, parse_float=finite_float,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, JobError, RecursionError):
        return evidence
    if not isinstance(value, dict):
        return evidence
    evidence.update(diagnostic_evidence(value))
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
    if value.get('schemaVersion') == 'offmenu-refresh-error/1':
        try:
            root = str(Path(__file__).resolve().parent.parent)
            if root not in sys.path:
                sys.path.insert(0, root)
            from offmenu.refresh.native_ciqual import ERROR_CODES
            if value.get('errorCode') in ERROR_CODES:
                evidence['errorCode'] = value['errorCode']
        except (ImportError, TypeError):
            pass
    return evidence


def run_child(command, code, timeout=240):
    started = time.monotonic()
    if CANCEL_EVENT.is_set():
        return {"status": "cancelled", "exitCode": 130, "durationSeconds": 0, "evidence": {}}
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
                if CANCEL_EVENT.is_set():
                    status, exit_code = "cancelled", 130
                    break
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


def profile_steps(profile, code, trusted_sha=None):
    python = sys.executable
    replay = [python, "-B", "-m", "offmenu.refresh", "replay",
              "--manifest", "tests/fixtures/corpus-refresh/input-manifest.json",
              "--input-root", "tests/fixtures/corpus-refresh", "--workspace", str(OUTPUT / "pilot")]
    steps = [("readiness", [], [python, "-B", "-c", "import sys, fcntl, resource, offmenu.refresh; assert sys.version_info >= (3, 10)"])]
    if profile == "zenodo-private-original":
        steps += [
            ("zenodo-original-tests", ["readiness"], [python, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_fixed_zenodo_original.py"]),
            ("zenodo-private-original", ["readiness", "zenodo-original-tests"], [python, "-B", "scripts/acquire-fixed-zenodo.py"]),
        ]
    if profile == "collection-prepare":
        steps += [
            ("collection-preparation-tests", ["readiness"], [python, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_fixed_collection_preparation.py"]),
            ("collection-prepare", ["readiness", "collection-preparation-tests"], [python, "-B", "scripts/prepare-fixed-collection.py"]),
        ]
    if profile == "offline-reconciliation":
        steps.append(("reconciliation-tests", ["readiness"], [python, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_offline_reconciliation.py"]))
        for mode in ("source-claims", "transfer-receipts", "native-continuity", "disk-reservations", "pending-ownership"):
            steps.append((mode, ["readiness", "reconciliation-tests"], [python, "-B", "scripts/offline-reconciliation.py", "--mode", mode]))
    if profile == "global-readiness":
        observed = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        steps += [
            ("global-readiness-tests", ["readiness"], [python, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_global_readiness.py"]),
            ("global-runtime", ["readiness", "global-readiness-tests"], [python, "-B", "scripts/global-readiness.py", "--mode", "runtime", "--observed-at", observed]),
            ("global-registry-tests", ["readiness"], [python, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_global_coverage.py"]),
            ("global-harness-tests", ["readiness"], [python, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_refresh_global_run.py"]),
            ("global-coverage", ["readiness", "global-readiness-tests", "global-registry-tests", "global-harness-tests"], [python, "-B", "scripts/global-readiness.py", "--mode", "coverage", "--observed-at", observed]),
        ]
    if profile == "ciqual-source-native":
        root = str(Path(__file__).resolve().parent.parent)
        if root not in sys.path:
            sys.path.insert(0, root)
        from offmenu.refresh.native_ciqual import selected_output
        candidate = [python, '-B', '-m', 'offmenu.refresh', 'candidate-ciqual-selected',
                     '--output', str(selected_output(trusted_sha))]
        steps += [
            ('ciqual-native-tests', ['readiness'], [python, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_ciqual_source_native*.py']),
            ('ciqual-native-candidate', ['readiness', 'ciqual-native-tests'], candidate),
            ('ciqual-native-retry', ['ciqual-native-candidate'], list(candidate)),
        ]
    if profile == "national-schema-survey":
        steps += [
            ("schema-survey-tests", ["readiness"], [python, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_refresh_survey*.py"]),
            ("schema-survey", ["readiness", "schema-survey-tests"], [python, "-B", "-m", "offmenu.refresh", "survey-selected", "--workspace", str(OUTPUT / "schema-surveys")]),
        ]
    if profile in {"inventory", "smoke", "delivery-diagnostics", "global-readiness"}:
        steps.append(("inventory", ["readiness"], [python, "-B", "-m", "offmenu.refresh", "inventory",
                                                  "--root", str(CACHE), "--max-entries", "10000", "--max-depth", "4"]))
    if profile == "global-readiness":
        steps += [
            ("dataset-tests", ["readiness"], [python, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_selected_dataset_metadata.py"]),
            ("selected-data-inventory", ["readiness", "dataset-tests"], [python, "-B", "scripts/inspect-selected-datasets.py", "--cache-root", str(CACHE)]),
        ]
    if profile == "delivery-diagnostics":
        steps += [
            ("ledger-tests", ["readiness"], [python, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_offmenu_ledger_audit.py"]),
            ("ledger-audit", ["readiness", "ledger-tests"], [python, "-B", "scripts/offmenu_ledger_audit.py"]),
            ("dataset-tests", ["readiness"], [python, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_selected_dataset_metadata.py"]),
            ("selected-data-inventory", ["readiness", "dataset-tests"], [python, "-B", "scripts/inspect-selected-datasets.py", "--cache-root", str(CACHE)]),
        ]
    if profile in {"offline-replay", "smoke", "delivery-diagnostics", "global-readiness"}:
        steps += [("refresh-tests", ["readiness"], [python, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_corpus_refresh.py"]),
                  ("offline-replay", ["readiness", "refresh-tests"], replay),
                  ("replay-idempotency", ["offline-replay"], replay)]
    return steps


def run_step(step_id, command, code):
    try:
        result = (run_child(command, code, timeout=930) if step_id == "zenodo-private-original"
                  else run_child(command, code))
        if result["status"] == "failed" and result["evidence"].get("errorCode") == "unfinished-run-requires-resume" and step_id == "offline-replay":
            previous = result
            result = run_child(command + ["--resume"], code)
            result["resumeAttempt"] = True
            result["durationSeconds"] += previous["durationSeconds"]
        if step_id == "replay-idempotency" and result["status"] == "passed" and result["evidence"].get("resultAction") != "verified-no-op":
            result.update(status="failed", exitCode=3, errorCode="idempotency-not-established")
        if step_id in {'ciqual-native-candidate', 'ciqual-native-retry'} and result['status'] == 'passed':
            receipt = result['evidence'].get('ciqualNative', {})
            if receipt.get('status') != 'private-source-native-extracted':
                result.update(status='failed', exitCode=3, errorCode='native-candidate-not-established')
            elif step_id == 'ciqual-native-retry' and receipt.get('created') is not False:
                result.update(status='failed', exitCode=3, errorCode='native-idempotency-not-established')
        if step_id == "zenodo-private-original" and result["status"] in {"passed", "failed"}:
            report = result["evidence"].get("fixedOriginal", {})
            if report.get("status") == "verified-private-original" and result["exitCode"] == 0:
                result["status"] = "passed"
            elif report.get("status") == "blocked" and result["exitCode"] == 2:
                result["status"] = "blocked"
            elif report.get("status") != "failed" or result["exitCode"] != 2:
                result.update(status="failed", exitCode=3, errorCode="fixed-original-report-invalid")
        if step_id == "collection-prepare" and result["status"] in {"passed", "failed"}:
            report = result["evidence"].get("collectionPreparation", {})
            if report.get("status") == "prepared" and result["exitCode"] == 0:
                result["status"] = "passed"
            elif report.get("status") == "blocked" and result["exitCode"] == 2:
                result["status"] = "blocked"
            else:
                result.update(status="failed", exitCode=3, errorCode="collection-preparation-invalid")
        if step_id in {"source-claims", "transfer-receipts", "native-continuity", "disk-reservations", "pending-ownership"} and result["status"] in {"passed", "failed"}:
            report = result["evidence"].get("offlineReconciliation", {})
            if report.get("mode") != step_id:
                result.update(status="failed", exitCode=3, errorCode="reconciliation-report-invalid")
            elif result["exitCode"] == 2 and report.get("status") == "blocked":
                result["status"] = "blocked"
            elif result["exitCode"] != 0 or report.get("status") != "complete":
                result.update(status="failed", exitCode=3, errorCode="reconciliation-not-established")
        if step_id in {"global-runtime", "global-coverage"} and result["status"] in {"passed", "failed"}:
            report = result["evidence"].get("globalReadiness", {})
            expected_kind = "runtime" if step_id == "global-runtime" else "coverage"
            if report.get("kind") != expected_kind:
                result.update(status="failed", exitCode=3, errorCode="global-readiness-report-invalid")
            elif result["exitCode"] == 2 and report.get("status") == "blocked":
                result["status"] = "blocked"
            elif result["exitCode"] != 0 or report.get("status") != "complete":
                result.update(status="failed", exitCode=3, errorCode="global-readiness-not-established")
        if step_id == "schema-survey" and result["status"] in {"passed", "failed"}:
            report = result["evidence"].get("schemaSurvey", {})
            if report.get("surveyComplete") is True and result["exitCode"] == 0:
                result["status"] = "passed"
            elif report.get("status") == "held" and result["exitCode"] == 2:
                result["status"] = "blocked"
            else:
                result.update(status="failed", exitCode=3, errorCode="schema-survey-result-not-established")
        if step_id in {"ledger-audit", "selected-data-inventory"} and result["status"] in {"passed", "failed"}:
            key = "ledgerAudit" if step_id == "ledger-audit" else "selectedDataInventory"
            report = result["evidence"].get(key, {})
            if step_id == "selected-data-inventory" and result["exitCode"] == 2 and report.get("status") == "incomplete":
                result["status"] = "blocked"
            elif result["status"] == "passed":
                expected = "complete" if step_id == "ledger-audit" else "ready-for-adapter-design"
                if report.get("status") != expected:
                    result.update(status="failed", exitCode=3, errorCode="diagnostic-result-not-established")
    except Cancelled:
        CANCEL_EVENT.set()
        result = {"status": "cancelled", "exitCode": 130, "durationSeconds": 0}
    except (OSError, subprocess.SubprocessError):
        result = {"status": "failed", "exitCode": 1, "durationSeconds": 0, "errorCode": "step-launch-failed"}
    return result


def skipped(cancelled, blocked):
    return {"status": "skipped", "exitCode": None, "durationSeconds": 0,
            "skipReason": "job-cancelled" if cancelled else "dependency-failed", "blockedBy": blocked}


def parallel_diagnostics(steps, code):
    """Two bounded child processes; dependencies preserve the serial replay pair.

    Cancellation propagates to each process group before the shared lock can be
    released. No shell command or parallelism setting is accepted from requests.
    """
    by_id, pending, active = {}, list(steps), {}
    cancelled = False
    with ThreadPoolExecutor(max_workers=2) as pool:
        while pending or active:
            try:
                for step in list(pending):
                    step_id, dependencies, command = step
                    if not all(dep in by_id for dep in dependencies):
                        continue
                    blocked = [dep for dep in dependencies if by_id[dep]["status"] != "passed"]
                    if cancelled or CANCEL_EVENT.is_set() or blocked:
                        by_id[step_id] = skipped(cancelled or CANCEL_EVENT.is_set(), blocked)
                        pending.remove(step)
                    elif len(active) < 2:
                        active[pool.submit(run_step, step_id, command, code)] = step_id
                        pending.remove(step)
                if active:
                    done, _ = wait(active, timeout=0.2, return_when=FIRST_COMPLETED)
                    for future in done:
                        step_id = active.pop(future)
                        by_id[step_id] = future.result()
                        if by_id[step_id]["status"] == "cancelled":
                            cancelled = True
                            CANCEL_EVENT.set()
            except Cancelled:
                cancelled = True
                CANCEL_EVENT.set()
    return by_id, cancelled


def run_profile(request, sha, code, run_id, attempt):
    steps = profile_steps(request["profile"], code, sha)
    cancelled = False
    if request["profile"] in {"delivery-diagnostics", "global-readiness"}:
        by_id, cancelled = parallel_diagnostics(steps, code)
    else:
        by_id = {}
        for step_id, dependencies, command in steps:
            blocked = [dep for dep in dependencies if by_id[dep]["status"] != "passed"]
            result = skipped(cancelled, blocked) if cancelled or blocked else run_step(step_id, command, code)
            cancelled = cancelled or result["status"] == "cancelled"
            if step_id == 'ciqual-native-retry' and result['status'] == 'passed':
                first = by_id['ciqual-native-candidate']['evidence']['ciqualNative']
                repeated = result['evidence']['ciqualNative']
                if {k: v for k, v in first.items() if k != 'created'} != {k: v for k, v in repeated.items() if k != 'created'}:
                    result.update(status='failed', exitCode=3, errorCode='native-retry-artifacts-changed')
            by_id[step_id] = result
    results = [by_id[step_id] | {"stepId": step_id, "dependsOn": dependencies}
               for step_id, dependencies, _ in steps]
    statuses = {result["status"] for result in results}
    state = ("cancelled" if cancelled else "passed" if statuses == {"passed"} else
             "incomplete" if statuses <= {"passed", "blocked"} else "failed")
    report = {"schemaVersion": 1, "reportKind": "offmenu-foo-job", "jobId": request["jobId"],
              "profile": request["profile"], "trustedCodeSha": sha, "githubRunId": run_id,
              "githubRunAttempt": attempt, "status": state, "steps": results,
              "sourceContentsUploaded": False, "externalPublication": False}
    if request["profile"] == "delivery-diagnostics":
        report.update(manifestCommitSha=LEDGER_SOURCE_SHA, maximumParallelChildren=2,
                      diagnosticScope="structural-ledger-and-selected-cache-metadata",
                      corpusAcceptanceEstablished=False)
    if request["profile"] == "zenodo-private-original":
        report.update(maximumParallelChildren=1, diagnosticScope="one-selected-global-private-original",
                      corpusAcceptanceEstablished=False, countryCoverageComplete=False,
                      candidateGenerationEnabled=False, commercialReuseApproved=False)
    if request["profile"] == "collection-prepare":
        report.update(maximumParallelChildren=1, diagnosticScope="pinned-custody-metadata-preparation",
                      corpusAcceptanceEstablished=False, countryCoverageComplete=False,
                      candidateGenerationEnabled=False, safeToAcquireEstablished=False,
                      networkAcquisitionEnabled=False)
    if request["profile"] == "offline-reconciliation":
        report.update(maximumParallelChildren=1, diagnosticScope="fixed-path-offline-metadata-observations",
                      corpusAcceptanceEstablished=False, countryCoverageComplete=False,
                      candidateGenerationEnabled=False, nativeProcessesObserved=False,
                      safeToAcquireEstablished=False)
    if request["profile"] == "global-readiness":
        report.update(maximumParallelChildren=2, diagnosticScope="fixed-scope-offline-global-readiness",
                      corpusAcceptanceEstablished=False, countryCoverageComplete=False,
                      candidateGenerationEnabled=False)
    if request["profile"] == "national-schema-survey":
        report.update(diagnosticScope="selected-no-fr-schema-and-dictionaries",
                      corpusAcceptanceEstablished=False, candidateGenerationEnabled=False,
                      sourceContentsUploaded=False, structuralDictionaryLabelsIncluded=True)
    if request['profile'] == 'ciqual-source-native':
        report.update(candidateGenerationEnabled=True, corpusAcceptanceEstablished=False,
                      sourceContentsUploaded=False, externalPublication=False,
                      countryCoverageComplete=False, candidateScope='private-source-native')
    return report


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
            if receipt.stat().st_size > report_limit(request):
                raise JobError("previous-receipt-invalid")
            previous = json.loads(receipt.read_bytes())
            if previous.get("requestIdentity") != identity:
                raise JobError("job-id-reused-for-different-request")
            if previous.get("status") in {"passed", "failed", "cancelled", "incomplete"}:
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
    CANCEL_EVENT.clear()
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


