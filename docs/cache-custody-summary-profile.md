# Retained-cache custody reconciliation

Baseline: `5cfb4f7d4346b06d58b82ec7d3e2c8dd5d5fedb3`. Control remains `160bd4db49faa46636fd27d70cc3d65557f5f2fb`. Reuse existing run `39091957512`, job `global-readiness-20261018-001`; this work does not dispatch another job.

## Established and missing evidence

- Historical inventory contains 22 releases with 21 handler-bound release entries, not necessarily 21 distinct parser files. Historical mappings record rights claims, not present permission or acceptance.
- The existing runner verified nine selected Norway/France files totaling 30,623,126 bytes. The attached JSON copies their observed hashes/sizes and read-only status. Norway and France have matching acquisition/prior-manifest provenance, but both original acquisition dates are unknown.
- The existing runner view does not expose the retained 171 GB dataset tree. Finland's two selected metadata files are missing; its manual-only hold remains. Other releases have no demonstrated runtime custody.
- Eighteen retained manifest paths are explicitly named by pinned historical reporting code. Four newer release paths remain unresolved rather than guessed. Path declarations establish candidates, not current existence/access.
- The pinned next-national acquisition receipt contains eight artifact hashes/sizes (NZ, Sweden, Finland), but no download timestamps. Filename dates, release dates, normalization completion dates and filesystem mtimes must not be substituted.
- Historical handover pins include small composition and worker-summary receipts plus Danish, Finland, Norway and France manifest metadata. The 5,950,633-byte curated blob manifest is recorded by hash only and excluded from the bounded first pass. Worker outputs remain evidence claims, never permission to execute.

## Planned single-batch read-only summary profile

This is a proposed profile, not an installed job or access grant. It must be reviewed and pinned before use. It must not run an existing collector or the historical reporting script, which reads normalized rows.

1. Consume this immutable candidate index and the existing sanitized run receipt. The default phase reuses existing evidence without opening or rehashing raw assets.
2. For already authorized metadata paths only, open exact files relative to the existing read-only cache root using anchored directory descriptors and no symlink following. No recursive traversal or discovery of arbitrary payloads. Missing, unreadable, unsafe, over-limit and unknown pins remain distinct outcomes.
3. Strictly parse JSON metadata only: reject duplicate keys/nonfinite values; at most 64 KiB per approved small metadata file, 2 MiB total, bounded file count and runtime. Reject oversized indexes rather than silently truncating them. No archives, spreadsheets, source JSON rows or normalized rows.
4. Compare exact byte hashes and sizes when pinned. Keep byte digest separate from legacy payload-digest fields. Join source/release identity and declared artifact hashes without opening their payloads. Report `declared-only` for unverified artifacts, never `verified`.
5. Admit an acquisition timestamp only from an explicitly identified original-download event tied to the same artifact hash and a timezone-bearing timestamp. A general `fetchedAt` inserted by a normalizer is insufficient. Conflicts or absent evidence remain `unknown`. An age beyond 30 days is a policy-review flag, never a download trigger. Reuse existing artifacts for at least 30 days; unknown age blocks automatic replacement.
6. Emit only an allowlisted compact summary: candidate ID, source/release, accessibility status, digest/size match state, provenance state, original acquisition date or null with evidence locator, rights-claim state, hold state and missing-evidence reason. No source contents, raw rows, arbitrary errors, credentials or payload copies.
7. Stop on scope violations and retain all source holds, production/CIX pauses and native-crash no-retry state. There is no download, upstream revalidation, permission modification, new mount or execution fallback.

## Smallest access gap

Existing selected metadata is readable in the runner's current namespace. The remaining explicitly indexed small manifests/acquisition receipts would need their own reviewed exact-path read-only metadata grant if their metadata cannot first be recovered from repository/handover records. Do not request a broad data-root bind or copy inaccessible content as root. Four unresolved paths require documentary identification first. A future grant must preserve held-source boundaries and exclude raw bodies, credentials and the oversized blob manifest.

## Verification performed here

Local reconciliation asserts 22 release entries, 21 handler-bound entries, nine inspected selected assets and 30,623,126 selected bytes. Reads were repository code and small retained metadata only; no Foo job, raw dataset read, network source fetch, GitHub write, mount or permission change occurred. This profile is documentary and has not been executed on Foo.
