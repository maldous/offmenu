# Worker 12 Owner06 callback-source review

Date:2026-10-14, Australia/Melbourne. **CORRECTIONS REQUIRED; candidate remains unselected. Two P2 strict-validation findings.** Existing d100 producer scoped PASS and all preceding evidence preserved. Old9b31 source and Worker05-owned19076 remain selected; no producer/callback rollout or provider acceptance is authorized by this review. Production STOP.

## Exact candidate and reproduction

Candidate `4397063e3036db07442947fdf7169885801b5eed`, parent `9b31f7d4de21dd30add0c49b038e5ac31413ec5d`. Exact Git binary diff SHA256 `71b7f5998b933e8c620bc7d5315334ef53d1411cc9f3020daa7ec4dbac0a5bd0`, candidate.diff. Exactly four additive contract/test/doc/verification files; all16 original mock files independently byte-identical to parent (base-files-unchanged.json). Supplied verification JSON hash72979272324d24145b0ce63d8f1516204189352e553dde9fd0a8cd32e76834fc matches the committed bytes.

Immutable tracked-source snapshot `/tmp/worker12-owner06-callback-v4_10wwp` holds only selected mock source files/package metadata, with all hashes in snapshot-manifest.json. node_modules is a reference symlink to existing shared dependencies, not a copy/install. No author checkout source or live runtime was imported/mutated by the new pure-function probes.

Actually-run: `node --test dev/wiremock/validation.test.mjs dev/wiremock/callback-source-contract.test.mjs`, **133/133 pass**, 133-tests.log. The unchanged128-case adapter matrix uses its own ephemeral loopback Node fixture server, closes it, and does not launch Java or contact Netlify/providers. It is synthetic source regression evidence, not real WireMock or callback-session acceptance.

Reviewer independent boundaries: **8/8 expected observations asserted**, independent-boundaries.mjs/.json/.log, zero I/O. Includes two reproduced defects; observation pass does not waive them.

## Findings

**C12-01 — P2 / medium: validated reply fields are re-read and getters can replace output.** Candidate dev/wiremock/callback-source-contract.mjs:41 validates `reply[key]`; :43 re-reads it for frozen tokenFields. Object.keys admits accessor fields. Original-probe input has an enumerable expires_in getter returning3600 for validation and86400 for copying. Observed:2reads, returned frozen expires_in86400. An access_token getter returning Alice during validation and Bob during output returns Bob access token paired with Alice refresh token.

Trigger/reproducer: independent-boundaries.mjs, first two probes. No HTTP/native/provider operation occurs; only a caller-supplied object exercises this API boundary. Impact: the claimed strict actor/lifetime validation can produce fields outside the checked native fixture contract, despite freezing the result.

Advice: validate and snapshot own plain data descriptors once, rejecting accessors/custom input behavior before invocation; return precisely the captured validated fields. Add zero-getter-invocation negatives and ordinary native JSON positives. No fix applied. Ordinary HTTP JSON replies pass; this does not claim parsed JSON contains executable getters or a current shipped callback is exposed.

**C12-02 — P2 / medium: coercible actor inputs can make a mixed pair expected.** Candidate :20 accepts actor IDs by Object.hasOwn property coercion without requiring a primitive known string; :40 calls identityToken with the original actor object, coercing it repeatedly. A Symbol.toPrimitive fixture returns Alice for the first3 coercions and Bob for the fourth. Passing an Alice access token/Bob refresh token now succeeds; output retains object-valued actorId. Observed4coercions and the mixed pair.

Trigger/reproducer: independent-boundaries.mjs, coercible actor object probe. Impact: unknown/ambiguous actor input hooks bypass the intended one-named-actor pairing boundary. This is a pure helper validation failure; native strict token endpoints remain unchanged and no native mixed grant was sent.

Advice: require actorId to be a primitive string equal to Alice/Bob/admin IDs before any lookup; use that captured identifier/actor consistently in request generation and expected-reply construction. Reject boxed/coercible/accessor-bearing identifiers without hooks. Both exported functions should share this check. Original16 files can remain unchanged; correction belongs only to the additive contract/tests/docs/evidence.

## Other boundaries checked

Primitive Alice/Bob/admin replies preserve exact native token fields and frozen output. Ordinary wrong/mixed actor tokens, changed3601/string expiry, missing/extra/state/provider fields, array/null replies and unknown string actors reject. Non200 numeric/string statuses reject matching fixed bytes. Literal IPv4 and IPv6 loopback origins pass; external/lookalike/localhost/HTTPS/credentials/path/query/fragment origins reject. Origin shape alone is not proof of an owned current port/receipt; caller must bind actual selected runtime.

The contract does no I/O or fragment construction. Native authorize/callback mappings remain14×501 across scenarios. currentSessionVerified=false, providerAcceptance=false, consent/accountLinking=unknown are truthful. Fixed fixture bytes cannot establish fresh response provenance, revocation/session validity or real OAuth consent. Worker04 same-tab intent/15-minute/consume-once/URL-scrub responsibilities are documented metadata, not implemented or independently qualified by this module. Cryptographic state/nonce, real provider callback and native/device bridge remain outside scope.

## Existing58 coordination payload / selection gates

For root/06/58: keep4397063e unselected. Owner06 should correct only C12-01 captured descriptor-backed reply validation and C12-02 primitive actor binding, preserving16originalfiles/501 semantics. Return immutable correction pin, focused before/after proof and truthful unknown/session flags. This adds no redirect or native callback success endpoint.

Worker58 should retain source-selection/per-request custody gates and distinguish pure helper PASS from actual installed-SDK/native callback execution. After independent corrected-source verdict, Worker05 owns any fresh source/runtime selection. Existing19076 must not be silently relabelled with this candidate; old9b31 and d100 PASS stay valid for their original scope. No duplicate reviewer/runtime audit or additional coordinator is needed. Concrete payload retained here; no messaging-tool action taken without the already-requested direct human authorization.

## Preservation

Own branch/HEAD/index and primary main/HEAD/index before/after stable; no tracked edits (custody-before-tests.json / custody-after-tests.json). d100 PASS artifact hashes verified unchanged (preservation.json). No source edits, process takeover, live19076 contact, catalogue19166 operation, Netlify/provider call, publish/deploy/merge, install, additional agent/session/worktree or bulk copy. Test environments stripped inherited GIT_*. Mandatoryauto_review and actual controls unchanged.

Review ready for Morgan's correction routing, not acceptance. Same Worker12 available for exact follow-through.
