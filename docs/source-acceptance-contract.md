# Offline source qualification and local acceptance

This implementation follows the restored refresh design: source interpretation,
curation, common-graph qualification, local acceptance and whole-country/domain
coverage are separate states. It makes the acceptance path executable without
activating any source rights or installing a production admission.

## Shared adapter output

`candidate.jsonl` is UTF-8 LF-delimited JSON. Every line contains a singleton
packet `[record]`; each record has `id`, `kind`, `schemaVersion` and provenance
`sourceId`, `releaseId`, `fetchedAt`. Adapters preserve source-specific data and
unknown values. The JSONL file is not itself an acceptance receipt.

The associated manifest has `sourceId`, `releaseId`, `acquiredAt`,
`normalizedRecords`, `candidateSha256`, `candidateBytes`, `inputFiles` (canonical
relative `path`, `bytes`, `sha256`, optional parser `role`),
`rightsEvidenceSha256` and `scopeEvidenceSha256`. Evidence-inclusive qualification
manifests may be separate from the original parser manifest; never rewrite the
original to pretend evidence files were interpreted as source data.

Nested inputs are permitted with exact custody. Archives, extracted files and
uninterpreted companions are separately pinned; archive extraction is not part
of qualification. The bounded shared `national_tabular.bundle_files` inventory
rejects unlisted files/directories, symlinks, special files and excessive depth or
entry counts. It is used by all adapter families, despite its module name.

## Trusted SourceContract

`offmenu.refresh.acceptance.SourceContract` is supplied by reviewed application
code. Never construct one from a source manifest, discovery row or CLI flag.
It specifies exact source/release/scope, acquisition timestamp, all assets,
independently expected record count and sorted-ID digest, full schemas by kind,
schema and semantic-policy identities, and an all-record semantic callback.
`semantic_validator(record)` returns fixed diagnostic codes; unresolved units,
bases, definitions or joins are errors when canonical qualification requires them.
Native source preservation may use a narrower, explicitly reviewed native scope.
Passing such a scope does not imply canonical semantic equivalence.

Use existing operation names: `retain`, `parse`, `transform`. `permitted_operations`
is the reviewed decision for these exact bytes and representation; the digest of
a rights file alone is not a permission grant. Conditions and source holds must
remain in the reviewed contract. A public output additionally requires `serve`
and `redistribute`. Merely building a private curated/common artifact does not
require a new public-sharing approval.

Schemas must include the actual record shape and source-specific validation;
semantic callbacks must perform the source-specific checks that JSON Schema
cannot express. Remote schema references are forbidden. The implementation uses
`jsonschema.Draft202012Validator`; missing runtime dependency fails closed.
Source-specific release schemas and production admissions are not installed by
this batch. Production runtime dependencies and reviewed callbacks must be pinned
by the existing execution isolation boundary before dispatch.

`qualify(contract, bundle, candidate, manifest, scratch_root=...)` verifies actual
asset bytes, independent count/IDs, source/release/timestamp, all record schemas
and semantics. It accumulates diagnostic codes across all bounded rows. Candidate
hashes bind the bytes actually parsed, with pre/post verification. IDs use SQLite
rather than a whole-release in-memory set. No rows are dropped to reach a passing
count. `accept(...)` revalidates current bytes and emits a separate deterministic
receipt; it neither edits a manifest nor changes an accepted pointer.

Contracts have explicit `max_input_bytes`, `max_output_bytes` and `max_records`.
Defaults are 256 MiB/256 MiB/1,000,000 rows, with reviewed upper bounds of 1 TiB
and 1 billion rows. Lines remain bounded at 8 MiB. Large runs must pass a private
Foo scratch directory for the SQLite index and use the runner's reviewed
resource/isolation boundary. Increasing a contract limit does not increase the
GLOBAL runtime budget or remove a source-specific eager-parser cap.

`fixture=True` produces `accepted-fixture-scope`, never production or country
acceptance. A positive fixture is evidence that the code path works, not evidence
that any real release was processed. `fixture=False` is reviewed configuration,
not a user-facing runtime toggle.

## Real endstate stage wiring

`CandidateArtifact` packages contract, bundle, candidate, manifest and optional
Foo `scratch_root`. `endstate_handlers(native, curate, graph, receipts,
discovery_id=...)` returns handlers and a private state dictionary. Native is a
trusted factory taking a StageContext. Curate and graph factories take the
context and previous qualified artifact, perform their reviewed transformation,
and return independently contracted output artifacts. Curate must produce
`output_scope='curated'`; graph must produce `output_scope='common'`.

A common artifact in this envelope must use a reviewed packet/record schema for
its actual graph output and existing graph validation, not reuse a nutrient
schema and call it a graph. The tests use synthetic envelopes solely to exercise
stage control. This batch does not install production curation or graph factories.
A missing factory stays unsupported; normalization is never silently promoted to
curation/graph success. The source identity is checked against StageContext,
with one explicit reviewed discovery alias when needed. Factories own their
reviewed OS resource boundary; this Python helper does not sandbox them.

Combine these handlers with acquisition/parse/normalize handlers in a GLOBAL
Binding, passing the returned state as `Binding.endstate`. The GLOBAL report
retains full per-stage qualification summaries, normalized-candidate status and
verified acceptance separately. Pass the private receipt mapping to
`global_run.run(..., acceptance_receipts=..., cell_requirements=...)`.

## Country/domain completeness

`CellRequirement` specifies country, domain, exact mandatory
(source, release, scope, qualification digest) tuples and independent reviewed
applicability and completeness evidence digests. These are trusted bindings, not
inferences from global routes, languages or parser success. Every required source
must have one untampered production acceptance receipt. GLOBAL additionally binds
the receipt to this run's completed accept-stage evidence. An old or orphaned
receipt cannot turn this run into a success.

Every country/domain cell is reported, including missing requirements. Counts can
be nonzero when requirements actually pass; whole coverage is true only when all
required cells pass. A passing cell does not erase an independent source failure.
The public deployment and CIX boundaries are unchanged.

## Verification and current limits

Synthetic tests cover positive deterministic acceptance; partial data; exact
nested custody; duplicate IDs/JSON keys; foreign provenance; schema, unit and
basis drift; missing rights/holds; remote-schema refusal; nonfinite values;
reacceptance after corruption; missing stages; source-binding mismatch; explicit
aliases; public-operation requirements; stale/tampered receipts; and reachable
nonzero GLOBAL country/domain acceptance. Existing GLOBAL tests remain green.

No real source download, raw-data publication, production acceptance, pointer
movement, rights activation or deployed graph is performed by these tests.
