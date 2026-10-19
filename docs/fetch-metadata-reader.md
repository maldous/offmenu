# Inactive exact-target owner metadata reader

This additive module is prepared against published base `5e7f4673e78b1f677c69a1ed48a36d24e2692a90`. It has no collector, launcher, CLI, configuration, network or publication hookup. Existing owner-002 bytes and all source originals remain unchanged. Only approved metadata inventories and synthetic fixtures were read during preparation.

## Contract and integration

`reconcile_metadata(proposal_raw, *, parent_selection=None, inventory=None, owner_runtime=None, lease_fd=None, current_read_holds=None, absolute_deadline=0)` returns the closed `offmenu-fetch-metadata-report/1` report. `parent_selection=None` is inactive and performs zero target/owner filesystem access. An invalid proposal pin raises a closed `MetadataError`; no trustworthy target denominator can be manufactured from changed input.

Build the immutable in-memory inventory with `build_inventory(closure_raw=..., runtime_manifest_raw=..., owner_config_raw=..., owner_selection_raw=..., dispatch_hold_raw=...)`. These are exact bytes, not paths. Every digest and byte extent is pinned in `INVENTORY_PINS`. The builder opens no files. The inventory contains exactly the existing 4,753 asset IDs, descriptor/source/country/type allowlists, held identities and exact digest-plus-extent associations. Snapshot identity strings are parsed only from the pinned inventory. No supplied source metadata can create a new ID.

The exact parent selection has these fields, with no additional keys:

- `schemaVersion`: `offmenu-fetch-metadata-parent-selection/1`
- `proposalSHA256`: reviewed 93-target proposal digest
- `readerSHA256`: exact reviewed module bytes
- `handoffId`: `owner-local-comprehensive-20261018-002`
- `ownerConfigSHA256`: `28acbde120ac7d457f24af8cd2e3203927bb770137b8ce414c0d7a082e63b4ba`
- `targets`: explicit, nonduplicated subset of the 92 whole-JSON candidates; each row has exactly `targetId`, `path`, `metadataSHA256`, `metadataBytes`, matching the proposal
- `withheldTargetIds`: explicit unique IDs, disjoint from selected targets
- `clearanceEvidenceSHA256`: immutable reviewed current-clearance evidence digest

The 93rd target, `native-events`, has only historical JSONL-prefix evidence and cannot be selected. All 93 targets remain in the report, including disabled, unselected, withheld, changed, missing and inaccessible entries. The 92 exact read caps sum to 16,493,475 bytes; the largest is 14,588,360 bytes. Bounds never expand after a mismatch.

`current_read_holds(binding)` is required for every selected target before and after its child worker and again before returning rows. It must recompute relevant current no-read, privacy, minor, source and withheld conditions; it is not a cached permission boolean. Its return has exactly:

- `schemaVersion`: `offmenu-fetch-metadata-current-clearance/1`
- `target`: the complete exact target binding above
- `evidenceSHA256`: the selection's exact clearance digest
- `checkedMonotonic`: finite monotonic time, no more than five seconds old
- `expiresMonotonic`: finite future monotonic time
- `decision`: `clear`, `held`, `withheld`, or `unknown`

Only `clear` proceeds. Historical metadata accessibility and recovered source fields do not clear a hold. An unavailable, stale or wrong-target callback is a zero-read blocker. The parent must supply current evidence, not synthesize clearance from metadata. There is no universal second approval requirement in this API; same-invocation authority remains governed by the parent selection and current evidence.

The current `OwnerRuntime` is checked against immutable owner-002 config, selected sources, native path, runner paths and provenance. UID must be 1000, runtime root must be `/home/user/src/offmenu-data/owner-collection-runtime`, and root/work/lock permissions must remain owner-private. The supplied lease descriptor must already own the exclusive Linux FLOCK on the exact named `collection/fixed-selection.lock`. The fdinfo proof ties the lock to that same open description, current PID, device and inode. A separately opened descriptor, even in the same process, is insufficient. This module never acquires, upgrades or releases the parent's lock.

## Isolation and bounds

A main-thread SIGALRM budget bounds parent checks, callbacks, and child supervision at the smaller of 180 seconds and the caller's absolute deadline. An already-active real-time interval timer is rejected rather than overwritten. Every target worker is a private child process; it immediately closes its inherited lease and owner directory descriptors. The parent uses nonblocking pipes and bounded reads. Only this exact child may be killed on expiry; unrelated processes are never signalled. Normal workers are reaped before their result is accepted.

Every target component is opened relative to no-follow directory descriptors, with the complete ancestor chain retained. Only regular final files are accepted; FIFO/device/symlink entries are rejected. File extent is checked before reading. Reads request no byte beyond the exact cap. Full digest, file device/inode/size/mtime/ctime, ancestor device/inode/owner/mode and re-resolved named path are checked after reading. Renaming/replacing a parent is detected even when a hard-linked final inode and content remain identical. No directory discovery or referenced-original access occurs.

If a worker is killed while blocked in an uninterruptible kernel read, the caller still returns within its deadline; immediate kernel termination cannot be guaranteed. SIGKILL is requested, the child has no inherited writer lease, and `bytesRead=null` plus the exact `readBytesUpperBound` conservatively accounts for all possibly consumed bytes. A zero-read hold never launches the worker. Known failures report measured byte counts; unknown read counts are never invented as zero.

Strict JSON rejects duplicate keys, nonfinite numbers, invalid UTF-8 and invalid syntax. A lexical pass bounds depth at 64 and cumulative visited tokens/nodes at 500,000 before constructing a JSON tree. Array/object traversal is only inside the exact metadata document. Recovered objects are capped at 10,000 and the complete sanitized report at 4 MiB, including target accounting. Bound failures stop remaining selected work and suppress partial rows.

## Sanitized evidence and non-claims

Fields are combined only from the same object. Each row retains the exact source-object JSON pointer, canonical object hash and pinned metadata-file hash. Siblings and parent/child fragments are never joined. Unknown IDs are not emitted. Exact recorded hash and extent can propose linkage to existing identities; they do not establish present owner custody. Unknown identity remains unresolved and never proves absence.

Original paths are emitted only as bounded, safe path metadata under the two fixed original roots. They are never opened. Secret-like path tokens, traversal, control characters and query/fragment syntax are suppressed. Arbitrary JSON-property names are not output as pointers; rows under unrecognized pointer components are suppressed.

URLs are emitted only with a normalized origin already present in the pinned inventories, an all-placeholder path shape, a finite allowlist of query KEY names, and the SHA-256 of the complete exact URL. Query values, signatures, credentials, fragments, arbitrary path segments and unknown query-key strings never cross the boundary. Userinfo or unknown origins are rejected. URL identity is not full request identity: method/body/header/release and rights remain independent and unresolved.

Title, purpose, release, holds, source role, outcome and rights never emit arbitrary free text. Presence is represented by an object pointer/hash and a closed classification, or `unresolved`. Headers, cookies, tokens, body text, unknown fields and raw exceptions are absent. Explicit nested restrictions exclude the candidate object and cannot be shed by descending into its children. Independent unrestricted siblings can still produce proposals. Known held asset/descriptor/payload identities are excluded.

The report contains all target outcomes, exact read counts or conservative uncertainty bounds, recovered/excluded/unresolved object counts and closed failure codes. `visitedNodes`, `sanitizedObjectsProduced` and `sanitizedRowBytesProduced` are charged both per target and globally immediately after worker return, before any post-read clearance, owner recheck or deadline check. These consumption counters include work whose rows are later suppressed. Further workers receive the remaining cumulative budgets, never budgets derived only from published rows. Terminal node/object/output limit codes stop the invocation before any post-read callback can mask them. Parse and depth failures retain consumed node accounting. The final validator requires global consumption counters to equal the per-target sums. `matchingCoverageExhaustive` is always false. Rows keep `requestIdentityStatus`, `custodyStatus` and `rightsStatus` unresolved; usable-original and country/type completion promotion are always false.

A `reconciled` outcome proves successful whole-file pin and safety checks. It does NOT prove that all original custody was discovered, that a missing match means absent custody, that a URL establishes a GET contract, or that a source is clear to acquire. Candidate admission must independently use exact full-request identity and current readable native/local/historical claim evidence, blocking relevant unresolved matches. The six FAO records are tested only as exact links to six existing snapshot asset IDs; they create no new assets, requests or verified-custody claims.

## Publication boundary

`sanitize_report(report, proposal_raw, *, inventory=None, parent_selection=None)` (also `validate_report`) rejects additional fields, raw URLs, arbitrary identifiers or classifications, changed target pins, duplicate object pointers, invalid counts, incomplete target accounting and promoted permission/custody/completion flags. It returns the original report without repairing it. This is shape/provenance validation, not a live execution or absent-custody capability. Successful active invocation runs this validator before returning.

The parent should retain the 4 MiB metadata report separately or as bounded closed chunks; it is not intended to fit inside the existing small global summary. The parent owns adoption, source-level gating, collector wiring and any later publication.

## Offline verification

`PYTHONPATH=. python -m unittest discover -s tests -p test_fetch_metadata_reconciliation.py -v`

The 53 tests read only the reviewed shared metadata fixtures plus synthetic temporary JSON, lock and directory fixtures. Production pins, root and UID are changed only by scoped test mocks. The reviewed metadata fixtures are expected at the explicitly documented shared review paths; this focused audit suite is not a fixture-free general CI suite. There is no production test bypass. No Foo access, metadata-target execution, original reads, network calls, source GETs, publication or owner-002 edits were performed.

## Review correction, successor r2

The first freeze had a confirmed ordering defect: post-read held/unknown clearance could mask already-consumed node counts and resource-limit outcomes. This successor preserves the first freeze unchanged and fixes the ordering. It also prevents discarded rows from resetting cumulative object/output budgets. The independent two-target regression with a four-node cap now reports four charged nodes, a node-limit outcome on the second target, no rows, and no later success. Eleven new regressions cover held/unknown/exception callbacks, parser and depth failures, post-read timeout, terminal node/object/output errors, cumulative suppressed-row budgets, lexical pre-reservation and publication-counter tampering. No authority or acquisition scope was expanded.
