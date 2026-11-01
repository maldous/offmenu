# Native Linear metadata executor

`native_harness_linear.NativeLinearAdapter` consumes the finite actions from
UIF-123's `linear_delivery.plan_delivery`. It uses the already admitted
`stokowski.linear.LinearClient` instance and its `_graphql` transport. It does
not load a credential, construct a client, retry transport, create a queue or
change workflow state. Only the root's normal admitted owner can call it under
the existing `CurrentWork` exclusive lock. Source delivery does not authorize
live Linear writes or installed runtime activation.

## Installed factory interface

```python
adapter = NativeLinearAdapter(existing_linear_client)
transaction = await adapter.observe(current, binding, action)
transaction = await adapter.step(current, binding, action)
```

Both methods return the runtime's exact transaction shape:
`{operation_id, status, child_tree_gone}`. `status` is `ready`, `unknown`,
`verified`, `denied` or `failed`. This adapter starts no child process; its
`child_tree_gone: True` concerns this metadata operation only. Coding/validation
child cleanup remains with its original owner.

`binding` is the root-selected frozen `OwnerBinding`, with `issue_id`,
`project_id`, `owner`, `packet_sha256`, `operation_id`, `phase` and `unit_sha256`.
Its phase must be `linear` and its operation ID must equal the exact action-body
fingerprint from the planner. The adapter checks the bound current owner,
project and active issue, action kind/fields and milestone identity. It rechecks
the current guard and stopping/read-only state across read boundaries.

The outer `OwnerAdapters.authorize` and `consume_boundary` must qualify the
actual sealed owner custody, packet and unit binding before these methods run.
A frozen Python value alone is not authority. The factory selects the exact
operation's action from the pinned plan for `observe`; `step` receives
`context['action']`. No callback, client factory, permission or module name is
read from issue JSON. The same frozen action remains available on reconciliation.

## Existing custody and effect boundary

All records remain in
`current.state['native_harness_linear'][binding.operation_id]`, persisted using
the ORIGINAL `CurrentWork.save`. Each retains the exact binding and action,
status and bounded readback identifiers. No database or replacement tracker is
introduced. The caller must hold the existing owner lock throughout the call.

A new action first obtains complete native readback. If already present, it
records verified observation without mutation. Otherwise `step` saves `pending`
intent before its single mutation. Failure to persist intent prevents that call.
A timeout, cancellation, crash, malformed response or lost reply never proves
absence. Any retained record, including `pending`, `unknown`, `failed`, `denied`
or formerly `verified`, permits readback only. Missing effects are held; even a
later deletion cannot authorize recreation. Only fresh exact readback yields
`verified`; HTTP success or GraphQL `success: true` alone cannot do so.

HTTP 401/403 mutation responses retain a denied hold when readback is absent;
other uncertain transport responses retain unknown. Explicit `success: false`
retains failed. No underlying exception text, raw response or unrelated comment
body is stored. The outer owner must resolve any deliberate retry/authority
change under its existing contract; this adapter never clears retained intent.

## Native API source and exact readback

The API selections were checked against the [official Linear SDK GraphQL
schema](https://github.com/linear/linear/blob/master/packages/sdk/src/schema.graphql)
and [Linear attachment documentation](https://linear.app/developers/attachments)
on 1 November 2026. Existing `_graphql` is used because the pinned native comment
reader does not expose complete pagination or distinguish read failure from an
empty collection.

| Planner action | Single mutation | Required native readback |
| --- | --- | --- |
| `linear-link-pr` | `attachmentCreate(input: AttachmentCreateInput!)` with exact issue, PR URL and fixed source title | Exact URL in that issue's `attachments`. |
| `linear-ensure-dependency` | `issueRelationCreate(input: IssueRelationCreateInput!)` with blocker `issueId`, dependent `relatedIssueId`, type `blocks` | Exact directional relation in the dependent issue's `inverseRelations`. |
| `linear-record-source-milestone` | `commentCreate(input: CommentCreateInput!)` | Exact deterministic source-only body in that issue's `comments`. |

Every page checks the canonical issue/project and complete `pageInfo`, with at
most 20 pages of 50 nodes. Missing/malformed pages, repeated cursors, conflicting
milestone content or duplicate matching records hold the action. An early empty
page never authorizes mutation before pagination completes. Readback retains
matched native IDs, not copied connection contents.

The comment body explicitly names an OffMenu source milestone and contains
`native-source-milestone:<milestone_id>` plus canonical JSON of the EXACT
milestone. A marker alone or altered structured content cannot qualify. Neither
integration nor release source metadata changes Done or proves product acceptance.

A verified dependency action means the native blocking relation exists. Its
readback also records `blocker_state_type`; a started/canceled blocker is not
completed. This adapter never emits `dependencies_satisfied` or admission. The
root must refresh the native planner inputs before granting eligibility; a
missing desired relation can be repaired in the Linear metadata phase while
coding/integration/release remain held until their dependencies are satisfied.

## Offline verification and runtime limits

The tests use the ACTUAL pinned Stokowski `LinearClient` and `httpx.MockTransport`,
with synthetic data only. Persisted restart uses the original `CurrentWork.save`
and temporary private owner files. No user credential or live API is touched.

The existing Stokowski environment lacks `jsonschema`, which the shared contract
requires. For source checks only, use the existing delivery interpreter plus the
explicit pinned Stokowski import path; no package installation follows:

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=src:tests/delivery:tools/delivery:/home/user/src/offmenu/.delivery/stokowski/venv/lib/python3.12/site-packages \
/home/user/src/offmenu/.venv-delivery/bin/python -m unittest \
  test_native_harness_linear test_linear_delivery -q
```

Coherent installed dependency qualification, root factory wiring, independent
review and actual runtime adoption remain separate owner work.
