# ADR 0010: Portable shared worker directions

- Status: source candidate for standard 2.4.1, published in PR #213; not merged into develop or deployed
- Scope: root AGENTS.md and docs/agents local policy and manifest
- Existing ADR 0004 through 0009 admission/integration contracts remain unchanged

## Decision

The user requested consistent agent directions across UIF and associated projects,
including independent Foo pickup and dynamic use of Codex allowance. Carry an
identical versioned local copy maintained in UIF, with SHA-256 and repo identity.
A bare link or symlink to another checkout would fail for isolated clones. Copying
whole AGENTS files would erase project-specific delivery and safety restrictions.
The local entrypoint composes shared directions with those preserved restrictions.

Separate native/cloud subagent availability, cloud durable task admission,
MCP deterministic execution and Foo/other Codex quota. A Foo quota outage must
not stop independent eligible work. A restored quota must not resume old work
without current normal admission and reconciled ownership.

## Validation and rollout

Check policy-copy identity and manifest references, preserve old AGENTS bytes,
run the existing discovery, delivery and final-layout checks in the pinned
interpreter, and report any blocked checks. Source review/adoption and remote
readback remain distinct from this local candidate. Existing active workers need
an explicit handoff; old worktrees do not inherit changes on another branch.
No runtime script, capacity-policy, workflow, scheduler or production service is
changed. Windmill enforcement investigation belongs to UIF documentation.
