# R4: preserve the host fetch receiver at the production default seam

Minimal correction: replace only

    fetchImpl=globalThis.fetch

with

    fetchImpl=(...args)=>globalThis.fetch(...args)

in createSourceBarcodeHandler's default input. This keeps host fetch attached to its original receiver. Caller-supplied injected fetches are unchanged. All existing method,redirect:error,credentials:omit,cache:no-store,Accept-Encoding:identity,AbortSignal,origin/path/hash/length checks,resource caps,strict parsing,stream validation,response flags and deadline behavior are byte-identical apart from this one default expression. No data gate,scope,source subset,fallback or account/runtime configuration change is included.

## Evidence and exact qualification limits

Native204 diagnostic supplied by sole integrator: manifest-fetch/runtime-operation-failed/TypeError,HTTP503 in5.682seconds; rolled back immediately to safe202. No bytes had been read. Existing compatibility_date2026-10-12,flags[nodejs_compat]. Native203/204 are inactive, and this task did not query the live202 additive route or mutate any live version.

Cloudflare's primary error documentation explains that a standalone method extraction loses its receiver and can cause Illegal invocation/TypeError; calling the method on its owner or explicitly rebinding preserves it:
https://developers.cloudflare.com/workers/observability/errors/#illegal-invocation-errors
The actual factory extracted globalThis.fetch, while all earlier local parity tests injected a receiver-insensitive Node/mock fetch. This default seam therefore had no receiver-sensitive coverage.

Focused receiver-sensitive reproduction exercises the real factory default without injecting fetchImpl: install a synthetic host fetch that throws TypeError if this!==globalThis; otherwise serve a small fully pinned synthetic manifest/empty shard. Unchanged source returns503 and fails the expected200 check (failing-before.log,exit1). One-line corrected source returns200 with a complete exact lookup; its two host calls use the correct receiver and preserve ALL fetch options (passing-after.log,exit0). Second regression uses fake time to prove the default still passes the original signal,aborts a noncooperative fetch at10seconds and makes no duplicate fallback.2/2 focused tests pass. No real index/source/provider request,production probe,producer proof/build or unrelated suite rerun occurred in this correction.

This verifies an actual host-receiver defect and a minimal supported correction. It matches the native failing stage/type, but the native error message was deliberately sanitized, so final causal confirmation is the sole integrator's one controlled actual Worker check. Do not claim live repair or hydrated facts from the synthetic check alone.

Do NOT remove cache:no-store: official compatibility documentation enables it by default from2024-11-11, earlier than the existing2026-10-12 date. The only explicit flag is nodejs_compat; cache_option_disabled was not reported. This source change neither changes compatibility date/flags nor adds configuration/services:
https://developers.cloudflare.com/workers/configuration/compatibility-flags/#enable-cache-no-store-http-standard-api
No signal option was removed. Request cancellation plus the original absolute budget remain tested.

## Sole integrator pickup

Use build/source-barcode-handler.bundle.mjs (four-source ESM component,esbuild0.25.12,no external imports). R4 includes the previously supplied optional sanitized diagnostic observer unchanged, allowing the existing controlled native check. Wire its existing fixed trusted manifest selection and exact route after environment fallback as before; preserve all other current modules/settings/bindings/scanner/auth behavior. The current live202 is not endpoint evidence; do not issue uncontrolled additive requests against it.

If integrating source against diagnostic candidate R3, apply R3-to-R4.patch (exact one-line change). If retaining the original R2 source without diagnostics, R2-binding-only.patch is the same one-line correction against that base; this optional alternative does not describe the full R4 diagnostic bundle. Hash both the source/base and final bundle,do not mix pins. No whole Worker source is replaced by these excerpts. Sole integrator owns review,one actual runtime check,publication/readback and rollback. Preserve its original snapshots and the safe202 rollback.

Request remains the same pinned milk query already supplied. Observe only sanitized stage/code/error type if it fails; if it succeeds,report envelope/count/hash/served module pins,not full source references/graph bodies. No further index validation or shard fetch is required by the source author. All R1/R2/R3 artifacts remain unchanged. R4 does not include or export the previously retained real manifest/shard.

## Source custody

CANDIDATE-RECEIPT.json and MANIFEST.json pin source,tests,bundle,one-line patches and the failing/passing logs. Build used the existing local0.25.12 esbuild via build-handler.mjs; no package install or full-app build. Unchanged stream parser,strict JSON and protocol pins match R2 byte-for-byte. No credentials,raw datasets,private bindings or real index payloads appear in this packet.
