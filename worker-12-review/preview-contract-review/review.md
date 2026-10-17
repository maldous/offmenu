# Worker 12 independent preview ownership review

Status: **CORRECTIONS REQUIRED BEFORE CONSUMER ADMISSION**. Actual Worker05-owned overlay/preview identity verified; this does not grant combined flow, provider/auth/profile/browser/device or release acceptance. Morgan owns disposition.

Pickup: same native Worker12 and preserved dataset branch/HEAD. Locked fresh fetch exit0 at 2026-10-14T10:14:57.183672+00:00, origin/develop `908ca373dfc918f2e33fd5e44260879577bed5c5`. No implementation branch, author file change or server takeover.

Producer pin: `f77bfafb4672e5e0660f1f66efbec0502ec493a8`; base `908ca373dfc918f2e33fd5e44260879577bed5c5`; exact Git binary diff SHA256 `018808ff1ecc0e038f5a74b706522e5a643300cc08d0469562b73e6231c5265b`, retained in producer.diff. Consumer pin: `e8c3e40e8b518681671392712b7f5661a1f4a4bf`. Selected source-file hashes in producer-pin.json / consumer-pin.json; exact files compared to pinned Git bytes before/after execution. Producer committed while initial inspection was underway; initial working-source observation was not treated as a completed immutable candidate. The final selected pin was re-read and verified. Tests import those unchanged source files by read-only reference, with isolated temporary descriptor/receipt fixtures; no server start/reset/stop or owner-file write.

## Verified owner/provenance and live identity

All 122 declared input files matched their Git blob hashes and materialized bytes, with part-to-author pin checked independently. Actual mock owner05/session is distinct from immutable source owner06 at `9b31f7d4de21dd30add0c49b038e5ac31413ec5d`. Java PID `695978`, boot `2d41e7a9-0baa-4e0c-afc8-c6966a8b6f5d`, birth `1923192`, actual /proc cwd `/home/user/src/offmenu-data/dev-preview-20261014/workers/worker-05/interactive/0b18df2e-282a-42d7-aa3e-187b304b4383/mock`, bind127.0.0.1/port19075 and argv matched custody. Its inherited CODEX_THREAD_ID is owner05. Health GET token matched without retaining the token. JAR path/version/SHA512 matched current referenced bytes and lock; WASM dependency hash, artifact SHA256, runtime-source and native-custody hashes matched. Native mapping-file hashes retained. No dependencies/corpora/JAR copied.

Preview PID `729700`, birth `1982544`, actual owner05 cwd and port18795 matched its ready receipt. /__dev/status owner/run/state/source/app/artifact/pins/composition matched, interactive true and productionCredentials false. Only fixture-health and status GETs executed. Identity176/reset2 qualification is **producer-recorded** at `2026-10-14T10:06:00.290Z`, not rerun by reviewer. Runtime and source readback is point-in-time evidence, not a lease lasting after it changes/stops.

Digest distinction: input composition `73c906be308a2714ae0fc5695b3dfaf4184f70b1c0f5897ce8a992f675a8b243` identifies selected inputs; live descriptor `a0a20164cafc39c75c04a80ec17bcd73d2d3c4a11d67152ba5b74f686ac30567` is what lifecycle/status compositionSha256 exposes. Neither is the preview receipt hash `ac91eee25979280ba84bb97ade0d9dc67f3b2da03fcf5974753f28c304283dde`. Consumer must compare the correct layer rather than substituting hashes.

## Findings

**P12-01 — P2 / medium, missing task-grant/action admission checks.** Producer interactive-preview.mjs:81 checks boundSession/root/pins/reviewer/composition/artifact but omits sourceThread, grant reference and permittedActions. Disposable fixture preserved every checked field while setting sourceThread to unrelated-task, grant empty and permittedActions to real-provider-flow. Rehashed descriptor was accepted by loadInteractive. Reproducer: producer-boundary-probes.mjs, missing-or-unrelated-task-grant observation. Impact: session/hash equality can be mistaken for task/action authorization. No real provider request occurred; source whitelist still blocks unsupported routes. Enforce independently selected grant/task reference and permitted synthetic action scope; controls and JSON hashes are not human approval proof.

**P12-02 — P2 / medium, qualification/dependency claims not checked by admission.** interactive-preview.mjs:82 validates owner/source/status and assertion counts; :84 checks native receipt hash, process health and six mock source files but does not validate declared qualification time/version/JAR hash/runtimeSource hash. Fixture rewrote qualifiedAt to 2000 (before this2026 process), version wrong-version, JAR SHA512 zeros and runtimeSource SHA256 zeros, then rehashed mock/descriptor. loadInteractive accepted it while real process/source bytes stayed unchanged. Reproducer: stale-qualifiedAt-and-false-dependency-claims. The live JAR happens to match in our independent readback, but current admission does not enforce the contract's JAR/qualification claims. Compare fields to lock/current dependencies and native custody, validate time/source/birth consistency, and bind preserved actual test/audit evidence. This is no claim that a token/signature alone could prove qualification.

No owner source corrected by this reviewer. Wrong owner, wrong bound session, wrong composition hash and stopped status all refuse in independent probes.

## Actually-run proof and scope

- Producer focused tests:2/2 passed; producer-focused-tests.log.
- Independent producer boundary observations:7/7 asserted, including two demonstrated acceptance gaps; producer-boundary-probes.json/.mjs/.log. Temporary descriptors under /tmp, source/runtime untouched; health GET only.
- Consumer admission negatives:3/3 passed, zero fetch calls and zero passed flows; consumer-admission-probes.json/.mjs/.log. Rejecting gate executed before each of four HTTP group entry attempts. External target and missing gate also refuse. No fabricated auth response or fake flow pass.
- Immutable overlay/JAR/WASM/process/status readback: overlay-readback.json / preview-readback.json.
- Minimal paired admission requirements: admission-contract.json, marked corrections-required rather than accepted.

Worker58 presently requires an admission callback before every request; implementation of an exact reviewed callback is still a dependency. Its HTTP helper covers four groups; corpus/public/localized, lifecycle freshness and no-egress require separate actual transport/audit qualification. No auth, care, community or admin fixture writes were performed here. Prepared shape tests cannot stand in for pinned fixture-token provenance or production role/Google/account grants.

## Concrete communication draft

For05: retain actual owner05 plus source06 provenance. Correct P12-01 task-grant/source/action checks and P12-02 dependency/native qualification consistency, preserving exact inputs/native receipts/runtime; publish an immutable correction pin and focused positive/refusal proof. No process relabel/adoption/restart requested.

For58: keep all flow groups unaccepted until corrected producer pin and independently admitted ready packet. Bind owner05/native birth+cwd+loopback port, source06 hashes, JAR/mappings/dependencies, task grant and both digest layers before every request. Recorded176+2 and our readback do not themselves execute your four HTTP groups or qualify the other four.

For root01a137cf-2242-761d-8fd7-6e6fc5658013: owner05/06 provenance distinction is correct and actual live readback succeeds; exact producer `f77bfafb4672e5e0660f1f66efbec0502ec493a8` has twoP2 admission gaps. Consumer `e8c3e40e8b518681671392712b7f5661a1f4a4bf` correctly fails closed with a rejecting callback; final paired admission requires corrections/re-review. No release/normal publication review approval issued.

Mandatory supplied controls preserved: unrestricted danger-full-access filesystem, network enabled, reviewer auto_review; separate approval-policy value and named profile unavailable. Grant authority is separate. No agents/sessions/worktrees, bulk/source copies, force/settings/security/Actions, merges/publication or owner process administration occurred.

## Final preservation/readback

Mapping factory/native custody equality verified independently:310 current mapping files match the exact pinned factory after its known health-identity substitution; token omitted from artifacts (mapping-identity-readback.json/.log/.mjs).

Own dataset branch/HEAD/index, main/primary HEAD/index and all prior review artifacts remained unchanged. Local develop moved concurrently from908ca373 to5f5bdb6ae716cbf80fab1e174d1af2e354468ead, observed by ref/reflog at2026-10-14T10:22:39Z. This reviewer ran only the authorized locked fetch and read-only Git commands; no local-develop update occurred in reviewer commands. Reflog evidence establishes timing, not the actor/authorization. The review remains bound to the explicit immutable producer/consumer pins above; no freshness or acceptance inferred from that concurrent movement. custody-comparison.json records the distinction rather than claiming develop stayed stable.

The concrete findings for05/58/root are prepared above. No messaging action has been taken: the messaging-tool contract requires direct human authorization and says another task's relayed request alone is insufficient. A direct authorization question has been presented; all unaffected review work is complete.
