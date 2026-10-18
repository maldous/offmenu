# Worker46 portfolio source bindings

Assignment M-STAGING-BIND-20261018-W46 retains RW, TH, US and VN ownership.
`offmenu.refresh.worker46_bindings` supplies a deterministic metadata preflight,
source-field binding declarations and small authored-fixture integration with the
existing acceptance and field-provenance contracts. It has no acquisition path,
real source reader, executable real-source contract or admission registry.

## Run without source bodies

From the repository root, using its existing Python environment:

```sh
python -m offmenu.refresh.worker46_bindings catalog > /tmp/worker46-metadata.json
python -m offmenu.refresh.worker46_bindings assess --now 2026-10-18T00:00:00Z < /tmp/worker46-metadata.json
python -m unittest discover -s tests -p test_worker46_bindings.py -v
```

`catalog` emits declared metadata, not verified custody. `assess` limits metadata
JSON to 64 KiB of UTF-8 bytes (reading one extra sentinel byte before decoding),
rejects duplicate keys, nonfinite numbers, container nesting beyond 64 and unknown
bindings, and writes canonical JSON to stdout. It accepts no source or
output paths. Missing selected bindings are diagnosed independently. A valid
report exits 0 even when individual bindings are held, missing or stale; malformed
portfolio JSON exits 2 with a fixed diagnostic. Inspect each binding's `status`.
The outer object counts toward the 64-container nesting limit. A byte scanner
checks nesting before the JSON decoder, independently of interpreter recursion
behavior; brackets inside strings and escaped quotes do not count as containers.

The library `replay_intent(key, metadata, now=UTC, previous_identity=SHA, mode=...)`
also emits a content identity/no-op decision. It uses the shared automatic-mode
vocabulary; every mode remains offline, including force-download. It claims
neither verified bytes nor completed acquisition. Validation timestamps never
reset original acquisition age. At exactly 30 days the result becomes stale and
requires a separate qualified cache decision; no download occurs. A prior
identity only suppresses unchanged binding work; it cannot waive a hold or age.

## Applicability and immutable evidence

`SPECS` is the executable, frozen declaration catalogue. Its complete source,
release, input SHA, original acquisition, author-manifest, rights and review SHA
pins are emitted by `catalog`. Bundle input paths are future canonical names,
not assertions that files exist beneath this checkout. Release keys for retained
snapshots are local custody identities, not invented publisher release dates.

| Binding | Applicable input and state | Scope still excluded |
| --- | --- | --- |
| rw-codebook | IITA Citizen-H2D3 descriptor, DOI 10.25502/s6d7-k988/d; retained SHA 8fe362318e26a64f1b7ce93bc3b533d5004d4e204215591c1f4f5dda8db8e169 | Participant records, food/nutrient observations, canonical IDs |
| th-table1 | PeerJ 13:e19606, DOI 10.7717/peerj.19606; main article SHA 8a4d551114a33dbd31cfa434c8a8f251b3ad8213daa7053dbcff7fe6db40e8d7 | National composition coverage, supplements, numeric conversion/admission |
| rw-participants | Held: privacy, consent and secondary use unqualified | All body processing; descriptor licence does not clear participant use |
| rw-recipes | Held: Wellspring text/image use unqualified | Recipe extraction or transformation |
| us-recipes | May 2013 FNS-430, publication/credits/use/selector held | PDF recipe-body processing; public catalogue access is not a reuse grant |
| vn-composition | 2017 catalogue only, qualified primary dataset not held | 403 bytes, lead counts or custody labels cannot stand in for a dataset |

Retained authority root (outside the repository):
`/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables`.
Source pointers are `owner-46/RW/reviewed-source-binding.json` (SHA
201cbf7395aa6e4e013dade718a309968450c417311ed324a4689e00bc360af3)
and `owner-46/TH/reviewed-source-binding.json` (SHA
e01795b9691fa8fa3bc2470cc054167f567dd8e8e63d5c5e25c60a07fef06906).
Their exact independent review is `owner-19/reviews/author46-result4015/review.json`
(SHA dbc7aee63006bbb70743b37c010e087174c831be2780cf137dd0dbb0ea674f3b),
result4281 with Gateway4305. It covers the retained 102 codebook metadata rows
and 35 experimental table cells only. It does not review this new code package.

## Field fidelity and authored fixtures

RW declarations preserve 19 ordered column names, string/empty states and logical
data-record ordinals 1–102. CSV ordinals are logical records, not physical lines.
TH selectors use global table row 3–9 and data column 2–6, mapped explicitly to
tbody row 1–7, sample codes A–E and the corresponding second header row. Nutrient
and unit strings derive from the row label; mean/SD/group/marker lexemes derive
from the same cell. Lexical components must agree with the declared cell string.
No locale repair, fill-down or conversion occurs. This binding grammar is a
bounded source-envelope declaration, not a general HTML parser.

Units remain Kcal/100 g, g/100 g and mg/kg; zero remains a string zero, missing
note markers remain null. Wet/dry/edible basis and canonical IDs remain null.
Every datum has a source, derived or policy-constant origin using the shared
`field_origin_errors` convention. A policy hash explains null/role constants;
it is not source evidence or permission.

`authored_fixture` accepts one to four fictional envelopes for RW/TH only. It
deep-copies caller data and constructs fixture-prefixed source/release IDs,
authored input bytes, rights/scope evidence and a `SourceContract(fixture=True)`.
The shared qualifier checks inventory/hash/schema/count/identity and field origins;
the portfolio semantic callback additionally compares every field and origin to
the authored input declaration. Fixture results are accepted-fixture-scope only.
The helper does not process the retained real records, confer rights or change
coverage/gold state. Shared schema/custody/hold failures remain intact.

## Integration boundary and next dependencies

Proposal base: abecb99ee1125730ccbc2824b6ec49ffc5cc4302, verified by integrator00
result5798. Recheck provider develop and immutable candidate at delivery/review.
Worker46 owns only this module, its tests and this document. Shared core remains
unchanged; integrator00/Morgan owns shared interfaces and review scheduling.

No generic pure private-cache planner exists at this baseline. The Wikibooks
`core.cache_policy` and registry-only `plan_fixture` must not be spoofed;
`CachedAcquirer` performs I/O and may fetch, so is not invoked here. A centrally
reviewed pure planning interface and a separately selected source-specific reader
are dependencies for real execution. Current metadata intent does not replace
either. Source-use/privacy authorities own RW/US clearance; the VN custodian must
supply a qualified primary release (owner52 result5078 says NOT_HELD). TH method
proposal and mapping require their own selected review. Preserve all source,
403/private, Finland/Frida/native NO-FR, security, production/CIX and DEV7645 holds.
No country is complete, no source dataset is newly downloaded, and no gold record
is admitted by this package. Independent review and Morgan's integration verdict
remain necessary before integration; Worker46 retains correction ownership.
