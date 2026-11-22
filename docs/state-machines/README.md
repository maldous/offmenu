# OffMenu state-machine inventory

Status: **in-progress source investigation**, not exhaustive completion or
runtime qualification. This is the versioned continuation of
[UIF-252](https://linear.app/maldous/issue/UIF-252), not a new implementation,
framework, scheduler or acceptance gate.

## Bound source and coverage

This pass selects accepted `develop` commit
`436f16c2a62a5e53af0ee7bf7bc06cd971910d63`, tree
`c46efaf40ffce140bfa2d14cf7a6195ac44e1f16`. All relative source/line anchors below
refer to that immutable edition. Later `develop` changes do not rewrite it.
PR #227 scanner/localisation, PR #234 standalone-product and other retained
editions are not assumed integrated. Private ignored data and runtime stores
were not traversed or exported.

The [coverage ledger](coverage.json) is a historical, commit-pinned ledger of
the 2,298 entries in that selected edition, with their Git blob identities and
initial classification. It does not enumerate the current standalone tree. Its
1,150 code-extension candidates include tests and history; they are not 1,150
discovered machines.
No keyword match is a completeness proof. Ten broad source passes remain:
account/authentication; scanner/camera/identity; household/pantry/expiry;
planning/shopping; corpus/enrichment/provenance; cache/withdrawal/privacy;
navigation/help/locales; background/provider work; supporting delivery
infrastructure; cross-component persistence and recovery. Generated origins,
schemas/configuration, fixtures and unmerged editions need explicit treatment.

The first semantic slice below reconstructs four domain machines from two
complete model modules and their UI caller. It does not close any parent issue.
Tests listed here were **read**, not rerun. Existing execution receipts remain
credited only at their original source and scope.

## OM-COOK-001: raw allocation to a cooked batch

Evidence: [cooking-model.js:5-6,21-37](../../apps/web/src/cooking-model.js),
[journey-ui.js:23-25,32](../../apps/web/src/journey-ui.js).

State is distributed across a batch's `undone`, `remaining`, allocations and
events, its raw lots and cooked lots. Initial absence of a live matching batch
differs from live/unserved, event-bearing, exhausted and undone states. Those
names summarize predicates, not a new enum or proposed implementation.

| Event | Guard / transition | Effect and failure boundary |
| --- | --- | --- |
| `cookMeal` with a new mutation/plan | Recipe quantities and positive servings qualify; eligible lots match ingredient/unit, are reviewed, positive and not expired for the selected date; shortages reject. | Works on copied stock, consumes allocations and returns a new batch plus cooked lot. Optional ingredients are skipped. No storage transaction occurs in this function. |
| Repeated cook | A non-undone batch has the same mutation ID, or the same nonempty plan ID. | Returns existing inventory/batch with `duplicate:true`; raw deductions are not repeated. A default random mutation ID alone does not deduplicate separate user actions. |
| `undoCook` before events | Every retained raw identity matches; event list must be empty. | Removes this batch's cooked stock and restores only allocated raw quantities. The UI caller sets `undone=true` and clears plan linkage before committing. The model does not itself set that flag. |
| Undo after any event | `events.length > 0`. | Rejects, including inventory-removal events; the error's serving wording is narrower than the actual guard. Already-undone input is an identical-reference no-op. |
| Raw identity conflict | Ingredient/unit/barcode, cooked identity or retained source/product reference differs. | Qualifies every allocation before restoration, then rejects without partial raw-stock restoration. Mutable name/storage/date edits are not identity fields. |

Durability, cross-tab atomicity, server authorization and UI commit failure are
not established by this pure-model slice. Undo is compensation, not a database
rollback. No retry/backoff or timeout is implemented in these functions.
Read assertions: [identity undo tests:26-120](../../tests/web/cooking-undo-identity.test.mjs)
and [finite household accounting:46-85](../../tests/web/household-inventory-finite.test.mjs).
Relevant open work: UIF-98/99/148/150/152 and current source-identity residuals.

## OM-SERVE-001: cooked stock to serving/intake/remainder

Evidence: [cooking-model.js:7-9,37](../../apps/web/src/cooking-model.js),
[journey-ui.js:29-32](../../apps/web/src/journey-ui.js).

The event ID, batch event list, remaining cooked portions and inventory total
form the accounting state. Unknown completion is represented by `null`, not zero.

| Event | Guard / transition | Effect and failure boundary |
| --- | --- | --- |
| New serving event | Batch not undone; positive finite portions within remaining; completion null or 0–100; cooked inventory total equals batch remaining; valid remainder action. | Produces a new batch/event, drawn cooked inventory and a separate history log. Saved known leftovers stay in cooked stock; other drawn portions leave it. |
| Unknown completion | `completion === null` or omitted. | Records unknown intake/remainder and draws served portions; it does not claim zero food intake. Nutrition-known counters are cleared for that unknown event. |
| Same event replay | ID and all portions/eaten/remainder/member/date/slot values agree. | Returns `duplicate:true` with unchanged batch/inventory and **no new `log`**. Callers must distinguish this return shape; the model's idempotency does not establish every caller's behavior. |
| Changed event replay | Existing ID but any compared accounting value differs. | Rejects rather than silently treating different consumption as the same event. |
| Cooked inventory removal | `reconcileCookedStock` observes a smaller total. | Lowers remaining and appends one removal event; repeated reconciliation at the same quantity is unchanged. A quantity increase rejects. |

The UI appends a returned history log after calling the model; distributed
atomicity and duplicate-result handling across all callsites remain to be traced.
Exhaustion is `remaining===0`, not deletion of the retained history. There is no
model-level timeout, automatic retry or new recovery worker.
Read assertions: [finite accounting:46-85](../../tests/web/household-inventory-finite.test.mjs)
and [unknown/split stock:77-86](../../tests/web/continuation.test.mjs).
Relevant work: UIF-98/99/148/149/150 and actual consumption/privacy boundaries.

## OM-SCAN-COMMIT-001: prepared scan to inventory

Evidence: [checkout-model.js:5-20](../../apps/web/src/checkout-model.js).
Mode, chosen location, item IDs, prior lots and an optional typed scanner
completion identify the transition. Purchase intention is not an input that
silently creates received stock here.

| Mode / event | Guard / transition | Effect |
| --- | --- | --- |
| `shelf` commit | Recognized mode; nonempty bounded area, nonempty shelf and items array; unique item IDs. | Replaces only the selected shelf's stock, retaining other locations. Empty sessions reject rather than erase a shelf. New item bodies/quantities are not schema-validated here; that boundary remains with the caller/other validation path. |
| `shopping` commit | Same structural session checks and no duplicate final IDs. | Appends actually supplied items to existing inventory; this function does not validate new item bodies, verify a purchase, import prices or infer receipt from intention. |
| `waste` commit | Each selected original lot/location/barcode/quantity/unit still matches; unique IDs; discard amount positive and within quantity. | Removes/discards only matched quantities. Stale stock rejects before returning an update. |
| Typed scanner-completion replay | Every repeated item matches the validated stored item. | Complete replay returns existing inventory; mixed replay/new or changed stock conflicts. Ordinary sessions without that completion schema retain duplicate-ID refusal. |

The function returns arrays and has no persistence, lease, network call,
cancellation or transaction. The scanner UI/server commit path needs its own
later pass; a model guard is not proof of cross-request atomicity.
Read assertions: [checkout:6-18](../../tests/web/checkout.test.mjs) and
[finite receipt accounting:22-43](../../tests/web/household-inventory-finite.test.mjs).
Relevant work: UIF-93/98/99/143/149 and scanner identity/persistence acceptance.

## OM-SCAN-GATE-001: suppressing a held code

Evidence: [checkout-model.js:36-37](../../apps/web/src/checkout-model.js),
[checkout assertion:16](../../tests/web/checkout.test.mjs).
Ephemeral state is the last code and last-seen timestamp. `read(next, now)`
suppresses the same code while the gap is strictly below 800 ms by default,
updating last-seen even on suppression. A different code is accepted; `miss`
rearms only once the gap has elapsed; `reset` clears both values. This is not
durable receipt idempotency, barcode validation, camera ownership or a lock.
It depends on caller-supplied time and has no independent timeout worker.

## Coverage, interactions and remaining uncertainty

Both model modules are source-read and mapped to the four IDs above. Their
normalizers, nutrient calculations and shape validators support these machines;
the UI caller is only partially traced. The ledger marks everything else pending
or explicitly classified, never reviewed-stateless by extension alone.

Remaining interactions include actual UI save/storage/server/database boundaries,
authentication and household projection, interrupted dialogs, pending wake-lock
requests, timers, input identity and concurrent edits. The dialog code contains
asynchronous resource acquisition and a close handler, but this pass does not
claim a tested late-completion cancellation guarantee. No implementation fix or
new library decision follows automatically from an inventory observation.

For each later slice, use the same comparison fields: domain/infrastructure
owner, representation/predicates, event and guard, side effect and persistence,
concurrency/ownership, idempotency/retry/recovery, observability/audit and
security/consumer limits. Refresh relevant open Linear requirements and record
changed-source revalidation. Completion still requires every in-scope area,
the full issue-impact matrix and an author-distinct coverage pass; no current
claim of exhaustive machine identification is made.
