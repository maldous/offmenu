# Incremental input access: installation outcome

Snapshot 2026-10-28 01:22 UTC. This additive private-repository custody publication changes no application, dataset, deployment, credential or workflow.

## Approved and installed scope

The owner approved read-only access, including named read/traverse ACLs where needed, to the two exact input directories and six optional existing recovery files listed in `approved-input-scope.json`. The earlier eight corpus-package directories and two receipt mounts remain preserved. Neither the entire data root nor private-home contents are exposed.

At 01:21 UTC the owner reported successful execution of the reviewed installer, SHA256 `7a0754128163b1e560256d99b4fd01c90e7066f83290e600d73cfc7cf66c8e81`:

- 56,723 inodes checked.
- Zero new ACL changes were needed.
- 44,889 externally shared inodes remained untouched.
- Existing ten mounts preserved; two new required input directories mounted read-only, for twelve mounts total.
- All six optional recovery files were absent and were not created.
- Local sandbox verification passed.
- Installed launcher SHA256: `0a7dfb6fc964dafcec4403596060421910b79241fe01c50a6b2357a7b559928d`.

This is owner-reported installation and local verification. Actual Windmill-worker metadata verification subsequently passed: run `01a18019-e9c6-9787-47ba-4a51b215f0b3`, safe readout `01a1801a-1377-2edd-0f2d-8a5665c02a6c`, exit 0, cleanup verified and no truncation. Both input roots are accessible and non-writable to the worker, and both manifest payload digests match. The bulk input has 9,801 regular files (14,181,854,541 bytes); curated input has 46,877 (5,254,537,351 bytes), with no non-regular files reported. Input assets have not yet been checksummed. This does not establish input source equivalence, corpus completeness, safe checkpoint resume, current host-process custody or production readiness. The existing malformed retained food packet remains preserved; this installer does not repair or delete it. The live Foo places producer differs from the checkpoint-capable source examined during recovery planning, and `scripts/places_checkpoint.py` is absent on Foo. These observed source pins are recorded rather than silently treating the two versions as equivalent. Free disk measured 194.431 GiB; that is not a post-output capacity guarantee.

The preparation-time `README.md` and `REVIEW.md` remain historical review records. Their pending-install language is superseded by the owner-reported outcome above, not rewritten as if preparation or independent review installed anything.

## Source custody and tests

The standalone installer is byte-identical to the reviewed, owner-run artifact, and rebuilding it from the included support sources produces the same hash. The custody copy of `test_incremental.py` changes only the temporary author-workspace scope-file locator to adjacent `approved-input-scope.json`; this fixture contains only the exact approved directory/file lists. All 42 tests passed in the portable copied layout. Expected refusal output in negative fixtures is not an installation failure.

No backup contents, raw datasets, runtime logs, private keys, credentials or user-message artifacts are published. This source is not an instruction to reinstall on an already updated launcher: it deliberately requires the exact prior launcher preimage.

## No Actions publication

The integration branch update is non-forced with an expected-head lease. Both existing workflow definitions were re-read at the parent commit. `foo-runner.yml` accepts pushes only to `offmenu-runner-jobs` changing `.github/offmenu-runner/request.json`; `third-party-services.yml` is manual-only. This additive custody subtree on the integration branch matches neither trigger. Workflow files are unchanged, and no workflow is dispatched or retried.
