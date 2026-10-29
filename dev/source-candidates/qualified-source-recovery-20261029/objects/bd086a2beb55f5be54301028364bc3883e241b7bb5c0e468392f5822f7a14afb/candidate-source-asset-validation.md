# Candidate source-asset validation

PASS: 83 candidate assets across 53 source groups. All are disabled, rights-unapproved and held for review.

- JSON parsing, unique IDs/keys, distinct method+URL+body representations, exact URLs in source reports, reference resolution, null local custody and minimum 30-day TTL: passed.
- 65 GET targets, 4 POST candidates, 14 unresolved target URLs; 6 exact advertised lengths.
- Existing SourceSpec/CachedAcquirer fields reused from integration/global-dataset-foundation-20261018. Mapping adapter and current registry reconciliation are still required; this is not a production registry.
- MAKSTAT POST, CKAN query metadata, Drive viewer/navigation and unresolved publisher downloads cannot be treated as plain HTTPS-file requests. Query strings are retained, never stripped.
- Shared sources have one source group with distinct representations. No 249-country fan-out. Regional CG/MK/SO relevance stays separate from verified country-specific source links.
- No network source downloads, user-computer access, repo writes, raw rows, credentials or invented local-source paths. Prior research probes do not establish acquisition custody.

JSON: candidate-source-asset-config.json
SHA-256: 74a2492a44dfc93a86e0419476b92558fb0c7e70bb8d2912b60fb4ee373dc7da
Bytes: 462527

Adapter coverage: candidate-source-asset-adapter-coverage.json; 13370 bytes; SHA-256 ccad666dc1c66534dabf64e645638a7aa896f81c215fc441c885b337d2d6aca4
Current worker branch worker00/collection-rerun-20261018 / reported 45510bfd was not accessible via GitHub. Existing SourceSpec was verified on the integration branch; reconcile evolving worker schema before use. Held means candidate review/compatibility incomplete, never a provider-denial claim. Current worker source custody remains unverified here.
