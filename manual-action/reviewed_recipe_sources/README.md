# Retained recipe ingestion: source closure and boundaries

`source_faithful_parse.py` and its schema are exact unmodified PR90 head
`f1faa0d63b6fd46e145122b1843ad3bb9fa60c0f` blobs. `manifest.json` binds both
Git blob SHA-1 and SHA-256. The parser pin is **843d780…**, not the obsolete
5f4c8d9… writer pin. The source-only native UniTools adapter **337604…** is not
replaced, spoofed or invoked with fabricated receipt evidence. No old native
`recipe_menu_store.py` is copied over the current writer.

`../ingest_recipes.py` is a new broad **additive staging** adapter. It invokes
this exact parser for explicitly selected retained HTML adapters when its
optional dependencies already exist. Missing optional dependencies are isolated
to their source, and independent stdlib multi-JSON-LD extraction remains usable.
No package is installed. A JSON-LD record is labelled as script-source
representation; it does not claim the old visible-text qualification.

The broad adapters stream JSON arrays/collection wrappers, JSONL (including
per-line error recovery), CSV/TSV, gzip, known SQLite payload tables opened
read-only, source JSON-LD HTML, Wikimedia revision/slot envelopes, and explicit
text/Markdown ingredient and procedure sections. They retain source objects,
record-level raw JSON where framed, source pointers, language maps and native
numeric lexemes. Container metadata after a large array becomes a separate
source-metadata row; it is not discarded. Unsupported records and raw PDFs are
isolated; parsed PDF section caches preserve their original raw sections.
A partial PDF-cache record keeps logical ingredient/step counts **unknown**,
not zero, and emits no fabricated granular ingredients. This adapter does not
revalidate PDF cache anchors or claim full-template acceptance.

Recipe and ingredient workers use the same deterministic entity/mention IDs and
one independent staging writer each. Recipe ingredient lines are raw mentions,
not normalized ingredient entities. Named source food/nutrition records remain
source entities with unverified cross-source normalization. OFF/USDA ingredient
label strings remain unsplit labels; structured source assertions retain their
reported IDs without promoting them to canonical identities. Product relations
are explicitly source-native/unresolved when no canonical barcode target is
known. Existing product DBs may be read to derive these ingredient rows; they
are never rewritten or copied wholesale. Restricted inputs remain skipped.

The SQLite writer provides resumable transactions and an entity-ID logical view.
Physical record counters describe source-provenance rows, not unique recipes.
Duplicate IDs across source files preserve separate custody/provenance; the
logical view groups them. A bounded in-memory duplicate cache suppresses repeated
objects in a stream, and persistent IDs keep repeats idempotent after rollover.
Existing accepted/live stores and app bindings are untouched.

Tests in `../tests/test_ingest_recipes.py` generate their own inputs and temporary
stores. No original recipe dataset, provider payload, credential, retained PDF,
Foo runtime or source acceptance operation is part of these tests.

Source references:
- https://github.com/maldous/offmenu/blob/f1faa0d63b6fd46e145122b1843ad3bb9fa60c0f/offmenu/refresh/source_faithful_parse.py
- https://github.com/maldous/offmenu/blob/7a7c69063e15f83067b1a13f23a4f352db996ee4/offmenu/refresh/unitools_recipe_adapter.py
- https://github.com/maldous/offmenu/blob/e18ff620e434cb0489c87a2d85069e621fefc4b8/offmenu/refresh/recipe_section_cache.py
