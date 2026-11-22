# Account and authentication state machines

Status: **bounded source investigation**, not a deployment, security audit or
runtime qualification. This is one semantic slice of
[UIF-252](https://linear.app/maldous/issue/UIF-252), not completion of the
[state-machine inventory](README.md).

## Source boundary

This document selects accepted source
`51ad2b27a226f097dcaa9a27db5fade33d9ef4dd`, tree
`6212683d485706ed894674348c64599e8c990289`. File and line ranges below describe
that edition. The inventory's earlier `436f16c2` coverage ledger remains its own
frozen edition; it is not silently rebased or extended by this document.

The complete implementation slice is
[auth-runtime.mjs](../../apps/web/server/auth-runtime.mjs),
[auth.mjs](../../apps/web/server/auth.mjs),
[auth-principal.mjs](../../apps/web/server/auth-principal.mjs) and
[auth-schema.sql](../../apps/web/server/auth-schema.sql). The state names below
summarize predicates and boundaries, not new enums or proposed implementation.
Focused test sources were read, **not executed**. No accounts, authentication
requests, databases, secrets, sessions or providers were accessed or changed.

Browser identity-client behavior, legacy verifier internals, the dispatcher's
complete implementation, private state persistence and synchronization are not
reconstructed here. Dispatcher assertions are identified separately as test
evidence. This does not amend the separate session-state/D1 or sync/persistence
slices, shared index or coverage ledger.

## OM-AUTH-MODE-001: deployment selection and request dispatch

Evidence: `auth-runtime.mjs:4-50`, `auth.mjs:6-42`.

Selection is a deployment configuration decision made when the runtime is
constructed. It is not an automatic migration or a per-request fallback.

| State/event | Guard and transition | Effect or failure boundary |
| --- | --- | --- |
| Missing mode or exact `netlify` | `OFFMENU_AUTH_MODE` is undefined or `netlify`. | Requires a callable `legacyVerifiedUser`; returns that exact verifier. Its auth-route handler returns `null`, leaving routing to its caller. This branch does not construct Better Auth or require its D1/secret configuration. |
| Exact `better-auth` | Constructs the explicit factory with deployment-owned options. | Returns a principal adapter and auth-route handler. A supplied legacy verifier is not retained as a recovery path. |
| Any other mode | No case folding, trimming or `auto` interpretation. | Throws `TypeError`; it does not silently choose either identity system. |
| Incomplete Better Auth configuration | Native D1-style `prepare` and `batch` functions; HTTPS origin without credentials, path, query or fragment; separately provisioned secret of at least 32 characters; explicit valid session policy. | Factory validation throws before construction. The secret length guard is not an entropy assessment. No schema, secret or provider is provisioned. |
| Legacy identity route in Better Auth mode | Path equals `/.netlify/identity` or is beneath that exact slash-delimited prefix. | Returns 410 with `no-store` and `nosniff`; no legacy proxy request is made by this runtime. |
| Unrelated route | Path is outside exact `/api/auth` and its slash-delimited descendants. | Returns `null`, not a fabricated auth response. `/api/authish` and `/.netlify/identityish` are outside these prefixes. |
| Auth handler returns a response | Calls `auth.handler(request)`. | Clones the response without flattening cookie headers or rewriting redirects, then sets `no-store` and `nosniff`. |
| Auth handler throws | Exception from the delegated handler. | Returns generic authentication-unavailable 503 with those headers. It never retries Netlify. |

The runtime does not catch `verifiedUser` lookup errors. That separate failure
propagates to its caller, rather than becoming a signed-out principal. The read
dispatcher tests assert a generic 503 at the mounted application boundary, but
this slice does not independently trace every dispatcher callsite.

## OM-AUTH-ACCOUNT-001: configured account and session lifecycle

Evidence: `auth.mjs:20-95`, `auth-schema.sql:1-8`; the lifecycle assertions in
`tests/edge/better-auth.test.mjs:87-195` and
`tests/edge/auth-runtime.test.mjs:49-95`.

The factory configures Better Auth; it does not itself implement that library's
account endpoints. Distinguish configured policy, assertions in the selected
offline fixtures and any unverified deployed behavior.

| State/event | Declared guard or selected fixture assertion | Boundary |
| --- | --- | --- |
| Email authentication disabled | Email options omitted, or explicit `enabled:false`. | Email/password authentication and signup are disabled. Social providers are empty; this slice does not activate Google registration or consent. |
| Enable email authentication | Explicit boolean setting, verification/reset delivery callbacks and boolean signup policy are required. | `allowSignUp:false` disables signup without disabling all email sign-in. Delivery callbacks are supplied by the caller, not created here. |
| Signup to unverified account | When explicitly enabled, verification is required before sign-in. | Fixture assertions show signup without a session cookie and refusal of sign-in before verification. These are read assertions, not a new run or evidence of real mail delivery. |
| Verification | Configured to send on signup; automatic sign-in after verification is false. | Fixtures follow a verification redirect and then sign in separately. Production link delivery and redirect registration are not established. |
| Sign-in to valid session | Library validation succeeds under configured origin and email policy. | Factory declares secure, HttpOnly, SameSite=Lax, root-path cookies with prefix `offmenu-auth`; cross-subdomain cookies are disabled. Fixtures assert a host-only secure session cookie. |
| Session expiry | `expiresIn` must be a positive safe integer; `updateAge` must be a nonnegative safe integer smaller than it. | No default durations are selected here. The principal adapter disables refresh on its lookup; this is not a claim that every library endpoint never renews sessions. Fixtures explicitly expire a session and expect a null principal. |
| Sign-out | Successful library sign-out. | Fixtures assert cookie removal and subsequent loss of the principal. Browser handling and all distributed clients remain outside this slice. |
| Password reset requested | Caller supplied reset delivery hook and email authentication is enabled. | Fixtures assert equivalent successful response bodies for known/unknown addresses and delivery only for the known fixture account. No production anti-enumeration audit is claimed. |
| Reset consumed | Library accepts a reset token. | `revokeSessionsOnPasswordReset:true`; fixtures assert old-session revocation and refusal of token reuse. This is not an independently implemented retry or recovery worker. |
| Schema absent or database lookup fails | Factory construction does not apply the DDL. | A configured binding is not proof of migrated schema. Runtime handler errors become 503; principal lookup errors propagate separately. No legacy fallback is introduced. |

The declared schema contains five auth tables: `auth_user`, `auth_account`,
`auth_session`, `auth_verification` and `auth_rate_limit`, plus three indexes.
Account and session rows reference user identity with declared delete cascades;
session tokens and user emails have unique constraints. `IF NOT EXISTS` supports
repeat application of these declarations, not arbitrary schema upgrades or
proof of live migration. The source does not apply this schema to `user_state`.

Database-backed rate limiting and OAuth-token encryption are configured. This
does not establish deployed rate thresholds, storage encryption for every auth
column, foreign-key enforcement in a particular database, or a complete abuse
and recovery policy. Change-email, delete-user and account-linking features are
disabled by this factory; their presence in a library is not activation here.

## OM-AUTH-PRINCIPAL-001: verified session to reduced principal

Evidence: `auth-principal.mjs:1-31`; read assertions in
`tests/web/auth-principal.test.mjs:13-62`.

| State/event | Guard and transition | Effect or failure boundary |
| --- | --- | --- |
| Lookup pending | `auth.api.getSession` receives the request headers with `disableCookieCache:true` and `disableRefresh:true`. | Uses the server verifier. No bearer bridge or caller-supplied user ID is added by this adapter. |
| Missing, inconsistent or unusable identity | No result; session owner differs from user ID; or ID is not a nonblank string shorter than 200 characters. | Returns `null`. Whitespace is checked for emptiness, but accepted opaque IDs are returned exactly, not trimmed, lowercased or reassigned. |
| Verified session and admissible subject | Matching owner plus admissible user ID. | Returns a frozen reduced principal containing exact ID, string-or-null name/email, strict boolean verification flag and frozen role metadata. Password/session-token fields are not copied into this principal. This does not audit every delegated auth endpoint's response body. |
| Trusted role storage valid | `appRoles` parses as an array consisting entirely of strings. | Deduplicates that array. The factory marks this additional field `input:false`; the adapter does not derive grants from browser metadata. Role-specific route authorization is a separate consumer. |
| Malformed role storage | Parse fails, value is not an array, or any member is not a string. | Keeps the authenticated subject but supplies an empty role list, rather than granting a role or signing the user out. |
| User metadata changes between lookups | Subsequent server lookup observes the current trusted record. | Fixtures change roles in D1 and assert promotion/removal on subsequent requests. The reduced principal's freeze is not a cross-request cache or a database transaction. |
| Lookup outage | Session/storage API rejects. | Error propagates. It is not indistinguishable from `null`, does not revoke an account by itself and does not trigger legacy verification. |

The adapter reports `emailVerified === true`; it does not independently require
that flag before returning a principal. Requiring verified email for configured
email sign-in and authorizing a particular route are different boundaries.
Preserving an imported opaque subject is necessary for ownership joins; the read
fixtures demonstrate synthetic state/AAD isolation, not a production account
migration or validation of the separate persistence implementation.

## Test-source evidence and remaining work

All links below are navigational; line ranges are bound to the source edition
above. **No listed test, build, auth request or schema operation was run for this
documentation change.** Earlier receipts retain their own source and scope.

* [Principal tests](../../tests/web/auth-principal.test.mjs): exact subject,
  reduced/frozen shape, malformed roles, owner mismatch and propagated outage.
* [Web runtime tests](../../tests/web/auth-runtime.test.mjs): exact mode selection,
  legacy-verifier identity and failure without fallback; build-condition
  assertions are source evidence only.
* [Better Auth edge tests](../../tests/edge/better-auth.test.mjs): explicit additive
  schema fixture, disabled defaults, verified email, cookie/origin controls,
  subject preservation, expiry and password-reset assertions.
* [Runtime edge tests](../../tests/edge/auth-runtime.test.mjs): mounted seam,
  slash-delimited routing, response headers, roles, logout and missing-schema
  distinction in a synthetic offline Worker.
* [Dispatcher tests](../../tests/edge/handler-auth-dispatch.test.mjs): mounted
  ordering, default legacy compatibility, selected private owner, role changes,
  revocation and generic outage responses. These assert the integration without
  replacing a complete dispatcher/client implementation review.

Remaining investigation includes live configuration and schema/migration custody,
real delivery/provider setup, library/version-specific behavior outside these
assertions, complete client/dispatcher consumers, operational revocation and
recovery, and their composition with separately owned state/persistence slices.
No live account, production cutover, exhaustive machine coverage or whole
UIF-252 completion follows from this source inventory.
