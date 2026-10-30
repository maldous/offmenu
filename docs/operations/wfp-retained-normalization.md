# Retained WFP Libya normalization

`offmenu.refresh.wfp_retained` projects the selected retained JSONL derivative
into source-scoped `priceObservation` singleton packets. It never opens the
original CSV, market file, Open Prices partitions or semantic-links body. There
is no CLI, acquisition path, registry admission or publication operation.

The selected source is `wfp-food-prices-for-libya`, release
`price-resource-modified-2026-10-11T15:38:40.693973`. The real operation is exactly
69,273 retained candidates, excluding original physical lines 2–201 and 327.
Authored fixtures use a separately named scope and smaller counts. Scope labels
and evidence hashes are declarations; they do not grant execution authority.

`normalize_record(candidate, context=..., input_line=...)` is pure. All sixteen
native strings map unchanged from `/values/<column>` to `/data/native/<column>`:
date, admin1, admin2, market, market_id, latitude, longitude, category, commodity,
commodity_id, unit, priceflag, pricetype, currency, price and usdprice. Zero,
empty strings and lexical formatting remain strings. No numeric conversion,
food classification, currency correction, FX orientation or basket comparison
is performed. Native category/commodity identifiers remain available for the
already accepted semantic role/link evidence; no role is filtered. The existing
semantic links and their role counts remain separate pinned evidence, not a
new classification performed by this adapter.

`/data/unqualified` contains explicit null concept, unit, currency, market,
basis, food-eligibility and FX-orientation targets. Each has a code-policy
constant origin. Native cells and copied unknown/issue flags have exact
retained-derivative field origins. Original source hash/line/byte selectors are
retained under provenance, without falsely describing them as newly checked
raw cells. Acquired and validated timestamps remain separate. Rows are not
accepted or automatically eligible for planning.

`normalize_retained(input_path, destination, context=..., expected_records=...,
limits=WfpLimits(), previous_receipt_sha256=None)` streams bounded input, checks
its exact byte/hash/count/source-order contract and writes deterministic
`normalized.jsonl.gz` plus `manifest.json`. These are candidate and receipt
files in the selected destination contract. Common `BoundedReader`, strict
JSON, canonical serialization, field-origin validation, code/runtime identity,
digesting, atomic receipt writing and fsync primitives are reused. No shared
engine files or global registries are modified.

The caller must establish the approved existing destination parent. This
function never creates a volume or parent directories. It validates the entire
input in a private temporary sibling, then reserves the final directory with
exclusive mkdir, moves the candidate and installs the completion manifest last.
Directory existence alone is not completion. A failure during final commit
leaves a partial destination for explicit recovery; subsequent calls stop. Only
the invocation's private temporary sibling is cleaned. Existing final files
are never overwritten or deleted. Multi-file crash atomicity is not claimed.

An existing completed destination requires the externally retained exact
manifest SHA-256, not a receipt discovered and trusted merely by pathname. The
adapter verifies that receipt, full context/count/limits/policy/code/runtime
identity, exact asset set, current derivative hash and compressed output hash.
Only then does it return `reused=True`, without writes or mtime changes. Changed
or partial output stops. This is candidate identity reuse, not independent
acceptance or a new source acquisition. Validation never substitutes for the
original acquisition timestamp.

Hard ceilings are 256 MiB input, 64 KiB input line, 100,000 rows, 256 MiB compressed
output, 1 GiB expanded canonical stream, depth 32 and 120 seconds of cooperative
wall-clock checking. Receipt size is at most 1 MiB. Expanded output is streamed,
never stored as an additional file. The caller must also enforce a reviewed
offline subprocess, 256 MiB memory and external wall timeout; this callable is
not an OS sandbox. The source hash/format/size, disk reservation, time and
destination volume must fit the actual reviewed runtime before the real run.
The ceilings are not permission or resource-reservation evidence.

Morgan selected writer59 and the existing Foo destination separately. Actual
execution still requires independent reviewer45 approval of the immutable code,
current exact input/rights checks and qualified runtime limits. Custody/use is
bound to worker27's source-specific receipt. The later independent source-output
review belongs to27 if not the handler author, otherwise45. Source-native data
stays on Foo. Production, publication, gold/real admission, CIX, DEV7645 and
actual source/denial holds remain in force.

The tests use authored fixture records only, including a non-food exchange
assertion and lexical zero/empty values. They cover malformed/deep/duplicate
input, scope/identity/prefix errors, provenance, bounded file access, streaming
determinism, exact completed no-op, corrupted output and partial-commit stops.
