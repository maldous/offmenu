import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,writeFile,rm,readFile} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {createIdentifierAdapter,identifierForms} from '../cloud/identifier-host.mjs';
import {lookupIdentityPage,lookupExactObservationDetail,sourceObservationReference as uiReference,DETAIL_SELECTION} from '../public/scanner-identity-v2.js';
import {validateLot} from '../public/model.js';
const DB='97c2f7390f75d8d187b49c927652515cd829e095301d7b305a0081120c7502f0';
const BACKEND='retained-product-federation-v1';
async function fixture(mode='valid',delay=0,timeoutMs=7000,records=null,failDisposition=null){
 const dir=await mkdtemp(join(tmpdir(),'offmenu-identity-host-owned-'));
 const index=join(dir,'identity.py'),details=join(dir,'details.py'),calls=join(dir,'calls.jsonl');
 const recordsJson=JSON.stringify(records??[1,2].map(n=>({assertion_id:n,run_id:'selected-run',namespace:'barcode',lexical_value:'00027000612323',source_id:'fixture-'+n,disposition:'source-asserted',ingredientStatus:'unclassified'})));
 const identity=`import sys,json,time\nq=json.load(sys.stdin)\ntime.sleep(${delay})\nwith open(${JSON.stringify(calls)},'a') as f:f.write('identity:'+q['action']+'\\n')\nif q['action']=='status':\n print(json.dumps({'databaseLoaded':True,'queryAvailable':True,'databaseSha256':'${DB}','loadComplete':True,'runId':'worker57-full-retained-identifiers-v1'}));sys.exit(0)\nrecords=json.loads(${JSON.stringify(recordsJson)})\nif q['disposition']==${JSON.stringify(failDisposition??'never-fail')}:sys.exit(3)\nrows=[r for r in records if r['namespace']==q['namespace'] and r['lexical_value']==q['lexical_value'] and r['disposition']==q['disposition'] and r['assertion_id']>q['after']]\nmore=len(rows)>q['limit'];rows=rows[:q['limit']]\nprint(json.dumps({'databaseSha256':'${DB}','rows':rows,'hasMore':more,'nextAssertionId':rows[-1]['assertion_id'] if more else None,'metadata':{'scope':'generated-only'},'assurance':'lexical-source-observations-only'}))\n`;
 let enrich=`import sys,json,time\nq=json.load(sys.stdin)\nwith open(${JSON.stringify(calls)},'a') as f:f.write('details:'+q['action']+'\\n')\np=q['identity'];p['details']={'detailBackend':'${BACKEND}','state':'loaded','accepted':False,'sourceProducts':[{'records':[{'kind':'product','data':{'name':'Generated product'}}],'ingredientUsability':{'status':'unclassified'}}]}\n`;
 if(mode==='invalid')enrich+="print('{invalid')\n";
 else if(mode==='overflow')enrich+="print('x'*262145)\n";
 else if(mode==='timeout')enrich+="time.sleep(0.4);print(json.dumps(p))\n";
 else if(mode==='mismatched')enrich+="p['rows']=[];print(json.dumps(p))\n";
 else if(mode==='failed')enrich+="sys.exit(3)\n";
 else enrich+="print(json.dumps(p,sort_keys=True))\n";
 await writeFile(index,identity);await writeFile(details,enrich);
 return {adapter:createIdentifierAdapter({scriptPath:index,federatedScriptPath:details,timeoutMs}),dir,calls,close:()=>rm(dir,{recursive:true,force:true})};
}
function request(changes={}){return new Request('https://offmenu-identifiers.invalid/__dev/identifiers',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({namespace:'barcode',lexical_value:'00027000612323',limit:25,cursor:null,generation:'generated-session',databaseSha256:DB,include:[BACKEND],...changes})});}

test('identity is retrieved before details, deep row binding ignores JSON key ordering',async()=>{
 const f=await fixture();try{const response=await f.adapter(request());const body=await response.json();assert.equal(response.status,200);assert.equal(body.rows.length,2);assert.equal(body.details.state,'loaded');assert.equal(body.rows[0].lexical_value,'00027000612323');assert.equal(body.identitySearchIndependentOfDetails,true);assert.deepEqual((await readFile(f.calls,'utf8')).trim().split('\n'),['identity:query','identity:query','identity:query','details:enrich']);assert.match(response.headers.get('Cache-Control'),/no-store/);}finally{await f.close();}
});
for(const mode of ['invalid','overflow','timeout','mismatched','failed'])test('detail '+mode+' preserves both exact identity/source results',async()=>{
 const f=await fixture(mode,0,mode==='timeout'?120:7000);try{const response=await f.adapter(request());const body=await response.json();assert.equal(response.status,200);assert.equal(body.rows.length,2);assert.deepEqual(body.rows.map(x=>x.source_id),['fixture-1','fixture-2']);assert.equal(body.details.state,'unavailable');assert.equal(body.rows[0].ingredientStatus,'unclassified');assert.equal(body.hasMore,false);assert.equal(body.nextCursor,null);}finally{await f.close();}
});
test('status and identity-only queries never depend on a detail child',async()=>{
 const f=await fixture('failed');try{const status=await f.adapter(new Request('https://offmenu-identifiers.invalid/__dev/identifiers/status'));const s=await status.json();assert.equal(s.queryAvailable,true);assert.equal(s.identitySearchPlanVersion,2);assert.equal(s.detailAvailability,'not-assessed');const body=await (await f.adapter(request({include:undefined}))).json();assert.equal(body.rows.length,2);assert.equal(body.details,undefined);assert.deepEqual((await readFile(f.calls,'utf8')).trim().split('\n'),['identity:status','identity:query','identity:query','identity:query']);}finally{await f.close();}
});
test('per-observation lazy detail uses an exact current assertion and never substitutes another',async()=>{
 const f=await fixture();try{let body=await (await f.adapter(request({detailAssertionId:2}))).json();assert.equal(body.operation,'observation-detail');assert.equal(body.rows.length,1);assert.equal(body.rows[0].assertion_id,2);assert.equal(body.details.state,'loaded');body=await (await f.adapter(request({detailAssertionId:99}))).json();assert.equal(body.rows.length,0);assert.equal(body.details.error.reasonCode,'NO_CURRENT_SELECTED_OBSERVATION');assert.equal(body.operation,'observation-detail');}finally{await f.close();}
});
test('keyset pages retain all source variants and reject changed query bindings',async()=>{
 const f=await fixture();try{const first=await (await f.adapter(request({limit:1,include:undefined}))).json();assert.equal(first.rows[0].assertion_id,1);assert.equal(first.hasMore,true);const second=await (await f.adapter(request({limit:1,cursor:first.nextCursor,include:undefined}))).json();assert.equal(second.rows[0].assertion_id,2);assert.equal(second.hasMore,true);const final=await (await f.adapter(request({limit:1,cursor:second.nextCursor,include:undefined}))).json();assert.deepEqual(final.rows,[]);assert.equal(final.hasMore,false);assert.equal((await f.adapter(request({limit:1,cursor:first.nextCursor,generation:'different'}))).status,400);assert.equal((await f.adapter(request({databaseSha256:'0'.repeat(64)}))).status,409);}finally{await f.close();}
});
test('unknown key is scoped empty output and not a detail failure',async()=>{
 const f=await fixture();try{const body=await (await f.adapter(request({lexical_value:'UNKNOWN'}))).json();assert.deepEqual(body.rows,[]);assert.equal(body.identitySearchState,'available');assert.equal(body.details.state,'not-loaded');assert.equal((await readFile(f.calls,'utf8')).trim(),'identity:query\nidentity:query\nidentity:query');}finally{await f.close();}
});
test('two-request concurrency remains bounded across child phases',async()=>{
 const f=await fixture('valid',0.15,1000);try{const a=f.adapter(request()),b=f.adapter(request());await new Promise(r=>setTimeout(r,25));assert.equal((await f.adapter(request())).status,429);assert.deepEqual((await Promise.all([a,b])).map(r=>r.status),[200,200]);assert.equal((await f.adapter(request())).status,200);}finally{await f.close();}
});

const row=(assertion_id,lexical_value,disposition='source-asserted')=>({assertion_id,run_id:'selected-run',namespace:'barcode',lexical_value,disposition,source_id:'source-'+assertion_id});
test('representation forms preserve originals and require explicit UPC-E symbology',()=>{
 assert.deepEqual(identifierForms('barcode','00027000612323').map(f=>f.lexicalValue),['00027000612323']);
 assert.deepEqual(identifierForms('barcode','04252614').map(f=>f.lexicalValue),['04252614']);
 assert.deepEqual(identifierForms('barcode','04252614','UPC-E').map(f=>f.lexicalValue),['04252614','042100005264','0042100005264']);
 assert.deepEqual(identifierForms('barcode','04252615','UPC-E').map(f=>f.lexicalValue),['04252615']);
 assert.deepEqual(identifierForms('USDA-FDC','0042100005264').map(f=>f.lexicalValue),['0042100005264']);
 assert.deepEqual(identifierForms('barcode','036000291452').map(f=>f.lexicalValue),['036000291452','0036000291452']);
 assert.deepEqual(identifierForms('barcode','0036000291452').map(f=>f.lexicalValue),['0036000291452','036000291452']);
 assert.deepEqual(identifierForms('barcode','036000291453').map(f=>f.lexicalValue),['036000291453']);
});
test('independent lane cursors retain all source assertions and uncertainty without merging products',async()=>{
 const records=[row(1,'036000291452'),row(9,'036000291452'),row(2,'036000291452','unresolved'),row(3,'036000291452','invalid'),row(4,'0036000291452'),row(7,'0036000291452','unresolved')];
 const f=await fixture('valid',0,7000,records);try{
  const ids=[],matches=[];let cursor=null,body;
  for(let page=0;page<8;page++){
   body=await (await f.adapter(request({lexical_value:'036000291452',limit:1,cursor,include:undefined}))).json();
   ids.push(...body.rows.map(r=>r.assertion_id));matches.push(...body.identityMatches);
   if(!body.hasMore)break;assert.ok(body.nextCursor);cursor=body.nextCursor;
  }
  assert.deepEqual(ids,[1,9,2,3,4,7]);assert.equal(body.hasMore,false);
  assert.equal(body.identityQuery.originalLexicalValue,'036000291452');
  assert.equal(matches.find(m=>m.assertionId===4).matchType,'representation-alias');
  assert.equal(matches.find(m=>m.assertionId===2).disposition,'unresolved');
  assert.equal(body.identitySearchCoverage.physicalProductIdentityAsserted,false);
  assert.equal(body.identitySearchCoverage.ingredientQualificationAsserted,false);
 }finally{await f.close();}
});
test('an unresolved-lane failure preserves the exact page and resumes the failed lane',async()=>{
 const f=await fixture('valid',0,7000,[row(5,'036000291452')],'unresolved');try{
  const body=await (await f.adapter(request({lexical_value:'036000291452',include:undefined}))).json();
  assert.deepEqual(body.rows.map(r=>r.assertion_id),[5]);assert.equal(body.identitySearchState,'partial');assert.equal(body.hasMore,true);
  const cursor=JSON.parse(Buffer.from(body.nextCursor,'base64url'));
  assert.equal(cursor.lane,1);assert.equal(cursor.after,0);
  assert.equal(body.identitySearchCoverage.failures[0].disposition,'unresolved');
  const next=await (await f.adapter(request({lexical_value:'036000291452',cursor:body.nextCursor,include:undefined}))).json();
  assert.deepEqual(next.rows,[]);assert.equal(next.identitySearchState,'partial');assert.equal(next.nextCursor,body.nextCursor);
 }finally{await f.close();}
});
test('alias observation detail binds exact lexical and disposition; arbitrary aliases and cursor reuse are rejected',async()=>{
 const f=await fixture('valid',0,7000,[row(8,'0036000291452')]);try{
  const body=await (await f.adapter(request({lexical_value:'036000291452',detailAssertionId:8,detailLexicalValue:'0036000291452',detailDisposition:'source-asserted'}))).json();
  assert.equal(body.rows[0].assertion_id,8);assert.equal(body.rows[0].lexical_value,'0036000291452');assert.equal(body.identityMatches[0].matchType,'representation-alias');
  assert.equal((await f.adapter(request({detailAssertionId:8,detailLexicalValue:'027000612323'}))).status,400);
  const page=await (await f.adapter(request({lexical_value:'036000291452',limit:1,include:undefined}))).json();
  assert.equal((await f.adapter(request({lexical_value:'036000291452',limit:1,cursor:page.nextCursor,symbology:'UPC-A',include:undefined}))).status,400);
 }finally{await f.close();}
});

test('actual wired UI and native host agree on release pins, aliases, lazy failure and pantry reference',async()=>{
 const original='036000291452',alias='0036000291452';
 const records=[row(5,original),row(7,alias,'unresolved')].map((r,i)=>({...r,
  run_id:'worker57-full-retained-identifiers-v1',input_id:'synthetic:source-input',record_ordinal:i+1,
  source_id:'off',release_id:'synthetic-release',source_record_id:String(r.assertion_id),native_record_id:'synthetic:'+r.assertion_id}));
 const f=await fixture('failed',0,7000,records);
 const fetchImpl=(path,options)=>{
  assert.match(path,/^\/__dev\/identifiers(?:\/status)?$/);
  return f.adapter(new Request('https://offmenu-identifiers.invalid'+path,options));
 };
 try{
  const page=await lookupIdentityPage(original,41,{fetchImpl});
  assert.notEqual(page.status,'unavailable');assert.equal(page.matches.length,2);
  assert.equal(DETAIL_SELECTION,'d9a08c3b2b9eec880418b8108d60c177a253b53802e8ea0453eb8fd502498290');
  assert.equal((await readFile(f.calls,'utf8')).includes('details:enrich'),false);
  const selected=page.matches.find(m=>m.identifier.assertion_id===7),ref=uiReference(selected,page);
  assert.equal(ref.matchType,'representation-alias');assert.equal(ref.disposition,'unresolved');
  assert.equal(ref.originalLexicalValue,original);assert.equal(ref.sourceLexicalValue,alias);
  const detail=await lookupExactObservationDetail(ref,41,{fetchImpl});
  assert.equal(detail.status,'detail-unavailable');assert.deepEqual(detail.sourceObservationReference,ref);
  assert.deepEqual(page.matches.map(m=>m.identifier.assertion_id),[5,7]);
  const lot=validateLot({barcode:original,name:'Synthetic source observation',ingredient:'unmapped',quantity:1,
   unit:'count',needsReview:true,sourceObservationReference:ref});
  assert.deepEqual(lot.sourceObservationReference,ref);
 }finally{await f.close();}
});
