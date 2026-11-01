# Original identity source on an advanced target

The `identity-client-focused` owner may seal an optional
`binding.source_projection` to publish the original reviewed commit after
`develop` advances. The original head, tree, branch, validation operation,
receipt, review and native unit stay unchanged. `binding.base` is the current
API target; the source commit's parent is `source_projection.source.base`.
No new publication commit or validation of another source is implied.

The record has exactly `version:1`, `profile`, `source:{head,base,tree,branch}`,
`target:{base,tree}`, `merge_tree`, `outputs`, `unit_sha256`, `operation_key`,
`receipt:{path,sha256}` and `review_sha256`. Existing owner configuration and
binding fingerprints seal it. The normal owner must qualify the original native
unit, Journal receipt and review associations. The Controller's projected-only
prepare path recomputes the immutable Git proof from its existing protected
workspace before preparing publication: original single parent and outputs,
target ancestry and untouched output paths, exact deterministic merge tree,
and identical source/result paths, modes and blobs outside only
`docs/development/`, `tools/delivery/`, `tests/delivery/` and
`src/offmenu/delivery/`. The record itself is not proof or authority.

The publisher checks raw Git object hashes, original commit parent, source and
target trees, exact reviewed output delta, operation plan, branch and native
request association. API readback still requires the current target base and
original head. Canonical merge readback uses parents `[target, original head]`
and the separately admitted `merge_tree`. Sole ownership, durable intent,
unknown-effect reconciliation and API permissions stay mandatory.

Projected configurations pin and carry
`src/offmenu/delivery/identity_source_projection.py` through the existing source
closure. Default and release required file sets do not change. There is no new
binary manifest, runtime selector, key path, callback, repository path or job.
The fixed invocation helper retains the original native source hash. Config
installation, publication and integration remain the existing owner's actions;
source tests do not perform them.
