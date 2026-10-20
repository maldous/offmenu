# Standalone compact product provenance codec

This is an author candidate for later independent review. It does not wire a
producer, mapper, schema, qualifier, acceptance path or wrapper. It grants no
source-use right and makes no country, gold, capacity or release claim. All tests
use authored synthetic origins and data; they do not invoke a source normalizer.

## Trust and API

`compact_product_origins.py` uses only the Python standard library. The caller
constructs frozen `Context`, `InputPin`, `Member` and `PolicyPin` values from an
independently trusted input manifest and policy evidence. Dictionary bytes never
construct this authority. The context binds exact source/release identifiers,
relative input paths and SHA-256 pins, archive member/table/row/field registries,
policy hashes and permitted labels, output pointer suffixes, rights/scope pins
and an optional clock pin. These hashes bind supplied metadata; the codec does
not read files, prove source values, evaluate transformations or authorize use.

`Codec(context)` seals the dictionary before encoding. `dictionary_bytes` and
`dictionary_sha256` are stable throughout an encode failure or across chunks.
`encode_chunk(record_id, ordinal, entries)` accepts `(pointer, origin)` pairs and
returns canonical UTF-8 JSON plus LF. The caller computes `digest(raw)` and
persists the resulting bytes and pin through its separately authorized store.

`Resolver(context, dictionary_bytes, expected_sha256)` requires both the exact
trusted compilation and the supplied pin. `open_chunk(raw, expected_sha256)`
checks the wire and creates a bounded `LeafResolver`. `resolve(pointer)` returns
one fresh origin tree. `iter_leaves()` yields sorted pointers one at a time.
There is no whole-record expansion method. Validated nodes, references, roots
and prefix inventories are immutable; mutations to returned leaves have no
effect on subsequent resolution. Trusted caller code must not replace internal
codec/resolver attributes or mutate an object concurrently with encoding.

`validate_record(record_id, data, chunks, expected_chunks=N)` checks exact scalar
pointer coverage, distinct groups, pinned chunks, record IDs, sequential chunk
ordinals, byte/work budgets and packing. A base group must be alone in chunk0;
observation chunks contain at most16 complete observation groups and every
nonfinal observation chunk contains16. Missing/extra/reordered chunks and split
groups fail. `data` is inspected without mutation; null, zero, false and empty
strings each require a leaf. Empty containers contribute no scalar pointers.
Nonfinite numbers fail. This method returns `qualified:false, accepted:false`.
Coverage alone cannot prove that an origin correctly explains a source value.

## Wire and semantic preservation

The dictionary is `offmenu-product-origin-dictionary/1` with the exact context.
The symbol pool is the sorted union of field pointers, policy symbols/transforms
and permitted output suffixes. Input/member order determines header indices;
policy order determines policy indices. A chunk pins this dictionary and carries
`offmenu-product-origin-chunk/1`, record ID, ordinal, nodes and root groups.

Nodes are `[0,header,rowOrLine,field]`, optionally followed by a `sourceSpan`,
`[1,policy,symbol]`, or `[2,policy,transform,[childIds...]]`. References point only
backward inside the same chunk. Identical nodes can share storage; repeated
ordered child references are preserved. Derivation inputs are never sorted or
deduplicated. Root groups encode a base `/data` prefix or one escaped nutrient
pointer prefix plus registered suffixes. JSON Pointer `~0` and `~1` retain their
exact meaning. Pointer/key iteration order is not a datum; leaf content and
ordered derivation inputs are preserved.

Only CSV logical data rows and JSONL line/JSON-pointer coordinates are supported.
Rows/lines are positive and within the trusted bounds. CSV member/table/field
must match the registry; CSV record IDs are `<member>:row:<row>`, JSONL IDs are
`line:<line>`. An optional closed `sourceSpan` has `byteStart`, `byteEnd`,
`sha256` and `coordinateSystem:UTF8-bytes`, including valid empty spans.
Unregistered fields, span aliases, unknown keys/kinds/coordinates/policy labels,
bad pins, duplicates, noncanonical wire, noninteger wire numbers, forward/cyclic
references and orphan nodes fail closed. Other legacy origin shapes need a
separately reviewed extension; they are never silently discarded or guessed.

## Bounds

`Limits` may only lower hard ceilings: dictionary1MiB, chunk4MiB, encoded
record16MiB,8192 nodes/chunk,32768 edges/chunk,1024 roots/chunk,131072 roots/record,
8192 chunks/record, derivation depth8, fan-in256, expanded leaf65536 bytes and8192
visits, expanded work512MiB/record and2million visits/record, encoder131072
visits/chunk. Data traversal is capped at depth32 and262144 visits. These are
format/work caps, not measured peak RAM or runtime guarantees. Wire byte caps
precede parsing; typed context registries have bounded counts and string lengths.

For each node the reader computes exact expanded depth, visits and serialized
JSON byte count before resolving anything. Repeated DAG edges each contribute
their expansion cost. An exponential shared graph therefore cannot pass simply
because its stored node count is small. Full expansion never creates more than
one admitted leaf per call. Summed record expansion is a virtual work measure,
not an allocated whole-record buffer. Caller traversal over arbitrary iterables
still needs its own cancellation/timeout and trusted orchestration.

## Conditional source-bound wire proof

`audit_usda_profile` enforces the extra shape used in `usda_wire_bound`:

- Every source is registered CSV and has no span; each derivation has at most5
  inputs. Header IDs<=15, row numbers<=99999999, symbol IDs<=1023, policy IDs<=7,
  local references<=8191 follow from the general codec registries/limits.
- Each base group has at most32 roots and128 distinct reachable nodes.
- Each observation group has at most24 roots and17 source,4 constant and20
  derived distinct reachable nodes. Shared nodes are counted separately in each
  group, conservatively. Serialized escaped prefix length is at most804 bytes,
  covering a fixed namespace and two64-UTF8-byte identifiers at up to6 encoded
  bytes per original byte. The audit checks the actual prefix byte bound.

Additional global obligations are deliberately explicit: for F witnessed food
rows, there are R=2F native records; each has exactly one base group; and there
are exactly O complete observation groups in total, one per witnessed
food_nutrient row. All records/chunks must satisfy the general validator and
profile audit, with greedy16-group packing. These global correspondences are
NOT proved by the standalone codec. A later reviewed producer/wrapper must
verify them against the same witness. Any duplicated observations or different
record multiplicity invalidates this accounting input. No assumption restricts
observations to product records; they may be distributed across all R records.

Using the actual canonical serializer, including LF as a conservative comma
allowance, maximum node lengths are S=21,C=11,D=38 bytes; root pair length T=12.
An observation group costs at most
`G=17S+4C+20D+804+6+24T=2259` bytes. A base costs at most
`B=128*max(S,C,D)+len(JSON('/data'))+6+32T=5261` bytes. The extra6 covers group
brackets/separators. The maximum empty chunk frame Q=1730 bytes uses a256-byte
record ID made entirely of control characters (worst-case JSON escaping),
ordinal8191 and a64-character digest. Empty node/group brackets already included
in Q make addition of the per-item comma allowances conservative.

Let k be the number of records with observations. Then k<=min(O,R) and
`sum(ceil(o_i/16)) <= floor((O+15k)/16)`. Thus the chunk count is at most
`K=R+floor((O+15*min(O,R))/16)` including one base chunk per record. The combined
dictionary and graph wire bound is
`1MiB + K*Q + R*B + O*G`. Sharing/deduplication can only reduce this quantity.

The recorded independent witness supplies F=2101279,O=27195013,R=4202558:
Worker57 terminal result9995 at
`/home/user/Documents/Codex/2026-10-20/worker57-usda-full-witness-execution/terminal-result.json`,
SHA-256 `aba42829675c17293104440f27e5190e2fdf543fdd0b0ec057a33b3a787efb5d`;
Worker64 output review9993 at
`/home/user/Documents/Codex/2026-10-20/worker64-usda-witness-output-review/terminal-output-review.json`,
SHA-256 `b0c4b52d078a6bc50e49d578e0ebef27535083a6cd9e12c3d670998df17b29d7`.
These are consumed as recorded count evidence, without opening original data.
The result packet contains exact evaluated arithmetic. This is a conditional
wire-only theorem, not a sample extrapolation or proof that the real producer
satisfies the profile. It excludes native/reference candidate bytes, DB/indexes,
staging, virtual expansion work, peak RAM, CPU and physical capacity. Spans,
non-USDA shapes and multiple dictionaries are outside this bound.

## Validation and handoff

Run from the isolated checkout:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests /home/user/src/offmenu-preservation-20261020/checkpoint-venv/bin/python -B -m unittest test_compact_product_origins -v
```

Tests cover exact nested roundtrip/order/repeated inputs, CSV/JSONL/spans,
null/zero/false/empty/escaped pointers, trusted dictionary binding and failure
isolation, source/policy registries, malformed/unknown wire, pin and reference
tampering, cycles and expansion bombs, immutable validated state, exact record
coverage/chunk sequence/greedy packing, work caps, profile rejection and
serializer-component/global-count arithmetic including sparse observations
distributed across multiple records. No raw-source, mapper or normalizer runs.

Freeze this three-new-path candidate for independent review through Gateway;
Worker00 alone integrates accepted changes. The held P1 correction, failed25
review route, emitter/shared iterator, USDA binding, product bridge, wrapper and
acceptance/schema wiring remain separate. This candidate does not retry or
substitute for that review. Source/country ownership and all source-use,
privacy, custody, runtime, CIX and production holds remain in place.
