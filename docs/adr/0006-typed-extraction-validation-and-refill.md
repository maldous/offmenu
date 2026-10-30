# ADR 0006: Reviewed extraction validation and finite refill observations

- Status: adopted in standard 2.3.0 through reviewed integration; independent source and real WFP mapping/import validation retained
- Accepted control baseline: `7780c8602b52e9f2fc7e6a38e5d08d8ad74f09e1`, standard 2.2.0
- Scope: existing Stokowski operation/stage/worker interfaces and private receipts
- Predecessors retained: ADR 0004 resource admission and ADR 0005 integration authority

## Concrete gap and decision

The independently reviewed WFP extraction at
`c749b5cbf85e80f77788475fd6605787d3565597` maps four retained source files into
the current layout without changing their bytes. It has local layout/import
acceptance but no native coding attempt. The previous stage requires a native
coding receipt and supports only the canonical `/offmenu` delivery suite.
Neither inventing a coding receipt nor validating another checkout is valid.
The required bound Windmill validation remains required.

Add a separately typed reviewed-extraction origin to the existing finite stage.
An owner-supplied immutable admission binds original source identity, old-to-new
mapping, file hashes and independent exact-head review. Check the declared
service-owned checkout's exact head/branch, clean source, base ancestry and
before/after hashes. Reject missing, stale or conflicting admission/review.
The stage consumes independent evidence; it does not issue independent acceptance.

Use a fixed mapping/import profile, not candidate-supplied arbitrary commands.
Materialize control validators from the same immutable accepted base and execute
them against candidate imports. The installed shared interpreter may retain its
canonical path; candidate source/tests must come from the candidate checkout.
Keep the existing deployed dispatcher/bridge and resource admission policy.
No dispatcher deployment, credential or integration-gate relaxation is introduced.

Keep v1 identities and command bytes compatible. A new origin/profile is a new
binding, not an upgrade of an in-flight operation. Persist intent before submission,
reconcile the same job after uncertainty and require original backend job,
command, runner, policy, output and stopped-child evidence. Cancellation never
means only cancelling a visible API wrapper.

## Execution and refill records

Capture task fit, requested model/effort/provider route, resolved observation or
explicit unknown, parent runtime/attempt, lease/job identities and requested
resources separately from observed samples. Current coding requests
`gpt-6.1-sol`/`medium` through the existing ChatGPT session; unresolved model
identity stays unknown. Affinity and sampled RSS/process counts do not prove a
kernel quota or guaranteed provider entitlement.

At existing completion/dependency boundaries persist one ready-refill observation
from the admitted manifest, actual overlapping leases, resource snapshot and
provider-proof freshness. It is provisional: final existing admission runs again
before execution. No reservation, queue, timer, dispatch or manager is created.
No admitted ready work is not a global statement about Linear. Unknown effects,
cancellation, stale/missing proof and scope overlap remain reasons to defer.

## Proof, continuity and adoption

The useful proof is one bound validation of the actual WFP extraction, then
checkpoint/journal reopen without duplicate computation. Preserve its unchanged
nine-fixture-test acceptance. Mapping/import checks are not WFP acquisition,
normalization, country completion or data-use permission; source/data holds remain.

Task sends and one inspector returned backend `UNKNOWN` while reads/Foo worked;
a later supported same-owner send succeeded after readback, cause unknown. One
cloud read rejected native source placement format 3. These facts do not prove
that optional settings caused/repaired transport or that switching owners is safe.
Unsupported voice, approval and same-turn interfaces remain unsupported. This
proposal does not promise uninterrupted supervision.

Adoption requires independent review of immutable source, focused tests,
accepted-base control validation and the sole integration owner's transaction.
The accepted integration policy still requires bound Windmill, independent review
and canonical readback. The publisher/package, schedules, held data, CIX and USF
are outside scope. Capacity stays 8 coding / 16 service / 32 admitted jobs / 64
declared subprocesses per job; choose actual workers for the selected commands.
