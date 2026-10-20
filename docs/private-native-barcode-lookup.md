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
