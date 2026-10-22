# Native ownership and Foo fallback

Native local sessions remain primary even when idle. The fixed Foo dispatcher
now refuses execution before creating output directories or job receipts unless
the same reviewed runtime layout and an explicit safe-boundary handoff qualify.
A free lock or an empty GitHub queue is insufficient. This source change does
not install configuration, hand off a session, change the workflow trusted pin,
or launch a job. Normal CI, hosted publisher, PR31, results and webhook routes
remain unchanged.

00 must compose this candidate with reviewed `manual-action/runner_paths.py` from
`3478b6f6e3fcdea883aa3d24ed395c4d82d28eaa` (unchanged from cab038), review the
composition, and publish the exact execution pin through the existing route.
The module is deliberately absent from the91da standalone base: missing API
fails closed.26 owns layout implementation;57 owns actual runtime admission.
No caller may load an alternate Python module using an operational environment
variable. The test-only `OFFMENU_TEST_RUNNER_PATHS` selects the frozen API for
standalone synthetic author tests; production never reads it.

The existing `OFFMENU_RUN_LAYOUT` selects `offmenu-runner-layout/1`. Its lock is
read from configuration; the current proposed value is
`/home/user/src/offmenu-data/runtime/locks/manual-runner.lock`, under an owner0700
parent. No old lock path is hardcoded or created by this guard. The selected
four private roots, exact configuration digest, existing0600 owner singleton
device/inode and `<runtime>/layout-admission.json` must match frozen26 bindings.
The existing runner_paths API pins config/root/lock identity and supplies the
same shared FD and config/binding hashes to children. Neither layout admission
nor ownership records are generated, chmodded or repaired by the dispatcher.

At an independently qualified native safe boundary, the authorized owner
provides `<runtime>/foo-fallback-admission.json`, a private0600 regular nonsymlink
file. It has exactly these keys:

```json
{
  "schema": "offmenu-foo-fallback/1",
  "owner": "actions-fallback",
  "boundary": "safe",
  "native_thread_id": "actual native owner thread",
  "handoff_id": "actual handoff identity",
  "handoff_evidence": "actual source-bound safe-boundary qualification receipt",
  "request_identity": "sha256 of existing canonical request plus trustedCodeSha",
  "github_run_id": "exact admitted run ID string",
  "github_run_attempt": "exact admitted attempt string",
  "config_sha256": "exact selected configuration bytes sha256",
  "binding_sha256": "StateLayout.admission_digest(shared_fd)",
  "expires_unix": 1
}
```

The example is intentionally non-executable and expired. All values must bind a
real authorized handoff; nonempty evidence references are pointers, not a
cryptographic proof of human approval. This is a trusted local owner boundary,
not protection against an actor able to rewrite the same user's private files.
`owner=native`, idle/unknown/missing ownership, stale or changed scope, wrong
run/attempt, and expired/unbounded expiry deny execution. Expiry must be in the
next30minutes; the workflow's existing25minute limit remains. The owner must
qualify the exact admitted run before it can execute; dispatching merely to
discover a run ID is not authorized by this source change. Missing access under
the existing service sandbox/UID fails closed;57 must qualify it without this
guard changing service controls.

The shared singleton is held throughout execution and inherited by each direct
child alongside the existing dispatcher lock. Handoff and physical bindings
are checked throughout each child's lifetime, even after both output pipes
close, and before recording a terminal receipt. Cancellation and deadlines also
remain active after pipe EOF. Changed or revoked admission stops the child process group. The guard restores process
environment pins and closes its FD on exit; surviving children keep inherited
lock custody. It does not invent a native-session scheduler or wake mechanism.

Per-job terminal receipts retain existing idempotent reuse. A matching
nonterminal/interrupted receipt now returns
`unfinished-job-requires-reconciliation` without overwriting or executing it.
A free lease cannot settle prior side effects. The existing owner must reconcile
the exact admission/receipt/child outcome before selecting any new execution;
this change provides no automatic retry or repair route. Missing admission
returns `ownership-admission-refused`; no source paths or private file contents
are emitted in its public error.

Focused verification uses generated temporary private layouts and the frozen26
resolver, without installed config/state/DB access. Run the ownership tests on
the reviewed composed source, or explicitly select the frozen resolver for
standalone author tests. Existing queue tests mock only the separate admission
boundary to retain profile/receipt regressions; ownership tests exercise real
flocks, physical bindings, child FD inheritance, revocation and refusal before
output creation. No fixture authorizes live fallback or deployed pin changes.
