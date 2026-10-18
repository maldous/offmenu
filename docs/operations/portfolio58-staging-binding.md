# RU, NC, NF and PG metadata bindings

This package binds nine retained source leads to 24 required country/type cells.
It reads only the exact, size-bounded, hash-pinned inspection/receipt JSON named in
`config/staging/portfolio58.json`. It does not open original PDFs, XLS files,
publisher pages or raw datasets. No real `SourceContract`, acquisition admission,
country acceptance or golden promotion is installed.

## Run

From the reviewed checkout on Foo:

```sh
python3 -B -m offmenu.refresh.portfolio_58 --now 2026-10-18T06:00:00Z > /approved/private/report.json
python3 -B -m unittest tests.test_portfolio_58 -v
```

The clock is explicit. Exit 2 means at least one missing, held, malformed, stale
or blocked metadata binding; the JSON report still includes independent peers.
`--previous /approved/private/report.json` supplies prior replay keys only. An
unchanged key is not a rights, source-fidelity or acceptance receipt. The CLI does
not accept source URLs, original paths, rights overrides or a force-download mode.

Shared code supplies strict finite JSON, canonical bytes, timestamps, safe path
handling, `MIN_TTL` and `field_origin_errors`. No country parser or refresh engine
is copied. All source family applicability remains an unaccepted lead. Missing
sources for required types, including all four dietary-reference cells, remain
explicit empty source lists rather than being labelled inapplicable.

## Evidence and field origins

`metadataRow` is a `source-input-metadata` sidecar. Every scalar has an origin:
either an exact JSON pointer in the pinned retained inspection or an authored
configuration constant identified by its policy digest. These are **metadata
origins**, not original cell fidelity. Raw PDF page/BIFF coordinates require a
separate source-specific scope and actual evidence. Missing pointers fail;
explicit null, zero, literal bases and native role/metric labels are preserved.

The source/release, original hash/extent and acquisition receipt are pinned
separately. `acquisitionTimeOrigin` names the exact receipt/time selector when
established. Original response completion is not inferred from request time or
HTTP Last-Modified. Validation time remains null where its original evidence
does not establish it. An adapter invocation does not claim source validation.
Original acquisition and validation clocks never overwrite one another.

The RU scope remains the licensed two-paragraph Russian prose with existing
3784/4568/4571 scoped reviews. No quantities, `5 %` basis, yield, method or IDs are
completed. NC preserves index base December 2021 and separate weight vintages as
literal inspection evidence; converted cells are not original BIFF fidelity.
NF preserves menu/audit roles and unknown currency, effective date and portions.
PG preserves CPI index/percentage/contribution families and the literal June
quarter 2012 base; none becomes currency item prices. Three PG publications have
no acquired original and remain bibliographic/source-use dependencies.

Source-use gaps and actual acquisition custody are separate dependency types.
Missing internal custody does not establish a legal prohibition. Conversely,
public landing access or a metadata hash does not establish a processing grant.
No new publisher documentation claim is needed for this metadata-only package;
existing source-use statements and missing grants remain pinned, unresolved.

## Cache and replay interface

`cacheRequest` contains original acquisition time, separate validation time,
explicit clock, exact original digest, minimum 30 days, holds and scope. Held
bindings never invoke a planner. The optional callable must be selected shared
reviewed code, return no network requests, retain a minimum 30-day window and
return either `reuse-retained-metadata` or `review-required-no-download`.

There is currently no generic pure production metadata planner on this baseline:
`core.cache_policy` hardcodes Wikibooks, `policy.plan_fixture` requires registered
fixtures, and `CachedAcquirer.acquire` may hash bodies and fetch. None is invoked
or spoofed. An absent planner yields `shared-pure-cache-planner-not-bound`.
The proposed interface was sent to integrator00; shared-core changes are outside
this worker's ownership. Tests inject small authored interface fixtures only.
They demonstrate stale/reuse outcome handling, not implemented production cache
age calculation, cache byte validity or actual 30-day reusable source entitlement.

Replay identity binds source/release, original bytes identity, selected data,
selectors, operation scope, holds and evidence pins. Validation-only clock changes
do not trigger a new transform key; the diagnostic origin sidecar is still newly
bound. Changed selected content or rights/scope evidence invalidates the key.
The command emits a report to stdout and never updates a cache/accepted pointer.

## Diagnostics and review boundary

Authored fixtures exercise valid, missing, held, malformed and stale inputs,
null/zero fidelity, pin tampering, duplicate/nonfinite JSON, bad pointers, future
and naive clocks, validation-before-acquisition, changed content/evidence,
validation-only no-op, planner failures, TTL/network refusal, symlinks and peer
isolation. Shared field-origin tests should remain green. Original-source
validation, production payload qualification and comprehensive global diagnostics
are not claimed by these tests.

Required next inputs: integrator-selected shared planner; NC original BIFF
evidence/operation scope; NF actual custody/use/date/currency/portion evidence;
PG authorized publication originals/extent/use and actual custody; independent
review and develop integration of this exact commit. Source bodies and raw data
stay on Foo. Finland/Frida, native NO/FR crash, denied routes, mandatory review,
production/CIX and the separate DEV7645 custodian remain unchanged.
