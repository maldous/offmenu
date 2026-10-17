#!/usr/bin/env python3
"""Measure native-fault recurrence at the repair-preflight JSON parse site.

2026-10-15 incident: ``Segmentation fault`` in the C JSON scanner
(``json/decoder.py:353 raw_decode`` <- ``representative_checks`` line 182
``packet = json.loads(line)``).  Root cause unproven; hypothesis is host-level
C-runtime instability (leading candidate: unregistered RAM fault) versus a rare
CPython 3.12.3 C-scanner defect.

This harness runs the same workload (``json.loads`` over every line of a gzip
member) in fresh subprocesses and reports the fault rate.  Scope is deliberately
bounded: only the named small retained assets are read (read-only), nothing is
written outside stdout, and no full-corpus scan is performed.  On an abnormal
child exit, stdout markers localize the faulting file; row-level bisection is a
documented follow-up only if a fault reproduces.

Output: one JSON report on stdout.
"""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path


CHILD = """
import gzip, hashlib, json, sys
report = {}
for path in sys.argv[1:]:
    count = 0
    digest = hashlib.sha256()
    with gzip.open(path, "rb") as handle:
        for line in handle:
            json.loads(line)
            digest.update(line)
            count += 1
    report[path] = {"lines": count, "sha256": digest.hexdigest()}
    print(f"OK {path} {count}", flush=True)
print("RESULT " + json.dumps(report, sort_keys=True))
"""

DEFAULT_ASSETS = [
    "packets/part-00000.jsonl.gz",
    "packets/part-00244.jsonl.gz",
    "packets/part-00413.jsonl.gz",
]


def snapshot_proc(pid):
    """Best-effort read-only /proc snapshot of a stalled child (watchdog)."""
    import os
    snapshot = {}
    for name in ("status", "stat", "wchan", "io", "cmdline"):
        try:
            snapshot[name] = Path(f"/proc/{pid}/{name}").read_text()[:2000]
        except OSError as error:
            snapshot[name] = f"(unreadable: {error})"
    try:
        snapshot["taskStates"] = {
            task: Path(f"/proc/{pid}/task/{task}/stat").read_text().split(") ")[-1].split()[0]
            for task in os.listdir(f"/proc/{pid}/task")
        }
    except OSError as error:
        snapshot["taskStates"] = f"(unreadable: {error})"
    return snapshot


def run_once(assets, timeout):
    started = time.monotonic()
    child = subprocess.Popen(
        [sys.executable, "-c", CHILD, *(str(item) for item in assets)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    timed_out = False
    stall_snapshot = None
    try:
        stdout, stderr = child.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        stall_snapshot = snapshot_proc(child.pid)
        child.kill()
        stdout, stderr = child.communicate()
    elapsed = time.monotonic() - started
    completed = []
    result = None
    for line in stdout.splitlines():
        if line.startswith("OK "):
            completed.append(line.split()[1])
        elif line.startswith("RESULT "):
            result = line[len("RESULT "):]
    faulting_file = None
    exit_code = 124 if timed_out else child.returncode
    if exit_code != 0 and completed != [str(item) for item in assets]:
        pending = [str(item) for item in assets if str(item) not in completed]
        faulting_file = pending[0] if pending else None
    return {
        "exitCode": exit_code,
        "signal": -child.returncode if (not timed_out and child.returncode < 0) else None,
        "timedOut": timed_out,
        "stallSnapshot": stall_snapshot,
        "elapsedSeconds": round(elapsed, 3),
        "completedFiles": completed,
        "faultingFile": faulting_file,
        "stderrTail": stderr[-400:] or None,
        "result": result,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path,
                        default=Path("/home/user/src/offmenu-data/common-bulk-food-20261014"))
    parser.add_argument("--asset", action="append", dest="assets", default=None,
                        help="Input-relative .jsonl.gz asset (repeatable); defaults to the three retained diagnosis assets")
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument("--per-run-timeout", type=int, default=120)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be positive")
    assets = [args.input / key for key in (args.assets or DEFAULT_ASSETS)]
    for asset in assets:
        if not asset.is_file():
            parser.error("asset not found: " + str(asset))
        if not asset.resolve().is_relative_to(args.input.resolve()):
            parser.error("asset escapes input root: " + str(asset))
    runs = []
    for _ in range(args.runs):
        runs.append(run_once(assets, args.per_run_timeout))
        if runs[-1]["exitCode"] != 0:
            break  # Stop at the first fault; localization beats volume.
    abnormal = [item for item in runs if item["exitCode"] != 0]
    results = {item["result"] for item in runs if item["result"] is not None}
    report = {
        "schemaVersion": "offmenu-representative-faultrate-report/1",
        "scope": "small retained assets only; read-only; no full-corpus scan",
        "assets": [str(item) for item in assets],
        "runsRequested": args.runs,
        "runsCompleted": len(runs),
        "abnormalRuns": len(abnormal),
        "faultRate": f"{len(abnormal)}/{len(runs)}",
        "identicalResults": len(results) == 1 and len(abnormal) == 0,
        "firstAbnormal": abnormal[0] if abnormal else None,
        "env": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "runs": runs,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
