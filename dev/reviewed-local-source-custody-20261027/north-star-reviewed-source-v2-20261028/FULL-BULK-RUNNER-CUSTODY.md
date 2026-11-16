# Full bulk North Star additive runner

This additive lane reads only the immutable normalized bulk package, not raw upstream food blobs. It leaves all original eight packages and independent global qualification unchanged.

- Input manifest byte SHA-256: `8cd8abbf28f8fac11ccb73f336a91c7a5d90fbaff6ec1c864ec7b492f13da58e`
- Selected schema: `89ff701460e0c9c6e27c5d5ece7bd6868f26f55fc2aedd1d85c87b4408cf1f6c`
- Selected contract: `b4fa5afb2f8cc77326299b55ccd75b93f121e807317fdc1f9953709e98faa0aa`
- Independently reviewed core ruleset2: `fee258de07319fd19c0032701ea2731afabc1f560eb69c80f111088c65cf0509`
- Actual manifest-only read at 07:09 UTC: 9,800 source assets; 9,797 packet assets; 9,796,656 packets/resources; 137,295,959 assertions; 2,915,727 relations; zero translations. Maximum compressed packet asset: 1,884,417 bytes. Packet assets total 13,880,627,503 bytes.

## Execution design

Four bounded workers derive deterministic per-manifest-asset candidate sidecars. Input assets are verified against exact bytes/hash; schema checked with the already-installed Rust validator; core2 preserves original quantity, source metadata, preparation unknowns, exact units and alias candidate status. No AI calls or runtime external lookups occur. Per-shard output and receipts are committed atomically. Resume verifies exact selection, code, contract, input and output pins. Empty candidate packets are omitted.

A local-only SQLite index exercises the explicit source+release+identifier namespace+lexical string to typed FoodProduct to source-declared profile to nutrient-context paths. Ambiguous lexical keys are not merged; missing revision, invalidated identifier, incompatible endpoint type/scope/source-release do not count as resolved consumer paths. Leading zeros remain strings. Counts are candidate corpus coverage, not accepted identity, calibrated confidence, public rights admission or live app query coverage.

## Publication boundary

The final manifest `files` allowlist contains only `shards/NNNNNN/derivations.jsonl.gz` with exact bytes/SHA256 and nonempty sidecar-packet count. SQLite, query-index gzip, checkpoint receipts, selection and progress are local-only. The output keeps `candidate-not-admitted`, `publicationEligible:false`, unknown confidence and separate exact base dependency pins. A publisher may issue a separate reviewed public-candidate publication receipt without changing those semantic assertions. Static derived namespace: `/common-data/derived-releases/north-star-structural-v2-20261028/`. No consumer wiring is implied.

## Review/execution status

Twelve focused runner tests pass locally. Independent runner review requested from the existing core reviewer. No full Foo job had been submitted when this note was created. Final run receipt and actual counts must supersede this preliminary status.

## Reviewed execution update — 07:28 UTC

The independent reviewer approved full runner `3adc476be2a6694d62c76bb4d539f0fc698810fd3b942dc9ae501e940efde7a1`; written review is `INDEPENDENT-FULL-RUN-REVIEW.md`. All 50 then-existing tests independently passed. Code staging succeeded under durable logical job `north-star-full-code-001`; actual Foo bytes and jsonschema_rs 0.58.6 were checked. Full job `north-star-full-bulk-001` / Windmill UUID `01a18161-828b-8e41-a74a-78886a2f9e31` was admitted and started 07:20:14 UTC. At elapsed448.404s: 1,734 of9,797 shards,1,734,000 packets,5,090,224 candidate contexts,315,284 structural projections,318,139 unit-alias candidates,2,245,621,596 committed shard/receipt bytes. This is progress, not final consumer coverage.

The 32GiB budget is a sampled owned named-output budget and admission reservation, not a kernel-enforced transient-disk cap; SQLite can unlink open temporary files. The 70GiB statvfs reserve still measures actual free-space pressure. The diagnostic consumer index is scoped specifically to the pinned bulk producer's single-resource/single-citation packets (selected `align-bulk-food-common.py` constructs every resource/assertion/relation from the one citation). Generic reuse on arbitrary merged multi-source packets requires additional context-to-resource source binding. The independently reviewed current input scope does not warrant interrupting the admitted immutable run.
