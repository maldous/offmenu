# Repository standard 3.0.0

Status: standalone-product candidate. The machine-readable contract is
[`repository-standard.json`](../../repository-standard.json); the decision is
[ADR 0014](../adr/0014-standalone-product.md). Acceptance and clean-build results
must be recorded against the actual reviewed candidate, not inferred from this
version label.

## Product boundary

This repository contains OffMenu product source, its contracts, examples,
dependencies, build tools and tests. A fresh checkout must install and build
without another project checkout, machine-specific directories, service
credentials or a shared orchestration process. Optional product integrations
have requirements only when selected for use or deployment.

Shared coordination, host/session administration and historical operational
records are maintained outside this product source tree. Their preservation
retains original identities and hashes; it does not assert a recipient transfer,
system adoption or runtime transition. Existing held private consumers must not
be moved or deleted merely because tracked source is reorganized.

## Layout

| Location | Responsibility |
| --- | --- |
| `src/offmenu/`, `src/offmenu_ciqual/`, `src/offmenu_norway/` | Installed product Python packages and declared resources. |
| `apps/web/`, `apps/retailer-extension/` | Browser/Worker product and retailer extension. |
| `deploy/netlify/public/`, `deploy/auth-return/` | Product hosting/authentication adapters. |
| `integrations/` | Optional unmounted product components; source presence does not activate them. |
| `contracts/`, `config/` | Product schemas, source/provenance contracts and reviewed non-secret configuration. |
| `tools/`, `scripts/` | Product data/development tools, build and validation entrypoints. |
| `tests/` | Authored fixtures, Python, browser, edge and compatibility checks. |
| `docs/`, `examples/` | Current product guides/decisions and offline examples. |

Root manifests and configuration stay where their package/build tools require
them. Keep dependencies, virtual environments, databases, build output, private
exports and caches untracked. Data rights and current consumers remain explicit;
a directory move never creates qualification or publication permission.

## Names and encoded checks

Use snake_case for Python modules/tests, descriptive lower kebab case for authored
JavaScript/prose/JSON filenames, and the conventional platform names listed in
the contract. Preserve imported product fixtures and source identities through
explicit naming exceptions, rather than renaming externally specified content.
New exceptions or structural policy changes require a versioned decision.

Use UTF-8, LF and a final newline. Keep new Python indentation at four spaces and
new JSON at two. Follow adjacent module style and avoid unrelated formatting.

```sh
python3 scripts/check_repository.py --discover
python3 scripts/check_repository.py
python3 scripts/check_final_layout.py
```

These checks inspect the selected repository and its layout/naming contract.
They need no project-specific environment bootstrap or service. Their pass does
not replace package installation, a complete product build or behavior checks.

## Branch, release and evidence

Use `feature/` or `bugfix/` branches from the selected current `develop` and retain
one integration writer. Review the exact diff and materially affected behavior
before source acceptance. Record source base/head/tree, changed paths, commands,
exits, artifacts, unrun checks and remaining limitations. Reconcile unknown
external effects before retrying the same operation.

Follow [`config/release-policy.json`](../../config/release-policy.json) for the
immutable release candidate, independent review, complete qualification,
canonical tree readback and immutable tag. A repair creates a new candidate;
keep `main` static between approved releases. No automatic product deployment
follows from this standard.

## Changes to the boundary

A structural change must identify actual consumers, distinguish product source
from generated/private/history material, preserve necessary originals outside the
tracked product tree, update the versioned contract and its callers together,
and verify the affected imports, packaging and outputs. Never weaken privacy,
source rights, authentication or data-loss assertions to make checks pass.
