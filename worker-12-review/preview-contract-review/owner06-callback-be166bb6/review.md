# Worker 12 C12 correction follow-through

Date:2026-10-14, Australia/Melbourne. **PASS — scoped pure callback-source contract review. C12-01/C12-02 resolved; no new reportable finding in this exact delta.** Candidate remains unselected until root/owner05 adoption. Existing d100 producer PASS, old9b31 selected source and live19076/19166 are unchanged. No runtime, callback/provider/session or production acceptance issued.

## Immutable pin and scope

Corrected `be166bb61483825498094d496e2caed9d8b775bb`, parent `4397063e3036db07442947fdf7169885801b5eed`. Exact Git binary correction SHA256 `4ec5674cbc3b2757e0a4e17efdddd7b21e00a04c6a949cc9f63e9f5ce702e39c` matches supplied hash; retained correction.diff. Only four additive callback files change. All16 original mock files byte-identical to9b31f7d4de21dd30add0c49b038e5ac31413ec5d, independently verified in base-files-unchanged.json. Verification JSON SHA256 b87db422b9cdcfd5a5ef875cf10e70fbcc5c75c8b1b7640be6903df6d6636ecc matches committed bytes.

Selected immutable source snapshot `/tmp/worker12-callback-correction-80tjxmnk` with file hashes in snapshot-manifest.json. Dependencies referenced by symlink to existing shared node_modules; no dependency/JAR/corpus copy or install. Only source-fixture files extracted, no author checkout modifications.

## Precise resolutions

C12-01: ownDataSnapshot captures each exact enumerable own data descriptor value once; reply and metadata proxies/accessors/hidden or symbol extras reject before reading hooks. Comparison and tokenFields output use the same captured fields. Original lifetime/access-token getter fixtures now reject with0reads. Plain and null-prototype native replies retain exact primitive tokens/type/3600 lifetime, with frozen output unaffected by subsequent input mutation.

C12-02: actor helper requires a primitive string before Object.hasOwn lookup. Both exported functions reject the original coercible actor/mixed-pair input without any Symbol.toPrimitive calls. Known primitive Alice/Bob/admin sources remain correct; boxed/coercible IDs cannot redefine which expected actor fields are paired.

Node types.isProxy is checked before reflection. Independent reply/metadata proxies produce0traps; metadata accessor and coercible-origin probes produce0hooks. This is a **Node fixture boundary**, not a browser/general-JavaScript claim that proxies can always be identified without traps. Existing adapter/miniflare and the new node:util dependency require qualification in the intended caller runtime; no browser import/install assumed.

## Actually-run proof

- `node --test dev/wiremock/validation.test.mjs dev/wiremock/callback-source-contract.test.mjs`: **137/137 pass**,137-tests.log (9 callback +128 unchanged baseline).
- Unchanged original vulnerable-observation script run against corrected snapshot: exits1 on immediate rejection of first accessor. Exact outcome/stderr retained in unchanged-old-probes-outcome.json/.log. This expected old-assertion failure is not misreported as an independent passing suite; original script untouched.
- Independent corrected expectations using the same exploit inputs plus proxy/metadata/snapshot boundaries: **11/11 confirmed**, independent-boundaries.mjs/.json/.log, zero I/O.

Old baseline matrix uses an owned ephemeral loopback Node fixture server and closes it; it is not real Java qualification and makes no Netlify/provider calls. Pure callback probes use no transport. No live19076/source adoption or19166 contact.

Independent positives/negatives retain primitive actor/token pairing, wrong/mixed ordinary actors, scalar/type expiry changes, exact fields, missing/extra shapes, non200 statuses, IPv4/IPv6 origin positives and external/credential/path/query/fragment negatives. Frozen state flags remain currentSessionVerified=false, providerAcceptance=false, consent/accountLinking=unknown, callbackEndpointStatus501.14native authorize/callback mapping defaults remain501.

Reproduce in selected snapshot with all inherited GIT_* removed. Independent script runs as `node /absolute/path/to/independent-boundaries.mjs /absolute/path/to/snapshot /absolute/path/to/this/artifact-directory`. No Git-writing fixtures/repos and no process control of existing runtimes.

## Existing58 handoff / remaining adoption gates

Exact be166bb source is eligible for root/05 selection following this scoped review. It is **not currently selected or loaded** by that verdict. Root must explicitly select it;05owns any fresh overlay/runtime/receipt generation and its source/process qualification. Preserve9b31/f77/2fd/d100 receipts and do not relabel existing19076 with new source identity.

Worker58 can consume this pure-contract review as its source gate, then bind actual selected tokens/native fresh response/user-refresh/session checks and Worker04 same-tab intent guard separately. Updated caller/producer integration requires exact reviewed pins, fresh per-request ownership/admission and actual execution evidence. No duplicate reviewer or audit is required to re-prove these pure input defects. Existing d100 PASS remains valid for its original9b31 inputs, not automatically extended to a new composition.

Newly observed HTTP200 and current live actor/revocation still require actual source evidence; matching fixed bytes cannot establish a session.15-minute same-tab guard, SDK fragment handling/scrubbing, real OAuth state/nonce, consent/linking, bridges and provider/native/device flows remain outside this module and this review. Production STOP, no native redirect/callback success fabricated.

## Custody

Original C12 report/reproducers and d100 PASS manifest hashes verified unchanged. Own branch/HEAD/index and primary main/HEAD/index stable; tracked state clean. Only authorized new review artifacts written. No source-owner edit, settings/security/Actions/PR/publish/merge, extra session/worker/agent/worktree, bulk data, dependency install or live-process action. Mandatoryauto_review and actual supplied controls preserved. Concrete existing58 coordination payload is retained here; no external messaging authorization inferred from a task relay.

Review complete; Morgan owns selection/adoption. Same Worker12 available for bounded follow-through.
