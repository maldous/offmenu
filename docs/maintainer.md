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

Use the [validation workflow](development/validation-workflow.md) to choose fast
local checks and thorough release validation, group coherent PRs and reuse exact
evidence. Fast iteration does not waive required branch checks; checks not run
remain explicitly unrun. The baseline sequence below is retained.

The manual baseline workflow in `.github/workflows/third-party-services.yml`
retains the configuration check, web tests, locale check, build, edge tests and
Python suite for explicit release validation. It has no automatic push or PR
trigger. During development, select the materially affected checks below;
preserve actual required security and branch checks. A retained manual declaration
does not prove hosted dispatch is available: the workflow must also exist on the
default branch, and this change does not promote it to `main`.
For an explicit full validation from the prepared checkout:

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

`npm test` selects `tests/web/*.test.mjs`; it does not select `tests/edge/`.
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
| `OFFMENU_AUTH_MODE` | The handler preserves the legacy verifier for missing mode or exact `netlify`. Exact `better-auth` selects the authentication adapter; a trusted `createOffMenuHandler({authOptions})` entry point must also supply its explicit policy. Unknown modes and incomplete enabled configuration fail closed. |
| `BETTER_AUTH_URL` | A deployment-owned explicit HTTPS origin. `https://offmenu.example.invalid` is a documentation placeholder, not a working environment. |
| `BETTER_AUTH_SECRET` | A separately provisioned deployment secret; no real or reusable example value belongs in source or this guide. |

The main handler now wires `cloud/auth-runtime.mjs` before its legacy proxy and
protected routes. Its default export retains Netlify authentication. Selecting
Better Auth requires a trusted deployment entry point with explicit auth options;
changing the mode alone does not supply them. Source integration and synthetic
tests do not apply a live schema, migrate accounts, register providers or switch
live login. The factory requires deployment-owned session policy and
explicit email callbacks before enabling email; Google is not a default provider.
See the [foundation](better-auth-foundation.md) and
[runtime seam](better-auth-runtime-seam.md) for the foundational slice boundaries and remaining
staging/account-continuity requirements.

Pinned Miniflare fixtures explicitly enable `nodejs_compat` when loading the
compiled Worker, including the landing-page locale fixture. Qualify the actual
runtime engine, compatibility date and flags before activation; do not assume an
older local engine has newer platform defaults. See
[Cloudflare's Node.js compatibility reference](https://developers.cloudflare.com/workers/runtime-apis/nodejs/).
This source requirement does not change any live runtime setting.

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

## Coordination and delivery states

Keep the existing implementation owner and peer together while a coupled
contract moves through clarification, correction and integration. Confirm their
disjoint file/interface boundaries; do not allocate a new owner for each small
helper or create another coordinator. Worker00 remains the shared mutation and
integration owner. That lock does not stop useful parallel work: existing owners
can prepare their own frozen patches, generated fixtures, qualified metadata and
focused checks within granted scope while shared application waits. It grants
no access to held source bodies or permission to start a paused job.

Use supported direct local-to-local or durable-to-durable specialist artifact
clarification where the existing human grant covers it. Gateway handles
cross-boundary routing, milestones, scheduling and escalation. Preserve the
specific UI and 14117 denied/uncertain-route exceptions; direct peer permission
does not authorize a retry, proxy sender or security change. A direct exchange
does not transfer source ownership or the shared write lock.

Carry the already-granted authority and its source reference in each handoff,
with the exact task, owner/peer, native session, source commit and artifact hashes,
affected interface, checks, holds, dependency owner and next concrete action.
Do not ask again for an action already within that grant. Missing permission or
an actual denial remains explicit; a message cannot broaden the grant. Keep one
canonical result ID for the finite deliverable and send short, source-bound
deltas referring to it instead of repeatedly copying a full handover. Preserve
immutable prior events and artifacts; changed evidence gets a linked delta or
superseding result, never different content under an already-recorded event ID.

Record each observed state independently in that same ledger:

| State | Evidence required; what it establishes |
| --- | --- |
| Dispatched | Supported transport envelope; admission alone proves no wake or pickup. |
| Picked up | Actual owner session/turn and scoped read acknowledgment. |
| Result/artifact ready | Frozen result ID, artifacts, source pins and scoped checks; dependencies may remain open. |
| Placed | Exact patch/files applied in a named checkout; placement may still be uncommitted WIP. |
| Tested | Actual check and result on those exact inputs; reused and unrun checks remain distinct. |
| Integrated | Accepted integration commit/provider receipt, separately from local placement or a private push. |
| Qualified | Exact source-use, custody, store, identity/auth, resource and operation qualifications for the selected effect. |
| Mounted | Actual running instance binds the selected code/build/configuration; source integration alone is insufficient. |
| Usable | The affected consumer behavior works on that qualified instance/input, with its remaining limits stated. |

These are evidence distinctions, not permission to execute the next stage or a
new mandatory audit sequence. For example, qualification needed before a source
read must precede that read. A finished author's scope can remain retained while
integration or usability is pending; neither a title nor an acknowledgment closes
those dependencies. Record only the blocker on the affected scope and keep
independent already-authorized preparation moving.

Keep source-event timestamps, their timezone and origin separate from ledger
record timestamps. A late ledger append cannot establish when execution began,
and sequence order is not a substitute for source-event chronology. From existing
receipts, report ready-to-usable time only when both matching endpoints exist.
Identify measured waiting and rework spans by their actual evidence; do not
infer idle time from silence or subtract unrelated intervals. Missing endpoints,
wait causes, token/cost attribution or causal speedup stay `UNKNOWN`, with the
available observation window. This uses existing receipts, not new telemetry.

Two examples from 25 October 2026 show why these distinctions matter:

| Existing receipt | Correct interpretation |
| --- | --- |
| Image index v3, terminal failure16475 and disposition16479 | One actual attempt failed with `field_count_limit` after committing an **unqualified 13,312-occurrence prefix**. Execution was not zero. Full EOF/hash/extent and target validation did not complete; normalized, mapped and Gold-admitted counts remained zero. Retain the failed prefix and consumed admission; no automatic retry or source reread follows. |
| PR130 provider timestamps,03:09:46–03:21:14UTC (14:09:46–14:21:14AEDT) | **11m28s is creation-to-merge PR time only**, not task duration, ready-to-usable time, a measured wait/rework reduction or a cost/speedup claim. Develop integration did not activate the runtime or admit source data. |

Keep completed scope, unique partial outputs, failure evidence and source/resume
pointers in their existing custody. Completion does not authorize destroying
them or another owner's cwd, processes or locks. Release only owned disposable
fixtures after custody/dependency checks, or retain them with an exact reason.
Apply documentation with its coherent implementation group; a small reversible
guidance correction does not need a new formal review gate, tracker or micro-PR.
Existing required checks, source/privacy/ownership/permission holds, Sonar
deferral, paused normalization, production and CIX boundaries still apply.

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
