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
from native_harness_runtime import consume_boundary
result = await consume_boundary(current, native_issue,
                                binding=owner_binding, adapters=owner_adapters)
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
