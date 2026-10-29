# Repository root disposition

Repository standard 2.0.0 replaces the transitional root classification. The
reasoning and compatibility obligations are in [ADR 0003](../adr/0003-final-repository-layout.md).

```text
src/                 offmenu, offmenu_ciqual, offmenu_norway installed packages
apps/                web/{src,assets,server}, retailer-extension
deploy/              netlify/public, auth-return
integrations/        staged/{auth,private-product-lookup}, candidates
contracts/           corpus, schemas
config/              reviewed configuration and source-bindings
tools/               delivery, data-processing, operations, corpus,
                     diagnostics/public-field, source-processing
scripts/             build, bootstrap and validation entrypoints
tests/               Python suites, web, edge, compat, support/wiremock
docs/                current guides, standards, ADRs, research and dated evidence
examples/            authored offline examples
archive/             immutable release-custody and migrations
```

Keep root `AGENTS.md`, `README.md`, `pyproject.toml`, `MANIFEST.in`, `package.json`,
`package-lock.json`, `netlify.toml`, `repository-standard.json`, `.editorconfig`,
`.gitignore`, `.github/` and `.agents/`: these are conventional tool entrypoints.
This is one mixed application repository with explicit internal responsibilities,
not a collection of new independently versioned packages.

| Local category | Disposition |
| --- | --- |
| `node_modules/`, `dist/`, `build/`, virtual environments, package metadata and caches | Ignored generated/dependency state. Commands regenerate it; it is never source acceptance. |
| `data/`, `output/`, `.delivery/` | Existing private mounts/output/checkpoints. Preserve access restrictions and operational consumers. No raw data or receipts enter Git. |
| Existing private tool directories | Retain their ignored tool-owned state; no speculative cleanup of active consumers. |
| 49 exact held `scripts/windmill/` files | Preserve paths for the existing bridge. They remain untracked and individually enumerated in the standard's runtime holds. |
| Retired generated roots and loose private `knowledge.md` | Recoverably relocate to ignored `.cache/retired-layout/`; private restore journal records original and retained paths. |
| Dated custody/imported names | Exact explicit naming exceptions, with reasons. The migration map distinguishes historic paths from current physical locations. |

[Final-layout migration map](../standards/layout-migration-v2.json) records every
tracked move from the accepted base. Historical evidence is not rewritten to
claim the new paths existed at its old revision. Current usage is documented in
[Python layout](python-layout.md), [web layout](web-layout.md) and
[data/tool layout](data-tool-layout.md).

Validate encoded structure with the installed environment:

```sh
.venv-delivery/bin/python -m offmenu.delivery discover
.venv-delivery/bin/python -m offmenu.delivery check
.venv-delivery/bin/python scripts/check_final_layout.py
```

These checks verify classification/names and required architecture. Installed
wheel resources, web imports/build, targeted behavior checks and graph accepted
output hashes establish the changed behavior. Full application or production
acceptance remains separate.

The [accepted verification summary](final-layout-verification.json) records exact
code revision, local and Windmill graph acceptance, native Symphony output,
bootstrap/build/test evidence and remaining baseline failures.
