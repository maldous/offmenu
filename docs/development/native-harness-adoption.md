# Native harness adoption preflight

UIF-130's `tools/delivery/native_harness_adoption.py` prepares a finite, immutable
packet for the sole integration/adoption owner. It does not install, upgrade,
start/stop services, acquire claims, change permissions, access credentials or
create task state. The owner consumes this preflight while preparing the exact
reviewed adoption route. Existing runtime, attempts, leases, jobs, uncertain
effects and permanent installer receipts remain in their original custody.

## Owner workflow

1. Select the exact coherent candidate with the existing shared
   `validate_release_candidate` contract. Stage only explicitly selected,
   nonsecret metadata and candidate artifacts under an existing private evidence
   directory. Preserve original files; references pin exact file bytes.
2. Bind each component UIF-121 through UIF-129 to its latest independently
   accepted source/test/review references. Root reconciles superseded findings
   before supplying acceptance; this tool cannot discover which review is latest.
3. Select an independently qualified coherent validation handoff. Its complete
   source and output identity must match the selected candidate; its recorded
   independent review must accept, its operation must succeed, and its effect
   must be verified. Original executor-policy pins remain unchanged, separate
   from the new source release-policy fingerprint.
4. Retain the original runtime/source/config snapshot, original install receipts,
   rollback custody and a fresh stopped/zero-inflight/children-gone witness. The
   preflight reads selected evidence, not a live task database or host census.
5. Call `prepare` from the authorized owner's existing process, supplying accepted
   references separately from request JSON. Save its returned bytes in existing
   private custody without overwriting prior packets and pin their SHA-256.
6. Resolve every hold through the existing owner. Re-run preflight against the
   same or explicitly newly selected evidence after changes. Reconcile unknown
   effects under their original IDs before any retry. An offline packet never
   supplies actual host mandatory confirmations or installed/active readback.

```python
from native_harness_adoption import prepare
from native_harness_contract import load_release_policy

# request and accepted are selected by the existing authorized owner, not by a
# coding child or an untrusted request's claims. Paths below are illustrative.
packet_bytes = prepare(
    request,
    load_release_policy('config/delivery-release-policy.json'),
    evidence_root='/private/existing-adoption-evidence',
    accepted={
        'components': latest_owner_accepted_component_references,
        'coherent_validation': exact_owner_qualified_validation_reference,
    },
)
```

The returned bytes use the protected owner's canonical encoding. Changing any
selected request, evidence pin or acceptance context changes the packet. Its
evaluation time and stop-witness expiry are explicit. Retaining a packet does
not extend witness freshness; the owner must recheck actual stopped state and
inflight operations at the host mutation boundary. No packet consumer or executor
is installed by this module.

For inspection without owner acceptance:

```sh
PYTHONPATH=src:tools/delivery /path/to/existing/python tools/delivery/native_harness_adoption.py \
  .delivery/adoption-request.json --policy config/delivery-release-policy.json \
  --evidence-root /private/existing-adoption-evidence
```

This CLI cannot mark component/coherent acceptance: those remain held until the
owner supplies its separately qualified context through the Python API. Exit
zero means a packet was produced. Rejected inputs exit two with a fixed error
that does not echo paths or contents. There are no callback, command, permission,
overwrite, force, execute or acceptance flags.

## Request and evidence interface

All objects have exactly the fields listed here. References are
`{path, sha256}` with a canonical relative path under the explicitly selected
evidence root and a lowercase 64-character file-byte digest. Reference files must
be single-link regular files; descriptor-relative reads refuse symlink traversal.
The shared canonical JSON fingerprint bounds request/output structure. Ordinary
metadata/artifacts are capped at 256 KiB each; protected owner/publisher prepared
manifests retain their existing 8/16 MiB bounds. Aggregate selected reads are
capped at 64 MiB. Large payloads/backups remain in existing custody; select their
bounded nonsecret manifests rather than scanning or copying their contents.

The request is `version: 1`, `kind: native-harness-adoption-request-v1`, with:

| Field | Selected value |
| --- | --- |
| `owner` | Bounded existing owner identity. |
| `candidate` | Reference to the shared immutable release-candidate JSON. |
| `components` | Exactly UIF-121 through UIF-129, each with `source`, `tests`, `review` references. Existing result/review formats remain opaque; owner acceptance must qualify their meaning. |
| `coherent_validation` | Reference to the shared v1 handoff described above. Its origin, evidence, review and operation receipt pins are also read and checked. |
| `legacy_snapshot` | Reference to the snapshot described below. |
| `stop_witness` | Reference to the bounded stop witness described below. |
| `rollback` | Reference to the original snapshot-bound custody packet described below. |
| `target` | Exact requested closure described below. |
| `credential_references` | One to sixteen unique existing uppercase reference names, such as `EXISTING_GITHUB_APP_REFERENCE`. No credential contents, paths or new credentials. |
| `effects` | Up to 64 references to original shared handoffs with operations. Unknown/pending/missing effects and submitted/running/unknown operations hold; original identities are returned unchanged. |
| `readback` | Exact expected `source_head`, `source_tree`, `policy_sha256`, `closure_sha256`, `config_sha256`, `dependencies_sha256`. Expectations alone are never observations. |

`target` fields are `source_head`, `source_tree`, `policy_sha256`, `paths`, `files`,
`dependencies`, `config`, `owner_manifest`, `publisher_manifest`. The first three
match the candidate source; `files` exactly matches candidate artifacts, whose
bytes are checked. `dependencies` and `config` reference bounded nonsecret
closure/config manifests; never select credential-bearing configuration.
`owner_manifest` and `publisher_manifest` select privately retained preparation
evidence: their byte pins are checked, without calling or replacing either
installer's deeper qualification. Do not use an old installer's prepare function
to misrepresent a new coherent source it does not support. The config/dependency
readback hashes identify these selected manifests, not fabricated live readback.

`paths` must equal the module's `TARGETS`, derived from existing installer
constants: owner source `/opt/offmenu-stokowski-current/source`, owner venv
`/opt/offmenu-stokowski-current/venv`, owner config
`/etc/offmenu-stokowski-current`, publisher `/opt/offmenu-publisher`, and publisher
config `/etc/offmenu-publisher`. `closure_sha256` is the shared canonical
`fingerprint(target)`, distinct from all file-byte digests.

The legacy snapshot is `version: 1`, `kind: native-legacy-snapshot-v1` and fields
`runtime_path`, `source_head`, `source_tree`, `config_sha256`, `runtime_sha256`,
`source_sha256`, `install_receipts`. The three SHA-256 fields pin preserved
nonsecret snapshot manifests, not copied runtime data or secrets. Original
installation receipt references are read and retained, never edited or replayed.

The stop witness is `version: 1`, `kind: native-stop-witness-v1`, with
`snapshot_sha256`, `observed_at` (Unix seconds), `stopped`, `inflight`,
`children_gone`, `operation_ids`. It binds the exact snapshot's file-byte digest.
Freshness qualification requires explicit true stopped/children-gone, integer
zero inflight, no unresolved operation IDs, and an observation no more than
300 seconds old and never in the future. False, null, positive inflight or stale
observations produce a hold. This verifies witness consistency/freshness, not
the truth of the asserted host state.

Rollback custody is `version: 1`, `kind: native-rollback-custody-v1`, with
`snapshot_sha256`, `custodian`, `artifacts`, `verification`. `artifacts` has exactly
`source`, `config`, `runtime` references; each digest must match the corresponding
original snapshot manifest pin, and each selected file is read. `verification`
references existing owner-qualified restore/custody evidence. Its meaning and
the actual availability/restorability of underlying backups require owner review;
hash checks cannot prove recovery. Changed/re-pinned metadata cannot silently
replace the original snapshot. There is no rollback executor.

## Installer gaps and explicit holds

`protected_owner_install` provides safe bounded regular-file reads, duplicate-key
rejection and canonical bytes reused here. Its `install` has fixed targets and
refuses any prior `/var/lib/offmenu-publisher/protected-current-install.json`,
including a failed/partial intent. It never adopts or overwrites existing files.

`protected_publisher_install` has a fixed source head
`bf9bd13fef1bad2f5994b54ae7eafbe1ff4d78d5`, fixed consumers and no-overwrite targets.
Its `/var/lib/offmenu-publisher/publisher-install.jsonl` is a permanent no-replay
fence. Neither interface implements replacement of a live installed closure.

A new coherent build therefore needs a separately reviewed typed upgrade route
that preserves these original receipts, validates exact prior and next closures,
retains rollback custody, rechecks zero inflight and performs actual installed
readback. Clearing receipts, changing fixed source constants, repointing JSON or
reusing a first-install function is not that route. Every packet retains
`REVIEWED_TYPED_UPGRADE_ROUTE_REQUIRED` and
`ACTUAL_HOST_CONFIRMATIONS_AND_READBACK_REQUIRED`; input claims cannot waive them.

Milestones remain distinct: latest component source readiness and exact coherent
validation may be established only from owner context plus matching evidence.
Released source, installed/adopted, active observed and legacy retired remain
unknown here. No service start or install receipt implies BAU acceptance. Legacy
custody remains intact until separately qualified retirement. Delivery BAU
activation requires all source/review/qualification gates and actual mandatory
host confirmations. Product deployment, CIX, Actions, new credentials/spend and
historical-worker restart remain forbidden.

## Executable upgrade procedure source

`native_harness_upgrade.py` adds a separately reviewed source procedure. It is
not installed or authorized on the actual host by these tests. It has no CLI,
dynamic module loader, JSON-selected commands, callbacks or permission actions.
The old protected installers remain unchanged. Their receipts are preserved,
read back by exact byte hash, and never cleared to permit another installation.

The sole owner imports `execute(plan_bytes, upgrade, admission=..., quiescence=...)`
only after separately reviewing this executable route and receiving actual host
mandatory confirmations. `OwnerAdmission` is a trusted Python capability binding
the owner, exact preflight byte hash, upgrade digest, host-confirmation evidence
hash and a short expiry. It is not authentication merely because someone can
construct the class. No worker JSON may issue it. `Quiescence` binds the original
snapshot, native observation evidence, observation time, integer zero inflight,
stopped descendants and no unresolved operation IDs. The actual native owners
must qualify that observation; the procedure cannot infer it from a successful
coding receipt or census arbitrary remote jobs.

The typed upgrade object has exactly `version: 1`,
`kind: native-harness-upgrade-v1`, `operation_id` (64 lowercase hex),
`preflight_sha256`, `old`, `new`, and `legacy_receipts`. `old` and `new` have
exactly the five fixed target roles from `TARGETS`. Each closure contains
`directories` and `files` maps. Directory keys are canonical relative paths,
with `""` identifying the closure root; metadata is `{mode, uid, gid}`. File
metadata adds `{size, sha256}`. Numeric modes are observed expectations, never
permissions to apply. Parent directories must be declared, UID must match the
admitted host owner, and group/world writable or special mode bits are refused.
Unexpected entries, links, hardlinks, missing files, unsafe custody and byte or
mode drift fail closed. Known credential and log paths are excluded. Source and
configuration selected by the owner must contain reference names, never secrets.

`upgrade_digest` is SHA-256 of the protected owner's canonical newline-terminated
JSON bytes, capped at 32 MiB. It intentionally differs from the shared bounded
JSON fingerprint used for the much smaller preflight contract. Whole source
closures may exceed that contract's 64-field/object bound. Closure reads have
finite 50,000-entry, 64 MiB/file and 1 GiB/closure limits, and inspect only the
explicit selected closure. Old source/venv/config descriptor bytes must match
the original snapshot's source/runtime/config manifest hashes. New config and
dependency descriptors must match the preflight pins. Selected candidate
artifact pins must appear in the new owner source, and old/new `.git/HEAD` bytes
must match the admitted heads. Actual Git tree truth and complete source/component
association remain independently qualified owner inputs, never inferred from a
branch name. Root must compose the accepted UIF-127 correction `731ce2034` and
UIF-128 correction `a6437a416` (or independently accepted successors); the
upgrade worker's older source checkout is not that coherent installed closure.

The owner stages each complete sealed directory beside its eventual target as
`.native-upgrade-<operation_id>-<role>.new`. Rollback custody uses the corresponding
`.old` sibling; existing custody refuses replacement. Staging/qualification is
an explicit owner action outside this module. The procedure:

1. Takes the existing coordinator and repository-owner locks, without creating
   replacement locks. Reads the fixed coordinator service's actual inactive,
   dead, zero-PID state and checks the separately qualified fresh native witness.
2. Verifies all old/staged closures and original installer receipts before any
   move. Writes and syncs a permanent old-closure fence, then operation intent.
   A crash even between those receipts suppresses another operation ID against
   the same old closure. It creates no queue or continuing controller.
3. Rechecks stopped/native state and each selected closure, then uses Linux
   create-only rename to move old target to `.old`, then staged target into place.
   Unsupported atomic rename, cross-device moves and existing targets hold.
4. Reads back exact installed and rollback bytes/modes, binds both permanent
   intents, then writes a create-only installed receipt. No service is started.

Any interruption retains the original intent and partial custody. `observe`
performs read-only reconciliation of that same operation, with distinct staged,
installed and rollback axes. It never retries, removes a receipt, changes IDs or
automatically rolls back a multi-directory partial move. The owner must qualify
an explicit recovery procedure for the observed partial state. Even a fully
installed closure is not active, released source, functional BAU or legacy
retirement acceptance.

Every intent write, individual rename (including the second rename of a role),
and installed-receipt write has a fresh admission/native/stopped-service guard
after preceding closure verification. Expiry and witness freshness are checked
again after service readback itself. Expiry between the two renames leaves the
first move's original custody and permanent intent intact, refuses the second
move and never authorizes replay. Tests advance a deterministic clock during
verification, between renames and during service readback, and change actual
synthetic service state after verification.

After separately authorized owner-managed activation, `verify_active` checks
installed/rollback bytes both before and after fixed service readback. It requires
an active/running positive PID and exactly the maintained launch argv:
`<protected-python> <protected-stokowski_adapter.py> --current --runtime <bound-runtime>`.
The runtime is retained from the admitted preflight in the permanent intent.
Script/flag tokens supplied as arguments to another script, `-c`, `-m`, extra
flags, reordered arguments or a different runtime fail closed. This deliberately
does not infer support for an unreviewed alternate launcher. Both observations
require unchanged service/PID binding. It reads
only bounded process command metadata and never returns command contents. It
does not start the service or claim continuous liveness or functional acceptance.

Production `Host` requires real UID/EUID root, safe root-owned parent custody,
existing owner locks and sealed target metadata. Existing publisher-owned or
caller-owned lock/runtime custody may fail those strict checks. The owner must
qualify the actual custody/interface seam; this source does not change ownership,
grant permissions or silently relax checks to pass it. A private test seam works
only under a disposable `/tmp` root for an unprivileged caller, with a fixed fake
service observer. All executed upgrade tests use that seam; neither actual host
services nor installed files, credentials or permissions are inspected or changed.
