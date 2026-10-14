# Pinned third-party compatibility

Status: **READY FOR MORGAN REVIEW**, not accepted, merged or deployed.

From the repository root, with the retained dependencies available:

```sh
node --test tests-web/pinned-third-party-compatibility.test.mjs
node scripts/run-third-party-compatibility.mjs
```

The runner prints a unique evidence location under ignored
`output/third-party-compatibility/`. To deliberately refresh the tracked receipt:

```sh
node scripts/run-third-party-compatibility.mjs --report docs/third-party-pinned-compatibility.json
```

The inputs are immutable commits, not the moving `main`, `origin/main`, current
checkout or an uncommitted application tree:

| Input | Commit |
| --- | --- |
| Main | `8652b312ce7989c5e4f2d49ae765d5d8daf5841d` |
| Third-party checkpoint | `84c4732af985965c3e5b00383acaa662bdd52ea6` |
| Common ancestor | `776c0f7e3ddd19bfc380dce6cfc3fbfdb434613f` |

The runner reads regular Git blobs and composes main leaf entries with only the
third-party delta from their common ancestor. Distinct simultaneous edits,
including delete/edit and mode conflicts, stop execution for review. Identical
edits can compose. It does not perform a Git merge, create Git objects, switch
branches or change either source checkout. The manifest covers the complete
composition, including retained main data-pipeline changes; those pipelines are
not executed by this native-feature check.

Only bounded code, schema and targeted-test inputs are materialized into a
temporary fixture. The tested fixture contains 124 pinned regular files,
1,383,682 bytes, below its enforced 16 MiB limit. Dependencies are referenced by
symlink. No checkout, external corpus or dependency tree is copied. The fixture
is removed after execution. The report records source tree IDs, composition and
input hashes, runner-file hashes, dependency versions, bundle hash, actual test
commands/counts and hashed TAP log references.

The Worker bundle embeds the composed HTML and compiled application,
data-workspace and service-worker JavaScript. Recipe data, nutrient details,
scanner binary and extension archive are explicitly synthetic/empty fixtures.
Consequently this is not a release build or corpus/transport acceptance.

## Fresh checks

The receipt records 107 targeted unit tests, five compiled Worker tests and two
additional pinned-main schema/runtime tests passing, with no failures, skips,
TODOs or cancellations. Three separate composition-runner tests pass. These
counts are fresh; the earlier 264/5/36 results remain historical evidence.

The additional checks use the **actual pinned main schema**, not just the
archived pre-care fixture. Ten additive migrations replay twice in SQLite and
local D1. Full synthetic private account state and sealed provider sentinels are
inserted before the first migration and preserved afterward. The migrated
schema structurally equals the fresh canonical schema. Compiled requests check
anonymous denial, forged user-metadata role denial, immediate trusted-role
revocation, wrong-origin denial, care-case ownership and private account/provider
isolation even for administrators. Existing targeted tests also cover community
moderation, delegated MCP scopes, CAS/audit rollback, service defaults and locale
headers/RTL/cache behavior.

Identity and provider behavior use synthetic fixtures. The added runtime test
uses Miniflare's outbound-fetch mock with networking disabled, following the
[Cloudflare testing API](https://developers.cloudflare.com/workers/testing/miniflare/core/standards/).
Local D1 uses the existing
[Miniflare D1 harness](https://developers.cloudflare.com/workers/testing/miniflare/storage/d1/).
No live provider, role, quota, account or paid-service qualification follows.

## Remaining composition and rollout gates

- Morgan owns independent review, recovery, integration and deployment decisions.
- Google IDP and Mock Services peer changes are not included in these two pins.
- Main corpus pipelines are retained in the manifest but not run; actual corpus
  transport, real data, scanner/extension and real-device/browser acceptance remain.
- Local workerd is tested with compatibility date `2026-08-06`; the deployed
  `2026-10-12` environment has not been qualified by this runner.
- Origin HTTP 403, subscription/billing/headroom, sender/domain/quota and trusted
  production administrator-role gates remain as recorded in the live readiness
  documents. No production migration or feature activation is authorized here.
- Historical preview Worker and four test logs remain missing; this fresh receipt
  does not recover or replace those artifacts.

No native runtime regression was demonstrated by these checks, so no native
care/community/admin implementation was changed.
