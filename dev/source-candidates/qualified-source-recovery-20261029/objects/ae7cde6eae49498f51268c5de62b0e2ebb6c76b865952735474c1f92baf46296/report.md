# Worker25 nightly tooling delta — 17 October2026

DONE_WITH_CONCERNS. The unmodified existing build passes in an isolated source-pinned snapshot. No new project-source defect was found; this is practical tooling evidence, not a product/readiness gate.

Source: locally observed develop5f5bdb6ae716cbf80fab1e174d1af2e354468ead, identical to Worker31's source. Its six direct dependency version/root-lock matches,66module syntax/import evidence and five Python syntax reads are reused rather than replayed. No fetch or active UI working-tree content was examined. Snapshot includes139tracked build-source/packaged-asset files, plus a read-only dependency symlink; original corpora/private data are excluded. The only research file is the1636-byte packaged metadata manifest. Corpus entries are code-only engine/guard, not records.

## New actual checks

- Existing node scripts/build.mjs completed with exit0. Its i18n prerequisite passed inventory consistency and reported2074messages,376Arabic translations and1698missing; this is not Arabic completeness. No extractor/translation update ran.
- Build emitted15embedded assets. Eight generated JavaScript artifacts parse via node --check. Nine artifacts have byte-size/SHA256 pins.
- Extension ZIP CRCs pass; all five entries match the snapshot and the embedded base64 ZIP. Scanner WASM magic/version is valid and bytes match the already installed dependency.
- Generated source release stamp matches5f5bdb6. A minimal external detached HEAD-only Git metadata directory supplied the unmodified build's git rev-parse HEAD call. It is a build stamp, not another branch/worktree/history or proof by itself;139source hashes independently bind the snapshot.
- Only current build tools Acorn/esbuild were read back against locked versions; Node binary/package/tool hashes are retained. No installation, registry scan, dependency update or new tool configuration occurred.

Initial snapshot selection omitted corpus/assert-curated.mjs, then the server closure's corpus/engine.mjs and research/manifest.json. Both failed build attempts/logs are preserved as audit-tool projection mistakes, not product defects. Existing Worker31 root/caller graph identified the complete closure; only those code/metadata dependencies were added. Repeats were justified by projection corrections; the final unmodified build passed. All snapshot source hashes remain unchanged after the build; generated files stay under this owned snapshot.

## Limits and disjoint next action

No declared lint or format-check target is available in this source package; neither was passed. Vulnerability status and Sonar remain unassessed; the existing Sonar/Docker access dependency was not attempted. No browser/device/provider, actual source/country/rights/admission, active UI or runtime restart/integration/release was exercised. No new architecture/dead-code conclusion or deletion proposal was made.

The only proposed repair is to the owned repeatable audit procedure: project the existing import closure before a future on-demand build so code/metadata directories are not confused with original data. No product patch, translation task, shared build output, new scheduler, daemon, worker or blanket gate is proposed. Active UI,64repair,14review and all source/privacy/rights/actual-denial/production/CIX holds remain unchanged. Gateway can retain these new build/artifact pins alongside Worker31 evidence without delaying daily development.
