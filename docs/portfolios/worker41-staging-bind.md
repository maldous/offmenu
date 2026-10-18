# Worker41 metadata-to-staging binding seam

Selected request: M-STAGING-BIND-20261018-W41. Baseline accepted develop snapshot
abecb99ee1125730ccbc2824b6ec49ffc5cc4302, not pending PR42/handover source.
The original worker41 checkout and all external immutable reports are preserved.

## Runnable metadata package

`python3 -m offmenu.refresh.portfolio41 --now 2026-10-18T12:00:00Z --output /private/new-report.json`

Supply an explicit UTC clock. The output must be a new file with an existing parent.
To identify unchanged metadata content, add `--previous-report /private/first.json`.
The module imports shared core canonical JSON, strict duplicate/nonfinite parsing,
timestamp/path/hash helpers, the shared field-origin validator, acquisition MIN_TTL
and GLOBAL StageResult. It does not copy country source parsers, register admission,
construct a SourceContract from untrusted metadata, or edit shared modules.

The default catalogue loads from the owned inert Python literal in
`offmenu.refresh.portfolio41_catalogue`, returning a deep copy without filesystem
access. Its values exactly mirror the unchanged `config/portfolios/worker41.json`;
the JSON mirror is not a runtime dependency of a wheel or source distribution.
This code-resource transport does not qualify the referenced source metadata.

The four pinned receipt inputs are the ONLY data files the normal command reads
besides an optional earlier metadata report. It never
follows a receipt's body path, URL, dictionary link or archive member. There is no
network implementation or dynamic plugin. Paths are private Foo-local metadata
locators, not inputs to publication. Small fabricated fixtures are in the test
factory; source documents and bulk data are not test fixtures or committed assets.

`READY_METADATA` means only an authored or otherwise unheld metadata representation
has passed this narrow contract. The real QA/TC/TW/VG configurations remain HELD;
bodyAdapter is null, bodyOperationsAllowed is always empty, acceptedDatasetRecords
is null and countryComplete is false. No automatic staged food records are created.

## Literal origins, release, unit and applicability

The configuration pins each exact retained receipt by path/size/SHA256 and uses
literal JSON selectors. The selected snapshots are labelled retained-20261014,
explicitly NOT verified publisher editions. Every metadata data scalar has a
source field origin bound to the receipt hash and exact selector; unknown native
unit/basis are null code-policy constants with a policy fingerprint, not source
cells. Source role/use language and historical body hashes are retained as metadata.

| Country | Metadata selector family | Domain applicability and missing evidence |
| --- | --- | --- |
| QA | /version, /kind, /utc, /rights/acquisition, /network/0/sha256 | Qatar Now catalogue only. No recipe/body edition, ingredient/quantity/yield/method witness or applicable extraction grant. |
| TC | /responses/1/{version,kind,utc,acquisition_basis,sha256} | Historical headline inflation is macro context, not item prices/baskets. Exact rate unit/base/selector and use/edition evidence remain missing. Magazine reproduction prohibition remains separate. |
| TW | /version, /kind, /utc, /rights/acquisition, /network/0/sha256 | AFA38766 PDF identity is not recipe field/quantity/yield/method or nutrient basis. Exact edition, exception-aware use applicability and internal selectors remain missing. |
| VG | /documents/0/{url,utc,rights,sha256}, /scope | One venue dinner-menu metadata. Item/serving/unit/currency/provider field witness missing; Protected Basket programme requires a distinct actual observation release. |

countryTypes=[] deliberately establishes no accepted food-domain applicability.
The portfolio still requires ingredients, recipes, nutrition, retailers/providers,
prices/baskets and dietary references where applicable. Their actual release/schema/
semantic-review completeness is not inferred from these four receipt bindings.
Historical20/52 are custody leads for TC/VG, not present exclusive actor proof.
Missing a custodian label is not a new legal prohibition: real source-use/format
unknowns and the surviving explicit body holds are retained independently.

## Replay, cache, and diagnostics contract

originalAcquiredAt comes from the exact receipt selector. validatedAt is a separate
metadata evidence observation; it cannot replace or reset acquisition age. Content
identity excludes validation time and assessment clock. Identical source/release/
receipt fields yield unchanged-content-no-op with the previous build key. The
report itself is a new immutable assessment, not an accepted pointer move.

The metadata cache recommendation reuses shared MIN_TTL=30 days, never mtime. Both
under30 reuse and older conditional-review outcomes allow zero network requests.
No force-download/revalidate escape is offered. This is an advisory metadata seam,
not verification of an original cached body or a production acquisition engine.
Held use remains held even if input is fresh, pinned and has unchanged content.
No real refresh is performed. Full country automatic acquisition must use existing
reviewed shared acquisition/refresh orchestration after the source-specific grant,
field-origin/semantic schemas and immutable review are selected.

Per-source outcomes: READY_METADATA, MISSING, HELD, MALFORMED, STALE. Diagnostics
are fixed codes; loader exception contents are not emitted. Each source is isolated;
a malformed/missing receipt cannot suppress diagnostics for independent peers.
Returned GLOBAL StageResult objects are summaries only, not installed dispatch
bindings or resource-isolation attestations. No source engine, worker, subprocess,
queue or controller is started. The pure assess function performs no filesystem IO.

## Current official documentation, 18 October 2026

AFA: https://www.afa.gov.tw/cht/index.php?code=list&ids=97
The open-data notice permits reuse with attribution within its stated copyright
scope and preserves exclusions for specified works, privacy and other rights.
Its inspected body refers to the Central Regional Branch while the receipt is a
main AFA cookbook download; exact applicability and special-work exclusions remain
unresolved. No blanket grant is inferred or source hold lifted. Other AFA portals'
notices are not silently substituted for this file. Locator: sections one/two,
rendered lines142-158; publication/update dates are notice dates, not cookbook dates.

TCI: https://www.gov.tc/stats/ links “Understanding the TCI Consumer Price Index”
to https://drive.google.com/file/d/1HkxcGRQJSBmkl8JZBeQfocHF9cR553mi/view?usp=drive_link
The method-document read returned “Failed to fetch ...: Cache miss”. No retry,
credential flow or alternative host was attempted. No field unit, base, missing
value semantics or reuse grant was inferred from current homepage indicators.
The distinct held DDME/MOH/merchant paths were not requested.

## Exact shared-interface request for integrator00

No shared change is required to run this package. A useful separately reviewed
follow-up would expose `plan_retained_input(source_id, release_id, bundle_sha256,
original_acquired_at, validation_events, now)` from the existing generic policy
module. It should be pure/offline, preserve original age, return under30 zero-network
reuse and stale review outcomes, and use explicit identity rather than the
fixture-only `plan_fixture` registry. Existing core.cache_policy is Wikibooks-bound;
using it and relabelling its output as these sources would be wrong. Do not broaden
CachedAcquirer or force policy here; do not bypass PR42's reproduced retry P2.

Current package remains portfolio-owned metadata config/glue/tests only. Review
must independently assess exact commit/diff and real-source holds. Integration00
owns any core change and develop integration. Golden promotion, source bodies,
production/CIX, DEV7645 and Finland/Frida/nativeNO-FR restrictions remain separate.
