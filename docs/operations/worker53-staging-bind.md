# LK/LR/LS/LT source-input binding package

This portfolio-only successor targets verified develop
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. It contains seven pinned
retained-metadata bindings and one deterministic metadata CLI. No source body is
opened, parsed or normalized by the CLI. No download or production factory exists.
Raw inputs remain on Foo; absolute local metadata references are intentional.

```sh
python3 -m offmenu.refresh.portfolio53 --now 2026-10-18T05:00:00Z > metadata-report.json
python3 -m offmenu.refresh.portfolio53 --now 2026-10-18T05:00:00Z \
  --previous-report metadata-report.json > metadata-replay.json
python3 -m unittest discover -s tests -p test_portfolio53.py -v
```

`config/portfolios/worker53-staging.json` is application-owned configuration,
not a user-defined SourceContract or dynamic plugin registry. Its exact JSON
metadata paths, sizes, hashes, roles and JSON pointers are checked with shared
`safe_path` and `strict_json`, plus a bounded nonblocking regular-file read on one
descriptor. Both file identity and the expected pin are checked without reopening;
nonregular replay inputs and parser depth failures return fixed diagnostics.
Opaque raw asset references are never opened or rehashed. Missing, held,
malformed and stale inputs remain independent from other sources' reports.
Diagnostic codes contain no source values or exception strings.

The unchanged JSON file is the source mirror of the installed inert Python
literal in `portfolio53_catalogue.py`. The default `load_catalogue()` returns a
deep copy without filesystem access, so wheel/sdist consumers do not depend on
the repository's external `config/` directory. This transports code declarations
only: it does not package, read or authorize the referenced source metadata.

Field declarations bind downstream targets to existing metadata selectors and
source-coordinate descriptions. They declare a proposed source-native mapping,
not evidence that a real record was staged or qualified. The LR price binding
preserves the `price`, `unit` and `date` headers; no source labels, currencies or
lexical decimals are converted. Units, bases and timestamps not established by
the selected metadata remain explicit unknowns. Markets are not merchants;
donation guidance, recipe mentions and school menus do not become composition.
The six country data-type requirements remain incomplete.

The authored one-row fixture calls the existing `acceptance.SourceContract` and
`qualify`, with `fixture=True` permanently fixed in code. Source-field coverage
uses the existing `field_provenance.field_origin_errors`; an additional bounded
semantic check verifies exact fixture literals and coordinates. Qualified
fixtures never install a production admission, emit a gold receipt, or qualify
real payloads. Real SourceContract factories remain unconfigured. This avoids
manufacturing permissions from evidence-file hashes or source manifests.

Original acquisition age is separate from metadata validation time. Metadata
validation cannot reset original age or certify source bytes. Before 30 days the
intent is retained-cache reuse only. At 30 days it is a stale-input diagnostic
and request for revalidation evidence, never a network action. Missing time means
unknown/no download. There is no `force` option. Deterministic report identity
ignores elapsed day count while preserving source pins and decisions: unchanged
metadata within the same policy state returns `verified-metadata-no-op`. Tampered
previous-report identities fail; crossing a policy boundary changes identity.
This is metadata intent, not a replacement acquisition/cache engine.

## Exact shared-interface proposal for integrator00

No shared-core changes are included. Current `core.cache_policy` identifies the
Wikibooks pilot; `policy.plan_fixture` requires a registered fixture, and
`CachedAcquirer.acquire` can perform filesystem/body/network work. None is invoked
to masquerade this portfolio as an existing source or to activate acquisition.

If Morgan selects the shared helper proposed by integration00, use one pure
`policy.plan_retained_input` interface accepting reviewed source/release and
input-manifest digest, original acquisition time, independent validation time,
UTC planning clock, retained-cache evidence and explicit holds. Return typed
reuse/revalidation/unknown intents with zero network and no asset verification,
permission or admission claim. Validate the identity/time chain, preserve the
original acquisition age and ensure no force flag permits automatic download
under 30 days. No registry changes, downloader, I/O or country engine belongs in
that helper. Integrator00 owns any implementation and independent review. The
portfolio CLI can later delegate its small metadata intent guard to that approved
interface; its absence does not block current metadata evidence delivery.

## Remaining execution dependencies

- Morgan must select exact native staging scope and independent review; these
  configuration files are not production contracts or dataset acceptance.
- LK: eight printed-total discrepancies and malformed age scope remain literal;
  explanatory methodology and structured-use evidence are missing.
- LR: existing 21,214 price / 59 market candidates and scoped reviews are reused,
  not reparsed. Production field-origin qualification and native-scope acceptance
  remain separate from canonical dictionary/equivalence requirements.
- LS: current metadata-holder attestations from existing32 and20 are retained;
  composition table/method/action-use and booklet author/edition/derivative grant
  remain NOT_HELD/UNKNOWN, not a new legal denial.
- LT: nine recipe mentions remain noncanonical; recipe-specific/third-party use
  and school-menu edition/page/action applicability remain unresolved.

Source holds, Finland/Frida restrictions, NO/FR native crash restrictions,
403/private/credential and other actual denials, mandatory auto_review,
production/CIX pauses and DEV7645 custody are unchanged. No source acquisition,
publisher contact, broad reprocessing, shared-engine edit or country completion
is part of this delivery. Review and develop integration are still required.
