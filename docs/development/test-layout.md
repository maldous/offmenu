# Product test layout

| Location | Scope | Command |
| --- | --- | --- |
| `tests/test_*.py` and Python subdirectories | Product packages and authored offline/source-contract fixtures | `python -m unittest discover -s tests -v` |
| `tests/web/*.test.mjs` | Browser models and Node-hosted product contracts | `npm test` |
| `tests/edge/*.test.mjs` | Worker runtime contracts | `npm run test:locale-edge` |
| `tests/compat/` | Explicit pinned compatibility replay | `node scripts/run-third-party-compatibility.mjs` |

For development, select actual affected test files:

```sh
npm run validate:dev -- tests/web/scanner.test.mjs --plan
npm run validate:dev -- tests/web/scanner.test.mjs
```

The plan option lists commands without executing tests. Use tests that exercise
the changed interface and its security/data-loss paths. Do not repeat unrelated
suites or create a passing substitute fixture for unavailable qualified data.

Some source-specific and compatibility tests require exact historical inputs,
Git objects or acceptance evidence. Their declared prerequisites and skips remain
explicit; a clean product build does not claim those external qualifications.
Frozen fixture identities are not rewritten when current physical paths change.

Verify packaging, generated outputs, imports and the complete build when their
boundaries change. Source/layout checks alone do not establish application or
production acceptance. Record exact source, commands, exit results, output hashes,
skips and limits with the reviewed candidate.
