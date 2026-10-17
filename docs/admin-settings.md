# Administrative service settings

This is an additive D1 migration: apply `cloud/admin-schema.sql` after the
account schema. It creates one `app_settings` row (`id = global`) and a
value-free audit table. The audit records only the current verified Identity
actor ID, resulting revision, changed setting paths and timestamp.

Only a fresh Netlify Identity user object with an exact `app_metadata.roles`
entry of `admin` or `offmenu-admin` can read or change these routes. Browser
claims, user metadata, email addresses, kitchen roles and token contents do not
grant administrator access.

`GET /api/admin/session` returns the authenticated user's `{isAdmin}` state.
`GET /api/admin/settings` is admin-only and returns revisioned public settings,
credential configuration metadata and value-free audit entries. `PUT
/api/admin/settings` requires same-origin `{revision,confirmed:true,settings,
credentials?}` and uses compare-and-swap revisioning. Credential values are
sealed with the existing vault under a global AAD and are never returned.

Each write carries a random `write_id`; the audit insert is conditional on that
nonce, so an update that loses a concurrent compare-and-swap cannot create an
audit entry even when timestamps coincide. Stored credentials apply per key:
an omitted key keeps the legacy environment value, while an explicit `null`
masks it. `loadAdminRuntime` also serializes validated global settings into
`SERVICE_GLOBAL_SETTINGS` for application-wide runtime use.

The credential allowlist is `SENTRY_DSN`, `BREVO_API_KEY`,
`BREVO_SENDER_EMAIL`, `BREVO_SENDER_NAME`, and `SUPPORT_EMAIL`. A `null` patch
persists a disabled override. A saved credential key overrides its legacy
environment value; an omitted key continues to use that environment value. On
malformed storage or failed decryption, runtime configuration falls back to safe
disabled defaults rather than enabling optional services.
