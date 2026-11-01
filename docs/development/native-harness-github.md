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
transactions. A fresh claim durably initializes prepared state under that lock
before publishing ownership, including a status-only preflight. Missing state
for an already claimed historical transaction is held for reconciliation. Pending or unknown publication, promotion or tag effects prevent
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
read back; any other existing object is a conflict. Unconsumed tag intents retain their exact durable action across separate gateway
invocations and transient observations. Consumption changes pending to unknown
before HTTP. Unknown merge/tag replies retain the same action identity and
reconcile through GET without replay; tag absence cannot authorize another POST.

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

## Fixed native runtime wire

The existing installed publisher supports one additional fixed invocation:

```text
/usr/bin/node /opt/offmenu-publisher/tools/delivery/github-app-publisher.mjs --native-rpc
```

The argv-free legacy invocation is unchanged. Native admission is opt-in; do
not retrofit its association into historical qualification snapshots or rebind
old receipts to exercise this route. The native flag reads at most
16 KiB of UTF-8 JSON from stdin. Duplicate keys, extra fields, non-JSON values,
unknown modes and mismatched identities fail before controller or key use. It
accepts exactly:

```json
{
  "version": 1,
  "mode": "observe",
  "operation_id": "<fingerprint of the existing protected publisher binding>",
  "issue_id": "<canonical UUID>",
  "project_id": "<canonical UUID>",
  "owner": "<admitted owner>",
  "unit_sha256": "<exact native unit fingerprint>",
  "packet_sha256": "<exact owner packet fingerprint>",
  "source_sha256": "<fingerprint of the shared handoff source>"
}
```

`mode` is `observe` or `step`. Commands, executables, config paths, credentials,
branch/ref selectors and callbacks are never accepted on this wire. Every
identity must match the fixed root-sealed configuration. The existing protected
`snapshot.native_runtime` association contains exactly
`{issue_id, project_id, owner, unit_sha256, packet_sha256, source}`, where `source`
is the full shared handoff source object. It must match the immutable publisher
source tuple; release source must equal the frozen candidate source. The existing
binding hash supplies `operation_id`. It is derived rather than embedded back
into the snapshot, which would make the integration qualification hash circular.
Every isolated Python RPC also compares the node process's exact binding and
native-association pins with the freshly reloaded protected config before any
transaction construction, so config drift cannot return another transaction's
status under the original identity. The caller receives that same transaction
pin through its sealed owner admission;
it cannot select another journal by sending another ID.

The response contains exactly `version:1`,
`kind:"native-publisher-response-v1"`, `request_sha256` (canonical fingerprint
of the parsed request), the seven request identity fields, derived `phase`
(`integration` or `release`), and `status`. Status is one of
`ready`, `pending`, `unknown`, `verified`, `denied`, `failed`. No raw snapshot,
claim path, plan, review payload, log, command or credential is returned.

The installed UIF-126 adapter must compare every response identity and request
hash with its existing owner binding before projecting the three-field runtime
transaction observation. The response makes **no child-cleanup assertion**.
The caller must wait/reap the actual fixed process and establish its own
`child_tree_gone` fact. A lost/failed invocation may already have changed the
original transaction; it requires observation of that same operation, with no
replacement ID or automatic effect replay.

`observe` reads the existing transaction and repository claim using the existing
lock without creating a lock, binding, prepared state, transaction or ownership
pointer. An unclaimed admitted transaction can report provisional readiness;
only the normal step can acquire its claim. A conflicting unresolved predecessor
holds the candidate. Missing historical state remains a hold. Canonical GET
reconciliation is allowed only for an already current exact claim, using the
original typed controller readers and existing checkpoint. That read-only path
cannot consume intent, write a claim or call repository mutation capabilities.
It can persist canonical reconciliation into the same original journal. Consumed
unknown publication, merge and tag operations remain GET-only even when a caller
requests `step`.

A ready `step` advances at most one existing finite publication/merge/tag phase.
It requalifies the exact local source before every ready integration merge,
including after publication completes, and preserves exact review/protection
gates and the original durable intent/consume-before-HTTP rule. Consumed unknown
effects use GET-only recovery even if that local source now fails qualification.
A resulting `ready` response
can mean the next phase of the same transaction is eligible; it never means the
whole source outcome has been integrated. `verified` means canonical source
integration or complete release/tag readback, according to the derived phase.
Neither result writes Linear Done or claims product/runtime acceptance.

The invocation still requires the actual existing publisher UID and all original
protected config/source/interpreter/key custody checks. It adds no `sudo`,
`runuser`, privilege transfer, launcher service or credentials. A current owner
process that cannot use this existing host boundary must remain explicitly held;
it must not retry a denied config read through another identity. The sole host
owner separately qualifies the permitted gatekeeper invocation, exact installation
and rollback closure before runtime adoption. Source tests use synthetic HTTP
and a real temporary Python RPC process, with no installed host effects.
