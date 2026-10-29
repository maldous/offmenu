import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {loadPriceObservations,renderSavedPriceObservations} from '../../public/saved-price-observations.js';
import {normalizeCSV} from '../../public/unified-data.js';
const root=new URL(process.env.SAVED_PRICE_V1?'../../../saved-price-lookup-20261026/candidate/public/':'../../public/',import.meta.url);
const app=readFileSync(new URL('app.js',root),'utf8'),insights=readFileSync(new URL('insights-ui.js',root),'utf8');
function node(tag='div'){return {tag,children:[],textContent:'',value:'',append(...items){this.children.push(...items);},replaceChildren(...items){this.children=items;this.textContent='';}};}
function flatten(n){return [n.textContent,...n.children.flatMap(flatten)].join(' ');}
function rows(owner){return normalizeCSV('id,name,code,amount,currency,date,store\n'+owner+',Synthetic,00123,1,AUD,2026-10-01,'+owner+' private store\n',{id:'personal-import',name:owner+' private source',license:'Synthetic only',url:'https://example.invalid'},{kind:'priceObservation',id:'id',name:'name',barcode:'code',price:'amount',currency:'currency',date:'date',retailer:'store',country:'AU'}).map(r=>({...r,provenance:{...r.provenance,privateUseConfirmed:true}}));}
function fixture(){
 const nodes=new Map(),$=id=>{if(!nodes.has(id))nodes.set(id,node());return nodes.get(id);};$('barcode').value=$('integration-barcode').value='00123';$('source-country').value='AU';
 const context={$,document:{createElement:node},profile:{country:'AU',dataRecords:rows('A')},requestIdentity:{owner:'A'},shopsRequest:0,demoMode:false,user:{id:'A'},authResolved:true,recoveryMode:false,KEY:'',PRODUCTS:'',RECIPES:'',PROFILE:'',SELECTIONS:'',revision:0,dirty:false,
  Number,Error,t:x=>x,names:{of:x=>x},localStorage:{getItem:()=>null},setLocalizedText:(n,s)=>{n.textContent=s;},card:(target,title,body)=>target.append({...node(),textContent:title+' '+body}),text:(tag,content)=>({...node(tag),textContent:content}),
  loadPriceObservations,renderSavedPriceObservations};
 for(const key of ['care','recipeCommunity','communityAI','personalAI','administration','adminOperations','dataUi','accountBackup'])context[key]={reset(){}};
 context.getIdentity=()=>context.requestIdentity;context.data=()=>({profile:context.profile});context.getData=context.data;
 context.boundFetch=context.request=async()=>({ok:true,json:async()=>({items:[],records:[]})});
 const script=vm.createContext(context);let start=insights.indexOf("$('integration-prices').onclick="),end=insights.indexOf('\nreturn {render',start);
 vm.runInContext('let priceRequest=0;'+insights.slice(start,end),script);
 context.insights={resetPrices:()=>vm.runInContext("typeof resetPrices==='function'&&resetPrices()",script)};
 start=app.indexOf("$('shops').onclick=");end=app.indexOf('\nfunction download(',start);vm.runInContext(app.slice(start,end),script);
 start=app.indexOf('function switchAccount(');end=app.indexOf('\nasync function initAuth(',start);vm.runInContext(app.slice(start,end),script);
 return {context,$,script,click:async()=>{const old=globalThis.document;globalThis.document=context.document;try{await $('shops').onclick();await $('integration-prices').onclick();}finally{globalThis.document=old;}},contents:()=>[$('prices'),$('integration-price-results')].map(flatten)};
}
for(const transition of ['B','logout','demo'])test('rendered A prices are cleared by actual switchAccount '+transition+' and a subsequent B lookup is isolated',async()=>{
 const f=fixture();await f.click();for(const output of f.contents())assert.match(output,/A private/);
 f.context.demoMode=transition==='demo';f.context.switchAccount(transition==='logout'?null:{id:transition==='demo'?'A':'B'});
 for(const output of f.contents())assert.equal(output.trim(),'');
 f.context.demoMode=false;f.context.switchAccount({id:'B'});f.context.profile={country:'AU',dataRecords:rows('B')};await f.click();
 for(const output of f.contents()){assert.match(output,/B private/);assert.doesNotMatch(output,/A private/);}
});
test('transition invalidates both pending handler generations before an old completion can alter the cleared panels',async()=>{
 const f=fixture(),pending=[];f.context.boundFetch=f.context.request=()=>new Promise(resolve=>pending.push(resolve));
 const old=globalThis.document;globalThis.document=f.context.document;
 try{
  const shops=f.$('shops').onclick(),insight=f.$('integration-prices').onclick();await Promise.resolve();
  assert.ok(pending.length>=2);f.context.switchAccount({id:'B'});for(const output of f.contents())assert.equal(output.trim(),'');
  for(const resolve of pending)resolve({ok:true,json:async()=>({items:[],records:rows('A')})});await Promise.all([shops,insight]);
  for(const output of f.contents())assert.equal(output.trim(),'');
 }finally{globalThis.document=old;}
});
