# Offline Better Auth runtime seam

Base: [72a8a74919773238e402b2a6f5a089bf8a4cefa2](https://github.com/maldous/offmenu/commit/72a8a74919773238e402b2a6f5a089bf8a4cefa2).

## Delivered scope

`apps/web/server/auth-runtime.mjs` is an **unmounted** adapter. The current dispatcher does not import it. No live authentication switch, environment setting, credential, provider, schema application, deployment or browser change is included.

Missing `OFFMENU_AUTH_MODE` or exact `netlify` returns the supplied legacy verifier unchanged and declines all route handling. Exact `better-auth` constructs the existing reviewed factory with deployment-owned options. Other values fail closed. Never derive mode, factory options or verifier from the request or mutable administrative settings.

A future dispatcher can use `handleAuthRequest` before the existing Netlify identity proxy and use `verifiedUser` for protected routes. In explicit Better Auth mode, only `/api/auth` and its children are delegated; similarly named paths are ignored. Netlify identity routes return 410 to prevent mixed identity modes. Auth responses preserve body, status, redirects and separate Set-Cookie headers while adding no-store/nosniff. Thrown auth-handler failures return generic 503; existing HTTP error responses retain their status. Principal lookup failures propagate to the caller. Neither path attempts legacy authentication after a new-mode failure. Configuration validation errors remain exceptions requiring the outer dispatcher’s normal safe error handling.

`workerRuntimeBuildOptions` applies `workerd` export conditions and external Node builtins only to the final Worker bundle. Browser bundles remain unchanged. This selects Better Auth's AsyncLocalStorage implementation for workerd rather than its pure fallback. The fixture uses the same production minification: an unminified dependency includes an unreachable dynamic import that Miniflare's automatic module scanner rejects. Node compatibility remains an explicit deployment prerequisite; no compatibility flag is enabled by this patch.

## Evidence

14 focused tests passed under Node 24.19.0 with native Miniflare/workerd D1: the 9 foundation/principal tests and 5 new seam/build tests. The added native tests exercise origin rejection, verification redirects, secure cookie headers, sign-in, fresh role removal, tampering, logout, exact route boundaries, missing-schema generic outage, and propagated principal failure. Default-mode tests require no D1 or secret and preserve the exact supplied verifier. Foundation regression tests retain opaque imported IDs, private state and AES-GCM AAD bindings; they use synthetic data, not a production import.

The current handler and its real dependency graph bundle successfully with the proposed Worker options (318025 bytes using synthetic empty assets). This is not a full app build. Installed dependencies are the foundation's existing installation, not a new clean install. Source CI and a complete asset build remain integration checks.

The unchanged catalogue extractor ran against all 91 verified current inputs plus this module; its check passes at 2811 messages, 376 Arabic translations and 2435 missing. Six newly inventoried error messages are included in the generated catalogue/coverage files. Existing translations are unchanged. Missing translations are reported honestly rather than fabricated or suppressed.

## Required before any cutover

- Mount the adapter deliberately, review every identity consumer and change the browser authentication integration. Existing Netlify UI cannot use this seam unchanged.
- Obtain explicit activation approval and provision origin, independent secret, native D1, session policy and delivery providers through approved secret channels. Apply the additive auth schema under the migration/backup plan.
- Import exact legacy IDs and trusted roles, including disabled-account handling. Verify original private-state keys and provider-vault AAD against staging imports. Do not normalize subjects or fall back by matching email.
- Treat principal lookup as read-only: it disables hidden session refresh. Deliver renewal via explicit Better Auth routes and preserve their Set-Cookie headers at the eventual dispatcher/browser boundary.
- Migrate delegated administrative proofs. Current `apps/web/server/admin-mcp.mjs` still encrypts a legacy bearer and checks it through Netlify on each fresh authorization. This module does not make those proofs compatible. Use an explicitly versioned proof tied to a trusted verified session identifier and original owner, check live session expiry/revocation and fresh roles, retain encryption/expiry/audience/PKCE restrictions, and provide bounded legacy-proof handling or reconsent. Never reinterpret old bearer contents as a new session ID or accept a caller-supplied owner. Normal integration grants retain their existing logout contract.
- Complete native staging acceptance, original-account continuity, provider/password policy, recovery and rollback checks from the approved migration plan. No activation is implied by source integration.

Source references: [factory](https://github.com/maldous/offmenu/blob/72a8a74919773238e402b2a6f5a089bf8a4cefa2/cloud/auth.mjs), [principal](https://github.com/maldous/offmenu/blob/72a8a74919773238e402b2a6f5a089bf8a4cefa2/cloud/auth-principal.mjs), [current admin proofs](https://github.com/maldous/offmenu/blob/72a8a74919773238e402b2a6f5a089bf8a4cefa2/cloud/admin-mcp.mjs).
