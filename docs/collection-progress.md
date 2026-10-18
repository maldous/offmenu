# Terminal progress for a manual collection pass

This is a next-version, source-only addition. It does not change an installed
launcher, start a collection, retry a source, or expand any collection approval.

The manual command writes progress to stderr. Its stdout remains one final
machine-readable JSON value. The launcher first prints a fixed
`stage=verifying-installation` line, then directly execs the collector with stderr
inherited. It does not capture or discard the collector's progress.
The launcher's fixed startup write also runs on a daemon thread with a bounded
0.2-second join, so a broken or stalled stderr cannot prevent execution.

The collector emits a startup line, immediate stage changes, a snapshot every
five seconds, and a final line. All lines are flushed, including when stderr is
not a TTY. No terminal framework, cursor control, percentage, ETA, or estimated
throughput is used. Counter updates do not emit a line per asset or data chunk.

## What the counters mean

- `download active`: requests whose actual transport has started and whose
  response has not reached EOF, failed, or closed. It includes connection setup
  and redirects performed by that transport. Cache verification and waiting
  futures do not count as downloads. An open response can remain counted until
  close when a known-length response ends without an EOF read.
- `prep active`: workers that have entered the preparation function and have not
  exited it. This is sampled from shared worker markers, not submitted-future
  counts. It includes integrity and cache checks inside preparation.
- `effective` and `configured`: the collector's observed resource-constrained
  limit and its selected configured ceiling. The display never raises either
  limit. Zero effective preparation workers remains zero.
- `queued`: jobs still in the scheduler's unscheduled queue. Jobs already
  submitted and doing claim, integrity, or cache checks are not in this queue.
- `download completed`: source results processed by the coordinator, including
  unsuccessful or blocked results. `downloaded` counts newly verified originals;
  `reused` counts verified retained originals requiring no request.
- `prep completed`: processed deduplicated preparation jobs, including failed,
  held, or unsupported jobs. `prepared` counts ready preparation results, and
  `reused` counts preparation-cache reuse. Duplicate asset aliases do not count
  as extra preparation jobs.
- `assets failed` and `held`: current asset outcome classifications, including
  aliases. These are a different unit from deduplicated preparation jobs.
- `bytes read`: the existing synchronized transfer meter's received bytes.
  `new-prepared-known`: new preparation bytes positively accounted for by the
  existing collector. It excludes reused outputs and does not claim that
  uncertain partial files occupy zero space. The JSON report continues to carry
  uncertainty/reservation accounting unchanged.
- `inventory classified`: manifest rows assigned an outcome classification.
  Classification can be held, missing, unsupported, unverified, or failed.
- `coverage verified`: independently verified country/type coverage, which is
  deliberately `unknown` in this hookup. The global denominator is 249 × 13 =
  3,237 cells. Neither a finished pass, classified inventory, completed job, nor
  prepared output proves that global coverage is collected or accepted.

Unknown totals are printed as `unknown`. Preparation totals are unknown until
the full deduplicated preparation queue exists. These totals are not inferred
from bytes, source counts, or the size of the manifest.

## Safety and failure behavior

Only the parent presentation thread writes stderr. Workers update count-only
observations. The reporter accepts a closed set of stages and nonnegative
integer counters; URLs, paths, headers, source identifiers, exception strings,
credentials, and document bodies are not display fields.

Preparation activity uses one shared byte per job, with a single worker writer
per slot. There is no progress IPC queue, feeder process, or shared lock that a
killed worker can strand. An unstable sample or uncertain process failure shows
`unknown` until all owned workers are confirmed stopped. Only then may the
parent clear remaining markers. Normal entry/exit markers are worker-owned.

Output occurs outside the progress state lock. A broken stderr disables only
presentation. A stalled sink can stall only the daemon presentation thread;
collection events and shutdown do not wait indefinitely on it. Start and stop
each wait at most 0.2 seconds for normal flushing. A failed or permanently
blocked output sink cannot be guaranteed to receive the final line.

Deadlines, request/byte budgets, per-host scheduling, output reservations,
durable checkpoints, original/preparation cache rules, downstream holds,
resource detection, and final result schemas remain collection authority. No
progress counter is used to make a collection decision.

## Integration requirements

1. Add `offmenu/refresh/collection_progress.py`, both focused test modules, and
   this document. Apply the separate collector/launcher hookup patch against
   the frozen `b83758a3067ecb8a39678fa05e66633a644350f3` source base, or adapt its
   narrow observation points during composition with another successor patch.
2. Preserve the existing error projection `progress` dictionary. The display
   is a separate optional `terminal` parameter. Keep actual transport wrapping
   around the final selected transport, including any new redirect policy.
   Do not replace a specialized transport with a less-restrictive default.
3. Keep the preparation worker initializer's existing storage-lock setup. The
   supplied initializer performs it before registering the activity markers.
   Keep spawn-callable functions in the importable module, not dynamically
   loaded collector fixture modules.
4. Preserve every scheduler/deadline cleanup rule. Do not clear activity solely
   because a future is marked done: a broken pool can complete futures while
   other child processes are still being stopped.
5. Refresh the successor launcher's complete source-file pins, including the new
   module, tests, document, and changed collector. Preserve exact predecessor
   pin/update mechanics. The hookup patch intentionally does not rewrite the
   frozen launcher's pin dictionaries; it is not an install-ready bundle.
6. Run the focused and existing regression suites after composing other changes.
   Do not publish, install, or execute a collection merely to test the display.

The tests use synthetic responses/files and local temporary installation
layouts. They cover concurrent transfer events, real spawned workers, killed
workers, zero capacity, unknown totals, cache reuse, error/interrupt terminal
flush, broken/stalled/non-TTY stderr, final stdout JSON purity, and actual
launcher exec inheritance of stderr.
