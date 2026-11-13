# Portfolio59 retained metadata / staging-input bindings

This package binds existing LV, LY, MA and MC evidence to the shared refresh
interfaces. It opens **no candidate, source, archive or normalized partition**.
No source parser, acquirer, SourceContract, admission, publication or production
binding is registered. Pending PR42 is not a dependency or an accepted baseline.

Owned files are `offmenu/refresh/portfolio59_bindings.py`, the portfolio JSON
configuration, this document and the focused test module. Shared core is unchanged.

## Use

```sh
python3 -m offmenu.refresh.portfolio59_bindings \
  --config config/portfolio59-staging-bindings.json \
  --metadata-envelope /absolute/approved/metadata-envelope.json \
  --now 2026-10-18T00:00:00Z
python3 -m unittest tests.test_portfolio59_bindings
```

An envelope is a JSON object mapping each declared metadata `path` to its exact
UTF-8 text. Those path strings are identifiers: the binder **never opens them**.
The CLI opens only its explicitly supplied configuration and metadata-envelope
files, rejects symlink components and caps each at 2 MiB. Each evidence document
is capped at 256 KiB and must match the configured SHA-256. The CLI does not
construct an envelope from source paths, load plugins, or allow a refresh flag.

The Python interface is `bind_portfolio(config, evidence_bytes, now=UTC_string,
cache_planner=None, previous=None)`. The reviewed portfolio configuration is not
a source permission file. Its requirements/holds are documentary declarations;
the module never elevates them into a trusted SourceContract or use entitlement.
The source metadata manifest SHA is independently pinned, not inferred from a
publisher landing page or a historical worker number.

## Scope and field origins

One Open Prices source binding supplies four country consumers, not four copied
engines. Its exact release is `2026-10-12`, original archive identity
`337f7bc662a8c8f880c457d966fffed7998722b25f2ed460b6194ba01f6653e0`.
One WFP Libya binding retains release-specific unit, currency, price-type,
price-flag and existing review metadata. Its missing shared body adapter remains
`shared-source-adapter-unavailable`, never a guessed CSV parser.

The configuration binds existing author/release/use/method/review reports by
path, hash and JSON pointer. `metadataRecord.provenance.fieldOrigins` is checked
by shared `field_origin_errors`; it points to the **metadata cells**, including
native unit strings, nulls and lexical values. It does not fabricate raw-cell
origins, deserialize the 69,273 candidates or repair historical projection loss.
The remaining raw-field/schema/quotation/ingredient-identity gaps stay typed.

The report lists all 24 country/type cells and their exact retained gap/hold
evidence references. Missing bindings are explicit. The gap references describe
already-retained requirements, not a new complete country inventory or new review.
No whole-country absence or applicability acceptance follows from an empty route.

## Cache, replay and diagnostics

Shared reuse: `strict_json`, `canonical`, `sha`, `timestamp`, `safe_path`,
`field_origin_errors`, `retained_adapters`, `StageResult`, and `MIN_TTL`.
The source identity key uses source/release/manifest hash, excluding country
consumption and validation age. The binding fingerprint also binds the exact
configuration and selected metadata values. Identical currently valid bindings
can return `reused`; a stale or missing document cannot reuse an old fingerprint.

No generic pure cache planner exists in verified develop `abecb99e...`.
`core.cache_policy` is Wikibooks-specific, `plan_fixture` needs a registered
fixture, and `CachedAcquirer` reads bodies and can fetch. None is spoofed or run.
The CLI therefore reports `shared-cache-planner-required` independently of
`metadataBinding.bound`; useful metadata remains bound even when stage readiness
is unsupported. Original acquisition time remains null when not evidenced.
Normalization/fetched-at/validation time is never substituted for acquisition.

An optional **trusted application-code** planner seam receives source identity,
original acquisition time, validation time and an explicit UTC clock. Its result
must preserve acquisition time, declare at least `MIN_TTL` (30 days), permit no
download and return only reuse or revalidation intent. A changed clock, shortened
TTL, download request, exception or unsupported decision gets a fixed diagnostic.
The four-key planner response is closed; it cannot override validation metadata
or attach arbitrary logs to the report.
Tests use an authored pure seam fixture, **not an implemented production TTL
planner**. No 30-day cache execution or body integrity is certified here.

Proposed shared extension for the product integrator: one source-neutral pure planner in
the existing policy module, with exact input identity / acquisition / revalidation
chain validation, explicit missing/held/unknown states, under-30-day reuse intent,
post-window conditional-review intent, zero I/O and no authority activation.
It remains a proposal; this portfolio changes no shared API.

Per-source failures accumulate fixed diagnostics, allowing other valid metadata
bindings to finish. Duplicate JSON keys, nonfinite/overflow values, missing
selectors, changed pins, identity mismatches and absent acquisition evidence are
distinct. CLI malformed-input errors are bounded; no raw logs or data are echoed.
`StageResult` is a metadata-readiness diagnostic, not a source execution receipt.

## Remaining decisions

- Original Open Prices acquisition timestamp, historical adapter/schema and raw
  field-origin binding; all 655 null unit prices / 642 null units remain explicit.
- Thirteen LV/MC `price_per=KILOGRAM` source bases do not establish ingredient
  identity or package size. MA DDM/ADP 2024 date conflicts are not recoded to MAD.
- WFP release-specific unit and `usdprice` / exchange-quotation methodology;
  original source actor remains unestablished beyond historical labels.
- Exact rights/scope/staging acceptance and independently qualified country/type
  requirements. Existing source holds remain; missing custody alone is not a
  newly invented legal prohibition.
- The shared pure planner and any missing generic source adapter require the product maintainer
  selection and integrator review. No source-body work is selected by this code.

Finland/Frida, NO/FR native crashes, 403/certificate/private/credential/actual
denials, raw-on-local executor, DEV7645, production/CIX and later golden-promotion holds are
unchanged. The package requires independent review and integration before a next
request. The authored tests are code evidence, not real-source acceptance.
