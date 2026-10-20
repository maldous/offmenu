# Opt-in same-release consumer lookup

`GET /api/data/public` accepts an opt-in pair:

```text
?source=off&barcode=001234&releaseId=example-release&manifestSha256=<64 lowercase hex digits>
```

Supplying either parameter selects curated-only mode. Both must appear exactly
once. `releaseId` is 1–128 ASCII letters, digits, hyphens or periods.
`manifestSha256` is SHA-256 of the **exact published manifest file bytes**,
including any trailing newline. It is not the manifest's self-declared legacy
`manifestSha256` field (which uses a different pre-self-field hash convention).
The caller must obtain the file pin from its selected pack/release metadata.

The existing curated loader verifies these bytes even on a manifest cache hit,
then requires the selected release ID. It retains all existing serving-manifest
and per-file checksum guards. The existing barcode/query engine performs lookup;
no alternate index or adapter is installed. Successful selected responses retain
the existing result and add `manifestSha256` with the exact file digest. Their
query-cache entries are separated from ordinary requests by this file pin.

Malformed/incomplete/duplicate binding parameters return 400. A release ID or
manifest-byte mismatch returns 409. Missing/unreadable/unaccepted curation,
missing source or missing/invalid shards return 503 in selected mode. These paths
never fall through to live OFF/Prices or another source route. A valid empty
result remains empty in that release, rather than attempting an upstream lookup.
Existing country short-circuiting cannot bypass a selected release check.
The selection validates the currently available curated release; it does not
fetch arbitrary historical release manifests or accept caller-defined origins.

Requests without either parameter retain their existing response shape,
curated lookup and source-fallback behavior. This opt-in boundary does not change
`/api/product`, `/api/prices`, source qualification, `accepted:false` origin
candidates, rights, dietary status, or independent acceptance. A correct release
pin establishes identity/integrity, not English coverage or approval to publish.
No consumer pack, real dataset, deployment or runtime activation is supplied here.

Focused invented-fixture verification:

```sh
node --test --test-isolation=none tests-web/consumer-release-boundary.test.mjs
```

All fetches in that file are replaced with in-memory responses. Tests assert
zero live-source fetch attempts on failed selected requests and exercise the
existing curated engine for matching-release requests. Ordinary OFF/Prices
fallback compatibility is separately checked with invented upstream responses.
