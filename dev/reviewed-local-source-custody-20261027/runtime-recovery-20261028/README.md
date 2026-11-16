# Reviewed recovery runtime and production source custody — 2026-10-28

Additive source custody only. Original producers, accepted manifests, source datasets, incomplete legacy outputs and prior custody remain unchanged. This directory is not an application deployment root or an instruction to execute jobs.

## Recovery variants
- `bulk-serial`: approved bounded serial recovery variant cb7355ecc5d62e34fc68b6dcbb1ab6828ddc7c3b6dccb7f5fa4ee9c79deb41f6; not a replacement of the original producer pin.
- `bulk-parallel`: separately reviewed bounded pool variant 2fde257a76102f192972cefe19d6fc908649be766fbf27c338d3c0fe8986d544, distinct new run-owned output. Parent alone journals committed assets; source comparison remains required on adoption.
- `places-v2`: exact accepted input-format correction; catalog helper 51d7523c6fde3a661b36a92c9b3e37357b5c11aa692c9cb12c0e23190a4cbac5; upstream manifest 337b441475cfb426ee93ca4bb0e9e4042355ce9a0e670f9c3a73eb650e2254b5.
- `driver-v2`: ede23e56ef8e67b13dc75f5bd321bbb3f1dd3bf30ac1bb65b22c61231d6d07ff and its exact v2 tests only. Upstream source manifests are provenance, not publication allowlists: obsolete driver v1, stale candidate README and first-run plan are deliberately omitted. The root SOURCE-MANIFEST is the actual snapshot inventory.

## Boundaries
One existing outer writer lock remains held while independent producer lanes use disjoint output roots. No Windmill replicas or host access policies are changed by this custody publication. CPU affinity and per-process address-space limits do not constitute aggregate cgroup enforcement. Memory-process accounting and aggregate disk admission are declarative/best-effort controls; reviewed producers retain output ceilings and the outer supervisor retains timeout, cancellation and descendant cleanup authority. No automatic replay of a prior fan-out run.

## Evidence, not completion
The preserved serial bulk checkpoint verifies 513 assets / 513,000 packets: 413 byte-identical adopted retained copies and 100 fresh outputs. The original truncated legacy tail is unchanged. Places verifies 275,000 unique source identities: 274 closed packets containing 274,000 resources plus one buffered packet containing 1,000 resources. Neither has a final manifest; qualification is false. Counts use different granularities and must not be added as equivalent records.

The timestamped dual live receipt establishes two running lanes only, not terminal success, cleanup, throughput improvement, complete manifests or package qualification. Terminal evidence now accompanies the historical live receipt: both lanes exited zero; outer job 01a18035-d8ac-16c0-a167-f69b15bf84cb completed with child_tree_gone=true in about180 seconds. Parallel bulk has400 source-compared copied assets /400,000 packets in its separate output; the frozen serial513 is preserved and these counts overlap, not additive. Places advanced to525,000 identities, including524,000 closed schema-validated resources and1,000 durable buffered resources. Both producers paused, neither has a final manifest. This initial proof used one process in each lane, not yet the bulk2-worker pool. No pipeline completion or corpus production-serving claim.

## Application custody
`app-reviewed-source` contains the exact reviewed final three-file application changes, four focused test files and three scoped patches, not a complete standalone build checkout. Final app.js source SHA256 is 55bc0086192208e7fe0892ef7fe8a0d34c67f293290c48f33b7597929f997ee2. Deployment receipts 189/190/191 were supplied by the production integrator and retain limitations: no authenticated end-to-end/device/GPU acceptance claim. Version191 is served at 100%; all211 other modules unchanged. The compiled served app hash differs legitimately from source bytes. No deployed asset carrier, bindings, credentials or raw data are included.

## Security and delivery
The included narrow GitGuardian triage concerns four fixed OS-account lookups, not passwords. No detector suppression, credential rotation or history rewrite performed. Keep scanning enabled.

No Actions dispatch/retry, workflow edits, Foo push, raw dataset publication or production mutation occurs in this commit. GitHub direct tree/commit and nonforced leased ref update preserve all earlier branch content. Workflow trigger definitions are checked before publication; exact remote content-address hashes and Actions run count are verified afterward.
