# Repository standard 2.5.0

Status: adopted through reviewed integration after independent source review and
real retained-extraction validation. Changes enter `develop`
through the reviewed GitFlow integration process. The machine-readable contract is
[`repository-standard.json`](../../repository-standard.json). This document
explains decisions; historical handovers do not override it.

## Decisions from discovery

OffMenu has three installed Python packages, a browser/Worker application,
a retailer extension, hosting adapters, source contracts and inactive integration
seams. Standard 2.0.0 groups those actual responsibilities and updates their
consumers. [ADR 0003](../adr/0003-final-repository-layout.md) supersedes the earlier
transitional root decision. A filename-check pass alone does not establish an
adequate architecture.

| Location | Responsibility |
| --- | --- |
| `src/offmenu/`, `src/offmenu_ciqual/`, `src/offmenu_norway/` | Installed Python packages with explicit resource packaging. |
| `apps/web/{src,assets,server}/`, `apps/retailer-extension/` | Browser/Worker application and retailer extension. |
| `deploy/netlify/public/`, `deploy/auth-return/` | Hosting adapters; published routes remain compatible. |
| `integrations/staged/`, `integrations/candidates/` | Inactive source seams; moving them does not activate them. |
| `contracts/{corpus,schemas}/`, `config/source-bindings/` | Source/provenance schemas and reviewed non-secret configuration. |
| `tools/` | Delivery, source-processing, corpus, data-processing, diagnostics and operations programs. |
| `scripts/` | Small build/bootstrap/validation entrypoints. |
| `tests/` | Python suites and `web/`, `edge/`, `compat/`, `support/` runtime verification. |
| `docs/`, `examples/`, `archive/` | Current guides and ADRs, offline examples, and explicitly frozen custody. |

Root manifests/configuration remain where their tools require them. Ignored
`node_modules/`, `dist/`, `build/`, virtual environments, package metadata and
caches remain generated local state. Private `data/`, `output/` and `.delivery/`
remain excluded from Git and preserve existing access/consumers. The exact 49
held operational files retain their paths. Other retired generated directories
are recoverably relocated, with a private restore journal. See
[root disposition](../development/root-layout.md) and the
[tracked migration map](layout-migration-v2.json). Dated evidence paths remain
historical; no raw datasets, secrets or private receipts are published.

Run both `python -m offmenu.delivery check` and
`python scripts/check_final_layout.py` in the bootstrapped environment. The former
checks classification/names; the latter enforces required architecture and
rejects retired maintained roots or tracked private artifacts. Neither replaces
behavior, packaging or accepted-output checks.

## Naming and coding conventions

New Python modules and tests use `snake_case.py` and `test_<behavior>.py`.
JavaScript modules, styles, schemas and prose use descriptive lower kebab case;
JS tests use `<behavior>.test.mjs`. Python package directory underscores remain
correct. JSON field casing follows its existing public schema, not its filename.
Keep platform conventions such as `README.md`, `MANIFEST.in`, `SKILL.md`,
`__init__.py` and lockfile names. Never rename an externally specified path just
to satisfy a generic regular expression.

Use UTF-8, LF, one final newline, four spaces in Python and two in new JSON.
Follow the adjacent JavaScript module style when changing existing code; use
ES modules in this `type: module` project. Changes must keep Python's declared
supported version and the Node version documented in the maintainer guide.
Do not reformat unrelated files. Python tests use `unittest`; JavaScript tests
use `node:test`. Check the smallest materially affected command surface, then
expand only for dependencies or failures. Installation alone is not validation.

The exact `legacy_paths` list retains only imported, historic custody and pinned
fixture identities, with a reason for each path. Authored Python CLI names now
use snake case under `tools/`; their current callers moved with them. New
exceptions require an ADR. Migration updates imports, packaging, build/routing
consumers and tests together. Logical provenance identities and dataset
qualification are not silently replaced by current physical source paths.

## Branch and merge discipline

`develop` is the integration branch; `main` is the reviewed release branch.
Create `feature/<purpose>` or `bugfix/<purpose>` from freshly checked `develop`.
Use `hotfix/<purpose>` only for a selected release repair and reconcile its
accepted change back to `develop`. This workstream uses exactly
`feature/langgraph-delivery-standardization`; parallel specialists share its
single integration writer. Existing suspended workers and branches remain held.

Before acceptance, record the base/head, exact changed paths, check results,
unrun checks and blockers. A clean checkout, pushed commit or preserved source
is not proof that application behavior works. Confirm the remote feature ref
and reviewed file content after pushing. Merge feature work into `develop`
through review. Freeze the accepted release candidate from `develop`, and promote
that exact candidate through `release/candidate-<candidate fingerprint>` to
`main` with separate release review. Exhaustive release checks remain bound to
the candidate's source, tree and artifacts while `develop` advances. A repair
creates a new candidate; it never rewrites prior evidence. Verify the resulting
`main` tree and immutable release tag. Keep `main` static between approved releases.
Never merge unqualified historical work simply because its branch exists.

The workflows inspected at adoption are manual, except the narrowly scoped
`offmenu-runner-jobs` push trigger in `foo-runner.yml`. This work does not dispatch
Actions or push to that control branch. Reinspect trigger changes before any
future publishing operation. Do not add broad release gates to routine fixes.

## Evolving the standard

Discovery reads tracked source, manifests, build scripts, imports, tests,
current operational contracts and Git status. Classify a proposed move as source,
generated, runtime/private data or historical evidence before planning it.
Emit a specific proposal, affected consumers, reversible migration and acceptance
checks. Compare current evidence with the last accepted checkpoint.

A change to the standard requires a new version, an ADR explaining evidence and
tradeoffs, explicit exception changes and verification. An LLM may propose a
revision; it cannot silently rewrite the standard, approve its own migration,
claim completion from an intermediate job, or convert an exception into success.
Deterministic local checks remain the acceptance authority for encoded rules.
For guarantees that require judgment, preserve the reviewer decision and scope.

## Parallel execution capacity

Standard 2.1.0 adopts [ADR 0004](../adr/0004-resource-aware-parallel-capacity.md)
and the explicit [8/16/32/64 policy](../../tools/delivery/capacity-policy.json).
See [admission and resource limits](../development/parallel-capacity.md) and
[actual protocol boundaries](../development/execution-protocols.md). Capacity
selects ceilings; it does not activate workers, invent work or grant provider
entitlement. The single integration writer and existing pause boundaries remain.

## Autonomous integration

Standard 2.2.0 adopts [ADR 0005](../adr/0005-autonomous-integration.md).
The [integration policy](../../tools/delivery/integration-policy.json) enables
the deterministic controller for an authenticated connector owner. Persist intent
before mutation, compare exact head/base, require bound independent review and
Windmill validation, and verify canonical merge parents/tree and develop ancestry.
Linear metadata failure retries only metadata. Unknown external effects retain
repository ownership until reconciled. This authority does not enable Actions,
production deployment, main promotion or suspended historical workers.

## Origin-bound validation and continuation observations

The proposed 2.3.0 extension is described in
[ADR 0006](../adr/0006-typed-extraction-validation-and-refill.md). A reviewed
source-only extraction has its own origin/admission contract; it never acquires
a fabricated native coding receipt. Bind its exact mapping, review, candidate
workspace and output hashes to a fixed profile and same-base trusted validators.
The existing Windmill/integration policy and independent review remain required.

New receipts separate task-fit/model requests from actual observations and retain
parent/lease/job identity. Phase-boundary ready-refill records are provisional
observations, not new admission/dispatch authority. Missing provider or platform
capability is explicit. Active operation IDs, aggregate limits, legacy pauses and
publication permissions remain unchanged.


Standard 2.3.1 adds the bounded completed-native evidence consumer in
[ADR 0007](../adr/0007-completed-native-validation-consumption.md). Original
native admission, coding receipt, Engine validation and completed integration
retain distinct identities. This does not create a Journal, replay execution,
close a parent outcome, or grant new publication, provider or service authority.

## Native-platform harness and frozen releases

Standard 2.4.0 adopts the source and ownership contract in
[ADR 0009](../adr/0009-native-platform-harness.md) and
[`delivery-release-policy.json`](../../config/delivery-release-policy.json).
Linear retains outcomes and dependencies, Stokowski admitted coding, LangGraph
finite workflow state, Windmill deterministic jobs, and GitHub source/review and
release facts. Shared handoffs preserve distinct origins and original operation
identities; an uncertain effect must be reconciled before another write.

Coherent source review and meaningful validation precede installation. The
[adoption procedure](../development/native-harness-adoption.md) retains original
installer receipts, rollback custody and actual host confirmations. Component
tests, source integration and a service start do not establish useful BAU or
legacy retirement. Exact installed, active and functional evidence is required
before retiring the obsolete lane. This source standard grants no product
deployment, CIX execution, Actions, new credentials or spend.

The explicit installed `.offmenu-runtime/` location is governed by [ADR 0010](../adr/0010-explicit-windmill-runtime-installation.md). It does not replace private `.delivery/` staging or release existing runtime holds without a verified consumer handoff.
