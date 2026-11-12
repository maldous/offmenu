# Developer delivery workflow

This is an on-demand local workflow, with an optional Windmill entrypoint. It
never schedules work, creates branches, merges, pushes or deploys. Task JSON is
reviewed executable configuration: commands run with your account's privileges.
Keep credentials out of arguments, task files and outputs. This is not a sandbox.

## Bootstrap

Use Python 3.12 for the delivery environment (the application retains its declared
Python support). From the repository root:

```sh
python3.12 scripts/bootstrap_delivery.py
python3.12 scripts/bootstrap_delivery.py --check
.venv-delivery/bin/python -m offmenu.delivery discover
.venv-delivery/bin/python -m offmenu.delivery check
.venv-delivery/bin/python scripts/check_final_layout.py
GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=gc.auto GIT_CONFIG_VALUE_0=0 \
  GIT_CONFIG_KEY_1=maintenance.auto GIT_CONFIG_VALUE_1=false \
  PYTHONPATH="$PWD/src:$PWD/tools/delivery" \
  .venv-delivery/bin/python -m unittest discover -s tests/delivery -v
```

Bootstrap creates only the ignored project-local `.venv-delivery/`. `--check` checks all locked versions without network; installation is repeatable from a clean checkout and never mutates system Python.

The optional `.[delivery]` extra pins the two direct dependencies; the lock pins
this verified Python 3.12 environment transitively. No provider, model or paid
inference is configured. LangGraph owns the finite graph and SQLite checkpoints;
LangChain core is its integration dependency, not a second autonomous manager.
LangSmith is installed transitively but tracing is disabled in graph execution
and child commands, even if a developer's shell enables it.

## Standalone and optional executor validation

The OffMenu package and pinned delivery bootstrap do not depend on the external
Stokowski package or a UIF checkout. Run the commands above in this checkout.
The delivery suite includes optional Stokowski executor integration tests; when
that executor is absent, those tests explicitly skip before installing fixtures.
The test invocation disables Git background maintenance only in its child
processes: process-supervision tests become subreapers, so detached maintenance
children would otherwise contaminate later process-budget assertions. It does
not change saved Git settings or relax any execution resource limits.
Report skipped integration coverage separately from passing standalone checks.
A standalone pass does not qualify the optional executor, its publisher, or a
merge. Its existing pinned validation profiles still require their dependencies
and positive, unskipped tests. Do not install Stokowski merely to build OffMenu.

## Reviewed task contract

Use the [routing and tracking runbook](../../docs/development/task-routing.md)
to select an execution lane, retain one operation owner and link its evidence.
The [validation handoff example](../../examples/validation-handoff.json) is
schema-valid illustrative input, not an admitted or executable production task.

Create a task JSON under ignored `.delivery/` with `version:1`, a lowercase hyphenated
`id`, `owner`, `purpose`, immutable `base_revision` (40-character HEAD SHA), an optional explicit `branch` (the generated task includes it),
`checks:[{id,argv,timeout,attempts,retry_safe}]` and
`accepted_outputs:{"relative/path":"sha256"}`. Use the actual desired file bytes'
hashes, not hashes invented by the runner. Checks are explicit argument arrays;
there is no implicit shell. A shell explicitly named in argv remains executable
code requiring review. Require meaningful behavior checks, not just file existence.
The standards document and ADR describe how to discover and evolve standards.

```sh
.venv-delivery/bin/python -m offmenu.delivery run .delivery/accepted-layout.json --pause-after standards
.venv-delivery/bin/python -m offmenu.delivery status .delivery/accepted-layout.json
.venv-delivery/bin/python -m offmenu.delivery inspect .delivery/accepted-layout.json
.venv-delivery/bin/python -m offmenu.delivery run .delivery/accepted-layout.json
```

`status` returns historical receipts. `inspect` adds a versioned, read-only JSON
observation of the recorded acceptance, current declared output hashes, selected
revision/branch, command states needing reconciliation, cancellation and checkpoint
availability. It neither takes the writer lock nor opens the checkpoint database,
retries commands or changes receipts. A zero exit means inspection completed;
inspect `outputs_match`, `identity_matches`, `reconciliation_required` and `reasons`.
This is not an atomic snapshot of a running writer, does not revalidate source or
execution evidence, and does not authorize resume, merge or deployment. Use the
existing runner/reconciliation flow for those decisions.

Create the local validation task with `python -m offmenu.delivery prepare --task-id accepted-layout --owner YOUR-NAME`, then inspect its JSON before running it. The generated task verifies the delivered standard and tests; it does not generate arbitrary application changes.

The first invocation deliberately checkpoints after discovery and standards.
The next `run` uses the same ID/input and persisted graph state. Completed checks
have durable receipts bound to the exact source and output bytes observed after the command. They are reused only while that evidence still matches. Before reporting acceptance, the graph
verifies every declared output hash. `status` reports recorded acceptance only;
it does not revalidate current files. `run` revalidates accepted output bytes.
A changed task with an old ID fails closed. A changed HEAD requires a newly
reviewed task. Tasks and acceptance receipts are bound to the exact selected branch as well as the checkout's absolute path, owner, and tracked/new source hashes (excluding declared outputs and the exact held paths listed in the standard). Source or branch drift blocks cached check reuse. Declared outputs may be generated by commands, so their initial bytes are not frozen as source input; instead each completed command records the actual output hashes (or absence). Later producers may change them, and final acceptance must match the last completed check evidence. External output drift invalidates cached acceptance. Reexecution requires all checks to have the original explicit safe-retry declaration and unspent attempt budget; otherwise the run blocks. Rechecking spends that budget and preserves the invalidation event. Check IDs cannot use control names `binding`, `cancel`, `accepted`, `graph`, `writer`, `event`, or the `event-` prefix.

Each check has a 1–600 second deadline, at most three explicitly safe attempts,
and a 1 MiB local log cap. One cooperative writer per checkout is admitted with a
nonblocking OS lock; unrelated developers and legacy runners do not honor that
lock. Do not run this against a checkout another tool is changing. The workflow
is finite (maximum 32 checks) and does not use Windmill's capability ceilings as
load targets. Returned JSON status `blocked` or `failed` is not accepted delivery.

## Recovery and cancellation

`.delivery/<task-id>/` contains the input binding, SQLite graph checkpoints,
immutable event files, bounded private logs and acceptance receipt. It is ignored
by Git. Retain it across developer/worker restarts on the same mount. These are
same-disk receipts, not off-host backups or distributed locks. Do not share the
SQLite file between hosts. Restrict runtime access to trusted developers.

```sh
.venv-delivery/bin/python -m offmenu.delivery cancel .delivery/accepted-layout.json
```

Cancellation records intent without waiting for the writer lock. The active
command is killed as a process group when observed; its final receipt establishes
whether it stopped. A crashed supervisor may leave children/effects uncertain. Unresolved command receipts block admission of every task in the checkout, even after its writer lock is released; explicit reconciliation is the only writer operation allowed through that hold.
Do not clear a lock marker, change IDs or rerun an uncertain step. Inspect the
exact local command, process tree and output artifacts first. A `running`,
`timed_out` or `cancelled` receipt requires explicit reconciliation. Provide a
private evidence JSON containing `observer`, `reason`, and
`process_tree_gone:true`, then:

```sh
.venv-delivery/bin/python -m offmenu.delivery reconcile .delivery/accepted-layout.json --check-id CHECK --outcome failed --evidence /private/reconciliation.json
```

A succeeded reconciliation additionally verifies all declared output hashes.
Failed reconciliation verifies the original task/owner/checkout identity without requiring source to be unchanged or even its manifest to survive. It records a stopped failure, leaves the original binding and historical check evidence untouched, and clears the unresolved-operation hold so the source can be repaired. It cannot mark changed source successful: normal execution, successful reconciliation and acceptance retain their source/branch/output checks. A failed reconciliation does not grant extra attempts; only remaining attempts
explicitly declared safe in the original task can run. Cancellation remains
terminal for that task and is not silently cleared. Arbitrary command effects
are not transactional or rolled back by LangGraph.

## Windmill boundary

`windmill_entrypoint.py` provides `main(task_path, action='status')` for review and
on-demand deployment to the existing worker. It requires the reviewed OffMenu
package and pinned dependencies preinstalled on a worker with `/offmenu` and its
private `.delivery` mount. It never forwards MCP credentials, installs packages,
creates resources, schedules work, or resumes prior workers. Use the existing
approved bridge to the checkout when Windmill cannot access that mount directly;
do not infer a shared filesystem from matching path names. This change validates
the adapter locally; live installation is a separate verified deployment step.

Use the same immutable task ID for retries. A remote timeout is uncertainty:
inspect the same local receipt and Windmill job before retrying. The adapter
raises failed/blocked outcomes so Windmill cannot interpret transport success as
accepted delivery. The local writer lock supplies admission without depending on
Windmill enterprise concurrency features. Existing platform job supervision and
storage remain separate; this runner does not replace their capacity/backup claims.

The Stokowski operation journal observes a running API wrapper for a finite 210s
grace (180s reviewed computation timeout plus 30s wrapper completion). A stale
wrapper permits only the existing status-only backend observation with its
original logical job identity, never a computation resubmit. Terminal acceptance
still requires the bound command/runner/policy and stopped child tree. A live
backend rearms the grace; missing or refused observations retain uncertainty.
Cancellation continues through the original backend control intent. Existing
operations remain bound to their reviewed executor hash; do not silently migrate
their IDs/specs to a new executor. These hooks require an admitted stage invocation;
they do not add continuous supervision, voice intake or native approval/session
continuation APIs. A 403 is a refusal, not evidence of a pending approval.

## Existing Windmill bridge and separate execution identity

The current connected Foo Workspace account exposes only workspace `foo`;
supported connector calls use `workspace_id="foo"`. See the
[current workspace binding and adapter mismatch](../../docs/development/execution-protocols.md#connected-windmill-workspace).
The typed dispatcher and checkpoint adapters still hardcode `offmenu`, so their
dependent execution remains held pending UIF-owned alignment and qualification.
Do not pass the old workspace to this connector, infer a grant from a script
name, or change a fixed wrapper's arguments to bypass its contract.

The bridge procedure below records the historically verified
`u/admin/foo_jobs_20261027` route in workspace `offmenu`; it is not current
connector admission or proof that a deployed wrapper has switched namespaces.
Retain existing operation identities and verify the actual owner, target and
binding through supported controls before any later authorized execution.
The historical route runs reviewed commands through the existing `offmenu-wm` SSH jail,
where the source is `/offmenu`. Use `mode=write` for graph checkpoint creation,
even when checks read source. Its service account cannot write the developer's
private `.delivery/`; do not loosen that directory's permissions.

Create a service-owned source workspace under the already approved data mount.
The source repo is explicitly trusted for this clone invocation only; no global
Git trust setting or access grant is changed. `--no-local` and the explicit
upload-pack command propagate that narrow trust to the local Git server process.
Use a new chosen workspace/task ID per reviewed immutable source version and
reconcile an uncertain prior job before creating another:

```sh
git clone --no-local --upload-pack='git -c safe.directory=/offmenu/.git -c safe.directory=/offmenu upload-pack' --single-branch --branch feature/langgraph-delivery-standardization /offmenu /offmenu/data/.offmenu-platform/workspaces/SELECTED-WORKSPACE
```

Inside that new clone, use the existing project interpreter read-only:

```sh
PYTHONPATH=src /offmenu/.venv-delivery/bin/python -m offmenu.delivery prepare --task-id SELECTED-TASK --owner offmenu-windmill-writer
```

```sh
PYTHONPATH=src /offmenu/.venv-delivery/bin/python -m offmenu.delivery run .delivery/SELECTED-TASK.json --pause-after standards
```

A later Windmill job runs the same `run` command without `--pause-after`. Task,
checkpoint and acceptance IDs remain stable across those jobs. Inspect graph
acceptance, not merely the supervisor's exit0. Reentry revalidates output hashes
without rerunning successful checks. Keep source checkouts and runtime state
owned by their execution identity; never reuse another actor's private task root
or clear permissions/markers to force admission.

Checkpoints predating exact branch/output evidence remain retained historical records. They are not silently upgraded into new verification evidence; the runner refuses to reuse their incomplete binding. Reconcile their recorded outcome and prepare a reviewed task on the fixed source.

## Alternate checkout mounts

An editable install records its installation path. The existing SSH jail mounts
this checkout at `/offmenu`, not `/home/user/src/offmenu`. For that bridge, run
package commands with `PYTHONPATH=/offmenu/src` (or `PYTHONPATH=src` after changing
to an isolated workspace). The pinned interpreter still supplies dependencies.
Do not assume a host editable path exists inside a jail. For the existing
explicitly trusted canonical repository, process-scoped Git safe.directory may
select `/offmenu`; do not change global trust or broaden data permissions.

An isolated Windmill clone owns its `.delivery/` checkpoints and uses its own
`src` path; the canonical developer checkpoint directory remains private.

See the [architecture handover](../../docs/development/delivery-architecture.md)
for records versus checkpoints, proven adapters and remaining optional capabilities.

## Parallel operating capacity

Use the reviewed [8/16/32/64 capacity policy](capacity-policy.json),
[parallel task admission](../../docs/development/parallel-capacity.md) and
[protocol handover](../../docs/development/execution-protocols.md). The earlier
one-issue pilot receipts remain historical proof, not current capacity limits.

## Evidence-bound develop integration

ADR 0005 and `integration-policy.json` enable the integration controller for the
existing authenticated connector owner. A coding worker does not publish an
observation or invoke this gateway with its own report as authority.

The publisher reads GitHub/Linear through its authenticated connectors, and reads
the exact terminal Windmill operation and immutable candidate binding on Foo.
It invokes `.venv-delivery/bin/python -m offmenu.delivery.integration step`
with `--directory`, `--binding`, `--observation`, and the shared
`--claim-root /home/user/src/offmenu/.delivery/integration`. The resulting typed
action is consumed by `integration-gateway.mjs`: it refreshes head/base, uses the
normal exact-head merge API, records its known/unknown outcome, and obtains a
fresh observation. Canonical merge parents/tree and develop ancestry must match
before it requests a Linear Done update. The gateway consumes that metadata
action and any immediately returned bounded retry within the same finite invocation. A timeout never implies that a mutation did not execute.

The same gateway accepts injected authenticated GitHub/Linear adapters; it does
not create credentials or turn a coding child into an integration identity.
Repository claims, observations, graph checkpoints and API receipts stay private
under `.delivery/integration`. A controller restart reconciles retained intent;
it does not resubmit. Policy/review changes bind a new candidate. Refused actions
remain stopped unless genuinely new authority is recorded through normal review.

An enabled policy is distinct from publisher service availability. The current
publisher route uses the durable cloud connector owner's context; native Foo has
no independently configured GitHub API grant. Loss of that context pauses source
publication with durable evidence intact. Do not describe that as an installed
unattended local publisher or silently transfer cloud credentials into Foo.

## Completed validation and standalone unit review

For an already-completed reviewed-source validation, use the existing
`standalone-validation-review-v1` decision through the fixed v2
[unit-review transport](stokowski_unit_review.py). This route binds the original
unit separately from the repository claim's actual identity, including when a
different PR already integrated its source. Preserve the existing repository
binding and immutable claim; do not invent a pending merge intent, Controller
history or a replacement claim to make the old source appear unmerged.
[PR172](https://github.com/maldous/offmenu/pull/172),
[PR173](https://github.com/maldous/offmenu/pull/173) and
[PR174](https://github.com/maldous/offmenu/pull/174) contain the adopted contracts.

The authenticated sole publisher supplies the exact owner-qualified inputs:

1. Select the original operation, source head/base/tree/outputs and its retained
   successful validation receipt. Keep the original Journal identity and receipt
   digest; pin a regular original receipt artifact inside the selected origin
   runtime for `validation_receipt_source`. A copied status string is not proof.
2. Retain the exact admitted prior independent review. Its separate, dated
   provenance supplement must already be pinned in the stage inputs and match
   reviewer, source, outputs, authors and evidence ID. `provenance_source` names
   that supplement; `qualification_source` alone cannot establish its authority.
   Preserve the prior review bytes. Requested model/provider and observed
   resolution are distinct: record genuinely unavailable fields as unknown,
   with `resolved_model:null` and `resolution_status:"unknown"` for unknown
   resolution. Do not infer the reviewer's model from an author's coding receipt.
3. Retain the original typed qualification packet under the coordinator runtime
   and pin it as `qualification_source`. Its decision is
   `standalone-validation-qualified`, with `action:null` and
   `merge_effect:"not-applicable"`. It is not a merge-controller decision.
4. Use the existing fixed transport's status/write reconciliation and duplicate
   checks. The normal coordinator consumes the retained review at its next
   refresh. Unit approval remains `accepted_delivery:false`; it neither merges
   source nor closes the parent issue or establishes deployment/BAU acceptance.

The exact checks are in
[`CurrentWork._check_prior_review_provenance`, `_check_unit_review` and
`_check_reviewed_terminal`](stokowski_adapter.py). Historical executor hashes
may be reused only for an exact completed success with matching accepted outputs
and acceptance identity, an original owner-pinned receipt matching job, command,
runner and policy, stopped children, and no pending cancellation/observation or
reconciliation. Source must still qualify presently. This exception never runs
historical executor code or authorizes replay; fresh execution remains strict.

### Completed native coding with retained Engine validation

A completed native unit may have valid Engine/Windmill acceptance and an already
merged integration candidate, with a different integration branch/base from the
immutable coding admission. Those are separate facts. Never manufacture a
native-v1 Journal, change the manifest, invent a pending merge, or replay checks
just to satisfy the historical consumer.

The authenticated integration owner may select an exact private evidence ref in
`current.json.completed_native_validations[issue]`. The typed
`completed-native-validation-v1` consumer requires the unchanged native gate,
finished successful lease, exact native output bytes, admitted coding identity,
and explicit integration ancestry with no changes to those output paths between
bases. Candidate delta/output hashes and verified merge parents/tree must match.
It also requires the original owner-approved Engine task/request and terminal
Windmill result/receipt, command/request/runner/policy hashes, independent review,
and the original Controller binding, claim, terminal checkpoint and observation.
The executed command must match the recognized source-selection/Engine wrapper;
its literal embedded task must equal the pinned task and require an accepted
`Engine.run()` result. Successful unrelated commands never qualify.
Private byte-identical copies may provide receipt custody; provenance remains the
original records. The current authenticated owner claim remains separate from
that completed Controller's claim. Neither stdin nor a shared UID is authentication.

The fixed v2 review transport consumes that evidence using
`completed_native_source`, equal to the owner-selected ref. The finite
`reviewCompletedNativeValidation` gateway writes only the exact unit review;
it never invokes Controller steps, merge, Linear completion, Engine/Journal
submission or coding. The normal coordinator records completed validation and
consumes the unit review at refresh. Approval remains `accepted_delivery:false`.
Unknown reviewer model/provider fields remain explicitly unavailable in the
retained independent artifact, independent of the coding model request.

For an original compact review with `accepted-real-native-result-and-exact-source-patch`
disposition, the owner may additionally pin `historical_association` in that same
completed evidence. Its `retained-native-source-review-v1` record binds the unit,
integration binding, original checkpoint and raw review hashes; references the
original result metadata and patch; and records the raw reviewer identity and
native-session author with explicitly unobserved model/provider metadata. The
consumer verifies those original byte pins, native receipt/session/lease/output
bindings and the patch against the committed source delta. It accepts only the
original checkpoint's exact compact head/base/independent/evidence-id/verdict/findings
shape, preserving its observation and qualification digest. This is an association
of retained acceptance, not a replacement independent review.

The association's `runner_source: {commit,sha256}` must identify the original
admitted coding base and its committed `tools/delivery/windmill_runner.py` blob.
That blob must also match the candidate's runner and the original terminal
receipt. Only this owner-selected completed record may use that historical hash;
the active runner pin and all fresh execution requirements remain unchanged.
Absent an association, the existing typed-review/current-runner contract applies.

Adopt only independently reviewed source and exact owner-qualified configuration
through the existing service owner. Historical v1 and standalone contracts remain
unchanged. A source merge is not live adoption or proof of unattended continuity.
See [ADR 0007](../../docs/adr/0007-completed-native-validation-consumption.md).

For a submitted reviewed-source operation, supported local source/admission
drift does not create new submission authority. The existing
[Journal recovery/cancellation path](stokowski_operations.py) observes and
reconciles the same bound operation/job identity; new submission and acceptance
remain separately qualified. Do not rename unknown effects, clear their holds
or rerun completed work to repair metadata. These source contracts do not prove
a live transport, automatic refill, native SSH route or continuous supervision.

## Reviewed extraction origin (2.3.0 proposal)

A source-only extraction uses a separate typed admission and fixed mapping/import
profile, not a native coding receipt. The admission pins source/mapping/output
identity and independent exact-head review. Select the exact service-owned
candidate workspace, immutable base/head/branch and accepted-base control tests;
do not validate canonical source merely because its interpreter is shared.
Existing native origin, operation IDs, dispatcher/bridge resource envelope,
stopped-child checks and integration policy remain in force. See
[ADR 0006](../../docs/adr/0006-typed-extraction-validation-and-refill.md).

`bind-extraction --candidate-root` may select an explicit absolute, canonical,
non-symlink local source mirror for preflight. Its exact Git root, clean branch,
head, base ancestry, four-path delta and historical byte mapping must match the
admission. The binding records `local_source_root` separately from `workspace`;
the spec, admission and remote command retain the canonical jailed workspace.
The trusted admission file must stay outside both candidates.

The deterministic mapping profile requires task fit
`deterministic retained byte mapping validation`, null requested model/effort and
resolved model, provider route `none` and resolution status `not-applicable`.
It runs the accepted-base control validators once against candidate imports,
fixed import/layout/policy checks and before/after identity/output checks; it
does not repeat the candidate delivery suite or historical WFP fixture tests.
The v1 compatibility oracle remains pinned to accepted commit
`7780c8602b52e9f2fc7e6a38e5d08d8ad74f09e1`.

Execution records separate requested lane/model/effort/provider/resources from
observed resolution or explicit unknown, sampled resources and parent/lease/job
identity. The existing phase boundary records a provisional ready-refill
observation; final admission is still required and no work is started by that
record. Missing/stale provider proof, overlap and unresolved effects defer work.
This is not cloud voice/approval intake, an always-on supervisor or a new scheduler.

Source-only native privilege confinement and its runtime adoption hold are in the
[coding child confinement handoff](../../docs/development/coding-child-confinement.md).

## Adopted conditional validation

ADR 0011 defines the version 4 existing-PR binding for the connector-owner lane.
PR #217 integrated the owner-adopted `integration-policy-v2-candidate.json` bytes
in `integration-policy.json` into `develop`. PR #216 subsequently used this
accepted policy for independent cloud validation.
Do not use candidate source to approve its own policy or relabel an old receipt.
The explicitly authorized one-time initial adoption uses independent review and
cloud validation under ADR 0011, with original approval, review and validation
evidence pinned by the owner. It is distinct from prior-policy verification and
cannot be reused for future policy bytes. Owner adoption is complete for the
reviewed policy source identified in ADR 0011. Exact-head review, validation and
normal merge/readback completed for that source activation; future candidates
still require their own bound review, validation and integration.

The owner supplies `integration_policy`,
`policy_adoption` and `accepted_policy_at_base_sha256` from accepted policy state,
not the coding worker. The binding's `validation_contract` pins the route,
complete implementation/provenance actor set, sorted exact `source_paths`, original receipt hash, adoption
hash and (for cloud only) independent scope-review hash. The owner obtains
`changed_paths` from the canonical base/head diff, including both names of a
rename and deletions, and compares it with the bound list. No path allowlist or
cloud label establishes independence.

The original receipt binds repository, branch, base/head/tree, policy, capacity,
operation, source paths, accepted output hashes, accepted-base validator revision,
actual executor identity, environment/dependency hashes and command/log/results.
Required checks must pass without skips. Optional skipped coverage remains
explicit and cannot satisfy required checks. Review binds the receipt and scope
hashes to the exact candidate. A changed source, base, policy, receipt or review
requires a fresh binding. Retain runtime evidence privately under `.delivery/`.

Version 4 is intentionally limited to an existing PR and the existing
`advanceIntegration` gateway. Its action has the same exact-head/base normal
merge contract; claims, protection, cancellation, reconciliation and canonical
readback are unchanged. Version 2 pre-publication, source projection, installed
Foo publishers, completed validation and release bindings are not migrated.

### Merge-only amendment candidate

[ADR 0013](../../docs/adr/0013-merge-only-existing-pr.md) proposes an explicit
v4 shape with `integration_mode: "merge-only"` and `issue_id: null`. This is a
candidate contract until separately authorized bootstrap, reviewed integration
and canonical readback establish adoption; accepted old control code rejects it.
The issue key cannot be omitted, and project/full-issue acceptance fields are
forbidden. Observations must omit `linear` and `full_issue_acceptance`; no Linear
adapter or Done effect belongs to this mode. Canonical readback ends at
`merge-verified`. Existing issue-bound bindings and fingerprints are unchanged.

The authenticated caller derives `integrationMode` from the immutable binding
and passes `integrationMode: "merge-only"` to `advanceIntegration`. Its controller
adapter maps `step` to the pinned Python `Controller.run` and `outcome` to
`record_api_outcome`, using the same existing claim root/lock. The gateway also
refuses unexpected Linear actions. Never select a new root or run this candidate
controller to bootstrap itself without the concrete finite exception authority.
