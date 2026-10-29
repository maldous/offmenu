# Private support and explicit email

`apps/web/server/services-schema.sql` is additive to the account D1 schema. It retains a
sealed support or email payload for 30 days and only exposes request metadata to
the owner. At expiry `cleanupServiceRequests(env)` erases the sealed payload but
retains an idempotency tombstone, then removes old hourly rate-limit buckets.
The tombstone holds a versioned HMAC-SHA256 over the exact payload, owner and
request kind, keyed by `PROVIDER_VAULT_KEY`; it never holds a raw payload hash.
Changing that key makes an old idempotency key fail closed rather than resending.

The Worker module is `serviceSupportRoutes(request, env, { verifiedUser,
boundedJSON, reply })`. It accepts only same-origin, verified Netlify Identity
requests. It never accepts a recipient supplied by the browser.

| Route | Request | Result |
| --- | --- | --- |
| `GET /api/services/support` | authenticated | `{requests:[{id,kind,status,createdAt,updatedAt}]}` for the current owner |
| `POST /api/services/support` | `{idempotencyKey,confirmed:true,subject,message}` | sends only to configured `SUPPORT_EMAIL`; `201 {request:{id,status:"sent"}}` |
| `POST /api/services/email` | `{idempotencyKey,confirmed:true,document:{title,text}}` | sends plain text only to the verified account email; `201 {request:{id,status:"sent"}}` |

`idempotencyKey` is 16–128 `[A-Za-z0-9_-]` characters. Reusing it with changed
content returns `409`. A `pending` or `unknown` result also returns `409` and
is never retried automatically. `failed` requests are not retried under the
same key; a user can make a newly confirmed request with a new key.

Set Worker secrets/configuration outside source control:

* `BREVO_API_KEY` — secret, sent only as Brevo's `api-key` request header.
* `BREVO_SENDER_EMAIL` and `BREVO_SENDER_NAME` — verified Brevo sender.
* `SUPPORT_EMAIL` — optional support recipient; without it, support submission
  remains unavailable.
* `PROVIDER_VAULT_KEY` — existing 64-character hex vault key; it seals retained
  request content using per-request authenticated encryption.

Email-to-self requires the server-confirmed top-level Netlify Identity `email`
field (`confirmed_at` or `email_confirmed_at`); browser-provided profile or
metadata email values are never used. The implementation calls exactly `https://api.brevo.com/v3/smtp/email`, does
not create contacts, subscriptions, campaigns, or marketing sends. No live
requests or provider account changes are part of this change.
