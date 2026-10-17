# Vendored freebuff-relay poller — provenance and deliberate change

Source artifact: `/home/user/Downloads/freebuff-relay-artifact-2026-10-17.tar.gz`
- SHA-256: `999acb908d618e9a562611212f051292a4005f7036bbadbdc2e8c1c39e40f449`
- Read/extracted at `/tmp/freebuff-relay-artifact-read/freebuff-relay` on 2026-10-17.

Copied verbatim from `poller/` in that artifact (byte-identical at copy time, verified with `cmp`):
`src/contracts.mjs`, `src/transport.mjs`, `src/engine.mjs`, `src/journal.mjs`, `src/cli.mjs`,
`test/poller.test.mjs`, `package.json`, `adapters/unverified.mjs`.

## Deliberate reviewed change (the only modification to shipped code)

File: `src/contracts.mjs` — `validateCredentialHeaders` allowlist gains one name: `x-freebuff-launch-id`.

Verified live evidence on foo, 2026-10-17, read-only `GET /api/thread/:id?projectPath=/home/user/src/offmenu`
against the loopback API in `/home/user/.local/state/freebuff/api-session.json`:

| credential header sent                         | result |
|------------------------------------------------|--------|
| (none)                                         | 401    |
| `x-freebuff-launch-id: <launchId>`             | **200**, body keys `thread,messages,items` |
| `authorization: Bearer <launchId>`             | 401    |
| `x-api-key: <launchId>`                        | 401    |
| `x-freebuff-token: <launchId>`                 | 401    |
| `x-freebuff-session: <launchId>`               | 401    |
| `cookie: launchId=<launchId>`                  | 401    |
| `x-freebuff-launch-id: <wrong value>`          | 401    |

The API authenticates only with `x-freebuff-launch-id`, which the shipped allowlist does not
permit, so `LocalClient.snapshot` cannot work without this addition. The shipped README
sanctions exactly this path: "Any extra credential-header requirement must be reviewed and
deliberately added, rather than accepting arbitrary request headers."

## Second deliberate change — Morgan's exact target binding (2026-10-17)

`src/contracts.mjs` — `PROJECT_PATH` moves from `/home/user/src/offmenu` to
`/home/user/src/offmenu-workers/worker-62`, binding the poller to target session
`bac212ab-b73c-4f64-a995-e57ee9ec0877`. Applied consistently in the fixed project
restriction, the private config (`/home/user/.local/state/freebuff-relay/poller-config.json`,
mode 0600), and the live smoke. Consequent test adaptations (assertions kept exact,
now derived from `PROJECT_PATH`): the hard-coded `projectPath=` URL expectations in
`test/poller.test.mjs` and `test/localclient-verified-adapter.test.mjs`.

No other shipped line is changed. The rest of the allowlist behavior is preserved:
arbitrary header names (e.g. `host`), malformed values, and shared local/gateway credentials
are still rejected by `validateCredentialHeaders` / `LocalClient.headers()`.

## Adapter

`adapters/freebuff-verified.mjs` replaces `adapters/unverified.mjs` as the configured
`adapterFile`. It implements the exact README interface, including the object call form
`normalizeSnapshot(rawResponse, { sessionId })` used by `LocalClient.snapshot`.
`adapters/unverified.mjs` is kept because the shipped test suite references it.

Contract update (2026-10-17, Morgan-approved, live-evidence-driven): the message
temporary id is `msg-<ts>-<role>`. Cross-role same-millisecond pairs (turn
boundaries, observed live on `bac212ab`) are kept with their distinct ids;
only a true collision (same ts AND role) rejects the snapshot. Nothing is
silently dropped as truncation.
