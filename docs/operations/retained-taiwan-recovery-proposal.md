# Exact retained Taiwan PDF recovery proposal

Status: inactive source-only proposal. It is not wired into collection,
preparation, a launcher, a service, or a scheduler. No actual Taiwan body has
been examined in this development environment, and no host execution or source
download was performed here.

## New verified evidence

The second owner-run report is commit
`3bbb6835568dcc58ff147f8b1c459c5e37dfc3e0`, result SHA-256
`7e844aae16ed22b088c2643fec3f9722110cdad30b9f0fcc264c2db57eba4795`.
All 28 published metadata file identities were independently verified. Its
retained-Taiwan diagnostic found an exact UTF-8 BOM before `%PDF-` at offset 3
in all three retained files. The existing terminal-EOF rule passed, with two
trailing PDF-whitespace bytes. This explains the current strict-prefix failure.

| Source | Retained bytes | Observed body SHA-256 |
| --- | ---: | --- |
| 14101 | 2,290,082 | `b49be9438831bd5446669172408c7d9aab9307f0b1cc008b73e72414501500a0` |
| 14102 | 1,136,770 | `188749647a3aa866fccaf4c038928b7327caf37821d1193c631fb8ff3cd7b88b` |
| 14103 | 3,063,624 | `133041c9bdd981977434165c9978d95537d7e8ae42cbcd866fcb7b17f2ce461e` |

The hashes identify bytes observed during the diagnostic. They are not
publisher checksums and do not retroactively prove historical body identity.
The exact observed old failed-intent hashes are also bound in the new module.

## Why a restricted parser check is appropriate

PDF header conformance and tolerant parser behavior are distinct. Adobe's
[PDF 1.6 reference](https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/pdfreference1.6.pdf),
Appendix H, implementation note 13, describes historical viewer tolerance for
a header within the first 1,024 bytes. Adobe's later
[Acrobat troubleshooting archive](https://helpx.adobe.com/archive/acrobat/acrobat-9-troubleshooting.pdf)
documents stricter security-oriented handling of bytes preceding the header.
Neither is a reason to accept arbitrary preambles or declare strict conformance.

Poppler's [PDFDoc implementation](https://github.com/tsdgeos/poppler_mirror/blob/master/poppler/PDFDoc.cc)
searches for the header near the beginning and adjusts its logical stream
start. The maintainer mirror is linked from the
[Poppler project website](https://poppler.freedesktop.org/). The
[pdfinfo utility documentation](https://github.com/tsdgeos/poppler_mirror/blob/master/utils/pdfinfo.1)
and [pdftotext utility documentation](https://github.com/tsdgeos/poppler_mirror/blob/master/utils/pdftotext.1)
describe document metadata, page traversal, stdin/stdout operation, and error
statuses. Parser success is operational structural evidence, not proof of
complete PDF-standard conformance or semantic correctness.

The local synthetic test environment has Poppler 25.03.0. Complete synthetic
BOM-prefixed PDFs pass both utilities without diagnostics; malformed files
containing only a signature and EOF fail. The actual owner report records
Poppler 24.02.0. Its behavior on the actual three retained files is untested
until a reviewed owner invocation performs these checks.

## Inactive validation API

`validate_selected(source, output_root, absolute_deadline)` requires:

1. One of the exact three source keys and its unchanged full source-contract
   hash, serialized using the acquisition engine's canonical format.
2. The existing owner runtime, owner identity, failed result record, old
   failed-no-retry intent, private modes and exact retained byte extent.
3. Exact body and failed-intent hashes from the verified second-run report.
4. Exactly UTF-8 BOM followed by a supported `%PDF-` version header, plus the
   unchanged strict terminal-EOF predicate. No other preamble is accepted.
5. Matching installed pdfinfo/pdftotext versions; successful pdfinfo output;
   unencrypted status; a page count from 1 through 2,000; and successful
   pdftotext traversal of all those pages. Any parser diagnostic is a block.
6. Stable body, failed-intent, private-directory and runtime identities after
   parsing. A changed or replaced path cannot produce a valid proposal.

The existing collector must hold its writer lease and call from its main
thread; other threads receive `parser-isolation-unavailable` before a child is
started. Each source is limited to at most 60 seconds within the caller's deadline. Parser
processes receive only fixed commands and stdin data, never passwords or
network URLs. They run with a clean credential-free environment and resource
limits via installed `prlimit`: 768 MiB address space, bounded CPU time,
32 file descriptors and no regular-file output. Output and diagnostics are
drained with strict byte caps; page text is discarded, not persisted or
returned. Missing capabilities, encryption, warnings, malformed structure,
limits and deadlines produce explicit blocked results.

Document checks and version probes share the same scoped process ownership.
SIGTERM, SIGINT and SIGHUP are recorded during process creation and assignment,
then the owned process group is killed and its leader reaped before the signal
is redelivered using the caller's restored handlers. Signals already ignored by
the caller remain ignored. A custom handler that returns produces a blocked
`parser-interrupted` result. The guard also covers interruption during cleanup;
it does not claim to handle SIGKILL or machine failure. Synthetic regressions
check termination during execution, before spawning and immediately before
Popen returns, plus handler restoration and version-probe cleanup.

The successful report contains a proposal for
`validated-retained-original-reference/1`, referencing the existing
`original.partial` path and its exact digest. It always states
`dispositionApplied: false`. It does not rewrite, rename, copy, strip the BOM,
reset an intent, create an original, alter a contract, or perform a request.
It leaves the unknown original acquisition timestamp unset.

## Separate integration review required

Before activation, the collection owner must review an additive custody
receipt that preserves the historical failed intent and binds the complete
validation report. Existing generic acquisition and media validation remain
unchanged by this patch. A consumer must never translate the proposal into
`source-header-mismatch` suppression or blanket retry permission.

If later selected for preparation, the unchanged retained-file identity must
flow into the existing preparation queue. The optional helper
`exact_selected_bom_identity(source, data)` recognizes only the same full
source-contract/byte-digest combinations. It is a proposed narrow integration
hook, not a global media-sniffing exception and not proof that the parser ran.
The parent must also review the actual parser result and the additive custody
receipt before relying on that hook. No parser failure may be bypassed.

All current redistribution, commercial reuse, translation, normalization,
semantic/gold admission and country-completeness holds remain unchanged.
This proposal supplies no runner-resume authority and does not activate
scheduled work or a new acquisition route.
