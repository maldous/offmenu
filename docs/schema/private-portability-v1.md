# Private portability v1 — source preparation

This is an unmounted source implementation with generated verification. It does
not authorize or perform an actual private export, import, connection, key
provisioning, sharing operation, migration, route activation or deployment.
Worker19 owns the five-file proposal; Worker64 reviews the exact freeze and
Worker00 owns Git custody, integration and any later actual DDL execution.

The prepared architecture originally came from immutable commit
`011745f3aad5b5debf8765f74620437614039d31`, branch
`feature/normalization-second-crash-isolation-20261023`. The four PR106 provider
corrections use published baseline `2cc7b402d7b474475e2dd9cdbdce1da49ca64d44`
on `feature/private-portability-contracts-20261023`; its change from `666f949`
was CI-only and the five private files were unchanged before correction. These
source pins do not establish runtime adoption or an accepted release.
Worker57's frozen 17-kind schema is unreviewed design input. Its record shapes
are reused with qualification, encrypted packaging, lifecycle, clinical
provenance, attachment bodies, relationship provenance and versioned extensions.
No external-standard or legal-compliance certification follows.

## Existing identity and credential contract

| Existing source | Exact contract and portability consequence |
| --- | --- |
| `cloud/auth-principal.mjs` | `getOffMenuPrincipal` calls the existing server session verifier with cookie cache and refresh disabled, checks `session.userId === user.id`, then preserves the exact opaque `user.id`. Email, names and roles do not establish portable identity. The principal does **not** expose a verified issuer/subject pair. |
| `cloud/auth-runtime.mjs`, `cloud/auth.mjs` | Existing mode is deployment-owned; absent mode retains the legacy verifier. Better Auth is an unmounted option, with account linking disabled and no social provider registration. This proposal adds no IdP, JWT verifier, bearer bridge, account link or login method. |
| Legacy `provider_connections` / `cloud/provider-data.mjs` | Existing `sealed` credentials use existing owner/provider binding. No credential, key, legacy sealed credential, provider token or session material enters a portable payload. No rekey or legacy migration occurs. |
| `20261022-byoc-security-v1.sql` | Existing `sec_provider_connections` binds owner/provider, entitlement revision, consent revision, source policy, expiry and credential envelope reference. `sec_sessions` is revocation metadata, not a session issuer. None of these creates portable effective authority. |
| `cloud/byoc-envelope-v1.mjs` | Reuses `createEnvelopeCryptor`, external nonextractable AES-256-GCM keys, fresh nonce and authenticated owner/object/purpose binding. No fallback key generation or plaintext/wrapped key export. Existing `credentialUseAllowed` remains a separate private-provider-use snapshot predicate; portability never treats it as authentication or a transferable entitlement. |
| `20261022-household-domain-v1.sql` | Reuses exact owners, kitchens, profiles, encrypted envelopes and inventory concepts. Kitchen ownership/membership does not grant another member's profile, medical, credential or inventory access. CLI/ingest tables are distinct and are not migration targets. |

Issuer and subject are separately compared as exact opaque strings, together
with the existing owner ID and instance namespace. They are never derived from
email, normalized, merged by subject alone, or accepted from package claims.
The missing verified identity seam is a real adoption dependency: a trusted
adapter must obtain and bind it from the current existing authentication system.
If it cannot, these helpers deny use. The helper does not verify a browser-supplied
`authenticated` flag or establish an independent identity framework.

## Package and payload

`schemas/private-portable-package-v1.schema.json` defines the public encrypted
package and `$defs.payload` defines the decrypted typed data. Version 1 accepts
only `offmenu-household-domain/1` source representation. Unknown package/schema
versions fail; adopting another version requires an explicit reviewed migration.
There is no heuristic field renaming or silent migration.

The public manifest contains exact source/destination identity, instance,
package ID, field/record scope, consent ID/revision, protection metadata,
encrypted envelope, manifest digest and checksum. These identifiers are private metadata: it is
not a public publication artifact. The checksum covers the canonical manifest
except its own checksum, including encrypted bytes. It detects corruption;
it is not a signature, source identity proof or authorization grant. The
version-local canonicalization sorts object keys and retains array ordering;
it does not claim RFC 8785 interoperability.

The manifest digest is additionally authenticated by the existing BYOC AES-GCM
AAD: its purpose is `owned_data_portability/manifest1:<manifestDigest>`, while
the owner, native package ID, object type and empty provider binding retain
their existing separate AAD positions. For source packages the digest is SHA-256
of the canonical JSON array `["offmenu-private-package-manifest/1", manifest]`.
`manifest` includes every closed-schema package field except `envelope`,
`checksum` and `manifestDigest`; it therefore binds issuer/subject, recipient,
consent ID/revision, exact scope, recovery reference, source/version and timestamp.
The required protection binding marker prevents accepting the previous draft's
unbound format. Recomputing either public digest cannot repair a changed GCM tag.
This is authenticated integrity under the existing custody key, not a signature
or new authentication system. No previous actual export is adopted or migrated.

All profile/health/clinical labels, content, typed source values, nested inventory
locations, item/lot/holding/quantity/movement records, settings, safe connection
history, attachments, relationships and extensions live inside the sealed
payload. The existing cryptor's 1 MiB plaintext bound applies. Attachments include
their actual encrypted-with-the-bundle bytes, exact byte lengths, checksums,
record relationship and provenance; source filesystem paths, remote download
URLs and bearer URLs are not accepted attachment fields. This version performs
no automatic chunking or external attachment acquisition.

| Kind | Implemented behavior |
| --- | --- |
| `privacy-access` | Owner-only decryptable typed access report. Field redactions are explicit nulls/coverage/warnings. It is rejected as restore input. This is not a formatted legal response or a compliance completeness claim. |
| `portability` | Profile, medical-plan, inventory and derived-provenance transfer with explicit rebinding. Extra settings/content/auth-history records are rejected. |
| `owned-backup` | Complete owned-data snapshot in this bounded typed format, including content/settings/attachment/relationship/history/derived-provenance coverage. `unavailable` coverage or a payload that differs from the trusted complete snapshot digest is rejected. Credentials, session material and effective grants are intentionally excluded from owned data. |

The trusted `backupInventory` is a complete, package-bound source snapshot
attestation and digest, not the caller's own completeness assertion. A restore
must retrieve that retained snapshot attestation for the selected package while
separately checking **current** consent and deletion/revocation state. A changed
live dataset does not substitute for the original snapshot. This implementation
does not provide that durable snapshot inventory service.

Typed references must resolve within the same owner/kitchen. Location ancestry
must be acyclic; an inventory space ID equals its kitchen ID. Quantities preserve
decimal strings to six fractional places, explicit unit/dimension/basis and
unknown values. Values/deltas are bounded to the existing fixed-micro-unit range.
No unit conversion, implicit quantity aggregation, medicine/order execution,
inventory movement replay or clinical acceptance occurs. Medical recommendations
retain their source and recommendation provenance, with clinical review required
on import. Source assertions and source-language values are preserved; this lane
generates English fixture/output text only and performs no translation.

Unknown attributes are accepted only inside encrypted, namespaced, versioned
`extensions[].value` objects. They are preserved byte-semantically as JSON values,
with source origin retained, rather than dropped or flattened into core fields.
Their unknown references are not interpreted or rebound. Extension field scope
is required when source extensions are exported. Structural secret-key exclusion
also applies inside extensions. This is not a DLP detector for secrets hidden in
arbitrary user prose: a later authorized source extractor must exclude secret
content before using these helpers.
Generic `token`, `oauthToken`, `secret` and `secretKey` keys (including case and
underscore/hyphen variants covered by the structural rule) are rejected recursively,
including inside nested extension arrays. Unrelated keys such as `tokenCount`
are preserved.

The source extension limit remains 100 per record; import never appends to or
truncates that list. Optional `record.importOrigin` has a separate strict version-1
shape with bounded source namespace, identity and record ID. The first import
creates it; subsequent imports preserve it without accumulating a history list.
It is provenance metadata, not verified identity or a transferable grant. Existing
source extensions, including older origin extensions, remain unchanged.

## Trusted adapter hooks

`createPrivatePortability({readAuthority, resolveKey, custody, clock,
atomicRestore})` returns `exportPackage`, `accessReport`, `planRestore` and
`commitRestore`. There are no routes, request handlers, DB handles or defaults
that activate these hooks. `resolveKey` is the **existing** BYOC trusted custody
callback. All callbacks and clock are server-owned, never request-supplied.

`readAuthority({operation, phase, packageId})` must freshly authenticate through
the existing verifier and read independently authorized storage. Export/report
returns one context. Restore returns `{source, destination}` with independent
contexts. Each context supplies:

* `principal.id`, `identity:{ownerUserId,issuer,subject}`, `namespace`, `revision`;
* `auth:{reauthenticatedAt,expiresAt,revokedAt}` in integer milliseconds, with
  reauthentication at most five minutes old;
* authorized `kitchens`, exact `allowedRecords` as JSON `[type,id]` strings,
  current independent `tombstones`, and qualified external `recoveryRefs`;
* a current `consent` with `id`, `revision`, `ownerUserId`, exact `recipient`
  identity, operation `purpose`, `fields`, `validFrom`, `expiresAt`, `revokedAt`
  and `choice:'granted'`;
* for owned backups, retained `backupInventory:{complete:true,payloadDigest}`;
* on destination contexts, existing imported `records:[{type,id,digest}]` for
  conflict detection, plus a revision suitable for a real transactional CAS.

Absence, mismatches, expiry, withdrawal, revocation and deletion deny processing.
An old package cannot create its own live source consent, destination grant,
verified identity, current tombstone view or key recovery permission. Source
consent must still match the package's exact revision; destination consent is
freshly selected before planning and is pinned by the plan. Fields can separate
allergy/diet/preference/diagnosis/display-name/medical-plan data. Nonpermitted
profile fields must be explicit nulls; restoring a whole profile requires its
actual field permissions, not just household membership.

The current source and destination authority must remain accessible. Offline
recovery without that independent source/revocation/key evidence is unsupported
and denied. A genuinely independent recovery mechanism must be qualified by the
trusted custody adapter before listing a `recoveryRef`; the manifest's
`sourceInstanceOnly:false` flag does not prove portable key recovery by itself.
Actual keys, credentials and activation remain unauthorized in this task.

## Restore and atomicity boundary

`planRestore` requires an exact destination object containing only `namespace`
and `identity`; identity contains only `ownerUserId`, `issuer` and `subject`.
Both shapes reject unknown properties. Structural secret exclusion applies
before any restore authority/key callback or decryption, including nested extras;
unrecognized/credential properties cannot be reflected into the plaintext plan
or intent. Accepted opaque identity strings are compared and retained exactly.

It also requires a complete
one-to-one source-to-destination kitchen map and a destination key reference.
Destination IDs are deterministic from the exact source instance/identity/type/ID
and destination instance/identity (`destinationRecordId` is available to a trusted
scope adapter). Kitchen/space IDs use the explicit map. Names are never identity
keys. Known internal record references, attachments and relationship endpoints
are rebound; original provenance, source extensions and first-import origin survive.

The destination payload is freshly reencrypted with the existing cryptor under
destination owner/object AAD. The restore manifest uses domain
`offmenu-private-restore-manifest/1` and covers the entire plan except its
`envelope`, `checksum` and `manifestDigest`, including source manifest digest,
destination identity, consent revisions, scope-derived operations and logical
content digest. It is computed before sealing and checked before commit.
Relabeling source ciphertext is rejected. All key
awaits are followed by fresh authority checks. A dry run performs validation and
cryptography only; it never writes records or calls the restore executor.
Conflicts are reported explicitly. Exact destination record digests yield
`skip-identical`; differing content yields `conflict`, with no implicit overwrite,
merge or normalization. Clinical records require review. Identity links become
unlinked evidence; connections require reauthorization. Auth/consent/connection
history and movements/waste are history-only and never recreate active grants,
sessions, entitlements, credentials or double-applied inventory movements.

`commitRestore` denies operation without a trusted `atomicRestore` callback and
a checksum capability issued by the **same** adapter instance after successful
planning. Its bounded 100-plan in-memory capability set is not a durable session,
job or task store. Restart/eviction requires revalidation and replanning. A
retained encrypted package remains the durable input.

The executor must independently authenticate and atomically re-read/fence the
source/destination consent and deletion state, compare the expected destination
revision, check content-bound idempotency, insert all encrypted records/bundle
relationships/attachments, and write its receipt in one transaction or roll back.
The hook receives the plan and expected revisions/authority digest. A later
revocation during any await must prevent commit/serve. A receipt replay is allowed
only for the same idempotency key and logical content after fresh authorization;
new encryption nonces or insert-versus-skip observations do not change logical
content. A single trusted transaction boundary across independent source/key
services is **not provided or qualified here**. No remote exactly-once/atomicity
promise is made.

The SQL proposal adds only scoped consent metadata, encrypted medical-plan
references, body-free immutable restore receipts and encrypted owned-import
record pointers. It reuses existing profile/consent/key/envelope/kitchen sources.
The receipt stores the restore manifest digest. It is inserted before its imports
in the same atomic transaction; the import trigger joins that receipt and requires
its digest to match the envelope's exact authenticated purpose, as well as checking
the native package ID, owner and empty provider binding. A wrong manifest cannot
be attached by merely relabeling a record pointer.
Medical-plan insert/update additionally requires the same owner's granted
`private_use` consent for object type `household_profile` and the exact profile ID.
Connection, other-profile, denied, withdrawn, contribution and sharing consents
do not authorize that private clinical-record write. This storage constraint is
not a substitute for fresh runtime expiry/revocation/read authorization checks.
Imported data lands in owned encrypted storage/history; no automatic materializer
into live stock/profile/auth tables is mounted. SQL constraints do not establish
read authorization, authenticate an issuer or replace the required transaction
executor. Actual profile/inventory UI restoration, safe retention/deletion replay,
live adapter implementation and real runtime qualification remain integration
work, with no activation permission implied by this source proposal.

Downloaded external copies cannot be recalled. Revocation stops future authorized
use through controlled adapters; deletion tombstones must remain independently
available across backup restoration. Restored consent history is evidence only.

## Generated verification and acceptance

Run from the exact granted workdir:

```sh
node --test tests-web/private-portability-v1.test.mjs
```

Tests exercise all 17 kinds, encrypted round trip and destination AAD, profile
field redaction, issuer/subject/tenant isolation, consent withdrawal/expiry and
revocation during key awaits, tombstones, checksums/attachments, cycles/dangling
references, quantity basis, unknown version rejection, secret exclusion,
no-write dry runs, conflicts, forged plans and content-bound idempotent replay.
Python's installed JSON Schema validator independently checks the pinned schema
and generated fixtures. Generated in-memory SQLite executes the source proposal
after its exact prerequisites, with FK/trigger/rollback tests. A generated memory
executor tests the callback contract's rollback/CAS/idempotence behavior. These
are not native D1, actual private-data, real encryptor custody, external recovery,
remote atomicity or deployment qualification.

The predecessor's 28 generated tests and seven existing BYOC tests passed. The
corrected suite adds three focused R1/R2 tests: 99/100 source-extension round trips
with independently bounded origin and exact destination-shape/secret rejection.
The existing auth-principal suite initially could not load `better-auth`.
The documented `npm ci --ignore-scripts --no-audit --no-fund --offline` setup
resolved that environment gap from the local cache without source/manifest/lock
changes. Its five principal tests then passed, recorded separately. The four
native D1/workerd tests in `tests-edge/better-auth.test.mjs` remain NOT_RUN;
no full auth/runtime qualification is claimed. Dependency setup is not repeated
for these R1/R2 corrections, and no mock package or auth-source edit is used.

Four PR106 regressions cover metadata forgery even after public digests and fresh
authority are changed together, generic extension credentials, exact clinical
consent insert/update scope, and raw URI syntax. URI validation follows the
[RFC 3986 Appendix A grammar](https://www.rfc-editor.org/rfc/rfc3986#appendix-A)
without WHATWG URL normalization, network resolution or identity rewriting.
Runtime controls check raw invalid spaces/controls, escapes, authority/IP-literal
syntax and accepted URI strings. Scheme-specific validity and IRI support are
separate. This environment's Python JSON Schema installation has no optional
`uri` format checker; that independent URI check is reported NOT_AVAILABLE,
not silently counted as passing. Metaschema/structural checks and the explicit
runtime URI positive/negative controls still run.
After those corrections the full private suite has 35 passing tests and the
separate BYOC suite has seven. The prior five principal passes remain separate
historical evidence; the four native authentication tests remain NOT_RUN.

No actual private records, paid models, provider calls, sessions, source-cache
reacquisition, denied diagnostic inputs, live jobs, additional workers or security
settings are used. Country ownership and all retained source/denial holds remain
unchanged. Exact freeze review belongs to Worker64; Worker00 alone integrates
and decides later schema/runtime execution under existing gates.
