# North Star additive delivery — local processing complete, 2026-10-28 11:47 UTC

The existing Product North Star definition and selected package contract remain the authority. This lane adds exact source-bound relational/context candidates; it does not substitute eight-package integrity for full Product North Star semantics.

## Frozen local outputs

| Scope | Actual coverage | Final SHA256 |
|---|---|---|
| Bulk structural/context | 9,796,656 packets scanned; 46,795,344 quantity/metadata contexts; 2,915,727 resolved product→profile edges | `83773291ac70931a110f60e872ae47a2bd470b5f397c709195dcf016c0bf0694` |
| Whole-bulk namespace SQL | 2,980,298 source identifier→product→profile→context keys: 1,055,792 literal barcode and 1,924,506 USDA-FDC. 400,164 ambiguous barcode keys not merged. | `1fba08ba7c859afaa355530d74b4c0dc9ec6c35a0212ab8c871bf3cf68e41ef4` |
| National food/metric | 36,737 foods; 587,792 exact food→profile→metric contexts, including unknown values | `71fbf6f68e050989b95c4c602ee90775e2eac83a53ae66790f3b915d091af29d` |
| Expansion recipe repair | All 42 selected native recipes; 308 omitted yield/scaling fields copied as candidates, including unknown yields | `e10deb8b50cddce89b15a29f82aa664b71b87d1fdff56a901826aa793a9e53e5` |
| Core recipe query proof | All 25,135 selected packets; 198,791 typed ingredient-quantity joins, 1,853 positive source yields, 136,962 typed RecipeVariant→step joins | `9ab94d1566f9a3c784baea3621059a954736dd9b08899d718ebb6d7f5c38fbec` |
| Per-nutrient basis restoration | All 9,797 normalized assets / 9,796,656 packets and locators; 2,924,709 native profiles matched; 46,795,344 candidate basis targets; unmatched profiles and source-projection mismatches both zero | `3520dff24e7b96635fd3d8f8cfa60664d03d5bd65709b547059cee10b306e1a9` |
| Actual value-returning caller | 64 source-key queries: OFF barcode22, USDA-FDC41, USDA barcode1; 64 product/profile occurrences, 1,024 nutrient-context and 1,024 basis-target occurrences, 128 citation occurrences | `921fa2113c67b05213786dbebfb10e350e2716a45a325b977f44c18e7bacf61b` |

The caller preserved **400 unknown scalar quantities versus 124 exact zeros**. Full responses stayed inside the authorized worker; exported evidence contains only aggregates and pins. These finite occurrences are not distinct-food counts or a test of every connected key. Whole-index namespace SQL remains separately identified.

Basis public payload: 9,797 `basis-restorations.jsonl.gz` files, 7,028,472,464 bytes. Native projection SQLite, matched/locator SQLite, local locator rows and shard receipts are explicitly not public payload. The copied basis fields are retained source literals—not independently verified upstream preparation classifications or accepted canonical preparation states. Profile basis never substitutes for per-nutrient evidence.

## Execution and review integrity

- Reviewed basis runner completed at 11:23:07 UTC; exact command/terminal independently read, exit0 and child tree gone. Final source/index/shard counts reconcile; immutable originals unchanged.
- The first finite caller attempt reached its 600-second deadline at an inefficient SQL edge lookup. A narrow independently reviewed redundant subject equality enabled the existing subject index. No schema/index/data mutation was made. Seventeen caller/probe tests plus two independent multi-edge/full-object parity tests passed; the corrected actual run completed in 15.824 seconds, exit0 and tree gone.
- Final namespace-specific review binds source/normalized manifests, schema/contract, all implementation pins, public inventory, full matched-source SQL and the finite actual caller report. Candidate, source-qualification, confidence-not-calibrated and no-admission flags remain unchanged.

## Delivery and source custody

The existing publisher owns exact actually-served base-release binding and separate immutable derived namespaces. Bulk, national and recipe consumer receipts are staged. The basis receipt is being create-only staged at `basis-restoration-v1/reviewed-consumer-proof.json`; exact staging confirmation is recorded in `OWNER-CHECKPOINT.json`, not assumed by this snapshot. Basis namespace: `/common-data/derived-releases/north-star-basis-restoration-v1-20261028/`. No source identity promotion, alias replacement or automatic Cloudflare/application activation occurs.

Source V2 is published at private commit `a759cb1df44df4108dbd0cdc75f4221ecfd1d255`; V3 at `5957b94449fabfaa2f34f6f8e23c6474bc871012`. Later reviewed measurement/query correction and final actual receipts will be frozen as a distinct source-only follow-on packet, excluding datasets, raw rows, indices, credentials and runtime request payloads.

## Required semantic dependencies still open

Canonical cross-source product/GTIN identity, product formulation→culinary ingredient identity, source-explicit or reviewed step→ingredient usage, and compatible recipe quantities/units/yield/preparation/nutrient definitions remain absent or unaccepted in the selected scopes. All selected recipe sets have zero accepted recipe-nutrition edges. Core canonical-unknown amounts are not all proven source-unknown: only the selected 42+5 native recipe records received an exact prior-normalized fidelity comparison here.

These precise missing inputs do not block independent candidate publication, but they do prevent claiming full North Star semantics, accepted recipe nutrition, automatic planning or app serving. Full North Star complete=false; accepted identity joins=0; served application queries=0.
