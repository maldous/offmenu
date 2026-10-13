# OffMenu local curation and static delivery

Latest expanded execution, 13 October 2026: `expanded-world-20261013` is live
with 9,829,099 curated records from 14 sources. Complete local collections now
include eight added national composition tables (AU, FR, GB, DE, NO, DK, CA, JP),
the current 3,796-page Wikibooks recipe category, 1,505 Wikidata business
references and 100 country guideline references. The original source archives
remain local. Every curated record passed structural and consumer checks;
country-matched examples and pagination passed through the live Worker.
115 JavaScript tests, 17 Python tests and the build pass. Private state and
the vault are preserved. The prior accepted static release is retained so
cached manifests can finish requests across publication switches.

All 1,303 registered source landing pages have been checked; 182 have download
leads. The 249-country execution report distinguishes observed records from
remaining source, access, rights and field gaps. These checks do not establish
complete country coverage, verified ownership or diet qualification. See
[expanded execution](expanded-execution-20261013.json) and
[country execution](country-execution-20261013.json). Older checkpoints below
retain investigation history and are superseded by this evidence.

Latest recovery outcome: Workers Paid was activated with the user's explicit
approval ($5/month plus usage). OffMenu now has a 10,000 ms CPU ceiling.
Default and oversized live queries passed pagination checks across the published
three-source curation after activation. The prior CPU/plan blocker is resolved.
OFF recovery also completed: 4,807,663 raw rows reconcile to 4,807,217 accepted,
61 duplicates and 385 quarantined; all 9,614,434 normalized records passed the
consumer exercise. OFF remains local, outside the currently published release.
See `recovery-2026-10-13.json` for current evidence; earlier notes below retain
the investigation history.

Recovery update, 13 October 2026: the repository and authenticated deployment
are restored. The three-source static curation is live on Netlify and enabled in
the Worker. Residual public D1 rows and raw caches are zero; the private account
aggregate and vault binding are unchanged. Live queries still intermittently hit
Cloudflare CPU exhaustion. The API currently rejects CPU settings as Free-plan
unsupported despite the user's paid-plan context. This remains unresolved;
see `recovery-2026-10-13.json`. The complete OFF archive is verified locally,
with normalization and full-record exercise continuing under a user service.

13 October 2026. This decision supersedes bulk D1 corpus replication and the
prototype Netlify query function. User instructions: manually trigger local
collection and normalization; host only OffMenu curation; use Cloudflare for
request caching. No source datasets in Cloudflare or Netlify.

## Boundaries

| Location | Contents and role |
|---|---|
| Local `/home/user/src/offmenu-data` | Complete original releases, source SQLite tables, normalized source records, quarantine, reconciliation and build indexes |
| Netlify `offmenu-corpus` | Static OffMenu selected facts, own IDs, unresolved/review decisions, discovery references, provenance, compressed search indexes and manifests |
| Cloudflare Worker | Read-only queries against Netlify curation; manifest and completed-query cache; checksummed static-file reads; no public corpus database |
| Existing `offmenu-users` | Private account/shared-kitchen state, authentication support and encrypted BYOC connections; public source replicas retired |

Netlify Functions, Edge Functions, Database and Blobs are not required for this
path. Static delivery still uses Netlify bandwidth/web-request allowances.
Cloudflare query compute/cache limits still apply. No claim of unlimited hosting.

Selected facts are explicitly source reported, not independently reviewed or
verified diet qualifications. Renaming a source record is not sufficient curation:
the separate publication projection drops raw source fields, ingredient wording,
unmapped source tables, contributor/proof metadata and original recipe bodies.
Recipe discovery references cannot be automatically planned or cooked. Product
ingredient matches remain unresolved. Licences and attribution remain attached;
OffMenu's schema does not remove upstream rights obligations.

## Manual process

1. Collect the entire permitted named release locally. Reconcile all rows and
   required related tables; preserve original archives and hashes.
2. Run `scripts/exercise-collection.mjs` over every normalized record.
3. Run `scripts/build-curated-corpus.py` against admitted local releases, choosing
   a new immutable output/version. The publication projection is
   `corpus/curation.py`, governed by `corpus/policy.json`.
4. Run `scripts/exercise-curated-corpus.mjs` over all curated output. This gate
   checks checksums, source/private payload exclusion, joins and consumer paths.
5. Set `OFFMENU_CURATED_RELEASE` locally to that accepted release directory.
   Run `node scripts/prepare-curated-publication.mjs`. Only accepted checksummed
   curation files enter `dist/curated-public`; local SQLite/originals never do.
6. Deploy that static directory with the Netlify CLI to site
   `a1df1508-4bb9-4b55-ab1f-88611e456e61`. This is a separate project from
   `offmenu-accounts`; do not relink or deploy to the authentication project.
7. Verify the live static manifest and indexed queries, then enable the Worker
   `CURATED_CORPUS_ORIGIN=https://offmenu-corpus.netlify.app` setting. Until that
   acceptance passes, the binding remains absent and corpus coverage empty.

Netlify CLI authentication is currently unavailable in this execution environment.
The empty target project exists; no curation deploy has been claimed. The CLI's
normal login flow is required; never extract connector or CLI tokens from configs.

## Cleanup checkpoint

Cloudflare `offmenu-open-corpus` database
`a3c9b1fc-bc8d-4c3e-afdf-de78caeeba49` deleted successfully. `CORPUS` detached
from the Worker; settings deployment `82549a5b-a0b0-494b-a540-43bac7c0c878`,
version `268d0f10-00ff-4254-ab58-35d7333bdfdf`. Read-back verifies only private
DB and the unchanged `PROVIDER_VAULT_KEY` secret bindings. Account aggregate
remains one row, summed revision 2, 821 bytes. Authentication endpoint unchanged.

Deleting the remaining 15,312 `public:*` unified records returned Cloudflare
7500 (D1 free-tier daily write quota). Remaining old source caches: products 14,
price observations 1; `public_products` 0. These are pending deletion, not removed.
Never drop the shared account DB or mixed `unified_records` table. Keep the
40 existing curated application recipes and private/application tables.

`cloud/provider-data.mjs` retires national source replica serving and excludes
replica counts from current operational coverage. `cloud/handler.mjs` stops raw
product/price response cache reads and writes. Deploy and verify that code before
claiming those retirement changes are live.

## Collection correctness checkpoint

The initial OFF normalization used Node readline, which splits valid JSON
strings at Unicode U+2028/U+2029. Its reconciliation and all-record exercise are
superseded. The original complete archive remains intact. `scripts/gzip-jsonl.mjs`
uses literal LF and propagates gzip corruption errors. Tests verify Unicode
separators, multibyte text and truncated gzip. The full OFF release is being
recollected into `off-2026-10-12-lf`; no accepted final counts yet.

The unfinished curation version 2 was stopped and its reproducible output removed
before upload. It must not be accepted or published. Full curation rebuild follows
the corrected OFF reconciliation and all-record consumer exercise.
