# OffMenu product operations

Use the selected reviewed commit and a dedicated checkout. `develop` accepts
reviewed integration; `main` changes only for approved product releases. The
[maintainer guide](maintainer.md) describes local dependencies, build outputs and
the small Python demo. Product build/test commands require no other project
checkout or service credentials.

## Release and deployment

Follow [`config/release-policy.json`](../config/release-policy.json). Freeze the
exact source base, head, tree, policy and artifact hashes. Independent review,
complete candidate validation, canonical tree readback and an immutable tag
are required for release. A repair creates a new candidate. Keep `main` static
between approved releases. A source merge or local build does not deploy the
application, switch authentication or publish data.

For an authorized deployment, qualify its actual platform, account, selected
bindings and existing state. Do not overwrite authentication, database bindings
or credential protection with example configuration. The generated Worker embeds
its Git commit and build time; its public health response is source identity
information, not proof that every feature or data source is working.

## Storage and authentication

`DB` is the deployment's account/application database binding. It is separate
from a local demo database and from original source corpora. Preserve the
configured provider-vault secret and account state during a change. Use reviewed
migrations rather than recreating databases or identity configuration.

The default handler retains its existing authentication verifier. Selecting an
optional authentication adapter requires its trusted session policy and enabled
configuration; a changed environment string alone is insufficient. Source and
synthetic tests do not prove hosted sign-in, provider continuity, physical-device
behavior or live account migration.

Personal REST and MCP use separately scoped, audience-bound tokens. A shared
kitchen membership does not grant access to private measurements/history.
Sensitive health scope is not automatically requested when a caller omits scopes.
External-client acceptance and delegated household access remain separately
qualified features, not an implicit expansion of token permissions.

## Sources, caching and rights

Selected source policies determine permitted lookup, retention, export,
derivation, audience and market. Unknown provider rights deny the affected
operation until qualified. A user checkbox cannot override a source policy.
Source policies are operator-maintained and cannot be replaced by anonymous
import payloads.

Resolver leases partition by source, exact query, policy and normalizer version.
Policy checks occur before reads and writes. Expired leases can be reclaimed;
failures back off. Withdrawal denies reads, and maintenance removes expired
cache/leases and explicitly expired retained records according to their actual
policy. Source integration does not enable shared contributions or behavioral
aggregation.

Private imports retain their source rights. Personal/retailer confirmations
remain private and unverified. Provider disconnect removes the account-owned
source records handled by that action; revoke external credentials at the
provider separately when intended. Sensitive health/history records use their
separately consented workflows rather than generic record scopes.

Preserve attribution and notices for public datasets. Food-place references
include the full Foursquare publisher notice and applicable Apache 2.0/CDLA
Permissive 2.0 licence copies; see [public lookup contracts and notices](places-national-expansion.md).
Normalization never relicenses an original source.

## Verification and recovery

Check the exact candidate's generated output, packaging, affected behavior and
source-policy boundaries. For a selected hosted change, record actual service,
account isolation, pagination, source citation and browser evidence separately
from the local build. Never log private records, credential values or production
snapshots.

Preserve the original operation identity when an external result is uncertain.
Observe that original effect before retrying; do not repeat a source publication,
account mutation or deployment merely because its response was lost. Keep
unrelated user data and held consumers intact until their owner records a safe
handoff. Historical evidence preserved elsewhere is not current configuration or
proof of deployment.
