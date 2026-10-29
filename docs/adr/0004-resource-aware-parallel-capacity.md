# ADR 0004: Resource-aware parallel execution capacity

- Status: implemented with deterministic admission and native configuration checks
- Standard: repository 2.1.0
- Base: ecd9341baf5e860ab5786315443eceaedbfa013c
- Supersedes: pilot concurrency and single-task admission in the initial Symphony demonstration

The user selected explicit ceilings: Symphony eight concurrent agents, Windmill
sixteen service workers, thirty-two resource-declared jobs and sixty-four
computation subprocesses per job. The earlier one-agent pilot established a
working route; it is not the operating ceiling. These numbers are capability
ceilings, not an instruction to manufacture work or guaranteed provider quotas.

One reviewed capacity-policy.json defines the settings. Native Symphony uses
reviewed manifests with exact project, issue, branch/head, owner, write scopes,
acceptance and resource demand. Its hooks no longer require every manifest to
select UIF-90. Private clones isolate physical edits; logical write ownership
prevents concurrent overlapping deliverables. One integration writer reviews and
publishes source. Coding-session completion never means accepted application work.

A local transactional reservation pool admits up to eight sessions. Immutable
bindings and persistent cancellation/terminal records prevent implicit replay or
expiry-based release of uncertain work. Release requires observed process-tree
termination. The finite supervisor retains owned child cleanup and checkpoint
identities; Codex app-server state is separate per workspace. Provider admission
requires fresh existing-session/model readiness and a locally selected session
budget; it does not assert a vendor concurrency entitlement or purchase API use.

On the observed 31-CPU host, reserve four CPUs for system work, eight for native
coding, and nineteen for deterministic computation. Child CPU affinity preserves
that partition. Of the 54-GiB execution RAM budget, reserve 12 GiB for native
coding and up to 42 GiB for deterministic jobs, while retaining eight GiB of host
headroom. Current observed availability can reduce admission further. Native
coding reserves eight logical I/O slots; deterministic jobs reserve thirty-two.
These are declared I/O admission units, not measured device bandwidth. Preserve
70 GiB free disk space and account for declared outputs. Resource declarations,
sampled memory/process guards and OS CPU affinity do not create a security
sandbox or hard RAM/device-I/O cgroup isolation.

The reviewed Windmill runner lives under tools/delivery. Its policy hash is part
of the immutable request identity. The existing deployed SSH bridge selects that
runner with unchanged credentials, ACL and host-key pin. The original untracked
operational source remains preserved. Legacy calls without resource declarations
retain their documented compatibility exclusion (two slots, one long job, shared
writer exclusion); use explicit resources for the thirty-two-job pool. This
compatibility mode is not the new pool's operating limit.

The sixteen-worker reduction follows an idle preflight and preserves the database
and named cache/log volumes. Forty-seven retired Compose containers are retained.
One pre-existing standalone worker auto-removed its container on stop; both named
volumes were verified intact and the final readback reconciled before completion.
No data volume, source, paused coding worker or hourly automation was removed or
resumed. No saturation workload or eight-model filler run is part of validation.
