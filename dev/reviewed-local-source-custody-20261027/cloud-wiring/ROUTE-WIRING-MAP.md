# OffMenu application wiring — exact-source reconciliation

## Useful result

A real shared-kitchen lifecycle defect is reproduced and corrected in the source-only patch `shared-kitchen-scope-wiring.patch`. A delayed selection response currently applies the old kitchen after the account changes or resets, writing the old selection under the then-current local-storage key. Both regressions fail against the exact origin preimage. The candidate passes 13 focused checks with stubbed network requests. No authentication policy, profile-sharing policy, scanner design, production route or deployment was changed.

## Evidence identities and scope

- `origin/develop`: `dc39d0d7f29f0b0650be374f0e7e2111ec45c4b7`, inspected through GitHub tools, not assumed to be the current runtime.
- PR 138 source custody: `feature/source08-feedback-176-20261027` at `97b98b44df4bc5ae838e8b4a102c2ce8e52fa582`. Its 178–183 source is newer than develop's 175 custody. The PR was open when inspected.
- Contained application: `dev/production-release-custody/20261027-existing-fullscanner-vertical/production181-authenticated-own-data-containment/deployed-application.mjs`, verified local SHA-256 `13bd5e94c11ded5756a09edafc414791164425f4aca0b12b947849e1af60157a`. The entire blob was read through GitHub `fetch_blob`; the contents endpoint returns an empty content field for this large file and is not sufficient evidence by itself.
- Existing preserved entry: `dev/production-release-custody/20261026-existing-fullscanner-vertical/production109-exact-app-source/worker.mjs`. Release 183's wrapper delegates to this entry, whose `deployed-application.mjs` import must resolve to the contained 181 bytes, **not** the older 109 application.
- Pending local corrections were not available as verified bytes in this lane: all15 preload1384, cover49d, localhostalias5d54, own-dataR8, sourceidentityclient13d608. This patch is not claimed to include or supersede them.

## Route map: existing route composition, not a replacement design

| User flow | Exact observed wiring | What is and is not established |
|---|---|---|
| Landing → Demo | Release 183 `landing-only.mjs` final root assignment has `href="/demo/scanner.html"`. Asset overrides bind `/demo/scanner.html`, `/demo/full-scanner.js`, theme, decoder and WASM. Release 180 replaces the guest scanner bundle with the reviewed audio successor. | The existing full scanner is the Demo. Do not reintroduce the initial `/demo/scanner.js` mini-source or invent a replacement scanner. Later all15/cover local corrections still need reconciliation. |
| Landing → login | Same final root assignment has `href="/auth.html"`; auth HTML/JS are composed into the release assets. | Source link exists. The earlier root assignment was masked by a later override; `production178-normal-auth-root/root-override-disposition.json` records the fix. Edit final route composition, not an obsolete initial asset constant. |
| Login → scanner | Extracted release183 `/auth.js`: `continueToScanner` rechecks browser user against `/api/auth-page/session` and then navigates to `/shelf-scanner.html`. The server guard protects the scanner document. | Existing separate continuation exists; it must be preserved. This lane did not use a real account or claim end-to-end login acceptance. |
| Login → full app | Same auth controller has `continueToKitchen`, identical session verification, then `/kitchen.html`. Preserved worker rewrites that path internally to `/` on the retained application, adds the legacy login redirect, and keeps the browser URL at `/kitchen.html`. | Existing full-app route exists. The contained application opens the workspace after obtaining its user. The newer local identity-client correction must be reconciled rather than replaced by older origin identity code. |
| Auth guards and API | Preserved entry classifies `/shelf-scanner.html`, `/shelf-scanner`, `/kitchen.html`, `/index.html`, `/data-workspace.html` as protected documents. Unauthenticated document reads redirect to `/auth.html`; protected API reads receive 401. Private responses get `no-store` and `Vary: Cookie, Authorization`. | Do not remove or weaken these boundaries while joining source modules. No new auth gates were added here. |
| Food lookup containment | Preserved entry blocks `/api/product`, `/api/prices`, `/api/data/public` except the later qualified outer public-inventory route. Contained181 application blocks authenticated `POST /api/data/lookup` after existing checks with `503 OWN_DATA_REQUIRED`. | Develop's direct `cloud/handler.mjs` still has legacy external product/prices code. A generic source rebuild could restore it. Never adopt that fallback; own-dataR8 is a pending newer dependency. No provider was contacted in this lane. |

## Full-app interfaces already in source

| Area | Concrete paths/interfaces | Persistence and reconciliation notes |
|---|---|---|
| Profile | `public/app.js`: `loadProfile`, `saveProfile`, `persistProfile`; country/units/servings, feedback, accessibility. | `PROFILE=offmenu-profile-v1` gains `-user-<id>` or `-demo` in `switchAccount`. `saveProfile` marks dirty; personal account state includes profile. |
| Family | `public/app.js`: `renderHousehold`, `openMember`, `member-form` submission; `public/household-model.js`: `householdPortions`, `groupSuitability`, `rankedMenus`. | Members/restrictions/portion factors feed meal ranking and plan generation. Source member editing preserves existing `mealPreferences`; this is newer than the retained old bundle and must not be lost by whole-file replacement. |
| Menus and plan | `public/app.js`: `findMeals`, `menuInventory`, `renderPlan`; `public/menu-model.js`: `planSummary`; `public/household-model.js`: `generateHouseholdDay`. | Matching uses reviewed stock ingredient/quantity/location/expiry and selected diners. Recipe amounts and nutrient bases remain evidence-dependent. No canonical food identity should be invented from a barcode. |
| Cook and serve | `public/journey-ui.js`: `setupJourney({getData,commit,today,view})`, `openCook`, `openServe`; `public/cooking-model.js`: `cookMeal`, `serveBatch`, `undoCook`. | Cooking commits raw-stock deductions and cooked batch; serving writes batch events and profile history, then commits inventory. In `app.js`, the journey commit calls `save`, `persistProfile`, rerenders pantry/meals. Existing flows should be connected, not rewritten. |
| Account cloud state | `public/app.js`: `currentState`, `applySynced`, `cloudRequest`; `public/sync-ui.js`: `setupSync`; `cloud/handler.mjs`: `GET/PUT /api/state`. | Whole-account snapshot contains inventory/products/recipes/profile/selections. Optimistic revision, account-scoped storage and pending IndexedDB checkpoints already exist. The separate `cloud/session-state-d1-owner04.mjs` protocol is not imported by the inspected direct handler; do not infer it is mounted. |
| Shared kitchen | `public/sharing-ui.js`: `setupSharing`; `public/sync-model.js`: `kitchenProjection`, `applyKitchen`; `cloud/kitchens.mjs`: `/api/kitchens`, `/join`, `/:id/state`, `/members`, `/invites`. | `kitchenProjection` deliberately excludes personal members and serving identities; preserve that privacy policy. Server membership/role checks and optimistic revisions already exist. Candidate patch only binds asynchronous client requests to their originating account/key/reset generation/selected kitchen. |
| Navigation | `public/app.js:182` `setView` switches checkout, shelves, meals, plan, household, insights, integrations, me. `openWorkspace` defaults to meals; brand/#home returns to landing. | Both direct source and retained bundle lack view-specific `history.pushState`/Back-Forward restoration. This is a concrete unresolved navigation seam, not a claim that every screen is missing. No app.js rewrite was attempted while newer local app corrections are outstanding. |

## Concrete unresolved source/runtime seams

1. **Normal build is not the deployed route composition.** `scripts/build.mjs` bundles `public/app.js` and `public/shelf-scanner.js` into the direct handler. It does not include the preserved login/landing alias/auth wrapper. Direct handler maps `/` to `index.html`; it does not implement `/kitchen.html` or `/auth.html` itself. Preserve the existing wrapper and final overrides during consolidation.
2. **Scanner → stock handoff exists in develop, not in the inspected retained private app.** `public/shelf-scanner.js:172–180` writes `offmenu-scanner-kitchen-pending-v1`, schema `offmenu-scanner-kitchen-handoff/1`, then `/kitchen.html?scan=staged`. `public/app.js:53,186–190,296` validates the handoff, stages checkout with operation receipts, and requires reviewed amount/ingredient before inventory confirmation. The exact contained181 `app.js` has none of that handoff key/schema/consumer, and the preserved109 scanner keeps `kitchen-handoff` hidden. Latest local own-dataR8 may supersede this gap; its bytes are required before selecting the integration delta. Do not substitute the public-source handoff contract for the newer own-data contract without comparison.
3. **Back/Forward does not identify full-app views** in the inspected source/bundle. Only `#home` is handled. This needs a narrow integration against the selected app source once exported; no speculative route rewrite is included here.
4. **Shared selection request lifecycle** was independently patchable in `public/sharing-ui.js`. This lane supplies that delta, with the exact preimage below. Other state/lifecycle issues were not represented as fixed.

## Candidate patch and verification

Files: modified `public/sharing-ui.js`; added `public/scoped-kitchen-request.js`, `tests-web/scoped-kitchen-request.test.mjs`, `tests-web/sharing-scope-lifecycle.test.mjs`.

The request guard checks scope after session refresh, headers, and body parsing. Reset invalidates same-account in-flight work. A selection transition may close its old kitchen, but cannot cross an account/key/reset boundary. Existing authorized operations remain unchanged; no server policy or projection changes.

- Exact original `public/sharing-ui.js` Git blob: `6bafe618eae47e9a9ebc690ebca9fce27daecc03`.
- `verification/original-failure.log`: original source 1 pass / 2 expected regression failures, showing late old inventory applied.
- `verification/candidate-pass.log`: candidate 13 pass / 0 fail.
- Both changed/new browser modules pass `node --check`.
- Tests use synthetic states and fully stubbed fetches. No real-account records, source datasets, external food lookup, production change, broad release test or new delivery gate.
- `source-custody.json` records preimage and candidate SHA-256 hashes. `candidate/` is source-only, not a complete checkout/build.

Before adoption compare the recovered export's `sharing-ui.js` to the retained preimage and apply only this narrow delta if it has newer changes. This is duplicate-source reconciliation, not a request for fresh approval. Existing approved local fixes and contained181 application bytes take precedence over stale origin source.

## Historical branches inspected

- `codex/production-landing-idp-scanner-20261025`: diverged from develop, 6 commits ahead / 45 behind at inspection; contains older auth/landing/production-entry source. Do not merge wholesale over custody.
- `codex/production-landing-login-preserved-20261025`: diverged, 6 ahead / 564 behind; contains readable preserved guard/entry source matching the older deployed wrapper ancestry. Useful provenance, not current app source.
- `codex/local-onboarding-audio-20261025`: diverged, 6 ahead / 45 behind; older landing/auth/scanner changes, not the pending all15 or reviewed180 audio source selection.
- `codex/generated-menu-20261024`: already behind develop, 0 ahead / 121 behind. No independent menu delta to re-add.
