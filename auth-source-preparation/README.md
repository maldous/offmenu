# Reviewed authentication source preparation

This inactive source package contains the reviewed email callback corrections and
Google return correlation adapter. The current application does not import or
mount it. Email actions and OAuth capabilities remain off until an owner supplies
the exact qualified configuration. The selected OAuth adapter supports Google;
other providers configured in the identity realm remain unsupported here.

The callback classifier rejects duplicate accepted fields before constructing the
SDK. Google return correlation retains its one-time nonce, exact return origin
and path, and verified-subject checks. Credentials remain with the existing SDK.

Run `node auth-source-preparation/build.mjs` from the repository root to reproduce
the final reviewed browser assets. The build verifies their exact hashes and
writes only this package's ignored `dist` directory. It makes no network request
and does not modify the normal application build.

The integration patch targets the separately retained production source commit
`d22590723c943050edc56919ad5618956dd837e6`; that source has a different composition
from the current development application. The strict asset helper requires the
original three compiled preimages. Neither artifact applies itself. A future
adoption must reconcile the actual composition and retain the complete corrected
asset, rather than mixing an older standalone bundle with a new source hook.

The SQL file is source only. No schema, provider setting, account, email delivery,
session, runtime route or deployment is activated by this package. Actual email
delivery, confirmation, recovery and matching-subject acceptance remain open.
Actual Google callback, return and nonce-consumption acceptance also remain open.
Generated source checks do not establish those live results.
