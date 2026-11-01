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
4. Retain opaque identities of the four original directories, the fixed old
   publisher config hash/key metadata, original receipts and a fresh
   stopped/zero-inflight/children-gone witness. No full legacy audit or restore
   drill is required to restore BAU. The
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
`source_sha256`, `install_receipts`. The three SHA-256 fields pin canonical opaque directory custody records for old
owner config, owner venv and owner source respectively. They assert root
identity custody, not old byte coverage or copied runtime data/secrets. Known
old source/tree/config-binding headers remain declared owner evidence. Original
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
original opaque custody record pin, and each selected metadata record is read.
`verification` references existing retained-custody/inspection evidence only.
It is not a restore exercise, legacy environment audit or BAU gate for optional
rollback tooling. Changed/re-pinned metadata cannot silently replace the original
snapshot. There is no automatic restore or rollback executor.

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
exactly the five fixed target roles from `TARGETS`. For the four OLD directory
roles, the record is exactly `{kind: "retained-directory-v1", dev, ino, uid, gid, mode}`.
It binds the original root directory only; the procedure never lists, reads,
hashes or imports its children. Production roots remain UID0, safe permissions,
and no-follow directory identity must match both FD and named entry. OLD
publisher config remains the fixed config.json hash/metadata plus retained
directory/key context below. Each NEW closure contains
`directories` and `files` maps. Directory keys are canonical relative paths,
with `""` identifying the closure root; metadata is `{mode, uid, gid}`. File
metadata adds `{size, sha256}`. Numeric modes are observed expectations, never
permissions to apply. Parent directories must be declared, UID must match the
admitted host owner, and group/world writable or special mode bits are refused.
For NEW payloads, unexpected entries, links, hardlinks, missing files, unsafe
custody and byte or mode drift fail closed. Known credential and log paths are excluded. Source and
configuration selected by the owner must contain reference names, never secrets.

`upgrade_digest` is SHA-256 of the protected owner's canonical newline-terminated
JSON bytes, capped at 32 MiB. It intentionally differs from the shared bounded
JSON fingerprint used for the much smaller preflight contract. Whole source
closures may exceed that contract's 64-field/object bound. Closure reads have
finite 50,000-entry, 64 MiB/file and 1 GiB/closure limits, and inspect only the
explicit selected NEW closure. Old source/venv/config opaque record bytes must
match the original snapshot's source/runtime/config descriptor hashes. Those
hashes cover only custody metadata, never full old contents. New config and
dependency descriptors must match the preflight pins. Selected candidate
artifact pins must appear in the new owner source, and NEW `.git/HEAD` bytes
must match the admitted new head. No legacy Git header schema or old dependency
CA/RECORD/body audit is required. Actual Git tree truth and complete source/component
association remain independently qualified owner inputs, never inferred from a
branch name. Root must compose the accepted UIF-127 correction `731ce2034` and
UIF-128 correction `a6437a416` (or independently accepted successors); the
upgrade worker's older source checkout is not that coherent installed closure.

For the four directory roles, the owner stages each complete sealed directory beside its eventual target as
`.native-upgrade-<operation_id>-<role>.new`. Rollback custody uses the corresponding
`.old` sibling; existing custody refuses replacement. Staging/qualification is
an explicit owner action outside this module. The publisher config role uses the
fixed-file exception below, preserving its credential directory/key in place.
The procedure:

1. Takes the existing coordinator and repository-owner locks, without creating
   replacement locks. Reads the fixed coordinator service's actual inactive,
   dead, zero-PID state and checks the separately qualified fresh native witness.
2. Verifies old root identities, the fixed old publisher config hash, complete
   NEW staged closures and original installer receipt pins before any move. Writes and syncs a permanent old-closure fence, then operation intent.
   A crash even between those receipts suppresses another operation ID against
   the same old closure. It creates no queue or continuing controller.
3. Rechecks stopped/native state, old root custody and NEW closure, then uses Linux
   create-only rename to move old target to `.old`, then staged target into place.
   Unsupported atomic rename, cross-device moves and existing targets hold.
4. Reads back full NEW installed bytes/modes, exact retained OLD directory-root
   identity and old publisher config hash, binds both permanent intents, then
   writes a create-only installed receipt. No service is started.

Any interruption retains the original intent and partial custody. `observe`
performs read-only reconciliation of that same operation, with distinct staged,
installed and rollback axes. It never retries, removes a receipt, changes IDs or
automatically rolls back a multi-directory partial move. The owner must qualify
an explicit recovery procedure for the observed partial state. Even a fully
installed closure is not active, released source, functional BAU or legacy
retirement acceptance.

The existing result key `rollback_verified` is retained for caller compatibility
and means **retained custody only**. `old_custody_coverage` states
`directory-root-identity-only; publisher-old-config-file-hash`; the four old
backup axes report `retained-identity`, never restored or full-byte verified.
Existing partial/uncertain operations retain their original IDs and receipts.
A prior-format uncertain operation remains unknown; do not reinterpret it or
issue a new ID to bypass a fence. No automatic restore, cleanup or retry follows.

Legacy directories may contain old links, logs, public CA variants or Git
formats. They stay intact without examination. The terminal history reference
`.delivery/native-ssh-publication/4d589c0f73405f3fa8324bc88ec41eb59425bfb5c67fdc544a3cf5a85d6c70d2.json`
stays inside the retained old source, located through the adoption receipt's
old-directory identity/backup mapping. It is not copied into the new payload,
read, migrated or given a rewritten historical path by the upgrade. The current
published successor already uses the unchanged user-private namespace; existing
protected-source mapping continues to the same runtime-root parent. No current
unit flags, restore project or history copy is needed for this state continuity.
An actual startup failure, rather than a speculative compatibility audit, is the
trigger for a separately bounded existing-owner fix. Existing verified GitHub
merge/commit facts remain distinct from unknown Linear metadata; this upgrade
adds no claim handover or legacy-control migration.

The real read-only owner snapshot's active service and unknown native work are
not a stop/quiescence witness. Actual stopped service, three locks, all permitted
writer/descendant/backend quiescence, source/host permission and final time checks
remain required. Optional rollback tooling/drills/full-old-environment audits
are deferred; NEW payload qualification and real BAU readback are not relaxed.

Every intent write, individual rename (including the second rename of a role),
and installed-receipt write has a fresh admission/native/stopped-service guard
after preceding closure verification. Expiry and witness freshness are checked
again after service readback itself. After **all** blocking lock/key custody
checks, a final pure clock gate checks admission expiry and native/lock/publisher
custody freshness. It performs no filesystem/service reads or callbacks. The
low-level mutation methods repeat that pure gate after their own preparation,
immediately before each actual syscall: rename arguments and publisher-file key
checks are complete before `renameat2`; path resolution/encoding are complete
before exclusive receipt creation. Every new-receipt mode/content write is also
pure-gated, including each partial-write continuation. Only durability sync/close
of already-authorized partial data may continue as cleanup after expiry; no
further content, mode or rename is authorized. An ephemeral frozen `MutationWindow`
binds those existing accepted observations within `execute` and is cleared on
exit; it adds no JSON authority, manager or queue. Expiry between the two renames leaves the
first move's original custody and permanent intent intact, refuses the second
move and never authorizes replay. Tests advance a deterministic clock during
verification, between renames and during service readback, and change actual
synthetic service state after verification. UGC1 regression tests additionally
advance time after the last successful key/lock read, after the publisher move's
own key read, after create-path preparation/exclusive open and during a partial
intent write. They assert no expired mutation syscall, retained original/partial
custody and permanent no-replay behavior.

After separately authorized owner-managed activation, `verify_active` checks
full NEW installed bytes and retained OLD custody both before and after fixed
service readback. It requires
an active/running positive PID and exactly the maintained launch argv:
`<protected-python> <protected-stokowski_adapter.py> --current --runtime <bound-runtime>`.
The runtime is retained from the admitted preflight in the permanent intent.
Script/flag tokens supplied as arguments to another script, `-c`, `-m`, extra
flags, reordered arguments or a different runtime fail closed. This deliberately
does not infer support for an unreviewed alternate launcher. Both observations
require unchanged service/PID binding. It reads
only bounded process command metadata and never returns command contents. It
does not start the service or claim continuous liveness or functional acceptance.

Production `Host` requires real UID/EUID root, safe root-owned static mutation
parents and sealed target metadata. Existing caller/publisher lock custody uses
the separate exact admission below; it never weakens static mutation custody.
The owner must qualify the actual custody/interface seam; this source does not
change ownership, grant permissions or infer unknown metadata. A private test seam works
only under a disposable `/tmp` root for an unprivileged caller, with a fixed fake
service observer. All executed upgrade tests use that seam; neither actual host
services nor installed files, credentials or permissions are inspected or changed.

## Exact existing lock custody

The established contracts use caller-owned runtime state and publisher-owned
integration state. `protected_owner_install` pins the original runtime's
UID/GID/device/inode; `protected_publisher_install` creates integration state as
984:976 mode 0700. The coordinator holds its per-runtime lock and then the shared
`config.runtime_root` lock. Requiring every lock/ancestor to be root-owned would
reject those contracts; omitting the shared-root lock would miss serialization.

`execute(..., lock_custody=...)` now requires a frozen, root-qualified
`LockCustody` object separately from worker/request JSON. `OwnerAdmission` must
bind `lock_custody_sha256 = upgrade_digest(dataclasses.asdict(custody))`. A missing
record, missing metadata or mismatched digest is a hold; the module never derives
new permissions from whatever it finds on disk. Existing five-field admission
callers must supply this additional context before productive execution.

`LockCustody` contains `runtime`, `runtime_root`, `config_manifest_sha256`,
`protected_binding_evidence_sha256`, `writers_quiescence_sha256`, `observed_at`
and a tuple of exactly three `LockRecord` objects, in this order:

1. `runtime-coordinator`: `<qualified runtime>/coordinator.lock`.
2. `shared-root-coordinator`: `<qualified runtime_root>/coordinator.lock`.
3. `publisher-repository`: `/var/lib/offmenu-publisher/integration/repository-owner.lock`.

The runtime must equal the admitted old snapshot. The shared root must contain
it and satisfy the existing `.delivery/stokowski` contract. Root independently
qualifies both paths against the protected config/binding evidence; config
manifest and writer-quiescence pins must match the preflight/native observation.
Custody observation is fresh for at most 300 seconds, never future-dated.

Each `LockRecord` contains `role`, exact derived `path`, the complete root-to-parent
tuple of `ParentCustody(path, identity)`, file `identity`, `policy` and a tuple of
`permitted_writers`. `NodeIdentity` pins `dev`, `ino`, `uid`, `gid`, numeric `mode`
and `nlink`. Unknown shared-root/publisher observations are not valid identities.
Every file is regular/single-link, every parent is a directory, shared parent
pins must agree, and the three lock inodes must be distinct.

Production predicates are fixed:

| Policy | File custody | Explicit permitted writers |
| --- | --- | --- |
| `caller-private-v1` | 1000:1000, 0600 | `uid:1000` |
| `caller-historical-0664-v1` | 1000:1000, exactly 0664 | `uid:1000`, `gid:1000` |
| `publisher-existing-v1` | 984:976, 0600 | `uid:984` |

Historical 0664 is permitted only for the two caller lock roles under an exact
root-approved metadata/policy/writer association. Merely pinning a group-writable
file does not select that policy. Caller-owned ancestor metadata must likewise
match exact admitted pins: private policies allow 0700/0750/0755; the explicit
historical policy additionally allows caller1000:1000 ancestor modes 0770/0775.
No world-writable ancestor is accepted. Production `/` remains root-owned;
root-owned ancestors never gain a group-write exception. Publisher integration
itself must match 984:976/0700, with root-controlled ancestors. No generic
arbitrary-owner or group-write exemption is provided. Different actual metadata
requires owner reconciliation and independent source review, never auto-adoption.

Lock traversal is isolated from `Host.path`, which still enforces root custody
for every static create/move/verify operation. The lock-only path uses retained
directory descriptors, no-follow opens and read-only existing file descriptors;
it never creates, appends to, renames, unlinks, chmods or chowns a lock. Exclusive
nonblocking flock uses the same original inode as the existing owner. Contention
closes acquired descriptors without an upgrade intent. Each mutation guard
rechecks freshness, all descriptor metadata, and each current directory entry
against its held FD, on both sides of service observation. Replacement, alias,
mode/ownership drift or parent substitution holds without requalifying new state.

These checks do not prevent an uncooperative permitted principal from replacing
actor-owned names between observations. Root must qualify and maintain the
quiescence of **all** permitted writers, including group/ACL access, under the
existing owner contracts. If that prerequisite cannot be established, the route
remains blocked; no chmod, replacement lock, extra claim or alternate coordinator
is a substitute. The code does not inspect group membership, credentials or
denied state to invent that qualification.

The actual worker remains EUID1000. Actual shared-root and publisher lock metadata,
privileged immutable loader/admission and mandatory host confirmations remain
unqualified. Tests substitute current test UID/GID only inside the explicit
unprivileged `/tmp` seam; pure production-policy tests exercise fixed 1000/984
predicates without host access. Returned observations and permanent intent record
`host_scope: synthetic` for that seam. Normal runtime glue must never report
productive activation from synthetic observation. No production adapter may
select the private seam through JSON or ordinary CLI flags.

## Preserve the publisher key with a fixed config-file swap

The existing publisher loads its private key at the fixed path
`/etc/offmenu-publisher/github-app-private-key.pem`. Complete-directory verification
would reject that key under the unchanged `.pem` payload prohibition; replacing
the whole directory would move/remove its credential custody. Neither behavior
is an acceptable upgrade. `TARGETS.publisher_config` and the preflight path
contract remain `/etc/offmenu-publisher`, but this role now operates only on:

- `/etc/offmenu-publisher/config.json`;
- `/etc/offmenu-publisher/.native-upgrade-<operation_id>-publisher_config.new.json`;
- `/etc/offmenu-publisher/.native-upgrade-<operation_id>-publisher_config.old.json`.

The fixed directory is never renamed. The key is never opened, read, copied,
hashed, staged, backed up or renamed by this procedure. Directory contents are
never enumerated for this role. Other four roles keep complete-directory
verification; private-key/log exclusion remains unchanged, with only the selected
public-CA dependency exception below. Even the move
helper refuses a publisher directory rename or a key/rollback path selector.

The role's old/new descriptor keeps the `directories`/`files` shape, but accepts
exactly `directories: {"": {mode, uid, gid}}` and
`files: {"config.json": {mode, uid, gid, size, sha256}}`. These describe only the
existing retained directory and the old/new **nonsecret** config file. Production
file custody is exactly root0:976/0440, positive size at most 1 MiB; parent custody
is root0:976/0750. Root independently validates the new config's actual semantics
through the accepted UIF-127 publisher contract before issuing upgrade admission.
Byte association here does not replace that validation and never relaxes the old
first-install `SOURCE_HEAD` or no-overwrite fences.

`execute`, `observe` and `verify_active` take the separately qualified frozen
`publisher_config_custody=PublisherConfigCustody(...)`. `OwnerAdmission` binds
`publisher_config_custody_sha256 = upgrade_digest(dataclasses.asdict(custody))`.
Custody contains `directory` and `key` `NodeIdentity` records, `key_size`,
`key_mtime_ns`, `key_ctime_ns`, `qualification_sha256` and `observed_at`. There
are no selected paths or credential contents. Key custody must match the existing
publisher reader: a regular single-link root0:976/0440 file, positive size at most
64 KiB. Unknown/denied metadata cannot be filled from assumptions or inferred by
an unprivileged worker. Actual old config bytes and parent/key metadata still
need authorized privileged qualification.

The procedure retains the original directory FD and compares its metadata and
current name-to-FD association. It uses no-follow metadata lookup of the fixed
key basename to compare device/inode/UID/GID/mode/link count, size and timestamps.
No key FD is opened. Every mutation guard checks directory/key custody before
and after service readback; actual file renames occur descriptor-relative inside
that original directory, with create-only semantics and per-rename freshness.
It moves `config.json` to the fixed `.old.json` slot, then `.new.json` to
`config.json`. Interrupted second rename leaves both old backup and staged new
file observable and the original directory/key untouched. Permanent operation
and old-closure intents still forbid replay, including a new operation ID.

Custody observations must be fresh for mutation. Later **read-only** installed,
rollback and active checks reuse the intent-bound immutable custody expectations
and make new actual metadata observations, reporting `publisher_observed_at`.
They do not refresh or issue mutation admission. Missing/wrong custody, changed
directory/key metadata, absent config or changed bytes hold acceptance. This
distinction permits recovery/readback after the original short-lived admission
expires without replay or rewriting any receipt. There is no automatic rollback
or forced file replacement.

Tests retain all prior lock/expiry/no-replay checks and add a temporary fixture
that actually contains a synthetic `.pem` key. Instrumentation fails on any key
open/read or publisher-directory enumeration during execution/readback. Only the
test, outside those guards, reads its synthetic sentinel to confirm unchanged
bytes; directory/key identity and metadata are also unchanged. Focused cases cover
unknown custody, key/directory drift, unsupported payload/mode, interrupted second
file rename, later read-only observation and rejected key/directory move forms.
Those fixtures remain explicitly synthetic and do not qualify actual protected
config, credentials, installed source or activation.

## Selected public certifi resource

The dependency closure can legitimately contain certifi's public CA bundle.
`PUBLIC_CA_PATHS` allows only these exact role-relative paths:

- `owner_venv`: `lib/python3.12/site-packages/certifi/cacert.pem`;
- `publisher`: `venv/lib/python3.12/site-packages/certifi/cacert.pem`.

This is not a filename suffix exemption. `PublicCARecordPin` is a separately
owner-qualified PUBLICRECORD/blob association with `role`, `closure_sha256`,
`path`, `blob_sha256` and `public_record_sha256`. The independent selected blob
must match the selected closure's file pin and the actual read bytes. Root
qualifies the public record and dependency-blob provenance before admission;
the upgrade never invents the association from a worker's self-pinned payload.

When either exact resource is present in the NEW payload, `execute`, `observe`
and `verify_active` require `public_ca_pins`, a tuple covering its distinct
role/closure/path associations (at most two). No old dependency resource is
examined or requires a compatibility pin. `OwnerAdmission.public_ca_pins_sha256` binds
`upgrade_digest([dataclasses.asdict(pin) for pin in public_ca_pins])`; the permanent
intent retains that digest. Missing, changed, unrelated or incomplete selection
holds before dependency reads. If neither role contains the resource, both pins
and admission digest must be absent; no unused resource authority is carried.

Only the exact qualified role/path/blob may pass the `.pem` guard. Its actual
sealed file still has the ordinary metadata, regular/single-link, no-follow,
size, hash and drift checks. Other `.pem` paths, source/config roles, private-key
names, `.key` files and the protected publisher key remain prohibited. The
publisher key is still observed only through its fixed metadata custody, never
opened as a payload. Tests use synthetic public resources under both dependency
roles and reject wrong role/path/digest/closure, absent PUBLICRECORD pin, omitted
new-role selection, changed bytes and arbitrary PEM/private-key names. No
protected dependency file or actual key is read by these tests.


## Installed native coordinator launcher

The Foo protected coordinator uses
[`offmenu-stokowski-current-native.conf`](../../deploy/stokowski/offmenu-stokowski-current-native.conf)
as its service `ExecStart` override. This is the exact configuration applied for
UIF-131 to the existing protected runtime; its fixed paths are specific to that
installation. An authorised activation owner installs it as a root-owned service
drop-in, reloads the service configuration and controls the existing service's
restart. Copying this repository file does not activate a service.

The isolated interpreter retains `-E -s -B`. Its import path contains the sealed
`tools/delivery` and `src` directories instead of the launcher's working-directory
entry. The loader registers one adapter module under both `__main__` and
`stokowski_adapter` before executing the unchanged CLI. This preserves the
runtime's exact `CurrentWork` class identity and all existing ownership checks.
Direct script execution omitted `src`; a first `runpy` launcher supplied that
path but loaded a second adapter class through the canonical import.

Live verification used the original UIF-117 operation: the running coordinator
recorded and read back its exact source-integrated Linear milestone, then
observed the same effect on subsequent polls. This proves that handover, rather
than only interpreter import or service liveness. Coding/validation receipts,
PR194 and its merge retain their original identities. A source milestone does
not mark product delivery Done or demonstrate another backlog pickup.

The original service directives, credentials, environment restrictions, runtime
and installed package remain in place. The current `verify_active` helper only
recognises direct-script process arguments; it does not accept this `-c` launcher.
Do not claim that helper passed for this configuration. Use the actual selected
service arguments and the original operation's effect readback as the scoped
operational evidence until that separate diagnostic interface is updated.
