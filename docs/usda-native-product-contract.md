# Fixed USDA April 2026 private native contract

`offmenu.refresh.usda_product_contract` supplies reviewed application code for the
exact retained FoodData Central CSV archive. It is not a source-JSON contract
loader or a source registry admission. The fixed original SHA/bytes/release and
the existing reviewed CC0/private-operation rights asset remain unchanged.

The independent full-source witness9995, reviewed64/9993, measured
`expectedRecords=4202558` and sorted-ID digest
`2d5be06c4e3be042b4bed583a5ada885066188b901aa3b23f7a9dc48a1472f0f`.
These are two native IDs per actual food ID: product and nutrientProfile.
They are not 36,049,091 raw table rows, 1,999,950 branded-food rows, a distinct
GTIN count, or evidence that any normalized records have been produced.
The factory fixes the exact witness/review hashes and this count/digest in code;
callers cannot replace them with CLI arguments or a discovered manifest total.

`native_schemas()` defines the complete existing projector record shapes for
both kinds, including every product/serving field, identifiers, each nutrient
observation and raw CSV fields, provenance/source row/archive pin, rights/scope,
unknown acquisition clock and the optional later field-origin extension.
Extra projected fields fail the closed schemas. Original arbitrary CSV columns
remain string-valued raw fields; no new columns or units are guessed.

The all-record semantic callback enforces source/release/ID consistency, native
FDC identity rather than GTIN identity, product-to-profile references, evidence
digests, source-row bounds, archive pin, raw nutrient food/key/amount lineage,
numeric value versus its preserved lexical amount, lowercased source units,
source basis/method and distinct observations. Empty amounts stay null, literal
zero stays zero; malformed/nonfinite amounts are rejected. Unknown nutrient IDs
and units remain native source assertions. Repeated nutrient measurements retain
their existing observation suffixes. This does not qualify source units as
canonical dimensions, clinical facts or nutrient-definition equivalences.

The primary name belongs to the first **source CSV row** for that mapped nutrient;
later rows use the existing `:observation:<source ID>` suffix. Neither numeric
source-ID sorting nor JSON object key order establishes source order. Fixed
nutrient-profile qualification fails closed without authoritative row order.
The product qualifier automatically binds the fixed semantic policy to the same
normalization's private `source.sqlite`, checked against its normalization
manifest/source-context/input/output pins and read-only DB hash/identity before
and after qualification. Its query uses the stored CSV `ordinal`, with bounded
rows/bytes, and checks exact expected observation names and source raw fields.
Suffix-only, swapped-primary, missing-observation and coherent row/value forgery
are rejected without changing IDs. The pinned projector itself is unchanged.

The field-origin stage uses that same order authority during new and retry
qualification. Direct `qualify`/`accept` with the unbound fixed policy remains
held. A later explicit native acceptance must use
`bind_normalized_semantics(contract, normalization_dir, qualification_manifest,
reviewed_limits)` and pass its yielded contract to `accept`. This context is
supplied only verified product-normalization artifacts, never discovery JSON.
It neither reruns the archive parser nor changes counts/rights/publication.
Fresh57/64 resource qualification must include the extra read-only DB handle,
bounded row queries and pre/post DB hash IO; no existing resource admission is
implicitly extended by this correction.

`evidence_documents()` deterministically produces new product scope and clock
metadata. Write exactly the bytes returned by `acceptance.canonical`; using the
JSONL encoder or adding a newline changes their pins. Copy only the existing
reviewed rights metadata into the new exact evidence directory, preserving its
bytes/hash. Witness evidence, historical scope/templates, legacy canonical asset
`usda-archive:2026-04` and original bodies remain untouched. Acquisition time and
downloader remain unknown; release/verification times do not fill them in.

`usda_20260430_contract(limits=reviewed_product_limits)` returns the fixed native
SourceContract. There is no default real-resource envelope. Worker57 supplies
fresh reviewed runtime/output/database/scratch/CPU/destination ceilings and
capacity. Full input/expanded/raw-row floors must cover the measured archive;
the operation must also account separately for candidate, source SQLite,
qualification index, origin sidecar/staging and final retained outputs. A passing
constructor validates fields/floors, not actual resource sufficiency or execution
admission. Its semantic-policy hash pins this module's source file and the exact
existing adapter/schema/witness identities; it is not loaded-bytecode attestation.

After independent review and00 integration of this binding and the separate
`47b0b4d7` input-root candidate, the selected executor calls the existing product
qualifier with the explicit evidence bundle and in-place
`input_root`. No competing routing implementation is introduced. Actual rights,
runtime, capacity and final execution qualification remain required. The schema
and callback here define checks to run across the future complete candidate;
synthetic tests do not establish that the real candidate passed them.

The first selected shape is `qualify_product_candidate`, which retains native
normalization and returns qualification diagnostics with `accepted:false`.
Full field-origin materialization is not selected:57's current resource assessment
reports a synthetic lower bound around700.6GB per origin-bearing file, with two
files retained by the existing stage. This is relayed steering, not a measurement
made by26 or a new resource cap.57's exact source-bound packet must establish the
storage correction before that stage is selected. Native output/database fit is
also still57's separate measurement/qualification; this change asserts no fit.

The existing field-origin wrapper must independently verify every datum against
the pinned source DB/member/row/column and its emitter policy, and then requalify
the enriched candidate. An optional `fieldOrigins` object in the native schema
does not establish coverage by itself. The projected `countries=['US']` is the
existing source-context constant, not proof of market-country coverage. English
consumer semantics, canonical nutrient meaning, Gold, public operations and whole
country acceptance remain separate. No raw normalization is part of this change.
