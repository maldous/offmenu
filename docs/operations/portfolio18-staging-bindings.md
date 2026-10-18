# Worker18 retained portfolio bindings

Base: `abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. Selected task:
`M-STAGING-BIND-20261018-W18`. Owner: existing local Worker18,
`01a138f7-e2a4-72a1-ad65-580963d1d2b9`; countries BO/BQ/BR/BS.

`offmenu.refresh.portfolio18_catalogue` is reviewable application configuration.
It pins retained manifests/receipts and derived inputs, source releases, exact
applicability, scoped counts, source-native selector declarations, units,
unknowns and dependency owners. Absolute paths are custody pointers only. The
diagnostic never opens them. Source hashes are historical declarations; only the
metadata receipts/manifests were checked during implementation. No raw data is
included in this commit.

| Binding | Current retained extent | Remaining gate |
| --- | --- | --- |
| BO | Zenodo release metadata; zero food records | Actual custodian, dictionary, record unit and privacy-safe scope |
| BQ | CBS2021 coordinate contract: 12 definitions,36 locators | Methodology, population/units/missingness, Fruit erratum, document exceptions |
| BR | TACO4: 8 IDs,26 columns,208 private literal cells | Repeatable exact-extent projection, reviewed staging/writer binding |
| BS | BNSI: 78 private CPI literals,13 categories,6 periods | Base/weight/use semantics; CPI is not item price |

Every country/domain cell remains incomplete. BS cookbook and FAO profile and
other BR sources remain separately held in the catalogue. The BR overlap is
already reconciled: old31x11 and new8x26 share88 cells; union31 food IDs/461
coordinates. Do not re-acquire, re-parse or add the extents as disjoint records.

## Invocation and output

Prepare a bounded envelope using
`request_for(binding_id, validated_at_utc)`, serialize with shared `canonical`,
and pipe it to:

```sh
python3 -B -m offmenu.refresh.portfolio18 --binding BR-taco4-literals --now 2026-10-18T00:00:00Z
```

The CLI reads at most65537 bytes from stdin, accepts no source-file path, URL,
command, dynamic plugin or output-directory option, and writes one deterministic
JSON diagnostic. Exit0 means metadata ready/unchanged; exit2 means
missing/held/malformed/stale. `inspect` provides the same in-process interface.
An unknown binding is rejected; callers cannot install policy, remove holds or
change pins through the envelope. `request_for` prepares assertions, without
checking asset bytes. All four current real bindings return held.

`StageResult` is the existing shared receipt shape. This package does not register
a GlobalRun handler or admission, manufacture a SourceContract from metadata,
or execute a source parser/writer. `origin_diagnostics` reuses the shared
per-datum coverage checker with the exact retained-input pins. It explicitly
leaves selector/value semantics unsupported until a reviewed projection checks
the underlying coordinate. The input JSON selector and upstream original
coordinate must both survive a future projection. Hash equality does not prove
field meaning or source permission.

## Acquisition age, cache and replay

Original acquisition time and metadata validation time are separate. Only the
BO metadata acquisition time is matched to its pinned receipt request. BQ/BR
acquisition times are unknown; BS candidate snapshot time is retained separately
and is not promoted to a verified acquisition time. Survey/publication periods
are never acquisition timestamps.

The private portfolio diagnostic uses the shared minimum30day constant only to
report age and block stale input in authored tests. There is no generic pure
cache planner at this base. `core.cache_policy` is Wikibooks-specific and
`plan_fixture` is registry-only; neither is spoofed. `CachedAcquirer` can read
bodies/fetch and is never invoked here. This package does not implement a new
shared cache engine, cache storage, invalidation or operational refresh.

Under30days means metadata reuse intent only; at/after30days requires qualified
revalidation, never an automatic download. Unknown age stays unknown. Holds
remain dominant at every age. The replay digest binds the entire trusted
catalogue entry, exact pins and original acquisition time; observational
validation time is excluded. An unchanged fresh authored plan returns no-op.
No-op never proves existing bytes, rights, a completed stage or country admission.

## Validation and isolation

```sh
python3 -B -m unittest tests.test_refresh_portfolio18 -v
```

Small authored inputs demonstrate valid, missing, held, malformed, stale,
30day boundary, replay/no-op, unknown acquisition time, duplicate/nonfinite JSON,
identity/pin changes, and non-bypassable real holds. A tiny invented CSV and
singleton-JSONL candidate exercise shared `SourceContract`, `qualify`, `accept`
and `field_origin_errors`, including wrong selectors and held scope. The only
accepted receipt is explicitly fixture-only; no country dataset is accepted.

The CLI test uses a separate child process with5second timeout,3CPU seconds,
256MiB address-space ceiling and zero regular-file output budget. It receives a
bounded metadata envelope and a minimal environment. This is resource/process
isolation, not a filesystem/network sandbox. No security settings are changed;
there is no network code or source-file opening path in this adapter. Do not
claim production dispatch isolation from this test.

## Integration handoff and dependencies

The integrator00 baseline/interface result5798 (receipt SHA256
`f94fbf0a42b5d7906e20ace0416295ae569ee400ddfd770f90a427f803d3b7cb`)
confirms the missing source-neutral pure-planner interface. If Morgan selects a
shared extension, propose `policy.plan_retained_input` centrally with explicit
source/release/bundle identity, acquisition/revalidation times, holds/unknowns
and zero-I/O intent output. This commit adds no such public shared API.

Next: independent review of this exact commit/config/tests, then integrator00
decides integration and any shared interface extension. Source-specific body
projection requires a separately qualified dispatch and reviewed semantic
callback/asset inventory/rights scope. Retain correction ownership while review
is pending; do not repeat completed tests without changes or new evidence.

Morgan owns cross-worker scheduling and ledger reconciliation. Existing25
reviews,57 NL adapter,64 continuation/sync and source custodians49/50 remain
separate. All source-use/privacy/custody/actual denial, Finland/Frida, native
NO/FR crash restrictions, raw-on-Foo, production/CIX and DEV7645 holds remain.
