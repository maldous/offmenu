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
reference must be one of the stage's original file-byte pins; those bytes must
equal the qualified packet receipt and retain the original Journal digest.
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
