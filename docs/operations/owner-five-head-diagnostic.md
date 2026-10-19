# Exact-five owner HEAD diagnostic: inactive review package

Status: prepared and tested; activation is unselected. No source request, owner-machine access, publication, GET retry, or custody change was performed to prepare this package. The earlier inactive HEAD proposal remains unchanged.

## Smallest activation selection

Select one owner-run, read-only HTTP observation pass for the five original URLs already pinned by this manifest, under existing handoff `owner-local-comprehensive-20261018-002`. Allow at most one HEAD per source, five total, no redirects or retries, and zero application body reads. Allow only a sibling private diagnostic ledger with a durable attempt marker and sanitized result. Keep the existing dispatch hold and every failed GET intent unchanged.

This is a distinct observation authority. It does not select GET reacquisition, signed-target requests, parsing, source-intent reset, custody promotion, hold removal, new owner runtime, automatic publication, or a `003` handoff. Those authorities remain unselected.

The supplied activation JSON has `selected: false` and `diagnosticLedgerWriteApproved: false`. The implementation also has `ACTIVATION_SHA256 = None`, so the CLI returns `diagnostic-inactive` before owner-local I/O or process creation. Both barriers are intentional. After parent review and explicit selection, the smallest patch sets those two JSON booleans to true and pins its canonical bytes in `ACTIVATION_SHA256`. The active JSON must exactly match the closed activation schema; environment variables and command-line overrides cannot activate it. Use the reviewed source inventory for installation; do not alter the old 002 runtime/hold files.

Prospective selected activation SHA256: `a275ce332a340b4e2eb735860f2caf9cd437edc7b74854faeaf4768b5cee5baf`.

## Exact evidence and live prerequisites

- Baseline source: `5e7f4673e78b1f677c69a1ed48a36d24e2692a90`.
- Fresh fetch result: `2471124b16b770c9bbebee536a2b0bf4a809f5338c2ab523b58cbd97ba780816`, published report commit `bd378c69e2bbc90c4205b34497a39ffdae7b5b68`.
- Third-run failure result: `c36d6a2f8a34ad71e77d11f9bed89957cdde002d0e1820da4b4d0c1215f8556d`.
- Source-bound manifest: `6ae3989bc83a05abb60713e595d392f26efa2682ef7d470943b92c56706f50a1`.
- Sources: `so-wfp-markets`, `so-wfp-metadata`, `so-wfp-prices`, `pg58-plos-0184279-s001`, `pg58-plos-0184279-s002`.

The immutable manifest pins the exact source contracts, original URL hashes, old/fresh asset rows, published receipts/verifications, existing 002 runtime/hold, baseline acquisition/intake modules, old/fresh detail identities, and source/downstream holds. The five expected failed-intent hashes are derived from the reviewed original execution contract. They are not a claim that live owner files have already been inspected. In particular, the original execution carries diagnostic pin `4be1b7b1703617e29a67e4cc7d4265452ef30d990101200679ac2a01eae96f4b`; temporary validation slices do not change that execution provenance.

At execution, real and effective UID must both be 1000. Before any request, the existing owner `latest-fetch` pointer and exact fresh-result envelope, all five old detail records, all five fresh blocked detail records, and all five failed intents must match their pins and closed semantics. Missing or mismatched evidence blocks the entire pass. The current native claims root must be readable and current source claims must pass the unchanged `OwnerRuntime.admit` checks. Existing 002 handling of unavailable historical runner roots is reused under its unchanged hold; no new empty-catalogue assumption is introduced.

The existing `collection/fixed-selection.lock` is opened without creation/truncation and held through the complete pass. Guarded owner metadata uses no-follow descriptor traversal, private ownership/mode and hard-link checks, bounded reads, byte hashes and inode rechecks. Source originals, partials, provenance and reservations must remain absent. Current claim admission and metadata/lease/ledger identity are checked before and after each observation. This module does not construct `OwnerRuntime` through its mutating initializer.

## Transport and bounded cleanup

`scripts/diagnose-owner-five-heads.py` is the only reviewed owner entrypoint. It starts a single-threaded POSIX fork supervisor with a 90-second aggregate deadline including guard I/O, DNS, connection, TLS, header reading, result serialization and cleanup. Each source has a separately supervised 15-second bound with cleanup reserve. A blocked DNS/connect/TLS/read/close cannot bypass that deadline. No spawned-process serialization gap is used. The outer supervisor kills the entire worker process group before reaping its leader, including timeout, pre-readiness and abrupt-owner-exit cases. Ordinary returns require verified child termination. An OS failure to verify cleanup is terminal, never a retry authorization.

The transport sends the original exact HTTPS target with HEAD, identity encoding and connection close. It performs one DNS resolution and one connection attempt without address failover; it does not use a proxy, cookies, authentication, ambient HTTP clients or redirect handlers. Certificate and hostname validation remain enabled. TLS application reads request exactly one byte, stop at the final header terminator, and never call a body API. TLS may internally process encrypted records; this is not a claim that no encrypted record contains additional application data.

All informational and final header sections share one 65,536-byte envelope. At most 100 final fields are accepted. Duplicate headers and trailing value whitespace are preserved for comparison with the existing validators. Each safe observation is capped at 12,000 bytes; overall reports and each IPC stream are capped at 65,536 bytes, including message framing. Excess data fails closed.

## Safe output and its meaning

Raw header values remain only in the short-lived transport worker. The worker disables core dumps and redirects both native and Python stdout/stderr. Only a closed, revalidated metadata schema crosses to the owner coordinator. Unknown header/query names and unreviewed hosts are hashed. Output contains permitted names/counts, value lengths, validation codes, method-specific status, and redirect host/origin plus hashed path/segment/length/query-key shape. It never contains raw paths, signed URLs, query values, cookies, other header values, raw logs or exception strings.

`Vary` remains descriptive (`unsupportedVary` can be true). The already selected private-save Vary correction is preserved. The shared HTTP-cache retention policy, encoding rejection, critical duplicate/length/framing checks and exact source/redirect contracts are unchanged. A HEAD success cannot explain the prior GET failure, permit a redirect, authorize a new GET or clear an intent/hold. HEAD 401/403/407/451, 429 and method denials remain held.

## Crash-safe at-most-once ledger

After all five sources pass preflight, one private immutable marker consumes all five source slots and is fsynced, followed by directory fsync, before the first HEAD. Its inode/hash is rechecked with other protected metadata. Any existing, partial, corrupt or uncertain attempt marker blocks another pass. A crash can therefore consume unused observations; it never enables a retry. No existing source GET intent is changed.

The ledger lives in `head-observations` beside `collection`, outside the existing source-claim scanner. Only the new ledger directory, immutable attempt marker and immutable sanitized result may be written. A successful stored result has `ledgerResultSHA256: null`; the returned report supplies the hash of those stored bytes, avoiding a hash cycle. Incomplete coordinator reports may be returned without a stored result; the consumed marker remains decisive. Interrupted outer supervision conservatively reports up to five unknown attempts and unknown metadata stability, never zero requests by inference.

## Review and execution remaining

1. Parent reviews the frozen additive inventory, tests and this authority selection.
2. Parent explicitly selects the bounded observation authority, then prepares the narrow activation patch described above with the exact selected JSON hash.
3. Install only reviewed source; verify the current 002 hold/claims and live pinned evidence through this entrypoint. A mismatch must be reported, not repaired or bypassed.
4. If selected, run once and review its safe metadata. Any GET successor, redirect target, parsing or hold disposition requires its own source-bound review.

All implementation tests use synthetic metadata/socket/process fixtures. No real HTTP or owner-runtime access is part of the test run.
