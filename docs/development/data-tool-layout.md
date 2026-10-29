# Data and operations tools

Repository commands are grouped by responsibility. Importable application code
lives in the installed `src/` packages. Python command filenames use snake_case;
command directories use kebab-case like the other repository areas.

| Area | Maintained commands |
| --- | --- |
| `tools/data-processing/` | Acquisition adapters, normalization, qualification, packaging and offline evidence checks; specialized subgroups retain their boundaries. |
| `tools/corpus/` | Corpus policy and curation helpers. |
| `tools/source-processing/completed-observation-query/` | Inactive read-only adapter and generated-fixture checks for completed observations. |
| `tools/operations/` | Runner setup, dispatch, readiness, ledger and selected-dataset grant commands. |
| `scripts/` | Small developer bootstrap and layout-check entrypoints. |

Use the repository's pinned delivery Python environment after bootstrapping it;
commands import the installed packages rather than injecting a legacy repository
root into Python's import path. For example, from the repository root:

```sh
.venv-delivery/bin/python -B -m unittest discover \
  -s tools/source-processing/completed-observation-query \
  -p 'test_query_normalization.py'
.venv-delivery/bin/python -B tools/data-processing/run_ciqual_synthetic.py --help
.venv-delivery/bin/python -B tools/operations/dispatch_foo_job.py --help
```

Moving a command does not authorize its execution. Acquisition, publication,
runner administration and dataset grants retain their explicit admission and
source-use conditions. Historical measurement reruns remain disabled. Historical
commit references keep their original paths; current consumers use the migrated
paths. Exact implementation hashes in current grant dependencies are measured
from their current bytes, while historical evidence and dataset locks remain
unchanged.

The held files under `scripts/windmill/` are private live bridge dependencies.
They are not part of this tracked-source migration and must remain where their
existing consumers expect them until a separately verified runtime transition.
