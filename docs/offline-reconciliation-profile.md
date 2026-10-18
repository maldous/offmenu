# Fixed offline reconciliation observations

Prepared 2026-10-18. Source base: `5cfb4f7d4346b06d58b82ec7d3e2c8dd5d5fedb3`. Control base: `160bd4db49faa46636fd27d70cc3d65557f5f2fb`.

## Execution contract

The existing runner accepts the same exact three-field request: `schemaVersion`, `jobId`, `profile`. This addition allowlists `offline-reconciliation`, with fixed steps:

1. readiness
2. reconciliation-tests
3. source-claims
4. transfer-receipts
5. native-continuity
6. disk-reservations
7. pending-ownership

Every observation depends only on readiness and the focused fixtures, so an inaccessible source does not suppress other observations. Execution is serial and uses the existing dispatcher kernel lock and receipt/idempotency rules. No coordinator, service, schedule, credential, filesystem grant, mount, or permission change is added. All paths and modes are code constants; requests cannot choose commands, paths, roots, network targets, or concurrency.

The observation script only reads exact registered metadata files and `statvfs` observations for the existing cache/output roots plus the exact native originals root. It does not list any originals/worker-receipts directory, read source dataset bodies, discover unknown claim paths, inspect or control native processes, start acquisition, claim ownership, or repair a ledger. The existing dispatcher still writes its own normal bounded job receipt. Native `latest-session-receipt.json` and legacy `latest-receipt.json` remain distinct; this script writes neither.

## Exact current registration

- Native ledger handover and bounded events tail: `/home/user/Documents/Codex/2026-10-13/task-3/permanent-ledger/{handover.json,events.jsonl}`
- Operating entrypoint: `/home/user/Documents/Codex/2026-10-13/task-3/OFFMENU-OPERATING-ENTRYPOINT.md`, metadata/stat only
- Worker 57 reconciliation: `/home/user/Documents/Codex/2026-10-18/country-collection-inventory/worker57/final-cut8822-reconciliation/result.json`
- Worker 57 refill metadata: `/home/user/Documents/Codex/2026-10-18/country-collection-inventory/worker57/later-next-eleven-refill-packets/eleven-packet-summary.json`
- Owner 31 hold-summary path: `/home/user/Documents/Codex/2026-10-18/country-collection-inventory/worker57/owner31-source-use-incident-retained/hold-propagation-result.json`, metadata/stat only. No restricted raw or derivative files are touched.
- PH20 partial-transfer recovery metadata: `/home/user/Documents/Codex/2026-10-18/worker64-acquisition-continuity/next-real-continuation-foodblog-20261018/actual8805-current-recovery.json`
- Capacity only: `/srv/offmenu-refresh/cache`, `/srv/offmenu-refresh/outputs`, `/home/user/src/offmenu-data/originals`

These exact names were supplied by current cutover evidence. Their registration is not evidence the runner can access them. The cloud fixtures do not prove Foo permissions. Unknown source-claim, transfer-receipt catalog, full reservation-register and worker-receipts-root paths remain unknown. The single PH20 recovery file does not establish transfer-catalog coverage. A registration flag means only that that mode has exact named metadata inputs, not that its worldwide/native scope is fully registered.

The source-claims step is explicitly unregistered. The disk-reservations step observes actual accessible capacity but remains blocked because the authoritative reservation path is unregistered. No available-space figure is reduced by guessed reservations or presented as acquisition headroom.

## Bounded evidence and interpretation

Each file is capped at 2 MiB. Oversized JSON is reported as blocked. JSONL can read only the last 2 MiB and last 5,000 complete rows; sampling is explicit and does not establish whole-ledger state. Parsing is bounded to 50,000 nodes and 24 nesting levels. Symlink components, nonregular files, changing files, malformed/duplicate-key JSON, and unavailable paths are rejected. Access error text is a fixed enum; the only published paths are exact reviewed constants.

Reports contain file sizes/timestamps, metadata-only SHA-256 with explicit whole-file/tail scope, and counts projected from fixed field/key/value allowlists. Reservation-field counts/sums are raw observations that may contain duplicates; they are never authoritative reservations. State/owner field counts are observations, not deduplicated current claims, active native workers, or assigned ownership. A recent event or report never proves native execution or successor pickup. Mtime never proves acquisition freshness. Raw metadata bodies, arbitrary keys/values, URLs, logs, filenames discovered at runtime, credentials, and dataset contents never enter the report.

A mode exits 0 only for complete observations of its registered files; it exits 2 for missing/unregistered/inaccessible/partial metadata. The dispatcher preserves each step's exit code and translates valid exit-2 reports to blocked. The overall job stays incomplete if any observation is blocked. `nativeProcessesObserved`, `safeToAcquireEstablished`, `reservationTotalsAuthoritative`, `ownershipEstablished`, and source-content-upload flags remain false. An observation succeeding does not authorize acquisition or release existing ownership/holds. In particular, PH8485 and the conservative 160 MiB PH20 reservation remain unchanged; no resume or source GET is added.

The existing hosted publisher keeps its strict projection: only validated step identities/status/exit/duration go into the small legacy completion receipt. The bounded sanitized per-step evidence remains in the source Actions report/log. No arbitrary child evidence is copied to the results branch. Reviewers/parent must inspect that source report for access findings. Use a fresh job ID; reused local receipts remain bound to their originating run.

## Validation and rollout

Focused fixture command: `python3 -B -m unittest discover -s tests -p test_offline_reconciliation.py -v`.

Fixtures cover exact request and command allowlists; no reads for unregistered scopes; no source mutation; metadata-only no-body access; symlink and FIFO rejection; missing/permission errors; size, tail, row, node and race bounds; secret/key/value projection; schema/flag spoof rejection; and independent blocked-step continuation.

Source publication consists only of the new script, dispatcher change, focused test, and this document. The separate control overlay changes the profile-choice and three embedded publisher allowlists, then requires both trusted-source pins to be set to the reviewed source commit. Request submission remains a separate root-owned action. No dispatch occurred while preparing this bundle. Existing readiness/replay/acquisition behavior is unchanged.
