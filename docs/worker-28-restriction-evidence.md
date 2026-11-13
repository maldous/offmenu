# Worker 28 restriction evidence — ready for the product maintainer review

Custody: branch `feature/restriction-evidence-20261014`, exact base
`8652b312ce7989c5e4f2d49ae765d5d8daf5841d`. Dispatch supplied the successful
origin/develop fetch receipt at `2026-10-14T06:40:59.087726+00:00`; local HEAD
and origin/develop were checked against that SHA. No additional fetch performed.
Baseline verdict: `PROVISIONAL_UNQUALIFIED_INTEGRATION_BASELINE`. Development
START already granted; this result is neither integrated nor release-certified.

## Requirements and demonstrated gap

Dependencies: [DATA-05](recommendation-delivery-register.json#L399), approved GS1
supplier/product identity feeds; [ENRICH-04](recommendation-delivery-register.json#L1043),
scheme/certifier/site/product/lot scoped certification evidence. Both register
entries are unassessed; this adapter does not satisfy their data acquisition or
independent acceptance obligations. Worker 14's proposed decomposition was not
used as acceptance evidence.

Existing `public/evidence-model.js:19–27` exports `qualify()`. Its filters at line
21 inspect subject, market, status, match and dates but do not inspect lot/menu
scope or call `admission()` (lines 3–16). The first new test supplies a verified
halal assertion for lot A of product `supplier:product:001`, while the actual
selected lot is B. The existing evaluator returns `pass`; the adapter returns
`unknown`. This is a concrete missing binding, not a replacement evaluator.
Existing focused tests in `tests-web/global-data.test.mjs:14–16` cover admission,
qualification and recall individually, but not this composed binding.

`public/household-model.js:8–12` evaluates culinary ingredient identities and
leaves package checks as reminders; it does not consume actual package claims.
`cloud/catalogue.mjs:19` is an existing evaluation caller that could adopt the
adapter under its owner's control; it currently invokes `qualify()` directly.
No existing caller or file was changed.

## Integration contract

`packageRestrictionEvidence({rule,target,evidence,policies,owner,consent,market,now})`
is synchronous and pure, with no ambient clock, storage or transport. Inputs
are owner-reviewed assertion DTOs compatible with `qualify()` plus explicit
`sourceId` and `scope`. This DTO is an adapter boundary, not a new persisted
schema or a normalization of raw provider labels.

Target requires account `owner`, exact source-namespaced `subject`, and kind:

- `package`: assertion scope must be `package` with the same subject.
- `lot`: exact, nonempty `lotCode` must also match the assertion scope.
- `menu`: exact, nonempty `menuId` and `menuItemId` must also match.

Each assertion requires original namespaced `id`, `sourceId`, matching account,
explicit market, verified identity, value, validFrom/validUntil/freshUntil and
exact scope. Missing/invalid/stale dates, foreign scopes and denied dependencies
are withheld. Policies are keyed by sourceId; `admission()` must allow both
`display` and `derive` in the private account and market. `derive` is the explicit
permission this adapter requires for its computed result, not a claim that any
provider grants it. Certification passes additionally require schemeId and
certifierId. Contradictory admitted values remain `conflict`. Rule operators are
explicit `include` or `exclude`; at most 200 assertions per call.

An existing caller can replace its direct evaluation invocation with:

```js
const result = packageRestrictionEvidence({
  rule: reviewedRule, target: selectedActualTarget,
  evidence: reviewedScopedAssertions, policies: reviewedSourcePolicies,
  owner: verifiedAccount.id, consent: accountEvidenceConsent === true,
  market: selectedMarket, now: injectedClock()
});
```

The source/data and caller owners must implement that mapping and attest actual
identity, scope, policy and consent custody. DATA-05 identity feeds and ENRICH-04
scheme/certifier/site-to-product bindings remain their integration dependencies.
Site, organization or concept assertions cannot be promoted to package claims
by this adapter. Upstream owners must explicitly resolve those bindings.

The output retains selected source assertion IDs; no input is mutated, and
quantity/unit fields are neither converted nor inferred. It always sets
`automaticSelection:false`. A `pass` is only a scoped rule evaluation; callers
must retain independent household checks, uncertainty, certification review,
cross-contact checks and their own menu selection gates. No medical safety,
allergy safety, nutrition equivalence, expiry of food, ownership, purchasing
authority or publication rights are established.

## Verification and custody limits

Checks run (two focused test invocations; no broad suite):

- `node --test tests-web/package-restriction-evidence.test.mjs`: initial eight
  checks passed before tightening derived-use and required-date admission.
- `node --test --test-name-pattern='negative baseline|exact binding|no concept|package and menu|account, consent|invalid, future|conflict and negative|bounded input|rights admission|unknown, expired|GTIN' tests-web/package-restriction-evidence.test.mjs tests-web/global-data.test.mjs`:
  final 11 checks passed, zero failures (eight adapter and three existing tests).

Bounded synthetic fixtures only; no providers, servers, Git-writing fixtures,
installs, corpora, extra workers or agents. Focused checks are recorded with the
result. Unit coverage demonstrates this independent adapter slice, not shipment.
Only the three reserved new files are eligible for this commit. Shared common
directory identity, main checkout HEAD and main index hash are checked before
and after commit; the worker's own branch/index necessarily change on commit.

Completion status: **READY FOR MORGAN REVIEW**, pending owner integration and
independent acceptance. Worker 28 returns idle after the immutable result.
