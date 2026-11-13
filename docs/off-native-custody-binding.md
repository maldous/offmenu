# OFF same-normalization custody binding

This source candidate binds the accepted OFF native policy to the SAME verified
normalization context. It is synthetic-only author evidence, not a real witness,
SourceContract factory, source grant, resource envelope or body-pass selection.
Worker57's live OFF witness/c670 checkout/session95514/lease10346 is untouched.

## Owned paths and reuse

New `off_native_binding.py` supplies one context manager, with new tests and this
document. The only existing-file change is a second, OFF-specific context in
`product_qualification.qualify_product_candidate`. The accepted USDA context
remains in place; non-OFF policies pass through the new context unchanged.
The normalizer/producers, accepted OFF policy, origin stage, PR71 consumer,
USDA/P1 code, price code and codec are unchanged. No failed review probes are read
or retried. This is a new OFF binding, not retrospective clearance of another path.

## Trust boundary and API

```python
with bind_normalized_semantics(contract, normalized, qualification_manifest, limits) as checked:
    result = qualify(checked, evidence_bundle, candidate, qualification_manifest,
                     input_root=originals_root)
    # Or explicit accept(...), with the same exact inputs and checked contract.
# Use the result only after this context exits successfully.
```

Only a reviewed application `SourceContract` carrying typed `PinnedOffSemantics`
and an exactly matching `policy_sha256` selects the OFF binding. Its immutable
`DerivationPins` must independently pin normalization manifest, database and
candidate hashes plus the independent derivation-review evidence reference.
Bare `UnboundOffSemantics` now refuses binding. The caller supplies the normalizer
result, but its recomputed hashes alone confer no authority. The
generic bridge already verifies source/evidence before parsing; the normalizer
rechecks its actual inputs; generic qualify/accept verifies selected assets and
candidate bytes before and after qualification. The new context does not replace
those checks or independently reparse the original to prove DB derivation.

A reviewed application factory must select those literal pins from accepted
evidence that establishes derivation from the exact pinned original, producer,
context and operation. It must never copy them from the cache being reused or
merely review its internal consistency. `independent_review_sha256` is a reference
to that accepted evidence, not a signature or a claim that this module performed
review. Computing `derivation_policy_sha256` authenticates nothing by itself.
There is no production cache-to-authority helper or real configured derivation.

The old direct-normalizer-result assumption was insufficient on reuse: the
normalizer may return an internally rehashed cache without rebuilding it. The
bridge now requires the external trusted snapshot for both new and reused output;
a changed artifact cannot replace that snapshot by recomputing its own hashes.
If no independent original-derivation evidence exists, qualification stays held.
A separately permitted and resource-qualified rebuild/verification against the
original may produce evidence for subsequent independent review and factory
selection. No such rebuild, original read, or automatic fallback is added here.
Explicit qualify/accept must still run within the binding context.

## Exact binding

Before opening SQLite, the context requires:

- Private native OFF2026-10-12, no holds, required/permitted retain/parse/transform,
  unknown original acquisition, exact policy context and rights/scope/clock assets.
- Application-pinned derivation and independent-review reference bound into
  SourceContract.policy_sha256, with exact manifest/DB/candidate snapshot matching.
- Exactly the source and three distinct evidence assets, with the declared source
  pin fixed by the accepted OFF policy. No JSON-loaded source/grant constructor.
- Exact source-specific schemas and schema fingerprint; explicit trusted expected
  count, supplied ProductLimits and SourceContract limits. No real values default.
- The existing normalization context, adapter version, clock-policy source hash,
  supplied limits and parser `products` role. Canonical comparisons retain numeric
  types, so a changed float/integer metadata representation does not compare equal.
- Exact qualification input list/role map; pinned on-disk `manifest.json` whose
  parsed fields agree with the supplied result, preserving the normalizer's own
  LF-inclusive `sharedSourceKey` calculation.
- Normalizer rawRows/paired product-profile counts consistent with that trusted
  expected count and supplied row limit. These are cross-checks, not a substitute
  for the actual independent full-input witness/ID digest.
- Regular non-symlink manifest/DB paths; manifest and DB byte/hash/identity checks;
  no SQLite WAL/SHM/journal sidecar. Private DB path remains `source.sqlite`.

SQLite opens with `mode=ro&immutable=1`, connection-local `query_only` and a native
value-size limit derived from the supplied row bound plus fixed framing overhead.
This prevents oversized TEXT being materialized in Python. These are local handle
settings, not platform/runtime/security-policy changes or new resource authority.
The expected physical `raw` table/columns must exist. No view is accepted instead.

For every product AND profile, a parameterized indexed query retrieves at most two
`raw` rows for the exact `products` identity. Missing/duplicate identity, oversized
or malformed body, invalid/out-of-extent ordinal and body-code mismatch fail with
fixed diagnostics. The stored logical ordinal, exact decoded raw body and trusted
context go to the accepted pure OFF semantic checker. A candidate's self-consistent
source row or candidate order cannot supply this authority.

On every exit, including exceptions, the handle closes and the escaped callback
expires. Manifest and DB identities/hashes and absence of sidecars are rechecked.
Even an atomic replacement with identical bytes invalidates that lifetime. A later
explicit retry may re-open unchanged pinned bytes under a new verified lifetime.
Detected mutation raises before the bridge returns/persists qualification output.
Receipts/results computed inside the context are usable only after normal exit.

The context hashes the DB before and after use, plus metadata, and performs two
source-row lookups per product/profile pair. That work must be included in the
future actual resource/operation qualification; no fit, timing or capacity claim
is made here. Generic acceptance continues to own candidate/input pre/post checks
and disk-backed ID/count validation. The origin-enriched path is not newly enabled.

## Fixtures and verification

Tests create only temporary authored gzip originals, evidence and normalization
DBs. A test-only mock substitutes the accepted policy's expected source asset
with that generated fixture pin, and fixture SourceContracts use authored count/ID
expectations and `fixture=True`. No source override or fixture switch is added to
the production API; no retained original/cache/sample/live database is accessed.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests python -B -m unittest test_off_native_binding test_off_native_policy test_product_qualification test_product_input_roots test_usda_product_contract -v
```

Coverage includes both native kinds through qualification, fixture acceptance and
retry; unbound refusal; missing/mismatched/tampered source/evidence/manifest/DB
context, role, pins, counts and limits; logical ordinal/body identity; DB schema,
sidecars, symlinks and FIFO refusal; same-byte replacement and lifetime mutations;
read-only handles, callback expiry and exception closure; oversized/corrupt DB
values; and original mutation during generic qualification. Existing OFF input-root,
legacy product and accepted USDA tests exercise the shared hook's compatibility,
not a denied review or retrospective source/data admission. The new PR72
regression rewrites DB rows, corresponding candidate records, all output hashes
and the manifest while leaving original bytes and trusted configuration unchanged.
It reproduces acceptance on4944b16 and refusal on the corrected source. Independent
fixture pin selection is explicit test setup, never a production authority helper.

## Still unresolved for real OFF

Actual eligible terminal/review hashes, count/sorted-ID digest, raw-row extent and
anomaly disposition remain unset. So do real ProductLimits/SourceContract limits,
reviewed product-specific rights/scope/clock evidence, runtime/destination/current
commitments/capacity and once-only operation selection. Historical dropped subsets
and proposed flags cannot fill these fields. Real source use remains private data
assertions under exact conditions; barcode strings are not verified GTIN/product
identity. No English/ingredient relationship/public/gold/country delivery follows.

the product maintainer routes this exact candidate to fresh existing56 independent review, then
the product integrator alone integrates the current accepted author/review pair. Worker57's live
witness and all source/custody/incident10230/privacy/denial/production/CIX holds
remain unchanged. No new job, charge, controller or framework is created.
Real independently approved original-derivation snapshot/review pins also remain
unset. The dirty-full-scope proposal is separate and not implemented here.
