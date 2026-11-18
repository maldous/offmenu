# Scanner controls and help crosswalk

This is a bounded source map for the barcode reader and source-inspection task,
not a complete OffMenu feature, audience or accessibility inventory. It maps all
48 static `button`, `input`, `select` and `textarea` nodes in
[`shelf-scanner.html`](../apps/web/assets/shelf-scanner.html) at source
`0e02f3de39757af60d8d58673afc09205600e865`. There are 43 distinct IDs;
the four readout tabs and the manual-submit button have no ID.

The task guide references below mean its frozen, source-reviewed edition
[`c0644bc9812dc1f4ddb00474c1eb49175903f3a6`](https://github.com/maldous/offmenu/blob/c0644bc9812dc1f4ddb00474c1eb49175903f3a6/docs/scanner-user-guide.md),
not an assertion that a running installation uses that edition. That guide
retains the original journey-body source pin and separately identifies its
current-language note. This crosswalk does not recertify the whole older body.

## Reading the table

- **Direct** means the named guide passage explains the task/control at a source
  level. It does not establish discoverability, readability or a successful task.
- **Partial** means the guide explains the broader task but not this particular
  affordance, alternative or recovery condition. Do not count it as full help.
- **Gap** means no explicit explanation was found in the selected task guide.
  It does not mean there is no help anywhere else in OffMenu.
- The intended actor here is a person reading a barcode and inspecting source
  information. Household roles, administrators, assistive-technology users,
  language/device audiences and their full journeys remain separately unmapped.

`S` below is the [shelf entrypoint at the selected source](https://github.com/maldous/offmenu/blob/0e02f3de39757af60d8d58673afc09205600e865/apps/web/src/shelf-scanner.js);
`C` is its [camera adapter](https://github.com/maldous/offmenu/blob/0e02f3de39757af60d8d58673afc09205600e865/apps/web/src/scanner-ui.js);
`L` is [shared language setup](https://github.com/maldous/offmenu/blob/0e02f3de39757af60d8d58673afc09205600e865/apps/web/src/i18n.js).
Line numbers describe that immutable edition, not future line positions.

## Static control mapping

The node number is zero-based HTML order within the stated four tag kinds.
Names in parentheses identify the otherwise ID-less controls, not invented IDs.

| Node | Control | Source task/binding | Selected guide passage | Coverage |
| --- | --- | --- | --- | --- |
| 0 | `manual-quick` | S 173 delegates to `manual-open`. | Type the printed code or use a photo | Direct |
| 1 | `tools-open` | S 191 opens Scanner tools. | Open the scanner and present one item; current-language note | Direct |
| 2 | `product-handle` | S 20–40, 174 binds click, vertical drag and ArrowUp/ArrowDown to sheet snaps. | Read a result without filling in the unknowns | Partial: opening is described, not all gestures/keys. |
| 3 | `kitchen-handoff` | S 177–186 stages a selected live source reference and navigates to kitchen; this is not an inventory write. | Read a result without filling in the unknowns | Direct |
| 4 | (Overview tab) | S 189 selects `data-tab` and renders the readout. | Read a result without filling in the unknowns | Direct |
| 5 | (Ingredients tab) | S 189 selects `data-tab` and renders the readout. | Read a result without filling in the unknowns | Direct |
| 6 | (Nutrition tab) | S 189 selects `data-tab` and renders the readout. | Read a result without filling in the unknowns | Direct |
| 7 | (Source tab) | S 189 selects `data-tab` and renders the readout. | Read a result without filling in the unknowns | Direct |
| 8 | `data-expand` | S 192 renders the current readout in a dialog. | Read a result without filling in the unknowns | Direct |
| 9 | `detail-prev` | S 191 decreases the page index; rendering bounds it. | Read a result without filling in the unknowns | Direct |
| 10 | `detail-next` | S 191 increases the page index; rendering bounds it. | Read a result without filling in the unknowns | Direct |
| 11 | `undo` | S 188 removes the latest capture and handles the separate surrogate undo path. | Pause, finish or recover | Partial: real capture semantics are described, not surrogate undo. |
| 12 | `pause` | S 188 toggles pause; a pending lookup becomes unavailable; resuming attempts camera start. | Pause, finish or recover | Partial: pause/resume is described, not pending-lookup invalidation. |
| 13 | `finish` | S 188 stops capture and opens the session dialog. | Pause, finish or recover | Direct |
| 14 | `scanner-language` | L 120–147 binds `[data-ui-language]`; a changed choice persists preference and reloads with a URL locale. | Current-language note | Direct; complete Arabic coverage is not claimed. |
| 15 | `manual-open` | S 172 initializes the manual dialog and closes the session dialog. | Type the printed code or use a photo | Direct |
| 16 | `session-button` | S 187 renders and opens the session dialog. | Open the scanner and present one item; Pause, finish or recover | Direct |
| 17 | `theme` | S 193 toggles scanner light/dark preference; this is separate from language. | None explicit | Gap |
| 18 | `tools-close` | S 191 closes Scanner tools. | None explicit | Gap: navigation label exists, but no explicit help. |
| 19 | `close-data` | S 192 closes the expanded readout. | Read a result without filling in the unknowns | Partial: expansion is described, not this return action. |
| 20 | `options-handle` | S 31–37, 175 binds option-sheet snaps to click, drag and arrow keys. | Open the scanner and present one item | Partial: settings are described, not sheet gestures/keys. |
| 21 | `connection` | S 168 applies the selected connection on the Enter mode button; S 194 explains the separate surrogate lane. | Type the printed code or use a photo; Pause, finish or recover | Partial: retained-data limits are described, not private/surrogate selection. |
| 22 | `mode` | S 167 updates the mode description; S 168 applies the mode on the Enter mode button. | Pause, finish or recover | Direct for the live connection's no-inventory-action limits. |
| 23 | `saved-file` | S 170 verifies a selected file against `TRUSTED_PINS`, retaining the result only in memory. | None explicit | Gap: do not infer import eligibility or request a private file from this map. |
| 24 | `scanner-mode` | C 211–217 selects placement, camera direction and preview preferences; an active camera restarts. | Open the scanner and present one item | Direct |
| 25 | `scanner-camera` | C 97–102 enumerates lenses; C 218–221 applies selection and restarts an active camera. | Open the scanner and present one item | Direct |
| 26 | `scanner-mirror` | C 222 updates preview preferences. | Open the scanner and present one item | Direct |
| 27 | `scanner-rotate` | C 222 updates preview preferences. | Open the scanner and present one item | Direct |
| 28 | `scanner-enhance` | C 222 updates the decoding-enhancement preference. | Open the scanner and present one item | Direct; enhancement does not repair a blurred code. |
| 29 | `sound` | S 190 toggles read sound and attempts browser audio initialization. | Open the scanner and present one item | Direct |
| 30 | `camera-check` | S 195 reports browser/context/stream facts, not decoding success. | Pause, finish or recover | Direct |
| 31 | `scanner-torch` | C 223 toggles the exposed track torch constraint. | Open the scanner and present one item | Direct; available controls depend on the camera/browser. |
| 32 | `scanner-focus` | C 224 applies an exposed focus mode. | Open the scanner and present one item | Direct at the task level. |
| 33 | `scanner-focus-distance` | C 225–228 applies focus distance with manual focus. | Open the scanner and present one item | Direct at the task level. |
| 34 | `scanner-zoom` | C 225–228 applies the exposed zoom constraint. | Open the scanner and present one item | Direct at the task level. |
| 35 | `scanner-exposure` | C 225–228 applies exposed exposure compensation. | Open the scanner and present one item | Direct at the task level. |
| 36 | `enter-mode` | S 168 applies mode/connection and attempts camera start. | Open the scanner and present one item; Pause, finish or recover | Direct for the described live mode. |
| 37 | `close-mode` | S 168 closes options, resumes active/unpaused state and attempts camera start. | None explicit | Gap: Cancel is not equivalent to finishing or stopping capture. |
| 38 | `scanner-rearm` | C 229 rearms presentation of the next identical pack. | Open the scanner and present one item | Direct |
| 39 | `close-session` | S 187 closes the session dialog. | Pause, finish or recover | Partial: the session journey is described, not this return action. |
| 40 | `change-mode` | S 187 stops capture and opens the mode dialog. | Open the scanner and present one item; Pause, finish or recover | Direct |
| 41 | `scanner-photo` | C 230–250 reads one selected image with size and single-code checks; attempts allowed auto-resume afterward. | Type the printed code or use a photo | Direct |
| 42 | `barcode` | S 172 submits the original lexical value through the manual form. | Type the printed code or use a photo | Direct |
| 43 | `manual-namespace` | S 171 disables/reset representation hints for USDA-FDC; S 172 checks supported namespaces. | Type the printed code or use a photo | Direct |
| 44 | `manual-representation` | S 172 supplies an optional representation hint; a hint is rejected for USDA-FDC. | Type the printed code or use a photo | Direct |
| 45 | (Confirm identifier submit) | S 172 handles the parent manual form's submit event. | Type the printed code or use a photo | Direct |
| 46 | `manual-cancel` | S 172 closes the manual dialog without invoking capture. | Type the printed code or use a photo | Direct |
| 47 | `close-matches` | S 187 closes the source-match dialog. | Read a result without filling in the unknowns | Partial: selecting source details is described, not this return action. |

## Boundaries and follow-through

All 48 nodes have a row; this is enumeration coverage, not 48 successful user
journeys. HTML attributes alone do not establish runtime visibility, effective
disabled state, keyboard reachability, accessible names or translation quality.
Camera capabilities and dialog state make some controls conditional.

This table excludes dynamically created source-choice/continuation/session
buttons, `summary` elements, links, custom controls, main-app and data-workspace
controls, retailer-extension controls and any authenticated/admin surfaces.
Those exclusions remain inventory work; they are not proof of absent features.
It also does not qualify source data, live lookups, inventory actions, privacy,
rights, production deployment, help search or representative device/AT behavior.

Use the **Partial** and **Gap** rows to select concrete content corrections,
then check the affected source and guide together. Do not expand a help passage
from a label alone or offer private import data without its existing authority.
The OffMenu source-change owner updates this crosswalk and affected user guide
when these controls or bindings change. The
[help/search verification plan](help-search-verification-plan.md) remains the
separate verification scope; this map is not its execution receipt.
