# CX/MZ/SZ/VE receipt-to-staging bindings

This package delivers **source-input metadata bindings**, not permission to parse
the retained publications or accept a dataset. It is scoped to
`M-STAGING-BIND-20261018-W39` on verified develop
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. The pending handover/PR42 is not its
baseline. No shared core, registry, acquisition grant or runtime admission changes.

## Run and consume

From a source checkout with Python 3.10+:

```sh
python3 -m offmenu.portfolio39 --now 2026-10-18T05:10:00Z --output /private/offmenu/new-plan.json
python3 -m offmenu.portfolio39 --now 2026-10-18T05:10:00Z --previous /private/offmenu/new-plan.json
python3 -m unittest discover -s tests -p test_portfolio39_bindings.py -v
```

`--now` is explicit UTC; there is no implicit clock, fetch, force-download,
revalidate, source-parser or acceptance option. Output creation is exclusive and
rejects symlink components. CLI exit 0 means a diagnostic report was produced,
including held/missing inputs; inspect each `outcome`, `sourceStage` and
`countryTypes`. Exit 2 is a typed CLI input/output failure. No result accepts a
country or makes it gold. Previous keys are only no-op hints: the current pinned
metadata and its selectors are always checked again.

Library callers use `bindings()`, `bind_receipt(binding, receipt_bytes, now=...)`
or `run_portfolio(entries, metadata_provider, now=..., previous=...)`. The static
Python configuration in `offmenu/portfolio39/sources.py` ships under the existing
package finder without a shared packaging edit. It pins exactly five receipt
JSON assets, logical relative names and trusted selectors. A receipt cannot
provide new callbacks, change holds, set approvals or construct a SourceContract.
The only CLI provider reads those bounded static `.json` paths (32 KiB maximum).
Raw body paths/URLs inside a receipt are inert data and are never followed,
statted, rehashed or fetched. There is no global worker dispatch.

## Retained bindings

| Country/source | Metadata extent | Applicability and remaining restriction |
| --- | --- | --- |
| CX `73bcb37d059886266107` | IOT 2023 publisher/rights-access receipt | Price-reference lead only; report original missing, publisher access denial preserved |
| MZ `2d028e62c7a8313207faef47` | Sabores da Zambezia receipt | Recipe-work lead; derivative-use and complete occurrence remain unqualified |
| SZ `bd7949088e671edb6c8f` | IITA recipe-work receipt | Recipe-work lead; 2018 receipt label versus 2019 printed citation preserved, licence version/exceptions and independent review pending |
| VE `4c71db11071d61e5b4a1` | Cavendes/INN booklet receipt | Recipe-work lead; no verified edition or private derivative-use basis |
| VE `afbb485a7f07886b7aec` | Pestana Caracas menu receipt | Provider/menu lead; no qualified derivative-use basis or effective date; not dated item prices |

Exact source/release-context IDs, absolute retained metadata paths, byte counts,
SHA-256 pins and JSON pointers are in `sources.py`. These release-context IDs are
binding identities, **not newly verified publisher editions**. The configuration
retains all real-source holds and unqualified acquisition epochs. It does not
infer commercial reuse from missing custody, public landing access, the IITA
unversioned CC BY symbol, or website software GPL/MIT notices. No source-method
interpretation is attempted where documentation has not supplied units/bases.

Every run exposes all 24 country/type cells: ingredients, recipes, nutrition,
retailers/providers, prices/baskets and dietary references for each country.
Five cells have these metadata leads; the other 19 are explicitly missing a
qualified source binding. Even a represented cell has no selected source
execution or acceptance. Existing SZ literal candidate/review evidence remains
external and unchanged, not reread or promoted by this package.

## Field origins and unknowns

Shared `strict_json`, `canonical`, `timestamp`, `serialization.encode_records`,
`field_origin_errors` and `global_run.StageResult` supply parsing, deterministic
serialization, scalar provenance validation and diagnostic envelopes. No country
parser or shared cache engine is copied.

Records are `source-input-binding` metadata packets. All scalar data, including
zero, false, nulls and array elements, receive exact escaped JSON pointers.
Source origins name the pinned **receipt JSON** and its actual field; they do
not pretend a receipt assertion is an independently checked PDF/workbook cell.
Policy unknowns are explicit nulls with a binding-policy digest and named
constant origin. A source's explicit null is kept as a source origin instead.
No units, bases, dates, yields, ingredient identities or mappings are imputed.

`valid`, `noop`, `missing`, `held`, `malformed` and `stale` describe metadata
binding results. Source-stage operations are always empty and the shared stage
envelope stays held for source execution. Fixed diagnostic codes isolate corrupt
or missing peers without echoing filesystem exceptions or arbitrary receipt
text. Successful metadata alone cannot construct a production SourceContract,
qualify raw inputs, move an accepted pointer or increment a gold count.

## Cache and replay boundary

The cache view is a **metadata-only intent declaration**, not a shared pure
cache planner, a body verification result or an operational cache. Its schema
explicitly reports `intentOnly`, `retainedBodyVerified=false`,
`sharedPureCachePlanner=unsupported-at-selected-baseline`, `fetchAllowed=false`
and zero network requests. Actual caching remains with the shared reviewed
acquisition/runner owner and is unsupported for these held real inputs.

Original-acquisition and last-validation timestamps remain separate. Receipt
observations do not become qualified acquisition epochs: all five real bindings
set `acquisition_epoch_qualified=false`. A recent validation does not reset
original acquisition age; mtime is never used. For the authored qualified fixture,
under 30 days yields zero-download reuse intent, exactly 30 days is stale review
intent, and absent/unqualified/future/inverted timestamps cannot establish
freshness. No intent removes source-use, retention or privacy restrictions.

Content identity binds source, release, exact metadata SHA, selector/hold/epoch
policy and canonical packet bytes, excluding observation clock and filesystem
mtime. Same bytes/policy yield the same key; a previous matching key may report
metadata no-op, but cannot skip current pin verification. Changed receipts require
a newly reviewed binding; they never silently repin a release.

the product integrator result 5798 and addendum are retained as interface evidence:

- the retained baseline-interface receipt
  SHA-256 `f94fbf0a42b5d7906e20ace0416295ae569ee400ddfd770f90a427f803d3b7cb`.
- `late-dependency-addendum.json` in the same directory,
  SHA-256 `73af91948fe0e7529d7c73a022e6f04234544dcfbc48718a5899ed76fa0e3b0d`.

No shared change is required to run this metadata package. If the product maintainer later selects
a standard pure planner, the proposal for the product integrator is a keyword-only
`policy.plan_retained_input(source_id, release_id, input_identity,
original_acquired_at, revalidations, now, retention_status, hold_status)`, returning
identity-bound, zero-I/O/no-download intents and explicit unknown/held diagnostics.
It must not read bodies, authorize operations or let force flags bypass automatic
under-30-day zero-download reuse. This is a proposal only, not a callable used
here. `core.cache_policy` is Wikibooks-specific and `plan_fixture` is registry-only;
neither is spoofed. Real `CachedAcquirer` is never invoked by this package.

## Focused qualification and limits

Authored fixtures cover pin-correct valid/missing/held/malformed/stale input,
lexical values and zero/false/null, escaped nested origins, invalid coordinates,
duplicate/nonfinite/deep JSON, corrupt pins despite a prior no-op key, UTC and
acquisition/validation ordering, metadata size/symlinks, output preservation,
peer isolation, unsupported force flags and no body/socket calls. One synthetic
shared `CachedAcquirer` test uses a fake transport to demonstrate automatic
under-30-day cache reuse without another transport call; it has no real source
or socket. Shared `SourceContract/qualify` checks the authored one-record metadata
candidate and preserves a trusted negative hold. No `accept` call is made.

This is comprehensive for the bounded metadata interface, not exhaustive source
parser, OS isolation or real full-country dataset qualification. Existing guarded
runner/isolation, fresh input manifests, source-specific rights/custody, field
semantics, reviewer appointment and independent acceptance remain required before
any real execution. Finland/Frida, native NO/FR crash, 403/private/credential and
other explicit denied-action holds, raw-on-local executor, production/CIX and DEV7645 custody
remain unchanged.
