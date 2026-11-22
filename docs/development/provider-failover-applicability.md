# Does OffMenu need the historical FreeBuff route?

**No declared OffMenu product caller selects FreeBuff or switches to it on failure at
`develop` [51ad2b27](https://github.com/maldous/offmenu/commit/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd).**
There *is* a product inference caller: community moderation can send a bounded
public submission to one explicitly selected self-hosted endpoint. That is not
evidence of which model sits behind a deployment, or of an alternate endpoint.
Adding automatic redirection would change the product and its data destination;
it is not a missing implementation of the current contract.

## Product call paths

| Entry point | What happens | Consequence for failover |
| --- | --- | --- |
| **Community review, administrator UI** | The [panel](../../apps/web/src/community-ai-ui.js) saves one provider and sends a confirmed run to `/api/admin/community/ai/run`. The [mounted Worker handler](../../apps/web/server/handler.mjs) dispatches to [community AI](../../apps/web/server/community-ai.mjs). The [build](../../scripts/build.mjs) bundles that handler, not a separate AI gateway. | The default is disabled. In `mcp` mode a selected item is recorded as `awaiting_agent`; no model endpoint is called. In `self-hosted` mode, `qualifiedEndpoint` requires an allowed HTTPS origin. `infer` sends one request to **that endpoint** for the candidate. An unusable response takes the failure path, not another provider. Failure to finalize is reported separately. |
| **Community review, delegated admin MCP** | [Admin MCP](../../apps/web/server/admin-mcp.mjs) routes its review request to the same administrative handler and routes completion to `completeAwaitingAgentDecision`. The [review guide](../community-ai-review-guide.md) distinguishes a queued decision from a completed external review. | This is another entry to the same product policy, not a second inference route. The stored self-hosted model name labels a decision; it is not proof of model selection or identity behind the endpoint. |
| **Personal AI and food-provider lookup** | The [personal MCP tools](../../apps/web/server/personal-ai.mjs) are served by [the integration endpoint](../../apps/web/server/integrations.mjs). `lookup_provider` delegates to the selected [food-data adapter](../../apps/web/server/provider-data.mjs). [Personal AI preferences](../personal-ai-guide.md) store an agent name and rules for use with an external client. | OffMenu exposes tools to that client. It does not select the client's inference provider or use food-provider credentials for moderation. |
| **Offline extraction** | The [assistant-intermediate module](../../src/offmenu/refresh/assistant_intermediate.py) consumes a supplied response and validates/replays it. The [inventory](../../src/offmenu/refresh/inventory.py) explicitly skips the historical tool's directory. | Neither is a model dispatcher; a saved response or a directory name is not a callable integration. |

## Which historical obligations remain?

The [catalogue](../operations/morgan-historical-reference-catalog.json) preserves
two different requirements (source sequence 5271):

* **FREEBUFF-COMPAT** was health-only evidence, not an Alexander model or MCP
  roundtrip. No product caller above requires that named service. Its live
  identity, availability, entitlement and cost remain **unverified**, not
  disproved. A configurable endpoint could be backed by a service not named in
  Git; no endpoint, deployment settings or private account were inspected.
* **ROUTING-FAILOVER** was desired, not implemented, for a historical delivery
  route. For the product, [community review policy](../community-ai.md) selects
  one mode, caps the daily budget and retains failed decisions. It does not
  select hosted Workers AI or personal keys as fallbacks. For *delivery*,
  [UIF's operating procedure at bb8bd5a8](https://github.com/maldous/uif/blob/bb8bd5a82acef73c0088f60004e2b993ca579117/docs/operating-procedure.md)
  specifies recovery on existing authorised resources, not a new inference
  provider. Installation and operation of that lifecycle remain distinct from
  this product finding.

## Recheck the finding

At the commit above, run this read-only index of named references, then trace
the generic callers in the table; the text search alone cannot identify the
provider behind an injected endpoint.

```sh
git grep -ilE 'free.?buff|routing[-_ ]?failover' 51ad2b27 -- \
  apps src deploy config contracts scripts integrations tools .github \
  pyproject.toml package.json package-lock.json netlify.toml
```

The only match in that scope was `src/offmenu/refresh/inventory.py`. The existing
[community AI tests](../../tests/web/community-ai.test.mjs) distinguish MCP queueing,
one-time claims and a synthetic provider result from an externally executed model.
None demonstrates a deployment or capacity.

[UIF-157](https://linear.app/maldous/issue/UIF-157) owns this caller disposition.
A future product change would need a named consuming journey, trigger and
authorised destination, with an explicit data, capacity and cost policy. A live
identity/availability claim would need a current receipt from the actual
deployment custodian. Neither is necessary to retain the source disposition,
and neither was inferred from a historical health check.
