# Reviewed repository knowledge baseline

This baseline retains small reviewed source contracts, historical design documents and paused-work records alongside code. Documentary custody does not establish current runtime, rights, dataset freshness or production acceptance.

Large generated inventories are excluded under the owner’s Foo-runner-only requirement. [Bounded artifact references](bulk-artifact-references.json) preserve their exact sizes, hashes and source pins. Foo transfer, storage location and retained-byte readback remain unverified. Local exact bytes were checked before exclusion; no local deletion is authorized by this record.

The excluded discovery inventory historically described 249 countries and 1,303 discovery sources. These are historical index counts, not fresh source acquisition or operational coverage, and the repository-only verifier does not revalidate them. The full 347-artifact disposition inventory and 1,318-row historical inventory are likewise not present.

Run `python3 scripts/verify-knowledge-baseline.py` for the bounded reference structure, restored design bytes and 49 paused-work records. Its output explicitly reports external inventory verification as unavailable. `--check-code-tree` cannot reproduce the old full disposition check without that excluded inventory and returns an incomplete result. Run `python3 scripts/verify-expanded-knowledge.py` for retained documents and requirement navigation; `--check-other-lane` additionally checks pinned copies in the product lane.

See [retained knowledge](knowledge/README.md), [paused work](paused-work.json) and [provenance](provenance.json). No preserved branch, raw dataset, credential or runtime resource is deleted or activated by this baseline.
