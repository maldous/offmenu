import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {recordPermission} from '../public/record-policy.js';
import {record,normalizePrices} from '../public/unified-data.js';
import {sourceById} from '../public/sources.js';
import {storePrivateRecords,listPrivateRecords,providerDataRoutes} from '../cloud/provider-data.mjs';
import {catalogueRoutes} from '../cloud/catalogue.mjs';
import {enrichmentRoutes} from '../cloud/enrichment.mjs';
import {calculateBasket,compareBaskets,cookedComposition} from '../public/basket-model.js';
import {cookMeal,serveBatch,reconcileCookedStock,validateBatches} from '../public/cooking-model.js';
import {kitchenProjection} from '../public/sync-model.js';
import {healthStatistics,validateHealthRecords} from '../public/health-model.js';
import {qualify} from '../public/evidence-model.js';
import {integrationRoutes} from '../cloud/integrations.mjs';
const spec=JSON.parse(readFileSync(new URL('../research/OffMenu_Basket_Normalization_Spec.json',import.meta.url)));
function database(){
 const db=new DatabaseSync(':memory:');
 for(const file of ['schema.sql','catalogue-schema.sql'])db.exec(readFileSync(new URL('../cloud/'+file,import.meta.url),'utf8'));
 const env={DB:{prepare(sql){const stmt=args=>({async first(){return db.prepare(sql).get(...args)||null;},async all(){return {results:db.prepare(sql).all(...args)};},async run(){return db.prepare(sql).run(...args);}});return {...stmt([]),bind(...args){return stmt(args);}}}}};return {db,env};
}
const origin='https://app.example';
const request=(path,method='GET',body)=>new Request(origin+path,{method,headers:{Origin:origin},body:body?JSON.stringify(body):undefined});
const opts={verifiedUser:async()=>({id:'alice'}),boundedJSON:r=>r.json()};
const recipe={id:'rice',title:'Rice',servings:2,source:'offmenu',license:'Original',instructions:['Cook'],ingredients:[{ingredient:'rice',quantity:200,unit:'g'}]};
const raw=[{id:'raw',barcode:'12345678',name:'Rice',ingredient:'rice',quantity:400,unit:'g',location:{area:'Pantry',shelf:'Top'}}];
const nutrient=(value,unit,definition='same')=>({value,unit,definition,state:'prepared',basisAmount:100,basisUnit:'g',sourceId:'synthetic',status:'analytical'});
const basket=()=>({id:'A',track:'synthetic',state:'prepared',lines:[{id:'a',edibleG:100,state:'prepared',nutrients:{energy_kcal:nutrient(100,'kcal'),protein_g:nutrient(5,'g')},groupFractions:{fruit:.5,vegetables:.5},groupDefinition:'groups/1'}]});
test('unknown provider rights cannot be granted by a checkbox; retained dependencies and clocks govern reuse',()=>{
 const r=record('product','1',{name:'x'},sourceById('edamam'),{visibility:'private'});
 for(const action of ['persist','export','derive'])assert.equal(recordPermission(r,{action,confirmed:true}).allowed,false);
 r.provenance.sourceId='usda';r.provenance.retainUntil='2000-01-01';assert.equal(recordPermission(r).allowed,false);
 delete r.provenance.retainUntil;r.provenance.dependencies=[{allowed:false}];assert.equal(recordPermission(r).allowed,false);
});
test('source-policy withdrawal immediately withholds private reads and export',async()=>{
 const {db,env}=database();const rows=normalizePrices({items:[{id:1,price:5,currency:'AUD'}]},sourceById('prices'));
 await storePrivateRecords(env,'alice',rows);assert.equal((await listPrivateRecords(env,'alice')).length,1);
 db.prepare('INSERT INTO source_policies VALUES(?,?,?,?)').run('prices',JSON.stringify({version:'withdrawn',actions:[],audiences:[]}),2,0);
 assert.equal((await listPrivateRecords(env,'alice',{action:'export'})).length,0);
 await assert.rejects(()=>storePrivateRecords(env,'alice',rows));
});
test('provider disconnect invalidates only the caller’s retained source records',async()=>{
 const {db,env}=database();const row=record('product','1',{name:'x'},sourceById('usda'),{visibility:'private'});
 await storePrivateRecords(env,'alice',[row]);await storePrivateRecords(env,'bob',[row]);
 const r=await providerDataRoutes(request('/api/data/connections','DELETE',{sourceId:'usda'}),env,opts);
 assert.equal(r.status,200);assert.equal((await listPrivateRecords(env,'alice')).length,0);assert.equal((await listPrivateRecords(env,'bob')).length,1);
});
test('private health imports require explicit consent; same observations deduplicate by source and member',async()=>{
 const {env}=database();const data={records:[{type:'weight',value:80,unit:'kg',observedAt:'2026-10-13',source:'manual'}]};
 const call=b=>catalogueRoutes(request('/api/personal/health','POST',b),env,opts);
 assert.equal((await call({id:'a',revision:0,data})).status,400);
 assert.equal((await call({id:'a',revision:0,data,consent:{accepted:true,version:'offmenu-health/1'}})).status,201);
 const a=validateHealthRecords(data.records),b=validateHealthRecords(data.records);
 assert.equal(healthStatistics([...a,...b]).weight.count,1);
 assert.equal(healthStatistics([...a,...b.map(r=>({...r,memberId:'other'}))]).weight.count,2);
});
test('generic data scope cannot read health observations; sensitive scopes are explicit',async()=>{
 const {db,env}=database();const row=record('healthObservation','1',{value:80},sourceById('usda'),{visibility:'private'});
 db.prepare('INSERT INTO unified_records VALUES(?,?,?,?,?,?,?,?)').run('alice',row.id,row.kind,'usda','[]',JSON.stringify(row),'now','');
 assert.equal((await listPrivateRecords(env,'alice')).length,0);
 const issued=await(await integrationRoutes(request('/api/integrations/tokens','POST',{resource:'api'}),env,opts)).json();
 assert.ok(!issued.scope.includes('health:read'));
 const req=new Request(origin+'/api/v1/health',{headers:{Authorization:'Bearer '+issued.access_token}});
 assert.equal((await integrationRoutes(req,env,opts)).status,403);
});
test('incompatible energy definitions withhold all energy denominators and rank',()=>{
 const b=basket();b.lines.push({...structuredClone(b.lines[0]),id:'b'});b.lines[1].nutrients.energy_kcal.definition='other';
 const r=calculateBasket(b,spec.metric_dictionary);assert.equal(r.energyKcal,null);assert.equal(r.metrics.protein_g.total,10);assert.equal(r.metrics.protein_g.per1000kcal,null);assert.equal(r.metrics.protein_g.rankEligible,false);
});
test('food-group denominators require full fraction evidence; preparation and purpose gate comparisons',()=>{
 const b=basket(),r=calculateBasket(b,spec.metric_dictionary);assert.equal(r.foodGroupMetrics.fruit.per1000kcal,500);
 const c=structuredClone(b);c.purpose='another';assert.equal(compareBaskets(r,calculateBasket(c,spec.metric_dictionary),'protein_g').status,'incomparable');
 delete b.lines[0].groupDefinition;assert.equal(calculateBasket(b,spec.metric_dictionary).foodGroupMetrics.fruit.total,null);
 assert.equal(cookedComposition({rawG:100,nutrients:{protein_g:{value:10}},yieldFactor:2,retentionFactors:{protein_g:.8}}).nutrients.protein_g.value,4);
});
test('unknown consumption remains unknown, removal reconciles batches, and split cooked lots draw once',()=>{
 const c=cookMeal({recipe,inventory:raw,products:{},servings:2,date:'2026-10-13',mutationId:'batch'});
 const removed=c.inventory.filter(l=>!l.cookBatchId);const reconciled=reconcileCookedStock([c.batch],removed,{date:'2026-10-13'});
 assert.equal(reconciled[0].remaining,0);assert.equal(reconciled[0].events[0].quantity,2);assert.ok(validateBatches(reconciled));
 assert.throws(()=>serveBatch({batch:c.batch,inventory:removed,portions:1,date:'2026-10-13'}));
 const s=serveBatch({batch:c.batch,inventory:c.inventory,portions:1,date:'2026-10-13'});
 assert.equal(s.log.intakeKnown,false);assert.equal(s.batch.events[0].unknownRemainder,1);
 const cooked=c.inventory.find(l=>l.cookBatchId),split=[...c.inventory.filter(l=>!l.cookBatchId),{...cooked,quantity:1},{...cooked,id:'second',quantity:1}];
 const served=serveBatch({batch:c.batch,inventory:split,portions:.5,completion:100,date:'2026-10-13'});
 assert.equal(served.inventory.filter(l=>l.cookBatchId).reduce((n,l)=>n+l.quantity,0),1.5);
});
test('shared projection retains stock accounting without personal intake or private provider nutrients',()=>{
 const c=cookMeal({recipe,inventory:raw,products:{},servings:2,date:'2026-10-13',mutationId:'batch'});
 const s=serveBatch({batch:c.batch,inventory:c.inventory,portions:1,completion:50,remainder:'saved',memberId:'private-person',date:'2026-10-13'});
 const projected=kitchenProjection({inventory:s.inventory,recipes:[],products:{x:{name:'Rice',nutriments:{protein:3},nutritionProvenance:{visibility:'private'},privateToken:'SECRET'}},profile:{batches:[s.batch]}});
 assert.equal(projected.profile.batches[0].events[0].quantity,.5);assert.ok(!JSON.stringify(projected).includes('private-person'));assert.equal(projected.products.x.nutriments,undefined);assert.equal(projected.products.x.privateToken,undefined);
});
test('quarantined supplier assertions cannot pass qualification',()=>{
 assert.equal(qualify({predicate:'certified',value:true},[{predicate:'certified',value:true,matchStatus:'verified',status:'quarantined'}]).status,'unknown');
});
test('public enrichment caches only within unchanged source policy and denies withdrawal',async()=>{
 const {db,env}=database(),oldFetch=globalThis.fetch;let fetches=0;
 globalThis.fetch=async()=>{fetches++;return Response.json({data:[{id:'lei',attributes:{entity:{legalName:{name:'Example'}}}}]});};
 try{
  const route=()=>enrichmentRoutes(request('/api/catalogue/enrich?source=gleif&query=Example'),env,opts);
  assert.equal((await route()).status,200);assert.equal((await(await route()).json()).cache,'hit');assert.equal(fetches,1);
  db.prepare("UPDATE source_policies SET active=0 WHERE id='gleif'").run();assert.equal((await route()).status,403);assert.equal(fetches,1);
  assert.equal(db.prepare('SELECT count(*) AS n FROM resolver_leases').get().n,0);
 }finally{globalThis.fetch=oldFetch;}
});

import {generateHouseholdDay} from '../public/household-model.js';
test('automatic planning withholds menus with unresolved strict dietary evidence',()=>{const member={id:'a',name:'A',portion:1,advisors:[],restrictions:[{type:'allergy',term:'peanut'}]};assert.equal(generateHouseholdDay([recipe],raw,{},[member],'2026-10-13').length,0);});

import handler from '../cloud/handler.mjs';
test('the full Worker dispatcher reaches public enrichment instead of catalogue 404',async()=>{const {env}=database(),original=globalThis.fetch;globalThis.fetch=async()=>Response.json({data:[]});try{const r=await handler.fetch(request('/api/catalogue/enrich?source=gleif&query=Example'),env);assert.equal(r.status,200);assert.equal((await r.json()).cache,'miss');}finally{globalThis.fetch=original;}});
