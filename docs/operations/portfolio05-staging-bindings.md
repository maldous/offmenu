# Worker05 BB/JO/PY metadata staging bindings

Selected request: `M-STAGING-BIND-20261018-W05`. Base is verified develop
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. Pending PR42 is not this baseline.
Only `portfolio05.py`, its owned Python source configuration, this document and portfolio
tests belong to this package. Shared core, registry and source engines are unchanged.

## Runnable interface

From this checkout:

```sh
python3 -B -m offmenu.refresh.portfolio05 --now 2026-10-18T06:00:00Z
python3 -B -m offmenu.refresh.portfolio05 --now 2026-10-18T06:00:00Z --previous /private/foo/metadata-diagnostics.json
python3 -B -m unittest discover -s tests -p test_portfolio05_bindings.py -v
```

The first command emits canonical JSON on stdout; redirect it only to a private
Foo report directory. The second compares per-candidate content hashes with an
existing report. It does not persist candidates or change accepted/cache pointers.
`unchangedContentNoOp` means no candidate-content change and no data write; checking
metadata pins still reads the eight receipts. No automatic download/revalidation,
force flag, external plugin or raw input path is exposed. Runtime uses the
reviewed fixed source configuration; editing it requires source review.

The optional previous-report reader rejects nonregular files before reading by
using nonblocking/no-follow descriptor opens and directory-fd traversal. It checks
the opened regular descriptor's size and before/after identity/change metadata,
reads at most1MiB, then validates the prior source-ID/digest map. Invalid previous
inputs return exit2 and a fixed stderr diagnostic before current metadata reads.
Regular report bytes/mtime are preserved, including on replay. This owned boundary
repair does not change the shared reader/core or source processing scope.

`bind(spec, receipt_bytes, now=..., previous_candidate_sha256=...)` is a pure
portfolio adapter. `inspect_portfolio(now=..., previous=...)` reads only bounded,
exactly pinned receipt files. It never follows original-artifact paths. Duplicate
JSON keys, receipt drift, missing fields, invalid country/clock/field types and
unavailable files produce fixed diagnostics isolated to each source. Missing,
malformed, held, stale and valid are distinct outcomes; stale means the prior
metadata candidate hash differs from current content/policy, not a cache-age
decision. Holds take precedence. Diagnostics contain no source
body, unselected receipt fields, signed URLs or exception contents.

## Metadata manifest and field origins

`portfolio05_sources.py` pins eight receipts and associated retained metadata
manifests/custody evidence. These are declarations of exact retained scope, not
downloads or proof that every referenced raw body currently exists. BB newsletter,
school guidelines and BioIsland promotion; JO book, FAO print-only catalogue and
publisher HTML; PY UNICEF publication and failed Senatur lead remain distinct.
All six required data types are listed for each source, alongside actual lead
roles and empty accepted-type inventories. A promotional publication never becomes
a register; a catalogue never becomes analytical tables; an HTTP403 error is not
a dataset. This package supplies no recipe or measured nutrient/price records.

The configuration is an inert owned Python declaration imported with the package,
not a JSON file that depends on an undeclared package-data convention. The normal
setuptools wheel contains it without any shared packaging change. An offline
authored smoke test builds a wheel from source in scratch, extracts it outside
the checkout, imports with isolated Python and loads all eight held declarations
with receipt/resource reads prohibited. The returned configuration is a defensive
copy. This proves installed-artifact configuration availability; it does not
activate source paths, source parsing, rights or staging acceptance.

The only proposed record kind is `document-reference-metadata`. `inputFiles`
describes a logical bundle `metadata/receipt.json` with exact bytes/hash.
`fieldOrigins` binds country, recorded release/role/access basis and timestamps to
receipt JSON pointers. Null native unit/basis and the non-measurement marker are
explicit policy constants whose hash is the exact reviewed spec. Their nulls do
not assert that missing recipe amounts have no units. Source release literals
retain uncertainty; filenames and PDF page totals do not invent editions.

Shared `field_provenance.field_origin_errors` checks all scalar origins. The
portfolio wrapper also resolves actual receipt values and compares each source
field. Shared `core.strict_json`, `core.verify`, canonical serialization and
`serialization.encode_records` are reused. Tests hand the authored metadata
candidate to shared `acceptance.qualify` using a trusted **test-code**
`SourceContract(fixture=True)`. Actual-source contracts are not generated from
manifests or CLI flags. No real `accept`, registry/global Binding, source admission
or whole-country acceptance is installed.

## Acquisition clock, validation age and replay

Acquisition pointers identify recorded original request starts (`/utc`,
`/response/utc`, `/started_utc`); their meaning is explicit. They do not newly prove
successful byte completion or an independently qualified original cache record.
Validation/finalization pointers are kept separately. They never reset original
acquisition age. Filesystem mtime is unused.

The pinned develop has **no generic pure cache planner**. The wrapper reports
`unsupported-real-source-cache-planner`, unknown freshness, the required30day
minimum and observed age. It does not call the Wikibooks-specific
`core.cache_policy`, registry-only `plan_fixture`, or operational/body-reading
`CachedAcquirer`. It neither invents a new planner nor claims reuse eligibility at
any age. Downloads stay disabled. Tests cover age30 with freshness still unknown,
validation that cannot reset age, unchanged content and stale prior-candidate
hashes after content/policy change. Holds survive all observations.

## Current official documentation research

Checked18October2026, HTML documentation only; no publication PDFs were opened.

- [UNICEF legal information](https://www.unicef.org/legal#terms-of-use), sections
  “Copyright” and “The UNICEF Web Site”: describes personal/educational use and
  permission requirements for other uses or reproduction/translation beyond a
  de minimis portion. It also notes third-party rights in some publications.
  This general documentation does not decide the exact Paraguay recipe operation,
  required credit, applicable exception or third-party material. Those stay held.
- [ACOR publisher metadata](https://publications.acorjordan.org/chapters/jordanian-traditional-cuisine-arabic/)
  offers full-text access and displays a generic access legend plus website
  copyright. Neither supplies an edition-specific derivative licence. The
  retained book receipt's reservation remains binding; no book body was read.
- [Barbados National Nutrition Centre](https://nutritioncentre.health.gov.bb/)
  publisher homepage was reachable as metadata; no source-specific derivative
  licence was established. A follow-up web-tool line read returned Internal Error;
  no retry or access workaround was attempted. The retained acquisition-only
  receipt conditions remain. The Export Barbados promotion's specific reuse and
  field scope are likewise unestablished by the retained custody reply.

No publisher was contacted. Public documentation is evidence, not a synthesized
legal decision, new entitlement or removal of an existing explicit hold.

## Typed remaining blockers and integrator interface proposal

| Type | Exact remaining dependency | Owner / next action |
| --- | --- | --- |
| Integration/review | This committed package needs independent scope/code review and accepted-develop integration | Integrator00/Morgan select reviewer, integrate through normal gates; no push by Worker05 |
| Shared interface | No general pure cache planner; current capability explicitly unsupported, not all metadata bindings blocked | Integrator00/Morgan alone may select one shared `policy.plan_retained_input` per result5798; reviewed identity/evidence/hold binding, original age, unknown-no-download, no execution or admission. Worker05 did not edit shared core or copy a planner |
| BB source use/scope | Exact operation-specific use/credit/exception decisions and finite source fields absent in scoped36reply | Morgan selects new lawful evidence/operation; do not repeat identical request to36 |
| JO source use/scope | Exact primary clause/page and applicable private annotation decision/credit absent in49reply | Morgan/right-scope owner resolves; recorded copying/transmission/translation hold remains |
| PY source use/selectors | Exact lawful-use decision, credit and recipe ID/page/ingredient/method/measure/yield selectors absent in40reply | Morgan selects qualified inputs; no repeated identical request to40 |
| Source denial | Senatur403 | Preserve no-retry/no-body-processing; no alternate actor/route |
| Actual staging acceptance | Reviewed real-source contract, measured expected inventory, field semantics and rights not supplied | Remains later selection; authored fixture pass and metadata proposals do not satisfy dataset acceptance |

Finland/Frida, native NO/FR crash restrictions, private/credential/source holds,
mandatory auto_review, production/CIX pause and separate DEV7645 custody survive.
Raw stays Foo. No shared engine fork, source-body processing, acquisition,
source-test replay, permission change or accepted pointer movement occurred.
