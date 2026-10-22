# Acquired institutional and municipal menu adapters

**2026-10-22 — implementation/tests, not a production-ingest completion claim.**

`ingest_acquired_menus.py` is a read-only, stdlib-only adapter for the already
acquired files selected by the verified acquisition catalog. No production fetch,
linked-resource fetch, source execution, raw export upload, live Foo mutation or
`./run` change is part of this work. The current Foo run remains untouched.

## Supported contracts

Entry point: `run_domain(domain, sources, context)`; `ADAPTER_VERSION` is exported.
`iter_records(domain, source, context, stats)` and
`project_row(source, row, locator, raw_json)` expose the streaming/projection
contract. Projection returns `(domain-record pairs, fixed schema-need codes)`.

A source must have `acquired_adapter`, `acquired_role`, `format`, `id`, `path`,
`disposition: candidate`, and `metadata.acquisition.verified: true`; restricted,
loaded or unverified inputs are not opened. The catalog owns hash/receipt/rights
verification. This module does not downgrade a hold or infer a source from its
filename. Provenance retains acquisition evidence, source URL/revision, artifact,
resource ID, license, SHA256 and record pointer in private staging.

| Exact adapter | Role / selected artifacts | Domains and representation |
|---|---|---|
| `fr_cnous_menus` | `menu`; 26 manifest XML feeds | recipes: menu → meal/course section → item; ingredients: optional unsplit source ingredient statements; citations: evidence links |
| `fr_begles_menus` | `menu`; `met_menu_cantine.json` | recipes: dated/audience/venue menu → course → item; citations |
| `fr_begles_menus` | `dish`; `met_plat_cantine.json` | recipes: composition anchor + row observation; ingredients: explicit product mentions; citations |
| `fr_toulouse_menus` | `menu`; `menus.json` | recipes: dated/daypart/audience menu → ordered course → item; citations |
| `fr_toulouse_menus` | `dish`; `plats-extrait-de-datameal.json` | recipes: dish/composition-reference anchors + observation; citations |
| `fr_toulouse_menus` | `ingredient`; `denrees-extrait-de-datameal.json` | ingredients: source-native anchor + observation; citations |
| `fr_toulouse_menus` | `technical_sheet_reference`; `liste-des-ft-des-denrees-de-la-cc-tls.json` | citations: registry metadata only, with exact ingredient reference |

No row is promoted to a cooking recipe. `code_recette` is a source composition
reference, not evidence of preparation steps. Recipe references remain null;
quantities and units remain null when absent. Repeated offers across dates,
audiences and source rows survive. Identical anchor records are bounded-deduped;
different observations of the same native dish/ingredient are not overwritten.

## Evidence and honest schema status

Municipal field IDs were verified through the original API console and recorded
in `docs/data-discovery/20261022-recipes-menus/fetch-preparation/endpoint-ready.json`
(the cloud worktree copy is `recipe-menu-discovery-20261022/fetch-preparation/endpoint-ready.json`).
The parser uses those observed IDs, not inferred dish names or export labels.

The [official CNOUS catalog](https://www.data.gouv.fr/datasets/menus-des-restaurants-brasseries-et-cafeterias)
describes identity/date/meal/course/composition. A bounded web attempt to inspect
an original XML feed was unavailable through that tool; no cloud dataset was
acquired. The pinned [ESUP-Portail primary XML mapping](https://github.com/EsupPortail/esup-dining/blob/733e47d9365ab7f604c0085ed4dae4ef66e713c3/src/main/resources/schema/portlet.xsl)
provides the technical structure:

- `menu` attributes `restaurant`, `date`;
- `repas` attribute `nom` for meal/daypart;
- `plats` attribute `nom` for course/category;
- `plat/nom` text for dish name;
- optional `plat/ingredients` text and `plat/code` attribute `valeur`.

The parser independently implements that structure and also preserves nested
restaurant-context variants. No upstream XSLT is executed or copied into the
runner. Native IDs retain their exact strings (no historical prefix stripping or
numeric conversion). Unrecognized XML structure remains in the source tree on
recognized menu records; missing date/venue context generates a schema need.
A restaurant directory without menu nodes is not counted as menus. Generated
tests establish code behavior, not a claim that all 26 acquired snapshots share
one exact shape. Feed-specific schema errors are isolated and reported on Foo.

## Exact relations and hierarchy

Native anchor IDs are `kind:sha256([family, scope, native_id])`; JSON value types,
leading zeroes, suffixes and Unicode are preserved. No fuzzy/title match, suffix
stripping, case folding or numeric/string coercion occurs.

- Bègles dish references require both collectivity and establishment SIRET. Menu
  and composition prefixes map to the same exact two-part scope. Missing scope
  preserves the observation but deliberately creates no menu-to-dish join.
- Toulouse `code_plat` → dish, `code_recette` → composition reference and
  `code_denree` → ingredient are provider-scoped exact joins. A menu code ending
  in an audience suffix does **not** match a stripped composition code.
- Cross-artifact relations carry `target_identity_kind: acquired_scoped_id`,
  `target_source_policy: selected_family`, `target_adapter`, `target_scope`,
  `target_native_id` and the deterministic target ID. Anchor records carry
  `source_family`, `source_scope` and `source_native_id`. A reference is an
  assertion, not proof that the target exists in selected compatible snapshots.
- Same-source hierarchy uses `section_of` / `item_of`; full CNOUS trees also emit
  `contains_menu_entry`. Item-to-ingredient links are explicit. Municipal parent
  anchors are streamed, so children provide reverse parent links without
  retaining an unbounded whole export in memory.
- `cites` targets citation IDs; source citations use `cites_record` with the
  appropriate target domain. Technical-sheet references do not fetch their URLs.

## Semantics, parsing and error isolation

Bègles `menuplatprix` becomes **theoretical production cost, EUR**, not retail
price. Original decimal values and lexical JSON remain intact; no serving basis
is invented. `platproduitnutriment` stays raw with unknown basis. Allergen labels,
including true/false, zero, strings and null, remain source assertions rather than
an allergy-safety guarantee. Whole-meal nutrition is not copied to items. CNOUS
optional source code values are retained without inventing code meanings.

JSON/JSONL readers are incremental. Duplicate-key/nonfinite framed members,
malformed JSONL rows and semantic row failures are isolated; unknowable broken
JSON framing stops that source, never guesses a repair. CSV/TSV retain strings,
empty values, Unicode, leading zeros and decimal commas. UTF-8 BOM is handled;
other encodings must be declared, never silently guessed. Delimiters are declared
or selected from comma/semicolon/tab header syntax. Duplicate headers and ragged
rows are diagnosed; subsequent well-framed rows continue. Actual JSON null is
not confused with CSV empty strings or the literal string `null`.

XML uses streaming Expat with explicit DTD/entity/external-entity rejection,
including UTF-16 documents, disabled parameter entities, nesting/source/record
caps and no network or source code. Complete earlier menus survive a malformed
tail. Read-only no-symlink opening and held-file identity checks reuse the
reviewed retained adapter utilities. The existing `DomainStore` owns batched
transactions, row-size checks, durable errors, source versions and replay-based
checkpoints; a capped run resumes without duplicate logical rows.

Source summaries expose only counters, opaque source keys and finite `REASONS`:
`input_records`, `emitted_records`, record-kind counts, reason counts and
schema-need counts. `projection_status` distinguishes current projection from
schema/join needs or an already-completed source not parsed this invocation.
Never expose payloads, source paths, titles, exception messages, codes or URLs in
public error summaries. Durable errors remain partial on an unchanged rerun.

## Validation and remaining action

```sh
python -m unittest discover -s manual-action/tests -p 'test_ingest_acquired_menus.py' -v
```

23 generated tests cover hierarchy, exact scoped joins, audience/date separation,
cost semantics, allergens/nutrient basis, optional CNOUS ingredient statements,
technical-sheet metadata-only behavior, native ID noncoercion, malformed record
isolation, sanitized diagnostics, CSV encoding/delimiters, safe XML, source holds,
resumption and idempotence. No raw acquired corpus is included in tests.

| Action | Target | Reason | Status |
|---|---|---|---|
| Include adapter/catalog/telemetry in next reviewed runner | Next post-current-run Foo execution | Current runner has not yet used these new adapters | Integration owned by parent workstream |
| Validate selected actual snapshots through this adapter | Verified Foo acquisition cache | Cloud tests are generated; no full raw snapshot accessible here | Await next authorized full ingest, not additional fetching |
| Review any emitted schema/join reason codes | Individual failed rows/feeds only | Missing native scope or unsupported structure must not become invented links | Self-reporting diagnostics prepared; no whole-family fetch loop |
