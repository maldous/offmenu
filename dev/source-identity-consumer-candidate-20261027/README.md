# Source identity consumer candidate R2

Unadmitted source candidate. No app, role, endpoint, provider or production adoption.

This narrow USDA reader presents exact source identifier claims with provenance,
attribution and explicit unknown names, language, food type and nutrition. Food
enrichment is not required to present a source record. It makes no canonical
identity, physical equivalence, normalization, planning or Gold assertion.

The two closed Worker19 indexes contain 2,574 source observations and lexical
barcode claims: 2,559 checksum-valid and 15 invalid. Invalid strings are retained
without repair, and native USDA-FDC identity remains separately queryable. The
two producer schemas are adapted explicitly; no raw shard is reopened.

The source-rights contract is Worker56 `56a7c4c3...`, with distinct product-role
`e648f1d8...` and native-representation `5f45979f...` qualifications. This contract
does not rewrite the historical private-only operation receipt into permission
to serve. A new, exact local field-operation admission and focused review are
required. Public publication and production remain excluded.

`manifest.review-candidate.json` is the selected prepared manifest. The earlier
`manifest.prepared.json` is retained preparation history. `internal-source-custody.json`
contains internal paths and must not be served. The selected manifest and returned
observations contain no local file paths or raw payloads. No actual admission is
issued in this package. Synthetic admissions occur only in focused tests.

The existing foundation reader's exact seven-field source subject is preserved.
Composition leaves qualified phase rows unchanged and suppresses partial claims
only for the same complete source subject. Technical phase failures are not
silently converted into missing products. Targeted queries against the current
f933 USDA index found 16 already-qualified source subjects, leaving 2,558 additional
source claims. This is selected-cut membership, not a new live query or a corpus
rescan, global unique-product count or serving increment.

The bounded selected index is 3,310,666 bytes; the prototype caps index input at
8 MiB and 10,000 observations. It does not load, publish or provide access to the
entire retained 5.24-million-key index. Larger releases need the existing scalable
origin/index mechanism, with the same field and operation bindings.

Validation: `node --test source-identity-reader.test.mjs` (11 focused groups).
`prepare-closed-identity-metadata.py` uses exclusive output creation: do not replay
it into the occupied directory. The closed inputs, prepared data and membership
evidence remain in local runtime custody; Git custody contains code only.
