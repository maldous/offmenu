# R5: current Workers-compatible redirect refusal

Concrete current platform incompatibility: this adapter passed redirect:'error'. Cloudflare Workers supports only follow/manual and throws TypeError while constructing a Request, including fetch(url,init), before sending it. This exactly fits the observed manifest-fetch TypeError stage, independently of shard parsing. Native confirmation remains with the sole integrator; no live repair is claimed from mock tests.

Primary current documentation:
https://developers.cloudflare.com/workers/runtime-apis/request/#constructor
The redirect option documents only follow/manual and explicitly rejects error.
Primary current workerd implementation:
https://github.com/cloudflare/workerd/blob/main/src/workerd/api/http.c++
Request::constructor around450-454 rejects values absent from Request::tryParseRedirect; tryParseRedirect around575-582 accepts only follow/manual. No compatibility-date/flag conditional surrounds this restriction. Request::Redirect in http.h contains only FOLLOW/MANUAL. This is stronger/current evidence than the old credentials issue.

## Minimal correction and unchanged security

One line relative to frozen R4 changes ONLY redirect:'error' to redirect:'manual' in fetchBytes. The existing status===200 and !redirected/exact-response-URL checks already reject all redirects before body acceptance. A3xx response is never followed; body is canceled and returned as shaped503 index-unavailable. No partial absence or trusted-origin exception was added.

Everything else remains byte-identical: fixed manifest/shard origins/paths,explicit Accept and Accept-Encoding:identity headers,credentials:'omit',cache:'no-store',AbortSignal,absolute10s budget,compressed/decoded/parser/ref/response bounds,SHA checks,stream/full-entry validation,cursor binding,source dates and null/false evidence semantics. No incoming Request is forwarded as the fetch argument; only a literal fixed public URL string and freshly constructed headers/options are used. Cookie,Authorization,private headers,request.cf/body and URL userinfo are never copied. Workers has no browser cookie handling; it treats Cookie as an explicit header, as documented in its Request properties. The redirect is manual and rejected so no credentials could be forwarded to a target. No account credentials or stores are read.

Existing actual metadata supplied by integrator remains compatibility_date2026-10-12 and compatibility_flags[nodejs_compat]. No date/flag/account change is needed. cache:no-store is supported from2024-11-11 and is preserved. Current workerd http.h RequestInitializerDict around604-611 treats browser-only credentials as ignored; current JSG_STRUCT around650-651 does not implement that field as an error-producing option. The2023 workers-sdk2514 issue therefore is not sufficient current evidence to blame/remove credentials. This packet does not claim that credentials caused native205. Current source:
https://github.com/cloudflare/workerd/blob/main/src/workerd/api/http.h
Relevant current security/platform docs:
https://developers.cloudflare.com/workers/runtime-apis/request/#properties
https://developers.cloudflare.com/workers/configuration/compatibility-flags/#enable-cache-no-store-http-standard-api

## Evidence and honest status

Frozen R4 was published/read back by the native owner but still returned503 in2.692s. Its receiver-sensitive regression proved only a host-binding defect, NOT a successful native repair. R4 and all earlier artifacts remain unchanged. R5 preserves its safe globalThis.fetch wrapper and optional fixed-field diagnostic callback.

Focused current-workerd-contract test installs a synthetic receiver-sensitive host fetch which accepts only the two current documented redirect modes. It uses a tiny fully pinned synthetic manifest/shard,not a real index. Unchanged R4 fails expected200 with503 (failing-before.log,exit1); changing the single mode makes it pass. Three after-tests pass (passing-after.log,exit0): correct host/default invocation and complete lookup with no copied synthetic inbound Cookie/Authorization/private headers; manual302 rejection without following target or returning Set-Cookie; and unchanged signal/absolute deadline with no duplicate fallback. No real data/index/proof checks or unrelated suite reruns occurred. No network/provider/production operation ran in this correction.

## Sole integrator pickup and rollback

Review R4-to-R5.patch,whose inverse restores exactly frozen R4 source077703d8135b826e78a81747d9723967a90f4e9811ec54650b5cead76e89be26. Use build/source-barcode-handler.bundle.mjs (four-source ESM component,existing esbuild0.25.12,no external imports). Keep all other modules,assets,auth,scanner,bindings,settings and the existing fixed published selection unchanged. Only the sole integrator may perform its controlled actual Worker check/publication/readback/rollback. Optional sanitized diagnostics remain available if the next native check exposes a different error. Do not claim final endpoint availability until that check succeeds. Preserve safe202 rollback and inactive diagnostic versions.

No actual manifest/shard/graph payloads,private bindings,credentials or raw datasets are included in this source-only packet. Source/parser/pins other than the one redirect expression match R4 exactly. Reproduction: node --test tests/worker-fetch-contract.test.mjs; component build: node build-handler.mjs using the existing pinned toolchain. No package installs/new service or full application build.
