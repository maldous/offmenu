# Worker52 source-input binding proposal

Selected task: M-STAGING-BIND-20261018-W52. Baseline is accepted develop
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. Pending PR42/handover is not this
baseline. Ownership is confined to `portfolio52.py`, `portfolio52_bindings.py`,
the focused test/fixture and this document. Shared core is unchanged.

## Executable interfaces

`python3 -m offmenu.refresh.portfolio52 --now 2026-10-18T00:00:00Z` emits a
canonical deterministic JSON metadata proposal. Exit 2 is expected because RS/SS
remain held. `--stdin` accepts at most 65,536 bytes, with exact packet fields
`inputs` and optional `previousKeys`. It accepts metadata values, not file paths
to load. Duplicate keys, nonfinite numbers, unknown fields/countries, unpinned
identity or attempted hold/time changes fail closed. Each known country's
missing/malformed/held/stale outcome is isolated. Nothing fetches or opens raw
paths. No force-download flag exists.

`plan_portfolio()` uses the original receipt acquisition timestamp for the
30-day boundary. Last validation time is separately reported, never resets that
age and cannot be replaced through input metadata. At or beyond 30 days it
returns `source-stale-review-required-no-download`. An unchanged proposal key
returns replay `no-op`; this is a metadata-proposal no-op, not proof that real
candidate bytes were reverified. Credit, scope/holds, retained content pins and
origin declaration changes invalidate that key. Diagnostic time and last
validation time are not build inputs.

`bind_literal(country, literal)` is a pure binding of an already-parsed
MX/SG literal record supplied by a reviewed caller. It does not run a country
parser, read source bodies, locate retained files, convert values or claim
source/candidate byte verification. It rejects RS/SS. The existing retained
parser is not copied or executed. The proposed envelope uses the shared
singleton-record JSONL serializer and generic `field_origin_errors` validator.
`observation_schema(country)` supplies the full envelope schema, and
`functools.partial(observation_errors, country)` supplies the source-specific
semantic/selector hook for a future reviewed `SourceContract`.

Original and retained projection pins are separate. MX's labels, durability and
weight lexemes link to A/B/C cells in `xl/worksheets/sheet1.xml`, `Table 1`
rows 3–447. Source grouping is preserved; headers/total are excluded from this
proposed observation projection. Historical 448 source rows are not an accepted
445-record projection count or independent ID inventory. Ponderador is expenditure
percentage, not a price, quantity, ingredient identity or sum across groups and
items. Null/zero lexemes stay distinct; formulas are not evaluated.

SG type labels and value lexemes link to exact `/result/records/{index}/...`
pointers. Year is explicitly a derived JSON object-member name, not the numeric
value at that pointer. `na` remains literal, with unavailable/inapplicable nuance
unknown. Number is an end-of-period aggregate count, not entity identity or flow.
2006/2019/2020 changes and nonadditivity notes stay in the metadata proposal.
No actual SG rows were loaded or projected for this task.

## Evidence and source boundaries

`portfolio52_bindings.py` contains the exact original/release, source receipt,
validation, retained candidate and B03 rights/semantic metadata paths and hashes.
These are **recorded custody pins**, not fresh raw-body validation. The recorded
original acquisition times are 14 October 2026 UTC; later validation times are
kept distinct. Raw data stays on the selected local executor. Credit text is retained from B03 evidence;
no new publisher terms or licence grant is inferred.

MX/SG report `binding-ready-pending-review`, while `datasetExecutionAllowed` and
`accepted` remain false. Their pending independent staging-scope decisions are
explicit. RS is private source-use scope held; SS is inspection-only with scale
erratum and numeric-use evidence not held. Explicit HTTP403/404, Finland/Frida,
native NO/FR crash, credential, privacy, production/CIX and DEV7645 holds remain.
Counts/types here do not establish required whole-country coverage.

## Integration proposal for the product integrator

No shared interface change is needed to review or consume this package. Do not
add production ADMISSIONS or global routes in this patch. After designated
independent approval, use the existing shared `SourceContract`, `qualify`,
`accept`, `CandidateArtifact`/`endstate_handlers` and serialization interfaces:

1. Bind both the original and retained projection bytes, evidence files and
   exact inventory as independently reviewed `Asset` inputs. Body verification
   is a later authorized operation, not performed by the metadata CLI.
2. Supply reviewed `retain/parse/transform` decisions, independent projected
   count/sorted-ID digest, exact private native scope, schema hash, semantic
   callback policy and approved code identity. Never construct these decisions
   from a manifest or CLI flags. Current production values are missing.
3. Give the reviewed projection caller the generic resource/isolation boundary,
   serializer and shared qualifier. Select acquisition/normalization/global
   bindings separately. Missing callback/contract stays unsupported. Do not
   mistake this proposal for an installed shared execution adapter.

The generic accepted-develop `core.cache_policy`/`policy.plan_fixture` interfaces
are tied to their registered historical/fixture sources; calling them for MX/SG
would report the wrong source identity. This portfolio therefore provides a
pure metadata-only age diagnostic with identical 30-day/no-download boundary,
not a copied cache/acquisition engine. Any future generic source-aware policy
extension belongs to the product integrator and must preserve the automatic under-30-day
zero-download invariant. No shared change is included or required now.

Typed remaining blockers: application-owned scope/rights and independent
inventory approval (the product maintainer/designated reviewer); source-body execution selection
(the product maintainer); RS use and SS authoritative scale/use inputs (recorded source owners);
actual production cache/refresh/isolated qualification wiring (the product integrator after
selection). Public documentation already retained resolves the selected MX/SG
native meanings; unknown canonical mappings are not papered over with new data.

## Verification

`python3 -m unittest discover -s tests -p test_portfolio52.py -v` covers authored
literal and metadata fixtures only. The five small named cases include valid,
missing, held, malformed and stale inputs. Selector/pin/identity/formula drift,
year-key derivation, null/zero/na preservation, exact 30-day boundary, forbidden
timestamp/hold overrides, deterministic CLI/replay and peer-isolated diagnostics
are exercised. Existing generic field-origin and serialization functions are
used directly. An authored cell witness and independently pinned fixture-only
rights/scope/projection assets also exercise shared `SourceContract`, `qualify`
and `accept`: success is `accepted-fixture-scope`, held/missing assets fail.
No real-source fidelity, production acceptance, refresh or
whole-country completion is claimed by synthetic tests.
