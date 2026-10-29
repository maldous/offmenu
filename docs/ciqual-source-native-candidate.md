# Exact retained CIQUAL 2025: private source-native candidate

## What this adds

`offmenu_ciqual.source_native` is a separate, versioned extraction path for the
actual CIQUAL workbook and identity XML. It does not relax or modify the existing
73-column synthetic adapter, its `ALIMENTS` envelope, canonical nutrient mapping,
input lock, golden artifacts, or historical-input rejection.

The new path admits the exact nine inputs already rehashed through the read-only
Foo view by `national-schema-survey-20261017-004` (GitHub run `39080278066`, trusted
source commit `314822f900c49953aeca04d82ce0957d851d19c9`). The static JSON contract
contains their sizes and SHA-256 values, the full sanitized FR structural report,
84 observed header labels and raw header hashes, INFOODS positional hashes, and
the XML/workbook identity-set digest. This is observed schema evidence, not a
copy of the source bodies. Its report still correctly says the original survey
did not enable candidate generation or establish semantic acceptance.

The candidate preserves source-native facts:

- 3,484 source food IDs, subject to exact runtime reconciliation
- all 84 first-sheet columns by position, including raw decoded text, OOXML cell
  type, cell presence and style ID
- all 74 unit-bearing source columns, with literal header suffixes retained
- the independent column 84 Jones factor, without a nutrient-unit assumption
- each XML field's exact decoded text and attributes in the real `TABLE/ALIM`
  envelope, including attributed empty scientific names
- all 225 INFOODS cells in their original row/column positions
- uninterpreted style-element trees and a workbook-feature inventory

Numeric observations use decimal strings to avoid binary64 precision loss.
Missing cells, present cells without a value, blank text, dash, trace, ND, NT,
N, bounds, explicit zero and unresolved/invalid text remain distinguishable.
The original lexical value is always retained. An observation classifier is not
a claim about a detection limit, measurement validity or concentration.

The repeated ENERC tags and numeric codes 327, 328, 332 and 333 never become one
quantity or canonical nutrient. Dictionary row order is not treated as a join to
workbook column order. The source-native record kind is `sourceNativeFood`, not
a corpus-accepted `nutrientProfile`.

## Known limits and source notice

Remaining unknowns do not need invented resolutions for lexical preservation:

- style/custom-format/extension meanings are unreviewed and not interpreted
- INFOODS component-label semantics and crosswalks are not accepted
- the original acquisition time is unavailable, so freshness stays unknown;
  the 30-day reuse rule is retained and no mtime is used as acquisition evidence
- no country coverage assessment or corpus acceptance has been performed

The retained source profile names `Etalab Licence Ouverte 2.0`, attribution
`Anses. 2025. Ciqual French food composition table.`, and source URL
<https://zenodo.org/records/17550133>. These are carried through as a source
notice, with `sourceUseDecision: not-performed`. The implementation does not
invent a new legal decision, accept terms, relicense data, or authorize public
redistribution. It produces only the requested private candidate on Foo.

## Integration points

The parent integration owns CLI, registry, dispatcher, runner and packaging
changes. This change set modifies none of those files.

1. Add `include src/offmenu_ciqual/native-contract-v1.json` to `MANIFEST.in` when
   packaging this adapter.
2. Call `offmenu_ciqual.source_native.build_selected(output)` from a trusted
   normal-user Foo runner. Input paths are fixed by the existing survey module;
   the output must be directly under `/srv/offmenu-refresh/outputs`, named
   `ciqual-source-native-` plus 1–80 ASCII letters/digits/hyphens/underscores.
   Use a distinct destination for a different code/runtime build.
3. Only the returned aggregate receipt may be uploaded. The four candidate
   files, raw food cells and native dictionary metadata must remain on Foo.
4. A wrapper already owning the shared lifecycle can instead call the pure
   `render_verified_bundle(blobs)`. It accepts exactly all nine pin-verified
   byte inputs, with no caller-supplied contract or historical override, and
   returns `normalized.jsonl.gz`, `source-metadata.json`,
   `content-manifest.json` and `build-manifest.json`.

The included local publisher reuses existing refresh path checks, kernel writer
lock, fsync and artifact-inventory primitives. A complete candidate is published
by one same-filesystem rename. Identical retries compare every output byte and
are no-ops. Conflicts are never overwritten. No accepted pointer, source copy,
cache mutation, download or external publication exists. The wrapper currently
does not add a shared SQLite lifecycle entry; integration can own that step.

Build identity pins all nine inputs, all eleven transitive application code/
contract dependencies, Python implementation/version, Expat, zlib, and the
existing deterministic serialization policy. Canonical content hashes and
compressed transport hashes remain separate. Code dependencies are checked
before and after extraction.

## Verification and activation boundary

The tests use authored real-schema-shaped fixtures only. They cover the actual
84-column and 75×3-dictionary shapes, TABLE/ALIM identities, lexical precision,
qualifiers, header/identity drift, refusal of non-pinned bundles, INFOODS energy
separation, deterministic render, atomic interruption, identical retries,
conflicting candidates, output symlinks, fixed Foo output scope, read failure
before output, and aggregate-only receipts. All 61 existing synthetic adapter
tests also pass unchanged.

The retained source bodies were not copied here, downloaded, or executed by
this implementation task. Therefore the actual 3,484-record candidate and its
artifact hashes are not claimed as verified yet. The concrete remaining step is
one reviewed Foo execution against the existing nine read-only pins, followed by
an identical retry and aggregate receipt verification. If exact structural
parity fails, it fails before publication with a fixed diagnostic code; that
specific discrepancy can be corrected without another general research phase.

## Fixed runner integration

The reviewed `ciqual-source-native` dispatcher profile runs readiness, the focused
native tests, `candidate-ciqual-selected`, then the identical candidate command.
Its output directory is derived from the verified 40-character source revision
and a 16-character runtime fingerprint. Requests cannot supply source or output
paths. A runtime change gets a distinct destination; conflicts remain errors.
The retry must report `created=false` and every aggregate field and artifact hash
must match the first receipt. Neither an exit status alone nor a new candidate
on the retry establishes success.

`offmenu.refresh.native_ciqual.sanitize_receipt` exports only exact aggregate
counts, the fixed input-bundle identity, build identity, four artifact byte/hash
pairs and explicit private/non-acceptance boundaries. It rejects unknown fields,
food records, paths, arbitrary text and changed admission claims. The complete
candidate stays in its private Foo directory. CLI failures export only fixed
allowlisted diagnostic codes through the existing dispatcher sanitizer.

The integration uses the handler's existing atomic local lifecycle; it does not
register a synthetic fixture or add a separate SQLite lifecycle. Its manifests
explicitly retain `registryComplete=false`. The dispatcher retains its existing
240-second per-stage timeout, process-group cleanup, output locks and 32 KiB
outer receipt cap for this profile. The handler retains its 256 MiB artifact cap
and all nine read-only input pins. No new runtime/audit configuration, host
permission or source acquisition is part of this integration.
