# Locale preference verification preparation

This UIF-191 plan covers existing English/Arabic preference selection and
fallback at source revision `d0d5257afda171956d2f5855202aeda9bd8564b7`.
All cases below are **planned, not executed**. Source inspection is not evidence
that browser navigation preserves forms, accounts remain isolated, translations
are linguistically complete, or first-render language is correct in deployment.
The agreed locale/surface inventory and completed translations/RTL work remain
requirements for final UIF-191 acceptance.

This document neither selects additional languages nor repeats UIF-190's
cooking/serving direction matrix or the help-search ranking plan. It requires
no new translation provider, GeoIP service, account or browser operation.

## Source contract to retain

[`locale-negotiation.js`](../apps/web/src/locale-negotiation.js) supports `en`
and `ar`, including supported language subtags. `negotiateLocale` considers
URL, device, explicit cookie, profile, provider, accepted languages, country
hint and configured/default fallback in that order. Invalid/unsupported values
fall through; they do not register another language. Geography is a coarse
hint, not evidence of language, nationality or precise location.

[`i18n.js`](../apps/web/src/i18n.js) supplies `browserLocaleDecision`,
`setupLanguage` and `applyAccountLanguage`. It reads `uiLanguage` from the URL,
the device's `offmenu-ui-language-v1` storage key, the explicit language cookie,
account-hint cookie, browser preferences and bootstrap hints. Browser language
and inferred region choices are not automatically saved as explicit preferences.
The selected language control attempts device storage and cookie writes, calls
the profile preference handler and navigates with the URL preference when the
language changes. Guarded failures here do not prove that all app storage use
works when storage is blocked.

[`app.js`](../apps/web/src/app.js) calls `setupLanguage` during module startup.
Its preference handler writes the current profile's `uiLanguage`. `signedIn`
calls `switchAccount` then `loadProfile`; the latter applies account language
after authentication resolves. `switchAccount` changes account/demo storage
namespaces and resets several views. These source relationships identify what
to verify, not a completed identity or persistence qualification.

## Bounded case matrix

Use synthetic preference/profile values in a qualified isolated fixture when
execution is separately selected. Preserve the exact inputs and observed
decision source as well as the selected locale; matching output language can
hide a wrong precedence decision.

| Case | Inputs / transition | Source-backed expectation and evidence still needed |
| --- | --- | --- |
| L1 · explicit precedence | URL `uiLanguage=ar`, saved device `en`, conflicting cookie/profile/provider hints | URL wins. Then remove each higher-priority input in turn to check device, cookie, profile and provider precedence. Record decision source; do not change an actual user's preferences. |
| L2 · unsupported and multiple preferences | Unsupported URL/device tags; browser preferences such as `fr`, `ar-EG`, `en`; malformed tags | Invalid/unsupported entries fall through; supported subtags resolve to their base. The first supported accepted language wins after higher priorities. Document the supplied ordering rather than assuming every caller parses weighted HTTP headers. |
| L3 · geography/default limits | No supported higher-priority input; Arabic-country hint, missing/unknown country, configured fallback, explicit exclusions | Country can select Arabic only when it is not excluded in this fallback branch. Configured fallback must be supported and not excluded; otherwise choose an unexcluded supported locale, finally English if none remains. Exclusions do not override an explicit higher-priority choice in this function. No real GeoIP request is needed. |
| L4 · blocked storage and cookies | Storage read/write throws; cookie access/write unavailable; change language through an exposed selector | The locale helpers guard their storage operations. The selector retains a URL preference when navigating, and a profile-handler exception must not block its own language choice. Separately record whether the full app actually loads: other profile/storage reads can still fail. Do not claim offline or universal storage-denial support. |
| L5 · account A → B → logout | Distinct synthetic profile/provider hints, no explicit override; then repeat with a device/URL override | `applyAccountLanguage` replaces or clears the account-hint cookie and removes prior profile/provider bootstrap hints before re-evaluation. A changed result requests reload; demo mode skips this helper. Verify no previous-account hint survives, while explicit device/URL choice can legitimately remain. This is distinct from proving that all private app data is isolated. |
| L6 · reload and unfinished forms | Choose another language while a safe unsaved fixture form or staged checkout exists | `setupLanguage` navigates when the choice changes; source comments about separately persisted data do not prove preservation of every form. Record precisely what survives, what is lost and whether a warning is provided. Lost user input is a gap, not an assumed supported behavior. |
| L7 · browser/OS change and first render | Change browser language ordering between visits; with/without an explicit preference; compare response/bootstrap and post-JavaScript locale | Explicit preferences retain priority. No reactive OS-change listener or no-flash guarantee is established by these selected functions. Capture the actual first rendered language, later language/direction and any visible switch in an authorized browser fixture. OS theme behavior is outside this locale-only selection. |
| L8 · missing keys/plural/interpolation drift | An existing translated key, a deliberately missing synthetic key, placeholder values and plural categories at the pinned catalogs | English keys are the fallback. `t` selects a plural category from finite `count`, then `other`, then source text; placeholders remain plain text and numeric values use locale formatting. Record missing translations and mismatched placeholders rather than counting fallback text as translated. Static text nodes receive English fallback language tagging via `translateUI`; localized attributes require their own actual accessibility observation. |

Before expanding L8 into a coverage count, bind exact catalog/source editions
and the agreed user-facing-key classification. Reuse the existing source audit;
do not count shader/SQL extraction noise as untranslated interface text or
recreate the entire inventory. Infrastructure checks and pseudolocalization
cannot replace independent Arabic linguistic review.

## Later execution evidence

For each case retain source/tree, selected locale, all precedence inputs,
decision source, fixture authority, browser/version, storage/network conditions,
actual result and residual gap. Use no credentials or real household data.
Browser observations must distinguish physical devices from emulation across
WEB, TABLET, FOLDABLE and MOBILE. Record viewport/zoom, accessible selector name,
keyboard focus, selected state, `html lang/dir`, relevant screen-reader/version
and observed announcement. Record untested equipment and reduced-motion limits;
do not infer WCAG certification from markup or a source-only plan.

Account switch/reload and form-retention results need actual authorized fixtures.
Missing or inconsistent bootstrap/network responses must be recorded separately
from missing translation keys. No provider activation or precise-location
permission is required by this preparation. Failures that need product changes
return to the existing source owner; this plan authorizes none.

## Drift and update responsibilities

These are role requirements, not invented named operational appointments:

- The locale/source owner identifies changes to precedence, storage/cookie keys,
  supported locales, callers and navigation, and marks affected cases stale.
- The account/profile owner supplies the actual selected identity/fixture boundary
  for account-switch checks; a null assignee is not evidence of free custody.
- The translation reviewer owns linguistic accuracy, terminology and plural/
  placeholder review for the exact approved locale/surface list.
- The documentation maintainer keeps expectations aligned with changed source;
  the independent verifier records measured results and untested gaps at exact
  editions. Name the actual accepting owners in the existing issue when assigned.

On a source/catalog or caller change, compare the affected paths and rebind only
affected cases before reusing their evidence. Keep original results at their
original pins. Review changed/missing keys, placeholder sets and plural branches;
do not silently broaden the locale list or relabel English fallback as complete
Arabic. This is not a new universal release gate or another inventory tracker.

## Exact source pins

| Path | SHA-256 |
| --- | --- |
| `apps/web/src/i18n.js` | `4ea82cfbbd6421bc2b390f09ddff733f06c6493933b37533edbf0a6e8e911fb5` |
| `apps/web/src/locale-negotiation.js` | `f3d7a7d6cb03db4d31ab8caa967f4f172fdf6ff2990c9b42ec6cd7af36604fdb` |
| `apps/web/src/app.js` | `ee6543a3c1e0472237dadff1ae4e5590bfd8e0d173f8a1e782adfcba71a1d237` |

These are inspected source pins, not execution results. Final localization,
cross-profile, accessibility and device acceptance remains unqualified.
