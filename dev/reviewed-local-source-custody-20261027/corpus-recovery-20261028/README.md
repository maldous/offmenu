# Corpus recovery custody — 2026-10-28

This additive custody snapshot preserves the reviewed restricted corpus-access installer, metadata/integrity probes, tests and sanitized results. It does not change the application, production deployment, datasets, credentials or workflows. No raw dataset rows, runtime logs, private keys or backup contents are included.

## Access outcome

The owner ran the exact reviewed combined installer, SHA256 `bd8a61898801bbc578f5ab782a0965ea539d93f074c580529b51e51825b7d004`, and reported successful installation: 4,513 inodes checked, 2,840 named read/read-traverse ACL changes, no write grants, owner changes or default-ACL changes. All ten approved read-only mounts passed the local sandbox check. Installed launcher SHA256: `93a8e8eeb65666d775caf45235d39d2d9695c33d25285948aeb4dff7be52b1c2`.

Actual Windmill worker verification then passed: [inventory run](https://windmill.aldous.info/run/01a18006-a398-b79c-4977-9cae7b11ae36?workspace=offmenu), exit 0 with cleanup verified. The eight directories and two receipts are accessible at `/offmenu-corpus`, read-only. `access/README.md` and `access/REVIEW.md` are retained preparation-time records; their pending-install statements are superseded by this outcome, not rewritten as if the review itself installed anything.

The installer is historical reproducible source, not a command to rerun on an already updated launcher. It deliberately requires the original exact launcher preimage. No new access is granted by this Git snapshot.

## Retained package verification

- Six manifests match the retained six-package proof, current schema/contract and expected mapping counts.
- All 1,661 declared assets match exact sizes and SHA256: 401,128,230 bytes, zero missing/mismatched assets. [Asset verification run](https://windmill.aldous.info/run/01a1800d-0be9-e74c-d700-8e56d04d7b88?workspace=offmenu).
- Existing assembler rules attribute 95,121 records across 17 of 22 mapping sources to those packages. Do not use the legacy core manifest's broad 22,574,292 field as the six-package proof's coverage.
- The five uncovered sources account for 22,479,269 planned records. Food and places retained outputs have no final manifests.
- A historical custody receipt is not proof of current host-process state. No old PID was resumed or killed.

These checks establish retained-byte custody and metadata consistency. They do not newly prove semantics, whole 22-source completion, all-eight-package qualification, public serving coverage or production readiness. The common-corpus expansion, current production foundation release and identity-only candidate remain separate contracts.

## Retained partial integrity outcome

The full bounded read-only scan attempted all 2,821 inventoried gzip candidates with zero skips in 192,486 ms. It verified gzip CRC/EOF, JSON/basic packet shape and stable byte hashes for 413 of 414 food files and all 2,407 places files. This counted 413,000 food packets and 2,407 places packets; packet granularity differs and neither count is a source-record claim. Original files were not modified.

Food `packets/part-00413.jsonl.gz` (741,421 bytes, SHA256 `9609e5728df5248926deabdea9424e764ff9b348866b27d224a1c1a121e03fc6`) has a confirmed gzip EOF error with stable metadata. It is retained, not deleted or silently adopted. The bulk checkpoint is absent. Detailed reports and terminal receipts are in `evidence/`. [Full scan run](https://windmill.aldous.info/run/01a1800f-9490-31d8-baf0-2a1a64742724?workspace=offmenu).

This supersedes the earlier 32-file sample for integrity coverage only. Full schema, source equivalence and release qualification remain false, including for the files that passed basic integrity. The execution exit code was zero because the diagnostic completed; it does not erase the reported bad file.

## Recovery/access boundary

At this snapshot, original bulk and curated places input directories and optional historical checkpoint/lock sidecars remain outside the installed scope. The owner approved the separate narrow read-only/ACL request at 2026-10-28 01:11:11 UTC, but the incremental access installation and worker verification are still pending. This snapshot includes no second installer and grants nothing beyond the installed eight directories and two receipts. Legacy partials cannot be blindly resumed or assigned fabricated checkpoints. Preserve them and use current producer contracts for source comparison and new run-owned outputs once prerequisites are established.

## Reproducibility and publication

The standalone installer is byte-for-byte the reviewed and owner-run artifact. Its support sources reproduce it with `python3 build.py` from `access/`. The portable custody copy of `test_combined.py` replaces only a temporary author-workspace scope-file locator with adjacent `approved-scope.json`; the fixture contains only the original exact ten approved paths. All 24 access tests and 11 probe tests passed in this copied layout. Cloud syscall fixtures use mapped UID1000; actual Foo UID985 behavior is established by the owner-run verification, not those fixtures.

Publication uses a Git tree/commit and non-forced expected-head update on `integration/reviewed-local-source-custody-20261027`. The two existing workflows were inspected: `foo-runner.yml` handles pushes only to `offmenu-runner-jobs` changing `.github/offmenu-runner/request.json`; `third-party-services.yml` is manual-only. Neither matches this custody-only integration-branch update. Workflow files are unchanged; no Actions run is dispatched or retried. The source manifest pins every included file except itself; a separate local publication receipt records the final commit and remote blob verification.
