# Focused independent merge review — 2026-10-28

Approved exact artifacts:
- helper: 2bac27e64a4631ad9e82856eb51362c6d829191a49b540a4fe3983e71669db3b
- wrapper: 9fea04504b33581140a6c05c3a23a17681047208ad11313ae1e647f9993cd816
- migration: a79e3d7c41b7a20e06b9d2a5283c431206d0921d7c7d7c16b3b6f0e1b5a7bb87
- adapter: a1b5c9902fab95282061672392bd55e0af4c2ac98e23ce6231fb1704126143fe

Independently ran 47 qualifier tests (9.543s) and 11 adapter tests (0.007s), all passed. Includes original validator positives/rejections, exact all-eight small-fixture graph/evidence equivalence excluding elapsed time, mismatching text/citation and all ID-kind conflicts, equal duplicates causing no UPDATE, unrelated integrity error propagation, mid-merge SQL interruption atomic rollback, actual committed-v2-asset migration and continuation, global unresolved-reference/wrong-translation rejection, budget/cancellation/init failure and source pin custody. Tests are local fixtures, not a stress test or actual Foo runtime certification.

Runtime delta uses connection-local TEMP triggers explicitly bound to main texts/citations. UPSERT does nothing for identical identity/canonical hashes and enters a trigger-aborted UPDATE only on conflict. Direct IDs INSERT preserves uniqueness and runs diagnostic join only after PRIMARYKEY failure. No durable schema changes or graph row reinterpretation. The entire shard and checkpoint remain one parent transaction, and final global scans remain mandatory.

Migration accepts only exact prior wrapper62e1/helper2068 and requires explicit exact new target hashes. Prior/next provenance and pins commit in one FULL SQLite transaction; progress and all graph rows stay intact. Adapter changes only fixed v3 path and wrapper pin. Deploy only after the active v2 proof reaches its clean natural checkpoint and descendants are gone; no live migration or job interruption performed by reviewer. No actual speedup claim follows from this correctness approval.
