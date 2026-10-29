# Retained documentary knowledge

The 256 files under `sources/` are exact historical design/source-contract documents, not activated code or fresh source acceptance. [The catalogue](CATALOGUE.md) provides topic navigation. [The compact hash index](document-hashes.json) pins each copy to original bytes and source commit/path. [The requirements map](requirements-map.json) links 52 requirement IDs to these documents.

The full 1,318-row historical disposition inventory is excluded from GitHub as a bulk generated artifact. Its size/hash and unverified Foo custody are recorded in [bounded references](../bulk-artifact-references.json). The compact index checks selected copies only; it cannot establish completeness of that excluded inventory or lossless Foo retention. Original holds and historical wording remain in force.

`python3 scripts/verify-expanded-knowledge.py` checks all 256 selected files, exact lengths/Git blob hashes, requirement references, and local guide links. `--check-other-lane` also checks the 10 source documents retained through approved product packages. External full-inventory checks are explicitly unavailable, even when the bounded repository checks pass.
