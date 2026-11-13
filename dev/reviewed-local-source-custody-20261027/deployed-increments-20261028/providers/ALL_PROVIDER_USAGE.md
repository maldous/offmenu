# All-provider orchestration — 2026-10-28 05:35 UTC

Private deployed entrypoint:
https://windmill.aldous.info/scripts/get/u/admin/offmenu_provider_orchestrator_20261028?workspace=offmenu

Arguments:
- `{"action":"plan"}` returns ALL18 provider groups and evidence-backed disposition.
- `{"action":"check","requests":[{"provider":"cohere","task":"batch_user_help"},{"provider":"groq","task":"parallel_batch_test_design"},{"provider":"gemini","task":"manifest_verification_tests"}]}` checks current eligibility/capacity without inference.
- Same arguments with action `submit` launch eligible independent jobs natively. Ineligible requested providers are reported, not allowed to block independent ready work.
- `{"action":"status","job_ids":["CHILD_UUID"]}`, `results`, or `cancel` use returned child IDs.

64 scheduler services minus2 controller headroom gives62 batch ceiling, checked against currently running jobs. This is observational capacity admission, NOT atomic global leases. Existing task templates limit actual useful distinct tasks; no worker-filling duplicates or artificial waits. Account quota remains independent of service capacity. No private input, paid fallback, alias rotation or automatic retry.

## Actual dispositions
- Ready task-fit: Groq public code/test scenario review; Gemini manifest scenarios; **Cohere public documentation**, not its failed parser task.
- Configured429 cooldown: OpenRouter, Mistral, Z.ai. Resume only after real cooldown/eligibility reconciliation, not blanket removal.
- Auth repair deferred: SambaNova401; Nous403 (new metadata audit).
- NVIDIA: platform review allowed under new instruction, but two documented model routes returned410. No blind model guessing.
- HF: both credential candidates catalog200 (135models), roles write/read confirmed. Least-privilege read candidate selected for one bounded free-grant call:402 Payment Required. No topup, purchased-credit use or alias switching.
- DeepSeek: balance metadata200, grantUSD0.00/is_availablefalse, no inference.
- Fireworks: official account endpoint412, unresolved account prerequisite; no inference.
- Cerebras/Together/OpenAI: no qualified free entitlement. Auth/catalog does not establish free inference; Codex subscription is separate.
- GitHub Models retired.
- Ollama cloud PAYG is not free-token entitlement; local runtime deferred. Configuration deployment returned unsuccessful, no bypass.
- CodeBuff aliases preserved; SDK/data-boundary/free-only route unqualified. No repository transmission.

## Concrete useful output
Cohere job `01a180fe-1250-1b61-e89a-5c4a7f0413fe` returned useful plain-English batch help,200/3095ms. Core statements accepted: child IDs, coordinator completion is not child completion, cancellation cannot recall sent requests, review results. Omit its overbroad claim that review 'ensures all child jobs completed successfully'; completion must be checked from actual statuses.

## Evidence
Five real parallel metadata children under `01a180fc-9c56-952d-02bd-57c2b4abfccc`: Nous403, Fireworks412, two HF catalogs200, DeepSeekbalance200. No inference in this metadata fanout.

HF inference: `01a180ff-e317-c00c-37c6-6666613d409f`402.
NVIDIA: `01a180fb-9a83-bc70-19fd-1658470d3042`410; current documented coder model `01a180fd-1c72-cf42-b1a3-14119eb83505`410.

Orchestrator check `01a18100-fbbf-ef38-b33d-731ca32bfea8` succeeded154ms:3ready, Nous independentlydeferred, observedactive1/available61, submitted0.8 offline tests pass. Source readback private (`extraPerms:{}`, `isDraft:false`). No additional inference merely to test orchestrator; native enqueue primitive already proved productive overlap earlier.

This is public/synthetic development orchestration, NOT execution of every private OffMenu ledger requirement. Generated outputs remain candidates pending deterministic/human review. Cancellation is scoped to children whose parent is this entrypoint; sent external requests cannot be recalled.

## Review correction — 05:48 UTC

Deployed source SHA256 `2f568d51aef98c405eb7b6e681719d572f820d7e9e8e8ebdd8bd425637804649` supersedes50ef.14 tests pass, including expired/nonexpired Retry-After, evidence-bound registry reset, no automatic retry, and exact OpenRouter resource reference.

`retry_providers:["provider"]` requests a controlled retry only after observed Retry-After seconds/date or an evidence-bound registry `cooldown_until` has expired. Old429 no longer unconditionally blocks forever.401/403 remain deferred. If no reset timestamp is known, the status is `reset_metadata_required`, not a claimed timed cooldown. Current OpenRouter/Mistral/Z.ai receipts have no verified reset evidence; do not invent one. Operator-recorded cooldown reset must be tied to exact `cooldown_evidence_job` and `cooldown_evidence_basis`.

Exact resource references are allowlisted; OpenRouter is `u/admin/intelligible_openrouter` (the original verified connection), not the separately imported credential. Enabled Groq/Gemini/Cohere deployed parameter schemas were checked. OpenRouter/Mistral useful-task adapters are currently draft-only; even after cooldown expiry the orchestrator reports `reviewed_adapter_not_deployed` until they are deployed, rather than claiming usability.

Live check `01a1810c-ee3f-7525-e2d5-f286c4f9f498`183ms confirmed Groq ready, OpenRouter reset-metadata-required, submitted0. This did not call providers. Fresh registry receipt was exported from deployed state with all18 dispatch dispositions present.
