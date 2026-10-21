# Selected UniTools native recipe adapter

This is a source-only implementation for the one retained UniTools JSON file
specified by Worker13's single-family contract. It does not acquire sources,
run a collector, read the world-library gzip, or install a runtime permission.
The production selection is fixed to the 2,733,812-byte asset, its retained
five-part identity, repository revision and independently recorded Git blob.
There is no arbitrary path, source factory or fixture switch in the API.

The future custody caller supplies four already-qualified receipt pins through
`UnitoolsSelection`: source-use, custody/sole producer, operation and existing
source-key coverage reconciliation. Each is an absolute path/SHA-256 pair.
Licence existence alone is not a source-use operation grant. Current source
SHA-256 and actual recipe counts remain unknown until a separately selected
read; 501 is the declared count and the historical 499 lead is unproven.

## Finite input and load interface

1. The selected caller opens only `INPUT_PATH` using `O_RDONLY | O_NOFOLLOW`.
   `qualify_unitools_once(selection, held_fd)` requires offset zero, regular
   file, no symlink ancestors, exact size and held/named identity. It reads to
   exact EOF once, computes SHA-256 and Git blob SHA-1 concurrently, verifies
   the independently pinned blob and checks custody again. It returns one
   `VerifiedUnitoolsInput` with immutable raw bytes and classification receipt.
   Close the descriptor in the caller's `finally` block. Do not hash or read
   the source in a preparatory second pass.
2. The bounded strict JSON parser retains byte offsets and original numeric
   tokens. Duplicate JSON keys, invalid UTF-8, nonfinite literals, excessive
   depth/fields and trailing bytes fail. Every recipe-array occurrence has a
   slug/type/disposition receipt; count mismatches and malformed occurrences
   prevent manifest construction/import. Duplicate slugs remain distinct
   occurrences, with explicit conflicts and a publication hold.
3. `asset_from_verified(verified)` builds the one asset from its observed
   SHA-256. `prepare_recipe_menu([asset], accepted_source_adapter=verified)`
   returns the manifest including native code/schema and qualification pins.
   Compute `SHA256(core.canonical(manifest))` only after qualification.
4. Optional diagnostic projection is
   `project_unitools_source(verified, source_language_policy=('en', 'ru'))`.
   The other supported policy is `('ru', 'en')`. Missing chosen-language
   fields fail with exact pointer/ordinal evidence. Both maps and all unknown
   fields remain in an exact `rawNativeRecord` source note.
5. For a separately selected exclusive empty database, call
   `ingest_recipe_menu(db, [asset], accepted_source_adapter=verified,
   limits=..., run_id=..., input_manifest_sha256=...,
   selection_receipt_sha256=...)`. Omit `parser_module` and `parse_asset_once`:
   the native branch rejects caller replacements and uses its fixed adapter.
   Projection/manifest/import consume the qualified buffer without reopening
   the original. Existing SQL tables, transactions, bounds and failure
   retention are reused. Existing publication close/fsync/hash/custody checks
   remain with the execution owner; any `publicationHoldReasons` must hold
   publication. An import summary is not canonical, release or country acceptance.

The native profile requires an idle `sqlite3.Connection` using legacy transaction
control. On Python 3.12+, explicitly select
`autocommit=sqlite3.LEGACY_TRANSACTION_CONTROL` (the existing default); earlier
Python versions use their legacy connection behavior. `autocommit=True`,
`autocommit=False`, and an active caller transaction are rejected with
`recipe-store-unitools-connection-mode` before any database statements. The
caller transaction is left untouched. This preflight is native-only; the
default HTML writer path is unchanged.

The source read has an 8 MiB hard cap, 1,024 occurrence cap and 5,000 ingredient
and step caps per occurrence. Projection has a 16 MiB cap. Worker13's proposed
first load additionally selects 2 CPUs/2 GiB, 120-second worker/180-second outer
limits, 64 MiB database/128 MiB owned output, exclusive output custody and current
disk commitments before mutation. This module does not claim those resources
are currently admitted. No automatic retry or old-stage deletion is introduced.

## Representation and identity

One source occurrence produces one variant, irrespective of bilingual fields.
SQL native IDs are actual slugs; source ordinals and `/recipes/I` pointers
distinguish duplicates. Country tags are retained in the raw native object and
never become inferred origin assertions. Canonical dish and ingredient links,
dictionary/mapping versions, interpreted quantities and units remain null.

Ingredient `originalExpression` is the exact JSON object substring, labelled
`native-json-object` in the raw-record note. Number/string quantity lexemes are
exact JSON tokens; null/missing distinctions survive in the raw object. There
is no invented flat ingredient sentence, unit conversion or portion scaling.
Steps project the chosen supplied text and retain original array order; all
other step fields and both languages remain losslessly in the raw object.
Yield uses the actual `baseServings` scalar token without an invented unit.

Native locations carry `kind=native-json`, source SHA-256, JSON pointer,
record pointer and exact UTF-8 byte range/span SHA-256. They do not invent PDF
pages or HTML text hashes. A selected schema overlay adds this location branch
and null semantic-version fields without editing the accepted shared HTML/PDF
schema. Root attribution, licence URL and all other root metadata are retained
as source notes; repository/revision/blob provenance, unknown acquisition URL
and time, attribution/share-alike conditions and projection change statement
remain explicit in the qualification/projection receipt.

Generated tests patch production constants only in their test process. They
exercise exact 2,733,812-byte generated input, same-buffer import, raw token and
pointer replay, bilingual retention, malformed/count/duplicate dispositions,
custody failure, native code/asset selection and unchanged HTML/DDL behavior.
No retained source body, populated store, PDF cache or scanner was accessed.
