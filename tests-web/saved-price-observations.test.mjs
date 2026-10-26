import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {normalizeCSV} from '../public/unified-data.js';
const root=new URL(process.env.SAVED_PRICE_PREIMAGE?'../../preimage/public/':'../public/',import.meta.url);
const source={id:'personal-import',name:'Synthetic import',license:'Authored synthetic only',url:'https://example.invalid'};
function records(){return normalizeCSV('id,name,code,amount,currency,date,store\na,Example,00123,0,EUR,2026-10-01,A\nb,Example,00123,3,EUR,2026-10-02,B\n',source,{kind:'priceObservation',id:'id',name:'name',barcode:'code',price:'amount',currency:'currency',date:'date',retailer:'store',country:'AU'}).map(r=>({...r,provenance:{...r.provenance,privateUseConfirmed:true}}));}
function node(tag='div'){return {tag,children:[],textContent:'',value:'',append(...items){this.children.push(...items);},replaceChildren(...items){this.children=items;this.textContent='';}};}
function flatten(n){return [n.textContent,...n.children.flatMap(flatten)].join(' ');}
async function click({upstreamFails=false}={}){
 const nodes=new Map(),$=id=>{if(!nodes.has(id))nodes.set(id,node());return nodes.get(id);};
 $('integration-barcode').value='00123';$('source-country').value='AU';
 const profile={dataRecords:records()},context={$,document:{createElement:node},getData:()=>({profile}),data:()=>({profile}),getIdentity:()=>identity,request,loadPriceObservations:module.loadPriceObservations,renderSavedPriceObservations:module.renderSavedPriceObservations,t:x=>x,text:(tag,content)=>({...node(tag),textContent:content}),setLocalizedText:(n,s)=>{n.textContent=s;},apiError:v=>Error(v.error),AbortSignal,fetch:request};
 const identity={owner:null};async function request(path){if(upstreamFails)throw Error('Synthetic upstream offline');return {ok:true,json:async()=>({items:[]})};}
 const s=readFileSync(new URL('insights-ui.js',root),'utf8'),start=s.indexOf("$('integration-prices').onclick="),end=s.indexOf('\nreturn {render',start);
 vm.runInNewContext('let priceRequest=0;'+s.slice(start,end),context);const previous=globalThis.document;globalThis.document=context.document;try{await $('integration-prices').onclick();return flatten($('integration-price-results'));}finally{globalThis.document=previous;}
}
let module={};try{module=await import('../public/saved-price-observations.js');}catch(e){if(e.code!=='ERR_MODULE_NOT_FOUND')throw e;}
test('actual Insights handler displays both saved dated observations',async()=>{const output=await click();assert.match(output,/2026-10-01/);assert.match(output,/2026-10-02/);assert.match(output,/personal-import/);assert.match(output,/not verified current stock/);});
test('actual Insights handler retains saved prices when optional upstream fails',async()=>{const output=await click({upstreamFails:true});assert.match(output,/2026-10-01/);assert.match(output,/unavailable/i);});
test('selector preserves lexical joins, native IDs and rights without inferring matches',()=>{
 const rows=records();rows[0].data.taxIncluded=null;rows[0].data.promotion=false;rows[0].data.loyalty={required:true};
 const bad=[{...rows[0],id:'expired',provenance:{...rows[0].provenance,retainUntil:'2000-01-01'}},{...rows[0],id:'held',provenance:{...rows[0].provenance,status:'quarantined'}},{...rows[0],id:'unconfirmed',provenance:{...rows[0].provenance,privateUseConfirmed:false}},{...rows[0],id:'dependency',provenance:{...rows[0].provenance,dependencies:[{allowed:false}]}},{...rows[0],id:'numeric',data:{...rows[0].data,identifiers:[{system:'barcode',value:123}]}}];
 assert.deepEqual(module.selectSavedPriceObservations([...rows,...bad],{barcode:'00123',country:'AU'}),rows);
 assert.equal(module.selectSavedPriceObservations(rows,{barcode:'123'}).length,0);assert.equal(module.selectSavedPriceObservations(rows,{barcode:'00123',country:'NZ'}).length,0);
 assert.equal(rows[0].provenance.recordId,'a');assert.equal(rows[0].data.amount,0);assert.equal(rows[0].data.promotion,false);
});
test('owner cloud pagination includes later matches and preserves reviewed server display policy',async()=>{
 const identity={owner:'synthetic-owner'},calls=[],rows=records();rows[1].provenance.sourceId='custom-server-policy';
 const result=await module.loadPriceObservations({barcode:'00123',country:'AU',profile:{dataRecords:[rows[0]]},getIdentity:()=>identity,request:async path=>{calls.push(path);if(path.startsWith('/api/prices'))throw Error('offline');const second=new URL(path,'https://example.invalid').searchParams.get('cursor');return {ok:true,json:async()=>({records:second?[rows[1]]:[rows[0]],nextCursor:second?null:'page2'})};}});
 assert.equal(result.saved.length,2);assert.equal(calls.filter(p=>p.startsWith('/api/data/records')).length,2);assert.ok(result.upstreamError);assert.ok(calls.every(p=>!p.includes('synthetic-owner')));
});
test('guest and demo load browser records without requesting private account records',async()=>{
 const calls=[],result=await module.loadPriceObservations({barcode:'00123',profile:{dataRecords:records()},getIdentity:()=>null,request:async p=>{calls.push(p);return {ok:true,json:async()=>({items:[]})};}});assert.equal(result.saved.length,2);assert.deepEqual(calls,['/api/prices?barcode=00123']);
});
test('account transition while body is pending rejects the entire result',async()=>{
 let identity={owner:'a'};await assert.rejects(module.loadPriceObservations({barcode:'00123',profile:{dataRecords:records()},getIdentity:()=>identity,request:async()=>({ok:true,json:async()=>{identity={owner:'b'};return {records:records(),items:[]};}})}),/Account changed/);
});

test('saved account failure does not hide eligible browser observations or upstream results',async()=>{
 const identity={owner:'synthetic'},rows=records();const result=await module.loadPriceObservations({barcode:'00123',profile:{dataRecords:rows},getIdentity:()=>identity,request:async path=>{if(path.startsWith('/api/data'))return {ok:false,json:async()=>({error:'unavailable'})};return {ok:true,json:async()=>({results:[{id:0,price:0,currency:'EUR',date:'2026-10-03'}],offmenu_stale:true})};}});
 assert.equal(result.saved.length,2);assert.ok(result.savedError);assert.equal(result.upstream.items[0].id,0);assert.equal(result.upstream.items[0].price,0);assert.equal(result.upstream.offmenu_stale,true);
});
test('repeated account cursor terminates with an explicit partial-result warning',async()=>{
 const identity={owner:'synthetic'},result=await module.loadPriceObservations({barcode:'00123',profile:{},getIdentity:()=>identity,request:async path=>({ok:true,json:async()=>path.startsWith('/api/data')?{records:records(),nextCursor:'same'}:{items:[]}})});
 assert.equal(result.saved.length,2);assert.match(result.savedError.message,/cursor/);
});
for(const upstreamFails of [false,true])test('actual shops handler displays saved observations with upstream '+(upstreamFails?'failure':'success'),async()=>{
 const nodes=new Map(),$=id=>{if(!nodes.has(id))nodes.set(id,node());return nodes.get(id);};$('barcode').value='00123';
 const profile={country:'AU',dataRecords:records()},identity={owner:null};
 const context={$,document:{createElement:node},profile,requestIdentity:identity,shopsRequest:0,t:x=>x,names:{of:x=>x},Error,
  boundFetch:async()=>{if(upstreamFails)throw Error('offline');return {ok:true,json:async()=>({items:[]})};},
  loadPriceObservations:module.loadPriceObservations,renderSavedPriceObservations:module.renderSavedPriceObservations,
  setLocalizedText:(n,s)=>{n.textContent=s;},card:(target,title,body)=>target.append({...node(),textContent:title+' '+body}),
  jsonFetch:async()=>{if(upstreamFails)throw Error('offline');return {items:[]};}};
 const source=readFileSync(new URL('app.js',root),'utf8'),start=source.indexOf("$('shops').onclick="),end=source.indexOf("\nfunction download(",start);
 vm.runInNewContext(source.slice(start,end),context);const previous=globalThis.document;globalThis.document=context.document;
 try{await $('shops').onclick();const output=flatten($('prices'));assert.match(output,/2026-10-01/);assert.match(output,/2026-10-02/);assert.match(output,/not verified current stock/);if(upstreamFails)assert.match(output,/unavailable/);}finally{globalThis.document=previous;}
});
