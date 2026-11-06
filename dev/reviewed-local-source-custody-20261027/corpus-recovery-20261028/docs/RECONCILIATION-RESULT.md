# Actual retained-corpus reconciliation, 2026-10-28

No publication, source/data modification, raw-record export or semantic/global qualification rerun occurred.

## Evidence
- Initial actual inventory: Windmill run 01a18006-a398-b79c-4977-9cae7b11ae36; safe stdout retrieval 01a18006-f8b4-4a0e-95d7-89f922799b77.
- Reconciliation v1: 01a1800a-1499-d544-929c-794dfd6a24c3 completed normally but extractor returned unsafe_count_map. It incorrectly excluded legitimate mixed-case/slash recipe source IDs. This was an extractor defect, not a corpus failure. No partial changes were possible.
- Corrected reconciliation v2: 01a1800b-3f2e-e6dc-c685-cb48f07e695d; safe output retrieval 01a1800b-609e-fad4-dc22-7bf9778877c8. All proof/manifest/schema/contract/mapping/custody checks pass. Actual qualifier schema permits arbitrary string source IDs; output uses restricted safe identifiers or hash labels.
- Declared asset byte verification: 01a1800d-0be9-e74c-d700-8e56d04d7b88; safe output retrieval 01a1800d-2f47-4fbc-007b-31600ffcf6aa. 1661/1661 assets, 401128230 bytes, match exact manifest sizes and SHA256. No errors, mismatch, missing assets or truncation. Elapsed0.589s reported by probe; runner read-mode30s deadline, exit0 and child_tree_gone true.

## Meaning
Six present manifests match the historical six-package global proof exactly, as do their counts and admitted source records. Current repository schema/contract and source mapping digests match the proof. Under the existing assembler rules, these six packages cover95121records across17of22mapping sources; the core manifest legacy broad22,574,292 field is not that proof's coverage. Five sources accounting for22479269records remain uncovered: off5452981, usda-files4025777, prices317898, overture-food-places12681108, wikidata-food-businesses1505.

Food partial retains414regular files; places partial2407regular files. Neither has a final manifest. File counts are not packet-row counts. Current process quiescence was not inspected; historical custody receipt is not proof of current host processes.

No changed corpus bytes were found in the six complete manifests and their declared assets. This does not establish semantics anew, complete22source coverage, or public serving readiness. Extra non-manifest-listed files were counted but not content-hashed by the asset pass.

## Hash distinction
81b2918d8384ac3da63397263263c01340dc9b90031672d1fa4baab16aef8c1a is host scripts/windmill/job_runner.py self-hash. 06ac14241752df96dbec7bf9d7320cccb9634f576310be2ec613f9b74798c5da is deployed Windmill scripts/windmill/windmill_foo_jobs.py source hash. Both match recorded pins; they are different components, not a drift finding.
