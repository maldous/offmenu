# OffMenu feedback and customer relations

Architecture recommendation, 14 October 2026. Functional scope for `third-party-services`; final visual layout remains open. The case, discussion and editorial workflows described here are proposed functionality, beyond the existing service and administrator settings routes.

Deliver a native OffMenu customer-care area and staff workspace using the existing authentication, Worker and D1 stack. Start with a small case queue, contextual correction reports, an update feed and moderated discussions. Keep third-party providers behind server-side adapters. Core feedback and moderation must work without email delivery, a vendor widget, another account, or a paid feedback subscription.

The cost constraint is zero additional service or hosting spend at the expected low volume. Reuse existing infrastructure within its confirmed included allowance. This does not assert that OffMenu's existing hosting bill is zero. Do not introduce another paid plan, trial dependency, automatic upgrade, AI moderation charge, or always-running server. If an existing allowance is exhausted, defer optional delivery or temporarily limit submissions rather than incur additional spend.

## Product experience

Use OffMenu typography, controls, language handling, RTL support, status messages and navigation throughout. A help or feedback entry opens an application view. Reports also originate beside the relevant recipe or translated text. Vendor names and configuration belong in staff service settings. No iframe, hosted board redirect, vendor login or third-party popup is required to complete a customer or staff task.

| Customer action | Native OffMenu behavior | Staff workflow |
| --- | --- | --- |
| Report a recipe problem | Select an issue such as quantity, ingredient, instruction or source attribution; preview the selected context and correction | Triage, request clarification, link duplicates, prepare a correction and record editorial review |
| Report a translation problem | Include the message/text identifier, locale, version, observed wording and proposed wording; keep user text distinct from interface text | Review language, placeholders and source meaning; link a tested translation change to its release |
| Contact support | Private case with messages, status, reply history and notification preference | Shared inbox with assignment, private staff notes, reply, resolve and reopen |
| Suggest a feature | Private submission initially; user can explicitly choose a public community suggestion | Categorize, merge public duplicates, label consideration/planned/shipped and link updates |
| Discuss or flag a post | Public or members-only threads with replies, follow/unfollow and flagging | Review flags; hide/restore, lock/unlock, pin, move, merge and mark spam with a reason |
| Read product updates | Searchable changelog and in-app unread indicator; optional subscribed email | Draft, preview by language, schedule, publish, correct or withdraw an announcement |

The customer-care area has “My requests”, “Community” and “What’s new”. The role-gated staff workspace has “Inbox”, “Corrections”, “Translations”, “Moderation” and “Updates”, with global service settings alongside them. These are navigation responsibilities, not a commitment to final placement or a visual redesign. Small screens use one list and detail view; a wider screen can show the same list beside the selected detail.

Show meaningful status, reply expectations and a durable request reference. Save private drafts only within the current account and clear them on account changes. A failed submit preserves the reviewed draft. Browsing updates and public discussions can work as a guest; posting and private cases use the existing sign-in flow. The customer never needs a separate feedback-service identity.

## Administrator access and customer privacy

All application administrators retain access to application-wide customer-care tasks. Authority comes from current trusted authentication roles, as in [administrator settings](admin-settings.md). A future capability map can grant narrower support, moderator and editor responsibilities through trusted roles; it must not derive authority from editable profile metadata. Authentication adapters should supply a verified issuer/subject identity and trusted roles, keeping these workflows compatible with the bring-your-own-authentication principle.

A private case is an explicitly submitted record with its own staff-access purpose. Before submission, the customer sees the exact text and selected context that customer-care administrators will receive. Reading this case is authorized by that submission; it does not authorize access to the user's full profile, pantry, receipts, health history, private recipes, private search results or provider credentials.

Staff customer history consists of that customer's submitted cases, correspondence and community moderation actions. It does not include a profile inspector, account impersonation, raw user-directory export or arbitrary account search. Case lookup can use the case reference and a minimal customer-care identity. Verified email is resolved only for authorized delivery; public posts use a user-selected display alias, never an email address.

Default reports are private. Creating a public suggestion requires a separate public preview and explicit publication choice. Staff may draft a redacted public summary of a private case, but cannot publish it without the submitter's approval. A private case cannot be merged into a public thread with its body, identity or subscribers intact. Public duplicate links and private case links remain different operations. Users' personal provider results cannot become public recipe corrections merely because staff can read a report.

Seal private case bodies and staff notes under a dedicated case binding. Existing personal credential APIs and their owner checks remain unchanged. Audit actor, action, record identifier, revision and reason code; keep case bodies, emails, private notes and secrets out of audit and diagnostic events. Apply retention to case content and moderation evidence separately; remove expired private content from derived indexes and exports. Public-content backups must exclude private cases. Account deletion also addresses case ownership/contact projections under the configured retention policy.

Community restrictions limit posting, replying or voting. Moderators cannot disable kitchen access, change authentication roles, reset another user's credentials or edit their profile. A restriction has a reason, scope, expiry where appropriate and an appeal path. Private staff notes are distinct from customer-visible replies.

## Recipe and translation corrections

A report carries a reference and version/digest of the affected public resource plus only the selected excerpt. The server resolves public context through public adapters. For a private recipe or provider result, the user explicitly submits the necessary excerpt; the server must not fetch the private resource using staff authority.

Use the editorial states `submitted → triaged → proposed → reviewed → released`, with separate `duplicate`, `declined` and `needs information` outcomes. “Resolved” must distinguish a reply or workaround from a released correction. A report is not itself a right to edit or republish source material.

Recipe correction proposals retain source identifiers, licence/attribution, original instructions, quantities and units. Check measurement dimensions, yield, scaling and any nutrition/allergen implications. Publish accepted public changes through the existing curated release process, with an immutable change record and a reversible version. Never silently replace a customer's privately reviewed recipe. Notify affected followers that an update is available and let them review it.

Interface translation reports use the existing source-message key, locale, application release and observed wording. Corpus reports use the existing text/resource IDs and source digest. Preserve placeholders, plural variants, language direction and source meaning. Run the current i18n checks and corpus consumer checks before release. Unreviewed translation suggestions stay drafts; a source change invalidates an older translation. Keep English fallback visible where Arabic remains incomplete, as described in [internationalization](i18n.md). Staff review a change, then the normal engineering or curation release publishes it; the browser does not write arbitrary catalogue or corpus replacements.

## Notifications and customer correspondence

The native case thread and update feed are authoritative. In-app notifications need no email vendor. Users choose notifications for their cases and followed topics; promotional/product-update email has a separate opt-in and unsubscribe control. Staff cannot subscribe a customer on their behalf or segment messages using kitchen/health data.

Brevo Free is the initial optional customer-email transport. Cloudflare Email Routing is the preferred branded inbound-address option when the selected destination is verified. Its documented Free plan includes transactional email and 300 daily sends; current OffMenu account eligibility and remaining quota must be confirmed before activation. Use an application-wide daily budget shared with existing support/document delivery, reserve capacity for account-requested replies, and defer announcements when capacity is unavailable. Do not purchase credits. [Brevo plan documentation](https://help.brevo.com/hc/en-us/articles/208589409-About-Brevo-s-pricing-plans), [transactional API](https://developers.brevo.com/docs/send-a-transactional-email).

By default, an email says an OffMenu reply/update is available and links to the authenticated view. It does not contain the private case body. Use versioned outbox items and idempotency; verify preferences and the current verified recipient at send time. Provider timeout creates an uncertain delivery state, not an automatic resend. Authenticated delivery callbacks can reconcile outcomes without opening access to case data. Release emails never share recipient lists. Inbound email replies and arbitrary attachments can wait: the native thread completes the first customer-care workflow without them.

## Branded support addresses and sign in

Use `support@offmenu.aldous.info` as the customer-facing contact and reply destination, with sender name “OffMenu Support”. Start with one support queue; correction and translation categories do not need separate mailboxes. An alias or forwarding address is not an independent login/mailbox. Connect it to the selected verified staff destination first; native email ingestion can follow once case ingestion and its abuse/authentication rules are implemented. Outbound sender/domain authentication and verified reply routing are separate readiness checks.

Reuse existing managed sign-in and trusted staff role claims. The current public Identity settings expose Google and email login; additional SSO providers or custom SAML are not required to use customer care. If “SSO configurations” is confirmed, configure only needed integrations within current free entitlements, preserving current callbacks and account identities. Never create a shared staff password or infer an administrator from an email suffix.

The user authorized creating appropriate support accounts and service configurations. Destination selection is still required before enabling forwarding. Setup must preserve existing apex-domain mail and use OffMenu-specific records. Mail branding covers sender name, verified from/reply address, both plain text and HTML, readable language/direction, first-party links and clear unsubscribe choices for optional updates.

[Cloudflare pricing](https://developers.cloudflare.com/email-service/platform/pricing/) documents free inbound routing. Arbitrary-recipient sending requires Workers Paid and includes 3,000 monthly account-wide messages before metered overage. Its current account quota readback is null, so the setup has not qualified that outbound entitlement. Do not activate metered customer sending to satisfy this zero-additional-cost scope. Account-wide routing does not make a new staff mailbox free by itself. [Subdomain routing configuration](https://developers.cloudflare.com/email-service/configuration/subdomains/) allows OffMenu records to be scoped separately.

## Tool selection and self hosting

| Option | Assessment | Decision |
| --- | --- | --- |
| Existing Worker/D1 and authentication | One identity, existing privacy boundaries, native correction context and no separate service to operate | Initial system of record and API; bound usage to existing entitlements |
| Cloudflare Email Routing | Free inbound address routing to an existing verified destination; forwarding is separate from case ingestion | Branded support alias after destination selection and DNS/rule readback |
| Brevo Free | Optional low-volume delivery; feedback stays usable when unavailable | Reuse behind an email adapter within the confirmed free quota |
| Sleekplan | Free Indie offers a board/changelog and a single administrator; SSO, REST API and webhooks are listed under paid Starter | Do not make it a dependency under the zero-additional-cost constraint; existing widget/board seam is not the target customer-care interface |
| Self-hosted Fider | Open-source feedback/voting tool; official deployment requires Docker, PostgreSQL and email | Strong candidate if a dedicated suggestions engine becomes useful and an existing host has spare capacity; qualify its API/role operations against this contract first |
| Self-hosted Discourse | Open-source forum with an API; separate forum operations and hosting still need capacity and maintenance | Prefer if full community discussion grows beyond the bounded native moderation scope; reuse OffMenu views and identity through a server adapter |
| GitHub | Existing engineering delivery path | Optional staff-selected, redacted engineering handoff; customer feedback never requires a GitHub account |

Sources: [Sleekplan pricing](https://sleekplan.com/pricing), [Sleekplan API](https://sleekplan.com/docs/api/overview), [Fider repository](https://github.com/getfider/fider), [Fider hosting requirements](https://docs.fider.io/hosting-instance/), [Discourse self hosting](https://www.discourse.org/pricing), [Discourse API](https://docs.discourse.org/).

Fider and Discourse are evaluated alternatives, not additions to the register of historically used services. Free software removes licence fees; a separate deployment only satisfies this cost constraint when its hosting, database, backups and email use existing available capacity at no extra charge. Neither is a drop-in D1 application. Avoid a new host for the first low-volume release. Use the software's licence and supported extension/API model if adopted, rather than assuming a vendor UI can be freely copied into OffMenu.

## Implementation contract

Create a focused customer-care module with its own case, message, editorial-proposal, public-thread, moderation-action, announcement, subscription and notification-outbox records. Separate public projections from private records at storage and API boundaries. Reuse role verification, same-origin mutations, bounded JSON, CAS revisions, sealed payloads and atomic value-free audit. Do not extend the private delivery ledger into a general admin-readable profile store or retrospectively ingest old support messages into a forum.

The browser calls same-origin OffMenu APIs for cases, corrections, discussions and updates. Provider credentials stay server-side. Optional provider adapters accept typed, explicitly approved projections and return normalized results. OffMenu remains authoritative for visibility, roles, publication, locale, subscriptions and audit. Choose one owner for each external synchronization path; signed callbacks must not grant roles or convert private records to public ones.

Start with paginated lists, text-only messages, bounded excerpts, per-account and global submission caps, a human review queue, and on-demand refresh while a view is open. Defer file uploads, rich HTML, chat, push notifications, machine translation and AI moderation. Show cases and replies immediately after a durable database commit; email and optional engineering synchronization are separate outbox work. No user-facing success claim depends on a vendor accepting delivery.

## Delivery order and acceptance

1. Native private intake and customer threads, shared staff inbox, assignment and replies, case-specific visibility, audit and in-app notifications. Core works with all optional providers disabled.
2. Contextual recipe and translation reports, staff proposals/review, tested release references and customer-visible outcomes.
3. Public suggestions/discussions, duplicate linking, follow/unfollow, report queue, reversible moderation and appeal handling.
4. Native localized changelog, scheduling and publication, followed-topic notifications and optional free-quota email.
5. Introduce a self-hosted engine only when observed needs exceed the native scope and a zero-additional-cost deployment is qualified.

Acceptance must prove: fresh role revocation; owner/staff/public visibility at each endpoint; no profile or provider-credential access; case-to-public conversion requires user approval; private duplicate merges do not leak content/subscribers; restriction scope does not block kitchen access; atomic concurrent moderation/editing and audit; source/digest checks for corrections; safe text rendering, accessible keyboard controls and RTL; unsubscribe-before-send; uncertain email outcomes do not duplicate; quota exhaustion adds no spend; provider outage preserves case submission/reply and update browsing. Match the product's final layout when agreed without changing these functional contracts.
