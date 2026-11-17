# Meal-plan adapter state transitions

This is a bounded source-identification slice for
[UIF-252](https://linear.app/maldous/issue/UIF-252), not a product change,
adoption decision, runtime qualification or exhaustive inventory.

## Source edition and coverage

All code observations below bind accepted OffMenu commit
`51ad2b27a226f097dcaa9a27db5fade33d9ef4dd`, tree
`6212683d485706ed894674348c64599e8c990289`.

| Input | Exact Git blob | Coverage in this slice |
| --- | --- | --- |
| `apps/web/src/meal-plan-owner19.mjs` | `5eedec4f74130e2b78bdd136d1663271d8aea676` | All 181 lines source-read: capture/validation helpers, aggregate transitions and async owner adapter. |
| `tests/web/meal-plan-owner19.test.mjs` | `b83d006165a37c1a45de61bdc57f0ef430f5945c` | All ten test bodies read, not executed. Assertions are source evidence, not a new pass. |
| `apps/web/server/state.mjs` | `e3b1b941515eebf096f2f19f0308d87cd7b643d5` | Only the plan projection at line 34 and adjacent profile context inspected; not a full server or persistence review. |

The [existing inventory](README.md) retains its earlier `436f16c2` source
edition and four cooking/serving/checkout machines. Those entries are not
rewritten here. This slice adds a caller-level aggregate and an asynchronous
commit adapter, rather than counting the imported cooking functions again.
The shared coverage ledger and index are intentionally unchanged while other
disjoint inventory slices are being prepared.

The existing [Worker 19 candidate note](../meal-plan-owner19.md) is historical
design/review provenance. Its old paths, test outcomes and adoption status are
not substituted for current call-site or runtime proof. A literal-reference
scan of tracked `apps/`, `tools/`, `scripts/` and `tests/` (excluding `tests/fixtures/`) found this
adapter and its focused test as the references to its filename/exported entry
points. That scoped result does not qualify dynamic/external consumers or a
deployed version.

## OM-PLAN-001: copied plan and cooked-batch aggregate

**Responsibility:** domain transition adapter. Representation is distributed
across `profile.plan`, `profile.batches`, `profile.history` and inventory,
not a single status enum. The code-observed predicates below are descriptive
names, not new persisted fields.

- An eligible plan exists by `planId`; a missing plan is an error, not creation.
- An uncooked plan has no active batch for that plan and no live batch link.
- An active batch is one with matching `planId` and `!undone`.
- A plan link names a non-undone batch owned by that plan. A bad link or multiple
  active batches is a reconciliation refusal.
- A served batch has events/history managed through the imported cooking model.
  An undone batch remains retained but is no longer active.
- These are per-input predicates. There is no local durable transaction, global
  actor, background worker or terminal deletion in this adapter.

Evidence:
[aggregate selection, lines 74–88](https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/apps/web/src/meal-plan-owner19.mjs#L74-L88),
[capture and validation, lines 1–68](https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/apps/web/src/meal-plan-owner19.mjs#L1-L68).

| Event | Guard and transition | Output/effect boundary |
| --- | --- | --- |
| `copy` | New bounded plan identity, capacity below 10,000, existing recipe and valid editable fields. A cooked source plan may be copied. | Appends a separate plan, deletes its live `cookBatchId`, preserves existing source evidence or captures original plan/recipe evidence, and returns `requiresReview:true`. Original plan and recipe are not rewritten or scaled. |
| `edit` | Rejects while an active or linked cooked batch exists. Only date, slot, servings, members and adjustments are editable. | Replaces the selected plan in copied state and returns `requiresReview:true`. This flag is not a persisted approval or food/rights qualification. |
| `cook` | Exact `reviewed:true`, recipe present, valid mutation identity/date matching the plan, no reused undone/other-plan batch identity, no generated-lot collision, compatible existing batch and reconciled stock. | Calls existing `cookMeal`, verifies unique inventory output, appends only a genuinely new batch with timestamp/source evidence, and sets the live plan link. A duplicate cook preserves batches and can repair a missing plan link without another raw-stock deduction. |
| `serve` | Active/linked batch and matching cooked-stock total; bounded event identity/date; selected member within plan attendance when supplied; no other-batch history collision or changed replay fields. | Calls existing `serveBatch`. A new result updates inventory, batch and one timestamped history row. A duplicate requires the matching history row and appends nothing. Batch/history disagreement refuses reconciliation rather than silently reconstructing history. |
| `undo` | Active/linked batch and matching stock; imported `undoCook` must permit compensation. | Returns restored inventory, marks the retained batch undone and clears live links to it. The imported model protects event-bearing batches; this wrapper does not weaken that guard. |
| Unsupported action or invalid aggregate | Invalid/missing/duplicate identities, invalid plan shape, broken links or unsupported action. | Throws; no returned successor is committed here. Original input state is captured into separate plain data before transition work. |

Evidence: [copy/edit, lines 89–104](https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/apps/web/src/meal-plan-owner19.mjs#L89-L104),
[cook, lines 106–121](https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/apps/web/src/meal-plan-owner19.mjs#L106-L121),
[serve/undo, lines 123–154](https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/apps/web/src/meal-plan-owner19.mjs#L123-L154).

### Supporting constraints and interactions

Descriptor-based capture rejects accessor properties, symbols, unsafe keys,
sparse/custom arrays, unsupported prototypes and nonfinite values; it bounds
depth, node count, array length and total string characters. Those checks are
input-capture guards, not authentication or a universal isolation guarantee.

Plan dates are checked for actual calendar round-trip validity. Plan and
mutation/event identities are caller-supplied; the adapter does not mint a new
identity after a failure. Copy/edit are not idempotent approval operations.
Cook/serve replay handling is specific to retained plan/batch/event identity and
payload. An identical domain result does not establish durable commit idempotency.

Underlying raw allocation, serving/intake/remainder and compensation semantics
remain with `cookMeal`, `serveBatch` and `undoCook`, mapped by the existing
`OM-COOK-001` / `OM-SERVE-001` entries. Unknown completion remains null.
No purchase intention, source-rights admission, dietary recommendation or
food-safety approval follows from a copied recipe or a `reviewed` boolean.

Read assertions:
[lifecycle/replay, lines 15–51](https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/tests/web/meal-plan-owner19.test.mjs#L15-L51),
[copy/edit and identity guards, lines 52–105](https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/tests/web/meal-plan-owner19.test.mjs#L52-L105).

## OM-PLAN-COMMIT-001: one adapter instance's async operation gate

**Responsibility:** caller/infrastructure boundary around the domain transition.
State is the closure's `busy` boolean plus the captured intent, selected account,
read snapshot/revision, calculated successor and awaited commit response.
The following phase names describe control flow; they are not stored statuses.

| Phase/event | Guard and successor | Failure/ownership boundary |
| --- | --- | --- |
| Idle → pending | Reject a second call when `busy`; otherwise set it before capturing intent. | Serializes only calls using this one adapter instance, not other tabs/processes/instances. |
| Capture → read | Capture the request before the asynchronous `read()`; take a bounded account identity from `scope()`. | Later caller edits do not change this captured request. Capture/scope/read errors enter `finally`. |
| Read → transition | Snapshot account and current scope match the selected account; revision is a bounded identity; `preservesPlanEvidence===true`. | Capability is required, not manufactured by this module. A scope string alone is not authentication. |
| Transition → commit | Calculate the copied successor, then recheck account scope. | Calls exactly the supplied `commit({accountId,expectedRevision,state})`. This module does not implement the actual account/revision fence or storage transaction. |
| Commit acknowledgment → return | Require exactly `saved?.committed===true`. | Returns only the domain result. It does not return the new durable revision or prove the callback's acknowledgment is truthful. |
| Success or throw → idle | `finally` sets `busy=false`. | Releasing this local gate is not rollback, effect reconciliation or a global claim release. |

Evidence:
[async adapter, lines 157–181](https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/apps/web/src/meal-plan-owner19.mjs#L157-L181).
Read assertions:
[commit harness and refusals, lines 106–129](https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/tests/web/meal-plan-owner19.test.mjs#L106-L129),
[pending intent capture, lines 130–141](https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/tests/web/meal-plan-owner19.test.mjs#L130-L141).

There is no timeout, abort/cancel signal, automatic retry/backoff or durable
operation journal here. An unresolved read/commit keeps that instance pending;
abandoning the caller does not establish cancellation. A commit may have taken
effect before throwing or returning an unconfirmed response. The adapter cannot
undo that effect or choose a safe fresh operation identity. Actual owner-queue
reconciliation and authenticated revision/operation binding remain outside this
slice. Even a domain duplicate still proceeds through the supplied commit call.

## Persistence, privacy and adoption gaps

The actual server plan projection
[state.mjs:34](https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/apps/web/server/state.mjs#L34)
constructs a whitelist of plan fields without `sourceEvidence`. The focused
[assertion at lines 142–147](https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/tests/web/meal-plan-owner19.test.mjs#L142-L147)
explicitly expects that evidence to be lost through the real validator.
This is current source evidence of an interface mismatch, not a new test result
or permission to change the validator.

Copied source evidence can include the original plan and its member identities.
Preserving it in account-private state does not authorize sharing it. The
historical candidate note separately reserves persistence and sharing projection
work; this slice does not qualify those consumers, their present deployment,
consent or rights, or a final Owner04/16 bridge edition.

## Coverage closure and continuation

| Source region | Disposition |
| --- | --- |
| Adapter lines 1–68 | Input capture/identity/date/plan/edit/stock guards supporting the two machines; not separate schedulers. |
| Adapter lines 74–154 | Fully mapped to `OM-PLAN-001`, including all five actions and rejection/replay branches. |
| Adapter lines 157–181 | Fully mapped to `OM-PLAN-COMMIT-001`; actual commit implementation remains outside scope. |
| Focused test file | Ten assertion bodies read; no tests executed or historical passes relabeled. |
| Server state module | Plan-projection boundary only; remainder explicitly unreviewed by this slice. |
| UI, queue, authenticated storage, sharing and deployment | Not qualified; do not infer adoption from an exported adapter or synthetic commit harness. |

For UIF-252 this adds two source-bound machines and one concrete persistence
interface gap to the continuing inventory. It does not close UIF-252, any
functional caller/receipt outcome, or the full open-issue impact matrix.
Subsequent inventory composition should link this slice and reconcile its source
edition with the shared ledger without overwriting the earlier edition or
parallel account/auth and sync/persistence work.

Revalidate this slice when any of the three pinned blobs, the adapter's imported
cooking contracts, a real consumer/import, the owner commit contract or the
server/sharing evidence projection changes. An author-distinct source/coverage
review remains required; documentation alone supplies no new runtime acceptance.
