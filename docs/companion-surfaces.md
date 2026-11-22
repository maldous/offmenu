# OffMenu shortcuts and companion surfaces

Open **Plan** for upcoming meals and **Shop** for the current week’s list. Installed web apps can advertise **Meal plan** and **Shopping list** when their launcher reads manifest shortcuts. The entries contain generic labels and destinations. They use the same kitchen entry and access flow as the browser. You can also bookmark `/?view=plan` or `/?view=shopping`. The ordinary start destination is unchanged. In the kitchen, use the browser’s access-key modifier with **P** for Plan or **S** for Shop, or Tab to either button and press Enter.

In a shared recipe’s review dialog, open **Recipe actions** with Enter or Space. Choose **Share source link** when the browser offers sharing, or **Download source recipe as JSON-LD**. The disclosure leaves the recipe, its edits and the confirmation checkbox in place. Escape inside the expanded actions returns focus to the summary. The original source link also remains available. In Shop, **Copy shopping list** requires a separate activation. Declining a share leaves the list available.

## Host support matrix

“Web” below describes the implemented browser path. Launcher presentation, physical-device privacy and assistive technology still require checks on each intended host.

| Host | Available in this edition | Host work and fallback |
| --- | --- | --- |
| Apple phone and tablet | Browser Plan, Shop and recipe actions. Sharing depends on the browser offering Web Share. | WidgetKit and App Intents adapters are required for a selected-list widget, interactive check-off, device recipe search and Shortcuts/Siri. An incoming share/open-in extension, verified recipe links and a user-confirmed Reminders writer need host implementation. Use the in-app list, source link or export. |
| Apple Watch | Handset web paths above. | A paired watch app is required for next meal, selected-list filter/edit/check-off, handoff and reconnect. Keep edits on the handset until device replay and revocation checks pass. |
| Android phone and tablet | Web meal-plan and shopping launcher entries where supported, in-app checkbox and browser share/download. | A widget/action receiver, verified app links, incoming share target and device search adapter need implementation. Use the web destination when the launcher omits shortcuts. |
| Wear OS | Handset web paths above. | A paired app/tile and handset receiver are required for glance, list operations and handoff. No watch mutation route is enabled. |
| Desktop browsers and installed web apps | Plan/Shop buttons, access keys, recipe disclosure and exports. The Chromium retailer extension previews structured products on the selected tab. | Launcher shortcut availability depends on the host. The retailer extension has no recipe-import action. Use the recipe source link or file export. OS indexing, native mail composition, default link registration and browser-plugin recipe entry require separate adapters/use cases. |
| Locked phone or watch | Launcher shortcuts contain no personalized title, nutrition, household ID or list contents. | Live timer/step activity, selected-list widget previews, notification actions and watch complications need host implementations and locked-device observation. Default to a generic open action. Require current unlock and scope before showing details or writing. |

### Controls and scope

| Area | Available path | Outstanding |
| --- | --- | --- |
| Display and navigation | Scanner theme, kitchen large type and quiet mode, standard buttons and checkboxes, and a recipe action disclosure. | Qualify adaptive rail and panes, visible Back and focus through navigation, non-drag parity for each action, typeface and compact-column controls, and a persistent user-selected start destination. |
| Cooking and planning | Meal slot and unit selection, foreground cooking steps/timer, user-initiated keep-awake with browser support, and speech feedback controls. | Custom meal-type management, OS timer/step activity and background notification behavior need separate verification. |
| Browser and sharing | Share the selected source URL or uncollected shopping text. Clipboard write needs its own button. Downloads work without either host API. Document email uses the existing verified-address confirmation flow. | Custom browser start page, link-opening policy, private/cache controls, native mail/open-in handlers and desktop rendering/spellcheck recovery need host-specific work. |
| Permissions | Share, copy and keep-awake start with a user action. Permission failure during export leaves the download path available. | Device permissions, revocation while offline, screen-reader announcements, reconnect and cancellation across app/device boundaries need real-host tests. |

### Voice intent manifest

| Host | Enabled intents | Proposed scoped intents | Link, permission and unlink behavior required before enabling |
| --- | --- | --- | --- |
| Apple Siri / Shortcuts | None | Find recipe, read current step, next/previous step, capture shopping item, open on handset | Enable per device for a selected account and kitchen. Permit reading selected recipes, navigating the current cook session, and proposing an addition to a selected list separately. Confirm a write on an unlocked device. Unlink clears donated items and invalidates pending actions. |
| Android assistant | None | Same five action families when supported by its host adapter | Link in settings to a named account/device. Show which list or session each action addresses. Recheck grants at execution and discard stale queued actions on unlink. |
| Desktop, browsers and unpaired wearables | None | Explicit handset handoff only where a receiver can establish scope | Keep account linking off until a scoped receiver exists. Use in-app recipe search, written steps and manual shopping capture. |

A native wearable write should carry the intended checked state, stable list/item and operation IDs, account/device scope and the revision used. After reconnect, acknowledge an already applied operation, recheck permissions, and surface a stale or conflicting edit for review. Qualification needs a delayed duplicate, an offline edit, an intervening handset edit and unlink before delivery. A refusal or decline must leave the confirmed list and recipe untouched. These are acceptance cases for future host adapters.
