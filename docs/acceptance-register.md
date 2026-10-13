# OffMenu acceptance register

Continuation from private GitHub main `a3b0f89c8148bfcd7c3d3feb17f7d8e83b9bedd0`, 13 October 2026. Functionality takes priority over presentation. Research discovery is not operational data coverage. All five PDFs and four registers are preserved; checksums and structural checks are in `research-audit.json`.

Status meanings: **verified** has automated or live evidence; **implemented** needs the stated acceptance; **blocked** needs an external dependency. Source checkpoint tests: 92 JavaScript / 7 Python passed; production build passed.

| Requirement | Implementation / evidence | Status and remaining acceptance |
|---|---|---|
| Research preservation | Five unchanged PDFs; four checksum-matched registers; 249 unique countries in each country register | Verified locally |
| Catalogue and source applicability | 5,167 D1 catalogue records; 1,400 source-country links; cursor pagination; seven special territories get no fabricated household starter | D1 verified; new workspace live verification pending |
| Country baskets | 2,523 editorial starters / 707 published examples; no invented quantity, nutritional adequacy or complete national basket | Verified source; comparison-ready countries remain zero |
| Regional composition | AFCD 1,801; Ciqual 3,484; CoFID 2,887; BLS 7,140. Source-isolated documents and exact preparation/basis confirmation | D1 counts verified; no unnecessary import replay |
| Source rights / private imports | Reviewed source policies, private-use admission, retention/access clocks, dependency gates; unknown commercial reuse denied | Verified: source-policy/expiry/dependency admission and revoked reads tested |
| Revocation / invalidation | Provider disconnect removes that account's retained records; policy checked on cache reads; contribution and aggregates disabled | Verified: per-account disconnect and public cache-policy withdrawal tested; shared promotion blocked on source-specific rights/privacy review |
| Basket nutrients and groups | 45 metrics, explicit unknowns, energy/definition gates, group grams and density; compatible-cohort comparison API | Verified: synthetic arithmetic, missing nutrients, incompatible energy/definitions, group density and cohort/purpose gates; real national quantities and matches externally unresolved |
| Enrichment and qualification | GLEIF/Wikidata candidates, temporal control paths, explicit origin scopes, unknown/conflict/fail/pass; quarantined evidence excluded | Automated checks verified; live candidate/cache acceptance pending; product-company identity requires evidence review |
| Inventory and receipts | Continuous scanner, package/manual/produce amounts, custom locations, partial cleanup receipts | Existing automated tests; physical scanner/accessibility trials blocked on devices |
| Recipe and ingredient pack | 31 quantified concept recipes; aliases and dimensional conversion; incomplete imports excluded by default | Structural checks pass; independent cooking/nutrition review blocked on reviewers |
| Food-to-meal accounting | Single batch deducts raw lots once; stock-linked servings/saved leftovers/waste; retries idempotent; external intake logs remain separate | Verified: idempotent cooking/serving, split lots, unknown intake and removal reconciliation |
| Household privacy and roles | Owner/editor/viewer, single-use invitations, CAS, revocation; private measurements/history/provider projections excluded | Automated two-account acceptance; physical two-device/offline pilot outstanding |
| Offline continuity | IndexedDB checkpoint recovery, three-way merge, backoff, concurrent cooking/serving conflicts | Automated model checks; browser reload/network scenarios pending |
| Health and statistics | Explicit import consent, supported units/date/source, deduplication by source/member, private account history/statistics/export/delete | Verified: explicit consent, deduplication, account isolation, units and CAS; native HealthKit/Health Connect blocked on mobile build/permissions |
| BYOC providers | Existing encrypted vault preserved; USDA/Edamam transient lookups; unsupported adapters labelled accurately | Credentialed live verification blocked: no configured connections/issued keys |
| REST/MCP | Audience-bound, scoped, revocable tokens; private health/basket/evidence scopes; no sensitive fields via generic data scope | Automated protocol/PKCE tests; independent external client certification outstanding |
| Operations and checkpoint | Deployment/settings reconciled; query redaction and secret binding retained; acceptance/source/deployment evidence saved | 103-test checkpoint complete; deployment and final live checks pending |
| Additional integrations | OCR, contracted retailer feeds/cart, native wearables, clinical workflows, exhaustive recall/legal coverage | Blocked on service rights/access, native code/device permission, or independent specialist validation; no active connector claim |
| International UI and pilots | Unicode source names, explicit country/unit selection, dimensional imperial conversions, keyboard alternatives | Complete translated locale packs and physical accessibility/household pilots need language/device/user review; UI/UX feedback is a later run |

## Preservation and deployment constraints

Do not replace user-state tables or authentication. Never regenerate `PROVIDER_VAULT_KEY`; upload must retain secret bindings. No private production exports, bearer tokens or credentials belong in source. Only additive, idempotent schema changes may be applied. Recheck remote main and live deployment immediately before mutation to avoid overwriting concurrent work.

## Continuation changes verified locally

104 JavaScript tests and 7 Python tests pass. New regression cases cover unknown provider rights, policy withdrawal, account-specific disconnect, explicit measurement consent, cross-import measurement deduplication, sensitive scope exclusion, incompatible energy definitions, food-group denominators, coherent cooked-stock removals/split lots, private shared-kitchen projection, quarantine, and cache-policy withdrawal. Automatic menu selection now withholds unresolved dietary evidence; manual cooking requires the user's recorded review when checks remain. Private documents and unified records have explicit cursor pagination; REST/MCP expose it, and browser exports follow every page.

Existing live maintenance schedule `17 * * * *` is retained. The only required additive schema change is the public resolver lease table. Account snapshot baseline: 1 record, total revision 2, 821 JSON bytes. Production account content has not been exported or modified. No provider keys or bearer tokens were generated for production acceptance.
