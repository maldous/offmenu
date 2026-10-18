# EC / NE / TJ / VU source-input metadata bindings

Base: accepted develop snapshot `abecb99ee1125730ccbc2824b6ec49ffc5cc4302`.
Selection: `M-STAGING-BIND-20261018-W48`. Pending PR42 is not this baseline.

This package projects **pinned acquisition receipt metadata** into deterministic
JSONL staging candidates. It does not parse, normalize, qualify or admit the
described PDFs/workbook. The eight receipt projections are not eight food,
recipe, price or nutrition observations. All 24 country/type cells remain
unassessed; golden promotion remains later.

## Portfolio and evidence

`offmenu.refresh.portfolio48._bindings.BINDINGS` is the static configuration.
It is packaged Python data so the installed interface needs neither Git nor a
workstation-relative JSON resource. `registry()` returns a defensive copy.
Each declaration pins the exact receipt size/SHA256, logical filename, retained
custody locator, source/release identity, scalar JSON-pointer selectors and
source-specific exclusions. Custody locators are provenance references only;
**no path is followed by default**. Explicit receipt mappings are required.

| Country | Bindings | Remaining raw-data boundary |
| --- | --- | --- |
| EC | 2021 gastronomic map; USFQ composition; El Pulpo Season V menu; failed cookbook response | Map/menu reuse unqualified; USFQ noncommercial exclusion retained; cookbook 404 is not a PDF, no retry; actual table/recipe/price selectors not qualified |
| NE | WAFCT 2019 regional workbook receipt; failed INS price metadata | Dictionary and record applicability unqualified; extraction/use scope unresolved; HTTP500 empty metadata response supplies no price dataset and is not retried |
| TJ | Al Mandi embedded menu receipt | Four-page image PDF identity only; original custodian unestablished, no action-specific transcription decision, no row/price dictionary; restricted actor hold preserved |
| VU | Household nutrition analysis 2015 report receipt | Existing native34 metadata handoff retained; no Table15 measure/row contract or action-specific use/attribution acceptance; not live prices or composition |

The static declarations include exact parent packet, source-resolution and
returned-custody manifest pins. These references are not recursively loaded.
Units, denominators, missing-value semantics and unqualified fields are null
with explicit reasons, never guessed from the country, title or file extension.
Data types are *source leads*, not national category-completeness assertions.
The unknown dietary-reference requirements remain visible in the 24-cell report.

## Offline interface

```sh
python3 -B -m offmenu.refresh.portfolio48 --now 2026-10-18T00:00:00Z
python3 -B -m offmenu.refresh.portfolio48 --now 2026-10-18T00:00:00Z \
  --metadata-map /approved/receipt-map.json \
  --candidate-output /approved/foo/metadata-candidate.jsonl
python3 -B -m offmenu.refresh.portfolio48 --now 2026-10-18T00:00:00Z \
  --metadata-map /approved/receipt-map.json \
  --previous-candidate /approved/foo/metadata-candidate.jsonl
```

The explicit map is `{ "ec-map-2021.receipt.json": "path/to/receipt.json" }`;
relative values resolve beside the map. Other keys fail closed. Receipt inputs
are JSON, symlink-free, and bounded to 1 MiB each; the map is at most 64 KiB.
Only the reviewed scalar selector whitelist is emitted. Response headers,
cookies, page observations, original bodies and private URLs are not copied.
An original asset locator inside a receipt is never opened, statted or hashed.

Reports use `valid`, `missing`, `held`, `malformed` and `stale` with fixed
diagnostic codes. One source failure leaves independent metadata peers running.
Held *raw source* declarations can yield permitted metadata candidates while
remaining `held`. A metadata-use hold blocks before the input reader. Unknown
inputs, stale hashes and malformed/duplicate/nonfinite JSON cannot silently
produce metadata rows. No force-download or acquisition option exists.

Exit 2 means incomplete/held metadata or invalid input; it does not erase the
complete per-source diagnostic report. Every shipped raw-source binding remains
held, so a fully supplied historical receipt run still exits 2. Exit 0 in the
pure API tests is not a source/data acceptance claim.

`replay(report, previous_bytes)` recomputes canonical bytes with the shared
serializer. Exact existing byte equality yields `verified-no-op`; a different
candidate yields `metadata-replayed`. A caller-provided digest alone is not
verification. The API checks report hash/size/count consistency. CLI outputs are
exclusive creates: existing artifacts are never overwritten. Publication,
checkpoint recovery and CAS lifecycle remain owned by the shared engine, not a
new country engine in this package. No production `Binding` is registered.

## Provenance, cache and generic integration

The package reuses `strict_json`, `canonical`, `timestamp`, `encode_records`,
`field_origin_errors` and `StageResult`. Each projected scalar has its exact
receipt SHA and JSON-pointer source field, or an explicit policy-pinned constant
for an unknown. Nothing is presented as an original dataset cell. The shared
origin checker validates coverage/identity; production source semantics require
separate source-specific review. Small authored fixtures also exercise the
existing `SourceContract` / `qualify` interface with fixture-only rights/scope
evidence and expected IDs. No source grant is constructed from those fixtures.

Original acquisition time and validation observation are distinct. Only an
evidenced original acquisition selector supplies age. VU's `checkedUTC` is a
validation observation and does not supply original acquisition time. Missing
original time stays unknown. File mtimes and report/replay times never reset age.
Diagnostics expose the minimum 30-day requirement and whether the original
age has elapsed; neither is permission to read cache bodies or refresh sources.

**Typed shared capability gap:** at this base there is no generic pure cache
planner. `core.cache_policy` is Wikibooks-specific; `plan_fixture` is registry
only; `CachedAcquirer` is operational and can read bodies/fetch. None is called
or relabelled here. `plannerCapability` is
`shared-pure-cache-planner-unavailable`, `effectiveDecision` is
`not-enabled-no-source-cache-read`, and `nextOnlineStep` is `none`. These
diagnostics are not a new planner or proof of 30-day production cached reuse.

Proposed shared-interface request to existing integrator00: if Morgan selects
it, provide one pure source-neutral `plan_retained_input` in shared policy,
accepting reviewed source/release/bundle identity, original-acquisition and
revalidation evidence, explicit UTC clock, retention/operation/hold state. It
must validate the exact binding/time chain, preserve original age, return only
under30-day reuse intent or later conditional-review intent, and report unknowns
without I/O/network, source verification, rights activation or fixture identity
spoofing. This package does not implement or require that extension to bind
metadata. Independent review/integration and source-specific staging admission
remain required.

Diagnostics are bounded pure evaluation plus authored-fixture subprocess tests,
not claimed OS network/resource confinement. Reports explicitly mark the OS
boundary unverified and production binding absent. An execution wrapper must
separately qualify that boundary before any future dataset operation.

## Current official documentation observations

On 18 October 2026 the official [FAO WAFCT catalogue](https://www.fao.org/food-composition/tables-and-databases/detail/food-composition-tables/en)
listed Niger within the regional 2019 source and described PDF/electronic
English/French references. This supports regional lead applicability, not a
Niger-specific record or workbook-cell interpretation. No workbook or PDF was
downloaded for this observation.

The official [FAO terms](https://www.fao.org/contact-us/terms/en/) distinguish
publication, statistical-database and other website-content policies and address
attribution and third-party components. The general policy is not assigned as a
licence for either retained FAO asset. Existing exact source-use holds remain;
no publisher contact, terms acceptance or permission expansion occurred.

## Focused checks and review boundary

```sh
python3 -B -m unittest discover -s tests -p 'test_portfolio48_bindings.py' -v
```

Authored receipts cover valid/missing/held/malformed/stale states, source identity
and pointer failures, explicit unknown/zero/native-unit retention, origin-tamper
rejection through shared qualification, peer isolation, symlinks/byte limits,
age versus validation, the exact 30-day boundary, unavailable planner/no network,
immutable output, deterministic metadata replay and no-op. No tests depend on
retained workstation datasets, hidden Git objects or acquisition credentials.

The new code/config/tests/document are portfolio-owned. Shared core, other
country adapters, the old dirty AFCD branch and all source originals remain
unchanged. Provider/base/candidate identities must be reverified at delivery;
independent approval and develop integration precede the next request.
