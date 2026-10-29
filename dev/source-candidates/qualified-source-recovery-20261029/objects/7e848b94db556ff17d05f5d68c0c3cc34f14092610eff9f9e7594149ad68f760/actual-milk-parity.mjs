import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {performance} from 'node:perf_hooks';
import {createSourceBarcodeHandler,PUBLIC_BASE} from './build/source-barcode-handler.bundle.mjs';
import {SOURCE_PINS} from './source/protocol-pins.mjs';
const root=new URL('./',import.meta.url),input=new URL('./input/',root);
const manifest=fs.readFileSync('/home/user/src/offmenu-source-barcode-handler-20261029-r3/input/published-manifest.json');
const shard=fs.readFileSync('/home/user/src/offmenu-source-barcode-handler-20261029-r3/input/milk-shard.json.gz');
const selected=JSON.parse(fs.readFileSync(new URL('actual-milk-reference.json',input)));
const asset=fs.readFileSync(new URL('actual-milk-original-asset.jsonl.gz',input));
const sha=x=>createHash('sha256').update(x).digest('hex');
if(sha(manifest)!=='d22d0c464d32ea8df1b81da1f74701db5b563cd3c5b69c1d4e0f9b116709c839'||sha(shard)!=='992dd13bd543d3af7050544ec48dea9e4536fa1afcb9044e3a0bf0c8690f9ba3'||sha(asset)!==selected.reference.asset.sha256)throw Error('retained custody differs');
const prefix='https://offmenu-corpus.netlify.app/common-data/derived-releases/source-barcode-index-v1-20261029/';
const manifestUrl=prefix+'manifest.json',assetUrl=PUBLIC_BASE.origin+selected.reference.asset.path;const calls=[];
const handler=createSourceBarcodeHandler({selection:{manifestUrl,manifestSha256:sha(manifest),indexReleaseId:'source-barcode-index-v1-20261029',sourcePins:SOURCE_PINS,publicBase:PUBLIC_BASE},fetchImpl:async(url,options)=>{
 calls.push(url===assetUrl?'one-original-asset':url===manifestUrl?'retained-manifest':'retained-milk-shard');
 if(options.redirect!=='manual'||options.headers['Accept-Encoding']!=='identity')throw Error('Worker transport contract');
 if(url===manifestUrl)return new Response(manifest);if(url===prefix+'shards/85.json.gz')return new Response(shard);
 if(url===assetUrl)return new Response(asset);throw Error('unapproved-extra-request');
}});
const start=performance.now();const response=await handler(new Request('https://offmenu.aldous.info/api/corpus/source-barcode?source=off&release=2026-10-12&namespace=barcode&value=4088700055496&include=facts'));
const body=await response.text(),value=JSON.parse(body),f=value.originalFacts;
fs.writeFileSync(new URL('actual-api-facts-response.json',input),body+'\n',{mode:0o600});
const receipt={schemaVersion:'offmenu-one-original-public-product-api-facts-parity/1',boundary:'local bundled API handler; one original asset fetched externally once; retained index bytes reused; NOT deployed API acceptance',
 httpStatus:response.status,schema:value.schemaVersion,factsStatus:value.factsStatus,manifestSha256:sha(manifest),assetSha256:sha(asset),assetBytes:asset.length,packetOrdinal:119,packetCount:1000,
 candidateTotal:value.candidateLookup.candidateTotal,candidateCountKnown:value.candidateLookup.countKnown,candidateLookupComplete:value.candidateLookup.complete,
 originalName:f?.name??null,originalFieldCount:f?.facts.length??0,citationCount:f?.citations.length??0,unknownMarkerCount:f?.facts.reduce((n,x)=>n+(x.text.match(/Unknown/g)||[]).length,0)??null,
 explicitZeroMarkerCount:f?.facts.reduce((n,x)=>n+(x.text.match(/(?:^|[ :])0(?:\s|$)/g)||[]).length,0)??null,unresolvedRelatedResourceCount:f?.unresolvedRelations.length??null,
 exactReturnedFields:f?.facts.map(x=>({label:x.label,formattedOriginalValueSha256:sha(Buffer.from(x.text)),status:x.status,sourcePath:x.sourcePath,citationCount:x.citationIds.length}))??[],
 citationsAllSourceBound:f?.citations.every(c=>c.sourceId==='off'&&c.revisionId==='2026-10-12')??false,citationsAllLicensed:f?.citations.every(c=>typeof c.license==='string'&&!!c.license)??false,
 apiResponseSha256:sha(Buffer.from(body)),apiResponseBytes:Buffer.byteLength(body),calls,elapsedMs:performance.now()-start,
 canonicalIdentityAsserted:value.canonicalIdentityAsserted,automaticPlanningEligible:value.automaticPlanningEligible,nutritionAggregationEligible:value.nutritionAggregationEligible,
 qualifications:'Original display fields only; references stay unresolved; no complete nutrition/ingredient coverage, zero filling, cross-packet resolution or planning admission'};
fs.writeFileSync(new URL('ACTUAL-MILK-FACTS-RECEIPT.json',root),JSON.stringify(receipt,null,2)+'\n');
console.log(JSON.stringify(receipt));
if(response.status!==200||value.factsStatus!=='verified-original-public-packet'||f?.name!=='Champ iced coffee'||f?.facts.length!==9||f?.citations.length!==1)process.exitCode=1;
