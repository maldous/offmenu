# Owner16 immutable test source fixtures

These byte-exact snapshots make the focused tests executable without historical Git objects. `manifest.json` records original commits/paths/SHA256; `verify.mjs` verifies them. Do not edit snapshots to make tests pass. Update only through an explicit reviewed protocol selection with corresponding provenance.

`sqlite04` is reviewed Owner04 protocol25543bd and its complete relative import closure plus schema; `d104` is selected native D1 protocolf88902e and its complete relative import closure. `predecessor16` and `queue12` retain the actual wrong-digest predecessor demonstration. Their reproduction is intentionally vulnerable; neither is a newly adopted runtime component.

All files are test-only. Actual authority, grant expiry, CAS and ledger outcomes are implemented by the exact selected protocol; injected outcome damage exercises confirmation without granting authority. Production owner modules import none of these fixtures. SAME25's prior review supplied scoped digest PASS and packaging changes required; this packaging correction still requires exact-candidate re-review.
