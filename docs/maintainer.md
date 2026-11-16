# Maintainer setup and local checks

Use a real Git checkout of the reviewed branch or commit. Record `git rev-parse
HEAD` and check local changes before building: the application build embeds Git
HEAD and a timestamp, so a source archive without Git metadata is insufficient.
A dirty build does not identify all inputs through its embedded commit.

## Dependencies

Use Node.js 24 and Python 3.12 for the commands below; the manifests declare the
package requirements. Create an ordinary environment for this checkout:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
npm ci
```

The build invokes `python3` for ZIP creation as well as Node. Keep the intended
virtual environment active. A fresh checkout does not need another project,
service credentials or a running orchestration service to install or build.
Dependency installation uses the declared public packages; it does not start
collection, select data, grant source rights or configure provider accounts.
Collection extras are separate from the ordinary product/test installation.

## Source and build checks

Choose affected checks with [the validation workflow](development/validation-workflow.md).
The product source checks are self-contained:

```sh
python3 scripts/check_repository.py --discover
npm run check:repository
npm run check:layout
npm run check:generated
npm run build
```

Run `check:generated` before the build: regeneration must not conceal a
pre-existing difference in the tracked extension bundle. Reconcile and review
any difference deliberately. The build checks locale inventory, bundles browser
assets and the Worker, and creates the retailer-extension archive. It neither
deploys the application nor publishes a data candidate.

For broader selected validation, use:

```sh
node scripts/verify-third-party-config.mjs
npm test
npm run test:locale-edge
python -m unittest discover -s tests -v
```

`npm test` selects `tests/web/*.test.mjs`; edge tests are separate. Focused
authentication checks use `npm run test:auth`. `npm run validate:dev -- <test-path>`
runs explicitly selected web/edge tests; `npm run validate:release -- --plan`
lists the existing release profile without executing it. Report skipped or
unrun tests with their actual prerequisites rather than treating a partial pass
as complete product acceptance.

Optional unmounted authentication source has its own build. When reviewing that
component and its imports, build it before the corresponding import audit:

```sh
node integrations/staged/auth/build.mjs
npm run check:web-imports
```

This does not mount the component in the application. A source-only or frozen
fixture may have additional declared prerequisites; it is not permission to
read retained data or contact a provider.

## Build outputs

| Output | Meaning |
| --- | --- |
| `dist/worker.mjs` | Generated Worker module; not a standalone Node server. |
| Other `dist/` files | Browser, scanner and extension build outputs. |
| `apps/web/server/generated.mjs`, `deploy/auth-return/i18n.js` | Ignored generated composition/auth-return output. |
| `apps/retailer-extension/popup.js` | Tracked generated bundle; review changes against `popup-source.js`. |
| `apps/web/assets/locales/en.json`, `docs/i18n-coverage.json` | Locale inventory rewritten only by `npm run i18n:extract`; `i18n:check` is read-only. |

Wheels can be built independently of the browser build:

```sh
python -m pip wheel --no-deps --wheel-dir dist/python .
```

Verify a wheel in a separate environment and working directory so checkout
imports cannot mask missing package resources. The wheel must provide the
`offmenu`, `offmenu_ciqual` and `offmenu_norway` product packages, the console
entry point and their declared resources. A wheel build or import check does
not qualify source-specific data processing.

## Local Python demo

Use a dedicated database and the authored example files:

```sh
mkdir -p .cache/local-demo
OFFMENU_DEMO_DB=.cache/local-demo/offmenu.sqlite
python -m offmenu --db "$OFFMENU_DEMO_DB" init
python -m offmenu --db "$OFFMENU_DEMO_DB" import-products examples/products.jsonl
python -m offmenu --db "$OFFMENU_DEMO_DB" import-recipes examples/recipes.json
python -m offmenu --db "$OFFMENU_DEMO_DB" inventory
python -m offmenu.server --db "$OFFMENU_DEMO_DB" --host 127.0.0.1 --port 8765
```

The global `--db` option precedes the subcommand. Even inventory reads open a
schema-initializing connection, so do not point the example at a retained or
private source database. Example imports update records in that demo database.
The server is the small Python interface at `http://127.0.0.1:8765`; stop your
own process with Ctrl-C. It is distinct from the full browser/Worker product.

## Product configuration

The product build uses repository source and assets. Optional deployed features
require their own selected configuration:

| Name | Product role |
| --- | --- |
| `DB` | Deployment-owned account/application D1 binding, separate from the local CLI database. |
| `PROVIDER_VAULT_KEY` | Existing deployment secret protecting provider credentials; changes require a reviewed migration. |
| `CURATED_CORPUS_ORIGIN` | Selected static curation origin after its source/publication acceptance. |
| `OFFMENU_CURATED_RELEASE` | Local tool selection of a qualified release directory; not a credential or publication grant. |
| `OFFMENU_AUTH_MODE` | Missing/exact `netlify` retains the legacy verifier; exact `better-auth` selects the adapter only with trusted explicit policy. Unknown or incomplete configuration fails closed. |
| `BETTER_AUTH_URL`, `BETTER_AUTH_SECRET` | Separately provisioned authentication origin/secret; no reusable secret belongs in source. |

The handler factory requires deployment-owned session policy and explicit email
callbacks before enabling email. Google is not a default provider. Source tests
do not migrate accounts, switch live login or provision services. Keep the
actual runtime engine, compatibility date and flags explicit; local Worker
fixtures using Node compatibility do not change a deployment.

## Data, privacy and release

Keep databases, account exports, raw sources, credentials and runtime evidence
out of Git. Source rights, consent, permitted audience, retention and withdrawal
remain required for each real data operation. Unknown values are not zero and
source publication does not confer a licence.

Use [the release policy](../config/release-policy.json) for reviewed promotion of
an immutable candidate to `main`. Development may continue on `develop` while a
frozen candidate is qualified; a repair creates a new candidate. Source acceptance,
local build, data admission, account activation and product deployment are
separate facts. Follow [operations](operations.md) for the product boundaries.
