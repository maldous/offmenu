# Selected offline provider contract checks

These four existing test files use authored, generated fixtures. They do not
acquire food records, open retained corpora, qualify real inputs, activate a
provider or publish anything. This profile is deliberately narrower than the
complete product test suite and is not production/provider acceptance.

## Product-local dependency closure

Use Python 3.12 and Node.js 24.22.2. The OpenPrices fixture invokes the pure
JavaScript normalizer through `node`; no npm dependency installation is needed
for this selected profile. Do not classify it as a Python-only check.

[`config/provider-contracts-requirements.lock`](../../config/provider-contracts-requirements.lock)
contains the same six exact Python versions selected by the earlier provider
profile at accepted source `a31bcbc1aee3fc13919bf95ba710f45ef115a7e9`.
The lock supplies version pins, not distribution hashes. An isolated executor
must verify the downloaded wheel identities and hashes against the official
package-index metadata, install the verified closure offline and run `pip check`.
Keep the resulting wheel manifest and command receipts outside the repository.
Do not silently replace pins or reuse the removed orchestration lock path.

For an ordinary private virtual environment, the selected dependency install is:

```sh
python3.12 -m venv .venv-provider
.venv-provider/bin/python -m pip install -r config/provider-contracts-requirements.lock
.venv-provider/bin/python -m pip check
```

Installation contacts the package index; the test phase must have network access
disabled by its executor. Merely setting an environment variable is not a
network-isolation boundary. No credentials, live API keys, provider accounts or
source-data paths are inputs to this profile.

## Exact commands

Run from the repository root with its real Git metadata. Set `PYTHONPATH=src`
and select the private environment's Python executable for each command:

```sh
PYTHONPATH=src .venv-provider/bin/python -m unittest discover -s tests -p test_pr136_provider_regressions.py -v
PYTHONPATH=src .venv-provider/bin/python -m unittest discover -s tests -p test_usda_product_contract.py -v
PYTHONPATH=src .venv-provider/bin/python -m unittest discover -s tests -p test_private_source_lookup_contract.py -v
PYTHONPATH=src .venv-provider/bin/python -m unittest discover -s tests -p test_openprices_cache_contract.py -v
```

The fixtures also import their adjacent `test_product_adapters.py` helper and
the selected product modules, schemas and policy evidence under `src/` and
`contracts/`. Retain those exact source inputs, not only the four top-level test
hashes. Python temporary files and generated SQLite/ZIP fixtures stay in the
executor's private temporary directory, not in held source-data locations.

The standalone repository-convention check is separate and needs only Python
stdlib plus Git:

```sh
python3 scripts/check_repository.py
```

Neither command group repeats or supersedes the accepted web build/layout
receipts. Bind any new execution to its exact branch, commit/tree, lock and
fixture/module inputs. A published profile or submitted job is not a passed
check. Keep live-provider, browser/device, rights and release qualification
explicitly separate. Historical delivery targets retain their historical
source applicability; they are not renamed as standalone product checks.
