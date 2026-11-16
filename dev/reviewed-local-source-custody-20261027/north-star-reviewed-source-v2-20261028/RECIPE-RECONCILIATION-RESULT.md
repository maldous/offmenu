# Actual recipe reconciliation — 2026-10-28 08:25 UTC

This is selected normalized-data and local consumer-query evidence, not application serving, culinary identity acceptance or automatic meal planning.

## Full core recipe assets

Manifest `c15005b224ae18c1e660837c6ac9fab88beb0b4d53ce34db6a5a87f12f6d919d`, all 51 `recipes/` packet assets and 25,135 packets were schema-validated and every SQLite resource/relationship/fact projection was checked against the exact source fields and citations. The existing index was opened read-only; streamed before/after hashes agree. Report SHA256 `9ab94d1566f9a3c784baea3621059a954736dd9b08899d718ebb6d7f5c38fbec`; index SHA256 `c2de1379038bfe8cae003c394d343fefb0282ffb0637f56e18f57053eb89e428`.

| Actual selected coverage | Count |
|---|---:|
| RecipeVariant resources | 24,879 |
| HistoricalRecipeCandidate resources | 256 |
| Ingredient mentions | 199,504 |
| Type/scope/status-qualified recipe → ingredient quantity joins | 198,791 |
| Unknown ingredient amounts, across selected recipe assets | 151,339 |
| Recorded zero ingredient amounts | 0 |
| Positive source yield assertions | 1,853 |
| Source recipe → step joins | 136,962 |
| Candidate ingredient identity links | 37,241 |
| Reviewed exact ingredient identity links | 0 |
| Step → ingredient links | 0 |
| Recipe nutrient-observation edges | 0 |
| Explicit automatic-planning=false assertions | 25,135 |
| Automatic-planning=true / served-app queries | 0 / 0 |

Historical candidates are not silently counted as RecipeVariant consumer joins. These counts do not prove that the positive yields have compatible ingredient quantities, identities or composition inputs. They do establish that the earlier small-package zero-known-yield result must not be generalized to this larger corpus.

## Exact native-input fidelity and additive repairs

- **42 recipe-expansion records:** all selected normalized quantities preserve the manifest-listed native values. There are 64 canonical numeric amounts, 112 additional source numeric amounts with unresolved canonical units, and 90 source-unknown amounts. The common builder omitted 42 explicit unknown yields and 266 scaling fields. Independently reviewed restoration produced exactly those **308 candidate assertions**, preserving unknown yields and copied scaling codes without changing the base package.
- **5 historical records:** 51 source and canonical amounts are already unknown in the native normalized input, all 5 yields are unknown, and selected fields are faithfully retained. No missing field restoration was needed. This is not proof that earlier OCR extraction recovered every source measurement.
- Expansion sidecar manifest SHA256: `e10deb8b50cddce89b15a29f82aa664b71b87d1fdff56a901826aa793a9e53e5`. Its sole 46,299-byte payload is `recipe-context.jsonl.gz`, SHA256 `b8ba2924b38193f961608a7d0f6f73ee8cf3909e5742aa6d0c99d431e5001a0a`.

## Recovery and remaining dependencies

The first full-core query pass built its index but attempted an unbounded whole-index RAM hash; the resource supervisor terminated it. Recovery changed hashing to 1 MiB chunks, reopened the old index read-only, and reverified every selected source projection and table extent rather than copying the 1.36 GB index or assuming the partial file was sufficient proof. The final durable job succeeded in 59 seconds with 512 MiB memory and 64 MiB new-output reservations.

The exact remaining dependencies are source-explicit or reviewed ingredient identity, usable quantities/units and yield/preparation where absent, and explicit step-ingredient usage. Text matching, recipe names, a numeric yield or a larger graph relation count cannot supply these admissions. Original datasets, rights, candidate statuses and planning holds remain unchanged. Full North Star completion and live-app serving are not claimed.
