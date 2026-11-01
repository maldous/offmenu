# Integration from completed Journal v3 validation

The existing protected owner may select an integration context containing exactly
`reviewed_runtime` (the original private Journal runtime directory) and
`unit_review` (an original private `{path, sha256}` packet reference), plus the
existing optional `publisher_invocation`. This is an integration-only alternative
to `engine_root`, `engine_task`, and `unit_review`. Release retains Engine evidence.

The packet must have `origin: retained-typed-review-v1`. The original
`CurrentWork._check_unit_review` reader must recompute that exact packet from the
admitted reviewed source and all pinned original inputs. Its integration binding
supplies head, base, tree, outputs, and head_branch; its validation_receipt is the
actual completed receipt. Review coverage binds those facts to the handoff.
This runtime hook does not infer model provenance or qualify a six-key source
review by itself. The existing standalone supplement route remains separate.

The hook then calls the same `reviewed_origin` and `_check_reviewed_terminal`
readers. The selected runtime, issue/project/owner, source and output identities
must match. The handoff operation must bind the original operation key, logical
job, succeeded status, command/runner/policy hashes and receipt. Its receipt
reference must be the fixed original `reviewed_runtime/validation-receipt.json`
path or one of the stage's original file-byte pins. The fixed path permits a
receipt created after the frozen admission, without rewriting that admission.
The terminal reader receives that exact fixed receipt_path and returns the
fully qualified original receipt. The sealed handoff's file hash is checked by
pinned_private; those bytes must equal both the terminal reader's returned
receipt and the qualified packet receipt, retaining the original Journal digest.
An arbitrary unpinned path cannot qualify even when its contents match.
Journal receipt-state digests use `symphony_capacity.digest` (compact sorted
JSON). Engine digests and shared wire fingerprints retain their own formats.
The handoff's existing effect/reconciliation gates also remain required.

Normal `owner_adapters` supplies the optional seventh
`OwnerAdapters.integration_acceptance` callback only for this explicit Journal
context. `CurrentWork` must preserve that field when wrapping trusted adapters.
The existing six-argument adapter contract defaults to the Engine path. The
adapter's finite context validator must admit the Journal context only for
integration, qualify reviewed_runtime as a private directory and unit_review as
a pinned reference, and retain the optional invocation checks. These adapter and
retained-reader changes belong to owner122 and require consolidation separately.

Successful qualification supplies truthful `context.validation` evidence with
origin `reviewed-source-journal-v3`; it does not supply `context.engine` or create
Engine bindings, check receipts, acceptance files, Controller history or jobs.
The sole publisher still owns the original claim, permissions, durable intents,
uncertain-effect reconciliation and canonical publication/merge readbacks.
Unit approval keeps accepted_delivery false. Existing owner authorization,
verified transaction cleanup, Linear/outcome and successor rules control refill.

Focused verification uses `test_native_harness_journal_acceptance`. It exercises
the real owner factory and finite boundary with a synthetic reader122 trust seam,
including original-reader/terminal refusal, runtime/operation/receipt/source
binding, and unchanged release refusal. It does not validate reader122 itself;
the consolidated original-reader contract must be checked by its owner/reviewer.
`RealTerminalDigestTests` additionally exercises the real original terminal
reader with compact Journal state, six frozen nonreceipt inputs, body drift and
sealed file-hash drift. Before consolidation its test-only
`OFFMENU_TEST_TERMINAL_READER_SOURCE` may name owner122's exact source file;
otherwise it uses the consolidated installed reader. No receipt reader is mocked
in those tests, and the generated fixed command is only hashed, never executed.

## Identity unit into an advanced develop target

An owner-qualified publication v2 binding may additionally carry
`source_projection` with exactly ten keys: `version: 1`,
`profile: identity-client-focused`, `source: {head, base, tree, branch}`,
`target: {base, tree}`, `merge_tree`, `outputs`, `unit_sha256`, `operation_key`,
`receipt: {path, sha256}`, and `review_sha256`. Existing binding/snapshot hashes
seal this data. The original qualified unit, review-packet fingerprint and
Journal operation/receipt references retain their original meaning; the owner
associates them through the existing qualified native unit before sealing.

Binding head/tree/branch remain the original reviewed source. Binding base is
the current API target. Validation and review head/base remain the original
source, never the advanced target or a new publication commit. The original
commit keeps its original parent. A canonical merge must have parents
`[binding.base, binding.head]` and exactly the admitted merge_tree. Unit merge
verification remains separate from full-issue acceptance and Linear Done.

`identity_source_projection.qualify_projection` reads immutable Git objects.
It requires the original source's single parent/base, base ancestry of target,
source changes exactly the reviewed outputs, unchanged target entries for those
outputs, and original reviewed file modes/blob hashes. Replacing those entries
in the target must produce exactly merge_tree, preserving every other accepted
target entry. No commit, ref, worktree, claim or validation is created.

All source/result Git bytes and modes outside exactly `docs/development/`,
`tools/delivery/`, `tests/delivery/`, and `src/offmenu/delivery/` must match. These
are delivery-only exclusions for the fixed two-test identity profile. Inspection
of the actual UIF-96 inputs found 62 tracked paths and 123 import/file-read edges,
including the injected handler, SQL, app imports, corpus/research inputs, build
options and package/lock manifests. None imports those excluded namespaces or
the 23 advanced-target delivery paths. Both fixed Node test entry points and
all their tracked inputs match the merged tree. This admission transfers the
already-qualified unit delta, not arbitrary profiles or execution environments.
Historical runtime facts remain unchanged and unknown where unobserved; no new
binary manifest or installed-byte equality claim is required.

Normal Python publisher preparation takes the repository only from the existing
protected publisher workspace. Projected bindings lazily import this small
validator and pin its source under the existing codePins rule. Other bindings
and release behavior retain their current source/pin requirements. The publisher
counterpart must keep the original raw commit parent distinct from target base,
qualify native source through the admitted association, and preserve current
refs, ownership, durable intents, uncertain-effect handling and exact readbacks.

`test_identity_source_projection` covers a real Git clean merge, original
validation plus advanced-target publication, canonical merged-tree refusal,
input/output-target drift, forbidden profile/default behavior and separate unit
versus full-issue outcome. Its Controller and claim state are isolated fixtures;
no API operation or Node validation job runs.
