var yl={schema:"offmenu-foundation-handoff-bindings/2",selections:[{releaseId:"offmenu-foundation-production-20261027-v1",manifestSha256:"10f4f5acb9dbab8e5411dc7c7aa9136d6bb6317cd5eb11d9ec6c9ccdd4a1a0db",sourceAdmissionSha256:"fedce50756a6598ee3fc53d6e0507a4d21103711dcaee6911c61679b70cb2cdb",sources:{off:{releaseId:"2026-10-12",qualificationSha256:"96a192c8d7ec08e4116b9c7b1c8fb77da452a22820656fa43ceef1200c96cfc0",license:"ODbL / DbCL; images CC BY-SA",attribution:"Open Food Facts"},"usda-files":{releaseId:"2026-04-30",qualificationSha256:"e648f1d83bb1012e076d43610aa80ed6b811dfa1ff3521d028bcf274923792d9",license:"USDA FoodData Central public domain / CC0 (retained declaration)",attribution:"USDA Agricultural Research Service FoodData Central"}}},{releaseId:"offmenu-reviewed-foundation-r8-local-20261027-v1",manifestSha256:"f9338984eb416c0c4681697c5257ae72cf2e178fe88879331d4b74efc6dc9aa7",sourceAdmissionSha256:"d02e9df26a9469328118cc12321566cc2cef8df2037957372812a1f954439258",sources:{off:{releaseId:"2026-10-12",qualificationSha256:"96a192c8d7ec08e4116b9c7b1c8fb77da452a22820656fa43ceef1200c96cfc0",license:"ODbL / DbCL; images CC BY-SA",attribution:"Open Food Facts"},"usda-files":{releaseId:"2026-04-30",qualificationSha256:"e648f1d83bb1012e076d43610aa80ed6b811dfa1ff3521d028bcf274923792d9",license:"USDA FoodData Central public domain / CC0 (retained declaration)",attribution:"USDA Agricultural Research Service FoodData Central"}}},{releaseId:"offmenu-reviewed-foundation-r2-named-r3-20261027-v1",manifestSha256:"fc2e17c8864cef45b36ad7cfee4a3c0ef15dd73acb8dbe54cf008fca141cd4a7",sourceAdmissionSha256:"de1ae0bf0be081145352f3ddb92a6d2ca1a6df75d0c86bbf608a2835fd334c87",sources:{off:{releaseId:"2026-10-12",qualificationSha256:"96a192c8d7ec08e4116b9c7b1c8fb77da452a22820656fa43ceef1200c96cfc0",license:"ODbL / DbCL; images CC BY-SA",attribution:"Open Food Facts"},"usda-files":{releaseId:"2026-04-30",qualificationSha256:"e648f1d83bb1012e076d43610aa80ed6b811dfa1ff3521d028bcf274923792d9",license:"USDA FoodData Central public domain / CC0 (retained declaration)",attribution:"USDA Agricultural Research Service FoodData Central"}}},{releaseId:"offmenu-reviewed-foundation-r2-20261027-v1",manifestSha256:"9fe0cb763cec1e8b4afee9c77d508f98f15788f1ad4400fb2ecb659b14730acc",sourceAdmissionSha256:"2a29f7f0949d8b41bf60d670d60bcb6651aaaff8f1ab3c7c812f4779d7d0ceb9",sources:{off:{releaseId:"2026-10-12",qualificationSha256:"96a192c8d7ec08e4116b9c7b1c8fb77da452a22820656fa43ceef1200c96cfc0",license:"ODbL / DbCL; images CC BY-SA",attribution:"Open Food Facts"},"usda-files":{releaseId:"2026-04-30",qualificationSha256:"e648f1d83bb1012e076d43610aa80ed6b811dfa1ff3521d028bcf274923792d9",license:"USDA FoodData Central public domain / CC0 (retained declaration)",attribution:"USDA Agricultural Research Service FoodData Central"}}}]};var Sl="offmenu-foundation-source-reference/1",Ha="offmenu-foundation-scanner-handoff/1",Ga=["sourceId","releaseId","recordId","sourceObservationSha256","sourceDocumentSha256","inputDatabaseSha256","sourceQualificationSha256"],Wa=["normalizationComplete","fullProductComplete","goldAdmitted","automaticPlanningEligible","recipeNutritionJoinsAccepted"],wn=/^[a-f0-9]{64}$/,eh=e=>typeof e=="string"&&/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(e),ja=e=>e!==null&&typeof e=="object"&&!Array.isArray(e),er=(e,t)=>typeof e=="string"&&e.length>0&&e.length<=t&&!/[\x00-\x1f\x7f]/.test(e),It=(e,t)=>{if(!e)throw Error(t)},Ki=(e,t)=>ja(e)&&Object.keys(e).length===t.length&&t.every(r=>Object.hasOwn(e,r));function El(e){if(typeof e!="string"||!/^(?:[0-9]{8}|[0-9]{12}|[0-9]{13}|[0-9]{14})$/.test(e))return!1;let t=0,r=3;for(let i=e.length-2;i>=0;i--)t+=Number(e[i])*r,r=r===3?1:3;return(10-t%10)%10===Number(e.at(-1))}function th(e){let t=ja(e)&&e.schema==="offmenu-foundation-handoff-bindings/2";It(!t||Ki(e,["schema","selections"]),"Fixed foundation handoff selections required.");let r=structuredClone(t?e.selections:[e]);It(Array.isArray(r)&&r.length>0&&r.length<=8&&r.every(l=>er(l?.releaseId,128)&&wn.test(l.manifestSha256)&&wn.test(l.sourceAdmissionSha256)&&ja(l.sources)),"Fixed foundation handoff selection required.");let i=l=>JSON.stringify([l.releaseId,l.manifestSha256,l.sourceAdmissionSha256]);It(new Set(r.map(i)).size===r.length,"Foundation handoff selections repeat a cut.");function n(l,d){let h=["schema","fieldContract","releaseId","manifestSha256","sourceAdmissionSha256","recordId","namespace","lexicalValue","nativeRecordId","stageRecordWireSha256","sourceBinding","license","attribution","foundationComplete",...Wa],m=r.find(f=>f.releaseId===l?.releaseId&&f.manifestSha256===l?.manifestSha256&&f.sourceAdmissionSha256===l?.sourceAdmissionSha256);It(m&&Ki(l,h)&&l.schema===Sl&&l.fieldContract==="offmenu-barcode-foundation-phase/2","Foundation source selection changed.");let g=l.sourceBinding,_=m.sources[g?.sourceId];return It(Ki(g,Ga)&&_&&er(g.sourceId,40)&&g.releaseId===_.releaseId&&g.sourceQualificationSha256===_.qualificationSha256&&er(g.recordId,250)&&Ga.slice(3).every(f=>wn.test(g[f])),"Foundation source subject is incomplete."),It(l.namespace==="barcode"&&El(d)&&l.lexicalValue===d&&er(l.recordId,250)&&er(l.nativeRecordId,250)&&l.nativeRecordId.startsWith(g.sourceId+":product:")&&wn.test(l.stageRecordWireSha256),"Foundation exact barcode or wire binding changed."),It(l.license===_.license&&l.attribution===_.attribution&&er(l.license,512)&&er(l.attribution,512)&&l.foundationComplete===!0&&Wa.every(f=>l[f]===!1),"Foundation qualification or source notices changed."),{schema:Sl,fieldContract:l.fieldContract,releaseId:m.releaseId,manifestSha256:m.manifestSha256,sourceAdmissionSha256:m.sourceAdmissionSha256,recordId:l.recordId,namespace:"barcode",lexicalValue:d,nativeRecordId:l.nativeRecordId,stageRecordWireSha256:l.stageRecordWireSha256,sourceBinding:Object.fromEntries(Ga.map(f=>[f,g[f]])),license:l.license,attribution:l.attribution,foundationComplete:!0,...Object.fromEntries(Wa.map(f=>[f,!1]))}}let a=(l,d)=>{try{return n(l,d),!0}catch{return!1}};function o(l){return It(Ki(l,["operationId","barcode","namespace","symbology","name","brand","userSelected","foundationSourceReference"])&&eh(l.operationId)&&l.namespace==="barcode"&&l.userSelected===!0&&El(l.barcode)&&(l.symbology===null||er(l.symbology,128))&&(l.name===null||er(l.name,240))&&(l.brand===null||er(l.brand,240)),"Explicit source choice is required for every kept item."),{operationId:l.operationId,barcode:l.barcode,namespace:"barcode",symbology:l.symbology,name:l.name,brand:l.brand,userSelected:!0,foundationSourceReference:n(l.foundationSourceReference,l.barcode)}}let s=l=>JSON.stringify(o(l));function c(l){It(Ki(l,["schema","items"])&&l.schema===Ha&&Array.isArray(l.items)&&l.items.length>0&&l.items.length<=20,"Foundation scanner handoff is invalid.");let d=l.items.map(o);It(new Set(d.map(m=>m.operationId)).size===d.length,"Scanner handoff repeats an operation.");let h={schema:Ha,items:d};return It(new TextEncoder().encode(JSON.stringify(h)).byteLength<=3e3,"Scanner handoff exceeds the existing tab limit. Review a smaller batch."),h}function u(l){return It(Array.isArray(l)&&l.length>0,"Scan at least one item before finishing."),c({schema:Ha,items:l.map(d=>{let h=d?.selectedRecord;return It(d.foundationLookup===!0&&d.namespace==="barcode"&&d.sourceChoiceConfirmed===!0&&d.status!=="pending"&&d.pending!==!0&&d.lookupPending!==!0&&d.matches?.includes(h),"Choose and confirm a qualified source observation for every kept item."),{operationId:d.id,barcode:d.raw,namespace:"barcode",symbology:d.symbology??null,name:h.name??null,brand:h.brand??null,userSelected:!0,foundationSourceReference:h.foundationSourceReference}})})}return Object.freeze({validFoundationSourceReference:a,copyFoundationSourceReference:n,foundationHandoffFingerprint:s,parseFoundationScannerHandoff:c,createFoundationScannerHandoff:u})}var rh=th(yl),{validFoundationSourceReference:Xa,copyFoundationSourceReference:Ji,foundationHandoffFingerprint:ih,parseFoundationScannerHandoff:db,createFoundationScannerHandoff:Tl}=rh;var nh="offmenu-typed-identifier/1",pb=Object.freeze({upce:"https://ref.gs1.org/guidelines/2d-in-retail/1.0.0/",jan:"https://www.gs1jp.org/standard/barcode/jan_symbol.html",itf14:"https://support.gs1.org/support/solutions/articles/43000734528-what-type-of-gtin-can-be-encoded-in-itf-14-",packaging:"https://www.gs1uk.org/knowledge-hub/product-identification/how-do-i-identify-packaging-levels",isbnGS1:"https://support.gs1.org/support/solutions/articles/43000734165-how-is-an-isbn-used-in-a-gs1-barcode-",isbnAgency:"https://www.isbn-international.org/content/what-isbn/10"}),ah=Object.freeze(["GTIN-8","GTIN-12","GTIN-13","GTIN-14","EAN-8","EAN-13","UPC-A","UPC-E","JAN","JAN-8","JAN-13","ISBN-10","ISBN-13"]),wl=Object.freeze({"GTIN-8":8,"EAN-8":8,"GTIN-12":12,"UPC-A":12,"GTIN-13":13,"EAN-13":13,"GTIN-14":14}),Ml=Object.freeze({"EAN-8":"EAN-8",EAN8:"EAN-8",ean_8:"EAN-8","EAN-13":"EAN-13",EAN13:"EAN-13",ean_13:"EAN-13","UPC-A":"UPC-A",UPCA:"UPC-A",upc_a:"UPC-A","UPC-E":"UPC-E",UPCE:"UPC-E",upc_e:"UPC-E","ITF-14":"GTIN-14",ITF14:"GTIN-14"}),Rl=e=>typeof e=="string"&&/^[0-9]+$/.test(e);function Cl(e){let t=0;for(let r=e.length-1,i=3;r>=0;r--,i=4-i)t+=Number(e[r])*i;return String((10-t%10)%10)}function fr(e){return Rl(e)&&[8,12,13,14].includes(e.length)&&Cl(e.slice(0,-1))===e.at(-1)}function Il(e){if(typeof e!="string"||!/^[0-9]{9}[0-9X]$/.test(e))return!1;let t=0;for(let r=0;r<10;r++)t+=(e[r]==="X"?10:Number(e[r]))*(10-r);return t%11===0}function Nl(e){return typeof e=="string"&&/^(978|979)[0-9]{10}$/.test(e)&&fr(e)}function Zi(e){if(typeof e!="string"||!/^[01][0-9]{7}$/.test(e))return null;let[t,r,i,n,a,o,s,c]=e,u=s<="2"?t+r+i+s+"0000"+n+a+o+c:s==="3"?t+r+i+n+"00000"+a+o+c:s==="4"?t+r+i+n+a+"00000"+o+c:t+r+i+n+a+o+"0000"+s+c;return fr(u)?u:null}function oh(e){if(!Il(e))return null;let t="978"+e.slice(0,9);return t+Cl(t)}function sh(e){if(!Nl(e))return Object.freeze({status:"invalid",value:null,allocationStatus:"not-verified"});if(e.startsWith("979"))return Object.freeze({status:"no-equivalent",value:null,allocationStatus:"not-verified"});let t=e.slice(3,12),r=0;for(let n=0;n<9;n++)r+=Number(t[n])*(10-n);let i=(11-r%11)%11;return Object.freeze({status:"converted",value:t+(i===10?"X":String(i)),allocationStatus:"not-verified"})}function lh(e){return e==="JAN-8"?Object.freeze({naming:"JAN-8",representation:"EAN-8",countryOfManufacture:null}):e==="JAN-13"?Object.freeze({naming:"JAN-13",representation:"EAN-13",countryOfManufacture:null}):e==="JAN"?Object.freeze({naming:"JAN",representation:null,countryOfManufacture:null}):null}function ch(e){return typeof e=="string"&&Object.hasOwn(Ml,e)?Ml[e]:null}function Al(e){return e==="UPC-E"?"UPC-E":e==="ISBN-10"?"ISBN-10":e==="ISBN-13"?13:wl[e]??null}function Rn(e,t){if(e==null)return null;if(typeof e!="string")throw new TypeError(t+" must be a string or null");return e}function uh(e){return e.labelledEquivalents=Object.freeze(e.labelledEquivalents.map(Object.freeze)),e.possibleRepresentations=Object.freeze(e.possibleRepresentations.map(Object.freeze)),Object.freeze(e)}function Pl(e){if(!e||typeof e!="object"||Array.isArray(e))throw new TypeError("input must be an object");if(typeof e.original!="string"||!e.original.length)throw new TypeError("original must be a nonempty string");if(typeof e.namespace!="string"||!e.namespace.length)throw new TypeError("namespace must be explicit and nonempty");let t=Rn(e.representationHint,"representationHint"),r=Rn(e.observedCarrier,"observedCarrier"),i=lh(t),n=ch(r),a=i?i.representation:t??n,o={contractVersion:nh,original:e.original,namespace:e.namespace,sourceLexicalValue:Rn(e.sourceLexicalValue,"sourceLexicalValue"),sourceId:Rn(e.sourceId,"sourceId"),lookupOriginal:e.original,lookupContract:"caller-owned",requestedHint:t,effectiveHint:a,observedCarrier:r,hintOrigin:t!==null?"explicit":n?"decoder-label":"none",namingRelationship:i,countryOfManufacture:null,status:"untyped",reason:"explicit-representation-required",syntaxValid:null,checksumValid:null,validatedRepresentation:null,comparisonGTIN14:null,gtin14LeadingDigit:null,packagingRelationship:"not-established",labelledEquivalents:[],possibleRepresentations:[],isbn10Equivalent:null,isbn10Availability:"not-applicable",allocationStatus:"not-verified",catalogueStatus:"not-queried",physicalCarrierStatus:r===null?"unobserved":"caller-label-only",productIdentityAsserted:!1,ingredientClassification:"not-assessed"},s=()=>uh(o),c=(l,d,h)=>{l!==e.original&&!o.labelledEquivalents.some(m=>m.value===l&&m.representation===d)&&o.labelledEquivalents.push({value:l,representation:d,rule:h})};if(t!==null&&!ah.includes(t))return o.status="invalid",o.reason="unsupported-representation-hint",s();if(t==="JAN")return o.status="hint-required",o.reason="choose-JAN-8-or-JAN-13-explicitly",s();if(a===null)return r==="ITF"||r==="itf"?o.reason="generic-ITF-does-not-declare-GTIN":/^[0-9]{8}$/.test(e.original)&&(o.status="ambiguous",o.reason="eight-digits-do-not-select-EAN-8-or-UPC-E",o.possibleRepresentations=[{representation:"EAN-8",checksumCompatible:fr(e.original)},{representation:"UPC-E",checksumCompatible:Zi(e.original)!==null}]),s();if(t!==null&&n&&Al(a)!==Al(n))return o.status="conflict",o.reason="explicit-hint-conflicts-with-decoder-label",s();let u=null;if(a==="ISBN-10")o.syntaxValid=/^[0-9]{9}[0-9X]$/.test(e.original),o.checksumValid=o.syntaxValid?Il(e.original):null,o.checksumValid&&(u=oh(e.original),o.validatedRepresentation="ISBN-10",o.isbn10Equivalent=e.original,o.isbn10Availability="original",c(u,"ISBN-13","validated-ISBN-10-to-978-ISBN-13"));else if(a==="ISBN-13"){if(o.syntaxValid=/^(978|979)[0-9]{10}$/.test(e.original),o.checksumValid=o.syntaxValid?Nl(e.original):null,o.checksumValid){u=e.original,o.validatedRepresentation="ISBN-13";let l=sh(e.original);o.isbn10Availability=l.status,o.isbn10Equivalent=l.value,l.value&&c(l.value,"ISBN-10","validated-978-ISBN-13-to-ISBN-10")}}else if(a==="UPC-E")o.syntaxValid=/^[01][0-9]{7}$/.test(e.original),u=o.syntaxValid?Zi(e.original):null,o.checksumValid=o.syntaxValid?u!==null:null,u&&(o.validatedRepresentation="UPC-E",c(u,"GTIN-12","explicit-UPC-E-to-GTIN-12"),c("0"+u,"EAN-13","GTIN-12-as-leading-zero-EAN-13"));else{let l=wl[a];o.syntaxValid=!!l&&Rl(e.original)&&e.original.length===l,o.checksumValid=o.syntaxValid?fr(e.original):null,o.checksumValid&&(u=e.original,o.validatedRepresentation="GTIN-"+l,l===12&&c("0"+u,"EAN-13","GTIN-12-as-leading-zero-EAN-13"),l===13&&u.startsWith("0")&&c(u.slice(1),"GTIN-12","leading-zero-EAN-13-as-GTIN-12"),l===14&&(o.gtin14LeadingDigit=u[0]))}return o.checksumValid?(o.status="checksum-valid",o.reason="typed-syntax-and-checksum-only",o.comparisonGTIN14=u.padStart(14,"0"),s()):(o.status="invalid",o.reason=o.syntaxValid?"checksum-invalid":"representation-syntax-invalid",s())}var $i=/^[a-f0-9]{64}$/,qa=e=>e!==null&&typeof e=="object"&&!Array.isArray(e),mi=e=>typeof e=="string"&&e.length>0&&e.length<=512&&!/[\x00-\x1f\x7f]/.test(e),Cn=["sourceId","releaseId","recordId","sourceObservationSha256","sourceDocumentSha256","inputDatabaseSha256","sourceQualificationSha256"],dh=[...Cn,"nativeRecordId"],Ol=["canonicalIdentityAccepted","identityAssociationAccepted","physicalProductEquivalenceAsserted","normalizationComplete","goldAdmitted","automaticPlanningEligible","recipeNutritionJoinsAccepted"],Ll=["originalProductName","originalLanguage","englishName","foodType","nutrition"],hh=["schema","stageId","nativeId","wireSha256","sourceBinding","sourceIdentifiers","sourceRights","matchedIdentifier","sourceInputIndexSha256","rightsVisibilityField","sourceURL",...Ll,...Ol],ph=["status","sourceId","namespace","lexicalValue","manifestSha256","totalSourceObservations","nextOffset","records","externalFallback","publicPublicationAccepted","normalizationComplete","goldAdmitted"];function _t(e,t="SOURCE_IDENTITY_RESPONSE_MISMATCH"){if(!e)throw Error(t)}var mr=(e,t)=>qa(e)&&Object.keys(e).length===t.length&&t.every(r=>Object.hasOwn(e,r));function gi(e){return _t(qa(e)&&Cn.every(t=>mi(e[t]))&&Cn.filter(t=>t.endsWith("Sha256")).every(t=>$i.test(e[t]))),JSON.stringify(Cn.map(t=>e[t]))}function In(e){return _t(mr(e,["selectionSha256","admissionSha256","manifestSha256","sourceId","releaseId","sourceQualificationSha256","sourceInputIndexSha256s"]),"SOURCE_IDENTITY_NOT_CONFIGURED"),_t(["selectionSha256","admissionSha256","manifestSha256","sourceQualificationSha256"].every(t=>$i.test(e[t]))&&e.sourceId==="usda-files"&&e.releaseId==="2026-04-30"&&Array.isArray(e.sourceInputIndexSha256s)&&e.sourceInputIndexSha256s.length>0&&e.sourceInputIndexSha256s.length<=16&&e.sourceInputIndexSha256s.every(t=>$i.test(t))&&new Set(e.sourceInputIndexSha256s).size===e.sourceInputIndexSha256s.length,"SOURCE_IDENTITY_NOT_CONFIGURED"),structuredClone(e)}function Ya(e,t,r){let i=In(r);_t(qa(t)&&["barcode","USDA-FDC"].includes(t.namespace)&&mi(t.value)&&Number.isSafeInteger(t.offset)&&t.offset>=0&&t.offset<=1e4&&Number.isSafeInteger(t.limit)&&t.limit>0&&t.limit<=20),_t(mr(e,["schema","kind","httpStatus","selectionSha256","admissionSha256","readerResult","status"])&&e.schema==="offmenu-source-identity-http/1"&&e.kind==="source-identifier-claims"&&e.httpStatus===200&&e.selectionSha256===i.selectionSha256&&e.admissionSha256===i.admissionSha256);let n=e.readerResult;_t(mr(n,ph)&&n.sourceId===i.sourceId&&n.namespace===t.namespace&&n.lexicalValue===t.value&&n.manifestSha256===i.manifestSha256&&["externalFallback","publicPublicationAccepted","normalizationComplete","goldAdmitted"].every(s=>n[s]===!1)),_t(Number.isSafeInteger(n.totalSourceObservations)&&n.totalSourceObservations>=0&&n.totalSourceObservations<=1e4&&Array.isArray(n.records)&&n.records.length<=t.limit);let a=Math.min(t.limit,Math.max(0,n.totalSourceObservations-t.offset));_t(n.records.length===a&&e.status===n.status&&n.status===(n.totalSourceObservations>0?"source-identity-claims-found":"no-selected-source-identity")),_t(n.nextOffset===(t.offset+n.records.length<n.totalSourceObservations?t.offset+n.records.length:null));let o=new Set;for(let s of n.records){_t(mr(s,hh)&&s.schema==="offmenu-source-identity-observation/2"&&mi(s.stageId)&&mi(s.nativeId)&&$i.test(s.wireSha256)&&$i.test(s.sourceInputIndexSha256)&&i.sourceInputIndexSha256s.includes(s.sourceInputIndexSha256)&&["visibility","sourceVisibility"].includes(s.rightsVisibilityField));let c=s.sourceBinding;_t(mr(c,dh)&&c.sourceId===i.sourceId&&c.releaseId===i.releaseId&&c.nativeRecordId===s.nativeId&&c.sourceQualificationSha256===i.sourceQualificationSha256),gi(c),_t(mr(s.sourceRights,["license","attribution","sourceVisibility"])&&s.sourceRights.license==="USDA FoodData Central public domain / CC0 (retained declaration)"&&s.sourceRights.attribution==="USDA Agricultural Research Service FoodData Central"&&s.sourceRights.sourceVisibility==="source-staging"&&s.sourceURL==="https://fdc.nal.usda.gov/download-datasets/"),_t(Array.isArray(s.sourceIdentifiers)&&s.sourceIdentifiers.length>0&&s.sourceIdentifiers.length<=16&&s.sourceIdentifiers.every(d=>mr(d,["system","value"])&&["barcode","USDA-FDC"].includes(d.system)&&mi(d.value))&&s.sourceIdentifiers.some(d=>d.system==="USDA-FDC"&&d.value===c.recordId));let u=s.matchedIdentifier;_t(mr(u,["namespace","lexicalValue","relationship","representation","physicalCarrier","sourceChecksumValid"])&&u.namespace===t.namespace&&u.lexicalValue===t.value&&u.relationship==="exact-source-claim"&&u.representation==="untyped"&&u.physicalCarrier===(t.namespace==="barcode"?"unverified":"not-applicable")&&(t.namespace==="barcode"?typeof u.sourceChecksumValid=="boolean"&&u.sourceChecksumValid===fr(t.value):u.sourceChecksumValid===null)&&s.sourceIdentifiers.some(d=>d.system===t.namespace&&d.value===t.value)),_t(Ll.every(d=>mr(s[d],["state","reason"])&&s[d].state==="unknown"&&s[d].reason==="not-in-qualified-identity-metadata")&&Ol.every(d=>s[d]===!1));let l=JSON.stringify([s.stageId,gi(c)]);_t(!o.has(l)),o.add(l)}return structuredClone(n)}function Ul({selection:e,fetchImpl:t=globalThis.fetch}={}){let r;try{r=In(e)}catch{}return async function(n,a,o="barcode",s=0,c=20){let u=h=>({identityLookup:!0,sourceId:"usda-files",namespace:o,lexicalValue:n,generation:a,requestOffset:s,records:[],nextOffset:null,error:h});if(!r)return u("SOURCE_IDENTITY_NOT_CONFIGURED");if(!mi(n)||!["barcode","USDA-FDC"].includes(o)||!Number.isSafeInteger(a)||!Number.isSafeInteger(s)||s<0||s>1e4||!Number.isSafeInteger(c)||c<1||c>20)return u("SOURCE_IDENTITY_QUERY_UNAVAILABLE");let l={namespace:o,value:n,offset:s,limit:c},d=new URL("/api/corpus/source-identity","http://local.invalid");for(let[h,m]of Object.entries({source:"usda-files",namespace:o,value:n,offset:s,limit:c}))d.searchParams.set(h,String(m));try{let h=await t(d.pathname+d.search,{method:"GET",credentials:"omit",cache:"no-store",redirect:"error",mode:"same-origin",headers:{Accept:"application/json"}});if(h.status!==200)return{...u(h.status===403?"SOURCE_IDENTITY_ACCESS_UNAVAILABLE":h.status===400?"SOURCE_IDENTITY_QUERY_UNAVAILABLE":"SOURCE_IDENTITY_SERVICE_UNAVAILABLE"),httpStatus:h.status};let m=await h.text();return _t(new TextEncoder().encode(m).length<=2097152),{...Ya(JSON.parse(m),l,r),identityLookup:!0,generation:a,requestOffset:s,selectionSha256:r.selectionSha256,admissionSha256:r.admissionSha256,error:null}}catch{return u("SOURCE_IDENTITY_RESPONSE_UNAVAILABLE")}}}function vi(e){return{kind:"source-identity",id:JSON.stringify(["source-identity",e.stageId,gi(e.sourceBinding)]),name:null,brand:null,sourceIdentityRecord:structuredClone(e),provenance:{...structuredClone(e.sourceBinding),license:e.sourceRights.license,attribution:e.sourceRights.attribution},sourceObservationReference:null}}function Ka(e){let t=e?.sourceIdentityRecord;return t?"USDA-FDC \xB7 "+t.sourceBinding.recordId:"Name not available"}function Ja(e,t,r="overview"){let i=e.sourceIdentityRecord,n=[{label:"Source record",text:"USDA-FDC \xB7 "+i.sourceBinding.recordId},{label:"Identifiers",text:i.sourceIdentifiers.map(a=>a.system+" \xB7 "+a.value).join(" / ")},{label:"Source",text:i.sourceBinding.sourceId+" \xB7 "+i.sourceBinding.releaseId}];for(let[a,o]of[["originalProductName","Product name"],["originalLanguage","Language"],["englishName","English name"],["foodType","Food type"],["nutrition","Nutrition"]])n.push({label:o,text:"Unknown \xB7 not supplied by this source identity view"});return n.push({label:"Licence and credits",text:i.sourceRights.attribution+" \xB7 "+i.sourceRights.license},{label:"Source URL",text:i.sourceURL},{label:"About this record",text:"Source identifier claims only. Product identity, food classification and inventory eligibility have not been established."}),i.matchedIdentifier.namespace==="barcode"&&n.push({label:"Source barcode claim",text:i.matchedIdentifier.lexicalValue+" \xB7 "+(i.matchedIdentifier.sourceChecksumValid?"checksum valid; physical carrier unverified":"invalid checksum; source claim retained without correction")}),t.phaseTechnicalFailure&&n.push({label:"Lookup status",text:"Some product details could not be checked. This source record does not resolve that lookup failure."}),t.identityState?.error&&n.push({label:"Source lookup",text:"Additional source records could not be checked right now."}),r==="source"&&n.push({label:"Source record reference",text:JSON.stringify({stageId:i.stageId,nativeId:i.nativeId,wireSha256:i.wireSha256,sourceBinding:i.sourceBinding,sourceInputIndexSha256:i.sourceInputIndexSha256})}),n}function Za(e){let t=e?.identityState;return t?t.error?[{label:"Source lookup",text:{SOURCE_IDENTITY_NOT_CONFIGURED:"Additional source records are not enabled in this view.",SOURCE_IDENTITY_ACCESS_UNAVAILABLE:"Source records could not be accessed.",SOURCE_IDENTITY_QUERY_UNAVAILABLE:"This source identifier could not be checked.",SOURCE_IDENTITY_SERVICE_UNAVAILABLE:"Source records are unavailable right now.",SOURCE_IDENTITY_RESPONSE_UNAVAILABLE:"Source records could not be verified right now."}[t.error]||"Source records are unavailable right now."}]:t.records.length?[]:[{label:"Source lookup",text:"No exact source record was returned by this selected view. Other records may not be covered."}]:[]}var $a="offmenu-source-identity-reference/1",Qa="offmenu-owned-source-scanner-handoff/1",Dl=64*1024,Fl=e=>e!==null&&typeof e=="object"&&!Array.isArray(e),Nn=(e,t)=>typeof e=="string"&&e.length>0&&e.length<=t&&!/[\x00-\x1f\x7f]/.test(e),fh=e=>typeof e=="string"&&/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(e),eo=(e,t)=>Fl(e)&&Object.keys(e).length===t.length&&t.every(r=>Object.hasOwn(e,r)),_i=e=>Array.isArray(e)?"["+e.map(_i).join(",")+"]":Fl(e)?"{"+Object.keys(e).sort().map(t=>JSON.stringify(t)+":"+_i(e[t])).join(",")+"}":JSON.stringify(e),tr=(e,t)=>{if(!e)throw Error(t)};function mh(e,{copyFoundation:t=Ji}={}){let r=null;try{r=In(e)}catch{}function i(u,l,d=u?.observation?.matchedIdentifier?.namespace){tr(r,"SOURCE_IDENTITY_NOT_CONFIGURED"),tr(eo(u,["schema","selectionSha256","admissionSha256","manifestSha256","observation"])&&u.schema===$a&&u.selectionSha256===r.selectionSha256&&u.admissionSha256===r.admissionSha256&&u.manifestSha256===r.manifestSha256,"Source identity selection changed.");let h="source-identity-claims-found",m=Ya({schema:"offmenu-source-identity-http/1",kind:"source-identifier-claims",httpStatus:200,status:h,selectionSha256:r.selectionSha256,admissionSha256:r.admissionSha256,readerResult:{status:h,sourceId:r.sourceId,namespace:d,lexicalValue:l,manifestSha256:r.manifestSha256,totalSourceObservations:1,nextOffset:null,records:[u.observation],externalFallback:!1,publicPublicationAccepted:!1,normalizationComplete:!1,goldAdmitted:!1}},{namespace:d,value:l,offset:0,limit:1},r);return{schema:$a,selectionSha256:r.selectionSha256,admissionSha256:r.admissionSha256,manifestSha256:r.manifestSha256,observation:JSON.parse(_i(m.records[0]))}}function n(u){let l=u.selectedRecord?.sourceIdentityRecord,d=u.identityState;return tr(d&&d.namespace===u.namespace&&d.lexicalValue===u.raw&&d.generation===(u.queryGeneration??u.generation)&&Array.isArray(d.records)&&d.records.some(h=>_i(h)===_i(l)),"Selected source observation is not in this lookup."),i({schema:$a,selectionSha256:d.selectionSha256,admissionSha256:d.admissionSha256,manifestSha256:d.manifestSha256,observation:l},u.raw,u.namespace)}function a(u){let l=Object.hasOwn(u??{},"sourceIdentityReference"),d=l?"sourceIdentityReference":"foundationSourceReference";tr(eo(u,["operationId","barcode","namespace","symbology","name","brand","userSelected",d])&&fh(u.operationId)&&Nn(u.barcode,512)&&u.userSelected===!0&&(u.symbology===null||Nn(u.symbology,128))&&(u.name===null||Nn(u.name,240))&&(u.brand===null||Nn(u.brand,240)),"Explicit source choice is required for every kept item."),tr(l?["barcode","USDA-FDC"].includes(u.namespace)&&u.name===null&&u.brand===null:u.namespace==="barcode","Source identity must not acquire a product name or type.");let h=l?i(u[d],u.barcode,u.namespace):t(u[d],u.barcode);return{operationId:u.operationId,barcode:u.barcode,namespace:u.namespace,symbology:u.symbology,name:u.name,brand:u.brand,userSelected:!0,[d]:h}}let o=u=>_i(a(u));function s(u){tr(eo(u,["schema","items"])&&u.schema===Qa&&Array.isArray(u.items)&&u.items.length>0&&u.items.length<=20,"Owned source scanner handoff is invalid.");let l=u.items.map(a);tr(new Set(l.map(h=>h.operationId)).size===l.length,"Scanner handoff repeats an operation.");let d={schema:Qa,items:l};return tr(new TextEncoder().encode(JSON.stringify(d)).byteLength<=Dl,"Source handoff exceeds the bounded tab payload. Nothing was dropped."),d}function c(u){return tr(Array.isArray(u)&&u.length>0,"Scan at least one item before finishing."),s({schema:Qa,items:u.map(l=>{let d=l?.selectedRecord;tr(l.foundationLookup===!0&&l.sourceChoiceConfirmed===!0&&l.status!=="pending"&&l.pending!==!0&&l.lookupPending!==!0&&l.matches?.includes(d),"Choose and confirm a source observation for every kept item.");let h=d.kind==="source-identity";return{operationId:l.id,barcode:l.raw,namespace:l.namespace,symbology:l.symbology??null,name:h?null:d.name??null,brand:h?null:d.brand??null,userSelected:!0,...h?{sourceIdentityReference:n(l)}:{foundationSourceReference:d.foundationSourceReference}}})})}return Object.freeze({copySourceIdentityReference:i,ownedSourceHandoffFingerprint:o,parseOwnedSourceScannerHandoff:s,createOwnedSourceScannerHandoff:c})}var gh=mh(null),{copySourceIdentityReference:vh,ownedSourceHandoffFingerprint:_h,parseOwnedSourceScannerHandoff:yb,createOwnedSourceScannerHandoff:kl}=gh;var bh="97c2f7390f75d8d187b49c927652515cd829e095301d7b305a0081120c7502f0",xh="worker57-full-retained-identifiers-v1",yh="d9a08c3b2b9eec880418b8108d60c177a253b53802e8ea0453eb8fd502498290",Sh=new Set(["source-asserted","unresolved","invalid"]),Eh=new Set(["barcode","USDA-FDC"]),Th=new Set(["EAN-13","EAN-8","UPC-A","UPC-E","GTIN-14"]);var Pn=(e,t)=>typeof e=="string"&&e.length>0&&e.length<=t;function ro(e){if(!/^(?:\d{8}|\d{12}|\d{13}|\d{14})$/.test(e))return!1;let t=0;for(let r=e.length-2,i=3;r>=0;r--,i=4-i)t+=Number(e[r])*i;return(10-t%10)%10===Number(e.at(-1))}function Mh(e,t=null,r="barcode"){let i=[{lexicalValue:e,matchType:"exact",equivalence:null}];if(r!=="barcode")return i;let n=(o,s)=>{i.some(c=>c.lexicalValue===o)||i.push({lexicalValue:o,matchType:"representation-alias",equivalence:s})},a=e;if(t==="UPC-E"){if(!/^[01]\d{7}$/.test(e))return i;let[o,s,c,u,l,d,h,m]=e;if(a=h<="2"?o+s+c+h+"0000"+u+l+d+m:h==="3"?o+s+c+u+"00000"+l+d+m:h==="4"?o+s+c+u+l+"00000"+d+m:o+s+c+u+l+d+"0000"+h+m,!ro(a))return i;n(a,"explicit-upc-e-to-upc-a")}return ro(a)&&(a.length===12&&(!t||t==="UPC-A"||t==="UPC-E")?n("0"+a,"upc-a-as-leading-zero-ean-13"):a.length===13&&a[0]==="0"&&(!t||t==="EAN-13")&&n(a.slice(1),"leading-zero-ean-13-as-upc-a")),i}function Qi(e,t){let r=e?.observationKey,i=Mh(t,e?.symbology,e?.namespace).find(n=>n.lexicalValue===e?.sourceLexicalValue);return e?.schema==="offmenu-identifier-observation/2"&&e.databaseSha256===bh&&e.runId===xh&&Eh.has(e.namespace)&&e.originalLexicalValue===t&&Pn(e.sourceId,40)&&(e.releaseId===null||Pn(e.releaseId,80))&&(e.sourceRecordId===null||Pn(e.sourceRecordId,200))&&(e.symbology===null||e.namespace==="barcode"&&Th.has(e.symbology))&&Sh.has(e.disposition)&&i?.matchType===e.matchType&&i?.equivalence===e.equivalence&&r?.run_id===e.runId&&Pn(r.input_id,250)&&Number.isSafeInteger(r.record_ordinal)&&r.record_ordinal>=0&&Number.isSafeInteger(r.assertion_id)&&r.assertion_id>0&&e.detailSelectionSha256===yh}var Ah="offmenu-source-classification-relationships/1",wh=new Set(["ingredient","type","nonfood","not-applicable","unresolved","conflict"]),Vl=e=>typeof e=="string"&&/^[0-9a-f]{64}$/.test(e),gr=e=>typeof e=="string"&&e.length>0,vr=e=>e!==null&&typeof e=="object"&&!Array.isArray(e)&&[Object.prototype,null].includes(Object.getPrototypeOf(e)),Bl=e=>vr(e)&&gr(e.path)&&Vl(e.sha256)&&Object.keys(e).length===2;function io(e){return e===null||typeof e=="string"||typeof e=="boolean"?!0:typeof e=="number"?Number.isFinite(e):Array.isArray(e)?e.every(io)&&Object.keys(e).length===e.length:vr(e)&&Object.values(e).every(io)}function no(e){if(!vr(e)||!vr(e.sourceBinding)||e.schema!==Ah||!gr(e.sourceBinding.sourceRecordId)||!Vl(e.sourceBinding.snapshotSha256))throw Error("Exact source record/snapshot binding required");let t=e.classification;if(!vr(t)||!wh.has(t.disposition)||!Array.isArray(t.reasonCodes)||!t.reasonCodes.every(gr)||!Array.isArray(t.evidenceRefs)||!t.evidenceRefs.every(r=>vr(r)&&gr(r.assertionId)&&Bl(r.admission))||!Array.isArray(e.relationships)||!e.relationships.every(vr))throw Error("Explicit classification disposition/evidence required");if(typeof t.identityEquivalence!="boolean"||![t.canonicalId,t.idScope,t.relation].every(r=>r===null||gr(r)))throw Error("Explicit typed ID/scope/relation/identity state required");if(e.sourceBinding.sourceObservationReference!==void 0&&e.sourceBinding.sourceObservationReference!==null&&!vr(e.sourceBinding.sourceObservationReference))throw Error("Observation reference must retain an object or null");if(!["applicable","nonfood","not-applicable","unresolved","conflict"].includes(t.ingredientApplicability))throw Error("Explicit ingredient applicability required");if(t.disposition==="ingredient"&&t.ingredientApplicability!=="applicable")throw Error("Nonfood cannot become an ingredient");if(["nonfood","not-applicable","unresolved","conflict"].includes(t.disposition)&&t.ingredientApplicability!==t.disposition)throw Error("Disposition/applicability conflict");if(["ingredient","type"].includes(t.disposition)&&(!gr(t.canonicalId)||!gr(t.idScope)||!gr(t.relation)))throw Error("Supported ID requires explicit identity scope and relation");if(["unresolved","conflict","not-applicable","nonfood"].includes(t.disposition)&&t.canonicalId!==null)throw Error("Do not force an ingredient/type ID for unresolved/nonfood/not-applicable/conflict");if(t.disposition!=="unresolved"&&t.disposition!=="conflict"&&(!t.evidenceRefs.length||!t.evidenceRefs.every(r=>gr(r.assertionId)&&Bl(r.admission))))throw Error("Positive/nonfood/not-applicable decisions require qualified evidence and admission references");if(["unresolved","conflict","nonfood","not-applicable"].includes(t.disposition)&&!t.reasonCodes.length)throw Error("Unresolved/conflict/nonfood/not-applicable reason required");if(t.relation==="represents"&&t.identityEquivalence!==!1)throw Error("Scoped class membership is not identity equivalence");if(e.visualClassification!==null&&!vr(e.visualClassification))throw Error("Visual contract is separately bound or null");if(!io(e))throw Error("Finite JSON data required; no silent coercion or dropped evidence");return e}var Rh=e=>e!==null&&typeof e=="object"&&!Array.isArray(e),Nb=new TextEncoder;var Ch={name:"name",names:"names",brand:"brand",packageQuantity:"pack",servingQuantity:"serving",dataType:"dataType",ingredientDeclaration:"ingredientsText",categories:"categories",sourceAllergenClaims:"allergens",sourceTraceClaims:"traces",sourceDietaryLabelClaims:"labels",origins:"origins",manufacturingPlaces:"manufacturingPlaces",rawNutriments:"rawNutriments",nutritionSourceBasis:"nutritionSourceBasis",nutrientProfile:"nutrientProfile",imageUrlReferences:"imageUrlReferences"},Pb=[...Object.keys(Ch),"markets","sourceProvenance"];function zl(e,t){let r=[];e?.sourceAssertionAvailability?.state==="unavailable"&&r.push({label:"Additional source facts",text:"Unavailable in this response. The published barcode record is still shown; no source absence is established."});let i=a=>a==null?"Unknown":Array.isArray(a)?a.length?a.map(i).join(", "):"No values in this projection; original presence unknown":Rh(a)?Object.entries(a).filter(([,o])=>o!=null).map(([o,s])=>o+": "+i(s)).join(" \xB7 ")||"Unknown":String(a),n=a=>a?a.state==="present"?i(a.value):a.state==="null"?"Unknown in this source projection":a.state==="not-loaded"?"Not loaded":a.state==="not-applicable"?"Not applicable as explicitly supplied by this source":["unknown","unresolved"].includes(a.state)?"Unresolved in this source projection":["restricted","rights-held"].includes(a.state)?"Not available for display":"Not supplied in this projection":"Not captured; original presence unknown";for(let a of e?.sourceAssertions||[]){let o=a.sourceObservationReference,s=a.fields.sourceProvenance?.value?.attribution||o.sourceId,c="Separate source \xB7 "+s+" \xB7 "+o.releaseId;r.push({label:c,text:"Same barcode; product variant match is unverified. These facts are shown separately."});let u=a.classificationProjection.classification;r.push({label:c+" \xB7 source classification",text:u.disposition+" \xB7 ingredient applicability: "+u.ingredientApplicability+" \xB7 scope: "+(u.idScope||"unresolved")});let l=t==="nutrition"?["nutritionSourceBasis","nutrientProfile","rawNutriments"]:t==="ingredients"?["ingredientDeclaration","sourceAllergenClaims","sourceTraceClaims"]:t==="source"?Object.keys(a.fields):["name","brand","markets","categories","sourceAllergenClaims","sourceTraceClaims","sourceDietaryLabelClaims"];for(let d of l){let h=a.fields[d];if(!h){r.push({label:c+" \xB7 "+d,text:"Not captured in this selected representation; original presence unknown."});continue}if(r.push({label:c+" \xB7 "+d,text:t==="source"?JSON.stringify(h):d==="nutrientProfile"&&h.state==="present"?"Projected profile basis: "+i(h.value?.basis):n(h)}),d==="nutrientProfile"&&h.state==="present")for(let[m,g]of Object.entries(h.value?.nutrients||{}))r.push({label:c+" \xB7 "+m,text:(g.value==null?"Unknown \xB7 not zero":i(g.value)+" "+(g.unit||"unit unknown"))+" \xB7 basis: "+i(g.basis)+" \xB7 method: "+i(g.method)})}t==="source"&&r.push({label:c+" \xB7 exact source binding",text:JSON.stringify({sourceObservationReference:o,binding:a.binding})}),t==="nutrition"&&r.push({label:c+" \xB7 basis distinction",text:a.nutritionBasisRelationship})}return r}var Ih="offmenu-typed-identifier/1",Lb=Object.freeze({upce:"https://ref.gs1.org/guidelines/2d-in-retail/1.0.0/",jan:"https://www.gs1jp.org/standard/barcode/jan_symbol.html",itf14:"https://support.gs1.org/support/solutions/articles/43000734528-what-type-of-gtin-can-be-encoded-in-itf-14-",packaging:"https://www.gs1uk.org/knowledge-hub/product-identification/how-do-i-identify-packaging-levels",isbnGS1:"https://support.gs1.org/support/solutions/articles/43000734165-how-is-an-isbn-used-in-a-gs1-barcode-",isbnAgency:"https://www.isbn-international.org/content/what-isbn/10"}),Nh=Object.freeze(["GTIN-8","GTIN-12","GTIN-13","GTIN-14","EAN-8","EAN-13","UPC-A","UPC-E","JAN","JAN-8","JAN-13","ISBN-10","ISBN-13"]),jl=Object.freeze({"GTIN-8":8,"EAN-8":8,"GTIN-12":12,"UPC-A":12,"GTIN-13":13,"EAN-13":13,"GTIN-14":14}),Hl=Object.freeze({"EAN-8":"EAN-8",EAN8:"EAN-8",ean_8:"EAN-8","EAN-13":"EAN-13",EAN13:"EAN-13",ean_13:"EAN-13","UPC-A":"UPC-A",UPCA:"UPC-A",upc_a:"UPC-A","UPC-E":"UPC-E",UPCE:"UPC-E",upc_e:"UPC-E","ITF-14":"GTIN-14",ITF14:"GTIN-14"}),Xl=e=>typeof e=="string"&&/^[0-9]+$/.test(e);function ql(e){let t=0;for(let r=e.length-1,i=3;r>=0;r--,i=4-i)t+=Number(e[r])*i;return String((10-t%10)%10)}function Ln(e){return Xl(e)&&[8,12,13,14].includes(e.length)&&ql(e.slice(0,-1))===e.at(-1)}function Yl(e){if(typeof e!="string"||!/^[0-9]{9}[0-9X]$/.test(e))return!1;let t=0;for(let r=0;r<10;r++)t+=(e[r]==="X"?10:Number(e[r]))*(10-r);return t%11===0}function Kl(e){return typeof e=="string"&&/^(978|979)[0-9]{10}$/.test(e)&&Ln(e)}function Gl(e){if(typeof e!="string"||!/^[01][0-9]{7}$/.test(e))return null;let[t,r,i,n,a,o,s,c]=e,u=s<="2"?t+r+i+s+"0000"+n+a+o+c:s==="3"?t+r+i+n+"00000"+a+o+c:s==="4"?t+r+i+n+a+"00000"+o+c:t+r+i+n+a+o+"0000"+s+c;return Ln(u)?u:null}function Ph(e){if(!Yl(e))return null;let t="978"+e.slice(0,9);return t+ql(t)}function Oh(e){if(!Kl(e))return Object.freeze({status:"invalid",value:null,allocationStatus:"not-verified"});if(e.startsWith("979"))return Object.freeze({status:"no-equivalent",value:null,allocationStatus:"not-verified"});let t=e.slice(3,12),r=0;for(let n=0;n<9;n++)r+=Number(t[n])*(10-n);let i=(11-r%11)%11;return Object.freeze({status:"converted",value:t+(i===10?"X":String(i)),allocationStatus:"not-verified"})}function Lh(e){return e==="JAN-8"?Object.freeze({naming:"JAN-8",representation:"EAN-8",countryOfManufacture:null}):e==="JAN-13"?Object.freeze({naming:"JAN-13",representation:"EAN-13",countryOfManufacture:null}):e==="JAN"?Object.freeze({naming:"JAN",representation:null,countryOfManufacture:null}):null}function Uh(e){return typeof e=="string"&&Object.hasOwn(Hl,e)?Hl[e]:null}function Wl(e){return e==="UPC-E"?"UPC-E":e==="ISBN-10"?"ISBN-10":e==="ISBN-13"?13:jl[e]??null}function On(e,t){if(e==null)return null;if(typeof e!="string")throw new TypeError(t+" must be a string or null");return e}function Dh(e){return e.labelledEquivalents=Object.freeze(e.labelledEquivalents.map(Object.freeze)),e.possibleRepresentations=Object.freeze(e.possibleRepresentations.map(Object.freeze)),Object.freeze(e)}function Jl(e){if(!e||typeof e!="object"||Array.isArray(e))throw new TypeError("input must be an object");if(typeof e.original!="string"||!e.original.length)throw new TypeError("original must be a nonempty string");if(typeof e.namespace!="string"||!e.namespace.length)throw new TypeError("namespace must be explicit and nonempty");let t=On(e.representationHint,"representationHint"),r=On(e.observedCarrier,"observedCarrier"),i=Lh(t),n=Uh(r),a=i?i.representation:t??n,o={contractVersion:Ih,original:e.original,namespace:e.namespace,sourceLexicalValue:On(e.sourceLexicalValue,"sourceLexicalValue"),sourceId:On(e.sourceId,"sourceId"),lookupOriginal:e.original,lookupContract:"caller-owned",requestedHint:t,effectiveHint:a,observedCarrier:r,hintOrigin:t!==null?"explicit":n?"decoder-label":"none",namingRelationship:i,countryOfManufacture:null,status:"untyped",reason:"explicit-representation-required",syntaxValid:null,checksumValid:null,validatedRepresentation:null,comparisonGTIN14:null,gtin14LeadingDigit:null,packagingRelationship:"not-established",labelledEquivalents:[],possibleRepresentations:[],isbn10Equivalent:null,isbn10Availability:"not-applicable",allocationStatus:"not-verified",catalogueStatus:"not-queried",physicalCarrierStatus:r===null?"unobserved":"caller-label-only",productIdentityAsserted:!1,ingredientClassification:"not-assessed"},s=()=>Dh(o),c=(l,d,h)=>{l!==e.original&&!o.labelledEquivalents.some(m=>m.value===l&&m.representation===d)&&o.labelledEquivalents.push({value:l,representation:d,rule:h})};if(t!==null&&!Nh.includes(t))return o.status="invalid",o.reason="unsupported-representation-hint",s();if(t==="JAN")return o.status="hint-required",o.reason="choose-JAN-8-or-JAN-13-explicitly",s();if(a===null)return r==="ITF"||r==="itf"?o.reason="generic-ITF-does-not-declare-GTIN":/^[0-9]{8}$/.test(e.original)&&(o.status="ambiguous",o.reason="eight-digits-do-not-select-EAN-8-or-UPC-E",o.possibleRepresentations=[{representation:"EAN-8",checksumCompatible:Ln(e.original)},{representation:"UPC-E",checksumCompatible:Gl(e.original)!==null}]),s();if(t!==null&&n&&Wl(a)!==Wl(n))return o.status="conflict",o.reason="explicit-hint-conflicts-with-decoder-label",s();let u=null;if(a==="ISBN-10")o.syntaxValid=/^[0-9]{9}[0-9X]$/.test(e.original),o.checksumValid=o.syntaxValid?Yl(e.original):null,o.checksumValid&&(u=Ph(e.original),o.validatedRepresentation="ISBN-10",o.isbn10Equivalent=e.original,o.isbn10Availability="original",c(u,"ISBN-13","validated-ISBN-10-to-978-ISBN-13"));else if(a==="ISBN-13"){if(o.syntaxValid=/^(978|979)[0-9]{10}$/.test(e.original),o.checksumValid=o.syntaxValid?Kl(e.original):null,o.checksumValid){u=e.original,o.validatedRepresentation="ISBN-13";let l=Oh(e.original);o.isbn10Availability=l.status,o.isbn10Equivalent=l.value,l.value&&c(l.value,"ISBN-10","validated-978-ISBN-13-to-ISBN-10")}}else if(a==="UPC-E")o.syntaxValid=/^[01][0-9]{7}$/.test(e.original),u=o.syntaxValid?Gl(e.original):null,o.checksumValid=o.syntaxValid?u!==null:null,u&&(o.validatedRepresentation="UPC-E",c(u,"GTIN-12","explicit-UPC-E-to-GTIN-12"),c("0"+u,"EAN-13","GTIN-12-as-leading-zero-EAN-13"));else{let l=jl[a];o.syntaxValid=!!l&&Xl(e.original)&&e.original.length===l,o.checksumValid=o.syntaxValid?Ln(e.original):null,o.checksumValid&&(u=e.original,o.validatedRepresentation="GTIN-"+l,l===12&&c("0"+u,"EAN-13","GTIN-12-as-leading-zero-EAN-13"),l===13&&u.startsWith("0")&&c(u.slice(1),"GTIN-12","leading-zero-EAN-13-as-GTIN-12"),l===14&&(o.gtin14LeadingDigit=u[0]))}return o.checksumValid?(o.status="checksum-valid",o.reason="typed-syntax-and-checksum-only",o.comparisonGTIN14=u.padStart(14,"0"),s()):(o.status="invalid",o.reason=o.syntaxValid?"checksum-invalid":"representation-syntax-invalid",s())}var Ql="offmenu-scanner-kitchen-pending-v1",oo="offmenu-scanner-kitchen-handoff/2",lo="offmenu-published-product-reference/1";var Fh=3e3,ao=Object.freeze({sourceId:"off",releaseId:"offmenu-off-selected-products-20261025-v1",manifestSha256:"1bf09a371a164ebd8215fd9b44a1b2ac9816caaa65cd13504086defad76d4e8f"}),kh=e=>typeof e=="string"&&/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(e),bi=(e,t)=>typeof e=="string"&&e.length>0&&e.length<=t&&!/[\x00-\x1f\x7f]/.test(e),so=(e,t)=>e===null||bi(e,t),Zl=e=>typeof e=="string"&&/^\d{4,32}$/.test(e),$l=e=>{if(e==null)return!0;if(!bi(e,700))return!1;try{let t=new URL(e);return t.protocol==="https:"&&!t.username&&!t.password&&(t.href===e||e===t.origin)}catch{return!1}};function co(e,t){if(!bi(t,128))return!1;if(e?.lexicalValue===t)return Zl(t)&&e.capturedLexicalValue===void 0&&e.representationHint===void 0;if(e?.capturedLexicalValue!==t||typeof e.representationHint!="string"||!Zl(e.lexicalValue))return!1;let r=Jl({original:t,namespace:"barcode",representationHint:e.representationHint});return r.status==="checksum-valid"&&r.labelledEquivalents.some(i=>i.value===e.lexicalValue)}function ec(e,t){let r=e?.provenance;return e?.schema===lo&&e.sourceId===ao.sourceId&&e.releaseId===ao.releaseId&&e.manifestSha256===ao.manifestSha256&&bi(e.recordId,200)&&e.recordId.startsWith("offmenu:")&&e.namespace==="barcode"&&co(e,t)&&r?.sourceId==="off"&&r.visibility==="public"&&bi(r.license,160)&&bi(r.attribution,240)&&$l(r.url)&&$l(r.licenseUrl)&&so(r.sourceDate,80)}function tc(e,t){if(!ec(e,t))throw Error("Published source reference does not match the selected barcode and release.");return{schema:lo,sourceId:e.sourceId,releaseId:e.releaseId,manifestSha256:e.manifestSha256,recordId:e.recordId,namespace:"barcode",lexicalValue:e.lexicalValue,...e.lexicalValue!==t?{capturedLexicalValue:t,representationHint:e.representationHint}:{},provenance:{sourceId:"off",visibility:"public",license:e.provenance.license,attribution:e.provenance.attribution,url:e.provenance.url??null,licenseUrl:e.provenance.licenseUrl??null,sourceDate:e.provenance.sourceDate}}}function Bh(e){if(!kh(e?.operationId)||!co(e.publicProductReference,e.barcode)||!so(e.name,240)||!so(e.brand,240))throw Error("Scanner handoff item is incomplete.");return{operationId:e.operationId,barcode:e.barcode,name:e.name,brand:e.brand,publicProductReference:tc(e.publicProductReference,e.barcode)}}function Vh(e){if(e?.schema!==oo||!Array.isArray(e.items)||!e.items.length||e.items.length>20)throw Error("Scanner handoff is invalid.");let t=e.items.map(Bh);if(new Set(t.map(i=>i.operationId)).size!==t.length)throw Error("Scanner handoff repeats an operation.");let r={schema:oo,items:t};if(new TextEncoder().encode(JSON.stringify(r)).byteLength>Fh)throw Error("Scanner handoff exceeds the existing tab limit. Review a smaller batch.");return r}function rc(e){if(!Array.isArray(e)||!e.length)throw Error("Scan at least one item before finishing.");return Vh({schema:oo,items:e.map(t=>{let r=t.selectedRecord,i=r?.publicRecord,n=i?.provenance,a=r?.matchContext?.sourceLexicalValue??t.raw,o={lexicalValue:a,...a!==t.raw?{capturedLexicalValue:t.raw,representationHint:t.symbology}:{}};if(!t.matches?.includes(r)||!co(o,t.raw)||!i?.data?.identifiers?.some(c=>c.system==="barcode"&&c.value===a)||n?.sourceId!=="off"||n.visibility!=="public")throw Error("Choose a published source record for every kept item, or Undo it before finishing.");let s={schema:lo,sourceId:"off",releaseId:t.releaseId,manifestSha256:t.manifestSha256,recordId:i.id,namespace:t.namespace,...o,provenance:{sourceId:n.sourceId,visibility:n.visibility,license:n.license,attribution:n.attribution,url:n.url??null,licenseUrl:n.licenseUrl??null,sourceDate:n.sourceDate??null}};return{operationId:t.id,barcode:t.raw,name:r.name??null,brand:r.brand??null,publicProductReference:s}})})}var kn="offmenu-barcode-foundation-phase/2",jr={releaseId:"offmenu-foundation-production-20261027-v1",manifestSha256:"10f4f5acb9dbab8e5411dc7c7aa9136d6bb6317cd5eb11d9ec6c9ccdd4a1a0db"},uo=["off","usda-files"],nc="offmenu-local-foundation-scanner/1",Dn=["sourceId","releaseId","recordId","sourceObservationSha256","sourceDocumentSha256","inputDatabaseSha256","sourceQualificationSha256"],zh=["baseMaterial","milkBase","fatClass","sugarStatus","saltStatus","lactoseStatus","processing","form","flavour","scent","colour","material","size","netAmount","packageCount","concentration","strength","dimensions","capacity","compatibility","finish","grade","originVariant","otherQualifiedVariant"],Hh=/^[a-f0-9]{64}$/,en=e=>e!==null&&typeof e=="object"&&!Array.isArray(e),Cr=e=>typeof e=="string"&&e.length>0&&e.length<=1024&&!/[\x00-\x1f\x7f]/.test(e),Fn=e=>Array.isArray(e)?"["+e.map(Fn).join(",")+"]":en(e)?"{"+Object.keys(e).sort().map(t=>JSON.stringify(t)+":"+Fn(e[t])).join(",")+"}":JSON.stringify(e),ac=(e,t)=>Fn(e)===Fn(t),ho=e=>JSON.stringify(Dn.map(t=>e.provenance[t]).concat(e.id));function Gh(e,t,r){let i=e?.provenance,n=e?.data,a=e?.curation;return e?.schemaVersion==="1.0"&&e.kind==="product"&&Cr(e.id)&&en(i)&&i.sourceId===t&&i.visibility==="public"&&Dn.every(o=>Cr(i[o]))&&Dn.slice(3).every(o=>Hh.test(i[o]))&&Cr(i.license)&&Cr(i.attribution)&&a?.schema==="offmenu-foundation-curation/2"&&a.phaseContract===kn&&a.rawSourcePayloadPublished===!1&&a.legacyCuratedAdmission===!1&&en(n)&&Cr(n.name)&&Cr(n.canonicalEnglishKey)&&Cr(n.canonicalConceptId)&&["ingredient","noningredient"].includes(n.classification)&&n.identifiers?.some(o=>o.system==="barcode"&&o.value===r)&&n.foundationComplete===!0&&["fullProductComplete","normalizationComplete","goldAdmitted","automaticPlanningEligible","recipeNutritionJoinsAccepted"].every(o=>n[o]===!1)&&n.meaningfulType?.state==="reviewed"&&Cr(n.meaningfulType.canonicalEnglishLabel)&&n.meaningfulType.subjectConceptId===n.canonicalConceptId&&en(n.variantParameters)&&Object.keys(n.variantParameters).length===24&&zh.every(o=>en(n.variantParameters[o])&&["known","unknown"].includes(n.variantParameters[o].state))&&(!Object.hasOwn(e,"foundationSourceReference")||Xa(e.foundationSourceReference,r)&&e.foundationSourceReference.recordId===e.id&&e.foundationSourceReference.namespace==="barcode"&&e.foundationSourceReference.lexicalValue===r&&Dn.every(o=>e.foundationSourceReference.sourceBinding[o]===i[o]))}function Wh(e){let t=structuredClone(e);return{id:ho(t),name:"Canonical base \xB7 "+t.data.name,brand:null,provenance:structuredClone(t.provenance),foundationRecord:t,...Xa(t.foundationSourceReference,t.data.identifiers[0]?.value)?{foundationSourceReference:Ji(t.foundationSourceReference,t.data.identifiers[0].value)}:{},sourceObservationReference:null}}function oc(e,t){let r=new Map;for(let i of[...e,...t]){let n=ho(i.foundationRecord),a=r.get(n);if(a&&!ac(a.foundationRecord,i.foundationRecord))throw Error("FOUNDATION_OBSERVATION_CHANGED");a||r.set(n,i)}return[...r.values()]}function ic(e,t,r,i,n,a){let o=a.some(c=>c.pending),s=a.some(c=>c.error);return{original:e,namespace:"barcode",symbology:r,generation:t,requestCursor:i,foundationLookup:!0,matches:n,providerStates:a.map(c=>({...c})),status:s?n.length?"partial":"unavailable":n.length>1||n.length&&o?"ambiguous":n.length?"source-match":"unavailable",hasMore:o,nextCursor:o?JSON.stringify({schema:nc,raw:e,generation:t,symbology:r,selection:jr,lanes:a}):null,fullProductComplete:!1,goldAdmitted:!1,automaticPlanningEligible:!1,physicalProductEquivalenceAsserted:!1,externalFallback:!1}}function po({fetchImpl:e=globalThis.fetch}={}){return async function(r,i,n=null,a=null,o="barcode"){let s=l=>({...ic(r,i,a,n,[],uo.map(d=>({source:d,pending:!1,cursor:null,error:l,status:null}))),error:l});if(o!=="barcode"||typeof r!="string"||!/^\d{4,32}$/.test(r)||!Number.isSafeInteger(i)||a!==null&&typeof a!="string")return s("UNSUPPORTED_EXACT_BARCODE");let c=uo.map(l=>({source:l,pending:!0,cursor:null,error:null,status:null}));if(n!==null)try{if(typeof n!="string"||n.length>6e3)throw Error();let l=JSON.parse(n);if(l.schema!==nc||l.raw!==r||l.generation!==i||l.symbology!==a||!ac(l.selection,jr)||!Array.isArray(l.lanes)||l.lanes.length!==2)throw Error();c=l.lanes.map((d,h)=>{if(d.source!==uo[h]||typeof d.pending!="boolean"||d.cursor!==null&&(typeof d.cursor!="string"||d.cursor.length>700)||d.error!==null&&typeof d.error!="string")throw Error();return{...d}})}catch{return s("FOUNDATION_CURSOR_MISMATCH")}let u=[];for(let l of c){if(!l.pending)continue;l.pending=!1,l.error=null;let d=new URL("/api/corpus/foundation","http://offmenu.invalid");d.searchParams.set("source",l.source),d.searchParams.set("barcode",r),d.searchParams.set("limit","20"),l.cursor&&d.searchParams.set("cursor",l.cursor);try{let h=await e(d.pathname+d.search,{method:"GET",credentials:"omit",cache:"no-store",redirect:"error",mode:"same-origin",headers:{Accept:"application/json"}});if(l.status=h.status,h.status!==200){l.error=h.status===503?"OWN_DATA_UNAVAILABLE":h.status===401||h.status===403?"FOUNDATION_ACCESS_UNAVAILABLE":"FOUNDATION_QUERY_UNAVAILABLE";continue}let m=await h.text();if(new TextEncoder().encode(m).byteLength>2097152)throw Error("FOUNDATION_RESPONSE_BOUND");let g=JSON.parse(m);if(g.schemaVersion!=="1.0"||g.fieldContract!==kn||g.source!==l.source||g.barcode!==r||g.releaseId!==jr.releaseId||g.manifestSha256!==jr.manifestSha256||g.externalFallback!==!1||g.physicalProductEquivalenceAsserted!==!1||g.goldAdmitted!==!1||g.fullProductComplete!==!1||g.httpStatus!==200||g.status!=="phase-qualified-own-data"||!Array.isArray(g.records)||g.records.length<1||g.records.length>20||!Number.isSafeInteger(g.qualifiedSourceObservationCount)||g.qualifiedSourceObservationCount<g.records.length||g.nextCursor!==null&&(typeof g.nextCursor!="string"||g.nextCursor.length>700||!g.nextCursor.length)||g.records.some(_=>!Gh(_,l.source,r)))throw Error("FOUNDATION_RESPONSE_MISMATCH");if(new Set(g.records.map(ho)).size!==g.records.length)throw Error("FOUNDATION_DUPLICATE_OBSERVATION");u.push(...g.records.map(Wh)),l.cursor=g.nextCursor,l.pending=g.nextCursor!==null,l.observationCount=g.qualifiedSourceObservationCount}catch{l.error="FOUNDATION_RESPONSE_UNAVAILABLE",l.pending=!1}}return ic(r,i,a,n,oc([],u),c)}}var zb=po();function fo(e,t){if(!e.foundationLookup||!t.foundationLookup||e.original!==t.original||e.generation!==t.generation||e.symbology!==t.symbology||e.nextCursor!==t.requestCursor)throw Error("FOUNDATION_PAGE_CONTEXT_CHANGED");let r=oc(e.matches,t.matches);return{...t,matches:r,status:t.providerStates.some(i=>i.error)?r.length?"partial":"unavailable":r.length>1||r.length&&t.hasMore?"ambiguous":r.length?"source-match":"unavailable"}}var Un=e=>e==null?"Unknown":typeof e=="object"?JSON.stringify(e):String(e);function mo(e,t,r="overview"){let i=[{label:"Foundation observations",text:"Source-qualified base and type only. Full product, nutrition/recipe joins, normalization, Gold and automatic inventory/planning remain unaccepted. Distinct observations are not physical-product equivalence."}];for(let s of t?.providerStates||[])i.push({label:"Source \xB7 "+s.source,text:s.error?s.error+" \xB7 selected representation unavailable, not global absence":Un(s.observationCount)+" selected source observations"+(s.pending?" \xB7 more pages remain":"")});let n=e?.foundationRecord;if(!n)return i.push(t?.status==="scoped-miss"?{label:"Barcode retained",text:"No qualified details in the selected source indexes for "+(t.raw??t.original)+". Other sources may differ. Product, ingredient and nutrition facts remain unknown."}:{label:"Source choice",text:"Inspect the separate source observations. No product identity is inferred from the code alone."}),i;let a=n.data,o=n.provenance;if(i.push({label:"Canonical English base",text:a.name},{label:"Meaningful type",text:a.meaningfulType.canonicalEnglishLabel},{label:"Ingredient eligibility",text:a.classification},{label:"Source notice",text:o.attribution+" \xB7 "+o.license},{label:"Source observation",text:o.sourceId+" \xB7 "+o.releaseId+" \xB7 "+o.recordId}),r==="nutrition"&&i.push({label:"Nutrition",text:"Not joined or accepted by this foundation response. Unknown, not zero."}),r==="overview"||r==="ingredients")for(let[s,c]of Object.entries(a.variantParameters))i.push({label:s+" \xB7 "+c.state,text:c.state==="unknown"?"Unknown \xB7 "+Un(c.reason)+" \xB7 "+Un(c.qualificationDisposition):Un(c.value)});return r==="source"&&i.push({label:"Exact source binding",text:JSON.stringify(o)},{label:"Reviewed type relation",text:JSON.stringify(a.meaningfulType)},{label:"All parameter states and evidence",text:JSON.stringify(a.variantParameters)},{label:"Complete supplied foundation observation",text:JSON.stringify(n)}),i}function go({fetchImpl:e=globalThis.fetch}={}){return async function(r,i,n=null,a=null,o="barcode"){let s=new Map,u=await po({fetchImpl:async(l,d)=>{let h=await e(l,d),m=new URL(l,"http://local.invalid").searchParams.get("source");if(h.status===503){let g="service-unavailable";try{let _=await h.clone().text();if(new TextEncoder().encode(_).byteLength>65536)throw Error();let f=JSON.parse(_);f.schemaVersion==="1.0"&&f.fieldContract===kn&&f.source===m&&f.barcode===r&&f.releaseId===jr.releaseId&&f.manifestSha256===jr.manifestSha256&&f.httpStatus===503&&f.status==="own-data-unavailable"&&Array.isArray(f.records)&&f.records.length===0&&f.qualifiedSourceObservationCount===0&&f.externalFallback===!1&&f.physicalProductEquivalenceAsserted===!1&&f.goldAdmitted===!1&&f.fullProductComplete===!1&&(g="no-usable-qualified-details")}catch{}s.set(m,g)}else h.status===400||h.status===409?s.set(m,"query-unavailable"):(h.status===401||h.status===403)&&s.set(m,"access-unavailable");return h}})(r,i,n,a,o);const providerStates=u.providerStates.map(l=>{const kind=s.get(l.source);return kind==="no-usable-qualified-details"?{...l,error:null,availabilityKind:kind,lookupOutcome:"source-key-not-found",observationCount:0}:{...l,...l.error?{availabilityKind:kind||"service-unavailable"}:{}}});const failed=providerStates.some(l=>l.error),count=u.matches.length;const status=failed?(count?"partial":"unavailable"):count>1||count&&u.hasMore?"ambiguous":count?"source-match":providerStates.every(l=>l.lookupOutcome==="source-key-not-found")?"scoped-miss":"unavailable";let nextCursor=u.nextCursor;if(nextCursor!==null){const page=JSON.parse(nextCursor);page.lanes=providerStates;nextCursor=JSON.stringify(page)}return{...u,providerStates,status,nextCursor}}}var Wb=go();var sc=(e,t)=>JSON.stringify(e)===JSON.stringify(t),jh=e=>(e?.providerStates??[]).some(t=>t.error&&t.availabilityKind!=="no-usable-qualified-details");function Bn(e,t,r=[]){let i=e?.matches??[],n=new Set(i.map(l=>gi(l.foundationRecord.provenance))),a=new Map(r.map(l=>[l.id,l])),o=[];for(let l of t.records??[]){if(n.has(gi(l.sourceBinding)))continue;let d=vi(l),h=a.get(d.id);o.push(h&&sc(h.sourceIdentityRecord,l)?h:d)}let s=[...i,...o],c=(e?.providerStates??[]).some(l=>l.error)||!!t.error,u=e??{original:t.lexicalValue,namespace:t.namespace,symbology:null,generation:t.generation,foundationLookup:!0,providerStates:[],hasMore:!1,nextCursor:null,requestCursor:null,externalFallback:!1,fullProductComplete:!1,goldAdmitted:!1,automaticPlanningEligible:!1,physicalProductEquivalenceAsserted:!1};return{...u,phaseResult:e,identityState:t,matches:s,phaseTechnicalFailure:jh(e),identityNextOffset:t.nextOffset??null,status:t.error==="SOURCE_IDENTITY_NOT_CONFIGURED"&&e?e.status:c?s.length?"partial":"unavailable":s.length>1||s.length&&u.hasMore?"ambiguous":s.length?"source-match":"unavailable"}}function Xh({selection:e=null,fetchImpl:t=globalThis.fetch}={}){let r=go({fetchImpl:t}),i=Ul({selection:e,fetchImpl:t});async function n(o,s,c=null,u=null,l="barcode"){let d=l==="barcode"?await r(o,s,c,u,l):null;if(!["barcode","USDA-FDC"].includes(l))return d??{foundationLookup:!0,original:o,namespace:l,generation:s,matches:[],providerStates:[],status:"unavailable",error:"UNSUPPORTED_EXACT_BARCODE",hasMore:!1,nextCursor:null};let h=await i(o,s,l,0,20);return Bn(d,h)}async function a(o){let s=o.identityState;if(!s||s.error||s.nextOffset===null||s.nextOffset===void 0)throw Error("SOURCE_IDENTITY_PAGE_UNAVAILABLE");let c=await i(o.raw,o.queryGeneration??o.generation,o.namespace,s.nextOffset,20);if(o.identityState!==s)throw Error("SOURCE_IDENTITY_PAGE_CONTEXT_CHANGED");if(c.error)return Bn(o.phaseResult,{...s,error:c.error},o.matches);if(c.namespace!==s.namespace||c.lexicalValue!==s.lexicalValue||c.generation!==s.generation||c.manifestSha256!==s.manifestSha256||c.selectionSha256!==s.selectionSha256||c.admissionSha256!==s.admissionSha256||c.requestOffset!==s.nextOffset||c.totalSourceObservations!==s.totalSourceObservations)throw Error("SOURCE_IDENTITY_PAGE_CONTEXT_CHANGED");let u=[...s.records],l=new Map(u.map(d=>[vi(d).id,d]));for(let d of c.records){let h=vi(d).id;if(l.has(h))throw Error("SOURCE_IDENTITY_DUPLICATE_PAGE_RECORD");l.set(h,d),u.push(d)}return Bn(o.phaseResult,{...c,records:u,requestOffset:s.requestOffset},o.matches)}return Object.assign(n,{moreIdentity:a})}function lc(e,t){let r=e.phaseResult,i=t.phaseResult;if(!r||!i)throw Error("FOUNDATION_PAGE_CONTEXT_CHANGED");let n=fo(r,i),a=e.identityState,o=t.identityState;if(!a||!o||a.namespace!==o.namespace||a.lexicalValue!==o.lexicalValue||a.generation!==o.generation||a.manifestSha256!==o.manifestSha256||a.selectionSha256!==o.selectionSha256||a.admissionSha256!==o.admissionSha256)throw Error("SOURCE_IDENTITY_PAGE_CONTEXT_CHANGED");if(!o.error&&o.records.some(s=>{let c=a.records.find(u=>vi(u).id===vi(s).id);return c&&!sc(c,s)}))throw Error("SOURCE_IDENTITY_OBSERVATION_CHANGED");return Bn(n,o.error?{...a,error:o.error}:a,e.matches)}function vo(e,t,r="overview"){return e?.kind==="source-identity"?Ja(e,t,r):[...mo(e,t,r),...Za(t)]}var Vn=Xh(),cc=e=>Vn.moreIdentity(e);var uc=Object.freeze({"Offline resource unavailable":"\u0627\u0644\u0645\u0648\u0631\u062F \u063A\u064A\u0631 \u0645\u062A\u0627\u062D \u062F\u0648\u0646 \u0627\u062A\u0635\u0627\u0644","Translation is stale; showing the original source text.":"\u0627\u0644\u062A\u0631\u062C\u0645\u0629 \u0642\u062F\u064A\u0645\u0629\u061B \u064A\u064F\u0639\u0631\u0636 \u0646\u0635 \u0627\u0644\u0645\u0635\u062F\u0631 \u0627\u0644\u0623\u0635\u0644\u064A.","Common corpus graph loaded for local preview. Source identities, citations and quantities are preserved; nothing is saved.":"\u062A\u0645 \u062A\u062D\u0645\u064A\u0644 \u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0645\u062C\u0645\u0648\u0639\u0629 \u0644\u0644\u0645\u0639\u0627\u064A\u0646\u0629 \u0627\u0644\u0645\u062D\u0644\u064A\u0629. \u062A\u0628\u0642\u0649 \u0647\u0648\u064A\u0627\u062A \u0627\u0644\u0645\u0635\u0627\u062F\u0631 \u0648\u0627\u0644\u0627\u0633\u062A\u0634\u0647\u0627\u062F\u0627\u062A \u0648\u0627\u0644\u0643\u0645\u064A\u0627\u062A \u0643\u0645\u0627 \u0647\u064A\u061B \u0644\u0645 \u062A\u064F\u062D\u0641\u0638 \u0623\u064A \u062A\u063A\u064A\u064A\u0631\u0627\u062A.","Return to offmenu":"\u0627\u0644\u0639\u0648\u062F\u0629 \u0625\u0644\u0649 offmenu","Returning to offmenu\u2026":"\u062C\u0627\u0631\u064D \u0627\u0644\u0639\u0648\u062F\u0629 \u0625\u0644\u0649 offmenu\u2026","Open offmenu":"\u0627\u0641\u062A\u062D offmenu",Yes:"\u0646\u0639\u0645",No:"\u0644\u0627","Unknown unit":"\u0648\u062D\u062F\u0629 \u063A\u064A\u0631 \u0645\u0639\u0631\u0648\u0641\u0629","Kitchen inventory":"\u0645\u062E\u0632\u0648\u0646 \u0627\u0644\u0645\u0637\u0628\u062E","Home checkout receipt":"\u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636 \u0627\u0644\u0645\u0646\u0632\u0644","Household menus & recipe booklet":"\u0648\u062C\u0628\u0627\u062A \u0627\u0644\u0623\u0633\u0631\u0629 \u0648\u0643\u062A\u064A\u0651\u0628 \u0627\u0644\u0648\u0635\u0641\u0627\u062A","Meal-plan shopping list":"\u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u062A\u0633\u0648\u0651\u0642 \u0644\u062E\u0637\u0629 \u0627\u0644\u0648\u062C\u0628\u0627\u062A","Household preferences":"\u062A\u0641\u0636\u064A\u0644\u0627\u062A \u0627\u0644\u0623\u0633\u0631\u0629","Food history & nutrition":"\u0633\u062C\u0644 \u0627\u0644\u0637\u0639\u0627\u0645 \u0648\u0627\u0644\u062A\u063A\u0630\u064A\u0629","Waste & freshness report":"\u062A\u0642\u0631\u064A\u0631 \u0627\u0644\u0647\u062F\u0631 \u0648\u062D\u0627\u0644\u0629 \u0627\u0644\u0637\u0639\u0627\u0645",Product:"\u0627\u0644\u0645\u0646\u062A\u062C",Amount:"\u0627\u0644\u0643\u0645\u064A\u0629","Recipe ingredient":"\u0645\u0643\u0648\u0651\u0646 \u0627\u0644\u0648\u0635\u0641\u0629",Expiry:"\u062A\u0627\u0631\u064A\u062E \u0627\u0644\u0627\u0646\u062A\u0647\u0627\u0621",Directions:"\u0627\u0644\u0637\u0631\u064A\u0642\u0629",Contents:"\u0627\u0644\u0645\u062D\u062A\u0648\u064A\u0627\u062A","Recipes indexed: {count}":{zero:"\u0644\u0627 \u0648\u0635\u0641\u0627\u062A \u0645\u0641\u0647\u0631\u0633\u0629 ({count})",one:"\u0648\u0635\u0641\u0629 \u0648\u0627\u062D\u062F\u0629 \u0645\u0641\u0647\u0631\u0633\u0629 ({count})",two:"\u0648\u0635\u0641\u062A\u0627\u0646 \u0645\u0641\u0647\u0631\u0633\u062A\u0627\u0646 ({count})",few:"{count} \u0648\u0635\u0641\u0627\u062A \u0645\u0641\u0647\u0631\u0633\u0629",many:"{count} \u0648\u0635\u0641\u0629 \u0645\u0641\u0647\u0631\u0633\u0629",other:"\u0648\u0635\u0641\u0627\u062A \u0645\u0641\u0647\u0631\u0633\u0629: {count}"},"Translation unavailable; showing the original source text.":"\u0627\u0644\u062A\u0631\u062C\u0645\u0629 \u063A\u064A\u0631 \u0645\u062A\u0627\u062D\u0629\u061B \u064A\u064F\u0639\u0631\u0636 \u0646\u0635 \u0627\u0644\u0645\u0635\u062F\u0631 \u0627\u0644\u0623\u0635\u0644\u064A.","Same as interface language":"\u0645\u062B\u0644 \u0644\u063A\u0629 \u0627\u0644\u0648\u0627\u062C\u0647\u0629","Arabic when supplied":"\u0627\u0644\u0639\u0631\u0628\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627","Japanese when supplied":"\u0627\u0644\u064A\u0627\u0628\u0627\u0646\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627","English when supplied":"\u0627\u0644\u0625\u0646\u062C\u0644\u064A\u0632\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627","French when supplied":"\u0627\u0644\u0641\u0631\u0646\u0633\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627","German when supplied":"\u0627\u0644\u0623\u0644\u0645\u0627\u0646\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627","Chinese when supplied":"\u0627\u0644\u0635\u064A\u0646\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627","Hindi when supplied":"\u0627\u0644\u0647\u0646\u062F\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627","Indonesian when supplied":"\u0627\u0644\u0625\u0646\u062F\u0648\u0646\u064A\u0633\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627","Russian when supplied":"\u0627\u0644\u0631\u0648\u0633\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627","Original source language":"\u0644\u063A\u0629 \u0627\u0644\u0645\u0635\u062F\u0631 \u0627\u0644\u0623\u0635\u0644\u064A\u0629","Food-name display language":"\u0644\u063A\u0629 \u0639\u0631\u0636 \u0623\u0633\u0645\u0627\u0621 \u0627\u0644\u0623\u0637\u0639\u0645\u0629","All languages":"\u062C\u0645\u064A\u0639 \u0627\u0644\u0644\u063A\u0627\u062A","Recipe language":"\u0644\u063A\u0629 \u0627\u0644\u0648\u0635\u0641\u0629","RECIPES FROM AROUND THE WORLD":"\u0648\u0635\u0641\u0627\u062A \u0645\u0646 \u0623\u0646\u062D\u0627\u0621 \u0627\u0644\u0639\u0627\u0644\u0645","Explore the shared recipe library.":"\u0627\u0633\u062A\u0643\u0634\u0641 \u0645\u0643\u062A\u0628\u0629 \u0627\u0644\u0648\u0635\u0641\u0627\u062A \u0627\u0644\u0645\u0634\u062A\u0631\u0643\u0629.","Open worldwide recipes":"\u0627\u0641\u062A\u062D \u0648\u0635\u0641\u0627\u062A \u0627\u0644\u0639\u0627\u0644\u0645","Dish or ingredients":"\u0627\u0644\u0637\u0628\u0642 \u0623\u0648 \u0627\u0644\u0645\u0643\u0648\u0651\u0646\u0627\u062A","Original source":"\u0627\u0644\u0645\u0635\u062F\u0631 \u0627\u0644\u0623\u0635\u0644\u064A","Prioritise recipes using my available ingredients":"\u0623\u0639\u0637\u0650 \u0627\u0644\u0623\u0648\u0644\u0648\u064A\u0629 \u0644\u0644\u0648\u0635\u0641\u0627\u062A \u0627\u0644\u062A\u064A \u062A\u0633\u062A\u062E\u062F\u0645 \u0645\u0643\u0648\u0651\u0646\u0627\u062A\u064A \u0627\u0644\u0645\u062A\u0627\u062D\u0629","Shared recipes are available to everyone. Your pantry matching runs on this device.":"\u0627\u0644\u0648\u0635\u0641\u0627\u062A \u0627\u0644\u0645\u0634\u062A\u0631\u0643\u0629 \u0645\u062A\u0627\u062D\u0629 \u0644\u0644\u062C\u0645\u064A\u0639. \u062A\u064F\u0637\u0627\u0628\u064E\u0642 \u0645\u0639 \u0645\u062E\u0632\u0648\u0646\u0643 \u0639\u0644\u0649 \u0647\u0630\u0627 \u0627\u0644\u062C\u0647\u0627\u0632.","A little room for possibility.":"\u0645\u0633\u0627\u062D\u0629 \u0635\u063A\u064A\u0631\u0629 \u0644\u0623\u0641\u0643\u0627\u0631 \u062C\u062F\u064A\u062F\u0629.","Choose a shelf and scan your first items through checkout.":"\u0627\u062E\u062A\u0631 \u0631\u0641\u064B\u0627 \u0648\u0627\u0645\u0633\u062D \u0623\u0635\u0646\u0627\u0641\u0643 \u0627\u0644\u0623\u0648\u0644\u0649 \u0644\u0625\u0636\u0627\u0641\u062A\u0647\u0627 \u0625\u0644\u0649 \u0627\u0644\u0642\u0627\u0626\u0645\u0629.","offmenu \xB7 A little checkout. A better stocked home.":"offmenu \xB7 \u0642\u0627\u0626\u0645\u0629 \u0628\u0633\u064A\u0637\u0629. \u0648\u0645\u062E\u0632\u0648\u0646 \u0645\u0646\u0632\u0644\u064A \u0623\u0641\u0636\u0644.","Pantry, fridge or freezer. One satisfying":"\u062E\u0632\u0627\u0646\u0629 \u0627\u0644\u0637\u0639\u0627\u0645 \u0623\u0648 \u0627\u0644\u062B\u0644\u0627\u062C\u0629 \u0623\u0648 \u0627\u0644\u0645\u062C\u0645\u0651\u062F. \u062A\u0646\u0628\u064A\u0647",beep:"\u0644\u0637\u064A\u0641","at a time.":"\u0645\u0639 \u0643\u0644 \u0635\u0646\u0641.","THE HOME CHECKOUT CLUB":"\u0646\u0627\u062F\u064A \u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636 \u0627\u0644\u0645\u0646\u0632\u0644","EST. RIGHT NOW":"\u0627\u0628\u062F\u0623 \u0627\u0644\u0622\u0646","Oh, so that\u2019s what\u2019s":"\u0625\u0630\u064B\u0627 \u0647\u0630\u0627 \u0645\u0627 \u0643\u0627\u0646","at the back of the shelf.":"\u0641\u064A \u0622\u062E\u0631 \u0627\u0644\u0631\u0641.","HELLO, KITCHEN.":"\u0645\u0631\u062D\u0628\u064B\u0627 \u064A\u0627 \u0645\u0637\u0628\u062E.","3 items \xB7 endless possibilities":"\u0663 \u0623\u0635\u0646\u0627\u0641 \xB7 \u0623\u0641\u0643\u0627\u0631 \u0644\u0627 \u062D\u0635\u0631 \u0644\u0647\u0627","THE GOOD":"\u0627\u0644\u0637\u0639\u0627\u0645",STUFF:"\u0627\u0644\u062C\u064A\u0651\u062F","YOUR KITCHEN":"\u0645\u0637\u0628\u062E\u0643","A little inspiration":"\u0642\u0644\u064A\u0644 \u0645\u0646 \u0627\u0644\u0625\u0644\u0647\u0627\u0645","ALREADY YOURS \u2713":"\u0644\u062F\u064A\u0643 \u0628\u0627\u0644\u0641\u0639\u0644 \u2713","\u25CE See what\u2019s hiding":"\u25CE \u0627\u0643\u062A\u0634\u0641 \u0645\u0627 \u0644\u062F\u064A\u0643","\u25A5 Make space for good food":"\u25A5 \u062E\u0635\u0651\u0635 \u0645\u0633\u0627\u062D\u0629 \u0644\u0644\u0637\u0639\u0627\u0645 \u0627\u0644\u062C\u064A\u0651\u062F","\u2733 Find your next meal":"\u2733 \u0627\u062E\u062A\u0631 \u0648\u062C\u0628\u062A\u0643 \u0627\u0644\u062A\u0627\u0644\u064A\u0629","A little more play. A little less \u201Cwhat\u2019s for dinner?\u201D":"\u0645\u062A\u0639\u0629 \u0623\u0643\u062B\u0631 \u0648\u062D\u064A\u0631\u0629 \u0623\u0642\u0644 \u0628\u0634\u0623\u0646 \u0627\u0644\u0639\u0634\u0627\u0621.","Illustration of the offmenu home checkout":"\u0631\u0633\u0645 \u062A\u0648\u0636\u064A\u062D\u064A \u0644\u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636 \u0627\u0644\u0645\u0646\u0632\u0644 \u0641\u064A offmenu","Turn shelf-by-shelf inventory into a little checkout ritual. Scan your pantry, fridge and freezer, then discover what to cook.":"\u062D\u0648\u0651\u0644 \u062C\u0631\u062F \u0627\u0644\u0631\u0641\u0648\u0641 \u0625\u0644\u0649 \u0639\u0627\u062F\u0629 \u0628\u0633\u064A\u0637\u0629. \u0627\u0645\u0633\u062D \u062E\u0632\u0627\u0646\u0629 \u0627\u0644\u0637\u0639\u0627\u0645 \u0648\u0627\u0644\u062B\u0644\u0627\u062C\u0629 \u0648\u0627\u0644\u0645\u062C\u0645\u0651\u062F\u060C \u062B\u0645 \u0627\u0643\u062A\u0634\u0641 \u0645\u0627 \u064A\u0645\u0643\u0646\u0643 \u0637\u0647\u064A\u0647.","Interface language":"\u0644\u063A\u0629 \u0627\u0644\u0648\u0627\u062C\u0647\u0629","Interface language is saved on this device. Recipes and food names keep their source language.":"\u062A\u064F\u062D\u0641\u0638 \u0644\u063A\u0629 \u0627\u0644\u0648\u0627\u062C\u0647\u0629 \u0639\u0644\u0649 \u0647\u0630\u0627 \u0627\u0644\u062C\u0647\u0627\u0632. \u062A\u062D\u062A\u0641\u0638 \u0627\u0644\u0648\u0635\u0641\u0627\u062A \u0648\u0623\u0633\u0645\u0627\u0621 \u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0628\u0644\u063A\u062A\u0647\u0627 \u0627\u0644\u0623\u0635\u0644\u064A\u0629.","Skip to kitchen":"\u0627\u0646\u062A\u0642\u0644 \u0625\u0644\u0649 \u0627\u0644\u0645\u0637\u0628\u062E","Global data":"\u0627\u0644\u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0639\u0627\u0644\u0645\u064A\u0629","How it works":"\u0643\u064A\u0641 \u064A\u0639\u0645\u0644","Log in":"\u062A\u0633\u062C\u064A\u0644 \u0627\u0644\u062F\u062E\u0648\u0644","My kitchen \u2197":"\u0645\u0637\u0628\u062E\u064A \u2197","YOUR KITCHEN. YOUR CHECKOUT.":"\u0645\u0637\u0628\u062E\u0643. \u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636\u0643.","Dinner starts":"\u064A\u0628\u062F\u0623 \u0627\u0644\u0639\u0634\u0627\u0621","with what you":"\u0628\u0645\u0627 \u0644\u062F\u064A\u0643","already have.":"\u0628\u0627\u0644\u0641\u0639\u0644.","Scan a few foods, find meals that fit your household, and buy only what\u2019s missing. Start with five foods or one shelf.":"\u0627\u0645\u0633\u062D \u0628\u0639\u0636 \u0627\u0644\u0623\u0637\u0639\u0645\u0629\u060C \u0648\u0627\u0639\u062B\u0631 \u0639\u0644\u0649 \u0648\u062C\u0628\u0627\u062A \u062A\u0646\u0627\u0633\u0628 \u0623\u0633\u0631\u062A\u0643\u060C \u0648\u0627\u0634\u062A\u0631\u0650 \u0645\u0627 \u064A\u0646\u0642\u0635\u0643 \u0641\u0642\u0637. \u0627\u0628\u062F\u0623 \u0628\u062E\u0645\u0633\u0629 \u0623\u0635\u0646\u0627\u0641 \u0623\u0648 \u0631\u0641 \u0648\u0627\u062D\u062F.","Add my first food":"\u0623\u0636\u0641 \u0623\u0648\u0644 \u0637\u0639\u0627\u0645","Try a kitchen":"\u062C\u0631\u0651\u0628 \u0645\u0637\u0628\u062E\u064B\u0627","A SMALL RITUAL. A FRESH START.":"\u0639\u0627\u062F\u0629 \u0628\u0633\u064A\u0637\u0629. \u0628\u062F\u0627\u064A\u0629 \u062C\u062F\u064A\u062F\u0629.","Give your kitchen":"\u0627\u0645\u0646\u062D \u0645\u0637\u0628\u062E\u0643","a little shelf respect.":"\u0628\u0639\u0636 \u0627\u0644\u0639\u0646\u0627\u064A\u0629 \u0628\u0631\u0641\u0648\u0641\u0647.","No whole-house marathon required.":"\u0644\u0627 \u062A\u062D\u062A\u0627\u062C \u0625\u0644\u0649 \u062A\u0631\u062A\u064A\u0628 \u0627\u0644\u0645\u0646\u0632\u0644 \u0643\u0644\u0647.","Just one shelf and a clear bit of bench.":"\u064A\u0643\u0641\u064A \u0631\u0641 \u0648\u0627\u062D\u062F \u0648\u0645\u0633\u0627\u062D\u0629 \u062E\u0627\u0644\u064A\u0629 \u0639\u0644\u0649 \u0627\u0644\u0637\u0627\u0648\u0644\u0629.","Clear a shelf.":"\u0623\u0641\u0631\u063A \u0631\u0641\u064B\u0627.","Pick your pantry, fridge or freezer. Put its contents on the bench so you can see what\u2019s there.":"\u0627\u062E\u062A\u0631 \u062E\u0632\u0627\u0646\u0629 \u0627\u0644\u0637\u0639\u0627\u0645 \u0623\u0648 \u0627\u0644\u062B\u0644\u0627\u062C\u0629 \u0623\u0648 \u0627\u0644\u0645\u062C\u0645\u0651\u062F. \u0636\u0639 \u0645\u062D\u062A\u0648\u064A\u0627\u062A\u0647 \u0639\u0644\u0649 \u0627\u0644\u0637\u0627\u0648\u0644\u0629 \u0644\u062A\u0631\u0649 \u0645\u0627 \u0644\u062F\u064A\u0643.","Play shopkeeper.":"\u0627\u0645\u0633\u062D \u0623\u063A\u0631\u0627\u0636\u0643.","Scan each item straight onto your receipt. Glance at nutrition and enjoy the beep. Review it all at the end.":"\u0627\u0645\u0633\u062D \u0643\u0644 \u0635\u0646\u0641 \u0644\u0625\u0636\u0627\u0641\u062A\u0647 \u0625\u0644\u0649 \u0642\u0627\u0626\u0645\u062A\u0643. \u0627\u0637\u0651\u0644\u0639 \u0639\u0644\u0649 \u0628\u064A\u0627\u0646\u0627\u062A\u0647 \u0627\u0644\u063A\u0630\u0627\u0626\u064A\u0629 \u062B\u0645 \u0631\u0627\u062C\u0639 \u0627\u0644\u0642\u0627\u0626\u0645\u0629 \u0641\u064A \u0627\u0644\u0646\u0647\u0627\u064A\u0629.","Put the good stuff back.":"\u0623\u0639\u062F \u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0625\u0644\u0649 \u0645\u0643\u0627\u0646\u0647\u0627.","Review your receipt, update that shelf, then find a meal that starts with what you have.":"\u0631\u0627\u062C\u0639 \u0642\u0627\u0626\u0645\u062A\u0643 \u0648\u062D\u062F\u0651\u062B \u0627\u0644\u0631\u0641\u060C \u062B\u0645 \u0627\u062E\u062A\u0631 \u0648\u062C\u0628\u0629 \u0645\u0646 \u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0627\u0644\u0645\u0648\u062C\u0648\u062F\u0629 \u0644\u062F\u064A\u0643.","FRESH FROM THE SHOP":"\u0645\u0646 \u0627\u0644\u0645\u062A\u062C\u0631 \u0625\u0644\u0649 \u0645\u0637\u0628\u062E\u0643","Shopping bags in.":"\u0623\u062D\u0636\u0631\u062A \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A.","Kitchen sorted.":"\u0648\u0627\u0644\u0622\u0646 \u0631\u062A\u0651\u0628 \u0627\u0644\u0645\u0637\u0628\u062E.","Give new groceries the same checkout treatment before putting them away. Add to your shelves as you unpack.":"\u0627\u0645\u0633\u062D \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A \u0627\u0644\u062C\u062F\u064A\u062F\u0629 \u0642\u0628\u0644 \u062A\u062E\u0632\u064A\u0646\u0647\u0627\u060C \u0648\u0623\u0636\u0641\u0647\u0627 \u0625\u0644\u0649 \u0631\u0641\u0648\u0641\u0643 \u0623\u062B\u0646\u0627\u0621 \u062A\u0641\u0631\u064A\u063A \u0627\u0644\u0623\u0643\u064A\u0627\u0633.","Try an unpacking run \u2197":"\u062C\u0631\u0651\u0628 \u0625\u0636\u0627\u0641\u0629 \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A \u2197","Product information from Open Food Facts. Always check the package for allergens.":"\u0645\u0639\u0644\u0648\u0645\u0627\u062A \u0627\u0644\u0645\u0646\u062A\u062C\u0627\u062A \u0645\u0646 Open Food Facts. \u062A\u062D\u0642\u0651\u0642 \u062F\u0627\u0626\u0645\u064B\u0627 \u0645\u0646 \u0627\u0644\u0639\u0628\u0648\u0629 \u0644\u0645\u0639\u0631\u0641\u0629 \u0645\u0633\u0628\u0651\u0628\u0627\u062A \u0627\u0644\u062D\u0633\u0627\u0633\u064A\u0629.","YOUR HOME CHECKOUT":"\u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636 \u0645\u0637\u0628\u062E\u0643","Let\u2019s take stock.":"\u0644\u0646\u0631\u0627\u062C\u0639 \u0645\u0627 \u0644\u062F\u064A\u0646\u0627.","DEMO \xB7 SAMPLE PRODUCTS":"\u062A\u062C\u0631\u0628\u0629 \xB7 \u0645\u0646\u062A\u062C\u0627\u062A \u0646\u0645\u0648\u0630\u062C\u064A\u0629","\u266A Sound off":"\u266A \u0627\u0644\u0635\u0648\u062A \u0645\u062A\u0648\u0642\u0641","\u266A Sound on":"\u266A \u0627\u0644\u0635\u0648\u062A \u0645\u0641\u0639\u0651\u0644","Scan feedback \u2733":"\u062A\u0646\u0628\u064A\u0647\u0627\u062A \u0627\u0644\u0645\u0633\u062D \u2733","Profile & backup":"\u0627\u0644\u0645\u0644\u0641 \u0627\u0644\u0634\u062E\u0635\u064A \u0648\u0627\u0644\u0646\u0633\u062E \u0627\u0644\u0627\u062D\u062A\u064A\u0627\u0637\u064A","Exit demo":"\u0625\u0646\u0647\u0627\u0621 \u0627\u0644\u062A\u062C\u0631\u0628\u0629","\u2733 Today":"\u2733 \u0627\u0644\u064A\u0648\u0645","\u25A4 Kitchen":"\u25A4 \u0627\u0644\u0645\u0637\u0628\u062E","\u25A6 Plan":"\u25A6 \u0627\u0644\u062E\u0637\u0629","\u25C7 Shop":"\u25C7 \u0627\u0644\u062A\u0633\u0648\u0651\u0642","\u2667 Me":"\u2667 \u062D\u0633\u0627\u0628\u064A","\u25A5 Scan groceries":"\u25A5 \u0627\u0645\u0633\u062D \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A","+ Add food":"+ \u0623\u0636\u0641 \u0637\u0639\u0627\u0645\u064B\u0627","Saved on this device":"\u0645\u062D\u0641\u0648\u0638 \u0639\u0644\u0649 \u0647\u0630\u0627 \u0627\u0644\u062C\u0647\u0627\u0632","YOUR KITCHEN, YOUR WAY":"\u0645\u0637\u0628\u062E\u0643 \u0643\u0645\u0627 \u062A\u062D\u0628","People, preferences & progress.":"\u0627\u0644\u0623\u0634\u062E\u0627\u0635 \u0648\u0627\u0644\u062A\u0641\u0636\u064A\u0644\u0627\u062A \u0648\u0627\u0644\u062A\u0642\u062F\u0651\u0645.","\u2667 Dietary profiles":"\u2667 \u0627\u0644\u0645\u0644\u0641\u0627\u062A \u0627\u0644\u063A\u0630\u0627\u0626\u064A\u0629","\u25F7 Statistics & history":"\u25F7 \u0627\u0644\u0625\u062D\u0635\u0627\u0621\u0627\u062A \u0648\u0627\u0644\u0633\u062C\u0644","\u25A4 Printable documents & Kindle":"\u25A4 \u0645\u0633\u062A\u0646\u062F\u0627\u062A \u0644\u0644\u0637\u0628\u0627\u0639\u0629 \u0648Kindle","Account & backup":"\u0627\u0644\u062D\u0633\u0627\u0628 \u0648\u0627\u0644\u0646\u0633\u062E \u0627\u0644\u0627\u062D\u062A\u064A\u0627\u0637\u064A","Connections & developers":"\u0627\u0644\u0627\u062A\u0635\u0627\u0644\u0627\u062A \u0648\u0627\u0644\u0645\u0637\u0648\u0651\u0631\u0648\u0646","Large text":"\u0646\u0635 \u0643\u0628\u064A\u0631","Quiet mode \xB7 disable scan effects":"\u0627\u0644\u0648\u0636\u0639 \u0627\u0644\u0647\u0627\u062F\u0626 \xB7 \u062A\u0639\u0637\u064A\u0644 \u0645\u0624\u062B\u0631\u0627\u062A \u0627\u0644\u0645\u0633\u062D","People sharing this kitchen":"\u0627\u0644\u0623\u0634\u062E\u0627\u0635 \u0627\u0644\u0645\u0634\u0627\u0631\u0643\u0648\u0646 \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u0637\u0628\u062E","Trust, privacy & support":"\u0627\u0644\u062B\u0642\u0629 \u0648\u0627\u0644\u062E\u0635\u0648\u0635\u064A\u0629 \u0648\u0627\u0644\u062F\u0639\u0645","Clear this device\u2019s account data":"\u0627\u0645\u0633\u062D \u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u062D\u0633\u0627\u0628 \u0645\u0646 \u0647\u0630\u0627 \u0627\u0644\u062C\u0647\u0627\u0632","PICK YOUR NEXT LITTLE WIN":"\u0627\u062E\u062A\u0631 \u062E\u0637\u0648\u062A\u0643 \u0627\u0644\u062A\u0627\u0644\u064A\u0629","What\u2019s on the bench?":"\u0645\u0627\u0630\u0627 \u0639\u0644\u0649 \u0627\u0644\u0637\u0627\u0648\u0644\u0629\u061F","\u25A4 Rebuild a shelf":"\u25A4 \u0631\u062A\u0651\u0628 \u0631\u0641\u064B\u0627","\u2672 Garbage scan":"\u2672 \u0627\u0645\u0633\u062D \u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0644\u0644\u062A\u062E\u0644\u0651\u0635 \u0645\u0646\u0647\u0627","\u{1F6CD} Unpack shopping":"\u{1F6CD} \u0623\u0636\u0641 \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A",Pantry:"\u062E\u0632\u0627\u0646\u0629 \u0627\u0644\u0637\u0639\u0627\u0645",Fridge:"\u0627\u0644\u062B\u0644\u0627\u062C\u0629",Freezer:"\u0627\u0644\u0645\u062C\u0645\u0651\u062F","Dry goods & everyday staples":"\u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0627\u0644\u062C\u0627\u0641\u0629 \u0648\u0627\u0644\u0645\u0648\u0627\u062F \u0627\u0644\u0623\u0633\u0627\u0633\u064A\u0629","Fresh things & leftovers":"\u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0627\u0644\u0637\u0627\u0632\u062C\u0629 \u0648\u0628\u0642\u0627\u064A\u0627 \u0627\u0644\u0648\u062C\u0628\u0627\u062A","Future-you\u2019s favourite food":"\u0623\u0637\u0639\u0645\u0629 \u0645\u062D\u0641\u0648\u0638\u0629 \u0644\u0644\u0623\u064A\u0627\u0645 \u0627\u0644\u0642\u0627\u062F\u0645\u0629","Storage area":"\u0645\u0643\u0627\u0646 \u0627\u0644\u062A\u062E\u0632\u064A\u0646","Shelf / container":"\u0627\u0644\u0631\u0641 \u0623\u0648 \u0627\u0644\u062D\u0627\u0648\u064A\u0629","e.g. Bench":"\u0645\u062B\u0644: \u0627\u0644\u0637\u0627\u0648\u0644\u0629","e.g. Top shelf":"\u0645\u062B\u0644: \u0627\u0644\u0631\u0641 \u0627\u0644\u0639\u0644\u0648\u064A","Clear this shelf onto your bench. Its current inventory stays intact until you review and finish.":"\u0623\u0641\u0631\u063A \u0645\u062D\u062A\u0648\u064A\u0627\u062A \u0647\u0630\u0627 \u0627\u0644\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0637\u0627\u0648\u0644\u0629. \u0644\u0646 \u064A\u062A\u063A\u064A\u0651\u0631 \u0645\u062E\u0632\u0648\u0646\u0647 \u062D\u062A\u0649 \u062A\u0631\u0627\u062C\u0639 \u0627\u0644\u0642\u0627\u0626\u0645\u0629 \u0648\u062A\u0646\u0647\u064A \u0627\u0644\u0639\u0645\u0644\u064A\u0629.","Choose the source location. Scan items you are discarding; review the removal receipt before the inventory changes.":"\u0627\u062E\u062A\u0631 \u0645\u0643\u0627\u0646 \u0627\u0644\u062A\u062E\u0632\u064A\u0646. \u0627\u0645\u0633\u062D \u0627\u0644\u0623\u0635\u0646\u0627\u0641 \u0627\u0644\u062A\u064A \u0633\u062A\u062A\u062E\u0644\u0651\u0635 \u0645\u0646\u0647\u0627\u060C \u0648\u0631\u0627\u062C\u0639 \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0625\u0632\u0627\u0644\u0629 \u0642\u0628\u0644 \u062A\u063A\u064A\u064A\u0631 \u0627\u0644\u0645\u062E\u0632\u0648\u0646.","Choose where these groceries will go. Scan one destination at a time, then add them to the items already there.":"\u0627\u062E\u062A\u0631 \u0645\u0643\u0627\u0646 \u0647\u0630\u0647 \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A. \u0627\u0645\u0633\u062D \u0627\u0644\u0623\u0635\u0646\u0627\u0641 \u0644\u0643\u0644 \u0645\u0643\u0627\u0646 \u0639\u0644\u0649 \u062D\u062F\u0629\u060C \u062B\u0645 \u0623\u0636\u0641\u0647\u0627 \u0625\u0644\u0649 \u0627\u0644\u0645\u0648\u062C\u0648\u062F \u0641\u064A\u0647.","Open my checkout \u2197":"\u0627\u0628\u062F\u0623 \u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636\u064A \u2197","SHELF RESET":"\u0625\u0639\u0627\u062F\u0629 \u062A\u0631\u062A\u064A\u0628 \u0627\u0644\u0631\u0641","GARBAGE \xB7 SOURCE LOCATION":"\u0627\u0644\u062A\u062E\u0644\u0651\u0635 \u0645\u0646 \u0627\u0644\u0637\u0639\u0627\u0645 \xB7 \u0645\u0643\u0627\u0646 \u0627\u0644\u062A\u062E\u0632\u064A\u0646","GROCERY UNPACKING":"\u0625\u0636\u0627\u0641\u0629 \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A","Scan, check, then put it back.":"\u0627\u0645\u0633\u062D \u0648\u062A\u062D\u0642\u0651\u0642 \u062B\u0645 \u0623\u0639\u062F\u0647 \u0625\u0644\u0649 \u0645\u0643\u0627\u0646\u0647.","Pause & choose another shelf":"\u062A\u0648\u0642\u0651\u0641 \u0648\u0627\u062E\u062A\u0631 \u0631\u0641\u064B\u0627 \u0622\u062E\u0631","CHECKOUT OPEN":"\u0627\u0644\u0642\u0627\u0626\u0645\u0629 \u0645\u0641\u062A\u0648\u062D\u0629","Next item, please.":"\u0627\u0644\u0635\u0646\u0641 \u0627\u0644\u062A\u0627\u0644\u064A\u060C \u0645\u0646 \u0641\u0636\u0644\u0643.","Your bench \u2192 your shelf":"\u0645\u0646 \u0627\u0644\u0637\u0627\u0648\u0644\u0629 \u2190 \u0625\u0644\u0649 \u0627\u0644\u0631\u0641",ITEMS:"\u0623\u0635\u0646\u0627\u0641","THE SCANNING SPOT":"\u0645\u0646\u0637\u0642\u0629 \u0627\u0644\u0645\u0633\u062D","Bring on the beeps.":"\u0644\u0646\u0628\u062F\u0623 \u0627\u0644\u0645\u0633\u062D.","Scan next demo item \u25A5":"\u0627\u0645\u0633\u062D \u0627\u0644\u0635\u0646\u0641 \u0627\u0644\u062A\u062C\u0631\u064A\u0628\u064A \u0627\u0644\u062A\u0627\u0644\u064A \u25A5","How are you scanning?":"\u0643\u064A\u0641 \u062A\u0631\u064A\u062F \u0627\u0644\u0645\u0633\u062D\u061F","Handheld \xB7 rear camera":"\u0628\u0627\u0644\u064A\u062F \xB7 \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u062E\u0644\u0641\u064A\u0629","Screen-up bench \xB7 front camera":"\u0639\u0644\u0649 \u0627\u0644\u0637\u0627\u0648\u0644\u0629 \u0648\u0627\u0644\u0634\u0627\u0634\u0629 \u0644\u0644\u0623\u0639\u0644\u0649 \xB7 \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u0623\u0645\u0627\u0645\u064A\u0629","Hands-free stand \xB7 rear camera":"\u0639\u0644\u0649 \u062D\u0627\u0645\u0644 \xB7 \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u062E\u0644\u0641\u064A\u0629","Camera / lens":"\u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0623\u0648 \u0627\u0644\u0639\u062F\u0633\u0629","Rear camera (automatic)":"\u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u062E\u0644\u0641\u064A\u0629 (\u062A\u0644\u0642\u0627\u0626\u064A)","Front camera (automatic)":"\u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u0623\u0645\u0627\u0645\u064A\u0629 (\u062A\u0644\u0642\u0627\u0626\u064A)","Open camera scanner \u25A5":"\u0627\u0641\u062A\u062D \u0645\u0627\u0633\u062D \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u25A5","Stop camera":"\u0623\u0648\u0642\u0641 \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627","Live barcode camera preview":"\u0645\u0639\u0627\u064A\u0646\u0629 \u0645\u0628\u0627\u0634\u0631\u0629 \u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u0628\u0627\u0631\u0643\u0648\u062F","Whole barcode + blank edges":"\u0627\u0644\u0628\u0627\u0631\u0643\u0648\u062F \u0643\u0627\u0645\u0644\u064B\u0627 \u0645\u0639 \u062D\u0648\u0627\u0641 \u0641\u0627\u0631\u063A\u0629","Choose a setup, then open the camera.":"\u0627\u062E\u062A\u0631 \u0625\u0639\u062F\u0627\u062F \u0627\u0644\u0645\u0633\u062D \u062B\u0645 \u0627\u0641\u062A\u062D \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627.","Mirror preview":"\u0627\u0639\u0643\u0633 \u0627\u0644\u0645\u0639\u0627\u064A\u0646\u0629","Turn preview upside down":"\u0627\u0642\u0644\u0628 \u0627\u0644\u0645\u0639\u0627\u064A\u0646\u0629 \u0631\u0623\u0633\u064B\u0627 \u0639\u0644\u0649 \u0639\u0642\u0628","Light off":"\u0627\u0644\u0625\u0636\u0627\u0621\u0629 \u0645\u062A\u0648\u0642\u0641\u0629","Light on":"\u0627\u0644\u0625\u0636\u0627\u0621\u0629 \u0645\u0641\u0639\u0651\u0644\u0629","Focus, zoom & exposure":"\u0627\u0644\u062A\u0631\u0643\u064A\u0632 \u0648\u0627\u0644\u062A\u0643\u0628\u064A\u0631 \u0648\u0627\u0644\u062A\u0639\u0631\u064A\u0636",Barcode:"\u0627\u0644\u0628\u0627\u0631\u0643\u0648\u062F","Look up":"\u0627\u0628\u062D\u062B","Look up product":"\u0627\u0628\u062D\u062B \u0639\u0646 \u0627\u0644\u0645\u0646\u062A\u062C",Quantity:"\u0627\u0644\u0643\u0645\u064A\u0629",Unit:"\u0627\u0644\u0648\u062D\u062F\u0629",Ingredient:"\u0627\u0644\u0645\u0643\u0648\u0651\u0646","Product name":"\u0627\u0633\u0645 \u0627\u0644\u0645\u0646\u062A\u062C","Expiry date":"\u062A\u0627\u0631\u064A\u062E \u0627\u0644\u0627\u0646\u062A\u0647\u0627\u0621",Optional:"\u0627\u062E\u062A\u064A\u0627\u0631\u064A",Remove:"\u0625\u0632\u0627\u0644\u0629",Edit:"\u062A\u0639\u062F\u064A\u0644",Save:"\u062D\u0641\u0638",Cancel:"\u0625\u0644\u063A\u0627\u0621",Close:"\u0625\u063A\u0644\u0627\u0642",Delete:"\u062D\u0630\u0641",Add:"\u0625\u0636\u0627\u0641\u0629",Search:"\u0628\u062D\u062B",All:"\u0627\u0644\u0643\u0644",Unknown:"\u063A\u064A\u0631 \u0645\u0639\u0631\u0648\u0641",unknown:"\u063A\u064A\u0631 \u0645\u0639\u0631\u0648\u0641","Loading\u2026":"\u062C\u0627\u0631\u064D \u0627\u0644\u062A\u062D\u0645\u064A\u0644\u2026","Loading recipes\u2026":"\u062C\u0627\u0631\u064D \u062A\u062D\u0645\u064A\u0644 \u0627\u0644\u0648\u0635\u0641\u0627\u062A\u2026","Looking up\u2026":"\u062C\u0627\u0631\u064D \u0627\u0644\u0628\u062D\u062B\u2026","Review details at the end":"\u0631\u0627\u062C\u0639 \u0627\u0644\u062A\u0641\u0627\u0635\u064A\u0644 \u0641\u064A \u0627\u0644\u0646\u0647\u0627\u064A\u0629","Final receipt \u2192":"\u0627\u0644\u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0646\u0647\u0627\u0626\u064A\u0629 \u2190","Nothing scanned yet. Let\u2019s see what\u2019s hiding.":"\u0644\u0645 \u062A\u0645\u0633\u062D \u0623\u064A \u0635\u0646\u0641 \u0628\u0639\u062F. \u0644\u0646\u0643\u062A\u0634\u0641 \u0645\u0627 \u0644\u062F\u064A\u0643.","1 package":"\u0639\u0628\u0648\u0629 \u0648\u0627\u062D\u062F\u0629","Scan \u2192 beep \u2192 put it back. Every scan is accepted automatically.":"\u0627\u0645\u0633\u062D\u060C \u0648\u0627\u0633\u062A\u0645\u0639 \u0644\u0644\u062A\u0646\u0628\u064A\u0647\u060C \u062B\u0645 \u0623\u0639\u062F \u0627\u0644\u0635\u0646\u0641. \u064A\u064F\u0636\u0627\u0641 \u0643\u0644 \u0645\u0633\u062D \u062A\u0644\u0642\u0627\u0626\u064A\u064B\u0627.","From your shopping bag to its new home.":"\u0645\u0646 \u0643\u064A\u0633 \u0627\u0644\u062A\u0633\u0648\u0651\u0642 \u0625\u0644\u0649 \u0645\u0643\u0627\u0646\u0647 \u0627\u0644\u062C\u062F\u064A\u062F.","Scan recorded items from this location. Each scan stages removal of that whole recorded item.":"\u0627\u0645\u0633\u062D \u0627\u0644\u0623\u0635\u0646\u0627\u0641 \u0627\u0644\u0645\u0633\u062C\u0651\u0644\u0629 \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u0643\u0627\u0646. \u064A\u062C\u0647\u0651\u0632 \u0643\u0644 \u0645\u0633\u062D \u0625\u0632\u0627\u0644\u0629 \u0627\u0644\u0635\u0646\u0641 \u0627\u0644\u0645\u0633\u062C\u0651\u0644 \u0643\u0627\u0645\u0644\u064B\u0627.","Accepted. Next item, please.":"\u062A\u0645\u062A \u0627\u0644\u0625\u0636\u0627\u0641\u0629. \u0627\u0644\u0635\u0646\u0641 \u0627\u0644\u062A\u0627\u0644\u064A\u060C \u0645\u0646 \u0641\u0636\u0644\u0643.","Accepted. Looking up details while you keep scanning\u2026":"\u062A\u0645\u062A \u0627\u0644\u0625\u0636\u0627\u0641\u0629. \u062C\u0627\u0631\u064D \u0627\u0644\u0628\u062D\u062B \u0639\u0646 \u0627\u0644\u062A\u0641\u0627\u0635\u064A\u0644\u060C \u0648\u064A\u0645\u0643\u0646\u0643 \u0645\u062A\u0627\u0628\u0639\u0629 \u0627\u0644\u0645\u0633\u062D\u2026","Unknown product kept on your receipt. Keep scanning; review it at the end.":"\u0623\u064F\u0628\u0642\u064A \u0627\u0644\u0645\u0646\u062A\u062C \u063A\u064A\u0631 \u0627\u0644\u0645\u0639\u0631\u0648\u0641 \u0641\u064A \u0642\u0627\u0626\u0645\u062A\u0643. \u062A\u0627\u0628\u0639 \u0627\u0644\u0645\u0633\u062D \u0648\u0631\u0627\u062C\u0639\u0647 \u0641\u064A \u0627\u0644\u0646\u0647\u0627\u064A\u0629.","Product details unavailable.":"\u062A\u0641\u0627\u0635\u064A\u0644 \u0627\u0644\u0645\u0646\u062A\u062C \u063A\u064A\u0631 \u0645\u062A\u0627\u062D\u0629.","Lookup unavailable.":"\u0627\u0644\u0628\u062D\u062B \u063A\u064A\u0631 \u0645\u062A\u0627\u062D.","Enter or scan a barcode first.":"\u0623\u062F\u062E\u0644 \u0628\u0627\u0631\u0643\u0648\u062F \u0623\u0648 \u0627\u0645\u0633\u062D\u0647 \u0623\u0648\u0644\u064B\u0627.","Recipes imported.":"\u062A\u0645 \u0627\u0633\u062A\u064A\u0631\u0627\u062F \u0627\u0644\u0648\u0635\u0641\u0627\u062A.","No remaining matching inventory item in this source location. Nothing removed.":"\u0644\u0627 \u064A\u0648\u062C\u062F \u0635\u0646\u0641 \u0645\u0637\u0627\u0628\u0642 \u0645\u062A\u0628\u0642\u064D \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u0643\u0627\u0646. \u0644\u0645 \u064A\u064F\u062D\u0630\u0641 \u0634\u064A\u0621.","Demo kitchen \xB7 separate sample data.":"\u0645\u0637\u0628\u062E \u062A\u062C\u0631\u064A\u0628\u064A \xB7 \u0628\u064A\u0627\u0646\u0627\u062A \u0646\u0645\u0648\u0630\u062C\u064A\u0629 \u0645\u0646\u0641\u0635\u0644\u0629.","Signed in \xB7 automatic cloud saves; local copy available offline.":"\u062A\u0645 \u062A\u0633\u062C\u064A\u0644 \u0627\u0644\u062F\u062E\u0648\u0644 \xB7 \u062D\u0641\u0638 \u0633\u062D\u0627\u0628\u064A \u062A\u0644\u0642\u0627\u0626\u064A \u0648\u0646\u0633\u062E\u0629 \u0645\u062D\u0644\u064A\u0629 \u0645\u062A\u0627\u062D\u0629 \u062F\u0648\u0646 \u0627\u062A\u0635\u0627\u0644.","Guest pantry \xB7 saved in this browser.":"\u0645\u062E\u0632\u0648\u0646 \u0627\u0644\u0636\u064A\u0641 \xB7 \u0645\u062D\u0641\u0648\u0638 \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u062A\u0635\u0641\u062D.","Offline \xB7 Pantry and downloaded recipes work. New product and shop lookups need internet.":"\u062F\u0648\u0646 \u0627\u062A\u0635\u0627\u0644 \xB7 \u064A\u0639\u0645\u0644 \u0627\u0644\u0645\u062E\u0632\u0648\u0646 \u0648\u0627\u0644\u0648\u0635\u0641\u0627\u062A \u0627\u0644\u0645\u0646\u0632\u0651\u0644\u0629. \u064A\u062A\u0637\u0644\u0651\u0628 \u0627\u0644\u0628\u062D\u062B \u0639\u0646 \u0645\u0646\u062A\u062C\u0627\u062A \u0648\u0645\u062A\u0627\u062C\u0631 \u062C\u062F\u064A\u062F\u0629 \u0627\u062A\u0635\u0627\u0644\u064B\u0627 \u0628\u0627\u0644\u0625\u0646\u062A\u0631\u0646\u062A.","Demo changes stay separate from your kitchen.":"\u062A\u0628\u0642\u0649 \u062A\u063A\u064A\u064A\u0631\u0627\u062A \u0627\u0644\u062A\u062C\u0631\u0628\u0629 \u0645\u0646\u0641\u0635\u0644\u0629 \u0639\u0646 \u0645\u0637\u0628\u062E\u0643.","Local changes \xB7 saving automatically.":"\u062A\u063A\u064A\u064A\u0631\u0627\u062A \u0645\u062D\u0644\u064A\u0629 \xB7 \u062C\u0627\u0631\u064D \u0627\u0644\u062D\u0641\u0638 \u062A\u0644\u0642\u0627\u0626\u064A\u064B\u0627.","Guest data is saved in this browser.":"\u062A\u064F\u062D\u0641\u0638 \u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0636\u064A\u0641 \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u062A\u0635\u0641\u062D.","Guest data stays in this browser.":"\u062A\u0628\u0642\u0649 \u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0636\u064A\u0641 \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u062A\u0635\u0641\u062D.","Preferred country":"\u0627\u0644\u0628\u0644\u062F \u0627\u0644\u0645\u0641\u0636\u0651\u0644","Global \xB7 all countries":"\u0639\u0627\u0644\u0645\u064A \xB7 \u062C\u0645\u064A\u0639 \u0627\u0644\u0628\u0644\u062F\u0627\u0646","Preferred display units":"\u0648\u062D\u062F\u0627\u062A \u0627\u0644\u0639\u0631\u0636 \u0627\u0644\u0645\u0641\u0636\u0651\u0644\u0629",Metric:"\u0645\u062A\u0631\u064A",Imperial:"\u0625\u0645\u0628\u0631\u0627\u0637\u0648\u0631\u064A","Sign out":"\u062A\u0633\u062C\u064A\u0644 \u0627\u0644\u062E\u0631\u0648\u062C","Save kitchen to cloud \u2191":"\u0627\u062D\u0641\u0638 \u0627\u0644\u0645\u0637\u0628\u062E \u0641\u064A \u0627\u0644\u0633\u062D\u0627\u0628\u0629 \u2191","Restore cloud copy \u2193":"\u0627\u0633\u062A\u0639\u062F \u0627\u0644\u0646\u0633\u062E\u0629 \u0627\u0644\u0633\u062D\u0627\u0628\u064A\u0629 \u2193","Backups & recipe imports":"\u0627\u0644\u0646\u0633\u062E \u0627\u0644\u0627\u062D\u062A\u064A\u0627\u0637\u064A\u0629 \u0648\u0627\u0633\u062A\u064A\u0631\u0627\u062F \u0627\u0644\u0648\u0635\u0641\u0627\u062A","Export kitchen backup":"\u0635\u062F\u0651\u0631 \u0646\u0633\u062E\u0629 \u0627\u062D\u062A\u064A\u0627\u0637\u064A\u0629 \u0644\u0644\u0645\u0637\u0628\u062E","Sign in to restore your pantry on another device.":"\u0633\u062C\u0651\u0644 \u0627\u0644\u062F\u062E\u0648\u0644 \u0644\u0627\u0633\u062A\u0639\u0627\u062F\u0629 \u0645\u062E\u0632\u0648\u0646\u0643 \u0639\u0644\u0649 \u062C\u0647\u0627\u0632 \u0622\u062E\u0631.","Account setup pending. Guest pantry and offline recipes remain available.":"\u0625\u0639\u062F\u0627\u062F \u0627\u0644\u062D\u0633\u0627\u0628 \u0642\u064A\u062F \u0627\u0644\u0627\u0646\u062A\u0638\u0627\u0631. \u064A\u0638\u0644 \u0645\u062E\u0632\u0648\u0646 \u0627\u0644\u0636\u064A\u0641 \u0648\u0627\u0644\u0648\u0635\u0641\u0627\u062A \u062F\u0648\u0646 \u0627\u062A\u0635\u0627\u0644 \u0645\u062A\u0627\u062D\u064A\u0646.","Exit the demo to save your own kitchen.":"\u0623\u0646\u0647\u0650 \u0627\u0644\u062A\u062C\u0631\u0628\u0629 \u0644\u062D\u0641\u0638 \u0645\u0637\u0628\u062E\u0643 \u0627\u0644\u062E\u0627\u0635.","Cloud operation failed.":"\u0641\u0634\u0644\u062A \u0627\u0644\u0639\u0645\u0644\u064A\u0629 \u0627\u0644\u0633\u062D\u0627\u0628\u064A\u0629.","Replace this browser copy with the cloud save? Export local changes first.":"\u0647\u0644 \u062A\u0631\u064A\u062F \u0627\u0633\u062A\u0628\u062F\u0627\u0644 \u0646\u0633\u062E\u0629 \u0647\u0630\u0627 \u0627\u0644\u0645\u062A\u0635\u0641\u062D \u0628\u0627\u0644\u0646\u0633\u062E\u0629 \u0627\u0644\u0633\u062D\u0627\u0628\u064A\u0629\u061F \u0635\u062F\u0651\u0631 \u0627\u0644\u062A\u063A\u064A\u064A\u0631\u0627\u062A \u0627\u0644\u0645\u062D\u0644\u064A\u0629 \u0623\u0648\u0644\u064B\u0627.","Cloud copy restored.":"\u062A\u0645\u062A \u0627\u0633\u062A\u0639\u0627\u062F\u0629 \u0627\u0644\u0646\u0633\u062E\u0629 \u0627\u0644\u0633\u062D\u0627\u0628\u064A\u0629.","No cloud copy yet. Add items or import a backup, then save.":"\u0644\u0627 \u062A\u0648\u062C\u062F \u0646\u0633\u062E\u0629 \u0633\u062D\u0627\u0628\u064A\u0629 \u0628\u0639\u062F. \u0623\u0636\u0641 \u0623\u0635\u0646\u0627\u0641\u064B\u0627 \u0623\u0648 \u0627\u0633\u062A\u0648\u0631\u062F \u0646\u0633\u062E\u0629 \u0627\u062D\u062A\u064A\u0627\u0637\u064A\u0629\u060C \u062B\u0645 \u0627\u062D\u0641\u0638.","Saved to cloud. Automatic saving continues.":"\u062A\u0645 \u0627\u0644\u062D\u0641\u0638 \u0641\u064A \u0627\u0644\u0633\u062D\u0627\u0628\u0629. \u064A\u0633\u062A\u0645\u0631 \u0627\u0644\u062D\u0641\u0638 \u0627\u0644\u062A\u0644\u0642\u0627\u0626\u064A.","Check your email to confirm your account.":"\u062A\u062D\u0642\u0651\u0642 \u0645\u0646 \u0628\u0631\u064A\u062F\u0643 \u0627\u0644\u0625\u0644\u0643\u062A\u0631\u0648\u0646\u064A \u0644\u062A\u0623\u0643\u064A\u062F \u062D\u0633\u0627\u0628\u0643.","Check your email for recovery instructions.":"\u062A\u062D\u0642\u0651\u0642 \u0645\u0646 \u0628\u0631\u064A\u062F\u0643 \u0627\u0644\u0625\u0644\u0643\u062A\u0631\u0648\u0646\u064A \u0644\u0644\u062D\u0635\u0648\u0644 \u0639\u0644\u0649 \u062A\u0639\u0644\u064A\u0645\u0627\u062A \u0627\u0644\u0627\u0633\u062A\u0639\u0627\u062F\u0629.","Forgot password?":"\u0646\u0633\u064A\u062A \u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631\u061F","Set new password":"\u0639\u064A\u0651\u0646 \u0643\u0644\u0645\u0629 \u0645\u0631\u0648\u0631 \u062C\u062F\u064A\u062F\u0629",Email:"\u0627\u0644\u0628\u0631\u064A\u062F \u0627\u0644\u0625\u0644\u0643\u062A\u0631\u0648\u0646\u064A",Password:"\u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631","Create account":"\u0625\u0646\u0634\u0627\u0621 \u062D\u0633\u0627\u0628","YOUR INGREDIENTS, NEW IDEAS":"\u0645\u0643\u0648\u0651\u0646\u0627\u062A\u0643 \u0648\u0623\u0641\u0643\u0627\u0631 \u062C\u062F\u064A\u062F\u0629","START WITH WHAT YOU HAVE":"\u0627\u0628\u062F\u0623 \u0628\u0645\u0627 \u0644\u062F\u064A\u0643","Three ideas for dinner.":"\u062B\u0644\u0627\u062B \u0623\u0641\u0643\u0627\u0631 \u0644\u0644\u0639\u0634\u0627\u0621.","Household portions":"\u062D\u0635\u0635 \u0627\u0644\u0623\u0633\u0631\u0629","Refresh \u21BB":"\u062A\u062D\u062F\u064A\u062B \u21BB","Find a dish or ingredient":"\u0627\u0628\u062D\u062B \u0639\u0646 \u0637\u0628\u0642 \u0623\u0648 \u0645\u0643\u0648\u0651\u0646","e.g. rice, soup, coconut":"\u0645\u062B\u0644: \u0627\u0644\u0623\u0631\u0632 \u0623\u0648 \u0627\u0644\u062D\u0633\u0627\u0621 \u0623\u0648 \u062C\u0648\u0632 \u0627\u0644\u0647\u0646\u062F","Cook from":"\u0627\u0633\u062A\u062E\u062F\u0645 \u0645\u062E\u0632\u0648\u0646","Whole kitchen":"\u0627\u0644\u0645\u0637\u0628\u062E \u0643\u0644\u0647",Show:"\u0639\u0631\u0636","All menus":"\u062C\u0645\u064A\u0639 \u0627\u0644\u0648\u062C\u0628\u0627\u062A","Ready to cook":"\u062C\u0627\u0647\u0632 \u0644\u0644\u0637\u0647\u064A","Missing ingredients":"\u0645\u0643\u0648\u0651\u0646\u0627\u062A \u0646\u0627\u0642\u0635\u0629","Needs review":"\u064A\u062D\u062A\u0627\u062C \u0625\u0644\u0649 \u0645\u0631\u0627\u062C\u0639\u0629","Who is eating?":"\u0645\u0646 \u0633\u064A\u062A\u0646\u0627\u0648\u0644 \u0627\u0644\u0637\u0639\u0627\u0645\u061F","Cook this meal":"\u0627\u0637\u0647\u0650 \u0647\u0630\u0647 \u0627\u0644\u0648\u062C\u0628\u0629","Serve / after meal":"\u0642\u062F\u0651\u0645 \u0627\u0644\u0648\u062C\u0628\u0629 \u0623\u0648 \u0633\u062C\u0651\u0644\u0647\u0627","Save as favourite":"\u0627\u062D\u0641\u0638 \u0641\u064A \u0627\u0644\u0645\u0641\u0636\u0651\u0644\u0629","Saved favourite \u2713":"\u0645\u062D\u0641\u0648\u0638 \u0641\u064A \u0627\u0644\u0645\u0641\u0636\u0651\u0644\u0629 \u2713",Breakfast:"\u0627\u0644\u0641\u0637\u0648\u0631",Lunch:"\u0627\u0644\u063A\u062F\u0627\u0621",Dinner:"\u0627\u0644\u0639\u0634\u0627\u0621",Snack:"\u0648\u062C\u0628\u0629 \u062E\u0641\u064A\u0641\u0629",Meal:"\u0627\u0644\u0648\u062C\u0628\u0629",Date:"\u0627\u0644\u062A\u0627\u0631\u064A\u062E",Daily:"\u064A\u0648\u0645\u064A",Weekly:"\u0623\u0633\u0628\u0648\u0639\u064A",Portions:"\u0627\u0644\u062D\u0635\u0635","Planned meals":"\u0627\u0644\u0648\u062C\u0628\u0627\u062A \u0627\u0644\u0645\u062E\u0637\u0651\u0637\u0629","Planned portions":"\u0627\u0644\u062D\u0635\u0635 \u0627\u0644\u0645\u062E\u0637\u0651\u0637\u0629","All storage":"\u062C\u0645\u064A\u0639 \u0623\u0645\u0627\u0643\u0646 \u0627\u0644\u062A\u062E\u0632\u064A\u0646","Edit location":"\u0639\u062F\u0651\u0644 \u0645\u0643\u0627\u0646 \u0627\u0644\u062A\u062E\u0632\u064A\u0646","Edit preferences":"\u0639\u062F\u0651\u0644 \u0627\u0644\u062A\u0641\u0636\u064A\u0644\u0627\u062A","Remove member":"\u0623\u0632\u0644 \u0627\u0644\u0634\u062E\u0635","Add people, their preferences and dietary advisors to personalise your menus.":"\u0623\u0636\u0641 \u0627\u0644\u0623\u0634\u062E\u0627\u0635 \u0648\u062A\u0641\u0636\u064A\u0644\u0627\u062A\u0647\u0645 \u0648\u062E\u064A\u0627\u0631\u0627\u062A\u0647\u0645 \u0627\u0644\u063A\u0630\u0627\u0626\u064A\u0629 \u0644\u062A\u062E\u0635\u064A\u0635 \u0627\u0644\u0648\u062C\u0628\u0627\u062A.","Recipe no longer available":"\u0627\u0644\u0648\u0635\u0641\u0629 \u0644\u0645 \u062A\u0639\u062F \u0645\u062A\u0627\u062D\u0629","Meal nutrients & notes":"\u0645\u063A\u0630\u0651\u064A\u0627\u062A \u0627\u0644\u0648\u062C\u0628\u0629 \u0648\u0627\u0644\u0645\u0644\u0627\u062D\u0638\u0627\u062A","Delete log":"\u0627\u062D\u0630\u0641 \u0627\u0644\u0633\u062C\u0644","AFTER THE LAST BITE":"\u0628\u0639\u062F \u0627\u0644\u0648\u062C\u0628\u0629","How did the meal go?":"\u0643\u064A\u0641 \u0643\u0627\u0646\u062A \u0627\u0644\u0648\u062C\u0628\u0629\u061F","Recipe or custom meal":"\u0648\u0635\u0641\u0629 \u0623\u0648 \u0648\u062C\u0628\u0629 \u0645\u062E\u0635\u0651\u0635\u0629","Date eaten":"\u062A\u0627\u0631\u064A\u062E \u062A\u0646\u0627\u0648\u0644 \u0627\u0644\u0637\u0639\u0627\u0645","Who ate this?":"\u0645\u0646 \u062A\u0646\u0627\u0648\u0644 \u0647\u0630\u0647 \u0627\u0644\u0648\u062C\u0628\u0629\u061F","Portions served":"\u0627\u0644\u062D\u0635\u0635 \u0627\u0644\u0645\u0642\u062F\u0651\u0645\u0629","Eaten (%) \xB7 optional":"\u0627\u0644\u0646\u0633\u0628\u0629 \u0627\u0644\u0645\u0623\u0643\u0648\u0644\u0629 (%) \xB7 \u0627\u062E\u062A\u064A\u0627\u0631\u064A","100 if left blank":"\u0661\u0660\u0660 \u0625\u0630\u0627 \u062A\u064F\u0631\u0643 \u0641\u0627\u0631\u063A\u064B\u0627","What happened to the rest?":"\u0645\u0627\u0630\u0627 \u062D\u062F\u062B \u0644\u0644\u0628\u0627\u0642\u064A\u061F","Not recorded":"\u063A\u064A\u0631 \u0645\u0633\u062C\u0651\u0644","Saved for later":"\u0645\u062D\u0641\u0648\u0638 \u0644\u0648\u0642\u062A \u0644\u0627\u062D\u0642",Discarded:"\u062A\u0645 \u0627\u0644\u062A\u062E\u0644\u0651\u0635 \u0645\u0646\u0647","Shared with someone else":"\u062A\u0645\u062A \u0645\u0634\u0627\u0631\u0643\u062A\u0647 \u0645\u0639 \u0634\u062E\u0635 \u0622\u062E\u0631","Meal name":"\u0627\u0633\u0645 \u0627\u0644\u0648\u062C\u0628\u0629","Meal notes":"\u0645\u0644\u0627\u062D\u0638\u0627\u062A \u0627\u0644\u0648\u062C\u0628\u0629","Likes, dislikes, leftovers\u2026":"\u0645\u0627 \u0623\u0639\u062C\u0628\u0643 \u0648\u0645\u0627 \u0644\u0645 \u064A\u0639\u062C\u0628\u0643 \u0648\u0628\u0642\u0627\u064A\u0627 \u0627\u0644\u0637\u0639\u0627\u0645\u2026","Save after-meal record \u2713":"\u0627\u062D\u0641\u0638 \u0633\u062C\u0644 \u0645\u0627 \u0628\u0639\u062F \u0627\u0644\u0648\u062C\u0628\u0629 \u2713",Energy:"\u0627\u0644\u0637\u0627\u0642\u0629",Protein:"\u0627\u0644\u0628\u0631\u0648\u062A\u064A\u0646",Carbohydrates:"\u0627\u0644\u0643\u0631\u0628\u0648\u0647\u064A\u062F\u0631\u0627\u062A",Fat:"\u0627\u0644\u062F\u0647\u0648\u0646",Fibre:"\u0627\u0644\u0623\u0644\u064A\u0627\u0641",Sugar:"\u0627\u0644\u0633\u0643\u0631",Sodium:"\u0627\u0644\u0635\u0648\u062F\u064A\u0648\u0645",Salt:"\u0627\u0644\u0645\u0644\u062D","Search recipes":"\u0627\u0628\u062D\u062B \u0639\u0646 \u0627\u0644\u0648\u0635\u0641\u0627\u062A","Read recipe & review quantities":"\u0627\u0642\u0631\u0623 \u0627\u0644\u0648\u0635\u0641\u0629 \u0648\u0631\u0627\u062C\u0639 \u0627\u0644\u0643\u0645\u064A\u0627\u062A","Show more recipes":"\u0627\u0639\u0631\u0636 \u0627\u0644\u0645\u0632\u064A\u062F \u0645\u0646 \u0627\u0644\u0648\u0635\u0641\u0627\u062A","Source instructions":"\u062A\u0639\u0644\u064A\u0645\u0627\u062A \u0627\u0644\u0645\u0635\u062F\u0631","Review for my kitchen":"\u0631\u0627\u062C\u0639\u0647\u0627 \u0644\u0645\u0637\u0628\u062E\u064A","Reviewed serving yield":"\u0639\u062F\u062F \u0627\u0644\u062D\u0635\u0635 \u0628\u0639\u062F \u0627\u0644\u0645\u0631\u0627\u062C\u0639\u0629","Save my reviewed recipe":"\u0627\u062D\u0641\u0638 \u0648\u0635\u0641\u062A\u064A \u0627\u0644\u0645\u0631\u0627\u062C\u064E\u0639\u0629","Download source recipe as JSON-LD":"\u0646\u0632\u0651\u0644 \u0648\u0635\u0641\u0629 \u0627\u0644\u0645\u0635\u062F\u0631 \u0628\u0635\u064A\u063A\u0629 JSON-LD","Keep the kitchen current.":"\u062D\u062F\u0651\u062B \u062D\u0627\u0644\u0629 \u0627\u0644\u0645\u0637\u0628\u062E.","Inventory item":"\u0627\u0644\u0635\u0646\u0641 \u0641\u064A \u0627\u0644\u0645\u062E\u0632\u0648\u0646","Label use-by date (optional)":"\u062A\u0627\u0631\u064A\u062E \u0627\u0644\u0627\u0633\u062A\u062E\u062F\u0627\u0645 \u0639\u0644\u0649 \u0627\u0644\u0639\u0628\u0648\u0629 (\u0627\u062E\u062A\u064A\u0627\u0631\u064A)","Estimated check reminder, days from today (optional)":"\u062A\u0630\u0643\u064A\u0631 \u062A\u0642\u062F\u064A\u0631\u064A \u0628\u0627\u0644\u0641\u062D\u0635\u060C \u0628\u0627\u0644\u0623\u064A\u0627\u0645 \u0645\u0646 \u0627\u0644\u064A\u0648\u0645 (\u0627\u062E\u062A\u064A\u0627\u0631\u064A)","Choose based on this item and storage":"\u0627\u062E\u062A\u0631 \u062D\u0633\u0628 \u0627\u0644\u0635\u0646\u0641 \u0648\u0638\u0631\u0648\u0641 \u062A\u062E\u0632\u064A\u0646\u0647","Use suggested check interval":"\u0627\u0633\u062A\u062E\u062F\u0645 \u0641\u062A\u0631\u0629 \u0627\u0644\u0641\u062D\u0635 \u0627\u0644\u0645\u0642\u062A\u0631\u062D\u0629","Reminder note":"\u0645\u0644\u0627\u062D\u0638\u0629 \u0627\u0644\u062A\u0630\u0643\u064A\u0631","e.g. opened today; check freshness":"\u0645\u062B\u0644: \u0641\u064F\u062A\u062D \u0627\u0644\u064A\u0648\u0645\u061B \u062A\u062D\u0642\u0651\u0642 \u0645\u0646 \u062D\u0627\u0644\u062A\u0647","Save dates & reminder":"\u0627\u062D\u0641\u0638 \u0627\u0644\u062A\u0648\u0627\u0631\u064A\u062E \u0648\u0627\u0644\u062A\u0630\u0643\u064A\u0631","Close recipe":"\u0623\u063A\u0644\u0642 \u0627\u0644\u0648\u0635\u0641\u0629","Close meal log":"\u0623\u063A\u0644\u0642 \u0633\u062C\u0644 \u0627\u0644\u0648\u062C\u0628\u0629","Close freshness settings":"\u0623\u063A\u0644\u0642 \u0625\u0639\u062F\u0627\u062F\u0627\u062A \u0627\u0644\u062A\u0630\u0643\u064A\u0631","Kitchen navigation":"\u0627\u0644\u062A\u0646\u0642\u0651\u0644 \u0641\u064A \u0627\u0644\u0645\u0637\u0628\u062E","offmenu home":"\u0635\u0641\u062D\u0629 offmenu \u0627\u0644\u0631\u0626\u064A\u0633\u064A\u0629","Not available":"\u063A\u064A\u0631 \u0645\u062A\u0627\u062D","not available":"\u063A\u064A\u0631 \u0645\u062A\u0627\u062D","Food data & estimated nutrition":"\u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0637\u0639\u0627\u0645 \u0648\u0627\u0644\u062A\u063A\u0630\u064A\u0629 \u0627\u0644\u062A\u0642\u062F\u064A\u0631\u064A\u0629","Add a meal to see shopping gaps.":"\u0623\u0636\u0641 \u0648\u062C\u0628\u0629 \u0644\u0631\u0624\u064A\u0629 \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A \u0627\u0644\u0646\u0627\u0642\u0635\u0629.","Add a menu to build your ingredient list.":"\u0623\u0636\u0641 \u0648\u062C\u0628\u0629 \u0644\u0625\u0646\u0634\u0627\u0621 \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0645\u0643\u0648\u0651\u0646\u0627\u062A.","Unmeasured ingredients to review":"\u0645\u0643\u0648\u0651\u0646\u0627\u062A \u063A\u064A\u0631 \u0645\u0642\u0627\u0633\u0629 \u062A\u062D\u062A\u0627\u062C \u0625\u0644\u0649 \u0645\u0631\u0627\u062C\u0639\u0629","No measured ingredient gaps. Check unmeasured ingredients below.":"\u0644\u0627 \u062A\u0648\u062C\u062F \u0645\u0643\u0648\u0651\u0646\u0627\u062A \u0645\u0642\u0627\u0633\u0629 \u0646\u0627\u0642\u0635\u0629. \u0631\u0627\u062C\u0639 \u0627\u0644\u0645\u0643\u0648\u0651\u0646\u0627\u062A \u063A\u064A\u0631 \u0627\u0644\u0645\u0642\u0627\u0633\u0629 \u0623\u062F\u0646\u0627\u0647.","Your food journal starts with the next meal. Log a recipe or enter totals from a label.":"\u064A\u0628\u062F\u0623 \u0633\u062C\u0644 \u0637\u0639\u0627\u0645\u0643 \u0628\u0627\u0644\u0648\u062C\u0628\u0629 \u0627\u0644\u062A\u0627\u0644\u064A\u0629. \u0633\u062C\u0651\u0644 \u0648\u0635\u0641\u0629 \u0623\u0648 \u0623\u062F\u062E\u0644 \u0627\u0644\u0625\u062C\u0645\u0627\u0644\u064A\u0627\u062A \u0645\u0646 \u0627\u0644\u0639\u0628\u0648\u0629.","Unavailable source text":"\u0646\u0635 \u0627\u0644\u0645\u0635\u062F\u0631 \u063A\u064A\u0631 \u0645\u062A\u0627\u062D","Nutrient metric":"\u0627\u0644\u0645\u0624\u0634\u0631 \u0627\u0644\u063A\u0630\u0627\u0626\u064A",Status:"\u0627\u0644\u062D\u0627\u0644\u0629",Total:"\u0627\u0644\u0625\u062C\u0645\u0627\u0644\u064A","Known subtotal":"\u0627\u0644\u0625\u062C\u0645\u0627\u0644\u064A \u0627\u0644\u062C\u0632\u0626\u064A \u0627\u0644\u0645\u0639\u0631\u0648\u0641","Per 1,000 kcal":"\u0644\u0643\u0644 \u0661\u0660\u0660\u0660 \u0633\u0639\u0631\u0629 \u062D\u0631\u0627\u0631\u064A\u0629","Mass coverage":"\u062A\u063A\u0637\u064A\u0629 \u0627\u0644\u0643\u062A\u0644\u0629","Done.":"\u062A\u0645\u0651.",Country:"\u0627\u0644\u0628\u0644\u062F",Evidence:"\u0627\u0644\u0623\u062F\u0644\u0629","Global food and evidence workspace":"\u0645\u0633\u0627\u062D\u0629 \u0639\u0645\u0644 \u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0637\u0639\u0627\u0645 \u0648\u0627\u0644\u0623\u062F\u0644\u0629 \u0627\u0644\u0639\u0627\u0644\u0645\u064A\u0629","OffMenu \xB7 Global data workspace":"OffMenu \xB7 \u0645\u0633\u0627\u062D\u0629 \u0639\u0645\u0644 \u0627\u0644\u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0639\u0627\u0644\u0645\u064A\u0629","\u2190 My kitchen":"\u2190 \u0645\u0637\u0628\u062E\u064A","Open country":"\u0627\u0639\u0631\u0636 \u0627\u0644\u0628\u0644\u062F","Country coverage and starter baskets":"\u062A\u063A\u0637\u064A\u0629 \u0627\u0644\u0628\u0644\u062F\u0627\u0646 \u0648\u0633\u0644\u0627\u0644 \u0627\u0644\u0628\u062F\u0627\u064A\u0629","Calculate nutrients and coverage":"\u0627\u062D\u0633\u0628 \u0627\u0644\u0639\u0646\u0627\u0635\u0631 \u0627\u0644\u063A\u0630\u0627\u0626\u064A\u0629 \u0648\u0627\u0644\u062A\u063A\u0637\u064A\u0629","Native language support":"\u062F\u0639\u0645 \u0627\u0644\u0644\u063A\u0629 \u0627\u0644\u0623\u0635\u0644\u064A\u0629","National sources / access":"\u0627\u0644\u0645\u0635\u0627\u062F\u0631 \u0627\u0644\u0648\u0637\u0646\u064A\u0629 \u0648\u0625\u0645\u0643\u0627\u0646\u064A\u0629 \u0627\u0644\u0648\u0635\u0648\u0644","Current offmenu coverage":"\u062A\u063A\u0637\u064A\u0629 offmenu \u0627\u0644\u062D\u0627\u0644\u064A\u0629","Source-specific identity":"\u0647\u0648\u064A\u0629 \u062E\u0627\u0635\u0629 \u0628\u0627\u0644\u0645\u0635\u062F\u0631","Candidate identity link":"\u0631\u0627\u0628\u0637 \u0647\u0648\u064A\u0629 \u0645\u0631\u0634\u0651\u062D","Curated concept":"\u0645\u0641\u0647\u0648\u0645 \u0645\u064F\u0631\u0627\u062C\u0639","Identified resource":"\u0645\u0648\u0631\u062F \u0645\u062D\u062F\u0651\u062F \u0627\u0644\u0647\u0648\u064A\u0629","Source assertion":"\u0628\u064A\u0627\u0646 \u0645\u0646 \u0627\u0644\u0645\u0635\u062F\u0631",Candidate:"\u0645\u0631\u0634\u0651\u062D","Editor authored":"\u0645\u0646 \u062A\u0623\u0644\u064A\u0641 \u0627\u0644\u0645\u062D\u0631\u0651\u0631",Reviewed:"\u0645\u064F\u0631\u0627\u062C\u0639",Verified:"\u0645\u062A\u062D\u0642\u0651\u0642 \u0645\u0646\u0647",Conflicting:"\u0645\u062A\u0639\u0627\u0631\u0636",Superseded:"\u0645\u0633\u062A\u0628\u062F\u064E\u0644","Needs transcription":"\u064A\u062D\u062A\u0627\u062C \u0625\u0644\u0649 \u062A\u0641\u0631\u064A\u063A \u0627\u0644\u0646\u0635","Recipe Variant":"\u0646\u0633\u062E\u0629 \u0645\u0646 \u0648\u0635\u0641\u0629","Recipe Step":"\u062E\u0637\u0648\u0629 \u0641\u064A \u0627\u0644\u0648\u0635\u0641\u0629","Recipe Concept":"\u0645\u0641\u0647\u0648\u0645 \u0648\u0635\u0641\u0629",instruction:"\u062A\u0639\u0644\u064A\u0645\u0627\u062A",position:"\u0627\u0644\u062A\u0631\u062A\u064A\u0628","original Source Record":"\u0633\u062C\u0644 \u0627\u0644\u0645\u0635\u062F\u0631 \u0627\u0644\u0623\u0635\u0644\u064A"});var qh=Object.freeze(["en","ar"]);var lx=Object.freeze([{code:"en",name:"English",direction:"ltr"},{code:"ar",name:"\u0627\u0644\u0639\u0631\u0628\u064A\u0629",direction:"rtl"}]);var Yh={ar:uc},xi=new Map,dc="en";function rr(e,t={},r=dc){if(typeof e=="number")return new Intl.NumberFormat(r,{maximumFractionDigits:20}).format(e);let i=String(e??""),n=Yh[r]||{},a=Object.hasOwn(n,i)?n[i]:i,o=Number.isFinite(t.count)?new Intl.PluralRules(r).select(t.count):"other",c=(typeof a=="string"?a:a[o]||a.other||i).replace(/\{([\w]+)\}/g,(d,h)=>Object.hasOwn(t,h)?typeof t[h]=="number"?new Intl.NumberFormat(r,{maximumFractionDigits:20}).format(t[h]):String(t[h]):d),u=xi.get(i),l=Object.hasOwn(n,i)?r:u&&!Object.keys(t).length?u:"en";return xi.size>=2e3&&xi.delete(xi.keys().next().value),xi.set(c,l),c}function Kh(e){return xi.get(String(e))}function Xr(e,t,r={},i=dc){let n=rr(t,r,i);e.textContent=n,e.lang=typeof t=="number"?i:Kh(n)||"en",e.dir="auto"}var _o=["ean_13","ean_8","upc_a","upc_e"];function hc({gap:e=1200,misses:t=4,confirmations:r=2}={}){let i="",n="",a=0,o=0,s=null,c=0;return{observe(u,l){let d=[...new Set(u.filter(Boolean))];if(d.length!==1)return n="",a=0,d.length?(s=null,c=0,null):(s??=l,++c>=t&&l-s>=e&&(i=""),null);s=null,c=0;let h=d[0];return h===n&&l-o<=1800?a++:(n=h,a=1),o=l,a<r||i===h?null:(i=h,h)},rearm(){i="",n="",a=0,s=null,c=0}}}function pc(e){return{NotAllowedError:"Camera permission is blocked. Allow the camera in this site\u2019s browser settings, then retry.",NotFoundError:"No camera found. Connect a camera or use a barcode photo or manual entry.",NotReadableError:"The camera is busy. Close other camera apps and retry.",OverconstrainedError:"This camera cannot use those settings. Try another camera.",SecurityError:"Open OffMenu directly over HTTPS to use the camera."}[e?.name]||"Camera could not start. Try another camera, a barcode photo, or manual entry."}var zn="offmenu-decoder-capture/1",fc=8192,Jh=128,mc=Object.freeze({ean_13:"EAN-13",EAN13:"EAN-13","EAN-13":"EAN-13",ean_8:"EAN-8",EAN8:"EAN-8","EAN-8":"EAN-8",upc_a:"UPC-A",UPCA:"UPC-A","UPC-A":"UPC-A",upc_e:"UPC-E",UPCE:"UPC-E","UPC-E":"UPC-E",ITF:"ITF",itf:"ITF","ITF-14":"ITF",ITF14:"ITF"});function Zh(e){if(e==null||e==="")return{value:null,state:"absent"};if(typeof e!="string"||e.length>fc)return{value:null,state:"unsupported-or-oversize"};try{let t=JSON.parse(e);return!t||typeof t!="object"||Array.isArray(t)||typeof t.UPCE!="string"?{value:null,state:"no-UPCE"}:{value:t.UPCE,state:"present"}}catch{return{value:null,state:"invalid-json"}}}function tn(e,t){let r=e?.rawValue??e?.text,i=e?.format??null,n=typeof i=="string"?mc[i]??null:null,a=e?.extra??null,o=Zh(a),s={schema:zn,namespace:"barcode",decoderPath:t,decoderText:typeof r=="string"?r:null,returnedFormat:i,rawExtra:a,extraState:o.state,extraUPCE:o.value,labelledDerived:null,lookupLexicalValue:null,lookupSymbology:null,lookupOrigin:null,typed:null,status:"manual-required",reason:"decoder-result-unavailable"},c=(l,d,h=null,m=null,g=null)=>(s.status=l,s.reason=d,s.lookupLexicalValue=h,s.lookupSymbology=m,s.lookupOrigin=g,h&&(s.typed=Pl({original:h,namespace:"barcode",representationHint:m,observedCarrier:n==="ITF"?"ITF":i})),s);if(e?.error||typeof r!="string"||!r.length||r.length>Jh||/[\x00-\x1f\x7f]/.test(r))return c("manual-required","decoder-text-unavailable-or-out-of-bounds");if(a!=null&&(typeof a!="string"||a.length>fc))return c("manual-required","decoder-extra-unavailable-or-out-of-bounds");if(!n)return c("unsupported","decoder-format-not-enabled");if(n==="ITF")return c("literal-untyped","generic-ITF-does-not-declare-GTIN",r,null,"decoder-text");if(n==="UPC-E"){if(r.length===8)return Zi(r)?o.value!==null&&o.value!==r?c("manual-required","UPC-E-extra-conflicts-with-decoder-text"):o.state==="unsupported-or-oversize"||o.state==="invalid-json"?c("manual-required","UPC-E-extra-unreadable"):c("ready","validated-compressed-UPC-E",r,"UPC-E","decoder-text"):c("manual-required","UPC-E-syntax-or-checksum-invalid");if(r.length!==12&&r.length!==13)return c("manual-required","normalized-UPC-E-text-has-unsupported-width");if(o.state!=="present")return c("manual-required","compressed-UPC-E-extra-missing");let l=Zi(o.value);return!l||r!==l&&r!=="0"+l?c("manual-required","UPC-E-extra-conflicts-with-normalized-text"):c("ready","validated-UPC-E-extra-against-normalized-text",o.value,"UPC-E","validated-decoder-extra.UPCE")}if(n==="UPC-A"&&r.length===13&&r.startsWith("0")&&fr(r))return s.labelledDerived={value:r.slice(1),representation:"UPC-A",rule:"leading-zero-EAN-13-to-UPC-A; printed original unverified"},c("ready","UPC-A-decoder-returned-leading-zero-EAN-13-text",r,null,"decoder-returned-13-digit-form; printed-original-unverified");let u=n==="UPC-A"?12:n==="EAN-13"?13:8;return r.length!==u||!fr(r)?c("manual-required","decoder-representation-syntax-or-checksum-invalid"):c("ready","validated-decoder-text",r,n,"decoder-text")}function Hn(e,t){return(e||[]).map(r=>tn(r,t)).filter(r=>r.status==="ready")}function Gn(e,t){return(e||[]).some(r=>{let i=tn(r,t);return i.returnedFormat!==null&&mc[i.returnedFormat]==="UPC-E"&&i.status==="manual-required"})}function gc(e){return e?.schema!==zn||e.status!=="ready"?null:{schema:zn,decoderPath:e.decoderPath,decoderText:e.decoderText,returnedFormat:e.returnedFormat,rawExtra:e.rawExtra,lookupLexicalValue:e.lookupLexicalValue,lookupSymbology:e.lookupSymbology,lookupOrigin:e.lookupOrigin,labelledDerived:e.labelledDerived}}function vc(e,t,r){if(e==null)return!0;if(e.schema!==zn||!["native","zxing-wasm","photo-zxing-wasm"].includes(e.decoderPath))return!1;let i=tn({text:e.decoderText,format:e.returnedFormat,extra:e.rawExtra},e.decoderPath);return i.status==="ready"&&i.lookupLexicalValue===t&&i.lookupSymbology===r&&i.lookupOrigin===e.lookupOrigin&&JSON.stringify(i.labelledDerived)===JSON.stringify(e.labelledDerived)}function $h(e,t,r,i,{mirror:n=!1,rotate:a=!1,fit:o="cover"}={}){if(!(e>0&&t>0&&r?.width>0&&r?.height>0&&i?.width>0&&i?.height>0))return null;let s=o==="contain"?Math.min(r.width/e,r.height/t):Math.max(r.width/e,r.height/t),c=r.left+(r.width-e*s)/2,u=r.top+(r.height-t*s)/2,l=Math.max(r.left,c,i.left),d=Math.max(r.top,u,i.top),h=Math.min(r.left+r.width,c+e*s,i.left+i.width),m=Math.min(r.top+r.height,u+t*s,i.top+i.height);if(h-l<24||m-d<24)return null;let g=(l-c)/s,_=(d-u)/s,f=(h-l)/s,p=(m-d)/s;return!!n!=!!a&&(g=e-g-f),a&&(_=t-_-p),{sx:Math.max(0,g),sy:Math.max(0,_),sw:Math.min(f,e-Math.max(0,g)),sh:Math.min(p,t-Math.max(0,_))}}function _c({canScan:e,onCode:t,onStream:r,onStartGesture:i,autoResume:n=!1,storage:a}){let o=z=>document.getElementById(z),s=o("video"),c=document.createElement("canvas"),u=c.getContext("2d",{willReadFrequently:!0}),l=hc(),d=null,h=0,m=null,g=null,_=null,f=0,p=null,R=null,y=!1,A=!1,O=-1,I=0,C=0,U=0,S=[],x=null,M={mode:"handheld",camera:"environment",mirror:!1,rotate:!1,enhance:!0};try{M={...M,...JSON.parse((a??localStorage).getItem("offmenu-scanner-v2")||"{}")}}catch{}["handheld","bench","stand"].includes(M.mode)||(M.mode="bench");let k=z=>{Xr(o("scanner-status"),z)},H=()=>{try{(a??localStorage).setItem("offmenu-scanner-v2",JSON.stringify(M))}catch{}},V=z=>z&&Number.isFinite(z.min)&&Number.isFinite(z.max)&&z.max>z.min,Z=()=>{try{return x?.getCapabilities?.()||{}}catch{return{}}};function G(){s.style.transform=`rotate(${M.rotate?180:0}deg) scaleX(${M.mirror?-1:1})`,o("scanner-mirror").checked=M.mirror,o("scanner-rotate").checked=M.rotate,o("scanner-enhance").checked=M.enhance}function ee(){o("scanner-mode").value=M.mode,Xr(o("scanner-placement"),M.mode==="bench"?rr("Screen-up bench: front camera faces the barcode. Start around 30\u201350 cm away and move slowly until the bars look sharp. Fixed-focus lenses may need more distance; use a rear-camera stand if they stay blurry."):M.mode==="stand"?rr("Hands-free rear: prop the phone securely upright or in a stand, with the rear lens exposed. Move each barcode into view and pause for the beep. A phone lying screen-up blocks its rear camera."):rr("Handheld: rear camera recommended. Start around 15\u201330 cm from the barcode; move back if it blurs. Keep the entire code and its blank edges visible. Tilt shiny packaging away from glare."))}async function W(z){if(navigator.wakeLock?.request)try{let ae=await navigator.wakeLock.request("screen");z!==h||!y?await ae.release():R=ae}catch{}}function ie(){g?.terminate(),g=null,_&&(clearTimeout(_.timeout),_.reject(Error(rr("Decoder stopped"))),_=null)}function ce({announce:z=!0}={}){h++,y=!1,A=!1,clearTimeout(m),ie(),p=null,d?.getTracks().forEach(ae=>ae.stop()),d=null,x=null,r(null),s.srcObject=null,s.hidden=!0,o("camera-stage").hidden=!0,o("scanner-controls").hidden=!0,o("stop")&&(o("stop").hidden=!0),o("scan")&&(o("scan").disabled=!1),o("scanner-photo").disabled=!1,o("scanner-rearm").disabled=!0,R&&(R.release().catch(()=>{}),R=null),l.rearm(),O=-1,S=[],z&&k("Camera stopped. Your scanned items are kept.")}async function Pe(z){let ae=x;if(!ae)return!1;try{return await ae.applyConstraints({advanced:[z]}),ae===x}catch{return k("This camera/browser could not apply that control. Scanning continues with its current settings."),!1}}function Fe(){let z=Z(),ae=x?.getSettings?.()||{},$=z.focusMode||[];o("scanner-focus").replaceChildren();for(let[ge,T]of[["continuous","Autofocus"],["single-shot","Focus once"],["manual","Manual focus"]])$.includes(ge)&&(ge!=="manual"||V(z.focusDistance))&&o("scanner-focus").add(new Option(T,ge));o("scanner-focus-row").hidden=!o("scanner-focus").options.length,o("scanner-focus").value=ae.focusMode||o("scanner-focus").options[0]?.value||"",o("scanner-focus-distance-row").hidden=o("scanner-focus").value!=="manual"||!V(z.focusDistance);for(let[ge,T,Se]of[["zoom",z.zoom,"zoom"],["focus-distance",z.focusDistance,"focusDistance"],["exposure",z.exposureCompensation,"exposureCompensation"]]){let Ee=o("scanner-"+ge);ge!=="focus-distance"&&(o("scanner-"+ge+"-row").hidden=!V(T)),V(T)&&(Ee.min=T.min,Ee.max=T.max,Ee.step=T.step||(T.max-T.min)/100,Ee.value=ae[Se]??T.min)}o("scanner-torch").hidden=!z.torch,o("scanner-torch").setAttribute("aria-pressed",String(!!ae.torch)),Xr(o("scanner-torch"),ae.torch?rr("Light on"):rr("Light off")),Xr(o("scanner-capabilities"),`${ae.width||s.videoWidth} \xD7 ${ae.height||s.videoHeight} \xB7 `+($.includes("continuous")?"autofocus control available":$.length?"focus controls available":"focus control not exposed; lens may be fixed-focus or managed by the camera")+` \xB7 ${p?"native + enhanced decoder":"enhanced decoder"}`)}async function $e(){let z=(await navigator.mediaDevices.enumerateDevices()).filter(ge=>ge.kind==="videoinput"),ae=x?.getSettings?.().deviceId,$=o("scanner-camera");$.replaceChildren(new Option("Rear camera (automatic)","environment"),new Option("Front camera (automatic)","user")),z.forEach((ge,T)=>$.add(new Option(ge.label||`Camera ${T+1}`,ge.deviceId))),$.value=z.some(ge=>ge.deviceId===ae)?ae:M.camera}function We(z,ae){return g||(g=new Worker("/production-scanner-worker.js",{type:"module"}),g.onmessage=({data:$})=>{if(!_||_.id!==$.id)return;let ge=_;_=null,clearTimeout(ge.timeout),$.error?ge.reject(Error($.error)):ge.resolve($.results)},g.onerror=()=>ie()),new Promise(($,ge)=>{let T=++f;_={id:T,resolve:$,reject:ge,timeout:setTimeout(()=>ie(),15e3)},g.postMessage({id:T,image:z,enhance:ae},[z.data.buffer])})}function j(z=s,ae=1920){let $=z.videoWidth||z.width,ge=z.videoHeight||z.height;if(!$||!ge)throw Error(rr("No camera frame yet"));let T=o("capture-guide")||o("camera-stage")?.querySelector(".scanner-guide"),Se=z===s&&T?$h($,ge,s.getBoundingClientRect(),T.getBoundingClientRect(),{...M,fit:getComputedStyle(s).objectFit}):null;if(z===s&&!Se)throw Error(rr("Visible aiming area unavailable"));let Ee=Se?.sw||$,Ve=Se?.sh||ge,fe=Math.min(1,ae/Math.max(Ee,Ve));return c.width=Math.max(1,Math.round(Ee*fe)),c.height=Math.max(1,Math.round(Ve*fe)),u.drawImage(z,Se?.sx||0,Se?.sy||0,Ee,Ve,0,0,c.width,c.height),u.getImageData(0,0,c.width,c.height)}async function oe(z){if(z!==h||!y)return;if(!e()){m=setTimeout(()=>void oe(z),140);return}let ae=performance.now();try{if(s.readyState>=2&&s.currentTime!==O){O=s.currentTime,I++;let $=[],ge="native",T=j();if(p)try{$=await p.detect(c)}catch{p=null}if(z!==h||(!Gn($,"native")&&!Hn($,"native").length&&(!p||I%3===0)&&($=await We(T,M.enhance),ge="zxing-wasm"),z!==h))return;let Se=Gn($,ge)?[]:Hn($,ge),Ee=[...new Set(Se.map(fe=>fe.lookupLexicalValue+"\0"+(fe.lookupSymbology||"")))];S=Ee;let Ve=l.observe(Ee,performance.now());if(Ve){let fe=Se.find(Ze=>Ze.lookupLexicalValue+"\0"+(Ze.lookupSymbology||"")===Ve);U=performance.now(),t(fe.lookupLexicalValue,{captureEnvelope:fe,originalCaptures:[{value:fe.lookupLexicalValue,symbology:fe.lookupSymbology}]}),Xr(o("scanner-last"),"Accepted: {v0}",{v0:fe.lookupLexicalValue}),k("Scanned \xB7 move item away"),o("camera-stage").classList.add("scan-accepted"),setTimeout(()=>o("camera-stage").classList.remove("scan-accepted"),500)}else Ee.length>1?k("One barcode at a time"):Ee.length===1&&performance.now()-U>2e3?k(U?"Move item away":"Hold steady"):U&&!Ee.length?k("Ready"):!U&&performance.now()-C>6e3&&k($.some(fe=>tn(fe,ge).status==="manual-required")?"Check code in Scan options":"Aim at barcode")}}catch{if(z!==h)return;if(p)k("Enhanced decoder unavailable; using the device decoder.");else{ce({announce:!1}),k("Barcode decoder unavailable. Reconnect and reopen the camera, or type the barcode.");return}}z===h&&y&&(m=setTimeout(()=>void oe(z),Math.max(70,140-(performance.now()-ae))))}async function ne(){if(!e()||y||A)return;ce({announce:!1}),A=!0;let z=h;o("scan")&&(o("scan").disabled=!0),o("stop")&&(o("stop").hidden=!1),k("Opening camera\u2026"),i?.();try{if(!window.isSecureContext||!navigator.mediaDevices?.getUserMedia)throw{name:"SecurityError"};let ae=M.camera,$=["environment","user"].includes(ae)?{facingMode:{ideal:ae}}:{deviceId:{exact:ae}},ge;try{ge=await navigator.mediaDevices.getUserMedia({audio:!1,video:{...$,width:{ideal:1920},height:{ideal:1080},frameRate:{ideal:30}}})}catch(Se){if(Se.name!=="OverconstrainedError"||z!==h)throw Se;ge=await navigator.mediaDevices.getUserMedia({audio:!1,video:$})}if(z!==h){ge.getTracks().forEach(Se=>Se.stop());return}if(d=ge,x=d.getVideoTracks()[0],r(d),x.addEventListener("ended",()=>{z===h&&(ce({announce:!1}),k("Camera disconnected. Reconnect and open the scanner again."))}),s.srcObject=d,s.hidden=!1,o("camera-stage").hidden=!1,await s.play(),z!==h)return;let T=Z();for(let Se of["focusMode","exposureMode","whiteBalanceMode"])if(T[Se]?.includes("continuous")&&await Pe({[Se]:"continuous"}),z!==h)return;if(p=null,"BarcodeDetector"in window)try{let Se=await BarcodeDetector.getSupportedFormats();_o.every(Ee=>Se.includes(Ee))&&(p=new BarcodeDetector({formats:_o}))}catch{}if(z!==h)return;try{await $e()}catch{}if(z!==h)return;G(),Fe(),o("scanner-controls").hidden=!1,o("scanner-rearm").disabled=!1,y=!0,A=!1,C=performance.now(),U=0,I=0,k("Ready \xB7 aim at barcode"),W(z),oe(z)}catch(ae){z===h&&(ce({announce:!1}),k(pc(ae)))}}o("scanner-mode").onchange=()=>{M.mode=o("scanner-mode").value,M.camera=M.mode==="bench"?"user":"environment",M.mirror=M.mode==="bench",M.rotate=!1,o("scanner-camera").value=M.camera,ee(),G(),H(),(y||A)&&(ce({announce:!1}),ne())},o("scanner-camera").onchange=()=>{M.camera=o("scanner-camera").value,H(),(y||A)&&(ce({announce:!1}),ne())};for(let z of["mirror","rotate","enhance"])o("scanner-"+z).onchange=()=>{M[z]=o("scanner-"+z).checked,G(),H()};o("scanner-torch").onclick=async()=>{await Pe({torch:!x?.getSettings?.().torch}),Fe()},o("scanner-focus").onchange=async()=>{await Pe({focusMode:o("scanner-focus").value}),Fe()};for(let[z,ae]of[["zoom","zoom"],["focus-distance","focusDistance"],["exposure","exposureCompensation"]])o("scanner-"+z).onchange=async()=>{let $={[ae]:Number(o("scanner-"+z).value)};ae==="focusDistance"&&($.focusMode="manual"),await Pe($),Fe()};return o("scanner-rearm").onclick=()=>{l.rearm(),k("Ready to count the next identical pack. Keep its barcode in view.")},o("scanner-photo").onchange=async()=>{let z=o("scanner-photo").files[0];if(o("scanner-photo").value="",!z||!e())return;ce({announce:!1});let ae=h;if(z.size>2e7)return k("Choose an image smaller than 20 MB.");o("scanner-photo").disabled=!0,k("Reading barcode photo\u2026");let $;try{if($=await createImageBitmap(z),ae!==h)return;let ge=await We(j($,2560),M.enhance);if(ae!==h)return;let T=Gn(ge,"photo-zxing-wasm")?[]:Hn(ge,"photo-zxing-wasm"),Se=[...new Set(T.map(Ve=>Ve.lookupLexicalValue+"\0"+(Ve.lookupSymbology||"")))];if(Se.length!==1)return k(Se.length?"Several barcodes found. Crop the photo to one product.":ge.length?"Decoder representation needs manual confirmation. Type the printed code.":"No retail barcode found. Use a sharp photo of the entire barcode, including its blank edges.");let Ee=T[0];t(Ee.lookupLexicalValue,{captureKind:"photo",captureEnvelope:Ee,originalCaptures:[{value:Ee.lookupLexicalValue,symbology:Ee.lookupSymbology}]}),Xr(o("scanner-last"),"Accepted from photo: {v0}",{v0:Ee.lookupLexicalValue}),k("Photo accepted \u2713")}catch{ae===h&&k("Photo could not be decoded. Try a JPEG/PNG photo or enter the barcode.")}finally{$?.close(),ae===h&&(ie(),o("scanner-photo").disabled=!1,n&&e()&&ne())}},o("scan")&&(o("scan").onclick=()=>void ne()),o("stop")&&(o("stop").onclick=()=>ce()),document.addEventListener("visibilitychange",()=>{document.hidden?ce():n&&e()&&ne()}),n&&navigator.permissions?.query&&navigator.permissions.query({name:"camera"}).then(z=>z.addEventListener("change",()=>{z.state==="granted"&&!document.hidden&&e()&&ne()})).catch(()=>{}),window.addEventListener("pagehide",()=>ce()),ee(),G(),["environment","user"].includes(M.camera)||o("scanner-camera").add(new Option("Last used camera",M.camera)),o("scanner-camera").value=M.camera,{stop:ce,start:ne,noteAccepted(){y&&(U=performance.now(),k("Ready"))}}}var Qh="offmenu-source-assertion-photo-selection/1",ep="reviewed-retained-photo-for-explicit-native-source-assertion",jn=e=>Array.isArray(e)?"["+e.map(jn).join(",")+"]":e&&typeof e=="object"?"{"+Object.keys(e).sort().map(t=>JSON.stringify(t)+":"+jn(e[t])).join(",")+"}":JSON.stringify(e),Wn=(e,t)=>jn(e)===jn(t),qr=e=>typeof e=="string"&&/^[a-f0-9]{64}$/.test(e),tp=["observationKey","sourceObservation","sourceBinding","referenceRecordId","exactObservationBridge"],bc=e=>Object.fromEntries(tp.filter(t=>Object.hasOwn(e||{},t)).map(t=>[t,e[t]]));function rp(e,t,{origin:r,runtimeSelectionSha256:i}={}){return e?.state==="qualified"&&t?.state==="qualified"&&Object.keys(e).sort().join(",")==="origin,runtimeSelectionSha256,state,useSelectionRef"&&e.useSelectionRef&&Object.keys(e.useSelectionRef).sort().join(",")==="id,sha256"&&typeof e.useSelectionRef?.id=="string"&&e.useSelectionRef.id.length>0&&qr(e.useSelectionRef.sha256)&&qr(e.runtimeSelectionSha256)&&e.origin===r&&(!i||e.runtimeSelectionSha256===i)&&Wn(e,t)}function ip(e,t){let r=t?.sourceBinding,i=t?.sourceObservation,n=t?.observationKey;if(e?.sourceId!=="off"||e.namespace!=="barcode"||e.disposition!=="source-asserted"||typeof t?.referenceRecordId!="string"||!t.referenceRecordId||!r||!i||!n||n.databaseSha256!==e.databaseSha256)return!1;for(let a of["run_id","input_id","record_ordinal","assertion_id"])if(n[a]!==e.observationKey[a]||i[a]!==e.observationKey[a])return!1;if(i.source_id!==e.sourceId||i.release_id!==e.releaseId||i.namespace!==e.namespace||i.lexical_value!==e.sourceLexicalValue||i.source_record_id!==e.sourceRecordId||i.disposition!=="source-asserted"||r.sourceId!==e.sourceId||r.releaseId!==e.releaseId||r.identifierInputId!==e.observationKey.input_id||r.identifierRecordOrdinal!==e.observationKey.record_ordinal||r.identifierSourceRecordId!==e.sourceRecordId||i.artifact_sha256!==r.identifierAssetSha256||i.native_record_id!==r.identifierNativeRecordId||r.identifierNativeRecordId!=="off:sourceOccurrence:"+r.originalSha256+":"+e.observationKey.record_ordinal)return!1;for(let a of["originalSha256","recordSha256","identifierAssetSha256","inputAssetSha256","operationReceiptSha256","rightsReceiptSha256","custodyReceiptSha256"])if(!qr(r[a]))return!1;return r.componentDigests&&Object.keys(r.componentDigests).length>0&&Object.values(r.componentDigests).every(qr)}function np(e,t){return[e?.sourcePage,e?.photoLicensePage,e?.licenseUrl,e?.attributionDetails?.productUrl].every(i=>{try{let n=new URL(i);return n.protocol!=="https:"||n.username||n.password||n.port||n.hash||n.href!==i?!1:n.hostname==="creativecommons.org"?/^\/licenses\/by-sa\/3\.0(?:\/deed\.en)?\/?$/.test(n.pathname)&&!n.search:n.hostname!=="world.openfoodfacts.org"?!1:n.pathname==="/cgi/product_image.pl"?n.searchParams.get("code")===t&&n.searchParams.get("id")==="front_en"&&[...n.searchParams.keys()].length===2:(n.pathname==="/product/"+t||n.pathname.startsWith("/product/"+t+"/"))&&!n.search}catch{return!1}})}function xc(e,t,{origin:r}={}){let i=d=>({state:"unavailable",reasonCode:d,candidate:null});if(e?.schema!==Qh)return i("RETAINED_PHOTO_SELECTION_MISSING");let n=e.reference;if(!Qi(n,n?.originalLexicalValue)||!ip(n,e.detail))return i("RETAINED_PHOTO_NATIVE_REFERENCE_MISSING");if(!rp(e.currentOutputUse,t?.currentOutputUse,{origin:r})||!Wn(e.useSelectionRef,e.currentOutputUse.useSelectionRef))return i("RETAINED_PHOTO_CURRENT_OUTPUT_USE_UNQUALIFIED");let a=e.qualification;if(a?.state!=="qualified"||a.scope!==ep||!qr(a.adoptionReceiptSha256)||!qr(a.bindingReviewRef?.sha256))return i("RETAINED_PHOTO_ADOPTION_UNAVAILABLE");let o=(Array.isArray(t?.sourceAssertions)?t.sourceAssertions:[]).filter(d=>d&&typeof d=="object"&&Wn(d.sourceObservationReference,n)&&Wn(bc(d.binding),bc(e.detail)));if(o.length!==1)return i("RETAINED_PHOTO_EXPLICIT_ASSERTION_MISMATCH");let s=e.detail?.sourceBinding,c=e.imageObservation,u=e.localAsset;if(!s||c?.sourceCode!==n.sourceLexicalValue||c.role!=="front"||!/^front_[a-z]{2}$/.test(c.selectedKey||"")||!/^[1-9][0-9]*$/.test(c.revision||"")||!/^[0-9]+$/.test(c.imageId||"")||!/^[1-9][0-9]*$/.test(c.resolution||"")||!Number.isInteger(c.image?.bytes)||c.image.bytes<1||c.image.type!=="image/jpeg"||c.sourceLocator?.sourceId!==n.sourceId||c.sourceLocator?.releaseId!==n.releaseId||c.sourceLocator?.originalSha256!==s.originalSha256||c.sourceLocator?.ordinal!==n.observationKey.record_ordinal||!qr(u?.sha256)||c.image?.sha256!==u.sha256||u.type!=="image/jpeg"||typeof u.path!="string"||!/^\/api\/off-photos\/[A-Za-z0-9_-]+\.jpg$/.test(u.path))return i("RETAINED_PHOTO_IMAGE_ASSET_BINDING");let l=e.rights;return l?.displayPermitted!==!0||!l.license||!l.attribution||!l.evidenceReference||!np(l,n.sourceLexicalValue)?i("RETAINED_PHOTO_RIGHTS_UNQUALIFIED"):{state:"qualified",reasonCode:null,assertion:o[0],candidate:{sourceObservationReference:n,productRecordId:e.detail.referenceRecordId,qualification:a,role:"front",selectionRole:"selected-front",localAssetPath:u.path,offlineAvailable:!1,provenance:{sourceId:n.sourceId,releaseId:n.releaseId,imageId:c.imageId,revision:c.revision,sourceCode:n.sourceLexicalValue,associationScope:"explicit-independent-native-source-assertion",relationship:"Current retrieval selected by retained metadata; historical image bytes and primary-product variant match unverified",metadataRelease:n.releaseId,retrievedAt:c.retrievedAt,imageSha256:u.sha256},rights:l}}}var ap=Object.freeze({"Offline resource unavailable":"\u0627\u0644\u0645\u0648\u0631\u062F \u063A\u064A\u0631 \u0645\u062A\u0627\u062D \u062F\u0648\u0646 \u0627\u062A\u0635\u0627\u0644","Translation is stale; showing the original source text.":"\u0627\u0644\u062A\u0631\u062C\u0645\u0629 \u0642\u062F\u064A\u0645\u0629\u061B \u064A\u064F\u0639\u0631\u0636 \u0646\u0635 \u0627\u0644\u0645\u0635\u062F\u0631 \u0627\u0644\u0623\u0635\u0644\u064A.","Common corpus graph loaded for local preview. Source identities, citations and quantities are preserved; nothing is saved.":"\u062A\u0645 \u062A\u062D\u0645\u064A\u0644 \u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0645\u062C\u0645\u0648\u0639\u0629 \u0644\u0644\u0645\u0639\u0627\u064A\u0646\u0629 \u0627\u0644\u0645\u062D\u0644\u064A\u0629. \u062A\u0628\u0642\u0649 \u0647\u0648\u064A\u0627\u062A \u0627\u0644\u0645\u0635\u0627\u062F\u0631 \u0648\u0627\u0644\u0627\u0633\u062A\u0634\u0647\u0627\u062F\u0627\u062A \u0648\u0627\u0644\u0643\u0645\u064A\u0627\u062A \u0643\u0645\u0627 \u0647\u064A\u061B \u0644\u0645 \u062A\u064F\u062D\u0641\u0638 \u0623\u064A \u062A\u063A\u064A\u064A\u0631\u0627\u062A.","Return to offmenu":"\u0627\u0644\u0639\u0648\u062F\u0629 \u0625\u0644\u0649 offmenu","Returning to offmenu\u2026":"\u062C\u0627\u0631\u064D \u0627\u0644\u0639\u0648\u062F\u0629 \u0625\u0644\u0649 offmenu\u2026","Open offmenu":"\u0627\u0641\u062A\u062D offmenu",Yes:"\u0646\u0639\u0645",No:"\u0644\u0627","Unknown unit":"\u0648\u062D\u062F\u0629 \u063A\u064A\u0631 \u0645\u0639\u0631\u0648\u0641\u0629","Kitchen inventory":"\u0645\u062E\u0632\u0648\u0646 \u0627\u0644\u0645\u0637\u0628\u062E","Home checkout receipt":"\u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636 \u0627\u0644\u0645\u0646\u0632\u0644","Household menus & recipe booklet":"\u0648\u062C\u0628\u0627\u062A \u0627\u0644\u0623\u0633\u0631\u0629 \u0648\u0643\u062A\u064A\u0651\u0628 \u0627\u0644\u0648\u0635\u0641\u0627\u062A","Meal-plan shopping list":"\u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u062A\u0633\u0648\u0651\u0642 \u0644\u062E\u0637\u0629 \u0627\u0644\u0648\u062C\u0628\u0627\u062A","Household preferences":"\u062A\u0641\u0636\u064A\u0644\u0627\u062A \u0627\u0644\u0623\u0633\u0631\u0629","Food history & nutrition":"\u0633\u062C\u0644 \u0627\u0644\u0637\u0639\u0627\u0645 \u0648\u0627\u0644\u062A\u063A\u0630\u064A\u0629","Waste & freshness report":"\u062A\u0642\u0631\u064A\u0631 \u0627\u0644\u0647\u062F\u0631 \u0648\u062D\u0627\u0644\u0629 \u0627\u0644\u0637\u0639\u0627\u0645",Product:"\u0627\u0644\u0645\u0646\u062A\u062C",Amount:"\u0627\u0644\u0643\u0645\u064A\u0629","Recipe ingredient":"\u0645\u0643\u0648\u0651\u0646 \u0627\u0644\u0648\u0635\u0641\u0629",Expiry:"\u062A\u0627\u0631\u064A\u062E \u0627\u0644\u0627\u0646\u062A\u0647\u0627\u0621",Directions:"\u0627\u0644\u0637\u0631\u064A\u0642\u0629",Contents:"\u0627\u0644\u0645\u062D\u062A\u0648\u064A\u0627\u062A","Recipes indexed: {count}":{zero:"\u0644\u0627 \u0648\u0635\u0641\u0627\u062A \u0645\u0641\u0647\u0631\u0633\u0629 ({count})",one:"\u0648\u0635\u0641\u0629 \u0648\u0627\u062D\u062F\u0629 \u0645\u0641\u0647\u0631\u0633\u0629 ({count})",two:"\u0648\u0635\u0641\u062A\u0627\u0646 \u0645\u0641\u0647\u0631\u0633\u062A\u0627\u0646 ({count})",few:"{count} \u0648\u0635\u0641\u0627\u062A \u0645\u0641\u0647\u0631\u0633\u0629",many:"{count} \u0648\u0635\u0641\u0629 \u0645\u0641\u0647\u0631\u0633\u0629",other:"\u0648\u0635\u0641\u0627\u062A \u0645\u0641\u0647\u0631\u0633\u0629: {count}"},"Translation unavailable; showing the original source text.":"\u0627\u0644\u062A\u0631\u062C\u0645\u0629 \u063A\u064A\u0631 \u0645\u062A\u0627\u062D\u0629\u061B \u064A\u064F\u0639\u0631\u0636 \u0646\u0635 \u0627\u0644\u0645\u0635\u062F\u0631 \u0627\u0644\u0623\u0635\u0644\u064A.","Same as interface language":"\u0645\u062B\u0644 \u0644\u063A\u0629 \u0627\u0644\u0648\u0627\u062C\u0647\u0629","Arabic when supplied":"\u0627\u0644\u0639\u0631\u0628\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627","Japanese when supplied":"\u0627\u0644\u064A\u0627\u0628\u0627\u0646\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627","English when supplied":"\u0627\u0644\u0625\u0646\u062C\u0644\u064A\u0632\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627","French when supplied":"\u0627\u0644\u0641\u0631\u0646\u0633\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627","German when supplied":"\u0627\u0644\u0623\u0644\u0645\u0627\u0646\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627","Chinese when supplied":"\u0627\u0644\u0635\u064A\u0646\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627","Hindi when supplied":"\u0627\u0644\u0647\u0646\u062F\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627","Indonesian when supplied":"\u0627\u0644\u0625\u0646\u062F\u0648\u0646\u064A\u0633\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627","Russian when supplied":"\u0627\u0644\u0631\u0648\u0633\u064A\u0629 \u0639\u0646\u062F \u062A\u0648\u0641\u0631\u0647\u0627","Original source language":"\u0644\u063A\u0629 \u0627\u0644\u0645\u0635\u062F\u0631 \u0627\u0644\u0623\u0635\u0644\u064A\u0629","Food-name display language":"\u0644\u063A\u0629 \u0639\u0631\u0636 \u0623\u0633\u0645\u0627\u0621 \u0627\u0644\u0623\u0637\u0639\u0645\u0629","All languages":"\u062C\u0645\u064A\u0639 \u0627\u0644\u0644\u063A\u0627\u062A","Recipe language":"\u0644\u063A\u0629 \u0627\u0644\u0648\u0635\u0641\u0629","RECIPES FROM AROUND THE WORLD":"\u0648\u0635\u0641\u0627\u062A \u0645\u0646 \u0623\u0646\u062D\u0627\u0621 \u0627\u0644\u0639\u0627\u0644\u0645","Explore the shared recipe library.":"\u0627\u0633\u062A\u0643\u0634\u0641 \u0645\u0643\u062A\u0628\u0629 \u0627\u0644\u0648\u0635\u0641\u0627\u062A \u0627\u0644\u0645\u0634\u062A\u0631\u0643\u0629.","Open worldwide recipes":"\u0627\u0641\u062A\u062D \u0648\u0635\u0641\u0627\u062A \u0627\u0644\u0639\u0627\u0644\u0645","Dish or ingredients":"\u0627\u0644\u0637\u0628\u0642 \u0623\u0648 \u0627\u0644\u0645\u0643\u0648\u0651\u0646\u0627\u062A","Original source":"\u0627\u0644\u0645\u0635\u062F\u0631 \u0627\u0644\u0623\u0635\u0644\u064A","Prioritise recipes using my available ingredients":"\u0623\u0639\u0637\u0650 \u0627\u0644\u0623\u0648\u0644\u0648\u064A\u0629 \u0644\u0644\u0648\u0635\u0641\u0627\u062A \u0627\u0644\u062A\u064A \u062A\u0633\u062A\u062E\u062F\u0645 \u0645\u0643\u0648\u0651\u0646\u0627\u062A\u064A \u0627\u0644\u0645\u062A\u0627\u062D\u0629","Shared recipes are available to everyone. Your pantry matching runs on this device.":"\u0627\u0644\u0648\u0635\u0641\u0627\u062A \u0627\u0644\u0645\u0634\u062A\u0631\u0643\u0629 \u0645\u062A\u0627\u062D\u0629 \u0644\u0644\u062C\u0645\u064A\u0639. \u062A\u064F\u0637\u0627\u0628\u064E\u0642 \u0645\u0639 \u0645\u062E\u0632\u0648\u0646\u0643 \u0639\u0644\u0649 \u0647\u0630\u0627 \u0627\u0644\u062C\u0647\u0627\u0632.","A little room for possibility.":"\u0645\u0633\u0627\u062D\u0629 \u0635\u063A\u064A\u0631\u0629 \u0644\u0623\u0641\u0643\u0627\u0631 \u062C\u062F\u064A\u062F\u0629.","Choose a shelf and scan your first items through checkout.":"\u0627\u062E\u062A\u0631 \u0631\u0641\u064B\u0627 \u0648\u0627\u0645\u0633\u062D \u0623\u0635\u0646\u0627\u0641\u0643 \u0627\u0644\u0623\u0648\u0644\u0649 \u0644\u0625\u0636\u0627\u0641\u062A\u0647\u0627 \u0625\u0644\u0649 \u0627\u0644\u0642\u0627\u0626\u0645\u0629.","offmenu \xB7 A little checkout. A better stocked home.":"offmenu \xB7 \u0642\u0627\u0626\u0645\u0629 \u0628\u0633\u064A\u0637\u0629. \u0648\u0645\u062E\u0632\u0648\u0646 \u0645\u0646\u0632\u0644\u064A \u0623\u0641\u0636\u0644.","Pantry, fridge or freezer. One satisfying":"\u062E\u0632\u0627\u0646\u0629 \u0627\u0644\u0637\u0639\u0627\u0645 \u0623\u0648 \u0627\u0644\u062B\u0644\u0627\u062C\u0629 \u0623\u0648 \u0627\u0644\u0645\u062C\u0645\u0651\u062F. \u062A\u0646\u0628\u064A\u0647",beep:"\u0644\u0637\u064A\u0641","at a time.":"\u0645\u0639 \u0643\u0644 \u0635\u0646\u0641.","THE HOME CHECKOUT CLUB":"\u0646\u0627\u062F\u064A \u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636 \u0627\u0644\u0645\u0646\u0632\u0644","EST. RIGHT NOW":"\u0627\u0628\u062F\u0623 \u0627\u0644\u0622\u0646","Oh, so that\u2019s what\u2019s":"\u0625\u0630\u064B\u0627 \u0647\u0630\u0627 \u0645\u0627 \u0643\u0627\u0646","at the back of the shelf.":"\u0641\u064A \u0622\u062E\u0631 \u0627\u0644\u0631\u0641.","HELLO, KITCHEN.":"\u0645\u0631\u062D\u0628\u064B\u0627 \u064A\u0627 \u0645\u0637\u0628\u062E.","3 items \xB7 endless possibilities":"\u0663 \u0623\u0635\u0646\u0627\u0641 \xB7 \u0623\u0641\u0643\u0627\u0631 \u0644\u0627 \u062D\u0635\u0631 \u0644\u0647\u0627","THE GOOD":"\u0627\u0644\u0637\u0639\u0627\u0645",STUFF:"\u0627\u0644\u062C\u064A\u0651\u062F","YOUR KITCHEN":"\u0645\u0637\u0628\u062E\u0643","A little inspiration":"\u0642\u0644\u064A\u0644 \u0645\u0646 \u0627\u0644\u0625\u0644\u0647\u0627\u0645","ALREADY YOURS \u2713":"\u0644\u062F\u064A\u0643 \u0628\u0627\u0644\u0641\u0639\u0644 \u2713","\u25CE See what\u2019s hiding":"\u25CE \u0627\u0643\u062A\u0634\u0641 \u0645\u0627 \u0644\u062F\u064A\u0643","\u25A5 Make space for good food":"\u25A5 \u062E\u0635\u0651\u0635 \u0645\u0633\u0627\u062D\u0629 \u0644\u0644\u0637\u0639\u0627\u0645 \u0627\u0644\u062C\u064A\u0651\u062F","\u2733 Find your next meal":"\u2733 \u0627\u062E\u062A\u0631 \u0648\u062C\u0628\u062A\u0643 \u0627\u0644\u062A\u0627\u0644\u064A\u0629","A little more play. A little less \u201Cwhat\u2019s for dinner?\u201D":"\u0645\u062A\u0639\u0629 \u0623\u0643\u062B\u0631 \u0648\u062D\u064A\u0631\u0629 \u0623\u0642\u0644 \u0628\u0634\u0623\u0646 \u0627\u0644\u0639\u0634\u0627\u0621.","Illustration of the offmenu home checkout":"\u0631\u0633\u0645 \u062A\u0648\u0636\u064A\u062D\u064A \u0644\u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636 \u0627\u0644\u0645\u0646\u0632\u0644 \u0641\u064A offmenu","Turn shelf-by-shelf inventory into a little checkout ritual. Scan your pantry, fridge and freezer, then discover what to cook.":"\u062D\u0648\u0651\u0644 \u062C\u0631\u062F \u0627\u0644\u0631\u0641\u0648\u0641 \u0625\u0644\u0649 \u0639\u0627\u062F\u0629 \u0628\u0633\u064A\u0637\u0629. \u0627\u0645\u0633\u062D \u062E\u0632\u0627\u0646\u0629 \u0627\u0644\u0637\u0639\u0627\u0645 \u0648\u0627\u0644\u062B\u0644\u0627\u062C\u0629 \u0648\u0627\u0644\u0645\u062C\u0645\u0651\u062F\u060C \u062B\u0645 \u0627\u0643\u062A\u0634\u0641 \u0645\u0627 \u064A\u0645\u0643\u0646\u0643 \u0637\u0647\u064A\u0647.","Interface language":"\u0644\u063A\u0629 \u0627\u0644\u0648\u0627\u062C\u0647\u0629","Interface language is saved on this device. Recipes and food names keep their source language.":"\u062A\u064F\u062D\u0641\u0638 \u0644\u063A\u0629 \u0627\u0644\u0648\u0627\u062C\u0647\u0629 \u0639\u0644\u0649 \u0647\u0630\u0627 \u0627\u0644\u062C\u0647\u0627\u0632. \u062A\u062D\u062A\u0641\u0638 \u0627\u0644\u0648\u0635\u0641\u0627\u062A \u0648\u0623\u0633\u0645\u0627\u0621 \u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0628\u0644\u063A\u062A\u0647\u0627 \u0627\u0644\u0623\u0635\u0644\u064A\u0629.","Skip to kitchen":"\u0627\u0646\u062A\u0642\u0644 \u0625\u0644\u0649 \u0627\u0644\u0645\u0637\u0628\u062E","Global data":"\u0627\u0644\u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0639\u0627\u0644\u0645\u064A\u0629","How it works":"\u0643\u064A\u0641 \u064A\u0639\u0645\u0644","Log in":"\u062A\u0633\u062C\u064A\u0644 \u0627\u0644\u062F\u062E\u0648\u0644","My kitchen \u2197":"\u0645\u0637\u0628\u062E\u064A \u2197","YOUR KITCHEN. YOUR CHECKOUT.":"\u0645\u0637\u0628\u062E\u0643. \u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636\u0643.","Dinner starts":"\u064A\u0628\u062F\u0623 \u0627\u0644\u0639\u0634\u0627\u0621","with what you":"\u0628\u0645\u0627 \u0644\u062F\u064A\u0643","already have.":"\u0628\u0627\u0644\u0641\u0639\u0644.","Scan a few foods, find meals that fit your household, and buy only what\u2019s missing. Start with five foods or one shelf.":"\u0627\u0645\u0633\u062D \u0628\u0639\u0636 \u0627\u0644\u0623\u0637\u0639\u0645\u0629\u060C \u0648\u0627\u0639\u062B\u0631 \u0639\u0644\u0649 \u0648\u062C\u0628\u0627\u062A \u062A\u0646\u0627\u0633\u0628 \u0623\u0633\u0631\u062A\u0643\u060C \u0648\u0627\u0634\u062A\u0631\u0650 \u0645\u0627 \u064A\u0646\u0642\u0635\u0643 \u0641\u0642\u0637. \u0627\u0628\u062F\u0623 \u0628\u062E\u0645\u0633\u0629 \u0623\u0635\u0646\u0627\u0641 \u0623\u0648 \u0631\u0641 \u0648\u0627\u062D\u062F.","Add my first food":"\u0623\u0636\u0641 \u0623\u0648\u0644 \u0637\u0639\u0627\u0645","Try a kitchen":"\u062C\u0631\u0651\u0628 \u0645\u0637\u0628\u062E\u064B\u0627","A SMALL RITUAL. A FRESH START.":"\u0639\u0627\u062F\u0629 \u0628\u0633\u064A\u0637\u0629. \u0628\u062F\u0627\u064A\u0629 \u062C\u062F\u064A\u062F\u0629.","Give your kitchen":"\u0627\u0645\u0646\u062D \u0645\u0637\u0628\u062E\u0643","a little shelf respect.":"\u0628\u0639\u0636 \u0627\u0644\u0639\u0646\u0627\u064A\u0629 \u0628\u0631\u0641\u0648\u0641\u0647.","No whole-house marathon required.":"\u0644\u0627 \u062A\u062D\u062A\u0627\u062C \u0625\u0644\u0649 \u062A\u0631\u062A\u064A\u0628 \u0627\u0644\u0645\u0646\u0632\u0644 \u0643\u0644\u0647.","Just one shelf and a clear bit of bench.":"\u064A\u0643\u0641\u064A \u0631\u0641 \u0648\u0627\u062D\u062F \u0648\u0645\u0633\u0627\u062D\u0629 \u062E\u0627\u0644\u064A\u0629 \u0639\u0644\u0649 \u0627\u0644\u0637\u0627\u0648\u0644\u0629.","Clear a shelf.":"\u0623\u0641\u0631\u063A \u0631\u0641\u064B\u0627.","Pick your pantry, fridge or freezer. Put its contents on the bench so you can see what\u2019s there.":"\u0627\u062E\u062A\u0631 \u062E\u0632\u0627\u0646\u0629 \u0627\u0644\u0637\u0639\u0627\u0645 \u0623\u0648 \u0627\u0644\u062B\u0644\u0627\u062C\u0629 \u0623\u0648 \u0627\u0644\u0645\u062C\u0645\u0651\u062F. \u0636\u0639 \u0645\u062D\u062A\u0648\u064A\u0627\u062A\u0647 \u0639\u0644\u0649 \u0627\u0644\u0637\u0627\u0648\u0644\u0629 \u0644\u062A\u0631\u0649 \u0645\u0627 \u0644\u062F\u064A\u0643.","Play shopkeeper.":"\u0627\u0645\u0633\u062D \u0623\u063A\u0631\u0627\u0636\u0643.","Scan each item straight onto your receipt. Glance at nutrition and enjoy the beep. Review it all at the end.":"\u0627\u0645\u0633\u062D \u0643\u0644 \u0635\u0646\u0641 \u0644\u0625\u0636\u0627\u0641\u062A\u0647 \u0625\u0644\u0649 \u0642\u0627\u0626\u0645\u062A\u0643. \u0627\u0637\u0651\u0644\u0639 \u0639\u0644\u0649 \u0628\u064A\u0627\u0646\u0627\u062A\u0647 \u0627\u0644\u063A\u0630\u0627\u0626\u064A\u0629 \u062B\u0645 \u0631\u0627\u062C\u0639 \u0627\u0644\u0642\u0627\u0626\u0645\u0629 \u0641\u064A \u0627\u0644\u0646\u0647\u0627\u064A\u0629.","Put the good stuff back.":"\u0623\u0639\u062F \u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0625\u0644\u0649 \u0645\u0643\u0627\u0646\u0647\u0627.","Review your receipt, update that shelf, then find a meal that starts with what you have.":"\u0631\u0627\u062C\u0639 \u0642\u0627\u0626\u0645\u062A\u0643 \u0648\u062D\u062F\u0651\u062B \u0627\u0644\u0631\u0641\u060C \u062B\u0645 \u0627\u062E\u062A\u0631 \u0648\u062C\u0628\u0629 \u0645\u0646 \u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0627\u0644\u0645\u0648\u062C\u0648\u062F\u0629 \u0644\u062F\u064A\u0643.","FRESH FROM THE SHOP":"\u0645\u0646 \u0627\u0644\u0645\u062A\u062C\u0631 \u0625\u0644\u0649 \u0645\u0637\u0628\u062E\u0643","Shopping bags in.":"\u0623\u062D\u0636\u0631\u062A \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A.","Kitchen sorted.":"\u0648\u0627\u0644\u0622\u0646 \u0631\u062A\u0651\u0628 \u0627\u0644\u0645\u0637\u0628\u062E.","Give new groceries the same checkout treatment before putting them away. Add to your shelves as you unpack.":"\u0627\u0645\u0633\u062D \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A \u0627\u0644\u062C\u062F\u064A\u062F\u0629 \u0642\u0628\u0644 \u062A\u062E\u0632\u064A\u0646\u0647\u0627\u060C \u0648\u0623\u0636\u0641\u0647\u0627 \u0625\u0644\u0649 \u0631\u0641\u0648\u0641\u0643 \u0623\u062B\u0646\u0627\u0621 \u062A\u0641\u0631\u064A\u063A \u0627\u0644\u0623\u0643\u064A\u0627\u0633.","Try an unpacking run \u2197":"\u062C\u0631\u0651\u0628 \u0625\u0636\u0627\u0641\u0629 \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A \u2197","Product information from Open Food Facts. Always check the package for allergens.":"\u0645\u0639\u0644\u0648\u0645\u0627\u062A \u0627\u0644\u0645\u0646\u062A\u062C\u0627\u062A \u0645\u0646 Open Food Facts. \u062A\u062D\u0642\u0651\u0642 \u062F\u0627\u0626\u0645\u064B\u0627 \u0645\u0646 \u0627\u0644\u0639\u0628\u0648\u0629 \u0644\u0645\u0639\u0631\u0641\u0629 \u0645\u0633\u0628\u0651\u0628\u0627\u062A \u0627\u0644\u062D\u0633\u0627\u0633\u064A\u0629.","YOUR HOME CHECKOUT":"\u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636 \u0645\u0637\u0628\u062E\u0643","Let\u2019s take stock.":"\u0644\u0646\u0631\u0627\u062C\u0639 \u0645\u0627 \u0644\u062F\u064A\u0646\u0627.","DEMO \xB7 SAMPLE PRODUCTS":"\u062A\u062C\u0631\u0628\u0629 \xB7 \u0645\u0646\u062A\u062C\u0627\u062A \u0646\u0645\u0648\u0630\u062C\u064A\u0629","\u266A Sound off":"\u266A \u0627\u0644\u0635\u0648\u062A \u0645\u062A\u0648\u0642\u0641","\u266A Sound on":"\u266A \u0627\u0644\u0635\u0648\u062A \u0645\u0641\u0639\u0651\u0644","Scan feedback \u2733":"\u062A\u0646\u0628\u064A\u0647\u0627\u062A \u0627\u0644\u0645\u0633\u062D \u2733","Profile & backup":"\u0627\u0644\u0645\u0644\u0641 \u0627\u0644\u0634\u062E\u0635\u064A \u0648\u0627\u0644\u0646\u0633\u062E \u0627\u0644\u0627\u062D\u062A\u064A\u0627\u0637\u064A","Exit demo":"\u0625\u0646\u0647\u0627\u0621 \u0627\u0644\u062A\u062C\u0631\u0628\u0629","\u2733 Today":"\u2733 \u0627\u0644\u064A\u0648\u0645","\u25A4 Kitchen":"\u25A4 \u0627\u0644\u0645\u0637\u0628\u062E","\u25A6 Plan":"\u25A6 \u0627\u0644\u062E\u0637\u0629","\u25C7 Shop":"\u25C7 \u0627\u0644\u062A\u0633\u0648\u0651\u0642","\u2667 Me":"\u2667 \u062D\u0633\u0627\u0628\u064A","\u25A5 Scan groceries":"\u25A5 \u0627\u0645\u0633\u062D \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A","+ Add food":"+ \u0623\u0636\u0641 \u0637\u0639\u0627\u0645\u064B\u0627","Saved on this device":"\u0645\u062D\u0641\u0648\u0638 \u0639\u0644\u0649 \u0647\u0630\u0627 \u0627\u0644\u062C\u0647\u0627\u0632","YOUR KITCHEN, YOUR WAY":"\u0645\u0637\u0628\u062E\u0643 \u0643\u0645\u0627 \u062A\u062D\u0628","People, preferences & progress.":"\u0627\u0644\u0623\u0634\u062E\u0627\u0635 \u0648\u0627\u0644\u062A\u0641\u0636\u064A\u0644\u0627\u062A \u0648\u0627\u0644\u062A\u0642\u062F\u0651\u0645.","\u2667 Dietary profiles":"\u2667 \u0627\u0644\u0645\u0644\u0641\u0627\u062A \u0627\u0644\u063A\u0630\u0627\u0626\u064A\u0629","\u25F7 Statistics & history":"\u25F7 \u0627\u0644\u0625\u062D\u0635\u0627\u0621\u0627\u062A \u0648\u0627\u0644\u0633\u062C\u0644","\u25A4 Printable documents & Kindle":"\u25A4 \u0645\u0633\u062A\u0646\u062F\u0627\u062A \u0644\u0644\u0637\u0628\u0627\u0639\u0629 \u0648Kindle","Account & backup":"\u0627\u0644\u062D\u0633\u0627\u0628 \u0648\u0627\u0644\u0646\u0633\u062E \u0627\u0644\u0627\u062D\u062A\u064A\u0627\u0637\u064A","Connections & developers":"\u0627\u0644\u0627\u062A\u0635\u0627\u0644\u0627\u062A \u0648\u0627\u0644\u0645\u0637\u0648\u0651\u0631\u0648\u0646","Large text":"\u0646\u0635 \u0643\u0628\u064A\u0631","Quiet mode \xB7 disable scan effects":"\u0627\u0644\u0648\u0636\u0639 \u0627\u0644\u0647\u0627\u062F\u0626 \xB7 \u062A\u0639\u0637\u064A\u0644 \u0645\u0624\u062B\u0631\u0627\u062A \u0627\u0644\u0645\u0633\u062D","People sharing this kitchen":"\u0627\u0644\u0623\u0634\u062E\u0627\u0635 \u0627\u0644\u0645\u0634\u0627\u0631\u0643\u0648\u0646 \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u0637\u0628\u062E","Trust, privacy & support":"\u0627\u0644\u062B\u0642\u0629 \u0648\u0627\u0644\u062E\u0635\u0648\u0635\u064A\u0629 \u0648\u0627\u0644\u062F\u0639\u0645","Clear this device\u2019s account data":"\u0627\u0645\u0633\u062D \u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u062D\u0633\u0627\u0628 \u0645\u0646 \u0647\u0630\u0627 \u0627\u0644\u062C\u0647\u0627\u0632","PICK YOUR NEXT LITTLE WIN":"\u0627\u062E\u062A\u0631 \u062E\u0637\u0648\u062A\u0643 \u0627\u0644\u062A\u0627\u0644\u064A\u0629","What\u2019s on the bench?":"\u0645\u0627\u0630\u0627 \u0639\u0644\u0649 \u0627\u0644\u0637\u0627\u0648\u0644\u0629\u061F","\u25A4 Rebuild a shelf":"\u25A4 \u0631\u062A\u0651\u0628 \u0631\u0641\u064B\u0627","\u2672 Garbage scan":"\u2672 \u0627\u0645\u0633\u062D \u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0644\u0644\u062A\u062E\u0644\u0651\u0635 \u0645\u0646\u0647\u0627","\u{1F6CD} Unpack shopping":"\u{1F6CD} \u0623\u0636\u0641 \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A",Pantry:"\u062E\u0632\u0627\u0646\u0629 \u0627\u0644\u0637\u0639\u0627\u0645",Fridge:"\u0627\u0644\u062B\u0644\u0627\u062C\u0629",Freezer:"\u0627\u0644\u0645\u062C\u0645\u0651\u062F","Dry goods & everyday staples":"\u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0627\u0644\u062C\u0627\u0641\u0629 \u0648\u0627\u0644\u0645\u0648\u0627\u062F \u0627\u0644\u0623\u0633\u0627\u0633\u064A\u0629","Fresh things & leftovers":"\u0627\u0644\u0623\u0637\u0639\u0645\u0629 \u0627\u0644\u0637\u0627\u0632\u062C\u0629 \u0648\u0628\u0642\u0627\u064A\u0627 \u0627\u0644\u0648\u062C\u0628\u0627\u062A","Future-you\u2019s favourite food":"\u0623\u0637\u0639\u0645\u0629 \u0645\u062D\u0641\u0648\u0638\u0629 \u0644\u0644\u0623\u064A\u0627\u0645 \u0627\u0644\u0642\u0627\u062F\u0645\u0629","Storage area":"\u0645\u0643\u0627\u0646 \u0627\u0644\u062A\u062E\u0632\u064A\u0646","Shelf / container":"\u0627\u0644\u0631\u0641 \u0623\u0648 \u0627\u0644\u062D\u0627\u0648\u064A\u0629","e.g. Bench":"\u0645\u062B\u0644: \u0627\u0644\u0637\u0627\u0648\u0644\u0629","e.g. Top shelf":"\u0645\u062B\u0644: \u0627\u0644\u0631\u0641 \u0627\u0644\u0639\u0644\u0648\u064A","Clear this shelf onto your bench. Its current inventory stays intact until you review and finish.":"\u0623\u0641\u0631\u063A \u0645\u062D\u062A\u0648\u064A\u0627\u062A \u0647\u0630\u0627 \u0627\u0644\u0631\u0641 \u0639\u0644\u0649 \u0627\u0644\u0637\u0627\u0648\u0644\u0629. \u0644\u0646 \u064A\u062A\u063A\u064A\u0651\u0631 \u0645\u062E\u0632\u0648\u0646\u0647 \u062D\u062A\u0649 \u062A\u0631\u0627\u062C\u0639 \u0627\u0644\u0642\u0627\u0626\u0645\u0629 \u0648\u062A\u0646\u0647\u064A \u0627\u0644\u0639\u0645\u0644\u064A\u0629.","Choose the source location. Scan items you are discarding; review the removal receipt before the inventory changes.":"\u0627\u062E\u062A\u0631 \u0645\u0643\u0627\u0646 \u0627\u0644\u062A\u062E\u0632\u064A\u0646. \u0627\u0645\u0633\u062D \u0627\u0644\u0623\u0635\u0646\u0627\u0641 \u0627\u0644\u062A\u064A \u0633\u062A\u062A\u062E\u0644\u0651\u0635 \u0645\u0646\u0647\u0627\u060C \u0648\u0631\u0627\u062C\u0639 \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0625\u0632\u0627\u0644\u0629 \u0642\u0628\u0644 \u062A\u063A\u064A\u064A\u0631 \u0627\u0644\u0645\u062E\u0632\u0648\u0646.","Choose where these groceries will go. Scan one destination at a time, then add them to the items already there.":"\u0627\u062E\u062A\u0631 \u0645\u0643\u0627\u0646 \u0647\u0630\u0647 \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A. \u0627\u0645\u0633\u062D \u0627\u0644\u0623\u0635\u0646\u0627\u0641 \u0644\u0643\u0644 \u0645\u0643\u0627\u0646 \u0639\u0644\u0649 \u062D\u062F\u0629\u060C \u062B\u0645 \u0623\u0636\u0641\u0647\u0627 \u0625\u0644\u0649 \u0627\u0644\u0645\u0648\u062C\u0648\u062F \u0641\u064A\u0647.","Open my checkout \u2197":"\u0627\u0628\u062F\u0623 \u0642\u0627\u0626\u0645\u0629 \u0623\u063A\u0631\u0627\u0636\u064A \u2197","SHELF RESET":"\u0625\u0639\u0627\u062F\u0629 \u062A\u0631\u062A\u064A\u0628 \u0627\u0644\u0631\u0641","GARBAGE \xB7 SOURCE LOCATION":"\u0627\u0644\u062A\u062E\u0644\u0651\u0635 \u0645\u0646 \u0627\u0644\u0637\u0639\u0627\u0645 \xB7 \u0645\u0643\u0627\u0646 \u0627\u0644\u062A\u062E\u0632\u064A\u0646","GROCERY UNPACKING":"\u0625\u0636\u0627\u0641\u0629 \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A","Scan, check, then put it back.":"\u0627\u0645\u0633\u062D \u0648\u062A\u062D\u0642\u0651\u0642 \u062B\u0645 \u0623\u0639\u062F\u0647 \u0625\u0644\u0649 \u0645\u0643\u0627\u0646\u0647.","Pause & choose another shelf":"\u062A\u0648\u0642\u0651\u0641 \u0648\u0627\u062E\u062A\u0631 \u0631\u0641\u064B\u0627 \u0622\u062E\u0631","CHECKOUT OPEN":"\u0627\u0644\u0642\u0627\u0626\u0645\u0629 \u0645\u0641\u062A\u0648\u062D\u0629","Next item, please.":"\u0627\u0644\u0635\u0646\u0641 \u0627\u0644\u062A\u0627\u0644\u064A\u060C \u0645\u0646 \u0641\u0636\u0644\u0643.","Your bench \u2192 your shelf":"\u0645\u0646 \u0627\u0644\u0637\u0627\u0648\u0644\u0629 \u2190 \u0625\u0644\u0649 \u0627\u0644\u0631\u0641",ITEMS:"\u0623\u0635\u0646\u0627\u0641","THE SCANNING SPOT":"\u0645\u0646\u0637\u0642\u0629 \u0627\u0644\u0645\u0633\u062D","Bring on the beeps.":"\u0644\u0646\u0628\u062F\u0623 \u0627\u0644\u0645\u0633\u062D.","Scan next demo item \u25A5":"\u0627\u0645\u0633\u062D \u0627\u0644\u0635\u0646\u0641 \u0627\u0644\u062A\u062C\u0631\u064A\u0628\u064A \u0627\u0644\u062A\u0627\u0644\u064A \u25A5","How are you scanning?":"\u0643\u064A\u0641 \u062A\u0631\u064A\u062F \u0627\u0644\u0645\u0633\u062D\u061F","Handheld \xB7 rear camera":"\u0628\u0627\u0644\u064A\u062F \xB7 \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u062E\u0644\u0641\u064A\u0629","Screen-up bench \xB7 front camera":"\u0639\u0644\u0649 \u0627\u0644\u0637\u0627\u0648\u0644\u0629 \u0648\u0627\u0644\u0634\u0627\u0634\u0629 \u0644\u0644\u0623\u0639\u0644\u0649 \xB7 \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u0623\u0645\u0627\u0645\u064A\u0629","Hands-free stand \xB7 rear camera":"\u0639\u0644\u0649 \u062D\u0627\u0645\u0644 \xB7 \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u062E\u0644\u0641\u064A\u0629","Camera / lens":"\u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0623\u0648 \u0627\u0644\u0639\u062F\u0633\u0629","Rear camera (automatic)":"\u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u062E\u0644\u0641\u064A\u0629 (\u062A\u0644\u0642\u0627\u0626\u064A)","Front camera (automatic)":"\u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u0623\u0645\u0627\u0645\u064A\u0629 (\u062A\u0644\u0642\u0627\u0626\u064A)","Open camera scanner \u25A5":"\u0627\u0641\u062A\u062D \u0645\u0627\u0633\u062D \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u25A5","Stop camera":"\u0623\u0648\u0642\u0641 \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627","Live barcode camera preview":"\u0645\u0639\u0627\u064A\u0646\u0629 \u0645\u0628\u0627\u0634\u0631\u0629 \u0644\u0643\u0627\u0645\u064A\u0631\u0627 \u0627\u0644\u0628\u0627\u0631\u0643\u0648\u062F","Whole barcode + blank edges":"\u0627\u0644\u0628\u0627\u0631\u0643\u0648\u062F \u0643\u0627\u0645\u0644\u064B\u0627 \u0645\u0639 \u062D\u0648\u0627\u0641 \u0641\u0627\u0631\u063A\u0629","Choose a setup, then open the camera.":"\u0627\u062E\u062A\u0631 \u0625\u0639\u062F\u0627\u062F \u0627\u0644\u0645\u0633\u062D \u062B\u0645 \u0627\u0641\u062A\u062D \u0627\u0644\u0643\u0627\u0645\u064A\u0631\u0627.","Mirror preview":"\u0627\u0639\u0643\u0633 \u0627\u0644\u0645\u0639\u0627\u064A\u0646\u0629","Turn preview upside down":"\u0627\u0642\u0644\u0628 \u0627\u0644\u0645\u0639\u0627\u064A\u0646\u0629 \u0631\u0623\u0633\u064B\u0627 \u0639\u0644\u0649 \u0639\u0642\u0628","Light off":"\u0627\u0644\u0625\u0636\u0627\u0621\u0629 \u0645\u062A\u0648\u0642\u0641\u0629","Light on":"\u0627\u0644\u0625\u0636\u0627\u0621\u0629 \u0645\u0641\u0639\u0651\u0644\u0629","Focus, zoom & exposure":"\u0627\u0644\u062A\u0631\u0643\u064A\u0632 \u0648\u0627\u0644\u062A\u0643\u0628\u064A\u0631 \u0648\u0627\u0644\u062A\u0639\u0631\u064A\u0636",Barcode:"\u0627\u0644\u0628\u0627\u0631\u0643\u0648\u062F","Look up":"\u0627\u0628\u062D\u062B","Look up product":"\u0627\u0628\u062D\u062B \u0639\u0646 \u0627\u0644\u0645\u0646\u062A\u062C",Quantity:"\u0627\u0644\u0643\u0645\u064A\u0629",Unit:"\u0627\u0644\u0648\u062D\u062F\u0629",Ingredient:"\u0627\u0644\u0645\u0643\u0648\u0651\u0646","Product name":"\u0627\u0633\u0645 \u0627\u0644\u0645\u0646\u062A\u062C","Expiry date":"\u062A\u0627\u0631\u064A\u062E \u0627\u0644\u0627\u0646\u062A\u0647\u0627\u0621",Optional:"\u0627\u062E\u062A\u064A\u0627\u0631\u064A",Remove:"\u0625\u0632\u0627\u0644\u0629",Edit:"\u062A\u0639\u062F\u064A\u0644",Save:"\u062D\u0641\u0638",Cancel:"\u0625\u0644\u063A\u0627\u0621",Close:"\u0625\u063A\u0644\u0627\u0642",Delete:"\u062D\u0630\u0641",Add:"\u0625\u0636\u0627\u0641\u0629",Search:"\u0628\u062D\u062B",All:"\u0627\u0644\u0643\u0644",Unknown:"\u063A\u064A\u0631 \u0645\u0639\u0631\u0648\u0641",unknown:"\u063A\u064A\u0631 \u0645\u0639\u0631\u0648\u0641","Loading\u2026":"\u062C\u0627\u0631\u064D \u0627\u0644\u062A\u062D\u0645\u064A\u0644\u2026","Loading recipes\u2026":"\u062C\u0627\u0631\u064D \u062A\u062D\u0645\u064A\u0644 \u0627\u0644\u0648\u0635\u0641\u0627\u062A\u2026","Looking up\u2026":"\u062C\u0627\u0631\u064D \u0627\u0644\u0628\u062D\u062B\u2026","Review details at the end":"\u0631\u0627\u062C\u0639 \u0627\u0644\u062A\u0641\u0627\u0635\u064A\u0644 \u0641\u064A \u0627\u0644\u0646\u0647\u0627\u064A\u0629","Final receipt \u2192":"\u0627\u0644\u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0646\u0647\u0627\u0626\u064A\u0629 \u2190","Nothing scanned yet. Let\u2019s see what\u2019s hiding.":"\u0644\u0645 \u062A\u0645\u0633\u062D \u0623\u064A \u0635\u0646\u0641 \u0628\u0639\u062F. \u0644\u0646\u0643\u062A\u0634\u0641 \u0645\u0627 \u0644\u062F\u064A\u0643.","1 package":"\u0639\u0628\u0648\u0629 \u0648\u0627\u062D\u062F\u0629","Scan \u2192 beep \u2192 put it back. Every scan is accepted automatically.":"\u0627\u0645\u0633\u062D\u060C \u0648\u0627\u0633\u062A\u0645\u0639 \u0644\u0644\u062A\u0646\u0628\u064A\u0647\u060C \u062B\u0645 \u0623\u0639\u062F \u0627\u0644\u0635\u0646\u0641. \u064A\u064F\u0636\u0627\u0641 \u0643\u0644 \u0645\u0633\u062D \u062A\u0644\u0642\u0627\u0626\u064A\u064B\u0627.","From your shopping bag to its new home.":"\u0645\u0646 \u0643\u064A\u0633 \u0627\u0644\u062A\u0633\u0648\u0651\u0642 \u0625\u0644\u0649 \u0645\u0643\u0627\u0646\u0647 \u0627\u0644\u062C\u062F\u064A\u062F.","Scan recorded items from this location. Each scan stages removal of that whole recorded item.":"\u0627\u0645\u0633\u062D \u0627\u0644\u0623\u0635\u0646\u0627\u0641 \u0627\u0644\u0645\u0633\u062C\u0651\u0644\u0629 \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u0643\u0627\u0646. \u064A\u062C\u0647\u0651\u0632 \u0643\u0644 \u0645\u0633\u062D \u0625\u0632\u0627\u0644\u0629 \u0627\u0644\u0635\u0646\u0641 \u0627\u0644\u0645\u0633\u062C\u0651\u0644 \u0643\u0627\u0645\u0644\u064B\u0627.","Accepted. Next item, please.":"\u062A\u0645\u062A \u0627\u0644\u0625\u0636\u0627\u0641\u0629. \u0627\u0644\u0635\u0646\u0641 \u0627\u0644\u062A\u0627\u0644\u064A\u060C \u0645\u0646 \u0641\u0636\u0644\u0643.","Accepted. Looking up details while you keep scanning\u2026":"\u062A\u0645\u062A \u0627\u0644\u0625\u0636\u0627\u0641\u0629. \u062C\u0627\u0631\u064D \u0627\u0644\u0628\u062D\u062B \u0639\u0646 \u0627\u0644\u062A\u0641\u0627\u0635\u064A\u0644\u060C \u0648\u064A\u0645\u0643\u0646\u0643 \u0645\u062A\u0627\u0628\u0639\u0629 \u0627\u0644\u0645\u0633\u062D\u2026","Unknown product kept on your receipt. Keep scanning; review it at the end.":"\u0623\u064F\u0628\u0642\u064A \u0627\u0644\u0645\u0646\u062A\u062C \u063A\u064A\u0631 \u0627\u0644\u0645\u0639\u0631\u0648\u0641 \u0641\u064A \u0642\u0627\u0626\u0645\u062A\u0643. \u062A\u0627\u0628\u0639 \u0627\u0644\u0645\u0633\u062D \u0648\u0631\u0627\u062C\u0639\u0647 \u0641\u064A \u0627\u0644\u0646\u0647\u0627\u064A\u0629.","Product details unavailable.":"\u062A\u0641\u0627\u0635\u064A\u0644 \u0627\u0644\u0645\u0646\u062A\u062C \u063A\u064A\u0631 \u0645\u062A\u0627\u062D\u0629.","Lookup unavailable.":"\u0627\u0644\u0628\u062D\u062B \u063A\u064A\u0631 \u0645\u062A\u0627\u062D.","Enter or scan a barcode first.":"\u0623\u062F\u062E\u0644 \u0628\u0627\u0631\u0643\u0648\u062F \u0623\u0648 \u0627\u0645\u0633\u062D\u0647 \u0623\u0648\u0644\u064B\u0627.","Recipes imported.":"\u062A\u0645 \u0627\u0633\u062A\u064A\u0631\u0627\u062F \u0627\u0644\u0648\u0635\u0641\u0627\u062A.","No remaining matching inventory item in this source location. Nothing removed.":"\u0644\u0627 \u064A\u0648\u062C\u062F \u0635\u0646\u0641 \u0645\u0637\u0627\u0628\u0642 \u0645\u062A\u0628\u0642\u064D \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u0643\u0627\u0646. \u0644\u0645 \u064A\u064F\u062D\u0630\u0641 \u0634\u064A\u0621.","Demo kitchen \xB7 separate sample data.":"\u0645\u0637\u0628\u062E \u062A\u062C\u0631\u064A\u0628\u064A \xB7 \u0628\u064A\u0627\u0646\u0627\u062A \u0646\u0645\u0648\u0630\u062C\u064A\u0629 \u0645\u0646\u0641\u0635\u0644\u0629.","Signed in \xB7 automatic cloud saves; local copy available offline.":"\u062A\u0645 \u062A\u0633\u062C\u064A\u0644 \u0627\u0644\u062F\u062E\u0648\u0644 \xB7 \u062D\u0641\u0638 \u0633\u062D\u0627\u0628\u064A \u062A\u0644\u0642\u0627\u0626\u064A \u0648\u0646\u0633\u062E\u0629 \u0645\u062D\u0644\u064A\u0629 \u0645\u062A\u0627\u062D\u0629 \u062F\u0648\u0646 \u0627\u062A\u0635\u0627\u0644.","Guest pantry \xB7 saved in this browser.":"\u0645\u062E\u0632\u0648\u0646 \u0627\u0644\u0636\u064A\u0641 \xB7 \u0645\u062D\u0641\u0648\u0638 \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u062A\u0635\u0641\u062D.","Offline \xB7 Pantry and downloaded recipes work. New product and shop lookups need internet.":"\u062F\u0648\u0646 \u0627\u062A\u0635\u0627\u0644 \xB7 \u064A\u0639\u0645\u0644 \u0627\u0644\u0645\u062E\u0632\u0648\u0646 \u0648\u0627\u0644\u0648\u0635\u0641\u0627\u062A \u0627\u0644\u0645\u0646\u0632\u0651\u0644\u0629. \u064A\u062A\u0637\u0644\u0651\u0628 \u0627\u0644\u0628\u062D\u062B \u0639\u0646 \u0645\u0646\u062A\u062C\u0627\u062A \u0648\u0645\u062A\u0627\u062C\u0631 \u062C\u062F\u064A\u062F\u0629 \u0627\u062A\u0635\u0627\u0644\u064B\u0627 \u0628\u0627\u0644\u0625\u0646\u062A\u0631\u0646\u062A.","Demo changes stay separate from your kitchen.":"\u062A\u0628\u0642\u0649 \u062A\u063A\u064A\u064A\u0631\u0627\u062A \u0627\u0644\u062A\u062C\u0631\u0628\u0629 \u0645\u0646\u0641\u0635\u0644\u0629 \u0639\u0646 \u0645\u0637\u0628\u062E\u0643.","Local changes \xB7 saving automatically.":"\u062A\u063A\u064A\u064A\u0631\u0627\u062A \u0645\u062D\u0644\u064A\u0629 \xB7 \u062C\u0627\u0631\u064D \u0627\u0644\u062D\u0641\u0638 \u062A\u0644\u0642\u0627\u0626\u064A\u064B\u0627.","Guest data is saved in this browser.":"\u062A\u064F\u062D\u0641\u0638 \u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0636\u064A\u0641 \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u062A\u0635\u0641\u062D.","Guest data stays in this browser.":"\u062A\u0628\u0642\u0649 \u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0636\u064A\u0641 \u0641\u064A \u0647\u0630\u0627 \u0627\u0644\u0645\u062A\u0635\u0641\u062D.","Preferred country":"\u0627\u0644\u0628\u0644\u062F \u0627\u0644\u0645\u0641\u0636\u0651\u0644","Global \xB7 all countries":"\u0639\u0627\u0644\u0645\u064A \xB7 \u062C\u0645\u064A\u0639 \u0627\u0644\u0628\u0644\u062F\u0627\u0646","Preferred display units":"\u0648\u062D\u062F\u0627\u062A \u0627\u0644\u0639\u0631\u0636 \u0627\u0644\u0645\u0641\u0636\u0651\u0644\u0629",Metric:"\u0645\u062A\u0631\u064A",Imperial:"\u0625\u0645\u0628\u0631\u0627\u0637\u0648\u0631\u064A","Sign out":"\u062A\u0633\u062C\u064A\u0644 \u0627\u0644\u062E\u0631\u0648\u062C","Save kitchen to cloud \u2191":"\u0627\u062D\u0641\u0638 \u0627\u0644\u0645\u0637\u0628\u062E \u0641\u064A \u0627\u0644\u0633\u062D\u0627\u0628\u0629 \u2191","Restore cloud copy \u2193":"\u0627\u0633\u062A\u0639\u062F \u0627\u0644\u0646\u0633\u062E\u0629 \u0627\u0644\u0633\u062D\u0627\u0628\u064A\u0629 \u2193","Backups & recipe imports":"\u0627\u0644\u0646\u0633\u062E \u0627\u0644\u0627\u062D\u062A\u064A\u0627\u0637\u064A\u0629 \u0648\u0627\u0633\u062A\u064A\u0631\u0627\u062F \u0627\u0644\u0648\u0635\u0641\u0627\u062A","Export kitchen backup":"\u0635\u062F\u0651\u0631 \u0646\u0633\u062E\u0629 \u0627\u062D\u062A\u064A\u0627\u0637\u064A\u0629 \u0644\u0644\u0645\u0637\u0628\u062E","Sign in to restore your pantry on another device.":"\u0633\u062C\u0651\u0644 \u0627\u0644\u062F\u062E\u0648\u0644 \u0644\u0627\u0633\u062A\u0639\u0627\u062F\u0629 \u0645\u062E\u0632\u0648\u0646\u0643 \u0639\u0644\u0649 \u062C\u0647\u0627\u0632 \u0622\u062E\u0631.","Account setup pending. Guest pantry and offline recipes remain available.":"\u0625\u0639\u062F\u0627\u062F \u0627\u0644\u062D\u0633\u0627\u0628 \u0642\u064A\u062F \u0627\u0644\u0627\u0646\u062A\u0638\u0627\u0631. \u064A\u0638\u0644 \u0645\u062E\u0632\u0648\u0646 \u0627\u0644\u0636\u064A\u0641 \u0648\u0627\u0644\u0648\u0635\u0641\u0627\u062A \u062F\u0648\u0646 \u0627\u062A\u0635\u0627\u0644 \u0645\u062A\u0627\u062D\u064A\u0646.","Exit the demo to save your own kitchen.":"\u0623\u0646\u0647\u0650 \u0627\u0644\u062A\u062C\u0631\u0628\u0629 \u0644\u062D\u0641\u0638 \u0645\u0637\u0628\u062E\u0643 \u0627\u0644\u062E\u0627\u0635.","Cloud operation failed.":"\u0641\u0634\u0644\u062A \u0627\u0644\u0639\u0645\u0644\u064A\u0629 \u0627\u0644\u0633\u062D\u0627\u0628\u064A\u0629.","Replace this browser copy with the cloud save? Export local changes first.":"\u0647\u0644 \u062A\u0631\u064A\u062F \u0627\u0633\u062A\u0628\u062F\u0627\u0644 \u0646\u0633\u062E\u0629 \u0647\u0630\u0627 \u0627\u0644\u0645\u062A\u0635\u0641\u062D \u0628\u0627\u0644\u0646\u0633\u062E\u0629 \u0627\u0644\u0633\u062D\u0627\u0628\u064A\u0629\u061F \u0635\u062F\u0651\u0631 \u0627\u0644\u062A\u063A\u064A\u064A\u0631\u0627\u062A \u0627\u0644\u0645\u062D\u0644\u064A\u0629 \u0623\u0648\u0644\u064B\u0627.","Cloud copy restored.":"\u062A\u0645\u062A \u0627\u0633\u062A\u0639\u0627\u062F\u0629 \u0627\u0644\u0646\u0633\u062E\u0629 \u0627\u0644\u0633\u062D\u0627\u0628\u064A\u0629.","No cloud copy yet. Add items or import a backup, then save.":"\u0644\u0627 \u062A\u0648\u062C\u062F \u0646\u0633\u062E\u0629 \u0633\u062D\u0627\u0628\u064A\u0629 \u0628\u0639\u062F. \u0623\u0636\u0641 \u0623\u0635\u0646\u0627\u0641\u064B\u0627 \u0623\u0648 \u0627\u0633\u062A\u0648\u0631\u062F \u0646\u0633\u062E\u0629 \u0627\u062D\u062A\u064A\u0627\u0637\u064A\u0629\u060C \u062B\u0645 \u0627\u062D\u0641\u0638.","Saved to cloud. Automatic saving continues.":"\u062A\u0645 \u0627\u0644\u062D\u0641\u0638 \u0641\u064A \u0627\u0644\u0633\u062D\u0627\u0628\u0629. \u064A\u0633\u062A\u0645\u0631 \u0627\u0644\u062D\u0641\u0638 \u0627\u0644\u062A\u0644\u0642\u0627\u0626\u064A.","Check your email to confirm your account.":"\u062A\u062D\u0642\u0651\u0642 \u0645\u0646 \u0628\u0631\u064A\u062F\u0643 \u0627\u0644\u0625\u0644\u0643\u062A\u0631\u0648\u0646\u064A \u0644\u062A\u0623\u0643\u064A\u062F \u062D\u0633\u0627\u0628\u0643.","Check your email for recovery instructions.":"\u062A\u062D\u0642\u0651\u0642 \u0645\u0646 \u0628\u0631\u064A\u062F\u0643 \u0627\u0644\u0625\u0644\u0643\u062A\u0631\u0648\u0646\u064A \u0644\u0644\u062D\u0635\u0648\u0644 \u0639\u0644\u0649 \u062A\u0639\u0644\u064A\u0645\u0627\u062A \u0627\u0644\u0627\u0633\u062A\u0639\u0627\u062F\u0629.","Forgot password?":"\u0646\u0633\u064A\u062A \u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631\u061F","Set new password":"\u0639\u064A\u0651\u0646 \u0643\u0644\u0645\u0629 \u0645\u0631\u0648\u0631 \u062C\u062F\u064A\u062F\u0629",Email:"\u0627\u0644\u0628\u0631\u064A\u062F \u0627\u0644\u0625\u0644\u0643\u062A\u0631\u0648\u0646\u064A",Password:"\u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631","Create account":"\u0625\u0646\u0634\u0627\u0621 \u062D\u0633\u0627\u0628","YOUR INGREDIENTS, NEW IDEAS":"\u0645\u0643\u0648\u0651\u0646\u0627\u062A\u0643 \u0648\u0623\u0641\u0643\u0627\u0631 \u062C\u062F\u064A\u062F\u0629","START WITH WHAT YOU HAVE":"\u0627\u0628\u062F\u0623 \u0628\u0645\u0627 \u0644\u062F\u064A\u0643","Three ideas for dinner.":"\u062B\u0644\u0627\u062B \u0623\u0641\u0643\u0627\u0631 \u0644\u0644\u0639\u0634\u0627\u0621.","Household portions":"\u062D\u0635\u0635 \u0627\u0644\u0623\u0633\u0631\u0629","Refresh \u21BB":"\u062A\u062D\u062F\u064A\u062B \u21BB","Find a dish or ingredient":"\u0627\u0628\u062D\u062B \u0639\u0646 \u0637\u0628\u0642 \u0623\u0648 \u0645\u0643\u0648\u0651\u0646","e.g. rice, soup, coconut":"\u0645\u062B\u0644: \u0627\u0644\u0623\u0631\u0632 \u0623\u0648 \u0627\u0644\u062D\u0633\u0627\u0621 \u0623\u0648 \u062C\u0648\u0632 \u0627\u0644\u0647\u0646\u062F","Cook from":"\u0627\u0633\u062A\u062E\u062F\u0645 \u0645\u062E\u0632\u0648\u0646","Whole kitchen":"\u0627\u0644\u0645\u0637\u0628\u062E \u0643\u0644\u0647",Show:"\u0639\u0631\u0636","All menus":"\u062C\u0645\u064A\u0639 \u0627\u0644\u0648\u062C\u0628\u0627\u062A","Ready to cook":"\u062C\u0627\u0647\u0632 \u0644\u0644\u0637\u0647\u064A","Missing ingredients":"\u0645\u0643\u0648\u0651\u0646\u0627\u062A \u0646\u0627\u0642\u0635\u0629","Needs review":"\u064A\u062D\u062A\u0627\u062C \u0625\u0644\u0649 \u0645\u0631\u0627\u062C\u0639\u0629","Who is eating?":"\u0645\u0646 \u0633\u064A\u062A\u0646\u0627\u0648\u0644 \u0627\u0644\u0637\u0639\u0627\u0645\u061F","Cook this meal":"\u0627\u0637\u0647\u0650 \u0647\u0630\u0647 \u0627\u0644\u0648\u062C\u0628\u0629","Serve / after meal":"\u0642\u062F\u0651\u0645 \u0627\u0644\u0648\u062C\u0628\u0629 \u0623\u0648 \u0633\u062C\u0651\u0644\u0647\u0627","Save as favourite":"\u0627\u062D\u0641\u0638 \u0641\u064A \u0627\u0644\u0645\u0641\u0636\u0651\u0644\u0629","Saved favourite \u2713":"\u0645\u062D\u0641\u0648\u0638 \u0641\u064A \u0627\u0644\u0645\u0641\u0636\u0651\u0644\u0629 \u2713",Breakfast:"\u0627\u0644\u0641\u0637\u0648\u0631",Lunch:"\u0627\u0644\u063A\u062F\u0627\u0621",Dinner:"\u0627\u0644\u0639\u0634\u0627\u0621",Snack:"\u0648\u062C\u0628\u0629 \u062E\u0641\u064A\u0641\u0629",Meal:"\u0627\u0644\u0648\u062C\u0628\u0629",Date:"\u0627\u0644\u062A\u0627\u0631\u064A\u062E",Daily:"\u064A\u0648\u0645\u064A",Weekly:"\u0623\u0633\u0628\u0648\u0639\u064A",Portions:"\u0627\u0644\u062D\u0635\u0635","Planned meals":"\u0627\u0644\u0648\u062C\u0628\u0627\u062A \u0627\u0644\u0645\u062E\u0637\u0651\u0637\u0629","Planned portions":"\u0627\u0644\u062D\u0635\u0635 \u0627\u0644\u0645\u062E\u0637\u0651\u0637\u0629","All storage":"\u062C\u0645\u064A\u0639 \u0623\u0645\u0627\u0643\u0646 \u0627\u0644\u062A\u062E\u0632\u064A\u0646","Edit location":"\u0639\u062F\u0651\u0644 \u0645\u0643\u0627\u0646 \u0627\u0644\u062A\u062E\u0632\u064A\u0646","Edit preferences":"\u0639\u062F\u0651\u0644 \u0627\u0644\u062A\u0641\u0636\u064A\u0644\u0627\u062A","Remove member":"\u0623\u0632\u0644 \u0627\u0644\u0634\u062E\u0635","Add people, their preferences and dietary advisors to personalise your menus.":"\u0623\u0636\u0641 \u0627\u0644\u0623\u0634\u062E\u0627\u0635 \u0648\u062A\u0641\u0636\u064A\u0644\u0627\u062A\u0647\u0645 \u0648\u062E\u064A\u0627\u0631\u0627\u062A\u0647\u0645 \u0627\u0644\u063A\u0630\u0627\u0626\u064A\u0629 \u0644\u062A\u062E\u0635\u064A\u0635 \u0627\u0644\u0648\u062C\u0628\u0627\u062A.","Recipe no longer available":"\u0627\u0644\u0648\u0635\u0641\u0629 \u0644\u0645 \u062A\u0639\u062F \u0645\u062A\u0627\u062D\u0629","Meal nutrients & notes":"\u0645\u063A\u0630\u0651\u064A\u0627\u062A \u0627\u0644\u0648\u062C\u0628\u0629 \u0648\u0627\u0644\u0645\u0644\u0627\u062D\u0638\u0627\u062A","Delete log":"\u0627\u062D\u0630\u0641 \u0627\u0644\u0633\u062C\u0644","AFTER THE LAST BITE":"\u0628\u0639\u062F \u0627\u0644\u0648\u062C\u0628\u0629","How did the meal go?":"\u0643\u064A\u0641 \u0643\u0627\u0646\u062A \u0627\u0644\u0648\u062C\u0628\u0629\u061F","Recipe or custom meal":"\u0648\u0635\u0641\u0629 \u0623\u0648 \u0648\u062C\u0628\u0629 \u0645\u062E\u0635\u0651\u0635\u0629","Date eaten":"\u062A\u0627\u0631\u064A\u062E \u062A\u0646\u0627\u0648\u0644 \u0627\u0644\u0637\u0639\u0627\u0645","Who ate this?":"\u0645\u0646 \u062A\u0646\u0627\u0648\u0644 \u0647\u0630\u0647 \u0627\u0644\u0648\u062C\u0628\u0629\u061F","Portions served":"\u0627\u0644\u062D\u0635\u0635 \u0627\u0644\u0645\u0642\u062F\u0651\u0645\u0629","Eaten (%) \xB7 optional":"\u0627\u0644\u0646\u0633\u0628\u0629 \u0627\u0644\u0645\u0623\u0643\u0648\u0644\u0629 (%) \xB7 \u0627\u062E\u062A\u064A\u0627\u0631\u064A","100 if left blank":"\u0661\u0660\u0660 \u0625\u0630\u0627 \u062A\u064F\u0631\u0643 \u0641\u0627\u0631\u063A\u064B\u0627","What happened to the rest?":"\u0645\u0627\u0630\u0627 \u062D\u062F\u062B \u0644\u0644\u0628\u0627\u0642\u064A\u061F","Not recorded":"\u063A\u064A\u0631 \u0645\u0633\u062C\u0651\u0644","Saved for later":"\u0645\u062D\u0641\u0648\u0638 \u0644\u0648\u0642\u062A \u0644\u0627\u062D\u0642",Discarded:"\u062A\u0645 \u0627\u0644\u062A\u062E\u0644\u0651\u0635 \u0645\u0646\u0647","Shared with someone else":"\u062A\u0645\u062A \u0645\u0634\u0627\u0631\u0643\u062A\u0647 \u0645\u0639 \u0634\u062E\u0635 \u0622\u062E\u0631","Meal name":"\u0627\u0633\u0645 \u0627\u0644\u0648\u062C\u0628\u0629","Meal notes":"\u0645\u0644\u0627\u062D\u0638\u0627\u062A \u0627\u0644\u0648\u062C\u0628\u0629","Likes, dislikes, leftovers\u2026":"\u0645\u0627 \u0623\u0639\u062C\u0628\u0643 \u0648\u0645\u0627 \u0644\u0645 \u064A\u0639\u062C\u0628\u0643 \u0648\u0628\u0642\u0627\u064A\u0627 \u0627\u0644\u0637\u0639\u0627\u0645\u2026","Save after-meal record \u2713":"\u0627\u062D\u0641\u0638 \u0633\u062C\u0644 \u0645\u0627 \u0628\u0639\u062F \u0627\u0644\u0648\u062C\u0628\u0629 \u2713",Energy:"\u0627\u0644\u0637\u0627\u0642\u0629",Protein:"\u0627\u0644\u0628\u0631\u0648\u062A\u064A\u0646",Carbohydrates:"\u0627\u0644\u0643\u0631\u0628\u0648\u0647\u064A\u062F\u0631\u0627\u062A",Fat:"\u0627\u0644\u062F\u0647\u0648\u0646",Fibre:"\u0627\u0644\u0623\u0644\u064A\u0627\u0641",Sugar:"\u0627\u0644\u0633\u0643\u0631",Sodium:"\u0627\u0644\u0635\u0648\u062F\u064A\u0648\u0645",Salt:"\u0627\u0644\u0645\u0644\u062D","Search recipes":"\u0627\u0628\u062D\u062B \u0639\u0646 \u0627\u0644\u0648\u0635\u0641\u0627\u062A","Read recipe & review quantities":"\u0627\u0642\u0631\u0623 \u0627\u0644\u0648\u0635\u0641\u0629 \u0648\u0631\u0627\u062C\u0639 \u0627\u0644\u0643\u0645\u064A\u0627\u062A","Show more recipes":"\u0627\u0639\u0631\u0636 \u0627\u0644\u0645\u0632\u064A\u062F \u0645\u0646 \u0627\u0644\u0648\u0635\u0641\u0627\u062A","Source instructions":"\u062A\u0639\u0644\u064A\u0645\u0627\u062A \u0627\u0644\u0645\u0635\u062F\u0631","Review for my kitchen":"\u0631\u0627\u062C\u0639\u0647\u0627 \u0644\u0645\u0637\u0628\u062E\u064A","Reviewed serving yield":"\u0639\u062F\u062F \u0627\u0644\u062D\u0635\u0635 \u0628\u0639\u062F \u0627\u0644\u0645\u0631\u0627\u062C\u0639\u0629","Save my reviewed recipe":"\u0627\u062D\u0641\u0638 \u0648\u0635\u0641\u062A\u064A \u0627\u0644\u0645\u0631\u0627\u062C\u064E\u0639\u0629","Download source recipe as JSON-LD":"\u0646\u0632\u0651\u0644 \u0648\u0635\u0641\u0629 \u0627\u0644\u0645\u0635\u062F\u0631 \u0628\u0635\u064A\u063A\u0629 JSON-LD","Keep the kitchen current.":"\u062D\u062F\u0651\u062B \u062D\u0627\u0644\u0629 \u0627\u0644\u0645\u0637\u0628\u062E.","Inventory item":"\u0627\u0644\u0635\u0646\u0641 \u0641\u064A \u0627\u0644\u0645\u062E\u0632\u0648\u0646","Label use-by date (optional)":"\u062A\u0627\u0631\u064A\u062E \u0627\u0644\u0627\u0633\u062A\u062E\u062F\u0627\u0645 \u0639\u0644\u0649 \u0627\u0644\u0639\u0628\u0648\u0629 (\u0627\u062E\u062A\u064A\u0627\u0631\u064A)","Estimated check reminder, days from today (optional)":"\u062A\u0630\u0643\u064A\u0631 \u062A\u0642\u062F\u064A\u0631\u064A \u0628\u0627\u0644\u0641\u062D\u0635\u060C \u0628\u0627\u0644\u0623\u064A\u0627\u0645 \u0645\u0646 \u0627\u0644\u064A\u0648\u0645 (\u0627\u062E\u062A\u064A\u0627\u0631\u064A)","Choose based on this item and storage":"\u0627\u062E\u062A\u0631 \u062D\u0633\u0628 \u0627\u0644\u0635\u0646\u0641 \u0648\u0638\u0631\u0648\u0641 \u062A\u062E\u0632\u064A\u0646\u0647","Use suggested check interval":"\u0627\u0633\u062A\u062E\u062F\u0645 \u0641\u062A\u0631\u0629 \u0627\u0644\u0641\u062D\u0635 \u0627\u0644\u0645\u0642\u062A\u0631\u062D\u0629","Reminder note":"\u0645\u0644\u0627\u062D\u0638\u0629 \u0627\u0644\u062A\u0630\u0643\u064A\u0631","e.g. opened today; check freshness":"\u0645\u062B\u0644: \u0641\u064F\u062A\u062D \u0627\u0644\u064A\u0648\u0645\u061B \u062A\u062D\u0642\u0651\u0642 \u0645\u0646 \u062D\u0627\u0644\u062A\u0647","Save dates & reminder":"\u0627\u062D\u0641\u0638 \u0627\u0644\u062A\u0648\u0627\u0631\u064A\u062E \u0648\u0627\u0644\u062A\u0630\u0643\u064A\u0631","Close recipe":"\u0623\u063A\u0644\u0642 \u0627\u0644\u0648\u0635\u0641\u0629","Close meal log":"\u0623\u063A\u0644\u0642 \u0633\u062C\u0644 \u0627\u0644\u0648\u062C\u0628\u0629","Close freshness settings":"\u0623\u063A\u0644\u0642 \u0625\u0639\u062F\u0627\u062F\u0627\u062A \u0627\u0644\u062A\u0630\u0643\u064A\u0631","Kitchen navigation":"\u0627\u0644\u062A\u0646\u0642\u0651\u0644 \u0641\u064A \u0627\u0644\u0645\u0637\u0628\u062E","offmenu home":"\u0635\u0641\u062D\u0629 offmenu \u0627\u0644\u0631\u0626\u064A\u0633\u064A\u0629","Not available":"\u063A\u064A\u0631 \u0645\u062A\u0627\u062D","not available":"\u063A\u064A\u0631 \u0645\u062A\u0627\u062D","Food data & estimated nutrition":"\u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0637\u0639\u0627\u0645 \u0648\u0627\u0644\u062A\u063A\u0630\u064A\u0629 \u0627\u0644\u062A\u0642\u062F\u064A\u0631\u064A\u0629","Add a meal to see shopping gaps.":"\u0623\u0636\u0641 \u0648\u062C\u0628\u0629 \u0644\u0631\u0624\u064A\u0629 \u0627\u0644\u0645\u0634\u062A\u0631\u064A\u0627\u062A \u0627\u0644\u0646\u0627\u0642\u0635\u0629.","Add a menu to build your ingredient list.":"\u0623\u0636\u0641 \u0648\u062C\u0628\u0629 \u0644\u0625\u0646\u0634\u0627\u0621 \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0645\u0643\u0648\u0651\u0646\u0627\u062A.","Unmeasured ingredients to review":"\u0645\u0643\u0648\u0651\u0646\u0627\u062A \u063A\u064A\u0631 \u0645\u0642\u0627\u0633\u0629 \u062A\u062D\u062A\u0627\u062C \u0625\u0644\u0649 \u0645\u0631\u0627\u062C\u0639\u0629","No measured ingredient gaps. Check unmeasured ingredients below.":"\u0644\u0627 \u062A\u0648\u062C\u062F \u0645\u0643\u0648\u0651\u0646\u0627\u062A \u0645\u0642\u0627\u0633\u0629 \u0646\u0627\u0642\u0635\u0629. \u0631\u0627\u062C\u0639 \u0627\u0644\u0645\u0643\u0648\u0651\u0646\u0627\u062A \u063A\u064A\u0631 \u0627\u0644\u0645\u0642\u0627\u0633\u0629 \u0623\u062F\u0646\u0627\u0647.","Your food journal starts with the next meal. Log a recipe or enter totals from a label.":"\u064A\u0628\u062F\u0623 \u0633\u062C\u0644 \u0637\u0639\u0627\u0645\u0643 \u0628\u0627\u0644\u0648\u062C\u0628\u0629 \u0627\u0644\u062A\u0627\u0644\u064A\u0629. \u0633\u062C\u0651\u0644 \u0648\u0635\u0641\u0629 \u0623\u0648 \u0623\u062F\u062E\u0644 \u0627\u0644\u0625\u062C\u0645\u0627\u0644\u064A\u0627\u062A \u0645\u0646 \u0627\u0644\u0639\u0628\u0648\u0629.","Unavailable source text":"\u0646\u0635 \u0627\u0644\u0645\u0635\u062F\u0631 \u063A\u064A\u0631 \u0645\u062A\u0627\u062D","Nutrient metric":"\u0627\u0644\u0645\u0624\u0634\u0631 \u0627\u0644\u063A\u0630\u0627\u0626\u064A",Status:"\u0627\u0644\u062D\u0627\u0644\u0629",Total:"\u0627\u0644\u0625\u062C\u0645\u0627\u0644\u064A","Known subtotal":"\u0627\u0644\u0625\u062C\u0645\u0627\u0644\u064A \u0627\u0644\u062C\u0632\u0626\u064A \u0627\u0644\u0645\u0639\u0631\u0648\u0641","Per 1,000 kcal":"\u0644\u0643\u0644 \u0661\u0660\u0660\u0660 \u0633\u0639\u0631\u0629 \u062D\u0631\u0627\u0631\u064A\u0629","Mass coverage":"\u062A\u063A\u0637\u064A\u0629 \u0627\u0644\u0643\u062A\u0644\u0629","Done.":"\u062A\u0645\u0651.",Country:"\u0627\u0644\u0628\u0644\u062F",Evidence:"\u0627\u0644\u0623\u062F\u0644\u0629","Global food and evidence workspace":"\u0645\u0633\u0627\u062D\u0629 \u0639\u0645\u0644 \u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0637\u0639\u0627\u0645 \u0648\u0627\u0644\u0623\u062F\u0644\u0629 \u0627\u0644\u0639\u0627\u0644\u0645\u064A\u0629","OffMenu \xB7 Global data workspace":"OffMenu \xB7 \u0645\u0633\u0627\u062D\u0629 \u0639\u0645\u0644 \u0627\u0644\u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0639\u0627\u0644\u0645\u064A\u0629","\u2190 My kitchen":"\u2190 \u0645\u0637\u0628\u062E\u064A","Open country":"\u0627\u0639\u0631\u0636 \u0627\u0644\u0628\u0644\u062F","Country coverage and starter baskets":"\u062A\u063A\u0637\u064A\u0629 \u0627\u0644\u0628\u0644\u062F\u0627\u0646 \u0648\u0633\u0644\u0627\u0644 \u0627\u0644\u0628\u062F\u0627\u064A\u0629","Calculate nutrients and coverage":"\u0627\u062D\u0633\u0628 \u0627\u0644\u0639\u0646\u0627\u0635\u0631 \u0627\u0644\u063A\u0630\u0627\u0626\u064A\u0629 \u0648\u0627\u0644\u062A\u063A\u0637\u064A\u0629","Native language support":"\u062F\u0639\u0645 \u0627\u0644\u0644\u063A\u0629 \u0627\u0644\u0623\u0635\u0644\u064A\u0629","National sources / access":"\u0627\u0644\u0645\u0635\u0627\u062F\u0631 \u0627\u0644\u0648\u0637\u0646\u064A\u0629 \u0648\u0625\u0645\u0643\u0627\u0646\u064A\u0629 \u0627\u0644\u0648\u0635\u0648\u0644","Current offmenu coverage":"\u062A\u063A\u0637\u064A\u0629 offmenu \u0627\u0644\u062D\u0627\u0644\u064A\u0629","Source-specific identity":"\u0647\u0648\u064A\u0629 \u062E\u0627\u0635\u0629 \u0628\u0627\u0644\u0645\u0635\u062F\u0631","Candidate identity link":"\u0631\u0627\u0628\u0637 \u0647\u0648\u064A\u0629 \u0645\u0631\u0634\u0651\u062D","Curated concept":"\u0645\u0641\u0647\u0648\u0645 \u0645\u064F\u0631\u0627\u062C\u0639","Identified resource":"\u0645\u0648\u0631\u062F \u0645\u062D\u062F\u0651\u062F \u0627\u0644\u0647\u0648\u064A\u0629","Source assertion":"\u0628\u064A\u0627\u0646 \u0645\u0646 \u0627\u0644\u0645\u0635\u062F\u0631",Candidate:"\u0645\u0631\u0634\u0651\u062D","Editor authored":"\u0645\u0646 \u062A\u0623\u0644\u064A\u0641 \u0627\u0644\u0645\u062D\u0631\u0651\u0631",Reviewed:"\u0645\u064F\u0631\u0627\u062C\u0639",Verified:"\u0645\u062A\u062D\u0642\u0651\u0642 \u0645\u0646\u0647",Conflicting:"\u0645\u062A\u0639\u0627\u0631\u0636",Superseded:"\u0645\u0633\u062A\u0628\u062F\u064E\u0644","Needs transcription":"\u064A\u062D\u062A\u0627\u062C \u0625\u0644\u0649 \u062A\u0641\u0631\u064A\u063A \u0627\u0644\u0646\u0635","Recipe Variant":"\u0646\u0633\u062E\u0629 \u0645\u0646 \u0648\u0635\u0641\u0629","Recipe Step":"\u062E\u0637\u0648\u0629 \u0641\u064A \u0627\u0644\u0648\u0635\u0641\u0629","Recipe Concept":"\u0645\u0641\u0647\u0648\u0645 \u0648\u0635\u0641\u0629",instruction:"\u062A\u0639\u0644\u064A\u0645\u0627\u062A",position:"\u0627\u0644\u062A\u0631\u062A\u064A\u0628","original Source Record":"\u0633\u062C\u0644 \u0627\u0644\u0645\u0635\u062F\u0631 \u0627\u0644\u0623\u0635\u0644\u064A"});var op=Object.freeze(["en","ar"]);var Cx=Object.freeze([{code:"en",name:"English",direction:"ltr"},{code:"ar",name:"\u0627\u0644\u0639\u0631\u0628\u064A\u0629",direction:"rtl"}]);var lp={plant:["rice|long grain rice|basmati|jasmine rice","peas|green peas|frozen peas","carrot|carrots","olive oil|extra virgin olive oil","water|tap water","red lentils|red lentil|split red lentils","green lentils|brown lentils","spinach|baby spinach","mushroom|mushrooms","broccoli","potato|potatoes","sweet potato|sweet potatoes","cucumber","tomato|tomatoes","lemon juice","couscous","cumin","quinoa","cauliflower","zucchini|courgette|courgettes","eggplant|aubergine","coriander|cilantro","onion|onions","garlic","ginger","apple|apples","banana|bananas","orange","pear","peach","plum","strawberry","blueberry","raspberry","grapes","melon","pineapple","mango","avocado","lettuce","cabbage","kale","celery","beetroot|beet","pumpkin|squash","capsicum|bell pepper","green beans","asparagus","leek","spring onion|scallion","radish","fennel","parsley","basil","mint","dill","rosemary","thyme","oregano","chilli|chili","black pepper","salt","sugar","brown sugar","maple syrup","sunflower oil","canola oil|rapeseed oil","sesame oil","vinegar","rice vinegar","cider vinegar","cocoa butter","cocoa powder","coffee","tea","chickpea flour|gram flour|besan","rice flour","corn flour|cornflour|maize flour","almond flour","oats","buckwheat","millet","corn|maize","rice noodles","canned chickpeas|chickpeas canned","canned kidney beans|kidney beans canned","canned tomato|canned tomatoes|tinned tomatoes","coconut milk","coconut cream","almond milk","oat milk","soy milk|soya milk","peanut butter","peanuts","almonds","walnuts","cashew|cashews","hazelnut","sesame seeds","chia seeds","flaxseed|linseed","sunflower seeds","pumpkin seeds","tofu|bean curd","tempeh","chickpeas","kidney beans","black beans"],dairy:["milk|cow milk","cream|dairy cream","cheese|cheddar","butter|dairy butter","yoghurt|yogurt","whey"],meat:["chicken","beef","pork","bacon","turkey","duck","lamb","veal","venison","sausage","ham","gelatin|gelatine","meat"],fish:["fish","salmon","tuna","canned tuna","prawn|shrimp|prawns|shrimps","sardine","anchovy","cod","haddock","mussel","crab","lobster"],animal:["egg|eggs","honey"],compound:["pasta|spaghetti","bread","flatbread","wheat flour|plain flour|flour","barley","rye","bulgur","soy sauce","curry powder","vegetable stock","chicken stock","beef stock"]},cp=Object.entries(lp).flatMap(([e,t])=>t.map(r=>{let[i,...n]=r.split("|");return{id:i,aliases:n,category:e}}));var Ox=new Map(cp.flatMap(e=>[e.id,...e.aliases].map(t=>[t,e])));function Xn(e,t){if(e?.schema==="offmenu-identifier-observation/2")return Qi(e,t);let r=(n,a)=>typeof n=="string"&&n.length>0&&n.length<=a,i=e?.observationKey;return e?.schema==="offmenu-identifier-observation/1"&&/^[a-f0-9]{64}$/.test(e.databaseSha256||"")&&r(e.runId,100)&&e.namespace==="barcode"&&e.lexicalValue===t&&r(e.sourceId,40)&&r(e.releaseId,80)&&(e.sourceRecordId===null||r(e.sourceRecordId,200))&&i&&i.run_id===e.runId&&r(i.input_id,250)&&Number.isSafeInteger(i.record_ordinal)&&i.record_ordinal>=0&&Number.isSafeInteger(i.assertion_id)&&i.assertion_id>0&&(e.detailSelectionSha256===null||/^[a-f0-9]{64}$/.test(e.detailSelectionSha256||""))}var up="offmenu-off-photo-metadata/1",bo=Object.freeze({name:"CC BY-SA 3.0",url:"https://creativecommons.org/licenses/by-sa/3.0/"});var dp=e=>e!==null&&typeof e=="object"&&!Array.isArray(e),Ir=e=>typeof e=="string"&&e.length>0&&e.length<=8192?e:null,Sc=e=>typeof e=="string"&&/^\d{1,32}$/.test(e)?e:null,hp=e=>typeof e=="string"&&/^\d{1,16}$/.test(e)?e:Number.isSafeInteger(e)&&e>=0?String(e):null,yc=e=>e.replaceAll("~","~0").replaceAll("/","~1");function pp(e){if(!Sc(e))return null;let t=e.replace(/^0+/,"")||"0";return t.length<=8?t.padStart(8,"0"):t.length<=12?t.padStart(13,"0"):t}function fp(e){let t=pp(e);return t?.length<=8?t:t?.replace(/^(...)(...)(...)(.*)$/,"$1/$2/$3/$4")}function mp(e,t,r,i=null){if(!Ir(e)||e.length>4096)return null;try{let n=new URL(e),a="/images/products/"+fp(t)+"/";if(n.protocol!=="https:"||n.hostname!=="images.openfoodfacts.org"||n.port||n.username||n.password||n.search||n.hash||n.href!==e||!n.pathname.startsWith(a))return null;let o=/^(front|nutrition|ingredients|packaging)_([a-z]{2})\.(\d{1,16})\.(100|200|400|full)\.(?:jpg|jpeg|png|webp)$/.exec(n.pathname.slice(a.length));return!o||o[1]!==r||i&&o[2]!==i?null:{url:e,role:o[1],language:o[2],revision:o[3],resolution:o[4],selectedKey:o[1]+"_"+o[2]}}catch{return null}}var gp=["title","copyright","copyright_notice","license_notice","disclaimer","attribution"];function vp(e,t,{selected:r=null,raw:i=null,catalogue:n=null}={}){let a={selected:"/images/"+yc(t.selectedKey),raw:"/images/"+yc(hp(r?.imgid)||""),catalogue:"OFF_PHOTOS[key="+String(n?.key||"")+"]"},o=[];for(let[u,l]of[["selected",r],["raw",i],["catalogue",n]])for(let d of gp)Ir(l?.[d])&&o.push({field:d,text:l[d],origin:u,sourceField:a[u]+(u==="catalogue"?".":"/")+d});let s=Ir(i?.uploader)||Ir(r?.uploader)||Ir(n?.contributor),c={};for(let u of["imgid","rev","angle","normalize","white_magic","x1","x2","y1","y2","geometry","coordinates_image_size"])r&&Object.hasOwn(r,u)&&(r[u]===null||typeof r[u]=="boolean"||typeof r[u]=="number"&&Number.isFinite(r[u])||typeof r[u]=="string"&&r[u].length<=8192)&&(c[u]=r[u]);return{schema:up,sourceName:"Open Food Facts",sourceCode:e,productUrl:"https://world.openfoodfacts.org/product/"+e,photoPage:"https://world.openfoodfacts.org/cgi/product_image.pl?code="+e+"&id="+t.selectedKey,photoLicense:{...bo,scope:"Publisher-stated product-photo licence; not database licensing"},databaseLicenses:[{name:"ODbL",url:"https://opendatacommons.org/licenses/odbl/1-0/"},{name:"DbCL",url:"https://opendatacommons.org/licenses/dbcl/1-0/"}],author:s?{value:s,role:"publisher-reported uploader; independent authorship unverified",sourceField:Ir(i?.uploader)?a.raw+"/uploader":Ir(r?.uploader)?a.selected+"/uploader":a.catalogue+".contributor"}:null,notices:o,adaptationProvenance:{retainedSourceSelection:c,offmenuImageChanges:[],imageBytesFetched:!1,imageBytesChanged:!1,previousChanges:Ir(n?.changes)||null,statement:"Metadata selection/URL construction only; no new image adaptation performed."},packagingRights:{status:"not-universally-cleared",qualification:"Packaging artwork and other underlying rights remain separate; the photo licence alone does not establish all permissions for a proposed use."},placement:"accessible-photo-details",compactHeaderCredit:!1}}function Ec(e,t){if(!dp(e)||!Sc(e.sourceCode)||e.sourceCode!==t||e.license!==bo.name||e.licenseUrl!==bo.url)return null;let r=mp(e.url,e.sourceCode,"front");return!r||r.revision!==e.revision?null:{...vp(e.sourceCode,r,{catalogue:e}),retainedSourceUrl:e.url,retainedSourcePage:e.sourcePage,retainedPhotoLicensePage:e.licensePage,imageId:e.imageId,revision:e.revision,sourceKind:"retained-fixed-catalogue-metadata",snapshotMembership:"unverified; current publisher observation only"}}var xo=Object.freeze([Object.freeze({key:"flour-front-en-rev5",sourceCode:"0078742003986",imageId:"1",revision:"5",path:"/api/off-photos/flour-front-en-rev5.jpg",url:"https://images.openfoodfacts.org/images/products/007/874/200/3986/front_en.5.400.jpg",sourcePage:"https://world.openfoodfacts.org/product/0078742003986/all-purpose-flour-great-value",licensePage:"https://world.openfoodfacts.org/cgi/product_image.pl?code=0078742003986&id=front_en",contributor:"foodless",license:"CC BY-SA 3.0",licenseUrl:"https://creativecommons.org/licenses/by-sa/3.0/"}),Object.freeze({key:"nutella-front-en-rev879",sourceCode:"3017620422003",imageId:"180",revision:"879",path:"/api/off-photos/nutella-front-en-rev879.jpg",url:"https://images.openfoodfacts.org/images/products/301/762/042/2003/front_en.879.400.jpg",sourcePage:"https://world.openfoodfacts.org/cgi/product_image.pl?code=3017620422003&id=front_en",licensePage:"https://world.openfoodfacts.org/cgi/product_image.pl?code=3017620422003&id=front_en",contributor:"org-ferrero-france-commerciale",license:"CC BY-SA 3.0",licenseUrl:"https://creativecommons.org/licenses/by-sa/3.0/"})]);function Tc(e,t){return e?.schema!=="offmenu-identifier-observation/2"||e.sourceId!=="off"||e.namespace!=="barcode"||e.disposition!=="source-asserted"||typeof t?.referenceRecordId!="string"||t.sourceBinding?.sourceId!=="off"||t.sourceObservation?.source_id!=="off"||t.sourceObservation.lexical_value!==e.sourceLexicalValue||t.sourceObservation.release_id!==e.releaseId||t.sourceBinding.releaseId!==e.releaseId||(t.sourceObservation.source_record_id??null)!==(e.sourceRecordId??null)||t.sourceObservation.namespace!=="barcode"||t.sourceObservation.disposition!=="source-asserted"||t.observationKey?.databaseSha256!==e.databaseSha256||["run_id","input_id","record_ordinal","assertion_id"].some(r=>t.observationKey?.[r]!==e.observationKey?.[r]||t.sourceObservation[r]!==e.observationKey?.[r])||!t.records?.[0]?.data?.identifiers?.some(r=>r.system==="barcode"&&r.value===e.sourceLexicalValue)?[]:xo.filter(r=>r.sourceCode===e.sourceLexicalValue).map(r=>({sourceObservationReference:e,productRecordId:t.referenceRecordId,qualification:{state:"qualified",scope:"separately-observed-current-publisher-photo-for-exact-OFF-source-code"},role:"front",selectionRole:"selected-front",localAssetPath:r.path,sourceUrl:r.url,offlineAvailable:!1,provenance:{sourceId:"off",releaseId:null,imageId:r.imageId,revision:r.revision,sourceCode:r.sourceCode,sourcePage:r.sourcePage,evidenceObservedDate:"2026-10-25",relationship:"current-publisher-photo; retained-snapshot-image-membership-unverified",contributor:r.contributor,contributorRole:"publisher-reported-uploader; independent-authorship-unverified"},rights:{displayPermitted:!0,license:r.license,attribution:"Open Food Facts \xB7 contributor "+r.contributor,licenseUrl:r.licenseUrl,sourcePage:r.sourcePage,photoLicensePage:r.licensePage,changes:"Image bytes relayed unchanged; displayed to fit.",evidenceReference:"docs/off-publisher-photos.md#"+r.key,attributionDetails:Ec(r,e.sourceLexicalValue)}}))}var So="offmenu-product-visual-selector/1",_p=Object.freeze({light:"/scanner-balanced-final.svg",dark:"/scanner-balanced-final-dark.svg"}),ir=e=>e!==null&&typeof e=="object"&&!Array.isArray(e);function qn(e){return Array.isArray(e)?"["+e.map(qn).join(",")+"]":ir(e)?"{"+Object.keys(e).sort().map(t=>JSON.stringify(t)+":"+qn(e[t])).join(",")+"}":JSON.stringify(e)}function Mc(e,t){return ir(e)&&ir(t)&&e.schema==="offmenu-identifier-observation/2"&&qn(e)===qn(t)}function Ac(e,t){return typeof e=="string"&&Array.isArray(t)&&t.includes(e)&&/^\/[A-Za-z0-9/_-]+\.(?:svg|png|webp|jpe?g)$/.test(e)&&!e.includes("..")&&!e.includes("//")}function bp(e){try{let t=new URL(e);return t.protocol==="https:"&&t.hostname==="images.openfoodfacts.org"&&t.username===""&&t.password===""&&t.search===""&&t.hash===""&&/^\/images\/products\/(?:[0-9]{3}\/)+[0-9]+\/front_[a-z]{2}\.[1-9][0-9]*\.[1-9][0-9]*\.(?:jpg|jpeg|png|webp)$/.test(t.pathname)&&t.href===e}catch{return!1}}function xp(e,t,r){if(!ir(e)||!Mc(e.sourceObservationReference,t.sourceObservationReference)||e.qualification?.state!=="qualified"||e.rights?.displayPermitted!==!0||typeof t.selectedProductRecordId!="string"||!t.selectedProductRecordId||e.productRecordId!==t.selectedProductRecordId||e.role!=="front"||!ir(e.provenance)||!e.provenance.sourceId||!(e.provenance.releaseId||e.provenance.releaseId===null&&e.qualification.scope==="separately-observed-current-publisher-photo-for-exact-OFF-source-code"&&e.provenance.relationship==="current-publisher-photo; retained-snapshot-image-membership-unverified"&&/^\d{4}-\d{2}-\d{2}$/.test(e.provenance.evidenceObservedDate))||!e.provenance.imageId||!e.provenance.revision||!e.rights.license||!e.rights.attribution||!e.rights.evidenceReference)return null;let i=e.localAssetPath||e.sourceUrl;return typeof i!="string"||r.has(i)||!(e.localAssetPath?Ac(i,t.permittedLocalAssets):e.provenance.sourceId==="off"&&bp(i))||t.offline===!0&&(!e.localAssetPath||e.offlineAvailable!==!0)?null:{src:i,candidate:e}}function yo(e,t,r="category"){let i=r==="ingredient"?"ingredientMappings":r==="type"?"typeMappings":"categoryMappings";if(r!=="category"&&(!e.classificationEvidenceReference||r==="ingredient"&&(e.ingredientApplicability?.state!=="applicable"||!e.ingredientApplicability.evidenceReference)))return null;let n=(Array.isArray(e[i])?e[i]:[]).filter(g=>ir(g)&&Mc(g.sourceObservationReference,e.sourceObservationReference)&&g.status==="qualified"&&g.relation==="exact"&&typeof e.selectedProductRecordId=="string"&&g.productRecordId===e.selectedProductRecordId&&typeof g.conceptId=="string"&&g.conceptId&&typeof g.taxonomyVersion=="string"&&g.taxonomyVersion&&typeof g.crosswalkVersion=="string"&&g.crosswalkVersion&&ir(g.provenance)&&ir(g.originalSource)&&(r==="category"||typeof g.provenance.sourceId=="string"&&!!g.provenance.sourceId&&typeof g.provenance.pointer=="string"&&!!g.provenance.pointer)&&(typeof g.originalSource.term=="string"&&!!g.originalSource.term||typeof g.originalSource.code=="string"&&!!g.originalSource.code));if(new Set(n.map(g=>g.taxonomyVersion+"\0"+g.conceptId)).size!==1)return null;let[o]=n,s=(Array.isArray(e.canonicalConcepts)?e.canonicalConcepts:[]).filter(g=>ir(g)&&(r==="category"||g.kind===r)&&g.conceptId===o.conceptId&&g.taxonomyVersion===o.taxonomyVersion&&g.definitionStatus==="accepted"&&typeof g.preferredEnglishLabel=="string"&&g.preferredEnglishLabel.trim());if(s.length!==1)return null;let c=s[0],u=c.presentation;if(u?.status!=="approved"||r!=="category"&&!u.evidenceReference)return null;let l=r==="ingredient"?"Ingredient":r==="type"?"Type":"Category",d=r==="category"?"category-illustration":r+"-illustration",h={conceptId:c.conceptId,taxonomyVersion:c.taxonomyVersion,preferredEnglishLabel:c.preferredEnglishLabel,...r==="category"?{}:{kind:r,classificationEvidenceReference:e.classificationEvidenceReference,presentationEvidenceReference:u.evidenceReference},mappings:n.map(g=>({crosswalkVersion:g.crosswalkVersion,relation:g.relation,originalSource:g.originalSource,provenance:g.provenance}))};if(typeof u.emoji=="string"&&u.emoji.length>0&&Array.from(u.emoji).length<=16&&!/[\x00-\x1f\x7f<>]/.test(u.emoji))return{tier:d,kind:"emoji",text:u.emoji,alt:l+" illustration of "+c.preferredEnglishLabel+"; not a product photo",caption:l+" illustration, not product photo \xB7 emoji appearance varies by platform",evidence:h,rights:{presentation:"Unicode emoji; platform appearance varies"}};let m=u.localIconAssetPath;return Ac(m,e.permittedLocalAssets)&&!t.has(m)&&u.iconRights?.displayPermitted===!0&&u.iconRights?.evidenceReference&&(e.offline!==!0||u.offlineAvailable===!0)?{tier:d,kind:"image",src:m,alt:l+" illustration of "+c.preferredEnglishLabel+"; not a product photo",caption:l+" illustration, not product photo",evidence:h,rights:u.iconRights}:null}function Yn(e,{failedSources:t=[]}={}){if(!ir(e)||e.sourceObservationReference?.schema!=="offmenu-identifier-observation/2")throw new TypeError("Exact selected source observation required");let r=new Set(t),i=(e.photoCandidates||[]).map(s=>xp(s,e,r)).filter(Boolean),n=i.filter(s=>s.candidate.selectionRole==="selected-front"),a=n.length===1?n[0]:i.length===1?i[0]:null;if(a){let{src:s,candidate:c}=a,u=typeof e.sourceProductName=="string"&&e.sourceProductName.trim()?e.sourceProductName.trim():"selected source product",l=c.qualification.scope==="reviewed-retained-photo-for-explicit-native-source-assertion",d=c.qualification.scope==="separately-observed-current-publisher-photo-for-exact-OFF-source-code";return{tier:"product-photo",kind:"image",src:s,alt:l?"Photo from the explicitly selected source; product variant match unverified":d?"Current Open Food Facts photo for source code "+c.provenance.sourceCode+"; retained label "+u+"; snapshot image unverified":"Source product photo for "+u,caption:l?"Selected source photo":d?"Current publisher photo":"Source product photo",provenance:c.provenance,rights:c.rights,identity:{sourceObservationReference:e.sourceObservationReference},competingPhotoCount:i.length}}let o=yo(e,r,"ingredient")||yo(e,r,"type")||yo(e,r);return o||Kn(e,{failedSources:t})}function Kn(e={},{failedSources:t=[]}={}){let r=new Set(t),i=e.theme==="dark"?"dark":"light",n=_p[i];return r.has(n)?{tier:"app-fallback",kind:"text",text:"OffMenu",alt:"OffMenu app fallback; no eligible product photo or category illustration",caption:"Product photo unavailable \xB7 no qualified category illustration"}:{tier:"app-fallback",kind:"image",src:n,alt:"OffMenu app icon; no eligible product photo or category illustration",caption:"Product photo unavailable \xB7 no qualified category illustration",provenance:{asset:"Selected Balanced Final OffMenu app icon",theme:i}}}function wc(e,t,{failedSources:r=[]}={}){return!t||t.kind!=="image"||typeof t.src!="string"?Yn(e,{failedSources:r}):Yn(e,{failedSources:[...r,t.src]})}var Rc="offmenu-product-visual-association/1",yp=["schema","databaseSha256","runId","namespace","originalLexicalValue","sourceLexicalValue","symbology","matchType","equivalence","disposition","sourceId","releaseId","sourceRecordId","detailSelectionSha256"],Sp=["run_id","input_id","record_ordinal","assertion_id"];function Jn(e){try{return e?.schema!=="offmenu-identifier-observation/2"||!Xn(e,e.originalLexicalValue)?null:{...Object.fromEntries(yp.map(t=>[t,e[t]])),observationKey:Object.fromEntries(Sp.map(t=>[t,e.observationKey[t]]))}}catch{return null}}var Ep="offmenu-product-visual-classification/1",Eo=e=>typeof e=="string"&&e.length>0&&e.length<=2e3?e:null;function Tp(e,t){let r={state:"unresolved",evidenceReference:null,ingredientApplicability:{state:"unresolved",evidenceReference:null},ingredientMappings:[],typeMappings:[],canonicalConcepts:[],permittedLocalAssets:[]};if(!e)return r;let i=t?.classificationProjection;try{no(i)}catch{return r}let n=i.classification;if(JSON.stringify(Jn(i.sourceBinding.sourceObservationReference))!==JSON.stringify(e))return r;let a=e.sourceRecordId;if(typeof a!="string"||!a||i.sourceBinding.sourceRecordId!==a)return r;for(let[h,m]of[[t?.sourceObservation,"source_record_id"],[t?.sourceBinding,"identifierSourceRecordId"],[t?.sourceBinding,"sourceRecordId"]])if(h&&Object.hasOwn(h,m)&&h[m]!==a)return r;if(["unresolved","conflict"].includes(n.disposition))return{...r,state:n.disposition,semanticDisposition:n.disposition,semanticRelation:n.relation??null,ingredientApplicability:{state:n.ingredientApplicability,evidenceReference:null}};let o={...r,semanticDisposition:n.disposition,semanticRelation:n.relation??null,ingredientApplicability:{state:n.ingredientApplicability,evidenceReference:null}},s=i.visualClassification;if(!e||s?.schema!==Ep||s.productRecordId!==t.referenceRecordId||!s.productRecordId||s.qualification?.state!=="qualified"||!Eo(s.qualification.evidenceReference)||JSON.stringify(Jn(s.sourceObservationReference))!==JSON.stringify(e))return o;let c=s.ingredientApplicability?.state;if(c!==n.ingredientApplicability)return o;let u=["applicable","nonfood","not-applicable"].includes(c)&&Eo(s.ingredientApplicability.evidenceReference)?{state:c,evidenceReference:s.ingredientApplicability.evidenceReference}:r.ingredientApplicability,l=h=>(Array.isArray(s[h])?s[h]:[]).slice(0,100).filter(m=>m&&typeof m=="object").map(m=>({sourceObservationReference:Jn(m.sourceObservationReference),productRecordId:m.productRecordId,status:m.status,relation:m.relation,conceptId:m.conceptId,taxonomyVersion:m.taxonomyVersion,crosswalkVersion:m.crosswalkVersion,originalSource:{term:m.originalSource?.term,code:m.originalSource?.code,language:m.originalSource?.language},provenance:{sourceId:m.provenance?.sourceId,releaseId:m.provenance?.releaseId,pointer:m.provenance?.pointer}})),d=(Array.isArray(s.canonicalConcepts)?s.canonicalConcepts:[]).slice(0,100).filter(h=>h&&typeof h=="object").map(h=>({conceptId:h.conceptId,taxonomyVersion:h.taxonomyVersion,kind:h.kind,definitionStatus:h.definitionStatus,preferredEnglishLabel:h.preferredEnglishLabel,presentation:{status:h.presentation?.status,evidenceReference:h.presentation?.evidenceReference,emoji:h.presentation?.emoji,localIconAssetPath:h.presentation?.localIconAssetPath,offlineAvailable:h.presentation?.offlineAvailable,iconRights:{displayPermitted:h.presentation?.iconRights?.displayPermitted,evidenceReference:h.presentation?.iconRights?.evidenceReference}}}));return{state:"qualified",semanticDisposition:n.disposition,semanticRelation:n.relation,evidenceReference:s.qualification.evidenceReference,ingredientApplicability:u,ingredientMappings:l("ingredientMappings"),typeMappings:l("typeMappings"),canonicalConcepts:d,permittedLocalAssets:(Array.isArray(s.permittedLocalAssets)?s.permittedLocalAssets:[]).filter(Eo).slice(0,100)}}function Cc(e={}){let{reference:t=null,detail:r=null,name:i="",theme:n="light",offline:a=!1,sourcePhotoSelection:o=null}=e??{},s=o?xc(o,r,{origin:e?.origin??globalThis.location?.origin}):null,c=s?.state==="qualified",u=Jn(c?o.reference:t),l={theme:n,offline:a},d=c?{...s.assertion.binding,classificationProjection:s.assertion.classificationProjection}:r,h=Tp(u,d);if(!u)return{reference:null,input:null,appearance:l,classification:h,retained:s};let m=o?c?[s.candidate]:[]:Tc(u,r);return{reference:u,appearance:l,classification:h,retained:s,input:{sourceObservationReference:u,selectedProductRecordId:typeof d?.referenceRecordId=="string"?d.referenceRecordId:null,sourceProductName:c?"explicit independent source assertion":typeof i=="string"?i:"",theme:n,offline:a,photoCandidates:m,categoryMappings:[],ingredientMappings:h.ingredientMappings,typeMappings:h.typeMappings,canonicalConcepts:h.canonicalConcepts,ingredientApplicability:h.ingredientApplicability,classificationEvidenceReference:h.evidenceReference,permittedLocalAssets:[...xo.map(g=>g.path),...h.permittedLocalAssets,...c?[o.localAsset.path]:[]]}}}function Ic(e,t){return{schema:Rc,selectorVersion:So,sourceObservationReference:e.reference,productRecordId:t.tier==="product-photo"?e.input.selectedProductRecordId:null,sourcePhotoSelection:{state:e.retained?.state??"not-supplied",reasonCode:e.retained?.reasonCode??null,scope:e.retained?.state==="qualified"?"explicit-independent-native-source-assertion":null},associationState:t.tier==="product-photo"?"qualified-current-publisher-photo":["ingredient-illustration","type-illustration"].includes(t.tier)?"qualified-canonical-illustration":"unavailable",classification:{state:e.classification.state,semanticDisposition:e.classification.semanticDisposition??"unresolved",semanticRelation:e.classification.semanticRelation??null,evidenceReference:e.classification.evidenceReference,ingredientApplicability:e.classification.ingredientApplicability,selectedIcon:t.evidence?.kind?{kind:t.evidence.kind,conceptId:t.evidence.conceptId,taxonomyVersion:t.evidence.taxonomyVersion}:null,meaning:"Visual classification supplies no recipe composition, nutrition or physical-product equivalence."},visual:t,category:{label:"Category",state:"unidentified",display:"Not yet identified",sourceCategory:{state:"not-loaded-by-association",claims:null,evidence:null,reasonCode:"SOURCE_CATEGORY_CLAIMS_REQUIRE_SEPARATELY_BOUND_DETAIL_EVIDENCE"},normalizedCategory:{state:"unknown",conceptId:null,preferredEnglishLabel:null,crosswalk:null,reasonCode:"NO_ACCEPTED_BACKING_STORE_QUALIFIED_CATEGORY_MAPPING"}},ingredientMatch:{label:"Ingredient match",state:"unidentified",display:"Not yet identified",conceptId:null,composition:null,evidence:null,reasonCode:"NO_ACCEPTED_BACKING_STORE_QUALIFIED_INGREDIENT_MAPPING"},evidence:{associationVersion:Rc,selectorVersion:So,sourceReferenceState:e.reference?"valid-current-selected-contract":"unavailable",sourceCategoryAndMappings:"Separate source claims, normalized category and ingredient authority required; photo qualification supplies none."}}}function Nc(e={},{failedSources:t=[]}={}){let r=Cc(e),i=r.input?Yn(r.input,{failedSources:t}):Kn(r.appearance,{failedSources:t});return Ic(r,i)}function Pc(e,t,{failedSources:r=[]}={}){let i=Cc(e),n=i.input?wc(i.input,t?.visual,{failedSources:r}):Kn(i.appearance,{failedSources:t?.visual?.kind==="image"?[...r,t.visual.src]:r});return Ic(i,n)}function To(e,t,{onChange:r=()=>{}}={}){let i=e.ownerDocument,n=0,a=null,o=[],s=null,c=(l,d)=>{let h=i.createElement(l);return h.textContent=d,h};function u(l,d,h=!1,m=null){let g=l??{theme:i.documentElement?.dataset.theme==="dark"?"dark":"light"},_=m?Pc(g,m,{failedSources:o}):Nc(g,{failedSources:o}),f=l?_.visual:{..._.visual,alt:"OffMenu app icon; product photo unavailable"};if(s=f,e.replaceChildren(),t.replaceChildren(),e.dataset.visualTier=f.tier,f.kind==="image"){let p=i.createElement("img");p.alt=f.alt,p.referrerPolicy="no-referrer",f.tier==="app-fallback"&&(p.dataset.offmenuLogo=""),p.onerror=()=>{d!==n||p!==e.firstChild||(l?(o=[...new Set([...o,f.src])],u(l,d,!0,_)):(e.replaceChildren(c("span","OffMenu")),s={...f,kind:"text",text:"OffMenu"},r(s)))},p.src=f.src,e.append(p)}else e.append(c("span",f.text));if(t.append(c("p",f.caption)),f.tier==="product-photo"){let p=c("details",""),R=f.rights.attributionDetails;p.append(c("summary","Photo source and licence"),c("p",f.rights.attribution)),p.append(c("p",f.provenance?.associationScope==="explicit-independent-native-source-assertion"?"Photo from the selected source. The product variant and older-snapshot image membership are unverified.":"Current publisher photo; membership in the retained snapshot is unverified.")),f.provenance?.associationScope==="explicit-independent-native-source-assertion"&&(p.append(c("p","Photo author and notices were not captured in the selected metadata; their absence is not established.")),p.append(c("p","Image retrieved "+f.provenance.retrievedAt+"; metadata release "+f.provenance.metadataRelease+".")));for(let[y,A]of[["Product on Open Food Facts",R?.productUrl||f.rights.sourcePage],["Photo source",f.rights.sourcePage],["Photo licence",f.rights.photoLicensePage],[f.rights.license,f.rights.licenseUrl]]){let O=c("a",y);O.href=A,O.target="_blank",O.rel="noopener noreferrer",p.append(O)}for(let y of R?.notices||[])p.append(c("p",y.field+": "+y.text));p.append(c("p",f.rights.changes)),R?.packagingRights?.qualification&&p.append(c("p",R.packagingRights.qualification)),t.append(p)}return h&&r(f),f}return{show({reference:l=null,detail:d=null,entryId:h=null,generation:m=null,name:g="",theme:_="light",offline:f=!1,sourcePhotoSelection:p=null}={}){let R=l&&Xn(l,l.originalLexicalValue),y=JSON.stringify([h,m,l,d?.referenceRecordId??null,p,d?.currentOutputUse]);y!==a&&(o=[],a=y);let A=++n;return u(R||p?{reference:R?l:null,detail:d,name:g,theme:_,offline:f,sourcePhotoSelection:p}:null,A)},current:()=>s,destroy(){n++,e.replaceChildren(),t.replaceChildren()}}}var Ou="180",Mp=0,Oc=1,Ap=2,Lu=1,wp=2,Er=3,Vr=0,Rt=1,Tr=2,kr=0,ki=1,Lc=2,Uc=3,Dc=4,Rp=5,ri=100,Cp=101,Ip=102,Np=103,Pp=104,Op=200,Lp=201,Up=202,Dp=203,ns=204,as=205,Fp=206,kp=207,Bp=208,Vp=209,zp=210,Hp=211,Gp=212,Wp=213,jp=214,os=0,ss=1,ls=2,Vi=3,cs=4,us=5,ds=6,hs=7,Uu=0,Xp=1,qp=2,Br=0,Yp=1,Kp=2,Jp=3,Zp=4,$p=5,Qp=6,ef=7,Du=300,zi=301,Hi=302,ps=303,fs=304,Na=306,ms=1e3,ni=1001,gs=1002,Kt=1003,tf=1004,Zn=1005,ar=1006,Mo=1007,ai=1008,lr=1009,Fu=1010,ku=1011,un=1012,Ks=1013,si=1014,Mr=1015,mn=1016,Js=1017,Zs=1018,dn=1020,Bu=35902,Vu=35899,zu=1021,Hu=1022,qt=1023,hn=1026,pn=1027,Gu=1028,$s=1029,Wu=1030,Qs=1031,el=1033,xa=33776,ya=33777,Sa=33778,Ea=33779,vs=35840,_s=35841,bs=35842,xs=35843,ys=36196,Ss=37492,Es=37496,Ts=37808,Ms=37809,As=37810,ws=37811,Rs=37812,Cs=37813,Is=37814,Ns=37815,Ps=37816,Os=37817,Ls=37818,Us=37819,Ds=37820,Fs=37821,ks=36492,Bs=36494,Vs=36495,zs=36283,Hs=36284,Gs=36285,Ws=36286,wa=2300,js=2301,Ao=2302,Fc=2400,kc=2401,Bc=2402,rf=3200,nf=3201,ju=0,af=1,Fr="",Ft="srgb",Gi="srgb-linear",Ra="linear",Je="srgb",yi=7680,Vc=519,of=512,sf=513,lf=514,Xu=515,cf=516,uf=517,df=518,hf=519,zc=35044,Hc="300 es",or=2e3,Ca=2001,ji=class{addEventListener(e,t){this._listeners===void 0&&(this._listeners={});let r=this._listeners;r[e]===void 0&&(r[e]=[]),r[e].indexOf(t)===-1&&r[e].push(t)}hasEventListener(e,t){let r=this._listeners;return r===void 0?!1:r[e]!==void 0&&r[e].indexOf(t)!==-1}removeEventListener(e,t){let r=this._listeners;if(r===void 0)return;let i=r[e];if(i!==void 0){let n=i.indexOf(t);n!==-1&&i.splice(n,1)}}dispatchEvent(e){let t=this._listeners;if(t===void 0)return;let r=t[e.type];if(r!==void 0){e.target=this;let i=r.slice(0);for(let n=0,a=i.length;n<a;n++)i[n].call(this,e);e.target=null}}},xt=["00","01","02","03","04","05","06","07","08","09","0a","0b","0c","0d","0e","0f","10","11","12","13","14","15","16","17","18","19","1a","1b","1c","1d","1e","1f","20","21","22","23","24","25","26","27","28","29","2a","2b","2c","2d","2e","2f","30","31","32","33","34","35","36","37","38","39","3a","3b","3c","3d","3e","3f","40","41","42","43","44","45","46","47","48","49","4a","4b","4c","4d","4e","4f","50","51","52","53","54","55","56","57","58","59","5a","5b","5c","5d","5e","5f","60","61","62","63","64","65","66","67","68","69","6a","6b","6c","6d","6e","6f","70","71","72","73","74","75","76","77","78","79","7a","7b","7c","7d","7e","7f","80","81","82","83","84","85","86","87","88","89","8a","8b","8c","8d","8e","8f","90","91","92","93","94","95","96","97","98","99","9a","9b","9c","9d","9e","9f","a0","a1","a2","a3","a4","a5","a6","a7","a8","a9","aa","ab","ac","ad","ae","af","b0","b1","b2","b3","b4","b5","b6","b7","b8","b9","ba","bb","bc","bd","be","bf","c0","c1","c2","c3","c4","c5","c6","c7","c8","c9","ca","cb","cc","cd","ce","cf","d0","d1","d2","d3","d4","d5","d6","d7","d8","d9","da","db","dc","dd","de","df","e0","e1","e2","e3","e4","e5","e6","e7","e8","e9","ea","eb","ec","ed","ee","ef","f0","f1","f2","f3","f4","f5","f6","f7","f8","f9","fa","fb","fc","fd","fe","ff"],wo=Math.PI/180,Xs=180/Math.PI;function gn(){let e=Math.random()*4294967295|0,t=Math.random()*4294967295|0,r=Math.random()*4294967295|0,i=Math.random()*4294967295|0;return(xt[e&255]+xt[e>>8&255]+xt[e>>16&255]+xt[e>>24&255]+"-"+xt[t&255]+xt[t>>8&255]+"-"+xt[t>>16&15|64]+xt[t>>24&255]+"-"+xt[r&63|128]+xt[r>>8&255]+"-"+xt[r>>16&255]+xt[r>>24&255]+xt[i&255]+xt[i>>8&255]+xt[i>>16&255]+xt[i>>24&255]).toLowerCase()}function Ge(e,t,r){return Math.max(t,Math.min(r,e))}function pf(e,t){return(e%t+t)%t}function Ro(e,t,r){return(1-r)*e+r*t}function rn(e,t){switch(t.constructor){case Float32Array:return e;case Uint32Array:return e/4294967295;case Uint16Array:return e/65535;case Uint8Array:return e/255;case Int32Array:return Math.max(e/2147483647,-1);case Int16Array:return Math.max(e/32767,-1);case Int8Array:return Math.max(e/127,-1);default:throw new Error("Invalid component type.")}}function wt(e,t){switch(t.constructor){case Float32Array:return e;case Uint32Array:return Math.round(e*4294967295);case Uint16Array:return Math.round(e*65535);case Uint8Array:return Math.round(e*255);case Int32Array:return Math.round(e*2147483647);case Int16Array:return Math.round(e*32767);case Int8Array:return Math.round(e*127);default:throw new Error("Invalid component type.")}}var Ye=class qu{constructor(t=0,r=0){qu.prototype.isVector2=!0,this.x=t,this.y=r}get width(){return this.x}set width(t){this.x=t}get height(){return this.y}set height(t){this.y=t}set(t,r){return this.x=t,this.y=r,this}setScalar(t){return this.x=t,this.y=t,this}setX(t){return this.x=t,this}setY(t){return this.y=t,this}setComponent(t,r){switch(t){case 0:this.x=r;break;case 1:this.y=r;break;default:throw new Error("index is out of range: "+t)}return this}getComponent(t){switch(t){case 0:return this.x;case 1:return this.y;default:throw new Error("index is out of range: "+t)}}clone(){return new this.constructor(this.x,this.y)}copy(t){return this.x=t.x,this.y=t.y,this}add(t){return this.x+=t.x,this.y+=t.y,this}addScalar(t){return this.x+=t,this.y+=t,this}addVectors(t,r){return this.x=t.x+r.x,this.y=t.y+r.y,this}addScaledVector(t,r){return this.x+=t.x*r,this.y+=t.y*r,this}sub(t){return this.x-=t.x,this.y-=t.y,this}subScalar(t){return this.x-=t,this.y-=t,this}subVectors(t,r){return this.x=t.x-r.x,this.y=t.y-r.y,this}multiply(t){return this.x*=t.x,this.y*=t.y,this}multiplyScalar(t){return this.x*=t,this.y*=t,this}divide(t){return this.x/=t.x,this.y/=t.y,this}divideScalar(t){return this.multiplyScalar(1/t)}applyMatrix3(t){let r=this.x,i=this.y,n=t.elements;return this.x=n[0]*r+n[3]*i+n[6],this.y=n[1]*r+n[4]*i+n[7],this}min(t){return this.x=Math.min(this.x,t.x),this.y=Math.min(this.y,t.y),this}max(t){return this.x=Math.max(this.x,t.x),this.y=Math.max(this.y,t.y),this}clamp(t,r){return this.x=Ge(this.x,t.x,r.x),this.y=Ge(this.y,t.y,r.y),this}clampScalar(t,r){return this.x=Ge(this.x,t,r),this.y=Ge(this.y,t,r),this}clampLength(t,r){let i=this.length();return this.divideScalar(i||1).multiplyScalar(Ge(i,t,r))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this}negate(){return this.x=-this.x,this.y=-this.y,this}dot(t){return this.x*t.x+this.y*t.y}cross(t){return this.x*t.y-this.y*t.x}lengthSq(){return this.x*this.x+this.y*this.y}length(){return Math.sqrt(this.x*this.x+this.y*this.y)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)}normalize(){return this.divideScalar(this.length()||1)}angle(){return Math.atan2(-this.y,-this.x)+Math.PI}angleTo(t){let r=Math.sqrt(this.lengthSq()*t.lengthSq());if(r===0)return Math.PI/2;let i=this.dot(t)/r;return Math.acos(Ge(i,-1,1))}distanceTo(t){return Math.sqrt(this.distanceToSquared(t))}distanceToSquared(t){let r=this.x-t.x,i=this.y-t.y;return r*r+i*i}manhattanDistanceTo(t){return Math.abs(this.x-t.x)+Math.abs(this.y-t.y)}setLength(t){return this.normalize().multiplyScalar(t)}lerp(t,r){return this.x+=(t.x-this.x)*r,this.y+=(t.y-this.y)*r,this}lerpVectors(t,r,i){return this.x=t.x+(r.x-t.x)*i,this.y=t.y+(r.y-t.y)*i,this}equals(t){return t.x===this.x&&t.y===this.y}fromArray(t,r=0){return this.x=t[r],this.y=t[r+1],this}toArray(t=[],r=0){return t[r]=this.x,t[r+1]=this.y,t}fromBufferAttribute(t,r){return this.x=t.getX(r),this.y=t.getY(r),this}rotateAround(t,r){let i=Math.cos(r),n=Math.sin(r),a=this.x-t.x,o=this.y-t.y;return this.x=a*i-o*n+t.x,this.y=a*n+o*i+t.y,this}random(){return this.x=Math.random(),this.y=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y}},Xi=class{constructor(e=0,t=0,r=0,i=1){this.isQuaternion=!0,this._x=e,this._y=t,this._z=r,this._w=i}static slerpFlat(e,t,r,i,n,a,o){let s=r[i+0],c=r[i+1],u=r[i+2],l=r[i+3],d=n[a+0],h=n[a+1],m=n[a+2],g=n[a+3];if(o===0){e[t+0]=s,e[t+1]=c,e[t+2]=u,e[t+3]=l;return}if(o===1){e[t+0]=d,e[t+1]=h,e[t+2]=m,e[t+3]=g;return}if(l!==g||s!==d||c!==h||u!==m){let _=1-o,f=s*d+c*h+u*m+l*g,p=f>=0?1:-1,R=1-f*f;if(R>Number.EPSILON){let A=Math.sqrt(R),O=Math.atan2(A,f*p);_=Math.sin(_*O)/A,o=Math.sin(o*O)/A}let y=o*p;if(s=s*_+d*y,c=c*_+h*y,u=u*_+m*y,l=l*_+g*y,_===1-o){let A=1/Math.sqrt(s*s+c*c+u*u+l*l);s*=A,c*=A,u*=A,l*=A}}e[t]=s,e[t+1]=c,e[t+2]=u,e[t+3]=l}static multiplyQuaternionsFlat(e,t,r,i,n,a){let o=r[i],s=r[i+1],c=r[i+2],u=r[i+3],l=n[a],d=n[a+1],h=n[a+2],m=n[a+3];return e[t]=o*m+u*l+s*h-c*d,e[t+1]=s*m+u*d+c*l-o*h,e[t+2]=c*m+u*h+o*d-s*l,e[t+3]=u*m-o*l-s*d-c*h,e}get x(){return this._x}set x(e){this._x=e,this._onChangeCallback()}get y(){return this._y}set y(e){this._y=e,this._onChangeCallback()}get z(){return this._z}set z(e){this._z=e,this._onChangeCallback()}get w(){return this._w}set w(e){this._w=e,this._onChangeCallback()}set(e,t,r,i){return this._x=e,this._y=t,this._z=r,this._w=i,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._w)}copy(e){return this._x=e.x,this._y=e.y,this._z=e.z,this._w=e.w,this._onChangeCallback(),this}setFromEuler(e,t=!0){let r=e._x,i=e._y,n=e._z,a=e._order,o=Math.cos,s=Math.sin,c=o(r/2),u=o(i/2),l=o(n/2),d=s(r/2),h=s(i/2),m=s(n/2);switch(a){case"XYZ":this._x=d*u*l+c*h*m,this._y=c*h*l-d*u*m,this._z=c*u*m+d*h*l,this._w=c*u*l-d*h*m;break;case"YXZ":this._x=d*u*l+c*h*m,this._y=c*h*l-d*u*m,this._z=c*u*m-d*h*l,this._w=c*u*l+d*h*m;break;case"ZXY":this._x=d*u*l-c*h*m,this._y=c*h*l+d*u*m,this._z=c*u*m+d*h*l,this._w=c*u*l-d*h*m;break;case"ZYX":this._x=d*u*l-c*h*m,this._y=c*h*l+d*u*m,this._z=c*u*m-d*h*l,this._w=c*u*l+d*h*m;break;case"YZX":this._x=d*u*l+c*h*m,this._y=c*h*l+d*u*m,this._z=c*u*m-d*h*l,this._w=c*u*l-d*h*m;break;case"XZY":this._x=d*u*l-c*h*m,this._y=c*h*l-d*u*m,this._z=c*u*m+d*h*l,this._w=c*u*l+d*h*m;break;default:console.warn("THREE.Quaternion: .setFromEuler() encountered an unknown order: "+a)}return t===!0&&this._onChangeCallback(),this}setFromAxisAngle(e,t){let r=t/2,i=Math.sin(r);return this._x=e.x*i,this._y=e.y*i,this._z=e.z*i,this._w=Math.cos(r),this._onChangeCallback(),this}setFromRotationMatrix(e){let t=e.elements,r=t[0],i=t[4],n=t[8],a=t[1],o=t[5],s=t[9],c=t[2],u=t[6],l=t[10],d=r+o+l;if(d>0){let h=.5/Math.sqrt(d+1);this._w=.25/h,this._x=(u-s)*h,this._y=(n-c)*h,this._z=(a-i)*h}else if(r>o&&r>l){let h=2*Math.sqrt(1+r-o-l);this._w=(u-s)/h,this._x=.25*h,this._y=(i+a)/h,this._z=(n+c)/h}else if(o>l){let h=2*Math.sqrt(1+o-r-l);this._w=(n-c)/h,this._x=(i+a)/h,this._y=.25*h,this._z=(s+u)/h}else{let h=2*Math.sqrt(1+l-r-o);this._w=(a-i)/h,this._x=(n+c)/h,this._y=(s+u)/h,this._z=.25*h}return this._onChangeCallback(),this}setFromUnitVectors(e,t){let r=e.dot(t)+1;return r<1e-8?(r=0,Math.abs(e.x)>Math.abs(e.z)?(this._x=-e.y,this._y=e.x,this._z=0,this._w=r):(this._x=0,this._y=-e.z,this._z=e.y,this._w=r)):(this._x=e.y*t.z-e.z*t.y,this._y=e.z*t.x-e.x*t.z,this._z=e.x*t.y-e.y*t.x,this._w=r),this.normalize()}angleTo(e){return 2*Math.acos(Math.abs(Ge(this.dot(e),-1,1)))}rotateTowards(e,t){let r=this.angleTo(e);if(r===0)return this;let i=Math.min(1,t/r);return this.slerp(e,i),this}identity(){return this.set(0,0,0,1)}invert(){return this.conjugate()}conjugate(){return this._x*=-1,this._y*=-1,this._z*=-1,this._onChangeCallback(),this}dot(e){return this._x*e._x+this._y*e._y+this._z*e._z+this._w*e._w}lengthSq(){return this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w}length(){return Math.sqrt(this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w)}normalize(){let e=this.length();return e===0?(this._x=0,this._y=0,this._z=0,this._w=1):(e=1/e,this._x=this._x*e,this._y=this._y*e,this._z=this._z*e,this._w=this._w*e),this._onChangeCallback(),this}multiply(e){return this.multiplyQuaternions(this,e)}premultiply(e){return this.multiplyQuaternions(e,this)}multiplyQuaternions(e,t){let r=e._x,i=e._y,n=e._z,a=e._w,o=t._x,s=t._y,c=t._z,u=t._w;return this._x=r*u+a*o+i*c-n*s,this._y=i*u+a*s+n*o-r*c,this._z=n*u+a*c+r*s-i*o,this._w=a*u-r*o-i*s-n*c,this._onChangeCallback(),this}slerp(e,t){if(t===0)return this;if(t===1)return this.copy(e);let r=this._x,i=this._y,n=this._z,a=this._w,o=a*e._w+r*e._x+i*e._y+n*e._z;if(o<0?(this._w=-e._w,this._x=-e._x,this._y=-e._y,this._z=-e._z,o=-o):this.copy(e),o>=1)return this._w=a,this._x=r,this._y=i,this._z=n,this;let s=1-o*o;if(s<=Number.EPSILON){let h=1-t;return this._w=h*a+t*this._w,this._x=h*r+t*this._x,this._y=h*i+t*this._y,this._z=h*n+t*this._z,this.normalize(),this}let c=Math.sqrt(s),u=Math.atan2(c,o),l=Math.sin((1-t)*u)/c,d=Math.sin(t*u)/c;return this._w=a*l+this._w*d,this._x=r*l+this._x*d,this._y=i*l+this._y*d,this._z=n*l+this._z*d,this._onChangeCallback(),this}slerpQuaternions(e,t,r){return this.copy(e).slerp(t,r)}random(){let e=2*Math.PI*Math.random(),t=2*Math.PI*Math.random(),r=Math.random(),i=Math.sqrt(1-r),n=Math.sqrt(r);return this.set(i*Math.sin(e),i*Math.cos(e),n*Math.sin(t),n*Math.cos(t))}equals(e){return e._x===this._x&&e._y===this._y&&e._z===this._z&&e._w===this._w}fromArray(e,t=0){return this._x=e[t],this._y=e[t+1],this._z=e[t+2],this._w=e[t+3],this._onChangeCallback(),this}toArray(e=[],t=0){return e[t]=this._x,e[t+1]=this._y,e[t+2]=this._z,e[t+3]=this._w,e}fromBufferAttribute(e,t){return this._x=e.getX(t),this._y=e.getY(t),this._z=e.getZ(t),this._w=e.getW(t),this._onChangeCallback(),this}toJSON(){return this.toArray()}_onChange(e){return this._onChangeCallback=e,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._w}},F=class Yu{constructor(t=0,r=0,i=0){Yu.prototype.isVector3=!0,this.x=t,this.y=r,this.z=i}set(t,r,i){return i===void 0&&(i=this.z),this.x=t,this.y=r,this.z=i,this}setScalar(t){return this.x=t,this.y=t,this.z=t,this}setX(t){return this.x=t,this}setY(t){return this.y=t,this}setZ(t){return this.z=t,this}setComponent(t,r){switch(t){case 0:this.x=r;break;case 1:this.y=r;break;case 2:this.z=r;break;default:throw new Error("index is out of range: "+t)}return this}getComponent(t){switch(t){case 0:return this.x;case 1:return this.y;case 2:return this.z;default:throw new Error("index is out of range: "+t)}}clone(){return new this.constructor(this.x,this.y,this.z)}copy(t){return this.x=t.x,this.y=t.y,this.z=t.z,this}add(t){return this.x+=t.x,this.y+=t.y,this.z+=t.z,this}addScalar(t){return this.x+=t,this.y+=t,this.z+=t,this}addVectors(t,r){return this.x=t.x+r.x,this.y=t.y+r.y,this.z=t.z+r.z,this}addScaledVector(t,r){return this.x+=t.x*r,this.y+=t.y*r,this.z+=t.z*r,this}sub(t){return this.x-=t.x,this.y-=t.y,this.z-=t.z,this}subScalar(t){return this.x-=t,this.y-=t,this.z-=t,this}subVectors(t,r){return this.x=t.x-r.x,this.y=t.y-r.y,this.z=t.z-r.z,this}multiply(t){return this.x*=t.x,this.y*=t.y,this.z*=t.z,this}multiplyScalar(t){return this.x*=t,this.y*=t,this.z*=t,this}multiplyVectors(t,r){return this.x=t.x*r.x,this.y=t.y*r.y,this.z=t.z*r.z,this}applyEuler(t){return this.applyQuaternion(Gc.setFromEuler(t))}applyAxisAngle(t,r){return this.applyQuaternion(Gc.setFromAxisAngle(t,r))}applyMatrix3(t){let r=this.x,i=this.y,n=this.z,a=t.elements;return this.x=a[0]*r+a[3]*i+a[6]*n,this.y=a[1]*r+a[4]*i+a[7]*n,this.z=a[2]*r+a[5]*i+a[8]*n,this}applyNormalMatrix(t){return this.applyMatrix3(t).normalize()}applyMatrix4(t){let r=this.x,i=this.y,n=this.z,a=t.elements,o=1/(a[3]*r+a[7]*i+a[11]*n+a[15]);return this.x=(a[0]*r+a[4]*i+a[8]*n+a[12])*o,this.y=(a[1]*r+a[5]*i+a[9]*n+a[13])*o,this.z=(a[2]*r+a[6]*i+a[10]*n+a[14])*o,this}applyQuaternion(t){let r=this.x,i=this.y,n=this.z,a=t.x,o=t.y,s=t.z,c=t.w,u=2*(o*n-s*i),l=2*(s*r-a*n),d=2*(a*i-o*r);return this.x=r+c*u+o*d-s*l,this.y=i+c*l+s*u-a*d,this.z=n+c*d+a*l-o*u,this}project(t){return this.applyMatrix4(t.matrixWorldInverse).applyMatrix4(t.projectionMatrix)}unproject(t){return this.applyMatrix4(t.projectionMatrixInverse).applyMatrix4(t.matrixWorld)}transformDirection(t){let r=this.x,i=this.y,n=this.z,a=t.elements;return this.x=a[0]*r+a[4]*i+a[8]*n,this.y=a[1]*r+a[5]*i+a[9]*n,this.z=a[2]*r+a[6]*i+a[10]*n,this.normalize()}divide(t){return this.x/=t.x,this.y/=t.y,this.z/=t.z,this}divideScalar(t){return this.multiplyScalar(1/t)}min(t){return this.x=Math.min(this.x,t.x),this.y=Math.min(this.y,t.y),this.z=Math.min(this.z,t.z),this}max(t){return this.x=Math.max(this.x,t.x),this.y=Math.max(this.y,t.y),this.z=Math.max(this.z,t.z),this}clamp(t,r){return this.x=Ge(this.x,t.x,r.x),this.y=Ge(this.y,t.y,r.y),this.z=Ge(this.z,t.z,r.z),this}clampScalar(t,r){return this.x=Ge(this.x,t,r),this.y=Ge(this.y,t,r),this.z=Ge(this.z,t,r),this}clampLength(t,r){let i=this.length();return this.divideScalar(i||1).multiplyScalar(Ge(i,t,r))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this}dot(t){return this.x*t.x+this.y*t.y+this.z*t.z}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)}normalize(){return this.divideScalar(this.length()||1)}setLength(t){return this.normalize().multiplyScalar(t)}lerp(t,r){return this.x+=(t.x-this.x)*r,this.y+=(t.y-this.y)*r,this.z+=(t.z-this.z)*r,this}lerpVectors(t,r,i){return this.x=t.x+(r.x-t.x)*i,this.y=t.y+(r.y-t.y)*i,this.z=t.z+(r.z-t.z)*i,this}cross(t){return this.crossVectors(this,t)}crossVectors(t,r){let i=t.x,n=t.y,a=t.z,o=r.x,s=r.y,c=r.z;return this.x=n*c-a*s,this.y=a*o-i*c,this.z=i*s-n*o,this}projectOnVector(t){let r=t.lengthSq();if(r===0)return this.set(0,0,0);let i=t.dot(this)/r;return this.copy(t).multiplyScalar(i)}projectOnPlane(t){return Co.copy(this).projectOnVector(t),this.sub(Co)}reflect(t){return this.sub(Co.copy(t).multiplyScalar(2*this.dot(t)))}angleTo(t){let r=Math.sqrt(this.lengthSq()*t.lengthSq());if(r===0)return Math.PI/2;let i=this.dot(t)/r;return Math.acos(Ge(i,-1,1))}distanceTo(t){return Math.sqrt(this.distanceToSquared(t))}distanceToSquared(t){let r=this.x-t.x,i=this.y-t.y,n=this.z-t.z;return r*r+i*i+n*n}manhattanDistanceTo(t){return Math.abs(this.x-t.x)+Math.abs(this.y-t.y)+Math.abs(this.z-t.z)}setFromSpherical(t){return this.setFromSphericalCoords(t.radius,t.phi,t.theta)}setFromSphericalCoords(t,r,i){let n=Math.sin(r)*t;return this.x=n*Math.sin(i),this.y=Math.cos(r)*t,this.z=n*Math.cos(i),this}setFromCylindrical(t){return this.setFromCylindricalCoords(t.radius,t.theta,t.y)}setFromCylindricalCoords(t,r,i){return this.x=t*Math.sin(r),this.y=i,this.z=t*Math.cos(r),this}setFromMatrixPosition(t){let r=t.elements;return this.x=r[12],this.y=r[13],this.z=r[14],this}setFromMatrixScale(t){let r=this.setFromMatrixColumn(t,0).length(),i=this.setFromMatrixColumn(t,1).length(),n=this.setFromMatrixColumn(t,2).length();return this.x=r,this.y=i,this.z=n,this}setFromMatrixColumn(t,r){return this.fromArray(t.elements,r*4)}setFromMatrix3Column(t,r){return this.fromArray(t.elements,r*3)}setFromEuler(t){return this.x=t._x,this.y=t._y,this.z=t._z,this}setFromColor(t){return this.x=t.r,this.y=t.g,this.z=t.b,this}equals(t){return t.x===this.x&&t.y===this.y&&t.z===this.z}fromArray(t,r=0){return this.x=t[r],this.y=t[r+1],this.z=t[r+2],this}toArray(t=[],r=0){return t[r]=this.x,t[r+1]=this.y,t[r+2]=this.z,t}fromBufferAttribute(t,r){return this.x=t.getX(r),this.y=t.getY(r),this.z=t.getZ(r),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this}randomDirection(){let t=Math.random()*Math.PI*2,r=Math.random()*2-1,i=Math.sqrt(1-r*r);return this.x=i*Math.cos(t),this.y=r,this.z=i*Math.sin(t),this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z}},Co=new F,Gc=new Xi,Be=class Ku{constructor(t,r,i,n,a,o,s,c,u){Ku.prototype.isMatrix3=!0,this.elements=[1,0,0,0,1,0,0,0,1],t!==void 0&&this.set(t,r,i,n,a,o,s,c,u)}set(t,r,i,n,a,o,s,c,u){let l=this.elements;return l[0]=t,l[1]=n,l[2]=s,l[3]=r,l[4]=a,l[5]=c,l[6]=i,l[7]=o,l[8]=u,this}identity(){return this.set(1,0,0,0,1,0,0,0,1),this}copy(t){let r=this.elements,i=t.elements;return r[0]=i[0],r[1]=i[1],r[2]=i[2],r[3]=i[3],r[4]=i[4],r[5]=i[5],r[6]=i[6],r[7]=i[7],r[8]=i[8],this}extractBasis(t,r,i){return t.setFromMatrix3Column(this,0),r.setFromMatrix3Column(this,1),i.setFromMatrix3Column(this,2),this}setFromMatrix4(t){let r=t.elements;return this.set(r[0],r[4],r[8],r[1],r[5],r[9],r[2],r[6],r[10]),this}multiply(t){return this.multiplyMatrices(this,t)}premultiply(t){return this.multiplyMatrices(t,this)}multiplyMatrices(t,r){let i=t.elements,n=r.elements,a=this.elements,o=i[0],s=i[3],c=i[6],u=i[1],l=i[4],d=i[7],h=i[2],m=i[5],g=i[8],_=n[0],f=n[3],p=n[6],R=n[1],y=n[4],A=n[7],O=n[2],I=n[5],C=n[8];return a[0]=o*_+s*R+c*O,a[3]=o*f+s*y+c*I,a[6]=o*p+s*A+c*C,a[1]=u*_+l*R+d*O,a[4]=u*f+l*y+d*I,a[7]=u*p+l*A+d*C,a[2]=h*_+m*R+g*O,a[5]=h*f+m*y+g*I,a[8]=h*p+m*A+g*C,this}multiplyScalar(t){let r=this.elements;return r[0]*=t,r[3]*=t,r[6]*=t,r[1]*=t,r[4]*=t,r[7]*=t,r[2]*=t,r[5]*=t,r[8]*=t,this}determinant(){let t=this.elements,r=t[0],i=t[1],n=t[2],a=t[3],o=t[4],s=t[5],c=t[6],u=t[7],l=t[8];return r*o*l-r*s*u-i*a*l+i*s*c+n*a*u-n*o*c}invert(){let t=this.elements,r=t[0],i=t[1],n=t[2],a=t[3],o=t[4],s=t[5],c=t[6],u=t[7],l=t[8],d=l*o-s*u,h=s*c-l*a,m=u*a-o*c,g=r*d+i*h+n*m;if(g===0)return this.set(0,0,0,0,0,0,0,0,0);let _=1/g;return t[0]=d*_,t[1]=(n*u-l*i)*_,t[2]=(s*i-n*o)*_,t[3]=h*_,t[4]=(l*r-n*c)*_,t[5]=(n*a-s*r)*_,t[6]=m*_,t[7]=(i*c-u*r)*_,t[8]=(o*r-i*a)*_,this}transpose(){let t,r=this.elements;return t=r[1],r[1]=r[3],r[3]=t,t=r[2],r[2]=r[6],r[6]=t,t=r[5],r[5]=r[7],r[7]=t,this}getNormalMatrix(t){return this.setFromMatrix4(t).invert().transpose()}transposeIntoArray(t){let r=this.elements;return t[0]=r[0],t[1]=r[3],t[2]=r[6],t[3]=r[1],t[4]=r[4],t[5]=r[7],t[6]=r[2],t[7]=r[5],t[8]=r[8],this}setUvTransform(t,r,i,n,a,o,s){let c=Math.cos(a),u=Math.sin(a);return this.set(i*c,i*u,-i*(c*o+u*s)+o+t,-n*u,n*c,-n*(-u*o+c*s)+s+r,0,0,1),this}scale(t,r){return this.premultiply(Io.makeScale(t,r)),this}rotate(t){return this.premultiply(Io.makeRotation(-t)),this}translate(t,r){return this.premultiply(Io.makeTranslation(t,r)),this}makeTranslation(t,r){return t.isVector2?this.set(1,0,t.x,0,1,t.y,0,0,1):this.set(1,0,t,0,1,r,0,0,1),this}makeRotation(t){let r=Math.cos(t),i=Math.sin(t);return this.set(r,-i,0,i,r,0,0,0,1),this}makeScale(t,r){return this.set(t,0,0,0,r,0,0,0,1),this}equals(t){let r=this.elements,i=t.elements;for(let n=0;n<9;n++)if(r[n]!==i[n])return!1;return!0}fromArray(t,r=0){for(let i=0;i<9;i++)this.elements[i]=t[i+r];return this}toArray(t=[],r=0){let i=this.elements;return t[r]=i[0],t[r+1]=i[1],t[r+2]=i[2],t[r+3]=i[3],t[r+4]=i[4],t[r+5]=i[5],t[r+6]=i[6],t[r+7]=i[7],t[r+8]=i[8],t}clone(){return new this.constructor().fromArray(this.elements)}},Io=new Be;function Ju(e){for(let t=e.length-1;t>=0;--t)if(e[t]>=65535)return!0;return!1}function Ia(e){return document.createElementNS("http://www.w3.org/1999/xhtml",e)}function ff(){let e=Ia("canvas");return e.style.display="block",e}var Wc={};function fn(e){e in Wc||(Wc[e]=!0,console.warn(e))}function mf(e,t,r){return new Promise(function(i,n){function a(){switch(e.clientWaitSync(t,e.SYNC_FLUSH_COMMANDS_BIT,0)){case e.WAIT_FAILED:n();break;case e.TIMEOUT_EXPIRED:setTimeout(a,r);break;default:i()}}setTimeout(a,r)})}var jc=new Be().set(.4123908,.3575843,.1804808,.212639,.7151687,.0721923,.0193308,.1191948,.9505322),Xc=new Be().set(3.2409699,-1.5373832,-.4986108,-.9692436,1.8759675,.0415551,.0556301,-.203977,1.0569715);function gf(){let e={enabled:!0,workingColorSpace:Gi,spaces:{},convert:function(n,a,o){return this.enabled===!1||a===o||!a||!o||(this.spaces[a].transfer===Je&&(n.r=Ar(n.r),n.g=Ar(n.g),n.b=Ar(n.b)),this.spaces[a].primaries!==this.spaces[o].primaries&&(n.applyMatrix3(this.spaces[a].toXYZ),n.applyMatrix3(this.spaces[o].fromXYZ)),this.spaces[o].transfer===Je&&(n.r=Bi(n.r),n.g=Bi(n.g),n.b=Bi(n.b))),n},workingToColorSpace:function(n,a){return this.convert(n,this.workingColorSpace,a)},colorSpaceToWorking:function(n,a){return this.convert(n,a,this.workingColorSpace)},getPrimaries:function(n){return this.spaces[n].primaries},getTransfer:function(n){return n===Fr?Ra:this.spaces[n].transfer},getToneMappingMode:function(n){return this.spaces[n].outputColorSpaceConfig.toneMappingMode||"standard"},getLuminanceCoefficients:function(n,a=this.workingColorSpace){return n.fromArray(this.spaces[a].luminanceCoefficients)},define:function(n){Object.assign(this.spaces,n)},_getMatrix:function(n,a,o){return n.copy(this.spaces[a].toXYZ).multiply(this.spaces[o].fromXYZ)},_getDrawingBufferColorSpace:function(n){return this.spaces[n].outputColorSpaceConfig.drawingBufferColorSpace},_getUnpackColorSpace:function(n=this.workingColorSpace){return this.spaces[n].workingColorSpaceConfig.unpackColorSpace},fromWorkingColorSpace:function(n,a){return fn("THREE.ColorManagement: .fromWorkingColorSpace() has been renamed to .workingToColorSpace()."),e.workingToColorSpace(n,a)},toWorkingColorSpace:function(n,a){return fn("THREE.ColorManagement: .toWorkingColorSpace() has been renamed to .colorSpaceToWorking()."),e.colorSpaceToWorking(n,a)}},t=[.64,.33,.3,.6,.15,.06],r=[.2126,.7152,.0722],i=[.3127,.329];return e.define({[Gi]:{primaries:t,whitePoint:i,transfer:Ra,toXYZ:jc,fromXYZ:Xc,luminanceCoefficients:r,workingColorSpaceConfig:{unpackColorSpace:Ft},outputColorSpaceConfig:{drawingBufferColorSpace:Ft}},[Ft]:{primaries:t,whitePoint:i,transfer:Je,toXYZ:jc,fromXYZ:Xc,luminanceCoefficients:r,outputColorSpaceConfig:{drawingBufferColorSpace:Ft}}}),e}var Xe=gf();function Ar(e){return e<.04045?e*.0773993808:Math.pow(e*.9478672986+.0521327014,2.4)}function Bi(e){return e<.0031308?e*12.92:1.055*Math.pow(e,.41666)-.055}var Si,vf=class{static getDataURL(e,t="image/png"){if(/^data:/i.test(e.src)||typeof HTMLCanvasElement>"u")return e.src;let r;if(e instanceof HTMLCanvasElement)r=e;else{Si===void 0&&(Si=Ia("canvas")),Si.width=e.width,Si.height=e.height;let i=Si.getContext("2d");e instanceof ImageData?i.putImageData(e,0,0):i.drawImage(e,0,0,e.width,e.height),r=Si}return r.toDataURL(t)}static sRGBToLinear(e){if(typeof HTMLImageElement<"u"&&e instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&e instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&e instanceof ImageBitmap){let t=Ia("canvas");t.width=e.width,t.height=e.height;let r=t.getContext("2d");r.drawImage(e,0,0,e.width,e.height);let i=r.getImageData(0,0,e.width,e.height),n=i.data;for(let a=0;a<n.length;a++)n[a]=Ar(n[a]/255)*255;return r.putImageData(i,0,0),t}else if(e.data){let t=e.data.slice(0);for(let r=0;r<t.length;r++)t instanceof Uint8Array||t instanceof Uint8ClampedArray?t[r]=Math.floor(Ar(t[r]/255)*255):t[r]=Ar(t[r]);return{data:t,width:e.width,height:e.height}}else return console.warn("THREE.ImageUtils.sRGBToLinear(): Unsupported image type. No color space conversion applied."),e}},_f=0,tl=class{constructor(e=null){this.isSource=!0,Object.defineProperty(this,"id",{value:_f++}),this.uuid=gn(),this.data=e,this.dataReady=!0,this.version=0}getSize(e){let t=this.data;return typeof HTMLVideoElement<"u"&&t instanceof HTMLVideoElement?e.set(t.videoWidth,t.videoHeight,0):t instanceof VideoFrame?e.set(t.displayHeight,t.displayWidth,0):t!==null?e.set(t.width,t.height,t.depth||0):e.set(0,0,0),e}set needsUpdate(e){e===!0&&this.version++}toJSON(e){let t=e===void 0||typeof e=="string";if(!t&&e.images[this.uuid]!==void 0)return e.images[this.uuid];let r={uuid:this.uuid,url:""},i=this.data;if(i!==null){let n;if(Array.isArray(i)){n=[];for(let a=0,o=i.length;a<o;a++)i[a].isDataTexture?n.push(No(i[a].image)):n.push(No(i[a]))}else n=No(i);r.url=n}return t||(e.images[this.uuid]=r),r}};function No(e){return typeof HTMLImageElement<"u"&&e instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&e instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&e instanceof ImageBitmap?vf.getDataURL(e):e.data?{data:Array.from(e.data),width:e.width,height:e.height,type:e.data.constructor.name}:(console.warn("THREE.Texture: Unable to serialize Texture."),{})}var bf=0,Po=new F,cr=class Ta extends ji{constructor(t=Ta.DEFAULT_IMAGE,r=Ta.DEFAULT_MAPPING,i=ni,n=ni,a=ar,o=ai,s=qt,c=lr,u=Ta.DEFAULT_ANISOTROPY,l=Fr){super(),this.isTexture=!0,Object.defineProperty(this,"id",{value:bf++}),this.uuid=gn(),this.name="",this.source=new tl(t),this.mipmaps=[],this.mapping=r,this.channel=0,this.wrapS=i,this.wrapT=n,this.magFilter=a,this.minFilter=o,this.anisotropy=u,this.format=s,this.internalFormat=null,this.type=c,this.offset=new Ye(0,0),this.repeat=new Ye(1,1),this.center=new Ye(0,0),this.rotation=0,this.matrixAutoUpdate=!0,this.matrix=new Be,this.generateMipmaps=!0,this.premultiplyAlpha=!1,this.flipY=!0,this.unpackAlignment=4,this.colorSpace=l,this.userData={},this.updateRanges=[],this.version=0,this.onUpdate=null,this.renderTarget=null,this.isRenderTargetTexture=!1,this.isArrayTexture=!!(t&&t.depth&&t.depth>1),this.pmremVersion=0}get width(){return this.source.getSize(Po).x}get height(){return this.source.getSize(Po).y}get depth(){return this.source.getSize(Po).z}get image(){return this.source.data}set image(t=null){this.source.data=t}updateMatrix(){this.matrix.setUvTransform(this.offset.x,this.offset.y,this.repeat.x,this.repeat.y,this.rotation,this.center.x,this.center.y)}addUpdateRange(t,r){this.updateRanges.push({start:t,count:r})}clearUpdateRanges(){this.updateRanges.length=0}clone(){return new this.constructor().copy(this)}copy(t){return this.name=t.name,this.source=t.source,this.mipmaps=t.mipmaps.slice(0),this.mapping=t.mapping,this.channel=t.channel,this.wrapS=t.wrapS,this.wrapT=t.wrapT,this.magFilter=t.magFilter,this.minFilter=t.minFilter,this.anisotropy=t.anisotropy,this.format=t.format,this.internalFormat=t.internalFormat,this.type=t.type,this.offset.copy(t.offset),this.repeat.copy(t.repeat),this.center.copy(t.center),this.rotation=t.rotation,this.matrixAutoUpdate=t.matrixAutoUpdate,this.matrix.copy(t.matrix),this.generateMipmaps=t.generateMipmaps,this.premultiplyAlpha=t.premultiplyAlpha,this.flipY=t.flipY,this.unpackAlignment=t.unpackAlignment,this.colorSpace=t.colorSpace,this.renderTarget=t.renderTarget,this.isRenderTargetTexture=t.isRenderTargetTexture,this.isArrayTexture=t.isArrayTexture,this.userData=JSON.parse(JSON.stringify(t.userData)),this.needsUpdate=!0,this}setValues(t){for(let r in t){let i=t[r];if(i===void 0){console.warn(`THREE.Texture.setValues(): parameter '${r}' has value of undefined.`);continue}let n=this[r];if(n===void 0){console.warn(`THREE.Texture.setValues(): property '${r}' does not exist.`);continue}n&&i&&n.isVector2&&i.isVector2||n&&i&&n.isVector3&&i.isVector3||n&&i&&n.isMatrix3&&i.isMatrix3?n.copy(i):this[r]=i}}toJSON(t){let r=t===void 0||typeof t=="string";if(!r&&t.textures[this.uuid]!==void 0)return t.textures[this.uuid];let i={metadata:{version:4.7,type:"Texture",generator:"Texture.toJSON"},uuid:this.uuid,name:this.name,image:this.source.toJSON(t).uuid,mapping:this.mapping,channel:this.channel,repeat:[this.repeat.x,this.repeat.y],offset:[this.offset.x,this.offset.y],center:[this.center.x,this.center.y],rotation:this.rotation,wrap:[this.wrapS,this.wrapT],format:this.format,internalFormat:this.internalFormat,type:this.type,colorSpace:this.colorSpace,minFilter:this.minFilter,magFilter:this.magFilter,anisotropy:this.anisotropy,flipY:this.flipY,generateMipmaps:this.generateMipmaps,premultiplyAlpha:this.premultiplyAlpha,unpackAlignment:this.unpackAlignment};return Object.keys(this.userData).length>0&&(i.userData=this.userData),r||(t.textures[this.uuid]=i),i}dispose(){this.dispatchEvent({type:"dispose"})}transformUv(t){if(this.mapping!==Du)return t;if(t.applyMatrix3(this.matrix),t.x<0||t.x>1)switch(this.wrapS){case ms:t.x=t.x-Math.floor(t.x);break;case ni:t.x=t.x<0?0:1;break;case gs:Math.abs(Math.floor(t.x)%2)===1?t.x=Math.ceil(t.x)-t.x:t.x=t.x-Math.floor(t.x);break}if(t.y<0||t.y>1)switch(this.wrapT){case ms:t.y=t.y-Math.floor(t.y);break;case ni:t.y=t.y<0?0:1;break;case gs:Math.abs(Math.floor(t.y)%2)===1?t.y=Math.ceil(t.y)-t.y:t.y=t.y-Math.floor(t.y);break}return this.flipY&&(t.y=1-t.y),t}set needsUpdate(t){t===!0&&(this.version++,this.source.needsUpdate=!0)}set needsPMREMUpdate(t){t===!0&&this.pmremVersion++}};cr.DEFAULT_IMAGE=null;cr.DEFAULT_MAPPING=Du;cr.DEFAULT_ANISOTROPY=1;var lt=class Zu{constructor(t=0,r=0,i=0,n=1){Zu.prototype.isVector4=!0,this.x=t,this.y=r,this.z=i,this.w=n}get width(){return this.z}set width(t){this.z=t}get height(){return this.w}set height(t){this.w=t}set(t,r,i,n){return this.x=t,this.y=r,this.z=i,this.w=n,this}setScalar(t){return this.x=t,this.y=t,this.z=t,this.w=t,this}setX(t){return this.x=t,this}setY(t){return this.y=t,this}setZ(t){return this.z=t,this}setW(t){return this.w=t,this}setComponent(t,r){switch(t){case 0:this.x=r;break;case 1:this.y=r;break;case 2:this.z=r;break;case 3:this.w=r;break;default:throw new Error("index is out of range: "+t)}return this}getComponent(t){switch(t){case 0:return this.x;case 1:return this.y;case 2:return this.z;case 3:return this.w;default:throw new Error("index is out of range: "+t)}}clone(){return new this.constructor(this.x,this.y,this.z,this.w)}copy(t){return this.x=t.x,this.y=t.y,this.z=t.z,this.w=t.w!==void 0?t.w:1,this}add(t){return this.x+=t.x,this.y+=t.y,this.z+=t.z,this.w+=t.w,this}addScalar(t){return this.x+=t,this.y+=t,this.z+=t,this.w+=t,this}addVectors(t,r){return this.x=t.x+r.x,this.y=t.y+r.y,this.z=t.z+r.z,this.w=t.w+r.w,this}addScaledVector(t,r){return this.x+=t.x*r,this.y+=t.y*r,this.z+=t.z*r,this.w+=t.w*r,this}sub(t){return this.x-=t.x,this.y-=t.y,this.z-=t.z,this.w-=t.w,this}subScalar(t){return this.x-=t,this.y-=t,this.z-=t,this.w-=t,this}subVectors(t,r){return this.x=t.x-r.x,this.y=t.y-r.y,this.z=t.z-r.z,this.w=t.w-r.w,this}multiply(t){return this.x*=t.x,this.y*=t.y,this.z*=t.z,this.w*=t.w,this}multiplyScalar(t){return this.x*=t,this.y*=t,this.z*=t,this.w*=t,this}applyMatrix4(t){let r=this.x,i=this.y,n=this.z,a=this.w,o=t.elements;return this.x=o[0]*r+o[4]*i+o[8]*n+o[12]*a,this.y=o[1]*r+o[5]*i+o[9]*n+o[13]*a,this.z=o[2]*r+o[6]*i+o[10]*n+o[14]*a,this.w=o[3]*r+o[7]*i+o[11]*n+o[15]*a,this}divide(t){return this.x/=t.x,this.y/=t.y,this.z/=t.z,this.w/=t.w,this}divideScalar(t){return this.multiplyScalar(1/t)}setAxisAngleFromQuaternion(t){this.w=2*Math.acos(t.w);let r=Math.sqrt(1-t.w*t.w);return r<1e-4?(this.x=1,this.y=0,this.z=0):(this.x=t.x/r,this.y=t.y/r,this.z=t.z/r),this}setAxisAngleFromRotationMatrix(t){let r,i,n,a,o=t.elements,s=o[0],c=o[4],u=o[8],l=o[1],d=o[5],h=o[9],m=o[2],g=o[6],_=o[10];if(Math.abs(c-l)<.01&&Math.abs(u-m)<.01&&Math.abs(h-g)<.01){if(Math.abs(c+l)<.1&&Math.abs(u+m)<.1&&Math.abs(h+g)<.1&&Math.abs(s+d+_-3)<.1)return this.set(1,0,0,0),this;r=Math.PI;let p=(s+1)/2,R=(d+1)/2,y=(_+1)/2,A=(c+l)/4,O=(u+m)/4,I=(h+g)/4;return p>R&&p>y?p<.01?(i=0,n=.707106781,a=.707106781):(i=Math.sqrt(p),n=A/i,a=O/i):R>y?R<.01?(i=.707106781,n=0,a=.707106781):(n=Math.sqrt(R),i=A/n,a=I/n):y<.01?(i=.707106781,n=.707106781,a=0):(a=Math.sqrt(y),i=O/a,n=I/a),this.set(i,n,a,r),this}let f=Math.sqrt((g-h)*(g-h)+(u-m)*(u-m)+(l-c)*(l-c));return Math.abs(f)<.001&&(f=1),this.x=(g-h)/f,this.y=(u-m)/f,this.z=(l-c)/f,this.w=Math.acos((s+d+_-1)/2),this}setFromMatrixPosition(t){let r=t.elements;return this.x=r[12],this.y=r[13],this.z=r[14],this.w=r[15],this}min(t){return this.x=Math.min(this.x,t.x),this.y=Math.min(this.y,t.y),this.z=Math.min(this.z,t.z),this.w=Math.min(this.w,t.w),this}max(t){return this.x=Math.max(this.x,t.x),this.y=Math.max(this.y,t.y),this.z=Math.max(this.z,t.z),this.w=Math.max(this.w,t.w),this}clamp(t,r){return this.x=Ge(this.x,t.x,r.x),this.y=Ge(this.y,t.y,r.y),this.z=Ge(this.z,t.z,r.z),this.w=Ge(this.w,t.w,r.w),this}clampScalar(t,r){return this.x=Ge(this.x,t,r),this.y=Ge(this.y,t,r),this.z=Ge(this.z,t,r),this.w=Ge(this.w,t,r),this}clampLength(t,r){let i=this.length();return this.divideScalar(i||1).multiplyScalar(Ge(i,t,r))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this.w=Math.floor(this.w),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this.w=Math.ceil(this.w),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this.w=Math.round(this.w),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this.w=Math.trunc(this.w),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this.w=-this.w,this}dot(t){return this.x*t.x+this.y*t.y+this.z*t.z+this.w*t.w}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)+Math.abs(this.w)}normalize(){return this.divideScalar(this.length()||1)}setLength(t){return this.normalize().multiplyScalar(t)}lerp(t,r){return this.x+=(t.x-this.x)*r,this.y+=(t.y-this.y)*r,this.z+=(t.z-this.z)*r,this.w+=(t.w-this.w)*r,this}lerpVectors(t,r,i){return this.x=t.x+(r.x-t.x)*i,this.y=t.y+(r.y-t.y)*i,this.z=t.z+(r.z-t.z)*i,this.w=t.w+(r.w-t.w)*i,this}equals(t){return t.x===this.x&&t.y===this.y&&t.z===this.z&&t.w===this.w}fromArray(t,r=0){return this.x=t[r],this.y=t[r+1],this.z=t[r+2],this.w=t[r+3],this}toArray(t=[],r=0){return t[r]=this.x,t[r+1]=this.y,t[r+2]=this.z,t[r+3]=this.w,t}fromBufferAttribute(t,r){return this.x=t.getX(r),this.y=t.getY(r),this.z=t.getZ(r),this.w=t.getW(r),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this.w=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z,yield this.w}},xf=class extends ji{constructor(e=1,t=1,r={}){super(),r=Object.assign({generateMipmaps:!1,internalFormat:null,minFilter:ar,depthBuffer:!0,stencilBuffer:!1,resolveDepthBuffer:!0,resolveStencilBuffer:!0,depthTexture:null,samples:0,count:1,depth:1,multiview:!1},r),this.isRenderTarget=!0,this.width=e,this.height=t,this.depth=r.depth,this.scissor=new lt(0,0,e,t),this.scissorTest=!1,this.viewport=new lt(0,0,e,t);let i={width:e,height:t,depth:r.depth},n=new cr(i);this.textures=[];let a=r.count;for(let o=0;o<a;o++)this.textures[o]=n.clone(),this.textures[o].isRenderTargetTexture=!0,this.textures[o].renderTarget=this;this._setTextureOptions(r),this.depthBuffer=r.depthBuffer,this.stencilBuffer=r.stencilBuffer,this.resolveDepthBuffer=r.resolveDepthBuffer,this.resolveStencilBuffer=r.resolveStencilBuffer,this._depthTexture=null,this.depthTexture=r.depthTexture,this.samples=r.samples,this.multiview=r.multiview}_setTextureOptions(e={}){let t={minFilter:ar,generateMipmaps:!1,flipY:!1,internalFormat:null};e.mapping!==void 0&&(t.mapping=e.mapping),e.wrapS!==void 0&&(t.wrapS=e.wrapS),e.wrapT!==void 0&&(t.wrapT=e.wrapT),e.wrapR!==void 0&&(t.wrapR=e.wrapR),e.magFilter!==void 0&&(t.magFilter=e.magFilter),e.minFilter!==void 0&&(t.minFilter=e.minFilter),e.format!==void 0&&(t.format=e.format),e.type!==void 0&&(t.type=e.type),e.anisotropy!==void 0&&(t.anisotropy=e.anisotropy),e.colorSpace!==void 0&&(t.colorSpace=e.colorSpace),e.flipY!==void 0&&(t.flipY=e.flipY),e.generateMipmaps!==void 0&&(t.generateMipmaps=e.generateMipmaps),e.internalFormat!==void 0&&(t.internalFormat=e.internalFormat);for(let r=0;r<this.textures.length;r++)this.textures[r].setValues(t)}get texture(){return this.textures[0]}set texture(e){this.textures[0]=e}set depthTexture(e){this._depthTexture!==null&&(this._depthTexture.renderTarget=null),e!==null&&(e.renderTarget=this),this._depthTexture=e}get depthTexture(){return this._depthTexture}setSize(e,t,r=1){if(this.width!==e||this.height!==t||this.depth!==r){this.width=e,this.height=t,this.depth=r;for(let i=0,n=this.textures.length;i<n;i++)this.textures[i].image.width=e,this.textures[i].image.height=t,this.textures[i].image.depth=r,this.textures[i].isArrayTexture=this.textures[i].image.depth>1;this.dispose()}this.viewport.set(0,0,e,t),this.scissor.set(0,0,e,t)}clone(){return new this.constructor().copy(this)}copy(e){this.width=e.width,this.height=e.height,this.depth=e.depth,this.scissor.copy(e.scissor),this.scissorTest=e.scissorTest,this.viewport.copy(e.viewport),this.textures.length=0;for(let t=0,r=e.textures.length;t<r;t++){this.textures[t]=e.textures[t].clone(),this.textures[t].isRenderTargetTexture=!0,this.textures[t].renderTarget=this;let i=Object.assign({},e.textures[t].image);this.textures[t].source=new tl(i)}return this.depthBuffer=e.depthBuffer,this.stencilBuffer=e.stencilBuffer,this.resolveDepthBuffer=e.resolveDepthBuffer,this.resolveStencilBuffer=e.resolveStencilBuffer,e.depthTexture!==null&&(this.depthTexture=e.depthTexture.clone()),this.samples=e.samples,this}dispose(){this.dispatchEvent({type:"dispose"})}},li=class extends xf{constructor(e=1,t=1,r={}){super(e,t,r),this.isWebGLRenderTarget=!0}},$u=class extends cr{constructor(e=null,t=1,r=1,i=1){super(null),this.isDataArrayTexture=!0,this.image={data:e,width:t,height:r,depth:i},this.magFilter=Kt,this.minFilter=Kt,this.wrapR=ni,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1,this.layerUpdates=new Set}addLayerUpdate(e){this.layerUpdates.add(e)}clearLayerUpdates(){this.layerUpdates.clear()}},yf=class extends cr{constructor(e=null,t=1,r=1,i=1){super(null),this.isData3DTexture=!0,this.image={data:e,width:t,height:r,depth:i},this.magFilter=Kt,this.minFilter=Kt,this.wrapR=ni,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1}},vn=class{constructor(e=new F(1/0,1/0,1/0),t=new F(-1/0,-1/0,-1/0)){this.isBox3=!0,this.min=e,this.max=t}set(e,t){return this.min.copy(e),this.max.copy(t),this}setFromArray(e){this.makeEmpty();for(let t=0,r=e.length;t<r;t+=3)this.expandByPoint(Gt.fromArray(e,t));return this}setFromBufferAttribute(e){this.makeEmpty();for(let t=0,r=e.count;t<r;t++)this.expandByPoint(Gt.fromBufferAttribute(e,t));return this}setFromPoints(e){this.makeEmpty();for(let t=0,r=e.length;t<r;t++)this.expandByPoint(e[t]);return this}setFromCenterAndSize(e,t){let r=Gt.copy(t).multiplyScalar(.5);return this.min.copy(e).sub(r),this.max.copy(e).add(r),this}setFromObject(e,t=!1){return this.makeEmpty(),this.expandByObject(e,t)}clone(){return new this.constructor().copy(this)}copy(e){return this.min.copy(e.min),this.max.copy(e.max),this}makeEmpty(){return this.min.x=this.min.y=this.min.z=1/0,this.max.x=this.max.y=this.max.z=-1/0,this}isEmpty(){return this.max.x<this.min.x||this.max.y<this.min.y||this.max.z<this.min.z}getCenter(e){return this.isEmpty()?e.set(0,0,0):e.addVectors(this.min,this.max).multiplyScalar(.5)}getSize(e){return this.isEmpty()?e.set(0,0,0):e.subVectors(this.max,this.min)}expandByPoint(e){return this.min.min(e),this.max.max(e),this}expandByVector(e){return this.min.sub(e),this.max.add(e),this}expandByScalar(e){return this.min.addScalar(-e),this.max.addScalar(e),this}expandByObject(e,t=!1){e.updateWorldMatrix(!1,!1);let r=e.geometry;if(r!==void 0){let n=r.getAttribute("position");if(t===!0&&n!==void 0&&e.isInstancedMesh!==!0)for(let a=0,o=n.count;a<o;a++)e.isMesh===!0?e.getVertexPosition(a,Gt):Gt.fromBufferAttribute(n,a),Gt.applyMatrix4(e.matrixWorld),this.expandByPoint(Gt);else e.boundingBox!==void 0?(e.boundingBox===null&&e.computeBoundingBox(),$n.copy(e.boundingBox)):(r.boundingBox===null&&r.computeBoundingBox(),$n.copy(r.boundingBox)),$n.applyMatrix4(e.matrixWorld),this.union($n)}let i=e.children;for(let n=0,a=i.length;n<a;n++)this.expandByObject(i[n],t);return this}containsPoint(e){return e.x>=this.min.x&&e.x<=this.max.x&&e.y>=this.min.y&&e.y<=this.max.y&&e.z>=this.min.z&&e.z<=this.max.z}containsBox(e){return this.min.x<=e.min.x&&e.max.x<=this.max.x&&this.min.y<=e.min.y&&e.max.y<=this.max.y&&this.min.z<=e.min.z&&e.max.z<=this.max.z}getParameter(e,t){return t.set((e.x-this.min.x)/(this.max.x-this.min.x),(e.y-this.min.y)/(this.max.y-this.min.y),(e.z-this.min.z)/(this.max.z-this.min.z))}intersectsBox(e){return e.max.x>=this.min.x&&e.min.x<=this.max.x&&e.max.y>=this.min.y&&e.min.y<=this.max.y&&e.max.z>=this.min.z&&e.min.z<=this.max.z}intersectsSphere(e){return this.clampPoint(e.center,Gt),Gt.distanceToSquared(e.center)<=e.radius*e.radius}intersectsPlane(e){let t,r;return e.normal.x>0?(t=e.normal.x*this.min.x,r=e.normal.x*this.max.x):(t=e.normal.x*this.max.x,r=e.normal.x*this.min.x),e.normal.y>0?(t+=e.normal.y*this.min.y,r+=e.normal.y*this.max.y):(t+=e.normal.y*this.max.y,r+=e.normal.y*this.min.y),e.normal.z>0?(t+=e.normal.z*this.min.z,r+=e.normal.z*this.max.z):(t+=e.normal.z*this.max.z,r+=e.normal.z*this.min.z),t<=-e.constant&&r>=-e.constant}intersectsTriangle(e){if(this.isEmpty())return!1;this.getCenter(nn),Qn.subVectors(this.max,nn),Ei.subVectors(e.a,nn),Ti.subVectors(e.b,nn),Mi.subVectors(e.c,nn),Nr.subVectors(Ti,Ei),Pr.subVectors(Mi,Ti),Yr.subVectors(Ei,Mi);let t=[0,-Nr.z,Nr.y,0,-Pr.z,Pr.y,0,-Yr.z,Yr.y,Nr.z,0,-Nr.x,Pr.z,0,-Pr.x,Yr.z,0,-Yr.x,-Nr.y,Nr.x,0,-Pr.y,Pr.x,0,-Yr.y,Yr.x,0];return!Oo(t,Ei,Ti,Mi,Qn)||(t=[1,0,0,0,1,0,0,0,1],!Oo(t,Ei,Ti,Mi,Qn))?!1:(ea.crossVectors(Nr,Pr),t=[ea.x,ea.y,ea.z],Oo(t,Ei,Ti,Mi,Qn))}clampPoint(e,t){return t.copy(e).clamp(this.min,this.max)}distanceToPoint(e){return this.clampPoint(e,Gt).distanceTo(e)}getBoundingSphere(e){return this.isEmpty()?e.makeEmpty():(this.getCenter(e.center),e.radius=this.getSize(Gt).length()*.5),e}intersect(e){return this.min.max(e.min),this.max.min(e.max),this.isEmpty()&&this.makeEmpty(),this}union(e){return this.min.min(e.min),this.max.max(e.max),this}applyMatrix4(e){return this.isEmpty()?this:(_r[0].set(this.min.x,this.min.y,this.min.z).applyMatrix4(e),_r[1].set(this.min.x,this.min.y,this.max.z).applyMatrix4(e),_r[2].set(this.min.x,this.max.y,this.min.z).applyMatrix4(e),_r[3].set(this.min.x,this.max.y,this.max.z).applyMatrix4(e),_r[4].set(this.max.x,this.min.y,this.min.z).applyMatrix4(e),_r[5].set(this.max.x,this.min.y,this.max.z).applyMatrix4(e),_r[6].set(this.max.x,this.max.y,this.min.z).applyMatrix4(e),_r[7].set(this.max.x,this.max.y,this.max.z).applyMatrix4(e),this.setFromPoints(_r),this)}translate(e){return this.min.add(e),this.max.add(e),this}equals(e){return e.min.equals(this.min)&&e.max.equals(this.max)}toJSON(){return{min:this.min.toArray(),max:this.max.toArray()}}fromJSON(e){return this.min.fromArray(e.min),this.max.fromArray(e.max),this}},_r=[new F,new F,new F,new F,new F,new F,new F,new F],Gt=new F,$n=new vn,Ei=new F,Ti=new F,Mi=new F,Nr=new F,Pr=new F,Yr=new F,nn=new F,Qn=new F,ea=new F,Kr=new F;function Oo(e,t,r,i,n){for(let a=0,o=e.length-3;a<=o;a+=3){Kr.fromArray(e,a);let s=n.x*Math.abs(Kr.x)+n.y*Math.abs(Kr.y)+n.z*Math.abs(Kr.z),c=t.dot(Kr),u=r.dot(Kr),l=i.dot(Kr);if(Math.max(-Math.max(c,u,l),Math.min(c,u,l))>s)return!1}return!0}var Sf=new vn,an=new F,Lo=new F,rl=class{constructor(e=new F,t=-1){this.isSphere=!0,this.center=e,this.radius=t}set(e,t){return this.center.copy(e),this.radius=t,this}setFromPoints(e,t){let r=this.center;t!==void 0?r.copy(t):Sf.setFromPoints(e).getCenter(r);let i=0;for(let n=0,a=e.length;n<a;n++)i=Math.max(i,r.distanceToSquared(e[n]));return this.radius=Math.sqrt(i),this}copy(e){return this.center.copy(e.center),this.radius=e.radius,this}isEmpty(){return this.radius<0}makeEmpty(){return this.center.set(0,0,0),this.radius=-1,this}containsPoint(e){return e.distanceToSquared(this.center)<=this.radius*this.radius}distanceToPoint(e){return e.distanceTo(this.center)-this.radius}intersectsSphere(e){let t=this.radius+e.radius;return e.center.distanceToSquared(this.center)<=t*t}intersectsBox(e){return e.intersectsSphere(this)}intersectsPlane(e){return Math.abs(e.distanceToPoint(this.center))<=this.radius}clampPoint(e,t){let r=this.center.distanceToSquared(e);return t.copy(e),r>this.radius*this.radius&&(t.sub(this.center).normalize(),t.multiplyScalar(this.radius).add(this.center)),t}getBoundingBox(e){return this.isEmpty()?(e.makeEmpty(),e):(e.set(this.center,this.center),e.expandByScalar(this.radius),e)}applyMatrix4(e){return this.center.applyMatrix4(e),this.radius=this.radius*e.getMaxScaleOnAxis(),this}translate(e){return this.center.add(e),this}expandByPoint(e){if(this.isEmpty())return this.center.copy(e),this.radius=0,this;an.subVectors(e,this.center);let t=an.lengthSq();if(t>this.radius*this.radius){let r=Math.sqrt(t),i=(r-this.radius)*.5;this.center.addScaledVector(an,i/r),this.radius+=i}return this}union(e){return e.isEmpty()?this:this.isEmpty()?(this.copy(e),this):(this.center.equals(e.center)===!0?this.radius=Math.max(this.radius,e.radius):(Lo.subVectors(e.center,this.center).setLength(e.radius),this.expandByPoint(an.copy(e.center).add(Lo)),this.expandByPoint(an.copy(e.center).sub(Lo))),this)}equals(e){return e.center.equals(this.center)&&e.radius===this.radius}clone(){return new this.constructor().copy(this)}toJSON(){return{radius:this.radius,center:this.center.toArray()}}fromJSON(e){return this.radius=e.radius,this.center.fromArray(e.center),this}},br=new F,Uo=new F,ta=new F,Or=new F,Do=new F,ra=new F,Fo=new F,Ef=class{constructor(e=new F,t=new F(0,0,-1)){this.origin=e,this.direction=t}set(e,t){return this.origin.copy(e),this.direction.copy(t),this}copy(e){return this.origin.copy(e.origin),this.direction.copy(e.direction),this}at(e,t){return t.copy(this.origin).addScaledVector(this.direction,e)}lookAt(e){return this.direction.copy(e).sub(this.origin).normalize(),this}recast(e){return this.origin.copy(this.at(e,br)),this}closestPointToPoint(e,t){t.subVectors(e,this.origin);let r=t.dot(this.direction);return r<0?t.copy(this.origin):t.copy(this.origin).addScaledVector(this.direction,r)}distanceToPoint(e){return Math.sqrt(this.distanceSqToPoint(e))}distanceSqToPoint(e){let t=br.subVectors(e,this.origin).dot(this.direction);return t<0?this.origin.distanceToSquared(e):(br.copy(this.origin).addScaledVector(this.direction,t),br.distanceToSquared(e))}distanceSqToSegment(e,t,r,i){Uo.copy(e).add(t).multiplyScalar(.5),ta.copy(t).sub(e).normalize(),Or.copy(this.origin).sub(Uo);let n=e.distanceTo(t)*.5,a=-this.direction.dot(ta),o=Or.dot(this.direction),s=-Or.dot(ta),c=Or.lengthSq(),u=Math.abs(1-a*a),l,d,h,m;if(u>0)if(l=a*s-o,d=a*o-s,m=n*u,l>=0)if(d>=-m)if(d<=m){let g=1/u;l*=g,d*=g,h=l*(l+a*d+2*o)+d*(a*l+d+2*s)+c}else d=n,l=Math.max(0,-(a*d+o)),h=-l*l+d*(d+2*s)+c;else d=-n,l=Math.max(0,-(a*d+o)),h=-l*l+d*(d+2*s)+c;else d<=-m?(l=Math.max(0,-(-a*n+o)),d=l>0?-n:Math.min(Math.max(-n,-s),n),h=-l*l+d*(d+2*s)+c):d<=m?(l=0,d=Math.min(Math.max(-n,-s),n),h=d*(d+2*s)+c):(l=Math.max(0,-(a*n+o)),d=l>0?n:Math.min(Math.max(-n,-s),n),h=-l*l+d*(d+2*s)+c);else d=a>0?-n:n,l=Math.max(0,-(a*d+o)),h=-l*l+d*(d+2*s)+c;return r&&r.copy(this.origin).addScaledVector(this.direction,l),i&&i.copy(Uo).addScaledVector(ta,d),h}intersectSphere(e,t){br.subVectors(e.center,this.origin);let r=br.dot(this.direction),i=br.dot(br)-r*r,n=e.radius*e.radius;if(i>n)return null;let a=Math.sqrt(n-i),o=r-a,s=r+a;return s<0?null:o<0?this.at(s,t):this.at(o,t)}intersectsSphere(e){return e.radius<0?!1:this.distanceSqToPoint(e.center)<=e.radius*e.radius}distanceToPlane(e){let t=e.normal.dot(this.direction);if(t===0)return e.distanceToPoint(this.origin)===0?0:null;let r=-(this.origin.dot(e.normal)+e.constant)/t;return r>=0?r:null}intersectPlane(e,t){let r=this.distanceToPlane(e);return r===null?null:this.at(r,t)}intersectsPlane(e){let t=e.distanceToPoint(this.origin);return t===0||e.normal.dot(this.direction)*t<0}intersectBox(e,t){let r,i,n,a,o,s,c=1/this.direction.x,u=1/this.direction.y,l=1/this.direction.z,d=this.origin;return c>=0?(r=(e.min.x-d.x)*c,i=(e.max.x-d.x)*c):(r=(e.max.x-d.x)*c,i=(e.min.x-d.x)*c),u>=0?(n=(e.min.y-d.y)*u,a=(e.max.y-d.y)*u):(n=(e.max.y-d.y)*u,a=(e.min.y-d.y)*u),r>a||n>i||((n>r||isNaN(r))&&(r=n),(a<i||isNaN(i))&&(i=a),l>=0?(o=(e.min.z-d.z)*l,s=(e.max.z-d.z)*l):(o=(e.max.z-d.z)*l,s=(e.min.z-d.z)*l),r>s||o>i)||((o>r||r!==r)&&(r=o),(s<i||i!==i)&&(i=s),i<0)?null:this.at(r>=0?r:i,t)}intersectsBox(e){return this.intersectBox(e,br)!==null}intersectTriangle(e,t,r,i,n){Do.subVectors(t,e),ra.subVectors(r,e),Fo.crossVectors(Do,ra);let a=this.direction.dot(Fo),o;if(a>0){if(i)return null;o=1}else if(a<0)o=-1,a=-a;else return null;Or.subVectors(this.origin,e);let s=o*this.direction.dot(ra.crossVectors(Or,ra));if(s<0)return null;let c=o*this.direction.dot(Do.cross(Or));if(c<0||s+c>a)return null;let u=-o*Or.dot(Fo);return u<0?null:this.at(u/a,n)}applyMatrix4(e){return this.origin.applyMatrix4(e),this.direction.transformDirection(e),this}equals(e){return e.origin.equals(this.origin)&&e.direction.equals(this.direction)}clone(){return new this.constructor().copy(this)}},pt=class qs{constructor(t,r,i,n,a,o,s,c,u,l,d,h,m,g,_,f){qs.prototype.isMatrix4=!0,this.elements=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],t!==void 0&&this.set(t,r,i,n,a,o,s,c,u,l,d,h,m,g,_,f)}set(t,r,i,n,a,o,s,c,u,l,d,h,m,g,_,f){let p=this.elements;return p[0]=t,p[4]=r,p[8]=i,p[12]=n,p[1]=a,p[5]=o,p[9]=s,p[13]=c,p[2]=u,p[6]=l,p[10]=d,p[14]=h,p[3]=m,p[7]=g,p[11]=_,p[15]=f,this}identity(){return this.set(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1),this}clone(){return new qs().fromArray(this.elements)}copy(t){let r=this.elements,i=t.elements;return r[0]=i[0],r[1]=i[1],r[2]=i[2],r[3]=i[3],r[4]=i[4],r[5]=i[5],r[6]=i[6],r[7]=i[7],r[8]=i[8],r[9]=i[9],r[10]=i[10],r[11]=i[11],r[12]=i[12],r[13]=i[13],r[14]=i[14],r[15]=i[15],this}copyPosition(t){let r=this.elements,i=t.elements;return r[12]=i[12],r[13]=i[13],r[14]=i[14],this}setFromMatrix3(t){let r=t.elements;return this.set(r[0],r[3],r[6],0,r[1],r[4],r[7],0,r[2],r[5],r[8],0,0,0,0,1),this}extractBasis(t,r,i){return t.setFromMatrixColumn(this,0),r.setFromMatrixColumn(this,1),i.setFromMatrixColumn(this,2),this}makeBasis(t,r,i){return this.set(t.x,r.x,i.x,0,t.y,r.y,i.y,0,t.z,r.z,i.z,0,0,0,0,1),this}extractRotation(t){let r=this.elements,i=t.elements,n=1/Ai.setFromMatrixColumn(t,0).length(),a=1/Ai.setFromMatrixColumn(t,1).length(),o=1/Ai.setFromMatrixColumn(t,2).length();return r[0]=i[0]*n,r[1]=i[1]*n,r[2]=i[2]*n,r[3]=0,r[4]=i[4]*a,r[5]=i[5]*a,r[6]=i[6]*a,r[7]=0,r[8]=i[8]*o,r[9]=i[9]*o,r[10]=i[10]*o,r[11]=0,r[12]=0,r[13]=0,r[14]=0,r[15]=1,this}makeRotationFromEuler(t){let r=this.elements,i=t.x,n=t.y,a=t.z,o=Math.cos(i),s=Math.sin(i),c=Math.cos(n),u=Math.sin(n),l=Math.cos(a),d=Math.sin(a);if(t.order==="XYZ"){let h=o*l,m=o*d,g=s*l,_=s*d;r[0]=c*l,r[4]=-c*d,r[8]=u,r[1]=m+g*u,r[5]=h-_*u,r[9]=-s*c,r[2]=_-h*u,r[6]=g+m*u,r[10]=o*c}else if(t.order==="YXZ"){let h=c*l,m=c*d,g=u*l,_=u*d;r[0]=h+_*s,r[4]=g*s-m,r[8]=o*u,r[1]=o*d,r[5]=o*l,r[9]=-s,r[2]=m*s-g,r[6]=_+h*s,r[10]=o*c}else if(t.order==="ZXY"){let h=c*l,m=c*d,g=u*l,_=u*d;r[0]=h-_*s,r[4]=-o*d,r[8]=g+m*s,r[1]=m+g*s,r[5]=o*l,r[9]=_-h*s,r[2]=-o*u,r[6]=s,r[10]=o*c}else if(t.order==="ZYX"){let h=o*l,m=o*d,g=s*l,_=s*d;r[0]=c*l,r[4]=g*u-m,r[8]=h*u+_,r[1]=c*d,r[5]=_*u+h,r[9]=m*u-g,r[2]=-u,r[6]=s*c,r[10]=o*c}else if(t.order==="YZX"){let h=o*c,m=o*u,g=s*c,_=s*u;r[0]=c*l,r[4]=_-h*d,r[8]=g*d+m,r[1]=d,r[5]=o*l,r[9]=-s*l,r[2]=-u*l,r[6]=m*d+g,r[10]=h-_*d}else if(t.order==="XZY"){let h=o*c,m=o*u,g=s*c,_=s*u;r[0]=c*l,r[4]=-d,r[8]=u*l,r[1]=h*d+_,r[5]=o*l,r[9]=m*d-g,r[2]=g*d-m,r[6]=s*l,r[10]=_*d+h}return r[3]=0,r[7]=0,r[11]=0,r[12]=0,r[13]=0,r[14]=0,r[15]=1,this}makeRotationFromQuaternion(t){return this.compose(Tf,t,Mf)}lookAt(t,r,i){let n=this.elements;return Nt.subVectors(t,r),Nt.lengthSq()===0&&(Nt.z=1),Nt.normalize(),Lr.crossVectors(i,Nt),Lr.lengthSq()===0&&(Math.abs(i.z)===1?Nt.x+=1e-4:Nt.z+=1e-4,Nt.normalize(),Lr.crossVectors(i,Nt)),Lr.normalize(),ia.crossVectors(Nt,Lr),n[0]=Lr.x,n[4]=ia.x,n[8]=Nt.x,n[1]=Lr.y,n[5]=ia.y,n[9]=Nt.y,n[2]=Lr.z,n[6]=ia.z,n[10]=Nt.z,this}multiply(t){return this.multiplyMatrices(this,t)}premultiply(t){return this.multiplyMatrices(t,this)}multiplyMatrices(t,r){let i=t.elements,n=r.elements,a=this.elements,o=i[0],s=i[4],c=i[8],u=i[12],l=i[1],d=i[5],h=i[9],m=i[13],g=i[2],_=i[6],f=i[10],p=i[14],R=i[3],y=i[7],A=i[11],O=i[15],I=n[0],C=n[4],U=n[8],S=n[12],x=n[1],M=n[5],k=n[9],H=n[13],V=n[2],Z=n[6],G=n[10],ee=n[14],W=n[3],ie=n[7],ce=n[11],Pe=n[15];return a[0]=o*I+s*x+c*V+u*W,a[4]=o*C+s*M+c*Z+u*ie,a[8]=o*U+s*k+c*G+u*ce,a[12]=o*S+s*H+c*ee+u*Pe,a[1]=l*I+d*x+h*V+m*W,a[5]=l*C+d*M+h*Z+m*ie,a[9]=l*U+d*k+h*G+m*ce,a[13]=l*S+d*H+h*ee+m*Pe,a[2]=g*I+_*x+f*V+p*W,a[6]=g*C+_*M+f*Z+p*ie,a[10]=g*U+_*k+f*G+p*ce,a[14]=g*S+_*H+f*ee+p*Pe,a[3]=R*I+y*x+A*V+O*W,a[7]=R*C+y*M+A*Z+O*ie,a[11]=R*U+y*k+A*G+O*ce,a[15]=R*S+y*H+A*ee+O*Pe,this}multiplyScalar(t){let r=this.elements;return r[0]*=t,r[4]*=t,r[8]*=t,r[12]*=t,r[1]*=t,r[5]*=t,r[9]*=t,r[13]*=t,r[2]*=t,r[6]*=t,r[10]*=t,r[14]*=t,r[3]*=t,r[7]*=t,r[11]*=t,r[15]*=t,this}determinant(){let t=this.elements,r=t[0],i=t[4],n=t[8],a=t[12],o=t[1],s=t[5],c=t[9],u=t[13],l=t[2],d=t[6],h=t[10],m=t[14],g=t[3],_=t[7],f=t[11],p=t[15];return g*(+a*c*d-n*u*d-a*s*h+i*u*h+n*s*m-i*c*m)+_*(+r*c*m-r*u*h+a*o*h-n*o*m+n*u*l-a*c*l)+f*(+r*u*d-r*s*m-a*o*d+i*o*m+a*s*l-i*u*l)+p*(-n*s*l-r*c*d+r*s*h+n*o*d-i*o*h+i*c*l)}transpose(){let t=this.elements,r;return r=t[1],t[1]=t[4],t[4]=r,r=t[2],t[2]=t[8],t[8]=r,r=t[6],t[6]=t[9],t[9]=r,r=t[3],t[3]=t[12],t[12]=r,r=t[7],t[7]=t[13],t[13]=r,r=t[11],t[11]=t[14],t[14]=r,this}setPosition(t,r,i){let n=this.elements;return t.isVector3?(n[12]=t.x,n[13]=t.y,n[14]=t.z):(n[12]=t,n[13]=r,n[14]=i),this}invert(){let t=this.elements,r=t[0],i=t[1],n=t[2],a=t[3],o=t[4],s=t[5],c=t[6],u=t[7],l=t[8],d=t[9],h=t[10],m=t[11],g=t[12],_=t[13],f=t[14],p=t[15],R=d*f*u-_*h*u+_*c*m-s*f*m-d*c*p+s*h*p,y=g*h*u-l*f*u-g*c*m+o*f*m+l*c*p-o*h*p,A=l*_*u-g*d*u+g*s*m-o*_*m-l*s*p+o*d*p,O=g*d*c-l*_*c-g*s*h+o*_*h+l*s*f-o*d*f,I=r*R+i*y+n*A+a*O;if(I===0)return this.set(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0);let C=1/I;return t[0]=R*C,t[1]=(_*h*a-d*f*a-_*n*m+i*f*m+d*n*p-i*h*p)*C,t[2]=(s*f*a-_*c*a+_*n*u-i*f*u-s*n*p+i*c*p)*C,t[3]=(d*c*a-s*h*a-d*n*u+i*h*u+s*n*m-i*c*m)*C,t[4]=y*C,t[5]=(l*f*a-g*h*a+g*n*m-r*f*m-l*n*p+r*h*p)*C,t[6]=(g*c*a-o*f*a-g*n*u+r*f*u+o*n*p-r*c*p)*C,t[7]=(o*h*a-l*c*a+l*n*u-r*h*u-o*n*m+r*c*m)*C,t[8]=A*C,t[9]=(g*d*a-l*_*a-g*i*m+r*_*m+l*i*p-r*d*p)*C,t[10]=(o*_*a-g*s*a+g*i*u-r*_*u-o*i*p+r*s*p)*C,t[11]=(l*s*a-o*d*a-l*i*u+r*d*u+o*i*m-r*s*m)*C,t[12]=O*C,t[13]=(l*_*n-g*d*n+g*i*h-r*_*h-l*i*f+r*d*f)*C,t[14]=(g*s*n-o*_*n-g*i*c+r*_*c+o*i*f-r*s*f)*C,t[15]=(o*d*n-l*s*n+l*i*c-r*d*c-o*i*h+r*s*h)*C,this}scale(t){let r=this.elements,i=t.x,n=t.y,a=t.z;return r[0]*=i,r[4]*=n,r[8]*=a,r[1]*=i,r[5]*=n,r[9]*=a,r[2]*=i,r[6]*=n,r[10]*=a,r[3]*=i,r[7]*=n,r[11]*=a,this}getMaxScaleOnAxis(){let t=this.elements,r=t[0]*t[0]+t[1]*t[1]+t[2]*t[2],i=t[4]*t[4]+t[5]*t[5]+t[6]*t[6],n=t[8]*t[8]+t[9]*t[9]+t[10]*t[10];return Math.sqrt(Math.max(r,i,n))}makeTranslation(t,r,i){return t.isVector3?this.set(1,0,0,t.x,0,1,0,t.y,0,0,1,t.z,0,0,0,1):this.set(1,0,0,t,0,1,0,r,0,0,1,i,0,0,0,1),this}makeRotationX(t){let r=Math.cos(t),i=Math.sin(t);return this.set(1,0,0,0,0,r,-i,0,0,i,r,0,0,0,0,1),this}makeRotationY(t){let r=Math.cos(t),i=Math.sin(t);return this.set(r,0,i,0,0,1,0,0,-i,0,r,0,0,0,0,1),this}makeRotationZ(t){let r=Math.cos(t),i=Math.sin(t);return this.set(r,-i,0,0,i,r,0,0,0,0,1,0,0,0,0,1),this}makeRotationAxis(t,r){let i=Math.cos(r),n=Math.sin(r),a=1-i,o=t.x,s=t.y,c=t.z,u=a*o,l=a*s;return this.set(u*o+i,u*s-n*c,u*c+n*s,0,u*s+n*c,l*s+i,l*c-n*o,0,u*c-n*s,l*c+n*o,a*c*c+i,0,0,0,0,1),this}makeScale(t,r,i){return this.set(t,0,0,0,0,r,0,0,0,0,i,0,0,0,0,1),this}makeShear(t,r,i,n,a,o){return this.set(1,i,a,0,t,1,o,0,r,n,1,0,0,0,0,1),this}compose(t,r,i){let n=this.elements,a=r._x,o=r._y,s=r._z,c=r._w,u=a+a,l=o+o,d=s+s,h=a*u,m=a*l,g=a*d,_=o*l,f=o*d,p=s*d,R=c*u,y=c*l,A=c*d,O=i.x,I=i.y,C=i.z;return n[0]=(1-(_+p))*O,n[1]=(m+A)*O,n[2]=(g-y)*O,n[3]=0,n[4]=(m-A)*I,n[5]=(1-(h+p))*I,n[6]=(f+R)*I,n[7]=0,n[8]=(g+y)*C,n[9]=(f-R)*C,n[10]=(1-(h+_))*C,n[11]=0,n[12]=t.x,n[13]=t.y,n[14]=t.z,n[15]=1,this}decompose(t,r,i){let n=this.elements,a=Ai.set(n[0],n[1],n[2]).length(),o=Ai.set(n[4],n[5],n[6]).length(),s=Ai.set(n[8],n[9],n[10]).length();this.determinant()<0&&(a=-a),t.x=n[12],t.y=n[13],t.z=n[14],Wt.copy(this);let c=1/a,u=1/o,l=1/s;return Wt.elements[0]*=c,Wt.elements[1]*=c,Wt.elements[2]*=c,Wt.elements[4]*=u,Wt.elements[5]*=u,Wt.elements[6]*=u,Wt.elements[8]*=l,Wt.elements[9]*=l,Wt.elements[10]*=l,r.setFromRotationMatrix(Wt),i.x=a,i.y=o,i.z=s,this}makePerspective(t,r,i,n,a,o,s=or,c=!1){let u=this.elements,l=2*a/(r-t),d=2*a/(i-n),h=(r+t)/(r-t),m=(i+n)/(i-n),g,_;if(c)g=a/(o-a),_=o*a/(o-a);else if(s===or)g=-(o+a)/(o-a),_=-2*o*a/(o-a);else if(s===Ca)g=-o/(o-a),_=-o*a/(o-a);else throw new Error("THREE.Matrix4.makePerspective(): Invalid coordinate system: "+s);return u[0]=l,u[4]=0,u[8]=h,u[12]=0,u[1]=0,u[5]=d,u[9]=m,u[13]=0,u[2]=0,u[6]=0,u[10]=g,u[14]=_,u[3]=0,u[7]=0,u[11]=-1,u[15]=0,this}makeOrthographic(t,r,i,n,a,o,s=or,c=!1){let u=this.elements,l=2/(r-t),d=2/(i-n),h=-(r+t)/(r-t),m=-(i+n)/(i-n),g,_;if(c)g=1/(o-a),_=o/(o-a);else if(s===or)g=-2/(o-a),_=-(o+a)/(o-a);else if(s===Ca)g=-1/(o-a),_=-a/(o-a);else throw new Error("THREE.Matrix4.makeOrthographic(): Invalid coordinate system: "+s);return u[0]=l,u[4]=0,u[8]=0,u[12]=h,u[1]=0,u[5]=d,u[9]=0,u[13]=m,u[2]=0,u[6]=0,u[10]=g,u[14]=_,u[3]=0,u[7]=0,u[11]=0,u[15]=1,this}equals(t){let r=this.elements,i=t.elements;for(let n=0;n<16;n++)if(r[n]!==i[n])return!1;return!0}fromArray(t,r=0){for(let i=0;i<16;i++)this.elements[i]=t[i+r];return this}toArray(t=[],r=0){let i=this.elements;return t[r]=i[0],t[r+1]=i[1],t[r+2]=i[2],t[r+3]=i[3],t[r+4]=i[4],t[r+5]=i[5],t[r+6]=i[6],t[r+7]=i[7],t[r+8]=i[8],t[r+9]=i[9],t[r+10]=i[10],t[r+11]=i[11],t[r+12]=i[12],t[r+13]=i[13],t[r+14]=i[14],t[r+15]=i[15],t}},Ai=new F,Wt=new pt,Tf=new F(0,0,0),Mf=new F(1,1,1),Lr=new F,ia=new F,Nt=new F,qc=new pt,Yc=new Xi,zr=class Qu{constructor(t=0,r=0,i=0,n=Qu.DEFAULT_ORDER){this.isEuler=!0,this._x=t,this._y=r,this._z=i,this._order=n}get x(){return this._x}set x(t){this._x=t,this._onChangeCallback()}get y(){return this._y}set y(t){this._y=t,this._onChangeCallback()}get z(){return this._z}set z(t){this._z=t,this._onChangeCallback()}get order(){return this._order}set order(t){this._order=t,this._onChangeCallback()}set(t,r,i,n=this._order){return this._x=t,this._y=r,this._z=i,this._order=n,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._order)}copy(t){return this._x=t._x,this._y=t._y,this._z=t._z,this._order=t._order,this._onChangeCallback(),this}setFromRotationMatrix(t,r=this._order,i=!0){let n=t.elements,a=n[0],o=n[4],s=n[8],c=n[1],u=n[5],l=n[9],d=n[2],h=n[6],m=n[10];switch(r){case"XYZ":this._y=Math.asin(Ge(s,-1,1)),Math.abs(s)<.9999999?(this._x=Math.atan2(-l,m),this._z=Math.atan2(-o,a)):(this._x=Math.atan2(h,u),this._z=0);break;case"YXZ":this._x=Math.asin(-Ge(l,-1,1)),Math.abs(l)<.9999999?(this._y=Math.atan2(s,m),this._z=Math.atan2(c,u)):(this._y=Math.atan2(-d,a),this._z=0);break;case"ZXY":this._x=Math.asin(Ge(h,-1,1)),Math.abs(h)<.9999999?(this._y=Math.atan2(-d,m),this._z=Math.atan2(-o,u)):(this._y=0,this._z=Math.atan2(c,a));break;case"ZYX":this._y=Math.asin(-Ge(d,-1,1)),Math.abs(d)<.9999999?(this._x=Math.atan2(h,m),this._z=Math.atan2(c,a)):(this._x=0,this._z=Math.atan2(-o,u));break;case"YZX":this._z=Math.asin(Ge(c,-1,1)),Math.abs(c)<.9999999?(this._x=Math.atan2(-l,u),this._y=Math.atan2(-d,a)):(this._x=0,this._y=Math.atan2(s,m));break;case"XZY":this._z=Math.asin(-Ge(o,-1,1)),Math.abs(o)<.9999999?(this._x=Math.atan2(h,u),this._y=Math.atan2(s,a)):(this._x=Math.atan2(-l,m),this._y=0);break;default:console.warn("THREE.Euler: .setFromRotationMatrix() encountered an unknown order: "+r)}return this._order=r,i===!0&&this._onChangeCallback(),this}setFromQuaternion(t,r,i){return qc.makeRotationFromQuaternion(t),this.setFromRotationMatrix(qc,r,i)}setFromVector3(t,r=this._order){return this.set(t.x,t.y,t.z,r)}reorder(t){return Yc.setFromEuler(this),this.setFromQuaternion(Yc,t)}equals(t){return t._x===this._x&&t._y===this._y&&t._z===this._z&&t._order===this._order}fromArray(t){return this._x=t[0],this._y=t[1],this._z=t[2],t[3]!==void 0&&(this._order=t[3]),this._onChangeCallback(),this}toArray(t=[],r=0){return t[r]=this._x,t[r+1]=this._y,t[r+2]=this._z,t[r+3]=this._order,t}_onChange(t){return this._onChangeCallback=t,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._order}};zr.DEFAULT_ORDER="XYZ";var ed=class{constructor(){this.mask=1}set(e){this.mask=(1<<e|0)>>>0}enable(e){this.mask|=1<<e|0}enableAll(){this.mask=-1}toggle(e){this.mask^=1<<e|0}disable(e){this.mask&=~(1<<e|0)}disableAll(){this.mask=0}test(e){return(this.mask&e.mask)!==0}isEnabled(e){return(this.mask&(1<<e|0))!==0}},Af=0,Kc=new F,wi=new Xi,xr=new pt,na=new F,on=new F,wf=new F,Rf=new Xi,Jc=new F(1,0,0),Zc=new F(0,1,0),$c=new F(0,0,1),Qc={type:"added"},Cf={type:"removed"},Ri={type:"childadded",child:null},ko={type:"childremoved",child:null},kt=class Ma extends ji{constructor(){super(),this.isObject3D=!0,Object.defineProperty(this,"id",{value:Af++}),this.uuid=gn(),this.name="",this.type="Object3D",this.parent=null,this.children=[],this.up=Ma.DEFAULT_UP.clone();let t=new F,r=new zr,i=new Xi,n=new F(1,1,1);function a(){i.setFromEuler(r,!1)}function o(){r.setFromQuaternion(i,void 0,!1)}r._onChange(a),i._onChange(o),Object.defineProperties(this,{position:{configurable:!0,enumerable:!0,value:t},rotation:{configurable:!0,enumerable:!0,value:r},quaternion:{configurable:!0,enumerable:!0,value:i},scale:{configurable:!0,enumerable:!0,value:n},modelViewMatrix:{value:new pt},normalMatrix:{value:new Be}}),this.matrix=new pt,this.matrixWorld=new pt,this.matrixAutoUpdate=Ma.DEFAULT_MATRIX_AUTO_UPDATE,this.matrixWorldAutoUpdate=Ma.DEFAULT_MATRIX_WORLD_AUTO_UPDATE,this.matrixWorldNeedsUpdate=!1,this.layers=new ed,this.visible=!0,this.castShadow=!1,this.receiveShadow=!1,this.frustumCulled=!0,this.renderOrder=0,this.animations=[],this.customDepthMaterial=void 0,this.customDistanceMaterial=void 0,this.userData={}}onBeforeShadow(){}onAfterShadow(){}onBeforeRender(){}onAfterRender(){}applyMatrix4(t){this.matrixAutoUpdate&&this.updateMatrix(),this.matrix.premultiply(t),this.matrix.decompose(this.position,this.quaternion,this.scale)}applyQuaternion(t){return this.quaternion.premultiply(t),this}setRotationFromAxisAngle(t,r){this.quaternion.setFromAxisAngle(t,r)}setRotationFromEuler(t){this.quaternion.setFromEuler(t,!0)}setRotationFromMatrix(t){this.quaternion.setFromRotationMatrix(t)}setRotationFromQuaternion(t){this.quaternion.copy(t)}rotateOnAxis(t,r){return wi.setFromAxisAngle(t,r),this.quaternion.multiply(wi),this}rotateOnWorldAxis(t,r){return wi.setFromAxisAngle(t,r),this.quaternion.premultiply(wi),this}rotateX(t){return this.rotateOnAxis(Jc,t)}rotateY(t){return this.rotateOnAxis(Zc,t)}rotateZ(t){return this.rotateOnAxis($c,t)}translateOnAxis(t,r){return Kc.copy(t).applyQuaternion(this.quaternion),this.position.add(Kc.multiplyScalar(r)),this}translateX(t){return this.translateOnAxis(Jc,t)}translateY(t){return this.translateOnAxis(Zc,t)}translateZ(t){return this.translateOnAxis($c,t)}localToWorld(t){return this.updateWorldMatrix(!0,!1),t.applyMatrix4(this.matrixWorld)}worldToLocal(t){return this.updateWorldMatrix(!0,!1),t.applyMatrix4(xr.copy(this.matrixWorld).invert())}lookAt(t,r,i){t.isVector3?na.copy(t):na.set(t,r,i);let n=this.parent;this.updateWorldMatrix(!0,!1),on.setFromMatrixPosition(this.matrixWorld),this.isCamera||this.isLight?xr.lookAt(on,na,this.up):xr.lookAt(na,on,this.up),this.quaternion.setFromRotationMatrix(xr),n&&(xr.extractRotation(n.matrixWorld),wi.setFromRotationMatrix(xr),this.quaternion.premultiply(wi.invert()))}add(t){if(arguments.length>1){for(let r=0;r<arguments.length;r++)this.add(arguments[r]);return this}return t===this?(console.error("THREE.Object3D.add: object can't be added as a child of itself.",t),this):(t&&t.isObject3D?(t.removeFromParent(),t.parent=this,this.children.push(t),t.dispatchEvent(Qc),Ri.child=t,this.dispatchEvent(Ri),Ri.child=null):console.error("THREE.Object3D.add: object not an instance of THREE.Object3D.",t),this)}remove(t){if(arguments.length>1){for(let i=0;i<arguments.length;i++)this.remove(arguments[i]);return this}let r=this.children.indexOf(t);return r!==-1&&(t.parent=null,this.children.splice(r,1),t.dispatchEvent(Cf),ko.child=t,this.dispatchEvent(ko),ko.child=null),this}removeFromParent(){let t=this.parent;return t!==null&&t.remove(this),this}clear(){return this.remove(...this.children)}attach(t){return this.updateWorldMatrix(!0,!1),xr.copy(this.matrixWorld).invert(),t.parent!==null&&(t.parent.updateWorldMatrix(!0,!1),xr.multiply(t.parent.matrixWorld)),t.applyMatrix4(xr),t.removeFromParent(),t.parent=this,this.children.push(t),t.updateWorldMatrix(!1,!0),t.dispatchEvent(Qc),Ri.child=t,this.dispatchEvent(Ri),Ri.child=null,this}getObjectById(t){return this.getObjectByProperty("id",t)}getObjectByName(t){return this.getObjectByProperty("name",t)}getObjectByProperty(t,r){if(this[t]===r)return this;for(let i=0,n=this.children.length;i<n;i++){let a=this.children[i].getObjectByProperty(t,r);if(a!==void 0)return a}}getObjectsByProperty(t,r,i=[]){this[t]===r&&i.push(this);let n=this.children;for(let a=0,o=n.length;a<o;a++)n[a].getObjectsByProperty(t,r,i);return i}getWorldPosition(t){return this.updateWorldMatrix(!0,!1),t.setFromMatrixPosition(this.matrixWorld)}getWorldQuaternion(t){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(on,t,wf),t}getWorldScale(t){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(on,Rf,t),t}getWorldDirection(t){this.updateWorldMatrix(!0,!1);let r=this.matrixWorld.elements;return t.set(r[8],r[9],r[10]).normalize()}raycast(){}traverse(t){t(this);let r=this.children;for(let i=0,n=r.length;i<n;i++)r[i].traverse(t)}traverseVisible(t){if(this.visible===!1)return;t(this);let r=this.children;for(let i=0,n=r.length;i<n;i++)r[i].traverseVisible(t)}traverseAncestors(t){let r=this.parent;r!==null&&(t(r),r.traverseAncestors(t))}updateMatrix(){this.matrix.compose(this.position,this.quaternion,this.scale),this.matrixWorldNeedsUpdate=!0}updateMatrixWorld(t){this.matrixAutoUpdate&&this.updateMatrix(),(this.matrixWorldNeedsUpdate||t)&&(this.matrixWorldAutoUpdate===!0&&(this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix)),this.matrixWorldNeedsUpdate=!1,t=!0);let r=this.children;for(let i=0,n=r.length;i<n;i++)r[i].updateMatrixWorld(t)}updateWorldMatrix(t,r){let i=this.parent;if(t===!0&&i!==null&&i.updateWorldMatrix(!0,!1),this.matrixAutoUpdate&&this.updateMatrix(),this.matrixWorldAutoUpdate===!0&&(this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix)),r===!0){let n=this.children;for(let a=0,o=n.length;a<o;a++)n[a].updateWorldMatrix(!1,!0)}}toJSON(t){let r=t===void 0||typeof t=="string",i={};r&&(t={geometries:{},materials:{},textures:{},images:{},shapes:{},skeletons:{},animations:{},nodes:{}},i.metadata={version:4.7,type:"Object",generator:"Object3D.toJSON"});let n={};n.uuid=this.uuid,n.type=this.type,this.name!==""&&(n.name=this.name),this.castShadow===!0&&(n.castShadow=!0),this.receiveShadow===!0&&(n.receiveShadow=!0),this.visible===!1&&(n.visible=!1),this.frustumCulled===!1&&(n.frustumCulled=!1),this.renderOrder!==0&&(n.renderOrder=this.renderOrder),Object.keys(this.userData).length>0&&(n.userData=this.userData),n.layers=this.layers.mask,n.matrix=this.matrix.toArray(),n.up=this.up.toArray(),this.matrixAutoUpdate===!1&&(n.matrixAutoUpdate=!1),this.isInstancedMesh&&(n.type="InstancedMesh",n.count=this.count,n.instanceMatrix=this.instanceMatrix.toJSON(),this.instanceColor!==null&&(n.instanceColor=this.instanceColor.toJSON())),this.isBatchedMesh&&(n.type="BatchedMesh",n.perObjectFrustumCulled=this.perObjectFrustumCulled,n.sortObjects=this.sortObjects,n.drawRanges=this._drawRanges,n.reservedRanges=this._reservedRanges,n.geometryInfo=this._geometryInfo.map(s=>({...s,boundingBox:s.boundingBox?s.boundingBox.toJSON():void 0,boundingSphere:s.boundingSphere?s.boundingSphere.toJSON():void 0})),n.instanceInfo=this._instanceInfo.map(s=>({...s})),n.availableInstanceIds=this._availableInstanceIds.slice(),n.availableGeometryIds=this._availableGeometryIds.slice(),n.nextIndexStart=this._nextIndexStart,n.nextVertexStart=this._nextVertexStart,n.geometryCount=this._geometryCount,n.maxInstanceCount=this._maxInstanceCount,n.maxVertexCount=this._maxVertexCount,n.maxIndexCount=this._maxIndexCount,n.geometryInitialized=this._geometryInitialized,n.matricesTexture=this._matricesTexture.toJSON(t),n.indirectTexture=this._indirectTexture.toJSON(t),this._colorsTexture!==null&&(n.colorsTexture=this._colorsTexture.toJSON(t)),this.boundingSphere!==null&&(n.boundingSphere=this.boundingSphere.toJSON()),this.boundingBox!==null&&(n.boundingBox=this.boundingBox.toJSON()));function a(s,c){return s[c.uuid]===void 0&&(s[c.uuid]=c.toJSON(t)),c.uuid}if(this.isScene)this.background&&(this.background.isColor?n.background=this.background.toJSON():this.background.isTexture&&(n.background=this.background.toJSON(t).uuid)),this.environment&&this.environment.isTexture&&this.environment.isRenderTargetTexture!==!0&&(n.environment=this.environment.toJSON(t).uuid);else if(this.isMesh||this.isLine||this.isPoints){n.geometry=a(t.geometries,this.geometry);let s=this.geometry.parameters;if(s!==void 0&&s.shapes!==void 0){let c=s.shapes;if(Array.isArray(c))for(let u=0,l=c.length;u<l;u++){let d=c[u];a(t.shapes,d)}else a(t.shapes,c)}}if(this.isSkinnedMesh&&(n.bindMode=this.bindMode,n.bindMatrix=this.bindMatrix.toArray(),this.skeleton!==void 0&&(a(t.skeletons,this.skeleton),n.skeleton=this.skeleton.uuid)),this.material!==void 0)if(Array.isArray(this.material)){let s=[];for(let c=0,u=this.material.length;c<u;c++)s.push(a(t.materials,this.material[c]));n.material=s}else n.material=a(t.materials,this.material);if(this.children.length>0){n.children=[];for(let s=0;s<this.children.length;s++)n.children.push(this.children[s].toJSON(t).object)}if(this.animations.length>0){n.animations=[];for(let s=0;s<this.animations.length;s++){let c=this.animations[s];n.animations.push(a(t.animations,c))}}if(r){let s=o(t.geometries),c=o(t.materials),u=o(t.textures),l=o(t.images),d=o(t.shapes),h=o(t.skeletons),m=o(t.animations),g=o(t.nodes);s.length>0&&(i.geometries=s),c.length>0&&(i.materials=c),u.length>0&&(i.textures=u),l.length>0&&(i.images=l),d.length>0&&(i.shapes=d),h.length>0&&(i.skeletons=h),m.length>0&&(i.animations=m),g.length>0&&(i.nodes=g)}return i.object=n,i;function o(s){let c=[];for(let u in s){let l=s[u];delete l.metadata,c.push(l)}return c}}clone(t){return new this.constructor().copy(this,t)}copy(t,r=!0){if(this.name=t.name,this.up.copy(t.up),this.position.copy(t.position),this.rotation.order=t.rotation.order,this.quaternion.copy(t.quaternion),this.scale.copy(t.scale),this.matrix.copy(t.matrix),this.matrixWorld.copy(t.matrixWorld),this.matrixAutoUpdate=t.matrixAutoUpdate,this.matrixWorldAutoUpdate=t.matrixWorldAutoUpdate,this.matrixWorldNeedsUpdate=t.matrixWorldNeedsUpdate,this.layers.mask=t.layers.mask,this.visible=t.visible,this.castShadow=t.castShadow,this.receiveShadow=t.receiveShadow,this.frustumCulled=t.frustumCulled,this.renderOrder=t.renderOrder,this.animations=t.animations.slice(),this.userData=JSON.parse(JSON.stringify(t.userData)),r===!0)for(let i=0;i<t.children.length;i++){let n=t.children[i];this.add(n.clone())}return this}};kt.DEFAULT_UP=new F(0,1,0);kt.DEFAULT_MATRIX_AUTO_UPDATE=!0;kt.DEFAULT_MATRIX_WORLD_AUTO_UPDATE=!0;var jt=new F,yr=new F,Bo=new F,Sr=new F,Ci=new F,Ii=new F,eu=new F,Vo=new F,zo=new F,Ho=new F,Go=new lt,Wo=new lt,jo=new lt,sn=class Ui{constructor(t=new F,r=new F,i=new F){this.a=t,this.b=r,this.c=i}static getNormal(t,r,i,n){n.subVectors(i,r),jt.subVectors(t,r),n.cross(jt);let a=n.lengthSq();return a>0?n.multiplyScalar(1/Math.sqrt(a)):n.set(0,0,0)}static getBarycoord(t,r,i,n,a){jt.subVectors(n,r),yr.subVectors(i,r),Bo.subVectors(t,r);let o=jt.dot(jt),s=jt.dot(yr),c=jt.dot(Bo),u=yr.dot(yr),l=yr.dot(Bo),d=o*u-s*s;if(d===0)return a.set(0,0,0),null;let h=1/d,m=(u*c-s*l)*h,g=(o*l-s*c)*h;return a.set(1-m-g,g,m)}static containsPoint(t,r,i,n){return this.getBarycoord(t,r,i,n,Sr)===null?!1:Sr.x>=0&&Sr.y>=0&&Sr.x+Sr.y<=1}static getInterpolation(t,r,i,n,a,o,s,c){return this.getBarycoord(t,r,i,n,Sr)===null?(c.x=0,c.y=0,"z"in c&&(c.z=0),"w"in c&&(c.w=0),null):(c.setScalar(0),c.addScaledVector(a,Sr.x),c.addScaledVector(o,Sr.y),c.addScaledVector(s,Sr.z),c)}static getInterpolatedAttribute(t,r,i,n,a,o){return Go.setScalar(0),Wo.setScalar(0),jo.setScalar(0),Go.fromBufferAttribute(t,r),Wo.fromBufferAttribute(t,i),jo.fromBufferAttribute(t,n),o.setScalar(0),o.addScaledVector(Go,a.x),o.addScaledVector(Wo,a.y),o.addScaledVector(jo,a.z),o}static isFrontFacing(t,r,i,n){return jt.subVectors(i,r),yr.subVectors(t,r),jt.cross(yr).dot(n)<0}set(t,r,i){return this.a.copy(t),this.b.copy(r),this.c.copy(i),this}setFromPointsAndIndices(t,r,i,n){return this.a.copy(t[r]),this.b.copy(t[i]),this.c.copy(t[n]),this}setFromAttributeAndIndices(t,r,i,n){return this.a.fromBufferAttribute(t,r),this.b.fromBufferAttribute(t,i),this.c.fromBufferAttribute(t,n),this}clone(){return new this.constructor().copy(this)}copy(t){return this.a.copy(t.a),this.b.copy(t.b),this.c.copy(t.c),this}getArea(){return jt.subVectors(this.c,this.b),yr.subVectors(this.a,this.b),jt.cross(yr).length()*.5}getMidpoint(t){return t.addVectors(this.a,this.b).add(this.c).multiplyScalar(1/3)}getNormal(t){return Ui.getNormal(this.a,this.b,this.c,t)}getPlane(t){return t.setFromCoplanarPoints(this.a,this.b,this.c)}getBarycoord(t,r){return Ui.getBarycoord(t,this.a,this.b,this.c,r)}getInterpolation(t,r,i,n,a){return Ui.getInterpolation(t,this.a,this.b,this.c,r,i,n,a)}containsPoint(t){return Ui.containsPoint(t,this.a,this.b,this.c)}isFrontFacing(t){return Ui.isFrontFacing(this.a,this.b,this.c,t)}intersectsBox(t){return t.intersectsTriangle(this)}closestPointToPoint(t,r){let i=this.a,n=this.b,a=this.c,o,s;Ci.subVectors(n,i),Ii.subVectors(a,i),Vo.subVectors(t,i);let c=Ci.dot(Vo),u=Ii.dot(Vo);if(c<=0&&u<=0)return r.copy(i);zo.subVectors(t,n);let l=Ci.dot(zo),d=Ii.dot(zo);if(l>=0&&d<=l)return r.copy(n);let h=c*d-l*u;if(h<=0&&c>=0&&l<=0)return o=c/(c-l),r.copy(i).addScaledVector(Ci,o);Ho.subVectors(t,a);let m=Ci.dot(Ho),g=Ii.dot(Ho);if(g>=0&&m<=g)return r.copy(a);let _=m*u-c*g;if(_<=0&&u>=0&&g<=0)return s=u/(u-g),r.copy(i).addScaledVector(Ii,s);let f=l*g-m*d;if(f<=0&&d-l>=0&&m-g>=0)return eu.subVectors(a,n),s=(d-l)/(d-l+(m-g)),r.copy(n).addScaledVector(eu,s);let p=1/(f+_+h);return o=_*p,s=h*p,r.copy(i).addScaledVector(Ci,o).addScaledVector(Ii,s)}equals(t){return t.a.equals(this.a)&&t.b.equals(this.b)&&t.c.equals(this.c)}},td={aliceblue:15792383,antiquewhite:16444375,aqua:65535,aquamarine:8388564,azure:15794175,beige:16119260,bisque:16770244,black:0,blanchedalmond:16772045,blue:255,blueviolet:9055202,brown:10824234,burlywood:14596231,cadetblue:6266528,chartreuse:8388352,chocolate:13789470,coral:16744272,cornflowerblue:6591981,cornsilk:16775388,crimson:14423100,cyan:65535,darkblue:139,darkcyan:35723,darkgoldenrod:12092939,darkgray:11119017,darkgreen:25600,darkgrey:11119017,darkkhaki:12433259,darkmagenta:9109643,darkolivegreen:5597999,darkorange:16747520,darkorchid:10040012,darkred:9109504,darksalmon:15308410,darkseagreen:9419919,darkslateblue:4734347,darkslategray:3100495,darkslategrey:3100495,darkturquoise:52945,darkviolet:9699539,deeppink:16716947,deepskyblue:49151,dimgray:6908265,dimgrey:6908265,dodgerblue:2003199,firebrick:11674146,floralwhite:16775920,forestgreen:2263842,fuchsia:16711935,gainsboro:14474460,ghostwhite:16316671,gold:16766720,goldenrod:14329120,gray:8421504,green:32768,greenyellow:11403055,grey:8421504,honeydew:15794160,hotpink:16738740,indianred:13458524,indigo:4915330,ivory:16777200,khaki:15787660,lavender:15132410,lavenderblush:16773365,lawngreen:8190976,lemonchiffon:16775885,lightblue:11393254,lightcoral:15761536,lightcyan:14745599,lightgoldenrodyellow:16448210,lightgray:13882323,lightgreen:9498256,lightgrey:13882323,lightpink:16758465,lightsalmon:16752762,lightseagreen:2142890,lightskyblue:8900346,lightslategray:7833753,lightslategrey:7833753,lightsteelblue:11584734,lightyellow:16777184,lime:65280,limegreen:3329330,linen:16445670,magenta:16711935,maroon:8388608,mediumaquamarine:6737322,mediumblue:205,mediumorchid:12211667,mediumpurple:9662683,mediumseagreen:3978097,mediumslateblue:8087790,mediumspringgreen:64154,mediumturquoise:4772300,mediumvioletred:13047173,midnightblue:1644912,mintcream:16121850,mistyrose:16770273,moccasin:16770229,navajowhite:16768685,navy:128,oldlace:16643558,olive:8421376,olivedrab:7048739,orange:16753920,orangered:16729344,orchid:14315734,palegoldenrod:15657130,palegreen:10025880,paleturquoise:11529966,palevioletred:14381203,papayawhip:16773077,peachpuff:16767673,peru:13468991,pink:16761035,plum:14524637,powderblue:11591910,purple:8388736,rebeccapurple:6697881,red:16711680,rosybrown:12357519,royalblue:4286945,saddlebrown:9127187,salmon:16416882,sandybrown:16032864,seagreen:3050327,seashell:16774638,sienna:10506797,silver:12632256,skyblue:8900331,slateblue:6970061,slategray:7372944,slategrey:7372944,snow:16775930,springgreen:65407,steelblue:4620980,tan:13808780,teal:32896,thistle:14204888,tomato:16737095,turquoise:4251856,violet:15631086,wheat:16113331,white:16777215,whitesmoke:16119285,yellow:16776960,yellowgreen:10145074},Ur={h:0,s:0,l:0},aa={h:0,s:0,l:0};function Xo(e,t,r){return r<0&&(r+=1),r>1&&(r-=1),r<1/6?e+(t-e)*6*r:r<1/2?t:r<2/3?e+(t-e)*6*(2/3-r):e}var qe=class{constructor(e,t,r){return this.isColor=!0,this.r=1,this.g=1,this.b=1,this.set(e,t,r)}set(e,t,r){if(t===void 0&&r===void 0){let i=e;i&&i.isColor?this.copy(i):typeof i=="number"?this.setHex(i):typeof i=="string"&&this.setStyle(i)}else this.setRGB(e,t,r);return this}setScalar(e){return this.r=e,this.g=e,this.b=e,this}setHex(e,t=Ft){return e=Math.floor(e),this.r=(e>>16&255)/255,this.g=(e>>8&255)/255,this.b=(e&255)/255,Xe.colorSpaceToWorking(this,t),this}setRGB(e,t,r,i=Xe.workingColorSpace){return this.r=e,this.g=t,this.b=r,Xe.colorSpaceToWorking(this,i),this}setHSL(e,t,r,i=Xe.workingColorSpace){if(e=pf(e,1),t=Ge(t,0,1),r=Ge(r,0,1),t===0)this.r=this.g=this.b=r;else{let n=r<=.5?r*(1+t):r+t-r*t,a=2*r-n;this.r=Xo(a,n,e+1/3),this.g=Xo(a,n,e),this.b=Xo(a,n,e-1/3)}return Xe.colorSpaceToWorking(this,i),this}setStyle(e,t=Ft){function r(n){n!==void 0&&parseFloat(n)<1&&console.warn("THREE.Color: Alpha component of "+e+" will be ignored.")}let i;if(i=/^(\w+)\(([^\)]*)\)/.exec(e)){let n,a=i[1],o=i[2];switch(a){case"rgb":case"rgba":if(n=/^\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o))return r(n[4]),this.setRGB(Math.min(255,parseInt(n[1],10))/255,Math.min(255,parseInt(n[2],10))/255,Math.min(255,parseInt(n[3],10))/255,t);if(n=/^\s*(\d+)\%\s*,\s*(\d+)\%\s*,\s*(\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o))return r(n[4]),this.setRGB(Math.min(100,parseInt(n[1],10))/100,Math.min(100,parseInt(n[2],10))/100,Math.min(100,parseInt(n[3],10))/100,t);break;case"hsl":case"hsla":if(n=/^\s*(\d*\.?\d+)\s*,\s*(\d*\.?\d+)\%\s*,\s*(\d*\.?\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o))return r(n[4]),this.setHSL(parseFloat(n[1])/360,parseFloat(n[2])/100,parseFloat(n[3])/100,t);break;default:console.warn("THREE.Color: Unknown color model "+e)}}else if(i=/^\#([A-Fa-f\d]+)$/.exec(e)){let n=i[1],a=n.length;if(a===3)return this.setRGB(parseInt(n.charAt(0),16)/15,parseInt(n.charAt(1),16)/15,parseInt(n.charAt(2),16)/15,t);if(a===6)return this.setHex(parseInt(n,16),t);console.warn("THREE.Color: Invalid hex color "+e)}else if(e&&e.length>0)return this.setColorName(e,t);return this}setColorName(e,t=Ft){let r=td[e.toLowerCase()];return r!==void 0?this.setHex(r,t):console.warn("THREE.Color: Unknown color "+e),this}clone(){return new this.constructor(this.r,this.g,this.b)}copy(e){return this.r=e.r,this.g=e.g,this.b=e.b,this}copySRGBToLinear(e){return this.r=Ar(e.r),this.g=Ar(e.g),this.b=Ar(e.b),this}copyLinearToSRGB(e){return this.r=Bi(e.r),this.g=Bi(e.g),this.b=Bi(e.b),this}convertSRGBToLinear(){return this.copySRGBToLinear(this),this}convertLinearToSRGB(){return this.copyLinearToSRGB(this),this}getHex(e=Ft){return Xe.workingToColorSpace(yt.copy(this),e),Math.round(Ge(yt.r*255,0,255))*65536+Math.round(Ge(yt.g*255,0,255))*256+Math.round(Ge(yt.b*255,0,255))}getHexString(e=Ft){return("000000"+this.getHex(e).toString(16)).slice(-6)}getHSL(e,t=Xe.workingColorSpace){Xe.workingToColorSpace(yt.copy(this),t);let r=yt.r,i=yt.g,n=yt.b,a=Math.max(r,i,n),o=Math.min(r,i,n),s,c,u=(o+a)/2;if(o===a)s=0,c=0;else{let l=a-o;switch(c=u<=.5?l/(a+o):l/(2-a-o),a){case r:s=(i-n)/l+(i<n?6:0);break;case i:s=(n-r)/l+2;break;case n:s=(r-i)/l+4;break}s/=6}return e.h=s,e.s=c,e.l=u,e}getRGB(e,t=Xe.workingColorSpace){return Xe.workingToColorSpace(yt.copy(this),t),e.r=yt.r,e.g=yt.g,e.b=yt.b,e}getStyle(e=Ft){Xe.workingToColorSpace(yt.copy(this),e);let t=yt.r,r=yt.g,i=yt.b;return e!==Ft?`color(${e} ${t.toFixed(3)} ${r.toFixed(3)} ${i.toFixed(3)})`:`rgb(${Math.round(t*255)},${Math.round(r*255)},${Math.round(i*255)})`}offsetHSL(e,t,r){return this.getHSL(Ur),this.setHSL(Ur.h+e,Ur.s+t,Ur.l+r)}add(e){return this.r+=e.r,this.g+=e.g,this.b+=e.b,this}addColors(e,t){return this.r=e.r+t.r,this.g=e.g+t.g,this.b=e.b+t.b,this}addScalar(e){return this.r+=e,this.g+=e,this.b+=e,this}sub(e){return this.r=Math.max(0,this.r-e.r),this.g=Math.max(0,this.g-e.g),this.b=Math.max(0,this.b-e.b),this}multiply(e){return this.r*=e.r,this.g*=e.g,this.b*=e.b,this}multiplyScalar(e){return this.r*=e,this.g*=e,this.b*=e,this}lerp(e,t){return this.r+=(e.r-this.r)*t,this.g+=(e.g-this.g)*t,this.b+=(e.b-this.b)*t,this}lerpColors(e,t,r){return this.r=e.r+(t.r-e.r)*r,this.g=e.g+(t.g-e.g)*r,this.b=e.b+(t.b-e.b)*r,this}lerpHSL(e,t){this.getHSL(Ur),e.getHSL(aa);let r=Ro(Ur.h,aa.h,t),i=Ro(Ur.s,aa.s,t),n=Ro(Ur.l,aa.l,t);return this.setHSL(r,i,n),this}setFromVector3(e){return this.r=e.x,this.g=e.y,this.b=e.z,this}applyMatrix3(e){let t=this.r,r=this.g,i=this.b,n=e.elements;return this.r=n[0]*t+n[3]*r+n[6]*i,this.g=n[1]*t+n[4]*r+n[7]*i,this.b=n[2]*t+n[5]*r+n[8]*i,this}equals(e){return e.r===this.r&&e.g===this.g&&e.b===this.b}fromArray(e,t=0){return this.r=e[t],this.g=e[t+1],this.b=e[t+2],this}toArray(e=[],t=0){return e[t]=this.r,e[t+1]=this.g,e[t+2]=this.b,e}fromBufferAttribute(e,t){return this.r=e.getX(t),this.g=e.getY(t),this.b=e.getZ(t),this}toJSON(){return this.getHex()}*[Symbol.iterator](){yield this.r,yield this.g,yield this.b}},yt=new qe;qe.NAMES=td;var If=0,_n=class extends ji{constructor(){super(),this.isMaterial=!0,Object.defineProperty(this,"id",{value:If++}),this.uuid=gn(),this.name="",this.type="Material",this.blending=ki,this.side=Vr,this.vertexColors=!1,this.opacity=1,this.transparent=!1,this.alphaHash=!1,this.blendSrc=ns,this.blendDst=as,this.blendEquation=ri,this.blendSrcAlpha=null,this.blendDstAlpha=null,this.blendEquationAlpha=null,this.blendColor=new qe(0,0,0),this.blendAlpha=0,this.depthFunc=Vi,this.depthTest=!0,this.depthWrite=!0,this.stencilWriteMask=255,this.stencilFunc=Vc,this.stencilRef=0,this.stencilFuncMask=255,this.stencilFail=yi,this.stencilZFail=yi,this.stencilZPass=yi,this.stencilWrite=!1,this.clippingPlanes=null,this.clipIntersection=!1,this.clipShadows=!1,this.shadowSide=null,this.colorWrite=!0,this.precision=null,this.polygonOffset=!1,this.polygonOffsetFactor=0,this.polygonOffsetUnits=0,this.dithering=!1,this.alphaToCoverage=!1,this.premultipliedAlpha=!1,this.forceSinglePass=!1,this.allowOverride=!0,this.visible=!0,this.toneMapped=!0,this.userData={},this.version=0,this._alphaTest=0}get alphaTest(){return this._alphaTest}set alphaTest(e){this._alphaTest>0!=e>0&&this.version++,this._alphaTest=e}onBeforeRender(){}onBeforeCompile(){}customProgramCacheKey(){return this.onBeforeCompile.toString()}setValues(e){if(e!==void 0)for(let t in e){let r=e[t];if(r===void 0){console.warn(`THREE.Material: parameter '${t}' has value of undefined.`);continue}let i=this[t];if(i===void 0){console.warn(`THREE.Material: '${t}' is not a property of THREE.${this.type}.`);continue}i&&i.isColor?i.set(r):i&&i.isVector3&&r&&r.isVector3?i.copy(r):this[t]=r}}toJSON(e){let t=e===void 0||typeof e=="string";t&&(e={textures:{},images:{}});let r={metadata:{version:4.7,type:"Material",generator:"Material.toJSON"}};r.uuid=this.uuid,r.type=this.type,this.name!==""&&(r.name=this.name),this.color&&this.color.isColor&&(r.color=this.color.getHex()),this.roughness!==void 0&&(r.roughness=this.roughness),this.metalness!==void 0&&(r.metalness=this.metalness),this.sheen!==void 0&&(r.sheen=this.sheen),this.sheenColor&&this.sheenColor.isColor&&(r.sheenColor=this.sheenColor.getHex()),this.sheenRoughness!==void 0&&(r.sheenRoughness=this.sheenRoughness),this.emissive&&this.emissive.isColor&&(r.emissive=this.emissive.getHex()),this.emissiveIntensity!==void 0&&this.emissiveIntensity!==1&&(r.emissiveIntensity=this.emissiveIntensity),this.specular&&this.specular.isColor&&(r.specular=this.specular.getHex()),this.specularIntensity!==void 0&&(r.specularIntensity=this.specularIntensity),this.specularColor&&this.specularColor.isColor&&(r.specularColor=this.specularColor.getHex()),this.shininess!==void 0&&(r.shininess=this.shininess),this.clearcoat!==void 0&&(r.clearcoat=this.clearcoat),this.clearcoatRoughness!==void 0&&(r.clearcoatRoughness=this.clearcoatRoughness),this.clearcoatMap&&this.clearcoatMap.isTexture&&(r.clearcoatMap=this.clearcoatMap.toJSON(e).uuid),this.clearcoatRoughnessMap&&this.clearcoatRoughnessMap.isTexture&&(r.clearcoatRoughnessMap=this.clearcoatRoughnessMap.toJSON(e).uuid),this.clearcoatNormalMap&&this.clearcoatNormalMap.isTexture&&(r.clearcoatNormalMap=this.clearcoatNormalMap.toJSON(e).uuid,r.clearcoatNormalScale=this.clearcoatNormalScale.toArray()),this.sheenColorMap&&this.sheenColorMap.isTexture&&(r.sheenColorMap=this.sheenColorMap.toJSON(e).uuid),this.sheenRoughnessMap&&this.sheenRoughnessMap.isTexture&&(r.sheenRoughnessMap=this.sheenRoughnessMap.toJSON(e).uuid),this.dispersion!==void 0&&(r.dispersion=this.dispersion),this.iridescence!==void 0&&(r.iridescence=this.iridescence),this.iridescenceIOR!==void 0&&(r.iridescenceIOR=this.iridescenceIOR),this.iridescenceThicknessRange!==void 0&&(r.iridescenceThicknessRange=this.iridescenceThicknessRange),this.iridescenceMap&&this.iridescenceMap.isTexture&&(r.iridescenceMap=this.iridescenceMap.toJSON(e).uuid),this.iridescenceThicknessMap&&this.iridescenceThicknessMap.isTexture&&(r.iridescenceThicknessMap=this.iridescenceThicknessMap.toJSON(e).uuid),this.anisotropy!==void 0&&(r.anisotropy=this.anisotropy),this.anisotropyRotation!==void 0&&(r.anisotropyRotation=this.anisotropyRotation),this.anisotropyMap&&this.anisotropyMap.isTexture&&(r.anisotropyMap=this.anisotropyMap.toJSON(e).uuid),this.map&&this.map.isTexture&&(r.map=this.map.toJSON(e).uuid),this.matcap&&this.matcap.isTexture&&(r.matcap=this.matcap.toJSON(e).uuid),this.alphaMap&&this.alphaMap.isTexture&&(r.alphaMap=this.alphaMap.toJSON(e).uuid),this.lightMap&&this.lightMap.isTexture&&(r.lightMap=this.lightMap.toJSON(e).uuid,r.lightMapIntensity=this.lightMapIntensity),this.aoMap&&this.aoMap.isTexture&&(r.aoMap=this.aoMap.toJSON(e).uuid,r.aoMapIntensity=this.aoMapIntensity),this.bumpMap&&this.bumpMap.isTexture&&(r.bumpMap=this.bumpMap.toJSON(e).uuid,r.bumpScale=this.bumpScale),this.normalMap&&this.normalMap.isTexture&&(r.normalMap=this.normalMap.toJSON(e).uuid,r.normalMapType=this.normalMapType,r.normalScale=this.normalScale.toArray()),this.displacementMap&&this.displacementMap.isTexture&&(r.displacementMap=this.displacementMap.toJSON(e).uuid,r.displacementScale=this.displacementScale,r.displacementBias=this.displacementBias),this.roughnessMap&&this.roughnessMap.isTexture&&(r.roughnessMap=this.roughnessMap.toJSON(e).uuid),this.metalnessMap&&this.metalnessMap.isTexture&&(r.metalnessMap=this.metalnessMap.toJSON(e).uuid),this.emissiveMap&&this.emissiveMap.isTexture&&(r.emissiveMap=this.emissiveMap.toJSON(e).uuid),this.specularMap&&this.specularMap.isTexture&&(r.specularMap=this.specularMap.toJSON(e).uuid),this.specularIntensityMap&&this.specularIntensityMap.isTexture&&(r.specularIntensityMap=this.specularIntensityMap.toJSON(e).uuid),this.specularColorMap&&this.specularColorMap.isTexture&&(r.specularColorMap=this.specularColorMap.toJSON(e).uuid),this.envMap&&this.envMap.isTexture&&(r.envMap=this.envMap.toJSON(e).uuid,this.combine!==void 0&&(r.combine=this.combine)),this.envMapRotation!==void 0&&(r.envMapRotation=this.envMapRotation.toArray()),this.envMapIntensity!==void 0&&(r.envMapIntensity=this.envMapIntensity),this.reflectivity!==void 0&&(r.reflectivity=this.reflectivity),this.refractionRatio!==void 0&&(r.refractionRatio=this.refractionRatio),this.gradientMap&&this.gradientMap.isTexture&&(r.gradientMap=this.gradientMap.toJSON(e).uuid),this.transmission!==void 0&&(r.transmission=this.transmission),this.transmissionMap&&this.transmissionMap.isTexture&&(r.transmissionMap=this.transmissionMap.toJSON(e).uuid),this.thickness!==void 0&&(r.thickness=this.thickness),this.thicknessMap&&this.thicknessMap.isTexture&&(r.thicknessMap=this.thicknessMap.toJSON(e).uuid),this.attenuationDistance!==void 0&&this.attenuationDistance!==1/0&&(r.attenuationDistance=this.attenuationDistance),this.attenuationColor!==void 0&&(r.attenuationColor=this.attenuationColor.getHex()),this.size!==void 0&&(r.size=this.size),this.shadowSide!==null&&(r.shadowSide=this.shadowSide),this.sizeAttenuation!==void 0&&(r.sizeAttenuation=this.sizeAttenuation),this.blending!==ki&&(r.blending=this.blending),this.side!==Vr&&(r.side=this.side),this.vertexColors===!0&&(r.vertexColors=!0),this.opacity<1&&(r.opacity=this.opacity),this.transparent===!0&&(r.transparent=!0),this.blendSrc!==ns&&(r.blendSrc=this.blendSrc),this.blendDst!==as&&(r.blendDst=this.blendDst),this.blendEquation!==ri&&(r.blendEquation=this.blendEquation),this.blendSrcAlpha!==null&&(r.blendSrcAlpha=this.blendSrcAlpha),this.blendDstAlpha!==null&&(r.blendDstAlpha=this.blendDstAlpha),this.blendEquationAlpha!==null&&(r.blendEquationAlpha=this.blendEquationAlpha),this.blendColor&&this.blendColor.isColor&&(r.blendColor=this.blendColor.getHex()),this.blendAlpha!==0&&(r.blendAlpha=this.blendAlpha),this.depthFunc!==Vi&&(r.depthFunc=this.depthFunc),this.depthTest===!1&&(r.depthTest=this.depthTest),this.depthWrite===!1&&(r.depthWrite=this.depthWrite),this.colorWrite===!1&&(r.colorWrite=this.colorWrite),this.stencilWriteMask!==255&&(r.stencilWriteMask=this.stencilWriteMask),this.stencilFunc!==Vc&&(r.stencilFunc=this.stencilFunc),this.stencilRef!==0&&(r.stencilRef=this.stencilRef),this.stencilFuncMask!==255&&(r.stencilFuncMask=this.stencilFuncMask),this.stencilFail!==yi&&(r.stencilFail=this.stencilFail),this.stencilZFail!==yi&&(r.stencilZFail=this.stencilZFail),this.stencilZPass!==yi&&(r.stencilZPass=this.stencilZPass),this.stencilWrite===!0&&(r.stencilWrite=this.stencilWrite),this.rotation!==void 0&&this.rotation!==0&&(r.rotation=this.rotation),this.polygonOffset===!0&&(r.polygonOffset=!0),this.polygonOffsetFactor!==0&&(r.polygonOffsetFactor=this.polygonOffsetFactor),this.polygonOffsetUnits!==0&&(r.polygonOffsetUnits=this.polygonOffsetUnits),this.linewidth!==void 0&&this.linewidth!==1&&(r.linewidth=this.linewidth),this.dashSize!==void 0&&(r.dashSize=this.dashSize),this.gapSize!==void 0&&(r.gapSize=this.gapSize),this.scale!==void 0&&(r.scale=this.scale),this.dithering===!0&&(r.dithering=!0),this.alphaTest>0&&(r.alphaTest=this.alphaTest),this.alphaHash===!0&&(r.alphaHash=!0),this.alphaToCoverage===!0&&(r.alphaToCoverage=!0),this.premultipliedAlpha===!0&&(r.premultipliedAlpha=!0),this.forceSinglePass===!0&&(r.forceSinglePass=!0),this.wireframe===!0&&(r.wireframe=!0),this.wireframeLinewidth>1&&(r.wireframeLinewidth=this.wireframeLinewidth),this.wireframeLinecap!=="round"&&(r.wireframeLinecap=this.wireframeLinecap),this.wireframeLinejoin!=="round"&&(r.wireframeLinejoin=this.wireframeLinejoin),this.flatShading===!0&&(r.flatShading=!0),this.visible===!1&&(r.visible=!1),this.toneMapped===!1&&(r.toneMapped=!1),this.fog===!1&&(r.fog=!1),Object.keys(this.userData).length>0&&(r.userData=this.userData);function i(n){let a=[];for(let o in n){let s=n[o];delete s.metadata,a.push(s)}return a}if(t){let n=i(e.textures),a=i(e.images);n.length>0&&(r.textures=n),a.length>0&&(r.images=a)}return r}clone(){return new this.constructor().copy(this)}copy(e){this.name=e.name,this.blending=e.blending,this.side=e.side,this.vertexColors=e.vertexColors,this.opacity=e.opacity,this.transparent=e.transparent,this.blendSrc=e.blendSrc,this.blendDst=e.blendDst,this.blendEquation=e.blendEquation,this.blendSrcAlpha=e.blendSrcAlpha,this.blendDstAlpha=e.blendDstAlpha,this.blendEquationAlpha=e.blendEquationAlpha,this.blendColor.copy(e.blendColor),this.blendAlpha=e.blendAlpha,this.depthFunc=e.depthFunc,this.depthTest=e.depthTest,this.depthWrite=e.depthWrite,this.stencilWriteMask=e.stencilWriteMask,this.stencilFunc=e.stencilFunc,this.stencilRef=e.stencilRef,this.stencilFuncMask=e.stencilFuncMask,this.stencilFail=e.stencilFail,this.stencilZFail=e.stencilZFail,this.stencilZPass=e.stencilZPass,this.stencilWrite=e.stencilWrite;let t=e.clippingPlanes,r=null;if(t!==null){let i=t.length;r=new Array(i);for(let n=0;n!==i;++n)r[n]=t[n].clone()}return this.clippingPlanes=r,this.clipIntersection=e.clipIntersection,this.clipShadows=e.clipShadows,this.shadowSide=e.shadowSide,this.colorWrite=e.colorWrite,this.precision=e.precision,this.polygonOffset=e.polygonOffset,this.polygonOffsetFactor=e.polygonOffsetFactor,this.polygonOffsetUnits=e.polygonOffsetUnits,this.dithering=e.dithering,this.alphaTest=e.alphaTest,this.alphaHash=e.alphaHash,this.alphaToCoverage=e.alphaToCoverage,this.premultipliedAlpha=e.premultipliedAlpha,this.forceSinglePass=e.forceSinglePass,this.visible=e.visible,this.toneMapped=e.toneMapped,this.userData=JSON.parse(JSON.stringify(e.userData)),this}dispose(){this.dispatchEvent({type:"dispose"})}set needsUpdate(e){e===!0&&this.version++}},rd=class extends _n{constructor(e){super(),this.isMeshBasicMaterial=!0,this.type="MeshBasicMaterial",this.color=new qe(16777215),this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.specularMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new zr,this.combine=Uu,this.reflectivity=1,this.refractionRatio=.98,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.fog=!0,this.setValues(e)}copy(e){return super.copy(e),this.color.copy(e.color),this.map=e.map,this.lightMap=e.lightMap,this.lightMapIntensity=e.lightMapIntensity,this.aoMap=e.aoMap,this.aoMapIntensity=e.aoMapIntensity,this.specularMap=e.specularMap,this.alphaMap=e.alphaMap,this.envMap=e.envMap,this.envMapRotation.copy(e.envMapRotation),this.combine=e.combine,this.reflectivity=e.reflectivity,this.refractionRatio=e.refractionRatio,this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this.wireframeLinecap=e.wireframeLinecap,this.wireframeLinejoin=e.wireframeLinejoin,this.fog=e.fog,this}},st=new F,oa=new Ye,Nf=0,sr=class{constructor(e,t,r=!1){if(Array.isArray(e))throw new TypeError("THREE.BufferAttribute: array should be a Typed Array.");this.isBufferAttribute=!0,Object.defineProperty(this,"id",{value:Nf++}),this.name="",this.array=e,this.itemSize=t,this.count=e!==void 0?e.length/t:0,this.normalized=r,this.usage=zc,this.updateRanges=[],this.gpuType=Mr,this.version=0}onUploadCallback(){}set needsUpdate(e){e===!0&&this.version++}setUsage(e){return this.usage=e,this}addUpdateRange(e,t){this.updateRanges.push({start:e,count:t})}clearUpdateRanges(){this.updateRanges.length=0}copy(e){return this.name=e.name,this.array=new e.array.constructor(e.array),this.itemSize=e.itemSize,this.count=e.count,this.normalized=e.normalized,this.usage=e.usage,this.gpuType=e.gpuType,this}copyAt(e,t,r){e*=this.itemSize,r*=t.itemSize;for(let i=0,n=this.itemSize;i<n;i++)this.array[e+i]=t.array[r+i];return this}copyArray(e){return this.array.set(e),this}applyMatrix3(e){if(this.itemSize===2)for(let t=0,r=this.count;t<r;t++)oa.fromBufferAttribute(this,t),oa.applyMatrix3(e),this.setXY(t,oa.x,oa.y);else if(this.itemSize===3)for(let t=0,r=this.count;t<r;t++)st.fromBufferAttribute(this,t),st.applyMatrix3(e),this.setXYZ(t,st.x,st.y,st.z);return this}applyMatrix4(e){for(let t=0,r=this.count;t<r;t++)st.fromBufferAttribute(this,t),st.applyMatrix4(e),this.setXYZ(t,st.x,st.y,st.z);return this}applyNormalMatrix(e){for(let t=0,r=this.count;t<r;t++)st.fromBufferAttribute(this,t),st.applyNormalMatrix(e),this.setXYZ(t,st.x,st.y,st.z);return this}transformDirection(e){for(let t=0,r=this.count;t<r;t++)st.fromBufferAttribute(this,t),st.transformDirection(e),this.setXYZ(t,st.x,st.y,st.z);return this}set(e,t=0){return this.array.set(e,t),this}getComponent(e,t){let r=this.array[e*this.itemSize+t];return this.normalized&&(r=rn(r,this.array)),r}setComponent(e,t,r){return this.normalized&&(r=wt(r,this.array)),this.array[e*this.itemSize+t]=r,this}getX(e){let t=this.array[e*this.itemSize];return this.normalized&&(t=rn(t,this.array)),t}setX(e,t){return this.normalized&&(t=wt(t,this.array)),this.array[e*this.itemSize]=t,this}getY(e){let t=this.array[e*this.itemSize+1];return this.normalized&&(t=rn(t,this.array)),t}setY(e,t){return this.normalized&&(t=wt(t,this.array)),this.array[e*this.itemSize+1]=t,this}getZ(e){let t=this.array[e*this.itemSize+2];return this.normalized&&(t=rn(t,this.array)),t}setZ(e,t){return this.normalized&&(t=wt(t,this.array)),this.array[e*this.itemSize+2]=t,this}getW(e){let t=this.array[e*this.itemSize+3];return this.normalized&&(t=rn(t,this.array)),t}setW(e,t){return this.normalized&&(t=wt(t,this.array)),this.array[e*this.itemSize+3]=t,this}setXY(e,t,r){return e*=this.itemSize,this.normalized&&(t=wt(t,this.array),r=wt(r,this.array)),this.array[e+0]=t,this.array[e+1]=r,this}setXYZ(e,t,r,i){return e*=this.itemSize,this.normalized&&(t=wt(t,this.array),r=wt(r,this.array),i=wt(i,this.array)),this.array[e+0]=t,this.array[e+1]=r,this.array[e+2]=i,this}setXYZW(e,t,r,i,n){return e*=this.itemSize,this.normalized&&(t=wt(t,this.array),r=wt(r,this.array),i=wt(i,this.array),n=wt(n,this.array)),this.array[e+0]=t,this.array[e+1]=r,this.array[e+2]=i,this.array[e+3]=n,this}onUpload(e){return this.onUploadCallback=e,this}clone(){return new this.constructor(this.array,this.itemSize).copy(this)}toJSON(){let e={itemSize:this.itemSize,type:this.array.constructor.name,array:Array.from(this.array),normalized:this.normalized};return this.name!==""&&(e.name=this.name),this.usage!==zc&&(e.usage=this.usage),e}},id=class extends sr{constructor(e,t,r){super(new Uint16Array(e),t,r)}},nd=class extends sr{constructor(e,t,r){super(new Uint32Array(e),t,r)}},oi=class extends sr{constructor(e,t,r){super(new Float32Array(e),t,r)}},Pf=0,Dt=new pt,qo=new kt,Ni=new F,Pt=new vn,ln=new vn,ht=new F,bn=class ad extends ji{constructor(){super(),this.isBufferGeometry=!0,Object.defineProperty(this,"id",{value:Pf++}),this.uuid=gn(),this.name="",this.type="BufferGeometry",this.index=null,this.indirect=null,this.attributes={},this.morphAttributes={},this.morphTargetsRelative=!1,this.groups=[],this.boundingBox=null,this.boundingSphere=null,this.drawRange={start:0,count:1/0},this.userData={}}getIndex(){return this.index}setIndex(t){return Array.isArray(t)?this.index=new(Ju(t)?nd:id)(t,1):this.index=t,this}setIndirect(t){return this.indirect=t,this}getIndirect(){return this.indirect}getAttribute(t){return this.attributes[t]}setAttribute(t,r){return this.attributes[t]=r,this}deleteAttribute(t){return delete this.attributes[t],this}hasAttribute(t){return this.attributes[t]!==void 0}addGroup(t,r,i=0){this.groups.push({start:t,count:r,materialIndex:i})}clearGroups(){this.groups=[]}setDrawRange(t,r){this.drawRange.start=t,this.drawRange.count=r}applyMatrix4(t){let r=this.attributes.position;r!==void 0&&(r.applyMatrix4(t),r.needsUpdate=!0);let i=this.attributes.normal;if(i!==void 0){let a=new Be().getNormalMatrix(t);i.applyNormalMatrix(a),i.needsUpdate=!0}let n=this.attributes.tangent;return n!==void 0&&(n.transformDirection(t),n.needsUpdate=!0),this.boundingBox!==null&&this.computeBoundingBox(),this.boundingSphere!==null&&this.computeBoundingSphere(),this}applyQuaternion(t){return Dt.makeRotationFromQuaternion(t),this.applyMatrix4(Dt),this}rotateX(t){return Dt.makeRotationX(t),this.applyMatrix4(Dt),this}rotateY(t){return Dt.makeRotationY(t),this.applyMatrix4(Dt),this}rotateZ(t){return Dt.makeRotationZ(t),this.applyMatrix4(Dt),this}translate(t,r,i){return Dt.makeTranslation(t,r,i),this.applyMatrix4(Dt),this}scale(t,r,i){return Dt.makeScale(t,r,i),this.applyMatrix4(Dt),this}lookAt(t){return qo.lookAt(t),qo.updateMatrix(),this.applyMatrix4(qo.matrix),this}center(){return this.computeBoundingBox(),this.boundingBox.getCenter(Ni).negate(),this.translate(Ni.x,Ni.y,Ni.z),this}setFromPoints(t){let r=this.getAttribute("position");if(r===void 0){let i=[];for(let n=0,a=t.length;n<a;n++){let o=t[n];i.push(o.x,o.y,o.z||0)}this.setAttribute("position",new oi(i,3))}else{let i=Math.min(t.length,r.count);for(let n=0;n<i;n++){let a=t[n];r.setXYZ(n,a.x,a.y,a.z||0)}t.length>r.count&&console.warn("THREE.BufferGeometry: Buffer size too small for points data. Use .dispose() and create a new geometry."),r.needsUpdate=!0}return this}computeBoundingBox(){this.boundingBox===null&&(this.boundingBox=new vn);let t=this.attributes.position,r=this.morphAttributes.position;if(t&&t.isGLBufferAttribute){console.error("THREE.BufferGeometry.computeBoundingBox(): GLBufferAttribute requires a manual bounding box.",this),this.boundingBox.set(new F(-1/0,-1/0,-1/0),new F(1/0,1/0,1/0));return}if(t!==void 0){if(this.boundingBox.setFromBufferAttribute(t),r)for(let i=0,n=r.length;i<n;i++){let a=r[i];Pt.setFromBufferAttribute(a),this.morphTargetsRelative?(ht.addVectors(this.boundingBox.min,Pt.min),this.boundingBox.expandByPoint(ht),ht.addVectors(this.boundingBox.max,Pt.max),this.boundingBox.expandByPoint(ht)):(this.boundingBox.expandByPoint(Pt.min),this.boundingBox.expandByPoint(Pt.max))}}else this.boundingBox.makeEmpty();(isNaN(this.boundingBox.min.x)||isNaN(this.boundingBox.min.y)||isNaN(this.boundingBox.min.z))&&console.error('THREE.BufferGeometry.computeBoundingBox(): Computed min/max have NaN values. The "position" attribute is likely to have NaN values.',this)}computeBoundingSphere(){this.boundingSphere===null&&(this.boundingSphere=new rl);let t=this.attributes.position,r=this.morphAttributes.position;if(t&&t.isGLBufferAttribute){console.error("THREE.BufferGeometry.computeBoundingSphere(): GLBufferAttribute requires a manual bounding sphere.",this),this.boundingSphere.set(new F,1/0);return}if(t){let i=this.boundingSphere.center;if(Pt.setFromBufferAttribute(t),r)for(let a=0,o=r.length;a<o;a++){let s=r[a];ln.setFromBufferAttribute(s),this.morphTargetsRelative?(ht.addVectors(Pt.min,ln.min),Pt.expandByPoint(ht),ht.addVectors(Pt.max,ln.max),Pt.expandByPoint(ht)):(Pt.expandByPoint(ln.min),Pt.expandByPoint(ln.max))}Pt.getCenter(i);let n=0;for(let a=0,o=t.count;a<o;a++)ht.fromBufferAttribute(t,a),n=Math.max(n,i.distanceToSquared(ht));if(r)for(let a=0,o=r.length;a<o;a++){let s=r[a],c=this.morphTargetsRelative;for(let u=0,l=s.count;u<l;u++)ht.fromBufferAttribute(s,u),c&&(Ni.fromBufferAttribute(t,u),ht.add(Ni)),n=Math.max(n,i.distanceToSquared(ht))}this.boundingSphere.radius=Math.sqrt(n),isNaN(this.boundingSphere.radius)&&console.error('THREE.BufferGeometry.computeBoundingSphere(): Computed radius is NaN. The "position" attribute is likely to have NaN values.',this)}}computeTangents(){let t=this.index,r=this.attributes;if(t===null||r.position===void 0||r.normal===void 0||r.uv===void 0){console.error("THREE.BufferGeometry: .computeTangents() failed. Missing required attributes (index, position, normal or uv)");return}let i=r.position,n=r.normal,a=r.uv;this.hasAttribute("tangent")===!1&&this.setAttribute("tangent",new sr(new Float32Array(4*i.count),4));let o=this.getAttribute("tangent"),s=[],c=[];for(let U=0;U<i.count;U++)s[U]=new F,c[U]=new F;let u=new F,l=new F,d=new F,h=new Ye,m=new Ye,g=new Ye,_=new F,f=new F;function p(U,S,x){u.fromBufferAttribute(i,U),l.fromBufferAttribute(i,S),d.fromBufferAttribute(i,x),h.fromBufferAttribute(a,U),m.fromBufferAttribute(a,S),g.fromBufferAttribute(a,x),l.sub(u),d.sub(u),m.sub(h),g.sub(h);let M=1/(m.x*g.y-g.x*m.y);isFinite(M)&&(_.copy(l).multiplyScalar(g.y).addScaledVector(d,-m.y).multiplyScalar(M),f.copy(d).multiplyScalar(m.x).addScaledVector(l,-g.x).multiplyScalar(M),s[U].add(_),s[S].add(_),s[x].add(_),c[U].add(f),c[S].add(f),c[x].add(f))}let R=this.groups;R.length===0&&(R=[{start:0,count:t.count}]);for(let U=0,S=R.length;U<S;++U){let x=R[U],M=x.start,k=x.count;for(let H=M,V=M+k;H<V;H+=3)p(t.getX(H+0),t.getX(H+1),t.getX(H+2))}let y=new F,A=new F,O=new F,I=new F;function C(U){O.fromBufferAttribute(n,U),I.copy(O);let S=s[U];y.copy(S),y.sub(O.multiplyScalar(O.dot(S))).normalize(),A.crossVectors(I,S);let x=A.dot(c[U])<0?-1:1;o.setXYZW(U,y.x,y.y,y.z,x)}for(let U=0,S=R.length;U<S;++U){let x=R[U],M=x.start,k=x.count;for(let H=M,V=M+k;H<V;H+=3)C(t.getX(H+0)),C(t.getX(H+1)),C(t.getX(H+2))}}computeVertexNormals(){let t=this.index,r=this.getAttribute("position");if(r!==void 0){let i=this.getAttribute("normal");if(i===void 0)i=new sr(new Float32Array(r.count*3),3),this.setAttribute("normal",i);else for(let h=0,m=i.count;h<m;h++)i.setXYZ(h,0,0,0);let n=new F,a=new F,o=new F,s=new F,c=new F,u=new F,l=new F,d=new F;if(t)for(let h=0,m=t.count;h<m;h+=3){let g=t.getX(h+0),_=t.getX(h+1),f=t.getX(h+2);n.fromBufferAttribute(r,g),a.fromBufferAttribute(r,_),o.fromBufferAttribute(r,f),l.subVectors(o,a),d.subVectors(n,a),l.cross(d),s.fromBufferAttribute(i,g),c.fromBufferAttribute(i,_),u.fromBufferAttribute(i,f),s.add(l),c.add(l),u.add(l),i.setXYZ(g,s.x,s.y,s.z),i.setXYZ(_,c.x,c.y,c.z),i.setXYZ(f,u.x,u.y,u.z)}else for(let h=0,m=r.count;h<m;h+=3)n.fromBufferAttribute(r,h+0),a.fromBufferAttribute(r,h+1),o.fromBufferAttribute(r,h+2),l.subVectors(o,a),d.subVectors(n,a),l.cross(d),i.setXYZ(h+0,l.x,l.y,l.z),i.setXYZ(h+1,l.x,l.y,l.z),i.setXYZ(h+2,l.x,l.y,l.z);this.normalizeNormals(),i.needsUpdate=!0}}normalizeNormals(){let t=this.attributes.normal;for(let r=0,i=t.count;r<i;r++)ht.fromBufferAttribute(t,r),ht.normalize(),t.setXYZ(r,ht.x,ht.y,ht.z)}toNonIndexed(){function t(s,c){let u=s.array,l=s.itemSize,d=s.normalized,h=new u.constructor(c.length*l),m=0,g=0;for(let _=0,f=c.length;_<f;_++){s.isInterleavedBufferAttribute?m=c[_]*s.data.stride+s.offset:m=c[_]*l;for(let p=0;p<l;p++)h[g++]=u[m++]}return new sr(h,l,d)}if(this.index===null)return console.warn("THREE.BufferGeometry.toNonIndexed(): BufferGeometry is already non-indexed."),this;let r=new ad,i=this.index.array,n=this.attributes;for(let s in n){let c=n[s],u=t(c,i);r.setAttribute(s,u)}let a=this.morphAttributes;for(let s in a){let c=[],u=a[s];for(let l=0,d=u.length;l<d;l++){let h=u[l],m=t(h,i);c.push(m)}r.morphAttributes[s]=c}r.morphTargetsRelative=this.morphTargetsRelative;let o=this.groups;for(let s=0,c=o.length;s<c;s++){let u=o[s];r.addGroup(u.start,u.count,u.materialIndex)}return r}toJSON(){let t={metadata:{version:4.7,type:"BufferGeometry",generator:"BufferGeometry.toJSON"}};if(t.uuid=this.uuid,t.type=this.type,this.name!==""&&(t.name=this.name),Object.keys(this.userData).length>0&&(t.userData=this.userData),this.parameters!==void 0){let c=this.parameters;for(let u in c)c[u]!==void 0&&(t[u]=c[u]);return t}t.data={attributes:{}};let r=this.index;r!==null&&(t.data.index={type:r.array.constructor.name,array:Array.prototype.slice.call(r.array)});let i=this.attributes;for(let c in i){let u=i[c];t.data.attributes[c]=u.toJSON(t.data)}let n={},a=!1;for(let c in this.morphAttributes){let u=this.morphAttributes[c],l=[];for(let d=0,h=u.length;d<h;d++){let m=u[d];l.push(m.toJSON(t.data))}l.length>0&&(n[c]=l,a=!0)}a&&(t.data.morphAttributes=n,t.data.morphTargetsRelative=this.morphTargetsRelative);let o=this.groups;o.length>0&&(t.data.groups=JSON.parse(JSON.stringify(o)));let s=this.boundingSphere;return s!==null&&(t.data.boundingSphere=s.toJSON()),t}clone(){return new this.constructor().copy(this)}copy(t){this.index=null,this.attributes={},this.morphAttributes={},this.groups=[],this.boundingBox=null,this.boundingSphere=null;let r={};this.name=t.name;let i=t.index;i!==null&&this.setIndex(i.clone());let n=t.attributes;for(let u in n){let l=n[u];this.setAttribute(u,l.clone(r))}let a=t.morphAttributes;for(let u in a){let l=[],d=a[u];for(let h=0,m=d.length;h<m;h++)l.push(d[h].clone(r));this.morphAttributes[u]=l}this.morphTargetsRelative=t.morphTargetsRelative;let o=t.groups;for(let u=0,l=o.length;u<l;u++){let d=o[u];this.addGroup(d.start,d.count,d.materialIndex)}let s=t.boundingBox;s!==null&&(this.boundingBox=s.clone());let c=t.boundingSphere;return c!==null&&(this.boundingSphere=c.clone()),this.drawRange.start=t.drawRange.start,this.drawRange.count=t.drawRange.count,this.userData=t.userData,this}dispose(){this.dispatchEvent({type:"dispose"})}},tu=new pt,Jr=new Ef,sa=new rl,ru=new F,la=new F,ca=new F,ua=new F,Yo=new F,da=new F,iu=new F,ha=new F,Yt=class extends kt{constructor(e=new bn,t=new rd){super(),this.isMesh=!0,this.type="Mesh",this.geometry=e,this.material=t,this.morphTargetDictionary=void 0,this.morphTargetInfluences=void 0,this.count=1,this.updateMorphTargets()}copy(e,t){return super.copy(e,t),e.morphTargetInfluences!==void 0&&(this.morphTargetInfluences=e.morphTargetInfluences.slice()),e.morphTargetDictionary!==void 0&&(this.morphTargetDictionary=Object.assign({},e.morphTargetDictionary)),this.material=Array.isArray(e.material)?e.material.slice():e.material,this.geometry=e.geometry,this}updateMorphTargets(){let e=this.geometry.morphAttributes,t=Object.keys(e);if(t.length>0){let r=e[t[0]];if(r!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let i=0,n=r.length;i<n;i++){let a=r[i].name||String(i);this.morphTargetInfluences.push(0),this.morphTargetDictionary[a]=i}}}}getVertexPosition(e,t){let r=this.geometry,i=r.attributes.position,n=r.morphAttributes.position,a=r.morphTargetsRelative;t.fromBufferAttribute(i,e);let o=this.morphTargetInfluences;if(n&&o){da.set(0,0,0);for(let s=0,c=n.length;s<c;s++){let u=o[s],l=n[s];u!==0&&(Yo.fromBufferAttribute(l,e),a?da.addScaledVector(Yo,u):da.addScaledVector(Yo.sub(t),u))}t.add(da)}return t}raycast(e,t){let r=this.geometry,i=this.material,n=this.matrixWorld;i!==void 0&&(r.boundingSphere===null&&r.computeBoundingSphere(),sa.copy(r.boundingSphere),sa.applyMatrix4(n),Jr.copy(e.ray).recast(e.near),!(sa.containsPoint(Jr.origin)===!1&&(Jr.intersectSphere(sa,ru)===null||Jr.origin.distanceToSquared(ru)>(e.far-e.near)**2))&&(tu.copy(n).invert(),Jr.copy(e.ray).applyMatrix4(tu),!(r.boundingBox!==null&&Jr.intersectsBox(r.boundingBox)===!1)&&this._computeIntersections(e,t,Jr)))}_computeIntersections(e,t,r){let i,n=this.geometry,a=this.material,o=n.index,s=n.attributes.position,c=n.attributes.uv,u=n.attributes.uv1,l=n.attributes.normal,d=n.groups,h=n.drawRange;if(o!==null)if(Array.isArray(a))for(let m=0,g=d.length;m<g;m++){let _=d[m],f=a[_.materialIndex],p=Math.max(_.start,h.start),R=Math.min(o.count,Math.min(_.start+_.count,h.start+h.count));for(let y=p,A=R;y<A;y+=3){let O=o.getX(y),I=o.getX(y+1),C=o.getX(y+2);i=pa(this,f,e,r,c,u,l,O,I,C),i&&(i.faceIndex=Math.floor(y/3),i.face.materialIndex=_.materialIndex,t.push(i))}}else{let m=Math.max(0,h.start),g=Math.min(o.count,h.start+h.count);for(let _=m,f=g;_<f;_+=3){let p=o.getX(_),R=o.getX(_+1),y=o.getX(_+2);i=pa(this,a,e,r,c,u,l,p,R,y),i&&(i.faceIndex=Math.floor(_/3),t.push(i))}}else if(s!==void 0)if(Array.isArray(a))for(let m=0,g=d.length;m<g;m++){let _=d[m],f=a[_.materialIndex],p=Math.max(_.start,h.start),R=Math.min(s.count,Math.min(_.start+_.count,h.start+h.count));for(let y=p,A=R;y<A;y+=3){let O=y,I=y+1,C=y+2;i=pa(this,f,e,r,c,u,l,O,I,C),i&&(i.faceIndex=Math.floor(y/3),i.face.materialIndex=_.materialIndex,t.push(i))}}else{let m=Math.max(0,h.start),g=Math.min(s.count,h.start+h.count);for(let _=m,f=g;_<f;_+=3){let p=_,R=_+1,y=_+2;i=pa(this,a,e,r,c,u,l,p,R,y),i&&(i.faceIndex=Math.floor(_/3),t.push(i))}}}};function Of(e,t,r,i,n,a,o,s){let c;if(t.side===Rt?c=i.intersectTriangle(o,a,n,!0,s):c=i.intersectTriangle(n,a,o,t.side===Vr,s),c===null)return null;ha.copy(s),ha.applyMatrix4(e.matrixWorld);let u=r.ray.origin.distanceTo(ha);return u<r.near||u>r.far?null:{distance:u,point:ha.clone(),object:e}}function pa(e,t,r,i,n,a,o,s,c,u){e.getVertexPosition(s,la),e.getVertexPosition(c,ca),e.getVertexPosition(u,ua);let l=Of(e,t,r,i,la,ca,ua,iu);if(l){let d=new F;sn.getBarycoord(iu,la,ca,ua,d),n&&(l.uv=sn.getInterpolatedAttribute(n,s,c,u,d,new Ye)),a&&(l.uv1=sn.getInterpolatedAttribute(a,s,c,u,d,new Ye)),o&&(l.normal=sn.getInterpolatedAttribute(o,s,c,u,d,new F),l.normal.dot(i.direction)>0&&l.normal.multiplyScalar(-1));let h={a:s,b:c,c:u,normal:new F,materialIndex:0};sn.getNormal(la,ca,ua,h.normal),l.face=h,l.barycoord=d}return l}var xn=class od extends bn{constructor(t=1,r=1,i=1,n=1,a=1,o=1){super(),this.type="BoxGeometry",this.parameters={width:t,height:r,depth:i,widthSegments:n,heightSegments:a,depthSegments:o};let s=this;n=Math.floor(n),a=Math.floor(a),o=Math.floor(o);let c=[],u=[],l=[],d=[],h=0,m=0;g("z","y","x",-1,-1,i,r,t,o,a,0),g("z","y","x",1,-1,i,r,-t,o,a,1),g("x","z","y",1,1,t,i,r,n,o,2),g("x","z","y",1,-1,t,i,-r,n,o,3),g("x","y","z",1,-1,t,r,i,n,a,4),g("x","y","z",-1,-1,t,r,-i,n,a,5),this.setIndex(c),this.setAttribute("position",new oi(u,3)),this.setAttribute("normal",new oi(l,3)),this.setAttribute("uv",new oi(d,2));function g(_,f,p,R,y,A,O,I,C,U,S){let x=A/C,M=O/U,k=A/2,H=O/2,V=I/2,Z=C+1,G=U+1,ee=0,W=0,ie=new F;for(let ce=0;ce<G;ce++){let Pe=ce*M-H;for(let Fe=0;Fe<Z;Fe++){let $e=Fe*x-k;ie[_]=$e*R,ie[f]=Pe*y,ie[p]=V,u.push(ie.x,ie.y,ie.z),ie[_]=0,ie[f]=0,ie[p]=I>0?1:-1,l.push(ie.x,ie.y,ie.z),d.push(Fe/C),d.push(1-ce/U),ee+=1}}for(let ce=0;ce<U;ce++)for(let Pe=0;Pe<C;Pe++){let Fe=h+Pe+Z*ce,$e=h+Pe+Z*(ce+1),We=h+(Pe+1)+Z*(ce+1),j=h+(Pe+1)+Z*ce;c.push(Fe,$e,j),c.push($e,We,j),W+=6}s.addGroup(m,W,S),m+=W,h+=ee}}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}static fromJSON(t){return new od(t.width,t.height,t.depth,t.widthSegments,t.heightSegments,t.depthSegments)}};function Wi(e){let t={};for(let r in e){t[r]={};for(let i in e[r]){let n=e[r][i];n&&(n.isColor||n.isMatrix3||n.isMatrix4||n.isVector2||n.isVector3||n.isVector4||n.isTexture||n.isQuaternion)?n.isRenderTargetTexture?(console.warn("UniformsUtils: Textures of render targets cannot be cloned via cloneUniforms() or mergeUniforms()."),t[r][i]=null):t[r][i]=n.clone():Array.isArray(n)?t[r][i]=n.slice():t[r][i]=n}}return t}function Et(e){let t={};for(let r=0;r<e.length;r++){let i=Wi(e[r]);for(let n in i)t[n]=i[n]}return t}function Lf(e){let t=[];for(let r=0;r<e.length;r++)t.push(e[r].clone());return t}function sd(e){let t=e.getRenderTarget();return t===null?e.outputColorSpace:t.isXRRenderTarget===!0?t.texture.colorSpace:Xe.workingColorSpace}var Uf={clone:Wi,merge:Et},Df=`void main() {
	gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
}`,Ff=`void main() {
	gl_FragColor = vec4( 1.0, 0.0, 0.0, 1.0 );
}`,Hr=class extends _n{constructor(e){super(),this.isShaderMaterial=!0,this.type="ShaderMaterial",this.defines={},this.uniforms={},this.uniformsGroups=[],this.vertexShader=Df,this.fragmentShader=Ff,this.linewidth=1,this.wireframe=!1,this.wireframeLinewidth=1,this.fog=!1,this.lights=!1,this.clipping=!1,this.forceSinglePass=!0,this.extensions={clipCullDistance:!1,multiDraw:!1},this.defaultAttributeValues={color:[1,1,1],uv:[0,0],uv1:[0,0]},this.index0AttributeName=void 0,this.uniformsNeedUpdate=!1,this.glslVersion=null,e!==void 0&&this.setValues(e)}copy(e){return super.copy(e),this.fragmentShader=e.fragmentShader,this.vertexShader=e.vertexShader,this.uniforms=Wi(e.uniforms),this.uniformsGroups=Lf(e.uniformsGroups),this.defines=Object.assign({},e.defines),this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this.fog=e.fog,this.lights=e.lights,this.clipping=e.clipping,this.extensions=Object.assign({},e.extensions),this.glslVersion=e.glslVersion,this}toJSON(e){let t=super.toJSON(e);t.glslVersion=this.glslVersion,t.uniforms={};for(let i in this.uniforms){let n=this.uniforms[i].value;n&&n.isTexture?t.uniforms[i]={type:"t",value:n.toJSON(e).uuid}:n&&n.isColor?t.uniforms[i]={type:"c",value:n.getHex()}:n&&n.isVector2?t.uniforms[i]={type:"v2",value:n.toArray()}:n&&n.isVector3?t.uniforms[i]={type:"v3",value:n.toArray()}:n&&n.isVector4?t.uniforms[i]={type:"v4",value:n.toArray()}:n&&n.isMatrix3?t.uniforms[i]={type:"m3",value:n.toArray()}:n&&n.isMatrix4?t.uniforms[i]={type:"m4",value:n.toArray()}:t.uniforms[i]={value:n}}Object.keys(this.defines).length>0&&(t.defines=this.defines),t.vertexShader=this.vertexShader,t.fragmentShader=this.fragmentShader,t.lights=this.lights,t.clipping=this.clipping;let r={};for(let i in this.extensions)this.extensions[i]===!0&&(r[i]=!0);return Object.keys(r).length>0&&(t.extensions=r),t}},ld=class extends kt{constructor(){super(),this.isCamera=!0,this.type="Camera",this.matrixWorldInverse=new pt,this.projectionMatrix=new pt,this.projectionMatrixInverse=new pt,this.coordinateSystem=or,this._reversedDepth=!1}get reversedDepth(){return this._reversedDepth}copy(e,t){return super.copy(e,t),this.matrixWorldInverse.copy(e.matrixWorldInverse),this.projectionMatrix.copy(e.projectionMatrix),this.projectionMatrixInverse.copy(e.projectionMatrixInverse),this.coordinateSystem=e.coordinateSystem,this}getWorldDirection(e){return super.getWorldDirection(e).negate()}updateMatrixWorld(e){super.updateMatrixWorld(e),this.matrixWorldInverse.copy(this.matrixWorld).invert()}updateWorldMatrix(e,t){super.updateWorldMatrix(e,t),this.matrixWorldInverse.copy(this.matrixWorld).invert()}clone(){return new this.constructor().copy(this)}},Dr=new F,nu=new Ye,au=new Ye,Xt=class extends ld{constructor(e=50,t=1,r=.1,i=2e3){super(),this.isPerspectiveCamera=!0,this.type="PerspectiveCamera",this.fov=e,this.zoom=1,this.near=r,this.far=i,this.focus=10,this.aspect=t,this.view=null,this.filmGauge=35,this.filmOffset=0,this.updateProjectionMatrix()}copy(e,t){return super.copy(e,t),this.fov=e.fov,this.zoom=e.zoom,this.near=e.near,this.far=e.far,this.focus=e.focus,this.aspect=e.aspect,this.view=e.view===null?null:Object.assign({},e.view),this.filmGauge=e.filmGauge,this.filmOffset=e.filmOffset,this}setFocalLength(e){let t=.5*this.getFilmHeight()/e;this.fov=Xs*2*Math.atan(t),this.updateProjectionMatrix()}getFocalLength(){let e=Math.tan(wo*.5*this.fov);return .5*this.getFilmHeight()/e}getEffectiveFOV(){return Xs*2*Math.atan(Math.tan(wo*.5*this.fov)/this.zoom)}getFilmWidth(){return this.filmGauge*Math.min(this.aspect,1)}getFilmHeight(){return this.filmGauge/Math.max(this.aspect,1)}getViewBounds(e,t,r){Dr.set(-1,-1,.5).applyMatrix4(this.projectionMatrixInverse),t.set(Dr.x,Dr.y).multiplyScalar(-e/Dr.z),Dr.set(1,1,.5).applyMatrix4(this.projectionMatrixInverse),r.set(Dr.x,Dr.y).multiplyScalar(-e/Dr.z)}getViewSize(e,t){return this.getViewBounds(e,nu,au),t.subVectors(au,nu)}setViewOffset(e,t,r,i,n,a){this.aspect=e/t,this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=e,this.view.fullHeight=t,this.view.offsetX=r,this.view.offsetY=i,this.view.width=n,this.view.height=a,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){let e=this.near,t=e*Math.tan(wo*.5*this.fov)/this.zoom,r=2*t,i=this.aspect*r,n=-.5*i,a=this.view;if(this.view!==null&&this.view.enabled){let s=a.fullWidth,c=a.fullHeight;n+=a.offsetX*i/s,t-=a.offsetY*r/c,i*=a.width/s,r*=a.height/c}let o=this.filmOffset;o!==0&&(n+=e*o/this.getFilmWidth()),this.projectionMatrix.makePerspective(n,n+i,t,t-r,e,this.far,this.coordinateSystem,this.reversedDepth),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(e){let t=super.toJSON(e);return t.object.fov=this.fov,t.object.zoom=this.zoom,t.object.near=this.near,t.object.far=this.far,t.object.focus=this.focus,t.object.aspect=this.aspect,this.view!==null&&(t.object.view=Object.assign({},this.view)),t.object.filmGauge=this.filmGauge,t.object.filmOffset=this.filmOffset,t}},Pi=-90,Oi=1,kf=class extends kt{constructor(e,t,r){super(),this.type="CubeCamera",this.renderTarget=r,this.coordinateSystem=null,this.activeMipmapLevel=0;let i=new Xt(Pi,Oi,e,t);i.layers=this.layers,this.add(i);let n=new Xt(Pi,Oi,e,t);n.layers=this.layers,this.add(n);let a=new Xt(Pi,Oi,e,t);a.layers=this.layers,this.add(a);let o=new Xt(Pi,Oi,e,t);o.layers=this.layers,this.add(o);let s=new Xt(Pi,Oi,e,t);s.layers=this.layers,this.add(s);let c=new Xt(Pi,Oi,e,t);c.layers=this.layers,this.add(c)}updateCoordinateSystem(){let e=this.coordinateSystem,t=this.children.concat(),[r,i,n,a,o,s]=t;for(let c of t)this.remove(c);if(e===or)r.up.set(0,1,0),r.lookAt(1,0,0),i.up.set(0,1,0),i.lookAt(-1,0,0),n.up.set(0,0,-1),n.lookAt(0,1,0),a.up.set(0,0,1),a.lookAt(0,-1,0),o.up.set(0,1,0),o.lookAt(0,0,1),s.up.set(0,1,0),s.lookAt(0,0,-1);else if(e===Ca)r.up.set(0,-1,0),r.lookAt(-1,0,0),i.up.set(0,-1,0),i.lookAt(1,0,0),n.up.set(0,0,1),n.lookAt(0,1,0),a.up.set(0,0,-1),a.lookAt(0,-1,0),o.up.set(0,-1,0),o.lookAt(0,0,1),s.up.set(0,-1,0),s.lookAt(0,0,-1);else throw new Error("THREE.CubeCamera.updateCoordinateSystem(): Invalid coordinate system: "+e);for(let c of t)this.add(c),c.updateMatrixWorld()}update(e,t){this.parent===null&&this.updateMatrixWorld();let{renderTarget:r,activeMipmapLevel:i}=this;this.coordinateSystem!==e.coordinateSystem&&(this.coordinateSystem=e.coordinateSystem,this.updateCoordinateSystem());let[n,a,o,s,c,u]=this.children,l=e.getRenderTarget(),d=e.getActiveCubeFace(),h=e.getActiveMipmapLevel(),m=e.xr.enabled;e.xr.enabled=!1;let g=r.texture.generateMipmaps;r.texture.generateMipmaps=!1,e.setRenderTarget(r,0,i),e.render(t,n),e.setRenderTarget(r,1,i),e.render(t,a),e.setRenderTarget(r,2,i),e.render(t,o),e.setRenderTarget(r,3,i),e.render(t,s),e.setRenderTarget(r,4,i),e.render(t,c),r.texture.generateMipmaps=g,e.setRenderTarget(r,5,i),e.render(t,u),e.setRenderTarget(l,d,h),e.xr.enabled=m,r.texture.needsPMREMUpdate=!0}},cd=class extends cr{constructor(e=[],t=zi,r,i,n,a,o,s,c,u){super(e,t,r,i,n,a,o,s,c,u),this.isCubeTexture=!0,this.flipY=!1}get images(){return this.image}set images(e){this.image=e}},Bf=class extends li{constructor(e=1,t={}){super(e,e,t),this.isWebGLCubeRenderTarget=!0;let r={width:e,height:e,depth:1},i=[r,r,r,r,r,r];this.texture=new cd(i),this._setTextureOptions(t),this.texture.isRenderTargetTexture=!0}fromEquirectangularTexture(e,t){this.texture.type=t.type,this.texture.colorSpace=t.colorSpace,this.texture.generateMipmaps=t.generateMipmaps,this.texture.minFilter=t.minFilter,this.texture.magFilter=t.magFilter;let r={uniforms:{tEquirect:{value:null}},vertexShader:`

				varying vec3 vWorldDirection;

				vec3 transformDirection( in vec3 dir, in mat4 matrix ) {

					return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );

				}

				void main() {

					vWorldDirection = transformDirection( position, modelMatrix );

					#include <begin_vertex>
					#include <project_vertex>

				}
			`,fragmentShader:`

				uniform sampler2D tEquirect;

				varying vec3 vWorldDirection;

				#include <common>

				void main() {

					vec3 direction = normalize( vWorldDirection );

					vec2 sampleUV = equirectUv( direction );

					gl_FragColor = texture2D( tEquirect, sampleUV );

				}
			`},i=new xn(5,5,5),n=new Hr({name:"CubemapFromEquirect",uniforms:Wi(r.uniforms),vertexShader:r.vertexShader,fragmentShader:r.fragmentShader,side:Rt,blending:kr});n.uniforms.tEquirect.value=t;let a=new Yt(i,n),o=t.minFilter;return t.minFilter===ai&&(t.minFilter=ar),new kf(1,10,this).update(e,a),t.minFilter=o,a.geometry.dispose(),a.material.dispose(),this}clear(e,t=!0,r=!0,i=!0){let n=e.getRenderTarget();for(let a=0;a<6;a++)e.setRenderTarget(this,a),e.clear(t,r,i);e.setRenderTarget(n)}},fa=class extends kt{constructor(){super(),this.isGroup=!0,this.type="Group"}},Vf={type:"move"},Ko=class{constructor(){this._targetRay=null,this._grip=null,this._hand=null}getHandSpace(){return this._hand===null&&(this._hand=new fa,this._hand.matrixAutoUpdate=!1,this._hand.visible=!1,this._hand.joints={},this._hand.inputState={pinching:!1}),this._hand}getTargetRaySpace(){return this._targetRay===null&&(this._targetRay=new fa,this._targetRay.matrixAutoUpdate=!1,this._targetRay.visible=!1,this._targetRay.hasLinearVelocity=!1,this._targetRay.linearVelocity=new F,this._targetRay.hasAngularVelocity=!1,this._targetRay.angularVelocity=new F),this._targetRay}getGripSpace(){return this._grip===null&&(this._grip=new fa,this._grip.matrixAutoUpdate=!1,this._grip.visible=!1,this._grip.hasLinearVelocity=!1,this._grip.linearVelocity=new F,this._grip.hasAngularVelocity=!1,this._grip.angularVelocity=new F),this._grip}dispatchEvent(e){return this._targetRay!==null&&this._targetRay.dispatchEvent(e),this._grip!==null&&this._grip.dispatchEvent(e),this._hand!==null&&this._hand.dispatchEvent(e),this}connect(e){if(e&&e.hand){let t=this._hand;if(t)for(let r of e.hand.values())this._getHandJoint(t,r)}return this.dispatchEvent({type:"connected",data:e}),this}disconnect(e){return this.dispatchEvent({type:"disconnected",data:e}),this._targetRay!==null&&(this._targetRay.visible=!1),this._grip!==null&&(this._grip.visible=!1),this._hand!==null&&(this._hand.visible=!1),this}update(e,t,r){let i=null,n=null,a=null,o=this._targetRay,s=this._grip,c=this._hand;if(e&&t.session.visibilityState!=="visible-blurred"){if(c&&e.hand){a=!0;for(let g of e.hand.values()){let _=t.getJointPose(g,r),f=this._getHandJoint(c,g);_!==null&&(f.matrix.fromArray(_.transform.matrix),f.matrix.decompose(f.position,f.rotation,f.scale),f.matrixWorldNeedsUpdate=!0,f.jointRadius=_.radius),f.visible=_!==null}let u=c.joints["index-finger-tip"],l=c.joints["thumb-tip"],d=u.position.distanceTo(l.position),h=.02,m=.005;c.inputState.pinching&&d>h+m?(c.inputState.pinching=!1,this.dispatchEvent({type:"pinchend",handedness:e.handedness,target:this})):!c.inputState.pinching&&d<=h-m&&(c.inputState.pinching=!0,this.dispatchEvent({type:"pinchstart",handedness:e.handedness,target:this}))}else s!==null&&e.gripSpace&&(n=t.getPose(e.gripSpace,r),n!==null&&(s.matrix.fromArray(n.transform.matrix),s.matrix.decompose(s.position,s.rotation,s.scale),s.matrixWorldNeedsUpdate=!0,n.linearVelocity?(s.hasLinearVelocity=!0,s.linearVelocity.copy(n.linearVelocity)):s.hasLinearVelocity=!1,n.angularVelocity?(s.hasAngularVelocity=!0,s.angularVelocity.copy(n.angularVelocity)):s.hasAngularVelocity=!1));o!==null&&(i=t.getPose(e.targetRaySpace,r),i===null&&n!==null&&(i=n),i!==null&&(o.matrix.fromArray(i.transform.matrix),o.matrix.decompose(o.position,o.rotation,o.scale),o.matrixWorldNeedsUpdate=!0,i.linearVelocity?(o.hasLinearVelocity=!0,o.linearVelocity.copy(i.linearVelocity)):o.hasLinearVelocity=!1,i.angularVelocity?(o.hasAngularVelocity=!0,o.angularVelocity.copy(i.angularVelocity)):o.hasAngularVelocity=!1,this.dispatchEvent(Vf)))}return o!==null&&(o.visible=i!==null),s!==null&&(s.visible=n!==null),c!==null&&(c.visible=a!==null),this}_getHandJoint(e,t){if(e.joints[t.jointName]===void 0){let r=new fa;r.matrixAutoUpdate=!1,r.visible=!1,e.joints[t.jointName]=r,e.add(r)}return e.joints[t.jointName]}},ud=class extends kt{constructor(){super(),this.isScene=!0,this.type="Scene",this.background=null,this.environment=null,this.fog=null,this.backgroundBlurriness=0,this.backgroundIntensity=1,this.backgroundRotation=new zr,this.environmentIntensity=1,this.environmentRotation=new zr,this.overrideMaterial=null,typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}copy(e,t){return super.copy(e,t),e.background!==null&&(this.background=e.background.clone()),e.environment!==null&&(this.environment=e.environment.clone()),e.fog!==null&&(this.fog=e.fog.clone()),this.backgroundBlurriness=e.backgroundBlurriness,this.backgroundIntensity=e.backgroundIntensity,this.backgroundRotation.copy(e.backgroundRotation),this.environmentIntensity=e.environmentIntensity,this.environmentRotation.copy(e.environmentRotation),e.overrideMaterial!==null&&(this.overrideMaterial=e.overrideMaterial.clone()),this.matrixAutoUpdate=e.matrixAutoUpdate,this}toJSON(e){let t=super.toJSON(e);return this.fog!==null&&(t.object.fog=this.fog.toJSON()),this.backgroundBlurriness>0&&(t.object.backgroundBlurriness=this.backgroundBlurriness),this.backgroundIntensity!==1&&(t.object.backgroundIntensity=this.backgroundIntensity),t.object.backgroundRotation=this.backgroundRotation.toArray(),this.environmentIntensity!==1&&(t.object.environmentIntensity=this.environmentIntensity),t.object.environmentRotation=this.environmentRotation.toArray(),t}},Jo=new F,zf=new F,Hf=new Be,ei=class{constructor(e=new F(1,0,0),t=0){this.isPlane=!0,this.normal=e,this.constant=t}set(e,t){return this.normal.copy(e),this.constant=t,this}setComponents(e,t,r,i){return this.normal.set(e,t,r),this.constant=i,this}setFromNormalAndCoplanarPoint(e,t){return this.normal.copy(e),this.constant=-t.dot(this.normal),this}setFromCoplanarPoints(e,t,r){let i=Jo.subVectors(r,t).cross(zf.subVectors(e,t)).normalize();return this.setFromNormalAndCoplanarPoint(i,e),this}copy(e){return this.normal.copy(e.normal),this.constant=e.constant,this}normalize(){let e=1/this.normal.length();return this.normal.multiplyScalar(e),this.constant*=e,this}negate(){return this.constant*=-1,this.normal.negate(),this}distanceToPoint(e){return this.normal.dot(e)+this.constant}distanceToSphere(e){return this.distanceToPoint(e.center)-e.radius}projectPoint(e,t){return t.copy(e).addScaledVector(this.normal,-this.distanceToPoint(e))}intersectLine(e,t){let r=e.delta(Jo),i=this.normal.dot(r);if(i===0)return this.distanceToPoint(e.start)===0?t.copy(e.start):null;let n=-(e.start.dot(this.normal)+this.constant)/i;return n<0||n>1?null:t.copy(e.start).addScaledVector(r,n)}intersectsLine(e){let t=this.distanceToPoint(e.start),r=this.distanceToPoint(e.end);return t<0&&r>0||r<0&&t>0}intersectsBox(e){return e.intersectsPlane(this)}intersectsSphere(e){return e.intersectsPlane(this)}coplanarPoint(e){return e.copy(this.normal).multiplyScalar(-this.constant)}applyMatrix4(e,t){let r=t||Hf.getNormalMatrix(e),i=this.coplanarPoint(Jo).applyMatrix4(e),n=this.normal.applyMatrix3(r).normalize();return this.constant=-i.dot(n),this}translate(e){return this.constant-=e.dot(this.normal),this}equals(e){return e.normal.equals(this.normal)&&e.constant===this.constant}clone(){return new this.constructor().copy(this)}},Zr=new rl,Gf=new Ye(.5,.5),ma=new F,il=class{constructor(e=new ei,t=new ei,r=new ei,i=new ei,n=new ei,a=new ei){this.planes=[e,t,r,i,n,a]}set(e,t,r,i,n,a){let o=this.planes;return o[0].copy(e),o[1].copy(t),o[2].copy(r),o[3].copy(i),o[4].copy(n),o[5].copy(a),this}copy(e){let t=this.planes;for(let r=0;r<6;r++)t[r].copy(e.planes[r]);return this}setFromProjectionMatrix(e,t=or,r=!1){let i=this.planes,n=e.elements,a=n[0],o=n[1],s=n[2],c=n[3],u=n[4],l=n[5],d=n[6],h=n[7],m=n[8],g=n[9],_=n[10],f=n[11],p=n[12],R=n[13],y=n[14],A=n[15];if(i[0].setComponents(c-a,h-u,f-m,A-p).normalize(),i[1].setComponents(c+a,h+u,f+m,A+p).normalize(),i[2].setComponents(c+o,h+l,f+g,A+R).normalize(),i[3].setComponents(c-o,h-l,f-g,A-R).normalize(),r)i[4].setComponents(s,d,_,y).normalize(),i[5].setComponents(c-s,h-d,f-_,A-y).normalize();else if(i[4].setComponents(c-s,h-d,f-_,A-y).normalize(),t===or)i[5].setComponents(c+s,h+d,f+_,A+y).normalize();else if(t===Ca)i[5].setComponents(s,d,_,y).normalize();else throw new Error("THREE.Frustum.setFromProjectionMatrix(): Invalid coordinate system: "+t);return this}intersectsObject(e){if(e.boundingSphere!==void 0)e.boundingSphere===null&&e.computeBoundingSphere(),Zr.copy(e.boundingSphere).applyMatrix4(e.matrixWorld);else{let t=e.geometry;t.boundingSphere===null&&t.computeBoundingSphere(),Zr.copy(t.boundingSphere).applyMatrix4(e.matrixWorld)}return this.intersectsSphere(Zr)}intersectsSprite(e){Zr.center.set(0,0,0);let t=Gf.distanceTo(e.center);return Zr.radius=.7071067811865476+t,Zr.applyMatrix4(e.matrixWorld),this.intersectsSphere(Zr)}intersectsSphere(e){let t=this.planes,r=e.center,i=-e.radius;for(let n=0;n<6;n++)if(t[n].distanceToPoint(r)<i)return!1;return!0}intersectsBox(e){let t=this.planes;for(let r=0;r<6;r++){let i=t[r];if(ma.x=i.normal.x>0?e.max.x:e.min.x,ma.y=i.normal.y>0?e.max.y:e.min.y,ma.z=i.normal.z>0?e.max.z:e.min.z,i.distanceToPoint(ma)<0)return!1}return!0}containsPoint(e){let t=this.planes;for(let r=0;r<6;r++)if(t[r].distanceToPoint(e)<0)return!1;return!0}clone(){return new this.constructor().copy(this)}},dd=class extends cr{constructor(e,t,r=si,i,n,a,o=Kt,s=Kt,c,u=hn,l=1){if(u!==hn&&u!==pn)throw new Error("DepthTexture format must be either THREE.DepthFormat or THREE.DepthStencilFormat");let d={width:e,height:t,depth:l};super(d,i,n,a,o,s,u,r,c),this.isDepthTexture=!0,this.flipY=!1,this.generateMipmaps=!1,this.compareFunction=null}copy(e){return super.copy(e),this.source=new tl(Object.assign({},e.image)),this.compareFunction=e.compareFunction,this}toJSON(e){let t=super.toJSON(e);return this.compareFunction!==null&&(t.compareFunction=this.compareFunction),t}},hd=class extends cr{constructor(e=null){super(),this.sourceTexture=e,this.isExternalTexture=!0}copy(e){return super.copy(e),this.sourceTexture=e.sourceTexture,this}},pd=class fd extends bn{constructor(t=1,r=1,i=1,n=1){super(),this.type="PlaneGeometry",this.parameters={width:t,height:r,widthSegments:i,heightSegments:n};let a=t/2,o=r/2,s=Math.floor(i),c=Math.floor(n),u=s+1,l=c+1,d=t/s,h=r/c,m=[],g=[],_=[],f=[];for(let p=0;p<l;p++){let R=p*h-o;for(let y=0;y<u;y++){let A=y*d-a;g.push(A,-R,0),_.push(0,0,1),f.push(y/s),f.push(1-p/c)}}for(let p=0;p<c;p++)for(let R=0;R<s;R++){let y=R+u*p,A=R+u*(p+1),O=R+1+u*(p+1),I=R+1+u*p;m.push(y,A,I),m.push(A,O,I)}this.setIndex(m),this.setAttribute("position",new oi(g,3)),this.setAttribute("normal",new oi(_,3)),this.setAttribute("uv",new oi(f,2))}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}static fromJSON(t){return new fd(t.width,t.height,t.widthSegments,t.heightSegments)}},md=class extends _n{constructor(e){super(),this.isMeshStandardMaterial=!0,this.type="MeshStandardMaterial",this.defines={STANDARD:""},this.color=new qe(16777215),this.roughness=1,this.metalness=0,this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.emissive=new qe(0),this.emissiveIntensity=1,this.emissiveMap=null,this.bumpMap=null,this.bumpScale=1,this.normalMap=null,this.normalMapType=ju,this.normalScale=new Ye(1,1),this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.roughnessMap=null,this.metalnessMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new zr,this.envMapIntensity=1,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.flatShading=!1,this.fog=!0,this.setValues(e)}copy(e){return super.copy(e),this.defines={STANDARD:""},this.color.copy(e.color),this.roughness=e.roughness,this.metalness=e.metalness,this.map=e.map,this.lightMap=e.lightMap,this.lightMapIntensity=e.lightMapIntensity,this.aoMap=e.aoMap,this.aoMapIntensity=e.aoMapIntensity,this.emissive.copy(e.emissive),this.emissiveMap=e.emissiveMap,this.emissiveIntensity=e.emissiveIntensity,this.bumpMap=e.bumpMap,this.bumpScale=e.bumpScale,this.normalMap=e.normalMap,this.normalMapType=e.normalMapType,this.normalScale.copy(e.normalScale),this.displacementMap=e.displacementMap,this.displacementScale=e.displacementScale,this.displacementBias=e.displacementBias,this.roughnessMap=e.roughnessMap,this.metalnessMap=e.metalnessMap,this.alphaMap=e.alphaMap,this.envMap=e.envMap,this.envMapRotation.copy(e.envMapRotation),this.envMapIntensity=e.envMapIntensity,this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this.wireframeLinecap=e.wireframeLinecap,this.wireframeLinejoin=e.wireframeLinejoin,this.flatShading=e.flatShading,this.fog=e.fog,this}},Wf=class extends _n{constructor(e){super(),this.isMeshDepthMaterial=!0,this.type="MeshDepthMaterial",this.depthPacking=rf,this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.wireframe=!1,this.wireframeLinewidth=1,this.setValues(e)}copy(e){return super.copy(e),this.depthPacking=e.depthPacking,this.map=e.map,this.alphaMap=e.alphaMap,this.displacementMap=e.displacementMap,this.displacementScale=e.displacementScale,this.displacementBias=e.displacementBias,this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this}},jf=class extends _n{constructor(e){super(),this.isMeshDistanceMaterial=!0,this.type="MeshDistanceMaterial",this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.setValues(e)}copy(e){return super.copy(e),this.map=e.map,this.alphaMap=e.alphaMap,this.displacementMap=e.displacementMap,this.displacementScale=e.displacementScale,this.displacementBias=e.displacementBias,this}};function ga(e,t){return!e||e.constructor===t?e:typeof t.BYTES_PER_ELEMENT=="number"?new t(e):Array.prototype.slice.call(e)}function Xf(e){return ArrayBuffer.isView(e)&&!(e instanceof DataView)}var Pa=class{constructor(e,t,r,i){this.parameterPositions=e,this._cachedIndex=0,this.resultBuffer=i!==void 0?i:new t.constructor(r),this.sampleValues=t,this.valueSize=r,this.settings=null,this.DefaultSettings_={}}evaluate(e){let t=this.parameterPositions,r=this._cachedIndex,i=t[r],n=t[r-1];r:{e:{let a;t:{i:if(!(e<i)){for(let o=r+2;;){if(i===void 0){if(e<n)break i;return r=t.length,this._cachedIndex=r,this.copySampleValue_(r-1)}if(r===o)break;if(n=i,i=t[++r],e<i)break e}a=t.length;break t}if(!(e>=n)){let o=t[1];e<o&&(r=2,n=o);for(let s=r-2;;){if(n===void 0)return this._cachedIndex=0,this.copySampleValue_(0);if(r===s)break;if(i=n,n=t[--r-1],e>=n)break e}a=r,r=0;break t}break r}for(;r<a;){let o=r+a>>>1;e<t[o]?a=o:r=o+1}if(i=t[r],n=t[r-1],n===void 0)return this._cachedIndex=0,this.copySampleValue_(0);if(i===void 0)return r=t.length,this._cachedIndex=r,this.copySampleValue_(r-1)}this._cachedIndex=r,this.intervalChanged_(r,n,i)}return this.interpolate_(r,n,e,i)}getSettings_(){return this.settings||this.DefaultSettings_}copySampleValue_(e){let t=this.resultBuffer,r=this.sampleValues,i=this.valueSize,n=e*i;for(let a=0;a!==i;++a)t[a]=r[n+a];return t}interpolate_(){throw new Error("call to abstract method")}intervalChanged_(){}},qf=class extends Pa{constructor(e,t,r,i){super(e,t,r,i),this._weightPrev=-0,this._offsetPrev=-0,this._weightNext=-0,this._offsetNext=-0,this.DefaultSettings_={endingStart:Fc,endingEnd:Fc}}intervalChanged_(e,t,r){let i=this.parameterPositions,n=e-2,a=e+1,o=i[n],s=i[a];if(o===void 0)switch(this.getSettings_().endingStart){case kc:n=e,o=2*t-r;break;case Bc:n=i.length-2,o=t+i[n]-i[n+1];break;default:n=e,o=r}if(s===void 0)switch(this.getSettings_().endingEnd){case kc:a=e,s=2*r-t;break;case Bc:a=1,s=r+i[1]-i[0];break;default:a=e-1,s=t}let c=(r-t)*.5,u=this.valueSize;this._weightPrev=c/(t-o),this._weightNext=c/(s-r),this._offsetPrev=n*u,this._offsetNext=a*u}interpolate_(e,t,r,i){let n=this.resultBuffer,a=this.sampleValues,o=this.valueSize,s=e*o,c=s-o,u=this._offsetPrev,l=this._offsetNext,d=this._weightPrev,h=this._weightNext,m=(r-t)/(i-t),g=m*m,_=g*m,f=-d*_+2*d*g-d*m,p=(1+d)*_+(-1.5-2*d)*g+(-.5+d)*m+1,R=(-1-h)*_+(1.5+h)*g+.5*m,y=h*_-h*g;for(let A=0;A!==o;++A)n[A]=f*a[u+A]+p*a[c+A]+R*a[s+A]+y*a[l+A];return n}},Yf=class extends Pa{constructor(e,t,r,i){super(e,t,r,i)}interpolate_(e,t,r,i){let n=this.resultBuffer,a=this.sampleValues,o=this.valueSize,s=e*o,c=s-o,u=(r-t)/(i-t),l=1-u;for(let d=0;d!==o;++d)n[d]=a[c+d]*l+a[s+d]*u;return n}},Kf=class extends Pa{constructor(e,t,r,i){super(e,t,r,i)}interpolate_(e){return this.copySampleValue_(e-1)}},ur=class{constructor(e,t,r,i){if(e===void 0)throw new Error("THREE.KeyframeTrack: track name is undefined");if(t===void 0||t.length===0)throw new Error("THREE.KeyframeTrack: no keyframes in track named "+e);this.name=e,this.times=ga(t,this.TimeBufferType),this.values=ga(r,this.ValueBufferType),this.setInterpolation(i||this.DefaultInterpolation)}static toJSON(e){let t=e.constructor,r;if(t.toJSON!==this.toJSON)r=t.toJSON(e);else{r={name:e.name,times:ga(e.times,Array),values:ga(e.values,Array)};let i=e.getInterpolation();i!==e.DefaultInterpolation&&(r.interpolation=i)}return r.type=e.ValueTypeName,r}InterpolantFactoryMethodDiscrete(e){return new Kf(this.times,this.values,this.getValueSize(),e)}InterpolantFactoryMethodLinear(e){return new Yf(this.times,this.values,this.getValueSize(),e)}InterpolantFactoryMethodSmooth(e){return new qf(this.times,this.values,this.getValueSize(),e)}setInterpolation(e){let t;switch(e){case wa:t=this.InterpolantFactoryMethodDiscrete;break;case js:t=this.InterpolantFactoryMethodLinear;break;case Ao:t=this.InterpolantFactoryMethodSmooth;break}if(t===void 0){let r="unsupported interpolation for "+this.ValueTypeName+" keyframe track named "+this.name;if(this.createInterpolant===void 0)if(e!==this.DefaultInterpolation)this.setInterpolation(this.DefaultInterpolation);else throw new Error(r);return console.warn("THREE.KeyframeTrack:",r),this}return this.createInterpolant=t,this}getInterpolation(){switch(this.createInterpolant){case this.InterpolantFactoryMethodDiscrete:return wa;case this.InterpolantFactoryMethodLinear:return js;case this.InterpolantFactoryMethodSmooth:return Ao}}getValueSize(){return this.values.length/this.times.length}shift(e){if(e!==0){let t=this.times;for(let r=0,i=t.length;r!==i;++r)t[r]+=e}return this}scale(e){if(e!==1){let t=this.times;for(let r=0,i=t.length;r!==i;++r)t[r]*=e}return this}trim(e,t){let r=this.times,i=r.length,n=0,a=i-1;for(;n!==i&&r[n]<e;)++n;for(;a!==-1&&r[a]>t;)--a;if(++a,n!==0||a!==i){n>=a&&(a=Math.max(a,1),n=a-1);let o=this.getValueSize();this.times=r.slice(n,a),this.values=this.values.slice(n*o,a*o)}return this}validate(){let e=!0,t=this.getValueSize();t-Math.floor(t)!==0&&(console.error("THREE.KeyframeTrack: Invalid value size in track.",this),e=!1);let r=this.times,i=this.values,n=r.length;n===0&&(console.error("THREE.KeyframeTrack: Track is empty.",this),e=!1);let a=null;for(let o=0;o!==n;o++){let s=r[o];if(typeof s=="number"&&isNaN(s)){console.error("THREE.KeyframeTrack: Time is not a valid number.",this,o,s),e=!1;break}if(a!==null&&a>s){console.error("THREE.KeyframeTrack: Out of order keys.",this,o,s,a),e=!1;break}a=s}if(i!==void 0&&Xf(i))for(let o=0,s=i.length;o!==s;++o){let c=i[o];if(isNaN(c)){console.error("THREE.KeyframeTrack: Value is not a valid number.",this,o,c),e=!1;break}}return e}optimize(){let e=this.times.slice(),t=this.values.slice(),r=this.getValueSize(),i=this.getInterpolation()===Ao,n=e.length-1,a=1;for(let o=1;o<n;++o){let s=!1,c=e[o],u=e[o+1];if(c!==u&&(o!==1||c!==e[0]))if(i)s=!0;else{let l=o*r,d=l-r,h=l+r;for(let m=0;m!==r;++m){let g=t[l+m];if(g!==t[d+m]||g!==t[h+m]){s=!0;break}}}if(s){if(o!==a){e[a]=e[o];let l=o*r,d=a*r;for(let h=0;h!==r;++h)t[d+h]=t[l+h]}++a}}if(n>0){e[a]=e[n];for(let o=n*r,s=a*r,c=0;c!==r;++c)t[s+c]=t[o+c];++a}return a!==e.length?(this.times=e.slice(0,a),this.values=t.slice(0,a*r)):(this.times=e,this.values=t),this}clone(){let e=this.times.slice(),t=this.values.slice(),r=this.constructor,i=new r(this.name,e,t);return i.createInterpolant=this.createInterpolant,i}};ur.prototype.ValueTypeName="";ur.prototype.TimeBufferType=Float32Array;ur.prototype.ValueBufferType=Float32Array;ur.prototype.DefaultInterpolation=js;var yn=class extends ur{constructor(e,t,r){super(e,t,r)}};yn.prototype.ValueTypeName="bool";yn.prototype.ValueBufferType=Array;yn.prototype.DefaultInterpolation=wa;yn.prototype.InterpolantFactoryMethodLinear=void 0;yn.prototype.InterpolantFactoryMethodSmooth=void 0;var Jf=class extends ur{constructor(e,t,r,i){super(e,t,r,i)}};Jf.prototype.ValueTypeName="color";var Zf=class extends ur{constructor(e,t,r,i){super(e,t,r,i)}};Zf.prototype.ValueTypeName="number";var $f=class extends Pa{constructor(e,t,r,i){super(e,t,r,i)}interpolate_(e,t,r,i){let n=this.resultBuffer,a=this.sampleValues,o=this.valueSize,s=(r-t)/(i-t),c=e*o;for(let u=c+o;c!==u;c+=4)Xi.slerpFlat(n,0,a,c-o,a,c,s);return n}},gd=class extends ur{constructor(e,t,r,i){super(e,t,r,i)}InterpolantFactoryMethodLinear(e){return new $f(this.times,this.values,this.getValueSize(),e)}};gd.prototype.ValueTypeName="quaternion";gd.prototype.InterpolantFactoryMethodSmooth=void 0;var Sn=class extends ur{constructor(e,t,r){super(e,t,r)}};Sn.prototype.ValueTypeName="string";Sn.prototype.ValueBufferType=Array;Sn.prototype.DefaultInterpolation=wa;Sn.prototype.InterpolantFactoryMethodLinear=void 0;Sn.prototype.InterpolantFactoryMethodSmooth=void 0;var Qf=class extends ur{constructor(e,t,r,i){super(e,t,r,i)}};Qf.prototype.ValueTypeName="vector";var em=class{constructor(e,t,r){let i=this,n=!1,a=0,o=0,s,c=[];this.onStart=void 0,this.onLoad=e,this.onProgress=t,this.onError=r,this.abortController=new AbortController,this.itemStart=function(u){o++,n===!1&&i.onStart!==void 0&&i.onStart(u,a,o),n=!0},this.itemEnd=function(u){a++,i.onProgress!==void 0&&i.onProgress(u,a,o),a===o&&(n=!1,i.onLoad!==void 0&&i.onLoad())},this.itemError=function(u){i.onError!==void 0&&i.onError(u)},this.resolveURL=function(u){return s?s(u):u},this.setURLModifier=function(u){return s=u,this},this.addHandler=function(u,l){return c.push(u,l),this},this.removeHandler=function(u){let l=c.indexOf(u);return l!==-1&&c.splice(l,2),this},this.getHandler=function(u){for(let l=0,d=c.length;l<d;l+=2){let h=c[l],m=c[l+1];if(h.global&&(h.lastIndex=0),h.test(u))return m}return null},this.abort=function(){return this.abortController.abort(),this.abortController=new AbortController,this}}},tm=new em,rm=class{constructor(e){this.manager=e!==void 0?e:tm,this.crossOrigin="anonymous",this.withCredentials=!1,this.path="",this.resourcePath="",this.requestHeader={}}load(){}loadAsync(e,t){let r=this;return new Promise(function(i,n){r.load(e,i,t,n)})}parse(){}setCrossOrigin(e){return this.crossOrigin=e,this}setWithCredentials(e){return this.withCredentials=e,this}setPath(e){return this.path=e,this}setResourcePath(e){return this.resourcePath=e,this}setRequestHeader(e){return this.requestHeader=e,this}abort(){return this}};rm.DEFAULT_MATERIAL_NAME="__DEFAULT";var vd=class extends kt{constructor(e,t=1){super(),this.isLight=!0,this.type="Light",this.color=new qe(e),this.intensity=t}dispose(){}copy(e,t){return super.copy(e,t),this.color.copy(e.color),this.intensity=e.intensity,this}toJSON(e){let t=super.toJSON(e);return t.object.color=this.color.getHex(),t.object.intensity=this.intensity,this.groundColor!==void 0&&(t.object.groundColor=this.groundColor.getHex()),this.distance!==void 0&&(t.object.distance=this.distance),this.angle!==void 0&&(t.object.angle=this.angle),this.decay!==void 0&&(t.object.decay=this.decay),this.penumbra!==void 0&&(t.object.penumbra=this.penumbra),this.shadow!==void 0&&(t.object.shadow=this.shadow.toJSON()),this.target!==void 0&&(t.object.target=this.target.uuid),t}},Zo=new pt,ou=new F,su=new F,im=class{constructor(e){this.camera=e,this.intensity=1,this.bias=0,this.normalBias=0,this.radius=1,this.blurSamples=8,this.mapSize=new Ye(512,512),this.mapType=lr,this.map=null,this.mapPass=null,this.matrix=new pt,this.autoUpdate=!0,this.needsUpdate=!1,this._frustum=new il,this._frameExtents=new Ye(1,1),this._viewportCount=1,this._viewports=[new lt(0,0,1,1)]}getViewportCount(){return this._viewportCount}getFrustum(){return this._frustum}updateMatrices(e){let t=this.camera,r=this.matrix;ou.setFromMatrixPosition(e.matrixWorld),t.position.copy(ou),su.setFromMatrixPosition(e.target.matrixWorld),t.lookAt(su),t.updateMatrixWorld(),Zo.multiplyMatrices(t.projectionMatrix,t.matrixWorldInverse),this._frustum.setFromProjectionMatrix(Zo,t.coordinateSystem,t.reversedDepth),t.reversedDepth?r.set(.5,0,0,.5,0,.5,0,.5,0,0,1,0,0,0,0,1):r.set(.5,0,0,.5,0,.5,0,.5,0,0,.5,.5,0,0,0,1),r.multiply(Zo)}getViewport(e){return this._viewports[e]}getFrameExtents(){return this._frameExtents}dispose(){this.map&&this.map.dispose(),this.mapPass&&this.mapPass.dispose()}copy(e){return this.camera=e.camera.clone(),this.intensity=e.intensity,this.bias=e.bias,this.radius=e.radius,this.autoUpdate=e.autoUpdate,this.needsUpdate=e.needsUpdate,this.normalBias=e.normalBias,this.blurSamples=e.blurSamples,this.mapSize.copy(e.mapSize),this}clone(){return new this.constructor().copy(this)}toJSON(){let e={};return this.intensity!==1&&(e.intensity=this.intensity),this.bias!==0&&(e.bias=this.bias),this.normalBias!==0&&(e.normalBias=this.normalBias),this.radius!==1&&(e.radius=this.radius),(this.mapSize.x!==512||this.mapSize.y!==512)&&(e.mapSize=this.mapSize.toArray()),e.camera=this.camera.toJSON(!1).object,delete e.camera.matrix,e}},Oa=class extends ld{constructor(e=-1,t=1,r=1,i=-1,n=.1,a=2e3){super(),this.isOrthographicCamera=!0,this.type="OrthographicCamera",this.zoom=1,this.view=null,this.left=e,this.right=t,this.top=r,this.bottom=i,this.near=n,this.far=a,this.updateProjectionMatrix()}copy(e,t){return super.copy(e,t),this.left=e.left,this.right=e.right,this.top=e.top,this.bottom=e.bottom,this.near=e.near,this.far=e.far,this.zoom=e.zoom,this.view=e.view===null?null:Object.assign({},e.view),this}setViewOffset(e,t,r,i,n,a){this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=e,this.view.fullHeight=t,this.view.offsetX=r,this.view.offsetY=i,this.view.width=n,this.view.height=a,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){let e=(this.right-this.left)/(2*this.zoom),t=(this.top-this.bottom)/(2*this.zoom),r=(this.right+this.left)/2,i=(this.top+this.bottom)/2,n=r-e,a=r+e,o=i+t,s=i-t;if(this.view!==null&&this.view.enabled){let c=(this.right-this.left)/this.view.fullWidth/this.zoom,u=(this.top-this.bottom)/this.view.fullHeight/this.zoom;n+=c*this.view.offsetX,a=n+c*this.view.width,o-=u*this.view.offsetY,s=o-u*this.view.height}this.projectionMatrix.makeOrthographic(n,a,o,s,this.near,this.far,this.coordinateSystem,this.reversedDepth),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(e){let t=super.toJSON(e);return t.object.zoom=this.zoom,t.object.left=this.left,t.object.right=this.right,t.object.top=this.top,t.object.bottom=this.bottom,t.object.near=this.near,t.object.far=this.far,this.view!==null&&(t.object.view=Object.assign({},this.view)),t}},nm=class extends im{constructor(){super(new Oa(-5,5,5,-5,.5,500)),this.isDirectionalLightShadow=!0}},_d=class extends vd{constructor(e,t){super(e,t),this.isDirectionalLight=!0,this.type="DirectionalLight",this.position.copy(kt.DEFAULT_UP),this.updateMatrix(),this.target=new kt,this.shadow=new nm}dispose(){this.shadow.dispose()}copy(e){return super.copy(e),this.target=e.target.clone(),this.shadow=e.shadow.clone(),this}},bd=class extends vd{constructor(e,t){super(e,t),this.isAmbientLight=!0,this.type="AmbientLight"}},am=class extends Xt{constructor(e=[]){super(),this.isArrayCamera=!0,this.isMultiViewCamera=!1,this.cameras=e}},nl="\\[\\]\\.:\\/",om=new RegExp("["+nl+"]","g"),al="[^"+nl+"]",sm="[^"+nl.replace("\\.","")+"]",lm=/((?:WC+[\/:])*)/.source.replace("WC",al),cm=/(WCOD+)?/.source.replace("WCOD",sm),um=/(?:\.(WC+)(?:\[(.+)\])?)?/.source.replace("WC",al),dm=/\.(WC+)(?:\[(.+)\])?/.source.replace("WC",al),hm=new RegExp("^"+lm+cm+um+dm+"$"),pm=["material","materials","bones","map"],fm=class{constructor(e,t,r){let i=r||nt.parseTrackName(t);this._targetGroup=e,this._bindings=e.subscribe_(t,i)}getValue(e,t){this.bind();let r=this._targetGroup.nCachedObjects_,i=this._bindings[r];i!==void 0&&i.getValue(e,t)}setValue(e,t){let r=this._bindings;for(let i=this._targetGroup.nCachedObjects_,n=r.length;i!==n;++i)r[i].setValue(e,t)}bind(){let e=this._bindings;for(let t=this._targetGroup.nCachedObjects_,r=e.length;t!==r;++t)e[t].bind()}unbind(){let e=this._bindings;for(let t=this._targetGroup.nCachedObjects_,r=e.length;t!==r;++t)e[t].unbind()}},nt=class Di{constructor(t,r,i){this.path=r,this.parsedPath=i||Di.parseTrackName(r),this.node=Di.findNode(t,this.parsedPath.nodeName),this.rootNode=t,this.getValue=this._getValue_unbound,this.setValue=this._setValue_unbound}static create(t,r,i){return t&&t.isAnimationObjectGroup?new Di.Composite(t,r,i):new Di(t,r,i)}static sanitizeNodeName(t){return t.replace(/\s/g,"_").replace(om,"")}static parseTrackName(t){let r=hm.exec(t);if(r===null)throw new Error("PropertyBinding: Cannot parse trackName: "+t);let i={nodeName:r[2],objectName:r[3],objectIndex:r[4],propertyName:r[5],propertyIndex:r[6]},n=i.nodeName&&i.nodeName.lastIndexOf(".");if(n!==void 0&&n!==-1){let a=i.nodeName.substring(n+1);pm.indexOf(a)!==-1&&(i.nodeName=i.nodeName.substring(0,n),i.objectName=a)}if(i.propertyName===null||i.propertyName.length===0)throw new Error("PropertyBinding: can not parse propertyName from trackName: "+t);return i}static findNode(t,r){if(r===void 0||r===""||r==="."||r===-1||r===t.name||r===t.uuid)return t;if(t.skeleton){let i=t.skeleton.getBoneByName(r);if(i!==void 0)return i}if(t.children){let i=function(a){for(let o=0;o<a.length;o++){let s=a[o];if(s.name===r||s.uuid===r)return s;let c=i(s.children);if(c)return c}return null},n=i(t.children);if(n)return n}return null}_getValue_unavailable(){}_setValue_unavailable(){}_getValue_direct(t,r){t[r]=this.targetObject[this.propertyName]}_getValue_array(t,r){let i=this.resolvedProperty;for(let n=0,a=i.length;n!==a;++n)t[r++]=i[n]}_getValue_arrayElement(t,r){t[r]=this.resolvedProperty[this.propertyIndex]}_getValue_toArray(t,r){this.resolvedProperty.toArray(t,r)}_setValue_direct(t,r){this.targetObject[this.propertyName]=t[r]}_setValue_direct_setNeedsUpdate(t,r){this.targetObject[this.propertyName]=t[r],this.targetObject.needsUpdate=!0}_setValue_direct_setMatrixWorldNeedsUpdate(t,r){this.targetObject[this.propertyName]=t[r],this.targetObject.matrixWorldNeedsUpdate=!0}_setValue_array(t,r){let i=this.resolvedProperty;for(let n=0,a=i.length;n!==a;++n)i[n]=t[r++]}_setValue_array_setNeedsUpdate(t,r){let i=this.resolvedProperty;for(let n=0,a=i.length;n!==a;++n)i[n]=t[r++];this.targetObject.needsUpdate=!0}_setValue_array_setMatrixWorldNeedsUpdate(t,r){let i=this.resolvedProperty;for(let n=0,a=i.length;n!==a;++n)i[n]=t[r++];this.targetObject.matrixWorldNeedsUpdate=!0}_setValue_arrayElement(t,r){this.resolvedProperty[this.propertyIndex]=t[r]}_setValue_arrayElement_setNeedsUpdate(t,r){this.resolvedProperty[this.propertyIndex]=t[r],this.targetObject.needsUpdate=!0}_setValue_arrayElement_setMatrixWorldNeedsUpdate(t,r){this.resolvedProperty[this.propertyIndex]=t[r],this.targetObject.matrixWorldNeedsUpdate=!0}_setValue_fromArray(t,r){this.resolvedProperty.fromArray(t,r)}_setValue_fromArray_setNeedsUpdate(t,r){this.resolvedProperty.fromArray(t,r),this.targetObject.needsUpdate=!0}_setValue_fromArray_setMatrixWorldNeedsUpdate(t,r){this.resolvedProperty.fromArray(t,r),this.targetObject.matrixWorldNeedsUpdate=!0}_getValue_unbound(t,r){this.bind(),this.getValue(t,r)}_setValue_unbound(t,r){this.bind(),this.setValue(t,r)}bind(){let t=this.node,r=this.parsedPath,i=r.objectName,n=r.propertyName,a=r.propertyIndex;if(t||(t=Di.findNode(this.rootNode,r.nodeName),this.node=t),this.getValue=this._getValue_unavailable,this.setValue=this._setValue_unavailable,!t){console.warn("THREE.PropertyBinding: No target node found for track: "+this.path+".");return}if(i){let u=r.objectIndex;switch(i){case"materials":if(!t.material){console.error("THREE.PropertyBinding: Can not bind to material as node does not have a material.",this);return}if(!t.material.materials){console.error("THREE.PropertyBinding: Can not bind to material.materials as node.material does not have a materials array.",this);return}t=t.material.materials;break;case"bones":if(!t.skeleton){console.error("THREE.PropertyBinding: Can not bind to bones as node does not have a skeleton.",this);return}t=t.skeleton.bones;for(let l=0;l<t.length;l++)if(t[l].name===u){u=l;break}break;case"map":if("map"in t){t=t.map;break}if(!t.material){console.error("THREE.PropertyBinding: Can not bind to material as node does not have a material.",this);return}if(!t.material.map){console.error("THREE.PropertyBinding: Can not bind to material.map as node.material does not have a map.",this);return}t=t.material.map;break;default:if(t[i]===void 0){console.error("THREE.PropertyBinding: Can not bind to objectName of node undefined.",this);return}t=t[i]}if(u!==void 0){if(t[u]===void 0){console.error("THREE.PropertyBinding: Trying to bind to objectIndex of objectName, but is undefined.",this,t);return}t=t[u]}}let o=t[n];if(o===void 0){let u=r.nodeName;console.error("THREE.PropertyBinding: Trying to update property for track: "+u+"."+n+" but it wasn't found.",t);return}let s=this.Versioning.None;this.targetObject=t,t.isMaterial===!0?s=this.Versioning.NeedsUpdate:t.isObject3D===!0&&(s=this.Versioning.MatrixWorldNeedsUpdate);let c=this.BindingType.Direct;if(a!==void 0){if(n==="morphTargetInfluences"){if(!t.geometry){console.error("THREE.PropertyBinding: Can not bind to morphTargetInfluences because node does not have a geometry.",this);return}if(!t.geometry.morphAttributes){console.error("THREE.PropertyBinding: Can not bind to morphTargetInfluences because node does not have a geometry.morphAttributes.",this);return}t.morphTargetDictionary[a]!==void 0&&(a=t.morphTargetDictionary[a])}c=this.BindingType.ArrayElement,this.resolvedProperty=o,this.propertyIndex=a}else o.fromArray!==void 0&&o.toArray!==void 0?(c=this.BindingType.HasFromToArray,this.resolvedProperty=o):Array.isArray(o)?(c=this.BindingType.EntireArray,this.resolvedProperty=o):this.propertyName=n;this.getValue=this.GetterByBindingType[c],this.setValue=this.SetterByBindingTypeAndVersioning[c][s]}unbind(){this.node=null,this.getValue=this._getValue_unbound,this.setValue=this._setValue_unbound}};nt.Composite=fm;nt.prototype.BindingType={Direct:0,EntireArray:1,ArrayElement:2,HasFromToArray:3};nt.prototype.Versioning={None:0,NeedsUpdate:1,MatrixWorldNeedsUpdate:2};nt.prototype.GetterByBindingType=[nt.prototype._getValue_direct,nt.prototype._getValue_array,nt.prototype._getValue_arrayElement,nt.prototype._getValue_toArray];nt.prototype.SetterByBindingTypeAndVersioning=[[nt.prototype._setValue_direct,nt.prototype._setValue_direct_setNeedsUpdate,nt.prototype._setValue_direct_setMatrixWorldNeedsUpdate],[nt.prototype._setValue_array,nt.prototype._setValue_array_setNeedsUpdate,nt.prototype._setValue_array_setMatrixWorldNeedsUpdate],[nt.prototype._setValue_arrayElement,nt.prototype._setValue_arrayElement_setNeedsUpdate,nt.prototype._setValue_arrayElement_setMatrixWorldNeedsUpdate],[nt.prototype._setValue_fromArray,nt.prototype._setValue_fromArray_setNeedsUpdate,nt.prototype._setValue_fromArray_setMatrixWorldNeedsUpdate]];var sy=new Float32Array(1);function lu(e,t,r,i){let n=mm(i);switch(r){case zu:return e*t;case Gu:return e*t/n.components*n.byteLength;case $s:return e*t/n.components*n.byteLength;case Wu:return e*t*2/n.components*n.byteLength;case Qs:return e*t*2/n.components*n.byteLength;case Hu:return e*t*3/n.components*n.byteLength;case qt:return e*t*4/n.components*n.byteLength;case el:return e*t*4/n.components*n.byteLength;case xa:case ya:return Math.floor((e+3)/4)*Math.floor((t+3)/4)*8;case Sa:case Ea:return Math.floor((e+3)/4)*Math.floor((t+3)/4)*16;case _s:case xs:return Math.max(e,16)*Math.max(t,8)/4;case vs:case bs:return Math.max(e,8)*Math.max(t,8)/2;case ys:case Ss:return Math.floor((e+3)/4)*Math.floor((t+3)/4)*8;case Es:return Math.floor((e+3)/4)*Math.floor((t+3)/4)*16;case Ts:return Math.floor((e+3)/4)*Math.floor((t+3)/4)*16;case Ms:return Math.floor((e+4)/5)*Math.floor((t+3)/4)*16;case As:return Math.floor((e+4)/5)*Math.floor((t+4)/5)*16;case ws:return Math.floor((e+5)/6)*Math.floor((t+4)/5)*16;case Rs:return Math.floor((e+5)/6)*Math.floor((t+5)/6)*16;case Cs:return Math.floor((e+7)/8)*Math.floor((t+4)/5)*16;case Is:return Math.floor((e+7)/8)*Math.floor((t+5)/6)*16;case Ns:return Math.floor((e+7)/8)*Math.floor((t+7)/8)*16;case Ps:return Math.floor((e+9)/10)*Math.floor((t+4)/5)*16;case Os:return Math.floor((e+9)/10)*Math.floor((t+5)/6)*16;case Ls:return Math.floor((e+9)/10)*Math.floor((t+7)/8)*16;case Us:return Math.floor((e+9)/10)*Math.floor((t+9)/10)*16;case Ds:return Math.floor((e+11)/12)*Math.floor((t+9)/10)*16;case Fs:return Math.floor((e+11)/12)*Math.floor((t+11)/12)*16;case ks:case Bs:case Vs:return Math.ceil(e/4)*Math.ceil(t/4)*16;case zs:case Hs:return Math.ceil(e/4)*Math.ceil(t/4)*8;case Gs:case Ws:return Math.ceil(e/4)*Math.ceil(t/4)*16}throw new Error(`Unable to determine texture byte length for ${r} format.`)}function mm(e){switch(e){case lr:case Fu:return{byteLength:1,components:1};case un:case ku:case mn:return{byteLength:2,components:1};case Js:case Zs:return{byteLength:2,components:4};case si:case Ks:case Mr:return{byteLength:4,components:1};case Bu:case Vu:return{byteLength:4,components:3}}throw new Error(`Unknown texture type ${e}.`)}typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("register",{detail:{revision:"180"}}));typeof window<"u"&&(window.__THREE__?console.warn("WARNING: Multiple instances of Three.js being imported."):window.__THREE__="180");function xd(){let e=null,t=!1,r=null,i=null;function n(a,o){r(a,o),i=e.requestAnimationFrame(n)}return{start:function(){t!==!0&&r!==null&&(i=e.requestAnimationFrame(n),t=!0)},stop:function(){e.cancelAnimationFrame(i),t=!1},setAnimationLoop:function(a){r=a},setContext:function(a){e=a}}}function gm(e){let t=new WeakMap;function r(s,c){let u=s.array,l=s.usage,d=u.byteLength,h=e.createBuffer();e.bindBuffer(c,h),e.bufferData(c,u,l),s.onUploadCallback();let m;if(u instanceof Float32Array)m=e.FLOAT;else if(typeof Float16Array<"u"&&u instanceof Float16Array)m=e.HALF_FLOAT;else if(u instanceof Uint16Array)s.isFloat16BufferAttribute?m=e.HALF_FLOAT:m=e.UNSIGNED_SHORT;else if(u instanceof Int16Array)m=e.SHORT;else if(u instanceof Uint32Array)m=e.UNSIGNED_INT;else if(u instanceof Int32Array)m=e.INT;else if(u instanceof Int8Array)m=e.BYTE;else if(u instanceof Uint8Array)m=e.UNSIGNED_BYTE;else if(u instanceof Uint8ClampedArray)m=e.UNSIGNED_BYTE;else throw new Error("THREE.WebGLAttributes: Unsupported buffer data format: "+u);return{buffer:h,type:m,bytesPerElement:u.BYTES_PER_ELEMENT,version:s.version,size:d}}function i(s,c,u){let l=c.array,d=c.updateRanges;if(e.bindBuffer(u,s),d.length===0)e.bufferSubData(u,0,l);else{d.sort((m,g)=>m.start-g.start);let h=0;for(let m=1;m<d.length;m++){let g=d[h],_=d[m];_.start<=g.start+g.count+1?g.count=Math.max(g.count,_.start+_.count-g.start):(++h,d[h]=_)}d.length=h+1;for(let m=0,g=d.length;m<g;m++){let _=d[m];e.bufferSubData(u,_.start*l.BYTES_PER_ELEMENT,l,_.start,_.count)}c.clearUpdateRanges()}c.onUploadCallback()}function n(s){return s.isInterleavedBufferAttribute&&(s=s.data),t.get(s)}function a(s){s.isInterleavedBufferAttribute&&(s=s.data);let c=t.get(s);c&&(e.deleteBuffer(c.buffer),t.delete(s))}function o(s,c){if(s.isInterleavedBufferAttribute&&(s=s.data),s.isGLBufferAttribute){let l=t.get(s);(!l||l.version<s.version)&&t.set(s,{buffer:s.buffer,type:s.type,bytesPerElement:s.elementSize,version:s.version});return}let u=t.get(s);if(u===void 0)t.set(s,r(s,c));else if(u.version<s.version){if(u.size!==s.array.byteLength)throw new Error("THREE.WebGLAttributes: The size of the buffer attribute's array buffer does not match the original size. Resizing buffer attributes is not supported.");i(u.buffer,s,c),u.version=s.version}}return{get:n,remove:a,update:o}}var vm=`#ifdef USE_ALPHAHASH
	if ( diffuseColor.a < getAlphaHashThreshold( vPosition ) ) discard;
#endif`,_m=`#ifdef USE_ALPHAHASH
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
#endif`,bm=`#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, vAlphaMapUv ).g;
#endif`,xm=`#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`,ym=`#ifdef USE_ALPHATEST
	#ifdef ALPHA_TO_COVERAGE
	diffuseColor.a = smoothstep( alphaTest, alphaTest + fwidth( diffuseColor.a ), diffuseColor.a );
	if ( diffuseColor.a == 0.0 ) discard;
	#else
	if ( diffuseColor.a < alphaTest ) discard;
	#endif
#endif`,Sm=`#ifdef USE_ALPHATEST
	uniform float alphaTest;
#endif`,Em=`#ifdef USE_AOMAP
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
#endif`,Tm=`#ifdef USE_AOMAP
	uniform sampler2D aoMap;
	uniform float aoMapIntensity;
#endif`,Mm=`#ifdef USE_BATCHING
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
#endif`,Am=`#ifdef USE_BATCHING
	mat4 batchingMatrix = getBatchingMatrix( getIndirectIndex( gl_DrawID ) );
#endif`,wm=`vec3 transformed = vec3( position );
#ifdef USE_ALPHAHASH
	vPosition = vec3( position );
#endif`,Rm=`vec3 objectNormal = vec3( normal );
#ifdef USE_TANGENT
	vec3 objectTangent = vec3( tangent.xyz );
#endif`,Cm=`float G_BlinnPhong_Implicit( ) {
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
} // validated`,Im=`#ifdef USE_IRIDESCENCE
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
#endif`,Nm=`#ifdef USE_BUMPMAP
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
#endif`,Pm=`#if NUM_CLIPPING_PLANES > 0
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
#endif`,Om=`#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
	uniform vec4 clippingPlanes[ NUM_CLIPPING_PLANES ];
#endif`,Lm=`#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
#endif`,Um=`#if NUM_CLIPPING_PLANES > 0
	vClipPosition = - mvPosition.xyz;
#endif`,Dm=`#if defined( USE_COLOR_ALPHA )
	diffuseColor *= vColor;
#elif defined( USE_COLOR )
	diffuseColor.rgb *= vColor;
#endif`,Fm=`#if defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#elif defined( USE_COLOR )
	varying vec3 vColor;
#endif`,km=`#if defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#elif defined( USE_COLOR ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )
	varying vec3 vColor;
#endif`,Bm=`#if defined( USE_COLOR_ALPHA )
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
#endif`,Vm=`#define PI 3.141592653589793
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
} // validated`,zm=`#ifdef ENVMAP_TYPE_CUBE_UV
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
#endif`,Hm=`vec3 transformedNormal = objectNormal;
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
#endif`,Gm=`#ifdef USE_DISPLACEMENTMAP
	uniform sampler2D displacementMap;
	uniform float displacementScale;
	uniform float displacementBias;
#endif`,Wm=`#ifdef USE_DISPLACEMENTMAP
	transformed += normalize( objectNormal ) * ( texture2D( displacementMap, vDisplacementMapUv ).x * displacementScale + displacementBias );
#endif`,jm=`#ifdef USE_EMISSIVEMAP
	vec4 emissiveColor = texture2D( emissiveMap, vEmissiveMapUv );
	#ifdef DECODE_VIDEO_TEXTURE_EMISSIVE
		emissiveColor = sRGBTransferEOTF( emissiveColor );
	#endif
	totalEmissiveRadiance *= emissiveColor.rgb;
#endif`,Xm=`#ifdef USE_EMISSIVEMAP
	uniform sampler2D emissiveMap;
#endif`,qm="gl_FragColor = linearToOutputTexel( gl_FragColor );",Ym=`vec4 LinearTransferOETF( in vec4 value ) {
	return value;
}
vec4 sRGBTransferEOTF( in vec4 value ) {
	return vec4( mix( pow( value.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), value.rgb * 0.0773993808, vec3( lessThanEqual( value.rgb, vec3( 0.04045 ) ) ) ), value.a );
}
vec4 sRGBTransferOETF( in vec4 value ) {
	return vec4( mix( pow( value.rgb, vec3( 0.41666 ) ) * 1.055 - vec3( 0.055 ), value.rgb * 12.92, vec3( lessThanEqual( value.rgb, vec3( 0.0031308 ) ) ) ), value.a );
}`,Km=`#ifdef USE_ENVMAP
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
#endif`,Jm=`#ifdef USE_ENVMAP
	uniform float envMapIntensity;
	uniform float flipEnvMap;
	uniform mat3 envMapRotation;
	#ifdef ENVMAP_TYPE_CUBE
		uniform samplerCube envMap;
	#else
		uniform sampler2D envMap;
	#endif
	
#endif`,Zm=`#ifdef USE_ENVMAP
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
#endif`,$m=`#ifdef USE_ENVMAP
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		
		varying vec3 vWorldPosition;
	#else
		varying vec3 vReflect;
		uniform float refractionRatio;
	#endif
#endif`,Qm=`#ifdef USE_ENVMAP
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
#endif`,eg=`#ifdef USE_FOG
	vFogDepth = - mvPosition.z;
#endif`,tg=`#ifdef USE_FOG
	varying float vFogDepth;
#endif`,rg=`#ifdef USE_FOG
	#ifdef FOG_EXP2
		float fogFactor = 1.0 - exp( - fogDensity * fogDensity * vFogDepth * vFogDepth );
	#else
		float fogFactor = smoothstep( fogNear, fogFar, vFogDepth );
	#endif
	gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, fogFactor );
#endif`,ig=`#ifdef USE_FOG
	uniform vec3 fogColor;
	varying float vFogDepth;
	#ifdef FOG_EXP2
		uniform float fogDensity;
	#else
		uniform float fogNear;
		uniform float fogFar;
	#endif
#endif`,ng=`#ifdef USE_GRADIENTMAP
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
}`,ag=`#ifdef USE_LIGHTMAP
	uniform sampler2D lightMap;
	uniform float lightMapIntensity;
#endif`,og=`LambertMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularStrength = specularStrength;`,sg=`varying vec3 vViewPosition;
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
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Lambert`,lg=`uniform bool receiveShadow;
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
#endif`,cg=`#ifdef USE_ENVMAP
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
#endif`,ug=`ToonMaterial material;
material.diffuseColor = diffuseColor.rgb;`,dg=`varying vec3 vViewPosition;
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
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Toon`,hg=`BlinnPhongMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularColor = specular;
material.specularShininess = shininess;
material.specularStrength = specularStrength;`,pg=`varying vec3 vViewPosition;
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
#define RE_IndirectDiffuse		RE_IndirectDiffuse_BlinnPhong`,fg=`PhysicalMaterial material;
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
#endif`,mg=`struct PhysicalMaterial {
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
}`,gg=`
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
#endif`,vg=`#if defined( RE_IndirectDiffuse )
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
#endif`,_g=`#if defined( RE_IndirectDiffuse )
	RE_IndirectDiffuse( irradiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif
#if defined( RE_IndirectSpecular )
	RE_IndirectSpecular( radiance, iblIrradiance, clearcoatRadiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif`,bg=`#if defined( USE_LOGARITHMIC_DEPTH_BUFFER )
	gl_FragDepth = vIsPerspective == 0.0 ? gl_FragCoord.z : log2( vFragDepth ) * logDepthBufFC * 0.5;
#endif`,xg=`#if defined( USE_LOGARITHMIC_DEPTH_BUFFER )
	uniform float logDepthBufFC;
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`,yg=`#ifdef USE_LOGARITHMIC_DEPTH_BUFFER
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`,Sg=`#ifdef USE_LOGARITHMIC_DEPTH_BUFFER
	vFragDepth = 1.0 + gl_Position.w;
	vIsPerspective = float( isPerspectiveMatrix( projectionMatrix ) );
#endif`,Eg=`#ifdef USE_MAP
	vec4 sampledDiffuseColor = texture2D( map, vMapUv );
	#ifdef DECODE_VIDEO_TEXTURE
		sampledDiffuseColor = sRGBTransferEOTF( sampledDiffuseColor );
	#endif
	diffuseColor *= sampledDiffuseColor;
#endif`,Tg=`#ifdef USE_MAP
	uniform sampler2D map;
#endif`,Mg=`#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
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
#endif`,Ag=`#if defined( USE_POINTS_UV )
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
#endif`,wg=`float metalnessFactor = metalness;
#ifdef USE_METALNESSMAP
	vec4 texelMetalness = texture2D( metalnessMap, vMetalnessMapUv );
	metalnessFactor *= texelMetalness.b;
#endif`,Rg=`#ifdef USE_METALNESSMAP
	uniform sampler2D metalnessMap;
#endif`,Cg=`#ifdef USE_INSTANCING_MORPH
	float morphTargetInfluences[ MORPHTARGETS_COUNT ];
	float morphTargetBaseInfluence = texelFetch( morphTexture, ivec2( 0, gl_InstanceID ), 0 ).r;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		morphTargetInfluences[i] =  texelFetch( morphTexture, ivec2( i + 1, gl_InstanceID ), 0 ).r;
	}
#endif`,Ig=`#if defined( USE_MORPHCOLORS )
	vColor *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		#if defined( USE_COLOR_ALPHA )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ) * morphTargetInfluences[ i ];
		#elif defined( USE_COLOR )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ).rgb * morphTargetInfluences[ i ];
		#endif
	}
#endif`,Ng=`#ifdef USE_MORPHNORMALS
	objectNormal *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) objectNormal += getMorph( gl_VertexID, i, 1 ).xyz * morphTargetInfluences[ i ];
	}
#endif`,Pg=`#ifdef USE_MORPHTARGETS
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
#endif`,Og=`#ifdef USE_MORPHTARGETS
	transformed *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) transformed += getMorph( gl_VertexID, i, 0 ).xyz * morphTargetInfluences[ i ];
	}
#endif`,Lg=`float faceDirection = gl_FrontFacing ? 1.0 : - 1.0;
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
vec3 nonPerturbedNormal = normal;`,Ug=`#ifdef USE_NORMALMAP_OBJECTSPACE
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
#endif`,Dg=`#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,Fg=`#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,kg=`#ifndef FLAT_SHADED
	vNormal = normalize( transformedNormal );
	#ifdef USE_TANGENT
		vTangent = normalize( transformedTangent );
		vBitangent = normalize( cross( vNormal, vTangent ) * tangent.w );
	#endif
#endif`,Bg=`#ifdef USE_NORMALMAP
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
#endif`,Vg=`#ifdef USE_CLEARCOAT
	vec3 clearcoatNormal = nonPerturbedNormal;
#endif`,zg=`#ifdef USE_CLEARCOAT_NORMALMAP
	vec3 clearcoatMapN = texture2D( clearcoatNormalMap, vClearcoatNormalMapUv ).xyz * 2.0 - 1.0;
	clearcoatMapN.xy *= clearcoatNormalScale;
	clearcoatNormal = normalize( tbn2 * clearcoatMapN );
#endif`,Hg=`#ifdef USE_CLEARCOATMAP
	uniform sampler2D clearcoatMap;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform sampler2D clearcoatNormalMap;
	uniform vec2 clearcoatNormalScale;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform sampler2D clearcoatRoughnessMap;
#endif`,Gg=`#ifdef USE_IRIDESCENCEMAP
	uniform sampler2D iridescenceMap;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform sampler2D iridescenceThicknessMap;
#endif`,Wg=`#ifdef OPAQUE
diffuseColor.a = 1.0;
#endif
#ifdef USE_TRANSMISSION
diffuseColor.a *= material.transmissionAlpha;
#endif
gl_FragColor = vec4( outgoingLight, diffuseColor.a );`,jg=`vec3 packNormalToRGB( const in vec3 normal ) {
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
}`,Xg=`#ifdef PREMULTIPLIED_ALPHA
	gl_FragColor.rgb *= gl_FragColor.a;
#endif`,qg=`vec4 mvPosition = vec4( transformed, 1.0 );
#ifdef USE_BATCHING
	mvPosition = batchingMatrix * mvPosition;
#endif
#ifdef USE_INSTANCING
	mvPosition = instanceMatrix * mvPosition;
#endif
mvPosition = modelViewMatrix * mvPosition;
gl_Position = projectionMatrix * mvPosition;`,Yg=`#ifdef DITHERING
	gl_FragColor.rgb = dithering( gl_FragColor.rgb );
#endif`,Kg=`#ifdef DITHERING
	vec3 dithering( vec3 color ) {
		float grid_position = rand( gl_FragCoord.xy );
		vec3 dither_shift_RGB = vec3( 0.25 / 255.0, -0.25 / 255.0, 0.25 / 255.0 );
		dither_shift_RGB = mix( 2.0 * dither_shift_RGB, -2.0 * dither_shift_RGB, grid_position );
		return color + dither_shift_RGB;
	}
#endif`,Jg=`float roughnessFactor = roughness;
#ifdef USE_ROUGHNESSMAP
	vec4 texelRoughness = texture2D( roughnessMap, vRoughnessMapUv );
	roughnessFactor *= texelRoughness.g;
#endif`,Zg=`#ifdef USE_ROUGHNESSMAP
	uniform sampler2D roughnessMap;
#endif`,$g=`#if NUM_SPOT_LIGHT_COORDS > 0
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
#endif`,Qg=`#if NUM_SPOT_LIGHT_COORDS > 0
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
#endif`,ev=`#if ( defined( USE_SHADOWMAP ) && ( NUM_DIR_LIGHT_SHADOWS > 0 || NUM_POINT_LIGHT_SHADOWS > 0 ) ) || ( NUM_SPOT_LIGHT_COORDS > 0 )
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
#endif`,tv=`float getShadowMask() {
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
}`,rv=`#ifdef USE_SKINNING
	mat4 boneMatX = getBoneMatrix( skinIndex.x );
	mat4 boneMatY = getBoneMatrix( skinIndex.y );
	mat4 boneMatZ = getBoneMatrix( skinIndex.z );
	mat4 boneMatW = getBoneMatrix( skinIndex.w );
#endif`,iv=`#ifdef USE_SKINNING
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
#endif`,nv=`#ifdef USE_SKINNING
	vec4 skinVertex = bindMatrix * vec4( transformed, 1.0 );
	vec4 skinned = vec4( 0.0 );
	skinned += boneMatX * skinVertex * skinWeight.x;
	skinned += boneMatY * skinVertex * skinWeight.y;
	skinned += boneMatZ * skinVertex * skinWeight.z;
	skinned += boneMatW * skinVertex * skinWeight.w;
	transformed = ( bindMatrixInverse * skinned ).xyz;
#endif`,av=`#ifdef USE_SKINNING
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
#endif`,ov=`float specularStrength;
#ifdef USE_SPECULARMAP
	vec4 texelSpecular = texture2D( specularMap, vSpecularMapUv );
	specularStrength = texelSpecular.r;
#else
	specularStrength = 1.0;
#endif`,sv=`#ifdef USE_SPECULARMAP
	uniform sampler2D specularMap;
#endif`,lv=`#if defined( TONE_MAPPING )
	gl_FragColor.rgb = toneMapping( gl_FragColor.rgb );
#endif`,cv=`#ifndef saturate
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
vec3 CustomToneMapping( vec3 color ) { return color; }`,uv=`#ifdef USE_TRANSMISSION
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
#endif`,dv=`#ifdef USE_TRANSMISSION
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
#endif`,hv=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
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
#endif`,pv=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
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
#endif`,fv=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
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
#endif`,mv=`#if defined( USE_ENVMAP ) || defined( DISTANCE ) || defined ( USE_SHADOWMAP ) || defined ( USE_TRANSMISSION ) || NUM_SPOT_LIGHT_COORDS > 0
	vec4 worldPosition = vec4( transformed, 1.0 );
	#ifdef USE_BATCHING
		worldPosition = batchingMatrix * worldPosition;
	#endif
	#ifdef USE_INSTANCING
		worldPosition = instanceMatrix * worldPosition;
	#endif
	worldPosition = modelMatrix * worldPosition;
#endif`,gv=`varying vec2 vUv;
uniform mat3 uvTransform;
void main() {
	vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	gl_Position = vec4( position.xy, 1.0, 1.0 );
}`,vv=`uniform sampler2D t2D;
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
}`,_v=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,bv=`#ifdef ENVMAP_TYPE_CUBE
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
}`,xv=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,yv=`uniform samplerCube tCube;
uniform float tFlip;
uniform float opacity;
varying vec3 vWorldDirection;
void main() {
	vec4 texColor = textureCube( tCube, vec3( tFlip * vWorldDirection.x, vWorldDirection.yz ) );
	gl_FragColor = texColor;
	gl_FragColor.a *= opacity;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,Sv=`#include <common>
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
}`,Ev=`#if DEPTH_PACKING == 3200
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
}`,Tv=`#define DISTANCE
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
}`,Mv=`#define DISTANCE
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
}`,Av=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
}`,wv=`uniform sampler2D tEquirect;
varying vec3 vWorldDirection;
#include <common>
void main() {
	vec3 direction = normalize( vWorldDirection );
	vec2 sampleUV = equirectUv( direction );
	gl_FragColor = texture2D( tEquirect, sampleUV );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,Rv=`uniform float scale;
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
}`,Cv=`uniform vec3 diffuse;
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
}`,Iv=`#include <common>
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
}`,Nv=`uniform vec3 diffuse;
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
}`,Pv=`#define LAMBERT
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
}`,Ov=`#define LAMBERT
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
}`,Lv=`#define MATCAP
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
}`,Uv=`#define MATCAP
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
}`,Dv=`#define NORMAL
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
}`,Fv=`#define NORMAL
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
}`,kv=`#define PHONG
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
}`,Bv=`#define PHONG
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
}`,Vv=`#define STANDARD
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
}`,zv=`#define STANDARD
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
}`,Hv=`#define TOON
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
}`,Gv=`#define TOON
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
}`,Wv=`uniform float size;
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
}`,jv=`uniform vec3 diffuse;
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
}`,Xv=`#include <common>
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
}`,qv=`uniform vec3 color;
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
}`,Yv=`uniform float rotation;
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
}`,Kv=`uniform vec3 diffuse;
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
}`,ke={alphahash_fragment:vm,alphahash_pars_fragment:_m,alphamap_fragment:bm,alphamap_pars_fragment:xm,alphatest_fragment:ym,alphatest_pars_fragment:Sm,aomap_fragment:Em,aomap_pars_fragment:Tm,batching_pars_vertex:Mm,batching_vertex:Am,begin_vertex:wm,beginnormal_vertex:Rm,bsdfs:Cm,iridescence_fragment:Im,bumpmap_pars_fragment:Nm,clipping_planes_fragment:Pm,clipping_planes_pars_fragment:Om,clipping_planes_pars_vertex:Lm,clipping_planes_vertex:Um,color_fragment:Dm,color_pars_fragment:Fm,color_pars_vertex:km,color_vertex:Bm,common:Vm,cube_uv_reflection_fragment:zm,defaultnormal_vertex:Hm,displacementmap_pars_vertex:Gm,displacementmap_vertex:Wm,emissivemap_fragment:jm,emissivemap_pars_fragment:Xm,colorspace_fragment:qm,colorspace_pars_fragment:Ym,envmap_fragment:Km,envmap_common_pars_fragment:Jm,envmap_pars_fragment:Zm,envmap_pars_vertex:$m,envmap_physical_pars_fragment:cg,envmap_vertex:Qm,fog_vertex:eg,fog_pars_vertex:tg,fog_fragment:rg,fog_pars_fragment:ig,gradientmap_pars_fragment:ng,lightmap_pars_fragment:ag,lights_lambert_fragment:og,lights_lambert_pars_fragment:sg,lights_pars_begin:lg,lights_toon_fragment:ug,lights_toon_pars_fragment:dg,lights_phong_fragment:hg,lights_phong_pars_fragment:pg,lights_physical_fragment:fg,lights_physical_pars_fragment:mg,lights_fragment_begin:gg,lights_fragment_maps:vg,lights_fragment_end:_g,logdepthbuf_fragment:bg,logdepthbuf_pars_fragment:xg,logdepthbuf_pars_vertex:yg,logdepthbuf_vertex:Sg,map_fragment:Eg,map_pars_fragment:Tg,map_particle_fragment:Mg,map_particle_pars_fragment:Ag,metalnessmap_fragment:wg,metalnessmap_pars_fragment:Rg,morphinstance_vertex:Cg,morphcolor_vertex:Ig,morphnormal_vertex:Ng,morphtarget_pars_vertex:Pg,morphtarget_vertex:Og,normal_fragment_begin:Lg,normal_fragment_maps:Ug,normal_pars_fragment:Dg,normal_pars_vertex:Fg,normal_vertex:kg,normalmap_pars_fragment:Bg,clearcoat_normal_fragment_begin:Vg,clearcoat_normal_fragment_maps:zg,clearcoat_pars_fragment:Hg,iridescence_pars_fragment:Gg,opaque_fragment:Wg,packing:jg,premultiplied_alpha_fragment:Xg,project_vertex:qg,dithering_fragment:Yg,dithering_pars_fragment:Kg,roughnessmap_fragment:Jg,roughnessmap_pars_fragment:Zg,shadowmap_pars_fragment:$g,shadowmap_pars_vertex:Qg,shadowmap_vertex:ev,shadowmask_pars_fragment:tv,skinbase_vertex:rv,skinning_pars_vertex:iv,skinning_vertex:nv,skinnormal_vertex:av,specularmap_fragment:ov,specularmap_pars_fragment:sv,tonemapping_fragment:lv,tonemapping_pars_fragment:cv,transmission_fragment:uv,transmission_pars_fragment:dv,uv_pars_fragment:hv,uv_pars_vertex:pv,uv_vertex:fv,worldpos_vertex:mv,background_vert:gv,background_frag:vv,backgroundCube_vert:_v,backgroundCube_frag:bv,cube_vert:xv,cube_frag:yv,depth_vert:Sv,depth_frag:Ev,distanceRGBA_vert:Tv,distanceRGBA_frag:Mv,equirect_vert:Av,equirect_frag:wv,linedashed_vert:Rv,linedashed_frag:Cv,meshbasic_vert:Iv,meshbasic_frag:Nv,meshlambert_vert:Pv,meshlambert_frag:Ov,meshmatcap_vert:Lv,meshmatcap_frag:Uv,meshnormal_vert:Dv,meshnormal_frag:Fv,meshphong_vert:kv,meshphong_frag:Bv,meshphysical_vert:Vv,meshphysical_frag:zv,meshtoon_vert:Hv,meshtoon_frag:Gv,points_vert:Wv,points_frag:jv,shadow_vert:Xv,shadow_frag:qv,sprite_vert:Yv,sprite_frag:Kv},ue={common:{diffuse:{value:new qe(16777215)},opacity:{value:1},map:{value:null},mapTransform:{value:new Be},alphaMap:{value:null},alphaMapTransform:{value:new Be},alphaTest:{value:0}},specularmap:{specularMap:{value:null},specularMapTransform:{value:new Be}},envmap:{envMap:{value:null},envMapRotation:{value:new Be},flipEnvMap:{value:-1},reflectivity:{value:1},ior:{value:1.5},refractionRatio:{value:.98}},aomap:{aoMap:{value:null},aoMapIntensity:{value:1},aoMapTransform:{value:new Be}},lightmap:{lightMap:{value:null},lightMapIntensity:{value:1},lightMapTransform:{value:new Be}},bumpmap:{bumpMap:{value:null},bumpMapTransform:{value:new Be},bumpScale:{value:1}},normalmap:{normalMap:{value:null},normalMapTransform:{value:new Be},normalScale:{value:new Ye(1,1)}},displacementmap:{displacementMap:{value:null},displacementMapTransform:{value:new Be},displacementScale:{value:1},displacementBias:{value:0}},emissivemap:{emissiveMap:{value:null},emissiveMapTransform:{value:new Be}},metalnessmap:{metalnessMap:{value:null},metalnessMapTransform:{value:new Be}},roughnessmap:{roughnessMap:{value:null},roughnessMapTransform:{value:new Be}},gradientmap:{gradientMap:{value:null}},fog:{fogDensity:{value:25e-5},fogNear:{value:1},fogFar:{value:2e3},fogColor:{value:new qe(16777215)}},lights:{ambientLightColor:{value:[]},lightProbe:{value:[]},directionalLights:{value:[],properties:{direction:{},color:{}}},directionalLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},directionalShadowMap:{value:[]},directionalShadowMatrix:{value:[]},spotLights:{value:[],properties:{color:{},position:{},direction:{},distance:{},coneCos:{},penumbraCos:{},decay:{}}},spotLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},spotLightMap:{value:[]},spotShadowMap:{value:[]},spotLightMatrix:{value:[]},pointLights:{value:[],properties:{color:{},position:{},decay:{},distance:{}}},pointLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{},shadowCameraNear:{},shadowCameraFar:{}}},pointShadowMap:{value:[]},pointShadowMatrix:{value:[]},hemisphereLights:{value:[],properties:{direction:{},skyColor:{},groundColor:{}}},rectAreaLights:{value:[],properties:{color:{},position:{},width:{},height:{}}},ltc_1:{value:null},ltc_2:{value:null}},points:{diffuse:{value:new qe(16777215)},opacity:{value:1},size:{value:1},scale:{value:1},map:{value:null},alphaMap:{value:null},alphaMapTransform:{value:new Be},alphaTest:{value:0},uvTransform:{value:new Be}},sprite:{diffuse:{value:new qe(16777215)},opacity:{value:1},center:{value:new Ye(.5,.5)},rotation:{value:0},map:{value:null},mapTransform:{value:new Be},alphaMap:{value:null},alphaMapTransform:{value:new Be},alphaTest:{value:0}}},nr={basic:{uniforms:Et([ue.common,ue.specularmap,ue.envmap,ue.aomap,ue.lightmap,ue.fog]),vertexShader:ke.meshbasic_vert,fragmentShader:ke.meshbasic_frag},lambert:{uniforms:Et([ue.common,ue.specularmap,ue.envmap,ue.aomap,ue.lightmap,ue.emissivemap,ue.bumpmap,ue.normalmap,ue.displacementmap,ue.fog,ue.lights,{emissive:{value:new qe(0)}}]),vertexShader:ke.meshlambert_vert,fragmentShader:ke.meshlambert_frag},phong:{uniforms:Et([ue.common,ue.specularmap,ue.envmap,ue.aomap,ue.lightmap,ue.emissivemap,ue.bumpmap,ue.normalmap,ue.displacementmap,ue.fog,ue.lights,{emissive:{value:new qe(0)},specular:{value:new qe(1118481)},shininess:{value:30}}]),vertexShader:ke.meshphong_vert,fragmentShader:ke.meshphong_frag},standard:{uniforms:Et([ue.common,ue.envmap,ue.aomap,ue.lightmap,ue.emissivemap,ue.bumpmap,ue.normalmap,ue.displacementmap,ue.roughnessmap,ue.metalnessmap,ue.fog,ue.lights,{emissive:{value:new qe(0)},roughness:{value:1},metalness:{value:0},envMapIntensity:{value:1}}]),vertexShader:ke.meshphysical_vert,fragmentShader:ke.meshphysical_frag},toon:{uniforms:Et([ue.common,ue.aomap,ue.lightmap,ue.emissivemap,ue.bumpmap,ue.normalmap,ue.displacementmap,ue.gradientmap,ue.fog,ue.lights,{emissive:{value:new qe(0)}}]),vertexShader:ke.meshtoon_vert,fragmentShader:ke.meshtoon_frag},matcap:{uniforms:Et([ue.common,ue.bumpmap,ue.normalmap,ue.displacementmap,ue.fog,{matcap:{value:null}}]),vertexShader:ke.meshmatcap_vert,fragmentShader:ke.meshmatcap_frag},points:{uniforms:Et([ue.points,ue.fog]),vertexShader:ke.points_vert,fragmentShader:ke.points_frag},dashed:{uniforms:Et([ue.common,ue.fog,{scale:{value:1},dashSize:{value:1},totalSize:{value:2}}]),vertexShader:ke.linedashed_vert,fragmentShader:ke.linedashed_frag},depth:{uniforms:Et([ue.common,ue.displacementmap]),vertexShader:ke.depth_vert,fragmentShader:ke.depth_frag},normal:{uniforms:Et([ue.common,ue.bumpmap,ue.normalmap,ue.displacementmap,{opacity:{value:1}}]),vertexShader:ke.meshnormal_vert,fragmentShader:ke.meshnormal_frag},sprite:{uniforms:Et([ue.sprite,ue.fog]),vertexShader:ke.sprite_vert,fragmentShader:ke.sprite_frag},background:{uniforms:{uvTransform:{value:new Be},t2D:{value:null},backgroundIntensity:{value:1}},vertexShader:ke.background_vert,fragmentShader:ke.background_frag},backgroundCube:{uniforms:{envMap:{value:null},flipEnvMap:{value:-1},backgroundBlurriness:{value:0},backgroundIntensity:{value:1},backgroundRotation:{value:new Be}},vertexShader:ke.backgroundCube_vert,fragmentShader:ke.backgroundCube_frag},cube:{uniforms:{tCube:{value:null},tFlip:{value:-1},opacity:{value:1}},vertexShader:ke.cube_vert,fragmentShader:ke.cube_frag},equirect:{uniforms:{tEquirect:{value:null}},vertexShader:ke.equirect_vert,fragmentShader:ke.equirect_frag},distanceRGBA:{uniforms:Et([ue.common,ue.displacementmap,{referencePosition:{value:new F},nearDistance:{value:1},farDistance:{value:1e3}}]),vertexShader:ke.distanceRGBA_vert,fragmentShader:ke.distanceRGBA_frag},shadow:{uniforms:Et([ue.lights,ue.fog,{color:{value:new qe(0)},opacity:{value:1}}]),vertexShader:ke.shadow_vert,fragmentShader:ke.shadow_frag}};nr.physical={uniforms:Et([nr.standard.uniforms,{clearcoat:{value:0},clearcoatMap:{value:null},clearcoatMapTransform:{value:new Be},clearcoatNormalMap:{value:null},clearcoatNormalMapTransform:{value:new Be},clearcoatNormalScale:{value:new Ye(1,1)},clearcoatRoughness:{value:0},clearcoatRoughnessMap:{value:null},clearcoatRoughnessMapTransform:{value:new Be},dispersion:{value:0},iridescence:{value:0},iridescenceMap:{value:null},iridescenceMapTransform:{value:new Be},iridescenceIOR:{value:1.3},iridescenceThicknessMinimum:{value:100},iridescenceThicknessMaximum:{value:400},iridescenceThicknessMap:{value:null},iridescenceThicknessMapTransform:{value:new Be},sheen:{value:0},sheenColor:{value:new qe(0)},sheenColorMap:{value:null},sheenColorMapTransform:{value:new Be},sheenRoughness:{value:1},sheenRoughnessMap:{value:null},sheenRoughnessMapTransform:{value:new Be},transmission:{value:0},transmissionMap:{value:null},transmissionMapTransform:{value:new Be},transmissionSamplerSize:{value:new Ye},transmissionSamplerMap:{value:null},thickness:{value:0},thicknessMap:{value:null},thicknessMapTransform:{value:new Be},attenuationDistance:{value:0},attenuationColor:{value:new qe(0)},specularColor:{value:new qe(1,1,1)},specularColorMap:{value:null},specularColorMapTransform:{value:new Be},specularIntensity:{value:1},specularIntensityMap:{value:null},specularIntensityMapTransform:{value:new Be},anisotropyVector:{value:new Ye},anisotropyMap:{value:null},anisotropyMapTransform:{value:new Be}}]),vertexShader:ke.meshphysical_vert,fragmentShader:ke.meshphysical_frag};var va={r:0,b:0,g:0},$r=new zr,Jv=new pt;function Zv(e,t,r,i,n,a,o){let s=new qe(0),c=a===!0?0:1,u,l,d=null,h=0,m=null;function g(y){let A=y.isScene===!0?y.background:null;return A&&A.isTexture&&(A=(y.backgroundBlurriness>0?r:t).get(A)),A}function _(y){let A=!1,O=g(y);O===null?p(s,c):O&&O.isColor&&(p(O,1),A=!0);let I=e.xr.getEnvironmentBlendMode();I==="additive"?i.buffers.color.setClear(0,0,0,1,o):I==="alpha-blend"&&i.buffers.color.setClear(0,0,0,0,o),(e.autoClear||A)&&(i.buffers.depth.setTest(!0),i.buffers.depth.setMask(!0),i.buffers.color.setMask(!0),e.clear(e.autoClearColor,e.autoClearDepth,e.autoClearStencil))}function f(y,A){let O=g(A);O&&(O.isCubeTexture||O.mapping===Na)?(l===void 0&&(l=new Yt(new xn(1,1,1),new Hr({name:"BackgroundCubeMaterial",uniforms:Wi(nr.backgroundCube.uniforms),vertexShader:nr.backgroundCube.vertexShader,fragmentShader:nr.backgroundCube.fragmentShader,side:Rt,depthTest:!1,depthWrite:!1,fog:!1,allowOverride:!1})),l.geometry.deleteAttribute("normal"),l.geometry.deleteAttribute("uv"),l.onBeforeRender=function(I,C,U){this.matrixWorld.copyPosition(U.matrixWorld)},Object.defineProperty(l.material,"envMap",{get:function(){return this.uniforms.envMap.value}}),n.update(l)),$r.copy(A.backgroundRotation),$r.x*=-1,$r.y*=-1,$r.z*=-1,O.isCubeTexture&&O.isRenderTargetTexture===!1&&($r.y*=-1,$r.z*=-1),l.material.uniforms.envMap.value=O,l.material.uniforms.flipEnvMap.value=O.isCubeTexture&&O.isRenderTargetTexture===!1?-1:1,l.material.uniforms.backgroundBlurriness.value=A.backgroundBlurriness,l.material.uniforms.backgroundIntensity.value=A.backgroundIntensity,l.material.uniforms.backgroundRotation.value.setFromMatrix4(Jv.makeRotationFromEuler($r)),l.material.toneMapped=Xe.getTransfer(O.colorSpace)!==Je,(d!==O||h!==O.version||m!==e.toneMapping)&&(l.material.needsUpdate=!0,d=O,h=O.version,m=e.toneMapping),l.layers.enableAll(),y.unshift(l,l.geometry,l.material,0,0,null)):O&&O.isTexture&&(u===void 0&&(u=new Yt(new pd(2,2),new Hr({name:"BackgroundMaterial",uniforms:Wi(nr.background.uniforms),vertexShader:nr.background.vertexShader,fragmentShader:nr.background.fragmentShader,side:Vr,depthTest:!1,depthWrite:!1,fog:!1,allowOverride:!1})),u.geometry.deleteAttribute("normal"),Object.defineProperty(u.material,"map",{get:function(){return this.uniforms.t2D.value}}),n.update(u)),u.material.uniforms.t2D.value=O,u.material.uniforms.backgroundIntensity.value=A.backgroundIntensity,u.material.toneMapped=Xe.getTransfer(O.colorSpace)!==Je,O.matrixAutoUpdate===!0&&O.updateMatrix(),u.material.uniforms.uvTransform.value.copy(O.matrix),(d!==O||h!==O.version||m!==e.toneMapping)&&(u.material.needsUpdate=!0,d=O,h=O.version,m=e.toneMapping),u.layers.enableAll(),y.unshift(u,u.geometry,u.material,0,0,null))}function p(y,A){y.getRGB(va,sd(e)),i.buffers.color.setClear(va.r,va.g,va.b,A,o)}function R(){l!==void 0&&(l.geometry.dispose(),l.material.dispose(),l=void 0),u!==void 0&&(u.geometry.dispose(),u.material.dispose(),u=void 0)}return{getClearColor:function(){return s},setClearColor:function(y,A=1){s.set(y),c=A,p(s,c)},getClearAlpha:function(){return c},setClearAlpha:function(y){c=y,p(s,c)},render:_,addToRenderList:f,dispose:R}}function $v(e,t){let r=e.getParameter(e.MAX_VERTEX_ATTRIBS),i={},n=h(null),a=n,o=!1;function s(x,M,k,H,V){let Z=!1,G=d(H,k,M);a!==G&&(a=G,u(a.object)),Z=m(x,H,k,V),Z&&g(x,H,k,V),V!==null&&t.update(V,e.ELEMENT_ARRAY_BUFFER),(Z||o)&&(o=!1,A(x,M,k,H),V!==null&&e.bindBuffer(e.ELEMENT_ARRAY_BUFFER,t.get(V).buffer))}function c(){return e.createVertexArray()}function u(x){return e.bindVertexArray(x)}function l(x){return e.deleteVertexArray(x)}function d(x,M,k){let H=k.wireframe===!0,V=i[x.id];V===void 0&&(V={},i[x.id]=V);let Z=V[M.id];Z===void 0&&(Z={},V[M.id]=Z);let G=Z[H];return G===void 0&&(G=h(c()),Z[H]=G),G}function h(x){let M=[],k=[],H=[];for(let V=0;V<r;V++)M[V]=0,k[V]=0,H[V]=0;return{geometry:null,program:null,wireframe:!1,newAttributes:M,enabledAttributes:k,attributeDivisors:H,object:x,attributes:{},index:null}}function m(x,M,k,H){let V=a.attributes,Z=M.attributes,G=0,ee=k.getAttributes();for(let W in ee)if(ee[W].location>=0){let ie=V[W],ce=Z[W];if(ce===void 0&&(W==="instanceMatrix"&&x.instanceMatrix&&(ce=x.instanceMatrix),W==="instanceColor"&&x.instanceColor&&(ce=x.instanceColor)),ie===void 0||ie.attribute!==ce||ce&&ie.data!==ce.data)return!0;G++}return a.attributesNum!==G||a.index!==H}function g(x,M,k,H){let V={},Z=M.attributes,G=0,ee=k.getAttributes();for(let W in ee)if(ee[W].location>=0){let ie=Z[W];ie===void 0&&(W==="instanceMatrix"&&x.instanceMatrix&&(ie=x.instanceMatrix),W==="instanceColor"&&x.instanceColor&&(ie=x.instanceColor));let ce={};ce.attribute=ie,ie&&ie.data&&(ce.data=ie.data),V[W]=ce,G++}a.attributes=V,a.attributesNum=G,a.index=H}function _(){let x=a.newAttributes;for(let M=0,k=x.length;M<k;M++)x[M]=0}function f(x){p(x,0)}function p(x,M){let k=a.newAttributes,H=a.enabledAttributes,V=a.attributeDivisors;k[x]=1,H[x]===0&&(e.enableVertexAttribArray(x),H[x]=1),V[x]!==M&&(e.vertexAttribDivisor(x,M),V[x]=M)}function R(){let x=a.newAttributes,M=a.enabledAttributes;for(let k=0,H=M.length;k<H;k++)M[k]!==x[k]&&(e.disableVertexAttribArray(k),M[k]=0)}function y(x,M,k,H,V,Z,G){G===!0?e.vertexAttribIPointer(x,M,k,V,Z):e.vertexAttribPointer(x,M,k,H,V,Z)}function A(x,M,k,H){_();let V=H.attributes,Z=k.getAttributes(),G=M.defaultAttributeValues;for(let ee in Z){let W=Z[ee];if(W.location>=0){let ie=V[ee];if(ie===void 0&&(ee==="instanceMatrix"&&x.instanceMatrix&&(ie=x.instanceMatrix),ee==="instanceColor"&&x.instanceColor&&(ie=x.instanceColor)),ie!==void 0){let ce=ie.normalized,Pe=ie.itemSize,Fe=t.get(ie);if(Fe===void 0)continue;let $e=Fe.buffer,We=Fe.type,j=Fe.bytesPerElement,oe=We===e.INT||We===e.UNSIGNED_INT||ie.gpuType===Ks;if(ie.isInterleavedBufferAttribute){let ne=ie.data,z=ne.stride,ae=ie.offset;if(ne.isInstancedInterleavedBuffer){for(let $=0;$<W.locationSize;$++)p(W.location+$,ne.meshPerAttribute);x.isInstancedMesh!==!0&&H._maxInstanceCount===void 0&&(H._maxInstanceCount=ne.meshPerAttribute*ne.count)}else for(let $=0;$<W.locationSize;$++)f(W.location+$);e.bindBuffer(e.ARRAY_BUFFER,$e);for(let $=0;$<W.locationSize;$++)y(W.location+$,Pe/W.locationSize,We,ce,z*j,(ae+Pe/W.locationSize*$)*j,oe)}else{if(ie.isInstancedBufferAttribute){for(let ne=0;ne<W.locationSize;ne++)p(W.location+ne,ie.meshPerAttribute);x.isInstancedMesh!==!0&&H._maxInstanceCount===void 0&&(H._maxInstanceCount=ie.meshPerAttribute*ie.count)}else for(let ne=0;ne<W.locationSize;ne++)f(W.location+ne);e.bindBuffer(e.ARRAY_BUFFER,$e);for(let ne=0;ne<W.locationSize;ne++)y(W.location+ne,Pe/W.locationSize,We,ce,Pe*j,Pe/W.locationSize*ne*j,oe)}}else if(G!==void 0){let ce=G[ee];if(ce!==void 0)switch(ce.length){case 2:e.vertexAttrib2fv(W.location,ce);break;case 3:e.vertexAttrib3fv(W.location,ce);break;case 4:e.vertexAttrib4fv(W.location,ce);break;default:e.vertexAttrib1fv(W.location,ce)}}}}R()}function O(){U();for(let x in i){let M=i[x];for(let k in M){let H=M[k];for(let V in H)l(H[V].object),delete H[V];delete M[k]}delete i[x]}}function I(x){if(i[x.id]===void 0)return;let M=i[x.id];for(let k in M){let H=M[k];for(let V in H)l(H[V].object),delete H[V];delete M[k]}delete i[x.id]}function C(x){for(let M in i){let k=i[M];if(k[x.id]===void 0)continue;let H=k[x.id];for(let V in H)l(H[V].object),delete H[V];delete k[x.id]}}function U(){S(),o=!0,a!==n&&(a=n,u(a.object))}function S(){n.geometry=null,n.program=null,n.wireframe=!1}return{setup:s,reset:U,resetDefaultState:S,dispose:O,releaseStatesOfGeometry:I,releaseStatesOfProgram:C,initAttributes:_,enableAttribute:f,disableUnusedAttributes:R}}function Qv(e,t,r){let i;function n(u){i=u}function a(u,l){e.drawArrays(i,u,l),r.update(l,i,1)}function o(u,l,d){d!==0&&(e.drawArraysInstanced(i,u,l,d),r.update(l,i,d))}function s(u,l,d){if(d===0)return;t.get("WEBGL_multi_draw").multiDrawArraysWEBGL(i,u,0,l,0,d);let h=0;for(let m=0;m<d;m++)h+=l[m];r.update(h,i,1)}function c(u,l,d,h){if(d===0)return;let m=t.get("WEBGL_multi_draw");if(m===null)for(let g=0;g<u.length;g++)o(u[g],l[g],h[g]);else{m.multiDrawArraysInstancedWEBGL(i,u,0,l,0,h,0,d);let g=0;for(let _=0;_<d;_++)g+=l[_]*h[_];r.update(g,i,1)}}this.setMode=n,this.render=a,this.renderInstances=o,this.renderMultiDraw=s,this.renderMultiDrawInstances=c}function e_(e,t,r,i){let n;function a(){if(n!==void 0)return n;if(t.has("EXT_texture_filter_anisotropic")===!0){let C=t.get("EXT_texture_filter_anisotropic");n=e.getParameter(C.MAX_TEXTURE_MAX_ANISOTROPY_EXT)}else n=0;return n}function o(C){return!(C!==qt&&i.convert(C)!==e.getParameter(e.IMPLEMENTATION_COLOR_READ_FORMAT))}function s(C){let U=C===mn&&(t.has("EXT_color_buffer_half_float")||t.has("EXT_color_buffer_float"));return!(C!==lr&&i.convert(C)!==e.getParameter(e.IMPLEMENTATION_COLOR_READ_TYPE)&&C!==Mr&&!U)}function c(C){if(C==="highp"){if(e.getShaderPrecisionFormat(e.VERTEX_SHADER,e.HIGH_FLOAT).precision>0&&e.getShaderPrecisionFormat(e.FRAGMENT_SHADER,e.HIGH_FLOAT).precision>0)return"highp";C="mediump"}return C==="mediump"&&e.getShaderPrecisionFormat(e.VERTEX_SHADER,e.MEDIUM_FLOAT).precision>0&&e.getShaderPrecisionFormat(e.FRAGMENT_SHADER,e.MEDIUM_FLOAT).precision>0?"mediump":"lowp"}let u=r.precision!==void 0?r.precision:"highp",l=c(u);l!==u&&(console.warn("THREE.WebGLRenderer:",u,"not supported, using",l,"instead."),u=l);let d=r.logarithmicDepthBuffer===!0,h=r.reversedDepthBuffer===!0&&t.has("EXT_clip_control"),m=e.getParameter(e.MAX_TEXTURE_IMAGE_UNITS),g=e.getParameter(e.MAX_VERTEX_TEXTURE_IMAGE_UNITS),_=e.getParameter(e.MAX_TEXTURE_SIZE),f=e.getParameter(e.MAX_CUBE_MAP_TEXTURE_SIZE),p=e.getParameter(e.MAX_VERTEX_ATTRIBS),R=e.getParameter(e.MAX_VERTEX_UNIFORM_VECTORS),y=e.getParameter(e.MAX_VARYING_VECTORS),A=e.getParameter(e.MAX_FRAGMENT_UNIFORM_VECTORS),O=g>0,I=e.getParameter(e.MAX_SAMPLES);return{isWebGL2:!0,getMaxAnisotropy:a,getMaxPrecision:c,textureFormatReadable:o,textureTypeReadable:s,precision:u,logarithmicDepthBuffer:d,reversedDepthBuffer:h,maxTextures:m,maxVertexTextures:g,maxTextureSize:_,maxCubemapSize:f,maxAttributes:p,maxVertexUniforms:R,maxVaryings:y,maxFragmentUniforms:A,vertexTextures:O,maxSamples:I}}function t_(e){let t=this,r=null,i=0,n=!1,a=!1,o=new ei,s=new Be,c={value:null,needsUpdate:!1};this.uniform=c,this.numPlanes=0,this.numIntersection=0,this.init=function(d,h){let m=d.length!==0||h||i!==0||n;return n=h,i=d.length,m},this.beginShadows=function(){a=!0,l(null)},this.endShadows=function(){a=!1},this.setGlobalState=function(d,h){r=l(d,h,0)},this.setState=function(d,h,m){let g=d.clippingPlanes,_=d.clipIntersection,f=d.clipShadows,p=e.get(d);if(!n||g===null||g.length===0||a&&!f)a?l(null):u();else{let R=a?0:i,y=R*4,A=p.clippingState||null;c.value=A,A=l(g,h,y,m);for(let O=0;O!==y;++O)A[O]=r[O];p.clippingState=A,this.numIntersection=_?this.numPlanes:0,this.numPlanes+=R}};function u(){c.value!==r&&(c.value=r,c.needsUpdate=i>0),t.numPlanes=i,t.numIntersection=0}function l(d,h,m,g){let _=d!==null?d.length:0,f=null;if(_!==0){if(f=c.value,g!==!0||f===null){let p=m+_*4,R=h.matrixWorldInverse;s.getNormalMatrix(R),(f===null||f.length<p)&&(f=new Float32Array(p));for(let y=0,A=m;y!==_;++y,A+=4)o.copy(d[y]).applyMatrix4(R,s),o.normal.toArray(f,A),f[A+3]=o.constant}c.value=f,c.needsUpdate=!0}return t.numPlanes=_,t.numIntersection=0,f}}function r_(e){let t=new WeakMap;function r(o,s){return s===ps?o.mapping=zi:s===fs&&(o.mapping=Hi),o}function i(o){if(o&&o.isTexture){let s=o.mapping;if(s===ps||s===fs)if(t.has(o)){let c=t.get(o).texture;return r(c,o.mapping)}else{let c=o.image;if(c&&c.height>0){let u=new Bf(c.height);return u.fromEquirectangularTexture(e,o),t.set(o,u),o.addEventListener("dispose",n),r(u.texture,o.mapping)}else return null}}return o}function n(o){let s=o.target;s.removeEventListener("dispose",n);let c=t.get(s);c!==void 0&&(t.delete(s),c.dispose())}function a(){t=new WeakMap}return{get:i,dispose:a}}var Fi=4,cu=[.125,.215,.35,.446,.526,.582],ii=20,$o=new Oa,uu=new qe,Qo=null,es=0,ts=0,rs=!1,ti=(1+Math.sqrt(5))/2,Li=1/ti,du=[new F(-ti,Li,0),new F(ti,Li,0),new F(-Li,0,ti),new F(Li,0,ti),new F(0,ti,-Li),new F(0,ti,Li),new F(-1,1,-1),new F(1,1,-1),new F(-1,1,1),new F(1,1,1)],i_=new F,hu=class{constructor(e){this._renderer=e,this._pingPongRenderTarget=null,this._lodMax=0,this._cubeSize=0,this._lodPlanes=[],this._sizeLods=[],this._sigmas=[],this._blurMaterial=null,this._cubemapMaterial=null,this._equirectMaterial=null,this._compileMaterial(this._blurMaterial)}fromScene(e,t=0,r=.1,i=100,n={}){let{size:a=256,position:o=i_}=n;Qo=this._renderer.getRenderTarget(),es=this._renderer.getActiveCubeFace(),ts=this._renderer.getActiveMipmapLevel(),rs=this._renderer.xr.enabled,this._renderer.xr.enabled=!1,this._setSize(a);let s=this._allocateTargets();return s.depthBuffer=!0,this._sceneToCubeUV(e,r,i,s,o),t>0&&this._blur(s,0,0,t),this._applyPMREM(s),this._cleanup(s),s}fromEquirectangular(e,t=null){return this._fromTexture(e,t)}fromCubemap(e,t=null){return this._fromTexture(e,t)}compileCubemapShader(){this._cubemapMaterial===null&&(this._cubemapMaterial=mu(),this._compileMaterial(this._cubemapMaterial))}compileEquirectangularShader(){this._equirectMaterial===null&&(this._equirectMaterial=fu(),this._compileMaterial(this._equirectMaterial))}dispose(){this._dispose(),this._cubemapMaterial!==null&&this._cubemapMaterial.dispose(),this._equirectMaterial!==null&&this._equirectMaterial.dispose()}_setSize(e){this._lodMax=Math.floor(Math.log2(e)),this._cubeSize=Math.pow(2,this._lodMax)}_dispose(){this._blurMaterial!==null&&this._blurMaterial.dispose(),this._pingPongRenderTarget!==null&&this._pingPongRenderTarget.dispose();for(let e=0;e<this._lodPlanes.length;e++)this._lodPlanes[e].dispose()}_cleanup(e){this._renderer.setRenderTarget(Qo,es,ts),this._renderer.xr.enabled=rs,e.scissorTest=!1,_a(e,0,0,e.width,e.height)}_fromTexture(e,t){e.mapping===zi||e.mapping===Hi?this._setSize(e.image.length===0?16:e.image[0].width||e.image[0].image.width):this._setSize(e.image.width/4),Qo=this._renderer.getRenderTarget(),es=this._renderer.getActiveCubeFace(),ts=this._renderer.getActiveMipmapLevel(),rs=this._renderer.xr.enabled,this._renderer.xr.enabled=!1;let r=t||this._allocateTargets();return this._textureToCubeUV(e,r),this._applyPMREM(r),this._cleanup(r),r}_allocateTargets(){let e=3*Math.max(this._cubeSize,112),t=4*this._cubeSize,r={magFilter:ar,minFilter:ar,generateMipmaps:!1,type:mn,format:qt,colorSpace:Gi,depthBuffer:!1},i=pu(e,t,r);if(this._pingPongRenderTarget===null||this._pingPongRenderTarget.width!==e||this._pingPongRenderTarget.height!==t){this._pingPongRenderTarget!==null&&this._dispose(),this._pingPongRenderTarget=pu(e,t,r);let{_lodMax:n}=this;({sizeLods:this._sizeLods,lodPlanes:this._lodPlanes,sigmas:this._sigmas}=n_(n)),this._blurMaterial=a_(n,e,t)}return i}_compileMaterial(e){let t=new Yt(this._lodPlanes[0],e);this._renderer.compile(t,$o)}_sceneToCubeUV(e,t,r,i,n){let a=new Xt(90,1,t,r),o=[1,-1,1,1,1,1],s=[1,1,1,-1,-1,-1],c=this._renderer,u=c.autoClear,l=c.toneMapping;c.getClearColor(uu),c.toneMapping=Br,c.autoClear=!1,c.state.buffers.depth.getReversed()&&(c.setRenderTarget(i),c.clearDepth(),c.setRenderTarget(null));let d=new rd({name:"PMREM.Background",side:Rt,depthWrite:!1,depthTest:!1}),h=new Yt(new xn,d),m=!1,g=e.background;g?g.isColor&&(d.color.copy(g),e.background=null,m=!0):(d.color.copy(uu),m=!0);for(let _=0;_<6;_++){let f=_%3;f===0?(a.up.set(0,o[_],0),a.position.set(n.x,n.y,n.z),a.lookAt(n.x+s[_],n.y,n.z)):f===1?(a.up.set(0,0,o[_]),a.position.set(n.x,n.y,n.z),a.lookAt(n.x,n.y+s[_],n.z)):(a.up.set(0,o[_],0),a.position.set(n.x,n.y,n.z),a.lookAt(n.x,n.y,n.z+s[_]));let p=this._cubeSize;_a(i,f*p,_>2?p:0,p,p),c.setRenderTarget(i),m&&c.render(h,a),c.render(e,a)}h.geometry.dispose(),h.material.dispose(),c.toneMapping=l,c.autoClear=u,e.background=g}_textureToCubeUV(e,t){let r=this._renderer,i=e.mapping===zi||e.mapping===Hi;i?(this._cubemapMaterial===null&&(this._cubemapMaterial=mu()),this._cubemapMaterial.uniforms.flipEnvMap.value=e.isRenderTargetTexture===!1?-1:1):this._equirectMaterial===null&&(this._equirectMaterial=fu());let n=i?this._cubemapMaterial:this._equirectMaterial,a=new Yt(this._lodPlanes[0],n),o=n.uniforms;o.envMap.value=e;let s=this._cubeSize;_a(t,0,0,3*s,2*s),r.setRenderTarget(t),r.render(a,$o)}_applyPMREM(e){let t=this._renderer,r=t.autoClear;t.autoClear=!1;let i=this._lodPlanes.length;for(let n=1;n<i;n++){let a=Math.sqrt(this._sigmas[n]*this._sigmas[n]-this._sigmas[n-1]*this._sigmas[n-1]),o=du[(i-n-1)%du.length];this._blur(e,n-1,n,a,o)}t.autoClear=r}_blur(e,t,r,i,n){let a=this._pingPongRenderTarget;this._halfBlur(e,a,t,r,i,"latitudinal",n),this._halfBlur(a,e,r,r,i,"longitudinal",n)}_halfBlur(e,t,r,i,n,a,o){let s=this._renderer,c=this._blurMaterial;a!=="latitudinal"&&a!=="longitudinal"&&console.error("blur direction must be either latitudinal or longitudinal!");let u=3,l=new Yt(this._lodPlanes[i],c),d=c.uniforms,h=this._sizeLods[r]-1,m=isFinite(n)?Math.PI/(2*h):2*Math.PI/(2*ii-1),g=n/m,_=isFinite(n)?1+Math.floor(u*g):ii;_>ii&&console.warn(`sigmaRadians, ${n}, is too large and will clip, as it requested ${_} samples when the maximum is set to ${ii}`);let f=[],p=0;for(let I=0;I<ii;++I){let C=I/g,U=Math.exp(-C*C/2);f.push(U),I===0?p+=U:I<_&&(p+=2*U)}for(let I=0;I<f.length;I++)f[I]=f[I]/p;d.envMap.value=e.texture,d.samples.value=_,d.weights.value=f,d.latitudinal.value=a==="latitudinal",o&&(d.poleAxis.value=o);let{_lodMax:R}=this;d.dTheta.value=m,d.mipInt.value=R-r;let y=this._sizeLods[i],A=3*y*(i>R-Fi?i-R+Fi:0),O=4*(this._cubeSize-y);_a(t,A,O,3*y,2*y),s.setRenderTarget(t),s.render(l,$o)}};function n_(e){let t=[],r=[],i=[],n=e,a=e-Fi+1+cu.length;for(let o=0;o<a;o++){let s=Math.pow(2,n);r.push(s);let c=1/s;o>e-Fi?c=cu[o-e+Fi-1]:o===0&&(c=0),i.push(c);let u=1/(s-2),l=-u,d=1+u,h=[l,l,d,l,d,d,l,l,d,d,l,d],m=6,g=6,_=3,f=2,p=1,R=new Float32Array(_*g*m),y=new Float32Array(f*g*m),A=new Float32Array(p*g*m);for(let I=0;I<m;I++){let C=I%3*2/3-1,U=I>2?0:-1,S=[C,U,0,C+2/3,U,0,C+2/3,U+1,0,C,U,0,C+2/3,U+1,0,C,U+1,0];R.set(S,_*g*I),y.set(h,f*g*I);let x=[I,I,I,I,I,I];A.set(x,p*g*I)}let O=new bn;O.setAttribute("position",new sr(R,_)),O.setAttribute("uv",new sr(y,f)),O.setAttribute("faceIndex",new sr(A,p)),t.push(O),n>Fi&&n--}return{lodPlanes:t,sizeLods:r,sigmas:i}}function pu(e,t,r){let i=new li(e,t,r);return i.texture.mapping=Na,i.texture.name="PMREM.cubeUv",i.scissorTest=!0,i}function _a(e,t,r,i,n){e.viewport.set(t,r,i,n),e.scissor.set(t,r,i,n)}function a_(e,t,r){let i=new Float32Array(ii),n=new F(0,1,0);return new Hr({name:"SphericalGaussianBlur",defines:{n:ii,CUBEUV_TEXEL_WIDTH:1/t,CUBEUV_TEXEL_HEIGHT:1/r,CUBEUV_MAX_MIP:`${e}.0`},uniforms:{envMap:{value:null},samples:{value:1},weights:{value:i},latitudinal:{value:!1},dTheta:{value:0},mipInt:{value:0},poleAxis:{value:n}},vertexShader:ol(),fragmentShader:`

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
		`,blending:kr,depthTest:!1,depthWrite:!1})}function fu(){return new Hr({name:"EquirectangularToCubeUV",uniforms:{envMap:{value:null}},vertexShader:ol(),fragmentShader:`

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
		`,blending:kr,depthTest:!1,depthWrite:!1})}function mu(){return new Hr({name:"CubemapToCubeUV",uniforms:{envMap:{value:null},flipEnvMap:{value:-1}},vertexShader:ol(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			uniform float flipEnvMap;

			varying vec3 vOutputDirection;

			uniform samplerCube envMap;

			void main() {

				gl_FragColor = textureCube( envMap, vec3( flipEnvMap * vOutputDirection.x, vOutputDirection.yz ) );

			}
		`,blending:kr,depthTest:!1,depthWrite:!1})}function ol(){return`

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
	`}function o_(e){let t=new WeakMap,r=null;function i(s){if(s&&s.isTexture){let c=s.mapping,u=c===ps||c===fs,l=c===zi||c===Hi;if(u||l){let d=t.get(s),h=d!==void 0?d.texture.pmremVersion:0;if(s.isRenderTargetTexture&&s.pmremVersion!==h)return r===null&&(r=new hu(e)),d=u?r.fromEquirectangular(s,d):r.fromCubemap(s,d),d.texture.pmremVersion=s.pmremVersion,t.set(s,d),d.texture;if(d!==void 0)return d.texture;{let m=s.image;return u&&m&&m.height>0||l&&m&&n(m)?(r===null&&(r=new hu(e)),d=u?r.fromEquirectangular(s):r.fromCubemap(s),d.texture.pmremVersion=s.pmremVersion,t.set(s,d),s.addEventListener("dispose",a),d.texture):null}}}return s}function n(s){let c=0,u=6;for(let l=0;l<u;l++)s[l]!==void 0&&c++;return c===u}function a(s){let c=s.target;c.removeEventListener("dispose",a);let u=t.get(c);u!==void 0&&(t.delete(c),u.dispose())}function o(){t=new WeakMap,r!==null&&(r.dispose(),r=null)}return{get:i,dispose:o}}function s_(e){let t={};function r(i){if(t[i]!==void 0)return t[i];let n;switch(i){case"WEBGL_depth_texture":n=e.getExtension("WEBGL_depth_texture")||e.getExtension("MOZ_WEBGL_depth_texture")||e.getExtension("WEBKIT_WEBGL_depth_texture");break;case"EXT_texture_filter_anisotropic":n=e.getExtension("EXT_texture_filter_anisotropic")||e.getExtension("MOZ_EXT_texture_filter_anisotropic")||e.getExtension("WEBKIT_EXT_texture_filter_anisotropic");break;case"WEBGL_compressed_texture_s3tc":n=e.getExtension("WEBGL_compressed_texture_s3tc")||e.getExtension("MOZ_WEBGL_compressed_texture_s3tc")||e.getExtension("WEBKIT_WEBGL_compressed_texture_s3tc");break;case"WEBGL_compressed_texture_pvrtc":n=e.getExtension("WEBGL_compressed_texture_pvrtc")||e.getExtension("WEBKIT_WEBGL_compressed_texture_pvrtc");break;default:n=e.getExtension(i)}return t[i]=n,n}return{has:function(i){return r(i)!==null},init:function(){r("EXT_color_buffer_float"),r("WEBGL_clip_cull_distance"),r("OES_texture_float_linear"),r("EXT_color_buffer_half_float"),r("WEBGL_multisampled_render_to_texture"),r("WEBGL_render_shared_exponent")},get:function(i){let n=r(i);return n===null&&fn("THREE.WebGLRenderer: "+i+" extension not supported."),n}}}function l_(e,t,r,i){let n={},a=new WeakMap;function o(d){let h=d.target;h.index!==null&&t.remove(h.index);for(let g in h.attributes)t.remove(h.attributes[g]);h.removeEventListener("dispose",o),delete n[h.id];let m=a.get(h);m&&(t.remove(m),a.delete(h)),i.releaseStatesOfGeometry(h),h.isInstancedBufferGeometry===!0&&delete h._maxInstanceCount,r.memory.geometries--}function s(d,h){return n[h.id]===!0||(h.addEventListener("dispose",o),n[h.id]=!0,r.memory.geometries++),h}function c(d){let h=d.attributes;for(let m in h)t.update(h[m],e.ARRAY_BUFFER)}function u(d){let h=[],m=d.index,g=d.attributes.position,_=0;if(m!==null){let R=m.array;_=m.version;for(let y=0,A=R.length;y<A;y+=3){let O=R[y+0],I=R[y+1],C=R[y+2];h.push(O,I,I,C,C,O)}}else if(g!==void 0){let R=g.array;_=g.version;for(let y=0,A=R.length/3-1;y<A;y+=3){let O=y+0,I=y+1,C=y+2;h.push(O,I,I,C,C,O)}}else return;let f=new(Ju(h)?nd:id)(h,1);f.version=_;let p=a.get(d);p&&t.remove(p),a.set(d,f)}function l(d){let h=a.get(d);if(h){let m=d.index;m!==null&&h.version<m.version&&u(d)}else u(d);return a.get(d)}return{get:s,update:c,getWireframeAttribute:l}}function c_(e,t,r){let i;function n(h){i=h}let a,o;function s(h){a=h.type,o=h.bytesPerElement}function c(h,m){e.drawElements(i,m,a,h*o),r.update(m,i,1)}function u(h,m,g){g!==0&&(e.drawElementsInstanced(i,m,a,h*o,g),r.update(m,i,g))}function l(h,m,g){if(g===0)return;t.get("WEBGL_multi_draw").multiDrawElementsWEBGL(i,m,0,a,h,0,g);let _=0;for(let f=0;f<g;f++)_+=m[f];r.update(_,i,1)}function d(h,m,g,_){if(g===0)return;let f=t.get("WEBGL_multi_draw");if(f===null)for(let p=0;p<h.length;p++)u(h[p]/o,m[p],_[p]);else{f.multiDrawElementsInstancedWEBGL(i,m,0,a,h,0,_,0,g);let p=0;for(let R=0;R<g;R++)p+=m[R]*_[R];r.update(p,i,1)}}this.setMode=n,this.setIndex=s,this.render=c,this.renderInstances=u,this.renderMultiDraw=l,this.renderMultiDrawInstances=d}function u_(e){let t={geometries:0,textures:0},r={frame:0,calls:0,triangles:0,points:0,lines:0};function i(a,o,s){switch(r.calls++,o){case e.TRIANGLES:r.triangles+=s*(a/3);break;case e.LINES:r.lines+=s*(a/2);break;case e.LINE_STRIP:r.lines+=s*(a-1);break;case e.LINE_LOOP:r.lines+=s*a;break;case e.POINTS:r.points+=s*a;break;default:console.error("THREE.WebGLInfo: Unknown draw mode:",o);break}}function n(){r.calls=0,r.triangles=0,r.points=0,r.lines=0}return{memory:t,render:r,programs:null,autoReset:!0,reset:n,update:i}}function d_(e,t,r){let i=new WeakMap,n=new lt;function a(o,s,c){let u=o.morphTargetInfluences,l=s.morphAttributes.position||s.morphAttributes.normal||s.morphAttributes.color,d=l!==void 0?l.length:0,h=i.get(s);if(h===void 0||h.count!==d){let m=function(){U.dispose(),i.delete(s),s.removeEventListener("dispose",m)};h!==void 0&&h.texture.dispose();let g=s.morphAttributes.position!==void 0,_=s.morphAttributes.normal!==void 0,f=s.morphAttributes.color!==void 0,p=s.morphAttributes.position||[],R=s.morphAttributes.normal||[],y=s.morphAttributes.color||[],A=0;g===!0&&(A=1),_===!0&&(A=2),f===!0&&(A=3);let O=s.attributes.position.count*A,I=1;O>t.maxTextureSize&&(I=Math.ceil(O/t.maxTextureSize),O=t.maxTextureSize);let C=new Float32Array(O*I*4*d),U=new $u(C,O,I,d);U.type=Mr,U.needsUpdate=!0;let S=A*4;for(let x=0;x<d;x++){let M=p[x],k=R[x],H=y[x],V=O*I*4*x;for(let Z=0;Z<M.count;Z++){let G=Z*S;g===!0&&(n.fromBufferAttribute(M,Z),C[V+G+0]=n.x,C[V+G+1]=n.y,C[V+G+2]=n.z,C[V+G+3]=0),_===!0&&(n.fromBufferAttribute(k,Z),C[V+G+4]=n.x,C[V+G+5]=n.y,C[V+G+6]=n.z,C[V+G+7]=0),f===!0&&(n.fromBufferAttribute(H,Z),C[V+G+8]=n.x,C[V+G+9]=n.y,C[V+G+10]=n.z,C[V+G+11]=H.itemSize===4?n.w:1)}}h={count:d,texture:U,size:new Ye(O,I)},i.set(s,h),s.addEventListener("dispose",m)}if(o.isInstancedMesh===!0&&o.morphTexture!==null)c.getUniforms().setValue(e,"morphTexture",o.morphTexture,r);else{let m=0;for(let _=0;_<u.length;_++)m+=u[_];let g=s.morphTargetsRelative?1:1-m;c.getUniforms().setValue(e,"morphTargetBaseInfluence",g),c.getUniforms().setValue(e,"morphTargetInfluences",u)}c.getUniforms().setValue(e,"morphTargetsTexture",h.texture,r),c.getUniforms().setValue(e,"morphTargetsTextureSize",h.size)}return{update:a}}function h_(e,t,r,i){let n=new WeakMap;function a(c){let u=i.render.frame,l=c.geometry,d=t.get(c,l);if(n.get(d)!==u&&(t.update(d),n.set(d,u)),c.isInstancedMesh&&(c.hasEventListener("dispose",s)===!1&&c.addEventListener("dispose",s),n.get(c)!==u&&(r.update(c.instanceMatrix,e.ARRAY_BUFFER),c.instanceColor!==null&&r.update(c.instanceColor,e.ARRAY_BUFFER),n.set(c,u))),c.isSkinnedMesh){let h=c.skeleton;n.get(h)!==u&&(h.update(),n.set(h,u))}return d}function o(){n=new WeakMap}function s(c){let u=c.target;u.removeEventListener("dispose",s),r.remove(u.instanceMatrix),u.instanceColor!==null&&r.remove(u.instanceColor)}return{update:a,dispose:o}}var yd=new cr,gu=new dd(1,1),Sd=new $u,Ed=new yf,Td=new cd,vu=[],_u=[],bu=new Float32Array(16),xu=new Float32Array(9),yu=new Float32Array(4);function qi(e,t,r){let i=e[0];if(i<=0||i>0)return e;let n=t*r,a=vu[n];if(a===void 0&&(a=new Float32Array(n),vu[n]=a),t!==0){i.toArray(a,0);for(let o=1,s=0;o!==t;++o)s+=r,e[o].toArray(a,s)}return a}function ct(e,t){if(e.length!==t.length)return!1;for(let r=0,i=e.length;r<i;r++)if(e[r]!==t[r])return!1;return!0}function ut(e,t){for(let r=0,i=t.length;r<i;r++)e[r]=t[r]}function La(e,t){let r=_u[t];r===void 0&&(r=new Int32Array(t),_u[t]=r);for(let i=0;i!==t;++i)r[i]=e.allocateTextureUnit();return r}function p_(e,t){let r=this.cache;r[0]!==t&&(e.uniform1f(this.addr,t),r[0]=t)}function f_(e,t){let r=this.cache;if(t.x!==void 0)(r[0]!==t.x||r[1]!==t.y)&&(e.uniform2f(this.addr,t.x,t.y),r[0]=t.x,r[1]=t.y);else{if(ct(r,t))return;e.uniform2fv(this.addr,t),ut(r,t)}}function m_(e,t){let r=this.cache;if(t.x!==void 0)(r[0]!==t.x||r[1]!==t.y||r[2]!==t.z)&&(e.uniform3f(this.addr,t.x,t.y,t.z),r[0]=t.x,r[1]=t.y,r[2]=t.z);else if(t.r!==void 0)(r[0]!==t.r||r[1]!==t.g||r[2]!==t.b)&&(e.uniform3f(this.addr,t.r,t.g,t.b),r[0]=t.r,r[1]=t.g,r[2]=t.b);else{if(ct(r,t))return;e.uniform3fv(this.addr,t),ut(r,t)}}function g_(e,t){let r=this.cache;if(t.x!==void 0)(r[0]!==t.x||r[1]!==t.y||r[2]!==t.z||r[3]!==t.w)&&(e.uniform4f(this.addr,t.x,t.y,t.z,t.w),r[0]=t.x,r[1]=t.y,r[2]=t.z,r[3]=t.w);else{if(ct(r,t))return;e.uniform4fv(this.addr,t),ut(r,t)}}function v_(e,t){let r=this.cache,i=t.elements;if(i===void 0){if(ct(r,t))return;e.uniformMatrix2fv(this.addr,!1,t),ut(r,t)}else{if(ct(r,i))return;yu.set(i),e.uniformMatrix2fv(this.addr,!1,yu),ut(r,i)}}function __(e,t){let r=this.cache,i=t.elements;if(i===void 0){if(ct(r,t))return;e.uniformMatrix3fv(this.addr,!1,t),ut(r,t)}else{if(ct(r,i))return;xu.set(i),e.uniformMatrix3fv(this.addr,!1,xu),ut(r,i)}}function b_(e,t){let r=this.cache,i=t.elements;if(i===void 0){if(ct(r,t))return;e.uniformMatrix4fv(this.addr,!1,t),ut(r,t)}else{if(ct(r,i))return;bu.set(i),e.uniformMatrix4fv(this.addr,!1,bu),ut(r,i)}}function x_(e,t){let r=this.cache;r[0]!==t&&(e.uniform1i(this.addr,t),r[0]=t)}function y_(e,t){let r=this.cache;if(t.x!==void 0)(r[0]!==t.x||r[1]!==t.y)&&(e.uniform2i(this.addr,t.x,t.y),r[0]=t.x,r[1]=t.y);else{if(ct(r,t))return;e.uniform2iv(this.addr,t),ut(r,t)}}function S_(e,t){let r=this.cache;if(t.x!==void 0)(r[0]!==t.x||r[1]!==t.y||r[2]!==t.z)&&(e.uniform3i(this.addr,t.x,t.y,t.z),r[0]=t.x,r[1]=t.y,r[2]=t.z);else{if(ct(r,t))return;e.uniform3iv(this.addr,t),ut(r,t)}}function E_(e,t){let r=this.cache;if(t.x!==void 0)(r[0]!==t.x||r[1]!==t.y||r[2]!==t.z||r[3]!==t.w)&&(e.uniform4i(this.addr,t.x,t.y,t.z,t.w),r[0]=t.x,r[1]=t.y,r[2]=t.z,r[3]=t.w);else{if(ct(r,t))return;e.uniform4iv(this.addr,t),ut(r,t)}}function T_(e,t){let r=this.cache;r[0]!==t&&(e.uniform1ui(this.addr,t),r[0]=t)}function M_(e,t){let r=this.cache;if(t.x!==void 0)(r[0]!==t.x||r[1]!==t.y)&&(e.uniform2ui(this.addr,t.x,t.y),r[0]=t.x,r[1]=t.y);else{if(ct(r,t))return;e.uniform2uiv(this.addr,t),ut(r,t)}}function A_(e,t){let r=this.cache;if(t.x!==void 0)(r[0]!==t.x||r[1]!==t.y||r[2]!==t.z)&&(e.uniform3ui(this.addr,t.x,t.y,t.z),r[0]=t.x,r[1]=t.y,r[2]=t.z);else{if(ct(r,t))return;e.uniform3uiv(this.addr,t),ut(r,t)}}function w_(e,t){let r=this.cache;if(t.x!==void 0)(r[0]!==t.x||r[1]!==t.y||r[2]!==t.z||r[3]!==t.w)&&(e.uniform4ui(this.addr,t.x,t.y,t.z,t.w),r[0]=t.x,r[1]=t.y,r[2]=t.z,r[3]=t.w);else{if(ct(r,t))return;e.uniform4uiv(this.addr,t),ut(r,t)}}function R_(e,t,r){let i=this.cache,n=r.allocateTextureUnit();i[0]!==n&&(e.uniform1i(this.addr,n),i[0]=n);let a;this.type===e.SAMPLER_2D_SHADOW?(gu.compareFunction=Xu,a=gu):a=yd,r.setTexture2D(t||a,n)}function C_(e,t,r){let i=this.cache,n=r.allocateTextureUnit();i[0]!==n&&(e.uniform1i(this.addr,n),i[0]=n),r.setTexture3D(t||Ed,n)}function I_(e,t,r){let i=this.cache,n=r.allocateTextureUnit();i[0]!==n&&(e.uniform1i(this.addr,n),i[0]=n),r.setTextureCube(t||Td,n)}function N_(e,t,r){let i=this.cache,n=r.allocateTextureUnit();i[0]!==n&&(e.uniform1i(this.addr,n),i[0]=n),r.setTexture2DArray(t||Sd,n)}function P_(e){switch(e){case 5126:return p_;case 35664:return f_;case 35665:return m_;case 35666:return g_;case 35674:return v_;case 35675:return __;case 35676:return b_;case 5124:case 35670:return x_;case 35667:case 35671:return y_;case 35668:case 35672:return S_;case 35669:case 35673:return E_;case 5125:return T_;case 36294:return M_;case 36295:return A_;case 36296:return w_;case 35678:case 36198:case 36298:case 36306:case 35682:return R_;case 35679:case 36299:case 36307:return C_;case 35680:case 36300:case 36308:case 36293:return I_;case 36289:case 36303:case 36311:case 36292:return N_}}function O_(e,t){e.uniform1fv(this.addr,t)}function L_(e,t){let r=qi(t,this.size,2);e.uniform2fv(this.addr,r)}function U_(e,t){let r=qi(t,this.size,3);e.uniform3fv(this.addr,r)}function D_(e,t){let r=qi(t,this.size,4);e.uniform4fv(this.addr,r)}function F_(e,t){let r=qi(t,this.size,4);e.uniformMatrix2fv(this.addr,!1,r)}function k_(e,t){let r=qi(t,this.size,9);e.uniformMatrix3fv(this.addr,!1,r)}function B_(e,t){let r=qi(t,this.size,16);e.uniformMatrix4fv(this.addr,!1,r)}function V_(e,t){e.uniform1iv(this.addr,t)}function z_(e,t){e.uniform2iv(this.addr,t)}function H_(e,t){e.uniform3iv(this.addr,t)}function G_(e,t){e.uniform4iv(this.addr,t)}function W_(e,t){e.uniform1uiv(this.addr,t)}function j_(e,t){e.uniform2uiv(this.addr,t)}function X_(e,t){e.uniform3uiv(this.addr,t)}function q_(e,t){e.uniform4uiv(this.addr,t)}function Y_(e,t,r){let i=this.cache,n=t.length,a=La(r,n);ct(i,a)||(e.uniform1iv(this.addr,a),ut(i,a));for(let o=0;o!==n;++o)r.setTexture2D(t[o]||yd,a[o])}function K_(e,t,r){let i=this.cache,n=t.length,a=La(r,n);ct(i,a)||(e.uniform1iv(this.addr,a),ut(i,a));for(let o=0;o!==n;++o)r.setTexture3D(t[o]||Ed,a[o])}function J_(e,t,r){let i=this.cache,n=t.length,a=La(r,n);ct(i,a)||(e.uniform1iv(this.addr,a),ut(i,a));for(let o=0;o!==n;++o)r.setTextureCube(t[o]||Td,a[o])}function Z_(e,t,r){let i=this.cache,n=t.length,a=La(r,n);ct(i,a)||(e.uniform1iv(this.addr,a),ut(i,a));for(let o=0;o!==n;++o)r.setTexture2DArray(t[o]||Sd,a[o])}function $_(e){switch(e){case 5126:return O_;case 35664:return L_;case 35665:return U_;case 35666:return D_;case 35674:return F_;case 35675:return k_;case 35676:return B_;case 5124:case 35670:return V_;case 35667:case 35671:return z_;case 35668:case 35672:return H_;case 35669:case 35673:return G_;case 5125:return W_;case 36294:return j_;case 36295:return X_;case 36296:return q_;case 35678:case 36198:case 36298:case 36306:case 35682:return Y_;case 35679:case 36299:case 36307:return K_;case 35680:case 36300:case 36308:case 36293:return J_;case 36289:case 36303:case 36311:case 36292:return Z_}}var Q_=class{constructor(e,t,r){this.id=e,this.addr=r,this.cache=[],this.type=t.type,this.setValue=P_(t.type)}},e0=class{constructor(e,t,r){this.id=e,this.addr=r,this.cache=[],this.type=t.type,this.size=t.size,this.setValue=$_(t.type)}},t0=class{constructor(e){this.id=e,this.seq=[],this.map={}}setValue(e,t,r){let i=this.seq;for(let n=0,a=i.length;n!==a;++n){let o=i[n];o.setValue(e,t[o.id],r)}}},is=/(\w+)(\])?(\[|\.)?/g;function Su(e,t){e.seq.push(t),e.map[t.id]=t}function r0(e,t,r){let i=e.name,n=i.length;for(is.lastIndex=0;;){let a=is.exec(i),o=is.lastIndex,s=a[1],c=a[2]==="]",u=a[3];if(c&&(s=s|0),u===void 0||u==="["&&o+2===n){Su(r,u===void 0?new Q_(s,e,t):new e0(s,e,t));break}else{let l=r.map[s];l===void 0&&(l=new t0(s),Su(r,l)),r=l}}}var Aa=class{constructor(e,t){this.seq=[],this.map={};let r=e.getProgramParameter(t,e.ACTIVE_UNIFORMS);for(let i=0;i<r;++i){let n=e.getActiveUniform(t,i),a=e.getUniformLocation(t,n.name);r0(n,a,this)}}setValue(e,t,r,i){let n=this.map[t];n!==void 0&&n.setValue(e,r,i)}setOptional(e,t,r){let i=t[r];i!==void 0&&this.setValue(e,r,i)}static upload(e,t,r,i){for(let n=0,a=t.length;n!==a;++n){let o=t[n],s=r[o.id];s.needsUpdate!==!1&&o.setValue(e,s.value,i)}}static seqWithValue(e,t){let r=[];for(let i=0,n=e.length;i!==n;++i){let a=e[i];a.id in t&&r.push(a)}return r}};function Eu(e,t,r){let i=e.createShader(t);return e.shaderSource(i,r),e.compileShader(i),i}var i0=37297,n0=0;function a0(e,t){let r=e.split(`
`),i=[],n=Math.max(t-6,0),a=Math.min(t+6,r.length);for(let o=n;o<a;o++){let s=o+1;i.push(`${s===t?">":" "} ${s}: ${r[o]}`)}return i.join(`
`)}var Tu=new Be;function o0(e){Xe._getMatrix(Tu,Xe.workingColorSpace,e);let t=`mat3( ${Tu.elements.map(r=>r.toFixed(4))} )`;switch(Xe.getTransfer(e)){case Ra:return[t,"LinearTransferOETF"];case Je:return[t,"sRGBTransferOETF"];default:return console.warn("THREE.WebGLProgram: Unsupported color space: ",e),[t,"LinearTransferOETF"]}}function Mu(e,t,r){let i=e.getShaderParameter(t,e.COMPILE_STATUS),n=(e.getShaderInfoLog(t)||"").trim();if(i&&n==="")return"";let a=/ERROR: 0:(\d+)/.exec(n);if(a){let o=parseInt(a[1]);return r.toUpperCase()+`

`+n+`

`+a0(e.getShaderSource(t),o)}else return n}function s0(e,t){let r=o0(t);return[`vec4 ${e}( vec4 value ) {`,`	return ${r[1]}( vec4( value.rgb * ${r[0]}, value.a ) );`,"}"].join(`
`)}function l0(e,t){let r;switch(t){case Yp:r="Linear";break;case Kp:r="Reinhard";break;case Jp:r="Cineon";break;case Zp:r="ACESFilmic";break;case Qp:r="AgX";break;case ef:r="Neutral";break;case $p:r="Custom";break;default:console.warn("THREE.WebGLProgram: Unsupported toneMapping:",t),r="Linear"}return"vec3 "+e+"( vec3 color ) { return "+r+"ToneMapping( color ); }"}var ba=new F;function c0(){Xe.getLuminanceCoefficients(ba);let e=ba.x.toFixed(4),t=ba.y.toFixed(4),r=ba.z.toFixed(4);return["float luminance( const in vec3 rgb ) {",`	const vec3 weights = vec3( ${e}, ${t}, ${r} );`,"	return dot( weights, rgb );","}"].join(`
`)}function u0(e){return[e.extensionClipCullDistance?"#extension GL_ANGLE_clip_cull_distance : require":"",e.extensionMultiDraw?"#extension GL_ANGLE_multi_draw : require":""].filter(cn).join(`
`)}function d0(e){let t=[];for(let r in e){let i=e[r];i!==!1&&t.push("#define "+r+" "+i)}return t.join(`
`)}function h0(e,t){let r={},i=e.getProgramParameter(t,e.ACTIVE_ATTRIBUTES);for(let n=0;n<i;n++){let a=e.getActiveAttrib(t,n),o=a.name,s=1;a.type===e.FLOAT_MAT2&&(s=2),a.type===e.FLOAT_MAT3&&(s=3),a.type===e.FLOAT_MAT4&&(s=4),r[o]={type:a.type,location:e.getAttribLocation(t,o),locationSize:s}}return r}function cn(e){return e!==""}function Au(e,t){let r=t.numSpotLightShadows+t.numSpotLightMaps-t.numSpotLightShadowsWithMaps;return e.replace(/NUM_DIR_LIGHTS/g,t.numDirLights).replace(/NUM_SPOT_LIGHTS/g,t.numSpotLights).replace(/NUM_SPOT_LIGHT_MAPS/g,t.numSpotLightMaps).replace(/NUM_SPOT_LIGHT_COORDS/g,r).replace(/NUM_RECT_AREA_LIGHTS/g,t.numRectAreaLights).replace(/NUM_POINT_LIGHTS/g,t.numPointLights).replace(/NUM_HEMI_LIGHTS/g,t.numHemiLights).replace(/NUM_DIR_LIGHT_SHADOWS/g,t.numDirLightShadows).replace(/NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS/g,t.numSpotLightShadowsWithMaps).replace(/NUM_SPOT_LIGHT_SHADOWS/g,t.numSpotLightShadows).replace(/NUM_POINT_LIGHT_SHADOWS/g,t.numPointLightShadows)}function wu(e,t){return e.replace(/NUM_CLIPPING_PLANES/g,t.numClippingPlanes).replace(/UNION_CLIPPING_PLANES/g,t.numClippingPlanes-t.numClipIntersection)}var p0=/^[ \t]*#include +<([\w\d./]+)>/gm;function Ys(e){return e.replace(p0,m0)}var f0=new Map;function m0(e,t){let r=ke[t];if(r===void 0){let i=f0.get(t);if(i!==void 0)r=ke[i],console.warn('THREE.WebGLRenderer: Shader chunk "%s" has been deprecated. Use "%s" instead.',t,i);else throw new Error("Can not resolve #include <"+t+">")}return Ys(r)}var g0=/#pragma unroll_loop_start\s+for\s*\(\s*int\s+i\s*=\s*(\d+)\s*;\s*i\s*<\s*(\d+)\s*;\s*i\s*\+\+\s*\)\s*{([\s\S]+?)}\s+#pragma unroll_loop_end/g;function Ru(e){return e.replace(g0,v0)}function v0(e,t,r,i){let n="";for(let a=parseInt(t);a<parseInt(r);a++)n+=i.replace(/\[\s*i\s*\]/g,"[ "+a+" ]").replace(/UNROLLED_LOOP_INDEX/g,a);return n}function Cu(e){let t=`precision ${e.precision} float;
	precision ${e.precision} int;
	precision ${e.precision} sampler2D;
	precision ${e.precision} samplerCube;
	precision ${e.precision} sampler3D;
	precision ${e.precision} sampler2DArray;
	precision ${e.precision} sampler2DShadow;
	precision ${e.precision} samplerCubeShadow;
	precision ${e.precision} sampler2DArrayShadow;
	precision ${e.precision} isampler2D;
	precision ${e.precision} isampler3D;
	precision ${e.precision} isamplerCube;
	precision ${e.precision} isampler2DArray;
	precision ${e.precision} usampler2D;
	precision ${e.precision} usampler3D;
	precision ${e.precision} usamplerCube;
	precision ${e.precision} usampler2DArray;
	`;return e.precision==="highp"?t+=`
#define HIGH_PRECISION`:e.precision==="mediump"?t+=`
#define MEDIUM_PRECISION`:e.precision==="lowp"&&(t+=`
#define LOW_PRECISION`),t}function _0(e){let t="SHADOWMAP_TYPE_BASIC";return e.shadowMapType===Lu?t="SHADOWMAP_TYPE_PCF":e.shadowMapType===wp?t="SHADOWMAP_TYPE_PCF_SOFT":e.shadowMapType===Er&&(t="SHADOWMAP_TYPE_VSM"),t}function b0(e){let t="ENVMAP_TYPE_CUBE";if(e.envMap)switch(e.envMapMode){case zi:case Hi:t="ENVMAP_TYPE_CUBE";break;case Na:t="ENVMAP_TYPE_CUBE_UV";break}return t}function x0(e){let t="ENVMAP_MODE_REFLECTION";if(e.envMap)switch(e.envMapMode){case Hi:t="ENVMAP_MODE_REFRACTION";break}return t}function y0(e){let t="ENVMAP_BLENDING_NONE";if(e.envMap)switch(e.combine){case Uu:t="ENVMAP_BLENDING_MULTIPLY";break;case Xp:t="ENVMAP_BLENDING_MIX";break;case qp:t="ENVMAP_BLENDING_ADD";break}return t}function S0(e){let t=e.envMapCubeUVHeight;if(t===null)return null;let r=Math.log2(t)-2,i=1/t;return{texelWidth:1/(3*Math.max(Math.pow(2,r),112)),texelHeight:i,maxMip:r}}function E0(e,t,r,i){let n=e.getContext(),a=r.defines,o=r.vertexShader,s=r.fragmentShader,c=_0(r),u=b0(r),l=x0(r),d=y0(r),h=S0(r),m=u0(r),g=d0(a),_=n.createProgram(),f,p,R=r.glslVersion?"#version "+r.glslVersion+`
`:"";r.isRawShaderMaterial?(f=["#define SHADER_TYPE "+r.shaderType,"#define SHADER_NAME "+r.shaderName,g].filter(cn).join(`
`),f.length>0&&(f+=`
`),p=["#define SHADER_TYPE "+r.shaderType,"#define SHADER_NAME "+r.shaderName,g].filter(cn).join(`
`),p.length>0&&(p+=`
`)):(f=[Cu(r),"#define SHADER_TYPE "+r.shaderType,"#define SHADER_NAME "+r.shaderName,g,r.extensionClipCullDistance?"#define USE_CLIP_DISTANCE":"",r.batching?"#define USE_BATCHING":"",r.batchingColor?"#define USE_BATCHING_COLOR":"",r.instancing?"#define USE_INSTANCING":"",r.instancingColor?"#define USE_INSTANCING_COLOR":"",r.instancingMorph?"#define USE_INSTANCING_MORPH":"",r.useFog&&r.fog?"#define USE_FOG":"",r.useFog&&r.fogExp2?"#define FOG_EXP2":"",r.map?"#define USE_MAP":"",r.envMap?"#define USE_ENVMAP":"",r.envMap?"#define "+l:"",r.lightMap?"#define USE_LIGHTMAP":"",r.aoMap?"#define USE_AOMAP":"",r.bumpMap?"#define USE_BUMPMAP":"",r.normalMap?"#define USE_NORMALMAP":"",r.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",r.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",r.displacementMap?"#define USE_DISPLACEMENTMAP":"",r.emissiveMap?"#define USE_EMISSIVEMAP":"",r.anisotropy?"#define USE_ANISOTROPY":"",r.anisotropyMap?"#define USE_ANISOTROPYMAP":"",r.clearcoatMap?"#define USE_CLEARCOATMAP":"",r.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",r.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",r.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",r.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",r.specularMap?"#define USE_SPECULARMAP":"",r.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",r.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",r.roughnessMap?"#define USE_ROUGHNESSMAP":"",r.metalnessMap?"#define USE_METALNESSMAP":"",r.alphaMap?"#define USE_ALPHAMAP":"",r.alphaHash?"#define USE_ALPHAHASH":"",r.transmission?"#define USE_TRANSMISSION":"",r.transmissionMap?"#define USE_TRANSMISSIONMAP":"",r.thicknessMap?"#define USE_THICKNESSMAP":"",r.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",r.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",r.mapUv?"#define MAP_UV "+r.mapUv:"",r.alphaMapUv?"#define ALPHAMAP_UV "+r.alphaMapUv:"",r.lightMapUv?"#define LIGHTMAP_UV "+r.lightMapUv:"",r.aoMapUv?"#define AOMAP_UV "+r.aoMapUv:"",r.emissiveMapUv?"#define EMISSIVEMAP_UV "+r.emissiveMapUv:"",r.bumpMapUv?"#define BUMPMAP_UV "+r.bumpMapUv:"",r.normalMapUv?"#define NORMALMAP_UV "+r.normalMapUv:"",r.displacementMapUv?"#define DISPLACEMENTMAP_UV "+r.displacementMapUv:"",r.metalnessMapUv?"#define METALNESSMAP_UV "+r.metalnessMapUv:"",r.roughnessMapUv?"#define ROUGHNESSMAP_UV "+r.roughnessMapUv:"",r.anisotropyMapUv?"#define ANISOTROPYMAP_UV "+r.anisotropyMapUv:"",r.clearcoatMapUv?"#define CLEARCOATMAP_UV "+r.clearcoatMapUv:"",r.clearcoatNormalMapUv?"#define CLEARCOAT_NORMALMAP_UV "+r.clearcoatNormalMapUv:"",r.clearcoatRoughnessMapUv?"#define CLEARCOAT_ROUGHNESSMAP_UV "+r.clearcoatRoughnessMapUv:"",r.iridescenceMapUv?"#define IRIDESCENCEMAP_UV "+r.iridescenceMapUv:"",r.iridescenceThicknessMapUv?"#define IRIDESCENCE_THICKNESSMAP_UV "+r.iridescenceThicknessMapUv:"",r.sheenColorMapUv?"#define SHEEN_COLORMAP_UV "+r.sheenColorMapUv:"",r.sheenRoughnessMapUv?"#define SHEEN_ROUGHNESSMAP_UV "+r.sheenRoughnessMapUv:"",r.specularMapUv?"#define SPECULARMAP_UV "+r.specularMapUv:"",r.specularColorMapUv?"#define SPECULAR_COLORMAP_UV "+r.specularColorMapUv:"",r.specularIntensityMapUv?"#define SPECULAR_INTENSITYMAP_UV "+r.specularIntensityMapUv:"",r.transmissionMapUv?"#define TRANSMISSIONMAP_UV "+r.transmissionMapUv:"",r.thicknessMapUv?"#define THICKNESSMAP_UV "+r.thicknessMapUv:"",r.vertexTangents&&r.flatShading===!1?"#define USE_TANGENT":"",r.vertexColors?"#define USE_COLOR":"",r.vertexAlphas?"#define USE_COLOR_ALPHA":"",r.vertexUv1s?"#define USE_UV1":"",r.vertexUv2s?"#define USE_UV2":"",r.vertexUv3s?"#define USE_UV3":"",r.pointsUvs?"#define USE_POINTS_UV":"",r.flatShading?"#define FLAT_SHADED":"",r.skinning?"#define USE_SKINNING":"",r.morphTargets?"#define USE_MORPHTARGETS":"",r.morphNormals&&r.flatShading===!1?"#define USE_MORPHNORMALS":"",r.morphColors?"#define USE_MORPHCOLORS":"",r.morphTargetsCount>0?"#define MORPHTARGETS_TEXTURE_STRIDE "+r.morphTextureStride:"",r.morphTargetsCount>0?"#define MORPHTARGETS_COUNT "+r.morphTargetsCount:"",r.doubleSided?"#define DOUBLE_SIDED":"",r.flipSided?"#define FLIP_SIDED":"",r.shadowMapEnabled?"#define USE_SHADOWMAP":"",r.shadowMapEnabled?"#define "+c:"",r.sizeAttenuation?"#define USE_SIZEATTENUATION":"",r.numLightProbes>0?"#define USE_LIGHT_PROBES":"",r.logarithmicDepthBuffer?"#define USE_LOGARITHMIC_DEPTH_BUFFER":"",r.reversedDepthBuffer?"#define USE_REVERSED_DEPTH_BUFFER":"","uniform mat4 modelMatrix;","uniform mat4 modelViewMatrix;","uniform mat4 projectionMatrix;","uniform mat4 viewMatrix;","uniform mat3 normalMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;","#ifdef USE_INSTANCING","	attribute mat4 instanceMatrix;","#endif","#ifdef USE_INSTANCING_COLOR","	attribute vec3 instanceColor;","#endif","#ifdef USE_INSTANCING_MORPH","	uniform sampler2D morphTexture;","#endif","attribute vec3 position;","attribute vec3 normal;","attribute vec2 uv;","#ifdef USE_UV1","	attribute vec2 uv1;","#endif","#ifdef USE_UV2","	attribute vec2 uv2;","#endif","#ifdef USE_UV3","	attribute vec2 uv3;","#endif","#ifdef USE_TANGENT","	attribute vec4 tangent;","#endif","#if defined( USE_COLOR_ALPHA )","	attribute vec4 color;","#elif defined( USE_COLOR )","	attribute vec3 color;","#endif","#ifdef USE_SKINNING","	attribute vec4 skinIndex;","	attribute vec4 skinWeight;","#endif",`
`].filter(cn).join(`
`),p=[Cu(r),"#define SHADER_TYPE "+r.shaderType,"#define SHADER_NAME "+r.shaderName,g,r.useFog&&r.fog?"#define USE_FOG":"",r.useFog&&r.fogExp2?"#define FOG_EXP2":"",r.alphaToCoverage?"#define ALPHA_TO_COVERAGE":"",r.map?"#define USE_MAP":"",r.matcap?"#define USE_MATCAP":"",r.envMap?"#define USE_ENVMAP":"",r.envMap?"#define "+u:"",r.envMap?"#define "+l:"",r.envMap?"#define "+d:"",h?"#define CUBEUV_TEXEL_WIDTH "+h.texelWidth:"",h?"#define CUBEUV_TEXEL_HEIGHT "+h.texelHeight:"",h?"#define CUBEUV_MAX_MIP "+h.maxMip+".0":"",r.lightMap?"#define USE_LIGHTMAP":"",r.aoMap?"#define USE_AOMAP":"",r.bumpMap?"#define USE_BUMPMAP":"",r.normalMap?"#define USE_NORMALMAP":"",r.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",r.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",r.emissiveMap?"#define USE_EMISSIVEMAP":"",r.anisotropy?"#define USE_ANISOTROPY":"",r.anisotropyMap?"#define USE_ANISOTROPYMAP":"",r.clearcoat?"#define USE_CLEARCOAT":"",r.clearcoatMap?"#define USE_CLEARCOATMAP":"",r.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",r.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",r.dispersion?"#define USE_DISPERSION":"",r.iridescence?"#define USE_IRIDESCENCE":"",r.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",r.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",r.specularMap?"#define USE_SPECULARMAP":"",r.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",r.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",r.roughnessMap?"#define USE_ROUGHNESSMAP":"",r.metalnessMap?"#define USE_METALNESSMAP":"",r.alphaMap?"#define USE_ALPHAMAP":"",r.alphaTest?"#define USE_ALPHATEST":"",r.alphaHash?"#define USE_ALPHAHASH":"",r.sheen?"#define USE_SHEEN":"",r.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",r.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",r.transmission?"#define USE_TRANSMISSION":"",r.transmissionMap?"#define USE_TRANSMISSIONMAP":"",r.thicknessMap?"#define USE_THICKNESSMAP":"",r.vertexTangents&&r.flatShading===!1?"#define USE_TANGENT":"",r.vertexColors||r.instancingColor||r.batchingColor?"#define USE_COLOR":"",r.vertexAlphas?"#define USE_COLOR_ALPHA":"",r.vertexUv1s?"#define USE_UV1":"",r.vertexUv2s?"#define USE_UV2":"",r.vertexUv3s?"#define USE_UV3":"",r.pointsUvs?"#define USE_POINTS_UV":"",r.gradientMap?"#define USE_GRADIENTMAP":"",r.flatShading?"#define FLAT_SHADED":"",r.doubleSided?"#define DOUBLE_SIDED":"",r.flipSided?"#define FLIP_SIDED":"",r.shadowMapEnabled?"#define USE_SHADOWMAP":"",r.shadowMapEnabled?"#define "+c:"",r.premultipliedAlpha?"#define PREMULTIPLIED_ALPHA":"",r.numLightProbes>0?"#define USE_LIGHT_PROBES":"",r.decodeVideoTexture?"#define DECODE_VIDEO_TEXTURE":"",r.decodeVideoTextureEmissive?"#define DECODE_VIDEO_TEXTURE_EMISSIVE":"",r.logarithmicDepthBuffer?"#define USE_LOGARITHMIC_DEPTH_BUFFER":"",r.reversedDepthBuffer?"#define USE_REVERSED_DEPTH_BUFFER":"","uniform mat4 viewMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;",r.toneMapping!==Br?"#define TONE_MAPPING":"",r.toneMapping!==Br?ke.tonemapping_pars_fragment:"",r.toneMapping!==Br?l0("toneMapping",r.toneMapping):"",r.dithering?"#define DITHERING":"",r.opaque?"#define OPAQUE":"",ke.colorspace_pars_fragment,s0("linearToOutputTexel",r.outputColorSpace),c0(),r.useDepthPacking?"#define DEPTH_PACKING "+r.depthPacking:"",`
`].filter(cn).join(`
`)),o=Ys(o),o=Au(o,r),o=wu(o,r),s=Ys(s),s=Au(s,r),s=wu(s,r),o=Ru(o),s=Ru(s),r.isRawShaderMaterial!==!0&&(R=`#version 300 es
`,f=[m,"#define attribute in","#define varying out","#define texture2D texture"].join(`
`)+`
`+f,p=["#define varying in",r.glslVersion===Hc?"":"layout(location = 0) out highp vec4 pc_fragColor;",r.glslVersion===Hc?"":"#define gl_FragColor pc_fragColor","#define gl_FragDepthEXT gl_FragDepth","#define texture2D texture","#define textureCube texture","#define texture2DProj textureProj","#define texture2DLodEXT textureLod","#define texture2DProjLodEXT textureProjLod","#define textureCubeLodEXT textureLod","#define texture2DGradEXT textureGrad","#define texture2DProjGradEXT textureProjGrad","#define textureCubeGradEXT textureGrad"].join(`
`)+`
`+p);let y=R+f+o,A=R+p+s,O=Eu(n,n.VERTEX_SHADER,y),I=Eu(n,n.FRAGMENT_SHADER,A);n.attachShader(_,O),n.attachShader(_,I),r.index0AttributeName!==void 0?n.bindAttribLocation(_,0,r.index0AttributeName):r.morphTargets===!0&&n.bindAttribLocation(_,0,"position"),n.linkProgram(_);function C(M){if(e.debug.checkShaderErrors){let k=n.getProgramInfoLog(_)||"",H=n.getShaderInfoLog(O)||"",V=n.getShaderInfoLog(I)||"",Z=k.trim(),G=H.trim(),ee=V.trim(),W=!0,ie=!0;if(n.getProgramParameter(_,n.LINK_STATUS)===!1)if(W=!1,typeof e.debug.onShaderError=="function")e.debug.onShaderError(n,_,O,I);else{let ce=Mu(n,O,"vertex"),Pe=Mu(n,I,"fragment");console.error("THREE.WebGLProgram: Shader Error "+n.getError()+" - VALIDATE_STATUS "+n.getProgramParameter(_,n.VALIDATE_STATUS)+`

Material Name: `+M.name+`
Material Type: `+M.type+`

Program Info Log: `+Z+`
`+ce+`
`+Pe)}else Z!==""?console.warn("THREE.WebGLProgram: Program Info Log:",Z):(G===""||ee==="")&&(ie=!1);ie&&(M.diagnostics={runnable:W,programLog:Z,vertexShader:{log:G,prefix:f},fragmentShader:{log:ee,prefix:p}})}n.deleteShader(O),n.deleteShader(I),U=new Aa(n,_),S=h0(n,_)}let U;this.getUniforms=function(){return U===void 0&&C(this),U};let S;this.getAttributes=function(){return S===void 0&&C(this),S};let x=r.rendererExtensionParallelShaderCompile===!1;return this.isReady=function(){return x===!1&&(x=n.getProgramParameter(_,i0)),x},this.destroy=function(){i.releaseStatesOfProgram(this),n.deleteProgram(_),this.program=void 0},this.type=r.shaderType,this.name=r.shaderName,this.id=n0++,this.cacheKey=t,this.usedTimes=1,this.program=_,this.vertexShader=O,this.fragmentShader=I,this}var T0=0,M0=class{constructor(){this.shaderCache=new Map,this.materialCache=new Map}update(e){let t=e.vertexShader,r=e.fragmentShader,i=this._getShaderStage(t),n=this._getShaderStage(r),a=this._getShaderCacheForMaterial(e);return a.has(i)===!1&&(a.add(i),i.usedTimes++),a.has(n)===!1&&(a.add(n),n.usedTimes++),this}remove(e){let t=this.materialCache.get(e);for(let r of t)r.usedTimes--,r.usedTimes===0&&this.shaderCache.delete(r.code);return this.materialCache.delete(e),this}getVertexShaderID(e){return this._getShaderStage(e.vertexShader).id}getFragmentShaderID(e){return this._getShaderStage(e.fragmentShader).id}dispose(){this.shaderCache.clear(),this.materialCache.clear()}_getShaderCacheForMaterial(e){let t=this.materialCache,r=t.get(e);return r===void 0&&(r=new Set,t.set(e,r)),r}_getShaderStage(e){let t=this.shaderCache,r=t.get(e);return r===void 0&&(r=new A0(e),t.set(e,r)),r}},A0=class{constructor(e){this.id=T0++,this.code=e,this.usedTimes=0}};function w0(e,t,r,i,n,a,o){let s=new ed,c=new M0,u=new Set,l=[],d=n.logarithmicDepthBuffer,h=n.vertexTextures,m=n.precision,g={MeshDepthMaterial:"depth",MeshDistanceMaterial:"distanceRGBA",MeshNormalMaterial:"normal",MeshBasicMaterial:"basic",MeshLambertMaterial:"lambert",MeshPhongMaterial:"phong",MeshToonMaterial:"toon",MeshStandardMaterial:"physical",MeshPhysicalMaterial:"physical",MeshMatcapMaterial:"matcap",LineBasicMaterial:"basic",LineDashedMaterial:"dashed",PointsMaterial:"points",ShadowMaterial:"shadow",SpriteMaterial:"sprite"};function _(S){return u.add(S),S===0?"uv":`uv${S}`}function f(S,x,M,k,H){let V=k.fog,Z=H.geometry,G=S.isMeshStandardMaterial?k.environment:null,ee=(S.isMeshStandardMaterial?r:t).get(S.envMap||G),W=ee&&ee.mapping===Na?ee.image.height:null,ie=g[S.type];S.precision!==null&&(m=n.getMaxPrecision(S.precision),m!==S.precision&&console.warn("THREE.WebGLProgram.getParameters:",S.precision,"not supported, using",m,"instead."));let ce=Z.morphAttributes.position||Z.morphAttributes.normal||Z.morphAttributes.color,Pe=ce!==void 0?ce.length:0,Fe=0;Z.morphAttributes.position!==void 0&&(Fe=1),Z.morphAttributes.normal!==void 0&&(Fe=2),Z.morphAttributes.color!==void 0&&(Fe=3);let $e,We,j,oe;if(ie){let Ke=nr[ie];$e=Ke.vertexShader,We=Ke.fragmentShader}else $e=S.vertexShader,We=S.fragmentShader,c.update(S),j=c.getVertexShaderID(S),oe=c.getFragmentShaderID(S);let ne=e.getRenderTarget(),z=e.state.buffers.depth.getReversed(),ae=H.isInstancedMesh===!0,$=H.isBatchedMesh===!0,ge=!!S.map,T=!!S.matcap,Se=!!ee,Ee=!!S.aoMap,Ve=!!S.lightMap,fe=!!S.bumpMap,Ze=!!S.normalMap,Re=!!S.displacementMap,Ce=!!S.emissiveMap,mt=!!S.metalnessMap,dt=!!S.roughnessMap,at=S.anisotropy>0,E=S.clearcoat>0,v=S.dispersion>0,L=S.iridescence>0,Y=S.sheen>0,J=S.transmission>0,X=at&&!!S.anisotropyMap,be=E&&!!S.clearcoatMap,se=E&&!!S.clearcoatNormalMap,Te=E&&!!S.clearcoatRoughnessMap,Ae=L&&!!S.iridescenceMap,re=L&&!!S.iridescenceThicknessMap,de=Y&&!!S.sheenColorMap,Ne=Y&&!!S.sheenRoughnessMap,we=!!S.specularMap,pe=!!S.specularColorMap,ze=!!S.specularIntensityMap,w=J&&!!S.transmissionMap,he=J&&!!S.thicknessMap,le=!!S.gradientMap,ye=!!S.alphaMap,te=S.alphaTest>0,K=!!S.alphaHash,xe=!!S.extensions,Ie=Br;S.toneMapped&&(ne===null||ne.isXRRenderTarget===!0)&&(Ie=e.toneMapping);let ot={shaderID:ie,shaderType:S.type,shaderName:S.name,vertexShader:$e,fragmentShader:We,defines:S.defines,customVertexShaderID:j,customFragmentShaderID:oe,isRawShaderMaterial:S.isRawShaderMaterial===!0,glslVersion:S.glslVersion,precision:m,batching:$,batchingColor:$&&H._colorsTexture!==null,instancing:ae,instancingColor:ae&&H.instanceColor!==null,instancingMorph:ae&&H.morphTexture!==null,supportsVertexTextures:h,outputColorSpace:ne===null?e.outputColorSpace:ne.isXRRenderTarget===!0?ne.texture.colorSpace:Gi,alphaToCoverage:!!S.alphaToCoverage,map:ge,matcap:T,envMap:Se,envMapMode:Se&&ee.mapping,envMapCubeUVHeight:W,aoMap:Ee,lightMap:Ve,bumpMap:fe,normalMap:Ze,displacementMap:h&&Re,emissiveMap:Ce,normalMapObjectSpace:Ze&&S.normalMapType===af,normalMapTangentSpace:Ze&&S.normalMapType===ju,metalnessMap:mt,roughnessMap:dt,anisotropy:at,anisotropyMap:X,clearcoat:E,clearcoatMap:be,clearcoatNormalMap:se,clearcoatRoughnessMap:Te,dispersion:v,iridescence:L,iridescenceMap:Ae,iridescenceThicknessMap:re,sheen:Y,sheenColorMap:de,sheenRoughnessMap:Ne,specularMap:we,specularColorMap:pe,specularIntensityMap:ze,transmission:J,transmissionMap:w,thicknessMap:he,gradientMap:le,opaque:S.transparent===!1&&S.blending===ki&&S.alphaToCoverage===!1,alphaMap:ye,alphaTest:te,alphaHash:K,combine:S.combine,mapUv:ge&&_(S.map.channel),aoMapUv:Ee&&_(S.aoMap.channel),lightMapUv:Ve&&_(S.lightMap.channel),bumpMapUv:fe&&_(S.bumpMap.channel),normalMapUv:Ze&&_(S.normalMap.channel),displacementMapUv:Re&&_(S.displacementMap.channel),emissiveMapUv:Ce&&_(S.emissiveMap.channel),metalnessMapUv:mt&&_(S.metalnessMap.channel),roughnessMapUv:dt&&_(S.roughnessMap.channel),anisotropyMapUv:X&&_(S.anisotropyMap.channel),clearcoatMapUv:be&&_(S.clearcoatMap.channel),clearcoatNormalMapUv:se&&_(S.clearcoatNormalMap.channel),clearcoatRoughnessMapUv:Te&&_(S.clearcoatRoughnessMap.channel),iridescenceMapUv:Ae&&_(S.iridescenceMap.channel),iridescenceThicknessMapUv:re&&_(S.iridescenceThicknessMap.channel),sheenColorMapUv:de&&_(S.sheenColorMap.channel),sheenRoughnessMapUv:Ne&&_(S.sheenRoughnessMap.channel),specularMapUv:we&&_(S.specularMap.channel),specularColorMapUv:pe&&_(S.specularColorMap.channel),specularIntensityMapUv:ze&&_(S.specularIntensityMap.channel),transmissionMapUv:w&&_(S.transmissionMap.channel),thicknessMapUv:he&&_(S.thicknessMap.channel),alphaMapUv:ye&&_(S.alphaMap.channel),vertexTangents:!!Z.attributes.tangent&&(Ze||at),vertexColors:S.vertexColors,vertexAlphas:S.vertexColors===!0&&!!Z.attributes.color&&Z.attributes.color.itemSize===4,pointsUvs:H.isPoints===!0&&!!Z.attributes.uv&&(ge||ye),fog:!!V,useFog:S.fog===!0,fogExp2:!!V&&V.isFogExp2,flatShading:S.flatShading===!0&&S.wireframe===!1,sizeAttenuation:S.sizeAttenuation===!0,logarithmicDepthBuffer:d,reversedDepthBuffer:z,skinning:H.isSkinnedMesh===!0,morphTargets:Z.morphAttributes.position!==void 0,morphNormals:Z.morphAttributes.normal!==void 0,morphColors:Z.morphAttributes.color!==void 0,morphTargetsCount:Pe,morphTextureStride:Fe,numDirLights:x.directional.length,numPointLights:x.point.length,numSpotLights:x.spot.length,numSpotLightMaps:x.spotLightMap.length,numRectAreaLights:x.rectArea.length,numHemiLights:x.hemi.length,numDirLightShadows:x.directionalShadowMap.length,numPointLightShadows:x.pointShadowMap.length,numSpotLightShadows:x.spotShadowMap.length,numSpotLightShadowsWithMaps:x.numSpotLightShadowsWithMaps,numLightProbes:x.numLightProbes,numClippingPlanes:o.numPlanes,numClipIntersection:o.numIntersection,dithering:S.dithering,shadowMapEnabled:e.shadowMap.enabled&&M.length>0,shadowMapType:e.shadowMap.type,toneMapping:Ie,decodeVideoTexture:ge&&S.map.isVideoTexture===!0&&Xe.getTransfer(S.map.colorSpace)===Je,decodeVideoTextureEmissive:Ce&&S.emissiveMap.isVideoTexture===!0&&Xe.getTransfer(S.emissiveMap.colorSpace)===Je,premultipliedAlpha:S.premultipliedAlpha,doubleSided:S.side===Tr,flipSided:S.side===Rt,useDepthPacking:S.depthPacking>=0,depthPacking:S.depthPacking||0,index0AttributeName:S.index0AttributeName,extensionClipCullDistance:xe&&S.extensions.clipCullDistance===!0&&i.has("WEBGL_clip_cull_distance"),extensionMultiDraw:(xe&&S.extensions.multiDraw===!0||$)&&i.has("WEBGL_multi_draw"),rendererExtensionParallelShaderCompile:i.has("KHR_parallel_shader_compile"),customProgramCacheKey:S.customProgramCacheKey()};return ot.vertexUv1s=u.has(1),ot.vertexUv2s=u.has(2),ot.vertexUv3s=u.has(3),u.clear(),ot}function p(S){let x=[];if(S.shaderID?x.push(S.shaderID):(x.push(S.customVertexShaderID),x.push(S.customFragmentShaderID)),S.defines!==void 0)for(let M in S.defines)x.push(M),x.push(S.defines[M]);return S.isRawShaderMaterial===!1&&(R(x,S),y(x,S),x.push(e.outputColorSpace)),x.push(S.customProgramCacheKey),x.join()}function R(S,x){S.push(x.precision),S.push(x.outputColorSpace),S.push(x.envMapMode),S.push(x.envMapCubeUVHeight),S.push(x.mapUv),S.push(x.alphaMapUv),S.push(x.lightMapUv),S.push(x.aoMapUv),S.push(x.bumpMapUv),S.push(x.normalMapUv),S.push(x.displacementMapUv),S.push(x.emissiveMapUv),S.push(x.metalnessMapUv),S.push(x.roughnessMapUv),S.push(x.anisotropyMapUv),S.push(x.clearcoatMapUv),S.push(x.clearcoatNormalMapUv),S.push(x.clearcoatRoughnessMapUv),S.push(x.iridescenceMapUv),S.push(x.iridescenceThicknessMapUv),S.push(x.sheenColorMapUv),S.push(x.sheenRoughnessMapUv),S.push(x.specularMapUv),S.push(x.specularColorMapUv),S.push(x.specularIntensityMapUv),S.push(x.transmissionMapUv),S.push(x.thicknessMapUv),S.push(x.combine),S.push(x.fogExp2),S.push(x.sizeAttenuation),S.push(x.morphTargetsCount),S.push(x.morphAttributeCount),S.push(x.numDirLights),S.push(x.numPointLights),S.push(x.numSpotLights),S.push(x.numSpotLightMaps),S.push(x.numHemiLights),S.push(x.numRectAreaLights),S.push(x.numDirLightShadows),S.push(x.numPointLightShadows),S.push(x.numSpotLightShadows),S.push(x.numSpotLightShadowsWithMaps),S.push(x.numLightProbes),S.push(x.shadowMapType),S.push(x.toneMapping),S.push(x.numClippingPlanes),S.push(x.numClipIntersection),S.push(x.depthPacking)}function y(S,x){s.disableAll(),x.supportsVertexTextures&&s.enable(0),x.instancing&&s.enable(1),x.instancingColor&&s.enable(2),x.instancingMorph&&s.enable(3),x.matcap&&s.enable(4),x.envMap&&s.enable(5),x.normalMapObjectSpace&&s.enable(6),x.normalMapTangentSpace&&s.enable(7),x.clearcoat&&s.enable(8),x.iridescence&&s.enable(9),x.alphaTest&&s.enable(10),x.vertexColors&&s.enable(11),x.vertexAlphas&&s.enable(12),x.vertexUv1s&&s.enable(13),x.vertexUv2s&&s.enable(14),x.vertexUv3s&&s.enable(15),x.vertexTangents&&s.enable(16),x.anisotropy&&s.enable(17),x.alphaHash&&s.enable(18),x.batching&&s.enable(19),x.dispersion&&s.enable(20),x.batchingColor&&s.enable(21),x.gradientMap&&s.enable(22),S.push(s.mask),s.disableAll(),x.fog&&s.enable(0),x.useFog&&s.enable(1),x.flatShading&&s.enable(2),x.logarithmicDepthBuffer&&s.enable(3),x.reversedDepthBuffer&&s.enable(4),x.skinning&&s.enable(5),x.morphTargets&&s.enable(6),x.morphNormals&&s.enable(7),x.morphColors&&s.enable(8),x.premultipliedAlpha&&s.enable(9),x.shadowMapEnabled&&s.enable(10),x.doubleSided&&s.enable(11),x.flipSided&&s.enable(12),x.useDepthPacking&&s.enable(13),x.dithering&&s.enable(14),x.transmission&&s.enable(15),x.sheen&&s.enable(16),x.opaque&&s.enable(17),x.pointsUvs&&s.enable(18),x.decodeVideoTexture&&s.enable(19),x.decodeVideoTextureEmissive&&s.enable(20),x.alphaToCoverage&&s.enable(21),S.push(s.mask)}function A(S){let x=g[S.type],M;if(x){let k=nr[x];M=Uf.clone(k.uniforms)}else M=S.uniforms;return M}function O(S,x){let M;for(let k=0,H=l.length;k<H;k++){let V=l[k];if(V.cacheKey===x){M=V,++M.usedTimes;break}}return M===void 0&&(M=new E0(e,x,S,a),l.push(M)),M}function I(S){if(--S.usedTimes===0){let x=l.indexOf(S);l[x]=l[l.length-1],l.pop(),S.destroy()}}function C(S){c.remove(S)}function U(){c.dispose()}return{getParameters:f,getProgramCacheKey:p,getUniforms:A,acquireProgram:O,releaseProgram:I,releaseShaderCache:C,programs:l,dispose:U}}function R0(){let e=new WeakMap;function t(o){return e.has(o)}function r(o){let s=e.get(o);return s===void 0&&(s={},e.set(o,s)),s}function i(o){e.delete(o)}function n(o,s,c){e.get(o)[s]=c}function a(){e=new WeakMap}return{has:t,get:r,remove:i,update:n,dispose:a}}function C0(e,t){return e.groupOrder!==t.groupOrder?e.groupOrder-t.groupOrder:e.renderOrder!==t.renderOrder?e.renderOrder-t.renderOrder:e.material.id!==t.material.id?e.material.id-t.material.id:e.z!==t.z?e.z-t.z:e.id-t.id}function Iu(e,t){return e.groupOrder!==t.groupOrder?e.groupOrder-t.groupOrder:e.renderOrder!==t.renderOrder?e.renderOrder-t.renderOrder:e.z!==t.z?t.z-e.z:e.id-t.id}function Nu(){let e=[],t=0,r=[],i=[],n=[];function a(){t=0,r.length=0,i.length=0,n.length=0}function o(d,h,m,g,_,f){let p=e[t];return p===void 0?(p={id:d.id,object:d,geometry:h,material:m,groupOrder:g,renderOrder:d.renderOrder,z:_,group:f},e[t]=p):(p.id=d.id,p.object=d,p.geometry=h,p.material=m,p.groupOrder=g,p.renderOrder=d.renderOrder,p.z=_,p.group=f),t++,p}function s(d,h,m,g,_,f){let p=o(d,h,m,g,_,f);m.transmission>0?i.push(p):m.transparent===!0?n.push(p):r.push(p)}function c(d,h,m,g,_,f){let p=o(d,h,m,g,_,f);m.transmission>0?i.unshift(p):m.transparent===!0?n.unshift(p):r.unshift(p)}function u(d,h){r.length>1&&r.sort(d||C0),i.length>1&&i.sort(h||Iu),n.length>1&&n.sort(h||Iu)}function l(){for(let d=t,h=e.length;d<h;d++){let m=e[d];if(m.id===null)break;m.id=null,m.object=null,m.geometry=null,m.material=null,m.group=null}}return{opaque:r,transmissive:i,transparent:n,init:a,push:s,unshift:c,finish:l,sort:u}}function I0(){let e=new WeakMap;function t(i,n){let a=e.get(i),o;return a===void 0?(o=new Nu,e.set(i,[o])):n>=a.length?(o=new Nu,a.push(o)):o=a[n],o}function r(){e=new WeakMap}return{get:t,dispose:r}}function N0(){let e={};return{get:function(t){if(e[t.id]!==void 0)return e[t.id];let r;switch(t.type){case"DirectionalLight":r={direction:new F,color:new qe};break;case"SpotLight":r={position:new F,direction:new F,color:new qe,distance:0,coneCos:0,penumbraCos:0,decay:0};break;case"PointLight":r={position:new F,color:new qe,distance:0,decay:0};break;case"HemisphereLight":r={direction:new F,skyColor:new qe,groundColor:new qe};break;case"RectAreaLight":r={color:new qe,position:new F,halfWidth:new F,halfHeight:new F};break}return e[t.id]=r,r}}}function P0(){let e={};return{get:function(t){if(e[t.id]!==void 0)return e[t.id];let r;switch(t.type){case"DirectionalLight":r={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new Ye};break;case"SpotLight":r={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new Ye};break;case"PointLight":r={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new Ye,shadowCameraNear:1,shadowCameraFar:1e3};break}return e[t.id]=r,r}}}var O0=0;function L0(e,t){return(t.castShadow?2:0)-(e.castShadow?2:0)+(t.map?1:0)-(e.map?1:0)}function U0(e){let t=new N0,r=P0(),i={version:0,hash:{directionalLength:-1,pointLength:-1,spotLength:-1,rectAreaLength:-1,hemiLength:-1,numDirectionalShadows:-1,numPointShadows:-1,numSpotShadows:-1,numSpotMaps:-1,numLightProbes:-1},ambient:[0,0,0],probe:[],directional:[],directionalShadow:[],directionalShadowMap:[],directionalShadowMatrix:[],spot:[],spotLightMap:[],spotShadow:[],spotShadowMap:[],spotLightMatrix:[],rectArea:[],rectAreaLTC1:null,rectAreaLTC2:null,point:[],pointShadow:[],pointShadowMap:[],pointShadowMatrix:[],hemi:[],numSpotLightShadowsWithMaps:0,numLightProbes:0};for(let u=0;u<9;u++)i.probe.push(new F);let n=new F,a=new pt,o=new pt;function s(u){let l=0,d=0,h=0;for(let S=0;S<9;S++)i.probe[S].set(0,0,0);let m=0,g=0,_=0,f=0,p=0,R=0,y=0,A=0,O=0,I=0,C=0;u.sort(L0);for(let S=0,x=u.length;S<x;S++){let M=u[S],k=M.color,H=M.intensity,V=M.distance,Z=M.shadow&&M.shadow.map?M.shadow.map.texture:null;if(M.isAmbientLight)l+=k.r*H,d+=k.g*H,h+=k.b*H;else if(M.isLightProbe){for(let G=0;G<9;G++)i.probe[G].addScaledVector(M.sh.coefficients[G],H);C++}else if(M.isDirectionalLight){let G=t.get(M);if(G.color.copy(M.color).multiplyScalar(M.intensity),M.castShadow){let ee=M.shadow,W=r.get(M);W.shadowIntensity=ee.intensity,W.shadowBias=ee.bias,W.shadowNormalBias=ee.normalBias,W.shadowRadius=ee.radius,W.shadowMapSize=ee.mapSize,i.directionalShadow[m]=W,i.directionalShadowMap[m]=Z,i.directionalShadowMatrix[m]=M.shadow.matrix,R++}i.directional[m]=G,m++}else if(M.isSpotLight){let G=t.get(M);G.position.setFromMatrixPosition(M.matrixWorld),G.color.copy(k).multiplyScalar(H),G.distance=V,G.coneCos=Math.cos(M.angle),G.penumbraCos=Math.cos(M.angle*(1-M.penumbra)),G.decay=M.decay,i.spot[_]=G;let ee=M.shadow;if(M.map&&(i.spotLightMap[O]=M.map,O++,ee.updateMatrices(M),M.castShadow&&I++),i.spotLightMatrix[_]=ee.matrix,M.castShadow){let W=r.get(M);W.shadowIntensity=ee.intensity,W.shadowBias=ee.bias,W.shadowNormalBias=ee.normalBias,W.shadowRadius=ee.radius,W.shadowMapSize=ee.mapSize,i.spotShadow[_]=W,i.spotShadowMap[_]=Z,A++}_++}else if(M.isRectAreaLight){let G=t.get(M);G.color.copy(k).multiplyScalar(H),G.halfWidth.set(M.width*.5,0,0),G.halfHeight.set(0,M.height*.5,0),i.rectArea[f]=G,f++}else if(M.isPointLight){let G=t.get(M);if(G.color.copy(M.color).multiplyScalar(M.intensity),G.distance=M.distance,G.decay=M.decay,M.castShadow){let ee=M.shadow,W=r.get(M);W.shadowIntensity=ee.intensity,W.shadowBias=ee.bias,W.shadowNormalBias=ee.normalBias,W.shadowRadius=ee.radius,W.shadowMapSize=ee.mapSize,W.shadowCameraNear=ee.camera.near,W.shadowCameraFar=ee.camera.far,i.pointShadow[g]=W,i.pointShadowMap[g]=Z,i.pointShadowMatrix[g]=M.shadow.matrix,y++}i.point[g]=G,g++}else if(M.isHemisphereLight){let G=t.get(M);G.skyColor.copy(M.color).multiplyScalar(H),G.groundColor.copy(M.groundColor).multiplyScalar(H),i.hemi[p]=G,p++}}f>0&&(e.has("OES_texture_float_linear")===!0?(i.rectAreaLTC1=ue.LTC_FLOAT_1,i.rectAreaLTC2=ue.LTC_FLOAT_2):(i.rectAreaLTC1=ue.LTC_HALF_1,i.rectAreaLTC2=ue.LTC_HALF_2)),i.ambient[0]=l,i.ambient[1]=d,i.ambient[2]=h;let U=i.hash;(U.directionalLength!==m||U.pointLength!==g||U.spotLength!==_||U.rectAreaLength!==f||U.hemiLength!==p||U.numDirectionalShadows!==R||U.numPointShadows!==y||U.numSpotShadows!==A||U.numSpotMaps!==O||U.numLightProbes!==C)&&(i.directional.length=m,i.spot.length=_,i.rectArea.length=f,i.point.length=g,i.hemi.length=p,i.directionalShadow.length=R,i.directionalShadowMap.length=R,i.pointShadow.length=y,i.pointShadowMap.length=y,i.spotShadow.length=A,i.spotShadowMap.length=A,i.directionalShadowMatrix.length=R,i.pointShadowMatrix.length=y,i.spotLightMatrix.length=A+O-I,i.spotLightMap.length=O,i.numSpotLightShadowsWithMaps=I,i.numLightProbes=C,U.directionalLength=m,U.pointLength=g,U.spotLength=_,U.rectAreaLength=f,U.hemiLength=p,U.numDirectionalShadows=R,U.numPointShadows=y,U.numSpotShadows=A,U.numSpotMaps=O,U.numLightProbes=C,i.version=O0++)}function c(u,l){let d=0,h=0,m=0,g=0,_=0,f=l.matrixWorldInverse;for(let p=0,R=u.length;p<R;p++){let y=u[p];if(y.isDirectionalLight){let A=i.directional[d];A.direction.setFromMatrixPosition(y.matrixWorld),n.setFromMatrixPosition(y.target.matrixWorld),A.direction.sub(n),A.direction.transformDirection(f),d++}else if(y.isSpotLight){let A=i.spot[m];A.position.setFromMatrixPosition(y.matrixWorld),A.position.applyMatrix4(f),A.direction.setFromMatrixPosition(y.matrixWorld),n.setFromMatrixPosition(y.target.matrixWorld),A.direction.sub(n),A.direction.transformDirection(f),m++}else if(y.isRectAreaLight){let A=i.rectArea[g];A.position.setFromMatrixPosition(y.matrixWorld),A.position.applyMatrix4(f),o.identity(),a.copy(y.matrixWorld),a.premultiply(f),o.extractRotation(a),A.halfWidth.set(y.width*.5,0,0),A.halfHeight.set(0,y.height*.5,0),A.halfWidth.applyMatrix4(o),A.halfHeight.applyMatrix4(o),g++}else if(y.isPointLight){let A=i.point[h];A.position.setFromMatrixPosition(y.matrixWorld),A.position.applyMatrix4(f),h++}else if(y.isHemisphereLight){let A=i.hemi[_];A.direction.setFromMatrixPosition(y.matrixWorld),A.direction.transformDirection(f),_++}}}return{setup:s,setupView:c,state:i}}function Pu(e){let t=new U0(e),r=[],i=[];function n(l){u.camera=l,r.length=0,i.length=0}function a(l){r.push(l)}function o(l){i.push(l)}function s(){t.setup(r)}function c(l){t.setupView(r,l)}let u={lightsArray:r,shadowsArray:i,camera:null,lights:t,transmissionRenderTarget:{}};return{init:n,state:u,setupLights:s,setupLightsView:c,pushLight:a,pushShadow:o}}function D0(e){let t=new WeakMap;function r(n,a=0){let o=t.get(n),s;return o===void 0?(s=new Pu(e),t.set(n,[s])):a>=o.length?(s=new Pu(e),o.push(s)):s=o[a],s}function i(){t=new WeakMap}return{get:r,dispose:i}}var F0=`void main() {
	gl_Position = vec4( position, 1.0 );
}`,k0=`uniform sampler2D shadow_pass;
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
}`;function B0(e,t,r){let i=new il,n=new Ye,a=new Ye,o=new lt,s=new Wf({depthPacking:nf}),c=new jf,u={},l=r.maxTextureSize,d={[Vr]:Rt,[Rt]:Vr,[Tr]:Tr},h=new Hr({defines:{VSM_SAMPLES:8},uniforms:{shadow_pass:{value:null},resolution:{value:new Ye},radius:{value:4}},vertexShader:F0,fragmentShader:k0}),m=h.clone();m.defines.HORIZONTAL_PASS=1;let g=new bn;g.setAttribute("position",new sr(new Float32Array([-1,-1,.5,3,-1,.5,-1,3,.5]),3));let _=new Yt(g,h),f=this;this.enabled=!1,this.autoUpdate=!0,this.needsUpdate=!1,this.type=Lu;let p=this.type;this.render=function(I,C,U){if(f.enabled===!1||f.autoUpdate===!1&&f.needsUpdate===!1||I.length===0)return;let S=e.getRenderTarget(),x=e.getActiveCubeFace(),M=e.getActiveMipmapLevel(),k=e.state;k.setBlending(kr),k.buffers.depth.getReversed()===!0?k.buffers.color.setClear(0,0,0,0):k.buffers.color.setClear(1,1,1,1),k.buffers.depth.setTest(!0),k.setScissorTest(!1);let H=p!==Er&&this.type===Er,V=p===Er&&this.type!==Er;for(let Z=0,G=I.length;Z<G;Z++){let ee=I[Z],W=ee.shadow;if(W===void 0){console.warn("THREE.WebGLShadowMap:",ee,"has no shadow.");continue}if(W.autoUpdate===!1&&W.needsUpdate===!1)continue;n.copy(W.mapSize);let ie=W.getFrameExtents();if(n.multiply(ie),a.copy(W.mapSize),(n.x>l||n.y>l)&&(n.x>l&&(a.x=Math.floor(l/ie.x),n.x=a.x*ie.x,W.mapSize.x=a.x),n.y>l&&(a.y=Math.floor(l/ie.y),n.y=a.y*ie.y,W.mapSize.y=a.y)),W.map===null||H===!0||V===!0){let Pe=this.type!==Er?{minFilter:Kt,magFilter:Kt}:{};W.map!==null&&W.map.dispose(),W.map=new li(n.x,n.y,Pe),W.map.texture.name=ee.name+".shadowMap",W.camera.updateProjectionMatrix()}e.setRenderTarget(W.map),e.clear();let ce=W.getViewportCount();for(let Pe=0;Pe<ce;Pe++){let Fe=W.getViewport(Pe);o.set(a.x*Fe.x,a.y*Fe.y,a.x*Fe.z,a.y*Fe.w),k.viewport(o),W.updateMatrices(ee,Pe),i=W.getFrustum(),A(C,U,W.camera,ee,this.type)}W.isPointLightShadow!==!0&&this.type===Er&&R(W,U),W.needsUpdate=!1}p=this.type,f.needsUpdate=!1,e.setRenderTarget(S,x,M)};function R(I,C){let U=t.update(_);h.defines.VSM_SAMPLES!==I.blurSamples&&(h.defines.VSM_SAMPLES=I.blurSamples,m.defines.VSM_SAMPLES=I.blurSamples,h.needsUpdate=!0,m.needsUpdate=!0),I.mapPass===null&&(I.mapPass=new li(n.x,n.y)),h.uniforms.shadow_pass.value=I.map.texture,h.uniforms.resolution.value=I.mapSize,h.uniforms.radius.value=I.radius,e.setRenderTarget(I.mapPass),e.clear(),e.renderBufferDirect(C,null,U,h,_,null),m.uniforms.shadow_pass.value=I.mapPass.texture,m.uniforms.resolution.value=I.mapSize,m.uniforms.radius.value=I.radius,e.setRenderTarget(I.map),e.clear(),e.renderBufferDirect(C,null,U,m,_,null)}function y(I,C,U,S){let x=null,M=U.isPointLight===!0?I.customDistanceMaterial:I.customDepthMaterial;if(M!==void 0)x=M;else if(x=U.isPointLight===!0?c:s,e.localClippingEnabled&&C.clipShadows===!0&&Array.isArray(C.clippingPlanes)&&C.clippingPlanes.length!==0||C.displacementMap&&C.displacementScale!==0||C.alphaMap&&C.alphaTest>0||C.map&&C.alphaTest>0||C.alphaToCoverage===!0){let k=x.uuid,H=C.uuid,V=u[k];V===void 0&&(V={},u[k]=V);let Z=V[H];Z===void 0&&(Z=x.clone(),V[H]=Z,C.addEventListener("dispose",O)),x=Z}if(x.visible=C.visible,x.wireframe=C.wireframe,S===Er?x.side=C.shadowSide!==null?C.shadowSide:C.side:x.side=C.shadowSide!==null?C.shadowSide:d[C.side],x.alphaMap=C.alphaMap,x.alphaTest=C.alphaToCoverage===!0?.5:C.alphaTest,x.map=C.map,x.clipShadows=C.clipShadows,x.clippingPlanes=C.clippingPlanes,x.clipIntersection=C.clipIntersection,x.displacementMap=C.displacementMap,x.displacementScale=C.displacementScale,x.displacementBias=C.displacementBias,x.wireframeLinewidth=C.wireframeLinewidth,x.linewidth=C.linewidth,U.isPointLight===!0&&x.isMeshDistanceMaterial===!0){let k=e.properties.get(x);k.light=U}return x}function A(I,C,U,S,x){if(I.visible===!1)return;if(I.layers.test(C.layers)&&(I.isMesh||I.isLine||I.isPoints)&&(I.castShadow||I.receiveShadow&&x===Er)&&(!I.frustumCulled||i.intersectsObject(I))){I.modelViewMatrix.multiplyMatrices(U.matrixWorldInverse,I.matrixWorld);let k=t.update(I),H=I.material;if(Array.isArray(H)){let V=k.groups;for(let Z=0,G=V.length;Z<G;Z++){let ee=V[Z],W=H[ee.materialIndex];if(W&&W.visible){let ie=y(I,W,S,x);I.onBeforeShadow(e,I,C,U,k,ie,ee),e.renderBufferDirect(U,null,k,ie,I,ee),I.onAfterShadow(e,I,C,U,k,ie,ee)}}}else if(H.visible){let V=y(I,H,S,x);I.onBeforeShadow(e,I,C,U,k,V,null),e.renderBufferDirect(U,null,k,V,I,null),I.onAfterShadow(e,I,C,U,k,V,null)}}let M=I.children;for(let k=0,H=M.length;k<H;k++)A(M[k],C,U,S,x)}function O(I){I.target.removeEventListener("dispose",O);for(let C in u){let U=u[C],S=I.target.uuid;S in U&&(U[S].dispose(),delete U[S])}}}var V0={[os]:ss,[ls]:ds,[cs]:hs,[Vi]:us,[ss]:os,[ds]:ls,[hs]:cs,[us]:Vi};function z0(e,t){function r(){let w=!1,he=new lt,le=null,ye=new lt(0,0,0,0);return{setMask:function(te){le!==te&&!w&&(e.colorMask(te,te,te,te),le=te)},setLocked:function(te){w=te},setClear:function(te,K,xe,Ie,ot){ot===!0&&(te*=Ie,K*=Ie,xe*=Ie),he.set(te,K,xe,Ie),ye.equals(he)===!1&&(e.clearColor(te,K,xe,Ie),ye.copy(he))},reset:function(){w=!1,le=null,ye.set(-1,0,0,0)}}}function i(){let w=!1,he=!1,le=null,ye=null,te=null;return{setReversed:function(K){if(he!==K){let xe=t.get("EXT_clip_control");K?xe.clipControlEXT(xe.LOWER_LEFT_EXT,xe.ZERO_TO_ONE_EXT):xe.clipControlEXT(xe.LOWER_LEFT_EXT,xe.NEGATIVE_ONE_TO_ONE_EXT),he=K;let Ie=te;te=null,this.setClear(Ie)}},getReversed:function(){return he},setTest:function(K){K?ne(e.DEPTH_TEST):z(e.DEPTH_TEST)},setMask:function(K){le!==K&&!w&&(e.depthMask(K),le=K)},setFunc:function(K){if(he&&(K=V0[K]),ye!==K){switch(K){case os:e.depthFunc(e.NEVER);break;case ss:e.depthFunc(e.ALWAYS);break;case ls:e.depthFunc(e.LESS);break;case Vi:e.depthFunc(e.LEQUAL);break;case cs:e.depthFunc(e.EQUAL);break;case us:e.depthFunc(e.GEQUAL);break;case ds:e.depthFunc(e.GREATER);break;case hs:e.depthFunc(e.NOTEQUAL);break;default:e.depthFunc(e.LEQUAL)}ye=K}},setLocked:function(K){w=K},setClear:function(K){te!==K&&(he&&(K=1-K),e.clearDepth(K),te=K)},reset:function(){w=!1,le=null,ye=null,te=null,he=!1}}}function n(){let w=!1,he=null,le=null,ye=null,te=null,K=null,xe=null,Ie=null,ot=null;return{setTest:function(Ke){w||(Ke?ne(e.STENCIL_TEST):z(e.STENCIL_TEST))},setMask:function(Ke){he!==Ke&&!w&&(e.stencilMask(Ke),he=Ke)},setFunc:function(Ke,$t,Qt){(le!==Ke||ye!==$t||te!==Qt)&&(e.stencilFunc(Ke,$t,Qt),le=Ke,ye=$t,te=Qt)},setOp:function(Ke,$t,Qt){(K!==Ke||xe!==$t||Ie!==Qt)&&(e.stencilOp(Ke,$t,Qt),K=Ke,xe=$t,Ie=Qt)},setLocked:function(Ke){w=Ke},setClear:function(Ke){ot!==Ke&&(e.clearStencil(Ke),ot=Ke)},reset:function(){w=!1,he=null,le=null,ye=null,te=null,K=null,xe=null,Ie=null,ot=null}}}let a=new r,o=new i,s=new n,c=new WeakMap,u=new WeakMap,l={},d={},h=new WeakMap,m=[],g=null,_=!1,f=null,p=null,R=null,y=null,A=null,O=null,I=null,C=new qe(0,0,0),U=0,S=!1,x=null,M=null,k=null,H=null,V=null,Z=e.getParameter(e.MAX_COMBINED_TEXTURE_IMAGE_UNITS),G=!1,ee=0,W=e.getParameter(e.VERSION);W.indexOf("WebGL")!==-1?(ee=parseFloat(/^WebGL (\d)/.exec(W)[1]),G=ee>=1):W.indexOf("OpenGL ES")!==-1&&(ee=parseFloat(/^OpenGL ES (\d)/.exec(W)[1]),G=ee>=2);let ie=null,ce={},Pe=e.getParameter(e.SCISSOR_BOX),Fe=e.getParameter(e.VIEWPORT),$e=new lt().fromArray(Pe),We=new lt().fromArray(Fe);function j(w,he,le,ye){let te=new Uint8Array(4),K=e.createTexture();e.bindTexture(w,K),e.texParameteri(w,e.TEXTURE_MIN_FILTER,e.NEAREST),e.texParameteri(w,e.TEXTURE_MAG_FILTER,e.NEAREST);for(let xe=0;xe<le;xe++)w===e.TEXTURE_3D||w===e.TEXTURE_2D_ARRAY?e.texImage3D(he,0,e.RGBA,1,1,ye,0,e.RGBA,e.UNSIGNED_BYTE,te):e.texImage2D(he+xe,0,e.RGBA,1,1,0,e.RGBA,e.UNSIGNED_BYTE,te);return K}let oe={};oe[e.TEXTURE_2D]=j(e.TEXTURE_2D,e.TEXTURE_2D,1),oe[e.TEXTURE_CUBE_MAP]=j(e.TEXTURE_CUBE_MAP,e.TEXTURE_CUBE_MAP_POSITIVE_X,6),oe[e.TEXTURE_2D_ARRAY]=j(e.TEXTURE_2D_ARRAY,e.TEXTURE_2D_ARRAY,1,1),oe[e.TEXTURE_3D]=j(e.TEXTURE_3D,e.TEXTURE_3D,1,1),a.setClear(0,0,0,1),o.setClear(1),s.setClear(0),ne(e.DEPTH_TEST),o.setFunc(Vi),fe(!1),Ze(Oc),ne(e.CULL_FACE),Ee(kr);function ne(w){l[w]!==!0&&(e.enable(w),l[w]=!0)}function z(w){l[w]!==!1&&(e.disable(w),l[w]=!1)}function ae(w,he){return d[w]!==he?(e.bindFramebuffer(w,he),d[w]=he,w===e.DRAW_FRAMEBUFFER&&(d[e.FRAMEBUFFER]=he),w===e.FRAMEBUFFER&&(d[e.DRAW_FRAMEBUFFER]=he),!0):!1}function $(w,he){let le=m,ye=!1;if(w){le=h.get(he),le===void 0&&(le=[],h.set(he,le));let te=w.textures;if(le.length!==te.length||le[0]!==e.COLOR_ATTACHMENT0){for(let K=0,xe=te.length;K<xe;K++)le[K]=e.COLOR_ATTACHMENT0+K;le.length=te.length,ye=!0}}else le[0]!==e.BACK&&(le[0]=e.BACK,ye=!0);ye&&e.drawBuffers(le)}function ge(w){return g!==w?(e.useProgram(w),g=w,!0):!1}let T={[ri]:e.FUNC_ADD,[Cp]:e.FUNC_SUBTRACT,[Ip]:e.FUNC_REVERSE_SUBTRACT};T[Np]=e.MIN,T[Pp]=e.MAX;let Se={[Op]:e.ZERO,[Lp]:e.ONE,[Up]:e.SRC_COLOR,[ns]:e.SRC_ALPHA,[zp]:e.SRC_ALPHA_SATURATE,[Bp]:e.DST_COLOR,[Fp]:e.DST_ALPHA,[Dp]:e.ONE_MINUS_SRC_COLOR,[as]:e.ONE_MINUS_SRC_ALPHA,[Vp]:e.ONE_MINUS_DST_COLOR,[kp]:e.ONE_MINUS_DST_ALPHA,[Hp]:e.CONSTANT_COLOR,[Gp]:e.ONE_MINUS_CONSTANT_COLOR,[Wp]:e.CONSTANT_ALPHA,[jp]:e.ONE_MINUS_CONSTANT_ALPHA};function Ee(w,he,le,ye,te,K,xe,Ie,ot,Ke){if(w===kr){_===!0&&(z(e.BLEND),_=!1);return}if(_===!1&&(ne(e.BLEND),_=!0),w!==Rp){if(w!==f||Ke!==S){if((p!==ri||A!==ri)&&(e.blendEquation(e.FUNC_ADD),p=ri,A=ri),Ke)switch(w){case ki:e.blendFuncSeparate(e.ONE,e.ONE_MINUS_SRC_ALPHA,e.ONE,e.ONE_MINUS_SRC_ALPHA);break;case Lc:e.blendFunc(e.ONE,e.ONE);break;case Uc:e.blendFuncSeparate(e.ZERO,e.ONE_MINUS_SRC_COLOR,e.ZERO,e.ONE);break;case Dc:e.blendFuncSeparate(e.DST_COLOR,e.ONE_MINUS_SRC_ALPHA,e.ZERO,e.ONE);break;default:console.error("THREE.WebGLState: Invalid blending: ",w);break}else switch(w){case ki:e.blendFuncSeparate(e.SRC_ALPHA,e.ONE_MINUS_SRC_ALPHA,e.ONE,e.ONE_MINUS_SRC_ALPHA);break;case Lc:e.blendFuncSeparate(e.SRC_ALPHA,e.ONE,e.ONE,e.ONE);break;case Uc:console.error("THREE.WebGLState: SubtractiveBlending requires material.premultipliedAlpha = true");break;case Dc:console.error("THREE.WebGLState: MultiplyBlending requires material.premultipliedAlpha = true");break;default:console.error("THREE.WebGLState: Invalid blending: ",w);break}R=null,y=null,O=null,I=null,C.set(0,0,0),U=0,f=w,S=Ke}return}te=te||he,K=K||le,xe=xe||ye,(he!==p||te!==A)&&(e.blendEquationSeparate(T[he],T[te]),p=he,A=te),(le!==R||ye!==y||K!==O||xe!==I)&&(e.blendFuncSeparate(Se[le],Se[ye],Se[K],Se[xe]),R=le,y=ye,O=K,I=xe),(Ie.equals(C)===!1||ot!==U)&&(e.blendColor(Ie.r,Ie.g,Ie.b,ot),C.copy(Ie),U=ot),f=w,S=!1}function Ve(w,he){w.side===Tr?z(e.CULL_FACE):ne(e.CULL_FACE);let le=w.side===Rt;he&&(le=!le),fe(le),w.blending===ki&&w.transparent===!1?Ee(kr):Ee(w.blending,w.blendEquation,w.blendSrc,w.blendDst,w.blendEquationAlpha,w.blendSrcAlpha,w.blendDstAlpha,w.blendColor,w.blendAlpha,w.premultipliedAlpha),o.setFunc(w.depthFunc),o.setTest(w.depthTest),o.setMask(w.depthWrite),a.setMask(w.colorWrite);let ye=w.stencilWrite;s.setTest(ye),ye&&(s.setMask(w.stencilWriteMask),s.setFunc(w.stencilFunc,w.stencilRef,w.stencilFuncMask),s.setOp(w.stencilFail,w.stencilZFail,w.stencilZPass)),Ce(w.polygonOffset,w.polygonOffsetFactor,w.polygonOffsetUnits),w.alphaToCoverage===!0?ne(e.SAMPLE_ALPHA_TO_COVERAGE):z(e.SAMPLE_ALPHA_TO_COVERAGE)}function fe(w){x!==w&&(w?e.frontFace(e.CW):e.frontFace(e.CCW),x=w)}function Ze(w){w!==Mp?(ne(e.CULL_FACE),w!==M&&(w===Oc?e.cullFace(e.BACK):w===Ap?e.cullFace(e.FRONT):e.cullFace(e.FRONT_AND_BACK))):z(e.CULL_FACE),M=w}function Re(w){w!==k&&(G&&e.lineWidth(w),k=w)}function Ce(w,he,le){w?(ne(e.POLYGON_OFFSET_FILL),(H!==he||V!==le)&&(e.polygonOffset(he,le),H=he,V=le)):z(e.POLYGON_OFFSET_FILL)}function mt(w){w?ne(e.SCISSOR_TEST):z(e.SCISSOR_TEST)}function dt(w){w===void 0&&(w=e.TEXTURE0+Z-1),ie!==w&&(e.activeTexture(w),ie=w)}function at(w,he,le){le===void 0&&(ie===null?le=e.TEXTURE0+Z-1:le=ie);let ye=ce[le];ye===void 0&&(ye={type:void 0,texture:void 0},ce[le]=ye),(ye.type!==w||ye.texture!==he)&&(ie!==le&&(e.activeTexture(le),ie=le),e.bindTexture(w,he||oe[w]),ye.type=w,ye.texture=he)}function E(){let w=ce[ie];w!==void 0&&w.type!==void 0&&(e.bindTexture(w.type,null),w.type=void 0,w.texture=void 0)}function v(){try{e.compressedTexImage2D(...arguments)}catch(w){console.error("THREE.WebGLState:",w)}}function L(){try{e.compressedTexImage3D(...arguments)}catch(w){console.error("THREE.WebGLState:",w)}}function Y(){try{e.texSubImage2D(...arguments)}catch(w){console.error("THREE.WebGLState:",w)}}function J(){try{e.texSubImage3D(...arguments)}catch(w){console.error("THREE.WebGLState:",w)}}function X(){try{e.compressedTexSubImage2D(...arguments)}catch(w){console.error("THREE.WebGLState:",w)}}function be(){try{e.compressedTexSubImage3D(...arguments)}catch(w){console.error("THREE.WebGLState:",w)}}function se(){try{e.texStorage2D(...arguments)}catch(w){console.error("THREE.WebGLState:",w)}}function Te(){try{e.texStorage3D(...arguments)}catch(w){console.error("THREE.WebGLState:",w)}}function Ae(){try{e.texImage2D(...arguments)}catch(w){console.error("THREE.WebGLState:",w)}}function re(){try{e.texImage3D(...arguments)}catch(w){console.error("THREE.WebGLState:",w)}}function de(w){$e.equals(w)===!1&&(e.scissor(w.x,w.y,w.z,w.w),$e.copy(w))}function Ne(w){We.equals(w)===!1&&(e.viewport(w.x,w.y,w.z,w.w),We.copy(w))}function we(w,he){let le=u.get(he);le===void 0&&(le=new WeakMap,u.set(he,le));let ye=le.get(w);ye===void 0&&(ye=e.getUniformBlockIndex(he,w.name),le.set(w,ye))}function pe(w,he){let le=u.get(he).get(w);c.get(he)!==le&&(e.uniformBlockBinding(he,le,w.__bindingPointIndex),c.set(he,le))}function ze(){e.disable(e.BLEND),e.disable(e.CULL_FACE),e.disable(e.DEPTH_TEST),e.disable(e.POLYGON_OFFSET_FILL),e.disable(e.SCISSOR_TEST),e.disable(e.STENCIL_TEST),e.disable(e.SAMPLE_ALPHA_TO_COVERAGE),e.blendEquation(e.FUNC_ADD),e.blendFunc(e.ONE,e.ZERO),e.blendFuncSeparate(e.ONE,e.ZERO,e.ONE,e.ZERO),e.blendColor(0,0,0,0),e.colorMask(!0,!0,!0,!0),e.clearColor(0,0,0,0),e.depthMask(!0),e.depthFunc(e.LESS),o.setReversed(!1),e.clearDepth(1),e.stencilMask(4294967295),e.stencilFunc(e.ALWAYS,0,4294967295),e.stencilOp(e.KEEP,e.KEEP,e.KEEP),e.clearStencil(0),e.cullFace(e.BACK),e.frontFace(e.CCW),e.polygonOffset(0,0),e.activeTexture(e.TEXTURE0),e.bindFramebuffer(e.FRAMEBUFFER,null),e.bindFramebuffer(e.DRAW_FRAMEBUFFER,null),e.bindFramebuffer(e.READ_FRAMEBUFFER,null),e.useProgram(null),e.lineWidth(1),e.scissor(0,0,e.canvas.width,e.canvas.height),e.viewport(0,0,e.canvas.width,e.canvas.height),l={},ie=null,ce={},d={},h=new WeakMap,m=[],g=null,_=!1,f=null,p=null,R=null,y=null,A=null,O=null,I=null,C=new qe(0,0,0),U=0,S=!1,x=null,M=null,k=null,H=null,V=null,$e.set(0,0,e.canvas.width,e.canvas.height),We.set(0,0,e.canvas.width,e.canvas.height),a.reset(),o.reset(),s.reset()}return{buffers:{color:a,depth:o,stencil:s},enable:ne,disable:z,bindFramebuffer:ae,drawBuffers:$,useProgram:ge,setBlending:Ee,setMaterial:Ve,setFlipSided:fe,setCullFace:Ze,setLineWidth:Re,setPolygonOffset:Ce,setScissorTest:mt,activeTexture:dt,bindTexture:at,unbindTexture:E,compressedTexImage2D:v,compressedTexImage3D:L,texImage2D:Ae,texImage3D:re,updateUBOMapping:we,uniformBlockBinding:pe,texStorage2D:se,texStorage3D:Te,texSubImage2D:Y,texSubImage3D:J,compressedTexSubImage2D:X,compressedTexSubImage3D:be,scissor:de,viewport:Ne,reset:ze}}function H0(e,t,r,i,n,a,o){let s=t.has("WEBGL_multisampled_render_to_texture")?t.get("WEBGL_multisampled_render_to_texture"):null,c=typeof navigator>"u"?!1:/OculusBrowser/g.test(navigator.userAgent),u=new Ye,l=new WeakMap,d,h=new WeakMap,m=!1;try{m=typeof OffscreenCanvas<"u"&&new OffscreenCanvas(1,1).getContext("2d")!==null}catch{}function g(E,v){return m?new OffscreenCanvas(E,v):Ia("canvas")}function _(E,v,L){let Y=1,J=at(E);if((J.width>L||J.height>L)&&(Y=L/Math.max(J.width,J.height)),Y<1)if(typeof HTMLImageElement<"u"&&E instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&E instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&E instanceof ImageBitmap||typeof VideoFrame<"u"&&E instanceof VideoFrame){let X=Math.floor(Y*J.width),be=Math.floor(Y*J.height);d===void 0&&(d=g(X,be));let se=v?g(X,be):d;return se.width=X,se.height=be,se.getContext("2d").drawImage(E,0,0,X,be),console.warn("THREE.WebGLRenderer: Texture has been resized from ("+J.width+"x"+J.height+") to ("+X+"x"+be+")."),se}else return"data"in E&&console.warn("THREE.WebGLRenderer: Image in DataTexture is too big ("+J.width+"x"+J.height+")."),E;return E}function f(E){return E.generateMipmaps}function p(E){e.generateMipmap(E)}function R(E){return E.isWebGLCubeRenderTarget?e.TEXTURE_CUBE_MAP:E.isWebGL3DRenderTarget?e.TEXTURE_3D:E.isWebGLArrayRenderTarget||E.isCompressedArrayTexture?e.TEXTURE_2D_ARRAY:e.TEXTURE_2D}function y(E,v,L,Y,J=!1){if(E!==null){if(e[E]!==void 0)return e[E];console.warn("THREE.WebGLRenderer: Attempt to use non-existing WebGL internal format '"+E+"'")}let X=v;if(v===e.RED&&(L===e.FLOAT&&(X=e.R32F),L===e.HALF_FLOAT&&(X=e.R16F),L===e.UNSIGNED_BYTE&&(X=e.R8)),v===e.RED_INTEGER&&(L===e.UNSIGNED_BYTE&&(X=e.R8UI),L===e.UNSIGNED_SHORT&&(X=e.R16UI),L===e.UNSIGNED_INT&&(X=e.R32UI),L===e.BYTE&&(X=e.R8I),L===e.SHORT&&(X=e.R16I),L===e.INT&&(X=e.R32I)),v===e.RG&&(L===e.FLOAT&&(X=e.RG32F),L===e.HALF_FLOAT&&(X=e.RG16F),L===e.UNSIGNED_BYTE&&(X=e.RG8)),v===e.RG_INTEGER&&(L===e.UNSIGNED_BYTE&&(X=e.RG8UI),L===e.UNSIGNED_SHORT&&(X=e.RG16UI),L===e.UNSIGNED_INT&&(X=e.RG32UI),L===e.BYTE&&(X=e.RG8I),L===e.SHORT&&(X=e.RG16I),L===e.INT&&(X=e.RG32I)),v===e.RGB_INTEGER&&(L===e.UNSIGNED_BYTE&&(X=e.RGB8UI),L===e.UNSIGNED_SHORT&&(X=e.RGB16UI),L===e.UNSIGNED_INT&&(X=e.RGB32UI),L===e.BYTE&&(X=e.RGB8I),L===e.SHORT&&(X=e.RGB16I),L===e.INT&&(X=e.RGB32I)),v===e.RGBA_INTEGER&&(L===e.UNSIGNED_BYTE&&(X=e.RGBA8UI),L===e.UNSIGNED_SHORT&&(X=e.RGBA16UI),L===e.UNSIGNED_INT&&(X=e.RGBA32UI),L===e.BYTE&&(X=e.RGBA8I),L===e.SHORT&&(X=e.RGBA16I),L===e.INT&&(X=e.RGBA32I)),v===e.RGB&&(L===e.UNSIGNED_INT_5_9_9_9_REV&&(X=e.RGB9_E5),L===e.UNSIGNED_INT_10F_11F_11F_REV&&(X=e.R11F_G11F_B10F)),v===e.RGBA){let be=J?Ra:Xe.getTransfer(Y);L===e.FLOAT&&(X=e.RGBA32F),L===e.HALF_FLOAT&&(X=e.RGBA16F),L===e.UNSIGNED_BYTE&&(X=be===Je?e.SRGB8_ALPHA8:e.RGBA8),L===e.UNSIGNED_SHORT_4_4_4_4&&(X=e.RGBA4),L===e.UNSIGNED_SHORT_5_5_5_1&&(X=e.RGB5_A1)}return(X===e.R16F||X===e.R32F||X===e.RG16F||X===e.RG32F||X===e.RGBA16F||X===e.RGBA32F)&&t.get("EXT_color_buffer_float"),X}function A(E,v){let L;return E?v===null||v===si||v===dn?L=e.DEPTH24_STENCIL8:v===Mr?L=e.DEPTH32F_STENCIL8:v===un&&(L=e.DEPTH24_STENCIL8,console.warn("DepthTexture: 16 bit depth attachment is not supported with stencil. Using 24-bit attachment.")):v===null||v===si||v===dn?L=e.DEPTH_COMPONENT24:v===Mr?L=e.DEPTH_COMPONENT32F:v===un&&(L=e.DEPTH_COMPONENT16),L}function O(E,v){return f(E)===!0||E.isFramebufferTexture&&E.minFilter!==Kt&&E.minFilter!==ar?Math.log2(Math.max(v.width,v.height))+1:E.mipmaps!==void 0&&E.mipmaps.length>0?E.mipmaps.length:E.isCompressedTexture&&Array.isArray(E.image)?v.mipmaps.length:1}function I(E){let v=E.target;v.removeEventListener("dispose",I),U(v),v.isVideoTexture&&l.delete(v)}function C(E){let v=E.target;v.removeEventListener("dispose",C),x(v)}function U(E){let v=i.get(E);if(v.__webglInit===void 0)return;let L=E.source,Y=h.get(L);if(Y){let J=Y[v.__cacheKey];J.usedTimes--,J.usedTimes===0&&S(E),Object.keys(Y).length===0&&h.delete(L)}i.remove(E)}function S(E){let v=i.get(E);e.deleteTexture(v.__webglTexture);let L=E.source,Y=h.get(L);delete Y[v.__cacheKey],o.memory.textures--}function x(E){let v=i.get(E);if(E.depthTexture&&(E.depthTexture.dispose(),i.remove(E.depthTexture)),E.isWebGLCubeRenderTarget)for(let Y=0;Y<6;Y++){if(Array.isArray(v.__webglFramebuffer[Y]))for(let J=0;J<v.__webglFramebuffer[Y].length;J++)e.deleteFramebuffer(v.__webglFramebuffer[Y][J]);else e.deleteFramebuffer(v.__webglFramebuffer[Y]);v.__webglDepthbuffer&&e.deleteRenderbuffer(v.__webglDepthbuffer[Y])}else{if(Array.isArray(v.__webglFramebuffer))for(let Y=0;Y<v.__webglFramebuffer.length;Y++)e.deleteFramebuffer(v.__webglFramebuffer[Y]);else e.deleteFramebuffer(v.__webglFramebuffer);if(v.__webglDepthbuffer&&e.deleteRenderbuffer(v.__webglDepthbuffer),v.__webglMultisampledFramebuffer&&e.deleteFramebuffer(v.__webglMultisampledFramebuffer),v.__webglColorRenderbuffer)for(let Y=0;Y<v.__webglColorRenderbuffer.length;Y++)v.__webglColorRenderbuffer[Y]&&e.deleteRenderbuffer(v.__webglColorRenderbuffer[Y]);v.__webglDepthRenderbuffer&&e.deleteRenderbuffer(v.__webglDepthRenderbuffer)}let L=E.textures;for(let Y=0,J=L.length;Y<J;Y++){let X=i.get(L[Y]);X.__webglTexture&&(e.deleteTexture(X.__webglTexture),o.memory.textures--),i.remove(L[Y])}i.remove(E)}let M=0;function k(){M=0}function H(){let E=M;return E>=n.maxTextures&&console.warn("THREE.WebGLTextures: Trying to use "+E+" texture units while this GPU supports only "+n.maxTextures),M+=1,E}function V(E){let v=[];return v.push(E.wrapS),v.push(E.wrapT),v.push(E.wrapR||0),v.push(E.magFilter),v.push(E.minFilter),v.push(E.anisotropy),v.push(E.internalFormat),v.push(E.format),v.push(E.type),v.push(E.generateMipmaps),v.push(E.premultiplyAlpha),v.push(E.flipY),v.push(E.unpackAlignment),v.push(E.colorSpace),v.join()}function Z(E,v){let L=i.get(E);if(E.isVideoTexture&&mt(E),E.isRenderTargetTexture===!1&&E.isExternalTexture!==!0&&E.version>0&&L.__version!==E.version){let Y=E.image;if(Y===null)console.warn("THREE.WebGLRenderer: Texture marked for update but no image data found.");else if(Y.complete===!1)console.warn("THREE.WebGLRenderer: Texture marked for update but image is incomplete");else{oe(L,E,v);return}}else E.isExternalTexture&&(L.__webglTexture=E.sourceTexture?E.sourceTexture:null);r.bindTexture(e.TEXTURE_2D,L.__webglTexture,e.TEXTURE0+v)}function G(E,v){let L=i.get(E);if(E.isRenderTargetTexture===!1&&E.version>0&&L.__version!==E.version){oe(L,E,v);return}r.bindTexture(e.TEXTURE_2D_ARRAY,L.__webglTexture,e.TEXTURE0+v)}function ee(E,v){let L=i.get(E);if(E.isRenderTargetTexture===!1&&E.version>0&&L.__version!==E.version){oe(L,E,v);return}r.bindTexture(e.TEXTURE_3D,L.__webglTexture,e.TEXTURE0+v)}function W(E,v){let L=i.get(E);if(E.version>0&&L.__version!==E.version){ne(L,E,v);return}r.bindTexture(e.TEXTURE_CUBE_MAP,L.__webglTexture,e.TEXTURE0+v)}let ie={[ms]:e.REPEAT,[ni]:e.CLAMP_TO_EDGE,[gs]:e.MIRRORED_REPEAT},ce={[Kt]:e.NEAREST,[tf]:e.NEAREST_MIPMAP_NEAREST,[Zn]:e.NEAREST_MIPMAP_LINEAR,[ar]:e.LINEAR,[Mo]:e.LINEAR_MIPMAP_NEAREST,[ai]:e.LINEAR_MIPMAP_LINEAR},Pe={[of]:e.NEVER,[hf]:e.ALWAYS,[sf]:e.LESS,[Xu]:e.LEQUAL,[lf]:e.EQUAL,[df]:e.GEQUAL,[cf]:e.GREATER,[uf]:e.NOTEQUAL};function Fe(E,v){if(v.type===Mr&&t.has("OES_texture_float_linear")===!1&&(v.magFilter===ar||v.magFilter===Mo||v.magFilter===Zn||v.magFilter===ai||v.minFilter===ar||v.minFilter===Mo||v.minFilter===Zn||v.minFilter===ai)&&console.warn("THREE.WebGLRenderer: Unable to use linear filtering with floating point textures. OES_texture_float_linear not supported on this device."),e.texParameteri(E,e.TEXTURE_WRAP_S,ie[v.wrapS]),e.texParameteri(E,e.TEXTURE_WRAP_T,ie[v.wrapT]),(E===e.TEXTURE_3D||E===e.TEXTURE_2D_ARRAY)&&e.texParameteri(E,e.TEXTURE_WRAP_R,ie[v.wrapR]),e.texParameteri(E,e.TEXTURE_MAG_FILTER,ce[v.magFilter]),e.texParameteri(E,e.TEXTURE_MIN_FILTER,ce[v.minFilter]),v.compareFunction&&(e.texParameteri(E,e.TEXTURE_COMPARE_MODE,e.COMPARE_REF_TO_TEXTURE),e.texParameteri(E,e.TEXTURE_COMPARE_FUNC,Pe[v.compareFunction])),t.has("EXT_texture_filter_anisotropic")===!0){if(v.magFilter===Kt||v.minFilter!==Zn&&v.minFilter!==ai||v.type===Mr&&t.has("OES_texture_float_linear")===!1)return;if(v.anisotropy>1||i.get(v).__currentAnisotropy){let L=t.get("EXT_texture_filter_anisotropic");e.texParameterf(E,L.TEXTURE_MAX_ANISOTROPY_EXT,Math.min(v.anisotropy,n.getMaxAnisotropy())),i.get(v).__currentAnisotropy=v.anisotropy}}}function $e(E,v){let L=!1;E.__webglInit===void 0&&(E.__webglInit=!0,v.addEventListener("dispose",I));let Y=v.source,J=h.get(Y);J===void 0&&(J={},h.set(Y,J));let X=V(v);if(X!==E.__cacheKey){J[X]===void 0&&(J[X]={texture:e.createTexture(),usedTimes:0},o.memory.textures++,L=!0),J[X].usedTimes++;let be=J[E.__cacheKey];be!==void 0&&(J[E.__cacheKey].usedTimes--,be.usedTimes===0&&S(v)),E.__cacheKey=X,E.__webglTexture=J[X].texture}return L}function We(E,v,L){return Math.floor(Math.floor(E/L)/v)}function j(E,v,L,Y){let J=E.updateRanges;if(J.length===0)r.texSubImage2D(e.TEXTURE_2D,0,0,0,v.width,v.height,L,Y,v.data);else{J.sort((Ae,re)=>Ae.start-re.start);let X=0;for(let Ae=1;Ae<J.length;Ae++){let re=J[X],de=J[Ae],Ne=re.start+re.count,we=We(de.start,v.width,4),pe=We(re.start,v.width,4);de.start<=Ne+1&&we===pe&&We(de.start+de.count-1,v.width,4)===we?re.count=Math.max(re.count,de.start+de.count-re.start):(++X,J[X]=de)}J.length=X+1;let be=e.getParameter(e.UNPACK_ROW_LENGTH),se=e.getParameter(e.UNPACK_SKIP_PIXELS),Te=e.getParameter(e.UNPACK_SKIP_ROWS);e.pixelStorei(e.UNPACK_ROW_LENGTH,v.width);for(let Ae=0,re=J.length;Ae<re;Ae++){let de=J[Ae],Ne=Math.floor(de.start/4),we=Math.ceil(de.count/4),pe=Ne%v.width,ze=Math.floor(Ne/v.width),w=we;e.pixelStorei(e.UNPACK_SKIP_PIXELS,pe),e.pixelStorei(e.UNPACK_SKIP_ROWS,ze),r.texSubImage2D(e.TEXTURE_2D,0,pe,ze,w,1,L,Y,v.data)}E.clearUpdateRanges(),e.pixelStorei(e.UNPACK_ROW_LENGTH,be),e.pixelStorei(e.UNPACK_SKIP_PIXELS,se),e.pixelStorei(e.UNPACK_SKIP_ROWS,Te)}}function oe(E,v,L){let Y=e.TEXTURE_2D;(v.isDataArrayTexture||v.isCompressedArrayTexture)&&(Y=e.TEXTURE_2D_ARRAY),v.isData3DTexture&&(Y=e.TEXTURE_3D);let J=$e(E,v),X=v.source;r.bindTexture(Y,E.__webglTexture,e.TEXTURE0+L);let be=i.get(X);if(X.version!==be.__version||J===!0){r.activeTexture(e.TEXTURE0+L);let se=Xe.getPrimaries(Xe.workingColorSpace),Te=v.colorSpace===Fr?null:Xe.getPrimaries(v.colorSpace),Ae=v.colorSpace===Fr||se===Te?e.NONE:e.BROWSER_DEFAULT_WEBGL;e.pixelStorei(e.UNPACK_FLIP_Y_WEBGL,v.flipY),e.pixelStorei(e.UNPACK_PREMULTIPLY_ALPHA_WEBGL,v.premultiplyAlpha),e.pixelStorei(e.UNPACK_ALIGNMENT,v.unpackAlignment),e.pixelStorei(e.UNPACK_COLORSPACE_CONVERSION_WEBGL,Ae);let re=_(v.image,!1,n.maxTextureSize);re=dt(v,re);let de=a.convert(v.format,v.colorSpace),Ne=a.convert(v.type),we=y(v.internalFormat,de,Ne,v.colorSpace,v.isVideoTexture);Fe(Y,v);let pe,ze=v.mipmaps,w=v.isVideoTexture!==!0,he=be.__version===void 0||J===!0,le=X.dataReady,ye=O(v,re);if(v.isDepthTexture)we=A(v.format===pn,v.type),he&&(w?r.texStorage2D(e.TEXTURE_2D,1,we,re.width,re.height):r.texImage2D(e.TEXTURE_2D,0,we,re.width,re.height,0,de,Ne,null));else if(v.isDataTexture)if(ze.length>0){w&&he&&r.texStorage2D(e.TEXTURE_2D,ye,we,ze[0].width,ze[0].height);for(let te=0,K=ze.length;te<K;te++)pe=ze[te],w?le&&r.texSubImage2D(e.TEXTURE_2D,te,0,0,pe.width,pe.height,de,Ne,pe.data):r.texImage2D(e.TEXTURE_2D,te,we,pe.width,pe.height,0,de,Ne,pe.data);v.generateMipmaps=!1}else w?(he&&r.texStorage2D(e.TEXTURE_2D,ye,we,re.width,re.height),le&&j(v,re,de,Ne)):r.texImage2D(e.TEXTURE_2D,0,we,re.width,re.height,0,de,Ne,re.data);else if(v.isCompressedTexture)if(v.isCompressedArrayTexture){w&&he&&r.texStorage3D(e.TEXTURE_2D_ARRAY,ye,we,ze[0].width,ze[0].height,re.depth);for(let te=0,K=ze.length;te<K;te++)if(pe=ze[te],v.format!==qt)if(de!==null)if(w){if(le)if(v.layerUpdates.size>0){let xe=lu(pe.width,pe.height,v.format,v.type);for(let Ie of v.layerUpdates){let ot=pe.data.subarray(Ie*xe/pe.data.BYTES_PER_ELEMENT,(Ie+1)*xe/pe.data.BYTES_PER_ELEMENT);r.compressedTexSubImage3D(e.TEXTURE_2D_ARRAY,te,0,0,Ie,pe.width,pe.height,1,de,ot)}v.clearLayerUpdates()}else r.compressedTexSubImage3D(e.TEXTURE_2D_ARRAY,te,0,0,0,pe.width,pe.height,re.depth,de,pe.data)}else r.compressedTexImage3D(e.TEXTURE_2D_ARRAY,te,we,pe.width,pe.height,re.depth,0,pe.data,0,0);else console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()");else w?le&&r.texSubImage3D(e.TEXTURE_2D_ARRAY,te,0,0,0,pe.width,pe.height,re.depth,de,Ne,pe.data):r.texImage3D(e.TEXTURE_2D_ARRAY,te,we,pe.width,pe.height,re.depth,0,de,Ne,pe.data)}else{w&&he&&r.texStorage2D(e.TEXTURE_2D,ye,we,ze[0].width,ze[0].height);for(let te=0,K=ze.length;te<K;te++)pe=ze[te],v.format!==qt?de!==null?w?le&&r.compressedTexSubImage2D(e.TEXTURE_2D,te,0,0,pe.width,pe.height,de,pe.data):r.compressedTexImage2D(e.TEXTURE_2D,te,we,pe.width,pe.height,0,pe.data):console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()"):w?le&&r.texSubImage2D(e.TEXTURE_2D,te,0,0,pe.width,pe.height,de,Ne,pe.data):r.texImage2D(e.TEXTURE_2D,te,we,pe.width,pe.height,0,de,Ne,pe.data)}else if(v.isDataArrayTexture)if(w){if(he&&r.texStorage3D(e.TEXTURE_2D_ARRAY,ye,we,re.width,re.height,re.depth),le)if(v.layerUpdates.size>0){let te=lu(re.width,re.height,v.format,v.type);for(let K of v.layerUpdates){let xe=re.data.subarray(K*te/re.data.BYTES_PER_ELEMENT,(K+1)*te/re.data.BYTES_PER_ELEMENT);r.texSubImage3D(e.TEXTURE_2D_ARRAY,0,0,0,K,re.width,re.height,1,de,Ne,xe)}v.clearLayerUpdates()}else r.texSubImage3D(e.TEXTURE_2D_ARRAY,0,0,0,0,re.width,re.height,re.depth,de,Ne,re.data)}else r.texImage3D(e.TEXTURE_2D_ARRAY,0,we,re.width,re.height,re.depth,0,de,Ne,re.data);else if(v.isData3DTexture)w?(he&&r.texStorage3D(e.TEXTURE_3D,ye,we,re.width,re.height,re.depth),le&&r.texSubImage3D(e.TEXTURE_3D,0,0,0,0,re.width,re.height,re.depth,de,Ne,re.data)):r.texImage3D(e.TEXTURE_3D,0,we,re.width,re.height,re.depth,0,de,Ne,re.data);else if(v.isFramebufferTexture){if(he)if(w)r.texStorage2D(e.TEXTURE_2D,ye,we,re.width,re.height);else{let te=re.width,K=re.height;for(let xe=0;xe<ye;xe++)r.texImage2D(e.TEXTURE_2D,xe,we,te,K,0,de,Ne,null),te>>=1,K>>=1}}else if(ze.length>0){if(w&&he){let te=at(ze[0]);r.texStorage2D(e.TEXTURE_2D,ye,we,te.width,te.height)}for(let te=0,K=ze.length;te<K;te++)pe=ze[te],w?le&&r.texSubImage2D(e.TEXTURE_2D,te,0,0,de,Ne,pe):r.texImage2D(e.TEXTURE_2D,te,we,de,Ne,pe);v.generateMipmaps=!1}else if(w){if(he){let te=at(re);r.texStorage2D(e.TEXTURE_2D,ye,we,te.width,te.height)}le&&r.texSubImage2D(e.TEXTURE_2D,0,0,0,de,Ne,re)}else r.texImage2D(e.TEXTURE_2D,0,we,de,Ne,re);f(v)&&p(Y),be.__version=X.version,v.onUpdate&&v.onUpdate(v)}E.__version=v.version}function ne(E,v,L){if(v.image.length!==6)return;let Y=$e(E,v),J=v.source;r.bindTexture(e.TEXTURE_CUBE_MAP,E.__webglTexture,e.TEXTURE0+L);let X=i.get(J);if(J.version!==X.__version||Y===!0){r.activeTexture(e.TEXTURE0+L);let be=Xe.getPrimaries(Xe.workingColorSpace),se=v.colorSpace===Fr?null:Xe.getPrimaries(v.colorSpace),Te=v.colorSpace===Fr||be===se?e.NONE:e.BROWSER_DEFAULT_WEBGL;e.pixelStorei(e.UNPACK_FLIP_Y_WEBGL,v.flipY),e.pixelStorei(e.UNPACK_PREMULTIPLY_ALPHA_WEBGL,v.premultiplyAlpha),e.pixelStorei(e.UNPACK_ALIGNMENT,v.unpackAlignment),e.pixelStorei(e.UNPACK_COLORSPACE_CONVERSION_WEBGL,Te);let Ae=v.isCompressedTexture||v.image[0].isCompressedTexture,re=v.image[0]&&v.image[0].isDataTexture,de=[];for(let K=0;K<6;K++)!Ae&&!re?de[K]=_(v.image[K],!0,n.maxCubemapSize):de[K]=re?v.image[K].image:v.image[K],de[K]=dt(v,de[K]);let Ne=de[0],we=a.convert(v.format,v.colorSpace),pe=a.convert(v.type),ze=y(v.internalFormat,we,pe,v.colorSpace),w=v.isVideoTexture!==!0,he=X.__version===void 0||Y===!0,le=J.dataReady,ye=O(v,Ne);Fe(e.TEXTURE_CUBE_MAP,v);let te;if(Ae){w&&he&&r.texStorage2D(e.TEXTURE_CUBE_MAP,ye,ze,Ne.width,Ne.height);for(let K=0;K<6;K++){te=de[K].mipmaps;for(let xe=0;xe<te.length;xe++){let Ie=te[xe];v.format!==qt?we!==null?w?le&&r.compressedTexSubImage2D(e.TEXTURE_CUBE_MAP_POSITIVE_X+K,xe,0,0,Ie.width,Ie.height,we,Ie.data):r.compressedTexImage2D(e.TEXTURE_CUBE_MAP_POSITIVE_X+K,xe,ze,Ie.width,Ie.height,0,Ie.data):console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .setTextureCube()"):w?le&&r.texSubImage2D(e.TEXTURE_CUBE_MAP_POSITIVE_X+K,xe,0,0,Ie.width,Ie.height,we,pe,Ie.data):r.texImage2D(e.TEXTURE_CUBE_MAP_POSITIVE_X+K,xe,ze,Ie.width,Ie.height,0,we,pe,Ie.data)}}}else{if(te=v.mipmaps,w&&he){te.length>0&&ye++;let K=at(de[0]);r.texStorage2D(e.TEXTURE_CUBE_MAP,ye,ze,K.width,K.height)}for(let K=0;K<6;K++)if(re){w?le&&r.texSubImage2D(e.TEXTURE_CUBE_MAP_POSITIVE_X+K,0,0,0,de[K].width,de[K].height,we,pe,de[K].data):r.texImage2D(e.TEXTURE_CUBE_MAP_POSITIVE_X+K,0,ze,de[K].width,de[K].height,0,we,pe,de[K].data);for(let xe=0;xe<te.length;xe++){let Ie=te[xe].image[K].image;w?le&&r.texSubImage2D(e.TEXTURE_CUBE_MAP_POSITIVE_X+K,xe+1,0,0,Ie.width,Ie.height,we,pe,Ie.data):r.texImage2D(e.TEXTURE_CUBE_MAP_POSITIVE_X+K,xe+1,ze,Ie.width,Ie.height,0,we,pe,Ie.data)}}else{w?le&&r.texSubImage2D(e.TEXTURE_CUBE_MAP_POSITIVE_X+K,0,0,0,we,pe,de[K]):r.texImage2D(e.TEXTURE_CUBE_MAP_POSITIVE_X+K,0,ze,we,pe,de[K]);for(let xe=0;xe<te.length;xe++){let Ie=te[xe];w?le&&r.texSubImage2D(e.TEXTURE_CUBE_MAP_POSITIVE_X+K,xe+1,0,0,we,pe,Ie.image[K]):r.texImage2D(e.TEXTURE_CUBE_MAP_POSITIVE_X+K,xe+1,ze,we,pe,Ie.image[K])}}}f(v)&&p(e.TEXTURE_CUBE_MAP),X.__version=J.version,v.onUpdate&&v.onUpdate(v)}E.__version=v.version}function z(E,v,L,Y,J,X){let be=a.convert(L.format,L.colorSpace),se=a.convert(L.type),Te=y(L.internalFormat,be,se,L.colorSpace),Ae=i.get(v),re=i.get(L);if(re.__renderTarget=v,!Ae.__hasExternalTextures){let de=Math.max(1,v.width>>X),Ne=Math.max(1,v.height>>X);J===e.TEXTURE_3D||J===e.TEXTURE_2D_ARRAY?r.texImage3D(J,X,Te,de,Ne,v.depth,0,be,se,null):r.texImage2D(J,X,Te,de,Ne,0,be,se,null)}r.bindFramebuffer(e.FRAMEBUFFER,E),Ce(v)?s.framebufferTexture2DMultisampleEXT(e.FRAMEBUFFER,Y,J,re.__webglTexture,0,Re(v)):(J===e.TEXTURE_2D||J>=e.TEXTURE_CUBE_MAP_POSITIVE_X&&J<=e.TEXTURE_CUBE_MAP_NEGATIVE_Z)&&e.framebufferTexture2D(e.FRAMEBUFFER,Y,J,re.__webglTexture,X),r.bindFramebuffer(e.FRAMEBUFFER,null)}function ae(E,v,L){if(e.bindRenderbuffer(e.RENDERBUFFER,E),v.depthBuffer){let Y=v.depthTexture,J=Y&&Y.isDepthTexture?Y.type:null,X=A(v.stencilBuffer,J),be=v.stencilBuffer?e.DEPTH_STENCIL_ATTACHMENT:e.DEPTH_ATTACHMENT,se=Re(v);Ce(v)?s.renderbufferStorageMultisampleEXT(e.RENDERBUFFER,se,X,v.width,v.height):L?e.renderbufferStorageMultisample(e.RENDERBUFFER,se,X,v.width,v.height):e.renderbufferStorage(e.RENDERBUFFER,X,v.width,v.height),e.framebufferRenderbuffer(e.FRAMEBUFFER,be,e.RENDERBUFFER,E)}else{let Y=v.textures;for(let J=0;J<Y.length;J++){let X=Y[J],be=a.convert(X.format,X.colorSpace),se=a.convert(X.type),Te=y(X.internalFormat,be,se,X.colorSpace),Ae=Re(v);L&&Ce(v)===!1?e.renderbufferStorageMultisample(e.RENDERBUFFER,Ae,Te,v.width,v.height):Ce(v)?s.renderbufferStorageMultisampleEXT(e.RENDERBUFFER,Ae,Te,v.width,v.height):e.renderbufferStorage(e.RENDERBUFFER,Te,v.width,v.height)}}e.bindRenderbuffer(e.RENDERBUFFER,null)}function $(E,v){if(v&&v.isWebGLCubeRenderTarget)throw new Error("Depth Texture with cube render targets is not supported");if(r.bindFramebuffer(e.FRAMEBUFFER,E),!(v.depthTexture&&v.depthTexture.isDepthTexture))throw new Error("renderTarget.depthTexture must be an instance of THREE.DepthTexture");let L=i.get(v.depthTexture);L.__renderTarget=v,(!L.__webglTexture||v.depthTexture.image.width!==v.width||v.depthTexture.image.height!==v.height)&&(v.depthTexture.image.width=v.width,v.depthTexture.image.height=v.height,v.depthTexture.needsUpdate=!0),Z(v.depthTexture,0);let Y=L.__webglTexture,J=Re(v);if(v.depthTexture.format===hn)Ce(v)?s.framebufferTexture2DMultisampleEXT(e.FRAMEBUFFER,e.DEPTH_ATTACHMENT,e.TEXTURE_2D,Y,0,J):e.framebufferTexture2D(e.FRAMEBUFFER,e.DEPTH_ATTACHMENT,e.TEXTURE_2D,Y,0);else if(v.depthTexture.format===pn)Ce(v)?s.framebufferTexture2DMultisampleEXT(e.FRAMEBUFFER,e.DEPTH_STENCIL_ATTACHMENT,e.TEXTURE_2D,Y,0,J):e.framebufferTexture2D(e.FRAMEBUFFER,e.DEPTH_STENCIL_ATTACHMENT,e.TEXTURE_2D,Y,0);else throw new Error("Unknown depthTexture format")}function ge(E){let v=i.get(E),L=E.isWebGLCubeRenderTarget===!0;if(v.__boundDepthTexture!==E.depthTexture){let Y=E.depthTexture;if(v.__depthDisposeCallback&&v.__depthDisposeCallback(),Y){let J=()=>{delete v.__boundDepthTexture,delete v.__depthDisposeCallback,Y.removeEventListener("dispose",J)};Y.addEventListener("dispose",J),v.__depthDisposeCallback=J}v.__boundDepthTexture=Y}if(E.depthTexture&&!v.__autoAllocateDepthBuffer){if(L)throw new Error("target.depthTexture not supported in Cube render targets");let Y=E.texture.mipmaps;Y&&Y.length>0?$(v.__webglFramebuffer[0],E):$(v.__webglFramebuffer,E)}else if(L){v.__webglDepthbuffer=[];for(let Y=0;Y<6;Y++)if(r.bindFramebuffer(e.FRAMEBUFFER,v.__webglFramebuffer[Y]),v.__webglDepthbuffer[Y]===void 0)v.__webglDepthbuffer[Y]=e.createRenderbuffer(),ae(v.__webglDepthbuffer[Y],E,!1);else{let J=E.stencilBuffer?e.DEPTH_STENCIL_ATTACHMENT:e.DEPTH_ATTACHMENT,X=v.__webglDepthbuffer[Y];e.bindRenderbuffer(e.RENDERBUFFER,X),e.framebufferRenderbuffer(e.FRAMEBUFFER,J,e.RENDERBUFFER,X)}}else{let Y=E.texture.mipmaps;if(Y&&Y.length>0?r.bindFramebuffer(e.FRAMEBUFFER,v.__webglFramebuffer[0]):r.bindFramebuffer(e.FRAMEBUFFER,v.__webglFramebuffer),v.__webglDepthbuffer===void 0)v.__webglDepthbuffer=e.createRenderbuffer(),ae(v.__webglDepthbuffer,E,!1);else{let J=E.stencilBuffer?e.DEPTH_STENCIL_ATTACHMENT:e.DEPTH_ATTACHMENT,X=v.__webglDepthbuffer;e.bindRenderbuffer(e.RENDERBUFFER,X),e.framebufferRenderbuffer(e.FRAMEBUFFER,J,e.RENDERBUFFER,X)}}r.bindFramebuffer(e.FRAMEBUFFER,null)}function T(E,v,L){let Y=i.get(E);v!==void 0&&z(Y.__webglFramebuffer,E,E.texture,e.COLOR_ATTACHMENT0,e.TEXTURE_2D,0),L!==void 0&&ge(E)}function Se(E){let v=E.texture,L=i.get(E),Y=i.get(v);E.addEventListener("dispose",C);let J=E.textures,X=E.isWebGLCubeRenderTarget===!0,be=J.length>1;if(be||(Y.__webglTexture===void 0&&(Y.__webglTexture=e.createTexture()),Y.__version=v.version,o.memory.textures++),X){L.__webglFramebuffer=[];for(let se=0;se<6;se++)if(v.mipmaps&&v.mipmaps.length>0){L.__webglFramebuffer[se]=[];for(let Te=0;Te<v.mipmaps.length;Te++)L.__webglFramebuffer[se][Te]=e.createFramebuffer()}else L.__webglFramebuffer[se]=e.createFramebuffer()}else{if(v.mipmaps&&v.mipmaps.length>0){L.__webglFramebuffer=[];for(let se=0;se<v.mipmaps.length;se++)L.__webglFramebuffer[se]=e.createFramebuffer()}else L.__webglFramebuffer=e.createFramebuffer();if(be)for(let se=0,Te=J.length;se<Te;se++){let Ae=i.get(J[se]);Ae.__webglTexture===void 0&&(Ae.__webglTexture=e.createTexture(),o.memory.textures++)}if(E.samples>0&&Ce(E)===!1){L.__webglMultisampledFramebuffer=e.createFramebuffer(),L.__webglColorRenderbuffer=[],r.bindFramebuffer(e.FRAMEBUFFER,L.__webglMultisampledFramebuffer);for(let se=0;se<J.length;se++){let Te=J[se];L.__webglColorRenderbuffer[se]=e.createRenderbuffer(),e.bindRenderbuffer(e.RENDERBUFFER,L.__webglColorRenderbuffer[se]);let Ae=a.convert(Te.format,Te.colorSpace),re=a.convert(Te.type),de=y(Te.internalFormat,Ae,re,Te.colorSpace,E.isXRRenderTarget===!0),Ne=Re(E);e.renderbufferStorageMultisample(e.RENDERBUFFER,Ne,de,E.width,E.height),e.framebufferRenderbuffer(e.FRAMEBUFFER,e.COLOR_ATTACHMENT0+se,e.RENDERBUFFER,L.__webglColorRenderbuffer[se])}e.bindRenderbuffer(e.RENDERBUFFER,null),E.depthBuffer&&(L.__webglDepthRenderbuffer=e.createRenderbuffer(),ae(L.__webglDepthRenderbuffer,E,!0)),r.bindFramebuffer(e.FRAMEBUFFER,null)}}if(X){r.bindTexture(e.TEXTURE_CUBE_MAP,Y.__webglTexture),Fe(e.TEXTURE_CUBE_MAP,v);for(let se=0;se<6;se++)if(v.mipmaps&&v.mipmaps.length>0)for(let Te=0;Te<v.mipmaps.length;Te++)z(L.__webglFramebuffer[se][Te],E,v,e.COLOR_ATTACHMENT0,e.TEXTURE_CUBE_MAP_POSITIVE_X+se,Te);else z(L.__webglFramebuffer[se],E,v,e.COLOR_ATTACHMENT0,e.TEXTURE_CUBE_MAP_POSITIVE_X+se,0);f(v)&&p(e.TEXTURE_CUBE_MAP),r.unbindTexture()}else if(be){for(let se=0,Te=J.length;se<Te;se++){let Ae=J[se],re=i.get(Ae),de=e.TEXTURE_2D;(E.isWebGL3DRenderTarget||E.isWebGLArrayRenderTarget)&&(de=E.isWebGL3DRenderTarget?e.TEXTURE_3D:e.TEXTURE_2D_ARRAY),r.bindTexture(de,re.__webglTexture),Fe(de,Ae),z(L.__webglFramebuffer,E,Ae,e.COLOR_ATTACHMENT0+se,de,0),f(Ae)&&p(de)}r.unbindTexture()}else{let se=e.TEXTURE_2D;if((E.isWebGL3DRenderTarget||E.isWebGLArrayRenderTarget)&&(se=E.isWebGL3DRenderTarget?e.TEXTURE_3D:e.TEXTURE_2D_ARRAY),r.bindTexture(se,Y.__webglTexture),Fe(se,v),v.mipmaps&&v.mipmaps.length>0)for(let Te=0;Te<v.mipmaps.length;Te++)z(L.__webglFramebuffer[Te],E,v,e.COLOR_ATTACHMENT0,se,Te);else z(L.__webglFramebuffer,E,v,e.COLOR_ATTACHMENT0,se,0);f(v)&&p(se),r.unbindTexture()}E.depthBuffer&&ge(E)}function Ee(E){let v=E.textures;for(let L=0,Y=v.length;L<Y;L++){let J=v[L];if(f(J)){let X=R(E),be=i.get(J).__webglTexture;r.bindTexture(X,be),p(X),r.unbindTexture()}}}let Ve=[],fe=[];function Ze(E){if(E.samples>0){if(Ce(E)===!1){let v=E.textures,L=E.width,Y=E.height,J=e.COLOR_BUFFER_BIT,X=E.stencilBuffer?e.DEPTH_STENCIL_ATTACHMENT:e.DEPTH_ATTACHMENT,be=i.get(E),se=v.length>1;if(se)for(let Ae=0;Ae<v.length;Ae++)r.bindFramebuffer(e.FRAMEBUFFER,be.__webglMultisampledFramebuffer),e.framebufferRenderbuffer(e.FRAMEBUFFER,e.COLOR_ATTACHMENT0+Ae,e.RENDERBUFFER,null),r.bindFramebuffer(e.FRAMEBUFFER,be.__webglFramebuffer),e.framebufferTexture2D(e.DRAW_FRAMEBUFFER,e.COLOR_ATTACHMENT0+Ae,e.TEXTURE_2D,null,0);r.bindFramebuffer(e.READ_FRAMEBUFFER,be.__webglMultisampledFramebuffer);let Te=E.texture.mipmaps;Te&&Te.length>0?r.bindFramebuffer(e.DRAW_FRAMEBUFFER,be.__webglFramebuffer[0]):r.bindFramebuffer(e.DRAW_FRAMEBUFFER,be.__webglFramebuffer);for(let Ae=0;Ae<v.length;Ae++){if(E.resolveDepthBuffer&&(E.depthBuffer&&(J|=e.DEPTH_BUFFER_BIT),E.stencilBuffer&&E.resolveStencilBuffer&&(J|=e.STENCIL_BUFFER_BIT)),se){e.framebufferRenderbuffer(e.READ_FRAMEBUFFER,e.COLOR_ATTACHMENT0,e.RENDERBUFFER,be.__webglColorRenderbuffer[Ae]);let re=i.get(v[Ae]).__webglTexture;e.framebufferTexture2D(e.DRAW_FRAMEBUFFER,e.COLOR_ATTACHMENT0,e.TEXTURE_2D,re,0)}e.blitFramebuffer(0,0,L,Y,0,0,L,Y,J,e.NEAREST),c===!0&&(Ve.length=0,fe.length=0,Ve.push(e.COLOR_ATTACHMENT0+Ae),E.depthBuffer&&E.resolveDepthBuffer===!1&&(Ve.push(X),fe.push(X),e.invalidateFramebuffer(e.DRAW_FRAMEBUFFER,fe)),e.invalidateFramebuffer(e.READ_FRAMEBUFFER,Ve))}if(r.bindFramebuffer(e.READ_FRAMEBUFFER,null),r.bindFramebuffer(e.DRAW_FRAMEBUFFER,null),se)for(let Ae=0;Ae<v.length;Ae++){r.bindFramebuffer(e.FRAMEBUFFER,be.__webglMultisampledFramebuffer),e.framebufferRenderbuffer(e.FRAMEBUFFER,e.COLOR_ATTACHMENT0+Ae,e.RENDERBUFFER,be.__webglColorRenderbuffer[Ae]);let re=i.get(v[Ae]).__webglTexture;r.bindFramebuffer(e.FRAMEBUFFER,be.__webglFramebuffer),e.framebufferTexture2D(e.DRAW_FRAMEBUFFER,e.COLOR_ATTACHMENT0+Ae,e.TEXTURE_2D,re,0)}r.bindFramebuffer(e.DRAW_FRAMEBUFFER,be.__webglMultisampledFramebuffer)}else if(E.depthBuffer&&E.resolveDepthBuffer===!1&&c){let v=E.stencilBuffer?e.DEPTH_STENCIL_ATTACHMENT:e.DEPTH_ATTACHMENT;e.invalidateFramebuffer(e.DRAW_FRAMEBUFFER,[v])}}}function Re(E){return Math.min(n.maxSamples,E.samples)}function Ce(E){let v=i.get(E);return E.samples>0&&t.has("WEBGL_multisampled_render_to_texture")===!0&&v.__useRenderToTexture!==!1}function mt(E){let v=o.render.frame;l.get(E)!==v&&(l.set(E,v),E.update())}function dt(E,v){let L=E.colorSpace,Y=E.format,J=E.type;return E.isCompressedTexture===!0||E.isVideoTexture===!0||L!==Gi&&L!==Fr&&(Xe.getTransfer(L)===Je?(Y!==qt||J!==lr)&&console.warn("THREE.WebGLTextures: sRGB encoded textures have to use RGBAFormat and UnsignedByteType."):console.error("THREE.WebGLTextures: Unsupported texture color space:",L)),v}function at(E){return typeof HTMLImageElement<"u"&&E instanceof HTMLImageElement?(u.width=E.naturalWidth||E.width,u.height=E.naturalHeight||E.height):typeof VideoFrame<"u"&&E instanceof VideoFrame?(u.width=E.displayWidth,u.height=E.displayHeight):(u.width=E.width,u.height=E.height),u}this.allocateTextureUnit=H,this.resetTextureUnits=k,this.setTexture2D=Z,this.setTexture2DArray=G,this.setTexture3D=ee,this.setTextureCube=W,this.rebindTextures=T,this.setupRenderTarget=Se,this.updateRenderTargetMipmap=Ee,this.updateMultisampleRenderTarget=Ze,this.setupDepthRenderbuffer=ge,this.setupFrameBufferTexture=z,this.useMultisampledRTT=Ce}function G0(e,t){function r(i,n=Fr){let a,o=Xe.getTransfer(n);if(i===lr)return e.UNSIGNED_BYTE;if(i===Js)return e.UNSIGNED_SHORT_4_4_4_4;if(i===Zs)return e.UNSIGNED_SHORT_5_5_5_1;if(i===Bu)return e.UNSIGNED_INT_5_9_9_9_REV;if(i===Vu)return e.UNSIGNED_INT_10F_11F_11F_REV;if(i===Fu)return e.BYTE;if(i===ku)return e.SHORT;if(i===un)return e.UNSIGNED_SHORT;if(i===Ks)return e.INT;if(i===si)return e.UNSIGNED_INT;if(i===Mr)return e.FLOAT;if(i===mn)return e.HALF_FLOAT;if(i===zu)return e.ALPHA;if(i===Hu)return e.RGB;if(i===qt)return e.RGBA;if(i===hn)return e.DEPTH_COMPONENT;if(i===pn)return e.DEPTH_STENCIL;if(i===Gu)return e.RED;if(i===$s)return e.RED_INTEGER;if(i===Wu)return e.RG;if(i===Qs)return e.RG_INTEGER;if(i===el)return e.RGBA_INTEGER;if(i===xa||i===ya||i===Sa||i===Ea)if(o===Je)if(a=t.get("WEBGL_compressed_texture_s3tc_srgb"),a!==null){if(i===xa)return a.COMPRESSED_SRGB_S3TC_DXT1_EXT;if(i===ya)return a.COMPRESSED_SRGB_ALPHA_S3TC_DXT1_EXT;if(i===Sa)return a.COMPRESSED_SRGB_ALPHA_S3TC_DXT3_EXT;if(i===Ea)return a.COMPRESSED_SRGB_ALPHA_S3TC_DXT5_EXT}else return null;else if(a=t.get("WEBGL_compressed_texture_s3tc"),a!==null){if(i===xa)return a.COMPRESSED_RGB_S3TC_DXT1_EXT;if(i===ya)return a.COMPRESSED_RGBA_S3TC_DXT1_EXT;if(i===Sa)return a.COMPRESSED_RGBA_S3TC_DXT3_EXT;if(i===Ea)return a.COMPRESSED_RGBA_S3TC_DXT5_EXT}else return null;if(i===vs||i===_s||i===bs||i===xs)if(a=t.get("WEBGL_compressed_texture_pvrtc"),a!==null){if(i===vs)return a.COMPRESSED_RGB_PVRTC_4BPPV1_IMG;if(i===_s)return a.COMPRESSED_RGB_PVRTC_2BPPV1_IMG;if(i===bs)return a.COMPRESSED_RGBA_PVRTC_4BPPV1_IMG;if(i===xs)return a.COMPRESSED_RGBA_PVRTC_2BPPV1_IMG}else return null;if(i===ys||i===Ss||i===Es)if(a=t.get("WEBGL_compressed_texture_etc"),a!==null){if(i===ys||i===Ss)return o===Je?a.COMPRESSED_SRGB8_ETC2:a.COMPRESSED_RGB8_ETC2;if(i===Es)return o===Je?a.COMPRESSED_SRGB8_ALPHA8_ETC2_EAC:a.COMPRESSED_RGBA8_ETC2_EAC}else return null;if(i===Ts||i===Ms||i===As||i===ws||i===Rs||i===Cs||i===Is||i===Ns||i===Ps||i===Os||i===Ls||i===Us||i===Ds||i===Fs)if(a=t.get("WEBGL_compressed_texture_astc"),a!==null){if(i===Ts)return o===Je?a.COMPRESSED_SRGB8_ALPHA8_ASTC_4x4_KHR:a.COMPRESSED_RGBA_ASTC_4x4_KHR;if(i===Ms)return o===Je?a.COMPRESSED_SRGB8_ALPHA8_ASTC_5x4_KHR:a.COMPRESSED_RGBA_ASTC_5x4_KHR;if(i===As)return o===Je?a.COMPRESSED_SRGB8_ALPHA8_ASTC_5x5_KHR:a.COMPRESSED_RGBA_ASTC_5x5_KHR;if(i===ws)return o===Je?a.COMPRESSED_SRGB8_ALPHA8_ASTC_6x5_KHR:a.COMPRESSED_RGBA_ASTC_6x5_KHR;if(i===Rs)return o===Je?a.COMPRESSED_SRGB8_ALPHA8_ASTC_6x6_KHR:a.COMPRESSED_RGBA_ASTC_6x6_KHR;if(i===Cs)return o===Je?a.COMPRESSED_SRGB8_ALPHA8_ASTC_8x5_KHR:a.COMPRESSED_RGBA_ASTC_8x5_KHR;if(i===Is)return o===Je?a.COMPRESSED_SRGB8_ALPHA8_ASTC_8x6_KHR:a.COMPRESSED_RGBA_ASTC_8x6_KHR;if(i===Ns)return o===Je?a.COMPRESSED_SRGB8_ALPHA8_ASTC_8x8_KHR:a.COMPRESSED_RGBA_ASTC_8x8_KHR;if(i===Ps)return o===Je?a.COMPRESSED_SRGB8_ALPHA8_ASTC_10x5_KHR:a.COMPRESSED_RGBA_ASTC_10x5_KHR;if(i===Os)return o===Je?a.COMPRESSED_SRGB8_ALPHA8_ASTC_10x6_KHR:a.COMPRESSED_RGBA_ASTC_10x6_KHR;if(i===Ls)return o===Je?a.COMPRESSED_SRGB8_ALPHA8_ASTC_10x8_KHR:a.COMPRESSED_RGBA_ASTC_10x8_KHR;if(i===Us)return o===Je?a.COMPRESSED_SRGB8_ALPHA8_ASTC_10x10_KHR:a.COMPRESSED_RGBA_ASTC_10x10_KHR;if(i===Ds)return o===Je?a.COMPRESSED_SRGB8_ALPHA8_ASTC_12x10_KHR:a.COMPRESSED_RGBA_ASTC_12x10_KHR;if(i===Fs)return o===Je?a.COMPRESSED_SRGB8_ALPHA8_ASTC_12x12_KHR:a.COMPRESSED_RGBA_ASTC_12x12_KHR}else return null;if(i===ks||i===Bs||i===Vs)if(a=t.get("EXT_texture_compression_bptc"),a!==null){if(i===ks)return o===Je?a.COMPRESSED_SRGB_ALPHA_BPTC_UNORM_EXT:a.COMPRESSED_RGBA_BPTC_UNORM_EXT;if(i===Bs)return a.COMPRESSED_RGB_BPTC_SIGNED_FLOAT_EXT;if(i===Vs)return a.COMPRESSED_RGB_BPTC_UNSIGNED_FLOAT_EXT}else return null;if(i===zs||i===Hs||i===Gs||i===Ws)if(a=t.get("EXT_texture_compression_rgtc"),a!==null){if(i===zs)return a.COMPRESSED_RED_RGTC1_EXT;if(i===Hs)return a.COMPRESSED_SIGNED_RED_RGTC1_EXT;if(i===Gs)return a.COMPRESSED_RED_GREEN_RGTC2_EXT;if(i===Ws)return a.COMPRESSED_SIGNED_RED_GREEN_RGTC2_EXT}else return null;return i===dn?e.UNSIGNED_INT_24_8:e[i]!==void 0?e[i]:null}return{convert:r}}var W0=`
void main() {

	gl_Position = vec4( position, 1.0 );

}`,j0=`
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

}`,X0=class{constructor(){this.texture=null,this.mesh=null,this.depthNear=0,this.depthFar=0}init(e,t){if(this.texture===null){let r=new hd(e.texture);(e.depthNear!==t.depthNear||e.depthFar!==t.depthFar)&&(this.depthNear=e.depthNear,this.depthFar=e.depthFar),this.texture=r}}getMesh(e){if(this.texture!==null&&this.mesh===null){let t=e.cameras[0].viewport,r=new Hr({vertexShader:W0,fragmentShader:j0,uniforms:{depthColor:{value:this.texture},depthWidth:{value:t.z},depthHeight:{value:t.w}}});this.mesh=new Yt(new pd(20,20),r)}return this.mesh}reset(){this.texture=null,this.mesh=null}getDepthTexture(){return this.texture}},q0=class extends ji{constructor(e,t){super();let r=this,i=null,n=1,a=null,o="local-floor",s=1,c=null,u=null,l=null,d=null,h=null,m=null,g=typeof XRWebGLBinding<"u",_=new X0,f={},p=t.getContextAttributes(),R=null,y=null,A=[],O=[],I=new Ye,C=null,U=new Xt;U.viewport=new lt;let S=new Xt;S.viewport=new lt;let x=[U,S],M=new am,k=null,H=null;this.cameraAutoUpdate=!0,this.enabled=!1,this.isPresenting=!1,this.getController=function(j){let oe=A[j];return oe===void 0&&(oe=new Ko,A[j]=oe),oe.getTargetRaySpace()},this.getControllerGrip=function(j){let oe=A[j];return oe===void 0&&(oe=new Ko,A[j]=oe),oe.getGripSpace()},this.getHand=function(j){let oe=A[j];return oe===void 0&&(oe=new Ko,A[j]=oe),oe.getHandSpace()};function V(j){let oe=O.indexOf(j.inputSource);if(oe===-1)return;let ne=A[oe];ne!==void 0&&(ne.update(j.inputSource,j.frame,c||a),ne.dispatchEvent({type:j.type,data:j.inputSource}))}function Z(){i.removeEventListener("select",V),i.removeEventListener("selectstart",V),i.removeEventListener("selectend",V),i.removeEventListener("squeeze",V),i.removeEventListener("squeezestart",V),i.removeEventListener("squeezeend",V),i.removeEventListener("end",Z),i.removeEventListener("inputsourceschange",G);for(let j=0;j<A.length;j++){let oe=O[j];oe!==null&&(O[j]=null,A[j].disconnect(oe))}k=null,H=null,_.reset();for(let j in f)delete f[j];e.setRenderTarget(R),h=null,d=null,l=null,i=null,y=null,We.stop(),r.isPresenting=!1,e.setPixelRatio(C),e.setSize(I.width,I.height,!1),r.dispatchEvent({type:"sessionend"})}this.setFramebufferScaleFactor=function(j){n=j,r.isPresenting===!0&&console.warn("THREE.WebXRManager: Cannot change framebuffer scale while presenting.")},this.setReferenceSpaceType=function(j){o=j,r.isPresenting===!0&&console.warn("THREE.WebXRManager: Cannot change reference space type while presenting.")},this.getReferenceSpace=function(){return c||a},this.setReferenceSpace=function(j){c=j},this.getBaseLayer=function(){return d!==null?d:h},this.getBinding=function(){return l===null&&g&&(l=new XRWebGLBinding(i,t)),l},this.getFrame=function(){return m},this.getSession=function(){return i},this.setSession=async function(j){if(i=j,i!==null){if(R=e.getRenderTarget(),i.addEventListener("select",V),i.addEventListener("selectstart",V),i.addEventListener("selectend",V),i.addEventListener("squeeze",V),i.addEventListener("squeezestart",V),i.addEventListener("squeezeend",V),i.addEventListener("end",Z),i.addEventListener("inputsourceschange",G),p.xrCompatible!==!0&&await t.makeXRCompatible(),C=e.getPixelRatio(),e.getSize(I),g&&"createProjectionLayer"in XRWebGLBinding.prototype){let oe=null,ne=null,z=null;p.depth&&(z=p.stencil?t.DEPTH24_STENCIL8:t.DEPTH_COMPONENT24,oe=p.stencil?pn:hn,ne=p.stencil?dn:si);let ae={colorFormat:t.RGBA8,depthFormat:z,scaleFactor:n};l=this.getBinding(),d=l.createProjectionLayer(ae),i.updateRenderState({layers:[d]}),e.setPixelRatio(1),e.setSize(d.textureWidth,d.textureHeight,!1),y=new li(d.textureWidth,d.textureHeight,{format:qt,type:lr,depthTexture:new dd(d.textureWidth,d.textureHeight,ne,void 0,void 0,void 0,void 0,void 0,void 0,oe),stencilBuffer:p.stencil,colorSpace:e.outputColorSpace,samples:p.antialias?4:0,resolveDepthBuffer:d.ignoreDepthValues===!1,resolveStencilBuffer:d.ignoreDepthValues===!1})}else{let oe={antialias:p.antialias,alpha:!0,depth:p.depth,stencil:p.stencil,framebufferScaleFactor:n};h=new XRWebGLLayer(i,t,oe),i.updateRenderState({baseLayer:h}),e.setPixelRatio(1),e.setSize(h.framebufferWidth,h.framebufferHeight,!1),y=new li(h.framebufferWidth,h.framebufferHeight,{format:qt,type:lr,colorSpace:e.outputColorSpace,stencilBuffer:p.stencil,resolveDepthBuffer:h.ignoreDepthValues===!1,resolveStencilBuffer:h.ignoreDepthValues===!1})}y.isXRRenderTarget=!0,this.setFoveation(s),c=null,a=await i.requestReferenceSpace(o),We.setContext(i),We.start(),r.isPresenting=!0,r.dispatchEvent({type:"sessionstart"})}},this.getEnvironmentBlendMode=function(){if(i!==null)return i.environmentBlendMode},this.getDepthTexture=function(){return _.getDepthTexture()};function G(j){for(let oe=0;oe<j.removed.length;oe++){let ne=j.removed[oe],z=O.indexOf(ne);z>=0&&(O[z]=null,A[z].disconnect(ne))}for(let oe=0;oe<j.added.length;oe++){let ne=j.added[oe],z=O.indexOf(ne);if(z===-1){for(let $=0;$<A.length;$++)if($>=O.length){O.push(ne),z=$;break}else if(O[$]===null){O[$]=ne,z=$;break}if(z===-1)break}let ae=A[z];ae&&ae.connect(ne)}}let ee=new F,W=new F;function ie(j,oe,ne){ee.setFromMatrixPosition(oe.matrixWorld),W.setFromMatrixPosition(ne.matrixWorld);let z=ee.distanceTo(W),ae=oe.projectionMatrix.elements,$=ne.projectionMatrix.elements,ge=ae[14]/(ae[10]-1),T=ae[14]/(ae[10]+1),Se=(ae[9]+1)/ae[5],Ee=(ae[9]-1)/ae[5],Ve=(ae[8]-1)/ae[0],fe=($[8]+1)/$[0],Ze=ge*Ve,Re=ge*fe,Ce=z/(-Ve+fe),mt=Ce*-Ve;if(oe.matrixWorld.decompose(j.position,j.quaternion,j.scale),j.translateX(mt),j.translateZ(Ce),j.matrixWorld.compose(j.position,j.quaternion,j.scale),j.matrixWorldInverse.copy(j.matrixWorld).invert(),ae[10]===-1)j.projectionMatrix.copy(oe.projectionMatrix),j.projectionMatrixInverse.copy(oe.projectionMatrixInverse);else{let dt=ge+Ce,at=T+Ce,E=Ze-mt,v=Re+(z-mt),L=Se*T/at*dt,Y=Ee*T/at*dt;j.projectionMatrix.makePerspective(E,v,L,Y,dt,at),j.projectionMatrixInverse.copy(j.projectionMatrix).invert()}}function ce(j,oe){oe===null?j.matrixWorld.copy(j.matrix):j.matrixWorld.multiplyMatrices(oe.matrixWorld,j.matrix),j.matrixWorldInverse.copy(j.matrixWorld).invert()}this.updateCamera=function(j){if(i===null)return;let oe=j.near,ne=j.far;_.texture!==null&&(_.depthNear>0&&(oe=_.depthNear),_.depthFar>0&&(ne=_.depthFar)),M.near=S.near=U.near=oe,M.far=S.far=U.far=ne,(k!==M.near||H!==M.far)&&(i.updateRenderState({depthNear:M.near,depthFar:M.far}),k=M.near,H=M.far),M.layers.mask=j.layers.mask|6,U.layers.mask=M.layers.mask&3,S.layers.mask=M.layers.mask&5;let z=j.parent,ae=M.cameras;ce(M,z);for(let $=0;$<ae.length;$++)ce(ae[$],z);ae.length===2?ie(M,U,S):M.projectionMatrix.copy(U.projectionMatrix),Pe(j,M,z)};function Pe(j,oe,ne){ne===null?j.matrix.copy(oe.matrixWorld):(j.matrix.copy(ne.matrixWorld),j.matrix.invert(),j.matrix.multiply(oe.matrixWorld)),j.matrix.decompose(j.position,j.quaternion,j.scale),j.updateMatrixWorld(!0),j.projectionMatrix.copy(oe.projectionMatrix),j.projectionMatrixInverse.copy(oe.projectionMatrixInverse),j.isPerspectiveCamera&&(j.fov=Xs*2*Math.atan(1/j.projectionMatrix.elements[5]),j.zoom=1)}this.getCamera=function(){return M},this.getFoveation=function(){if(!(d===null&&h===null))return s},this.setFoveation=function(j){s=j,d!==null&&(d.fixedFoveation=j),h!==null&&h.fixedFoveation!==void 0&&(h.fixedFoveation=j)},this.hasDepthSensing=function(){return _.texture!==null},this.getDepthSensingMesh=function(){return _.getMesh(M)},this.getCameraTexture=function(j){return f[j]};let Fe=null;function $e(j,oe){if(u=oe.getViewerPose(c||a),m=oe,u!==null){let ne=u.views;h!==null&&(e.setRenderTargetFramebuffer(y,h.framebuffer),e.setRenderTarget(y));let z=!1;ne.length!==M.cameras.length&&(M.cameras.length=0,z=!0);for(let $=0;$<ne.length;$++){let ge=ne[$],T=null;if(h!==null)T=h.getViewport(ge);else{let Ee=l.getViewSubImage(d,ge);T=Ee.viewport,$===0&&(e.setRenderTargetTextures(y,Ee.colorTexture,Ee.depthStencilTexture),e.setRenderTarget(y))}let Se=x[$];Se===void 0&&(Se=new Xt,Se.layers.enable($),Se.viewport=new lt,x[$]=Se),Se.matrix.fromArray(ge.transform.matrix),Se.matrix.decompose(Se.position,Se.quaternion,Se.scale),Se.projectionMatrix.fromArray(ge.projectionMatrix),Se.projectionMatrixInverse.copy(Se.projectionMatrix).invert(),Se.viewport.set(T.x,T.y,T.width,T.height),$===0&&(M.matrix.copy(Se.matrix),M.matrix.decompose(M.position,M.quaternion,M.scale)),z===!0&&M.cameras.push(Se)}let ae=i.enabledFeatures;if(ae&&ae.includes("depth-sensing")&&i.depthUsage=="gpu-optimized"&&g){l=r.getBinding();let $=l.getDepthInformation(ne[0]);$&&$.isValid&&$.texture&&_.init($,i.renderState)}if(ae&&ae.includes("camera-access")&&g){e.state.unbindTexture(),l=r.getBinding();for(let $=0;$<ne.length;$++){let ge=ne[$].camera;if(ge){let T=f[ge];T||(T=new hd,f[ge]=T);let Se=l.getCameraImage(ge);T.sourceTexture=Se}}}}for(let ne=0;ne<A.length;ne++){let z=O[ne],ae=A[ne];z!==null&&ae!==void 0&&ae.update(z,oe,c||a)}Fe&&Fe(j,oe),oe.detectedPlanes&&r.dispatchEvent({type:"planesdetected",data:oe}),m=null}let We=new xd;We.setAnimationLoop($e),this.setAnimationLoop=function(j){Fe=j},this.dispose=function(){}}},Qr=new zr,Y0=new pt;function K0(e,t){function r(f,p){f.matrixAutoUpdate===!0&&f.updateMatrix(),p.value.copy(f.matrix)}function i(f,p){p.color.getRGB(f.fogColor.value,sd(e)),p.isFog?(f.fogNear.value=p.near,f.fogFar.value=p.far):p.isFogExp2&&(f.fogDensity.value=p.density)}function n(f,p,R,y,A){p.isMeshBasicMaterial||p.isMeshLambertMaterial?a(f,p):p.isMeshToonMaterial?(a(f,p),d(f,p)):p.isMeshPhongMaterial?(a(f,p),l(f,p)):p.isMeshStandardMaterial?(a(f,p),h(f,p),p.isMeshPhysicalMaterial&&m(f,p,A)):p.isMeshMatcapMaterial?(a(f,p),g(f,p)):p.isMeshDepthMaterial?a(f,p):p.isMeshDistanceMaterial?(a(f,p),_(f,p)):p.isMeshNormalMaterial?a(f,p):p.isLineBasicMaterial?(o(f,p),p.isLineDashedMaterial&&s(f,p)):p.isPointsMaterial?c(f,p,R,y):p.isSpriteMaterial?u(f,p):p.isShadowMaterial?(f.color.value.copy(p.color),f.opacity.value=p.opacity):p.isShaderMaterial&&(p.uniformsNeedUpdate=!1)}function a(f,p){f.opacity.value=p.opacity,p.color&&f.diffuse.value.copy(p.color),p.emissive&&f.emissive.value.copy(p.emissive).multiplyScalar(p.emissiveIntensity),p.map&&(f.map.value=p.map,r(p.map,f.mapTransform)),p.alphaMap&&(f.alphaMap.value=p.alphaMap,r(p.alphaMap,f.alphaMapTransform)),p.bumpMap&&(f.bumpMap.value=p.bumpMap,r(p.bumpMap,f.bumpMapTransform),f.bumpScale.value=p.bumpScale,p.side===Rt&&(f.bumpScale.value*=-1)),p.normalMap&&(f.normalMap.value=p.normalMap,r(p.normalMap,f.normalMapTransform),f.normalScale.value.copy(p.normalScale),p.side===Rt&&f.normalScale.value.negate()),p.displacementMap&&(f.displacementMap.value=p.displacementMap,r(p.displacementMap,f.displacementMapTransform),f.displacementScale.value=p.displacementScale,f.displacementBias.value=p.displacementBias),p.emissiveMap&&(f.emissiveMap.value=p.emissiveMap,r(p.emissiveMap,f.emissiveMapTransform)),p.specularMap&&(f.specularMap.value=p.specularMap,r(p.specularMap,f.specularMapTransform)),p.alphaTest>0&&(f.alphaTest.value=p.alphaTest);let R=t.get(p),y=R.envMap,A=R.envMapRotation;y&&(f.envMap.value=y,Qr.copy(A),Qr.x*=-1,Qr.y*=-1,Qr.z*=-1,y.isCubeTexture&&y.isRenderTargetTexture===!1&&(Qr.y*=-1,Qr.z*=-1),f.envMapRotation.value.setFromMatrix4(Y0.makeRotationFromEuler(Qr)),f.flipEnvMap.value=y.isCubeTexture&&y.isRenderTargetTexture===!1?-1:1,f.reflectivity.value=p.reflectivity,f.ior.value=p.ior,f.refractionRatio.value=p.refractionRatio),p.lightMap&&(f.lightMap.value=p.lightMap,f.lightMapIntensity.value=p.lightMapIntensity,r(p.lightMap,f.lightMapTransform)),p.aoMap&&(f.aoMap.value=p.aoMap,f.aoMapIntensity.value=p.aoMapIntensity,r(p.aoMap,f.aoMapTransform))}function o(f,p){f.diffuse.value.copy(p.color),f.opacity.value=p.opacity,p.map&&(f.map.value=p.map,r(p.map,f.mapTransform))}function s(f,p){f.dashSize.value=p.dashSize,f.totalSize.value=p.dashSize+p.gapSize,f.scale.value=p.scale}function c(f,p,R,y){f.diffuse.value.copy(p.color),f.opacity.value=p.opacity,f.size.value=p.size*R,f.scale.value=y*.5,p.map&&(f.map.value=p.map,r(p.map,f.uvTransform)),p.alphaMap&&(f.alphaMap.value=p.alphaMap,r(p.alphaMap,f.alphaMapTransform)),p.alphaTest>0&&(f.alphaTest.value=p.alphaTest)}function u(f,p){f.diffuse.value.copy(p.color),f.opacity.value=p.opacity,f.rotation.value=p.rotation,p.map&&(f.map.value=p.map,r(p.map,f.mapTransform)),p.alphaMap&&(f.alphaMap.value=p.alphaMap,r(p.alphaMap,f.alphaMapTransform)),p.alphaTest>0&&(f.alphaTest.value=p.alphaTest)}function l(f,p){f.specular.value.copy(p.specular),f.shininess.value=Math.max(p.shininess,1e-4)}function d(f,p){p.gradientMap&&(f.gradientMap.value=p.gradientMap)}function h(f,p){f.metalness.value=p.metalness,p.metalnessMap&&(f.metalnessMap.value=p.metalnessMap,r(p.metalnessMap,f.metalnessMapTransform)),f.roughness.value=p.roughness,p.roughnessMap&&(f.roughnessMap.value=p.roughnessMap,r(p.roughnessMap,f.roughnessMapTransform)),p.envMap&&(f.envMapIntensity.value=p.envMapIntensity)}function m(f,p,R){f.ior.value=p.ior,p.sheen>0&&(f.sheenColor.value.copy(p.sheenColor).multiplyScalar(p.sheen),f.sheenRoughness.value=p.sheenRoughness,p.sheenColorMap&&(f.sheenColorMap.value=p.sheenColorMap,r(p.sheenColorMap,f.sheenColorMapTransform)),p.sheenRoughnessMap&&(f.sheenRoughnessMap.value=p.sheenRoughnessMap,r(p.sheenRoughnessMap,f.sheenRoughnessMapTransform))),p.clearcoat>0&&(f.clearcoat.value=p.clearcoat,f.clearcoatRoughness.value=p.clearcoatRoughness,p.clearcoatMap&&(f.clearcoatMap.value=p.clearcoatMap,r(p.clearcoatMap,f.clearcoatMapTransform)),p.clearcoatRoughnessMap&&(f.clearcoatRoughnessMap.value=p.clearcoatRoughnessMap,r(p.clearcoatRoughnessMap,f.clearcoatRoughnessMapTransform)),p.clearcoatNormalMap&&(f.clearcoatNormalMap.value=p.clearcoatNormalMap,r(p.clearcoatNormalMap,f.clearcoatNormalMapTransform),f.clearcoatNormalScale.value.copy(p.clearcoatNormalScale),p.side===Rt&&f.clearcoatNormalScale.value.negate())),p.dispersion>0&&(f.dispersion.value=p.dispersion),p.iridescence>0&&(f.iridescence.value=p.iridescence,f.iridescenceIOR.value=p.iridescenceIOR,f.iridescenceThicknessMinimum.value=p.iridescenceThicknessRange[0],f.iridescenceThicknessMaximum.value=p.iridescenceThicknessRange[1],p.iridescenceMap&&(f.iridescenceMap.value=p.iridescenceMap,r(p.iridescenceMap,f.iridescenceMapTransform)),p.iridescenceThicknessMap&&(f.iridescenceThicknessMap.value=p.iridescenceThicknessMap,r(p.iridescenceThicknessMap,f.iridescenceThicknessMapTransform))),p.transmission>0&&(f.transmission.value=p.transmission,f.transmissionSamplerMap.value=R.texture,f.transmissionSamplerSize.value.set(R.width,R.height),p.transmissionMap&&(f.transmissionMap.value=p.transmissionMap,r(p.transmissionMap,f.transmissionMapTransform)),f.thickness.value=p.thickness,p.thicknessMap&&(f.thicknessMap.value=p.thicknessMap,r(p.thicknessMap,f.thicknessMapTransform)),f.attenuationDistance.value=p.attenuationDistance,f.attenuationColor.value.copy(p.attenuationColor)),p.anisotropy>0&&(f.anisotropyVector.value.set(p.anisotropy*Math.cos(p.anisotropyRotation),p.anisotropy*Math.sin(p.anisotropyRotation)),p.anisotropyMap&&(f.anisotropyMap.value=p.anisotropyMap,r(p.anisotropyMap,f.anisotropyMapTransform))),f.specularIntensity.value=p.specularIntensity,f.specularColor.value.copy(p.specularColor),p.specularColorMap&&(f.specularColorMap.value=p.specularColorMap,r(p.specularColorMap,f.specularColorMapTransform)),p.specularIntensityMap&&(f.specularIntensityMap.value=p.specularIntensityMap,r(p.specularIntensityMap,f.specularIntensityMapTransform))}function g(f,p){p.matcap&&(f.matcap.value=p.matcap)}function _(f,p){let R=t.get(p).light;f.referencePosition.value.setFromMatrixPosition(R.matrixWorld),f.nearDistance.value=R.shadow.camera.near,f.farDistance.value=R.shadow.camera.far}return{refreshFogUniforms:i,refreshMaterialUniforms:n}}function J0(e,t,r,i){let n={},a={},o=[],s=e.getParameter(e.MAX_UNIFORM_BUFFER_BINDINGS);function c(R,y){let A=y.program;i.uniformBlockBinding(R,A)}function u(R,y){let A=n[R.id];A===void 0&&(g(R),A=l(R),n[R.id]=A,R.addEventListener("dispose",f));let O=y.program;i.updateUBOMapping(R,O);let I=t.render.frame;a[R.id]!==I&&(h(R),a[R.id]=I)}function l(R){let y=d();R.__bindingPointIndex=y;let A=e.createBuffer(),O=R.__size,I=R.usage;return e.bindBuffer(e.UNIFORM_BUFFER,A),e.bufferData(e.UNIFORM_BUFFER,O,I),e.bindBuffer(e.UNIFORM_BUFFER,null),e.bindBufferBase(e.UNIFORM_BUFFER,y,A),A}function d(){for(let R=0;R<s;R++)if(o.indexOf(R)===-1)return o.push(R),R;return console.error("THREE.WebGLRenderer: Maximum number of simultaneously usable uniforms groups reached."),0}function h(R){let y=n[R.id],A=R.uniforms,O=R.__cache;e.bindBuffer(e.UNIFORM_BUFFER,y);for(let I=0,C=A.length;I<C;I++){let U=Array.isArray(A[I])?A[I]:[A[I]];for(let S=0,x=U.length;S<x;S++){let M=U[S];if(m(M,I,S,O)===!0){let k=M.__offset,H=Array.isArray(M.value)?M.value:[M.value],V=0;for(let Z=0;Z<H.length;Z++){let G=H[Z],ee=_(G);typeof G=="number"||typeof G=="boolean"?(M.__data[0]=G,e.bufferSubData(e.UNIFORM_BUFFER,k+V,M.__data)):G.isMatrix3?(M.__data[0]=G.elements[0],M.__data[1]=G.elements[1],M.__data[2]=G.elements[2],M.__data[3]=0,M.__data[4]=G.elements[3],M.__data[5]=G.elements[4],M.__data[6]=G.elements[5],M.__data[7]=0,M.__data[8]=G.elements[6],M.__data[9]=G.elements[7],M.__data[10]=G.elements[8],M.__data[11]=0):(G.toArray(M.__data,V),V+=ee.storage/Float32Array.BYTES_PER_ELEMENT)}e.bufferSubData(e.UNIFORM_BUFFER,k,M.__data)}}}e.bindBuffer(e.UNIFORM_BUFFER,null)}function m(R,y,A,O){let I=R.value,C=y+"_"+A;if(O[C]===void 0)return typeof I=="number"||typeof I=="boolean"?O[C]=I:O[C]=I.clone(),!0;{let U=O[C];if(typeof I=="number"||typeof I=="boolean"){if(U!==I)return O[C]=I,!0}else if(U.equals(I)===!1)return U.copy(I),!0}return!1}function g(R){let y=R.uniforms,A=0,O=16;for(let C=0,U=y.length;C<U;C++){let S=Array.isArray(y[C])?y[C]:[y[C]];for(let x=0,M=S.length;x<M;x++){let k=S[x],H=Array.isArray(k.value)?k.value:[k.value];for(let V=0,Z=H.length;V<Z;V++){let G=H[V],ee=_(G),W=A%O,ie=W%ee.boundary,ce=W+ie;A+=ie,ce!==0&&O-ce<ee.storage&&(A+=O-ce),k.__data=new Float32Array(ee.storage/Float32Array.BYTES_PER_ELEMENT),k.__offset=A,A+=ee.storage}}}let I=A%O;return I>0&&(A+=O-I),R.__size=A,R.__cache={},this}function _(R){let y={boundary:0,storage:0};return typeof R=="number"||typeof R=="boolean"?(y.boundary=4,y.storage=4):R.isVector2?(y.boundary=8,y.storage=8):R.isVector3||R.isColor?(y.boundary=16,y.storage=12):R.isVector4?(y.boundary=16,y.storage=16):R.isMatrix3?(y.boundary=48,y.storage=48):R.isMatrix4?(y.boundary=64,y.storage=64):R.isTexture?console.warn("THREE.WebGLRenderer: Texture samplers can not be part of an uniforms group."):console.warn("THREE.WebGLRenderer: Unsupported uniform value type.",R),y}function f(R){let y=R.target;y.removeEventListener("dispose",f);let A=o.indexOf(y.__bindingPointIndex);o.splice(A,1),e.deleteBuffer(n[y.id]),delete n[y.id],delete a[y.id]}function p(){for(let R in n)e.deleteBuffer(n[R]);o=[],n={},a={}}return{bind:c,update:u,dispose:p}}var Md=class{constructor(e={}){let{canvas:t=ff(),context:r=null,depth:i=!0,stencil:n=!1,alpha:a=!1,antialias:o=!1,premultipliedAlpha:s=!0,preserveDrawingBuffer:c=!1,powerPreference:u="default",failIfMajorPerformanceCaveat:l=!1,reversedDepthBuffer:d=!1}=e;this.isWebGLRenderer=!0;let h;if(r!==null){if(typeof WebGLRenderingContext<"u"&&r instanceof WebGLRenderingContext)throw new Error("THREE.WebGLRenderer: WebGL 1 is not supported since r163.");h=r.getContextAttributes().alpha}else h=a;let m=new Uint32Array(4),g=new Int32Array(4),_=null,f=null,p=[],R=[];this.domElement=t,this.debug={checkShaderErrors:!0,onShaderError:null},this.autoClear=!0,this.autoClearColor=!0,this.autoClearDepth=!0,this.autoClearStencil=!0,this.sortObjects=!0,this.clippingPlanes=[],this.localClippingEnabled=!1,this.toneMapping=Br,this.toneMappingExposure=1,this.transmissionResolutionScale=1;let y=this,A=!1;this._outputColorSpace=Ft;let O=0,I=0,C=null,U=-1,S=null,x=new lt,M=new lt,k=null,H=new qe(0),V=0,Z=t.width,G=t.height,ee=1,W=null,ie=null,ce=new lt(0,0,Z,G),Pe=new lt(0,0,Z,G),Fe=!1,$e=new il,We=!1,j=!1,oe=new pt,ne=new F,z=new lt,ae={background:null,fog:null,environment:null,overrideMaterial:null,isScene:!0},$=!1;function ge(){return C===null?ee:1}let T=r;function Se(b,P){return t.getContext(b,P)}try{let b={alpha:!0,depth:i,stencil:n,antialias:o,premultipliedAlpha:s,preserveDrawingBuffer:c,powerPreference:u,failIfMajorPerformanceCaveat:l};if("setAttribute"in t&&t.setAttribute("data-engine","three.js r180"),t.addEventListener("webglcontextlost",he,!1),t.addEventListener("webglcontextrestored",le,!1),t.addEventListener("webglcontextcreationerror",ye,!1),T===null){let P="webgl2";if(T=Se(P,b),T===null)throw Se(P)?new Error("Error creating WebGL context with your selected attributes."):new Error("Error creating WebGL context.")}}catch(b){throw console.error("THREE.WebGLRenderer: "+b.message),b}let Ee,Ve,fe,Ze,Re,Ce,mt,dt,at,E,v,L,Y,J,X,be,se,Te,Ae,re,de,Ne,we,pe;function ze(){Ee=new s_(T),Ee.init(),Ne=new G0(T,Ee),Ve=new e_(T,Ee,e,Ne),fe=new z0(T,Ee),Ve.reversedDepthBuffer&&d&&fe.buffers.depth.setReversed(!0),Ze=new u_(T),Re=new R0,Ce=new H0(T,Ee,fe,Re,Ve,Ne,Ze),mt=new r_(y),dt=new o_(y),at=new gm(T),we=new $v(T,at),E=new l_(T,at,Ze,we),v=new h_(T,E,at,Ze),Ae=new d_(T,Ve,Ce),be=new t_(Re),L=new w0(y,mt,dt,Ee,Ve,we,be),Y=new K0(y,Re),J=new I0,X=new D0(Ee),Te=new Zv(y,mt,dt,fe,v,h,s),se=new B0(y,v,Ve),pe=new J0(T,Ze,Ve,fe),re=new Qv(T,Ee,Ze),de=new c_(T,Ee,Ze),Ze.programs=L.programs,y.capabilities=Ve,y.extensions=Ee,y.properties=Re,y.renderLists=J,y.shadowMap=se,y.state=fe,y.info=Ze}ze();let w=new q0(y,T);this.xr=w,this.getContext=function(){return T},this.getContextAttributes=function(){return T.getContextAttributes()},this.forceContextLoss=function(){let b=Ee.get("WEBGL_lose_context");b&&b.loseContext()},this.forceContextRestore=function(){let b=Ee.get("WEBGL_lose_context");b&&b.restoreContext()},this.getPixelRatio=function(){return ee},this.setPixelRatio=function(b){b!==void 0&&(ee=b,this.setSize(Z,G,!1))},this.getSize=function(b){return b.set(Z,G)},this.setSize=function(b,P,D=!0){if(w.isPresenting){console.warn("THREE.WebGLRenderer: Can't change size while VR device is presenting.");return}Z=b,G=P,t.width=Math.floor(b*ee),t.height=Math.floor(P*ee),D===!0&&(t.style.width=b+"px",t.style.height=P+"px"),this.setViewport(0,0,b,P)},this.getDrawingBufferSize=function(b){return b.set(Z*ee,G*ee).floor()},this.setDrawingBufferSize=function(b,P,D){Z=b,G=P,ee=D,t.width=Math.floor(b*D),t.height=Math.floor(P*D),this.setViewport(0,0,b,P)},this.getCurrentViewport=function(b){return b.copy(x)},this.getViewport=function(b){return b.copy(ce)},this.setViewport=function(b,P,D,B){b.isVector4?ce.set(b.x,b.y,b.z,b.w):ce.set(b,P,D,B),fe.viewport(x.copy(ce).multiplyScalar(ee).round())},this.getScissor=function(b){return b.copy(Pe)},this.setScissor=function(b,P,D,B){b.isVector4?Pe.set(b.x,b.y,b.z,b.w):Pe.set(b,P,D,B),fe.scissor(M.copy(Pe).multiplyScalar(ee).round())},this.getScissorTest=function(){return Fe},this.setScissorTest=function(b){fe.setScissorTest(Fe=b)},this.setOpaqueSort=function(b){W=b},this.setTransparentSort=function(b){ie=b},this.getClearColor=function(b){return b.copy(Te.getClearColor())},this.setClearColor=function(){Te.setClearColor(...arguments)},this.getClearAlpha=function(){return Te.getClearAlpha()},this.setClearAlpha=function(){Te.setClearAlpha(...arguments)},this.clear=function(b=!0,P=!0,D=!0){let B=0;if(b){let N=!1;if(C!==null){let Q=C.texture.format;N=Q===el||Q===Qs||Q===$s}if(N){let Q=C.texture.type,me=Q===lr||Q===si||Q===un||Q===dn||Q===Js||Q===Zs,ve=Te.getClearColor(),_e=Te.getClearAlpha(),Oe=ve.r,De=ve.g,Le=ve.b;me?(m[0]=Oe,m[1]=De,m[2]=Le,m[3]=_e,T.clearBufferuiv(T.COLOR,0,m)):(g[0]=Oe,g[1]=De,g[2]=Le,g[3]=_e,T.clearBufferiv(T.COLOR,0,g))}else B|=T.COLOR_BUFFER_BIT}P&&(B|=T.DEPTH_BUFFER_BIT),D&&(B|=T.STENCIL_BUFFER_BIT,this.state.buffers.stencil.setMask(4294967295)),T.clear(B)},this.clearColor=function(){this.clear(!0,!1,!1)},this.clearDepth=function(){this.clear(!1,!0,!1)},this.clearStencil=function(){this.clear(!1,!1,!0)},this.dispose=function(){t.removeEventListener("webglcontextlost",he,!1),t.removeEventListener("webglcontextrestored",le,!1),t.removeEventListener("webglcontextcreationerror",ye,!1),Te.dispose(),J.dispose(),X.dispose(),Re.dispose(),mt.dispose(),dt.dispose(),v.dispose(),we.dispose(),pe.dispose(),L.dispose(),w.dispose(),w.removeEventListener("sessionstart",$t),w.removeEventListener("sessionend",Qt),Gr.stop()};function he(b){b.preventDefault(),console.log("THREE.WebGLRenderer: Context Lost."),A=!0}function le(){console.log("THREE.WebGLRenderer: Context Restored."),A=!1;let b=Ze.autoReset,P=se.enabled,D=se.autoUpdate,B=se.needsUpdate,N=se.type;ze(),Ze.autoReset=b,se.enabled=P,se.autoUpdate=D,se.needsUpdate=B,se.type=N}function ye(b){console.error("THREE.WebGLRenderer: A WebGL context could not be created. Reason: ",b.statusMessage)}function te(b){let P=b.target;P.removeEventListener("dispose",te),K(P)}function K(b){xe(b),Re.remove(b)}function xe(b){let P=Re.get(b).programs;P!==void 0&&(P.forEach(function(D){L.releaseProgram(D)}),b.isShaderMaterial&&L.releaseShaderCache(b))}this.renderBufferDirect=function(b,P,D,B,N,Q){P===null&&(P=ae);let me=N.isMesh&&N.matrixWorld.determinant()<0,ve=Yd(b,P,D,B,N);fe.setMaterial(B,me);let _e=D.index,Oe=1;if(B.wireframe===!0){if(_e=E.getWireframeAttribute(D),_e===void 0)return;Oe=2}let De=D.drawRange,Le=D.attributes.position,je=De.start*Oe,Qe=(De.start+De.count)*Oe;Q!==null&&(je=Math.max(je,Q.start*Oe),Qe=Math.min(Qe,(Q.start+Q.count)*Oe)),_e!==null?(je=Math.max(je,0),Qe=Math.min(Qe,_e.count)):Le!=null&&(je=Math.max(je,0),Qe=Math.min(Qe,Le.count));let tt=Qe-je;if(tt<0||tt===1/0)return;we.setup(N,B,ve,D,_e);let rt,et=re;if(_e!==null&&(rt=at.get(_e),et=de,et.setIndex(rt)),N.isMesh)B.wireframe===!0?(fe.setLineWidth(B.wireframeLinewidth*ge()),et.setMode(T.LINES)):et.setMode(T.TRIANGLES);else if(N.isLine){let Me=B.linewidth;Me===void 0&&(Me=1),fe.setLineWidth(Me*ge()),N.isLineSegments?et.setMode(T.LINES):N.isLineLoop?et.setMode(T.LINE_LOOP):et.setMode(T.LINE_STRIP)}else N.isPoints?et.setMode(T.POINTS):N.isSprite&&et.setMode(T.TRIANGLES);if(N.isBatchedMesh)if(N._multiDrawInstances!==null)fn("THREE.WebGLRenderer: renderMultiDrawInstances has been deprecated and will be removed in r184. Append to renderMultiDraw arguments and use indirection."),et.renderMultiDrawInstances(N._multiDrawStarts,N._multiDrawCounts,N._multiDrawCount,N._multiDrawInstances);else if(Ee.get("WEBGL_multi_draw"))et.renderMultiDraw(N._multiDrawStarts,N._multiDrawCounts,N._multiDrawCount);else{let Me=N._multiDrawStarts,gt=N._multiDrawCounts,pr=N._multiDrawCount,zt=_e?at.get(_e).bytesPerElement:1,fi=Re.get(B).currentProgram.getUniforms();for(let Ct=0;Ct<pr;Ct++)fi.setValue(T,"_gl_DrawID",Ct),et.render(Me[Ct]/zt,gt[Ct])}else if(N.isInstancedMesh)et.renderInstances(je,tt,N.count);else if(D.isInstancedBufferGeometry){let Me=D._maxInstanceCount!==void 0?D._maxInstanceCount:1/0,gt=Math.min(D.instanceCount,Me);et.renderInstances(je,tt,gt)}else et.render(je,tt)};function Ie(b,P,D){b.transparent===!0&&b.side===Tr&&b.forceSinglePass===!1?(b.side=Rt,b.needsUpdate=!0,An(b,P,D),b.side=Vr,b.needsUpdate=!0,An(b,P,D),b.side=Tr):An(b,P,D)}this.compile=function(b,P,D=null){D===null&&(D=b),f=X.get(D),f.init(P),R.push(f),D.traverseVisible(function(N){N.isLight&&N.layers.test(P.layers)&&(f.pushLight(N),N.castShadow&&f.pushShadow(N))}),b!==D&&b.traverseVisible(function(N){N.isLight&&N.layers.test(P.layers)&&(f.pushLight(N),N.castShadow&&f.pushShadow(N))}),f.setupLights();let B=new Set;return b.traverse(function(N){if(!(N.isMesh||N.isPoints||N.isLine||N.isSprite))return;let Q=N.material;if(Q)if(Array.isArray(Q))for(let me=0;me<Q.length;me++){let ve=Q[me];Ie(ve,D,N),B.add(ve)}else Ie(Q,D,N),B.add(Q)}),f=R.pop(),B},this.compileAsync=function(b,P,D=null){let B=this.compile(b,P,D);return new Promise(N=>{function Q(){if(B.forEach(function(me){Re.get(me).currentProgram.isReady()&&B.delete(me)}),B.size===0){N(b);return}setTimeout(Q,10)}Ee.get("KHR_parallel_shader_compile")!==null?Q():setTimeout(Q,10)})};let ot=null;function Ke(b){ot&&ot(b)}function $t(){Gr.stop()}function Qt(){Gr.start()}let Gr=new xd;Gr.setAnimationLoop(Ke),typeof self<"u"&&Gr.setContext(self),this.setAnimationLoop=function(b){ot=b,w.setAnimationLoop(b),b===null?Gr.stop():Gr.start()},w.addEventListener("sessionstart",$t),w.addEventListener("sessionend",Qt),this.render=function(b,P){if(P!==void 0&&P.isCamera!==!0){console.error("THREE.WebGLRenderer.render: camera is not an instance of THREE.Camera.");return}if(A===!0)return;if(b.matrixWorldAutoUpdate===!0&&b.updateMatrixWorld(),P.parent===null&&P.matrixWorldAutoUpdate===!0&&P.updateMatrixWorld(),w.enabled===!0&&w.isPresenting===!0&&(w.cameraAutoUpdate===!0&&w.updateCamera(P),P=w.getCamera()),b.isScene===!0&&b.onBeforeRender(y,b,P,C),f=X.get(b,R.length),f.init(P),R.push(f),oe.multiplyMatrices(P.projectionMatrix,P.matrixWorldInverse),$e.setFromProjectionMatrix(oe,or,P.reversedDepth),j=this.localClippingEnabled,We=be.init(this.clippingPlanes,j),_=J.get(b,p.length),_.init(),p.push(_),w.enabled===!0&&w.isPresenting===!0){let Q=y.xr.getDepthSensingMesh();Q!==null&&Va(Q,P,-1/0,y.sortObjects)}Va(b,P,0,y.sortObjects),_.finish(),y.sortObjects===!0&&_.sort(W,ie),$=w.enabled===!1||w.isPresenting===!1||w.hasDepthSensing()===!1,$&&Te.addToRenderList(_,b),this.info.render.frame++,We===!0&&be.beginShadows();let D=f.state.shadowsArray;se.render(D,b,P),We===!0&&be.endShadows(),this.info.autoReset===!0&&this.info.reset();let B=_.opaque,N=_.transmissive;if(f.setupLights(),P.isArrayCamera){let Q=P.cameras;if(N.length>0)for(let me=0,ve=Q.length;me<ve;me++){let _e=Q[me];vl(B,N,b,_e)}$&&Te.render(b);for(let me=0,ve=Q.length;me<ve;me++){let _e=Q[me];gl(_,b,_e,_e.viewport)}}else N.length>0&&vl(B,N,b,P),$&&Te.render(b),gl(_,b,P);C!==null&&I===0&&(Ce.updateMultisampleRenderTarget(C),Ce.updateRenderTargetMipmap(C)),b.isScene===!0&&b.onAfterRender(y,b,P),we.resetDefaultState(),U=-1,S=null,R.pop(),R.length>0?(f=R[R.length-1],We===!0&&be.setGlobalState(y.clippingPlanes,f.state.camera)):f=null,p.pop(),p.length>0?_=p[p.length-1]:_=null};function Va(b,P,D,B){if(b.visible===!1)return;if(b.layers.test(P.layers)){if(b.isGroup)D=b.renderOrder;else if(b.isLOD)b.autoUpdate===!0&&b.update(P);else if(b.isLight)f.pushLight(b),b.castShadow&&f.pushShadow(b);else if(b.isSprite){if(!b.frustumCulled||$e.intersectsSprite(b)){B&&z.setFromMatrixPosition(b.matrixWorld).applyMatrix4(oe);let Q=v.update(b),me=b.material;me.visible&&_.push(b,Q,me,D,z.z,null)}}else if((b.isMesh||b.isLine||b.isPoints)&&(!b.frustumCulled||$e.intersectsObject(b))){let Q=v.update(b),me=b.material;if(B&&(b.boundingSphere!==void 0?(b.boundingSphere===null&&b.computeBoundingSphere(),z.copy(b.boundingSphere.center)):(Q.boundingSphere===null&&Q.computeBoundingSphere(),z.copy(Q.boundingSphere.center)),z.applyMatrix4(b.matrixWorld).applyMatrix4(oe)),Array.isArray(me)){let ve=Q.groups;for(let _e=0,Oe=ve.length;_e<Oe;_e++){let De=ve[_e],Le=me[De.materialIndex];Le&&Le.visible&&_.push(b,Q,Le,D,z.z,De)}}else me.visible&&_.push(b,Q,me,D,z.z,null)}}let N=b.children;for(let Q=0,me=N.length;Q<me;Q++)Va(N[Q],P,D,B)}function gl(b,P,D,B){let N=b.opaque,Q=b.transmissive,me=b.transparent;f.setupLightsView(D),We===!0&&be.setGlobalState(y.clippingPlanes,D),B&&fe.viewport(x.copy(B)),N.length>0&&Mn(N,P,D),Q.length>0&&Mn(Q,P,D),me.length>0&&Mn(me,P,D),fe.buffers.depth.setTest(!0),fe.buffers.depth.setMask(!0),fe.buffers.color.setMask(!0),fe.setPolygonOffset(!1)}function vl(b,P,D,B){if((D.isScene===!0?D.overrideMaterial:null)!==null)return;f.state.transmissionRenderTarget[B.id]===void 0&&(f.state.transmissionRenderTarget[B.id]=new li(1,1,{generateMipmaps:!0,type:Ee.has("EXT_color_buffer_half_float")||Ee.has("EXT_color_buffer_float")?mn:lr,minFilter:ai,samples:4,stencilBuffer:n,resolveDepthBuffer:!1,resolveStencilBuffer:!1,colorSpace:Xe.workingColorSpace}));let N=f.state.transmissionRenderTarget[B.id],Q=B.viewport||x;N.setSize(Q.z*y.transmissionResolutionScale,Q.w*y.transmissionResolutionScale);let me=y.getRenderTarget(),ve=y.getActiveCubeFace(),_e=y.getActiveMipmapLevel();y.setRenderTarget(N),y.getClearColor(H),V=y.getClearAlpha(),V<1&&y.setClearColor(16777215,.5),y.clear(),$&&Te.render(D);let Oe=y.toneMapping;y.toneMapping=Br;let De=B.viewport;if(B.viewport!==void 0&&(B.viewport=void 0),f.setupLightsView(B),We===!0&&be.setGlobalState(y.clippingPlanes,B),Mn(b,D,B),Ce.updateMultisampleRenderTarget(N),Ce.updateRenderTargetMipmap(N),Ee.has("WEBGL_multisampled_render_to_texture")===!1){let Le=!1;for(let je=0,Qe=P.length;je<Qe;je++){let tt=P[je],rt=tt.object,et=tt.geometry,Me=tt.material,gt=tt.group;if(Me.side===Tr&&rt.layers.test(B.layers)){let pr=Me.side;Me.side=Rt,Me.needsUpdate=!0,_l(rt,D,B,et,Me,gt),Me.side=pr,Me.needsUpdate=!0,Le=!0}}Le===!0&&(Ce.updateMultisampleRenderTarget(N),Ce.updateRenderTargetMipmap(N))}y.setRenderTarget(me,ve,_e),y.setClearColor(H,V),De!==void 0&&(B.viewport=De),y.toneMapping=Oe}function Mn(b,P,D){let B=P.isScene===!0?P.overrideMaterial:null;for(let N=0,Q=b.length;N<Q;N++){let me=b[N],ve=me.object,_e=me.geometry,Oe=me.group,De=me.material;De.allowOverride===!0&&B!==null&&(De=B),ve.layers.test(D.layers)&&_l(ve,P,D,_e,De,Oe)}}function _l(b,P,D,B,N,Q){b.onBeforeRender(y,P,D,B,N,Q),b.modelViewMatrix.multiplyMatrices(D.matrixWorldInverse,b.matrixWorld),b.normalMatrix.getNormalMatrix(b.modelViewMatrix),N.onBeforeRender(y,P,D,B,b,Q),N.transparent===!0&&N.side===Tr&&N.forceSinglePass===!1?(N.side=Rt,N.needsUpdate=!0,y.renderBufferDirect(D,P,B,N,b,Q),N.side=Vr,N.needsUpdate=!0,y.renderBufferDirect(D,P,B,N,b,Q),N.side=Tr):y.renderBufferDirect(D,P,B,N,b,Q),b.onAfterRender(y,P,D,B,N,Q)}function An(b,P,D){P.isScene!==!0&&(P=ae);let B=Re.get(b),N=f.state.lights,Q=f.state.shadowsArray,me=N.state.version,ve=L.getParameters(b,N.state,Q,P,D),_e=L.getProgramCacheKey(ve),Oe=B.programs;B.environment=b.isMeshStandardMaterial?P.environment:null,B.fog=P.fog,B.envMap=(b.isMeshStandardMaterial?dt:mt).get(b.envMap||B.environment),B.envMapRotation=B.environment!==null&&b.envMap===null?P.environmentRotation:b.envMapRotation,Oe===void 0&&(b.addEventListener("dispose",te),Oe=new Map,B.programs=Oe);let De=Oe.get(_e);if(De!==void 0){if(B.currentProgram===De&&B.lightsStateVersion===me)return xl(b,ve),De}else ve.uniforms=L.getUniforms(b),b.onBeforeCompile(ve,y),De=L.acquireProgram(ve,_e),Oe.set(_e,De),B.uniforms=ve.uniforms;let Le=B.uniforms;return(!b.isShaderMaterial&&!b.isRawShaderMaterial||b.clipping===!0)&&(Le.clippingPlanes=be.uniform),xl(b,ve),B.needsLights=Jd(b),B.lightsStateVersion=me,B.needsLights&&(Le.ambientLightColor.value=N.state.ambient,Le.lightProbe.value=N.state.probe,Le.directionalLights.value=N.state.directional,Le.directionalLightShadows.value=N.state.directionalShadow,Le.spotLights.value=N.state.spot,Le.spotLightShadows.value=N.state.spotShadow,Le.rectAreaLights.value=N.state.rectArea,Le.ltc_1.value=N.state.rectAreaLTC1,Le.ltc_2.value=N.state.rectAreaLTC2,Le.pointLights.value=N.state.point,Le.pointLightShadows.value=N.state.pointShadow,Le.hemisphereLights.value=N.state.hemi,Le.directionalShadowMap.value=N.state.directionalShadowMap,Le.directionalShadowMatrix.value=N.state.directionalShadowMatrix,Le.spotShadowMap.value=N.state.spotShadowMap,Le.spotLightMatrix.value=N.state.spotLightMatrix,Le.spotLightMap.value=N.state.spotLightMap,Le.pointShadowMap.value=N.state.pointShadowMap,Le.pointShadowMatrix.value=N.state.pointShadowMatrix),B.currentProgram=De,B.uniformsList=null,De}function bl(b){if(b.uniformsList===null){let P=b.currentProgram.getUniforms();b.uniformsList=Aa.seqWithValue(P.seq,b.uniforms)}return b.uniformsList}function xl(b,P){let D=Re.get(b);D.outputColorSpace=P.outputColorSpace,D.batching=P.batching,D.batchingColor=P.batchingColor,D.instancing=P.instancing,D.instancingColor=P.instancingColor,D.instancingMorph=P.instancingMorph,D.skinning=P.skinning,D.morphTargets=P.morphTargets,D.morphNormals=P.morphNormals,D.morphColors=P.morphColors,D.morphTargetsCount=P.morphTargetsCount,D.numClippingPlanes=P.numClippingPlanes,D.numIntersection=P.numClipIntersection,D.vertexAlphas=P.vertexAlphas,D.vertexTangents=P.vertexTangents,D.toneMapping=P.toneMapping}function Yd(b,P,D,B,N){P.isScene!==!0&&(P=ae),Ce.resetTextureUnits();let Q=P.fog,me=B.isMeshStandardMaterial?P.environment:null,ve=C===null?y.outputColorSpace:C.isXRRenderTarget===!0?C.texture.colorSpace:Gi,_e=(B.isMeshStandardMaterial?dt:mt).get(B.envMap||me),Oe=B.vertexColors===!0&&!!D.attributes.color&&D.attributes.color.itemSize===4,De=!!D.attributes.tangent&&(!!B.normalMap||B.anisotropy>0),Le=!!D.morphAttributes.position,je=!!D.morphAttributes.normal,Qe=!!D.morphAttributes.color,tt=Br;B.toneMapped&&(C===null||C.isXRRenderTarget===!0)&&(tt=y.toneMapping);let rt=D.morphAttributes.position||D.morphAttributes.normal||D.morphAttributes.color,et=rt!==void 0?rt.length:0,Me=Re.get(B),gt=f.state.lights;if(We===!0&&(j===!0||b!==S)){let vt=b===S&&B.id===U;be.setState(B,b,vt)}let pr=!1;B.version===Me.__version?(Me.needsLights&&Me.lightsStateVersion!==gt.state.version||Me.outputColorSpace!==ve||N.isBatchedMesh&&Me.batching===!1||!N.isBatchedMesh&&Me.batching===!0||N.isBatchedMesh&&Me.batchingColor===!0&&N.colorTexture===null||N.isBatchedMesh&&Me.batchingColor===!1&&N.colorTexture!==null||N.isInstancedMesh&&Me.instancing===!1||!N.isInstancedMesh&&Me.instancing===!0||N.isSkinnedMesh&&Me.skinning===!1||!N.isSkinnedMesh&&Me.skinning===!0||N.isInstancedMesh&&Me.instancingColor===!0&&N.instanceColor===null||N.isInstancedMesh&&Me.instancingColor===!1&&N.instanceColor!==null||N.isInstancedMesh&&Me.instancingMorph===!0&&N.morphTexture===null||N.isInstancedMesh&&Me.instancingMorph===!1&&N.morphTexture!==null||Me.envMap!==_e||B.fog===!0&&Me.fog!==Q||Me.numClippingPlanes!==void 0&&(Me.numClippingPlanes!==be.numPlanes||Me.numIntersection!==be.numIntersection)||Me.vertexAlphas!==Oe||Me.vertexTangents!==De||Me.morphTargets!==Le||Me.morphNormals!==je||Me.morphColors!==Qe||Me.toneMapping!==tt||Me.morphTargetsCount!==et)&&(pr=!0):(pr=!0,Me.__version=B.version);let zt=Me.currentProgram;pr===!0&&(zt=An(B,P,N));let fi=!1,Ct=!1,Yi=!1,it=zt.getUniforms(),Lt=Me.uniforms;if(fe.useProgram(zt.program)&&(fi=!0,Ct=!0,Yi=!0),B.id!==U&&(U=B.id,Ct=!0),fi||S!==b){fe.buffers.depth.getReversed()&&b.reversedDepth!==!0&&(b._reversedDepth=!0,b.updateProjectionMatrix()),it.setValue(T,"projectionMatrix",b.projectionMatrix),it.setValue(T,"viewMatrix",b.matrixWorldInverse);let vt=it.map.cameraPosition;vt!==void 0&&vt.setValue(T,ne.setFromMatrixPosition(b.matrixWorld)),Ve.logarithmicDepthBuffer&&it.setValue(T,"logDepthBufFC",2/(Math.log(b.far+1)/Math.LN2)),(B.isMeshPhongMaterial||B.isMeshToonMaterial||B.isMeshLambertMaterial||B.isMeshBasicMaterial||B.isMeshStandardMaterial||B.isShaderMaterial)&&it.setValue(T,"isOrthographic",b.isOrthographicCamera===!0),S!==b&&(S=b,Ct=!0,Yi=!0)}if(N.isSkinnedMesh){it.setOptional(T,N,"bindMatrix"),it.setOptional(T,N,"bindMatrixInverse");let vt=N.skeleton;vt&&(vt.boneTexture===null&&vt.computeBoneTexture(),it.setValue(T,"boneTexture",vt.boneTexture,Ce))}N.isBatchedMesh&&(it.setOptional(T,N,"batchingTexture"),it.setValue(T,"batchingTexture",N._matricesTexture,Ce),it.setOptional(T,N,"batchingIdTexture"),it.setValue(T,"batchingIdTexture",N._indirectTexture,Ce),it.setOptional(T,N,"batchingColorTexture"),N._colorsTexture!==null&&it.setValue(T,"batchingColorTexture",N._colorsTexture,Ce));let Ut=D.morphAttributes;if((Ut.position!==void 0||Ut.normal!==void 0||Ut.color!==void 0)&&Ae.update(N,D,zt),(Ct||Me.receiveShadow!==N.receiveShadow)&&(Me.receiveShadow=N.receiveShadow,it.setValue(T,"receiveShadow",N.receiveShadow)),B.isMeshGouraudMaterial&&B.envMap!==null&&(Lt.envMap.value=_e,Lt.flipEnvMap.value=_e.isCubeTexture&&_e.isRenderTargetTexture===!1?-1:1),B.isMeshStandardMaterial&&B.envMap===null&&P.environment!==null&&(Lt.envMapIntensity.value=P.environmentIntensity),Ct&&(it.setValue(T,"toneMappingExposure",y.toneMappingExposure),Me.needsLights&&Kd(Lt,Yi),Q&&B.fog===!0&&Y.refreshFogUniforms(Lt,Q),Y.refreshMaterialUniforms(Lt,B,ee,G,f.state.transmissionRenderTarget[b.id]),Aa.upload(T,bl(Me),Lt,Ce)),B.isShaderMaterial&&B.uniformsNeedUpdate===!0&&(Aa.upload(T,bl(Me),Lt,Ce),B.uniformsNeedUpdate=!1),B.isSpriteMaterial&&it.setValue(T,"center",N.center),it.setValue(T,"modelViewMatrix",N.modelViewMatrix),it.setValue(T,"normalMatrix",N.normalMatrix),it.setValue(T,"modelMatrix",N.matrixWorld),B.isShaderMaterial||B.isRawShaderMaterial){let vt=B.uniformsGroups;for(let Ht=0,za=vt.length;Ht<za;Ht++){let Wr=vt[Ht];pe.update(Wr,zt),pe.bind(Wr,zt)}}return zt}function Kd(b,P){b.ambientLightColor.needsUpdate=P,b.lightProbe.needsUpdate=P,b.directionalLights.needsUpdate=P,b.directionalLightShadows.needsUpdate=P,b.pointLights.needsUpdate=P,b.pointLightShadows.needsUpdate=P,b.spotLights.needsUpdate=P,b.spotLightShadows.needsUpdate=P,b.rectAreaLights.needsUpdate=P,b.hemisphereLights.needsUpdate=P}function Jd(b){return b.isMeshLambertMaterial||b.isMeshToonMaterial||b.isMeshPhongMaterial||b.isMeshStandardMaterial||b.isShadowMaterial||b.isShaderMaterial&&b.lights===!0}this.getActiveCubeFace=function(){return O},this.getActiveMipmapLevel=function(){return I},this.getRenderTarget=function(){return C},this.setRenderTargetTextures=function(b,P,D){let B=Re.get(b);B.__autoAllocateDepthBuffer=b.resolveDepthBuffer===!1,B.__autoAllocateDepthBuffer===!1&&(B.__useRenderToTexture=!1),Re.get(b.texture).__webglTexture=P,Re.get(b.depthTexture).__webglTexture=B.__autoAllocateDepthBuffer?void 0:D,B.__hasExternalTextures=!0},this.setRenderTargetFramebuffer=function(b,P){let D=Re.get(b);D.__webglFramebuffer=P,D.__useDefaultFramebuffer=P===void 0};let Zd=T.createFramebuffer();this.setRenderTarget=function(b,P=0,D=0){C=b,O=P,I=D;let B=!0,N=null,Q=!1,me=!1;if(b){let ve=Re.get(b);if(ve.__useDefaultFramebuffer!==void 0)fe.bindFramebuffer(T.FRAMEBUFFER,null),B=!1;else if(ve.__webglFramebuffer===void 0)Ce.setupRenderTarget(b);else if(ve.__hasExternalTextures)Ce.rebindTextures(b,Re.get(b.texture).__webglTexture,Re.get(b.depthTexture).__webglTexture);else if(b.depthBuffer){let De=b.depthTexture;if(ve.__boundDepthTexture!==De){if(De!==null&&Re.has(De)&&(b.width!==De.image.width||b.height!==De.image.height))throw new Error("WebGLRenderTarget: Attached DepthTexture is initialized to the incorrect size.");Ce.setupDepthRenderbuffer(b)}}let _e=b.texture;(_e.isData3DTexture||_e.isDataArrayTexture||_e.isCompressedArrayTexture)&&(me=!0);let Oe=Re.get(b).__webglFramebuffer;b.isWebGLCubeRenderTarget?(Array.isArray(Oe[P])?N=Oe[P][D]:N=Oe[P],Q=!0):b.samples>0&&Ce.useMultisampledRTT(b)===!1?N=Re.get(b).__webglMultisampledFramebuffer:Array.isArray(Oe)?N=Oe[D]:N=Oe,x.copy(b.viewport),M.copy(b.scissor),k=b.scissorTest}else x.copy(ce).multiplyScalar(ee).floor(),M.copy(Pe).multiplyScalar(ee).floor(),k=Fe;if(D!==0&&(N=Zd),fe.bindFramebuffer(T.FRAMEBUFFER,N)&&B&&fe.drawBuffers(b,N),fe.viewport(x),fe.scissor(M),fe.setScissorTest(k),Q){let ve=Re.get(b.texture);T.framebufferTexture2D(T.FRAMEBUFFER,T.COLOR_ATTACHMENT0,T.TEXTURE_CUBE_MAP_POSITIVE_X+P,ve.__webglTexture,D)}else if(me){let ve=P;for(let _e=0;_e<b.textures.length;_e++){let Oe=Re.get(b.textures[_e]);T.framebufferTextureLayer(T.FRAMEBUFFER,T.COLOR_ATTACHMENT0+_e,Oe.__webglTexture,D,ve)}}else if(b!==null&&D!==0){let ve=Re.get(b.texture);T.framebufferTexture2D(T.FRAMEBUFFER,T.COLOR_ATTACHMENT0,T.TEXTURE_2D,ve.__webglTexture,D)}U=-1},this.readRenderTargetPixels=function(b,P,D,B,N,Q,me,ve=0){if(!(b&&b.isWebGLRenderTarget)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");return}let _e=Re.get(b).__webglFramebuffer;if(b.isWebGLCubeRenderTarget&&me!==void 0&&(_e=_e[me]),_e){fe.bindFramebuffer(T.FRAMEBUFFER,_e);try{let Oe=b.textures[ve],De=Oe.format,Le=Oe.type;if(!Ve.textureFormatReadable(De)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not in RGBA or implementation defined format.");return}if(!Ve.textureTypeReadable(Le)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not in UnsignedByteType or implementation defined type.");return}P>=0&&P<=b.width-B&&D>=0&&D<=b.height-N&&(b.textures.length>1&&T.readBuffer(T.COLOR_ATTACHMENT0+ve),T.readPixels(P,D,B,N,Ne.convert(De),Ne.convert(Le),Q))}finally{let Oe=C!==null?Re.get(C).__webglFramebuffer:null;fe.bindFramebuffer(T.FRAMEBUFFER,Oe)}}},this.readRenderTargetPixelsAsync=async function(b,P,D,B,N,Q,me,ve=0){if(!(b&&b.isWebGLRenderTarget))throw new Error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");let _e=Re.get(b).__webglFramebuffer;if(b.isWebGLCubeRenderTarget&&me!==void 0&&(_e=_e[me]),_e)if(P>=0&&P<=b.width-B&&D>=0&&D<=b.height-N){fe.bindFramebuffer(T.FRAMEBUFFER,_e);let Oe=b.textures[ve],De=Oe.format,Le=Oe.type;if(!Ve.textureFormatReadable(De))throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in RGBA or implementation defined format.");if(!Ve.textureTypeReadable(Le))throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in UnsignedByteType or implementation defined type.");let je=T.createBuffer();T.bindBuffer(T.PIXEL_PACK_BUFFER,je),T.bufferData(T.PIXEL_PACK_BUFFER,Q.byteLength,T.STREAM_READ),b.textures.length>1&&T.readBuffer(T.COLOR_ATTACHMENT0+ve),T.readPixels(P,D,B,N,Ne.convert(De),Ne.convert(Le),0);let Qe=C!==null?Re.get(C).__webglFramebuffer:null;fe.bindFramebuffer(T.FRAMEBUFFER,Qe);let tt=T.fenceSync(T.SYNC_GPU_COMMANDS_COMPLETE,0);return T.flush(),await mf(T,tt,4),T.bindBuffer(T.PIXEL_PACK_BUFFER,je),T.getBufferSubData(T.PIXEL_PACK_BUFFER,0,Q),T.deleteBuffer(je),T.deleteSync(tt),Q}else throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: requested read bounds are out of range.")},this.copyFramebufferToTexture=function(b,P=null,D=0){let B=Math.pow(2,-D),N=Math.floor(b.image.width*B),Q=Math.floor(b.image.height*B),me=P!==null?P.x:0,ve=P!==null?P.y:0;Ce.setTexture2D(b,0),T.copyTexSubImage2D(T.TEXTURE_2D,D,0,0,me,ve,N,Q),fe.unbindTexture()};let $d=T.createFramebuffer(),Qd=T.createFramebuffer();this.copyTextureToTexture=function(b,P,D=null,B=null,N=0,Q=null){Q===null&&(N!==0?(fn("WebGLRenderer: copyTextureToTexture function signature has changed to support src and dst mipmap levels."),Q=N,N=0):Q=0);let me,ve,_e,Oe,De,Le,je,Qe,tt,rt=b.isCompressedTexture?b.mipmaps[Q]:b.image;if(D!==null)me=D.max.x-D.min.x,ve=D.max.y-D.min.y,_e=D.isBox3?D.max.z-D.min.z:1,Oe=D.min.x,De=D.min.y,Le=D.isBox3?D.min.z:0;else{let Ut=Math.pow(2,-N);me=Math.floor(rt.width*Ut),ve=Math.floor(rt.height*Ut),b.isDataArrayTexture?_e=rt.depth:b.isData3DTexture?_e=Math.floor(rt.depth*Ut):_e=1,Oe=0,De=0,Le=0}B!==null?(je=B.x,Qe=B.y,tt=B.z):(je=0,Qe=0,tt=0);let et=Ne.convert(P.format),Me=Ne.convert(P.type),gt;P.isData3DTexture?(Ce.setTexture3D(P,0),gt=T.TEXTURE_3D):P.isDataArrayTexture||P.isCompressedArrayTexture?(Ce.setTexture2DArray(P,0),gt=T.TEXTURE_2D_ARRAY):(Ce.setTexture2D(P,0),gt=T.TEXTURE_2D),T.pixelStorei(T.UNPACK_FLIP_Y_WEBGL,P.flipY),T.pixelStorei(T.UNPACK_PREMULTIPLY_ALPHA_WEBGL,P.premultiplyAlpha),T.pixelStorei(T.UNPACK_ALIGNMENT,P.unpackAlignment);let pr=T.getParameter(T.UNPACK_ROW_LENGTH),zt=T.getParameter(T.UNPACK_IMAGE_HEIGHT),fi=T.getParameter(T.UNPACK_SKIP_PIXELS),Ct=T.getParameter(T.UNPACK_SKIP_ROWS),Yi=T.getParameter(T.UNPACK_SKIP_IMAGES);T.pixelStorei(T.UNPACK_ROW_LENGTH,rt.width),T.pixelStorei(T.UNPACK_IMAGE_HEIGHT,rt.height),T.pixelStorei(T.UNPACK_SKIP_PIXELS,Oe),T.pixelStorei(T.UNPACK_SKIP_ROWS,De),T.pixelStorei(T.UNPACK_SKIP_IMAGES,Le);let it=b.isDataArrayTexture||b.isData3DTexture,Lt=P.isDataArrayTexture||P.isData3DTexture;if(b.isDepthTexture){let Ut=Re.get(b),vt=Re.get(P),Ht=Re.get(Ut.__renderTarget),za=Re.get(vt.__renderTarget);fe.bindFramebuffer(T.READ_FRAMEBUFFER,Ht.__webglFramebuffer),fe.bindFramebuffer(T.DRAW_FRAMEBUFFER,za.__webglFramebuffer);for(let Wr=0;Wr<_e;Wr++)it&&(T.framebufferTextureLayer(T.READ_FRAMEBUFFER,T.COLOR_ATTACHMENT0,Re.get(b).__webglTexture,N,Le+Wr),T.framebufferTextureLayer(T.DRAW_FRAMEBUFFER,T.COLOR_ATTACHMENT0,Re.get(P).__webglTexture,Q,tt+Wr)),T.blitFramebuffer(Oe,De,me,ve,je,Qe,me,ve,T.DEPTH_BUFFER_BIT,T.NEAREST);fe.bindFramebuffer(T.READ_FRAMEBUFFER,null),fe.bindFramebuffer(T.DRAW_FRAMEBUFFER,null)}else if(N!==0||b.isRenderTargetTexture||Re.has(b)){let Ut=Re.get(b),vt=Re.get(P);fe.bindFramebuffer(T.READ_FRAMEBUFFER,$d),fe.bindFramebuffer(T.DRAW_FRAMEBUFFER,Qd);for(let Ht=0;Ht<_e;Ht++)it?T.framebufferTextureLayer(T.READ_FRAMEBUFFER,T.COLOR_ATTACHMENT0,Ut.__webglTexture,N,Le+Ht):T.framebufferTexture2D(T.READ_FRAMEBUFFER,T.COLOR_ATTACHMENT0,T.TEXTURE_2D,Ut.__webglTexture,N),Lt?T.framebufferTextureLayer(T.DRAW_FRAMEBUFFER,T.COLOR_ATTACHMENT0,vt.__webglTexture,Q,tt+Ht):T.framebufferTexture2D(T.DRAW_FRAMEBUFFER,T.COLOR_ATTACHMENT0,T.TEXTURE_2D,vt.__webglTexture,Q),N!==0?T.blitFramebuffer(Oe,De,me,ve,je,Qe,me,ve,T.COLOR_BUFFER_BIT,T.NEAREST):Lt?T.copyTexSubImage3D(gt,Q,je,Qe,tt+Ht,Oe,De,me,ve):T.copyTexSubImage2D(gt,Q,je,Qe,Oe,De,me,ve);fe.bindFramebuffer(T.READ_FRAMEBUFFER,null),fe.bindFramebuffer(T.DRAW_FRAMEBUFFER,null)}else Lt?b.isDataTexture||b.isData3DTexture?T.texSubImage3D(gt,Q,je,Qe,tt,me,ve,_e,et,Me,rt.data):P.isCompressedArrayTexture?T.compressedTexSubImage3D(gt,Q,je,Qe,tt,me,ve,_e,et,rt.data):T.texSubImage3D(gt,Q,je,Qe,tt,me,ve,_e,et,Me,rt):b.isDataTexture?T.texSubImage2D(T.TEXTURE_2D,Q,je,Qe,me,ve,et,Me,rt.data):b.isCompressedTexture?T.compressedTexSubImage2D(T.TEXTURE_2D,Q,je,Qe,rt.width,rt.height,et,rt.data):T.texSubImage2D(T.TEXTURE_2D,Q,je,Qe,me,ve,et,Me,rt);T.pixelStorei(T.UNPACK_ROW_LENGTH,pr),T.pixelStorei(T.UNPACK_IMAGE_HEIGHT,zt),T.pixelStorei(T.UNPACK_SKIP_PIXELS,fi),T.pixelStorei(T.UNPACK_SKIP_ROWS,Ct),T.pixelStorei(T.UNPACK_SKIP_IMAGES,Yi),Q===0&&P.generateMipmaps&&T.generateMipmap(gt),fe.unbindTexture()},this.initRenderTarget=function(b){Re.get(b).__webglFramebuffer===void 0&&Ce.setupRenderTarget(b)},this.initTexture=function(b){b.isCubeTexture?Ce.setTextureCube(b,0):b.isData3DTexture?Ce.setTexture3D(b,0):b.isDataArrayTexture||b.isCompressedArrayTexture?Ce.setTexture2DArray(b,0):Ce.setTexture2D(b,0),fe.unbindTexture()},this.resetState=function(){O=0,I=0,C=null,fe.reset(),we.reset()},typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}get coordinateSystem(){return or}get outputColorSpace(){return this._outputColorSpace}set outputColorSpace(e){this._outputColorSpace=e;let t=this.getContext();t.drawingBufferColorSpace=Xe._getDrawingBufferColorSpace(e),t.unpackColorSpace=Xe._getUnpackColorSpace()}};var q=e=>document.getElementById(e),Od=To(q("thumbnail"),q("product-visual-caption"),{onChange:()=>{Bd(),pi()}}),$0={Explore:"Inspect source information. No inventory changes.",Buy:"Collect shopping intent for later receipt comparison. This is not payment.",Stock:"Unpacking intake needs eligible identity, quantity and a verified pantry action.",Audit:"Reconcile existing lots; never double-add scanned inventory.",Discard:"Outflow needs an identified lot, quantity and reason, with undo."},Ld="offmenu-scanner-read-beep",Ud="offmenu-scanner-spoken-name";function Dd(e){try{return localStorage.getItem(e)!=="off"}catch{return!0}}var cl="Explore",At=!0,St=!1,Fd=!1,ul=!1,ft=[],Bt=0,Ue=null,He=null,wr="overview",Jt=Dd(Ld),ui=Dd(Ud),Zt=null,Ad=null,En=null,sl=null,dr=0,dl=!1,Ua=2;function Fa(e,{user:t=!1}={}){dr=Math.max(0,Math.min(3,e)),t&&(dl=!0);let r=q("product-sheet");r.dataset.snap=String(dr);let i=[64,Math.min(Math.max(innerHeight*.32,190),310),Math.min(Math.max(innerHeight*.58,310),580),Math.max(220,innerHeight-116)];document.documentElement.style.setProperty("--sheet-occlusion",i[dr]+"px"),q("product-handle").setAttribute("aria-expanded",String(dr>0)),q("product-sheet-body").setAttribute("aria-hidden",String(dr===0)),q("snap-label").textContent=dr===3?"\u2304":"\u2303",q("product-handle").setAttribute("aria-label",dr===3?"Collapse product details":dr===0?"Expand product details":"Show additional product details"),requestAnimationFrame(()=>pi())}function Q0(e){Ua=Math.max(0,Math.min(3,e)),q("mode-dialog").dataset.snap=String(Ua),q("options-handle").setAttribute("aria-label",Ua===3?"Collapse scanner options":"Expand scanner options")}function kd(e,t,r){let i=q(e),n=null,a=!1;i.addEventListener("pointerdown",o=>{n=o.clientY,a=!1,i.setPointerCapture(o.pointerId)}),i.addEventListener("pointerup",o=>{if(n===null)return;let s=o.clientY-n;n=null,Math.abs(s)>28&&(a=!0,r(t()+(s<0?1:-1)))}),i.addEventListener("click",()=>{if(a){a=!1;return}r(t()===3?0:t()+1)}),i.addEventListener("keydown",o=>{(o.key==="ArrowUp"||o.key==="ArrowDown")&&(o.preventDefault(),r(t()+(o.key==="ArrowUp"?1:-1)))})}var wd=new Map,Rd=new Set,Cd="offmenu-kitchen-scanner-prefill-v1";function eb(){try{let e=sessionStorage.getItem(Cd);if(sessionStorage.removeItem(Cd),!e||e.length>1500)return null;let t=JSON.parse(e);return t.schema!=="offmenu-kitchen-scanner-prefill/1"||typeof t.raw!="string"||t.raw.length<1||t.raw.length>128||/[\x00-\x1f\x7f]/.test(t.raw)?null:{raw:t.raw}}catch{return null}}function Tt(e,t,r){let i=document.createElement(e);return i.textContent=t,r&&(i.className=r),i}function Tn(e,t){let r=Tt("button",e);return r.type="button",r.onclick=t,r}function Vt(e){q("lookup-status").textContent=e,q("lookup-status").title=e}function hi(e){q(e).open||q(e).showModal()}function Mt(e){q(e).close()}function Id(e,t){q(e).textContent=t||"\u2014",q(e).title=t||"Unavailable"}function ka(e){return He?.detail?.fields?.[e]}function hl(e){let t=ka(e);return t?.state==="present"?t.value:null}function tb(){let e=He?.provenance?.sourceId||He?.detail?.sourceBinding?.sourceId;return e==="off"?"Open Food Facts source \xB7 retain attribution and ODbL/DbCL notices. Source claims are not independently certified. Image and trademark permissions remain separate from product data rights.":e==="usda-files"?"USDA ARS FoodData Central source \xB7 retained public-domain/CC0 declaration. Source lineage applies; third-party image and trademark rights are unverified.":e?"Source "+e+" \xB7 attribution and use terms require the retained source record.":"Source attribution unavailable."}function rb(e){return Array.isArray(e)?e.map(t=>[t.role,t.qualificationState,t.reasonCode||"no reason supplied"].join(" \xB7 ")).join(" / "):"Role reasons unavailable"}var hr=0,Nd="";function Rr(e){if(e==null)return"Unknown";if(Array.isArray(e))return e.length?e.map(Rr).join(", "):"No values supplied";if(typeof e=="object"){let t=Object.entries(e).filter(([,r])=>r!=null);return t.length?t.map(([r,i])=>r.replace(/([a-z])([A-Z])/g,"$1 $2")+": "+Rr(i)).join(" \xB7 "):"Unknown"}return String(e)}function ci(e){let t=ka(e);return t?t.state==="present"?Rr(t.value):t.state==="null"?"Unknown":t.state==="missing"?"Not supplied":t.state==="not-loaded"?"Not loaded":t.state==="restricted"||t.state==="rights-held"?"Not available for display":"Unavailable right now":"Not supplied"}function ib(e){if(!e||typeof e!="object")return"Unknown \xB7 not zero";let t=e.value===null||e.value===void 0?"Unknown \xB7 not zero":Rr(e.value)+" "+(e.unit||"unit unknown"),r=[["basis",e.basis],["method",e.method],["source name",e.sourceName],["source nutrient ID",e.sourceNutrientId],["source row ID",e.sourceRowId],["source amount",e.sourceAmount],["source unit",e.sourceUnit]].filter(([,i])=>i!=null).map(([i,n])=>i+": "+Rr(n));return[t,...r].join(" \xB7 ")}function Bd(){if(Ue?.foundationLookup){let t=q("consumer-summary");t.replaceChildren();for(let r of vo(He,Ue,"overview").slice(0,8))t.append(Tt("p",r.label+": "+r.text,"label"));return}let e=q("consumer-summary");if(e.replaceChildren(),!He?.detail){e.append(Tt("p",Ue?.status==="scoped-miss"?"No match in the available barcode records. Other products may not be covered.":Vd(Ue)?zd(Ue):Ue?.status==="unavailable"?"Product lookup is unavailable for this release. Your scanned code is retained in this session; no product has been identified.":Ue?"Choose a source record to see its details.":"Scan to inspect a product.","label"));return}e.append(Tt("p","Source: "+(He.provenance?.sourceId||"unknown")+" \xB7 release "+(He.provenance?.releaseId||"unknown"),"label"));for(let[t,r]of[["Market","markets"],["Source allergens","sourceAllergenClaims"],["Source traces","sourceTraceClaims"],["Source labels","sourceDietaryLabelClaims"],["Source categories","categories"],["Source origins","origins"],["Manufactured (source)","manufacturingPlaces"]]){let i=hl(r);i!=null&&(!Array.isArray(i)||i.length)&&e.append(Tt("p",t+": "+Rr(i)))}for(let t of He.detail.labelSections?.sections||[])t.category==="origin_claim"&&e.append(Tt("p","Source origin claim: "+t.text))}function nb(e){let t=[],r=(i,n)=>{let a=(i.nameSpans||[]).map(c=>c.text).join(" \xB7 ")||i.text,o=(i.quantities||[]).map(c=>"Source-stated "+c.text+" \xB7 basis unknown; no interpreted amount"),s=(i.uncertainty||[]).map(c=>typeof c=="string"?c:c.reason||c.meaning||"Source syntax uncertain");t.push({label:"  ".repeat(n)+(n?"\u21B3 ":"")+a,text:[i.text,...o,...s].join(" \xB7 ")});for(let c of i.children||[])r(c,n+1)};for(let i of e.components||[])r(i,0);return t}function Vd(e){return e?.detailsState==="unavailable"&&!!e.detailReasonCode}function zd(e){return"Product details are unavailable right now. The barcode record is still shown."}function ab(){if(Ue?.foundationLookup){let n=vo(He,Ue,wr);return Ue.matches?.length&&n.push({label:"Source alternatives",text:"Inspect source observations",action:di}),n}if(!Ue)return[{label:"Ready",text:"Scan a barcode to see product details."}];let e=He?.detail;if(Ue.status==="unavailable")return[{label:"Product lookup",text:"Unavailable for this release. The code was read, but no product identity or details were verified."}];if(!e&&["partial","searching"].includes(Ue.status))return[{label:"Selected search",text:Ue.status==="partial"?"Incomplete \xB7 retry the failed lane; loaded source observations remain visible.":Ue.status==="searching"?"More selected lanes remain; no absence established.":"Selected identifier lookup unavailable; no absence established."},{label:"Loaded source observations",text:String(Ue.matches?.length||0),action:di}];if(!e){let n=[{label:"Source details",text:Ue.status==="scoped-miss"?"No matching source observation in the selected index and completed query plan \xB7 not global absence.":Vd(Ue)?Ue.matches.length+" source identifier assertion(s) retained \xB7 "+zd(Ue):Ue.status==="ambiguous"?"Multiple source records or eligible detail projections; inspect without resolving identity.":"Identifier known \xB7 product details "+(He?.availability?.state||Ue.detailsState||"not-loaded")+" \xB7 "+(He?.availability?.reasonCode||Ue.detailReasonCode||"reason unavailable")}];for(let a of Ue.matches||[])a.availability?.roleReasons?.length&&n.push({label:"Source assertion "+a.identifier.assertion_id+" \xB7 required role reasons",text:rb(a.availability.roleReasons)});return Ue.detailBackend==="retained-product-federation-v1"&&n.push({label:"Per-backend coverage \xB7 global counts unknown",text:Rr(Ue.productDetailCoverage)}),Ue.matches?.length&&n.push({label:"Source alternatives",action:di,text:"Inspect source records"}),n}let t=e.fields,r=[],i=(n,a)=>r.push({label:n,text:Rr(a)});if(wr==="overview"){for(let[n,a]of[["Product \xB7 source assertion","name"],["Brand \xB7 source assertion","brand"],["Markets (not origin)","markets"],["Package \xB7 source projection","packageQuantity"],["Serving \xB7 source projection, not package","servingQuantity"],["Source data type","dataType"],["Source categories","categories"],["Source allergen claims (not certification)","sourceAllergenClaims"],["Source trace claims (not certification)","sourceTraceClaims"],["Source dietary / label claims (not certification)","sourceDietaryLabelClaims"],["Source origins","origins"],["Manufacturing places","manufacturingPlaces"],["Names / languages","names"]])i(n,ci(a));i("Ingredient use","Unclassified by this response \xB7 no qualified usable_as or contains relation. Barcode and source identity remain visible."),i("Supplier / offers, recalls, recipe links","No qualified relation supplied by this selected response \xB7 unknown, not none."),i("Product image",Od.current()?.caption||"Product photo unavailable"),Ue.detailBackend==="retained-product-federation-v1"&&i("Detail coverage","Federated retained subset \xB7 incomplete. Identifier coverage is separate; unknown global counts are not zero."),r.push({label:"Competing observations",text:"Inspect source records",action:di})}else if(wr==="ingredients"){let n=e.labelSections,a=e.ingredientComponents;if(a?.state==="cached-candidate")i("Source-derived candidate components","Parent/child label syntax only \xB7 no Ingredients heading, canonical identities, certification or unstated quantities."),r.push(...nb(a)),i("Component annotation evidence",a.annotationSha256),i("Annotation limits",a.reviewStatus);else if(n?.state==="cached-candidate")for(let o of n.sections)o.category==="ingredient_list"&&i("Candidate ingredient passage \xB7 component annotation unavailable",o.text);else i("Whole label text \xB7 extraction pending",ci("ingredientDeclaration"));for(let o of n?.sections||[])o.category==="allergen_statement"&&i("Separate source allergen statement \xB7 not certification",o.text)}else if(wr==="nutrition"){let n=hl("nutrientProfile");i("Projected measurement basis \xB7 applicability unverified",ka("nutrientProfile")?.state==="present"?n?.basis:ci("nutrientProfile")),i("Source nutrition basis",ci("nutritionSourceBasis"));for(let[a,o]of Object.entries(n?.nutrients||{}))i(a+" \xB7 source nutrient assertion",ib(o));i("Raw retained nutrient values",ci("rawNutriments"))}else{if(i("Source and use notice",tb()),i("Source release",He?.identifier?.release_id||"Unknown"),i("Source record",He?.identifier?.source_record_id||"Unknown"),i("Source citation",He?.identifier?.citation_id||"Not supplied"),i("Full package label",ci("ingredientDeclaration")),e.labelSections?.state==="cached-candidate")for(let n of e.labelSections.sections)n.text.trim()&&i("Source label \xB7 "+n.category.replaceAll("_"," "),n.text);for(let[n]of Object.entries(t))n!=="ingredientDeclaration"&&i(n.replace(/([a-z])([A-Z])/g,"$1 $2").replaceAll("_"," "),ci(n));Ue.matches?.length>1&&r.push({label:"Other source records",text:"See all matching records",action:di})}return r.push(...zl(e,wr)),r}function pi(){let e=q("data-pane");q("product-visual-caption").hidden=wr!=="source";let t=(Ue?.id||"empty")+":"+(He?.id||"none")+":"+wr;t!==Nd&&(Nd=t,hr=0);let r=[[]];e.replaceChildren(),e.setAttribute("aria-label",wr+" readout");let i=()=>e.clientHeight<60||e.scrollHeight<=e.clientHeight+1,n=(o,s)=>{let c=Tt("article","","paged-field");return c.append(Tt("h3",o.label),o.action?Tn(o.text,o.action):Tt("p",s)),c},a=()=>{r.push([]),e.replaceChildren()};for(let o of ab()){let s=Array.from(o.text||"\u2014"),c=0;do{let u=n(o,s.slice(c).join(""));if(e.append(u),i()){r.at(-1).push(u);break}if(u.remove(),r.at(-1).length){a();continue}let l=1,d=s.length-c,h=1;for(;l<=d;){let m=Math.floor((l+d)/2);u=n(o,s.slice(c,c+m).join("")),e.append(u);let g=i();u.remove(),g?(h=m,l=m+1):d=m-1}u=n(o,s.slice(c,c+h).join("")),r.at(-1).push(u),e.append(u),c+=h,c<s.length&&a()}while(c<s.length)}hr=Math.min(hr,r.length-1),e.replaceChildren(...r[hr]),q("detail-page-status").textContent=hr+1+" / "+r.length,q("detail-prev").disabled=hr===0,q("detail-next").disabled=hr===r.length-1}function Hd(e){let t=e?.selectedRecord;return t&&e.matches?.includes(t)?t:null}function Ot(){Ue&&(Ue.selectedRecord=He&&Ue.matches.includes(He)?He:null),Od.show({reference:He?.sourceObservationReference??null,sourcePhotoSelection:He?.detail?.sourcePhotoSelection??null,detail:He?.detail,entryId:Ue?.id,generation:Bt,name:He?.name,theme:document.documentElement.dataset.theme,offline:navigator.onLine===!1});let e=Ue;q("identifier-label").textContent=e?.namespace==="USDA-FDC"?"USDA-FDC \xB7 original identifier":"Barcode \xB7 original",q("current-barcode").textContent=e?.raw||"\u2014",Id("product-name",He?.kind==="source-identity"?null:He?.name||(e?.status==="source-match"?"Name unavailable \xB7 source record found":e?.status==="ambiguous"?"Name unavailable \xB7 multiple source records":null)),Id("brand-name",He?.brand);let t=He?.detail?.canonicalCategory,r=He?.detail?.canonicalIngredient,i=He?.kind==="source-identity"?"Unknown":t?.status==="qualified"&&t?.preferredLabel?t.preferredLabel:"Not yet identified",n=He?.kind==="source-identity"?"Unknown":r?.status==="qualified"&&r?.preferredLabel?r.preferredLabel:r?.status==="not-applicable"?"Not applicable":"Not yet identified",a=ka("packageQuantity")?.state==="present"?Rr(hl("packageQuantity")):"\u2014";for(let[o,s,c]of[["category-value","Category",i],["ingredient-value","Ingredient match",n],["pack-value","Source pack size",a]])q(o).textContent=c,q(o).setAttribute("aria-label",s+": "+c);q("sheet-handle-label").textContent=e?.raw?He?.name||"Barcode "+e.raw:"Ready to scan",Bd(),q("kitchen-handoff").hidden=!0,q("queue-count").textContent=ft.length,q("active-mode").textContent=cl+(ul?" \xB7 Finished":St?" \xB7 Paused":""),q("undo").disabled=!ft.length,q("pause").disabled=!1,q("pause").textContent="List",q("finish").textContent="Finish",q("camera-empty").hidden=Fd,Vt(e?e.status==="unavailable"?"Code read \xB7 public product lookup unavailable for this release":e.status==="pending"?"Code read \xB7 checking available product records":"Product status unavailable":"Ready \xB7 scan or enter a code"),e?.foundationLookup&&Vt(e.status==="scoped-miss"?"Barcode retained · no qualified details in the selected source indexes. Other sources may differ.":e.status==="unavailable"?"Code read \xB7 selected foundation data unavailable; no global absence established":e.matches.length+" source foundation observation(s) \xB7 full product not established"),pi()}async function Gd(){let e=window.AudioContext||window.webkitAudioContext;if(!e)return q("feedback-status").textContent="Sound is unavailable in this browser.",!1;try{if(Zt??=new e,Zt.state!=="running"&&await Zt.resume(),Zt.state==="running")return!0;q("feedback-status").textContent="Tap the scanner to allow sound."}catch(t){q("feedback-status").textContent="Tap the scanner to allow sound.",console.warn("Scanner audio could not start",t?.name||"unknown")}return!1}function Ba(){!Jt||Zt?.state==="running"||Gd().then(e=>{if(!e)return;let t=En;En=null,q("audio-unlock").hidden=!0,t&&t.id===Ue?.id&&performance.now()-t.at<1200&&Wd()})}function Wd(){if(!Jt||Zt?.state!=="running")return!1;try{let e=Zt.createOscillator(),t=Zt.createGain(),r=Zt.currentTime;return e.type="sine",e.frequency.setValueAtTime(1e3,r),e.frequency.linearRampToValueAtTime(1240,r+.045),t.gain.setValueAtTime(1e-4,r),t.gain.linearRampToValueAtTime(.032,r+.008),t.gain.exponentialRampToValueAtTime(1e-4,r+.12),e.connect(t),t.connect(Zt.destination),e.start(r),e.stop(r+.13),!0}catch(e){return q("feedback-status").textContent="Sound is unavailable; the scan remains visible.",console.warn("Scanner beep failed",e?.name||"unknown"),!1}}function ob(e,t){q("scanner-last").textContent=(e.captureKind==="manual lexical identifier"?"Code entered":"Scanned")+" \xB7 "+e.raw,q("instrument").dataset.readCue="read",clearTimeout(Ad),Ad=setTimeout(()=>{delete q("instrument").dataset.readCue},1100)}function jd(){sl&&(window.speechSynthesis?.removeEventListener?.("voiceschanged",sl),sl=null)}function pl(){q("sound").textContent=Jt?"Beep on":"Beep off",q("sound").setAttribute("aria-pressed",String(Jt)),q("spoken-name").textContent=ui?"Speak product name on":"Speak product name off",q("spoken-name").setAttribute("aria-pressed",String(ui))}var sb={ean_13:"EAN-13",ean_8:"EAN-8",upc_a:"UPC-A",upc_e:"UPC-E","EAN-13":"EAN-13","EAN-8":"EAN-8","UPC-A":"UPC-A","UPC-E":"UPC-E","GTIN-14":"GTIN-14"};async function Xd(e,t,r=null,i=crypto.randomUUID(),{sourceNamespace:n="barcode",representationHint:a=null,decoderCapture:o=null}={}){if(!At||St||Rd.has(i))return;if(typeof e!="string"||!e.length||e.length>128||/[\x00-\x1f\x7f]/.test(e)){Vt("Invalid capture \xB7 enter 1\u2013128 original printable characters.");return}let s=n==="barcode"&&(a||sb[t])||null,c=o?gc(o):null;if(o&&(!c||!vc(c,e,s))){Vt("Decoder capture needs manual confirmation. No lookup was started.");return}Rd.add(i),jd(),En=null;try{window.speechSynthesis?.cancel()}catch{}let u=++Bt,l={id:i,foundationLookup:!0,lookupPending:!0,sourceChoiceConfirmed:!1,queryGeneration:u,raw:e,namespace:n,captureKind:t,symbology:s,alias:r,decoderCapture:c,status:"pending",matches:[],mode:cl};ft.push(l),Ue=l,He=null,dl||Fa(innerWidth>=740?3:1),Ot();let d=Wd();En=Jt&&!d&&Zt?.state!=="running"?{id:l.id,at:performance.now()}:null,q("audio-unlock").hidden=!En,ob(l,d);let h=await Vn(e,l.queryGeneration,null,s,n);!ft.some(m=>m.id===l.id)||l.status!=="pending"||(Object.assign(l,h),l.lookupPending=!1,u===Bt&&(Ue=l,h.matches?.length&&["source-match","ambiguous"].includes(h.status)&&bt.noteAccepted(),He=h.status==="source-match"?h.matches[0]:null,Ot()))}function di(){let e=Ue,t=Bt,r=q("match-list");r.replaceChildren(),q("matches-note").textContent=(e?.matches?.length||0)+" source observation(s). Keep source claims separate; no physical-product equivalence or full-product completion is inferred.";for(let i of e?.matches||[]){let n=Tt("div","","choice");n.append(Tt("strong",i.kind==="source-identity"?Ka(i):i.name||"Name not supplied"),Tt("p","Source: "+i.provenance.sourceId+" \xB7 release "+(i.provenance.releaseId||"unknown")+" \xB7 record "+i.id),Tn("Choose this source observation",()=>{t!==Bt||Ue?.id!==e.id||(He=i,e.sourceChoiceConfirmed=!0,Mt("matches-dialog"),Ot())})),r.append(n)}e?.hasMore&&r.append(Tn("Continue source search",async()=>{let i=await Vn(e.raw,e.queryGeneration??e.generation,e.nextCursor,e.symbology,e.namespace);if(!(t!==Bt||Ue?.id!==e.id)){if(i.status==="unavailable"){Vt("Next source page is unavailable; loaded records remain visible.");return}try{Object.assign(e,lc(e,i))}catch{Vt("Source release changed; loaded records remain visible.");return}Ot(),di()}})),e?.identityNextOffset!==null&&e?.identityNextOffset!==void 0&&!e?.identityState?.error&&r.append(Tn("More source records",async()=>{try{let i=await cc(e);if(t!==Bt||Ue?.id!==e.id)return;Object.assign(e,i),Ot(),di()}catch{Vt("Additional source records are unavailable; loaded records remain visible.")}})),hi("matches-dialog")}function qd(){let e=q("queue-list");e.replaceChildren(),q("session-summary").textContent=ft.length?ft.length+" item"+(ft.length===1?"":"s")+" scanned. "+ft.filter(t=>t.status==="ambiguous").length+" need"+(ft.filter(t=>t.status==="ambiguous").length===1?"s":"")+" a choice. Nothing has been added to your pantry.":"No items scanned yet.";for(let t of ft){let r=Tt("div","","queue-row");r.append(Tt("strong",t.raw),Tt("span",t.mode+" \xB7 "+t.status+" \xB7 "+t.matches.length+" source records"),Tn("Inspect",()=>{Bt++,Ue=t,He=Hd(t),Mt("session-dialog"),Ot()})),e.append(r)}}var bt=_c({autoResume:!0,canScan:()=>At&&!St&&(dr<3||innerWidth>=740)&&!["tools-dialog","manual-dialog","session-dialog","matches-dialog","data-dialog","mode-dialog"].some(e=>q(e)?.open),onCode:(e,t)=>{let r=t?.captureEnvelope,i=t?.originalCaptures||[];if(!r||r.status!=="ready"||i.length!==1||i[0].value!==r.lookupLexicalValue||e!==r.lookupLexicalValue){Vt("Decoder capture needs manual confirmation \xB7 use Type code.");return}t?.captureKind==="photo"&&Mt("manual-dialog"),Xd(e,t?.captureKind==="photo"?"photo":"camera lexical capture",null,crypto.randomUUID(),{representationHint:r.lookupSymbology,decoderCapture:r})},onStream:e=>{Fd=!!e,Ot()},onStartGesture:()=>Jt?Gd():void 0,storage:{getItem:e=>wd.get(e)||null,setItem:(e,t)=>wd.set(e,t)}});q("scanner-mode").value="handheld";q("scanner-mode").onchange();q("mode").onchange=()=>{q("mode-description").textContent=$0[q("mode").value],q("enter-mode").textContent="Enter "+q("mode").value};q("mode").onchange();q("enter-mode").onclick=()=>{Bt++,Ue=ft.at(-1)||null,He=null,cl=q("mode").value,At=!0,St=!1,ul=!1,Mt("mode-dialog"),Ot(),bt.start()};q("close-mode").onclick=()=>{Mt("mode-dialog"),At=!0,St=!1,Ot(),bt.start()};q("mode-dialog").addEventListener("cancel",()=>{At=!0,St=!1,Ot(),bt.start()});q("manual-namespace").onchange=()=>{let e=q("manual-namespace").value==="USDA-FDC";q("manual-representation").disabled=e,e&&(q("manual-representation").value="")};q("manual").onsubmit=e=>{e.preventDefault();let t=q("barcode").value,r=q("manual-namespace").value,i=q("manual-representation").value||null;if(!["barcode","USDA-FDC"].includes(r)||r==="USDA-FDC"&&i){Vt("Choose a supported namespace and barcode hint.");return}q("barcode").value="",Mt("manual-dialog"),At&&!St&&bt.start(),Xd(t,"manual lexical identifier",null,crypto.randomUUID(),{sourceNamespace:r,representationHint:i})};q("manual-open").onclick=()=>{Mt("session-dialog"),q("barcode").value="",q("manual-namespace").value="barcode",q("manual-representation").value="",q("manual-namespace").onchange(),hi("manual-dialog")};q("manual-cancel").onclick=()=>{Mt("manual-dialog"),At&&!St&&bt.start()};q("manual-dialog").addEventListener("cancel",()=>{At&&!St&&bt.start()});kd("product-handle",()=>dr,e=>Fa(e,{user:!0}));kd("options-handle",()=>Ua,Q0);window.addEventListener("resize",()=>{dl||Fa(Ue?innerWidth>=740?3:1:0)});q("session-button").onclick=()=>{qd(),hi("session-dialog")};q("close-session").onclick=()=>{Mt("session-dialog"),At&&!St&&bt.start()};q("change-mode").onclick=()=>{Bt++,At=!1,St=!1,bt.stop(),Mt("tools-dialog"),Mt("session-dialog"),Ot(),hi("mode-dialog")};q("close-matches").onclick=()=>Mt("matches-dialog");q("undo").onclick=()=>{Bt++;let e=ft.pop();Ue=ft.at(-1)||null,He=Hd(Ue),Ot()};q("pause").onclick=()=>{qd(),hi("session-dialog"),bt.stop({announce:!1})};q("finish").onclick=()=>{try{let e=ft.some(r=>r.selectedRecord?.kind==="source-identity")?kl(ft):ft.some(r=>r.foundationLookup)?Tl(ft):rc(ft),t=JSON.stringify(e);if(e.schema==="offmenu-foundation-scanner-handoff/1"&&new TextEncoder().encode(t).byteLength>3e3)throw Error("Selected source handoff exceeds this tab limit. Keep fewer items and finish again.");sessionStorage.setItem(Ql,t),Bt++,At=!1,ul=!0,St=!1,bt.stop(),location.assign("/kitchen.html?scan=staged")}catch(e){Vt("Finish needs review: "+e.message)}};for(let e of document.querySelectorAll("[data-tab]"))e.onclick=()=>{wr=e.dataset.tab,document.querySelectorAll("[data-tab]").forEach(t=>t.setAttribute("aria-selected",String(t===e))),pi()};pl();q("audio-unlock").onclick=Ba;document.addEventListener("pointerdown",Ba,{capture:!0});document.addEventListener("keydown",e=>{!e.repeat&&!e.ctrlKey&&!e.metaKey&&!e.altKey&&Ba()},{capture:!0});q("sound").onclick=()=>{Jt=!Jt;try{localStorage.setItem(Ld,Jt?"on":"off")}catch{}pl(),Jt&&Ba(),q("feedback-status").textContent=Jt?"Beep enabled where browser audio is available.":"Beep muted; visual confirmation stays on."};q("spoken-name").onclick=()=>{ui=!ui;try{localStorage.setItem(Ud,ui?"on":"off")}catch{}if(!ui){jd();try{window.speechSynthesis?.cancel()}catch{}}pl(),q("feedback-status").textContent=ui?"English product names will be spoken when a source-backed name and voice are available.":"Spoken names off."};q("tools-open").onclick=()=>{hi("tools-dialog"),bt.stop({announce:!1})};q("tools-close").onclick=()=>{Mt("tools-dialog"),At&&!St&&bt.start()};q("tools-dialog").addEventListener("cancel",()=>{At&&!St&&bt.start()});q("tools-dialog").addEventListener("click",e=>{if(e.target===e.currentTarget){Mt("tools-dialog"),At&&!St&&bt.start();return}e.target.closest("#manual-open,#session-button,#change-mode")&&Mt("tools-dialog")},{capture:!0});q("session-dialog").addEventListener("cancel",()=>{At&&!St&&bt.start()});q("detail-prev").onclick=()=>{hr=Math.max(0,hr-1),pi()};q("detail-next").onclick=()=>{hr++,pi()};var Pd;new ResizeObserver(()=>{cancelAnimationFrame(Pd),Pd=requestAnimationFrame(()=>pi())}).observe(q("data-pane"));var Da=()=>{};function fl(e,t){document.documentElement.dataset.theme=e,document.documentElement.dataset.themeSource=t;for(let r of document.querySelectorAll("img[data-offmenu-logo]"))r.src=e==="dark"?"/scanner-balanced-final-dark.svg":"/scanner-balanced-final.svg";Da()}q("theme").onclick=()=>{let e=document.documentElement.dataset.theme==="dark"?"light":"dark";try{localStorage.setItem("offmenu-scanner-theme",e)}catch{}fl(e,"manual")};var lb=matchMedia("(prefers-color-scheme: dark)");lb.addEventListener("change",e=>{let t;try{t=localStorage.getItem("offmenu-scanner-theme")}catch{}["dark","light"].includes(t)||fl(e.matches?"dark":"light","system")});fl(document.documentElement.dataset.theme,document.documentElement.dataset.themeSource||"system");q("camera-check").onclick=async()=>{let e="unavailable";try{e=(await navigator.permissions.query({name:"camera"})).state}catch{}let t={context:window.isSecureContext?"secure":"insecure",origin:location.origin,browser:navigator.userAgent,mediaDevices:!!navigator.mediaDevices,getUserMedia:typeof navigator.mediaDevices?.getUserMedia,nativeBarcodeDetector:typeof window.BarcodeDetector,permission:e,videoReadyState:q("video").readyState,streamActive:!!q("video").srcObject?.active,decoder:"Existing native retail formats + local ZXing WASM fallback; decoding not established by this diagnostic"};q("camera-diagnostics").textContent=JSON.stringify(t,null,2)};try{let e=q("bezel"),t=new Md({alpha:!0,antialias:!0,powerPreference:"low-power"});t.setPixelRatio(Math.min(devicePixelRatio||1,1.5)),t.domElement.setAttribute("aria-hidden","true"),e.append(t.domElement);let r=new ud,i=new Oa(-1,1,1,-1,.1,100);i.position.z=12;let n=new md({color:4875656,metalness:.4,roughness:.6}),a=new xn(1,1,.18),o=[];for(let l=0;l<4;l++){let d=new Yt(a,n);r.add(d),o.push(d)}r.add(new bd(16777215,2));let s=new _d(14412543,3);s.position.set(-3,5,8),r.add(s);let c=0;Da=()=>{let l=e.getBoundingClientRect();if(!l.width||!l.height)return;let d=l.width/100,h=l.height/100;i.left=-d/2,i.right=d/2,i.top=h/2,i.bottom=-h/2,i.updateProjectionMatrix(),t.setSize(l.width,l.height,!1),o[0].scale.set(d,.008,1),o[0].position.set(0,h/2-.025,0),o[1].scale.set(d,.008,1),o[1].position.set(0,-h/2+.025,0),o[2].scale.set(.008,h,1),o[2].position.set(-d/2+.025,0,0),o[3].scale.set(.008,h,1),o[3].position.set(d/2-.025,0,0),n.color.set(document.documentElement.dataset.theme==="dark"?4875656:11388901),t.render(r,i),e.dataset.renderer="Three.js r"+Ou,e.dataset.renderedFrames=String(++c)};let u=new ResizeObserver(Da);u.observe(e),Da(),window.addEventListener("pagehide",()=>{u.disconnect(),a.dispose(),n.dispose(),t.dispose()},{once:!0})}catch(e){q("bezel").dataset.renderer="CSS fallback \xB7 "+e.name}function ml(){document.documentElement.style.setProperty("--screen",(window.visualViewport?.height||innerHeight)+"px")}window.visualViewport?.addEventListener("resize",ml);window.addEventListener("resize",ml);ml();Fa(0);Ot();var ll=eb();ll&&(q("barcode").value=ll.raw,q("manual-namespace").value="barcode",q("manual-representation").value="",q("manual-namespace").onchange(),hi("manual-dialog"),Vt("Kitchen capture ready \xB7 confirm original "+ll.raw+" for public lookup. No inventory change yet."));bt.start();
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
