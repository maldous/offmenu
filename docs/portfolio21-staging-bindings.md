# Worker 21 country staging bindings

M-STAGING-BIND-20261018-W21; portfolio MD, SJ, TD, UM. Base:
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. This package is a local metadata audit
and an authored-fixture bridge to shared candidate qualification. It installs no
production SourceContract, global handler, downloader, acceptance or gold admission.

## Run and contract

From this checkout, with an existing destination parent:

```sh
python3 -m offmenu.portfolio21 \
  --metadata-root /home/user/src/offmenu-data \
  --as-of 2026-10-18T00:00:00Z \
  --output /absolute/new/portfolio21-metadata.json
python3 -m unittest tests.test_portfolio21_staging -v
```

The explicit timestamp makes replay reproducible; use a fresh truthful UTC time
for a new audit. An identical report returns `reused` without rewriting it. A
different existing report is preserved and rejected. No shared pointer is changed.
The audit opens only nine exact JSON metadata paths declared in `BINDINGS` and
verifies their SHA-256 pins before parsing. It follows no receipt URL, redirect,
rights link, original_path or request path. It does not read, rehash or stat any
source body. Metadata reads share a 1 MiB cumulative budget, checked before each
read; pin mismatch or exhausted budget stops the entire run without a report.
Missing, malformed and stale metadata produce isolated fixed-code diagnostics.
The Linux reader opens each directory and leaf using no-follow descriptors, with
nonblocking opens and a regular-file check before I/O. FIFOs and directories yield
`metadata-not-regular`; unreadable or concurrently replaced/mutated entries yield
fixed isolated diagnostics while valid peers continue. Read bytes still count
against the cumulative budget if a later race check fails. Existing output replay
uses the same bounded reader and rejects nonregular or oversized destinations.
Descriptors close on success and failure. Authored FIFO regressions run only the
corrected successor in subprocesses with a five-second timeout; no predecessor
hang is replayed. Symlink paths are rejected. JSON duplicate keys and nonfinite values are rejected
through the shared strict reader. Selected JSON pointers distinguish absent from
explicit null. Receipt assertion counts are not observed parsed record counts.

Metadata verification uses the existing `StageResult` receipt interface. A
successful metadata check is distinct from the held staging gate. Every real
binding remains held; a synthetic no-hold metadata fixture still cannot install a
production contract. There is no runtime plugin or config-driven permission path.

## Source inputs, field origins and unknowns

| Binding | Evidence and current interpretation | Missing prerequisite / next owner action |
| --- | --- | --- |
| MD Prices 2026-10-12 | Pinned normalized manifest claims 4 MD observations; original archive SHA is a claim only. `/completedAt` is normalization time. `/license`, `/attribution`, `/scope` are declarations. | Gateway obtain the actual raw custodian, original acquisition time, role assets/pins, retained rights/scope evidence and reviewed exact inventory. Owner59 produced a derivative; native custody remains unverified. |
| SJ SSB | Pinned receipt `/release` null, zero retained response bytes, no original. Discontinued Svalbard CPI is not a current SJ basket. | Gateway and historical owner38 resolve exact asset/release, explicit source-use scope, actual custodian and SJ applicability. No Jan Mayen inference. |
| TD WFP markets/prices | Two receipts claim complete CSV originals (355 / 134716 rows; 17637 / 16677432 bytes). Their `/rights_evidence` points to an unqualified package receipt; no body/schema verification in this task. | Worker21 retains ownership. Gateway/source-use reviewer resolve exact publisher release, licence text, intended operations, attribution and custody before authorizing body access. Then bind reviewed CSV selectors and exact inventory through an appropriate shared adapter. |
| TD other leads | JS route, package metadata, advertised PDF answered with HTML, menu API metadata. | Exact permitted original corpus and finite scope still needed. No dataset count from these responses. |
| UM DLA | Receipt reports 403, 510 response bytes, zero source records. | Gateway/historical owner45 identify an independently permitted exact UM asset, rights and applicability. Existing denial means no retry or alternate-host bypass. Native custody remains unverified. |

No nutrition, recipe, current national basket or country-completeness claim follows
from these bindings. MD's four earlier validated price observations remain a partial
price result, with unknown package basis, unit and unitPrice. MD recipe source33's
CC BY-NC-ND 3.0 US acquisition-only restriction remains. TD metadata-planning
approval3588 and receipt metadata qualification do not grant source body access,
transformation or redistribution. Source admission, custody and independent review
remain separate prerequisites for each exact source/release and intended use.

`PRICE_SELECTORS` declares prospective shared Prices adapter field coordinates,
not measured source-cell provenance for retained MD records. It covers all scalar
data fields in the authored fixture. Price amount and unit price retain lexical
source amounts alongside numeric projection. Currency/date/unit pass through;
`price_per` null stays null. No currency conversion, package-size join, serving
basis, per-100g basis or inferred unit price is performed. Retailer fields require
the location_id join; proof_id requires an existing proof. Availability `unknown`
and `dated-observation` are code constants, not source facts. Missing source cells
need explicit reviewed unknown constants; they cannot be represented as observed
null cells. No TD, SJ or UM body column names are invented.

The authored fixture invokes shared `qualify_product_candidate` with a trusted
code-created `SourceContract(fixture=True)`. The shared engine checks rights,
scope, exact bundle membership/pins, declared inventory and semantic qualification
and calls the existing product adapter. The bridge rejects real contracts. Its
candidate remains unaccepted and its private SQLite file is not public output.
The fixture separately exercises shared `field_origin_errors` against explicit
source/derived/constant origin declarations and a pinned policy. The generic
product adapter does not itself emit full `fieldOrigins`; the test does not imply
that it does. Real per-datum origin coverage and semantics remain an integration
prerequisite; source metadata labels cannot construct a trusted contract.

## Cache, replay and shared interface questions

`reuse_plan` uses the shared product adapter minimum of 30 days. It separates
original acquisition age from validation age; validation cannot reset acquisition
age. Missing original acquisition time stays unknown. At and beyond 30 days,
pinned cached input can still be reused locally: the plan never fetches, refreshes
or grants refresh permission. A new publisher release, rights change or invalid
pin needs a separate reviewed action, not an mtime heuristic. Audit verification
time is reported separately from source validation time; source times are unknown
for these real metadata-only bindings.

No generic pure cache planner exists at this pinned base (integrator00 result5798).
The local age calculation is metadata bookkeeping only and does not invoke or
replace a shared acquisition engine. Its absent capability is explicit in reports.

Integrator00 must resolve two shared interface gaps before real production binding:
(1) how a shared acquisition receipt preserves `originalAcquiredAt` separately from
`checkedAt` under revalidation (the current generic acquisition cache uses checkedAt
for its window); (2) where the Prices stage emits full per-datum fieldOrigins and
source-specific semantic validation. No shared core was modified here. Do not
register these portfolio metadata helpers as production stages to work around
those gaps. Independent review and integrator acceptance are required before merge.

## Public methodology references

Official pages consulted 2026-10-18, documentation only, no API/data request:

- [Open Prices API field reference](https://openfoodfacts.github.io/documentation/docs/Open-prices/prices/prices_create/): optional nullable `price_per`, nullable price/currency/date; supports preserving unknowns. Current API docs do not prove a historical export schema or source permissions.
- [Open Prices API licence guidance](https://github.com/openfoodfacts/open-prices/blob/main/API.md): ODbL source attribution/reuse obligations are documented. The software licence is not the data licence. This reference does not clear the retained exact-release/source-use hold.

All existing source/ownership/denied-action holds remain. Production, CIX, UI/runtime
and native NO/FR crash or Finland/Frida holds remain paused; no retry, new worker,
source-body read or acquisition was performed. Morgan retains scheduling and ledger
reconciliation. COUNTRY-QUEUE stays open.

Review correction6190 addresses W11-W21-READER-01 and W11-W21-POINTER-02 only.
The pointer helper rejects negative, leading-zero, non-ASCII or otherwise invalid
array indices and malformed RFC6901 escapes; numeric object keys remain exact
keys. Source declarations, cache semantics and all admission/ownership holds are
unchanged. The frozen successor requires designated reviewer11 delta review.
