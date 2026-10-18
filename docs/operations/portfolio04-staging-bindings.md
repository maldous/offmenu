# Worker04 source-input bindings

Selected scope: `M-STAGING-BIND-20261018-W04`, AE/CH/GL/KZ. Baseline develop
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`, independently matched by remote
`refs/heads/develop` at pickup. The old f6cb92ae checkout and its untracked files
are preserved. This package owns portfolio configuration/bindings/tests only.
No shared core, registry, admissions, existing source artifacts or runtime change.

## Executable use and output

From the source checkout:

```sh
python3 -m offmenu.refresh.portfolio04_binding --now 2026-10-18T00:00:00Z
python3 -m unittest tests.test_portfolio04_binding tests.test_reference_acceptance tests.test_refresh_field_provenance -v
```

The CLI uses the inert owned `portfolio04_catalogue.py` literal through a deep-copy
loader. `config/portfolio04-staging-bindings.json` remains its byte-unchanged JSON
mirror; it is not required in an installed wheel. No shared packaging rules are
changed. Catalogue transport grants no source access or acceptance.
The CLI accepts no caller-supplied URLs, permissions or executable plugins. It opens only the 17
explicitly pinned JSON metadata sidecars, bounded to 2 MiB each / 16 MiB total.
Symlink paths refuse; absent/unreadable metadata fails closed. **Original body
paths are scalar provenance, never opened, statted or rehashed.** It does not
open the retained reference JSONL or original archives. Raw data stays on Foo.

Exit0 means every binding is metadata-ready; exit2 reports held/missing/stale or
malformed entries, and exit3 rejects an invalid profile/invocation. Each result
has its own status, fixed errors, missing fields, holds and cache diagnostics.
A bad entry does not prevent the other entries being inspected. This is bounded
in-process metadata diagnostic isolation; OS process/memory isolation belongs to
the existing integrator execution boundary. No automatic network/refresh occurs.

The real profile describes 11 archived source assets plus the explicit missing
AE composition input. It separately enumerates all six required categories per
country, with their original gap selectors. No unsupported category disappears
because an archive exists. All 12 current real bindings retain holds; none is an
accepted dataset or a source-processing admission.

`candidateRecords` are **source-input metadata descriptors**, not parsed source
rows. Their `metadataReleaseId` denotes the receipt/inventory snapshot;
`data.datasetRelease` retains the recorded original release string or null. A
null is an explicit unknown, never a guessed native unit/basis. Every emitted
scalar has a shared `field_provenance` origin: an exact pinned sidecar JSON pointer
or a policy-bound explicit-unknown constant. `metadata_semantic_errors` verifies
pointer/value equality without reading the referenced body. Retained asset
hash/size/path and publisher URLs are copied as evidence assertions, not current
byte-integrity or source-format certification.

## Existing shared interfaces

This uses shared `acceptance.canonical/fingerprint`, `acquisition.MIN_TTL`,
`core.strict_json/timestamp`, `field_provenance.field_origin_errors`, and
`reference_adapters.candidate_bytes`. It does not clone a nutrient, CSV, XLSX or
PDF engine. The shared `adapter_mapping` currently supplies no reviewed retained
parser/release route for these 11 exact inputs; profile `adapterBinding` therefore
stays unsupported rather than assigning an unrelated family by country/domain.

The authored fixture demonstrates the existing `SourceContract`, `qualify` and
`accept` path with `fixture=True`, exact metadata bundle pins, a metadata schema,
and both shared field-origin and source-coordinate semantic callbacks. It proves
only integration compatibility. Runtime configuration never constructs a real
SourceContract from a manifest or permission string. No real source acceptance,
country completeness or gold promotion follows.

## Acquisition age, validation and replay

`originalAcquiredAt` comes from each original receipt's exact request `/utc`;
file modification time, receipt start time, validation time and today's time do
not substitute. Missing AE composition acquisition time remains null.
`metadataVerifiedAt` separately records explicit `--now` after metadata hashes
and declarations pass. No validation refreshes original acquisition age.

Age below the shared 30-day minimum reports `under-minimum-reuse`. At exactly
30 days the otherwise ready authored case becomes `stale` with
`refresh-selection-required`. Future/invalid timestamps fail closed. The module
always reports `networkAllowed=false`, including stale cases; only a later
reviewed source/execution contract could select eligible conditional refresh.
Source-specific private/no-store/denial/retention constraints take precedence;
this metadata package does not claim to implement HTTP cache retention.

Pass `--previous-candidate-sha256 DIGEST` to detect an unchanged candidate payload.
The digest excludes evaluation time. `replay=no-op` means **candidate bytes only**;
fresh status, holds, age and diagnostics must still be consumed. Hash mismatch,
missing evidence or malformed entries cannot produce a trusted no-op. The CLI
writes stdout only; it never overwrites a candidate or moves an accepted pointer.

## Evidence and public documentation

Exact local pins and selectors are in the profile; original result3855 records
11 archive checks and two retained AE/CH reference packets. Review4519 concerns
Author09, not these source bodies; review20/483 concerns AE locator/gap metadata.
Returned author37 response5205 explicitly holds no new composition release,
extent, dictionary or dataset-use grant. Those results are reused, not repeated.

On18 October2026, the official [Kazakhstan BNS use policy](https://stat.gov.kz/en/description/)
provided general evidence permitting reuse/modification of official statistics
with source attribution. This is relevant policy evidence for the four BNS
workbook leads, **not** the QazaqGourmet menu. It does not establish table/cell
selectors, units, scope completeness, native custody or independent acceptance
for a specific operation. Existing recorded restrictions and holds remain.

The official [SNB API documentation lead](https://data.snb.ch/en/help_api) did not
establish plkopr-specific units or reuse: the direct read returned a
JavaScript-required page. No endpoints were fetched and no rights were borrowed
from another SNB dataset. Current observations and their limits are recorded in
`config/portfolio04-official-document-observations.json`; this authored note is
not a retained publisher-body hash or licence grant.

## Typed remaining blockers and integrator00 request

- **Evidence/input:** AE has no qualified composition release/dictionary. CH CPI,
  GL CPI/recipes and KZ releases lack accepted exact field-origin/unit/basis
  selectors. A menu does not establish recipes or ingredients; indices are not
  item prices. All24 country/category gaps stay explicit in the profile.
- **Scope/use:** acquisition clauses are not extraction decisions. Swiss46
  nutrition rights, GL recipe derivative scope and all source-specific holds
  remain. The new BNS policy evidence needs exact release/action applicability
  review; an internal custodian gap alone is not a legal prohibition.
- **Integration/acceptance:** integrator00 should review the metadata descriptor
  output/schema and trusted SourceContract/callback handoff before a later
  source-format-specific stage. No shared-core change is required to run this
  standalone package. Proposed interface: a private metadata `Binding` factory
  may call `evaluate(profile, pinned_metadata_bytes, now=..., previous_digest)`
  and inspect `results`; do not register it as a source acquisition/parser or
  accept-stage handler. If shared registration is desired,00 owns that change.
- **Execution:** real parser/candidate execution requires reviewed custody/use,
  scope/count/schema/semantics and existing process-resource isolation. This
  module supplies diagnostics and cache planning only, not those approvals.

Independent exact-commit approval and develop integration are required before
the next request. Pending PR42 is not accepted develop. Finland/Frida, native
NO/FR crash and403/private/credential/denied-action holds remain. No old uncertain
send, publisher contact, raw processing, production/CIX/DEV7645 or automation
change is part of this package.
