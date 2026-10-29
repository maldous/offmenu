# Repository standard 1.0.0

Status: adopted for the delivery-standardization feature branch; promotion to
`develop` requires review. The machine-readable contract is
[`repository-standard.json`](../../repository-standard.json). This document
explains decisions; historical handovers do not override it.

## Decisions from discovery

OffMenu is a Python package and a browser/Worker application in one repository.
`pyproject.toml` discovers `offmenu*`; `scripts/build.mjs` consumes `public/`,
`cloud/`, `extension/` and `netlify-return/`; `netlify.toml` publishes a curated
build. Those are actual dependency boundaries. A generic conversion to `src/`
or a new JavaScript monorepo would break imports and publication without solving
workflow continuity. Keep these entry points explicit and stable. The root
contract classifies each permitted tracked root by responsibility and ownership.
An owner is a review responsibility, not a claim that a suspended worker resumed.

Use the following layout for new work:

| Location | Responsibility |
| --- | --- |
| `offmenu/`, `offmenu_ciqual/`, `offmenu_norway/` | Importable Python runtime and selected source adapters. |
| `public/`, `cloud/`, `extension/`, `netlify/`, `netlify-return/` | Browser, Worker and hosting entry points. |
| `scripts/` | Bounded developer/build/operations commands; no private receipts. |
| `tests/` | Automated verification, grouped by runtime or feature. Browser, edge and compatibility suites belong under `web/`, `edge/`, `compat/`. |
| `config/`, `bindings/`, `schemas/` | Reviewed non-secret configuration, source binding contracts and schemas. |
| `docs/standards/`, `docs/adr/` | Current standards and reasoned changes. |
| `docs/` | Maintainer guides and explicitly historical evidence. |
| `examples/` | Small authored offline examples safe to redistribute. |
| `dev/`, `auth-source-preparation/`, `private-product-lookup/`, `manual-action/` | Existing distinct integration or source-processing seams; no new unrelated work belongs here. |
| `corpus/`, `research/`, `migration/` | Existing provenance and migration material; read status before reuse. |

Generated `dist/`, `node_modules/`, `.venv/`, `*.egg-info/` and Python caches are
local artifacts, excluded from Git. The ignored `.delivery/` directory can hold local delivery checkpoints; never commit it.
Runtime checkpoints, source databases,
private screenshots, tokens and custody receipts belong outside the checkout,
under an explicitly selected private runtime/data root. Existing held paths are
not safe to relocate merely because they are ignored. Preserve the consumers
and recovery journals recorded in the
[developer pickup](../reconciliation/2026-10-29/EXTERNAL-DEVELOPER-PICKUP.md).

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

The explicit `legacy_paths` list records existing naming debt. It allows
incremental compliance without falsely asserting old material has been fixed.
New violations cannot be added silently to that list. A migration must update
consumers, imports, build/package/routing references and selected tests together.
Do not rewrite dated provenance references as if the original evidence used a
new path. A baseline exception never authorizes new copies of that name.

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
through review; promote accepted `develop` to `main` through release review.
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
