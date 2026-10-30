# Offline Better Auth runtime seam

Historical slice base: [72a8a74919773238e402b2a6f5a089bf8a4cefa2](https://github.com/maldous/offmenu/commit/72a8a74919773238e402b2a6f5a089bf8a4cefa2).

## Current source scope

At `9e007c742dad43fa2c35caecf7e97c46ec4c30f4`, [the dispatcher](../apps/web/server/handler.mjs) imports `createOffMenuAuthRuntime`, calls `handleAuthRequest` before the legacy identity proxy and catch-all, and supplies the selected `verifiedUser` to protected routes. The adapter was unmounted in the historical slice below; mounting is now present in source. This does not establish Better Auth selection or live acceptance. This documentation correction changes no authentication configuration, credentials, providers, schema, deployment or browser behavior.

Missing `OFFMENU_AUTH_MODE` or exact `netlify` returns the supplied legacy verifier unchanged and declines all route handling. Exact `better-auth` constructs the existing reviewed factory with deployment-owned options. Unknown modes and incomplete Better Auth configuration fail closed through the dispatcher’s generic 503 handling, without legacy fallback. The default handler supplies no configured factory options; setting the mode alone is insufficient. Never derive mode, factory options or verifier from the request or mutable administrative settings.

In explicit Better Auth mode, only `/api/auth` and its children are delegated; similarly named paths are ignored. Netlify identity routes return 410 to prevent mixed identity modes. Auth responses preserve body, status, redirects and separate Set-Cookie headers while adding no-store/nosniff. Thrown auth-handler failures return generic 503; existing HTTP error responses retain their status. Principal lookup failures propagate to the caller. Neither path attempts legacy authentication after a new-mode failure. Configuration validation errors remain exceptions handled by the outer dispatcher’s generic 503 response.

`workerRuntimeBuildOptions` applies `workerd` export conditions and external Node builtins only to the final Worker bundle. Browser bundles remain unchanged. This selects Better Auth's AsyncLocalStorage implementation for workerd rather than its pure fallback. The fixture uses the same production minification: an unminified dependency includes an unreachable dynamic import that Miniflare's automatic module scanner rejects. Node compatibility remains an explicit deployment prerequisite; no compatibility flag is enabled by this patch.

The browser selection is separate: [app.js](../apps/web/src/app.js) calls [createOffMenuIdentityClient](../apps/web/src/offmenu-identity-client.js) with only the Netlify client, retaining its default `netlify` mode. The optional Better Auth client supports email login/logout and session lookup/refresh using server-owned cookies, with no browser token export. Signup, recovery, invite, profile/password changes and provider flows are intentionally unavailable there; the factory also disables account linking. These limits do not establish a defect in the current Netlify Google button/callback path.

Identity boundaries remain exact: [the principal adapter](../apps/web/server/auth-principal.mjs) preserves opaque `user.id` and requires `session.userId === user.id`; the dispatcher keys private `user_state` by that ID with revision CAS. The browser keeps private local-storage keys under the exact ID, separate from guest/demo state, rotates `requestIdentity` on account switches, and uses [sessionFetch](../apps/web/src/session-fetch.js) guards across refresh, current-user lookup, response headers, delayed bodies and clones. [Provider vault storage](../apps/web/server/provider-data.mjs) retains `user_id` ownership and AES-GCM AAD `user.id + '|' + source.id`. Source inspection does not prove an original-account migration.

## Historical slice evidence

The following counts and build/catalogue results describe the original offline slice only. They were not rerun for this correction and are not current production acceptance.

14 focused tests passed under Node 24.19.0 with native Miniflare/workerd D1: the 9 foundation/principal tests and 5 new seam/build tests. The added native tests exercise origin rejection, verification redirects, secure cookie headers, sign-in, fresh role removal, tampering, logout, exact route boundaries, missing-schema generic outage, and propagated principal failure. Default-mode tests require no D1 or secret and preserve the exact supplied verifier. Foundation regression tests retain opaque imported IDs, private state and AES-GCM AAD bindings; they use synthetic data, not a production import.

The then-current handler and its real dependency graph bundled successfully with the proposed Worker options (318025 bytes using synthetic empty assets). This is not a full app build. Installed dependencies are the foundation's existing installation, not a new clean install. Source CI and a complete asset build remain integration checks.

The unchanged catalogue extractor ran against all 91 inputs verified for that slice plus this module; its check passes at 2811 messages, 376 Arabic translations and 2435 missing. Six newly inventoried error messages are included in the generated catalogue/coverage files. Existing translations are unchanged. Missing translations are reported honestly rather than fabricated or suppressed.

The retained historical SAME4 validator `65df4acd070871d8e89e071fe45dd0373af87e5a` remains scoped preflight only, with no adoption or authentication conclusion. Its original reviewer receipt was unavailable in the inspected qualification packet.

## Required before any cutover

- Review every identity consumer and qualify deployment-owned server options and browser selection together. The server mount exists; the current Netlify browser selection does not select Better Auth.
- Obtain explicit activation approval and provision origin, independent secret, native D1, session policy and delivery providers through approved secret channels. Apply the additive auth schema under the migration/backup plan. Qualify the auth realm, separate DEV configuration, and proof that production rejects DEV identity.
- Import exact legacy IDs and trusted roles, including disabled-account handling. Verify original private-state keys and provider-vault AAD against staging imports. Do not normalize subjects or fall back by matching email.
- Treat principal lookup as read-only: it disables hidden session refresh. Deliver renewal via explicit Better Auth routes and preserve their Set-Cookie headers at the mounted dispatcher and selected browser boundary.
- Resolve delegated administrative proof compatibility before cutover. Current [admin-mcp.mjs](../apps/web/server/admin-mcp.mjs) still seals a legacy JWT and performs fresh bearer verification, including owner and administrator-role checks. A Better Auth cookie session is not interchangeable with that proof; compatibility remains unresolved. This correction designs no replacement proof or migration. Normal integration grants retain their existing logout contract.
- Complete native staging acceptance, original-account continuity, provider/password policy, pending invite, recovery and rollback checks from the approved migration plan. No activation is implied by source integration.

Historical source references: [factory](https://github.com/maldous/offmenu/blob/72a8a74919773238e402b2a6f5a089bf8a4cefa2/cloud/auth.mjs), [principal](https://github.com/maldous/offmenu/blob/72a8a74919773238e402b2a6f5a089bf8a4cefa2/cloud/auth-principal.mjs), [then-current admin proofs](https://github.com/maldous/offmenu/blob/72a8a74919773238e402b2a6f5a089bf8a4cefa2/cloud/admin-mcp.mjs).

Current source contracts: [runtime](../apps/web/server/auth-runtime.mjs), [factory](../apps/web/server/auth.mjs), [dispatcher test source](../tests/edge/handler-auth-dispatch.test.mjs), and [client test source](../tests/web/offmenu-identity-client.test.mjs). Test sources were read offline, not executed.
