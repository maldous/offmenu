# OffMenu lifecycle delivery runbook — 17 October 2026

This is Worker31's external working runbook and evidence entrypoint. The existing permanent ledger remains authority. This file neither schedules work nor assigns another writer. Use the exact result IDs in receipt.json; never treat this directory as a replacement tracker.

## Carry one useful outcome through delivery

Start with the actual user journey, current source revision and existing writer. Choose an outcome such as inventory → three meal choices → plan/list → cook → serve/save leftovers → restore, rather than another helper in isolation. Preserve already accepted source/report/review evidence; do not repeat its broad tests. Fix an observed error and check the affected behavior proportionately. Heavy static/dependency audits belong to initial or Main's existing nightly health work. No new pre-commit, mandatory GitHub Action, general review-per-increment barrier or scheduler follows.

Shared changes require the exact existing custodian and allowed current target; that is a real single-writer boundary, not a generic request for design permission. Worker31 owns this external runbook/inspection artifact only. Main's existing nightly scheduling remains untouched. Existing25 tooling and24 repository support were proposed in the assignment, not dispatched by this worker. Coordinate their eventual evidence through Gateway, without direct worker messages.

## Distinguish the three delivery paths

| Path | Source/build entry | Result and boundary |
| --- | --- | --- |
| Legacy local Python prototype | `offmenu/cli.py`, `offmenu/core.py`, `offmenu/server.py` | SQLite inventory/menu CLI and optional local server. It is not the deployed app, curated corpus or proof of cross-device restore. |
| Application / account / household path | `public/app.js` → pure models/UI adapters; `scripts/build.mjs` → `dist/worker.mjs`; `cloud/handler.mjs` | Cloudflare application with separately authenticated private state and public/cached provider routes. Build writes generated/source-adjacent artifacts, so do not run it in another owner's dirty checkout. No application deployment is authorized here. |
| Curated public corpus publication | `netlify.toml` → `scripts/prepare-curated-publication.mjs` | Requires an explicit accepted local curated release and emits `dist/curated-public`, not the household app. Source archives/private responses remain local. Netlify's small curation landing page is not a missing app build. Publication remains held. |

Never infer a deployed release from a branch name, helper acceptance, README or build command. Bind source commit, artifact hash, allowed provider target, actual integration and observed readback separately when selected. Keep Netlify corpus and Cloudflare application evidence separate. Do not execute old deployment instructions from README or stale handovers merely because they are present.

## Current source and custody readback

Initial immutable local snapshots: main `8652b312ce7989c5e4f2d49ae765d5d8daf5841d`; develop `5f5bdb6ae716cbf80fab1e174d1af2e354468ead`; origin/develop tracking ref `4693cbc3fe17cdde2e292e6eb00cd83769ee45ae`. Main is an ancestor of develop by16 commits; local develop is behind its tracking ref by12. These are local observations, not a fresh provider fetch. No integration target was appointed by this review.

The main checkout has existing modifications in `offmenu/cli.py` and `public/sources.js`, plus existing untracked provider/data work. Preserve them. There are99 registered worktrees; registration is neither99 native workers nor authority to clean them up. No reset, clean, stash, prune, archive or process action is permitted by this runbook. Worker31's original and helper checkouts remain retained.

The delivery policy's historical sentence saying lifecycle messaging is blocked describes its publication-time state. Current renewed dispatch, observed native turn01a1450c-a4ca-77f2-ac19-734a3a53ff76 and pickup2263 establish this task's actual pickup. They do not erase previous denials or authorize other routes. Retained human ordinary-update authority permits status/results only to the existing Gateway; raw send admission does not prove wake, pickup or acceptance. Do not retry an uncertain or denied send.

## Reuse the implemented inspection tools

The external `inspect-delivery.mjs` reads an explicit immutable Git revision, parses JavaScript modules with the already installed Acorn, and writes a source-hashed import graph outside the repository. It never builds/evaluates application code, installs, fetches, schedules or edits Git/source. Run it only for a selected initial/nightly investigation or a changed source concern:

```sh
node /home/user/Documents/Codex/2026-10-17/offmenu-lifecycle-health/owner-31/inspect-delivery.mjs \
  /home/user/src/offmenu IMMUTABLE_COMMIT \
  /home/user/Documents/Codex/2026-10-17/offmenu-lifecycle-health/owner-31/SELECTED_OUTPUT.json \
  /home/user/src/offmenu/node_modules/acorn/dist/acorn.mjs
```

Select the commit/output first; do not overwrite frozen evidence. A module outside declared roots can be an intentional tool, HTML entry or standalone component. It is not a deletion candidate without caller analysis. Current snapshots have zero parse errors and missing relative imports; that does not prove runtime correctness. Exact duplicate function bodies were not found; related allocation logic still has divergent semantics.

`observe-journey.mjs` is the retained reproduction of this investigation's fabricated model path and observed defects. It loads immutable source into an isolated VM with presentation-only i18n stubs. Its output demonstrates pure-model behavior, not physical scanning, browser storage, account sessions, provider correctness, cooking/nutrition safety or end-to-end product acceptance. Reuse its current output; rerun only against an appointed correction or materially changed source, not on every turn. The Node experimental VM warning is a harness limitation.

## Fix the observed product defects through the existing writer

Use corrective-packets.json; they contain exact functions/source hashes, reproduced before-state, outcome and narrow verification. Priority is expired-stock duration inflation, then false ready status for unknown recipe yield, then null amount coercion. No speculative edge matrix or wholesale identity/unit redesign is needed to correct these observed behaviors. The known source/caller-basis gaps remain separate and must not be filled by invented stock or preparation facts. Current-target/custody binding is required before shared edits; this review did not appoint one.

Use the observed model journey as the useful outcome when integrating related corrections: five fabricated lots produced three ready choices; planned stock generated no measured gaps; cooking deducted100g rice; serving one portion at50% saved0.5 portion and left1.5; validation retained the batch, history and manual list; duplicate serving did not decrement again. These narrow positives do not certify all requirements.

## Sonar dependency — no access bypass

`OFFMENU-SONAR-ASSESSMENT-REMEDIATION` is a separate dependency under BACKLOG-AUDIT. Retained Gateway baseline reports permission denied on `/var/run/docker.sock`. Service/version/project, scan source coverage and issues remain unknown; zero scan was performed. This worker did not retry Docker, change permissions/groups, use sudo, probe another port, install a service or create credentials.

The existing host custodian must supply an already-authorized service/scan route and actual service/version/project identity. Then Gateway can select the scan against the whole selected product source, bind revision/analysis timestamp and coverage, preserve issue keys/severity/components, appoint disjoint existing writers for real fixes, and rerun the same project/source scope to verify changes. Keep source/secret/private-data boundaries. Do not blanket-exclude files, suppress findings, weaken quality gates or equate AST parsing with a Sonar scan. If the route is still unavailable, record that exact dependency without replaying the denied command. No new service or scheduler is the workaround.

## Completion and remaining work

Record prioritized results and implemented external fixes under the existing BACKLOG-AUDIT child, refresh the existing handover, and notify Gateway once with the exact result/receipt pin under retained human authority. Bind transport evidence separately. Shared bug corrections, source admission, caller integration, live phone/provider/two-device checks and Sonar are remaining work; this initial bounded assessment does not close BACKLOG-AUDIT or the whole product. Publication, production, CIX, source/privacy/custody and all actual denied-action holds remain.
