# PT / SX / TR / VC metadata staging bindings

This is a portfolio configuration and diagnostics package on accepted snapshot
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. It reads only five pinned retained
receipt JSONs, never a path found inside them. It does not parse original menu,
research, CPI or composition bytes. No source admission, country completion,
translation, nutrient equivalence or golden promotion follows from this package.

Run from the source checkout on the selected local executor:

```sh
python3 -m offmenu.refresh.portfolios.worker38 --now 2026-10-18T00:00:00Z
python3 -m unittest discover -s tests -p test_worker38_staging_bindings.py -v
```

The clock is explicit. The CLI prints diagnostics only and writes no cache or
accepted pointer. Inputs are reviewable declarations in `worker38_sources.py`,
not CLI-selected arbitrary local files. Strict JSON, timestamps and per-field
origins reuse shared `core`, `national_tabular`, `acceptance` and
`field_provenance` helpers. The owned reader bounds bytes on one regular-file
descriptor. There is no copied country engine or shared-core edit.

## Source and field evidence

Each declaration pins the actual retained receipt SHA256 and absolute local executor path.
Receipt selectors are JSON pointers. Generated metadata candidate `data` fields
have matching shared `fieldOrigins`: source/release namespace, receipt digest,
canonical relative input alias, receipt identity and exact literal source field.
Only fields actually selected from verified bytes can be proposed; zero, null
and whitespace remain literal. Receipt identity/field consistency is checked,
not original-table value fidelity. `releaseId` is the internal retained-metadata
binding namespace, not a claim of a publisher release; `releaseLabel`, where
supplied, preserves the receipt's unmodified publisher/revision description.

| Binding | Evidence and applicability | Raw-data limits retained |
| --- | --- | --- |
| PT PortFIR | National composition receipt: country, source, unverified release label | No workbook acquired; no manifest/use/release binding. Source43 is a custody lead, not a transfer. |
| PT O Sargo | Single venue menu2025 receipt: country and release description | Guest/local-reading evidence only. Item locator/transcription use absent; attestation3696 reused. |
| SX CPI | STAT H1-2025 title/release/country; response-completion timestamp | Historical aggregate index, never item prices/basket. Series/page/index-base/use unknown;16 custody remains distinct. |
| TR Fruits32160 | Country/revision/article-level CC BY declaration; response-start timestamp | Research scope, not national composition. Table/measure/unit/basis/method/credit exceptions unknown;3698 reused. |
| VC Bagatelle | Country assertion in selected dinner-menu receipt | Edition notation, structured private dish/price use and item scope unresolved; original50 custody distinct. |

All raw manifest, exact raw selector, native unit, native basis, scope acceptance
and operation-specific source-use decisions are explicit `None` until evidence
supports a reviewed successor. They are never defaulted to per100g, currency,
current offers or a general licence grant. The 24 country/type cells include
every required type, even cells with no proposed source. Their `accepted` and
`countryComplete` values remain false. Five source bindings are not five accepted
datasets, and one source referenced by two types is never summed as two releases.

No new public-document retrieval is performed: this session's direct no-source-
network restriction remains. Article-level or acquisition rights metadata is not
silently promoted to transformation rights. Current missing publisher-specific
documentation/use/exception evidence remains a typed dependency, not proof of a
legal prohibition. Prior source holds and denials remain unchanged.

## Cache and no-op seam

Original acquisition evidence is distinct from `metadataValidatedAt`. SX uses
the exact retained response-completion pointer; TR has response-start evidence
only, explicitly labelled. Other declarations leave the original timestamp
unknown rather than use a validation time. A plan never independently verifies
original bytes; `rawCacheReuseQualified` remains false.

The accepted shared cache helpers are presently a Wikibooks pilot or registered
fixture planner. Production must not substitute those source-specific policies.
Therefore `cache_planner=None` produces `shared-cache-planner-unavailable` and
withholds output. Integration00 has the exact proposed shared interface:

```python
cache_planner(original_acquired_at, input_sha256, *, now)
# pure trusted code; no source file, network, force or download operation
# returns minimumReuseDays>=30, acquisitionAgeDays, decision,
# mtimeUsedForFreshness=False, assetBytesVerifiedByThisPlan=False,
# networkRequests=0
# decision: reuse-verified-cache | conditional-revalidation-required
```

This is an injected reviewed-code interface, never a manifest/CLI plugin. The
tests inject fixed authored protocol responses to exercise the seam; they
do not spoof a production source or reuse the Wikibooks policy. A separate
authored metadata packet qualifies through actual shared SourceContract/qualify,
and candidate corruption is refused by that same validator. Implementing/reviewing the shared pure planner belongs to integration00
under the product maintainer's selection. The production CLI fails closed until that dependency
is resolved; no new cache engine has been installed.

`diagnose` accepts an optional prior build key; `run` accepts prior keys per
source. The content key covers source/release, exact metadata digest, selector
mapping, country/type/role, holds and declared scope/units/use plus original
capture timestamp. Validation clock does not enter the key. Identical eligible
metadata yields `no-op` and the same candidate; changed input/scope produces a
different key. Held, missing, malformed or stale input never gets a successful
no-op. An over30day cache returns a review-required diagnostic and zero network
requests, not an automatic download. No automatic force mode exists.

## Diagnostics and integration boundary

Each source has independent fixed diagnostics. Missing metadata, pin mismatch,
missing selectors, wrong country, duplicate/nonfinite JSON, future/unknown time,
explicit holds, stale inputs and missing/failing/invalid shared planners withhold
the entire source proposal; valid peers still report. No source values or private
exception text are echoed in errors. `metadata-proposal-ready` is possible only
with valid metadata and a trusted planner, and still sets source acceptance and
country completion false. A separate `metadataCandidate` preserves verified
receipt fields/origins even when raw processing or cache intent is held; a pin,
selector or structure failure withholds that projection too. An absent planner
does not prevent independent permitted metadata work. The staged shape is receipt
metadata, not a native nutrient/product/recipe record or production admission.

Remaining dependencies: exact source-use/field-origin selectors/native unit and
basis/scope acceptance for each actual payload; independently reviewed per-source
contracts; shared pure cache planner; independent review and the product integrator's
develop integration. Raw data stays on the selected local executor. Finland/Frida, NO/FR native crash,
403/private/credential denials, production/CIX and DEV7645 boundaries survive.

Authored fixture coverage exercises positive metadata, missing file/selector,
held data despite fresh cache, exact30day/stale boundaries, original versus
validation age, deterministic content/no-op and scope changes, malformed JSON,
overflow, zero/null/whitespace, symlink rejection, isolated peers and planner
failure. No original rows, source downloads or broad old validation are replayed.

### W38-R23-F1 reader correction

The original verify-then-`Path.read_bytes` sequence allowed replacement between
checks to bypass the read ceiling or block on a FIFO. `_read_metadata` now checks
the initial regular file and opens exactly one content descriptor with
`O_NONBLOCK|O_NOFOLLOW`. It verifies descriptor identity before reading, consumes
at most the metadata ceiling plus one overflow-detection byte, then verifies
descriptor/path identity and size before returning any bytes. The path is never
reopened for content. Missing, nonregular, replaced or oversized inputs retain
the existing per-source `metadata-unavailable` result and peer continuation.

`python3 -B -m unittest discover -s tests -p test_worker38_reader_delta.py -v`
passes six focused temporary-file regressions: ordinary bytes with all
`Path.read_bytes` calls forbidden, oversized input before open, FIFO replacement
after initial stat (bounded child, reaped), symlink replacement before open,
growth after descriptor verification with measured read ceiling and valid peer,
and path replacement with a FIFO after open without a content reopen. These use
authored bytes only. Original pure metadata, replay, source-hold and field-origin
coverage is retained unchanged; no real receipts, shared suites or original
18-test suite were rerun for this correction. Same reviewer23 owns delta review.
