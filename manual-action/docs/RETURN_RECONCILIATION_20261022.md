# Receipt return reconciliation — 2026-10-22

## What is known, and what is not

The reviewed runner pulls the manual-action branch once, fast-forward only, before
starting its plan (`Runner.pull`, `main`). Each receipt is canonically validated,
committed locally, then pushed without force (`Runner.publish`).

If a push fails, `run_ingest_plan.deliver` catches the transport error and disables
further publication attempts for that process. Ingestion continues independently.
Each subsequent progress/final receipt is first persisted under
`.git/offmenu-runner/ingest-pending`; local data is not rolled back. A later
`./run` cannot fix a genuinely diverged branch because its startup fast-forward
pull fails before pending receipts are recovered. A local merge alone is not
sufficient: the normal runner rejects unpublished merge commits.

This behavior explains a *possible* transport stall. It does **not** prove that
Foo's live process has failed, stopped, or reached any particular count. The
last reported published checkpoint was `01c9c63bc6a7bdbdf66b971fe804c83845450939`.
The exact approved manual-action remote revision for this recovery is
`c792d3b71bc7907e96b6688242e090ede100b6ab`. No Foo connection or session was used
for this work, and no workflow was dispatched.

## Narrow recovery, only after the current run exits

`manual-action/reconcile_returns.py` is a one-shot tool, not a watcher or an
alternate ingest runner. Fetch it from the **separate** recovery integration
branch into `.git`, rather than checking out that branch in the ingest worktree.
Use the separately supplied pinned commit and SHA-256 bootstrap command.

The helper:

1. Reuses the existing nonblocking `.git/offmenu-run.lock`. A live `./run` causes
   refusal. An inherited bootstrap lock FD is checked against that exact file.
2. Requires the existing manual-action branch, private OffMenu origin, no pending
   Git operation, a clean index, and no tracked working-tree edits. Untracked
   runner files are refused; any other untracked merge collision is preserved.
3. Fetches only `integration/manual-actions-20261022`, without tags or submodules.
   The fetched HEAD must exactly equal the fixed reviewed revision above. A
   changed remote stops recovery; it is never blindly accepted or retried.
4. Requires the published checkpoint to be an ancestor of both histories.
   Every local-only ordinary commit must use the runner's exact commit message
   and add only regular, canonical, strict-schema sanitized receipts. Size and
   commit-count limits apply. No source dataset or unrelated local commit passes.
5. Fast-forwards when possible; otherwise makes a two-parent merge with the exact
   reviewed remote. It never rebases or rewrites local receipt commits. A conflict
   stops with the conflict available for review; no automatic resolution or abort.
6. Revalidates that both histories survive and the entire outgoing tree delta is
   receipt additions only, then performs a normal non-force push. Git commands
   have the existing runner's 120-second timeout and suppress private Git output.

If a merge succeeds but its push fails, the merge remains local. A retry with the
same remote pin accepts only this helper's exact merge shape/message and validated
receipt-only delta. A remote change still stops for a fresh review. A successful
run changes the remote HEAD, so repeating this fixed-pin helper after success is
not needed and will intentionally report a stale pin.

The helper does **not** start ingestion, drain/delete the pending spool, discover
sources, export raw data, reset, rebase, stash, clean, or force-push. It publishes
only receipts already committed locally. It leaves all local data and spooled
progress/final receipts untouched. Do not interpret its success as proof that all
pending final receipts have already been uploaded.

After successful reconciliation, the user's next explicit `./run` can again
fast-forward normally. Its existing startup recovery validates and drains pending
receipts before entering the normal ingest plan. Reconciliation itself does not
invoke that command or promise that a changed/new plan never reads source rows.

## Stop handling

- `another_run_is_active`: current run owns the lock; leave it alone and wait for
  its terminal summary. This is not an ingestion failure.
- `remote_changed_since_review_no_merge_or_push`: exact remote pin no longer
  matches; review the new branch head before preparing any changed recovery.
- Dirty index/worktree, unrelated commit, or missing checkpoint ancestry: preserve
  the state; inspect only the affected Git metadata before choosing recovery.
- Merge failure/conflict: preserve conflict state and both histories; no retry
  that silently resolves or removes work.
- Push failure: local merge/receipts remain; network/auth failure may be retried
  with the same pin. If the remote advanced, stop for review instead.

## Regression evidence and custody

18 generated-local-Git tests cover divergence, exact parent/receipt preservation,
fast-forward, local-only publication, live-lock refusal, inherited-lock handoff,
dirty tracked/index states, untracked collision, unrelated/raw-path commits,
malformed receipts, missing ancestry, stale remote pin, conflict preservation,
missing-identity fallback, failed-push retry, concurrent remote advancement, and
a counterfeit helper merge with an unauthorized tree change. The ingest engine
and plan entry points are guarded against invocation in these fixtures. A private
spool sentinel is verified byte-identical after reconciliation.

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s manual-action/tests -p test_reconcile_returns.py -v
```

Only this helper, its generated-fixture tests, and this documentation are added on
`integration/return-recovery-20261022`, based on the exact reviewed revision.
`run`, `plan_runner.py`, the plan, workflows, source adapters, and the active
manual-action branch are not modified by publication. No raw datasets,
credentials, private source paths, live process logs, or Foo state are included.

## Small future transport fix (design only, not active migration)

Keep `git pull` / `./run` as the user interface, but separate reviewed code from
receipt return history. The code branch should receive reviewed code only; a
fixed dedicated return branch should receive schema-validated, append-only
sanitized receipts from an isolated Git state directory. The running code
worktree must never pull, merge, or rebase in response to receipt push contention.
Use the existing durable spool and canonical receipt names. A return-branch
non-force race may be retried only after validating that the intervening remote
delta consists solely of valid receipt additions; otherwise retain the spool and
stop transport, not ingestion. Pin the code implementation in each receipt.

This design is not deployed here. Until separately reviewed and installed while
idle, do not publish new code/doc commits to the active run's shared return branch.
