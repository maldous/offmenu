# Independent focused capacity review — 2026-10-28

Approved supervisor SHA256 2ae57cc8edc66d9b56f43ad26dd8871fda155d23e50563988d3b0cac89d21674 and client SHA256 4a19ef0acfd49b83236b83dc65dca41785bb1ffad304b22f4a6ea04d556c3d8e against exact supervisor preimage 81b2918d8384ac3da63397263263c01340dc9b90031672d1fa4baab16aef8c1a.

Independently ran 36 offline checks, all passed in 6.460 seconds. See INDEPENDENT-TEST-RESULTS.log. Ceiling 64 jobs × 256 workers tested as declarations only, not a stress test or real workload claim. Behavior fixtures launch only a few harmless children.

Inspected atomic admission lock, durable reservation markers, held slot locks, aggregate declared budgets, ancestor/descendant read/write exclusion, retained legacy long/writer/reader behavior, stale-marker refusal, cancellation and sampled overbudget cleanup. Reservations persist through unknown outcomes and release only after verified child cleanup. No mount/network/ACL/host-admin expansion.

Cutover must occur at a clean natural qualification boundary, with no legacy readers and all future scheduled shared entrypoint calls routed to v3. Old v1 reader invocations after pooled work starts could bypass new accounting; direct old-file invocation is outside the cooperative reviewed-command contract, not made impossible by this patch.

The capability is cooperative resource-aware readiness: CPU millicore declarations are not CPU quotas; child RSS/process monitoring is sampled rather than instantaneous kernel enforcement; read/write roots are reviewed-command declarations, not a new filesystem boundary. Cgroup/ancestor limits remain unverified. These limitations are accurately documented and must remain in delivery claims. New supervisor file installs create-only; old active code is not replaced.

No Foo actions performed by reviewer.
