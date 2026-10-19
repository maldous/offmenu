# Exact Taiwan retained-reference acceptance proposal

Status: inactive, awaiting independent review and parent/root selection. This
is an additive metadata proposal, not an accepted custody disposition. Nothing
in the collector, acquisition engine, media preparer, launcher, service or
scheduler is changed or wired to this file. No original was read or copied in
this development workspace; no Foo access, network request, actual-source
parser invocation, source download, custody write, publication or activation
was performed. Existing parser regressions use synthetic files only.

## Evidence and exact scope

Source baseline: `c74cfaee99c6d743c8d4982de4d8d8cce651b057`.
The verified third owner-run metadata report is commit
`d6ce260a296e73a9a9f1985f8c2db79b7ec5ddbf`, envelope SHA-256
`c36d6a2f8a34ad71e77d11f9bed89957cdde002d0e1820da4b4d0c1215f8556d`,
and publication receipt SHA-256
`6d363a25c06d9a6ffa8044e429de003290bcd2033c41ce23a9b2e3a25bf96825`.
The manifest contains exact repository paths to the envelope and receipt,
individual canonical validation-result hashes, complete source contracts and
existing preparation selections. The publication receipt is not a custody
acceptance, and its `baseReviewedSource` field is an ancestor reference, not an
attestation that a particular runtime source commit executed. The proposal's
baseline identifies the code being extended separately from report evidence.

| Source | Asset index | Retained bytes | Traversed pages |
| --- | ---: | ---: | ---: |
| AFA 14101, Taitung | 4747 | 2,290,082 | 8 |
| AFA 14102, Yilan | 4748 | 1,136,770 | 4 |
| AFA 14103, Hualien | 4749 | 3,063,624 | 10 |

All three third-run results are `validated-proposal`, report matching Poppler
24.02.0 utilities, exit status zero, zero diagnostics, unencrypted documents
and bounded traversal of all pages. Each still says `dispositionApplied:false`.
Those facts validate structure for the observed exact bytes only. They do not
prove publisher checksums, original acquisition times, historical body
identity, strict ISO conformance, semantic correctness or country coverage.

The full manifest is
`docs/collection-selections/retained-taiwan-acceptance-proposal.json`.
Every source, body length/hash, old failed intent hash and original failed
detail hash is bound to its corresponding third-run validation result. No
fourth source, changed source contract, changed byte, alternate file or generic
BOM-prefixed PDF qualifies. Acquisition's existing strict-prefix rule stays
unchanged.

## Existing owner context is unchanged

This proposal stays on `owner-local-comprehensive-20261018-002`, runtime hash
`28acbde120ac7d457f24af8cd2e3203927bb770137b8ce414c0d7a082e63b4ba`,
and dispatch-hold hash
`a78f209e2d1636cadf3ad913514d98472bf3e173b3c08c008ae573cade56ad8b`.
These are bound by the exact envelope and publication receipt. The existing
runtime configuration and dispatch hold are not edited. No successor handoff is
created, and OPC/progress remain on 002. If actual application needs an
additional authority artifact, it must be a separately selected, narrow
acceptance binding; this proposal leaves that authority explicitly unselected
and does not invent a new runtime or handoff.

## Reference semantics and historical custody

The only proposed object is a `validated-retained-original-reference/1` to the
existing `collection/private-originals/<exact-source-contract-sha>/original.partial`
under `/home/user/src/offmenu-data/owner-collection-runtime`, owner UID 1000.
It is a reference to unchanged bytes, not a new physical original. The BOM
remains present. Do not rename, copy, delete, truncate, replace, normalize,
redownload or retry this body. Do not create `original.pdf`, `provenance.json`
or a new acquisition reservation. Preserve `successor-intent.json` in its
existing `failed-no-retry` state and preserve the original failed detail file
byte-for-byte. Historical failed observations remain valid historical facts.

`originalAcquiredAt` stays null. The acquisition success schema currently
requires a non-null acquisition time and assumes its ordinary filename;
therefore this proposal must never be coerced into `verified-private-original`
or a fabricated acquisition-success report. Any later collection schema must
represent retained-reference acceptance separately and count reused originals
without claiming a new download, new body allocation or past acquisition date.

A future reviewed application may write only an additive, private, immutable
acceptance receipt after all execution gates pass. Proposed receipt namespace:
`collection/retained-taiwan-acceptance/<selected-manifest-sha256>/receipt-<receipt-sha256>.json`.
The receipt must bind the selected manifest's exact file digest, parent/root
selection evidence, source/asset identities, both published-result and fresh
validation digests, unchanged body and failed-record identities, applied scope,
and an actual acceptance timestamp. An acceptance timestamp is not an original
acquisition timestamp. No receipt may overwrite an old record. An identical
committed receipt may be reused only after fresh custody verification;
a conflicting receipt, incomplete prior write or uncertain state blocks reuse.
No receipt writer is implemented or invoked by this patch.

## Execution and preparation authorization gates

1. Independently review this exact manifest and any later integration patch.
   Parent/root selection must bind the reviewed manifest digest and these exact
   three references. This proposal records neither selection nor approval.
2. On the owner runtime, hold the existing single-writer lease. Resolve every
   component without symlink following; require private owner-controlled
   directories, regular single-link retained files, exact size/hash, and exact
   failed intent/detail identities. Missing, replaced, inaccessible or changed
   custody blocks; it never triggers a network fallback or a retry.
3. Run the already reviewed exact validator again under its bounded deadline,
   installed parser and resource limits. Require a fresh successful result for
   each selected identity and recheck all files and parent directories before
   committing the additive receipt. Prior published success alone cannot
   establish current custody. Do not suppress any parser failure or diagnostic.
4. Commit and verify the private additive receipt before allowing reference
   reuse. A failed or uncertain commit cannot advance any outcome to accepted.
   Report application outcomes separately from the unchanged third-run report.
5. Preparation is a separate gate. The published exact comprehensive selection
   already records `read/copy/extract:true` for these three source contracts;
   this proposal preserves that evidence and does not infer or grant new
   permissions from a parser pass or public availability. Recheck the selected
   preparation contract, per-source holds, unchanged bytes, private output
   destination, output reservation and existing free-space floor before work.
   Any permission/hold change requires the appropriate updated selection.
6. Queue the existing retained-file path and digest through the existing
   bounded preparation worker only after its integration has been reviewed.
   The source-bound `exact_selected_bom_identity(source,data)` may recognize
   only these exact full source-contract/body pairs. A hook match alone is
   neither parser success nor custody acceptance. Do not strip the BOM, alter
   generic sniffing or add a generic bypass. Unsupported/failed preparation
   remains unsupported/failed; this receipt cannot manufacture ready-nextstage.

All redistribution, commercial corpus reuse, translation, normalization,
semantic/gold admission and country-completeness holds remain unchanged.
Acceptance does not resume the runner, enable schedules, transfer claims,
release reservations, establish exhaustive claim coverage or change unrelated
source restrictions. No newly inferred permission is needed to validate this
inactive metadata proposal; actual application remains gated as described.

## Offline API and tests

`scripts/propose-retained-taiwan-acceptance.py` exposes two pure functions:

- `build_proposal(result_bytes, receipt_bytes, selection_bytes, asset_manifest_bytes)`
  requires exact raw-byte pins for all four published/baseline inputs and
  returns the deterministic inactive proposal.
- `validate_proposal(proposal_bytes, result_bytes, receipt_bytes, selection_bytes, asset_manifest_bytes)`
  checks the complete proposal against that derived result and returns
  `verified-inactive-proposal`. It explicitly reports custody unchecked and
  execution, disposition and preparation inactive.

There is no CLI, filesystem reader, source body argument, permission override,
apply flag or runtime integration. JSON object duplicate keys and non-finite
numbers are rejected. Canonical subobject hashes use the existing acquisition
format: sorted compact UTF-8 JSON, `ensure_ascii=false`, `allow_nan=false`, one
final newline. Published evidence hashes bind exact file bytes instead.

The two metadata-only fixtures reproduce the exact verified third-run envelope
and publication receipt. They contain no original bodies or page text. Run:

`PYTHONPATH=. python -m unittest discover -s tests -p test_retained_taiwan_acceptance.py -v`

Negative coverage includes activation flags, source substitution, changed
body/path/intent/detail/timestamps, altered parser results, removed holds or
review gates, duplicated/missing identities, exact evidence-byte mismatches,
malformed JSON and attempted external side effects.
