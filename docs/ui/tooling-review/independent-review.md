# Independent review: issue 33

Result: **APPROVED AS CORRECTED**, 18 October 2026 UTC. Documentation-only
assessment. No installation, UI implementation, framework migration, account
change or production action was performed or approved by this review.

## Resolved finding

The original report incorrectly said the stylesheet lacked reduced-motion
handling and proposed adding a root-scroll override. The exact pinned
[style.css, line 2](https://github.com/maldous/offmenu/blob/314822f900c49953aeca04d82ce0957d851d19c9/public/style.css#L2)
already sets scrolling to auto and disables animation/transition under the
reduced-motion media query. Independent GitHub retrieval verified blob
`d31ea4fe0ff076fed4d5f2e83bef75fa6ce4d901`; its decoded bytes produce that same
Git blob identity. The original local evidence copy has one extra trailing
newline, with otherwise identical content; this does not change the finding.

Corrected the source-findings row and UI-03: preserve existing protections and
verify only demonstrated gaps in JS-driven sensory feedback or press states.
[app.js lines 116–125](https://github.com/maldous/offmenu/blob/314822f900c49953aeca04d82ce0957d851d19c9/public/app.js#L116-L125)
contains class-based pulses and timed scan-glow/torch feedback. This is a focused
verification target, not a reproduced accessibility failure.

## Conclusions retained

- Keep the current DOM/HTML/CSS, esbuild and Worker architecture. Pinned
  package/build source supports that description. No framework migration is
  justified by these tooling choices.
- Defer Biome installation. A separately assigned, exact-version changed-file
  pilot is optional and must not block UI work. Its official support table
  confirms JS/JSON/CSS support and experimental HTML formatting:
  [Biome language support](https://biomejs.dev/introduction/language-support/).
- Reject nestjs-trpc for the current backend mismatch, not for a supposed React
  requirement. [Its documentation](https://nestjs-trpc.io/) describes Nest
  providers/decorators and Express/Fastify integration. Direct tRPC's
  [Fetch adapter](https://trpc.io/docs/server/adapters/fetch) remains technically
  possible but provides no demonstrated reason to migrate this application.
- Reject shadcn's React component stack and nuqs here. Official
  [shadcn installation](https://ui.shadcn.com/docs/installation/manual) requires
  Tailwind and React ecosystem dependencies; [nuqs installation](https://nuqs.dev/docs/installation)
  lists React-based adapters. Existing native controls/CSS and URLSearchParams
  are viable no-new-dependency alternatives.

## Scope and evidence clarifications

Clarified that source implementations are not fresh runtime proof; a Biome pilot
is a recommendation, not new authority; and physical-device checks apply to
changed device workflows, not to closing this assessment or unrelated CSS work.
No benchmark, price, complete historical-ledger reconciliation, port 7645 fix or
physical-phone test is claimed.

The supplied requirements reconcile actual owner messages with current source,
including meal-first navigation, bench/front-camera default, oversized controls,
auto-accept/void/final-receipt behavior and explicit missing feedback. The
unavailable screenshot remains an honest limitation. The independently fetched
[issue 33](https://github.com/maldous/offmenu/issues/33) matches this scope.

Publish only the decision and review deliverables to the already-authorized
repository. Raw recovered conversation JSON remains private review input.

No further prerequisite is needed before using this corrected decision package.
