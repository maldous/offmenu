# Worker21 independent regional quantity review

Candidate: b086c941cc3de3c6da126e15c650f2cd544686c2.
Verdict: CHANGES REQUESTED for P2 W21-REGIONAL-F1. No adoption.

Six new counterexample tests: five passed, one errored. The eight author checks
were inspected, not repeated. Tests execute the exact immutable module in memory;
fixtures are explicitly synthetic issuers, not real source permission grants.

## P2 W21-REGIONAL-F1: malformed unit escapes the unknown contract

`convert_chain` checks only truthiness of `source.unit` (line 59), then makes
`start = (source.unit, source.basis)` and builds `{start}` for traversal (line 128).
An otherwise valid source observation with `unit=['regional-cup']` or
`unit={'id':'regional-cup'}` passes the source gate and exact synthetic hash/issuer
grant but raises TypeError: unhashable type list/dict. Unknown input should be
withheld as an explicit unknown result. This can abort a consumer batch rather
than preserve per-observation missingness. It does not create an unsafe numeric
conversion or prove an authorization bypass.

Recommendation: validate source unit as a nonempty string before constructing
graph nodes. Keep original malformed source evidence in the unknown result.
Retain both regression cases. Owner15 alone corrects source; exact-pin recheck
required before adoption. No source file was edited by the reviewer.

## Passed independent boundaries

Each context dimension (food/version, region, form/state, definition, temperature)
failed to join mismatched evidence. Edible/drained grams did not infer reverse
gross conversion. Mixed regional cohorts and unknown requirements withheld totals.
Identical independent density paths remained conflicting. Mutated result lineage
failed projection integrity. Wrong issuer/use/hash grants withheld conversion.

PDF01 A6–A7 requires explicit original quantity/state/basis, supported volume/count
conversion and unknown evidence; A13 retains qualification gates. Original PDF01
pp2–13 were read and hash-recorded in this worker's preceding quantity review;
those unchanged pages/evidence are reused, not duplicated. PDF02 p5 preserves
P0-03 uncertain density/count and actual consumption acceptance. Earlier SI-only
14b7 scoped PASS remains unchanged and does not close all P0-03.

No real regional issuer definition was selected by the author. Synthetic grants
qualify boundary behavior only. Source admission, food/version matching authority,
nutrient/metric transfer and shared importer integration remain separate. This
review exercises module/projection entrypoints, not a deployed canonical/allocation
hook. Production STOP and whole-product/PDF105 holds remain. Previous lot, intake,
recall and SI checkpoints and local recovery artifacts are preserved.
