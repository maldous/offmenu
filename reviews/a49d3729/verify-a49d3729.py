#!/usr/bin/env python3
"""
Deterministic read-only verifier for the independent exact review of Worker05
commit a49d3729fb86db4de79b16e5fb968090a1de88e0
(MORGAN-BOUNDED-SEMANTIC-EXACT-REVIEW-YIELD-20261015-W06, Task 2).

Commit: "Apply review M1-M3: pin layout note, source-pinned asset count, exact log path"
Branch: bugfix/62/freebuff-repair-diagnosis-20261015 (slot62, canonical repo read-only).
Parent: 72d4a09438ec72793c739625ad2d2b2127e1f3c8 (whose doc blob equals 5d8b24e's).

Reproduces the checkable claims of the M1/M2/M3 corrections and the incident
disclosures.  It runs NO fault-rate batch, no suspect-core probe and no
containment change; the only execution is one bounded 1000-line JSON parse per
named retained fixture in a fresh interpreter (explicitly in review scope:
"bounded metadata/necessary small fixtures only").  Exit 0 when every claim holds.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/user/src/offmenu")
COMMIT = "a49d3729fb86db4de79b16e5fb968090a1de88e0"
PARENT = "72d4a09438ec72793c739625ad2d2b2127e1f3c8"
CHAIN_PRIOR = "5d8b24e"  # resolved to its full SHA by git at runtime
DOC = "docs/repair-diagnosis-20261015.md"
KNOWN_LATER = "53e4b34"  # repair-subset builder; deferred review target, not reviewed here
DOC_FILE_SHA = "d089a910dac5f4719a7201cbed9c8fff5bfd486aa532c906ebaa61b255829ae5"
INPUT_ROOT = Path("/home/user/src/offmenu-data/common-bulk-food-20261014")
HANG_EVIDENCE = Path("/home/user/src/offmenu-data/logs/repair-hang-evidence-20261015.json")
LOCK = Path("/home/user/src/offmenu-data/common-bulk-food-semantic-final-recovery-20261015.repair.lock")
LOCK_RECONCILED = Path(str(LOCK) + ".reconciled-20261015T013540Z")
OUTPUT_DIR = Path("/home/user/src/offmenu-data/common-bulk-food-semantic-final-recovery-20261015")
FIXTURES = ("part-00000.jsonl.gz", "part-00244.jsonl.gz", "part-00413.jsonl.gz")

OUTCOMES = []


def record(label: str, ok: bool, detail: str) -> None:
    OUTCOMES.append((label, ok, detail))


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args],
                          capture_output=True, text=True, check=True).stdout.strip()


def git_show(rev: str, path: str) -> bytes:
    return subprocess.run(["git", "-C", str(REPO), "show", f"{rev}:{path}"],
                          capture_output=True, check=True).stdout


CHILD = ("import gzip,json,sys\nn=0\nwith gzip.open(sys.argv[1],'rt') as h:\n"
         "    for i,l in enumerate(h):\n        if i>=1000: break\n        json.loads(l); n+=1\n"
         "print('OK',n)")


def main() -> int:
    # 0. commit identity / exact bytes
    full = git("rev-parse", COMMIT)
    parent = git("rev-parse", f"{COMMIT}^")
    record("commit_and_parent_exact", full == COMMIT and parent == PARENT, f"{full[:8]} <- {parent[:8]}")
    doc_bytes = git_show(COMMIT, DOC)
    record("doc_file_bytes_match_reviewed_copy",
           hashlib.sha256(doc_bytes).hexdigest() == DOC_FILE_SHA,
           hashlib.sha256(doc_bytes).hexdigest()[:16])
    changed = git("diff-tree", "--no-commit-id", "--name-only", "-r", COMMIT).split()
    record("delta_is_doc_only", changed == [DOC], "changed paths: " + (", ".join(changed) or "none"))
    # interposed coordinator commit did not touch the doc: parent doc blob == 5d8b24e doc blob
    record("interposed_commit_left_doc_untouched",
           git("rev-parse", f"{PARENT}:{DOC}") == git("rev-parse", f"{CHAIN_PRIOR}:{DOC}")
           and git("show", "--stat", "--format=", PARENT).strip().endswith("1 file changed, 201 insertions(+)"),
           f"doc blob unchanged through {PARENT[:8]}; that commit added the review verifier only")

    # 1. M1 — checkout-layout qualification, verified against the pinned script source
    src = git_show(COMMIT, "scripts/repair-bulk-controls-20261014.py").decode()
    lines = src.splitlines()
    pins_idx = next(i for i, l in enumerate(lines) if l.startswith("def checkpoint_pins"))
    body = lines[pins_idx:pins_idx + 8]
    record("M1_checkpoint_pins_reads_corpus_from_checkout_root",
           any("parents[1]" in l for l in body)
           and any('"corpus/common-data.schema.json"' in l for l in body)
           and any('"corpus/common-data-contract.json"' in l for l in body),
           f"checkpoint_pins at line {pins_idx + 1}: root=parents[1], both corpus pins read from it")
    record("M1_pinned_implementation_unchanged_at_commit",
           git("rev-parse", f"{COMMIT}:scripts/repair-bulk-controls-20261014.py") == "7403673ab33422ddf734f0b646e08927d14db837",
           "runtime blob == base 4693cbc3 blob")

    # 2. M2 — source-pinned asset count from the authoritative input manifest
    manifest = json.loads((INPUT_ROOT / "manifest.json").read_text())
    keys = [e["key"] for e in manifest["files"]]
    gz = [k for k in keys if k.endswith(".jsonl.gz")]
    aux = [k for k in keys if not k.endswith(".jsonl.gz")]
    record("M2_manifest_9800_equals_9797_gz_plus_3_aux",
           len(keys) == 9800 and len(gz) == 9797
           and aux == ["schema.json", "contract.json", "source-mappings.json"]
           and all(k.startswith("packets/") for k in gz),
           f"{len(keys)} files = {len(gz)} packets/*.jsonl.gz + {len(aux)} aux {aux}")

    # 3. M3 — full retained path for the hang evidence
    record("M3_hang_evidence_at_full_retained_path",
           HANG_EVIDENCE.is_file() and hashlib.sha256(HANG_EVIDENCE.read_bytes()).hexdigest().startswith("1ef540b0"),
           f"{HANG_EVIDENCE.name} sha256 1ef540b0… ({HANG_EVIDENCE.stat().st_size} B)")

    # 4. incident disclosures — kernel lines and their CPU attribution
    kern = Path("/var/log/kern.log").read_text(errors="replace")
    claimed = {
        "09:51:48 basic-memory segfault": any("09:51:48" in l and "basic-memory" in l and "segfault" in l for l in kern.splitlines()),
        "10:23:05 python general protection fault": any("10:23:05" in l and "general protection fault" in l and "python" in l for l in kern.splitlines()),
        "10:04:37 codebuff trap int3": any("10:04:37" in l and "trap int3" in l for l in kern.splitlines()),
    }
    record("incident_kernel_lines_present", all(claimed.values()), json.dumps(claimed))
    stamps = ("03:30", "04:12", "09:51", "14:15", "14:43")
    attributed = {ts: sum(1 for l in kern.splitlines() if f"2026-10-15T{ts}" in l and "CPU 10" in l) for ts in stamps}
    record("five_oct15_cpu10_attributed_faults",
           all(v == 1 for v in attributed.values()), json.dumps(attributed))
    record("no_mce_edac_error_entries",
           not any(("EDAC" in l or "Machine check" in l or "mce:" in l)
                   and "Ver:" not in l for l in kern.splitlines()),
           "only EDAC line is the driver version banner; zero memory-error report entries")

    # 5. orphaned-lock custody disclosure (left in place, not reclaimed)
    lock_txt = LOCK.read_text() if LOCK.is_file() else ""
    record("orphaned_lock_left_in_place_with_dead_owner",
           LOCK.is_file() and LOCK.stat().st_size == 174 and '"pid": 2423767' in lock_txt
           and LOCK_RECONCILED.is_file() and not OUTPUT_DIR.exists(),
           f"lock 174 B pid 2423767; reconciled sibling present; output dir absent (zero repair output)")

    # 6. bounded fixture claim: 1000/1000 clean parses per named retained asset, fresh interpreters
    fixture_results = {}
    for name in FIXTURES:
        asset = INPUT_ROOT / "packets" / name
        run = subprocess.run([sys.executable, "-c", CHILD, str(asset)], capture_output=True, text=True)
        fixture_results[name] = (run.returncode, run.stdout.strip())
    record("bounded_fixture_1000_lines_clean_each",
           all(rc == 0 and out == "OK 1000" for rc, out in fixture_results.values()),
           "; ".join(f"{k}={v[1] or v[0]}" for k, v in fixture_results.items()))

    # 7. custody honesty: later commits on the same branch exist and are NOT covered here
    tip = git("log", "-1", "--format=%h %s", "bugfix/62/freebuff-repair-diagnosis-20261015")
    later = git("log", "--format=%h", f"{COMMIT}..bugfix/62/freebuff-repair-diagnosis-20261015").split()
    record("later_commits_exist_and_are_not_covered",
           COMMIT[:8] not in tip and len(later) >= 2 and any(c.startswith(KNOWN_LATER[:7]) for c in later),
           f"branch tip {tip.split()[0]} {tip.split(' ',1)[1][:40]}; later: {' '.join(c[:8] for c in later)}")

    ok_all = all(ok for _, ok, _ in OUTCOMES)
    for label, ok, detail in OUTCOMES:
        print(f"{'MATCH' if ok else 'REVIEW-DEVIATION'}  {label}  {detail}")
    print("A49D3729_REVIEW_REPRODUCED" if ok_all else "DEVIATIONS_PRESENT")
    return 0 if ok_all else 2


if __name__ == "__main__":
    sys.exit(main())
