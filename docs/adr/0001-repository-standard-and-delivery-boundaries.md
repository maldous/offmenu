# ADR 0001: Architecture-aware standards and durable delivery

- Date: 2026-10-29
- Status: accepted after source and implementation review
- Standard: repository 1.0.0

## Context

The reconciliation preserved source and recoverable runtime custody. It did not
make hundreds of unrelated entries a maintainable architecture or establish
accepted application correctness. The tracked tree contains a Python CLI,
source adapters, browser application, Worker, extension, hosting seams, multiple
test runtimes and substantial historical evidence. Directory counts alone cannot
distinguish generated files from source, private data or active consumers.

## Decision

Adopt a versioned machine-readable root and naming contract, with a human guide
and explicit legacy exceptions. Preserve actual package/build boundaries and
consolidate test locations where consumer updates and checks demonstrate safety.
Keep runtime/checkpoint data outside the product checkout. Do not mass-rename
source or erase retained evidence to improve a directory count.

Use LangGraph for an explicit finite state machine: discovery, proposal,
execution, verification and receipt. Use durable checkpoints and exact run
identity so an interrupted operation can reconcile its accepted result before
retrying. Windmill provides deterministic selected execution, admission and job
outcome evidence where available. Neither tool independently proves delivery.
Keep LangChain integrations limited to a concrete approved provider need;
LangSmith telemetry is optional later work and remains disabled by default.
Local discovery and validation must work without model credentials or paid calls.

A delivery receipt binds source revision, standard version, changed paths,
selected checks, actual exit outcomes, checkpoint identity and unresolved holds.
A resumed run first reconciles its source and operation identity. Cancellation
must prevent new work and preserve the last receipt. Resource ceilings are
admission limits, never instructions to fill capacity. Use bounded retries for
known retryable operations; uncertain side effects require outcome inspection.
Do not introduce recursive LLM managers or self-approved policy updates.

Use one integration writer on one feature branch for this workstream. Existing
application workers and hourly automation stay suspended. Review accepted work
into `develop`, then release `main` separately. Publication of this feature branch
must not trigger GitHub Actions, deploy the application or expose private inputs.

## Alternatives and consequences

Moving every package into a generic `src/` tree would require packaging and
consumer rewrites with no measured benefit at this stage. A documentation-only
policy would leave continuity dependent on memory. A tool that silently rewrites
its own rules could satisfy its checker while weakening the project's contract.
The selected approach supplies a runnable boundary and incremental migration,
while making the remaining migration debt visible.

Existing public/imported filenames can need explicit compatibility exceptions.
The standard therefore has a legacy baseline, not an assertion of full historical
compliance. Any further consolidation requires a concrete consumer map, affected
checks and a reversible move. Preserved scanner and API work retains its recorded
status; this ADR does not certify or resume it.

## Evidence inspected

- `pyproject.toml`: Python discovery includes `offmenu*` and package data.
- `package.json`: separate browser and edge Node test commands.
- `scripts/build.mjs`: browser, extension, Worker and generated asset consumers.
- `netlify.toml`: curated publication directory.
- `.gitignore`: generated outputs and private/runtime exclusions.
- `.github/workflows/foo-runner.yml`: manual dispatch plus scoped control-branch push.
- `.github/workflows/third-party-services.yml`: manual dispatch only.
- `docs/maintainer.md`: supported development commands and private runtime roots.
- `docs/reconciliation/2026-10-29/EXTERNAL-DEVELOPER-PICKUP.md`: unfinished branch work and holds.

Implementation and tests must substantiate the selected behavior. This ADR is
a decision record, not an execution receipt or evidence that a deployment ran.
