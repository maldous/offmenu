# Historical asset bindings candidate

99 existing exported descriptors now have exact historical evidence joins. The candidate contains 289 guarded metadata field replacements and 388 identity/value tests. It creates no new asset ID, source key, execution selection, rights grant, country edge or local-custody claim.

## Concrete recoveries

- All 22 native mappings match original source ID, release, canonical types and derived-manifest URL. Publisher attribution, historical licence context and source-specific release evidence are attached. Derived manifests remain distinct from original source inputs.
- 17 MEXT file descriptors match an exact publisher-observed download URL and the retained `2023-corrected-20260327-main` release. The candidate fills missing publisher citations and declared PDF/XLSX formats. These are 12 XLSX and 5 PDF distribution descriptors, not 17 newly downloaded assets.
- Four recorded SHA-256 matches recover historical source-input identity without using filenames: three Open Prices exports and the old Open Food Facts input. No file was opened or rehashed. The old OFF count receipt remains superseded and the existing file descriptor receives the same explicit count hold.
- All 16 Overture member descriptors match the full object key, release and per-member SHA-256. Their historical selection criteria and member counts are linked, without fabricating a requested/final URL or per-country coverage. The manifest digest is never used as the concatenated member digest.
- The USDA full archive descriptor matches the historical archive SHA-256 and release. The exact April 30 CSV ZIP distribution is retained as a candidate only. Missing original request/final URL custody is not inferred from its filename.
- 17 focused global citations, six shared basket methodology citations and 17 country-level basket citations are joined by exact URLs and original citation evidence. Two citations belong to both global and methodology groups, so group counts overlap.
- All 17 country-level basket citations previously exported with `[null]` source IDs recover their original `C###` basket-register IDs. Documentary country and publication year are labelled separately from dataset release or coverage.
- One existing Vanuatu reference-document descriptor joins the exact historical FAO report URL. Its citation and declared PDF format are supplied without promoting it to a national basket dataset.

## Exact source-input matches

| Exported asset ID | Historical source input | Recorded SHA-256 |
| --- | --- | --- |
| `file:c82823748e38c1c8ec486217` | Open Prices prices | `337f7bc662a8c8f880c457d966fffed7998722b25f2ed460b6194ba01f6653e0` |
| `file:c24f7e05435fd2d5ec0f6616` | Open Prices locations | `94f3b6b9d2ac00dae4d5827f5ea4fe0edf3c5994d5e50b2ef1491e659d27c506` |
| `file:11607d7435415472028c10ad` | Open Prices proof metadata | `f7be3b51454af92d9f77f406253d2c8bd452ac6b89599cc2b7b4057791585c78` |
| `file:65297c67a3360efe9a02ef79` | OFF historical input; count receipt superseded | `11f50515dc79181f385df8e59d37ae5ddb85b9b932f84b6411055e026d84680e` |

All four are recorded-metadata matches. Their existing integrity and local-binding qualifications are unchanged.

## Counts and remaining work

The simulated candidate removes 22 `publisher-citation` gaps and 18 `format` gaps. The former changes from 1,292 to 1,270 and the latter from 2,883 to 2,865. These are metadata gap occurrences, not newly acquired files, verified rights or newly complete sources.

All 2,922 exported descriptors remain unresolved. The authoritative total remains 2,923 descriptors including the separately verified WFP Libya original omitted from this unresolved export. All 3,105 unlinked country/type requirements are untouched. The overlapping reason-category totals are unchanged.

Rights/selection, custody, integrity, request contracts, original acquisition clocks, destination and budget holds remain. OSM documentation is not an extract; S031 is the HDX API cookbook PDF, not a WFP price file. UN M49/UNSD, FAOSTAT and UN Comtrade bindings remain unresolved. No old OFF counts, broad country coverage, NZ/LK provenance repair or native execution permission is implied.

## Application boundary

- `historical-asset-bindings-patch.json` contains the readable evidence dossier, exact source/export IDs, joins, before/after values, unknowns and reason accounting.
- `historical-asset-bindings-rfc6902.json` contains the direct RFC6902 operations against the exact published `unresolved-assets.json`, including tests for every asset identity and before value.
- `historical-asset-bindings-validation.json` records local metadata-only simulation results.

The target export is pinned at [e382d841](https://github.com/maldous/offmenu/blob/e382d8413c7073e0f27edf2503f4729e30b14909/docs/registry-candidate/2026-10-18/unresolved-assets.json), SHA-256 `3028ef06a2748f898ded96670130c038f80a27918daffb0b56b7e0051473bcdb`.

Historical recovery is pinned at [61504bff](https://github.com/maldous/offmenu/blob/61504bff6725375b7720bc47c112ce24d05f5e8b/docs/collection-preparation/20261018/historical-source-catalogue-recovery.json), SHA-256 `244ac78b255762564c9931f822365667bf89ab804ab04bf581d9b5badfea798b`.

This is a metadata-export patch, not a runnable acquisition-selection configuration. Owner00 retains runner/schema adoption; owner57 retains country/type and exact runtime applicability reconciliation. Applying this patch to the metadata export does not authorize or perform either. Do not apply against a changed export without reconciling the guarded identities and values.
