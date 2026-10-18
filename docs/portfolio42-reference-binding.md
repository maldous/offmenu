# Worker42 retained IN reference binding proposal

Base: `abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. This package contains portfolio configuration, an offline metadata adapter and authored fixture tests. No shared core changes, downloaded data, source admission or country completion.

`config/portfolio42/in-reference-binding.json` pins the existing 2319-byte IN wrapper, its rights manifest and prior scoped review. The upstream compressed directory pin and line47/index0 are provenance only: this task does not open that body or any linked national document. The previous review concerns the retained reference, not this new code. Linked national documents require their copyright holders' permission. IFCT original-source and dataset-use evidence remain missing.

## API and deterministic diagnostics

`offmenu.refresh.portfolio42.prepare(payload, now=..., validated_at=None, previous_build_key=None)` accepts at most64KiB of wrapper bytes supplied by a separately authorized caller. Production defaults are code-owned retained pins. The injectable Binding seam is trusted application configuration for authored tests, never source JSON or a user-supplied grant. The function performs no file, network, clock, AI or acceptance operations. It returns candidate-ready, missing, held, malformed or stale with explicit diagnostic codes. A caller must verify the independently reviewed rights/scope assets with shared qualification before any later execution/admission; merely listing their hashes in a manifest is not verification.

For description only: `python -B -m offmenu.refresh.portfolio42 --describe`. Offline stdin diagnostics require `--now` with an explicit timezone. The CLI reads no named file and offers no URL, force-download, permission or plugin option. Exit0 means candidate-ready only; exit2 reports other outcomes. Empty stdin means missing. It is not registered in the global production execution path; dietary-guidelines remains unsupported there. This proposal does not authorize running retained real inputs.

Seven scalar reference fields receive shared per-datum provenance coverage with selectors `/record/data/<field>`, exact input hash, source/release/record identity. Existing origins are held for review rather than overwritten. Records preserve their original fields. Native units and quantity basis are null because directory strings have no dimensional values; no nutrients, currency, portions, dietary targets or national-document permissions are inferred.

Original acquisition time remains 2026-10-13T07:13:20.585551+00:00. Validation observation time and age are separate; a recent validation never resets acquisition age. Below30days matching input pins can yield reuse intent; at30days the result is stale/conditional-review-required-no-download. Hash drift is stale regardless of age. A deterministic build key covers input pins, mapping policy/scope and canonical candidate bytes. Matching prior key reports verified-no-op; it does not verify a previously published artifact or authorize an executor. There is no generic pure shared cache planner at this base: the local decision is limited to this offline binding, using shared MIN_TTL/timestamp helpers. No operational CachedAcquirer or Wikibooks-specific cache identity is invoked.

## Portfolio applicability and dependencies

IN: one own CC0 directory-reference metadata record only. Independent code/scope review and integrator00/Morgan selection are required before shared activation. Actual staging execution and gold admission remain absent.

IM: two retained historical menu facts remain partial; source40 owns existing custody evidence. Currency/portion and source-use gaps hold further mapping/admission. IO: no applicable permitted territory source; acquisition remains with existing country owner42 under Morgan scheduling. No Mauritius substitution. IQ: PDF structural integrity does not establish data semantics; actual original custodian and derivative-use grant are unestablished (source43 label is not custody). No extraction/mapping permitted without that evidence. Each held country returns without parsing even an opaque supplied buffer. All other country types remain outside this binding. No country is complete.

## Validation and review

`python3 -B -m unittest tests.test_portfolio42_binding tests.test_refresh_field_provenance tests.test_reference_acceptance` tests authored data only. The binding suite exercises five outcomes, exact selector/pin/shape/rights failures, held-input parse suppression, timezone and age boundary, replay/no-op, byte bounds, provenance mutation resistance and CLI behavior. Synthetic shared SourceContract/qualify tests verify candidate identity/schema/provenance/assets with fixture=True, reject held and tampered candidates, and grant no real source rights. Socket creation is prohibited during the pure fixture call. Running from an unrelated temporary directory with isolated Python import confirms the tested package selection.

The additional existing test_reference_common module requires jsonschema_rs, unavailable in this runtime; it is a recorded environment limitation, not a passing check. No dependency installation is part of this package.

Independent review must use the immutable committed diff, test evidence and source-pin receipt; the author does not accept its own change. Morgan owns scheduling/ledger reconciliation, integrator00 owns selected integration. Preserve source/private/Finland/Frida/nativeNO-FR/403 and denied-action holds, mandatory auto_review, production and CIX pauses. No source engine, admissions registry, security setting, service or deployment changed.
