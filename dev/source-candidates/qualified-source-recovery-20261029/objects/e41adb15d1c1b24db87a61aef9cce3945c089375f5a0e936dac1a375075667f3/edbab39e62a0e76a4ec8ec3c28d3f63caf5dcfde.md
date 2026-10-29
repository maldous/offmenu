# Independent Worker53 review of Worker62 LEI adapter

Candidate b2091af737445519d98c1d30eb6e316ec95353c5. Verdict: changes required for namespace-preserving field mapping; actual-source qualification blocked.

Medium correctness finding: fields() removes namespace URI from every child tag. Mutating only the existing synthetic LegalAddress Country into urn:not-gleif retains the same /Entity/LegalAddress/Country=AU mapped fact. Original namespace is not represented in that fact. Correct by preserving namespace/QName and rejecting or explicitly segregating foreign fields; add collision regression. No candidate code was edited.

Three original synthetic tests pass. Independent mutations confirm distinct EntityStatus versus RegistrationStatus, legal versus HQ addresses, revision-sensitive observation identity and no size/origin/independence assertions. The namespace mutation reproduces the finding. All checks are synthetic, not real source evidence.

PDF03 pp3–8 require source identity/dated evidence and distinct ownership roles. LEI-CDF Level1 cannot prove brand, manufacturer, product origin, size or independence. Accounting parents require independently pinned RR-CDF with temporal qualifiers and reporting exceptions; empty relationships are unknown. Serialized XML hash is explicitly not an original byte-slice hash.

Worker36 receipt supplies CC0 metadata but zero actual samples and no exact release. Caller rights/input hash shapes do not verify rights custody. Exact missing artifacts are listed in JSON. Whole105 and recipe production STOP remain. Prior 8d census and 6bf recipe bodies retain their separate scope and are not LEI proof. No source network, new fixture, merge, admission or production activity.
