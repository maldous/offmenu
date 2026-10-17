# Worker 12 PDF-backed lifecycle review

Date:2026-10-15, Australia/Melbourne. **CORRECTIONS REQUIRED — one reproduced P2 command-identity defect.** Genuine owner-performed bounded lifecycle and supplementary preservation evidence retained. Completed434bindingPASS remains unchanged. Source transport remains ASSIGNED-WAITING, not implemented/accepted. Production STOP and whole105/source-admission holds remain.

## Immutable sources and evidence

Main source `606b231f68f18ec5920977323f6da61e84138365`, parent `5f5bdb6ae716cbf80fab1e174d1af2e354468ead`; binary Git diffSHA256 `65c5bfdaa08b7c37b90ea8ada09e6726b2ada5f538f27f6e5d9cab22a6639ac9`, candidate.diff. Five carried dev helper files independently byte-identical to selected434b56c, so old accepted434/be166 tests were not repeated. New source paths are worker05-lifecycle. Snapshot-manifest.json records immutable lease/test/dependency-reference files only; runner/qualify operations were not imported/executed.

Supplementary additive source `27169ac47167a456e6d0f46572af66500069d01e`, parent `606b231f68f18ec5920977323f6da61e84138365`; diffSHA256 `7403e57fd3dfc83364d607d5cfacc8651be4d3d533a757b4367f8bc1adfd7ee6`. Only preservation.mjs added;606 code unchanged. No supplementary operation rerun by reviewer.

Main owner result JSON53af5741ca421618cf78edc00e2814c8875ee47737e5bfda5e1bd254362f8b71 and supplementary c1d18f5afaf221429431d0eec55b6e688d1a879e4d5f6fee961faaa9642be4bf verified. The owner recorded44assertions/12HTTP, separate supplementary4HTTP. This review independently matched ready/stopped snapshots,11operation/stdout/snapshot refs, control-refusal/reset/stop payloads and distinct run/lease/state/birth. Both initial leases and the supplementary lease are stopped/exit0 and their PIDs absent;18809currently refuses readiness. Reviewer issued no process/state operation.

## Finding L12-01 — P2 / medium: runner path in any argument is accepted as executable identity

Location: candidate worker05-lifecycle/lease.mjs:11, reached by verifyControl at:15. It checks whether /proc/PID/cmdline includes the expected runner path, without requiring that path to be the actual Node entry point.

Actually-run isolated immutable-source reproducer: command-boundary-probe.mjs/.json/.log. This reviewer's own ordinary Node process runs a probe script from the disposable source snapshot and receives the expected runner path merely as an inert `--inert-runner-tag` argument. Actual argv[1] is the reviewer probe, not runner.mjs. A receipt constructed with the current own PID/boot/birth/cwd and correctly scoped fixture metadata is accepted by live verifyLease; verifyControl returns stop. No stop/reset/control was executed and no existing producer PID was targeted. Wrong birth and lease controls still refuse, proving this is specifically the command check.

Impact: the new ownership/admission helper can classify a non-runner as the disposable runner; it cannot substantiate actual runner-command custody from the current predicate. The observed606operations did run genuine runners; this defect concerns false admission for a different command, not an allegation of fabricated qualification or an actual wrong-process stop.

Advice: check the actual executable and script position matching the fixed spawn contract (`process.execPath`, absolute runner at argv[1]); if runtime options are allowed, parse their entry-point semantics explicitly. Do not use string membership anywhere in argv. Add this inert-argument negative plus actual runner positive. Carry original434 helper files unchanged; fix only the new lease/control path. No owner fix applied.

## Actually-run reviewer checks

- New lease.test.mjs only:1/1 focused test passed; no old434/be166 repeats.
- New live-command boundary probe reproduced false acceptance using only its own Node process; wrong-birth/wrong-lease negatives refused. No service/runtime launched.
- Immutable carried helpers compared and both owner packet hashes/operation refs inspected.
- Read-only feedback status/receipt identity and refused18809checked. No consumer/auth/state writes. Main/own/index and old review preservation captured separately.

The staged20-case harness remains available. Its local-normalization driver is not a claimed producer API. Actual606interfaces bound the focused command/lease cases directly. Restore-time withdrawal replay/full deletion and transport cases are unsupported lanes, not silently passed or treated as implemented by user_state reset. Source-policy/CAS/graph interfaces still require actual07 output and selected producer source before those cases can run.

## Preservation evidence and limits

Supplementary271 packet compares19receipt/durableSQLite-WALfiles,3002768bytes before/after; snapshots match exactly, -shm explicitly excluded and no raw data copied. Reviewer verified recorded equality and current path hashes:18/19match; the active feedback mainSQLite file now has a different digest from that historical snapshot. This later observation does not identify its actor/cause or invalidate the recorded before/after window; no continuous byte-preservation claim is made. Keep it distinct from immutable receipt/state evidence and legitimate live feedback changes.

Reset scope is only qualification-created user_state rows in an exclusive disposable D1. It is not a wholeD1/production deletion, backup replay or restore-policy implementation. PDF04pp2-5/7-9 and PDF02pp8-9 support authorization, scoped ownership, provenance/rights/clocks/withdrawal and restore constraints; original pages/hash refs are in the preserved readiness directory. These are design requirements, not current licence/privacy clearance. No corpus is admitted from starter records or this lifecycle proof.

Root/Morgan/05 should correct L12-01 and return the exact new lease pin for existing12/58 recheck.44+supplementary evidence can remain preserved; no request to replay unchanged accepted work or operate feedback/native processes.58state-writing admission for this new lifecycle source remains pending exact correction review. Original434bindingPASS is not withdrawn or widened.

Standing preservation checkpoint/backup outcome is recorded separately in checkpoint-preservation.json. No remote merge/release/publish or permission change is implied. Same Worker12 reserved; production STOP.
