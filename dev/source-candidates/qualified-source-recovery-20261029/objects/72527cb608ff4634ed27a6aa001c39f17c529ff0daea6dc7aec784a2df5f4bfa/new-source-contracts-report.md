# CG / MK / SO candidate request-contract patch

## Result

`new-source-contracts-patch.json` is a candidate **assetCatalog fragment**, validated against the exact `#/properties/assetCatalog` subschema of `offmenu-acquisition-selection/2`. It is not a full selection registry, JSON Merge Patch, or executable acquisition configuration. A reviewer must reconcile individual entries by asset ID; never replace the current catalog or append already-known IDs as duplicates.

46 entries: CG 7, MK 20, SO 19. They preserve 33 direct-download GET contracts, 6 metadata-only GET contracts, 4 read-only POST declarations, and 3 existing source-page citations. Twenty further source-page/viewer/unresolved candidates remain in the source research bundle and are not expanded here.

- MK-07 and MK-09 include the exact recorded one-cell request bodies, deterministically serialized as UTF-8 JSON strings. These are method examples, not full acquisition queries.
- MK-08 and MK-10 have no known body. The body is omitted rather than invented; neither is executable.
- GET metadata stays separate from dataset rows. The CKAN `id` query is preserved verbatim, and `query_keys` is explicit.
- All source keys remain empty. There are no execution sources, selected claims, requirement/binding additions, resource budgets, destinations, rights approvals, enable-flag changes, or new acquisition requests.
- Country references and research source-type labels are preserved; owner57's canonical 13-type applicability mapping is not inferred.

## Existing-ID reconciliation

| Research candidate | Existing descriptor ID | Evidence / limit |
|---|---|---|
| CG INHPC | `citation:9e5e083da038bf0b94926017` | Exact publications-page URL only; August PDF/Excel original locators remain unknown |
| MK 2014 IPH guide | `file:838e31630572feacfe55ce28` | Provisional: SHA-256(URL) first 20 hex characters match published path component; advertised length also matches 1,564,693 bytes; original receipt confirmation remains required |
| SO FSNAU general MEB workbook | `file:f13bd54936e0c5e651977015` | Exact request URL matches published descriptor |
| SO FSNAU urban MEB workbook | `file:2ac7813d7490b28e5c354fc8` | Exact request URL matches published descriptor |
| SO August 2026 CPI PDF | `file:b2756fa860c9ddbb669ac4ce` | Provisional URL-hash path correlation; source release agrees; original receipt confirmation remains required |
| SO 2026 CFSVA PDF | `file:4c26b05425d3dacafe09bc49` | Provisional URL-hash path correlation; source release agrees; original receipt confirmation remains required |
| SoBS products | `citation:9dc68b0c2da730ac90c61465` | Exact directory URL; citation only, no machine-readable distribution established |
| SoBS providers | `citation:d9b8c93f0e961873a7d2105d` | Exact directory URL; citation only, no machine-readable distribution established |

The shared FSNAU markets citation `citation:ac49a64eed7363559e54fc4f` is related source-page evidence, not a workbook identity. No update is made to it. Three hash-path matches are expressly provisional. Thirty-eight `candidate:` IDs are preparation identifiers, not newly assigned stable registry IDs; absence from this pinned export is not absence from Foo.

## Custody and holds

The published metadata declares five relevant originals. Its paths, hashes, byte lengths and acquisition clocks are preserved as **recorded metadata**, not freshly verified source custody. No receipt or source original was read on Foo; no original was rehashed or downloaded by this adapter. Current bindings remain unknown.

The parent-reported country summaries (CG 6 references / 23.31 MB; SO 4 files / 14.02 MB; MK 8 files / 5.93 MB) are aggregate context, not asset-by-asset proof and not a download queue. Reconcile the current original receipts before any network request. The pinned export can lag those summaries.

Existing access, source-use, rights, denial and ownership holds remain. Legacy query/POST transport holds from the older research configuration are preserved as historical holds: the published v2 schema now represents `query_keys`, `request_method`, `request_body` and `public_read_only_post`, but structural field support does not prove deployed runner support or authorize execution. A declared licence is not rights admission.

## Verification

- Exact published assetCatalog JSON Schema validation: passed.
- Request fields with SourceSpec analogues validate against the published v2 property definitions: passed.
- Unique IDs, HTTPS/credential/fragment sanity, GET empty bodies and explicit query keys: passed.
- The two supplied POST bodies round-trip to the original research objects; all selectors are bounded single-item selectors; output is `json-stat2`: passed.
- Missing bodies, resources, destinations, approved source keys and fresh custody remain unfilled: passed.
- No source-network calls, Foo access, raw rows, credentials, framework implementation, registry adoption or repository/control/main changes: performed none.
- Full runner semantic/gate/integration tests: not run; runner implementation/configuration was not part of the publication.

Detailed validation and all entry dispositions are in `new-source-contracts-validation.json`. The builder is `new-source-contracts-work/build.py`; it reads local metadata only and uses the existing JSON Schema validator.

## Immutable inputs

- [Published schema and metadata export](https://github.com/maldous/offmenu/tree/e382d8413c7073e0f27edf2503f4729e30b14909/docs/registry-candidate/2026-10-18)
- [Research candidate configuration](https://github.com/maldous/offmenu/blob/61504bff6725375b7720bc47c112ce24d05f5e8b/docs/collection-preparation/20261018/candidate-source-asset-config.json)
- Schema SHA-256: `884ff1bef5e878ea8b82fe2cbf63816858104f1700cbbd16a390fb63dc333d2f`.
- Unresolved export SHA-256: `3028ef06a2748f898ded96670130c038f80a27918daffb0b56b7e0051473bcdb`; Git blob `9621a1f323d9524dc2f5fbb8b1095aa82f3c5243`.

Local input bytes were checked against the published manifest. The initial materialization had one additional trailing newline from the file-writing tool; it was removed only after verifying that the resulting byte hashes exactly matched the published originals. No semantic rewrite was applied to the evidence copies.
