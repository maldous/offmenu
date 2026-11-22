# ADR 0013: Explicit merge-only existing PRs

- Status: preparation approved; amendment and controller candidate, not adopted
- Repository standard: 2.5.3 candidate; predecessor source: `349dbf9ff37d5bf9de15695d70391234b0f6f8ee`
- Scope: issue association in the v4 connector-owner existing-PR lane only

## Problem and decision

PR 222 repairs reproducible build/test failures on accepted develop. No existing
current issue accurately covers that complete repair. Creating or borrowing an
issue merely to satisfy `UUID(issue_id)` would misstate the outcome. ADR 0005
requires an issue association, so removing it requires an explicit amendment,
not a silent schema relaxation. The user approved preparation of this amendment
and a bounded bootstrap proposal; that approval does not execute the bootstrap.

Permit exactly one new shape alongside unchanged issue-bound v4 bindings:
`version: 4`, `integration_mode: "merge-only"`, `issue_id: null`. The issue key
must be present. A non-null issue or an unknown mode is rejected. Versions 1 and
2 retain their mandatory issue and existing semantics. Project ID and full-issue
acceptance pins are forbidden in the merge-only binding, even when null.

The mode is part of the immutable binding fingerprint. No default or null is
inserted into old records. Old bindings, fingerprints, claims, checkpoints and
policy-adoption objects are not rewritten. The original integration-policy v2
bytes and adoption record remain unchanged; their owner must still match the
actual authenticated logical publisher role. This amendment changes no native
v2 publisher configuration or release binding.

## Effects and operating contract

The existing Controller and repository-wide lock admit each new transaction.
Preceding pending/unknown effects still block admission. Historical immutable
claims remain; only normal admitted active-pointer progression is permitted.
The selected source, head, base, tree, accepted policy, independent review,
validation, output hashes, cancellation and normal GitHub protections remain
required. Cloud validation still requires an independent exact-source scope
verdict. There is no new credential, root, scheduler or deployment permission.

For merge-only, observations containing `linear` or `full_issue_acceptance` are
quarantined. Canonical merge readback terminates at `merge-verified`, never
`accepted`, and emits no metadata action. Linear outcome and Linear-refusal
reauthorization calls are rejected. A stored Linear effect/action or `accepted`
state for this new mode is quarantined rather than resumed as legitimate work.
Pre-publication bindings remain issue-bound; this mode cannot create Linear
issues or publish PRs. It only admits an already existing PR.

The authenticated gateway caller derives `integrationMode: "merge-only"` from
the pinned binding when calling `advanceIntegration`. The gateway needs no
Linear adapter for that mode and refuses any unexpected `update-linear` action
before invoking one. Historical callers default to `issue-bound` and keep their
existing behavior. Python `controller.step` still maps to `Controller.run`,
`outcome` to `record_api_outcome`; status is not a claim-acquisition preflight.

## Verification and compatibility

Use offline graph/checkpoint tests for the actual no-issue lifecycle: intent,
unknown API outcome, canonical readback, refusal of Linear fields/effects,
stale source/owner/policy, lock contention and unresolved predecessor admission.
Prove an issue-bound verified predecessor's original files remain unchanged and
its normal successor uses the same lock/root. Preserve a fingerprint captured
with the accepted controller and exercise issue-bound pending restart plus the
existing integration/conditional-validation/gateway tests. These are synthetic
operating-path tests, not live admission or integration receipts.

## Bounded bootstrap proposal, not executed

The accepted controller rejects the new binding shape. This candidate cannot
qualify or authorize itself, and the initial ADR 0011 bootstrap is not reusable.
The authorized policy owner must separately approve one concrete immutable
amendment/controller candidate and its exact independent review/validation
evidence for a finite no-issue bootstrap. Retain that authority privately with
the exact head/base/tree, changed paths, actor set and operation identity.

The proposed bootstrap is one owner-supervised existing-PR integration using
the independently reviewed candidate's controller from a pinned isolated source
closure, authorized specifically for that finite operation. It must use the
existing repository-wide root/lock and real predecessor admission, original
policy adoption, fresh authenticated observations, ordinary protected GitHub
merge, uncertainty reconciliation and canonical readback. Authorizing this
controlled exception must explicitly permit the selected candidate controller
for this one bootstrap; no such authority is claimed by this document.

No old adoption record is relabelled and no issue UUID is fabricated. If the
actual helper cannot safely execute that exact bounded exception under its
existing permitted capabilities, report that precise implementation/permission
gap rather than copy claim state, switch roots or invoke the native v2 publisher.
Only after accepted source and effective helper/controller readback may normal
merge-only candidates use this amendment. Reconcile PR 222 and later PRs to the
then-current accepted base with appropriate exact-source evidence; old-base
validation does not automatically validate a rebased candidate.
