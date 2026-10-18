# Local waste report CLI (Owner03)

Run with Node.js (verified with 24.16.0); no install, network, database, browser or credentials required. The existing `analyzeWaste` helper remains unchanged. This utility reads caller-prepared, already-authorized synthetic/private snapshots; it does not authenticate the supplied account or obtain consent.

```sh
node scripts/waste-report-owner03.mjs --account synthetic-account --input snapshot.json
node scripts/waste-report-owner03.mjs --account synthetic-account --input snapshot.json --json
```

Without `--input`, or with `--input -`, reads stdin. `--help` prints usage. Input must be a JSON array, at most 2 MiB and 1000 records. Unknown/repeated flags, absent account, malformed input, cross-account rows, helper errors and aggregate overflow exit 1 with no partial stdout. JSON mode reports `{error:"WASTE_REPORT_FAILED",message:...}` on stderr; successful reports exit 0.

Synthetic input example:

```json
[{"accountId":"synthetic-account","receiptId":"r1","sourceId":"stock1","quantity":125,"unit":"g","measured":true,"costSnapshot":{"sourceId":"stock1","quantity":500,"unit":"g","amount":8,"currency":"AUD"}}]
```

This produces 125 g and AUD 2 from the supplied matching snapshot. It is not a current price or a receipt capture/import path. Input is the helper's owner-adapted record array, not an app profile or raw `wasteObservations` array. Receipt/source IDs must already exist; this utility never assigns or repairs them.

JSON output schema `offmenu-waste-report/1` includes `accountId`, helper `records`, `quantities`, `values`, `coverage` and `suggestions`. Human mode renders those same groups. Quantities remain separate by exact unit; values remain separate by exact currency. No conversions, exchange rates, total across unlike units/currencies, inferred prices or missing-value substitutions occur. Empty groups mean no usable observations, not measured zero. The existing positive-only helper treats explicit zero as unaggregated/unknown coverage; it is not displayed as a zero measured total. Null/invalid/unmeasured quantities and absent/incompatible cost snapshots remain unknown in helper output. Values retain JavaScript numeric precision; human output does not round them into a financial guarantee.

Smaller-pack prompts are only the helper's existing `oversized-pack` / caller-supplied season / compatible recorded pack options suggestions. They grant no purchasing, safety or stock authority. All strings in human output are quoted/escaped, including untrusted terminal control characters. No input/output files are written by the CLI; stdout/stderr are its only outputs. File-reading does not modify input bytes. The byte cap applies to the full source, including whitespace; rejection is not a partial report.

## Portable closure and verification

Preserve relative paths for `scripts/waste-report-owner03.mjs`, `public/waste-analysis-model.js` and root `package.json` (ES module mode). Only Node built-ins and that helper are used; declared repository dependencies do not need installation. Documentation may accompany the closure. A focused test copies only these three files into a temporary folder with no node_modules and verifies execution and unchanged input bytes.

```sh
node --test tests-web/waste-report-owner03.test.mjs
```

Five groups exercise real child-process invocation, unit/currency separation and cost ratios, unknown/zero coverage, suggestion eligibility, human rendering, malformed/unauthorized input, flag/record/byte/overflow limits and portability. Synthetic fixtures are inline in the owned test. No app, cloud, generated locale, receipt integration, shared state, production or source-data changes are included. Existing helper qualifications and limits remain in effect. Exact candidate is for SAME14 independent review through Gateway; no publication or integration acceptance is implied.
