# Worker23 retained portfolio metadata bindings

Selected request: `M-STAGING-BIND-20261018-W23`. Baseline is the selected accepted
snapshot `abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. New source is confined to
`offmenu/refresh/portfolios/worker23*`, its package initializer, this document and
`tests/test_worker23_staging_bindings.py`. No shared-core changes or admissions.

This package stages **metadata**, not publisher observations. It reuses shared
`core.strict_json`, `core.timestamp`, `acceptance.fingerprint`, and
`field_provenance.field_origin_errors`; it contains no copied country parser.
`worker23.json` is trusted portfolio configuration pending independent review,
never a runtime rights grant. It declares five exact source/release bindings and
the four retained qualification/validation metadata assets, including sizes and
SHA-256 pins. Acquisition-receipt metadata has separate pins and selectors.
The CLI opens only these installed metadata paths. Embedded body paths, URLs,
neighbours and archives are never opened. No network client is implemented.

## Binding and provenance scope

| Country | Binding | Metadata that can be staged | Payload prerequisites retained |
| --- | --- | --- | --- |
| CI | ANADER farmgate 2021–2023 | 36 panel / 108 observation lineage counts, 101 numeric and 7 null | FCFA issuer/denomination, source-to-kg acceptance, annual method, exact date semantics, food eligibility; source licence/attribution scope preserved |
| CK | Tourism quality standard | Printed update/effective dates, non-membership classification | This is not an operator register; reuse/identifier/version/membership evidence remains distinct |
| CK | One merchant menu | Unknown currency/date/operator identity, single-merchant classification | Structured derivative use, explicit currency, menu version/date and operator identity |
| CL | INE May2024 V2 CPI manual | 613 reviewed hierarchy-count metadata, base2023=100, weight-reference interval | Exact release/derivative terms binding; no price/weight rows or household quantities; current month unknown |
| CM | Pelé/Le Berre historical publication | 1966-12/1967 conflict, digitization2001, unknown item basis | Applicable derivative rights; item/table/observation amount/unit, preparation, edible fraction, wet/dry and method/status |

The binding IDs are internal portfolio namespaces, not new publisher identifiers.
Every scalar under `packet.data`, including zero and null, has an exact RFC6901
selector into the pinned **retained metadata JSON**. Origin checks verify coverage,
identity and pins; projection code resolves those actual selectors. They do not
pretend to verify an underlying PDF cell. `nativeSemantics` is an authored policy
declaration in the configuration, bound by the content key; it is separate from
source-derived `data`. The original body hashes and custody labels are metadata
claims only in this run. Body integrity, source fidelity and canonical semantic
acceptance are not established here. No source ownership is transferred.

`packet.provenance.fetchedAt` preserves the original acquisition event evidenced
by the independently pinned receipt/qualification, not this validation's time.
CI's available timestamp is the original request event, with completion precision
unknown; this qualification is explicit in `acquisitionEvidence.meaning`.
An absent acquisition timestamp stays null. Original acquisition age and metadata
validation age are separate. Source mtime and publisher publication year are not
used as acquisition age. Body-cache verification remains false.

## Deterministic interface and diagnostics

```sh
python3 -m offmenu.refresh.portfolios.worker23 --now 2026-10-18T05:00:00Z
python3 -m offmenu.refresh.portfolios.worker23 --now 2026-10-18T05:00:00Z --operation payload-stage
```

Stdout is a deterministic JSON report; no files or pointers are written. The first
command stages five metadata packets if exact retained metadata is available.
The second is a **planning diagnostic only** and returns held; it cannot invoke a
payload handler. Exit0 means every selected metadata binding is valid; exit2
retains isolated source failures. Neither exit establishes dataset acceptance.

`assess(spec, raw, now=..., acquisition_raw=..., previous_key=...)` is the bounded
in-memory API used by authored tests; the installed `run` supplies only the fixed
allowlisted metadata bytes. The 256KiB per-metadata-file limit applies before
JSON parsing. Duplicate keys, nonfinite values, malformed JSON, bad source/pins,
missing/non-scalar selectors and invalid timestamps fail closed with fixed codes.
Symlink paths and nonregular inputs are refused. One failed source does not erase
successful peer metadata results. No input/body/error text is put in diagnostics.

Reader correction for `W21-W23-READER-01`: metadata and acquisition evidence now
use the same descriptor-relative traversal with `O_NOFOLLOW`, a nonblocking final
open, regular-file `fstat`, and a bounded descriptor read. File identities and
ancestor names are checked around that read; pathnames are never reopened for
payload reading after verification. All descriptors close on success or failure.
Seven focused authored regressions cover leaf/ancestor symlink swaps, a FIFO
successor under a child deadline, bounded growth, same-pin name replacement,
acquisition-evidence isolation, valid peers and descriptor cleanup. This correction
does not change selectors, source declarations, clock policy or payload holds.

Status is `valid`, `missing`, `malformed`, `held` or `stale-input`. Payload holds
take precedence over cache age. Metadata may remain valid while payload use is
held or its cache evidence is missing/stale; both states are returned separately.
Under30day acquisition age requests retained reuse with zero downloads; at the
exact30day boundary the result requests conditional review with zero downloads.
Revalidation never resets acquisition age. Freshness never proves rights or body
integrity and never installs a payload adapter.

The `contentKey` binds projection, exact portfolio contract and runtime helper
code hashes. The explicit evaluation clock and validation timestamp are excluded
from rebuild identity. Pass `--previous-key BINDING_ID=SHA256` (repeatable) or
`previous_keys` to compare exact prior outputs. Identical inputs return `no-op`
and `emitPacket=false`; the diagnostic report still includes the verified packet.
An integration caller must respect `emitPacket` before publishing new stage files.
No previous-key argument can grant rights or bypass validation.

## Current official documentation check, 18 October 2026

[INE terms, section III](https://www.ine.gob.cl/terminos-de-uso-y-licencia-de-datos-abiertos)
state that site content uses CC BY-SA4.0 and permits adaptation, subject to credit,
a licence link, change notices and sharealike. This is positive primary publisher
evidence; the historical metadata's unsuccessful PDF notice search does not prove
absence of rights. The next selected derivative task can bind these conditions to
the exact May2024 V2 manual and its output plan. This turn does not accept terms,
process that body or remove the explicit metadata/code assignment restriction.

An official IRD open-access guidance search yielded general policy rather than
an applicable1966-release licence; the guidance page open returned404 and was
not retried. Cook Islands official searches yielded programme/media terms, not a
specific grant for the retained standard or merchant menu. These are missing
applicable evidence, not claims of legal prohibition or absence of permission.
No alternate actor, denied-source retry, body download or terms workaround occurs.

## Integration handoff and remaining typed dependencies

No shared-interface edit is required for this metadata package. Proposed future
integrator-owned hook: a source-agnostic equivalent of `core.cache_policy` taking
explicit source/release, immutable input identity, original acquisition evidence
and validation history. The existing helper is Wikibooks-specific; it must not be
mislabelled as a generic portfolio policy. This package's metadata-only age plan
does not replace an acquisition/cache engine. Future payload bindings should use
existing `SourceContract`, reviewed `GLOBAL Binding` and per-source resource
boundaries; production admissions are not generated from this JSON configuration.

Morgan selects the designated independent reviewer and any new substantive task.
Integrator00 verifies the fresh accepted integration baseline and composes reviewed
changes. Local `develop` and `origin/develop` observed at pickup differed from the
selected snapshot; both and the prior branch were preserved. This commit does not
claim to be integrated or based on whichever branch name happens to be latest.
PR42 remains separate pending work with its reported P2 merge hold.

Operation restrictions: all source-use, actual denial/403, private/credential,
Finland/Frida/nativeNO-FR crash, production/CIX and separate DEV7645 holds persist.
Missing inputs: CI semantic targets; CK register/menu evidence; CM per-item basis.
Technical dependency: no reviewed generic payload bindings for these exact retained
formats. These dependencies do not block the delivered metadata interface or imply
whole-country completion. Gold, source acceptance and whole-country counts remain0.

Authored tests cover all five requested outcome classes, exact30day/under30day
reuse, metadata-age independence, replay, acquisition metadata pins/timestamps,
zero/null origins, malformed inputs, isolated failures and CK role separation.
They require no private filesystem or publisher data. Real invocation evidence
is retained outside Git in the existing Worker23 task receipt directory.
