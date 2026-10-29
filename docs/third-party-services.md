# Third-party services

This is the implementation disposition for the 149 records in the [service inventory](third-party-service-inventory.json). The JSON register is exhaustive: each source record appears once and retains the inventory's exact evidence status, qualification requirement, and evidence links. A disposition does not turn historical evidence into current entitlement.

OffMenu retains Cloudflare Workers/D1 and Netlify Identity, including managed Google sign-in. GitHub Actions is the engineering delivery path. Existing public food-data adapters and published/imported sources remain subject to their existing provenance and licence records.

The following product seams are deliberately configuration-first because final UI design is pending:

- Sentry can receive filtered technical errors once an OffMenu project and DSN are confirmed. Never include private kitchen, health, receipt, access-token, or identity content.
- Brevo can send an explicit support or transactional email when an OffMenu sender and recipient policy are qualified. It is not a general background-email feature.
- iubenda can govern the consent banner and policy links. Zaraz analytics stays coarse and loads only after consent. Google Analytics is not added directly.
- Sleekplan can supply a feedback board after the product and board URL are configured. There is no fixed widget placement yet.
- Google Search Console and Bing Webmaster Tools are verification/discovery configuration only.
- AdSense remains off unless the site is individually approved and consent/policy configuration is complete. AdMob and Google Funding Choices wait for a native-app decision.
- UptimeRobot, Snyk, and Sonar remain optional operations tooling. This branch never creates accounts or runs a scan merely because a historical record exists.

`THIRD_PARTY_CONFIG` is a JSON runtime setting. [config/third-party.example.json](../config/third-party.example.json) is a safe disabled example; it contains no credential values. Validate it with:

```bash
node scripts/verify-third-party-config.mjs
```

The validator reports a valid disabled configuration as `configured: false`. It reports enabled flags honestly and uses the shared Worker parser, so it rejects unknown settings, partial consent IDs, enabled analytics without a Zaraz consent purpose, and approved ads without configured TCF consent. It accepts only string numeric consent/feedback/ad-slot IDs. `client.ads.personalized` is not a supported setting: the initial advertising contract permits nonpersonalized requests only. Feedback board URLs are restricted to Sleekplan domains by the shared parser. `client.consent.policyLanguage` must be an iubenda-supported locale: `en`, `en-GB`, `it`, `es`, `nl`, `fr`, `de`, `ru`, `pt`, `pt-BR`, or `da`. Arabic currently requires an external CMP fallback and a vendor-supported, licensed Arabic policy; OffMenu does not generate a substitute policy.

Useful runtime secret names, supplied separately from `THIRD_PARTY_CONFIG`, are: `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `BREVO_API_KEY`, `BREVO_SENDER_EMAIL`, `BREVO_SENDER_NAME`, `PROVIDER_VAULT_KEY`, and `SUPPORT_EMAIL`. Optional CI-only names are `SNYK_TOKEN`, `SONAR_TOKEN`, `SONAR_HOST_URL`, and `SONAR_PROJECT_KEY`. The validator reports only an `emailConfigured` boolean and the prerequisite names, never a credential value. Names are listed for deployment setup only; this branch contains no supplied live credentials. Authorized administrators can validate and replace shared application credentials through the sealed settings route; intentional support/email delivery uses those credentials server-side. Personal provider credentials remain owner-scoped.

The [third-party workflow](../.github/workflows/third-party-services.yml) retains no-cost application checks for explicit manual release validation: npm tests, i18n, build, locale-edge tests, and Python tests. Automatic push and PR execution is disabled; development uses affected checks while preserving actual required security and branch contexts. The manual declaration does not prove hosted dispatch availability, which also requires the workflow on the default branch; this change does not modify `main`. Snyk and Sonar jobs run only from a manually dispatched workflow with `run_external_scans` selected and existing credentials/configuration supplied. A requested scan with missing credentials fails before any scan command runs, rather than reporting a green skipped scan. No account, paid service, production environment, advertising placement, consent record, email, or external scan is activated here.

AI-provider history is development-tool history. It does not authorize a runtime assistant, provider credential, user-data transfer, or an AI product feature. Health, activity, retailer, and approval-gated food sources remain deferred until their own product, legal, and provider approvals are complete.

## Administrator operations

The account panel exposes global service configuration, write-only shared credential replacement/disabling, application defaults, service feature controls, per-account service caps, retention for new delivery requests, and value-free audit history to fresh trusted Identity `app_metadata.roles` entries `admin` or `offmenu-admin`. A public-source panel can suspend/reactivate existing reviewed public policies without changing their rights or publishing personal records. See [settings](admin-settings.md), [source operations](admin-operations.md), and [client behavior](admin-client.md).

Existing installations require both additive migrations `apps/web/server/admin-schema.sql` and `apps/web/server/admin-operations-schema.sql`; fresh installations include the same tables in `apps/web/server/schema.sql`. Apply migrations through the normal reviewed deployment process before using admin controls. No migration or production deployment was performed in this task. Provision roles in the authentication provider's trusted administration surface. Browser/user metadata and shared-kitchen roles cannot assign application administrator authority. Infrastructure deployment, domain management, provider account approval/billing and CI credentials continue through their respective privileged provider/GitHub dashboards. App administrator roles do not grant those external account permissions.

Personal pantry/health/profile operations and private provider connections/results continue to use the authenticated owner or an explicitly authorized sharing scope. There is no admin browsing, impersonation, credential export, private-result selection, or promotion endpoint. Defaults seed new local profiles and never overwrite a saved profile; default language remains below explicit/account/browser/geographic language preferences. Shared service credentials are sealed separately from personal credentials and never appear in admin readback, public capabilities or audit.

## Integrated feedback and customer relations

Native private case threads, contextual recipe/translation reports, reviewed public recipes/comments, opt-in community profiles/trophies, moderated discussions and localized updates are implemented on `third-party-services` at `65805762`; see [functional verification](third-party-functional-validation.md) and [integration readiness](third-party-integration-readiness.json). The native care client replaces the external board/widget in the application. The architecture document retains its earlier recommendation history; broader proposals there are not all delivered. Scoped personal AI and trusted administrator MCP management are also implemented following the later explicit user authorization. These facts do not activate historical AI providers, prove provider entitlement, or establish production integration/deployment. Zero additional service/hosting spend remains the requirement; capacity and optional outbound email remain unqualified.
