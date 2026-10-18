# Worker06 source-input bindings

Selected task M-STAGING-BIND-20261018-W06. Base develop snapshot
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. Own additions only; shared
execution, acquisition, adapters, qualification and registry remain unchanged.

## Run and inspect

From the repository, run:

```sh
python3 -m offmenu.refresh.worker06_bindings --now 2026-10-18T00:00:00Z > /private/foo/metadata-report.json
python3 -m offmenu.refresh.worker06_bindings --now 2026-10-18T00:00:00Z --previous /private/foo/metadata-report.json
python3 -m unittest tests.test_worker06_bindings -v
python3 -m unittest tests.test_worker06_packaging -v
```

Use an existing private Foo output directory. The module prints JSON and never
writes to source/cache/accepted pointers. Its only retained-input reads are the
four exact small `deliverable-validation.json` metadata manifests selected by
the committed configuration. Repeated reads are per binding, at most128KiB each;
no PDF/HTML or receipt pointer in those manifests is opened. Missing metadata is
reported per binding; symlinks, read failures, malformed/duplicate JSON,
selectors and hash drift fail closed. No replacement search or fetch occurs.
The reader opens each directory component without following links, then opens
the final component nonblocking and checks its descriptor with `fstat` before
reading. FIFOs/nonregular files are rejected without waiting for a writer;
before/after file identity/size/change metadata and exact input pins remain
checked. Authored FIFO tests prove the following sibling still reports.
The optional `--previous` report uses that same bounded regular-file reader;
nonregular/missing/unreadable or malformed reports produce fixed
`previous-report-unreadable-or-invalid` argument errors (exit2) before source
iteration. Regular prior reports preserve content replay. Neither prior nor
metadata input bytes/mtime are written. The report limit is128KiB.

Exit0 means every metadata input is valid or explicitly held; it never means a
payload is accepted. Missing/malformed/stale metadata causes exit1 while all
independent bindings still report. The explicit UTC clock makes runs repeatable.

## Bound source scope

The owned `offmenu.refresh.worker06_catalog` declaration has13 source entries:
ME8, MF2, MG1, MH2. `load_config()` imports the packaged Python literal and returns
a defensive deep copy; it does not look outside the installed package for a
repository JSON resource. The entire declaration is value-identical to the
reviewed predecessor JSON, including all source pins and holds. These are
metadata bindings, not13 datasets, normalized observations or accepted records.
Each entry pins the exact validation manifest and JSON selector, original source
receipt path/hash, release label, country and role. Retained payload pins are
copied only where the existing validation manifest actually supplies them;
empty arrays do not mean the original is absent. No source body was rehashed.

| Country | Selected context | Explicit exclusions/gaps |
| --- | --- | --- |
| ME | MONSTAT2021 HBS,2025 catalogue and six NTO brochure edition leads |2021 is not2025; catalogue is not release data; brochure integrity is not complete recipe scope |
| MF | IEDOM2024 edition2025 and tourism2025 guide landing metadata | French Saint-Martin, not SX; not BQP/item-price rows or PNNS applicability; guide original still missing |
| MG | World Bank P177968 poverty assessment2024 | Research context, not national composition; exact tables/units/bases/use unresolved |
| MH | World Bank paper10018(2022) and SPC regional cooking guide | Research not HIES replacement; SPC MH chapter span/list unknown; WB explicit rights correction retained |

`sourceId` is explicitly a **metadata** identity scoped to this binding. The
publisher receipt and release are retained separately. It is not an invented
registration in shared RELEASES/ADMISSIONS and does not route a publisher PDF to
an incompatible national-tabular or reference parser.

Every datum in the metadata candidate has a shared `field_origin_errors` origin:
release/URL/role point into exact pinned validation JSON; unknown native units,
bases, body selectors, body record identity and typed schema are null with a
versioned policy-constant origin. These are declarations of missing evidence,
not guessed PDF coordinates or canonical conversions. The corresponding source
receipt is an independent custody pointer; the metadata pointer is not presented
as a coordinate inside the original PDF/HTML.

## Cache and replay interface

`originalAcquiredAt` is null on all real entries: no evidence-bound acquisition
clock has been selected. `integrityValidatedAt` is the prior validation manifest's
checkedUTC. Validation/read/mtime does not substitute for acquisition and never
resets source age. Shared `acquisition.MIN_TTL` expresses the30day requirement
only. There is no generic pure cache planner at this base: `cacheDecision` is
`unsupported-real-source-cache-planner` and `freshness` remains `unknown` at
every age, including exactly30days. No local reuse, conditional-refresh or
stale-by-age policy is implemented. Known acquisition/validation ages are
separate timestamp observations; unknown acquisition age remains null. Zero
network and no asset verification apply in every case. The Wikibooks planner,
registry-only fixture planner and operational CachedAcquirer are never called.

The metadata content fingerprint binds the entire source configuration,
candidate and versioned unknown policy, excluding the caller's current clock.
An unchanged fingerprint yields `unchanged-no-op` even while source holds remain.
This is a **metadata replay** result, not proof of underlying source-content
verification, an HTTP304, or acceptance. A changed source pin is `stale` and
cannot be repaired by refreshing the validation timestamp.

These corrections supersede predecessor `0ee0311a`'s FIFO reader and local
30day decision/status logic, and the related cache-intent qualification in the
external interface5798 addendum. Prior artifacts remain retained history.

## Qualification handoff and remaining dependencies

Shared functions reused: strict JSON and UTC timestamps in `core`,
`acceptance.fingerprint`, `field_provenance.field_origin_errors`, and the shared
minimum TTL. Authored tests also compose an explicitly fixture-only trusted
`SourceContract` with shared `acceptance.accept`; the positive result is
`accepted-fixture-scope`, never production/country acceptance. Held/rights-missing
fixture contracts fail through the same qualifier. No country engine is copied.

Real bindings remain `held`, with typed owners and blockers. Payload operation
lists are empty and no actual SourceContract is created. Before a real source
successor, Morgan and its existing rights/scope reviewer must bind exact
operation-use evidence, allowed source portion, format-specific parser/adapter,
native units/bases/definitions, independently expected counts/IDs/schema, body
field origins and original-acquisition clock. Source-specific exceptions and
retained explicit denials remain in that future trusted contract. No new grant
is required merely because a custodian is missing; positive existing evidence
may qualify a narrowly reviewed operation. Missing evidence is not a denial.

Integrator00 can integrate these owned portfolio files after designated
independent review. No shared-interface mutation is proposed in this batch.
The live PR43 catalogue finding4305926950 is addressed for Worker06 by this
owned declaration. An authored offline test builds an sdist from the package
source, rebuilds its wheel, and checks installed catalogue loading/defensive
copy with resource and retained metadata reads forbidden. Shared packaging
rules are unchanged. Author evidence does not close the PR thread or replace
independent delta review/current-head CI.
If a future body format requires another generic handler, its exact interface
and reviewed semantic/custody contract must be selected with00; this module
does not silently install one. All source-domain acceptance and country
completeness remain with the shared trusted qualifier and country requirements.

## Official documentation evidence checked18October2026

These are documentation reads, not source-data downloads or source-specific
rights decisions. No publisher contact, account or terms acceptance was made.

* [IEDOM legal notice](https://www.iedom.fr/mentions-legales?lang=fr), updated
  3February2025, sections “Sont autorisées” and “Sont interdites sans autorisation
  préalable”: allows narrowly described citation/analysis and personal use,
  while other electronic reproduction/use needs prior agreement. This does not
  qualify bulk structured extraction of the retained MF report. Keep its
  operation-use blocker and attribution/portion question with the existing
  rights reviewer; do not convert a landing page into a licence.
* [World Bank terms](https://www.worldbank.org/ext/en/legal/terms-conditions),
  notice amended25July2025: distinguishes datasets and Open Knowledge Repository
  material from other site material, with source-specific terms and third-party
  ownership caveats. General site terms alone do not resolve the exact MG report
  or MH10018 correction. The linked OKR terms endpoint returned403 during this
  documentation read. No retry/alternate copy was attempted.
* SPC copyright-guide address returned only a one-line HTML response, not
  usable publication terms. The official publishing-style manual URL returned
  **403 Forbidden**. That fetch denial is retained; no alternate transport,
  challenge bypass or re-request was attempted. Search snippets or another SPC
  work's rights text are not assigned to the MH cooking guide.
* Bounded MONSTAT official-document search found contextual statistics pages,
  not a release-specific reuse/method grant for the selected HBS. No claim of
  universal absence or publisher denial follows. NTO/tourism source-specific
  extraction terms and all exact body-method selectors remain unqualified.

Finland/Frida, NO/FR native-crash, private/credential/actual-denial restrictions,
UI STOP/DEV7645, production and CIX holds remain. Raw datasets stay on Foo.
Code/metadata delivery is not permission to fetch, process or publish them.
