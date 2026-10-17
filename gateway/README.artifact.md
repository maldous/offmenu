# Private Freebuff transport bridge

Implementation artifact, not a completed integration. The gateway is fail-closed; the local poller is deliberately unconfigured. No real credentials or Freebuff API were accessed to build or test this artifact.

## Architecture and limits

Owner → OAuth-protected Streamable HTTP MCP → SQLite Durable Object → outbound-only Node 24 poller → existing Freebuff loopback API. Morgan decides what to send. This code only transports explicitly supplied messages and observations.

Exactly five MCP tools: `bridge_status`, `list_sessions`, `read_messages`, `enqueue_message`, `get_receipt`. No shell, URL fetch, file, session creation, session start/resume, or arbitrary API tool. Up to three configured existing sessions. `list_sessions` reports this allowlist and last snapshots, not an invented Freebuff discovery API. The historical paused session `8d8caabd-881d-4fda-bb90-7c7c3f10e178` is explicitly excluded. Both the gateway and poller refuse dispatch with paused/unknown/stale state; the poller rechecks locally and always sends `now:false`.

- Messages: 16 KiB UTF-8 maximum, nonblank, excluding the reserved relay-marker prefix.
- Snapshot: latest 40 messages, each 4096 JavaScript characters; whole HTTP body ≤256 KiB. Read results include observation time and staleness. Data is untrusted content, not instructions.
- Queue: 32 accepted/uncertain requests, 10,000 retained receipts. Delivered receipts do not occupy pending-dispatch capacity.
- Identity: stable lower-case UUIDv4 request IDs, payload SHA-256 over `JSON.stringify({sessionId,text})`, one assigned lease per request, durable local sending intent before POST.
- A lease is never reassigned. Expiry becomes `uncertain`; only positive exact user-message readback can reconcile delivery. Missing readback is not proof of absence and never permits automatic resend.
- Distinct states: accepted, delivered, started, completed, failed, uncertain. Queue acceptance is not local delivery; local delivery is not agent execution. The supplied poller cannot emit started/completed because no request-correlated Freebuff lifecycle schema has been verified.
- Gateway message text, snapshots and receipts expire seven days after their original timestamps/acceptance. Reads hide expired data immediately; Durable Object alarms schedule physical deletion and may be delayed by platform outages. SQLite/Cloudflare platform backups and recovery behavior are outside an application-level deletion guarantee.
- The local journal removes request text/report evidence on the same original seven-day deadline. Minimal request-ID/hash/state tombstones remain locally to prevent replay indefinitely; they contain no message text. See `poller/README.md`.
- Default polling: 30 seconds, snapshots per session every 60 seconds. Unchanged snapshot messages are not rewritten. No polling KV writes. OAuth dynamic registration is capped at 100/day; exact callback allowlist required. These are bounded design defaults, not a guarantee of zero cost under traffic or attack. No plan upgrade is performed by this artifact.

## Auth route: one consistent design

A Cloudflare Access **self-hosted application protects only `/authorize`** on the gateway hostname. The gateway validates the Access JWT cryptographically with the configured team JWKS, RS256, exact issuer and audience, required expiry/issued-at claims, `type:app`, owner email, and owner subject. It does not trust an email header or decoded unsigned JWT.

After that owner identity check, `@cloudflare/workers-oauth-provider` provides OAuth 2.1/PKCE, browser-bound single-use consent, token issuance, resource audience checking and discovery. This is the supported one-Worker `OAuthProvider` mode, not Access for SaaS OIDC. No upstream OIDC client secret is needed.

Keep `/mcp`, `/.well-known/*`, `/oauth/token`, `/oauth/register`, and `/bridge/*` outside the Access browser-login gate. MCP uses OAuth bearer tokens; `/bridge/*` independently accepts only its own scoped poller bearer. The poller token cannot call MCP and an MCP token cannot call poller endpoints. The Worker has no external-token passthrough or arbitrary metadata URL fetching. OAuth redirects must match exact configured HTTPS URLs. Both `bridge:read` and `bridge:write` are advertised and required; missing scopes return the standard OAuth insufficient-scope response.

## Configured non-secret deployment facts

The parent verified/provisioned these account resources separately; this build did not deploy or create them:

- Cloudflare account: `7edd51038e07b5b84a635b3ff7e11144`
- Gateway origin: `https://freebuff-gateway.aldous.info`
- Access team: `matthewaldous.cloudflareaccess.com`
- Access application: `a4d06e5c-ae70-4a58-b479-c25d0d7eb70b`
- Access AUD: `6ff19b6255cbbd295d4d0ff7cf10a9a27079930c7cb641fe0d4b8cb970b77fe2`
- Access owner allow policy: `c871fb32-ad05-480a-9b69-5df8476d5ad6`
- Approved bridge owner: `alexander.emmalyn.thomas@gmail.com`. The Cloudflare administrator email is a different identity and is not authorized as this bridge owner.
- OAuth KV binding: `OAUTH_KV`, namespace `5b9e248128ab424b8a31b034a2c3c269`
- SQLite Durable Object binding/class: `BRIDGE` / `BridgeQueue`, migration `v1`

`wrangler.jsonc` and `dist/bootstrap-metadata.json` keep `ENABLED=false`, `OWNER_SUB=""`, and both allowlists empty. The raw poller token is not in any artifact. The future Worker secret `POLLER_TOKEN_SHA256` stores only the lowercase SHA-256 hash of a separately generated random 32-byte base64url token; the raw token stays in an owner-only file on the poller host. Provision it only through the authorized secure setup process. It is not the existing Freebuff API credential.

## Bounded setup and verification sequence

1. Deploy the reviewed bundle with bootstrap metadata, still disabled; attach only the verified gateway hostname. Do not modify the existing `offmenu` Worker. For first deployment use the `new_tag:v1` SQLite migration; subsequent updates must use the existing migration state and must not recreate the class. Disable workers.dev and preview URLs as specified in the Wrangler config; those toggles and custom-domain attachment are separate from the script-upload metadata.
2. Visit `https://freebuff-gateway.aldous.info/authorize?setup=1` and sign in as `alexander.emmalyn.thomas@gmail.com`. This route validates signature/issuer/audience/expiry/app type and the approved email even while the bridge is disabled. It returns only `{ownerSub:"..."}`. It never returns the JWT, issues an OAuth grant, or enables MCP. Set `OWNER_SUB` to that verified non-secret subject. Wrong-email logins must remain denied.
3. Configure exact OAuth redirect URI(s) from the actual ChatGPT/private-plugin setup screen or verified client metadata. Do not assume the synthetic callback in the tests is a production callback. No wildcard, user-supplied callback, or guessed domain. Leave dynamic client metadata documents disabled.
4. Select 1–3 explicitly approved existing Freebuff session IDs and set the identical gateway and poller allowlists. Do not include the historical paused target, create another session, or resume an existing one. Provision the separate scoped poller token securely; pin only its hash in the Worker.
5. On the authorized host, perform the bounded verification in `poller/README.md`: verify Node 24, literal loopback API port, the existing private authentication-file schema/header, GET response session identity, authoritative pause field, original message text/authorship/IDs/timestamps, and the queue route's documented `now:false` behavior. The only known routes are GET `/api/thread/:id?projectPath=/home/user/src/offmenu` and POST `/api/thread/:id/queue` with `{projectPath,text,now:false}`. Do not guess a session-list endpoint. Keep all credentials on that host; never copy the authentication file into this artifact, gateway, logs or chat.
6. Implement and test the small `extractCredential`/`normalizeSnapshot` adapter from verified local evidence. The shipped `verified:false` adapter exits before any credential read or network access. Only after the verified adapter and private config are ready, run the poller in the foreground and check read-only snapshots. The included service file is inert and is not installed automatically.
7. Set `ENABLED=true` only after identity, callback allowlist, session allowlist, poller hash, and adapter are verified. Test actual owner login/consent; verify unauthenticated MCP is 401 and another identity cannot authorize. Check `bridge_status` and `list_sessions` show the intended session and fresh pause state.
8. With an explicitly approved, unpaused target and harmless test message, perform one live enqueue. Confirm the same request ID/payload hash, one local user message with exact marker, and a delivered receipt. Retry the same MCP request ID to prove no duplicate. Then test pause rejection without resuming a session. Treat a failed or uncertain test as unresolved; never delete the journal or reissue automatically.
9. Install the user-service only after that round-trip passes. Root owns deployment/activation authorization and user updates. This artifact does not claim those stages have happened.

## Reproduce verification

Node 24 is required. In this artifact directory:

```sh
npm ci --ignore-scripts
npm run typecheck
npm test
npm run build                  # wrangler deploy --dry-run only; no deployment
npm run test:runtime
```

Where HOME is read-only, set `npm_config_cache` and `XDG_CONFIG_HOME` to writable directories. Test credentials are synthetic and ephemeral. The runtime test runs the real bundled Worker under workerd/Miniflare, with SQLite Durable Objects and a synthetic Access JWKS. Its ingress wrapper corrects Miniflare's loopback Host header to the rewritten URL host to model a real custom-domain request. It uses manual redirects and does not perform live authentication. These checks do not establish compatibility with the real Freebuff API or a live ChatGPT connector.

Deployment artifact: `dist/index.js`, a single ESM bundle; only Cloudflare/Node built-in imports remain. `dist/index.js.gz` is the same bundle compressed for transport. `dist/bootstrap-metadata.json` is script-upload metadata for the initial disabled deployment; it contains no credentials. `dist/manifest.json` records sizes and hash. The source map is not needed for upload and can expose source, so it is excluded from the delivery archive.

## Current primary references

Retrieved 2026-10-17 and checked against installed package types/source:

- [Cloudflare MCP handler API](https://developers.cloudflare.com/agents/model-context-protocol/apis/handler-api/): `createMcpHandler` from `agents/mcp/server`; fresh SDK v2 server factory.
- [Cloudflare MCP authorization](https://developers.cloudflare.com/agents/model-context-protocol/protocol/authorization/).
- [Workers OAuth Provider source and documentation](https://github.com/cloudflare/workers-oauth-provider), including bundled `docs/consent-page.md` and `dist/oauth-provider.d.ts` in version 1.2.3.
- [Validate Cloudflare Access JWTs](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/).
- [Workers best practices](https://developers.cloudflare.com/workers/best-practices/workers-best-practices/).
- [RPC error handling](https://developers.cloudflare.com/workers/runtime-apis/rpc/error-handling/): errors use an explicit bounded DTO across the Durable Object RPC boundary.
- [Node 24 SQLite API](https://nodejs.org/download/release/latest-v24.x/docs/api/sqlite.html).
