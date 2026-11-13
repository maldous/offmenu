# Validation during development and at release

Use the checkout and source revision selected for your change. The
[maintainer guide](../maintainer.md#source-and-build-checks) remains the
command reference. Optional `validate:dev` and `validate:release` aliases group
existing commands; direct commands remain valid and no new mandatory tool is introduced.

## Fast local iteration

Reuse exact still-valid evidence for unchanged source and inputs. Copies, docs
edits and minor unchanged fragments do not trigger a local hundreds-test rerun.
A move that changes imports, paths or runtime bindings is a material interface
change and needs its affected check, not an automatic full-suite replay.

Validate the smallest coherent behavior change while developing. Inspect the
actual diff and its dependency boundary; include security and data-loss paths
when affected. A local fast pass is evidence for that scope, not a release pass.

1. Check syntax of changed JavaScript entry points or modules. For example:

   ```sh
   node --check apps/web/src/checkout-model.js
   node --check apps/web/src/app.js
   ```

2. Run the existing tests that exercise the changed interface or invariant.
   For receipt, shelf replacement, undo, resume or inventory consequences:

   ```sh
   node --test tests/web/checkout.test.mjs tests/web/checkout-ui.test.mjs tests/web/receipt-identity-ui.test.mjs tests/web/receipt-identity-preservation.test.mjs
   ```

   These names are examples for that seam, not a requirement to run checkout
   tests for unrelated documentation. Syntax checks do not exercise behavior.

   `npm run validate:dev -- tests/web/scanner-capture-envelope.test.mjs` runs only
   explicitly selected test files and deduplicates repeated paths. No paths is
   an error. Add `--plan` to list the command without executing tests. Select
   auth, isolation and data-integrity cases when their dependency boundary changes;
   run the separate syntax or build checks below when the change needs them.

3. If imports, entry points, browser assets, Worker wiring or generated output
   changed, check the generated extension **before** rebuilding:

   ```sh
   npm run check:generated
   npm run build
   ```

   A build regenerates tracked `apps/retailer-extension/popup.js`. Do not use that regeneration
   to conceal prior drift. Resolve and review drift deliberately; keep its
   initial failure evidence. A build checks compilation and asset packaging,
   not the serving instance, phone, authentication or full API behavior.

4. Exercise the affected interface using the existing bounded test. For the
   identifier UI/host boundary, the repository has:

   ```sh
   node --test tests/web/identifier-ui-wired.test.mjs tests/web/identifier-host.test.mjs
   ```

   The Node/Python native host and the Worker are different runtime boundaries.
   A mock or static assertion alone is not proof that a real endpoint works.
   Record native/device prerequisites and actual runtime evidence separately
   when that behavior is part of the change; do not start an unrelated service.

For HTML/CSS or docs-only changes, select the appropriate link, layout or static
check rather than inventing a JavaScript syntax check for those files. Browser
layout evidence is needed for claimed visual fixes. A docs-only local check may
leave the build unrun with a reason; it never changes the required branch gates.

## Specific security and data-loss regressions

Choose by the behavior changed, preserving existing auth and isolation checks:

| Affected seam | Existing command / evidence boundary |
| --- | --- |
| Principal/session verification or auth adapter | `npm run test:auth`; runtime seam changes also use `node --test tests/web/auth-runtime.test.mjs tests/edge/auth-runtime.test.mjs`. Synthetic auth tests do not activate a provider or migrate users. |
| Shared-kitchen permissions | `node --test tests/web/kitchens.test.mjs`; retain owner/read-only/account isolation assertions. |
| Checkout, receipt identity, replacement or cancellation | The focused checkout/receipt command above; preserve source observation identity, resumed drafts, undo and final-confirmation consequences. |
| Account persistence or queued state | Select affected cases in `tests/web/session-state-d1-owner04.test.mjs` and `tests/web/queue-state-http-owner16.test.mjs`; state changes must preserve account separation, revisions, conflict and replay semantics. |
| Source/data admission, privacy or schema | Use the selected owner's exact synthetic contract checks and reviewed input/admission evidence. Do not replay held corpora, use live private data or treat a generated fixture as real-input acceptance. |

A failure affecting unauthorized access, account mixing, secret exposure,
destructive writes or lost state is not a cosmetic exception. Correct it and
rerun the affected evidence. Fast development never means disabling an auth,
isolation, provenance or data-loss assertion to get a green result.

## Coherent PRs and evidence reuse

Group a change by one understandable behavior or interface: implementation,
necessary tests and its documentation belong together. Keep unrelated
formatting, framework adoption, source acquisition and deployment out of that
PR. Do not create a PR for every tiny mechanical edit; split when ownership,
rollback, release or security boundaries actually require it. The integrator
preserves other owners' work and the normal feature → develop → reviewed
release/main flow.

Reuse a previous check only when its tested source/content hashes, dependency
closure, lockfiles, schemas, selected fixtures and relevant runtime assumptions
still apply. Link the exact original command, result and evidence receipt and
state the unchanged scope. Rerun when one of those dependencies changes or a new
failure invalidates the evidence. Do not relabel an old pass as a fresh run.
Unchanged valid evidence need not be repeatedly regenerated merely because a
new report or review was requested.

For each required or selected check record `PASS`, `FAIL`, `UNRUN`, `PENDING`,
`REUSED` or `DEFERRED_RELEASE` with exact evidence. Include source commit/diff, command, environment,
selected inputs, observed result and reason for any unrun or reused check.
Use `DEFERRED_RELEASE` for a non-mandatory local full-suite check explicitly
reserved for the frozen release; record the release trigger and owner. It cannot
waive a required provider context. Actually run, reused and deferred-release
evidence remain separate. `UNRUN`, `PENDING` and `DEFERRED_RELEASE` are never
`PASS`. Reused scoped evidence does not manufacture
a green required CI context for a new commit.

## Carry scoped evidence into integration

Keep one integration writer for a coupled interface and obtain independent
review of its source and evidence. Pass the exact source/artifact pins, tested
boundary, remaining dependency and responsible maintainer. Disjoint preparation
can continue without overwriting another owner's work. It does not authorize
reading held data, deploying, or activating an unapproved service.

Record prepared, reviewed, tested, integrated and deployed outcomes separately.
A source patch and passing focused test establish only their selected scope.
Preserve original failures and evidence, including source observation times and
any remaining consumer requirement. A documentation correction normally needs
focused static checks, not a repeated application suite.

## Thorough validation at the release boundary

At the coherent release cut, run the full existing baseline and every actual
required branch check. `npm run validate:release -- --plan` lists the full local
profile without running checks; `npm run validate:release` executes it. It retains
configuration, generated-extension, all web and edge tests, Python, explicit
receipt OCR and the normal build. The generated-file guard runs before build,
and build runs before edge tests that load `dist/worker.mjs`. The build already
includes `i18n:check`, so the local wrapper omits that duplicate invocation.
The Third-party services workflow retains this full validation as an explicit
manual release action. Its automatic push and PR triggers are disabled by owner
direction; development uses affected checks. Other workflows and actual required
security or branch contexts remain unchanged.

Choose the wrapper or the corresponding direct baseline, rather than running
both. Do not add `test:auth` after full web and edge suites that already include
its files. The combined baseline below preserves source workflow checks and the
maintainer generated-file guard:

```sh
node scripts/verify-third-party-config.mjs
npm test
npm run i18n:check
npm run check:generated
npm run build
npm run test:locale-edge
python3 -m unittest discover -s tests -v
```

The workflow also names its portable receipt-OCR checks. Preserve them where
required, along with current branch protection and reviewed security/data
regressions. Source CI configuration does not by itself reveal the hosted
branch-protection rules: the integrator verifies those actual required contexts.
Removing the Third-party services automatic triggers does not waive a real
required security or branch context. If one remains required, report that precise
constraint rather than invent a pass or change branch protection. Preserve old
failed runs as failures. Manual dispatch availability must be qualified separately
because GitHub requires the workflow on the default branch; no `main` promotion
or production action follows here. Keep optional
external scans under their existing explicit configuration and holds; Sonar's
current deferral is not a passing scan.

Release evidence also covers affected built assets, source/release identity,
account/data continuity, rollback and real serving behavior. Phone-camera,
audio, keyboard/safe-area and other physical-device claims need appropriate
hardware evidence when those workflows change. Scope those checks to the
release's real behavior; do not make unrelated device tests a new gate on a
separate documentation or CSS change.

Keep exact valid test evidence from development rather than blindly repeating
it; required branch checks and release-specific integration checks still must
satisfy their actual current rules. Build, source integration, data admission,
auth activation and production deployment are separate states. Record meaningful
actions and actual check states against the selected product change, including
its source revision and output hashes. Keep one integration writer and preserve
independent review. Preserve meaningful tests and evidence; do not delete
assertions to make either profile faster.
