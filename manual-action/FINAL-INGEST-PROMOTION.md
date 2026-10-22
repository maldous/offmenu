# Receipt-preserving final-ingest promotion — 2026-10-22

## Provenance and recovery boundary

This release combines the previously reviewed final-ingest preparation
`f9eb4628f05e62828205aa308a57b408c904dc61` with the independently reviewed narrow
supplier global-budget correction and separate storage-conservation correction. It is based on the successfully reconciled
manual-action head `db0bbdee86e1afb4919cc75072b401b94fe9151a` (tree
`a8b91759a07e57efe7e020d9a2e44809c260024b`), not on an older source tree that would
lose recovered receipt history.

The recovery commit has exact parents
`5410758433517fc03cd404bc5f0f0c28d4289ee7` and
`c792d3b71bc7907e96b6688242e090ede100b6ab`. Both preserve the published
`01c9c63bc6a7bdbdf66b971fe804c83845450939` checkpoint ancestry. Remote verification
found all 1,474 previous blobs unchanged and exactly one added canonical,
strict-schema sanitized receipt, validated with the exact baseline runner.
That receipt is an earlier running checkpoint, not a terminal ingest result.
The recovery helper deliberately left the pending local spool untouched.

The promotion tree starts from the recovered tree, overlays only reviewed
source/test/documentation files, and retains every recovered receipt. Its Git
parents preserve both the recovered manual-action history and the original
prepared source history. Source publication does not drain the spool, start
ingestion, fetch data, or change Foo files.

## Current source closure

The original `FINAL-INGEST-SOURCE-MANIFEST.json` and preparation release note
remain unchanged historical records for `f9eb4628`. They must not be read as
current hashes for the subsequently corrected files. The narrow overrides and
independent reviews are recorded under
`corrections/supplier-global-budget-stop-20261022/` and
`corrections/standard-run-no-extra-copy-20261022/`; the complete current source
delta against the recovered head is listed in
`FINAL-INGEST-PROMOTION-MANIFEST.json`.

The correction checks global budgets before suppliers open another eligible
source, stops the unread tail when the global budget is exhausted, and preserves
the committed cursor of an active partial source. Source-local row caps and
malformed-source isolation still permit later sources. The first global stop
records a bounded fixed reason and contemporaneous limit/free-space values,
separately from row errors. No adapter version, source fingerprint, store schema,
existing checkpoint or prior count is rewritten.

The standard `./run` explicitly disables automatic derived relational
materialization, so it does not add a per-snapshot copy of staging payloads or
claim a new relational-target report. The standalone materializer, schema and
mapping remain available only for explicit optional use. Existing derived files
and staging databases are not deleted, compacted or moved. Suppliers also honor
already-known catalog duplicates (same inode or bounded-small-file byte equality)
without a new broad scan. One cached source asset plus its actual database
representation remains the intended normal path; no global or cross-domain
physical deduplication is claimed.

ACL helpers, ACL test-verification tools, capacity tooling, raw test logs,
datasets, private outputs, credentials, runner workflow/profile files, execution
requests and source pins remain outside this publication. The fetch identity
dependency and reviewed artifact manifest remain present without any automatic
fetch activation.

## Exact publication verification

An isolated tree was assembled from the original publication, the five
manifest-bound budget source/test files, and the separate seven-file storage
source/test/documentation correction. The original source manifest hash
is still `9cd97cd7ce74f560a4f965ed506a1cccc557ba94a051a37ebbb900f9241bea5b`.

```sh
python3 -B -m unittest discover -s manual-action/tests -v
```

Result: **530 tests run, OK, one optional PyArrow skip**.
This exact ingestion publication closure is the prior 518 tests plus ten focused
budget-stop tests and two supplier duplicate-preservation tests. The builder's
broader 595-test working-tree suite additionally
contains separately managed ACL, ACL-test-verification and capacity tests; those
tools are not silently included here. All final frozen correction file hashes
were rechecked after the publication test run. Independent review is separately
bound to both correction manifests and patch hashes.

The integration tests continue to cover generated 50-artifact/six-family ingest,
completed-source no-replay, partial cursor continuation, legacy spool migration,
sanitized evidence supplements and isolated receipt publication. The updated
standard-run test also verifies that no new derived snapshot/report is created,
that historical target-file sentinels remain unchanged, and that a repeated run
does not repeat completed record writes.

## Next ordinary run and remaining gates

Once this release is on `integration/manual-actions-20261022`, the existing
checkout at the reconciled head can use its ordinary **`./run`** command. The
launcher locks, pulls fast-forward only, reloads reviewed code and recovers the
preserved pending receipts before normal ingestion. New receipts use the isolated
`integration/ingest-receipts-20261022` transport; the source branch no longer
receives new runtime receipts. No command is invoked by this publication.

The user subsequently reported 286 GB free. That restores substantial headroom,
but is not a guarantee that all remaining ingestion fits. Resource guards remain active; no reserve is lowered.
Actual CLI cache readability, custody checks, acceptance counts, disk headroom
throughout the run and terminal receipts remain runtime evidence requirements.
Partial work remains resumable. Application/gold binding and private household
input are still deferred. No additional fetching is enabled.
