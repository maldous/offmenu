# One native harness boundary

`native_harness_runtime.consume_boundary` consumes the accepted component APIs
at one existing Stokowski `CurrentWork` boundary. It creates no queue, timer,
process, journal or credential route. The sole integration/activation owner
supplies installed adapters. UIF-124 owns the actual callsite and protected
configuration changes; this component does not edit that adapter or claim that
an unwired helper establishes normal runtime acceptance.

Minimum callsite, under the existing coordinator's exclusive owner lock and
after its normal validation/review continuation:

```python
from native_harness_runtime import consume_boundary, owner_adapters
adapters = owner_adapters(current, native_issue, owner_binding, selection,
                         linear_client=owner._linear)
result = await consume_boundary(current, native_issue,
                                binding=owner_binding, adapters=adapters)
```

`native_issue` is the original native issue object with `id` and `identifier`.
Absent `owner_binding` returns `status:legacy` without inspecting or modifying
CurrentWork. Old configuration, manifests, receipts and v1 readers stay intact.
The optional configuration must be root-sealed and explicitly allowlisted by
UIF-124; it must never be inferred from an issue description, branch name or
candidate JSON. The adapter must not run this from coding callbacks, read-only
views, or outside the existing lock.

## Owner binding and trusted functions

Construct the frozen `OwnerBinding` from reviewed owner configuration:

- `issue_id`, `project_id`, `owner`: exact existing native identity.
- `packet_sha256`: shared `fingerprint` of the owner-loaded packet below.
- `unit_sha256`: shared `fingerprint` of the actual existing `gate_binding`.
- `operation_id`: original transaction ID from existing publisher/metadata custody.
  A Linear transaction uses the planner's immutable `action_id`.
- `phase`: `linear`, `integration` or `release`, selected by owner configuration.

The existing unit fingerprint and owner packet are an explicitly authorized
pair. A JSON fingerprint establishes byte identity, never admission or permission.
`OwnerAdapters` contains six executable functions supplied by reviewed installed
owner code, with synchronous or async return values:

| Function | Required behavior |
| --- | --- |
| `authorize(current, issue, binding)` | Return exactly `True` only after checking the current root-sealed grant, source/config pins and permission for this exact binding; otherwise false or raise. |
| `load(binding)` | Read the exact pinned packet through existing private custody. |
| `engine(binding)` | Return the actual already-admitted Engine instance for the selected workspace, or `None` while incomplete; never execute commands in this getter. |
| `review(current, issue, binding)` | Return the original independent unit-review packet accepted by CurrentWork's existing checker. |
| `observe(binding)` | Read the existing transaction journal without effects. |
| `step(binding, context)` | Perform at most one scoped owner transaction, retaining its original durable intent, permission check and canonical readback in that same journal. |

No packet field can name Python modules, callbacks, commands to import, a token
or a credential file. The release catalog's reviewed executable arrays retain
their existing validation; this module never dispatches them. The `step` adapter
must bind `integration` to the existing scoped publisher transaction functions
(`publicationStep`/`integrationStep` as appropriate), `release` to `releaseStep`,
and `linear` to the one exact planner action. The publisher's independent source
review, exact command/receipt, source permissions and canonical API gates remain
mandatory. No general subprocess executor or whole-issue Done callback belongs
in these adapters.

`observe` and `step` return exactly `{operation_id,status,child_tree_gone}`.
Statuses are `ready`, `pending`, `unknown`, `verified`, `denied` or `failed`;
cleanup is a Boolean. Only `ready` with stopped children permits one `step`.
A thrown step may already have effected its transaction. On reentry, observe
its same existing journal first; a pending/unknown effect never becomes a fresh
operation. The adapter contract requires durable intent before mutation, as do
the existing publisher functions. This module cannot provide atomicity for an
adapter that violates that contract.

## Pinned packet and component checks

The loaded packet has exactly `policy`, `handoff`, `candidate`, `linear`,
`release`. `candidate` and `release` may be null. `handoff` is the actual shared
v1 handoff; `linear` is the existing finite Linear planner request. The optional
`release` is exactly `{summary,plan,results,catalog,evidence_root}` for the real
release qualification API. Its candidate must equal the shared candidate.
The owner selects the evidence root under its existing private read authority.
Never copy request resource declarations into an observed raw receipt.

The consumer invokes the actual CurrentWork guard, context and native unit
binding checks. Native identity, provider/admission/resource/receipt gates and
stopped descendants must qualify independently of handoff shape. It rechecks
authority and the native gate immediately before a transaction. New admission,
provider proof and execution remain the existing stage owner's responsibility.
This consumer never calls `Engine.run`, starts Windmill work or refreshes leases.

Shared validators qualify the handoff/candidate; native observation projection
retains unknown operations. The real Linear planner qualifies dependencies and
retained metadata effects. Unknown/held validation and metadata cannot advance.
For publisher phases, the consumer rechecks the actual Engine source, successful
command receipts, outputs and original acceptance bytes, including task and
handoff/candidate bindings. It then invokes the original CurrentWork unit-review
checker. Release additionally reaggregates all required profiles and exact raw
receipt/output/evidence bytes using `validate_qualification`.

After that original origin-specific reader qualifies a review, its exact head,
base, tree, branch and output hash mapping must match the Engine/handoff source
and outputs. A same-issue or same-unit review for different bytes is a hold.
For a release, those facts must cover the actual frozen candidate source and
artifacts; an earlier feature review does not implicitly cover a develop merge
or later candidate. Changed candidates require independently qualified exact
coverage through the original review route. No ancestry guess, synthetic coding
attempt or callback assertion substitutes for that coverage. The existing
publisher's independent release/candidate authority remains separately required.

The result is a bounded action/effect observation, not a new task state. It
always reports `accepted_delivery:false` and `refill_eligible:false`. The existing
final-unit consumer remains responsible for current unit disposition and refill.
A verified wrapper/transaction cannot release an unstopped child. No helper
projection changes CurrentWork state or synthesizes lease clearance.

## Verification and remaining adoption work

Use the installed pinned interpreter and coherent source:

```sh
PYTHONPATH=src:tools/delivery:tests/delivery /home/user/src/offmenu/.venv-delivery/bin/python -m unittest test_native_harness_runtime -v
```

Tests exercise actual CurrentWork admission/native receipts and the real Linear
planner at a finite boundary with fake owner/external adapters. They cover
single-action/reopen, uncertain/lost effects, denied permissions, changed native
unit/project/packet and stopped-child gates. Separate real Engine and release
API fixtures reverify acceptance/output/raw-receipt bytes without computation
replay. These are synthetic component checks, not live publisher authentication
or end-to-end runtime adoption. Root must qualify the actual protected adapter
wiring, installed closure, per-transaction publisher adapter, raw receipt custody,
recovery/readback and existing final-unit/refill behavior before activation.

## Concrete normal factory

`owner_adapters` reads `current.config.native_harness_boundaries[identifier]`,
a private `{path,sha256}` selection reference admitted by the root seal.
The selection record is exactly `{binding,packet,context}`; `binding` contains
OwnerBinding's seven fields, `packet` is a private file-byte reference, and
context is exactly:

```json
{
  "engine_root": "/canonical/private/existing/workspace",
  "engine_task": {"path": "/private/original-task.json", "sha256": "<file SHA-256>"},
  "unit_review": {"path": "/private/original-unit-review.json", "sha256": "<file SHA-256>"}
}
```

All paths must qualify through the existing CurrentWork private-root check.
Selection/packet bytes and canonical packet fingerprint are checked separately;
the actual owner map, custody and imported source pins are rechecked. Missing
source/schema/dependency closure remains a hold. Engine construction only reuses
an existing binding and accepted receipt, then the consumer revalidates original
command/source/output evidence. No new task binding, graph run or lease is made.

For Linear, the factory uses UIF-125's `NativeLinearAdapter` with the caller's
already admitted `LinearClient`; it never constructs a client or reads a key.
Observation selects the exact planner action by original operation ID, or its
exact retained binding/action in the existing CurrentWork journal. The original
adapter owns durable intent, native API write, paginated readback and uncertainty.
Metadata can execute its exact action while dependencies are unresolved: creating
a missing blocking relation is itself a metadata action. Integration and release
retain their dependency holds. Relation readback never establishes blocker
completion, coding eligibility or refill.

For publisher phases, the factory invokes only the fixed argv
`/usr/bin/node /opt/offmenu-publisher/tools/delivery/github-app-publisher.mjs --native-rpc`.
Root and ordinary uid 1000 are held before protected config access. An already
admitted publisher caller must match uid/euid/gid/egid from the fixed nonsecret
root-owned config and its sealed native-runtime association. No sudo, identity
switch, new token, user-selected executable or generic privileged route exists.
The operational cross-identity launch capability is separately owned and held.

The bounded RPC sends only version/mode and the exact operation/native owner,
unit, packet and source fingerprints. Response identity, phase and request hash
must match. The parent drains each pipe with a 64 KiB bound, uses a 25-second
deadline and actually kills/reaps its fixed invocation group on error/cancellation.
Current fixed publisher Python children share that group. Cleanup is checked
from the host, never accepted from child JSON. Unknown invocation effects retain
the original protected publisher journal; the factory never invents a retry ID.

The concrete factory consumes CurrentWork's actual
`protected-current-owner-v1` custody **dictionary**, returned by the original
`current_config` and requalified by the original `guard`. Its schema, exact field
set, runtime/source roots, current config path/hash and catalog/interpreter hash
fields must match that existing contract. Boolean `True`, arbitrary truthy
metadata and stale/malformed bindings are not custody. No CurrentWork field or
root guard is changed to accommodate the factory.

The default-factory composition regression constructs the real CurrentWork with
sealed binding/config/catalog fixtures, copies the complete native/schema/Linear
source closure into a real synthetic Git commit, and leaves constructor, source
pins, guard, native gate and default factory logic intact. Only protected kernel
file ownership/interpreter custody and external HTTP are synthetic. It uses the
actual LinearClient with MockTransport, asserts intent in the original owner
file before one native mutation, then reopens and reads back without replay.
A standalone component checkout predating UIF-124's hook may explicitly supply
`OFFMENU_TEST_CURRENT_ADAPTER=/exact/accepted/source/tools/delivery/stokowski_adapter.py`
for this composition test; coherent checkouts use their own actual adapter.
That test source selection is not a product callback/configuration surface.

## Optional fixed publisher-owner invocation client

The direct same-publisher-identity route remains the default, including its early
ordinary/root UID hold. A separately qualified host owner may opt in through the
root-sealed selection reference by adding only:

```json
{
  "publisher_invocation": {
    "version": 1,
    "closure_sha256": "<installed closure file-byte SHA-256>",
    "host_confirmation_sha256": "<actual qualified host execution/adoption proof SHA-256>"
  }
}
```

This is an optional field of `selection.context`, alongside its original three
fields. It cannot select a command, path, UID, environment or callback. A sudo
policy listing, source review or hash-shaped string alone is not host execution
approval. The client never derives or manufactures this capability from those
observations; root must qualify the actual installed closure, existing grant and
mandatory execution/adoption permission before sealing it. Absence preserves the
direct route and its existing holds.

After fresh CurrentWork guard, sealed-reference and native unit checks, the
client can call only this literal tuple, with fixed cwd `/`, closed descriptors,
minimal PATH/LANG environment and bounded pipes/deadline:

```text
/usr/bin/sudo -n -u #984 -g #976 -- /opt/offmenu-publisher/venv/bin/python -I -B /opt/offmenu-publisher/tools/delivery/native_publisher_invocation.py
```

The ordinary caller never reads protected publisher config, key or transaction
state. It requires the pinned source of the real helper's pure `validate_result`
API. The helper independently admits the preexisting protected transaction,
claim, binding and state; this client never initializes a Controller or prepares
that transaction. Root prepares through the existing fixed local-only RPC only
after installed qualification and actual permission.

The caller records its exact invocation UUID, outer/inner request, owner/unit,
packet, selection and capability association **before spawn**, in
`CurrentWork.state.native_harness_publisher_invocations` via the existing `save`.
This is bounded per-operation invocation custody, not another queue/database.
At most one helper call occurs in a constructed finite boundary. A fresh readonly
observation uses outer `invoke` with inner `observe`. Its completed readonly
readiness can permit one later boundary's step; the protected publisher still
performs its own fresh canonical checks. No second helper call is made just to
step within the first boundary.

An ambiguous/lost reply or missing original terminal proof permits only outer
`observe` of the **same UUID and original inner request**, including an original
inner `step`. The client never substitutes a new request or UUID to repair that
uncertainty. A new observer's ECHILD/process census cannot clear old children.
Only the original durable helper receipt's matching closure, request, invocation,
supervisor and kernel-stopped proof can close lifecycle uncertainty. Reaping the
caller's sudo process proves nothing about privileged descendants, and the
transport returns no cleanup assertion. Contradictory proof, capability drift,
missing receipt or lost proof remains an explicit hold.

Lifecycle `complete` is not native effect success. Null/error/pending/unknown
publisher results remain held. After a valid original durable kernel-stopped
proof, a later boundary may create a new **readonly** supervised invocation for
the same external operation to refresh canonical protected-journal facts. It
cannot replay a step while native outcome is uncertain. Verified native effects
remain bound to their original receipt and exact owner/source/unit/packet context.
All prior invocation records are retained; a finite 128-record bound holds
rather than silently discarding old uncertainty or extending work indefinitely.

Tests construct actual CurrentWork with sealed refs and source/native gates,
intercept the fixed privileged tuple without executing sudo, and run the actual
helper supervisor in disposable ordinary test processes. Positive lifecycle
receipts contain real same-supervisor kernel results. Tests cover lost readonly
and step replies, same-UUID recovery, missing original terminal proof despite a
dead supervisor, forbidden new-observer ECHILD inference, exact inner/outer
association, capability drift, unknown/null native outcomes and readonly-only
reconciliation, output/cancellation bounds and preserved direct UID holds.
These tests establish source behavior only; they do not grant or exercise actual
publisher-owner privileges, install code, read keys or mutate live APIs.

Every helper call, including recovery, saves its exact `last_request` and pending
transport state before launch while retaining the immutable original invoke
intent. Verified/denied/failed readback is reauthenticated with same-UUID outer
`observe` of the protected original receipt; caller-cached JSON alone does not
create a final-unit/refill permit. Cached readonly readiness grants no refill
and only bridges to a later helper step with fresh protected prior-receipt and
Controller checks.
