# Public source administration

`/api/admin/sources` accepts only a freshly verified Netlify Identity user whose trusted `app_metadata.roles` includes `admin` or `offmenu-admin`.

It lists and changes only existing, reviewed public source policies, alongside a sanitized operational audit. A write is a confirmed compare-and-swap of `active`; it cannot change a policy document, licence, audience, action, source identifier, or publication rule. The value-free audit records actor, source identifier, revision, action, and time. A nonce lock plus the preceding update's `changes()` result makes the source update and audit one atomic D1 batch.

This administration surface does not query or expose user state, private documents, provider connections, service requests, health records, or user-supplied credentials. Identity role provisioning remains in the Identity provider dashboard.

Fresh installs use the canonical schema. Existing installs apply `apps/web/server/admin-operations-schema.sql` as an additive migration alongside `apps/web/server/admin-schema.sql`. Neither migration has been applied to production in this task.
