# Native harness GitHub publication and release promotion

UIF-127 extends the existing fixed publisher and repository controller. It is
source behavior, with independent review and coherent runtime adoption still
required. The sole integration/activation owner supplies protected admission;
coding children cannot select source, claims, credentials or HTTP requests.

## Repeated source candidates

Every admitted candidate has a new immutable binding, exact publication plan
and owner-issued review/validation snapshot. The fixed Python bridge selects
`/var/lib/offmenu-publisher/integration/transaction-<fingerprint(binding)>`.
It resumes `current` only when its existing binding matches exactly; a new
candidate gets a new transaction directory. Historical receipts and IDs remain.
The original repository-owner lock and immutable claim evidence serialize these
transactions. Pending or unknown publication, promotion or tag effects prevent
another candidate taking ownership. A superseded transaction cannot restart
publication; verified legacy merge metadata remains separately recoverable.

Feature and bugfix publication still targets `develop`. The existing finite
publication sequence persists each exact intent, consumes it before HTTP, and
reads back blob/tree/commit/ref/PR identity. A lost reply reconciles that same
effect through GET; absent readback never authorizes another mutation. A fresh
candidate never inherits PR191/PR194's binding or completed operations. The
Git Data commit reader accepts GitHub's omission of one terminal message newline
while retaining exact object SHA, tree, parents, author, committer and message
content checks.

## Separately admitted releases

A release is an additional protected configuration (config version 2, binding
version 3), with kind `release-promotion-v1`. It contains repository, owner,
canonical `issue_id` and `project_id`, the shared `release-candidate-v1` value,
its release policy, qualification inputs, PR number, expected `main_base` and
an immutable `release/<name>` tag. `plan` is exactly
`{"kind":"release-promotion-v1"}`. This never changes the legacy feature route
or grants general main-promotion permission.

The qualification input is `{summary, plan, results, catalog, evidence_root}`.
The controller invokes UIF-122's `validate_release_candidate` and UIF-128's
`validate_qualification` on the exact candidate and actual evidence bytes.
Partial, missing, failed, unknown, changed or unstopped results fail closed.
The root-controlled `authority` is exactly:

```json
{
  "version": 1,
  "kind": "release-promotion-authority-v1",
  "owner": "<admitted integration owner>",
  "issue_id": "<canonical release issue UUID>",
  "project_id": "<canonical project UUID>",
  "candidate_sha256": "<fingerprint(candidate)>",
  "qualification_sha256": "<fingerprint(qualification inputs)>",
  "pr_number": 248,
  "main_base": "<expected main commit>",
  "tag": "release/<admitted name>"
}
```

This is a protected owner association, not authentication from worker JSON.
Before this helper runs, the owner prepares and independently reviews a normal
GitHub PR from `release/candidate-<fingerprint(candidate)>` to `main`, with that
branch pointing exactly at the frozen candidate head. Preparing this branch/PR
remains the normal owner's publication action. The candidate's recorded source
branch stays `develop`; subsequent movement of live `develop` never substitutes
new source. The helper does not create or select a moving release candidate.

The protected snapshot binds `publisher_owner`, `qualification_sha256`, exact
independent release `review` (head, expected main base, evidence ID, accepted
verdict and empty findings), empty `unresolved_findings`, false
`publication_triggers_actions`, and `github_review_facts_sha256` from a fresh
canonical review observation. Normal GitHub protections and exact head/base
checks remain mandatory. No review approval, force, protection bypass, Actions,
Linear Done write or product deployment is emitted by this release route.

`releaseStep` uses the existing fixed credential loader and isolated Python RPC.
It persists/consumes `promote-release` before the normal merge API. Canonical
merge readback must match the exact expected main/source parents, frozen tree
and main ancestry. Only then does `create-release-tag` admit a create-only
lightweight tag pointing at that canonical merge. An existing matching tag is
read back; any other existing object is a conflict. Unknown merge/tag replies
retain the same action identity and reconcile through GET without replay.

The protected release closure additionally pins
`tools/delivery/native_harness_contract.py`,
`contracts/schemas/delivery-handoff-v1.schema.json`, and
`tools/delivery/release_qualification.py`. The offline installer checks byte
association without importing copied code. Its existing fixed source revision,
no-overwrite installation and permission holds remain: coherent installation,
reviewed config replacement, rollback custody and actual host/readback evidence
belong to the integration/activation owner. Source tests do not certify any
installed closure or credential isolation.

## Bounded local verification

Use the existing delivery interpreter with `PYTHONPATH=src:tools/delivery`:

- `python -m unittest discover -s tests/delivery -p test_integration_controller.py`
- `python -m unittest discover -s tests/delivery -p test_protected_publisher_install.py`
- `OFFMENU_DELIVERY_TEST_PYTHON=<existing interpreter> node --test tests/delivery/github-app-adapter.test.mjs tests/delivery/github-app-publisher.test.mjs`

During component review, the exact sibling UIF-122/UIF-128 tools paths may be
added to `PYTHONPATH`; they are dependencies awaiting coherent source adoption,
not copied validators. All HTTP, identities, keys and receipts in these checks
are synthetic. No install, service restart, live publication or release occurs.
