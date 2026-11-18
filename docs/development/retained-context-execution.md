# Retained provider contexts: offline execution boundary

This Foo-only library processes one **already retained**, independently admitted
OFF or USDA Files product projection. It neither downloads an original nor
approves an input. The package has no CLI, timer, production request handler,
network client, credentials, legacy worker, or permissive default claim issuer.

## Inputs and effects

1. Reconcile the **same** provider, release, representation, cohort, shard and
   original operation. Check original producer and helper claims, checkpoints,
   final-file/receipt pairs and unresolved effects. Preserve old cursor and
   partial files. Missing process/lock rows are only point-in-time observations.
   Do not treat “planned, not read” as an expired claim or mark its helper complete.
2. An authenticated issuer must reserve this exact operation and generation,
   register the private source and output directory identities, verify rights
   for this specific processing operation, reserve the maximum bytes/resources,
   and hold its fencing mechanism through every actual read, reconciliation
   (including private prior outputs) or commit. The finite lease must remain
   valid through the externally enforced hard job deadline, and ownership must
   not transfer during a held effect. Never
   mint a local grant, edit an expired claim, or use an unenforced lease check.
   A new generation must explicitly reconcile its predecessor; this library
   refuses to appropriate the original generation's output. A scoped sandbox
   that excludes the corpus root is **not** a substitute processing route.
3. Supply the exact queue, assignment, cohort receipt, cohort index, global
   index and compressed-shard fingerprints. Bind full SHA-256, size, device,
   inode, mtime and ctime, parser version, rights and the exact source count.
   Use an independently checked immutable **index** fingerprint; do not rehash
   a large global index per shard, trust a path in a queue, or substitute an
   original publisher asset for a staged representation. No fetching or automatic
   fallback exists when a binding is missing. The runner re-verifies the
   selected compressed shard, the line digest before decoding its body, local
   and global row bindings, rights, and barcode postings. It bounds decompressed
   input, rows, row size and the cumulative output.
4. The first release-bound provider/shard owns its private output namespace.
   An exclusive directory lock spans the operation; the authority guard separately
   fences every effect. Durable segments use file fsync, atomic no-overwrite
   link, directory fsync and a hash chain. A restart verifies each complete
   segment before accepting progress. A missing receipt after final-segment
   installation is repaired deterministically without re-running the consumer.
   Uncommitted work may be computed again; earlier committed semantic output
   is never appended twice. Corrupt/mixed segments, conflicting bindings,
   unknown existing files or too many crash temporaries stop processing.
   No legacy partial is truncated. Temporary artifacts may survive a process
   or machine failure and are not silently admitted or purged.
5. Independently verify the terminal count/hash, rights, scope, and output.
   One provider's completion does not close another provider or its consumers.

## Resource plan and rollout

Use the existing admitted, resource-aware Foo supervisor, not another queue.
Do not run the historical all-domain database-normalization command to process
a single provider. Start with **at most one shard per independently admitted
provider**, two lanes only after both admissions permit it. Allocate CPU, RAM,
read I/O and total private output per operation using measured sample sizes and
the full temporary/immutable-space allowance. Check available headroom **at
admission**; configured worker ceilings and a quiet prior sample are not free
slots. Bind the entire CPU/memory/I/O/private disk/timeout/worker declaration
into the immutable operation key; require the supervising host to enforce it.
For an initial measured shard, a candidate request is one worker, 1,000 CPU
millis, 2 GiB RAM, one I/O slot, 2 GiB private disk and 900 seconds: **not**
a reservation or a promise that a slower cold index check fits the deadline.
Serialize any new large-index verification and reuse a qualified immutable
identity across eligible readers. Share only immutable index reads, not writer cursors. Scale independent
shards only when measured memory, I/O, output, deadlines and current ownership
support them. No new cadence is created here.

## Static delivery, not a runtime provider client

- If permitted, provider acquisition or translation belongs only to a separately
  scheduled Foo build with a specific provider, interval, accepted authority,
  terms, and budget. This offline retained stage performs neither operation.
- Version the built static assets and data by immutable source, parser and build
  identities. Carry source attribution, rights, uncertainty, source-language
  evidence, and explicit nonpublication state. This runner's source-bound
  receipt is **not** public-distribution rights, a translation, a Gold decision,
  a publication manifest or a go-live instruction.
- The application should read only separately approved static data. Provider
  citations are explicit user-initiated links, not background fetches, CDN
  embeds, prefetches, translation calls or tracking. No live interface, browser
  or distribution path is activated or certified by these synthetic tests.
