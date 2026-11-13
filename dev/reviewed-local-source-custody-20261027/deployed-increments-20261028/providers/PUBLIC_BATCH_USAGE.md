# Private public/synthetic development batch entrypoint

Deployed: `u/admin/offmenu_public_development_batch_20261028`

Open https://windmill.aldous.info/scripts/get/u/admin/offmenu_public_development_batch_20261028?workspace=offmenu under the existing account. This is a runnable script, not a new UI or credential setup. Its JSON arguments:

- Catalog: `{"action":"plan"}`
- Verify eligible routes without inference: `{"action":"check","tasks":["parallel_batch_test_design","manifest_verification_tests"]}`
- Submit real selected work: `{"action":"submit","tasks":["parallel_batch_test_design","manifest_verification_tests"]}`
- Status: `{"action":"status","job_ids":["RETURNED_CHILD_UUID"]}`
- Results: `{"action":"results","job_ids":["RETURNED_CHILD_UUID"]}`
- Cancel: `{"action":"cancel","job_ids":["RETURNED_CHILD_UUID"]}`

No token is pasted into arguments. The worker resolves existing private connection references.

## Task catalog

Groq: `atomic_checkpoint_review`, `parallel_batch_test_design`, `exact_hash_custody_test_design`, `capacity_admission_invariants`, `checkpoint_cancellation_boundary`.
Gemini: `manifest_verification_tests`.

Select 1–3 unique tasks; at most two Groq tasks and one Gemini task per batch. Tasks use existing fixed public/synthetic specifications. This is deliberately NOT an arbitrary prompt, private repository, raw data, or file ingestion interface. Additional real requirements can be represented as reviewed public/synthetic task templates; no private data authorization is implied.

## Results, limits and cancellation

- The submitter returns actual child job IDs and run URLs. Native worker dispatch avoids cloud-connector enqueue serialization. Coordinator activity is not productive-work count.
- Outputs are candidates requiring human/deterministic review. Completed HTTP200 is not delivery. Existing generated cases contained arithmetic and fixture errors; no generated code runs automatically.
- Registry free eligibility must be literal true and enabled policy must match fixed-public tasks. Latest completed provider result429/401/403 stops that provider's new batch pending reconciliation. This checks latest observed outcome, not a durable global rate lease; overlapping submissions can race.
- Bounds are PER BATCH, not a global worker lease. Capacity owner confirms Foo confinement coordinator does not govern these network jobs. Do not spam batches to fill workers.
- No automatic retry, paid fallback, token/key rotation, private input, or local AI installation.
- Cancelling the short-lived submit coordinator does not recall already-launched children. Use returned child IDs. Cancel action only touches allowlisted child paths whose parent was this entrypoint. A sent external provider request cannot be recalled; cancellation reports requested, not confirmed.
- In Windmill Runs, select **All job kinds** to see child jobs: default parent-only filtering can hide actual parallelism.

## Verification

9 local mocked tests passed (including bounds, private-input rejection,429hold, cancel scope and output sanitization), plus independent source review. Deployed source readback confirms `isDraft:false`, `extraPerms:{}`.

Live non-inference jobs:
- plan `01a180f6-b76c-84ec-31c8-106f06cb4feb`, success108ms.
- results `01a180f6-c692-1e14-3ab8-febd9ec264df`, success168ms, retrieved prior Gemini result safely.
- check `01a180f7-72db-bda1-a3b3-30982941f337`, success163ms, Groq/Gemini eligible and submitted0.

No new provider inference was performed just to test this wrapper. Submission is locally mocked and uses the same native dispatch primitive already verified with3 overlapping provider children. Cancellation ownership is tested offline, not exercised against real useful running work.
