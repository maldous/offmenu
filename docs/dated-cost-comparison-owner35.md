# Worker 35: NORM-09 dated cost, FX and PPP boundary

## PR 10 provider-review correction

Provider review of 1c7da6cfaed4f8ede3c3e011ec5a49cd69d8f475 reported P2
on foreign-realm rejected promises. The parent returns a blocked result but then
exits Node with an unhandled rejection: its instanceof Promise guard is tied to
one JavaScript realm. An isolated node:vm reproduction confirmed exit 1.

The first correction b2529ab15f73a2bd2c028fbf47b10b99b0cde2b5 fixed ordinary
foreign promises but SAME Worker41 found residual P2 W41-DATED35-SHADOWED-PROMISE:
an own then accessor or then:null shadow bypassed observation. The exact retained
reviewer child-process probe reproduced both strict-mode failures with getter
hits zero. That head was NOT accepted and remains preserved in history.

The successor uses the captured Promise.prototype.then intrinsic to observe
genuine native promises across realms without consulting their shadowed then
properties. Plain malformed thenables are not assimilated and their callbacks
never run. All async/malformed evidence remains denied; observation grants no
source evidence. Regression checks cover rejected/fulfilled foreign promises,
native shadowed then descriptors, plain/inherited thenables and accessor
nonexecution. Only Node builtins are used in the test closure (node:vm).
This narrow successor requires SAME41 independent exact-pin review, root binding
and provider recheck. Earlier PASS does not approve changed code; no merge or
caller activation is claimed here.

Candidate for independent review, not full NORM-09 completion. No actual UI,
provider, handler, schema, account, payment or purchase path is installed.
Production STOP, source admission and whole105 acceptance remain withheld.

## Source requirements and ownership

Read original report 01 physical page 8 (comparison purpose/denominators) and
report 05 physical pages 3–5. The source distinguishes acquisition from intake,
pack purchases from consumed amounts, CPI expenditure weights from quantities,
and date-matched FX from broad contextual PPP. Like-for-like price comparison
holds food specification/quantities constant; different basket compositions must
be compared separately. Missing values do not become zero. A rounding-level
difference does not establish a winner. Local currency, geography, period,
outlet/channel, tax, delivery, promotion and loyalty conditions remain evidence.

Read existing Worker23 source-bound pack-cost contract and current thread
handoff: it owns offer/product binding, as-sold quantity evidence, pack rounding,
fees and price-condition qualification. This module accepts already computed
cost amounts and performs none of those operations. No prior helper is imported
or adopted. Read Worker41 typed basket-measure contract and alias successor
handoff: country entries remain unresolved quantities; classification of source
measure is separate from this calculator. No source census or lexical measure
classification is performed here. These were read-only coordination inspections;
no inter-thread message or ownership release is claimed.

Only public/dated-cost-comparison-owner35.mjs,
tests-web/dated-cost-comparison-owner35.test.mjs and this note are owned edits.
Fresh locked develop fetch exited 0, base
148fec8102ee64ec6801d4df96dfeb9a946ac619. Fixed branch
feature/dated-cost-comparison-owner35-20261015 in
/home/user/src/offmenu-workers/worker-35. Earlier detached bootstrap at
abe0ddc9db357b1e8d0d61825392d6b9923352f0 and all previous review artifacts
remain retained. Main/index were snapshotted before fetch and remain protected.

## Actual exported entrypoint

`compareDatedCosts(input, {resolveEvidence})` is synchronous and transport-free.
It captures bounded own plain JSON before invoking any hook. No getters, cyclic
structures, sparse arrays, nonfinite values or coercion hooks are admitted.
Returned nested objects are detached and frozen. Source snapshots, original
costs/quantities, exact qualification bindings and provenance are retained.

Input contains view (`local`, `fx`, `ppp`), purpose, targetCurrency, cohort,
candidates and optional rates. All candidates belong to ONE exact cohort:

- Named/versioned cohort and food specification; evidenceTrack is one of
  source-price-observation, published-basic-needs or recipe-modelled. This is an
  explicit qualified classification, not an inferred source label. CPI weights,
  tourism demos, acquisition/intake conflation and alternative cohort tracks
  cannot supply a quantity by changing the label.
- Population and food state, strict calendar date YYYY-MM-DD, inclusive reference
  period containing that date, channel and identical explicit conditions. Tax
  must be included; delivery/promotion/loyalty require named conditions. Different
  regions/outlets remain explicit and must be independently source-qualified.
- Exact required specification line IDs and quantities in g, ml or count. There
  is no unit conversion, density or edible-yield inference. Decimal strings must
  use ordinary nonnegative notation, at most six decimal places and at most
  twelve whole digits. Required quantities are positive; unknown stays null.
- amountBasis is pack or consumed. Each line cost must name the same basis and
  candidate currency; a supplied pack total is not a consumed amount. No cost
  proportionality or source quantity scaling is calculated.
- denominator is basket/basket/"1", person-days/person-day/positive decimal, or
  energy/kcal/positive decimal. The latter two require consumed basis; energy
  computes cost per 1,000 kcal. No implicit person count, period, energy or default
  denominator is supplied. comparisonResolution is an explicit positive amount
  in the FINAL compared currency/metric, backed by the qualified cohort.

Candidate fields: id, geography {country,region}, outlet, channel, conditions,
date, period, currency and lines [{id,quantity,cost:{value,currency,basis},...}].
Country/currency strings do not themselves establish ISO membership, rights,
current availability or source quality. Owner evidence must establish those facts.
No candidate may change the cohort food specification, state or quantities.

## Qualification and conversion

`resolveEvidence({kind,binding})` receives a frozen detached exact binding. Kinds
are price, denominator, fx and ppp. It must return plain own JSON with status
qualified, the EXACT binding, and provenance {sourceId,version,sha256,
rights:{derivedUse:true,...}}. sourceId/version must be nonblank strings and
sha256 must be 64 lowercase hex characters. Fields do not verify themselves:
the trusted owner must obtain independent source qualification, current access/
retention/withdrawal permissions, date, cohort, precision and specification proof.
Reflecting the request as qualified, as the labelled synthetic tests do, is NOT
a production authority. Client approval/status flags are ignored. Wrong bindings,
conflicts, missing rights, hook failure and asynchronous verdicts block arithmetic.
Accidental rejected Promise hooks are observed and denied without an unhandled
rejection; they never grant a qualification.

local requires every currency to equal targetCurrency. fx permits a direct
qualified target-per-source factor on the SAME observation date and purpose
dated-price-comparison. No inversion, interpolation, chained rates or latest-rate
lookup occurs. Exactly one from/to rate must be supplied; duplicates are ambiguous,
even when the numbers agree. Rate id/version, positive decimal value, date,
direction, purpose and exact source qualification are required.

ppp requires purpose ppp-analysis, targetCurrency international-dollar and cohort
level aggregate-basket. It divides an aggregate local amount by a qualified
local-per-international-dollar factor, with named series, component, methodology,
referenceYear and exact geography. The date and entire period must share that
reference year. Geography distinguishes rates even when local currency is shared.
PPP is contextual aggregate analysis; no SKU-level, checkout or transaction
conversion, nutritional equivalence or current-price conclusion follows. Owners
must qualify whether the named component/series is applicable before using it.

## Exact arithmetic and unknown coverage

BigInt reduced rationals preserve exact decimal inputs, divisions, FX and PPP.
Results contain numerator/denominator strings. decimal is supplied only if the
result is exactly expressible within six decimal places; recurring results keep
their fraction and decimal=null. There is no automatic rounding or floating-point
Infinity. Any monetary or quantity aggregate above 1,000,000,000,000, or rational
numerator/denominator above 120 digits, blocks the cohort. Decimal input bounds
also reject exponent notation, leading-zero ambiguity and unsupported precision.

At most 50 candidates, 100 required lines/candidate and 100 rates. Capture is
limited to 100,000 nodes, depth 32 and 2,000,000 key/value characters; arrays at
most 10,000 elements. Serialized output above 8,000,000 UTF-8 bytes rejects.
Large inputs can hit those stricter combined limits before nominal line bounds.
Malformed structure throws; incomplete qualified evidence returns status blocked.

Each row preserves unknown line IDs/reasons, exact known subtotal in ORIGINAL
currency/basis, known/required line counts, and separate g/ml/count coverage.
An unknown required quantity leaves the relevant total coverage null and names
its unresolved line. Different dimensions are never summed. Known zero cost
requires qualification and differs from missing; an empty known subtotal of zero
is accompanied by zero known lines and explicit unknown IDs, never a full total.

If ANY candidate/rate/denominator/basis/aggregate is blocked, ALL complete totals
and cohort ranking are null. A complete candidate's status can still say comparable
while its total is withheld because another cohort member is incomplete. No total
across alternative candidates is produced. Complete cohorts rank only exact
observed arithmetic, not current cheapest shopping or recommended purchases.
Neighbouring amounts within comparisonResolution form conservative chained tie
groups, so a rounding-level difference does not declare a winner. No intervals,
confidence model, affordability inference or composite score is manufactured.

## Checks and remaining adoption

Focused command: node --test tests-web/dated-cost-comparison-owner35.test.mjs.
Synthetic fixtures only; they do not admit real prices, exchange rates, PPP
series, account scopes or publishers. Checks cover finite exact totals, mixed
dimensions, observed zero versus absence, all-cohort fail-closed coverage,
date/direction/rights/version/duplicate-rate refusal, contextual geography-specific
PPP, consumed denominators, precision/overflow, CPI refusal, conflict and async
qualification, input/resolver mutation, immutable output and conservative ties.
Tests import only Node builtins and the same-tree helper. No Git objects, local
corpora, dependency links, provider APIs or live quotes are required.

Existing Worker41 is the reserved different-author reviewer after its basket-alias
handback. Exact independent review is PENDING; no self-approval, normal PR,
develop merge, caller hook or production activation is claimed. Owner02/23 must
supply/adopt qualified snapshots and typed UI representation; owner41/source
owners must validate basket purpose and denominator evidence. Future live-source
qualification is separate and not performed here.

External pickup/checkpoint/log/patch receipts live under
/home/user/Documents/Codex/2026-10-15/task-2/worker35-dated-cost.
Only the three owned paths are staged. Local commit, verified private-origin
backup, independent review and authorized develop merge are separate states.
Private origin is verified with connected GitHub metadata before non-force backup;
remote SHA is independently read back. A guard refusal preserves local work and
is reported without another actor/tool or bypass. Supplied unrestricted filesystem,
network enabled and mandatory auto_review remain; named environment profile and
separate approval-policy/user configuration are unavailable. No settings changes.
