# ADR 0008: Preserve confirmed prelaunch refusals when admitting replacement units

- Status: candidate; source review, integration and installed qualification pending
- Scope: existing Foo current-owner catalog, intake and publication boundaries
- Parents: ADR 0004 resource admission, ADR 0005 integration authority, ADR 0007 completed evidence

## Demonstrated gap

UIF-117 reached normal admission but its coding child never started. The fixed
confinement binder refused an inherited group-writable clone. Its immutable
failed receipt and failed resource lease remain valid history. The old worker
correctly refuses a retained attempt, while the original catalog permits only
one entry per Linear issue. Clearing that evidence or creating another issue
for the same outcome would disguise the failure instead of recovering it.

## Decision

Keep the raw catalog append-only. A new owner-qualified unit may append an
entry for the same issue UUID only with a typed `replacement_of` relation using
`schema: confirmed-prelaunch-replacement-v1`. The relation pins the immediately
active prior entry's canonical digest, exact receipt path/hash, failed lease and
binding fingerprint. The root-sealed catalog grants still authorize the exact
directed append edge; the relation alone grants nothing.

The read-only qualifier checks the original admission, manifest, request,
dispatch intent, resource intent, receipt and actual Pool row. It accepts only
a terminal failed confinement prelaunch refusal with `child_started:false`,
stopped children, unchanged source identity, no session, no outputs and no scope
violations. Unknown, started, cancelled or successful attempts do not qualify.
The new unit must have the same project/issue identity and owner, but a distinct
runtime, request binding and lease. Branching, skipping a generation, runtime
reuse, an ordinary duplicate or an arbitrary identity rebind stays refused.

Derive one active catalog view from the explicit chain. The normal coordinator
checkpoints the old entry, binding, task and refusal witness with the new active
binding. Original runtime files, attempts and leases are never edited or
removed. Reopening the same catalog cannot repeat the transition. Intake keeps
its prior authority/reference separately. Rearming archives the original
published metadata request and nonce as a confirmed refusal, never as an
approved review or an accepted delivery.

The new handoff, owner authority, preparation and native publication readback
must all bind the same relation. The old scope becomes reusable only for this
exact qualified replacement. All normal provider/resource/source checks,
independent review, Windmill validation, protected publication, canonical merge
readback and truthful Linear acceptance still apply.

Completed-native triggers retain ADR 0007's actual completed evidence. Their
successors requalify that evidence rather than creating an operations database
that did not exist. Live Journal origins keep the existing operation claim.

## Adoption and limits

This is a typed extension for a demonstrated refusal, not a general retry or
rework permission. Preserve legacy four-field entries and their no-rebind
behavior. Deploy code and the one sealed owner grant coherently before exposing
the new catalog entry. A previous consumer cannot interpret the new relation
and must remain fail-closed; never roll its catalog back after consumption.

Acceptance requires focused refusal/identity/lease/chain tests, legacy regression
checks, independent exact-source review, ordinary source integration and a real
fresh admission. Qualify the downstream candidate/validation/review/publisher
routes before starting that unit. A metadata publication, passing test fixture
or running service is not a useful completed coding cycle or automatic refill.
No new controller, issue, schedule, credential, model purchase, historical
worker activation, CIX execution or production authority follows.
