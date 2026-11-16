# Product repository layout

[Repository standard 3.0.0](../standards/repository.md) and
[ADR 0014](../adr/0014-standalone-product.md) define this candidate boundary.

```text
src/                 installed product Python packages and resources
apps/                web/{src,assets,server}, retailer-extension
deploy/              product hosting and authentication adapters
integrations/        optional unmounted product components
contracts/           schemas and source/provenance contracts
config/              product configuration and source bindings
tools/               product data and development programs
scripts/             build and source-validation entrypoints
tests/               Python, web, edge, compatibility and authored fixtures
docs/                current product guides, standards and decisions
examples/            authored offline examples
```

Root package/build manifests, `AGENTS.md`, `README.md`, `repository-standard.json`,
editor/ignore configuration and conventional `.github/` and `.agents/` entries
remain product development entrypoints. This is one mixed application repository,
not a set of new independently versioned packages.

Dependencies, `.venv`, build output, caches, private data and exports are local
untracked state. No raw dataset or private account record belongs in Git.
Shared coordination and historical operational records are preserved outside the
tracked product tree; their original paths do not become clean-checkout
requirements. A source move does not move a live private consumer.

```sh
python3 scripts/check_repository.py --discover
python3 scripts/check_repository.py
python3 scripts/check_final_layout.py
```

The checks establish encoded layout and naming only. Verify installed resources,
complete builds and changed behavior separately. See [Python layout](python-layout.md),
[web layout](web-layout.md), [data tools](data-tool-layout.md) and
[the test layout](test-layout.md).
