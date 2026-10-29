# OffMenu UI acceptance and reuse map

This extends the existing [issue 33 decision record](tooling-review/decisions.md). It does not replace the operations ledger, the historical 105-requirement delivery register or their original owners. Current source baseline: `66d9aa67ac3406f897c86c53bda7210780dd6538`. The separate dirty DEV7645 playground is not assumed identical to develop.

## Start here for future UI work

1. Read `tooling-review/decisions.md` for recovered user direction and reviewed keep-current architecture decisions.
2. Find the applicable stable contract in `requirements-traceability.json`. Its historical crosswalk maps all 105 existing obligations without inventing duplicate product promises. Source dates matter: historical delivery statuses are not current acceptance results.
3. Reuse the playground's shared design assets and catalog when their exact paths/version are recorded by the implementation owner. Those bindings remain deliberately pending in this revision. Do not infer that the catalog is already delivered from this document.
4. Add a new contract only when no existing contract covers the requirement. Record source, applicability, rationale, priority, owner, state/route and exact test evidence. Preserve exclusions and qualified unknowns.
5. Change one reversible user-facing slice, run focused checks and inspect the actual rendered page. Publish source through the sole writer; production activation remains separate.

## Decision boundary

The repository is the reusable source of truth. Native HTML controls, CSS variables and small ESM helpers remain the architecture. A new design-system store, React/Preact island, component runtime or remote telemetry service is not needed. Shared tokens should express semantic roles (surface, text, border, action, warning), typography, spacing, radii and motion rather than one-off page colors. Every component needs default, hover/focus/pressed, disabled, busy, error and empty states where applicable, plus documented DOM/attribute/event contracts. Examples must consume the same assets as the three review areas.

Light, dark and system modes are one token system. Local theme preference may persist with failure-safe storage; system changes should be followed only while system mode is selected. Theme changes must preserve focus, current task and contrast. Do not advertise dark-mode completeness until secondary surfaces, diagrams, forms, dialogs, disabled controls and print output have been checked.

## Review evidence, not a compliance badge

The matrix is a product-specific acceptance plan informed by current primary sources. WCAG 2.2 is the accessibility reference, with WAI practical guidance for keyboard, dialog, form and page structure checks. It is not a legal-compliance or certification claim. A few examples or automated checks do not prove full-process accessibility.

The first visible slice must demonstrate the existing visual identity and Emil-guided hierarchy, spacing, feedback and motion choices. A citation alone is not a design result. Keep keyboard and repeated scan actions immediate; optional decorative effects cannot delay tasks. Compare default and worst-case content at320CSSpx, desktop, increased text size/zoom and Arabic RTL. Retain source units, unknown values, incomplete nutrition denominators and truthful provider states.

Use synthetic data only in the playground. Demo auth should be inert state exploration, without collecting passwords, tokens or real email. Show account cancellation/expiry/recovery and viewer/conflict states without activating production services. Any feedback or diagnostic export must be user-initiated, previewable and stripped of private payloads. No analytics SDK, production telemetry, medical recommendation, child profiling or external data sharing is authorized by this UI work.

## Evidence format

Each accepted requirement needs: exact build/version; route and variant; theme/locale/viewport; observed result; focused test command/result; and outstanding device/backend/independent review limits. Use explicit statuses such as source-present, implemented-unverified, rendered-verified, device-pending and accepted. Empty `evidence` and null `playgroundRoute` in the current matrix are intentional until the custodian returns actual results.

For human scoring, record clarity, visual coherence, task effort, confidence/recovery and accessibility separately, with a short reason and component/state reference. Do not turn a visual ranking into food-safety, medical, security or data-completeness approval.

## Research checked 18 October 2026 UTC

Primary URLs and their contract bindings are in the JSON `sources` map: W3C WCAG2.2, WAI patterns/tutorials, W3C internationalization and Privacy Principles, MDN Intl/theme/offline APIs, web.dev Web Vitals, official Google identity guidance, and the pinned Emil skills. Architectural and acceptance choices here are our application of that guidance. They are not copied upstream source. No external package was installed.

## Still open

- Exact playground routes, assets and first changed rendered build are owned by the existing DEV custodian.
- Actual screen-reader, physical-phone camera/audio/keyboard/safe-area and two-device behavior need their own evidence.
- Provider activation, clinical/IDDSI scope, age/jurisdiction-specific governance and production telemetry remain separate decisions.
- Global acquisition/normalization/rights work continues under dataset owners. UI samples do not satisfy it.
