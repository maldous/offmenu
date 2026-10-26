# Owned backup source composition

`cloud/private-portability-owned-backup-v1.mjs` composes the independently accepted `owned-snapshot-extractor.mjs` with the existing private portability exporter. Each invocation owns its component instances and authority stamp. Every extraction/export authority read must preserve the same complete context. A changed identity, namespace, consent, deletion scope or revision requires a fresh call. The exporter still requires an independently supplied package-bound complete inventory and payload digest.

Only `packageId`, `recoveryRef` and `keyReference` are caller inputs. Trusted server adapters supply `readAuthority`, `openSnapshot`, `authorizeSourceRecord` and `resolveKey`. Do not infer verified issuer/subject from an email or create attestation from extraction completeness. Connections retain their safe archival shape; credentials and active grants are excluded.

These source modules are unmounted. This change supplies no application route, current identity/storage/key adapter, database migration, UI action or operational restore. Actual trusted adapters and private export acceptance remain unqualified. Existing limits, per-record source rights and deletion controls still apply.

Acceptance pins: extractor `aba2af62` with Worker57 review `9ef81e11`; composition successor `610485c3` with Worker62 closure `82db7763`. The earlier composition `663e34a9` remains held. Full receipts and generated-proof qualification are in the existing OffMenu permanent ledger. The narrow authority-continuity slice is recorded under the existing `REVOCATION-DELETION-RESTORE` parent; this does not complete the parent or the broader portability assignment.
