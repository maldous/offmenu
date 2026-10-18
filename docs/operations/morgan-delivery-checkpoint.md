# OffMenu operations checkpoint

The publication candidate is `docs/operations/morgan-delivery-ledger.json`, accompanied by `docs/operations/morgan-historical-reference-catalog.json`. These update the existing delivery ledger and reference immutable history; they do not replace the original journal or establish semantic replay. Root publication and immutable readback are still pending.

## Latest verified result

[Survey004 run 39080278066](https://github.com/maldous/offmenu/actions/runs/39080278066) finished incomplete. The hosted publisher succeeded, but that does not mean corpus acceptance. France has 3,484 exact matching XML/XLSX IDs and 84 visible headers; dictionary and value semantics remain incomplete. Norway crashed with SIGSEGV during its first strict JSON parse after the selected assets were read. All nine configured pins were verified in the terminal verification; Norway's final worker result did not establish completed pin/read-only attestation. No raw food rows were exported and no corpus acceptance was established.

The verified source is [314822f](https://github.com/maldous/offmenu/commit/314822f900c49953aeca04d82ce0957d851d19c9), with [control 498d66b](https://github.com/maldous/offmenu/commit/498d66b07c48f66e9a9d2ec99ce5845d140e3aa2). The [receipt artifact](https://github.com/maldous/offmenu/actions/runs/39080278066/artifacts/12118319259) has SHA-256 `184f7b527188c9f4678b9d419951c19ca2fa9308baec0d784039c71565b68849`.

The automatic cycle is already proven: [canary 39079524637](https://github.com/maldous/offmenu/actions/runs/39079524637) → actual webhook → [follow-on 39079671083](https://github.com/maldous/offmenu/actions/runs/39079671083) → actual webhook. Both executions succeeded. Preserve [PR31](https://github.com/maldous/offmenu/pull/31), its branches, workflow, continuation automation, source pins and PR30.

## Coordination and current work

Morgan owns priorities, dependencies, ledger completeness, dispatch, verification, capacity refill and user updates. Concurrent workers own substantive investigation, implementation, review and deliverables.

- Active: Norway targeted parser correction; France source-native extraction; Better Auth first implementation after the architecture plan and 13 tests; ledger finalization.
- Seven total concurrent sessions including Morgan, one Foo runner. Two stale pending-initialization tasks consume slots. The UI/tooling backfill attempt hit the limit and remains queued, not active.
- [Issue32](https://github.com/maldous/offmenu/issues/32) continues identity requirements. Preserve stable user-ID/private-data mapping and session/access-control compatibility. No production migration is established.
- [Issue33](https://github.com/maldous/offmenu/issues/33) continues UI feedback and architecture decisions: recover prior feedback, assess current-stack alternatives and independent adversarial review. No React/Preact solely for tools.
- [Issue34](https://github.com/maldous/offmenu/issues/34) is genuinely new CRM consideration, deferred until a working production platform.
- Automatically backfill available capacity with eligible bounded work. Reuse preserved shopping-deficit and meal-availability outputs before rebuilding; respect auth/state/UI single-writer ownership.

## History, provenance and open acceptance

The [immutable source summary](https://github.com/maldous/offmenu/blob/8c25c6d76088c958d17f7adc4a3c0af7aab5c298/operational-ledger/management-summary.json) contains 89 obligations and 43 bounded work items. Both sets, original owners/states and source JSON pointers are preserved. These counts overlap and are not current open-task totals. Historical cuts 5271, 5269, 5105 and 4889 remain distinct. Private filesystem locators are omitted from the publication derivative; exact original provenance remains bound to the immutable source and row pointers.

Six exact projector source bodies still need preservation and review before semantic replay. Source-specific rights/custodian/actor holds remain. Product caller/adoption receipts, Sonar findings and actual Android/iPhone device acceptance remain open or unverified. Earlier ac04 product-tree checks are identified as baseline checks rather than claims about every latest-source path. Historical scoped reviews do not close whole requirements.

Extra phase-durability work is parked. Production/CIX remain paused and FI held. No GitHub or Foo writes were performed by this finalization. Publish only the explicit allowlist in `publication-manifest.json`; the draft builder and local evidence directory are not publication artifacts.
