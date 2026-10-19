# Inactive exact Taiwan retained-reference writer

This separate additive code proposal extends the frozen acceptance manifest
`676293ceb7d7f7169ed103f7dd494c8da58f50148572ce1f941850ba476aee5e`.
The six previously reviewed proposal files remain byte-identical. No collector,
media module, runtime configuration, dispatch hold, launcher, OPC/progress
configuration or scheduler is changed. Existing owner handoff 002 remains the
only context. There is no CLI or default activation. Only synthetic temporary
custody fixtures were exercised here; no Foo access, source download, original
copy, publication or activation was performed.

## Application prerequisites

The calling reviewed owner integration must supply all of:

1. The exact frozen acceptance manifest bytes.
2. An explicit `parent_selection` dictionary with precisely these fields:
   - `schemaVersion`: `offmenu-retained-taiwan-parent-selection/1`
   - `acceptanceManifestSHA256`: the exact frozen manifest digest above
   - `reviewedWriterSHA256`: SHA-256 of the independently reviewed exact
     `scripts/accept-retained-taiwan.py` bytes actually imported
   - `handoffId`: `owner-local-comprehensive-20261018-002`
   - `scope`: `exact-three-unchanged-retained-reference-acceptance`
   - `preparationSelected`: `false`
3. The existing live `OwnerRuntime` object under the existing 002 profile.
   Its source selection, config, owner, root and provenance must match the
   pinned current source files and frozen manifest. Its existing `admit` method
   supplies native/local/historical claim scans; unavailable native claims are
   a block. An inaccessible historical runner root retains the existing exact
   dispatch-hold exception and is never described as an empty claim catalogue.
4. The already-held `collection/fixed-selection.lock` descriptor on the main
   thread. The API does not acquire or upgrade a lock. Linux fdinfo must prove
   that this specific open file description owns the exclusive flock, under
   this PID, for the same private regular single-link file still named there.
5. A callable `current_adverse_evidence` which recomputes the caller's current
   bounded metadata-only source-conflict evidence on each invocation. Use the
   existing acquisition/collection conflict workflow. Do not supply cached
   clearance, a default empty assertion or a network-producing callback.
6. A finite `absolute_deadline` using `time.monotonic()`. The operation is capped
   again at 210 seconds. Each exact parser validation retains its existing
   60-second bound. The existing selected storage floor must cover the small
   metadata writes; it is never reduced.

Supplying a selection dictionary is the trusted owner's explicit execution
selection boundary, not cryptographic proof of human approval. The reviewer and
parent must select the exact writer artifact before an invocation. A publisher
or remote document cannot provide this authority. Missing selection fails before
owner/custody access. The imported writer bytes and three frozen direct source
dependencies are pinned; the enclosing owner launcher must also continue to pin
its complete owner adapter and dependency closure.

## Owner API

`accept_selected(manifest_raw, *, parent_selection=None, owner_runtime=None,
lease_fd=None, current_adverse_evidence=None, absolute_deadline=0)` returns
`(result, VerifiedAcceptance)` or raises `AcceptanceError`.

Before writing any acceptance file it:

- Verifies the exact manifest and source/code selection, main thread, unchanged
  owner 002 config/current hold and existing writer lease.
- Opens every source body, failed intent, failed detail and relevant ancestor
  through no-follow private owner descriptors. Original files must be regular,
  single-linked and retain their exact identity and extent.
- Runs current source/claim admission and reruns `validate_selected` for all
  three exact sources. Each fresh result must equal its complete pinned
  third-run validation proposal. This includes exact source/body/intent/detail
  identity, parser version, bounded full traversal and zero diagnostics.
  Changed parser evidence requires a new review rather than being ignored.
- Repeats current admission and verifies that the original descriptors and
  paths remained stable. Fresh validation alone does not apply disposition.

The only writable namespace is:

`collection/retained-taiwan-acceptance/<manifest-sha>/`

The immutable, content-addressed `receipt-<receipt-sha>.json` binds the explicit
parent selection, exact old publication evidence, all three unchanged retained
references, full fresh validation results, preserved holds and the actual new
`acceptedAtUTC`. Original acquisition times remain null. The receipt contains
no original body or page text. It is not an acquisition success and cannot be
reported as a download or as a new physical original.

## Commit, crash and repeat semantics

The writer creates private directories and then exclusively creates the receipt
with mode 0600. It handles short writes, fsyncs the file and directory and reads
back the exact content-addressed bytes. It checks claims, current owner context,
custody identities and the lease again before exclusively creating
`committed-<receipt-sha>.json`. The marker binds the receipt hash/extent and the
same manifest/selection. It too is fsynced and read back, followed by identity,
lease and deadline checks.

A receipt has no consumable acceptance status without its exact valid commit
marker. Unknown files, multiple/conflicting receipts, symlinks, unsafe modes,
identity changes, partial JSON or receipt-without-marker are fail-closed.
Nothing is overwritten or deleted, including a failed/partial write. No retry
repairs or clears uncertain state. A future explicit recovery decision is
needed for an incomplete transaction. Empty newly created directories contain
no acceptance and may be retried after all fresh gates.

SIGTERM/SIGINT/SIGHUP use the reviewed scoped signal ownership: interruption is
deferred until owned descriptors/parser children are cleaned up, then delivered
to the restored caller handler. An interrupted invocation returns no successful
capability. A fully valid surviving receipt and marker can be reconsidered only
through the complete fresh reuse checks. SIGKILL and machine failure cannot run
cleanup; the same persisted two-file protocol decides later readability.

An identical completed transaction is reused only after the full current
admission and exact three-source parser validation. Repeat/reuse writes no new
receipt and preserves the original acceptance timestamp. It does not claim a
new disposition application. The original `original.partial`, old
`successor-intent.json` and failed detail remain untouched in every path.
No `original.pdf`, copied original, reset intent, acquisition reservation, GET
or retry is created.

## Read-only fetch and spawn-safe preparation

`fetch_accepted_references(...)` takes the same explicit arguments and performs
the same live checks. It never creates directories or files; absent or uncertain
receipts block. Its returned capability is immutable, process-local and expires
at the bounded owner transaction deadline. `capability.references()` yields
metadata-only retained references for the caller. The local
`exact_accepted_bom_identity(source, data, capability)` is an identity check only;
it is not the spawn-worker integration contract.

For spawn workers use both of these APIs:

1. `make_preparation_descriptor(capability, source, preparation_contract,
   *, lease_fd)` emits an ordinary JSON object, at most 8 KiB, for only the exact
   source contract and existing selected preparation contract. The descriptor
   binds manifest, reviewed parent selection, committed receipt, source hash,
   retained relative path/hash/size, preparation-contract hash, parent PID/start
   time/lease descriptor/inode, and the transaction monotonic deadline. The
   caller must separately have selected the preparation operation. Constructing
   a descriptor does not perform or activate it.
2. `verify_worker_descriptor(descriptor, source, data, original_path,
   preparation_contract, *, absolute_deadline)` is safe in a spawned process.
   It independently reads and verifies the committed receipt/marker, current
   pinned runtime/hold, exact full source and preparation contract, original
   identity and old failed-record hashes. It verifies the parent process start
   identity and still-held exclusive flock via `/proc/<pid>/fdinfo/<fd>` before
   and after the read. Missing `/proc` capability is a block, never a bypass.
   It rehashes the exact unchanged retained file under no-follow custody and
   checks that the bytes supplied for sniffing have the same exact length/hash
   and satisfy the source-bound BOM hook. It bounds this read to 30 seconds
   within both caller and descriptor deadlines. It runs no parser and writes
   nothing. Native claims are the live parent admission's responsibility before
   queueing; the parent must keep its lease for the worker's entire lifetime.

A successful worker result is `verified-exact-retained-bom-identity` with
`actualMediaType: application/pdf`. Only that successful result may support the
narrow media-identification exception. The media worker must still execute its
ordinary permission/hold checks, integrity checks, bounded parser, storage
reservation/floor and preparation receipt handling. Pass the BOM-containing
bytes unchanged. Never modify generic PDF recognition or allow an unverified
boolean to substitute for the descriptor check. Renew an expired descriptor
through fresh owner fetch/admission; do not extend its deadline manually.

## Remaining integration work

This patch intentionally provides no collector/media hookup. The reviewed
integration must intercept only these exact three retained identities before
ordinary failed-intent acquisition, call the writer/fetch APIs under the owner
lease, record the separate acceptance result, and reuse the existing partial
path. It must add an explicit bounded descriptor channel to spawn preparation
workers and call the read-only worker verifier after integrity and contract
checks. All other sources retain existing acquisition and sniffing behavior.
The existing acquisition success schema requires an acquired timestamp and an
ordinary original filename; it must not receive a fabricated success row.

Existing downstream holds remain: redistribution, commercial corpus reuse,
translation, normalization, semantic/gold admission and country completeness.
No runner resume, new handoff, source-policy expansion or new permission follows
from acceptance. Root has selected the frozen manifest conditionally; actual
code selection and owner execution remain subject to independent review.

## Verification

Run the writer tests with:

`PYTHONPATH=. python -m unittest discover -s tests -p test_retained_taiwan_acceptance_writer.py -v`

Tests use synthetic PDFs and private temporary owner trees. They exercise actual
installed parser subprocesses only in the owner validation fixture, actual
Linux flock proof, current native claim scans, append-only writes, short writes,
interruption, crash-like uncommitted state, reuse, path and record changes,
capacity/permission gates, and an actual spawn process performing the read-only
worker descriptor check without a parser or network.
