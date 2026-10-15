# Synthetic Owner04 / integrated queue compatibility witness

Input queue commit: `e4c87278bf94f791b0dd7f30672b65edf992317e` (integrated PR13). Input D1 commit: `38a7d0b3a86dfd11d582f7f5238215a06abd9103`; independent mechanical composition review: `/home/user/Documents/Codex/2026-10-15/worker13-d1-38a7d0b-review/receipt.json` (scoped PASS).

`inputs.json` binds all 15 selected executable source files to the actual input commits, original paths, reused local fixture paths and SHA256. Preparation compared Git blob bytes directly. The selected D1 module and 11 other closure files match the existing packaged fixtures. Two locale helpers differ in the selected final-f6 closure; only those two exact snapshots were added under `tests-web/fixtures/queue-d1-compatibility-owner16/`, with scoped LF attributes. Bundling resolves the complete selected D1 closure through this explicit manifest, not moving checkout or Git lookups. Runtime integrity comparison canonicalizes CRLF to LF only, matching the documented LF Git-source hashes. Mutation of substantive source content still changes the digest. Queue bridge and entrypoint remain byte-identical to the integrated input. No existing runtime or accepted test was modified.

`tests-web/queue-d1-compatibility-owner16.test.mjs` reuses the existing synthetic HTTP/native D1 fixture composition with explicit test credentials and disposable Miniflare D1. Project-declared dependencies are reused; no new install or external server. The host entrypoint only serves a disposable synthetic test surface: no application route, deployment, session enrollment service, migration or real user data is activated.

Three new bounded groups passed, zero failed/skipped:

- Actual selected D1 ledger and integrated queue ACK agree on subject/session/realm/epoch/resource, operation ID, independently calculated canonical digest, expectedVersion+1 and explicit acknowledgement. Exact replay has one effect.
- After real commits, separately damaged subject/session/realm/epoch/resource/digest/ID/version/ACK responses stay unconfirmed. Exact-command recovery succeeds with matching digest/revision; another payload cannot recover the outcome. Stale expectedVersion produces a confirmed conflict with acknowledged=false.
- A real enrollment/public selector does not confer authority: cross-account, capability, epoch and realm mismatches deny with no ledger effect. A matching ACK for an earlier authorized commit survives subsequent server expiry; new send/status remain denied.

Only this new witness ran: `node --test tests-web/queue-d1-compatibility-owner16.test.mjs`. `results.log` retains exact output. No replay of unchanged 19-check acceptance or unrelated suite. Runtime resources disposed after each group. This is a synthetic local compatibility witness, not issuer/credential-policy, central caller, remote D1, rights/consent, release or production qualification. Actual authority remains in Owner04's authenticated, persisted session checks, not the selector or response-damage fixture.

Prior branch/history and untracked `.wrangler/` custody are preserved. The witness adds only unique owner test/evidence and two test-only helper snapshots. SAME25 exact new-delta review and manager acceptance remain required; all adoption and production holds persist.
