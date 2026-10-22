# Final-ingest source preparation — 2026-10-22

## Publication and installation boundary

This is a source-only preparation on `integration/final-ingest-20261022`, based
exactly on commit `c792d3b71bc7907e96b6688242e090ede100b6ab` (base tree
`4de653f4ad20805243f11702cef55e06d2aaea2f`). It is not an installation,
an execution request, or evidence of a completed real-data ingest.

The runtime source `BRANCH` deliberately remains
`integration/manual-actions-20261022`; this preparation branch is **not directly
runnable** against Foo. The active old `./run` must exit, and its existing local
receipt history and complete `.git/offmenu-runner` state must be preserved and
reconciled, before reviewed promotion to the normal manual-action branch.
Never switch/reset/stash a live checkout or delete its pending receipt spool.
See [FINAL-INGEST-RUN.md](FINAL-INGEST-RUN.md) for the after-exit boundary.

Publication changes neither the active manual branch nor control/results
branches, runner workflow/profile files, source pins, execution requests, or
Foo state. The root launcher and all unchanged baseline files retain their
existing repository bytes and modes. Existing baseline receipt files remain
untouched; no receipt or private output is added by this release.

## Included closure and exclusions

The 36 reviewed payload changes comprise the finite acquired-source catalog;
recipe, static-JavaScript and menu adapters; versioned relational target
schema/mapping/materializer; evidence collection; ingest engine/orchestrator,
finite plan, runner and isolated receipt transport; and their generated tests
and documentation. This release note and the machine-readable
[FINAL-INGEST-SOURCE-MANIFEST.json](FINAL-INGEST-SOURCE-MANIFEST.json) provide the
publication inventory. The manifest binds all other changed files by Git blob
SHA-1, SHA-256 and byte count; it excludes only its own self-hash.

`fetch-sources.json` is required by the offline acquired catalog. The catalog's
generated tests additionally compare artifact identities with
`fetch_sources.artifact_key`, so `fetch_sources.py` and its generated tests are
included unchanged from the reviewed source tree. The offline ingest code does
not import or execute that network fetcher. There is no fetch operation in the
plan and no automatic acquisition activation. The acquisition manifest retains
its separate historical authorization and is not a new ingest readiness claim.

Dependency review found no ingestion/test imports of the separate ACL helper.
`grant_acquired_read_access.py`, `source-access-handoff-plan.json`,
`SOURCE-ACCESS-HANDOFF.md`, and `test_grant_acquired_read_access.py` are excluded
and remain a separately managed handoff. The unrelated `fetch_capacity.py`,
its tests, and standalone fetch-execution instructions are also excluded.
No credentials, raw datasets, caches, private outputs, logs, bytecode, internal
notes, or new return files are included.

## Verification evidence

The publication closure was copied into an isolated local tree and tested after
those exclusions:

```sh
python3 -B -m unittest discover -s manual-action/tests -v
```

Result: **518 tests run, OK, one skip** (`optional installed-only pyarrow
unavailable`). This is the prior 569-test reviewed superset less 36 separately
managed ACL tests and 15 unrelated capacity tests. The excluded ACL filesystem
skip therefore is not part of this publication closure. Tests use generated
source-shaped fixtures and temporary local bare Git remotes, not Foo data.

The full executable `./run` integration fixture covers all 50 generated acquired
artifacts / six families, completed retained-source no-replay, partial cursor
continuation, legacy receipt-spool migration, malformed-source isolation, exact
relational links and bounded unresolved candidates, atomic sanitized receipt and
evidence-supplement delivery, and concurrent code-branch advancement.

Frozen reviewed implementation SHA-256 values:

* `ingest_engine.py`: `306a74ee5a3d8e9c97b13ea8e4a31e14e044cdb308239c2736e51ff3f88c0b86`
* `plan_runner.py`: `705124b0496ceb8a72d8d8621a7bab890c54011acd04da6457b629ef20a89ad1`

## Runtime gates remain open

The actual invoking identity must be able to traverse the exact reviewed cache
parents and read the allowlisted artifacts and custody receipts. Missing access
is a per-source blocker, not permission to broaden privileges. Cache integrity,
actual record counts, resource availability, adapter acceptance and terminal
receipts still require the eventual real run after promotion and recovery.

Outputs are source-faithful staging and separately versioned derived relational
targets, **not application-bound gold databases**. Application binding, semantic
review and private household input remain explicitly deferred. Subsequent normal
runs automatically return pre/checkpoint/post evidence, pending work and bounded
failure reasons; partial work resumes rather than initiating endless fetching.
