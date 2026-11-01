# Finite publisher-owner invocation

`native_publisher_invocation.py` is source for one publisher-owner lifecycle.
It creates no service, queue, coding attempt, backend job, admission authority or
controller. It is not installed by adding this file. The sole owner must obtain
independent exact-source review, qualify the coherent installed closure, exact
host launch permission and mandatory host approval before use. Current UID1000
must not read the publisher's configuration, state or key. Product, CIX, Actions,
new credentials/spend and existing denied-action holds remain unchanged.

## Fixed entry and preparation

The proposed installed entry is exactly:

```text
/opt/offmenu-publisher/venv/bin/python -I -B /opt/offmenu-publisher/tools/delivery/native_publisher_invocation.py
```

It accepts no arguments. Real/effective UID must be 984 and real/effective GID
976. It selects only `/usr/bin/node`, the fixed installed
`github-app-publisher.mjs`, and `--native-rpc`. No request, environment variable or
CLI field can choose an executable, root, path, UID, config, key or callback.
The helper itself does not read the key or perform HTTP. The existing publisher
retains credential and transaction authority.

A root-approved policy listing of the **Node** command is not permission evidence
for this different **Python** helper entry, installation, actual execution or
cleanup. Qualify the exact helper command separately through the normal owner
route before launching it. No sudoers, group, permission, credential or service
change follows from this source. Never replace a denied config read with another
identity or command. If the existing grant does not permit the fixed helper or
same-UID signals, retain the hold.

Production verifies root-owned sealed code/ancestors and the fixed interpreter
and Node. The shared fixed manifest is
`/opt/offmenu-publisher/native-harness-closure.json`, root-owned mode 0444:

```text
{version:1,kind:"native-publisher-closure-v1",source_head:<40hex>,
 source_tree:<40hex>,node_sha256:<64hex>,files:{relative_regular_path:byte_sha256}}
```

`validate_closure(raw, source_head)` validates this exact bounded format and
canonical bytes: sorted keys, compact separators, ASCII escapes, final LF.
The manifest is at most 16 MiB/50,000 files, excludes itself, and covers EXACTLY
the selected publisher source/dependency regular files, helper, reviewed runner,
capacity policy and `venv/bin/python`. `closure_sha256` is SHA256 of the exact
manifest bytes, not the 256-KiB bounded generic fingerprint. The helper streams
file hashing with finite per-file/total bounds. Existing config `codePins` remains
unchanged and must agree with its corresponding manifest entries.

Config `sourceHead` must equal manifest `source_head`, the installed harness CODE
head; it need not equal the transaction candidate head. Manifest `source_tree` is
an owner-qualified accepted package/admission fact, not inferred Git truth. The
factory must know the independently qualified expected manifest digest through
its root-sealed preparation. An untrusted response's hash is not authentication.
The fixed Node must have root custody and match `node_sha256`; this source does
not change its ownership if actual host custody fails.

A generic `.pem` manifest entry is refused before file reads. The sole exception
is `venv/lib/python3.12/site-packages/certifi/cacert.pem`, a public CA bundle.
It requires exactly one manifest-pinned certifi dist-info RECORD, a matching
URL-safe SHA256 row and exact size. The private key's fixed `/etc` path is never
a manifest entry and is never read/copied by this helper.

The existing protected config's `snapshot.native_runtime` must match the original
issue, project, owner, unit, packet, source and `fingerprint(binding)` operation.
The helper selects only the preexisting
`/var/lib/offmenu-publisher/integration/transaction-<operation_id>` directory.
Its `binding.json`, `state.json` and existing exact `active-owner.json` association
must already qualify. Missing normal preparation is `prepared_transaction_missing`;
the helper never creates a Controller binding/state/claim, steals a claim or
migrates historical `current` custody. The original owner's normal prepare route
must establish that transaction before this helper can supervise it. Superseded
claim/config selection remains held until the original owner qualifies recovery.

## Stable wire and Python API

`request(raw: bytes)` validates one UTF-8 outer request, at most 16 KiB:

```json
{
  "version": 1,
  "mode": "invoke",
  "invocation_id": "12345678-1234-1234-1234-123456789abc",
  "request": {
    "version": 1,
    "mode": "observe",
    "operation_id": "<original fingerprint(binding)>",
    "issue_id": "<canonical issue UUID>",
    "project_id": "<canonical project UUID>",
    "owner": "<original owner>",
    "unit_sha256": "<native unit fingerprint>",
    "packet_sha256": "<owner packet fingerprint>",
    "source_sha256": "<sealed source fingerprint>"
  }
}
```

Hash placeholders above are explanatory, not valid input. The inner request and
response remain the exact UIF-127 wire. Duplicate/extra fields, paths, commands,
noncanonical IDs and mismatched sealed associations fail closed.

`invoke(raw: bytes)` uses only the fixed production host. Ordinary readiness is
outer `invoke` plus inner `observe`, with its own supervised invocation evidence.
The inner publisher remains responsible for its read-only readiness contract;
this helper initializes no Controller state or claim. A mutating boundary uses
outer `invoke` plus the exact independently admitted inner `step` request.

The caller must choose a UUID and persist it in existing CurrentWork state BEFORE
attempting the call. It is process-evidence identity, never a replacement logical
operation/job/lease. Reusing it always reads the original receipt, even after a
failed or uncertain invocation. An unresolved invocation for the same operation
blocks another UUID. Keep capacity/ownership held while cleanup is unqualified.

The bounded outer response has exactly:

```text
version: 1
kind: native-publisher-invocation-v1
operation_id: original operation
invocation_id: caller-persisted UUID
request_sha256: fingerprint(original exact inner request)
status: complete | unknown | not-found
response: unchanged validated UIF-127 response | null
receipt: {sha256: digest of exact canonical newline-terminated record bytes,
          body: exact durable record} | null
```

`complete` establishes lifecycle evidence, not publisher success. A stopped
failed/timed-out/cancelled/invalid-response invocation can be `complete` with
`response:null`; it cannot become a verified transaction. `unknown` retains
missing stopped proof. `not-found` from recovery is a hold, never absence of an
external effect or authority to resend. Neither status nor wrapper exit implies
BAU acceptance, issue closure or refill.

`validate_result(value, envelope, closure_sha256)` is pure and performs no I/O.
It validates exact response/record shape, original request/operation/invocation,
expected closure, typed proof and inner response digest/association. The factory
must authenticate the installed route and expected closure separately before
using a validated terminal `child_tree_gone`. No direct protected-state read is
needed by UID1000. Hash consistency alone cannot authenticate arbitrary callers.

## Same-process stopped proof

The fresh publisher-owner process sets and reads back Linux
`PR_SET_CHILD_SUBREAPER` before launching its only fixed child. It uses bounded
nonblocking stdin/stdout/stderr, a fixed minimal environment, a 180-second child
deadline and one new process session. SIGTERM/INT/HUP enter cleanup. Stdout is
capped at 16 KiB and stderr at 4 KiB; raw logs are never returned or persisted.
The caller must allow the owner deadline plus cleanup/fsync before its own
transport deadline; an earlier loss remains uncertain.

Cleanup reuses the accepted `windmill_runner.cleanup`/`descendants` helpers,
including detached-child termination. It never calls the general runner's
`run`, `setup`, `status` or `cancel`, and creates no Windmill job/slot/checkpoint.
Those procfs helpers can skip unreadable entries, so their return value is not a
stopped witness. After actual direct-child wait/reap, the **same subreaper** drains
`waitpid(-1, WNOHANG)` until `ECHILD`. A live-child result, permission/cleanup error,
unavailable subreaper or missing direct-child proof retains false/unknown cleanup.
This same-identity process owns and may signal only its descendants. No privileged
cross-UID killing, global process census, generic executor or new daemon is added.

The original transaction contains a bounded `native-invocation.lock` and one
`native-invocation-<UUID>.json` record per invocation. The mutex is distinct from
the Controller's repository lock so the child can use its existing lock normally.
At most 256 directory entries are admitted; exhaustion holds without pruning
history. Intent is written and fsynced before spawn. The terminal record embeds
that original intent and the actual same-process proof, response and response
hash. It is atomically written, fsynced and read back before a reply is emitted.
A partial temporary write is never acceptance. Original binding/state/claims and
other invocation records are not overwritten. Existing Controller remains the
sole authority for remote effects.

## Recovery

Outer `observe` carries the SAME UUID and SAME original inner request. It reads
only that existing receipt after fixed custody/admission qualification. It never
creates a lock, record or state, sets a subreaper, starts Node or recomputes proof.
A lost response after a durable terminal receipt can recover that exact original
proof. A crash/SIGKILL or failed terminal write leaves intent with no terminal
proof. Even if a new observer has no children, it must report the old invocation
as unknown; it cannot upgrade the old receipt, retry the effect or allocate a new
UUID to bypass the hold. Existing owner reconciliation must qualify that same
invocation before any further action.

## Coherent closure and checks

The installed closure must include this module, the exact accepted
`windmill_runner.py` and its `capacity-policy.json` import dependency, the fixed
publisher/adapter/gateway/Python bridge and their sealed imports/dependencies,
fixed Python and Node. The older first-install allowlists/fixed-head/no-overwrite
receipts do not install these additions. The sole owner must reconcile prepared
manifests and the reviewed upgrade route without clearing original receipts.
The selected source base does not yet contain UIF-127's new `--native-rpc`;
coherent adoption must compose its independently accepted successor first.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tools/delivery:tests/delivery /home/user/src/offmenu/.venv-delivery/bin/python -m unittest test_native_publisher_invocation -v
```

Tests use private disposable `/tmp` in-process seams and fresh unprivileged Python
fixtures. They do not invoke sudo, the installed publisher, protected paths,
credentials, model sessions or live services. They cover real subreaper timeout,
cancellation, setsid/double-fork cleanup, false cleanup success with a live adopted
child, actual process crash, retained unknown intent, lost-response/reopen without
replay, strict wire/association and durable receipt/custody refusal. These tests
are source evidence, not actual host approval, installed equivalence or BAU proof.
