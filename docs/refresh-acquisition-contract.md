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

- Standard-library HTTPS GET only; no redirects, cookies, credentials, proxy
  discovery, query strings, custom ports, custom headers or decompression.
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
