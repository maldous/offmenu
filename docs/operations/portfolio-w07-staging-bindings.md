# Worker 07 retained metadata staging bindings

This portfolio proposal starts at develop `abecb99ee1125730ccbc2824b6ec49ffc5cc4302` for assignment `M-STAGING-BIND-20261018-W07`. It supplies six pinned metadata bindings across AQ, AR, AS and AT. It does not supply a real-source SourceContract or country acceptance. Originals remain in local executor custody outside Git. The authored fixture contains invented values only.

## Run locally

From the repository root, with retained local executor metadata available:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m offmenu.refresh.portfolio_w07 \
  --config config/refresh/portfolio-w07.json \
  --now 2026-10-18T05:01:43Z \
  --output /absolute/new/private-metadata-stage
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_portfolio_w07.py -v
```

Omit `--output` for a read-only plan. A nonvalid binding yields exit 2 and a structured diagnostic; the retained configuration intentionally has six held bindings. `valid` means structurally usable metadata only. Every result reports zero source-data records, zero gold admission, no country acceptance and zero network requests. Local paths are custody locators, not portable output identity or grants. A different host needs the same exact metadata bytes at an authorized local locator; missing metadata remains missing. No download, force refresh, source-body or runtime plugin option exists.

The private stage contains singleton-array JSONL records of kind `sourceInputBinding` and a pinned manifest. Each field preserves its literal source value and declared native unit/basis; unavailable units/bases are explicit null constants with policy origins, never fabricated conversions. Every scalar has a logical input path, hash, source/release, record ID and exact selector, or an explicit constant policy pin. The shared field-origin validator verifies coverage. These are metadata context records, not normalized food, recipe, nutrition, provider or price rows.

Original receipt acquisition and current validation time remain separate. Metadata-response captures (including PNDB's checkedAt) do not establish dataset download time. Filesystem modification time never establishes acquisition. The shared MIN_TTL constant provides a 30-day diagnostic boundary; validation cannot reset acquisition age. Stale metadata requires revalidation evidence, with no automatic network action or source-body reuse. There is no generic shared pure cache planner at this base: this bounded portfolio diagnostic wrapper does not impersonate registry fixtures, use the Wikibooks-specific cache policy, or call operational CachedAcquirer.

Repeating the same metadata/config verifies the manifest and actual candidate hash and returns `verified-metadata-no-op`, without rewriting the stage. Validation time and local custody path do not alter candidate identity. Partial, conflicting, corrupted or symlinked stages fail rather than being adopted. Validation diagnostics remain in returned JSON, separately from the immutable stage. Malformed declarations/load failures are isolated per binding after the bounded, uniquely identified envelope is validated. Duplicate binding IDs or an invalid envelope reject the batch before metadata reads.

## Retained portfolio applicability and holds

Exact metadata paths, sizes, hashes and selectors are in `config/refresh/portfolio-w07.json`.

| Binding | Meaning and unresolved dependency | Next action / owner |
|---|---|---|
| AQ ASE | Retained education article; not a cookbook or recipe corpus. Source use remains unqualified. | W07 retains role correction; the product maintainer selects an authorized cookbook/source qualification route. Existing source custodian20 supplies provenance if needed. |
| AR provincial recipe | Retained May2023/January2025 recipe-document metadata; recipe use and semantics unqualified. | Existing source custodian21 supplies exact release/use evidence; W07 can bind a reviewed grant and field/unit/basis map once supplied. |
| AS USDA census | Aggregate agriculture statistics, not retailer/provider identities. | W07 preserves nonapplicability; the product maintainer selects an actual provider source, avoiding duplicate acquisition by existing custodian24. |
| AS PNDB | Regional metadata; American Samoa membership unknown, not excluded. Dataset-specific use, definitions and units/bases unresolved. | Existing PNDB/source-rights custodian via the product maintainer supplies country membership and operation-specific evidence. W07 implements a reviewed binding after that dependency. No retry/download authorized here. |
| AT Vienna market | Retained HTTP404/error context, not market data; no-retry hold. | the product maintainer routes an alternate authorized source to existing custodian26; preserve the failed attempt. |
| AT COREMA | Image-object reference; image licence does not establish recipe-text or commercial recipe-use permission. | Existing custodian26/source-rights authority supplies a source-specific text grant or alternative, routed by the product maintainer. |

No cell of the four-country/six-type requirement is completed by this package:

| Required type | AQ | AR | AS | AT |
|---|---|---|---|---|
| Ingredients | Missing source/input | Missing source/input | Missing source/input | Missing source/input |
| Recipes | Education context only | Held metadata only | Missing source/input | Held image context only |
| Nutrition | Missing source/input | Missing source/input | PNDB applicability/use held | Missing source/input |
| Retailers/providers | Missing source/input | Missing source/input | Aggregate nonapplicable | HTTP error nondata |
| Prices/baskets | Missing source/input | Missing source/input | Missing source/input | Missing source/input |
| Dietary references | Missing source/input | Missing source/input | Missing applicable input | Missing source/input |

Each cell still needs source/release identity, applicable evidence, exact input inventory, required operation permissions, field origins, native units/bases, scope/count/identity expectations and independent semantics/acceptance review. Missing inputs differ from source-use holds and technical HTTP failure. Actual authorization/denied-action holds remain independently binding. No additional raw bodies were opened or acquired for this implementation.

## Shared-interface evidence and handoff

The implementation reuses shared strict JSON, canonicalization, hashing, UTC timestamps, safe-path validation and descriptor custody checks, singleton JSONL serialization, field origins, logical input-name validation and MIN_TTL. No shared core, engine or source registry is modified. Focused tests cover valid/missing/held/malformed/stale inputs, literal values/units/bases/unknowns, original versus validation clocks, exact TTL boundary, replay/tamper/partial-stage checks and isolated failures. One trusted, fully constrained authored-fixture SourceContract passes the shared qualifier; adding an authored hold fails qualification. That fixture contract is test code, not a runtime rights constructor or real-source permission.

`sourceInputBinding` currently has no reviewed real-source contract/schema factory. The metadata stage is a proposal, not an acceptance manifest consumed directly by `qualify`. A next real-source acceptance path needs an independently reviewed trusted contract, schemas and semantic callback with exact inventory/rights/scope evidence. the product maintainer and integrator owns shared-interface selection; W07 owns portfolio corrections. Submit the local commit through the product maintainer for independent review and the product integrator, preserving the existing branch/artifacts. Do not copy another country engine, edit shared core or retry held source acquisition to fill this gap. Pending review/integration is separate from the completed local implementation.

Production and CIX execution remain paused. Source/ownership/custody, denied-action, actual permission and mandatory auto_review holds remain active. This package grants no release, publication, permission change, new worker, scheduler or deployment authority.

## Designated 03 review correction

Successor to `dedaf6da` addresses `W03-W07-ISOLATION-01` and `W03-W07-NONREGULAR-02` from review6196. Declarations, including unknown fields, now receive iterative depth (32), node (8192) and serialized-size (262144 bytes) bounds before recursive copying or hashing. Invalid declarations contribute a bounded ID/malformed projection to the batch fingerprint, preserving valid peer rows and diagnostics. Binding IDs remain a bounded unique batch-envelope requirement.

Config, selected metadata, and existing stage manifest/candidate reads use anchored directory descriptors, no-follow/nonblocking opens, regular-file/size checks before reading, and matching descriptor/path identity and metadata after bounded reads. A regular-to-FIFO replacement between stat and open is rejected before reading. Config or stage failure returns exit 2 and a fixed structured CLI diagnostic without an exception traceback. Per-binding metadata failures remain isolated. Existing stage content is not rewritten on failure. These checks detect path replacement and observed mutation; they do not grant source access or assert protection against a privileged filesystem adversary.

Focused authored regressions cover mixed good/600-level malformed declarations through both pure planning and actual CLI; FIFO config with no writer, device/directory config, FIFO existing-stage manifest, regular-to-FIFO open race, oversized regular files and mutation during reading. Prior source/portfolio results remain retained evidence, without another source-data or full batch replay. The frozen successor requires delta review by the same designated03 and integration by00; author checks do not clear independent review holds.
