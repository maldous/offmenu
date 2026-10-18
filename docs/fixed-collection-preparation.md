# Fixed collection preparation

The fixed `collection-prepare` profile imports the corrected owner snapshot and derives useful metadata dispositions. It activates no source and invokes no source transport. The request stays exactly `schemaVersion`, `jobId`, `profile`; paths, commands, selections and budgets cannot be supplied through the request or environment.

## Immutable composition

- Runner base: `ea3988b88bf33bbe288b974b94650b6e741f89cb`.
- Control base: `2f29a00de5edf70a701936726889b175cd877263`. The separate control preview adds only the profile choice, publisher profile allowlist, two step IDs and exact profile-step sequence. Both trusted-source pins, runner identity, permissions, publisher verification, PR31 and receipt lineage remain unchanged until the separately reviewed source-pin substitution. This is not a workflow copied from develop.
- Collector CLI, acquisition/core and 75 focused tests: exact reviewed bytes from merged `37903ac616e6b3c1a5228f0acbcfc67acf4df08b`. The existing `scripts/collect-source-access.py` and `offmenu.refresh.acquisition.collect_registry` remain the collection implementation.
- Adopted r6 registry: `b15de9593d242d36a63d2b00dd6078d57b4d82a3`, entry `docs/registry-candidate/2026-10-18/CURRENT249.json`, registry SHA-256 `c24dbcb802d1f0d8fe617f08de42c28a60c216a1f136614509b990d7d1d63bab`.
- Lookup: commit `769df4a95465aa9396c3f5a7b5f3de390f6b075d`, `docs/registry-candidate/2026-10-18/country-lookup-handover/adopted-country-index-summary-20261018.json`, SHA-256 `554b66c8ab159ce01de6b9042ec624ebe31e8beb570b0395d0be6a4f83235880`. This bounded index has 1,933 asset descriptors and 96 detailed recipe/ingredient/archive records, not the full 3,603-asset registry.
- Corrected snapshot: commit `4aa0976b9dc509b91f76874717f9de5e5e5529df`, `docs/handover/2026-10-18/foo-owner-custody/snapshots/20261018T133622Z-408b58302fc3a4fd.json`, 1,104,001 exact bytes, SHA-256 `408b58302fc3a4fd498497e8b769d374261b9002b04f368249bb6d088e8b294c`, Git blob `f4506a58914e0be199527eb6f918b00803ca661e`.
- Pure validator: commit `976a6566ffd9b9790e48533eddc2b23e90aac51c`, `scripts/foo-owner-handover.py`, SHA-256 `a628602ad83299f0e24f746cd36cf85df7ffc6e510200f7023f9c44f54bf1916`. The exact verified bytes execute in memory. `validate_imported_snapshot` validates the complete `/2` snapshot without native files, processes or network. Version 1 cannot qualify.

The fixed steps are `readiness`, `collection-preparation-tests`, `collection-prepare`. Existing dispatcher locking and child bounds apply. Every input is independently byte-pinned; metadata input reads are limited to 8 MiB each and detail output to 16 MiB. The immutable dependency files can be composed using their existing Git blobs without reuploading their contents.

## Deterministic metadata results

The actual snapshot was observed at 2026-10-18T13:36:22Z. Local metadata-only verification imports 98 packets and all 6,471 projected records. Of these, 2,184 have a source/asset/URL identity and form 2,179 dispositions; 4,287 unbound metadata fragments remain separately preserved. These are metadata observations, not food rows or unique original-file counts.

| Disposition | Count |
|---|---:|
| Held | 103 |
| Ownership observation | 34 |
| Partial | 2 |
| Retained-reported | 162 |
| Unresolved | 1,878 |

Physical retained evidence is recorded independently on 236 dispositions, including sources whose stricter holds take precedence. There are 65 matched dispositions covering 64 distinct adopted assets: direct exact asset IDs or same-row exact URL/SHA-256/byte matches. Hash-only fragments are never joined by adjacency. Descriptive release-label differences are preserved explicitly without asserting release equivalence or currency. Country/type acceptance is not required to report an exact retained original, and a country edge never duplicates storage.

All matched r6 source-use holds and unresolved constraints survive. Compound held/denied/stop/no-retry states remain blocking; `held-locally-with-evidence` describes possession and does not itself create a source-use hold. The owner26 CA cookbook partial retains 33,538,266 bytes and its explicit STOP_NO_RETRY state. PH20 and other baseline source constraints remain intact. Four owner31/52 packets are explicitly withheld by source hold; no absence is inferred from their zero projected records.

The 39 claim-file observations provide adverse ownership/duplicate evidence but no current clearance. All 32 reservation observations are unbound and explicitly counted; zero source-bound reservation blockers therefore does not mean zero reservations. Catalogue scope remains non-exhaustive, claims identified, reservation catalogue unidentified, and unknown commitments are never assumed zero. Capacity observations and the original planning baseline are retained verbatim as evidence; this profile establishes no admission budget or current free-space guarantee.

## Output and safety

The complete metadata detail is atomically published, without replacement, inside the already-existing `/srv/offmenu-refresh/outputs`; exact-byte reuse supports retries. Stdout is a closed summary containing its content hash, input snapshot hash, disposition and conservation counts, with all acquisition/claim-change/coverage flags false. No raw source body is read or uploaded. The profile creates no mount, permission grant, credential, claim, reservation release, coordinator or service.

The source allowlist is empty because this selected batch is custody preparation rather than a transport trial. The minimum cache policy is 30 days. Every disposition remains disabled for acquisition. An unmatched record means unresolved metadata, never a missing download.

## Useful next batch and remaining acquisition facts

The selected next runner batch is this exact corrected-snapshot import and deterministic disposition report. Its local synthetic and actual-data checks are complete; publication, live pin substitution and one request remain separately controlled integration actions. The observed output must be reconciled with the normal receipt/publisher lineage before being described as actual Foo execution.

A later acquisition must pin a specific existing collector registry and licensed allowlist with source request/release/representation, source-specific rights, current ownership facts, no prohibitive hold or uncertain partial, per-source byte/time limits, output location, 30-day reuse and all-results capture. Shared physical assets must deduplicate before transport. The current missing fact is an exact approved, permitted, distinct and unowned source selection, not canonical food typing or semantic/gold acceptance.

The existing 88,418,025,472-byte full-pool planning bound already includes the 20 GiB floor. A small distinct original may be assessable against that conservative bound plus its own physical reservation and a fresh runner filesystem observation; an unidentified global reservation catalogue alone is not a new blanket prerequisite. However, the bound is not a universal measured reservation total. Unknown commitments cannot be zeroed, the two identical native free-space observations cannot be summed, and this metadata-only profile establishes no authoritative headroom. Any actual admission must account for relevant concurrent commitments and uncertainty through the existing collector's reviewed controls. Large-source budgets must not be squeezed into the diagnostic child timeout.
