# Test layout

The repository uses one `tests/` root, with runtime-specific suites:

| Path | Purpose | Command |
| --- | --- | --- |
| `tests/test_*.py` and existing Python subdirectories | Python package and offline-data tests | `python3 -m unittest discover -s tests -v` |
| `tests/web/*.test.mjs` | Browser models and Node-hosted contracts | `npm test` |
| `tests/edge/*.test.mjs` | Worker runtime contracts | `npm run test:locale-edge` |
| `tests/compat/pinned-schema-runtime.test.mjs` | Generated, pinned historical compatibility fixture | `node scripts/run-third-party-compatibility.mjs` |

For a bounded development change, use explicit affected paths:

```sh
npm run validate:dev -- tests/web/scanner.test.mjs --plan
npm run validate:dev -- tests/web/scanner.test.mjs
```

The 2026-10-29 migration relocated 191 tracked files from `tests-web/`,
`tests-edge/`, and `tests-compat/`. Top-level test imports and project-root
resolution were adjusted by one directory. The 40 fixture files with no project-root imports retain their exact bytes.
The shared photo fixture import advances one directory, and the compatibility
loader translates historical fixture paths without modifying its pinned manifest. No application source, runtime data,
provider setting, dependency version, or GitHub Actions trigger changed.

Old paths in dated handoffs, source-custody manifests, review records, and
consolidated evidence describe the tree at their recorded revision. Keep them
unchanged. The third-party compatibility runner intentionally selects old
`tests-web/` and `tests-edge/` paths from immutable historical snapshots; it
uses today's `tests/compat/` harness for schema replay. Translate old test
commands to `tests/web/` or `tests/edge/` when working on the current checkout.

Some retained tests require historical Git objects, installed project
dependencies, or external acceptance evidence. A layout check does not certify
the unfinished scanner/UI work or qualify a production release.

Verify the migration against its immutable base without touching the index:

```sh
python3 scripts/check_test_layout.py
```

This checks relocated file presence, previously tracked literal relative-file
dependencies, pinned fixture bytes, and top-level Node syntax. It is separate
from behavioral tests and does not claim a full application pass.
