# Worker 26: scoped recall applicability

## Custody and scope

One deliverable on `feature/recall-scope-20261014`, based on provisional
`8652b312ce7989c5e4f2d49ae765d5d8daf5841d`. Morgan dispatch reports successful
fetch at `2026-10-14T06:48:50.753283+00:00`; Worker 26 verified its HEAD and
branch before editing. This records supplied fetch custody, not an independently
repeated fetch or release certification. Development START is already granted.
Morgan review/integration remains required. Dataset01 retains source ownership.

Only `public/recall-scope-model.js`, `tests-web/recall-scope-model.test.mjs` and
this document are assigned. No collector, provider access, personal data, UI,
storage guidance, legal-rule engine, source-policy change or ownership change.

## Requirement and existing behavior evidence

The full relevant product-review pages 6–9 and normalization pages A10–A11
were read locally, alongside register entries and the delivery plan:

- **P2-09**, product review page 6: country notices, batch/date matching,
  source links and user review; incomplete identification yields potential
  matches and coverage must never be described as exhaustive.
- **DATA-09**, product review page 7 (source assertion contract on page 9):
  official recall references and attributed storage guidance require reuse
  and geographic review; storage guidance cannot override packaging or handling.
  This deliverable implements only a recall scope projection, not that whole requirement.
- **NORM-11**, normalization A10: valid canonical GTIN with original identity,
  market/product label version, lot/date scope; historical brand recalls must
  not be generalized. A11 requires unknowns and scoped qualification claims.
- `docs/research-delivery-plan.md` recalls row explicitly separates historical
  openFDA research from current alerts and requires regulator/event/product/
  GTIN/lot/market dates and action links.

`public/evidence-model.js:matchRecall` already handles valid GTIN equivalence,
known market mismatch, explicit all batches, lot membership and absent lot
(`possible`). Its existing global-data test covers leading zeros/all batches/
missing lot. It is unchanged and reused through `canonicalGTIN`, not copied.

Concrete missing case: `{gtin, market:'AU', lots:['A']}` matches lot A with the
same valid barcode and **no market**. It also ignores label/date restrictions
and action/evidence lifecycle. The new tests demonstrate the legacy behavior
and the new `unknown` result. A same-GTIN all-batch record must not bypass
market, label or date restrictions or promote historical/inspection evidence.

## Owner integration contract

Import `evaluateRecallScope(notice, lot, {asOf})` from the new module. This is a
pure opt-in model; existing callers and ingestion are unchanged. Source owner
must first review permissions, identity mapping, actual declared action,
scope completeness and freshness. The evaluator cannot authenticate a regulator
or infer a recall from a feed name, inspection, noncompliance, brand or keywords.

Owner-reviewed notice projection:

- `id`: retained notice identity.
- `action`: `{type:'recall', regulator, ...}`; preserve original action wording
  and links. Other/absent actions cannot establish current recall applicability.
- `provenance`: `{sourceId, recordId, url, retrievedAt, ...}`; retain licence,
  attribution, source version and transformations. Metadata is cloned intact,
  not a permission grant or a source authenticity check.
- `evidence`: `{kind:'current'|'historical', validFrom, freshUntil, validUntil?}`.
  Explicit UTC timestamps with `Z`, optional fractional seconds of **one to
  three digits**, mandatory caller `asOf`; current requires
  `validFrom <= retrievedAt <= asOf < freshUntil`, and `asOf < validUntil`
  if present. Freshness bounds are owner supplied, never guessed. Stale,
  malformed, future or absent bounds yield unknown. More than three fractional
  digits in any current-evidence timestamp (including retrieval or `asOf`)
  yield unknown, even with trailing zeros. Unsupported precision is rejected
  before comparison, never rounded or truncated. Preserve original source
  timestamp strings; do not shorten them to force admission. Historical stays historical.
- `scope`: `{gtin, markets, allBatches:true}` **or** `{gtin, markets, lots}`,
  plus optional `labelVersions` and `dateRange:{field,from,through}`. Nonempty
  exact string lists, valid GTIN strings, explicit batch scope. All-batches
  plus a lot list is unresolved. Date fields are `bestBefore`, `useBy` or
  `productionDate`, using valid ISO calendar dates with inclusive endpoints.
  Missing label/date restrictions mean the owner has established that the
  notice contains no such restriction; do not drop unparsed scope text.
- Lot: `{barcode, market, lotCode?, labelVersion?, bestBefore?, useBy?,
  productionDate?}`. Market/lot/label values require exact owner-normalized
  matches. Date types cannot substitute for each other. GS1/Digital Link parsing
  remains upstream; this module validates the resulting GTIN string only.

Result includes `scopeMatch` and `applicability` (`matched`, `not-matched`,
`unknown`), `evidenceStatus`, machine-readable reasons, notice identity and
independent provenance/action snapshots. A proven scope exclusion wins over
other missing fields; invalid identifiers are unknown rather than proof of an
exclusion. Scope matches with historical or unresolved evidence have unknown
current applicability. `matched` means only this declared current notice
matches these dimensions. `not-matched` excludes only this notice scope; it
does not establish food safety or complete recall coverage. `automaticSelection`
is always false. Preserve unknowns, original source links and user review in any
future UI; source owners must integrate and independently accept that behavior.

## Validation and handoff

Run `node --test tests-web/recall-scope-model.test.mjs`. Synthetic `.invalid`
URLs and invented source/action identifiers only; no networking, process spawning
inside tests or Git fixtures. One test-runner child, within the two-child ceiling.
Cases cover legacy gap, all scope dimensions, date boundaries/types, malformed
scope/GTIN, historical and non-recall evidence, lifecycle/freshness/provenance,
exclusion precedence and input/output isolation.

Initial candidate result: **14 tests passed, 0 failed** on Node `v24.16.0`.
No tests create Git fixtures or spawn child processes. Shared main controls
captured before editing and confirmed unchanged immediately before commit:

| Shared Git file | SHA-256 |
| --- | --- |
| `.git/index` | `4332ef16a3df2cd9032b4f099a74425a111bd2e5448e0f5066c5f3f3cb54f389` |
| `.git/HEAD` | `28d25bf82af4c0e2b72f50959b2beb859e3e60b9630a5e8c603dad4ddb2b6e80` |
| `.git/refs/heads/main` | `4b9c51c3f104ae9af331274450d8d1fa2cf3b06df913f45339abc4a5536e408e` |

Git writing commands strip inherited `GIT_*` and use this explicit checkout;
no Git-writing fixtures exist, so no temporary repository is needed. Commit
only these three paths with command-scoped Worker 26 identity. Shared main
HEAD/ref/index hashes are compared before and after. Review the immutable commit
and its parent diff; Morgan owns integration onto freshly fetched provisional
`develop` with recorded SHA/custody/review. No delivery register completion or
accepted release is claimed by this isolated model/test result.

## W10-RECALL-F1 correction

Worker 10 reviewed immutable candidate
`adf42e947b21c2d5441fcb69b683c931d726e31c` and found that arbitrary fractional
precision admitted by `instant()` exceeded the millisecond precision preserved
by `Date.parse`. This could admit future effective/retrieval instants within
the same millisecond, or treat a future submillisecond expiry as already expired.

Before modifying the model, the expanded focused suite reproduced the defect:
**15 passed, 1 failed**. The failing test retained the review's exact future
effective/retrieval inputs, plus isolated high-precision timestamps at each
gate. Existing and new millisecond controls passed. The exact high-precision
freshness/validity boundary cases are retained with the revised `unknown`
expectation: the model now explicitly admits at most millisecond precision,
not full fractional precision. Original notice/provenance strings remain unchanged.

The correction changes only the timestamp validator and its contract/tests.
Regression coverage includes `validFrom`, `retrievedAt`, caller `asOf`,
`freshUntil`, `validUntil`, excess trailing zeros, equal/one-millisecond
effective/retrieval boundaries, exclusive expiry boundaries and equivalent
one/two/three-digit fractional forms. After correction: **16 passed, 0 failed**.
Two focused runner invocations total; no test-spawned processes or Git fixtures.

The prior candidate remains the parent of a new correction commit on the same
feature branch. Morgan owns disposition and integration; Worker 10's exact
recheck of the new immutable pin is still required. Dataset01 retains source
authority. No actual caller, source adoption or safety certification is implied.
