# Offline sync: when is a kitchen actually saved?

A local edit, a durable browser checkpoint, and an acknowledged server revision
are three different outcomes. **Synced** means the latest sampled browser state
matched the acknowledged baseline for that scope. **Pending** and **conflict**
do not establish what a server committed after a lost response.

This [UIF-252](https://linear.app/maldous/issue/UIF-252) inventory entry describes
`maldous/offmenu` develop [51ad2b27](https://github.com/maldous/offmenu/commit/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd),
tree `6212683d485706ed894674348c64599e8c990289`. It covers the full `sync-model.js`
and `sync-ui.js` modules, plus the cited portions of callers, schema and tests.
State names below describe source predicates, not new enums or product behavior.
This does not change the [earlier inventory's source edition](README.md).

## OM-SYNC-CHECKPOINT-001: preserve and recover local edits

The [queue and recovery code][queue] keeps one version-1 snapshot **per key**
in the IndexedDB `pending` store. A put replaces that key's previous
checkpoint. It contains a clone of state, baseline, revision, time and a fresh
mutation ID. It is not an append-only operation log. A completed IndexedDB
transaction is not acknowledgment of a cloud write. Browser localStorage
separately holds the scope's baseline, revision and dirty marker.

| Event | From → to | Observable effect or limit |
| --- | --- | --- |
| New scope key | Prior context → new generation | Load the new key's baseline/revision; reset conflict, recovery and retry tracking. One recovery promise is reused per context. |
| Absent, invalid or redundant checkpoint | Recovering → current local state | The version/state guard, an unchanged checkpoint or equality with current state yields no restoration. A queue read failure is ignored by recovery; it is not proof no edits existed. |
| Pending checkpoint and local edits | Recovering → restored, unchanged or blocked | Merge checkpoint base, current state and saved state. On conflict, retain local state and report a conflict. On actual restoration, apply merged state, remember the checkpoint base/revision and mark dirty. |
| User confirms device-copy removal | Local data → cleared for the selected prefixes | The [clear-local handler][app-clear] removes matching localStorage entries, awaits prefix-based IndexedDB removal, then reloads. This is **not** a cloud delete or rollback. The synthetic fixture path returns without clearing shared storage. |

The [three-way merge][model] accepts an identical value or the side that differs
from base when the other side has not changed. It recursively merges objects,
string-keyed or string-ID arrays; incompatible changes retain the local value
and surface a conflict path. Independent new cooking batches drawing the same
lot, or divergent new serving histories on the same prior batch, also signal
conflict. `recoverCheckpoint` and the network loop choose separately whether
to apply a result: a reported conflict is not an automatically resolved edit.

## OM-SYNC-ATTEMPT-001: reconcile with one remote revision

The [sync instance][sync] carries `busy`, `blocked`, retry time, generation,
active key, baseline and revision. A run can start only with a user, outside
demo, online, idle, unblocked and past its retry time. These guards apply to an
instance, not all browser tabs.

1. **Schedule and recover.** Scheduling refreshes context, replaces the previous
   debounce timer and, for a signed-in non-demo user, initiates a checkpoint and
   schedules a run after one second. Online events schedule; offline events
   update status. Visible tabs also attempt a run at 60-second intervals.
2. **Read and compare.** Recover, snapshot, checkpoint, then GET. Recheck the
   initiating scope after the network response. If remote state exists, merge
   it against the remembered baseline and current local state. A conflict
   blocks automatic progression and preserves local work.
3. **Write if different.** Apply a clean merged change locally when needed.
   Use the fetched revision. A differing state is checkpointed and sent in a
   revision-conditional PUT; an equal state needs no PUT. The PUT carries
   revision and state, **not** the checkpoint mutation ID. The client checks
   context again before consuming the result.
4. **Settle or retry.** Persist the revision/baseline and checkpoint a fresh
   snapshot. Equality clears the dirty marker; later edits keep it pending
   and schedule again. A current non-abort failure retains pending status and
   backs off from 15 seconds to at most five minutes; stale-context/abort
   handling suppresses that failure's status. `finally` releases the busy flag.
   A late or unsuccessful response is not evidence that the original PUT had
   no effect. A later run reads current state again.

`resume` clears the block and schedules; `reset` replaces the baseline and
in-memory revision, marks recovery satisfied for that context and schedules.
Neither constitutes a cross-tab lock, a durable transaction across browser
stores, or server-side compensation.

## OM-SYNC-SCOPE-001: account, shared editor and viewer

| Owner / boundary | State and transition | Persistence and authority |
| --- | --- | --- |
| Account client | [Account switch and dirty tracking][account] select guest, demo or user keys. [Account wiring][app] suppresses account auto-sync while sharing is active. | A snapshot covers lots, products, recipes, profile and selections. Applying synced state writes these separately to browser storage, then renders. There is no multi-key transaction here. The account request uses a 15-second timeout. |
| Shared client | [Select, close and resume][sharing] use a selection generation. Selecting remembers the account snapshot, reads kitchen state and applies it. On ordinary exit an editor with pending work attempts sync; if still pending it stays in the kitchen. Forced exit has different behavior. | Its sync key includes account scope and kitchen ID. It sends the [shared projection][projection], not the whole private profile. Viewers do not enter the editor sync path; polling can refresh the displayed state or detect revoked membership. Filtering a projection is not proof of every privacy requirement. |
| Account server | [GET and conditional PUT][server] read the verified user's row. Revision zero attempts first insert; a later revision updates only a matching user/revision. No returned row yields a conflict, not an unconditional overwrite. | The [schema][schema] stores user ID, revision, state and update time. A successful response binds a specific revision. Client status, local checkpoint and database commit are separate observations. |
| Kitchen server | [Kitchen routes][kitchens] check membership; viewers cannot PUT. A valid revision and projected/validated state precede a revision-conditional update. A mismatch returns a conflict. | Kitchen and account rows differ. A client scope change can discard a stale response locally; it does **not** retract a request already received by the server. No distributed lock or cross-channel rollback is evidenced. |

## Evidence, issue impact and maintenance

The [journey assertions][journey-tests] describe checkpoint recovery, competing
edits, shared projections and concurrent cooking/serving. The [scope
cancellation assertions][scope-tests] use a stub environment and rejected
requests for changed account, stale/abort and ordinary failure. They do not
exercise a physical browser database or a successful server-side write with
a lost response. These tests were **read**, not rerun; no live account, device,
database, provider, service or deployment was used.

* **UIF-145** (account journeys): account-key changes and stale-result handling
  matter; migration, sign-in and cutover are not qualified by this trace.
* **UIF-149** (collaborative shopping): shared projections include shopping
  fields, but synchronizing a list does not record physical receipt.
* **UIF-98/99** (household planning): merge conflicts on common lots and batch
  events constrain concurrent edits; inventory and meal acceptance stay separate.

For revalidation compare the two module blobs
(`11a9ad5b07226d881a7542f63ef58c6bd63b2596` and
`31ad13c52e48544141675baa8021ff7b943d5bf7`) and *all* cited caller, handler,
schema and assertion ranges against the next selected revision. Recheck changed
interfaces, not just the two blobs. Browser storage failures, concurrent-device
timing, quota/eviction, hosted schema and deployed behavior remain unverified.
Other source editions and the project-wide coverage ledger retain their own
owners; this entry is not exhaustive project acceptance.

[queue]: https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/apps/web/src/sync-ui.js#L4-L13
[model]: https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/apps/web/src/sync-model.js#L1-L4
[sync]: https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/apps/web/src/sync-ui.js#L9-L18
[app-clear]: https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/apps/web/src/app.js#L336
[account]: https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/apps/web/src/app.js#L153-L165
[app]: https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/apps/web/src/app.js#L324-L334
[sharing]: https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/apps/web/src/sharing-ui.js#L6-L51
[projection]: https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/apps/web/src/sync-model.js#L5-L6
[server]: https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/apps/web/server/handler.mjs#L63-L72
[schema]: https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/apps/web/server/schema.sql#L1-L14
[kitchens]: https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/apps/web/server/kitchens.mjs#L6-L12
[journey-tests]: https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/tests/web/journey.test.mjs#L7-L19
[scope-tests]: https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/tests/web/sync-scope-cancellation.test.mjs#L4-L28
