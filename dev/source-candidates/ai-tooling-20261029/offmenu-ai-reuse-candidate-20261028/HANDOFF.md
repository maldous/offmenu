# Groq accepted-result reuse candidate

Implemented locally, not deployed. No push, GitHub Actions, live Windmill changes,
provider probes, credentials, installations, admission changes, or private inputs.
The execution model is unknown (not exposed by this environment).

## Source custody

Base repository: private `maldous/offmenu`, pinned commit
`5957b94449fabfaa2f34f6f8e23c6474bc871012`, reviewed branch
`integration/reviewed-local-source-custody-20261027`.
Modified existing component (same filename):
`dev/reviewed-local-source-custody-20261027/qualification-capacity-successors-20261028/provider-adapter/offmenu_groq_public_development_20261028.py`.
Source and its public deployment metadata were retrieved read-only via the connected
GitHub tool. `base/` retains the exact returned content. The receipt names deployed
Windmill path `u/admin/offmenu_groq_public_development_20261028` and verified runs
`01a180cb-0380-4e03-b8c5-1cbd5b56ee10`, `01a180cd-8c18-5e1a-4305-a77649bb5ff3`.
Those metadata establish prior deployment; this task did not fetch run outputs or
assert their acceptance under the new validator. No existing output was seeded.
No preexisting AI reuse implementation or deterministic harness was found in this
component or the inspected local tooling. Tests use stdlib unittest and synthetic
responses, with no network access.

The working checkout remains at `8652b312ce7989c5e4f2d49ae765d5d8daf5841d`.
Its 68 on-disk Windmill files (including bytecode; 49 non-bytecode files) were
inventoried before work and verified unchanged afterward. No source worktree was
altered. The candidate lives entirely in this separate task directory.

## Behavior

`main(connection, task)` retains the fixed synthetic prompts, Groq endpoint,
`openai/gpt-oss-20b`, generation settings and explicit no-retry request path.
It adds deterministic JSON/shape validation, rejects duplicate keys/nonfinite
numbers, requires a stopped completion, and preserves exact bounded response bytes
in base64, response IDs, status, errors and full output (the old 6000-character
output clipping is removed). Response bodies remain capped at 1 MiB plus one
sentinel byte, with explicit truncation metadata. Validation is structural;
generated advice stays untrusted and is not evidence of semantic correctness.

Opt-in `run_cached` extends that same adapter, rather than creating another
provider gateway. Its exact canonical key covers provider and explicit non-secret
account namespace, model plus operator version/epoch, adapter source hash, input
hash, task, prompt/schema/validator/policy versions and generation settings. Any
change misses the old key. Each hit checks provenance, result integrity and the
current validator. An invalid entry is retained under `rejected/` before replacement.
Only structurally accepted results enter `accepted/`. Outputs/errors from all
calls are retained in immutable per-call receipts; rejected in-flight outcomes
are also retained in `attempts/` for concurrent waiters only. A later independent
call may try again; it cannot reuse that rejection as accepted.

Per-key POSIX flock spans request/validation/atomic commit; processes on one host
must share the same trusted local store. Kernel lock release handles process exit.
Concurrent identical callers share a successful result or an in-flight rejection;
separate keys do not block each other's provider calls. Atomic writes use fsync
and replace. This is not distributed coordination or an admission control change.
No TTL or semantic similarity matching is introduced. Retention/size management
remains with the provider owner; do not place the store on an untrusted shared path
or assume network filesystem flock semantics. Disk I/O errors propagate and must
not be interpreted as provider rejection or trigger automatic provider retry.

Receipts record `cache_hit`, `shared_inflight` for rejected waiters, actual
`inference_calls`, prompt/completion tokens, `provider_cached_tokens` when supplied,
and caller elapsed seconds including lock wait. Missing provider usage stays null;
reused calls charge zero inference/prompt/completion tokens and retain original
usage under `origin_usage`. No cache hit is inferred from prompt contents or
unreported usage. A deterministic accepted artifact ID binds provenance plus exact
output; `artifacts/` keeps it unique, including regeneration after cache corruption.
`new_accepted_outputs` is zero for repeats. Aggregate call metrics from distinct
receipt IDs and count unique artifact IDs (or artifacts files); never add
`origin_usage` to call totals. Unknown usage must remain unknown in aggregates.
Elapsed time is local observed call time, not a claimed production speedup.

## Minimal provider-owner integration

1. Review `adapter.patch` and tests against the pinned existing adapter; keep
   `base/` and the source manifest as rollback/custody evidence. Place the test file
   alongside the reviewed candidate during verification.
2. At the existing explicit provider invocation seam, opt in with:

   ```python
   result = run_cached(connection, task,
                       cache_dir=owner_selected_trusted_local_directory,
                       account_namespace=owner_nonsecret_account_identifier,
                       model_version=owner_verified_model_revision_or_epoch)
   ```

   No credentials belong in those arguments or provenance. The model is a public
   alias; the owner must pin a verified model revision or rotate its explicit epoch
   when alias behavior/version changes. This code cannot detect a silent upstream
   alias change without external evidence. The wrapper cannot silently enable
   reuse in unchanged Windmill jobs; deployment and a shared persistent store are
   still the provider owner's work. Existing typed connection remains unchanged.
3. Retain every full receipt and accepted artifact ID in the owner's normal local
   evidence flow. No global terminal hooks or shortened receipts are installed.
4. Rollback: restore the exact `base/` adapter and route the existing explicit
   invocation to `main` again. Stop using this store; preserve its receipts and
   artifacts for accounting. No production/data/admission rollback is needed.

## Verification and limits

Run `python -m unittest discover -s candidate -v` from this directory.
Tests cover exact reuse, all provenance dimensions, current-validator rejection,
cache tampering and unique IDs, failed/malformed/truncated output retention,
namespace/version preconditions, reported provider cached tokens, and multiprocess
single-flight for successful and rejected requests. All provider behavior is mocked.
No output-byte reduction, token savings, provider latency or production gains were
measured or claimed. Nine tests passed before handoff; see `tests.log`.
