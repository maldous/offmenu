# Explicit foundation publication candidate

This source is unadopted. The pure projection adapter and origin reader require
independent implementation review before publication or runtime adoption.
Existing v1/v2 code and independently reviewed semantic receipts retain their
separate scope.

The projection adapter consumes a hash-qualified, closed producer projection. It
checks source identity, seven source-subject fields, stage-wire representation,
exact native/lexical identifier association, accepted R2 eligibility and rule
source, meaningful type relation, source-field commitments and assertion values.
It preserves structured base-material values and every selected nonexclusive
processing assertion. Unreviewed multiplicity remains an explicit unknown axis
with all alternatives retained; it does not remove an independently qualified
base/type. Unknown describes the qualified representation, not publisher
absence. No N/A is inferred.

V2's existing encoded assertion-list limit is 512 characters, and combined outer
and nested evidence is limited to 32 items. Overflow rejects explicitly; no facts
or evidence are truncated. These are bounded representation limits, not an
all-optional-facts requirement.

## Separate public namespace

Use `own-data/foundation/<releaseId>/`. The new format does not change legacy
`curated-release-ready`, `assertCurated`, Gold or full-product completion flags.
Create a reader per request; its cache and eight-read budget are request scoped.
Use the existing fixed-origin, bounded, redirect-refusing blob transport.

A fixed server selection contains `sourceId`, `releaseId`, exact `manifest` and
`policy` descriptors, `consumerCodeSha256` and `admissionReceiptSha256`.

The manifest schema is `offmenu-foundation-publication/2`, with:

- `status: phase-qualified-release-ready` and `fieldContract` equal to the v2
  foundation contract, only after actual selected-record consumer exercise.
- Actual policy/code hashes and `acceptance` containing
  `status: selected-phase-records-exercised` plus the exact qualification receipt
  hash. A prepared/internal projection does not satisfy this admission.
- `privateProviderData`, `rawSourcePayloadPublished`, `acquisitionAtRuntime`,
  `goldAdmitted`, `fullProductComplete` and `legacyCuratedAdmission` all false.
- Per-source original release, qualification hash, licence and attribution,
  together with `partitions` mapping barcode SHA-256 prefixes (2–8 hex digits)
  to bounded descriptors under the same release namespace.

Product partitions have schema `offmenu-foundation-products/2`, the fixed
`sourceId`, actual `policySha256`, and `entries` mapping each exact barcode to an
ordered array of distinct source observations. An observation has schema
`offmenu-foundation-product/2`, `id`, and the qualified adapter's `candidate`.
Only explicitly selected public fields may be exported; internal producer
projection envelopes, filesystem paths, private records and operation grants are
excluded. Preserve exact source observations rather than choosing a barcode
winner. A phase-only derivative export does not rebuild or replace the retained
full barcode index or rerun the source classifier.

Descriptors bind exact compressed bytes and SHA-256. A gzip descriptor also
binds exact expanded UTF-8 bytes. Compressed files are at most 1 MiB, expanded
files at most 2 MiB, and manifest/policy files at most 128 KiB. Split partitions
by a longer prefix when needed; do not raise guards to fit data.

The reader reassesses each returned candidate through v2. It binds cursors to
publication/policy/source/barcode/page size, returns at most 20 observations,
retains source-specific notices and never fetches an external food provider.
An unavailable selected record is not evidence of global absence. Publication
qualification, source rights, append-only preservation of the existing site,
actual deployment and application integration remain distinct required effects.
