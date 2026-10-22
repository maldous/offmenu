# BYOC, encrypted private payloads and lifecycle contract v1

**Prepared, not activated.** Immutable baseline: `af99cdfb4bac3bce9f4badae34333921a0074a76`. This additive source proposal creates no real credentials, key material, provider connections, live tables, privacy choices or deployment. The companion household-domain migration references this schema. Passing synthetic tests does not establish production isolation, KMS availability, legal rights or anonymous publication.

## Actual design and implementation evidence

- `research/reports/04-OffMenu_User_Driven_Cache_and_Enrichment_Design-1-.pdf`, SHA-256 `2e049a433c329421249a27ccbf92f15c64b9da2cc3adb065d8c6ddb13dff2ccd`: pp. 2–4 require scoped credentials, field-level rights, connection/entitlement-bound private caches and separate public facts; p. 5 prohibits quota pooling; p. 6 prohibits inference that family membership permits private health access; p. 7 separates private use, contribution and background refresh, with job/commit/serve rechecks; pp. 8–9 require no cookie pooling, private mixed responses and deletion through derivatives/backups.
- `cloud/provider-data.mjs`: existing `provider_connections(user_id,source_id,sealed)` uses AES-GCM and AAD `user.id + '|' + source.id`; only USDA and Edamam own-key lookups are implemented. Lists omit keys, lookups are private/nonpersisted, disconnect removes that owner's stored connection and private provider records. This is direct-key v1, not a rotating envelope-key system.
- `README.md`, Global data and bring-your-own credentials: preserve the existing `PROVIDER_VAULT_KEY`; do not regenerate it after credentials exist. No provider secret in profile backups, localStorage, logs or error URLs.
- `extension/README.md`: current preview reads user-invoked page data, requires review and exports selected JSON. It does not read passwords, cookies or payment details, emulate APIs or purchase automatically. Browser-local connection metadata below is accommodation, not new access permission or an implemented connector.
- `docs/private-aggregate-admission-owner59.md`: aggregate admission is a distinct qualification path; existing synthetic validator denies real use/publication. Consent and redaction alone never grant provider reuse rights or establish anonymity.
- `cloud/schema.sql`, `docs/better-auth-foundation.md`, `docs/better-auth-runtime-seam.md`, `docs/session-state-d1-owner04.md`: preserve opaque subject IDs, kitchens and existing grants. Better Auth and session-state adapters have explicit unmounted/adoption gates; do not infer live migration from source presence.

## Storage contract (10 new tables)

Apply `cloud/migrations/20261022-byoc-security-v1.sql` **after** existing `cloud/schema.sql`, then household-domain schema, in an approved migration process. This work has not run those steps on any real store. SQLite tests run in memory with foreign keys on; native D1 constraint/runtime acceptance remains required.

| Table | Purpose and boundary |
| --- | --- |
| `sec_key_references` | Opaque external DEK reference/version, owner, custody, algorithm and lifecycle. Never a raw key, wrapped key, secret-manager credential or provider secret. |
| `sec_envelopes` | Authenticated ciphertext + 12-byte nonce + key reference/version; owner, optional kitchen, object, purpose and provider bind AAD. Immutable rows: rotation creates a replacement, then atomically changes references. |
| `sec_consents` | Current explicit choice, actor, object/purpose/target, notice version, revision and expiry. Scope changes need a new row. Private use, facts, aggregates, background refresh and profile sharing are distinct. |
| `sec_consent_events` | Append-only choice history, no body. Retention-controlled purge; not a public or anonymous ledger. Update projection and append event atomically with revision CAS. |
| `sec_provider_connections` | Owner-private opaque connection, provider/kind/custody, entitlement and source-policy revisions, consent reference, state and expiry. Binding triggers prevent another owner/provider/object envelope being attached. |
| `sec_connection_scopes` | Exact scope/resource/purpose allowlist bound to owner+connection. No implied wildcard or household grant. |
| `sec_sessions` | Companion subject/issuer/session-reference hash, audience, realm, epoch, expiry and revoke metadata. No bearer/session issuance and no replacement identity system. |
| `sec_deletion_requests` | Scope, deadline, completion, explicit evidence-retention horizon and restore-replay requirement. Do not mark complete with missing target evidence. Completed evidence is immutable and purge is blocked until its retention horizon. |
| `sec_deletion_targets` | Per-store removal/not-applicable evidence: credential, cache, body, assertion, search, embedding, derivative, queued job, contributor link, backup replay. |
| `sec_audit_events` | Restricted action/outcome/opaque resource IDs and retention. No request/response bodies, secrets, query URLs or arbitrary errors. |

There is no new users/tenant table: existing `kitchens.id` is the kitchen FK; `owner_user_id` is the original verified identity subject and is not forced to unactivated `auth_user`. Profile IDs are not login IDs. `sec_envelopes` exposes both `UNIQUE(owner_user_id,id)` and `UNIQUE(kitchen_id,owner_user_id,id)` for account-private and household operational payload references respectively. `sec_consents` exposes `UNIQUE(owner_user_id,id)`.

Profile payload references must bind the profile owner, object and purpose. Explicit profile-grant rows reference a separate `profile_share` consent naming the grantee. A kitchen owner/editor role does **not** grant another member's credential, health, religious preference or private profile access. SQL foreign keys enforce referential ownership, not reads; SQLite/D1 has no row-level policy here. Every query, index lookup, export and decryption requires application authorization.

Opaque owner/connection IDs, expiry, revision, and operational inventory quantity/date metadata remain sensitive private metadata; this is not full database encryption or E2EE. No such metadata is admitted to public analytics by default. Labels, provider secrets and health/religious profile values belong in typed sealed payloads, not `state_json`, search indexes or public source records.

## External key custody and versioned encryption

`cloud/byoc-envelope-v1.mjs` is an **unmounted** WebCrypto helper, not a KMS adapter. It accepts a trusted `resolveKey` custody function, returns only AES-256-GCM ciphertext metadata and emits generic failure messages. The repository/database contains only an opaque key-reference ID and version. The helper refuses missing, raw, extractable, wrong-algorithm or wrong-use keys. No key is generated as a fallback; only tests generate disposable nonextractable synthetic keys.

Server-envelope custody requires an external custodian to keep each DEK wrapped by a separately controlled KEK, resolve/unwrap it under authenticated subject/purpose authorization and return a nonextractable AES-256-GCM CryptoKey. Both raw and wrapped key material stay outside this application database; key references are not usable credentials. Separate access controls are required for ciphertext and external custody. This proposal chooses an interface, **not a vendor or provisioned production KMS**. Runtime memory necessarily sees authorized plaintext; nonextractability does not make a compromised server safe.

Client custody is a separate explicit mode: only the owner's authorized device resolves the key. The server stores/relays ciphertext and cannot decrypt, enrich, recover or schedule unattended use without a separately designed grant. A server-envelope instance refuses client-custody envelopes. Browser-local retailer sessions remain in the retailer/browser; no cookie/token upload, cookie pooling or extension permission broadening is included.

AAD is canonical JSON array:
`['offmenu-sealed/1', version, algorithm, custody, keyRef, keyVersion, ownerUserId, kitchenId-or-empty, objectType, objectId, purpose, providerId-or-empty]`.

The adopting mapper translates SQL `key_ref_id` to envelope `keyRef` and decodes canonical base64 nonce/ciphertext into BLOB columns. It reconstructs expected AAD from authenticated/authorized stored context, never from caller-owned identity claims. The nonce is cryptographically random and unique per key/version; SQL rejects reuse. Payload limit is 1 MiB; unknown format, tamper, wrong owner/kitchen/provider/purpose, missing key or unsupported custody fails closed. Do not downgrade to plaintext, an older vault, another account or a public provider.

Rotation: create a new external key version; make old key decrypt-only; freshly authorize and decrypt/re-encrypt each selected envelope with new nonce and AAD; atomically CAS connection/profile references; verify readback before removing old material. Keep old keys only for documented permitted retention/restore requirements. Revocation stops decrypt/use immediately even while ciphertext awaits deletion; destruction needs external custody evidence. An individual record's key should not be shared across unrelated owners; crypto-erasure claims require proof of every copy and backup key's disposition.

Legacy v1 migration is a **separate blocking prerequisite**: inventory connection row counts without exposing secrets; preserve the exact existing vault secret and original `user|provider` AAD; decrypt only inside approved runtime; re-encrypt into the new format and verify per-row before atomic cutover. No bulk copy/relabel can turn direct-key ciphertext into envelope encryption. This patch leaves legacy rows and handlers unchanged.

## Authorization/API integration contract (not mounted routes)

Use the existing authenticated `/api/data/connections` and `/api/data/lookup` surfaces; do not add an alternative unguarded endpoint. Suggested versioned service operations:

1. **Connect/replace**: verified owner session, exact same origin/CSRF, bounded body, known provider-specific fields; validate source tier/policy and separate private-use choice, seal in memory, then atomically write bound envelope+connection+scope+consent event and safe audit. Return metadata only. Encryption success does not validate provider credentials or activate an unimplemented adapter.
2. **Use**: freshly authenticate original subject/session; read exact active owner connection, current consent and policy, owner+connection-bound scope/resource/purpose, entitlement revision, expiry and custody; resolve key only after admission. `credentialUseAllowed` is a pure **private-use snapshot predicate**, not authentication, an authoritative store, transaction or future-use lease. Caller must couple current predicates atomically to start/commit/serve and handle withdrawal during awaits. It deliberately denies background refresh/client custody; those require their own fresh explicit authorization.
3. **Background refresh**: additional `background_refresh` consent, named datasets, source scheduled-use permission, frequency/quota/spend budget, no rotating across owners to evade quotas. Recheck start/commit/serve. Queue only opaque references and pinned revisions; never credential material, raw response bodies or key-bearing URLs. No worker/queue is supplied here.
4. **Disconnect/revoke**: atomically revoke connection, advance entitlement/session epoch where scoped, cancel pending work, stop cache/derived reads immediately and begin retention-aware erasure. Provider-side revocation requires that provider's actual supported operation; keep pending/failed status rather than claiming local deletion revoked an upstream token.
5. **Sessions**: authenticate through selected existing IdP; preserve issuer/audience/realm/epoch and expiry, never accept request-supplied owner or email equivalence. Hash high-entropy opaque upstream session references; do not store raw bearers. No invalid-session fallback to another IdP. The companion table does not revoke independent OAuth/MCP grants automatically; retain established scope/logout behavior unless separately migrated.
6. **Delete/restore**: enumerate every applicable target, tombstone access first, invalidate derivatives, obtain target acknowledgements, persist minimal purpose-limited replay evidence outside the deleted data, and replay tombstones before restored data is exposed. Mark complete only after target evidence and backup replay obligations are satisfied. Completed request/target evidence remains immutable until its explicit evidence-retention horizon, then may be purged target-first; no invented fixed retention period. The horizon must cover the last possible relevant backup restore, not merely primary-store deletion.

`Cache-Control: no-store` and safe error handling apply to mixed/private responses. Provider-host allowlists and fixed service adapters prevent user-selected exfiltration destinations. Credentials never appear in response lists, profile backups, REST/MCP normalized records, localStorage, logs, traces, telemetry or Git. Synthetic test values are not real secrets.

## Public-cache boundary

Private connection use works when contribution is denied. A connection grant does not authorize fact contribution; fact contribution does not authorize aggregate activity; neither authorizes advertising/model training. Promotion is field-level and additionally requires explicit source rights for action/audience/territory, current dependency rights and identity/quality checks. Personal prices, receipt/address/loyalty/payment data, health and household sequences remain private. Remove names or hash IDs is not anonymization. Do not publish contributor IDs or call this restricted audit anonymous.

The SQL deliberately contains no boolean such as `anonymous=true` that bypasses qualification and no automatic promotion trigger. Existing Owner59 aggregate machinery still requires qualified lineage/cohort/composition/privacy-budget/withdrawal evidence; public publication remains denied. Source-policy narrowing invalidates every dependent cache/index/export/derived output even if consent is unchanged. Independent public facts may remain only under their own permitted lineage.

## What is and is not established

Prepared: versioned schema, owner/provider/AAD binding, explicit external/client custody modes, pure deny-by-default snapshot gate, consent/deletion/audit shapes, and targeted synthetic checks. No populated production tables, provider API calls, KMS, environment/security setting, IdP migration, new credential, schema application, browser extension change, deployment, Foo/remote action or real personal dataset access occurred.

Remaining runtime gates: trusted custody implementation and independent KEK/DEK lifecycle; native D1 migrations and transaction/authorization adapters; fresh atomic job/commit/serve withdrawal coupling; actual UI notices and per-member/guardian authority; provider-specific OAuth/retailer contracts and scopes; verified upstream revoke; deletion/index/backup executor and restore testing; source-policy/promotion qualification.

Existing `cloud/auth-schema.sql` includes Better Auth token/session text columns. This patch does not silently rewrite library-owned schema, claim those fields are encrypted, or activate that unmounted subsystem. Any later adoption must qualify token persistence and session storage separately. Existing `user_state`/kitchen JSON is not retroactively encrypted or migrated by adding tables.

## Focused checks

```
node --test tests-web/byoc-envelope-v1.test.mjs
python -m unittest discover -s tests -p test_byoc_security_schema.py -v
```

Tests use Node WebCrypto and Python in-memory SQLite with the actual baseline `cloud/schema.sql`, no network or provider data. They check owner/kitchen/provider/purpose tamper, missing keys, custody modes, expiry/revocation/consent/scope changes, bound FKs, append-only history, legacy preservation and deletion completion. Native D1 and actual authenticated routing/withdrawal races are not established by these tests.
