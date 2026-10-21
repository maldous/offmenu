# Private native Dietary importer

`offmenu.refresh.dietary_native_store` imports one explicitly selected LOCAL
native USDA/OFF singleton-packet JSONL artifact into a NEW private SQLite DB.
Worker56 owns this source; Worker13 remains the sole DDL owner, Worker64 the
independent reviewer, Worker00 the integrator and Worker57 the runtime/custody
owner. Source implementation and generated-fixture tests do not select a real
body operation, create an actual populated Dietary target, or grant source use.
No acquisition, CLI factory, service, model call or production route is installed.

## Frozen callable and schema

- `DietaryInput`: trusted native `SourceContract`, exact independent qualification
  digest, candidate path/bytes/five-part FD identity, expected profile/product
  counts, provenance-manifest/operation-evidence digests, optional existing
  asset/citation IDs and explicit pending citation status.
- `prepare_dietary_manifest(spec)`: validates and snapshots metadata without
  opening/statting a body. Bind its `sha256(core.canonical(manifest))` in the
  independent runtime selection. A manifest or digest is not an authority grant.
- `DietaryLimits`: explicit byte/packet/line/observation/per-profile/exception/
  database/aggregate-storage/time ceilings and batch checkpoint interval.
- `build_dietary_database(spec, new_path, *, limits, load_id,
  input_manifest_sha256, selection_receipt_sha256)`: returns a terminal receipt
  only after same-pass EOF/hash/size/count/identity, SQL conservation/integrity,
  output hash/custody and exclusive no-replace publication have passed.

The exact Worker13 `dietary-native-store-v1/schema.sql` bytes are embedded as
`DDL`, SHA256 `c37ac158bbd970e53616ae382c57227a0004d1fbfe902cbb8cf55c8610b260d3`;
interface SHA256 `66da03eec5045fbf233d22f09d8f0ab9951a910649964be6f95824baf972a8eb`.
There are six tables and two views. This implementation does not edit that
contract, copy/mutate13's empty DB, or alter the identifier DB. The interface's
older26 source-writer wording is superseded by Gateway's explicit56 assignment.

Trusted reviewed caller code supplies the contract and current custody identity;
there is no JSON-to-contract loader. The existing native qualification validator
checks retain/parse/transform scope, holds, source/release/native-private output,
contract/qualification fingerprints and fixture status. An arbitrary citation ID
or evidence digest does not prove FETCH authority; unresolved citations remain
pending. The exact independently reviewed operation still determines body rights.

## Preservation and accounting

All packets get source-scoped ordinal audits. Product packets count as other-kind
without joining or retaining product payloads. Every actual nutrient profile,
including empty, missing, null or invalid nutrient containers, retains its exact
UTF8 packet text including LF, document hash, source identity, source-row JSON,
complete provenance, unknown fields and upstream transforms. This is the retained
native representation, not reconstructed original CSV or canonical nutrition.

Decoded nutrient-map order determines observation ordinals. Each original entry
key (including occurrence suffixes) gets one row; no merging, averaging or name
matching. Pointers escape `~` and `/`. Entry hashes use the named
`sorted-UTF8-exact-decimal-JSON-no-LF/1` encoding, not original byte spans or the
core LF-inclusive encoding. Native packet hashes cover actual input bytes.

JSON-valued columns retain JSON types. SQL NULL means absent; JSON text `null`
means explicit null. Field-state JSON records missing/null/present/invalid.
Decimal parsing preserves exact finite numeric values, including long decimal
precision, negative zero and exponents beyond binary float range. Numeric
spelling remains authoritative in the exact packet document; sourceAmount retains
its own original lexical text. Units and sourceUnit case, basis and method remain
unchanged. An invalid entry is retained as quarantined; an unknown/missing/null
field is unresolved. All source fields and unknown `rawFields` remain in the
profile document. No absent nutrient becomes zero, allergen absence or advice.

Original language remains NULL/unknown unless explicitly supplied. All canonical
food/ingredient/nutrient/unit links remain NULL and all normalization/semantic
statuses pending. Dictionary, selector, English output, cross-domain joins and
citation backfill are not raw-load gates. Local DB creation time is not an
acquisition/publisher timestamp. No RLS or rights grant is inferred from SQLite.

Malformed/wrong-source/unknown-kind packets get quarantined audits and bounded
exceptions; the full pass fails conservation and publishes no completed target.
Malformed profile data and malformed observation values retain their original
profile documents and explicit dispositions. Observation totals are measured;
the upstream27,195,013 configured ceiling is never reported as an actual count.

## Runtime and failure contract

Linux `/proc` and a serialized default SQLite connection are required, following
existing identifier-loader custody/publication primitives. The caller provides
an existing0700 output parent; the importer creates an exclusive0700 stage and
0600 database. No overwrite, retry, cleanup, process creation or server occurs.
One candidate FD is opened; current lstat/path and held-FD identities are checked
before and after the single read/hash/parse pass. Symlinks are rejected. SQLite
uses DELETE journaling, memory temp storage, an8MiB cache, no mmap, a page-count
ceiling and deadline checks. Database/journal allocations are checked at packet
boundaries and within large profiles. These are application ceilings, not an OS
sandbox:57 must qualify and enforce actual CPU/address-space/FD/file-size/storage
and wall-time boundaries including journal and retained diagnostic overhead.

Packets use savepoints within bounded batch transactions. Running checkpoints
use scalar counts, avoiding repeated scans of growing tables. On failure, the
current uncommitted batch rolls back; durable read/unread/observation counts are
reconciled from SQL and state becomes incomplete where possible. The exception's
`dietary_retained_state` identifies stage/destination and actual read attempts,
not accepted or necessarily committed rows. External terminal inspection must
reconcile failures where SQLite/OS limits prevent checkpoint writes. Never infer
zero exceptions/unread rows or completion from a failed process or a partial DB.
No automatic resume/overwrite is supported. Retain and review before a new
independently selected generation. Complete stage state without a successful
terminal publication/receipt is not a successful delivered load.

The receipt includes input/schema/interface/selection pins, byte/hash/FD proofs,
packet/profile/observation/exception SQL counts, field missingness, nutrient
container states and observation dispositions. Output digest is external to the
DB, avoiding self-hash cycles. `accepted`, `goldAdmitted`, `countryComplete` and
`runtimeOrResourcesAdmitted` remain false. Logical content IDs are deterministic;
DB bytes vary with timestamps/load metadata, so byte-identical DB replay is not
claimed.

Publication retains the hashed device/inode/size/mtime and byte extent across
rename, allowing its expected ctime change. After file/directory fsync and final
custody checks, the named file and held FD must still match the publication
signature. Post-hash append/rewrite refuses a successful receipt and retains the
published/staged state; no additional database hash pass is added.

## First real operation proposal (not executed)

The worker artifact packet freezes the full numerical proposal against11519:
18,424,445,399B local USDA candidate SHA256
`706c767d47d0feebf64915c6f0d3aba45840b012ab07bb7a2d21915f303b06a3`,
4,202,558 packets =2,101,279 profiles+2,101,279 products.57 must bind current
custody and operation evidence, reviewed runtime/source/DDL and fresh actual
resources before one selected body pass. No prehash, original ZIP, source DB,
full identifier scan or profile-by-ID lookup is required. All source/rights/
privacy/denial/SAME11/mandatory auto_review/execution/promotion/production/CIX
holds persist. NO MORE FETCHING applies. No profile/inventory data is invented.

Validation: `python3 -B -m unittest tests.test_dietary_native_store -q`:
25 tests pass, including post-hash append/rewrite at rename and directory fsync.
The related36-test native-lookup/identifier suite has an existing
FD-count assertion failure (observed descriptor count decreases6 versus10),
reproduced in the untouched shared baseline. An earlier59-test combined run
passed; later60-test and separate36-test runs expose that baseline instability.
No existing assertion was changed. All fixtures are generated locally; no
retained body is read by these tests.
