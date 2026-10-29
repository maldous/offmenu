# Repository root disposition

The root is a mixed Python and JavaScript workspace. Its directories have
separate runtime, packaging, provenance, and deployment contracts. A smaller
root should come from grouping related work with verified consumers, rather
than relocating production assets or private data without their owners.

The 2026-10-29 changes consolidate web, edge, and compatibility tests under
`tests/`, and selected source-processing tools under `tools/source-processing/`.
Their nine guides live under `docs/source-processing/` using lower-case kebab
filenames. Current callers were updated. Historical custody and pinned snapshot
paths remain descriptions of their original revisions.

| Root paths | Classification and disposition |
| --- | --- |
| `offmenu/`, `offmenu_ciqual/`, `offmenu_norway/` | Python packages found by the existing setuptools manifest. Keep import paths and package resource contracts stable. A future `src/` migration requires wheel/install/import validation and adapter-lock version decisions. |
| `public/`, `cloud/`, `extension/` | Authored browser, Worker, and extension source. Keep current bundler and deployment entrypoints stable. |
| `netlify/`, `netlify-return/`, `netlify.toml` | Distinct static hosting and authentication return surfaces. Their names are deployment contracts; any grouping needs routing/build checks. |
| `auth-source-preparation/`, `private-product-lookup/`, `dev/` | Retained integration seams and unfinished work with separate acceptance. Keep their boundaries; moving them is not permission to integrate or activate them. New unrelated tools belong in `tools/` or `scripts/`. |
| `tools/` | Cohesive developer/source tools, their schemas and seam-local tests. Selected source processing is grouped here; developer guides live in `docs/`. |
| `scripts/` | Repository command entrypoints and bounded build/validation helpers. Historical public CLI filenames may use kebab case; importable Python modules use snake case. |
| `tests/`, `examples/` | Runtime-specific tests and authored examples. Pinned fixture internals retain their exact bytes and local imports. |
| `corpus/`, `bindings/`, `schemas/`, `config/` | Authored data contracts, mapping/policy definitions, and reviewed configuration. These are source, not bulk datasets. Avoid combining them without checking schema IDs and consumer paths. |
| `docs/`, `research/`, `migration/` | Human guides, source/provenance material, and historical migration evidence including a Git bundle. Their retention is not current runtime acceptance. |
| `data/`, `output/`, `.delivery/` | Ignored local data and operational state. Preserve selected-input/configuration/evidence holds; do not publish them through a source-only commit. |
| `dist/`, `cloud/generated.mjs`, `netlify-return/i18n.js`, `node_modules/`, `offmenu.egg-info/` | Ignored generated build or installed dependency state. Their local presence is not source duplication. Rebuild or dependency-install contracts own their lifecycle. |

## Naming baseline classification

Policy 1.0.0 recorded 137 exceptions before the additional source-tool migration.
That baseline contains these distinct categories:

| Count | Category | Disposition |
| ---: | --- | --- |
| 9 | Upper-case `manual-action/*.md` guides | Migrated to lower-case kebab names under `docs/source-processing/`. |
| 71 | Python command filenames: 67 under `scripts/`, two under `cloud/`, one under `dev/`, one under `private-product-lookup/` | Existing CLI path contracts; allow by declared entrypoint role or migrate with consumer and source-pin evidence. Do not rename every command solely to match importable-module conventions. |
| 52 | Provenance and pinned names: 38 historical/custody docs, nine research registers/reports, five upstream/pinned fixture names | Keep exact names and hashes, including source workbook and candidate `A`/`B` names. These are evidence fidelity requirements. |
| 4 | Private Python module names beginning `_` under `offmenu/` | Conventional Python names; the naming policy should recognize private modules. |
| 1 | `netlify-return/_headers` | Hosting framework filename contract. |

Standard 1.1 recognizes the five conventional private/framework names directly, leaving 123 exact exceptions: 71 command contracts and 52 evidence identities. Every retained exception has a reason in the machine-readable policy. They are not a single rename backlog.
New source and guides follow the versioned standards; changing a legacy path
requires its actual references and applicable hash, build, packaging, and
runtime contracts to be checked. Standards changes use a new policy version
and ADR, rather than silently blessing new exceptions.
