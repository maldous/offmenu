# Discovery to retained offline adapter evidence

`offmenu.refresh.adapter_mapping.assess(matrix_path, ledger_path)` adds a separate,
metadata-only capability view to the existing coverage assessment. It reads only
the original pinned 249-country matrix and 1,303-source discovery ledger. It does
not fetch source bodies, invoke parsers, change the existing coverage classification,
register admissions, create Foo jobs, accept records, or publish anything.

## Reconciled result

Against the exact original inventory:

- 15 retained-format candidate adapters: seven national, three product and five reference families.
- 18 discovery entries link to those retained adapters. Seventeen have unverified discovery format/release compatibility; CNF discovery 2026 explicitly differs from retained 2015.
- Three additional evidence-only links: discovery:S045 to Overture attribution/licensing documentation; discovery:S049 to Wikibooks copyright documentation; src-24921f46d04f to USDA branded-field definitions.
- Four held sources remain held: Finland, Frida, Norway and France.
- 1,278 entries remain unsupported in this added view, including dietary guidelines without a reviewed retained parser.
- Zero compatible discovery payload bindings, production admissions, accepted records or whole-country acceptances.

These categories total 1,303. The three new links close document-to-family lookup
gaps only. They do not reduce the number of unbound production sources. Original
coverage counts and all source/country blockers remain byte-for-byte equivalent
as Python values after removing the added annotations.

## Exact joins and provenance

Only exact discovery IDs already inspected in the pinned ledger join to families.
No URL hostname, title, HTTP success, licence name or country creates a mapping.
Each row includes the original ledger pin, discovery ID, recorded URL and research
reference. Existing capabilities supply the exact retained source/release identity,
historical handler Git blob and scope. The existing `capabilities.py` identifiers
remain canonical; no new release aliases or API-to-bulk compatibility are invented.

Ledger: 1,701,843 bytes, SHA-256
`2f3c917a6463153824b8c807b41707870e7f763c65b5ff7957ec4988cd96bfcf`.
Matrix: 133,210 bytes, SHA-256
`894e05f09744c76b790f8e5f159141bed6c308a9af3d90c3c82aa79105cf5ea8`.
Historical mapping evidence remains `corpus/common-source-mappings.json`, Git blob
`858c4de5f6e27deb049ee8bc27567a40461bad49`, as documented by existing coverage.

Supported formats are the reviewed local contracts: exact national workbooks or
archive-plus-extracted bundles; OFF/Prices gzip JSONL; USDA relational CSV ZIP;
Wikidata SPARQL JSON; Wikibooks revision JSON; FoodOn own-namespace RDF/XML;
QUDT selected lexical Turtle blocks; and Overture JSON projection. Overture
Parquet ingestion and QUDT general Turtle interpretation remain unsupported.

National country/domain evidence is inherited only from retained capabilities.
Global families retain empty country scope instead of being multiplied across all
249 countries. A document linked to a family never inherits its data scope or
confers its rights. Actual acquisition, custody, notice verification, full-release
scope, semantic qualification and acceptance remain independent gates.

## Refresh and integration boundary

The descriptor reports a minimum 30-day refresh interval and prohibits AI refresh.
It neither schedules nor enforces a new runtime refresh policy; existing reviewed
acquisition/cache gates continue to own enforcement. Shared descriptors are keyed
by source and retained release, never country. All source provenance is retained.

This additive module is intentionally not wired into existing execution or
acceptance paths. Consumers can call the new assessment when they need accurate
retained-format availability without changing historical coverage semantics.
Tests cross-check national and reference adapter sets and reference release/format
contracts, preserve holds/mismatch/zero acceptance, reject missing supporting
metadata, and demonstrate no domain-name inference or implicit global coverage.
No original large inventory or raw dataset is part of this three-file overlay.
