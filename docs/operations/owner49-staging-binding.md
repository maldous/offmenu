# Owner49 portfolio staging binding proposal

This bounded package targets accepted develop
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. Pending PR42/28a5ba7 is not its
baseline. It processes retained **metadata** and small authored fixtures only.
No source body was read or qualified, no source downloaded, and no admission or
country completion follows from these results.

Reviewer38 R1/R2 correction: portfolio request envelopes are validated before
sorting/unpacking; malformed names get synthetic diagnostic slots and valid peers
still report. Binding containers and the actual boolean fixture discriminator
are checked before authored cells are processed. Focused regressions run with
`python3 -B -m unittest discover -s tests -p test_owner49_staging_corrections.py -v`.

`owner49-staging-catalog.json` is the source-linked configuration for FI/JP/KE/KG.
It contains exact retained manifests/receipt hashes, input identities, country/type
applicability, field selectors, native units/basis, unknowns and typed dependencies.
These absolute metadata pointers remain on the selected local executor. They are not source bodies,
credentials, a new ledger, or a request to acquire anything.

FI selectors are the retained two-food/four-observation measured CSV/JSON map;
the code does not replay it. Its 18 columns and concrete FAT/SUGOH coordinates
are preserved, including source labels and null/zero uncertainty. The original
national acquisition timestamp is unknown; a record's fetchedAt and an overlay's
creation timestamp are not substituted. The selected-export review does not
clear the national Fineli hold or 53,654 unresolved zero meanings.

JP binds the official 2024 CAA compilation and two errata asset pins to their
actual receipt acquisition clocks. One name-index crosslink is reference evidence,
not monograph/method/formula/nutrition/legal acceptance. KE retains both the
403 composition denial and the distinct catalogue SSL failure, plus already
returned 46/51 custody metadata; no retry or repeated missing-input request is
performed. KG binds author-deposit metadata only: files=[], no actual dataset,
no native units/basis or food/recipe selectors. Description counts are not records.
Every country still lacks complete ingredients, recipes, nutrition, providers,
price/basket and dietary-reference coverage.

## Pure metadata interfaces

`offmenu.refresh.owner49_staging.retained_diagnostics(catalog_bytes)` returns
canonical per-country diagnostics with explicit unsupported production capability,
unperformed body verification and unknown/no-download cache intent. It never
follows a path. Each country's missing inputs and owners remain isolated.

`MetadataBinding` is a trusted-code declaration, not a source-controlled manifest
or CLI registration. `assess_metadata(binding, manifest_bytes, validated_at=UTC,
previous_key=None)` takes a bounded proposed input envelope. The envelope format
is shown in `tests/fixtures/owner49_staging/manifest.json`: exact source/release,
country/type, input relative path/bytes/hash and original acquisition UTC. Its
SHA-256 must already be pinned by trusted code. Historical portfolio receipts
have different formats; this package does not relabel them as accepted manifests.
Real envelope creation/contract approval remains pending source-specific evidence.

Results distinguish valid, no-op, missing, held, malformed and stale-input. All
carry admitted=false. A valid result verifies supplied **metadata consistency**,
not asset existence/content, licence sufficiency or review. Replay identity binds
trusted selectors, input pins, native semantics and original acquisition; validation
time is separate and cannot reset age. Identical input gives the same replay key.
Previous-key equality reports a no-op intent, not proof that a prior output exists.

At this base there is no generic pure cache planner. The binding uses shared
`MIN_TTL` (30 days), UTC validation and fixed local intent classification only:
under 30 days is reuse intent; exactly 30 days or older is stale-input with no
automatic refresh. Real portfolio diagnostics conservatively report unknown.
No force, revalidate or download mode exists here. Existing source-use/retention
holds take precedence over age; actual cache verification and acquisition remain
with shared reviewed handlers. `core.cache_policy` is Wikibooks-specific and
`plan_fixture` is registry-only; neither is called or given spoofed source IDs.
`CachedAcquirer` is not instantiated or run.

`stage_authored_fixture` is deliberately fixture-only and bounded to 16 KiB.
It binds concrete flat source cells to exact target pointers, checks authored
native unit/basis semantics, preserves null/zero and invokes shared
`field_origin_errors` and `serialization.encode_records`. It is not a Fineli,
CAA PDF, KE or KG parser. Tests also qualify this authored candidate using the
existing shared `SourceContract/qualify` API with fixture=true. No real source
contract or GLOBAL handler/admission is registered. Diagnostics suppress parser
exception text, source bodies and credential-like strings.

## Validation and integration

Run `python3 -m unittest discover -s tests -p test_owner49_staging.py -v`.
The small fixtures are authored, contain one synthetic record, and include no
country source data. Tests cover all outcomes, duplicate/nonfinite JSON, size,
identity/hash/time mismatch, TTL boundary, replay, per-source failure isolation,
zero/null origins, native unit/basis failure and shared fixture qualification.

Proposed shared interface for the product maintainer **only if selected**: one pure
`plan_retained_input` in the shared policy module, with trusted source/release and
input pins, original-acquisition/revalidation chain, UTC now and hold/retention
status; return unknown/reuse/revalidation intent with zero network and no asset,
rights or admission claim. the product integrator result5798 documents the same gap.
This package does not add that public API or copy a shared acquisition engine.

Only these owner49 paths change. Shared core and other workers' bindings remain
owned by their current authors. Submit the immutable commit, files and focused
test evidence through the product maintainer to the product integrator and a designated independent
reviewer. Human direct00 messaging authority is not inferred from another chat's
request. Current package is an author proposal until independent approval and
develop integration. No next source assignment, security change, production/CIX
execution, DEV7645 action, source retry or data admission is implied.
