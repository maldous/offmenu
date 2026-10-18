# Worker26 portfolio metadata/staging bindings

Base: verified develop `abecb99ee1125730ccbc2824b6ec49ffc5cc4302`.
This package owns only `offmenu/refresh/portfolio26.py`, its configuration,
authored fixtures, tests and this document. It does not change shared core,
install a SourceContract/Admission, parse a retained payload or accept a country.
Pending PR42 code is not imported or treated as accepted develop.

## Run and consume

From this repository checkout on Foo:

```sh
python3 -m offmenu.refresh.portfolio26 --now 2026-10-18T00:00:00Z
PYRSISTENT_NO_C_EXTENSION=1 python3 -m unittest discover -s tests -p test_portfolio26_bindings.py -v
```

The repository configuration is trusted review input, never a source-supplied
manifest or user plugin. The CLI has no URL, parser, force-download, network,
raw-data, credential or admission options. It writes deterministic JSON to
stdout; it neither modifies manifests nor creates a scheduler/cache database.
The default configuration is an inert package-local Python literal returned as
a deep copy, including in wheel and sdist layouts. The retained repository JSON
is an equivalent review snapshot; it is not a required installed resource.
An explicit `configuration(path)` still reads trusted review JSON. Descriptors
use exact existing Foo metadata locators, so another host reports missing
metadata instead of copying raw data. Loading the catalogue reads no sources.

`configuration()` returns ten portfolio descriptors. `plan(config, now=...,
previous_keys=...)` emits all 24 country/type cells and one shared `StageResult`
receipt per descriptor. `inspect_binding(binding, now=..., previous_key=...)`
can be used by the existing integrator's metadata planning layer. It cannot
dispatch GLOBAL data stages: its successful stage is **metadata-bound only**.
`acceptedRecords=null`, `countryComplete=false`, `qualificationContract=null`
and `processingAdmission=not-installed` remain explicit.

Missing manifest pointers/files return `unsupported/portfolio-manifest-missing`.
Explicit holds return `held/source-held` **before any locator I/O**. Malformed
JSON, duplicate keys, invalid timestamps and mismatched source/release identities
fail closed. Changed pinned metadata, including definition/use evidence, returns
`quarantined/portfolio-metadata-stale`. Shared bounded digest/strict JSON/path
helpers reject oversize files and symlinks. Diagnostics are fixed codes, not raw
exception messages. Independent source pins and code review remain necessary.

## Exact retained evidence and scope

`config/portfolio26-bindings.json` pins the existing CNF2015 and BLS4.0 manifests,
CA StatCan packet and source-specific use/field-declaration evidence. Paths and
SHA-256 values are metadata references; no original payload is included in Git.
The inspector only reads these `.json` metadata files. It never follows a JSON
pointer into a raw body, opens normalized gzip, reads a workbook/CSV/PDF, invokes
an adapter or traverses a source directory.

CNF binds the shared `cnf`/2015 adapter, retaining NutrientID versus NutrientCode,
100g edible/as-described basis and source-ID/method distinction. Food534/ID328
remains unresolved; Code328/ID339 is not a repair. Component definitions do not
prove ingredient equivalence. Source-specific guideline conditions remain in
the referenced evidence. Montreal recipe entitlement is separately held.

BLS binds `germany-bls`/4.0. Source components, units, method/reference and trace
qualifiers remain distinct. `Hinweis` is metadata, not a nutrient quantity.
No full-population semantic acceptance or canonical target is installed.

StatCan metadata is bound to an immutable content snapshot; the configuration's
release string explicitly denotes that hash, not a guessed publisher release.
Its monthly statistical prices are not merchant offers. Dollars is a source
UOM label with unknown ISO currency. Four nonfood labels and ingredient
equivalence proposals remain separate. No generic StatCan data adapter is
currently selected by this package.

CY recipe, CZ operator/NutriDatabaze/SZU and DE recipe/menu holds remain closed.
The missing CY composition manifest is an explicit unsupported input. Metadata
availability does not permit a 403 retry, private-body read, access workaround,
current-country inference, translation, serving or redistribution. Every
unbound required country/type remains visible; none is declared inapplicable.

## Field origins and shared validators

Each `origins` declaration names a destination field pattern, source selector,
meaning and pinned retained metadata evidence. These declarations are
**not row-verified provenance** and cannot stand in for a per-datum serializer.
Hash-valid rights evidence is not a reviewed operation grant. Both limitations
are explicit in the report. The wrapper reuses shared `execution.ADAPTERS`,
`capabilities.RELEASES`, `national_semantic_errors`, `field_origin_errors`,
`StageResult`, strict JSON/hash helpers and the acquisition `MIN_TTL` constant.

`diagnose_authored_profile` and `diagnose_authored_origins` are small-fixture
interfaces using those existing validators. Fixture unit allowlists are not a
production semantic policy. Tests preserve a null source datum with its origin,
reject missing/foreign origins and retain unresolved units/definitions. No
production SourceContract is constructed from the configuration or manifests.

An authored test constructs `SourceContract(fixture=True)` and calls shared
`qualify` with a tiny authored JSON input, rights/scope placeholders and exact
candidate origins. It proves fixture-only qualification plus held/stale failures;
it neither calls `accept` nor installs a production contract. The documented
test command uses a process-only pure-Python dependency fallback, without
installation or persistent environment changes.

## Acquisition age, cache and replay

`originalAcquiredAt` and `validationObservedAt` are independent. Production
descriptors currently leave both null: existing parser `completedAt` and
normalization `fetchedAt` must not become original-acquisition proof. Acquisition
age is never read from mtime or reset by revalidation. Authored tests observe
the under-30-day window and exact 30-day boundary. They do not claim a generic
cache plan or runtime reuse: `decision=unsupported-shared-cache-planner`,
`sharedPlanner=null`, and `runtimeReuseVerified=false` are explicit at this base.
The wrapper has no transport at any age and offers no override/force mode.

`bindingKey` fingerprints the metadata descriptor, pins and scope, excluding
acquisition/validation timestamps. It is not a payload-cache identity or an
acceptance digest. Equal keys yield `metadata-no-op` only for the packaging
decision. Current metadata/evidence hashes are still checked on every call;
age and holds are still assessed. Thus a metadata no-op can coexist with a
missing acquisition time, an old retention window or an unsupported planner;
it never authorizes reuse of unread
payload bytes or a download. A new source pin/evidence/scope changes the key.

## Precise interface requests to integrator00

No shared-core edits are included. These are proposed interfaces for the
existing integrator's decision, not approval to implement or execute them:

1. A source-neutral pure cache decision API taking reviewed source/release,
   content identity, original acquisition timestamp and separate validation
   events, with the automatic under-30-day zero-download rule independent of
   explicit revalidate/force modes. This portfolio wrapper currently reports
   that metadata decision only; it does not replace `CachedAcquirer`. Preserve
   the PR42 P2/merge hold and test the exact reviewed shared successor.
2. A reviewed source-coordinate serializer/factory that can consume the
   CNF/BLS selector declarations and emit shared `fieldOrigins` for every scalar,
   with distinct source/derived/constant markers and exact input pins. Keep
   `Hinweis` metadata and unresolved CNF328/trace facts intact. The current
   declarations cannot substitute for that implementation or source review.
3. Trusted native-scope SourceContract and acquisition/scope/custody evidence
   for unchanged retained candidate bundles. Use existing `CandidateArtifact`
   and shared acceptance entry points; never build trusted contracts from this
   JSON config. StatCan needs a separately selected generic tabular interface.

Next ready dependency is independent review of this commit and integrator00's
decision on these exact interfaces. Actual payload work, source admission,
refresh execution and develop integration require their existing gates. Raw
stays on Foo; Finland/Frida/NO/FR, production/CIX and DEV7645 boundaries persist.
