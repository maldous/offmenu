# Third-party functional checkpoint

This branch adds native customer care, public recipe/community participation,
opt-in community profiles and trophies, owner-scoped personal AI preferences and
MCP actions, and separately scoped administrator MCP operations. Canonical
`cloud/schema.sql` includes the additive feature tables for a fresh database.

Verification on 14 October 2026 (Melbourne): 253 JavaScript tests, four compiled
Worker tests, and 36 Python tests pass. The compiled care test uses only the
canonical schema and verifies case ownership, staff authorization, owner replies,
public recipe review, AI attribution, voting and self-vote rejection. Build and
localization inventory checks pass. Arabic is incomplete: 376 of 2688 messages
are translated; missing strings use explicit English fallback.

The browser preview uses mocked identity and blocks external networking. Checks
covered startup without JavaScript errors, opening the native care dialog,
signing in, reviewing and submitting a request, and staff request detail. These
checks do not prove production identity provisioning or real email delivery.

Account-bound fetch rejects writes when an asynchronous session refresh switches
accounts. Personal assistant publication uses only the owner's explicitly chosen
assistant name, never a private integration label. Staff may access submitted
care messages and public moderation queues; these permissions do not grant
access to users' personal provider credentials or private kitchens/results.

AI reviews process at most three candidates per run, exclude terminal decisions
before source pagination and use a durable applying state before provider work
or moderation. A later authorized run reconciles incomplete finalization after its 60-second
lease expires, without repeating provider calls. Ambiguous interrupted actions
return to held review and never infer AI credit from a human moderation change. Automatic actions are restricted to reversible hiding
of topics/replies; recipes and recipe comments require explicit review. There is
no automatically scheduled job with an unqualified administrator identity.

No new feature schema has been applied to production, and no new feature Worker
has been deployed. Main-branch integration remains pending coordination. Existing
inbound support forwarding is separately documented in
`support-email-readiness.json`. Outbound branded sending, additional account
headroom and production administrator-role provisioning remain unqualified.
Paid services remain disabled. Case correction states retain review evidence;
publication into the main recipe corpus or translation catalogue is a separate
reviewed operation.
