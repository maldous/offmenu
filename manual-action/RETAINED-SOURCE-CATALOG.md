# Retained-source catalog

`ingest_catalog.discover_sources(options)` is an offline, bounded discovery stage
for the real ingest runner, not a diagnostic-only gate. It returns individual
file classifications, adapter descriptors, independent errors, eight-domain
counts and a resumable cursor. It does not fetch data, execute source code, open
retained databases for writing, contact Foo, or upload catalogs or source bodies.

## Coverage and limits

- Default selected root: `/home/user/src/offmenu-data`. The one exact published
  recipe-retention terminal report is also considered if present. Additional
  roots can come from explicitly selected trusted project reports; ordinary
  source manifests cannot widen the selected roots. No home-wide search occurs.
- Documented qualified recipe collections and existing native collections are
  prioritized when present, followed by the full selected-root walk. The default
  budget is 250,000 inspected paths, depth 40 and 120 seconds, not a hidden
  first-1,000-file sample. Directory enumeration is paginated.
- `truncated`, `stop_reason` and `resume_cursor` identify unfinished discovery.
  The runner persists the cursor and merges the next page by stable source ID on
  the next invocation. A depth stop needs a larger explicit depth bound. A
  complete traversal is not proof that every historical acquisition exists.
- JSON/JSONL/CSV/TSV manifests and inventories can bind exact retained paths.
  Metadata reads default to 4 MiB per file; structural samples to 64 KiB. Limits
  and failures are explicit. Dataset records are not included in descriptors.
- JSONL/JSON/CSV/TSV/SQLite/Parquet/HTML/PDF/text/Markdown and compressed JSON
  families are recognized, as are formats requiring an additional bounded
  adapter. Recognition is not a claim that an optional dependency is installed
  or that an unqualified source can be transformed faithfully.
- Paths and inodes are deduplicated. Full byte digests are calculated only for
  small files (default at most 1 MiB), never huge inputs or SQLite databases.
  Private household bodies are not sampled or hashed. Known restrictions follow
  hardlink identities and cheap byte-identical aliases; updates also apply to
  earlier catalog pages. This does not claim undiscovered large byte copies are
  cryptographically reconciled.
- Symlink leaves and ancestors, credential-looking paths, code caches, special
  files, and the runner's state/output directory are excluded. The current
  `state_dir` and any explicit `exclude_paths` are excluded recursively so a
  subsequent run cannot ingest its own staging databases or progress files.

Descriptors include `id`, private local `path`, `format`, `compression`,
`provider`, `kind`, `domains`, licence/custody hints, observed file identity,
`existing_store`, `loaded`, `restricted`, `incomplete`, `disposition`, `reason`
and narrow metadata. SQLite sidecar presence, size, inode and modification time
are recorded without reading database contents. Metadata/source claims are not
publisher authenticity or current verified row counts.

## Evidence-backed source bindings

The implementation was prepared from these pinned, published project sources:

- [Continuation review delta](https://github.com/maldous/offmenu/blob/d37125e286841ba240e2bd2d3e8cd3ddb737dfc4/continuation/cloud-continuation-review-delta-20261022.md)
  and [source-purpose audit](https://github.com/maldous/offmenu/blob/d37125e286841ba240e2bd2d3e8cd3ddb737dfc4/source-purpose-audit/REPORT.md).
- [Sixteen exact native collection directories](https://github.com/maldous/offmenu/blob/52b6a50a59b458bdb49fe7ea090b72c63a4b1a30/docs/owner-manifest-metadata.md).
- [World-recipe receipt](https://github.com/maldous/offmenu/blob/52b6a50a59b458bdb49fe7ea090b72c63a4b1a30/docs/world-recipe-research-20261014.json)
  and [retained source normalizer](https://github.com/maldous/offmenu/blob/52b6a50a59b458bdb49fe7ea090b72c63a4b1a30/scripts/collect-world-recipes.py).
  Exact source families under the default root include
  `recipe-research-20261013`, `recipe-wikis-20261013`,
  `world-recipes-common-input-20261014` and
  `curated-world-recipes-common-20261014`. UniTools uses the retained
  `unitools.json`; Wikibooks uses recorded `revisions-*.json` and
  `linked-revisions-*.json`; normalized collections use
  `normalized.jsonl.gz`, with one `[record]` packet per line and provenance
  outside the record's `data` object.
- [Source-faithful HTML run](https://github.com/maldous/offmenu/blob/52b6a50a59b458bdb49fe7ea090b72c63a4b1a30/docs/operations/source-faithful-parse-20261020.md)
  binds retained parsed recipes and menu items, while retaining their specific
  private-research/reuse restrictions.
- [Supplier source contract](https://github.com/maldous/offmenu/blob/52b6a50a59b458bdb49fe7ea090b72c63a4b1a30/docs/private-source-suppliers-import.md)
  binds `wikidata-businesses-20261013-native/normalized.jsonl.gz`.
- [Overture collection](https://github.com/maldous/offmenu/blob/52b6a50a59b458bdb49fe7ea090b72c63a4b1a30/docs/collections/overture-food-places-2026-09-23.1.json)
  is separate from the historically partial OSM planet transfer.

The historical 25,135 recipe/source records, 1,378 recipe-original paths and
988-file prior cohort are separate scopes, not summable recipe totals. Overture's
16 files/12,681,108 selected places are historical source counts, not verified
suppliers. OSM's expected 95,244,184,503 bytes and last observed 88.47 GB partial
are not completion, present custody, or loss evidence. No missing exact OSM path
is invented.

The full identifier store's documented path is
`barcode-identifiers-worker57-full-retained-v1/identifiers.sqlite`; the old
`selected22` demo is not substituted for it. Existing OFF/USDA product counts
4,807,217 and 2,101,279 remain historical hints. Rich product-store paths are
resolved from actual retained manifests/report bindings, not guessed. Every
SQLite file is marked read-only reuse evidence, but generic SQLite presence
alone never sets `loaded=true`; existing-store adapters must inspect supported
schema and current counts safely. Product references also route to ingredients
and dietary adapters for explicit source-field derivation, not duplicate product
loads or inferred dietary safety.

## Dispositions and rights

`candidate` means an adapter may consider the source, not that all rows are
accepted. Other dispositions include `existing-store`, `metadata-only`,
`restricted`, `incomplete-hold`, `duplicate`, `adapter-required`, `unclassified`,
`documentation`, `excluded`, `missing`, `unreadable` and `historical-demo`.
Unknown licences remain explicit and are not a blanket global ingest gate.
Specific established restrictions are retained.

In particular, the raw historical archive's wrapper Unlicense does not clear
all underlying books. Its unqualified raw scope remains held; already-qualified
normalized recipe collections remain eligible under their per-record provenance
and rights. Known private HTML/menu outputs, Recipe1M, unlicensed CookLikeHOC
and the identified noncommercial/uncleared recipe scopes do not enter the
shared reference corpus automatically. Household profiles and stock are not
fabricated from reference datasets. A source absent at one selected path is not
labelled globally lost.

All generated-fixture tests are offline and contain no retained source payloads.
They cover more than 1,000 files, resume and depth cursors, mixed formats,
manifest and TSV bindings, state-directory exclusion, independent errors,
SQLite sidecars, symlink/credential refusal, duplicate identities and rights
propagation across catalog pages.
