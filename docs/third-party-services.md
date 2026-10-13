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

Useful runtime secret names, supplied separately from `THIRD_PARTY_CONFIG`, are: `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `BREVO_API_KEY`, `BREVO_SENDER_EMAIL`, `BREVO_SENDER_NAME`, `PROVIDER_VAULT_KEY`, and `SUPPORT_EMAIL`. Optional CI-only names are `SNYK_TOKEN`, `SONAR_TOKEN`, `SONAR_HOST_URL`, and `SONAR_PROJECT_KEY`. The validator reports only an `emailConfigured` boolean and the prerequisite names, never a credential value. Names are listed for deployment setup only; this branch does not supply, rotate, validate, or transmit a credential.

The [third-party workflow](../.github/workflows/third-party-services.yml) runs no-cost application checks: npm tests, i18n, build, locale-edge tests, and Python tests. Snyk and Sonar jobs run only from a manually dispatched workflow with `run_external_scans` selected and existing credentials/configuration supplied. A requested scan with missing credentials fails before any scan command runs, rather than reporting a green skipped scan. No account, paid service, production environment, advertising placement, consent record, email, or external scan is activated here.

AI-provider history is development-tool history. It does not authorize a runtime assistant, provider credential, user-data transfer, or an AI product feature. Health, activity, retailer, and approval-gated food sources remain deferred until their own product, legal, and provider approvals are complete.
