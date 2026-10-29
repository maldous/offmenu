# OffMenu System 1.0

A bounded shared foundation for the OffMenu platform, implemented in the existing repository and vanilla HTML/JS/CSS build. The landing, authentication examples, application and component catalog all consume the **same** tokens and native component functions. This is available for future UI work; legacy surfaces have not been silently migrated.

## Discover and review

- Source tokens, layout, responsive and print primitives: `public/offmenu-system.css`.
- Shared rendering/interaction helpers: `public/offmenu-system.js`.
- Machine-readable component inventory: [components.json](components.json).
- Working catalog: `/playground.html?area=components`.
- Marketing: `/playground.html?area=landing`.
- Demo authentication: `/playground.html?area=auth&state=demo`.
- Inert account design: `/playground.html?area=auth&state=account`.
- Application: `/playground.html?area=app&view=today`.

Append `theme=light|dark|system` and `dir=ltr|rtl` to compare. RTL is a layout preview; copy remains English. Existing locale/RTL and source-data routes are preserved independently. Never put private pantry, household, health or authentication content in shareable URLs.

Application `view`: today, kitchen, plan, shop, me. Public review `state`: ready, loading, empty, error, offline, recovery. Auth `state`: demo, sent, error, account. These are explicitly simulated presentation states. No browser network or security setting is changed. Catalog `data`: demo, worst, empty, one. Human scores and comments stay in tab memory until an explicit local download; no telemetry or outbound submission.

## Tokens and theme contract

CSS custom properties are authoritative; do not duplicate the values in an external store. Brand cream `#f7f4eb`, forest `#183f35`, coral `#ad402d`. Semantic pairs are `--om-bg/--om-ink`, `--om-surface/--om-ink`, `--om-action/--om-on-action`, `--om-accent/--om-on-accent`; never use an accent as body text on arbitrary backgrounds. Dark mode changes semantic tokens while preserving the brand relationship. `setTheme()` sets a public data attribute and browser theme colour; System follows `prefers-color-scheme` changes without account storage.

Typography: system sans for controls/body; local Georgia/Times serif for expressive marketing headings. No external font requests. Body1rem/1.55; inputs at least16px; fluid title and hero scales. Amounts use tabular figures and `Intl.NumberFormat`, null is explicitly “Quantity needs review”. Never truncate quantities, units or dates. Spacing4/8/12/16/24/32/48/64px. Card radius18px, controls10px. Default controls56px, optional extra-large64px. Document content remains selectable; zoom is enabled.

Layout primitives: `om-main`, `om-stack`, `om-stack-sm`, `om-row`, `om-grid`, `om-two`, `om-panes`, `om-section`. Grid children use min-width0; long names wrap. At760px the main two-pane layouts stack; review and app navigation remain visible. Safe-area padding and dynamic dialog height are used; the document keeps native scrolling. Physical Android/iOS keyboard, tap and safe-area feel require actual hardware review, not a desktop emulation claim.

## APIs and state contracts

```js
import {button, badge, card, field, emptyState, openDialog,
        announce, setTheme, escapeHTML, amount} from './offmenu-system.js';
button('Add food', {variant:'accent', id:'add'});
button('Explore', {href:'/playground.html?area=app'});
button('Unavailable', {disabled:true});
badge('Needs review', 'accent');
card('Your kitchen', trustedStaticBodyHTML, {feature:false});
field('Quantity', '<input type="number" min="0" required>', 'Source unit: g');
emptyState('Room for possibility.', 'Add your first sample item.');
openDialog('Final receipt', trustedStaticBodyHTML);
announce('Item accepted.');
setTheme('system');
```

`button`: native button for an action, anchor for navigation; primary/secondary/accent/quiet variants; disabled never activates. `field`: wraps a native control and visible label/hint. Provide explicit ID/description when an independently announced error needs it. `card`: layout, not a clickable div. `openDialog`: native `dialog.showModal`, labelled heading, Escape, close control, focus at heading and return to connected trigger. No animation delays acceptance. `announce`: persistent polite status region; does not replace visible status text. Trusted body/control HTML is an internal composition API: escape untrusted content once, never pass user content directly to HTML parameters. The stock/feedback views use escaped text or `.value`.

The app uses existing `matchMeals` for measured sample readiness. Manual sample stock remains review-needed. Measured quantities, missing ingredients and unknown nutrition are distinct. No family/child/allergy safety or nutritional completeness is inferred. Shelf checkout replaces only Pantry/Shelf1 at final confirmation; grocery checkout adds. Items auto-accept, can be voided before final save, and cancellation does not change stock. These are deterministic example presentations, not a camera or barcode-decoder test. Existing full-kitchen scanner/receipts remain unchanged.

## Interaction and motion

High-frequency state updates and navigation are immediate. Pointer press feedback uses transform at120ms with `cubic-bezier(.23,1,.32,1)` and static inset confirmation. Keyboard, quiet and reduced-motion actions remove movement. Hover is capability-gated. There are no entrance keyframes, animation dependencies or screen flashes. Optional short sound/vibration/speech are off and quiet by default, require user opt-in and relevant browser support, and never block acceptance. Hardware effects are not qualified by desktop tests.

Native keyboard activation, visible focus, minimum targets and semantic labels are contracts. Contrast checks cover semantic text/surface, primary and accent pairs in light/dark. Zoom and RTL review use the same components; no new translation-completeness claim. Print styles remove review controls and keep units/grouping legible; actual print/EPUB qualification remains separate.

## Extend safely

1. Read the approved `docs/ui/tooling-review/decisions.md` from the selected repository revision; do not overwrite dirty playground files with remote snapshots.
2. Reuse semantic tokens and components. Add a component only for a concrete interaction gap; record states, inputs, keyboard/focus, unknowns and responsive behavior in components.json.
3. Preserve real auth/source/privacy boundaries. The demo has no real credentials, account calls or external store.
4. Use the existing esbuild asset list and same DEV watcher. Observe actual new build and rendered version; a source commit or old watcher record alone is not activation evidence.
5. Run changed-surface consistency checks; capture real rendered routes, small/large/RTL/dark/long/empty/error states and focused interactions. Keep physical-device and screen-reader limits explicit.

## Guidance and licensing

Official Emil Kowalski `emil-design-eng`, `mobile-native`, `pick-ui-library`, `break-ui` and `review-animations` were read at revision `2d228630ba1446365f614a108cb8252f1feda202`. Their principles guide the current stack; their React-library list is not authorization for dependencies. The MIT notice is retained in [EMIL-LICENSE.txt](EMIL-LICENSE.txt). The implementation is original native code; no upstream runtime/component package was installed.


## P41.9 brand and responsive correction
P41.2 failed human brand acceptance. Restore the selected dark Unified Desktop v1 palette (#081719 canvas, #102426 surface, #5DA2FF primary, #78C79E brand) and humanist sans. Reuse existing ◒ OffMenu implementation identity, bundled landing-art.css product-tour images and original home checkout scene. A standalone approved leaf SVG has not been located; do not invent one from the mockup. Light remains an optional alternate, dark is the default.

Shared density tokens: --om-gutter clamp(12px,1.4vw,24px), --om-gap clamp(12px,1.2vw,20px), --om-panel clamp(16px,1.5vw,24px). Main is full width; readable copy remains bounded. Desktop app adds a task rail, wide desktop shows three meal cards plus source-qualified kitchen context; tablet has two columns; mobile uses one pane and five task tabs. Keep56px targets,16px inputs, focus, safe areas and reduced-motion/quiet behavior. No real auth or account storage. Google/Apple/email are explicitly planned/inert. Checkout scope chooses pantry/fridge/freezer; only final confirmation mutates the chosen shelf, shopping is additive.


## P41.9 viewport contract
Latest explicit Matt direction via Morgan01a14729: one pane, no vertical scrolling of any type, stationary header/footer, full viewport and predictable layout. Native DOM pagination keeps all pages connected and preserves handlers. Screen and modal Previous/Next controls replace vertical overflow; resize/visualViewport changes repaginate. Restrained inset gloss and small static shadows give depth; no blur/animation. If an atomic control cannot fit at high zoom/keyboard height, a visible layout-conflict alert replaces a silent clip; this is an unresolved accessibility conflict, not a pass or permission to reduce text/touch targets. Physical keyboard/assistive-tech/zoom qualification remains separately evidenced.


Wide-screen feedback correction P41.9: Matt reported excessive empty PC background. Keep marketing hero and existing checkout context side by side for the full available page height. Compact the actual demo stock/ready-recipe/planned-meal context into a table beside the three meal cards; no invented progress, extra filler widgets or fabricated prices/nutrition. Preserve fixed header/footer and native page controls. Human visual acceptance remains pending.


## P41.9 — human consistency rejection, canonical foundation
P41.5 failed Matt’s visual consistency review. Same1440x900 dark rendered comparison found H1s49/65/32/64px, Georgia italic in landing/auth, blue vs gold actions and pale mint checkout canvas. Shadows were absent or only13% black/3% highlight. Do not infer acceptance from shared token names.

Canonical all-four typography: system sans stack, body16px/1.5, H1 clamp(32px,3.333333vw,48px)/1.1 weight750, H2 24px/1.2 weight750, H3 18px/1.35 weight700. No serif emphasis; brand green can emphasize with the same face. Same semantic teal surfaces, blue primary actions,16px panels/10px controls, shared border and visible static shadow plus top-edge gloss. Gold is informational status, not a competing primary action scheme. Retained artwork canvas now uses the same surface; decorative package/receipt objects remain artwork.

URL theme is explicit canonical state. Header brand navigation carries it; all in-app route navigation applies it. Preference system resolves to explicit data-theme light/dark and retains data-theme-preference system; the visible build marker names the actual resolved theme. System change rerenders coherently. No account/storage persistence, credentials or provider calls. No features/tooling work in this slice. Human review remains required.


P41.9 final focused foundation: all-four shared type/palette/elevation and continuous mobile frame; marketing landing, provider-first sign-in, sample post-sign-in workspace, actual component catalog retain distinct purposes. No copied marketing hero in sign-in. Issue32 and inspected develop-abecb99 docs establish required Better Auth migration with an unmounted factory/seam: email disabled by default, Google absent pending qualification, no source-default live social provider. Apple/GitHub/Microsoft are labelled library capability catalog only, not configured/approved OffMenu methods. No passkey/enterprise project requirement was established, so those are omitted. Local demo is explicitly available; provider actions disabled; no credentials. Official Better Auth Google/GitHub/Microsoft/email documentation read alongside exact project docs, retained in auth32 evidence.

Latest mobile feedback: continuous canvas, shared purposeful separators; outer stacked panel frames removed on mobile. Desktop retains visible canonical shadow/gloss. Shared flex tracks fill the viewport while fixed-size controls stay fixed. First-page wrappers and actual panel bounds both require rendered checks; a full-height empty wrapper is not evidence of a filled sheet.

Checkout is HTML/CSS, not Three.js. Optional one-shot1200ms transform-only sample movement is explicitly requested; no automatic loop, no state mutation. Reduced-motion path remains static; IntersectionObserver pauses offscreen illustration. Three.js trial remains a separate later selection, not installed.


## P41.9 landing story replacement
Matt rejected the home-checkout/toy hero completely. Replaced it with one adult paper/vector kitchen character and a seven-chapter scan→stock→recipes→plan→shop→cook/use→replenish narrative. Play/Pause, Replay, Back/Next, named chapter select and chapter progress are native controls. SVG content and meaning-bearing captions render only on Landing. No video/3D/dependency/network load; one3200ms timer only while explicitly played, end stops, offscreen/hidden document pauses. Reduced motion disables playback and keeps every static chapter accessible. Scene objects depict sample rice/peas/tomatoes and state unknown nutrition/current prices; no pantry/account/camera mutation. Storyboard and rollback are retained in playground-story-20261018. Prior shared visual foundation remains; human narrative acceptance pending.


P41.9 latest human motion correction supersedes paused-by-default/one-pass P41.8 behavior: normal motion autoplays only while the hero is visible and the document is not hidden, cycling seven3200ms chapters. Pause explicitly persists in this tab; chapter selection switches to static inspection. Replay returns to the start. Reduced-motion disables playback and retains captions/chapters. Hand gesture, scan beam and cooking steam are transform/opacity-only and stop offscreen/hidden; one timer exists only during active playback. No Three.js/video/dependency. Actual motion and scene transitions must be observed before claiming this direction delivered.
