# Assistant-authored extraction intermediates

This is a local-only extension to the source-faithful parse stage. The code does
not call an AI provider. The operator supplies an exact assistant-authored JSON
response once per source record that is eligible for such extraction; the code
checks it against the unchanged retained original, caches it, and deterministically
replays it through the existing `offmenu-source-recipe/2` record validator.

## Stages

`original -> deterministic source parser -> assistant intermediate (only when
needed and permitted) -> versioned deterministic schema replay -> separate
normalization -> translated English gold`.

This change implements the intermediate cache/replay seam only. It does not
implement normalization, translation, cross-record identity merging, a model
client, or golden-volume admission. The existing parsed record is preserved;
assistant-assisted output is stored in a separate `assistant-assisted/` tree.

## Required permission gate

`cache_assistant_intermediate()` requires
`source.assistantExtractionAllowed is True` and a nonempty,
source-specific `assistantExtractionPermissionEvidence` citation. This is not
a license inference. Copy/read permission does not imply semantic extraction,
AI processing, derivative use, normalization, translation, or publication.

No external model calls are made. An assistant response may only be cached for
sources whose documented scope authorizes that processing. In the absence of
such a grant, retain the deterministic record and report the block; never
rewrite or enrich its output with an unapproved interpretation.

## Cache contract

The cache key includes the original SHA-256, exact ingredient/direction/yield/
variation segment hash, intermediate schema and prompt versions, model identity
and version, inference settings, parser/schema version, and transformation
version. The envelope preserves the exact raw response, its SHA-256, extraction
time, validation status/uncertainty, source provenance, transformation versions,
and the base deterministic record. Cache files and response bodies belong on
Foo and must not be committed or published.

Tooling is conditional, not a required cache field. When a derivation actually
uses a reusable local tool (for example, a translator/validator script or an
adapter created for that pass), pass its artifact as `tooling_artifacts` with a
logical name, local path, and optional version. The cache archives those exact
bytes under a content-addressed `tooling/` path, records SHA-256/size/version,
includes that identity in the cache key, and verifies the archived bytes during
lookup and replay. A changed tool therefore cannot silently reuse output made
with the old tool. Reuse the compatible cached output/tool archive before
re-running the derivation where possible. Do not pass tools that were not
actually involved in producing the result.

When no reusable tooling was created or used—for example, an AI-only English
recipe pass/translation—the cache stores the derived AI response and its normal
source/model/prompt/validation provenance only. It emits no empty tooling
manifest and creates no tooling artifact. Translation provenance should still
identify the model/method and input/output hashes; that does not imply a tool
exists. Tool artifacts are local cache material and must not be committed or
published without a separate review.

The current API accepts tooling artifacts as caller-provided evidence; it does
not discover which programs an external model runtime used. Callers must only
supply artifacts known to have participated in the derivation. Model/provider
execution details remain separately represented by model identity/version and
inference settings.

Atomic exclusive file creation plus a per-directory writer lock prevents
partial or conflicting writes. Rejected attempts are saved under `rejected/`
with the response hash and failure reason; they are never usable records. On a
rerun, call `find_compatible_intermediate()` before asking for another
assistant response. Only a fully validated compatible cache may be replayed.
A changed source, source segment, model, settings, schema, prompt, or transform
version cannot silently reuse an incompatible entry.

## Validation

The current bounded recipe adapter verifies ingredient and instruction coverage
against the deterministic extraction, source quote byte/character spans, order,
quantities/units/preparation alternatives, direction span coverage and ordering,
source-supported timings/temperatures/equipment, source yield and variation
coverage, and record schema. It keeps raw language and lexemes; it performs no
unit conversion, ingredient identity mapping, inferred nutritional completion,
country assignment, or recipe matching. It rejects unsupported additions and
records explicit uncertainty/ambiguity with evidence locations.

The adapter is currently for recipe HTML with explicit Ingredients/Method
sections. Other document types need matching deterministic page/row/section
segmentation and adapters before processing. It does not OCR PDFs or invent
section boundaries.

## Foo execution

Run heavy corpus decompression, source parsing, schema checks, and future
normalization batches on Foo. Use bounded worker pools subject to measured
memory and IO, checkpoint per asset, and one cache writer lock. Do not run
duplicate parser/cache writers. Fetch remains paused and is outside this stage.
Raw originals and all source-derived cache contents remain local to Foo.

## Published inventory snapshot and current scope

The supplied publication is pinned to
`maldous/offmenu@7522b07c97445f99be08e5900dc1607640af890d`,
`docs/coverage-register/2026-10-19/coverage-register.json.gz`.
The local gzip checksum is
`d971359e3991fdcf391e28bf040f443cb758c01b891b0f199d734794b889abd0`;
its decompressed JSON contains 6,068 asset entries and 3,250 origin/type cells.
It reports 12 locally parsed-output releases (148 parsed-evidence cells), 63
independently verified source files, zero complete country/type cells, and
unresolved acquisition, source-use, extraction, and coverage holds. These
figures describe that snapshot, not current completed work.

The local copy and a sanitized eligibility summary are under the owner-local
data workspace. No source body is included in the summary. No inventory row was
found with both an explicit local original path and a verifiable source-specific
assistant-extraction grant. Separately, checksum joining the 15-asset
2026-10-20 local parse run against the snapshot's 6,068 asset rows found no
matches. Treat those as distinct evidence sets; do not claim the published
inventory accounts for this local run. Actual assistant extraction is blocked
pending a source-specific grant; historical custody metadata is not processing
permission.

## Per-stage processing provenance

`scripts/build-processing-provenance.py` builds a private companion ledger from
a source-parse run manifest and its existing artifact manifests. Each asset has
separate `parse`, `normalize`, and `englishTranslation` stages, each recording:

- method: `code`, `one-off-agent-AI`, or `hybrid` (null when not run);
- engine identity/version, with unavailable details marked `unknown`;
- input location and checksum; cached output locations and checksums;
- processing date with evidence, or `unknown` when no reliable timestamp exists;
- validation status/evidence and unresolved issues; and
- supporting source/run references.

For agent-derived results, preserve extraction instruction/prompt version,
model identity/version when known, exact response checksum, and supporting
source spans/pages. When reusable tooling actually participated, preserve its
content hash/version and local cache reference alongside the derived result;
when no such tooling was used, omit the tooling artifact rather than inventing
one. Do not guess missing engine or processing-date values. A stage proven not
to have run is `not-run`; a failed prerequisite is `blocked`. Successful parse
does not imply normalization, translation, completeness, or publication
permission.

The builder is offline and does not read originals, invoke a parser or model,
fetch, normalize, or translate. It verifies cached-output bytes against the
asset manifest. The generated ledger includes private absolute paths and must
remain local unless sanitized and explicitly reviewed. It refuses to overwrite
an existing ledger.

## Current parse batch and verification

The 2026-10-20 source-faithful batch has 15 assets (13 recipes and two menus),
83 accepted records, and zero failed assets. The parser identity is
`offmenu-source-faithful-recipe-parser/1.3.0`. The run log establishes the run
date, but no per-asset processing timestamps are present; these remain
`unknown` rather than inferred from filesystem timestamps. Normalization and
English translation were explicitly not run. This local batch does not checksum-
join to the pinned 6,068-row inventory snapshot, so the grant finding for that
inventory should not be generalized to all these 15 inputs.

Focused tests in `tests/test_assistant_intermediate.py` use synthetic HTML and
verify cache reuse, deterministic replay, source-span checks, rejection
quarantine, source-change invalidation, and the permission gate.
`tests/test_processing_provenance.py` use temporary synthetic manifests to
verify stage separation, unknown/not-run values, and output checksum validation.
These tests do not count as model extraction successes or rights evidence.

To generate a private ledger from a completed existing run (without rerunning
the parser), pass the run manifest and a new output path to
`scripts/build-processing-provenance.py --run-manifest <manifest> --output <ledger>`.
Keep both the ledger and its absolute source/cache locations in private storage.

Never commit source bodies, raw assistant responses, or a ledger containing
private absolute paths. This provenance records work performed; it is not a
rights determination or authorization for downstream use.
