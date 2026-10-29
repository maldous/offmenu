# PR 5 test dependency correction

Root assigned Worker25 the P1 finding at
https://github.com/maldous/offmenu/pull/5#discussion_r4272399151.
The retrieved comment had no reply or competing correction owner. PR5 and its
prior review/proof history remain unchanged. Earlier local passes did not prove
clean-checkout portability; this document does not retroactively claim they did.

Branch: `fix/intake-history-test-portability-25-20261015`.
Fresh locked fetch exited 0 at 2026-10-14T15:45:33.815488+00:00, base
`35bedc68162dd8ffc48824ef08afb4dbce9d0c5d`.

## Reproduction and correction

Two independent disposable shallow, single-branch clones of private published
origin/develop at the exact base were created with blob filtering and a sparse
checkout of package.json, the focused test and its 13-file reviewed runtime
closure. Neither clone shared the primary Git common directory. All Git and Node
subprocesses stripped inherited GIT_*; no repository settings/hooks were changed.
Disposable checkout manipulation used explicit `git -C` paths. No source corpus,
dependency links, installs, credentials or shared owners were copied.

Baseline clone: helper commit `59d8bca52cc3281741862d17f2579668d6e6140d` was
unavailable. `node --test tests-web/intake-history-owner25.test.mjs` exited 1 during
module initialization: git show could not resolve the source path/ref. Zero
authored cases ran. This confirms the required npm-test included file was broken
in a published checkout, even though the author's shared-object checkout passed.

Correction: replace the subprocess/data-URL load with a relative static import of
`tests-web/fixtures/intake-entry-model-owner25.mjs`. This is an exact test-only
snapshot of `public/intake-entry-model.js` from the original full source pin above.
SHA-256: `eec623d6f49ac0b7a57f97af550198eed909347ff4ce9d4b3c327515d294655a`.
The source is Worker25-authored OffMenu code, with original commit provenance
retained. No remote response, raw dataset, production dependency or inferred
model acceptance is introduced. The fixture lives under tests only; production
adapter continues to require an explicitly injected reviewed model.

Fresh second published-base clone: applied only the authored test correction and
declared fixture, confirmed the old helper object remained unavailable, then ran
the same exact focused Node command. Exit 0: all nine cases passed, comprising the
six required existing cases plus three provenance/unknown/partition fixture
qualification probes. No case was skipped or excluded. No dependency install,
common-dir object access, broad npm suite, or production model qualification was
used. These were current-tree source checks, not a declaration of hermetic Node
runtime qualification. Node was v24.16.0.

The adapter runtime file is unchanged. Fixture hash is checked in the test;
unknown amount remains null, source lineage retained, top-level nutrients reject,
and planned/consumed-zero/unknown buckets remain distinct. Existing18 is reserved
for independent correction review after its own source fix; actual helper fixture
qualification and current-develop composition must be reviewed before merge.

## Custody and scope

Only the unique fixture, focused test and this note are owned. Primary main remains
`8652b312ce7989c5e4f2d49ae765d5d8daf5841d`, primary index SHA-256
`4332ef16a3df2cd9032b4f099a74425a111bd2e5448e0f5066c5f3f3cb54f389`.
Original composition branch24d75fa, original candidate53853, helper59d8bca,
dataset4168ae2, PR5 and review artifacts remain retained. No endpoint/schema/locale
or session/consent adoption, production deployment or whole-feature acceptance.
Result pin/backup/readback and review gate are reported separately to root.

## Follow-up: CRLF checkout checksum

PR7 automated review on original correction866cce8 found that core.autocrlf=true
converts the fixture's working bytes and breaks its raw-byte checksum. The fixture
Git blob remains exact source bytes. Test checksum now canonicalizes CRLF to LF
before comparison; content changes remain detectable. No shared attributes or
repository configuration are changed. The original accepted pin remains retained
as parent; this follow-up requires a fresh independent review and root acceptance.
An isolated published-branch sparse clone checked out with command-scoped
core.autocrlf=true confirmed actual fixture CRLF. The original focused test exited
1; applying only the corrected test (also CRLF) yielded nine passed, zero failed.
Disposable checkout configuration did not change any owner/shared Git settings.
