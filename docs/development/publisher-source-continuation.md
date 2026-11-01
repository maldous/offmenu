# Same-operation publisher source continuation

Coherent source adoption can replace a publisher capability while its existing
integration operation is still active. The owner first stops the normal service
and freezes its actual invocation history. No publication binding, source unit,
claim, packet identity, validation job or original receipt is replaced.

The Root-sealed selection may add `context.publisher_continuation`, identical to
the optional protected publisher config `nativeContinuation`. This integration
context extension requires the existing reviewed runtime and publisher capability.
The descriptor has exactly nine keys:

- `version: 1`, `operation_id`, `unit_sha256`, `packet_sha256`.
- `claim_sha256`: the helper fingerprint of the unchanged actual active claim.
- `previous_selection_sha256`: the original selection fingerprint.
- `previous_capability`: the original exact version/closure/host-confirmation tuple.
- `previous_record_sha256`: the helper fingerprint of the entire old invocation record.
- `receipts`: 1–128 unique canonical invocation IDs, each with exactly
  `invocation_id`, `closure_sha256`, `receipt_sha256`.

Receipt hashes cover the original helper wire body **including its final newline**;
record and claim fingerprints exclude that newline. Root qualifies the actual
claim and original durable receipt bytes. A descriptor is data, not an assertion
of privilege or permission to replay an unknown action. There is no callback or
executable selector and no new-closure field that could introduce a sealing cycle.

Under the existing coordinator lock, the normal owner consumer validates the
exact previous record and every original request, result and kernel terminal
proof. A failed original read-only observation can remain terminal history;
unknown/pending results, incomplete proof, a failed step without a native result,
missing receipts and conflicting pins hold continuation. The ordinary unit,
selection, source and ownership gates still run. One normal atomic state save
retains the whole previous record under `history`, records the sealed grant, and
switches the active epoch and task selection together. Restart does not append
that history again. The existing total limit of 128 invocations still applies;
at most eight retained epochs can be read.

Old epochs are always validated with their original capabilities. The privileged
helper checks the actual old receipt files against the sealed whitelist and
validates each old closure independently before any new spawn. Old bytes are
never relabeled with the new closure. Missing original files hold even when the
coordinator has a cached copy. New receipts record the actual newly installed
closure. The active epoch starts empty, so an old ready response cannot authorize
a step: a fresh supervised read-only observation under the new capability must
precede a new step. The existing Controller and claim continue to own effect
reconciliation and prevent replay; no second tracker or manager is introduced.

The integration admission used to qualify fresh GitHub observations is a separate
optional config field owned by the fixed publisher. Neither extension changes the
original snapshot/qualification/publication operation or manufactures a new review.
Root must install and seal the coherent accepted source, capabilities and actual
host proof before the normal consumer can apply this transition. Source tests do
not establish live adoption, product deployment or CIX permission.
