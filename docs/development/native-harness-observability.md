# Native harness observations

UIF-129 provides an on-demand local projection of an owner-selected
`delivery-handoff-v1` through the shared `native_harness_contract` validator.
It creates no task state, claim, queue, checkpoint, service or telemetry store.
Linear remains the outcome authority; original Stokowski, Windmill, GitHub and
LangGraph records remain in their existing custody. Historical receipt readers
and `offmenu.delivery inspect` retain their existing meaning.

From the exact selected checkout, using the already qualified Python runtime:

```sh
PYTHONPATH=src:tools/delivery /path/to/existing/python tools/delivery/native_observations.py \
  .delivery/selected-handoff.json --policy config/delivery-release-policy.json
```

An optional `--native-receipt /private/original/receipt.json` projects allowlisted
request/resource metadata from an original native-coding receipt. The receipt
must match the handoff origin's exact file-byte SHA-256, original attempt ID,
lease ID and admitted source base. It is supported only for `native-coding-v1`
with an attempt, never by fabricating coding identity for another origin.
Inputs are explicitly selected local files, each capped at 256 KiB. References
are returned as bounded path/hash pairs and are never opened automatically.
No live connector or credentials are needed. Keep input/output private in the
existing ignored `.delivery/` custody; do not commit operational receipts.

The output has `authority: observation_only` and `references_verified: false`.
Schema qualification establishes shape and cross-field consistency; it does not
authenticate a source or establish external truth, freshness or permission.
The handoff fingerprint identifies the selected snapshot, not a live database.
Concurrent owner writes are not observed atomically. Exit zero means projection
succeeded, never acceptance or permission to dispatch, retry, merge or deploy.

The projection keeps these facts separate:

- `source_acceptance.recorded_review` retains its source/output-bound review
  reference and verdict. Integration and release acceptance stay unknown.
- `operation` and `effect` retain their original native identifiers and recorded
  states. A verified effect does not imply source acceptance or runtime readback.
- `execution.requested` and `declared_resources` remain distinct from `observed`
  and `sampled_resources`. The existing performance projection supplies the
  allowlist and sampled-resource semantics. A model is observed only with a
  completed turn and explicit observed resolution. Unsampled legacy zero peaks
  remain null. Provider/effort observations unavailable in that reader stay null.
- `cost_usd` is null and `runtime_readback` is unknown; neither billing nor live
  installation is established by a receipt or handoff.
- `next_pickup.status` stays unknown because this handoff has no native pickup
  observation. Its owner-record reference points back to the canonical origin;
  admission, a successful job or a review never proves the next worker picked up.
- `recovery` points to the same original operation receipt (or origin when no
  operation exists). Submitted/running/unknown operations and absent/uncertain
  effects require owner reconciliation; this advisory field executes nothing.

Missing facts are null/unknown, and raw receipt logs, prompts, credentials,
transcripts and arbitrary extra fields are excluded. Rejected CLI input returns
a fixed error without echoing input or paths. Source references can themselves
be private locators, so the output is intended for the existing authorized owner.

This is a source-only seam. Live observation adapters, actual next-pickup proof,
independent review, integration and coherent runtime adoption remain with their
existing owners. It neither advances UIF-129 in Linear nor closes UIF-120.
