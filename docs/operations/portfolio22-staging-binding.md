# Portfolio22 retained input / staging metadata binding

Scope: CF, BY, CC and CD. This is a deterministic **metadata/code** binding, not
new country-body processing or data acceptance. The baseline is remote-verified
develop `abecb99ee1125730ccbc2824b6ec49ffc5cc4302`; pending PR42 is excluded.

The shipped config binds CF WFP resource `cb558a54-357a-4bcd-9edd-30caf65b1bd7`,
revision `2026-10-11T10:10:05.452162`, to exact retained original/candidate byte
declarations, source manifests, publisher method/licence metadata and scoped
reviews. These pins are declarations here: **no source or candidate body is
opened or hashed**. The CLI reads only its bounded metadata evidence file.

## Interface and outcomes

`expected_evidence(country)` returns a template with validation time unknown.
It is not a validation receipt. A caller supplies an actually evidenced UTC
`lastValidatedAt` and explicit UTC `now`. Example with authored metadata only:

```python
from offmenu.refresh.portfolio22 import expected_evidence, assess, candidate_bytes
e = expected_evidence('CF')
e['lastValidatedAt'] = '2026-10-17T12:00:00Z'  # authored example, not a new source check
r = assess('CF', e, now='2026-10-18T12:00:00Z')
assert r['state'] == 'ready' and not r['sourceProcessingAllowed']
metadata_jsonl = candidate_bytes(r)
```

The repeatable no-AI CLI is:

```sh
python -m offmenu.refresh.portfolio22 CF evidence.json --now 2026-10-18T12:00:00Z
```

Exit0 means a metadata descriptor is ready/unchanged; exit2 is a typed
missing/held/malformed/stale result. It never means a dataset was accepted.
`stage` uses shared `global_run.StageResult` diagnostics. `remainingBlockers`
keeps source-body, trusted SourceContract, framing and field/use acceptance
separate from successful metadata validation. Explicit `held:true` fails closed.
BY/CC/CD templates report their exact original/use gaps; no release, original
acquisition date, unit or identity is invented to make them ready.

`bindingKey` is the shared qualification fingerprint of pinned code config and
content/selector semantics. Validation clocks are outside that key. The same key
returns `no-op`; deterministic metadata output uses the shared singleton-array
JSONL serializer. Validation time never overwrites original acquisition.

At less than the shared30-day minimum, the plan requests declared retained-input
reuse with zero network. At exactly30 days it returns `stale` and requires a
separately selected conditional review; no download/AI path exists. It neither
creates an actual payload cache nor asserts asset-byte verification. There is
no force/revalidate option capable of bypassing the minimum window. Source holds
and actual retention restrictions continue to override any later cache adapter.

## Field origins and source roles

All16 retained CSV columns have explicit source-column selectors, in addition
to projected price/date/market fields, source row ordinal and original receipt
time. Native denomination strings remain `KG`, `L`, `Packet`, `Unit`, `400 G`,
`Sack`, `Package`, `1.5 L` and `XAF`. Canonical currency, metric basis, preparation,
food eligibility and analytical assay remain unknown. Publisher `Registry`
describes collection, not preparation or measurement. Market fields in the old
candidate's `retailer` slot are publisher market context, not verified merchants.
All147 source non-food observations remain excluded from any food-total use.

The existing CF record stream is bare-record JSONL; shared acceptance expects
singleton-array JSONL. This package does not read/reframe those65,197,188bytes.
It emits a separate `source-input-binding` metadata record with its own schema
and cannot be substituted for the31,384 actual price observations.

## Reused shared contracts and integration request

No shared core, generic adapter, registry or ADMISSIONS entry changes. This module
uses shared strict JSON/timestamps, MIN_TTL, qualification fingerprint,
StageResult, field-origin coverage and serialization. Every emitted metadata
datum, including nulls, is traced to a JSON pointer in the exact shipped config;
the shared `field_origin_errors` validates this inventory. That scope is
`binding-config-metadata-only`: the underlying CSV selectors are declarations,
not newly verified source-cell fidelity. Tests exercise actual `SourceContract` /
`acceptance.accept` on one explicitly authored metadata fixture, including a
hold and a corrupted candidate. `fixture=True` prevents production/country
acceptance. That fixture uses its own authored source/release identity, not a
production source or fixture-registry masquerade. No fixture rights file grants
rights to real CF payloads.

Integrator00 result5798 confirms that no generic pure cache planner exists at
this baseline. The age comparisons here are portfolio-specific metadata intent
only; no source-specific Wikibooks/registry policy is invoked, and operational
`CachedAcquirer` is not run. A shared source-neutral pure planner extension is
proposal-only for Morgan/00; its absence does not block these metadata bindings.

Existing00 should review this exact additive module/config/tests and the metadata
kind/schema interface. Before a real data operation, the existing owners must
supply a reviewed private native scope/rights/expected count-ID/schema-semantic
SourceContract and source-field-origin acceptance. A separately selected generic
retained-candidate framing projection may be needed; do not use Open Prices'
unrelated input dialect, add a duplicate country engine, or install admission
from this config. No change to the shared interface is implemented here.

Missing internal custody alone is not a legal prohibition. The exact blockers
are recorded source/use/operation and contract gaps: BY zero-byte DNS acquisition;
CC missing cookbook edition/recipe membership/reuse; CD absent CSV with retained
unfollowed302/no-reroute hold; CF current instruction forbids new body processing
and production contract/framing/semantic acceptance is not installed. Dataset
licence declarations and scoped source-role reviews are kept separate from
redistribution and admission. No publisher research was needed to identify these
already-retained exact format/method/licence declarations.

## Focused verification and limits

Run `python -m unittest discover -s tests -p test_portfolio22_binding.py -v`.
Authored tests cover valid/missing/held/malformed/stale metadata, exact30-day
boundary, validation-age separation, deterministic replay/no-op, strict duplicate
keys, source/selector/pin drift, unavailable admissions and shared fixture-only
qualification. This is no claim of production-scale isolation or a reviewed
real-data payload. Existing runner resource boundaries still apply to later
selected execution. All Finland/Frida/native NO-FR, source/privacy/custody/denial,
integration/UI/DEV7645/production/CIX holds remain.
