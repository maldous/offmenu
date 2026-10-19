# Separate installed fetch and parse commands

After installing the reviewed successor with the existing `--install COMMIT TREE`
setup, the private owner installation exposes these commands from any directory:

- `~/offmenu-global-collection/fetch` selects `--mode user --stage fetch`.
- `~/offmenu-global-collection/parse` selects `--mode user --stage parse`.
- `~/offmenu-global-collection/run` is a compatibility alias that executes `fetch`.

The launcher itself also defaults to fetch when invoked without arguments. No
installed command invokes the old combined collection pass. Fetch and parse are
separate collector stages; installing these commands does not execute either.
The collector owns stage behavior, result validation, and authorization. Stage
selection does not expand source/002/runtime authority, permissions, budgets,
worker limits, or access. Parse must be requested explicitly.

Publication-only recovery retains its existing flag. Use `fetch --publish-only`
or `parse --publish-only` to forward the matching stage and `--publish-only` to
the collector. `run --publish-only` remains valid and selects fetch publication
recovery. The collector must keep this route publication-only, without entering
fetch or parse work. Unknown stages and attempts to override a wrapper's stage
are rejected before collection.

## Upgrade and interruption behavior

The setup accepts the exact reviewed legacy, versioned, and c74 predecessor run
wrappers and their existing source/pin maps. Their source directories and pin
files remain unchanged. The old `wrapper_bytes(source)` representation is kept
byte-for-byte for predecessor verification. Existing fetch/parse command files
must be absent or exactly match the new selected source; unknown commands and
symlinks are rejected before source fetching.

Setup verifies the selected source and writes its immutable pin first. It then
installs fetch and parse commands with atomic, owner-only replacements, rechecks
both, and switches run to its fetch alias last. If an earlier step fails, the
previous run command remains intact. A partially installed exact fetch/parse
pair can be completed by repeating the same reviewed setup. Changed command
pointers are never silently overwritten. No data, custody records, receipts,
source claims, or historical failure records move during setup.

GitHub credentials remain inherited environment values, never argv or stored
files. Source verification, clean-environment rules, timeout bounds, and the
normal-user requirement remain unchanged.

## Composition requirement

This launcher patch deliberately does not refresh dependency hashes. The parent
must compose it with the separately reviewed collector stage implementation,
refresh the successor dependency pins (including this document and the new
stage tests), and verify the full installed bundle before publication or setup.
The launcher patch alone is not a runnable staged collection release.

## Stage-aware terminal observations

After validating arguments, the collector calls
`terminal.execution_stage('fetch')` or `terminal.execution_stage('parse')`.
Fetch may then use `terminal.stage('verifying')`; parse retains the preparing
phase. The reporter accepts only those two execution-stage labels.

Fetch calls the worker group verification and omits preparation-readiness,
extraction-held, and preparation-storage labels. Old or unselected parsing
outcomes are not presented as fetch failures. Verified original records remain
explicitly alias-inclusive, and network body bytes remain separate from exact
verified retained payload counts and bytes.

Parse displays acquisition job counts explicitly, with zero supplied by the
collector when no acquisition is scheduled. The display never hardcodes zero
or hides a contradictory observation. It shows local custody verified payload
counts/bytes separately from network bytes and preparation storage. Verified
payload bytes do not claim total local I/O, including diagnostic scans.
Worker activity still uses actual worker entry/exit markers, not queued futures.
These labels neither authorize a stage nor alter report schemas or counters.
