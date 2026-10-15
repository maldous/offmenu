# Care updates and notifications

`/api/care/updates` exposes only published updates whose publish time has arrived, in the requested `en` or `ar` locale. Updates are native Worker/D1 records; no vendor board, email provider, profile data, kitchen data, health data, or provider connection is read.

Administrators create drafts and use revisioned publish, withdraw, or edit actions. Every mutation is same-origin, role-gated, compare-and-swap guarded, and recorded with value-free audit paths.

Each authenticated owner controls in-app case, community, and update notifications, plus a separate `emailUpdates` opt-in. In-app notifications contain only a generic kind and resource reference. Email delivery is deliberately disabled: sender qualification, quota plan, and operational evidence are still missing.
