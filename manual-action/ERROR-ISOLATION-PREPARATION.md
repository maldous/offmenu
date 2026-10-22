# Error isolation and expected-skip preparation — 2026-10-22

Base: `af99cdfb4bac3bce9f4badae34333921a0074a76`. Cloud-only generated-fixture preparation; not installed on Foo and not an instruction to replace running code.

## Concrete changes

1. Retained `unrecognized_recipe_or_lead_only` and `not_a_supported_recipe_record` outcomes now count as **skipped**, not malformed/error rows. They remain unimported and have an explicit fixed-code `unsupported_reason_counts` source-summary histogram. Missing ingredient granularity, malformed recipe fields, unsupported whole-file formats, and access failures retain their existing error treatment. No eligibility, licensing, acquisition, or hold changes.
2. Expected skips reserve the old negative adapter-callback ordinal in memory. That preserves later real-error identity when resuming a partially processed source whose earlier execution recorded leads as errors. No per-lead SQLite error write, source fingerprint/stat, or coordinator event is performed.
3. An invalid JSON payload in a retained SQLite row now rejects that row only; later rows survive. A duplicate-key/nonfinite JSON **array member with established framing** is likewise rejected independently, with original later-member pointers intact. Broken framing still terminates the source; bytes are never guessed/repaired. Invalid wrapper metadata is not silently ignored.
4. Current callback telemetry recognizes the already-reviewed finite acquired recipe/menu reason vocabulary and the `MalformedAcquiredRecipe` / `UnsupportedJavaScript` classes. JSON/Unicode/archive exceptions receive fixed normalized reason codes, never exception text. Historical stored class/reason data is not retrospectively rewritten. Histograms using newly introduced reasons are bounded to 2,048 encoded bytes: most frequent reasons remain exact and overflow counts enter `other_or_unavailable`; full finite observations remain in private details. Legacy-only telemetry retains its exact existing projection for old receipt recovery.

## Evidence and limits

The actual 09:49:33 checkpoint reported 242,380 current-run `unrecognized_recipe_or_lead_only` callbacks (29,024 at 09:46:28), while recipe writes remained 198,557. This supports fixing false-error/SQLite overhead now. It does not establish raw source contents. The older 392,001 `UnsupportedSource` class total was a different, historical all-retained-versions metric; it must not be described as newly malformed recipes.

A generated 5,000-lead + one-valid-recipe comparison produced:

| Measure | Base | Candidate |
|---|---:|---:|
| Written recipes | 1 | 1 |
| Visible skipped leads | 5,000 | 5,000 |
| Durable error rows | 5,000 | 0 |
| Source fingerprint calls | 5,003 | 3 |
| One local fixture elapsed seconds | 2.533128 | 0.144995 |

Timing is a local synthetic observation, **not** a throughput forecast for Foo or a proof of utilization of its 24 CPUs / 64 GB RAM. Current collapsed acquired error counts do not justify inventing source-field corrections. Improved exact reasons enable a subsequent evidence-backed correction if needed.

## Cursor/version compatibility

All adapter versions and staging schema versions remain unchanged. Valid supported projections, record IDs, and previously accepted prefixes are unchanged. Newly reachable rows occur after a previously terminal stream error, so a partial source's emitted-record cursor still denotes the same accepted prefix. Tests cover resumed array/SQLite tails, output order/pointers, exact source-version reuse, and legacy callback ordinal stability.

Completed unchanged source versions, including `complete_with_errors`, are not replayed or rewritten. Existing historical errors are not deleted. A formerly terminal stream error remains historical evidence even if a future resume records a more precise callback for that rejected input. This patch does not pretend to reconstruct physical-record identity absent from the legacy error schema.

## Verification

129 generated-fixture focused tests pass, zero skips/failures, covering:

- new expected-skip/isolation/cursor/privacy regressions;
- existing error telemetry and strict 64 KiB receipt boundary;
- retained recipes and both acquired recipe/menu adapters;
- ingestion engine/store, budget stop, and final-ingest integration.

No raw datasets, Foo reads/writes, network acquisition, credential changes, remote mutations, complete corpus benchmark, or broad full-suite claim.

A single focused command from the repository root:

```sh
PYTHONPATH=manual-action:manual-action/tests python3 -B -m unittest -v test_ingest_error_isolation test_ingest_errors test_ingest_recipes test_ingest_acquired_recipes test_ingest_acquired_menus test_ingest_engine test_ingest_budget_stop test_final_ingest_integration
```

## Composition boundaries

The live-totals patch has disjoint `ingest_store.py` / `ingest_engine.py` hunks. Preserve `reserve_adapter_error_slot`, `_active_error_identity`, and `IngestContext.report_skip` when composing.

The throughput patch refactors `iter_records`. Its `event == 'unsupported'` branch must call `_unsupported_record(context, source, exc, stats)` **once**, not additionally increment `skipped` or call `report_error`. Keep ordered callback events and deduplication, the parser-recovery hunks, and the separate summary histogram. Rerun the focused tests against the composed source; independent patch passes do not prove integration.

Promotion/installation remains after the active run exits, with existing checkout/state/receipt reconciliation preserved. Do not reset, switch, or replace code in the live checkout.
