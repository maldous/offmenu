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
   proves `verify_input` had completed (all listed input entries hash-verified
   that run) before the fault hit during representative scanning.  The
   9,797-asset figure is **source-pinned** to the authoritative input manifest
   `/home/user/src/offmenu-data/common-bulk-food-20261014/manifest.json`:
   9,797 `.jsonl.gz` packet assets plus 3 auxiliary JSON entries
   (`schema.json`, `contract.json`, `source-mappings.json`) = 9,800 `files`
   entries that `verify_input` verifies (review finding M2).

## Evidence (paths and findings)

- `/home/user/src/offmenu-data/logs/bulkfood-semantic-recovery-20261015.log` —
  fatal stacks for incidents 1 and 3.
- `/home/user/src/offmenu-data/logs/repair-hang-evidence-20261015.json` —
  incident 2 hang evidence (full retained path; review finding M3).
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
= **92/92 OK** (exit 0) under a dependency venv at `/tmp/offmenu-w62-testvenv`
with the pyproject-pinned test extras (system Python is PEP 668 externally
managed; the 12 loader errors under system Python are missing optional extras
`jsonschema_rs`/`openpyxl`/`mwparserfromhell`, pre-existing and unrelated).
**Checkout layout requirement (review finding M1):** the pinned script's
`checkpoint_pins()` reads `corpus/common-data.schema.json` and
`corpus/common-data-contract.json` from the checkout root
(`Path(__file__).resolve().parents[1]`), so the committed suite passes only in
a complete-layout checkout that contains `corpus/` beside `scripts/` — the
venv supplies dependencies only, not layout; a scripts-only clone is not a
valid test host without materializing those corpus pins.

## Fault-rate reproduction results (2026-10-15, same stage)

Harness `scripts/diagnose-representative-faultrate-20261015.py` (watchdog-hardened:
abnormal child exits are recorded; stalls are recorded as timeout runs with a
read-only `/proc` snapshot before the child is killed).  All runs parse the
three small retained assets only — read-only, no full-corpus scan, no bulk
output.

- Batch 1 (30 fresh processes × 3,000 lines): **0/30 faults**, identical
  results (90,000 clean parses).  The raw batch-1 report file was overwritten
  by the failed batch-2 run and is **not preserved**; the result survives in
  the stage receipt and session transcript only.
- Batch 2 (500 requested): one child **stalled ≥120 s on a 0.17 s workload**
  (hang signature — recorded as a separate observation from the SIGSEGV, not
  conflated); the un-hardened harness then crashed on the unhandled timeout
  (harness defect, fixed).  System load 0.50 / MemAvailable 41 GB at the time
  → not CPU or memory contention.
- Batch 3 (300 fresh processes): **fault reproduced** — run 235 died with
  **SIGSEGV (exit −11)** while parsing `part-00413.jsonl.gz`, after the same
  bytes had parsed clean in the other 234 fresh processes.  Stochastic fault
  rate ≈ **1/235 fresh processes** (~705,000 line parses); a deterministic
  data trigger is ruled out at run level.
- Kernel correlation: `14:43:57 python3[2456598]: segfault at 2332 ip
  0000000000586d84 error 4 … likely on CPU 10 (core 20, socket 0)` — **same
  instruction pointer** as the 14:15:00 fault (`segfault at 4489 ip …586d84`),
  and **all five** of the day's python3.12 C-level faults report "likely on CPU
  10 (core 20)" (03:30 basic-memory, 04:12 python3, 09:51 basic-memory, 14:15
  python3, 14:43 harness child; the 10:23 repair GPF did not report a CPU).
- CPU-pinned comparison — **interpretation corrected 2026-10-15 per
  containment instruction**: `taskset -c 10` → 0/300 and `taskset -c 11` →
  0/300 were **both executed on the suspect physical core 20** (CPUs 10 and 11
  are SMT siblings of core 20, socket 0), so the run labeled "control" was an
  **invalid control**.  Both results are preserved as observations but can
  neither confirm nor refute the core-20 localization.  The valid design
  (suspect core vs a different physical core) was queued as
  `27a68576-8390-4df3-8579-a1b07f050824` and **withdrawn before pickup** under
  the containment instruction — do not run it.

Hypothesis status updated: native-fault recurrence at the crash workload is
now **observed** (stochastic, not deterministic).  Leading hypothesis remains
a hardware fault (core-20 localization suggested by the kernel reports but not
confirmed by the pinned comparison); a fixed-IP defect in CPython 3.12.3
(same crash IP `…586d84` twice) remains a live alternative.  **Still no fix
invented** — the pinned implementation is unchanged.

## Bounded next tests (status after the reproduction results)

1. ~~Repeated-subprocess fault-rate loop~~ — **EXECUTED** (above): fault
   reproduced at ≈1/235 processes on `part-00413.jsonl.gz`.  Row-level
   localization is a repeated-parse bisect of that file only (the fault is
   stochastic, so a single triggering row is not assumed).
2. Bounded non-destructive memory-health check to test the hardware hypothesis
   (proper RAM testing needs a non-installed tool or a reboot — gate noted).
   CPU-pinned fault-rate comparisons against the suspect core are withdrawn;
   any future diagnosis runs only on currently online CPUs.
3. Repair relaunch remains gated: if resumed, run on online CPUs under a
   watchdog that snapshots `/proc` on freeze/crash (the harness demonstrates
   the pattern) to a fresh output root with Morgan's explicit go; the pinned
   implementation's per-asset checkpoint journal already bounds loss to one
   asset and supports `--resume` once the first checkpoint exists.

## Precautionary runtime containment (2026-10-15, authoritative instruction)

At Matt's explicit request, logical CPUs **10 and 11** (SMT siblings of
physical core 20, socket 0) are **offline** via supported Linux CPU hotplug;
the online list is `0-9,12-31` (verified read-only:
`/sys/devices/system/cpu/online`, `cpu10/online=0`, `cpu11/online=0`).
Constrains for all subsequent work:

- no further tests on the excluded/suspect core; no re-enabling cores; no
  global settings changes;
- the queued CPU10-vs-CPU12 comparison (`27a68576-8390-4df3-8579-a1b07f050824`)
  is withdrawn — not to be picked up;
- existing observations are preserved unchanged; only their interpretation is
  corrected (see the CPU-pinned comparison bullet above);
- this is **precautionary containment, NOT proven hardware failure** — the
  hypothesis remains unproven either way;
- no confidence-only fault-rate batches: further batches must answer a
  decision-driving question or not run.

Containment-aware relaunch posture (for Morgan's verdict): any repair relaunch
runs on online CPUs to a fresh output root under the `/proc` watchdog; the
pinned per-asset checkpoint journal bounds a stochastic fault to one asset and
`--resume` continues from it; orphaned-lock custody must be decided first.

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
