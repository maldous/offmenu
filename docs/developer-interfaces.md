# OffMenu developer interfaces

The frozen broader reference below describes source at commit `3540b2d4d5f4e96a518a63c832ccd6c3db809686`
(tree `62efa45bb564affe4f1f1b2388bbb3447a14482c`). It does not establish which
version is deployed. The current OpenAPI correction is separately pinned in
[the current OpenAPI section](#current-openapi-correction). Source acceptance, authentication activation and live
provider availability are separate facts. Example URLs use the reserved
`offmenu.example.invalid` domain and are not service addresses.

## Interface map and boundaries

| Surface | Intended consumer | Authoritative source |
| --- | --- | --- |
| Personal REST reads | Authorized clients reading saved account data | [Integration handler](../apps/web/server/integrations.mjs) |
| Personal MCP | Scoped personal clients; reads plus separately scoped reviewed mutations | [Integration handler](../apps/web/server/integrations.mjs), [personal tools](../apps/web/server/personal-ai.mjs) |
| OpenAPI | Discovery of eight personal REST GET paths | [Integration handler](../apps/web/server/integrations.mjs); limitations below |
| Administrative MCP | Separately authorized short-lived administrator delegation | [Administrative implementation](../apps/web/server/admin-mcp.mjs), [security guide](admin-mcp.md) |
| Native care client | Internal browser module using the existing care routes | [Care client guide](care-client.md), [care UI source](../apps/web/src/care-ui.js) |
| Optional-service client | Internal browser module honoring independent consent | [Consent guide](third-party-client.md), [services UI source](../apps/web/src/services-ui.js) |
| Local offline CLI | Explicit local SQLite database and authored/imported files | [CLI source](../src/offmenu/cli.py), [maintainer setup](maintainer.md) |
| Configuration | Deployment/maintainer-owned bindings and trusted entry points | [Configuration reference](maintainer.md#configuration-and-authentication-state) |

The inspected product manifests do not define a separately published OffMenu
client SDK. Do not treat internal modules, delivery tooling, retained `/__dev`
routes or third-party vendor libraries as a supported public OffMenu SDK.
Private internal routes are not documented here as external integration APIs.

## Personal REST

The eight source-defined routes are GET-only. Use an account-authorized bearer
with the exact API audience `<origin>/api/v1` and the named scope. API and MCP
bearers are not interchangeable. Read results are saved server state, not
unsaved browser edits.

| Path | Scope | Actual JSON envelope |
| --- | --- | --- |
| `/api/v1/inventory` | `inventory:read` | `version, revision, updatedAt, data`; data is inventory rows |
| `/api/v1/plans` | `plans:read` | Same envelope; data is the saved plan |
| `/api/v1/history` | `history:read` | Same envelope; data has separate `food` and `cleanup` arrays |
| `/api/v1/directory` | `directory:read` | Same envelope; data has `locations` and `recipes` |
| `/api/v1/data` | `data:read` | `schemaVersion, records, nextCursor, withheld, scope` |
| `/api/v1/health` | `health:read` | `documents, nextCursor, scope` |
| `/api/v1/baskets` | `baskets:read` | `documents, nextCursor, scope` |
| `/api/v1/evidence` | `evidence:read` | `documents, nextCursor, scope` |

Plans/history accept inclusive `from` and `to` date filters. The REST helper
filters strings without the MCP date-validation step: clients should send
`YYYY-MM-DD`. Document pages accept `cursor` and `limit` (default 100,
bounded to 1–1000). Continue with the returned opaque cursor until null.
Unified records also accept `kind`, `source` and `country` filters; export
rights filtering can withhold records, so an empty result is not proof of no
source records. Never substitute a UI count for export completeness.

Missing/expired/revoked or wrong-audience credentials return 401; a missing
required scope returns 403. Non-GET API calls return 405, unknown resource paths
404. The source uses `Cache-Control: no-store`. See
[catalogue pagination](../apps/web/server/catalogue.mjs) and
[record permissions/export](../apps/web/server/provider-data.mjs).

### Frozen OpenAPI limitation

At the frozen source pin above, `/openapi.json` advertises OpenAPI 3.1.0, bearer
authentication and all eight paths. Its common 200-response description lists only
`version, revision, updatedAt, data`. That description is incomplete for
`data`, `health`, `baskets` and `evidence`, whose actual envelopes are
listed above. Pagination and extra unified-record filters are also omitted.
Because the schema has no required fields and allows additional properties,
this is an under-specified contract, not proof that those responses fail
JSON Schema validation. Do not generate a complete response model from it.
The example captures both descriptions and actual responses; it does not
silently change the product schema.

### Current OpenAPI correction

The additive correction at [code commit `3b36d969f35e04a820961ac99c2d6bc7407f565d`](https://github.com/maldous/offmenu/commit/3b36d969f35e04a820961ac99c2d6bc7407f565d)
(tree `7c12006dbc3d0a97ceafcc7e9cacab1ba157abfd`) describes the actual eight
GET response envelopes and their guaranteed outer fields. `data` has
`schemaVersion, records, nextCursor, withheld, scope`; `health`, `baskets` and
`evidence` have `documents, nextCursor, scope`. The other four retain the
versioned state envelope. Nested records/document data remain source-specific,
not fully modeled schemas.

The document now includes document/record `cursor` and `limit`, unified-record
`kind`, `source` and `country`, and inclusive plans/history date parameters.
Descriptions preserve existing behavior: omitted, non-numeric and zero page
limits default to 100, other numeric values are clamped to 1–1000, and clients
should send an integer. REST date filters compare strings without calendar
validation; clients should send `YYYY-MM-DD`. An empty rights-filtered page can
still carry a next cursor. Schema correction changes no route, permission,
authentication, data handling or runtime validation.

Run `node examples/openapi-contract.mjs` from the repository root for the focused
current example. It verifies [42 code/schema file hashes](../examples/openapi-contract-source.json)
before loading the handler, blocks network entry points, and uses only authored
in-memory accounts, documents and normalized records. It checks actual populated
responses against the emitted envelope keywords, document pagination, an empty
rights-withheld page with an advancing cursor, country/kind/source filters and
inclusive dates. It prints JSON to stdout; keep captured results in ignored
private evidence storage.

The tested runtime is Node 24.22.1 with built-in `node:sqlite`; no server or
package installation is required. This later example/manifest pins the code
closure at the immutable code commit; it does not claim the example files were
present in that commit. The code pin is a reviewed candidate, not a statement of
accepted `develop`, deployed HTTP behavior or account activation. General
OpenAPI/JSON Schema validation, nested schemas and all possible rights/source
policies remain unqualified. The original broader REST/MCP example and its
3540b2d source manifest are preserved unchanged below; use their exact frozen
source, not this corrected checkout, to reproduce that historical example.

## MCP protocol and discovery

Send one JSON-RPC 2.0 object by POST to `/mcp` using a bearer scoped for
`<origin>/mcp`. Supported negotiated versions are `2025-11-25`,
`2025-06-18` and `2025-03-26`; another version falls back to `2025-11-25`.
The implementation is stateless JSON: GET/SSE and JSON-RPC batches are
unsupported. DELETE returns 204, notifications return 202.
A supplied foreign Origin is rejected.

Use `initialize`, `tools/list`, `tools/call` and `ping`.
Tool discovery is scope-filtered. A listed schema or annotation is not a grant
of permission to use a provider or modify data.

| Read tool | Scope |
| --- | --- |
| `get_inventory` | `inventory:read` |
| `get_meal_plan` | `plans:read` |
| `get_food_history` | `history:read` |
| `get_directory` | `directory:read` |
| `get_unified_records` | `data:read` |
| `get_health_observations` | `health:read` |
| `get_saved_baskets` | `baskets:read` |
| `get_private_evidence` | `evidence:read` |

Read tools return both text JSON and equivalent `structuredContent`, with
`isError:false`. Plans/history declare `from`/`to`; document/record reads
declare `cursor`/`limit`. Invalid tool arguments or unknown tool names return
JSON-RPC -32602; unknown methods -32601; malformed JSON uses HTTP 400/-32700.
Use the declared input schemas rather than relying on incidental extra
arguments accepted by a helper.

The other personal tools are `get_profile`, `get_recipes`,
`get_providers`, `lookup_provider`, `update_profile`, `save_recipe`,
`save_plan`, `update_inventory`, `get_ai_preferences`,
`save_ai_preferences`, and `contribute_recipe`. Their exact scopes,
required properties, confirmation/revision inputs and annotations are captured
in the [source-derived tool schema reference](reference/developer-tool-schemas.json).
They are not all read-only. The current initialize instructions still describe
the personal surface as read-only, so clients must inspect each actual tool
schema and scope instead of generalizing that phrase. The executable example
discovers these tools but does not execute their extra reads, writes or
provider actions.

## Administrative and care interfaces

Administrative grants are separate from personal scopes, MCP-audience-only and
limited to 15 minutes. The source requires fresh administrator identity proof
and revalidation; schema discovery in this example is a pure exported-function
inspection, not successful authorization or execution.

The full pinned list has 16 tools. The [schema reference](reference/developer-tool-schemas.json)
lists each tool's required administrative scope and complete input schema.
It includes community queue/moderation/AI decisions, public updates, care
case reads and reviewed replies/updates, service metadata/settings, public
source policies and community-AI settings/review. Provider settings return
metadata, not secrets. Mutating actions retain their explicit confirmation,
revision and reason requirements. Consult the [admin security guide](admin-mcp.md)
and implementation together; an older short tool list is not complete.

The care browser module exposes `setupCare({root,getUser,authFetch})`,
`refresh()`, `reset()` and `report(context)`. It is an internal browser
integration, not a remote SDK. Preserve account-epoch guards, private text
removal, staff detail authorization and revision-conflict handling described
in the [care guide](care-client.md). These UI behaviors were not rendered or
device-tested by the developer example.

## Offline CLI round trip

Run from the repository root with Python and a new disposable path.
`--db` belongs before the subcommand. Use only authored demo input here:

```bash
demo_dir="$(mktemp -d)"
demo_db="$demo_dir/authored-demo.sqlite"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=src
python3 -m offmenu --db "$demo_db" init
python3 -m offmenu --db "$demo_db" import-products examples/products.jsonl
python3 -m offmenu --db "$demo_db" import-recipes examples/recipes.json
python3 -m offmenu --db "$demo_db" map 0000000000001 "coconut milk"
python3 -m offmenu --db "$demo_db" add 0000000000001 400 ml
python3 -m offmenu --db "$demo_db" inventory
python3 -m offmenu --db "$demo_db" remove 1
python3 -m offmenu --db "$demo_db" inventory
```

The fresh-database example adds barcode `0000000000001`, Demo coconut milk,
quantity 400 ml, then ends with an empty inventory. Keep identifiers as strings
to preserve leading zeroes. The CLI also exposes `import-prices`, `meals`
and `shops`; inspect each subcommand's `--help` for its actual arguments.
Those additional commands are not covered by this round trip. The local
SQLite database is distinct from the deployment D1 binding.

## Reproduce the synthetic REST/MCP example

To reproduce the preserved broader example, use the exact qualified code/schema
bytes from `3540b2d4d5f4e96a518a63c832ccd6c3db809686` as the working directory
and invoke `node /path/to/preserved-reference/examples/developer-interfaces.mjs`.
The script resolves source files from the working directory and reads its
manifest alongside the script. The later reference/example artifacts are not
claimed to have existed in that qualified code commit. Its unchanged manifest
intentionally rejects the corrected handler in a current checkout. Use the
focused current command above for the OpenAPI repair.
The tested runtime is Node 24.16.0 with built-in `node:sqlite`;
no package installation or server is needed. The script first checks the
[source file manifest](../examples/developer-interface-source.json), then uses
only in-memory SQLite and authored accounts/records. Its fixed bearer strings
are unusable outside that in-memory fixture. Network entry points are blocked;
no sign-in, real credential, remote call, provider or held dataset is used.
JSON results go to stdout. Redirect them to private ignored evidence storage,
not source control.

The example covers all eight REST read paths and equivalent MCP read calls,
account isolation, scope/audience rejection, expiry/revocation, date filtering,
document pagination, discovery and selected protocol/error responses.
The unified-record fixture is empty: it does not certify nonempty rights
filtering. Additional personal/admin actions, live transport, deployed OAuth,
device behavior and full JSON Schema validation remain unverified.
The original integration tests also exercise synthetic token-management and
OAuth code/PKCE behavior. Neither example is an account activation workflow.

## Configuration, consent and updates

Keep configuration names and their owners in the
[maintainer reference](maintainer.md#configuration-and-authentication-state).
A mode variable alone does not activate Better Auth, provision email callbacks,
migrate accounts or qualify a deployment. Do not place secret values in examples.

Optional privacy, analytics, diagnostics, support and advertising choices start
off and are separate from account/pantry/health state. The
[optional-service guide](third-party-client.md) defines each finite client API
and consent boundary. A configured vendor identifier is not user consent or
proof of provider activation.
The pinned [service metadata builder](../apps/web/server/service-config.mjs)
marks Cloudflare and Netlify Identity as configured unconditionally; those
labels are not runtime, identity-activation or account-entitlement evidence.

The source-change owner must update affected current reference/schema/example
coverage when a handler/tool/configuration contract changes. Preserve explicit
frozen artifacts and their original provenance; add separately pinned current
coverage rather than relabelling historical acceptance. Generate from reviewed
source, run the relevant current example and review the exact diff through the
existing integration owner. Do not blindly replace
hashes to make a drift failure pass. Historical acceptance is not current
source presence. Product-specific gaps belong in OffMenu; shared source-role
and consumer principles remain in the existing
[documentation ownership guidance](development/task-routing.md#documentation-homes-and-update-responsibility).
