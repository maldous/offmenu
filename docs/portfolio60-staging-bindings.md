# GG / NR / TM / YE source-input bindings

This portfolio package binds **metadata** to the shared refresh contracts at
accepted develop `abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. It does not parse
source PDFs/CSVs, install acquisitions, qualify real source rows, or accept a
country or golden corpus. All four real sources remain held and disabled.
Pending PR42 is not this baseline.

Run an isolated, deterministic inspection using an explicit UTC observation time:

```sh
python3 -B -m offmenu.portfolio60 --as-of 2026-10-18T00:00:00Z \
  --output-root /absolute/private/portfolio60-output
```

`--output-root` is optional; without it JSON is written only to stdout. The
content-addressed `binding-manifest.json` stores source/release pins, role/type
applicability, field-origin declarations, explicit nulls and typed blockers.
Metadata-only staging does not establish source-data STAGING acceptance.
Unchanged inputs and code produce the same content identity. Reuse leaves the
manifest's bytes, inode and modification time unchanged. A conflicting/corrupt
artifact fails rather than being replaced. There is no download/force option.

The observation time and acquisition-age diagnostics are separate from the
content identity. Only a pinned original-download event with the same reported
hash, byte extent, successful status and completion marker supplies acquisition
time. These are historical metadata claims; original bytes are never reverified.
Metadata validation does not reset original acquisition age. Unknown original
age stays unknown. An under-30-day observation requires zero downloads; reaching
30 days is review-only, never an automatic refresh authorization.
The source-content **claim** identity hashes source/release/reported-original hash;
it is separate from metadata artifact identity and is not bitstream verification.
Changing an evidence pin requires a new reviewed config and metadata artifact,
even if that evidence reports the same original content. No raw-source refresh
or transformation is implied by such a metadata change.

## Owned inputs and interfaces

`offmenu/portfolio60/catalog.py` is trusted, portfolio-specific configuration.
It names exact JSON receipt/custody files, byte lengths, SHA-256 digests, selectors,
source/release identities and holds. No original source payload is embedded.
There is no arbitrary config/plugin/URL input. A changed metadata pin yields
`stale-input`; it is never silently repinned. Missing, held, malformed and valid
metadata have distinct outcomes. One failed binding does not prevent independent
bindings from being assessed. Metadata validity never opens a source gate.

The reader opens only the configured JSON files, at most 64 KiB per file and
1 MiB per binding. It never follows paths found inside those documents. Source
URLs are checked against their exact metadata selectors but are not requested.
Receipt ingress retains safe-path checks and opens each parent through a
no-follow directory descriptor. The leaf opens with no-follow/nonblocking flags;
its descriptor must be a regular file with exactly one hard link and a bounded
size before any bytes are read. FIFO/directory/alias failures remain isolated
under the existing fixed per-input diagnostics. Authored regressions cover a
FIFO with a healthy peer, leaf and parent symlink swaps, and a hard-link alias.
Absolute paths are existing Foo-local evidence locators; relocated custody needs
a newly reviewed configuration, not an inferred replacement. Raw stays on Foo.

Shared implementations are reused directly:

- `core.strict_json`, `verify_source`, `canonical`, `timestamp`, `safe_path`;
- `field_provenance.datum_pointers` and `field_origin_errors` for every scalar;
- disabled `acquisition.SourceSpec` descriptors and shared `MIN_TTL`;
- `runner.deny_network` in a bounded `-I -B` worker (10-second CPU, 256 MiB memory,
  2 MiB file size; parent timeout 20 seconds). This is trusted-code isolation,
  not a hostile-code security sandbox.

Diagnostics contain fixed error codes and declared field/input identifiers,
not source bodies, headers, exception text or credentials. Exit zero means the
inspection ran; consumers must read each binding's `status` and diagnostics.

## Exact portfolio scope

| Binding | Role/applicability | Remaining source-data blockers |
|---|---|---|
| GG Balthazar February 2026 receipt | Menu reference; provider/price leads | Body actor, source-use decision, effective date, complete item/portion/currency selectors |
| NR 2012/13 hardship report | Historical poverty-basket method | Complete table/quantity/unit selectors and applicable noncommercial operation decision; SPREP licence lead is preserved |
| TM MICS 2015/16 English report | Aggregate nutrition survey | Exact report-use/credit/exclusions and one complete table/population/denominator/layout contract; not food composition |
| YE WFP price-resource metadata | Market-price lead | Actual CSV not held, body actor and record/header/use qualification absent; resource modification time is not a publisher version |

Returned custody metadata is pinned beside each source receipt. Its attestation
is distinct from current body-actor admission. A menu is not a recipe corpus,
a survey is not food composition, and market prices are not a complete basket.
Domains absent from these lead bindings remain unassessed; all six required
country data types still need their own accepted source/scope evidence.

Units, bases, effective dates, currency codes, row selectors and use decisions
remain explicit unknowns wherever not supplied. A code-origin constant marks an
unknown; it is never presented as a source cell. Known scalar metadata values
retain exact input SHA and JSON-pointer origins. The shared validator checks
origin coverage/identity; it does not establish semantic or rights acceptance.

## Shared-interface proposal for Integrator00

No generic pure source cache planner exists at the selected base.
`policy.plan_fixture` is fixture-registry-specific; `core.cache_policy` carries
Wikibooks identity. `CachedAcquirer` is operational, opens bodies and may fetch;
it is never called here. Sources/fixtures are not spoofed to use those APIs.

The binding emits a read-only age observation and a typed
`unsupported-interface-at-selected-base` capability. It is not a new cache or
acquisition engine. Proposed shared interface, for Morgan/00 review only:

```python
plan_retained_metadata(source_id, release_id, input_sha256,
                       original_acquired_at, validation_events, *, now)
```

It should be pure and perform no IO/network; distinguish original acquisition
from validation; retain unknown/future/malformed states; never authorize download
within 30 days even via explicit modes; make older age review-only; and keep
validation timestamps outside source content identity. No shared-core edit is
part of this portfolio commit. Source-specific parsers, rights/actor admission,
complete field-origin manifests and independent acceptance remain separate
dependencies before any real data processing or integration.

## Focused validation

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v tests.test_portfolio60_bindings
python3 -B -m offmenu.portfolio60 --fixture valid --as-of 2026-10-18T00:00:00Z
```

The code-owned small authored fixtures exercise valid, missing, held, malformed
and stale-input outcomes through the isolated CLI, 30-day boundaries, clock/content
separation, true no-op, corrupt outputs, safe metadata IO, isolated failures and
complete known/unknown origins. A separate test uses the existing shared
`SourceContract/qualify` on authored metadata only and rejects corrupted provenance.
It does not use `accept`, real source bodies, national fixtures or production
admissions. Frozen external receipts bind actual CLI results and test evidence;
independent review and develop integration remain required.
