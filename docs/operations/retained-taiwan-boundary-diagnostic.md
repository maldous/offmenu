# Taiwan retained-original failure diagnosis

## Established from the actual owner run

The immutable report commit is `c041a0ce815747414df8454865fee01a07149fec`,
with summary SHA-256 `213b9c4fb27fa961f26ae0211db29fe7040c5c9e30dac626b0e1a98e1ae5ce6e`.
The executing source was `d97316cf3bdd9fce2d415b87a708d071ad8074e7`.

The three selected Eastern Regional Branch PDF sources returned HTTP 200,
`application/pdf`, identity content encoding, and passed the exact response
contract checks. Their bodies were retained locally before PDF-content
validation rejected them:

| Source ID | Retained bytes | Failed result SHA-256 |
| --- | ---: | --- |
| 14101 | 2,290,082 | `1abb104dea5275b1d1cdd557e7b26017fb30bf9b134be3ec656f030ccf523e9b` |
| 14102 | 1,136,770 | `7106964b9e0f792523f3c2fc952005b45b4fd506ccb94c9e44224c4a138f68d2` |
| 14103 | 3,063,624 | `df0e955daedeef00e594d174ec9e64bda282b89469433737fe1606c6c7b71c62` |

The unchanged `validate_original` function emits `source-header-mismatch` for
either of two PDF predicates: the first five bytes must be `%PDF-`, and the last
4,096 bytes must contain `%%EOF` followed only by PDF whitespace through the
end of the file. The published result cannot distinguish these branches.
The error does not establish an HTTP-header defect, invalid MIME, malformed
PDF, valid PDF preamble, or harmless trailing data.

No raw original or retained partial was available in this engineering
environment. No source request, HEAD, GET, range request or retry was performed.
Changing the MIME check or weakening either PDF predicate is not justified by
the available evidence.

## Bounded diagnostic stage

`scripts/diagnose-retained-taiwan.py` provides
`run_diagnostics(output_root, absolute_deadline)` and the closed-schema
`sanitize_diagnostics(report)` function. The owner-mode collector calls this
under its existing exclusive `fixed-selection.lock` lease and without GitHub
credentials in the collection environment. The wrapper owns persistence and
metadata-only publication; the diagnostic module writes no files.

Only the three exact failed-result records, source-contract directories,
failed successor intents and existing `original.partial` files are read.
The historical owner UID, runtime root, contract hashes, failed-result hashes
and retained byte lengths are fixed. Symlinks, nonregular files, hard-linked
files, wrong owners, broad private-custody permissions, incompatible custody
state, metadata mismatches and changed-during-read files fail closed.

The diagnostic reads no more than 6,490,476 body bytes in total, computes a
SHA-256, and derives facts from at most the first 1,024 and final 4,096 bytes of
each file. Its metadata-only report is capped at 16 KiB. It emits booleans,
bounded classifications, offsets, byte counts and hashes, never body excerpts,
encoded body bytes, cookies, raw headers or arbitrary exception messages.

The stage reports the exact current PDF predicate that would fail. An
`observed` item means the retained-byte inspection succeeded; it does not
mean the document is a valid PDF or that acquisition is accepted. A `complete`
diagnostic likewise describes observation completion only. Errors and deadlines
remain explicit per item.

The newly computed digest identifies the bytes observed now. Historical body
identity is explicitly unestablished because the failed run did not publish a
partial-body digest. Any later parser-based analysis must remain read-only,
use documented parser behavior, and separately justify a narrow correction.

## Preserved scope

No source contract, HTTP/MIME validation, PDF acceptance predicate, acquisition
selection, failed intent, partial, reservation, original, provenance record or
runner control state is changed by this stage. It enables no acquisition,
automatic retry, repair, truncation, conversion, promotion, normalization,
semantic parsing, gold admission or additional source requests. The seven
successful originals remain subject to their existing reuse-only rules.

The owner should use the reviewed, pinned reusable collection entrypoint that
integrates this stage. Do not run an older whole-source batch or delete an
intent to obtain diagnostics. Failed Taiwan originals remain held until the
new sanitized observations are reviewed. No automatic runner resumption is
authorized by a diagnostic result.

## Verification

Synthetic offline tests cover exact metadata/source binding, failed intent
state, current-validator predicate parity, BOM/whitespace preambles, missing
EOF and trailing data, exact/bounded byte reads, complete digests, repeated
read-only execution, per-item deadlines/failures, no network/parser/write API,
mutation during reads, symlinks, hard links, file ownership and permissions,
FIFOs, conflicting custody files, deeply malformed metadata, and closed-schema
rejection of raw fields or promoted claims. These tests do not establish the
content or validity of the actual retained Taiwan files.
