# Wired product origin stage (private candidate)

The new callable `product_origin_stage.qualify_product_origins` is the concrete
versioned integration entry point for retained OFF, Prices and USDA bundles. It
calls the unchanged reviewed product normalization/qualification bridge, verifies
its original SQLite and candidate hashes, emits actual per-datum origins into a
new candidate and sidecar, and runs the qualification contract with both its
original semantic validator and the shared field-origin coverage validator.

Call with the same trusted SourceContract, bundle and role mapping used for
`qualify_product_candidate`, plus separate non-overlapping normalization and
origin-stage destinations, license, attribution and limits. No caller-authored
ZIP member map is needed: the wrapper inventories exact member paths from the
verified pinned ZIP under the existing bounded metadata checks. Relative asset
paths come directly from the source contract. No frozen dependency is modified.

Outputs in the new destination:
- candidate.jsonl: canonical single-element arrays containing enriched records
- field-origins.jsonl: canonical single-element arrays containing matching record
  IDs and complete fieldOrigins maps
- manifest.json: evidence-inclusive input inventory, enriched candidate digest,
  both output hashes, original candidate/SQLite hashes, exact archive members,
  original normalization manifest pin, limits and all policy/dependency pins

The original candidate and private SQLite remain unchanged in the separate
normalization directory. The origin-stage manifest describes that external
custody by hash, without inventing a source file path. No raw database is copied
into the enriched stage.

The stage streams bounded lines and writes into a private temporary directory.
Before completion it rechecks every source asset and both original normalized
artifacts. A failure discards only the new temporary tree. Existing completed
origin stages require identical contracts and verified candidate/sidecar hashes,
and are requalified against the current exact source contract. A different
semantic policy, dependency, source input or limit cannot silently reuse output.
Qualified or not, a result remains `accepted: false`; production admission and
GLOBAL rollout are separate operations. A failed semantic qualification is
retained as a diagnostic candidate and never becomes qualified or accepted.

## Evidence and boundaries

26 targeted tests (16 emitter + 10 integration), 228 composed tests and compileall
pass. All three synthetic retained source formats produce an actual enriched
candidate and sidecar that satisfy the shared origin validator and independent
fixture expected-count/ID/source-semantic qualification contracts. Tests also
cover replay into the same and a new destination, private original preservation,
SQLite corruption, sidecar corruption, source pin changes, output cleanup on
origin expansion failure, path overlap, and a failing semantic contract.

This wrapper is executable offline integration, not merely a wiring proposal.
It is not yet selected by a production scheduler or admission registry; callers
must use this entry point rather than the old normalization-only bridge to claim
field-origin coverage. The emitter remains pinned to the previously reviewed
product adapter SHA-256; changing those adapter bytes requires a new review and
explicit repin. Original source rights, scope and capacity/Foo custody rules
still apply. No network, raw production inputs, scheduler, GitHub write or
production admission occurred during implementation/testing.
