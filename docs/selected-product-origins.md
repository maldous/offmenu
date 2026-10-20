# Bounded selected USDA product origin caller

`selected_product_origins.emit_selected_usda_product_origins` reuses the accepted
`ProductOriginEmitter.emit/usda`, `SourceRow.leaf` and `field_origin_errors`.
It adds only a selected-product caller and a restricted source-row view. It does
not call the full origin-stage wrapper, normalize/requalify a candidate, scan a
candidate or lookup, open the original ZIP, infer graph roles or publish output.
There is no real selected22 application factory or execution admission here.
All implementation verification uses generated rows and proof fixtures.

## Required external bindings

Arguments are an already bounded TUPLE of selected native product dictionaries,
explicit `SelectedOriginScope`/`SelectedOriginLimits`, the unchanged full native
SourceContract and independent qualification receipt, bounded normalization
manifest bytes, bounded binding-evidence bytes and the selected database root.
Generators, candidate paths, missing scope or unspecified limits are refused.

Reviewed application code must independently select:

- Exact selected product IDs/count/ID digest, candidate lines/order and record
  byte pins from the independently reviewed selected lookup artifact. All
  collisions/distinct products remain; no GTIN/global identity inference.
- Full original source/release/archive pin, native SourceContract and independent
  qualification/candidate pins, plus matching ProductContext/rights/clock.
- Normalization manifest and DB hashes from independently established derivation
  context, and its independent review pin. A manifest's own output hashes do not
  establish derivation authority.
- Fresh qualified DB device/inode/size/mtime/ctime identity bound to that same
  independently trusted DB hash and custody-review evidence. This caller does
  not replace missing qualification with its own whole-file hash or path stat.
- Exact ZIP member paths for BOTH food and branded_food and every selected
  product's independently bound logical row ordinals and raw.body UTF8 hashes.
  CSV extension recognition matches the producer's `suffix.lower() == '.csv'`;
  the bound member path and table stem retain their exact spelling and case.
  No member path, branded row or row witness is derived from a food sourceRow,
  candidate line, barcode string or a guessed filename.
- Selected operation/binding evidence, exact emitter/caller code pins and all
  limits. No SourceContract expected count/ID constant is replaced with22.

The binding document is `offmenu-selected-origin-binding/1`, with `scope` equal
to the selected dataclass descriptor except its own operation_evidence_sha256
root, and `limits` equal to the explicit limits. The expected operation SHA is
selected independently in application code; hashing an arbitrary document and
passing its new hash is not an authority constructor. The same root binds the
members, row pins, DB identity, reviews and caps. Changing any of them under the
existing root is refused. This is a small source-specific operation contract,
not another resolver/controller or graph evidence protocol.

The existing native lookup `_binding` check is reused ONLY for bounded receipt/
contract metadata validation. It does not scan the original candidate. The
normalization manifest must match the selected full native count, original
archive, context, producer version, candidate hash and DB hash. The full native
factory/contract remains unchanged. Newly supplied records must match every
selected ID/key/candidate membership pin and primary-food sourceRow; a private
JSON byte snapshot is checked and used for emission, preserving exact values.
Unknown acquisition remains unknown through the selected ProductContext.

## Actual database access

The caller opens only the selected source.sqlite using mode=ro&immutable=1.
It requires the caller-qualified serialized Linux/default SQLite main-file
descriptor-attribution contract used by the accepted partition core. Observed
Python/OS concurrency and ambiguous new FD inventories refuse setup. The actual
SQLite open descriptor is duplicated and must match the externally qualified
identity; basename checks alone do not establish connection agreement. WAL,
SHM or journal sidecars are refused. Runtime/loaded-code/OS qualification remains
external; endpoint thread checks do not prove continuous absence or safety for
custom VFS/hostile in-process FD manipulation.

The existing emitter's food-key/branded-key queries are served by a tiny view.
Each independently selected key maps to its explicit food and branded_food row
pins. Actual SQL reads use `WHERE tab=? AND ordinal=? LIMIT 2`; query plans must
positively report a SEARCH of raw with BOTH `tab=?` and `ordinal=?` in its indexed
search constraints. SCAN/temp B-tree refusal examines the leading plan operation;
a valid SEARCH index name may contain `scan`. Index names never establish either
point constraint. A tab-only SEARCH
does not satisfy this contract: LIMIT2 caps matches, not the table-prefix index
walk before ordinal filtering. Unsupported plan representations fail closed;
neither index names nor the word SEARCH alone prove composite point access.
Existing VM/time bounds still constrain work, and this correction does not claim
that a prior partial-index case was unbounded or occurred on a real source DB.
Missing/duplicate rows,
wrong identity/key/ordinal/body hash or excess bytes fail. Only food and
branded_food are supported, each once per product; cached reuse serves the
emitter's existence/join lookup. No food_nutrient/profile/archive read, aggregate
COUNT, table traversal or index build is permitted. This does not claim that
SQLite page IO contains only selected cells; real page/index/cache costs still
need the selected executor's OS/resource boundary.

Limits bound records/input/metadata, raw row and total row bytes, enriched-record
and aggregate output bytes, declared DB size, cooperative time and SQLite VM
steps independently: `max_row_bytes` limits each raw body, while
`max_record_bytes` limits each input and complete enriched record. The unchanged
emitter's shared line envelope uses the larger of those two caps; the caller
checks each enriched record against its own cap before retaining it. A permitted
unused raw column does not consume the enriched-record allowance.
The progress handler checks every VM step during the point-query phase;
it is not an OS walltime/IO/memory boundary. The fixed open/header setup precedes
that counter. SQLite length limits supplement row checks. The SQLite C-int API
argument is capped at `2**31 - 1`, retaining the existing 4096-byte floor; the
declared row-byte bound remains unchanged in the binding and Python row checks.
SQLite may enforce a lower compiled hard limit. A large declared bound therefore
does not promise support for equally large rows or establish resource admission.
All results remain in a bounded private buffer until the post-read DB identity,
sidecar, implementation and deadline checks pass. The owned read connection and
duplicate FD close on success/failure. Source DB is never written or copied.

## Complete origin inventory and unchanged data

The emitter's complete product projection must equal the existing data exactly.
Every data scalar, including zero/null/array values and missing-field constants,
receives an origin, validated again with `field_origin_errors`. A partial
barcode/ingredients/nutrition three-field packet cannot be labeled complete.
Unknown/changed/partial data or emitter drift fails instead of filling gaps.

Food and branded-food coordinates are distinct: product name and the food key
use food; barcode and ingredient values carry the food-to-branded join and the
ACTUAL branded_food member/row/field. nutritionId remains the existing derived
native profile reference from the primary food fdc_id. No target profile body is
read or claimed qualified here. Ingredient text remains verbatim opaque source
text; no concepts, quantities, language, identities, claims or edges are inferred.

The returned packet identifies the full contract/qualification, selected scope,
lookup/review/derivation/custody/operation pins, input/member/code pins and exact
selected IDs/count, with complete-data-scalars origin coverage and bounded
measurements. It keeps qualified/accepted/runtime-resource flags false and
records originalArchiveRead/fullDatabaseHashPerformed/candidateScanPerformed
false. New origin coverage is not fresh full-source qualification, source-use
permission, field-witness review, English/gold, canonical identity or publication.
No output publisher, retry, cleanup or actual source factory is installed.

## Later real source access and costs

Only metadata review10737 was used for current real lookup context. Its selected
private result is34,844B/22 native products. The body, private IDs/query/text,
normalization DB/manifest and archive members were not opened or copied here.
Existing full candidate is18,424,445,399B/4,202,558 rows per that review; rescanning
it is NOT part of this caller. The precise real selected-ID digest/record pins,
derivation DB/manifest/custody evidence, ZIP member map and food/branded row pins
are not supplied by that metadata summary and must not be invented.

When separately admitted, a qualified owner can read/verify that small exact
selected artifact and two bounded metadata buffers. Once the required bindings
are available, the caller performs at most44 indexed source row fetches for22
products,44 query-plan checks, one read-only DB open/header and pre/post identity/
sidecar checks; no full DB hash, candidate scan or ZIP/member read. Source-row
bytes are explicitly bounded, not known actual costs. Physical page IO, actual
DB size/memory/time and output expansion remain qualification inputs.

Preparing missing row/member/derivation/custody evidence may need a separately
selected bounded row/ZIP-metadata extraction and review. If no independently
qualified DB checksum bound to its current identity exists, qualifying it can
require full D/pre/post hashing outside this caller, budgeted explicitly rather
than hidden as a selected22 read. This caller's computed row hashes are checks
against selected source pins, not independent derivation or CSV witness authority.
No real field witness or actual row/member is asserted by the fixtures.

Existing57 owns actual source access/runtime/resources; Gateway selects the exact
operation and independent review, then00 integrates source.56 owns the separate
native identity/relationship adapter; this caller does not overlap that work.
Full native SourceContract and selected origin scope stay separate. All source,
privacy/custody/OpenPrices/failed25/production/CIX holds remain. Actual22/DB/
original/archive/member access is unselected in this source task.
