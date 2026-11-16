# OffMenu 64 job / 256 worker ceiling — deployed configuration verified

## Confirmed baseline

Live Foo supervisor v1 SHA256 `81b2918d8384ac3da63397263263c01340dc9b90031672d1fa4baab16aef8c1a`; exact source in `job_runner_preimage.py`. Two short reader slots; one >30s job; shared writes globally serialized. Live Windmill client exact source retained in `windmill_foo_jobs_preimage.py`. See `LIVE-CAPS-20261028.json` for sanitized real getrlimit and 64 worker metadata evidence. Cgroup/ancestor PID and RAM limits are not visible inside jail; do not claim kernel certification.

## Opt-in capability, not forced operating allocation

- Maximum 64 admitted pooled jobs; each declares 1–256 computation workers plus 1–8 orchestration/child processes.
- Actual operating reservations, not maxima, are summed in one durable coordinator: CPU millicores (independent of process count), RAM bytes, declared output growth bytes, process count and read/write roots.
- 31-CPU Foo keeps four CPU affinity slots aside; pooled children share remaining 27. CPU demand total <=27000m. This is cooperative demand accounting, not a CFS quota. Up to256 I/O workers may declare1000m CPU.
- Declared aggregate RAM <=54GiB and observed MemAvailable minus8GiB; declared disk growth plus70GiB reserve plus bounded log allowance must fit. Outstanding reservations are conservatively subtracted again from current free amounts, which may reduce utilization but cannot justify overcommit.
- Mode `write` plus nonempty declared `write_roots` allows only disjoint declarations; write/write and write/read ancestor/descendant overlap is refused. `read` may not declare writes. Symlink paths, noncanonical paths, out-of-/offmenu roots and writes overlapping coordinator locks/jobs/checkpoints/runner source are refused.
- Declarations are trusted reviewed-command contracts, NOT filesystem isolation. Commands still possess existing checkout access. No new mount, network, ACL, UID, SSH, Docker, host or cgroup permission is added. A cooperative command can override affinity/environment or underdeclare writes; do not call this an adversarial enforcement boundary.
- Sampled descendants/RSS guardrails stop a job exceeding declared worker+overhead processes or RAM. These are not instantaneous kernel limits; threads are not worker processes. Child BLAS thread defaults are1. Kernel RLIMIT_NPROC is UID-wide and unchanged.

## Atomicity, locks, custody and legacy behavior

- A nonblocking `capacity-admission.lock` covers all v3 admission decisions and creation of the durable per-slot inflight marker. Up to64 legacy-named `execution-slot-N` locks/markers are shared, so future callers see the whole pool.
- The transaction lock is released immediately after marker creation; job slot and legacy shared access locks stay held throughout execution. Reservations are released only after terminal receipt and verified descendant cleanup. Unknown/stale markers fail closed; there is no automatic stale-marker deletion or replay.
- Pooled work holds the existing `execution-access.lock` shared. Thus any already-running legacy writer prevents admission; any new legacy writer is prevented while pooled work exists. Active old v1 read markers cause new pool admission refusal. Old v1 read invocations made after pools start could bypass the new accounting, so cutover requires no old running reader plus routing all future scheduled work through the upgraded entrypoint; direct execution of old files remains outside the cooperative contract.
- Calls without `resources` preserve two short-reader slots, one long-job lock and global writer exclusion. v3 legacy calls also refuse pooled markers. No default loosening.
- Existing cancellation files, heartbeat, stdout/stderr limits, request identities, checkpoints and subreaper descendant cleanup remain in place. Existing-ID receipts are observations; runner pin changes can produce id_conflict for resubmission, so use `status` for old IDs.

## Deployment contract

Reviewed `job_runner.py` installs create-only as `/offmenu/scripts/windmill/job_runner_capacity_v3.py`, without replacing old runner. Then existing owner-private `u/admin/foo_jobs_20261027` client can be updated to route future jobs to the new file; it accepts optional `resources` and sanitizes v1/v3 receipts. Preserve extraPerms `{}`. Independent review and mandatory confirmation are required before change. Coordinate entrypoint cutover at a verified natural qualification checkpoint; never cancel active qualification for this. Installation and readback are within existing approved project access; no host-admin helper should be needed. Host-level cgroup certification would require separately authorized metadata visibility and is not performed here.

## Validation

Offline unit/behavior checks only, no stress/load tests, no64-job/256-process test launch. Pure declaration test establishes64×256 schema/admission ceilings under low demand; local behavior tests launch at most a few harmless child processes to check legacy exclusion, stale reservations, cancellation and cleanup. This is configuration correctness, not throughput qualification.

## Normal scheduler operating policy

The executor ceiling remains64 and the pool schema accepts64 slots. Normal orchestration dispatches at most62 business jobs so two existing default-group workers can handle status/cancellation/checkpoint operations. These are not dedicated worker groups or a hard limit enforced by this file; the caller must honor the operating policy. If all64 workers are occupied, Windmill's server-side `cancel_job` endpoint remains callable without scheduling a65th worker job. That emergency path cancels the selected Windmill job; after a worker frees, inspect the Foo durable receipt and descendants/marker state before any retry. Do not assume a server cancellation alone proves remote cleanup or clears a stale reservation. Existing code never silently deletes a stale marker.

## Actual cutover

Completed2026-10-28 at05:05UTC after qualification005 naturally paused. Create-only install and deployed client exact-source readback succeeded; old supervisor unchanged, no inflight markers, owner-private ACL preserved. Initial deploy rejection was not bypassed: private draft was discarded, and exactly one retry followed materially new explicit trusted user setup/apply authorization. See `DEPLOYMENT-RECEIPT.json`. No business fanout/stress workload was launched. Assessor released to resume normal qualification using the same entrypoint with resources omitted.
