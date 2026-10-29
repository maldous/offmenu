# Frozen R2 candidate — review only, not deployed

This directory supersedes the first candidate for review without modifying it.
R1 was a blocking flock held across a provider operation with only a socket
inactivity timeout. R2 uses nonblocking flock acquisition with a monotonic waiter
budget, plus a supervised provider subprocess with its own real-time deadline.

## Exact baseline and preserved tasks

`base/offmenu_groq_public_development_20261028.py` was reconstructed solely from
the provider owner's supplied source-only diff against the prior pinned baseline.
Its SHA-256 is exactly
`3760b83e2678f89e2330a62f2ccdf0a8e935461f5cbc2168a3f57d0e725e9f38`.
This is owner-supplied live-source evidence, not a fresh live fetch by this task.
Both added prompts are retained verbatim: `capacity_admission_invariants` and
`checkpoint_cancellation_boundary`. Each requires a bare JSON array of exactly
four objects with exactly `name`, `setup_summary`, `invariant`, all nonempty
strings, under 220 whitespace-delimited words. Wrapped arrays, missing/extra
fields and wrong counts fail validation. Earlier task shapes remain intact.

## Deadline correction

* `run_cached` defaults to a 5-second lock-wait budget (maximum 60). It uses
  LOCK_NB and polls with a bounded sleep. A stalled live owner produces
  `single_flight_wait_timeout`, an independent full failure receipt, zero inference
  calls and zero accepted outputs. The waiter never calls the provider as fallback.
* The owner executes the original provider function only in a POSIX fork child.
  A monotonic total provider budget defaults to 45 seconds (maximum 45), including
  request, response reading, parsing and child result persistence. The child arms
  ITIMER_REAL with default SIGALRM termination before touching the provider; this
  deadline remains effective even if the supervisor dies. It is not a socket
  timeout. Parent supervision also kills a still-live child at deadline and uses
  a bounded .25-second join for kill confirmation, without retry.
* A deadline produces `provider_deadline_exceeded`, unknown actual provider-call
  and token counts, `provider_outcome_unknown=true`, no accepted entry, and a full
  local failure receipt. A remote provider may already have processed the request;
  local termination does not prove upstream cancellation. Concurrent waiters can
  share that in-flight rejection; later explicit calls remain explicit new calls.
* The fork child inherits the key lock until exit. If kill cannot be confirmed,
  that live child keeps the lock; bounded waiters do not bypass it. No resource
  overwrite or stale-lock deletion is used as distributed coordination.
* Python KeyboardInterrupt/SystemExit are re-raised after supervised child cleanup
  and a cancellation receipt. Job-level SIGKILL cannot promise a final parent
  receipt; the child self-deadline still ends its provider operation. Any complete
  or partial worker result files are retained under `workers/` as evidence and are
  never accepted after timeout/cancellation. No provider result travels in argv,
  logs, cache keys, or new credential storage; the typed connection stays in memory.

Bounds assume functioning local POSIX I/O and ordinary OS scheduling. Filesystem
I/O, fork startup and kernel scheduling are not hard-real-time operations; a hung
or unsupported mount requires a verified outer job deadline before adoption.
POSIX fork/signal availability must also be verified in the actual job runtime.
The direct `main` entry point preserves the original transport contract; only an
explicit call to `run_cached` opts into the supervisor and reuse behavior.

## Existing-owner integration and unresolved prerequisites

Owner-supplied metadata identifies workspace `offmenu`, deployed adapter
`u/admin/offmenu_groq_public_development_20261028`, caller
`u/admin/offmenu_provider_orchestrator_20261028`, and typed connection resource
reference `$res:u/admin/offmenu_provider_groq_20261028`. No resource value or
credentials were read. These identifiers are supplied evidence, not newly verified
caller source. The owner reports `u/admin/offmenu_platform` state as
single_writer_per_key, not an atomic lock. Do not use it for single-flight.

Actual shared trusted POSIX storage across the Windmill containers remains
UNVERIFIED and is being checked separately by the owner. No store, namespace,
model epoch, deployment configuration or runtime mount was chosen here. The
smallest integration remains an owner-reviewed explicit call in the existing
caller/execution environment, only after those prerequisites are verified:

```python
result = run_cached(connection, task,
                    cache_dir=owner_verified_shared_trusted_posix_directory,
                    account_namespace=owner_nonsecret_account_identifier,
                    model_version=owner_verified_model_revision_or_epoch,
                    wait_seconds=5.0, provider_seconds=45.0)
```

Different container-local paths do not provide cross-container single-flight.
No new service is proposed. Account namespace/model epoch must not be derived
from credentials. Review the existing adapter/caller packaging and POSIX process
support before any live adoption. Retain full receipts and unique accepted IDs.
The prior exact-key provenance, revalidation, accepted-only cache, unique artifact
IDs, token accounting and fail-closed behavior remain; validator source/version
changes invalidate prior cache keys.

Rollback: restore the exact new `base/` adapter (including both added tasks) and
its prior direct main invocation. Stop using the candidate store; retain receipts,
worker evidence and artifacts. No live change has happened in this task.

## Evidence

15 local tests passed: the reused nine tests plus focused coverage for a live
stalled lock owner, total provider termination, independent child deadline,
cancellation receipts/rethrow, invalid deadline parameters and both retained task
shapes. All provider calls are synthetic mocks; no inference was performed.
See `tests.log`. The patch applies cleanly to the exact supplied live baseline.
The old frozen inventory and all original Windmill hashes were checked unchanged.
`FILE-INVENTORY.json` provides every deliverable's exact hash and size, excluding
itself. No test-only gains imply provider latency, token or production gains.
