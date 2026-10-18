# Worker 62 metadata bindings: GR, OM, TT, ZA

This package binds **recorded acquisition metadata** to shared staging interfaces.
It does not parse a PDF, acquire data, construct a `SourceContract`, qualify a
dataset, or install a production `Binding`. Its ten metadata references are not
ten food records. All 24 country/type requirements remain unqualified.

## Run and replay

From the reviewed repository baseline, with explicit UTC clock:

```sh
python3 -m offmenu.portfolio_worker62 --now 2026-10-18T05:00:00Z --output /private/foo/worker62-metadata
```

The CLI has no source URL, dynamic plugin, force-download, source-body, or
configuration override flag. The owned inert Python catalogue
`offmenu.portfolio_worker62_catalogue` supplies an independent deep copy of the
read allowlist: 19 exact JSON receipt/claim pins. `worker62-inputs.json` remains
an exactly equivalent documentation mirror, never a default runtime resource.
The installed wheel/sdist needs no repository `docs/` tree. Original PDF paths in
`originalReference` are documentary and are never opened, statted or rehashed.
Inputs stay on Foo; generated outputs belong outside Git. A caller can use the
pure `bind(config, metadata_bytes, now=..., previous_key=..., validated_at=...)`
interface with small authored metadata instead of filesystem access.

`metadata-candidate.jsonl` uses shared canonical singleton-record serialization.
Every emitted scalar, including null, has an origin checked by the shared
`field_origin_errors`: exact metadata digest, record alias and JSON pointer, or
an explicit unknown constant bound to the configuration digest. Nested literal
values keep their coordinates. Source-native units and bases stay literal when
present; none are inferred in the retained portfolio. Unknowns have reasons in
the report and null values in the metadata record. An unknown is not evidence
that a publisher states “not specified.”

Input bytes must match both their declared length and SHA-256 before decoding.
Duplicate keys, nonfinite JSON, invalid JSON, missing files/coordinates, pin drift
and invalid acquisition times produce per-source diagnostics. A source with any
input error emits no partial metadata record; independent sources still report.
Allowlisted files are opened nonblocking with no-follow, checked as regular files
against their pre-open identity before bounded reading, and checked again after
reading. Unavailable or invalid files remain isolated metadata errors. JSON
canonicalizability is checked per input, including overflowing numeric exponents.
`valid` means a complete metadata binding, and `held` preserves a binding with
explicit body/scope holds. Neither means body permission. Diagnostic states are
`valid`, `missing`, `held`, `malformed`, `stale-input`; `metadataStage` is a shared
`StageResult` receipt for callers that consume that envelope.

The content key depends on configuration and verified input content/outcomes,
not evaluation time or validation age. Same content replays as `no-op`. The CLI
does not rewrite an identical candidate file. A changed diagnostic can change
the content key even when no candidate was emitted; no-op is an artifact action,
not success or acceptance. Source holds remain present on replay.

## Cache semantics

There is **no source-neutral pure cache planner** at the selected develop base.
The package does not call the Wikibooks-specific `core.cache_policy`, registry
fixture planner or operational `CachedAcquirer`. It reports the typed capability
gap `unsupported-source-neutral-cache-planner` and time facts only; these are not
a substitute shared refresh engine. Acquisition UTC comes from an exact receipt
selector: GR request UTC, OM capture UTC. These are historical receipt timestamps,
not freshly verified download-completion timestamps. TT/ZA have no eligible
original, so acquisition time is explicitly unknown. Receipt `checked`/capture
time for a failed challenge is never substituted as a dataset acquisition time.

`--validated-at` reports prior validation age separately and never resets original
acquisition age or the content key. `underMinimumReuseWindow` annotates the
30-day boundary without selecting an acquisition/revalidation action. The
30-day minimum is a contract requirement, not proof of a supported source cache.
All results have zero network requests and
`conditionalRefreshEligible=false`: the metadata reader cannot release source
rights, actor, retention or exact-manifest holds. Publisher restrictions still
prevail. No cache completeness or actual original-byte verification is claimed.

## Actual source scope

- **GR:** one Greek dairy establishment list approved for Saudi export. Source
  role is a jurisdiction-specific reference, not all retailers/farms, ownership,
  ingredient origin or composition. Exact receipt and native claim are pinned.
- **OM:** four dated merchant menu snapshots and three contextual MOH
  publications. Menus are not complete recipes or current national prices; MOH
  context is not a composition table or numeric dietary target. The proposed
  two-page/ten-statement/5,000-character quotation cap remains **unselected**.
- **TT:** CAD March 2025 metadata and exact native claim, with no retained
  workbook. Preserve HTTP307/no-retry and the initial claim-exclusivity exception.
- **ZA:** SAFOODS sixth-edition 2024 discovery metadata. No composition export or
  written download/use permission is held. Historical discovery and website
  viewing terms are not permission to copy a dataset.

Claims establish acquisition-native provenance, not current actor appointment.
Country/type applicability is reference-only, never completeness. The original
asset digests are reported historical pins; the exact allowlisted metadata bytes
are the only assets this package verifies. No earlier source validation/review
is replayed. Raw originals and previous artifacts are unchanged.

## Integration proposal for existing integrator 00

Owned files are this document, `worker62-inputs.json`,
`offmenu/portfolio_worker62.py`, the authored fixture and its test module. No
shared refresh core is edited. Integrate this as an offline metadata diagnostic
binding only. Do not register it as an acquire/parse/normalize/accept handler or
turn metadata holds into production permissions.

The proposed shared-interface improvement is a pure **source-neutral cache-age
planner** returning acquisition age, validation age and reuse/revalidation
decision with explicit clock/TTL, without the pilot's fixed source/release
identity. Keep acquisition policy/transport and trust decisions outside it.
Worker 62 currently reports the missing capability explicitly; 00 owns any shared
implementation and its independent review. No requested shared change is silently
installed by this package.

To admit a later actual staging candidate, Morgan must select the exact reviewed
parser/record schema and current native custodian, finite source selectors,
operation-specific rights/retention/attribution evidence, field-origin semantics,
release/units/bases and scope contracts. Independent expected counts/ID digests
and `SourceContract` acceptance remain required. Cache/replay and synthetic code
tests cannot fill those gaps. Golden promotion is later.

Output publication preflights **both** target names before reading or changing
either artifact. Existing targets must be regular files with one link; symlinks,
hardlinks, directories and FIFOs are rejected. Candidate comparison reads at most
the expected candidate length plus one byte through a checked descriptor. New
bytes are written to owned temporary files in the selected directory, target
identities are rechecked, and publication replaces directory entries rather than
truncating existing inodes. This prevents an output alias from redirecting writes
into an external file. It is not a two-artifact crash-atomic transaction.

## Authored checks

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_portfolio_worker62.py -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_refresh_field_provenance.py -v
```

Sixteen binding tests cover valid values/origins, explicit null/unknown, holds, missing input and
selector isolation, malformed/duplicate/nonfinite JSON, stale metadata pins,
timestamp failures, original-age versus validation-age, 30-day boundary,
deterministic replay and unchanged candidate mtime. They open no raw dataset and
make no network request. An explicit authored-only SourceContract also qualifies the
metadata record through shared qualify(), and demonstrates that a contract hold
prevents qualification. No real SourceContract is constructed. Their success is
code evidence, not country acceptance. The SAME50 correction regressions also
cover nonblocking FIFO rejection with a valid peer, a nonregular input swap,
both output names with hardlink/FIFO/symlink/directory targets, external alias
insertion immediately before replacement, and `1e999` isolation with a valid peer.

Three portable-catalogue tests cover exact literal/mirror equivalence, independent
nested copies, and the default CLI with resource reads and actual metadata
readers forbidden. `tests/worker62_installed_catalogue_probe.py` runs under
`python -I` from outside the repository against an offline installed target. It
checks the catalogue content digest and default loader, without a catalogue
override or `docs/` resource. The actual metadata boundary is explicitly stubbed
to empty inputs, while lower-level readers raise if called. Successful probes
therefore show installed catalogue availability and missing-input diagnostics,
not real source processing. Building/installing this project uses unchanged
packaging configuration, offline/no-deps/no-build-isolation; no dependency is
installed. The original three IO closures and the absence of a two-artifact
crash-atomicity guarantee remain unchanged.
