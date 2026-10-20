# Retained OFF / USDA clocks

This is an opt-in private product qualification protocol, not acquisition, a
cache-freshness exception, a real-source binder or runtime admission. Known clocks
still require a timezone-aware timestamp. Existing cache and acquisition code is
unchanged. No completion, release, filesystem or verification date substitutes for
an unknown acquisition date; no downloader identity is invented.

A reviewed application `SourceContract` may select `acquisition_clock_status=
'unknown-retained'`, `acquired_at=None` and a pinned `clock_evidence: Asset` only
for `off` or `usda-files`, native/private. A manifest flag cannot select it. The
clock asset is an additional non-parser asset in the exact bundle, distinct from
rights and scope evidence. Neither proposal JSON nor evidence JSON constructs the
trusted contract. Independent expected count/ID evidence and all existing rights,
holds, schemas, custody and semantic requirements remain necessary.

The clock evidence is bounded to 1 MiB, hashed and read before payload parsing:

```json
{
  "schemaVersion": "offmenu-retained-clock-evidence/1",
  "sourceId": "off",
  "releaseId": "exact-reviewed-release",
  "scopeId": "exact-independent-scope",
  "status": "unknown-retained",
  "originalAcquiredAt": null,
  "basisEvidenceSha256": "<SHA256 of retained clock-search evidence reviewed by binder>",
  "rightsEvidenceSha256": "<exact rights asset SHA256>",
  "inputFiles": [{"path": "data/products.gz", "bytes": 123, "sha256": "<exact original SHA256>"}]
}
```

`inputFiles` is the sorted full set of parser assets, excluding rights, scope and
clock evidence. This example is illustrative; placeholder digests are invalid.
`basisEvidenceSha256` identifies the retained historical evidence the reviewer
must inspect; it is not by itself proof or a permission grant. The independently
pinned scope evidence is a JSON object with matching `sourceId`, `releaseId`,
`scopeId` and `acquisitionClock: {status: 'unknown-retained', evidenceSha256: ...}`.
Its other independently reviewed count and ID declarations remain intact.

Candidates preserve `provenance.fetchedAt: null`; manifests preserve
`acquiredAt: null`. Both carry the exact `acquisitionClock` object. The new local
`schemas/retained-product-clock-v2.schema.json` is a clock overlay for a trusted
contract's full source-specific product/nutrient schemas, not a complete semantic
schema. The unrelated reference schema remains strict and unchanged. Clock
metadata does not invent field origins into raw source bytes.

Normalization/candidate and origin-stage versions advance to 2. New context,
contract and dependency fingerprints prevent output reuse under a different clock
contract. Old output directories and receipts remain immutable; rerun into a new
destination after review. Candidate manifests remain `accepted: false`.

## Exact retained USDA release alias

Reviewed binder code may explicitly call
`product_clock.resolve_retained_usda_release(alias, archive_asset)` before
constructing a contract and its matching source/scope evidence. The resolver maps
only `None`, `usda-2026-04`, `2026-04` or `2026-04-30` to `2026-04-30`, and only for
an `Asset` whose basename is `FoodData_Central_csv_2026-04-30.zip`, bytes are
481517495 and SHA256 is
`c33d91e5c44ddbcd71ed6038714fb648b26089b3f91fabfa3be63d96d5763a01`.
It performs no IO and grants no authenticity or source-use claim. Normal
qualification still verifies all actual bytes. It never rewrites legacy asset IDs,
manifests or receipts, guesses another monthly release, or supplies a clock.

Synthetic verification:

```sh
python -B -m unittest discover -s tests -p test_retained_product_clock.py
python -B -m unittest discover -s tests -p 'test_product*.py'
python -B -m unittest discover -s tests -p test_refresh_acceptance.py
```

These tests process generated fixtures only. Real retained data still requires a
reviewed binder, complete independent denominator/count/ID witness, current rights
and source-operation qualification, safe private capacity and accepted code.
