# ADR 0014: Environment-owned UIF operating policy

- Status: review candidate for repository standard 2.5.4; no runtime adoption implied
- Scope: agent startup references and operational documentation
- Predecessors: ADR 0010 and ADR 0012 instruction distribution only

## Decision

The user approved UIF operating policy 2.0.0 with project-specific instructions
and separate cloud, Foo Codex and Foo MCP execution profiles. Install and pin
the shared policy in the selected execution environment. Keep OffMenu's source,
toolchain, privacy, review, validation and integration contracts in this project.
The environment bundle records the exact version, digest and source revision;
agents acknowledge what they actually loaded at startup and handoff.

Replace the mandatory local shared-policy copy with a short reference and a
reference manifest. Preserve the previous policy 1.2.3 and its manifest byte for
byte under `docs/agents/history/`. Their recorded hash still identifies that
historical copy; it does not identify the new environment bundle. Isolated
product builds and ordinary project instructions require no UIF checkout or
policy installation.

## Operating implications

Linear remains the authoritative queue. In qualified runtime operation,
Stokowski admits local work while quota is available. Hard quota exhaustion
closes affected local model admission, reconciles original operations and
transfers eligible unfinished work to the corresponding project roles through
one durable ownership authority. Agents can use isolated cloud Git or deterministic
Foo MCP execution. On recovery, active cloud tasks keep their claims while fresh
independent local work resumes under resource admission.

The final operating target includes unattended Morgan reconstruction and an
ownership authority independent of Foo and this conversation. Sustained Foo/MCP
reachability failure defaults to a configurable 900-second grace and at least two
qualified probes; a healthy probe resets grace. Confirmed hard quota is a
separate immediate local-admission signal. Eligible cloud delivery continues
through the qualified independent authority; uncertain original effects and
unavailable dependencies hold only their affected units.

Preserve existing authorized running capacity and automatically resume eligible
work through supported recovery/admission when its prerequisites return. The
source contribution does not qualify the lifecycle or off-Foo authority adapter.
The 64 Foo-local-session ceiling is
separate from the older OffMenu adapter's eight-session configuration, Windmill
workers, deterministic jobs and subprocesses. Actual admission uses verified
current source/configuration and a shared resource budget.

## Preservation and verification

This change does not install the policy, change runtime capacity, qualify the
new ownership adapter, start services, resume historical workers, amend typed
validation, grant publication rights or release project/data holds. Existing
ADRs and integration-policy bytes retain their scope.

Verify preserved historical file hashes, current reference links/manifest,
standards discovery/check, final layout and whitespace. Exact-source review and
remote readback precede accepted source adoption. Loaded policy acknowledgement,
installed enforcement and useful operational delivery require separate evidence.
