# Protected native source-reference integration

## Delivered source change

`native-reference-integration.patch` implements the missing protected Finish/model
path against actual Worker13 source custody commit
`7dd3ed8cf25b345b41edeaa4367735c0bda66444` and exact source dependencies already in
foundation origin `d6267b36bba7db669561293bd191980e1a6b567a`.
`integration-manifest.json` identifies all seven changed source paths with exact
preimage/postimage byte lengths, SHA-256 and Git blob hashes.

- New `public/source-identity-handoff.mjs` retains the complete source observation,
  source-rights notice, qualification/input/source-document pins and exact lexical
  identifier in a distinct native reference. It calls the recovered strict client
  validator rather than weakening or duplicating its observation parser.
- Protected scanner Finish handles explicitly chosen mixed phase/native records.
  Choice membership, query/generation and fixed selection pins are checked. No row
  is silently discarded, converted into a phase record, or automatically chosen.
- Model, checkout, kitchen import and operation-receipt replay preserve the native
  reference. Source-only facts remain unknown/false. Initial quantity is `null`,
  ingredient is `unmapped`, and review is required; no package/full-pack assumption
  is introduced. Final stock requires a positive manually recorded amount. User
  inventory annotations do not change source normalization/qualification flags.
- The HTTP success envelope now exposes `status: result.status`, which the actual
  recovered strict client requires. This is an envelope compatibility correction,
  not a new admission, runtime grant, reader interpretation or route.

The separate mixed handoff has a 64 KiB UTF-8 bound and the existing maximum of 20
items so it can retain full references. Existing public/foundation handoff schemas
retain their 3,000-byte bound. Guest Finish remains Map-only. Supported barcode
interpretation/typed-identifier code, leading-zero handling, existing foundation
validator, phase precedence, identity client and composer remain unchanged.

## Exact boundaries and dependencies

Actual `source-identity-selection.mjs` remains byte-identical and exports `null`.
No actual selection/admission pins have been supplied by these recovered source
bytes. Native-reference operations therefore fail closed until the operator binds
an actual eligible immutable selection through the existing contract. Synthetic
pins in the test are confined to a disposable local test copy and are not a
candidate selection.

No credentials, raw datasets, runtime authorization grants, source acquisition or
external provider lookup are part of this patch. Test observations are explicitly
synthetic. Source-rights strings are the existing contract's retained notices.
This source artifact does not establish production admission or normalized-food
coverage. In particular, 2,574 selected identity claims do not mean 2,574 normalized
food records; current reviewed contract state remains NOT_ADMITTED_NOT_SERVED.

`base-dependency-manifest.json` records the 26 exact test/preimage source inputs,
with actual custody or immutable origin locations. `base/` and `overlay/` are local
reproduction support, **not complete deployment worktrees**. Do not copy either
wholesale into canonical source or a deployed module: the historical R8 binding
used as a preimage must not overwrite newer selected R9/all15/alias/cover work.
Only the seven listed deltas belong to this change. The production composition
lane must map them onto the actual current module graph and preserve untouched
current183 module bytes/auth/routing/containment.

Optional `pr139-http-status-type.patch` adds the same `status` field to the exact
`SourceIdentityHTTPSuccess` declaration from draft PR139/commit
`cc7811f9fc0d4f1555bf88919436c3b25e62102f`. Apply it only if that declaration artifact
is adopted too. It is not an eighth runtime-source change.

The remaining documentary reference for actual admission/count provenance is
`.../worker00/private10300-local-integration-20261026/source-identity-consumer-candidate-v1-20261027/r2/focused-review-handoff-result.json`,
SHA-256 `1f88170ad4b562e58ff824a39826067723da041a156b672a7d785861a54cb99a`.
Its bytes/size are not present here. Do not infer its contents or use that SHA as
an admission. This is a concrete metadata dependency, not a new test/delivery gate.

## Focused checks already completed

- Nine new focused integration tests passed: explicit mixed choices/full rights,
  leading-zero/native/invalid exact source claims, unknown quantity/manual final
  stock, full-reference persistence and idempotent/conflicting Finish, fail-closed
  selection/provenance/choice checks, actual protected Finish handler, actual app
  import handler and auto-accept, and real reader/HTTP output through recovered
  strict client.
- Twenty existing reader/HTTP tests passed unchanged.
- Syntax checks passed for all seven changed source files.
- `git apply --check` succeeds against the exact `base/` preimages.

Logs are `focused-integration-tests.log` and `existing-reader-http-tests.log`.
This is not a browser/camera/WASM test, current183 module build verification,
production acceptance or deployment. No GitHub Actions or remote executor ran.

For focused reproduction, materialize `base/` from its manifest, copy it to
`overlay/`, apply the patch there, then from this artifact directory run:

```
node --test native-reference-integration.test.mjs
node --test overlay/dev/source-identity-consumer-candidate-20261027/source-identity-{reader,http}.test.mjs
```

The test creates and removes its own temporary copy; it never edits the actual
null selection or recorded foundation binding in the delivered source overlay.

## Handoff ownership

Importer owns GitHub custody writes; preserve this patch, test and manifests as
source-only integration artifacts without changing live paths. Parent/current
production composition owns adoption, actual selection/bindings and eventual
production review. This lane neither uploads an executable production version nor
changes runtime, main, deployment, security settings or source datasets.
