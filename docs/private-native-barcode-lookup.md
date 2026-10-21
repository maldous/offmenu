# Private qualified native barcode lookup

`offmenu.refresh.native_barcode_lookup.lookup_native_barcode` consumes one
independently qualified OFF or USDA native product output. It returns exact
lexical barcode matches with the native product ID, source-record ID, exact
`ingredientsText`/null and the complete native record, including provenance and
unknown/unmapped fields. A present empty string, explicit null and missing field
remain distinguishable. Multiple products sharing a barcode remain separate
matches in source order. Nutrient profiles do not substitute for products.

The existing public curated engine rejects native/private ingredientsText, and
the inventory table does not retain its qualification/provenance. This separate
private consumer uses the existing singleton-packet JSONL product projection
without changing its schema, source factory, common graph or public routes.

## Trusted input and invocation

```python
from offmenu.refresh.native_barcode_lookup import lookup_native_barcode

result = lookup_native_barcode(
    selected_native_candidate_path,
    contract=reviewed_source_contract,
    qualification=actual_source_qualification,
    qualification_sha256=independently_selected_qualification_digest,
    barcode="00012345",
    max_scan_bytes=selected_full_scan_budget,
)
```

These names are application inputs, not a manifest-to-contract constructor or
installed runtime caller. Worker26 owns the exact source-specific contract,
record schemas and semantic policy. `qualification` must be the actual existing
`SourceContract.qualify` result for the same exact private native output; its
independently selected digest must come from trusted reviewed selection, never
from the same untrusted receipt being checked. A hash/fingerprint is not a
signature, permission grant or review authority. The consumer verifies that pin,
contract fingerprint/source/release/scope/native/private/fixture/count bindings,
current contract holds/operations, and exact candidate hash before returning any
matches. Source qualification is not independent food identity/ingredients/GTIN
assurance, English, dietary, gold or country acceptance.

The path is the selected **uncompressed qualified candidate JSONL output**, with
one `[record]` packet per LF line. It is not an archive, gzip cache, source.sqlite,
retained raw original, curation shard or generic sidecar. Originals and source
inputs are not opened/requalified by this module. The API has no CLI, network,
source factory, server, public/UI route or activation. Both receipt and current
trusted SourceContract must explicitly agree on fixture scope; tests cannot
silently become real data admission.

## Output and work bounds

`result.matches` contains `nativeProductId`, `sourceRecordId`, `ingredientsText`,
`ingredientsTextState`, `candidateLine` and the full parsed native `record`.
`candidateLine` locates the product within the exact candidate digest returned
with the result. Source attribution/rights and unknown fields remain in the
record. IDs and barcode strings are never stripped, cast, case-folded, translated
or check-digit validated. Structured ingredient edges and cross-source joins are
not generated. Missing/unknown ingredients never become a claim of no ingredients.

Each lookup performs one bounded **full artifact scan** (linear work), with no
persistent index. The default scan limit is64MiB, limited additionally by the
selected contract output cap. Maximum packet length is the existing8MiB source
record limit. Defaults allow100 matches and8MiB of match payload; explicit limits
permit at most1000 matches/64MiB payload and1TiB full scan. All limits are strict
positive integers. A limit failure returns a fixed error, never a silently partial
list or false no-match. Even a no-match verifies all bytes. Candidate inode/size/
mtime/ctime and its exact receipt-bound SHA are checked; source IDs/releases and
private visibility are checked for all rows. This assumes the caller's existing
private execution/custody boundary, not a new OS sandbox.

Worker57 must select/qualify runtime and full-scan I/O/memory/walltime bounds for
any real eligible output. This module itself imposes byte/row/payload bounds,
not a walltime watchdog or full-corpus performance guarantee. Do not run a large
artifact with its default budget and interpret a bound error as absence. No
actual index or real lookup is built/run in this change.

## Verification and remaining dependency

The synthetic suite obtains eligible fixture receipts through the existing
`qualify`, then checks exact Unicode/whitespace/line separators, leading zeros,
lexical non-matches, barcode collisions, USDA IDs, ingredient unknowns, full native
provenance/data, private/source/contract/policy/fixture pins, receipt tampering,
late candidate mutation, no-match verification, scan/result limits and symlinks.
No production source contract is fabricated or source body/sample is read.

The next data dependency is one selected independently qualified native OFF/USDA
output with its exact current contract and pinned receipt, plus Worker57's scoped
runtime/read selection. Existing incident10230, source-operation/privacy/custody,
failed25/P1/review/platform and caller/runtime/public/production/CIX holds remain.
Gateway selects independent review and existing00 alone integrates source. Real
lookup rows remain0 until eligible input and execution are actually selected.

## Retained paired OFF projection adapter

`lookup_retained_off_products(path, selection=RetainedProductShard(...),
observations=selected_identifier_rows, limits=RetainedProductLimits(...))` is an
additional preparation/load-time callable in the same module. It does not change
the qualified-native consumer above. It reads exactly one independently selected
legacy OFF gzip shard, never the original dump, identifier DB or sibling shards.
There is no real-data factory, CLI, server, image fetch or automatic retry.

Trusted application code selects the manifest-derived shard key, exact extent and
SHA, original/occurrence/database hashes, current five-part file identity, current
rights/custody/operation receipt pins, retain/parse/transform operations and holds.
These typed values are evidence bindings, not permission or review grants. Caller57
owns real source/FD/runtime/resource selection; fixture success grants none.
Gateway selected the private local scanner consumer scope only. Public/cloud/
production distribution, training, image use and denied routes remain unselected.

The bounded input is at most25 current identifier observations from trusted code,
not client-provided paths, ordinals or SQL. Every observation binds its run, input,
assertion, source/release, exact lexical code, original occurrence ID and occurrence
asset. Each projected packet must contain the linked product and nutrient profile
with the same original sourceRow/archiveSHA/release/code. A same-barcode packet at
another ordinal never supplies details. All requested observations survive;
missing duplicate/quarantine bodies stay `not-loaded`, with no selected primary.

The implementation uses one read-only, no-follow/nonblocking held FD and one
hashing gzip parse/CRC/EOF pass. It validates every packet's schema, shard key,
unique legacy native key and profile provenance. Exact compressed extent/hash,
packet count and named/held identity are checked before any result returns.
Byte/packet/expanded/result/deadline failures are fixed errors, never partial
success or a false source absence. Caller-owned OS limits remain necessary.

Returned sourceProducts carry exact observation keys, the original observation,
LOCAL citation ID if supplied, complete paired projected records and field states.
Fields include name/names/brand, package quantity, markets/categories, ingredient
declaration, raw nutriments and source basis, the complete nutrient profile,
allergen/trace/dietary-label source claims, origins, manufacturing places and
provenance. Unknown data stays in the complete records. `canonicalIngredient`
remains null/unmapped and never suppresses source text. Empty string, explicit
null and absent projected field are distinct; original publisher presence and
per-field language remain unknown. The packet evidence SHA uses this module's
canonical sorted JSON bytes, not original JSON lexemes or the original body SHA.
The packet coordinate plus `/0/...` or `/1/...` field pointer locates the value.
Pointers are returned only for fields present in the retained document, including
explicit null or empty values. A supported missing field retains its projection
evidence hash with a null pointer, consistently in direct and indexed OFF paths.

This historical projection may have used name fallback, collapsed source
missing/null/empty values, converted package numbers, mapped countries, defaulted
nutrient bases or derived nutrient values. Returned text/quantities are exactly
the retained projection, with these limits stated; they are not upgraded to raw
source lexemes, English, canonical facts, allergen safety or dietary certification.
Image references are `not-loaded/representation-not-provided`; original image
availability is unknown. No barcode-derived image URL is invented.

Use this callable once in the selected preparation/population operation, retaining
its qualified output in the existing product-detail read model for the sole05/UI
consumer. Do not invoke a shard scan on every HTTP request or rebuild the full
identifier DB. The deterministic shard rule applies to every exact barcode;
there is no hardcoded product. Full identifier-index coverage and populated
product-detail coverage remain separate. Additional shards/full-scope population
need their own exact eligible input/runtime selection, rather than a hidden scan.
The host may render typed `not-loaded` failures without hiding identifier matches;
`restricted` requires a concrete current source-use hold, not a missing receipt.

## Source-native indexed product-detail population

`offmenu.refresh.product_detail_store` adopts the exact13 five-table/one-view
`offmenu-retained-product-detail-store/1` SQL (SHA
`f85e1696fa46d3c1b268d4969fa0569534ccaa8ade209c1c523c09bbd0046632`).
It operates only on a caller57-owned **new empty private SQLite connection**;
the working scanner and validated identifier DB are not migrated or opened.

`prepare_product_detail_manifest(assets)` is metadata-only. Assets bind exact
source/release/representation, input extent/hash, expected product/profile counts,
parent identifier input/hash, original source hash, projection, citation status
and current selected rights/custody. Pending custody may be represented in a
proposal, but `ingest_product_details` refuses execution without real selected
pins and an operation-selection digest. Hashes and typed objects grant no rights.

The writer accepts `scan_asset_once(asset, consume)` from the qualified57 caller.
The callback emits `consume(packet, productOrdinal, profileOrdinalOrNone,
identifierRecordOrdinal, sourcePointer)` provisionally, then returns a verified
one-pass receipt. `scan_retained_off_product_shard` streams **all** paired OFF
packets using the existing1446 reader's schema/hash/gzip/FD checks;
`scan_qualified_native_product_pairs` reuses native qualification and streams the
USDA candidate in product/profile order, retaining raw nutrient observations.
`scan_cached_product_detail_asset` reuses either a reviewed saved OFF pair or the
existing bounded USDA cached-lookup decoder. The USDA cache caller must additionally pass the independently
selected `native_lookup_contract=IdentifierInput.contract` alongside its existing
`native_lookup_metadata`. Before opening the cache, the adapter checks the exact
contract fingerprint and original-input list against that metadata, then permits
`originalSHA256` only from contract source inputs, excluding rights/scope/clock
evidence. Archive, native candidate and lookup hashes in `assetBindings` do not
establish original-source identity. This reuses the selected contract without
requalification or opening any parent asset. The OFF cache retains its verified
paired-document original binding. A product-only cache supplies no
invented profile. None of these reads an original archive, source.sqlite or the
identifier DB. No real source/operation factory, job or new server is installed.

An asset commits only after exact hash/extent/EOF/schema/custody, source identity,
qualification and actual counts agree. A failure rolls back that asset, retains
the completed prefix and marks the generation incomplete with actual SQL counts.
There is no automatic retry, deletion or false success after deadline expiry.
The caller owns OS/aggregate-storage limits, exclusive output FD custody, final
close/fsync/hash, terminal receipt retention and independent output selection.

Full product and profile JSON are retained as separate source documents with
source-native IDs, distinct logical record ordinals, exact pointers, record hashes
and citations/unknowns. Paired profiles link only through verified producer
context. Ingredient concepts remain null/pending and never suppress source text.
Field wrappers are constructed from the selected bounded documents on read;
`fields_json` stays null, avoiding a second copy of large nutrient payloads.
Existing legacy fallback/null-collapse/quantity conversion/country mapping/basis
and derived-value limitations survive. No original JSON number-token format,
language, canonical identity, certification or missing publisher field is guessed.
For a loaded product, an absent supported key is `missing/projection-field-absent`
and retains the projection evidence hash. Explicit null and present empty values
stay distinct. Original publisher presence stays `unknown`; missing a projection
key does not prove publisher absence. An unsupplied paired profile and unsupported
image representation remain `not-loaded/representation-not-provided`. Capability
maps are specific to the selected representation: both USDA variants follow the
closed `usda_product_contract.native_schemas` product shape; both legacy OFF
variants follow the actual `normalizeOFF` used by `collect-jsonl.mjs`. USDA lacks
OFF pack/names/categories/raw-nutriment fields; legacy OFF lacks USDA serving and
data type. Unsupported wrappers stay `not-loaded`, even if an unknown extension
key appears in raw data; complete records retain that data unchanged. Tests bind
the maps to both actual schema/producer outputs rather than inventing support.

`read_product_details(connection, observations, selection=ProductDetailQuerySelection(...),
identifier_evidence=CurrentIdentifierEvidence(identifier_connection, selected_run_id, selected_database_sha256))`
uses the namespaced lexical B-tree for bounded candidates, then verifies source,
release, parent input/hash, original/native ordinal and native/source record IDs
against each complete current identifier observation. Before any detail lookup,
it checks the assertion primary key in the persisted identifier inspection view,
including the independently selected run, actual disposition and completed load
state. Missing, changed, invalid or fabricated assertions return `not-loaded`
without a bridge. A missing or mismatched evidence context fails explicitly.
It returns all exact linked
projections; multiple eligible projections are explicit ambiguity, never a first
winner. Exact bridges are returned as evidence in memory. The optional physical
bridge table starts empty rather than requiring a replay of millions of identifier
rows. No query writes, gzip scans, full DB hashes or global count scans occur.
The existing05 caller supplies both generation-selected RO held connections and
verifies their external receipts/custody. Construct the identifier evidence context
from that trusted selected receipt, never request observations. The module opens
neither DB itself and does not hash the full identifier DB. The helper checks trusted generation/manifest/operation/
identifier-DB pins, at most25 observations, candidate/VM/time/256KiB result bounds,
and clears both progress hooks on exits. Identifier verification performs at most
one indexed assertion point lookup per observation; no assertion replay is needed.
USDA scanner `originalAssetSHA256s` contains only source inputs: the contract's
rights, scope and optional clock evidence paths are excluded, as in the identifier
loader's original-lineage rule. Such evidence hashes cannot substitute for an
original-source manifest binding. Oversize/errors stay explicit; do not
convert them to an empty match or truncate ingredient/nutrient data.

The result's `sourceProducts`/observation keys/field states compose through the
existing13/05 private response route. For unambiguous pages, the sole owner can
wrap them in its existing inspected-output envelope using the returned manifest
and operation-selection pins. Existing13 composition rejects multiple projections;
preserve the returned ambiguity/variants in equivalent approved composition.
Identifier pagination and live11986 binding remain unchanged until an actual new
detail generation is selected. Index coverage and detail-store coverage are separate.

The metadata proposal lists all256 retained OFF shards and the full qualified USDA
candidate, plus a separate optional small-cache generation. Cached AF output
contains one pair, not every pair parsed by11919. Cached22 USDA products are a
subset of the full native cohort and contain no profiles. Keep them as compatible
interim data, never add them to full-cohort counts or silently rerun an identical
completed compatible generation. Actual body passes/resources remain a separate57
once-selection after current capacity/ownership checks; finite caps are stop limits,
not allocation, measured fit or full-corpus acceptance.

## Cached label sections and ingredient syntax

`product_label_sections.extract_label_sections` preserves the complete label,
hashes, code-point/UTF8 offsets, section evidence and uncertain spans.
Explicit allergen, storage and marketing statements terminate at LF, CRLF or CR
line boundaries as well as their existing punctuation/end boundaries. The exact
line separators survive in unclassified gaps rather than ingredient fallback.
Marketing claims share the punctuation boundary used by the other statements:
sentence-ending punctuation followed by whitespace/end terminates a claim while
decimal points remain within its text. Following sentences/explicit sections,
adjacent claim markers and batch codes retain their own spans and classifications.
`extract_ingredient_components` consumes only a selected ingredient span and
retains comma/bracket parent-child syntax and explicit source quantity lexemes.
Unlabelled opening text stays a candidate; bare numeric/additive fragments are not
quantities, percentage bases stay unknown and no concept/certification is created.
These optional cached derivations are not a prerequisite for full source import
and are not run by a browser/HTTP request or runtime AI.
