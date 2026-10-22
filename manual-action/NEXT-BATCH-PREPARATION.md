# Next ingestion batch: stored totals and classified record isolation

Preparation only, based on deployed source `af99cdfb4bac3bce9f4badae34333921a0074a76`.
The current Foo process is not changed or interrupted. Promotion requires a safe
exit boundary; this source export does not authorize starting another process.

This batch combines the independently reviewed live stored-totals/adapter-group
reporting correction with the independently reviewed expected-skip and framed
record-isolation correction. Each patch applied cleanly to the unchanged base;
shared engine/store hunks composed without manual conflict resolution.

- Existing writer-owned committed metadata totals are observed while workers run;
  they count staging source/version rows, not distinct entities or run writes.
- Completed adapter-group diagnostics become visible before the full domain ends.
- Expected non-recipe/lead-only records skip the per-error SQLite work while
  preserving historical callback ordinals and resume/source identities.
- Independently framed malformed JSON-array/SQLite records do not discard valid
  later records; irrecoverable framing errors remain terminal for that source.
- Acquired finite reason codes are retained in bounded, privacy-safe telemetry.

No fetch activation, new database copy, data deletion, workflow/profile change,
parallel parser/process activation, adapter version bump, or cursor reset.
The separately prepared process-parallel parser is EXCLUDED: measured lead-heavy
work was slower. The current eight-domain execution topology is unchanged.

Verification reuses the component suites (43 totals/callback and 129 error-related
focused cases), independent review (6 and 12 cases), and adds only 18 combined
focused cases: totals, error isolation, and exact receipt/spool size bound. All
passed. No broad suite or Foo diagnostic run was started for composition.
