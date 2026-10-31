# Native-platform harness contract

This maintained guide implements the source decision in ADR 0009 and
`config/delivery-release-policy.json`. Source adoption and runtime readiness are
separate. UIF-120 owns the outcome; UIF-121–130 divide the reviewed implementation.

## Source and release flow

1. Select an eligible canonical Linear outcome and an accepted `develop` base.
2. Admit one coding attempt in an isolated feature/bugfix worktree with an exact
   owner, allowed paths and fresh provider/resource proof.
3. Validate the candidate's exact source and outputs through the existing finite
   graph and bounded Windmill backend. Obtain independent exact-source review.
4. The sole integration owner publishes/merges with current head/base and reads
   back canonical commit/tree/ancestry. Reconcile unknown effects before retry.
5. At a release cut, freeze candidate base/head/tree, policy, required profiles
   and artifact hashes. Test that candidate while `develop` continues.
6. The release owner promotes the accepted result to `main`, verifies its tree
   and immutable tag, and preserves the previous release. Main then remains
   static until the next approved release. Product deployment is separate.

Linear status must name the acceptance actually established: source integrated,
released source, delivery BAU accepted and product/deployment accepted are not
synonyms. Promotion explicitly links its constituent issues. A branch name is
navigation, not the identity of an issue, attempt, operation or release.

## Shared boundary API for component work

UIF-122 owns `tools/delivery/native_harness_contract.py` and the versioned handoff
schema. It must provide deterministic `fingerprint(value)`,
`load_release_policy(path)`, `validate_handoff(value, policy)` and
`validate_release_candidate(value, policy)` entry points. Validation returns the
qualified value or raises a bounded contract error; it performs no network,
claim, dispatch, receipt migration or credential access. Exact schema fields are
defined by UIF-122's reviewed contract and are consumed by component owners,
not copied as competing validator definitions.

The contract keeps canonical issue/project UUID, owner, typed execution origin,
exact source branch/base/head/tree/target and policy pin distinct from optional
attempt/lease, operation/backend job, review/effect and release references. An
origin without coding never fabricates a coding attempt. Evidence is linked by
bounded immutable references/hashes; raw logs, secrets and transcripts remain
in their existing private custody.

## Parallel ownership

UIF-123 owns Linear action planning; UIF-124 owns the Stokowski adapter/worker
and coding admission; UIF-125 owns the delivery graph engine; UIF-126 owns
Windmill dispatcher/runner/bridge; UIF-127 owns the integration controller and
GitHub publisher; UIF-128 owns the release-cut/profile/aggregation path;
UIF-129 owns read-only observation projection. UIF-130 owns coherent adoption
and final maintained standard/entrypoint reconciliation. The Linear issue lists
exact owned files; a shared-file change requires explicit owner reconciliation.

All component workers use already installed dependencies and bounded affected
checks. They preserve other workers' edits, old runtime/catalog files and all
uncertain effects. The root retains the sole Linear mutation, integration,
publication and activation role; available capacity never grants extra authority.
