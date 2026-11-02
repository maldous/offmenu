# Original native publication producer

`native_harness_runtime.produce_native_publication(current, issue, packet)` is the
normal owner interface. It consumes the original runtime's immutable
`native-publication-packet.json` and returns the existing binding/packet/context
selection. It does not change the protected owner map or install configuration.
Worker 122 owns the normal caller and selection retention. The publisher owns
the derived admission; ordinary observe, publication, integration and outcome
continue through the existing native consumer and Controller.

The fixed helper's additional request has exactly `version: 1`, `mode: prepare`,
`issue`, `issue_id`, `project_id`, `owner`, `unit_sha256` and `packet_sha256`.
There are no caller-selected paths, commands, configuration, claim roots or
callbacks. Original paths come from the protected current catalog and the fixed
packet filename. A normal `invoke`/`observe`/`review` request keeps its old shape.

## One initial owner grant

Root may seal the optional `native_policy` in the existing publisher config:

```json
{
  "version": 1,
  "kind": "native-source-publication-policy-v1",
  "owner": "<existing logical owner>",
  "project_ids": ["ce60c1ab-a732-4a71-8471-14c9dc393886", "ffb6c7d9-4eff-46eb-a805-99f0cc2edfa0"],
  "controller_runtime": "/home/user/src/offmenu/.delivery/stokowski/<existing coordinator>",
  "source_head": "<accepted installed controller/publisher source head>",
  "source_sha256": {"tools/delivery/native_publisher_invocation.py": "<actual owner source pin>"},
  "owner_python_sha256": "<actual fixed owner interpreter pin>",
  "automatic_integration_enabled": true,
  "profiles": {
    "enrichment-resilience-focused": {"allowed_paths": ["<exact existing output path>"]},
    "delivery-unit-focused": {"allowed_paths": ["<exact approved Python source path>"]}
  }
}
```

The source pins must cover the actual accepted owner source used by qualification
and match the protected owner config. Profile paths are exact repository file
allowlists, bounded to sixteen entries; the generic profile permits Python files
and the exact reviewed `docs/development/project-aware-intake.md` output. Markdown
is hashed source data and is never executed. Root selects the narrower approved work class, including its file count.
The policy is an explicit delegation of ordinary develop integration. It grants
no release, new credential, caller API or coding-child merge authority.

Root's initial installation must also provide the exact fixed read-only actor
permission from UID 984 to UID 1000 for this argv (no wildcard arguments):

```text
/opt/offmenu-stokowski-current/venv/bin/python -I -B /opt/offmenu-stokowski-current/source/tools/delivery/native_publisher_invocation.py --qualify-native
```

The UID 984 parent independently checks the Root-owned installed source and
interpreter pins, supplies its sealed policy over the child pipe, and captures
the bounded result. The controlled owner actor reopens the original private
native lease/receipt, successful Journal/public receipt, independent native
review and approved exact gate. No runtime is chowned and no general traversal
or read ACL is granted to UID 984. The actor has no keys or HTTP interface.
An absent grant or unreadable proof holds preparation; a caller-supplied body
never substitutes for this requalification.

## Existing protected transaction

The qualified actor derives the v2 binding, snapshot and exact Git publication
plan from the actual reviewed candidate, with no projection or invented review.
Only the allowed changed bytes and necessary hash-checked Git objects cross the
pipe. The publisher stores immutable `native-config.json`, `native-objects.json`
and the terminal `native-prepared.json` under the existing
`transaction-<operation hash>` directory, as UID 984, mode 0600. The private
object closure lets the existing JavaScript candidate qualifier recheck the
entire plan without opening private owner workspaces as UID 984.

Preparation calls the existing `publisher_request(..., {op: prepare})` and
`Controller.prepare_publication`. The existing global repository lock and
`claim_releasable` rule decide claim transfer. A pending or unknown predecessor
holds; an interrupted admission keeps its partial files and holds replay.
An exact completed preparation returns its retained receipt without invoking
the Controller again. Normal publication and integration still require their
original fixed intent, protections and actual GitHub readback.

The Root config, key path, code closure and process identities stay fixed.
Dynamic admissions may change only binding, snapshot, plan, workspace and
integration admission; the workspace is the derived transaction directory.
Both fixed JavaScript and Python bridges independently select that admission
from the checked operation hash and enforce the sealed template. The existing
fixed original operation and its continuation/history path remain intact.

## Focused evidence

The dedicated `test_native_publication_producer.NativePublicationProducerTests`
uses real private Git, original native lease/receipt and Journal readers,
the normal private Controller and existing JavaScript object qualifier. Host
custody and the already-qualified independent-review reader are explicit test
boundaries. Generic profile cases test the Python/JavaScript policy association;
the fixed generic executor and full reviewer admission belong to their existing
owners. No test installs, reads a real key, calls an API or changes live claims.

## Accepted project source after verified readback

The optional `native_policy.project_source` uses exactly `repository`, `branch`,
`origin`, `source_repository`, `seed: {head, tree}` and `accepted_facts_path`.
The repository is `maldous/offmenu`, branch `develop`, origin
`git@github.com:maldous/offmenu.git`, shared object repository
`/home/user/src/offmenu`, and pointer path
`/var/lib/offmenu-publisher/accepted-sources/latest.json`. This descriptor keeps
project source separate from the sealed control-code source head. The shared
repository's dirty checkout is never changed by the publisher metadata writer.

Root initially creates the fixed accepted-sources directory as UID 984/GID 976,
mode 0755. After a new dynamic operation's actual stopped, verified helper
receipt, the publisher reopens the existing Controller's actual saved canonical
observation under the repository lock. Only `merge-verified`, exact canonical
commit/tree/parents/PR and develop ancestry qualify. Repair, unknown or a forged
status summary cannot stamp a fact. No new API request or merge replay is used.

The append-only public fact is `by-operation/<operation hash>.json`, UID 984,
mode 0444, schema `offmenu-accepted-project-source/1`, with exactly repository,
branch, head, tree, parents, base, candidate_head, pr_url, operation_id,
unit_sha256, packet_sha256, policy_sha256, helper_receipt `{path, sha256}`,
previous and integer observed_at. Previous is an immutable `{path, sha256}`
fact reference or the first `offmenu-accepted-project-source-seed/1` marker
containing head, tree and the fingerprint of the Root-sealed descriptor.
`latest.json` atomically points to the fact as
`{schema: offmenu-accepted-project-source-pointer/1, latest: {path, sha256}}`.
Facts never overwrite; repeated observations retain the first receipt/timestamp
and cannot rewind the pointer. The chain is bounded and anchored at the sealed
seed. A partial write or broken chain holds for reconciliation.

The optional outer helper result facet is `accepted_source: {reference, fact}`;
the original terminal publisher response stays unchanged. Outer observation
only reads an existing fact. The legacy fixed original operation does not emit
or downgrade a source seed.

The fixed async accessor
`native_harness_runtime.verified_canonical_source(current, issue, binding)`
returns exactly `{fact, evidence: {path, sha256}}`. It pins the installed owner
policy accessor before import, reads the publisher-owned fixed fact, validates
custody, digest and seed chain, and correlates the actual selected operation,
unit, packet, candidate, base, tree and integration policy. The normal outcome
owner consumes this evidence; writable coordinator projections are not authority.
