# Google sign-in correction for current OffMenu auth page

Candidate only. No production write, provider call, new client/grant, credential read or security configuration change occurred. The source packet is current v199; reconcile newer auth assets before any splice. The full Worker was not supplied locally.

## Concrete defect and correction

Public Identity discovery already has Google enabled. The actual Worker initializer hardcodes oauthCallbackReady:false, causing /api/auth-page/config to return oauthAvailable:false. auth.js hides its entire provider section under that gate. Its original enabled-provider renderer also contains text alone, without requested Google branding.

candidate/auth.js preserves the official bundled Identity SDK bytes before the controller boundary (26,167 bytes), its loginExternalUrl route and existing scopes. It substitutes source/auth-controller.mjs at the original controller boundary and adds the official Google button image only for Google. The official whole-image asset is embedded locally in the existing JS to avoid another runtime request. candidate/auth.html supplies scoped focus/button styling. The image is 354x80 rendered at 177x40 without stretching; its text is supplied in the approved image rather than approximated typography. Accessible name and visible keyboard focus are provided. Other provider labels and handlers are preserved.

The controller has a 15-second total budget per operation (including all callback/session steps). A timeout refuses acceptance/navigation; it does not cancel SDK-internal work. No late SDK resolution changes controller state or navigates. Callback acceptance requires OAuth callback user == recovered current user == authenticated server session user, with matching mode and same configuration origin. OAuth error fragments and unqualified runtime gates are refused. Every scanner/kitchen continuation re-verifies the session and uses the original fixed local destinations. Signup/email/signout and separate provider-consent controls remain gated as before. auth-return-bridge now routes provider-error fragments as well as the original supported token fragments to /auth.html without moving them into query strings or requests.

## Sole integrator pickup

1. Review candidate assets and auth-google.patch against exact baseline assets. Retain rollback snapshots. Do not replace a newer whole Worker with this v199 packet.
2. Apply the three asset updates using existing asset delivery. Read WORKER-GATE-HOOK.json: change only the exact existing real-Netlify auth-page initializer oauthCallbackReady:!1 to !0, after verifying one match in the actual current Worker. The full Worker diff/readback is owned by the integrator. Keep verifiedUser CA, all session/tenant checks, proxy/authorize routes, consent scopes and private bindings unchanged.
3. Verify actual deployed assets match the three candidate hashes; public settings still expose Google=true; auth-page/config returns real, synthetic=false, oauthAvailable=true on the actual origin. Preserve unrelated version/corpus/barcode changes. No source/identity promotion or credentials/configuration activation is needed here: Google is already enabled.
4. Served rendering must verify the official image, keyboard focus and existing CSP permits these scoped inline styles/data image. Do not relax CSP to make a button appear; if the existing policy disallows them, return that exact conflict for an asset-delivery-only correction.
5. Read back the actual existing authorize target and return bridge. Route tests show the unchanged SDK computes same-origin /.netlify/identity/authorize?provider=google with no added scope. They do not assert the upstream Google client/consent configuration is valid. Matt's actual Google journey and successful server-verified scanner/kitchen continuation remain required acceptance. No real login was performed locally.

Rollback: restore the exact three baseline asset snapshots and the previous initializer using current-Worker-local edits, preserving all later unrelated changes. No credentials/storage migration is part of this patch.

## Evidence

12 focused deterministic tests pass (focused-tests.log). These include full supplied bundle discovery/render/authorize behavior and an actual bundled SDK callback using synthetic token/user/session responses, plus mismatch/unauthenticated/wrong-mode checks, bounded stalled callback/provider work, fixed return destinations, provider denial, and email/signup/signout gates. No external requests are allowed by the test harness. Initial expanded callback fixture needed a real cookie-jar simulation and a syntactically valid explicitly synthetic token; final suite passes. No real account/token was accessed. CANDIDATE-RECEIPT.json holds exact source, test, patch and baseline pins.

Google primary reference checked 2026-10-29:
https://developers.google.com/identity/branding-guidelines
Official supplied image:
https://developers.google.com/static/identity/images/branding_guideline_sample_lt_sq_lg.png

Reproduction uses existing Node24.16.0 and esbuild0.25.12 (no install): node build-auth.mjs; node --test tests/auth-google.test.mjs. build-auth.mjs pins the SDK preimage and esbuild version, reconstructs the minimal controller/renderer seam, and checks final JS syntax. Its local module path points to the existing Foo esbuild installation; another approved executor must select its own already-pinned module path. This lane does not build/redeploy the unrelated main-app v198 candidate.
