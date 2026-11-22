# Opt-in OFF partition custody adapter

This source-only adapter wraps the accepted occurrence partition core. It adds
no source registry entry, CLI, real operation factory, executor, resource grant,
normalizer, consumer schema or publication/cleanup framework. Existing clean
witness/default behavior and historical outputs remain unchanged. Validation uses
generated original gzip files and generated metadata only.

`partition_retained_original(operation, evidence_root, original_root, destination,
limits=...)` requires an exact typed `PartitionOperation`, `ImplementationPins`
and `CustodyLimits`; all cooperative limits are explicit. These are reviewed
application constants, never loaded from source/cache/discovery JSON. Supplying a
dataclass or computing its fingerprint does not make a selection independently
reviewed or authorize execution. There is no real-source constructor here.

## Selected evidence and authority

The trusted operation selects the original relative path, exact compressed bytes
and SHA, release/scope, full source row denominator, four metadata assets, reviewed
operation rights, implementation source pins, holds and fixture designation.
Only source `off`, table `products`, full original occurrence partitioning and
private output are supported. The required operations are `retain`, `parse` and
`transform`; their reviewed decision comes from application code. Rights file
text/hash is evidence, not a permission parser or grant. Any operation hold or
missing required permission fails before original access.

The evidence root contains exactly the distinct rights, scope, clock and
independent selection files, each bounded to 1 MiB. The original root is separate;
only its exact selected original is opened, without root inventory, fallback,
copy, extraction or cache reuse. Destination must be outside both roots and must
not exist. Symlink components and nonregular selected assets fail closed.

The adapter reuses the reviewed descriptor-buffer metadata protocol. It verifies
the exact size/SHA and path/open-file identity before parsing those same bytes.
Scope binds source/release/scope, original, rights, unknown-clock evidence, full
source denominator, gzip/UTF8/JSONL/LF framing, complete ordinal S/C/Q policy,
explicit cooperative limits and executor requirements. The separately selected
selection asset binds that scope SHA, original, rights/clock, row denominator,
permitted operations, implementation pins and fixture flag. Additional or
mismatched scope/selection fields are rejected. This prevents adopting a changed
source manifest as the selected operation; it cannot establish the independence
of the caller's selected pins. A future application factory must derive them
from accepted external scope/provenance/review, never from produced partitions.

The clock follows the existing retained-product schema, bound to this exact
source/release/scope, original and rights, with a basis-evidence SHA. Only
`unknown-retained` with `originalAcquiredAt:null` is supported. Neither filesystem
timestamps nor run time become an acquisition date. The basis reference and
rights/provenance interpretation still require external review; syntactic hashes
alone establish no source-use authority.

Implementation pins select this module, accepted partition core and reused
original/metadata protocol source files. Entry and postchecks must match them.
These source-file observations are not proof of loaded executable/runtime
identity. The reviewed executor must separately pin and qualify that runtime.

## Original descriptor and complete traversal

The existing `_VerifiedOriginal` opens a no-follow/nonblocking regular descriptor,
checks path/open-file device/inode/size/mtime/ctime agreement and enforces its
deadline around reads. The same held descriptor is SHA/size verified before
traversal, used by `gzip.GzipFile`, then rehashed after complete gzip EOF before
the core may finish. Gzip CRC/ISIZE, concatenated members and full compressed
stream EOF are validated by the standard library; corruption/truncation or
trailing non-gzip data fails. The input is never copied into another corpus.

Bounded raw decompressed lines pass unchanged to the accepted core. No row is
filtered, coerced, decoded/re-encoded or renumbered here. The core checks LF,
strict JSON, row/line/expanded caps and the selected full denominator, then emits
every ordinal in S/C/Q with every repeated-key member held and no primary chosen.
Declaration/count agreement alone is not source custody or scope authority.

Metadata is reverified at complete traversal and after the core returns. The
held original's identity is checked again after core publication, preserving the
pre/post hash identity across evidence generation. The overall cooperative
deadline includes preflight/hash/traversal/postchecks; the core's own selected
deadline remains additional. A blocked read or SQLite call still needs an OS
boundary. The intended source workload is two full compressed SHA passes plus
one gzip traversal; expanded metadata generation and independent output review
have their own costs. No real resource envelope is inferred from fixtures.

## Receipt, publication and retained resources

Only complete adapter success returns a SEPARATE in-memory custody receipt. It
binds the typed operation and selected evidence/code pins, observed source file
identity/size/SHA, full gzip traversal and the exact returned core-result value
via `returnedPartitionResultSha256`. `originalFileCustodyVerified:true` describes
that selected file protocol, not rights, independent selection or acceptance.
The core's on-disk result retains its original `sourceCustodyVerified:false` and
other unqualified flags. The adapter does not rewrite it or publish a durable
custody receipt. The existing owner must retain a successful returned receipt
through the existing evidence/ledger route and arrange independent output review.
That returned-value hash alone does not revalidate a mutable output pathname or
establish derivation authority. Consumers must verify current core directory/
file identities and all evidence hashes against the selected successful receipt.

Late source/evidence/code/deadline failure may occur after core publication. It
returns no custody receipt and leaves the unqualified core evidence intact.
`partition_custody_state` reports pre/post hash/traversal observations, whether the
core returned and any unqualified output location. Core retained-state metadata
is preserved on the exception; after a late failure it includes the returned
scratch obligation. A core `result.json` found on disk is never proof of complete
adapter success. No automatic retry, rollback, deletion or destination reuse is
performed. Reconcile exact retained state before selecting any continuation.

The accepted core's limits remain explicit: caller-qualified serialized Linux/
default SQLite descriptor attribution, with observed concurrency/ambiguous FD
delta refusal; no arbitrary threaded/custom-VFS/hostile callback guarantee.
Publication uses post-rename point-in-time attestation, not prevention of movement
or indefinite path custody. Scratch database remains ACTIVE on success/failure,
outside published evidence on success; created/connected inode aliases represent
one file and must be charged once. Safe quiescent owner disposition remains
separate. This adapter neither qualifies an executor nor releases that storage.

Every returned receipt keeps `accepted`, `runtimeQualified`,
`realResourcesAdmitted`, clean-scope eligibility and country completion false;
expected accepted record/ID bindings stay null. Core singleton product/profile
digests remain candidates. No product semantics, English/gold, field provenance,
partition normalization, PR72 derivation factory or real corpus admission follows.

## Remaining real operation and review prerequisites

Existing owners must select independently reviewed OFF-specific rights, source
provenance, unknown-clock/basis and full-denominator scope, plus exact adapter/
core/runtime/executor and destination. A real typed application factory is absent.
Actual partition G/S/C/Q/memberships/product IDs remain unobserved. No historical
filtered count or subset becomes an oracle. Preserve the original denominator
and separately reconcile prior full-witness accounting under independent review.

A source-bound resource plan must include compressed/decompressed IO, DB/index
and retained scratch, all output files and receipt bytes, Python/native SQLite/
gzip memory, CPU/walltime, file/inode limits, available capacity and concurrent
commitments charged once. These values, actual OS boundary and real operation
admission remain unset; a cooperative cap or self-hashed plan is not a grant.
Worker57's existing qualification/runtime/session remains untouched. the product maintainer
selects fresh appropriate56/64 source/evidence review; the product integrator alone integrates.
All source/privacy/custody/denial/incident10230/production/CIX holds remain.

## Generated verification

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests python -B -m unittest test_off_partition_custody test_off_partition_witness test_product_input_witness -v
```

Controls cover exact selection/rights/clock/code binding before original open,
one held source descriptor and two full SHA passes, full ordinal partitioning,
no payload copying, wrong hash/size, symlink/FIFO rejection, replacement/in-place
write, gzip CRC/truncation/trailing data and concatenated members, strict framing/
denominator/caps, late deadline/source/evidence failures with unqualified retained
outputs, no original-root inventory and no automatic deletion. They use generated
fixtures only and do not qualify any actual original, executor or resource plan.
