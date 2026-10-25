# Maintainer setup and local checks

Run commands from the source checkout you are maintaining, in the directory
containing `package.json` and `pyproject.toml`. Check its branch, commit and local
changes before building. The primary checkout, an accepted review checkout and
a running preview can intentionally have different commits.

## Workspace and data locations

| Location | Purpose |
| --- | --- |
| `/home/user/src/offmenu` | Primary repository checkout; `main` is the stable branch. |
| `/home/user/src/offmenu-worktrees/` | Feature, integration and pinned review checkouts. Use the checkout selected for your change. |
| `/home/user/src/offmenu-data/` | Retained sources, private databases, generated data and operational evidence, outside the product checkout. |
| `/home/user/src/offmenu-data/runtime/` | Current control, custody, review and result artifacts. Historical Documents paths are not a new output destination. |

The local `develop` checkout can remain held while a running preview depends on
its loaded Python source, assets, app state or mock services. A newer accepted
commit in another checkout does not release those dependencies. Keep the
running owner's paths and state until its recorded safe handoff; do not reset,
move or repoint the held checkout as part of setup. Consult the current
integration/runtime receipt for the actual accepted commit and runtime pin.

## Dependencies

CI uses Node.js 24 and Python 3.12; the Python package declares Python 3.10 or
newer. Use the committed lockfile and declared extras for a fresh development
environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e '.[test]'
npm ci
```

The build invokes `python3` as well as Node. The test extra supplies the parser,
schema, image and spreadsheet dependencies used by the Python suite. Collection
extras are separate; installing dependencies does not select a source, grant
source-use rights or start acquisition.

## Checks and generated files

The baseline workflow in `.github/workflows/third-party-services.yml` runs the
configuration check, web tests, locale check, build, edge tests and Python suite.
From the prepared checkout:

```sh
node scripts/verify-third-party-config.mjs
npm test
npm run i18n:check
npm run check:generated
npm run build
npm run test:locale-edge
python3 -m unittest discover -s tests -v
```

Run `check:generated` before the build so regeneration cannot hide committed
extension drift. If it reports drift, reconcile the source and regenerate/review
the output deliberately; do not treat a subsequent build as evidence that the
original output was current.

`npm test` selects `tests-web/*.test.mjs`; it does not select `tests-edge/`.
`npm run test:auth` is an additional focused authentication command. The workflow
also names a bounded portable receipt-OCR check; retain that check when changing
its extraction or admission path. Optional external scans are separate from
these local checks and remain subject to their current configuration and holds.

| Command/output | Effect |
| --- | --- |
| `npm run i18n:check` | Checks the generated locale inventory without rewriting it. |
| `npm run i18n:extract` | Rewrites `public/locales/en.json` and `docs/i18n-coverage.json`; review both diffs. |
| `npm run build` | Checks locale inventory, builds browser assets and the Worker, and creates the extension archive. |
| `dist/`, `cloud/generated.mjs`, `netlify-return/i18n.js` | Ignored generated outputs. `dist/worker.mjs` is a Worker module, not a standalone static-site server. |
| `extension/popup.js` | Tracked generated file from `extension/popup-source.js`; a build can change it. Review the generated diff. |
| `npm run check:generated` | Compares that tracked extension output with an in-memory build; writes no replacement output. |

Builds embed the checkout's Git HEAD and a build timestamp. Building dirty source
can therefore produce an artifact whose embedded commit does not identify every
input. Preserve the actual source revision and reviewed build evidence for a
release. A build does not deploy the app or publish a data candidate.

## Local Python demo and server

The CLI's default database is `data/offmenu.sqlite` relative to the checkout.
Choose a dedicated demo database to keep it separate from retained source and
Gold databases. The following commands import only the authored example files:

```sh
OFFMENU_DEMO_DB=/home/user/src/offmenu-data/local-demo/offmenu.sqlite
python3 -m offmenu --db "$OFFMENU_DEMO_DB" init
python3 -m offmenu --db "$OFFMENU_DEMO_DB" import-products examples/products.jsonl
python3 -m offmenu --db "$OFFMENU_DEMO_DB" import-recipes examples/recipes.json
python3 -m offmenu --db "$OFFMENU_DEMO_DB" inventory
python3 -m offmenu.server --db "$OFFMENU_DEMO_DB" --host 127.0.0.1 --port 8765
```

The CLI's `--db` goes before the subcommand. Even commands such as `inventory`
open a schema-initializing connection; use the demo database rather than treating
this CLI as a read-only Gold inspector. Repeating example imports updates the
example records in that database.

The server serves `offmenu/web.html` and its local SQLite API. Open
`http://127.0.0.1:8765`; stop your own server with Ctrl-C. This is the small Python
interface, not the Cloudflare app under `public/` and not the owner-held native
preview. There is no `npm run dev` or `npm start` script. Use the preview owner's
current run instructions for the full web app; do not substitute the Python
server or run `dist/worker.mjs` directly with Node. LAN camera testing additionally
needs the trusted HTTPS setup described in the README; physical device checks
remain separate from automated tests.

## Configuration and authentication state

| Name or mode | Meaning and owner |
| --- | --- |
| `DB` | Deployment-owned D1 binding for account/application state. It is not a local CLI database or a raw-source corpus store. |
| `PROVIDER_VAULT_KEY` | Existing deployment secret protecting provider credentials. Preserve the binding; rotation needs its reviewed migration. |
| `CURATED_CORPUS_ORIGIN` | Deployment-selected static curation origin after publication acceptance; see the curation architecture. |
| `OFFMENU_CURATED_RELEASE` | Local publication-tool input selecting an accepted release directory, not an app credential or permission to publish. |
| `OFFMENU_AUTH_MODE` | The unmounted auth adapter returns the legacy verifier for missing mode or exact `netlify`; exact `better-auth` selects the new factory only when a dispatcher explicitly mounts it. Other values fail closed. |
| `BETTER_AUTH_URL` | A deployment-owned explicit HTTPS origin. `https://offmenu.example.invalid` is a documentation placeholder, not a working environment. |
| `BETTER_AUTH_SECRET` | A separately provisioned deployment secret; no real or reusable example value belongs in source or this guide. |

At this source baseline, `cloud/auth-runtime.mjs` is unmounted: the main handler
does not import it. Source integration and its synthetic tests do not activate
Better Auth, apply its schema, migrate accounts, register providers or switch
live login. The factory also requires deployment-owned session policy and
explicit email callbacks before enabling email; Google is not a default provider.
See the [foundation](better-auth-foundation.md) and
[runtime seam](better-auth-runtime-seam.md) for the exact boundaries and remaining
staging/account-continuity requirements.

The foundation's focused test procedure uses `npm ci --ignore-scripts` and
`npm run test:auth`, with reported evidence under Node 24.19.0. That procedure is
separate from the normal application CI install, `npm ci`; it is not evidence
that a clean full application build passed with lifecycle scripts disabled.
Keep private environment values in the existing local/deployment configuration;
changing a variable in a file does not mount an adapter or qualify activation.

## Automatic work tracking

OffMenu work, deliverables and action status belong in the existing canonical
ledger, not GitHub Issues. GitHub pull requests remain the code-review route.
Existing operational callers must record meaningful actions automatically as
part of their workflow: pickup, result, review, failure, merge, activation,
pause and cleanup. Returning a chat answer or changing an issue is not a ledger
record. This rule does not introduce a new tracker or imply that a background
scheduler is running.

The same authority is
`/home/user/src/offmenu-data/runtime/control/interim-obligation-index.json` plus
`/home/user/src/offmenu-data/runtime/control/permanent-ledger/events.jsonl`.
Use its existing adapter and derived `management-summary.json`:

```sh
python3 /home/user/src/offmenu-data/runtime/control/tools/worker64-permanent-ledger-adoption/ledger.py --store /home/user/src/offmenu-data/runtime/control/permanent-ledger summary
```

The summary is a bounded derived view, not a second source of truth. Each action
record must retain its actor, native session/turn, existing task and parent,
dependencies, actual working directory, time with timezone, exact evidence
paths/hashes, actual state and concrete next action. A notification transport
receipt is separate from recipient pickup, review, execution and completion.
Failures and uncertain sends remain visible; absence of acknowledgment does
not justify replay.

Operational event inputs use the existing `id`, `task`, `source`, `decision`,
`action` and `nextAction` contract. Put actor/session/parent/dependency/cwd/time
and actual-state evidence in the action receipt. `source` is exactly the
artifact's `path` and `sha256`; do not add `bytes` to that reference. The existing
authorized writer records an event with the same adapter's `record --input
/absolute/event.json` command. Where the integrator owns the shared write, retain
the exact event input and send it through that existing route rather than
starting another writer or tracker.

The integrator owns migration of existing GitHub Issues 32, 33 and 34. Preserve
the exact issue snapshots and source links, record the corresponding ledger
mapping/disposition, and retain the provider's closure receipt separately. Issue
preservation, ledger migration, issue closure and completion of the underlying
work are distinct facts. Use the actual migration result when reconciling them;
no migration completion is asserted by this guide. Do not create replacement
OffMenu task issues or duplicate that preservation work.

## Private data and data lifecycle

Keep `.env`, `.dev.vars`, private keys and account/provider credentials local.
They are ignored by the product repository; an ignore rule is not encryption or
permission to include credentials in exported data, backups, logs or reports.
Use the existing configured credential store for an integration, and preserve
its secret bindings during a separately reviewed release.

Retained source files and manifests, derived proposals, independently reviewed
outputs, unadmitted database candidates and scoped admission receipts are
separate stages. Reuse the selected existing source custody instead of copying
a whole corpus into a checkout or rerunning a historical acquisition script.
Per-record attribution, rights, original text, quantity lexemes and unknowns
must survive processing. Source-fact acceptance does not establish normalized
instructions, executable suitability, complete nutrition or country completion.
The demo catalogue and live preview are not implicitly updated by a private
candidate or its receipt.

For the delivery architecture, use [local curation and static delivery](curation-architecture.md):
originals and source stores stay local; only selected publication projections
enter static delivery, while D1 retains account/application state. The dated
counts and live assertions in architecture checkpoints require their matching
release evidence; they are not a new deployment observation. The code map and
current-versus-historical navigation are in the [docs index](README.md).

For the actual operation contracts, see [source acceptance](source-acceptance-contract.md),
[refresh and acquisition](refresh-acquisition-contract.md),
[local ingredient ingestion](ingredient-ingestion.md), and the source-only
[barcode](../manual-action/GOLD-BARCODE-LOOKUP.md) and
[literal-facts](../manual-action/SOURCE-RECIPE-LITERAL-FACTS.md) interfaces.
Collection, normalization, publication and deployment use their selected owner,
input manifest, review and finite limits; they are not onboarding smoke tests.
