# Independent private retained-product witness

`offmenu.refresh.product_input_witness.witness_retained_input` traverses one
reviewed original and derives source-native IDs independently. It never reads a
candidate, imports a candidate ID projector, accepts data, acquires sources,
activates runtime or changes a country/corpus ledger. Its only adapter dependency
is the existing bounded ZIP central-directory reader; custody, path, canonical
JSON and exact evidence-bundle checks reuse existing machinery.

`WitnessContract` is trusted Python configuration, never loaded from source or
proposal JSON. `product_witness_bindings.retained_witness_contract` freezes exact
retained OFF and USDA original pins and USDA34 CSV headers/35 member paths from
the9467 metadata witness. It requires separately reviewed rights, scope and clock
Assets. Worker26 owns actual operation/binder evidence qualification; these
helpers confer no permission by themselves. No old metadata-only assignment is a
publisher prohibition. Private data retain/parse/transform and public operations
remain separate. Original acquisition/downloader are never guessed.

The evidence bundle is exactly rights, scope and clock files. Passing the separate
`input_root` reads the original in place by its exact relative filename and hash;
unrelated corpus files are not inventoried. With no `input_root`, all four files
must form the exact bundle. Source/evidence/output paths reject symlinks and
overlap. All evidence hashes and exact source/release/scope/operation bindings are
checked before original custody reads. Capacity/floor checks precede original
hashing/allocation. Original and evidence hashes are rechecked after traversal.
Evidence preflight reads each metadata asset into one bounded descriptor buffer,
checks its exact size/SHA and regular-file/path/descriptor identity before and
after reading, and parses only those verified bytes. It does not reopen a path
after hashing. Reads reject leaf symlinks/non-regular files without blocking on
FIFOs, and check the operation deadline around every chunk and metadata parse.
Growth, replacement, oversized data or deadline expiry fails before original
custody reads or scratch allocation. The post-traversal checks remain mandatory.
Original custody verification and gzip/ZIP parsing share one retained regular-file
descriptor opened with nonblocking/no-follow flags. Identity, size and the deadline
are checked around reads; path replacement, including a FIFO swap, fails closed
without a blocking pathname reopen. The descriptor is hashed before scratch is
created and rehashed after traversal. Metadata postchecks still use verified
bounded buffers.

## Denominator and IDs

OFF: every decompressed JSONL line is a row, including blank lines. Invalid UTF8,
JSON (including duplicate object keys) or object shapes are `invalid`; missing,
numeric or malformed code is `quarantined`. A code is a source string of4–32
digits with leading zeroes intact. Repeated native codes are `duplicate`, with
same-content versus conflicting-content counts; original ordinal diagnostics are
retained. No historical61 duplicates or385 quarantines disappear into a filtered
expected count.

USDA: the exact complete member set is mandatory. All CSVs are streamed without
extraction, with exact declared headers, strict UTF8/CSV and logical multiline
record bounds. Every non-CSV companion is fully traversed for ZIP integrity.
Malformed row width is `invalid`; missing declared native keys are `quarantined`;
repeated keys are `duplicate`. Keyless supporting tables contribute every row as
valid/keyless, explicitly without a uniqueness claim or synthetic native ID.
Columns named `id` use that native key; food/branded_food use `fdc_id`; others are
explicitly keyless. Required joins include branded_food→food and
food_nutrient→food/nutrient. The witness reports these joins, not an invented
all-relational-schema acceptance. Branded GTIN and market-acquisition UPC remain
distinct source columns, never a GTIN uniqueness oracle.

`valid + duplicate + invalid + quarantined == rows` on every fully traversed
table. `keyless` is a subset of valid; `joinFailures` is orthogonal. Every anomaly
has a deterministic private table/member/row/category diagnostic. Invalid stream
framing, corrupt compression, uncertain CSV boundaries and resource/time limits
stop with `fullDenominatorTraversed=false`, explicit errors and null expected
count/ID fields; observed counts cover only the identified prefix. No tail is
silently treated as traversed. Partial native-ID digests are diagnostic only.
An observed row interrupted before disposition is counted in `unclassifiedRows`;
`unparsedTailPossible` explicitly retains unknown tail scope on incomplete runs.

Full traversal is separate from a clean witness. Only a fully traversed scope
without duplicate/invalid/quarantined/join findings emits `expectedRecords` and
`expectedSortedIdSha256`. Independently selected OFF code / USDA food keys yield
two potential IDs each (`nutrientProfile`, `product`), sorted with SQLite BINARY;
canonical JSON ID string plus LF feeds SHA256. This agrees with the documented
acceptance digest format without using candidate contents as an oracle. It does
not prove nutrient semantics, field origins, English output or source acceptance.
`policySha256` retains a snapshot of this module file taken at operation entry,
before source traversal. Replacing or removing that file during a long traversal
cannot relabel the receipt with a later revision. It is a pre-traversal source-file
pin; the surrounding reviewed runtime/contract evidence remains separate.
Zero source rows yield zero expected rows, not a valid nonempty source acceptance.

## Narrow private scratch budget

The existing Worker61 `SharedBudget` remains unchanged: its managed small-file
scope does not admit SQLite. This witness proposes a distinct **per-operation
budget extension** for existing64 review/00 integration, not another allocator or
permission framework. One source at a time, one fresh0700 private scratch tree:

| Source | SQLite key/reference DB cap | Diagnostics cap | Result/control slack | Total ceiling |
|---|---:|---:|---:|---:|
| OFF |8GiB |2GiB−2MiB |1MiB result+1MiB slack |10GiB |
| USDA |24GiB |4GiB−2MiB |1MiB result+1MiB slack |28GiB |

These are prospective fail-closed ceilings, not measured sufficiency or actual
needs. No original bodies, normalized candidates or field-origin outputs are
staged. SQLite `max_page_count` bounds the DB; its existing primary indexes supply
all ordering. Query plans requiring temporary B-tree sort scratch are refused.
Journaling is off only for this disposable private DB. No SQL extension/plugins
or external sorting subprocesses are used. Cache is16MiB; the one-record parse
bound is8MiB. Native keys are at most64 UTF8 bytes; oversized keys stop incomplete,
never truncate. The Python CSV field cap is reported and an exceeded cap fails
incomplete. The real scope caps are checked even if callers supply custom limits.
Each real DB, diagnostic and result component is also capped individually at the
table values; reducing another component cannot increase one of those ceilings.

Fresh free bytes must cover the new complete witness ceiling **plus** the current
protected amount including its20GiB floor. Existing allocated originals/retained
files are already reflected in free space. Outstanding envelopes remain charged;
no other owner's reservation is released. At least10000 free inodes remain
protected. Free space/inodes and deadlines are checked throughout streaming and
ID traversal. SQLite has a deadline progress handler as well. Limits do not imply
atomic reservation against other writers: Gateway must reconcile actual concurrent
commitments and select the one source before execution.

The2026-10-20 Worker57 capacity packet freshly reads the existing ledger and
reservation metadata. It retains the higher9341 floor-inclusive conservative
guard88,552,243,200B, including the49-country/preparation envelopes and VE extra,
rather than inventing a universal outstanding total. Physical allocation receipts
are recorded separately and not subtracted again from free space. Subsequent
capacity-changing events must be reconciled at selection.

Existing destinations are refused. A completed or handled-incomplete attempt
retains diagnostics and publishes its terminal result last without replacement,
removes only its own temporary DB,
and needs a new destination to retry. Unexpected IO errors that prevent even a
terminal receipt clean only the fresh own staging directory and raise; such an
exception is never a successful or complete witness. No existing output is
repaired, rewritten or silently reused.
Publication prepares both hard links in a0700 child of the caller's existing
private staging directory, using directory descriptors. Linux `renameat2` with
`RENAME_NOREPLACE` atomically transfers the complete private directory to the final
name. There is no final-path mkdir, adoption of its later inode, partial-file
publication, or final-path rollback deletion. An existing file, symlink or even
empty foreign directory makes the kernel refuse publication without overwrite.
The output inherits the prepared directory's0700 mode. The private staging
container must already be caller-owned0700 and contain exactly the two produced
files; arbitrary foreign/nonprivate containers are refused.

Ordinary first/second-link, private-directory-open or atomic-rename failures clean
only private staging and allow retry. If atomic transfer may already have
committed, missing source entry means cleanup must preserve the published output;
the caller reports uncertainty and reconciles that output before any retry.
Unsupported atomic no-overwrite publication fails closed, without an overwrite
rename fallback. No final destination is ever removed as publication cleanup.

## Selected execution shape

After review/integration,26's exact evidence Assets and Gateway's current capacity
selection complete this API call (no real command is run by the author task):

```python
contract = retained_witness_contract(source, rights_asset, scope_asset, clock_asset)
limits = retained_witness_limits(source, protected_bytes_including_floor=current_guard)
result = witness_retained_input(contract, evidence_bundle, fresh_private_destination,
                               input_root=retained_originals, limits=limits)
```

`tools/data-processing/witness_retained_products.py` provides this exact fixed-source API as a
CLI. Evidence arguments are explicit `relative-path:bytes:sha256` pins, never an
arbitrary JSON contract/plugin. It returns2 for an incomplete or anomalous
witness,0 only for a clean scope witness, never a data-acceptance claim. Required
arguments are source, evidence bundle, originals root, fresh destination, rights,
scope, clock and protected bytes including floor. Before a selected run,26's
reviewed packet supplies the three exact evidence pins and matching scope/clock
files; missing pins are a concrete input dependency, not a publisher prohibition.

The exact source-specific pins, operation packet reference, capacity cut and
future invocation belong in the existing owner artifacts and Gateway ledger.
`accepted:false`, no publication/country completion, original custody and all
source/rights/denial/production/CIX holds persist. Unresolved actual operation
restrictions must be named individually; internal scratch policy is not a licence
denial or blanket request for renewed publisher approval.

Synthetic verification uses generated sources only:

```sh
python -B -m unittest discover -s tests -p test_product_input_witness.py
python -B -m unittest discover -s tests -p 'test_product*.py'
```
