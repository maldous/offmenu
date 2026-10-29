# Validation scope — 2026-10-29

Base: `366c3710eeb9f732197250b217d412cd9e3b5d7e` on `develop`, freshly
verified against origin. Integration branch:
`feature/langgraph-delivery-standardization`. Existing workers and hourly
OffMenu automation remain suspended. No Actions, deployments or model calls
were made by these checks.

Passed:

- 28 delivery/standards/worker-adapter tests, including restart recovery,
  no duplicate execution, source/revision drift, bounded retry/cancellation,
  output hash verification, 1 MiB log cap and writer admission.
- 32 focused migrated browser/compatibility tests, including actual local WASM
  barcode decoding and photo-metadata behavior.
- Migration verifier: 191 files relocated, 430 literal file dependencies
  resolve, 40 unchanged fixtures, 150 modules parse, zero issues.
- Repository naming/layout check, with 137 explicit historic naming exceptions.
- Installed Symphony bundle's native workflow/config parsers in isolation.

Commands:

```sh
python -m unittest discover -s tests/delivery -v
python -m offmenu.delivery check
python3 scripts/check_test_layout.py
node --test --test-isolation=none tests/web/scanner.test.mjs tests/web/pinned-third-party-compatibility.test.mjs tests/web/services-config-check.test.mjs tests/web/off-photo-metadata-focused.test.mjs
```

The first two commands require the pinned delivery environment for graph tests.

Not passed or not performed:

- Broad Node suites stalled and were terminated with exit 130. No test jobs
  remain pending. This is not a full-suite success claim.
- Existing missing `better-auth` dependency blocks auth suites. No unrelated
  dependency change was bundled with the migration.
- Frozen scanner/UI and other application branch work remains unqualified.
  Local WASM tests do not establish scanner UI acceptance.
- Windmill adapter is tested locally; no live installation or job was claimed.
  The connected Windmill workspace was read as `offmenu`; the connection is
  advertised as read-only. Existing host runtime files remain preserved.
- Symphony workflow is bound to the actual OffMenu Linear project/issue IDs
  and parses against the installed bundle, but admission remains disabled.
  The local process lacks `OFFMENU_LINEAR_API_KEY` and `LINEAR_API_KEY`.
  MCP authentication has not been transferred. No eligible model command or
  workpad admission was invented, and no CIX service was changed.

The local graph demonstration uses a generated private task pinned to the source
commit, pauses after standards, resumes from SQLite in another process, verifies
checks and declared hashes, and reenters without replay. Its receipt remains
under ignored `.delivery/`; publish only sanitized hashes/status as evidence.
