# ADR 0012: Cloud routing and shared worker policy 1.2.0

- Status: decision recorded for repository standard 2.5.2; source adoption is established by reviewed integration and canonical readback
- Scope: shared policy copy/manifest and task-routing documentation
- Predecessor: ADR 0010; conditional validation remains governed by ADR 0011

## Evidence and decision

The user requested consistent project-agent operating directions. The accepted
AGENTS entrypoint already permits independent project-cloud Git, CPU and storage,
with optional correctly scoped Foo MCP execution. The task-routing runbook still
prescribed Foo/Stokowski for repository work and Windmill for all deterministic
validation. Reconcile those statements with the accepted operating model and
ADR 0011's independent cloud validation for reviewed Foo-independent scope.

Carry the exact canonical UIF worker policy 1.2.0 from commit
`a3765f7e50592f552a2d1d3a5edccb13cb6a38de`, with SHA-256
`f5ee8222835c8c7ba775c9fc10462c202bc32bc1676e9ca698e29126249f84e5`.
Change only the local manifest version/hash; preserve its repository and custody
fields. The canonical copy supplies continuous-operation, ownership, execution-
mode and handoff directions. Keep the earlier 1.1.1 record historical.

## Boundaries and tradeoffs

A local pinned copy works in isolated checkouts, but later canonical revisions
require explicit coordinated distribution. Source adoption does not provision a
role, establish provider availability, resume historical workers or deploy host
configuration. The general Cloud role remains without Git configuration or a
repository binding. MCP execution supplements project-cloud work and must bind
the correct project, host, owner, worktree and branch.

Preserve typed admission, resources, immutable evidence, independent review and
the sole authenticated integration writer. Foo-dependent or unclassified
validation retains Windmill; cloud validation uses the accepted v4 contract.
No integration-policy bytes, runtime code, capacity limits, workflow, permissions,
service configuration or exception rules change. There are no new delivery gates.

## Verification and rollout

Verify canonical policy bytes/hash and preserved manifest fields; run the pinned
discovery, standards and final-layout checks, exact-source review and whitespace
checks. Publish through normal project integration and verify remote source
readback. Existing sessions must load the accepted instructions at startup or
handoff; a merged copy alone does not prove universal runtime adoption.
