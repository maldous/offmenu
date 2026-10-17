# Worker 12 preview-contract correction review

Date:2026-10-14, Australia/Melbourne. Same existing review; original f77 evidence preserved. **Original P12-01/P12-02 reproducers now refuse, but two qualification-admission gaps remain. Corrections required before Worker58 state-writing admission.** Morgan owns final disposition. No process administration or combined/auth/provider acceptance issued.

Previous producer `f77bfafb4672e5e0660f1f66efbec0502ec493a8`; corrected `2fd7db9e54dc93752f4973556bdbb59507f82118`. Exact Git binary delta SHA256 `2410f198cade80376678e5bcdc757c0eefa326f01abaca200bed4f9e087e0e6a`, retained correction.diff. Three changed files: interactive-preview.mjs, receipt-binding tests and owned contract documentation. Selected source hashes in source-hashes.json, confirmed identical to immutable Git bytes and unchanged through execution. Tests/read-only imports reference those pinned unchanged source files; all mutated receipt/descriptor fixtures are disposable /tmp files. No author writes.

## Original resolutions

P12-01: registered root source/grant text/action set now checked separately from bound session/root/input/artifact/control claims. Original unrelated-task + empty grant + real-provider-action fixture now refuses. Individual grant source/text/duplicate/expanded/empty action negatives pass in owner's focused suite. This is a task binding check, not cryptographic or human-approval proof.

P12-02: original before-process timestamp / false version / zero JAR and runtime hashes fixture now refuses. Wrapper/native custody equality, JAR bytes/lock/version, runtime/source hash, kernel process birth/actual cwd, reset/audit hashes and qualification chronology are now enforced. Owner's individual future/expired/dependency/native/reset contradictions also refuse. Present execution evidence binds validator/source/process and actual recorded results. Its absence and descriptor timestamp still need the following corrections.

## Remaining findings

**P12-03 — P2 / medium: actual execution evidence can be omitted.** Corrected interactive-preview.mjs:41 guards execution validation with `if(r.executionEvidence)`. From the supplied new qualification packet, delete only executionEvidence, preserve custody/reset/audit/declared result fields, rehash the qualification and descriptor. `loadInteractive` still admits. Independent observation missing-actual-execution-record-still-admitted is true in producer-boundary-probes.json/.mjs.

Impact: the new admission path can accept declared176+2 result semantics without the newly introduced preserved Identity execution record/validator binding. The supplied real packet does contain and match that evidence; the finding concerns fail-closed enforcement, not a claim its current tests were fabricated.

Advice: require execution evidence for new/state-writing admission. If legacy packet compatibility is deliberate, make its inspection mode explicit and prevent that mode from returning a qualified adapter for58. Preserve original receipts without rewriting/relabeling them; add missing execution-reference rejection and actual new packet positive.

**P12-04 — P2 / medium: descriptor qualification chronology remains unchecked.** Corrected interactive-preview.mjs:120–124 parses/binds descriptor but never validates d.qualifiedAt; validateQualification checks only mock receipt chronology. Rehash the new descriptor with qualifiedAt2099-01-01 or2000-01-01, keeping its current valid mock receipt. Both admit. Independent observations future-descriptor-time-still-admitted and descriptor-before-mock-qualification-still-admitted reproduce this.

Impact: internally impossible/future descriptor qualification claims pass despite the requested mock-start ≤ qualification ≤ descriptor ≤ current-time invariant. Native process identity still matches; this is an evidence-integrity/admission gap, not a changed runtime or invented need for a TTL.

Advice: require finite descriptor time at or after mock qualification and not later than current time plus an explicitly documented clock tolerance. Keep explicit expiry checking and lifetime-bound process identity separate. Add absent/invalid/future/before-mock negatives and current packet positive.

## Actually-run proof

- Owner focused tests at corrected pin: **7/7 pass**, focused-tests.log; command `node --test tests-dev/interactive-preview.test.mjs tests-dev/receipt-binding.test.mjs`.
- Reviewer boundary observations: **10/10 expected observations confirmed**, producer-boundary-probes.mjs/.json/.log. Original grant/dependency reproducers now refuse; current packet admits; owner/session/composition/stopped negatives refuse; the two remaining findings deliberately reproduce acceptance. A passing observation test is not a waiver of those gaps.
- New runtime readback: runtime-readback.json. Java PID883005/loopback19076 and preview PID883879/loopback18796 boot/birth/actual cwd/command matched their current native/ready receipts. Preview sourceCommit is exactly2fd7db9e, not f77. Health and /__dev/status GETs matched identity; no token retained.
- New descriptor SHA256 `38a042e49a39b3b5c22c5b2be035aedc9a9477770348d12776e0140e71129574`; qualification SHA256 `45ae5357b45958f5ea1a517f501a3b9125184819438310fdcb5d5aa8d7e56397` match supplied pins. Execution-record SHA256 `1020430d071de852919231fce08d9eb77fe7a3f1a2c8b28d0cc176fbe12232c3` and reset/audit/JAR hashes independently match referenced bytes. Owner corrected-readback.json SHA256 b8db56ce149aef6df95b12e852b5123bc1fa70b3a5e0053416d87227a6667690 verified.
- Input packet4eb72d2450c472815d8d96dc5e3f24611c31bd86ee0528358f4d80ff3181452b and app artifact608a82b8a4010fa1b5781c8966a240b25a2f2bb4e4d1d6ca41d9e708d627e0d2 unchanged. Actual source owner06/provenance pin9b31f7d remains distinct from process owner05.

Actual176 Identity +2 reset assertions are producer-recorded execution evidence, not rerun by reviewer. All reviewer network activity was existing loopback health/status GETs; no auth/state/reset/admin lifecycle operation, fake-provider flow pass or server start/stop. Original f77 app729700/Java695978 receipts and processes were neither relabelled nor administered.

## Custody / next step

Source and test processes strip inherited GIT_*; no Git-writing fixture or shared ref write. Own branch/HEAD/index and primary main/HEAD/index stable; original review artifact hashes verified unchanged. Local develop before/after separately retained to distinguish concurrent owner movement. No tracked owner/reviewer source changes, new branch/worktree/agent/session or settings/security/Actions/publication performed. Mandatory auto_review remains; actual filesystem unrestricted and network enabled, separate policy/profile unavailable.

For05: address only P12-03 execution-reference requirement/mode and P12-04 descriptor time ordering, preserve both runtime generations, return new immutable pin and exact packet-scope statement. A changed admission source is not automatically loaded into an existing process. For58: retain the state-write hold; exact paired admission/re-review and per-request custody remains required. No duplicate producer176+2 rerun is requested merely to repair validation of existing immutable evidence; any new execution must remain labelled with its actual loaded source/process.

Ready for Morgan review of these precise findings. Messaging remains pending direct human authorization already requested; this retained report is the concrete communication payload. Same Worker12 remains available for exact follow-through.
