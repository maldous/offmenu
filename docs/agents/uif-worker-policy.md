# OffMenu execution-environment policy reference

UIF operating policy **2.0.0** is owned and installed by the selected execution
environment. Its canonical source is [maldous/uif](https://github.com/maldous/uif/blob/develop/docs/agents/uif-worker-policy.md)
and its [version manifest](https://github.com/maldous/uif/blob/develop/docs/agents/uif-worker-policy.json).
This file is a reference, not an installed policy bundle or proof of adoption.

When the UIF maintenance lane is selected, load the environment's verified bundle
and the `offmenu` profile, then this repository's current `AGENTS.md` and
applicable component instructions. Record actual version, digest, source revision,
executor and task ownership in the existing handoff. A branch link is navigation;
the installed manifest must pin the exact loaded source. Missing or conflicting
execution policy holds that maintenance lane; it does not create a product build
or runtime dependency on UIF.

Cloud Git, Foo Codex inference and Foo MCP commands have different prerequisites.
Quota exhaustion permits transfer only through qualified ownership and effect
fences. In the initial quota-only rollout, Foo must remain reachable and Morgan
must be active. On quota recovery, active cloud tasks retain their claims while
fresh independent local work may resume. A 64 Foo-local-session ceiling is bounded
by current resource admission and is separate from job/subprocess counts.

The environment policy does not activate services, relax project holds, transfer
publication rights or establish that handoff controls are deployed. This
repository retains its source, toolchain, review, privacy and acceptance contracts.
For white-room restart, reconstruct the selected task from current accepted Git
and Linear, reconcile retained work/checkpoints and original operation receipts,
then obtain fresh admission. Reuse accepted recovery evidence without replaying
superseded work or reclassifying protected data as a product prerequisite.
Local policy 1.2.3 and its manifest are preserved unchanged in
`history/` as dated evidence; they are not current startup instructions.
