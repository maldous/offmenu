# Private local product lookup

This development-only adapter reads one explicitly selected, immutable local
snapshot. It is disabled by default and accepts only the selected loopback origin,
existing verified Netlify session, source scope and runtime owner binding.

The worker route delegates authentication to the application's existing session
endpoint. Only an exact barcode reaches the native reader; account subjects,
cookies and authorization headers do not. Responses retain source variants,
unknown values, provenance, attribution and truncation indicators. They are
private, unreviewed source observations, not canonical or Gold records.

Limits are eight products, four candidate nutritional profiles per product,
32 metrics per profile and 64 KiB per response. These nutritional profiles are
source records, not personal user profiles. The Python reader opens the selected
snapshot read-only and rejects a changed snapshot. The native adapter also
requires the current owner-issued source selection. This repository does not
contain the snapshot, operational source permissions or runtime admissions.

The portable tests use generated data only. The separately retained local
source qualification is not a live authenticated HTTP acceptance test. An actual
signed-in session is required to complete that acceptance; the private UI remains
off until the authenticated bounded-output check is complete.

This source package does not activate a route, migrate a database, provision an
account or deploy anything. Runtime composition and source-use permissions are
separate from source publication.
