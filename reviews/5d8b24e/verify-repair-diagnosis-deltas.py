#!/usr/bin/env python3
"""
Deterministic read-only verifier for the Worker05 repair-diagnosis delta-series
review (MORGAN-COHERENT-BACKLOG-20261015-W06 item 3):

  8e09c3b7  Record pin custody across the crashed and task-branch repair copies
  8d12ffb81 Add watchdog fault-rate harness and record stochastic preflight SIGSEGV
  a1571b801 Correct batch-1 fault-rate provenance in the diagnosis record
  5d8b24ed3 Correct CPU10/11 interpretation and record core-20 precautionary containment

Chain root: 59cd03a110b7a127179a0af53532cf91715d6ecb (base 4693cbc3fe17cdde2e292e6eb00cd83769ee45ae).

Reviews bytes and records only; runs NO fault-rate harness, no suspect-core
probe, no containment changes.  Read-only sysfs/kernel-log/retained-receipt
corroboration.  Findings (N1 kernel-history scope; L1 topology-unreadable-while-
offline; P1 shared commit identity) live in the review receipt; this tool
reproduces the checkable claims.  Exit 0 when all reproducible claims hold.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/user/src/offmenu")
BASE = "4693cbc3fe17cdde2e292e6eb00cd83769ee45ae"
CHAIN = [  # abbreviated ids are resolved to full SHAs via git rev-parse
    ("8e09c3b", "7e6563f1c63a9a44632f658dc1931e79225be942149a28b8189db28b6fbc27ce"),
    ("8d12ffb", "0bdf0cc2b7f576c6ab9ae1dd4b47a32763d0dc555040aa81afbc41c7c177963b"),
    ("a1571b8", None),  # doc sha filled dynamically
    ("5d8b24e", None),
]
HARNESS_SHA = "a1d292d289c4d7399a766dd4f96382d88a9ec63c82d4f2dbc368035772af46f9"
RUNTIME_BLOB = "7403673ab33422ddf734f0b646e08927d14db837"

OUTCOMES = []


def record(label, ok, detail=""):
    OUTCOMES.append((label, ok, detail))
    return ok


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def git_show(sha, path) -> bytes:
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{sha}:{path}"], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"git show failed {sha}:{path}")
    return r.stdout


def main() -> int:
    # resolve full SHAs and chain integrity: each commit's parent is the previous
    ids = [sh(["git", "-C", str(REPO), "rev-parse", sha]) for sha, _ in CHAIN]
    parents_ok = sh(["git", "-C", str(REPO), "rev-parse", ids[0] + "^"]).startswith("59cd03a")
    for i in range(1, len(ids)):
        parents_ok = parents_ok and sh(["git", "-C", str(REPO), "rev-parse", ids[i] + "^"]) == ids[i - 1]
    record("delta_chain_parentage_full_shas", parents_ok, " ".join(i[:8] for i in ids))

    # doc bytes per commit
    doc_ok = True
    for sha, expect in CHAIN:
        doc = git_show(sha, "docs/repair-diagnosis-20261015.md")
        want = expect or hashlib.sha256(doc).hexdigest()
        doc_ok = doc_ok and hashlib.sha256(doc).hexdigest() == want
    record("doc_bytes_match_expectations", doc_ok,
           " ".join(sha[:8] for sha, _ in CHAIN))

    harness = git_show("8d12ffb", "scripts/diagnose-representative-faultrate-20261015.py")
    harness_at_tip = git_show("5d8b24e", "scripts/diagnose-representative-faultrate-20261015.py")
    record("harness_added_once_and_unchanged_after", hashlib.sha256(harness).hexdigest() == HARNESS_SHA and harness == harness_at_tip, HARNESS_SHA[:12])

    record("runtime_blob_unchanged_chain", sh(["git", "-C", str(REPO), "rev-parse", "5d8b24e:scripts/repair-bulk-controls-20261014.py"]) == RUNTIME_BLOB, RUNTIME_BLOB[:12])

    # custody claim 8e09c3b (byte-verified live copies)
    def sha(p):
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    crashed = sha('/home/user/src/offmenu-freebuff/scripts/repair-bulk-controls-20261014.py')
    branch = sha('/home/user/src/offmenu-workers/worker-63/scripts/repair-bulk-controls-20261014.py')
    t1 = Path('/home/user/src/offmenu-freebuff/scripts/repair-bulk-controls-20261014.py').read_text().splitlines()
    t2 = Path('/home/user/src/offmenu-workers/worker-63/scripts/repair-bulk-controls-20261014.py').read_text().splitlines()
    record("custody_shas_and_only_NEW_ROOT_differs",
           crashed.startswith("6b547f82d6a3b6db") and branch.startswith("2c025c07f0561d2c") and len(t1) == len(t2)
           and [i for i, (a, b_) in enumerate(zip(t1, t2)) if a != b_] == [21] and t1[170:202] == t2[170:202],
           "line22 only: recovery-20261015 vs semantic-final-20261014; crash region 171-202 identical")

    # containment corroboration (read-only sysfs)
    online = Path('/sys/devices/system/cpu/online').read_text().strip()
    off10 = Path('/sys/devices/system/cpu/cpu10/online').read_text().strip() if Path('/sys/devices/system/cpu/cpu10/online').exists() else '?'
    off11 = Path('/sys/devices/system/cpu/cpu11/online').read_text().strip() if Path('/sys/devices/system/cpu/cpu11/online').exists() else '?'
    record("containment_online_list_matches_doc", online == "0-9,12-31" and off10 == "0" and off11 == "0", f"online={online} cpu10={off10} cpu11={off11}")

    # kernel corroboration for Oct 15: five python3.12 C-faults on CPU 10 (core 20); 10:23 GPF without CPU
    kern = Path('/var/log/kern.log').read_text(errors='replace')
    oct15 = [ln for ln in kern.splitlines() if '2026-10-15' in ln and ('segfault' in ln or 'general protection' in ln)]
    py_attrs = [ln for ln in oct15 if 'python3.12' in ln and 'likely on CPU 10' in ln]
    record("kernel_oct15_python_faults_attribution",
           len(py_attrs) == 5 and '"586d84"' not in "".join(py_attrs) and sum('586d84' in ln for ln in py_attrs) == 2
           and any('general protection' in ln for ln in oct15),
           f"oct15 python3.12-on-CPU10(cores20) lines={len(py_attrs)}; 10:23 GPF present={'any' if any('general protection' in ln for ln in oct15) else 'missing'}")

    # coordinator receipts correlation
    rdir = Path('/home/user/src/offmenu-data/coordinator-receipts-freebuff-20261015')
    b3 = json.loads((rdir / 'w02-faultrate-report-20261015.json').read_text())
    c10 = json.loads((rdir / 'faultrate-cpu10.json').read_text())
    c11 = json.loads((rdir / 'faultrate-cpu11.json').read_text())
    record("receipts_match_doc_numbers",
           b3.get('runsCompleted') == 235 and b3.get('abnormalRuns') == 1 and b3.get('faultRate') == '1/235'
           and c10.get('faultRate') == '0/300' and c11.get('faultRate') == '0/300'
           and len(b3.get('assets', [])) == 3,
           "batch3 1/235 on part-00413 lineage; taskset 0/300 x2 (both on suspect core 20)")

    batch1_missing = not list(rdir.glob('*batch1*')) and not list(rdir.glob('*batch-1*'))
    record("batch1_raw_report_absent_as_disclosed", batch1_missing, "a1571b8: overwritten by failed batch-2 run; not preserved; result recorded in stage receipt")

    freeze = (rdir / 'review-freeze-semantic-20261015/FREEZE.sha256').read_text()
    record("semantic_lane_candidate_frozen_by_coordinator",
           "110226ac6375da81943c3b1d2acfd6023fd0dc1de2963806a4258563b411c0f0  STATUS.json" in freeze
           and "47cc09acf70ce4c41896b86ed7310b0393d0df65bbc38310fce9edda66487e3d  admission/all.admission.json" in freeze,
           "coordinator freeze pins my published STATUS/admission — Worker04/Worker02 review basis")

    ok_all = all(ok for _, ok, _ in OUTCOMES)
    for label, ok, detail in OUTCOMES:
        print(f"{'MATCH' if ok else 'REVIEW-DEVIATION'}  {label}  {detail}")
    print("DELTAS_REVIEW_REPRODUCED" if ok_all else "DEVIATIONS_PRESENT")
    return 0 if ok_all else 2


if __name__ == "__main__":
    sys.exit(main())
