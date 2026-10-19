# Private-original Vary policy correction

## Scope

This narrowly removes the generic Vary refusal from application-private file
saving in `scripts/save-private-original.py:download_headers` and
`offmenu/refresh/known_asset_intake.py:checked_headers`. A single syntactically
valid Vary field such as Cookie or Origin no longer blocks an otherwise valid,
authorized private-original save merely because it differs from Accept-Encoding.
This also covers the media intake's already-pinned publisher redirect check;
redirect identity, capability checks and request budgets are unchanged.

The ordinary HTTP-cache policy in `offmenu/refresh/acquisition.py` is unchanged
and still refuses unsupported Vary, private and no-store responses. Private
saving continues to record `responsePolicy.vary=unsupported` as a descriptive
fact with `httpResponseCached=false`, `httpCacheReuse=false`, and
`httpResponseCacheEnabled=false`. It does not turn those responses into shared
cache entries or retain raw Vary values in metadata.

The five exact comprehensive WFP/PLOS source contracts contain no Vary-specific
condition. Their expected media, exact original request identity, query pairs,
rights, source-specific conditions and downstream holds remain unchanged.
Legacy PDF contracts with an explicit `expectedResponse.vary` remain enforced
by the existing exact response-contract comparison. Media sources remain closed
to their exact pinned contracts; introducing a new condition requires its usual
source-contract review, not an implicit Vary exception.

## Preserved boundaries

- Syntax and 8192-character value bounds, including ignored Cookie/CSP fields.
- Duplicate nonignored headers, including duplicate Vary, Content-Length,
  Location, Content-Type and other critical names.
- Content-Encoding identity requirement and all framing/media checks.
- Media field-count and shared 64 KiB header-envelope limits.
- Exact source URLs, methods, bodies, queries, redirect host/path/capability
  validation, connection closure and per-source/aggregate request budgets.
- No ambient authentication, cookies, proxy credentials, raw capability output,
  source discovery, cache reuse, retries, intent resets or custody promotion.
- The existing failed-no-retry and partial/uncertain-intent blocks. This patch
  does not create authority for any new request or recover the five failures.

WFP 302 redirects remain `source-response-not-permitted`, with zero body bytes
and no follow. A PLOS origin response with duplicate nonignored headers or an
oversized value still fails before any storage request. Unsupported Vary cannot
be asserted as the historical `invalid-response-headers` cause: in current code
that generic error arises before the later Vary gate, and the original report
lacks the offending header. The frozen HEAD proposal is unchanged.

## Composition

Prepared against `/workspace/shared/offmenu-opc-progress-amendment/composed`.
Only the two production header functions above change. The patch does not touch
`run_selected` signatures or bodies and is intended to compose with the parent's
separate fetch/parse isolation and `reuse_only` work. Apply the narrow patch;
do not overwrite a concurrently revised full source file with an older overlay.
No runtime/selection/owner handoff or activation artifact is changed here.

The existing test that asserted Vary: Cookie rejection is explicitly revised
to assert private Cookie/Origin acceptance and retain its gzip rejection. No
other existing policy expectation changes.

## Verification

`tests/test_private_vary_policy.py` adds 16 fully offline tests. Socket creation,
connection and DNS resolution are patched to fail. Tests cover:

- Validly framed private PDF/CSV/JSON/DOCX Cookie and Origin acceptance.
- Descriptive unsupported facts, no HTTP cache and no raw Vary values persisted.
- Actual CachedAcquirer rejection before body reads, plus unchanged cache policy.
- Explicit legacy source response-contract enforcement and closed media pins.
- Duplicate/oversized/malformed values, encoding, framing and envelope failures.
- WFP redirect no-follow, PLOS duplicate/oversize rejection before storage,
  wrong redirect identity, and failed-intent no-retry after each rejected attempt.
- Synthetic private saving and zero-network reuse under the unchanged clocks.

The existing private-save, media-intake and shared-cache suites are also run.
The frozen inventory records exact suite results and hashes. No actual source
HTTP, Foo access, publication, or failed-intent mutation was performed.
