# Worker 19: reviewed-week copy proposal

Status: READY FOR MORGAN REVIEW after focused verification. Independent pure module;
no existing app, UI, auth, schema, source data or owner receipts changed. This does
not claim integration, acceptance, or release certification.

## Requirement and custody

- [P1-02](recommendation-delivery-register.json): “Reusable planning, lunchboxes,
  attendance, batch cooking and date-aware reservations”; register remains unassessed.
- [Planning scope](research-delivery-plan.md): meal and household planning row,
  including reusable weeks, attendance, lunchboxes and equipment bounds.
- Dependencies: P0-06 cooking reconciliation; P0-05 durable sync.
- Dispatch: `feature/plan-templates-20261014`, exact base
  `8652b312ce7989c5e4f2d49ae765d5d8daf5841d`. Coordinator supplied successful fresh
  origin/develop fetch at `2026-10-14T06:40:41.587837+00:00`; local origin/develop
  and initial HEAD matched. Baseline verdict: PROVISIONAL_UNQUALIFIED_INTEGRATION_BASELINE.

## Existing-source gap and bounded negative example

[menu-model.js](../public/menu-model.js) exports weekDates and planSummary but no
week-copy operation. [app.js](../public/app.js) adds individual meals (line 144)
and renders/removes/logs them (line 145). [household-model.js](../public/household-model.js)
generates one day; it does not copy a reviewed week or enforce target attendance,
equipment and lunchbox portability. Relevant menu tests cover summary, weekday
boundaries and cloud survival, not copying. Searches of existing model modules
and menu/household/journey/core tests found no template/attendance/lunchbox/equipment
copy implementation. Worker14 draft decomposition is not acceptance evidence.

Negative baseline, executed before implementation: copy a two-serving synthetic
rice meal from October 12 to October 19 retaining `cookBatchId: old-batch`, with
no stock. Expected new-week ingredient requirement: 100 g rice; actual shopping
missing list: empty. planSummary suppresses ingredient allocation whenever
cookBatchId is present. The focused regression test demonstrates both the old
naive copy and the corrected proposal without changing the summary implementation.

## Integration contract

`copyReviewedWeek({source, target, requirements, newIds, existingIds})` accepts
explicit account scope, a caller-reviewed source Monday week, at most 100 meals,
caller-supplied new identities, and explicit target bounds. It has no clock,
storage, random ID generation, transport or external calls to inject.

Every meal requires explicit member IDs and target date/slot attendance. Required
equipment and lunchbox intent are per-source-entry declarations; absent bounds
block. Lunchbox meals require an explicit portability confirmation. This concerns
portability only and provides no allergy, medical, expiry or food safety assurance.
Attendance must contain every source attendee; this slice never changes servings
or infers portion scaling. Any blocker returns no entries, preventing partial copy.

Successful output remains `needs-target-review`. Weekday offsets and servings,
recipe references, adjustments and opaque provenance/uncertainty/rights fields are
deep-copied; source is untouched. Old entry identities are replaced and cookBatchId
is removed so cooked inventory is not reused. No stock reservations or purchases
are created. ExistingIds must include all identities currently in the target plan.

Example adoption by the planner owner: construct authenticated same-account input
from profile.plan, gather current target attendance and recipe equipment/portability
evidence, supply fresh entry IDs and all current profile.plan IDs; show blockers
or the returned proposal for target-week review. After explicit confirmation,
append entries once under an owner-controlled atomic/idempotent sync operation.
Never call this directly during renderPlan or treat source review as target approval.

Owner-controlled dependencies: the planner owner integrates the review UI and
checks current recipe existence, quantities, rights, consent and household evidence;
P0-06 owner handles stock/batch/reservation lifecycle; P0-05 owner handles replay,
concurrency, account authorization and persistence. Cloud validation currently
projects known plan fields only (cloud/state.mjs line 25), so opaque metadata and
template review/bounds require an owner-reviewed storage contract before shipping.
An accountId string is a scope assertion, not authentication. Review and evidence
can become stale; the caller must recheck at commit time. No integration is shipped.

## Verification

Focused command: `node --test tests-web/plan-template-model.test.mjs`.
Actual result: exit 0, six tests passed, zero failures (2026-10-14).
Fixtures are bounded synthetic objects and write no Git repositories, files,
storage or shared state. No Git-writing fixture or disposable repository is needed.
Checks cover the cooked-stock regression, date remapping, deep-copy custody,
unknown/unavailable bounds, all-or-nothing results, account/review gating,
ID collisions, invalid dates, quantities and template limits. No heavy suite,
browser/server, provider, install, bulk job or extra worker was used.
