# Pinned typed-context consumer v1 — source-review candidate

This disjoint wrapper invokes the existing qualified
`SourceScopedConsumer.lookup(..., include_candidates=True)`, then the frozen
`typed-context-adapter-v1.adapt()`. It neither edits nor replaces those modules.
It supplies its own reviewed bindings after verifying existing local metadata;
the caller does not supply manifest or code hashes.

## Public entrypoint

```python
with TypedContextConsumer(base=existing_confined_base) as consumer:
    typed = consumer.lookup(source_id, release, namespace, lexical_value,
                            include_candidates=True)
```

No literal True opt-in: return no records without opening packages or indices.
The four exact source-key strings go only to the existing reader. Missing and
ambiguous keys retain `callerStatus` and empty records; there is no text/name
matching, fallback lookup, external network or identity admission.

## Verified upstream

The confined default base is the already-existing
`/offmenu/data/.offmenu-platform/corpus-recovery-20261028-v1`.
The corresponding source metadata inspected in this executor was actually at
`/home/user/src/offmenu/data/.offmenu-platform/corpus-recovery-20261028-v1`.
No alias, mount or input copy was created. All paths beneath the chosen existing
base have fixed package/source-relative names, and aliases/symlink traversal are
rejected. The actual exercise must use its existing confined namespace.

1. Read and byte-verify the exact reviewed source, structural and basis manifests.
   Require completed candidate-only packages, matching normalized selection,
   exact producer code pins, same selected schema/contract byte pins, native
   selection and the two expected consumer-index/proof pins.
2. Read the unique manifest-listed `contract.json` and `schema.json`; verify both
   manifest-listed byte sizes and pinned SHA256 values. Parse exact contract
   bytes and compute its canonical digest using the producer's JSON encoding.
   The canonical contract digest is
   `3c3397af8c735cf19eef98f88ddd4da9ce23602c46ec97b4c67561fa15fc3bf1`;
   it differs from the byte digest
   `b4fa5afb2f8cc77326299b55ccd75b93f121e807317fdc1f9953709e98faa0aa`.
   This was computed from the actual selected 46,420-byte contract, not a fixture.
3. Verify exact retained code bytes before compiling fresh local module objects.
   Bind the caller's local imports to verified producer modules; restore the
   producer's sys.path insertion and do not replace global sys.modules entries.
   Verify selected basis producer sources but do not rerun their derivations.
   The frozen adapter's byte SHA is
   `d85a499493f982bec60af67e2588290f56d74b50a0cba03602de083b26a16e8e`.
   This loader executes trusted pinned code; it is not a sandbox for foreign code.
4. Hold nonblocking shared locks on the two existing derived-package
   `.writer.lock` files, opened read-only. The retained reader byte-verifies both
   immutable SQLite indices, uses its existing query-only readers, and verifies
   selected normalized/sidecar asset bytes, packet bindings, exact identifier/
   edge/source/citation/scope evidence. These guarantees remain reader-bound.
5. Call the frozen adapter with the verified manifest pins, verified code bindings
   and computed canonical contract digest. Annotate output with the exact
   `SourceScopedConsumer.lookup` upstream identity and selected verification scope.

Manifest/index pins are fixed in the new module:
- Normalized manifest: `8cd8abbf28f8fac11ccb73f336a91c7a5d90fbaff6ec1c864ec7b492f13da58e`
- Structural manifest: `83773291ac70931a110f60e872ae47a2bd470b5f397c709195dcf016c0bf0694`
- Basis manifest: `3520dff24e7b96635fd3d8f8cfa60664d03d5bd65709b547059cee10b306e1a9`
- Structural index: `5e6d5c14a26515632a56aac2ff128a12baaa6ec7d030703c368cc8c297a4c1ad`
- Basis proof index: `1691828696477efe932d6b3bfc1e20cbdc99ddf047da3e695067f40478e8c2cd`
- Schema bytes: `89ff701460e0c9c6e27c5d5ece7bd6868f26f55fc2aedd1d85c87b4408cf1f6c`

The pure adapter remains caller-bound. This wrapper establishes its particular
verified upstream reader and selection; it does not freshly re-prove the whole
corpus, source rights, culinary identity or nutritional comparability. Original
licence/attribution, unknown/zero, literal preparation, uncalibrated confidence,
and candidate-only/no-admission/no-aggregation/planning/application boundaries
remain unchanged. Ingredient/recipe links remain not supplied by this caller.
Previously retained immutable source, rights, qualification and namespace proofs
remain prerequisites; stale or unknown evidence is not upgraded.

## One-key exercise — pending independent source review

The optional CLI is solely a new integration exercise:
```sh
python3 -B typed-context-consumer-v1/typed_context_consumer.py \
  --base /offmenu/data/.offmenu-platform/corpus-recovery-20261028-v1 \
  --proof-root /offmenu/data/.offmenu-platform/corpus-recovery-20261028-v1/north-star-derived-20261028/typed-context-proof-v1-exercise-001 \
  --max-seconds 600
```

It selects at most one existing connected unique source key with the retained
index predicates and LIMIT 1, invokes the actual reader and adapter once, then
writes only `integration-proof.json` into a fresh create-only proof directory.
No real returned identifiers or values are printed/persisted by this entrypoint.
The exported report contains code/source/index/contract pins, typed-record,
unknown/zero/preparation counts, false admission/activation flags and canonical
output SHA256. No connected key produces an explicit zero-query non-success
status rather than a fabricated result. SQLite progress handlers bound SQL;
deadline checks surround verification and reading. Existing supervisor wall-time
and resource limits remain necessary, including during index hashing, gzip
reads and source loading; Python deadline checks alone do not preempt those IOs.

Run ONLY through the existing deployed `u/admin/foo_jobs_20261027` confined
supervisor with normal capacity admission: one worker, three overhead processes,
1,000 CPU millicores, 2 GiB RAM, 8 MiB output reservation and 660-second outer
timeout. Declare only selected packages/code as read roots and the fresh proof
root as write root. The supervisor must preserve its existing 70 GiB free-space
reserve; do not bypass a busy or refused admission. This wrapper does not submit
jobs, acquire capacity admission itself, reconcile other owners' reservations,
or create another data producer. The only write is its fresh aggregate proof.

Source review must precede that real exercise. At this handoff, only new focused
synthetic tests have run. The 24 accepted adapter tests and previous 64-key actual
caller exercise were not rerun. Wrapper tests reuse only the pinned synthetic
fixture builder from the frozen adapter tests, plus actual retained source-only
module loading; no populated indices, source rows or derived data are read.

There is no deployment, publication, app integration, source-rights grant,
external lookup, model call, paid call or runtime activation in this packet.
