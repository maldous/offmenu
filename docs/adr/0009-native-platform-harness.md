# ADR 0009: Native-platform harness with develop/main releases

- Status: contract accepted under UIF-121; source standard 2.4.0; runtime adoption remains separate under UIF-130
- Accepted starting source: `37f733cc29627c6f137eb7905221dfabe39a7ecb`
- Parent outcome: UIF-120; shared evidence contract: UIF-122; coherent adoption: UIF-130
- Retains ADRs 0004–0008 and their original operation/evidence interpretation

## Decision

Keep `develop` for ongoing integration and `main` for reviewed releases. Freeze
an immutable release candidate from accepted `develop`, including exact base,
head, tree, policy and artifact hashes. Exhaustive release qualification targets
that candidate while `develop` continues. A repair creates a new candidate; it
does not rewrite old evidence. Promote only the reviewed, fully qualified result
to `main` and read back its canonical tree and immutable release tag. `main`
stays static between approved releases. An existing tag may be read back but
never moved. A merge that creates a different commit must still have the accepted
resulting tree; otherwise its changed result requires qualification.

Linear owns outcomes, dependencies and acceptance. Stokowski owns coding
dispatch/stages within fresh resource and scope admission. LangGraph owns finite
decision/checkpoint state. Windmill owns deterministic backend jobs and their
native identifiers. GitHub owns source/review/merge/tag facts. One integration
owner serializes shared source publication; one activation owner qualifies and
adopts a coherent installed closure. The roles can be held by the same admitted
owner. No copied queue, transcript, new scheduler or second task authority is
introduced.

The machine-readable contract is `config/delivery-release-policy.json`. It
describes required behavior, not credentials, approval or runtime activation.
UIF-122 supplies the typed handoff validator. Existing receipts retain their
original validators, origins, source and operation identities; this new policy
does not silently rebind historical or uncertain work.

## Admission and evidence

Every implementation binds the issue UUID, owner, accepted source, exact branch,
owned paths, provider/resource request and actual/unknown resolution. Independent
source review and meaningful exact-source tests precede shared integration.
Command, runner, policy, job and accepted output identities accompany validation.
Coding success is a candidate, not independent acceptance. A process exit, tag,
source integration, service start and product acceptance remain separate facts.

Unknown submissions or effects reconcile the same original operation/job before
retry. Resource leases release only after actual descendant termination. An
accepted merge with failed metadata write retries metadata, never the merge.
Branch movement never grants replay or upgrades an old checkpoint.

## Release and repair

The release owner explicitly selects and records a candidate; neither a moving
branch name nor the newest available build selects it implicitly. Independent
release checks may run concurrently under fresh aggregate resource and logical
write-scope admission. An aggregator requires every required profile/check and
output to match the same candidate; partial, failed and unknown checks cannot
become success. Routine feature changes need their affected checks; exhaustive
release qualification applies at the explicit release cut.

A release fix is first reviewed against the affected release source, qualified
as a new candidate, and reconciled into `develop` through normal review. It does
not force-update a tag or rewrite shared history. Deployment and product
acceptance remain separate from source release.

## Migration and activation

The user-directed pivot supersedes the obsolete temporary BAU approach; delivered
PR194 code and all original failed/completed receipts remain retained. Component
workers edit disjoint source paths and do not mutate Linear, publish, install,
restart or activate. Shared integration and coherent adoption remain serialized.

Activation of the new delivery BAU requires independently reviewed source,
meaningful end-to-end and recovery evidence, qualified existing credential
references, a reviewed exact installation/configuration, rollback custody and
actual runtime readback. Preserve the live legacy lane until the replacement
is accepted; retire only that qualified obsolete lane with state/history intact.
Actual host permissions and mandatory confirmations remain required. This source
decision does not grant product deployment, CIX execution, Actions, new spend,
credentials or security bypass.

## Acceptance

Verify fixed candidate identity across advancing `develop`, changed-source
rejection, exact promotion tree and tag no-overwrite; preserve legacy readers,
stopped-child and same-operation reconciliation. UIF-121 accepts this contract
through independent review. Component and runtime proof belong to UIF-122–130;
the contract is not their completion evidence.
