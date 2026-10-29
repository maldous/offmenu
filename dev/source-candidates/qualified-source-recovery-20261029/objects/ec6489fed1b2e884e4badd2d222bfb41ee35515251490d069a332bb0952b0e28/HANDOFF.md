# Additive original product facts API — source review handoff

Implemented the sole integrator's exact finite contract atop byte-exact R5. No production write, scanner/browser change, account setting, cache redesign, source rebuild or new service occurred. Speed is not an acceptance gate. Existing candidate-only requests remain unchanged; explicit include=facts adds original public facts.

## Integration — replace one endpoint module only

The new self-contained ESM build/source-barcode-handler.bundle.mjs exports the SAME createSourceBarcodeHandler({selection,fetchImpl,onDiagnostic}) factory used by ./source-barcode-handler-205.mjs. The sole integrator changes only that endpoint module from exact preimage f8b9cfc68091d2505d7c689fe0e35ce97d090f1a0c5ba52a484fa74891863cbd. Preserve its fixed current206selection,one factory call,dispatcher guard/route and every other212modules/auth/scanner/settings/bindings. No Worker/full application source replacement or extra live writer is introduced. Retain that exact preimage and current version rollback. The source factory delegates candidate-only requests directly to unchanged R5, without recursion.

Source entry is source/source-barcode-facts-handler.mjs. All four R5 source modules are retained unchanged (original handler SHA56723cd22ecb72713b5dd4cc98b1a24adbb262200d25796e2d74f4a069d9d9eb). The new wrapper,server transport and three exact reviewed hydration dependencies are additive. R5-ADDITIVE-SOURCE.patch exposes those additions for review. Native source review/deployed curl acceptance remain with the reserved reviewer and sole integrator.

## Explicit API contract

GET /api/corpus/source-barcode?source=off&release=2026-10-12&namespace=barcode&value=4088700055496&include=facts

The original source/release/namespace/value/limit/cursor semantics remain. Nonempty original lexical values,including non-food identifiers/leading zeros/Unicode/whitespace,are not normalized. Missing include follows exactly R5's candidate-only path. Unknown or repeated include is invalid400 through the original request validator.

For valid include=facts, schemaVersion is offmenu-source-barcode-facts/1. candidateLookup is the original candidate envelope, including exact scoped query,pins,counts,ambiguity,truncation and references. originalFacts is null unless verified. factsStatus/HTTP outcomes:

* verified-original-public-packet /200: exactly one eligible source candidate and its full bound original packet verified; originalFacts is the unchanged existing projectOriginalPacket projection.
* selection-required /200: candidateTotal>1; no candidate is hydrated or arbitrarily selected,even if limit makes the current page contain one ref.
* source-key-not-found /200: successful complete scoped index miss; no hydration. It is not global absence.
* index-unavailable /503: original index technical failure; exact unavailable candidateLookup retained. Original400/405request errors preserve their HTTP status.
* facts-unavailable /503: candidate lookup succeeded but packet hydration/integrity/resource availability failed; successful candidateLookup is retained,originalFacts:null. Never converted into absence.

All three canonical-identity/planning/nutrition-aggregation flags stay false at response and verified projection levels. originalFacts preserves name,names,resourceType,identityStatus,identifierStatus,facts,citations and unresolvedRelations from the reviewed projector. Each source fact contains original label,formatted source value,assertion ID/status,source path and citation IDs. This is a display-string projection,NOT a normalized/structured nutrition model. No full schema qualification,complete nutrition/ingredient coverage,zero filling or cross-packet resolution is claimed. Unknown and unresolved references remain explicit; no labels alone are treated as populated nutrient facts.

## Reuse and integrity

The existing reviewed projectOriginalPacket is used unchanged from source/reviewed-hydration/source-barcode-hydrator.mjs SHAa2d96a9736942982408f51233384e503df7b7795ea24533a3f9d5f94c76300d9. The reviewed parseSourceBarcodeJSON and validateSourceBarcodeReference come from exact source-barcode-client.mjs SHA273afcb617a208c9e7385026351bc3f748e133b17a2eb37f5454b230b5351197. Its required selection module remains exact SHAadaddd1ea29bc47860e4ed557b477240bab677b5eb431dc255a5c5887159f71e. No new value formatter/fact inference was authored.

The full author archive was Library-authoritatively resolved to libfile_a8a4eb3e47a481918020b9657474a1d7,file_000000004ef881f5a15bf1154cbd8f4e,41814bytes,SHA c3300cb207ac08b029f32b858bd5a5e14180131f0ff1faf451b0d997c11d7ead; all19payload manifest entries matched. The other mistakenly supplied file ID was never used.

The browser hydrator's full-asset decoded-string/split implementation is NOT executed by the Worker entry. The new bounded Worker transport reuses its exact projector/parser/reference verification after retaining only the selected JSONL packet. It verifies the whole compressed asset's declared bytes/SHA,then full gzip stream EOF/UTF8/newline/packet-count boundary and exact ordinal before parsing that one packet. The reused projector verifies original resource,identifier assertion ID/canonical digest,subject,original lexical/namespace,public resource/assertion/citation scopes,source/release,licence/attribution and original text hashes. It returns related references unresolved. The index's selected public base/source pins remain authoritative via unchanged R5; no invented original packet digest is added.

Worker fetch keeps the R5 globalThis.fetch receiver wrapper and uses supported redirect:manual plus reject non200/exact URL,credentials:omit,cache:no-store,explicit safe Accept/Accept-Encoding:identity and no incoming Cookie/Authorization/private-header copying. No origin/path/redirect/hash check is relaxed. Unsupported browser redirect:error calls are absent from the compiled Worker bundle (build assertion).

## Bounds and lifecycle

Only exactly one eligible candidate can hydrate,with per-request lifetime/state and no shared I/O/cache. One asset:<=8MiB compressed,<=32MiB decoded,<=10000packets,selected packet<=2MiB,reviewed projection<=30000rows/depth30/display budget65536characters,facts response<=2MiB. Decoded gzip is streamed through64KiB UTF8 windows; nonselected packets are discarded without graphs,whole-file text or a split-lines array. The selected packet alone is retained and parsed. Compressed network chunks/joined hash buffer remain bounded. The original reviewed projector's own typed-value and citation checks apply unchanged.

Hydration has a120second absolute async budget after the unchanged R5 lookup,and preserves caller cancellation. This is an honest finite resource bound,not a speed acceptance criterion. Noncooperative fetch/read is raced with abort; no duplicate fallback. Synchronous work remains structurally bounded rather than timer-preempted; native runtime memory/CPU acceptance is still part of the sole integrator's existing publication check. No settings/paid quota/compatibility limit changes are requested. Any integrity/resource failure returns facts-unavailable with candidate evidence retained.

## Verification and actual available milk fields

11focused deterministic tests pass: known facts/unknown/zero fidelity,byte-exact default candidate envelope,invalid include,scoped miss,ambiguity,technical index failure,asset hash/encoding/redirect/count/ordinal failure,public citation/licence/source/text/assertion validation,tiny streaming boundaries/cancellation,finite deadline and selected-packet bound. Standard-library mocks only; no source-data fixture is exported in tests. No old19-test index suite or producer proof/build was rerun.

One bounded ACTUAL facts API parity executed against the compiled bundle. The existing retained verified milk manifest/shard bytes were reused only for this new include=facts exercise,not re-fetched or submitted as a candidate-only deliverable. One exact original public asset was fetched once:part-03002.jsonl.gz,1148789bytes,SHA5a242e24b4d21ce485210b9069070adc9973664092649b45ec64e6fd10d4f8a3,packetOrdinal119 of1000. No other shard/graph/private database/data tree was read. Local HTTP200 verified-original-public-packet returned Champ iced coffee,9original fields,1source-bound licensed citation,3unknown markers,0zero markers,1unresolved related resource. Response5975bytes,SHA9ef78e296b81965ba362bb519a59afd5e800781a39d0596dbc78b1cf38509cf9. This is local bundled-handler parity,not deployed acceptance; timing is recorded only as observed local execution,not a production gain.

Exact returned field labels now observed: name,names,brand,pack,identifiers,nutritionId,ingredientConcepts,ingredientMappingStatus,qualificationStatus. In particular nutritionId is not hydrated nutrient observations; ingredientConcepts field presence is not complete ingredient evidence. ACTUAL-MILK-FACTS-RECEIPT.json retains each returned field's formatted-value SHA,status/source path/citation count and aggregate boundary checks. Full actual API response is retained privately at input/actual-api-facts-response.json,excluded from this source-only packet along with actual index/asset bodies. No raw datasets or credentials are exported. Sole integrator/reviewer will perform actual deployed curl acceptance and inspect the original facts returned by that live API.

## Build and custody

One endpoint-only component build with existing esbuild0.25.12,8source inputs,zero external imports and no compiled redirect:error. No installs,scanner/application build or browser work. build-facts.mjs documents the exact current tool path/recipe; another approved executor must select its existing pinned esbuild path. Source inventories,contract,unchanged-source receipts,focused log and bounded actual parity receipt are frozen for independent review. Deployment remains exclusively the native integrator's action.
