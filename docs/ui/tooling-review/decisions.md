# OffMenu issue 33: design reconciliation and tooling decisions

Status: INDEPENDENT REVIEW COMPLETE; APPROVED AS CORRECTED. No adoption or production change authorized by this report.

Decision date: 18 October 2026 AEDT. Original assessment: 17 October UTC; independent review and correction: 18 October UTC. Documentation-only decision package; no packages installed, runtime edited, framework migrated, credentials changed or deployment performed.

## Outcome

Keep the existing vanilla JavaScript/HTML/CSS, esbuild and Cloudflare Worker architecture. Do not adopt nestjs-trpc, shadcn/ui or nuqs in this implementation. Biome is compatible as developer tooling, but defer adoption pending one small, nonblocking, exact-version pilot; it is not a dependency of UI delivery. Implement focused presentation repairs using current native controls and CSS. Preserve the original product concept and the later explicit correction that meals must not be secondary to scanning.

## Evidence and confidence

- [Issue 33](https://github.com/maldous/offmenu/issues/33) defines assessment scope and prohibits a React/Preact migration merely to use tooling. Issue body is the current recorded direction, not evidence that any implementation is complete.
- Pinned source: [314822f900c49953aeca04d82ce0957d851d19c9](https://github.com/maldous/offmenu/tree/314822f900c49953aeca04d82ce0957d851d19c9). GitHub connector reads of package.json, scripts/build.mjs, public/index.html, public/style.css, public/app.js and public/scanner-ui.js were preserved for this review. This is source inspection, not a current live-site or phone test.
- [Latest operations checkpoint](https://github.com/maldous/offmenu/blob/3a103bc7c380da01c83fcda35d82c92741379804/docs/operations/morgan-delivery-ledger.json) references the preserved base, 5,271-event journal and separate historical cuts. It records issue 33 and pending semantic projection; its queued worker roster predates this task's actual pickup. Do not claim all historical requirements have been replayed or closed. The underlying journal is not semantically reconciled by this report.
- Prior conversation messages below were read in context through the connected conversation reader. Direct owner requirements are distinguished from assistant completion reports. The attachment in the development-server conversation was omitted by that reader, so its screenshot is unavailable here.

## Recovered requirements and decision history

All dates in this section are 12 October 2026 UTC unless stated otherwise. Links are private user conversation links; do not grant access or copy private conversation content to a new audience. Concise product requirements may be published to the already-authorized repository, with links retained as provenance.

| ID | Source-linked owner requirement | Current pinned implementation and disposition |
| --- | --- | --- |
| R1 | [08:34 layout direction](https://chatgpt.com/c/6acc7fdf-a7bc-83ec-98f0-54206442ff39?messageId=bbb21a18-e6c0-4f58-a291-c6191f17d351): marketing landing, login/demo, branded identity-provider options; interactive widgets rather than text analytics | index.html has marketing hero, demo/login controls and illustrated checkout; keep this identity. Verify actual supported login options with auth lane; do not show fictitious providers. |
| R2 | Same source: empty one pantry/fridge/freezer shelf onto a bench, scan it back through a fun simulated checkout; also unpack shopping/deliveries | Existing shelf reset and additive shopping modes, register illustration, nutrition, final receipt. Keep distinct replace-versus-add consequences. |
| R3 | [08:57 front camera](https://chatgpt.com/c/6acc7fdf-a7bc-83ec-98f0-54206442ff39?messageId=bbb210ad-da18-4b36-9c2d-bb80472215db): phone screen-up on bench | scanner-ui.js:10–12 sets bench/user/mirrored defaults, then restores saved settings. Mark present; HTML option order alone is not behavior. Preserve selectable rear modes for unsuitable front-camera focus. |
| R4 | [08:58 efficient checkout](https://chatgpt.com/c/6acc7fdf-a7bc-83ec-98f0-54206442ff39?messageId=bbb21ffe-00d7-4c8c-a3ed-b3e2b8c341b6): auto-accept without per-scan buttons, void/undo, final receipt review and print/PDF | app.js autoAccept, receipt Void/Correct and print handler exist. Unknown products remain on receipt for review. Preserve nonblocking lookup and duplicate protection; final review must precede inventory replacement. |
| R5 | [09:00 feedback options](https://chatgpt.com/c/6acc7fdf-a7bc-83ec-98f0-54206442ff39?messageId=bbb218ce-af67-4d38-b80e-b4c3f6abe644): vibration, light/screen, sounds, spoken product; [09:03 accessible controls](https://chatgpt.com/c/6acc7fdf-a7bc-83ec-98f0-54206442ff39?messageId=bbb2104e-f183-4103-a1d2-b1dcc5570907): oversized buttons | Feedback preferences default off; quiet mode and large controls already exist. CSS later overrides base buttons to 56px and many mobile controls to 64px. Preserve this; do not report the earlier 38px chip rule as final computed height. Verify unsupported device options accurately. |
| R6 | [09:10 correction](https://chatgpt.com/c/6acc7fdf-a7bc-83ec-98f0-54206442ff39?messageId=bbb21606-650b-40b0-80b6-db173f7f2d2e): menus must not be second class; quantities, directions, food data, daily/weekly totals; fix missing space in kitchen heading | Current primary navigation is Today/Kitchen/Plan/Shop/Me, with scan/add in a capture dock. Hero leads with dinner from existing food; heading has separating space. Retain these delivered corrections rather than redesigning around scanning again. |
| R7 | [09:23 planning direction](https://chatgpt.com/c/6acc7fdf-a7bc-83ec-98f0-54206442ff39?messageId=bbb213f4-c870-40ac-af34-b3ac98a259b8): custom storage locations, household dietary preferences, shared meal solutions, shopping to unlock meals, duration planning, professional print/Kindle/phone artifacts | Custom storage input, member forms, plan and document/EPUB/print UI exist. Presence is not correctness or nutritional completeness; retain existing workflows and verify them separately. |
| R8 | [10:03 statistics](https://chatgpt.com/c/6acc7fdf-a7bc-83ec-98f0-54206442ff39?messageId=38ae91df-b59d-4280-ae41-1f2c6d409fbe), [10:11 completion/waste](https://chatgpt.com/c/6acc7fdf-a7bc-83ec-98f0-54206442ff39?messageId=bbb21ca6-6ea2-459e-8ea9-6181c644b7c5), [10:20 wording correction](https://chatgpt.com/c/6acc7fdf-a7bc-83ec-98f0-54206442ff39?messageId=df36e7a6-9a76-4f98-9b8e-87467e860a88): intake charts/goals, optional meal completion, garbage checkout, dietary history | Preserve statistics/history, waste receipts, entered dates versus freshness estimates and optional completion controls. Never imply estimated freshness proves safety, or incomplete nutrition is complete. This decision task adds no health advice or data sharing. |
| R9 | [15 Oct development-session report](https://chatgpt.com/c/6ad14ed5-670c-83ec-9f55-2d5953593f1a?messageId=9905d423-438f-4d7a-b37b-ae6c5a12df03): actual port 7645 looked unstyled and retained unwanted private-development banner | Secondary assistant report; original user image unavailable. Requires same-instance serving/process/asset verification, not another design. This task did not access port 7645 and cannot call it fixed. Removing a banner must preserve authentication and truthful feature limitations. |

Additional scanner conversation was discovered ("Optimise Barcode Scanning", conversation 6accc096-1268-83ec-bce9-96194ad858f1); its search results describe added camera/lens/mirror controls and outstanding real-device testing. Search for OffMenu camera returned partial results, so complete camera history is not asserted. Nothing recovered supersedes the bench default established in actual source.

## Actual stack

[package.json](https://github.com/maldous/offmenu/blob/314822f900c49953aeca04d82ce0957d851d19c9/package.json) uses ESM, Node test runner, i18n checks, esbuild 0.25.12, Acorn, Miniflare, Netlify Identity and zxing-wasm. No React, Preact, NestJS, Tailwind or TypeScript application framework is declared. [build.mjs](https://github.com/maldous/offmenu/blob/314822f900c49953aeca04d82ce0957d851d19c9/scripts/build.mjs) bundles browser entry points and a Worker, packages HTML/CSS/assets, and stamps the source commit. [app.js](https://github.com/maldous/offmenu/blob/314822f900c49953aeca04d82ce0957d851d19c9/public/app.js) uses DOM handlers, fetch, native dialogs, local state and URLSearchParams. This is not the older Python-only web.html prototype.

## Compatibility, alternatives, costs and decisions

| Tool/problem | Fit and useful benefit | Alternatives, impact and decision |
| --- | --- | --- |
| Biome: formatting/linting | Framework-independent; supports JS/JSON/CSS. Current official support table marks HTML formatting experimental/opt-in, YAML and Markdown in progress. Could improve readability of dense source and catch mistakes; not an accessibility or behavioral test. | **Defer installation; recommend a scoped optional pilot only if separately assigned.** One exact-version dev dependency, config and binary/update ownership; no runtime payload or new hosting service. Compare against keep-current targeted Node tests and manual style, and Prettier (broader HTML/Markdown/YAML formatting) plus ESLint (custom lint ecosystem). Two-tool alternative adds config/package maintenance; existing source has no formatter migration to preserve. Measure actual changed-file runtime, diagnostic value and diff before adopting; exclude generated assets, datasets, lockfiles and copied vendor material. No mandatory precommit/full-repository checks, unsafe auto-fixes or format-only churn during active feature lanes. |
| nestjs-trpc: typed API integration | Designed for NestJS providers/decorators and Express/Fastify; type generation and tRPC/Zod ecosystem. Not a UI library, and not inherently React-only. Current Worker/JS backend does not have NestJS. | **Do not adopt.** Adds Nest runtime/DI/decorator and schema/type generation work, tRPC dependencies, API-client migration and deployment requalification without evidence this is the bottleneck. Keep current fetch endpoints, validators and targeted contract tests. Direct tRPC has a Fetch/edge adapter and is a more plausible future option if an independently justified TypeScript contract project emerges, but also introduces schema/client/protocol maintenance. Neither option fixes UI or preserves external REST/MCP clients automatically. No new server/paid infrastructure justified here. |
| shadcn/ui: reusable accessible UI | Open-code component distribution, not a hosted magic styling switch. Current official install uses Tailwind and React ecosystem components/dependencies. Owning copied source means ongoing component updates and tests are our responsibility. | **Do not adopt its React component stack.** Native buttons/selects/dialogs plus existing CSS are the immediate alternative, with keyboard/focus/contrast testing. Web Components could be reconsidered for a specifically demonstrated complex widget, but no new component runtime is needed now. Introducing React or Preact islands solely to use shadcn violates scope and creates duplicate state/rendering/style systems. Copying design principles is possible; blindly transplanting component behavior is not. |
| nuqs: URL state | Current nuqs v2 supported adapters are React/Next/Remix/React Router/TanStack React. Useful typed query parsers and synchronization in those applications; no direct fit for current DOM app. | **Do not adopt.** Keep URL/URLSearchParams and History API with a small tested serializer if deep links become a scoped feature. Allowlist public view/filter/sort/page state; preserve unrelated query parameters and back/forward behavior; reset page when filters change. Never serialize household measurements, dietary histories, tokens or private pantry content into shareable URLs. This requires tests and ownership but no runtime dependency or framework. |
| Keep current: all four domains | The pinned source contains implementations of the core checkout/meal/receipt patterns; runtime correctness remains separately qualified. | **Chosen implementation baseline.** Zero added package/runtime/license exposure; still incurs maintenance of DOM rendering, URL parsing and accessibility. Split functions only where a concrete changed workflow needs it. Keep tests focused on changed behavior. Revisit a library only when a measured gap outweighs its full migration/maintenance cost. |

No dollar estimate or performance benchmark is invented. These are local-code tools rather than a required metered service purchase; adoption still incurs engineering, supply-chain, update and license-compliance costs. Before any package pilot, record exact release and license from its published package; no rolling installer is approved by this document.

Official sources checked 17 October 2026 UTC: [Biome](https://biomejs.dev/), [Biome language support](https://biomejs.dev/introduction/language-support/), [Prettier](https://prettier.io/docs/), [ESLint](https://eslint.org/docs/latest/use/getting-started), [nestjs-trpc](https://nestjs-trpc.io/), [tRPC Fetch adapter](https://trpc.io/docs/server/adapters/fetch), [shadcn introduction](https://ui.shadcn.com/docs), [shadcn manual installation](https://ui.shadcn.com/docs/installation/manual), [nuqs installation](https://nuqs.dev/docs/installation), [URLSearchParams](https://developer.mozilla.org/en-US/docs/Web/API/URLSearchParams). Compatibility conclusions are this review's architectural inference from those sources and pinned code, not measured installation trials.

## Final presentation standards

1. Landing: retain cream/forest/coral palette, checkout illustration and friendly voice. Lead with the meal outcome, then explain shelf inventory and shopping-unpacking. Keep demo and actual login visibly available. No speculative new brand/theme, scanner-only homepage, fabricated endorsements or promised unavailable integrations.
2. Application: retain Today/Kitchen/Plan/Shop/Me hierarchy with fast scan/add access. Use clear task cards and progressive disclosure; statistics and menus remain first-class. Show ingredient quantities, units, portions, evidence gaps and daily/weekly context. Never replace a real unknown with zero or hide an incomplete nutrition denominator.
3. Checkout: auto-accept confirmed barcode events without per-item confirmation; preserve presentation/duplicate gate and optional correction. Make latest-item status, count, Void and final receipt easy to see. Unknown lookups must remain reversible and explicitly unresolved. Final action distinguishes shelf replacement, additive groceries and waste removal.
4. Inclusive interaction: retain oversized controls (existing 56px baseline and larger mobile scan actions), keyboard activation, visible focus and semantic labels. No hover-only actions; capability-gate decorative hover. Keep zoom and content selection. Inputs, including textarea and compact language controls, need mobile computed text-size review rather than assumptions from base declarations.
5. Motion and feedback: optional sensory effects, quiet setting, no required sound/vibration/speech. Reduced motion must disable unnecessary smooth scroll/pulses; repeated checkout feedback never delays accepting the next scan. Use short scoped CSS properties and press feedback; do not add an animation runtime. Avoid screen-flash patterns that are unsafe or distracting; make a static status equally sufficient.
6. Mobile/responsive: test actual component widths, 320px, wide desktop, 200% zoom, long translations and current Arabic RTL. Fixed/sticky elements must clear safe areas and soft keyboard. Do not globally disable scrolling/overscroll or selection. Android/iOS camera, audio, focus and safe-area behavior remain real-device acceptance items.
7. Trust: demo is clearly labelled and isolated; unavailable services are honestly labelled at the relevant action. Do not expose fixture credentials or a stale private-development banner. Preserve auth/security and account-private health data during styling changes. Printed receipts/plans should have legible grouping, units, dates, page breaks and provenance; test print and EPUB outputs rather than promising a new PDF engine.

Applied guidance: read actual pinned Emil `emil-design-eng`, `mobile-native` and `pick-ui-library` source, revision [2d228630ba1446365f614a108cb8252f1feda202](https://github.com/emilkowalski/skills/tree/2d228630ba1446365f614a108cb8252f1feda202). The curated library list is not authorization to add React dependencies. For implementation, apply `break-ui` fixtures and explicitly run `review-animations` on changed motion. Preserve MIT notice if copying any upstream material. This standards document paraphrases applications and does not install the skills.

## Scoped implementation backlog and acceptance

Owners are implementation roles, not claims of active task pickup. Morgan coordinates assignment and publication; a separate reviewer must validate each change. No production action is included in this decision task. Acceptance checks apply to changed surfaces; unrelated physical-device checks remain explicit open items, not prerequisites to closing this assessment or shipping an orthogonal CSS fix.

| Priority / ID | Owner and scope | Acceptance evidence / stop condition |
| --- | --- | --- |
| P0 / UI-01 | Development-server maintainer: reconcile actual port7645 process/worktree/build and asset path, without stopping unrelated workers | Same forwarded endpoint Android-sized screenshot, CSS/JS successful responses/content types, no console fatal error, serving source commit, primary navigation/buttons work; banner absent while auth remains enforced. If endpoint unavailable, record that blocker; a build pass is insufficient. |
| P1 / UI-02 | UI engineer: focused CSS/accessibility polish only | Before/after screenshots at320px/desktop/200% and Arabic RTL; keyboard/focus checks; no clipped primary action; retain oversized hit areas. Fix ungated hover, textarea/compact input text-size issues if computed styles confirm them. No wholesale restyling. |
| P1 / UI-03 | UI engineer + accessibility reviewer: verify existing reduced-motion handling; repair only demonstrated JS-feedback or press-state gaps | Retain the existing CSS reduced-motion block. Check JS-driven scan-glow/light feedback and press states where changed; require before/after/why evidence for actual repairs. Repeated scans must not wait for effects; static status works with quiet mode. Physical sensory checks apply when those effects change and remain explicitly pending otherwise. |
| P1 / UI-04 | UI QA: synthetic state/checkout regression tests at current boundaries | Long/non-Latin names, zero/one/large collections, decimal quantities, unknown packs, delayed/error lookup, duplicate presentation, Void, final confirmation, cancel/reload, read-only kitchen; no live user data mutated. Document existing tests reused and precise new tests; do not rerun unrelated corpus suites. |
| P1 / UI-05 | Product/UI QA + auth lane: demonstrate preserved journeys | Demo/login landing, bench default and saved rear preference, shelf versus groceries, meal planning/shopping, stats, documents. Browser evidence plus physical-phone camera/audio check; supported provider branding only. No auth migration dependency added solely for presentation. |
| P2 / TOOL-01 | Developer tooling owner: optional exact-version Biome pilot after UI-01 priority | Changed-file check timings and useful diagnostics versus baseline; reviewed sample diff; no generated/data files touched; target tests remain green. Adopt only if measured value outweighs churn. Otherwise explicitly keep current. No mandatory heavy gate. |
| P2 / UI-06 | UI engineer: URL-state helper only when shareable filters are requested or needed | Valid/invalid/duplicate parameters, unicode, reload and back/forward, unrelated query preservation; sensitive fields excluded; no nuqs/React added. Do not implement speculative routing. |

## Adversarial checks and independent resolution

| Challenge | Resolution |
| --- | --- |
| Keeping vanilla can perpetuate dense/unmaintainable DOM code | True. Use concrete workflow seams and targeted tests; dense code alone does not justify a second rendering stack. Biome pilot may help readability but is not a refactor substitute. |
| Rejecting nestjs-trpc because React is forbidden would be technically wrong | Rejected for Nest/backend mismatch, not React. Direct tRPC Fetch remains a technically possible but currently unjustified future contract option. |
| Native controls do not guarantee complete accessibility | Correct. Keyboard, focus-return, announcement, contrast and zoom checks are mandatory acceptance evidence; dependency count is not accessibility evidence. |
| HTML source suggests rear camera default and small chips | Runtime preferences select bench/front; later CSS overrides enlarge controls. Do not file false regressions from first declarations. |
| Biome website says HTML support; report calls it limited | Official detailed table specifically labels HTML formatting experimental/opt-in. Avoid HTML autoformat pilot; recheck exact pinned package support. |
| Historic assistant reported deployments/tests, so requirements are complete | No. Prior completion reports are contextual, current code presence is qualified, and this task has no live/device evidence. |
| New standards could erase prior design | Requirements above preserve the original checkout playfulness and explicit later meal-first correction; no new visual language is invented. |

## Source-level polish findings to verify during implementation

| Before | After | Why |
| --- | --- | --- |
| style.css:2 ungated button:hover; no :active rule found in this stylesheet | Capability-gated hover and short press-state feedback | Touch must not rely on sticky simulated hover; verify focus and disabled states |
| style.css:2 already has a reduced-motion block that changes root scroll to auto and disables animations/transitions; app.js:114 also checks reduced motion for one scroll | Preserve both existing protections. Verify remaining JS-driven scan-glow/light behavior in app.js:125 only if that workflow changes | Independent review corrected the earlier false missing-CSS claim; a duplicated root-scroll repair is unnecessary |
| style.css:42 language-select 14px; textarea inherits 15px body or context (17/54) | Verify computed mobile fonts, set affected inputs to at least16px | Existing input/select16px override at line8 does not cover every later specific rule |

These are static findings, not visual/device failures reproduced in this task. No code repair was performed.

## Independent review result

Approved as corrected on 18 October 2026 UTC. The reviewer independently checked
the pinned source, all supplied artifact hashes, issue 33, recovered owner-message
roles and current official tool documentation. The compatibility conclusions and
keep-current baseline stand; no new dependency is necessary for the planned UI work.

The material correction was a false negative in the source-level motion finding.
[style.css at the pinned commit, line 2](https://github.com/maldous/offmenu/blob/314822f900c49953aeca04d82ce0957d851d19c9/public/style.css#L2)
already contains a reduced-motion media query that sets root scrolling to auto
and disables animations and transitions. The GitHub connector independently
confirmed blob d31ea4fe0ff076fed4d5f2e83bef75fa6ce4d901. UI-03 now preserves that
block and scopes any work to demonstrated gaps in JS-driven feedback or press states.

Two clarifications prevent accidental extra scope: the Biome pilot is an optional
recommendation, not authorization or a prerequisite; physical-device acceptance
items apply to affected device workflows and do not hold up this documentation
decision or unrelated styling fixes. Current-source implementations are not
described as fresh end-to-end runtime proof.

The preserved raw conversation JSON files are private review inputs. Publish only
the decision/review deliverables to the already-authorized repository; do not
publish the raw recovered conversations or broaden their audience.
