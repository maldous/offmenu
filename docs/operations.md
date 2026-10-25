# OffMenu operations

Repository: private `maldous/offmenu`. The primary checkout is `/home/user/src/offmenu`; `main` is stable and `develop` is the integration branch. Feature and pinned review checkouts live under `/home/user/src/offmenu-worktrees`, while retained data and operational evidence live under `/home/user/src/offmenu-data`. Select the accepted integration/release receipt for the work; a remote tip or an old local branch alone does not establish acceptance.

Use the [maintainer setup and local checks](maintainer.md) for dependencies, build side effects and the small Python demo. A held live checkout may intentionally remain behind accepted integration while loaded source, assets and state depend on it. Preserve that runtime until its owner records a safe handoff; do not reset or repoint it to perform documentation/build work.

OffMenu action tracking belongs in the existing canonical ledger, not GitHub Issues; pull requests remain code review. Follow the [automatic tracking contract](maintainer.md#automatic-work-tracking), preserving separate transport, pickup and completion evidence.

Historical pre-migration GitHub reconstruction and checkpoint observations remain in their original receipts. They are not current authentication, deployment or branch-freshness evidence.

Install the declared development dependencies and run the current baseline checks listed in the maintainer guide. `npm test` covers the web suite; locale-edge and Python checks are separate. Production deployment is a separate reviewed release action under the current operational holds. The generated Worker embeds its source commit and build date; `/api/health` exposes these without private state. Build after committing functional source. Production verification results belong in a subsequent evidence-only commit.

Cloudflare Worker `offmenu` binds D1 `offmenu-users` (`006cbdd6-6be8-4181-9dd5-519de280b6ef`) as `DB`. Keep current compatibility settings, observability query redaction and hourly maintenance schedule. Module upload must set `keep_bindings:["secret_text"]`; never replace `PROVIDER_VAULT_KEY`. Netlify Identity remains the identity provider. Source uploads must not recreate authentication or reset D1.

New resolver leases prevent equivalent public misses from sharing in-flight request promises across Workers requests. Keys partition by source, exact query, source policy document and normalizer version. Expired leases are reclaimable; failures back off. Policy checks occur before reads and before writes. Source withdrawal immediately denies reads; maintenance removes expired cache, leases and explicitly expired private retained records. Shared contribution and behavioural aggregates remain disabled.

Private imported records retain original rights. Reviewed open sources permit private processing under their attached notices. Unknown provider persistence/export/derivation is denied until a reviewed active source policy permits the action/audience/market. `source_policies` is operator-maintained, not writable by anonymous import payloads. User-confirmed personal/retailer imports remain private and unverified. Provider disconnect removes account-owned source records; external credentials must be revoked at the provider separately. Sensitive unified kinds use dedicated consented health/history workflows, not generic data scopes.

Read-only REST and MCP use separately scoped tokens. Sensitive health scope is never automatically requested when the caller omits scopes. APIs remain account-scoped; a kitchen membership does not grant private measurements/history. Household-scoped delegated integrations and external-client certification remain acceptance work, not an implicit widening of existing token permissions.

Deployment acceptance: verify release commit, catalogue completeness, country/source pagination, special territory behaviour, synthetic calculations/comparisons, company candidates and warm cache, auth-required private routes, identity settings, OpenAPI/OAuth metadata, and browser demo. Recheck D1 counts, account aggregate revision/size and secret binding. Do not include private documents, credential values or production snapshots in logs or evidence files.

Public food-place API attribution: Overture/Foursquare references retain the full [Foursquare publisher NOTICE](https://offmenu-corpus.netlify.app/notices/overture-food-places/2026-09-23.1/FOURSQUARE-NOTICE.txt), Apache 2.0 and CDLA Permissive 2.0 licence copies. See [public lookup contracts and notices](places-national-expansion.md).
