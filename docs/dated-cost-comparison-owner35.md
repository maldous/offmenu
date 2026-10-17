# Worker35: JSON-only dated cost boundary, contract version 2

PR10 remains HELD for SAME41 changed-contract review, root acceptance and provider
recheck. This is partial standalone NORM-09, not source/feature/release acceptance.
No production authority producer, store, UI/handler, provider, account/purchasing
integration or activation is implemented. Production STOP and whole105 holds remain.

## Deliberate breaking contract

`compareDatedCosts(inputJSON, receiptsJSON, nowMs, operationId)` accepts primitive
serialized JSON strings and captured primitive time/operation context only. The
legacy object/resolveEvidence callback API is rejected BEFORE property inspection
or invocation; there is no compatibility fallback. No callable authority, Promise,
thenable, accessor or caller object crosses this boundary. The exported calculator
has no imports, source I/O, callback execution or Promise rejection handling.

nowMs must be a nonnegative safe integer epoch-millisecond value; operationId is a
nonblank bounded string. These primitives bind supplied receipt claims, not an
actual authenticated clock/session. They must eventually come from the separately
qualified owner. Caller-provided context cannot activate authority here.

Input JSON has the existing cohort/candidates/rates shape. Receipt JSON is:

```json
{
  "schema": "dated-cost-receipts/2",
  "operationId": "opaque-operation",
  "receipts": [{
    "kind": "price",
    "operationId": "opaque-operation",
    "issuedAt": 1791979199000,
    "expiresAt": 1791979201000,
    "status": "supported-claim",
    "binding": {"exact": "captured binding described below"},
    "provenance": {
      "sourceId": "synthetic-only",
      "version": "1",
      "sha256": "1111111111111111111111111111111111111111111111111111111111111111",
      "rights": {"derivedUse": true}
    }
  }]
}
```

This is a SHAPE example, not a valid source receipt. Parsed claims are NOT
verified signatures or authenticated authority. No status, admitted/authenticated
flag, source hash or rights-shaped field can grant qualification. Default output
is always `status:blocked`, `authority.authenticated:false`, `rows[*].total:null`
and `ranking:null`, even when every supplied claim matches. A complete mathematical
projection appears only in `conditionalArithmetic`, marked UNADMITTED, with
conditional amounts and comparisonGroups. Those groups are arithmetic diagnostics,
not an authoritative recommendation/ranking or a product activation switch.
`knownSubtotal` likewise carries authority `unverified-receipt-claims`.

## Exact receipt-claim binding and unknowns

A receipt kind is price, denominator, fx or ppp. Matching requires exact structural
binding, envelope and receipt operationId equal to captured context, and exactly
one matching record. Duplicates remain conflicting even if numerical values agree.
issuedAt <= nowMs < expiresAt, nonnegative safe-integer timestamps and a maximum
five-minute claimed validity interval are required. This is bounded staleness
checking of claims, not independent source freshness or a verified current clock.
SourceId/version must be nonblank, sha256 64 lowercase hex, derivedUse exactly true.
Conflict, stale/future/overlong validity, malformed or missing binding/provenance/
rights records withhold conditional arithmetic; no claim is silently promoted.

Bindings retain:

- price: purpose, complete cohort, candidateId, geography, date, period, outlet,
  currency, channel, conditions and complete exact line snapshot;
- denominator: purpose, complete cohort and denominator;
- fx/ppp: purpose, complete cohort, candidateId, geography, date and exact rate.

No client line/source status is independent verification. Actual producer admission
must establish all source rights, withdrawal/retention/access, source/version/hash,
food specification/state/quantity, comparison purpose, outlet/conditions, rate and
operation context against trusted current records. That producer is UNIMPLEMENTED.
No parameter enables it or overrides the current default denial.

A malformed receipt string/envelope becomes explicit `receiptError:malformed-receipts`
with an empty effective receipt set. Invalid request JSON/structure throws without
returning a total. Duplicate JSON keys, nonfinite values and excessive nesting are
rejected. Raw executable objects are never JSON-stringified by this module.
Unknown line IDs/reasons, source snapshots, parsed receipt snapshots and separate
mass/volume/count coverage remain visible. Missing quantity leaves required unit
coverage null, not zero. Missing evidence never becomes a complete total. Any
incomplete cohort member makes ALL conditional cohort amounts/groups null. The
outer authoritative totals/ranking remain null in every case.

## Arithmetic and dimensional contract preserved

Every candidate uses the same named/versioned cohort and food specification,
evidenceTrack, population, food state, exact quantities and units, observation date
and period, channel and explicit tax/delivery/promotion/loyalty conditions. Different
country/region/outlet remain declared claims, not inferred ISO membership or origin.
Evidence tracks are source-price-observation, published-basic-needs or recipe-modelled;
CPI expenditure weights, national availability and editorial demos cannot become
food quantities by label substitution. Whole-source admission is not performed.

Quantities use positive decimal strings in g/ml/count, identical source and cohort
notation. Costs use nonnegative decimal strings with explicit currency and pack or
consumed basis. No pack rounding, proportional consumption, unit/density conversion,
edible-yield or offer binding is supplied; existing Worker23 owns those prerequisites.
Existing Worker41 basket-measure classification/unknowns remain separate. Both owner
contracts were inspected read-only; no ownership release or source adoption is inferred.

local requires the target currency. fx uses a single direct target-per-source
factor on the exact observation date, version and purpose dated-price-comparison.
No inversion, interpolation, chained or latest-rate lookup occurs. ppp requires
purpose ppp-analysis, international-dollar target, aggregate-basket level, a qualified
future producer for named series/component/methodology, geography and referenceYear.
Conditional math divides by local-per-international-dollar; observation date and
entire period must share that year. PPP is contextual aggregate analysis, never a
SKU/checkout conversion or recommendation.

Denominators are explicit basket/basket/"1", or positive person-days/person-day or
energy/kcal. The latter require consumed basis; energy yields per-1,000-kcal cost.
No default person count, period, energy or intake inference is made. Acquisition,
pack costs and actual consumption remain distinct. comparisonResolution is a
positive amount in the final conditional currency/metric. Conservative chained tie
groups do not turn rounding-level differences into a winner.

BigInt rational arithmetic preserves exact results. Output numerator/denominator
strings stay exact; decimal is supplied only when exact within six places, otherwise
null. Inputs permit at most six fractional and twelve whole digits, no exponent,
sign/leading-zero ambiguity or implicit float conversion. Monetary/quantity
aggregates above 1,000,000,000,000 or rational components above 120 digits block.
No Infinity, imputed zero, extrapolation, confidence model or score is fabricated.

## Bounds and host containment — qualification remains held

Each JSON string is at most 2,000,000 UTF-8 bytes. Preparse depth is capped at 32;
plain capture at 100,000 nodes and 2,000,000 key/value characters, arrays 10,000.
At most 50 candidates, 100 lines each, 100 rates and 1,000 receipt records. Combined
limits can reject below nominal per-field limits. Serialized output is at most
8,000,000 UTF-8 bytes. Malformed input structure throws; absent or incomplete receipt
claims return denied/unknown evidence. Returned snapshots are detached and frozen.

The PROPOSED host boundary runs asynchronous evidence preparation outside this
calculator, before invocation. For arbitrary publisher/plugin failure tolerance,
an owner-reviewed disposable process/worker must have bounded time/output and
parent-side error/exit handling. Parent accepts only successful bounded JSON text
from an authenticated qualified producer; failed exit, timeout, output overflow,
parse failure or unavailable receipt maps to unknown. Hostile returned objects
must not be stringified in the parent. A Node vm shares process fate and is not
process containment. No global rejection listener/setting, species mutation or
publisher-object mutation is an acceptable replacement.

Only OWNED DISPOSABLE SYNTHETIC test producers are implemented here. Test parent
uses Node spawnSync, strict rejection mode in the child, 1s timeout and 32KiB output
limit. Constructor/species rejections and explicit crashes exit the child; malformed,
over-limit and timed-out outputs become unknown in the surviving parent. Successful
bounded child JSON remains unauthenticated. This proves that test containment,
not a real authority service, deployed runtime, signed store or access policy.
A production host/producer and independent current rights/source/operation binding
remain explicit adoption prerequisites. No worker/service/job is installed.

## Failure history and review evidence preserved

Original provider review on 1c7da6c identified foreign rejected promises escaping
instanceof checks. b2529ab's descriptor assimilation fixed ordinary foreign promises
but SAME41 found W41-DATED35-SHADOWED-PROMISE. ec1ddf2's intrinsic fixed the exact
shadowed-then controls but SAME41 found separate W41-DATED35-PROMISE-SPECIES:
constructor/species access can throw before handlers attach. ec1ddf2 is NOT accepted.
These versions, findings and unchanged reviewer probes remain in Git and external
recovery receipts. No old callback negative control is skipped, weakened or passed
off as fixed by this incompatible API. The selected contract instead removes all
callback execution; old callback failure evidence stays independently reproducible.

Old source hashes, source/composition reviews ddb5917/d2557a and changes-required
reviews 405df9c/a28709f remain preserved. Relevant runtime reason is documented in
ECMAScript Promise.prototype.then/PerformPromiseThen/PromiseResolve algorithms:
https://tc39.es/ecma262/multipage/control-abstraction-objects.html#sec-promise.prototype.then .
Report01 p8 and report05 pp3–5 remain the original purpose/denominator/FX/PPP,
pack-versus-consumed and CPI-versus-quantity requirements.

Focused new-contract command:
`node --unhandled-rejections=strict --test tests-web/dated-cost-comparison-owner35.test.mjs`.
New tests exercise the actual exported JSON-only entrypoint, conditional math and
all outer denial gates, duplicate/stale/conflict receipts, immutable snapshots,
callback/getter nonexecution and disposable producer exit/timeout/output handling.
Only Node builtins plus the same-tree pure helper and ESM package are needed; no
historical objects, corpus, source acquisition, install or real provider fixture.

## Delivery and adoption state

Only this note, public/dated-cost-comparison-owner35.mjs and its unique test change.
Fixed branch feature/dated-cost-composition-owner35-4693cbc3-20261015 retains all old
pins in ancestry. Main/index, previous Worker35 review artifacts, deps and owner
paths are protected. Exact local/private-backup/source/tree/patch records are under
/home/user/Documents/Codex/2026-10-15/task-2/worker35-dated-cost-json-contract.
SAME41 must review the CHANGED CONTRACT and exact successor; root then binds it
before ordinary provider recheck/eligible merge. Old PASS cannot approve this code.
No real source/issuer/store/FX/PPP/provider, customer ranking, central account,
purchasing, normal merge or production activation is claimed. Mandatory auto_review
remains; filesystem unrestricted, network enabled, named env profile and separate
approval-policy/user configuration unavailable. No controls were changed.
