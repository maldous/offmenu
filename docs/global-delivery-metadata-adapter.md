# Global delivery metadata adapter

`python -m offmenu.refresh.global_delivery --config CONTROL.json --output-root EXISTING_DIRECTORY`
extends the accepted `coverage.assess` and `global_run.run` interfaces. It passes
empty trusted bindings and runs their bounded metadata jobs. Exit3 means
`BLOCKED_STAGING_AUTHORITY`, not a successful source operation. It adds no source
runner, writer, dynamic plugin, scheduler, discovery census or permission grant.

The explicit config pins partition, seed, crosswalk, owner59 runplan, the selected
WFP execution plan, and a reference-only current ledger evidence snapshot.
Each pin has an absolute metadata path and SHA256; byte length is also checked
when declared. `owner59` requires a verified metadata byte length for the shared
retained policy planner. Config also selects exact retained matrix/source-ledger
paths, the reviewed retained policy SHA256, an observation clock and selected
management scope. The matrix/ledger retain their existing hardcoded pins.
Projection metadata cache identity includes the declared byte-length value and
whether it is present. Reusing a path/hash never bypasses a different length pin,
and a rejected pin cannot poison a valid peer sharing the same path/hash.
The result records `retainedPolicySha256` and binds it into
`planIdentitySha256`, so a policy change changes the plan approval identity.
The selected scope must explicitly match the immutable plan and unique retained
batch: batch ID, country, complete source/release/hash/use identity, derivative
path/hash, record count, writer and exact operation text, selection source pin
and ledger sequence. Custody joins the same country/release/hash/acquisition
clock. Missing or conflicting inputs stop before any blocker is resolved.
Only pinned control documents,64 owner packets and249 category control files are
opened. Embedded raw, derivative, review and handler references are not followed.

All249x13=3237 canonical domains remain explicit. The249x6=1494 projection is
separate routing metadata. The alternate `rows`/`sixCategoryRows` containers and
explicit `ingredients/composition` label alias are recorded, without semantic
equivalence or category acceptance. Malformed peer metadata preserves cells and
diagnostics. Fatal denominator, ownership, selection or primary pin conflicts
stop the run rather than substitute data. No inferred not-applicable exemptions.
Decoded null/scalar/list peer roots and malformed matched rows produce fixed
per-cell diagnostics while valid peer controls and all cells remain present.

The manifest joins delivery owner, separately unqualified source custodian,
source/review/handler references, acquisition and validation clocks, accepted
staging counts, provenance extent and replay disposition. Old scoped reviews,
historical handlers and latest ledger references never grant new authority.
Owner59's52 canonical and24 projection rows are validated separately; its five
candidate batches remain candidates, even if their metadata names accepted
historical scopes. Management-selected59/LY operation and writer are resolved;
exact source custody/use, reviewed normalizer and approved existing destination
remain explicit prerequisites. Original country owners retain execution ownership.

The shared retained policy is applied to the actual verified **metadata** pin,
with the source's declared original acquisition clock. Its key is not a dataset
body identity proof. Validation never resets source age. Missing authority remains
blocked even for matching metadata identity. Exact existing output bytes can
produce an artifact replay with zero writes, explicitly never dataset no-op or
admission. Output publication reuses the existing exclusive report writer.

Outputs are `manifest.json` and the unchanged harness `global-run.json`. Use a
new explicitly selected existing output directory for changed inputs. Existing
different bytes, symlinks and unsupported metadata inputs are rejected. No body
callbacks are enabled by this CLI, including when a config declares an authority.
Both output identities are preflighted before either publication, including
dangling symlinks. An existing conflict therefore leaves both destinations
unchanged. Each write retains its exclusive writer and replay check; this is
not a multi-file transaction against concurrent writers or later I/O failures.
Real source execution requires independently reviewed application bindings,
resource boundaries, exact existing destination contract and current source-use
qualification through Gateway. Production/CIX and other holds remain intact.
The metadata API explicitly selects `Limits(workers=4, max_sources=4096)`;
source-count capacity and the3237-cell canonical denominator remain distinct.
The CLI loads no trusted bindings. Existing `execution.reviewed_bindings` covers
only acquire/verify/parse/normalize/validate and cannot imply final admission.

Focused authored validation: `python -m unittest discover -s tests -p test_global_delivery.py`.
