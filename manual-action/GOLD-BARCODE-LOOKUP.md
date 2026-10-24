# Admitted GOLD barcode consumer

`gold_barcode_lookup.py` adds a private-local read-only entry point over a caller
selected, immutable admitted GOLD snapshot. It reuses
`gold_relation_lookup.lookup_recipe_products` for recipe source qualification and
exclusive alternatives. The existing `offmenu.refresh` identifier/detail readers
operate on separate selected-generation stores; this module does not retarget,
repopulate or replace those interfaces.

```sh
python3 -B manual-action/gold_barcode_lookup.py \
  --admission /absolute/path/scoped-admission-receipt.json \
  --admission-sha256 '<independently selected receipt SHA-256>' \
  --barcode '078742003986'
```

The CLI reads at most 1 MiB plus one byte from a single receipt open, rejects
oversize input, hashes that exact buffer and parses the same bytes. Replacing the
receipt path after the read cannot substitute another artifact or notice under
the selected hash. It checks the `ACCEPTED_` disposition and verifies
its exact artifact hash, rejects WAL/SHM/journal sidecars, opens the frozen file
with `mode=ro&immutable=1` and `query_only=ON`, closes it, and verifies the database
bytes and sidecar absence again. This is not discovery or proof that an arbitrary
receipt is authentic: the authorized caller must independently select the
admission, its digest, permitted operation and source purpose. There is no latest
snapshot fallback. Existing live/WAL databases are outside this interface.

Python callers can use `query_snapshot(receipt_path, receipt_sha256, barcode,
...)`, or supply an exclusively owned RO connection and a trusted
`SnapshotSelection` to `read_barcode`. The latter does not independently bind a
caller-supplied connection to a file digest; connection custody/hash selection
belongs to that caller. Do not run concurrent work or install another progress
handler on the same connection during the call.

The current admitted identifier interface is `usda:gtin-upc` assertions with a
string identifier value, exact subject/property binding and scoped support.
Other numeric identifiers (such as SKUs), source IDs, digit substrings or names
are not barcode evidence. Other source identifier properties need their own
qualified interface extension; the response reports `identifierProperties` so
that absence cannot imply global barcode coverage. The raw digit lexeme is
preserved, including leading zeros; integers, trimming and zero padding are
rejected. No GS1 allocation/ownership claim follows.

All qualifying source products are returned; multiple products are explicitly
ambiguous, with no winner. `--selected-product-id` narrows to an exact source
resource ID and never falls back to another product. The recipe reader's existing
`--selections-json` contract requires exact recipe, mention, source key/version,
record and content hash for an alternative branch. Unknown/unselected branches
produce no conditional paths; independent unconditional paths remain eligible.
Scoped choices and qualification holds are included in the response.

`paths` are qualified product → class → source mention → recipe associations.
They retain the actual relation payloads, citations and scopes. The `entities`
map also contains source-qualified candidates examined while evaluating choices;
its presence is not selection or a recommendation. Full source resource records,
occurrences, original names/languages, qualified original/English text records,
source paths, citation rights/attribution and recorded holds remain available.
JSON database columns are decoded once in the response (`payload`, `evidence`,
`context`, `original` and `sourcePayload`); duplicate escaped transport copies of
the same JSON are omitted. All decoded source values, raw original text and
language remain intact. This keeps definition rights within the existing byte
cap without truncating source records or increasing limits.
Only already-qualified English names are displayed; an unsupported English name
is `unknown`, with the original resource preserved. The query calls no model or
translation service and does not silently translate outward.

Nutrition records stay attached to the exact scanned source product and its
qualified source claim/metric. Original numeric/unit payloads, context, basis,
date/method/uncertainty and citations are retained. `--context-json` annotates
matching, different and unknown contexts; it selects no winner, averages nothing
and fills no unknown. Missing or held nutrition is explicit and does not erase
independent structural paths. Canonical/source-reference nutrients never transfer
to a product or recipe, and recipe totals remain null.
Every returned metric also carries its qualified `definition` support records
and citation IDs; distinct definition licences/attributions are retained in the
shared citation map. Absent, invalid, wrongly scoped or nonpublic definition
provenance holds the affected nutrition while independent recipe paths survive.

Menu relationships are returned only when qualified menu entities and actual
supported edges connect to a returned recipe. Predicate and direction are
preserved; no menu membership is invented. No related qualified edges produces
`no-qualified-menu-relationships-found`, not a global menu coverage claim. The
selected admitted batch16 demonstration has no menu entities at all.

Limits apply to every query, including the reused recipe helper:

| Resource | Default | Hard ceiling |
| --- | ---: | ---: |
| Rows returned/read, including support metadata and cached lookups | 10,000 | 20,000 |
| Qualified path rows | 50 | 100 |
| Complete UTF-8 JSON response bytes, including admission notice | 262,144 | 1,048,576 |
| SQLite VM instructions | 1,000,000 | 2,000,000 |
| Query wall-clock seconds | 3 | 10 |
| Source bytes materialized per call | 8 MiB | 8 MiB |
| SQLite cell/row length limit | 1 MiB | 1 MiB |

Receipt input is at most 1 MiB; the file route accepts snapshots up to 1 GiB.
Hash verification is streamed separately from the query VM/time budget. Context
and selection JSON are capped at 4 KiB/32 KiB. Oversize/error results fail with an
explicit error, never a successful truncated value or fake empty result.
The progress handler is cleared and the prior connection length limit restored
on both success and failure. The CLI/API create no indexes or sidecars.

Admitted snapshots lack a support-target index. A bounded per-call in-memory
index of **support metadata only** avoids repeated full support scans by the
existing recipe reader. Resource/text/relation/metric metadata remain bounded;
assertion metadata is filtered in SQL to the exact barcode's source products.
Unrelated source-reference assertion growth does not fill the default index.
All metric definition metadata remain eligible so filtering cannot erase their
rights. Citation bodies load only as required. This is neither a
persistent cache nor a database/schema migration; its rows/bytes share the same
budgets. A smaller row budget or future growth of the remaining metadata can
still produce an honest typed limit error. No limit is automatically raised.
Frozen c612 failed with `row-limit` on admitted batch17 at published defaults;
its successor is tested explicitly on admitted16 and17 at the same defaults.

No response establishes current stock, recall/allergen/private-profile safety,
universal ingredient identity, product substitution, legal business ownership,
complete executable recipes or automatic cooking/planning. All admission and
source-use restrictions remain mandatory. This implementation does not write
GOLD, alter normalizer/source/cache stores or activate production.

Generated tests cover the complete path, lexemes, ambiguous/selected products,
exclusive branches, held/missing evidence and nutrition, original/English name
handling, actual/absent menus, source-reference non-transfer, row/path/byte/VM
limits and cleanup, receipt pins, read-only CLI bytes and sidecars. Run:

```sh
python3 -B -m unittest discover -s manual-action/tests -p test_gold_barcode_lookup.py
```
