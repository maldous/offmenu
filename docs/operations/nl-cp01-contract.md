# NL CP01 metadata contract and authored fixture harness

This owned binding extends reviewed source-native selection5751, independent
review5903 and integrator intake6010. It does not read, stat, hash or re-extract
the real Eurostat JSON, selected observations or a cached source body. Real source
execution remains held; no data, country, canonical or golden admission follows.

The packaged `nl_cp01_metadata.py` contains only axes, labels and control-file pins
from the exact reviewed manifest0ae79fbc and terms5002. Source body SHA is
ca4356f747e32363ea77271df1979a80cc55c124a2cf739fa6b5a1084c65bf68;
original acquisition is2026-10-14T22:16:49.278357+00:00. Five units/bases stay
distinct. Expected IDs are independently enumerated from pinned axis positions
using dimension strides: CP01/NL/M ×five units ×369months =1845unique IDs and
flat coordinates. Prior1804numeric/41absent/0null/0status counts are retained
review evidence, not recomputed observations. No retail-price/basket equivalence,
unit conversion, missing-to-zero coercion or canonical food identity is assigned.

## Offline CLI

From the accepted-code checkout with the owned change:

```sh
python3 -m offmenu.refresh.nl_cp01 --now 2026-10-18T07:00:00+00:00 \
  --output /absolute/owned-report/nl-contract.json
python3 -m offmenu.refresh.nl_cp01 --now 2026-10-18T08:00:00+00:00 \
  --previous /absolute/owned-report/nl-contract.json \
  --output /absolute/owned-report/nl-contract.json
python3 -m unittest tests.test_nl_cp01 -v
```

Only four exact allowlisted metadata files are opened. The CLI emits a stable
contract snapshot and reports validation/cache observations separately on stdout.
Changed validation time does not change the snapshot, content key or original
acquisition clock. The second command reports zero writes. Source/selector/
units/basis/expected-ID/policy/owned-and-used-shared-code changes invalidate the
content key; conflicting input pins fail closed. Previous reports use the same
bounded regular-file reader as metadata; no user-selected adapter, URL, force or
source-body path is accepted. Output cannot overlap reviewed metadata or source
data. Missing canonical /2 owner/key/generation/declaration remains unavailable
and ineligible, rather than being invented by this code.

`source_contract()` creates a descriptive shared `SourceContract` with exact input
assets, independent expected-ID digest, source-specific callback and schemas.
Its mandatory hold is`real-source-body-execution-not-selected`. The callback
checks coordinates/unit labels, lexical/numeric and absent/null/presence states,
status, sparse value/status locators, field-origin coverage/pins and source
provenance. Actual value-to-original equality still belongs to a separately
selected exact source adapter; this metadata-only binding cannot prove it.

## Shared interfaces and selected qualified planner dependency

The implementation uses integrated `SourceContract`, `ids_digest`, fingerprints,
UTC timestamps, canonical serialization, field-origin validation, `MIN_TTL` and
the accepted bounded regular-descriptor reader. No shared file is changed.

The selected correction composes exact dependency
`d5147b2713abfe0c87332ab3ee692b33a80a05b1` (SAME06 scoped PASS6979).
`offmenu/refresh/retained_policy.py` remains byte-identical SHA256
`ba47921d80d3cc43afe109d10f24db6d196f97231d50ad423505ed32f62e8f9e`.
The NL caller imports `plan_retained_input` from that shared module; it does not
copy its engine or edit any shared file. Exact real source/release, declared input
pins, owned policy/code identity, independent expected-ID scope, original clock,
validation clock, prior key, minimum TTL and holds are passed explicitly.

The former pure-interface gap is resolved for this selected local caller delta.
Every returned plan still requires input verification and forbids network/data
admission. A declaration is not body-cache integrity or operational refresh.
The original source/fixture planners are not spoofed with NL identity;
`CachedAcquirer` remains unused for real query-bearing Eurostat input.
00 owns final dependency/current-develop composition and integration after
SAME45 reviews this owned successor. Local composition also contains the existing
f3258 accepted ancestor; these dependency bytes are not authored NL changes.

The real binding reports the shared pure metadata-only minimum30day policy using
the original acquisition time and no network at any age. At exactly30days it
reports`revalidation-required`; validation never resets acquisition age.
The shared key and replay decision stay distinct from elapsed cache age.
Explicit holds dominate replay, even with a matching key and unavailable payload.
This is not proof of body-cache integrity or refresh.
Tests separately exercise the actual integrated `CachedAcquirer` with explicitly
authored fixture bytes, a fixture.invalid source and injected in-memory transport:
under30days reuses with zero extra requests, exactly30days can conditionally
revalidate,304 preserves original acquisition/source hash. No real source identity
or grant is substituted. Shared qualification also runs only on authored fixture
assets/rows/evidence, never real source or selected observations.

Focused tests cover expected IDs, native unit/basis checks, source pointers and
origin coverage, explicit null versus absent, numeric lexical text, cache-boundary
clocks, policy/inventory/code invalidation, exact no-op/replay, malformed and held
peer isolation, bounded FIFO/symlink/oversize ingress and a healthy peer surviving
failures. Preserve existing data/review outputs and source/privacy/denial/NO-FR/
Finland/Frida/production/CIX/DEV7645 holds. Reviewer45 owns changed-code review;
integration00 alone integrates after independent acceptance and normal gates.

## SAME45 W45-NL57-F1 correction

Publication opens and retains every output ancestor directory with no-follow
descriptors, then rechecks the named inode links before staging, before replace
and before returning. Existing output reads, exclusive temporary creation,
cleanup and replacement all use the pinned final directory descriptor. A renamed
parent cannot redirect these operations through a replacement symlink. Drift
fails with`output-parent-changed`; even a swap at the replace syscall can only
publish into the original pinned report directory, never the protected target.
Final file/parent path strings are not re-resolved for publication. Ordinary write,
exact no-op and unchanged mtime behaviour remain. Focused authored tests cover
both race points and the changed shared-planner caller only; SAME45's prior ten
positive scopes and the old NL data review are retained without broad replay.
