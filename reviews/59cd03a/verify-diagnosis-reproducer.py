#!/usr/bin/env python3
"""
Deterministic read-only verifier for the diagnosis/reproducer commit review:
  commit  59cd03a110b7a127179a0af53532cf91715d6ecb  (branch bugfix/62/freebuff-repair-diagnosis-20261015)
  base    4693cbc3fe17cdde2e292e6eb00cd83769ee45ae
Receipt: semantic/reviews/20261015-diagnosis-reproducer-review-W03.json

Runs only reads/fetches into a temp dir. Never touches Worker05's checkout,
never re-enables or probes the offline physical cores (10/11 offline by authority),
never runs assurance batches — only the one small committed focused test.

Checks:
 1. exact SHA resolves; parent == base; changed paths exactly as reviewed.
 2. runtime/contract unchanged: scripts/repair-bulk-controls-20261014.py blob
    identical between base tree and commit tree.
 3. doc/test byte pins (content sha256).
 4. log/hang-evidence/lock corroboration for the three-incident triage:
    SIGSEGV stack at json/decoder.py:353 <- representative_checks line 182,
    EXIT=139; hang evidence PID 2381191 + frozen rchar + part-00244 ruled out;
    orphaned lock 174 B, dead PID 2423767, reconciled sibling present.
 5. committed focused suite executed in the complete exact-SHA layout
    (script + corpus/common-data.schema.json + corpus/common-data-contract.json
    extracted from the commit tree) → 3/3 OK exit 0. Layout-coupling of
    checkpoint_pins is documented, not treated as a test defect.
 6. "no fix invented": diff of the commit vs base touches ONLY the two files.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path("/home/user/src/offmenu")
COMMIT = "59cd03a110b7a127179a0af53532cf91715d6ecb"
BASE = "4693cbc3fe17cdde2e292e6eb00cd83769ee45ae"

DOC_SHA = "a52c0f1cf3ca7971f2c02622250541f2d531d4376353f958a342f0f7c747878b"
TEST_SHA = "ec2bfd5917d0d9f743e8447a10ce8b42daaf8df45639a9bc6e27745d5c0c4b02"
CLUSIVE_FILE = "corpus/common-data-contract.json"
SCHEMA_FILE = "corpus/common-data.schema.json"

OUTCOMES: list[tuple[str, bool, str]] = []


def record(label: str, ok: bool, detail: str = "") -> bool:
    OUTCOMES.append((label, ok, detail))
    return ok


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True).stdout


def main() -> int:
    record("commit_resolves", git("rev-parse", COMMIT + "^{commit}").strip() == COMMIT, COMMIT[:16])
    record("parent_is_base", git("rev-parse", COMMIT + "^").strip() == BASE, BASE[:16])
    changed = [ln for ln in git("show", "--name-only", "--format=", COMMIT).splitlines() if ln.strip()]
    record("changed_paths_exactly_two_reviewed_files",
           sorted(changed) == ["docs/repair-diagnosis-20261015.md", "tests/test_representative_preflight_determinism.py"],
           str(changed))

    script = "scripts/repair-bulk-controls-20261014.py"
    record("runtime_blob_unchanged_base_vs_commit",
           git("rev-parse", BASE + ":" + script).strip() == git("rev-parse", COMMIT + ":" + script).strip(),
           "7403673a… IDENTICAL")

    with tempfile.TemporaryDirectory(prefix="w03-c59cd03a-") as td:
        tmp = Path(td)
        (tmp / "docs").mkdir(); (tmp / "tests").mkdir(); (tmp / "scripts").mkdir(); (tmp / "corpus").mkdir()
        doc_b = subprocess.run(["git", "-C", str(REPO), "show", f"{COMMIT}:docs/repair-diagnosis-20261015.md"], capture_output=True, check=True).stdout
        test_b = subprocess.run(["git", "-C", str(REPO), "show", f"{COMMIT}:tests/test_representative_preflight_determinism.py"], capture_output=True, check=True).stdout
        temp_b = subprocess.run(["git", "-C", str(REPO), "show", f"{COMMIT}:{SCHEMA_FILE}"], capture_output=True, check=True).stdout
        cont_b = subprocess.run(["git", "-C", str(REPO), "show", f"{COMMIT}:{CLUSIVE_FILE}"], capture_output=True, check=True).stdout
        script_b = subprocess.run(["git", "-C", str(REPO), "show", f"{COMMIT}:scripts/repair-bulk-controls-20261014.py"], capture_output=True, check=True).stdout
        record("script_content_sha_pinned", sha_bytes(script_b).startswith("2c025c07f056"), sha_bytes(script_b)[:12])
        record("doc_bytes_pinned", sha_bytes(doc_b) == DOC_SHA, DOC_SHA[:12])
        record("test_bytes_pinned", sha_bytes(test_b) == TEST_SHA, TEST_SHA[:12])
        record("contract_artifact_matches_semantic_line_pin", sha_bytes(cont_b) == "b4fa5afb2f8cc77326299b55ccd75b93f121e807317fdc1f9953709e98faa0aa", cont_b and hashlib.sha256(cont_b).hexdigest()[:12])
        (tmp / "scripts/repair-bulk-controls-20261014.py").write_bytes(script_b)
        (tmp / "docs/repair-diagnosis-20261015.md").write_bytes(doc_b)
        (tmp / "tests/test_representative_preflight_determinism.py").write_bytes(test_b)
        (tmp / SCHEMA_FILE).write_bytes(temp_b)
        (tmp / CLUSIVE_FILE).write_bytes(cont_b)

        # 4. evidence corroboration (retained, read-only)
        logp = Path("/home/user/src/offmenu-data/logs/bulkfood-semantic-recovery-20261015.log")
        log = logp.read_text(errors="replace")
        record("log_sigsegv_stack_corroborated",
               "Fatal Python error: Segmentation fault" in log and "json/decoder.py\", line 353 in raw_decode" in log
               and "line 182 in representative_checks" in log and "EXIT=139" in log,
               "lines ~60-66")
        hpath = Path("/home/user/src/offmenu-data/logs/repair-hang-evidence-20261015.json")
        h = json.loads(hpath.read_text())
        record("hang_evidence_pid_rchar_part244_corroborated",
               h.get("pid") == 2381191 and "rchar frozen at 14471614713" in h.get("diagnosis", "")
               and any("part-00244" in x for x in h.get("hypothesesRuledOut", [])),
               str(h.get("pid")))
        lock = Path("/home/user/src/offmenu-data/common-bulk-food-semantic-final-recovery-20261015.repair.lock")
        locktxt = lock.read_text(errors="replace") if lock.exists() else ""
        sib = Path(str(lock) + ".reconciled-20261015T013540Z")
        record("orphaned_lock_corroborated",
               lock.exists() and lock.stat().st_size == 174 and "2423767" in locktxt and sib.exists(),
               "174B dead pid 2423767; sibling left in place")

        # 5. focused suite under complete exact-SHA layout
        r = subprocess.run([sys.executable, str(tmp / "tests/test_representative_preflight_determinism.py")],
                           capture_output=True, text=True,
                           env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        combined = (r.stdout + r.stderr).splitlines()
        tail_lines = [ln for ln in combined if ln.strip()]
        record("focused_suite_3_of_3_ok_exit0",
               r.returncode == 0 and "Ran 3 tests" in r.stdout + r.stderr and tail_lines and tail_lines[-1].startswith("OK"),
               f"exit={r.returncode} tail={' | '.join(tail_lines[-2:])} stdout={r.stdout[-120:]!r} stderr={r.stderr[-160:]!r}")
        # 6. no fix invented — the two added files are the ONLY change (checked above);
        #    also assert the doc says the pinned script is unchanged
        record("doc_states_no_fix_invented", "no fix invented" in doc_b.decode("utf-8", "replace").lower(),
               "docs/repair-diagnosis-20261015.md")

    ok_all = all(ok for _, ok, _ in OUTCOMES)
    for label, ok, detail in OUTCOMES:
        print(f"{'MATCH' if ok else 'REVIEW-DEVIATION'}  {label}  {detail}")
    print("DIAGNOSIS_REVIEW_REPRODUCED" if ok_all else "DEVIATIONS_PRESENT")
    return 0 if ok_all else 2


if __name__ == "__main__":
    sys.exit(main())
