# Cooperative capacity-aware lane driver v7

Candidate successor; no v6 or running job mutation. Install create-only at the reviewed corpus BASE/parallel-control-v7/parallel_driver_v7.py after independent review. Legacy invocation remains unchanged. Pooled invocation adds `--outer-job-id <logical foo_jobs job_id>` and must supply matching explicit `resources` to deployed `u/admin/foo_jobs_20261027`.

The explicit ID and marker/receipt request SHA select a reservation, not a security credential. A nonblocking shared admission snapshot lock prevents racing admission while validating the own held slot and any conflicting peer paths. Future admissions remain the v3 supervisor's responsibility. This is trusted cooperative coordination, not an additional filesystem sandbox or hard CPU quota.

Pooled plan lanes must fit their outer reservation: computation workers, shell+driver+lane parent/tracker process overhead, CPU budget, declared lane memory plus 512 MiB shared outer-control allowance, output growth, write roots including driver receipt/log root, and source-pin read roots. The 512 MiB is admitted headroom within the whole-job sampled RSS cap, not an independent per-control-process RLIMIT. Existing producer per-process virtual-memory enforcement stays unchanged. Already restricted pooled affinity does not lose another four control CPUs; legacy affinity retains its original four-CPU reserve. Both paths keep the driver memory headroom guard, source pins, bounded logs, cancellation, timeout, lane locks, and outer cleanup requirement.

`read_roots`/`write_roots` describe cooperative conflicts in the writable `/offmenu` namespace, not an exhaustive input manifest or access authorization. Approved immutable `/offmenu-corpus` mounts cannot be declared as any pooled job's writable root and remain fully represented by the qualifier's input provenance/pins. No host mount or scope expansion is involved. Mutable `/offmenu` source and data reads must still be declared.

The outer supervisor's own protected lock/job/checkpoint bookkeeping remains implicit supervisor control, not a workload write-root permission. A driver writes only its declared lane outputs and declared parallel receipt root, plus existing per-lane hashed coordination locks.

Validation: 44 local unit tests (31 unchanged legacy behaviors +13 capacity metadata fixtures), not a load/stress run. Test command: `python3 -m unittest discover -s offmenu-driver-capacity-v7-20261028 -p 'test_*.py' -q`.
