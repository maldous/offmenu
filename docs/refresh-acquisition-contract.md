# Bounded cache-aware acquisition contract

This is an opt-in acquisition library, not an enabled global source campaign.
It has no AI runtime and does not interpret source bodies. No production source
is registered by this change, and no real download is part of its validation.
Baseline: develop `2266e85046eb22d5baccba09149c0f3b70dadd25`.

## API and authority boundary

`CachedAcquirer(cache_root, sources, transport=None, retries=2, resource_budget=None).acquire(source_key,
fetch_policy='reuse', now=None)` returns `AcquisitionResult(path, sha256, bytes,
status, provenance)`. `sources` must be reviewed application code/configuration,
not arbitrary user-supplied CLI URLs or discovery results. A mapping member is a
frozen `SourceSpec(source_key, url, policy_fingerprint, rights_reference, ...)`.
`enabled` and `rights_approved` default false; `held` blocks even cache reuse.
The registry contains no implicit source admission. `policy_fingerprint` binds
reviewed operation policy; a rights reference is evidence, not a rights inference.
This adapter supports only public retention scope; restricted scopes fail closed.
Finland/manual-source holds and native normalization crashes remain unaffected.

## Modes and timestamps

- `reuse`: hash-verify and reuse fresh bytes; never access the network. Missing or
  stale bytes fail explicitly.
- `refresh`: reuse fresh bytes; otherwise request conditional validation with
  ETag and/or Last-Modified when retained. Without validators, download a bounded
  complete representation.
- `revalidate`: explicitly contact the allowed source even during freshness,
  retaining conditional validators.
- `force-download`: explicitly contact the allowed source without validators.
  This does not override a gate, expand authority or guarantee changed content.

Local forced normalization/rebuild is a separate harness option and does not
translate into any acquisition policy. `ttl_seconds` cannot be below 30 days.
Original body acquisition time is `originalAcquiredAt`; successful validation time
is `checkedAt`. A matching 304 or identical 200 preserves original acquisition
provenance while refreshing scheduling from `checkedAt`, avoiding repeat network
validation on every run after the original body reaches 30 days. HTTP no-cache or
short max-age restrictions can make reuse ineligible earlier; automatic refresh
then defers until the minimum window ends. Only explicit revalidate/force-download
can contact the publisher earlier. No-store/private
responses are rejected. Unsupported Expires/Age semantics conservatively remain
stale. The existing offline fixture policy's acquisition-age report is unchanged.

## Cache and recovery

Requests are keyed by source key, exact URL, release, acquisition version,
representation, reviewed policy and rights reference, bounds, and scope.
Country identity is deliberately absent. One request key may serve all 249
country consumers without duplicate downloading. Country applicability is never
inferred by this module. Complete bodies are SHA-256-addressed once in the public
cache. Every reuse verifies actual bytes, size, and matching immutable evidence; ETag is never a content hash.
Immutable evidence is stored separately from the mutable current pointer.
A recovery receipt safely restores a fully received, hashed object after a crash
between evidence publication and pointer update. Partial transfers are discarded
and restarted, never appended. Range resume and paginated API snapshots are not
implemented. An interrupted transfer cannot be reported as complete.

## Transport bounds and deliberate limits

- Standard-library HTTPS with exact reviewed public GET/query or read-only JSON
  POST contracts; no redirects, cookies, credentials, proxy discovery, custom
  ports, caller-defined headers or decompression.
- Only fixed reviewed exact locators; no URL expansion, alternate hosts or
  fallback source requests. Request header is Accept-Encoding: identity, plus
  applicable validators.
- Default transfer budget is 64 MiB. Reviewed source-specific byte limits can be
  larger only with an explicit runner-owned ResourceBudget matching the exact
  cache storage root. This gate precedes cached-body hashing as well as network
  access. This supports streaming files, not archive extraction,
  decompression or paginated source semantics. The runner must establish the
  approved execution host (Foo for large payloads), storage root and resource
  budget; a string saying Foo is not identity proof. No cloud large-payload
  transfer was performed or authorized by these tests.
- ResourceBudget(storage_root, max_transfer_bytes, minimum_free_bytes=64MiB,
  max_seconds=600) is bounded at 1 TiB cumulative transferred bytes and 86400
  seconds. Default without a policy is 64 MiB and 180 seconds. Count transferred
  bytes across retries, including discarded partials. Check available disk for
  source limit plus reserve before networking and remaining reserve each chunk.
  Stream chunks of at most 1 MiB to disk, never buffer the whole body.
- Socket operations timeout at 30 seconds. A cumulative walltime deadline covers
  requests, reads, retries and backoff. A daemon watchdog shuts down the active
  socket at the deadline, and HTTP reads use read1 to avoid read(size) looping.
  Check the deadline again after every read including EOF. Blocking system DNS
  resolution is outside the socket shutdown guarantee; deployment must supply a
  bounded resolver/network boundary. No claim of end-to-end live network QA.
- Two retries by default, at most three; backoff capped at four seconds. Only
  429/500/502/503/504 or interrupted/time-out transfers are retried. Redirects,
  authentication, forbidden/challenge and other responses fail without retry.
  Retry-After is honored; publisher delays above the bounded backoff defer the
  operation rather than issue an early retry.
- A nonblocking global cache lock allows only one acquisition per cache at once,
  bounding host load and duplicate concurrent retrieval; lock contention fails
  explicitly for caller retry. Multiple independent cache roots do not share a
  host budget and must not be used to bypass this limit.
- Cache record reads are capped at 1 MiB. Headers are bounded individually.
  Only nonsecret representation/cache validator headers are persisted.
- No native parser, normalization, output qualification or country acceptance is
  enabled here. Source adapters, policy approvals, large payload acquisition,
  signed/credentialed URLs, restricted storage, and actual global coverage remain
  separate completion requirements.

## Validation

Synthetic response fixtures only, with no socket calls: 36 unit tests covering
30-day boundary, 249-consumer deduplication, validators, immutable acquisition
age versus validation freshness, denied sources and scopes, corrupt/missing
bodies, interruption recovery, retry bounds, response-size restrictions,
retention directives, secret-header exclusion, symlink rejection, immutable
evidence tampering, publisher Retry-After, cumulative transfer and disk budgets,
large-source configuration gates, and post-EOF walltime enforcement.

## Pinned raw collection selections

The existing `scripts/collect-source-access.py OUTPUT` retains its legacy landing
access mode. Actual raw collection is explicit:

```sh
python3 -B scripts/collect-source-access.py REPORT_DIRECTORY \
  --collection-registry /absolute/reviewed-selection.json \
  --registry-sha256 EXACT_REVIEWED_SELECTION_SHA256
```

This invokes `offmenu.refresh.acquisition.collect_registry`, using the same
`CachedAcquirer`, locks, content-addressed objects and recovery receipts. It
does not invoke host bootstrap, source parsers, fixture admission, normalization,
AI, or gold/publication. The hash identifies configuration; it grants no rights.

The backwards-compatible selection schema `offmenu-acquisition-selection/1` has
exactly five fields:

- `resources`: `storageRoot`, `maxTransferBytes`, `minimumFreeBytes`, `maxSeconds`.
  The caller qualifies actual execution host and storage separately. Byte and
  deadline limits also apply across the batch, including failed network reads.
- `sources`: entries with `spec` (the existing `SourceSpec` fields), `operation`,
  `claim`, `holds`, `retained`. Operations are `https-refresh` or `retained-copy`.
  A claim is `{owner: 0, state: "selected", evidence: {path, sha256}}`: this
  bounded runner is currently assigned to existing Worker00. Other-owner claims,
  explicit holds, unapproved sources and unsupported operations fail closed.
  The operator must reconcile actual competing claims before selection; this
  local check does not replace Gateway's allocation authority.
- `bindings`: `{sourceKey, country, type, evidence: {path, sha256}}` edges. Multiple
  countries/types share a single source entry. Duplicate representation aliases
  are rejected; duplicate edges are rejected. All selected sources need an edge.
- `evidence`: exact local `{path, sha256}` pins binding current source-use,
  custody and selection contracts. Evidence and applicability are verified before
  acquisition; content interpretation is outside this operation.
- `schemaVersion`: the schema name above.

Country inventory57's `all249-source-collection-v2.json` and its current-report
caveats are reviewed metadata intake, **not** a runtime acquisition registry or a
universal download grant. Copying inventory rows into a selection cannot qualify
rights, source release, payload completeness, actual custody or competing claims.
NZ/LK unresolved provenance and active acquisition claims remain separate holds.
Current source-specific budget decisions must accompany the relevant selection;
one source's approved budget does not authorize another source's transfer.

`retained-copy` supplies exactly `path`, `sha256`, `bytes`, `originalAcquiredAt`,
`headers` and `evidence`. Only the bounded nonsecret retained-header allowlist is
accepted. Import checks exact existing original bytes and pinned custody evidence,
streams a verified local copy and uses no-overwrite object promotion. Its receipt
uses `result: retained-import` and `retainedOrigin`, preserving the original
acquisition/validation timestamp. Local verification time is separately recorded;
it never creates a new 30-day window. Existing HTTP retention restrictions still
apply. A stale retained selection fails offline; no fallback download is inferred.
The canonical public source URL identifies provenance, never a historical signed
transport URL. Source receipt pins preserve the original provenance without
copying credentials into reports.

Each source checkpoints an immutable report plus `collection-report.json` before
the next source. Failure is isolated and recorded; rerunning re-verifies cache
bytes and resumes completed objects. Partial copies/transfers restart, never
append. Existing serial cache locking remains; no new concurrency cap, background
controller, claim allocator or scheduler is introduced. Evidence paths must be
stable for a run. Whole-selection structural/pin errors fail before any request.

Reports distinguish verified local originals, failures, applicability edges,
actual network requests/body bytes and original acquisition provenance. They
explicitly report zero parsing/normalization/gold admission and do not infer
country completion. `retainedImportStatus` separates first local import from an
already cached repeat. The CLI returns nonzero for a rejected selection or any
failed source, while retaining the complete per-source report.

The orchestration tests cover many-to-many deduplication, unchanged repeat,
conditional due refresh, held/forbidden isolation, aggregate byte bounds, stale
retained age, original/cache corruption, claim and evidence failures, and safe
restart. Live retained-copy acceptance is recorded outside Git in the exact
worker result packet; synthetic HTTP tests do not establish live provider access.

## Historical descriptors and reviewed request extensions

`offmenu-acquisition-selection/2` adds exactly `assetCatalog` to v1's five fields.
The catalog is `{version, assets, requirements, evidence, qualification}`. Each
asset has exactly these fields:

```text
assetId, kind, publisherCitation, request, release, datatype, format, destination,
integrity, budget, holds, reuse, purpose, actualScope, localEvidence, provenance,
sourceKeys, unresolved
```

Unknown fields use null or an explicit unresolved list. A catalog descriptor
does not become executable: `sourceKeys` binds exactly the selected `sources`,
with no duplicate or missing executable binding. Other historical originals,
supporting/failed/derived metadata and desired citations retain distinct kinds.
`requirements` rows are `{country, type, assetIds, status,
coverageQualification, evidence}`; absent asset links remain absent. Registry
version and exact SHA identify a run; ledger results separately bind that identity.
Catalog evidence is pinned local metadata, not fresh proof of raw-file presence.

```sh
python3 -B scripts/collect-source-access.py METADATA_OUTPUT \
  --collection-registry REGISTRY --registry-sha256 SHA --describe-registry
```

This opens metadata only, writes `registry-summary.json` and the sanitized
`unresolved-descriptors.json`, and performs no acquisition or raw-body hashing.
Counts distinguish declared local descriptors, desired citations, recorded
locators, publisher citation metadata and unresolved descriptors. Publisher
citation counts include documentary citations and are not counts of qualified
original custodians. Requirement edges report declared mapping presence, not
semantic acceptance or full coverage. The current metadata reports deliberately
retain `mappingComplete: false` and `countryComplete: false`;57 reconciles actual
coverage and missing owner/provenance evidence.

`SourceSpec` now optionally accepts `query_keys` (default empty),
`request_method` (default GET), `request_body` (default empty) and
`public_read_only_post` (default false). Existing default GET identities remain
byte-compatible. Query keys must match the exact reviewed URL, be unique and
exclude credential/token/signature keys. Query values are never expanded.
POST requires an explicit reviewed public-read-only assertion and a canonical
JSON object body of at most64KiB. Credential fields, arbitrary methods, request
headers, redirects, signed URLs and automatic pagination stay unsupported.
The exact POST method/content-type/body/read-only policy binds cache identity;
different queries/bodies cannot reuse a different response representation.
The transport sends the exact public query/body to the exact fixed HTTPS host.
These fields qualify a reviewed static contract, not arbitrary interactive API
access; all existing gates and holds run first. Multi-document/paginated sets
must remain explicit pending contracts unless each exact reviewed member is
separately selected. No MK/MAKSTAT claim or transfer is taken over by these tests.
