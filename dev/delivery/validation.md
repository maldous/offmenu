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
- The new adapter is tested locally. The existing deployed Windmill SSH bridge
  subsequently executed the live standard check successfully (receipt below);
  no replacement bridge installation was necessary. Existing runtime files remain preserved.
- Symphony workflow is bound to the actual OffMenu Linear project/issue IDs
  and parses against the installed bundle, but admission remains disabled.
  The local process lacks `OFFMENU_LINEAR_API_KEY` and `LINEAR_API_KEY`.
  MCP authentication has not been transferred. No eligible model command or
  workpad admission was invented, and no CIX service was changed.

The local graph demonstration uses a generated private task pinned to the source
commit, pauses after standards, resumes from SQLite in another process, verifies
checks and declared hashes, and reenters without replay. Its receipt remains
under ignored `.delivery/`; publish only sanitized hashes/status as evidence.

## Second implementation checkpoint

Standard 1.1.0 removes the manual-action root by grouping 42 tools/schemas/tests
under tools/source-processing and nine renamed guides under docs/source-processing.
384 Python and10 JavaScript scenario tests pass. A dedicated verifier checks51
relocated files,35 parsed Python modules, six unchanged native fixtures and two
schema consumer references. One existing filesystem timestamp test initially
flaked, then passed unchanged in the final full tool suite and original baseline.

A fresh ignored project-local .venv-delivery was installed from41 pinned packages,
verified for exact installed versions and pip dependency consistency, then passed
all28 delivery tests. scripts/bootstrap_delivery.py is the supported bootstrap.

Existing Windmill route: u/admin/foo_jobs_20261027 in workspace offmenu,
logical job offmenu-standardization-20261029-v2. Windmill run
01a18681-71f9-788b-a64d-2f56da95a645 executed the standard check through
the approved SSH jail /offmenu: admitted=true, succeeded, exit0,
child_tree_gone=true, reconcile_required=false. Runner SHA256
2ae57cc8edc66d9b56f43ad26dd8871fda155d23e50563988d3b0cac89d21674.
The preceding same-ID status established not_found before submission.

An isolated transient systemd user process injected the existing tracker
credential using LoadCredential and verified read access to the exact OffMenu
project UUID. No credential was printed or persisted, and CIX was unchanged.

## Live graph execution through Windmill

The developer-private checkpoint directory correctly denied the service actor's
first graph bootstrap. A source clone initially failed Git's ownership guard;
client-only -c settings do not propagate through local clone's server boundary.
No checkpoint or coding work was started by those failures. The final selected
workspace uses an explicit narrowly trusted upload-pack command, a service-owned
checkout and its private graph state. No permissions or global Git trust changed.

Windmill prepare/pause run:01a1868c-d9d5-1845-dbc2-953de6366d6c.
Resume/reentry run:01a1868d-445c-2bdd-ba78-786f8e3049df. Both admitted,
succeeded, exit0, child_tree_gone=true, reconcile_required=false.
Graph task windmill-layout-20261029-v2 accepted source
1cc9011a68f0a865c29dfef46dbf123ee9ee783e under standard1.1.0,
verified four declared outputs, and recorded exactly one check start/attempt1.
Acceptance receipt SHA256:
8aaaebdf3f18d0831966bc0101322b38051c49e748603f204af53cfc7d7ab908.
The private receipt remains in the approved runtime mount.

## Native Symphony coding output

The first selected attempt failed before thread/start because inherited Codex
home configuration blocked initialize. An exact-command initialize-only A/B
reproduced the failure and proved isolated OffMenu configuration initializes.
The fix references the existing authentication path through a private ephemeral
symlink, without reading/copying credentials or inheriting workstation plugins.

The second session passed thread/start and produced tests/delivery/test_cli.py:
11 real offline CLI lifecycle tests. Root review and an independent rerun passed
all11 in7.1seconds. The finite180-second supervisor deadline stopped the native
continuation, so the process receipt correctly stayed unaccepted. Source output
acceptance is separate and was established by review and behavioral tests.
One-turn admission is now selected to prevent redundant continuation.

## Completed one-turn native session

The OffMenu-only v3 session admitted exactly UIF-90 on source
7283d8227ae724f1cb376ed30750faa0a3ed43ab, requestedgpt-6.1-sol/medium
through the verified existing Pro account, and ended normal_turn_completed.
The after-run marker was observed before the deadline; finite_deadline_or_interrupt
wasfalse. The wrapper deliberately stopped its owned native polling process
after the task ended, and the transient unit finished success. No legacy service
was started. Its process receipt still marks accepted_delivery=false because
source review belongs to the integration writer.

The reviewed output adds five CLI regressions: successful safe retry without
replay, timeout plus explicit reconciliation/retry, writer contention, source
drift across process resume, and output verification at final acceptance.
Combined with the preceding eleven, the CLI suite now has16 tests.

Sanitized native process receipt SHA256: 987677e7df3c0fe9c731beca171542df94b3c806cab94cb3cd9ce52b6dd5568b.

## Independent review corrections

Review of fdadf958 identified three correctness defects: substituted output
bytes could reuse a successful check, same-HEAD branch switches were not bound,
and check IDs could collide with control receipts. The fixes record actual
post-command output state and source evidence, bind the exact branch, and reject
reserved names/path variants before writing controls. Output drift blocks by
default; only the original explicit safe-retry declarations and remaining budgets
allow graph reexecution. Generated outputs and known failed-producer recovery
remain supported. Historical bindings lacking this evidence are not auto-upgraded.

63 selected tests pass locally, including eight focused graph regressions and
three additional CLI subprocess regressions. Scope remains the delivery engine,
CLI, their tests and documentation; no legacy worker or application work resumed.
A separate sanitized verification receipt retains the subsequent Windmill
source identity, supervisor result and actual test summary for external review.
