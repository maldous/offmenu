# Personal AI

Personal AI is an owner-scoped MCP capability. It uses the existing personal integration grant and never accepts an owner identifier in tool arguments. A grant can request only the capabilities it needs: profile, recipes, plans, inventory, connected-provider metadata and lookup, AI preferences, or community contribution.

Profile, recipes, inventory and plans are read from the grant owner’s `user_state` row. Profile writes can set only country, units, servings and interface language; household members, health-related state, history, locations and plans are retained. Every write uses that row’s revision and validates the complete reconstructed state before a compare-and-swap update. The operation preserves the owner’s unrelated state and cannot select another account.

Every MCP write additionally requires `confirmed: true` in its exact argument schema. This is the connected client’s reviewed-action assertion and supports autonomous work within the owner’s explicitly scoped grant; it does not create a new interactive approval requirement for each call. Replacing a complete plan or inventory is marked destructive in MCP metadata. Profile patches and recipe upserts are not.

Provider tools expose only `sourceId` and label metadata. Lookup is proxied to the existing same-origin provider adapter under the grant owner’s identity; the personal AI module never selects, decrypts, logs, or returns provider credentials.

Preferences are stored separately in `personal_ai_preferences`, encrypted with `PERSONAL_AI_VAULT_KEY` (or the existing provider vault key during migration), and bound to the owner. Rules are limited to 5,000 characters and the agent name to 80 characters. Browser preferences use the authenticated `/api/care/ai/preferences` endpoint with an Origin check and revision check. The UI keeps no plaintext persistence.

Public contribution is a deliberate MCP write. It requires `community:contribute`, explicit `confirmed` and `rightsConfirmed` values, a supported explicit public license, and a saved personal assistant name selected by the owner. The submitted attribution is `{kind: "ai", agentName}` from those preferences, never an integration-token name, and community moderation remains required. Private instructions, health data, provider credentials, and lookup results are never attached to the contribution. This integration does not call or buy access to a hosted AI model; an MCP client supplies any model it chooses.
