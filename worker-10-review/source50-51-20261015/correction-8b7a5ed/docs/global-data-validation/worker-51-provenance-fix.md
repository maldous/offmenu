# Worker 51 — W10-MEXT-F1 provenance correction

Worker10 independently requested changes on exact candidate 02d5ad3c3c7b9736cfb65e0a49ffd656f9886d30. The five provenance probes were reproduced before editing: release, workbook hash, member hash, worksheet and publisher URL conflicts all passed proof while it reported original MEXT identity.

The successor validates publisher/release/workbook/URL constants against exact retained workbook bytes and pinned release/acquisition manifests. The trusted worksheet index is derived from publisher OOXML workbook relationships and actual member bytes. Unit/component schema and edible-basis header references must match that trusted source. Proof then compares source cells against actual worksheet rows in a bounded pass, rejecting self-rehashed fabricated rows. A conflicting record fails before any successful source proof is returned; empty record proofs also fail.

All five probes now reject. All192 actual records keep the exact prior adapted record-set digest, original Japanese labels/forms/components, nulls and lexical qualifiers. Nine tests pass (the original seven plus provenance/header/row/self-rehash probes). Five retained input hashes and primary main HEAD/index remain unchanged. Prior evidence reports are preserved rather than rewritten. No network source reads, source copies, dependencies, canonical schema or importer changes.

Exact parent-to-successor delta requires the same Worker10 independent reviewer. This owner-side fix is not independent acceptance or corpus/publication qualification. A normal private-origin fast-forward backup with independent remote SHA readback follows the own commit. Production STOP.
