# Focused validation of the completed enrichment unit

`enrichment-resilience-focused` is a native-v1 validation profile for exactly
`tests/web/enrichment-resilience.test.mjs`. Its only Node argv is:

```text
/bin/node --test --test-concurrency=1 tests/web/enrichment-resilience.test.mjs
```

The fixed Python wrapper runs in the exact candidate at
`/offmenu/.delivery/stokowski/native-validation/<spec.head>` (validated 40-hex
head), checks
head/branch, direct contribution parent/base, clean tracked/untracked state and
the sole committed output hash before and after execution. Scratch HOME/TMPDIR
and XDG locations are outside the candidate; the fixed environment carries no
inherited credentials, NODE_OPTIONS or NODE_TEST_CONTEXT. The actual TAP result
must contain four executed/passing cases, zero suites/failures/cancellations/
skips/todos and exit zero. One passing file is not four observed cases. This
does not retag the historical reviewer command: its direct Node observation
reported four named cases, while its focused test-runner result reported one
passing file. Only the new actual deterministic job can provide its own counts.

The profile retains the existing 180-second read-only bridge envelope/resources,
normal operation identity, observation, cancellation and no-replay behavior.
The standalone dispatcher recognizes the entire fixed wrapper and its literal
spec through AST/data checks and a normalized body hash; no candidate argv,
environment, callback or executable is selected from JSON. Existing profiles
retain their commands. This profile does not run the Python delivery suite.
Root prepares that new Engine-UID985 private clone under the existing host
project bind: `/home/user/src/offmenu/.delivery/stokowski/native-validation/<head>`.
It must contain the actual candidate head/tree/branch and be accessible to the
existing execution actor. Neither the shared checkout HEAD/workfiles nor the
SSH jail/mapping changes. The dispatcher requires this exact head-derived root;
`/offmenu` itself, another head or an arbitrary path cannot qualify. Other
profiles retain their existing roots. No workspace field is added to the spec.

## Same original runtime, separate contribution

Use `stokowski_stage.bind(original_runtime, spec, candidate_root=owner_selected_root)`
or its existing CLI `bind --candidate-root ...`. The argument is accepted only
for this native-v1 profile and is mandatory for it. It is not a new spec field.
The selected validation-binding record gains only `candidate_root`, retaining
the original six fields and their meanings. It is covered by the existing
selection/identity checks, and the adapter must independently requalify it.

The original manifest, admission, request, native workspace HEAD/branch, session,
receipt, provider history and lease remain untouched. The binder reconstructs
the original native binding, verifies the actual intent/dispatch hashes and
read-only SQLite finished-success lease, successful stopped receipt and unchanged
native output. The operation acceptance digest remains the existing compact
digest of original task, original receipt file hash and profile.

The reviewed contribution has its own root/head/branch. It must have the original
native base as its single parent, be clean, change exactly the original sole
output and retain its exact bytes and regular committed blob. No derivation is
allowed for this profile. The resulting operation spec keeps `base` at original
coding base and uses the actual contribution `head`/`branch`; the original
coding receipt never claims that contribution executed during coding.

For the observed UIF-102 unit, original execution remains `1bd0b370…` on
`bugfix/uif133-native-stage-continuation`, receipt `cb31fbb8…`, with output
`739ed6ad…`. The separately committed contribution is `08df89cd…` on
`bugfix/uif102-enrichment-resilience`, parent `1bd0b370…`. Original reviewer report
`59571927…` and separate contribution-equivalence supplement `0512bad8…` retain
their own identities. The coordinator/control source that contains this profile
is a separate executable pin, not either historical coding head or candidate.

This route uses the original native runtime's validation-bindings/Journal.
It creates no replacement, successor, reviewed-stage catalog entry or coding
lease. The adapter counterpart owns narrowly qualified finished-native control
continuation and unit-review comparison to the contribution branch. Active or
unstarted coding remains strict. Root must review/adopt the composed source,
then qualify the actual candidate, original result, selected metadata and remote
checkout before the normal deterministic validation job. Source acceptance is
not installation or execution permission.

The focused Python test uses real isolated Git, binding files and SQLite to
exercise this route, dispatcher qualification and critical active-lease/body/
file-only-result refusals. Node is an explicit command-boundary double there;
the test is not live enrichment validation. No original job, reviewer tests,
provider call, live source rights or whole UIF-102 acceptance is replayed.
