# DJ / NA / TG / VI receipt-to-staging bindings

Selected scope: `M-STAGING-BIND-20261018-W44`. Proposal base is verified develop
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. This package owns only
`portfolio44.py`, its catalog, focused tests/fixture and these documents. No core,
schema, curation, source registry or runtime admission is changed.

## Runnable interface

```sh
python3 -m unittest tests.test_portfolio44 -v
python3 -m offmenu.refresh.portfolio44 --binding na-asset-12 \
  --validated-at 2026-10-18T00:00:00Z --now 2026-10-18T00:00:00Z \
  --output /path/to/new/private-metadata-output
```

The CLI reads only the exact code-pinned JSON receipt; it never opens the source
PDF/HTML/body referenced inside it. `candidate.jsonl` uses the shared singleton
packet serializer and `source-input-reference` kind. `manifest.json` identifies
**receipt-metadata-only** scope. Exit 2 for a held real input is intentional and
can still accompany a useful metadata reference artifact. Exit 0 means valid
metadata, not accepted food records, a source grant or country completion.

`bind_receipt` is pure; `bind_many` isolates each loader/format failure. All error
messages are fixed codes. Inputs are bounded at 64 KiB, exact size/hash checked,
strict JSON decoded, with missing/null/unbound kept distinct. Output-directory
reuse requires identical candidate bytes and a matching manifest; it leaves their
bytes and mtimes unchanged. Changed/tampered output requires a new directory.

Every scalar under `/data` has shared `fieldOrigins` coverage. Receipt values
carry exact JSON pointers and receipt pins; missing declarations, scope labels,
holds and unknown markers are reviewed policy constants, not inferred cells.
`semantic_errors` also checks actual values against the permitted receipt, so
origin coverage alone cannot bless a changed value. It is compatible with the
shared `SourceContract.semantic_validator` callback. Only authored fixtures are
qualified in the tests; no production contract is constructed from a receipt.

## Exact retained metadata inventory and applicability

The catalog pins fourteen response references from corrected identity result4924:

the retained `owner-44/B03-W44-identity-resolution/corrected-identity-index.json` evidence artifact

SHA256 `889a6b71ed27a226c1d0bc942d5d5c6bf899115a86aee09a2139fddb02224c1a`.
That index retains fifteen lineage links: the CCD June2022 PDF's two receipts
refer to one reported asset. Three previously unbound references resolve to
retained Djibonline, ODPIC and LANAA landing pages, not finite datasets.

| Country | Metadata references | Narrow context; actual record input remains held |
| --- | --- | --- |
| DJ | 11 | CCD directory; merchant menu/link pages; two failed404 responses; INSTAD redirect/non-PDF; Djibonline/ODPIC/LANAA discovery references |
| NA | 1 | February2026 CPI bulletin, statistical index rather than retail offers |
| TG | 1 | IITA training dataset metadata; actual data embargo remains |
| VI | 1 | USDA aggregate census publication, not retail prices or individual-farm data |

`domain` and country are reviewed discovery-context labels, not accepted domain
coverage. Ingredients, recipes, nutrition, retailers/providers, prices/baskets
and dietary references remain unfinished for each country. No category is
declared not applicable. The metadata snapshot release is `receipt-<hashprefix>`;
it does not invent a source edition. Native units/bases and actual row selectors
are explicitly unbound. All real bindings retain body-operation holds; missing
internal custody alone is not asserted to be a legal prohibition.

The source receipts contain recorded owner labels and sometimes producer/thread
pointers; they do not establish current exclusive source custody. ODPIC response
5173 explicitly retains `CUSTODIAN_UNESTABLISHED` and no selected finite release
or dataset-specific use decision. It must not be routed back as a new question.

## Acquisition, validation and cache are separate

`originalAcquiredAt` is a reported response acquisition only, never a validated
dataset acquisition. Failed/redirect/non-PDF responses have it unbound. A receipt
creation time is not substituted for a missing original acquisition time.
`metadataValidatedAt` is supplied for the current metadata-pin check and does not
alter source provenance or claim a publisher validation. An old validation is
reported stale at thirty days; rechecking metadata cannot reset body acquisition
or grant refresh. Candidate identity excludes this scheduling/diagnostic age.

There is **no source-neutral pure cache planner at the pinned baseline**.
`body_capability` explicitly reports it unsupported. This package neither spoofs
Wikibooks/fixture policy identities nor copies a cache engine. The shared
`CachedAcquirer` is exercised only with small authored bytes and a fake transport:
29-day automatic refresh performs zero calls, day30 reuse is stale, a fixture304
preserves original acquisition while updating checked time, and the subsequent
automatic call reuses it. These operational fixture checks are not production
cache, retention-rights or source-planner acceptance. No live transport is used.

Minimum30day cached reuse and no automatic download inside that window remain
the country contract. Real private/held source cache capability, retention/use,
refresh manifests, field origins, units/bases, source edition/extent and reviewed
native adapters remain typed dependencies. Golden promotion is later.

## Public documentation checked without acquiring data

The [NSA February2026 document page](https://nsa.org.na/document/namibia-cpi-bulletin-february-2026/)
identifies a PDF in its NCPI category; it supplies no table selector or
dataset-specific derivative permission. The [USDA 2022 publication index](https://www.nass.usda.gov/Publications/AgCensus/2022/index.php)
lists the Virgin Islands release dated March27,2025; the
[USDA overview](https://www.nass.usda.gov/AgCensus/index.php) distinguishes Virgin
Islands agriculture in2023. These publisher catalog facts are supplementary
edition context, not proof of printed table fields, suppression handling,
third-party exceptions, source use or country acceptance. No linked dataset/PDF
was downloaded or opened. No denied DJ/TG route was revisited.

## Review and integration

Fixtures cover ready/missing/held/malformed/stale metadata, field-origin/value
tampering, explicit nulls, deterministic replay, changed policy, no-op output,
peer isolation, shared qualification, and the shared fixture cache window.
The source-specific production callback/contracts are not installed. Existing00
must capture the candidate/base/provider at the delivery gate and obtain the
designated independent review before develop integration. Keep
old worker44 checkout, raw local executor holdings, Finland/Frida/NO-FR crash restrictions,
actual denials, production/CIX and DEV7645 custody unchanged.

## Bounded review correction: W32-W44-15CE-F1 / F2

Runtime receipt, prior-manifest and existing-candidate reads now open a
nonblocking/nofollow descriptor, check the opened inode is a bounded regular
file, and read that same descriptor. Identity/size/timestamps are checked after
reading and against the current path. FIFO replacement cannot force a blocking
reopen. New output files are exclusive creations; existing no-op bytes stay
untouched. This is an owned reader correction, not a shared-core change.

Selected values are limited to64 nesting levels before recursive origin/JSON
traversal. Unselected metadata is not subjected to that selected-value policy.
Parser or traversal RecursionError is also converted to a fixed malformed
diagnostic and cannot suppress later peers. Focused regressions cover both
reported failures and required normal/no-op/qualification controls; previous
unaffected source and shared-batch evidence is reused, not replayed.

## PR48 comment4306286782: identical partial output recovery

Each new file is completely staged and flushed in the private output directory
before exclusive publication. A failure during manifest staging/publication may
leave the already-complete candidate visible. An identical retry verifies that
candidate with the existing descriptor reader, then publishes only the missing
manifest; a matching manifest-only pair can similarly complete its candidate.
The result reports `recovered-identical-partial`. The next run is a no-op.

Mismatching, malformed, symlinked or nonregular existing members remain errors;
they are never overwritten or deleted. Exception cleanup removes only this
invocation's staging temporary. This is bounded identical-pair recovery, **not**
universal two-output crash atomicity, crash-orphan cleanup or a concurrency lock.
Source operations, admission and rights remain closed.

Manifest identity uses the existing canonical JSON serialization at both the
prepublication and readback checks. This preserves JSON scalar types, refusing
`true` in place of `1` or `0` in place of `false`, while accepting differences in
whitespace and object key order. A mismatching manifest-only output is preserved
and its missing candidate is not published. Focused authored controls cover both
boundaries and legitimate recovery followed by an unchanged no-op.
