var _OffMenuSourceBarcode=(()=>{var q=Object.defineProperty;var ce=Object.getOwnPropertyDescriptor;var de=Object.getOwnPropertyNames;var le=Object.prototype.hasOwnProperty;var ue=(e,n)=>{for(var t in n)q(e,t,{get:n[t],enumerable:!0})},fe=(e,n,t,a)=>{if(n&&typeof n=="object"||typeof n=="function")for(let i of de(n))!le.call(e,i)&&i!==t&&q(e,i,{get:()=>n[i],enumerable:!(a=ce(n,i))||a.enumerable});return e};var pe=e=>fe(q({},"__esModule",{value:!0}),e);var Re={};ue(Re,{HYDRATION_LIMITS:()=>A,SOURCE_BARCODE_INDEX_RELEASE:()=>$,SOURCE_BARCODE_PINS:()=>P,SOURCE_BARCODE_PUBLIC_BASE:()=>w,SOURCE_BARCODE_SCHEMA:()=>F,automaticSourceSelection:()=>Ce,createSourceBarcodeHydrator:()=>K,createSourceBarcodeInventory:()=>Se,createSourceBarcodeLookup:()=>V,hydratedSourceBarcodeReadout:()=>Q,inventoryReadout:()=>me,parseSourceBarcodeJSON:()=>D,projectOriginalPacket:()=>oe,sourceBarcodeMatch:()=>ae,sourceBarcodeReadout:()=>z,validateSourceBarcodeEnvelope:()=>ne,validateSourceBarcodeReference:()=>X,validateSourceBarcodeSelection:()=>L});var F="offmenu-source-barcode-candidates/1",$="source-barcode-index-v1-20261029",P=Object.freeze({sourceManifestSha256:"8cd8abbf28f8fac11ccb73f336a91c7a5d90fbaff6ec1c864ec7b492f13da58e",structuralManifestSha256:"83773291ac70931a110f60e872ae47a2bd470b5f397c709195dcf016c0bf0694",consumerIndexSha256:"5e6d5c14a26515632a56aac2ff128a12baaa6ec7d030703c368cc8c297a4c1ad",locatorManifestSha256:"3520dff24e7b96635fd3d8f8cfa60664d03d5bd65709b547059cee10b306e1a9",locatorIndexSha256:"1691828696477efe932d6b3bfc1e20cbdc99ddf047da3e695067f40478e8c2cd",publicBaseManifestSha256:"66b2ee6e016838453c59c1d1f6f05941d14c84a8084361ef099463a3a6471c05",qualificationReceiptSha256:"9e60de075a9bf049e0348c666e4cc2cbe9edb07c6771bcab95649038dafd1226",schemaSha256:"89ff701460e0c9c6e27c5d5ece7bd6868f26f55fc2aedd1d85c87b4408cf1f6c",contractSha256:"b4fa5afb2f8cc77326299b55ccd75b93f121e807317fdc1f9953709e98faa0aa"}),M="/common-data/releases/common-corpus-expanded-20261014/",w=Object.freeze({origin:"https://offmenu-corpus.netlify.app",releaseId:"common-corpus-expanded-20261014",manifestPath:M+"manifest.json",manifestSha256:P.publicBaseManifestSha256,sourcePackageManifestPath:M+"bulk-food/source-package-manifest.json",sourcePackageManifestSha256:P.sourceManifestSha256,assetPrefix:M+"bulk-food/"}),Z=["schemaVersion","query","status","candidateTotal","countKnown","complete","returnedCount","truncated","candidates","nextCursor","referenceCoverageComplete","canonicalIdentityAsserted","automaticPlanningEligible","nutritionAggregationEligible"],he=[...Z,"manifestSha256","indexReleaseId","sourcePins","publicBase"],ee=e=>e!==null&&typeof e=="object"&&!Array.isArray(e),_=(e,n)=>ee(e)&&Object.keys(e).length===n.length&&n.every(t=>Object.hasOwn(e,t)),O=e=>typeof e=="string"&&e.length>0,N=e=>Number.isSafeInteger(e)&&e>=0,H=e=>typeof e=="string"&&/^[a-f0-9]{64}$/.test(e),T=e=>Array.isArray(e)?"["+e.map(T).join(",")+"]":ee(e)?"{"+Object.keys(e).sort().map(n=>JSON.stringify(n)+":"+T(e[n])).join(",")+"}":JSON.stringify(e),B=(e,n)=>T(e)===T(n),h=(e,n="SOURCE_BARCODE_RESPONSE_MISMATCH")=>{if(!e)throw Error(n)},I=e=>structuredClone(e);function D(e){h(typeof e=="string"&&new TextEncoder().encode(e).length<=2*1024*1024,"SOURCE_BARCODE_RESPONSE_BOUND");let n=JSON.parse(e),t=0,a=()=>{for(;/[\x20\t\n\r]/.test(e[t]||"x");)t++};function i(){let d=t++;for(;t<e.length;){let S=e[t++];if(S==="\\")t++;else if(S==='"')return JSON.parse(e.slice(d,t))}throw Error("SOURCE_BARCODE_JSON")}function o(d=0){if(h(d<=40,"SOURCE_BARCODE_JSON_DEPTH"),a(),e[t]==="{"){t++,a();let S=new Set;if(e[t]==="}"){t++;return}for(;;){a();let l=i();if(h(!S.has(l),"SOURCE_BARCODE_DUPLICATE_JSON_KEY"),S.add(l),a(),t++,o(d+1),a(),e[t++]==="}")break}}else if(e[t]==="["){if(t++,a(),e[t]==="]"){t++;return}for(;o(d+1),a(),e[t++]!=="]";);}else if(e[t]==='"')i();else{let S=t;for(;t<e.length&&!/[\x20\t\n\r,}\]]/.test(e[t]);)t++;let l=JSON.parse(e.slice(S,t));h(typeof l!="number"||Number.isFinite(l),"SOURCE_BARCODE_NONFINITE_JSON")}}return o(),a(),h(t===e.length),n}async function ge(e){if(e.headers?.get("content-length")&&h(Number(e.headers.get("content-length"))<=2097152,"SOURCE_BARCODE_RESPONSE_BOUND"),!e.body?.getReader){let d=await e.text();return h(new TextEncoder().encode(d).length<=2097152,"SOURCE_BARCODE_RESPONSE_BOUND"),d}let t=e.body.getReader(),a=new TextDecoder("utf-8",{fatal:!0}),i=0,o="";try{for(;;){let d=await t.read();if(d.done)break;i+=d.value.byteLength,h(i<=2097152,"SOURCE_BARCODE_RESPONSE_BOUND"),o+=a.decode(d.value,{stream:!0})}return o+a.decode()}catch(d){throw await t.cancel().catch(()=>{}),d}finally{t.releaseLock()}}function W(e,n,t){let a={source:e.source,release:e.release,namespace:t,lexical:n};return h(O(a.source)&&O(a.release)&&t==="barcode"&&O(n),"SOURCE_BARCODE_QUERY_UNAVAILABLE"),h(new TextEncoder().encode(JSON.stringify([a.source,a.release,t,n])).length<=16384,"SOURCE_BARCODE_QUERY_BOUND"),a}function L(e){h(_(e,["manifestSha256","indexReleaseId","scopes"])&&H(e.manifestSha256)&&e.indexReleaseId===$&&Array.isArray(e.scopes)&&e.scopes.length>0&&e.scopes.length<=8,"SOURCE_BARCODE_NOT_CONFIGURED");for(let n of e.scopes)h(_(n,["source","release"])&&O(n.source)&&O(n.release),"SOURCE_BARCODE_NOT_CONFIGURED");return h(new Set(e.scopes.map(T)).size===e.scopes.length,"SOURCE_BARCODE_NOT_CONFIGURED"),I(e)}function J(e,n,t,a){h(O(e)&&e.length<=32768&&/^[A-Za-z0-9_-]+$/.test(e),"SOURCE_BARCODE_CURSOR_MISMATCH");let i=Uint8Array.from(atob(e.replaceAll("-","+").replaceAll("_","/")+"=".repeat((4-e.length%4)%4)),d=>d.charCodeAt(0)),o=D(new TextDecoder("utf-8",{fatal:!0}).decode(i));return h(_(o,["manifestSha256","query","limit","offset"])&&o.manifestSha256===a.manifestSha256&&B(o.query,n)&&o.limit===t&&N(o.offset)&&o.offset<=20,"SOURCE_BARCODE_CURSOR_MISMATCH"),o}function te(e,n){h(_(e,["sourceResourceId","asset","identifierAssertion","sourceAssertionStatus","sourceAssertionStatusState","citationRefs","ingredientRefs","nutrientRefs"])&&O(e.sourceResourceId));let t=e.asset;h(_(t,["path","sha256","bytes","packetOrdinal","packetCount","packetCanonicalSha256","packetDigestState"])),h(O(t.path)&&t.path.startsWith(n.assetPrefix)&&!t.path.split("/").slice(1).some(o=>!o||o==="."||o===".."));let a=new URL(t.path,n.origin);h(a.origin===n.origin&&a.pathname===t.path&&!a.search&&!a.hash),h(H(t.sha256)&&N(t.bytes)&&t.bytes>0&&N(t.packetOrdinal)&&N(t.packetCount)&&t.packetOrdinal<t.packetCount),h(t.packetCanonicalSha256===null&&t.packetDigestState==="not-retained-in-selected-product-locator-index");let i=e.identifierAssertion;return h(_(i,["id","canonicalSha256","matchingAssertionCount","referencesTruncated"])&&O(i.id)&&H(i.canonicalSha256)&&N(i.matchingAssertionCount)&&i.matchingAssertionCount>=1&&i.referencesTruncated===i.matchingAssertionCount>1),h(e.sourceAssertionStatus===null&&e.sourceAssertionStatusState==="resolve-original-public-assertion"&&e.citationRefs===null&&e.ingredientRefs===null&&e.nutrientRefs===null),I(e)}function ne(e,n,t,{limit:a=20,cursor:i=null}={}){if(h(e?.schemaVersion===F&&B(e.query,n)),h(e.canonicalIdentityAsserted===!1&&e.automaticPlanningEligible===!1&&e.nutritionAggregationEligible===!1),e.status==="index-unavailable")return h(_(e,Z)&&e.candidateTotal===null&&e.countKnown===!1&&e.complete===!1&&e.returnedCount===0&&e.truncated===null&&Array.isArray(e.candidates)&&e.candidates.length===0&&e.nextCursor===null&&e.referenceCoverageComplete===!1),I(e);h(_(e,he)&&e.manifestSha256===t.manifestSha256&&e.indexReleaseId===t.indexReleaseId&&B(e.sourcePins,P)&&B(e.publicBase,w)),h(e.countKnown===!0&&e.complete===!0&&N(e.candidateTotal)&&Array.isArray(e.candidates)&&e.candidates.length<=a&&e.returnedCount===e.candidates.length);let o=i===null?0:J(i,n,a,t).offset,d=Math.min(e.candidateTotal,20);h(o<=d&&e.returnedCount===Math.min(a,d-o)&&e.truncated===e.candidateTotal>e.returnedCount&&e.referenceCoverageComplete===(d===e.candidateTotal)),h(e.status===(e.candidateTotal===0?"source-key-not-found":e.candidateTotal>1?"ambiguous-source-key":"source-scoped-candidates"));let S=new Set;for(let l of e.candidates)te(l,e.publicBase),h(!S.has(l.sourceResourceId)),S.add(l.sourceResourceId);return o+e.returnedCount<d?(h(e.nextCursor!==null),h(J(e.nextCursor,n,a,t).offset===o+e.returnedCount)):h(e.nextCursor===null),I(e)}function U(e,n){return{schemaVersion:F,query:I(e),status:"index-unavailable",candidateTotal:null,countKnown:!1,complete:!1,returnedCount:0,truncated:null,candidates:[],nextCursor:null,referenceCoverageComplete:!1,canonicalIdentityAsserted:!1,automaticPlanningEligible:!1,nutritionAggregationEligible:!1,clientError:n}}function ae(e,n){return{kind:"source-barcode-candidate",id:T(["source-barcode-candidate",n.manifestSha256,n.query,e.sourceResourceId,e.asset.sha256,e.asset.packetOrdinal,e.identifierAssertion.canonicalSha256]),name:null,brand:null,provenance:{sourceId:n.query.source,releaseId:n.query.release},sourceBarcodeCandidate:{query:I(n.query),manifestSha256:n.manifestSha256,indexReleaseId:n.indexReleaseId,publicBase:I(n.publicBase),reference:I(e),hydrationState:"not-loaded",factsState:"details-pending",canonicalIdentityAsserted:!1,automaticPlanningEligible:!1,nutritionAggregationEligible:!1}}}function G(e,n,t,a,i){return{enabled:!0,original:e,namespace:"barcode",generation:n,symbology:t,manifestSha256:i.manifestSha256,indexReleaseId:i.indexReleaseId,lanes:a,matches:a.flatMap(o=>o.candidates.map(d=>ae(d,o))),hasMore:a.some(o=>o.nextCursor!==null),complete:a.every(o=>o.complete===!0),ambiguous:a.some(o=>o.candidateTotal>1),referenceCoverageComplete:a.every(o=>o.referenceCoverageComplete===!0)}}function V({selection:e=null,fetchImpl:n=globalThis.fetch,limit:t=20}={}){let a;try{a=L(e),h(Number.isSafeInteger(t)&&t>=1&&t<=20)}catch{a=null}let i=!1,o=new Set;async function d(c,g,s){if(i)return U(c,"SOURCE_BARCODE_CLOSED");s!==null&&J(s,c,g,a);let u=new URL("/api/corpus/source-barcode","https://offmenu.invalid");for(let[m,C]of Object.entries({source:c.source,release:c.release,namespace:c.namespace,value:c.lexical,limit:g}))u.searchParams.set(m,String(C));s!==null&&u.searchParams.set("cursor",s);let p=new AbortController;o.add(p);let E=setTimeout(()=>p.abort(),12e3);try{let m=await n(u.pathname+u.search,{method:"GET",credentials:"omit",cache:"no-store",redirect:"error",mode:"same-origin",headers:{Accept:"application/json"},signal:p.signal});if(i||p.signal.aborted)return U(c,"SOURCE_BARCODE_CLOSED");if(m.status!==200)return U(c,"SOURCE_BARCODE_TRANSPORT_UNAVAILABLE");let C=await ge(m);return i||p.signal.aborted?U(c,"SOURCE_BARCODE_CLOSED"):{...ne(D(C),c,a,{limit:g,cursor:s}),requestCursor:s,limit:g}}catch{return U(c,"SOURCE_BARCODE_RESPONSE_UNAVAILABLE")}finally{clearTimeout(E),o.delete(p)}}async function S(c,g,s=null,u="barcode"){if(!a)return{enabled:e!=null,matches:[],lanes:[],hasMore:!1,complete:!1,configurationError:e!=null,reason:"SOURCE_BARCODE_NOT_CONFIGURED"};let p;try{h(Number.isSafeInteger(g),"SOURCE_BARCODE_QUERY_UNAVAILABLE"),p=a.scopes.map(E=>W(E,c,u))}catch{return G(c,g,s,a.scopes.map(E=>U({source:E.source,release:E.release,namespace:u,lexical:c},"SOURCE_BARCODE_QUERY_UNAVAILABLE")),a)}return G(c,g,s,await Promise.all(p.map(E=>d(E,t,null))),a)}async function l(c){h(a&&c?.enabled&&c.manifestSha256===a.manifestSha256&&c.indexReleaseId===a.indexReleaseId&&c.lanes.length===a.scopes.length,"SOURCE_BARCODE_PAGE_CONTEXT_CHANGED");let g=await Promise.all(c.lanes.map(async(s,u)=>{if(h(B(s.query,W(a.scopes[u],c.original,c.namespace)),"SOURCE_BARCODE_PAGE_CONTEXT_CHANGED"),!s.nextCursor)return s;let p=await d(s.query,s.limit,s.nextCursor);if(p.status==="index-unavailable")return{...s,pageError:p.clientError||"SOURCE_BARCODE_PAGE_UNAVAILABLE"};h(p.candidateTotal===s.candidateTotal&&B(p.sourcePins,s.sourcePins)&&B(p.publicBase,s.publicBase),"SOURCE_BARCODE_PAGE_CONTEXT_CHANGED");let E=new Set(s.candidates.map(m=>m.sourceResourceId));for(let m of p.candidates)h(!E.has(m.sourceResourceId),"SOURCE_BARCODE_DUPLICATE_PAGE_RESOURCE"),E.add(m.sourceResourceId);return{...p,candidates:[...s.candidates,...p.candidates],returnedCount:s.candidates.length+p.candidates.length}}));return G(c.original,c.generation,c.symbology,g,a)}return Object.assign(S,{more:l,destroy(){i=!0;for(let c of o)c.abort();o.clear()}})}function z(e,n,t="overview"){let a=e?.sourceBarcodeCandidate;if(!a)return[];let i=n?.sourceBarcodeResult?.lanes.find(d=>B(d.query,a.query)),o=[{label:"Identifier match \xB7 details pending",text:a.query.lexical},{label:"Source scope",text:a.query.source+" \xB7 "+a.query.release+" \xB7 "+a.query.namespace},{label:"Original resource reference",text:a.reference.sourceResourceId},{label:"Facts not loaded",text:"This is a source-scoped identifier candidate. Original name, type, ingredient, nutrition, citations, status and licence require verified original-packet hydration. Unknown, not absent or zero. No product/food identity or planning admission is asserted."}];return i&&o.push({label:"Candidate coverage",text:String(i.candidateTotal)+" eligible source resource(s); "+i.candidates.length+" reference(s) loaded"+(i.referenceCoverageComplete?"":"; reference inventory is capped or incomplete")+(i.nextCursor?"; another stored page is available":"")+(i.pageError?"; additional page unavailable":"")}),t==="source"&&o.push({label:"Exact index/asset/assertion binding",text:JSON.stringify(a)},{label:"Source evidence state",text:"citationRefs, ingredientRefs and nutrientRefs are not materialized in this index. Original packet digest is not retained; verify asset bytes/SHA, ordinal, resource and assertion digest before factual display."}),o}var X=(e,n=w)=>te(e,n);var j="urn:offmenu:property:",f=e=>{if(!e)throw Error("SOURCE_DETAILS_UNAVAILABLE")},k=e=>Array.isArray(e)?"["+e.map(k).join(",")+"]":e!==null&&typeof e=="object"?"{"+Object.keys(e).sort().map(n=>JSON.stringify(n)+":"+k(e[n])).join(",")+"}":JSON.stringify(e),Ee=(e,n)=>k(e)===k(n),Y=async e=>Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",e)),n=>n.toString(16).padStart(2,"0")).join(""),A=Object.freeze({compressedBytes:8*1024*1024,expandedBytes:32*1024*1024,packetBytes:2*1024*1024,packets:1e4,rows:3e4,timeoutMs:15e3,displayCharacters:65536});async function re(e,n,t){f(e?.getReader);let a=e.getReader(),i=[],o=0,d=()=>{a.cancel().catch(()=>{})};t.addEventListener("abort",d,{once:!0});try{for(;;){f(!t.aborted);let c=await a.read();if(f(!t.aborted),c.done)break;o+=c.value.byteLength,f(o<=n),i.push(c.value)}let S=new Uint8Array(o),l=0;for(let c of i)S.set(c,l),l+=c.byteLength;return S}finally{t.removeEventListener("abort",d),await a.cancel().catch(()=>{}),a.releaseLock()}}async function oe(e,n,t=new AbortController().signal){f(e?.schemaVersion==="offmenu-common/1");let a={},i=0;for(let r of["resources","assertions","relations","citations","translations"]){f(Array.isArray(e[r])),i+=e[r].length,f(i<=A.rows),a[r]=new Map;for(let b of e[r])f(typeof b.id=="string"&&b.id&&!a[r].has(b.id)),a[r].set(b.id,b)}let o=r=>{let b=a.citations.get(r);return f(b?.scope?.visibility==="public"&&b.sourceId===n.query.source&&b.revisionId===n.query.release&&typeof b.license=="string"&&b.license.length>0&&typeof b.attribution=="string"&&b.attribution.length>0),b},d=r=>(f(Array.isArray(r)&&r.length>0),r.map(o)),S=r=>(f(r?.scope?.visibility==="public"),d(r.citationIds),f(r.status!=="superseded"),r),l=S(a.resources.get(n.reference.sourceResourceId)),c=S(a.assertions.get(n.reference.identifierAssertion.id));f(c.subjectId===l.id&&c.propertyId===j+"sourceIdentifier"&&["source-asserted","candidate","editor-authored","reviewed","verified"].includes(c.status)),f(await Y(new TextEncoder().encode(k(c)))===n.reference.identifierAssertion.canonicalSha256);let g=c.value?.fields;f(c.value?.kind==="structure"&&g?.system?.kind==="identifier"&&g.system.value===n.query.namespace&&g.value?.kind==="identifier"&&g.value.value===n.query.lexical);let s=A.displayCharacters,u=new Map;function p(r){for(let b of d(r))u.set(b.id,{id:b.id,sourceId:b.sourceId,revisionId:b.revisionId,originalRecordId:b.originalRecordId??null,license:b.license,attribution:b.attribution,originalUrl:b.originalUrl??null,rightsEvidenceUrl:b.rightsEvidenceUrl??null})}function E(r){return f(typeof r=="string"),s-=r.length,f(s>=0&&!t.aborted),r}async function m(r,b=0){switch(f(b<=30&&r&&typeof r=="object"&&!t.aborted),r.kind){case"text":return f(r.status!=="superseded"),p(r.citationIds),f(typeof r.value=="string"&&await Y(new TextEncoder().encode(r.value))===r.sourceTextSha256),E(r.value);case"null":return f(r.value===null),"Unknown";case"number":return f(typeof r.value=="number"&&Number.isFinite(r.value)),String(r.value);case"boolean":return f(typeof r.value=="boolean"),String(r.value);case"identifier":case"uri":case"expression":case"date":case"datetime":return E(r.value);case"reference":return E(r.id)+" (source reference; unresolved)";case"list":return f(Array.isArray(r.items)),(await Promise.all(r.items.map(R=>m(R,b+1)))).join(" \xB7 ");case"structure":return f(r.fields&&typeof r.fields=="object"&&!Array.isArray(r.fields)),(await Promise.all(Object.entries(r.fields).map(async([R,ie])=>E(R)+": "+await m(ie,b+1)))).join(" \xB7 ");case"quantity":{f(r.value===null||typeof r.value=="number"&&Number.isFinite(r.value));let R=(r.value===null?"Unknown":String(r.value))+" "+E(r.sourceUnit||r.unitId||"Unknown unit");return r.basis&&(R+=" per "+await m(r.basis,b+1)),r.qualifiers&&(R+="; qualifiers: "+E(JSON.stringify(r.qualifiers))),r.sourceValue!==void 0&&(R+="; original value: "+E(JSON.stringify(r.sourceValue))),r.sourceNotation&&(R+="; notation: "+await m(r.sourceNotation,b+1)),R}default:throw Error("SOURCE_DETAILS_UNAVAILABLE")}}p(l.citationIds),p(c.citationIds);let C=[];for(let r of l.names||[])C.push(await m(r));let y=[];for(let r of e.assertions.filter(b=>b.subjectId===l.id))if(S(r),p(r.citationIds),!!["sourceFields","nutrientObservation","sourceNutrientMetadata"].some(b=>r.propertyId===j+b))if(r.propertyId===j+"sourceFields"){f(r.value?.kind==="structure"&&r.value.fields);for(let[b,R]of Object.entries(r.value.fields))y.push({label:E(b),text:await m(R),assertionId:r.id,status:r.status,sourcePath:r.sourcePath??null,citationIds:[...r.citationIds]})}else y.push({label:r.sourcePath||r.propertyId.slice(j.length),text:await m(r.value),assertionId:r.id,status:r.status,sourcePath:r.sourcePath??null,citationIds:[...r.citationIds]});let x=[];for(let r of e.relations.filter(b=>b.subjectId===l.id))S(r),p(r.citationIds),x.push({predicateId:r.predicateId,objectId:r.objectId,status:r.status});return f(!t.aborted),{name:C[0]??null,names:C,resourceType:l.type,identityStatus:l.identityStatus,identifierStatus:c.status,facts:y,citations:[...u.values()],unresolvedRelations:x,canonicalIdentityAsserted:!1,automaticPlanningEligible:!1,nutritionAggregationEligible:!1}}function K({selection:e,fetchImpl:n=globalThis.fetch}={}){let t=null;try{t=L(e)}catch{}let a=!1,i=new Set;async function o(d,{signal:S}={}){let l=structuredClone(d?.sourceBarcodeCandidate),c,g,s;try{f(!a&&i.size===0&&t&&l&&l.manifestSha256===t.manifestSha256&&l.indexReleaseId===t.indexReleaseId&&Ee(l.publicBase,w)),f(l.canonicalIdentityAsserted===!1&&l.automaticPlanningEligible===!1&&l.nutritionAggregationEligible===!1),f(l.query?.namespace==="barcode"&&typeof l.query.lexical=="string"&&l.query.lexical.length>0&&t.scopes.some(R=>R.source===l.query.source&&R.release===l.query.release)),X(l.reference,w);let u=l.reference.asset;f(u.bytes<=A.compressedBytes&&u.packetCount<=A.packets&&u.path.endsWith(".jsonl.gz"));let p=new URL(u.path,w.origin);f(p.origin===w.origin&&p.pathname===u.path&&!p.search&&!p.hash),c=new AbortController,i.add(c),s=()=>c.abort(),S?.addEventListener("abort",s,{once:!0}),f(!S?.aborted),g=setTimeout(s,A.timeoutMs);let E=await n(p.href,{method:"GET",credentials:"omit",cache:"no-store",redirect:"error",signal:c.signal});f(E.status===200&&!E.redirected&&(!E.url||E.url===p.href)),f(!E.headers.get("content-encoding")||E.headers.get("content-encoding")==="identity"),E.headers.has("content-length")&&f(Number(E.headers.get("content-length"))===u.bytes);let m=await re(E.body,u.bytes,c.signal);f(m.byteLength===u.bytes&&await Y(m)===u.sha256&&!c.signal.aborted);let C=await re(new Blob([m]).stream().pipeThrough(new DecompressionStream("gzip")),A.expandedBytes,c.signal),y=new TextDecoder("utf-8",{fatal:!0}).decode(C);f(y.endsWith(`
`));let x=y.slice(0,-1).split(`
`);f(x.length===u.packetCount&&x.length<=A.packets);let r=x[u.packetOrdinal];f(new TextEncoder().encode(r).length<=A.packetBytes);let b=await oe(D(r),l,c.signal);return f(!a&&!c.signal.aborted),{...d,name:b.name,sourceBarcodeCandidate:{...l,hydrationState:"verified",factsState:"verified-original-public-packet",facts:b}}}catch{return{...d,sourceBarcodeCandidate:{...l,hydrationState:"unavailable",factsState:"technical-details-unavailable"}}}finally{clearTimeout(g),s&&S?.removeEventListener("abort",s),c&&i.delete(c)}}return Object.freeze({hydrate:o,destroy(){a=!0;for(let d of i)d.abort();i.clear()}})}function Q(e){let n=e?.sourceBarcodeCandidate,t=n?.facts;return n?.hydrationState!=="verified"||!t?null:[{label:t.name||"Verified source identifier \xB7 name unknown",text:n.query.lexical},{label:"Source scope / assertion",text:n.query.source+" \xB7 "+n.query.release+" \xB7 "+t.identifierStatus+" \xB7 "+t.identityStatus},{label:"Original resource type",text:t.resourceType},...t.facts.map(a=>({label:a.label,text:a.text+" ["+a.status+"]"})),...t.citations.map(a=>({label:"Source citation / licence",text:a.sourceId+" \xB7 "+a.revisionId+" \xB7 "+a.license+" \xB7 "+a.attribution+" \xB7 "+(a.originalRecordId||"record unknown")+" \xB7 "+(a.originalUrl||"source URL unknown")})),...t.unresolvedRelations.map(a=>({label:"Related source facts unresolved",text:a.predicateId+" \u2192 "+a.objectId+"; this referenced packet has not been verified. Nutrition/ingredients remain unknown where not supplied above."})),{label:"Unspecified source facts",text:"Any name, ingredient, quantity or nutrient fact not supplied above remains unknown in this verified packet. Index null references do not establish absence. Related packets remain unhydrated."},{label:"Evidence boundary",text:"Exact original public asset SHA/bytes, packet ordinal, resource and identifier assertion verified. Fields retain source names, units, zero, unknown and basis. No canonical identity, planning or nutrition aggregation admission."}]}var se=(e,n)=>JSON.stringify(e)===JSON.stringify(n);function v(e,n,t=[]){if(!n?.enabled)return e;let a=new Map(t.map(g=>[g.id,g])),i=n.matches.map(g=>{let s=a.get(g.id);return s&&se(s.sourceBarcodeCandidate?.reference,g.sourceBarcodeCandidate?.reference)&&se(s.sourceBarcodeCandidate?.query,g.sourceBarcodeCandidate?.query)&&s.sourceBarcodeCandidate?.manifestSha256===g.sourceBarcodeCandidate?.manifestSha256?s:g}),o=[...e.matches,...i],d=(e.providerStates||[]).some(g=>g.error)||!!e.error&&!["UNSUPPORTED_EXACT_BARCODE"].includes(e.error),S=n.configurationError||n.lanes.some(g=>g.status==="index-unavailable"||g.pageError),l=d||S,c=o.length?l?"partial":o.length>1||e.hasMore||n.ambiguous?"ambiguous":"source-match":l?"unavailable":e.hasMore?"searching":n.complete&&n.lanes.every(g=>g.status==="source-key-not-found")?"scoped-miss":"unavailable";return{...e,matches:o,status:c,foundationResult:e,sourceBarcodeResult:n,hasMore:e.hasMore,nextCursor:e.nextCursor,canonicalIdentityAsserted:!1,automaticPlanningEligible:!1,nutritionAggregationEligible:!1}}function Se({foundationInventory:e,selection:n,fetchImpl:t=globalThis.fetch,limit:a=20}={}){if(!e||typeof e.lookupIdentifiers!="function"||typeof e.mergeIdentifierPages!="function"||typeof e.destroy!="function")throw Error("EXISTING_FOUNDATION_INVENTORY_REQUIRED");let i=V({selection:n,fetchImpl:t,limit:a}),o=!1,d=K({selection:n,fetchImpl:t});async function S(s,u,p=null,E=null,m="barcode"){let C=await e.lookupIdentifiers(s,u,p,E,m);if(o||m!=="barcode"||p!==null)return{...C,foundationResult:C};let y=await i(s,u,E,m);return o?{...C,foundationResult:C}:v(C,y)}function l(s,u){let p=e.mergeIdentifierPages(s.foundationResult||s,u.foundationResult||u);return v(p,s.sourceBarcodeResult,s.matches)}async function c(s){if(o||!s?.sourceBarcodeResult?.enabled)throw Error("SOURCE_BARCODE_PAGE_CONTEXT_CHANGED");let u=s.sourceBarcodeResult;if(u.original!==s.raw&&u.original!==s.original||u.generation!==(s.queryGeneration??s.generation))throw Error("SOURCE_BARCODE_PAGE_CONTEXT_CHANGED");let p=await i.more(u);if(o||s.sourceBarcodeResult!==u)throw Error("SOURCE_BARCODE_PAGE_CONTEXT_CHANGED");return v(s.foundationResult||s,p,s.matches)}async function g(s,u){if(o||!s?.matches?.includes(u)||u?.kind!=="source-barcode-candidate"||s.sourceBarcodeResult?.generation!==(s.queryGeneration??s.generation))throw Error("SOURCE_DETAILS_CONTEXT_CHANGED");let p=s.sourceBarcodeResult,E=await d.hydrate(u);if(o||s.sourceBarcodeResult!==p||!s.matches.includes(u))throw Error("SOURCE_DETAILS_CONTEXT_CHANGED");return{...s,matches:s.matches.map(m=>m===u?E:m)}}return Object.freeze({lookupIdentifiers:S,mergeIdentifierPages:l,moreSourceBarcode:c,hydrateSourceBarcode:g,destroy(){o||(o=!0,i.destroy(),d.destroy(),e.destroy())}})}function me(e,n,t,a="overview"){if(n?.kind==="source-barcode-candidate")return Q(n)||[...z(n,t,a),...n.sourceBarcodeCandidate.hydrationState==="unavailable"?[{label:"Source details unavailable",text:"Technical verification or loading failed. Identifier retained; no source absence is established."}]:[]];let i=e(n,t,a),o=t?.sourceBarcodeResult;if(!o?.enabled)return i;let d=o.matches.length,S=o.configurationError||!o.complete||o.lanes.some(l=>l.status==="index-unavailable"||l.pageError);return[...i,{label:"Additional source identifier index",text:d?d+" source-scoped identifier reference(s) loaded. Choose a reference for its exact source binding; original facts remain pending verified hydration.":S?"The additional index could not be checked completely. The original identifier is retained; no source absence is established.":"No source key in the selected complete public index scopes. Other sources may differ; the original identifier is retained."}]}function Ce(e){if(e?.status==="source-match"&&e.matches?.length===1)return e.matches[0];let n=e?.foundationResult,t=e?.sourceBarcodeResult;return t?.enabled&&(t.configurationError||!t.complete||t.lanes?.some(i=>i.status==="index-unavailable"||i.pageError))&&t.matches?.length===0&&n?.status==="source-match"&&n.matches?.length===1&&!n.hasMore?n.matches[0]:null}return pe(Re);})();

var _OffMenuSourceBarcodeSelection = {"manifestSha256":"d22d0c464d32ea8df1b81da1f74701db5b563cd3c5b69c1d4e0f9b116709c839","indexReleaseId":"source-barcode-index-v1-20261029","scopes":[{"source":"off","release":"2026-10-12"},{"source":"usda-files","release":"usda-2026-04"}]};
var _OffMenuGuestFoundation=(()=>{var P=Object.defineProperty;var ie=Object.getOwnPropertyDescriptor;var se=Object.getOwnPropertyNames;var ce=Object.prototype.hasOwnProperty;var ue=(e,o)=>{for(var a in o)P(e,a,{get:o[a],enumerable:!0})},le=(e,o,a,i)=>{if(o&&typeof o=="object"||typeof o=="function")for(let t of se(o))!ce.call(e,t)&&t!==a&&P(e,t,{get:()=>o[t],enumerable:!(i=ie(o,t))||i.enumerable});return e};var de=e=>le(P({},"__esModule",{value:!0}),e);var Ne={};ue(Ne,{createGuestFoundationLookup:()=>Ie,foundationReadout:()=>ye});var M={schema:"offmenu-foundation-handoff-bindings/2",selections:[{releaseId:"offmenu-foundation-production-20261027-v1",manifestSha256:"10f4f5acb9dbab8e5411dc7c7aa9136d6bb6317cd5eb11d9ec6c9ccdd4a1a0db",sourceAdmissionSha256:"fedce50756a6598ee3fc53d6e0507a4d21103711dcaee6911c61679b70cb2cdb",sources:{off:{releaseId:"2026-10-12",qualificationSha256:"96a192c8d7ec08e4116b9c7b1c8fb77da452a22820656fa43ceef1200c96cfc0",license:"ODbL / DbCL; images CC BY-SA",attribution:"Open Food Facts"},"usda-files":{releaseId:"2026-04-30",qualificationSha256:"e648f1d83bb1012e076d43610aa80ed6b811dfa1ff3521d028bcf274923792d9",license:"USDA FoodData Central public domain / CC0 (retained declaration)",attribution:"USDA Agricultural Research Service FoodData Central"}}},{releaseId:"offmenu-reviewed-foundation-r8-local-20261027-v1",manifestSha256:"f9338984eb416c0c4681697c5257ae72cf2e178fe88879331d4b74efc6dc9aa7",sourceAdmissionSha256:"d02e9df26a9469328118cc12321566cc2cef8df2037957372812a1f954439258",sources:{off:{releaseId:"2026-10-12",qualificationSha256:"96a192c8d7ec08e4116b9c7b1c8fb77da452a22820656fa43ceef1200c96cfc0",license:"ODbL / DbCL; images CC BY-SA",attribution:"Open Food Facts"},"usda-files":{releaseId:"2026-04-30",qualificationSha256:"e648f1d83bb1012e076d43610aa80ed6b811dfa1ff3521d028bcf274923792d9",license:"USDA FoodData Central public domain / CC0 (retained declaration)",attribution:"USDA Agricultural Research Service FoodData Central"}}},{releaseId:"offmenu-reviewed-foundation-r2-named-r3-20261027-v1",manifestSha256:"fc2e17c8864cef45b36ad7cfee4a3c0ef15dd73acb8dbe54cf008fca141cd4a7",sourceAdmissionSha256:"de1ae0bf0be081145352f3ddb92a6d2ca1a6df75d0c86bbf608a2835fd334c87",sources:{off:{releaseId:"2026-10-12",qualificationSha256:"96a192c8d7ec08e4116b9c7b1c8fb77da452a22820656fa43ceef1200c96cfc0",license:"ODbL / DbCL; images CC BY-SA",attribution:"Open Food Facts"},"usda-files":{releaseId:"2026-04-30",qualificationSha256:"e648f1d83bb1012e076d43610aa80ed6b811dfa1ff3521d028bcf274923792d9",license:"USDA FoodData Central public domain / CC0 (retained declaration)",attribution:"USDA Agricultural Research Service FoodData Central"}}},{releaseId:"offmenu-reviewed-foundation-r2-20261027-v1",manifestSha256:"9fe0cb763cec1e8b4afee9c77d508f98f15788f1ad4400fb2ecb659b14730acc",sourceAdmissionSha256:"2a29f7f0949d8b41bf60d670d60bcb6651aaaff8f1ab3c7c812f4779d7d0ceb9",sources:{off:{releaseId:"2026-10-12",qualificationSha256:"96a192c8d7ec08e4116b9c7b1c8fb77da452a22820656fa43ceef1200c96cfc0",license:"ODbL / DbCL; images CC BY-SA",attribution:"Open Food Facts"},"usda-files":{releaseId:"2026-04-30",qualificationSha256:"e648f1d83bb1012e076d43610aa80ed6b811dfa1ff3521d028bcf274923792d9",license:"USDA FoodData Central public domain / CC0 (retained declaration)",attribution:"USDA Agricultural Research Service FoodData Central"}}}]};var z="offmenu-foundation-source-reference/1",k="offmenu-foundation-scanner-handoff/1",q=["sourceId","releaseId","recordId","sourceObservationSha256","sourceDocumentSha256","inputDatabaseSha256","sourceQualificationSha256"],j=["normalizationComplete","fullProductComplete","goldAdmitted","automaticPlanningEligible","recipeNutritionJoinsAccepted"],U=/^[a-f0-9]{64}$/,fe=e=>typeof e=="string"&&/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(e),B=e=>e!==null&&typeof e=="object"&&!Array.isArray(e),C=(e,o)=>typeof e=="string"&&e.length>0&&e.length<=o&&!/[\x00-\x1f\x7f]/.test(e),S=(e,o)=>{if(!e)throw Error(o)},v=(e,o)=>B(e)&&Object.keys(e).length===o.length&&o.every(a=>Object.hasOwn(e,a));function Q(e){if(typeof e!="string"||!/^(?:[0-9]{8}|[0-9]{12}|[0-9]{13}|[0-9]{14})$/.test(e))return!1;let o=0,a=3;for(let i=e.length-2;i>=0;i--)o+=Number(e[i])*a,a=a===3?1:3;return(10-o%10)%10===Number(e.at(-1))}function pe(e){let o=B(e)&&e.schema==="offmenu-foundation-handoff-bindings/2";S(!o||v(e,["schema","selections"]),"Fixed foundation handoff selections required.");let a=structuredClone(o?e.selections:[e]);S(Array.isArray(a)&&a.length>0&&a.length<=8&&a.every(n=>C(n?.releaseId,128)&&U.test(n.manifestSha256)&&U.test(n.sourceAdmissionSha256)&&B(n.sources)),"Fixed foundation handoff selection required.");let i=n=>JSON.stringify([n.releaseId,n.manifestSha256,n.sourceAdmissionSha256]);S(new Set(a.map(i)).size===a.length,"Foundation handoff selections repeat a cut.");function t(n,r){let d=["schema","fieldContract","releaseId","manifestSha256","sourceAdmissionSha256","recordId","namespace","lexicalValue","nativeRecordId","stageRecordWireSha256","sourceBinding","license","attribution","foundationComplete",...j],f=a.find(m=>m.releaseId===n?.releaseId&&m.manifestSha256===n?.manifestSha256&&m.sourceAdmissionSha256===n?.sourceAdmissionSha256);S(f&&v(n,d)&&n.schema===z&&n.fieldContract==="offmenu-barcode-foundation-phase/2","Foundation source selection changed.");let s=n.sourceBinding,g=f.sources[s?.sourceId];return S(v(s,q)&&g&&C(s.sourceId,40)&&s.releaseId===g.releaseId&&s.sourceQualificationSha256===g.qualificationSha256&&C(s.recordId,250)&&q.slice(3).every(m=>U.test(s[m])),"Foundation source subject is incomplete."),S(n.namespace==="barcode"&&Q(r)&&n.lexicalValue===r&&C(n.recordId,250)&&C(n.nativeRecordId,250)&&n.nativeRecordId.startsWith(s.sourceId+":product:")&&U.test(n.stageRecordWireSha256),"Foundation exact barcode or wire binding changed."),S(n.license===g.license&&n.attribution===g.attribution&&C(n.license,512)&&C(n.attribution,512)&&n.foundationComplete===!0&&j.every(m=>n[m]===!1),"Foundation qualification or source notices changed."),{schema:z,fieldContract:n.fieldContract,releaseId:f.releaseId,manifestSha256:f.manifestSha256,sourceAdmissionSha256:f.sourceAdmissionSha256,recordId:n.recordId,namespace:"barcode",lexicalValue:r,nativeRecordId:n.nativeRecordId,stageRecordWireSha256:n.stageRecordWireSha256,sourceBinding:Object.fromEntries(q.map(m=>[m,s[m]])),license:n.license,attribution:n.attribution,foundationComplete:!0,...Object.fromEntries(j.map(m=>[m,!1]))}}let u=(n,r)=>{try{return t(n,r),!0}catch{return!1}};function l(n){return S(v(n,["operationId","barcode","namespace","symbology","name","brand","userSelected","foundationSourceReference"])&&fe(n.operationId)&&n.namespace==="barcode"&&n.userSelected===!0&&Q(n.barcode)&&(n.symbology===null||C(n.symbology,128))&&(n.name===null||C(n.name,240))&&(n.brand===null||C(n.brand,240)),"Explicit source choice is required for every kept item."),{operationId:n.operationId,barcode:n.barcode,namespace:"barcode",symbology:n.symbology,name:n.name,brand:n.brand,userSelected:!0,foundationSourceReference:t(n.foundationSourceReference,n.barcode)}}let b=n=>JSON.stringify(l(n));function c(n){S(v(n,["schema","items"])&&n.schema===k&&Array.isArray(n.items)&&n.items.length>0&&n.items.length<=20,"Foundation scanner handoff is invalid.");let r=n.items.map(l);S(new Set(r.map(f=>f.operationId)).size===r.length,"Scanner handoff repeats an operation.");let d={schema:k,items:r};return S(new TextEncoder().encode(JSON.stringify(d)).byteLength<=3e3,"Scanner handoff exceeds the existing tab limit. Review a smaller batch."),d}function p(n){return S(Array.isArray(n)&&n.length>0,"Scan at least one item before finishing."),c({schema:k,items:n.map(r=>{let d=r?.selectedRecord;return S(r.foundationLookup===!0&&r.namespace==="barcode"&&r.sourceChoiceConfirmed===!0&&r.status!=="pending"&&r.pending!==!0&&r.lookupPending!==!0&&r.matches?.includes(d),"Choose and confirm a qualified source observation for every kept item."),{operationId:r.id,barcode:r.raw,namespace:"barcode",symbology:r.symbology??null,name:d.name??null,brand:d.brand??null,userSelected:!0,foundationSourceReference:d.foundationSourceReference}})})}return Object.freeze({validFoundationSourceReference:u,copyFoundationSourceReference:t,foundationHandoffFingerprint:b,parseFoundationScannerHandoff:c,createFoundationScannerHandoff:p})}var he=pe(M),{validFoundationSourceReference:G,copyFoundationSourceReference:$,foundationHandoffFingerprint:Re,parseFoundationScannerHandoff:De,createFoundationScannerHandoff:Te}=he;var X="offmenu-barcode-foundation-phase/2",I={releaseId:"offmenu-foundation-production-20261027-v1",manifestSha256:"10f4f5acb9dbab8e5411dc7c7aa9136d6bb6317cd5eb11d9ec6c9ccdd4a1a0db"},J=["off","usda-files"],Y="offmenu-local-foundation-scanner/1",x=["sourceId","releaseId","recordId","sourceObservationSha256","sourceDocumentSha256","inputDatabaseSha256","sourceQualificationSha256"],be=["baseMaterial","milkBase","fatClass","sugarStatus","saltStatus","lactoseStatus","processing","form","flavour","scent","colour","material","size","netAmount","packageCount","concentration","strength","dimensions","capacity","compatibility","finish","grade","originVariant","otherQualifiedVariant"],me=/^[a-f0-9]{64}$/,F=e=>e!==null&&typeof e=="object"&&!Array.isArray(e),y=e=>typeof e=="string"&&e.length>0&&e.length<=1024&&!/[\x00-\x1f\x7f]/.test(e),L=e=>Array.isArray(e)?"["+e.map(L).join(",")+"]":F(e)?"{"+Object.keys(e).sort().map(o=>JSON.stringify(o)+":"+L(e[o])).join(",")+"}":JSON.stringify(e),K=(e,o)=>L(e)===L(o),H=e=>JSON.stringify(x.map(o=>e.provenance[o]).concat(e.id));function Se(e,o,a){let i=e?.provenance,t=e?.data,u=e?.curation;return e?.schemaVersion==="1.0"&&e.kind==="product"&&y(e.id)&&F(i)&&i.sourceId===o&&i.visibility==="public"&&x.every(l=>y(i[l]))&&x.slice(3).every(l=>me.test(i[l]))&&y(i.license)&&y(i.attribution)&&u?.schema==="offmenu-foundation-curation/2"&&u.phaseContract===X&&u.rawSourcePayloadPublished===!1&&u.legacyCuratedAdmission===!1&&F(t)&&y(t.name)&&y(t.canonicalEnglishKey)&&y(t.canonicalConceptId)&&["ingredient","noningredient"].includes(t.classification)&&t.identifiers?.some(l=>l.system==="barcode"&&l.value===a)&&t.foundationComplete===!0&&["fullProductComplete","normalizationComplete","goldAdmitted","automaticPlanningEligible","recipeNutritionJoinsAccepted"].every(l=>t[l]===!1)&&t.meaningfulType?.state==="reviewed"&&y(t.meaningfulType.canonicalEnglishLabel)&&t.meaningfulType.subjectConceptId===t.canonicalConceptId&&F(t.variantParameters)&&Object.keys(t.variantParameters).length===24&&be.every(l=>F(t.variantParameters[l])&&["known","unknown"].includes(t.variantParameters[l].state))&&(!Object.hasOwn(e,"foundationSourceReference")||G(e.foundationSourceReference,a)&&e.foundationSourceReference.recordId===e.id&&e.foundationSourceReference.namespace==="barcode"&&e.foundationSourceReference.lexicalValue===a&&x.every(l=>e.foundationSourceReference.sourceBinding[l]===i[l]))}function ge(e){let o=structuredClone(e);return{id:H(o),name:"Canonical base \xB7 "+o.data.name,brand:null,provenance:structuredClone(o.provenance),foundationRecord:o,...G(o.foundationSourceReference,o.data.identifiers[0]?.value)?{foundationSourceReference:$(o.foundationSourceReference,o.data.identifiers[0].value)}:{},sourceObservationReference:null}}function Ae(e,o){let a=new Map;for(let i of[...e,...o]){let t=H(i.foundationRecord),u=a.get(t);if(u&&!K(u.foundationRecord,i.foundationRecord))throw Error("FOUNDATION_OBSERVATION_CHANGED");u||a.set(t,i)}return[...a.values()]}function W(e,o,a,i,t,u){let l=u.some(c=>c.pending),b=u.some(c=>c.error);return{original:e,namespace:"barcode",symbology:a,generation:o,requestCursor:i,foundationLookup:!0,matches:t,providerStates:u.map(c=>({...c})),status:b?t.length?"partial":"unavailable":t.length>1||t.length&&l?"ambiguous":t.length?"source-match":u.every(c=>c.lookupOutcome==="source-key-not-found")?"scoped-miss":"unavailable",hasMore:l,nextCursor:l?JSON.stringify({schema:Y,raw:e,generation:o,symbology:a,selection:I,lanes:u}):null,fullProductComplete:!1,goldAdmitted:!1,automaticPlanningEligible:!1,physicalProductEquivalenceAsserted:!1,externalFallback:!1}}function V({fetchImpl:e=globalThis.fetch}={}){return async function(a,i,t=null,u=null,l="barcode"){let b=n=>({...W(a,i,u,t,[],J.map(r=>({source:r,pending:!1,cursor:null,error:n,status:null}))),error:n});if(l!=="barcode"||typeof a!="string"||!/^\d{4,32}$/.test(a)||!Number.isSafeInteger(i)||u!==null&&typeof u!="string")return b("UNSUPPORTED_EXACT_BARCODE");let c=J.map(n=>({source:n,pending:!0,cursor:null,error:null,status:null}));if(t!==null)try{if(typeof t!="string"||t.length>6e3)throw Error();let n=JSON.parse(t);if(n.schema!==Y||n.raw!==a||n.generation!==i||n.symbology!==u||!K(n.selection,I)||!Array.isArray(n.lanes)||n.lanes.length!==2)throw Error();c=n.lanes.map((r,d)=>{if(r.source!==J[d]||typeof r.pending!="boolean"||r.cursor!==null&&(typeof r.cursor!="string"||r.cursor.length>700)||r.error!==null&&typeof r.error!="string")throw Error();return{...r}})}catch{return b("FOUNDATION_CURSOR_MISMATCH")}let p=[];for(let n of c){if(!n.pending)continue;n.pending=!1,n.error=null;let r=new URL("/api/corpus/foundation","http://offmenu.invalid");r.searchParams.set("source",n.source),r.searchParams.set("barcode",a),r.searchParams.set("limit","20"),n.cursor&&r.searchParams.set("cursor",n.cursor);try{let d=await e(r.pathname+r.search,{method:"GET",credentials:"omit",cache:"no-store",redirect:"error",mode:"same-origin",headers:{Accept:"application/json"}});if(n.status=d.status,d.status===503){try{let text=await d.clone().text();if(new TextEncoder().encode(text).byteLength>65536)throw Error("BOUND");let empty=JSON.parse(text);if(empty.schemaVersion==="1.0"&&empty.fieldContract===X&&empty.source===n.source&&empty.barcode===a&&empty.releaseId===I.releaseId&&empty.manifestSha256===I.manifestSha256&&empty.httpStatus===503&&empty.status==="own-data-unavailable"&&Array.isArray(empty.records)&&empty.records.length===0&&empty.qualifiedSourceObservationCount===0&&empty.externalFallback===false&&empty.physicalProductEquivalenceAsserted===false&&empty.goldAdmitted===false&&empty.fullProductComplete===false){n.error=null;n.availabilityKind="no-usable-qualified-details";n.lookupOutcome="source-key-not-found";n.observationCount=0;continue}}catch{}}if(d.status!==200){n.error=d.status===503?"OWN_DATA_UNAVAILABLE":d.status===401||d.status===403?"FOUNDATION_ACCESS_UNAVAILABLE":"FOUNDATION_QUERY_UNAVAILABLE";continue}let f=await d.text();if(new TextEncoder().encode(f).byteLength>2097152)throw Error("FOUNDATION_RESPONSE_BOUND");let s=JSON.parse(f);if(s.schemaVersion!=="1.0"||s.fieldContract!==X||s.source!==n.source||s.barcode!==a||s.releaseId!==I.releaseId||s.manifestSha256!==I.manifestSha256||s.externalFallback!==!1||s.physicalProductEquivalenceAsserted!==!1||s.goldAdmitted!==!1||s.fullProductComplete!==!1||s.httpStatus!==200||s.status!=="phase-qualified-own-data"||!Array.isArray(s.records)||s.records.length<1||s.records.length>20||!Number.isSafeInteger(s.qualifiedSourceObservationCount)||s.qualifiedSourceObservationCount<s.records.length||s.nextCursor!==null&&(typeof s.nextCursor!="string"||s.nextCursor.length>700||!s.nextCursor.length)||s.records.some(g=>!Se(g,n.source,a)))throw Error("FOUNDATION_RESPONSE_MISMATCH");if(new Set(s.records.map(H)).size!==s.records.length)throw Error("FOUNDATION_DUPLICATE_OBSERVATION");p.push(...s.records.map(ge)),n.cursor=s.nextCursor,n.pending=s.nextCursor!==null,n.observationCount=s.qualifiedSourceObservationCount}catch{n.error="FOUNDATION_RESPONSE_UNAVAILABLE",n.pending=!1}}return W(a,i,u,t,Ae([],p),c)}}var xe=V();var _=e=>e==null?"Unknown":typeof e=="object"?JSON.stringify(e):String(e);function Z(e,o,a="overview"){let i=[{label:"Foundation observations",text:"Source-qualified base and type only. Full product, nutrition/recipe joins, normalization, Gold and automatic inventory/planning remain unaccepted. Distinct observations are not physical-product equivalence."}];for(let b of o?.providerStates||[])i.push({label:"Source \xB7 "+b.source,text:b.error?b.error+" \xB7 selected representation unavailable, not global absence":_(b.observationCount)+" selected source observations"+(b.pending?" \xB7 more pages remain":"")});let t=e?.foundationRecord;if(!t)return i.push(o?.status==="scoped-miss"?{label:"Barcode retained",text:"No qualified details in the selected source indexes for "+(o.raw??o.original)+". Other sources may differ. Product, ingredient and nutrition facts remain unknown."}:o?.status==="searching"?{label:"Barcode retained",text:"More selected barcode representations remain to check. Details remain unknown."}:{label:"Source choice",text:"Inspect the separate source observations. No product identity is inferred from the code alone."}),i;let u=t.data,l=t.provenance;if(i.push({label:"Canonical English base",text:u.name},{label:"Meaningful type",text:u.meaningfulType.canonicalEnglishLabel},{label:"Ingredient eligibility",text:u.classification},{label:"Source notice",text:l.attribution+" \xB7 "+l.license},{label:"Source observation",text:l.sourceId+" \xB7 "+l.releaseId+" \xB7 "+l.recordId}),a==="nutrition"&&i.push({label:"Nutrition",text:"Not joined or accepted by this foundation response. Unknown, not zero."}),a==="overview"||a==="ingredients")for(let[b,c]of Object.entries(u.variantParameters))i.push({label:b+" \xB7 "+c.state,text:c.state==="unknown"?"Unknown \xB7 "+_(c.reason)+" \xB7 "+_(c.qualificationDisposition):_(c.value)});return a==="source"&&i.push({label:"Exact source binding",text:JSON.stringify(l)},{label:"Reviewed type relation",text:JSON.stringify(u.meaningfulType)},{label:"All parameter states and evidence",text:JSON.stringify(u.variantParameters)},{label:"Complete supplied foundation observation",text:JSON.stringify(t)}),i}var Oe="https://offmenu.aldous.info",ee="offmenu-guest-foundation-pages/1",N=e=>Array.isArray(e)?"["+e.map(N).join(",")+"]":e&&typeof e=="object"?"{"+Object.keys(e).sort().map(o=>JSON.stringify(o)+":"+N(e[o])).join(",")+"}":JSON.stringify(e),Ce=(e,o,a,i,t)=>({original:e,namespace:"barcode",symbology:a,generation:o,requestCursor:i,foundationLookup:!0,matches:[],status:"unavailable",hasMore:!1,nextCursor:null,providerStates:[],externalFallback:!1,error:t}),ne=(e,o,a)=>o.some(i=>i.error)?e.length?"partial":"unavailable":e.length>1||e.length&&a?"ambiguous":e.length?"source-match":a?"searching":o.length&&o.every(i=>i.lookupOutcome==="source-key-not-found")?"scoped-miss":"unavailable";function Ie({origin:e,fetchImpl:o=globalThis.fetch,analyzeIdentifier:a}={}){if(e!==Oe||globalThis.location?.origin&&globalThis.location.origin!==e||typeof o!="function"||typeof a!="function")throw Error("EXACT_PUBLIC_FOUNDATION_ORIGIN_REQUIRED");let i=!1,t=0,u=new Set;async function l(c,p,n=null,r=null,d="barcode"){let f=h=>Ce(c,p,r,n,h);if(i)return f("GUEST_FOUNDATION_CLOSED");if(d!=="barcode"||typeof c!="string"||!/^\d{4,32}$/.test(c)||!Number.isSafeInteger(p)||r!==null&&typeof r!="string")return f("UNSUPPORTED_EXACT_BARCODE");let s;try{let h=a({original:c,namespace:d,representationHint:r});if(s=[{value:c,rule:null},...h.status==="checksum-valid"?h.labelledEquivalents:[]].filter((A,O,D)=>/^\d{4,32}$/.test(A.value)&&D.findIndex(T=>T.value===A.value)===O),!s.length||s.length>8)throw Error()}catch{return f("UNSUPPORTED_EXACT_BARCODE")}let g=0,m=null;if(n!==null)try{if(typeof n!="string"||n.length>1e4)throw Error();let h=JSON.parse(n);if(h.schema!==ee||h.original!==c||h.generation!==p||h.symbology!==r||N(h.selection)!==N(I)||!Number.isSafeInteger(h.index)||h.index<0||h.index>=s.length||h.sourceCursor!==null&&(typeof h.sourceCursor!="string"||h.sourceCursor.length>6e3))throw Error();g=h.index,m=h.sourceCursor}catch{return f("FOUNDATION_GUEST_CURSOR_MISMATCH")}let oe=t,R=new AbortController;u.add(R);let te=setTimeout(()=>R.abort(),12e3),ae=(h,A={})=>{let O=new URL(h,e);if(O.origin!==e||O.pathname!=="/api/corpus/foundation"||A.method&&A.method!=="GET")throw Error("GUEST_FOUNDATION_ROUTE_CHANGED");return o(O.href,{...A,method:"GET",credentials:"omit",cache:"no-store",redirect:"error",mode:"same-origin",signal:R.signal})};try{let h=V({fetchImpl:ae}),A=s[g],O=await h(A.value,p,m,r,d);if(i||oe!==t)return f("GUEST_FOUNDATION_CLOSED");let D=O.matches.map(re=>{let E=structuredClone(re);return E.id=JSON.stringify([E.id,A.value]),E.matchContext={originalLexicalValue:c,sourceLexicalValue:A.value,symbology:r,matchType:A.value===c?"exact":"representation-alias",equivalence:A.rule??null,physicalProductEquivalenceAsserted:!1},E.lookupOrigin={provider:"qualified-owned-foundation",selection:{...I}},E.detail={fields:{},sourceBinding:{sourceId:E.provenance.sourceId},assurance:"Qualified canonical base and type only; no full-product, normalization, nutrition or automatic inventory admission."},E}),T=O.hasMore?g:g+1,w=T<s.length;return{...O,original:c,requestCursor:n,matches:D,status:ne(D,O.providerStates,w),hasMore:w,nextCursor:w?JSON.stringify({schema:ee,original:c,generation:p,symbology:r,selection:I,index:T,sourceCursor:O.hasMore?O.nextCursor:null}):null,selectedFoundation:{...I},coverage:{scope:"selected-qualified-owned-foundation-only",externalFallback:!1,globalProductTotal:null,identityEquivalence:!1},guestInventoryMutation:!1}}catch{return f("GUEST_FOUNDATION_UNAVAILABLE")}finally{clearTimeout(te),u.delete(R)}}function b(c,p){if(!c.foundationLookup||!p.foundationLookup||c.original!==p.original||c.namespace!==p.namespace||c.generation!==p.generation||c.symbology!==p.symbology||c.nextCursor!==p.requestCursor||N(c.selectedFoundation)!==N(p.selectedFoundation))throw Error("GUEST_FOUNDATION_PAGE_CHANGED");let n=new Map;for(let f of[...c.matches,...p.matches]){if(n.has(f.id)&&N(n.get(f.id))!==N(f))throw Error("GUEST_FOUNDATION_OBSERVATION_CHANGED");n.set(f.id,f)}let r=[...n.values()],d=p.providerStates;return{...p,matches:r,status:ne(r,d,p.hasMore)}}return Object.freeze({lookupIdentifiers:l,mergeIdentifierPages:b,destroy(){i=!0,t++;for(let c of u)c.abort();u.clear()}})}function ye(e,o,a){let i=Z(e,o,a);return e?.matchContext?.matchType==="representation-alias"&&i.splice(1,0,{label:"Barcode representation",text:"Original "+e.matchContext.originalLexicalValue+"; selected source representation "+e.matchContext.sourceLexicalValue+". Representation relation only, not physical-product equivalence."}),i.push({label:"Demo session",text:"Selected source observations remain in this tab. Finish does not add pantry stock, infer quantity, join nutrition, or change a private profile."}),i}return de(Ne);})();

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/scanner-identity-v2.js
var IDENTIFIER_DB = "97c2f7390f75d8d187b49c927652515cd829e095301d7b305a0081120c7502f0";
var IDENTIFIER_RUN = "worker57-full-retained-identifiers-v1";
var DETAIL_SELECTION = "d9a08c3b2b9eec880418b8108d60c177a253b53802e8ea0453eb8fd502498290";
var DISPOSITIONS = /* @__PURE__ */ new Set(["source-asserted", "unresolved", "invalid"]);
var NAMESPACES = /* @__PURE__ */ new Set(["barcode", "USDA-FDC"]);
var SYMBOLOGIES = /* @__PURE__ */ new Set(["EAN-13", "EAN-8", "UPC-A", "UPC-E", "GTIN-14"]);
var bounded = (value, max) => typeof value === "string" && value.length > 0 && value.length <= max;
function validGTIN(value) {
  if (!/^(?:\d{8}|\d{12}|\d{13}|\d{14})$/.test(value)) return false;
  let sum = 0;
  for (let i14 = value.length - 2, weight = 3; i14 >= 0; i14--, weight = 4 - weight) sum += Number(value[i14]) * weight;
  return (10 - sum % 10) % 10 === Number(value.at(-1));
}
function expectedForms(original, symbology = null, namespace = "barcode") {
  const forms = [{ lexicalValue: original, matchType: "exact", equivalence: null }];
  if (namespace !== "barcode") return forms;
  const add = (lexicalValue, equivalence) => {
    if (!forms.some((form) => form.lexicalValue === lexicalValue)) forms.push({ lexicalValue, matchType: "representation-alias", equivalence });
  };
  let expanded = original;
  if (symbology === "UPC-E") {
    if (!/^[01]\d{7}$/.test(original)) return forms;
    const [n, a, b, c, d, e, f, k] = original;
    expanded = f <= "2" ? n + a + b + f + "0000" + c + d + e + k : f === "3" ? n + a + b + c + "00000" + d + e + k : f === "4" ? n + a + b + c + d + "00000" + e + k : n + a + b + c + d + e + "0000" + f + k;
    if (!validGTIN(expanded)) return forms;
    add(expanded, "explicit-upc-e-to-upc-a");
  }
  if (!validGTIN(expanded)) return forms;
  if (expanded.length === 12 && (!symbology || symbology === "UPC-A" || symbology === "UPC-E")) add("0" + expanded, "upc-a-as-leading-zero-ean-13");
  else if (expanded.length === 13 && expanded[0] === "0" && (!symbology || symbology === "EAN-13")) add(expanded.slice(1), "leading-zero-ean-13-as-upc-a");
  return forms;
}
function validSourceObservationReference(ref, original) {
  const key = ref?.observationKey;
  const form = expectedForms(original, ref?.symbology, ref?.namespace).find((item) => item.lexicalValue === ref?.sourceLexicalValue);
  return ref?.schema === "offmenu-identifier-observation/2" && ref.databaseSha256 === IDENTIFIER_DB && ref.runId === IDENTIFIER_RUN && NAMESPACES.has(ref.namespace) && ref.originalLexicalValue === original && bounded(ref.sourceId, 40) && (ref.releaseId === null || bounded(ref.releaseId, 80)) && (ref.sourceRecordId === null || bounded(ref.sourceRecordId, 200)) && (ref.symbology === null || ref.namespace === "barcode" && SYMBOLOGIES.has(ref.symbology)) && DISPOSITIONS.has(ref.disposition) && form?.matchType === ref.matchType && form?.equivalence === ref.equivalence && key?.run_id === ref.runId && bounded(key.input_id, 250) && Number.isSafeInteger(key.record_ordinal) && key.record_ordinal >= 0 && Number.isSafeInteger(key.assertion_id) && key.assertion_id > 0 && ref.detailSelectionSha256 === DETAIL_SELECTION;
}

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/source-classification-contract.mjs
var CLASSIFICATION_CONTRACT = "offmenu-source-classification-relationships/1";
var dispositions = /* @__PURE__ */ new Set(["ingredient", "type", "nonfood", "not-applicable", "unresolved", "conflict"]);
var sha = (x) => typeof x === "string" && /^[0-9a-f]{64}$/.test(x);
var named = (x) => typeof x === "string" && x.length > 0;
var object = (x) => x !== null && typeof x === "object" && !Array.isArray(x) && [Object.prototype, null].includes(Object.getPrototypeOf(x));
var pin = (x) => object(x) && named(x.path) && sha(x.sha256) && Object.keys(x).length === 2;
function jsonData(v) {
  if (v === null || typeof v === "string" || typeof v === "boolean") return true;
  if (typeof v === "number") return Number.isFinite(v);
  if (Array.isArray(v)) return v.every(jsonData) && Object.keys(v).length === v.length;
  return object(v) && Object.values(v).every(jsonData);
}
function validateClassificationProjection(value) {
  if (!object(value) || !object(value.sourceBinding) || value.schema !== CLASSIFICATION_CONTRACT || !named(value.sourceBinding.sourceRecordId) || !sha(value.sourceBinding.snapshotSha256)) throw Error("Exact source record/snapshot binding required");
  const c = value.classification;
  if (!object(c) || !dispositions.has(c.disposition) || !Array.isArray(c.reasonCodes) || !c.reasonCodes.every(named) || !Array.isArray(c.evidenceRefs) || !c.evidenceRefs.every((e) => object(e) && named(e.assertionId) && pin(e.admission)) || !Array.isArray(value.relationships) || !value.relationships.every(object)) throw Error("Explicit classification disposition/evidence required");
  if (typeof c.identityEquivalence !== "boolean" || ![c.canonicalId, c.idScope, c.relation].every((x) => x === null || named(x))) throw Error("Explicit typed ID/scope/relation/identity state required");
  if (value.sourceBinding.sourceObservationReference !== void 0 && value.sourceBinding.sourceObservationReference !== null && !object(value.sourceBinding.sourceObservationReference)) throw Error("Observation reference must retain an object or null");
  if (!["applicable", "nonfood", "not-applicable", "unresolved", "conflict"].includes(c.ingredientApplicability)) throw Error("Explicit ingredient applicability required");
  if (c.disposition === "ingredient" && c.ingredientApplicability !== "applicable") throw Error("Nonfood cannot become an ingredient");
  if (["nonfood", "not-applicable", "unresolved", "conflict"].includes(c.disposition) && c.ingredientApplicability !== c.disposition) throw Error("Disposition/applicability conflict");
  if (["ingredient", "type"].includes(c.disposition) && (!named(c.canonicalId) || !named(c.idScope) || !named(c.relation))) throw Error("Supported ID requires explicit identity scope and relation");
  if (["unresolved", "conflict", "not-applicable", "nonfood"].includes(c.disposition) && c.canonicalId !== null) throw Error("Do not force an ingredient/type ID for unresolved/nonfood/not-applicable/conflict");
  if (c.disposition !== "unresolved" && c.disposition !== "conflict" && (!c.evidenceRefs.length || !c.evidenceRefs.every((e) => named(e.assertionId) && pin(e.admission)))) throw Error("Positive/nonfood/not-applicable decisions require qualified evidence and admission references");
  if (["unresolved", "conflict", "nonfood", "not-applicable"].includes(c.disposition) && !c.reasonCodes.length) throw Error("Unresolved/conflict/nonfood/not-applicable reason required");
  if (c.relation === "represents" && c.identityEquivalence !== false) throw Error("Scoped class membership is not identity equivalence");
  if (value.visualClassification !== null && !object(value.visualClassification)) throw Error("Visual contract is separately bound or null");
  if (!jsonData(value)) throw Error("Finite JSON data required; no silent coercion or dropped evidence");
  return value;
}
function unresolvedProjection(sourceBinding, reasonCodes = ["NO_ACCEPTED_CLASSIFICATION_EVIDENCE"]) {
  return validateClassificationProjection({
    schema: CLASSIFICATION_CONTRACT,
    sourceBinding: structuredClone(sourceBinding),
    classification: { disposition: "unresolved", ingredientApplicability: "unresolved", canonicalId: null, idScope: null, relation: null, identityEquivalence: false, evidenceRefs: [], reasonCodes: [...reasonCodes] },
    relationships: [],
    visualClassification: null
  });
}

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/production-scanner/scanner-source-assertions.js
var SOURCE_ASSERTIONS_SCHEMA = "offmenu-local-source-assertions/1";
var hex = (value) => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
var object2 = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
var encode = new TextEncoder();
var nativeKeys = ["run_id", "input_id", "record_ordinal", "assertion_id"];
var bindingKeys = ["observationKey", "sourceObservation", "sourceBinding", "referenceRecordId", "exactObservationBridge"];
var sourceKeys = [
  "sourceId",
  "releaseId",
  "identifierInputId",
  "identifierAssetSha256",
  "identifierRecordOrdinal",
  "identifierSourceRecordId",
  "identifierNativeRecordId",
  "originalSha256",
  "inputAssetSha256",
  "recordPointer",
  "recordPointers",
  "recordSha256",
  "rightsReceiptSha256",
  "operationReceiptSha256",
  "custodyReceiptSha256",
  "productReference",
  "componentDigests",
  "backingRole"
];
var fieldsMap = {
  name: "name",
  names: "names",
  brand: "brand",
  packageQuantity: "pack",
  servingQuantity: "serving",
  dataType: "dataType",
  ingredientDeclaration: "ingredientsText",
  categories: "categories",
  sourceAllergenClaims: "allergens",
  sourceTraceClaims: "traces",
  sourceDietaryLabelClaims: "labels",
  origins: "origins",
  manufacturingPlaces: "manufacturingPlaces",
  rawNutriments: "rawNutriments",
  nutritionSourceBasis: "nutritionSourceBasis",
  nutrientProfile: "nutrientProfile",
  imageUrlReferences: "imageUrlReferences"
};
var publicFields = [...Object.keys(fieldsMap), "markets", "sourceProvenance"];
function requireThat(value, code2) {
  if (!value) throw Error(code2);
}
function stable(value) {
  if (Array.isArray(value)) return "[" + value.map(stable).join(",") + "]";
  if (object2(value)) return "{" + Object.keys(value).sort().map((k) => JSON.stringify(k) + ":" + stable(value[k])).join(",") + "}";
  return JSON.stringify(value);
}
function copy(value, depth = 0, budget = { nodes: 0 }) {
  requireThat(++budget.nodes <= 2e4 && depth <= 24, "LOCAL_ASSERTION_STRUCTURE_BOUND");
  if (value === null || typeof value === "boolean" || typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    requireThat(encode.encode(value).length <= 131072, "LOCAL_ASSERTION_STRING_BOUND");
    return value;
  }
  if (Array.isArray(value)) {
    requireThat(value.length <= 4096, "LOCAL_ASSERTION_ARRAY_BOUND");
    return value.map((v) => copy(v, depth + 1, budget));
  }
  requireThat(object2(value) && [Object.prototype, null].includes(Object.getPrototypeOf(value)), "LOCAL_ASSERTION_JSON_REQUIRED");
  return Object.fromEntries(Object.entries(value).map(([k, v]) => {
    requireThat(encode.encode(k).length <= 4096, "LOCAL_ASSERTION_KEY_BOUND");
    return [k, copy(v, depth + 1, budget)];
  }));
}
function bounded2(value) {
  requireThat(encode.encode(JSON.stringify(value)).length <= 262144, "LOCAL_ASSERTION_OUTPUT_BOUND");
  return value;
}
function createSourceAssertion(input, { expectedReference, expectedBinding, expectedClassificationProjection } = {}) {
  const ref = input?.sourceObservationReference, binding = input?.binding, source = binding?.sourceBinding;
  requireThat(validSourceObservationReference(ref, ref?.originalLexicalValue) && ref.namespace === "barcode" && validGTIN(ref.originalLexicalValue), "LOCAL_ASSERTION_REFERENCE_INVALID");
  requireThat(stable(ref) === stable(expectedReference), "LOCAL_ASSERTION_EXPECTED_REFERENCE_MISMATCH");
  requireThat(object2(source) && object2(expectedBinding), "LOCAL_ASSERTION_EXPECTED_BINDING_REQUIRED");
  for (const key of sourceKeys) requireThat(Object.hasOwn(expectedBinding, key) && stable(source[key]) === stable(expectedBinding[key]), "LOCAL_ASSERTION_BINDING_" + key);
  for (const key of ["profileReference", "subsetCertificateSha256", "backingStoreSha256"])
    if (Object.hasOwn(expectedBinding, key) && !expectedBinding[key]?.captureState)
      requireThat(stable(source[key]) === stable(expectedBinding[key]), "LOCAL_ASSERTION_BINDING_" + key);
  requireThat(source.sourceId === ref.sourceId && source.releaseId === ref.releaseId && source.identifierInputId === ref.observationKey.input_id && source.identifierRecordOrdinal === ref.observationKey.record_ordinal && source.identifierSourceRecordId === ref.sourceRecordId, "LOCAL_ASSERTION_SOURCE_IDENTITY");
  requireThat(binding.observationKey?.databaseSha256 === ref.databaseSha256, "LOCAL_ASSERTION_DATABASE_BINDING");
  for (const key of nativeKeys) requireThat(
    binding.observationKey[key] === ref.observationKey[key],
    "LOCAL_ASSERTION_OBSERVATION_" + key
  );
  requireThat(binding.sourceObservation?.source_id === ref.sourceId && binding.sourceObservation?.release_id === ref.releaseId && binding.sourceObservation?.namespace === ref.namespace && binding.sourceObservation?.lexical_value === ref.sourceLexicalValue, "LOCAL_ASSERTION_SOURCE_OBSERVATION");
  requireThat(binding.sourceObservation?.artifact_sha256 === source.identifierAssetSha256 && binding.sourceObservation?.native_record_id === source.identifierNativeRecordId && binding.sourceObservation?.record_ordinal === source.identifierRecordOrdinal && binding.sourceObservation?.source_record_id === ref.sourceRecordId, "LOCAL_ASSERTION_RECORD_LINEAGE");
  for (const key of [
    "originalSha256",
    "inputAssetSha256",
    "recordSha256",
    "rightsReceiptSha256",
    "operationReceiptSha256",
    "custodyReceiptSha256"
  ]) requireThat(hex(source[key]), "LOCAL_ASSERTION_DIGEST_" + key);
  requireThat(object2(source.componentDigests) && Object.keys(source.componentDigests).length > 0 && Object.values(source.componentDigests).every(hex), "LOCAL_ASSERTION_COMPONENT_DIGESTS");
  const provenance = input.fields?.sourceProvenance;
  requireThat(provenance?.state === "present" && provenance.value?.visibility === "public" && provenance.value.sourceId === source.sourceId, "LOCAL_ASSERTION_PUBLIC_PROVENANCE_REQUIRED");
  for (const [key, expected] of [
    ["archiveSha256", source.originalSha256],
    ["releaseId", source.releaseId],
    ["sourceRow", source.identifierRecordOrdinal]
  ]) if (Object.hasOwn(provenance.value, key))
    requireThat(provenance.value[key] === expected, "LOCAL_ASSERTION_PROVENANCE_" + key);
  requireThat(object2(input.fields), "LOCAL_ASSERTION_FIELDS_REQUIRED");
  const fields = {};
  for (const name of publicFields) if (Object.hasOwn(input.fields, name)) {
    const field = input.fields[name];
    requireThat(object2(field) && typeof field.state === "string", "LOCAL_ASSERTION_FIELD_ENVELOPE");
    requireThat(!["restricted", "rights-held"].includes(field.state) || field.value == null, "LOCAL_ASSERTION_RESTRICTED_VALUE");
    fields[name] = copy(field);
  }
  const classificationBinding = {
    sourceRecordId: source.identifierNativeRecordId,
    snapshotSha256: source.originalSha256,
    sourceObservationReference: copy(ref),
    inputAssetSha256: source.inputAssetSha256,
    recordSha256: source.recordSha256,
    componentDigests: copy(source.componentDigests)
  };
  let classificationProjection = unresolvedProjection(classificationBinding);
  if (input.classificationProjection) {
    validateClassificationProjection(input.classificationProjection);
    requireThat(
      stable(input.classificationProjection) === stable(expectedClassificationProjection),
      "LOCAL_ASSERTION_CLASSIFICATION_EXPECTED_INPUT"
    );
    requireThat(
      input.classificationProjection.sourceBinding.sourceRecordId === classificationBinding.sourceRecordId && input.classificationProjection.sourceBinding.snapshotSha256 === classificationBinding.snapshotSha256 && stable(input.classificationProjection.sourceBinding.sourceObservationReference) === stable(ref),
      "LOCAL_ASSERTION_CLASSIFICATION_SOURCE_BINDING"
    );
    classificationProjection = copy(input.classificationProjection);
  }
  return bounded2({
    schema: "offmenu-local-source-assertion/1",
    sourceObservationReference: copy(ref),
    binding: Object.fromEntries(bindingKeys.filter((k) => Object.hasOwn(binding, k)).map((k) => [k, copy(binding[k])])),
    fields,
    classificationProjection,
    identity: {
      namespace: "barcode",
      lexicalValue: ref.originalLexicalValue,
      identifierValidation: "valid-exact-GTIN",
      relationship: "separate-attributed-source-assertion",
      productVariantEquivalence: "unresolved"
    },
    sourceState: "upstream-projection; original field presence and numeric lexemes may be unknown",
    nutritionBasisRelationship: "raw source basis and projected profile basis remain separate; applicability unverified",
    imageReferenceMeaning: "Metadata only; no display grant or external image request",
    imageReferenceCapture: Object.hasOwn(fields, "imageUrlReferences") ? "supplied-envelope" : "not-captured-in-selected-input"
  });
}
function selectSourceAssertion(assertions, key) {
  requireThat(
    key?.schema === "offmenu-source-assertion-selection/1" && Array.isArray(assertions),
    "LOCAL_ASSERTION_EXPLICIT_SELECTION_REQUIRED"
  );
  const matches = assertions.filter((a) => stable(a.sourceObservationReference) === stable(key.reference) && stable(a.binding) === stable(key.binding));
  requireThat(matches.length === 1, "LOCAL_ASSERTION_SELECTION_NOT_UNIQUE");
  return matches[0];
}
function makeSourcePhotoSelection(assertions, request, currentOutputUse) {
  const a = selectSourceAssertion(assertions, request?.selectionKey), ref = a.sourceObservationReference, image = request.imageObservation, locator = image?.sourceLocator, asset = request.localAsset;
  requireThat(currentOutputUse?.state === "qualified" && hex(currentOutputUse.runtimeSelectionSha256) && stable(currentOutputUse.useSelectionRef) === stable(request.useSelectionRef), "LOCAL_ASSERTION_PHOTO_CURRENT_USE");
  requireThat(
    locator?.sourceId === ref.sourceId && locator.releaseId === ref.releaseId && locator.originalSha256 === a.binding.sourceBinding.originalSha256 && locator.ordinal === ref.observationKey.record_ordinal && image.photo?.sourceCode === ref.sourceLexicalValue,
    "LOCAL_ASSERTION_PHOTO_NATIVE_BINDING"
  );
  requireThat(
    typeof asset?.path === "string" && /^\/api\/off-photos\/[A-Za-z0-9_-]+\.(?:jpg|jpeg|png|webp)$/.test(asset.path) && hex(asset.sha256) && ["image/jpeg", "image/png", "image/webp"].includes(asset.type) && image.snapshotSeparation?.imageBytesSnapshot?.sha256 === asset.sha256 && hex(image.retrieval?.sha256),
    "LOCAL_ASSERTION_PHOTO_ASSET_BINDING"
  );
  return bounded2({
    schema: "offmenu-source-assertion-photo-selection/1",
    reference: copy(ref),
    detail: { ...copy(a.binding), fields: copy(a.fields), classificationProjection: copy(a.classificationProjection) },
    imageObservation: copy(image),
    useSelectionRef: copy(request.useSelectionRef),
    localAsset: copy(asset),
    currentOutputUse: copy(currentOutputUse)
  });
}
function publishedFields(record) {
  const d = record.data, field = (value, path) => ({
    state: value === void 0 ? "missing" : value === null ? "null" : "present",
    value: value ?? null,
    reasonCode: value === void 0 ? "not-projected-in-selected-public-record" : value === null ? "explicit-projected-null" : null,
    fieldPointer: path,
    evidenceSha256: record.provenance?.sourceDocumentSha256 ?? null,
    valueOrigin: "selected-public-record",
    sourceFieldState: "unknown",
    language: null
  });
  const fields = {};
  for (const [name, key] of Object.entries(fieldsMap)) fields[name] = field(d[key], "/data/" + key);
  for (const name of ["nutrientProfile", "imageUrlReferences"]) if (fields[name].state === "missing")
    fields[name] = { ...fields[name], state: "not-loaded", reasonCode: "representation-not-provided" };
  if (d.name === d.identifiers?.[0]?.value) fields.name = { ...fields.name, state: "null", value: null, reasonCode: "identifier-is-not-product-name" };
  fields.markets = field(record.countries, "/countries");
  fields.sourceProvenance = field(record.provenance, "/provenance");
  for (const [key, value] of Object.entries(d)) if (!Object.hasOwn(fields, key)) fields[key] = field(value, "/data/" + key);
  return fields;
}
function projectPublishedRecord(record, { assertions: sidecar, selection } = {}) {
  requireThat(object2(record?.data) && object2(record.provenance), "PUBLIC_RECORD_REQUIRED");
  const fields = publishedFields(record), sourceAssertions = [];
  let sourceAssertionAvailability = { state: sidecar ? "provided" : "not-supplied", reasonCode: null, returned: 0, globalCoverage: "unknown" };
  if (sidecar !== void 0) try {
    requireThat(
      sidecar?.schema === SOURCE_ASSERTIONS_SCHEMA && object2(selection) && stable(sidecar.publicSelection) === stable(selection) && record.releaseId === selection.releaseId,
      "LOCAL_ASSERTION_READER_SELECTION_MISMATCH"
    );
    requireThat(Array.isArray(sidecar.assertions) && sidecar.assertions.length <= 25, "LOCAL_ASSERTION_COUNT_BOUND");
    for (const assertion of sidecar.assertions) {
      const ref2 = assertion.sourceObservationReference;
      requireThat(
        assertion.schema === "offmenu-local-source-assertion/1" && validSourceObservationReference(ref2, ref2?.originalLexicalValue) && validGTIN(ref2.originalLexicalValue) && record.data.identifiers?.some((id2) => id2.system === "barcode" && id2.value === ref2.originalLexicalValue),
        "LOCAL_ASSERTION_READER_IDENTIFIER_MISMATCH"
      );
      sourceAssertions.push(createSourceAssertion(assertion, {
        expectedReference: ref2,
        expectedBinding: assertion.binding?.sourceBinding,
        expectedClassificationProjection: assertion.classificationProjection
      }));
    }
    sourceAssertionAvailability = {
      ...sourceAssertionAvailability,
      state: sidecar.state === "unavailable" ? "unavailable" : "provided",
      reasonCode: sidecar.reasonCode ?? null,
      returned: sourceAssertions.length
    };
  } catch (error) {
    if (!/^LOCAL_ASSERTION_/.test(error.message)) throw error;
    sourceAssertions.length = 0;
    sourceAssertionAvailability = { ...sourceAssertionAvailability, state: "unavailable", reasonCode: error.message };
  }
  const snapshot = selection?.manifestSha256 || record.provenance.sourceDocumentSha256;
  const classificationProjection = hex(snapshot) ? unresolvedProjection({
    sourceRecordId: record.id,
    snapshotSha256: snapshot,
    sourceObservationReference: null
  }) : null;
  const match = {
    id: record.id,
    name: fields.name.value,
    brand: fields.brand.value,
    ingredientsText: record.data.ingredientsText ?? null,
    provenance: { ...record.provenance, releaseId: record.releaseId ?? null },
    detail: {
      fields,
      sourceBinding: { sourceId: record.provenance.sourceId },
      sourceAssertions,
      classificationProjection,
      sourceAssertionAvailability,
      assurance: "Published source record; additional local assertions are separately attributed, not merged or independently certified."
    },
    publicRecord: record
  };
  const ref = record.sourceObservationReference;
  if (ref && validSourceObservationReference(ref, ref.originalLexicalValue) && ref.sourceId === record.provenance.sourceId && record.data.identifiers?.some((id2) => id2.system === "barcode" && id2.value === ref.originalLexicalValue))
    match.sourceObservationReference = ref;
  if (sourceAssertions.length && sidecar.currentOutputUse?.state === "qualified") {
    match.detail.currentOutputUse = copy(sidecar.currentOutputUse);
    if (sidecar.sourcePhotoSelection) {
      try {
        const photo = sidecar.sourcePhotoSelection;
        const key = {
          schema: "offmenu-source-assertion-selection/1",
          reference: photo.reference,
          binding: Object.fromEntries(bindingKeys.filter((k) => Object.hasOwn(photo.detail || {}, k)).map((k) => [k, photo.detail[k]]))
        };
        const selected3 = selectSourceAssertion(sourceAssertions, key);
        requireThat(stable(photo.currentOutputUse) === stable(sidecar.currentOutputUse) && stable(photo.detail.fields) === stable(selected3.fields), "LOCAL_ASSERTION_PHOTO_READER_BINDING");
        match.detail.sourcePhotoSelection = makeSourcePhotoSelection(sourceAssertions, {
          selectionKey: key,
          imageObservation: photo.imageObservation,
          useSelectionRef: photo.useSelectionRef,
          localAsset: photo.localAsset
        }, sidecar.currentOutputUse);
      } catch (error) {
        if (!/^LOCAL_ASSERTION_/.test(error.message)) throw error;
        match.detail.sourcePhotoSelectionAvailability = { state: "unavailable", reasonCode: error.message };
      }
    } else if (sidecar.sourcePhotoSelectionAvailability)
      match.detail.sourcePhotoSelectionAvailability = copy(sidecar.sourcePhotoSelectionAvailability);
  }
  return bounded2(match);
}
function sourceAssertionReadout(detail, tab2) {
  const rows = [];
  if (detail?.sourceAssertionAvailability?.state === "unavailable") rows.push({
    label: "Additional source facts",
    text: "Unavailable in this response. The published barcode record is still shown; no source absence is established."
  });
  const show = (value) => value == null ? "Unknown" : Array.isArray(value) ? value.length ? value.map(show).join(", ") : "No values in this projection; original presence unknown" : object2(value) ? Object.entries(value).filter(([, v]) => v != null).map(([k, v]) => k + ": " + show(v)).join(" \xB7 ") || "Unknown" : String(value);
  const fieldText = (field) => !field ? "Not captured; original presence unknown" : field.state === "present" ? show(field.value) : field.state === "null" ? "Unknown in this source projection" : field.state === "not-loaded" ? "Not loaded" : field.state === "not-applicable" ? "Not applicable as explicitly supplied by this source" : ["unknown", "unresolved"].includes(field.state) ? "Unresolved in this source projection" : ["restricted", "rights-held"].includes(field.state) ? "Not available for display" : "Not supplied in this projection";
  for (const assertion of detail?.sourceAssertions || []) {
    const ref = assertion.sourceObservationReference, attribution = assertion.fields.sourceProvenance?.value?.attribution || ref.sourceId, prefix = "Separate source \xB7 " + attribution + " \xB7 " + ref.releaseId;
    rows.push({ label: prefix, text: "Same barcode; product variant match is unverified. These facts are shown separately." });
    const classification = assertion.classificationProjection.classification;
    rows.push({ label: prefix + " \xB7 source classification", text: classification.disposition + " \xB7 ingredient applicability: " + classification.ingredientApplicability + " \xB7 scope: " + (classification.idScope || "unresolved") });
    const names = tab2 === "nutrition" ? ["nutritionSourceBasis", "nutrientProfile", "rawNutriments"] : tab2 === "ingredients" ? ["ingredientDeclaration", "sourceAllergenClaims", "sourceTraceClaims"] : tab2 === "source" ? Object.keys(assertion.fields) : ["name", "brand", "markets", "categories", "sourceAllergenClaims", "sourceTraceClaims", "sourceDietaryLabelClaims"];
    for (const name of names) {
      const f = assertion.fields[name];
      if (!f) {
        rows.push({ label: prefix + " \xB7 " + name, text: "Not captured in this selected representation; original presence unknown." });
        continue;
      }
      rows.push({ label: prefix + " \xB7 " + name, text: tab2 === "source" ? JSON.stringify(f) : name === "nutrientProfile" && f.state === "present" ? "Projected profile basis: " + show(f.value?.basis) : fieldText(f) });
      if (name === "nutrientProfile" && f.state === "present") for (const [nutrient, n] of Object.entries(f.value?.nutrients || {}))
        rows.push({ label: prefix + " \xB7 " + nutrient, text: (n.value == null ? "Unknown \xB7 not zero" : show(n.value) + " " + (n.unit || "unit unknown")) + " \xB7 basis: " + show(n.basis) + " \xB7 method: " + show(n.method) });
    }
    if (tab2 === "source") rows.push({ label: prefix + " \xB7 exact source binding", text: JSON.stringify({ sourceObservationReference: ref, binding: assertion.binding }) });
    if (tab2 === "nutrition") rows.push({ label: prefix + " \xB7 basis distinction", text: assertion.nutritionBasisRelationship });
  }
  return rows;
}

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/production-scanner/typed-identifier-contract.mjs
var CONTRACT_VERSION = "offmenu-typed-identifier/1";
var CITATIONS = Object.freeze({
  upce: "https://ref.gs1.org/guidelines/2d-in-retail/1.0.0/",
  jan: "https://www.gs1jp.org/standard/barcode/jan_symbol.html",
  itf14: "https://support.gs1.org/support/solutions/articles/43000734528-what-type-of-gtin-can-be-encoded-in-itf-14-",
  packaging: "https://www.gs1uk.org/knowledge-hub/product-identification/how-do-i-identify-packaging-levels",
  isbnGS1: "https://support.gs1.org/support/solutions/articles/43000734165-how-is-an-isbn-used-in-a-gs1-barcode-",
  isbnAgency: "https://www.isbn-international.org/content/what-isbn/10"
});
var REPRESENTATIONS = Object.freeze([
  "GTIN-8",
  "GTIN-12",
  "GTIN-13",
  "GTIN-14",
  "EAN-8",
  "EAN-13",
  "UPC-A",
  "UPC-E",
  "JAN",
  "JAN-8",
  "JAN-13",
  "ISBN-10",
  "ISBN-13"
]);
var WIDTH = Object.freeze({
  "GTIN-8": 8,
  "EAN-8": 8,
  "GTIN-12": 12,
  "UPC-A": 12,
  "GTIN-13": 13,
  "EAN-13": 13,
  "GTIN-14": 14
});
var CARRIER_HINT = Object.freeze({
  "EAN-8": "EAN-8",
  EAN8: "EAN-8",
  ean_8: "EAN-8",
  "EAN-13": "EAN-13",
  EAN13: "EAN-13",
  ean_13: "EAN-13",
  "UPC-A": "UPC-A",
  UPCA: "UPC-A",
  upc_a: "UPC-A",
  "UPC-E": "UPC-E",
  UPCE: "UPC-E",
  upc_e: "UPC-E",
  "ITF-14": "GTIN-14",
  ITF14: "GTIN-14"
});
var digits = (value) => typeof value === "string" && /^[0-9]+$/.test(value);
function checkDigit(body) {
  let sum = 0;
  for (let i14 = body.length - 1, weight = 3; i14 >= 0; i14--, weight = 4 - weight)
    sum += Number(body[i14]) * weight;
  return String((10 - sum % 10) % 10);
}
function validateGTIN(value) {
  return digits(value) && [8, 12, 13, 14].includes(value.length) && checkDigit(value.slice(0, -1)) === value.at(-1);
}
function validateISBN10(value) {
  if (typeof value !== "string" || !/^[0-9]{9}[0-9X]$/.test(value)) return false;
  let sum = 0;
  for (let i14 = 0; i14 < 10; i14++) sum += (value[i14] === "X" ? 10 : Number(value[i14])) * (10 - i14);
  return sum % 11 === 0;
}
function validateISBN13(value) {
  return typeof value === "string" && /^(978|979)[0-9]{10}$/.test(value) && validateGTIN(value);
}
function expandUPCE(value) {
  if (typeof value !== "string" || !/^[01][0-9]{7}$/.test(value)) return null;
  const [n, a, b, c, d, e, f, k] = value;
  const expanded = f <= "2" ? n + a + b + f + "0000" + c + d + e + k : f === "3" ? n + a + b + c + "00000" + d + e + k : f === "4" ? n + a + b + c + d + "00000" + e + k : n + a + b + c + d + e + "0000" + f + k;
  return validateGTIN(expanded) ? expanded : null;
}
function isbn10To13(value) {
  if (!validateISBN10(value)) return null;
  const body = "978" + value.slice(0, 9);
  return body + checkDigit(body);
}
function isbn13To10(value) {
  if (!validateISBN13(value)) return Object.freeze({ status: "invalid", value: null, allocationStatus: "not-verified" });
  if (value.startsWith("979")) return Object.freeze({ status: "no-equivalent", value: null, allocationStatus: "not-verified" });
  const body = value.slice(3, 12);
  let sum = 0;
  for (let i14 = 0; i14 < 9; i14++) sum += Number(body[i14]) * (10 - i14);
  const k = (11 - sum % 11) % 11;
  return Object.freeze({ status: "converted", value: body + (k === 10 ? "X" : String(k)), allocationStatus: "not-verified" });
}
function janNaming(hint) {
  if (hint === "JAN-8") return Object.freeze({ naming: "JAN-8", representation: "EAN-8", countryOfManufacture: null });
  if (hint === "JAN-13") return Object.freeze({ naming: "JAN-13", representation: "EAN-13", countryOfManufacture: null });
  if (hint === "JAN") return Object.freeze({ naming: "JAN", representation: null, countryOfManufacture: null });
  return null;
}
function representationFromCarrier(carrier) {
  return typeof carrier === "string" && Object.hasOwn(CARRIER_HINT, carrier) ? CARRIER_HINT[carrier] : null;
}
function family(hint) {
  return hint === "UPC-E" ? "UPC-E" : hint === "ISBN-10" ? "ISBN-10" : hint === "ISBN-13" ? 13 : WIDTH[hint] ?? null;
}
function nullableString(value, name) {
  if (value == null) return null;
  if (typeof value !== "string") throw new TypeError(name + " must be a string or null");
  return value;
}
function freezeResult(result) {
  result.labelledEquivalents = Object.freeze(result.labelledEquivalents.map(Object.freeze));
  result.possibleRepresentations = Object.freeze(result.possibleRepresentations.map(Object.freeze));
  return Object.freeze(result);
}
function analyzeIdentifier(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new TypeError("input must be an object");
  if (typeof input.original !== "string" || !input.original.length) throw new TypeError("original must be a nonempty string");
  if (typeof input.namespace !== "string" || !input.namespace.length) throw new TypeError("namespace must be explicit and nonempty");
  const hint = nullableString(input.representationHint, "representationHint");
  const carrier = nullableString(input.observedCarrier, "observedCarrier");
  const naming = janNaming(hint);
  const carrierHint = representationFromCarrier(carrier);
  const effective = naming ? naming.representation : hint ?? carrierHint;
  const result = {
    contractVersion: CONTRACT_VERSION,
    original: input.original,
    namespace: input.namespace,
    sourceLexicalValue: nullableString(input.sourceLexicalValue, "sourceLexicalValue"),
    sourceId: nullableString(input.sourceId, "sourceId"),
    lookupOriginal: input.original,
    lookupContract: "caller-owned",
    requestedHint: hint,
    effectiveHint: effective,
    observedCarrier: carrier,
    hintOrigin: hint !== null ? "explicit" : carrierHint ? "decoder-label" : "none",
    namingRelationship: naming,
    countryOfManufacture: null,
    status: "untyped",
    reason: "explicit-representation-required",
    syntaxValid: null,
    checksumValid: null,
    validatedRepresentation: null,
    comparisonGTIN14: null,
    gtin14LeadingDigit: null,
    packagingRelationship: "not-established",
    labelledEquivalents: [],
    possibleRepresentations: [],
    isbn10Equivalent: null,
    isbn10Availability: "not-applicable",
    allocationStatus: "not-verified",
    catalogueStatus: "not-queried",
    physicalCarrierStatus: carrier === null ? "unobserved" : "caller-label-only",
    productIdentityAsserted: false,
    ingredientClassification: "not-assessed"
  };
  const done = () => freezeResult(result);
  const add = (value, representation, rule) => {
    if (value !== input.original && !result.labelledEquivalents.some((x) => x.value === value && x.representation === representation))
      result.labelledEquivalents.push({ value, representation, rule });
  };
  if (hint !== null && !REPRESENTATIONS.includes(hint)) {
    result.status = "invalid";
    result.reason = "unsupported-representation-hint";
    return done();
  }
  if (hint === "JAN") {
    result.status = "hint-required";
    result.reason = "choose-JAN-8-or-JAN-13-explicitly";
    return done();
  }
  if (effective === null) {
    if (carrier === "ITF" || carrier === "itf") result.reason = "generic-ITF-does-not-declare-GTIN";
    else if (/^[0-9]{8}$/.test(input.original)) {
      result.status = "ambiguous";
      result.reason = "eight-digits-do-not-select-EAN-8-or-UPC-E";
      result.possibleRepresentations = [
        { representation: "EAN-8", checksumCompatible: validateGTIN(input.original) },
        { representation: "UPC-E", checksumCompatible: expandUPCE(input.original) !== null }
      ];
    }
    return done();
  }
  if (hint !== null && carrierHint && family(effective) !== family(carrierHint)) {
    result.status = "conflict";
    result.reason = "explicit-hint-conflicts-with-decoder-label";
    return done();
  }
  let gtin = null;
  if (effective === "ISBN-10") {
    result.syntaxValid = /^[0-9]{9}[0-9X]$/.test(input.original);
    result.checksumValid = result.syntaxValid ? validateISBN10(input.original) : null;
    if (result.checksumValid) {
      gtin = isbn10To13(input.original);
      result.validatedRepresentation = "ISBN-10";
      result.isbn10Equivalent = input.original;
      result.isbn10Availability = "original";
      add(gtin, "ISBN-13", "validated-ISBN-10-to-978-ISBN-13");
    }
  } else if (effective === "ISBN-13") {
    result.syntaxValid = /^(978|979)[0-9]{10}$/.test(input.original);
    result.checksumValid = result.syntaxValid ? validateISBN13(input.original) : null;
    if (result.checksumValid) {
      gtin = input.original;
      result.validatedRepresentation = "ISBN-13";
      const converted = isbn13To10(input.original);
      result.isbn10Availability = converted.status;
      result.isbn10Equivalent = converted.value;
      if (converted.value) add(converted.value, "ISBN-10", "validated-978-ISBN-13-to-ISBN-10");
    }
  } else if (effective === "UPC-E") {
    result.syntaxValid = /^[01][0-9]{7}$/.test(input.original);
    gtin = result.syntaxValid ? expandUPCE(input.original) : null;
    result.checksumValid = result.syntaxValid ? gtin !== null : null;
    if (gtin) {
      result.validatedRepresentation = "UPC-E";
      add(gtin, "GTIN-12", "explicit-UPC-E-to-GTIN-12");
      add("0" + gtin, "EAN-13", "GTIN-12-as-leading-zero-EAN-13");
    }
  } else {
    const width = WIDTH[effective];
    result.syntaxValid = !!width && digits(input.original) && input.original.length === width;
    result.checksumValid = result.syntaxValid ? validateGTIN(input.original) : null;
    if (result.checksumValid) {
      gtin = input.original;
      result.validatedRepresentation = "GTIN-" + width;
      if (width === 12) add("0" + gtin, "EAN-13", "GTIN-12-as-leading-zero-EAN-13");
      if (width === 13 && gtin.startsWith("0")) add(gtin.slice(1), "GTIN-12", "leading-zero-EAN-13-as-GTIN-12");
      if (width === 14) result.gtin14LeadingDigit = gtin[0];
    }
  }
  if (!result.checksumValid) {
    result.status = "invalid";
    result.reason = result.syntaxValid ? "checksum-invalid" : "representation-syntax-invalid";
    return done();
  }
  result.status = "checksum-valid";
  result.reason = "typed-syntax-and-checksum-only";
  result.comparisonGTIN14 = gtin.padStart(14, "0");
  return done();
}

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/production-scanner/scanner-production-lookup.js
var SELECTED_PUBLIC_RELEASE = Object.freeze({ sourceId: "off", releaseId: "offmenu-off-selected-products-20261025-v1", manifestSha256: "1bf09a371a164ebd8215fd9b44a1b2ac9816caaa65cd13504086defad76d4e8f" });
var HEX = /^[a-f0-9]{64}$/;
var RELEASE = /^[-A-Za-z0-9.]{1,128}$/;
var PUBLIC_SOURCE = "off";
var unavailable = (generation2, reasonCode) => ({ generation: generation2, status: "unavailable", matches: [], hasMore: false, nextCursor: null, error: reasonCode });
function selected(selection) {
  return selection && RELEASE.test(selection.releaseId || "") && HEX.test(selection.manifestSha256 || "") && selection.sourceId === PUBLIC_SOURCE;
}
function projected(record, context) {
  return projectPublishedRecord(record, context);
}
function lookupForms(raw, namespace, symbology) {
  if (namespace !== "barcode" || typeof raw !== "string" || !raw.length || raw.length > 128 || symbology !== null && typeof symbology !== "string") return [];
  const typed = analyzeIdentifier({ original: raw, namespace, representationHint: symbology });
  const forms = [{ value: raw, rule: null }, ...typed.status === "checksum-valid" ? typed.labelledEquivalents : []];
  return forms.filter((form, index) => /^\d{4,32}$/.test(form.value) && forms.findIndex((x) => x.value === form.value) === index);
}
var pageStatus = (matches, hasMore) => matches.length ? matches.length > 1 || hasMore ? "ambiguous" : "source-match" : hasMore ? "searching" : "scoped-miss";
function continuation(raw, symbology, selection, index, sourceCursor) {
  return JSON.stringify({ version: 1, raw, symbology, releaseId: selection.releaseId, manifestSha256: selection.manifestSha256, index, sourceCursor });
}
function createPublicLookup({ selection, fetchImpl = fetch } = {}) {
  return async function lookup2(raw, generation2, cursor = null, symbology = null, namespace = "barcode") {
    if (!selected(selection)) return unavailable(generation2, "PUBLIC_RELEASE_NOT_SELECTED");
    const forms = lookupForms(raw, namespace, symbology);
    if (!forms.length) return unavailable(generation2, "UNSUPPORTED_PUBLIC_IDENTIFIER");
    let index = 0, sourceCursor = null;
    if (cursor !== null) {
      try {
        if (typeof cursor !== "string" || cursor.length > 2048) throw Error("cursor");
        const c = JSON.parse(cursor);
        if (c.version !== 1 || c.raw !== raw || c.symbology !== symbology || c.releaseId !== selection.releaseId || c.manifestSha256 !== selection.manifestSha256 || !Number.isSafeInteger(c.index) || c.index < 0 || c.index >= forms.length || c.sourceCursor !== null && (typeof c.sourceCursor !== "string" || !c.sourceCursor.length || c.sourceCursor.length > 600)) throw Error("cursor");
        index = c.index;
        sourceCursor = c.sourceCursor;
      } catch {
        return unavailable(generation2, "PUBLIC_CURSOR_INVALID");
      }
    }
    while (index < forms.length) {
      const form = forms[index];
      const url = new URL("/api/data/public", globalThis.location?.origin || "https://offmenu.invalid");
      for (const [k, v] of Object.entries({ source: PUBLIC_SOURCE, barcode: form.value, releaseId: selection.releaseId, manifestSha256: selection.manifestSha256, kind: "product", limit: "25" })) url.searchParams.set(k, v);
      if (sourceCursor) url.searchParams.set("cursor", sourceCursor);
      try {
        const response = await fetchImpl(url.pathname + url.search, { method: "GET", cache: "no-store", headers: { Accept: "application/json" } });
        if (!response.ok) return unavailable(generation2, response.status === 409 ? "PUBLIC_RELEASE_MISMATCH" : response.status === 400 ? "PUBLIC_QUERY_INVALID" : "PUBLIC_LOOKUP_UNAVAILABLE");
        const body = await response.text();
        if (new TextEncoder().encode(body).byteLength > 262144) return unavailable(generation2, "PUBLIC_RESPONSE_BOUND");
        const data = JSON.parse(body);
        if (data.releaseId !== selection.releaseId || data.manifestSha256 !== selection.manifestSha256 || !Array.isArray(data.records)) return unavailable(generation2, "PUBLIC_RESPONSE_MISMATCH");
        const matches = [];
        for (const record of data.records) {
          if (record?.kind !== "product" || typeof record.id !== "string" || !record.id.length || record.provenance?.sourceId !== PUBLIC_SOURCE || record.provenance?.visibility !== "public" || record.data?.identifiers?.some((id2) => id2.system === "barcode" && id2.value === form.value) !== true) return unavailable(generation2, "PUBLIC_RECORD_BINDING");
          matches.push(projected({ ...record, releaseId: selection.releaseId }, { assertions: data.localSourceAssertions, selection }));
        }
        for (const match of matches) match.matchContext = { originalLexicalValue: raw, sourceLexicalValue: form.value, symbology, matchType: form.value === raw ? "exact" : "representation-alias", equivalence: form.rule };
        if (data.nextCursor !== null && data.nextCursor !== void 0 && typeof data.nextCursor !== "string") return unavailable(generation2, "PUBLIC_CURSOR_INVALID");
        if (data.nextCursor && data.nextCursor.length > 600) return unavailable(generation2, "PUBLIC_CURSOR_INVALID");
        if (!data.nextCursor && !matches.length && index + 1 < forms.length) {
          index++;
          sourceCursor = null;
          continue;
        }
        const nextIndex = data.nextCursor ? index : index + 1;
        const hasMore = nextIndex < forms.length;
        const nextCursor = hasMore ? continuation(raw, symbology, selection, nextIndex, data.nextCursor || null) : null;
        return { generation: generation2, status: pageStatus(matches, hasMore), matches, hasMore, nextCursor, requestCursor: cursor, original: raw, namespace, symbology, releaseId: selection.releaseId, manifestSha256: selection.manifestSha256 };
      } catch {
        return unavailable(generation2, "PUBLIC_LOOKUP_UNAVAILABLE");
      }
    }
  };
}
var lookupIdentifiers = createPublicLookup({ selection: SELECTED_PUBLIC_RELEASE });

// ../offmenu-data/runtime/layout-migration/worker13/qualified-public-inventory-client-composition-20261026/inventory-only-r2/candidate/public/production-scanner/guest-inventory-lookup.mjs
var sha2 = (x) => typeof x === "string" && /^[a-f0-9]{64}$/.test(x);
var stable2 = (x) => Array.isArray(x) ? "[" + x.map(stable2).join(",") + "]" : x && typeof x === "object" ? "{" + Object.keys(x).sort().map((k) => JSON.stringify(k) + ":" + stable2(x[k])).join(",") + "}" : JSON.stringify(x);
var same = (a, b) => stable2(a) === stable2(b);
var unavailable2 = (generation2, error) => ({ generation: generation2, status: "unavailable", matches: [], hasMore: false, nextCursor: null, error });
var CURSOR = "offmenu-qualified-guest-inventory-cursor/2";
var laneId = (s) => "public:" + s.sourceId + ":" + s.releaseId + ":" + s.manifestSha256;
var status = (matches, states, hasMore) => states.some((s) => s.status === "unavailable") ? matches.length ? "partial" : "unavailable" : matches.length > 1 ? "ambiguous" : matches.length ? "source-match" : hasMore ? "searching" : "scoped-miss";
function sourceKey(match) {
  const p = match.lookupOrigin;
  if (!p || typeof match.id !== "string") throw Error("COMPOSITION_SOURCE_REQUIRED");
  return JSON.stringify([p.provider, p.selection, match.id]);
}
function union(previous, next) {
  const result = /* @__PURE__ */ new Map();
  for (const value of [...previous, ...next]) {
    const match = structuredClone(value), key = sourceKey(match), old = result.get(key);
    if (!old) {
      result.set(key, match);
      continue;
    }
    const original = (x) => {
      const c = { ...x };
      delete c.matchContext;
      delete c.lookupContexts;
      return c;
    };
    if (!same(original(old), original(match))) throw Error("QUALIFIED_SOURCE_RECORD_CHANGED");
    old.lookupContexts = [...new Map([...old.lookupContexts ?? [], ...match.lookupContexts ?? []].map((x) => [stable2(x), x])).values()];
  }
  return [...result.values()];
}
function mergeQualifiedGuestPages(previous, next) {
  if (previous.generation !== next.generation || previous.nextCursor !== next.requestCursor || previous.original !== next.original || previous.namespace !== next.namespace || previous.symbology !== next.symbology || !same(previous.selectedInventories, next.selectedInventories)) throw Error("QUALIFIED_COMPOSITION_CHANGED");
  const matches = union(previous.matches ?? [], next.matches ?? []);
  return { ...next, matches, status: status(matches, next.providerStates, next.hasMore) };
}
function createQualifiedGuestLookup({ selections, origin, fetchImpl = globalThis.fetch } = {}) {
  if (!Array.isArray(selections) || !selections.length || selections.some((s) => s?.sourceId !== "off" || typeof s.releaseId !== "string" || !/^[-A-Za-z0-9.]{1,128}$/.test(s.releaseId) || !sha2(s.manifestSha256))) throw Error("EXACT_QUALIFIED_PUBLIC_SELECTION_REQUIRED");
  const selected3 = structuredClone(selections).map(({ sourceId, releaseId, manifestSha256 }) => ({ sourceId, releaseId, manifestSha256 }));
  if (new Set(selected3.map(laneId)).size !== selected3.length) throw Error("DUPLICATE_PUBLIC_SELECTION");
  const base = new URL(origin);
  if (base.origin !== origin || !["http:", "https:"].includes(base.protocol) || globalThis.location?.origin && globalThis.location.origin !== origin || typeof fetchImpl !== "function") throw Error("EXACT_CURRENT_SERVED_ORIGIN_REQUIRED");
  const definitions = selected3.map((selection) => ({ id: laneId(selection), selection }));
  let closed = false, epoch = 0;
  const controllers = /* @__PURE__ */ new Set();
  async function lookupIdentifiers3(raw, generation2, cursor = null, symbology = null, namespace = "barcode") {
    if (closed) return unavailable2(generation2, "GUEST_COMPOSITION_CLOSED");
    if (typeof raw !== "string" || !/^\d{4,32}$/.test(raw) || namespace !== "barcode" || symbology !== null && typeof symbology !== "string") return unavailable2(generation2, "UNSUPPORTED_SELECTED_PUBLIC_IDENTIFIER");
    let lanes = definitions.map((d) => ({ ...d, pending: true, cursor: null, status: "not-requested", error: null }));
    if (cursor !== null) try {
      if (typeof cursor !== "string" || cursor.length > 65536) throw Error();
      const c = JSON.parse(cursor);
      if (c.schema !== CURSOR || c.raw !== raw || c.generation !== generation2 || c.namespace !== namespace || c.symbology !== symbology || !same(c.selections, selected3) || !Array.isArray(c.lanes) || c.lanes.length !== definitions.length) throw Error();
      lanes = c.lanes.map((l, i14) => {
        if (l.id !== definitions[i14].id || typeof l.pending !== "boolean" || l.cursor !== null && typeof l.cursor !== "string" || typeof l.status !== "string") throw Error();
        return { ...definitions[i14], pending: l.pending, cursor: l.cursor, status: l.status, error: l.error ?? null };
      });
    } catch {
      return unavailable2(generation2, "COMPOSITION_CURSOR_MISMATCH");
    }
    const turn = epoch, controller = typeof AbortController === "function" ? new AbortController() : null;
    let timer;
    if (controller) {
      controllers.add(controller);
      timer = setTimeout(() => controller.abort(), 12e3);
    }
    try {
      const results = await Promise.all(lanes.map(async (lane) => {
        if (!lane.pending) return { lane, result: null };
        let httpStatus = null;
        const boundedFetch = async (url, init = {}) => {
          const target = new URL(url, origin);
          if (target.origin !== origin || init.method && init.method !== "GET") throw Error("PUBLIC_ORIGIN_OR_METHOD_CHANGED");
          if (target.pathname !== "/api/data/public" || target.searchParams.get("source") !== lane.selection.sourceId || target.searchParams.get("releaseId") !== lane.selection.releaseId || target.searchParams.get("manifestSha256") !== lane.selection.manifestSha256) throw Error("PUBLIC_SELECTION_CHANGED");
          const response = await fetchImpl(target.href, { ...init, method: "GET", credentials: "omit", cache: "no-store", redirect: "error", mode: "same-origin", ...controller ? { signal: controller.signal } : {} });
          httpStatus = response.status;
          return response;
        };
        const lookup2 = createPublicLookup({ selection: lane.selection, fetchImpl: boundedFetch });
        let result;
        try {
          result = await lookup2(raw, generation2, lane.cursor, symbology, namespace);
        } catch {
          result = unavailable2(generation2, "SELECTED_PUBLIC_SOURCE_UNAVAILABLE");
        }
        const denied = httpStatus === 401 || httpStatus === 403;
        const failed = result.status === "unavailable", pending = failed ? !denied : result.hasMore === true;
        return { lane: { ...lane, status: result.status, error: result.error ?? null, pending, cursor: failed ? lane.cursor : result.nextCursor ?? null, httpStatus }, result };
      }));
      if (closed || turn !== epoch) return unavailable2(generation2, "GUEST_COMPOSITION_CLOSED");
      const matches = [];
      for (const { lane, result } of results) for (const value of result?.matches ?? []) {
        const match = structuredClone(value);
        match.lookupOrigin = { provider: "qualified-public-inventory", selection: structuredClone(lane.selection) };
        match.lookupContexts = match.matchContext ? [structuredClone(match.matchContext)] : [];
        matches.push(match);
      }
      const distinct = union([], matches), states = results.map(({ lane }) => ({ id: lane.id, status: lane.status, error: lane.error ?? null, pending: lane.pending, cursor: lane.cursor, httpStatus: lane.httpStatus ?? null })), hasMore = states.some((s) => s.pending);
      const nextCursor = hasMore ? JSON.stringify({ schema: CURSOR, raw, generation: generation2, namespace, symbology, selections: selected3, lanes: states }) : null;
      if (nextCursor && nextCursor.length > 65536) return unavailable2(generation2, "COMPOSITION_CURSOR_BOUND");
      return { generation: generation2, original: raw, namespace, symbology, requestCursor: cursor, matches: distinct, status: status(distinct, states, hasMore), hasMore, nextCursor, selectedInventories: structuredClone(selected3), providerStates: states.map(({ cursor: cursor2, ...s }) => s), coverage: { scope: "selected-qualified-offmenu-public-inventory-only", servingProvider: "offmenu-normalized-inventory", externalFallback: false, complete: !hasMore && !states.some((s) => s.status === "unavailable"), globalProductTotal: null, identityEquivalence: false } };
    } finally {
      if (timer) clearTimeout(timer);
      if (controller) controllers.delete(controller);
    }
  }
  return Object.freeze({ lookupIdentifiers: lookupIdentifiers3, mergeIdentifierPages: mergeQualifiedGuestPages, destroy() {
    closed = true;
    epoch++;
    for (const c of controllers) c.abort();
    controllers.clear();
  } });
}

// ../offmenu-data/runtime/layout-migration/worker13/qualified-public-inventory-client-composition-20261026/inventory-only-r2/candidate/public/production-scanner/qualified-public-inventory-selection.mjs
var QUALIFIED_PUBLIC_SELECTIONS = Object.freeze([Object.freeze({ sourceId: "off", releaseId: "offmenu-off-selected-products-20261025-v1", manifestSha256: "1bf09a371a164ebd8215fd9b44a1b2ac9816caaa65cd13504086defad76d4e8f" })]);

// ../offmenu-data/runtime/layout-migration/worker19/full-scanner-guest-providers-20261026/candidate/public/production-scanner/guest-scanner-state.mjs
var encoder = new TextEncoder();
var MAX_BYTES = 262144;
var size = (key, value) => encoder.encode(key).length + encoder.encode(value).length;
function createGuestStorage() {
  const values = /* @__PURE__ */ new Map();
  let used = 0;
  return Object.freeze({
    get length() {
      return values.size;
    },
    key(index) {
      return Number.isInteger(index) && index >= 0 ? [...values.keys()][index] ?? null : null;
    },
    getItem(key) {
      key = String(key);
      return values.has(key) ? values.get(key) : null;
    },
    setItem(key, value) {
      key = String(key);
      value = String(value);
      const previous = values.has(key) ? size(key, values.get(key)) : 0, next = used - previous + size(key, value);
      if (next > MAX_BYTES) {
        const error = Error("Demo memory limit reached.");
        error.name = "QuotaExceededError";
        throw error;
      }
      values.set(key, value);
      used = next;
    },
    removeItem(key) {
      key = String(key);
      if (values.has(key)) {
        used -= size(key, values.get(key));
        values.delete(key);
      }
    },
    clear() {
      values.clear();
      used = 0;
    }
  });
}
var guestStorage = createGuestStorage();
function readGuestPrefill() {
  return null;
}
function finishGuestSession(queue2) {
  if (!Array.isArray(queue2)) throw Error("DEMO_QUEUE_REQUIRED");
  return {
    message: "Demo session finished. Your list stays in this tab until you reload.",
    captureCount: queue2.length,
    persisted: false,
    scope: "guest-demo"
  };
}

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/production-scanner/locales/ar.js
var ARABIC = Object.freeze({
  "Offline resource unavailable": "\u0627\u0644\u0645\u0648\u0631\u062F \u063A\u064A\u0631 \u0645\u062A\u0627\u062D \u062F\u0648\u0646 \u0627\u062A\u0635\u0627\u0644",
  "Translation is stale; showing the original source text.": "\u0627\u0644\u062A\u0631\u062C\u0645\u0629 \u0642\u062F\u064A\u0645\u0629\u061B \u064A\u064F\u0639\u0631\u0636 \u0646\u0635 \u0627\u0644\u0645\u0635\u062F\u0631 \u0627\u0644\u0623\u0635\u0644\u064A.",
  "Common corpus graph loaded for local preview. Source identities, citations and quantities are preserved; nothing is saved.": "\u062A\u0645 \u062A\u062D\u0645\u064A\u0644 \u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0645\u062C\u0645\u0648\u0639\u0629 \u0644\u0644\u0645\u0639\u0627\u064A\u0646\u0629 \u0627\u0644\u0645\u062D\u0644\u064A\u0629. \u062A\u0628\u0642\u0649 \u0647\u0648\u064A\u0627\u062A \u0627\u0644\u0645\u0635\u0627\u062F\u0631 \u0648\u0627\u0644\u0627\u0633\u062A\u0634\u0647\u0627\u062F\u0627\u062A \u0648\u0627\u0644\u0643\u0645\u064A\u0627\u062A \u0643\u0645\u0627 \u0647\u064A\u061B \u0644\u0645 \u062A\u064F\u062D\u0641\u0638 \u0623\u064A \u062A\u063A\u064A\u064A\u0631\u0627\u062A.",
  "Return to offmenu": "\u0627\u0644\u0639\u0648\u062F\u0629 \u0625\u0644\u0649 offmenu",
  "Returning to offmenu\u2026": "\u062C\u0627\u0631\u064D \u0627\u0644\u0639\u0648\u062F\u0629 \u0625\u0644\u0649 offmenu\u2026",
  "Open offmenu": "\u0627\u0641\u062A\u062D offmenu",
  "Yes": "\u0646\u0639\u0645",
  "No": "\u0644\u0627",
  "Unknown unit": "\u0648\u062D\u062F\u0629 \u063A\u064A\u0631 \u0645\u0639\u0631\u0648\u0641\u0629",
  "Kitchen inventory": "\u0645\u062E\u0632\u0648\u0646 \u0627\u0644\u0645\u0637\u0628\u062E",
  "Home checkout receipt": "\u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636 \u0627\u0644\u0645\u0646\u0632\u0644",
  "Household menus & recipe booklet": "\u0648\u062C\u0628\u0627\u062A \u0627\u0644\u0623\u0633\u0631\u0629 \u0648\u0643\u062A\u064A\u0651\u0628 \u0627\u0644\u0648\u0635\u0641\u0627\u062A",
  "Meal-plan shopping list": "\u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u062A\u0633\u0648\u0651\u0642 \u0644\u062E\u0637\u0629 \u0627\u0644\u0648\u062C\u0628\u0627\u062A",
  "Household preferences": "\u062A\u0641\u0636\u064A\u0644\u0627\u062A \u0627\u0644\u0623\u0633\u0631\u0629",
  "Food history & nutrition": "\u0633\u062C\u0644 \u0627\u0644\u0637\u0639\u0627\u0645 \u0648\u0627\u0644\u062A\u063A\u0630\u064A\u0629",
  "Waste & freshness report": "\u062A\u0642\u0631\u064A\u0631 \u0627\u0644\u0647\u062F\u0631 \u0648\u062D\u0627\u0644\u0629 \u0627\u0644\u0637\u0639\u0627\u0645",
  "Product": "\u0627\u0644\u0645\u0646\u062A\u062C",
  "Amount": "\u0627\u0644\u0643\u0645\u064A\u0629",
  "Recipe ingredient": "\u0645\u0643\u0648\u0651\u0646 \u0627\u0644\u0648\u0635\u0641\u0629",
  "Expiry": "\u062A\u0627\u0631\u064A\u062E \u0627\u0644\u0627\u0646\u062A\u0647\u0627\u0621",
  "Directions": "\u0627\u0644\u0637\u0631\u064A\u0642\u0629",
  "Contents": "\u0627\u0644\u0645\u062D\u062A\u0648\u064A\u0627\u062A",
  "Recipes indexed: {count}": {
    zero: "\u0644\u0627 \u0648\u0635\u0641\u0627\u062A \u0645\u0641\u0647\u0631\u0633\u0629 ({count})",
    one: "\u0648\u0635\u0641\u0629 \u0648\u0627\u062D\u062F\u0629 \u0645\u0641\u0647\u0631\u0633\u0629 ({count})",
    two: "\u0648\u0635\u0641\u062A\u0627\u0646 \u0645\u0641\u0647\u0631\u0633\u062A\u0627\u0646 ({count})",
    few: "{count} \u0648\u0635\u0641\u0627\u062A \u0645\u0641\u0647\u0631\u0633\u0629",
    many: "{count} \u0648\u0635\u0641\u0629 \u0645\u0641\u0647\u0631\u0633\u0629",
    other: "\u0648\u0635\u0641\u0627\u062A \u0645\u0641\u0647\u0631\u0633\u0629: {count}"
  },
  "Translation unavailable; showing the original source text.": "\u0627\u0644\u062A\u0631\u062C\u0645\u0629 \u063A\u064A\u0631 \u0645\u062A\u0627\u062D\u0629\u061B \u064A\u064F\u0639\u0631\u0636 \u0646\u0635 \u0627\u0644\u0645\u0635\u062F\u0631 \u0627\u0644\u0623\u0635\u0644\u064A.",
  "Same as interface language": "\u0645\u062B\u0644 \u0644\u063A\u0629 \u0627\u0644\u0648\u0627\u062C\u0647\u0629",
  "Arabic when supplied": "\u0627\u0644\u0639\u0631\u0628\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627",
  "Japanese when supplied": "\u0627\u0644\u064A\u0627\u0628\u0627\u0646\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627",
  "English when supplied": "\u0627\u0644\u0625\u0646\u062C\u0644\u064A\u0632\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627",
  "French when supplied": "\u0627\u0644\u0641\u0631\u0646\u0633\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627",
  "German when supplied": "\u0627\u0644\u0623\u0644\u0645\u0627\u0646\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627",
  "Chinese when supplied": "\u0627\u0644\u0635\u064A\u0646\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627",
  "Hindi when supplied": "\u0627\u0644\u0647\u0646\u062F\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627",
  "Indonesian when supplied": "\u0627\u0644\u0625\u0646\u062F\u0648\u0646\u064A\u0633\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627",
  "Russian when supplied": "\u0627\u0644\u0631\u0648\u0633\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627",
  "Original source language": "\u0644\u063A\u0629 \u0627\u0644\u0645\u0635\u062F\u0631 \u0627\u0644\u0623\u0635\u0644\u064A\u0629",
  "Food-name display language": "\u0644\u063A\u0629 \u0639\u0631\u0636 \u0623\u0633\u0645\u0627\u0621 \u0627\u0644\u0623\u0637\u0639\u0645\u0629",
  "All languages": "\u062C\u0645\u064A\u0639 \u0627\u0644\u0644\u063A\u0627\u062A",
  "Recipe language": "\u0644\u063A\u0629 \u0627\u0644\u0648\u0635\u0641\u0629",
  "RECIPES FROM AROUND THE WORLD": "\u0648\u0635\u0641\u0627\u062A \u0645\u0646 \u0623\u0646\u062D\u0627\u0621 \u0627\u0644\u0639\u0627\u0644\u0645",
  "Explore the shared recipe library.": "\u0627\u0633\u062A\u0643\u0634\u0641 \u0645\u0643\u062A\u0628\u0629 \u0627\u0644\u0648\u0635\u0641\u0627\u062A \u0627\u0644\u0645\u0634\u062A\u0631\u0643\u0629.",
  "Open worldwide recipes": "\u0627\u0641\u062A\u062D \u0648\u0635\u0641\u0627\u062A \u0627\u0644\u0639\u0627\u0644\u0645",
  "Dish or ingredients": "\u0627\u0644\u0637\u0628\u0642 \u0623\u0648 \u0627\u0644\u0645\u0643\u0648\u0651\u0646\u0627\u062A",
  "Original source": "\u0627\u0644\u0645\u0635\u062F\u0631 \u0627\u0644\u0623\u0635\u0644\u064A",
  "Prioritise recipes using my available ingredients": "\u0623\u0639\u0637\u0650 \u0627\u0644\u0623\u0648\u0644\u0648\u064A\u0629 \u0644\u0644\u0648\u0635\u0641\u0627\u062A \u0627\u0644\u062A\u064A \u062A\u0633\u062A\u062E\u062F\u0645 \u0645\u0643\u0648\u0651\u0646\u0627\u062A\u064A \u0627\u0644\u0645\u062A\u0627\u062D\u0629",
  "Shared recipes are available to everyone. Your pantry matching runs on this device.": "\u0627\u0644\u0648\u0635\u0641\u0627\u062A \u0627\u0644\u0645\u0634\u062A\u0631\u0643\u0629 \u0645\u062A\u0627\u062D\u0629 \u0644\u0644\u062C\u0645\u064A\u0639. \u062A\u064F\u0637\u0627\u0628\u064E\u0642 \u0645\u0639 \u0645\u062E\u0632\u0648\u0646\u0643 \u0639\u0644\u0649 \u0647\u0630\u0627 \u0627\u0644\u062C\u0647\u0627\u0632.",
  "A little room for possibility.": "\u0645\u0633\u0627\u062D\u0629 \u0635\u063A\u064A\u0631\u0629 \u0644\u0623\u0641\u0643\u0627\u0631 \u062C\u062F\u064A\u062F\u0629.",
  "Choose a shelf and scan your first items through checkout.": "\u0627\u062E\u062A\u0631 \u0631\u0641\u064B\u0627 \u0648\u0627\u0645\u0633\u062D \u0623\u0635\u0646\u0627\u0641\u0643 \u0627\u0644\u0623\u0648\u0644\u0649 \u0644\u0625\u0636\u0627\u0641\u062A\u0647\u0627 \u0625\u0644\u0649 \u0627\u0644\u0642\u0627\u0626\u0645\u0629.",
  "offmenu \xB7 A little checkout. A better stocked home.": "offmenu \xB7 \u0642\u0627\u0626\u0645\u0629 \u0628\u0633\u064A\u0637\u0629. \u0648\u0645\u062E\u0632\u0648\u0646 \u0645\u0646\u0632\u0644\u064A \u0623\u0641\u0636\u0644.",
  "Pantry, fridge or freezer. One satisfying": "\u062E\u0632\u0627\u0646\u0629 \u0627\u0644\u0637\u0639\u0627\u0645 \u0623\u0648 \u0627\u0644\u062B\u0644\u0627\u062C\u0629 \u0623\u0648 \u0627\u0644\u0645\u062C\u0645\u0651\u062F. \u062A\u0646\u0628\u064A\u0647",
  "beep": "\u0644\u0637\u064A\u0641",
  "at a time.": "\u0645\u0639 \u0643\u0644 \u0635\u0646\u0641.",
  "THE HOME CHECKOUT CLUB": "\u0646\u0627\u062F\u064A \u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636 \u0627\u0644\u0645\u0646\u0632\u0644",
  "EST. RIGHT NOW": "\u0627\u0628\u062F\u0623 \u0627\u0644\u0622\u0646",
  "Oh, so that\u2019s what\u2019s": "\u0625\u0630\u064B\u0627 \u0647\u0630\u0627 \u0645\u0627 \u0643\u0627\u0646",
  "at the back of the shelf.": "\u0641\u064A \u0622\u062E\u0631 \u0627\u0644\u0631\u0641.",
  "HELLO, KITCHEN.": "\u0645\u0631\u062D\u0628\u064B\u0627 \u064A\u0627 \u0645\u0637\u0628\u062E.",
  "3 items \xB7 endless possibilities": "\u0663 \u0623\u0635\u0646\u0627\u0641 \xB7 \u0623\u0641\u0643\u0627\u0631 \u0644\u0627 \u062D\u0635\u0631 \u0644\u0647\u0627",
  "THE GOOD": "\u0627\u0644\u0637\u0639\u0627\u0645",
  "STUFF": "\u0627\u0644\u062C\u064A\u0651\u062F",
  "YOUR KITCHEN": "\u0645\u0637\u0628\u062E\u0643",
  "A little inspiration": "\u0642\u0644\u064A\u0644 \u0645\u0646 \u0627\u0644\u0625\u0644\u0647\u0627\u0645",
  "ALREADY YOURS \u2713": "\u0644\u062F\u064A\u0643 \u0628\u0627\u0644\u0641\u0639\u0644 \u2713",
  "\u25CE See what\u2019s hiding": "\u25CE \u0627\u0643\u062A\u0634\u0641 \u0645\u0627 \u0644\u062F\u064A\u0643",
  "\u25A5 Make space for good food": "\u25A5 \u062E\u0635\u0651\u0635 \u0645\u0633\u0627\u062D\u0629 \u0644\u0644\u0637\u0639\u0627\u0645 \u0627\u0644\u062C\u064A\u0651\u062F",
  "\u2733 Find your next meal": "\u2733 \u0627\u062E\u062A\u0631 \u0648\u062C\u0628\u062A\u0643 \u0627\u0644\u062A\u0627\u0644\u064A\u0629",
  "A little more play. A little less \u201Cwhat\u2019s for dinner?\u201D": "\u0645\u062A\u0639\u0629 \u0623\u0643\u062B\u0631 \u0648\u062D\u064A\u0631\u0629 \u0623\u0642\u0644 \u0628\u0634\u0623\u0646 \u0627\u0644\u0639\u0634\u0627\u0621.",
  "Illustration of the offmenu home checkout": "\u0631\u0633\u0645 \u062A\u0648\u0636\u064A\u062D\u064A \u0644\u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636 \u0627\u0644\u0645\u0646\u0632\u0644 \u0641\u064A offmenu",
  "Turn shelf-by-shelf inventory into a little checkout ritual. Scan your pantry, fridge and freezer, then discover what to cook.": "\u062D\u0648\u0651\u0644 \u062C\u0631\u062F \u0627\u0644\u0631\u0641\u0648\u0641 \u0625\u0644\u0649 \u0639\u0627\u062F\u0629 \u0628\u0633\u064A\u0637\u0629. \u0627\u0645\u0633\u062D \u062E\u0632\u0627\u0646\u0629 \u0627\u0644\u0637\u0639\u0627\u0645 \u0648\u0627\u0644\u062B\u0644\u0627\u062C\u0629 \u0648\u0627\u0644\u0645\u062C\u0645\u0651\u062F\u060C \u062B\u0645 \u0627\u0643\u062A\u0634\u0641 \u0645\u0627 \u064A\u0645\u0643\u0646\u0643 \u0637\u0647\u064A\u0647.",
  "Interface language": "\u0644\u063A\u0629 \u0627\u0644\u0648\u0627\u062C\u0647\u0629",
  "Interface language is saved on this device. Recipes and food names keep their source language.": "\u062A\u064F\u062D\u0641\u0638 \u0644\u063A\u0629 \u0627\u0644\u0648\u0627\u062C\u0647\u0629 \u0639\u0644\u0649 \u0647\u0630\u0627 \u0627\u0644\u062C\u0647\u0627\u0632. \u062A\u062D\u062A\u0641\u0638 \u0627\u0644\u0648\u0635\u0641\u0627\u062A \u0648\u0623\u0633\u0645\u0627\u0621 \u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0628\u0644\u063A\u062A\u0647\u0627 \u0627\u0644\u0623\u0635\u0644\u064A\u0629.",
  "Skip to kitchen": "\u0627\u0646\u062A\u0642\u0644 \u0625\u0644\u0649 \u0627\u0644\u0645\u0637\u0628\u062E",
  "Global data": "\u0627\u0644\u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0639\u0627\u0644\u0645\u064A\u0629",
  "How it works": "\u0643\u064A\u0641 \u064A\u0639\u0645\u0644",
  "Log in": "\u062A\u0633\u062C\u064A\u0644 \u0627\u0644\u062F\u062E\u0648\u0644",
  "My kitchen \u2197": "\u0645\u0637\u0628\u062E\u064A \u2197",
  "YOUR KITCHEN. YOUR CHECKOUT.": "\u0645\u0637\u0628\u062E\u0643. \u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636\u0643.",
  "Dinner starts": "\u064A\u0628\u062F\u0623 \u0627\u0644\u0639\u0634\u0627\u0621",
  "with what you": "\u0628\u0645\u0627 \u0644\u062F\u064A\u0643",
  "already have.": "\u0628\u0627\u0644\u0641\u0639\u0644.",
  "Scan a few foods, find meals that fit your household, and buy only what\u2019s missing. Start with five foods or one shelf.": "\u0627\u0645\u0633\u062D \u0628\u0639\u0636 \u0627\u0644\u0623\u0637\u0639\u0645\u0629\u060C \u0648\u0627\u0639\u062B\u0631 \u0639\u0644\u0649 \u0648\u062C\u0628\u0627\u062A \u062A\u0646\u0627\u0633\u0628 \u0623\u0633\u0631\u062A\u0643\u060C \u0648\u0627\u0634\u062A\u0631\u0650 \u0645\u0627 \u064A\u0646\u0642\u0635\u0643 \u0641\u0642\u0637. \u0627\u0628\u062F\u0623 \u0628\u062E\u0645\u0633\u0629 \u0623\u0635\u0646\u0627\u0641 \u0623\u0648 \u0631\u0641 \u0648\u0627\u062D\u062F.",
  "Add my first food": "\u0623\u0636\u0641 \u0623\u0648\u0644 \u0637\u0639\u0627\u0645",
  "Try a kitchen": "\u062C\u0631\u0651\u0628 \u0645\u0637\u0628\u062E\u064B\u0627",
  "A SMALL RITUAL. A FRESH START.": "\u0639\u0627\u062F\u0629 \u0628\u0633\u064A\u0637\u0629. \u0628\u062F\u0627\u064A\u0629 \u062C\u062F\u064A\u062F\u0629.",
  "Give your kitchen": "\u0627\u0645\u0646\u062D \u0645\u0637\u0628\u062E\u0643",
  "a little shelf respect.": "\u0628\u0639\u0636 \u0627\u0644\u0639\u0646\u0627\u064A\u0629 \u0628\u0631\u0641\u0648\u0641\u0647.",
  "No whole-house marathon required.": "\u0644\u0627 \u062A\u062D\u062A\u0627\u062C \u0625\u0644\u0649 \u062A\u0631\u062A\u064A\u0628 \u0627\u0644\u0645\u0646\u0632\u0644 \u0643\u0644\u0647.",
  "Just one shelf and a clear bit of bench.": "\u064A\u0643\u0641\u064A \u0631\u0641 \u0648\u0627\u062D\u062F \u0648\u0645\u0633\u0627\u062D\u0629 \u062E\u0627\u0644\u064A\u0629 \u0639\u0644\u0649 \u0627\u0644\u0637\u0627\u0648\u0644\u0629.",
  "Clear a shelf.": "\u0623\u0641\u0631\u063A \u0631\u0641\u064B\u0627.",
  "Pick your pantry, fridge or freezer. Put its contents on the bench so you can see what\u2019s there.": "\u0627\u062E\u062A\u0631 \u062E\u0632\u0627\u0646\u0629 \u0627\u0644\u0637\u0639\u0627\u0645 \u0623\u0648 \u0627\u0644\u062B\u0644\u0627\u062C\u0629 \u0623\u0648 \u0627\u0644\u0645\u062C\u0645\u0651\u062F. \u0636\u0639 \u0645\u062D\u062A\u0648\u064A\u0627\u062A\u0647 \u0639\u0644\u0649 \u0627\u0644\u0637\u0627\u0648\u0644\u0629 \u0644\u062A\u0631\u0649 \u0645\u0627 \u0644\u062F\u064A\u0643.",
  "Play shopkeeper.": "\u0627\u0645\u0633\u062D \u0623\u063A\u0631\u0627\u0636\u0643.",
  "Scan each item straight onto your receipt. Glance at nutrition and enjoy the beep. Review it all at the end.": "\u0627\u0645\u0633\u062D \u0643\u0644 \u0635\u0646\u0641 \u0644\u0625\u0636\u0627\u0641\u062A\u0647 \u0625\u0644\u0649 \u0642\u0627\u0626\u0645\u062A\u0643. \u0627\u0637\u0651\u0644\u0639 \u0639\u0644\u0649 \u0628\u064A\u0627\u0646\u0627\u062A\u0647 \u0627\u0644\u063A\u0630\u0627\u0626\u064A\u0629 \u062B\u0645 \u0631\u0627\u062C\u0639 \u0627\u0644\u0642\u0627\u0626\u0645\u0629 \u0641\u064A \u0627\u0644\u0646\u0647\u0627\u064A\u0629.",
  "Put the good stuff back.": "\u0623\u0639\u062F \u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0625\u0644\u0649 \u0645\u0643\u0627\u0646\u0647\u0627.",
  "Review your receipt, update that shelf, then find a meal that starts with what you have.": "\u0631\u0627\u062C\u0639 \u0642\u0627\u0626\u0645\u062A\u0643 \u0648\u062D\u062F\u0651\u062B \u0627\u0644\u0631\u0641\u060C \u062B\u0645 \u0627\u062E\u062A\u0631 \u0648\u062C\u0628\u0629 \u0645\u0646 \u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0627\u0644\u0645\u0648\u062C\u0648\u062F\u0629 \u0644\u062F\u064A\u0643.",
  "FRESH FROM THE SHOP": "\u0645\u0646 \u0627\u0644\u0645\u062A\u062C\u0631 \u0625\u0644\u0649 \u0645\u0637\u0628\u062E\u0643",
  "Shopping bags in.": "\u0623\u062D\u0636\u0631\u062A \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A.",
  "Kitchen sorted.": "\u0648\u0627\u0644\u0622\u0646 \u0631\u062A\u0651\u0628 \u0627\u0644\u0645\u0637\u0628\u062E.",
  "Give new groceries the same checkout treatment before putting them away. Add to your shelves as you unpack.": "\u0627\u0645\u0633\u062D \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A \u0627\u0644\u062C\u062F\u064A\u062F\u0629 \u0642\u0628\u0644 \u062A\u062E\u0632\u064A\u0646\u0647\u0627\u060C \u0648\u0623\u0636\u0641\u0647\u0627 \u0625\u0644\u0649 \u0631\u0641\u0648\u0641\u0643 \u0623\u062B\u0646\u0627\u0621 \u062A\u0641\u0631\u064A\u063A \u0627\u0644\u0623\u0643\u064A\u0627\u0633.",
  "Try an unpacking run \u2197": "\u062C\u0631\u0651\u0628 \u0625\u0636\u0627\u0641\u0629 \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A \u2197",
  "Product information from Open Food Facts. Always check the package for allergens.": "\u0645\u0639\u0644\u0648\u0645\u0627\u062A \u0627\u0644\u0645\u0646\u062A\u062C\u0627\u062A \u0645\u0646 Open Food Facts. \u062A\u062D\u0642\u0651\u0642 \u062F\u0627\u0626\u0645\u064B\u0627 \u0645\u0646 \u0627\u0644\u0639\u0628\u0648\u0629 \u0644\u0645\u0639\u0631\u0641\u0629 \u0645\u0633\u0628\u0651\u0628\u0627\u062A \u0627\u0644\u062D\u0633\u0627\u0633\u064A\u0629.",
  "YOUR HOME CHECKOUT": "\u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636 \u0645\u0637\u0628\u062E\u0643",
  "Let\u2019s take stock.": "\u0644\u0646\u0631\u0627\u062C\u0639 \u0645\u0627 \u0644\u062F\u064A\u0646\u0627.",
  "DEMO \xB7 SAMPLE PRODUCTS": "\u062A\u062C\u0631\u0628\u0629 \xB7 \u0645\u0646\u062A\u062C\u0627\u062A \u0646\u0645\u0648\u0630\u062C\u064A\u0629",
  "\u266A Sound off": "\u266A \u0627\u0644\u0635\u0648\u062A \u0645\u062A\u0648\u0642\u0641",
  "\u266A Sound on": "\u266A \u0627\u0644\u0635\u0648\u062A \u0645\u0641\u0639\u0651\u0644",
  "Scan feedback \u2733": "\u062A\u0646\u0628\u064A\u0647\u0627\u062A \u0627\u0644\u0645\u0633\u062D \u2733",
  "Profile & backup": "\u0627\u0644\u0645\u0644\u0641 \u0627\u0644\u0634\u062E\u0635\u064A \u0648\u0627\u0644\u0646\u0633\u062E \u0627\u0644\u0627\u062D\u062A\u064A\u0627\u0637\u064A",
  "Exit demo": "\u0625\u0646\u0647\u0627\u0621 \u0627\u0644\u062A\u062C\u0631\u0628\u0629",
  "\u2733 Today": "\u2733 \u0627\u0644\u064A\u0648\u0645",
  "\u25A4 Kitchen": "\u25A4 \u0627\u0644\u0645\u0637\u0628\u062E",
  "\u25A6 Plan": "\u25A6 \u0627\u0644\u062E\u0637\u0629",
  "\u25C7 Shop": "\u25C7 \u0627\u0644\u062A\u0633\u0648\u0651\u0642",
  "\u2667 Me": "\u2667 \u062D\u0633\u0627\u0628\u064A",
  "\u25A5 Scan groceries": "\u25A5 \u0627\u0645\u0633\u062D \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A",
  "+ Add food": "+ \u0623\u0636\u0641 \u0637\u0639\u0627\u0645\u064B\u0627",
  "Saved on this device": "\u0645\u062D\u0641\u0648\u0638 \u0639\u0644\u0649 \u0647\u0630\u0627 \u0627\u0644\u062C\u0647\u0627\u0632",
  "YOUR KITCHEN, YOUR WAY": "\u0645\u0637\u0628\u062E\u0643 \u0643\u0645\u0627 \u062A\u062D\u0628",
  "People, preferences & progress.": "\u0627\u0644\u0623\u0634\u062E\u0627\u0635 \u0648\u0627\u0644\u062A\u0641\u0636\u064A\u0644\u0627\u062A \u0648\u0627\u0644\u062A\u0642\u062F\u0651\u0645.",
  "\u2667 Dietary profiles": "\u2667 \u0627\u0644\u0645\u0644\u0641\u0627\u062A \u0627\u0644\u063A\u0630\u0627\u0626\u064A\u0629",
  "\u25F7 Statistics & history": "\u25F7 \u0627\u0644\u0625\u062D\u0635\u0627\u0621\u0627\u062A \u0648\u0627\u0644\u0633\u062C\u0644",
  "\u25A4 Printable documents & Kindle": "\u25A4 \u0645\u0633\u062A\u0646\u062F\u0627\u062A \u0644\u0644\u0637\u0628\u0627\u0639\u0629 \u0648Kindle",
  "Account & backup": "\u0627\u0644\u062D\u0633\u0627\u0628 \u0648\u0627\u0644\u0646\u0633\u062E \u0627\u0644\u0627\u062D\u062A\u064A\u0627\u0637\u064A",
  "Connections & developers": "\u0627\u0644\u0627\u062A\u0635\u0627\u0644\u0627\u062A \u0648\u0627\u0644\u0645\u0637\u0648\u0651\u0631\u0648\u0646",
  "Large text": "\u0646\u0635 \u0643\u0628\u064A\u0631",
  "Quiet mode \xB7 disable scan effects": "\u0627\u0644\u0648\u0636\u0639 \u0627\u0644\u0647\u0627\u062F\u0626 \xB7 \u062A\u0639\u0637\u064A\u0644 \u0645\u0624\u062B\u0631\u0627\u062A \u0627\u0644\u0645\u0633\u062D",
  "People sharing this kitchen": "\u0627\u0644\u0623\u0634\u062E\u0627\u0635 \u0627\u0644\u0645\u0634\u0627\u0631\u0643\u0648\u0646 \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u0637\u0628\u062E",
  "Trust, privacy & support": "\u0627\u0644\u062B\u0642\u0629 \u0648\u0627\u0644\u062E\u0635\u0648\u0635\u064A\u0629 \u0648\u0627\u0644\u062F\u0639\u0645",
  "Clear this device\u2019s account data": "\u0627\u0645\u0633\u062D \u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u062D\u0633\u0627\u0628 \u0645\u0646 \u0647\u0630\u0627 \u0627\u0644\u062C\u0647\u0627\u0632",
  "PICK YOUR NEXT LITTLE WIN": "\u0627\u062E\u062A\u0631 \u062E\u0637\u0648\u062A\u0643 \u0627\u0644\u062A\u0627\u0644\u064A\u0629",
  "What\u2019s on the bench?": "\u0645\u0627\u0630\u0627 \u0639\u0644\u0649 \u0627\u0644\u0637\u0627\u0648\u0644\u0629\u061F",
  "\u25A4 Rebuild a shelf": "\u25A4 \u0631\u062A\u0651\u0628 \u0631\u0641\u064B\u0627",
  "\u2672 Garbage scan": "\u2672 \u0627\u0645\u0633\u062D \u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0644\u0644\u062A\u062E\u0644\u0651\u0635 \u0645\u0646\u0647\u0627",
  "\u{1F6CD} Unpack shopping": "\u{1F6CD} \u0623\u0636\u0641 \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A",
  "Pantry": "\u062E\u0632\u0627\u0646\u0629 \u0627\u0644\u0637\u0639\u0627\u0645",
  "Fridge": "\u0627\u0644\u062B\u0644\u0627\u062C\u0629",
  "Freezer": "\u0627\u0644\u0645\u062C\u0645\u0651\u062F",
  "Dry goods & everyday staples": "\u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0627\u0644\u062C\u0627\u0641\u0629 \u0648\u0627\u0644\u0645\u0648\u0627\u062F \u0627\u0644\u0623\u0633\u0627\u0633\u064A\u0629",
  "Fresh things & leftovers": "\u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0627\u0644\u0637\u0627\u0632\u062C\u0629 \u0648\u0628\u0642\u0627\u064A\u0627 \u0627\u0644\u0648\u062C\u0628\u0627\u062A",
  "Future-you\u2019s favourite food": "\u0623\u0637\u0639\u0645\u0629 \u0645\u062D\u0641\u0648\u0638\u0629 \u0644\u0644\u0623\u064A\u0627\u0645 \u0627\u0644\u0642\u0627\u062F\u0645\u0629",
  "Storage area": "\u0645\u0643\u0627\u0646 \u0627\u0644\u062A\u062E\u0632\u064A\u0646",
  "Shelf / container": "\u0627\u0644\u0631\u0641 \u0623\u0648 \u0627\u0644\u062D\u0627\u0648\u064A\u0629",
  "e.g. Bench": "\u0645\u062B\u0644: \u0627\u0644\u0637\u0627\u0648\u0644\u0629",
  "e.g. Top shelf": "\u0645\u062B\u0644: \u0627\u0644\u0631\u0641 \u0627\u0644\u0639\u0644\u0648\u064A",
  "Clear this shelf onto your bench. Its current inventory stays intact until you review and finish.": "\u0623\u0641\u0631\u063A \u0645\u062D\u062A\u0648\u064A\u0627\u062A \u0647\u0630\u0627 \u0627\u0644\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0637\u0627\u0648\u0644\u0629. \u0644\u0646 \u064A\u062A\u063A\u064A\u0651\u0631 \u0645\u062E\u0632\u0648\u0646\u0647 \u062D\u062A\u0649 \u062A\u0631\u0627\u062C\u0639 \u0627\u0644\u0642\u0627\u0626\u0645\u0629 \u0648\u062A\u0646\u0647\u064A \u0627\u0644\u0639\u0645\u0644\u064A\u0629.",
  "Choose the source location. Scan items you are discarding; review the removal receipt before the inventory changes.": "\u0627\u062E\u062A\u0631 \u0645\u0643\u0627\u0646 \u0627\u0644\u062A\u062E\u0632\u064A\u0646. \u0627\u0645\u0633\u062D \u0627\u0644\u0623\u0635\u0646\u0627\u0641 \u0627\u0644\u062A\u064A \u0633\u062A\u062A\u062E\u0644\u0651\u0635 \u0645\u0646\u0647\u0627\u060C \u0648\u0631\u0627\u062C\u0639 \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0625\u0632\u0627\u0644\u0629 \u0642\u0628\u0644 \u062A\u063A\u064A\u064A\u0631 \u0627\u0644\u0645\u062E\u0632\u0648\u0646.",
  "Choose where these groceries will go. Scan one destination at a time, then add them to the items already there.": "\u0627\u062E\u062A\u0631 \u0645\u0643\u0627\u0646 \u0647\u0630\u0647 \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A. \u0627\u0645\u0633\u062D \u0627\u0644\u0623\u0635\u0646\u0627\u0641 \u0644\u0643\u0644 \u0645\u0643\u0627\u0646 \u0639\u0644\u0649 \u062D\u062F\u0629\u060C \u062B\u0645 \u0623\u0636\u0641\u0647\u0627 \u0625\u0644\u0649 \u0627\u0644\u0645\u0648\u062C\u0648\u062F \u0641\u064A\u0647.",
  "Open my checkout \u2197": "\u0627\u0628\u062F\u0623 \u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636\u064A \u2197",
  "SHELF RESET": "\u0625\u0639\u0627\u062F\u0629 \u062A\u0631\u062A\u064A\u0628 \u0627\u0644\u0631\u0641",
  "GARBAGE \xB7 SOURCE LOCATION": "\u0627\u0644\u062A\u062E\u0644\u0651\u0635 \u0645\u0646 \u0627\u0644\u0637\u0639\u0627\u0645 \xB7 \u0645\u0643\u0627\u0646 \u0627\u0644\u062A\u062E\u0632\u064A\u0646",
  "GROCERY UNPACKING": "\u0625\u0636\u0627\u0641\u0629 \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A",
  "Scan, check, then put it back.": "\u0627\u0645\u0633\u062D \u0648\u062A\u062D\u0642\u0651\u0642 \u062B\u0645 \u0623\u0639\u062F\u0647 \u0625\u0644\u0649 \u0645\u0643\u0627\u0646\u0647.",
  "Pause & choose another shelf": "\u062A\u0648\u0642\u0651\u0641 \u0648\u0627\u062E\u062A\u0631 \u0631\u0641\u064B\u0627 \u0622\u062E\u0631",
  "CHECKOUT OPEN": "\u0627\u0644\u0642\u0627\u0626\u0645\u0629 \u0645\u0641\u062A\u0648\u062D\u0629",
  "Next item, please.": "\u0627\u0644\u0635\u0646\u0641 \u0627\u0644\u062A\u0627\u0644\u064A\u060C \u0645\u0646 \u0641\u0636\u0644\u0643.",
  "Your bench \u2192 your shelf": "\u0645\u0646 \u0627\u0644\u0637\u0627\u0648\u0644\u0629 \u2190 \u0625\u0644\u0649 \u0627\u0644\u0631\u0641",
  "ITEMS": "\u0623\u0635\u0646\u0627\u0641",
  "THE SCANNING SPOT": "\u0645\u0646\u0637\u0642\u0629 \u0627\u0644\u0645\u0633\u062D",
  "Bring on the beeps.": "\u0644\u0646\u0628\u062F\u0623 \u0627\u0644\u0645\u0633\u062D.",
  "Scan next demo item \u25A5": "\u0627\u0645\u0633\u062D \u0627\u0644\u0635\u0646\u0641 \u0627\u0644\u062A\u062C\u0631\u064A\u0628\u064A \u0627\u0644\u062A\u0627\u0644\u064A \u25A5",
  "How are you scanning?": "\u0643\u064A\u0641 \u062A\u0631\u064A\u062F \u0627\u0644\u0645\u0633\u062D\u061F",
  "Handheld \xB7 rear camera": "\u0628\u0627\u0644\u064A\u062F \xB7 \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u062E\u0644\u0641\u064A\u0629",
  "Screen-up bench \xB7 front camera": "\u0639\u0644\u0649 \u0627\u0644\u0637\u0627\u0648\u0644\u0629 \u0648\u0627\u0644\u0634\u0627\u0634\u0629 \u0644\u0644\u0623\u0639\u0644\u0649 \xB7 \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u0623\u0645\u0627\u0645\u064A\u0629",
  "Hands-free stand \xB7 rear camera": "\u0639\u0644\u0649 \u062D\u0627\u0645\u0644 \xB7 \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u062E\u0644\u0641\u064A\u0629",
  "Camera / lens": "\u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0623\u0648 \u0627\u0644\u0639\u062F\u0633\u0629",
  "Rear camera (automatic)": "\u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u062E\u0644\u0641\u064A\u0629 (\u062A\u0644\u0642\u0627\u0626\u064A)",
  "Front camera (automatic)": "\u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u0623\u0645\u0627\u0645\u064A\u0629 (\u062A\u0644\u0642\u0627\u0626\u064A)",
  "Open camera scanner \u25A5": "\u0627\u0641\u062A\u062D \u0645\u0627\u0633\u062D \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u25A5",
  "Stop camera": "\u0623\u0648\u0642\u0641 \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627",
  "Live barcode camera preview": "\u0645\u0639\u0627\u064A\u0646\u0629 \u0645\u0628\u0627\u0634\u0631\u0629 \u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u0628\u0627\u0631\u0643\u0648\u062F",
  "Whole barcode + blank edges": "\u0627\u0644\u0628\u0627\u0631\u0643\u0648\u062F \u0643\u0627\u0645\u0644\u064B\u0627 \u0645\u0639 \u062D\u0648\u0627\u0641 \u0641\u0627\u0631\u063A\u0629",
  "Choose a setup, then open the camera.": "\u0627\u062E\u062A\u0631 \u0625\u0639\u062F\u0627\u062F \u0627\u0644\u0645\u0633\u062D \u062B\u0645 \u0627\u0641\u062A\u062D \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627.",
  "Mirror preview": "\u0627\u0639\u0643\u0633 \u0627\u0644\u0645\u0639\u0627\u064A\u0646\u0629",
  "Turn preview upside down": "\u0627\u0642\u0644\u0628 \u0627\u0644\u0645\u0639\u0627\u064A\u0646\u0629 \u0631\u0623\u0633\u064B\u0627 \u0639\u0644\u0649 \u0639\u0642\u0628",
  "Light off": "\u0627\u0644\u0625\u0636\u0627\u0621\u0629 \u0645\u062A\u0648\u0642\u0641\u0629",
  "Light on": "\u0627\u0644\u0625\u0636\u0627\u0621\u0629 \u0645\u0641\u0639\u0651\u0644\u0629",
  "Focus, zoom & exposure": "\u0627\u0644\u062A\u0631\u0643\u064A\u0632 \u0648\u0627\u0644\u062A\u0643\u0628\u064A\u0631 \u0648\u0627\u0644\u062A\u0639\u0631\u064A\u0636",
  "Barcode": "\u0627\u0644\u0628\u0627\u0631\u0643\u0648\u062F",
  "Look up": "\u0627\u0628\u062D\u062B",
  "Look up product": "\u0627\u0628\u062D\u062B \u0639\u0646 \u0627\u0644\u0645\u0646\u062A\u062C",
  "Quantity": "\u0627\u0644\u0643\u0645\u064A\u0629",
  "Unit": "\u0627\u0644\u0648\u062D\u062F\u0629",
  "Ingredient": "\u0627\u0644\u0645\u0643\u0648\u0651\u0646",
  "Product name": "\u0627\u0633\u0645 \u0627\u0644\u0645\u0646\u062A\u062C",
  "Expiry date": "\u062A\u0627\u0631\u064A\u062E \u0627\u0644\u0627\u0646\u062A\u0647\u0627\u0621",
  "Optional": "\u0627\u062E\u062A\u064A\u0627\u0631\u064A",
  "Remove": "\u0625\u0632\u0627\u0644\u0629",
  "Edit": "\u062A\u0639\u062F\u064A\u0644",
  "Save": "\u062D\u0641\u0638",
  "Cancel": "\u0625\u0644\u063A\u0627\u0621",
  "Close": "\u0625\u063A\u0644\u0627\u0642",
  "Delete": "\u062D\u0630\u0641",
  "Add": "\u0625\u0636\u0627\u0641\u0629",
  "Search": "\u0628\u062D\u062B",
  "All": "\u0627\u0644\u0643\u0644",
  "Unknown": "\u063A\u064A\u0631 \u0645\u0639\u0631\u0648\u0641",
  "unknown": "\u063A\u064A\u0631 \u0645\u0639\u0631\u0648\u0641",
  "Loading\u2026": "\u062C\u0627\u0631\u064D \u0627\u0644\u062A\u062D\u0645\u064A\u0644\u2026",
  "Loading recipes\u2026": "\u062C\u0627\u0631\u064D \u062A\u062D\u0645\u064A\u0644 \u0627\u0644\u0648\u0635\u0641\u0627\u062A\u2026",
  "Looking up\u2026": "\u062C\u0627\u0631\u064D \u0627\u0644\u0628\u062D\u062B\u2026",
  "Review details at the end": "\u0631\u0627\u062C\u0639 \u0627\u0644\u062A\u0641\u0627\u0635\u064A\u0644 \u0641\u064A \u0627\u0644\u0646\u0647\u0627\u064A\u0629",
  "Final receipt \u2192": "\u0627\u0644\u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0646\u0647\u0627\u0626\u064A\u0629 \u2190",
  "Nothing scanned yet. Let\u2019s see what\u2019s hiding.": "\u0644\u0645 \u062A\u0645\u0633\u062D \u0623\u064A \u0635\u0646\u0641 \u0628\u0639\u062F. \u0644\u0646\u0643\u062A\u0634\u0641 \u0645\u0627 \u0644\u062F\u064A\u0643.",
  "1 package": "\u0639\u0628\u0648\u0629 \u0648\u0627\u062D\u062F\u0629",
  "Scan \u2192 beep \u2192 put it back. Every scan is accepted automatically.": "\u0627\u0645\u0633\u062D\u060C \u0648\u0627\u0633\u062A\u0645\u0639 \u0644\u0644\u062A\u0646\u0628\u064A\u0647\u060C \u062B\u0645 \u0623\u0639\u062F \u0627\u0644\u0635\u0646\u0641. \u064A\u064F\u0636\u0627\u0641 \u0643\u0644 \u0645\u0633\u062D \u062A\u0644\u0642\u0627\u0626\u064A\u064B\u0627.",
  "From your shopping bag to its new home.": "\u0645\u0646 \u0643\u064A\u0633 \u0627\u0644\u062A\u0633\u0648\u0651\u0642 \u0625\u0644\u0649 \u0645\u0643\u0627\u0646\u0647 \u0627\u0644\u062C\u062F\u064A\u062F.",
  "Scan recorded items from this location. Each scan stages removal of that whole recorded item.": "\u0627\u0645\u0633\u062D \u0627\u0644\u0623\u0635\u0646\u0627\u0641 \u0627\u0644\u0645\u0633\u062C\u0651\u0644\u0629 \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u0643\u0627\u0646. \u064A\u062C\u0647\u0651\u0632 \u0643\u0644 \u0645\u0633\u062D \u0625\u0632\u0627\u0644\u0629 \u0627\u0644\u0635\u0646\u0641 \u0627\u0644\u0645\u0633\u062C\u0651\u0644 \u0643\u0627\u0645\u0644\u064B\u0627.",
  "Accepted. Next item, please.": "\u062A\u0645\u062A \u0627\u0644\u0625\u0636\u0627\u0641\u0629. \u0627\u0644\u0635\u0646\u0641 \u0627\u0644\u062A\u0627\u0644\u064A\u060C \u0645\u0646 \u0641\u0636\u0644\u0643.",
  "Accepted. Looking up details while you keep scanning\u2026": "\u062A\u0645\u062A \u0627\u0644\u0625\u0636\u0627\u0641\u0629. \u062C\u0627\u0631\u064D \u0627\u0644\u0628\u062D\u062B \u0639\u0646 \u0627\u0644\u062A\u0641\u0627\u0635\u064A\u0644\u060C \u0648\u064A\u0645\u0643\u0646\u0643 \u0645\u062A\u0627\u0628\u0639\u0629 \u0627\u0644\u0645\u0633\u062D\u2026",
  "Unknown product kept on your receipt. Keep scanning; review it at the end.": "\u0623\u064F\u0628\u0642\u064A \u0627\u0644\u0645\u0646\u062A\u062C \u063A\u064A\u0631 \u0627\u0644\u0645\u0639\u0631\u0648\u0641 \u0641\u064A \u0642\u0627\u0626\u0645\u062A\u0643. \u062A\u0627\u0628\u0639 \u0627\u0644\u0645\u0633\u062D \u0648\u0631\u0627\u062C\u0639\u0647 \u0641\u064A \u0627\u0644\u0646\u0647\u0627\u064A\u0629.",
  "Product details unavailable.": "\u062A\u0641\u0627\u0635\u064A\u0644 \u0627\u0644\u0645\u0646\u062A\u062C \u063A\u064A\u0631 \u0645\u062A\u0627\u062D\u0629.",
  "Lookup unavailable.": "\u0627\u0644\u0628\u062D\u062B \u063A\u064A\u0631 \u0645\u062A\u0627\u062D.",
  "Enter or scan a barcode first.": "\u0623\u062F\u062E\u0644 \u0628\u0627\u0631\u0643\u0648\u062F \u0623\u0648 \u0627\u0645\u0633\u062D\u0647 \u0623\u0648\u0644\u064B\u0627.",
  "Recipes imported.": "\u062A\u0645 \u0627\u0633\u062A\u064A\u0631\u0627\u062F \u0627\u0644\u0648\u0635\u0641\u0627\u062A.",
  "No remaining matching inventory item in this source location. Nothing removed.": "\u0644\u0627 \u064A\u0648\u062C\u062F \u0635\u0646\u0641 \u0645\u0637\u0627\u0628\u0642 \u0645\u062A\u0628\u0642\u064D \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u0643\u0627\u0646. \u0644\u0645 \u064A\u064F\u062D\u0630\u0641 \u0634\u064A\u0621.",
  "Demo kitchen \xB7 separate sample data.": "\u0645\u0637\u0628\u062E \u062A\u062C\u0631\u064A\u0628\u064A \xB7 \u0628\u064A\u0627\u0646\u0627\u062A \u0646\u0645\u0648\u0630\u062C\u064A\u0629 \u0645\u0646\u0641\u0635\u0644\u0629.",
  "Signed in \xB7 automatic cloud saves; local copy available offline.": "\u062A\u0645 \u062A\u0633\u062C\u064A\u0644 \u0627\u0644\u062F\u062E\u0648\u0644 \xB7 \u062D\u0641\u0638 \u0633\u062D\u0627\u0628\u064A \u062A\u0644\u0642\u0627\u0626\u064A \u0648\u0646\u0633\u062E\u0629 \u0645\u062D\u0644\u064A\u0629 \u0645\u062A\u0627\u062D\u0629 \u062F\u0648\u0646 \u0627\u062A\u0635\u0627\u0644.",
  "Guest pantry \xB7 saved in this browser.": "\u0645\u062E\u0632\u0648\u0646 \u0627\u0644\u0636\u064A\u0641 \xB7 \u0645\u062D\u0641\u0648\u0638 \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u062A\u0635\u0641\u062D.",
  "Offline \xB7 Pantry and downloaded recipes work. New product and shop lookups need internet.": "\u062F\u0648\u0646 \u0627\u062A\u0635\u0627\u0644 \xB7 \u064A\u0639\u0645\u0644 \u0627\u0644\u0645\u062E\u0632\u0648\u0646 \u0648\u0627\u0644\u0648\u0635\u0641\u0627\u062A \u0627\u0644\u0645\u0646\u0632\u0651\u0644\u0629. \u064A\u062A\u0637\u0644\u0651\u0628 \u0627\u0644\u0628\u062D\u062B \u0639\u0646 \u0645\u0646\u062A\u062C\u0627\u062A \u0648\u0645\u062A\u0627\u062C\u0631 \u062C\u062F\u064A\u062F\u0629 \u0627\u062A\u0635\u0627\u0644\u064B\u0627 \u0628\u0627\u0644\u0625\u0646\u062A\u0631\u0646\u062A.",
  "Demo changes stay separate from your kitchen.": "\u062A\u0628\u0642\u0649 \u062A\u063A\u064A\u064A\u0631\u0627\u062A \u0627\u0644\u062A\u062C\u0631\u0628\u0629 \u0645\u0646\u0641\u0635\u0644\u0629 \u0639\u0646 \u0645\u0637\u0628\u062E\u0643.",
  "Local changes \xB7 saving automatically.": "\u062A\u063A\u064A\u064A\u0631\u0627\u062A \u0645\u062D\u0644\u064A\u0629 \xB7 \u062C\u0627\u0631\u064D \u0627\u0644\u062D\u0641\u0638 \u062A\u0644\u0642\u0627\u0626\u064A\u064B\u0627.",
  "Guest data is saved in this browser.": "\u062A\u064F\u062D\u0641\u0638 \u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0636\u064A\u0641 \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u062A\u0635\u0641\u062D.",
  "Guest data stays in this browser.": "\u062A\u0628\u0642\u0649 \u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0636\u064A\u0641 \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u062A\u0635\u0641\u062D.",
  "Preferred country": "\u0627\u0644\u0628\u0644\u062F \u0627\u0644\u0645\u0641\u0636\u0651\u0644",
  "Global \xB7 all countries": "\u0639\u0627\u0644\u0645\u064A \xB7 \u062C\u0645\u064A\u0639 \u0627\u0644\u0628\u0644\u062F\u0627\u0646",
  "Preferred display units": "\u0648\u062D\u062F\u0627\u062A \u0627\u0644\u0639\u0631\u0636 \u0627\u0644\u0645\u0641\u0636\u0651\u0644\u0629",
  "Metric": "\u0645\u062A\u0631\u064A",
  "Imperial": "\u0625\u0645\u0628\u0631\u0627\u0637\u0648\u0631\u064A",
  "Sign out": "\u062A\u0633\u062C\u064A\u0644 \u0627\u0644\u062E\u0631\u0648\u062C",
  "Save kitchen to cloud \u2191": "\u0627\u062D\u0641\u0638 \u0627\u0644\u0645\u0637\u0628\u062E \u0641\u064A \u0627\u0644\u0633\u062D\u0627\u0628\u0629 \u2191",
  "Restore cloud copy \u2193": "\u0627\u0633\u062A\u0639\u062F \u0627\u0644\u0646\u0633\u062E\u0629 \u0627\u0644\u0633\u062D\u0627\u0628\u064A\u0629 \u2193",
  "Backups & recipe imports": "\u0627\u0644\u0646\u0633\u062E \u0627\u0644\u0627\u062D\u062A\u064A\u0627\u0637\u064A\u0629 \u0648\u0627\u0633\u062A\u064A\u0631\u0627\u062F \u0627\u0644\u0648\u0635\u0641\u0627\u062A",
  "Export kitchen backup": "\u0635\u062F\u0651\u0631 \u0646\u0633\u062E\u0629 \u0627\u062D\u062A\u064A\u0627\u0637\u064A\u0629 \u0644\u0644\u0645\u0637\u0628\u062E",
  "Sign in to restore your pantry on another device.": "\u0633\u062C\u0651\u0644 \u0627\u0644\u062F\u062E\u0648\u0644 \u0644\u0627\u0633\u062A\u0639\u0627\u062F\u0629 \u0645\u062E\u0632\u0648\u0646\u0643 \u0639\u0644\u0649 \u062C\u0647\u0627\u0632 \u0622\u062E\u0631.",
  "Account setup pending. Guest pantry and offline recipes remain available.": "\u0625\u0639\u062F\u0627\u062F \u0627\u0644\u062D\u0633\u0627\u0628 \u0642\u064A\u062F \u0627\u0644\u0627\u0646\u062A\u0638\u0627\u0631. \u064A\u0638\u0644 \u0645\u062E\u0632\u0648\u0646 \u0627\u0644\u0636\u064A\u0641 \u0648\u0627\u0644\u0648\u0635\u0641\u0627\u062A \u062F\u0648\u0646 \u0627\u062A\u0635\u0627\u0644 \u0645\u062A\u0627\u062D\u064A\u0646.",
  "Exit the demo to save your own kitchen.": "\u0623\u0646\u0647\u0650 \u0627\u0644\u062A\u062C\u0631\u0628\u0629 \u0644\u062D\u0641\u0638 \u0645\u0637\u0628\u062E\u0643 \u0627\u0644\u062E\u0627\u0635.",
  "Cloud operation failed.": "\u0641\u0634\u0644\u062A \u0627\u0644\u0639\u0645\u0644\u064A\u0629 \u0627\u0644\u0633\u062D\u0627\u0628\u064A\u0629.",
  "Replace this browser copy with the cloud save? Export local changes first.": "\u0647\u0644 \u062A\u0631\u064A\u062F \u0627\u0633\u062A\u0628\u062F\u0627\u0644 \u0646\u0633\u062E\u0629 \u0647\u0630\u0627 \u0627\u0644\u0645\u062A\u0635\u0641\u062D \u0628\u0627\u0644\u0646\u0633\u062E\u0629 \u0627\u0644\u0633\u062D\u0627\u0628\u064A\u0629\u061F \u0635\u062F\u0651\u0631 \u0627\u0644\u062A\u063A\u064A\u064A\u0631\u0627\u062A \u0627\u0644\u0645\u062D\u0644\u064A\u0629 \u0623\u0648\u0644\u064B\u0627.",
  "Cloud copy restored.": "\u062A\u0645\u062A \u0627\u0633\u062A\u0639\u0627\u062F\u0629 \u0627\u0644\u0646\u0633\u062E\u0629 \u0627\u0644\u0633\u062D\u0627\u0628\u064A\u0629.",
  "No cloud copy yet. Add items or import a backup, then save.": "\u0644\u0627 \u062A\u0648\u062C\u062F \u0646\u0633\u062E\u0629 \u0633\u062D\u0627\u0628\u064A\u0629 \u0628\u0639\u062F. \u0623\u0636\u0641 \u0623\u0635\u0646\u0627\u0641\u064B\u0627 \u0623\u0648 \u0627\u0633\u062A\u0648\u0631\u062F \u0646\u0633\u062E\u0629 \u0627\u062D\u062A\u064A\u0627\u0637\u064A\u0629\u060C \u062B\u0645 \u0627\u062D\u0641\u0638.",
  "Saved to cloud. Automatic saving continues.": "\u062A\u0645 \u0627\u0644\u062D\u0641\u0638 \u0641\u064A \u0627\u0644\u0633\u062D\u0627\u0628\u0629. \u064A\u0633\u062A\u0645\u0631 \u0627\u0644\u062D\u0641\u0638 \u0627\u0644\u062A\u0644\u0642\u0627\u0626\u064A.",
  "Check your email to confirm your account.": "\u062A\u062D\u0642\u0651\u0642 \u0645\u0646 \u0628\u0631\u064A\u062F\u0643 \u0627\u0644\u0625\u0644\u0643\u062A\u0631\u0648\u0646\u064A \u0644\u062A\u0623\u0643\u064A\u062F \u062D\u0633\u0627\u0628\u0643.",
  "Check your email for recovery instructions.": "\u062A\u062D\u0642\u0651\u0642 \u0645\u0646 \u0628\u0631\u064A\u062F\u0643 \u0627\u0644\u0625\u0644\u0643\u062A\u0631\u0648\u0646\u064A \u0644\u0644\u062D\u0635\u0648\u0644 \u0639\u0644\u0649 \u062A\u0639\u0644\u064A\u0645\u0627\u062A \u0627\u0644\u0627\u0633\u062A\u0639\u0627\u062F\u0629.",
  "Forgot password?": "\u0646\u0633\u064A\u062A \u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631\u061F",
  "Set new password": "\u0639\u064A\u0651\u0646 \u0643\u0644\u0645\u0629 \u0645\u0631\u0648\u0631 \u062C\u062F\u064A\u062F\u0629",
  "Email": "\u0627\u0644\u0628\u0631\u064A\u062F \u0627\u0644\u0625\u0644\u0643\u062A\u0631\u0648\u0646\u064A",
  "Password": "\u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631",
  "Create account": "\u0625\u0646\u0634\u0627\u0621 \u062D\u0633\u0627\u0628",
  "YOUR INGREDIENTS, NEW IDEAS": "\u0645\u0643\u0648\u0651\u0646\u0627\u062A\u0643 \u0648\u0623\u0641\u0643\u0627\u0631 \u062C\u062F\u064A\u062F\u0629",
  "START WITH WHAT YOU HAVE": "\u0627\u0628\u062F\u0623 \u0628\u0645\u0627 \u0644\u062F\u064A\u0643",
  "Three ideas for dinner.": "\u062B\u0644\u0627\u062B \u0623\u0641\u0643\u0627\u0631 \u0644\u0644\u0639\u0634\u0627\u0621.",
  "Household portions": "\u062D\u0635\u0635 \u0627\u0644\u0623\u0633\u0631\u0629",
  "Refresh \u21BB": "\u062A\u062D\u062F\u064A\u062B \u21BB",
  "Find a dish or ingredient": "\u0627\u0628\u062D\u062B \u0639\u0646 \u0637\u0628\u0642 \u0623\u0648 \u0645\u0643\u0648\u0651\u0646",
  "e.g. rice, soup, coconut": "\u0645\u062B\u0644: \u0627\u0644\u0623\u0631\u0632 \u0623\u0648 \u0627\u0644\u062D\u0633\u0627\u0621 \u0623\u0648 \u062C\u0648\u0632 \u0627\u0644\u0647\u0646\u062F",
  "Cook from": "\u0627\u0633\u062A\u062E\u062F\u0645 \u0645\u062E\u0632\u0648\u0646",
  "Whole kitchen": "\u0627\u0644\u0645\u0637\u0628\u062E \u0643\u0644\u0647",
  "Show": "\u0639\u0631\u0636",
  "All menus": "\u062C\u0645\u064A\u0639 \u0627\u0644\u0648\u062C\u0628\u0627\u062A",
  "Ready to cook": "\u062C\u0627\u0647\u0632 \u0644\u0644\u0637\u0647\u064A",
  "Missing ingredients": "\u0645\u0643\u0648\u0651\u0646\u0627\u062A \u0646\u0627\u0642\u0635\u0629",
  "Needs review": "\u064A\u062D\u062A\u0627\u062C \u0625\u0644\u0649 \u0645\u0631\u0627\u062C\u0639\u0629",
  "Who is eating?": "\u0645\u0646 \u0633\u064A\u062A\u0646\u0627\u0648\u0644 \u0627\u0644\u0637\u0639\u0627\u0645\u061F",
  "Cook this meal": "\u0627\u0637\u0647\u0650 \u0647\u0630\u0647 \u0627\u0644\u0648\u062C\u0628\u0629",
  "Serve / after meal": "\u0642\u062F\u0651\u0645 \u0627\u0644\u0648\u062C\u0628\u0629 \u0623\u0648 \u0633\u062C\u0651\u0644\u0647\u0627",
  "Save as favourite": "\u0627\u062D\u0641\u0638 \u0641\u064A \u0627\u0644\u0645\u0641\u0636\u0651\u0644\u0629",
  "Saved favourite \u2713": "\u0645\u062D\u0641\u0648\u0638 \u0641\u064A \u0627\u0644\u0645\u0641\u0636\u0651\u0644\u0629 \u2713",
  "Breakfast": "\u0627\u0644\u0641\u0637\u0648\u0631",
  "Lunch": "\u0627\u0644\u063A\u062F\u0627\u0621",
  "Dinner": "\u0627\u0644\u0639\u0634\u0627\u0621",
  "Snack": "\u0648\u062C\u0628\u0629 \u062E\u0641\u064A\u0641\u0629",
  "Meal": "\u0627\u0644\u0648\u062C\u0628\u0629",
  "Date": "\u0627\u0644\u062A\u0627\u0631\u064A\u062E",
  "Daily": "\u064A\u0648\u0645\u064A",
  "Weekly": "\u0623\u0633\u0628\u0648\u0639\u064A",
  "Portions": "\u0627\u0644\u062D\u0635\u0635",
  "Planned meals": "\u0627\u0644\u0648\u062C\u0628\u0627\u062A \u0627\u0644\u0645\u062E\u0637\u0651\u0637\u0629",
  "Planned portions": "\u0627\u0644\u062D\u0635\u0635 \u0627\u0644\u0645\u062E\u0637\u0651\u0637\u0629",
  "All storage": "\u062C\u0645\u064A\u0639 \u0623\u0645\u0627\u0643\u0646 \u0627\u0644\u062A\u062E\u0632\u064A\u0646",
  "Edit location": "\u0639\u062F\u0651\u0644 \u0645\u0643\u0627\u0646 \u0627\u0644\u062A\u062E\u0632\u064A\u0646",
  "Edit preferences": "\u0639\u062F\u0651\u0644 \u0627\u0644\u062A\u0641\u0636\u064A\u0644\u0627\u062A",
  "Remove member": "\u0623\u0632\u0644 \u0627\u0644\u0634\u062E\u0635",
  "Add people, their preferences and dietary advisors to personalise your menus.": "\u0623\u0636\u0641 \u0627\u0644\u0623\u0634\u062E\u0627\u0635 \u0648\u062A\u0641\u0636\u064A\u0644\u0627\u062A\u0647\u0645 \u0648\u062E\u064A\u0627\u0631\u0627\u062A\u0647\u0645 \u0627\u0644\u063A\u0630\u0627\u0626\u064A\u0629 \u0644\u062A\u062E\u0635\u064A\u0635 \u0627\u0644\u0648\u062C\u0628\u0627\u062A.",
  "Recipe no longer available": "\u0627\u0644\u0648\u0635\u0641\u0629 \u0644\u0645 \u062A\u0639\u062F \u0645\u062A\u0627\u062D\u0629",
  "Meal nutrients & notes": "\u0645\u063A\u0630\u0651\u064A\u0627\u062A \u0627\u0644\u0648\u062C\u0628\u0629 \u0648\u0627\u0644\u0645\u0644\u0627\u062D\u0638\u0627\u062A",
  "Delete log": "\u0627\u062D\u0630\u0641 \u0627\u0644\u0633\u062C\u0644",
  "AFTER THE LAST BITE": "\u0628\u0639\u062F \u0627\u0644\u0648\u062C\u0628\u0629",
  "How did the meal go?": "\u0643\u064A\u0641 \u0643\u0627\u0646\u062A \u0627\u0644\u0648\u062C\u0628\u0629\u061F",
  "Recipe or custom meal": "\u0648\u0635\u0641\u0629 \u0623\u0648 \u0648\u062C\u0628\u0629 \u0645\u062E\u0635\u0651\u0635\u0629",
  "Date eaten": "\u062A\u0627\u0631\u064A\u062E \u062A\u0646\u0627\u0648\u0644 \u0627\u0644\u0637\u0639\u0627\u0645",
  "Who ate this?": "\u0645\u0646 \u062A\u0646\u0627\u0648\u0644 \u0647\u0630\u0647 \u0627\u0644\u0648\u062C\u0628\u0629\u061F",
  "Portions served": "\u0627\u0644\u062D\u0635\u0635 \u0627\u0644\u0645\u0642\u062F\u0651\u0645\u0629",
  "Eaten (%) \xB7 optional": "\u0627\u0644\u0646\u0633\u0628\u0629 \u0627\u0644\u0645\u0623\u0643\u0648\u0644\u0629 (%) \xB7 \u0627\u062E\u062A\u064A\u0627\u0631\u064A",
  "100 if left blank": "\u0661\u0660\u0660 \u0625\u0630\u0627 \u062A\u064F\u0631\u0643 \u0641\u0627\u0631\u063A\u064B\u0627",
  "What happened to the rest?": "\u0645\u0627\u0630\u0627 \u062D\u062F\u062B \u0644\u0644\u0628\u0627\u0642\u064A\u061F",
  "Not recorded": "\u063A\u064A\u0631 \u0645\u0633\u062C\u0651\u0644",
  "Saved for later": "\u0645\u062D\u0641\u0648\u0638 \u0644\u0648\u0642\u062A \u0644\u0627\u062D\u0642",
  "Discarded": "\u062A\u0645 \u0627\u0644\u062A\u062E\u0644\u0651\u0635 \u0645\u0646\u0647",
  "Shared with someone else": "\u062A\u0645\u062A \u0645\u0634\u0627\u0631\u0643\u062A\u0647 \u0645\u0639 \u0634\u062E\u0635 \u0622\u062E\u0631",
  "Meal name": "\u0627\u0633\u0645 \u0627\u0644\u0648\u062C\u0628\u0629",
  "Meal notes": "\u0645\u0644\u0627\u062D\u0638\u0627\u062A \u0627\u0644\u0648\u062C\u0628\u0629",
  "Likes, dislikes, leftovers\u2026": "\u0645\u0627 \u0623\u0639\u062C\u0628\u0643 \u0648\u0645\u0627 \u0644\u0645 \u064A\u0639\u062C\u0628\u0643 \u0648\u0628\u0642\u0627\u064A\u0627 \u0627\u0644\u0637\u0639\u0627\u0645\u2026",
  "Save after-meal record \u2713": "\u0627\u062D\u0641\u0638 \u0633\u062C\u0644 \u0645\u0627 \u0628\u0639\u062F \u0627\u0644\u0648\u062C\u0628\u0629 \u2713",
  "Energy": "\u0627\u0644\u0637\u0627\u0642\u0629",
  "Protein": "\u0627\u0644\u0628\u0631\u0648\u062A\u064A\u0646",
  "Carbohydrates": "\u0627\u0644\u0643\u0631\u0628\u0648\u0647\u064A\u062F\u0631\u0627\u062A",
  "Fat": "\u0627\u0644\u062F\u0647\u0648\u0646",
  "Fibre": "\u0627\u0644\u0623\u0644\u064A\u0627\u0641",
  "Sugar": "\u0627\u0644\u0633\u0643\u0631",
  "Sodium": "\u0627\u0644\u0635\u0648\u062F\u064A\u0648\u0645",
  "Salt": "\u0627\u0644\u0645\u0644\u062D",
  "Search recipes": "\u0627\u0628\u062D\u062B \u0639\u0646 \u0627\u0644\u0648\u0635\u0641\u0627\u062A",
  "Read recipe & review quantities": "\u0627\u0642\u0631\u0623 \u0627\u0644\u0648\u0635\u0641\u0629 \u0648\u0631\u0627\u062C\u0639 \u0627\u0644\u0643\u0645\u064A\u0627\u062A",
  "Show more recipes": "\u0627\u0639\u0631\u0636 \u0627\u0644\u0645\u0632\u064A\u062F \u0645\u0646 \u0627\u0644\u0648\u0635\u0641\u0627\u062A",
  "Source instructions": "\u062A\u0639\u0644\u064A\u0645\u0627\u062A \u0627\u0644\u0645\u0635\u062F\u0631",
  "Review for my kitchen": "\u0631\u0627\u062C\u0639\u0647\u0627 \u0644\u0645\u0637\u0628\u062E\u064A",
  "Reviewed serving yield": "\u0639\u062F\u062F \u0627\u0644\u062D\u0635\u0635 \u0628\u0639\u062F \u0627\u0644\u0645\u0631\u0627\u062C\u0639\u0629",
  "Save my reviewed recipe": "\u0627\u062D\u0641\u0638 \u0648\u0635\u0641\u062A\u064A \u0627\u0644\u0645\u0631\u0627\u062C\u064E\u0639\u0629",
  "Download source recipe as JSON-LD": "\u0646\u0632\u0651\u0644 \u0648\u0635\u0641\u0629 \u0627\u0644\u0645\u0635\u062F\u0631 \u0628\u0635\u064A\u063A\u0629 JSON-LD",
  "Keep the kitchen current.": "\u062D\u062F\u0651\u062B \u062D\u0627\u0644\u0629 \u0627\u0644\u0645\u0637\u0628\u062E.",
  "Inventory item": "\u0627\u0644\u0635\u0646\u0641 \u0641\u064A \u0627\u0644\u0645\u062E\u0632\u0648\u0646",
  "Label use-by date (optional)": "\u062A\u0627\u0631\u064A\u062E \u0627\u0644\u0627\u0633\u062A\u062E\u062F\u0627\u0645 \u0639\u0644\u0649 \u0627\u0644\u0639\u0628\u0648\u0629 (\u0627\u062E\u062A\u064A\u0627\u0631\u064A)",
  "Estimated check reminder, days from today (optional)": "\u062A\u0630\u0643\u064A\u0631 \u062A\u0642\u062F\u064A\u0631\u064A \u0628\u0627\u0644\u0641\u062D\u0635\u060C \u0628\u0627\u0644\u0623\u064A\u0627\u0645 \u0645\u0646 \u0627\u0644\u064A\u0648\u0645 (\u0627\u062E\u062A\u064A\u0627\u0631\u064A)",
  "Choose based on this item and storage": "\u0627\u062E\u062A\u0631 \u062D\u0633\u0628 \u0627\u0644\u0635\u0646\u0641 \u0648\u0638\u0631\u0648\u0641 \u062A\u062E\u0632\u064A\u0646\u0647",
  "Use suggested check interval": "\u0627\u0633\u062A\u062E\u062F\u0645 \u0641\u062A\u0631\u0629 \u0627\u0644\u0641\u062D\u0635 \u0627\u0644\u0645\u0642\u062A\u0631\u062D\u0629",
  "Reminder note": "\u0645\u0644\u0627\u062D\u0638\u0629 \u0627\u0644\u062A\u0630\u0643\u064A\u0631",
  "e.g. opened today; check freshness": "\u0645\u062B\u0644: \u0641\u064F\u062A\u062D \u0627\u0644\u064A\u0648\u0645\u061B \u062A\u062D\u0642\u0651\u0642 \u0645\u0646 \u062D\u0627\u0644\u062A\u0647",
  "Save dates & reminder": "\u0627\u062D\u0641\u0638 \u0627\u0644\u062A\u0648\u0627\u0631\u064A\u062E \u0648\u0627\u0644\u062A\u0630\u0643\u064A\u0631",
  "Close recipe": "\u0623\u063A\u0644\u0642 \u0627\u0644\u0648\u0635\u0641\u0629",
  "Close meal log": "\u0623\u063A\u0644\u0642 \u0633\u062C\u0644 \u0627\u0644\u0648\u062C\u0628\u0629",
  "Close freshness settings": "\u0623\u063A\u0644\u0642 \u0625\u0639\u062F\u0627\u062F\u0627\u062A \u0627\u0644\u062A\u0630\u0643\u064A\u0631",
  "Kitchen navigation": "\u0627\u0644\u062A\u0646\u0642\u0651\u0644 \u0641\u064A \u0627\u0644\u0645\u0637\u0628\u062E",
  "offmenu home": "\u0635\u0641\u062D\u0629 offmenu \u0627\u0644\u0631\u0626\u064A\u0633\u064A\u0629",
  "Not available": "\u063A\u064A\u0631 \u0645\u062A\u0627\u062D",
  "not available": "\u063A\u064A\u0631 \u0645\u062A\u0627\u062D",
  "Food data & estimated nutrition": "\u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0637\u0639\u0627\u0645 \u0648\u0627\u0644\u062A\u063A\u0630\u064A\u0629 \u0627\u0644\u062A\u0642\u062F\u064A\u0631\u064A\u0629",
  "Add a meal to see shopping gaps.": "\u0623\u0636\u0641 \u0648\u062C\u0628\u0629 \u0644\u0631\u0624\u064A\u0629 \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A \u0627\u0644\u0646\u0627\u0642\u0635\u0629.",
  "Add a menu to build your ingredient list.": "\u0623\u0636\u0641 \u0648\u062C\u0628\u0629 \u0644\u0625\u0646\u0634\u0627\u0621 \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0645\u0643\u0648\u0651\u0646\u0627\u062A.",
  "Unmeasured ingredients to review": "\u0645\u0643\u0648\u0651\u0646\u0627\u062A \u063A\u064A\u0631 \u0645\u0642\u0627\u0633\u0629 \u062A\u062D\u062A\u0627\u062C \u0625\u0644\u0649 \u0645\u0631\u0627\u062C\u0639\u0629",
  "No measured ingredient gaps. Check unmeasured ingredients below.": "\u0644\u0627 \u062A\u0648\u062C\u062F \u0645\u0643\u0648\u0651\u0646\u0627\u062A \u0645\u0642\u0627\u0633\u0629 \u0646\u0627\u0642\u0635\u0629. \u0631\u0627\u062C\u0639 \u0627\u0644\u0645\u0643\u0648\u0651\u0646\u0627\u062A \u063A\u064A\u0631 \u0627\u0644\u0645\u0642\u0627\u0633\u0629 \u0623\u062F\u0646\u0627\u0647.",
  "Your food journal starts with the next meal. Log a recipe or enter totals from a label.": "\u064A\u0628\u062F\u0623 \u0633\u062C\u0644 \u0637\u0639\u0627\u0645\u0643 \u0628\u0627\u0644\u0648\u062C\u0628\u0629 \u0627\u0644\u062A\u0627\u0644\u064A\u0629. \u0633\u062C\u0651\u0644 \u0648\u0635\u0641\u0629 \u0623\u0648 \u0623\u062F\u062E\u0644 \u0627\u0644\u0625\u062C\u0645\u0627\u0644\u064A\u0627\u062A \u0645\u0646 \u0627\u0644\u0639\u0628\u0648\u0629.",
  "Unavailable source text": "\u0646\u0635 \u0627\u0644\u0645\u0635\u062F\u0631 \u063A\u064A\u0631 \u0645\u062A\u0627\u062D",
  "Nutrient metric": "\u0627\u0644\u0645\u0624\u0634\u0631 \u0627\u0644\u063A\u0630\u0627\u0626\u064A",
  "Status": "\u0627\u0644\u062D\u0627\u0644\u0629",
  "Total": "\u0627\u0644\u0625\u062C\u0645\u0627\u0644\u064A",
  "Known subtotal": "\u0627\u0644\u0625\u062C\u0645\u0627\u0644\u064A \u0627\u0644\u062C\u0632\u0626\u064A \u0627\u0644\u0645\u0639\u0631\u0648\u0641",
  "Per 1,000 kcal": "\u0644\u0643\u0644 \u0661\u0660\u0660\u0660 \u0633\u0639\u0631\u0629 \u062D\u0631\u0627\u0631\u064A\u0629",
  "Mass coverage": "\u062A\u063A\u0637\u064A\u0629 \u0627\u0644\u0643\u062A\u0644\u0629",
  "Done.": "\u062A\u0645\u0651.",
  "Country": "\u0627\u0644\u0628\u0644\u062F",
  "Evidence": "\u0627\u0644\u0623\u062F\u0644\u0629",
  "Global food and evidence workspace": "\u0645\u0633\u0627\u062D\u0629 \u0639\u0645\u0644 \u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0637\u0639\u0627\u0645 \u0648\u0627\u0644\u0623\u062F\u0644\u0629 \u0627\u0644\u0639\u0627\u0644\u0645\u064A\u0629",
  "OffMenu \xB7 Global data workspace": "OffMenu \xB7 \u0645\u0633\u0627\u062D\u0629 \u0639\u0645\u0644 \u0627\u0644\u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0639\u0627\u0644\u0645\u064A\u0629",
  "\u2190 My kitchen": "\u2190 \u0645\u0637\u0628\u062E\u064A",
  "Open country": "\u0627\u0639\u0631\u0636 \u0627\u0644\u0628\u0644\u062F",
  "Country coverage and starter baskets": "\u062A\u063A\u0637\u064A\u0629 \u0627\u0644\u0628\u0644\u062F\u0627\u0646 \u0648\u0633\u0644\u0627\u0644 \u0627\u0644\u0628\u062F\u0627\u064A\u0629",
  "Calculate nutrients and coverage": "\u0627\u062D\u0633\u0628 \u0627\u0644\u0639\u0646\u0627\u0635\u0631 \u0627\u0644\u063A\u0630\u0627\u0626\u064A\u0629 \u0648\u0627\u0644\u062A\u063A\u0637\u064A\u0629",
  "Native language support": "\u062F\u0639\u0645 \u0627\u0644\u0644\u063A\u0629 \u0627\u0644\u0623\u0635\u0644\u064A\u0629",
  "National sources / access": "\u0627\u0644\u0645\u0635\u0627\u062F\u0631 \u0627\u0644\u0648\u0637\u0646\u064A\u0629 \u0648\u0625\u0645\u0643\u0627\u0646\u064A\u0629 \u0627\u0644\u0648\u0635\u0648\u0644",
  "Current offmenu coverage": "\u062A\u063A\u0637\u064A\u0629 offmenu \u0627\u0644\u062D\u0627\u0644\u064A\u0629",
  "Source-specific identity": "\u0647\u0648\u064A\u0629 \u062E\u0627\u0635\u0629 \u0628\u0627\u0644\u0645\u0635\u062F\u0631",
  "Candidate identity link": "\u0631\u0627\u0628\u0637 \u0647\u0648\u064A\u0629 \u0645\u0631\u0634\u0651\u062D",
  "Curated concept": "\u0645\u0641\u0647\u0648\u0645 \u0645\u064F\u0631\u0627\u062C\u0639",
  "Identified resource": "\u0645\u0648\u0631\u062F \u0645\u062D\u062F\u0651\u062F \u0627\u0644\u0647\u0648\u064A\u0629",
  "Source assertion": "\u0628\u064A\u0627\u0646 \u0645\u0646 \u0627\u0644\u0645\u0635\u062F\u0631",
  "Candidate": "\u0645\u0631\u0634\u0651\u062D",
  "Editor authored": "\u0645\u0646 \u062A\u0623\u0644\u064A\u0641 \u0627\u0644\u0645\u062D\u0631\u0651\u0631",
  "Reviewed": "\u0645\u064F\u0631\u0627\u062C\u0639",
  "Verified": "\u0645\u062A\u062D\u0642\u0651\u0642 \u0645\u0646\u0647",
  "Conflicting": "\u0645\u062A\u0639\u0627\u0631\u0636",
  "Superseded": "\u0645\u0633\u062A\u0628\u062F\u064E\u0644",
  "Needs transcription": "\u064A\u062D\u062A\u0627\u062C \u0625\u0644\u0649 \u062A\u0641\u0631\u064A\u063A \u0627\u0644\u0646\u0635",
  "Recipe Variant": "\u0646\u0633\u062E\u0629 \u0645\u0646 \u0648\u0635\u0641\u0629",
  "Recipe Step": "\u062E\u0637\u0648\u0629 \u0641\u064A \u0627\u0644\u0648\u0635\u0641\u0629",
  "Recipe Concept": "\u0645\u0641\u0647\u0648\u0645 \u0648\u0635\u0641\u0629",
  "instruction": "\u062A\u0639\u0644\u064A\u0645\u0627\u062A",
  "position": "\u0627\u0644\u062A\u0631\u062A\u064A\u0628",
  "original Source Record": "\u0633\u062C\u0644 \u0627\u0644\u0645\u0635\u062F\u0631 \u0627\u0644\u0623\u0635\u0644\u064A"
});

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/production-scanner/locale-negotiation.js
var SUPPORTED_LOCALES = Object.freeze(["en", "ar"]);

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/production-scanner/i18n.js
var LANGUAGES = Object.freeze([
  { code: "en", name: "English", direction: "ltr" },
  { code: "ar", name: "\u0627\u0644\u0639\u0631\u0628\u064A\u0629", direction: "rtl" }
]);
var CATALOGUES = { ar: ARABIC };
var renderedLanguages = /* @__PURE__ */ new Map();
var language = "en";
function t(key, values = {}, locale = language) {
  if (typeof key === "number") return new Intl.NumberFormat(locale, { maximumFractionDigits: 20 }).format(key);
  const source = String(key ?? "");
  const catalogue = CATALOGUES[locale] || {};
  const entry = Object.hasOwn(catalogue, source) ? catalogue[source] : source;
  const category = Number.isFinite(values.count) ? new Intl.PluralRules(locale).select(values.count) : "other";
  const message2 = typeof entry === "string" ? entry : entry[category] || entry.other || source;
  const output = message2.replace(/\{([\w]+)\}/g, (match, name) => Object.hasOwn(values, name) ? typeof values[name] === "number" ? new Intl.NumberFormat(locale, { maximumFractionDigits: 20 }).format(values[name]) : String(values[name]) : match);
  const previous = renderedLanguages.get(source);
  const outputLanguage = Object.hasOwn(catalogue, source) ? locale : previous && !Object.keys(values).length ? previous : "en";
  if (renderedLanguages.size >= 2e3) renderedLanguages.delete(renderedLanguages.keys().next().value);
  renderedLanguages.set(output, outputLanguage);
  return output;
}
function renderedLanguage(value) {
  return renderedLanguages.get(String(value));
}
function setLocalizedText(element, key, values = {}, locale = language) {
  const output = t(key, values, locale);
  element.textContent = output;
  element.lang = typeof key === "number" ? locale : renderedLanguage(output) || "en";
  element.dir = "auto";
}

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/production-scanner/scanner-model.js
var NATIVE_FORMATS = ["ean_13", "ean_8", "upc_a", "upc_e"];
function createPresentationGate({ gap = 1200, misses = 4, confirmations = 2 } = {}) {
  let held = "", candidate = "", count = 0, last = 0, emptySince = null, emptyCount = 0;
  return {
    observe(codes, now) {
      const unique = [...new Set(codes.filter(Boolean))];
      if (unique.length !== 1) {
        candidate = "";
        count = 0;
        if (unique.length) {
          emptySince = null;
          emptyCount = 0;
          return null;
        }
        emptySince ??= now;
        if (++emptyCount >= misses && now - emptySince >= gap) held = "";
        return null;
      }
      emptySince = null;
      emptyCount = 0;
      const code2 = unique[0];
      if (code2 === candidate && now - last <= 1800) count++;
      else {
        candidate = code2;
        count = 1;
      }
      last = now;
      if (count < confirmations || held === code2) return null;
      held = code2;
      return code2;
    },
    rearm() {
      held = "";
      candidate = "";
      count = 0;
      emptySince = null;
      emptyCount = 0;
    }
  };
}
function cameraError(error) {
  return { NotAllowedError: "Camera permission is blocked. Allow the camera in this site\u2019s browser settings, then retry.", NotFoundError: "No camera found. Connect a camera or use a barcode photo or manual entry.", NotReadableError: "The camera is busy. Close other camera apps and retry.", OverconstrainedError: "This camera cannot use those settings. Try another camera.", SecurityError: "Open OffMenu directly over HTTPS to use the camera." }[error?.name] || "Camera could not start. Try another camera, a barcode photo, or manual entry.";
}

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/production-scanner/scanner-capture-envelope.js
var CAPTURE_SCHEMA = "offmenu-decoder-capture/1";
var EXTRA_LIMIT = 8192;
var CODE_LIMIT = 128;
var FORMAT = Object.freeze({
  ean_13: "EAN-13",
  EAN13: "EAN-13",
  "EAN-13": "EAN-13",
  ean_8: "EAN-8",
  EAN8: "EAN-8",
  "EAN-8": "EAN-8",
  upc_a: "UPC-A",
  UPCA: "UPC-A",
  "UPC-A": "UPC-A",
  upc_e: "UPC-E",
  UPCE: "UPC-E",
  "UPC-E": "UPC-E",
  ITF: "ITF",
  itf: "ITF",
  "ITF-14": "ITF",
  ITF14: "ITF"
});
function extraUPCE(raw) {
  if (raw == null || raw === "") return { value: null, state: "absent" };
  if (typeof raw !== "string" || raw.length > EXTRA_LIMIT) return { value: null, state: "unsupported-or-oversize" };
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed) || typeof parsed.UPCE !== "string") return { value: null, state: "no-UPCE" };
    return { value: parsed.UPCE, state: "present" };
  } catch {
    return { value: null, state: "invalid-json" };
  }
}
function captureFromDecoder(result, decoderPath) {
  const decoderText = result?.rawValue ?? result?.text;
  const returnedFormat = result?.format ?? null;
  const carrier = typeof returnedFormat === "string" ? FORMAT[returnedFormat] ?? null : null;
  const rawExtra = result?.extra ?? null, upce = extraUPCE(rawExtra);
  const envelope = {
    schema: CAPTURE_SCHEMA,
    namespace: "barcode",
    decoderPath,
    decoderText: typeof decoderText === "string" ? decoderText : null,
    returnedFormat,
    rawExtra,
    extraState: upce.state,
    extraUPCE: upce.value,
    labelledDerived: null,
    lookupLexicalValue: null,
    lookupSymbology: null,
    lookupOrigin: null,
    typed: null,
    status: "manual-required",
    reason: "decoder-result-unavailable"
  };
  const finish = (status2, reason, lexical = null, hint = null, origin = null) => {
    envelope.status = status2;
    envelope.reason = reason;
    envelope.lookupLexicalValue = lexical;
    envelope.lookupSymbology = hint;
    envelope.lookupOrigin = origin;
    if (lexical) envelope.typed = analyzeIdentifier({
      original: lexical,
      namespace: "barcode",
      representationHint: hint,
      observedCarrier: carrier === "ITF" ? "ITF" : returnedFormat
    });
    return envelope;
  };
  if (result?.error || typeof decoderText !== "string" || !decoderText.length || decoderText.length > CODE_LIMIT || /[\x00-\x1f\x7f]/.test(decoderText))
    return finish("manual-required", "decoder-text-unavailable-or-out-of-bounds");
  if (rawExtra !== null && rawExtra !== void 0 && (typeof rawExtra !== "string" || rawExtra.length > EXTRA_LIMIT))
    return finish("manual-required", "decoder-extra-unavailable-or-out-of-bounds");
  if (!carrier) return finish("unsupported", "decoder-format-not-enabled");
  if (carrier === "ITF") return finish(
    "literal-untyped",
    "generic-ITF-does-not-declare-GTIN",
    decoderText,
    null,
    "decoder-text"
  );
  if (carrier === "UPC-E") {
    if (decoderText.length === 8) {
      const expanded2 = expandUPCE(decoderText);
      if (!expanded2) return finish("manual-required", "UPC-E-syntax-or-checksum-invalid");
      if (upce.value !== null && upce.value !== decoderText)
        return finish("manual-required", "UPC-E-extra-conflicts-with-decoder-text");
      if (upce.state === "unsupported-or-oversize" || upce.state === "invalid-json")
        return finish("manual-required", "UPC-E-extra-unreadable");
      return finish("ready", "validated-compressed-UPC-E", decoderText, "UPC-E", "decoder-text");
    }
    if (decoderText.length !== 12 && decoderText.length !== 13)
      return finish("manual-required", "normalized-UPC-E-text-has-unsupported-width");
    if (upce.state !== "present") return finish("manual-required", "compressed-UPC-E-extra-missing");
    const expanded = expandUPCE(upce.value);
    if (!expanded || decoderText !== expanded && decoderText !== "0" + expanded)
      return finish("manual-required", "UPC-E-extra-conflicts-with-normalized-text");
    return finish(
      "ready",
      "validated-UPC-E-extra-against-normalized-text",
      upce.value,
      "UPC-E",
      "validated-decoder-extra.UPCE"
    );
  }
  if (carrier === "UPC-A" && decoderText.length === 13 && decoderText.startsWith("0") && validateGTIN(decoderText)) {
    envelope.labelledDerived = {
      value: decoderText.slice(1),
      representation: "UPC-A",
      rule: "leading-zero-EAN-13-to-UPC-A; printed original unverified"
    };
    return finish(
      "ready",
      "UPC-A-decoder-returned-leading-zero-EAN-13-text",
      decoderText,
      null,
      "decoder-returned-13-digit-form; printed-original-unverified"
    );
  }
  const width = carrier === "UPC-A" ? 12 : carrier === "EAN-13" ? 13 : 8;
  if (decoderText.length !== width || !validateGTIN(decoderText))
    return finish("manual-required", "decoder-representation-syntax-or-checksum-invalid");
  return finish("ready", "validated-decoder-text", decoderText, carrier, "decoder-text");
}
function selectableCaptures(results, decoderPath) {
  return (results || []).map((result) => captureFromDecoder(result, decoderPath)).filter((capture2) => capture2.status === "ready");
}
function requiresUPCEConfirmation(results, decoderPath) {
  return (results || []).some((result) => {
    const capture2 = captureFromDecoder(result, decoderPath);
    return capture2.returnedFormat !== null && FORMAT[capture2.returnedFormat] === "UPC-E" && capture2.status === "manual-required";
  });
}
function captureEvidence(capture2) {
  if (capture2?.schema !== CAPTURE_SCHEMA || capture2.status !== "ready") return null;
  return {
    schema: CAPTURE_SCHEMA,
    decoderPath: capture2.decoderPath,
    decoderText: capture2.decoderText,
    returnedFormat: capture2.returnedFormat,
    rawExtra: capture2.rawExtra,
    lookupLexicalValue: capture2.lookupLexicalValue,
    lookupSymbology: capture2.lookupSymbology,
    lookupOrigin: capture2.lookupOrigin,
    labelledDerived: capture2.labelledDerived
  };
}
function verifyCaptureEvidence(evidence, raw, hint) {
  if (evidence == null) return true;
  if (evidence.schema !== CAPTURE_SCHEMA || !["native", "zxing-wasm", "photo-zxing-wasm"].includes(evidence.decoderPath)) return false;
  const rederived = captureFromDecoder({
    text: evidence.decoderText,
    format: evidence.returnedFormat,
    extra: evidence.rawExtra
  }, evidence.decoderPath);
  return rederived.status === "ready" && rederived.lookupLexicalValue === raw && rederived.lookupSymbology === hint && rederived.lookupOrigin === evidence.lookupOrigin && JSON.stringify(rederived.labelledDerived) === JSON.stringify(evidence.labelledDerived);
}

// ../offmenu-data/runtime/layout-migration/worker13/existing-full-scanner-guest-wiring-20261026/source/production-scanner/guest-scanner-ui.js
function cameraCrop(videoWidth, videoHeight, frame, guide, { mirror = false, rotate = false, fit = "cover" } = {}) {
  if (!(videoWidth > 0 && videoHeight > 0 && frame?.width > 0 && frame?.height > 0 && guide?.width > 0 && guide?.height > 0)) return null;
  const scale = fit === "contain" ? Math.min(frame.width / videoWidth, frame.height / videoHeight) : Math.max(frame.width / videoWidth, frame.height / videoHeight);
  const imageLeft = frame.left + (frame.width - videoWidth * scale) / 2;
  const imageTop = frame.top + (frame.height - videoHeight * scale) / 2;
  const left = Math.max(frame.left, imageLeft, guide.left), top = Math.max(frame.top, imageTop, guide.top);
  const right = Math.min(frame.left + frame.width, imageLeft + videoWidth * scale, guide.left + guide.width);
  const bottom = Math.min(frame.top + frame.height, imageTop + videoHeight * scale, guide.top + guide.height);
  if (right - left < 24 || bottom - top < 24) return null;
  let sx = (left - imageLeft) / scale;
  let sy = (top - imageTop) / scale;
  const sw = (right - left) / scale, sh2 = (bottom - top) / scale;
  if (Boolean(mirror) !== Boolean(rotate)) sx = videoWidth - sx - sw;
  if (rotate) sy = videoHeight - sy - sh2;
  return { sx: Math.max(0, sx), sy: Math.max(0, sy), sw: Math.min(sw, videoWidth - Math.max(0, sx)), sh: Math.min(sh2, videoHeight - Math.max(0, sy)) };
}
function setupScanner({ canScan, onCode, onStream, onStartGesture, autoResume = false, storage }) {
  const $2 = (id2) => document.getElementById(id2), video = $2("video"), canvas = document.createElement("canvas");
  const context = canvas.getContext("2d", { willReadFrequently: true });
  const gate = createPresentationGate();
  let stream = null, token = 0, timer = null, worker = null, pending = null, job = 0, native = null, wake = null;
  let running = false, starting = false, lastFrame = -1, attempts = 0, started = 0, lastRead = 0, lastCodes = [], track = null;
  let preferences = { mode: "handheld", camera: "environment", mirror: false, rotate: false, enhance: true };
  try {
    preferences = { ...preferences, ...JSON.parse((storage ?? localStorage).getItem("offmenu-scanner-v2") || "{}") };
  } catch {
  }
  if (!["handheld", "bench", "stand"].includes(preferences.mode)) preferences.mode = "bench";
  const status2 = (text2) => {
    setLocalizedText($2("scanner-status"), text2);
  };
  const save = () => {
    try {
      (storage ?? localStorage).setItem("offmenu-scanner-v2", JSON.stringify(preferences));
    } catch {
    }
  };
  const range = (cap) => cap && Number.isFinite(cap.min) && Number.isFinite(cap.max) && cap.max > cap.min;
  const caps = () => {
    try {
      return track?.getCapabilities?.() || {};
    } catch {
      return {};
    }
  };
  function preview() {
    video.style.transform = `rotate(${preferences.rotate ? 180 : 0}deg) scaleX(${preferences.mirror ? -1 : 1})`;
    $2("scanner-mirror").checked = preferences.mirror;
    $2("scanner-rotate").checked = preferences.rotate;
    $2("scanner-enhance").checked = preferences.enhance;
  }
  function guide() {
    $2("scanner-mode").value = preferences.mode;
    setLocalizedText($2("scanner-placement"), preferences.mode === "bench" ? t("Screen-up bench: front camera faces the barcode. Start around 30\u201350 cm away and move slowly until the bars look sharp. Fixed-focus lenses may need more distance; use a rear-camera stand if they stay blurry.") : preferences.mode === "stand" ? t("Hands-free rear: prop the phone securely upright or in a stand, with the rear lens exposed. Move each barcode into view and pause for the beep. A phone lying screen-up blocks its rear camera.") : t("Handheld: rear camera recommended. Start around 15\u201330 cm from the barcode; move back if it blurs. Keep the entire code and its blank edges visible. Tilt shiny packaging away from glare."));
  }
  async function keepAwake(sessionToken) {
    if (!navigator.wakeLock?.request) return;
    try {
      const lock = await navigator.wakeLock.request("screen");
      if (sessionToken !== token || !running) await lock.release();
      else wake = lock;
    } catch {
    }
  }
  function closeDecoder() {
    worker?.terminate();
    worker = null;
    if (pending) {
      clearTimeout(pending.timeout);
      pending.reject(Error(t("Decoder stopped")));
      pending = null;
    }
  }
  function stop({ announce = true } = {}) {
    token++;
    running = false;
    starting = false;
    clearTimeout(timer);
    closeDecoder();
    native = null;
    stream?.getTracks().forEach((t3) => t3.stop());
    stream = null;
    track = null;
    onStream(null);
    video.srcObject = null;
    video.hidden = true;
    $2("camera-stage").hidden = true;
    $2("scanner-controls").hidden = true;
    if ($2("stop")) $2("stop").hidden = true;
    if ($2("scan")) $2("scan").disabled = false;
    $2("scanner-photo").disabled = false;
    $2("scanner-rearm").disabled = true;
    if (wake) {
      void wake.release().catch(() => {
      });
      wake = null;
    }
    gate.rearm();
    lastFrame = -1;
    lastCodes = [];
    if (announce) status2("Camera stopped. Your scanned items are kept.");
  }
  async function setting(values) {
    const activeTrack = track;
    if (!activeTrack) return false;
    try {
      await activeTrack.applyConstraints({ advanced: [values] });
      return activeTrack === track;
    } catch {
      status2("This camera/browser could not apply that control. Scanning continues with its current settings.");
      return false;
    }
  }
  function showControls() {
    const c = caps(), settings = track?.getSettings?.() || {};
    const modes2 = c.focusMode || [];
    $2("scanner-focus").replaceChildren();
    for (const [mode2, label] of [["continuous", "Autofocus"], ["single-shot", "Focus once"], ["manual", "Manual focus"]]) {
      if (modes2.includes(mode2) && (mode2 !== "manual" || range(c.focusDistance))) $2("scanner-focus").add(new Option(label, mode2));
    }
    $2("scanner-focus-row").hidden = !$2("scanner-focus").options.length;
    $2("scanner-focus").value = settings.focusMode || $2("scanner-focus").options[0]?.value || "";
    $2("scanner-focus-distance-row").hidden = $2("scanner-focus").value !== "manual" || !range(c.focusDistance);
    for (const [id2, cap, key] of [["zoom", c.zoom, "zoom"], ["focus-distance", c.focusDistance, "focusDistance"], ["exposure", c.exposureCompensation, "exposureCompensation"]]) {
      const input = $2("scanner-" + id2);
      if (id2 !== "focus-distance") $2("scanner-" + id2 + "-row").hidden = !range(cap);
      if (range(cap)) {
        input.min = cap.min;
        input.max = cap.max;
        input.step = cap.step || (cap.max - cap.min) / 100;
        input.value = settings[key] ?? cap.min;
      }
    }
    $2("scanner-torch").hidden = !c.torch;
    $2("scanner-torch").setAttribute("aria-pressed", String(!!settings.torch));
    setLocalizedText($2("scanner-torch"), settings.torch ? t("Light on") : t("Light off"));
    setLocalizedText($2("scanner-capabilities"), `${settings.width || video.videoWidth} \xD7 ${settings.height || video.videoHeight} \xB7 ` + (modes2.includes("continuous") ? "autofocus control available" : modes2.length ? "focus controls available" : "focus control not exposed; lens may be fixed-focus or managed by the camera") + ` \xB7 ${native ? "native + enhanced decoder" : "enhanced decoder"}`);
  }
  async function enumerate() {
    const devices = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "videoinput");
    const selected3 = track?.getSettings?.().deviceId;
    const select = $2("scanner-camera");
    select.replaceChildren(new Option("Rear camera (automatic)", "environment"), new Option("Front camera (automatic)", "user"));
    devices.forEach((d, i14) => select.add(new Option(d.label || `Camera ${i14 + 1}`, d.deviceId)));
    select.value = devices.some((d) => d.deviceId === selected3) ? selected3 : preferences.camera;
  }
  function decode(image, enhance) {
    if (!worker) {
      worker = new Worker("/demo/decoder-worker.js", { type: "module" });
      worker.onmessage = ({ data }) => {
        if (!pending || pending.id !== data.id) return;
        const request = pending;
        pending = null;
        clearTimeout(request.timeout);
        data.error ? request.reject(Error(data.error)) : request.resolve(data.results);
      };
      worker.onerror = () => closeDecoder();
    }
    return new Promise((resolve, reject) => {
      const id2 = ++job;
      pending = { id: id2, resolve, reject, timeout: setTimeout(() => closeDecoder(), 15e3) };
      worker.postMessage({ id: id2, image, enhance }, [image.data.buffer]);
    });
  }
  function pixels(source = video, limit = 1920) {
    const width = source.videoWidth || source.width, height = source.videoHeight || source.height;
    if (!width || !height) throw Error(t("No camera frame yet"));
    const guide2 = $2("capture-guide") || $2("camera-stage")?.querySelector(".scanner-guide");
    const crop = source === video && guide2 ? cameraCrop(width, height, video.getBoundingClientRect(), guide2.getBoundingClientRect(), { ...preferences, fit: getComputedStyle(video).objectFit }) : null;
    if (source === video && !crop) throw Error(t("Visible aiming area unavailable"));
    const sw = crop?.sw || width, sh2 = crop?.sh || height;
    const scale = Math.min(1, limit / Math.max(sw, sh2));
    canvas.width = Math.max(1, Math.round(sw * scale));
    canvas.height = Math.max(1, Math.round(sh2 * scale));
    context.drawImage(source, crop?.sx || 0, crop?.sy || 0, sw, sh2, 0, 0, canvas.width, canvas.height);
    return context.getImageData(0, 0, canvas.width, canvas.height);
  }
  async function loop(sessionToken) {
    if (sessionToken !== token || !running) return;
    if (!canScan()) {
      timer = setTimeout(() => void loop(sessionToken), 140);
      return;
    }
    const begin = performance.now();
    try {
      if (video.readyState >= 2 && video.currentTime !== lastFrame) {
        lastFrame = video.currentTime;
        attempts++;
        let results = [], decoderPath = "native";
        const frame = pixels();
        if (native) {
          try {
            results = await native.detect(canvas);
          } catch {
            native = null;
          }
        }
        if (sessionToken !== token) return;
        if (!requiresUPCEConfirmation(results, "native") && !selectableCaptures(results, "native").length && (!native || attempts % 3 === 0)) {
          results = await decode(frame, preferences.enhance);
          decoderPath = "zxing-wasm";
        }
        if (sessionToken !== token) return;
        const captures = requiresUPCEConfirmation(results, decoderPath) ? [] : selectableCaptures(results, decoderPath);
        const codes = [...new Set(captures.map((x) => x.lookupLexicalValue + "\0" + (x.lookupSymbology || "")))];
        lastCodes = codes;
        const accepted = gate.observe(codes, performance.now());
        if (accepted) {
          const captureEnvelope = captures.find((x) => x.lookupLexicalValue + "\0" + (x.lookupSymbology || "") === accepted);
          lastRead = performance.now();
          onCode(captureEnvelope.lookupLexicalValue, {
            captureEnvelope,
            originalCaptures: [{ value: captureEnvelope.lookupLexicalValue, symbology: captureEnvelope.lookupSymbology }]
          });
          setLocalizedText($2("scanner-last"), "Accepted: {v0}", { v0: captureEnvelope.lookupLexicalValue });
          status2("Scanned \xB7 move item away");
          $2("camera-stage").classList.add("scan-accepted");
          setTimeout(() => $2("camera-stage").classList.remove("scan-accepted"), 500);
        } else if (codes.length > 1) status2("One barcode at a time");
        else if (codes.length === 1 && performance.now() - lastRead > 2e3) status2(lastRead ? "Move item away" : "Hold steady");
        else if (lastRead && !codes.length) status2("Ready");
        else if (!lastRead && performance.now() - started > 6e3) status2(results.some((x) => captureFromDecoder(x, decoderPath).status === "manual-required") ? "Check code in Scan options" : "Aim at barcode");
      }
    } catch {
      if (sessionToken !== token) return;
      if (native) {
        status2("Enhanced decoder unavailable; using the device decoder.");
      } else {
        stop({ announce: false });
        status2("Barcode decoder unavailable. Reconnect and reopen the camera, or type the barcode.");
        return;
      }
    }
    if (sessionToken === token && running) timer = setTimeout(() => void loop(sessionToken), Math.max(70, 140 - (performance.now() - begin)));
  }
  async function start() {
    if (!canScan() || running || starting) return;
    stop({ announce: false });
    starting = true;
    const sessionToken = token;
    if ($2("scan")) $2("scan").disabled = true;
    if ($2("stop")) $2("stop").hidden = false;
    status2("Opening camera\u2026");
    void onStartGesture?.();
    try {
      if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) throw { name: "SecurityError" };
      const camera = preferences.camera;
      const selection = ["environment", "user"].includes(camera) ? { facingMode: { ideal: camera } } : { deviceId: { exact: camera } };
      let acquired;
      try {
        acquired = await navigator.mediaDevices.getUserMedia({ audio: false, video: { ...selection, width: { ideal: 1920 }, height: { ideal: 1080 }, frameRate: { ideal: 30 } } });
      } catch (error) {
        if (error.name !== "OverconstrainedError" || sessionToken !== token) throw error;
        acquired = await navigator.mediaDevices.getUserMedia({ audio: false, video: selection });
      }
      if (sessionToken !== token) {
        acquired.getTracks().forEach((t3) => t3.stop());
        return;
      }
      stream = acquired;
      track = stream.getVideoTracks()[0];
      onStream(stream);
      track.addEventListener("ended", () => {
        if (sessionToken === token) {
          stop({ announce: false });
          status2("Camera disconnected. Reconnect and open the scanner again.");
        }
      });
      video.srcObject = stream;
      video.hidden = false;
      $2("camera-stage").hidden = false;
      await video.play();
      if (sessionToken !== token) return;
      const c = caps();
      for (const key of ["focusMode", "exposureMode", "whiteBalanceMode"]) {
        if (c[key]?.includes("continuous")) await setting({ [key]: "continuous" });
        if (sessionToken !== token) return;
      }
      native = null;
      if ("BarcodeDetector" in window) {
        try {
          const supported = await BarcodeDetector.getSupportedFormats();
          if (NATIVE_FORMATS.every((f) => supported.includes(f))) native = new BarcodeDetector({ formats: NATIVE_FORMATS });
        } catch {
        }
      }
      if (sessionToken !== token) return;
      try {
        await enumerate();
      } catch {
      }
      if (sessionToken !== token) return;
      preview();
      showControls();
      $2("scanner-controls").hidden = false;
      $2("scanner-rearm").disabled = false;
      running = true;
      starting = false;
      started = performance.now();
      lastRead = 0;
      attempts = 0;
      status2("Ready \xB7 aim at barcode");
      void keepAwake(sessionToken);
      void loop(sessionToken);
    } catch (error) {
      if (sessionToken === token) {
        stop({ announce: false });
        status2(cameraError(error));
      }
    }
  }
  $2("scanner-mode").onchange = () => {
    preferences.mode = $2("scanner-mode").value;
    preferences.camera = preferences.mode === "bench" ? "user" : "environment";
    preferences.mirror = preferences.mode === "bench";
    preferences.rotate = false;
    $2("scanner-camera").value = preferences.camera;
    guide();
    preview();
    save();
    if (running || starting) {
      stop({ announce: false });
      void start();
    }
  };
  $2("scanner-camera").onchange = () => {
    preferences.camera = $2("scanner-camera").value;
    save();
    if (running || starting) {
      stop({ announce: false });
      void start();
    }
  };
  for (const key of ["mirror", "rotate", "enhance"]) $2("scanner-" + key).onchange = () => {
    preferences[key] = $2("scanner-" + key).checked;
    preview();
    save();
  };
  $2("scanner-torch").onclick = async () => {
    await setting({ torch: !track?.getSettings?.().torch });
    showControls();
  };
  $2("scanner-focus").onchange = async () => {
    await setting({ focusMode: $2("scanner-focus").value });
    showControls();
  };
  for (const [id2, key] of [["zoom", "zoom"], ["focus-distance", "focusDistance"], ["exposure", "exposureCompensation"]]) $2("scanner-" + id2).onchange = async () => {
    const values = { [key]: Number($2("scanner-" + id2).value) };
    if (key === "focusDistance") values.focusMode = "manual";
    await setting(values);
    showControls();
  };
  $2("scanner-rearm").onclick = () => {
    gate.rearm();
    status2("Ready to count the next identical pack. Keep its barcode in view.");
  };
  $2("scanner-photo").onchange = async () => {
    const file = $2("scanner-photo").files[0];
    $2("scanner-photo").value = "";
    if (!file || !canScan()) return;
    stop({ announce: false });
    const photoToken = token;
    if (file.size > 2e7) return status2("Choose an image smaller than 20 MB.");
    $2("scanner-photo").disabled = true;
    status2("Reading barcode photo\u2026");
    let bitmap;
    try {
      bitmap = await createImageBitmap(file);
      if (photoToken !== token) return;
      const results = await decode(pixels(bitmap, 2560), preferences.enhance);
      if (photoToken !== token) return;
      const captures = requiresUPCEConfirmation(results, "photo-zxing-wasm") ? [] : selectableCaptures(results, "photo-zxing-wasm");
      const codes = [...new Set(captures.map((x) => x.lookupLexicalValue + "\0" + (x.lookupSymbology || "")))];
      if (codes.length !== 1) return status2(codes.length ? "Several barcodes found. Crop the photo to one product." : results.length ? "Decoder representation needs manual confirmation. Type the printed code." : "No retail barcode found. Use a sharp photo of the entire barcode, including its blank edges.");
      const captureEnvelope = captures[0];
      onCode(captureEnvelope.lookupLexicalValue, {
        captureKind: "photo",
        captureEnvelope,
        originalCaptures: [{ value: captureEnvelope.lookupLexicalValue, symbology: captureEnvelope.lookupSymbology }]
      });
      setLocalizedText($2("scanner-last"), "Accepted from photo: {v0}", { v0: captureEnvelope.lookupLexicalValue });
      status2("Photo accepted \u2713");
    } catch {
      if (photoToken === token) status2("Photo could not be decoded. Try a JPEG/PNG photo or enter the barcode.");
    } finally {
      bitmap?.close();
      if (photoToken === token) {
        closeDecoder();
        $2("scanner-photo").disabled = false;
        if (autoResume && canScan()) void start();
      }
    }
  };
  if ($2("scan")) $2("scan").onclick = () => void start();
  if ($2("stop")) $2("stop").onclick = () => stop();
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stop();
    else if (autoResume && canScan()) void start();
  });
  if (autoResume && navigator.permissions?.query) void navigator.permissions.query({ name: "camera" }).then((p) => p.addEventListener("change", () => {
    if (p.state === "granted" && !document.hidden && canScan()) void start();
  })).catch(() => {
  });
  window.addEventListener("pagehide", () => stop());
  guide();
  preview();
  if (!["environment", "user"].includes(preferences.camera)) $2("scanner-camera").add(new Option("Last used camera", preferences.camera));
  $2("scanner-camera").value = preferences.camera;
  return { stop, start, noteAccepted() {
    if (running) {
      lastRead = performance.now();
      status2("Ready");
    }
  } };
}

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/product-visual-selector.js
var PRODUCT_VISUAL_SELECTOR = "offmenu-product-visual-selector/1";
var APP_ICONS = Object.freeze({ light: "/scanner-balanced-final.svg", dark: "/scanner-balanced-final-dark.svg" });
var object3 = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
function stable3(value) {
  if (Array.isArray(value)) return "[" + value.map(stable3).join(",") + "]";
  if (object3(value)) return "{" + Object.keys(value).sort().map((k) => JSON.stringify(k) + ":" + stable3(value[k])).join(",") + "}";
  return JSON.stringify(value);
}
function exactReference(a, b) {
  return object3(a) && object3(b) && a.schema === "offmenu-identifier-observation/2" && stable3(a) === stable3(b);
}
function validSourceProductReference(value) {
  const named2 = (x) => typeof x === "string" && x.length > 0 && x.length <= 2e3;
  const sha3 = (x) => typeof x === "string" && /^[a-f0-9]{64}$/.test(x);
  const keys2 = (x, list) => object3(x) && Object.keys(x).sort().join("|") === [...list].sort().join("|");
  const ref = value?.sourceReference;
  return keys2(value, ["productId", "sourceId", "releaseId", "archiveSha256", "sourceRow", "auditObservationSha256", "sourceReference"]) && named2(value.productId) && value.sourceId === "off" && named2(value.releaseId) && sha3(value.archiveSha256) && Number.isSafeInteger(value.sourceRow) && value.sourceRow >= 0 && sha3(value.auditObservationSha256) && keys2(ref, ["nativeReference", "storeSha256", "ordinal", "sourcePointer", "rawStoredDocumentSha256", "sourceQualificationSha256", "role"]) && named2(ref.nativeReference) && /^urn:offmenu:product-detail:[a-f0-9]{64}$/.test(ref.nativeReference) && sha3(ref.storeSha256) && Number.isSafeInteger(ref.ordinal) && ref.ordinal >= 0 && named2(ref.sourcePointer) && sha3(ref.rawStoredDocumentSha256) && sha3(ref.sourceQualificationSha256) && named2(ref.role);
}
function exactTypeSource(mapping, input, kind) {
  if (input.sourceProductReference !== void 0) return kind === "type" && input.sourceObservationReference == null && mapping.sourceObservationReference == null && validSourceProductReference(input.sourceProductReference) && validSourceProductReference(mapping.sourceProductReference) && stable3(mapping.sourceProductReference) === stable3(input.sourceProductReference);
  return exactReference(mapping.sourceObservationReference, input.sourceObservationReference);
}
function localAsset(path, permitted) {
  return typeof path === "string" && Array.isArray(permitted) && permitted.includes(path) && /^\/[A-Za-z0-9/_-]+\.(?:svg|png|webp|jpe?g)$/.test(path) && !path.includes("..") && !path.includes("//");
}
function offImageUrl(url) {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" && parsed.hostname === "images.openfoodfacts.org" && parsed.username === "" && parsed.password === "" && parsed.search === "" && parsed.hash === "" && /^\/images\/products\/(?:[0-9]{3}\/)+[0-9]+\/front_[a-z]{2}\.[1-9][0-9]*\.[1-9][0-9]*\.(?:jpg|jpeg|png|webp)$/.test(parsed.pathname) && parsed.href === url;
  } catch {
    return false;
  }
}
function photoSource(candidate, input, failed) {
  if (!object3(candidate) || !exactReference(candidate.sourceObservationReference, input.sourceObservationReference) || candidate.qualification?.state !== "qualified" || candidate.rights?.displayPermitted !== true || typeof input.selectedProductRecordId !== "string" || !input.selectedProductRecordId || candidate.productRecordId !== input.selectedProductRecordId || candidate.role !== "front" || !object3(candidate.provenance) || !candidate.provenance.sourceId || !(candidate.provenance.releaseId || candidate.provenance.releaseId === null && candidate.qualification.scope === "separately-observed-current-publisher-photo-for-exact-OFF-source-code" && candidate.provenance.relationship === "current-publisher-photo; retained-snapshot-image-membership-unverified" && /^\d{4}-\d{2}-\d{2}$/.test(candidate.provenance.evidenceObservedDate)) || !candidate.provenance.imageId || !candidate.provenance.revision || !candidate.rights.license || !candidate.rights.attribution || !candidate.rights.evidenceReference) return null;
  const src = candidate.localAssetPath || candidate.sourceUrl;
  if (typeof src !== "string" || failed.has(src) || !(candidate.localAssetPath ? localAsset(src, input.permittedLocalAssets) : candidate.provenance.sourceId === "off" && offImageUrl(src)) || input.offline === true && (!candidate.localAssetPath || candidate.offlineAvailable !== true)) return null;
  return { src, candidate };
}
function mappedChoice(input, failed, kind = "category") {
  const key = kind === "ingredient" ? "ingredientMappings" : kind === "type" ? "typeMappings" : "categoryMappings";
  if (kind !== "category" && (!input.classificationEvidenceReference || kind === "ingredient" && (input.ingredientApplicability?.state !== "applicable" || !input.ingredientApplicability.evidenceReference))) return null;
  const mappings = (Array.isArray(input[key]) ? input[key] : []).filter((item) => object3(item) && exactTypeSource(item, input, kind) && item.status === "qualified" && item.relation === "exact" && typeof input.selectedProductRecordId === "string" && item.productRecordId === input.selectedProductRecordId && typeof item.conceptId === "string" && item.conceptId && typeof item.taxonomyVersion === "string" && item.taxonomyVersion && typeof item.crosswalkVersion === "string" && item.crosswalkVersion && object3(item.provenance) && object3(item.originalSource) && (kind === "category" || typeof item.provenance.sourceId === "string" && !!item.provenance.sourceId && typeof item.provenance.pointer === "string" && !!item.provenance.pointer) && (typeof item.originalSource.term === "string" && !!item.originalSource.term || typeof item.originalSource.code === "string" && !!item.originalSource.code));
  const ids = new Set(mappings.map((item) => item.taxonomyVersion + "\0" + item.conceptId));
  if (ids.size !== 1) return null;
  const [mapping] = mappings;
  const concepts = (Array.isArray(input.canonicalConcepts) ? input.canonicalConcepts : []).filter((item) => object3(item) && (kind === "category" || item.kind === kind) && item.conceptId === mapping.conceptId && item.taxonomyVersion === mapping.taxonomyVersion && item.definitionStatus === "accepted" && typeof item.preferredEnglishLabel === "string" && item.preferredEnglishLabel.trim());
  if (concepts.length !== 1) return null;
  const concept = concepts[0], presentation = concept.presentation;
  if (presentation?.status !== "approved" || kind !== "category" && !presentation.evidenceReference) return null;
  const title = kind === "ingredient" ? "Ingredient" : kind === "type" ? "Type" : "Category";
  const tier = kind === "category" ? "category-illustration" : kind + "-illustration";
  const evidence = {
    conceptId: concept.conceptId,
    taxonomyVersion: concept.taxonomyVersion,
    preferredEnglishLabel: concept.preferredEnglishLabel,
    ...kind === "category" ? {} : { kind, classificationEvidenceReference: input.classificationEvidenceReference, presentationEvidenceReference: presentation.evidenceReference },
    mappings: mappings.map((item) => ({
      crosswalkVersion: item.crosswalkVersion,
      relation: item.relation,
      originalSource: item.originalSource,
      provenance: item.provenance
    }))
  };
  if (typeof presentation.emoji === "string" && presentation.emoji.length > 0 && Array.from(presentation.emoji).length <= 16 && !/[\x00-\x1f\x7f<>]/.test(presentation.emoji))
    return {
      tier,
      kind: "emoji",
      text: presentation.emoji,
      alt: title + " illustration of " + concept.preferredEnglishLabel + "; not a product photo",
      caption: title + " illustration, not product photo \xB7 emoji appearance varies by platform",
      evidence,
      rights: { presentation: "Unicode emoji; platform appearance varies" }
    };
  const src = presentation.localIconAssetPath;
  if (localAsset(src, input.permittedLocalAssets) && !failed.has(src) && presentation.iconRights?.displayPermitted === true && presentation.iconRights?.evidenceReference && (input.offline !== true || presentation.offlineAvailable === true))
    return {
      tier,
      kind: "image",
      src,
      alt: title + " illustration of " + concept.preferredEnglishLabel + "; not a product photo",
      caption: title + " illustration, not product photo",
      evidence,
      rights: presentation.iconRights
    };
  return null;
}
function selectProductVisual(input, { failedSources = [] } = {}) {
  if (object3(input) && input.sourceProductReference !== void 0) {
    if (input.sourceObservationReference != null || !validSourceProductReference(input.sourceProductReference)) throw new TypeError("Exact retained source product reference required");
    const failed2 = new Set(failedSources);
    return mappedChoice(input, failed2, "type") || appProductVisualFallback(input, { failedSources });
  }
  if (!object3(input) || input.sourceObservationReference?.schema !== "offmenu-identifier-observation/2")
    throw new TypeError("Exact selected source observation required");
  const failed = new Set(failedSources);
  const photos = (input.photoCandidates || []).map((item) => photoSource(item, input, failed)).filter(Boolean);
  const primary = photos.filter((item) => item.candidate.selectionRole === "selected-front");
  const chosen = primary.length === 1 ? primary[0] : photos.length === 1 ? photos[0] : null;
  if (chosen) {
    const { src, candidate } = chosen;
    const name = typeof input.sourceProductName === "string" && input.sourceProductName.trim() ? input.sourceProductName.trim() : "selected source product";
    const nativeAssertion = candidate.qualification.scope === "reviewed-retained-photo-for-explicit-native-source-assertion";
    const currentPublisher = candidate.qualification.scope === "separately-observed-current-publisher-photo-for-exact-OFF-source-code";
    return {
      tier: "product-photo",
      kind: "image",
      src,
      alt: nativeAssertion ? "Photo from the explicitly selected source; product variant match unverified" : currentPublisher ? "Current Open Food Facts photo for source code " + candidate.provenance.sourceCode + "; retained label " + name + "; snapshot image unverified" : "Source product photo for " + name,
      caption: nativeAssertion ? "Selected source photo" : currentPublisher ? "Current publisher photo" : "Source product photo",
      provenance: candidate.provenance,
      rights: candidate.rights,
      identity: { sourceObservationReference: input.sourceObservationReference },
      competingPhotoCount: photos.length
    };
  }
  const illustration = mappedChoice(input, failed, "ingredient") || mappedChoice(input, failed, "type") || mappedChoice(input, failed);
  if (illustration) return illustration;
  return appProductVisualFallback(input, { failedSources });
}
function appProductVisualFallback(input = {}, { failedSources = [] } = {}) {
  const failed = new Set(failedSources);
  const theme = input.theme === "dark" ? "dark" : "light", src = APP_ICONS[theme];
  if (failed.has(src)) return {
    tier: "app-fallback",
    kind: "text",
    text: "OffMenu",
    alt: "OffMenu app fallback; no eligible product photo or category illustration",
    caption: "Product photo unavailable \xB7 no qualified category illustration"
  };
  return {
    tier: "app-fallback",
    kind: "image",
    src,
    alt: "OffMenu app icon; no eligible product photo or category illustration",
    caption: "Product photo unavailable \xB7 no qualified category illustration",
    provenance: { asset: "Selected Balanced Final OffMenu app icon", theme }
  };
}
function afterVisualLoadFailure(input, previous, { failedSources = [] } = {}) {
  if (!previous || previous.kind !== "image" || typeof previous.src !== "string")
    return selectProductVisual(input, { failedSources });
  return selectProductVisual(input, { failedSources: [...failedSources, previous.src] });
}

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/local-retained-category-presentation.js
var stable4 = (x) => Array.isArray(x) ? "[" + x.map(stable4).join(",") + "]" : x && typeof x === "object" ? "{" + Object.keys(x).sort().map((k) => JSON.stringify(k) + ":" + stable4(x[k])).join(",") + "}" : JSON.stringify(x);
var same2 = (a, b) => stable4(a) === stable4(b);
function retainedCategoryAssociation(dto, reference, input = {}, failedSources = []) {
  if (dto?.schema !== "offmenu-local-retained-category-presentation/1" || !validSourceProductReference(reference) || !same2(dto.sourceProductReference, reference)) return null;
  const value = dto.association, type = value?.sourceTypePresentation, visual = value?.visual;
  if (!same2(value?.sourceProductReference, reference) || value.sourceCategoryBinding?.state !== "qualified-source-type" || value.sourceCategoryBinding.semanticIdentity !== false || value.sourceCategoryBinding.currentToHistoricalEquivalence !== false || value.sourceCategoryBinding.ingredientEligibility !== "unresolved" || type?.identityEquivalence !== false || type.productDefinitionEquivalence !== false || type.recipeEligibility !== "unresolved" || type.taxonomySnapshotSHA256 !== dto.taxonomySnapshotSHA256 || dto.categories?.state !== "present" || dto.categories.pointer !== "/data/categories" || dto.categories.evidenceEncoding !== "typed-exact-decimal-json/1; not an original byte-span hash" || !/^[a-f0-9]{64}$/.test(dto.categories.parsedValueEvidenceSha256 || "") || dto.categories.originalSourceAbsenceEstablished !== false) return null;
  const views = value.sourceCategoryBinding.categoryViews;
  if (!Array.isArray(views) || !views.length || views.length !== dto.categories.sourceValue?.length || !views.every((view, index) => view.categoryID === dto.categories.sourceValue[index] && view.snapshotSHA256 === dto.taxonomySnapshotSHA256 && view.type?.id === type.typeID)) return null;
  if (visual?.tier !== "type-illustration" || visual.kind !== "image" || !/^\/source-categories\/icons\/[a-z0-9-]+\.svg$/.test(visual.src || "") || visual.rights?.displayPermitted !== true || !views.every((view) => view.icon?.path === visual.src && view.icon.rightsID === visual.rights.evidenceReference)) return null;
  const result = structuredClone(value);
  if (failedSources.includes(visual.src)) {
    result.visual = appProductVisualFallback(input, { failedSources });
    result.associationState = "unavailable";
  }
  return result;
}

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/retained-source-photo-selection.js
var RETAINED_PHOTO_SELECTION = "offmenu-source-assertion-photo-selection/1";
var RETAINED_PHOTO_SCOPE = "reviewed-retained-photo-for-explicit-native-source-assertion";
var stablePhotoValue = (value) => Array.isArray(value) ? "[" + value.map(stablePhotoValue).join(",") + "]" : value && typeof value === "object" ? "{" + Object.keys(value).sort().map((k) => JSON.stringify(k) + ":" + stablePhotoValue(value[k])).join(",") + "}" : JSON.stringify(value);
var equal = (a, b) => stablePhotoValue(a) === stablePhotoValue(b);
var hex2 = (value) => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
var keys = ["observationKey", "sourceObservation", "sourceBinding", "referenceRecordId", "exactObservationBridge"];
var photoDetailIdentity = (detail) => Object.fromEntries(keys.filter((k) => Object.hasOwn(detail || {}, k)).map((k) => [k, detail[k]]));
function currentPhotoUseMatches(marker, expected, { origin, runtimeSelectionSha256 } = {}) {
  return marker?.state === "qualified" && expected?.state === "qualified" && Object.keys(marker).sort().join(",") === "origin,runtimeSelectionSha256,state,useSelectionRef" && marker.useSelectionRef && Object.keys(marker.useSelectionRef).sort().join(",") === "id,sha256" && typeof marker.useSelectionRef?.id === "string" && marker.useSelectionRef.id.length > 0 && hex2(marker.useSelectionRef.sha256) && hex2(marker.runtimeSelectionSha256) && marker.origin === origin && (!runtimeSelectionSha256 || marker.runtimeSelectionSha256 === runtimeSelectionSha256) && equal(marker, expected);
}
function flatNativePhotoBindingValid(reference, detail) {
  const s = detail?.sourceBinding, o = detail?.sourceObservation, k = detail?.observationKey;
  if (reference?.sourceId !== "off" || reference.namespace !== "barcode" || reference.disposition !== "source-asserted" || typeof detail?.referenceRecordId !== "string" || !detail.referenceRecordId || !s || !o || !k || k.databaseSha256 !== reference.databaseSha256) return false;
  for (const key of ["run_id", "input_id", "record_ordinal", "assertion_id"])
    if (k[key] !== reference.observationKey[key] || o[key] !== reference.observationKey[key]) return false;
  if (o.source_id !== reference.sourceId || o.release_id !== reference.releaseId || o.namespace !== reference.namespace || o.lexical_value !== reference.sourceLexicalValue || o.source_record_id !== reference.sourceRecordId || o.disposition !== "source-asserted" || s.sourceId !== reference.sourceId || s.releaseId !== reference.releaseId || s.identifierInputId !== reference.observationKey.input_id || s.identifierRecordOrdinal !== reference.observationKey.record_ordinal || s.identifierSourceRecordId !== reference.sourceRecordId || o.artifact_sha256 !== s.identifierAssetSha256 || o.native_record_id !== s.identifierNativeRecordId || s.identifierNativeRecordId !== "off:sourceOccurrence:" + s.originalSha256 + ":" + reference.observationKey.record_ordinal) return false;
  for (const key of [
    "originalSha256",
    "recordSha256",
    "identifierAssetSha256",
    "inputAssetSha256",
    "operationReceiptSha256",
    "rightsReceiptSha256",
    "custodyReceiptSha256"
  ]) if (!hex2(s[key])) return false;
  return s.componentDigests && Object.keys(s.componentDigests).length > 0 && Object.values(s.componentDigests).every(hex2);
}
function safePhotoCredits(rights, code2) {
  const urls = [rights?.sourcePage, rights?.photoLicensePage, rights?.licenseUrl, rights?.attributionDetails?.productUrl];
  return urls.every((value) => {
    try {
      const u = new URL(value);
      if (u.protocol !== "https:" || u.username || u.password || u.port || u.hash || u.href !== value) return false;
      if (u.hostname === "creativecommons.org") return /^\/licenses\/by-sa\/3\.0(?:\/deed\.en)?\/?$/.test(u.pathname) && !u.search;
      if (u.hostname !== "world.openfoodfacts.org") return false;
      return u.pathname === "/cgi/product_image.pl" ? u.searchParams.get("code") === code2 && u.searchParams.get("id") === "front_en" && [...u.searchParams.keys()].length === 2 : (u.pathname === "/product/" + code2 || u.pathname.startsWith("/product/" + code2 + "/")) && !u.search;
    } catch {
      return false;
    }
  });
}
function retainedSourcePhotoCandidate(selection, detail, { origin } = {}) {
  const refuse = (reasonCode) => ({ state: "unavailable", reasonCode, candidate: null });
  if (selection?.schema !== RETAINED_PHOTO_SELECTION) return refuse("RETAINED_PHOTO_SELECTION_MISSING");
  const ref = selection.reference;
  if (!validSourceObservationReference(ref, ref?.originalLexicalValue) || !flatNativePhotoBindingValid(ref, selection.detail)) return refuse("RETAINED_PHOTO_NATIVE_REFERENCE_MISSING");
  if (!currentPhotoUseMatches(selection.currentOutputUse, detail?.currentOutputUse, { origin }) || !equal(selection.useSelectionRef, selection.currentOutputUse.useSelectionRef)) return refuse("RETAINED_PHOTO_CURRENT_OUTPUT_USE_UNQUALIFIED");
  const q = selection.qualification;
  if (q?.state !== "qualified" || q.scope !== RETAINED_PHOTO_SCOPE || !hex2(q.adoptionReceiptSha256) || !hex2(q.bindingReviewRef?.sha256)) return refuse("RETAINED_PHOTO_ADOPTION_UNAVAILABLE");
  const matches = (Array.isArray(detail?.sourceAssertions) ? detail.sourceAssertions : []).filter((a) => a && typeof a === "object" && equal(a.sourceObservationReference, ref) && equal(photoDetailIdentity(a.binding), photoDetailIdentity(selection.detail)));
  if (matches.length !== 1) return refuse("RETAINED_PHOTO_EXPLICIT_ASSERTION_MISMATCH");
  const source = selection.detail?.sourceBinding, observation = selection.imageObservation, asset = selection.localAsset;
  if (!source || observation?.sourceCode !== ref.sourceLexicalValue || observation.role !== "front" || !/^front_[a-z]{2}$/.test(observation.selectedKey || "") || !/^[1-9][0-9]*$/.test(observation.revision || "") || !/^[0-9]+$/.test(observation.imageId || "") || !/^[1-9][0-9]*$/.test(observation.resolution || "") || !Number.isInteger(observation.image?.bytes) || observation.image.bytes < 1 || observation.image.type !== "image/jpeg" || observation.sourceLocator?.sourceId !== ref.sourceId || observation.sourceLocator?.releaseId !== ref.releaseId || observation.sourceLocator?.originalSha256 !== source.originalSha256 || observation.sourceLocator?.ordinal !== ref.observationKey.record_ordinal || !hex2(asset?.sha256) || observation.image?.sha256 !== asset.sha256 || asset.type !== "image/jpeg" || typeof asset.path !== "string" || !/^\/api\/off-photos\/[A-Za-z0-9_-]+\.jpg$/.test(asset.path)) return refuse("RETAINED_PHOTO_IMAGE_ASSET_BINDING");
  const rights = selection.rights;
  if (rights?.displayPermitted !== true || !rights.license || !rights.attribution || !rights.evidenceReference || !safePhotoCredits(rights, ref.sourceLexicalValue))
    return refuse("RETAINED_PHOTO_RIGHTS_UNQUALIFIED");
  return { state: "qualified", reasonCode: null, assertion: matches[0], candidate: {
    sourceObservationReference: ref,
    productRecordId: selection.detail.referenceRecordId,
    qualification: q,
    role: "front",
    selectionRole: "selected-front",
    localAssetPath: asset.path,
    offlineAvailable: false,
    provenance: {
      sourceId: ref.sourceId,
      releaseId: ref.releaseId,
      imageId: observation.imageId,
      revision: observation.revision,
      sourceCode: ref.sourceLexicalValue,
      associationScope: "explicit-independent-native-source-assertion",
      relationship: "Current retrieval selected by retained metadata; historical image bytes and primary-product variant match unverified",
      metadataRelease: ref.releaseId,
      retrievedAt: observation.retrievedAt,
      imageSha256: asset.sha256
    },
    rights
  } };
}

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/typed-identifier-contract.mjs
var CITATIONS2 = Object.freeze({
  upce: "https://ref.gs1.org/guidelines/2d-in-retail/1.0.0/",
  jan: "https://www.gs1jp.org/standard/barcode/jan_symbol.html",
  itf14: "https://support.gs1.org/support/solutions/articles/43000734528-what-type-of-gtin-can-be-encoded-in-itf-14-",
  packaging: "https://www.gs1uk.org/knowledge-hub/product-identification/how-do-i-identify-packaging-levels",
  isbnGS1: "https://support.gs1.org/support/solutions/articles/43000734165-how-is-an-isbn-used-in-a-gs1-barcode-",
  isbnAgency: "https://www.isbn-international.org/content/what-isbn/10"
});
var REPRESENTATIONS2 = Object.freeze([
  "GTIN-8",
  "GTIN-12",
  "GTIN-13",
  "GTIN-14",
  "EAN-8",
  "EAN-13",
  "UPC-A",
  "UPC-E",
  "JAN",
  "JAN-8",
  "JAN-13",
  "ISBN-10",
  "ISBN-13"
]);
var WIDTH2 = Object.freeze({
  "GTIN-8": 8,
  "EAN-8": 8,
  "GTIN-12": 12,
  "UPC-A": 12,
  "GTIN-13": 13,
  "EAN-13": 13,
  "GTIN-14": 14
});
var CARRIER_HINT2 = Object.freeze({
  "EAN-8": "EAN-8",
  EAN8: "EAN-8",
  ean_8: "EAN-8",
  "EAN-13": "EAN-13",
  EAN13: "EAN-13",
  ean_13: "EAN-13",
  "UPC-A": "UPC-A",
  UPCA: "UPC-A",
  upc_a: "UPC-A",
  "UPC-E": "UPC-E",
  UPCE: "UPC-E",
  upc_e: "UPC-E",
  "ITF-14": "GTIN-14",
  ITF14: "GTIN-14"
});

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/scanner-kitchen-handoff.js
var PUBLIC_PRODUCT_SELECTION = Object.freeze({ sourceId: "off", releaseId: "offmenu-off-selected-products-20261025-v1", manifestSha256: "1bf09a371a164ebd8215fd9b44a1b2ac9816caaa65cd13504086defad76d4e8f" });

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/locales/ar.js
var ARABIC2 = Object.freeze({
  "Offline resource unavailable": "\u0627\u0644\u0645\u0648\u0631\u062F \u063A\u064A\u0631 \u0645\u062A\u0627\u062D \u062F\u0648\u0646 \u0627\u062A\u0635\u0627\u0644",
  "Translation is stale; showing the original source text.": "\u0627\u0644\u062A\u0631\u062C\u0645\u0629 \u0642\u062F\u064A\u0645\u0629\u061B \u064A\u064F\u0639\u0631\u0636 \u0646\u0635 \u0627\u0644\u0645\u0635\u062F\u0631 \u0627\u0644\u0623\u0635\u0644\u064A.",
  "Common corpus graph loaded for local preview. Source identities, citations and quantities are preserved; nothing is saved.": "\u062A\u0645 \u062A\u062D\u0645\u064A\u0644 \u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0645\u062C\u0645\u0648\u0639\u0629 \u0644\u0644\u0645\u0639\u0627\u064A\u0646\u0629 \u0627\u0644\u0645\u062D\u0644\u064A\u0629. \u062A\u0628\u0642\u0649 \u0647\u0648\u064A\u0627\u062A \u0627\u0644\u0645\u0635\u0627\u062F\u0631 \u0648\u0627\u0644\u0627\u0633\u062A\u0634\u0647\u0627\u062F\u0627\u062A \u0648\u0627\u0644\u0643\u0645\u064A\u0627\u062A \u0643\u0645\u0627 \u0647\u064A\u061B \u0644\u0645 \u062A\u064F\u062D\u0641\u0638 \u0623\u064A \u062A\u063A\u064A\u064A\u0631\u0627\u062A.",
  "Return to offmenu": "\u0627\u0644\u0639\u0648\u062F\u0629 \u0625\u0644\u0649 offmenu",
  "Returning to offmenu\u2026": "\u062C\u0627\u0631\u064D \u0627\u0644\u0639\u0648\u062F\u0629 \u0625\u0644\u0649 offmenu\u2026",
  "Open offmenu": "\u0627\u0641\u062A\u062D offmenu",
  "Yes": "\u0646\u0639\u0645",
  "No": "\u0644\u0627",
  "Unknown unit": "\u0648\u062D\u062F\u0629 \u063A\u064A\u0631 \u0645\u0639\u0631\u0648\u0641\u0629",
  "Kitchen inventory": "\u0645\u062E\u0632\u0648\u0646 \u0627\u0644\u0645\u0637\u0628\u062E",
  "Home checkout receipt": "\u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636 \u0627\u0644\u0645\u0646\u0632\u0644",
  "Household menus & recipe booklet": "\u0648\u062C\u0628\u0627\u062A \u0627\u0644\u0623\u0633\u0631\u0629 \u0648\u0643\u062A\u064A\u0651\u0628 \u0627\u0644\u0648\u0635\u0641\u0627\u062A",
  "Meal-plan shopping list": "\u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u062A\u0633\u0648\u0651\u0642 \u0644\u062E\u0637\u0629 \u0627\u0644\u0648\u062C\u0628\u0627\u062A",
  "Household preferences": "\u062A\u0641\u0636\u064A\u0644\u0627\u062A \u0627\u0644\u0623\u0633\u0631\u0629",
  "Food history & nutrition": "\u0633\u062C\u0644 \u0627\u0644\u0637\u0639\u0627\u0645 \u0648\u0627\u0644\u062A\u063A\u0630\u064A\u0629",
  "Waste & freshness report": "\u062A\u0642\u0631\u064A\u0631 \u0627\u0644\u0647\u062F\u0631 \u0648\u062D\u0627\u0644\u0629 \u0627\u0644\u0637\u0639\u0627\u0645",
  "Product": "\u0627\u0644\u0645\u0646\u062A\u062C",
  "Amount": "\u0627\u0644\u0643\u0645\u064A\u0629",
  "Recipe ingredient": "\u0645\u0643\u0648\u0651\u0646 \u0627\u0644\u0648\u0635\u0641\u0629",
  "Expiry": "\u062A\u0627\u0631\u064A\u062E \u0627\u0644\u0627\u0646\u062A\u0647\u0627\u0621",
  "Directions": "\u0627\u0644\u0637\u0631\u064A\u0642\u0629",
  "Contents": "\u0627\u0644\u0645\u062D\u062A\u0648\u064A\u0627\u062A",
  "Recipes indexed: {count}": {
    zero: "\u0644\u0627 \u0648\u0635\u0641\u0627\u062A \u0645\u0641\u0647\u0631\u0633\u0629 ({count})",
    one: "\u0648\u0635\u0641\u0629 \u0648\u0627\u062D\u062F\u0629 \u0645\u0641\u0647\u0631\u0633\u0629 ({count})",
    two: "\u0648\u0635\u0641\u062A\u0627\u0646 \u0645\u0641\u0647\u0631\u0633\u062A\u0627\u0646 ({count})",
    few: "{count} \u0648\u0635\u0641\u0627\u062A \u0645\u0641\u0647\u0631\u0633\u0629",
    many: "{count} \u0648\u0635\u0641\u0629 \u0645\u0641\u0647\u0631\u0633\u0629",
    other: "\u0648\u0635\u0641\u0627\u062A \u0645\u0641\u0647\u0631\u0633\u0629: {count}"
  },
  "Translation unavailable; showing the original source text.": "\u0627\u0644\u062A\u0631\u062C\u0645\u0629 \u063A\u064A\u0631 \u0645\u062A\u0627\u062D\u0629\u061B \u064A\u064F\u0639\u0631\u0636 \u0646\u0635 \u0627\u0644\u0645\u0635\u062F\u0631 \u0627\u0644\u0623\u0635\u0644\u064A.",
  "Same as interface language": "\u0645\u062B\u0644 \u0644\u063A\u0629 \u0627\u0644\u0648\u0627\u062C\u0647\u0629",
  "Arabic when supplied": "\u0627\u0644\u0639\u0631\u0628\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627",
  "Japanese when supplied": "\u0627\u0644\u064A\u0627\u0628\u0627\u0646\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627",
  "English when supplied": "\u0627\u0644\u0625\u0646\u062C\u0644\u064A\u0632\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627",
  "French when supplied": "\u0627\u0644\u0641\u0631\u0646\u0633\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627",
  "German when supplied": "\u0627\u0644\u0623\u0644\u0645\u0627\u0646\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627",
  "Chinese when supplied": "\u0627\u0644\u0635\u064A\u0646\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627",
  "Hindi when supplied": "\u0627\u0644\u0647\u0646\u062F\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627",
  "Indonesian when supplied": "\u0627\u0644\u0625\u0646\u062F\u0648\u0646\u064A\u0633\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627",
  "Russian when supplied": "\u0627\u0644\u0631\u0648\u0633\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627",
  "Original source language": "\u0644\u063A\u0629 \u0627\u0644\u0645\u0635\u062F\u0631 \u0627\u0644\u0623\u0635\u0644\u064A\u0629",
  "Food-name display language": "\u0644\u063A\u0629 \u0639\u0631\u0636 \u0623\u0633\u0645\u0627\u0621 \u0627\u0644\u0623\u0637\u0639\u0645\u0629",
  "All languages": "\u062C\u0645\u064A\u0639 \u0627\u0644\u0644\u063A\u0627\u062A",
  "Recipe language": "\u0644\u063A\u0629 \u0627\u0644\u0648\u0635\u0641\u0629",
  "RECIPES FROM AROUND THE WORLD": "\u0648\u0635\u0641\u0627\u062A \u0645\u0646 \u0623\u0646\u062D\u0627\u0621 \u0627\u0644\u0639\u0627\u0644\u0645",
  "Explore the shared recipe library.": "\u0627\u0633\u062A\u0643\u0634\u0641 \u0645\u0643\u062A\u0628\u0629 \u0627\u0644\u0648\u0635\u0641\u0627\u062A \u0627\u0644\u0645\u0634\u062A\u0631\u0643\u0629.",
  "Open worldwide recipes": "\u0627\u0641\u062A\u062D \u0648\u0635\u0641\u0627\u062A \u0627\u0644\u0639\u0627\u0644\u0645",
  "Dish or ingredients": "\u0627\u0644\u0637\u0628\u0642 \u0623\u0648 \u0627\u0644\u0645\u0643\u0648\u0651\u0646\u0627\u062A",
  "Original source": "\u0627\u0644\u0645\u0635\u062F\u0631 \u0627\u0644\u0623\u0635\u0644\u064A",
  "Prioritise recipes using my available ingredients": "\u0623\u0639\u0637\u0650 \u0627\u0644\u0623\u0648\u0644\u0648\u064A\u0629 \u0644\u0644\u0648\u0635\u0641\u0627\u062A \u0627\u0644\u062A\u064A \u062A\u0633\u062A\u062E\u062F\u0645 \u0645\u0643\u0648\u0651\u0646\u0627\u062A\u064A \u0627\u0644\u0645\u062A\u0627\u062D\u0629",
  "Shared recipes are available to everyone. Your pantry matching runs on this device.": "\u0627\u0644\u0648\u0635\u0641\u0627\u062A \u0627\u0644\u0645\u0634\u062A\u0631\u0643\u0629 \u0645\u062A\u0627\u062D\u0629 \u0644\u0644\u062C\u0645\u064A\u0639. \u062A\u064F\u0637\u0627\u0628\u064E\u0642 \u0645\u0639 \u0645\u062E\u0632\u0648\u0646\u0643 \u0639\u0644\u0649 \u0647\u0630\u0627 \u0627\u0644\u062C\u0647\u0627\u0632.",
  "A little room for possibility.": "\u0645\u0633\u0627\u062D\u0629 \u0635\u063A\u064A\u0631\u0629 \u0644\u0623\u0641\u0643\u0627\u0631 \u062C\u062F\u064A\u062F\u0629.",
  "Choose a shelf and scan your first items through checkout.": "\u0627\u062E\u062A\u0631 \u0631\u0641\u064B\u0627 \u0648\u0627\u0645\u0633\u062D \u0623\u0635\u0646\u0627\u0641\u0643 \u0627\u0644\u0623\u0648\u0644\u0649 \u0644\u0625\u0636\u0627\u0641\u062A\u0647\u0627 \u0625\u0644\u0649 \u0627\u0644\u0642\u0627\u0626\u0645\u0629.",
  "offmenu \xB7 A little checkout. A better stocked home.": "offmenu \xB7 \u0642\u0627\u0626\u0645\u0629 \u0628\u0633\u064A\u0637\u0629. \u0648\u0645\u062E\u0632\u0648\u0646 \u0645\u0646\u0632\u0644\u064A \u0623\u0641\u0636\u0644.",
  "Pantry, fridge or freezer. One satisfying": "\u062E\u0632\u0627\u0646\u0629 \u0627\u0644\u0637\u0639\u0627\u0645 \u0623\u0648 \u0627\u0644\u062B\u0644\u0627\u062C\u0629 \u0623\u0648 \u0627\u0644\u0645\u062C\u0645\u0651\u062F. \u062A\u0646\u0628\u064A\u0647",
  "beep": "\u0644\u0637\u064A\u0641",
  "at a time.": "\u0645\u0639 \u0643\u0644 \u0635\u0646\u0641.",
  "THE HOME CHECKOUT CLUB": "\u0646\u0627\u062F\u064A \u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636 \u0627\u0644\u0645\u0646\u0632\u0644",
  "EST. RIGHT NOW": "\u0627\u0628\u062F\u0623 \u0627\u0644\u0622\u0646",
  "Oh, so that\u2019s what\u2019s": "\u0625\u0630\u064B\u0627 \u0647\u0630\u0627 \u0645\u0627 \u0643\u0627\u0646",
  "at the back of the shelf.": "\u0641\u064A \u0622\u062E\u0631 \u0627\u0644\u0631\u0641.",
  "HELLO, KITCHEN.": "\u0645\u0631\u062D\u0628\u064B\u0627 \u064A\u0627 \u0645\u0637\u0628\u062E.",
  "3 items \xB7 endless possibilities": "\u0663 \u0623\u0635\u0646\u0627\u0641 \xB7 \u0623\u0641\u0643\u0627\u0631 \u0644\u0627 \u062D\u0635\u0631 \u0644\u0647\u0627",
  "THE GOOD": "\u0627\u0644\u0637\u0639\u0627\u0645",
  "STUFF": "\u0627\u0644\u062C\u064A\u0651\u062F",
  "YOUR KITCHEN": "\u0645\u0637\u0628\u062E\u0643",
  "A little inspiration": "\u0642\u0644\u064A\u0644 \u0645\u0646 \u0627\u0644\u0625\u0644\u0647\u0627\u0645",
  "ALREADY YOURS \u2713": "\u0644\u062F\u064A\u0643 \u0628\u0627\u0644\u0641\u0639\u0644 \u2713",
  "\u25CE See what\u2019s hiding": "\u25CE \u0627\u0643\u062A\u0634\u0641 \u0645\u0627 \u0644\u062F\u064A\u0643",
  "\u25A5 Make space for good food": "\u25A5 \u062E\u0635\u0651\u0635 \u0645\u0633\u0627\u062D\u0629 \u0644\u0644\u0637\u0639\u0627\u0645 \u0627\u0644\u062C\u064A\u0651\u062F",
  "\u2733 Find your next meal": "\u2733 \u0627\u062E\u062A\u0631 \u0648\u062C\u0628\u062A\u0643 \u0627\u0644\u062A\u0627\u0644\u064A\u0629",
  "A little more play. A little less \u201Cwhat\u2019s for dinner?\u201D": "\u0645\u062A\u0639\u0629 \u0623\u0643\u062B\u0631 \u0648\u062D\u064A\u0631\u0629 \u0623\u0642\u0644 \u0628\u0634\u0623\u0646 \u0627\u0644\u0639\u0634\u0627\u0621.",
  "Illustration of the offmenu home checkout": "\u0631\u0633\u0645 \u062A\u0648\u0636\u064A\u062D\u064A \u0644\u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636 \u0627\u0644\u0645\u0646\u0632\u0644 \u0641\u064A offmenu",
  "Turn shelf-by-shelf inventory into a little checkout ritual. Scan your pantry, fridge and freezer, then discover what to cook.": "\u062D\u0648\u0651\u0644 \u062C\u0631\u062F \u0627\u0644\u0631\u0641\u0648\u0641 \u0625\u0644\u0649 \u0639\u0627\u062F\u0629 \u0628\u0633\u064A\u0637\u0629. \u0627\u0645\u0633\u062D \u062E\u0632\u0627\u0646\u0629 \u0627\u0644\u0637\u0639\u0627\u0645 \u0648\u0627\u0644\u062B\u0644\u0627\u062C\u0629 \u0648\u0627\u0644\u0645\u062C\u0645\u0651\u062F\u060C \u062B\u0645 \u0627\u0643\u062A\u0634\u0641 \u0645\u0627 \u064A\u0645\u0643\u0646\u0643 \u0637\u0647\u064A\u0647.",
  "Interface language": "\u0644\u063A\u0629 \u0627\u0644\u0648\u0627\u062C\u0647\u0629",
  "Interface language is saved on this device. Recipes and food names keep their source language.": "\u062A\u064F\u062D\u0641\u0638 \u0644\u063A\u0629 \u0627\u0644\u0648\u0627\u062C\u0647\u0629 \u0639\u0644\u0649 \u0647\u0630\u0627 \u0627\u0644\u062C\u0647\u0627\u0632. \u062A\u062D\u062A\u0641\u0638 \u0627\u0644\u0648\u0635\u0641\u0627\u062A \u0648\u0623\u0633\u0645\u0627\u0621 \u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0628\u0644\u063A\u062A\u0647\u0627 \u0627\u0644\u0623\u0635\u0644\u064A\u0629.",
  "Skip to kitchen": "\u0627\u0646\u062A\u0642\u0644 \u0625\u0644\u0649 \u0627\u0644\u0645\u0637\u0628\u062E",
  "Global data": "\u0627\u0644\u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0639\u0627\u0644\u0645\u064A\u0629",
  "How it works": "\u0643\u064A\u0641 \u064A\u0639\u0645\u0644",
  "Log in": "\u062A\u0633\u062C\u064A\u0644 \u0627\u0644\u062F\u062E\u0648\u0644",
  "My kitchen \u2197": "\u0645\u0637\u0628\u062E\u064A \u2197",
  "YOUR KITCHEN. YOUR CHECKOUT.": "\u0645\u0637\u0628\u062E\u0643. \u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636\u0643.",
  "Dinner starts": "\u064A\u0628\u062F\u0623 \u0627\u0644\u0639\u0634\u0627\u0621",
  "with what you": "\u0628\u0645\u0627 \u0644\u062F\u064A\u0643",
  "already have.": "\u0628\u0627\u0644\u0641\u0639\u0644.",
  "Scan a few foods, find meals that fit your household, and buy only what\u2019s missing. Start with five foods or one shelf.": "\u0627\u0645\u0633\u062D \u0628\u0639\u0636 \u0627\u0644\u0623\u0637\u0639\u0645\u0629\u060C \u0648\u0627\u0639\u062B\u0631 \u0639\u0644\u0649 \u0648\u062C\u0628\u0627\u062A \u062A\u0646\u0627\u0633\u0628 \u0623\u0633\u0631\u062A\u0643\u060C \u0648\u0627\u0634\u062A\u0631\u0650 \u0645\u0627 \u064A\u0646\u0642\u0635\u0643 \u0641\u0642\u0637. \u0627\u0628\u062F\u0623 \u0628\u062E\u0645\u0633\u0629 \u0623\u0635\u0646\u0627\u0641 \u0623\u0648 \u0631\u0641 \u0648\u0627\u062D\u062F.",
  "Add my first food": "\u0623\u0636\u0641 \u0623\u0648\u0644 \u0637\u0639\u0627\u0645",
  "Try a kitchen": "\u062C\u0631\u0651\u0628 \u0645\u0637\u0628\u062E\u064B\u0627",
  "A SMALL RITUAL. A FRESH START.": "\u0639\u0627\u062F\u0629 \u0628\u0633\u064A\u0637\u0629. \u0628\u062F\u0627\u064A\u0629 \u062C\u062F\u064A\u062F\u0629.",
  "Give your kitchen": "\u0627\u0645\u0646\u062D \u0645\u0637\u0628\u062E\u0643",
  "a little shelf respect.": "\u0628\u0639\u0636 \u0627\u0644\u0639\u0646\u0627\u064A\u0629 \u0628\u0631\u0641\u0648\u0641\u0647.",
  "No whole-house marathon required.": "\u0644\u0627 \u062A\u062D\u062A\u0627\u062C \u0625\u0644\u0649 \u062A\u0631\u062A\u064A\u0628 \u0627\u0644\u0645\u0646\u0632\u0644 \u0643\u0644\u0647.",
  "Just one shelf and a clear bit of bench.": "\u064A\u0643\u0641\u064A \u0631\u0641 \u0648\u0627\u062D\u062F \u0648\u0645\u0633\u0627\u062D\u0629 \u062E\u0627\u0644\u064A\u0629 \u0639\u0644\u0649 \u0627\u0644\u0637\u0627\u0648\u0644\u0629.",
  "Clear a shelf.": "\u0623\u0641\u0631\u063A \u0631\u0641\u064B\u0627.",
  "Pick your pantry, fridge or freezer. Put its contents on the bench so you can see what\u2019s there.": "\u0627\u062E\u062A\u0631 \u062E\u0632\u0627\u0646\u0629 \u0627\u0644\u0637\u0639\u0627\u0645 \u0623\u0648 \u0627\u0644\u062B\u0644\u0627\u062C\u0629 \u0623\u0648 \u0627\u0644\u0645\u062C\u0645\u0651\u062F. \u0636\u0639 \u0645\u062D\u062A\u0648\u064A\u0627\u062A\u0647 \u0639\u0644\u0649 \u0627\u0644\u0637\u0627\u0648\u0644\u0629 \u0644\u062A\u0631\u0649 \u0645\u0627 \u0644\u062F\u064A\u0643.",
  "Play shopkeeper.": "\u0627\u0645\u0633\u062D \u0623\u063A\u0631\u0627\u0636\u0643.",
  "Scan each item straight onto your receipt. Glance at nutrition and enjoy the beep. Review it all at the end.": "\u0627\u0645\u0633\u062D \u0643\u0644 \u0635\u0646\u0641 \u0644\u0625\u0636\u0627\u0641\u062A\u0647 \u0625\u0644\u0649 \u0642\u0627\u0626\u0645\u062A\u0643. \u0627\u0637\u0651\u0644\u0639 \u0639\u0644\u0649 \u0628\u064A\u0627\u0646\u0627\u062A\u0647 \u0627\u0644\u063A\u0630\u0627\u0626\u064A\u0629 \u062B\u0645 \u0631\u0627\u062C\u0639 \u0627\u0644\u0642\u0627\u0626\u0645\u0629 \u0641\u064A \u0627\u0644\u0646\u0647\u0627\u064A\u0629.",
  "Put the good stuff back.": "\u0623\u0639\u062F \u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0625\u0644\u0649 \u0645\u0643\u0627\u0646\u0647\u0627.",
  "Review your receipt, update that shelf, then find a meal that starts with what you have.": "\u0631\u0627\u062C\u0639 \u0642\u0627\u0626\u0645\u062A\u0643 \u0648\u062D\u062F\u0651\u062B \u0627\u0644\u0631\u0641\u060C \u062B\u0645 \u0627\u062E\u062A\u0631 \u0648\u062C\u0628\u0629 \u0645\u0646 \u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0627\u0644\u0645\u0648\u062C\u0648\u062F\u0629 \u0644\u062F\u064A\u0643.",
  "FRESH FROM THE SHOP": "\u0645\u0646 \u0627\u0644\u0645\u062A\u062C\u0631 \u0625\u0644\u0649 \u0645\u0637\u0628\u062E\u0643",
  "Shopping bags in.": "\u0623\u062D\u0636\u0631\u062A \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A.",
  "Kitchen sorted.": "\u0648\u0627\u0644\u0622\u0646 \u0631\u062A\u0651\u0628 \u0627\u0644\u0645\u0637\u0628\u062E.",
  "Give new groceries the same checkout treatment before putting them away. Add to your shelves as you unpack.": "\u0627\u0645\u0633\u062D \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A \u0627\u0644\u062C\u062F\u064A\u062F\u0629 \u0642\u0628\u0644 \u062A\u062E\u0632\u064A\u0646\u0647\u0627\u060C \u0648\u0623\u0636\u0641\u0647\u0627 \u0625\u0644\u0649 \u0631\u0641\u0648\u0641\u0643 \u0623\u062B\u0646\u0627\u0621 \u062A\u0641\u0631\u064A\u063A \u0627\u0644\u0623\u0643\u064A\u0627\u0633.",
  "Try an unpacking run \u2197": "\u062C\u0631\u0651\u0628 \u0625\u0636\u0627\u0641\u0629 \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A \u2197",
  "Product information from Open Food Facts. Always check the package for allergens.": "\u0645\u0639\u0644\u0648\u0645\u0627\u062A \u0627\u0644\u0645\u0646\u062A\u062C\u0627\u062A \u0645\u0646 Open Food Facts. \u062A\u062D\u0642\u0651\u0642 \u062F\u0627\u0626\u0645\u064B\u0627 \u0645\u0646 \u0627\u0644\u0639\u0628\u0648\u0629 \u0644\u0645\u0639\u0631\u0641\u0629 \u0645\u0633\u0628\u0651\u0628\u0627\u062A \u0627\u0644\u062D\u0633\u0627\u0633\u064A\u0629.",
  "YOUR HOME CHECKOUT": "\u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636 \u0645\u0637\u0628\u062E\u0643",
  "Let\u2019s take stock.": "\u0644\u0646\u0631\u0627\u062C\u0639 \u0645\u0627 \u0644\u062F\u064A\u0646\u0627.",
  "DEMO \xB7 SAMPLE PRODUCTS": "\u062A\u062C\u0631\u0628\u0629 \xB7 \u0645\u0646\u062A\u062C\u0627\u062A \u0646\u0645\u0648\u0630\u062C\u064A\u0629",
  "\u266A Sound off": "\u266A \u0627\u0644\u0635\u0648\u062A \u0645\u062A\u0648\u0642\u0641",
  "\u266A Sound on": "\u266A \u0627\u0644\u0635\u0648\u062A \u0645\u0641\u0639\u0651\u0644",
  "Scan feedback \u2733": "\u062A\u0646\u0628\u064A\u0647\u0627\u062A \u0627\u0644\u0645\u0633\u062D \u2733",
  "Profile & backup": "\u0627\u0644\u0645\u0644\u0641 \u0627\u0644\u0634\u062E\u0635\u064A \u0648\u0627\u0644\u0646\u0633\u062E \u0627\u0644\u0627\u062D\u062A\u064A\u0627\u0637\u064A",
  "Exit demo": "\u0625\u0646\u0647\u0627\u0621 \u0627\u0644\u062A\u062C\u0631\u0628\u0629",
  "\u2733 Today": "\u2733 \u0627\u0644\u064A\u0648\u0645",
  "\u25A4 Kitchen": "\u25A4 \u0627\u0644\u0645\u0637\u0628\u062E",
  "\u25A6 Plan": "\u25A6 \u0627\u0644\u062E\u0637\u0629",
  "\u25C7 Shop": "\u25C7 \u0627\u0644\u062A\u0633\u0648\u0651\u0642",
  "\u2667 Me": "\u2667 \u062D\u0633\u0627\u0628\u064A",
  "\u25A5 Scan groceries": "\u25A5 \u0627\u0645\u0633\u062D \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A",
  "+ Add food": "+ \u0623\u0636\u0641 \u0637\u0639\u0627\u0645\u064B\u0627",
  "Saved on this device": "\u0645\u062D\u0641\u0648\u0638 \u0639\u0644\u0649 \u0647\u0630\u0627 \u0627\u0644\u062C\u0647\u0627\u0632",
  "YOUR KITCHEN, YOUR WAY": "\u0645\u0637\u0628\u062E\u0643 \u0643\u0645\u0627 \u062A\u062D\u0628",
  "People, preferences & progress.": "\u0627\u0644\u0623\u0634\u062E\u0627\u0635 \u0648\u0627\u0644\u062A\u0641\u0636\u064A\u0644\u0627\u062A \u0648\u0627\u0644\u062A\u0642\u062F\u0651\u0645.",
  "\u2667 Dietary profiles": "\u2667 \u0627\u0644\u0645\u0644\u0641\u0627\u062A \u0627\u0644\u063A\u0630\u0627\u0626\u064A\u0629",
  "\u25F7 Statistics & history": "\u25F7 \u0627\u0644\u0625\u062D\u0635\u0627\u0621\u0627\u062A \u0648\u0627\u0644\u0633\u062C\u0644",
  "\u25A4 Printable documents & Kindle": "\u25A4 \u0645\u0633\u062A\u0646\u062F\u0627\u062A \u0644\u0644\u0637\u0628\u0627\u0639\u0629 \u0648Kindle",
  "Account & backup": "\u0627\u0644\u062D\u0633\u0627\u0628 \u0648\u0627\u0644\u0646\u0633\u062E \u0627\u0644\u0627\u062D\u062A\u064A\u0627\u0637\u064A",
  "Connections & developers": "\u0627\u0644\u0627\u062A\u0635\u0627\u0644\u0627\u062A \u0648\u0627\u0644\u0645\u0637\u0648\u0651\u0631\u0648\u0646",
  "Large text": "\u0646\u0635 \u0643\u0628\u064A\u0631",
  "Quiet mode \xB7 disable scan effects": "\u0627\u0644\u0648\u0636\u0639 \u0627\u0644\u0647\u0627\u062F\u0626 \xB7 \u062A\u0639\u0637\u064A\u0644 \u0645\u0624\u062B\u0631\u0627\u062A \u0627\u0644\u0645\u0633\u062D",
  "People sharing this kitchen": "\u0627\u0644\u0623\u0634\u062E\u0627\u0635 \u0627\u0644\u0645\u0634\u0627\u0631\u0643\u0648\u0646 \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u0637\u0628\u062E",
  "Trust, privacy & support": "\u0627\u0644\u062B\u0642\u0629 \u0648\u0627\u0644\u062E\u0635\u0648\u0635\u064A\u0629 \u0648\u0627\u0644\u062F\u0639\u0645",
  "Clear this device\u2019s account data": "\u0627\u0645\u0633\u062D \u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u062D\u0633\u0627\u0628 \u0645\u0646 \u0647\u0630\u0627 \u0627\u0644\u062C\u0647\u0627\u0632",
  "PICK YOUR NEXT LITTLE WIN": "\u0627\u062E\u062A\u0631 \u062E\u0637\u0648\u062A\u0643 \u0627\u0644\u062A\u0627\u0644\u064A\u0629",
  "What\u2019s on the bench?": "\u0645\u0627\u0630\u0627 \u0639\u0644\u0649 \u0627\u0644\u0637\u0627\u0648\u0644\u0629\u061F",
  "\u25A4 Rebuild a shelf": "\u25A4 \u0631\u062A\u0651\u0628 \u0631\u0641\u064B\u0627",
  "\u2672 Garbage scan": "\u2672 \u0627\u0645\u0633\u062D \u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0644\u0644\u062A\u062E\u0644\u0651\u0635 \u0645\u0646\u0647\u0627",
  "\u{1F6CD} Unpack shopping": "\u{1F6CD} \u0623\u0636\u0641 \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A",
  "Pantry": "\u062E\u0632\u0627\u0646\u0629 \u0627\u0644\u0637\u0639\u0627\u0645",
  "Fridge": "\u0627\u0644\u062B\u0644\u0627\u062C\u0629",
  "Freezer": "\u0627\u0644\u0645\u062C\u0645\u0651\u062F",
  "Dry goods & everyday staples": "\u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0627\u0644\u062C\u0627\u0641\u0629 \u0648\u0627\u0644\u0645\u0648\u0627\u062F \u0627\u0644\u0623\u0633\u0627\u0633\u064A\u0629",
  "Fresh things & leftovers": "\u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0627\u0644\u0637\u0627\u0632\u062C\u0629 \u0648\u0628\u0642\u0627\u064A\u0627 \u0627\u0644\u0648\u062C\u0628\u0627\u062A",
  "Future-you\u2019s favourite food": "\u0623\u0637\u0639\u0645\u0629 \u0645\u062D\u0641\u0648\u0638\u0629 \u0644\u0644\u0623\u064A\u0627\u0645 \u0627\u0644\u0642\u0627\u062F\u0645\u0629",
  "Storage area": "\u0645\u0643\u0627\u0646 \u0627\u0644\u062A\u062E\u0632\u064A\u0646",
  "Shelf / container": "\u0627\u0644\u0631\u0641 \u0623\u0648 \u0627\u0644\u062D\u0627\u0648\u064A\u0629",
  "e.g. Bench": "\u0645\u062B\u0644: \u0627\u0644\u0637\u0627\u0648\u0644\u0629",
  "e.g. Top shelf": "\u0645\u062B\u0644: \u0627\u0644\u0631\u0641 \u0627\u0644\u0639\u0644\u0648\u064A",
  "Clear this shelf onto your bench. Its current inventory stays intact until you review and finish.": "\u0623\u0641\u0631\u063A \u0645\u062D\u062A\u0648\u064A\u0627\u062A \u0647\u0630\u0627 \u0627\u0644\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0637\u0627\u0648\u0644\u0629. \u0644\u0646 \u064A\u062A\u063A\u064A\u0651\u0631 \u0645\u062E\u0632\u0648\u0646\u0647 \u062D\u062A\u0649 \u062A\u0631\u0627\u062C\u0639 \u0627\u0644\u0642\u0627\u0626\u0645\u0629 \u0648\u062A\u0646\u0647\u064A \u0627\u0644\u0639\u0645\u0644\u064A\u0629.",
  "Choose the source location. Scan items you are discarding; review the removal receipt before the inventory changes.": "\u0627\u062E\u062A\u0631 \u0645\u0643\u0627\u0646 \u0627\u0644\u062A\u062E\u0632\u064A\u0646. \u0627\u0645\u0633\u062D \u0627\u0644\u0623\u0635\u0646\u0627\u0641 \u0627\u0644\u062A\u064A \u0633\u062A\u062A\u062E\u0644\u0651\u0635 \u0645\u0646\u0647\u0627\u060C \u0648\u0631\u0627\u062C\u0639 \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0625\u0632\u0627\u0644\u0629 \u0642\u0628\u0644 \u062A\u063A\u064A\u064A\u0631 \u0627\u0644\u0645\u062E\u0632\u0648\u0646.",
  "Choose where these groceries will go. Scan one destination at a time, then add them to the items already there.": "\u0627\u062E\u062A\u0631 \u0645\u0643\u0627\u0646 \u0647\u0630\u0647 \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A. \u0627\u0645\u0633\u062D \u0627\u0644\u0623\u0635\u0646\u0627\u0641 \u0644\u0643\u0644 \u0645\u0643\u0627\u0646 \u0639\u0644\u0649 \u062D\u062F\u0629\u060C \u062B\u0645 \u0623\u0636\u0641\u0647\u0627 \u0625\u0644\u0649 \u0627\u0644\u0645\u0648\u062C\u0648\u062F \u0641\u064A\u0647.",
  "Open my checkout \u2197": "\u0627\u0628\u062F\u0623 \u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636\u064A \u2197",
  "SHELF RESET": "\u0625\u0639\u0627\u062F\u0629 \u062A\u0631\u062A\u064A\u0628 \u0627\u0644\u0631\u0641",
  "GARBAGE \xB7 SOURCE LOCATION": "\u0627\u0644\u062A\u062E\u0644\u0651\u0635 \u0645\u0646 \u0627\u0644\u0637\u0639\u0627\u0645 \xB7 \u0645\u0643\u0627\u0646 \u0627\u0644\u062A\u062E\u0632\u064A\u0646",
  "GROCERY UNPACKING": "\u0625\u0636\u0627\u0641\u0629 \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A",
  "Scan, check, then put it back.": "\u0627\u0645\u0633\u062D \u0648\u062A\u062D\u0642\u0651\u0642 \u062B\u0645 \u0623\u0639\u062F\u0647 \u0625\u0644\u0649 \u0645\u0643\u0627\u0646\u0647.",
  "Pause & choose another shelf": "\u062A\u0648\u0642\u0651\u0641 \u0648\u0627\u062E\u062A\u0631 \u0631\u0641\u064B\u0627 \u0622\u062E\u0631",
  "CHECKOUT OPEN": "\u0627\u0644\u0642\u0627\u0626\u0645\u0629 \u0645\u0641\u062A\u0648\u062D\u0629",
  "Next item, please.": "\u0627\u0644\u0635\u0646\u0641 \u0627\u0644\u062A\u0627\u0644\u064A\u060C \u0645\u0646 \u0641\u0636\u0644\u0643.",
  "Your bench \u2192 your shelf": "\u0645\u0646 \u0627\u0644\u0637\u0627\u0648\u0644\u0629 \u2190 \u0625\u0644\u0649 \u0627\u0644\u0631\u0641",
  "ITEMS": "\u0623\u0635\u0646\u0627\u0641",
  "THE SCANNING SPOT": "\u0645\u0646\u0637\u0642\u0629 \u0627\u0644\u0645\u0633\u062D",
  "Bring on the beeps.": "\u0644\u0646\u0628\u062F\u0623 \u0627\u0644\u0645\u0633\u062D.",
  "Scan next demo item \u25A5": "\u0627\u0645\u0633\u062D \u0627\u0644\u0635\u0646\u0641 \u0627\u0644\u062A\u062C\u0631\u064A\u0628\u064A \u0627\u0644\u062A\u0627\u0644\u064A \u25A5",
  "How are you scanning?": "\u0643\u064A\u0641 \u062A\u0631\u064A\u062F \u0627\u0644\u0645\u0633\u062D\u061F",
  "Handheld \xB7 rear camera": "\u0628\u0627\u0644\u064A\u062F \xB7 \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u062E\u0644\u0641\u064A\u0629",
  "Screen-up bench \xB7 front camera": "\u0639\u0644\u0649 \u0627\u0644\u0637\u0627\u0648\u0644\u0629 \u0648\u0627\u0644\u0634\u0627\u0634\u0629 \u0644\u0644\u0623\u0639\u0644\u0649 \xB7 \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u0623\u0645\u0627\u0645\u064A\u0629",
  "Hands-free stand \xB7 rear camera": "\u0639\u0644\u0649 \u062D\u0627\u0645\u0644 \xB7 \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u062E\u0644\u0641\u064A\u0629",
  "Camera / lens": "\u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0623\u0648 \u0627\u0644\u0639\u062F\u0633\u0629",
  "Rear camera (automatic)": "\u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u062E\u0644\u0641\u064A\u0629 (\u062A\u0644\u0642\u0627\u0626\u064A)",
  "Front camera (automatic)": "\u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u0623\u0645\u0627\u0645\u064A\u0629 (\u062A\u0644\u0642\u0627\u0626\u064A)",
  "Open camera scanner \u25A5": "\u0627\u0641\u062A\u062D \u0645\u0627\u0633\u062D \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u25A5",
  "Stop camera": "\u0623\u0648\u0642\u0641 \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627",
  "Live barcode camera preview": "\u0645\u0639\u0627\u064A\u0646\u0629 \u0645\u0628\u0627\u0634\u0631\u0629 \u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u0628\u0627\u0631\u0643\u0648\u062F",
  "Whole barcode + blank edges": "\u0627\u0644\u0628\u0627\u0631\u0643\u0648\u062F \u0643\u0627\u0645\u0644\u064B\u0627 \u0645\u0639 \u062D\u0648\u0627\u0641 \u0641\u0627\u0631\u063A\u0629",
  "Choose a setup, then open the camera.": "\u0627\u062E\u062A\u0631 \u0625\u0639\u062F\u0627\u062F \u0627\u0644\u0645\u0633\u062D \u062B\u0645 \u0627\u0641\u062A\u062D \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627.",
  "Mirror preview": "\u0627\u0639\u0643\u0633 \u0627\u0644\u0645\u0639\u0627\u064A\u0646\u0629",
  "Turn preview upside down": "\u0627\u0642\u0644\u0628 \u0627\u0644\u0645\u0639\u0627\u064A\u0646\u0629 \u0631\u0623\u0633\u064B\u0627 \u0639\u0644\u0649 \u0639\u0642\u0628",
  "Light off": "\u0627\u0644\u0625\u0636\u0627\u0621\u0629 \u0645\u062A\u0648\u0642\u0641\u0629",
  "Light on": "\u0627\u0644\u0625\u0636\u0627\u0621\u0629 \u0645\u0641\u0639\u0651\u0644\u0629",
  "Focus, zoom & exposure": "\u0627\u0644\u062A\u0631\u0643\u064A\u0632 \u0648\u0627\u0644\u062A\u0643\u0628\u064A\u0631 \u0648\u0627\u0644\u062A\u0639\u0631\u064A\u0636",
  "Barcode": "\u0627\u0644\u0628\u0627\u0631\u0643\u0648\u062F",
  "Look up": "\u0627\u0628\u062D\u062B",
  "Look up product": "\u0627\u0628\u062D\u062B \u0639\u0646 \u0627\u0644\u0645\u0646\u062A\u062C",
  "Quantity": "\u0627\u0644\u0643\u0645\u064A\u0629",
  "Unit": "\u0627\u0644\u0648\u062D\u062F\u0629",
  "Ingredient": "\u0627\u0644\u0645\u0643\u0648\u0651\u0646",
  "Product name": "\u0627\u0633\u0645 \u0627\u0644\u0645\u0646\u062A\u062C",
  "Expiry date": "\u062A\u0627\u0631\u064A\u062E \u0627\u0644\u0627\u0646\u062A\u0647\u0627\u0621",
  "Optional": "\u0627\u062E\u062A\u064A\u0627\u0631\u064A",
  "Remove": "\u0625\u0632\u0627\u0644\u0629",
  "Edit": "\u062A\u0639\u062F\u064A\u0644",
  "Save": "\u062D\u0641\u0638",
  "Cancel": "\u0625\u0644\u063A\u0627\u0621",
  "Close": "\u0625\u063A\u0644\u0627\u0642",
  "Delete": "\u062D\u0630\u0641",
  "Add": "\u0625\u0636\u0627\u0641\u0629",
  "Search": "\u0628\u062D\u062B",
  "All": "\u0627\u0644\u0643\u0644",
  "Unknown": "\u063A\u064A\u0631 \u0645\u0639\u0631\u0648\u0641",
  "unknown": "\u063A\u064A\u0631 \u0645\u0639\u0631\u0648\u0641",
  "Loading\u2026": "\u062C\u0627\u0631\u064D \u0627\u0644\u062A\u062D\u0645\u064A\u0644\u2026",
  "Loading recipes\u2026": "\u062C\u0627\u0631\u064D \u062A\u062D\u0645\u064A\u0644 \u0627\u0644\u0648\u0635\u0641\u0627\u062A\u2026",
  "Looking up\u2026": "\u062C\u0627\u0631\u064D \u0627\u0644\u0628\u062D\u062B\u2026",
  "Review details at the end": "\u0631\u0627\u062C\u0639 \u0627\u0644\u062A\u0641\u0627\u0635\u064A\u0644 \u0641\u064A \u0627\u0644\u0646\u0647\u0627\u064A\u0629",
  "Final receipt \u2192": "\u0627\u0644\u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0646\u0647\u0627\u0626\u064A\u0629 \u2190",
  "Nothing scanned yet. Let\u2019s see what\u2019s hiding.": "\u0644\u0645 \u062A\u0645\u0633\u062D \u0623\u064A \u0635\u0646\u0641 \u0628\u0639\u062F. \u0644\u0646\u0643\u062A\u0634\u0641 \u0645\u0627 \u0644\u062F\u064A\u0643.",
  "1 package": "\u0639\u0628\u0648\u0629 \u0648\u0627\u062D\u062F\u0629",
  "Scan \u2192 beep \u2192 put it back. Every scan is accepted automatically.": "\u0627\u0645\u0633\u062D\u060C \u0648\u0627\u0633\u062A\u0645\u0639 \u0644\u0644\u062A\u0646\u0628\u064A\u0647\u060C \u062B\u0645 \u0623\u0639\u062F \u0627\u0644\u0635\u0646\u0641. \u064A\u064F\u0636\u0627\u0641 \u0643\u0644 \u0645\u0633\u062D \u062A\u0644\u0642\u0627\u0626\u064A\u064B\u0627.",
  "From your shopping bag to its new home.": "\u0645\u0646 \u0643\u064A\u0633 \u0627\u0644\u062A\u0633\u0648\u0651\u0642 \u0625\u0644\u0649 \u0645\u0643\u0627\u0646\u0647 \u0627\u0644\u062C\u062F\u064A\u062F.",
  "Scan recorded items from this location. Each scan stages removal of that whole recorded item.": "\u0627\u0645\u0633\u062D \u0627\u0644\u0623\u0635\u0646\u0627\u0641 \u0627\u0644\u0645\u0633\u062C\u0651\u0644\u0629 \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u0643\u0627\u0646. \u064A\u062C\u0647\u0651\u0632 \u0643\u0644 \u0645\u0633\u062D \u0625\u0632\u0627\u0644\u0629 \u0627\u0644\u0635\u0646\u0641 \u0627\u0644\u0645\u0633\u062C\u0651\u0644 \u0643\u0627\u0645\u0644\u064B\u0627.",
  "Accepted. Next item, please.": "\u062A\u0645\u062A \u0627\u0644\u0625\u0636\u0627\u0641\u0629. \u0627\u0644\u0635\u0646\u0641 \u0627\u0644\u062A\u0627\u0644\u064A\u060C \u0645\u0646 \u0641\u0636\u0644\u0643.",
  "Accepted. Looking up details while you keep scanning\u2026": "\u062A\u0645\u062A \u0627\u0644\u0625\u0636\u0627\u0641\u0629. \u062C\u0627\u0631\u064D \u0627\u0644\u0628\u062D\u062B \u0639\u0646 \u0627\u0644\u062A\u0641\u0627\u0635\u064A\u0644\u060C \u0648\u064A\u0645\u0643\u0646\u0643 \u0645\u062A\u0627\u0628\u0639\u0629 \u0627\u0644\u0645\u0633\u062D\u2026",
  "Unknown product kept on your receipt. Keep scanning; review it at the end.": "\u0623\u064F\u0628\u0642\u064A \u0627\u0644\u0645\u0646\u062A\u062C \u063A\u064A\u0631 \u0627\u0644\u0645\u0639\u0631\u0648\u0641 \u0641\u064A \u0642\u0627\u0626\u0645\u062A\u0643. \u062A\u0627\u0628\u0639 \u0627\u0644\u0645\u0633\u062D \u0648\u0631\u0627\u062C\u0639\u0647 \u0641\u064A \u0627\u0644\u0646\u0647\u0627\u064A\u0629.",
  "Product details unavailable.": "\u062A\u0641\u0627\u0635\u064A\u0644 \u0627\u0644\u0645\u0646\u062A\u062C \u063A\u064A\u0631 \u0645\u062A\u0627\u062D\u0629.",
  "Lookup unavailable.": "\u0627\u0644\u0628\u062D\u062B \u063A\u064A\u0631 \u0645\u062A\u0627\u062D.",
  "Enter or scan a barcode first.": "\u0623\u062F\u062E\u0644 \u0628\u0627\u0631\u0643\u0648\u062F \u0623\u0648 \u0627\u0645\u0633\u062D\u0647 \u0623\u0648\u0644\u064B\u0627.",
  "Recipes imported.": "\u062A\u0645 \u0627\u0633\u062A\u064A\u0631\u0627\u062F \u0627\u0644\u0648\u0635\u0641\u0627\u062A.",
  "No remaining matching inventory item in this source location. Nothing removed.": "\u0644\u0627 \u064A\u0648\u062C\u062F \u0635\u0646\u0641 \u0645\u0637\u0627\u0628\u0642 \u0645\u062A\u0628\u0642\u064D \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u0643\u0627\u0646. \u0644\u0645 \u064A\u064F\u062D\u0630\u0641 \u0634\u064A\u0621.",
  "Demo kitchen \xB7 separate sample data.": "\u0645\u0637\u0628\u062E \u062A\u062C\u0631\u064A\u0628\u064A \xB7 \u0628\u064A\u0627\u0646\u0627\u062A \u0646\u0645\u0648\u0630\u062C\u064A\u0629 \u0645\u0646\u0641\u0635\u0644\u0629.",
  "Signed in \xB7 automatic cloud saves; local copy available offline.": "\u062A\u0645 \u062A\u0633\u062C\u064A\u0644 \u0627\u0644\u062F\u062E\u0648\u0644 \xB7 \u062D\u0641\u0638 \u0633\u062D\u0627\u0628\u064A \u062A\u0644\u0642\u0627\u0626\u064A \u0648\u0646\u0633\u062E\u0629 \u0645\u062D\u0644\u064A\u0629 \u0645\u062A\u0627\u062D\u0629 \u062F\u0648\u0646 \u0627\u062A\u0635\u0627\u0644.",
  "Guest pantry \xB7 saved in this browser.": "\u0645\u062E\u0632\u0648\u0646 \u0627\u0644\u0636\u064A\u0641 \xB7 \u0645\u062D\u0641\u0648\u0638 \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u062A\u0635\u0641\u062D.",
  "Offline \xB7 Pantry and downloaded recipes work. New product and shop lookups need internet.": "\u062F\u0648\u0646 \u0627\u062A\u0635\u0627\u0644 \xB7 \u064A\u0639\u0645\u0644 \u0627\u0644\u0645\u062E\u0632\u0648\u0646 \u0648\u0627\u0644\u0648\u0635\u0641\u0627\u062A \u0627\u0644\u0645\u0646\u0632\u0651\u0644\u0629. \u064A\u062A\u0637\u0644\u0651\u0628 \u0627\u0644\u0628\u062D\u062B \u0639\u0646 \u0645\u0646\u062A\u062C\u0627\u062A \u0648\u0645\u062A\u0627\u062C\u0631 \u062C\u062F\u064A\u062F\u0629 \u0627\u062A\u0635\u0627\u0644\u064B\u0627 \u0628\u0627\u0644\u0625\u0646\u062A\u0631\u0646\u062A.",
  "Demo changes stay separate from your kitchen.": "\u062A\u0628\u0642\u0649 \u062A\u063A\u064A\u064A\u0631\u0627\u062A \u0627\u0644\u062A\u062C\u0631\u0628\u0629 \u0645\u0646\u0641\u0635\u0644\u0629 \u0639\u0646 \u0645\u0637\u0628\u062E\u0643.",
  "Local changes \xB7 saving automatically.": "\u062A\u063A\u064A\u064A\u0631\u0627\u062A \u0645\u062D\u0644\u064A\u0629 \xB7 \u062C\u0627\u0631\u064D \u0627\u0644\u062D\u0641\u0638 \u062A\u0644\u0642\u0627\u0626\u064A\u064B\u0627.",
  "Guest data is saved in this browser.": "\u062A\u064F\u062D\u0641\u0638 \u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0636\u064A\u0641 \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u062A\u0635\u0641\u062D.",
  "Guest data stays in this browser.": "\u062A\u0628\u0642\u0649 \u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0636\u064A\u0641 \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u062A\u0635\u0641\u062D.",
  "Preferred country": "\u0627\u0644\u0628\u0644\u062F \u0627\u0644\u0645\u0641\u0636\u0651\u0644",
  "Global \xB7 all countries": "\u0639\u0627\u0644\u0645\u064A \xB7 \u062C\u0645\u064A\u0639 \u0627\u0644\u0628\u0644\u062F\u0627\u0646",
  "Preferred display units": "\u0648\u062D\u062F\u0627\u062A \u0627\u0644\u0639\u0631\u0636 \u0627\u0644\u0645\u0641\u0636\u0651\u0644\u0629",
  "Metric": "\u0645\u062A\u0631\u064A",
  "Imperial": "\u0625\u0645\u0628\u0631\u0627\u0637\u0648\u0631\u064A",
  "Sign out": "\u062A\u0633\u062C\u064A\u0644 \u0627\u0644\u062E\u0631\u0648\u062C",
  "Save kitchen to cloud \u2191": "\u0627\u062D\u0641\u0638 \u0627\u0644\u0645\u0637\u0628\u062E \u0641\u064A \u0627\u0644\u0633\u062D\u0627\u0628\u0629 \u2191",
  "Restore cloud copy \u2193": "\u0627\u0633\u062A\u0639\u062F \u0627\u0644\u0646\u0633\u062E\u0629 \u0627\u0644\u0633\u062D\u0627\u0628\u064A\u0629 \u2193",
  "Backups & recipe imports": "\u0627\u0644\u0646\u0633\u062E \u0627\u0644\u0627\u062D\u062A\u064A\u0627\u0637\u064A\u0629 \u0648\u0627\u0633\u062A\u064A\u0631\u0627\u062F \u0627\u0644\u0648\u0635\u0641\u0627\u062A",
  "Export kitchen backup": "\u0635\u062F\u0651\u0631 \u0646\u0633\u062E\u0629 \u0627\u062D\u062A\u064A\u0627\u0637\u064A\u0629 \u0644\u0644\u0645\u0637\u0628\u062E",
  "Sign in to restore your pantry on another device.": "\u0633\u062C\u0651\u0644 \u0627\u0644\u062F\u062E\u0648\u0644 \u0644\u0627\u0633\u062A\u0639\u0627\u062F\u0629 \u0645\u062E\u0632\u0648\u0646\u0643 \u0639\u0644\u0649 \u062C\u0647\u0627\u0632 \u0622\u062E\u0631.",
  "Account setup pending. Guest pantry and offline recipes remain available.": "\u0625\u0639\u062F\u0627\u062F \u0627\u0644\u062D\u0633\u0627\u0628 \u0642\u064A\u062F \u0627\u0644\u0627\u0646\u062A\u0638\u0627\u0631. \u064A\u0638\u0644 \u0645\u062E\u0632\u0648\u0646 \u0627\u0644\u0636\u064A\u0641 \u0648\u0627\u0644\u0648\u0635\u0641\u0627\u062A \u062F\u0648\u0646 \u0627\u062A\u0635\u0627\u0644 \u0645\u062A\u0627\u062D\u064A\u0646.",
  "Exit the demo to save your own kitchen.": "\u0623\u0646\u0647\u0650 \u0627\u0644\u062A\u062C\u0631\u0628\u0629 \u0644\u062D\u0641\u0638 \u0645\u0637\u0628\u062E\u0643 \u0627\u0644\u062E\u0627\u0635.",
  "Cloud operation failed.": "\u0641\u0634\u0644\u062A \u0627\u0644\u0639\u0645\u0644\u064A\u0629 \u0627\u0644\u0633\u062D\u0627\u0628\u064A\u0629.",
  "Replace this browser copy with the cloud save? Export local changes first.": "\u0647\u0644 \u062A\u0631\u064A\u062F \u0627\u0633\u062A\u0628\u062F\u0627\u0644 \u0646\u0633\u062E\u0629 \u0647\u0630\u0627 \u0627\u0644\u0645\u062A\u0635\u0641\u062D \u0628\u0627\u0644\u0646\u0633\u062E\u0629 \u0627\u0644\u0633\u062D\u0627\u0628\u064A\u0629\u061F \u0635\u062F\u0651\u0631 \u0627\u0644\u062A\u063A\u064A\u064A\u0631\u0627\u062A \u0627\u0644\u0645\u062D\u0644\u064A\u0629 \u0623\u0648\u0644\u064B\u0627.",
  "Cloud copy restored.": "\u062A\u0645\u062A \u0627\u0633\u062A\u0639\u0627\u062F\u0629 \u0627\u0644\u0646\u0633\u062E\u0629 \u0627\u0644\u0633\u062D\u0627\u0628\u064A\u0629.",
  "No cloud copy yet. Add items or import a backup, then save.": "\u0644\u0627 \u062A\u0648\u062C\u062F \u0646\u0633\u062E\u0629 \u0633\u062D\u0627\u0628\u064A\u0629 \u0628\u0639\u062F. \u0623\u0636\u0641 \u0623\u0635\u0646\u0627\u0641\u064B\u0627 \u0623\u0648 \u0627\u0633\u062A\u0648\u0631\u062F \u0646\u0633\u062E\u0629 \u0627\u062D\u062A\u064A\u0627\u0637\u064A\u0629\u060C \u062B\u0645 \u0627\u062D\u0641\u0638.",
  "Saved to cloud. Automatic saving continues.": "\u062A\u0645 \u0627\u0644\u062D\u0641\u0638 \u0641\u064A \u0627\u0644\u0633\u062D\u0627\u0628\u0629. \u064A\u0633\u062A\u0645\u0631 \u0627\u0644\u062D\u0641\u0638 \u0627\u0644\u062A\u0644\u0642\u0627\u0626\u064A.",
  "Check your email to confirm your account.": "\u062A\u062D\u0642\u0651\u0642 \u0645\u0646 \u0628\u0631\u064A\u062F\u0643 \u0627\u0644\u0625\u0644\u0643\u062A\u0631\u0648\u0646\u064A \u0644\u062A\u0623\u0643\u064A\u062F \u062D\u0633\u0627\u0628\u0643.",
  "Check your email for recovery instructions.": "\u062A\u062D\u0642\u0651\u0642 \u0645\u0646 \u0628\u0631\u064A\u062F\u0643 \u0627\u0644\u0625\u0644\u0643\u062A\u0631\u0648\u0646\u064A \u0644\u0644\u062D\u0635\u0648\u0644 \u0639\u0644\u0649 \u062A\u0639\u0644\u064A\u0645\u0627\u062A \u0627\u0644\u0627\u0633\u062A\u0639\u0627\u062F\u0629.",
  "Forgot password?": "\u0646\u0633\u064A\u062A \u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631\u061F",
  "Set new password": "\u0639\u064A\u0651\u0646 \u0643\u0644\u0645\u0629 \u0645\u0631\u0648\u0631 \u062C\u062F\u064A\u062F\u0629",
  "Email": "\u0627\u0644\u0628\u0631\u064A\u062F \u0627\u0644\u0625\u0644\u0643\u062A\u0631\u0648\u0646\u064A",
  "Password": "\u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631",
  "Create account": "\u0625\u0646\u0634\u0627\u0621 \u062D\u0633\u0627\u0628",
  "YOUR INGREDIENTS, NEW IDEAS": "\u0645\u0643\u0648\u0651\u0646\u0627\u062A\u0643 \u0648\u0623\u0641\u0643\u0627\u0631 \u062C\u062F\u064A\u062F\u0629",
  "START WITH WHAT YOU HAVE": "\u0627\u0628\u062F\u0623 \u0628\u0645\u0627 \u0644\u062F\u064A\u0643",
  "Three ideas for dinner.": "\u062B\u0644\u0627\u062B \u0623\u0641\u0643\u0627\u0631 \u0644\u0644\u0639\u0634\u0627\u0621.",
  "Household portions": "\u062D\u0635\u0635 \u0627\u0644\u0623\u0633\u0631\u0629",
  "Refresh \u21BB": "\u062A\u062D\u062F\u064A\u062B \u21BB",
  "Find a dish or ingredient": "\u0627\u0628\u062D\u062B \u0639\u0646 \u0637\u0628\u0642 \u0623\u0648 \u0645\u0643\u0648\u0651\u0646",
  "e.g. rice, soup, coconut": "\u0645\u062B\u0644: \u0627\u0644\u0623\u0631\u0632 \u0623\u0648 \u0627\u0644\u062D\u0633\u0627\u0621 \u0623\u0648 \u062C\u0648\u0632 \u0627\u0644\u0647\u0646\u062F",
  "Cook from": "\u0627\u0633\u062A\u062E\u062F\u0645 \u0645\u062E\u0632\u0648\u0646",
  "Whole kitchen": "\u0627\u0644\u0645\u0637\u0628\u062E \u0643\u0644\u0647",
  "Show": "\u0639\u0631\u0636",
  "All menus": "\u062C\u0645\u064A\u0639 \u0627\u0644\u0648\u062C\u0628\u0627\u062A",
  "Ready to cook": "\u062C\u0627\u0647\u0632 \u0644\u0644\u0637\u0647\u064A",
  "Missing ingredients": "\u0645\u0643\u0648\u0651\u0646\u0627\u062A \u0646\u0627\u0642\u0635\u0629",
  "Needs review": "\u064A\u062D\u062A\u0627\u062C \u0625\u0644\u0649 \u0645\u0631\u0627\u062C\u0639\u0629",
  "Who is eating?": "\u0645\u0646 \u0633\u064A\u062A\u0646\u0627\u0648\u0644 \u0627\u0644\u0637\u0639\u0627\u0645\u061F",
  "Cook this meal": "\u0627\u0637\u0647\u0650 \u0647\u0630\u0647 \u0627\u0644\u0648\u062C\u0628\u0629",
  "Serve / after meal": "\u0642\u062F\u0651\u0645 \u0627\u0644\u0648\u062C\u0628\u0629 \u0623\u0648 \u0633\u062C\u0651\u0644\u0647\u0627",
  "Save as favourite": "\u0627\u062D\u0641\u0638 \u0641\u064A \u0627\u0644\u0645\u0641\u0636\u0651\u0644\u0629",
  "Saved favourite \u2713": "\u0645\u062D\u0641\u0648\u0638 \u0641\u064A \u0627\u0644\u0645\u0641\u0636\u0651\u0644\u0629 \u2713",
  "Breakfast": "\u0627\u0644\u0641\u0637\u0648\u0631",
  "Lunch": "\u0627\u0644\u063A\u062F\u0627\u0621",
  "Dinner": "\u0627\u0644\u0639\u0634\u0627\u0621",
  "Snack": "\u0648\u062C\u0628\u0629 \u062E\u0641\u064A\u0641\u0629",
  "Meal": "\u0627\u0644\u0648\u062C\u0628\u0629",
  "Date": "\u0627\u0644\u062A\u0627\u0631\u064A\u062E",
  "Daily": "\u064A\u0648\u0645\u064A",
  "Weekly": "\u0623\u0633\u0628\u0648\u0639\u064A",
  "Portions": "\u0627\u0644\u062D\u0635\u0635",
  "Planned meals": "\u0627\u0644\u0648\u062C\u0628\u0627\u062A \u0627\u0644\u0645\u062E\u0637\u0651\u0637\u0629",
  "Planned portions": "\u0627\u0644\u062D\u0635\u0635 \u0627\u0644\u0645\u062E\u0637\u0651\u0637\u0629",
  "All storage": "\u062C\u0645\u064A\u0639 \u0623\u0645\u0627\u0643\u0646 \u0627\u0644\u062A\u062E\u0632\u064A\u0646",
  "Edit location": "\u0639\u062F\u0651\u0644 \u0645\u0643\u0627\u0646 \u0627\u0644\u062A\u062E\u0632\u064A\u0646",
  "Edit preferences": "\u0639\u062F\u0651\u0644 \u0627\u0644\u062A\u0641\u0636\u064A\u0644\u0627\u062A",
  "Remove member": "\u0623\u0632\u0644 \u0627\u0644\u0634\u062E\u0635",
  "Add people, their preferences and dietary advisors to personalise your menus.": "\u0623\u0636\u0641 \u0627\u0644\u0623\u0634\u062E\u0627\u0635 \u0648\u062A\u0641\u0636\u064A\u0644\u0627\u062A\u0647\u0645 \u0648\u062E\u064A\u0627\u0631\u0627\u062A\u0647\u0645 \u0627\u0644\u063A\u0630\u0627\u0626\u064A\u0629 \u0644\u062A\u062E\u0635\u064A\u0635 \u0627\u0644\u0648\u062C\u0628\u0627\u062A.",
  "Recipe no longer available": "\u0627\u0644\u0648\u0635\u0641\u0629 \u0644\u0645 \u062A\u0639\u062F \u0645\u062A\u0627\u062D\u0629",
  "Meal nutrients & notes": "\u0645\u063A\u0630\u0651\u064A\u0627\u062A \u0627\u0644\u0648\u062C\u0628\u0629 \u0648\u0627\u0644\u0645\u0644\u0627\u062D\u0638\u0627\u062A",
  "Delete log": "\u0627\u062D\u0630\u0641 \u0627\u0644\u0633\u062C\u0644",
  "AFTER THE LAST BITE": "\u0628\u0639\u062F \u0627\u0644\u0648\u062C\u0628\u0629",
  "How did the meal go?": "\u0643\u064A\u0641 \u0643\u0627\u0646\u062A \u0627\u0644\u0648\u062C\u0628\u0629\u061F",
  "Recipe or custom meal": "\u0648\u0635\u0641\u0629 \u0623\u0648 \u0648\u062C\u0628\u0629 \u0645\u062E\u0635\u0651\u0635\u0629",
  "Date eaten": "\u062A\u0627\u0631\u064A\u062E \u062A\u0646\u0627\u0648\u0644 \u0627\u0644\u0637\u0639\u0627\u0645",
  "Who ate this?": "\u0645\u0646 \u062A\u0646\u0627\u0648\u0644 \u0647\u0630\u0647 \u0627\u0644\u0648\u062C\u0628\u0629\u061F",
  "Portions served": "\u0627\u0644\u062D\u0635\u0635 \u0627\u0644\u0645\u0642\u062F\u0651\u0645\u0629",
  "Eaten (%) \xB7 optional": "\u0627\u0644\u0646\u0633\u0628\u0629 \u0627\u0644\u0645\u0623\u0643\u0648\u0644\u0629 (%) \xB7 \u0627\u062E\u062A\u064A\u0627\u0631\u064A",
  "100 if left blank": "\u0661\u0660\u0660 \u0625\u0630\u0627 \u062A\u064F\u0631\u0643 \u0641\u0627\u0631\u063A\u064B\u0627",
  "What happened to the rest?": "\u0645\u0627\u0630\u0627 \u062D\u062F\u062B \u0644\u0644\u0628\u0627\u0642\u064A\u061F",
  "Not recorded": "\u063A\u064A\u0631 \u0645\u0633\u062C\u0651\u0644",
  "Saved for later": "\u0645\u062D\u0641\u0648\u0638 \u0644\u0648\u0642\u062A \u0644\u0627\u062D\u0642",
  "Discarded": "\u062A\u0645 \u0627\u0644\u062A\u062E\u0644\u0651\u0635 \u0645\u0646\u0647",
  "Shared with someone else": "\u062A\u0645\u062A \u0645\u0634\u0627\u0631\u0643\u062A\u0647 \u0645\u0639 \u0634\u062E\u0635 \u0622\u062E\u0631",
  "Meal name": "\u0627\u0633\u0645 \u0627\u0644\u0648\u062C\u0628\u0629",
  "Meal notes": "\u0645\u0644\u0627\u062D\u0638\u0627\u062A \u0627\u0644\u0648\u062C\u0628\u0629",
  "Likes, dislikes, leftovers\u2026": "\u0645\u0627 \u0623\u0639\u062C\u0628\u0643 \u0648\u0645\u0627 \u0644\u0645 \u064A\u0639\u062C\u0628\u0643 \u0648\u0628\u0642\u0627\u064A\u0627 \u0627\u0644\u0637\u0639\u0627\u0645\u2026",
  "Save after-meal record \u2713": "\u0627\u062D\u0641\u0638 \u0633\u062C\u0644 \u0645\u0627 \u0628\u0639\u062F \u0627\u0644\u0648\u062C\u0628\u0629 \u2713",
  "Energy": "\u0627\u0644\u0637\u0627\u0642\u0629",
  "Protein": "\u0627\u0644\u0628\u0631\u0648\u062A\u064A\u0646",
  "Carbohydrates": "\u0627\u0644\u0643\u0631\u0628\u0648\u0647\u064A\u062F\u0631\u0627\u062A",
  "Fat": "\u0627\u0644\u062F\u0647\u0648\u0646",
  "Fibre": "\u0627\u0644\u0623\u0644\u064A\u0627\u0641",
  "Sugar": "\u0627\u0644\u0633\u0643\u0631",
  "Sodium": "\u0627\u0644\u0635\u0648\u062F\u064A\u0648\u0645",
  "Salt": "\u0627\u0644\u0645\u0644\u062D",
  "Search recipes": "\u0627\u0628\u062D\u062B \u0639\u0646 \u0627\u0644\u0648\u0635\u0641\u0627\u062A",
  "Read recipe & review quantities": "\u0627\u0642\u0631\u0623 \u0627\u0644\u0648\u0635\u0641\u0629 \u0648\u0631\u0627\u062C\u0639 \u0627\u0644\u0643\u0645\u064A\u0627\u062A",
  "Show more recipes": "\u0627\u0639\u0631\u0636 \u0627\u0644\u0645\u0632\u064A\u062F \u0645\u0646 \u0627\u0644\u0648\u0635\u0641\u0627\u062A",
  "Source instructions": "\u062A\u0639\u0644\u064A\u0645\u0627\u062A \u0627\u0644\u0645\u0635\u062F\u0631",
  "Review for my kitchen": "\u0631\u0627\u062C\u0639\u0647\u0627 \u0644\u0645\u0637\u0628\u062E\u064A",
  "Reviewed serving yield": "\u0639\u062F\u062F \u0627\u0644\u062D\u0635\u0635 \u0628\u0639\u062F \u0627\u0644\u0645\u0631\u0627\u062C\u0639\u0629",
  "Save my reviewed recipe": "\u0627\u062D\u0641\u0638 \u0648\u0635\u0641\u062A\u064A \u0627\u0644\u0645\u0631\u0627\u062C\u064E\u0639\u0629",
  "Download source recipe as JSON-LD": "\u0646\u0632\u0651\u0644 \u0648\u0635\u0641\u0629 \u0627\u0644\u0645\u0635\u062F\u0631 \u0628\u0635\u064A\u063A\u0629 JSON-LD",
  "Keep the kitchen current.": "\u062D\u062F\u0651\u062B \u062D\u0627\u0644\u0629 \u0627\u0644\u0645\u0637\u0628\u062E.",
  "Inventory item": "\u0627\u0644\u0635\u0646\u0641 \u0641\u064A \u0627\u0644\u0645\u062E\u0632\u0648\u0646",
  "Label use-by date (optional)": "\u062A\u0627\u0631\u064A\u062E \u0627\u0644\u0627\u0633\u062A\u062E\u062F\u0627\u0645 \u0639\u0644\u0649 \u0627\u0644\u0639\u0628\u0648\u0629 (\u0627\u062E\u062A\u064A\u0627\u0631\u064A)",
  "Estimated check reminder, days from today (optional)": "\u062A\u0630\u0643\u064A\u0631 \u062A\u0642\u062F\u064A\u0631\u064A \u0628\u0627\u0644\u0641\u062D\u0635\u060C \u0628\u0627\u0644\u0623\u064A\u0627\u0645 \u0645\u0646 \u0627\u0644\u064A\u0648\u0645 (\u0627\u062E\u062A\u064A\u0627\u0631\u064A)",
  "Choose based on this item and storage": "\u0627\u062E\u062A\u0631 \u062D\u0633\u0628 \u0627\u0644\u0635\u0646\u0641 \u0648\u0638\u0631\u0648\u0641 \u062A\u062E\u0632\u064A\u0646\u0647",
  "Use suggested check interval": "\u0627\u0633\u062A\u062E\u062F\u0645 \u0641\u062A\u0631\u0629 \u0627\u0644\u0641\u062D\u0635 \u0627\u0644\u0645\u0642\u062A\u0631\u062D\u0629",
  "Reminder note": "\u0645\u0644\u0627\u062D\u0638\u0629 \u0627\u0644\u062A\u0630\u0643\u064A\u0631",
  "e.g. opened today; check freshness": "\u0645\u062B\u0644: \u0641\u064F\u062A\u062D \u0627\u0644\u064A\u0648\u0645\u061B \u062A\u062D\u0642\u0651\u0642 \u0645\u0646 \u062D\u0627\u0644\u062A\u0647",
  "Save dates & reminder": "\u0627\u062D\u0641\u0638 \u0627\u0644\u062A\u0648\u0627\u0631\u064A\u062E \u0648\u0627\u0644\u062A\u0630\u0643\u064A\u0631",
  "Close recipe": "\u0623\u063A\u0644\u0642 \u0627\u0644\u0648\u0635\u0641\u0629",
  "Close meal log": "\u0623\u063A\u0644\u0642 \u0633\u062C\u0644 \u0627\u0644\u0648\u062C\u0628\u0629",
  "Close freshness settings": "\u0623\u063A\u0644\u0642 \u0625\u0639\u062F\u0627\u062F\u0627\u062A \u0627\u0644\u062A\u0630\u0643\u064A\u0631",
  "Kitchen navigation": "\u0627\u0644\u062A\u0646\u0642\u0651\u0644 \u0641\u064A \u0627\u0644\u0645\u0637\u0628\u062E",
  "offmenu home": "\u0635\u0641\u062D\u0629 offmenu \u0627\u0644\u0631\u0626\u064A\u0633\u064A\u0629",
  "Not available": "\u063A\u064A\u0631 \u0645\u062A\u0627\u062D",
  "not available": "\u063A\u064A\u0631 \u0645\u062A\u0627\u062D",
  "Food data & estimated nutrition": "\u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0637\u0639\u0627\u0645 \u0648\u0627\u0644\u062A\u063A\u0630\u064A\u0629 \u0627\u0644\u062A\u0642\u062F\u064A\u0631\u064A\u0629",
  "Add a meal to see shopping gaps.": "\u0623\u0636\u0641 \u0648\u062C\u0628\u0629 \u0644\u0631\u0624\u064A\u0629 \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A \u0627\u0644\u0646\u0627\u0642\u0635\u0629.",
  "Add a menu to build your ingredient list.": "\u0623\u0636\u0641 \u0648\u062C\u0628\u0629 \u0644\u0625\u0646\u0634\u0627\u0621 \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0645\u0643\u0648\u0651\u0646\u0627\u062A.",
  "Unmeasured ingredients to review": "\u0645\u0643\u0648\u0651\u0646\u0627\u062A \u063A\u064A\u0631 \u0645\u0642\u0627\u0633\u0629 \u062A\u062D\u062A\u0627\u062C \u0625\u0644\u0649 \u0645\u0631\u0627\u062C\u0639\u0629",
  "No measured ingredient gaps. Check unmeasured ingredients below.": "\u0644\u0627 \u062A\u0648\u062C\u062F \u0645\u0643\u0648\u0651\u0646\u0627\u062A \u0645\u0642\u0627\u0633\u0629 \u0646\u0627\u0642\u0635\u0629. \u0631\u0627\u062C\u0639 \u0627\u0644\u0645\u0643\u0648\u0651\u0646\u0627\u062A \u063A\u064A\u0631 \u0627\u0644\u0645\u0642\u0627\u0633\u0629 \u0623\u062F\u0646\u0627\u0647.",
  "Your food journal starts with the next meal. Log a recipe or enter totals from a label.": "\u064A\u0628\u062F\u0623 \u0633\u062C\u0644 \u0637\u0639\u0627\u0645\u0643 \u0628\u0627\u0644\u0648\u062C\u0628\u0629 \u0627\u0644\u062A\u0627\u0644\u064A\u0629. \u0633\u062C\u0651\u0644 \u0648\u0635\u0641\u0629 \u0623\u0648 \u0623\u062F\u062E\u0644 \u0627\u0644\u0625\u062C\u0645\u0627\u0644\u064A\u0627\u062A \u0645\u0646 \u0627\u0644\u0639\u0628\u0648\u0629.",
  "Unavailable source text": "\u0646\u0635 \u0627\u0644\u0645\u0635\u062F\u0631 \u063A\u064A\u0631 \u0645\u062A\u0627\u062D",
  "Nutrient metric": "\u0627\u0644\u0645\u0624\u0634\u0631 \u0627\u0644\u063A\u0630\u0627\u0626\u064A",
  "Status": "\u0627\u0644\u062D\u0627\u0644\u0629",
  "Total": "\u0627\u0644\u0625\u062C\u0645\u0627\u0644\u064A",
  "Known subtotal": "\u0627\u0644\u0625\u062C\u0645\u0627\u0644\u064A \u0627\u0644\u062C\u0632\u0626\u064A \u0627\u0644\u0645\u0639\u0631\u0648\u0641",
  "Per 1,000 kcal": "\u0644\u0643\u0644 \u0661\u0660\u0660\u0660 \u0633\u0639\u0631\u0629 \u062D\u0631\u0627\u0631\u064A\u0629",
  "Mass coverage": "\u062A\u063A\u0637\u064A\u0629 \u0627\u0644\u0643\u062A\u0644\u0629",
  "Done.": "\u062A\u0645\u0651.",
  "Country": "\u0627\u0644\u0628\u0644\u062F",
  "Evidence": "\u0627\u0644\u0623\u062F\u0644\u0629",
  "Global food and evidence workspace": "\u0645\u0633\u0627\u062D\u0629 \u0639\u0645\u0644 \u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0637\u0639\u0627\u0645 \u0648\u0627\u0644\u0623\u062F\u0644\u0629 \u0627\u0644\u0639\u0627\u0644\u0645\u064A\u0629",
  "OffMenu \xB7 Global data workspace": "OffMenu \xB7 \u0645\u0633\u0627\u062D\u0629 \u0639\u0645\u0644 \u0627\u0644\u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0639\u0627\u0644\u0645\u064A\u0629",
  "\u2190 My kitchen": "\u2190 \u0645\u0637\u0628\u062E\u064A",
  "Open country": "\u0627\u0639\u0631\u0636 \u0627\u0644\u0628\u0644\u062F",
  "Country coverage and starter baskets": "\u062A\u063A\u0637\u064A\u0629 \u0627\u0644\u0628\u0644\u062F\u0627\u0646 \u0648\u0633\u0644\u0627\u0644 \u0627\u0644\u0628\u062F\u0627\u064A\u0629",
  "Calculate nutrients and coverage": "\u0627\u062D\u0633\u0628 \u0627\u0644\u0639\u0646\u0627\u0635\u0631 \u0627\u0644\u063A\u0630\u0627\u0626\u064A\u0629 \u0648\u0627\u0644\u062A\u063A\u0637\u064A\u0629",
  "Native language support": "\u062F\u0639\u0645 \u0627\u0644\u0644\u063A\u0629 \u0627\u0644\u0623\u0635\u0644\u064A\u0629",
  "National sources / access": "\u0627\u0644\u0645\u0635\u0627\u062F\u0631 \u0627\u0644\u0648\u0637\u0646\u064A\u0629 \u0648\u0625\u0645\u0643\u0627\u0646\u064A\u0629 \u0627\u0644\u0648\u0635\u0648\u0644",
  "Current offmenu coverage": "\u062A\u063A\u0637\u064A\u0629 offmenu \u0627\u0644\u062D\u0627\u0644\u064A\u0629",
  "Source-specific identity": "\u0647\u0648\u064A\u0629 \u062E\u0627\u0635\u0629 \u0628\u0627\u0644\u0645\u0635\u062F\u0631",
  "Candidate identity link": "\u0631\u0627\u0628\u0637 \u0647\u0648\u064A\u0629 \u0645\u0631\u0634\u0651\u062D",
  "Curated concept": "\u0645\u0641\u0647\u0648\u0645 \u0645\u064F\u0631\u0627\u062C\u0639",
  "Identified resource": "\u0645\u0648\u0631\u062F \u0645\u062D\u062F\u0651\u062F \u0627\u0644\u0647\u0648\u064A\u0629",
  "Source assertion": "\u0628\u064A\u0627\u0646 \u0645\u0646 \u0627\u0644\u0645\u0635\u062F\u0631",
  "Candidate": "\u0645\u0631\u0634\u0651\u062D",
  "Editor authored": "\u0645\u0646 \u062A\u0623\u0644\u064A\u0641 \u0627\u0644\u0645\u062D\u0631\u0651\u0631",
  "Reviewed": "\u0645\u064F\u0631\u0627\u062C\u0639",
  "Verified": "\u0645\u062A\u062D\u0642\u0651\u0642 \u0645\u0646\u0647",
  "Conflicting": "\u0645\u062A\u0639\u0627\u0631\u0636",
  "Superseded": "\u0645\u0633\u062A\u0628\u062F\u064E\u0644",
  "Needs transcription": "\u064A\u062D\u062A\u0627\u062C \u0625\u0644\u0649 \u062A\u0641\u0631\u064A\u063A \u0627\u0644\u0646\u0635",
  "Recipe Variant": "\u0646\u0633\u062E\u0629 \u0645\u0646 \u0648\u0635\u0641\u0629",
  "Recipe Step": "\u062E\u0637\u0648\u0629 \u0641\u064A \u0627\u0644\u0648\u0635\u0641\u0629",
  "Recipe Concept": "\u0645\u0641\u0647\u0648\u0645 \u0648\u0635\u0641\u0629",
  "instruction": "\u062A\u0639\u0644\u064A\u0645\u0627\u062A",
  "position": "\u0627\u0644\u062A\u0631\u062A\u064A\u0628",
  "original Source Record": "\u0633\u062C\u0644 \u0627\u0644\u0645\u0635\u062F\u0631 \u0627\u0644\u0623\u0635\u0644\u064A"
});

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/locale-negotiation.js
var SUPPORTED_LOCALES2 = Object.freeze(["en", "ar"]);

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/i18n.js
var LANGUAGES2 = Object.freeze([
  { code: "en", name: "English", direction: "ltr" },
  { code: "ar", name: "\u0627\u0644\u0639\u0631\u0628\u064A\u0629", direction: "rtl" }
]);

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/ingredients.js
var groups = {
  plant: ["rice|long grain rice|basmati|jasmine rice", "peas|green peas|frozen peas", "carrot|carrots", "olive oil|extra virgin olive oil", "water|tap water", "red lentils|red lentil|split red lentils", "green lentils|brown lentils", "spinach|baby spinach", "mushroom|mushrooms", "broccoli", "potato|potatoes", "sweet potato|sweet potatoes", "cucumber", "tomato|tomatoes", "lemon juice", "couscous", "cumin", "quinoa", "cauliflower", "zucchini|courgette|courgettes", "eggplant|aubergine", "coriander|cilantro", "onion|onions", "garlic", "ginger", "apple|apples", "banana|bananas", "orange", "pear", "peach", "plum", "strawberry", "blueberry", "raspberry", "grapes", "melon", "pineapple", "mango", "avocado", "lettuce", "cabbage", "kale", "celery", "beetroot|beet", "pumpkin|squash", "capsicum|bell pepper", "green beans", "asparagus", "leek", "spring onion|scallion", "radish", "fennel", "parsley", "basil", "mint", "dill", "rosemary", "thyme", "oregano", "chilli|chili", "black pepper", "salt", "sugar", "brown sugar", "maple syrup", "sunflower oil", "canola oil|rapeseed oil", "sesame oil", "vinegar", "rice vinegar", "cider vinegar", "cocoa butter", "cocoa powder", "coffee", "tea", "chickpea flour|gram flour|besan", "rice flour", "corn flour|cornflour|maize flour", "almond flour", "oats", "buckwheat", "millet", "corn|maize", "rice noodles", "canned chickpeas|chickpeas canned", "canned kidney beans|kidney beans canned", "canned tomato|canned tomatoes|tinned tomatoes", "coconut milk", "coconut cream", "almond milk", "oat milk", "soy milk|soya milk", "peanut butter", "peanuts", "almonds", "walnuts", "cashew|cashews", "hazelnut", "sesame seeds", "chia seeds", "flaxseed|linseed", "sunflower seeds", "pumpkin seeds", "tofu|bean curd", "tempeh", "chickpeas", "kidney beans", "black beans"],
  dairy: ["milk|cow milk", "cream|dairy cream", "cheese|cheddar", "butter|dairy butter", "yoghurt|yogurt", "whey"],
  meat: ["chicken", "beef", "pork", "bacon", "turkey", "duck", "lamb", "veal", "venison", "sausage", "ham", "gelatin|gelatine", "meat"],
  fish: ["fish", "salmon", "tuna", "canned tuna", "prawn|shrimp|prawns|shrimps", "sardine", "anchovy", "cod", "haddock", "mussel", "crab", "lobster"],
  animal: ["egg|eggs", "honey"],
  compound: ["pasta|spaghetti", "bread", "flatbread", "wheat flour|plain flour|flour", "barley", "rye", "bulgur", "soy sauce", "curry powder", "vegetable stock", "chicken stock", "beef stock"]
};
var INGREDIENTS = Object.entries(groups).flatMap(([category, entries]) => entries.map((text2) => {
  const [id2, ...aliases] = text2.split("|");
  return { id: id2, aliases, category };
}));
var lookup = new Map(INGREDIENTS.flatMap((i14) => [i14.id, ...i14.aliases].map((x) => [x, i14])));

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/model.js
function validSourceObservationReference2(ref, barcode) {
  if (ref?.schema === "offmenu-identifier-observation/2") return validSourceObservationReference(ref, barcode);
  const bounded3 = (value, max) => typeof value === "string" && value.length > 0 && value.length <= max;
  const key = ref?.observationKey;
  return ref?.schema === "offmenu-identifier-observation/1" && /^[a-f0-9]{64}$/.test(ref.databaseSha256 || "") && bounded3(ref.runId, 100) && ref.namespace === "barcode" && ref.lexicalValue === barcode && bounded3(ref.sourceId, 40) && bounded3(ref.releaseId, 80) && (ref.sourceRecordId === null || bounded3(ref.sourceRecordId, 200)) && key && key.run_id === ref.runId && bounded3(key.input_id, 250) && Number.isSafeInteger(key.record_ordinal) && key.record_ordinal >= 0 && Number.isSafeInteger(key.assertion_id) && key.assertion_id > 0 && (ref.detailSelectionSha256 === null || /^[a-f0-9]{64}$/.test(ref.detailSelectionSha256 || ""));
}

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/off-photo-metadata.js
var OFF_PHOTO_METADATA = "offmenu-off-photo-metadata/1";
var OFF_PHOTO_LICENSE = Object.freeze({ name: "CC BY-SA 3.0", url: "https://creativecommons.org/licenses/by-sa/3.0/" });
var object4 = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
var text = (v) => typeof v === "string" && v.length > 0 && v.length <= 8192 ? v : null;
var code = (v) => typeof v === "string" && /^\d{1,32}$/.test(v) ? v : null;
var integer = (v) => typeof v === "string" && /^\d{1,16}$/.test(v) ? v : Number.isSafeInteger(v) && v >= 0 ? String(v) : null;
var pointer = (s) => s.replaceAll("~", "~0").replaceAll("/", "~1");
function offPhotoStorageCode(value) {
  if (!code(value)) return null;
  const significant = value.replace(/^0+/, "") || "0";
  return significant.length <= 8 ? significant.padStart(8, "0") : significant.length <= 12 ? significant.padStart(13, "0") : significant;
}
function folder(value) {
  const stored = offPhotoStorageCode(value);
  return stored?.length <= 8 ? stored : stored?.replace(/^(...)(...)(...)(.*)$/, "$1/$2/$3/$4");
}
function imageURL(value, sourceCode, role, language2 = null) {
  if (!text(value) || value.length > 4096) return null;
  try {
    const u = new URL(value), prefix = "/images/products/" + folder(sourceCode) + "/";
    if (u.protocol !== "https:" || u.hostname !== "images.openfoodfacts.org" || u.port || u.username || u.password || u.search || u.hash || u.href !== value || !u.pathname.startsWith(prefix)) return null;
    const match = /^(front|nutrition|ingredients|packaging)_([a-z]{2})\.(\d{1,16})\.(100|200|400|full)\.(?:jpg|jpeg|png|webp)$/.exec(u.pathname.slice(prefix.length));
    if (!match || match[1] !== role || language2 && match[2] !== language2) return null;
    return { url: value, role: match[1], language: match[2], revision: match[3], resolution: match[4], selectedKey: match[1] + "_" + match[2] };
  } catch {
    return null;
  }
}
var noticeFields = ["title", "copyright", "copyright_notice", "license_notice", "disclaimer", "attribution"];
function credit(sourceCode, photo, { selected: selected3 = null, raw = null, catalogue = null } = {}) {
  const paths = { selected: "/images/" + pointer(photo.selectedKey), raw: "/images/" + pointer(integer(selected3?.imgid) || ""), catalogue: "OFF_PHOTOS[key=" + String(catalogue?.key || "") + "]" };
  const notices = [];
  for (const [origin, entry] of [["selected", selected3], ["raw", raw], ["catalogue", catalogue]]) for (const field of noticeFields) if (text(entry?.[field])) notices.push({ field, text: entry[field], origin, sourceField: paths[origin] + (origin === "catalogue" ? "." : "/") + field });
  const uploader = text(raw?.uploader) || text(selected3?.uploader) || text(catalogue?.contributor);
  const adaptations = {};
  for (const field of ["imgid", "rev", "angle", "normalize", "white_magic", "x1", "x2", "y1", "y2", "geometry", "coordinates_image_size"]) if (selected3 && Object.hasOwn(selected3, field) && (selected3[field] === null || typeof selected3[field] === "boolean" || typeof selected3[field] === "number" && Number.isFinite(selected3[field]) || typeof selected3[field] === "string" && selected3[field].length <= 8192)) adaptations[field] = selected3[field];
  return {
    schema: OFF_PHOTO_METADATA,
    sourceName: "Open Food Facts",
    sourceCode,
    productUrl: "https://world.openfoodfacts.org/product/" + sourceCode,
    photoPage: "https://world.openfoodfacts.org/cgi/product_image.pl?code=" + sourceCode + "&id=" + photo.selectedKey,
    photoLicense: { ...OFF_PHOTO_LICENSE, scope: "Publisher-stated product-photo licence; not database licensing" },
    databaseLicenses: [{ name: "ODbL", url: "https://opendatacommons.org/licenses/odbl/1-0/" }, { name: "DbCL", url: "https://opendatacommons.org/licenses/dbcl/1-0/" }],
    author: uploader ? { value: uploader, role: "publisher-reported uploader; independent authorship unverified", sourceField: text(raw?.uploader) ? paths.raw + "/uploader" : text(selected3?.uploader) ? paths.selected + "/uploader" : paths.catalogue + ".contributor" } : null,
    notices,
    adaptationProvenance: {
      retainedSourceSelection: adaptations,
      offmenuImageChanges: [],
      imageBytesFetched: false,
      imageBytesChanged: false,
      previousChanges: text(catalogue?.changes) || null,
      statement: "Metadata selection/URL construction only; no new image adaptation performed."
    },
    packagingRights: { status: "not-universally-cleared", qualification: "Packaging artwork and other underlying rights remain separate; the photo licence alone does not establish all permissions for a proposed use." },
    placement: "accessible-photo-details",
    compactHeaderCredit: false
  };
}
function retainedCataloguePhotoAttribution(entry, selectedSourceCode) {
  if (!object4(entry) || !code(entry.sourceCode) || entry.sourceCode !== selectedSourceCode || entry.license !== OFF_PHOTO_LICENSE.name || entry.licenseUrl !== OFF_PHOTO_LICENSE.url) return null;
  const photo = imageURL(entry.url, entry.sourceCode, "front");
  if (!photo || photo.revision !== entry.revision) return null;
  return {
    ...credit(entry.sourceCode, photo, { catalogue: entry }),
    retainedSourceUrl: entry.url,
    retainedSourcePage: entry.sourcePage,
    retainedPhotoLicensePage: entry.licensePage,
    imageId: entry.imageId,
    revision: entry.revision,
    sourceKind: "retained-fixed-catalogue-metadata",
    snapshotMembership: "unverified; current publisher observation only"
  };
}

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/off-photo-catalogue.js
var OFF_PHOTOS = Object.freeze([
  Object.freeze({
    key: "flour-front-en-rev5",
    sourceCode: "0078742003986",
    imageId: "1",
    revision: "5",
    path: "/api/off-photos/flour-front-en-rev5.jpg",
    url: "https://images.openfoodfacts.org/images/products/007/874/200/3986/front_en.5.400.jpg",
    sourcePage: "https://world.openfoodfacts.org/product/0078742003986/all-purpose-flour-great-value",
    licensePage: "https://world.openfoodfacts.org/cgi/product_image.pl?code=0078742003986&id=front_en",
    contributor: "foodless",
    license: "CC BY-SA 3.0",
    licenseUrl: "https://creativecommons.org/licenses/by-sa/3.0/"
  }),
  Object.freeze({
    key: "nutella-front-en-rev879",
    sourceCode: "3017620422003",
    imageId: "180",
    revision: "879",
    path: "/api/off-photos/nutella-front-en-rev879.jpg",
    url: "https://images.openfoodfacts.org/images/products/301/762/042/2003/front_en.879.400.jpg",
    sourcePage: "https://world.openfoodfacts.org/cgi/product_image.pl?code=3017620422003&id=front_en",
    licensePage: "https://world.openfoodfacts.org/cgi/product_image.pl?code=3017620422003&id=front_en",
    contributor: "org-ferrero-france-commerciale",
    license: "CC BY-SA 3.0",
    licenseUrl: "https://creativecommons.org/licenses/by-sa/3.0/"
  })
]);
function selectedPublisherPhotos(reference, detail) {
  if (reference?.schema !== "offmenu-identifier-observation/2" || reference.sourceId !== "off" || reference.namespace !== "barcode" || reference.disposition !== "source-asserted" || typeof detail?.referenceRecordId !== "string" || detail.sourceBinding?.sourceId !== "off" || detail.sourceObservation?.source_id !== "off" || detail.sourceObservation.lexical_value !== reference.sourceLexicalValue || detail.sourceObservation.release_id !== reference.releaseId || detail.sourceBinding.releaseId !== reference.releaseId || (detail.sourceObservation.source_record_id ?? null) !== (reference.sourceRecordId ?? null) || detail.sourceObservation.namespace !== "barcode" || detail.sourceObservation.disposition !== "source-asserted" || detail.observationKey?.databaseSha256 !== reference.databaseSha256 || ["run_id", "input_id", "record_ordinal", "assertion_id"].some((key) => detail.observationKey?.[key] !== reference.observationKey?.[key] || detail.sourceObservation[key] !== reference.observationKey?.[key]) || !detail.records?.[0]?.data?.identifiers?.some((id2) => id2.system === "barcode" && id2.value === reference.sourceLexicalValue)) return [];
  return OFF_PHOTOS.filter((photo) => photo.sourceCode === reference.sourceLexicalValue).map((photo) => ({
    sourceObservationReference: reference,
    productRecordId: detail.referenceRecordId,
    qualification: { state: "qualified", scope: "separately-observed-current-publisher-photo-for-exact-OFF-source-code" },
    role: "front",
    selectionRole: "selected-front",
    localAssetPath: photo.path,
    sourceUrl: photo.url,
    offlineAvailable: false,
    provenance: {
      sourceId: "off",
      releaseId: null,
      imageId: photo.imageId,
      revision: photo.revision,
      sourceCode: photo.sourceCode,
      sourcePage: photo.sourcePage,
      evidenceObservedDate: "2026-10-25",
      relationship: "current-publisher-photo; retained-snapshot-image-membership-unverified",
      contributor: photo.contributor,
      contributorRole: "publisher-reported-uploader; independent-authorship-unverified"
    },
    rights: {
      displayPermitted: true,
      license: photo.license,
      attribution: "Open Food Facts \xB7 contributor " + photo.contributor,
      licenseUrl: photo.licenseUrl,
      sourcePage: photo.sourcePage,
      photoLicensePage: photo.licensePage,
      changes: "Image bytes relayed unchanged; displayed to fit.",
      evidenceReference: "docs/off-publisher-photos.md#" + photo.key,
      attributionDetails: retainedCataloguePhotoAttribution(photo, reference.sourceLexicalValue)
    }
  }));
}

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/product-visual-association.js
var PRODUCT_VISUAL_ASSOCIATION = "offmenu-product-visual-association/1";
var REFERENCE_KEYS = [
  "schema",
  "databaseSha256",
  "runId",
  "namespace",
  "originalLexicalValue",
  "sourceLexicalValue",
  "symbology",
  "matchType",
  "equivalence",
  "disposition",
  "sourceId",
  "releaseId",
  "sourceRecordId",
  "detailSelectionSha256"
];
var OBSERVATION_KEYS = ["run_id", "input_id", "record_ordinal", "assertion_id"];
function referenceSnapshot(reference) {
  try {
    if (reference?.schema !== "offmenu-identifier-observation/2" || !validSourceObservationReference2(reference, reference.originalLexicalValue)) return null;
    return {
      ...Object.fromEntries(REFERENCE_KEYS.map((key) => [key, reference[key]])),
      observationKey: Object.fromEntries(OBSERVATION_KEYS.map((key) => [key, reference.observationKey[key]]))
    };
  } catch {
    return null;
  }
}
var VISUAL_CLASSIFICATION = "offmenu-product-visual-classification/1";
var textValue = (value) => typeof value === "string" && value.length > 0 && value.length <= 2e3 ? value : null;
function classificationSnapshot(reference, detail) {
  const empty = { state: "unresolved", evidenceReference: null, ingredientApplicability: { state: "unresolved", evidenceReference: null }, ingredientMappings: [], typeMappings: [], canonicalConcepts: [], permittedLocalAssets: [] };
  if (!reference) return empty;
  const projection = detail?.classificationProjection;
  try {
    validateClassificationProjection(projection);
  } catch {
    return empty;
  }
  const semantic = projection.classification;
  if (JSON.stringify(referenceSnapshot(projection.sourceBinding.sourceObservationReference)) !== JSON.stringify(reference)) return empty;
  const sourceRecordId = reference.sourceRecordId;
  if (typeof sourceRecordId !== "string" || !sourceRecordId || projection.sourceBinding.sourceRecordId !== sourceRecordId) return empty;
  for (const [binding, key] of [
    [detail?.sourceObservation, "source_record_id"],
    [detail?.sourceBinding, "identifierSourceRecordId"],
    [detail?.sourceBinding, "sourceRecordId"]
  ])
    if (binding && Object.hasOwn(binding, key) && binding[key] !== sourceRecordId) return empty;
  if (["unresolved", "conflict"].includes(semantic.disposition)) return {
    ...empty,
    state: semantic.disposition,
    semanticDisposition: semantic.disposition,
    semanticRelation: semantic.relation ?? null,
    ingredientApplicability: { state: semantic.ingredientApplicability, evidenceReference: null }
  };
  const semanticOnly = {
    ...empty,
    semanticDisposition: semantic.disposition,
    semanticRelation: semantic.relation ?? null,
    ingredientApplicability: { state: semantic.ingredientApplicability, evidenceReference: null }
  };
  const value = projection.visualClassification;
  if (!reference || value?.schema !== VISUAL_CLASSIFICATION || value.productRecordId !== detail.referenceRecordId || !value.productRecordId || value.qualification?.state !== "qualified" || !textValue(value.qualification.evidenceReference) || JSON.stringify(referenceSnapshot(value.sourceObservationReference)) !== JSON.stringify(reference)) return semanticOnly;
  const state = value.ingredientApplicability?.state;
  if (state !== semantic.ingredientApplicability) return semanticOnly;
  const applicability = ["applicable", "nonfood", "not-applicable"].includes(state) && textValue(value.ingredientApplicability.evidenceReference) ? { state, evidenceReference: value.ingredientApplicability.evidenceReference } : empty.ingredientApplicability;
  const mappings = (name) => (Array.isArray(value[name]) ? value[name] : []).slice(0, 100).filter((m) => m && typeof m === "object").map((m) => ({
    sourceObservationReference: referenceSnapshot(m.sourceObservationReference),
    productRecordId: m.productRecordId,
    status: m.status,
    relation: m.relation,
    conceptId: m.conceptId,
    taxonomyVersion: m.taxonomyVersion,
    crosswalkVersion: m.crosswalkVersion,
    originalSource: { term: m.originalSource?.term, code: m.originalSource?.code, language: m.originalSource?.language },
    provenance: { sourceId: m.provenance?.sourceId, releaseId: m.provenance?.releaseId, pointer: m.provenance?.pointer }
  }));
  const concepts = (Array.isArray(value.canonicalConcepts) ? value.canonicalConcepts : []).slice(0, 100).filter((c) => c && typeof c === "object").map((c) => ({
    conceptId: c.conceptId,
    taxonomyVersion: c.taxonomyVersion,
    kind: c.kind,
    definitionStatus: c.definitionStatus,
    preferredEnglishLabel: c.preferredEnglishLabel,
    presentation: {
      status: c.presentation?.status,
      evidenceReference: c.presentation?.evidenceReference,
      emoji: c.presentation?.emoji,
      localIconAssetPath: c.presentation?.localIconAssetPath,
      offlineAvailable: c.presentation?.offlineAvailable,
      iconRights: { displayPermitted: c.presentation?.iconRights?.displayPermitted, evidenceReference: c.presentation?.iconRights?.evidenceReference }
    }
  }));
  return {
    state: "qualified",
    semanticDisposition: semantic.disposition,
    semanticRelation: semantic.relation,
    evidenceReference: value.qualification.evidenceReference,
    ingredientApplicability: applicability,
    ingredientMappings: mappings("ingredientMappings"),
    typeMappings: mappings("typeMappings"),
    canonicalConcepts: concepts,
    permittedLocalAssets: (Array.isArray(value.permittedLocalAssets) ? value.permittedLocalAssets : []).filter(textValue).slice(0, 100)
  };
}
function prepare(input = {}) {
  const { reference = null, detail = null, name = "", theme = "light", offline = false, sourcePhotoSelection = null } = input ?? {};
  const retained = sourcePhotoSelection ? retainedSourcePhotoCandidate(sourcePhotoSelection, detail, { origin: input?.origin ?? globalThis.location?.origin }) : null;
  const native = retained?.state === "qualified";
  const selected3 = referenceSnapshot(native ? sourcePhotoSelection.reference : reference), appearance = { theme, offline };
  const selectedDetail = native ? { ...retained.assertion.binding, classificationProjection: retained.assertion.classificationProjection } : detail;
  const classification = classificationSnapshot(selected3, selectedDetail);
  if (!selected3) return { reference: null, input: null, appearance, classification, retained };
  const photoCandidates = sourcePhotoSelection ? native ? [retained.candidate] : [] : selectedPublisherPhotos(selected3, detail);
  return { reference: selected3, appearance, classification, retained, input: {
    sourceObservationReference: selected3,
    selectedProductRecordId: typeof selectedDetail?.referenceRecordId === "string" ? selectedDetail.referenceRecordId : null,
    sourceProductName: native ? "explicit independent source assertion" : typeof name === "string" ? name : "",
    theme,
    offline,
    photoCandidates,
    categoryMappings: [],
    ingredientMappings: classification.ingredientMappings,
    typeMappings: classification.typeMappings,
    canonicalConcepts: classification.canonicalConcepts,
    ingredientApplicability: classification.ingredientApplicability,
    classificationEvidenceReference: classification.evidenceReference,
    permittedLocalAssets: [...OFF_PHOTOS.map((photo) => photo.path), ...classification.permittedLocalAssets, ...native ? [sourcePhotoSelection.localAsset.path] : []]
  } };
}
function descriptor(prepared, visual) {
  return {
    schema: PRODUCT_VISUAL_ASSOCIATION,
    selectorVersion: PRODUCT_VISUAL_SELECTOR,
    sourceObservationReference: prepared.reference,
    productRecordId: visual.tier === "product-photo" ? prepared.input.selectedProductRecordId : null,
    sourcePhotoSelection: {
      state: prepared.retained?.state ?? "not-supplied",
      reasonCode: prepared.retained?.reasonCode ?? null,
      scope: prepared.retained?.state === "qualified" ? "explicit-independent-native-source-assertion" : null
    },
    associationState: visual.tier === "product-photo" ? "qualified-current-publisher-photo" : ["ingredient-illustration", "type-illustration"].includes(visual.tier) ? "qualified-canonical-illustration" : "unavailable",
    classification: {
      state: prepared.classification.state,
      semanticDisposition: prepared.classification.semanticDisposition ?? "unresolved",
      semanticRelation: prepared.classification.semanticRelation ?? null,
      evidenceReference: prepared.classification.evidenceReference,
      ingredientApplicability: prepared.classification.ingredientApplicability,
      selectedIcon: visual.evidence?.kind ? { kind: visual.evidence.kind, conceptId: visual.evidence.conceptId, taxonomyVersion: visual.evidence.taxonomyVersion } : null,
      meaning: "Visual classification supplies no recipe composition, nutrition or physical-product equivalence."
    },
    visual,
    category: {
      label: "Category",
      state: "unidentified",
      display: "Not yet identified",
      sourceCategory: {
        state: "not-loaded-by-association",
        claims: null,
        evidence: null,
        reasonCode: "SOURCE_CATEGORY_CLAIMS_REQUIRE_SEPARATELY_BOUND_DETAIL_EVIDENCE"
      },
      normalizedCategory: {
        state: "unknown",
        conceptId: null,
        preferredEnglishLabel: null,
        crosswalk: null,
        reasonCode: "NO_ACCEPTED_BACKING_STORE_QUALIFIED_CATEGORY_MAPPING"
      }
    },
    ingredientMatch: {
      label: "Ingredient match",
      state: "unidentified",
      display: "Not yet identified",
      conceptId: null,
      composition: null,
      evidence: null,
      reasonCode: "NO_ACCEPTED_BACKING_STORE_QUALIFIED_INGREDIENT_MAPPING"
    },
    evidence: {
      associationVersion: PRODUCT_VISUAL_ASSOCIATION,
      selectorVersion: PRODUCT_VISUAL_SELECTOR,
      sourceReferenceState: prepared.reference ? "valid-current-selected-contract" : "unavailable",
      sourceCategoryAndMappings: "Separate source claims, normalized category and ingredient authority required; photo qualification supplies none."
    }
  };
}
function associateProductVisual(input = {}, { failedSources = [] } = {}) {
  const prepared = prepare(input);
  const visual = prepared.input ? selectProductVisual(prepared.input, { failedSources }) : appProductVisualFallback(prepared.appearance, { failedSources });
  return descriptor(prepared, visual);
}
function afterProductVisualAssociationFailure(input, previous, { failedSources = [] } = {}) {
  const prepared = prepare(input);
  const visual = prepared.input ? afterVisualLoadFailure(prepared.input, previous?.visual, { failedSources }) : appProductVisualFallback(prepared.appearance, { failedSources: previous?.visual?.kind === "image" ? [...failedSources, previous.visual.src] : failedSources });
  return descriptor(prepared, visual);
}

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/scanner-product-visuals.js
function mountScannerProductVisual(thumbnail, captionRoot, { onChange = () => {
} } = {}) {
  const doc = thumbnail.ownerDocument;
  let epoch = 0, key = null, failed = [], current2 = null;
  const text2 = (tag, value) => {
    const node = doc.createElement(tag);
    node.textContent = value;
    return node;
  };
  function render2(input, turn, notify = false, previous = null) {
    const selected3 = input ?? { theme: doc.documentElement?.dataset.theme === "dark" ? "dark" : "light" };
    const retained = input?.retainedSourceCategoryPresentation;
    const association = (retained ? retainedCategoryAssociation(retained, input.sourceProductReference, selected3, failed) : null) || (previous ? afterProductVisualAssociationFailure(selected3, previous, { failedSources: failed }) : associateProductVisual(selected3, { failedSources: failed }));
    const result = input ? association.visual : { ...association.visual, alt: "OffMenu app icon; product photo unavailable" };
    current2 = result;
    thumbnail.replaceChildren();
    captionRoot.replaceChildren();
    thumbnail.dataset.visualTier = result.tier;
    if (result.kind === "image") {
      const image = doc.createElement("img");
      image.alt = result.alt;
      image.referrerPolicy = "no-referrer";
      if (result.tier === "app-fallback") image.dataset.offmenuLogo = "";
      image.onerror = () => {
        if (turn !== epoch || image !== thumbnail.firstChild) return;
        if (input) {
          failed = [.../* @__PURE__ */ new Set([...failed, result.src])];
          render2(input, turn, true, association);
        } else {
          thumbnail.replaceChildren(text2("span", "OffMenu"));
          current2 = { ...result, kind: "text", text: "OffMenu" };
          onChange(current2);
        }
      };
      image.src = result.src;
      thumbnail.append(image);
    } else thumbnail.append(text2("span", result.text));
    captionRoot.append(text2("p", result.caption));
    if (result.tier === "product-photo") {
      const details = text2("details", ""), credit2 = result.rights.attributionDetails;
      details.append(text2("summary", "Photo source and licence"), text2("p", result.rights.attribution));
      details.append(text2("p", result.provenance?.associationScope === "explicit-independent-native-source-assertion" ? "Photo from the selected source. The product variant and older-snapshot image membership are unverified." : "Current publisher photo; membership in the retained snapshot is unverified."));
      if (result.provenance?.associationScope === "explicit-independent-native-source-assertion") {
        details.append(text2("p", "Photo author and notices were not captured in the selected metadata; their absence is not established."));
        details.append(text2("p", "Image retrieved " + result.provenance.retrievedAt + "; metadata release " + result.provenance.metadataRelease + "."));
      }
      for (const [label, url] of [
        ["Product on Open Food Facts", credit2?.productUrl || result.rights.sourcePage],
        ["Photo source", result.rights.sourcePage],
        ["Photo licence", result.rights.photoLicensePage],
        [result.rights.license, result.rights.licenseUrl]
      ]) {
        const link = text2("a", label);
        link.href = url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        details.append(link);
      }
      for (const notice of credit2?.notices || []) details.append(text2("p", notice.field + ": " + notice.text));
      details.append(text2("p", result.rights.changes));
      if (credit2?.packagingRights?.qualification) details.append(text2("p", credit2.packagingRights.qualification));
      captionRoot.append(details);
    }
    if (notify) onChange(result);
    return result;
  }
  return { show({ reference = null, detail = null, entryId = null, generation: generation2 = null, name = "", theme = "light", offline = false, sourcePhotoSelection = null, sourceProductReference = null, retainedSourceCategoryPresentation = null } = {}) {
    const valid = reference && validSourceObservationReference2(reference, reference.originalLexicalValue);
    const nextKey = JSON.stringify([entryId, generation2, reference, detail?.referenceRecordId ?? null, sourcePhotoSelection, detail?.currentOutputUse, sourceProductReference, retainedSourceCategoryPresentation]);
    if (nextKey !== key) {
      failed = [];
      key = nextKey;
    }
    const turn = ++epoch;
    const retained = !valid && !sourcePhotoSelection && retainedCategoryAssociation(
      retainedSourceCategoryPresentation,
      sourceProductReference,
      { theme, offline },
      failed
    );
    const input = valid || sourcePhotoSelection ? { reference: valid ? reference : null, detail, name, theme, offline, sourcePhotoSelection } : retained ? { sourceProductReference, retainedSourceCategoryPresentation, name, theme, offline } : null;
    return render2(input, turn);
  }, current: () => current2, destroy() {
    epoch++;
    thumbnail.replaceChildren();
    captionRoot.replaceChildren();
  } };
}

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/public/production-scanner/scanner-three.js
var Ea = "180";
var Fo = 0;
var Ta = 1;
var Oo = 2;
var Aa = 1;
var Bo = 2;
var Je = 3;
var on = 0;
var ve = 1;
var $e = 2;
var hn = 0;
var On = 1;
var wa = 2;
var Ca = 3;
var Ra = 4;
var zo = 5;
var Mn = 100;
var Vo = 101;
var ko = 102;
var Ho = 103;
var Go = 104;
var Wo = 200;
var Xo = 201;
var qo = 202;
var Yo = 203;
var Ms = 204;
var Ss = 205;
var Zo = 206;
var Jo = 207;
var $o = 208;
var Ko = 209;
var Qo = 210;
var jo = 211;
var tl = 212;
var el = 213;
var nl = 214;
var Js = 0;
var $s = 1;
var Ks = 2;
var Bn = 3;
var Qs = 4;
var js = 5;
var tr = 6;
var er = 7;
var Ia = 0;
var il = 1;
var sl = 2;
var un = 0;
var rl = 1;
var al = 2;
var ol = 3;
var ll = 4;
var cl = 5;
var hl = 6;
var ul = 7;
var Pa = 300;
var Hn = 301;
var Gn = 302;
var nr = 303;
var ir = 304;
var qi = 306;
var bs = 1e3;
var yn = 1001;
var Es = 1002;
var Ne = 1003;
var dl = 1004;
var Yi = 1005;
var ke = 1006;
var sr = 1007;
var wn = 1008;
var We = 1009;
var La = 1010;
var Da = 1011;
var gi = 1012;
var rr = 1013;
var Cn = 1014;
var Ke = 1015;
var _i = 1016;
var ar = 1017;
var or = 1018;
var xi = 1020;
var Ua = 35902;
var Na = 35899;
var Fa = 1021;
var Oa = 1022;
var Fe = 1023;
var ci = 1026;
var vi = 1027;
var Ba = 1028;
var lr = 1029;
var za = 1030;
var cr = 1031;
var hr = 1033;
var Zi = 33776;
var Ji = 33777;
var $i = 33778;
var Ki = 33779;
var ur = 35840;
var dr = 35841;
var fr = 35842;
var pr = 35843;
var mr = 36196;
var gr = 37492;
var _r = 37496;
var xr = 37808;
var vr = 37809;
var yr = 37810;
var Mr = 37811;
var Sr = 37812;
var br = 37813;
var Er = 37814;
var Tr = 37815;
var Ar = 37816;
var wr = 37817;
var Cr = 37818;
var Rr = 37819;
var Ir = 37820;
var Pr = 37821;
var Lr = 36492;
var Dr = 36494;
var Ur = 36495;
var Nr = 36283;
var Fr = 36284;
var Or = 36285;
var Br = 36286;
var Ii = 2300;
var Ts = 2301;
var ys = 2302;
var ga = 2400;
var _a = 2401;
var xa = 2402;
var fl = 3200;
var pl = 3201;
var Va = 0;
var ml = 1;
var dn = "";
var we = "srgb";
var zn = "srgb-linear";
var Pi = "linear";
var qt = "srgb";
var Nn = 7680;
var va = 519;
var gl = 512;
var _l = 513;
var xl = 514;
var ka = 515;
var vl = 516;
var yl = 517;
var Ml = 518;
var Sl = 519;
var ya = 35044;
var Ha = "300 es";
var Ve = 2e3;
var Li = 2001;
var ln = class {
  addEventListener(t3, e) {
    this._listeners === void 0 && (this._listeners = {});
    let n = this._listeners;
    n[t3] === void 0 && (n[t3] = []), n[t3].indexOf(e) === -1 && n[t3].push(e);
  }
  hasEventListener(t3, e) {
    let n = this._listeners;
    return n === void 0 ? false : n[t3] !== void 0 && n[t3].indexOf(e) !== -1;
  }
  removeEventListener(t3, e) {
    let n = this._listeners;
    if (n === void 0) return;
    let s = n[t3];
    if (s !== void 0) {
      let r = s.indexOf(e);
      r !== -1 && s.splice(r, 1);
    }
  }
  dispatchEvent(t3) {
    let e = this._listeners;
    if (e === void 0) return;
    let n = e[t3.type];
    if (n !== void 0) {
      t3.target = this;
      let s = n.slice(0);
      for (let r = 0, a = s.length; r < a; r++) s[r].call(this, t3);
      t3.target = null;
    }
  }
};
var pe = ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09", "0a", "0b", "0c", "0d", "0e", "0f", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "1a", "1b", "1c", "1d", "1e", "1f", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "2a", "2b", "2c", "2d", "2e", "2f", "30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "3a", "3b", "3c", "3d", "3e", "3f", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49", "4a", "4b", "4c", "4d", "4e", "4f", "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "5a", "5b", "5c", "5d", "5e", "5f", "60", "61", "62", "63", "64", "65", "66", "67", "68", "69", "6a", "6b", "6c", "6d", "6e", "6f", "70", "71", "72", "73", "74", "75", "76", "77", "78", "79", "7a", "7b", "7c", "7d", "7e", "7f", "80", "81", "82", "83", "84", "85", "86", "87", "88", "89", "8a", "8b", "8c", "8d", "8e", "8f", "90", "91", "92", "93", "94", "95", "96", "97", "98", "99", "9a", "9b", "9c", "9d", "9e", "9f", "a0", "a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8", "a9", "aa", "ab", "ac", "ad", "ae", "af", "b0", "b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8", "b9", "ba", "bb", "bc", "bd", "be", "bf", "c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9", "ca", "cb", "cc", "cd", "ce", "cf", "d0", "d1", "d2", "d3", "d4", "d5", "d6", "d7", "d8", "d9", "da", "db", "dc", "dd", "de", "df", "e0", "e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8", "e9", "ea", "eb", "ec", "ed", "ee", "ef", "f0", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "fa", "fb", "fc", "fd", "fe", "ff"];
var qr = Math.PI / 180;
var As = 180 / Math.PI;
function Qi() {
  let i14 = Math.random() * 4294967295 | 0, t3 = Math.random() * 4294967295 | 0, e = Math.random() * 4294967295 | 0, n = Math.random() * 4294967295 | 0;
  return (pe[i14 & 255] + pe[i14 >> 8 & 255] + pe[i14 >> 16 & 255] + pe[i14 >> 24 & 255] + "-" + pe[t3 & 255] + pe[t3 >> 8 & 255] + "-" + pe[t3 >> 16 & 15 | 64] + pe[t3 >> 24 & 255] + "-" + pe[e & 63 | 128] + pe[e >> 8 & 255] + "-" + pe[e >> 16 & 255] + pe[e >> 24 & 255] + pe[n & 255] + pe[n >> 8 & 255] + pe[n >> 16 & 255] + pe[n >> 24 & 255]).toLowerCase();
}
function Bt(i14, t3, e) {
  return Math.max(t3, Math.min(e, i14));
}
function lc(i14, t3) {
  return (i14 % t3 + t3) % t3;
}
function Yr(i14, t3, e) {
  return (1 - e) * i14 + e * t3;
}
function Ti(i14, t3) {
  switch (t3.constructor) {
    case Float32Array:
      return i14;
    case Uint32Array:
      return i14 / 4294967295;
    case Uint16Array:
      return i14 / 65535;
    case Uint8Array:
      return i14 / 255;
    case Int32Array:
      return Math.max(i14 / 2147483647, -1);
    case Int16Array:
      return Math.max(i14 / 32767, -1);
    case Int8Array:
      return Math.max(i14 / 127, -1);
    default:
      throw new Error("Invalid component type.");
  }
}
function Me(i14, t3) {
  switch (t3.constructor) {
    case Float32Array:
      return i14;
    case Uint32Array:
      return Math.round(i14 * 4294967295);
    case Uint16Array:
      return Math.round(i14 * 65535);
    case Uint8Array:
      return Math.round(i14 * 255);
    case Int32Array:
      return Math.round(i14 * 2147483647);
    case Int16Array:
      return Math.round(i14 * 32767);
    case Int8Array:
      return Math.round(i14 * 127);
    default:
      throw new Error("Invalid component type.");
  }
}
var Gt = class i {
  constructor(t3 = 0, e = 0) {
    i.prototype.isVector2 = true, this.x = t3, this.y = e;
  }
  get width() {
    return this.x;
  }
  set width(t3) {
    this.x = t3;
  }
  get height() {
    return this.y;
  }
  set height(t3) {
    this.y = t3;
  }
  set(t3, e) {
    return this.x = t3, this.y = e, this;
  }
  setScalar(t3) {
    return this.x = t3, this.y = t3, this;
  }
  setX(t3) {
    return this.x = t3, this;
  }
  setY(t3) {
    return this.y = t3, this;
  }
  setComponent(t3, e) {
    switch (t3) {
      case 0:
        this.x = e;
        break;
      case 1:
        this.y = e;
        break;
      default:
        throw new Error("index is out of range: " + t3);
    }
    return this;
  }
  getComponent(t3) {
    switch (t3) {
      case 0:
        return this.x;
      case 1:
        return this.y;
      default:
        throw new Error("index is out of range: " + t3);
    }
  }
  clone() {
    return new this.constructor(this.x, this.y);
  }
  copy(t3) {
    return this.x = t3.x, this.y = t3.y, this;
  }
  add(t3) {
    return this.x += t3.x, this.y += t3.y, this;
  }
  addScalar(t3) {
    return this.x += t3, this.y += t3, this;
  }
  addVectors(t3, e) {
    return this.x = t3.x + e.x, this.y = t3.y + e.y, this;
  }
  addScaledVector(t3, e) {
    return this.x += t3.x * e, this.y += t3.y * e, this;
  }
  sub(t3) {
    return this.x -= t3.x, this.y -= t3.y, this;
  }
  subScalar(t3) {
    return this.x -= t3, this.y -= t3, this;
  }
  subVectors(t3, e) {
    return this.x = t3.x - e.x, this.y = t3.y - e.y, this;
  }
  multiply(t3) {
    return this.x *= t3.x, this.y *= t3.y, this;
  }
  multiplyScalar(t3) {
    return this.x *= t3, this.y *= t3, this;
  }
  divide(t3) {
    return this.x /= t3.x, this.y /= t3.y, this;
  }
  divideScalar(t3) {
    return this.multiplyScalar(1 / t3);
  }
  applyMatrix3(t3) {
    let e = this.x, n = this.y, s = t3.elements;
    return this.x = s[0] * e + s[3] * n + s[6], this.y = s[1] * e + s[4] * n + s[7], this;
  }
  min(t3) {
    return this.x = Math.min(this.x, t3.x), this.y = Math.min(this.y, t3.y), this;
  }
  max(t3) {
    return this.x = Math.max(this.x, t3.x), this.y = Math.max(this.y, t3.y), this;
  }
  clamp(t3, e) {
    return this.x = Bt(this.x, t3.x, e.x), this.y = Bt(this.y, t3.y, e.y), this;
  }
  clampScalar(t3, e) {
    return this.x = Bt(this.x, t3, e), this.y = Bt(this.y, t3, e), this;
  }
  clampLength(t3, e) {
    let n = this.length();
    return this.divideScalar(n || 1).multiplyScalar(Bt(n, t3, e));
  }
  floor() {
    return this.x = Math.floor(this.x), this.y = Math.floor(this.y), this;
  }
  ceil() {
    return this.x = Math.ceil(this.x), this.y = Math.ceil(this.y), this;
  }
  round() {
    return this.x = Math.round(this.x), this.y = Math.round(this.y), this;
  }
  roundToZero() {
    return this.x = Math.trunc(this.x), this.y = Math.trunc(this.y), this;
  }
  negate() {
    return this.x = -this.x, this.y = -this.y, this;
  }
  dot(t3) {
    return this.x * t3.x + this.y * t3.y;
  }
  cross(t3) {
    return this.x * t3.y - this.y * t3.x;
  }
  lengthSq() {
    return this.x * this.x + this.y * this.y;
  }
  length() {
    return Math.sqrt(this.x * this.x + this.y * this.y);
  }
  manhattanLength() {
    return Math.abs(this.x) + Math.abs(this.y);
  }
  normalize() {
    return this.divideScalar(this.length() || 1);
  }
  angle() {
    return Math.atan2(-this.y, -this.x) + Math.PI;
  }
  angleTo(t3) {
    let e = Math.sqrt(this.lengthSq() * t3.lengthSq());
    if (e === 0) return Math.PI / 2;
    let n = this.dot(t3) / e;
    return Math.acos(Bt(n, -1, 1));
  }
  distanceTo(t3) {
    return Math.sqrt(this.distanceToSquared(t3));
  }
  distanceToSquared(t3) {
    let e = this.x - t3.x, n = this.y - t3.y;
    return e * e + n * n;
  }
  manhattanDistanceTo(t3) {
    return Math.abs(this.x - t3.x) + Math.abs(this.y - t3.y);
  }
  setLength(t3) {
    return this.normalize().multiplyScalar(t3);
  }
  lerp(t3, e) {
    return this.x += (t3.x - this.x) * e, this.y += (t3.y - this.y) * e, this;
  }
  lerpVectors(t3, e, n) {
    return this.x = t3.x + (e.x - t3.x) * n, this.y = t3.y + (e.y - t3.y) * n, this;
  }
  equals(t3) {
    return t3.x === this.x && t3.y === this.y;
  }
  fromArray(t3, e = 0) {
    return this.x = t3[e], this.y = t3[e + 1], this;
  }
  toArray(t3 = [], e = 0) {
    return t3[e] = this.x, t3[e + 1] = this.y, t3;
  }
  fromBufferAttribute(t3, e) {
    return this.x = t3.getX(e), this.y = t3.getY(e), this;
  }
  rotateAround(t3, e) {
    let n = Math.cos(e), s = Math.sin(e), r = this.x - t3.x, a = this.y - t3.y;
    return this.x = r * n - a * s + t3.x, this.y = r * s + a * n + t3.y, this;
  }
  random() {
    return this.x = Math.random(), this.y = Math.random(), this;
  }
  *[Symbol.iterator]() {
    yield this.x, yield this.y;
  }
};
var cn = class {
  constructor(t3 = 0, e = 0, n = 0, s = 1) {
    this.isQuaternion = true, this._x = t3, this._y = e, this._z = n, this._w = s;
  }
  static slerpFlat(t3, e, n, s, r, a, o) {
    let c = n[s + 0], l = n[s + 1], u = n[s + 2], d = n[s + 3], f = r[a + 0], m = r[a + 1], x = r[a + 2], v = r[a + 3];
    if (o === 0) {
      t3[e + 0] = c, t3[e + 1] = l, t3[e + 2] = u, t3[e + 3] = d;
      return;
    }
    if (o === 1) {
      t3[e + 0] = f, t3[e + 1] = m, t3[e + 2] = x, t3[e + 3] = v;
      return;
    }
    if (d !== v || c !== f || l !== m || u !== x) {
      let p = 1 - o, h = c * f + l * m + u * x + d * v, A = h >= 0 ? 1 : -1, T = 1 - h * h;
      if (T > Number.EPSILON) {
        let R = Math.sqrt(T), w = Math.atan2(R, h * A);
        p = Math.sin(p * w) / R, o = Math.sin(o * w) / R;
      }
      let b = o * A;
      if (c = c * p + f * b, l = l * p + m * b, u = u * p + x * b, d = d * p + v * b, p === 1 - o) {
        let R = 1 / Math.sqrt(c * c + l * l + u * u + d * d);
        c *= R, l *= R, u *= R, d *= R;
      }
    }
    t3[e] = c, t3[e + 1] = l, t3[e + 2] = u, t3[e + 3] = d;
  }
  static multiplyQuaternionsFlat(t3, e, n, s, r, a) {
    let o = n[s], c = n[s + 1], l = n[s + 2], u = n[s + 3], d = r[a], f = r[a + 1], m = r[a + 2], x = r[a + 3];
    return t3[e] = o * x + u * d + c * m - l * f, t3[e + 1] = c * x + u * f + l * d - o * m, t3[e + 2] = l * x + u * m + o * f - c * d, t3[e + 3] = u * x - o * d - c * f - l * m, t3;
  }
  get x() {
    return this._x;
  }
  set x(t3) {
    this._x = t3, this._onChangeCallback();
  }
  get y() {
    return this._y;
  }
  set y(t3) {
    this._y = t3, this._onChangeCallback();
  }
  get z() {
    return this._z;
  }
  set z(t3) {
    this._z = t3, this._onChangeCallback();
  }
  get w() {
    return this._w;
  }
  set w(t3) {
    this._w = t3, this._onChangeCallback();
  }
  set(t3, e, n, s) {
    return this._x = t3, this._y = e, this._z = n, this._w = s, this._onChangeCallback(), this;
  }
  clone() {
    return new this.constructor(this._x, this._y, this._z, this._w);
  }
  copy(t3) {
    return this._x = t3.x, this._y = t3.y, this._z = t3.z, this._w = t3.w, this._onChangeCallback(), this;
  }
  setFromEuler(t3, e = true) {
    let n = t3._x, s = t3._y, r = t3._z, a = t3._order, o = Math.cos, c = Math.sin, l = o(n / 2), u = o(s / 2), d = o(r / 2), f = c(n / 2), m = c(s / 2), x = c(r / 2);
    switch (a) {
      case "XYZ":
        this._x = f * u * d + l * m * x, this._y = l * m * d - f * u * x, this._z = l * u * x + f * m * d, this._w = l * u * d - f * m * x;
        break;
      case "YXZ":
        this._x = f * u * d + l * m * x, this._y = l * m * d - f * u * x, this._z = l * u * x - f * m * d, this._w = l * u * d + f * m * x;
        break;
      case "ZXY":
        this._x = f * u * d - l * m * x, this._y = l * m * d + f * u * x, this._z = l * u * x + f * m * d, this._w = l * u * d - f * m * x;
        break;
      case "ZYX":
        this._x = f * u * d - l * m * x, this._y = l * m * d + f * u * x, this._z = l * u * x - f * m * d, this._w = l * u * d + f * m * x;
        break;
      case "YZX":
        this._x = f * u * d + l * m * x, this._y = l * m * d + f * u * x, this._z = l * u * x - f * m * d, this._w = l * u * d - f * m * x;
        break;
      case "XZY":
        this._x = f * u * d - l * m * x, this._y = l * m * d - f * u * x, this._z = l * u * x + f * m * d, this._w = l * u * d + f * m * x;
        break;
      default:
        console.warn("THREE.Quaternion: .setFromEuler() encountered an unknown order: " + a);
    }
    return e === true && this._onChangeCallback(), this;
  }
  setFromAxisAngle(t3, e) {
    let n = e / 2, s = Math.sin(n);
    return this._x = t3.x * s, this._y = t3.y * s, this._z = t3.z * s, this._w = Math.cos(n), this._onChangeCallback(), this;
  }
  setFromRotationMatrix(t3) {
    let e = t3.elements, n = e[0], s = e[4], r = e[8], a = e[1], o = e[5], c = e[9], l = e[2], u = e[6], d = e[10], f = n + o + d;
    if (f > 0) {
      let m = 0.5 / Math.sqrt(f + 1);
      this._w = 0.25 / m, this._x = (u - c) * m, this._y = (r - l) * m, this._z = (a - s) * m;
    } else if (n > o && n > d) {
      let m = 2 * Math.sqrt(1 + n - o - d);
      this._w = (u - c) / m, this._x = 0.25 * m, this._y = (s + a) / m, this._z = (r + l) / m;
    } else if (o > d) {
      let m = 2 * Math.sqrt(1 + o - n - d);
      this._w = (r - l) / m, this._x = (s + a) / m, this._y = 0.25 * m, this._z = (c + u) / m;
    } else {
      let m = 2 * Math.sqrt(1 + d - n - o);
      this._w = (a - s) / m, this._x = (r + l) / m, this._y = (c + u) / m, this._z = 0.25 * m;
    }
    return this._onChangeCallback(), this;
  }
  setFromUnitVectors(t3, e) {
    let n = t3.dot(e) + 1;
    return n < 1e-8 ? (n = 0, Math.abs(t3.x) > Math.abs(t3.z) ? (this._x = -t3.y, this._y = t3.x, this._z = 0, this._w = n) : (this._x = 0, this._y = -t3.z, this._z = t3.y, this._w = n)) : (this._x = t3.y * e.z - t3.z * e.y, this._y = t3.z * e.x - t3.x * e.z, this._z = t3.x * e.y - t3.y * e.x, this._w = n), this.normalize();
  }
  angleTo(t3) {
    return 2 * Math.acos(Math.abs(Bt(this.dot(t3), -1, 1)));
  }
  rotateTowards(t3, e) {
    let n = this.angleTo(t3);
    if (n === 0) return this;
    let s = Math.min(1, e / n);
    return this.slerp(t3, s), this;
  }
  identity() {
    return this.set(0, 0, 0, 1);
  }
  invert() {
    return this.conjugate();
  }
  conjugate() {
    return this._x *= -1, this._y *= -1, this._z *= -1, this._onChangeCallback(), this;
  }
  dot(t3) {
    return this._x * t3._x + this._y * t3._y + this._z * t3._z + this._w * t3._w;
  }
  lengthSq() {
    return this._x * this._x + this._y * this._y + this._z * this._z + this._w * this._w;
  }
  length() {
    return Math.sqrt(this._x * this._x + this._y * this._y + this._z * this._z + this._w * this._w);
  }
  normalize() {
    let t3 = this.length();
    return t3 === 0 ? (this._x = 0, this._y = 0, this._z = 0, this._w = 1) : (t3 = 1 / t3, this._x = this._x * t3, this._y = this._y * t3, this._z = this._z * t3, this._w = this._w * t3), this._onChangeCallback(), this;
  }
  multiply(t3) {
    return this.multiplyQuaternions(this, t3);
  }
  premultiply(t3) {
    return this.multiplyQuaternions(t3, this);
  }
  multiplyQuaternions(t3, e) {
    let n = t3._x, s = t3._y, r = t3._z, a = t3._w, o = e._x, c = e._y, l = e._z, u = e._w;
    return this._x = n * u + a * o + s * l - r * c, this._y = s * u + a * c + r * o - n * l, this._z = r * u + a * l + n * c - s * o, this._w = a * u - n * o - s * c - r * l, this._onChangeCallback(), this;
  }
  slerp(t3, e) {
    if (e === 0) return this;
    if (e === 1) return this.copy(t3);
    let n = this._x, s = this._y, r = this._z, a = this._w, o = a * t3._w + n * t3._x + s * t3._y + r * t3._z;
    if (o < 0 ? (this._w = -t3._w, this._x = -t3._x, this._y = -t3._y, this._z = -t3._z, o = -o) : this.copy(t3), o >= 1) return this._w = a, this._x = n, this._y = s, this._z = r, this;
    let c = 1 - o * o;
    if (c <= Number.EPSILON) {
      let m = 1 - e;
      return this._w = m * a + e * this._w, this._x = m * n + e * this._x, this._y = m * s + e * this._y, this._z = m * r + e * this._z, this.normalize(), this;
    }
    let l = Math.sqrt(c), u = Math.atan2(l, o), d = Math.sin((1 - e) * u) / l, f = Math.sin(e * u) / l;
    return this._w = a * d + this._w * f, this._x = n * d + this._x * f, this._y = s * d + this._y * f, this._z = r * d + this._z * f, this._onChangeCallback(), this;
  }
  slerpQuaternions(t3, e, n) {
    return this.copy(t3).slerp(e, n);
  }
  random() {
    let t3 = 2 * Math.PI * Math.random(), e = 2 * Math.PI * Math.random(), n = Math.random(), s = Math.sqrt(1 - n), r = Math.sqrt(n);
    return this.set(s * Math.sin(t3), s * Math.cos(t3), r * Math.sin(e), r * Math.cos(e));
  }
  equals(t3) {
    return t3._x === this._x && t3._y === this._y && t3._z === this._z && t3._w === this._w;
  }
  fromArray(t3, e = 0) {
    return this._x = t3[e], this._y = t3[e + 1], this._z = t3[e + 2], this._w = t3[e + 3], this._onChangeCallback(), this;
  }
  toArray(t3 = [], e = 0) {
    return t3[e] = this._x, t3[e + 1] = this._y, t3[e + 2] = this._z, t3[e + 3] = this._w, t3;
  }
  fromBufferAttribute(t3, e) {
    return this._x = t3.getX(e), this._y = t3.getY(e), this._z = t3.getZ(e), this._w = t3.getW(e), this._onChangeCallback(), this;
  }
  toJSON() {
    return this.toArray();
  }
  _onChange(t3) {
    return this._onChangeCallback = t3, this;
  }
  _onChangeCallback() {
  }
  *[Symbol.iterator]() {
    yield this._x, yield this._y, yield this._z, yield this._w;
  }
};
var F = class i2 {
  constructor(t3 = 0, e = 0, n = 0) {
    i2.prototype.isVector3 = true, this.x = t3, this.y = e, this.z = n;
  }
  set(t3, e, n) {
    return n === void 0 && (n = this.z), this.x = t3, this.y = e, this.z = n, this;
  }
  setScalar(t3) {
    return this.x = t3, this.y = t3, this.z = t3, this;
  }
  setX(t3) {
    return this.x = t3, this;
  }
  setY(t3) {
    return this.y = t3, this;
  }
  setZ(t3) {
    return this.z = t3, this;
  }
  setComponent(t3, e) {
    switch (t3) {
      case 0:
        this.x = e;
        break;
      case 1:
        this.y = e;
        break;
      case 2:
        this.z = e;
        break;
      default:
        throw new Error("index is out of range: " + t3);
    }
    return this;
  }
  getComponent(t3) {
    switch (t3) {
      case 0:
        return this.x;
      case 1:
        return this.y;
      case 2:
        return this.z;
      default:
        throw new Error("index is out of range: " + t3);
    }
  }
  clone() {
    return new this.constructor(this.x, this.y, this.z);
  }
  copy(t3) {
    return this.x = t3.x, this.y = t3.y, this.z = t3.z, this;
  }
  add(t3) {
    return this.x += t3.x, this.y += t3.y, this.z += t3.z, this;
  }
  addScalar(t3) {
    return this.x += t3, this.y += t3, this.z += t3, this;
  }
  addVectors(t3, e) {
    return this.x = t3.x + e.x, this.y = t3.y + e.y, this.z = t3.z + e.z, this;
  }
  addScaledVector(t3, e) {
    return this.x += t3.x * e, this.y += t3.y * e, this.z += t3.z * e, this;
  }
  sub(t3) {
    return this.x -= t3.x, this.y -= t3.y, this.z -= t3.z, this;
  }
  subScalar(t3) {
    return this.x -= t3, this.y -= t3, this.z -= t3, this;
  }
  subVectors(t3, e) {
    return this.x = t3.x - e.x, this.y = t3.y - e.y, this.z = t3.z - e.z, this;
  }
  multiply(t3) {
    return this.x *= t3.x, this.y *= t3.y, this.z *= t3.z, this;
  }
  multiplyScalar(t3) {
    return this.x *= t3, this.y *= t3, this.z *= t3, this;
  }
  multiplyVectors(t3, e) {
    return this.x = t3.x * e.x, this.y = t3.y * e.y, this.z = t3.z * e.z, this;
  }
  applyEuler(t3) {
    return this.applyQuaternion(_o.setFromEuler(t3));
  }
  applyAxisAngle(t3, e) {
    return this.applyQuaternion(_o.setFromAxisAngle(t3, e));
  }
  applyMatrix3(t3) {
    let e = this.x, n = this.y, s = this.z, r = t3.elements;
    return this.x = r[0] * e + r[3] * n + r[6] * s, this.y = r[1] * e + r[4] * n + r[7] * s, this.z = r[2] * e + r[5] * n + r[8] * s, this;
  }
  applyNormalMatrix(t3) {
    return this.applyMatrix3(t3).normalize();
  }
  applyMatrix4(t3) {
    let e = this.x, n = this.y, s = this.z, r = t3.elements, a = 1 / (r[3] * e + r[7] * n + r[11] * s + r[15]);
    return this.x = (r[0] * e + r[4] * n + r[8] * s + r[12]) * a, this.y = (r[1] * e + r[5] * n + r[9] * s + r[13]) * a, this.z = (r[2] * e + r[6] * n + r[10] * s + r[14]) * a, this;
  }
  applyQuaternion(t3) {
    let e = this.x, n = this.y, s = this.z, r = t3.x, a = t3.y, o = t3.z, c = t3.w, l = 2 * (a * s - o * n), u = 2 * (o * e - r * s), d = 2 * (r * n - a * e);
    return this.x = e + c * l + a * d - o * u, this.y = n + c * u + o * l - r * d, this.z = s + c * d + r * u - a * l, this;
  }
  project(t3) {
    return this.applyMatrix4(t3.matrixWorldInverse).applyMatrix4(t3.projectionMatrix);
  }
  unproject(t3) {
    return this.applyMatrix4(t3.projectionMatrixInverse).applyMatrix4(t3.matrixWorld);
  }
  transformDirection(t3) {
    let e = this.x, n = this.y, s = this.z, r = t3.elements;
    return this.x = r[0] * e + r[4] * n + r[8] * s, this.y = r[1] * e + r[5] * n + r[9] * s, this.z = r[2] * e + r[6] * n + r[10] * s, this.normalize();
  }
  divide(t3) {
    return this.x /= t3.x, this.y /= t3.y, this.z /= t3.z, this;
  }
  divideScalar(t3) {
    return this.multiplyScalar(1 / t3);
  }
  min(t3) {
    return this.x = Math.min(this.x, t3.x), this.y = Math.min(this.y, t3.y), this.z = Math.min(this.z, t3.z), this;
  }
  max(t3) {
    return this.x = Math.max(this.x, t3.x), this.y = Math.max(this.y, t3.y), this.z = Math.max(this.z, t3.z), this;
  }
  clamp(t3, e) {
    return this.x = Bt(this.x, t3.x, e.x), this.y = Bt(this.y, t3.y, e.y), this.z = Bt(this.z, t3.z, e.z), this;
  }
  clampScalar(t3, e) {
    return this.x = Bt(this.x, t3, e), this.y = Bt(this.y, t3, e), this.z = Bt(this.z, t3, e), this;
  }
  clampLength(t3, e) {
    let n = this.length();
    return this.divideScalar(n || 1).multiplyScalar(Bt(n, t3, e));
  }
  floor() {
    return this.x = Math.floor(this.x), this.y = Math.floor(this.y), this.z = Math.floor(this.z), this;
  }
  ceil() {
    return this.x = Math.ceil(this.x), this.y = Math.ceil(this.y), this.z = Math.ceil(this.z), this;
  }
  round() {
    return this.x = Math.round(this.x), this.y = Math.round(this.y), this.z = Math.round(this.z), this;
  }
  roundToZero() {
    return this.x = Math.trunc(this.x), this.y = Math.trunc(this.y), this.z = Math.trunc(this.z), this;
  }
  negate() {
    return this.x = -this.x, this.y = -this.y, this.z = -this.z, this;
  }
  dot(t3) {
    return this.x * t3.x + this.y * t3.y + this.z * t3.z;
  }
  lengthSq() {
    return this.x * this.x + this.y * this.y + this.z * this.z;
  }
  length() {
    return Math.sqrt(this.x * this.x + this.y * this.y + this.z * this.z);
  }
  manhattanLength() {
    return Math.abs(this.x) + Math.abs(this.y) + Math.abs(this.z);
  }
  normalize() {
    return this.divideScalar(this.length() || 1);
  }
  setLength(t3) {
    return this.normalize().multiplyScalar(t3);
  }
  lerp(t3, e) {
    return this.x += (t3.x - this.x) * e, this.y += (t3.y - this.y) * e, this.z += (t3.z - this.z) * e, this;
  }
  lerpVectors(t3, e, n) {
    return this.x = t3.x + (e.x - t3.x) * n, this.y = t3.y + (e.y - t3.y) * n, this.z = t3.z + (e.z - t3.z) * n, this;
  }
  cross(t3) {
    return this.crossVectors(this, t3);
  }
  crossVectors(t3, e) {
    let n = t3.x, s = t3.y, r = t3.z, a = e.x, o = e.y, c = e.z;
    return this.x = s * c - r * o, this.y = r * a - n * c, this.z = n * o - s * a, this;
  }
  projectOnVector(t3) {
    let e = t3.lengthSq();
    if (e === 0) return this.set(0, 0, 0);
    let n = t3.dot(this) / e;
    return this.copy(t3).multiplyScalar(n);
  }
  projectOnPlane(t3) {
    return Zr.copy(this).projectOnVector(t3), this.sub(Zr);
  }
  reflect(t3) {
    return this.sub(Zr.copy(t3).multiplyScalar(2 * this.dot(t3)));
  }
  angleTo(t3) {
    let e = Math.sqrt(this.lengthSq() * t3.lengthSq());
    if (e === 0) return Math.PI / 2;
    let n = this.dot(t3) / e;
    return Math.acos(Bt(n, -1, 1));
  }
  distanceTo(t3) {
    return Math.sqrt(this.distanceToSquared(t3));
  }
  distanceToSquared(t3) {
    let e = this.x - t3.x, n = this.y - t3.y, s = this.z - t3.z;
    return e * e + n * n + s * s;
  }
  manhattanDistanceTo(t3) {
    return Math.abs(this.x - t3.x) + Math.abs(this.y - t3.y) + Math.abs(this.z - t3.z);
  }
  setFromSpherical(t3) {
    return this.setFromSphericalCoords(t3.radius, t3.phi, t3.theta);
  }
  setFromSphericalCoords(t3, e, n) {
    let s = Math.sin(e) * t3;
    return this.x = s * Math.sin(n), this.y = Math.cos(e) * t3, this.z = s * Math.cos(n), this;
  }
  setFromCylindrical(t3) {
    return this.setFromCylindricalCoords(t3.radius, t3.theta, t3.y);
  }
  setFromCylindricalCoords(t3, e, n) {
    return this.x = t3 * Math.sin(e), this.y = n, this.z = t3 * Math.cos(e), this;
  }
  setFromMatrixPosition(t3) {
    let e = t3.elements;
    return this.x = e[12], this.y = e[13], this.z = e[14], this;
  }
  setFromMatrixScale(t3) {
    let e = this.setFromMatrixColumn(t3, 0).length(), n = this.setFromMatrixColumn(t3, 1).length(), s = this.setFromMatrixColumn(t3, 2).length();
    return this.x = e, this.y = n, this.z = s, this;
  }
  setFromMatrixColumn(t3, e) {
    return this.fromArray(t3.elements, e * 4);
  }
  setFromMatrix3Column(t3, e) {
    return this.fromArray(t3.elements, e * 3);
  }
  setFromEuler(t3) {
    return this.x = t3._x, this.y = t3._y, this.z = t3._z, this;
  }
  setFromColor(t3) {
    return this.x = t3.r, this.y = t3.g, this.z = t3.b, this;
  }
  equals(t3) {
    return t3.x === this.x && t3.y === this.y && t3.z === this.z;
  }
  fromArray(t3, e = 0) {
    return this.x = t3[e], this.y = t3[e + 1], this.z = t3[e + 2], this;
  }
  toArray(t3 = [], e = 0) {
    return t3[e] = this.x, t3[e + 1] = this.y, t3[e + 2] = this.z, t3;
  }
  fromBufferAttribute(t3, e) {
    return this.x = t3.getX(e), this.y = t3.getY(e), this.z = t3.getZ(e), this;
  }
  random() {
    return this.x = Math.random(), this.y = Math.random(), this.z = Math.random(), this;
  }
  randomDirection() {
    let t3 = Math.random() * Math.PI * 2, e = Math.random() * 2 - 1, n = Math.sqrt(1 - e * e);
    return this.x = n * Math.cos(t3), this.y = e, this.z = n * Math.sin(t3), this;
  }
  *[Symbol.iterator]() {
    yield this.x, yield this.y, yield this.z;
  }
};
var Zr = new F();
var _o = new cn();
var Lt = class i3 {
  constructor(t3, e, n, s, r, a, o, c, l) {
    i3.prototype.isMatrix3 = true, this.elements = [1, 0, 0, 0, 1, 0, 0, 0, 1], t3 !== void 0 && this.set(t3, e, n, s, r, a, o, c, l);
  }
  set(t3, e, n, s, r, a, o, c, l) {
    let u = this.elements;
    return u[0] = t3, u[1] = s, u[2] = o, u[3] = e, u[4] = r, u[5] = c, u[6] = n, u[7] = a, u[8] = l, this;
  }
  identity() {
    return this.set(1, 0, 0, 0, 1, 0, 0, 0, 1), this;
  }
  copy(t3) {
    let e = this.elements, n = t3.elements;
    return e[0] = n[0], e[1] = n[1], e[2] = n[2], e[3] = n[3], e[4] = n[4], e[5] = n[5], e[6] = n[6], e[7] = n[7], e[8] = n[8], this;
  }
  extractBasis(t3, e, n) {
    return t3.setFromMatrix3Column(this, 0), e.setFromMatrix3Column(this, 1), n.setFromMatrix3Column(this, 2), this;
  }
  setFromMatrix4(t3) {
    let e = t3.elements;
    return this.set(e[0], e[4], e[8], e[1], e[5], e[9], e[2], e[6], e[10]), this;
  }
  multiply(t3) {
    return this.multiplyMatrices(this, t3);
  }
  premultiply(t3) {
    return this.multiplyMatrices(t3, this);
  }
  multiplyMatrices(t3, e) {
    let n = t3.elements, s = e.elements, r = this.elements, a = n[0], o = n[3], c = n[6], l = n[1], u = n[4], d = n[7], f = n[2], m = n[5], x = n[8], v = s[0], p = s[3], h = s[6], A = s[1], T = s[4], b = s[7], R = s[2], w = s[5], P = s[8];
    return r[0] = a * v + o * A + c * R, r[3] = a * p + o * T + c * w, r[6] = a * h + o * b + c * P, r[1] = l * v + u * A + d * R, r[4] = l * p + u * T + d * w, r[7] = l * h + u * b + d * P, r[2] = f * v + m * A + x * R, r[5] = f * p + m * T + x * w, r[8] = f * h + m * b + x * P, this;
  }
  multiplyScalar(t3) {
    let e = this.elements;
    return e[0] *= t3, e[3] *= t3, e[6] *= t3, e[1] *= t3, e[4] *= t3, e[7] *= t3, e[2] *= t3, e[5] *= t3, e[8] *= t3, this;
  }
  determinant() {
    let t3 = this.elements, e = t3[0], n = t3[1], s = t3[2], r = t3[3], a = t3[4], o = t3[5], c = t3[6], l = t3[7], u = t3[8];
    return e * a * u - e * o * l - n * r * u + n * o * c + s * r * l - s * a * c;
  }
  invert() {
    let t3 = this.elements, e = t3[0], n = t3[1], s = t3[2], r = t3[3], a = t3[4], o = t3[5], c = t3[6], l = t3[7], u = t3[8], d = u * a - o * l, f = o * c - u * r, m = l * r - a * c, x = e * d + n * f + s * m;
    if (x === 0) return this.set(0, 0, 0, 0, 0, 0, 0, 0, 0);
    let v = 1 / x;
    return t3[0] = d * v, t3[1] = (s * l - u * n) * v, t3[2] = (o * n - s * a) * v, t3[3] = f * v, t3[4] = (u * e - s * c) * v, t3[5] = (s * r - o * e) * v, t3[6] = m * v, t3[7] = (n * c - l * e) * v, t3[8] = (a * e - n * r) * v, this;
  }
  transpose() {
    let t3, e = this.elements;
    return t3 = e[1], e[1] = e[3], e[3] = t3, t3 = e[2], e[2] = e[6], e[6] = t3, t3 = e[5], e[5] = e[7], e[7] = t3, this;
  }
  getNormalMatrix(t3) {
    return this.setFromMatrix4(t3).invert().transpose();
  }
  transposeIntoArray(t3) {
    let e = this.elements;
    return t3[0] = e[0], t3[1] = e[3], t3[2] = e[6], t3[3] = e[1], t3[4] = e[4], t3[5] = e[7], t3[6] = e[2], t3[7] = e[5], t3[8] = e[8], this;
  }
  setUvTransform(t3, e, n, s, r, a, o) {
    let c = Math.cos(r), l = Math.sin(r);
    return this.set(n * c, n * l, -n * (c * a + l * o) + a + t3, -s * l, s * c, -s * (-l * a + c * o) + o + e, 0, 0, 1), this;
  }
  scale(t3, e) {
    return this.premultiply(Jr.makeScale(t3, e)), this;
  }
  rotate(t3) {
    return this.premultiply(Jr.makeRotation(-t3)), this;
  }
  translate(t3, e) {
    return this.premultiply(Jr.makeTranslation(t3, e)), this;
  }
  makeTranslation(t3, e) {
    return t3.isVector2 ? this.set(1, 0, t3.x, 0, 1, t3.y, 0, 0, 1) : this.set(1, 0, t3, 0, 1, e, 0, 0, 1), this;
  }
  makeRotation(t3) {
    let e = Math.cos(t3), n = Math.sin(t3);
    return this.set(e, -n, 0, n, e, 0, 0, 0, 1), this;
  }
  makeScale(t3, e) {
    return this.set(t3, 0, 0, 0, e, 0, 0, 0, 1), this;
  }
  equals(t3) {
    let e = this.elements, n = t3.elements;
    for (let s = 0; s < 9; s++) if (e[s] !== n[s]) return false;
    return true;
  }
  fromArray(t3, e = 0) {
    for (let n = 0; n < 9; n++) this.elements[n] = t3[n + e];
    return this;
  }
  toArray(t3 = [], e = 0) {
    let n = this.elements;
    return t3[e] = n[0], t3[e + 1] = n[1], t3[e + 2] = n[2], t3[e + 3] = n[3], t3[e + 4] = n[4], t3[e + 5] = n[5], t3[e + 6] = n[6], t3[e + 7] = n[7], t3[e + 8] = n[8], t3;
  }
  clone() {
    return new this.constructor().fromArray(this.elements);
  }
};
var Jr = new Lt();
function Ga(i14) {
  for (let t3 = i14.length - 1; t3 >= 0; --t3) if (i14[t3] >= 65535) return true;
  return false;
}
function Di(i14) {
  return document.createElementNS("http://www.w3.org/1999/xhtml", i14);
}
function bl() {
  let i14 = Di("canvas");
  return i14.style.display = "block", i14;
}
var xo = {};
function hi(i14) {
  i14 in xo || (xo[i14] = true, console.warn(i14));
}
function El(i14, t3, e) {
  return new Promise(function(n, s) {
    function r() {
      switch (i14.clientWaitSync(t3, i14.SYNC_FLUSH_COMMANDS_BIT, 0)) {
        case i14.WAIT_FAILED:
          s();
          break;
        case i14.TIMEOUT_EXPIRED:
          setTimeout(r, e);
          break;
        default:
          n();
      }
    }
    setTimeout(r, e);
  });
}
var vo = new Lt().set(0.4123908, 0.3575843, 0.1804808, 0.212639, 0.7151687, 0.0721923, 0.0193308, 0.1191948, 0.9505322);
var yo = new Lt().set(3.2409699, -1.5373832, -0.4986108, -0.9692436, 1.8759675, 0.0415551, 0.0556301, -0.203977, 1.0569715);
function cc() {
  let i14 = { enabled: true, workingColorSpace: zn, spaces: {}, convert: function(s, r, a) {
    return this.enabled === false || r === a || !r || !a || (this.spaces[r].transfer === qt && (s.r = an(s.r), s.g = an(s.g), s.b = an(s.b)), this.spaces[r].primaries !== this.spaces[a].primaries && (s.applyMatrix3(this.spaces[r].toXYZ), s.applyMatrix3(this.spaces[a].fromXYZ)), this.spaces[a].transfer === qt && (s.r = li(s.r), s.g = li(s.g), s.b = li(s.b))), s;
  }, workingToColorSpace: function(s, r) {
    return this.convert(s, this.workingColorSpace, r);
  }, colorSpaceToWorking: function(s, r) {
    return this.convert(s, r, this.workingColorSpace);
  }, getPrimaries: function(s) {
    return this.spaces[s].primaries;
  }, getTransfer: function(s) {
    return s === dn ? Pi : this.spaces[s].transfer;
  }, getToneMappingMode: function(s) {
    return this.spaces[s].outputColorSpaceConfig.toneMappingMode || "standard";
  }, getLuminanceCoefficients: function(s, r = this.workingColorSpace) {
    return s.fromArray(this.spaces[r].luminanceCoefficients);
  }, define: function(s) {
    Object.assign(this.spaces, s);
  }, _getMatrix: function(s, r, a) {
    return s.copy(this.spaces[r].toXYZ).multiply(this.spaces[a].fromXYZ);
  }, _getDrawingBufferColorSpace: function(s) {
    return this.spaces[s].outputColorSpaceConfig.drawingBufferColorSpace;
  }, _getUnpackColorSpace: function(s = this.workingColorSpace) {
    return this.spaces[s].workingColorSpaceConfig.unpackColorSpace;
  }, fromWorkingColorSpace: function(s, r) {
    return hi("THREE.ColorManagement: .fromWorkingColorSpace() has been renamed to .workingToColorSpace()."), i14.workingToColorSpace(s, r);
  }, toWorkingColorSpace: function(s, r) {
    return hi("THREE.ColorManagement: .toWorkingColorSpace() has been renamed to .colorSpaceToWorking()."), i14.colorSpaceToWorking(s, r);
  } }, t3 = [0.64, 0.33, 0.3, 0.6, 0.15, 0.06], e = [0.2126, 0.7152, 0.0722], n = [0.3127, 0.329];
  return i14.define({ [zn]: { primaries: t3, whitePoint: n, transfer: Pi, toXYZ: vo, fromXYZ: yo, luminanceCoefficients: e, workingColorSpaceConfig: { unpackColorSpace: we }, outputColorSpaceConfig: { drawingBufferColorSpace: we } }, [we]: { primaries: t3, whitePoint: n, transfer: qt, toXYZ: vo, fromXYZ: yo, luminanceCoefficients: e, outputColorSpaceConfig: { drawingBufferColorSpace: we } } }), i14;
}
var kt = cc();
function an(i14) {
  return i14 < 0.04045 ? i14 * 0.0773993808 : Math.pow(i14 * 0.9478672986 + 0.0521327014, 2.4);
}
function li(i14) {
  return i14 < 31308e-7 ? i14 * 12.92 : 1.055 * Math.pow(i14, 0.41666) - 0.055;
}
var $n;
var ws = class {
  static getDataURL(t3, e = "image/png") {
    if (/^data:/i.test(t3.src) || typeof HTMLCanvasElement > "u") return t3.src;
    let n;
    if (t3 instanceof HTMLCanvasElement) n = t3;
    else {
      $n === void 0 && ($n = Di("canvas")), $n.width = t3.width, $n.height = t3.height;
      let s = $n.getContext("2d");
      t3 instanceof ImageData ? s.putImageData(t3, 0, 0) : s.drawImage(t3, 0, 0, t3.width, t3.height), n = $n;
    }
    return n.toDataURL(e);
  }
  static sRGBToLinear(t3) {
    if (typeof HTMLImageElement < "u" && t3 instanceof HTMLImageElement || typeof HTMLCanvasElement < "u" && t3 instanceof HTMLCanvasElement || typeof ImageBitmap < "u" && t3 instanceof ImageBitmap) {
      let e = Di("canvas");
      e.width = t3.width, e.height = t3.height;
      let n = e.getContext("2d");
      n.drawImage(t3, 0, 0, t3.width, t3.height);
      let s = n.getImageData(0, 0, t3.width, t3.height), r = s.data;
      for (let a = 0; a < r.length; a++) r[a] = an(r[a] / 255) * 255;
      return n.putImageData(s, 0, 0), e;
    } else if (t3.data) {
      let e = t3.data.slice(0);
      for (let n = 0; n < e.length; n++) e instanceof Uint8Array || e instanceof Uint8ClampedArray ? e[n] = Math.floor(an(e[n] / 255) * 255) : e[n] = an(e[n]);
      return { data: e, width: t3.width, height: t3.height };
    } else return console.warn("THREE.ImageUtils.sRGBToLinear(): Unsupported image type. No color space conversion applied."), t3;
  }
};
var hc = 0;
var ui = class {
  constructor(t3 = null) {
    this.isSource = true, Object.defineProperty(this, "id", { value: hc++ }), this.uuid = Qi(), this.data = t3, this.dataReady = true, this.version = 0;
  }
  getSize(t3) {
    let e = this.data;
    return typeof HTMLVideoElement < "u" && e instanceof HTMLVideoElement ? t3.set(e.videoWidth, e.videoHeight, 0) : e instanceof VideoFrame ? t3.set(e.displayHeight, e.displayWidth, 0) : e !== null ? t3.set(e.width, e.height, e.depth || 0) : t3.set(0, 0, 0), t3;
  }
  set needsUpdate(t3) {
    t3 === true && this.version++;
  }
  toJSON(t3) {
    let e = t3 === void 0 || typeof t3 == "string";
    if (!e && t3.images[this.uuid] !== void 0) return t3.images[this.uuid];
    let n = { uuid: this.uuid, url: "" }, s = this.data;
    if (s !== null) {
      let r;
      if (Array.isArray(s)) {
        r = [];
        for (let a = 0, o = s.length; a < o; a++) s[a].isDataTexture ? r.push($r(s[a].image)) : r.push($r(s[a]));
      } else r = $r(s);
      n.url = r;
    }
    return e || (t3.images[this.uuid] = n), n;
  }
};
function $r(i14) {
  return typeof HTMLImageElement < "u" && i14 instanceof HTMLImageElement || typeof HTMLCanvasElement < "u" && i14 instanceof HTMLCanvasElement || typeof ImageBitmap < "u" && i14 instanceof ImageBitmap ? ws.getDataURL(i14) : i14.data ? { data: Array.from(i14.data), width: i14.width, height: i14.height, type: i14.data.constructor.name } : (console.warn("THREE.Texture: Unable to serialize Texture."), {});
}
var uc = 0;
var Kr = new F();
var Re = class i4 extends ln {
  constructor(t3 = i4.DEFAULT_IMAGE, e = i4.DEFAULT_MAPPING, n = yn, s = yn, r = ke, a = wn, o = Fe, c = We, l = i4.DEFAULT_ANISOTROPY, u = dn) {
    super(), this.isTexture = true, Object.defineProperty(this, "id", { value: uc++ }), this.uuid = Qi(), this.name = "", this.source = new ui(t3), this.mipmaps = [], this.mapping = e, this.channel = 0, this.wrapS = n, this.wrapT = s, this.magFilter = r, this.minFilter = a, this.anisotropy = l, this.format = o, this.internalFormat = null, this.type = c, this.offset = new Gt(0, 0), this.repeat = new Gt(1, 1), this.center = new Gt(0, 0), this.rotation = 0, this.matrixAutoUpdate = true, this.matrix = new Lt(), this.generateMipmaps = true, this.premultiplyAlpha = false, this.flipY = true, this.unpackAlignment = 4, this.colorSpace = u, this.userData = {}, this.updateRanges = [], this.version = 0, this.onUpdate = null, this.renderTarget = null, this.isRenderTargetTexture = false, this.isArrayTexture = !!(t3 && t3.depth && t3.depth > 1), this.pmremVersion = 0;
  }
  get width() {
    return this.source.getSize(Kr).x;
  }
  get height() {
    return this.source.getSize(Kr).y;
  }
  get depth() {
    return this.source.getSize(Kr).z;
  }
  get image() {
    return this.source.data;
  }
  set image(t3 = null) {
    this.source.data = t3;
  }
  updateMatrix() {
    this.matrix.setUvTransform(this.offset.x, this.offset.y, this.repeat.x, this.repeat.y, this.rotation, this.center.x, this.center.y);
  }
  addUpdateRange(t3, e) {
    this.updateRanges.push({ start: t3, count: e });
  }
  clearUpdateRanges() {
    this.updateRanges.length = 0;
  }
  clone() {
    return new this.constructor().copy(this);
  }
  copy(t3) {
    return this.name = t3.name, this.source = t3.source, this.mipmaps = t3.mipmaps.slice(0), this.mapping = t3.mapping, this.channel = t3.channel, this.wrapS = t3.wrapS, this.wrapT = t3.wrapT, this.magFilter = t3.magFilter, this.minFilter = t3.minFilter, this.anisotropy = t3.anisotropy, this.format = t3.format, this.internalFormat = t3.internalFormat, this.type = t3.type, this.offset.copy(t3.offset), this.repeat.copy(t3.repeat), this.center.copy(t3.center), this.rotation = t3.rotation, this.matrixAutoUpdate = t3.matrixAutoUpdate, this.matrix.copy(t3.matrix), this.generateMipmaps = t3.generateMipmaps, this.premultiplyAlpha = t3.premultiplyAlpha, this.flipY = t3.flipY, this.unpackAlignment = t3.unpackAlignment, this.colorSpace = t3.colorSpace, this.renderTarget = t3.renderTarget, this.isRenderTargetTexture = t3.isRenderTargetTexture, this.isArrayTexture = t3.isArrayTexture, this.userData = JSON.parse(JSON.stringify(t3.userData)), this.needsUpdate = true, this;
  }
  setValues(t3) {
    for (let e in t3) {
      let n = t3[e];
      if (n === void 0) {
        console.warn(`THREE.Texture.setValues(): parameter '${e}' has value of undefined.`);
        continue;
      }
      let s = this[e];
      if (s === void 0) {
        console.warn(`THREE.Texture.setValues(): property '${e}' does not exist.`);
        continue;
      }
      s && n && s.isVector2 && n.isVector2 || s && n && s.isVector3 && n.isVector3 || s && n && s.isMatrix3 && n.isMatrix3 ? s.copy(n) : this[e] = n;
    }
  }
  toJSON(t3) {
    let e = t3 === void 0 || typeof t3 == "string";
    if (!e && t3.textures[this.uuid] !== void 0) return t3.textures[this.uuid];
    let n = { metadata: { version: 4.7, type: "Texture", generator: "Texture.toJSON" }, uuid: this.uuid, name: this.name, image: this.source.toJSON(t3).uuid, mapping: this.mapping, channel: this.channel, repeat: [this.repeat.x, this.repeat.y], offset: [this.offset.x, this.offset.y], center: [this.center.x, this.center.y], rotation: this.rotation, wrap: [this.wrapS, this.wrapT], format: this.format, internalFormat: this.internalFormat, type: this.type, colorSpace: this.colorSpace, minFilter: this.minFilter, magFilter: this.magFilter, anisotropy: this.anisotropy, flipY: this.flipY, generateMipmaps: this.generateMipmaps, premultiplyAlpha: this.premultiplyAlpha, unpackAlignment: this.unpackAlignment };
    return Object.keys(this.userData).length > 0 && (n.userData = this.userData), e || (t3.textures[this.uuid] = n), n;
  }
  dispose() {
    this.dispatchEvent({ type: "dispose" });
  }
  transformUv(t3) {
    if (this.mapping !== Pa) return t3;
    if (t3.applyMatrix3(this.matrix), t3.x < 0 || t3.x > 1) switch (this.wrapS) {
      case bs:
        t3.x = t3.x - Math.floor(t3.x);
        break;
      case yn:
        t3.x = t3.x < 0 ? 0 : 1;
        break;
      case Es:
        Math.abs(Math.floor(t3.x) % 2) === 1 ? t3.x = Math.ceil(t3.x) - t3.x : t3.x = t3.x - Math.floor(t3.x);
        break;
    }
    if (t3.y < 0 || t3.y > 1) switch (this.wrapT) {
      case bs:
        t3.y = t3.y - Math.floor(t3.y);
        break;
      case yn:
        t3.y = t3.y < 0 ? 0 : 1;
        break;
      case Es:
        Math.abs(Math.floor(t3.y) % 2) === 1 ? t3.y = Math.ceil(t3.y) - t3.y : t3.y = t3.y - Math.floor(t3.y);
        break;
    }
    return this.flipY && (t3.y = 1 - t3.y), t3;
  }
  set needsUpdate(t3) {
    t3 === true && (this.version++, this.source.needsUpdate = true);
  }
  set needsPMREMUpdate(t3) {
    t3 === true && this.pmremVersion++;
  }
};
Re.DEFAULT_IMAGE = null;
Re.DEFAULT_MAPPING = Pa;
Re.DEFAULT_ANISOTROPY = 1;
var se = class i5 {
  constructor(t3 = 0, e = 0, n = 0, s = 1) {
    i5.prototype.isVector4 = true, this.x = t3, this.y = e, this.z = n, this.w = s;
  }
  get width() {
    return this.z;
  }
  set width(t3) {
    this.z = t3;
  }
  get height() {
    return this.w;
  }
  set height(t3) {
    this.w = t3;
  }
  set(t3, e, n, s) {
    return this.x = t3, this.y = e, this.z = n, this.w = s, this;
  }
  setScalar(t3) {
    return this.x = t3, this.y = t3, this.z = t3, this.w = t3, this;
  }
  setX(t3) {
    return this.x = t3, this;
  }
  setY(t3) {
    return this.y = t3, this;
  }
  setZ(t3) {
    return this.z = t3, this;
  }
  setW(t3) {
    return this.w = t3, this;
  }
  setComponent(t3, e) {
    switch (t3) {
      case 0:
        this.x = e;
        break;
      case 1:
        this.y = e;
        break;
      case 2:
        this.z = e;
        break;
      case 3:
        this.w = e;
        break;
      default:
        throw new Error("index is out of range: " + t3);
    }
    return this;
  }
  getComponent(t3) {
    switch (t3) {
      case 0:
        return this.x;
      case 1:
        return this.y;
      case 2:
        return this.z;
      case 3:
        return this.w;
      default:
        throw new Error("index is out of range: " + t3);
    }
  }
  clone() {
    return new this.constructor(this.x, this.y, this.z, this.w);
  }
  copy(t3) {
    return this.x = t3.x, this.y = t3.y, this.z = t3.z, this.w = t3.w !== void 0 ? t3.w : 1, this;
  }
  add(t3) {
    return this.x += t3.x, this.y += t3.y, this.z += t3.z, this.w += t3.w, this;
  }
  addScalar(t3) {
    return this.x += t3, this.y += t3, this.z += t3, this.w += t3, this;
  }
  addVectors(t3, e) {
    return this.x = t3.x + e.x, this.y = t3.y + e.y, this.z = t3.z + e.z, this.w = t3.w + e.w, this;
  }
  addScaledVector(t3, e) {
    return this.x += t3.x * e, this.y += t3.y * e, this.z += t3.z * e, this.w += t3.w * e, this;
  }
  sub(t3) {
    return this.x -= t3.x, this.y -= t3.y, this.z -= t3.z, this.w -= t3.w, this;
  }
  subScalar(t3) {
    return this.x -= t3, this.y -= t3, this.z -= t3, this.w -= t3, this;
  }
  subVectors(t3, e) {
    return this.x = t3.x - e.x, this.y = t3.y - e.y, this.z = t3.z - e.z, this.w = t3.w - e.w, this;
  }
  multiply(t3) {
    return this.x *= t3.x, this.y *= t3.y, this.z *= t3.z, this.w *= t3.w, this;
  }
  multiplyScalar(t3) {
    return this.x *= t3, this.y *= t3, this.z *= t3, this.w *= t3, this;
  }
  applyMatrix4(t3) {
    let e = this.x, n = this.y, s = this.z, r = this.w, a = t3.elements;
    return this.x = a[0] * e + a[4] * n + a[8] * s + a[12] * r, this.y = a[1] * e + a[5] * n + a[9] * s + a[13] * r, this.z = a[2] * e + a[6] * n + a[10] * s + a[14] * r, this.w = a[3] * e + a[7] * n + a[11] * s + a[15] * r, this;
  }
  divide(t3) {
    return this.x /= t3.x, this.y /= t3.y, this.z /= t3.z, this.w /= t3.w, this;
  }
  divideScalar(t3) {
    return this.multiplyScalar(1 / t3);
  }
  setAxisAngleFromQuaternion(t3) {
    this.w = 2 * Math.acos(t3.w);
    let e = Math.sqrt(1 - t3.w * t3.w);
    return e < 1e-4 ? (this.x = 1, this.y = 0, this.z = 0) : (this.x = t3.x / e, this.y = t3.y / e, this.z = t3.z / e), this;
  }
  setAxisAngleFromRotationMatrix(t3) {
    let e, n, s, r, c = t3.elements, l = c[0], u = c[4], d = c[8], f = c[1], m = c[5], x = c[9], v = c[2], p = c[6], h = c[10];
    if (Math.abs(u - f) < 0.01 && Math.abs(d - v) < 0.01 && Math.abs(x - p) < 0.01) {
      if (Math.abs(u + f) < 0.1 && Math.abs(d + v) < 0.1 && Math.abs(x + p) < 0.1 && Math.abs(l + m + h - 3) < 0.1) return this.set(1, 0, 0, 0), this;
      e = Math.PI;
      let T = (l + 1) / 2, b = (m + 1) / 2, R = (h + 1) / 2, w = (u + f) / 4, P = (d + v) / 4, N = (x + p) / 4;
      return T > b && T > R ? T < 0.01 ? (n = 0, s = 0.707106781, r = 0.707106781) : (n = Math.sqrt(T), s = w / n, r = P / n) : b > R ? b < 0.01 ? (n = 0.707106781, s = 0, r = 0.707106781) : (s = Math.sqrt(b), n = w / s, r = N / s) : R < 0.01 ? (n = 0.707106781, s = 0.707106781, r = 0) : (r = Math.sqrt(R), n = P / r, s = N / r), this.set(n, s, r, e), this;
    }
    let A = Math.sqrt((p - x) * (p - x) + (d - v) * (d - v) + (f - u) * (f - u));
    return Math.abs(A) < 1e-3 && (A = 1), this.x = (p - x) / A, this.y = (d - v) / A, this.z = (f - u) / A, this.w = Math.acos((l + m + h - 1) / 2), this;
  }
  setFromMatrixPosition(t3) {
    let e = t3.elements;
    return this.x = e[12], this.y = e[13], this.z = e[14], this.w = e[15], this;
  }
  min(t3) {
    return this.x = Math.min(this.x, t3.x), this.y = Math.min(this.y, t3.y), this.z = Math.min(this.z, t3.z), this.w = Math.min(this.w, t3.w), this;
  }
  max(t3) {
    return this.x = Math.max(this.x, t3.x), this.y = Math.max(this.y, t3.y), this.z = Math.max(this.z, t3.z), this.w = Math.max(this.w, t3.w), this;
  }
  clamp(t3, e) {
    return this.x = Bt(this.x, t3.x, e.x), this.y = Bt(this.y, t3.y, e.y), this.z = Bt(this.z, t3.z, e.z), this.w = Bt(this.w, t3.w, e.w), this;
  }
  clampScalar(t3, e) {
    return this.x = Bt(this.x, t3, e), this.y = Bt(this.y, t3, e), this.z = Bt(this.z, t3, e), this.w = Bt(this.w, t3, e), this;
  }
  clampLength(t3, e) {
    let n = this.length();
    return this.divideScalar(n || 1).multiplyScalar(Bt(n, t3, e));
  }
  floor() {
    return this.x = Math.floor(this.x), this.y = Math.floor(this.y), this.z = Math.floor(this.z), this.w = Math.floor(this.w), this;
  }
  ceil() {
    return this.x = Math.ceil(this.x), this.y = Math.ceil(this.y), this.z = Math.ceil(this.z), this.w = Math.ceil(this.w), this;
  }
  round() {
    return this.x = Math.round(this.x), this.y = Math.round(this.y), this.z = Math.round(this.z), this.w = Math.round(this.w), this;
  }
  roundToZero() {
    return this.x = Math.trunc(this.x), this.y = Math.trunc(this.y), this.z = Math.trunc(this.z), this.w = Math.trunc(this.w), this;
  }
  negate() {
    return this.x = -this.x, this.y = -this.y, this.z = -this.z, this.w = -this.w, this;
  }
  dot(t3) {
    return this.x * t3.x + this.y * t3.y + this.z * t3.z + this.w * t3.w;
  }
  lengthSq() {
    return this.x * this.x + this.y * this.y + this.z * this.z + this.w * this.w;
  }
  length() {
    return Math.sqrt(this.x * this.x + this.y * this.y + this.z * this.z + this.w * this.w);
  }
  manhattanLength() {
    return Math.abs(this.x) + Math.abs(this.y) + Math.abs(this.z) + Math.abs(this.w);
  }
  normalize() {
    return this.divideScalar(this.length() || 1);
  }
  setLength(t3) {
    return this.normalize().multiplyScalar(t3);
  }
  lerp(t3, e) {
    return this.x += (t3.x - this.x) * e, this.y += (t3.y - this.y) * e, this.z += (t3.z - this.z) * e, this.w += (t3.w - this.w) * e, this;
  }
  lerpVectors(t3, e, n) {
    return this.x = t3.x + (e.x - t3.x) * n, this.y = t3.y + (e.y - t3.y) * n, this.z = t3.z + (e.z - t3.z) * n, this.w = t3.w + (e.w - t3.w) * n, this;
  }
  equals(t3) {
    return t3.x === this.x && t3.y === this.y && t3.z === this.z && t3.w === this.w;
  }
  fromArray(t3, e = 0) {
    return this.x = t3[e], this.y = t3[e + 1], this.z = t3[e + 2], this.w = t3[e + 3], this;
  }
  toArray(t3 = [], e = 0) {
    return t3[e] = this.x, t3[e + 1] = this.y, t3[e + 2] = this.z, t3[e + 3] = this.w, t3;
  }
  fromBufferAttribute(t3, e) {
    return this.x = t3.getX(e), this.y = t3.getY(e), this.z = t3.getZ(e), this.w = t3.getW(e), this;
  }
  random() {
    return this.x = Math.random(), this.y = Math.random(), this.z = Math.random(), this.w = Math.random(), this;
  }
  *[Symbol.iterator]() {
    yield this.x, yield this.y, yield this.z, yield this.w;
  }
};
var Cs = class extends ln {
  constructor(t3 = 1, e = 1, n = {}) {
    super(), n = Object.assign({ generateMipmaps: false, internalFormat: null, minFilter: ke, depthBuffer: true, stencilBuffer: false, resolveDepthBuffer: true, resolveStencilBuffer: true, depthTexture: null, samples: 0, count: 1, depth: 1, multiview: false }, n), this.isRenderTarget = true, this.width = t3, this.height = e, this.depth = n.depth, this.scissor = new se(0, 0, t3, e), this.scissorTest = false, this.viewport = new se(0, 0, t3, e);
    let s = { width: t3, height: e, depth: n.depth }, r = new Re(s);
    this.textures = [];
    let a = n.count;
    for (let o = 0; o < a; o++) this.textures[o] = r.clone(), this.textures[o].isRenderTargetTexture = true, this.textures[o].renderTarget = this;
    this._setTextureOptions(n), this.depthBuffer = n.depthBuffer, this.stencilBuffer = n.stencilBuffer, this.resolveDepthBuffer = n.resolveDepthBuffer, this.resolveStencilBuffer = n.resolveStencilBuffer, this._depthTexture = null, this.depthTexture = n.depthTexture, this.samples = n.samples, this.multiview = n.multiview;
  }
  _setTextureOptions(t3 = {}) {
    let e = { minFilter: ke, generateMipmaps: false, flipY: false, internalFormat: null };
    t3.mapping !== void 0 && (e.mapping = t3.mapping), t3.wrapS !== void 0 && (e.wrapS = t3.wrapS), t3.wrapT !== void 0 && (e.wrapT = t3.wrapT), t3.wrapR !== void 0 && (e.wrapR = t3.wrapR), t3.magFilter !== void 0 && (e.magFilter = t3.magFilter), t3.minFilter !== void 0 && (e.minFilter = t3.minFilter), t3.format !== void 0 && (e.format = t3.format), t3.type !== void 0 && (e.type = t3.type), t3.anisotropy !== void 0 && (e.anisotropy = t3.anisotropy), t3.colorSpace !== void 0 && (e.colorSpace = t3.colorSpace), t3.flipY !== void 0 && (e.flipY = t3.flipY), t3.generateMipmaps !== void 0 && (e.generateMipmaps = t3.generateMipmaps), t3.internalFormat !== void 0 && (e.internalFormat = t3.internalFormat);
    for (let n = 0; n < this.textures.length; n++) this.textures[n].setValues(e);
  }
  get texture() {
    return this.textures[0];
  }
  set texture(t3) {
    this.textures[0] = t3;
  }
  set depthTexture(t3) {
    this._depthTexture !== null && (this._depthTexture.renderTarget = null), t3 !== null && (t3.renderTarget = this), this._depthTexture = t3;
  }
  get depthTexture() {
    return this._depthTexture;
  }
  setSize(t3, e, n = 1) {
    if (this.width !== t3 || this.height !== e || this.depth !== n) {
      this.width = t3, this.height = e, this.depth = n;
      for (let s = 0, r = this.textures.length; s < r; s++) this.textures[s].image.width = t3, this.textures[s].image.height = e, this.textures[s].image.depth = n, this.textures[s].isArrayTexture = this.textures[s].image.depth > 1;
      this.dispose();
    }
    this.viewport.set(0, 0, t3, e), this.scissor.set(0, 0, t3, e);
  }
  clone() {
    return new this.constructor().copy(this);
  }
  copy(t3) {
    this.width = t3.width, this.height = t3.height, this.depth = t3.depth, this.scissor.copy(t3.scissor), this.scissorTest = t3.scissorTest, this.viewport.copy(t3.viewport), this.textures.length = 0;
    for (let e = 0, n = t3.textures.length; e < n; e++) {
      this.textures[e] = t3.textures[e].clone(), this.textures[e].isRenderTargetTexture = true, this.textures[e].renderTarget = this;
      let s = Object.assign({}, t3.textures[e].image);
      this.textures[e].source = new ui(s);
    }
    return this.depthBuffer = t3.depthBuffer, this.stencilBuffer = t3.stencilBuffer, this.resolveDepthBuffer = t3.resolveDepthBuffer, this.resolveStencilBuffer = t3.resolveStencilBuffer, t3.depthTexture !== null && (this.depthTexture = t3.depthTexture.clone()), this.samples = t3.samples, this;
  }
  dispose() {
    this.dispatchEvent({ type: "dispose" });
  }
};
var Ze = class extends Cs {
  constructor(t3 = 1, e = 1, n = {}) {
    super(t3, e, n), this.isWebGLRenderTarget = true;
  }
};
var Ui = class extends Re {
  constructor(t3 = null, e = 1, n = 1, s = 1) {
    super(null), this.isDataArrayTexture = true, this.image = { data: t3, width: e, height: n, depth: s }, this.magFilter = Ne, this.minFilter = Ne, this.wrapR = yn, this.generateMipmaps = false, this.flipY = false, this.unpackAlignment = 1, this.layerUpdates = /* @__PURE__ */ new Set();
  }
  addLayerUpdate(t3) {
    this.layerUpdates.add(t3);
  }
  clearLayerUpdates() {
    this.layerUpdates.clear();
  }
};
var Rs = class extends Re {
  constructor(t3 = null, e = 1, n = 1, s = 1) {
    super(null), this.isData3DTexture = true, this.image = { data: t3, width: e, height: n, depth: s }, this.magFilter = Ne, this.minFilter = Ne, this.wrapR = yn, this.generateMipmaps = false, this.flipY = false, this.unpackAlignment = 1;
  }
};
var Sn = class {
  constructor(t3 = new F(1 / 0, 1 / 0, 1 / 0), e = new F(-1 / 0, -1 / 0, -1 / 0)) {
    this.isBox3 = true, this.min = t3, this.max = e;
  }
  set(t3, e) {
    return this.min.copy(t3), this.max.copy(e), this;
  }
  setFromArray(t3) {
    this.makeEmpty();
    for (let e = 0, n = t3.length; e < n; e += 3) this.expandByPoint(Oe.fromArray(t3, e));
    return this;
  }
  setFromBufferAttribute(t3) {
    this.makeEmpty();
    for (let e = 0, n = t3.count; e < n; e++) this.expandByPoint(Oe.fromBufferAttribute(t3, e));
    return this;
  }
  setFromPoints(t3) {
    this.makeEmpty();
    for (let e = 0, n = t3.length; e < n; e++) this.expandByPoint(t3[e]);
    return this;
  }
  setFromCenterAndSize(t3, e) {
    let n = Oe.copy(e).multiplyScalar(0.5);
    return this.min.copy(t3).sub(n), this.max.copy(t3).add(n), this;
  }
  setFromObject(t3, e = false) {
    return this.makeEmpty(), this.expandByObject(t3, e);
  }
  clone() {
    return new this.constructor().copy(this);
  }
  copy(t3) {
    return this.min.copy(t3.min), this.max.copy(t3.max), this;
  }
  makeEmpty() {
    return this.min.x = this.min.y = this.min.z = 1 / 0, this.max.x = this.max.y = this.max.z = -1 / 0, this;
  }
  isEmpty() {
    return this.max.x < this.min.x || this.max.y < this.min.y || this.max.z < this.min.z;
  }
  getCenter(t3) {
    return this.isEmpty() ? t3.set(0, 0, 0) : t3.addVectors(this.min, this.max).multiplyScalar(0.5);
  }
  getSize(t3) {
    return this.isEmpty() ? t3.set(0, 0, 0) : t3.subVectors(this.max, this.min);
  }
  expandByPoint(t3) {
    return this.min.min(t3), this.max.max(t3), this;
  }
  expandByVector(t3) {
    return this.min.sub(t3), this.max.add(t3), this;
  }
  expandByScalar(t3) {
    return this.min.addScalar(-t3), this.max.addScalar(t3), this;
  }
  expandByObject(t3, e = false) {
    t3.updateWorldMatrix(false, false);
    let n = t3.geometry;
    if (n !== void 0) {
      let r = n.getAttribute("position");
      if (e === true && r !== void 0 && t3.isInstancedMesh !== true) for (let a = 0, o = r.count; a < o; a++) t3.isMesh === true ? t3.getVertexPosition(a, Oe) : Oe.fromBufferAttribute(r, a), Oe.applyMatrix4(t3.matrixWorld), this.expandByPoint(Oe);
      else t3.boundingBox !== void 0 ? (t3.boundingBox === null && t3.computeBoundingBox(), ns.copy(t3.boundingBox)) : (n.boundingBox === null && n.computeBoundingBox(), ns.copy(n.boundingBox)), ns.applyMatrix4(t3.matrixWorld), this.union(ns);
    }
    let s = t3.children;
    for (let r = 0, a = s.length; r < a; r++) this.expandByObject(s[r], e);
    return this;
  }
  containsPoint(t3) {
    return t3.x >= this.min.x && t3.x <= this.max.x && t3.y >= this.min.y && t3.y <= this.max.y && t3.z >= this.min.z && t3.z <= this.max.z;
  }
  containsBox(t3) {
    return this.min.x <= t3.min.x && t3.max.x <= this.max.x && this.min.y <= t3.min.y && t3.max.y <= this.max.y && this.min.z <= t3.min.z && t3.max.z <= this.max.z;
  }
  getParameter(t3, e) {
    return e.set((t3.x - this.min.x) / (this.max.x - this.min.x), (t3.y - this.min.y) / (this.max.y - this.min.y), (t3.z - this.min.z) / (this.max.z - this.min.z));
  }
  intersectsBox(t3) {
    return t3.max.x >= this.min.x && t3.min.x <= this.max.x && t3.max.y >= this.min.y && t3.min.y <= this.max.y && t3.max.z >= this.min.z && t3.min.z <= this.max.z;
  }
  intersectsSphere(t3) {
    return this.clampPoint(t3.center, Oe), Oe.distanceToSquared(t3.center) <= t3.radius * t3.radius;
  }
  intersectsPlane(t3) {
    let e, n;
    return t3.normal.x > 0 ? (e = t3.normal.x * this.min.x, n = t3.normal.x * this.max.x) : (e = t3.normal.x * this.max.x, n = t3.normal.x * this.min.x), t3.normal.y > 0 ? (e += t3.normal.y * this.min.y, n += t3.normal.y * this.max.y) : (e += t3.normal.y * this.max.y, n += t3.normal.y * this.min.y), t3.normal.z > 0 ? (e += t3.normal.z * this.min.z, n += t3.normal.z * this.max.z) : (e += t3.normal.z * this.max.z, n += t3.normal.z * this.min.z), e <= -t3.constant && n >= -t3.constant;
  }
  intersectsTriangle(t3) {
    if (this.isEmpty()) return false;
    this.getCenter(Ai), is.subVectors(this.max, Ai), Kn.subVectors(t3.a, Ai), Qn.subVectors(t3.b, Ai), jn.subVectors(t3.c, Ai), fn.subVectors(Qn, Kn), pn.subVectors(jn, Qn), Pn.subVectors(Kn, jn);
    let e = [0, -fn.z, fn.y, 0, -pn.z, pn.y, 0, -Pn.z, Pn.y, fn.z, 0, -fn.x, pn.z, 0, -pn.x, Pn.z, 0, -Pn.x, -fn.y, fn.x, 0, -pn.y, pn.x, 0, -Pn.y, Pn.x, 0];
    return !Qr(e, Kn, Qn, jn, is) || (e = [1, 0, 0, 0, 1, 0, 0, 0, 1], !Qr(e, Kn, Qn, jn, is)) ? false : (ss.crossVectors(fn, pn), e = [ss.x, ss.y, ss.z], Qr(e, Kn, Qn, jn, is));
  }
  clampPoint(t3, e) {
    return e.copy(t3).clamp(this.min, this.max);
  }
  distanceToPoint(t3) {
    return this.clampPoint(t3, Oe).distanceTo(t3);
  }
  getBoundingSphere(t3) {
    return this.isEmpty() ? t3.makeEmpty() : (this.getCenter(t3.center), t3.radius = this.getSize(Oe).length() * 0.5), t3;
  }
  intersect(t3) {
    return this.min.max(t3.min), this.max.min(t3.max), this.isEmpty() && this.makeEmpty(), this;
  }
  union(t3) {
    return this.min.min(t3.min), this.max.max(t3.max), this;
  }
  applyMatrix4(t3) {
    return this.isEmpty() ? this : (tn[0].set(this.min.x, this.min.y, this.min.z).applyMatrix4(t3), tn[1].set(this.min.x, this.min.y, this.max.z).applyMatrix4(t3), tn[2].set(this.min.x, this.max.y, this.min.z).applyMatrix4(t3), tn[3].set(this.min.x, this.max.y, this.max.z).applyMatrix4(t3), tn[4].set(this.max.x, this.min.y, this.min.z).applyMatrix4(t3), tn[5].set(this.max.x, this.min.y, this.max.z).applyMatrix4(t3), tn[6].set(this.max.x, this.max.y, this.min.z).applyMatrix4(t3), tn[7].set(this.max.x, this.max.y, this.max.z).applyMatrix4(t3), this.setFromPoints(tn), this);
  }
  translate(t3) {
    return this.min.add(t3), this.max.add(t3), this;
  }
  equals(t3) {
    return t3.min.equals(this.min) && t3.max.equals(this.max);
  }
  toJSON() {
    return { min: this.min.toArray(), max: this.max.toArray() };
  }
  fromJSON(t3) {
    return this.min.fromArray(t3.min), this.max.fromArray(t3.max), this;
  }
};
var tn = [new F(), new F(), new F(), new F(), new F(), new F(), new F(), new F()];
var Oe = new F();
var ns = new Sn();
var Kn = new F();
var Qn = new F();
var jn = new F();
var fn = new F();
var pn = new F();
var Pn = new F();
var Ai = new F();
var is = new F();
var ss = new F();
var Ln = new F();
function Qr(i14, t3, e, n, s) {
  for (let r = 0, a = i14.length - 3; r <= a; r += 3) {
    Ln.fromArray(i14, r);
    let o = s.x * Math.abs(Ln.x) + s.y * Math.abs(Ln.y) + s.z * Math.abs(Ln.z), c = t3.dot(Ln), l = e.dot(Ln), u = n.dot(Ln);
    if (Math.max(-Math.max(c, l, u), Math.min(c, l, u)) > o) return false;
  }
  return true;
}
var dc = new Sn();
var wi = new F();
var jr = new F();
var di = class {
  constructor(t3 = new F(), e = -1) {
    this.isSphere = true, this.center = t3, this.radius = e;
  }
  set(t3, e) {
    return this.center.copy(t3), this.radius = e, this;
  }
  setFromPoints(t3, e) {
    let n = this.center;
    e !== void 0 ? n.copy(e) : dc.setFromPoints(t3).getCenter(n);
    let s = 0;
    for (let r = 0, a = t3.length; r < a; r++) s = Math.max(s, n.distanceToSquared(t3[r]));
    return this.radius = Math.sqrt(s), this;
  }
  copy(t3) {
    return this.center.copy(t3.center), this.radius = t3.radius, this;
  }
  isEmpty() {
    return this.radius < 0;
  }
  makeEmpty() {
    return this.center.set(0, 0, 0), this.radius = -1, this;
  }
  containsPoint(t3) {
    return t3.distanceToSquared(this.center) <= this.radius * this.radius;
  }
  distanceToPoint(t3) {
    return t3.distanceTo(this.center) - this.radius;
  }
  intersectsSphere(t3) {
    let e = this.radius + t3.radius;
    return t3.center.distanceToSquared(this.center) <= e * e;
  }
  intersectsBox(t3) {
    return t3.intersectsSphere(this);
  }
  intersectsPlane(t3) {
    return Math.abs(t3.distanceToPoint(this.center)) <= this.radius;
  }
  clampPoint(t3, e) {
    let n = this.center.distanceToSquared(t3);
    return e.copy(t3), n > this.radius * this.radius && (e.sub(this.center).normalize(), e.multiplyScalar(this.radius).add(this.center)), e;
  }
  getBoundingBox(t3) {
    return this.isEmpty() ? (t3.makeEmpty(), t3) : (t3.set(this.center, this.center), t3.expandByScalar(this.radius), t3);
  }
  applyMatrix4(t3) {
    return this.center.applyMatrix4(t3), this.radius = this.radius * t3.getMaxScaleOnAxis(), this;
  }
  translate(t3) {
    return this.center.add(t3), this;
  }
  expandByPoint(t3) {
    if (this.isEmpty()) return this.center.copy(t3), this.radius = 0, this;
    wi.subVectors(t3, this.center);
    let e = wi.lengthSq();
    if (e > this.radius * this.radius) {
      let n = Math.sqrt(e), s = (n - this.radius) * 0.5;
      this.center.addScaledVector(wi, s / n), this.radius += s;
    }
    return this;
  }
  union(t3) {
    return t3.isEmpty() ? this : this.isEmpty() ? (this.copy(t3), this) : (this.center.equals(t3.center) === true ? this.radius = Math.max(this.radius, t3.radius) : (jr.subVectors(t3.center, this.center).setLength(t3.radius), this.expandByPoint(wi.copy(t3.center).add(jr)), this.expandByPoint(wi.copy(t3.center).sub(jr))), this);
  }
  equals(t3) {
    return t3.center.equals(this.center) && t3.radius === this.radius;
  }
  clone() {
    return new this.constructor().copy(this);
  }
  toJSON() {
    return { radius: this.radius, center: this.center.toArray() };
  }
  fromJSON(t3) {
    return this.radius = t3.radius, this.center.fromArray(t3.center), this;
  }
};
var en = new F();
var ta = new F();
var rs = new F();
var mn = new F();
var ea = new F();
var as = new F();
var na = new F();
var Is = class {
  constructor(t3 = new F(), e = new F(0, 0, -1)) {
    this.origin = t3, this.direction = e;
  }
  set(t3, e) {
    return this.origin.copy(t3), this.direction.copy(e), this;
  }
  copy(t3) {
    return this.origin.copy(t3.origin), this.direction.copy(t3.direction), this;
  }
  at(t3, e) {
    return e.copy(this.origin).addScaledVector(this.direction, t3);
  }
  lookAt(t3) {
    return this.direction.copy(t3).sub(this.origin).normalize(), this;
  }
  recast(t3) {
    return this.origin.copy(this.at(t3, en)), this;
  }
  closestPointToPoint(t3, e) {
    e.subVectors(t3, this.origin);
    let n = e.dot(this.direction);
    return n < 0 ? e.copy(this.origin) : e.copy(this.origin).addScaledVector(this.direction, n);
  }
  distanceToPoint(t3) {
    return Math.sqrt(this.distanceSqToPoint(t3));
  }
  distanceSqToPoint(t3) {
    let e = en.subVectors(t3, this.origin).dot(this.direction);
    return e < 0 ? this.origin.distanceToSquared(t3) : (en.copy(this.origin).addScaledVector(this.direction, e), en.distanceToSquared(t3));
  }
  distanceSqToSegment(t3, e, n, s) {
    ta.copy(t3).add(e).multiplyScalar(0.5), rs.copy(e).sub(t3).normalize(), mn.copy(this.origin).sub(ta);
    let r = t3.distanceTo(e) * 0.5, a = -this.direction.dot(rs), o = mn.dot(this.direction), c = -mn.dot(rs), l = mn.lengthSq(), u = Math.abs(1 - a * a), d, f, m, x;
    if (u > 0) if (d = a * c - o, f = a * o - c, x = r * u, d >= 0) if (f >= -x) if (f <= x) {
      let v = 1 / u;
      d *= v, f *= v, m = d * (d + a * f + 2 * o) + f * (a * d + f + 2 * c) + l;
    } else f = r, d = Math.max(0, -(a * f + o)), m = -d * d + f * (f + 2 * c) + l;
    else f = -r, d = Math.max(0, -(a * f + o)), m = -d * d + f * (f + 2 * c) + l;
    else f <= -x ? (d = Math.max(0, -(-a * r + o)), f = d > 0 ? -r : Math.min(Math.max(-r, -c), r), m = -d * d + f * (f + 2 * c) + l) : f <= x ? (d = 0, f = Math.min(Math.max(-r, -c), r), m = f * (f + 2 * c) + l) : (d = Math.max(0, -(a * r + o)), f = d > 0 ? r : Math.min(Math.max(-r, -c), r), m = -d * d + f * (f + 2 * c) + l);
    else f = a > 0 ? -r : r, d = Math.max(0, -(a * f + o)), m = -d * d + f * (f + 2 * c) + l;
    return n && n.copy(this.origin).addScaledVector(this.direction, d), s && s.copy(ta).addScaledVector(rs, f), m;
  }
  intersectSphere(t3, e) {
    en.subVectors(t3.center, this.origin);
    let n = en.dot(this.direction), s = en.dot(en) - n * n, r = t3.radius * t3.radius;
    if (s > r) return null;
    let a = Math.sqrt(r - s), o = n - a, c = n + a;
    return c < 0 ? null : o < 0 ? this.at(c, e) : this.at(o, e);
  }
  intersectsSphere(t3) {
    return t3.radius < 0 ? false : this.distanceSqToPoint(t3.center) <= t3.radius * t3.radius;
  }
  distanceToPlane(t3) {
    let e = t3.normal.dot(this.direction);
    if (e === 0) return t3.distanceToPoint(this.origin) === 0 ? 0 : null;
    let n = -(this.origin.dot(t3.normal) + t3.constant) / e;
    return n >= 0 ? n : null;
  }
  intersectPlane(t3, e) {
    let n = this.distanceToPlane(t3);
    return n === null ? null : this.at(n, e);
  }
  intersectsPlane(t3) {
    let e = t3.distanceToPoint(this.origin);
    return e === 0 || t3.normal.dot(this.direction) * e < 0;
  }
  intersectBox(t3, e) {
    let n, s, r, a, o, c, l = 1 / this.direction.x, u = 1 / this.direction.y, d = 1 / this.direction.z, f = this.origin;
    return l >= 0 ? (n = (t3.min.x - f.x) * l, s = (t3.max.x - f.x) * l) : (n = (t3.max.x - f.x) * l, s = (t3.min.x - f.x) * l), u >= 0 ? (r = (t3.min.y - f.y) * u, a = (t3.max.y - f.y) * u) : (r = (t3.max.y - f.y) * u, a = (t3.min.y - f.y) * u), n > a || r > s || ((r > n || isNaN(n)) && (n = r), (a < s || isNaN(s)) && (s = a), d >= 0 ? (o = (t3.min.z - f.z) * d, c = (t3.max.z - f.z) * d) : (o = (t3.max.z - f.z) * d, c = (t3.min.z - f.z) * d), n > c || o > s) || ((o > n || n !== n) && (n = o), (c < s || s !== s) && (s = c), s < 0) ? null : this.at(n >= 0 ? n : s, e);
  }
  intersectsBox(t3) {
    return this.intersectBox(t3, en) !== null;
  }
  intersectTriangle(t3, e, n, s, r) {
    ea.subVectors(e, t3), as.subVectors(n, t3), na.crossVectors(ea, as);
    let a = this.direction.dot(na), o;
    if (a > 0) {
      if (s) return null;
      o = 1;
    } else if (a < 0) o = -1, a = -a;
    else return null;
    mn.subVectors(this.origin, t3);
    let c = o * this.direction.dot(as.crossVectors(mn, as));
    if (c < 0) return null;
    let l = o * this.direction.dot(ea.cross(mn));
    if (l < 0 || c + l > a) return null;
    let u = -o * mn.dot(na);
    return u < 0 ? null : this.at(u / a, r);
  }
  applyMatrix4(t3) {
    return this.origin.applyMatrix4(t3), this.direction.transformDirection(t3), this;
  }
  equals(t3) {
    return t3.origin.equals(this.origin) && t3.direction.equals(this.direction);
  }
  clone() {
    return new this.constructor().copy(this);
  }
};
var oe = class i6 {
  constructor(t3, e, n, s, r, a, o, c, l, u, d, f, m, x, v, p) {
    i6.prototype.isMatrix4 = true, this.elements = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1], t3 !== void 0 && this.set(t3, e, n, s, r, a, o, c, l, u, d, f, m, x, v, p);
  }
  set(t3, e, n, s, r, a, o, c, l, u, d, f, m, x, v, p) {
    let h = this.elements;
    return h[0] = t3, h[4] = e, h[8] = n, h[12] = s, h[1] = r, h[5] = a, h[9] = o, h[13] = c, h[2] = l, h[6] = u, h[10] = d, h[14] = f, h[3] = m, h[7] = x, h[11] = v, h[15] = p, this;
  }
  identity() {
    return this.set(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1), this;
  }
  clone() {
    return new i6().fromArray(this.elements);
  }
  copy(t3) {
    let e = this.elements, n = t3.elements;
    return e[0] = n[0], e[1] = n[1], e[2] = n[2], e[3] = n[3], e[4] = n[4], e[5] = n[5], e[6] = n[6], e[7] = n[7], e[8] = n[8], e[9] = n[9], e[10] = n[10], e[11] = n[11], e[12] = n[12], e[13] = n[13], e[14] = n[14], e[15] = n[15], this;
  }
  copyPosition(t3) {
    let e = this.elements, n = t3.elements;
    return e[12] = n[12], e[13] = n[13], e[14] = n[14], this;
  }
  setFromMatrix3(t3) {
    let e = t3.elements;
    return this.set(e[0], e[3], e[6], 0, e[1], e[4], e[7], 0, e[2], e[5], e[8], 0, 0, 0, 0, 1), this;
  }
  extractBasis(t3, e, n) {
    return t3.setFromMatrixColumn(this, 0), e.setFromMatrixColumn(this, 1), n.setFromMatrixColumn(this, 2), this;
  }
  makeBasis(t3, e, n) {
    return this.set(t3.x, e.x, n.x, 0, t3.y, e.y, n.y, 0, t3.z, e.z, n.z, 0, 0, 0, 0, 1), this;
  }
  extractRotation(t3) {
    let e = this.elements, n = t3.elements, s = 1 / ti.setFromMatrixColumn(t3, 0).length(), r = 1 / ti.setFromMatrixColumn(t3, 1).length(), a = 1 / ti.setFromMatrixColumn(t3, 2).length();
    return e[0] = n[0] * s, e[1] = n[1] * s, e[2] = n[2] * s, e[3] = 0, e[4] = n[4] * r, e[5] = n[5] * r, e[6] = n[6] * r, e[7] = 0, e[8] = n[8] * a, e[9] = n[9] * a, e[10] = n[10] * a, e[11] = 0, e[12] = 0, e[13] = 0, e[14] = 0, e[15] = 1, this;
  }
  makeRotationFromEuler(t3) {
    let e = this.elements, n = t3.x, s = t3.y, r = t3.z, a = Math.cos(n), o = Math.sin(n), c = Math.cos(s), l = Math.sin(s), u = Math.cos(r), d = Math.sin(r);
    if (t3.order === "XYZ") {
      let f = a * u, m = a * d, x = o * u, v = o * d;
      e[0] = c * u, e[4] = -c * d, e[8] = l, e[1] = m + x * l, e[5] = f - v * l, e[9] = -o * c, e[2] = v - f * l, e[6] = x + m * l, e[10] = a * c;
    } else if (t3.order === "YXZ") {
      let f = c * u, m = c * d, x = l * u, v = l * d;
      e[0] = f + v * o, e[4] = x * o - m, e[8] = a * l, e[1] = a * d, e[5] = a * u, e[9] = -o, e[2] = m * o - x, e[6] = v + f * o, e[10] = a * c;
    } else if (t3.order === "ZXY") {
      let f = c * u, m = c * d, x = l * u, v = l * d;
      e[0] = f - v * o, e[4] = -a * d, e[8] = x + m * o, e[1] = m + x * o, e[5] = a * u, e[9] = v - f * o, e[2] = -a * l, e[6] = o, e[10] = a * c;
    } else if (t3.order === "ZYX") {
      let f = a * u, m = a * d, x = o * u, v = o * d;
      e[0] = c * u, e[4] = x * l - m, e[8] = f * l + v, e[1] = c * d, e[5] = v * l + f, e[9] = m * l - x, e[2] = -l, e[6] = o * c, e[10] = a * c;
    } else if (t3.order === "YZX") {
      let f = a * c, m = a * l, x = o * c, v = o * l;
      e[0] = c * u, e[4] = v - f * d, e[8] = x * d + m, e[1] = d, e[5] = a * u, e[9] = -o * u, e[2] = -l * u, e[6] = m * d + x, e[10] = f - v * d;
    } else if (t3.order === "XZY") {
      let f = a * c, m = a * l, x = o * c, v = o * l;
      e[0] = c * u, e[4] = -d, e[8] = l * u, e[1] = f * d + v, e[5] = a * u, e[9] = m * d - x, e[2] = x * d - m, e[6] = o * u, e[10] = v * d + f;
    }
    return e[3] = 0, e[7] = 0, e[11] = 0, e[12] = 0, e[13] = 0, e[14] = 0, e[15] = 1, this;
  }
  makeRotationFromQuaternion(t3) {
    return this.compose(fc, t3, pc);
  }
  lookAt(t3, e, n) {
    let s = this.elements;
    return Te.subVectors(t3, e), Te.lengthSq() === 0 && (Te.z = 1), Te.normalize(), gn.crossVectors(n, Te), gn.lengthSq() === 0 && (Math.abs(n.z) === 1 ? Te.x += 1e-4 : Te.z += 1e-4, Te.normalize(), gn.crossVectors(n, Te)), gn.normalize(), os.crossVectors(Te, gn), s[0] = gn.x, s[4] = os.x, s[8] = Te.x, s[1] = gn.y, s[5] = os.y, s[9] = Te.y, s[2] = gn.z, s[6] = os.z, s[10] = Te.z, this;
  }
  multiply(t3) {
    return this.multiplyMatrices(this, t3);
  }
  premultiply(t3) {
    return this.multiplyMatrices(t3, this);
  }
  multiplyMatrices(t3, e) {
    let n = t3.elements, s = e.elements, r = this.elements, a = n[0], o = n[4], c = n[8], l = n[12], u = n[1], d = n[5], f = n[9], m = n[13], x = n[2], v = n[6], p = n[10], h = n[14], A = n[3], T = n[7], b = n[11], R = n[15], w = s[0], P = s[4], N = s[8], M = s[12], y = s[1], I = s[5], z = s[9], H = s[13], X = s[2], Z = s[6], W = s[10], et = s[14], V = s[3], rt = s[7], ct = s[11], St = s[15];
    return r[0] = a * w + o * y + c * X + l * V, r[4] = a * P + o * I + c * Z + l * rt, r[8] = a * N + o * z + c * W + l * ct, r[12] = a * M + o * H + c * et + l * St, r[1] = u * w + d * y + f * X + m * V, r[5] = u * P + d * I + f * Z + m * rt, r[9] = u * N + d * z + f * W + m * ct, r[13] = u * M + d * H + f * et + m * St, r[2] = x * w + v * y + p * X + h * V, r[6] = x * P + v * I + p * Z + h * rt, r[10] = x * N + v * z + p * W + h * ct, r[14] = x * M + v * H + p * et + h * St, r[3] = A * w + T * y + b * X + R * V, r[7] = A * P + T * I + b * Z + R * rt, r[11] = A * N + T * z + b * W + R * ct, r[15] = A * M + T * H + b * et + R * St, this;
  }
  multiplyScalar(t3) {
    let e = this.elements;
    return e[0] *= t3, e[4] *= t3, e[8] *= t3, e[12] *= t3, e[1] *= t3, e[5] *= t3, e[9] *= t3, e[13] *= t3, e[2] *= t3, e[6] *= t3, e[10] *= t3, e[14] *= t3, e[3] *= t3, e[7] *= t3, e[11] *= t3, e[15] *= t3, this;
  }
  determinant() {
    let t3 = this.elements, e = t3[0], n = t3[4], s = t3[8], r = t3[12], a = t3[1], o = t3[5], c = t3[9], l = t3[13], u = t3[2], d = t3[6], f = t3[10], m = t3[14], x = t3[3], v = t3[7], p = t3[11], h = t3[15];
    return x * (+r * c * d - s * l * d - r * o * f + n * l * f + s * o * m - n * c * m) + v * (+e * c * m - e * l * f + r * a * f - s * a * m + s * l * u - r * c * u) + p * (+e * l * d - e * o * m - r * a * d + n * a * m + r * o * u - n * l * u) + h * (-s * o * u - e * c * d + e * o * f + s * a * d - n * a * f + n * c * u);
  }
  transpose() {
    let t3 = this.elements, e;
    return e = t3[1], t3[1] = t3[4], t3[4] = e, e = t3[2], t3[2] = t3[8], t3[8] = e, e = t3[6], t3[6] = t3[9], t3[9] = e, e = t3[3], t3[3] = t3[12], t3[12] = e, e = t3[7], t3[7] = t3[13], t3[13] = e, e = t3[11], t3[11] = t3[14], t3[14] = e, this;
  }
  setPosition(t3, e, n) {
    let s = this.elements;
    return t3.isVector3 ? (s[12] = t3.x, s[13] = t3.y, s[14] = t3.z) : (s[12] = t3, s[13] = e, s[14] = n), this;
  }
  invert() {
    let t3 = this.elements, e = t3[0], n = t3[1], s = t3[2], r = t3[3], a = t3[4], o = t3[5], c = t3[6], l = t3[7], u = t3[8], d = t3[9], f = t3[10], m = t3[11], x = t3[12], v = t3[13], p = t3[14], h = t3[15], A = d * p * l - v * f * l + v * c * m - o * p * m - d * c * h + o * f * h, T = x * f * l - u * p * l - x * c * m + a * p * m + u * c * h - a * f * h, b = u * v * l - x * d * l + x * o * m - a * v * m - u * o * h + a * d * h, R = x * d * c - u * v * c - x * o * f + a * v * f + u * o * p - a * d * p, w = e * A + n * T + s * b + r * R;
    if (w === 0) return this.set(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);
    let P = 1 / w;
    return t3[0] = A * P, t3[1] = (v * f * r - d * p * r - v * s * m + n * p * m + d * s * h - n * f * h) * P, t3[2] = (o * p * r - v * c * r + v * s * l - n * p * l - o * s * h + n * c * h) * P, t3[3] = (d * c * r - o * f * r - d * s * l + n * f * l + o * s * m - n * c * m) * P, t3[4] = T * P, t3[5] = (u * p * r - x * f * r + x * s * m - e * p * m - u * s * h + e * f * h) * P, t3[6] = (x * c * r - a * p * r - x * s * l + e * p * l + a * s * h - e * c * h) * P, t3[7] = (a * f * r - u * c * r + u * s * l - e * f * l - a * s * m + e * c * m) * P, t3[8] = b * P, t3[9] = (x * d * r - u * v * r - x * n * m + e * v * m + u * n * h - e * d * h) * P, t3[10] = (a * v * r - x * o * r + x * n * l - e * v * l - a * n * h + e * o * h) * P, t3[11] = (u * o * r - a * d * r - u * n * l + e * d * l + a * n * m - e * o * m) * P, t3[12] = R * P, t3[13] = (u * v * s - x * d * s + x * n * f - e * v * f - u * n * p + e * d * p) * P, t3[14] = (x * o * s - a * v * s - x * n * c + e * v * c + a * n * p - e * o * p) * P, t3[15] = (a * d * s - u * o * s + u * n * c - e * d * c - a * n * f + e * o * f) * P, this;
  }
  scale(t3) {
    let e = this.elements, n = t3.x, s = t3.y, r = t3.z;
    return e[0] *= n, e[4] *= s, e[8] *= r, e[1] *= n, e[5] *= s, e[9] *= r, e[2] *= n, e[6] *= s, e[10] *= r, e[3] *= n, e[7] *= s, e[11] *= r, this;
  }
  getMaxScaleOnAxis() {
    let t3 = this.elements, e = t3[0] * t3[0] + t3[1] * t3[1] + t3[2] * t3[2], n = t3[4] * t3[4] + t3[5] * t3[5] + t3[6] * t3[6], s = t3[8] * t3[8] + t3[9] * t3[9] + t3[10] * t3[10];
    return Math.sqrt(Math.max(e, n, s));
  }
  makeTranslation(t3, e, n) {
    return t3.isVector3 ? this.set(1, 0, 0, t3.x, 0, 1, 0, t3.y, 0, 0, 1, t3.z, 0, 0, 0, 1) : this.set(1, 0, 0, t3, 0, 1, 0, e, 0, 0, 1, n, 0, 0, 0, 1), this;
  }
  makeRotationX(t3) {
    let e = Math.cos(t3), n = Math.sin(t3);
    return this.set(1, 0, 0, 0, 0, e, -n, 0, 0, n, e, 0, 0, 0, 0, 1), this;
  }
  makeRotationY(t3) {
    let e = Math.cos(t3), n = Math.sin(t3);
    return this.set(e, 0, n, 0, 0, 1, 0, 0, -n, 0, e, 0, 0, 0, 0, 1), this;
  }
  makeRotationZ(t3) {
    let e = Math.cos(t3), n = Math.sin(t3);
    return this.set(e, -n, 0, 0, n, e, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1), this;
  }
  makeRotationAxis(t3, e) {
    let n = Math.cos(e), s = Math.sin(e), r = 1 - n, a = t3.x, o = t3.y, c = t3.z, l = r * a, u = r * o;
    return this.set(l * a + n, l * o - s * c, l * c + s * o, 0, l * o + s * c, u * o + n, u * c - s * a, 0, l * c - s * o, u * c + s * a, r * c * c + n, 0, 0, 0, 0, 1), this;
  }
  makeScale(t3, e, n) {
    return this.set(t3, 0, 0, 0, 0, e, 0, 0, 0, 0, n, 0, 0, 0, 0, 1), this;
  }
  makeShear(t3, e, n, s, r, a) {
    return this.set(1, n, r, 0, t3, 1, a, 0, e, s, 1, 0, 0, 0, 0, 1), this;
  }
  compose(t3, e, n) {
    let s = this.elements, r = e._x, a = e._y, o = e._z, c = e._w, l = r + r, u = a + a, d = o + o, f = r * l, m = r * u, x = r * d, v = a * u, p = a * d, h = o * d, A = c * l, T = c * u, b = c * d, R = n.x, w = n.y, P = n.z;
    return s[0] = (1 - (v + h)) * R, s[1] = (m + b) * R, s[2] = (x - T) * R, s[3] = 0, s[4] = (m - b) * w, s[5] = (1 - (f + h)) * w, s[6] = (p + A) * w, s[7] = 0, s[8] = (x + T) * P, s[9] = (p - A) * P, s[10] = (1 - (f + v)) * P, s[11] = 0, s[12] = t3.x, s[13] = t3.y, s[14] = t3.z, s[15] = 1, this;
  }
  decompose(t3, e, n) {
    let s = this.elements, r = ti.set(s[0], s[1], s[2]).length(), a = ti.set(s[4], s[5], s[6]).length(), o = ti.set(s[8], s[9], s[10]).length();
    this.determinant() < 0 && (r = -r), t3.x = s[12], t3.y = s[13], t3.z = s[14], Be.copy(this);
    let l = 1 / r, u = 1 / a, d = 1 / o;
    return Be.elements[0] *= l, Be.elements[1] *= l, Be.elements[2] *= l, Be.elements[4] *= u, Be.elements[5] *= u, Be.elements[6] *= u, Be.elements[8] *= d, Be.elements[9] *= d, Be.elements[10] *= d, e.setFromRotationMatrix(Be), n.x = r, n.y = a, n.z = o, this;
  }
  makePerspective(t3, e, n, s, r, a, o = Ve, c = false) {
    let l = this.elements, u = 2 * r / (e - t3), d = 2 * r / (n - s), f = (e + t3) / (e - t3), m = (n + s) / (n - s), x, v;
    if (c) x = r / (a - r), v = a * r / (a - r);
    else if (o === Ve) x = -(a + r) / (a - r), v = -2 * a * r / (a - r);
    else if (o === Li) x = -a / (a - r), v = -a * r / (a - r);
    else throw new Error("THREE.Matrix4.makePerspective(): Invalid coordinate system: " + o);
    return l[0] = u, l[4] = 0, l[8] = f, l[12] = 0, l[1] = 0, l[5] = d, l[9] = m, l[13] = 0, l[2] = 0, l[6] = 0, l[10] = x, l[14] = v, l[3] = 0, l[7] = 0, l[11] = -1, l[15] = 0, this;
  }
  makeOrthographic(t3, e, n, s, r, a, o = Ve, c = false) {
    let l = this.elements, u = 2 / (e - t3), d = 2 / (n - s), f = -(e + t3) / (e - t3), m = -(n + s) / (n - s), x, v;
    if (c) x = 1 / (a - r), v = a / (a - r);
    else if (o === Ve) x = -2 / (a - r), v = -(a + r) / (a - r);
    else if (o === Li) x = -1 / (a - r), v = -r / (a - r);
    else throw new Error("THREE.Matrix4.makeOrthographic(): Invalid coordinate system: " + o);
    return l[0] = u, l[4] = 0, l[8] = 0, l[12] = f, l[1] = 0, l[5] = d, l[9] = 0, l[13] = m, l[2] = 0, l[6] = 0, l[10] = x, l[14] = v, l[3] = 0, l[7] = 0, l[11] = 0, l[15] = 1, this;
  }
  equals(t3) {
    let e = this.elements, n = t3.elements;
    for (let s = 0; s < 16; s++) if (e[s] !== n[s]) return false;
    return true;
  }
  fromArray(t3, e = 0) {
    for (let n = 0; n < 16; n++) this.elements[n] = t3[n + e];
    return this;
  }
  toArray(t3 = [], e = 0) {
    let n = this.elements;
    return t3[e] = n[0], t3[e + 1] = n[1], t3[e + 2] = n[2], t3[e + 3] = n[3], t3[e + 4] = n[4], t3[e + 5] = n[5], t3[e + 6] = n[6], t3[e + 7] = n[7], t3[e + 8] = n[8], t3[e + 9] = n[9], t3[e + 10] = n[10], t3[e + 11] = n[11], t3[e + 12] = n[12], t3[e + 13] = n[13], t3[e + 14] = n[14], t3[e + 15] = n[15], t3;
  }
};
var ti = new F();
var Be = new oe();
var fc = new F(0, 0, 0);
var pc = new F(1, 1, 1);
var gn = new F();
var os = new F();
var Te = new F();
var Mo = new oe();
var So = new cn();
var He = class i7 {
  constructor(t3 = 0, e = 0, n = 0, s = i7.DEFAULT_ORDER) {
    this.isEuler = true, this._x = t3, this._y = e, this._z = n, this._order = s;
  }
  get x() {
    return this._x;
  }
  set x(t3) {
    this._x = t3, this._onChangeCallback();
  }
  get y() {
    return this._y;
  }
  set y(t3) {
    this._y = t3, this._onChangeCallback();
  }
  get z() {
    return this._z;
  }
  set z(t3) {
    this._z = t3, this._onChangeCallback();
  }
  get order() {
    return this._order;
  }
  set order(t3) {
    this._order = t3, this._onChangeCallback();
  }
  set(t3, e, n, s = this._order) {
    return this._x = t3, this._y = e, this._z = n, this._order = s, this._onChangeCallback(), this;
  }
  clone() {
    return new this.constructor(this._x, this._y, this._z, this._order);
  }
  copy(t3) {
    return this._x = t3._x, this._y = t3._y, this._z = t3._z, this._order = t3._order, this._onChangeCallback(), this;
  }
  setFromRotationMatrix(t3, e = this._order, n = true) {
    let s = t3.elements, r = s[0], a = s[4], o = s[8], c = s[1], l = s[5], u = s[9], d = s[2], f = s[6], m = s[10];
    switch (e) {
      case "XYZ":
        this._y = Math.asin(Bt(o, -1, 1)), Math.abs(o) < 0.9999999 ? (this._x = Math.atan2(-u, m), this._z = Math.atan2(-a, r)) : (this._x = Math.atan2(f, l), this._z = 0);
        break;
      case "YXZ":
        this._x = Math.asin(-Bt(u, -1, 1)), Math.abs(u) < 0.9999999 ? (this._y = Math.atan2(o, m), this._z = Math.atan2(c, l)) : (this._y = Math.atan2(-d, r), this._z = 0);
        break;
      case "ZXY":
        this._x = Math.asin(Bt(f, -1, 1)), Math.abs(f) < 0.9999999 ? (this._y = Math.atan2(-d, m), this._z = Math.atan2(-a, l)) : (this._y = 0, this._z = Math.atan2(c, r));
        break;
      case "ZYX":
        this._y = Math.asin(-Bt(d, -1, 1)), Math.abs(d) < 0.9999999 ? (this._x = Math.atan2(f, m), this._z = Math.atan2(c, r)) : (this._x = 0, this._z = Math.atan2(-a, l));
        break;
      case "YZX":
        this._z = Math.asin(Bt(c, -1, 1)), Math.abs(c) < 0.9999999 ? (this._x = Math.atan2(-u, l), this._y = Math.atan2(-d, r)) : (this._x = 0, this._y = Math.atan2(o, m));
        break;
      case "XZY":
        this._z = Math.asin(-Bt(a, -1, 1)), Math.abs(a) < 0.9999999 ? (this._x = Math.atan2(f, l), this._y = Math.atan2(o, r)) : (this._x = Math.atan2(-u, m), this._y = 0);
        break;
      default:
        console.warn("THREE.Euler: .setFromRotationMatrix() encountered an unknown order: " + e);
    }
    return this._order = e, n === true && this._onChangeCallback(), this;
  }
  setFromQuaternion(t3, e, n) {
    return Mo.makeRotationFromQuaternion(t3), this.setFromRotationMatrix(Mo, e, n);
  }
  setFromVector3(t3, e = this._order) {
    return this.set(t3.x, t3.y, t3.z, e);
  }
  reorder(t3) {
    return So.setFromEuler(this), this.setFromQuaternion(So, t3);
  }
  equals(t3) {
    return t3._x === this._x && t3._y === this._y && t3._z === this._z && t3._order === this._order;
  }
  fromArray(t3) {
    return this._x = t3[0], this._y = t3[1], this._z = t3[2], t3[3] !== void 0 && (this._order = t3[3]), this._onChangeCallback(), this;
  }
  toArray(t3 = [], e = 0) {
    return t3[e] = this._x, t3[e + 1] = this._y, t3[e + 2] = this._z, t3[e + 3] = this._order, t3;
  }
  _onChange(t3) {
    return this._onChangeCallback = t3, this;
  }
  _onChangeCallback() {
  }
  *[Symbol.iterator]() {
    yield this._x, yield this._y, yield this._z, yield this._order;
  }
};
He.DEFAULT_ORDER = "XYZ";
var Ni = class {
  constructor() {
    this.mask = 1;
  }
  set(t3) {
    this.mask = (1 << t3 | 0) >>> 0;
  }
  enable(t3) {
    this.mask |= 1 << t3 | 0;
  }
  enableAll() {
    this.mask = -1;
  }
  toggle(t3) {
    this.mask ^= 1 << t3 | 0;
  }
  disable(t3) {
    this.mask &= ~(1 << t3 | 0);
  }
  disableAll() {
    this.mask = 0;
  }
  test(t3) {
    return (this.mask & t3.mask) !== 0;
  }
  isEnabled(t3) {
    return (this.mask & (1 << t3 | 0)) !== 0;
  }
};
var mc = 0;
var bo = new F();
var ei = new cn();
var nn = new oe();
var ls = new F();
var Ci = new F();
var gc = new F();
var _c = new cn();
var Eo = new F(1, 0, 0);
var To = new F(0, 1, 0);
var Ao = new F(0, 0, 1);
var wo = { type: "added" };
var xc = { type: "removed" };
var ni = { type: "childadded", child: null };
var ia = { type: "childremoved", child: null };
var xe = class i8 extends ln {
  constructor() {
    super(), this.isObject3D = true, Object.defineProperty(this, "id", { value: mc++ }), this.uuid = Qi(), this.name = "", this.type = "Object3D", this.parent = null, this.children = [], this.up = i8.DEFAULT_UP.clone();
    let t3 = new F(), e = new He(), n = new cn(), s = new F(1, 1, 1);
    function r() {
      n.setFromEuler(e, false);
    }
    function a() {
      e.setFromQuaternion(n, void 0, false);
    }
    e._onChange(r), n._onChange(a), Object.defineProperties(this, { position: { configurable: true, enumerable: true, value: t3 }, rotation: { configurable: true, enumerable: true, value: e }, quaternion: { configurable: true, enumerable: true, value: n }, scale: { configurable: true, enumerable: true, value: s }, modelViewMatrix: { value: new oe() }, normalMatrix: { value: new Lt() } }), this.matrix = new oe(), this.matrixWorld = new oe(), this.matrixAutoUpdate = i8.DEFAULT_MATRIX_AUTO_UPDATE, this.matrixWorldAutoUpdate = i8.DEFAULT_MATRIX_WORLD_AUTO_UPDATE, this.matrixWorldNeedsUpdate = false, this.layers = new Ni(), this.visible = true, this.castShadow = false, this.receiveShadow = false, this.frustumCulled = true, this.renderOrder = 0, this.animations = [], this.customDepthMaterial = void 0, this.customDistanceMaterial = void 0, this.userData = {};
  }
  onBeforeShadow() {
  }
  onAfterShadow() {
  }
  onBeforeRender() {
  }
  onAfterRender() {
  }
  applyMatrix4(t3) {
    this.matrixAutoUpdate && this.updateMatrix(), this.matrix.premultiply(t3), this.matrix.decompose(this.position, this.quaternion, this.scale);
  }
  applyQuaternion(t3) {
    return this.quaternion.premultiply(t3), this;
  }
  setRotationFromAxisAngle(t3, e) {
    this.quaternion.setFromAxisAngle(t3, e);
  }
  setRotationFromEuler(t3) {
    this.quaternion.setFromEuler(t3, true);
  }
  setRotationFromMatrix(t3) {
    this.quaternion.setFromRotationMatrix(t3);
  }
  setRotationFromQuaternion(t3) {
    this.quaternion.copy(t3);
  }
  rotateOnAxis(t3, e) {
    return ei.setFromAxisAngle(t3, e), this.quaternion.multiply(ei), this;
  }
  rotateOnWorldAxis(t3, e) {
    return ei.setFromAxisAngle(t3, e), this.quaternion.premultiply(ei), this;
  }
  rotateX(t3) {
    return this.rotateOnAxis(Eo, t3);
  }
  rotateY(t3) {
    return this.rotateOnAxis(To, t3);
  }
  rotateZ(t3) {
    return this.rotateOnAxis(Ao, t3);
  }
  translateOnAxis(t3, e) {
    return bo.copy(t3).applyQuaternion(this.quaternion), this.position.add(bo.multiplyScalar(e)), this;
  }
  translateX(t3) {
    return this.translateOnAxis(Eo, t3);
  }
  translateY(t3) {
    return this.translateOnAxis(To, t3);
  }
  translateZ(t3) {
    return this.translateOnAxis(Ao, t3);
  }
  localToWorld(t3) {
    return this.updateWorldMatrix(true, false), t3.applyMatrix4(this.matrixWorld);
  }
  worldToLocal(t3) {
    return this.updateWorldMatrix(true, false), t3.applyMatrix4(nn.copy(this.matrixWorld).invert());
  }
  lookAt(t3, e, n) {
    t3.isVector3 ? ls.copy(t3) : ls.set(t3, e, n);
    let s = this.parent;
    this.updateWorldMatrix(true, false), Ci.setFromMatrixPosition(this.matrixWorld), this.isCamera || this.isLight ? nn.lookAt(Ci, ls, this.up) : nn.lookAt(ls, Ci, this.up), this.quaternion.setFromRotationMatrix(nn), s && (nn.extractRotation(s.matrixWorld), ei.setFromRotationMatrix(nn), this.quaternion.premultiply(ei.invert()));
  }
  add(t3) {
    if (arguments.length > 1) {
      for (let e = 0; e < arguments.length; e++) this.add(arguments[e]);
      return this;
    }
    return t3 === this ? (console.error("THREE.Object3D.add: object can't be added as a child of itself.", t3), this) : (t3 && t3.isObject3D ? (t3.removeFromParent(), t3.parent = this, this.children.push(t3), t3.dispatchEvent(wo), ni.child = t3, this.dispatchEvent(ni), ni.child = null) : console.error("THREE.Object3D.add: object not an instance of THREE.Object3D.", t3), this);
  }
  remove(t3) {
    if (arguments.length > 1) {
      for (let n = 0; n < arguments.length; n++) this.remove(arguments[n]);
      return this;
    }
    let e = this.children.indexOf(t3);
    return e !== -1 && (t3.parent = null, this.children.splice(e, 1), t3.dispatchEvent(xc), ia.child = t3, this.dispatchEvent(ia), ia.child = null), this;
  }
  removeFromParent() {
    let t3 = this.parent;
    return t3 !== null && t3.remove(this), this;
  }
  clear() {
    return this.remove(...this.children);
  }
  attach(t3) {
    return this.updateWorldMatrix(true, false), nn.copy(this.matrixWorld).invert(), t3.parent !== null && (t3.parent.updateWorldMatrix(true, false), nn.multiply(t3.parent.matrixWorld)), t3.applyMatrix4(nn), t3.removeFromParent(), t3.parent = this, this.children.push(t3), t3.updateWorldMatrix(false, true), t3.dispatchEvent(wo), ni.child = t3, this.dispatchEvent(ni), ni.child = null, this;
  }
  getObjectById(t3) {
    return this.getObjectByProperty("id", t3);
  }
  getObjectByName(t3) {
    return this.getObjectByProperty("name", t3);
  }
  getObjectByProperty(t3, e) {
    if (this[t3] === e) return this;
    for (let n = 0, s = this.children.length; n < s; n++) {
      let a = this.children[n].getObjectByProperty(t3, e);
      if (a !== void 0) return a;
    }
  }
  getObjectsByProperty(t3, e, n = []) {
    this[t3] === e && n.push(this);
    let s = this.children;
    for (let r = 0, a = s.length; r < a; r++) s[r].getObjectsByProperty(t3, e, n);
    return n;
  }
  getWorldPosition(t3) {
    return this.updateWorldMatrix(true, false), t3.setFromMatrixPosition(this.matrixWorld);
  }
  getWorldQuaternion(t3) {
    return this.updateWorldMatrix(true, false), this.matrixWorld.decompose(Ci, t3, gc), t3;
  }
  getWorldScale(t3) {
    return this.updateWorldMatrix(true, false), this.matrixWorld.decompose(Ci, _c, t3), t3;
  }
  getWorldDirection(t3) {
    this.updateWorldMatrix(true, false);
    let e = this.matrixWorld.elements;
    return t3.set(e[8], e[9], e[10]).normalize();
  }
  raycast() {
  }
  traverse(t3) {
    t3(this);
    let e = this.children;
    for (let n = 0, s = e.length; n < s; n++) e[n].traverse(t3);
  }
  traverseVisible(t3) {
    if (this.visible === false) return;
    t3(this);
    let e = this.children;
    for (let n = 0, s = e.length; n < s; n++) e[n].traverseVisible(t3);
  }
  traverseAncestors(t3) {
    let e = this.parent;
    e !== null && (t3(e), e.traverseAncestors(t3));
  }
  updateMatrix() {
    this.matrix.compose(this.position, this.quaternion, this.scale), this.matrixWorldNeedsUpdate = true;
  }
  updateMatrixWorld(t3) {
    this.matrixAutoUpdate && this.updateMatrix(), (this.matrixWorldNeedsUpdate || t3) && (this.matrixWorldAutoUpdate === true && (this.parent === null ? this.matrixWorld.copy(this.matrix) : this.matrixWorld.multiplyMatrices(this.parent.matrixWorld, this.matrix)), this.matrixWorldNeedsUpdate = false, t3 = true);
    let e = this.children;
    for (let n = 0, s = e.length; n < s; n++) e[n].updateMatrixWorld(t3);
  }
  updateWorldMatrix(t3, e) {
    let n = this.parent;
    if (t3 === true && n !== null && n.updateWorldMatrix(true, false), this.matrixAutoUpdate && this.updateMatrix(), this.matrixWorldAutoUpdate === true && (this.parent === null ? this.matrixWorld.copy(this.matrix) : this.matrixWorld.multiplyMatrices(this.parent.matrixWorld, this.matrix)), e === true) {
      let s = this.children;
      for (let r = 0, a = s.length; r < a; r++) s[r].updateWorldMatrix(false, true);
    }
  }
  toJSON(t3) {
    let e = t3 === void 0 || typeof t3 == "string", n = {};
    e && (t3 = { geometries: {}, materials: {}, textures: {}, images: {}, shapes: {}, skeletons: {}, animations: {}, nodes: {} }, n.metadata = { version: 4.7, type: "Object", generator: "Object3D.toJSON" });
    let s = {};
    s.uuid = this.uuid, s.type = this.type, this.name !== "" && (s.name = this.name), this.castShadow === true && (s.castShadow = true), this.receiveShadow === true && (s.receiveShadow = true), this.visible === false && (s.visible = false), this.frustumCulled === false && (s.frustumCulled = false), this.renderOrder !== 0 && (s.renderOrder = this.renderOrder), Object.keys(this.userData).length > 0 && (s.userData = this.userData), s.layers = this.layers.mask, s.matrix = this.matrix.toArray(), s.up = this.up.toArray(), this.matrixAutoUpdate === false && (s.matrixAutoUpdate = false), this.isInstancedMesh && (s.type = "InstancedMesh", s.count = this.count, s.instanceMatrix = this.instanceMatrix.toJSON(), this.instanceColor !== null && (s.instanceColor = this.instanceColor.toJSON())), this.isBatchedMesh && (s.type = "BatchedMesh", s.perObjectFrustumCulled = this.perObjectFrustumCulled, s.sortObjects = this.sortObjects, s.drawRanges = this._drawRanges, s.reservedRanges = this._reservedRanges, s.geometryInfo = this._geometryInfo.map((o) => ({ ...o, boundingBox: o.boundingBox ? o.boundingBox.toJSON() : void 0, boundingSphere: o.boundingSphere ? o.boundingSphere.toJSON() : void 0 })), s.instanceInfo = this._instanceInfo.map((o) => ({ ...o })), s.availableInstanceIds = this._availableInstanceIds.slice(), s.availableGeometryIds = this._availableGeometryIds.slice(), s.nextIndexStart = this._nextIndexStart, s.nextVertexStart = this._nextVertexStart, s.geometryCount = this._geometryCount, s.maxInstanceCount = this._maxInstanceCount, s.maxVertexCount = this._maxVertexCount, s.maxIndexCount = this._maxIndexCount, s.geometryInitialized = this._geometryInitialized, s.matricesTexture = this._matricesTexture.toJSON(t3), s.indirectTexture = this._indirectTexture.toJSON(t3), this._colorsTexture !== null && (s.colorsTexture = this._colorsTexture.toJSON(t3)), this.boundingSphere !== null && (s.boundingSphere = this.boundingSphere.toJSON()), this.boundingBox !== null && (s.boundingBox = this.boundingBox.toJSON()));
    function r(o, c) {
      return o[c.uuid] === void 0 && (o[c.uuid] = c.toJSON(t3)), c.uuid;
    }
    if (this.isScene) this.background && (this.background.isColor ? s.background = this.background.toJSON() : this.background.isTexture && (s.background = this.background.toJSON(t3).uuid)), this.environment && this.environment.isTexture && this.environment.isRenderTargetTexture !== true && (s.environment = this.environment.toJSON(t3).uuid);
    else if (this.isMesh || this.isLine || this.isPoints) {
      s.geometry = r(t3.geometries, this.geometry);
      let o = this.geometry.parameters;
      if (o !== void 0 && o.shapes !== void 0) {
        let c = o.shapes;
        if (Array.isArray(c)) for (let l = 0, u = c.length; l < u; l++) {
          let d = c[l];
          r(t3.shapes, d);
        }
        else r(t3.shapes, c);
      }
    }
    if (this.isSkinnedMesh && (s.bindMode = this.bindMode, s.bindMatrix = this.bindMatrix.toArray(), this.skeleton !== void 0 && (r(t3.skeletons, this.skeleton), s.skeleton = this.skeleton.uuid)), this.material !== void 0) if (Array.isArray(this.material)) {
      let o = [];
      for (let c = 0, l = this.material.length; c < l; c++) o.push(r(t3.materials, this.material[c]));
      s.material = o;
    } else s.material = r(t3.materials, this.material);
    if (this.children.length > 0) {
      s.children = [];
      for (let o = 0; o < this.children.length; o++) s.children.push(this.children[o].toJSON(t3).object);
    }
    if (this.animations.length > 0) {
      s.animations = [];
      for (let o = 0; o < this.animations.length; o++) {
        let c = this.animations[o];
        s.animations.push(r(t3.animations, c));
      }
    }
    if (e) {
      let o = a(t3.geometries), c = a(t3.materials), l = a(t3.textures), u = a(t3.images), d = a(t3.shapes), f = a(t3.skeletons), m = a(t3.animations), x = a(t3.nodes);
      o.length > 0 && (n.geometries = o), c.length > 0 && (n.materials = c), l.length > 0 && (n.textures = l), u.length > 0 && (n.images = u), d.length > 0 && (n.shapes = d), f.length > 0 && (n.skeletons = f), m.length > 0 && (n.animations = m), x.length > 0 && (n.nodes = x);
    }
    return n.object = s, n;
    function a(o) {
      let c = [];
      for (let l in o) {
        let u = o[l];
        delete u.metadata, c.push(u);
      }
      return c;
    }
  }
  clone(t3) {
    return new this.constructor().copy(this, t3);
  }
  copy(t3, e = true) {
    if (this.name = t3.name, this.up.copy(t3.up), this.position.copy(t3.position), this.rotation.order = t3.rotation.order, this.quaternion.copy(t3.quaternion), this.scale.copy(t3.scale), this.matrix.copy(t3.matrix), this.matrixWorld.copy(t3.matrixWorld), this.matrixAutoUpdate = t3.matrixAutoUpdate, this.matrixWorldAutoUpdate = t3.matrixWorldAutoUpdate, this.matrixWorldNeedsUpdate = t3.matrixWorldNeedsUpdate, this.layers.mask = t3.layers.mask, this.visible = t3.visible, this.castShadow = t3.castShadow, this.receiveShadow = t3.receiveShadow, this.frustumCulled = t3.frustumCulled, this.renderOrder = t3.renderOrder, this.animations = t3.animations.slice(), this.userData = JSON.parse(JSON.stringify(t3.userData)), e === true) for (let n = 0; n < t3.children.length; n++) {
      let s = t3.children[n];
      this.add(s.clone());
    }
    return this;
  }
};
xe.DEFAULT_UP = new F(0, 1, 0);
xe.DEFAULT_MATRIX_AUTO_UPDATE = true;
xe.DEFAULT_MATRIX_WORLD_AUTO_UPDATE = true;
var ze = new F();
var sn = new F();
var sa = new F();
var rn = new F();
var ii = new F();
var si = new F();
var Co = new F();
var ra = new F();
var aa = new F();
var oa = new F();
var la = new se();
var ca = new se();
var ha = new se();
var vn = class i9 {
  constructor(t3 = new F(), e = new F(), n = new F()) {
    this.a = t3, this.b = e, this.c = n;
  }
  static getNormal(t3, e, n, s) {
    s.subVectors(n, e), ze.subVectors(t3, e), s.cross(ze);
    let r = s.lengthSq();
    return r > 0 ? s.multiplyScalar(1 / Math.sqrt(r)) : s.set(0, 0, 0);
  }
  static getBarycoord(t3, e, n, s, r) {
    ze.subVectors(s, e), sn.subVectors(n, e), sa.subVectors(t3, e);
    let a = ze.dot(ze), o = ze.dot(sn), c = ze.dot(sa), l = sn.dot(sn), u = sn.dot(sa), d = a * l - o * o;
    if (d === 0) return r.set(0, 0, 0), null;
    let f = 1 / d, m = (l * c - o * u) * f, x = (a * u - o * c) * f;
    return r.set(1 - m - x, x, m);
  }
  static containsPoint(t3, e, n, s) {
    return this.getBarycoord(t3, e, n, s, rn) === null ? false : rn.x >= 0 && rn.y >= 0 && rn.x + rn.y <= 1;
  }
  static getInterpolation(t3, e, n, s, r, a, o, c) {
    return this.getBarycoord(t3, e, n, s, rn) === null ? (c.x = 0, c.y = 0, "z" in c && (c.z = 0), "w" in c && (c.w = 0), null) : (c.setScalar(0), c.addScaledVector(r, rn.x), c.addScaledVector(a, rn.y), c.addScaledVector(o, rn.z), c);
  }
  static getInterpolatedAttribute(t3, e, n, s, r, a) {
    return la.setScalar(0), ca.setScalar(0), ha.setScalar(0), la.fromBufferAttribute(t3, e), ca.fromBufferAttribute(t3, n), ha.fromBufferAttribute(t3, s), a.setScalar(0), a.addScaledVector(la, r.x), a.addScaledVector(ca, r.y), a.addScaledVector(ha, r.z), a;
  }
  static isFrontFacing(t3, e, n, s) {
    return ze.subVectors(n, e), sn.subVectors(t3, e), ze.cross(sn).dot(s) < 0;
  }
  set(t3, e, n) {
    return this.a.copy(t3), this.b.copy(e), this.c.copy(n), this;
  }
  setFromPointsAndIndices(t3, e, n, s) {
    return this.a.copy(t3[e]), this.b.copy(t3[n]), this.c.copy(t3[s]), this;
  }
  setFromAttributeAndIndices(t3, e, n, s) {
    return this.a.fromBufferAttribute(t3, e), this.b.fromBufferAttribute(t3, n), this.c.fromBufferAttribute(t3, s), this;
  }
  clone() {
    return new this.constructor().copy(this);
  }
  copy(t3) {
    return this.a.copy(t3.a), this.b.copy(t3.b), this.c.copy(t3.c), this;
  }
  getArea() {
    return ze.subVectors(this.c, this.b), sn.subVectors(this.a, this.b), ze.cross(sn).length() * 0.5;
  }
  getMidpoint(t3) {
    return t3.addVectors(this.a, this.b).add(this.c).multiplyScalar(1 / 3);
  }
  getNormal(t3) {
    return i9.getNormal(this.a, this.b, this.c, t3);
  }
  getPlane(t3) {
    return t3.setFromCoplanarPoints(this.a, this.b, this.c);
  }
  getBarycoord(t3, e) {
    return i9.getBarycoord(t3, this.a, this.b, this.c, e);
  }
  getInterpolation(t3, e, n, s, r) {
    return i9.getInterpolation(t3, this.a, this.b, this.c, e, n, s, r);
  }
  containsPoint(t3) {
    return i9.containsPoint(t3, this.a, this.b, this.c);
  }
  isFrontFacing(t3) {
    return i9.isFrontFacing(this.a, this.b, this.c, t3);
  }
  intersectsBox(t3) {
    return t3.intersectsTriangle(this);
  }
  closestPointToPoint(t3, e) {
    let n = this.a, s = this.b, r = this.c, a, o;
    ii.subVectors(s, n), si.subVectors(r, n), ra.subVectors(t3, n);
    let c = ii.dot(ra), l = si.dot(ra);
    if (c <= 0 && l <= 0) return e.copy(n);
    aa.subVectors(t3, s);
    let u = ii.dot(aa), d = si.dot(aa);
    if (u >= 0 && d <= u) return e.copy(s);
    let f = c * d - u * l;
    if (f <= 0 && c >= 0 && u <= 0) return a = c / (c - u), e.copy(n).addScaledVector(ii, a);
    oa.subVectors(t3, r);
    let m = ii.dot(oa), x = si.dot(oa);
    if (x >= 0 && m <= x) return e.copy(r);
    let v = m * l - c * x;
    if (v <= 0 && l >= 0 && x <= 0) return o = l / (l - x), e.copy(n).addScaledVector(si, o);
    let p = u * x - m * d;
    if (p <= 0 && d - u >= 0 && m - x >= 0) return Co.subVectors(r, s), o = (d - u) / (d - u + (m - x)), e.copy(s).addScaledVector(Co, o);
    let h = 1 / (p + v + f);
    return a = v * h, o = f * h, e.copy(n).addScaledVector(ii, a).addScaledVector(si, o);
  }
  equals(t3) {
    return t3.a.equals(this.a) && t3.b.equals(this.b) && t3.c.equals(this.c);
  }
};
var Tl = { aliceblue: 15792383, antiquewhite: 16444375, aqua: 65535, aquamarine: 8388564, azure: 15794175, beige: 16119260, bisque: 16770244, black: 0, blanchedalmond: 16772045, blue: 255, blueviolet: 9055202, brown: 10824234, burlywood: 14596231, cadetblue: 6266528, chartreuse: 8388352, chocolate: 13789470, coral: 16744272, cornflowerblue: 6591981, cornsilk: 16775388, crimson: 14423100, cyan: 65535, darkblue: 139, darkcyan: 35723, darkgoldenrod: 12092939, darkgray: 11119017, darkgreen: 25600, darkgrey: 11119017, darkkhaki: 12433259, darkmagenta: 9109643, darkolivegreen: 5597999, darkorange: 16747520, darkorchid: 10040012, darkred: 9109504, darksalmon: 15308410, darkseagreen: 9419919, darkslateblue: 4734347, darkslategray: 3100495, darkslategrey: 3100495, darkturquoise: 52945, darkviolet: 9699539, deeppink: 16716947, deepskyblue: 49151, dimgray: 6908265, dimgrey: 6908265, dodgerblue: 2003199, firebrick: 11674146, floralwhite: 16775920, forestgreen: 2263842, fuchsia: 16711935, gainsboro: 14474460, ghostwhite: 16316671, gold: 16766720, goldenrod: 14329120, gray: 8421504, green: 32768, greenyellow: 11403055, grey: 8421504, honeydew: 15794160, hotpink: 16738740, indianred: 13458524, indigo: 4915330, ivory: 16777200, khaki: 15787660, lavender: 15132410, lavenderblush: 16773365, lawngreen: 8190976, lemonchiffon: 16775885, lightblue: 11393254, lightcoral: 15761536, lightcyan: 14745599, lightgoldenrodyellow: 16448210, lightgray: 13882323, lightgreen: 9498256, lightgrey: 13882323, lightpink: 16758465, lightsalmon: 16752762, lightseagreen: 2142890, lightskyblue: 8900346, lightslategray: 7833753, lightslategrey: 7833753, lightsteelblue: 11584734, lightyellow: 16777184, lime: 65280, limegreen: 3329330, linen: 16445670, magenta: 16711935, maroon: 8388608, mediumaquamarine: 6737322, mediumblue: 205, mediumorchid: 12211667, mediumpurple: 9662683, mediumseagreen: 3978097, mediumslateblue: 8087790, mediumspringgreen: 64154, mediumturquoise: 4772300, mediumvioletred: 13047173, midnightblue: 1644912, mintcream: 16121850, mistyrose: 16770273, moccasin: 16770229, navajowhite: 16768685, navy: 128, oldlace: 16643558, olive: 8421376, olivedrab: 7048739, orange: 16753920, orangered: 16729344, orchid: 14315734, palegoldenrod: 15657130, palegreen: 10025880, paleturquoise: 11529966, palevioletred: 14381203, papayawhip: 16773077, peachpuff: 16767673, peru: 13468991, pink: 16761035, plum: 14524637, powderblue: 11591910, purple: 8388736, rebeccapurple: 6697881, red: 16711680, rosybrown: 12357519, royalblue: 4286945, saddlebrown: 9127187, salmon: 16416882, sandybrown: 16032864, seagreen: 3050327, seashell: 16774638, sienna: 10506797, silver: 12632256, skyblue: 8900331, slateblue: 6970061, slategray: 7372944, slategrey: 7372944, snow: 16775930, springgreen: 65407, steelblue: 4620980, tan: 13808780, teal: 32896, thistle: 14204888, tomato: 16737095, turquoise: 4251856, violet: 15631086, wheat: 16113331, white: 16777215, whitesmoke: 16119285, yellow: 16776960, yellowgreen: 10145074 };
var _n = { h: 0, s: 0, l: 0 };
var cs = { h: 0, s: 0, l: 0 };
function ua(i14, t3, e) {
  return e < 0 && (e += 1), e > 1 && (e -= 1), e < 1 / 6 ? i14 + (t3 - i14) * 6 * e : e < 1 / 2 ? t3 : e < 2 / 3 ? i14 + (t3 - i14) * 6 * (2 / 3 - e) : i14;
}
var Vt = class {
  constructor(t3, e, n) {
    return this.isColor = true, this.r = 1, this.g = 1, this.b = 1, this.set(t3, e, n);
  }
  set(t3, e, n) {
    if (e === void 0 && n === void 0) {
      let s = t3;
      s && s.isColor ? this.copy(s) : typeof s == "number" ? this.setHex(s) : typeof s == "string" && this.setStyle(s);
    } else this.setRGB(t3, e, n);
    return this;
  }
  setScalar(t3) {
    return this.r = t3, this.g = t3, this.b = t3, this;
  }
  setHex(t3, e = we) {
    return t3 = Math.floor(t3), this.r = (t3 >> 16 & 255) / 255, this.g = (t3 >> 8 & 255) / 255, this.b = (t3 & 255) / 255, kt.colorSpaceToWorking(this, e), this;
  }
  setRGB(t3, e, n, s = kt.workingColorSpace) {
    return this.r = t3, this.g = e, this.b = n, kt.colorSpaceToWorking(this, s), this;
  }
  setHSL(t3, e, n, s = kt.workingColorSpace) {
    if (t3 = lc(t3, 1), e = Bt(e, 0, 1), n = Bt(n, 0, 1), e === 0) this.r = this.g = this.b = n;
    else {
      let r = n <= 0.5 ? n * (1 + e) : n + e - n * e, a = 2 * n - r;
      this.r = ua(a, r, t3 + 1 / 3), this.g = ua(a, r, t3), this.b = ua(a, r, t3 - 1 / 3);
    }
    return kt.colorSpaceToWorking(this, s), this;
  }
  setStyle(t3, e = we) {
    function n(r) {
      r !== void 0 && parseFloat(r) < 1 && console.warn("THREE.Color: Alpha component of " + t3 + " will be ignored.");
    }
    let s;
    if (s = /^(\w+)\(([^\)]*)\)/.exec(t3)) {
      let r, a = s[1], o = s[2];
      switch (a) {
        case "rgb":
        case "rgba":
          if (r = /^\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o)) return n(r[4]), this.setRGB(Math.min(255, parseInt(r[1], 10)) / 255, Math.min(255, parseInt(r[2], 10)) / 255, Math.min(255, parseInt(r[3], 10)) / 255, e);
          if (r = /^\s*(\d+)\%\s*,\s*(\d+)\%\s*,\s*(\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o)) return n(r[4]), this.setRGB(Math.min(100, parseInt(r[1], 10)) / 100, Math.min(100, parseInt(r[2], 10)) / 100, Math.min(100, parseInt(r[3], 10)) / 100, e);
          break;
        case "hsl":
        case "hsla":
          if (r = /^\s*(\d*\.?\d+)\s*,\s*(\d*\.?\d+)\%\s*,\s*(\d*\.?\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o)) return n(r[4]), this.setHSL(parseFloat(r[1]) / 360, parseFloat(r[2]) / 100, parseFloat(r[3]) / 100, e);
          break;
        default:
          console.warn("THREE.Color: Unknown color model " + t3);
      }
    } else if (s = /^\#([A-Fa-f\d]+)$/.exec(t3)) {
      let r = s[1], a = r.length;
      if (a === 3) return this.setRGB(parseInt(r.charAt(0), 16) / 15, parseInt(r.charAt(1), 16) / 15, parseInt(r.charAt(2), 16) / 15, e);
      if (a === 6) return this.setHex(parseInt(r, 16), e);
      console.warn("THREE.Color: Invalid hex color " + t3);
    } else if (t3 && t3.length > 0) return this.setColorName(t3, e);
    return this;
  }
  setColorName(t3, e = we) {
    let n = Tl[t3.toLowerCase()];
    return n !== void 0 ? this.setHex(n, e) : console.warn("THREE.Color: Unknown color " + t3), this;
  }
  clone() {
    return new this.constructor(this.r, this.g, this.b);
  }
  copy(t3) {
    return this.r = t3.r, this.g = t3.g, this.b = t3.b, this;
  }
  copySRGBToLinear(t3) {
    return this.r = an(t3.r), this.g = an(t3.g), this.b = an(t3.b), this;
  }
  copyLinearToSRGB(t3) {
    return this.r = li(t3.r), this.g = li(t3.g), this.b = li(t3.b), this;
  }
  convertSRGBToLinear() {
    return this.copySRGBToLinear(this), this;
  }
  convertLinearToSRGB() {
    return this.copyLinearToSRGB(this), this;
  }
  getHex(t3 = we) {
    return kt.workingToColorSpace(me.copy(this), t3), Math.round(Bt(me.r * 255, 0, 255)) * 65536 + Math.round(Bt(me.g * 255, 0, 255)) * 256 + Math.round(Bt(me.b * 255, 0, 255));
  }
  getHexString(t3 = we) {
    return ("000000" + this.getHex(t3).toString(16)).slice(-6);
  }
  getHSL(t3, e = kt.workingColorSpace) {
    kt.workingToColorSpace(me.copy(this), e);
    let n = me.r, s = me.g, r = me.b, a = Math.max(n, s, r), o = Math.min(n, s, r), c, l, u = (o + a) / 2;
    if (o === a) c = 0, l = 0;
    else {
      let d = a - o;
      switch (l = u <= 0.5 ? d / (a + o) : d / (2 - a - o), a) {
        case n:
          c = (s - r) / d + (s < r ? 6 : 0);
          break;
        case s:
          c = (r - n) / d + 2;
          break;
        case r:
          c = (n - s) / d + 4;
          break;
      }
      c /= 6;
    }
    return t3.h = c, t3.s = l, t3.l = u, t3;
  }
  getRGB(t3, e = kt.workingColorSpace) {
    return kt.workingToColorSpace(me.copy(this), e), t3.r = me.r, t3.g = me.g, t3.b = me.b, t3;
  }
  getStyle(t3 = we) {
    kt.workingToColorSpace(me.copy(this), t3);
    let e = me.r, n = me.g, s = me.b;
    return t3 !== we ? `color(${t3} ${e.toFixed(3)} ${n.toFixed(3)} ${s.toFixed(3)})` : `rgb(${Math.round(e * 255)},${Math.round(n * 255)},${Math.round(s * 255)})`;
  }
  offsetHSL(t3, e, n) {
    return this.getHSL(_n), this.setHSL(_n.h + t3, _n.s + e, _n.l + n);
  }
  add(t3) {
    return this.r += t3.r, this.g += t3.g, this.b += t3.b, this;
  }
  addColors(t3, e) {
    return this.r = t3.r + e.r, this.g = t3.g + e.g, this.b = t3.b + e.b, this;
  }
  addScalar(t3) {
    return this.r += t3, this.g += t3, this.b += t3, this;
  }
  sub(t3) {
    return this.r = Math.max(0, this.r - t3.r), this.g = Math.max(0, this.g - t3.g), this.b = Math.max(0, this.b - t3.b), this;
  }
  multiply(t3) {
    return this.r *= t3.r, this.g *= t3.g, this.b *= t3.b, this;
  }
  multiplyScalar(t3) {
    return this.r *= t3, this.g *= t3, this.b *= t3, this;
  }
  lerp(t3, e) {
    return this.r += (t3.r - this.r) * e, this.g += (t3.g - this.g) * e, this.b += (t3.b - this.b) * e, this;
  }
  lerpColors(t3, e, n) {
    return this.r = t3.r + (e.r - t3.r) * n, this.g = t3.g + (e.g - t3.g) * n, this.b = t3.b + (e.b - t3.b) * n, this;
  }
  lerpHSL(t3, e) {
    this.getHSL(_n), t3.getHSL(cs);
    let n = Yr(_n.h, cs.h, e), s = Yr(_n.s, cs.s, e), r = Yr(_n.l, cs.l, e);
    return this.setHSL(n, s, r), this;
  }
  setFromVector3(t3) {
    return this.r = t3.x, this.g = t3.y, this.b = t3.z, this;
  }
  applyMatrix3(t3) {
    let e = this.r, n = this.g, s = this.b, r = t3.elements;
    return this.r = r[0] * e + r[3] * n + r[6] * s, this.g = r[1] * e + r[4] * n + r[7] * s, this.b = r[2] * e + r[5] * n + r[8] * s, this;
  }
  equals(t3) {
    return t3.r === this.r && t3.g === this.g && t3.b === this.b;
  }
  fromArray(t3, e = 0) {
    return this.r = t3[e], this.g = t3[e + 1], this.b = t3[e + 2], this;
  }
  toArray(t3 = [], e = 0) {
    return t3[e] = this.r, t3[e + 1] = this.g, t3[e + 2] = this.b, t3;
  }
  fromBufferAttribute(t3, e) {
    return this.r = t3.getX(e), this.g = t3.getY(e), this.b = t3.getZ(e), this;
  }
  toJSON() {
    return this.getHex();
  }
  *[Symbol.iterator]() {
    yield this.r, yield this.g, yield this.b;
  }
};
var me = new Vt();
Vt.NAMES = Tl;
var vc = 0;
var bn = class extends ln {
  constructor() {
    super(), this.isMaterial = true, Object.defineProperty(this, "id", { value: vc++ }), this.uuid = Qi(), this.name = "", this.type = "Material", this.blending = On, this.side = on, this.vertexColors = false, this.opacity = 1, this.transparent = false, this.alphaHash = false, this.blendSrc = Ms, this.blendDst = Ss, this.blendEquation = Mn, this.blendSrcAlpha = null, this.blendDstAlpha = null, this.blendEquationAlpha = null, this.blendColor = new Vt(0, 0, 0), this.blendAlpha = 0, this.depthFunc = Bn, this.depthTest = true, this.depthWrite = true, this.stencilWriteMask = 255, this.stencilFunc = va, this.stencilRef = 0, this.stencilFuncMask = 255, this.stencilFail = Nn, this.stencilZFail = Nn, this.stencilZPass = Nn, this.stencilWrite = false, this.clippingPlanes = null, this.clipIntersection = false, this.clipShadows = false, this.shadowSide = null, this.colorWrite = true, this.precision = null, this.polygonOffset = false, this.polygonOffsetFactor = 0, this.polygonOffsetUnits = 0, this.dithering = false, this.alphaToCoverage = false, this.premultipliedAlpha = false, this.forceSinglePass = false, this.allowOverride = true, this.visible = true, this.toneMapped = true, this.userData = {}, this.version = 0, this._alphaTest = 0;
  }
  get alphaTest() {
    return this._alphaTest;
  }
  set alphaTest(t3) {
    this._alphaTest > 0 != t3 > 0 && this.version++, this._alphaTest = t3;
  }
  onBeforeRender() {
  }
  onBeforeCompile() {
  }
  customProgramCacheKey() {
    return this.onBeforeCompile.toString();
  }
  setValues(t3) {
    if (t3 !== void 0) for (let e in t3) {
      let n = t3[e];
      if (n === void 0) {
        console.warn(`THREE.Material: parameter '${e}' has value of undefined.`);
        continue;
      }
      let s = this[e];
      if (s === void 0) {
        console.warn(`THREE.Material: '${e}' is not a property of THREE.${this.type}.`);
        continue;
      }
      s && s.isColor ? s.set(n) : s && s.isVector3 && n && n.isVector3 ? s.copy(n) : this[e] = n;
    }
  }
  toJSON(t3) {
    let e = t3 === void 0 || typeof t3 == "string";
    e && (t3 = { textures: {}, images: {} });
    let n = { metadata: { version: 4.7, type: "Material", generator: "Material.toJSON" } };
    n.uuid = this.uuid, n.type = this.type, this.name !== "" && (n.name = this.name), this.color && this.color.isColor && (n.color = this.color.getHex()), this.roughness !== void 0 && (n.roughness = this.roughness), this.metalness !== void 0 && (n.metalness = this.metalness), this.sheen !== void 0 && (n.sheen = this.sheen), this.sheenColor && this.sheenColor.isColor && (n.sheenColor = this.sheenColor.getHex()), this.sheenRoughness !== void 0 && (n.sheenRoughness = this.sheenRoughness), this.emissive && this.emissive.isColor && (n.emissive = this.emissive.getHex()), this.emissiveIntensity !== void 0 && this.emissiveIntensity !== 1 && (n.emissiveIntensity = this.emissiveIntensity), this.specular && this.specular.isColor && (n.specular = this.specular.getHex()), this.specularIntensity !== void 0 && (n.specularIntensity = this.specularIntensity), this.specularColor && this.specularColor.isColor && (n.specularColor = this.specularColor.getHex()), this.shininess !== void 0 && (n.shininess = this.shininess), this.clearcoat !== void 0 && (n.clearcoat = this.clearcoat), this.clearcoatRoughness !== void 0 && (n.clearcoatRoughness = this.clearcoatRoughness), this.clearcoatMap && this.clearcoatMap.isTexture && (n.clearcoatMap = this.clearcoatMap.toJSON(t3).uuid), this.clearcoatRoughnessMap && this.clearcoatRoughnessMap.isTexture && (n.clearcoatRoughnessMap = this.clearcoatRoughnessMap.toJSON(t3).uuid), this.clearcoatNormalMap && this.clearcoatNormalMap.isTexture && (n.clearcoatNormalMap = this.clearcoatNormalMap.toJSON(t3).uuid, n.clearcoatNormalScale = this.clearcoatNormalScale.toArray()), this.sheenColorMap && this.sheenColorMap.isTexture && (n.sheenColorMap = this.sheenColorMap.toJSON(t3).uuid), this.sheenRoughnessMap && this.sheenRoughnessMap.isTexture && (n.sheenRoughnessMap = this.sheenRoughnessMap.toJSON(t3).uuid), this.dispersion !== void 0 && (n.dispersion = this.dispersion), this.iridescence !== void 0 && (n.iridescence = this.iridescence), this.iridescenceIOR !== void 0 && (n.iridescenceIOR = this.iridescenceIOR), this.iridescenceThicknessRange !== void 0 && (n.iridescenceThicknessRange = this.iridescenceThicknessRange), this.iridescenceMap && this.iridescenceMap.isTexture && (n.iridescenceMap = this.iridescenceMap.toJSON(t3).uuid), this.iridescenceThicknessMap && this.iridescenceThicknessMap.isTexture && (n.iridescenceThicknessMap = this.iridescenceThicknessMap.toJSON(t3).uuid), this.anisotropy !== void 0 && (n.anisotropy = this.anisotropy), this.anisotropyRotation !== void 0 && (n.anisotropyRotation = this.anisotropyRotation), this.anisotropyMap && this.anisotropyMap.isTexture && (n.anisotropyMap = this.anisotropyMap.toJSON(t3).uuid), this.map && this.map.isTexture && (n.map = this.map.toJSON(t3).uuid), this.matcap && this.matcap.isTexture && (n.matcap = this.matcap.toJSON(t3).uuid), this.alphaMap && this.alphaMap.isTexture && (n.alphaMap = this.alphaMap.toJSON(t3).uuid), this.lightMap && this.lightMap.isTexture && (n.lightMap = this.lightMap.toJSON(t3).uuid, n.lightMapIntensity = this.lightMapIntensity), this.aoMap && this.aoMap.isTexture && (n.aoMap = this.aoMap.toJSON(t3).uuid, n.aoMapIntensity = this.aoMapIntensity), this.bumpMap && this.bumpMap.isTexture && (n.bumpMap = this.bumpMap.toJSON(t3).uuid, n.bumpScale = this.bumpScale), this.normalMap && this.normalMap.isTexture && (n.normalMap = this.normalMap.toJSON(t3).uuid, n.normalMapType = this.normalMapType, n.normalScale = this.normalScale.toArray()), this.displacementMap && this.displacementMap.isTexture && (n.displacementMap = this.displacementMap.toJSON(t3).uuid, n.displacementScale = this.displacementScale, n.displacementBias = this.displacementBias), this.roughnessMap && this.roughnessMap.isTexture && (n.roughnessMap = this.roughnessMap.toJSON(t3).uuid), this.metalnessMap && this.metalnessMap.isTexture && (n.metalnessMap = this.metalnessMap.toJSON(t3).uuid), this.emissiveMap && this.emissiveMap.isTexture && (n.emissiveMap = this.emissiveMap.toJSON(t3).uuid), this.specularMap && this.specularMap.isTexture && (n.specularMap = this.specularMap.toJSON(t3).uuid), this.specularIntensityMap && this.specularIntensityMap.isTexture && (n.specularIntensityMap = this.specularIntensityMap.toJSON(t3).uuid), this.specularColorMap && this.specularColorMap.isTexture && (n.specularColorMap = this.specularColorMap.toJSON(t3).uuid), this.envMap && this.envMap.isTexture && (n.envMap = this.envMap.toJSON(t3).uuid, this.combine !== void 0 && (n.combine = this.combine)), this.envMapRotation !== void 0 && (n.envMapRotation = this.envMapRotation.toArray()), this.envMapIntensity !== void 0 && (n.envMapIntensity = this.envMapIntensity), this.reflectivity !== void 0 && (n.reflectivity = this.reflectivity), this.refractionRatio !== void 0 && (n.refractionRatio = this.refractionRatio), this.gradientMap && this.gradientMap.isTexture && (n.gradientMap = this.gradientMap.toJSON(t3).uuid), this.transmission !== void 0 && (n.transmission = this.transmission), this.transmissionMap && this.transmissionMap.isTexture && (n.transmissionMap = this.transmissionMap.toJSON(t3).uuid), this.thickness !== void 0 && (n.thickness = this.thickness), this.thicknessMap && this.thicknessMap.isTexture && (n.thicknessMap = this.thicknessMap.toJSON(t3).uuid), this.attenuationDistance !== void 0 && this.attenuationDistance !== 1 / 0 && (n.attenuationDistance = this.attenuationDistance), this.attenuationColor !== void 0 && (n.attenuationColor = this.attenuationColor.getHex()), this.size !== void 0 && (n.size = this.size), this.shadowSide !== null && (n.shadowSide = this.shadowSide), this.sizeAttenuation !== void 0 && (n.sizeAttenuation = this.sizeAttenuation), this.blending !== On && (n.blending = this.blending), this.side !== on && (n.side = this.side), this.vertexColors === true && (n.vertexColors = true), this.opacity < 1 && (n.opacity = this.opacity), this.transparent === true && (n.transparent = true), this.blendSrc !== Ms && (n.blendSrc = this.blendSrc), this.blendDst !== Ss && (n.blendDst = this.blendDst), this.blendEquation !== Mn && (n.blendEquation = this.blendEquation), this.blendSrcAlpha !== null && (n.blendSrcAlpha = this.blendSrcAlpha), this.blendDstAlpha !== null && (n.blendDstAlpha = this.blendDstAlpha), this.blendEquationAlpha !== null && (n.blendEquationAlpha = this.blendEquationAlpha), this.blendColor && this.blendColor.isColor && (n.blendColor = this.blendColor.getHex()), this.blendAlpha !== 0 && (n.blendAlpha = this.blendAlpha), this.depthFunc !== Bn && (n.depthFunc = this.depthFunc), this.depthTest === false && (n.depthTest = this.depthTest), this.depthWrite === false && (n.depthWrite = this.depthWrite), this.colorWrite === false && (n.colorWrite = this.colorWrite), this.stencilWriteMask !== 255 && (n.stencilWriteMask = this.stencilWriteMask), this.stencilFunc !== va && (n.stencilFunc = this.stencilFunc), this.stencilRef !== 0 && (n.stencilRef = this.stencilRef), this.stencilFuncMask !== 255 && (n.stencilFuncMask = this.stencilFuncMask), this.stencilFail !== Nn && (n.stencilFail = this.stencilFail), this.stencilZFail !== Nn && (n.stencilZFail = this.stencilZFail), this.stencilZPass !== Nn && (n.stencilZPass = this.stencilZPass), this.stencilWrite === true && (n.stencilWrite = this.stencilWrite), this.rotation !== void 0 && this.rotation !== 0 && (n.rotation = this.rotation), this.polygonOffset === true && (n.polygonOffset = true), this.polygonOffsetFactor !== 0 && (n.polygonOffsetFactor = this.polygonOffsetFactor), this.polygonOffsetUnits !== 0 && (n.polygonOffsetUnits = this.polygonOffsetUnits), this.linewidth !== void 0 && this.linewidth !== 1 && (n.linewidth = this.linewidth), this.dashSize !== void 0 && (n.dashSize = this.dashSize), this.gapSize !== void 0 && (n.gapSize = this.gapSize), this.scale !== void 0 && (n.scale = this.scale), this.dithering === true && (n.dithering = true), this.alphaTest > 0 && (n.alphaTest = this.alphaTest), this.alphaHash === true && (n.alphaHash = true), this.alphaToCoverage === true && (n.alphaToCoverage = true), this.premultipliedAlpha === true && (n.premultipliedAlpha = true), this.forceSinglePass === true && (n.forceSinglePass = true), this.wireframe === true && (n.wireframe = true), this.wireframeLinewidth > 1 && (n.wireframeLinewidth = this.wireframeLinewidth), this.wireframeLinecap !== "round" && (n.wireframeLinecap = this.wireframeLinecap), this.wireframeLinejoin !== "round" && (n.wireframeLinejoin = this.wireframeLinejoin), this.flatShading === true && (n.flatShading = true), this.visible === false && (n.visible = false), this.toneMapped === false && (n.toneMapped = false), this.fog === false && (n.fog = false), Object.keys(this.userData).length > 0 && (n.userData = this.userData);
    function s(r) {
      let a = [];
      for (let o in r) {
        let c = r[o];
        delete c.metadata, a.push(c);
      }
      return a;
    }
    if (e) {
      let r = s(t3.textures), a = s(t3.images);
      r.length > 0 && (n.textures = r), a.length > 0 && (n.images = a);
    }
    return n;
  }
  clone() {
    return new this.constructor().copy(this);
  }
  copy(t3) {
    this.name = t3.name, this.blending = t3.blending, this.side = t3.side, this.vertexColors = t3.vertexColors, this.opacity = t3.opacity, this.transparent = t3.transparent, this.blendSrc = t3.blendSrc, this.blendDst = t3.blendDst, this.blendEquation = t3.blendEquation, this.blendSrcAlpha = t3.blendSrcAlpha, this.blendDstAlpha = t3.blendDstAlpha, this.blendEquationAlpha = t3.blendEquationAlpha, this.blendColor.copy(t3.blendColor), this.blendAlpha = t3.blendAlpha, this.depthFunc = t3.depthFunc, this.depthTest = t3.depthTest, this.depthWrite = t3.depthWrite, this.stencilWriteMask = t3.stencilWriteMask, this.stencilFunc = t3.stencilFunc, this.stencilRef = t3.stencilRef, this.stencilFuncMask = t3.stencilFuncMask, this.stencilFail = t3.stencilFail, this.stencilZFail = t3.stencilZFail, this.stencilZPass = t3.stencilZPass, this.stencilWrite = t3.stencilWrite;
    let e = t3.clippingPlanes, n = null;
    if (e !== null) {
      let s = e.length;
      n = new Array(s);
      for (let r = 0; r !== s; ++r) n[r] = e[r].clone();
    }
    return this.clippingPlanes = n, this.clipIntersection = t3.clipIntersection, this.clipShadows = t3.clipShadows, this.shadowSide = t3.shadowSide, this.colorWrite = t3.colorWrite, this.precision = t3.precision, this.polygonOffset = t3.polygonOffset, this.polygonOffsetFactor = t3.polygonOffsetFactor, this.polygonOffsetUnits = t3.polygonOffsetUnits, this.dithering = t3.dithering, this.alphaTest = t3.alphaTest, this.alphaHash = t3.alphaHash, this.alphaToCoverage = t3.alphaToCoverage, this.premultipliedAlpha = t3.premultipliedAlpha, this.forceSinglePass = t3.forceSinglePass, this.visible = t3.visible, this.toneMapped = t3.toneMapped, this.userData = JSON.parse(JSON.stringify(t3.userData)), this;
  }
  dispose() {
    this.dispatchEvent({ type: "dispose" });
  }
  set needsUpdate(t3) {
    t3 === true && this.version++;
  }
};
var Fi = class extends bn {
  constructor(t3) {
    super(), this.isMeshBasicMaterial = true, this.type = "MeshBasicMaterial", this.color = new Vt(16777215), this.map = null, this.lightMap = null, this.lightMapIntensity = 1, this.aoMap = null, this.aoMapIntensity = 1, this.specularMap = null, this.alphaMap = null, this.envMap = null, this.envMapRotation = new He(), this.combine = Ia, this.reflectivity = 1, this.refractionRatio = 0.98, this.wireframe = false, this.wireframeLinewidth = 1, this.wireframeLinecap = "round", this.wireframeLinejoin = "round", this.fog = true, this.setValues(t3);
  }
  copy(t3) {
    return super.copy(t3), this.color.copy(t3.color), this.map = t3.map, this.lightMap = t3.lightMap, this.lightMapIntensity = t3.lightMapIntensity, this.aoMap = t3.aoMap, this.aoMapIntensity = t3.aoMapIntensity, this.specularMap = t3.specularMap, this.alphaMap = t3.alphaMap, this.envMap = t3.envMap, this.envMapRotation.copy(t3.envMapRotation), this.combine = t3.combine, this.reflectivity = t3.reflectivity, this.refractionRatio = t3.refractionRatio, this.wireframe = t3.wireframe, this.wireframeLinewidth = t3.wireframeLinewidth, this.wireframeLinecap = t3.wireframeLinecap, this.wireframeLinejoin = t3.wireframeLinejoin, this.fog = t3.fog, this;
  }
};
var le = new F();
var hs = new Gt();
var yc = 0;
var Ce = class {
  constructor(t3, e, n = false) {
    if (Array.isArray(t3)) throw new TypeError("THREE.BufferAttribute: array should be a Typed Array.");
    this.isBufferAttribute = true, Object.defineProperty(this, "id", { value: yc++ }), this.name = "", this.array = t3, this.itemSize = e, this.count = t3 !== void 0 ? t3.length / e : 0, this.normalized = n, this.usage = ya, this.updateRanges = [], this.gpuType = Ke, this.version = 0;
  }
  onUploadCallback() {
  }
  set needsUpdate(t3) {
    t3 === true && this.version++;
  }
  setUsage(t3) {
    return this.usage = t3, this;
  }
  addUpdateRange(t3, e) {
    this.updateRanges.push({ start: t3, count: e });
  }
  clearUpdateRanges() {
    this.updateRanges.length = 0;
  }
  copy(t3) {
    return this.name = t3.name, this.array = new t3.array.constructor(t3.array), this.itemSize = t3.itemSize, this.count = t3.count, this.normalized = t3.normalized, this.usage = t3.usage, this.gpuType = t3.gpuType, this;
  }
  copyAt(t3, e, n) {
    t3 *= this.itemSize, n *= e.itemSize;
    for (let s = 0, r = this.itemSize; s < r; s++) this.array[t3 + s] = e.array[n + s];
    return this;
  }
  copyArray(t3) {
    return this.array.set(t3), this;
  }
  applyMatrix3(t3) {
    if (this.itemSize === 2) for (let e = 0, n = this.count; e < n; e++) hs.fromBufferAttribute(this, e), hs.applyMatrix3(t3), this.setXY(e, hs.x, hs.y);
    else if (this.itemSize === 3) for (let e = 0, n = this.count; e < n; e++) le.fromBufferAttribute(this, e), le.applyMatrix3(t3), this.setXYZ(e, le.x, le.y, le.z);
    return this;
  }
  applyMatrix4(t3) {
    for (let e = 0, n = this.count; e < n; e++) le.fromBufferAttribute(this, e), le.applyMatrix4(t3), this.setXYZ(e, le.x, le.y, le.z);
    return this;
  }
  applyNormalMatrix(t3) {
    for (let e = 0, n = this.count; e < n; e++) le.fromBufferAttribute(this, e), le.applyNormalMatrix(t3), this.setXYZ(e, le.x, le.y, le.z);
    return this;
  }
  transformDirection(t3) {
    for (let e = 0, n = this.count; e < n; e++) le.fromBufferAttribute(this, e), le.transformDirection(t3), this.setXYZ(e, le.x, le.y, le.z);
    return this;
  }
  set(t3, e = 0) {
    return this.array.set(t3, e), this;
  }
  getComponent(t3, e) {
    let n = this.array[t3 * this.itemSize + e];
    return this.normalized && (n = Ti(n, this.array)), n;
  }
  setComponent(t3, e, n) {
    return this.normalized && (n = Me(n, this.array)), this.array[t3 * this.itemSize + e] = n, this;
  }
  getX(t3) {
    let e = this.array[t3 * this.itemSize];
    return this.normalized && (e = Ti(e, this.array)), e;
  }
  setX(t3, e) {
    return this.normalized && (e = Me(e, this.array)), this.array[t3 * this.itemSize] = e, this;
  }
  getY(t3) {
    let e = this.array[t3 * this.itemSize + 1];
    return this.normalized && (e = Ti(e, this.array)), e;
  }
  setY(t3, e) {
    return this.normalized && (e = Me(e, this.array)), this.array[t3 * this.itemSize + 1] = e, this;
  }
  getZ(t3) {
    let e = this.array[t3 * this.itemSize + 2];
    return this.normalized && (e = Ti(e, this.array)), e;
  }
  setZ(t3, e) {
    return this.normalized && (e = Me(e, this.array)), this.array[t3 * this.itemSize + 2] = e, this;
  }
  getW(t3) {
    let e = this.array[t3 * this.itemSize + 3];
    return this.normalized && (e = Ti(e, this.array)), e;
  }
  setW(t3, e) {
    return this.normalized && (e = Me(e, this.array)), this.array[t3 * this.itemSize + 3] = e, this;
  }
  setXY(t3, e, n) {
    return t3 *= this.itemSize, this.normalized && (e = Me(e, this.array), n = Me(n, this.array)), this.array[t3 + 0] = e, this.array[t3 + 1] = n, this;
  }
  setXYZ(t3, e, n, s) {
    return t3 *= this.itemSize, this.normalized && (e = Me(e, this.array), n = Me(n, this.array), s = Me(s, this.array)), this.array[t3 + 0] = e, this.array[t3 + 1] = n, this.array[t3 + 2] = s, this;
  }
  setXYZW(t3, e, n, s, r) {
    return t3 *= this.itemSize, this.normalized && (e = Me(e, this.array), n = Me(n, this.array), s = Me(s, this.array), r = Me(r, this.array)), this.array[t3 + 0] = e, this.array[t3 + 1] = n, this.array[t3 + 2] = s, this.array[t3 + 3] = r, this;
  }
  onUpload(t3) {
    return this.onUploadCallback = t3, this;
  }
  clone() {
    return new this.constructor(this.array, this.itemSize).copy(this);
  }
  toJSON() {
    let t3 = { itemSize: this.itemSize, type: this.array.constructor.name, array: Array.from(this.array), normalized: this.normalized };
    return this.name !== "" && (t3.name = this.name), this.usage !== ya && (t3.usage = this.usage), t3;
  }
};
var Oi = class extends Ce {
  constructor(t3, e, n) {
    super(new Uint16Array(t3), e, n);
  }
};
var Bi = class extends Ce {
  constructor(t3, e, n) {
    super(new Uint32Array(t3), e, n);
  }
};
var Ye = class extends Ce {
  constructor(t3, e, n) {
    super(new Float32Array(t3), e, n);
  }
};
var Mc = 0;
var Ue = new oe();
var da = new xe();
var ri = new F();
var Ae = new Sn();
var Ri = new Sn();
var de = new F();
var En = class i10 extends ln {
  constructor() {
    super(), this.isBufferGeometry = true, Object.defineProperty(this, "id", { value: Mc++ }), this.uuid = Qi(), this.name = "", this.type = "BufferGeometry", this.index = null, this.indirect = null, this.attributes = {}, this.morphAttributes = {}, this.morphTargetsRelative = false, this.groups = [], this.boundingBox = null, this.boundingSphere = null, this.drawRange = { start: 0, count: 1 / 0 }, this.userData = {};
  }
  getIndex() {
    return this.index;
  }
  setIndex(t3) {
    return Array.isArray(t3) ? this.index = new (Ga(t3) ? Bi : Oi)(t3, 1) : this.index = t3, this;
  }
  setIndirect(t3) {
    return this.indirect = t3, this;
  }
  getIndirect() {
    return this.indirect;
  }
  getAttribute(t3) {
    return this.attributes[t3];
  }
  setAttribute(t3, e) {
    return this.attributes[t3] = e, this;
  }
  deleteAttribute(t3) {
    return delete this.attributes[t3], this;
  }
  hasAttribute(t3) {
    return this.attributes[t3] !== void 0;
  }
  addGroup(t3, e, n = 0) {
    this.groups.push({ start: t3, count: e, materialIndex: n });
  }
  clearGroups() {
    this.groups = [];
  }
  setDrawRange(t3, e) {
    this.drawRange.start = t3, this.drawRange.count = e;
  }
  applyMatrix4(t3) {
    let e = this.attributes.position;
    e !== void 0 && (e.applyMatrix4(t3), e.needsUpdate = true);
    let n = this.attributes.normal;
    if (n !== void 0) {
      let r = new Lt().getNormalMatrix(t3);
      n.applyNormalMatrix(r), n.needsUpdate = true;
    }
    let s = this.attributes.tangent;
    return s !== void 0 && (s.transformDirection(t3), s.needsUpdate = true), this.boundingBox !== null && this.computeBoundingBox(), this.boundingSphere !== null && this.computeBoundingSphere(), this;
  }
  applyQuaternion(t3) {
    return Ue.makeRotationFromQuaternion(t3), this.applyMatrix4(Ue), this;
  }
  rotateX(t3) {
    return Ue.makeRotationX(t3), this.applyMatrix4(Ue), this;
  }
  rotateY(t3) {
    return Ue.makeRotationY(t3), this.applyMatrix4(Ue), this;
  }
  rotateZ(t3) {
    return Ue.makeRotationZ(t3), this.applyMatrix4(Ue), this;
  }
  translate(t3, e, n) {
    return Ue.makeTranslation(t3, e, n), this.applyMatrix4(Ue), this;
  }
  scale(t3, e, n) {
    return Ue.makeScale(t3, e, n), this.applyMatrix4(Ue), this;
  }
  lookAt(t3) {
    return da.lookAt(t3), da.updateMatrix(), this.applyMatrix4(da.matrix), this;
  }
  center() {
    return this.computeBoundingBox(), this.boundingBox.getCenter(ri).negate(), this.translate(ri.x, ri.y, ri.z), this;
  }
  setFromPoints(t3) {
    let e = this.getAttribute("position");
    if (e === void 0) {
      let n = [];
      for (let s = 0, r = t3.length; s < r; s++) {
        let a = t3[s];
        n.push(a.x, a.y, a.z || 0);
      }
      this.setAttribute("position", new Ye(n, 3));
    } else {
      let n = Math.min(t3.length, e.count);
      for (let s = 0; s < n; s++) {
        let r = t3[s];
        e.setXYZ(s, r.x, r.y, r.z || 0);
      }
      t3.length > e.count && console.warn("THREE.BufferGeometry: Buffer size too small for points data. Use .dispose() and create a new geometry."), e.needsUpdate = true;
    }
    return this;
  }
  computeBoundingBox() {
    this.boundingBox === null && (this.boundingBox = new Sn());
    let t3 = this.attributes.position, e = this.morphAttributes.position;
    if (t3 && t3.isGLBufferAttribute) {
      console.error("THREE.BufferGeometry.computeBoundingBox(): GLBufferAttribute requires a manual bounding box.", this), this.boundingBox.set(new F(-1 / 0, -1 / 0, -1 / 0), new F(1 / 0, 1 / 0, 1 / 0));
      return;
    }
    if (t3 !== void 0) {
      if (this.boundingBox.setFromBufferAttribute(t3), e) for (let n = 0, s = e.length; n < s; n++) {
        let r = e[n];
        Ae.setFromBufferAttribute(r), this.morphTargetsRelative ? (de.addVectors(this.boundingBox.min, Ae.min), this.boundingBox.expandByPoint(de), de.addVectors(this.boundingBox.max, Ae.max), this.boundingBox.expandByPoint(de)) : (this.boundingBox.expandByPoint(Ae.min), this.boundingBox.expandByPoint(Ae.max));
      }
    } else this.boundingBox.makeEmpty();
    (isNaN(this.boundingBox.min.x) || isNaN(this.boundingBox.min.y) || isNaN(this.boundingBox.min.z)) && console.error('THREE.BufferGeometry.computeBoundingBox(): Computed min/max have NaN values. The "position" attribute is likely to have NaN values.', this);
  }
  computeBoundingSphere() {
    this.boundingSphere === null && (this.boundingSphere = new di());
    let t3 = this.attributes.position, e = this.morphAttributes.position;
    if (t3 && t3.isGLBufferAttribute) {
      console.error("THREE.BufferGeometry.computeBoundingSphere(): GLBufferAttribute requires a manual bounding sphere.", this), this.boundingSphere.set(new F(), 1 / 0);
      return;
    }
    if (t3) {
      let n = this.boundingSphere.center;
      if (Ae.setFromBufferAttribute(t3), e) for (let r = 0, a = e.length; r < a; r++) {
        let o = e[r];
        Ri.setFromBufferAttribute(o), this.morphTargetsRelative ? (de.addVectors(Ae.min, Ri.min), Ae.expandByPoint(de), de.addVectors(Ae.max, Ri.max), Ae.expandByPoint(de)) : (Ae.expandByPoint(Ri.min), Ae.expandByPoint(Ri.max));
      }
      Ae.getCenter(n);
      let s = 0;
      for (let r = 0, a = t3.count; r < a; r++) de.fromBufferAttribute(t3, r), s = Math.max(s, n.distanceToSquared(de));
      if (e) for (let r = 0, a = e.length; r < a; r++) {
        let o = e[r], c = this.morphTargetsRelative;
        for (let l = 0, u = o.count; l < u; l++) de.fromBufferAttribute(o, l), c && (ri.fromBufferAttribute(t3, l), de.add(ri)), s = Math.max(s, n.distanceToSquared(de));
      }
      this.boundingSphere.radius = Math.sqrt(s), isNaN(this.boundingSphere.radius) && console.error('THREE.BufferGeometry.computeBoundingSphere(): Computed radius is NaN. The "position" attribute is likely to have NaN values.', this);
    }
  }
  computeTangents() {
    let t3 = this.index, e = this.attributes;
    if (t3 === null || e.position === void 0 || e.normal === void 0 || e.uv === void 0) {
      console.error("THREE.BufferGeometry: .computeTangents() failed. Missing required attributes (index, position, normal or uv)");
      return;
    }
    let n = e.position, s = e.normal, r = e.uv;
    this.hasAttribute("tangent") === false && this.setAttribute("tangent", new Ce(new Float32Array(4 * n.count), 4));
    let a = this.getAttribute("tangent"), o = [], c = [];
    for (let N = 0; N < n.count; N++) o[N] = new F(), c[N] = new F();
    let l = new F(), u = new F(), d = new F(), f = new Gt(), m = new Gt(), x = new Gt(), v = new F(), p = new F();
    function h(N, M, y) {
      l.fromBufferAttribute(n, N), u.fromBufferAttribute(n, M), d.fromBufferAttribute(n, y), f.fromBufferAttribute(r, N), m.fromBufferAttribute(r, M), x.fromBufferAttribute(r, y), u.sub(l), d.sub(l), m.sub(f), x.sub(f);
      let I = 1 / (m.x * x.y - x.x * m.y);
      isFinite(I) && (v.copy(u).multiplyScalar(x.y).addScaledVector(d, -m.y).multiplyScalar(I), p.copy(d).multiplyScalar(m.x).addScaledVector(u, -x.x).multiplyScalar(I), o[N].add(v), o[M].add(v), o[y].add(v), c[N].add(p), c[M].add(p), c[y].add(p));
    }
    let A = this.groups;
    A.length === 0 && (A = [{ start: 0, count: t3.count }]);
    for (let N = 0, M = A.length; N < M; ++N) {
      let y = A[N], I = y.start, z = y.count;
      for (let H = I, X = I + z; H < X; H += 3) h(t3.getX(H + 0), t3.getX(H + 1), t3.getX(H + 2));
    }
    let T = new F(), b = new F(), R = new F(), w = new F();
    function P(N) {
      R.fromBufferAttribute(s, N), w.copy(R);
      let M = o[N];
      T.copy(M), T.sub(R.multiplyScalar(R.dot(M))).normalize(), b.crossVectors(w, M);
      let I = b.dot(c[N]) < 0 ? -1 : 1;
      a.setXYZW(N, T.x, T.y, T.z, I);
    }
    for (let N = 0, M = A.length; N < M; ++N) {
      let y = A[N], I = y.start, z = y.count;
      for (let H = I, X = I + z; H < X; H += 3) P(t3.getX(H + 0)), P(t3.getX(H + 1)), P(t3.getX(H + 2));
    }
  }
  computeVertexNormals() {
    let t3 = this.index, e = this.getAttribute("position");
    if (e !== void 0) {
      let n = this.getAttribute("normal");
      if (n === void 0) n = new Ce(new Float32Array(e.count * 3), 3), this.setAttribute("normal", n);
      else for (let f = 0, m = n.count; f < m; f++) n.setXYZ(f, 0, 0, 0);
      let s = new F(), r = new F(), a = new F(), o = new F(), c = new F(), l = new F(), u = new F(), d = new F();
      if (t3) for (let f = 0, m = t3.count; f < m; f += 3) {
        let x = t3.getX(f + 0), v = t3.getX(f + 1), p = t3.getX(f + 2);
        s.fromBufferAttribute(e, x), r.fromBufferAttribute(e, v), a.fromBufferAttribute(e, p), u.subVectors(a, r), d.subVectors(s, r), u.cross(d), o.fromBufferAttribute(n, x), c.fromBufferAttribute(n, v), l.fromBufferAttribute(n, p), o.add(u), c.add(u), l.add(u), n.setXYZ(x, o.x, o.y, o.z), n.setXYZ(v, c.x, c.y, c.z), n.setXYZ(p, l.x, l.y, l.z);
      }
      else for (let f = 0, m = e.count; f < m; f += 3) s.fromBufferAttribute(e, f + 0), r.fromBufferAttribute(e, f + 1), a.fromBufferAttribute(e, f + 2), u.subVectors(a, r), d.subVectors(s, r), u.cross(d), n.setXYZ(f + 0, u.x, u.y, u.z), n.setXYZ(f + 1, u.x, u.y, u.z), n.setXYZ(f + 2, u.x, u.y, u.z);
      this.normalizeNormals(), n.needsUpdate = true;
    }
  }
  normalizeNormals() {
    let t3 = this.attributes.normal;
    for (let e = 0, n = t3.count; e < n; e++) de.fromBufferAttribute(t3, e), de.normalize(), t3.setXYZ(e, de.x, de.y, de.z);
  }
  toNonIndexed() {
    function t3(o, c) {
      let l = o.array, u = o.itemSize, d = o.normalized, f = new l.constructor(c.length * u), m = 0, x = 0;
      for (let v = 0, p = c.length; v < p; v++) {
        o.isInterleavedBufferAttribute ? m = c[v] * o.data.stride + o.offset : m = c[v] * u;
        for (let h = 0; h < u; h++) f[x++] = l[m++];
      }
      return new Ce(f, u, d);
    }
    if (this.index === null) return console.warn("THREE.BufferGeometry.toNonIndexed(): BufferGeometry is already non-indexed."), this;
    let e = new i10(), n = this.index.array, s = this.attributes;
    for (let o in s) {
      let c = s[o], l = t3(c, n);
      e.setAttribute(o, l);
    }
    let r = this.morphAttributes;
    for (let o in r) {
      let c = [], l = r[o];
      for (let u = 0, d = l.length; u < d; u++) {
        let f = l[u], m = t3(f, n);
        c.push(m);
      }
      e.morphAttributes[o] = c;
    }
    e.morphTargetsRelative = this.morphTargetsRelative;
    let a = this.groups;
    for (let o = 0, c = a.length; o < c; o++) {
      let l = a[o];
      e.addGroup(l.start, l.count, l.materialIndex);
    }
    return e;
  }
  toJSON() {
    let t3 = { metadata: { version: 4.7, type: "BufferGeometry", generator: "BufferGeometry.toJSON" } };
    if (t3.uuid = this.uuid, t3.type = this.type, this.name !== "" && (t3.name = this.name), Object.keys(this.userData).length > 0 && (t3.userData = this.userData), this.parameters !== void 0) {
      let c = this.parameters;
      for (let l in c) c[l] !== void 0 && (t3[l] = c[l]);
      return t3;
    }
    t3.data = { attributes: {} };
    let e = this.index;
    e !== null && (t3.data.index = { type: e.array.constructor.name, array: Array.prototype.slice.call(e.array) });
    let n = this.attributes;
    for (let c in n) {
      let l = n[c];
      t3.data.attributes[c] = l.toJSON(t3.data);
    }
    let s = {}, r = false;
    for (let c in this.morphAttributes) {
      let l = this.morphAttributes[c], u = [];
      for (let d = 0, f = l.length; d < f; d++) {
        let m = l[d];
        u.push(m.toJSON(t3.data));
      }
      u.length > 0 && (s[c] = u, r = true);
    }
    r && (t3.data.morphAttributes = s, t3.data.morphTargetsRelative = this.morphTargetsRelative);
    let a = this.groups;
    a.length > 0 && (t3.data.groups = JSON.parse(JSON.stringify(a)));
    let o = this.boundingSphere;
    return o !== null && (t3.data.boundingSphere = o.toJSON()), t3;
  }
  clone() {
    return new this.constructor().copy(this);
  }
  copy(t3) {
    this.index = null, this.attributes = {}, this.morphAttributes = {}, this.groups = [], this.boundingBox = null, this.boundingSphere = null;
    let e = {};
    this.name = t3.name;
    let n = t3.index;
    n !== null && this.setIndex(n.clone());
    let s = t3.attributes;
    for (let l in s) {
      let u = s[l];
      this.setAttribute(l, u.clone(e));
    }
    let r = t3.morphAttributes;
    for (let l in r) {
      let u = [], d = r[l];
      for (let f = 0, m = d.length; f < m; f++) u.push(d[f].clone(e));
      this.morphAttributes[l] = u;
    }
    this.morphTargetsRelative = t3.morphTargetsRelative;
    let a = t3.groups;
    for (let l = 0, u = a.length; l < u; l++) {
      let d = a[l];
      this.addGroup(d.start, d.count, d.materialIndex);
    }
    let o = t3.boundingBox;
    o !== null && (this.boundingBox = o.clone());
    let c = t3.boundingSphere;
    return c !== null && (this.boundingSphere = c.clone()), this.drawRange.start = t3.drawRange.start, this.drawRange.count = t3.drawRange.count, this.userData = t3.userData, this;
  }
  dispose() {
    this.dispatchEvent({ type: "dispose" });
  }
};
var Ro = new oe();
var Dn = new Is();
var us = new di();
var Io = new F();
var ds = new F();
var fs = new F();
var ps = new F();
var fa = new F();
var ms = new F();
var Po = new F();
var gs = new F();
var Ie = class extends xe {
  constructor(t3 = new En(), e = new Fi()) {
    super(), this.isMesh = true, this.type = "Mesh", this.geometry = t3, this.material = e, this.morphTargetDictionary = void 0, this.morphTargetInfluences = void 0, this.count = 1, this.updateMorphTargets();
  }
  copy(t3, e) {
    return super.copy(t3, e), t3.morphTargetInfluences !== void 0 && (this.morphTargetInfluences = t3.morphTargetInfluences.slice()), t3.morphTargetDictionary !== void 0 && (this.morphTargetDictionary = Object.assign({}, t3.morphTargetDictionary)), this.material = Array.isArray(t3.material) ? t3.material.slice() : t3.material, this.geometry = t3.geometry, this;
  }
  updateMorphTargets() {
    let e = this.geometry.morphAttributes, n = Object.keys(e);
    if (n.length > 0) {
      let s = e[n[0]];
      if (s !== void 0) {
        this.morphTargetInfluences = [], this.morphTargetDictionary = {};
        for (let r = 0, a = s.length; r < a; r++) {
          let o = s[r].name || String(r);
          this.morphTargetInfluences.push(0), this.morphTargetDictionary[o] = r;
        }
      }
    }
  }
  getVertexPosition(t3, e) {
    let n = this.geometry, s = n.attributes.position, r = n.morphAttributes.position, a = n.morphTargetsRelative;
    e.fromBufferAttribute(s, t3);
    let o = this.morphTargetInfluences;
    if (r && o) {
      ms.set(0, 0, 0);
      for (let c = 0, l = r.length; c < l; c++) {
        let u = o[c], d = r[c];
        u !== 0 && (fa.fromBufferAttribute(d, t3), a ? ms.addScaledVector(fa, u) : ms.addScaledVector(fa.sub(e), u));
      }
      e.add(ms);
    }
    return e;
  }
  raycast(t3, e) {
    let n = this.geometry, s = this.material, r = this.matrixWorld;
    s !== void 0 && (n.boundingSphere === null && n.computeBoundingSphere(), us.copy(n.boundingSphere), us.applyMatrix4(r), Dn.copy(t3.ray).recast(t3.near), !(us.containsPoint(Dn.origin) === false && (Dn.intersectSphere(us, Io) === null || Dn.origin.distanceToSquared(Io) > (t3.far - t3.near) ** 2)) && (Ro.copy(r).invert(), Dn.copy(t3.ray).applyMatrix4(Ro), !(n.boundingBox !== null && Dn.intersectsBox(n.boundingBox) === false) && this._computeIntersections(t3, e, Dn)));
  }
  _computeIntersections(t3, e, n) {
    let s, r = this.geometry, a = this.material, o = r.index, c = r.attributes.position, l = r.attributes.uv, u = r.attributes.uv1, d = r.attributes.normal, f = r.groups, m = r.drawRange;
    if (o !== null) if (Array.isArray(a)) for (let x = 0, v = f.length; x < v; x++) {
      let p = f[x], h = a[p.materialIndex], A = Math.max(p.start, m.start), T = Math.min(o.count, Math.min(p.start + p.count, m.start + m.count));
      for (let b = A, R = T; b < R; b += 3) {
        let w = o.getX(b), P = o.getX(b + 1), N = o.getX(b + 2);
        s = _s(this, h, t3, n, l, u, d, w, P, N), s && (s.faceIndex = Math.floor(b / 3), s.face.materialIndex = p.materialIndex, e.push(s));
      }
    }
    else {
      let x = Math.max(0, m.start), v = Math.min(o.count, m.start + m.count);
      for (let p = x, h = v; p < h; p += 3) {
        let A = o.getX(p), T = o.getX(p + 1), b = o.getX(p + 2);
        s = _s(this, a, t3, n, l, u, d, A, T, b), s && (s.faceIndex = Math.floor(p / 3), e.push(s));
      }
    }
    else if (c !== void 0) if (Array.isArray(a)) for (let x = 0, v = f.length; x < v; x++) {
      let p = f[x], h = a[p.materialIndex], A = Math.max(p.start, m.start), T = Math.min(c.count, Math.min(p.start + p.count, m.start + m.count));
      for (let b = A, R = T; b < R; b += 3) {
        let w = b, P = b + 1, N = b + 2;
        s = _s(this, h, t3, n, l, u, d, w, P, N), s && (s.faceIndex = Math.floor(b / 3), s.face.materialIndex = p.materialIndex, e.push(s));
      }
    }
    else {
      let x = Math.max(0, m.start), v = Math.min(c.count, m.start + m.count);
      for (let p = x, h = v; p < h; p += 3) {
        let A = p, T = p + 1, b = p + 2;
        s = _s(this, a, t3, n, l, u, d, A, T, b), s && (s.faceIndex = Math.floor(p / 3), e.push(s));
      }
    }
  }
};
function Sc(i14, t3, e, n, s, r, a, o) {
  let c;
  if (t3.side === ve ? c = n.intersectTriangle(a, r, s, true, o) : c = n.intersectTriangle(s, r, a, t3.side === on, o), c === null) return null;
  gs.copy(o), gs.applyMatrix4(i14.matrixWorld);
  let l = e.ray.origin.distanceTo(gs);
  return l < e.near || l > e.far ? null : { distance: l, point: gs.clone(), object: i14 };
}
function _s(i14, t3, e, n, s, r, a, o, c, l) {
  i14.getVertexPosition(o, ds), i14.getVertexPosition(c, fs), i14.getVertexPosition(l, ps);
  let u = Sc(i14, t3, e, n, ds, fs, ps, Po);
  if (u) {
    let d = new F();
    vn.getBarycoord(Po, ds, fs, ps, d), s && (u.uv = vn.getInterpolatedAttribute(s, o, c, l, d, new Gt())), r && (u.uv1 = vn.getInterpolatedAttribute(r, o, c, l, d, new Gt())), a && (u.normal = vn.getInterpolatedAttribute(a, o, c, l, d, new F()), u.normal.dot(n.direction) > 0 && u.normal.multiplyScalar(-1));
    let f = { a: o, b: c, c: l, normal: new F(), materialIndex: 0 };
    vn.getNormal(ds, fs, ps, f.normal), u.face = f, u.barycoord = d;
  }
  return u;
}
var Vn = class i11 extends En {
  constructor(t3 = 1, e = 1, n = 1, s = 1, r = 1, a = 1) {
    super(), this.type = "BoxGeometry", this.parameters = { width: t3, height: e, depth: n, widthSegments: s, heightSegments: r, depthSegments: a };
    let o = this;
    s = Math.floor(s), r = Math.floor(r), a = Math.floor(a);
    let c = [], l = [], u = [], d = [], f = 0, m = 0;
    x("z", "y", "x", -1, -1, n, e, t3, a, r, 0), x("z", "y", "x", 1, -1, n, e, -t3, a, r, 1), x("x", "z", "y", 1, 1, t3, n, e, s, a, 2), x("x", "z", "y", 1, -1, t3, n, -e, s, a, 3), x("x", "y", "z", 1, -1, t3, e, n, s, r, 4), x("x", "y", "z", -1, -1, t3, e, -n, s, r, 5), this.setIndex(c), this.setAttribute("position", new Ye(l, 3)), this.setAttribute("normal", new Ye(u, 3)), this.setAttribute("uv", new Ye(d, 2));
    function x(v, p, h, A, T, b, R, w, P, N, M) {
      let y = b / P, I = R / N, z = b / 2, H = R / 2, X = w / 2, Z = P + 1, W = N + 1, et = 0, V = 0, rt = new F();
      for (let ct = 0; ct < W; ct++) {
        let St = ct * I - H;
        for (let Ft = 0; Ft < Z; Ft++) {
          let Jt = Ft * y - z;
          rt[v] = Jt * A, rt[p] = St * T, rt[h] = X, l.push(rt.x, rt.y, rt.z), rt[v] = 0, rt[p] = 0, rt[h] = w > 0 ? 1 : -1, u.push(rt.x, rt.y, rt.z), d.push(Ft / P), d.push(1 - ct / N), et += 1;
        }
      }
      for (let ct = 0; ct < N; ct++) for (let St = 0; St < P; St++) {
        let Ft = f + St + Z * ct, Jt = f + St + Z * (ct + 1), jt = f + (St + 1) + Z * (ct + 1), Wt = f + (St + 1) + Z * ct;
        c.push(Ft, Jt, Wt), c.push(Jt, jt, Wt), V += 6;
      }
      o.addGroup(m, V, M), m += V, f += et;
    }
  }
  copy(t3) {
    return super.copy(t3), this.parameters = Object.assign({}, t3.parameters), this;
  }
  static fromJSON(t3) {
    return new i11(t3.width, t3.height, t3.depth, t3.widthSegments, t3.heightSegments, t3.depthSegments);
  }
};
function Wn(i14) {
  let t3 = {};
  for (let e in i14) {
    t3[e] = {};
    for (let n in i14[e]) {
      let s = i14[e][n];
      s && (s.isColor || s.isMatrix3 || s.isMatrix4 || s.isVector2 || s.isVector3 || s.isVector4 || s.isTexture || s.isQuaternion) ? s.isRenderTargetTexture ? (console.warn("UniformsUtils: Textures of render targets cannot be cloned via cloneUniforms() or mergeUniforms()."), t3[e][n] = null) : t3[e][n] = s.clone() : Array.isArray(s) ? t3[e][n] = s.slice() : t3[e][n] = s;
    }
  }
  return t3;
}
function ge(i14) {
  let t3 = {};
  for (let e = 0; e < i14.length; e++) {
    let n = Wn(i14[e]);
    for (let s in n) t3[s] = n[s];
  }
  return t3;
}
function bc(i14) {
  let t3 = [];
  for (let e = 0; e < i14.length; e++) t3.push(i14[e].clone());
  return t3;
}
function Wa(i14) {
  let t3 = i14.getRenderTarget();
  return t3 === null ? i14.outputColorSpace : t3.isXRRenderTarget === true ? t3.texture.colorSpace : kt.workingColorSpace;
}
var Al = { clone: Wn, merge: ge };
var Ec = `void main() {
	gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
}`;
var Tc = `void main() {
	gl_FragColor = vec4( 1.0, 0.0, 0.0, 1.0 );
}`;
var Ge = class extends bn {
  constructor(t3) {
    super(), this.isShaderMaterial = true, this.type = "ShaderMaterial", this.defines = {}, this.uniforms = {}, this.uniformsGroups = [], this.vertexShader = Ec, this.fragmentShader = Tc, this.linewidth = 1, this.wireframe = false, this.wireframeLinewidth = 1, this.fog = false, this.lights = false, this.clipping = false, this.forceSinglePass = true, this.extensions = { clipCullDistance: false, multiDraw: false }, this.defaultAttributeValues = { color: [1, 1, 1], uv: [0, 0], uv1: [0, 0] }, this.index0AttributeName = void 0, this.uniformsNeedUpdate = false, this.glslVersion = null, t3 !== void 0 && this.setValues(t3);
  }
  copy(t3) {
    return super.copy(t3), this.fragmentShader = t3.fragmentShader, this.vertexShader = t3.vertexShader, this.uniforms = Wn(t3.uniforms), this.uniformsGroups = bc(t3.uniformsGroups), this.defines = Object.assign({}, t3.defines), this.wireframe = t3.wireframe, this.wireframeLinewidth = t3.wireframeLinewidth, this.fog = t3.fog, this.lights = t3.lights, this.clipping = t3.clipping, this.extensions = Object.assign({}, t3.extensions), this.glslVersion = t3.glslVersion, this;
  }
  toJSON(t3) {
    let e = super.toJSON(t3);
    e.glslVersion = this.glslVersion, e.uniforms = {};
    for (let s in this.uniforms) {
      let a = this.uniforms[s].value;
      a && a.isTexture ? e.uniforms[s] = { type: "t", value: a.toJSON(t3).uuid } : a && a.isColor ? e.uniforms[s] = { type: "c", value: a.getHex() } : a && a.isVector2 ? e.uniforms[s] = { type: "v2", value: a.toArray() } : a && a.isVector3 ? e.uniforms[s] = { type: "v3", value: a.toArray() } : a && a.isVector4 ? e.uniforms[s] = { type: "v4", value: a.toArray() } : a && a.isMatrix3 ? e.uniforms[s] = { type: "m3", value: a.toArray() } : a && a.isMatrix4 ? e.uniforms[s] = { type: "m4", value: a.toArray() } : e.uniforms[s] = { value: a };
    }
    Object.keys(this.defines).length > 0 && (e.defines = this.defines), e.vertexShader = this.vertexShader, e.fragmentShader = this.fragmentShader, e.lights = this.lights, e.clipping = this.clipping;
    let n = {};
    for (let s in this.extensions) this.extensions[s] === true && (n[s] = true);
    return Object.keys(n).length > 0 && (e.extensions = n), e;
  }
};
var zi = class extends xe {
  constructor() {
    super(), this.isCamera = true, this.type = "Camera", this.matrixWorldInverse = new oe(), this.projectionMatrix = new oe(), this.projectionMatrixInverse = new oe(), this.coordinateSystem = Ve, this._reversedDepth = false;
  }
  get reversedDepth() {
    return this._reversedDepth;
  }
  copy(t3, e) {
    return super.copy(t3, e), this.matrixWorldInverse.copy(t3.matrixWorldInverse), this.projectionMatrix.copy(t3.projectionMatrix), this.projectionMatrixInverse.copy(t3.projectionMatrixInverse), this.coordinateSystem = t3.coordinateSystem, this;
  }
  getWorldDirection(t3) {
    return super.getWorldDirection(t3).negate();
  }
  updateMatrixWorld(t3) {
    super.updateMatrixWorld(t3), this.matrixWorldInverse.copy(this.matrixWorld).invert();
  }
  updateWorldMatrix(t3, e) {
    super.updateWorldMatrix(t3, e), this.matrixWorldInverse.copy(this.matrixWorld).invert();
  }
  clone() {
    return new this.constructor().copy(this);
  }
};
var xn = new F();
var Lo = new Gt();
var Do = new Gt();
var Se = class extends zi {
  constructor(t3 = 50, e = 1, n = 0.1, s = 2e3) {
    super(), this.isPerspectiveCamera = true, this.type = "PerspectiveCamera", this.fov = t3, this.zoom = 1, this.near = n, this.far = s, this.focus = 10, this.aspect = e, this.view = null, this.filmGauge = 35, this.filmOffset = 0, this.updateProjectionMatrix();
  }
  copy(t3, e) {
    return super.copy(t3, e), this.fov = t3.fov, this.zoom = t3.zoom, this.near = t3.near, this.far = t3.far, this.focus = t3.focus, this.aspect = t3.aspect, this.view = t3.view === null ? null : Object.assign({}, t3.view), this.filmGauge = t3.filmGauge, this.filmOffset = t3.filmOffset, this;
  }
  setFocalLength(t3) {
    let e = 0.5 * this.getFilmHeight() / t3;
    this.fov = As * 2 * Math.atan(e), this.updateProjectionMatrix();
  }
  getFocalLength() {
    let t3 = Math.tan(qr * 0.5 * this.fov);
    return 0.5 * this.getFilmHeight() / t3;
  }
  getEffectiveFOV() {
    return As * 2 * Math.atan(Math.tan(qr * 0.5 * this.fov) / this.zoom);
  }
  getFilmWidth() {
    return this.filmGauge * Math.min(this.aspect, 1);
  }
  getFilmHeight() {
    return this.filmGauge / Math.max(this.aspect, 1);
  }
  getViewBounds(t3, e, n) {
    xn.set(-1, -1, 0.5).applyMatrix4(this.projectionMatrixInverse), e.set(xn.x, xn.y).multiplyScalar(-t3 / xn.z), xn.set(1, 1, 0.5).applyMatrix4(this.projectionMatrixInverse), n.set(xn.x, xn.y).multiplyScalar(-t3 / xn.z);
  }
  getViewSize(t3, e) {
    return this.getViewBounds(t3, Lo, Do), e.subVectors(Do, Lo);
  }
  setViewOffset(t3, e, n, s, r, a) {
    this.aspect = t3 / e, this.view === null && (this.view = { enabled: true, fullWidth: 1, fullHeight: 1, offsetX: 0, offsetY: 0, width: 1, height: 1 }), this.view.enabled = true, this.view.fullWidth = t3, this.view.fullHeight = e, this.view.offsetX = n, this.view.offsetY = s, this.view.width = r, this.view.height = a, this.updateProjectionMatrix();
  }
  clearViewOffset() {
    this.view !== null && (this.view.enabled = false), this.updateProjectionMatrix();
  }
  updateProjectionMatrix() {
    let t3 = this.near, e = t3 * Math.tan(qr * 0.5 * this.fov) / this.zoom, n = 2 * e, s = this.aspect * n, r = -0.5 * s, a = this.view;
    if (this.view !== null && this.view.enabled) {
      let c = a.fullWidth, l = a.fullHeight;
      r += a.offsetX * s / c, e -= a.offsetY * n / l, s *= a.width / c, n *= a.height / l;
    }
    let o = this.filmOffset;
    o !== 0 && (r += t3 * o / this.getFilmWidth()), this.projectionMatrix.makePerspective(r, r + s, e, e - n, t3, this.far, this.coordinateSystem, this.reversedDepth), this.projectionMatrixInverse.copy(this.projectionMatrix).invert();
  }
  toJSON(t3) {
    let e = super.toJSON(t3);
    return e.object.fov = this.fov, e.object.zoom = this.zoom, e.object.near = this.near, e.object.far = this.far, e.object.focus = this.focus, e.object.aspect = this.aspect, this.view !== null && (e.object.view = Object.assign({}, this.view)), e.object.filmGauge = this.filmGauge, e.object.filmOffset = this.filmOffset, e;
  }
};
var ai = -90;
var oi = 1;
var Ps = class extends xe {
  constructor(t3, e, n) {
    super(), this.type = "CubeCamera", this.renderTarget = n, this.coordinateSystem = null, this.activeMipmapLevel = 0;
    let s = new Se(ai, oi, t3, e);
    s.layers = this.layers, this.add(s);
    let r = new Se(ai, oi, t3, e);
    r.layers = this.layers, this.add(r);
    let a = new Se(ai, oi, t3, e);
    a.layers = this.layers, this.add(a);
    let o = new Se(ai, oi, t3, e);
    o.layers = this.layers, this.add(o);
    let c = new Se(ai, oi, t3, e);
    c.layers = this.layers, this.add(c);
    let l = new Se(ai, oi, t3, e);
    l.layers = this.layers, this.add(l);
  }
  updateCoordinateSystem() {
    let t3 = this.coordinateSystem, e = this.children.concat(), [n, s, r, a, o, c] = e;
    for (let l of e) this.remove(l);
    if (t3 === Ve) n.up.set(0, 1, 0), n.lookAt(1, 0, 0), s.up.set(0, 1, 0), s.lookAt(-1, 0, 0), r.up.set(0, 0, -1), r.lookAt(0, 1, 0), a.up.set(0, 0, 1), a.lookAt(0, -1, 0), o.up.set(0, 1, 0), o.lookAt(0, 0, 1), c.up.set(0, 1, 0), c.lookAt(0, 0, -1);
    else if (t3 === Li) n.up.set(0, -1, 0), n.lookAt(-1, 0, 0), s.up.set(0, -1, 0), s.lookAt(1, 0, 0), r.up.set(0, 0, 1), r.lookAt(0, 1, 0), a.up.set(0, 0, -1), a.lookAt(0, -1, 0), o.up.set(0, -1, 0), o.lookAt(0, 0, 1), c.up.set(0, -1, 0), c.lookAt(0, 0, -1);
    else throw new Error("THREE.CubeCamera.updateCoordinateSystem(): Invalid coordinate system: " + t3);
    for (let l of e) this.add(l), l.updateMatrixWorld();
  }
  update(t3, e) {
    this.parent === null && this.updateMatrixWorld();
    let { renderTarget: n, activeMipmapLevel: s } = this;
    this.coordinateSystem !== t3.coordinateSystem && (this.coordinateSystem = t3.coordinateSystem, this.updateCoordinateSystem());
    let [r, a, o, c, l, u] = this.children, d = t3.getRenderTarget(), f = t3.getActiveCubeFace(), m = t3.getActiveMipmapLevel(), x = t3.xr.enabled;
    t3.xr.enabled = false;
    let v = n.texture.generateMipmaps;
    n.texture.generateMipmaps = false, t3.setRenderTarget(n, 0, s), t3.render(e, r), t3.setRenderTarget(n, 1, s), t3.render(e, a), t3.setRenderTarget(n, 2, s), t3.render(e, o), t3.setRenderTarget(n, 3, s), t3.render(e, c), t3.setRenderTarget(n, 4, s), t3.render(e, l), n.texture.generateMipmaps = v, t3.setRenderTarget(n, 5, s), t3.render(e, u), t3.setRenderTarget(d, f, m), t3.xr.enabled = x, n.texture.needsPMREMUpdate = true;
  }
};
var Vi = class extends Re {
  constructor(t3 = [], e = Hn, n, s, r, a, o, c, l, u) {
    super(t3, e, n, s, r, a, o, c, l, u), this.isCubeTexture = true, this.flipY = false;
  }
  get images() {
    return this.image;
  }
  set images(t3) {
    this.image = t3;
  }
};
var Ls = class extends Ze {
  constructor(t3 = 1, e = {}) {
    super(t3, t3, e), this.isWebGLCubeRenderTarget = true;
    let n = { width: t3, height: t3, depth: 1 }, s = [n, n, n, n, n, n];
    this.texture = new Vi(s), this._setTextureOptions(e), this.texture.isRenderTargetTexture = true;
  }
  fromEquirectangularTexture(t3, e) {
    this.texture.type = e.type, this.texture.colorSpace = e.colorSpace, this.texture.generateMipmaps = e.generateMipmaps, this.texture.minFilter = e.minFilter, this.texture.magFilter = e.magFilter;
    let n = { uniforms: { tEquirect: { value: null } }, vertexShader: `

				varying vec3 vWorldDirection;

				vec3 transformDirection( in vec3 dir, in mat4 matrix ) {

					return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );

				}

				void main() {

					vWorldDirection = transformDirection( position, modelMatrix );

					#include <begin_vertex>
					#include <project_vertex>

				}
			`, fragmentShader: `

				uniform sampler2D tEquirect;

				varying vec3 vWorldDirection;

				#include <common>

				void main() {

					vec3 direction = normalize( vWorldDirection );

					vec2 sampleUV = equirectUv( direction );

					gl_FragColor = texture2D( tEquirect, sampleUV );

				}
			` }, s = new Vn(5, 5, 5), r = new Ge({ name: "CubemapFromEquirect", uniforms: Wn(n.uniforms), vertexShader: n.vertexShader, fragmentShader: n.fragmentShader, side: ve, blending: hn });
    r.uniforms.tEquirect.value = e;
    let a = new Ie(s, r), o = e.minFilter;
    return e.minFilter === wn && (e.minFilter = ke), new Ps(1, 10, this).update(t3, a), e.minFilter = o, a.geometry.dispose(), a.material.dispose(), this;
  }
  clear(t3, e = true, n = true, s = true) {
    let r = t3.getRenderTarget();
    for (let a = 0; a < 6; a++) t3.setRenderTarget(this, a), t3.clear(e, n, s);
    t3.setRenderTarget(r);
  }
};
var Fn = class extends xe {
  constructor() {
    super(), this.isGroup = true, this.type = "Group";
  }
};
var Ac = { type: "move" };
var fi = class {
  constructor() {
    this._targetRay = null, this._grip = null, this._hand = null;
  }
  getHandSpace() {
    return this._hand === null && (this._hand = new Fn(), this._hand.matrixAutoUpdate = false, this._hand.visible = false, this._hand.joints = {}, this._hand.inputState = { pinching: false }), this._hand;
  }
  getTargetRaySpace() {
    return this._targetRay === null && (this._targetRay = new Fn(), this._targetRay.matrixAutoUpdate = false, this._targetRay.visible = false, this._targetRay.hasLinearVelocity = false, this._targetRay.linearVelocity = new F(), this._targetRay.hasAngularVelocity = false, this._targetRay.angularVelocity = new F()), this._targetRay;
  }
  getGripSpace() {
    return this._grip === null && (this._grip = new Fn(), this._grip.matrixAutoUpdate = false, this._grip.visible = false, this._grip.hasLinearVelocity = false, this._grip.linearVelocity = new F(), this._grip.hasAngularVelocity = false, this._grip.angularVelocity = new F()), this._grip;
  }
  dispatchEvent(t3) {
    return this._targetRay !== null && this._targetRay.dispatchEvent(t3), this._grip !== null && this._grip.dispatchEvent(t3), this._hand !== null && this._hand.dispatchEvent(t3), this;
  }
  connect(t3) {
    if (t3 && t3.hand) {
      let e = this._hand;
      if (e) for (let n of t3.hand.values()) this._getHandJoint(e, n);
    }
    return this.dispatchEvent({ type: "connected", data: t3 }), this;
  }
  disconnect(t3) {
    return this.dispatchEvent({ type: "disconnected", data: t3 }), this._targetRay !== null && (this._targetRay.visible = false), this._grip !== null && (this._grip.visible = false), this._hand !== null && (this._hand.visible = false), this;
  }
  update(t3, e, n) {
    let s = null, r = null, a = null, o = this._targetRay, c = this._grip, l = this._hand;
    if (t3 && e.session.visibilityState !== "visible-blurred") {
      if (l && t3.hand) {
        a = true;
        for (let v of t3.hand.values()) {
          let p = e.getJointPose(v, n), h = this._getHandJoint(l, v);
          p !== null && (h.matrix.fromArray(p.transform.matrix), h.matrix.decompose(h.position, h.rotation, h.scale), h.matrixWorldNeedsUpdate = true, h.jointRadius = p.radius), h.visible = p !== null;
        }
        let u = l.joints["index-finger-tip"], d = l.joints["thumb-tip"], f = u.position.distanceTo(d.position), m = 0.02, x = 5e-3;
        l.inputState.pinching && f > m + x ? (l.inputState.pinching = false, this.dispatchEvent({ type: "pinchend", handedness: t3.handedness, target: this })) : !l.inputState.pinching && f <= m - x && (l.inputState.pinching = true, this.dispatchEvent({ type: "pinchstart", handedness: t3.handedness, target: this }));
      } else c !== null && t3.gripSpace && (r = e.getPose(t3.gripSpace, n), r !== null && (c.matrix.fromArray(r.transform.matrix), c.matrix.decompose(c.position, c.rotation, c.scale), c.matrixWorldNeedsUpdate = true, r.linearVelocity ? (c.hasLinearVelocity = true, c.linearVelocity.copy(r.linearVelocity)) : c.hasLinearVelocity = false, r.angularVelocity ? (c.hasAngularVelocity = true, c.angularVelocity.copy(r.angularVelocity)) : c.hasAngularVelocity = false));
      o !== null && (s = e.getPose(t3.targetRaySpace, n), s === null && r !== null && (s = r), s !== null && (o.matrix.fromArray(s.transform.matrix), o.matrix.decompose(o.position, o.rotation, o.scale), o.matrixWorldNeedsUpdate = true, s.linearVelocity ? (o.hasLinearVelocity = true, o.linearVelocity.copy(s.linearVelocity)) : o.hasLinearVelocity = false, s.angularVelocity ? (o.hasAngularVelocity = true, o.angularVelocity.copy(s.angularVelocity)) : o.hasAngularVelocity = false, this.dispatchEvent(Ac)));
    }
    return o !== null && (o.visible = s !== null), c !== null && (c.visible = r !== null), l !== null && (l.visible = a !== null), this;
  }
  _getHandJoint(t3, e) {
    if (t3.joints[e.jointName] === void 0) {
      let n = new Fn();
      n.matrixAutoUpdate = false, n.visible = false, t3.joints[e.jointName] = n, t3.add(n);
    }
    return t3.joints[e.jointName];
  }
};
var Ds = class extends xe {
  constructor() {
    super(), this.isScene = true, this.type = "Scene", this.background = null, this.environment = null, this.fog = null, this.backgroundBlurriness = 0, this.backgroundIntensity = 1, this.backgroundRotation = new He(), this.environmentIntensity = 1, this.environmentRotation = new He(), this.overrideMaterial = null, typeof __THREE_DEVTOOLS__ < "u" && __THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe", { detail: this }));
  }
  copy(t3, e) {
    return super.copy(t3, e), t3.background !== null && (this.background = t3.background.clone()), t3.environment !== null && (this.environment = t3.environment.clone()), t3.fog !== null && (this.fog = t3.fog.clone()), this.backgroundBlurriness = t3.backgroundBlurriness, this.backgroundIntensity = t3.backgroundIntensity, this.backgroundRotation.copy(t3.backgroundRotation), this.environmentIntensity = t3.environmentIntensity, this.environmentRotation.copy(t3.environmentRotation), t3.overrideMaterial !== null && (this.overrideMaterial = t3.overrideMaterial.clone()), this.matrixAutoUpdate = t3.matrixAutoUpdate, this;
  }
  toJSON(t3) {
    let e = super.toJSON(t3);
    return this.fog !== null && (e.object.fog = this.fog.toJSON()), this.backgroundBlurriness > 0 && (e.object.backgroundBlurriness = this.backgroundBlurriness), this.backgroundIntensity !== 1 && (e.object.backgroundIntensity = this.backgroundIntensity), e.object.backgroundRotation = this.backgroundRotation.toArray(), this.environmentIntensity !== 1 && (e.object.environmentIntensity = this.environmentIntensity), e.object.environmentRotation = this.environmentRotation.toArray(), e;
  }
};
var pa = new F();
var wc = new F();
var Cc = new Lt();
var qe = class {
  constructor(t3 = new F(1, 0, 0), e = 0) {
    this.isPlane = true, this.normal = t3, this.constant = e;
  }
  set(t3, e) {
    return this.normal.copy(t3), this.constant = e, this;
  }
  setComponents(t3, e, n, s) {
    return this.normal.set(t3, e, n), this.constant = s, this;
  }
  setFromNormalAndCoplanarPoint(t3, e) {
    return this.normal.copy(t3), this.constant = -e.dot(this.normal), this;
  }
  setFromCoplanarPoints(t3, e, n) {
    let s = pa.subVectors(n, e).cross(wc.subVectors(t3, e)).normalize();
    return this.setFromNormalAndCoplanarPoint(s, t3), this;
  }
  copy(t3) {
    return this.normal.copy(t3.normal), this.constant = t3.constant, this;
  }
  normalize() {
    let t3 = 1 / this.normal.length();
    return this.normal.multiplyScalar(t3), this.constant *= t3, this;
  }
  negate() {
    return this.constant *= -1, this.normal.negate(), this;
  }
  distanceToPoint(t3) {
    return this.normal.dot(t3) + this.constant;
  }
  distanceToSphere(t3) {
    return this.distanceToPoint(t3.center) - t3.radius;
  }
  projectPoint(t3, e) {
    return e.copy(t3).addScaledVector(this.normal, -this.distanceToPoint(t3));
  }
  intersectLine(t3, e) {
    let n = t3.delta(pa), s = this.normal.dot(n);
    if (s === 0) return this.distanceToPoint(t3.start) === 0 ? e.copy(t3.start) : null;
    let r = -(t3.start.dot(this.normal) + this.constant) / s;
    return r < 0 || r > 1 ? null : e.copy(t3.start).addScaledVector(n, r);
  }
  intersectsLine(t3) {
    let e = this.distanceToPoint(t3.start), n = this.distanceToPoint(t3.end);
    return e < 0 && n > 0 || n < 0 && e > 0;
  }
  intersectsBox(t3) {
    return t3.intersectsPlane(this);
  }
  intersectsSphere(t3) {
    return t3.intersectsPlane(this);
  }
  coplanarPoint(t3) {
    return t3.copy(this.normal).multiplyScalar(-this.constant);
  }
  applyMatrix4(t3, e) {
    let n = e || Cc.getNormalMatrix(t3), s = this.coplanarPoint(pa).applyMatrix4(t3), r = this.normal.applyMatrix3(n).normalize();
    return this.constant = -s.dot(r), this;
  }
  translate(t3) {
    return this.constant -= t3.dot(this.normal), this;
  }
  equals(t3) {
    return t3.normal.equals(this.normal) && t3.constant === this.constant;
  }
  clone() {
    return new this.constructor().copy(this);
  }
};
var Un = new di();
var Rc = new Gt(0.5, 0.5);
var xs = new F();
var pi = class {
  constructor(t3 = new qe(), e = new qe(), n = new qe(), s = new qe(), r = new qe(), a = new qe()) {
    this.planes = [t3, e, n, s, r, a];
  }
  set(t3, e, n, s, r, a) {
    let o = this.planes;
    return o[0].copy(t3), o[1].copy(e), o[2].copy(n), o[3].copy(s), o[4].copy(r), o[5].copy(a), this;
  }
  copy(t3) {
    let e = this.planes;
    for (let n = 0; n < 6; n++) e[n].copy(t3.planes[n]);
    return this;
  }
  setFromProjectionMatrix(t3, e = Ve, n = false) {
    let s = this.planes, r = t3.elements, a = r[0], o = r[1], c = r[2], l = r[3], u = r[4], d = r[5], f = r[6], m = r[7], x = r[8], v = r[9], p = r[10], h = r[11], A = r[12], T = r[13], b = r[14], R = r[15];
    if (s[0].setComponents(l - a, m - u, h - x, R - A).normalize(), s[1].setComponents(l + a, m + u, h + x, R + A).normalize(), s[2].setComponents(l + o, m + d, h + v, R + T).normalize(), s[3].setComponents(l - o, m - d, h - v, R - T).normalize(), n) s[4].setComponents(c, f, p, b).normalize(), s[5].setComponents(l - c, m - f, h - p, R - b).normalize();
    else if (s[4].setComponents(l - c, m - f, h - p, R - b).normalize(), e === Ve) s[5].setComponents(l + c, m + f, h + p, R + b).normalize();
    else if (e === Li) s[5].setComponents(c, f, p, b).normalize();
    else throw new Error("THREE.Frustum.setFromProjectionMatrix(): Invalid coordinate system: " + e);
    return this;
  }
  intersectsObject(t3) {
    if (t3.boundingSphere !== void 0) t3.boundingSphere === null && t3.computeBoundingSphere(), Un.copy(t3.boundingSphere).applyMatrix4(t3.matrixWorld);
    else {
      let e = t3.geometry;
      e.boundingSphere === null && e.computeBoundingSphere(), Un.copy(e.boundingSphere).applyMatrix4(t3.matrixWorld);
    }
    return this.intersectsSphere(Un);
  }
  intersectsSprite(t3) {
    Un.center.set(0, 0, 0);
    let e = Rc.distanceTo(t3.center);
    return Un.radius = 0.7071067811865476 + e, Un.applyMatrix4(t3.matrixWorld), this.intersectsSphere(Un);
  }
  intersectsSphere(t3) {
    let e = this.planes, n = t3.center, s = -t3.radius;
    for (let r = 0; r < 6; r++) if (e[r].distanceToPoint(n) < s) return false;
    return true;
  }
  intersectsBox(t3) {
    let e = this.planes;
    for (let n = 0; n < 6; n++) {
      let s = e[n];
      if (xs.x = s.normal.x > 0 ? t3.max.x : t3.min.x, xs.y = s.normal.y > 0 ? t3.max.y : t3.min.y, xs.z = s.normal.z > 0 ? t3.max.z : t3.min.z, s.distanceToPoint(xs) < 0) return false;
    }
    return true;
  }
  containsPoint(t3) {
    let e = this.planes;
    for (let n = 0; n < 6; n++) if (e[n].distanceToPoint(t3) < 0) return false;
    return true;
  }
  clone() {
    return new this.constructor().copy(this);
  }
};
var ki = class extends Re {
  constructor(t3, e, n = Cn, s, r, a, o = Ne, c = Ne, l, u = ci, d = 1) {
    if (u !== ci && u !== vi) throw new Error("DepthTexture format must be either THREE.DepthFormat or THREE.DepthStencilFormat");
    let f = { width: t3, height: e, depth: d };
    super(f, s, r, a, o, c, u, n, l), this.isDepthTexture = true, this.flipY = false, this.generateMipmaps = false, this.compareFunction = null;
  }
  copy(t3) {
    return super.copy(t3), this.source = new ui(Object.assign({}, t3.image)), this.compareFunction = t3.compareFunction, this;
  }
  toJSON(t3) {
    let e = super.toJSON(t3);
    return this.compareFunction !== null && (e.compareFunction = this.compareFunction), e;
  }
};
var Hi = class extends Re {
  constructor(t3 = null) {
    super(), this.sourceTexture = t3, this.isExternalTexture = true;
  }
  copy(t3) {
    return super.copy(t3), this.sourceTexture = t3.sourceTexture, this;
  }
};
var Gi = class i12 extends En {
  constructor(t3 = 1, e = 1, n = 1, s = 1) {
    super(), this.type = "PlaneGeometry", this.parameters = { width: t3, height: e, widthSegments: n, heightSegments: s };
    let r = t3 / 2, a = e / 2, o = Math.floor(n), c = Math.floor(s), l = o + 1, u = c + 1, d = t3 / o, f = e / c, m = [], x = [], v = [], p = [];
    for (let h = 0; h < u; h++) {
      let A = h * f - a;
      for (let T = 0; T < l; T++) {
        let b = T * d - r;
        x.push(b, -A, 0), v.push(0, 0, 1), p.push(T / o), p.push(1 - h / c);
      }
    }
    for (let h = 0; h < c; h++) for (let A = 0; A < o; A++) {
      let T = A + l * h, b = A + l * (h + 1), R = A + 1 + l * (h + 1), w = A + 1 + l * h;
      m.push(T, b, w), m.push(b, R, w);
    }
    this.setIndex(m), this.setAttribute("position", new Ye(x, 3)), this.setAttribute("normal", new Ye(v, 3)), this.setAttribute("uv", new Ye(p, 2));
  }
  copy(t3) {
    return super.copy(t3), this.parameters = Object.assign({}, t3.parameters), this;
  }
  static fromJSON(t3) {
    return new i12(t3.width, t3.height, t3.widthSegments, t3.heightSegments);
  }
};
var Us = class extends bn {
  constructor(t3) {
    super(), this.isMeshStandardMaterial = true, this.type = "MeshStandardMaterial", this.defines = { STANDARD: "" }, this.color = new Vt(16777215), this.roughness = 1, this.metalness = 0, this.map = null, this.lightMap = null, this.lightMapIntensity = 1, this.aoMap = null, this.aoMapIntensity = 1, this.emissive = new Vt(0), this.emissiveIntensity = 1, this.emissiveMap = null, this.bumpMap = null, this.bumpScale = 1, this.normalMap = null, this.normalMapType = Va, this.normalScale = new Gt(1, 1), this.displacementMap = null, this.displacementScale = 1, this.displacementBias = 0, this.roughnessMap = null, this.metalnessMap = null, this.alphaMap = null, this.envMap = null, this.envMapRotation = new He(), this.envMapIntensity = 1, this.wireframe = false, this.wireframeLinewidth = 1, this.wireframeLinecap = "round", this.wireframeLinejoin = "round", this.flatShading = false, this.fog = true, this.setValues(t3);
  }
  copy(t3) {
    return super.copy(t3), this.defines = { STANDARD: "" }, this.color.copy(t3.color), this.roughness = t3.roughness, this.metalness = t3.metalness, this.map = t3.map, this.lightMap = t3.lightMap, this.lightMapIntensity = t3.lightMapIntensity, this.aoMap = t3.aoMap, this.aoMapIntensity = t3.aoMapIntensity, this.emissive.copy(t3.emissive), this.emissiveMap = t3.emissiveMap, this.emissiveIntensity = t3.emissiveIntensity, this.bumpMap = t3.bumpMap, this.bumpScale = t3.bumpScale, this.normalMap = t3.normalMap, this.normalMapType = t3.normalMapType, this.normalScale.copy(t3.normalScale), this.displacementMap = t3.displacementMap, this.displacementScale = t3.displacementScale, this.displacementBias = t3.displacementBias, this.roughnessMap = t3.roughnessMap, this.metalnessMap = t3.metalnessMap, this.alphaMap = t3.alphaMap, this.envMap = t3.envMap, this.envMapRotation.copy(t3.envMapRotation), this.envMapIntensity = t3.envMapIntensity, this.wireframe = t3.wireframe, this.wireframeLinewidth = t3.wireframeLinewidth, this.wireframeLinecap = t3.wireframeLinecap, this.wireframeLinejoin = t3.wireframeLinejoin, this.flatShading = t3.flatShading, this.fog = t3.fog, this;
  }
};
var Ns = class extends bn {
  constructor(t3) {
    super(), this.isMeshDepthMaterial = true, this.type = "MeshDepthMaterial", this.depthPacking = fl, this.map = null, this.alphaMap = null, this.displacementMap = null, this.displacementScale = 1, this.displacementBias = 0, this.wireframe = false, this.wireframeLinewidth = 1, this.setValues(t3);
  }
  copy(t3) {
    return super.copy(t3), this.depthPacking = t3.depthPacking, this.map = t3.map, this.alphaMap = t3.alphaMap, this.displacementMap = t3.displacementMap, this.displacementScale = t3.displacementScale, this.displacementBias = t3.displacementBias, this.wireframe = t3.wireframe, this.wireframeLinewidth = t3.wireframeLinewidth, this;
  }
};
var Fs = class extends bn {
  constructor(t3) {
    super(), this.isMeshDistanceMaterial = true, this.type = "MeshDistanceMaterial", this.map = null, this.alphaMap = null, this.displacementMap = null, this.displacementScale = 1, this.displacementBias = 0, this.setValues(t3);
  }
  copy(t3) {
    return super.copy(t3), this.map = t3.map, this.alphaMap = t3.alphaMap, this.displacementMap = t3.displacementMap, this.displacementScale = t3.displacementScale, this.displacementBias = t3.displacementBias, this;
  }
};
function vs(i14, t3) {
  return !i14 || i14.constructor === t3 ? i14 : typeof t3.BYTES_PER_ELEMENT == "number" ? new t3(i14) : Array.prototype.slice.call(i14);
}
function Ic(i14) {
  return ArrayBuffer.isView(i14) && !(i14 instanceof DataView);
}
var kn = class {
  constructor(t3, e, n, s) {
    this.parameterPositions = t3, this._cachedIndex = 0, this.resultBuffer = s !== void 0 ? s : new e.constructor(n), this.sampleValues = e, this.valueSize = n, this.settings = null, this.DefaultSettings_ = {};
  }
  evaluate(t3) {
    let e = this.parameterPositions, n = this._cachedIndex, s = e[n], r = e[n - 1];
    n: {
      t: {
        let a;
        e: {
          i: if (!(t3 < s)) {
            for (let o = n + 2; ; ) {
              if (s === void 0) {
                if (t3 < r) break i;
                return n = e.length, this._cachedIndex = n, this.copySampleValue_(n - 1);
              }
              if (n === o) break;
              if (r = s, s = e[++n], t3 < s) break t;
            }
            a = e.length;
            break e;
          }
          if (!(t3 >= r)) {
            let o = e[1];
            t3 < o && (n = 2, r = o);
            for (let c = n - 2; ; ) {
              if (r === void 0) return this._cachedIndex = 0, this.copySampleValue_(0);
              if (n === c) break;
              if (s = r, r = e[--n - 1], t3 >= r) break t;
            }
            a = n, n = 0;
            break e;
          }
          break n;
        }
        for (; n < a; ) {
          let o = n + a >>> 1;
          t3 < e[o] ? a = o : n = o + 1;
        }
        if (s = e[n], r = e[n - 1], r === void 0) return this._cachedIndex = 0, this.copySampleValue_(0);
        if (s === void 0) return n = e.length, this._cachedIndex = n, this.copySampleValue_(n - 1);
      }
      this._cachedIndex = n, this.intervalChanged_(n, r, s);
    }
    return this.interpolate_(n, r, t3, s);
  }
  getSettings_() {
    return this.settings || this.DefaultSettings_;
  }
  copySampleValue_(t3) {
    let e = this.resultBuffer, n = this.sampleValues, s = this.valueSize, r = t3 * s;
    for (let a = 0; a !== s; ++a) e[a] = n[r + a];
    return e;
  }
  interpolate_() {
    throw new Error("call to abstract method");
  }
  intervalChanged_() {
  }
};
var Os = class extends kn {
  constructor(t3, e, n, s) {
    super(t3, e, n, s), this._weightPrev = -0, this._offsetPrev = -0, this._weightNext = -0, this._offsetNext = -0, this.DefaultSettings_ = { endingStart: ga, endingEnd: ga };
  }
  intervalChanged_(t3, e, n) {
    let s = this.parameterPositions, r = t3 - 2, a = t3 + 1, o = s[r], c = s[a];
    if (o === void 0) switch (this.getSettings_().endingStart) {
      case _a:
        r = t3, o = 2 * e - n;
        break;
      case xa:
        r = s.length - 2, o = e + s[r] - s[r + 1];
        break;
      default:
        r = t3, o = n;
    }
    if (c === void 0) switch (this.getSettings_().endingEnd) {
      case _a:
        a = t3, c = 2 * n - e;
        break;
      case xa:
        a = 1, c = n + s[1] - s[0];
        break;
      default:
        a = t3 - 1, c = e;
    }
    let l = (n - e) * 0.5, u = this.valueSize;
    this._weightPrev = l / (e - o), this._weightNext = l / (c - n), this._offsetPrev = r * u, this._offsetNext = a * u;
  }
  interpolate_(t3, e, n, s) {
    let r = this.resultBuffer, a = this.sampleValues, o = this.valueSize, c = t3 * o, l = c - o, u = this._offsetPrev, d = this._offsetNext, f = this._weightPrev, m = this._weightNext, x = (n - e) / (s - e), v = x * x, p = v * x, h = -f * p + 2 * f * v - f * x, A = (1 + f) * p + (-1.5 - 2 * f) * v + (-0.5 + f) * x + 1, T = (-1 - m) * p + (1.5 + m) * v + 0.5 * x, b = m * p - m * v;
    for (let R = 0; R !== o; ++R) r[R] = h * a[u + R] + A * a[l + R] + T * a[c + R] + b * a[d + R];
    return r;
  }
};
var Bs = class extends kn {
  constructor(t3, e, n, s) {
    super(t3, e, n, s);
  }
  interpolate_(t3, e, n, s) {
    let r = this.resultBuffer, a = this.sampleValues, o = this.valueSize, c = t3 * o, l = c - o, u = (n - e) / (s - e), d = 1 - u;
    for (let f = 0; f !== o; ++f) r[f] = a[l + f] * d + a[c + f] * u;
    return r;
  }
};
var zs = class extends kn {
  constructor(t3, e, n, s) {
    super(t3, e, n, s);
  }
  interpolate_(t3) {
    return this.copySampleValue_(t3 - 1);
  }
};
var Pe = class {
  constructor(t3, e, n, s) {
    if (t3 === void 0) throw new Error("THREE.KeyframeTrack: track name is undefined");
    if (e === void 0 || e.length === 0) throw new Error("THREE.KeyframeTrack: no keyframes in track named " + t3);
    this.name = t3, this.times = vs(e, this.TimeBufferType), this.values = vs(n, this.ValueBufferType), this.setInterpolation(s || this.DefaultInterpolation);
  }
  static toJSON(t3) {
    let e = t3.constructor, n;
    if (e.toJSON !== this.toJSON) n = e.toJSON(t3);
    else {
      n = { name: t3.name, times: vs(t3.times, Array), values: vs(t3.values, Array) };
      let s = t3.getInterpolation();
      s !== t3.DefaultInterpolation && (n.interpolation = s);
    }
    return n.type = t3.ValueTypeName, n;
  }
  InterpolantFactoryMethodDiscrete(t3) {
    return new zs(this.times, this.values, this.getValueSize(), t3);
  }
  InterpolantFactoryMethodLinear(t3) {
    return new Bs(this.times, this.values, this.getValueSize(), t3);
  }
  InterpolantFactoryMethodSmooth(t3) {
    return new Os(this.times, this.values, this.getValueSize(), t3);
  }
  setInterpolation(t3) {
    let e;
    switch (t3) {
      case Ii:
        e = this.InterpolantFactoryMethodDiscrete;
        break;
      case Ts:
        e = this.InterpolantFactoryMethodLinear;
        break;
      case ys:
        e = this.InterpolantFactoryMethodSmooth;
        break;
    }
    if (e === void 0) {
      let n = "unsupported interpolation for " + this.ValueTypeName + " keyframe track named " + this.name;
      if (this.createInterpolant === void 0) if (t3 !== this.DefaultInterpolation) this.setInterpolation(this.DefaultInterpolation);
      else throw new Error(n);
      return console.warn("THREE.KeyframeTrack:", n), this;
    }
    return this.createInterpolant = e, this;
  }
  getInterpolation() {
    switch (this.createInterpolant) {
      case this.InterpolantFactoryMethodDiscrete:
        return Ii;
      case this.InterpolantFactoryMethodLinear:
        return Ts;
      case this.InterpolantFactoryMethodSmooth:
        return ys;
    }
  }
  getValueSize() {
    return this.values.length / this.times.length;
  }
  shift(t3) {
    if (t3 !== 0) {
      let e = this.times;
      for (let n = 0, s = e.length; n !== s; ++n) e[n] += t3;
    }
    return this;
  }
  scale(t3) {
    if (t3 !== 1) {
      let e = this.times;
      for (let n = 0, s = e.length; n !== s; ++n) e[n] *= t3;
    }
    return this;
  }
  trim(t3, e) {
    let n = this.times, s = n.length, r = 0, a = s - 1;
    for (; r !== s && n[r] < t3; ) ++r;
    for (; a !== -1 && n[a] > e; ) --a;
    if (++a, r !== 0 || a !== s) {
      r >= a && (a = Math.max(a, 1), r = a - 1);
      let o = this.getValueSize();
      this.times = n.slice(r, a), this.values = this.values.slice(r * o, a * o);
    }
    return this;
  }
  validate() {
    let t3 = true, e = this.getValueSize();
    e - Math.floor(e) !== 0 && (console.error("THREE.KeyframeTrack: Invalid value size in track.", this), t3 = false);
    let n = this.times, s = this.values, r = n.length;
    r === 0 && (console.error("THREE.KeyframeTrack: Track is empty.", this), t3 = false);
    let a = null;
    for (let o = 0; o !== r; o++) {
      let c = n[o];
      if (typeof c == "number" && isNaN(c)) {
        console.error("THREE.KeyframeTrack: Time is not a valid number.", this, o, c), t3 = false;
        break;
      }
      if (a !== null && a > c) {
        console.error("THREE.KeyframeTrack: Out of order keys.", this, o, c, a), t3 = false;
        break;
      }
      a = c;
    }
    if (s !== void 0 && Ic(s)) for (let o = 0, c = s.length; o !== c; ++o) {
      let l = s[o];
      if (isNaN(l)) {
        console.error("THREE.KeyframeTrack: Value is not a valid number.", this, o, l), t3 = false;
        break;
      }
    }
    return t3;
  }
  optimize() {
    let t3 = this.times.slice(), e = this.values.slice(), n = this.getValueSize(), s = this.getInterpolation() === ys, r = t3.length - 1, a = 1;
    for (let o = 1; o < r; ++o) {
      let c = false, l = t3[o], u = t3[o + 1];
      if (l !== u && (o !== 1 || l !== t3[0])) if (s) c = true;
      else {
        let d = o * n, f = d - n, m = d + n;
        for (let x = 0; x !== n; ++x) {
          let v = e[d + x];
          if (v !== e[f + x] || v !== e[m + x]) {
            c = true;
            break;
          }
        }
      }
      if (c) {
        if (o !== a) {
          t3[a] = t3[o];
          let d = o * n, f = a * n;
          for (let m = 0; m !== n; ++m) e[f + m] = e[d + m];
        }
        ++a;
      }
    }
    if (r > 0) {
      t3[a] = t3[r];
      for (let o = r * n, c = a * n, l = 0; l !== n; ++l) e[c + l] = e[o + l];
      ++a;
    }
    return a !== t3.length ? (this.times = t3.slice(0, a), this.values = e.slice(0, a * n)) : (this.times = t3, this.values = e), this;
  }
  clone() {
    let t3 = this.times.slice(), e = this.values.slice(), n = this.constructor, s = new n(this.name, t3, e);
    return s.createInterpolant = this.createInterpolant, s;
  }
};
Pe.prototype.ValueTypeName = "";
Pe.prototype.TimeBufferType = Float32Array;
Pe.prototype.ValueBufferType = Float32Array;
Pe.prototype.DefaultInterpolation = Ts;
var Tn = class extends Pe {
  constructor(t3, e, n) {
    super(t3, e, n);
  }
};
Tn.prototype.ValueTypeName = "bool";
Tn.prototype.ValueBufferType = Array;
Tn.prototype.DefaultInterpolation = Ii;
Tn.prototype.InterpolantFactoryMethodLinear = void 0;
Tn.prototype.InterpolantFactoryMethodSmooth = void 0;
var Vs = class extends Pe {
  constructor(t3, e, n, s) {
    super(t3, e, n, s);
  }
};
Vs.prototype.ValueTypeName = "color";
var ks = class extends Pe {
  constructor(t3, e, n, s) {
    super(t3, e, n, s);
  }
};
ks.prototype.ValueTypeName = "number";
var Hs = class extends kn {
  constructor(t3, e, n, s) {
    super(t3, e, n, s);
  }
  interpolate_(t3, e, n, s) {
    let r = this.resultBuffer, a = this.sampleValues, o = this.valueSize, c = (n - e) / (s - e), l = t3 * o;
    for (let u = l + o; l !== u; l += 4) cn.slerpFlat(r, 0, a, l - o, a, l, c);
    return r;
  }
};
var Wi = class extends Pe {
  constructor(t3, e, n, s) {
    super(t3, e, n, s);
  }
  InterpolantFactoryMethodLinear(t3) {
    return new Hs(this.times, this.values, this.getValueSize(), t3);
  }
};
Wi.prototype.ValueTypeName = "quaternion";
Wi.prototype.InterpolantFactoryMethodSmooth = void 0;
var An = class extends Pe {
  constructor(t3, e, n) {
    super(t3, e, n);
  }
};
An.prototype.ValueTypeName = "string";
An.prototype.ValueBufferType = Array;
An.prototype.DefaultInterpolation = Ii;
An.prototype.InterpolantFactoryMethodLinear = void 0;
An.prototype.InterpolantFactoryMethodSmooth = void 0;
var Gs = class extends Pe {
  constructor(t3, e, n, s) {
    super(t3, e, n, s);
  }
};
Gs.prototype.ValueTypeName = "vector";
var Ws = class {
  constructor(t3, e, n) {
    let s = this, r = false, a = 0, o = 0, c, l = [];
    this.onStart = void 0, this.onLoad = t3, this.onProgress = e, this.onError = n, this.abortController = new AbortController(), this.itemStart = function(u) {
      o++, r === false && s.onStart !== void 0 && s.onStart(u, a, o), r = true;
    }, this.itemEnd = function(u) {
      a++, s.onProgress !== void 0 && s.onProgress(u, a, o), a === o && (r = false, s.onLoad !== void 0 && s.onLoad());
    }, this.itemError = function(u) {
      s.onError !== void 0 && s.onError(u);
    }, this.resolveURL = function(u) {
      return c ? c(u) : u;
    }, this.setURLModifier = function(u) {
      return c = u, this;
    }, this.addHandler = function(u, d) {
      return l.push(u, d), this;
    }, this.removeHandler = function(u) {
      let d = l.indexOf(u);
      return d !== -1 && l.splice(d, 2), this;
    }, this.getHandler = function(u) {
      for (let d = 0, f = l.length; d < f; d += 2) {
        let m = l[d], x = l[d + 1];
        if (m.global && (m.lastIndex = 0), m.test(u)) return x;
      }
      return null;
    }, this.abort = function() {
      return this.abortController.abort(), this.abortController = new AbortController(), this;
    };
  }
};
var wl = new Ws();
var Xs = class {
  constructor(t3) {
    this.manager = t3 !== void 0 ? t3 : wl, this.crossOrigin = "anonymous", this.withCredentials = false, this.path = "", this.resourcePath = "", this.requestHeader = {};
  }
  load() {
  }
  loadAsync(t3, e) {
    let n = this;
    return new Promise(function(s, r) {
      n.load(t3, s, e, r);
    });
  }
  parse() {
  }
  setCrossOrigin(t3) {
    return this.crossOrigin = t3, this;
  }
  setWithCredentials(t3) {
    return this.withCredentials = t3, this;
  }
  setPath(t3) {
    return this.path = t3, this;
  }
  setResourcePath(t3) {
    return this.resourcePath = t3, this;
  }
  setRequestHeader(t3) {
    return this.requestHeader = t3, this;
  }
  abort() {
    return this;
  }
};
Xs.DEFAULT_MATERIAL_NAME = "__DEFAULT";
var Xi = class extends xe {
  constructor(t3, e = 1) {
    super(), this.isLight = true, this.type = "Light", this.color = new Vt(t3), this.intensity = e;
  }
  dispose() {
  }
  copy(t3, e) {
    return super.copy(t3, e), this.color.copy(t3.color), this.intensity = t3.intensity, this;
  }
  toJSON(t3) {
    let e = super.toJSON(t3);
    return e.object.color = this.color.getHex(), e.object.intensity = this.intensity, this.groundColor !== void 0 && (e.object.groundColor = this.groundColor.getHex()), this.distance !== void 0 && (e.object.distance = this.distance), this.angle !== void 0 && (e.object.angle = this.angle), this.decay !== void 0 && (e.object.decay = this.decay), this.penumbra !== void 0 && (e.object.penumbra = this.penumbra), this.shadow !== void 0 && (e.object.shadow = this.shadow.toJSON()), this.target !== void 0 && (e.object.target = this.target.uuid), e;
  }
};
var ma = new oe();
var Uo = new F();
var No = new F();
var Ma = class {
  constructor(t3) {
    this.camera = t3, this.intensity = 1, this.bias = 0, this.normalBias = 0, this.radius = 1, this.blurSamples = 8, this.mapSize = new Gt(512, 512), this.mapType = We, this.map = null, this.mapPass = null, this.matrix = new oe(), this.autoUpdate = true, this.needsUpdate = false, this._frustum = new pi(), this._frameExtents = new Gt(1, 1), this._viewportCount = 1, this._viewports = [new se(0, 0, 1, 1)];
  }
  getViewportCount() {
    return this._viewportCount;
  }
  getFrustum() {
    return this._frustum;
  }
  updateMatrices(t3) {
    let e = this.camera, n = this.matrix;
    Uo.setFromMatrixPosition(t3.matrixWorld), e.position.copy(Uo), No.setFromMatrixPosition(t3.target.matrixWorld), e.lookAt(No), e.updateMatrixWorld(), ma.multiplyMatrices(e.projectionMatrix, e.matrixWorldInverse), this._frustum.setFromProjectionMatrix(ma, e.coordinateSystem, e.reversedDepth), e.reversedDepth ? n.set(0.5, 0, 0, 0.5, 0, 0.5, 0, 0.5, 0, 0, 1, 0, 0, 0, 0, 1) : n.set(0.5, 0, 0, 0.5, 0, 0.5, 0, 0.5, 0, 0, 0.5, 0.5, 0, 0, 0, 1), n.multiply(ma);
  }
  getViewport(t3) {
    return this._viewports[t3];
  }
  getFrameExtents() {
    return this._frameExtents;
  }
  dispose() {
    this.map && this.map.dispose(), this.mapPass && this.mapPass.dispose();
  }
  copy(t3) {
    return this.camera = t3.camera.clone(), this.intensity = t3.intensity, this.bias = t3.bias, this.radius = t3.radius, this.autoUpdate = t3.autoUpdate, this.needsUpdate = t3.needsUpdate, this.normalBias = t3.normalBias, this.blurSamples = t3.blurSamples, this.mapSize.copy(t3.mapSize), this;
  }
  clone() {
    return new this.constructor().copy(this);
  }
  toJSON() {
    let t3 = {};
    return this.intensity !== 1 && (t3.intensity = this.intensity), this.bias !== 0 && (t3.bias = this.bias), this.normalBias !== 0 && (t3.normalBias = this.normalBias), this.radius !== 1 && (t3.radius = this.radius), (this.mapSize.x !== 512 || this.mapSize.y !== 512) && (t3.mapSize = this.mapSize.toArray()), t3.camera = this.camera.toJSON(false).object, delete t3.camera.matrix, t3;
  }
};
var mi = class extends zi {
  constructor(t3 = -1, e = 1, n = 1, s = -1, r = 0.1, a = 2e3) {
    super(), this.isOrthographicCamera = true, this.type = "OrthographicCamera", this.zoom = 1, this.view = null, this.left = t3, this.right = e, this.top = n, this.bottom = s, this.near = r, this.far = a, this.updateProjectionMatrix();
  }
  copy(t3, e) {
    return super.copy(t3, e), this.left = t3.left, this.right = t3.right, this.top = t3.top, this.bottom = t3.bottom, this.near = t3.near, this.far = t3.far, this.zoom = t3.zoom, this.view = t3.view === null ? null : Object.assign({}, t3.view), this;
  }
  setViewOffset(t3, e, n, s, r, a) {
    this.view === null && (this.view = { enabled: true, fullWidth: 1, fullHeight: 1, offsetX: 0, offsetY: 0, width: 1, height: 1 }), this.view.enabled = true, this.view.fullWidth = t3, this.view.fullHeight = e, this.view.offsetX = n, this.view.offsetY = s, this.view.width = r, this.view.height = a, this.updateProjectionMatrix();
  }
  clearViewOffset() {
    this.view !== null && (this.view.enabled = false), this.updateProjectionMatrix();
  }
  updateProjectionMatrix() {
    let t3 = (this.right - this.left) / (2 * this.zoom), e = (this.top - this.bottom) / (2 * this.zoom), n = (this.right + this.left) / 2, s = (this.top + this.bottom) / 2, r = n - t3, a = n + t3, o = s + e, c = s - e;
    if (this.view !== null && this.view.enabled) {
      let l = (this.right - this.left) / this.view.fullWidth / this.zoom, u = (this.top - this.bottom) / this.view.fullHeight / this.zoom;
      r += l * this.view.offsetX, a = r + l * this.view.width, o -= u * this.view.offsetY, c = o - u * this.view.height;
    }
    this.projectionMatrix.makeOrthographic(r, a, o, c, this.near, this.far, this.coordinateSystem, this.reversedDepth), this.projectionMatrixInverse.copy(this.projectionMatrix).invert();
  }
  toJSON(t3) {
    let e = super.toJSON(t3);
    return e.object.zoom = this.zoom, e.object.left = this.left, e.object.right = this.right, e.object.top = this.top, e.object.bottom = this.bottom, e.object.near = this.near, e.object.far = this.far, this.view !== null && (e.object.view = Object.assign({}, this.view)), e;
  }
};
var Sa = class extends Ma {
  constructor() {
    super(new mi(-5, 5, 5, -5, 0.5, 500)), this.isDirectionalLightShadow = true;
  }
};
var qs = class extends Xi {
  constructor(t3, e) {
    super(t3, e), this.isDirectionalLight = true, this.type = "DirectionalLight", this.position.copy(xe.DEFAULT_UP), this.updateMatrix(), this.target = new xe(), this.shadow = new Sa();
  }
  dispose() {
    this.shadow.dispose();
  }
  copy(t3) {
    return super.copy(t3), this.target = t3.target.clone(), this.shadow = t3.shadow.clone(), this;
  }
};
var Ys = class extends Xi {
  constructor(t3, e) {
    super(t3, e), this.isAmbientLight = true, this.type = "AmbientLight";
  }
};
var Zs = class extends Se {
  constructor(t3 = []) {
    super(), this.isArrayCamera = true, this.isMultiViewCamera = false, this.cameras = t3;
  }
};
var Xa = "\\[\\]\\.:\\/";
var Pc = new RegExp("[" + Xa + "]", "g");
var qa = "[^" + Xa + "]";
var Lc = "[^" + Xa.replace("\\.", "") + "]";
var Dc = /((?:WC+[\/:])*)/.source.replace("WC", qa);
var Uc = /(WCOD+)?/.source.replace("WCOD", Lc);
var Nc = /(?:\.(WC+)(?:\[(.+)\])?)?/.source.replace("WC", qa);
var Fc = /\.(WC+)(?:\[(.+)\])?/.source.replace("WC", qa);
var Oc = new RegExp("^" + Dc + Uc + Nc + Fc + "$");
var Bc = ["material", "materials", "bones", "map"];
var ba = class {
  constructor(t3, e, n) {
    let s = n || Qt.parseTrackName(e);
    this._targetGroup = t3, this._bindings = t3.subscribe_(e, s);
  }
  getValue(t3, e) {
    this.bind();
    let n = this._targetGroup.nCachedObjects_, s = this._bindings[n];
    s !== void 0 && s.getValue(t3, e);
  }
  setValue(t3, e) {
    let n = this._bindings;
    for (let s = this._targetGroup.nCachedObjects_, r = n.length; s !== r; ++s) n[s].setValue(t3, e);
  }
  bind() {
    let t3 = this._bindings;
    for (let e = this._targetGroup.nCachedObjects_, n = t3.length; e !== n; ++e) t3[e].bind();
  }
  unbind() {
    let t3 = this._bindings;
    for (let e = this._targetGroup.nCachedObjects_, n = t3.length; e !== n; ++e) t3[e].unbind();
  }
};
var Qt = class i13 {
  constructor(t3, e, n) {
    this.path = e, this.parsedPath = n || i13.parseTrackName(e), this.node = i13.findNode(t3, this.parsedPath.nodeName), this.rootNode = t3, this.getValue = this._getValue_unbound, this.setValue = this._setValue_unbound;
  }
  static create(t3, e, n) {
    return t3 && t3.isAnimationObjectGroup ? new i13.Composite(t3, e, n) : new i13(t3, e, n);
  }
  static sanitizeNodeName(t3) {
    return t3.replace(/\s/g, "_").replace(Pc, "");
  }
  static parseTrackName(t3) {
    let e = Oc.exec(t3);
    if (e === null) throw new Error("PropertyBinding: Cannot parse trackName: " + t3);
    let n = { nodeName: e[2], objectName: e[3], objectIndex: e[4], propertyName: e[5], propertyIndex: e[6] }, s = n.nodeName && n.nodeName.lastIndexOf(".");
    if (s !== void 0 && s !== -1) {
      let r = n.nodeName.substring(s + 1);
      Bc.indexOf(r) !== -1 && (n.nodeName = n.nodeName.substring(0, s), n.objectName = r);
    }
    if (n.propertyName === null || n.propertyName.length === 0) throw new Error("PropertyBinding: can not parse propertyName from trackName: " + t3);
    return n;
  }
  static findNode(t3, e) {
    if (e === void 0 || e === "" || e === "." || e === -1 || e === t3.name || e === t3.uuid) return t3;
    if (t3.skeleton) {
      let n = t3.skeleton.getBoneByName(e);
      if (n !== void 0) return n;
    }
    if (t3.children) {
      let n = function(r) {
        for (let a = 0; a < r.length; a++) {
          let o = r[a];
          if (o.name === e || o.uuid === e) return o;
          let c = n(o.children);
          if (c) return c;
        }
        return null;
      }, s = n(t3.children);
      if (s) return s;
    }
    return null;
  }
  _getValue_unavailable() {
  }
  _setValue_unavailable() {
  }
  _getValue_direct(t3, e) {
    t3[e] = this.targetObject[this.propertyName];
  }
  _getValue_array(t3, e) {
    let n = this.resolvedProperty;
    for (let s = 0, r = n.length; s !== r; ++s) t3[e++] = n[s];
  }
  _getValue_arrayElement(t3, e) {
    t3[e] = this.resolvedProperty[this.propertyIndex];
  }
  _getValue_toArray(t3, e) {
    this.resolvedProperty.toArray(t3, e);
  }
  _setValue_direct(t3, e) {
    this.targetObject[this.propertyName] = t3[e];
  }
  _setValue_direct_setNeedsUpdate(t3, e) {
    this.targetObject[this.propertyName] = t3[e], this.targetObject.needsUpdate = true;
  }
  _setValue_direct_setMatrixWorldNeedsUpdate(t3, e) {
    this.targetObject[this.propertyName] = t3[e], this.targetObject.matrixWorldNeedsUpdate = true;
  }
  _setValue_array(t3, e) {
    let n = this.resolvedProperty;
    for (let s = 0, r = n.length; s !== r; ++s) n[s] = t3[e++];
  }
  _setValue_array_setNeedsUpdate(t3, e) {
    let n = this.resolvedProperty;
    for (let s = 0, r = n.length; s !== r; ++s) n[s] = t3[e++];
    this.targetObject.needsUpdate = true;
  }
  _setValue_array_setMatrixWorldNeedsUpdate(t3, e) {
    let n = this.resolvedProperty;
    for (let s = 0, r = n.length; s !== r; ++s) n[s] = t3[e++];
    this.targetObject.matrixWorldNeedsUpdate = true;
  }
  _setValue_arrayElement(t3, e) {
    this.resolvedProperty[this.propertyIndex] = t3[e];
  }
  _setValue_arrayElement_setNeedsUpdate(t3, e) {
    this.resolvedProperty[this.propertyIndex] = t3[e], this.targetObject.needsUpdate = true;
  }
  _setValue_arrayElement_setMatrixWorldNeedsUpdate(t3, e) {
    this.resolvedProperty[this.propertyIndex] = t3[e], this.targetObject.matrixWorldNeedsUpdate = true;
  }
  _setValue_fromArray(t3, e) {
    this.resolvedProperty.fromArray(t3, e);
  }
  _setValue_fromArray_setNeedsUpdate(t3, e) {
    this.resolvedProperty.fromArray(t3, e), this.targetObject.needsUpdate = true;
  }
  _setValue_fromArray_setMatrixWorldNeedsUpdate(t3, e) {
    this.resolvedProperty.fromArray(t3, e), this.targetObject.matrixWorldNeedsUpdate = true;
  }
  _getValue_unbound(t3, e) {
    this.bind(), this.getValue(t3, e);
  }
  _setValue_unbound(t3, e) {
    this.bind(), this.setValue(t3, e);
  }
  bind() {
    let t3 = this.node, e = this.parsedPath, n = e.objectName, s = e.propertyName, r = e.propertyIndex;
    if (t3 || (t3 = i13.findNode(this.rootNode, e.nodeName), this.node = t3), this.getValue = this._getValue_unavailable, this.setValue = this._setValue_unavailable, !t3) {
      console.warn("THREE.PropertyBinding: No target node found for track: " + this.path + ".");
      return;
    }
    if (n) {
      let l = e.objectIndex;
      switch (n) {
        case "materials":
          if (!t3.material) {
            console.error("THREE.PropertyBinding: Can not bind to material as node does not have a material.", this);
            return;
          }
          if (!t3.material.materials) {
            console.error("THREE.PropertyBinding: Can not bind to material.materials as node.material does not have a materials array.", this);
            return;
          }
          t3 = t3.material.materials;
          break;
        case "bones":
          if (!t3.skeleton) {
            console.error("THREE.PropertyBinding: Can not bind to bones as node does not have a skeleton.", this);
            return;
          }
          t3 = t3.skeleton.bones;
          for (let u = 0; u < t3.length; u++) if (t3[u].name === l) {
            l = u;
            break;
          }
          break;
        case "map":
          if ("map" in t3) {
            t3 = t3.map;
            break;
          }
          if (!t3.material) {
            console.error("THREE.PropertyBinding: Can not bind to material as node does not have a material.", this);
            return;
          }
          if (!t3.material.map) {
            console.error("THREE.PropertyBinding: Can not bind to material.map as node.material does not have a map.", this);
            return;
          }
          t3 = t3.material.map;
          break;
        default:
          if (t3[n] === void 0) {
            console.error("THREE.PropertyBinding: Can not bind to objectName of node undefined.", this);
            return;
          }
          t3 = t3[n];
      }
      if (l !== void 0) {
        if (t3[l] === void 0) {
          console.error("THREE.PropertyBinding: Trying to bind to objectIndex of objectName, but is undefined.", this, t3);
          return;
        }
        t3 = t3[l];
      }
    }
    let a = t3[s];
    if (a === void 0) {
      let l = e.nodeName;
      console.error("THREE.PropertyBinding: Trying to update property for track: " + l + "." + s + " but it wasn't found.", t3);
      return;
    }
    let o = this.Versioning.None;
    this.targetObject = t3, t3.isMaterial === true ? o = this.Versioning.NeedsUpdate : t3.isObject3D === true && (o = this.Versioning.MatrixWorldNeedsUpdate);
    let c = this.BindingType.Direct;
    if (r !== void 0) {
      if (s === "morphTargetInfluences") {
        if (!t3.geometry) {
          console.error("THREE.PropertyBinding: Can not bind to morphTargetInfluences because node does not have a geometry.", this);
          return;
        }
        if (!t3.geometry.morphAttributes) {
          console.error("THREE.PropertyBinding: Can not bind to morphTargetInfluences because node does not have a geometry.morphAttributes.", this);
          return;
        }
        t3.morphTargetDictionary[r] !== void 0 && (r = t3.morphTargetDictionary[r]);
      }
      c = this.BindingType.ArrayElement, this.resolvedProperty = a, this.propertyIndex = r;
    } else a.fromArray !== void 0 && a.toArray !== void 0 ? (c = this.BindingType.HasFromToArray, this.resolvedProperty = a) : Array.isArray(a) ? (c = this.BindingType.EntireArray, this.resolvedProperty = a) : this.propertyName = s;
    this.getValue = this.GetterByBindingType[c], this.setValue = this.SetterByBindingTypeAndVersioning[c][o];
  }
  unbind() {
    this.node = null, this.getValue = this._getValue_unbound, this.setValue = this._setValue_unbound;
  }
};
Qt.Composite = ba;
Qt.prototype.BindingType = { Direct: 0, EntireArray: 1, ArrayElement: 2, HasFromToArray: 3 };
Qt.prototype.Versioning = { None: 0, NeedsUpdate: 1, MatrixWorldNeedsUpdate: 2 };
Qt.prototype.GetterByBindingType = [Qt.prototype._getValue_direct, Qt.prototype._getValue_array, Qt.prototype._getValue_arrayElement, Qt.prototype._getValue_toArray];
Qt.prototype.SetterByBindingTypeAndVersioning = [[Qt.prototype._setValue_direct, Qt.prototype._setValue_direct_setNeedsUpdate, Qt.prototype._setValue_direct_setMatrixWorldNeedsUpdate], [Qt.prototype._setValue_array, Qt.prototype._setValue_array_setNeedsUpdate, Qt.prototype._setValue_array_setMatrixWorldNeedsUpdate], [Qt.prototype._setValue_arrayElement, Qt.prototype._setValue_arrayElement_setNeedsUpdate, Qt.prototype._setValue_arrayElement_setMatrixWorldNeedsUpdate], [Qt.prototype._setValue_fromArray, Qt.prototype._setValue_fromArray_setNeedsUpdate, Qt.prototype._setValue_fromArray_setMatrixWorldNeedsUpdate]];
var mp = new Float32Array(1);
function Ya(i14, t3, e, n) {
  let s = zc(n);
  switch (e) {
    case Fa:
      return i14 * t3;
    case Ba:
      return i14 * t3 / s.components * s.byteLength;
    case lr:
      return i14 * t3 / s.components * s.byteLength;
    case za:
      return i14 * t3 * 2 / s.components * s.byteLength;
    case cr:
      return i14 * t3 * 2 / s.components * s.byteLength;
    case Oa:
      return i14 * t3 * 3 / s.components * s.byteLength;
    case Fe:
      return i14 * t3 * 4 / s.components * s.byteLength;
    case hr:
      return i14 * t3 * 4 / s.components * s.byteLength;
    case Zi:
    case Ji:
      return Math.floor((i14 + 3) / 4) * Math.floor((t3 + 3) / 4) * 8;
    case $i:
    case Ki:
      return Math.floor((i14 + 3) / 4) * Math.floor((t3 + 3) / 4) * 16;
    case dr:
    case pr:
      return Math.max(i14, 16) * Math.max(t3, 8) / 4;
    case ur:
    case fr:
      return Math.max(i14, 8) * Math.max(t3, 8) / 2;
    case mr:
    case gr:
      return Math.floor((i14 + 3) / 4) * Math.floor((t3 + 3) / 4) * 8;
    case _r:
      return Math.floor((i14 + 3) / 4) * Math.floor((t3 + 3) / 4) * 16;
    case xr:
      return Math.floor((i14 + 3) / 4) * Math.floor((t3 + 3) / 4) * 16;
    case vr:
      return Math.floor((i14 + 4) / 5) * Math.floor((t3 + 3) / 4) * 16;
    case yr:
      return Math.floor((i14 + 4) / 5) * Math.floor((t3 + 4) / 5) * 16;
    case Mr:
      return Math.floor((i14 + 5) / 6) * Math.floor((t3 + 4) / 5) * 16;
    case Sr:
      return Math.floor((i14 + 5) / 6) * Math.floor((t3 + 5) / 6) * 16;
    case br:
      return Math.floor((i14 + 7) / 8) * Math.floor((t3 + 4) / 5) * 16;
    case Er:
      return Math.floor((i14 + 7) / 8) * Math.floor((t3 + 5) / 6) * 16;
    case Tr:
      return Math.floor((i14 + 7) / 8) * Math.floor((t3 + 7) / 8) * 16;
    case Ar:
      return Math.floor((i14 + 9) / 10) * Math.floor((t3 + 4) / 5) * 16;
    case wr:
      return Math.floor((i14 + 9) / 10) * Math.floor((t3 + 5) / 6) * 16;
    case Cr:
      return Math.floor((i14 + 9) / 10) * Math.floor((t3 + 7) / 8) * 16;
    case Rr:
      return Math.floor((i14 + 9) / 10) * Math.floor((t3 + 9) / 10) * 16;
    case Ir:
      return Math.floor((i14 + 11) / 12) * Math.floor((t3 + 9) / 10) * 16;
    case Pr:
      return Math.floor((i14 + 11) / 12) * Math.floor((t3 + 11) / 12) * 16;
    case Lr:
    case Dr:
    case Ur:
      return Math.ceil(i14 / 4) * Math.ceil(t3 / 4) * 16;
    case Nr:
    case Fr:
      return Math.ceil(i14 / 4) * Math.ceil(t3 / 4) * 8;
    case Or:
    case Br:
      return Math.ceil(i14 / 4) * Math.ceil(t3 / 4) * 16;
  }
  throw new Error(`Unable to determine texture byte length for ${e} format.`);
}
function zc(i14) {
  switch (i14) {
    case We:
    case La:
      return { byteLength: 1, components: 1 };
    case gi:
    case Da:
    case _i:
      return { byteLength: 2, components: 1 };
    case ar:
    case or:
      return { byteLength: 2, components: 4 };
    case Cn:
    case rr:
    case Ke:
      return { byteLength: 4, components: 1 };
    case Ua:
    case Na:
      return { byteLength: 4, components: 3 };
  }
  throw new Error(`Unknown texture type ${i14}.`);
}
typeof __THREE_DEVTOOLS__ < "u" && __THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("register", { detail: { revision: "180" } }));
typeof window < "u" && (window.__THREE__ ? console.warn("WARNING: Multiple instances of Three.js being imported.") : window.__THREE__ = "180");
function Kl() {
  let i14 = null, t3 = false, e = null, n = null;
  function s(r, a) {
    e(r, a), n = i14.requestAnimationFrame(s);
  }
  return { start: function() {
    t3 !== true && e !== null && (n = i14.requestAnimationFrame(s), t3 = true);
  }, stop: function() {
    i14.cancelAnimationFrame(n), t3 = false;
  }, setAnimationLoop: function(r) {
    e = r;
  }, setContext: function(r) {
    i14 = r;
  } };
}
function Vc(i14) {
  let t3 = /* @__PURE__ */ new WeakMap();
  function e(o, c) {
    let l = o.array, u = o.usage, d = l.byteLength, f = i14.createBuffer();
    i14.bindBuffer(c, f), i14.bufferData(c, l, u), o.onUploadCallback();
    let m;
    if (l instanceof Float32Array) m = i14.FLOAT;
    else if (typeof Float16Array < "u" && l instanceof Float16Array) m = i14.HALF_FLOAT;
    else if (l instanceof Uint16Array) o.isFloat16BufferAttribute ? m = i14.HALF_FLOAT : m = i14.UNSIGNED_SHORT;
    else if (l instanceof Int16Array) m = i14.SHORT;
    else if (l instanceof Uint32Array) m = i14.UNSIGNED_INT;
    else if (l instanceof Int32Array) m = i14.INT;
    else if (l instanceof Int8Array) m = i14.BYTE;
    else if (l instanceof Uint8Array) m = i14.UNSIGNED_BYTE;
    else if (l instanceof Uint8ClampedArray) m = i14.UNSIGNED_BYTE;
    else throw new Error("THREE.WebGLAttributes: Unsupported buffer data format: " + l);
    return { buffer: f, type: m, bytesPerElement: l.BYTES_PER_ELEMENT, version: o.version, size: d };
  }
  function n(o, c, l) {
    let u = c.array, d = c.updateRanges;
    if (i14.bindBuffer(l, o), d.length === 0) i14.bufferSubData(l, 0, u);
    else {
      d.sort((m, x) => m.start - x.start);
      let f = 0;
      for (let m = 1; m < d.length; m++) {
        let x = d[f], v = d[m];
        v.start <= x.start + x.count + 1 ? x.count = Math.max(x.count, v.start + v.count - x.start) : (++f, d[f] = v);
      }
      d.length = f + 1;
      for (let m = 0, x = d.length; m < x; m++) {
        let v = d[m];
        i14.bufferSubData(l, v.start * u.BYTES_PER_ELEMENT, u, v.start, v.count);
      }
      c.clearUpdateRanges();
    }
    c.onUploadCallback();
  }
  function s(o) {
    return o.isInterleavedBufferAttribute && (o = o.data), t3.get(o);
  }
  function r(o) {
    o.isInterleavedBufferAttribute && (o = o.data);
    let c = t3.get(o);
    c && (i14.deleteBuffer(c.buffer), t3.delete(o));
  }
  function a(o, c) {
    if (o.isInterleavedBufferAttribute && (o = o.data), o.isGLBufferAttribute) {
      let u = t3.get(o);
      (!u || u.version < o.version) && t3.set(o, { buffer: o.buffer, type: o.type, bytesPerElement: o.elementSize, version: o.version });
      return;
    }
    let l = t3.get(o);
    if (l === void 0) t3.set(o, e(o, c));
    else if (l.version < o.version) {
      if (l.size !== o.array.byteLength) throw new Error("THREE.WebGLAttributes: The size of the buffer attribute's array buffer does not match the original size. Resizing buffer attributes is not supported.");
      n(l.buffer, o, c), l.version = o.version;
    }
  }
  return { get: s, remove: r, update: a };
}
var kc = `#ifdef USE_ALPHAHASH
	if ( diffuseColor.a < getAlphaHashThreshold( vPosition ) ) discard;
#endif`;
var Hc = `#ifdef USE_ALPHAHASH
	const float ALPHA_HASH_SCALE = 0.05;
	float hash2D( vec2 value ) {
		return fract( 1.0e4 * sin( 17.0 * value.x + 0.1 * value.y ) * ( 0.1 + abs( sin( 13.0 * value.y + value.x ) ) ) );
	}
	float hash3D( vec3 value ) {
		return hash2D( vec2( hash2D( value.xy ), value.z ) );
	}
	float getAlphaHashThreshold( vec3 position ) {
		float maxDeriv = max(
			length( dFdx( position.xyz ) ),
			length( dFdy( position.xyz ) )
		);
		float pixScale = 1.0 / ( ALPHA_HASH_SCALE * maxDeriv );
		vec2 pixScales = vec2(
			exp2( floor( log2( pixScale ) ) ),
			exp2( ceil( log2( pixScale ) ) )
		);
		vec2 alpha = vec2(
			hash3D( floor( pixScales.x * position.xyz ) ),
			hash3D( floor( pixScales.y * position.xyz ) )
		);
		float lerpFactor = fract( log2( pixScale ) );
		float x = ( 1.0 - lerpFactor ) * alpha.x + lerpFactor * alpha.y;
		float a = min( lerpFactor, 1.0 - lerpFactor );
		vec3 cases = vec3(
			x * x / ( 2.0 * a * ( 1.0 - a ) ),
			( x - 0.5 * a ) / ( 1.0 - a ),
			1.0 - ( ( 1.0 - x ) * ( 1.0 - x ) / ( 2.0 * a * ( 1.0 - a ) ) )
		);
		float threshold = ( x < ( 1.0 - a ) )
			? ( ( x < a ) ? cases.x : cases.y )
			: cases.z;
		return clamp( threshold , 1.0e-6, 1.0 );
	}
#endif`;
var Gc = `#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, vAlphaMapUv ).g;
#endif`;
var Wc = `#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`;
var Xc = `#ifdef USE_ALPHATEST
	#ifdef ALPHA_TO_COVERAGE
	diffuseColor.a = smoothstep( alphaTest, alphaTest + fwidth( diffuseColor.a ), diffuseColor.a );
	if ( diffuseColor.a == 0.0 ) discard;
	#else
	if ( diffuseColor.a < alphaTest ) discard;
	#endif
#endif`;
var qc = `#ifdef USE_ALPHATEST
	uniform float alphaTest;
#endif`;
var Yc = `#ifdef USE_AOMAP
	float ambientOcclusion = ( texture2D( aoMap, vAoMapUv ).r - 1.0 ) * aoMapIntensity + 1.0;
	reflectedLight.indirectDiffuse *= ambientOcclusion;
	#if defined( USE_CLEARCOAT ) 
		clearcoatSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_SHEEN ) 
		sheenSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_ENVMAP ) && defined( STANDARD )
		float dotNV = saturate( dot( geometryNormal, geometryViewDir ) );
		reflectedLight.indirectSpecular *= computeSpecularOcclusion( dotNV, ambientOcclusion, material.roughness );
	#endif
#endif`;
var Zc = `#ifdef USE_AOMAP
	uniform sampler2D aoMap;
	uniform float aoMapIntensity;
#endif`;
var Jc = `#ifdef USE_BATCHING
	#if ! defined( GL_ANGLE_multi_draw )
	#define gl_DrawID _gl_DrawID
	uniform int _gl_DrawID;
	#endif
	uniform highp sampler2D batchingTexture;
	uniform highp usampler2D batchingIdTexture;
	mat4 getBatchingMatrix( const in float i ) {
		int size = textureSize( batchingTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( batchingTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( batchingTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( batchingTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( batchingTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
	float getIndirectIndex( const in int i ) {
		int size = textureSize( batchingIdTexture, 0 ).x;
		int x = i % size;
		int y = i / size;
		return float( texelFetch( batchingIdTexture, ivec2( x, y ), 0 ).r );
	}
#endif
#ifdef USE_BATCHING_COLOR
	uniform sampler2D batchingColorTexture;
	vec3 getBatchingColor( const in float i ) {
		int size = textureSize( batchingColorTexture, 0 ).x;
		int j = int( i );
		int x = j % size;
		int y = j / size;
		return texelFetch( batchingColorTexture, ivec2( x, y ), 0 ).rgb;
	}
#endif`;
var $c = `#ifdef USE_BATCHING
	mat4 batchingMatrix = getBatchingMatrix( getIndirectIndex( gl_DrawID ) );
#endif`;
var Kc = `vec3 transformed = vec3( position );
#ifdef USE_ALPHAHASH
	vPosition = vec3( position );
#endif`;
var Qc = `vec3 objectNormal = vec3( normal );
#ifdef USE_TANGENT
	vec3 objectTangent = vec3( tangent.xyz );
#endif`;
var jc = `float G_BlinnPhong_Implicit( ) {
	return 0.25;
}
float D_BlinnPhong( const in float shininess, const in float dotNH ) {
	return RECIPROCAL_PI * ( shininess * 0.5 + 1.0 ) * pow( dotNH, shininess );
}
vec3 BRDF_BlinnPhong( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in vec3 specularColor, const in float shininess ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( specularColor, 1.0, dotVH );
	float G = G_BlinnPhong_Implicit( );
	float D = D_BlinnPhong( shininess, dotNH );
	return F * ( G * D );
} // validated`;
var th = `#ifdef USE_IRIDESCENCE
	const mat3 XYZ_TO_REC709 = mat3(
		 3.2404542, -0.9692660,  0.0556434,
		-1.5371385,  1.8760108, -0.2040259,
		-0.4985314,  0.0415560,  1.0572252
	);
	vec3 Fresnel0ToIor( vec3 fresnel0 ) {
		vec3 sqrtF0 = sqrt( fresnel0 );
		return ( vec3( 1.0 ) + sqrtF0 ) / ( vec3( 1.0 ) - sqrtF0 );
	}
	vec3 IorToFresnel0( vec3 transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - vec3( incidentIor ) ) / ( transmittedIor + vec3( incidentIor ) ) );
	}
	float IorToFresnel0( float transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - incidentIor ) / ( transmittedIor + incidentIor ));
	}
	vec3 evalSensitivity( float OPD, vec3 shift ) {
		float phase = 2.0 * PI * OPD * 1.0e-9;
		vec3 val = vec3( 5.4856e-13, 4.4201e-13, 5.2481e-13 );
		vec3 pos = vec3( 1.6810e+06, 1.7953e+06, 2.2084e+06 );
		vec3 var = vec3( 4.3278e+09, 9.3046e+09, 6.6121e+09 );
		vec3 xyz = val * sqrt( 2.0 * PI * var ) * cos( pos * phase + shift ) * exp( - pow2( phase ) * var );
		xyz.x += 9.7470e-14 * sqrt( 2.0 * PI * 4.5282e+09 ) * cos( 2.2399e+06 * phase + shift[ 0 ] ) * exp( - 4.5282e+09 * pow2( phase ) );
		xyz /= 1.0685e-7;
		vec3 rgb = XYZ_TO_REC709 * xyz;
		return rgb;
	}
	vec3 evalIridescence( float outsideIOR, float eta2, float cosTheta1, float thinFilmThickness, vec3 baseF0 ) {
		vec3 I;
		float iridescenceIOR = mix( outsideIOR, eta2, smoothstep( 0.0, 0.03, thinFilmThickness ) );
		float sinTheta2Sq = pow2( outsideIOR / iridescenceIOR ) * ( 1.0 - pow2( cosTheta1 ) );
		float cosTheta2Sq = 1.0 - sinTheta2Sq;
		if ( cosTheta2Sq < 0.0 ) {
			return vec3( 1.0 );
		}
		float cosTheta2 = sqrt( cosTheta2Sq );
		float R0 = IorToFresnel0( iridescenceIOR, outsideIOR );
		float R12 = F_Schlick( R0, 1.0, cosTheta1 );
		float T121 = 1.0 - R12;
		float phi12 = 0.0;
		if ( iridescenceIOR < outsideIOR ) phi12 = PI;
		float phi21 = PI - phi12;
		vec3 baseIOR = Fresnel0ToIor( clamp( baseF0, 0.0, 0.9999 ) );		vec3 R1 = IorToFresnel0( baseIOR, iridescenceIOR );
		vec3 R23 = F_Schlick( R1, 1.0, cosTheta2 );
		vec3 phi23 = vec3( 0.0 );
		if ( baseIOR[ 0 ] < iridescenceIOR ) phi23[ 0 ] = PI;
		if ( baseIOR[ 1 ] < iridescenceIOR ) phi23[ 1 ] = PI;
		if ( baseIOR[ 2 ] < iridescenceIOR ) phi23[ 2 ] = PI;
		float OPD = 2.0 * iridescenceIOR * thinFilmThickness * cosTheta2;
		vec3 phi = vec3( phi21 ) + phi23;
		vec3 R123 = clamp( R12 * R23, 1e-5, 0.9999 );
		vec3 r123 = sqrt( R123 );
		vec3 Rs = pow2( T121 ) * R23 / ( vec3( 1.0 ) - R123 );
		vec3 C0 = R12 + Rs;
		I = C0;
		vec3 Cm = Rs - T121;
		for ( int m = 1; m <= 2; ++ m ) {
			Cm *= r123;
			vec3 Sm = 2.0 * evalSensitivity( float( m ) * OPD, float( m ) * phi );
			I += Cm * Sm;
		}
		return max( I, vec3( 0.0 ) );
	}
#endif`;
var eh = `#ifdef USE_BUMPMAP
	uniform sampler2D bumpMap;
	uniform float bumpScale;
	vec2 dHdxy_fwd() {
		vec2 dSTdx = dFdx( vBumpMapUv );
		vec2 dSTdy = dFdy( vBumpMapUv );
		float Hll = bumpScale * texture2D( bumpMap, vBumpMapUv ).x;
		float dBx = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdx ).x - Hll;
		float dBy = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdy ).x - Hll;
		return vec2( dBx, dBy );
	}
	vec3 perturbNormalArb( vec3 surf_pos, vec3 surf_norm, vec2 dHdxy, float faceDirection ) {
		vec3 vSigmaX = normalize( dFdx( surf_pos.xyz ) );
		vec3 vSigmaY = normalize( dFdy( surf_pos.xyz ) );
		vec3 vN = surf_norm;
		vec3 R1 = cross( vSigmaY, vN );
		vec3 R2 = cross( vN, vSigmaX );
		float fDet = dot( vSigmaX, R1 ) * faceDirection;
		vec3 vGrad = sign( fDet ) * ( dHdxy.x * R1 + dHdxy.y * R2 );
		return normalize( abs( fDet ) * surf_norm - vGrad );
	}
#endif`;
var nh = `#if NUM_CLIPPING_PLANES > 0
	vec4 plane;
	#ifdef ALPHA_TO_COVERAGE
		float distanceToPlane, distanceGradient;
		float clipOpacity = 1.0;
		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {
			plane = clippingPlanes[ i ];
			distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
			distanceGradient = fwidth( distanceToPlane ) / 2.0;
			clipOpacity *= smoothstep( - distanceGradient, distanceGradient, distanceToPlane );
			if ( clipOpacity == 0.0 ) discard;
		}
		#pragma unroll_loop_end
		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES
			float unionClipOpacity = 1.0;
			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {
				plane = clippingPlanes[ i ];
				distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
				distanceGradient = fwidth( distanceToPlane ) / 2.0;
				unionClipOpacity *= 1.0 - smoothstep( - distanceGradient, distanceGradient, distanceToPlane );
			}
			#pragma unroll_loop_end
			clipOpacity *= 1.0 - unionClipOpacity;
		#endif
		diffuseColor.a *= clipOpacity;
		if ( diffuseColor.a == 0.0 ) discard;
	#else
		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {
			plane = clippingPlanes[ i ];
			if ( dot( vClipPosition, plane.xyz ) > plane.w ) discard;
		}
		#pragma unroll_loop_end
		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES
			bool clipped = true;
			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {
				plane = clippingPlanes[ i ];
				clipped = ( dot( vClipPosition, plane.xyz ) > plane.w ) && clipped;
			}
			#pragma unroll_loop_end
			if ( clipped ) discard;
		#endif
	#endif
#endif`;
var ih = `#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
	uniform vec4 clippingPlanes[ NUM_CLIPPING_PLANES ];
#endif`;
var sh = `#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
#endif`;
var rh = `#if NUM_CLIPPING_PLANES > 0
	vClipPosition = - mvPosition.xyz;
#endif`;
var ah = `#if defined( USE_COLOR_ALPHA )
	diffuseColor *= vColor;
#elif defined( USE_COLOR )
	diffuseColor.rgb *= vColor;
#endif`;
var oh = `#if defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#elif defined( USE_COLOR )
	varying vec3 vColor;
#endif`;
var lh = `#if defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#elif defined( USE_COLOR ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )
	varying vec3 vColor;
#endif`;
var ch = `#if defined( USE_COLOR_ALPHA )
	vColor = vec4( 1.0 );
#elif defined( USE_COLOR ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )
	vColor = vec3( 1.0 );
#endif
#ifdef USE_COLOR
	vColor *= color;
#endif
#ifdef USE_INSTANCING_COLOR
	vColor.xyz *= instanceColor.xyz;
#endif
#ifdef USE_BATCHING_COLOR
	vec3 batchingColor = getBatchingColor( getIndirectIndex( gl_DrawID ) );
	vColor.xyz *= batchingColor.xyz;
#endif`;
var hh = `#define PI 3.141592653589793
#define PI2 6.283185307179586
#define PI_HALF 1.5707963267948966
#define RECIPROCAL_PI 0.3183098861837907
#define RECIPROCAL_PI2 0.15915494309189535
#define EPSILON 1e-6
#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
#define whiteComplement( a ) ( 1.0 - saturate( a ) )
float pow2( const in float x ) { return x*x; }
vec3 pow2( const in vec3 x ) { return x*x; }
float pow3( const in float x ) { return x*x*x; }
float pow4( const in float x ) { float x2 = x*x; return x2*x2; }
float max3( const in vec3 v ) { return max( max( v.x, v.y ), v.z ); }
float average( const in vec3 v ) { return dot( v, vec3( 0.3333333 ) ); }
highp float rand( const in vec2 uv ) {
	const highp float a = 12.9898, b = 78.233, c = 43758.5453;
	highp float dt = dot( uv.xy, vec2( a,b ) ), sn = mod( dt, PI );
	return fract( sin( sn ) * c );
}
#ifdef HIGH_PRECISION
	float precisionSafeLength( vec3 v ) { return length( v ); }
#else
	float precisionSafeLength( vec3 v ) {
		float maxComponent = max3( abs( v ) );
		return length( v / maxComponent ) * maxComponent;
	}
#endif
struct IncidentLight {
	vec3 color;
	vec3 direction;
	bool visible;
};
struct ReflectedLight {
	vec3 directDiffuse;
	vec3 directSpecular;
	vec3 indirectDiffuse;
	vec3 indirectSpecular;
};
#ifdef USE_ALPHAHASH
	varying vec3 vPosition;
#endif
vec3 transformDirection( in vec3 dir, in mat4 matrix ) {
	return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );
}
vec3 inverseTransformDirection( in vec3 dir, in mat4 matrix ) {
	return normalize( ( vec4( dir, 0.0 ) * matrix ).xyz );
}
mat3 transposeMat3( const in mat3 m ) {
	mat3 tmp;
	tmp[ 0 ] = vec3( m[ 0 ].x, m[ 1 ].x, m[ 2 ].x );
	tmp[ 1 ] = vec3( m[ 0 ].y, m[ 1 ].y, m[ 2 ].y );
	tmp[ 2 ] = vec3( m[ 0 ].z, m[ 1 ].z, m[ 2 ].z );
	return tmp;
}
bool isPerspectiveMatrix( mat4 m ) {
	return m[ 2 ][ 3 ] == - 1.0;
}
vec2 equirectUv( in vec3 dir ) {
	float u = atan( dir.z, dir.x ) * RECIPROCAL_PI2 + 0.5;
	float v = asin( clamp( dir.y, - 1.0, 1.0 ) ) * RECIPROCAL_PI + 0.5;
	return vec2( u, v );
}
vec3 BRDF_Lambert( const in vec3 diffuseColor ) {
	return RECIPROCAL_PI * diffuseColor;
}
vec3 F_Schlick( const in vec3 f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
}
float F_Schlick( const in float f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
} // validated`;
var uh = `#ifdef ENVMAP_TYPE_CUBE_UV
	#define cubeUV_minMipLevel 4.0
	#define cubeUV_minTileSize 16.0
	float getFace( vec3 direction ) {
		vec3 absDirection = abs( direction );
		float face = - 1.0;
		if ( absDirection.x > absDirection.z ) {
			if ( absDirection.x > absDirection.y )
				face = direction.x > 0.0 ? 0.0 : 3.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		} else {
			if ( absDirection.z > absDirection.y )
				face = direction.z > 0.0 ? 2.0 : 5.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		}
		return face;
	}
	vec2 getUV( vec3 direction, float face ) {
		vec2 uv;
		if ( face == 0.0 ) {
			uv = vec2( direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 1.0 ) {
			uv = vec2( - direction.x, - direction.z ) / abs( direction.y );
		} else if ( face == 2.0 ) {
			uv = vec2( - direction.x, direction.y ) / abs( direction.z );
		} else if ( face == 3.0 ) {
			uv = vec2( - direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 4.0 ) {
			uv = vec2( - direction.x, direction.z ) / abs( direction.y );
		} else {
			uv = vec2( direction.x, direction.y ) / abs( direction.z );
		}
		return 0.5 * ( uv + 1.0 );
	}
	vec3 bilinearCubeUV( sampler2D envMap, vec3 direction, float mipInt ) {
		float face = getFace( direction );
		float filterInt = max( cubeUV_minMipLevel - mipInt, 0.0 );
		mipInt = max( mipInt, cubeUV_minMipLevel );
		float faceSize = exp2( mipInt );
		highp vec2 uv = getUV( direction, face ) * ( faceSize - 2.0 ) + 1.0;
		if ( face > 2.0 ) {
			uv.y += faceSize;
			face -= 3.0;
		}
		uv.x += face * faceSize;
		uv.x += filterInt * 3.0 * cubeUV_minTileSize;
		uv.y += 4.0 * ( exp2( CUBEUV_MAX_MIP ) - faceSize );
		uv.x *= CUBEUV_TEXEL_WIDTH;
		uv.y *= CUBEUV_TEXEL_HEIGHT;
		#ifdef texture2DGradEXT
			return texture2DGradEXT( envMap, uv, vec2( 0.0 ), vec2( 0.0 ) ).rgb;
		#else
			return texture2D( envMap, uv ).rgb;
		#endif
	}
	#define cubeUV_r0 1.0
	#define cubeUV_m0 - 2.0
	#define cubeUV_r1 0.8
	#define cubeUV_m1 - 1.0
	#define cubeUV_r4 0.4
	#define cubeUV_m4 2.0
	#define cubeUV_r5 0.305
	#define cubeUV_m5 3.0
	#define cubeUV_r6 0.21
	#define cubeUV_m6 4.0
	float roughnessToMip( float roughness ) {
		float mip = 0.0;
		if ( roughness >= cubeUV_r1 ) {
			mip = ( cubeUV_r0 - roughness ) * ( cubeUV_m1 - cubeUV_m0 ) / ( cubeUV_r0 - cubeUV_r1 ) + cubeUV_m0;
		} else if ( roughness >= cubeUV_r4 ) {
			mip = ( cubeUV_r1 - roughness ) * ( cubeUV_m4 - cubeUV_m1 ) / ( cubeUV_r1 - cubeUV_r4 ) + cubeUV_m1;
		} else if ( roughness >= cubeUV_r5 ) {
			mip = ( cubeUV_r4 - roughness ) * ( cubeUV_m5 - cubeUV_m4 ) / ( cubeUV_r4 - cubeUV_r5 ) + cubeUV_m4;
		} else if ( roughness >= cubeUV_r6 ) {
			mip = ( cubeUV_r5 - roughness ) * ( cubeUV_m6 - cubeUV_m5 ) / ( cubeUV_r5 - cubeUV_r6 ) + cubeUV_m5;
		} else {
			mip = - 2.0 * log2( 1.16 * roughness );		}
		return mip;
	}
	vec4 textureCubeUV( sampler2D envMap, vec3 sampleDir, float roughness ) {
		float mip = clamp( roughnessToMip( roughness ), cubeUV_m0, CUBEUV_MAX_MIP );
		float mipF = fract( mip );
		float mipInt = floor( mip );
		vec3 color0 = bilinearCubeUV( envMap, sampleDir, mipInt );
		if ( mipF == 0.0 ) {
			return vec4( color0, 1.0 );
		} else {
			vec3 color1 = bilinearCubeUV( envMap, sampleDir, mipInt + 1.0 );
			return vec4( mix( color0, color1, mipF ), 1.0 );
		}
	}
#endif`;
var dh = `vec3 transformedNormal = objectNormal;
#ifdef USE_TANGENT
	vec3 transformedTangent = objectTangent;
#endif
#ifdef USE_BATCHING
	mat3 bm = mat3( batchingMatrix );
	transformedNormal /= vec3( dot( bm[ 0 ], bm[ 0 ] ), dot( bm[ 1 ], bm[ 1 ] ), dot( bm[ 2 ], bm[ 2 ] ) );
	transformedNormal = bm * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = bm * transformedTangent;
	#endif
#endif
#ifdef USE_INSTANCING
	mat3 im = mat3( instanceMatrix );
	transformedNormal /= vec3( dot( im[ 0 ], im[ 0 ] ), dot( im[ 1 ], im[ 1 ] ), dot( im[ 2 ], im[ 2 ] ) );
	transformedNormal = im * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = im * transformedTangent;
	#endif
#endif
transformedNormal = normalMatrix * transformedNormal;
#ifdef FLIP_SIDED
	transformedNormal = - transformedNormal;
#endif
#ifdef USE_TANGENT
	transformedTangent = ( modelViewMatrix * vec4( transformedTangent, 0.0 ) ).xyz;
	#ifdef FLIP_SIDED
		transformedTangent = - transformedTangent;
	#endif
#endif`;
var fh = `#ifdef USE_DISPLACEMENTMAP
	uniform sampler2D displacementMap;
	uniform float displacementScale;
	uniform float displacementBias;
#endif`;
var ph = `#ifdef USE_DISPLACEMENTMAP
	transformed += normalize( objectNormal ) * ( texture2D( displacementMap, vDisplacementMapUv ).x * displacementScale + displacementBias );
#endif`;
var mh = `#ifdef USE_EMISSIVEMAP
	vec4 emissiveColor = texture2D( emissiveMap, vEmissiveMapUv );
	#ifdef DECODE_VIDEO_TEXTURE_EMISSIVE
		emissiveColor = sRGBTransferEOTF( emissiveColor );
	#endif
	totalEmissiveRadiance *= emissiveColor.rgb;
#endif`;
var gh = `#ifdef USE_EMISSIVEMAP
	uniform sampler2D emissiveMap;
#endif`;
var _h = "gl_FragColor = linearToOutputTexel( gl_FragColor );";
var xh = `vec4 LinearTransferOETF( in vec4 value ) {
	return value;
}
vec4 sRGBTransferEOTF( in vec4 value ) {
	return vec4( mix( pow( value.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), value.rgb * 0.0773993808, vec3( lessThanEqual( value.rgb, vec3( 0.04045 ) ) ) ), value.a );
}
vec4 sRGBTransferOETF( in vec4 value ) {
	return vec4( mix( pow( value.rgb, vec3( 0.41666 ) ) * 1.055 - vec3( 0.055 ), value.rgb * 12.92, vec3( lessThanEqual( value.rgb, vec3( 0.0031308 ) ) ) ), value.a );
}`;
var vh = `#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vec3 cameraToFrag;
		if ( isOrthographic ) {
			cameraToFrag = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToFrag = normalize( vWorldPosition - cameraPosition );
		}
		vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vec3 reflectVec = reflect( cameraToFrag, worldNormal );
		#else
			vec3 reflectVec = refract( cameraToFrag, worldNormal, refractionRatio );
		#endif
	#else
		vec3 reflectVec = vReflect;
	#endif
	#ifdef ENVMAP_TYPE_CUBE
		vec4 envColor = textureCube( envMap, envMapRotation * vec3( flipEnvMap * reflectVec.x, reflectVec.yz ) );
	#else
		vec4 envColor = vec4( 0.0 );
	#endif
	#ifdef ENVMAP_BLENDING_MULTIPLY
		outgoingLight = mix( outgoingLight, outgoingLight * envColor.xyz, specularStrength * reflectivity );
	#elif defined( ENVMAP_BLENDING_MIX )
		outgoingLight = mix( outgoingLight, envColor.xyz, specularStrength * reflectivity );
	#elif defined( ENVMAP_BLENDING_ADD )
		outgoingLight += envColor.xyz * specularStrength * reflectivity;
	#endif
#endif`;
var yh = `#ifdef USE_ENVMAP
	uniform float envMapIntensity;
	uniform float flipEnvMap;
	uniform mat3 envMapRotation;
	#ifdef ENVMAP_TYPE_CUBE
		uniform samplerCube envMap;
	#else
		uniform sampler2D envMap;
	#endif
	
#endif`;
var Mh = `#ifdef USE_ENVMAP
	uniform float reflectivity;
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		varying vec3 vWorldPosition;
		uniform float refractionRatio;
	#else
		varying vec3 vReflect;
	#endif
#endif`;
var Sh = `#ifdef USE_ENVMAP
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		
		varying vec3 vWorldPosition;
	#else
		varying vec3 vReflect;
		uniform float refractionRatio;
	#endif
#endif`;
var bh = `#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vWorldPosition = worldPosition.xyz;
	#else
		vec3 cameraToVertex;
		if ( isOrthographic ) {
			cameraToVertex = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToVertex = normalize( worldPosition.xyz - cameraPosition );
		}
		vec3 worldNormal = inverseTransformDirection( transformedNormal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vReflect = reflect( cameraToVertex, worldNormal );
		#else
			vReflect = refract( cameraToVertex, worldNormal, refractionRatio );
		#endif
	#endif
#endif`;
var Eh = `#ifdef USE_FOG
	vFogDepth = - mvPosition.z;
#endif`;
var Th = `#ifdef USE_FOG
	varying float vFogDepth;
#endif`;
var Ah = `#ifdef USE_FOG
	#ifdef FOG_EXP2
		float fogFactor = 1.0 - exp( - fogDensity * fogDensity * vFogDepth * vFogDepth );
	#else
		float fogFactor = smoothstep( fogNear, fogFar, vFogDepth );
	#endif
	gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, fogFactor );
#endif`;
var wh = `#ifdef USE_FOG
	uniform vec3 fogColor;
	varying float vFogDepth;
	#ifdef FOG_EXP2
		uniform float fogDensity;
	#else
		uniform float fogNear;
		uniform float fogFar;
	#endif
#endif`;
var Ch = `#ifdef USE_GRADIENTMAP
	uniform sampler2D gradientMap;
#endif
vec3 getGradientIrradiance( vec3 normal, vec3 lightDirection ) {
	float dotNL = dot( normal, lightDirection );
	vec2 coord = vec2( dotNL * 0.5 + 0.5, 0.0 );
	#ifdef USE_GRADIENTMAP
		return vec3( texture2D( gradientMap, coord ).r );
	#else
		vec2 fw = fwidth( coord ) * 0.5;
		return mix( vec3( 0.7 ), vec3( 1.0 ), smoothstep( 0.7 - fw.x, 0.7 + fw.x, coord.x ) );
	#endif
}`;
var Rh = `#ifdef USE_LIGHTMAP
	uniform sampler2D lightMap;
	uniform float lightMapIntensity;
#endif`;
var Ih = `LambertMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularStrength = specularStrength;`;
var Ph = `varying vec3 vViewPosition;
struct LambertMaterial {
	vec3 diffuseColor;
	float specularStrength;
};
void RE_Direct_Lambert( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Lambert( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Lambert
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Lambert`;
var Lh = `uniform bool receiveShadow;
uniform vec3 ambientLightColor;
#if defined( USE_LIGHT_PROBES )
	uniform vec3 lightProbe[ 9 ];
#endif
vec3 shGetIrradianceAt( in vec3 normal, in vec3 shCoefficients[ 9 ] ) {
	float x = normal.x, y = normal.y, z = normal.z;
	vec3 result = shCoefficients[ 0 ] * 0.886227;
	result += shCoefficients[ 1 ] * 2.0 * 0.511664 * y;
	result += shCoefficients[ 2 ] * 2.0 * 0.511664 * z;
	result += shCoefficients[ 3 ] * 2.0 * 0.511664 * x;
	result += shCoefficients[ 4 ] * 2.0 * 0.429043 * x * y;
	result += shCoefficients[ 5 ] * 2.0 * 0.429043 * y * z;
	result += shCoefficients[ 6 ] * ( 0.743125 * z * z - 0.247708 );
	result += shCoefficients[ 7 ] * 2.0 * 0.429043 * x * z;
	result += shCoefficients[ 8 ] * 0.429043 * ( x * x - y * y );
	return result;
}
vec3 getLightProbeIrradiance( const in vec3 lightProbe[ 9 ], const in vec3 normal ) {
	vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
	vec3 irradiance = shGetIrradianceAt( worldNormal, lightProbe );
	return irradiance;
}
vec3 getAmbientLightIrradiance( const in vec3 ambientLightColor ) {
	vec3 irradiance = ambientLightColor;
	return irradiance;
}
float getDistanceAttenuation( const in float lightDistance, const in float cutoffDistance, const in float decayExponent ) {
	float distanceFalloff = 1.0 / max( pow( lightDistance, decayExponent ), 0.01 );
	if ( cutoffDistance > 0.0 ) {
		distanceFalloff *= pow2( saturate( 1.0 - pow4( lightDistance / cutoffDistance ) ) );
	}
	return distanceFalloff;
}
float getSpotAttenuation( const in float coneCosine, const in float penumbraCosine, const in float angleCosine ) {
	return smoothstep( coneCosine, penumbraCosine, angleCosine );
}
#if NUM_DIR_LIGHTS > 0
	struct DirectionalLight {
		vec3 direction;
		vec3 color;
	};
	uniform DirectionalLight directionalLights[ NUM_DIR_LIGHTS ];
	void getDirectionalLightInfo( const in DirectionalLight directionalLight, out IncidentLight light ) {
		light.color = directionalLight.color;
		light.direction = directionalLight.direction;
		light.visible = true;
	}
#endif
#if NUM_POINT_LIGHTS > 0
	struct PointLight {
		vec3 position;
		vec3 color;
		float distance;
		float decay;
	};
	uniform PointLight pointLights[ NUM_POINT_LIGHTS ];
	void getPointLightInfo( const in PointLight pointLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = pointLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float lightDistance = length( lVector );
		light.color = pointLight.color;
		light.color *= getDistanceAttenuation( lightDistance, pointLight.distance, pointLight.decay );
		light.visible = ( light.color != vec3( 0.0 ) );
	}
#endif
#if NUM_SPOT_LIGHTS > 0
	struct SpotLight {
		vec3 position;
		vec3 direction;
		vec3 color;
		float distance;
		float decay;
		float coneCos;
		float penumbraCos;
	};
	uniform SpotLight spotLights[ NUM_SPOT_LIGHTS ];
	void getSpotLightInfo( const in SpotLight spotLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = spotLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float angleCos = dot( light.direction, spotLight.direction );
		float spotAttenuation = getSpotAttenuation( spotLight.coneCos, spotLight.penumbraCos, angleCos );
		if ( spotAttenuation > 0.0 ) {
			float lightDistance = length( lVector );
			light.color = spotLight.color * spotAttenuation;
			light.color *= getDistanceAttenuation( lightDistance, spotLight.distance, spotLight.decay );
			light.visible = ( light.color != vec3( 0.0 ) );
		} else {
			light.color = vec3( 0.0 );
			light.visible = false;
		}
	}
#endif
#if NUM_RECT_AREA_LIGHTS > 0
	struct RectAreaLight {
		vec3 color;
		vec3 position;
		vec3 halfWidth;
		vec3 halfHeight;
	};
	uniform sampler2D ltc_1;	uniform sampler2D ltc_2;
	uniform RectAreaLight rectAreaLights[ NUM_RECT_AREA_LIGHTS ];
#endif
#if NUM_HEMI_LIGHTS > 0
	struct HemisphereLight {
		vec3 direction;
		vec3 skyColor;
		vec3 groundColor;
	};
	uniform HemisphereLight hemisphereLights[ NUM_HEMI_LIGHTS ];
	vec3 getHemisphereLightIrradiance( const in HemisphereLight hemiLight, const in vec3 normal ) {
		float dotNL = dot( normal, hemiLight.direction );
		float hemiDiffuseWeight = 0.5 * dotNL + 0.5;
		vec3 irradiance = mix( hemiLight.groundColor, hemiLight.skyColor, hemiDiffuseWeight );
		return irradiance;
	}
#endif`;
var Dh = `#ifdef USE_ENVMAP
	vec3 getIBLIrradiance( const in vec3 normal ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * worldNormal, 1.0 );
			return PI * envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	vec3 getIBLRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 reflectVec = reflect( - viewDir, normal );
			reflectVec = normalize( mix( reflectVec, normal, roughness * roughness) );
			reflectVec = inverseTransformDirection( reflectVec, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * reflectVec, roughness );
			return envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	#ifdef USE_ANISOTROPY
		vec3 getIBLAnisotropyRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness, const in vec3 bitangent, const in float anisotropy ) {
			#ifdef ENVMAP_TYPE_CUBE_UV
				vec3 bentNormal = cross( bitangent, viewDir );
				bentNormal = normalize( cross( bentNormal, bitangent ) );
				bentNormal = normalize( mix( bentNormal, normal, pow2( pow2( 1.0 - anisotropy * ( 1.0 - roughness ) ) ) ) );
				return getIBLRadiance( viewDir, bentNormal, roughness );
			#else
				return vec3( 0.0 );
			#endif
		}
	#endif
#endif`;
var Uh = `ToonMaterial material;
material.diffuseColor = diffuseColor.rgb;`;
var Nh = `varying vec3 vViewPosition;
struct ToonMaterial {
	vec3 diffuseColor;
};
void RE_Direct_Toon( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	vec3 irradiance = getGradientIrradiance( geometryNormal, directLight.direction ) * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Toon( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Toon
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Toon`;
var Fh = `BlinnPhongMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularColor = specular;
material.specularShininess = shininess;
material.specularStrength = specularStrength;`;
var Oh = `varying vec3 vViewPosition;
struct BlinnPhongMaterial {
	vec3 diffuseColor;
	vec3 specularColor;
	float specularShininess;
	float specularStrength;
};
void RE_Direct_BlinnPhong( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
	reflectedLight.directSpecular += irradiance * BRDF_BlinnPhong( directLight.direction, geometryViewDir, geometryNormal, material.specularColor, material.specularShininess ) * material.specularStrength;
}
void RE_IndirectDiffuse_BlinnPhong( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_BlinnPhong
#define RE_IndirectDiffuse		RE_IndirectDiffuse_BlinnPhong`;
var Bh = `PhysicalMaterial material;
material.diffuseColor = diffuseColor.rgb * ( 1.0 - metalnessFactor );
vec3 dxy = max( abs( dFdx( nonPerturbedNormal ) ), abs( dFdy( nonPerturbedNormal ) ) );
float geometryRoughness = max( max( dxy.x, dxy.y ), dxy.z );
material.roughness = max( roughnessFactor, 0.0525 );material.roughness += geometryRoughness;
material.roughness = min( material.roughness, 1.0 );
#ifdef IOR
	material.ior = ior;
	#ifdef USE_SPECULAR
		float specularIntensityFactor = specularIntensity;
		vec3 specularColorFactor = specularColor;
		#ifdef USE_SPECULAR_COLORMAP
			specularColorFactor *= texture2D( specularColorMap, vSpecularColorMapUv ).rgb;
		#endif
		#ifdef USE_SPECULAR_INTENSITYMAP
			specularIntensityFactor *= texture2D( specularIntensityMap, vSpecularIntensityMapUv ).a;
		#endif
		material.specularF90 = mix( specularIntensityFactor, 1.0, metalnessFactor );
	#else
		float specularIntensityFactor = 1.0;
		vec3 specularColorFactor = vec3( 1.0 );
		material.specularF90 = 1.0;
	#endif
	material.specularColor = mix( min( pow2( ( material.ior - 1.0 ) / ( material.ior + 1.0 ) ) * specularColorFactor, vec3( 1.0 ) ) * specularIntensityFactor, diffuseColor.rgb, metalnessFactor );
#else
	material.specularColor = mix( vec3( 0.04 ), diffuseColor.rgb, metalnessFactor );
	material.specularF90 = 1.0;
#endif
#ifdef USE_CLEARCOAT
	material.clearcoat = clearcoat;
	material.clearcoatRoughness = clearcoatRoughness;
	material.clearcoatF0 = vec3( 0.04 );
	material.clearcoatF90 = 1.0;
	#ifdef USE_CLEARCOATMAP
		material.clearcoat *= texture2D( clearcoatMap, vClearcoatMapUv ).x;
	#endif
	#ifdef USE_CLEARCOAT_ROUGHNESSMAP
		material.clearcoatRoughness *= texture2D( clearcoatRoughnessMap, vClearcoatRoughnessMapUv ).y;
	#endif
	material.clearcoat = saturate( material.clearcoat );	material.clearcoatRoughness = max( material.clearcoatRoughness, 0.0525 );
	material.clearcoatRoughness += geometryRoughness;
	material.clearcoatRoughness = min( material.clearcoatRoughness, 1.0 );
#endif
#ifdef USE_DISPERSION
	material.dispersion = dispersion;
#endif
#ifdef USE_IRIDESCENCE
	material.iridescence = iridescence;
	material.iridescenceIOR = iridescenceIOR;
	#ifdef USE_IRIDESCENCEMAP
		material.iridescence *= texture2D( iridescenceMap, vIridescenceMapUv ).r;
	#endif
	#ifdef USE_IRIDESCENCE_THICKNESSMAP
		material.iridescenceThickness = (iridescenceThicknessMaximum - iridescenceThicknessMinimum) * texture2D( iridescenceThicknessMap, vIridescenceThicknessMapUv ).g + iridescenceThicknessMinimum;
	#else
		material.iridescenceThickness = iridescenceThicknessMaximum;
	#endif
#endif
#ifdef USE_SHEEN
	material.sheenColor = sheenColor;
	#ifdef USE_SHEEN_COLORMAP
		material.sheenColor *= texture2D( sheenColorMap, vSheenColorMapUv ).rgb;
	#endif
	material.sheenRoughness = clamp( sheenRoughness, 0.07, 1.0 );
	#ifdef USE_SHEEN_ROUGHNESSMAP
		material.sheenRoughness *= texture2D( sheenRoughnessMap, vSheenRoughnessMapUv ).a;
	#endif
#endif
#ifdef USE_ANISOTROPY
	#ifdef USE_ANISOTROPYMAP
		mat2 anisotropyMat = mat2( anisotropyVector.x, anisotropyVector.y, - anisotropyVector.y, anisotropyVector.x );
		vec3 anisotropyPolar = texture2D( anisotropyMap, vAnisotropyMapUv ).rgb;
		vec2 anisotropyV = anisotropyMat * normalize( 2.0 * anisotropyPolar.rg - vec2( 1.0 ) ) * anisotropyPolar.b;
	#else
		vec2 anisotropyV = anisotropyVector;
	#endif
	material.anisotropy = length( anisotropyV );
	if( material.anisotropy == 0.0 ) {
		anisotropyV = vec2( 1.0, 0.0 );
	} else {
		anisotropyV /= material.anisotropy;
		material.anisotropy = saturate( material.anisotropy );
	}
	material.alphaT = mix( pow2( material.roughness ), 1.0, pow2( material.anisotropy ) );
	material.anisotropyT = tbn[ 0 ] * anisotropyV.x + tbn[ 1 ] * anisotropyV.y;
	material.anisotropyB = tbn[ 1 ] * anisotropyV.x - tbn[ 0 ] * anisotropyV.y;
#endif`;
var zh = `struct PhysicalMaterial {
	vec3 diffuseColor;
	float roughness;
	vec3 specularColor;
	float specularF90;
	float dispersion;
	#ifdef USE_CLEARCOAT
		float clearcoat;
		float clearcoatRoughness;
		vec3 clearcoatF0;
		float clearcoatF90;
	#endif
	#ifdef USE_IRIDESCENCE
		float iridescence;
		float iridescenceIOR;
		float iridescenceThickness;
		vec3 iridescenceFresnel;
		vec3 iridescenceF0;
	#endif
	#ifdef USE_SHEEN
		vec3 sheenColor;
		float sheenRoughness;
	#endif
	#ifdef IOR
		float ior;
	#endif
	#ifdef USE_TRANSMISSION
		float transmission;
		float transmissionAlpha;
		float thickness;
		float attenuationDistance;
		vec3 attenuationColor;
	#endif
	#ifdef USE_ANISOTROPY
		float anisotropy;
		float alphaT;
		vec3 anisotropyT;
		vec3 anisotropyB;
	#endif
};
vec3 clearcoatSpecularDirect = vec3( 0.0 );
vec3 clearcoatSpecularIndirect = vec3( 0.0 );
vec3 sheenSpecularDirect = vec3( 0.0 );
vec3 sheenSpecularIndirect = vec3(0.0 );
vec3 Schlick_to_F0( const in vec3 f, const in float f90, const in float dotVH ) {
    float x = clamp( 1.0 - dotVH, 0.0, 1.0 );
    float x2 = x * x;
    float x5 = clamp( x * x2 * x2, 0.0, 0.9999 );
    return ( f - vec3( f90 ) * x5 ) / ( 1.0 - x5 );
}
float V_GGX_SmithCorrelated( const in float alpha, const in float dotNL, const in float dotNV ) {
	float a2 = pow2( alpha );
	float gv = dotNL * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNV ) );
	float gl = dotNV * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNL ) );
	return 0.5 / max( gv + gl, EPSILON );
}
float D_GGX( const in float alpha, const in float dotNH ) {
	float a2 = pow2( alpha );
	float denom = pow2( dotNH ) * ( a2 - 1.0 ) + 1.0;
	return RECIPROCAL_PI * a2 / pow2( denom );
}
#ifdef USE_ANISOTROPY
	float V_GGX_SmithCorrelated_Anisotropic( const in float alphaT, const in float alphaB, const in float dotTV, const in float dotBV, const in float dotTL, const in float dotBL, const in float dotNV, const in float dotNL ) {
		float gv = dotNL * length( vec3( alphaT * dotTV, alphaB * dotBV, dotNV ) );
		float gl = dotNV * length( vec3( alphaT * dotTL, alphaB * dotBL, dotNL ) );
		float v = 0.5 / ( gv + gl );
		return saturate(v);
	}
	float D_GGX_Anisotropic( const in float alphaT, const in float alphaB, const in float dotNH, const in float dotTH, const in float dotBH ) {
		float a2 = alphaT * alphaB;
		highp vec3 v = vec3( alphaB * dotTH, alphaT * dotBH, a2 * dotNH );
		highp float v2 = dot( v, v );
		float w2 = a2 / v2;
		return RECIPROCAL_PI * a2 * pow2 ( w2 );
	}
#endif
#ifdef USE_CLEARCOAT
	vec3 BRDF_GGX_Clearcoat( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material) {
		vec3 f0 = material.clearcoatF0;
		float f90 = material.clearcoatF90;
		float roughness = material.clearcoatRoughness;
		float alpha = pow2( roughness );
		vec3 halfDir = normalize( lightDir + viewDir );
		float dotNL = saturate( dot( normal, lightDir ) );
		float dotNV = saturate( dot( normal, viewDir ) );
		float dotNH = saturate( dot( normal, halfDir ) );
		float dotVH = saturate( dot( viewDir, halfDir ) );
		vec3 F = F_Schlick( f0, f90, dotVH );
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
		return F * ( V * D );
	}
#endif
vec3 BRDF_GGX( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material ) {
	vec3 f0 = material.specularColor;
	float f90 = material.specularF90;
	float roughness = material.roughness;
	float alpha = pow2( roughness );
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( f0, f90, dotVH );
	#ifdef USE_IRIDESCENCE
		F = mix( F, material.iridescenceFresnel, material.iridescence );
	#endif
	#ifdef USE_ANISOTROPY
		float dotTL = dot( material.anisotropyT, lightDir );
		float dotTV = dot( material.anisotropyT, viewDir );
		float dotTH = dot( material.anisotropyT, halfDir );
		float dotBL = dot( material.anisotropyB, lightDir );
		float dotBV = dot( material.anisotropyB, viewDir );
		float dotBH = dot( material.anisotropyB, halfDir );
		float V = V_GGX_SmithCorrelated_Anisotropic( material.alphaT, alpha, dotTV, dotBV, dotTL, dotBL, dotNV, dotNL );
		float D = D_GGX_Anisotropic( material.alphaT, alpha, dotNH, dotTH, dotBH );
	#else
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
	#endif
	return F * ( V * D );
}
vec2 LTC_Uv( const in vec3 N, const in vec3 V, const in float roughness ) {
	const float LUT_SIZE = 64.0;
	const float LUT_SCALE = ( LUT_SIZE - 1.0 ) / LUT_SIZE;
	const float LUT_BIAS = 0.5 / LUT_SIZE;
	float dotNV = saturate( dot( N, V ) );
	vec2 uv = vec2( roughness, sqrt( 1.0 - dotNV ) );
	uv = uv * LUT_SCALE + LUT_BIAS;
	return uv;
}
float LTC_ClippedSphereFormFactor( const in vec3 f ) {
	float l = length( f );
	return max( ( l * l + f.z ) / ( l + 1.0 ), 0.0 );
}
vec3 LTC_EdgeVectorFormFactor( const in vec3 v1, const in vec3 v2 ) {
	float x = dot( v1, v2 );
	float y = abs( x );
	float a = 0.8543985 + ( 0.4965155 + 0.0145206 * y ) * y;
	float b = 3.4175940 + ( 4.1616724 + y ) * y;
	float v = a / b;
	float theta_sintheta = ( x > 0.0 ) ? v : 0.5 * inversesqrt( max( 1.0 - x * x, 1e-7 ) ) - v;
	return cross( v1, v2 ) * theta_sintheta;
}
vec3 LTC_Evaluate( const in vec3 N, const in vec3 V, const in vec3 P, const in mat3 mInv, const in vec3 rectCoords[ 4 ] ) {
	vec3 v1 = rectCoords[ 1 ] - rectCoords[ 0 ];
	vec3 v2 = rectCoords[ 3 ] - rectCoords[ 0 ];
	vec3 lightNormal = cross( v1, v2 );
	if( dot( lightNormal, P - rectCoords[ 0 ] ) < 0.0 ) return vec3( 0.0 );
	vec3 T1, T2;
	T1 = normalize( V - N * dot( V, N ) );
	T2 = - cross( N, T1 );
	mat3 mat = mInv * transposeMat3( mat3( T1, T2, N ) );
	vec3 coords[ 4 ];
	coords[ 0 ] = mat * ( rectCoords[ 0 ] - P );
	coords[ 1 ] = mat * ( rectCoords[ 1 ] - P );
	coords[ 2 ] = mat * ( rectCoords[ 2 ] - P );
	coords[ 3 ] = mat * ( rectCoords[ 3 ] - P );
	coords[ 0 ] = normalize( coords[ 0 ] );
	coords[ 1 ] = normalize( coords[ 1 ] );
	coords[ 2 ] = normalize( coords[ 2 ] );
	coords[ 3 ] = normalize( coords[ 3 ] );
	vec3 vectorFormFactor = vec3( 0.0 );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 0 ], coords[ 1 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 1 ], coords[ 2 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 2 ], coords[ 3 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 3 ], coords[ 0 ] );
	float result = LTC_ClippedSphereFormFactor( vectorFormFactor );
	return vec3( result );
}
#if defined( USE_SHEEN )
float D_Charlie( float roughness, float dotNH ) {
	float alpha = pow2( roughness );
	float invAlpha = 1.0 / alpha;
	float cos2h = dotNH * dotNH;
	float sin2h = max( 1.0 - cos2h, 0.0078125 );
	return ( 2.0 + invAlpha ) * pow( sin2h, invAlpha * 0.5 ) / ( 2.0 * PI );
}
float V_Neubelt( float dotNV, float dotNL ) {
	return saturate( 1.0 / ( 4.0 * ( dotNL + dotNV - dotNL * dotNV ) ) );
}
vec3 BRDF_Sheen( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, vec3 sheenColor, const in float sheenRoughness ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float D = D_Charlie( sheenRoughness, dotNH );
	float V = V_Neubelt( dotNV, dotNL );
	return sheenColor * ( D * V );
}
#endif
float IBLSheenBRDF( const in vec3 normal, const in vec3 viewDir, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	float r2 = roughness * roughness;
	float a = roughness < 0.25 ? -339.2 * r2 + 161.4 * roughness - 25.9 : -8.48 * r2 + 14.3 * roughness - 9.95;
	float b = roughness < 0.25 ? 44.0 * r2 - 23.7 * roughness + 3.26 : 1.97 * r2 - 3.27 * roughness + 0.72;
	float DG = exp( a * dotNV + b ) + ( roughness < 0.25 ? 0.0 : 0.1 * ( roughness - 0.25 ) );
	return saturate( DG * RECIPROCAL_PI );
}
vec2 DFGApprox( const in vec3 normal, const in vec3 viewDir, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	const vec4 c0 = vec4( - 1, - 0.0275, - 0.572, 0.022 );
	const vec4 c1 = vec4( 1, 0.0425, 1.04, - 0.04 );
	vec4 r = roughness * c0 + c1;
	float a004 = min( r.x * r.x, exp2( - 9.28 * dotNV ) ) * r.x + r.y;
	vec2 fab = vec2( - 1.04, 1.04 ) * a004 + r.zw;
	return fab;
}
vec3 EnvironmentBRDF( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness ) {
	vec2 fab = DFGApprox( normal, viewDir, roughness );
	return specularColor * fab.x + specularF90 * fab.y;
}
#ifdef USE_IRIDESCENCE
void computeMultiscatteringIridescence( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float iridescence, const in vec3 iridescenceF0, const in float roughness, inout vec3 singleScatter, inout vec3 multiScatter ) {
#else
void computeMultiscattering( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness, inout vec3 singleScatter, inout vec3 multiScatter ) {
#endif
	vec2 fab = DFGApprox( normal, viewDir, roughness );
	#ifdef USE_IRIDESCENCE
		vec3 Fr = mix( specularColor, iridescenceF0, iridescence );
	#else
		vec3 Fr = specularColor;
	#endif
	vec3 FssEss = Fr * fab.x + specularF90 * fab.y;
	float Ess = fab.x + fab.y;
	float Ems = 1.0 - Ess;
	vec3 Favg = Fr + ( 1.0 - Fr ) * 0.047619;	vec3 Fms = FssEss * Favg / ( 1.0 - Ems * Favg );
	singleScatter += FssEss;
	multiScatter += Fms * Ems;
}
#if NUM_RECT_AREA_LIGHTS > 0
	void RE_Direct_RectArea_Physical( const in RectAreaLight rectAreaLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
		vec3 normal = geometryNormal;
		vec3 viewDir = geometryViewDir;
		vec3 position = geometryPosition;
		vec3 lightPos = rectAreaLight.position;
		vec3 halfWidth = rectAreaLight.halfWidth;
		vec3 halfHeight = rectAreaLight.halfHeight;
		vec3 lightColor = rectAreaLight.color;
		float roughness = material.roughness;
		vec3 rectCoords[ 4 ];
		rectCoords[ 0 ] = lightPos + halfWidth - halfHeight;		rectCoords[ 1 ] = lightPos - halfWidth - halfHeight;
		rectCoords[ 2 ] = lightPos - halfWidth + halfHeight;
		rectCoords[ 3 ] = lightPos + halfWidth + halfHeight;
		vec2 uv = LTC_Uv( normal, viewDir, roughness );
		vec4 t1 = texture2D( ltc_1, uv );
		vec4 t2 = texture2D( ltc_2, uv );
		mat3 mInv = mat3(
			vec3( t1.x, 0, t1.y ),
			vec3(    0, 1,    0 ),
			vec3( t1.z, 0, t1.w )
		);
		vec3 fresnel = ( material.specularColor * t2.x + ( vec3( 1.0 ) - material.specularColor ) * t2.y );
		reflectedLight.directSpecular += lightColor * fresnel * LTC_Evaluate( normal, viewDir, position, mInv, rectCoords );
		reflectedLight.directDiffuse += lightColor * material.diffuseColor * LTC_Evaluate( normal, viewDir, position, mat3( 1.0 ), rectCoords );
	}
#endif
void RE_Direct_Physical( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	#ifdef USE_CLEARCOAT
		float dotNLcc = saturate( dot( geometryClearcoatNormal, directLight.direction ) );
		vec3 ccIrradiance = dotNLcc * directLight.color;
		clearcoatSpecularDirect += ccIrradiance * BRDF_GGX_Clearcoat( directLight.direction, geometryViewDir, geometryClearcoatNormal, material );
	#endif
	#ifdef USE_SHEEN
		sheenSpecularDirect += irradiance * BRDF_Sheen( directLight.direction, geometryViewDir, geometryNormal, material.sheenColor, material.sheenRoughness );
	#endif
	reflectedLight.directSpecular += irradiance * BRDF_GGX( directLight.direction, geometryViewDir, geometryNormal, material );
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Physical( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectSpecular_Physical( const in vec3 radiance, const in vec3 irradiance, const in vec3 clearcoatRadiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight) {
	#ifdef USE_CLEARCOAT
		clearcoatSpecularIndirect += clearcoatRadiance * EnvironmentBRDF( geometryClearcoatNormal, geometryViewDir, material.clearcoatF0, material.clearcoatF90, material.clearcoatRoughness );
	#endif
	#ifdef USE_SHEEN
		sheenSpecularIndirect += irradiance * material.sheenColor * IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness );
	#endif
	vec3 singleScattering = vec3( 0.0 );
	vec3 multiScattering = vec3( 0.0 );
	vec3 cosineWeightedIrradiance = irradiance * RECIPROCAL_PI;
	#ifdef USE_IRIDESCENCE
		computeMultiscatteringIridescence( geometryNormal, geometryViewDir, material.specularColor, material.specularF90, material.iridescence, material.iridescenceFresnel, material.roughness, singleScattering, multiScattering );
	#else
		computeMultiscattering( geometryNormal, geometryViewDir, material.specularColor, material.specularF90, material.roughness, singleScattering, multiScattering );
	#endif
	vec3 totalScattering = singleScattering + multiScattering;
	vec3 diffuse = material.diffuseColor * ( 1.0 - max( max( totalScattering.r, totalScattering.g ), totalScattering.b ) );
	reflectedLight.indirectSpecular += radiance * singleScattering;
	reflectedLight.indirectSpecular += multiScattering * cosineWeightedIrradiance;
	reflectedLight.indirectDiffuse += diffuse * cosineWeightedIrradiance;
}
#define RE_Direct				RE_Direct_Physical
#define RE_Direct_RectArea		RE_Direct_RectArea_Physical
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Physical
#define RE_IndirectSpecular		RE_IndirectSpecular_Physical
float computeSpecularOcclusion( const in float dotNV, const in float ambientOcclusion, const in float roughness ) {
	return saturate( pow( dotNV + ambientOcclusion, exp2( - 16.0 * roughness - 1.0 ) ) - 1.0 + ambientOcclusion );
}`;
var Vh = `
vec3 geometryPosition = - vViewPosition;
vec3 geometryNormal = normal;
vec3 geometryViewDir = ( isOrthographic ) ? vec3( 0, 0, 1 ) : normalize( vViewPosition );
vec3 geometryClearcoatNormal = vec3( 0.0 );
#ifdef USE_CLEARCOAT
	geometryClearcoatNormal = clearcoatNormal;
#endif
#ifdef USE_IRIDESCENCE
	float dotNVi = saturate( dot( normal, geometryViewDir ) );
	if ( material.iridescenceThickness == 0.0 ) {
		material.iridescence = 0.0;
	} else {
		material.iridescence = saturate( material.iridescence );
	}
	if ( material.iridescence > 0.0 ) {
		material.iridescenceFresnel = evalIridescence( 1.0, material.iridescenceIOR, dotNVi, material.iridescenceThickness, material.specularColor );
		material.iridescenceF0 = Schlick_to_F0( material.iridescenceFresnel, 1.0, dotNVi );
	}
#endif
IncidentLight directLight;
#if ( NUM_POINT_LIGHTS > 0 ) && defined( RE_Direct )
	PointLight pointLight;
	#if defined( USE_SHADOWMAP ) && NUM_POINT_LIGHT_SHADOWS > 0
	PointLightShadow pointLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHTS; i ++ ) {
		pointLight = pointLights[ i ];
		getPointLightInfo( pointLight, geometryPosition, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_POINT_LIGHT_SHADOWS )
		pointLightShadow = pointLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getPointShadow( pointShadowMap[ i ], pointLightShadow.shadowMapSize, pointLightShadow.shadowIntensity, pointLightShadow.shadowBias, pointLightShadow.shadowRadius, vPointShadowCoord[ i ], pointLightShadow.shadowCameraNear, pointLightShadow.shadowCameraFar ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_SPOT_LIGHTS > 0 ) && defined( RE_Direct )
	SpotLight spotLight;
	vec4 spotColor;
	vec3 spotLightCoord;
	bool inSpotLightMap;
	#if defined( USE_SHADOWMAP ) && NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHTS; i ++ ) {
		spotLight = spotLights[ i ];
		getSpotLightInfo( spotLight, geometryPosition, directLight );
		#if ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#define SPOT_LIGHT_MAP_INDEX UNROLLED_LOOP_INDEX
		#elif ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		#define SPOT_LIGHT_MAP_INDEX NUM_SPOT_LIGHT_MAPS
		#else
		#define SPOT_LIGHT_MAP_INDEX ( UNROLLED_LOOP_INDEX - NUM_SPOT_LIGHT_SHADOWS + NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#endif
		#if ( SPOT_LIGHT_MAP_INDEX < NUM_SPOT_LIGHT_MAPS )
			spotLightCoord = vSpotLightCoord[ i ].xyz / vSpotLightCoord[ i ].w;
			inSpotLightMap = all( lessThan( abs( spotLightCoord * 2. - 1. ), vec3( 1.0 ) ) );
			spotColor = texture2D( spotLightMap[ SPOT_LIGHT_MAP_INDEX ], spotLightCoord.xy );
			directLight.color = inSpotLightMap ? directLight.color * spotColor.rgb : directLight.color;
		#endif
		#undef SPOT_LIGHT_MAP_INDEX
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		spotLightShadow = spotLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( spotShadowMap[ i ], spotLightShadow.shadowMapSize, spotLightShadow.shadowIntensity, spotLightShadow.shadowBias, spotLightShadow.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_DIR_LIGHTS > 0 ) && defined( RE_Direct )
	DirectionalLight directionalLight;
	#if defined( USE_SHADOWMAP ) && NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHTS; i ++ ) {
		directionalLight = directionalLights[ i ];
		getDirectionalLightInfo( directionalLight, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_DIR_LIGHT_SHADOWS )
		directionalLightShadow = directionalLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( directionalShadowMap[ i ], directionalLightShadow.shadowMapSize, directionalLightShadow.shadowIntensity, directionalLightShadow.shadowBias, directionalLightShadow.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_RECT_AREA_LIGHTS > 0 ) && defined( RE_Direct_RectArea )
	RectAreaLight rectAreaLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_RECT_AREA_LIGHTS; i ++ ) {
		rectAreaLight = rectAreaLights[ i ];
		RE_Direct_RectArea( rectAreaLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if defined( RE_IndirectDiffuse )
	vec3 iblIrradiance = vec3( 0.0 );
	vec3 irradiance = getAmbientLightIrradiance( ambientLightColor );
	#if defined( USE_LIGHT_PROBES )
		irradiance += getLightProbeIrradiance( lightProbe, geometryNormal );
	#endif
	#if ( NUM_HEMI_LIGHTS > 0 )
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_HEMI_LIGHTS; i ++ ) {
			irradiance += getHemisphereLightIrradiance( hemisphereLights[ i ], geometryNormal );
		}
		#pragma unroll_loop_end
	#endif
#endif
#if defined( RE_IndirectSpecular )
	vec3 radiance = vec3( 0.0 );
	vec3 clearcoatRadiance = vec3( 0.0 );
#endif`;
var kh = `#if defined( RE_IndirectDiffuse )
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		vec3 lightMapIrradiance = lightMapTexel.rgb * lightMapIntensity;
		irradiance += lightMapIrradiance;
	#endif
	#if defined( USE_ENVMAP ) && defined( STANDARD ) && defined( ENVMAP_TYPE_CUBE_UV )
		iblIrradiance += getIBLIrradiance( geometryNormal );
	#endif
#endif
#if defined( USE_ENVMAP ) && defined( RE_IndirectSpecular )
	#ifdef USE_ANISOTROPY
		radiance += getIBLAnisotropyRadiance( geometryViewDir, geometryNormal, material.roughness, material.anisotropyB, material.anisotropy );
	#else
		radiance += getIBLRadiance( geometryViewDir, geometryNormal, material.roughness );
	#endif
	#ifdef USE_CLEARCOAT
		clearcoatRadiance += getIBLRadiance( geometryViewDir, geometryClearcoatNormal, material.clearcoatRoughness );
	#endif
#endif`;
var Hh = `#if defined( RE_IndirectDiffuse )
	RE_IndirectDiffuse( irradiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif
#if defined( RE_IndirectSpecular )
	RE_IndirectSpecular( radiance, iblIrradiance, clearcoatRadiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif`;
var Gh = `#if defined( USE_LOGARITHMIC_DEPTH_BUFFER )
	gl_FragDepth = vIsPerspective == 0.0 ? gl_FragCoord.z : log2( vFragDepth ) * logDepthBufFC * 0.5;
#endif`;
var Wh = `#if defined( USE_LOGARITHMIC_DEPTH_BUFFER )
	uniform float logDepthBufFC;
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`;
var Xh = `#ifdef USE_LOGARITHMIC_DEPTH_BUFFER
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`;
var qh = `#ifdef USE_LOGARITHMIC_DEPTH_BUFFER
	vFragDepth = 1.0 + gl_Position.w;
	vIsPerspective = float( isPerspectiveMatrix( projectionMatrix ) );
#endif`;
var Yh = `#ifdef USE_MAP
	vec4 sampledDiffuseColor = texture2D( map, vMapUv );
	#ifdef DECODE_VIDEO_TEXTURE
		sampledDiffuseColor = sRGBTransferEOTF( sampledDiffuseColor );
	#endif
	diffuseColor *= sampledDiffuseColor;
#endif`;
var Zh = `#ifdef USE_MAP
	uniform sampler2D map;
#endif`;
var Jh = `#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
	#if defined( USE_POINTS_UV )
		vec2 uv = vUv;
	#else
		vec2 uv = ( uvTransform * vec3( gl_PointCoord.x, 1.0 - gl_PointCoord.y, 1 ) ).xy;
	#endif
#endif
#ifdef USE_MAP
	diffuseColor *= texture2D( map, uv );
#endif
#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, uv ).g;
#endif`;
var $h = `#if defined( USE_POINTS_UV )
	varying vec2 vUv;
#else
	#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
		uniform mat3 uvTransform;
	#endif
#endif
#ifdef USE_MAP
	uniform sampler2D map;
#endif
#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`;
var Kh = `float metalnessFactor = metalness;
#ifdef USE_METALNESSMAP
	vec4 texelMetalness = texture2D( metalnessMap, vMetalnessMapUv );
	metalnessFactor *= texelMetalness.b;
#endif`;
var Qh = `#ifdef USE_METALNESSMAP
	uniform sampler2D metalnessMap;
#endif`;
var jh = `#ifdef USE_INSTANCING_MORPH
	float morphTargetInfluences[ MORPHTARGETS_COUNT ];
	float morphTargetBaseInfluence = texelFetch( morphTexture, ivec2( 0, gl_InstanceID ), 0 ).r;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		morphTargetInfluences[i] =  texelFetch( morphTexture, ivec2( i + 1, gl_InstanceID ), 0 ).r;
	}
#endif`;
var tu = `#if defined( USE_MORPHCOLORS )
	vColor *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		#if defined( USE_COLOR_ALPHA )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ) * morphTargetInfluences[ i ];
		#elif defined( USE_COLOR )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ).rgb * morphTargetInfluences[ i ];
		#endif
	}
#endif`;
var eu = `#ifdef USE_MORPHNORMALS
	objectNormal *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) objectNormal += getMorph( gl_VertexID, i, 1 ).xyz * morphTargetInfluences[ i ];
	}
#endif`;
var nu = `#ifdef USE_MORPHTARGETS
	#ifndef USE_INSTANCING_MORPH
		uniform float morphTargetBaseInfluence;
		uniform float morphTargetInfluences[ MORPHTARGETS_COUNT ];
	#endif
	uniform sampler2DArray morphTargetsTexture;
	uniform ivec2 morphTargetsTextureSize;
	vec4 getMorph( const in int vertexIndex, const in int morphTargetIndex, const in int offset ) {
		int texelIndex = vertexIndex * MORPHTARGETS_TEXTURE_STRIDE + offset;
		int y = texelIndex / morphTargetsTextureSize.x;
		int x = texelIndex - y * morphTargetsTextureSize.x;
		ivec3 morphUV = ivec3( x, y, morphTargetIndex );
		return texelFetch( morphTargetsTexture, morphUV, 0 );
	}
#endif`;
var iu = `#ifdef USE_MORPHTARGETS
	transformed *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) transformed += getMorph( gl_VertexID, i, 0 ).xyz * morphTargetInfluences[ i ];
	}
#endif`;
var su = `float faceDirection = gl_FrontFacing ? 1.0 : - 1.0;
#ifdef FLAT_SHADED
	vec3 fdx = dFdx( vViewPosition );
	vec3 fdy = dFdy( vViewPosition );
	vec3 normal = normalize( cross( fdx, fdy ) );
#else
	vec3 normal = normalize( vNormal );
	#ifdef DOUBLE_SIDED
		normal *= faceDirection;
	#endif
#endif
#if defined( USE_NORMALMAP_TANGENTSPACE ) || defined( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY )
	#ifdef USE_TANGENT
		mat3 tbn = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn = getTangentFrame( - vViewPosition, normal,
		#if defined( USE_NORMALMAP )
			vNormalMapUv
		#elif defined( USE_CLEARCOAT_NORMALMAP )
			vClearcoatNormalMapUv
		#else
			vUv
		#endif
		);
	#endif
	#if defined( DOUBLE_SIDED ) && ! defined( FLAT_SHADED )
		tbn[0] *= faceDirection;
		tbn[1] *= faceDirection;
	#endif
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	#ifdef USE_TANGENT
		mat3 tbn2 = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn2 = getTangentFrame( - vViewPosition, normal, vClearcoatNormalMapUv );
	#endif
	#if defined( DOUBLE_SIDED ) && ! defined( FLAT_SHADED )
		tbn2[0] *= faceDirection;
		tbn2[1] *= faceDirection;
	#endif
#endif
vec3 nonPerturbedNormal = normal;`;
var ru = `#ifdef USE_NORMALMAP_OBJECTSPACE
	normal = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	#ifdef FLIP_SIDED
		normal = - normal;
	#endif
	#ifdef DOUBLE_SIDED
		normal = normal * faceDirection;
	#endif
	normal = normalize( normalMatrix * normal );
#elif defined( USE_NORMALMAP_TANGENTSPACE )
	vec3 mapN = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	mapN.xy *= normalScale;
	normal = normalize( tbn * mapN );
#elif defined( USE_BUMPMAP )
	normal = perturbNormalArb( - vViewPosition, normal, dHdxy_fwd(), faceDirection );
#endif`;
var au = `#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`;
var ou = `#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`;
var lu = `#ifndef FLAT_SHADED
	vNormal = normalize( transformedNormal );
	#ifdef USE_TANGENT
		vTangent = normalize( transformedTangent );
		vBitangent = normalize( cross( vNormal, vTangent ) * tangent.w );
	#endif
#endif`;
var cu = `#ifdef USE_NORMALMAP
	uniform sampler2D normalMap;
	uniform vec2 normalScale;
#endif
#ifdef USE_NORMALMAP_OBJECTSPACE
	uniform mat3 normalMatrix;
#endif
#if ! defined ( USE_TANGENT ) && ( defined ( USE_NORMALMAP_TANGENTSPACE ) || defined ( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY ) )
	mat3 getTangentFrame( vec3 eye_pos, vec3 surf_norm, vec2 uv ) {
		vec3 q0 = dFdx( eye_pos.xyz );
		vec3 q1 = dFdy( eye_pos.xyz );
		vec2 st0 = dFdx( uv.st );
		vec2 st1 = dFdy( uv.st );
		vec3 N = surf_norm;
		vec3 q1perp = cross( q1, N );
		vec3 q0perp = cross( N, q0 );
		vec3 T = q1perp * st0.x + q0perp * st1.x;
		vec3 B = q1perp * st0.y + q0perp * st1.y;
		float det = max( dot( T, T ), dot( B, B ) );
		float scale = ( det == 0.0 ) ? 0.0 : inversesqrt( det );
		return mat3( T * scale, B * scale, N );
	}
#endif`;
var hu = `#ifdef USE_CLEARCOAT
	vec3 clearcoatNormal = nonPerturbedNormal;
#endif`;
var uu = `#ifdef USE_CLEARCOAT_NORMALMAP
	vec3 clearcoatMapN = texture2D( clearcoatNormalMap, vClearcoatNormalMapUv ).xyz * 2.0 - 1.0;
	clearcoatMapN.xy *= clearcoatNormalScale;
	clearcoatNormal = normalize( tbn2 * clearcoatMapN );
#endif`;
var du = `#ifdef USE_CLEARCOATMAP
	uniform sampler2D clearcoatMap;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform sampler2D clearcoatNormalMap;
	uniform vec2 clearcoatNormalScale;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform sampler2D clearcoatRoughnessMap;
#endif`;
var fu = `#ifdef USE_IRIDESCENCEMAP
	uniform sampler2D iridescenceMap;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform sampler2D iridescenceThicknessMap;
#endif`;
var pu = `#ifdef OPAQUE
diffuseColor.a = 1.0;
#endif
#ifdef USE_TRANSMISSION
diffuseColor.a *= material.transmissionAlpha;
#endif
gl_FragColor = vec4( outgoingLight, diffuseColor.a );`;
var mu = `vec3 packNormalToRGB( const in vec3 normal ) {
	return normalize( normal ) * 0.5 + 0.5;
}
vec3 unpackRGBToNormal( const in vec3 rgb ) {
	return 2.0 * rgb.xyz - 1.0;
}
const float PackUpscale = 256. / 255.;const float UnpackDownscale = 255. / 256.;const float ShiftRight8 = 1. / 256.;
const float Inv255 = 1. / 255.;
const vec4 PackFactors = vec4( 1.0, 256.0, 256.0 * 256.0, 256.0 * 256.0 * 256.0 );
const vec2 UnpackFactors2 = vec2( UnpackDownscale, 1.0 / PackFactors.g );
const vec3 UnpackFactors3 = vec3( UnpackDownscale / PackFactors.rg, 1.0 / PackFactors.b );
const vec4 UnpackFactors4 = vec4( UnpackDownscale / PackFactors.rgb, 1.0 / PackFactors.a );
vec4 packDepthToRGBA( const in float v ) {
	if( v <= 0.0 )
		return vec4( 0., 0., 0., 0. );
	if( v >= 1.0 )
		return vec4( 1., 1., 1., 1. );
	float vuf;
	float af = modf( v * PackFactors.a, vuf );
	float bf = modf( vuf * ShiftRight8, vuf );
	float gf = modf( vuf * ShiftRight8, vuf );
	return vec4( vuf * Inv255, gf * PackUpscale, bf * PackUpscale, af );
}
vec3 packDepthToRGB( const in float v ) {
	if( v <= 0.0 )
		return vec3( 0., 0., 0. );
	if( v >= 1.0 )
		return vec3( 1., 1., 1. );
	float vuf;
	float bf = modf( v * PackFactors.b, vuf );
	float gf = modf( vuf * ShiftRight8, vuf );
	return vec3( vuf * Inv255, gf * PackUpscale, bf );
}
vec2 packDepthToRG( const in float v ) {
	if( v <= 0.0 )
		return vec2( 0., 0. );
	if( v >= 1.0 )
		return vec2( 1., 1. );
	float vuf;
	float gf = modf( v * 256., vuf );
	return vec2( vuf * Inv255, gf );
}
float unpackRGBAToDepth( const in vec4 v ) {
	return dot( v, UnpackFactors4 );
}
float unpackRGBToDepth( const in vec3 v ) {
	return dot( v, UnpackFactors3 );
}
float unpackRGToDepth( const in vec2 v ) {
	return v.r * UnpackFactors2.r + v.g * UnpackFactors2.g;
}
vec4 pack2HalfToRGBA( const in vec2 v ) {
	vec4 r = vec4( v.x, fract( v.x * 255.0 ), v.y, fract( v.y * 255.0 ) );
	return vec4( r.x - r.y / 255.0, r.y, r.z - r.w / 255.0, r.w );
}
vec2 unpackRGBATo2Half( const in vec4 v ) {
	return vec2( v.x + ( v.y / 255.0 ), v.z + ( v.w / 255.0 ) );
}
float viewZToOrthographicDepth( const in float viewZ, const in float near, const in float far ) {
	return ( viewZ + near ) / ( near - far );
}
float orthographicDepthToViewZ( const in float depth, const in float near, const in float far ) {
	return depth * ( near - far ) - near;
}
float viewZToPerspectiveDepth( const in float viewZ, const in float near, const in float far ) {
	return ( ( near + viewZ ) * far ) / ( ( far - near ) * viewZ );
}
float perspectiveDepthToViewZ( const in float depth, const in float near, const in float far ) {
	return ( near * far ) / ( ( far - near ) * depth - far );
}`;
var gu = `#ifdef PREMULTIPLIED_ALPHA
	gl_FragColor.rgb *= gl_FragColor.a;
#endif`;
var _u = `vec4 mvPosition = vec4( transformed, 1.0 );
#ifdef USE_BATCHING
	mvPosition = batchingMatrix * mvPosition;
#endif
#ifdef USE_INSTANCING
	mvPosition = instanceMatrix * mvPosition;
#endif
mvPosition = modelViewMatrix * mvPosition;
gl_Position = projectionMatrix * mvPosition;`;
var xu = `#ifdef DITHERING
	gl_FragColor.rgb = dithering( gl_FragColor.rgb );
#endif`;
var vu = `#ifdef DITHERING
	vec3 dithering( vec3 color ) {
		float grid_position = rand( gl_FragCoord.xy );
		vec3 dither_shift_RGB = vec3( 0.25 / 255.0, -0.25 / 255.0, 0.25 / 255.0 );
		dither_shift_RGB = mix( 2.0 * dither_shift_RGB, -2.0 * dither_shift_RGB, grid_position );
		return color + dither_shift_RGB;
	}
#endif`;
var yu = `float roughnessFactor = roughness;
#ifdef USE_ROUGHNESSMAP
	vec4 texelRoughness = texture2D( roughnessMap, vRoughnessMapUv );
	roughnessFactor *= texelRoughness.g;
#endif`;
var Mu = `#ifdef USE_ROUGHNESSMAP
	uniform sampler2D roughnessMap;
#endif`;
var Su = `#if NUM_SPOT_LIGHT_COORDS > 0
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#if NUM_SPOT_LIGHT_MAPS > 0
	uniform sampler2D spotLightMap[ NUM_SPOT_LIGHT_MAPS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
		uniform sampler2D directionalShadowMap[ NUM_DIR_LIGHT_SHADOWS ];
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		uniform sampler2D spotShadowMap[ NUM_SPOT_LIGHT_SHADOWS ];
		struct SpotLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		uniform sampler2D pointShadowMap[ NUM_POINT_LIGHT_SHADOWS ];
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
	float texture2DCompare( sampler2D depths, vec2 uv, float compare ) {
		float depth = unpackRGBAToDepth( texture2D( depths, uv ) );
		#ifdef USE_REVERSED_DEPTH_BUFFER
			return step( depth, compare );
		#else
			return step( compare, depth );
		#endif
	}
	vec2 texture2DDistribution( sampler2D shadow, vec2 uv ) {
		return unpackRGBATo2Half( texture2D( shadow, uv ) );
	}
	float VSMShadow( sampler2D shadow, vec2 uv, float compare ) {
		float occlusion = 1.0;
		vec2 distribution = texture2DDistribution( shadow, uv );
		#ifdef USE_REVERSED_DEPTH_BUFFER
			float hard_shadow = step( distribution.x, compare );
		#else
			float hard_shadow = step( compare, distribution.x );
		#endif
		if ( hard_shadow != 1.0 ) {
			float distance = compare - distribution.x;
			float variance = max( 0.00000, distribution.y * distribution.y );
			float softness_probability = variance / (variance + distance * distance );			softness_probability = clamp( ( softness_probability - 0.3 ) / ( 0.95 - 0.3 ), 0.0, 1.0 );			occlusion = clamp( max( hard_shadow, softness_probability ), 0.0, 1.0 );
		}
		return occlusion;
	}
	float getShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord ) {
		float shadow = 1.0;
		shadowCoord.xyz /= shadowCoord.w;
		shadowCoord.z += shadowBias;
		bool inFrustum = shadowCoord.x >= 0.0 && shadowCoord.x <= 1.0 && shadowCoord.y >= 0.0 && shadowCoord.y <= 1.0;
		bool frustumTest = inFrustum && shadowCoord.z <= 1.0;
		if ( frustumTest ) {
		#if defined( SHADOWMAP_TYPE_PCF )
			vec2 texelSize = vec2( 1.0 ) / shadowMapSize;
			float dx0 = - texelSize.x * shadowRadius;
			float dy0 = - texelSize.y * shadowRadius;
			float dx1 = + texelSize.x * shadowRadius;
			float dy1 = + texelSize.y * shadowRadius;
			float dx2 = dx0 / 2.0;
			float dy2 = dy0 / 2.0;
			float dx3 = dx1 / 2.0;
			float dy3 = dy1 / 2.0;
			shadow = (
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy, shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, dy1 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy1 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, dy1 ), shadowCoord.z )
			) * ( 1.0 / 17.0 );
		#elif defined( SHADOWMAP_TYPE_PCF_SOFT )
			vec2 texelSize = vec2( 1.0 ) / shadowMapSize;
			float dx = texelSize.x;
			float dy = texelSize.y;
			vec2 uv = shadowCoord.xy;
			vec2 f = fract( uv * shadowMapSize + 0.5 );
			uv -= f * texelSize;
			shadow = (
				texture2DCompare( shadowMap, uv, shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + vec2( dx, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + vec2( 0.0, dy ), shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + texelSize, shadowCoord.z ) +
				mix( texture2DCompare( shadowMap, uv + vec2( -dx, 0.0 ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, 0.0 ), shadowCoord.z ),
					 f.x ) +
				mix( texture2DCompare( shadowMap, uv + vec2( -dx, dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, dy ), shadowCoord.z ),
					 f.x ) +
				mix( texture2DCompare( shadowMap, uv + vec2( 0.0, -dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 0.0, 2.0 * dy ), shadowCoord.z ),
					 f.y ) +
				mix( texture2DCompare( shadowMap, uv + vec2( dx, -dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( dx, 2.0 * dy ), shadowCoord.z ),
					 f.y ) +
				mix( mix( texture2DCompare( shadowMap, uv + vec2( -dx, -dy ), shadowCoord.z ),
						  texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, -dy ), shadowCoord.z ),
						  f.x ),
					 mix( texture2DCompare( shadowMap, uv + vec2( -dx, 2.0 * dy ), shadowCoord.z ),
						  texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, 2.0 * dy ), shadowCoord.z ),
						  f.x ),
					 f.y )
			) * ( 1.0 / 9.0 );
		#elif defined( SHADOWMAP_TYPE_VSM )
			shadow = VSMShadow( shadowMap, shadowCoord.xy, shadowCoord.z );
		#else
			shadow = texture2DCompare( shadowMap, shadowCoord.xy, shadowCoord.z );
		#endif
		}
		return mix( 1.0, shadow, shadowIntensity );
	}
	vec2 cubeToUV( vec3 v, float texelSizeY ) {
		vec3 absV = abs( v );
		float scaleToCube = 1.0 / max( absV.x, max( absV.y, absV.z ) );
		absV *= scaleToCube;
		v *= scaleToCube * ( 1.0 - 2.0 * texelSizeY );
		vec2 planar = v.xy;
		float almostATexel = 1.5 * texelSizeY;
		float almostOne = 1.0 - almostATexel;
		if ( absV.z >= almostOne ) {
			if ( v.z > 0.0 )
				planar.x = 4.0 - v.x;
		} else if ( absV.x >= almostOne ) {
			float signX = sign( v.x );
			planar.x = v.z * signX + 2.0 * signX;
		} else if ( absV.y >= almostOne ) {
			float signY = sign( v.y );
			planar.x = v.x + 2.0 * signY + 2.0;
			planar.y = v.z * signY - 2.0;
		}
		return vec2( 0.125, 0.25 ) * planar + vec2( 0.375, 0.75 );
	}
	float getPointShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord, float shadowCameraNear, float shadowCameraFar ) {
		float shadow = 1.0;
		vec3 lightToPosition = shadowCoord.xyz;
		
		float lightToPositionLength = length( lightToPosition );
		if ( lightToPositionLength - shadowCameraFar <= 0.0 && lightToPositionLength - shadowCameraNear >= 0.0 ) {
			float dp = ( lightToPositionLength - shadowCameraNear ) / ( shadowCameraFar - shadowCameraNear );			dp += shadowBias;
			vec3 bd3D = normalize( lightToPosition );
			vec2 texelSize = vec2( 1.0 ) / ( shadowMapSize * vec2( 4.0, 2.0 ) );
			#if defined( SHADOWMAP_TYPE_PCF ) || defined( SHADOWMAP_TYPE_PCF_SOFT ) || defined( SHADOWMAP_TYPE_VSM )
				vec2 offset = vec2( - 1, 1 ) * shadowRadius * texelSize.y;
				shadow = (
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xyy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yyy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xyx, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yyx, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xxy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yxy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xxx, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yxx, texelSize.y ), dp )
				) * ( 1.0 / 9.0 );
			#else
				shadow = texture2DCompare( shadowMap, cubeToUV( bd3D, texelSize.y ), dp );
			#endif
		}
		return mix( 1.0, shadow, shadowIntensity );
	}
#endif`;
var bu = `#if NUM_SPOT_LIGHT_COORDS > 0
	uniform mat4 spotLightMatrix[ NUM_SPOT_LIGHT_COORDS ];
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
		uniform mat4 directionalShadowMatrix[ NUM_DIR_LIGHT_SHADOWS ];
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		struct SpotLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		uniform mat4 pointShadowMatrix[ NUM_POINT_LIGHT_SHADOWS ];
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
#endif`;
var Eu = `#if ( defined( USE_SHADOWMAP ) && ( NUM_DIR_LIGHT_SHADOWS > 0 || NUM_POINT_LIGHT_SHADOWS > 0 ) ) || ( NUM_SPOT_LIGHT_COORDS > 0 )
	vec3 shadowWorldNormal = inverseTransformDirection( transformedNormal, viewMatrix );
	vec4 shadowWorldPosition;
#endif
#if defined( USE_SHADOWMAP )
	#if NUM_DIR_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * directionalLightShadows[ i ].shadowNormalBias, 0 );
			vDirectionalShadowCoord[ i ] = directionalShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * pointLightShadows[ i ].shadowNormalBias, 0 );
			vPointShadowCoord[ i ] = pointShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
#endif
#if NUM_SPOT_LIGHT_COORDS > 0
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_COORDS; i ++ ) {
		shadowWorldPosition = worldPosition;
		#if ( defined( USE_SHADOWMAP ) && UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
			shadowWorldPosition.xyz += shadowWorldNormal * spotLightShadows[ i ].shadowNormalBias;
		#endif
		vSpotLightCoord[ i ] = spotLightMatrix[ i ] * shadowWorldPosition;
	}
	#pragma unroll_loop_end
#endif`;
var Tu = `float getShadowMask() {
	float shadow = 1.0;
	#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
		directionalLight = directionalLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( directionalShadowMap[ i ], directionalLight.shadowMapSize, directionalLight.shadowIntensity, directionalLight.shadowBias, directionalLight.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_SHADOWS; i ++ ) {
		spotLight = spotLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( spotShadowMap[ i ], spotLight.shadowMapSize, spotLight.shadowIntensity, spotLight.shadowBias, spotLight.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
	PointLightShadow pointLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
		pointLight = pointLightShadows[ i ];
		shadow *= receiveShadow ? getPointShadow( pointShadowMap[ i ], pointLight.shadowMapSize, pointLight.shadowIntensity, pointLight.shadowBias, pointLight.shadowRadius, vPointShadowCoord[ i ], pointLight.shadowCameraNear, pointLight.shadowCameraFar ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#endif
	return shadow;
}`;
var Au = `#ifdef USE_SKINNING
	mat4 boneMatX = getBoneMatrix( skinIndex.x );
	mat4 boneMatY = getBoneMatrix( skinIndex.y );
	mat4 boneMatZ = getBoneMatrix( skinIndex.z );
	mat4 boneMatW = getBoneMatrix( skinIndex.w );
#endif`;
var wu = `#ifdef USE_SKINNING
	uniform mat4 bindMatrix;
	uniform mat4 bindMatrixInverse;
	uniform highp sampler2D boneTexture;
	mat4 getBoneMatrix( const in float i ) {
		int size = textureSize( boneTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( boneTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( boneTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( boneTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( boneTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
#endif`;
var Cu = `#ifdef USE_SKINNING
	vec4 skinVertex = bindMatrix * vec4( transformed, 1.0 );
	vec4 skinned = vec4( 0.0 );
	skinned += boneMatX * skinVertex * skinWeight.x;
	skinned += boneMatY * skinVertex * skinWeight.y;
	skinned += boneMatZ * skinVertex * skinWeight.z;
	skinned += boneMatW * skinVertex * skinWeight.w;
	transformed = ( bindMatrixInverse * skinned ).xyz;
#endif`;
var Ru = `#ifdef USE_SKINNING
	mat4 skinMatrix = mat4( 0.0 );
	skinMatrix += skinWeight.x * boneMatX;
	skinMatrix += skinWeight.y * boneMatY;
	skinMatrix += skinWeight.z * boneMatZ;
	skinMatrix += skinWeight.w * boneMatW;
	skinMatrix = bindMatrixInverse * skinMatrix * bindMatrix;
	objectNormal = vec4( skinMatrix * vec4( objectNormal, 0.0 ) ).xyz;
	#ifdef USE_TANGENT
		objectTangent = vec4( skinMatrix * vec4( objectTangent, 0.0 ) ).xyz;
	#endif
#endif`;
var Iu = `float specularStrength;
#ifdef USE_SPECULARMAP
	vec4 texelSpecular = texture2D( specularMap, vSpecularMapUv );
	specularStrength = texelSpecular.r;
#else
	specularStrength = 1.0;
#endif`;
var Pu = `#ifdef USE_SPECULARMAP
	uniform sampler2D specularMap;
#endif`;
var Lu = `#if defined( TONE_MAPPING )
	gl_FragColor.rgb = toneMapping( gl_FragColor.rgb );
#endif`;
var Du = `#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
uniform float toneMappingExposure;
vec3 LinearToneMapping( vec3 color ) {
	return saturate( toneMappingExposure * color );
}
vec3 ReinhardToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	return saturate( color / ( vec3( 1.0 ) + color ) );
}
vec3 CineonToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	color = max( vec3( 0.0 ), color - 0.004 );
	return pow( ( color * ( 6.2 * color + 0.5 ) ) / ( color * ( 6.2 * color + 1.7 ) + 0.06 ), vec3( 2.2 ) );
}
vec3 RRTAndODTFit( vec3 v ) {
	vec3 a = v * ( v + 0.0245786 ) - 0.000090537;
	vec3 b = v * ( 0.983729 * v + 0.4329510 ) + 0.238081;
	return a / b;
}
vec3 ACESFilmicToneMapping( vec3 color ) {
	const mat3 ACESInputMat = mat3(
		vec3( 0.59719, 0.07600, 0.02840 ),		vec3( 0.35458, 0.90834, 0.13383 ),
		vec3( 0.04823, 0.01566, 0.83777 )
	);
	const mat3 ACESOutputMat = mat3(
		vec3(  1.60475, -0.10208, -0.00327 ),		vec3( -0.53108,  1.10813, -0.07276 ),
		vec3( -0.07367, -0.00605,  1.07602 )
	);
	color *= toneMappingExposure / 0.6;
	color = ACESInputMat * color;
	color = RRTAndODTFit( color );
	color = ACESOutputMat * color;
	return saturate( color );
}
const mat3 LINEAR_REC2020_TO_LINEAR_SRGB = mat3(
	vec3( 1.6605, - 0.1246, - 0.0182 ),
	vec3( - 0.5876, 1.1329, - 0.1006 ),
	vec3( - 0.0728, - 0.0083, 1.1187 )
);
const mat3 LINEAR_SRGB_TO_LINEAR_REC2020 = mat3(
	vec3( 0.6274, 0.0691, 0.0164 ),
	vec3( 0.3293, 0.9195, 0.0880 ),
	vec3( 0.0433, 0.0113, 0.8956 )
);
vec3 agxDefaultContrastApprox( vec3 x ) {
	vec3 x2 = x * x;
	vec3 x4 = x2 * x2;
	return + 15.5 * x4 * x2
		- 40.14 * x4 * x
		+ 31.96 * x4
		- 6.868 * x2 * x
		+ 0.4298 * x2
		+ 0.1191 * x
		- 0.00232;
}
vec3 AgXToneMapping( vec3 color ) {
	const mat3 AgXInsetMatrix = mat3(
		vec3( 0.856627153315983, 0.137318972929847, 0.11189821299995 ),
		vec3( 0.0951212405381588, 0.761241990602591, 0.0767994186031903 ),
		vec3( 0.0482516061458583, 0.101439036467562, 0.811302368396859 )
	);
	const mat3 AgXOutsetMatrix = mat3(
		vec3( 1.1271005818144368, - 0.1413297634984383, - 0.14132976349843826 ),
		vec3( - 0.11060664309660323, 1.157823702216272, - 0.11060664309660294 ),
		vec3( - 0.016493938717834573, - 0.016493938717834257, 1.2519364065950405 )
	);
	const float AgxMinEv = - 12.47393;	const float AgxMaxEv = 4.026069;
	color *= toneMappingExposure;
	color = LINEAR_SRGB_TO_LINEAR_REC2020 * color;
	color = AgXInsetMatrix * color;
	color = max( color, 1e-10 );	color = log2( color );
	color = ( color - AgxMinEv ) / ( AgxMaxEv - AgxMinEv );
	color = clamp( color, 0.0, 1.0 );
	color = agxDefaultContrastApprox( color );
	color = AgXOutsetMatrix * color;
	color = pow( max( vec3( 0.0 ), color ), vec3( 2.2 ) );
	color = LINEAR_REC2020_TO_LINEAR_SRGB * color;
	color = clamp( color, 0.0, 1.0 );
	return color;
}
vec3 NeutralToneMapping( vec3 color ) {
	const float StartCompression = 0.8 - 0.04;
	const float Desaturation = 0.15;
	color *= toneMappingExposure;
	float x = min( color.r, min( color.g, color.b ) );
	float offset = x < 0.08 ? x - 6.25 * x * x : 0.04;
	color -= offset;
	float peak = max( color.r, max( color.g, color.b ) );
	if ( peak < StartCompression ) return color;
	float d = 1. - StartCompression;
	float newPeak = 1. - d * d / ( peak + d - StartCompression );
	color *= newPeak / peak;
	float g = 1. - 1. / ( Desaturation * ( peak - newPeak ) + 1. );
	return mix( color, vec3( newPeak ), g );
}
vec3 CustomToneMapping( vec3 color ) { return color; }`;
var Uu = `#ifdef USE_TRANSMISSION
	material.transmission = transmission;
	material.transmissionAlpha = 1.0;
	material.thickness = thickness;
	material.attenuationDistance = attenuationDistance;
	material.attenuationColor = attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		material.transmission *= texture2D( transmissionMap, vTransmissionMapUv ).r;
	#endif
	#ifdef USE_THICKNESSMAP
		material.thickness *= texture2D( thicknessMap, vThicknessMapUv ).g;
	#endif
	vec3 pos = vWorldPosition;
	vec3 v = normalize( cameraPosition - pos );
	vec3 n = inverseTransformDirection( normal, viewMatrix );
	vec4 transmitted = getIBLVolumeRefraction(
		n, v, material.roughness, material.diffuseColor, material.specularColor, material.specularF90,
		pos, modelMatrix, viewMatrix, projectionMatrix, material.dispersion, material.ior, material.thickness,
		material.attenuationColor, material.attenuationDistance );
	material.transmissionAlpha = mix( material.transmissionAlpha, transmitted.a, material.transmission );
	totalDiffuse = mix( totalDiffuse, transmitted.rgb, material.transmission );
#endif`;
var Nu = `#ifdef USE_TRANSMISSION
	uniform float transmission;
	uniform float thickness;
	uniform float attenuationDistance;
	uniform vec3 attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		uniform sampler2D transmissionMap;
	#endif
	#ifdef USE_THICKNESSMAP
		uniform sampler2D thicknessMap;
	#endif
	uniform vec2 transmissionSamplerSize;
	uniform sampler2D transmissionSamplerMap;
	uniform mat4 modelMatrix;
	uniform mat4 projectionMatrix;
	varying vec3 vWorldPosition;
	float w0( float a ) {
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - a + 3.0 ) - 3.0 ) + 1.0 );
	}
	float w1( float a ) {
		return ( 1.0 / 6.0 ) * ( a *  a * ( 3.0 * a - 6.0 ) + 4.0 );
	}
	float w2( float a ){
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - 3.0 * a + 3.0 ) + 3.0 ) + 1.0 );
	}
	float w3( float a ) {
		return ( 1.0 / 6.0 ) * ( a * a * a );
	}
	float g0( float a ) {
		return w0( a ) + w1( a );
	}
	float g1( float a ) {
		return w2( a ) + w3( a );
	}
	float h0( float a ) {
		return - 1.0 + w1( a ) / ( w0( a ) + w1( a ) );
	}
	float h1( float a ) {
		return 1.0 + w3( a ) / ( w2( a ) + w3( a ) );
	}
	vec4 bicubic( sampler2D tex, vec2 uv, vec4 texelSize, float lod ) {
		uv = uv * texelSize.zw + 0.5;
		vec2 iuv = floor( uv );
		vec2 fuv = fract( uv );
		float g0x = g0( fuv.x );
		float g1x = g1( fuv.x );
		float h0x = h0( fuv.x );
		float h1x = h1( fuv.x );
		float h0y = h0( fuv.y );
		float h1y = h1( fuv.y );
		vec2 p0 = ( vec2( iuv.x + h0x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p1 = ( vec2( iuv.x + h1x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p2 = ( vec2( iuv.x + h0x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		vec2 p3 = ( vec2( iuv.x + h1x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		return g0( fuv.y ) * ( g0x * textureLod( tex, p0, lod ) + g1x * textureLod( tex, p1, lod ) ) +
			g1( fuv.y ) * ( g0x * textureLod( tex, p2, lod ) + g1x * textureLod( tex, p3, lod ) );
	}
	vec4 textureBicubic( sampler2D sampler, vec2 uv, float lod ) {
		vec2 fLodSize = vec2( textureSize( sampler, int( lod ) ) );
		vec2 cLodSize = vec2( textureSize( sampler, int( lod + 1.0 ) ) );
		vec2 fLodSizeInv = 1.0 / fLodSize;
		vec2 cLodSizeInv = 1.0 / cLodSize;
		vec4 fSample = bicubic( sampler, uv, vec4( fLodSizeInv, fLodSize ), floor( lod ) );
		vec4 cSample = bicubic( sampler, uv, vec4( cLodSizeInv, cLodSize ), ceil( lod ) );
		return mix( fSample, cSample, fract( lod ) );
	}
	vec3 getVolumeTransmissionRay( const in vec3 n, const in vec3 v, const in float thickness, const in float ior, const in mat4 modelMatrix ) {
		vec3 refractionVector = refract( - v, normalize( n ), 1.0 / ior );
		vec3 modelScale;
		modelScale.x = length( vec3( modelMatrix[ 0 ].xyz ) );
		modelScale.y = length( vec3( modelMatrix[ 1 ].xyz ) );
		modelScale.z = length( vec3( modelMatrix[ 2 ].xyz ) );
		return normalize( refractionVector ) * thickness * modelScale;
	}
	float applyIorToRoughness( const in float roughness, const in float ior ) {
		return roughness * clamp( ior * 2.0 - 2.0, 0.0, 1.0 );
	}
	vec4 getTransmissionSample( const in vec2 fragCoord, const in float roughness, const in float ior ) {
		float lod = log2( transmissionSamplerSize.x ) * applyIorToRoughness( roughness, ior );
		return textureBicubic( transmissionSamplerMap, fragCoord.xy, lod );
	}
	vec3 volumeAttenuation( const in float transmissionDistance, const in vec3 attenuationColor, const in float attenuationDistance ) {
		if ( isinf( attenuationDistance ) ) {
			return vec3( 1.0 );
		} else {
			vec3 attenuationCoefficient = -log( attenuationColor ) / attenuationDistance;
			vec3 transmittance = exp( - attenuationCoefficient * transmissionDistance );			return transmittance;
		}
	}
	vec4 getIBLVolumeRefraction( const in vec3 n, const in vec3 v, const in float roughness, const in vec3 diffuseColor,
		const in vec3 specularColor, const in float specularF90, const in vec3 position, const in mat4 modelMatrix,
		const in mat4 viewMatrix, const in mat4 projMatrix, const in float dispersion, const in float ior, const in float thickness,
		const in vec3 attenuationColor, const in float attenuationDistance ) {
		vec4 transmittedLight;
		vec3 transmittance;
		#ifdef USE_DISPERSION
			float halfSpread = ( ior - 1.0 ) * 0.025 * dispersion;
			vec3 iors = vec3( ior - halfSpread, ior, ior + halfSpread );
			for ( int i = 0; i < 3; i ++ ) {
				vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, iors[ i ], modelMatrix );
				vec3 refractedRayExit = position + transmissionRay;
				vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
				vec2 refractionCoords = ndcPos.xy / ndcPos.w;
				refractionCoords += 1.0;
				refractionCoords /= 2.0;
				vec4 transmissionSample = getTransmissionSample( refractionCoords, roughness, iors[ i ] );
				transmittedLight[ i ] = transmissionSample[ i ];
				transmittedLight.a += transmissionSample.a;
				transmittance[ i ] = diffuseColor[ i ] * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance )[ i ];
			}
			transmittedLight.a /= 3.0;
		#else
			vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, ior, modelMatrix );
			vec3 refractedRayExit = position + transmissionRay;
			vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
			vec2 refractionCoords = ndcPos.xy / ndcPos.w;
			refractionCoords += 1.0;
			refractionCoords /= 2.0;
			transmittedLight = getTransmissionSample( refractionCoords, roughness, ior );
			transmittance = diffuseColor * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance );
		#endif
		vec3 attenuatedColor = transmittance * transmittedLight.rgb;
		vec3 F = EnvironmentBRDF( n, v, specularColor, specularF90, roughness );
		float transmittanceFactor = ( transmittance.r + transmittance.g + transmittance.b ) / 3.0;
		return vec4( ( 1.0 - F ) * attenuatedColor, 1.0 - ( 1.0 - transmittedLight.a ) * transmittanceFactor );
	}
#endif`;
var Fu = `#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_SPECULARMAP
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`;
var Ou = `#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	uniform mat3 mapTransform;
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	uniform mat3 alphaMapTransform;
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	uniform mat3 lightMapTransform;
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	uniform mat3 aoMapTransform;
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	uniform mat3 bumpMapTransform;
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	uniform mat3 normalMapTransform;
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_DISPLACEMENTMAP
	uniform mat3 displacementMapTransform;
	varying vec2 vDisplacementMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	uniform mat3 emissiveMapTransform;
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	uniform mat3 metalnessMapTransform;
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	uniform mat3 roughnessMapTransform;
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	uniform mat3 anisotropyMapTransform;
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	uniform mat3 clearcoatMapTransform;
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform mat3 clearcoatNormalMapTransform;
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform mat3 clearcoatRoughnessMapTransform;
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	uniform mat3 sheenColorMapTransform;
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	uniform mat3 sheenRoughnessMapTransform;
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	uniform mat3 iridescenceMapTransform;
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform mat3 iridescenceThicknessMapTransform;
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SPECULARMAP
	uniform mat3 specularMapTransform;
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	uniform mat3 specularColorMapTransform;
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	uniform mat3 specularIntensityMapTransform;
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`;
var Bu = `#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	vUv = vec3( uv, 1 ).xy;
#endif
#ifdef USE_MAP
	vMapUv = ( mapTransform * vec3( MAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ALPHAMAP
	vAlphaMapUv = ( alphaMapTransform * vec3( ALPHAMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_LIGHTMAP
	vLightMapUv = ( lightMapTransform * vec3( LIGHTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_AOMAP
	vAoMapUv = ( aoMapTransform * vec3( AOMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_BUMPMAP
	vBumpMapUv = ( bumpMapTransform * vec3( BUMPMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_NORMALMAP
	vNormalMapUv = ( normalMapTransform * vec3( NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_DISPLACEMENTMAP
	vDisplacementMapUv = ( displacementMapTransform * vec3( DISPLACEMENTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_EMISSIVEMAP
	vEmissiveMapUv = ( emissiveMapTransform * vec3( EMISSIVEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_METALNESSMAP
	vMetalnessMapUv = ( metalnessMapTransform * vec3( METALNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ROUGHNESSMAP
	vRoughnessMapUv = ( roughnessMapTransform * vec3( ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ANISOTROPYMAP
	vAnisotropyMapUv = ( anisotropyMapTransform * vec3( ANISOTROPYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOATMAP
	vClearcoatMapUv = ( clearcoatMapTransform * vec3( CLEARCOATMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	vClearcoatNormalMapUv = ( clearcoatNormalMapTransform * vec3( CLEARCOAT_NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	vClearcoatRoughnessMapUv = ( clearcoatRoughnessMapTransform * vec3( CLEARCOAT_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCEMAP
	vIridescenceMapUv = ( iridescenceMapTransform * vec3( IRIDESCENCEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	vIridescenceThicknessMapUv = ( iridescenceThicknessMapTransform * vec3( IRIDESCENCE_THICKNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_COLORMAP
	vSheenColorMapUv = ( sheenColorMapTransform * vec3( SHEEN_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	vSheenRoughnessMapUv = ( sheenRoughnessMapTransform * vec3( SHEEN_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULARMAP
	vSpecularMapUv = ( specularMapTransform * vec3( SPECULARMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_COLORMAP
	vSpecularColorMapUv = ( specularColorMapTransform * vec3( SPECULAR_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	vSpecularIntensityMapUv = ( specularIntensityMapTransform * vec3( SPECULAR_INTENSITYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_TRANSMISSIONMAP
	vTransmissionMapUv = ( transmissionMapTransform * vec3( TRANSMISSIONMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_THICKNESSMAP
	vThicknessMapUv = ( thicknessMapTransform * vec3( THICKNESSMAP_UV, 1 ) ).xy;
#endif`;
var zu = `#if defined( USE_ENVMAP ) || defined( DISTANCE ) || defined ( USE_SHADOWMAP ) || defined ( USE_TRANSMISSION ) || NUM_SPOT_LIGHT_COORDS > 0
	vec4 worldPosition = vec4( transformed, 1.0 );
	#ifdef USE_BATCHING
		worldPosition = batchingMatrix * worldPosition;
	#endif
	#ifdef USE_INSTANCING
		worldPosition = instanceMatrix * worldPosition;
	#endif
	worldPosition = modelMatrix * worldPosition;
#endif`;
var Vu = `varying vec2 vUv;
uniform mat3 uvTransform;
void main() {
	vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	gl_Position = vec4( position.xy, 1.0, 1.0 );
}`;
var ku = `uniform sampler2D t2D;
uniform float backgroundIntensity;
varying vec2 vUv;
void main() {
	vec4 texColor = texture2D( t2D, vUv );
	#ifdef DECODE_VIDEO_TEXTURE
		texColor = vec4( mix( pow( texColor.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), texColor.rgb * 0.0773993808, vec3( lessThanEqual( texColor.rgb, vec3( 0.04045 ) ) ) ), texColor.w );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`;
var Hu = `varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`;
var Gu = `#ifdef ENVMAP_TYPE_CUBE
	uniform samplerCube envMap;
#elif defined( ENVMAP_TYPE_CUBE_UV )
	uniform sampler2D envMap;
#endif
uniform float flipEnvMap;
uniform float backgroundBlurriness;
uniform float backgroundIntensity;
uniform mat3 backgroundRotation;
varying vec3 vWorldDirection;
#include <cube_uv_reflection_fragment>
void main() {
	#ifdef ENVMAP_TYPE_CUBE
		vec4 texColor = textureCube( envMap, backgroundRotation * vec3( flipEnvMap * vWorldDirection.x, vWorldDirection.yz ) );
	#elif defined( ENVMAP_TYPE_CUBE_UV )
		vec4 texColor = textureCubeUV( envMap, backgroundRotation * vWorldDirection, backgroundBlurriness );
	#else
		vec4 texColor = vec4( 0.0, 0.0, 0.0, 1.0 );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`;
var Wu = `varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`;
var Xu = `uniform samplerCube tCube;
uniform float tFlip;
uniform float opacity;
varying vec3 vWorldDirection;
void main() {
	vec4 texColor = textureCube( tCube, vec3( tFlip * vWorldDirection.x, vWorldDirection.yz ) );
	gl_FragColor = texColor;
	gl_FragColor.a *= opacity;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`;
var qu = `#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
varying vec2 vHighPrecisionZW;
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#include <morphinstance_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vHighPrecisionZW = gl_Position.zw;
}`;
var Yu = `#if DEPTH_PACKING == 3200
	uniform float opacity;
#endif
#include <common>
#include <packing>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
varying vec2 vHighPrecisionZW;
void main() {
	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>
	#if DEPTH_PACKING == 3200
		diffuseColor.a = opacity;
	#endif
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <logdepthbuf_fragment>
	#ifdef USE_REVERSED_DEPTH_BUFFER
		float fragCoordZ = vHighPrecisionZW[ 0 ] / vHighPrecisionZW[ 1 ];
	#else
		float fragCoordZ = 0.5 * vHighPrecisionZW[ 0 ] / vHighPrecisionZW[ 1 ] + 0.5;
	#endif
	#if DEPTH_PACKING == 3200
		gl_FragColor = vec4( vec3( 1.0 - fragCoordZ ), opacity );
	#elif DEPTH_PACKING == 3201
		gl_FragColor = packDepthToRGBA( fragCoordZ );
	#elif DEPTH_PACKING == 3202
		gl_FragColor = vec4( packDepthToRGB( fragCoordZ ), 1.0 );
	#elif DEPTH_PACKING == 3203
		gl_FragColor = vec4( packDepthToRG( fragCoordZ ), 0.0, 1.0 );
	#endif
}`;
var Zu = `#define DISTANCE
varying vec3 vWorldPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#include <morphinstance_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <worldpos_vertex>
	#include <clipping_planes_vertex>
	vWorldPosition = worldPosition.xyz;
}`;
var Ju = `#define DISTANCE
uniform vec3 referencePosition;
uniform float nearDistance;
uniform float farDistance;
varying vec3 vWorldPosition;
#include <common>
#include <packing>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <clipping_planes_pars_fragment>
void main () {
	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	float dist = length( vWorldPosition - referencePosition );
	dist = ( dist - nearDistance ) / ( farDistance - nearDistance );
	dist = saturate( dist );
	gl_FragColor = packDepthToRGBA( dist );
}`;
var $u = `varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
}`;
var Ku = `uniform sampler2D tEquirect;
varying vec3 vWorldDirection;
#include <common>
void main() {
	vec3 direction = normalize( vWorldDirection );
	vec2 sampleUV = equirectUv( direction );
	gl_FragColor = texture2D( tEquirect, sampleUV );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`;
var Qu = `uniform float scale;
attribute float lineDistance;
varying float vLineDistance;
#include <common>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	vLineDistance = scale * lineDistance;
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`;
var ju = `uniform vec3 diffuse;
uniform float opacity;
uniform float dashSize;
uniform float totalSize;
varying float vLineDistance;
#include <common>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	if ( mod( vLineDistance, totalSize ) > dashSize ) {
		discard;
	}
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`;
var td = `#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#if defined ( USE_ENVMAP ) || defined ( USE_SKINNING )
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinbase_vertex>
		#include <skinnormal_vertex>
		#include <defaultnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <fog_vertex>
}`;
var ed = `uniform vec3 diffuse;
uniform float opacity;
#ifndef FLAT_SHADED
	varying vec3 vNormal;
#endif
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		reflectedLight.indirectDiffuse += lightMapTexel.rgb * lightMapIntensity * RECIPROCAL_PI;
	#else
		reflectedLight.indirectDiffuse += vec3( 1.0 );
	#endif
	#include <aomap_fragment>
	reflectedLight.indirectDiffuse *= diffuseColor.rgb;
	vec3 outgoingLight = reflectedLight.indirectDiffuse;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`;
var nd = `#define LAMBERT
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`;
var id = `#define LAMBERT
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_lambert_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_lambert_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`;
var sd = `#define MATCAP
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <displacementmap_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
	vViewPosition = - mvPosition.xyz;
}`;
var rd = `#define MATCAP
uniform vec3 diffuse;
uniform float opacity;
uniform sampler2D matcap;
varying vec3 vViewPosition;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	vec3 viewDir = normalize( vViewPosition );
	vec3 x = normalize( vec3( viewDir.z, 0.0, - viewDir.x ) );
	vec3 y = cross( viewDir, x );
	vec2 uv = vec2( dot( x, normal ), dot( y, normal ) ) * 0.495 + 0.5;
	#ifdef USE_MATCAP
		vec4 matcapColor = texture2D( matcap, uv );
	#else
		vec4 matcapColor = vec4( vec3( mix( 0.2, 0.8, uv.y ) ), 1.0 );
	#endif
	vec3 outgoingLight = diffuseColor.rgb * matcapColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`;
var ad = `#define NORMAL
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	vViewPosition = - mvPosition.xyz;
#endif
}`;
var od = `#define NORMAL
uniform float opacity;
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <packing>
#include <uv_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( 0.0, 0.0, 0.0, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	gl_FragColor = vec4( packNormalToRGB( normal ), diffuseColor.a );
	#ifdef OPAQUE
		gl_FragColor.a = 1.0;
	#endif
}`;
var ld = `#define PHONG
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`;
var cd = `#define PHONG
uniform vec3 diffuse;
uniform vec3 emissive;
uniform vec3 specular;
uniform float shininess;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_phong_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_phong_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + reflectedLight.directSpecular + reflectedLight.indirectSpecular + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`;
var hd = `#define STANDARD
varying vec3 vViewPosition;
#ifdef USE_TRANSMISSION
	varying vec3 vWorldPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
#ifdef USE_TRANSMISSION
	vWorldPosition = worldPosition.xyz;
#endif
}`;
var ud = `#define STANDARD
#ifdef PHYSICAL
	#define IOR
	#define USE_SPECULAR
#endif
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float roughness;
uniform float metalness;
uniform float opacity;
#ifdef IOR
	uniform float ior;
#endif
#ifdef USE_SPECULAR
	uniform float specularIntensity;
	uniform vec3 specularColor;
	#ifdef USE_SPECULAR_COLORMAP
		uniform sampler2D specularColorMap;
	#endif
	#ifdef USE_SPECULAR_INTENSITYMAP
		uniform sampler2D specularIntensityMap;
	#endif
#endif
#ifdef USE_CLEARCOAT
	uniform float clearcoat;
	uniform float clearcoatRoughness;
#endif
#ifdef USE_DISPERSION
	uniform float dispersion;
#endif
#ifdef USE_IRIDESCENCE
	uniform float iridescence;
	uniform float iridescenceIOR;
	uniform float iridescenceThicknessMinimum;
	uniform float iridescenceThicknessMaximum;
#endif
#ifdef USE_SHEEN
	uniform vec3 sheenColor;
	uniform float sheenRoughness;
	#ifdef USE_SHEEN_COLORMAP
		uniform sampler2D sheenColorMap;
	#endif
	#ifdef USE_SHEEN_ROUGHNESSMAP
		uniform sampler2D sheenRoughnessMap;
	#endif
#endif
#ifdef USE_ANISOTROPY
	uniform vec2 anisotropyVector;
	#ifdef USE_ANISOTROPYMAP
		uniform sampler2D anisotropyMap;
	#endif
#endif
varying vec3 vViewPosition;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <iridescence_fragment>
#include <cube_uv_reflection_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_physical_pars_fragment>
#include <fog_pars_fragment>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_physical_pars_fragment>
#include <transmission_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <clearcoat_pars_fragment>
#include <iridescence_pars_fragment>
#include <roughnessmap_pars_fragment>
#include <metalnessmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <roughnessmap_fragment>
	#include <metalnessmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <clearcoat_normal_fragment_begin>
	#include <clearcoat_normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_physical_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 totalDiffuse = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse;
	vec3 totalSpecular = reflectedLight.directSpecular + reflectedLight.indirectSpecular;
	#include <transmission_fragment>
	vec3 outgoingLight = totalDiffuse + totalSpecular + totalEmissiveRadiance;
	#ifdef USE_SHEEN
		float sheenEnergyComp = 1.0 - 0.157 * max3( material.sheenColor );
		outgoingLight = outgoingLight * sheenEnergyComp + sheenSpecularDirect + sheenSpecularIndirect;
	#endif
	#ifdef USE_CLEARCOAT
		float dotNVcc = saturate( dot( geometryClearcoatNormal, geometryViewDir ) );
		vec3 Fcc = F_Schlick( material.clearcoatF0, material.clearcoatF90, dotNVcc );
		outgoingLight = outgoingLight * ( 1.0 - material.clearcoat * Fcc ) + ( clearcoatSpecularDirect + clearcoatSpecularIndirect ) * material.clearcoat;
	#endif
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`;
var dd = `#define TOON
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`;
var fd = `#define TOON
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <gradientmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_toon_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_toon_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`;
var pd = `uniform float size;
uniform float scale;
#include <common>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
#ifdef USE_POINTS_UV
	varying vec2 vUv;
	uniform mat3 uvTransform;
#endif
void main() {
	#ifdef USE_POINTS_UV
		vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	#endif
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	gl_PointSize = size;
	#ifdef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) gl_PointSize *= ( scale / - mvPosition.z );
	#endif
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <fog_vertex>
}`;
var md = `uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <color_pars_fragment>
#include <map_particle_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_particle_fragment>
	#include <color_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`;
var gd = `#include <common>
#include <batching_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <shadowmap_pars_vertex>
void main() {
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`;
var _d = `uniform vec3 color;
uniform float opacity;
#include <common>
#include <packing>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <logdepthbuf_pars_fragment>
#include <shadowmap_pars_fragment>
#include <shadowmask_pars_fragment>
void main() {
	#include <logdepthbuf_fragment>
	gl_FragColor = vec4( color, opacity * ( 1.0 - getShadowMask() ) );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
}`;
var xd = `uniform float rotation;
uniform vec2 center;
#include <common>
#include <uv_pars_vertex>
#include <fog_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	vec4 mvPosition = modelViewMatrix[ 3 ];
	vec2 scale = vec2( length( modelMatrix[ 0 ].xyz ), length( modelMatrix[ 1 ].xyz ) );
	#ifndef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) scale *= - mvPosition.z;
	#endif
	vec2 alignedPosition = ( position.xy - ( center - vec2( 0.5 ) ) ) * scale;
	vec2 rotatedPosition;
	rotatedPosition.x = cos( rotation ) * alignedPosition.x - sin( rotation ) * alignedPosition.y;
	rotatedPosition.y = sin( rotation ) * alignedPosition.x + cos( rotation ) * alignedPosition.y;
	mvPosition.xy += rotatedPosition;
	gl_Position = projectionMatrix * mvPosition;
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`;
var vd = `uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
}`;
var Nt = { alphahash_fragment: kc, alphahash_pars_fragment: Hc, alphamap_fragment: Gc, alphamap_pars_fragment: Wc, alphatest_fragment: Xc, alphatest_pars_fragment: qc, aomap_fragment: Yc, aomap_pars_fragment: Zc, batching_pars_vertex: Jc, batching_vertex: $c, begin_vertex: Kc, beginnormal_vertex: Qc, bsdfs: jc, iridescence_fragment: th, bumpmap_pars_fragment: eh, clipping_planes_fragment: nh, clipping_planes_pars_fragment: ih, clipping_planes_pars_vertex: sh, clipping_planes_vertex: rh, color_fragment: ah, color_pars_fragment: oh, color_pars_vertex: lh, color_vertex: ch, common: hh, cube_uv_reflection_fragment: uh, defaultnormal_vertex: dh, displacementmap_pars_vertex: fh, displacementmap_vertex: ph, emissivemap_fragment: mh, emissivemap_pars_fragment: gh, colorspace_fragment: _h, colorspace_pars_fragment: xh, envmap_fragment: vh, envmap_common_pars_fragment: yh, envmap_pars_fragment: Mh, envmap_pars_vertex: Sh, envmap_physical_pars_fragment: Dh, envmap_vertex: bh, fog_vertex: Eh, fog_pars_vertex: Th, fog_fragment: Ah, fog_pars_fragment: wh, gradientmap_pars_fragment: Ch, lightmap_pars_fragment: Rh, lights_lambert_fragment: Ih, lights_lambert_pars_fragment: Ph, lights_pars_begin: Lh, lights_toon_fragment: Uh, lights_toon_pars_fragment: Nh, lights_phong_fragment: Fh, lights_phong_pars_fragment: Oh, lights_physical_fragment: Bh, lights_physical_pars_fragment: zh, lights_fragment_begin: Vh, lights_fragment_maps: kh, lights_fragment_end: Hh, logdepthbuf_fragment: Gh, logdepthbuf_pars_fragment: Wh, logdepthbuf_pars_vertex: Xh, logdepthbuf_vertex: qh, map_fragment: Yh, map_pars_fragment: Zh, map_particle_fragment: Jh, map_particle_pars_fragment: $h, metalnessmap_fragment: Kh, metalnessmap_pars_fragment: Qh, morphinstance_vertex: jh, morphcolor_vertex: tu, morphnormal_vertex: eu, morphtarget_pars_vertex: nu, morphtarget_vertex: iu, normal_fragment_begin: su, normal_fragment_maps: ru, normal_pars_fragment: au, normal_pars_vertex: ou, normal_vertex: lu, normalmap_pars_fragment: cu, clearcoat_normal_fragment_begin: hu, clearcoat_normal_fragment_maps: uu, clearcoat_pars_fragment: du, iridescence_pars_fragment: fu, opaque_fragment: pu, packing: mu, premultiplied_alpha_fragment: gu, project_vertex: _u, dithering_fragment: xu, dithering_pars_fragment: vu, roughnessmap_fragment: yu, roughnessmap_pars_fragment: Mu, shadowmap_pars_fragment: Su, shadowmap_pars_vertex: bu, shadowmap_vertex: Eu, shadowmask_pars_fragment: Tu, skinbase_vertex: Au, skinning_pars_vertex: wu, skinning_vertex: Cu, skinnormal_vertex: Ru, specularmap_fragment: Iu, specularmap_pars_fragment: Pu, tonemapping_fragment: Lu, tonemapping_pars_fragment: Du, transmission_fragment: Uu, transmission_pars_fragment: Nu, uv_pars_fragment: Fu, uv_pars_vertex: Ou, uv_vertex: Bu, worldpos_vertex: zu, background_vert: Vu, background_frag: ku, backgroundCube_vert: Hu, backgroundCube_frag: Gu, cube_vert: Wu, cube_frag: Xu, depth_vert: qu, depth_frag: Yu, distanceRGBA_vert: Zu, distanceRGBA_frag: Ju, equirect_vert: $u, equirect_frag: Ku, linedashed_vert: Qu, linedashed_frag: ju, meshbasic_vert: td, meshbasic_frag: ed, meshlambert_vert: nd, meshlambert_frag: id, meshmatcap_vert: sd, meshmatcap_frag: rd, meshnormal_vert: ad, meshnormal_frag: od, meshphong_vert: ld, meshphong_frag: cd, meshphysical_vert: hd, meshphysical_frag: ud, meshtoon_vert: dd, meshtoon_frag: fd, points_vert: pd, points_frag: md, shadow_vert: gd, shadow_frag: _d, sprite_vert: xd, sprite_frag: vd };
var st = { common: { diffuse: { value: new Vt(16777215) }, opacity: { value: 1 }, map: { value: null }, mapTransform: { value: new Lt() }, alphaMap: { value: null }, alphaMapTransform: { value: new Lt() }, alphaTest: { value: 0 } }, specularmap: { specularMap: { value: null }, specularMapTransform: { value: new Lt() } }, envmap: { envMap: { value: null }, envMapRotation: { value: new Lt() }, flipEnvMap: { value: -1 }, reflectivity: { value: 1 }, ior: { value: 1.5 }, refractionRatio: { value: 0.98 } }, aomap: { aoMap: { value: null }, aoMapIntensity: { value: 1 }, aoMapTransform: { value: new Lt() } }, lightmap: { lightMap: { value: null }, lightMapIntensity: { value: 1 }, lightMapTransform: { value: new Lt() } }, bumpmap: { bumpMap: { value: null }, bumpMapTransform: { value: new Lt() }, bumpScale: { value: 1 } }, normalmap: { normalMap: { value: null }, normalMapTransform: { value: new Lt() }, normalScale: { value: new Gt(1, 1) } }, displacementmap: { displacementMap: { value: null }, displacementMapTransform: { value: new Lt() }, displacementScale: { value: 1 }, displacementBias: { value: 0 } }, emissivemap: { emissiveMap: { value: null }, emissiveMapTransform: { value: new Lt() } }, metalnessmap: { metalnessMap: { value: null }, metalnessMapTransform: { value: new Lt() } }, roughnessmap: { roughnessMap: { value: null }, roughnessMapTransform: { value: new Lt() } }, gradientmap: { gradientMap: { value: null } }, fog: { fogDensity: { value: 25e-5 }, fogNear: { value: 1 }, fogFar: { value: 2e3 }, fogColor: { value: new Vt(16777215) } }, lights: { ambientLightColor: { value: [] }, lightProbe: { value: [] }, directionalLights: { value: [], properties: { direction: {}, color: {} } }, directionalLightShadows: { value: [], properties: { shadowIntensity: 1, shadowBias: {}, shadowNormalBias: {}, shadowRadius: {}, shadowMapSize: {} } }, directionalShadowMap: { value: [] }, directionalShadowMatrix: { value: [] }, spotLights: { value: [], properties: { color: {}, position: {}, direction: {}, distance: {}, coneCos: {}, penumbraCos: {}, decay: {} } }, spotLightShadows: { value: [], properties: { shadowIntensity: 1, shadowBias: {}, shadowNormalBias: {}, shadowRadius: {}, shadowMapSize: {} } }, spotLightMap: { value: [] }, spotShadowMap: { value: [] }, spotLightMatrix: { value: [] }, pointLights: { value: [], properties: { color: {}, position: {}, decay: {}, distance: {} } }, pointLightShadows: { value: [], properties: { shadowIntensity: 1, shadowBias: {}, shadowNormalBias: {}, shadowRadius: {}, shadowMapSize: {}, shadowCameraNear: {}, shadowCameraFar: {} } }, pointShadowMap: { value: [] }, pointShadowMatrix: { value: [] }, hemisphereLights: { value: [], properties: { direction: {}, skyColor: {}, groundColor: {} } }, rectAreaLights: { value: [], properties: { color: {}, position: {}, width: {}, height: {} } }, ltc_1: { value: null }, ltc_2: { value: null } }, points: { diffuse: { value: new Vt(16777215) }, opacity: { value: 1 }, size: { value: 1 }, scale: { value: 1 }, map: { value: null }, alphaMap: { value: null }, alphaMapTransform: { value: new Lt() }, alphaTest: { value: 0 }, uvTransform: { value: new Lt() } }, sprite: { diffuse: { value: new Vt(16777215) }, opacity: { value: 1 }, center: { value: new Gt(0.5, 0.5) }, rotation: { value: 0 }, map: { value: null }, mapTransform: { value: new Lt() }, alphaMap: { value: null }, alphaMapTransform: { value: new Lt() }, alphaTest: { value: 0 } } };
var Qe = { basic: { uniforms: ge([st.common, st.specularmap, st.envmap, st.aomap, st.lightmap, st.fog]), vertexShader: Nt.meshbasic_vert, fragmentShader: Nt.meshbasic_frag }, lambert: { uniforms: ge([st.common, st.specularmap, st.envmap, st.aomap, st.lightmap, st.emissivemap, st.bumpmap, st.normalmap, st.displacementmap, st.fog, st.lights, { emissive: { value: new Vt(0) } }]), vertexShader: Nt.meshlambert_vert, fragmentShader: Nt.meshlambert_frag }, phong: { uniforms: ge([st.common, st.specularmap, st.envmap, st.aomap, st.lightmap, st.emissivemap, st.bumpmap, st.normalmap, st.displacementmap, st.fog, st.lights, { emissive: { value: new Vt(0) }, specular: { value: new Vt(1118481) }, shininess: { value: 30 } }]), vertexShader: Nt.meshphong_vert, fragmentShader: Nt.meshphong_frag }, standard: { uniforms: ge([st.common, st.envmap, st.aomap, st.lightmap, st.emissivemap, st.bumpmap, st.normalmap, st.displacementmap, st.roughnessmap, st.metalnessmap, st.fog, st.lights, { emissive: { value: new Vt(0) }, roughness: { value: 1 }, metalness: { value: 0 }, envMapIntensity: { value: 1 } }]), vertexShader: Nt.meshphysical_vert, fragmentShader: Nt.meshphysical_frag }, toon: { uniforms: ge([st.common, st.aomap, st.lightmap, st.emissivemap, st.bumpmap, st.normalmap, st.displacementmap, st.gradientmap, st.fog, st.lights, { emissive: { value: new Vt(0) } }]), vertexShader: Nt.meshtoon_vert, fragmentShader: Nt.meshtoon_frag }, matcap: { uniforms: ge([st.common, st.bumpmap, st.normalmap, st.displacementmap, st.fog, { matcap: { value: null } }]), vertexShader: Nt.meshmatcap_vert, fragmentShader: Nt.meshmatcap_frag }, points: { uniforms: ge([st.points, st.fog]), vertexShader: Nt.points_vert, fragmentShader: Nt.points_frag }, dashed: { uniforms: ge([st.common, st.fog, { scale: { value: 1 }, dashSize: { value: 1 }, totalSize: { value: 2 } }]), vertexShader: Nt.linedashed_vert, fragmentShader: Nt.linedashed_frag }, depth: { uniforms: ge([st.common, st.displacementmap]), vertexShader: Nt.depth_vert, fragmentShader: Nt.depth_frag }, normal: { uniforms: ge([st.common, st.bumpmap, st.normalmap, st.displacementmap, { opacity: { value: 1 } }]), vertexShader: Nt.meshnormal_vert, fragmentShader: Nt.meshnormal_frag }, sprite: { uniforms: ge([st.sprite, st.fog]), vertexShader: Nt.sprite_vert, fragmentShader: Nt.sprite_frag }, background: { uniforms: { uvTransform: { value: new Lt() }, t2D: { value: null }, backgroundIntensity: { value: 1 } }, vertexShader: Nt.background_vert, fragmentShader: Nt.background_frag }, backgroundCube: { uniforms: { envMap: { value: null }, flipEnvMap: { value: -1 }, backgroundBlurriness: { value: 0 }, backgroundIntensity: { value: 1 }, backgroundRotation: { value: new Lt() } }, vertexShader: Nt.backgroundCube_vert, fragmentShader: Nt.backgroundCube_frag }, cube: { uniforms: { tCube: { value: null }, tFlip: { value: -1 }, opacity: { value: 1 } }, vertexShader: Nt.cube_vert, fragmentShader: Nt.cube_frag }, equirect: { uniforms: { tEquirect: { value: null } }, vertexShader: Nt.equirect_vert, fragmentShader: Nt.equirect_frag }, distanceRGBA: { uniforms: ge([st.common, st.displacementmap, { referencePosition: { value: new F() }, nearDistance: { value: 1 }, farDistance: { value: 1e3 } }]), vertexShader: Nt.distanceRGBA_vert, fragmentShader: Nt.distanceRGBA_frag }, shadow: { uniforms: ge([st.lights, st.fog, { color: { value: new Vt(0) }, opacity: { value: 1 } }]), vertexShader: Nt.shadow_vert, fragmentShader: Nt.shadow_frag } };
Qe.physical = { uniforms: ge([Qe.standard.uniforms, { clearcoat: { value: 0 }, clearcoatMap: { value: null }, clearcoatMapTransform: { value: new Lt() }, clearcoatNormalMap: { value: null }, clearcoatNormalMapTransform: { value: new Lt() }, clearcoatNormalScale: { value: new Gt(1, 1) }, clearcoatRoughness: { value: 0 }, clearcoatRoughnessMap: { value: null }, clearcoatRoughnessMapTransform: { value: new Lt() }, dispersion: { value: 0 }, iridescence: { value: 0 }, iridescenceMap: { value: null }, iridescenceMapTransform: { value: new Lt() }, iridescenceIOR: { value: 1.3 }, iridescenceThicknessMinimum: { value: 100 }, iridescenceThicknessMaximum: { value: 400 }, iridescenceThicknessMap: { value: null }, iridescenceThicknessMapTransform: { value: new Lt() }, sheen: { value: 0 }, sheenColor: { value: new Vt(0) }, sheenColorMap: { value: null }, sheenColorMapTransform: { value: new Lt() }, sheenRoughness: { value: 1 }, sheenRoughnessMap: { value: null }, sheenRoughnessMapTransform: { value: new Lt() }, transmission: { value: 0 }, transmissionMap: { value: null }, transmissionMapTransform: { value: new Lt() }, transmissionSamplerSize: { value: new Gt() }, transmissionSamplerMap: { value: null }, thickness: { value: 0 }, thicknessMap: { value: null }, thicknessMapTransform: { value: new Lt() }, attenuationDistance: { value: 0 }, attenuationColor: { value: new Vt(0) }, specularColor: { value: new Vt(1, 1, 1) }, specularColorMap: { value: null }, specularColorMapTransform: { value: new Lt() }, specularIntensity: { value: 1 }, specularIntensityMap: { value: null }, specularIntensityMapTransform: { value: new Lt() }, anisotropyVector: { value: new Gt() }, anisotropyMap: { value: null }, anisotropyMapTransform: { value: new Lt() } }]), vertexShader: Nt.meshphysical_vert, fragmentShader: Nt.meshphysical_frag };
var zr = { r: 0, b: 0, g: 0 };
var Xn = new He();
var yd = new oe();
function Md(i14, t3, e, n, s, r, a) {
  let o = new Vt(0), c = r === true ? 0 : 1, l, u, d = null, f = 0, m = null;
  function x(T) {
    let b = T.isScene === true ? T.background : null;
    return b && b.isTexture && (b = (T.backgroundBlurriness > 0 ? e : t3).get(b)), b;
  }
  function v(T) {
    let b = false, R = x(T);
    R === null ? h(o, c) : R && R.isColor && (h(R, 1), b = true);
    let w = i14.xr.getEnvironmentBlendMode();
    w === "additive" ? n.buffers.color.setClear(0, 0, 0, 1, a) : w === "alpha-blend" && n.buffers.color.setClear(0, 0, 0, 0, a), (i14.autoClear || b) && (n.buffers.depth.setTest(true), n.buffers.depth.setMask(true), n.buffers.color.setMask(true), i14.clear(i14.autoClearColor, i14.autoClearDepth, i14.autoClearStencil));
  }
  function p(T, b) {
    let R = x(b);
    R && (R.isCubeTexture || R.mapping === qi) ? (u === void 0 && (u = new Ie(new Vn(1, 1, 1), new Ge({ name: "BackgroundCubeMaterial", uniforms: Wn(Qe.backgroundCube.uniforms), vertexShader: Qe.backgroundCube.vertexShader, fragmentShader: Qe.backgroundCube.fragmentShader, side: ve, depthTest: false, depthWrite: false, fog: false, allowOverride: false })), u.geometry.deleteAttribute("normal"), u.geometry.deleteAttribute("uv"), u.onBeforeRender = function(w, P, N) {
      this.matrixWorld.copyPosition(N.matrixWorld);
    }, Object.defineProperty(u.material, "envMap", { get: function() {
      return this.uniforms.envMap.value;
    } }), s.update(u)), Xn.copy(b.backgroundRotation), Xn.x *= -1, Xn.y *= -1, Xn.z *= -1, R.isCubeTexture && R.isRenderTargetTexture === false && (Xn.y *= -1, Xn.z *= -1), u.material.uniforms.envMap.value = R, u.material.uniforms.flipEnvMap.value = R.isCubeTexture && R.isRenderTargetTexture === false ? -1 : 1, u.material.uniforms.backgroundBlurriness.value = b.backgroundBlurriness, u.material.uniforms.backgroundIntensity.value = b.backgroundIntensity, u.material.uniforms.backgroundRotation.value.setFromMatrix4(yd.makeRotationFromEuler(Xn)), u.material.toneMapped = kt.getTransfer(R.colorSpace) !== qt, (d !== R || f !== R.version || m !== i14.toneMapping) && (u.material.needsUpdate = true, d = R, f = R.version, m = i14.toneMapping), u.layers.enableAll(), T.unshift(u, u.geometry, u.material, 0, 0, null)) : R && R.isTexture && (l === void 0 && (l = new Ie(new Gi(2, 2), new Ge({ name: "BackgroundMaterial", uniforms: Wn(Qe.background.uniforms), vertexShader: Qe.background.vertexShader, fragmentShader: Qe.background.fragmentShader, side: on, depthTest: false, depthWrite: false, fog: false, allowOverride: false })), l.geometry.deleteAttribute("normal"), Object.defineProperty(l.material, "map", { get: function() {
      return this.uniforms.t2D.value;
    } }), s.update(l)), l.material.uniforms.t2D.value = R, l.material.uniforms.backgroundIntensity.value = b.backgroundIntensity, l.material.toneMapped = kt.getTransfer(R.colorSpace) !== qt, R.matrixAutoUpdate === true && R.updateMatrix(), l.material.uniforms.uvTransform.value.copy(R.matrix), (d !== R || f !== R.version || m !== i14.toneMapping) && (l.material.needsUpdate = true, d = R, f = R.version, m = i14.toneMapping), l.layers.enableAll(), T.unshift(l, l.geometry, l.material, 0, 0, null));
  }
  function h(T, b) {
    T.getRGB(zr, Wa(i14)), n.buffers.color.setClear(zr.r, zr.g, zr.b, b, a);
  }
  function A() {
    u !== void 0 && (u.geometry.dispose(), u.material.dispose(), u = void 0), l !== void 0 && (l.geometry.dispose(), l.material.dispose(), l = void 0);
  }
  return { getClearColor: function() {
    return o;
  }, setClearColor: function(T, b = 1) {
    o.set(T), c = b, h(o, c);
  }, getClearAlpha: function() {
    return c;
  }, setClearAlpha: function(T) {
    c = T, h(o, c);
  }, render: v, addToRenderList: p, dispose: A };
}
function Sd(i14, t3) {
  let e = i14.getParameter(i14.MAX_VERTEX_ATTRIBS), n = {}, s = f(null), r = s, a = false;
  function o(y, I, z, H, X) {
    let Z = false, W = d(H, z, I);
    r !== W && (r = W, l(r.object)), Z = m(y, H, z, X), Z && x(y, H, z, X), X !== null && t3.update(X, i14.ELEMENT_ARRAY_BUFFER), (Z || a) && (a = false, b(y, I, z, H), X !== null && i14.bindBuffer(i14.ELEMENT_ARRAY_BUFFER, t3.get(X).buffer));
  }
  function c() {
    return i14.createVertexArray();
  }
  function l(y) {
    return i14.bindVertexArray(y);
  }
  function u(y) {
    return i14.deleteVertexArray(y);
  }
  function d(y, I, z) {
    let H = z.wireframe === true, X = n[y.id];
    X === void 0 && (X = {}, n[y.id] = X);
    let Z = X[I.id];
    Z === void 0 && (Z = {}, X[I.id] = Z);
    let W = Z[H];
    return W === void 0 && (W = f(c()), Z[H] = W), W;
  }
  function f(y) {
    let I = [], z = [], H = [];
    for (let X = 0; X < e; X++) I[X] = 0, z[X] = 0, H[X] = 0;
    return { geometry: null, program: null, wireframe: false, newAttributes: I, enabledAttributes: z, attributeDivisors: H, object: y, attributes: {}, index: null };
  }
  function m(y, I, z, H) {
    let X = r.attributes, Z = I.attributes, W = 0, et = z.getAttributes();
    for (let V in et) if (et[V].location >= 0) {
      let ct = X[V], St = Z[V];
      if (St === void 0 && (V === "instanceMatrix" && y.instanceMatrix && (St = y.instanceMatrix), V === "instanceColor" && y.instanceColor && (St = y.instanceColor)), ct === void 0 || ct.attribute !== St || St && ct.data !== St.data) return true;
      W++;
    }
    return r.attributesNum !== W || r.index !== H;
  }
  function x(y, I, z, H) {
    let X = {}, Z = I.attributes, W = 0, et = z.getAttributes();
    for (let V in et) if (et[V].location >= 0) {
      let ct = Z[V];
      ct === void 0 && (V === "instanceMatrix" && y.instanceMatrix && (ct = y.instanceMatrix), V === "instanceColor" && y.instanceColor && (ct = y.instanceColor));
      let St = {};
      St.attribute = ct, ct && ct.data && (St.data = ct.data), X[V] = St, W++;
    }
    r.attributes = X, r.attributesNum = W, r.index = H;
  }
  function v() {
    let y = r.newAttributes;
    for (let I = 0, z = y.length; I < z; I++) y[I] = 0;
  }
  function p(y) {
    h(y, 0);
  }
  function h(y, I) {
    let z = r.newAttributes, H = r.enabledAttributes, X = r.attributeDivisors;
    z[y] = 1, H[y] === 0 && (i14.enableVertexAttribArray(y), H[y] = 1), X[y] !== I && (i14.vertexAttribDivisor(y, I), X[y] = I);
  }
  function A() {
    let y = r.newAttributes, I = r.enabledAttributes;
    for (let z = 0, H = I.length; z < H; z++) I[z] !== y[z] && (i14.disableVertexAttribArray(z), I[z] = 0);
  }
  function T(y, I, z, H, X, Z, W) {
    W === true ? i14.vertexAttribIPointer(y, I, z, X, Z) : i14.vertexAttribPointer(y, I, z, H, X, Z);
  }
  function b(y, I, z, H) {
    v();
    let X = H.attributes, Z = z.getAttributes(), W = I.defaultAttributeValues;
    for (let et in Z) {
      let V = Z[et];
      if (V.location >= 0) {
        let rt = X[et];
        if (rt === void 0 && (et === "instanceMatrix" && y.instanceMatrix && (rt = y.instanceMatrix), et === "instanceColor" && y.instanceColor && (rt = y.instanceColor)), rt !== void 0) {
          let ct = rt.normalized, St = rt.itemSize, Ft = t3.get(rt);
          if (Ft === void 0) continue;
          let Jt = Ft.buffer, jt = Ft.type, Wt = Ft.bytesPerElement, q = jt === i14.INT || jt === i14.UNSIGNED_INT || rt.gpuType === rr;
          if (rt.isInterleavedBufferAttribute) {
            let $2 = rt.data, dt = $2.stride, Rt = rt.offset;
            if ($2.isInstancedInterleavedBuffer) {
              for (let Mt = 0; Mt < V.locationSize; Mt++) h(V.location + Mt, $2.meshPerAttribute);
              y.isInstancedMesh !== true && H._maxInstanceCount === void 0 && (H._maxInstanceCount = $2.meshPerAttribute * $2.count);
            } else for (let Mt = 0; Mt < V.locationSize; Mt++) p(V.location + Mt);
            i14.bindBuffer(i14.ARRAY_BUFFER, Jt);
            for (let Mt = 0; Mt < V.locationSize; Mt++) T(V.location + Mt, St / V.locationSize, jt, ct, dt * Wt, (Rt + St / V.locationSize * Mt) * Wt, q);
          } else {
            if (rt.isInstancedBufferAttribute) {
              for (let $2 = 0; $2 < V.locationSize; $2++) h(V.location + $2, rt.meshPerAttribute);
              y.isInstancedMesh !== true && H._maxInstanceCount === void 0 && (H._maxInstanceCount = rt.meshPerAttribute * rt.count);
            } else for (let $2 = 0; $2 < V.locationSize; $2++) p(V.location + $2);
            i14.bindBuffer(i14.ARRAY_BUFFER, Jt);
            for (let $2 = 0; $2 < V.locationSize; $2++) T(V.location + $2, St / V.locationSize, jt, ct, St * Wt, St / V.locationSize * $2 * Wt, q);
          }
        } else if (W !== void 0) {
          let ct = W[et];
          if (ct !== void 0) switch (ct.length) {
            case 2:
              i14.vertexAttrib2fv(V.location, ct);
              break;
            case 3:
              i14.vertexAttrib3fv(V.location, ct);
              break;
            case 4:
              i14.vertexAttrib4fv(V.location, ct);
              break;
            default:
              i14.vertexAttrib1fv(V.location, ct);
          }
        }
      }
    }
    A();
  }
  function R() {
    N();
    for (let y in n) {
      let I = n[y];
      for (let z in I) {
        let H = I[z];
        for (let X in H) u(H[X].object), delete H[X];
        delete I[z];
      }
      delete n[y];
    }
  }
  function w(y) {
    if (n[y.id] === void 0) return;
    let I = n[y.id];
    for (let z in I) {
      let H = I[z];
      for (let X in H) u(H[X].object), delete H[X];
      delete I[z];
    }
    delete n[y.id];
  }
  function P(y) {
    for (let I in n) {
      let z = n[I];
      if (z[y.id] === void 0) continue;
      let H = z[y.id];
      for (let X in H) u(H[X].object), delete H[X];
      delete z[y.id];
    }
  }
  function N() {
    M(), a = true, r !== s && (r = s, l(r.object));
  }
  function M() {
    s.geometry = null, s.program = null, s.wireframe = false;
  }
  return { setup: o, reset: N, resetDefaultState: M, dispose: R, releaseStatesOfGeometry: w, releaseStatesOfProgram: P, initAttributes: v, enableAttribute: p, disableUnusedAttributes: A };
}
function bd(i14, t3, e) {
  let n;
  function s(l) {
    n = l;
  }
  function r(l, u) {
    i14.drawArrays(n, l, u), e.update(u, n, 1);
  }
  function a(l, u, d) {
    d !== 0 && (i14.drawArraysInstanced(n, l, u, d), e.update(u, n, d));
  }
  function o(l, u, d) {
    if (d === 0) return;
    t3.get("WEBGL_multi_draw").multiDrawArraysWEBGL(n, l, 0, u, 0, d);
    let m = 0;
    for (let x = 0; x < d; x++) m += u[x];
    e.update(m, n, 1);
  }
  function c(l, u, d, f) {
    if (d === 0) return;
    let m = t3.get("WEBGL_multi_draw");
    if (m === null) for (let x = 0; x < l.length; x++) a(l[x], u[x], f[x]);
    else {
      m.multiDrawArraysInstancedWEBGL(n, l, 0, u, 0, f, 0, d);
      let x = 0;
      for (let v = 0; v < d; v++) x += u[v] * f[v];
      e.update(x, n, 1);
    }
  }
  this.setMode = s, this.render = r, this.renderInstances = a, this.renderMultiDraw = o, this.renderMultiDrawInstances = c;
}
function Ed(i14, t3, e, n) {
  let s;
  function r() {
    if (s !== void 0) return s;
    if (t3.has("EXT_texture_filter_anisotropic") === true) {
      let P = t3.get("EXT_texture_filter_anisotropic");
      s = i14.getParameter(P.MAX_TEXTURE_MAX_ANISOTROPY_EXT);
    } else s = 0;
    return s;
  }
  function a(P) {
    return !(P !== Fe && n.convert(P) !== i14.getParameter(i14.IMPLEMENTATION_COLOR_READ_FORMAT));
  }
  function o(P) {
    let N = P === _i && (t3.has("EXT_color_buffer_half_float") || t3.has("EXT_color_buffer_float"));
    return !(P !== We && n.convert(P) !== i14.getParameter(i14.IMPLEMENTATION_COLOR_READ_TYPE) && P !== Ke && !N);
  }
  function c(P) {
    if (P === "highp") {
      if (i14.getShaderPrecisionFormat(i14.VERTEX_SHADER, i14.HIGH_FLOAT).precision > 0 && i14.getShaderPrecisionFormat(i14.FRAGMENT_SHADER, i14.HIGH_FLOAT).precision > 0) return "highp";
      P = "mediump";
    }
    return P === "mediump" && i14.getShaderPrecisionFormat(i14.VERTEX_SHADER, i14.MEDIUM_FLOAT).precision > 0 && i14.getShaderPrecisionFormat(i14.FRAGMENT_SHADER, i14.MEDIUM_FLOAT).precision > 0 ? "mediump" : "lowp";
  }
  let l = e.precision !== void 0 ? e.precision : "highp", u = c(l);
  u !== l && (console.warn("THREE.WebGLRenderer:", l, "not supported, using", u, "instead."), l = u);
  let d = e.logarithmicDepthBuffer === true, f = e.reversedDepthBuffer === true && t3.has("EXT_clip_control"), m = i14.getParameter(i14.MAX_TEXTURE_IMAGE_UNITS), x = i14.getParameter(i14.MAX_VERTEX_TEXTURE_IMAGE_UNITS), v = i14.getParameter(i14.MAX_TEXTURE_SIZE), p = i14.getParameter(i14.MAX_CUBE_MAP_TEXTURE_SIZE), h = i14.getParameter(i14.MAX_VERTEX_ATTRIBS), A = i14.getParameter(i14.MAX_VERTEX_UNIFORM_VECTORS), T = i14.getParameter(i14.MAX_VARYING_VECTORS), b = i14.getParameter(i14.MAX_FRAGMENT_UNIFORM_VECTORS), R = x > 0, w = i14.getParameter(i14.MAX_SAMPLES);
  return { isWebGL2: true, getMaxAnisotropy: r, getMaxPrecision: c, textureFormatReadable: a, textureTypeReadable: o, precision: l, logarithmicDepthBuffer: d, reversedDepthBuffer: f, maxTextures: m, maxVertexTextures: x, maxTextureSize: v, maxCubemapSize: p, maxAttributes: h, maxVertexUniforms: A, maxVaryings: T, maxFragmentUniforms: b, vertexTextures: R, maxSamples: w };
}
function Td(i14) {
  let t3 = this, e = null, n = 0, s = false, r = false, a = new qe(), o = new Lt(), c = { value: null, needsUpdate: false };
  this.uniform = c, this.numPlanes = 0, this.numIntersection = 0, this.init = function(d, f) {
    let m = d.length !== 0 || f || n !== 0 || s;
    return s = f, n = d.length, m;
  }, this.beginShadows = function() {
    r = true, u(null);
  }, this.endShadows = function() {
    r = false;
  }, this.setGlobalState = function(d, f) {
    e = u(d, f, 0);
  }, this.setState = function(d, f, m) {
    let x = d.clippingPlanes, v = d.clipIntersection, p = d.clipShadows, h = i14.get(d);
    if (!s || x === null || x.length === 0 || r && !p) r ? u(null) : l();
    else {
      let A = r ? 0 : n, T = A * 4, b = h.clippingState || null;
      c.value = b, b = u(x, f, T, m);
      for (let R = 0; R !== T; ++R) b[R] = e[R];
      h.clippingState = b, this.numIntersection = v ? this.numPlanes : 0, this.numPlanes += A;
    }
  };
  function l() {
    c.value !== e && (c.value = e, c.needsUpdate = n > 0), t3.numPlanes = n, t3.numIntersection = 0;
  }
  function u(d, f, m, x) {
    let v = d !== null ? d.length : 0, p = null;
    if (v !== 0) {
      if (p = c.value, x !== true || p === null) {
        let h = m + v * 4, A = f.matrixWorldInverse;
        o.getNormalMatrix(A), (p === null || p.length < h) && (p = new Float32Array(h));
        for (let T = 0, b = m; T !== v; ++T, b += 4) a.copy(d[T]).applyMatrix4(A, o), a.normal.toArray(p, b), p[b + 3] = a.constant;
      }
      c.value = p, c.needsUpdate = true;
    }
    return t3.numPlanes = v, t3.numIntersection = 0, p;
  }
}
function Ad(i14) {
  let t3 = /* @__PURE__ */ new WeakMap();
  function e(a, o) {
    return o === nr ? a.mapping = Hn : o === ir && (a.mapping = Gn), a;
  }
  function n(a) {
    if (a && a.isTexture) {
      let o = a.mapping;
      if (o === nr || o === ir) if (t3.has(a)) {
        let c = t3.get(a).texture;
        return e(c, a.mapping);
      } else {
        let c = a.image;
        if (c && c.height > 0) {
          let l = new Ls(c.height);
          return l.fromEquirectangularTexture(i14, a), t3.set(a, l), a.addEventListener("dispose", s), e(l.texture, a.mapping);
        } else return null;
      }
    }
    return a;
  }
  function s(a) {
    let o = a.target;
    o.removeEventListener("dispose", s);
    let c = t3.get(o);
    c !== void 0 && (t3.delete(o), c.dispose());
  }
  function r() {
    t3 = /* @__PURE__ */ new WeakMap();
  }
  return { get: n, dispose: r };
}
var Mi = 4;
var Cl = [0.125, 0.215, 0.35, 0.446, 0.526, 0.582];
var Zn = 20;
var Za = new mi();
var Rl = new Vt();
var Ja = null;
var $a = 0;
var Ka = 0;
var Qa = false;
var Yn = (1 + Math.sqrt(5)) / 2;
var yi = 1 / Yn;
var Il = [new F(-Yn, yi, 0), new F(Yn, yi, 0), new F(-yi, 0, Yn), new F(yi, 0, Yn), new F(0, Yn, -yi), new F(0, Yn, yi), new F(-1, 1, -1), new F(1, 1, -1), new F(-1, 1, 1), new F(1, 1, 1)];
var wd = new F();
var Hr = class {
  constructor(t3) {
    this._renderer = t3, this._pingPongRenderTarget = null, this._lodMax = 0, this._cubeSize = 0, this._lodPlanes = [], this._sizeLods = [], this._sigmas = [], this._blurMaterial = null, this._cubemapMaterial = null, this._equirectMaterial = null, this._compileMaterial(this._blurMaterial);
  }
  fromScene(t3, e = 0, n = 0.1, s = 100, r = {}) {
    let { size: a = 256, position: o = wd } = r;
    Ja = this._renderer.getRenderTarget(), $a = this._renderer.getActiveCubeFace(), Ka = this._renderer.getActiveMipmapLevel(), Qa = this._renderer.xr.enabled, this._renderer.xr.enabled = false, this._setSize(a);
    let c = this._allocateTargets();
    return c.depthBuffer = true, this._sceneToCubeUV(t3, n, s, c, o), e > 0 && this._blur(c, 0, 0, e), this._applyPMREM(c), this._cleanup(c), c;
  }
  fromEquirectangular(t3, e = null) {
    return this._fromTexture(t3, e);
  }
  fromCubemap(t3, e = null) {
    return this._fromTexture(t3, e);
  }
  compileCubemapShader() {
    this._cubemapMaterial === null && (this._cubemapMaterial = Dl(), this._compileMaterial(this._cubemapMaterial));
  }
  compileEquirectangularShader() {
    this._equirectMaterial === null && (this._equirectMaterial = Ll(), this._compileMaterial(this._equirectMaterial));
  }
  dispose() {
    this._dispose(), this._cubemapMaterial !== null && this._cubemapMaterial.dispose(), this._equirectMaterial !== null && this._equirectMaterial.dispose();
  }
  _setSize(t3) {
    this._lodMax = Math.floor(Math.log2(t3)), this._cubeSize = Math.pow(2, this._lodMax);
  }
  _dispose() {
    this._blurMaterial !== null && this._blurMaterial.dispose(), this._pingPongRenderTarget !== null && this._pingPongRenderTarget.dispose();
    for (let t3 = 0; t3 < this._lodPlanes.length; t3++) this._lodPlanes[t3].dispose();
  }
  _cleanup(t3) {
    this._renderer.setRenderTarget(Ja, $a, Ka), this._renderer.xr.enabled = Qa, t3.scissorTest = false, Vr(t3, 0, 0, t3.width, t3.height);
  }
  _fromTexture(t3, e) {
    t3.mapping === Hn || t3.mapping === Gn ? this._setSize(t3.image.length === 0 ? 16 : t3.image[0].width || t3.image[0].image.width) : this._setSize(t3.image.width / 4), Ja = this._renderer.getRenderTarget(), $a = this._renderer.getActiveCubeFace(), Ka = this._renderer.getActiveMipmapLevel(), Qa = this._renderer.xr.enabled, this._renderer.xr.enabled = false;
    let n = e || this._allocateTargets();
    return this._textureToCubeUV(t3, n), this._applyPMREM(n), this._cleanup(n), n;
  }
  _allocateTargets() {
    let t3 = 3 * Math.max(this._cubeSize, 112), e = 4 * this._cubeSize, n = { magFilter: ke, minFilter: ke, generateMipmaps: false, type: _i, format: Fe, colorSpace: zn, depthBuffer: false }, s = Pl(t3, e, n);
    if (this._pingPongRenderTarget === null || this._pingPongRenderTarget.width !== t3 || this._pingPongRenderTarget.height !== e) {
      this._pingPongRenderTarget !== null && this._dispose(), this._pingPongRenderTarget = Pl(t3, e, n);
      let { _lodMax: r } = this;
      ({ sizeLods: this._sizeLods, lodPlanes: this._lodPlanes, sigmas: this._sigmas } = Cd(r)), this._blurMaterial = Rd(r, t3, e);
    }
    return s;
  }
  _compileMaterial(t3) {
    let e = new Ie(this._lodPlanes[0], t3);
    this._renderer.compile(e, Za);
  }
  _sceneToCubeUV(t3, e, n, s, r) {
    let c = new Se(90, 1, e, n), l = [1, -1, 1, 1, 1, 1], u = [1, 1, 1, -1, -1, -1], d = this._renderer, f = d.autoClear, m = d.toneMapping;
    d.getClearColor(Rl), d.toneMapping = un, d.autoClear = false, d.state.buffers.depth.getReversed() && (d.setRenderTarget(s), d.clearDepth(), d.setRenderTarget(null));
    let v = new Fi({ name: "PMREM.Background", side: ve, depthWrite: false, depthTest: false }), p = new Ie(new Vn(), v), h = false, A = t3.background;
    A ? A.isColor && (v.color.copy(A), t3.background = null, h = true) : (v.color.copy(Rl), h = true);
    for (let T = 0; T < 6; T++) {
      let b = T % 3;
      b === 0 ? (c.up.set(0, l[T], 0), c.position.set(r.x, r.y, r.z), c.lookAt(r.x + u[T], r.y, r.z)) : b === 1 ? (c.up.set(0, 0, l[T]), c.position.set(r.x, r.y, r.z), c.lookAt(r.x, r.y + u[T], r.z)) : (c.up.set(0, l[T], 0), c.position.set(r.x, r.y, r.z), c.lookAt(r.x, r.y, r.z + u[T]));
      let R = this._cubeSize;
      Vr(s, b * R, T > 2 ? R : 0, R, R), d.setRenderTarget(s), h && d.render(p, c), d.render(t3, c);
    }
    p.geometry.dispose(), p.material.dispose(), d.toneMapping = m, d.autoClear = f, t3.background = A;
  }
  _textureToCubeUV(t3, e) {
    let n = this._renderer, s = t3.mapping === Hn || t3.mapping === Gn;
    s ? (this._cubemapMaterial === null && (this._cubemapMaterial = Dl()), this._cubemapMaterial.uniforms.flipEnvMap.value = t3.isRenderTargetTexture === false ? -1 : 1) : this._equirectMaterial === null && (this._equirectMaterial = Ll());
    let r = s ? this._cubemapMaterial : this._equirectMaterial, a = new Ie(this._lodPlanes[0], r), o = r.uniforms;
    o.envMap.value = t3;
    let c = this._cubeSize;
    Vr(e, 0, 0, 3 * c, 2 * c), n.setRenderTarget(e), n.render(a, Za);
  }
  _applyPMREM(t3) {
    let e = this._renderer, n = e.autoClear;
    e.autoClear = false;
    let s = this._lodPlanes.length;
    for (let r = 1; r < s; r++) {
      let a = Math.sqrt(this._sigmas[r] * this._sigmas[r] - this._sigmas[r - 1] * this._sigmas[r - 1]), o = Il[(s - r - 1) % Il.length];
      this._blur(t3, r - 1, r, a, o);
    }
    e.autoClear = n;
  }
  _blur(t3, e, n, s, r) {
    let a = this._pingPongRenderTarget;
    this._halfBlur(t3, a, e, n, s, "latitudinal", r), this._halfBlur(a, t3, n, n, s, "longitudinal", r);
  }
  _halfBlur(t3, e, n, s, r, a, o) {
    let c = this._renderer, l = this._blurMaterial;
    a !== "latitudinal" && a !== "longitudinal" && console.error("blur direction must be either latitudinal or longitudinal!");
    let u = 3, d = new Ie(this._lodPlanes[s], l), f = l.uniforms, m = this._sizeLods[n] - 1, x = isFinite(r) ? Math.PI / (2 * m) : 2 * Math.PI / (2 * Zn - 1), v = r / x, p = isFinite(r) ? 1 + Math.floor(u * v) : Zn;
    p > Zn && console.warn(`sigmaRadians, ${r}, is too large and will clip, as it requested ${p} samples when the maximum is set to ${Zn}`);
    let h = [], A = 0;
    for (let P = 0; P < Zn; ++P) {
      let N = P / v, M = Math.exp(-N * N / 2);
      h.push(M), P === 0 ? A += M : P < p && (A += 2 * M);
    }
    for (let P = 0; P < h.length; P++) h[P] = h[P] / A;
    f.envMap.value = t3.texture, f.samples.value = p, f.weights.value = h, f.latitudinal.value = a === "latitudinal", o && (f.poleAxis.value = o);
    let { _lodMax: T } = this;
    f.dTheta.value = x, f.mipInt.value = T - n;
    let b = this._sizeLods[s], R = 3 * b * (s > T - Mi ? s - T + Mi : 0), w = 4 * (this._cubeSize - b);
    Vr(e, R, w, 3 * b, 2 * b), c.setRenderTarget(e), c.render(d, Za);
  }
};
function Cd(i14) {
  let t3 = [], e = [], n = [], s = i14, r = i14 - Mi + 1 + Cl.length;
  for (let a = 0; a < r; a++) {
    let o = Math.pow(2, s);
    e.push(o);
    let c = 1 / o;
    a > i14 - Mi ? c = Cl[a - i14 + Mi - 1] : a === 0 && (c = 0), n.push(c);
    let l = 1 / (o - 2), u = -l, d = 1 + l, f = [u, u, d, u, d, d, u, u, d, d, u, d], m = 6, x = 6, v = 3, p = 2, h = 1, A = new Float32Array(v * x * m), T = new Float32Array(p * x * m), b = new Float32Array(h * x * m);
    for (let w = 0; w < m; w++) {
      let P = w % 3 * 2 / 3 - 1, N = w > 2 ? 0 : -1, M = [P, N, 0, P + 2 / 3, N, 0, P + 2 / 3, N + 1, 0, P, N, 0, P + 2 / 3, N + 1, 0, P, N + 1, 0];
      A.set(M, v * x * w), T.set(f, p * x * w);
      let y = [w, w, w, w, w, w];
      b.set(y, h * x * w);
    }
    let R = new En();
    R.setAttribute("position", new Ce(A, v)), R.setAttribute("uv", new Ce(T, p)), R.setAttribute("faceIndex", new Ce(b, h)), t3.push(R), s > Mi && s--;
  }
  return { lodPlanes: t3, sizeLods: e, sigmas: n };
}
function Pl(i14, t3, e) {
  let n = new Ze(i14, t3, e);
  return n.texture.mapping = qi, n.texture.name = "PMREM.cubeUv", n.scissorTest = true, n;
}
function Vr(i14, t3, e, n, s) {
  i14.viewport.set(t3, e, n, s), i14.scissor.set(t3, e, n, s);
}
function Rd(i14, t3, e) {
  let n = new Float32Array(Zn), s = new F(0, 1, 0);
  return new Ge({ name: "SphericalGaussianBlur", defines: { n: Zn, CUBEUV_TEXEL_WIDTH: 1 / t3, CUBEUV_TEXEL_HEIGHT: 1 / e, CUBEUV_MAX_MIP: `${i14}.0` }, uniforms: { envMap: { value: null }, samples: { value: 1 }, weights: { value: n }, latitudinal: { value: false }, dTheta: { value: 0 }, mipInt: { value: 0 }, poleAxis: { value: s } }, vertexShader: co(), fragmentShader: `

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;
			uniform int samples;
			uniform float weights[ n ];
			uniform bool latitudinal;
			uniform float dTheta;
			uniform float mipInt;
			uniform vec3 poleAxis;

			#define ENVMAP_TYPE_CUBE_UV
			#include <cube_uv_reflection_fragment>

			vec3 getSample( float theta, vec3 axis ) {

				float cosTheta = cos( theta );
				// Rodrigues' axis-angle rotation
				vec3 sampleDirection = vOutputDirection * cosTheta
					+ cross( axis, vOutputDirection ) * sin( theta )
					+ axis * dot( axis, vOutputDirection ) * ( 1.0 - cosTheta );

				return bilinearCubeUV( envMap, sampleDirection, mipInt );

			}

			void main() {

				vec3 axis = latitudinal ? poleAxis : cross( poleAxis, vOutputDirection );

				if ( all( equal( axis, vec3( 0.0 ) ) ) ) {

					axis = vec3( vOutputDirection.z, 0.0, - vOutputDirection.x );

				}

				axis = normalize( axis );

				gl_FragColor = vec4( 0.0, 0.0, 0.0, 1.0 );
				gl_FragColor.rgb += weights[ 0 ] * getSample( 0.0, axis );

				for ( int i = 1; i < n; i++ ) {

					if ( i >= samples ) {

						break;

					}

					float theta = dTheta * float( i );
					gl_FragColor.rgb += weights[ i ] * getSample( -1.0 * theta, axis );
					gl_FragColor.rgb += weights[ i ] * getSample( theta, axis );

				}

			}
		`, blending: hn, depthTest: false, depthWrite: false });
}
function Ll() {
  return new Ge({ name: "EquirectangularToCubeUV", uniforms: { envMap: { value: null } }, vertexShader: co(), fragmentShader: `

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;

			#include <common>

			void main() {

				vec3 outputDirection = normalize( vOutputDirection );
				vec2 uv = equirectUv( outputDirection );

				gl_FragColor = vec4( texture2D ( envMap, uv ).rgb, 1.0 );

			}
		`, blending: hn, depthTest: false, depthWrite: false });
}
function Dl() {
  return new Ge({ name: "CubemapToCubeUV", uniforms: { envMap: { value: null }, flipEnvMap: { value: -1 } }, vertexShader: co(), fragmentShader: `

			precision mediump float;
			precision mediump int;

			uniform float flipEnvMap;

			varying vec3 vOutputDirection;

			uniform samplerCube envMap;

			void main() {

				gl_FragColor = textureCube( envMap, vec3( flipEnvMap * vOutputDirection.x, vOutputDirection.yz ) );

			}
		`, blending: hn, depthTest: false, depthWrite: false });
}
function co() {
  return `

		precision mediump float;
		precision mediump int;

		attribute float faceIndex;

		varying vec3 vOutputDirection;

		// RH coordinate system; PMREM face-indexing convention
		vec3 getDirection( vec2 uv, float face ) {

			uv = 2.0 * uv - 1.0;

			vec3 direction = vec3( uv, 1.0 );

			if ( face == 0.0 ) {

				direction = direction.zyx; // ( 1, v, u ) pos x

			} else if ( face == 1.0 ) {

				direction = direction.xzy;
				direction.xz *= -1.0; // ( -u, 1, -v ) pos y

			} else if ( face == 2.0 ) {

				direction.x *= -1.0; // ( -u, v, 1 ) pos z

			} else if ( face == 3.0 ) {

				direction = direction.zyx;
				direction.xz *= -1.0; // ( -1, v, -u ) neg x

			} else if ( face == 4.0 ) {

				direction = direction.xzy;
				direction.xy *= -1.0; // ( -u, -1, v ) neg y

			} else if ( face == 5.0 ) {

				direction.z *= -1.0; // ( u, v, -1 ) neg z

			}

			return direction;

		}

		void main() {

			vOutputDirection = getDirection( uv, faceIndex );
			gl_Position = vec4( position, 1.0 );

		}
	`;
}
function Id(i14) {
  let t3 = /* @__PURE__ */ new WeakMap(), e = null;
  function n(o) {
    if (o && o.isTexture) {
      let c = o.mapping, l = c === nr || c === ir, u = c === Hn || c === Gn;
      if (l || u) {
        let d = t3.get(o), f = d !== void 0 ? d.texture.pmremVersion : 0;
        if (o.isRenderTargetTexture && o.pmremVersion !== f) return e === null && (e = new Hr(i14)), d = l ? e.fromEquirectangular(o, d) : e.fromCubemap(o, d), d.texture.pmremVersion = o.pmremVersion, t3.set(o, d), d.texture;
        if (d !== void 0) return d.texture;
        {
          let m = o.image;
          return l && m && m.height > 0 || u && m && s(m) ? (e === null && (e = new Hr(i14)), d = l ? e.fromEquirectangular(o) : e.fromCubemap(o), d.texture.pmremVersion = o.pmremVersion, t3.set(o, d), o.addEventListener("dispose", r), d.texture) : null;
        }
      }
    }
    return o;
  }
  function s(o) {
    let c = 0, l = 6;
    for (let u = 0; u < l; u++) o[u] !== void 0 && c++;
    return c === l;
  }
  function r(o) {
    let c = o.target;
    c.removeEventListener("dispose", r);
    let l = t3.get(c);
    l !== void 0 && (t3.delete(c), l.dispose());
  }
  function a() {
    t3 = /* @__PURE__ */ new WeakMap(), e !== null && (e.dispose(), e = null);
  }
  return { get: n, dispose: a };
}
function Pd(i14) {
  let t3 = {};
  function e(n) {
    if (t3[n] !== void 0) return t3[n];
    let s;
    switch (n) {
      case "WEBGL_depth_texture":
        s = i14.getExtension("WEBGL_depth_texture") || i14.getExtension("MOZ_WEBGL_depth_texture") || i14.getExtension("WEBKIT_WEBGL_depth_texture");
        break;
      case "EXT_texture_filter_anisotropic":
        s = i14.getExtension("EXT_texture_filter_anisotropic") || i14.getExtension("MOZ_EXT_texture_filter_anisotropic") || i14.getExtension("WEBKIT_EXT_texture_filter_anisotropic");
        break;
      case "WEBGL_compressed_texture_s3tc":
        s = i14.getExtension("WEBGL_compressed_texture_s3tc") || i14.getExtension("MOZ_WEBGL_compressed_texture_s3tc") || i14.getExtension("WEBKIT_WEBGL_compressed_texture_s3tc");
        break;
      case "WEBGL_compressed_texture_pvrtc":
        s = i14.getExtension("WEBGL_compressed_texture_pvrtc") || i14.getExtension("WEBKIT_WEBGL_compressed_texture_pvrtc");
        break;
      default:
        s = i14.getExtension(n);
    }
    return t3[n] = s, s;
  }
  return { has: function(n) {
    return e(n) !== null;
  }, init: function() {
    e("EXT_color_buffer_float"), e("WEBGL_clip_cull_distance"), e("OES_texture_float_linear"), e("EXT_color_buffer_half_float"), e("WEBGL_multisampled_render_to_texture"), e("WEBGL_render_shared_exponent");
  }, get: function(n) {
    let s = e(n);
    return s === null && hi("THREE.WebGLRenderer: " + n + " extension not supported."), s;
  } };
}
function Ld(i14, t3, e, n) {
  let s = {}, r = /* @__PURE__ */ new WeakMap();
  function a(d) {
    let f = d.target;
    f.index !== null && t3.remove(f.index);
    for (let x in f.attributes) t3.remove(f.attributes[x]);
    f.removeEventListener("dispose", a), delete s[f.id];
    let m = r.get(f);
    m && (t3.remove(m), r.delete(f)), n.releaseStatesOfGeometry(f), f.isInstancedBufferGeometry === true && delete f._maxInstanceCount, e.memory.geometries--;
  }
  function o(d, f) {
    return s[f.id] === true || (f.addEventListener("dispose", a), s[f.id] = true, e.memory.geometries++), f;
  }
  function c(d) {
    let f = d.attributes;
    for (let m in f) t3.update(f[m], i14.ARRAY_BUFFER);
  }
  function l(d) {
    let f = [], m = d.index, x = d.attributes.position, v = 0;
    if (m !== null) {
      let A = m.array;
      v = m.version;
      for (let T = 0, b = A.length; T < b; T += 3) {
        let R = A[T + 0], w = A[T + 1], P = A[T + 2];
        f.push(R, w, w, P, P, R);
      }
    } else if (x !== void 0) {
      let A = x.array;
      v = x.version;
      for (let T = 0, b = A.length / 3 - 1; T < b; T += 3) {
        let R = T + 0, w = T + 1, P = T + 2;
        f.push(R, w, w, P, P, R);
      }
    } else return;
    let p = new (Ga(f) ? Bi : Oi)(f, 1);
    p.version = v;
    let h = r.get(d);
    h && t3.remove(h), r.set(d, p);
  }
  function u(d) {
    let f = r.get(d);
    if (f) {
      let m = d.index;
      m !== null && f.version < m.version && l(d);
    } else l(d);
    return r.get(d);
  }
  return { get: o, update: c, getWireframeAttribute: u };
}
function Dd(i14, t3, e) {
  let n;
  function s(f) {
    n = f;
  }
  let r, a;
  function o(f) {
    r = f.type, a = f.bytesPerElement;
  }
  function c(f, m) {
    i14.drawElements(n, m, r, f * a), e.update(m, n, 1);
  }
  function l(f, m, x) {
    x !== 0 && (i14.drawElementsInstanced(n, m, r, f * a, x), e.update(m, n, x));
  }
  function u(f, m, x) {
    if (x === 0) return;
    t3.get("WEBGL_multi_draw").multiDrawElementsWEBGL(n, m, 0, r, f, 0, x);
    let p = 0;
    for (let h = 0; h < x; h++) p += m[h];
    e.update(p, n, 1);
  }
  function d(f, m, x, v) {
    if (x === 0) return;
    let p = t3.get("WEBGL_multi_draw");
    if (p === null) for (let h = 0; h < f.length; h++) l(f[h] / a, m[h], v[h]);
    else {
      p.multiDrawElementsInstancedWEBGL(n, m, 0, r, f, 0, v, 0, x);
      let h = 0;
      for (let A = 0; A < x; A++) h += m[A] * v[A];
      e.update(h, n, 1);
    }
  }
  this.setMode = s, this.setIndex = o, this.render = c, this.renderInstances = l, this.renderMultiDraw = u, this.renderMultiDrawInstances = d;
}
function Ud(i14) {
  let t3 = { geometries: 0, textures: 0 }, e = { frame: 0, calls: 0, triangles: 0, points: 0, lines: 0 };
  function n(r, a, o) {
    switch (e.calls++, a) {
      case i14.TRIANGLES:
        e.triangles += o * (r / 3);
        break;
      case i14.LINES:
        e.lines += o * (r / 2);
        break;
      case i14.LINE_STRIP:
        e.lines += o * (r - 1);
        break;
      case i14.LINE_LOOP:
        e.lines += o * r;
        break;
      case i14.POINTS:
        e.points += o * r;
        break;
      default:
        console.error("THREE.WebGLInfo: Unknown draw mode:", a);
        break;
    }
  }
  function s() {
    e.calls = 0, e.triangles = 0, e.points = 0, e.lines = 0;
  }
  return { memory: t3, render: e, programs: null, autoReset: true, reset: s, update: n };
}
function Nd(i14, t3, e) {
  let n = /* @__PURE__ */ new WeakMap(), s = new se();
  function r(a, o, c) {
    let l = a.morphTargetInfluences, u = o.morphAttributes.position || o.morphAttributes.normal || o.morphAttributes.color, d = u !== void 0 ? u.length : 0, f = n.get(o);
    if (f === void 0 || f.count !== d) {
      let M = function() {
        P.dispose(), n.delete(o), o.removeEventListener("dispose", M);
      };
      f !== void 0 && f.texture.dispose();
      let m = o.morphAttributes.position !== void 0, x = o.morphAttributes.normal !== void 0, v = o.morphAttributes.color !== void 0, p = o.morphAttributes.position || [], h = o.morphAttributes.normal || [], A = o.morphAttributes.color || [], T = 0;
      m === true && (T = 1), x === true && (T = 2), v === true && (T = 3);
      let b = o.attributes.position.count * T, R = 1;
      b > t3.maxTextureSize && (R = Math.ceil(b / t3.maxTextureSize), b = t3.maxTextureSize);
      let w = new Float32Array(b * R * 4 * d), P = new Ui(w, b, R, d);
      P.type = Ke, P.needsUpdate = true;
      let N = T * 4;
      for (let y = 0; y < d; y++) {
        let I = p[y], z = h[y], H = A[y], X = b * R * 4 * y;
        for (let Z = 0; Z < I.count; Z++) {
          let W = Z * N;
          m === true && (s.fromBufferAttribute(I, Z), w[X + W + 0] = s.x, w[X + W + 1] = s.y, w[X + W + 2] = s.z, w[X + W + 3] = 0), x === true && (s.fromBufferAttribute(z, Z), w[X + W + 4] = s.x, w[X + W + 5] = s.y, w[X + W + 6] = s.z, w[X + W + 7] = 0), v === true && (s.fromBufferAttribute(H, Z), w[X + W + 8] = s.x, w[X + W + 9] = s.y, w[X + W + 10] = s.z, w[X + W + 11] = H.itemSize === 4 ? s.w : 1);
        }
      }
      f = { count: d, texture: P, size: new Gt(b, R) }, n.set(o, f), o.addEventListener("dispose", M);
    }
    if (a.isInstancedMesh === true && a.morphTexture !== null) c.getUniforms().setValue(i14, "morphTexture", a.morphTexture, e);
    else {
      let m = 0;
      for (let v = 0; v < l.length; v++) m += l[v];
      let x = o.morphTargetsRelative ? 1 : 1 - m;
      c.getUniforms().setValue(i14, "morphTargetBaseInfluence", x), c.getUniforms().setValue(i14, "morphTargetInfluences", l);
    }
    c.getUniforms().setValue(i14, "morphTargetsTexture", f.texture, e), c.getUniforms().setValue(i14, "morphTargetsTextureSize", f.size);
  }
  return { update: r };
}
function Fd(i14, t3, e, n) {
  let s = /* @__PURE__ */ new WeakMap();
  function r(c) {
    let l = n.render.frame, u = c.geometry, d = t3.get(c, u);
    if (s.get(d) !== l && (t3.update(d), s.set(d, l)), c.isInstancedMesh && (c.hasEventListener("dispose", o) === false && c.addEventListener("dispose", o), s.get(c) !== l && (e.update(c.instanceMatrix, i14.ARRAY_BUFFER), c.instanceColor !== null && e.update(c.instanceColor, i14.ARRAY_BUFFER), s.set(c, l))), c.isSkinnedMesh) {
      let f = c.skeleton;
      s.get(f) !== l && (f.update(), s.set(f, l));
    }
    return d;
  }
  function a() {
    s = /* @__PURE__ */ new WeakMap();
  }
  function o(c) {
    let l = c.target;
    l.removeEventListener("dispose", o), e.remove(l.instanceMatrix), l.instanceColor !== null && e.remove(l.instanceColor);
  }
  return { update: r, dispose: a };
}
var Ql = new Re();
var Ul = new ki(1, 1);
var jl = new Ui();
var tc = new Rs();
var ec = new Vi();
var Nl = [];
var Fl = [];
var Ol = new Float32Array(16);
var Bl = new Float32Array(9);
var zl = new Float32Array(4);
function bi(i14, t3, e) {
  let n = i14[0];
  if (n <= 0 || n > 0) return i14;
  let s = t3 * e, r = Nl[s];
  if (r === void 0 && (r = new Float32Array(s), Nl[s] = r), t3 !== 0) {
    n.toArray(r, 0);
    for (let a = 1, o = 0; a !== t3; ++a) o += e, i14[a].toArray(r, o);
  }
  return r;
}
function ce(i14, t3) {
  if (i14.length !== t3.length) return false;
  for (let e = 0, n = i14.length; e < n; e++) if (i14[e] !== t3[e]) return false;
  return true;
}
function he(i14, t3) {
  for (let e = 0, n = t3.length; e < n; e++) i14[e] = t3[e];
}
function Gr(i14, t3) {
  let e = Fl[t3];
  e === void 0 && (e = new Int32Array(t3), Fl[t3] = e);
  for (let n = 0; n !== t3; ++n) e[n] = i14.allocateTextureUnit();
  return e;
}
function Od(i14, t3) {
  let e = this.cache;
  e[0] !== t3 && (i14.uniform1f(this.addr, t3), e[0] = t3);
}
function Bd(i14, t3) {
  let e = this.cache;
  if (t3.x !== void 0) (e[0] !== t3.x || e[1] !== t3.y) && (i14.uniform2f(this.addr, t3.x, t3.y), e[0] = t3.x, e[1] = t3.y);
  else {
    if (ce(e, t3)) return;
    i14.uniform2fv(this.addr, t3), he(e, t3);
  }
}
function zd(i14, t3) {
  let e = this.cache;
  if (t3.x !== void 0) (e[0] !== t3.x || e[1] !== t3.y || e[2] !== t3.z) && (i14.uniform3f(this.addr, t3.x, t3.y, t3.z), e[0] = t3.x, e[1] = t3.y, e[2] = t3.z);
  else if (t3.r !== void 0) (e[0] !== t3.r || e[1] !== t3.g || e[2] !== t3.b) && (i14.uniform3f(this.addr, t3.r, t3.g, t3.b), e[0] = t3.r, e[1] = t3.g, e[2] = t3.b);
  else {
    if (ce(e, t3)) return;
    i14.uniform3fv(this.addr, t3), he(e, t3);
  }
}
function Vd(i14, t3) {
  let e = this.cache;
  if (t3.x !== void 0) (e[0] !== t3.x || e[1] !== t3.y || e[2] !== t3.z || e[3] !== t3.w) && (i14.uniform4f(this.addr, t3.x, t3.y, t3.z, t3.w), e[0] = t3.x, e[1] = t3.y, e[2] = t3.z, e[3] = t3.w);
  else {
    if (ce(e, t3)) return;
    i14.uniform4fv(this.addr, t3), he(e, t3);
  }
}
function kd(i14, t3) {
  let e = this.cache, n = t3.elements;
  if (n === void 0) {
    if (ce(e, t3)) return;
    i14.uniformMatrix2fv(this.addr, false, t3), he(e, t3);
  } else {
    if (ce(e, n)) return;
    zl.set(n), i14.uniformMatrix2fv(this.addr, false, zl), he(e, n);
  }
}
function Hd(i14, t3) {
  let e = this.cache, n = t3.elements;
  if (n === void 0) {
    if (ce(e, t3)) return;
    i14.uniformMatrix3fv(this.addr, false, t3), he(e, t3);
  } else {
    if (ce(e, n)) return;
    Bl.set(n), i14.uniformMatrix3fv(this.addr, false, Bl), he(e, n);
  }
}
function Gd(i14, t3) {
  let e = this.cache, n = t3.elements;
  if (n === void 0) {
    if (ce(e, t3)) return;
    i14.uniformMatrix4fv(this.addr, false, t3), he(e, t3);
  } else {
    if (ce(e, n)) return;
    Ol.set(n), i14.uniformMatrix4fv(this.addr, false, Ol), he(e, n);
  }
}
function Wd(i14, t3) {
  let e = this.cache;
  e[0] !== t3 && (i14.uniform1i(this.addr, t3), e[0] = t3);
}
function Xd(i14, t3) {
  let e = this.cache;
  if (t3.x !== void 0) (e[0] !== t3.x || e[1] !== t3.y) && (i14.uniform2i(this.addr, t3.x, t3.y), e[0] = t3.x, e[1] = t3.y);
  else {
    if (ce(e, t3)) return;
    i14.uniform2iv(this.addr, t3), he(e, t3);
  }
}
function qd(i14, t3) {
  let e = this.cache;
  if (t3.x !== void 0) (e[0] !== t3.x || e[1] !== t3.y || e[2] !== t3.z) && (i14.uniform3i(this.addr, t3.x, t3.y, t3.z), e[0] = t3.x, e[1] = t3.y, e[2] = t3.z);
  else {
    if (ce(e, t3)) return;
    i14.uniform3iv(this.addr, t3), he(e, t3);
  }
}
function Yd(i14, t3) {
  let e = this.cache;
  if (t3.x !== void 0) (e[0] !== t3.x || e[1] !== t3.y || e[2] !== t3.z || e[3] !== t3.w) && (i14.uniform4i(this.addr, t3.x, t3.y, t3.z, t3.w), e[0] = t3.x, e[1] = t3.y, e[2] = t3.z, e[3] = t3.w);
  else {
    if (ce(e, t3)) return;
    i14.uniform4iv(this.addr, t3), he(e, t3);
  }
}
function Zd(i14, t3) {
  let e = this.cache;
  e[0] !== t3 && (i14.uniform1ui(this.addr, t3), e[0] = t3);
}
function Jd(i14, t3) {
  let e = this.cache;
  if (t3.x !== void 0) (e[0] !== t3.x || e[1] !== t3.y) && (i14.uniform2ui(this.addr, t3.x, t3.y), e[0] = t3.x, e[1] = t3.y);
  else {
    if (ce(e, t3)) return;
    i14.uniform2uiv(this.addr, t3), he(e, t3);
  }
}
function $d(i14, t3) {
  let e = this.cache;
  if (t3.x !== void 0) (e[0] !== t3.x || e[1] !== t3.y || e[2] !== t3.z) && (i14.uniform3ui(this.addr, t3.x, t3.y, t3.z), e[0] = t3.x, e[1] = t3.y, e[2] = t3.z);
  else {
    if (ce(e, t3)) return;
    i14.uniform3uiv(this.addr, t3), he(e, t3);
  }
}
function Kd(i14, t3) {
  let e = this.cache;
  if (t3.x !== void 0) (e[0] !== t3.x || e[1] !== t3.y || e[2] !== t3.z || e[3] !== t3.w) && (i14.uniform4ui(this.addr, t3.x, t3.y, t3.z, t3.w), e[0] = t3.x, e[1] = t3.y, e[2] = t3.z, e[3] = t3.w);
  else {
    if (ce(e, t3)) return;
    i14.uniform4uiv(this.addr, t3), he(e, t3);
  }
}
function Qd(i14, t3, e) {
  let n = this.cache, s = e.allocateTextureUnit();
  n[0] !== s && (i14.uniform1i(this.addr, s), n[0] = s);
  let r;
  this.type === i14.SAMPLER_2D_SHADOW ? (Ul.compareFunction = ka, r = Ul) : r = Ql, e.setTexture2D(t3 || r, s);
}
function jd(i14, t3, e) {
  let n = this.cache, s = e.allocateTextureUnit();
  n[0] !== s && (i14.uniform1i(this.addr, s), n[0] = s), e.setTexture3D(t3 || tc, s);
}
function tf(i14, t3, e) {
  let n = this.cache, s = e.allocateTextureUnit();
  n[0] !== s && (i14.uniform1i(this.addr, s), n[0] = s), e.setTextureCube(t3 || ec, s);
}
function ef(i14, t3, e) {
  let n = this.cache, s = e.allocateTextureUnit();
  n[0] !== s && (i14.uniform1i(this.addr, s), n[0] = s), e.setTexture2DArray(t3 || jl, s);
}
function nf(i14) {
  switch (i14) {
    case 5126:
      return Od;
    case 35664:
      return Bd;
    case 35665:
      return zd;
    case 35666:
      return Vd;
    case 35674:
      return kd;
    case 35675:
      return Hd;
    case 35676:
      return Gd;
    case 5124:
    case 35670:
      return Wd;
    case 35667:
    case 35671:
      return Xd;
    case 35668:
    case 35672:
      return qd;
    case 35669:
    case 35673:
      return Yd;
    case 5125:
      return Zd;
    case 36294:
      return Jd;
    case 36295:
      return $d;
    case 36296:
      return Kd;
    case 35678:
    case 36198:
    case 36298:
    case 36306:
    case 35682:
      return Qd;
    case 35679:
    case 36299:
    case 36307:
      return jd;
    case 35680:
    case 36300:
    case 36308:
    case 36293:
      return tf;
    case 36289:
    case 36303:
    case 36311:
    case 36292:
      return ef;
  }
}
function sf(i14, t3) {
  i14.uniform1fv(this.addr, t3);
}
function rf(i14, t3) {
  let e = bi(t3, this.size, 2);
  i14.uniform2fv(this.addr, e);
}
function af(i14, t3) {
  let e = bi(t3, this.size, 3);
  i14.uniform3fv(this.addr, e);
}
function of(i14, t3) {
  let e = bi(t3, this.size, 4);
  i14.uniform4fv(this.addr, e);
}
function lf(i14, t3) {
  let e = bi(t3, this.size, 4);
  i14.uniformMatrix2fv(this.addr, false, e);
}
function cf(i14, t3) {
  let e = bi(t3, this.size, 9);
  i14.uniformMatrix3fv(this.addr, false, e);
}
function hf(i14, t3) {
  let e = bi(t3, this.size, 16);
  i14.uniformMatrix4fv(this.addr, false, e);
}
function uf(i14, t3) {
  i14.uniform1iv(this.addr, t3);
}
function df(i14, t3) {
  i14.uniform2iv(this.addr, t3);
}
function ff(i14, t3) {
  i14.uniform3iv(this.addr, t3);
}
function pf(i14, t3) {
  i14.uniform4iv(this.addr, t3);
}
function mf(i14, t3) {
  i14.uniform1uiv(this.addr, t3);
}
function gf(i14, t3) {
  i14.uniform2uiv(this.addr, t3);
}
function _f(i14, t3) {
  i14.uniform3uiv(this.addr, t3);
}
function xf(i14, t3) {
  i14.uniform4uiv(this.addr, t3);
}
function vf(i14, t3, e) {
  let n = this.cache, s = t3.length, r = Gr(e, s);
  ce(n, r) || (i14.uniform1iv(this.addr, r), he(n, r));
  for (let a = 0; a !== s; ++a) e.setTexture2D(t3[a] || Ql, r[a]);
}
function yf(i14, t3, e) {
  let n = this.cache, s = t3.length, r = Gr(e, s);
  ce(n, r) || (i14.uniform1iv(this.addr, r), he(n, r));
  for (let a = 0; a !== s; ++a) e.setTexture3D(t3[a] || tc, r[a]);
}
function Mf(i14, t3, e) {
  let n = this.cache, s = t3.length, r = Gr(e, s);
  ce(n, r) || (i14.uniform1iv(this.addr, r), he(n, r));
  for (let a = 0; a !== s; ++a) e.setTextureCube(t3[a] || ec, r[a]);
}
function Sf(i14, t3, e) {
  let n = this.cache, s = t3.length, r = Gr(e, s);
  ce(n, r) || (i14.uniform1iv(this.addr, r), he(n, r));
  for (let a = 0; a !== s; ++a) e.setTexture2DArray(t3[a] || jl, r[a]);
}
function bf(i14) {
  switch (i14) {
    case 5126:
      return sf;
    case 35664:
      return rf;
    case 35665:
      return af;
    case 35666:
      return of;
    case 35674:
      return lf;
    case 35675:
      return cf;
    case 35676:
      return hf;
    case 5124:
    case 35670:
      return uf;
    case 35667:
    case 35671:
      return df;
    case 35668:
    case 35672:
      return ff;
    case 35669:
    case 35673:
      return pf;
    case 5125:
      return mf;
    case 36294:
      return gf;
    case 36295:
      return _f;
    case 36296:
      return xf;
    case 35678:
    case 36198:
    case 36298:
    case 36306:
    case 35682:
      return vf;
    case 35679:
    case 36299:
    case 36307:
      return yf;
    case 35680:
    case 36300:
    case 36308:
    case 36293:
      return Mf;
    case 36289:
    case 36303:
    case 36311:
    case 36292:
      return Sf;
  }
}
var to = class {
  constructor(t3, e, n) {
    this.id = t3, this.addr = n, this.cache = [], this.type = e.type, this.setValue = nf(e.type);
  }
};
var eo = class {
  constructor(t3, e, n) {
    this.id = t3, this.addr = n, this.cache = [], this.type = e.type, this.size = e.size, this.setValue = bf(e.type);
  }
};
var no = class {
  constructor(t3) {
    this.id = t3, this.seq = [], this.map = {};
  }
  setValue(t3, e, n) {
    let s = this.seq;
    for (let r = 0, a = s.length; r !== a; ++r) {
      let o = s[r];
      o.setValue(t3, e[o.id], n);
    }
  }
};
var ja = /(\w+)(\])?(\[|\.)?/g;
function Vl(i14, t3) {
  i14.seq.push(t3), i14.map[t3.id] = t3;
}
function Ef(i14, t3, e) {
  let n = i14.name, s = n.length;
  for (ja.lastIndex = 0; ; ) {
    let r = ja.exec(n), a = ja.lastIndex, o = r[1], c = r[2] === "]", l = r[3];
    if (c && (o = o | 0), l === void 0 || l === "[" && a + 2 === s) {
      Vl(e, l === void 0 ? new to(o, i14, t3) : new eo(o, i14, t3));
      break;
    } else {
      let d = e.map[o];
      d === void 0 && (d = new no(o), Vl(e, d)), e = d;
    }
  }
}
var Si = class {
  constructor(t3, e) {
    this.seq = [], this.map = {};
    let n = t3.getProgramParameter(e, t3.ACTIVE_UNIFORMS);
    for (let s = 0; s < n; ++s) {
      let r = t3.getActiveUniform(e, s), a = t3.getUniformLocation(e, r.name);
      Ef(r, a, this);
    }
  }
  setValue(t3, e, n, s) {
    let r = this.map[e];
    r !== void 0 && r.setValue(t3, n, s);
  }
  setOptional(t3, e, n) {
    let s = e[n];
    s !== void 0 && this.setValue(t3, n, s);
  }
  static upload(t3, e, n, s) {
    for (let r = 0, a = e.length; r !== a; ++r) {
      let o = e[r], c = n[o.id];
      c.needsUpdate !== false && o.setValue(t3, c.value, s);
    }
  }
  static seqWithValue(t3, e) {
    let n = [];
    for (let s = 0, r = t3.length; s !== r; ++s) {
      let a = t3[s];
      a.id in e && n.push(a);
    }
    return n;
  }
};
function kl(i14, t3, e) {
  let n = i14.createShader(t3);
  return i14.shaderSource(n, e), i14.compileShader(n), n;
}
var Tf = 37297;
var Af = 0;
function wf(i14, t3) {
  let e = i14.split(`
`), n = [], s = Math.max(t3 - 6, 0), r = Math.min(t3 + 6, e.length);
  for (let a = s; a < r; a++) {
    let o = a + 1;
    n.push(`${o === t3 ? ">" : " "} ${o}: ${e[a]}`);
  }
  return n.join(`
`);
}
var Hl = new Lt();
function Cf(i14) {
  kt._getMatrix(Hl, kt.workingColorSpace, i14);
  let t3 = `mat3( ${Hl.elements.map((e) => e.toFixed(4))} )`;
  switch (kt.getTransfer(i14)) {
    case Pi:
      return [t3, "LinearTransferOETF"];
    case qt:
      return [t3, "sRGBTransferOETF"];
    default:
      return console.warn("THREE.WebGLProgram: Unsupported color space: ", i14), [t3, "LinearTransferOETF"];
  }
}
function Gl(i14, t3, e) {
  let n = i14.getShaderParameter(t3, i14.COMPILE_STATUS), r = (i14.getShaderInfoLog(t3) || "").trim();
  if (n && r === "") return "";
  let a = /ERROR: 0:(\d+)/.exec(r);
  if (a) {
    let o = parseInt(a[1]);
    return e.toUpperCase() + `

` + r + `

` + wf(i14.getShaderSource(t3), o);
  } else return r;
}
function Rf(i14, t3) {
  let e = Cf(t3);
  return [`vec4 ${i14}( vec4 value ) {`, `	return ${e[1]}( vec4( value.rgb * ${e[0]}, value.a ) );`, "}"].join(`
`);
}
function If(i14, t3) {
  let e;
  switch (t3) {
    case rl:
      e = "Linear";
      break;
    case al:
      e = "Reinhard";
      break;
    case ol:
      e = "Cineon";
      break;
    case ll:
      e = "ACESFilmic";
      break;
    case hl:
      e = "AgX";
      break;
    case ul:
      e = "Neutral";
      break;
    case cl:
      e = "Custom";
      break;
    default:
      console.warn("THREE.WebGLProgram: Unsupported toneMapping:", t3), e = "Linear";
  }
  return "vec3 " + i14 + "( vec3 color ) { return " + e + "ToneMapping( color ); }";
}
var kr = new F();
function Pf() {
  kt.getLuminanceCoefficients(kr);
  let i14 = kr.x.toFixed(4), t3 = kr.y.toFixed(4), e = kr.z.toFixed(4);
  return ["float luminance( const in vec3 rgb ) {", `	const vec3 weights = vec3( ${i14}, ${t3}, ${e} );`, "	return dot( weights, rgb );", "}"].join(`
`);
}
function Lf(i14) {
  return [i14.extensionClipCullDistance ? "#extension GL_ANGLE_clip_cull_distance : require" : "", i14.extensionMultiDraw ? "#extension GL_ANGLE_multi_draw : require" : ""].filter(ji).join(`
`);
}
function Df(i14) {
  let t3 = [];
  for (let e in i14) {
    let n = i14[e];
    n !== false && t3.push("#define " + e + " " + n);
  }
  return t3.join(`
`);
}
function Uf(i14, t3) {
  let e = {}, n = i14.getProgramParameter(t3, i14.ACTIVE_ATTRIBUTES);
  for (let s = 0; s < n; s++) {
    let r = i14.getActiveAttrib(t3, s), a = r.name, o = 1;
    r.type === i14.FLOAT_MAT2 && (o = 2), r.type === i14.FLOAT_MAT3 && (o = 3), r.type === i14.FLOAT_MAT4 && (o = 4), e[a] = { type: r.type, location: i14.getAttribLocation(t3, a), locationSize: o };
  }
  return e;
}
function ji(i14) {
  return i14 !== "";
}
function Wl(i14, t3) {
  let e = t3.numSpotLightShadows + t3.numSpotLightMaps - t3.numSpotLightShadowsWithMaps;
  return i14.replace(/NUM_DIR_LIGHTS/g, t3.numDirLights).replace(/NUM_SPOT_LIGHTS/g, t3.numSpotLights).replace(/NUM_SPOT_LIGHT_MAPS/g, t3.numSpotLightMaps).replace(/NUM_SPOT_LIGHT_COORDS/g, e).replace(/NUM_RECT_AREA_LIGHTS/g, t3.numRectAreaLights).replace(/NUM_POINT_LIGHTS/g, t3.numPointLights).replace(/NUM_HEMI_LIGHTS/g, t3.numHemiLights).replace(/NUM_DIR_LIGHT_SHADOWS/g, t3.numDirLightShadows).replace(/NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS/g, t3.numSpotLightShadowsWithMaps).replace(/NUM_SPOT_LIGHT_SHADOWS/g, t3.numSpotLightShadows).replace(/NUM_POINT_LIGHT_SHADOWS/g, t3.numPointLightShadows);
}
function Xl(i14, t3) {
  return i14.replace(/NUM_CLIPPING_PLANES/g, t3.numClippingPlanes).replace(/UNION_CLIPPING_PLANES/g, t3.numClippingPlanes - t3.numClipIntersection);
}
var Nf = /^[ \t]*#include +<([\w\d./]+)>/gm;
function io(i14) {
  return i14.replace(Nf, Of);
}
var Ff = /* @__PURE__ */ new Map();
function Of(i14, t3) {
  let e = Nt[t3];
  if (e === void 0) {
    let n = Ff.get(t3);
    if (n !== void 0) e = Nt[n], console.warn('THREE.WebGLRenderer: Shader chunk "%s" has been deprecated. Use "%s" instead.', t3, n);
    else throw new Error("Can not resolve #include <" + t3 + ">");
  }
  return io(e);
}
var Bf = /#pragma unroll_loop_start\s+for\s*\(\s*int\s+i\s*=\s*(\d+)\s*;\s*i\s*<\s*(\d+)\s*;\s*i\s*\+\+\s*\)\s*{([\s\S]+?)}\s+#pragma unroll_loop_end/g;
function ql(i14) {
  return i14.replace(Bf, zf);
}
function zf(i14, t3, e, n) {
  let s = "";
  for (let r = parseInt(t3); r < parseInt(e); r++) s += n.replace(/\[\s*i\s*\]/g, "[ " + r + " ]").replace(/UNROLLED_LOOP_INDEX/g, r);
  return s;
}
function Yl(i14) {
  let t3 = `precision ${i14.precision} float;
	precision ${i14.precision} int;
	precision ${i14.precision} sampler2D;
	precision ${i14.precision} samplerCube;
	precision ${i14.precision} sampler3D;
	precision ${i14.precision} sampler2DArray;
	precision ${i14.precision} sampler2DShadow;
	precision ${i14.precision} samplerCubeShadow;
	precision ${i14.precision} sampler2DArrayShadow;
	precision ${i14.precision} isampler2D;
	precision ${i14.precision} isampler3D;
	precision ${i14.precision} isamplerCube;
	precision ${i14.precision} isampler2DArray;
	precision ${i14.precision} usampler2D;
	precision ${i14.precision} usampler3D;
	precision ${i14.precision} usamplerCube;
	precision ${i14.precision} usampler2DArray;
	`;
  return i14.precision === "highp" ? t3 += `
#define HIGH_PRECISION` : i14.precision === "mediump" ? t3 += `
#define MEDIUM_PRECISION` : i14.precision === "lowp" && (t3 += `
#define LOW_PRECISION`), t3;
}
function Vf(i14) {
  let t3 = "SHADOWMAP_TYPE_BASIC";
  return i14.shadowMapType === Aa ? t3 = "SHADOWMAP_TYPE_PCF" : i14.shadowMapType === Bo ? t3 = "SHADOWMAP_TYPE_PCF_SOFT" : i14.shadowMapType === Je && (t3 = "SHADOWMAP_TYPE_VSM"), t3;
}
function kf(i14) {
  let t3 = "ENVMAP_TYPE_CUBE";
  if (i14.envMap) switch (i14.envMapMode) {
    case Hn:
    case Gn:
      t3 = "ENVMAP_TYPE_CUBE";
      break;
    case qi:
      t3 = "ENVMAP_TYPE_CUBE_UV";
      break;
  }
  return t3;
}
function Hf(i14) {
  let t3 = "ENVMAP_MODE_REFLECTION";
  if (i14.envMap) switch (i14.envMapMode) {
    case Gn:
      t3 = "ENVMAP_MODE_REFRACTION";
      break;
  }
  return t3;
}
function Gf(i14) {
  let t3 = "ENVMAP_BLENDING_NONE";
  if (i14.envMap) switch (i14.combine) {
    case Ia:
      t3 = "ENVMAP_BLENDING_MULTIPLY";
      break;
    case il:
      t3 = "ENVMAP_BLENDING_MIX";
      break;
    case sl:
      t3 = "ENVMAP_BLENDING_ADD";
      break;
  }
  return t3;
}
function Wf(i14) {
  let t3 = i14.envMapCubeUVHeight;
  if (t3 === null) return null;
  let e = Math.log2(t3) - 2, n = 1 / t3;
  return { texelWidth: 1 / (3 * Math.max(Math.pow(2, e), 112)), texelHeight: n, maxMip: e };
}
function Xf(i14, t3, e, n) {
  let s = i14.getContext(), r = e.defines, a = e.vertexShader, o = e.fragmentShader, c = Vf(e), l = kf(e), u = Hf(e), d = Gf(e), f = Wf(e), m = Lf(e), x = Df(r), v = s.createProgram(), p, h, A = e.glslVersion ? "#version " + e.glslVersion + `
` : "";
  e.isRawShaderMaterial ? (p = ["#define SHADER_TYPE " + e.shaderType, "#define SHADER_NAME " + e.shaderName, x].filter(ji).join(`
`), p.length > 0 && (p += `
`), h = ["#define SHADER_TYPE " + e.shaderType, "#define SHADER_NAME " + e.shaderName, x].filter(ji).join(`
`), h.length > 0 && (h += `
`)) : (p = [Yl(e), "#define SHADER_TYPE " + e.shaderType, "#define SHADER_NAME " + e.shaderName, x, e.extensionClipCullDistance ? "#define USE_CLIP_DISTANCE" : "", e.batching ? "#define USE_BATCHING" : "", e.batchingColor ? "#define USE_BATCHING_COLOR" : "", e.instancing ? "#define USE_INSTANCING" : "", e.instancingColor ? "#define USE_INSTANCING_COLOR" : "", e.instancingMorph ? "#define USE_INSTANCING_MORPH" : "", e.useFog && e.fog ? "#define USE_FOG" : "", e.useFog && e.fogExp2 ? "#define FOG_EXP2" : "", e.map ? "#define USE_MAP" : "", e.envMap ? "#define USE_ENVMAP" : "", e.envMap ? "#define " + u : "", e.lightMap ? "#define USE_LIGHTMAP" : "", e.aoMap ? "#define USE_AOMAP" : "", e.bumpMap ? "#define USE_BUMPMAP" : "", e.normalMap ? "#define USE_NORMALMAP" : "", e.normalMapObjectSpace ? "#define USE_NORMALMAP_OBJECTSPACE" : "", e.normalMapTangentSpace ? "#define USE_NORMALMAP_TANGENTSPACE" : "", e.displacementMap ? "#define USE_DISPLACEMENTMAP" : "", e.emissiveMap ? "#define USE_EMISSIVEMAP" : "", e.anisotropy ? "#define USE_ANISOTROPY" : "", e.anisotropyMap ? "#define USE_ANISOTROPYMAP" : "", e.clearcoatMap ? "#define USE_CLEARCOATMAP" : "", e.clearcoatRoughnessMap ? "#define USE_CLEARCOAT_ROUGHNESSMAP" : "", e.clearcoatNormalMap ? "#define USE_CLEARCOAT_NORMALMAP" : "", e.iridescenceMap ? "#define USE_IRIDESCENCEMAP" : "", e.iridescenceThicknessMap ? "#define USE_IRIDESCENCE_THICKNESSMAP" : "", e.specularMap ? "#define USE_SPECULARMAP" : "", e.specularColorMap ? "#define USE_SPECULAR_COLORMAP" : "", e.specularIntensityMap ? "#define USE_SPECULAR_INTENSITYMAP" : "", e.roughnessMap ? "#define USE_ROUGHNESSMAP" : "", e.metalnessMap ? "#define USE_METALNESSMAP" : "", e.alphaMap ? "#define USE_ALPHAMAP" : "", e.alphaHash ? "#define USE_ALPHAHASH" : "", e.transmission ? "#define USE_TRANSMISSION" : "", e.transmissionMap ? "#define USE_TRANSMISSIONMAP" : "", e.thicknessMap ? "#define USE_THICKNESSMAP" : "", e.sheenColorMap ? "#define USE_SHEEN_COLORMAP" : "", e.sheenRoughnessMap ? "#define USE_SHEEN_ROUGHNESSMAP" : "", e.mapUv ? "#define MAP_UV " + e.mapUv : "", e.alphaMapUv ? "#define ALPHAMAP_UV " + e.alphaMapUv : "", e.lightMapUv ? "#define LIGHTMAP_UV " + e.lightMapUv : "", e.aoMapUv ? "#define AOMAP_UV " + e.aoMapUv : "", e.emissiveMapUv ? "#define EMISSIVEMAP_UV " + e.emissiveMapUv : "", e.bumpMapUv ? "#define BUMPMAP_UV " + e.bumpMapUv : "", e.normalMapUv ? "#define NORMALMAP_UV " + e.normalMapUv : "", e.displacementMapUv ? "#define DISPLACEMENTMAP_UV " + e.displacementMapUv : "", e.metalnessMapUv ? "#define METALNESSMAP_UV " + e.metalnessMapUv : "", e.roughnessMapUv ? "#define ROUGHNESSMAP_UV " + e.roughnessMapUv : "", e.anisotropyMapUv ? "#define ANISOTROPYMAP_UV " + e.anisotropyMapUv : "", e.clearcoatMapUv ? "#define CLEARCOATMAP_UV " + e.clearcoatMapUv : "", e.clearcoatNormalMapUv ? "#define CLEARCOAT_NORMALMAP_UV " + e.clearcoatNormalMapUv : "", e.clearcoatRoughnessMapUv ? "#define CLEARCOAT_ROUGHNESSMAP_UV " + e.clearcoatRoughnessMapUv : "", e.iridescenceMapUv ? "#define IRIDESCENCEMAP_UV " + e.iridescenceMapUv : "", e.iridescenceThicknessMapUv ? "#define IRIDESCENCE_THICKNESSMAP_UV " + e.iridescenceThicknessMapUv : "", e.sheenColorMapUv ? "#define SHEEN_COLORMAP_UV " + e.sheenColorMapUv : "", e.sheenRoughnessMapUv ? "#define SHEEN_ROUGHNESSMAP_UV " + e.sheenRoughnessMapUv : "", e.specularMapUv ? "#define SPECULARMAP_UV " + e.specularMapUv : "", e.specularColorMapUv ? "#define SPECULAR_COLORMAP_UV " + e.specularColorMapUv : "", e.specularIntensityMapUv ? "#define SPECULAR_INTENSITYMAP_UV " + e.specularIntensityMapUv : "", e.transmissionMapUv ? "#define TRANSMISSIONMAP_UV " + e.transmissionMapUv : "", e.thicknessMapUv ? "#define THICKNESSMAP_UV " + e.thicknessMapUv : "", e.vertexTangents && e.flatShading === false ? "#define USE_TANGENT" : "", e.vertexColors ? "#define USE_COLOR" : "", e.vertexAlphas ? "#define USE_COLOR_ALPHA" : "", e.vertexUv1s ? "#define USE_UV1" : "", e.vertexUv2s ? "#define USE_UV2" : "", e.vertexUv3s ? "#define USE_UV3" : "", e.pointsUvs ? "#define USE_POINTS_UV" : "", e.flatShading ? "#define FLAT_SHADED" : "", e.skinning ? "#define USE_SKINNING" : "", e.morphTargets ? "#define USE_MORPHTARGETS" : "", e.morphNormals && e.flatShading === false ? "#define USE_MORPHNORMALS" : "", e.morphColors ? "#define USE_MORPHCOLORS" : "", e.morphTargetsCount > 0 ? "#define MORPHTARGETS_TEXTURE_STRIDE " + e.morphTextureStride : "", e.morphTargetsCount > 0 ? "#define MORPHTARGETS_COUNT " + e.morphTargetsCount : "", e.doubleSided ? "#define DOUBLE_SIDED" : "", e.flipSided ? "#define FLIP_SIDED" : "", e.shadowMapEnabled ? "#define USE_SHADOWMAP" : "", e.shadowMapEnabled ? "#define " + c : "", e.sizeAttenuation ? "#define USE_SIZEATTENUATION" : "", e.numLightProbes > 0 ? "#define USE_LIGHT_PROBES" : "", e.logarithmicDepthBuffer ? "#define USE_LOGARITHMIC_DEPTH_BUFFER" : "", e.reversedDepthBuffer ? "#define USE_REVERSED_DEPTH_BUFFER" : "", "uniform mat4 modelMatrix;", "uniform mat4 modelViewMatrix;", "uniform mat4 projectionMatrix;", "uniform mat4 viewMatrix;", "uniform mat3 normalMatrix;", "uniform vec3 cameraPosition;", "uniform bool isOrthographic;", "#ifdef USE_INSTANCING", "	attribute mat4 instanceMatrix;", "#endif", "#ifdef USE_INSTANCING_COLOR", "	attribute vec3 instanceColor;", "#endif", "#ifdef USE_INSTANCING_MORPH", "	uniform sampler2D morphTexture;", "#endif", "attribute vec3 position;", "attribute vec3 normal;", "attribute vec2 uv;", "#ifdef USE_UV1", "	attribute vec2 uv1;", "#endif", "#ifdef USE_UV2", "	attribute vec2 uv2;", "#endif", "#ifdef USE_UV3", "	attribute vec2 uv3;", "#endif", "#ifdef USE_TANGENT", "	attribute vec4 tangent;", "#endif", "#if defined( USE_COLOR_ALPHA )", "	attribute vec4 color;", "#elif defined( USE_COLOR )", "	attribute vec3 color;", "#endif", "#ifdef USE_SKINNING", "	attribute vec4 skinIndex;", "	attribute vec4 skinWeight;", "#endif", `
`].filter(ji).join(`
`), h = [Yl(e), "#define SHADER_TYPE " + e.shaderType, "#define SHADER_NAME " + e.shaderName, x, e.useFog && e.fog ? "#define USE_FOG" : "", e.useFog && e.fogExp2 ? "#define FOG_EXP2" : "", e.alphaToCoverage ? "#define ALPHA_TO_COVERAGE" : "", e.map ? "#define USE_MAP" : "", e.matcap ? "#define USE_MATCAP" : "", e.envMap ? "#define USE_ENVMAP" : "", e.envMap ? "#define " + l : "", e.envMap ? "#define " + u : "", e.envMap ? "#define " + d : "", f ? "#define CUBEUV_TEXEL_WIDTH " + f.texelWidth : "", f ? "#define CUBEUV_TEXEL_HEIGHT " + f.texelHeight : "", f ? "#define CUBEUV_MAX_MIP " + f.maxMip + ".0" : "", e.lightMap ? "#define USE_LIGHTMAP" : "", e.aoMap ? "#define USE_AOMAP" : "", e.bumpMap ? "#define USE_BUMPMAP" : "", e.normalMap ? "#define USE_NORMALMAP" : "", e.normalMapObjectSpace ? "#define USE_NORMALMAP_OBJECTSPACE" : "", e.normalMapTangentSpace ? "#define USE_NORMALMAP_TANGENTSPACE" : "", e.emissiveMap ? "#define USE_EMISSIVEMAP" : "", e.anisotropy ? "#define USE_ANISOTROPY" : "", e.anisotropyMap ? "#define USE_ANISOTROPYMAP" : "", e.clearcoat ? "#define USE_CLEARCOAT" : "", e.clearcoatMap ? "#define USE_CLEARCOATMAP" : "", e.clearcoatRoughnessMap ? "#define USE_CLEARCOAT_ROUGHNESSMAP" : "", e.clearcoatNormalMap ? "#define USE_CLEARCOAT_NORMALMAP" : "", e.dispersion ? "#define USE_DISPERSION" : "", e.iridescence ? "#define USE_IRIDESCENCE" : "", e.iridescenceMap ? "#define USE_IRIDESCENCEMAP" : "", e.iridescenceThicknessMap ? "#define USE_IRIDESCENCE_THICKNESSMAP" : "", e.specularMap ? "#define USE_SPECULARMAP" : "", e.specularColorMap ? "#define USE_SPECULAR_COLORMAP" : "", e.specularIntensityMap ? "#define USE_SPECULAR_INTENSITYMAP" : "", e.roughnessMap ? "#define USE_ROUGHNESSMAP" : "", e.metalnessMap ? "#define USE_METALNESSMAP" : "", e.alphaMap ? "#define USE_ALPHAMAP" : "", e.alphaTest ? "#define USE_ALPHATEST" : "", e.alphaHash ? "#define USE_ALPHAHASH" : "", e.sheen ? "#define USE_SHEEN" : "", e.sheenColorMap ? "#define USE_SHEEN_COLORMAP" : "", e.sheenRoughnessMap ? "#define USE_SHEEN_ROUGHNESSMAP" : "", e.transmission ? "#define USE_TRANSMISSION" : "", e.transmissionMap ? "#define USE_TRANSMISSIONMAP" : "", e.thicknessMap ? "#define USE_THICKNESSMAP" : "", e.vertexTangents && e.flatShading === false ? "#define USE_TANGENT" : "", e.vertexColors || e.instancingColor || e.batchingColor ? "#define USE_COLOR" : "", e.vertexAlphas ? "#define USE_COLOR_ALPHA" : "", e.vertexUv1s ? "#define USE_UV1" : "", e.vertexUv2s ? "#define USE_UV2" : "", e.vertexUv3s ? "#define USE_UV3" : "", e.pointsUvs ? "#define USE_POINTS_UV" : "", e.gradientMap ? "#define USE_GRADIENTMAP" : "", e.flatShading ? "#define FLAT_SHADED" : "", e.doubleSided ? "#define DOUBLE_SIDED" : "", e.flipSided ? "#define FLIP_SIDED" : "", e.shadowMapEnabled ? "#define USE_SHADOWMAP" : "", e.shadowMapEnabled ? "#define " + c : "", e.premultipliedAlpha ? "#define PREMULTIPLIED_ALPHA" : "", e.numLightProbes > 0 ? "#define USE_LIGHT_PROBES" : "", e.decodeVideoTexture ? "#define DECODE_VIDEO_TEXTURE" : "", e.decodeVideoTextureEmissive ? "#define DECODE_VIDEO_TEXTURE_EMISSIVE" : "", e.logarithmicDepthBuffer ? "#define USE_LOGARITHMIC_DEPTH_BUFFER" : "", e.reversedDepthBuffer ? "#define USE_REVERSED_DEPTH_BUFFER" : "", "uniform mat4 viewMatrix;", "uniform vec3 cameraPosition;", "uniform bool isOrthographic;", e.toneMapping !== un ? "#define TONE_MAPPING" : "", e.toneMapping !== un ? Nt.tonemapping_pars_fragment : "", e.toneMapping !== un ? If("toneMapping", e.toneMapping) : "", e.dithering ? "#define DITHERING" : "", e.opaque ? "#define OPAQUE" : "", Nt.colorspace_pars_fragment, Rf("linearToOutputTexel", e.outputColorSpace), Pf(), e.useDepthPacking ? "#define DEPTH_PACKING " + e.depthPacking : "", `
`].filter(ji).join(`
`)), a = io(a), a = Wl(a, e), a = Xl(a, e), o = io(o), o = Wl(o, e), o = Xl(o, e), a = ql(a), o = ql(o), e.isRawShaderMaterial !== true && (A = `#version 300 es
`, p = [m, "#define attribute in", "#define varying out", "#define texture2D texture"].join(`
`) + `
` + p, h = ["#define varying in", e.glslVersion === Ha ? "" : "layout(location = 0) out highp vec4 pc_fragColor;", e.glslVersion === Ha ? "" : "#define gl_FragColor pc_fragColor", "#define gl_FragDepthEXT gl_FragDepth", "#define texture2D texture", "#define textureCube texture", "#define texture2DProj textureProj", "#define texture2DLodEXT textureLod", "#define texture2DProjLodEXT textureProjLod", "#define textureCubeLodEXT textureLod", "#define texture2DGradEXT textureGrad", "#define texture2DProjGradEXT textureProjGrad", "#define textureCubeGradEXT textureGrad"].join(`
`) + `
` + h);
  let T = A + p + a, b = A + h + o, R = kl(s, s.VERTEX_SHADER, T), w = kl(s, s.FRAGMENT_SHADER, b);
  s.attachShader(v, R), s.attachShader(v, w), e.index0AttributeName !== void 0 ? s.bindAttribLocation(v, 0, e.index0AttributeName) : e.morphTargets === true && s.bindAttribLocation(v, 0, "position"), s.linkProgram(v);
  function P(I) {
    if (i14.debug.checkShaderErrors) {
      let z = s.getProgramInfoLog(v) || "", H = s.getShaderInfoLog(R) || "", X = s.getShaderInfoLog(w) || "", Z = z.trim(), W = H.trim(), et = X.trim(), V = true, rt = true;
      if (s.getProgramParameter(v, s.LINK_STATUS) === false) if (V = false, typeof i14.debug.onShaderError == "function") i14.debug.onShaderError(s, v, R, w);
      else {
        let ct = Gl(s, R, "vertex"), St = Gl(s, w, "fragment");
        console.error("THREE.WebGLProgram: Shader Error " + s.getError() + " - VALIDATE_STATUS " + s.getProgramParameter(v, s.VALIDATE_STATUS) + `

Material Name: ` + I.name + `
Material Type: ` + I.type + `

Program Info Log: ` + Z + `
` + ct + `
` + St);
      }
      else Z !== "" ? console.warn("THREE.WebGLProgram: Program Info Log:", Z) : (W === "" || et === "") && (rt = false);
      rt && (I.diagnostics = { runnable: V, programLog: Z, vertexShader: { log: W, prefix: p }, fragmentShader: { log: et, prefix: h } });
    }
    s.deleteShader(R), s.deleteShader(w), N = new Si(s, v), M = Uf(s, v);
  }
  let N;
  this.getUniforms = function() {
    return N === void 0 && P(this), N;
  };
  let M;
  this.getAttributes = function() {
    return M === void 0 && P(this), M;
  };
  let y = e.rendererExtensionParallelShaderCompile === false;
  return this.isReady = function() {
    return y === false && (y = s.getProgramParameter(v, Tf)), y;
  }, this.destroy = function() {
    n.releaseStatesOfProgram(this), s.deleteProgram(v), this.program = void 0;
  }, this.type = e.shaderType, this.name = e.shaderName, this.id = Af++, this.cacheKey = t3, this.usedTimes = 1, this.program = v, this.vertexShader = R, this.fragmentShader = w, this;
}
var qf = 0;
var so = class {
  constructor() {
    this.shaderCache = /* @__PURE__ */ new Map(), this.materialCache = /* @__PURE__ */ new Map();
  }
  update(t3) {
    let e = t3.vertexShader, n = t3.fragmentShader, s = this._getShaderStage(e), r = this._getShaderStage(n), a = this._getShaderCacheForMaterial(t3);
    return a.has(s) === false && (a.add(s), s.usedTimes++), a.has(r) === false && (a.add(r), r.usedTimes++), this;
  }
  remove(t3) {
    let e = this.materialCache.get(t3);
    for (let n of e) n.usedTimes--, n.usedTimes === 0 && this.shaderCache.delete(n.code);
    return this.materialCache.delete(t3), this;
  }
  getVertexShaderID(t3) {
    return this._getShaderStage(t3.vertexShader).id;
  }
  getFragmentShaderID(t3) {
    return this._getShaderStage(t3.fragmentShader).id;
  }
  dispose() {
    this.shaderCache.clear(), this.materialCache.clear();
  }
  _getShaderCacheForMaterial(t3) {
    let e = this.materialCache, n = e.get(t3);
    return n === void 0 && (n = /* @__PURE__ */ new Set(), e.set(t3, n)), n;
  }
  _getShaderStage(t3) {
    let e = this.shaderCache, n = e.get(t3);
    return n === void 0 && (n = new ro(t3), e.set(t3, n)), n;
  }
};
var ro = class {
  constructor(t3) {
    this.id = qf++, this.code = t3, this.usedTimes = 0;
  }
};
function Yf(i14, t3, e, n, s, r, a) {
  let o = new Ni(), c = new so(), l = /* @__PURE__ */ new Set(), u = [], d = s.logarithmicDepthBuffer, f = s.vertexTextures, m = s.precision, x = { MeshDepthMaterial: "depth", MeshDistanceMaterial: "distanceRGBA", MeshNormalMaterial: "normal", MeshBasicMaterial: "basic", MeshLambertMaterial: "lambert", MeshPhongMaterial: "phong", MeshToonMaterial: "toon", MeshStandardMaterial: "physical", MeshPhysicalMaterial: "physical", MeshMatcapMaterial: "matcap", LineBasicMaterial: "basic", LineDashedMaterial: "dashed", PointsMaterial: "points", ShadowMaterial: "shadow", SpriteMaterial: "sprite" };
  function v(M) {
    return l.add(M), M === 0 ? "uv" : `uv${M}`;
  }
  function p(M, y, I, z, H) {
    let X = z.fog, Z = H.geometry, W = M.isMeshStandardMaterial ? z.environment : null, et = (M.isMeshStandardMaterial ? e : t3).get(M.envMap || W), V = et && et.mapping === qi ? et.image.height : null, rt = x[M.type];
    M.precision !== null && (m = s.getMaxPrecision(M.precision), m !== M.precision && console.warn("THREE.WebGLProgram.getParameters:", M.precision, "not supported, using", m, "instead."));
    let ct = Z.morphAttributes.position || Z.morphAttributes.normal || Z.morphAttributes.color, St = ct !== void 0 ? ct.length : 0, Ft = 0;
    Z.morphAttributes.position !== void 0 && (Ft = 1), Z.morphAttributes.normal !== void 0 && (Ft = 2), Z.morphAttributes.color !== void 0 && (Ft = 3);
    let Jt, jt, Wt, q;
    if (rt) {
      let Xt = Qe[rt];
      Jt = Xt.vertexShader, jt = Xt.fragmentShader;
    } else Jt = M.vertexShader, jt = M.fragmentShader, c.update(M), Wt = c.getVertexShaderID(M), q = c.getFragmentShaderID(M);
    let $2 = i14.getRenderTarget(), dt = i14.state.buffers.depth.getReversed(), Rt = H.isInstancedMesh === true, Mt = H.isBatchedMesh === true, zt = !!M.map, fe = !!M.matcap, E = !!et, te = !!M.aoMap, Pt = !!M.lightMap, wt = !!M.bumpMap, mt = !!M.normalMap, ee = !!M.displacementMap, gt = !!M.emissiveMap, Ut = !!M.metalnessMap, ue = !!M.roughnessMap, ae = M.anisotropy > 0, S = M.clearcoat > 0, g = M.dispersion > 0, U = M.iridescence > 0, G = M.sheen > 0, J = M.transmission > 0, k = ae && !!M.anisotropyMap, yt = S && !!M.clearcoatMap, nt = S && !!M.clearcoatNormalMap, _t = S && !!M.clearcoatRoughnessMap, xt = U && !!M.iridescenceMap, j = U && !!M.iridescenceThicknessMap, lt = G && !!M.sheenColorMap, At = G && !!M.sheenRoughnessMap, vt = !!M.specularMap, at = !!M.specularColorMap, Dt = !!M.specularIntensityMap, C = J && !!M.transmissionMap, tt = J && !!M.thicknessMap, it = !!M.gradientMap, ut = !!M.alphaMap, K = M.alphaTest > 0, Y = !!M.alphaHash, pt = !!M.extensions, It = un;
    M.toneMapped && ($2 === null || $2.isXRRenderTarget === true) && (It = i14.toneMapping);
    let $t = { shaderID: rt, shaderType: M.type, shaderName: M.name, vertexShader: Jt, fragmentShader: jt, defines: M.defines, customVertexShaderID: Wt, customFragmentShaderID: q, isRawShaderMaterial: M.isRawShaderMaterial === true, glslVersion: M.glslVersion, precision: m, batching: Mt, batchingColor: Mt && H._colorsTexture !== null, instancing: Rt, instancingColor: Rt && H.instanceColor !== null, instancingMorph: Rt && H.morphTexture !== null, supportsVertexTextures: f, outputColorSpace: $2 === null ? i14.outputColorSpace : $2.isXRRenderTarget === true ? $2.texture.colorSpace : zn, alphaToCoverage: !!M.alphaToCoverage, map: zt, matcap: fe, envMap: E, envMapMode: E && et.mapping, envMapCubeUVHeight: V, aoMap: te, lightMap: Pt, bumpMap: wt, normalMap: mt, displacementMap: f && ee, emissiveMap: gt, normalMapObjectSpace: mt && M.normalMapType === ml, normalMapTangentSpace: mt && M.normalMapType === Va, metalnessMap: Ut, roughnessMap: ue, anisotropy: ae, anisotropyMap: k, clearcoat: S, clearcoatMap: yt, clearcoatNormalMap: nt, clearcoatRoughnessMap: _t, dispersion: g, iridescence: U, iridescenceMap: xt, iridescenceThicknessMap: j, sheen: G, sheenColorMap: lt, sheenRoughnessMap: At, specularMap: vt, specularColorMap: at, specularIntensityMap: Dt, transmission: J, transmissionMap: C, thicknessMap: tt, gradientMap: it, opaque: M.transparent === false && M.blending === On && M.alphaToCoverage === false, alphaMap: ut, alphaTest: K, alphaHash: Y, combine: M.combine, mapUv: zt && v(M.map.channel), aoMapUv: te && v(M.aoMap.channel), lightMapUv: Pt && v(M.lightMap.channel), bumpMapUv: wt && v(M.bumpMap.channel), normalMapUv: mt && v(M.normalMap.channel), displacementMapUv: ee && v(M.displacementMap.channel), emissiveMapUv: gt && v(M.emissiveMap.channel), metalnessMapUv: Ut && v(M.metalnessMap.channel), roughnessMapUv: ue && v(M.roughnessMap.channel), anisotropyMapUv: k && v(M.anisotropyMap.channel), clearcoatMapUv: yt && v(M.clearcoatMap.channel), clearcoatNormalMapUv: nt && v(M.clearcoatNormalMap.channel), clearcoatRoughnessMapUv: _t && v(M.clearcoatRoughnessMap.channel), iridescenceMapUv: xt && v(M.iridescenceMap.channel), iridescenceThicknessMapUv: j && v(M.iridescenceThicknessMap.channel), sheenColorMapUv: lt && v(M.sheenColorMap.channel), sheenRoughnessMapUv: At && v(M.sheenRoughnessMap.channel), specularMapUv: vt && v(M.specularMap.channel), specularColorMapUv: at && v(M.specularColorMap.channel), specularIntensityMapUv: Dt && v(M.specularIntensityMap.channel), transmissionMapUv: C && v(M.transmissionMap.channel), thicknessMapUv: tt && v(M.thicknessMap.channel), alphaMapUv: ut && v(M.alphaMap.channel), vertexTangents: !!Z.attributes.tangent && (mt || ae), vertexColors: M.vertexColors, vertexAlphas: M.vertexColors === true && !!Z.attributes.color && Z.attributes.color.itemSize === 4, pointsUvs: H.isPoints === true && !!Z.attributes.uv && (zt || ut), fog: !!X, useFog: M.fog === true, fogExp2: !!X && X.isFogExp2, flatShading: M.flatShading === true && M.wireframe === false, sizeAttenuation: M.sizeAttenuation === true, logarithmicDepthBuffer: d, reversedDepthBuffer: dt, skinning: H.isSkinnedMesh === true, morphTargets: Z.morphAttributes.position !== void 0, morphNormals: Z.morphAttributes.normal !== void 0, morphColors: Z.morphAttributes.color !== void 0, morphTargetsCount: St, morphTextureStride: Ft, numDirLights: y.directional.length, numPointLights: y.point.length, numSpotLights: y.spot.length, numSpotLightMaps: y.spotLightMap.length, numRectAreaLights: y.rectArea.length, numHemiLights: y.hemi.length, numDirLightShadows: y.directionalShadowMap.length, numPointLightShadows: y.pointShadowMap.length, numSpotLightShadows: y.spotShadowMap.length, numSpotLightShadowsWithMaps: y.numSpotLightShadowsWithMaps, numLightProbes: y.numLightProbes, numClippingPlanes: a.numPlanes, numClipIntersection: a.numIntersection, dithering: M.dithering, shadowMapEnabled: i14.shadowMap.enabled && I.length > 0, shadowMapType: i14.shadowMap.type, toneMapping: It, decodeVideoTexture: zt && M.map.isVideoTexture === true && kt.getTransfer(M.map.colorSpace) === qt, decodeVideoTextureEmissive: gt && M.emissiveMap.isVideoTexture === true && kt.getTransfer(M.emissiveMap.colorSpace) === qt, premultipliedAlpha: M.premultipliedAlpha, doubleSided: M.side === $e, flipSided: M.side === ve, useDepthPacking: M.depthPacking >= 0, depthPacking: M.depthPacking || 0, index0AttributeName: M.index0AttributeName, extensionClipCullDistance: pt && M.extensions.clipCullDistance === true && n.has("WEBGL_clip_cull_distance"), extensionMultiDraw: (pt && M.extensions.multiDraw === true || Mt) && n.has("WEBGL_multi_draw"), rendererExtensionParallelShaderCompile: n.has("KHR_parallel_shader_compile"), customProgramCacheKey: M.customProgramCacheKey() };
    return $t.vertexUv1s = l.has(1), $t.vertexUv2s = l.has(2), $t.vertexUv3s = l.has(3), l.clear(), $t;
  }
  function h(M) {
    let y = [];
    if (M.shaderID ? y.push(M.shaderID) : (y.push(M.customVertexShaderID), y.push(M.customFragmentShaderID)), M.defines !== void 0) for (let I in M.defines) y.push(I), y.push(M.defines[I]);
    return M.isRawShaderMaterial === false && (A(y, M), T(y, M), y.push(i14.outputColorSpace)), y.push(M.customProgramCacheKey), y.join();
  }
  function A(M, y) {
    M.push(y.precision), M.push(y.outputColorSpace), M.push(y.envMapMode), M.push(y.envMapCubeUVHeight), M.push(y.mapUv), M.push(y.alphaMapUv), M.push(y.lightMapUv), M.push(y.aoMapUv), M.push(y.bumpMapUv), M.push(y.normalMapUv), M.push(y.displacementMapUv), M.push(y.emissiveMapUv), M.push(y.metalnessMapUv), M.push(y.roughnessMapUv), M.push(y.anisotropyMapUv), M.push(y.clearcoatMapUv), M.push(y.clearcoatNormalMapUv), M.push(y.clearcoatRoughnessMapUv), M.push(y.iridescenceMapUv), M.push(y.iridescenceThicknessMapUv), M.push(y.sheenColorMapUv), M.push(y.sheenRoughnessMapUv), M.push(y.specularMapUv), M.push(y.specularColorMapUv), M.push(y.specularIntensityMapUv), M.push(y.transmissionMapUv), M.push(y.thicknessMapUv), M.push(y.combine), M.push(y.fogExp2), M.push(y.sizeAttenuation), M.push(y.morphTargetsCount), M.push(y.morphAttributeCount), M.push(y.numDirLights), M.push(y.numPointLights), M.push(y.numSpotLights), M.push(y.numSpotLightMaps), M.push(y.numHemiLights), M.push(y.numRectAreaLights), M.push(y.numDirLightShadows), M.push(y.numPointLightShadows), M.push(y.numSpotLightShadows), M.push(y.numSpotLightShadowsWithMaps), M.push(y.numLightProbes), M.push(y.shadowMapType), M.push(y.toneMapping), M.push(y.numClippingPlanes), M.push(y.numClipIntersection), M.push(y.depthPacking);
  }
  function T(M, y) {
    o.disableAll(), y.supportsVertexTextures && o.enable(0), y.instancing && o.enable(1), y.instancingColor && o.enable(2), y.instancingMorph && o.enable(3), y.matcap && o.enable(4), y.envMap && o.enable(5), y.normalMapObjectSpace && o.enable(6), y.normalMapTangentSpace && o.enable(7), y.clearcoat && o.enable(8), y.iridescence && o.enable(9), y.alphaTest && o.enable(10), y.vertexColors && o.enable(11), y.vertexAlphas && o.enable(12), y.vertexUv1s && o.enable(13), y.vertexUv2s && o.enable(14), y.vertexUv3s && o.enable(15), y.vertexTangents && o.enable(16), y.anisotropy && o.enable(17), y.alphaHash && o.enable(18), y.batching && o.enable(19), y.dispersion && o.enable(20), y.batchingColor && o.enable(21), y.gradientMap && o.enable(22), M.push(o.mask), o.disableAll(), y.fog && o.enable(0), y.useFog && o.enable(1), y.flatShading && o.enable(2), y.logarithmicDepthBuffer && o.enable(3), y.reversedDepthBuffer && o.enable(4), y.skinning && o.enable(5), y.morphTargets && o.enable(6), y.morphNormals && o.enable(7), y.morphColors && o.enable(8), y.premultipliedAlpha && o.enable(9), y.shadowMapEnabled && o.enable(10), y.doubleSided && o.enable(11), y.flipSided && o.enable(12), y.useDepthPacking && o.enable(13), y.dithering && o.enable(14), y.transmission && o.enable(15), y.sheen && o.enable(16), y.opaque && o.enable(17), y.pointsUvs && o.enable(18), y.decodeVideoTexture && o.enable(19), y.decodeVideoTextureEmissive && o.enable(20), y.alphaToCoverage && o.enable(21), M.push(o.mask);
  }
  function b(M) {
    let y = x[M.type], I;
    if (y) {
      let z = Qe[y];
      I = Al.clone(z.uniforms);
    } else I = M.uniforms;
    return I;
  }
  function R(M, y) {
    let I;
    for (let z = 0, H = u.length; z < H; z++) {
      let X = u[z];
      if (X.cacheKey === y) {
        I = X, ++I.usedTimes;
        break;
      }
    }
    return I === void 0 && (I = new Xf(i14, y, M, r), u.push(I)), I;
  }
  function w(M) {
    if (--M.usedTimes === 0) {
      let y = u.indexOf(M);
      u[y] = u[u.length - 1], u.pop(), M.destroy();
    }
  }
  function P(M) {
    c.remove(M);
  }
  function N() {
    c.dispose();
  }
  return { getParameters: p, getProgramCacheKey: h, getUniforms: b, acquireProgram: R, releaseProgram: w, releaseShaderCache: P, programs: u, dispose: N };
}
function Zf() {
  let i14 = /* @__PURE__ */ new WeakMap();
  function t3(a) {
    return i14.has(a);
  }
  function e(a) {
    let o = i14.get(a);
    return o === void 0 && (o = {}, i14.set(a, o)), o;
  }
  function n(a) {
    i14.delete(a);
  }
  function s(a, o, c) {
    i14.get(a)[o] = c;
  }
  function r() {
    i14 = /* @__PURE__ */ new WeakMap();
  }
  return { has: t3, get: e, remove: n, update: s, dispose: r };
}
function Jf(i14, t3) {
  return i14.groupOrder !== t3.groupOrder ? i14.groupOrder - t3.groupOrder : i14.renderOrder !== t3.renderOrder ? i14.renderOrder - t3.renderOrder : i14.material.id !== t3.material.id ? i14.material.id - t3.material.id : i14.z !== t3.z ? i14.z - t3.z : i14.id - t3.id;
}
function Zl(i14, t3) {
  return i14.groupOrder !== t3.groupOrder ? i14.groupOrder - t3.groupOrder : i14.renderOrder !== t3.renderOrder ? i14.renderOrder - t3.renderOrder : i14.z !== t3.z ? t3.z - i14.z : i14.id - t3.id;
}
function Jl() {
  let i14 = [], t3 = 0, e = [], n = [], s = [];
  function r() {
    t3 = 0, e.length = 0, n.length = 0, s.length = 0;
  }
  function a(d, f, m, x, v, p) {
    let h = i14[t3];
    return h === void 0 ? (h = { id: d.id, object: d, geometry: f, material: m, groupOrder: x, renderOrder: d.renderOrder, z: v, group: p }, i14[t3] = h) : (h.id = d.id, h.object = d, h.geometry = f, h.material = m, h.groupOrder = x, h.renderOrder = d.renderOrder, h.z = v, h.group = p), t3++, h;
  }
  function o(d, f, m, x, v, p) {
    let h = a(d, f, m, x, v, p);
    m.transmission > 0 ? n.push(h) : m.transparent === true ? s.push(h) : e.push(h);
  }
  function c(d, f, m, x, v, p) {
    let h = a(d, f, m, x, v, p);
    m.transmission > 0 ? n.unshift(h) : m.transparent === true ? s.unshift(h) : e.unshift(h);
  }
  function l(d, f) {
    e.length > 1 && e.sort(d || Jf), n.length > 1 && n.sort(f || Zl), s.length > 1 && s.sort(f || Zl);
  }
  function u() {
    for (let d = t3, f = i14.length; d < f; d++) {
      let m = i14[d];
      if (m.id === null) break;
      m.id = null, m.object = null, m.geometry = null, m.material = null, m.group = null;
    }
  }
  return { opaque: e, transmissive: n, transparent: s, init: r, push: o, unshift: c, finish: u, sort: l };
}
function $f() {
  let i14 = /* @__PURE__ */ new WeakMap();
  function t3(n, s) {
    let r = i14.get(n), a;
    return r === void 0 ? (a = new Jl(), i14.set(n, [a])) : s >= r.length ? (a = new Jl(), r.push(a)) : a = r[s], a;
  }
  function e() {
    i14 = /* @__PURE__ */ new WeakMap();
  }
  return { get: t3, dispose: e };
}
function Kf() {
  let i14 = {};
  return { get: function(t3) {
    if (i14[t3.id] !== void 0) return i14[t3.id];
    let e;
    switch (t3.type) {
      case "DirectionalLight":
        e = { direction: new F(), color: new Vt() };
        break;
      case "SpotLight":
        e = { position: new F(), direction: new F(), color: new Vt(), distance: 0, coneCos: 0, penumbraCos: 0, decay: 0 };
        break;
      case "PointLight":
        e = { position: new F(), color: new Vt(), distance: 0, decay: 0 };
        break;
      case "HemisphereLight":
        e = { direction: new F(), skyColor: new Vt(), groundColor: new Vt() };
        break;
      case "RectAreaLight":
        e = { color: new Vt(), position: new F(), halfWidth: new F(), halfHeight: new F() };
        break;
    }
    return i14[t3.id] = e, e;
  } };
}
function Qf() {
  let i14 = {};
  return { get: function(t3) {
    if (i14[t3.id] !== void 0) return i14[t3.id];
    let e;
    switch (t3.type) {
      case "DirectionalLight":
        e = { shadowIntensity: 1, shadowBias: 0, shadowNormalBias: 0, shadowRadius: 1, shadowMapSize: new Gt() };
        break;
      case "SpotLight":
        e = { shadowIntensity: 1, shadowBias: 0, shadowNormalBias: 0, shadowRadius: 1, shadowMapSize: new Gt() };
        break;
      case "PointLight":
        e = { shadowIntensity: 1, shadowBias: 0, shadowNormalBias: 0, shadowRadius: 1, shadowMapSize: new Gt(), shadowCameraNear: 1, shadowCameraFar: 1e3 };
        break;
    }
    return i14[t3.id] = e, e;
  } };
}
var jf = 0;
function tp(i14, t3) {
  return (t3.castShadow ? 2 : 0) - (i14.castShadow ? 2 : 0) + (t3.map ? 1 : 0) - (i14.map ? 1 : 0);
}
function ep(i14) {
  let t3 = new Kf(), e = Qf(), n = { version: 0, hash: { directionalLength: -1, pointLength: -1, spotLength: -1, rectAreaLength: -1, hemiLength: -1, numDirectionalShadows: -1, numPointShadows: -1, numSpotShadows: -1, numSpotMaps: -1, numLightProbes: -1 }, ambient: [0, 0, 0], probe: [], directional: [], directionalShadow: [], directionalShadowMap: [], directionalShadowMatrix: [], spot: [], spotLightMap: [], spotShadow: [], spotShadowMap: [], spotLightMatrix: [], rectArea: [], rectAreaLTC1: null, rectAreaLTC2: null, point: [], pointShadow: [], pointShadowMap: [], pointShadowMatrix: [], hemi: [], numSpotLightShadowsWithMaps: 0, numLightProbes: 0 };
  for (let l = 0; l < 9; l++) n.probe.push(new F());
  let s = new F(), r = new oe(), a = new oe();
  function o(l) {
    let u = 0, d = 0, f = 0;
    for (let M = 0; M < 9; M++) n.probe[M].set(0, 0, 0);
    let m = 0, x = 0, v = 0, p = 0, h = 0, A = 0, T = 0, b = 0, R = 0, w = 0, P = 0;
    l.sort(tp);
    for (let M = 0, y = l.length; M < y; M++) {
      let I = l[M], z = I.color, H = I.intensity, X = I.distance, Z = I.shadow && I.shadow.map ? I.shadow.map.texture : null;
      if (I.isAmbientLight) u += z.r * H, d += z.g * H, f += z.b * H;
      else if (I.isLightProbe) {
        for (let W = 0; W < 9; W++) n.probe[W].addScaledVector(I.sh.coefficients[W], H);
        P++;
      } else if (I.isDirectionalLight) {
        let W = t3.get(I);
        if (W.color.copy(I.color).multiplyScalar(I.intensity), I.castShadow) {
          let et = I.shadow, V = e.get(I);
          V.shadowIntensity = et.intensity, V.shadowBias = et.bias, V.shadowNormalBias = et.normalBias, V.shadowRadius = et.radius, V.shadowMapSize = et.mapSize, n.directionalShadow[m] = V, n.directionalShadowMap[m] = Z, n.directionalShadowMatrix[m] = I.shadow.matrix, A++;
        }
        n.directional[m] = W, m++;
      } else if (I.isSpotLight) {
        let W = t3.get(I);
        W.position.setFromMatrixPosition(I.matrixWorld), W.color.copy(z).multiplyScalar(H), W.distance = X, W.coneCos = Math.cos(I.angle), W.penumbraCos = Math.cos(I.angle * (1 - I.penumbra)), W.decay = I.decay, n.spot[v] = W;
        let et = I.shadow;
        if (I.map && (n.spotLightMap[R] = I.map, R++, et.updateMatrices(I), I.castShadow && w++), n.spotLightMatrix[v] = et.matrix, I.castShadow) {
          let V = e.get(I);
          V.shadowIntensity = et.intensity, V.shadowBias = et.bias, V.shadowNormalBias = et.normalBias, V.shadowRadius = et.radius, V.shadowMapSize = et.mapSize, n.spotShadow[v] = V, n.spotShadowMap[v] = Z, b++;
        }
        v++;
      } else if (I.isRectAreaLight) {
        let W = t3.get(I);
        W.color.copy(z).multiplyScalar(H), W.halfWidth.set(I.width * 0.5, 0, 0), W.halfHeight.set(0, I.height * 0.5, 0), n.rectArea[p] = W, p++;
      } else if (I.isPointLight) {
        let W = t3.get(I);
        if (W.color.copy(I.color).multiplyScalar(I.intensity), W.distance = I.distance, W.decay = I.decay, I.castShadow) {
          let et = I.shadow, V = e.get(I);
          V.shadowIntensity = et.intensity, V.shadowBias = et.bias, V.shadowNormalBias = et.normalBias, V.shadowRadius = et.radius, V.shadowMapSize = et.mapSize, V.shadowCameraNear = et.camera.near, V.shadowCameraFar = et.camera.far, n.pointShadow[x] = V, n.pointShadowMap[x] = Z, n.pointShadowMatrix[x] = I.shadow.matrix, T++;
        }
        n.point[x] = W, x++;
      } else if (I.isHemisphereLight) {
        let W = t3.get(I);
        W.skyColor.copy(I.color).multiplyScalar(H), W.groundColor.copy(I.groundColor).multiplyScalar(H), n.hemi[h] = W, h++;
      }
    }
    p > 0 && (i14.has("OES_texture_float_linear") === true ? (n.rectAreaLTC1 = st.LTC_FLOAT_1, n.rectAreaLTC2 = st.LTC_FLOAT_2) : (n.rectAreaLTC1 = st.LTC_HALF_1, n.rectAreaLTC2 = st.LTC_HALF_2)), n.ambient[0] = u, n.ambient[1] = d, n.ambient[2] = f;
    let N = n.hash;
    (N.directionalLength !== m || N.pointLength !== x || N.spotLength !== v || N.rectAreaLength !== p || N.hemiLength !== h || N.numDirectionalShadows !== A || N.numPointShadows !== T || N.numSpotShadows !== b || N.numSpotMaps !== R || N.numLightProbes !== P) && (n.directional.length = m, n.spot.length = v, n.rectArea.length = p, n.point.length = x, n.hemi.length = h, n.directionalShadow.length = A, n.directionalShadowMap.length = A, n.pointShadow.length = T, n.pointShadowMap.length = T, n.spotShadow.length = b, n.spotShadowMap.length = b, n.directionalShadowMatrix.length = A, n.pointShadowMatrix.length = T, n.spotLightMatrix.length = b + R - w, n.spotLightMap.length = R, n.numSpotLightShadowsWithMaps = w, n.numLightProbes = P, N.directionalLength = m, N.pointLength = x, N.spotLength = v, N.rectAreaLength = p, N.hemiLength = h, N.numDirectionalShadows = A, N.numPointShadows = T, N.numSpotShadows = b, N.numSpotMaps = R, N.numLightProbes = P, n.version = jf++);
  }
  function c(l, u) {
    let d = 0, f = 0, m = 0, x = 0, v = 0, p = u.matrixWorldInverse;
    for (let h = 0, A = l.length; h < A; h++) {
      let T = l[h];
      if (T.isDirectionalLight) {
        let b = n.directional[d];
        b.direction.setFromMatrixPosition(T.matrixWorld), s.setFromMatrixPosition(T.target.matrixWorld), b.direction.sub(s), b.direction.transformDirection(p), d++;
      } else if (T.isSpotLight) {
        let b = n.spot[m];
        b.position.setFromMatrixPosition(T.matrixWorld), b.position.applyMatrix4(p), b.direction.setFromMatrixPosition(T.matrixWorld), s.setFromMatrixPosition(T.target.matrixWorld), b.direction.sub(s), b.direction.transformDirection(p), m++;
      } else if (T.isRectAreaLight) {
        let b = n.rectArea[x];
        b.position.setFromMatrixPosition(T.matrixWorld), b.position.applyMatrix4(p), a.identity(), r.copy(T.matrixWorld), r.premultiply(p), a.extractRotation(r), b.halfWidth.set(T.width * 0.5, 0, 0), b.halfHeight.set(0, T.height * 0.5, 0), b.halfWidth.applyMatrix4(a), b.halfHeight.applyMatrix4(a), x++;
      } else if (T.isPointLight) {
        let b = n.point[f];
        b.position.setFromMatrixPosition(T.matrixWorld), b.position.applyMatrix4(p), f++;
      } else if (T.isHemisphereLight) {
        let b = n.hemi[v];
        b.direction.setFromMatrixPosition(T.matrixWorld), b.direction.transformDirection(p), v++;
      }
    }
  }
  return { setup: o, setupView: c, state: n };
}
function $l(i14) {
  let t3 = new ep(i14), e = [], n = [];
  function s(u) {
    l.camera = u, e.length = 0, n.length = 0;
  }
  function r(u) {
    e.push(u);
  }
  function a(u) {
    n.push(u);
  }
  function o() {
    t3.setup(e);
  }
  function c(u) {
    t3.setupView(e, u);
  }
  let l = { lightsArray: e, shadowsArray: n, camera: null, lights: t3, transmissionRenderTarget: {} };
  return { init: s, state: l, setupLights: o, setupLightsView: c, pushLight: r, pushShadow: a };
}
function np(i14) {
  let t3 = /* @__PURE__ */ new WeakMap();
  function e(s, r = 0) {
    let a = t3.get(s), o;
    return a === void 0 ? (o = new $l(i14), t3.set(s, [o])) : r >= a.length ? (o = new $l(i14), a.push(o)) : o = a[r], o;
  }
  function n() {
    t3 = /* @__PURE__ */ new WeakMap();
  }
  return { get: e, dispose: n };
}
var ip = `void main() {
	gl_Position = vec4( position, 1.0 );
}`;
var sp = `uniform sampler2D shadow_pass;
uniform vec2 resolution;
uniform float radius;
#include <packing>
void main() {
	const float samples = float( VSM_SAMPLES );
	float mean = 0.0;
	float squared_mean = 0.0;
	float uvStride = samples <= 1.0 ? 0.0 : 2.0 / ( samples - 1.0 );
	float uvStart = samples <= 1.0 ? 0.0 : - 1.0;
	for ( float i = 0.0; i < samples; i ++ ) {
		float uvOffset = uvStart + i * uvStride;
		#ifdef HORIZONTAL_PASS
			vec2 distribution = unpackRGBATo2Half( texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( uvOffset, 0.0 ) * radius ) / resolution ) );
			mean += distribution.x;
			squared_mean += distribution.y * distribution.y + distribution.x * distribution.x;
		#else
			float depth = unpackRGBAToDepth( texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( 0.0, uvOffset ) * radius ) / resolution ) );
			mean += depth;
			squared_mean += depth * depth;
		#endif
	}
	mean = mean / samples;
	squared_mean = squared_mean / samples;
	float std_dev = sqrt( squared_mean - mean * mean );
	gl_FragColor = pack2HalfToRGBA( vec2( mean, std_dev ) );
}`;
function rp(i14, t3, e) {
  let n = new pi(), s = new Gt(), r = new Gt(), a = new se(), o = new Ns({ depthPacking: pl }), c = new Fs(), l = {}, u = e.maxTextureSize, d = { [on]: ve, [ve]: on, [$e]: $e }, f = new Ge({ defines: { VSM_SAMPLES: 8 }, uniforms: { shadow_pass: { value: null }, resolution: { value: new Gt() }, radius: { value: 4 } }, vertexShader: ip, fragmentShader: sp }), m = f.clone();
  m.defines.HORIZONTAL_PASS = 1;
  let x = new En();
  x.setAttribute("position", new Ce(new Float32Array([-1, -1, 0.5, 3, -1, 0.5, -1, 3, 0.5]), 3));
  let v = new Ie(x, f), p = this;
  this.enabled = false, this.autoUpdate = true, this.needsUpdate = false, this.type = Aa;
  let h = this.type;
  this.render = function(w, P, N) {
    if (p.enabled === false || p.autoUpdate === false && p.needsUpdate === false || w.length === 0) return;
    let M = i14.getRenderTarget(), y = i14.getActiveCubeFace(), I = i14.getActiveMipmapLevel(), z = i14.state;
    z.setBlending(hn), z.buffers.depth.getReversed() === true ? z.buffers.color.setClear(0, 0, 0, 0) : z.buffers.color.setClear(1, 1, 1, 1), z.buffers.depth.setTest(true), z.setScissorTest(false);
    let H = h !== Je && this.type === Je, X = h === Je && this.type !== Je;
    for (let Z = 0, W = w.length; Z < W; Z++) {
      let et = w[Z], V = et.shadow;
      if (V === void 0) {
        console.warn("THREE.WebGLShadowMap:", et, "has no shadow.");
        continue;
      }
      if (V.autoUpdate === false && V.needsUpdate === false) continue;
      s.copy(V.mapSize);
      let rt = V.getFrameExtents();
      if (s.multiply(rt), r.copy(V.mapSize), (s.x > u || s.y > u) && (s.x > u && (r.x = Math.floor(u / rt.x), s.x = r.x * rt.x, V.mapSize.x = r.x), s.y > u && (r.y = Math.floor(u / rt.y), s.y = r.y * rt.y, V.mapSize.y = r.y)), V.map === null || H === true || X === true) {
        let St = this.type !== Je ? { minFilter: Ne, magFilter: Ne } : {};
        V.map !== null && V.map.dispose(), V.map = new Ze(s.x, s.y, St), V.map.texture.name = et.name + ".shadowMap", V.camera.updateProjectionMatrix();
      }
      i14.setRenderTarget(V.map), i14.clear();
      let ct = V.getViewportCount();
      for (let St = 0; St < ct; St++) {
        let Ft = V.getViewport(St);
        a.set(r.x * Ft.x, r.y * Ft.y, r.x * Ft.z, r.y * Ft.w), z.viewport(a), V.updateMatrices(et, St), n = V.getFrustum(), b(P, N, V.camera, et, this.type);
      }
      V.isPointLightShadow !== true && this.type === Je && A(V, N), V.needsUpdate = false;
    }
    h = this.type, p.needsUpdate = false, i14.setRenderTarget(M, y, I);
  };
  function A(w, P) {
    let N = t3.update(v);
    f.defines.VSM_SAMPLES !== w.blurSamples && (f.defines.VSM_SAMPLES = w.blurSamples, m.defines.VSM_SAMPLES = w.blurSamples, f.needsUpdate = true, m.needsUpdate = true), w.mapPass === null && (w.mapPass = new Ze(s.x, s.y)), f.uniforms.shadow_pass.value = w.map.texture, f.uniforms.resolution.value = w.mapSize, f.uniforms.radius.value = w.radius, i14.setRenderTarget(w.mapPass), i14.clear(), i14.renderBufferDirect(P, null, N, f, v, null), m.uniforms.shadow_pass.value = w.mapPass.texture, m.uniforms.resolution.value = w.mapSize, m.uniforms.radius.value = w.radius, i14.setRenderTarget(w.map), i14.clear(), i14.renderBufferDirect(P, null, N, m, v, null);
  }
  function T(w, P, N, M) {
    let y = null, I = N.isPointLight === true ? w.customDistanceMaterial : w.customDepthMaterial;
    if (I !== void 0) y = I;
    else if (y = N.isPointLight === true ? c : o, i14.localClippingEnabled && P.clipShadows === true && Array.isArray(P.clippingPlanes) && P.clippingPlanes.length !== 0 || P.displacementMap && P.displacementScale !== 0 || P.alphaMap && P.alphaTest > 0 || P.map && P.alphaTest > 0 || P.alphaToCoverage === true) {
      let z = y.uuid, H = P.uuid, X = l[z];
      X === void 0 && (X = {}, l[z] = X);
      let Z = X[H];
      Z === void 0 && (Z = y.clone(), X[H] = Z, P.addEventListener("dispose", R)), y = Z;
    }
    if (y.visible = P.visible, y.wireframe = P.wireframe, M === Je ? y.side = P.shadowSide !== null ? P.shadowSide : P.side : y.side = P.shadowSide !== null ? P.shadowSide : d[P.side], y.alphaMap = P.alphaMap, y.alphaTest = P.alphaToCoverage === true ? 0.5 : P.alphaTest, y.map = P.map, y.clipShadows = P.clipShadows, y.clippingPlanes = P.clippingPlanes, y.clipIntersection = P.clipIntersection, y.displacementMap = P.displacementMap, y.displacementScale = P.displacementScale, y.displacementBias = P.displacementBias, y.wireframeLinewidth = P.wireframeLinewidth, y.linewidth = P.linewidth, N.isPointLight === true && y.isMeshDistanceMaterial === true) {
      let z = i14.properties.get(y);
      z.light = N;
    }
    return y;
  }
  function b(w, P, N, M, y) {
    if (w.visible === false) return;
    if (w.layers.test(P.layers) && (w.isMesh || w.isLine || w.isPoints) && (w.castShadow || w.receiveShadow && y === Je) && (!w.frustumCulled || n.intersectsObject(w))) {
      w.modelViewMatrix.multiplyMatrices(N.matrixWorldInverse, w.matrixWorld);
      let H = t3.update(w), X = w.material;
      if (Array.isArray(X)) {
        let Z = H.groups;
        for (let W = 0, et = Z.length; W < et; W++) {
          let V = Z[W], rt = X[V.materialIndex];
          if (rt && rt.visible) {
            let ct = T(w, rt, M, y);
            w.onBeforeShadow(i14, w, P, N, H, ct, V), i14.renderBufferDirect(N, null, H, ct, w, V), w.onAfterShadow(i14, w, P, N, H, ct, V);
          }
        }
      } else if (X.visible) {
        let Z = T(w, X, M, y);
        w.onBeforeShadow(i14, w, P, N, H, Z, null), i14.renderBufferDirect(N, null, H, Z, w, null), w.onAfterShadow(i14, w, P, N, H, Z, null);
      }
    }
    let z = w.children;
    for (let H = 0, X = z.length; H < X; H++) b(z[H], P, N, M, y);
  }
  function R(w) {
    w.target.removeEventListener("dispose", R);
    for (let N in l) {
      let M = l[N], y = w.target.uuid;
      y in M && (M[y].dispose(), delete M[y]);
    }
  }
}
var ap = { [Js]: $s, [Ks]: tr, [Qs]: er, [Bn]: js, [$s]: Js, [tr]: Ks, [er]: Qs, [js]: Bn };
function op(i14, t3) {
  function e() {
    let C = false, tt = new se(), it = null, ut = new se(0, 0, 0, 0);
    return { setMask: function(K) {
      it !== K && !C && (i14.colorMask(K, K, K, K), it = K);
    }, setLocked: function(K) {
      C = K;
    }, setClear: function(K, Y, pt, It, $t) {
      $t === true && (K *= It, Y *= It, pt *= It), tt.set(K, Y, pt, It), ut.equals(tt) === false && (i14.clearColor(K, Y, pt, It), ut.copy(tt));
    }, reset: function() {
      C = false, it = null, ut.set(-1, 0, 0, 0);
    } };
  }
  function n() {
    let C = false, tt = false, it = null, ut = null, K = null;
    return { setReversed: function(Y) {
      if (tt !== Y) {
        let pt = t3.get("EXT_clip_control");
        Y ? pt.clipControlEXT(pt.LOWER_LEFT_EXT, pt.ZERO_TO_ONE_EXT) : pt.clipControlEXT(pt.LOWER_LEFT_EXT, pt.NEGATIVE_ONE_TO_ONE_EXT), tt = Y;
        let It = K;
        K = null, this.setClear(It);
      }
    }, getReversed: function() {
      return tt;
    }, setTest: function(Y) {
      Y ? $2(i14.DEPTH_TEST) : dt(i14.DEPTH_TEST);
    }, setMask: function(Y) {
      it !== Y && !C && (i14.depthMask(Y), it = Y);
    }, setFunc: function(Y) {
      if (tt && (Y = ap[Y]), ut !== Y) {
        switch (Y) {
          case Js:
            i14.depthFunc(i14.NEVER);
            break;
          case $s:
            i14.depthFunc(i14.ALWAYS);
            break;
          case Ks:
            i14.depthFunc(i14.LESS);
            break;
          case Bn:
            i14.depthFunc(i14.LEQUAL);
            break;
          case Qs:
            i14.depthFunc(i14.EQUAL);
            break;
          case js:
            i14.depthFunc(i14.GEQUAL);
            break;
          case tr:
            i14.depthFunc(i14.GREATER);
            break;
          case er:
            i14.depthFunc(i14.NOTEQUAL);
            break;
          default:
            i14.depthFunc(i14.LEQUAL);
        }
        ut = Y;
      }
    }, setLocked: function(Y) {
      C = Y;
    }, setClear: function(Y) {
      K !== Y && (tt && (Y = 1 - Y), i14.clearDepth(Y), K = Y);
    }, reset: function() {
      C = false, it = null, ut = null, K = null, tt = false;
    } };
  }
  function s() {
    let C = false, tt = null, it = null, ut = null, K = null, Y = null, pt = null, It = null, $t = null;
    return { setTest: function(Xt) {
      C || (Xt ? $2(i14.STENCIL_TEST) : dt(i14.STENCIL_TEST));
    }, setMask: function(Xt) {
      tt !== Xt && !C && (i14.stencilMask(Xt), tt = Xt);
    }, setFunc: function(Xt, je, Xe) {
      (it !== Xt || ut !== je || K !== Xe) && (i14.stencilFunc(Xt, je, Xe), it = Xt, ut = je, K = Xe);
    }, setOp: function(Xt, je, Xe) {
      (Y !== Xt || pt !== je || It !== Xe) && (i14.stencilOp(Xt, je, Xe), Y = Xt, pt = je, It = Xe);
    }, setLocked: function(Xt) {
      C = Xt;
    }, setClear: function(Xt) {
      $t !== Xt && (i14.clearStencil(Xt), $t = Xt);
    }, reset: function() {
      C = false, tt = null, it = null, ut = null, K = null, Y = null, pt = null, It = null, $t = null;
    } };
  }
  let r = new e(), a = new n(), o = new s(), c = /* @__PURE__ */ new WeakMap(), l = /* @__PURE__ */ new WeakMap(), u = {}, d = {}, f = /* @__PURE__ */ new WeakMap(), m = [], x = null, v = false, p = null, h = null, A = null, T = null, b = null, R = null, w = null, P = new Vt(0, 0, 0), N = 0, M = false, y = null, I = null, z = null, H = null, X = null, Z = i14.getParameter(i14.MAX_COMBINED_TEXTURE_IMAGE_UNITS), W = false, et = 0, V = i14.getParameter(i14.VERSION);
  V.indexOf("WebGL") !== -1 ? (et = parseFloat(/^WebGL (\d)/.exec(V)[1]), W = et >= 1) : V.indexOf("OpenGL ES") !== -1 && (et = parseFloat(/^OpenGL ES (\d)/.exec(V)[1]), W = et >= 2);
  let rt = null, ct = {}, St = i14.getParameter(i14.SCISSOR_BOX), Ft = i14.getParameter(i14.VIEWPORT), Jt = new se().fromArray(St), jt = new se().fromArray(Ft);
  function Wt(C, tt, it, ut) {
    let K = new Uint8Array(4), Y = i14.createTexture();
    i14.bindTexture(C, Y), i14.texParameteri(C, i14.TEXTURE_MIN_FILTER, i14.NEAREST), i14.texParameteri(C, i14.TEXTURE_MAG_FILTER, i14.NEAREST);
    for (let pt = 0; pt < it; pt++) C === i14.TEXTURE_3D || C === i14.TEXTURE_2D_ARRAY ? i14.texImage3D(tt, 0, i14.RGBA, 1, 1, ut, 0, i14.RGBA, i14.UNSIGNED_BYTE, K) : i14.texImage2D(tt + pt, 0, i14.RGBA, 1, 1, 0, i14.RGBA, i14.UNSIGNED_BYTE, K);
    return Y;
  }
  let q = {};
  q[i14.TEXTURE_2D] = Wt(i14.TEXTURE_2D, i14.TEXTURE_2D, 1), q[i14.TEXTURE_CUBE_MAP] = Wt(i14.TEXTURE_CUBE_MAP, i14.TEXTURE_CUBE_MAP_POSITIVE_X, 6), q[i14.TEXTURE_2D_ARRAY] = Wt(i14.TEXTURE_2D_ARRAY, i14.TEXTURE_2D_ARRAY, 1, 1), q[i14.TEXTURE_3D] = Wt(i14.TEXTURE_3D, i14.TEXTURE_3D, 1, 1), r.setClear(0, 0, 0, 1), a.setClear(1), o.setClear(0), $2(i14.DEPTH_TEST), a.setFunc(Bn), wt(false), mt(Ta), $2(i14.CULL_FACE), te(hn);
  function $2(C) {
    u[C] !== true && (i14.enable(C), u[C] = true);
  }
  function dt(C) {
    u[C] !== false && (i14.disable(C), u[C] = false);
  }
  function Rt(C, tt) {
    return d[C] !== tt ? (i14.bindFramebuffer(C, tt), d[C] = tt, C === i14.DRAW_FRAMEBUFFER && (d[i14.FRAMEBUFFER] = tt), C === i14.FRAMEBUFFER && (d[i14.DRAW_FRAMEBUFFER] = tt), true) : false;
  }
  function Mt(C, tt) {
    let it = m, ut = false;
    if (C) {
      it = f.get(tt), it === void 0 && (it = [], f.set(tt, it));
      let K = C.textures;
      if (it.length !== K.length || it[0] !== i14.COLOR_ATTACHMENT0) {
        for (let Y = 0, pt = K.length; Y < pt; Y++) it[Y] = i14.COLOR_ATTACHMENT0 + Y;
        it.length = K.length, ut = true;
      }
    } else it[0] !== i14.BACK && (it[0] = i14.BACK, ut = true);
    ut && i14.drawBuffers(it);
  }
  function zt(C) {
    return x !== C ? (i14.useProgram(C), x = C, true) : false;
  }
  let fe = { [Mn]: i14.FUNC_ADD, [Vo]: i14.FUNC_SUBTRACT, [ko]: i14.FUNC_REVERSE_SUBTRACT };
  fe[Ho] = i14.MIN, fe[Go] = i14.MAX;
  let E = { [Wo]: i14.ZERO, [Xo]: i14.ONE, [qo]: i14.SRC_COLOR, [Ms]: i14.SRC_ALPHA, [Qo]: i14.SRC_ALPHA_SATURATE, [$o]: i14.DST_COLOR, [Zo]: i14.DST_ALPHA, [Yo]: i14.ONE_MINUS_SRC_COLOR, [Ss]: i14.ONE_MINUS_SRC_ALPHA, [Ko]: i14.ONE_MINUS_DST_COLOR, [Jo]: i14.ONE_MINUS_DST_ALPHA, [jo]: i14.CONSTANT_COLOR, [tl]: i14.ONE_MINUS_CONSTANT_COLOR, [el]: i14.CONSTANT_ALPHA, [nl]: i14.ONE_MINUS_CONSTANT_ALPHA };
  function te(C, tt, it, ut, K, Y, pt, It, $t, Xt) {
    if (C === hn) {
      v === true && (dt(i14.BLEND), v = false);
      return;
    }
    if (v === false && ($2(i14.BLEND), v = true), C !== zo) {
      if (C !== p || Xt !== M) {
        if ((h !== Mn || b !== Mn) && (i14.blendEquation(i14.FUNC_ADD), h = Mn, b = Mn), Xt) switch (C) {
          case On:
            i14.blendFuncSeparate(i14.ONE, i14.ONE_MINUS_SRC_ALPHA, i14.ONE, i14.ONE_MINUS_SRC_ALPHA);
            break;
          case wa:
            i14.blendFunc(i14.ONE, i14.ONE);
            break;
          case Ca:
            i14.blendFuncSeparate(i14.ZERO, i14.ONE_MINUS_SRC_COLOR, i14.ZERO, i14.ONE);
            break;
          case Ra:
            i14.blendFuncSeparate(i14.DST_COLOR, i14.ONE_MINUS_SRC_ALPHA, i14.ZERO, i14.ONE);
            break;
          default:
            console.error("THREE.WebGLState: Invalid blending: ", C);
            break;
        }
        else switch (C) {
          case On:
            i14.blendFuncSeparate(i14.SRC_ALPHA, i14.ONE_MINUS_SRC_ALPHA, i14.ONE, i14.ONE_MINUS_SRC_ALPHA);
            break;
          case wa:
            i14.blendFuncSeparate(i14.SRC_ALPHA, i14.ONE, i14.ONE, i14.ONE);
            break;
          case Ca:
            console.error("THREE.WebGLState: SubtractiveBlending requires material.premultipliedAlpha = true");
            break;
          case Ra:
            console.error("THREE.WebGLState: MultiplyBlending requires material.premultipliedAlpha = true");
            break;
          default:
            console.error("THREE.WebGLState: Invalid blending: ", C);
            break;
        }
        A = null, T = null, R = null, w = null, P.set(0, 0, 0), N = 0, p = C, M = Xt;
      }
      return;
    }
    K = K || tt, Y = Y || it, pt = pt || ut, (tt !== h || K !== b) && (i14.blendEquationSeparate(fe[tt], fe[K]), h = tt, b = K), (it !== A || ut !== T || Y !== R || pt !== w) && (i14.blendFuncSeparate(E[it], E[ut], E[Y], E[pt]), A = it, T = ut, R = Y, w = pt), (It.equals(P) === false || $t !== N) && (i14.blendColor(It.r, It.g, It.b, $t), P.copy(It), N = $t), p = C, M = false;
  }
  function Pt(C, tt) {
    C.side === $e ? dt(i14.CULL_FACE) : $2(i14.CULL_FACE);
    let it = C.side === ve;
    tt && (it = !it), wt(it), C.blending === On && C.transparent === false ? te(hn) : te(C.blending, C.blendEquation, C.blendSrc, C.blendDst, C.blendEquationAlpha, C.blendSrcAlpha, C.blendDstAlpha, C.blendColor, C.blendAlpha, C.premultipliedAlpha), a.setFunc(C.depthFunc), a.setTest(C.depthTest), a.setMask(C.depthWrite), r.setMask(C.colorWrite);
    let ut = C.stencilWrite;
    o.setTest(ut), ut && (o.setMask(C.stencilWriteMask), o.setFunc(C.stencilFunc, C.stencilRef, C.stencilFuncMask), o.setOp(C.stencilFail, C.stencilZFail, C.stencilZPass)), gt(C.polygonOffset, C.polygonOffsetFactor, C.polygonOffsetUnits), C.alphaToCoverage === true ? $2(i14.SAMPLE_ALPHA_TO_COVERAGE) : dt(i14.SAMPLE_ALPHA_TO_COVERAGE);
  }
  function wt(C) {
    y !== C && (C ? i14.frontFace(i14.CW) : i14.frontFace(i14.CCW), y = C);
  }
  function mt(C) {
    C !== Fo ? ($2(i14.CULL_FACE), C !== I && (C === Ta ? i14.cullFace(i14.BACK) : C === Oo ? i14.cullFace(i14.FRONT) : i14.cullFace(i14.FRONT_AND_BACK))) : dt(i14.CULL_FACE), I = C;
  }
  function ee(C) {
    C !== z && (W && i14.lineWidth(C), z = C);
  }
  function gt(C, tt, it) {
    C ? ($2(i14.POLYGON_OFFSET_FILL), (H !== tt || X !== it) && (i14.polygonOffset(tt, it), H = tt, X = it)) : dt(i14.POLYGON_OFFSET_FILL);
  }
  function Ut(C) {
    C ? $2(i14.SCISSOR_TEST) : dt(i14.SCISSOR_TEST);
  }
  function ue(C) {
    C === void 0 && (C = i14.TEXTURE0 + Z - 1), rt !== C && (i14.activeTexture(C), rt = C);
  }
  function ae(C, tt, it) {
    it === void 0 && (rt === null ? it = i14.TEXTURE0 + Z - 1 : it = rt);
    let ut = ct[it];
    ut === void 0 && (ut = { type: void 0, texture: void 0 }, ct[it] = ut), (ut.type !== C || ut.texture !== tt) && (rt !== it && (i14.activeTexture(it), rt = it), i14.bindTexture(C, tt || q[C]), ut.type = C, ut.texture = tt);
  }
  function S() {
    let C = ct[rt];
    C !== void 0 && C.type !== void 0 && (i14.bindTexture(C.type, null), C.type = void 0, C.texture = void 0);
  }
  function g() {
    try {
      i14.compressedTexImage2D(...arguments);
    } catch (C) {
      console.error("THREE.WebGLState:", C);
    }
  }
  function U() {
    try {
      i14.compressedTexImage3D(...arguments);
    } catch (C) {
      console.error("THREE.WebGLState:", C);
    }
  }
  function G() {
    try {
      i14.texSubImage2D(...arguments);
    } catch (C) {
      console.error("THREE.WebGLState:", C);
    }
  }
  function J() {
    try {
      i14.texSubImage3D(...arguments);
    } catch (C) {
      console.error("THREE.WebGLState:", C);
    }
  }
  function k() {
    try {
      i14.compressedTexSubImage2D(...arguments);
    } catch (C) {
      console.error("THREE.WebGLState:", C);
    }
  }
  function yt() {
    try {
      i14.compressedTexSubImage3D(...arguments);
    } catch (C) {
      console.error("THREE.WebGLState:", C);
    }
  }
  function nt() {
    try {
      i14.texStorage2D(...arguments);
    } catch (C) {
      console.error("THREE.WebGLState:", C);
    }
  }
  function _t() {
    try {
      i14.texStorage3D(...arguments);
    } catch (C) {
      console.error("THREE.WebGLState:", C);
    }
  }
  function xt() {
    try {
      i14.texImage2D(...arguments);
    } catch (C) {
      console.error("THREE.WebGLState:", C);
    }
  }
  function j() {
    try {
      i14.texImage3D(...arguments);
    } catch (C) {
      console.error("THREE.WebGLState:", C);
    }
  }
  function lt(C) {
    Jt.equals(C) === false && (i14.scissor(C.x, C.y, C.z, C.w), Jt.copy(C));
  }
  function At(C) {
    jt.equals(C) === false && (i14.viewport(C.x, C.y, C.z, C.w), jt.copy(C));
  }
  function vt(C, tt) {
    let it = l.get(tt);
    it === void 0 && (it = /* @__PURE__ */ new WeakMap(), l.set(tt, it));
    let ut = it.get(C);
    ut === void 0 && (ut = i14.getUniformBlockIndex(tt, C.name), it.set(C, ut));
  }
  function at(C, tt) {
    let ut = l.get(tt).get(C);
    c.get(tt) !== ut && (i14.uniformBlockBinding(tt, ut, C.__bindingPointIndex), c.set(tt, ut));
  }
  function Dt() {
    i14.disable(i14.BLEND), i14.disable(i14.CULL_FACE), i14.disable(i14.DEPTH_TEST), i14.disable(i14.POLYGON_OFFSET_FILL), i14.disable(i14.SCISSOR_TEST), i14.disable(i14.STENCIL_TEST), i14.disable(i14.SAMPLE_ALPHA_TO_COVERAGE), i14.blendEquation(i14.FUNC_ADD), i14.blendFunc(i14.ONE, i14.ZERO), i14.blendFuncSeparate(i14.ONE, i14.ZERO, i14.ONE, i14.ZERO), i14.blendColor(0, 0, 0, 0), i14.colorMask(true, true, true, true), i14.clearColor(0, 0, 0, 0), i14.depthMask(true), i14.depthFunc(i14.LESS), a.setReversed(false), i14.clearDepth(1), i14.stencilMask(4294967295), i14.stencilFunc(i14.ALWAYS, 0, 4294967295), i14.stencilOp(i14.KEEP, i14.KEEP, i14.KEEP), i14.clearStencil(0), i14.cullFace(i14.BACK), i14.frontFace(i14.CCW), i14.polygonOffset(0, 0), i14.activeTexture(i14.TEXTURE0), i14.bindFramebuffer(i14.FRAMEBUFFER, null), i14.bindFramebuffer(i14.DRAW_FRAMEBUFFER, null), i14.bindFramebuffer(i14.READ_FRAMEBUFFER, null), i14.useProgram(null), i14.lineWidth(1), i14.scissor(0, 0, i14.canvas.width, i14.canvas.height), i14.viewport(0, 0, i14.canvas.width, i14.canvas.height), u = {}, rt = null, ct = {}, d = {}, f = /* @__PURE__ */ new WeakMap(), m = [], x = null, v = false, p = null, h = null, A = null, T = null, b = null, R = null, w = null, P = new Vt(0, 0, 0), N = 0, M = false, y = null, I = null, z = null, H = null, X = null, Jt.set(0, 0, i14.canvas.width, i14.canvas.height), jt.set(0, 0, i14.canvas.width, i14.canvas.height), r.reset(), a.reset(), o.reset();
  }
  return { buffers: { color: r, depth: a, stencil: o }, enable: $2, disable: dt, bindFramebuffer: Rt, drawBuffers: Mt, useProgram: zt, setBlending: te, setMaterial: Pt, setFlipSided: wt, setCullFace: mt, setLineWidth: ee, setPolygonOffset: gt, setScissorTest: Ut, activeTexture: ue, bindTexture: ae, unbindTexture: S, compressedTexImage2D: g, compressedTexImage3D: U, texImage2D: xt, texImage3D: j, updateUBOMapping: vt, uniformBlockBinding: at, texStorage2D: nt, texStorage3D: _t, texSubImage2D: G, texSubImage3D: J, compressedTexSubImage2D: k, compressedTexSubImage3D: yt, scissor: lt, viewport: At, reset: Dt };
}
function lp(i14, t3, e, n, s, r, a) {
  let o = t3.has("WEBGL_multisampled_render_to_texture") ? t3.get("WEBGL_multisampled_render_to_texture") : null, c = typeof navigator > "u" ? false : /OculusBrowser/g.test(navigator.userAgent), l = new Gt(), u = /* @__PURE__ */ new WeakMap(), d, f = /* @__PURE__ */ new WeakMap(), m = false;
  try {
    m = typeof OffscreenCanvas < "u" && new OffscreenCanvas(1, 1).getContext("2d") !== null;
  } catch {
  }
  function x(S, g) {
    return m ? new OffscreenCanvas(S, g) : Di("canvas");
  }
  function v(S, g, U) {
    let G = 1, J = ae(S);
    if ((J.width > U || J.height > U) && (G = U / Math.max(J.width, J.height)), G < 1) if (typeof HTMLImageElement < "u" && S instanceof HTMLImageElement || typeof HTMLCanvasElement < "u" && S instanceof HTMLCanvasElement || typeof ImageBitmap < "u" && S instanceof ImageBitmap || typeof VideoFrame < "u" && S instanceof VideoFrame) {
      let k = Math.floor(G * J.width), yt = Math.floor(G * J.height);
      d === void 0 && (d = x(k, yt));
      let nt = g ? x(k, yt) : d;
      return nt.width = k, nt.height = yt, nt.getContext("2d").drawImage(S, 0, 0, k, yt), console.warn("THREE.WebGLRenderer: Texture has been resized from (" + J.width + "x" + J.height + ") to (" + k + "x" + yt + ")."), nt;
    } else return "data" in S && console.warn("THREE.WebGLRenderer: Image in DataTexture is too big (" + J.width + "x" + J.height + ")."), S;
    return S;
  }
  function p(S) {
    return S.generateMipmaps;
  }
  function h(S) {
    i14.generateMipmap(S);
  }
  function A(S) {
    return S.isWebGLCubeRenderTarget ? i14.TEXTURE_CUBE_MAP : S.isWebGL3DRenderTarget ? i14.TEXTURE_3D : S.isWebGLArrayRenderTarget || S.isCompressedArrayTexture ? i14.TEXTURE_2D_ARRAY : i14.TEXTURE_2D;
  }
  function T(S, g, U, G, J = false) {
    if (S !== null) {
      if (i14[S] !== void 0) return i14[S];
      console.warn("THREE.WebGLRenderer: Attempt to use non-existing WebGL internal format '" + S + "'");
    }
    let k = g;
    if (g === i14.RED && (U === i14.FLOAT && (k = i14.R32F), U === i14.HALF_FLOAT && (k = i14.R16F), U === i14.UNSIGNED_BYTE && (k = i14.R8)), g === i14.RED_INTEGER && (U === i14.UNSIGNED_BYTE && (k = i14.R8UI), U === i14.UNSIGNED_SHORT && (k = i14.R16UI), U === i14.UNSIGNED_INT && (k = i14.R32UI), U === i14.BYTE && (k = i14.R8I), U === i14.SHORT && (k = i14.R16I), U === i14.INT && (k = i14.R32I)), g === i14.RG && (U === i14.FLOAT && (k = i14.RG32F), U === i14.HALF_FLOAT && (k = i14.RG16F), U === i14.UNSIGNED_BYTE && (k = i14.RG8)), g === i14.RG_INTEGER && (U === i14.UNSIGNED_BYTE && (k = i14.RG8UI), U === i14.UNSIGNED_SHORT && (k = i14.RG16UI), U === i14.UNSIGNED_INT && (k = i14.RG32UI), U === i14.BYTE && (k = i14.RG8I), U === i14.SHORT && (k = i14.RG16I), U === i14.INT && (k = i14.RG32I)), g === i14.RGB_INTEGER && (U === i14.UNSIGNED_BYTE && (k = i14.RGB8UI), U === i14.UNSIGNED_SHORT && (k = i14.RGB16UI), U === i14.UNSIGNED_INT && (k = i14.RGB32UI), U === i14.BYTE && (k = i14.RGB8I), U === i14.SHORT && (k = i14.RGB16I), U === i14.INT && (k = i14.RGB32I)), g === i14.RGBA_INTEGER && (U === i14.UNSIGNED_BYTE && (k = i14.RGBA8UI), U === i14.UNSIGNED_SHORT && (k = i14.RGBA16UI), U === i14.UNSIGNED_INT && (k = i14.RGBA32UI), U === i14.BYTE && (k = i14.RGBA8I), U === i14.SHORT && (k = i14.RGBA16I), U === i14.INT && (k = i14.RGBA32I)), g === i14.RGB && (U === i14.UNSIGNED_INT_5_9_9_9_REV && (k = i14.RGB9_E5), U === i14.UNSIGNED_INT_10F_11F_11F_REV && (k = i14.R11F_G11F_B10F)), g === i14.RGBA) {
      let yt = J ? Pi : kt.getTransfer(G);
      U === i14.FLOAT && (k = i14.RGBA32F), U === i14.HALF_FLOAT && (k = i14.RGBA16F), U === i14.UNSIGNED_BYTE && (k = yt === qt ? i14.SRGB8_ALPHA8 : i14.RGBA8), U === i14.UNSIGNED_SHORT_4_4_4_4 && (k = i14.RGBA4), U === i14.UNSIGNED_SHORT_5_5_5_1 && (k = i14.RGB5_A1);
    }
    return (k === i14.R16F || k === i14.R32F || k === i14.RG16F || k === i14.RG32F || k === i14.RGBA16F || k === i14.RGBA32F) && t3.get("EXT_color_buffer_float"), k;
  }
  function b(S, g) {
    let U;
    return S ? g === null || g === Cn || g === xi ? U = i14.DEPTH24_STENCIL8 : g === Ke ? U = i14.DEPTH32F_STENCIL8 : g === gi && (U = i14.DEPTH24_STENCIL8, console.warn("DepthTexture: 16 bit depth attachment is not supported with stencil. Using 24-bit attachment.")) : g === null || g === Cn || g === xi ? U = i14.DEPTH_COMPONENT24 : g === Ke ? U = i14.DEPTH_COMPONENT32F : g === gi && (U = i14.DEPTH_COMPONENT16), U;
  }
  function R(S, g) {
    return p(S) === true || S.isFramebufferTexture && S.minFilter !== Ne && S.minFilter !== ke ? Math.log2(Math.max(g.width, g.height)) + 1 : S.mipmaps !== void 0 && S.mipmaps.length > 0 ? S.mipmaps.length : S.isCompressedTexture && Array.isArray(S.image) ? g.mipmaps.length : 1;
  }
  function w(S) {
    let g = S.target;
    g.removeEventListener("dispose", w), N(g), g.isVideoTexture && u.delete(g);
  }
  function P(S) {
    let g = S.target;
    g.removeEventListener("dispose", P), y(g);
  }
  function N(S) {
    let g = n.get(S);
    if (g.__webglInit === void 0) return;
    let U = S.source, G = f.get(U);
    if (G) {
      let J = G[g.__cacheKey];
      J.usedTimes--, J.usedTimes === 0 && M(S), Object.keys(G).length === 0 && f.delete(U);
    }
    n.remove(S);
  }
  function M(S) {
    let g = n.get(S);
    i14.deleteTexture(g.__webglTexture);
    let U = S.source, G = f.get(U);
    delete G[g.__cacheKey], a.memory.textures--;
  }
  function y(S) {
    let g = n.get(S);
    if (S.depthTexture && (S.depthTexture.dispose(), n.remove(S.depthTexture)), S.isWebGLCubeRenderTarget) for (let G = 0; G < 6; G++) {
      if (Array.isArray(g.__webglFramebuffer[G])) for (let J = 0; J < g.__webglFramebuffer[G].length; J++) i14.deleteFramebuffer(g.__webglFramebuffer[G][J]);
      else i14.deleteFramebuffer(g.__webglFramebuffer[G]);
      g.__webglDepthbuffer && i14.deleteRenderbuffer(g.__webglDepthbuffer[G]);
    }
    else {
      if (Array.isArray(g.__webglFramebuffer)) for (let G = 0; G < g.__webglFramebuffer.length; G++) i14.deleteFramebuffer(g.__webglFramebuffer[G]);
      else i14.deleteFramebuffer(g.__webglFramebuffer);
      if (g.__webglDepthbuffer && i14.deleteRenderbuffer(g.__webglDepthbuffer), g.__webglMultisampledFramebuffer && i14.deleteFramebuffer(g.__webglMultisampledFramebuffer), g.__webglColorRenderbuffer) for (let G = 0; G < g.__webglColorRenderbuffer.length; G++) g.__webglColorRenderbuffer[G] && i14.deleteRenderbuffer(g.__webglColorRenderbuffer[G]);
      g.__webglDepthRenderbuffer && i14.deleteRenderbuffer(g.__webglDepthRenderbuffer);
    }
    let U = S.textures;
    for (let G = 0, J = U.length; G < J; G++) {
      let k = n.get(U[G]);
      k.__webglTexture && (i14.deleteTexture(k.__webglTexture), a.memory.textures--), n.remove(U[G]);
    }
    n.remove(S);
  }
  let I = 0;
  function z() {
    I = 0;
  }
  function H() {
    let S = I;
    return S >= s.maxTextures && console.warn("THREE.WebGLTextures: Trying to use " + S + " texture units while this GPU supports only " + s.maxTextures), I += 1, S;
  }
  function X(S) {
    let g = [];
    return g.push(S.wrapS), g.push(S.wrapT), g.push(S.wrapR || 0), g.push(S.magFilter), g.push(S.minFilter), g.push(S.anisotropy), g.push(S.internalFormat), g.push(S.format), g.push(S.type), g.push(S.generateMipmaps), g.push(S.premultiplyAlpha), g.push(S.flipY), g.push(S.unpackAlignment), g.push(S.colorSpace), g.join();
  }
  function Z(S, g) {
    let U = n.get(S);
    if (S.isVideoTexture && Ut(S), S.isRenderTargetTexture === false && S.isExternalTexture !== true && S.version > 0 && U.__version !== S.version) {
      let G = S.image;
      if (G === null) console.warn("THREE.WebGLRenderer: Texture marked for update but no image data found.");
      else if (G.complete === false) console.warn("THREE.WebGLRenderer: Texture marked for update but image is incomplete");
      else {
        q(U, S, g);
        return;
      }
    } else S.isExternalTexture && (U.__webglTexture = S.sourceTexture ? S.sourceTexture : null);
    e.bindTexture(i14.TEXTURE_2D, U.__webglTexture, i14.TEXTURE0 + g);
  }
  function W(S, g) {
    let U = n.get(S);
    if (S.isRenderTargetTexture === false && S.version > 0 && U.__version !== S.version) {
      q(U, S, g);
      return;
    }
    e.bindTexture(i14.TEXTURE_2D_ARRAY, U.__webglTexture, i14.TEXTURE0 + g);
  }
  function et(S, g) {
    let U = n.get(S);
    if (S.isRenderTargetTexture === false && S.version > 0 && U.__version !== S.version) {
      q(U, S, g);
      return;
    }
    e.bindTexture(i14.TEXTURE_3D, U.__webglTexture, i14.TEXTURE0 + g);
  }
  function V(S, g) {
    let U = n.get(S);
    if (S.version > 0 && U.__version !== S.version) {
      $2(U, S, g);
      return;
    }
    e.bindTexture(i14.TEXTURE_CUBE_MAP, U.__webglTexture, i14.TEXTURE0 + g);
  }
  let rt = { [bs]: i14.REPEAT, [yn]: i14.CLAMP_TO_EDGE, [Es]: i14.MIRRORED_REPEAT }, ct = { [Ne]: i14.NEAREST, [dl]: i14.NEAREST_MIPMAP_NEAREST, [Yi]: i14.NEAREST_MIPMAP_LINEAR, [ke]: i14.LINEAR, [sr]: i14.LINEAR_MIPMAP_NEAREST, [wn]: i14.LINEAR_MIPMAP_LINEAR }, St = { [gl]: i14.NEVER, [Sl]: i14.ALWAYS, [_l]: i14.LESS, [ka]: i14.LEQUAL, [xl]: i14.EQUAL, [Ml]: i14.GEQUAL, [vl]: i14.GREATER, [yl]: i14.NOTEQUAL };
  function Ft(S, g) {
    if (g.type === Ke && t3.has("OES_texture_float_linear") === false && (g.magFilter === ke || g.magFilter === sr || g.magFilter === Yi || g.magFilter === wn || g.minFilter === ke || g.minFilter === sr || g.minFilter === Yi || g.minFilter === wn) && console.warn("THREE.WebGLRenderer: Unable to use linear filtering with floating point textures. OES_texture_float_linear not supported on this device."), i14.texParameteri(S, i14.TEXTURE_WRAP_S, rt[g.wrapS]), i14.texParameteri(S, i14.TEXTURE_WRAP_T, rt[g.wrapT]), (S === i14.TEXTURE_3D || S === i14.TEXTURE_2D_ARRAY) && i14.texParameteri(S, i14.TEXTURE_WRAP_R, rt[g.wrapR]), i14.texParameteri(S, i14.TEXTURE_MAG_FILTER, ct[g.magFilter]), i14.texParameteri(S, i14.TEXTURE_MIN_FILTER, ct[g.minFilter]), g.compareFunction && (i14.texParameteri(S, i14.TEXTURE_COMPARE_MODE, i14.COMPARE_REF_TO_TEXTURE), i14.texParameteri(S, i14.TEXTURE_COMPARE_FUNC, St[g.compareFunction])), t3.has("EXT_texture_filter_anisotropic") === true) {
      if (g.magFilter === Ne || g.minFilter !== Yi && g.minFilter !== wn || g.type === Ke && t3.has("OES_texture_float_linear") === false) return;
      if (g.anisotropy > 1 || n.get(g).__currentAnisotropy) {
        let U = t3.get("EXT_texture_filter_anisotropic");
        i14.texParameterf(S, U.TEXTURE_MAX_ANISOTROPY_EXT, Math.min(g.anisotropy, s.getMaxAnisotropy())), n.get(g).__currentAnisotropy = g.anisotropy;
      }
    }
  }
  function Jt(S, g) {
    let U = false;
    S.__webglInit === void 0 && (S.__webglInit = true, g.addEventListener("dispose", w));
    let G = g.source, J = f.get(G);
    J === void 0 && (J = {}, f.set(G, J));
    let k = X(g);
    if (k !== S.__cacheKey) {
      J[k] === void 0 && (J[k] = { texture: i14.createTexture(), usedTimes: 0 }, a.memory.textures++, U = true), J[k].usedTimes++;
      let yt = J[S.__cacheKey];
      yt !== void 0 && (J[S.__cacheKey].usedTimes--, yt.usedTimes === 0 && M(g)), S.__cacheKey = k, S.__webglTexture = J[k].texture;
    }
    return U;
  }
  function jt(S, g, U) {
    return Math.floor(Math.floor(S / U) / g);
  }
  function Wt(S, g, U, G) {
    let k = S.updateRanges;
    if (k.length === 0) e.texSubImage2D(i14.TEXTURE_2D, 0, 0, 0, g.width, g.height, U, G, g.data);
    else {
      k.sort((j, lt) => j.start - lt.start);
      let yt = 0;
      for (let j = 1; j < k.length; j++) {
        let lt = k[yt], At = k[j], vt = lt.start + lt.count, at = jt(At.start, g.width, 4), Dt = jt(lt.start, g.width, 4);
        At.start <= vt + 1 && at === Dt && jt(At.start + At.count - 1, g.width, 4) === at ? lt.count = Math.max(lt.count, At.start + At.count - lt.start) : (++yt, k[yt] = At);
      }
      k.length = yt + 1;
      let nt = i14.getParameter(i14.UNPACK_ROW_LENGTH), _t = i14.getParameter(i14.UNPACK_SKIP_PIXELS), xt = i14.getParameter(i14.UNPACK_SKIP_ROWS);
      i14.pixelStorei(i14.UNPACK_ROW_LENGTH, g.width);
      for (let j = 0, lt = k.length; j < lt; j++) {
        let At = k[j], vt = Math.floor(At.start / 4), at = Math.ceil(At.count / 4), Dt = vt % g.width, C = Math.floor(vt / g.width), tt = at, it = 1;
        i14.pixelStorei(i14.UNPACK_SKIP_PIXELS, Dt), i14.pixelStorei(i14.UNPACK_SKIP_ROWS, C), e.texSubImage2D(i14.TEXTURE_2D, 0, Dt, C, tt, it, U, G, g.data);
      }
      S.clearUpdateRanges(), i14.pixelStorei(i14.UNPACK_ROW_LENGTH, nt), i14.pixelStorei(i14.UNPACK_SKIP_PIXELS, _t), i14.pixelStorei(i14.UNPACK_SKIP_ROWS, xt);
    }
  }
  function q(S, g, U) {
    let G = i14.TEXTURE_2D;
    (g.isDataArrayTexture || g.isCompressedArrayTexture) && (G = i14.TEXTURE_2D_ARRAY), g.isData3DTexture && (G = i14.TEXTURE_3D);
    let J = Jt(S, g), k = g.source;
    e.bindTexture(G, S.__webglTexture, i14.TEXTURE0 + U);
    let yt = n.get(k);
    if (k.version !== yt.__version || J === true) {
      e.activeTexture(i14.TEXTURE0 + U);
      let nt = kt.getPrimaries(kt.workingColorSpace), _t = g.colorSpace === dn ? null : kt.getPrimaries(g.colorSpace), xt = g.colorSpace === dn || nt === _t ? i14.NONE : i14.BROWSER_DEFAULT_WEBGL;
      i14.pixelStorei(i14.UNPACK_FLIP_Y_WEBGL, g.flipY), i14.pixelStorei(i14.UNPACK_PREMULTIPLY_ALPHA_WEBGL, g.premultiplyAlpha), i14.pixelStorei(i14.UNPACK_ALIGNMENT, g.unpackAlignment), i14.pixelStorei(i14.UNPACK_COLORSPACE_CONVERSION_WEBGL, xt);
      let j = v(g.image, false, s.maxTextureSize);
      j = ue(g, j);
      let lt = r.convert(g.format, g.colorSpace), At = r.convert(g.type), vt = T(g.internalFormat, lt, At, g.colorSpace, g.isVideoTexture);
      Ft(G, g);
      let at, Dt = g.mipmaps, C = g.isVideoTexture !== true, tt = yt.__version === void 0 || J === true, it = k.dataReady, ut = R(g, j);
      if (g.isDepthTexture) vt = b(g.format === vi, g.type), tt && (C ? e.texStorage2D(i14.TEXTURE_2D, 1, vt, j.width, j.height) : e.texImage2D(i14.TEXTURE_2D, 0, vt, j.width, j.height, 0, lt, At, null));
      else if (g.isDataTexture) if (Dt.length > 0) {
        C && tt && e.texStorage2D(i14.TEXTURE_2D, ut, vt, Dt[0].width, Dt[0].height);
        for (let K = 0, Y = Dt.length; K < Y; K++) at = Dt[K], C ? it && e.texSubImage2D(i14.TEXTURE_2D, K, 0, 0, at.width, at.height, lt, At, at.data) : e.texImage2D(i14.TEXTURE_2D, K, vt, at.width, at.height, 0, lt, At, at.data);
        g.generateMipmaps = false;
      } else C ? (tt && e.texStorage2D(i14.TEXTURE_2D, ut, vt, j.width, j.height), it && Wt(g, j, lt, At)) : e.texImage2D(i14.TEXTURE_2D, 0, vt, j.width, j.height, 0, lt, At, j.data);
      else if (g.isCompressedTexture) if (g.isCompressedArrayTexture) {
        C && tt && e.texStorage3D(i14.TEXTURE_2D_ARRAY, ut, vt, Dt[0].width, Dt[0].height, j.depth);
        for (let K = 0, Y = Dt.length; K < Y; K++) if (at = Dt[K], g.format !== Fe) if (lt !== null) if (C) {
          if (it) if (g.layerUpdates.size > 0) {
            let pt = Ya(at.width, at.height, g.format, g.type);
            for (let It of g.layerUpdates) {
              let $t = at.data.subarray(It * pt / at.data.BYTES_PER_ELEMENT, (It + 1) * pt / at.data.BYTES_PER_ELEMENT);
              e.compressedTexSubImage3D(i14.TEXTURE_2D_ARRAY, K, 0, 0, It, at.width, at.height, 1, lt, $t);
            }
            g.clearLayerUpdates();
          } else e.compressedTexSubImage3D(i14.TEXTURE_2D_ARRAY, K, 0, 0, 0, at.width, at.height, j.depth, lt, at.data);
        } else e.compressedTexImage3D(i14.TEXTURE_2D_ARRAY, K, vt, at.width, at.height, j.depth, 0, at.data, 0, 0);
        else console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()");
        else C ? it && e.texSubImage3D(i14.TEXTURE_2D_ARRAY, K, 0, 0, 0, at.width, at.height, j.depth, lt, At, at.data) : e.texImage3D(i14.TEXTURE_2D_ARRAY, K, vt, at.width, at.height, j.depth, 0, lt, At, at.data);
      } else {
        C && tt && e.texStorage2D(i14.TEXTURE_2D, ut, vt, Dt[0].width, Dt[0].height);
        for (let K = 0, Y = Dt.length; K < Y; K++) at = Dt[K], g.format !== Fe ? lt !== null ? C ? it && e.compressedTexSubImage2D(i14.TEXTURE_2D, K, 0, 0, at.width, at.height, lt, at.data) : e.compressedTexImage2D(i14.TEXTURE_2D, K, vt, at.width, at.height, 0, at.data) : console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()") : C ? it && e.texSubImage2D(i14.TEXTURE_2D, K, 0, 0, at.width, at.height, lt, At, at.data) : e.texImage2D(i14.TEXTURE_2D, K, vt, at.width, at.height, 0, lt, At, at.data);
      }
      else if (g.isDataArrayTexture) if (C) {
        if (tt && e.texStorage3D(i14.TEXTURE_2D_ARRAY, ut, vt, j.width, j.height, j.depth), it) if (g.layerUpdates.size > 0) {
          let K = Ya(j.width, j.height, g.format, g.type);
          for (let Y of g.layerUpdates) {
            let pt = j.data.subarray(Y * K / j.data.BYTES_PER_ELEMENT, (Y + 1) * K / j.data.BYTES_PER_ELEMENT);
            e.texSubImage3D(i14.TEXTURE_2D_ARRAY, 0, 0, 0, Y, j.width, j.height, 1, lt, At, pt);
          }
          g.clearLayerUpdates();
        } else e.texSubImage3D(i14.TEXTURE_2D_ARRAY, 0, 0, 0, 0, j.width, j.height, j.depth, lt, At, j.data);
      } else e.texImage3D(i14.TEXTURE_2D_ARRAY, 0, vt, j.width, j.height, j.depth, 0, lt, At, j.data);
      else if (g.isData3DTexture) C ? (tt && e.texStorage3D(i14.TEXTURE_3D, ut, vt, j.width, j.height, j.depth), it && e.texSubImage3D(i14.TEXTURE_3D, 0, 0, 0, 0, j.width, j.height, j.depth, lt, At, j.data)) : e.texImage3D(i14.TEXTURE_3D, 0, vt, j.width, j.height, j.depth, 0, lt, At, j.data);
      else if (g.isFramebufferTexture) {
        if (tt) if (C) e.texStorage2D(i14.TEXTURE_2D, ut, vt, j.width, j.height);
        else {
          let K = j.width, Y = j.height;
          for (let pt = 0; pt < ut; pt++) e.texImage2D(i14.TEXTURE_2D, pt, vt, K, Y, 0, lt, At, null), K >>= 1, Y >>= 1;
        }
      } else if (Dt.length > 0) {
        if (C && tt) {
          let K = ae(Dt[0]);
          e.texStorage2D(i14.TEXTURE_2D, ut, vt, K.width, K.height);
        }
        for (let K = 0, Y = Dt.length; K < Y; K++) at = Dt[K], C ? it && e.texSubImage2D(i14.TEXTURE_2D, K, 0, 0, lt, At, at) : e.texImage2D(i14.TEXTURE_2D, K, vt, lt, At, at);
        g.generateMipmaps = false;
      } else if (C) {
        if (tt) {
          let K = ae(j);
          e.texStorage2D(i14.TEXTURE_2D, ut, vt, K.width, K.height);
        }
        it && e.texSubImage2D(i14.TEXTURE_2D, 0, 0, 0, lt, At, j);
      } else e.texImage2D(i14.TEXTURE_2D, 0, vt, lt, At, j);
      p(g) && h(G), yt.__version = k.version, g.onUpdate && g.onUpdate(g);
    }
    S.__version = g.version;
  }
  function $2(S, g, U) {
    if (g.image.length !== 6) return;
    let G = Jt(S, g), J = g.source;
    e.bindTexture(i14.TEXTURE_CUBE_MAP, S.__webglTexture, i14.TEXTURE0 + U);
    let k = n.get(J);
    if (J.version !== k.__version || G === true) {
      e.activeTexture(i14.TEXTURE0 + U);
      let yt = kt.getPrimaries(kt.workingColorSpace), nt = g.colorSpace === dn ? null : kt.getPrimaries(g.colorSpace), _t = g.colorSpace === dn || yt === nt ? i14.NONE : i14.BROWSER_DEFAULT_WEBGL;
      i14.pixelStorei(i14.UNPACK_FLIP_Y_WEBGL, g.flipY), i14.pixelStorei(i14.UNPACK_PREMULTIPLY_ALPHA_WEBGL, g.premultiplyAlpha), i14.pixelStorei(i14.UNPACK_ALIGNMENT, g.unpackAlignment), i14.pixelStorei(i14.UNPACK_COLORSPACE_CONVERSION_WEBGL, _t);
      let xt = g.isCompressedTexture || g.image[0].isCompressedTexture, j = g.image[0] && g.image[0].isDataTexture, lt = [];
      for (let Y = 0; Y < 6; Y++) !xt && !j ? lt[Y] = v(g.image[Y], true, s.maxCubemapSize) : lt[Y] = j ? g.image[Y].image : g.image[Y], lt[Y] = ue(g, lt[Y]);
      let At = lt[0], vt = r.convert(g.format, g.colorSpace), at = r.convert(g.type), Dt = T(g.internalFormat, vt, at, g.colorSpace), C = g.isVideoTexture !== true, tt = k.__version === void 0 || G === true, it = J.dataReady, ut = R(g, At);
      Ft(i14.TEXTURE_CUBE_MAP, g);
      let K;
      if (xt) {
        C && tt && e.texStorage2D(i14.TEXTURE_CUBE_MAP, ut, Dt, At.width, At.height);
        for (let Y = 0; Y < 6; Y++) {
          K = lt[Y].mipmaps;
          for (let pt = 0; pt < K.length; pt++) {
            let It = K[pt];
            g.format !== Fe ? vt !== null ? C ? it && e.compressedTexSubImage2D(i14.TEXTURE_CUBE_MAP_POSITIVE_X + Y, pt, 0, 0, It.width, It.height, vt, It.data) : e.compressedTexImage2D(i14.TEXTURE_CUBE_MAP_POSITIVE_X + Y, pt, Dt, It.width, It.height, 0, It.data) : console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .setTextureCube()") : C ? it && e.texSubImage2D(i14.TEXTURE_CUBE_MAP_POSITIVE_X + Y, pt, 0, 0, It.width, It.height, vt, at, It.data) : e.texImage2D(i14.TEXTURE_CUBE_MAP_POSITIVE_X + Y, pt, Dt, It.width, It.height, 0, vt, at, It.data);
          }
        }
      } else {
        if (K = g.mipmaps, C && tt) {
          K.length > 0 && ut++;
          let Y = ae(lt[0]);
          e.texStorage2D(i14.TEXTURE_CUBE_MAP, ut, Dt, Y.width, Y.height);
        }
        for (let Y = 0; Y < 6; Y++) if (j) {
          C ? it && e.texSubImage2D(i14.TEXTURE_CUBE_MAP_POSITIVE_X + Y, 0, 0, 0, lt[Y].width, lt[Y].height, vt, at, lt[Y].data) : e.texImage2D(i14.TEXTURE_CUBE_MAP_POSITIVE_X + Y, 0, Dt, lt[Y].width, lt[Y].height, 0, vt, at, lt[Y].data);
          for (let pt = 0; pt < K.length; pt++) {
            let $t = K[pt].image[Y].image;
            C ? it && e.texSubImage2D(i14.TEXTURE_CUBE_MAP_POSITIVE_X + Y, pt + 1, 0, 0, $t.width, $t.height, vt, at, $t.data) : e.texImage2D(i14.TEXTURE_CUBE_MAP_POSITIVE_X + Y, pt + 1, Dt, $t.width, $t.height, 0, vt, at, $t.data);
          }
        } else {
          C ? it && e.texSubImage2D(i14.TEXTURE_CUBE_MAP_POSITIVE_X + Y, 0, 0, 0, vt, at, lt[Y]) : e.texImage2D(i14.TEXTURE_CUBE_MAP_POSITIVE_X + Y, 0, Dt, vt, at, lt[Y]);
          for (let pt = 0; pt < K.length; pt++) {
            let It = K[pt];
            C ? it && e.texSubImage2D(i14.TEXTURE_CUBE_MAP_POSITIVE_X + Y, pt + 1, 0, 0, vt, at, It.image[Y]) : e.texImage2D(i14.TEXTURE_CUBE_MAP_POSITIVE_X + Y, pt + 1, Dt, vt, at, It.image[Y]);
          }
        }
      }
      p(g) && h(i14.TEXTURE_CUBE_MAP), k.__version = J.version, g.onUpdate && g.onUpdate(g);
    }
    S.__version = g.version;
  }
  function dt(S, g, U, G, J, k) {
    let yt = r.convert(U.format, U.colorSpace), nt = r.convert(U.type), _t = T(U.internalFormat, yt, nt, U.colorSpace), xt = n.get(g), j = n.get(U);
    if (j.__renderTarget = g, !xt.__hasExternalTextures) {
      let lt = Math.max(1, g.width >> k), At = Math.max(1, g.height >> k);
      J === i14.TEXTURE_3D || J === i14.TEXTURE_2D_ARRAY ? e.texImage3D(J, k, _t, lt, At, g.depth, 0, yt, nt, null) : e.texImage2D(J, k, _t, lt, At, 0, yt, nt, null);
    }
    e.bindFramebuffer(i14.FRAMEBUFFER, S), gt(g) ? o.framebufferTexture2DMultisampleEXT(i14.FRAMEBUFFER, G, J, j.__webglTexture, 0, ee(g)) : (J === i14.TEXTURE_2D || J >= i14.TEXTURE_CUBE_MAP_POSITIVE_X && J <= i14.TEXTURE_CUBE_MAP_NEGATIVE_Z) && i14.framebufferTexture2D(i14.FRAMEBUFFER, G, J, j.__webglTexture, k), e.bindFramebuffer(i14.FRAMEBUFFER, null);
  }
  function Rt(S, g, U) {
    if (i14.bindRenderbuffer(i14.RENDERBUFFER, S), g.depthBuffer) {
      let G = g.depthTexture, J = G && G.isDepthTexture ? G.type : null, k = b(g.stencilBuffer, J), yt = g.stencilBuffer ? i14.DEPTH_STENCIL_ATTACHMENT : i14.DEPTH_ATTACHMENT, nt = ee(g);
      gt(g) ? o.renderbufferStorageMultisampleEXT(i14.RENDERBUFFER, nt, k, g.width, g.height) : U ? i14.renderbufferStorageMultisample(i14.RENDERBUFFER, nt, k, g.width, g.height) : i14.renderbufferStorage(i14.RENDERBUFFER, k, g.width, g.height), i14.framebufferRenderbuffer(i14.FRAMEBUFFER, yt, i14.RENDERBUFFER, S);
    } else {
      let G = g.textures;
      for (let J = 0; J < G.length; J++) {
        let k = G[J], yt = r.convert(k.format, k.colorSpace), nt = r.convert(k.type), _t = T(k.internalFormat, yt, nt, k.colorSpace), xt = ee(g);
        U && gt(g) === false ? i14.renderbufferStorageMultisample(i14.RENDERBUFFER, xt, _t, g.width, g.height) : gt(g) ? o.renderbufferStorageMultisampleEXT(i14.RENDERBUFFER, xt, _t, g.width, g.height) : i14.renderbufferStorage(i14.RENDERBUFFER, _t, g.width, g.height);
      }
    }
    i14.bindRenderbuffer(i14.RENDERBUFFER, null);
  }
  function Mt(S, g) {
    if (g && g.isWebGLCubeRenderTarget) throw new Error("Depth Texture with cube render targets is not supported");
    if (e.bindFramebuffer(i14.FRAMEBUFFER, S), !(g.depthTexture && g.depthTexture.isDepthTexture)) throw new Error("renderTarget.depthTexture must be an instance of THREE.DepthTexture");
    let G = n.get(g.depthTexture);
    G.__renderTarget = g, (!G.__webglTexture || g.depthTexture.image.width !== g.width || g.depthTexture.image.height !== g.height) && (g.depthTexture.image.width = g.width, g.depthTexture.image.height = g.height, g.depthTexture.needsUpdate = true), Z(g.depthTexture, 0);
    let J = G.__webglTexture, k = ee(g);
    if (g.depthTexture.format === ci) gt(g) ? o.framebufferTexture2DMultisampleEXT(i14.FRAMEBUFFER, i14.DEPTH_ATTACHMENT, i14.TEXTURE_2D, J, 0, k) : i14.framebufferTexture2D(i14.FRAMEBUFFER, i14.DEPTH_ATTACHMENT, i14.TEXTURE_2D, J, 0);
    else if (g.depthTexture.format === vi) gt(g) ? o.framebufferTexture2DMultisampleEXT(i14.FRAMEBUFFER, i14.DEPTH_STENCIL_ATTACHMENT, i14.TEXTURE_2D, J, 0, k) : i14.framebufferTexture2D(i14.FRAMEBUFFER, i14.DEPTH_STENCIL_ATTACHMENT, i14.TEXTURE_2D, J, 0);
    else throw new Error("Unknown depthTexture format");
  }
  function zt(S) {
    let g = n.get(S), U = S.isWebGLCubeRenderTarget === true;
    if (g.__boundDepthTexture !== S.depthTexture) {
      let G = S.depthTexture;
      if (g.__depthDisposeCallback && g.__depthDisposeCallback(), G) {
        let J = () => {
          delete g.__boundDepthTexture, delete g.__depthDisposeCallback, G.removeEventListener("dispose", J);
        };
        G.addEventListener("dispose", J), g.__depthDisposeCallback = J;
      }
      g.__boundDepthTexture = G;
    }
    if (S.depthTexture && !g.__autoAllocateDepthBuffer) {
      if (U) throw new Error("target.depthTexture not supported in Cube render targets");
      let G = S.texture.mipmaps;
      G && G.length > 0 ? Mt(g.__webglFramebuffer[0], S) : Mt(g.__webglFramebuffer, S);
    } else if (U) {
      g.__webglDepthbuffer = [];
      for (let G = 0; G < 6; G++) if (e.bindFramebuffer(i14.FRAMEBUFFER, g.__webglFramebuffer[G]), g.__webglDepthbuffer[G] === void 0) g.__webglDepthbuffer[G] = i14.createRenderbuffer(), Rt(g.__webglDepthbuffer[G], S, false);
      else {
        let J = S.stencilBuffer ? i14.DEPTH_STENCIL_ATTACHMENT : i14.DEPTH_ATTACHMENT, k = g.__webglDepthbuffer[G];
        i14.bindRenderbuffer(i14.RENDERBUFFER, k), i14.framebufferRenderbuffer(i14.FRAMEBUFFER, J, i14.RENDERBUFFER, k);
      }
    } else {
      let G = S.texture.mipmaps;
      if (G && G.length > 0 ? e.bindFramebuffer(i14.FRAMEBUFFER, g.__webglFramebuffer[0]) : e.bindFramebuffer(i14.FRAMEBUFFER, g.__webglFramebuffer), g.__webglDepthbuffer === void 0) g.__webglDepthbuffer = i14.createRenderbuffer(), Rt(g.__webglDepthbuffer, S, false);
      else {
        let J = S.stencilBuffer ? i14.DEPTH_STENCIL_ATTACHMENT : i14.DEPTH_ATTACHMENT, k = g.__webglDepthbuffer;
        i14.bindRenderbuffer(i14.RENDERBUFFER, k), i14.framebufferRenderbuffer(i14.FRAMEBUFFER, J, i14.RENDERBUFFER, k);
      }
    }
    e.bindFramebuffer(i14.FRAMEBUFFER, null);
  }
  function fe(S, g, U) {
    let G = n.get(S);
    g !== void 0 && dt(G.__webglFramebuffer, S, S.texture, i14.COLOR_ATTACHMENT0, i14.TEXTURE_2D, 0), U !== void 0 && zt(S);
  }
  function E(S) {
    let g = S.texture, U = n.get(S), G = n.get(g);
    S.addEventListener("dispose", P);
    let J = S.textures, k = S.isWebGLCubeRenderTarget === true, yt = J.length > 1;
    if (yt || (G.__webglTexture === void 0 && (G.__webglTexture = i14.createTexture()), G.__version = g.version, a.memory.textures++), k) {
      U.__webglFramebuffer = [];
      for (let nt = 0; nt < 6; nt++) if (g.mipmaps && g.mipmaps.length > 0) {
        U.__webglFramebuffer[nt] = [];
        for (let _t = 0; _t < g.mipmaps.length; _t++) U.__webglFramebuffer[nt][_t] = i14.createFramebuffer();
      } else U.__webglFramebuffer[nt] = i14.createFramebuffer();
    } else {
      if (g.mipmaps && g.mipmaps.length > 0) {
        U.__webglFramebuffer = [];
        for (let nt = 0; nt < g.mipmaps.length; nt++) U.__webglFramebuffer[nt] = i14.createFramebuffer();
      } else U.__webglFramebuffer = i14.createFramebuffer();
      if (yt) for (let nt = 0, _t = J.length; nt < _t; nt++) {
        let xt = n.get(J[nt]);
        xt.__webglTexture === void 0 && (xt.__webglTexture = i14.createTexture(), a.memory.textures++);
      }
      if (S.samples > 0 && gt(S) === false) {
        U.__webglMultisampledFramebuffer = i14.createFramebuffer(), U.__webglColorRenderbuffer = [], e.bindFramebuffer(i14.FRAMEBUFFER, U.__webglMultisampledFramebuffer);
        for (let nt = 0; nt < J.length; nt++) {
          let _t = J[nt];
          U.__webglColorRenderbuffer[nt] = i14.createRenderbuffer(), i14.bindRenderbuffer(i14.RENDERBUFFER, U.__webglColorRenderbuffer[nt]);
          let xt = r.convert(_t.format, _t.colorSpace), j = r.convert(_t.type), lt = T(_t.internalFormat, xt, j, _t.colorSpace, S.isXRRenderTarget === true), At = ee(S);
          i14.renderbufferStorageMultisample(i14.RENDERBUFFER, At, lt, S.width, S.height), i14.framebufferRenderbuffer(i14.FRAMEBUFFER, i14.COLOR_ATTACHMENT0 + nt, i14.RENDERBUFFER, U.__webglColorRenderbuffer[nt]);
        }
        i14.bindRenderbuffer(i14.RENDERBUFFER, null), S.depthBuffer && (U.__webglDepthRenderbuffer = i14.createRenderbuffer(), Rt(U.__webglDepthRenderbuffer, S, true)), e.bindFramebuffer(i14.FRAMEBUFFER, null);
      }
    }
    if (k) {
      e.bindTexture(i14.TEXTURE_CUBE_MAP, G.__webglTexture), Ft(i14.TEXTURE_CUBE_MAP, g);
      for (let nt = 0; nt < 6; nt++) if (g.mipmaps && g.mipmaps.length > 0) for (let _t = 0; _t < g.mipmaps.length; _t++) dt(U.__webglFramebuffer[nt][_t], S, g, i14.COLOR_ATTACHMENT0, i14.TEXTURE_CUBE_MAP_POSITIVE_X + nt, _t);
      else dt(U.__webglFramebuffer[nt], S, g, i14.COLOR_ATTACHMENT0, i14.TEXTURE_CUBE_MAP_POSITIVE_X + nt, 0);
      p(g) && h(i14.TEXTURE_CUBE_MAP), e.unbindTexture();
    } else if (yt) {
      for (let nt = 0, _t = J.length; nt < _t; nt++) {
        let xt = J[nt], j = n.get(xt), lt = i14.TEXTURE_2D;
        (S.isWebGL3DRenderTarget || S.isWebGLArrayRenderTarget) && (lt = S.isWebGL3DRenderTarget ? i14.TEXTURE_3D : i14.TEXTURE_2D_ARRAY), e.bindTexture(lt, j.__webglTexture), Ft(lt, xt), dt(U.__webglFramebuffer, S, xt, i14.COLOR_ATTACHMENT0 + nt, lt, 0), p(xt) && h(lt);
      }
      e.unbindTexture();
    } else {
      let nt = i14.TEXTURE_2D;
      if ((S.isWebGL3DRenderTarget || S.isWebGLArrayRenderTarget) && (nt = S.isWebGL3DRenderTarget ? i14.TEXTURE_3D : i14.TEXTURE_2D_ARRAY), e.bindTexture(nt, G.__webglTexture), Ft(nt, g), g.mipmaps && g.mipmaps.length > 0) for (let _t = 0; _t < g.mipmaps.length; _t++) dt(U.__webglFramebuffer[_t], S, g, i14.COLOR_ATTACHMENT0, nt, _t);
      else dt(U.__webglFramebuffer, S, g, i14.COLOR_ATTACHMENT0, nt, 0);
      p(g) && h(nt), e.unbindTexture();
    }
    S.depthBuffer && zt(S);
  }
  function te(S) {
    let g = S.textures;
    for (let U = 0, G = g.length; U < G; U++) {
      let J = g[U];
      if (p(J)) {
        let k = A(S), yt = n.get(J).__webglTexture;
        e.bindTexture(k, yt), h(k), e.unbindTexture();
      }
    }
  }
  let Pt = [], wt = [];
  function mt(S) {
    if (S.samples > 0) {
      if (gt(S) === false) {
        let g = S.textures, U = S.width, G = S.height, J = i14.COLOR_BUFFER_BIT, k = S.stencilBuffer ? i14.DEPTH_STENCIL_ATTACHMENT : i14.DEPTH_ATTACHMENT, yt = n.get(S), nt = g.length > 1;
        if (nt) for (let xt = 0; xt < g.length; xt++) e.bindFramebuffer(i14.FRAMEBUFFER, yt.__webglMultisampledFramebuffer), i14.framebufferRenderbuffer(i14.FRAMEBUFFER, i14.COLOR_ATTACHMENT0 + xt, i14.RENDERBUFFER, null), e.bindFramebuffer(i14.FRAMEBUFFER, yt.__webglFramebuffer), i14.framebufferTexture2D(i14.DRAW_FRAMEBUFFER, i14.COLOR_ATTACHMENT0 + xt, i14.TEXTURE_2D, null, 0);
        e.bindFramebuffer(i14.READ_FRAMEBUFFER, yt.__webglMultisampledFramebuffer);
        let _t = S.texture.mipmaps;
        _t && _t.length > 0 ? e.bindFramebuffer(i14.DRAW_FRAMEBUFFER, yt.__webglFramebuffer[0]) : e.bindFramebuffer(i14.DRAW_FRAMEBUFFER, yt.__webglFramebuffer);
        for (let xt = 0; xt < g.length; xt++) {
          if (S.resolveDepthBuffer && (S.depthBuffer && (J |= i14.DEPTH_BUFFER_BIT), S.stencilBuffer && S.resolveStencilBuffer && (J |= i14.STENCIL_BUFFER_BIT)), nt) {
            i14.framebufferRenderbuffer(i14.READ_FRAMEBUFFER, i14.COLOR_ATTACHMENT0, i14.RENDERBUFFER, yt.__webglColorRenderbuffer[xt]);
            let j = n.get(g[xt]).__webglTexture;
            i14.framebufferTexture2D(i14.DRAW_FRAMEBUFFER, i14.COLOR_ATTACHMENT0, i14.TEXTURE_2D, j, 0);
          }
          i14.blitFramebuffer(0, 0, U, G, 0, 0, U, G, J, i14.NEAREST), c === true && (Pt.length = 0, wt.length = 0, Pt.push(i14.COLOR_ATTACHMENT0 + xt), S.depthBuffer && S.resolveDepthBuffer === false && (Pt.push(k), wt.push(k), i14.invalidateFramebuffer(i14.DRAW_FRAMEBUFFER, wt)), i14.invalidateFramebuffer(i14.READ_FRAMEBUFFER, Pt));
        }
        if (e.bindFramebuffer(i14.READ_FRAMEBUFFER, null), e.bindFramebuffer(i14.DRAW_FRAMEBUFFER, null), nt) for (let xt = 0; xt < g.length; xt++) {
          e.bindFramebuffer(i14.FRAMEBUFFER, yt.__webglMultisampledFramebuffer), i14.framebufferRenderbuffer(i14.FRAMEBUFFER, i14.COLOR_ATTACHMENT0 + xt, i14.RENDERBUFFER, yt.__webglColorRenderbuffer[xt]);
          let j = n.get(g[xt]).__webglTexture;
          e.bindFramebuffer(i14.FRAMEBUFFER, yt.__webglFramebuffer), i14.framebufferTexture2D(i14.DRAW_FRAMEBUFFER, i14.COLOR_ATTACHMENT0 + xt, i14.TEXTURE_2D, j, 0);
        }
        e.bindFramebuffer(i14.DRAW_FRAMEBUFFER, yt.__webglMultisampledFramebuffer);
      } else if (S.depthBuffer && S.resolveDepthBuffer === false && c) {
        let g = S.stencilBuffer ? i14.DEPTH_STENCIL_ATTACHMENT : i14.DEPTH_ATTACHMENT;
        i14.invalidateFramebuffer(i14.DRAW_FRAMEBUFFER, [g]);
      }
    }
  }
  function ee(S) {
    return Math.min(s.maxSamples, S.samples);
  }
  function gt(S) {
    let g = n.get(S);
    return S.samples > 0 && t3.has("WEBGL_multisampled_render_to_texture") === true && g.__useRenderToTexture !== false;
  }
  function Ut(S) {
    let g = a.render.frame;
    u.get(S) !== g && (u.set(S, g), S.update());
  }
  function ue(S, g) {
    let U = S.colorSpace, G = S.format, J = S.type;
    return S.isCompressedTexture === true || S.isVideoTexture === true || U !== zn && U !== dn && (kt.getTransfer(U) === qt ? (G !== Fe || J !== We) && console.warn("THREE.WebGLTextures: sRGB encoded textures have to use RGBAFormat and UnsignedByteType.") : console.error("THREE.WebGLTextures: Unsupported texture color space:", U)), g;
  }
  function ae(S) {
    return typeof HTMLImageElement < "u" && S instanceof HTMLImageElement ? (l.width = S.naturalWidth || S.width, l.height = S.naturalHeight || S.height) : typeof VideoFrame < "u" && S instanceof VideoFrame ? (l.width = S.displayWidth, l.height = S.displayHeight) : (l.width = S.width, l.height = S.height), l;
  }
  this.allocateTextureUnit = H, this.resetTextureUnits = z, this.setTexture2D = Z, this.setTexture2DArray = W, this.setTexture3D = et, this.setTextureCube = V, this.rebindTextures = fe, this.setupRenderTarget = E, this.updateRenderTargetMipmap = te, this.updateMultisampleRenderTarget = mt, this.setupDepthRenderbuffer = zt, this.setupFrameBufferTexture = dt, this.useMultisampledRTT = gt;
}
function cp(i14, t3) {
  function e(n, s = dn) {
    let r, a = kt.getTransfer(s);
    if (n === We) return i14.UNSIGNED_BYTE;
    if (n === ar) return i14.UNSIGNED_SHORT_4_4_4_4;
    if (n === or) return i14.UNSIGNED_SHORT_5_5_5_1;
    if (n === Ua) return i14.UNSIGNED_INT_5_9_9_9_REV;
    if (n === Na) return i14.UNSIGNED_INT_10F_11F_11F_REV;
    if (n === La) return i14.BYTE;
    if (n === Da) return i14.SHORT;
    if (n === gi) return i14.UNSIGNED_SHORT;
    if (n === rr) return i14.INT;
    if (n === Cn) return i14.UNSIGNED_INT;
    if (n === Ke) return i14.FLOAT;
    if (n === _i) return i14.HALF_FLOAT;
    if (n === Fa) return i14.ALPHA;
    if (n === Oa) return i14.RGB;
    if (n === Fe) return i14.RGBA;
    if (n === ci) return i14.DEPTH_COMPONENT;
    if (n === vi) return i14.DEPTH_STENCIL;
    if (n === Ba) return i14.RED;
    if (n === lr) return i14.RED_INTEGER;
    if (n === za) return i14.RG;
    if (n === cr) return i14.RG_INTEGER;
    if (n === hr) return i14.RGBA_INTEGER;
    if (n === Zi || n === Ji || n === $i || n === Ki) if (a === qt) if (r = t3.get("WEBGL_compressed_texture_s3tc_srgb"), r !== null) {
      if (n === Zi) return r.COMPRESSED_SRGB_S3TC_DXT1_EXT;
      if (n === Ji) return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT1_EXT;
      if (n === $i) return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT3_EXT;
      if (n === Ki) return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT5_EXT;
    } else return null;
    else if (r = t3.get("WEBGL_compressed_texture_s3tc"), r !== null) {
      if (n === Zi) return r.COMPRESSED_RGB_S3TC_DXT1_EXT;
      if (n === Ji) return r.COMPRESSED_RGBA_S3TC_DXT1_EXT;
      if (n === $i) return r.COMPRESSED_RGBA_S3TC_DXT3_EXT;
      if (n === Ki) return r.COMPRESSED_RGBA_S3TC_DXT5_EXT;
    } else return null;
    if (n === ur || n === dr || n === fr || n === pr) if (r = t3.get("WEBGL_compressed_texture_pvrtc"), r !== null) {
      if (n === ur) return r.COMPRESSED_RGB_PVRTC_4BPPV1_IMG;
      if (n === dr) return r.COMPRESSED_RGB_PVRTC_2BPPV1_IMG;
      if (n === fr) return r.COMPRESSED_RGBA_PVRTC_4BPPV1_IMG;
      if (n === pr) return r.COMPRESSED_RGBA_PVRTC_2BPPV1_IMG;
    } else return null;
    if (n === mr || n === gr || n === _r) if (r = t3.get("WEBGL_compressed_texture_etc"), r !== null) {
      if (n === mr || n === gr) return a === qt ? r.COMPRESSED_SRGB8_ETC2 : r.COMPRESSED_RGB8_ETC2;
      if (n === _r) return a === qt ? r.COMPRESSED_SRGB8_ALPHA8_ETC2_EAC : r.COMPRESSED_RGBA8_ETC2_EAC;
    } else return null;
    if (n === xr || n === vr || n === yr || n === Mr || n === Sr || n === br || n === Er || n === Tr || n === Ar || n === wr || n === Cr || n === Rr || n === Ir || n === Pr) if (r = t3.get("WEBGL_compressed_texture_astc"), r !== null) {
      if (n === xr) return a === qt ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_4x4_KHR : r.COMPRESSED_RGBA_ASTC_4x4_KHR;
      if (n === vr) return a === qt ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_5x4_KHR : r.COMPRESSED_RGBA_ASTC_5x4_KHR;
      if (n === yr) return a === qt ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_5x5_KHR : r.COMPRESSED_RGBA_ASTC_5x5_KHR;
      if (n === Mr) return a === qt ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_6x5_KHR : r.COMPRESSED_RGBA_ASTC_6x5_KHR;
      if (n === Sr) return a === qt ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_6x6_KHR : r.COMPRESSED_RGBA_ASTC_6x6_KHR;
      if (n === br) return a === qt ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x5_KHR : r.COMPRESSED_RGBA_ASTC_8x5_KHR;
      if (n === Er) return a === qt ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x6_KHR : r.COMPRESSED_RGBA_ASTC_8x6_KHR;
      if (n === Tr) return a === qt ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x8_KHR : r.COMPRESSED_RGBA_ASTC_8x8_KHR;
      if (n === Ar) return a === qt ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x5_KHR : r.COMPRESSED_RGBA_ASTC_10x5_KHR;
      if (n === wr) return a === qt ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x6_KHR : r.COMPRESSED_RGBA_ASTC_10x6_KHR;
      if (n === Cr) return a === qt ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x8_KHR : r.COMPRESSED_RGBA_ASTC_10x8_KHR;
      if (n === Rr) return a === qt ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x10_KHR : r.COMPRESSED_RGBA_ASTC_10x10_KHR;
      if (n === Ir) return a === qt ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_12x10_KHR : r.COMPRESSED_RGBA_ASTC_12x10_KHR;
      if (n === Pr) return a === qt ? r.COMPRESSED_SRGB8_ALPHA8_ASTC_12x12_KHR : r.COMPRESSED_RGBA_ASTC_12x12_KHR;
    } else return null;
    if (n === Lr || n === Dr || n === Ur) if (r = t3.get("EXT_texture_compression_bptc"), r !== null) {
      if (n === Lr) return a === qt ? r.COMPRESSED_SRGB_ALPHA_BPTC_UNORM_EXT : r.COMPRESSED_RGBA_BPTC_UNORM_EXT;
      if (n === Dr) return r.COMPRESSED_RGB_BPTC_SIGNED_FLOAT_EXT;
      if (n === Ur) return r.COMPRESSED_RGB_BPTC_UNSIGNED_FLOAT_EXT;
    } else return null;
    if (n === Nr || n === Fr || n === Or || n === Br) if (r = t3.get("EXT_texture_compression_rgtc"), r !== null) {
      if (n === Nr) return r.COMPRESSED_RED_RGTC1_EXT;
      if (n === Fr) return r.COMPRESSED_SIGNED_RED_RGTC1_EXT;
      if (n === Or) return r.COMPRESSED_RED_GREEN_RGTC2_EXT;
      if (n === Br) return r.COMPRESSED_SIGNED_RED_GREEN_RGTC2_EXT;
    } else return null;
    return n === xi ? i14.UNSIGNED_INT_24_8 : i14[n] !== void 0 ? i14[n] : null;
  }
  return { convert: e };
}
var hp = `
void main() {

	gl_Position = vec4( position, 1.0 );

}`;
var up = `
uniform sampler2DArray depthColor;
uniform float depthWidth;
uniform float depthHeight;

void main() {

	vec2 coord = vec2( gl_FragCoord.x / depthWidth, gl_FragCoord.y / depthHeight );

	if ( coord.x >= 1.0 ) {

		gl_FragDepth = texture( depthColor, vec3( coord.x - 1.0, coord.y, 1 ) ).r;

	} else {

		gl_FragDepth = texture( depthColor, vec3( coord.x, coord.y, 0 ) ).r;

	}

}`;
var ao = class {
  constructor() {
    this.texture = null, this.mesh = null, this.depthNear = 0, this.depthFar = 0;
  }
  init(t3, e) {
    if (this.texture === null) {
      let n = new Hi(t3.texture);
      (t3.depthNear !== e.depthNear || t3.depthFar !== e.depthFar) && (this.depthNear = t3.depthNear, this.depthFar = t3.depthFar), this.texture = n;
    }
  }
  getMesh(t3) {
    if (this.texture !== null && this.mesh === null) {
      let e = t3.cameras[0].viewport, n = new Ge({ vertexShader: hp, fragmentShader: up, uniforms: { depthColor: { value: this.texture }, depthWidth: { value: e.z }, depthHeight: { value: e.w } } });
      this.mesh = new Ie(new Gi(20, 20), n);
    }
    return this.mesh;
  }
  reset() {
    this.texture = null, this.mesh = null;
  }
  getDepthTexture() {
    return this.texture;
  }
};
var oo = class extends ln {
  constructor(t3, e) {
    super();
    let n = this, s = null, r = 1, a = null, o = "local-floor", c = 1, l = null, u = null, d = null, f = null, m = null, x = null, v = typeof XRWebGLBinding < "u", p = new ao(), h = {}, A = e.getContextAttributes(), T = null, b = null, R = [], w = [], P = new Gt(), N = null, M = new Se();
    M.viewport = new se();
    let y = new Se();
    y.viewport = new se();
    let I = [M, y], z = new Zs(), H = null, X = null;
    this.cameraAutoUpdate = true, this.enabled = false, this.isPresenting = false, this.getController = function(q) {
      let $2 = R[q];
      return $2 === void 0 && ($2 = new fi(), R[q] = $2), $2.getTargetRaySpace();
    }, this.getControllerGrip = function(q) {
      let $2 = R[q];
      return $2 === void 0 && ($2 = new fi(), R[q] = $2), $2.getGripSpace();
    }, this.getHand = function(q) {
      let $2 = R[q];
      return $2 === void 0 && ($2 = new fi(), R[q] = $2), $2.getHandSpace();
    };
    function Z(q) {
      let $2 = w.indexOf(q.inputSource);
      if ($2 === -1) return;
      let dt = R[$2];
      dt !== void 0 && (dt.update(q.inputSource, q.frame, l || a), dt.dispatchEvent({ type: q.type, data: q.inputSource }));
    }
    function W() {
      s.removeEventListener("select", Z), s.removeEventListener("selectstart", Z), s.removeEventListener("selectend", Z), s.removeEventListener("squeeze", Z), s.removeEventListener("squeezestart", Z), s.removeEventListener("squeezeend", Z), s.removeEventListener("end", W), s.removeEventListener("inputsourceschange", et);
      for (let q = 0; q < R.length; q++) {
        let $2 = w[q];
        $2 !== null && (w[q] = null, R[q].disconnect($2));
      }
      H = null, X = null, p.reset();
      for (let q in h) delete h[q];
      t3.setRenderTarget(T), m = null, f = null, d = null, s = null, b = null, Wt.stop(), n.isPresenting = false, t3.setPixelRatio(N), t3.setSize(P.width, P.height, false), n.dispatchEvent({ type: "sessionend" });
    }
    this.setFramebufferScaleFactor = function(q) {
      r = q, n.isPresenting === true && console.warn("THREE.WebXRManager: Cannot change framebuffer scale while presenting.");
    }, this.setReferenceSpaceType = function(q) {
      o = q, n.isPresenting === true && console.warn("THREE.WebXRManager: Cannot change reference space type while presenting.");
    }, this.getReferenceSpace = function() {
      return l || a;
    }, this.setReferenceSpace = function(q) {
      l = q;
    }, this.getBaseLayer = function() {
      return f !== null ? f : m;
    }, this.getBinding = function() {
      return d === null && v && (d = new XRWebGLBinding(s, e)), d;
    }, this.getFrame = function() {
      return x;
    }, this.getSession = function() {
      return s;
    }, this.setSession = async function(q) {
      if (s = q, s !== null) {
        if (T = t3.getRenderTarget(), s.addEventListener("select", Z), s.addEventListener("selectstart", Z), s.addEventListener("selectend", Z), s.addEventListener("squeeze", Z), s.addEventListener("squeezestart", Z), s.addEventListener("squeezeend", Z), s.addEventListener("end", W), s.addEventListener("inputsourceschange", et), A.xrCompatible !== true && await e.makeXRCompatible(), N = t3.getPixelRatio(), t3.getSize(P), v && "createProjectionLayer" in XRWebGLBinding.prototype) {
          let dt = null, Rt = null, Mt = null;
          A.depth && (Mt = A.stencil ? e.DEPTH24_STENCIL8 : e.DEPTH_COMPONENT24, dt = A.stencil ? vi : ci, Rt = A.stencil ? xi : Cn);
          let zt = { colorFormat: e.RGBA8, depthFormat: Mt, scaleFactor: r };
          d = this.getBinding(), f = d.createProjectionLayer(zt), s.updateRenderState({ layers: [f] }), t3.setPixelRatio(1), t3.setSize(f.textureWidth, f.textureHeight, false), b = new Ze(f.textureWidth, f.textureHeight, { format: Fe, type: We, depthTexture: new ki(f.textureWidth, f.textureHeight, Rt, void 0, void 0, void 0, void 0, void 0, void 0, dt), stencilBuffer: A.stencil, colorSpace: t3.outputColorSpace, samples: A.antialias ? 4 : 0, resolveDepthBuffer: f.ignoreDepthValues === false, resolveStencilBuffer: f.ignoreDepthValues === false });
        } else {
          let dt = { antialias: A.antialias, alpha: true, depth: A.depth, stencil: A.stencil, framebufferScaleFactor: r };
          m = new XRWebGLLayer(s, e, dt), s.updateRenderState({ baseLayer: m }), t3.setPixelRatio(1), t3.setSize(m.framebufferWidth, m.framebufferHeight, false), b = new Ze(m.framebufferWidth, m.framebufferHeight, { format: Fe, type: We, colorSpace: t3.outputColorSpace, stencilBuffer: A.stencil, resolveDepthBuffer: m.ignoreDepthValues === false, resolveStencilBuffer: m.ignoreDepthValues === false });
        }
        b.isXRRenderTarget = true, this.setFoveation(c), l = null, a = await s.requestReferenceSpace(o), Wt.setContext(s), Wt.start(), n.isPresenting = true, n.dispatchEvent({ type: "sessionstart" });
      }
    }, this.getEnvironmentBlendMode = function() {
      if (s !== null) return s.environmentBlendMode;
    }, this.getDepthTexture = function() {
      return p.getDepthTexture();
    };
    function et(q) {
      for (let $2 = 0; $2 < q.removed.length; $2++) {
        let dt = q.removed[$2], Rt = w.indexOf(dt);
        Rt >= 0 && (w[Rt] = null, R[Rt].disconnect(dt));
      }
      for (let $2 = 0; $2 < q.added.length; $2++) {
        let dt = q.added[$2], Rt = w.indexOf(dt);
        if (Rt === -1) {
          for (let zt = 0; zt < R.length; zt++) if (zt >= w.length) {
            w.push(dt), Rt = zt;
            break;
          } else if (w[zt] === null) {
            w[zt] = dt, Rt = zt;
            break;
          }
          if (Rt === -1) break;
        }
        let Mt = R[Rt];
        Mt && Mt.connect(dt);
      }
    }
    let V = new F(), rt = new F();
    function ct(q, $2, dt) {
      V.setFromMatrixPosition($2.matrixWorld), rt.setFromMatrixPosition(dt.matrixWorld);
      let Rt = V.distanceTo(rt), Mt = $2.projectionMatrix.elements, zt = dt.projectionMatrix.elements, fe = Mt[14] / (Mt[10] - 1), E = Mt[14] / (Mt[10] + 1), te = (Mt[9] + 1) / Mt[5], Pt = (Mt[9] - 1) / Mt[5], wt = (Mt[8] - 1) / Mt[0], mt = (zt[8] + 1) / zt[0], ee = fe * wt, gt = fe * mt, Ut = Rt / (-wt + mt), ue = Ut * -wt;
      if ($2.matrixWorld.decompose(q.position, q.quaternion, q.scale), q.translateX(ue), q.translateZ(Ut), q.matrixWorld.compose(q.position, q.quaternion, q.scale), q.matrixWorldInverse.copy(q.matrixWorld).invert(), Mt[10] === -1) q.projectionMatrix.copy($2.projectionMatrix), q.projectionMatrixInverse.copy($2.projectionMatrixInverse);
      else {
        let ae = fe + Ut, S = E + Ut, g = ee - ue, U = gt + (Rt - ue), G = te * E / S * ae, J = Pt * E / S * ae;
        q.projectionMatrix.makePerspective(g, U, G, J, ae, S), q.projectionMatrixInverse.copy(q.projectionMatrix).invert();
      }
    }
    function St(q, $2) {
      $2 === null ? q.matrixWorld.copy(q.matrix) : q.matrixWorld.multiplyMatrices($2.matrixWorld, q.matrix), q.matrixWorldInverse.copy(q.matrixWorld).invert();
    }
    this.updateCamera = function(q) {
      if (s === null) return;
      let $2 = q.near, dt = q.far;
      p.texture !== null && (p.depthNear > 0 && ($2 = p.depthNear), p.depthFar > 0 && (dt = p.depthFar)), z.near = y.near = M.near = $2, z.far = y.far = M.far = dt, (H !== z.near || X !== z.far) && (s.updateRenderState({ depthNear: z.near, depthFar: z.far }), H = z.near, X = z.far), z.layers.mask = q.layers.mask | 6, M.layers.mask = z.layers.mask & 3, y.layers.mask = z.layers.mask & 5;
      let Rt = q.parent, Mt = z.cameras;
      St(z, Rt);
      for (let zt = 0; zt < Mt.length; zt++) St(Mt[zt], Rt);
      Mt.length === 2 ? ct(z, M, y) : z.projectionMatrix.copy(M.projectionMatrix), Ft(q, z, Rt);
    };
    function Ft(q, $2, dt) {
      dt === null ? q.matrix.copy($2.matrixWorld) : (q.matrix.copy(dt.matrixWorld), q.matrix.invert(), q.matrix.multiply($2.matrixWorld)), q.matrix.decompose(q.position, q.quaternion, q.scale), q.updateMatrixWorld(true), q.projectionMatrix.copy($2.projectionMatrix), q.projectionMatrixInverse.copy($2.projectionMatrixInverse), q.isPerspectiveCamera && (q.fov = As * 2 * Math.atan(1 / q.projectionMatrix.elements[5]), q.zoom = 1);
    }
    this.getCamera = function() {
      return z;
    }, this.getFoveation = function() {
      if (!(f === null && m === null)) return c;
    }, this.setFoveation = function(q) {
      c = q, f !== null && (f.fixedFoveation = q), m !== null && m.fixedFoveation !== void 0 && (m.fixedFoveation = q);
    }, this.hasDepthSensing = function() {
      return p.texture !== null;
    }, this.getDepthSensingMesh = function() {
      return p.getMesh(z);
    }, this.getCameraTexture = function(q) {
      return h[q];
    };
    let Jt = null;
    function jt(q, $2) {
      if (u = $2.getViewerPose(l || a), x = $2, u !== null) {
        let dt = u.views;
        m !== null && (t3.setRenderTargetFramebuffer(b, m.framebuffer), t3.setRenderTarget(b));
        let Rt = false;
        dt.length !== z.cameras.length && (z.cameras.length = 0, Rt = true);
        for (let E = 0; E < dt.length; E++) {
          let te = dt[E], Pt = null;
          if (m !== null) Pt = m.getViewport(te);
          else {
            let mt = d.getViewSubImage(f, te);
            Pt = mt.viewport, E === 0 && (t3.setRenderTargetTextures(b, mt.colorTexture, mt.depthStencilTexture), t3.setRenderTarget(b));
          }
          let wt = I[E];
          wt === void 0 && (wt = new Se(), wt.layers.enable(E), wt.viewport = new se(), I[E] = wt), wt.matrix.fromArray(te.transform.matrix), wt.matrix.decompose(wt.position, wt.quaternion, wt.scale), wt.projectionMatrix.fromArray(te.projectionMatrix), wt.projectionMatrixInverse.copy(wt.projectionMatrix).invert(), wt.viewport.set(Pt.x, Pt.y, Pt.width, Pt.height), E === 0 && (z.matrix.copy(wt.matrix), z.matrix.decompose(z.position, z.quaternion, z.scale)), Rt === true && z.cameras.push(wt);
        }
        let Mt = s.enabledFeatures;
        if (Mt && Mt.includes("depth-sensing") && s.depthUsage == "gpu-optimized" && v) {
          d = n.getBinding();
          let E = d.getDepthInformation(dt[0]);
          E && E.isValid && E.texture && p.init(E, s.renderState);
        }
        if (Mt && Mt.includes("camera-access") && v) {
          t3.state.unbindTexture(), d = n.getBinding();
          for (let E = 0; E < dt.length; E++) {
            let te = dt[E].camera;
            if (te) {
              let Pt = h[te];
              Pt || (Pt = new Hi(), h[te] = Pt);
              let wt = d.getCameraImage(te);
              Pt.sourceTexture = wt;
            }
          }
        }
      }
      for (let dt = 0; dt < R.length; dt++) {
        let Rt = w[dt], Mt = R[dt];
        Rt !== null && Mt !== void 0 && Mt.update(Rt, $2, l || a);
      }
      Jt && Jt(q, $2), $2.detectedPlanes && n.dispatchEvent({ type: "planesdetected", data: $2 }), x = null;
    }
    let Wt = new Kl();
    Wt.setAnimationLoop(jt), this.setAnimationLoop = function(q) {
      Jt = q;
    }, this.dispose = function() {
    };
  }
};
var qn = new He();
var dp = new oe();
function fp(i14, t3) {
  function e(p, h) {
    p.matrixAutoUpdate === true && p.updateMatrix(), h.value.copy(p.matrix);
  }
  function n(p, h) {
    h.color.getRGB(p.fogColor.value, Wa(i14)), h.isFog ? (p.fogNear.value = h.near, p.fogFar.value = h.far) : h.isFogExp2 && (p.fogDensity.value = h.density);
  }
  function s(p, h, A, T, b) {
    h.isMeshBasicMaterial || h.isMeshLambertMaterial ? r(p, h) : h.isMeshToonMaterial ? (r(p, h), d(p, h)) : h.isMeshPhongMaterial ? (r(p, h), u(p, h)) : h.isMeshStandardMaterial ? (r(p, h), f(p, h), h.isMeshPhysicalMaterial && m(p, h, b)) : h.isMeshMatcapMaterial ? (r(p, h), x(p, h)) : h.isMeshDepthMaterial ? r(p, h) : h.isMeshDistanceMaterial ? (r(p, h), v(p, h)) : h.isMeshNormalMaterial ? r(p, h) : h.isLineBasicMaterial ? (a(p, h), h.isLineDashedMaterial && o(p, h)) : h.isPointsMaterial ? c(p, h, A, T) : h.isSpriteMaterial ? l(p, h) : h.isShadowMaterial ? (p.color.value.copy(h.color), p.opacity.value = h.opacity) : h.isShaderMaterial && (h.uniformsNeedUpdate = false);
  }
  function r(p, h) {
    p.opacity.value = h.opacity, h.color && p.diffuse.value.copy(h.color), h.emissive && p.emissive.value.copy(h.emissive).multiplyScalar(h.emissiveIntensity), h.map && (p.map.value = h.map, e(h.map, p.mapTransform)), h.alphaMap && (p.alphaMap.value = h.alphaMap, e(h.alphaMap, p.alphaMapTransform)), h.bumpMap && (p.bumpMap.value = h.bumpMap, e(h.bumpMap, p.bumpMapTransform), p.bumpScale.value = h.bumpScale, h.side === ve && (p.bumpScale.value *= -1)), h.normalMap && (p.normalMap.value = h.normalMap, e(h.normalMap, p.normalMapTransform), p.normalScale.value.copy(h.normalScale), h.side === ve && p.normalScale.value.negate()), h.displacementMap && (p.displacementMap.value = h.displacementMap, e(h.displacementMap, p.displacementMapTransform), p.displacementScale.value = h.displacementScale, p.displacementBias.value = h.displacementBias), h.emissiveMap && (p.emissiveMap.value = h.emissiveMap, e(h.emissiveMap, p.emissiveMapTransform)), h.specularMap && (p.specularMap.value = h.specularMap, e(h.specularMap, p.specularMapTransform)), h.alphaTest > 0 && (p.alphaTest.value = h.alphaTest);
    let A = t3.get(h), T = A.envMap, b = A.envMapRotation;
    T && (p.envMap.value = T, qn.copy(b), qn.x *= -1, qn.y *= -1, qn.z *= -1, T.isCubeTexture && T.isRenderTargetTexture === false && (qn.y *= -1, qn.z *= -1), p.envMapRotation.value.setFromMatrix4(dp.makeRotationFromEuler(qn)), p.flipEnvMap.value = T.isCubeTexture && T.isRenderTargetTexture === false ? -1 : 1, p.reflectivity.value = h.reflectivity, p.ior.value = h.ior, p.refractionRatio.value = h.refractionRatio), h.lightMap && (p.lightMap.value = h.lightMap, p.lightMapIntensity.value = h.lightMapIntensity, e(h.lightMap, p.lightMapTransform)), h.aoMap && (p.aoMap.value = h.aoMap, p.aoMapIntensity.value = h.aoMapIntensity, e(h.aoMap, p.aoMapTransform));
  }
  function a(p, h) {
    p.diffuse.value.copy(h.color), p.opacity.value = h.opacity, h.map && (p.map.value = h.map, e(h.map, p.mapTransform));
  }
  function o(p, h) {
    p.dashSize.value = h.dashSize, p.totalSize.value = h.dashSize + h.gapSize, p.scale.value = h.scale;
  }
  function c(p, h, A, T) {
    p.diffuse.value.copy(h.color), p.opacity.value = h.opacity, p.size.value = h.size * A, p.scale.value = T * 0.5, h.map && (p.map.value = h.map, e(h.map, p.uvTransform)), h.alphaMap && (p.alphaMap.value = h.alphaMap, e(h.alphaMap, p.alphaMapTransform)), h.alphaTest > 0 && (p.alphaTest.value = h.alphaTest);
  }
  function l(p, h) {
    p.diffuse.value.copy(h.color), p.opacity.value = h.opacity, p.rotation.value = h.rotation, h.map && (p.map.value = h.map, e(h.map, p.mapTransform)), h.alphaMap && (p.alphaMap.value = h.alphaMap, e(h.alphaMap, p.alphaMapTransform)), h.alphaTest > 0 && (p.alphaTest.value = h.alphaTest);
  }
  function u(p, h) {
    p.specular.value.copy(h.specular), p.shininess.value = Math.max(h.shininess, 1e-4);
  }
  function d(p, h) {
    h.gradientMap && (p.gradientMap.value = h.gradientMap);
  }
  function f(p, h) {
    p.metalness.value = h.metalness, h.metalnessMap && (p.metalnessMap.value = h.metalnessMap, e(h.metalnessMap, p.metalnessMapTransform)), p.roughness.value = h.roughness, h.roughnessMap && (p.roughnessMap.value = h.roughnessMap, e(h.roughnessMap, p.roughnessMapTransform)), h.envMap && (p.envMapIntensity.value = h.envMapIntensity);
  }
  function m(p, h, A) {
    p.ior.value = h.ior, h.sheen > 0 && (p.sheenColor.value.copy(h.sheenColor).multiplyScalar(h.sheen), p.sheenRoughness.value = h.sheenRoughness, h.sheenColorMap && (p.sheenColorMap.value = h.sheenColorMap, e(h.sheenColorMap, p.sheenColorMapTransform)), h.sheenRoughnessMap && (p.sheenRoughnessMap.value = h.sheenRoughnessMap, e(h.sheenRoughnessMap, p.sheenRoughnessMapTransform))), h.clearcoat > 0 && (p.clearcoat.value = h.clearcoat, p.clearcoatRoughness.value = h.clearcoatRoughness, h.clearcoatMap && (p.clearcoatMap.value = h.clearcoatMap, e(h.clearcoatMap, p.clearcoatMapTransform)), h.clearcoatRoughnessMap && (p.clearcoatRoughnessMap.value = h.clearcoatRoughnessMap, e(h.clearcoatRoughnessMap, p.clearcoatRoughnessMapTransform)), h.clearcoatNormalMap && (p.clearcoatNormalMap.value = h.clearcoatNormalMap, e(h.clearcoatNormalMap, p.clearcoatNormalMapTransform), p.clearcoatNormalScale.value.copy(h.clearcoatNormalScale), h.side === ve && p.clearcoatNormalScale.value.negate())), h.dispersion > 0 && (p.dispersion.value = h.dispersion), h.iridescence > 0 && (p.iridescence.value = h.iridescence, p.iridescenceIOR.value = h.iridescenceIOR, p.iridescenceThicknessMinimum.value = h.iridescenceThicknessRange[0], p.iridescenceThicknessMaximum.value = h.iridescenceThicknessRange[1], h.iridescenceMap && (p.iridescenceMap.value = h.iridescenceMap, e(h.iridescenceMap, p.iridescenceMapTransform)), h.iridescenceThicknessMap && (p.iridescenceThicknessMap.value = h.iridescenceThicknessMap, e(h.iridescenceThicknessMap, p.iridescenceThicknessMapTransform))), h.transmission > 0 && (p.transmission.value = h.transmission, p.transmissionSamplerMap.value = A.texture, p.transmissionSamplerSize.value.set(A.width, A.height), h.transmissionMap && (p.transmissionMap.value = h.transmissionMap, e(h.transmissionMap, p.transmissionMapTransform)), p.thickness.value = h.thickness, h.thicknessMap && (p.thicknessMap.value = h.thicknessMap, e(h.thicknessMap, p.thicknessMapTransform)), p.attenuationDistance.value = h.attenuationDistance, p.attenuationColor.value.copy(h.attenuationColor)), h.anisotropy > 0 && (p.anisotropyVector.value.set(h.anisotropy * Math.cos(h.anisotropyRotation), h.anisotropy * Math.sin(h.anisotropyRotation)), h.anisotropyMap && (p.anisotropyMap.value = h.anisotropyMap, e(h.anisotropyMap, p.anisotropyMapTransform))), p.specularIntensity.value = h.specularIntensity, p.specularColor.value.copy(h.specularColor), h.specularColorMap && (p.specularColorMap.value = h.specularColorMap, e(h.specularColorMap, p.specularColorMapTransform)), h.specularIntensityMap && (p.specularIntensityMap.value = h.specularIntensityMap, e(h.specularIntensityMap, p.specularIntensityMapTransform));
  }
  function x(p, h) {
    h.matcap && (p.matcap.value = h.matcap);
  }
  function v(p, h) {
    let A = t3.get(h).light;
    p.referencePosition.value.setFromMatrixPosition(A.matrixWorld), p.nearDistance.value = A.shadow.camera.near, p.farDistance.value = A.shadow.camera.far;
  }
  return { refreshFogUniforms: n, refreshMaterialUniforms: s };
}
function pp(i14, t3, e, n) {
  let s = {}, r = {}, a = [], o = i14.getParameter(i14.MAX_UNIFORM_BUFFER_BINDINGS);
  function c(A, T) {
    let b = T.program;
    n.uniformBlockBinding(A, b);
  }
  function l(A, T) {
    let b = s[A.id];
    b === void 0 && (x(A), b = u(A), s[A.id] = b, A.addEventListener("dispose", p));
    let R = T.program;
    n.updateUBOMapping(A, R);
    let w = t3.render.frame;
    r[A.id] !== w && (f(A), r[A.id] = w);
  }
  function u(A) {
    let T = d();
    A.__bindingPointIndex = T;
    let b = i14.createBuffer(), R = A.__size, w = A.usage;
    return i14.bindBuffer(i14.UNIFORM_BUFFER, b), i14.bufferData(i14.UNIFORM_BUFFER, R, w), i14.bindBuffer(i14.UNIFORM_BUFFER, null), i14.bindBufferBase(i14.UNIFORM_BUFFER, T, b), b;
  }
  function d() {
    for (let A = 0; A < o; A++) if (a.indexOf(A) === -1) return a.push(A), A;
    return console.error("THREE.WebGLRenderer: Maximum number of simultaneously usable uniforms groups reached."), 0;
  }
  function f(A) {
    let T = s[A.id], b = A.uniforms, R = A.__cache;
    i14.bindBuffer(i14.UNIFORM_BUFFER, T);
    for (let w = 0, P = b.length; w < P; w++) {
      let N = Array.isArray(b[w]) ? b[w] : [b[w]];
      for (let M = 0, y = N.length; M < y; M++) {
        let I = N[M];
        if (m(I, w, M, R) === true) {
          let z = I.__offset, H = Array.isArray(I.value) ? I.value : [I.value], X = 0;
          for (let Z = 0; Z < H.length; Z++) {
            let W = H[Z], et = v(W);
            typeof W == "number" || typeof W == "boolean" ? (I.__data[0] = W, i14.bufferSubData(i14.UNIFORM_BUFFER, z + X, I.__data)) : W.isMatrix3 ? (I.__data[0] = W.elements[0], I.__data[1] = W.elements[1], I.__data[2] = W.elements[2], I.__data[3] = 0, I.__data[4] = W.elements[3], I.__data[5] = W.elements[4], I.__data[6] = W.elements[5], I.__data[7] = 0, I.__data[8] = W.elements[6], I.__data[9] = W.elements[7], I.__data[10] = W.elements[8], I.__data[11] = 0) : (W.toArray(I.__data, X), X += et.storage / Float32Array.BYTES_PER_ELEMENT);
          }
          i14.bufferSubData(i14.UNIFORM_BUFFER, z, I.__data);
        }
      }
    }
    i14.bindBuffer(i14.UNIFORM_BUFFER, null);
  }
  function m(A, T, b, R) {
    let w = A.value, P = T + "_" + b;
    if (R[P] === void 0) return typeof w == "number" || typeof w == "boolean" ? R[P] = w : R[P] = w.clone(), true;
    {
      let N = R[P];
      if (typeof w == "number" || typeof w == "boolean") {
        if (N !== w) return R[P] = w, true;
      } else if (N.equals(w) === false) return N.copy(w), true;
    }
    return false;
  }
  function x(A) {
    let T = A.uniforms, b = 0, R = 16;
    for (let P = 0, N = T.length; P < N; P++) {
      let M = Array.isArray(T[P]) ? T[P] : [T[P]];
      for (let y = 0, I = M.length; y < I; y++) {
        let z = M[y], H = Array.isArray(z.value) ? z.value : [z.value];
        for (let X = 0, Z = H.length; X < Z; X++) {
          let W = H[X], et = v(W), V = b % R, rt = V % et.boundary, ct = V + rt;
          b += rt, ct !== 0 && R - ct < et.storage && (b += R - ct), z.__data = new Float32Array(et.storage / Float32Array.BYTES_PER_ELEMENT), z.__offset = b, b += et.storage;
        }
      }
    }
    let w = b % R;
    return w > 0 && (b += R - w), A.__size = b, A.__cache = {}, this;
  }
  function v(A) {
    let T = { boundary: 0, storage: 0 };
    return typeof A == "number" || typeof A == "boolean" ? (T.boundary = 4, T.storage = 4) : A.isVector2 ? (T.boundary = 8, T.storage = 8) : A.isVector3 || A.isColor ? (T.boundary = 16, T.storage = 12) : A.isVector4 ? (T.boundary = 16, T.storage = 16) : A.isMatrix3 ? (T.boundary = 48, T.storage = 48) : A.isMatrix4 ? (T.boundary = 64, T.storage = 64) : A.isTexture ? console.warn("THREE.WebGLRenderer: Texture samplers can not be part of an uniforms group.") : console.warn("THREE.WebGLRenderer: Unsupported uniform value type.", A), T;
  }
  function p(A) {
    let T = A.target;
    T.removeEventListener("dispose", p);
    let b = a.indexOf(T.__bindingPointIndex);
    a.splice(b, 1), i14.deleteBuffer(s[T.id]), delete s[T.id], delete r[T.id];
  }
  function h() {
    for (let A in s) i14.deleteBuffer(s[A]);
    a = [], s = {}, r = {};
  }
  return { bind: c, update: l, dispose: h };
}
var lo = class {
  constructor(t3 = {}) {
    let { canvas: e = bl(), context: n = null, depth: s = true, stencil: r = false, alpha: a = false, antialias: o = false, premultipliedAlpha: c = true, preserveDrawingBuffer: l = false, powerPreference: u = "default", failIfMajorPerformanceCaveat: d = false, reversedDepthBuffer: f = false } = t3;
    this.isWebGLRenderer = true;
    let m;
    if (n !== null) {
      if (typeof WebGLRenderingContext < "u" && n instanceof WebGLRenderingContext) throw new Error("THREE.WebGLRenderer: WebGL 1 is not supported since r163.");
      m = n.getContextAttributes().alpha;
    } else m = a;
    let x = new Uint32Array(4), v = new Int32Array(4), p = null, h = null, A = [], T = [];
    this.domElement = e, this.debug = { checkShaderErrors: true, onShaderError: null }, this.autoClear = true, this.autoClearColor = true, this.autoClearDepth = true, this.autoClearStencil = true, this.sortObjects = true, this.clippingPlanes = [], this.localClippingEnabled = false, this.toneMapping = un, this.toneMappingExposure = 1, this.transmissionResolutionScale = 1;
    let b = this, R = false;
    this._outputColorSpace = we;
    let w = 0, P = 0, N = null, M = -1, y = null, I = new se(), z = new se(), H = null, X = new Vt(0), Z = 0, W = e.width, et = e.height, V = 1, rt = null, ct = null, St = new se(0, 0, W, et), Ft = new se(0, 0, W, et), Jt = false, jt = new pi(), Wt = false, q = false, $2 = new oe(), dt = new F(), Rt = new se(), Mt = { background: null, fog: null, environment: null, overrideMaterial: null, isScene: true }, zt = false;
    function fe() {
      return N === null ? V : 1;
    }
    let E = n;
    function te(_, L) {
      return e.getContext(_, L);
    }
    try {
      let _ = { alpha: true, depth: s, stencil: r, antialias: o, premultipliedAlpha: c, preserveDrawingBuffer: l, powerPreference: u, failIfMajorPerformanceCaveat: d };
      if ("setAttribute" in e && e.setAttribute("data-engine", `three.js r${"180"}`), e.addEventListener("webglcontextlost", it, false), e.addEventListener("webglcontextrestored", ut, false), e.addEventListener("webglcontextcreationerror", K, false), E === null) {
        let L = "webgl2";
        if (E = te(L, _), E === null) throw te(L) ? new Error("Error creating WebGL context with your selected attributes.") : new Error("Error creating WebGL context.");
      }
    } catch (_) {
      throw console.error("THREE.WebGLRenderer: " + _.message), _;
    }
    let Pt, wt, mt, ee, gt, Ut, ue, ae, S, g, U, G, J, k, yt, nt, _t, xt, j, lt, At, vt, at, Dt;
    function C() {
      Pt = new Pd(E), Pt.init(), vt = new cp(E, Pt), wt = new Ed(E, Pt, t3, vt), mt = new op(E, Pt), wt.reversedDepthBuffer && f && mt.buffers.depth.setReversed(true), ee = new Ud(E), gt = new Zf(), Ut = new lp(E, Pt, mt, gt, wt, vt, ee), ue = new Ad(b), ae = new Id(b), S = new Vc(E), at = new Sd(E, S), g = new Ld(E, S, ee, at), U = new Fd(E, g, S, ee), j = new Nd(E, wt, Ut), nt = new Td(gt), G = new Yf(b, ue, ae, Pt, wt, at, nt), J = new fp(b, gt), k = new $f(), yt = new np(Pt), xt = new Md(b, ue, ae, mt, U, m, c), _t = new rp(b, U, wt), Dt = new pp(E, ee, wt, mt), lt = new bd(E, Pt, ee), At = new Dd(E, Pt, ee), ee.programs = G.programs, b.capabilities = wt, b.extensions = Pt, b.properties = gt, b.renderLists = k, b.shadowMap = _t, b.state = mt, b.info = ee;
    }
    C();
    let tt = new oo(b, E);
    this.xr = tt, this.getContext = function() {
      return E;
    }, this.getContextAttributes = function() {
      return E.getContextAttributes();
    }, this.forceContextLoss = function() {
      let _ = Pt.get("WEBGL_lose_context");
      _ && _.loseContext();
    }, this.forceContextRestore = function() {
      let _ = Pt.get("WEBGL_lose_context");
      _ && _.restoreContext();
    }, this.getPixelRatio = function() {
      return V;
    }, this.setPixelRatio = function(_) {
      _ !== void 0 && (V = _, this.setSize(W, et, false));
    }, this.getSize = function(_) {
      return _.set(W, et);
    }, this.setSize = function(_, L, O = true) {
      if (tt.isPresenting) {
        console.warn("THREE.WebGLRenderer: Can't change size while VR device is presenting.");
        return;
      }
      W = _, et = L, e.width = Math.floor(_ * V), e.height = Math.floor(L * V), O === true && (e.style.width = _ + "px", e.style.height = L + "px"), this.setViewport(0, 0, _, L);
    }, this.getDrawingBufferSize = function(_) {
      return _.set(W * V, et * V).floor();
    }, this.setDrawingBufferSize = function(_, L, O) {
      W = _, et = L, V = O, e.width = Math.floor(_ * O), e.height = Math.floor(L * O), this.setViewport(0, 0, _, L);
    }, this.getCurrentViewport = function(_) {
      return _.copy(I);
    }, this.getViewport = function(_) {
      return _.copy(St);
    }, this.setViewport = function(_, L, O, B) {
      _.isVector4 ? St.set(_.x, _.y, _.z, _.w) : St.set(_, L, O, B), mt.viewport(I.copy(St).multiplyScalar(V).round());
    }, this.getScissor = function(_) {
      return _.copy(Ft);
    }, this.setScissor = function(_, L, O, B) {
      _.isVector4 ? Ft.set(_.x, _.y, _.z, _.w) : Ft.set(_, L, O, B), mt.scissor(z.copy(Ft).multiplyScalar(V).round());
    }, this.getScissorTest = function() {
      return Jt;
    }, this.setScissorTest = function(_) {
      mt.setScissorTest(Jt = _);
    }, this.setOpaqueSort = function(_) {
      rt = _;
    }, this.setTransparentSort = function(_) {
      ct = _;
    }, this.getClearColor = function(_) {
      return _.copy(xt.getClearColor());
    }, this.setClearColor = function() {
      xt.setClearColor(...arguments);
    }, this.getClearAlpha = function() {
      return xt.getClearAlpha();
    }, this.setClearAlpha = function() {
      xt.setClearAlpha(...arguments);
    }, this.clear = function(_ = true, L = true, O = true) {
      let B = 0;
      if (_) {
        let D = false;
        if (N !== null) {
          let Q = N.texture.format;
          D = Q === hr || Q === cr || Q === lr;
        }
        if (D) {
          let Q = N.texture.type, ot = Q === We || Q === Cn || Q === gi || Q === xi || Q === ar || Q === or, ft = xt.getClearColor(), ht = xt.getClearAlpha(), Tt = ft.r, Ct = ft.g, bt = ft.b;
          ot ? (x[0] = Tt, x[1] = Ct, x[2] = bt, x[3] = ht, E.clearBufferuiv(E.COLOR, 0, x)) : (v[0] = Tt, v[1] = Ct, v[2] = bt, v[3] = ht, E.clearBufferiv(E.COLOR, 0, v));
        } else B |= E.COLOR_BUFFER_BIT;
      }
      L && (B |= E.DEPTH_BUFFER_BIT), O && (B |= E.STENCIL_BUFFER_BIT, this.state.buffers.stencil.setMask(4294967295)), E.clear(B);
    }, this.clearColor = function() {
      this.clear(true, false, false);
    }, this.clearDepth = function() {
      this.clear(false, true, false);
    }, this.clearStencil = function() {
      this.clear(false, false, true);
    }, this.dispose = function() {
      e.removeEventListener("webglcontextlost", it, false), e.removeEventListener("webglcontextrestored", ut, false), e.removeEventListener("webglcontextcreationerror", K, false), xt.dispose(), k.dispose(), yt.dispose(), gt.dispose(), ue.dispose(), ae.dispose(), U.dispose(), at.dispose(), Dt.dispose(), G.dispose(), tt.dispose(), tt.removeEventListener("sessionstart", Xe), tt.removeEventListener("sessionend", ho), Rn.stop();
    };
    function it(_) {
      _.preventDefault(), console.log("THREE.WebGLRenderer: Context Lost."), R = true;
    }
    function ut() {
      console.log("THREE.WebGLRenderer: Context Restored."), R = false;
      let _ = ee.autoReset, L = _t.enabled, O = _t.autoUpdate, B = _t.needsUpdate, D = _t.type;
      C(), ee.autoReset = _, _t.enabled = L, _t.autoUpdate = O, _t.needsUpdate = B, _t.type = D;
    }
    function K(_) {
      console.error("THREE.WebGLRenderer: A WebGL context could not be created. Reason: ", _.statusMessage);
    }
    function Y(_) {
      let L = _.target;
      L.removeEventListener("dispose", Y), pt(L);
    }
    function pt(_) {
      It(_), gt.remove(_);
    }
    function It(_) {
      let L = gt.get(_).programs;
      L !== void 0 && (L.forEach(function(O) {
        G.releaseProgram(O);
      }), _.isShaderMaterial && G.releaseShaderCache(_));
    }
    this.renderBufferDirect = function(_, L, O, B, D, Q) {
      L === null && (L = Mt);
      let ot = D.isMesh && D.matrixWorld.determinant() < 0, ft = nc(_, L, O, B, D);
      mt.setMaterial(B, ot);
      let ht = O.index, Tt = 1;
      if (B.wireframe === true) {
        if (ht = g.getWireframeAttribute(O), ht === void 0) return;
        Tt = 2;
      }
      let Ct = O.drawRange, bt = O.attributes.position, Ot = Ct.start * Tt, Yt = (Ct.start + Ct.count) * Tt;
      Q !== null && (Ot = Math.max(Ot, Q.start * Tt), Yt = Math.min(Yt, (Q.start + Q.count) * Tt)), ht !== null ? (Ot = Math.max(Ot, 0), Yt = Math.min(Yt, ht.count)) : bt != null && (Ot = Math.max(Ot, 0), Yt = Math.min(Yt, bt.count));
      let re = Yt - Ot;
      if (re < 0 || re === 1 / 0) return;
      at.setup(D, B, ft, O, ht);
      let Kt, Zt = lt;
      if (ht !== null && (Kt = S.get(ht), Zt = At, Zt.setIndex(Kt)), D.isMesh) B.wireframe === true ? (mt.setLineWidth(B.wireframeLinewidth * fe()), Zt.setMode(E.LINES)) : Zt.setMode(E.TRIANGLES);
      else if (D.isLine) {
        let Et = B.linewidth;
        Et === void 0 && (Et = 1), mt.setLineWidth(Et * fe()), D.isLineSegments ? Zt.setMode(E.LINES) : D.isLineLoop ? Zt.setMode(E.LINE_LOOP) : Zt.setMode(E.LINE_STRIP);
      } else D.isPoints ? Zt.setMode(E.POINTS) : D.isSprite && Zt.setMode(E.TRIANGLES);
      if (D.isBatchedMesh) if (D._multiDrawInstances !== null) hi("THREE.WebGLRenderer: renderMultiDrawInstances has been deprecated and will be removed in r184. Append to renderMultiDraw arguments and use indirection."), Zt.renderMultiDrawInstances(D._multiDrawStarts, D._multiDrawCounts, D._multiDrawCount, D._multiDrawInstances);
      else if (Pt.get("WEBGL_multi_draw")) Zt.renderMultiDraw(D._multiDrawStarts, D._multiDrawCounts, D._multiDrawCount);
      else {
        let Et = D._multiDrawStarts, ne = D._multiDrawCounts, Ht = D._multiDrawCount, be = ht ? S.get(ht).bytesPerElement : 1, Jn = gt.get(B).currentProgram.getUniforms();
        for (let Ee = 0; Ee < Ht; Ee++) Jn.setValue(E, "_gl_DrawID", Ee), Zt.render(Et[Ee] / be, ne[Ee]);
      }
      else if (D.isInstancedMesh) Zt.renderInstances(Ot, re, D.count);
      else if (O.isInstancedBufferGeometry) {
        let Et = O._maxInstanceCount !== void 0 ? O._maxInstanceCount : 1 / 0, ne = Math.min(O.instanceCount, Et);
        Zt.renderInstances(Ot, re, ne);
      } else Zt.render(Ot, re);
    };
    function $t(_, L, O) {
      _.transparent === true && _.side === $e && _.forceSinglePass === false ? (_.side = ve, _.needsUpdate = true, es(_, L, O), _.side = on, _.needsUpdate = true, es(_, L, O), _.side = $e) : es(_, L, O);
    }
    this.compile = function(_, L, O = null) {
      O === null && (O = _), h = yt.get(O), h.init(L), T.push(h), O.traverseVisible(function(D) {
        D.isLight && D.layers.test(L.layers) && (h.pushLight(D), D.castShadow && h.pushShadow(D));
      }), _ !== O && _.traverseVisible(function(D) {
        D.isLight && D.layers.test(L.layers) && (h.pushLight(D), D.castShadow && h.pushShadow(D));
      }), h.setupLights();
      let B = /* @__PURE__ */ new Set();
      return _.traverse(function(D) {
        if (!(D.isMesh || D.isPoints || D.isLine || D.isSprite)) return;
        let Q = D.material;
        if (Q) if (Array.isArray(Q)) for (let ot = 0; ot < Q.length; ot++) {
          let ft = Q[ot];
          $t(ft, O, D), B.add(ft);
        }
        else $t(Q, O, D), B.add(Q);
      }), h = T.pop(), B;
    }, this.compileAsync = function(_, L, O = null) {
      let B = this.compile(_, L, O);
      return new Promise((D) => {
        function Q() {
          if (B.forEach(function(ot) {
            gt.get(ot).currentProgram.isReady() && B.delete(ot);
          }), B.size === 0) {
            D(_);
            return;
          }
          setTimeout(Q, 10);
        }
        Pt.get("KHR_parallel_shader_compile") !== null ? Q() : setTimeout(Q, 10);
      });
    };
    let Xt = null;
    function je(_) {
      Xt && Xt(_);
    }
    function Xe() {
      Rn.stop();
    }
    function ho() {
      Rn.start();
    }
    let Rn = new Kl();
    Rn.setAnimationLoop(je), typeof self < "u" && Rn.setContext(self), this.setAnimationLoop = function(_) {
      Xt = _, tt.setAnimationLoop(_), _ === null ? Rn.stop() : Rn.start();
    }, tt.addEventListener("sessionstart", Xe), tt.addEventListener("sessionend", ho), this.render = function(_, L) {
      if (L !== void 0 && L.isCamera !== true) {
        console.error("THREE.WebGLRenderer.render: camera is not an instance of THREE.Camera.");
        return;
      }
      if (R === true) return;
      if (_.matrixWorldAutoUpdate === true && _.updateMatrixWorld(), L.parent === null && L.matrixWorldAutoUpdate === true && L.updateMatrixWorld(), tt.enabled === true && tt.isPresenting === true && (tt.cameraAutoUpdate === true && tt.updateCamera(L), L = tt.getCamera()), _.isScene === true && _.onBeforeRender(b, _, L, N), h = yt.get(_, T.length), h.init(L), T.push(h), $2.multiplyMatrices(L.projectionMatrix, L.matrixWorldInverse), jt.setFromProjectionMatrix($2, Ve, L.reversedDepth), q = this.localClippingEnabled, Wt = nt.init(this.clippingPlanes, q), p = k.get(_, A.length), p.init(), A.push(p), tt.enabled === true && tt.isPresenting === true) {
        let Q = b.xr.getDepthSensingMesh();
        Q !== null && Wr(Q, L, -1 / 0, b.sortObjects);
      }
      Wr(_, L, 0, b.sortObjects), p.finish(), b.sortObjects === true && p.sort(rt, ct), zt = tt.enabled === false || tt.isPresenting === false || tt.hasDepthSensing() === false, zt && xt.addToRenderList(p, _), this.info.render.frame++, Wt === true && nt.beginShadows();
      let O = h.state.shadowsArray;
      _t.render(O, _, L), Wt === true && nt.endShadows(), this.info.autoReset === true && this.info.reset();
      let B = p.opaque, D = p.transmissive;
      if (h.setupLights(), L.isArrayCamera) {
        let Q = L.cameras;
        if (D.length > 0) for (let ot = 0, ft = Q.length; ot < ft; ot++) {
          let ht = Q[ot];
          fo(B, D, _, ht);
        }
        zt && xt.render(_);
        for (let ot = 0, ft = Q.length; ot < ft; ot++) {
          let ht = Q[ot];
          uo(p, _, ht, ht.viewport);
        }
      } else D.length > 0 && fo(B, D, _, L), zt && xt.render(_), uo(p, _, L);
      N !== null && P === 0 && (Ut.updateMultisampleRenderTarget(N), Ut.updateRenderTargetMipmap(N)), _.isScene === true && _.onAfterRender(b, _, L), at.resetDefaultState(), M = -1, y = null, T.pop(), T.length > 0 ? (h = T[T.length - 1], Wt === true && nt.setGlobalState(b.clippingPlanes, h.state.camera)) : h = null, A.pop(), A.length > 0 ? p = A[A.length - 1] : p = null;
    };
    function Wr(_, L, O, B) {
      if (_.visible === false) return;
      if (_.layers.test(L.layers)) {
        if (_.isGroup) O = _.renderOrder;
        else if (_.isLOD) _.autoUpdate === true && _.update(L);
        else if (_.isLight) h.pushLight(_), _.castShadow && h.pushShadow(_);
        else if (_.isSprite) {
          if (!_.frustumCulled || jt.intersectsSprite(_)) {
            B && Rt.setFromMatrixPosition(_.matrixWorld).applyMatrix4($2);
            let ot = U.update(_), ft = _.material;
            ft.visible && p.push(_, ot, ft, O, Rt.z, null);
          }
        } else if ((_.isMesh || _.isLine || _.isPoints) && (!_.frustumCulled || jt.intersectsObject(_))) {
          let ot = U.update(_), ft = _.material;
          if (B && (_.boundingSphere !== void 0 ? (_.boundingSphere === null && _.computeBoundingSphere(), Rt.copy(_.boundingSphere.center)) : (ot.boundingSphere === null && ot.computeBoundingSphere(), Rt.copy(ot.boundingSphere.center)), Rt.applyMatrix4(_.matrixWorld).applyMatrix4($2)), Array.isArray(ft)) {
            let ht = ot.groups;
            for (let Tt = 0, Ct = ht.length; Tt < Ct; Tt++) {
              let bt = ht[Tt], Ot = ft[bt.materialIndex];
              Ot && Ot.visible && p.push(_, ot, Ot, O, Rt.z, bt);
            }
          } else ft.visible && p.push(_, ot, ft, O, Rt.z, null);
        }
      }
      let Q = _.children;
      for (let ot = 0, ft = Q.length; ot < ft; ot++) Wr(Q[ot], L, O, B);
    }
    function uo(_, L, O, B) {
      let D = _.opaque, Q = _.transmissive, ot = _.transparent;
      h.setupLightsView(O), Wt === true && nt.setGlobalState(b.clippingPlanes, O), B && mt.viewport(I.copy(B)), D.length > 0 && ts(D, L, O), Q.length > 0 && ts(Q, L, O), ot.length > 0 && ts(ot, L, O), mt.buffers.depth.setTest(true), mt.buffers.depth.setMask(true), mt.buffers.color.setMask(true), mt.setPolygonOffset(false);
    }
    function fo(_, L, O, B) {
      if ((O.isScene === true ? O.overrideMaterial : null) !== null) return;
      h.state.transmissionRenderTarget[B.id] === void 0 && (h.state.transmissionRenderTarget[B.id] = new Ze(1, 1, { generateMipmaps: true, type: Pt.has("EXT_color_buffer_half_float") || Pt.has("EXT_color_buffer_float") ? _i : We, minFilter: wn, samples: 4, stencilBuffer: r, resolveDepthBuffer: false, resolveStencilBuffer: false, colorSpace: kt.workingColorSpace }));
      let Q = h.state.transmissionRenderTarget[B.id], ot = B.viewport || I;
      Q.setSize(ot.z * b.transmissionResolutionScale, ot.w * b.transmissionResolutionScale);
      let ft = b.getRenderTarget(), ht = b.getActiveCubeFace(), Tt = b.getActiveMipmapLevel();
      b.setRenderTarget(Q), b.getClearColor(X), Z = b.getClearAlpha(), Z < 1 && b.setClearColor(16777215, 0.5), b.clear(), zt && xt.render(O);
      let Ct = b.toneMapping;
      b.toneMapping = un;
      let bt = B.viewport;
      if (B.viewport !== void 0 && (B.viewport = void 0), h.setupLightsView(B), Wt === true && nt.setGlobalState(b.clippingPlanes, B), ts(_, O, B), Ut.updateMultisampleRenderTarget(Q), Ut.updateRenderTargetMipmap(Q), Pt.has("WEBGL_multisampled_render_to_texture") === false) {
        let Ot = false;
        for (let Yt = 0, re = L.length; Yt < re; Yt++) {
          let Kt = L[Yt], Zt = Kt.object, Et = Kt.geometry, ne = Kt.material, Ht = Kt.group;
          if (ne.side === $e && Zt.layers.test(B.layers)) {
            let be = ne.side;
            ne.side = ve, ne.needsUpdate = true, po(Zt, O, B, Et, ne, Ht), ne.side = be, ne.needsUpdate = true, Ot = true;
          }
        }
        Ot === true && (Ut.updateMultisampleRenderTarget(Q), Ut.updateRenderTargetMipmap(Q));
      }
      b.setRenderTarget(ft, ht, Tt), b.setClearColor(X, Z), bt !== void 0 && (B.viewport = bt), b.toneMapping = Ct;
    }
    function ts(_, L, O) {
      let B = L.isScene === true ? L.overrideMaterial : null;
      for (let D = 0, Q = _.length; D < Q; D++) {
        let ot = _[D], ft = ot.object, ht = ot.geometry, Tt = ot.group, Ct = ot.material;
        Ct.allowOverride === true && B !== null && (Ct = B), ft.layers.test(O.layers) && po(ft, L, O, ht, Ct, Tt);
      }
    }
    function po(_, L, O, B, D, Q) {
      _.onBeforeRender(b, L, O, B, D, Q), _.modelViewMatrix.multiplyMatrices(O.matrixWorldInverse, _.matrixWorld), _.normalMatrix.getNormalMatrix(_.modelViewMatrix), D.onBeforeRender(b, L, O, B, _, Q), D.transparent === true && D.side === $e && D.forceSinglePass === false ? (D.side = ve, D.needsUpdate = true, b.renderBufferDirect(O, L, B, D, _, Q), D.side = on, D.needsUpdate = true, b.renderBufferDirect(O, L, B, D, _, Q), D.side = $e) : b.renderBufferDirect(O, L, B, D, _, Q), _.onAfterRender(b, L, O, B, D, Q);
    }
    function es(_, L, O) {
      L.isScene !== true && (L = Mt);
      let B = gt.get(_), D = h.state.lights, Q = h.state.shadowsArray, ot = D.state.version, ft = G.getParameters(_, D.state, Q, L, O), ht = G.getProgramCacheKey(ft), Tt = B.programs;
      B.environment = _.isMeshStandardMaterial ? L.environment : null, B.fog = L.fog, B.envMap = (_.isMeshStandardMaterial ? ae : ue).get(_.envMap || B.environment), B.envMapRotation = B.environment !== null && _.envMap === null ? L.environmentRotation : _.envMapRotation, Tt === void 0 && (_.addEventListener("dispose", Y), Tt = /* @__PURE__ */ new Map(), B.programs = Tt);
      let Ct = Tt.get(ht);
      if (Ct !== void 0) {
        if (B.currentProgram === Ct && B.lightsStateVersion === ot) return go(_, ft), Ct;
      } else ft.uniforms = G.getUniforms(_), _.onBeforeCompile(ft, b), Ct = G.acquireProgram(ft, ht), Tt.set(ht, Ct), B.uniforms = ft.uniforms;
      let bt = B.uniforms;
      return (!_.isShaderMaterial && !_.isRawShaderMaterial || _.clipping === true) && (bt.clippingPlanes = nt.uniform), go(_, ft), B.needsLights = sc(_), B.lightsStateVersion = ot, B.needsLights && (bt.ambientLightColor.value = D.state.ambient, bt.lightProbe.value = D.state.probe, bt.directionalLights.value = D.state.directional, bt.directionalLightShadows.value = D.state.directionalShadow, bt.spotLights.value = D.state.spot, bt.spotLightShadows.value = D.state.spotShadow, bt.rectAreaLights.value = D.state.rectArea, bt.ltc_1.value = D.state.rectAreaLTC1, bt.ltc_2.value = D.state.rectAreaLTC2, bt.pointLights.value = D.state.point, bt.pointLightShadows.value = D.state.pointShadow, bt.hemisphereLights.value = D.state.hemi, bt.directionalShadowMap.value = D.state.directionalShadowMap, bt.directionalShadowMatrix.value = D.state.directionalShadowMatrix, bt.spotShadowMap.value = D.state.spotShadowMap, bt.spotLightMatrix.value = D.state.spotLightMatrix, bt.spotLightMap.value = D.state.spotLightMap, bt.pointShadowMap.value = D.state.pointShadowMap, bt.pointShadowMatrix.value = D.state.pointShadowMatrix), B.currentProgram = Ct, B.uniformsList = null, Ct;
    }
    function mo(_) {
      if (_.uniformsList === null) {
        let L = _.currentProgram.getUniforms();
        _.uniformsList = Si.seqWithValue(L.seq, _.uniforms);
      }
      return _.uniformsList;
    }
    function go(_, L) {
      let O = gt.get(_);
      O.outputColorSpace = L.outputColorSpace, O.batching = L.batching, O.batchingColor = L.batchingColor, O.instancing = L.instancing, O.instancingColor = L.instancingColor, O.instancingMorph = L.instancingMorph, O.skinning = L.skinning, O.morphTargets = L.morphTargets, O.morphNormals = L.morphNormals, O.morphColors = L.morphColors, O.morphTargetsCount = L.morphTargetsCount, O.numClippingPlanes = L.numClippingPlanes, O.numIntersection = L.numClipIntersection, O.vertexAlphas = L.vertexAlphas, O.vertexTangents = L.vertexTangents, O.toneMapping = L.toneMapping;
    }
    function nc(_, L, O, B, D) {
      L.isScene !== true && (L = Mt), Ut.resetTextureUnits();
      let Q = L.fog, ot = B.isMeshStandardMaterial ? L.environment : null, ft = N === null ? b.outputColorSpace : N.isXRRenderTarget === true ? N.texture.colorSpace : zn, ht = (B.isMeshStandardMaterial ? ae : ue).get(B.envMap || ot), Tt = B.vertexColors === true && !!O.attributes.color && O.attributes.color.itemSize === 4, Ct = !!O.attributes.tangent && (!!B.normalMap || B.anisotropy > 0), bt = !!O.morphAttributes.position, Ot = !!O.morphAttributes.normal, Yt = !!O.morphAttributes.color, re = un;
      B.toneMapped && (N === null || N.isXRRenderTarget === true) && (re = b.toneMapping);
      let Kt = O.morphAttributes.position || O.morphAttributes.normal || O.morphAttributes.color, Zt = Kt !== void 0 ? Kt.length : 0, Et = gt.get(B), ne = h.state.lights;
      if (Wt === true && (q === true || _ !== y)) {
        let _e = _ === y && B.id === M;
        nt.setState(B, _, _e);
      }
      let Ht = false;
      B.version === Et.__version ? (Et.needsLights && Et.lightsStateVersion !== ne.state.version || Et.outputColorSpace !== ft || D.isBatchedMesh && Et.batching === false || !D.isBatchedMesh && Et.batching === true || D.isBatchedMesh && Et.batchingColor === true && D.colorTexture === null || D.isBatchedMesh && Et.batchingColor === false && D.colorTexture !== null || D.isInstancedMesh && Et.instancing === false || !D.isInstancedMesh && Et.instancing === true || D.isSkinnedMesh && Et.skinning === false || !D.isSkinnedMesh && Et.skinning === true || D.isInstancedMesh && Et.instancingColor === true && D.instanceColor === null || D.isInstancedMesh && Et.instancingColor === false && D.instanceColor !== null || D.isInstancedMesh && Et.instancingMorph === true && D.morphTexture === null || D.isInstancedMesh && Et.instancingMorph === false && D.morphTexture !== null || Et.envMap !== ht || B.fog === true && Et.fog !== Q || Et.numClippingPlanes !== void 0 && (Et.numClippingPlanes !== nt.numPlanes || Et.numIntersection !== nt.numIntersection) || Et.vertexAlphas !== Tt || Et.vertexTangents !== Ct || Et.morphTargets !== bt || Et.morphNormals !== Ot || Et.morphColors !== Yt || Et.toneMapping !== re || Et.morphTargetsCount !== Zt) && (Ht = true) : (Ht = true, Et.__version = B.version);
      let be = Et.currentProgram;
      Ht === true && (be = es(B, L, D));
      let Jn = false, Ee = false, Ei = false, ie = be.getUniforms(), Le = Et.uniforms;
      if (mt.useProgram(be.program) && (Jn = true, Ee = true, Ei = true), B.id !== M && (M = B.id, Ee = true), Jn || y !== _) {
        mt.buffers.depth.getReversed() && _.reversedDepth !== true && (_._reversedDepth = true, _.updateProjectionMatrix()), ie.setValue(E, "projectionMatrix", _.projectionMatrix), ie.setValue(E, "viewMatrix", _.matrixWorldInverse);
        let ye = ie.map.cameraPosition;
        ye !== void 0 && ye.setValue(E, dt.setFromMatrixPosition(_.matrixWorld)), wt.logarithmicDepthBuffer && ie.setValue(E, "logDepthBufFC", 2 / (Math.log(_.far + 1) / Math.LN2)), (B.isMeshPhongMaterial || B.isMeshToonMaterial || B.isMeshLambertMaterial || B.isMeshBasicMaterial || B.isMeshStandardMaterial || B.isShaderMaterial) && ie.setValue(E, "isOrthographic", _.isOrthographicCamera === true), y !== _ && (y = _, Ee = true, Ei = true);
      }
      if (D.isSkinnedMesh) {
        ie.setOptional(E, D, "bindMatrix"), ie.setOptional(E, D, "bindMatrixInverse");
        let _e = D.skeleton;
        _e && (_e.boneTexture === null && _e.computeBoneTexture(), ie.setValue(E, "boneTexture", _e.boneTexture, Ut));
      }
      D.isBatchedMesh && (ie.setOptional(E, D, "batchingTexture"), ie.setValue(E, "batchingTexture", D._matricesTexture, Ut), ie.setOptional(E, D, "batchingIdTexture"), ie.setValue(E, "batchingIdTexture", D._indirectTexture, Ut), ie.setOptional(E, D, "batchingColorTexture"), D._colorsTexture !== null && ie.setValue(E, "batchingColorTexture", D._colorsTexture, Ut));
      let De = O.morphAttributes;
      if ((De.position !== void 0 || De.normal !== void 0 || De.color !== void 0) && j.update(D, O, be), (Ee || Et.receiveShadow !== D.receiveShadow) && (Et.receiveShadow = D.receiveShadow, ie.setValue(E, "receiveShadow", D.receiveShadow)), B.isMeshGouraudMaterial && B.envMap !== null && (Le.envMap.value = ht, Le.flipEnvMap.value = ht.isCubeTexture && ht.isRenderTargetTexture === false ? -1 : 1), B.isMeshStandardMaterial && B.envMap === null && L.environment !== null && (Le.envMapIntensity.value = L.environmentIntensity), Ee && (ie.setValue(E, "toneMappingExposure", b.toneMappingExposure), Et.needsLights && ic(Le, Ei), Q && B.fog === true && J.refreshFogUniforms(Le, Q), J.refreshMaterialUniforms(Le, B, V, et, h.state.transmissionRenderTarget[_.id]), Si.upload(E, mo(Et), Le, Ut)), B.isShaderMaterial && B.uniformsNeedUpdate === true && (Si.upload(E, mo(Et), Le, Ut), B.uniformsNeedUpdate = false), B.isSpriteMaterial && ie.setValue(E, "center", D.center), ie.setValue(E, "modelViewMatrix", D.modelViewMatrix), ie.setValue(E, "normalMatrix", D.normalMatrix), ie.setValue(E, "modelMatrix", D.matrixWorld), B.isShaderMaterial || B.isRawShaderMaterial) {
        let _e = B.uniformsGroups;
        for (let ye = 0, Xr = _e.length; ye < Xr; ye++) {
          let In = _e[ye];
          Dt.update(In, be), Dt.bind(In, be);
        }
      }
      return be;
    }
    function ic(_, L) {
      _.ambientLightColor.needsUpdate = L, _.lightProbe.needsUpdate = L, _.directionalLights.needsUpdate = L, _.directionalLightShadows.needsUpdate = L, _.pointLights.needsUpdate = L, _.pointLightShadows.needsUpdate = L, _.spotLights.needsUpdate = L, _.spotLightShadows.needsUpdate = L, _.rectAreaLights.needsUpdate = L, _.hemisphereLights.needsUpdate = L;
    }
    function sc(_) {
      return _.isMeshLambertMaterial || _.isMeshToonMaterial || _.isMeshPhongMaterial || _.isMeshStandardMaterial || _.isShadowMaterial || _.isShaderMaterial && _.lights === true;
    }
    this.getActiveCubeFace = function() {
      return w;
    }, this.getActiveMipmapLevel = function() {
      return P;
    }, this.getRenderTarget = function() {
      return N;
    }, this.setRenderTargetTextures = function(_, L, O) {
      let B = gt.get(_);
      B.__autoAllocateDepthBuffer = _.resolveDepthBuffer === false, B.__autoAllocateDepthBuffer === false && (B.__useRenderToTexture = false), gt.get(_.texture).__webglTexture = L, gt.get(_.depthTexture).__webglTexture = B.__autoAllocateDepthBuffer ? void 0 : O, B.__hasExternalTextures = true;
    }, this.setRenderTargetFramebuffer = function(_, L) {
      let O = gt.get(_);
      O.__webglFramebuffer = L, O.__useDefaultFramebuffer = L === void 0;
    };
    let rc = E.createFramebuffer();
    this.setRenderTarget = function(_, L = 0, O = 0) {
      N = _, w = L, P = O;
      let B = true, D = null, Q = false, ot = false;
      if (_) {
        let ht = gt.get(_);
        if (ht.__useDefaultFramebuffer !== void 0) mt.bindFramebuffer(E.FRAMEBUFFER, null), B = false;
        else if (ht.__webglFramebuffer === void 0) Ut.setupRenderTarget(_);
        else if (ht.__hasExternalTextures) Ut.rebindTextures(_, gt.get(_.texture).__webglTexture, gt.get(_.depthTexture).__webglTexture);
        else if (_.depthBuffer) {
          let bt = _.depthTexture;
          if (ht.__boundDepthTexture !== bt) {
            if (bt !== null && gt.has(bt) && (_.width !== bt.image.width || _.height !== bt.image.height)) throw new Error("WebGLRenderTarget: Attached DepthTexture is initialized to the incorrect size.");
            Ut.setupDepthRenderbuffer(_);
          }
        }
        let Tt = _.texture;
        (Tt.isData3DTexture || Tt.isDataArrayTexture || Tt.isCompressedArrayTexture) && (ot = true);
        let Ct = gt.get(_).__webglFramebuffer;
        _.isWebGLCubeRenderTarget ? (Array.isArray(Ct[L]) ? D = Ct[L][O] : D = Ct[L], Q = true) : _.samples > 0 && Ut.useMultisampledRTT(_) === false ? D = gt.get(_).__webglMultisampledFramebuffer : Array.isArray(Ct) ? D = Ct[O] : D = Ct, I.copy(_.viewport), z.copy(_.scissor), H = _.scissorTest;
      } else I.copy(St).multiplyScalar(V).floor(), z.copy(Ft).multiplyScalar(V).floor(), H = Jt;
      if (O !== 0 && (D = rc), mt.bindFramebuffer(E.FRAMEBUFFER, D) && B && mt.drawBuffers(_, D), mt.viewport(I), mt.scissor(z), mt.setScissorTest(H), Q) {
        let ht = gt.get(_.texture);
        E.framebufferTexture2D(E.FRAMEBUFFER, E.COLOR_ATTACHMENT0, E.TEXTURE_CUBE_MAP_POSITIVE_X + L, ht.__webglTexture, O);
      } else if (ot) {
        let ht = L;
        for (let Tt = 0; Tt < _.textures.length; Tt++) {
          let Ct = gt.get(_.textures[Tt]);
          E.framebufferTextureLayer(E.FRAMEBUFFER, E.COLOR_ATTACHMENT0 + Tt, Ct.__webglTexture, O, ht);
        }
      } else if (_ !== null && O !== 0) {
        let ht = gt.get(_.texture);
        E.framebufferTexture2D(E.FRAMEBUFFER, E.COLOR_ATTACHMENT0, E.TEXTURE_2D, ht.__webglTexture, O);
      }
      M = -1;
    }, this.readRenderTargetPixels = function(_, L, O, B, D, Q, ot, ft = 0) {
      if (!(_ && _.isWebGLRenderTarget)) {
        console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");
        return;
      }
      let ht = gt.get(_).__webglFramebuffer;
      if (_.isWebGLCubeRenderTarget && ot !== void 0 && (ht = ht[ot]), ht) {
        mt.bindFramebuffer(E.FRAMEBUFFER, ht);
        try {
          let Tt = _.textures[ft], Ct = Tt.format, bt = Tt.type;
          if (!wt.textureFormatReadable(Ct)) {
            console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not in RGBA or implementation defined format.");
            return;
          }
          if (!wt.textureTypeReadable(bt)) {
            console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not in UnsignedByteType or implementation defined type.");
            return;
          }
          L >= 0 && L <= _.width - B && O >= 0 && O <= _.height - D && (_.textures.length > 1 && E.readBuffer(E.COLOR_ATTACHMENT0 + ft), E.readPixels(L, O, B, D, vt.convert(Ct), vt.convert(bt), Q));
        } finally {
          let Tt = N !== null ? gt.get(N).__webglFramebuffer : null;
          mt.bindFramebuffer(E.FRAMEBUFFER, Tt);
        }
      }
    }, this.readRenderTargetPixelsAsync = async function(_, L, O, B, D, Q, ot, ft = 0) {
      if (!(_ && _.isWebGLRenderTarget)) throw new Error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");
      let ht = gt.get(_).__webglFramebuffer;
      if (_.isWebGLCubeRenderTarget && ot !== void 0 && (ht = ht[ot]), ht) if (L >= 0 && L <= _.width - B && O >= 0 && O <= _.height - D) {
        mt.bindFramebuffer(E.FRAMEBUFFER, ht);
        let Tt = _.textures[ft], Ct = Tt.format, bt = Tt.type;
        if (!wt.textureFormatReadable(Ct)) throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in RGBA or implementation defined format.");
        if (!wt.textureTypeReadable(bt)) throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in UnsignedByteType or implementation defined type.");
        let Ot = E.createBuffer();
        E.bindBuffer(E.PIXEL_PACK_BUFFER, Ot), E.bufferData(E.PIXEL_PACK_BUFFER, Q.byteLength, E.STREAM_READ), _.textures.length > 1 && E.readBuffer(E.COLOR_ATTACHMENT0 + ft), E.readPixels(L, O, B, D, vt.convert(Ct), vt.convert(bt), 0);
        let Yt = N !== null ? gt.get(N).__webglFramebuffer : null;
        mt.bindFramebuffer(E.FRAMEBUFFER, Yt);
        let re = E.fenceSync(E.SYNC_GPU_COMMANDS_COMPLETE, 0);
        return E.flush(), await El(E, re, 4), E.bindBuffer(E.PIXEL_PACK_BUFFER, Ot), E.getBufferSubData(E.PIXEL_PACK_BUFFER, 0, Q), E.deleteBuffer(Ot), E.deleteSync(re), Q;
      } else throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: requested read bounds are out of range.");
    }, this.copyFramebufferToTexture = function(_, L = null, O = 0) {
      let B = Math.pow(2, -O), D = Math.floor(_.image.width * B), Q = Math.floor(_.image.height * B), ot = L !== null ? L.x : 0, ft = L !== null ? L.y : 0;
      Ut.setTexture2D(_, 0), E.copyTexSubImage2D(E.TEXTURE_2D, O, 0, 0, ot, ft, D, Q), mt.unbindTexture();
    };
    let ac = E.createFramebuffer(), oc = E.createFramebuffer();
    this.copyTextureToTexture = function(_, L, O = null, B = null, D = 0, Q = null) {
      Q === null && (D !== 0 ? (hi("WebGLRenderer: copyTextureToTexture function signature has changed to support src and dst mipmap levels."), Q = D, D = 0) : Q = 0);
      let ot, ft, ht, Tt, Ct, bt, Ot, Yt, re, Kt = _.isCompressedTexture ? _.mipmaps[Q] : _.image;
      if (O !== null) ot = O.max.x - O.min.x, ft = O.max.y - O.min.y, ht = O.isBox3 ? O.max.z - O.min.z : 1, Tt = O.min.x, Ct = O.min.y, bt = O.isBox3 ? O.min.z : 0;
      else {
        let De = Math.pow(2, -D);
        ot = Math.floor(Kt.width * De), ft = Math.floor(Kt.height * De), _.isDataArrayTexture ? ht = Kt.depth : _.isData3DTexture ? ht = Math.floor(Kt.depth * De) : ht = 1, Tt = 0, Ct = 0, bt = 0;
      }
      B !== null ? (Ot = B.x, Yt = B.y, re = B.z) : (Ot = 0, Yt = 0, re = 0);
      let Zt = vt.convert(L.format), Et = vt.convert(L.type), ne;
      L.isData3DTexture ? (Ut.setTexture3D(L, 0), ne = E.TEXTURE_3D) : L.isDataArrayTexture || L.isCompressedArrayTexture ? (Ut.setTexture2DArray(L, 0), ne = E.TEXTURE_2D_ARRAY) : (Ut.setTexture2D(L, 0), ne = E.TEXTURE_2D), E.pixelStorei(E.UNPACK_FLIP_Y_WEBGL, L.flipY), E.pixelStorei(E.UNPACK_PREMULTIPLY_ALPHA_WEBGL, L.premultiplyAlpha), E.pixelStorei(E.UNPACK_ALIGNMENT, L.unpackAlignment);
      let Ht = E.getParameter(E.UNPACK_ROW_LENGTH), be = E.getParameter(E.UNPACK_IMAGE_HEIGHT), Jn = E.getParameter(E.UNPACK_SKIP_PIXELS), Ee = E.getParameter(E.UNPACK_SKIP_ROWS), Ei = E.getParameter(E.UNPACK_SKIP_IMAGES);
      E.pixelStorei(E.UNPACK_ROW_LENGTH, Kt.width), E.pixelStorei(E.UNPACK_IMAGE_HEIGHT, Kt.height), E.pixelStorei(E.UNPACK_SKIP_PIXELS, Tt), E.pixelStorei(E.UNPACK_SKIP_ROWS, Ct), E.pixelStorei(E.UNPACK_SKIP_IMAGES, bt);
      let ie = _.isDataArrayTexture || _.isData3DTexture, Le = L.isDataArrayTexture || L.isData3DTexture;
      if (_.isDepthTexture) {
        let De = gt.get(_), _e = gt.get(L), ye = gt.get(De.__renderTarget), Xr = gt.get(_e.__renderTarget);
        mt.bindFramebuffer(E.READ_FRAMEBUFFER, ye.__webglFramebuffer), mt.bindFramebuffer(E.DRAW_FRAMEBUFFER, Xr.__webglFramebuffer);
        for (let In = 0; In < ht; In++) ie && (E.framebufferTextureLayer(E.READ_FRAMEBUFFER, E.COLOR_ATTACHMENT0, gt.get(_).__webglTexture, D, bt + In), E.framebufferTextureLayer(E.DRAW_FRAMEBUFFER, E.COLOR_ATTACHMENT0, gt.get(L).__webglTexture, Q, re + In)), E.blitFramebuffer(Tt, Ct, ot, ft, Ot, Yt, ot, ft, E.DEPTH_BUFFER_BIT, E.NEAREST);
        mt.bindFramebuffer(E.READ_FRAMEBUFFER, null), mt.bindFramebuffer(E.DRAW_FRAMEBUFFER, null);
      } else if (D !== 0 || _.isRenderTargetTexture || gt.has(_)) {
        let De = gt.get(_), _e = gt.get(L);
        mt.bindFramebuffer(E.READ_FRAMEBUFFER, ac), mt.bindFramebuffer(E.DRAW_FRAMEBUFFER, oc);
        for (let ye = 0; ye < ht; ye++) ie ? E.framebufferTextureLayer(E.READ_FRAMEBUFFER, E.COLOR_ATTACHMENT0, De.__webglTexture, D, bt + ye) : E.framebufferTexture2D(E.READ_FRAMEBUFFER, E.COLOR_ATTACHMENT0, E.TEXTURE_2D, De.__webglTexture, D), Le ? E.framebufferTextureLayer(E.DRAW_FRAMEBUFFER, E.COLOR_ATTACHMENT0, _e.__webglTexture, Q, re + ye) : E.framebufferTexture2D(E.DRAW_FRAMEBUFFER, E.COLOR_ATTACHMENT0, E.TEXTURE_2D, _e.__webglTexture, Q), D !== 0 ? E.blitFramebuffer(Tt, Ct, ot, ft, Ot, Yt, ot, ft, E.COLOR_BUFFER_BIT, E.NEAREST) : Le ? E.copyTexSubImage3D(ne, Q, Ot, Yt, re + ye, Tt, Ct, ot, ft) : E.copyTexSubImage2D(ne, Q, Ot, Yt, Tt, Ct, ot, ft);
        mt.bindFramebuffer(E.READ_FRAMEBUFFER, null), mt.bindFramebuffer(E.DRAW_FRAMEBUFFER, null);
      } else Le ? _.isDataTexture || _.isData3DTexture ? E.texSubImage3D(ne, Q, Ot, Yt, re, ot, ft, ht, Zt, Et, Kt.data) : L.isCompressedArrayTexture ? E.compressedTexSubImage3D(ne, Q, Ot, Yt, re, ot, ft, ht, Zt, Kt.data) : E.texSubImage3D(ne, Q, Ot, Yt, re, ot, ft, ht, Zt, Et, Kt) : _.isDataTexture ? E.texSubImage2D(E.TEXTURE_2D, Q, Ot, Yt, ot, ft, Zt, Et, Kt.data) : _.isCompressedTexture ? E.compressedTexSubImage2D(E.TEXTURE_2D, Q, Ot, Yt, Kt.width, Kt.height, Zt, Kt.data) : E.texSubImage2D(E.TEXTURE_2D, Q, Ot, Yt, ot, ft, Zt, Et, Kt);
      E.pixelStorei(E.UNPACK_ROW_LENGTH, Ht), E.pixelStorei(E.UNPACK_IMAGE_HEIGHT, be), E.pixelStorei(E.UNPACK_SKIP_PIXELS, Jn), E.pixelStorei(E.UNPACK_SKIP_ROWS, Ee), E.pixelStorei(E.UNPACK_SKIP_IMAGES, Ei), Q === 0 && L.generateMipmaps && E.generateMipmap(ne), mt.unbindTexture();
    }, this.initRenderTarget = function(_) {
      gt.get(_).__webglFramebuffer === void 0 && Ut.setupRenderTarget(_);
    }, this.initTexture = function(_) {
      _.isCubeTexture ? Ut.setTextureCube(_, 0) : _.isData3DTexture ? Ut.setTexture3D(_, 0) : _.isDataArrayTexture || _.isCompressedArrayTexture ? Ut.setTexture2DArray(_, 0) : Ut.setTexture2D(_, 0), mt.unbindTexture();
    }, this.resetState = function() {
      w = 0, P = 0, N = null, mt.reset(), at.reset();
    }, typeof __THREE_DEVTOOLS__ < "u" && __THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe", { detail: this }));
  }
  get coordinateSystem() {
    return Ve;
  }
  get outputColorSpace() {
    return this._outputColorSpace;
  }
  set outputColorSpace(t3) {
    this._outputColorSpace = t3;
    let e = this.getContext();
    e.drawingBufferColorSpace = kt._getDrawingBufferColorSpace(t3), e.unpackColorSpace = kt._getUnpackColorSpace();
  }
};

// ../offmenu-data/runtime/layout-migration/worker13/scanner-audio-current176-20261027/timeout-r1/candidate/guest-shelf-scanner-inventory.js
var guestStorage2 = createGuestStorage();
var inventory = _OffMenuSourceBarcode.createSourceBarcodeInventory({foundationInventory:_OffMenuGuestFoundation.createGuestFoundationLookup({origin:location.origin,analyzeIdentifier}),selection:_OffMenuSourceBarcodeSelection,fetchImpl:(...args)=>fetch(...args)});
var { lookupIdentifiers: lookupIdentifiers2, mergeIdentifierPages } = inventory;
var $ = (id2) => document.getElementById(id2);
var productVisual = mountScannerProductVisual($("thumbnail"), $("product-visual-caption"), { onChange: () => {
  renderConsumerSummary();
  renderData();
} });
var modes = { Explore: "Inspect source information. No inventory changes.", Buy: "Collect shopping intent for later receipt comparison. This is not payment.", Stock: "Unpacking intake needs eligible identity, quantity and a verified pantry action.", Audit: "Reconcile existing lots; never double-add scanned inventory.", Discard: "Outflow needs an identified lot, quantity and reason, with undo." };
var BEEP_PREFERENCE = "offmenu-scanner-read-beep";
var SPEECH_PREFERENCE = "offmenu-scanner-spoken-name";
function feedbackPreference(key) {
  try {
    return guestStorage2.getItem(key) !== "off";
  } catch {
    return true;
  }
}
var mode = "Explore";
var active = true;
var paused = false;
var streaming = false;
var finished = false;
var queue = [];
var generation = 0;
var current = null;
var selected2 = null;
var tab = "overview";
var sound = feedbackPreference(BEEP_PREFERENCE);
var spokenName = feedbackPreference(SPEECH_PREFERENCE);
var audio = null;
var readCueTimer = null;
var waitingReadCue = null;
var pendingSpeech = null;
var pendingSpeechTimer = null;
var sheetSnap = 0;
var sheetTouched = false;
var optionsSnap = 2;
function setSheetSnap(next, { user = false } = {}) {
  sheetSnap = Math.max(0, Math.min(3, next));
  if (user) sheetTouched = true;
  const sheet = $("product-sheet");
  sheet.dataset.snap = String(sheetSnap);
  const heights = [64, Math.min(Math.max(innerHeight * 0.32, 190), 310), Math.min(Math.max(innerHeight * 0.58, 310), 580), Math.max(220, innerHeight - 116)];
  document.documentElement.style.setProperty("--sheet-occlusion", heights[sheetSnap] + "px");
  $("product-handle").setAttribute("aria-expanded", String(sheetSnap > 0));
  $("product-sheet-body").setAttribute("aria-hidden", String(sheetSnap === 0));
  $("snap-label").textContent = sheetSnap === 3 ? "\u2304" : "\u2303";
  $("product-handle").setAttribute("aria-label", sheetSnap === 3 ? "Collapse product details" : sheetSnap === 0 ? "Expand product details" : "Show additional product details");
  requestAnimationFrame(() => renderData());
}
function setOptionsSnap(next) {
  optionsSnap = Math.max(0, Math.min(3, next));
  $("mode-dialog").dataset.snap = String(optionsSnap);
  $("options-handle").setAttribute("aria-label", optionsSnap === 3 ? "Collapse scanner options" : "Expand scanner options");
}
function bindSheetHandle(id2, get, set) {
  const node = $(id2);
  let from = null, dragged = false;
  node.addEventListener("pointerdown", (e) => {
    from = e.clientY;
    dragged = false;
    node.setPointerCapture(e.pointerId);
  });
  node.addEventListener("pointerup", (e) => {
    if (from === null) return;
    const dy = e.clientY - from;
    from = null;
    if (Math.abs(dy) > 28) {
      dragged = true;
      set(get() + (dy < 0 ? 1 : -1));
    }
  });
  node.addEventListener("click", () => {
    if (dragged) {
      dragged = false;
      return;
    }
    set(get() === 3 ? 0 : get() + 1);
  });
  node.addEventListener("keydown", (e) => {
    if (e.key === "ArrowUp" || e.key === "ArrowDown") {
      e.preventDefault();
      set(get() + (e.key === "ArrowUp" ? 1 : -1));
    }
  });
}
var processed = /* @__PURE__ */ new Set();
function readKitchenPrefill() {
  return readGuestPrefill();
}
function el2(tag, value, cls) {
  const e = document.createElement(tag);
  e.textContent = value;
  if (cls) e.className = cls;
  return e;
}
function btn(label, fn2) {
  const e = el2("button", label);
  e.type = "button";
  e.onclick = fn2;
  return e;
}
function message(s) {
  $("lookup-status").textContent = s;
  $("lookup-status").title = s;
}
function open(id2) {
  if (!$(id2).open) $(id2).showModal();
}
function close(id2) {
  $(id2).close();
}
function displayValue(id2, value) {
  $(id2).textContent = value || "\u2014";
  $(id2).title = value || "Unavailable";
}
function projectedField(name) {
  return selected2?.detail?.fields?.[name];
}
function projectedValue(name) {
  const f = projectedField(name);
  return f?.state === "present" ? f.value : null;
}
function sourceNotice() {
  const sourceId = selected2?.provenance?.sourceId || selected2?.detail?.sourceBinding?.sourceId;
  if (sourceId === "off") return "OffMenu inventory \xB7 original Open Food Facts source \xB7 retain attribution and ODbL/DbCL notices. Source claims are not independently certified. Image and trademark permissions remain separate from product data rights.";
  if (sourceId === "usda-files") return "USDA ARS FoodData Central source \xB7 retained public-domain/CC0 declaration. Source lineage applies; third-party image and trademark rights are unverified.";
  return sourceId ? "Source " + sourceId + " \xB7 attribution and use terms require the retained source record." : "Source attribution unavailable.";
}
function roleReasonsText(reasons) {
  return Array.isArray(reasons) ? reasons.map((r) => [r.role, r.qualificationState, r.reasonCode || "no reason supplied"].join(" \xB7 ")).join(" / ") : "Role reasons unavailable";
}
var detailPage = 0;
var detailPageKey = "";
function humanValue(v) {
  if (v === null || v === void 0) return "Unknown";
  if (Array.isArray(v)) return v.length ? v.map(humanValue).join(", ") : "No values supplied";
  if (typeof v === "object") {
    const entries = Object.entries(v).filter(([, x]) => x !== null && x !== void 0);
    return entries.length ? entries.map(([k, x]) => k.replace(/([a-z])([A-Z])/g, "$1 $2") + ": " + humanValue(x)).join(" \xB7 ") : "Unknown";
  }
  return String(v);
}
function readoutField(name) {
  const f = projectedField(name);
  if (!f) return "Not supplied";
  if (f.state === "present") return humanValue(f.value);
  if (f.state === "null") return "Unknown";
  if (f.state === "missing") return "Not supplied";
  if (f.state === "not-loaded") return "Not loaded";
  if (f.state === "restricted" || f.state === "rights-held") return "Not available for display";
  return "Unavailable right now";
}
function readoutNutrient(n) {
  if (!n || typeof n !== "object") return "Unknown \xB7 not zero";
  const value = n.value === null || n.value === void 0 ? "Unknown \xB7 not zero" : humanValue(n.value) + " " + (n.unit || "unit unknown");
  const details = [["basis", n.basis], ["method", n.method], ["source name", n.sourceName], ["source nutrient ID", n.sourceNutrientId], ["source row ID", n.sourceRowId], ["source amount", n.sourceAmount], ["source unit", n.sourceUnit]].filter(([, v]) => v !== null && v !== void 0).map(([label, v]) => label + ": " + humanValue(v));
  return [value, ...details].join(" \xB7 ");
}
function renderConsumerSummary() {
  const host = $("consumer-summary");
  host.replaceChildren();
  if (!selected2?.detail) {
    host.append(el2("p", current?.status === "scoped-miss" ? "No match in the available barcode records. Other products may not be covered." : detailQueryUnavailable(current) ? detailFailureText(current) : current?.status === "unavailable" ? "Product lookup is unavailable for this release. Your scanned code is retained in this session; no product has been identified." : current ? "Choose a source record to see its details." : "Scan to inspect a product.", "label"));
    return;
  }
  host.append(el2("p", "Source: " + (selected2.provenance?.sourceId || "unknown") + " \xB7 release " + (selected2.provenance?.releaseId || "unknown"), "label"));
  for (const [label, key] of [["Market", "markets"], ["Source allergens", "sourceAllergenClaims"], ["Source traces", "sourceTraceClaims"], ["Source labels", "sourceDietaryLabelClaims"], ["Source categories", "categories"], ["Source origins", "origins"], ["Manufactured (source)", "manufacturingPlaces"]]) {
    const value = projectedValue(key);
    if (value !== null && value !== void 0 && (!Array.isArray(value) || value.length)) host.append(el2("p", label + ": " + humanValue(value)));
  }
  for (const section of selected2.detail.labelSections?.sections || []) if (section.category === "origin_claim") host.append(el2("p", "Source origin claim: " + section.text));
}
function sourceComponentRows(tree) {
  const rows = [];
  const visit = (node, depth) => {
    const name = (node.nameSpans || []).map((span) => span.text).join(" \xB7 ") || node.text;
    const quantities = (node.quantities || []).map((q) => "Source-stated " + q.text + " \xB7 basis unknown; no interpreted amount");
    const cautions = (node.uncertainty || []).map((u) => typeof u === "string" ? u : u.reason || u.meaning || "Source syntax uncertain");
    rows.push({ label: "  ".repeat(depth) + (depth ? "\u21B3 " : "") + name, text: [node.text, ...quantities, ...cautions].join(" \xB7 ") });
    for (const child of node.children || []) visit(child, depth + 1);
  };
  for (const root of tree.components || []) visit(root, 0);
  return rows;
}
function detailQueryUnavailable(entry) {
  return entry?.detailsState === "unavailable" && !!entry.detailReasonCode;
}
function detailFailureText(entry) {
  return "Product details are unavailable right now. The barcode record is still shown.";
}
function readoutItems() {
  if(current?.foundationLookup){const rows=_OffMenuSourceBarcode.inventoryReadout(_OffMenuGuestFoundation.foundationReadout,selected2,current,tab);if(current.matches?.length||current.hasMore)rows.push({label:"Separate source observations",text:"Inspect source records",action:showMatches});if(current.sourceBarcodeResult?.hasMore)rows.push({label:"More source identifier candidates",text:"Load another stored reference page; facts remain pending verified hydration",action:async()=>{const entry=current,token=generation;try{const next=await inventory.moreSourceBarcode(entry);if(current!==entry||generation!==token)return;Object.assign(entry,next);render();showMatches();}catch{if(current===entry&&generation===token)message("Additional source candidate references are unavailable. Loaded references and original barcode are retained.");}}});if(selected2?.kind==="source-barcode-candidate"&&selected2.sourceBarcodeCandidate.hydrationState!=="verified")rows.push({label:"Load verified original source details",text:"Verify the pinned public asset before showing its original facts",action:async()=>{const entry=current,match=selected2,token=generation;try{message("Verifying original source details…");const next=await inventory.hydrateSourceBarcode(entry,match);if(current!==entry||generation!==token)return;Object.assign(entry,next);if(selected2===match)selected2=next.matches.find(m=>m.id===match.id);render();}catch{if(current===entry&&generation===token)message("Source details unavailable. Original identifier retained; no absence is established.");}}});return rows;}

  if (!current) return [{ label: "Ready", text: "Scan a barcode to see product details." }];
  const detail = selected2?.detail;
  if (current.status === "unavailable") return [{ label: "Product lookup", text: "Unavailable for this release. The code was read, but no product identity or details were verified." }];
  if (!detail && ["partial", "searching"].includes(current.status)) {
    return [{ label: "Selected search", text: current.status === "partial" ? "Incomplete \xB7 retry the failed lane; loaded source observations remain visible." : current.status === "searching" ? "More selected lanes remain; no absence established." : "Selected identifier lookup unavailable; no absence established." }, { label: "Loaded source observations", text: String(current.matches?.length || 0), action: showMatches }];
  }
  if (!detail) {
    const items2 = [{ label: "Source details", text: current.status === "scoped-miss" ? "No matching source observation in the selected index and completed query plan \xB7 not global absence." : detailQueryUnavailable(current) ? current.matches.length + " source identifier assertion(s) retained \xB7 " + detailFailureText(current) : current.status === "ambiguous" ? "Multiple source records or eligible detail projections; inspect without resolving identity." : "Identifier known \xB7 product details " + (selected2?.availability?.state || current.detailsState || "not-loaded") + " \xB7 " + (selected2?.availability?.reasonCode || current.detailReasonCode || "reason unavailable") }];
    for (const match of current.matches || []) if (match.availability?.roleReasons?.length) items2.push({ label: "Source assertion " + match.identifier.assertion_id + " \xB7 required role reasons", text: roleReasonsText(match.availability.roleReasons) });
    if (current.detailBackend === "retained-product-federation-v1") items2.push({ label: "Per-backend coverage \xB7 global counts unknown", text: humanValue(current.productDetailCoverage) });
    if (current.matches?.length) items2.push({ label: "Source alternatives", action: showMatches, text: "Inspect source records" });
    return items2;
  }
  const fields = detail.fields, items = [];
  const add = (label, v) => items.push({ label, text: humanValue(v) });
  if (tab === "overview") {
    for (const [label, key] of [["Product \xB7 source assertion", "name"], ["Brand \xB7 source assertion", "brand"], ["Markets (not origin)", "markets"], ["Package \xB7 source projection", "packageQuantity"], ["Serving \xB7 source projection, not package", "servingQuantity"], ["Source data type", "dataType"], ["Source categories", "categories"], ["Source allergen claims (not certification)", "sourceAllergenClaims"], ["Source trace claims (not certification)", "sourceTraceClaims"], ["Source dietary / label claims (not certification)", "sourceDietaryLabelClaims"], ["Source origins", "origins"], ["Manufacturing places", "manufacturingPlaces"], ["Names / languages", "names"]]) add(label, readoutField(key));
    add("Ingredient use", "Unclassified by this response \xB7 no qualified usable_as or contains relation. Barcode and source identity remain visible.");
    add("Supplier / offers, recalls, recipe links", "No qualified relation supplied by this selected response \xB7 unknown, not none.");
    add("Product image", productVisual.current()?.caption || "Product photo unavailable");
    if (current.detailBackend === "retained-product-federation-v1") add("Detail coverage", "Federated retained subset \xB7 incomplete. Identifier coverage is separate; unknown global counts are not zero.");
    items.push({ label: "Competing observations", text: "Inspect source records", action: showMatches });
  } else if (tab === "ingredients") {
    const annotation = detail.labelSections, tree = detail.ingredientComponents;
    if (tree?.state === "cached-candidate") {
      add("Source-derived candidate components", "Parent/child label syntax only \xB7 no Ingredients heading, canonical identities, certification or unstated quantities.");
      items.push(...sourceComponentRows(tree));
      add("Component annotation evidence", tree.annotationSha256);
      add("Annotation limits", tree.reviewStatus);
    } else if (annotation?.state === "cached-candidate") {
      for (const section of annotation.sections) if (section.category === "ingredient_list") add("Candidate ingredient passage \xB7 component annotation unavailable", section.text);
    } else add("Whole label text \xB7 extraction pending", readoutField("ingredientDeclaration"));
    for (const section of annotation?.sections || []) if (section.category === "allergen_statement") add("Separate source allergen statement \xB7 not certification", section.text);
  } else if (tab === "nutrition") {
    const profile = projectedValue("nutrientProfile");
    add("Projected measurement basis \xB7 applicability unverified", projectedField("nutrientProfile")?.state === "present" ? profile?.basis : readoutField("nutrientProfile"));
    add("Source nutrition basis", readoutField("nutritionSourceBasis"));
    for (const [name, n] of Object.entries(profile?.nutrients || {})) add(name + " \xB7 source nutrient assertion", readoutNutrient(n));
    add("Raw retained nutrient values", readoutField("rawNutriments"));
  } else {
    add("Source and use notice", sourceNotice());
    if (detail.retainedSourceCategoryPresentation) {
      const retained = detail.retainedSourceCategoryPresentation;
      add("Retained source category evidence", { sourceProductReference: retained.sourceProductReference, projectionEvidence: retained.projectionEvidence, categories: retained.categories, sourceScope: retained.sourceScope, taxonomySnapshotSHA256: retained.taxonomySnapshotSHA256, sourceNotice: retained.sourceNotice });
    }
    add("Source release", selected2?.identifier?.release_id || "Unknown");
    add("Source record", selected2?.identifier?.source_record_id || "Unknown");
    add("Source citation", selected2?.identifier?.citation_id || "Not supplied");
    add("Full package label", readoutField("ingredientDeclaration"));
    if (detail.labelSections?.state === "cached-candidate") {
      for (const section of detail.labelSections.sections) if (section.text.trim()) add("Source label \xB7 " + section.category.replaceAll("_", " "), section.text);
    }
    for (const [name] of Object.entries(fields)) {
      if (name === "ingredientDeclaration") continue;
      add(name.replace(/([a-z])([A-Z])/g, "$1 $2").replaceAll("_", " "), readoutField(name));
    }
    if (current.matches?.length > 1) items.push({ label: "Other source records", text: "See all matching records", action: showMatches });
  }
  items.push(...sourceAssertionReadout(detail, tab));
  return items;
}
function renderData() {
  const host = $("data-pane");
  $("product-visual-caption").hidden = tab !== "source";
  const key = (current?.id || "empty") + ":" + (selected2?.id || "none") + ":" + tab;
  if (key !== detailPageKey) {
    detailPageKey = key;
    detailPage = 0;
  }
  const pages = [[]];
  host.replaceChildren();
  host.setAttribute("aria-label", tab + " readout");
  const fits = () => host.clientHeight < 60 || host.scrollHeight <= host.clientHeight + 1;
  const block = (item, text2) => {
    const node = el2("article", "", "paged-field");
    node.append(el2("h3", item.label), item.action ? btn(item.text, item.action) : el2("p", text2));
    return node;
  };
  const next = () => {
    pages.push([]);
    host.replaceChildren();
  };
  for (const item of readoutItems()) {
    let chars = Array.from(item.text || "\u2014"), offset = 0;
    do {
      let node = block(item, chars.slice(offset).join(""));
      host.append(node);
      if (fits()) {
        pages.at(-1).push(node);
        break;
      }
      node.remove();
      if (pages.at(-1).length) {
        next();
        continue;
      }
      let lo2 = 1, hi2 = chars.length - offset, best = 1;
      while (lo2 <= hi2) {
        const mid = Math.floor((lo2 + hi2) / 2);
        node = block(item, chars.slice(offset, offset + mid).join(""));
        host.append(node);
        const okay = fits();
        node.remove();
        if (okay) {
          best = mid;
          lo2 = mid + 1;
        } else hi2 = mid - 1;
      }
      node = block(item, chars.slice(offset, offset + best).join(""));
      pages.at(-1).push(node);
      host.append(node);
      offset += best;
      if (offset < chars.length) next();
    } while (offset < chars.length);
  }
  detailPage = Math.min(detailPage, pages.length - 1);
  host.replaceChildren(...pages[detailPage]);
  $("detail-page-status").textContent = detailPage + 1 + " / " + pages.length;
  $("detail-prev").disabled = detailPage === 0;
  $("detail-next").disabled = detailPage === pages.length - 1;
}
function selectedQueueRecord(entry) {
  const choice = entry?.selectedRecord;
  return choice && entry.matches?.includes(choice) ? choice : null;
}
function render() {
  if (current) current.selectedRecord = selected2 && current.matches.includes(selected2) ? selected2 : null;
  productVisual.show({ sourceProductReference: selected2?.sourceProductReference ?? null, retainedSourceCategoryPresentation: selected2?.detail?.retainedSourceCategoryPresentation ?? null, reference: selected2?.sourceObservationReference ?? null, sourcePhotoSelection: selected2?.detail?.sourcePhotoSelection ?? null, detail: selected2?.detail, entryId: current?.id, generation, name: selected2?.name, theme: document.documentElement.dataset.theme, offline: navigator.onLine === false });
  const latest = current;
  $("identifier-label").textContent = latest?.namespace === "USDA-FDC" ? "USDA-FDC \xB7 original identifier" : "Barcode \xB7 original";
  $("current-barcode").textContent = latest?.raw || "\u2014";
  displayValue("product-name", selected2?.kind === "source-barcode-candidate" ? (selected2.sourceBarcodeCandidate.hydrationState === "verified" ? selected2.name || "Identifier match · name unknown" : selected2.sourceBarcodeCandidate.hydrationState === "unavailable" ? "Identifier match · details unavailable" : "Identifier match · details pending") : selected2?.name || (latest?.status === "source-match" ? "Name unavailable \xB7 source record found" : latest?.status === "ambiguous" ? "Name unavailable \xB7 multiple source records" : null));
  displayValue("brand-name", selected2?.brand);
  const category = selected2?.detail?.canonicalCategory, ingredient = selected2?.detail?.canonicalIngredient;
  const categoryText = category?.status === "qualified" && category?.preferredLabel ? category.preferredLabel : "Not yet identified";
  const ingredientText = ingredient?.status === "qualified" && ingredient?.preferredLabel ? ingredient.preferredLabel : ingredient?.status === "not-applicable" ? "Not applicable" : "Not yet identified";
  const packageText = projectedField("packageQuantity")?.state === "present" ? humanValue(projectedValue("packageQuantity")) : "\u2014";
  for (const [id2, label, value] of [["category-value", "Category", categoryText], ["ingredient-value", "Ingredient match", ingredientText], ["pack-value", "Source pack size", packageText]]) {
    $(id2).textContent = value;
    $(id2).setAttribute("aria-label", label + ": " + value);
  }
  $("sheet-handle-label").textContent = latest?.raw ? selected2?.name || "Barcode " + latest.raw : "Ready to scan";
  renderConsumerSummary();
  $("kitchen-handoff").hidden = true;
  $("queue-count").textContent = queue.length;
  $("active-mode").textContent = mode + (finished ? " \xB7 Finished" : paused ? " \xB7 Paused" : "");
  $("undo").disabled = !queue.length;
  $("pause").disabled = false;
  $("pause").textContent = "List";
  $("finish").textContent = "Finish";
  $("camera-empty").hidden = streaming;
  if (latest) {
    message(selected2?.kind === "source-barcode-candidate" ? (selected2.sourceBarcodeCandidate.hydrationState === "verified" ? "Verified original source facts · candidate identity" : selected2.sourceBarcodeCandidate.hydrationState === "unavailable" ? "Source identifier retained · technical details unavailable" : "Source identifier match · details pending") : latest.privateRetainedSource === true ? "Selected source record \xB7 ingredient use unclassified" : latest.status === "unavailable" ? "Code read \xB7 OffMenu inventory unavailable" : latest.status === "pending" ? "Code read \xB7 checking OffMenu inventory" : latest.status === "source-match" ? "Code read \xB7 OffMenu inventory record found" : latest.status === "scoped-miss" ? "Code read \xB7 no matching product in the selected OffMenu inventory" : latest.status === "partial" ? "Code read \xB7 some selected OffMenu inventory sources are unavailable; inspect loaded records" : latest.status === "searching" ? "Code read \xB7 more OffMenu inventory pages remain" : latest.status === "ambiguous" ? "Code read \xB7 multiple OffMenu inventory records; inspect a record" : "Product status unavailable");
  } else message("Ready \xB7 scan or enter a code");
  if (latest?.foundationLookup && selected2?.kind !== "source-barcode-candidate") { const foundation=latest.foundationResult||latest; message((foundation.status === "scoped-miss" ? "Barcode retained · no qualified details in the selected source indexes. Other sources may differ." : foundation.status === "searching" ? "Barcode retained · more selected representations remain to check." : foundation.status === "unavailable" ? "Code read · selected foundation data unavailable; no global absence established" : foundation.matches.length + " source foundation observation(s) · full product not established")+(latest.sourceBarcodeResult?.enabled && (latest.sourceBarcodeResult.configurationError || !latest.sourceBarcodeResult.complete || latest.sourceBarcodeResult.lanes?.some(l=>l.status==="index-unavailable"||l.pageError)) ? " · Additional identifier index unavailable; coverage incomplete." : "")); }
  renderData();
}
async function enableAudio() {
  const A = window.AudioContext || window.webkitAudioContext;
  if (!A) {
    $("feedback-status").textContent = "Sound is unavailable in this browser.";
    return false;
  }
  try {
    audio ??= new A();
    if (audio.state !== "running") await audio.resume();
    if (audio.state === "running") return true;
    $("feedback-status").textContent = "Tap the scanner to allow sound.";
  } catch (error) {
    $("feedback-status").textContent = "Tap the scanner to allow sound.";
    console.warn("Scanner audio could not start", error?.name || "unknown");
  }
  return false;
}
function unlockBeepOnGesture() {
  if (!sound || audio?.state === "running") return;
  void enableAudio().then((ok) => {
    if (!ok) return;
    const queued = waitingReadCue;
    waitingReadCue = null;
    $("audio-unlock").hidden = true;
    if (queued && queued.id === current?.id && performance.now() - queued.at < 1200) readTone();
  });
}
function readTone() {
  if (!sound) return false;
  if (audio?.state !== "running") return false;
  try {
    const o = audio.createOscillator(), g = audio.createGain(), t3 = audio.currentTime;
    o.type = "sine";
    o.frequency.setValueAtTime(1e3, t3);
    o.frequency.linearRampToValueAtTime(1240, t3 + 0.045);
    g.gain.setValueAtTime(1e-4, t3);
    g.gain.linearRampToValueAtTime(0.032, t3 + 8e-3);
    g.gain.exponentialRampToValueAtTime(1e-4, t3 + 0.12);
    o.connect(g);
    g.connect(audio.destination);
    o.start(t3);
    o.stop(t3 + 0.13);
    return true;
  } catch (error) {
    $("feedback-status").textContent = "Sound is unavailable; the scan remains visible.";
    console.warn("Scanner beep failed", error?.name || "unknown");
    return false;
  }
}
function showReadCue(entry, played) {
  $("scanner-last").textContent = (entry.captureKind === "manual lexical identifier" ? "Code entered" : "Scanned") + " \xB7 " + entry.raw;
  $("instrument").dataset.readCue = "read";
  clearTimeout(readCueTimer);
  readCueTimer = setTimeout(() => {
    delete $("instrument").dataset.readCue;
  }, 1100);
}
function englishDisplayName(variant) {
  const detail = variant?.detail, names = detail?.fields?.names?.state === "present" ? detail.fields.names.value : null;
  let name = typeof names?.en === "string" ? names.en : null;
  if (!name && Array.isArray(names)) {
    const item = names.find((x) => /^en(?:-|$)/i.test(x?.language || x?.lang || "") && typeof (x.value ?? x.name ?? x.text) === "string");
    name = item?.value ?? item?.name ?? item?.text ?? null;
  }
  const field = detail?.fields?.name;
  if (!name && /^en(?:-|$)/i.test(field?.language || field?.languageCode || detail?.nameLanguage || "") && field?.state === "present") name = variant?.name;
  return typeof name === "string" && name.trim() ? name.trim().slice(0, 160) : null;
}
function cancelPendingSpeech() {
  clearTimeout(pendingSpeechTimer);
  pendingSpeechTimer = null;
  if (pendingSpeech) {
    window.speechSynthesis?.removeEventListener?.("voiceschanged", pendingSpeech);
    pendingSpeech = null;
  }
}
function speakResolvedName(entry, variant, token, retry = false) {
  if (!spokenName || entry.spokenName || token !== generation || current?.id !== entry.id) return;
  const name = englishDisplayName(variant), synth = window.speechSynthesis, U = window.SpeechSynthesisUtterance;
  if (!name || !synth || !U) {
    $("feedback-status").textContent = name ? "Spoken names are unavailable in this browser." : "No English source name is available to speak.";
    return;
  }
  const voices = synth.getVoices?.() || [], voice = voices.find((v) => /^en(?:-|$)/i.test(v.lang || "") && v.localService === true);
  if (!voice) {
    if (!retry && typeof synth.addEventListener === "function") {
      cancelPendingSpeech();
      pendingSpeech = () => {
        cancelPendingSpeech();
        speakResolvedName(entry, variant, token, true);
      };
      synth.addEventListener("voiceschanged", pendingSpeech, { once: true });
      const listener = pendingSpeech;
      pendingSpeechTimer = setTimeout(() => {
        if (pendingSpeech !== listener) return;
        cancelPendingSpeech();
        if (token === generation && current?.id === entry.id) $("feedback-status").textContent = "No local English voice is available on this device.";
      }, 2500);
    } else $("feedback-status").textContent = "No local English voice is available on this device.";
    return;
  }
  try {
    cancelPendingSpeech();
    synth.cancel();
    const utterance = new U(name);
    utterance.voice = voice;
    utterance.lang = voice.lang;
    utterance.rate = 1;
    utterance.volume = 0.75;
    utterance.onerror = () => {
      $("feedback-status").textContent = "Spoken name could not play on this device.";
    };
    entry.spokenName = name;
    synth.speak(utterance);
  } catch (error) {
    $("feedback-status").textContent = "Spoken name could not play on this device.";
    console.warn("Scanner speech failed", error?.name || "unknown");
  }
}
function updateFeedbackButtons() {
  $("sound").textContent = sound ? "Beep on" : "Beep off";
  $("sound").setAttribute("aria-pressed", String(sound));
  $("spoken-name").textContent = spokenName ? "Speak product name on" : "Speak product name off";
  $("spoken-name").setAttribute("aria-pressed", String(spokenName));
}
var CAPTURE_FORMATS = { "ean_13": "EAN-13", "ean_8": "EAN-8", "upc_a": "UPC-A", "upc_e": "UPC-E", "EAN-13": "EAN-13", "EAN-8": "EAN-8", "UPC-A": "UPC-A", "UPC-E": "UPC-E", "GTIN-14": "GTIN-14" };
async function capture(raw, captureKind, alias = null, eventId = crypto.randomUUID(), { sourceNamespace = "barcode", representationHint = null, decoderCapture = null } = {}) {
  if (!active || paused || processed.has(eventId)) return;
  if (typeof raw !== "string" || !raw.length || raw.length > 128 || /[\x00-\x1f\x7f]/.test(raw)) {
    message("Invalid capture \xB7 enter 1\u2013128 original printable characters.");
    return;
  }
  const symbology = sourceNamespace === "barcode" ? representationHint || CAPTURE_FORMATS[captureKind] || null : null;
  const evidence = decoderCapture ? captureEvidence(decoderCapture) : null;
  if (decoderCapture && (!evidence || !verifyCaptureEvidence(evidence, raw, symbology))) {
    message("Decoder capture needs manual confirmation. No lookup was started.");
    return;
  }
  processed.add(eventId);
  cancelPendingSpeech();
  waitingReadCue = null;
  try {
    window.speechSynthesis?.cancel();
  } catch {
  }
  const token = ++generation, entry = { id: eventId, queryGeneration: token, raw, namespace: sourceNamespace, captureKind, symbology, alias, decoderCapture: evidence, status: "pending", matches: [], mode };
  queue.push(entry);
  current = entry;
  selected2 = null;
  if (!sheetTouched) setSheetSnap(innerWidth >= 740 ? 3 : 1);
  render();
  const played = readTone();
  waitingReadCue = sound && !played && audio?.state !== "running" ? { id: entry.id, at: performance.now() } : null;
  $("audio-unlock").hidden = !waitingReadCue;
  showReadCue(entry, played);
  const result = await lookupIdentifiers2(raw, entry.queryGeneration, null, symbology, sourceNamespace);
  if (!queue.some((x) => x.id === entry.id) || entry.status !== "pending") return;
  Object.assign(entry, result);
  if (token !== generation) return;
  current = entry;
  if (result.matches?.length && ["source-match", "ambiguous"].includes(result.status)) scanner.noteAccepted();
  selected2 = _OffMenuSourceBarcode.automaticSourceSelection(result);
  render();
  if (selected2) speakResolvedName(entry, selected2, token);
}
function showMatches() {
  const entry = current, token = generation, host = $("match-list");
  host.replaceChildren();
  $("matches-note").textContent = (entry?.sourceBarcodeResult?.enabled ? (entry.foundationResult?.matches?.length || 0) + " foundation observation(s) and " + entry.matches.filter(m=>m.kind==="source-barcode-candidate").length + " separate source identifier candidate(s). Verify original details before factual display." : (entry?.matches?.length || 0) + " public source product record(s). Source claims are attributed; ingredient suitability is not inferred.");
  for (const match of entry?.matches || []) {
    const box = el2("div", "", "choice");
    box.append(el2("strong", match.name || "Name not supplied"), el2("p", "Source: " + match.provenance.sourceId + " \xB7 release " + (match.provenance.releaseId || "unknown") + " \xB7 record " + match.id), btn(match.kind === "source-barcode-candidate" ? "Inspect source identifier candidate" : "Inspect product record", () => {
      if (token !== generation || current?.id !== entry.id) return;
      selected2 = match;
      close("matches-dialog");
      render();
      speakResolvedName(entry, match, token);
    }));
    host.append(box);
  }
  if (entry?.hasMore) host.append(btn("Continue source search", async () => {
    const result = await lookupIdentifiers2(entry.raw, entry.queryGeneration ?? entry.generation, entry.nextCursor, entry.symbology, entry.namespace);
    if (token !== generation || current?.id !== entry.id) return;
    if (result.status === "unavailable") {
      message("Next source page is unavailable; loaded records remain visible.");
      return;
    }
    try {
      Object.assign(entry, mergeIdentifierPages(entry, result));
    } catch {
      message("Source release changed; loaded records remain visible.");
      return;
    }
    render();
    showMatches();
  }));
  open("matches-dialog");
}
function renderQueue() {
  const host = $("queue-list");
  host.replaceChildren();
  $("session-summary").textContent = queue.length ? queue.length + " item" + (queue.length === 1 ? "" : "s") + " scanned. " + queue.filter((x) => x.status === "ambiguous").length + " need" + (queue.filter((x) => x.status === "ambiguous").length === 1 ? "s" : "") + " a choice. Nothing has been added to your pantry." : "No items scanned yet.";
  for (const entry of queue) {
    const row = el2("div", "", "queue-row");
    row.append(el2("strong", entry.raw), el2("span", entry.mode + " \xB7 " + entry.status + " \xB7 " + entry.matches.length + " source records"), btn("Inspect", () => {
      generation++;
      current = entry;
      selected2 = selectedQueueRecord(entry);
      close("session-dialog");
      render();
    }));
    host.append(row);
  }
}
var scanner = setupScanner({ autoResume: true, canScan: () => active && !paused && (sheetSnap < 3 || innerWidth >= 740) && !["tools-dialog", "manual-dialog", "session-dialog", "matches-dialog", "data-dialog", "mode-dialog"].some((id2) => $(id2)?.open), onCode: (code2, metadata) => {
  const evidence = metadata?.captureEnvelope, originals = metadata?.originalCaptures || [];
  if (!evidence || evidence.status !== "ready" || originals.length !== 1 || originals[0].value !== evidence.lookupLexicalValue || code2 !== evidence.lookupLexicalValue) {
    message("Decoder capture needs manual confirmation \xB7 use Type code.");
    return;
  }
  if (metadata?.captureKind === "photo") close("manual-dialog");
  void capture(code2, metadata?.captureKind === "photo" ? "photo" : "camera lexical capture", null, crypto.randomUUID(), { representationHint: evidence.lookupSymbology, decoderCapture: evidence });
}, onStream: (s) => {
  streaming = !!s;
  render();
}, onStartGesture: () => sound ? enableAudio() : void 0, storage: guestStorage2 });
$("scanner-mode").value = "handheld";
$("scanner-mode").onchange();
$("mode").onchange = () => {
  $("mode-description").textContent = modes[$("mode").value];
  $("enter-mode").textContent = "Enter " + $("mode").value;
};
$("mode").onchange();
$("enter-mode").onclick = () => {
  generation++;
  current = queue.at(-1) || null;
  selected2 = null;
  mode = $("mode").value;
  active = true;
  paused = false;
  finished = false;
  close("mode-dialog");
  render();
  void scanner.start();
};
$("close-mode").onclick = () => {
  close("mode-dialog");
  active = true;
  paused = false;
  render();
  void scanner.start();
};
$("mode-dialog").addEventListener("cancel", () => {
  active = true;
  paused = false;
  render();
  void scanner.start();
});
$("manual-namespace").onchange = () => {
  const fdc = $("manual-namespace").value === "USDA-FDC";
  $("manual-representation").disabled = fdc;
  if (fdc) $("manual-representation").value = "";
};
$("manual").onsubmit = (e) => {
  e.preventDefault();
  const raw = $("barcode").value, sourceNamespace = $("manual-namespace").value, representationHint = $("manual-representation").value || null;
  if (!["barcode", "USDA-FDC"].includes(sourceNamespace) || sourceNamespace === "USDA-FDC" && representationHint) {
    message("Choose a supported namespace and barcode hint.");
    return;
  }
  $("barcode").value = "";
  close("manual-dialog");
  if (active && !paused) void scanner.start();
  void capture(raw, "manual lexical identifier", null, crypto.randomUUID(), { sourceNamespace, representationHint });
};
$("manual-open").onclick = () => {
  close("session-dialog");
  $("barcode").value = "";
  $("manual-namespace").value = "barcode";
  $("manual-representation").value = "";
  $("manual-namespace").onchange();
  open("manual-dialog");
};
$("manual-cancel").onclick = () => {
  close("manual-dialog");
  if (active && !paused) void scanner.start();
};
$("manual-dialog").addEventListener("cancel", () => {
  if (active && !paused) void scanner.start();
});
bindSheetHandle("product-handle", () => sheetSnap, (next) => setSheetSnap(next, { user: true }));
bindSheetHandle("options-handle", () => optionsSnap, setOptionsSnap);
window.addEventListener("resize", () => {
  if (!sheetTouched) setSheetSnap(current ? innerWidth >= 740 ? 3 : 1 : 0);
});
$("session-button").onclick = () => {
  renderQueue();
  open("session-dialog");
};
$("close-session").onclick = () => {
  close("session-dialog");
  if (active && !paused) void scanner.start();
};
$("change-mode").onclick = () => {
  generation++;
  active = false;
  paused = false;
  scanner.stop();
  close("tools-dialog");
  close("session-dialog");
  render();
  open("mode-dialog");
};
$("close-matches").onclick = () => close("matches-dialog");
$("undo").onclick = () => {
  generation++;
  const removed = queue.pop();
  current = queue.at(-1) || null;
  selected2 = selectedQueueRecord(current);
  render();
};
$("pause").onclick = () => {
  renderQueue();
  open("session-dialog");
  scanner.stop({ announce: false });
};
$("finish").onclick = () => {
  try {
    const result = finishGuestSession(queue);
    generation++;
    active = false;
    finished = true;
    paused = false;
    scanner.stop();
    render();
    renderQueue();
    open("session-dialog");
    message(result.message);
  } catch (error) {
    message("Finish needs review: " + error.message);
  }
};
for (const b of document.querySelectorAll("[data-tab]")) b.onclick = () => {
  tab = b.dataset.tab;
  document.querySelectorAll("[data-tab]").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
  renderData();
};
updateFeedbackButtons();
$("audio-unlock").onclick = unlockBeepOnGesture;
document.addEventListener("pointerdown", unlockBeepOnGesture, { capture: true });
document.addEventListener("keydown", (e) => {
  if (!e.repeat && !e.ctrlKey && !e.metaKey && !e.altKey) unlockBeepOnGesture();
}, { capture: true });
$("sound").onclick = () => {
  sound = !sound;
  try {
    guestStorage2.setItem(BEEP_PREFERENCE, sound ? "on" : "off");
  } catch {
  }
  updateFeedbackButtons();
  if (sound) unlockBeepOnGesture();
  $("feedback-status").textContent = sound ? "Beep enabled where browser audio is available." : "Beep muted; visual confirmation stays on.";
};
$("spoken-name").onclick = () => {
  spokenName = !spokenName;
  try {
    guestStorage2.setItem(SPEECH_PREFERENCE, spokenName ? "on" : "off");
  } catch {
  }
  if (!spokenName) {
    cancelPendingSpeech();
    try {
      window.speechSynthesis?.cancel();
    } catch {
    }
  }
  updateFeedbackButtons();
  $("feedback-status").textContent = spokenName ? "English product names will be spoken when a source-backed name and voice are available." : "Spoken names off.";
};
$("tools-open").onclick = () => {
  open("tools-dialog");
  scanner.stop({ announce: false });
};
$("tools-close").onclick = () => {
  close("tools-dialog");
  if (active && !paused) void scanner.start();
};
$("tools-dialog").addEventListener("cancel", () => {
  if (active && !paused) void scanner.start();
});
$("tools-dialog").addEventListener("click", (e) => {
  if (e.target === e.currentTarget) {
    close("tools-dialog");
    if (active && !paused) void scanner.start();
    return;
  }
  if (e.target.closest("#manual-open,#session-button,#change-mode")) close("tools-dialog");
}, { capture: true });
$("session-dialog").addEventListener("cancel", () => {
  if (active && !paused) void scanner.start();
});
$("detail-prev").onclick = () => {
  detailPage = Math.max(0, detailPage - 1);
  renderData();
};
$("detail-next").onclick = () => {
  detailPage++;
  renderData();
};
var pagingFrame;
new ResizeObserver(() => {
  cancelAnimationFrame(pagingFrame);
  pagingFrame = requestAnimationFrame(() => renderData());
}).observe($("data-pane"));
var redraw = () => {
};
function applyScannerTheme(theme, source) {
  document.documentElement.dataset.theme = theme;
  document.documentElement.dataset.themeSource = source;
  for (const image of document.querySelectorAll("img[data-offmenu-logo]")) image.src = theme === "dark" ? "/scanner-balanced-final-dark.svg" : "/scanner-balanced-final.svg";
  redraw();
}
$("theme").onclick = () => {
  const theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  try {
    guestStorage2.setItem("offmenu-scanner-theme", theme);
  } catch {
  }
  applyScannerTheme(theme, "manual");
};
var systemTheme = matchMedia("(prefers-color-scheme: dark)");
systemTheme.addEventListener("change", (e) => {
  let preference;
  try {
    preference = guestStorage2.getItem("offmenu-scanner-theme");
  } catch {
  }
  if (!["dark", "light"].includes(preference)) applyScannerTheme(e.matches ? "dark" : "light", "system");
});
applyScannerTheme(document.documentElement.dataset.theme, document.documentElement.dataset.themeSource || "system");
$("camera-check").onclick = async () => {
  let permission = "unavailable";
  try {
    permission = (await navigator.permissions.query({ name: "camera" })).state;
  } catch {
  }
  const info = { context: window.isSecureContext ? "secure" : "insecure", origin: location.origin, browser: navigator.userAgent, mediaDevices: !!navigator.mediaDevices, getUserMedia: typeof navigator.mediaDevices?.getUserMedia, nativeBarcodeDetector: typeof window.BarcodeDetector, permission, videoReadyState: $("video").readyState, streamActive: !!$("video").srcObject?.active, decoder: "Existing native retail formats + local ZXing WASM fallback; decoding not established by this diagnostic" };
  $("camera-diagnostics").textContent = JSON.stringify(info, null, 2);
};
try {
  const host = $("bezel"), renderer = new lo({ alpha: true, antialias: true, powerPreference: "low-power" });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.5));
  renderer.domElement.setAttribute("aria-hidden", "true");
  host.append(renderer.domElement);
  const scene = new Ds(), camera = new mi(-1, 1, 1, -1, 0.1, 100);
  camera.position.z = 12;
  const material = new Us({ color: 4875656, metalness: 0.4, roughness: 0.6 });
  const geometry = new Vn(1, 1, 0.18), bars = [];
  for (let i14 = 0; i14 < 4; i14++) {
    const m = new Ie(geometry, material);
    scene.add(m);
    bars.push(m);
  }
  scene.add(new Ys(16777215, 2));
  const light = new qs(14412543, 3);
  light.position.set(-3, 5, 8);
  scene.add(light);
  let frames = 0;
  redraw = () => {
    const r = host.getBoundingClientRect();
    if (!r.width || !r.height) return;
    const w = r.width / 100, h = r.height / 100;
    camera.left = -w / 2;
    camera.right = w / 2;
    camera.top = h / 2;
    camera.bottom = -h / 2;
    camera.updateProjectionMatrix();
    renderer.setSize(r.width, r.height, false);
    bars[0].scale.set(w, 8e-3, 1);
    bars[0].position.set(0, h / 2 - 0.025, 0);
    bars[1].scale.set(w, 8e-3, 1);
    bars[1].position.set(0, -h / 2 + 0.025, 0);
    bars[2].scale.set(8e-3, h, 1);
    bars[2].position.set(-w / 2 + 0.025, 0, 0);
    bars[3].scale.set(8e-3, h, 1);
    bars[3].position.set(w / 2 - 0.025, 0, 0);
    material.color.set(document.documentElement.dataset.theme === "dark" ? 4875656 : 11388901);
    renderer.render(scene, camera);
    host.dataset.renderer = "Three.js r" + Ea;
    host.dataset.renderedFrames = String(++frames);
  };
  const observer = new ResizeObserver(redraw);
  observer.observe(host);
  redraw();
  window.addEventListener("pagehide", () => {
    observer.disconnect();
    geometry.dispose();
    material.dispose();
    renderer.dispose();
  }, { once: true });
} catch (e) {
  $("bezel").dataset.renderer = "CSS fallback \xB7 " + e.name;
}
function viewport() {
  document.documentElement.style.setProperty("--screen", (window.visualViewport?.height || innerHeight) + "px");
}
window.visualViewport?.addEventListener("resize", viewport);
window.addEventListener("resize", viewport);
viewport();
setSheetSnap(0);
render();
var kitchenPrefill = readKitchenPrefill();
if (kitchenPrefill) {
  $("barcode").value = kitchenPrefill.raw;
  $("manual-namespace").value = "barcode";
  $("manual-representation").value = "";
  $("manual-namespace").onchange();
  open("manual-dialog");
  message("Kitchen capture ready \xB7 confirm original " + kitchenPrefill.raw + " for public lookup. No inventory change yet.");
}
void scanner.start();
window.addEventListener("pagehide", () => {
  generation++;
  active = false;
  inventory.destroy();
  guestStorage2.clear();
}, { once: true });
/*! three@0.180.0
The MIT License

Copyright © 2010-2025 three.js authors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

*/
/*! three@0.180.0 MIT https://threejs.org — see scanner-three-LICENSE.txt */
/**
 * @license
 * Copyright 2010-2025 Three.js Authors
 * SPDX-License-Identifier: MIT
 */
