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
