# OffMenu acceptance register

## Recovered local execution — 13 October 2026

Current evidence is in `recovery-2026-10-13.json`; older checkpoints below are historical.
Residual source records and raw caches have been removed from D1 and verified empty,
including after a successful transient barcode lookup. The private account aggregate
and vault binding are preserved. Source `f9fec05` is deployed; 115 JavaScript
tests, nine Python tests and the build pass.

Full USDA, Open Prices and Wikibooks releases have been reacquired, reconciled and
exercised locally. Their 4,347,570 curated records are live on static Netlify.
176,781 USDA records were withheld. Every curated record and file passed the
publication gate. Hosted checksummed reads and small live queries passed.
Repeated default/large live pagination still intermittently exhausts Worker CPU;
full production query acceptance is NOT claimed. Cloudflare rejects CPU settings
with Free-plan error 100328; the user reports paid-plan context.
OpenNutrition's 326,759 rows reconcile; it remains unadmitted to authoritative
nutrition. The complete OFF archive is checksum verified, with normalization and
full-record exercise running under `offmenu-off-recovery-20261013.service`.
OFF is not part of current published coverage.

## Local curation amendment — 13 October 2026

- Verified separate public corpus D1 deletion and Worker binding removal.
- Verified account baseline unchanged and provider-vault secret binding preserved.
- Remaining 15,312 public unified rows and 15 old raw response-cache rows await
  D1 write availability; deletion is externally blocked by Cloudflare 7500.
- New code retires source replica serving/coverage and raw response persistence;
  production deployment acceptance is pending at this checkpoint.
- Static Netlify curation publisher and shared local/Worker query engine implemented.
  No Netlify runtime function retained. Full publication requires accepted curation
  output and CLI authentication; neither is claimed complete.
- Initial OFF collection acceptance superseded: Unicode text line separators
  incorrectly split JSON. Correct literal-LF full recollection running.
- 114 JavaScript and nine Python tests pass; Worker build passes. New tests cover
  publication projection/private rejection, Unicode queries/barcodes, local compiled
  serving, Unicode JSONL separators and truncated gzip integrity.

Continuation from private GitHub main `a3b0f89c8148bfcd7c3d3feb17f7d8e83b9bedd0`, 13 October 2026. Functionality takes priority over presentation. Research discovery is not operational data coverage. All five PDFs and four registers are preserved; checksums and structural checks are in `research-audit.json`.

Status meanings: **verified** has automated or live evidence; **implemented** needs the stated acceptance; **blocked** needs an external dependency. Source checkpoint tests: 92 JavaScript / 7 Python passed; production build passed.

| Requirement | Implementation / evidence | Status and remaining acceptance |
|---|---|---|
| Research preservation | Five unchanged PDFs; four checksum-matched registers; 249 unique countries in each country register | Verified locally |
| Catalogue and source applicability | 5,167 D1 catalogue records; 1,400 source-country links; cursor pagination; seven special territories get no fabricated household starter | D1 verified; workspace verified in live browser |
| Country baskets | 2,523 editorial starters / 707 published examples; no invented quantity, nutritional adequacy or complete national basket | Verified source; comparison-ready countries remain zero |
| Regional composition | AFCD 1,801; Ciqual 3,484; CoFID 2,887; BLS 7,140. Source-isolated documents and exact preparation/basis confirmation | D1 counts verified; no unnecessary import replay |
| Source rights / private imports | Reviewed source policies, private-use admission, retention/access clocks, dependency gates; unknown commercial reuse denied | Verified: source-policy/expiry/dependency admission and revoked reads tested |
| Revocation / invalidation | Provider disconnect removes that account's retained records; policy checked on cache reads; contribution and aggregates disabled | Verified: per-account disconnect and public cache-policy withdrawal tested; shared promotion blocked on source-specific rights/privacy review |
| Basket nutrients and groups | 45 metrics, explicit unknowns, energy/definition gates, group grams and density; compatible-cohort comparison API | Verified: synthetic arithmetic, missing nutrients, incompatible energy/definitions, group density and cohort/purpose gates; real national quantities and matches externally unresolved |
| Enrichment and qualification | GLEIF/Wikidata candidates, temporal control paths, explicit origin scopes, unknown/conflict/fail/pass; quarantined evidence excluded | Automated checks verified; live GLEIF/Wikidata lookups and GLEIF warm-cache reuse verified; product-company identity requires evidence review |
| Inventory and receipts | Continuous scanner, package/manual/produce amounts, custom locations, partial cleanup receipts | Existing automated tests; physical scanner/accessibility trials blocked on devices |
| Recipe and ingredient pack | 31 quantified concept recipes; aliases and dimensional conversion; incomplete imports excluded by default | Structural checks pass; independent cooking/nutrition review blocked on reviewers |
| Food-to-meal accounting | Single batch deducts raw lots once; stock-linked servings/saved leftovers/waste; retries idempotent; external intake logs remain separate | Verified: idempotent cooking/serving, split lots, unknown intake and removal reconciliation |
| Household privacy and roles | Owner/editor/viewer, single-use invitations, CAS, revocation; private measurements/history/provider projections excluded | Automated two-account acceptance; physical two-device/offline pilot outstanding |
| Offline continuity | IndexedDB checkpoint recovery, three-way merge, backoff, concurrent cooking/serving conflicts | Automated model checks; browser guest demo/cook/serve verified; actual two-device offline recovery remains unverified |
| Health and statistics | Explicit import consent, supported units/date/source, deduplication by source/member, private account history/statistics/export/delete | Verified: explicit consent, deduplication, account isolation, units and CAS; native HealthKit/Health Connect blocked on mobile build/permissions |
| BYOC providers | Existing encrypted vault preserved; USDA/Edamam transient lookups; unsupported adapters labelled accurately | Credentialed live verification blocked: no configured connections/issued keys |
| REST/MCP | Audience-bound, scoped, revocable tokens; private health/basket/evidence scopes; no sensitive fields via generic data scope | Automated protocol/PKCE tests; independent external client certification outstanding |
| Operations and checkpoint | Deployment/settings reconciled; query redaction and secret binding retained; acceptance/source/deployment evidence saved | Deployed and verified; see live-acceptance.json |
| Additional integrations | OCR, contracted retailer feeds/cart, native wearables, clinical workflows, exhaustive recall/legal coverage | Blocked on service rights/access, native code/device permission, or independent specialist validation; no active connector claim |
| International UI and pilots | Unicode source names, explicit country/unit selection, dimensional imperial conversions, keyboard alternatives | Complete translated locale packs and physical accessibility/household pilots need language/device/user review; UI/UX feedback is a later run |

## Preservation and deployment constraints

Do not replace user-state tables or authentication. Never regenerate `PROVIDER_VAULT_KEY`; upload must retain secret bindings. No private production exports, bearer tokens or credentials belong in source. Only additive, idempotent schema changes may be applied. Recheck remote main and live deployment immediately before mutation to avoid overwriting concurrent work.

## Continuation changes verified locally

106 JavaScript tests and 7 Python tests pass. New regression cases cover unknown provider rights, policy withdrawal, account-specific disconnect, explicit measurement consent, cross-import measurement deduplication, sensitive scope exclusion, incompatible energy definitions, food-group denominators, coherent cooked-stock removals/split lots, private shared-kitchen projection, quarantine, and cache-policy withdrawal. Automatic menu selection now withholds unresolved dietary evidence; manual cooking requires the user's recorded review when checks remain. Private documents and unified records have explicit cursor pagination; REST/MCP expose it, and browser exports follow every page.

Existing live maintenance schedule `17 * * * *` is retained. The only required additive schema change is the public resolver lease table. Account snapshot baseline: 1 record, total revision 2, 821 JSON bytes. Production account content has not been exported or modified. No provider keys or bearer tokens were generated for production acceptance.

## Final live acceptance

Functional source `e57db238d96059caa00712e9f6fb94f770e134db` serves production at 100% on Worker version `139f5839-fadc-446e-9557-9031168a521e`, deployment `495d5259-cea5-42f0-90d8-c04c718c2a34`. Live checks cover catalogue completeness, AU/AQ records, AFCD lookup, 70 recipes / 31 quantified, calculations, comparisons, unknown qualification, GLEIF/Wikidata, cache reuse, Origin rejection, unauthenticated private/REST/MCP denial, OAuth metadata, OpenAPI, and Identity settings. Browser demonstration confirms raw stock deduction and half-serving with saved cooked leftovers. The terminal Python HTTP client is denied by Cloudflare browser-integrity screening; the original curl client and browser completed acceptance.

Two integration defects were found by live acceptance and corrected: the catalogue dispatcher previously intercepted enrichment; upstream fetch used a redirect mode unsupported by Workers. Full-dispatch regression and live lookups now pass. The final evidence/test commit may follow the deployed functional commit; it does not change runtime code.

Production data remains preserved: 1 account record, summed revision 2, 821 snapshot bytes; catalogue/composition/source-country counts unchanged; vault binding, Netlify identity, query redaction and existing maintenance schedule retained. No account, connection, bearer token or private production test fixture was created. The public resolver lease table is the sole schema addition.

## Full collection programme — execution checkpoint

| Item | Delivered evidence | Current gate |
|---|---|---|
| Complete USDA April 2026 archive | All 34 CSV tables, 36,049,091 raw rows; 4,202,558 normalized records; original columns retained | Full corpus publication and feature acceptance pending |
| Complete Open Prices 12 October 2026 exports | 326,767 prices reconciled; 317,898 accepted; all locations and proof metadata parsed | Dedicated D1 import in progress; activation/live use pending |
| Complete Wikibooks 31 July 2024 snapshot | 3,895 recipe rows normalized and count-gated D1 activation | Worker deployment pending; independent recipe review remains external |
| Complete OFF 12 October 2026 export | Entire 13,132,516,914-byte gzip downloaded | Full normalization running; reconciliation/publication pending |
| Reusable collection tools | Atomic table checkpoints, archive change refusal, reconciliation, bounded import parts, inactive partial releases | 111 JavaScript / 9 Python tests pass; production build succeeds |
| HN discovery | OpenNutrition publisher checksum verified; primary methodology and modified attribution checked | Supplemental source/quality register in progress; no measured-nutrition claim |
| Durable raw release archive | Checksum and named upstream release retained; local archives acquired | R2 API error 10042 requires account activation; not claimed durable |

Detailed evidence: `docs/collection-execution.md`, `docs/collections/`. This is an in-progress checkpoint, not programme completion. No current account state or credential was read or modified.
