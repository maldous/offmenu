# Product data and development tools

Importable product code lives in the installed `src/` packages. Repository
programs are grouped by responsibility:

| Area | Purpose |
| --- | --- |
| `tools/data-processing/` | Source adapters, normalization, qualification and offline evidence checks. |
| `tools/corpus/` | Product corpus policy and curation helpers. |
| `tools/source-processing/` | Bounded source-processing interfaces and authored fixture checks. |
| `scripts/` | Product builds, generated-output and repository checks. |

Use this checkout's ordinary `.venv` with the declared dependencies. Do not
inject another checkout into `PYTHONPATH`, create package symlinks or depend on
an unrelated host directory. For example:

```sh
python -B tools/data-processing/run_ciqual_synthetic.py --help
```

A tool's presence or relocation does not authorize its real inputs or effects.
Acquisition, export, publication and source-specific processing keep their
licence, consent, audience and exact-input requirements. Authored fixtures are
not real-source acceptance. Historical source identities are provenance, not
filesystem paths that a clean checkout must provide.
