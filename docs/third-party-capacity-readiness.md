# Third-party capacity readiness

Assessment date: 2026-10-14 (Australia/Melbourne). This is a read-only capacity assessment for Cloudflare account `7edd51038e07b5b84a635b3ff7e11144`. It made no account change, deployment, D1 query, private-content read, secret read, or email send.

## Current account evidence

The connected Cloudflare API rejected the bounded metadata request with `10000: Authentication error`. The request was limited to account subscriptions, billable usage, D1 database metadata, Worker script metadata, Workers account settings, and Email Sending limits. No endpoint returned account data.

| Capability | Account plan, usage, and headroom | Capacity decision |
| --- | --- | --- |
| Workers / Pages Functions | Unknown: subscription, Workers usage model, current requests, CPU use, and budget were not readable. | Do not enable a paid or volume-sensitive capability from this evidence. |
| D1 | Unknown: database metadata, storage, row reads, and row writes were not readable. | Do not apply a production migration or enable data-intensive paths from this evidence. |
| Email Sending | Unknown: the account limit endpoint returned no limit, and sending-domain qualification was not checked. | Keep outbound email disabled. |
| Billing | Unknown: no subscription or billable-usage result was available. | There is no approved cost gate or confirmed headroom. |

An unavailable measurement is neither zero usage nor available capacity. It is a blocked qualification. The local application budgets remain conservative safeguards only; they do not establish Cloudflare capacity, spending authority, or a paid-plan authorization.

## Relevant provider constraints

- Pages Functions consume Workers request quota. On the Workers Free plan, the published shared limit is 100,000 requests per day and resets at midnight UTC; paid Workers has a minimum monthly charge and usage-based charges. [Cloudflare Pages Functions pricing](https://developers.cloudflare.com/pages/functions/pricing/) and [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/)
- D1 free-tier row-read and row-write limits are enforced daily. When exceeded, queries fail until midnight UTC; stored data remains intact. [Cloudflare D1 free-tier enforcement](https://developers.cloudflare.com/changelog/post/2026-09-01-d1-free-tier-limit-enforcement/)
- Email Sending begins with a conservative daily quota that changes with account standing and deliverability. A sending domain must be onboarded before arbitrary destinations are available. [Cloudflare Email Service limits](https://developers.cloudflare.com/email-service/platform/limits/)
- Cloudflare exposes active subscriptions and product-level usage/cost in Billing; budget alerts are an account configuration to be set by an authorized administrator. [Cloudflare billing overview](https://developers.cloudflare.com/billing/understand/how-billing-works/)

These provider-wide rules cannot establish the plan or remaining headroom of this account.

## Required read-only qualification before enablement

An authorized administrator should grant a read-only connection that can retrieve only the following metadata, then record the timestamp and values in a change review:

1. Active account subscriptions and Workers usage model; current billing-period product usage and approved budget threshold.
2. D1 database metadata and aggregated storage/row-read/row-write usage, without executing SQL or returning table rows.
3. Worker/Pages request and CPU usage for the current reset period, alongside configured runtime limits.
4. Email Sending limits, account reputation, and sending-domain verification status, without inspecting message bodies, suppression recipients, or sending a message.

Enable one capability only when its plan requirement, current use, remaining headroom, owner, cost ceiling, and reset/billing window are recorded. If any reading fails or is unavailable, retain the relevant feature flag as disabled and repeat the same bounded read later. This document does not qualify production capacity or authorize a purchase.

## Authenticated follow-up — 14 October 2026, 13:33:52 AEDT

Selected access is now verified: Cloudflare identity, Worker script/account settings and OffMenu D1 metadata returned successful authenticated reads. The database metadata reports 5,406,720 bytes and 24 tables; no SQL or user records were read. Netlify OffMenu project metadata and GitHub repository metadata reads also succeeded. This supersedes the earlier broad access uncertainty for these endpoints only.

The subscriptions endpoint still returns `Error: Cloudflare API error: 10000: Authentication error`. Email Sending limits returns HTTP 200 with `quota: null` and `usage: null`. Current billing, request/CPU/daily row-use headroom and outbound entitlement remain unqualified. Direct unauthenticated runner reads of OffMenu health/services returned HTTP 403; management API authentication does not resolve that distinct runtime-access result. The existing Netlify project reports `nf_team_pro`; this is not a new purchase or proof of zero-cost headroom. No feature activation, credentials, grants or account configuration changed.
