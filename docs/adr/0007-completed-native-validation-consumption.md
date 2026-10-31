# ADR 0007: Consume completed native validation without replay

- Status: proposed with standard 2.3.1; adoption requires independent review and integration
- Scope: read-only evidence qualification and the existing incoming unit-review transport
- Predecessors: ADR 0005 integration authority and ADR 0006 origin-bound validation

## Observed gap

A real service-owned native coding attempt completed with stopped children,
finished lease and exact outputs. Its independently reviewed candidate passed
Engine/Windmill validation and merged through the integration controller. The
historical native-v1 consumer nevertheless requires its own Journal and pending
merge, with branch/base equal to the coding manifest. Integration used a later,
verified disjoint base. The standalone consumer supports reviewed-source stages,
not this completed native unit. These constraints cannot be satisfied by relabeling
an Engine receipt, manufacturing admission/Controller history or replaying work.

## Decision

Add an explicit `completed-native-validation-v1` evidence variant, selected only
by the authenticated source owner through an immutable ref in the reviewed
current configuration. Keep the existing native gate identity unchanged. Qualify
native admission/request/receipt, successful finished lease and output bytes.
Keep native and integration branches/bases distinct; verify ancestry and absence
of changes to native output paths between bases, exact candidate delta and Git
blobs, and canonical merge parents/tree in the current accepted source lineage.

Consume original Engine task/request and terminal Windmill result/receipt,
including the recognized fixed source-selection/Engine wrapper, equality of its
literal embedded task, the required accepted-result assertion,
command/request/runner/policy identity, stopped children and no pending
reconciliation. Bind independent exact-source review, completed Controller
binding/claim/checkpoint/observation and merge readback. The owner-approved command
is executable configuration; receipt custody does not turn an arbitrary coding
report into a validator. The current authenticated owner claim stays separate
from the immutable historical integration claim. Retain requested and observed
reviewer metadata separately, including explicit unavailable values.

The coordinator may project that completed validation directly. It never ticks
or creates a Journal, runs Engine, resubmits a job, dispatches coding, changes a
lease, or reuses a successful model turn as a new task. The fixed v2 incoming
review transport requires the same owner-selected evidence and exact original
receipt bytes. A distinct finite gateway consumes the completed packet without
Controller mutation, Git/Linear effects or inference. Existing v1 and standalone
paths retain their checks. Conflicting incoming records remain immutable holds.

## Limits and adoption

Review and focused mutation/replay tests must cover original-unit binding,
separate integration ancestry, command/job/request/receipt identity, cleanup,
finished lease, independent reviewer, Controller checkpoint and owner custody.
The positive path must create only the incoming unit review, with zero execution
or submission. Same-UID malicious actors are outside the existing private owner
boundary; neither JSON flags nor UID establish authentication.

Runtime adoption requires reviewed source pins and exact selected evidence;
source-only integration activates nothing. Unit approval is not parent closure,
application/served acceptance, billing proof or continuous recovery/refill proof.
No provider grant, new task, credentials, service, scheduler, boot enablement,
Actions or production deployment is introduced. Historical receipts and original
Journal identities remain unchanged. There are no new layout exceptions.
