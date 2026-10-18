# Worker08 portfolio source-input metadata bindings

Task `M-STAGING-BIND-20261018-W08`; proposed source base
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`, as verified by integrator00's
`soleintegrator-portfolio-fresh-baseline-interface-result-20261018` (5798).
Local develop labels `4693cbc` and `5f5bdb6` are older ancestors, not newer
removals. The old Worker08 branch, two untracked symlinks and external receipts
remain preserved. This proposal requires independent review and integrator
readback of the live provider/candidate/base before integration.

## Deliverable and scope

Five owned paths: the portfolio module, configuration, one small authored fixture,
focused tests and this document. Shared core, registry, source adapters and CLI
entry points are unchanged. No country engine or source downloader is introduced.

The configuration binds ten retained receipt/claim source identities across
AW/AX/AZ/BA, plus all 24 country/type requirements. Actual roles, editions,
receipt hashes and Foo paths are citations, not source admission. Each real
binding remains disabled/held, with no field selectors, native units/bases or
processing grant invented. Each original or denial representation has an exact
receipt JSON pointer, hash, size, HTTP role and URL declaration; these are not
body reads or a new integrity validation. Original acquisition dates are cited where available;
unknown dates remain null. File mtimes and later validation are not acquisition.
The AW challenge, AZ Foundation403, AX table-use and BA acquisition-only holds
remain explicit. No Finland/Frida or NO/FR native handler is called.

`assess(policy, manifest, metadata=..., now=...)` accepts a trusted, reviewed
policy and detached finite JSON metadata. `assess_many` accepts independent
`(policy, manifest, metadata)` tuples and returns an outcome per source. The CLI
does not accept caller URLs, a policy file, body paths or arbitrary manifest
paths. Its only positive example is the explicitly authored synthetic fixture.
Real source flags in caller manifests cannot override policy.

Outcomes: `valid`, `missing`, `held`, `malformed`, `stale`. Holds are checked before
capturing a manifest or inspecting supplied metadata. No referenced path is
opened. For enabled authored metadata, exact input name/size/SHA and JSON bytes
must match the policy; every scalar has a shared `field_origin_errors`-validated
origin and its declared coordinate/value is compared with that pinned JSON.
Lexical values, source spelling, null units and null bases survive without
conversion, equivalence or gold claims. A valid result means a checked metadata
candidate only; body processing, source admission and country acceptance stay false.

## Shared interfaces and cache limitation

Uses existing `strict_json`, `canonical`, `timestamp`, `safe_path`, `atomic_json`,
`field_origin_errors`, `valid_input_name` and `acquisition.MIN_TTL`. It never
constructs or invokes `CachedAcquirer`, `SourceSpec`, fixture registry execution,
native handlers, a subprocess source parser, an AI service or a socket.

**No generic pure refresh planner exists at this base.** Every result explicitly
reports `refreshPlanner.status = unsupported-shared-interface`. Integrator00's
proposed `plan_retained_input` remains proposal-only; this package requests no
shared-core change or source identity spoofing. `cacheMetadata` is only an age
diagnostic for supplied metadata evidence, not a replacement acquisition planner,
retention-policy decision, body verification or permission to contact a source.

Original acquisition and checked-at times are separate, UTC and ordered. The
metadata age diagnostic uses the shared minimum 30-day constant. Under 30 days,
an eligible authored metadata candidate can be deterministically replayed with
zero downloads. At 30 days the result is `stale` with no candidate and no request;
the missing shared planner/actual source-use contract remains a typed dependency.
Recent validation does not change original acquisition age. Retention directives
and conditional refresh are not qualified here. No force/revalidate CLI exists.

Candidate identity includes source/release, exact input bundle, policy, country/
type and field origins; it excludes changing validation age. Publishing an
identical candidate is an actual file no-op (bytes, inode and mtime preserved).
Other output schemas and malformed/held/stale results are never overwritten as
successful candidates. The output is bounded metadata, not a raw data cache.

## Repeatable local commands

From this proposal checkout, with no dependency installation or live source:

```sh
python3 -B -m unittest discover -s tests -p test_portfolio08_bindings.py -v
python3 -B -m offmenu.refresh.portfolio08_bindings --now 2026-10-18T00:00:00Z
python3 -B -m offmenu.refresh.portfolio08_bindings --fixture \
  --now 2026-10-18T00:00:00Z --output /tmp/owner08-authored-metadata.json
```

The held portfolio command returns exit2 with isolated diagnostics and no input
or body reads. The authored fixture returns exit0; repeating it yields `no-op`.
The input document is authored in the fixture, not a downloaded country payload.

Tests cover exact provenance/lexical roundtrip, source/release/country/type
mismatch, missing fields/bytes, held-before-read behavior, hostile JSON,
wrong hashes/coordinates/values, explicit unknowns, date order and the 30-day
boundary, distinct acquisition/validation age, stable keys, actual file no-op,
isolated mixed outcomes and sockets forbidden. No historical source qualification
or prior reviewed country suite is replayed.

## Remaining dependencies

AX response5037 supplies metadata custody but NOT_HELD table selectors/units/
denominator/derivation grant. BA response5052 supplies receipt custody but
NOT_HELD recipe coordinates, jurisdiction allocation and extraction permission.
The claimed 45 recipes span BA/HR/ME programme areas; no 45-BA-record assumption.
AW menu/brochure and AZ tourism context remain reuse-unqualified. The four other
required data types do not appear merely because these documents are retained.

Morgan owns the source-specific next decision. Source custodians/rights holders
must supply actual permitted field/selector contracts before a future payload
binding. Shared planner work, real retained-byte refresh, full country diagnostics,
review, develop integration and golden promotion remain separate. Raw data stays
on Foo; DEV7645, production/CIX, credentials, Actions/control and native-crash holds
are unchanged. Integration00 receives this exact local commit through Gateway;
no remote push, self-approval or merge is part of this package.

A narrow official-documentation check on 18 October 2026 did not establish new
permission: opening `https://www.regeringen.ax/` returned HTTP403 (no retry or
alternate access), and the official CUHaCHA project-meeting page open timed out
once. The exact attempts are retained in configuration. Search snippets and
unrelated hosted copyright notices are not grants for either selected source.

## Installed catalogue transport correction

Default policy loading uses the owned inert Python literal in
`offmenu.refresh._portfolio08_catalogue`, returned through `deepcopy`. The full
catalogue remains value-for-value equivalent to the unchanged reviewed JSON
mirror `config/portfolio08-source-bindings.json`; its exact byte hash is pinned
in the module. Tests enforce mirror equivalence and detached nested returns.
The module is ordinary package code, so default loading requires neither the
checkout's config directory nor reads of retained source metadata or bodies.
All ten real sources remain held, and the default CLI still returns exit2.

This correction qualifies only catalogue availability in isolated wheel and
source archive extractions built offline with the existing backend. It does not
qualify shared packaging, source use, country acceptance or integration. The
explicit authored `--fixture` command above remains a checkout-only example;
this change does not package its test fixture or broaden that support claim.
