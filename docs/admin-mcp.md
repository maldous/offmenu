# Administrative MCP

Administrative MCP scopes are separate from personal read scopes and are limited to 15 minutes: `admin:community:read`, `admin:community:manage`, `admin:updates:manage`, `admin:care:read`, `admin:care:manage`, `admin:settings:read`, and `admin:settings:write`. They cannot be combined with private kitchen scopes and are valid only for the `/mcp` audience.

Issuing an administrative personal token or approving an OAuth grant requires a freshly verified Identity user with the `admin` or `offmenu-admin` role. The Identity bearer proof is AES-GCM sealed with token-specific associated data. It is never returned in an API result, tool result, or audit record. OAuth keeps the proof bound to the one-time authorization-code hash until exchange, then re-seals it to the opaque MCP token.

`tools/list` and every `tools/call` decrypt and revalidate that proof through the normal Identity verifier, confirm the original owner, and check the current role. Expiry, revocation, role removal, owner mismatch, invalid sealing, or an ordinary personal token denies access.

Available tools are deliberately finite: `listCommunityQueue`, `moderateCommunityItem`, and `publishUpdate`. Queue results contain public moderation fields only; private owner identifiers and sealed flag messages are removed. Mutations require a confirmed action, current revision, and a reason, and use the existing community, recipe-community, and care-update routes. There are no general SQL, URL-fetch, credential-export, profile-inspection, or private-record tools.

`completeCommunityAIDecision` is available only with `admin:community:manage`. It completes an existing `awaiting_agent` decision for a recipe, topic, reply, or recipe comment through the canonical revision-checked moderation helper. The MCP server never applies an AI decision directly.

Community AI controls are finite and individually scoped: `readCommunityAISettings` requires `admin:settings:read`; `configureCommunityAISettings` requires `admin:settings:write` and a confirmed revision; `runCommunityAIReview` requires `admin:community:manage` and confirmation; and `listCommunityAIDecisions` requires `admin:community:read`. They call only the pinned administrative community-AI routes, revalidate the administrator proof and role for every call, and record the opaque delegation ID in the administrative audit trail. Settings results contain configuration metadata only; no secret, arbitrary endpoint, or credential is exposed.
