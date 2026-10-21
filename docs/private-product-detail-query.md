# Private product-detail query boundary

This is the selected query-only extraction from reviewed source
`63dd92023c498b55a01711f0e1158c79fdd82a77`, on accepted base
`6431ddd417a746c9fe661230a9cb636b0375adce`. All six definition ASTs and five global
ASTs match that source. The new module contains no writer, DDL, manifest preparer,
scanner, cache decoder, original display lookup, label/component parser, source
factory or runtime activation.

This source lane is independent of import population and its PR85 integrity
correction. Full 256-OFF-plus-one-USDA population must not wait for query source
acceptance. Conversely, import acceptance does not accept this query or activate
its consumer. Held PR84 and its optional decimal-comma finding remain visible.

## Caller and namespaces

```python
from offmenu.refresh import product_detail_query as query

selection = query.ProductDetailQuerySelection(
    selected_generation_id, selected_input_manifest_sha256,
    selected_operation_sha256, selected_identifier_database_sha256)
evidence = query.CurrentIdentifierEvidence(
    independently_selected_held_identifier_connection,
    independently_selected_run_id, selected_identifier_database_sha256)
result = query.read_product_details(
    selected_held_detail_connection, current_identifier_rows,
    selection=selection, identifier_evidence=evidence)
```

Both dataclasses must come from the new module. A same-shaped object from an old
module or request JSON is not a selected context. Worker05 owns independent
selection of current completed output/review/receipt, database digest, held-file
identity, rights and the two RO connections. The run and database pins come from
that trusted context, never from request observations. The helper opens no path,
hashes no whole database and performs no index replay or rebuild.

Before returning a bridge, the helper performs one persisted assertion PK lookup
per observation. It compares all twelve selected assertion/source fields,
including run, assertion ID and disposition, and requires a completed or
completed-with-exceptions identifier load with a source-asserted assertion.
Missing, fabricated, changed or ineligible assertions return `not-loaded` without
a bridge. Detail candidates then use the BINARY namespace/lexical index and exact
source/release/input/hash/ordinal/native-ID/source-ID coordinates. There is no
barcode winner, canonical product inference or fuzzy fallback.

## Two canonical byte contracts

The production binding is deliberately:

```python
from .core import canonical, strict_json, RefreshError
from . import acceptance as readers
```

`readers.canonical` is the accepted packet serializer without a trailing LF.
`core.canonical` includes a trailing LF. Packet evidence and pair hashes use the
former; existing request/result size checks retain the latter. Aliasing `core`
as `readers` changes packet hashes and is invalid. These serializers are tested
as distinct functions and through a successful retained-record hash check.

## Source fields, coordinates and variants

The response retains complete product/profile records, source text, IDs,
provenance, source quantities and projection limitations. Canonical ingredient
concepts remain null/unmapped and never suppress source text. A supported absent
field is `missing` with projection evidence and a null field pointer. Explicit
null, empty and present values remain distinct. Unsupported representation fields
and unsupplied profiles/images remain `not-loaded`; publisher field presence and
language stay unknown.

Both USDA representations share the closed native schema capability map; both
legacy OFF representations share the actual OFF normalizer capability map.
Every non-null field pointer addresses the returned `records` array, including
explicit null or empty values. Source binding `recordPointer` addresses the actual
source record; `recordPointers` retains the ordered product/profile coordinates.
For example, full USDA uses separate `jsonl:line:P/0` and `jsonl:line:Q/0`
coordinates, while its product-only cache points at a record object without an
invented array suffix. The query preserves these accepted binding fields.

All eligible projections are returned. Multiple variants produce explicit
`ambiguous` availability rather than selecting the first. Consumer13/05 must
preserve variants, field states, source coordinates and errors in the existing
private response/UI contract; source readiness alone does not retarget that
caller or change activation.

## Bounds and errors

The helper accepts at most 25 observations, at most 1,000 candidate rows per
observation and at most 262,144 canonical response bytes, with finite VM-step and
time limits. Candidate overflow, record/hash integrity failures, oversized input
or output and resource limits are errors. They are not a successful empty result
or a truncated source value. Complete-response bounds include availability,
coverage and metadata even when there are no matches or no observations. The
size is measured with `core.canonical`, including its LF. A result exactly at the
requested cap is permitted; one byte above it is rejected. A caller cannot raise
the hard response ceiling above 262,144 bytes.

Both connection progress handlers are removed on exit, including errors. The
helper writes neither database. The caller retains connection/custody ownership
and must account for any additional outer transport/envelope budget separately.

## Qualification and owner handoff

`python3 -m unittest tests.test_product_detail_query -v` uses generated in-memory
SQL stores. Its detail fixture matches the independent Worker13 detail schema;
its identifier view has the selected persisted columns and PK joins. There is
no writer or old mixed-module import in fixture construction. Tests cover clean
imports/canonical aliases, new typed contexts, all twelve assertion fields,
disposition/load/generation negatives, RO behavior, source/field pointers,
capabilities and field states, ambiguity, PK/index `SEARCH` plans without `SCAN`,
candidate/response/payload/step/time bounds and both-handler cleanup. Exact-cap
and one-byte-oversize cases include match, no-match and empty-observation metadata
responses at both a requested budget and the hard ceiling.

Worker64 independently qualifies the exact extracted namespace, alias and source.
Worker00 integrates only these three new paths through an honest separate query
PR and normal provider/CI/security/expected-head/postmerge gates. Through Gateway,
Worker13 reconciles the existing envelope/variants contract and Worker05 prepares
the accepted-module/package-hash retarget. Both must use the new dataclass
namespace and independently selected current contexts after normal acceptance.
No actual store/body read, driver adoption, public/runtime activation, production
deployment, CIX execution or approval bypass follows from this source packet.
