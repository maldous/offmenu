# Python source and installed-package boundary

All three Python packages live under `src/`: `offmenu`, `offmenu_ciqual` and
`offmenu_norway`. Their public import names and the `offmenu` console command stay
unchanged. No root package copies, symlinks or import wrappers are required.

Setuptools discovers only `src/offmenu*`. The source distribution includes the
physical `src/` paths; wheels contain the ordinary import paths `offmenu/`,
`offmenu_ciqual/` and `offmenu_norway/`. Package HTML, schemas, binding catalogs
and source-adapter JSON contracts are declared package resources. Repository
configuration, tests, operations tools and private runtime data are not wheel
resources merely because development commands can access them.

Create the pinned Python 3.12 delivery environment and install the project:

```sh
python3 scripts/bootstrap_delivery.py
.venv-delivery/bin/python -m offmenu.delivery discover
.venv-delivery/bin/python -m unittest discover -s tests/delivery -v
```

The bootstrap installs the exact dependency/build lock, checks it, then installs
the current project editable with no dependency resolution or build isolation.
`--check` verifies the lock and refreshes that editable source binding without
network. A clone or moved checkout must install its own source binding before
running commands; a different checkout's editable installation imports that
other checkout. Select the intended interpreter and verify `offmenu.__file__`.
Do not compensate with a root package symlink.

For the broader Python suite, install its declared extras into the selected
project environment, then run the affected tests:

```sh
.venv-delivery/bin/python -m pip install --no-build-isolation -e '.[test]'
.venv-delivery/bin/python -m unittest discover -s tests -v
```

The test extra is distinct from collection dependencies and never selects a live
source or authorizes acquisition. Tests with frozen interpreter/parser identities
retain their explicit skip conditions. Historical evidence keeps its recorded
paths and hashes; a test harness resolves current physical source paths rather
than rewriting the evidence.

`offmenu.refresh.core.ROOT` denotes the importable package source root (`src/` in
a checkout, the installed package container in a wheel). Its separate
`REPOSITORY_ROOT` is used for checked-out tools and Git metadata. Logical package
provenance keys such as `offmenu/refresh/core.py` remain stable; physical tracked
source is `src/offmenu/refresh/core.py`. Repository-only metadata commands require
the selected checkout/configuration. Standalone package resource access must use
the installed package location, never assume the checkout is on `sys.path`.

Generated wheels, virtual environments, caches, source databases and private
checkpoints remain excluded from Git. The migration preserves existing private
runtime/data roots; it does not infer that ignored files can be deleted.

## Maintained parser routes and historical qualification

`offmenu.refresh.capabilities` retains its historical paths and Git object pins
unchanged. The separate `source_layout` module records explicit current physical
handler paths and measured Git blob identities under `offmenu-source-layout/2`.
Execution verifies those pins in both parent and isolated worker, including the
source-only loader that rejects unpinned/poisoned bytecode. New candidate receipts
record the layout version and actual parser blob. Dataset `ADMISSIONS` remains
empty. Authored offline workbook fixtures exercise the maintained routes; they
are not requalification of retained sources or permission to acquire data.

The ingredient vocabulary generator retains its original asset pin dictionary
as `HISTORICAL_PINS`; generation version 2 binds the relocated current assets and
changed JavaScript module import bytes explicitly. Old asset-selection keys are
rejected. Existing selected22/full-retained real-data qualifications remain stale
when their code fingerprint changes; tests assert that rejection before opening
source bodies. No old receipts, frozen fixture interiors or source qualification
hashes are rewritten to make a migration pass.
