# Per-nutrient preparation-basis restoration custody

This is a source-code and method record, not a completed production-data receipt.

The selected bulk aligner retains nutrient values and unit/basis quantities but drops the original per-nutrient basis state. A profile-wide state is not a substitute. The approved repair reads only manifest-listed public curated OFF and USDA records on the existing read-only mount, then joins those records back to the immutable normalized package. It neither fetches new sources nor admits a culinary identity.

## Exact inputs and implementation

- Curated input manifest SHA256: `312a7f5ce7c32b81d1eb02251303a000073eea2d0b46d9ac710e09ff89dee895`; only `records/off/*.jsonl.gz` and `records/usda-files/*.jsonl.gz` are selected. Per-file bytes and hashes are checked before processing. Source-specific policy and curation restrictions remain attached; withheld source records are not selected.
- Normalized bulk manifest SHA256: `8cd8abbf28f8fac11ccb73f336a91c7a5d90fbaff6ec1c864ec7b492f13da58e`.
- Selected package schema SHA256: `89ff701460e0c9c6e27c5d5ece7bd6868f26f55fc2aedd1d85c87b4408cf1f6c`; contract SHA256: `b4fa5afb2f8cc77326299b55ccd75b93f121e807317fdc1f9953709e98faa0aa`.
- Pure restoration module: `cae8b86cbacdbf0d81b9a52bb508dadae56e29639cfd332f87fb2b71bd18566a`.
- Checkpointed two-phase runner: `24b477296d17675f7eb2ef3c674e5ae153a603afa599743161a13d0e05106d59`.
- Independent reviews: `INDEPENDENT-BASIS-RESTORATION-REVIEW.md` and `review/BASIS-RUNNER-REVIEW.json`. Selected native-input metadata is in `evidence/CURATED-BASIS-INPUT-CUSTODY.json`.

## Source and semantic fidelity

The join requires the selected native source ID, resource and original-record reference, citation identity, revision, licence, scope, original nutrient assertion ID/path and unchanged quantity digest. Each restored group records native field and record digests, source and target manifest/file pins and ordinals, source qualification flags, and the versioned deterministic rule. A native record from another source cannot be relabelled by selecting a different source entry.

Only each nutrient's own source basis is copied. Missing or null state remains unknown. Source-specific literal states remain unclassified. Existing normalized state is not overwritten, and the original quantity is not changed. The output is an additive candidate, not a source-asserted normalized replacement, calibrated confidence score, canonical preparation identity or nutrition-comparability decision.

## Durable execution and actual caller boundary

Phase one builds a local-only minimal projection index with asset transactions and immutable completion pins. Phase two scans the unchanged normalized source, produces atomic per-asset restoration sidecars, and records exact source-resource locators while already reading those packets. Full-scan completion is separate from successful source-profile matches; the final manifest reports unmatched profiles explicitly. SQLite inputs, native projections and locators are not public payloads.

The runner uses one absolute owned-output cap across resumes, an exclusive writer lock, deadline checkpoints, atomic/fsynced output and exact byte checks. Admission reserves only proven remaining growth after a clean boundary. No source index is copied or assumed complete after a terminated process.

Production completion, matched/unmatched counts, source-scoped caller results and any publication projection must come from the eventual pinned result receipts; this document does not mint them. No application activation, accepted product-to-ingredient identity, recipe nutrition aggregation, diet qualification or automatic planning follows from these repairs. Base eight-package qualification and independent publication remain separate.
