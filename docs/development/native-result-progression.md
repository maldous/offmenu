# Native result progression

The existing CurrentWork poll prepares a contribution after a stopped native
coding success. A coding exit alone never qualifies source, publication or an
outcome. Original manifest, admission, request, native receipt and finished lease
remain unchanged and are requalified on every consumer boundary.

`stokowski_stage.prepare_completed_native(runtime, issue, *, candidate_root,
template)` returns `operation_key`, `candidate_root`, `source_head`, `spec_path`
and `spec_sha256`. Its exact template keys are `profile`, `policy_sha256`,
`runner_sha256`, `executor_sha256`, `git_author`, `validation_targets`,
`validation_scope`, and `source_repository`. The fixed profile is
`delivery-unit-focused`. Git author name/email come from the Root-sealed policy;
they identify contribution assembly, separately from the original coding
session. Commit metadata uses a fixed timestamp for deterministic recovery.
A private Git index writes ordinary objects and an immutable
`bugfix/native-<issue>-<receipt prefix>` ref in the selected project repository.
It never switches its HEAD or modifies its working tree/index. A separate private
bundle clone holds the exact contribution. Retained conflicting inputs hold.

The fixed Windmill Python consumer bundles that exact ref from `/offmenu` into a
private temporary clone owned by its execution identity. It checks exact
base/head/tree/output bytes, direct parent, clean source, and AST presence of
each selected unittest class/method before running it with the pinned Python.
Targets are bounded fully qualified unittest IDs, not shell, paths, import
expressions or arbitrary profiles. The existing dispatcher recognizes the whole
frozen body and exact resource envelope. This companion must be installed by
the existing live owner before the profile is operational. Preparation never
claims remote UID proof or live validation success.

Root seals one `native-review-template-v2` through the existing
`native_review_template` reference. It has the same static keys as v1 plus
`producer: {git_author: {name,email}, source_repository}`. `project_id`,
`source_root`, `resources` and `acceptance` are the literal `derived`. Owner,
control source/install pins, independent reviewer, provider/model/effort,
timeout, stopped-child requirement, receipt basename and read-only role retain
their existing checks. The owner-policy contract and typed validation-target accessor supply scope
and focused tests. A finite contract must explicitly bind its validation targets
in the original Root seal. A workclass contract retains its original finished
qualification. Both stay bounded to the existing six source files, and must
match the original admitted coding task. Neither authority is converted into
the other, and existing native source identities are preserved. No issue prose grants rights. The
review policy binds the actual private candidate and successful Journal receipt.
Requested and observed model/provider identities retain their original evidence.

`native_harness_runtime.prepare_native_unit(current, identifier,
linear_client=...)` derives the ordinary five-key owner packet at the original
runtime's `native-publication-packet.json`, then calls the independently owned
`produce_native_publication(current, issue, packet)` protected boundary. Its
returned normal selection is retained in the current runtime and consumed by
`owner_adapters` through the same fresh sealed-policy checks. Neither a packet
path nor saved coordinator status substitutes for that authority. Unknown
helper outcomes reconcile through the original helper identity. Native review
and validation remain original evidence, without rewriting them into publisher
receipts or admitting an Engine task.

The live owner must compose the owner-policy compiler/accessor, protected
publisher producer, source-acquisition separation and bounded outcome consumer
before installation. This source change does not install a dispatcher, grant
UID access, start jobs, call a provider or mark a whole outcome Done. Broad
UIF-102/UIF-130 acceptance remains false. The separately owned bounded outcome
consumer controls factual canonical integration and successor/refill acceptance.

The focused synthetic verification is:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tools/delivery:tests/delivery \
  /home/user/src/offmenu/.venv-delivery/bin/python -m unittest \
  test_stokowski_native_progression -v
```

It uses real isolated Git, SQLite, bundles and unittest execution, with explicit
review-provider and protected-publisher boundary doubles. It is source evidence,
not a live operational receipt.
