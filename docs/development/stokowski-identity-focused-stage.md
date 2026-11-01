# UIF-133: reviewed identity client stage

`identity-client-focused` is one fixed `reviewed-source-v1` / operation v3
profile. It retains the existing trusted owner admission, independently accepted
exact candidate, original native receipt/session/lease, source contribution and
path mapping. It supplies no new origin, coding admission, catalog grant or
publication capability.

The only test command is:

```
/bin/node --test --test-isolation=none --test-reporter=tap tests/web/offmenu-identity-client.test.mjs tests/edge/handler-auth-dispatch.test.mjs
```

The candidate must return exactly 14 tests/passes and zero failures, skips,
cancellations or todo. Its `control_sha256` hashes the accepted base's exact
`git archive BASE` of those two fixed test paths. The archive is checked, not
executed; existing Python harness profiles and their control tests are unchanged.
The source/ancestry/committed output oracle runs before tests and in `finally`
after them, including unsuccessful execution. Unexpected untracked source fails.

Miniflare's supported `MINIFLARE_CACHE_DIR` points into a temporary `/tmp`
runner scratch directory. `CLOUDFLARE_CF_FETCH_ENABLED=false` prevents the
host-side default CF metadata fetch/cache (`.wrangler/cache/cf.json`), and
Wrangler metrics are disabled. HOME, XDG paths and TMPDIR also select scratch;
no ambient auth, Node options or candidate-supplied environment is forwarded.
The existing fixture's synthetic bindings and disabled outbound fetch mock remain
unchanged. Loopback listeners and the existing pinned Node/esbuild/Miniflare
runtime require normal owner runtime admission. No installs or live auth occur.

For UIF-96, preserve native receipt `733ee322…`, executed head `7aac2240…`,
original session/lease and resolved-model status (unobserved). Root's extracted
contribution/candidate `bff58041…` has the same sole `c21c818e…` output; use
identity path mapping and null derivation. The personally attested typed review
`9be381c0…` and separate source association `866f6ac5…` retain original compact
review `4c8cef7c…` and its independently accepted 14-test run. Those old tests
remain evidence; the new stage job is new, not a historical Journal replacement.

After source acceptance, Root adopts the new producer/executor pins, prepares
real remote candidate custody and a trusted v3 admission outside the candidate,
then uses existing `stokowski_stage.bind_reviewed_source` and the same Journal,
bridge, resource policy, recovery and no-replay rules. CLI binding is usable only
under its documented SOURCE-private runtime constraint; the existing Python API
is available to the trusted owner caller, without rebinding globals. Root alone
registers the genuine reviewed-source validation entry and its stage manifest
with the same project-aware coordinator/catalog, then continues validation,
review/publication/completion/refill. No historical current-admission,
dispatch-intent or coding Journal may be manufactured for the direct native run.
