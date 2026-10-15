# Repair-preflight incident diagnosis — 2026-10-15 (Worker 02)

Task branch: `bugfix/62/freebuff-repair-diagnosis-20261015` (base `4693cbc3fe17cdde2e292e6eb00cd83769ee45ae`).
Status: **diagnosis preserved, root cause UNPROVEN, no fix invented.** Zero repair
output exists. This record is the reviewable companion to
`tests/test_representative_preflight_determinism.py` (the deterministic small
reproducer landed with it).

## Incident triage — three distinct incidents, not conflated

1. **Wrapper `NameError` (`types` / `__file__`)** — historical wrapper bugs in
   `<stdin>`-exec'd drivers (recovery log lines 1–57), long resolved, irrelevant
   to the pinned script.
2. **Userspace hang, PID 2381191** (01:0x–01:35Z) — frozen `rchar`, pure userspace
   spin; evidence-anchored recovery preserved in
   `repair-hang-evidence-20261015.json`.
3. **SIGSEGV in the C JSON scanner (the latest fatal stack)** — `Fatal Python
   error: Segmentation fault` at `json/decoder.py:353 raw_decode` ←
   `representative_checks` line 182 (`packet = json.loads(line)`), relaunched
   PID 2423767, 2026-10-15 12:43 local. **Not a JSONDecodeError.** The stack
   proves `verify_input` had completed (9,797 assets hash-verified that run)
   before the fault hit during representative scanning.

## Evidence (paths and findings)

- `/home/user/src/offmenu-data/logs/bulkfood-semantic-recovery-20261015.log` —
  fatal stacks for incidents 1 and 3.
- `repair-hang-evidence-20261015.json` — incident 2 hang evidence.
- Kernel log (read-only, 2026-10-15): `09:51:48 basic-memory[…]: segfault at ip
  0000000000000000 … in python3.12`; `10:23:05 python general protection fault …
  in python3.12`; `10:04:37 codebufffreebuff-desktop trap int3`; **zero**
  MCE/EDAC/memory-error entries.
- Bounded fixture parse (predecessor, fresh interpreters): part-00000,
  part-00244 (first-ever JSON parse of the hang-time file), part-00413 —
  **1000/1000 lines parse clean each**; the earlier "676 then truncated EOF"
  applies to the legacy *output* copy, a different file. No deterministic data
  trigger in bounded scope.
- Process/lock reconciliation (read-only, 2026-10-15, this stage): no repair
  process alive; orphaned
  `/home/user/src/offmenu-data/common-bulk-food-semantic-final-recovery-20261015.repair.lock`
  (174 B, dead owner PID 2423767) and its `.reconciled-20261015T013540Z`
  sibling **left in place** (no deletion, no signals); output directory absent
  → **zero repair output produced**.

## Hypothesis (preserved, NOT proven)

Host-level C-runtime instability — leading candidate an unregistered RAM fault;
alternative a rare CPython 3.12.3 C-scanner defect. Supporting: four independent
C-level anomalies across three processes in one day, one at a NULL instruction
pointer. Against a data trigger: all bounded retained fixtures parse clean in
fresh interpreters. **Per mandate, no fix was invented** while the root cause is
unproven; the pinned implementation `scripts/repair-bulk-controls-20261014.py`
is unchanged in this branch.

## What landed (reviewable, narrowest)

`tests/test_representative_preflight_determinism.py` — deterministic small
reproducer harness over a 3-file × 2-line retained temp fixture (a preamble row
exercises the full line scan at the exact crash site, line 182):

- `representative_checks` is byte-identical across 6 fresh interpreters;
- in-process and fresh-interpreter results agree;
- the real `verify_input → representative_checks → checkpoint` preflight path
  completes deterministically across 6 fresh interpreters (checkpoint
  `complete:true`, `representativePreflight` covers off/usda-files/prices,
  `inputAssetsVerified: 3`).

A recurrence of a native fault fails these tests loudly (non-zero subprocess
exit / signal) instead of being conflated with a data-format error.

Checks run: focused suites `tests.test_bulk_control_recovery` +
`tests.test_bulk_recovery_inspection` + `tests.test_representative_preflight_determinism`
= **17/17 OK** on the unchanged pinned script; full `unittest discover -s tests`
= **92/92 OK** (exit 0) under an isolated `/tmp/offmenu-w62-testvenv` with the
pyproject-pinned test extras (system Python is PEP 668 externally managed; the
12 loader errors under system Python are missing optional extras
`jsonschema_rs`/`openpyxl`/`mwparserfromhell`, pre-existing and unrelated).

## Bounded next tests (prepared, not executed this stage)

1. Repeated-subprocess `representative_checks` fault-rate loop over the real
   manifest *prefix only* (no full 9,797-asset scan) to measure fault rate and
   localize any triggering row; if found, pin its hash as a retained fixture.
2. Bounded non-destructive memory-health check to test the hardware hypothesis
   (proper RAM testing needs a non-installed tool or a reboot — gate noted).
3. If unreproducible, run the repair under a watchdog that snapshots `/proc` on
   freeze/crash.

## Pin custody (final verification, 2026-10-15)

The crashed run executed `/home/user/src/offmenu-freebuff/scripts/repair-bulk-controls-20261014.py`
(SHA-256 `6b547f82d6a3b6dbdc94f28d226d08f4df5a0dcef2122308e2c3be0c3284be14`),
which differs from this branch's copy (SHA-256
`2c025c07f0561d2ca0ac161778ca4ec98b0593b7c70b570ae53577a698c5bb4c`)
**only** in the `NEW_ROOT` default output path (line 22:
`…-semantic-final-recovery-20261015` vs `…-semantic-final-20261014`).  The
crash region `representative_checks` (lines 171–202, including line 182) is
byte-identical between the two copies.  The fatal stack cited above was
re-verified directly against `bulkfood-semantic-recovery-20261015.log` (log
lines 60–70: `Segmentation fault` ← `json/decoder.py:353 raw_decode` ←
`repair-bulk-controls-20261014.py:182 in representative_checks` ←
`repair_owned:300` ← `repair:271` ← `main:374`) in final checks.  No pin was
substituted; both hashes are recorded so neither copy is silently assumed to be
the other.

## Progress/DAG claim updates (this task branch; canonical DAG is in a read-only
checkout)

- `A2-bulk-food-repair`: **failed with SIGSEGV at preflight; 0 bytes output**;
  the earlier "running-verified-progress" claim (rchar ~23 MB/s) belongs to the
  *dead* PID 2423767 run and is superseded.
- Legacy 414-file partial: held (no pinned checkpoint; `--resume` refuses).
- Orphaned lock: custody unresolved — neither deleted nor reclaimed, awaiting an
  explicit custody decision (recorded in the stage receipt).
- Gates unchanged: repair package unproduced; independent review remains the
  acceptance gate for all peer-lane candidates.
