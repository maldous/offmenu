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
