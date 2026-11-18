import test from 'node:test';
import assert from 'node:assert/strict';
import {setupData} from '../../apps/web/src/data-ui.js';

// Exercise the mounted kitchen Data-tab handlers without a real browser profile,
// network, storage, provider, credentials or dataset.
const fixed=Date.parse('2030-01-01T00:00:00Z');
function row(id,provenance={},fields={}){
 return {schemaVersion:'1.0',id,kind:'product',countries:[],data:{name:id},provenance:{
  sourceId:'personal-import',attribution:'Authored fixture',license:'Synthetic only',
  privateUseConfirmed:true,visibility:'private',...provenance},...fields};
}
function node(tag='div'){
 return {tag,children:[],textContent:'',dataset:{},value:'',append(...items){this.children.push(...items);},
  replaceChildren(...items){this.children=items;this.textContent='';},close(){},setAttribute(){}};
}
function nodes(n){return [n,...n.children.flatMap(nodes)];}
function fixture(t,{dataRecords=[],signed=false,demo=false,responses=[]}={}){
 const elements=new Map(),$=id=>{if(!elements.has(id))elements.set(id,node());return elements.get(id);};
 const mounted={getElementById:$,createElement:node,createTextNode:text=>({...node(),textContent:text})};
 const originals=Object.getOwnPropertyDescriptors(globalThis),calls=[],downloads=[],recipes=[];
 t.after(()=>{for(const key of ['document','fetch'])if(originals[key])Object.defineProperty(globalThis,key,originals[key]);else delete globalThis[key];});
 globalThis.document=mounted;globalThis.fetch=async path=>{
  assert.ok(responses.length,'unexpected request');calls.push(path);
  const response=responses.shift();return {ok:true,json:async()=>response};
 };
 const state={profile:{dataRecords},user:signed?{id:'synthetic-owner'}:null,demo,persists:0};
 const ui=setupData({getData:()=>({profile:state.profile,inventory:[]}),getUser:()=>state.user,isDemo:()=>state.demo,
  persist:()=>{state.persists++;},refreshSession:async()=>{},download:(_name,data)=>downloads.push(JSON.parse(data)),addRecipe:r=>recipes.push(r)});
 ui.reset();$('data-rights').checked=true;$('data-language').value='ui';$('source-country').value='AU';
 const shown=()=>$('data-results').children.filter(n=>n.tag==='article').map(n=>JSON.parse(nodes(n).find(c=>c.tag==='pre').textContent).id);
 return {$,shown,ui,state,calls,downloads,recipes,open:()=>$('data-my-records').onclick()};
}

for(const demo of [true,false])test('saved '+(demo?'demo':'guest')+' view withholds denied rows and retains allowed peers without deleting anything',async t=>{
 const deny=(name,p,fields)=>row('withheld-'+name,p,fields);
 const rows=[row('allowed-global'),deny('expiry',{retainUntil:'2000-01-01'}),deny('access',{accessExpiresAt:'invalid'}),
  deny('withdrawn',{status:'withdrawn'}),deny('quarantine',{status:'quarantined'}),
  deny('dependency',{dependencies:[{allowed:true,retainUntil:'invalid'}]}),deny('unknown',{sourceId:'no-registered-policy'}),
  deny('unconfirmed',{privateUseConfirmed:false}),deny('sensitive',{}, {kind:'healthObservation'}),
  deny('other-market',{}, {countries:['NZ']}),null,deny('shape',{dependencies:{wrong:true}}),row('allowed-au',{}, {countries:['AU']})];
 const original=structuredClone(rows),f=fixture(t,{dataRecords:rows,demo,signed:demo});
 await f.open();assert.deepEqual(f.shown(),['allowed-global','allowed-au']);assert.equal(f.$('data-notice').textContent,'2 private profile records.');
 assert.equal(f.calls.length,0);assert.equal(f.state.persists,0);assert.deepEqual(rows,original);
 f.$('data-export').onclick();assert.deepEqual(f.downloads[0].records.map(r=>r.id),f.shown());
});

test('open local display removes dependent rows on their exact deadline without changing storage',async t=>{
 t.mock.timers.enable({apis:['Date','setTimeout'],now:fixed});
 const rowAt=(id,key,ms)=>row(id,{[key]:new Date(fixed+ms).toISOString()});
 const stored=[rowAt('access','accessExpiresAt',100),rowAt('retention','retainUntil',300),row('dependency',{dependencies:[
  {allowed:true},{allowed:true,retainUntil:new Date(fixed+200).toISOString()}]})];
 const f=fixture(t,{dataRecords:stored});await f.open();
 assert.deepEqual(f.shown(),['access','retention','dependency']);
 t.mock.timers.tick(100);assert.deepEqual(f.shown(),['retention','dependency']);
 t.mock.timers.tick(100);assert.deepEqual(f.shown(),['retention']);
 t.mock.timers.tick(100);assert.deepEqual(f.shown(),[]);assert.equal(f.$('data-notice').textContent,'0 private profile records.');
 assert.equal(stored.length,3);assert.equal(f.state.persists,0);
});

test('export and derive re-read approved local versions without upgrading a checked box into a grant',async t=>{
 const stored=[row('one'),row('original'),row('recipe',{}, {kind:'recipe'})];const f=fixture(t,{dataRecords:stored});await f.open();
 const button=nodes(f.$('data-results')).find(n=>n.tag==='button');assert.ok(button);
 stored[2].provenance.status='withdrawn';button.onclick();assert.deepEqual(f.recipes,[]);
 stored[1].data.name='replaced';stored.push(row('new'));f.$('data-export').onclick();
 assert.deepEqual(f.downloads[0].records.map(r=>r.id),['one']);assert.deepEqual(f.shown(),['one']);
 await f.open();assert.deepEqual(f.shown(),['one','original','new']);
});

test('a newly opened profile or server-authorized account is not governed by a prior local view',async t=>{
 const approved=row('ok-by-server',{sourceId:'custom-policy',privateUseConfirmed:false});
 const f=fixture(t,{dataRecords:[row('guest')],responses:[{records:[],nextCursor:'page2'},{records:[approved]}]});
 await f.open();f.state.user={id:'synthetic-owner'};f.ui.reset();assert.deepEqual(f.shown(),[]);
 await f.open();assert.equal(f.calls.length,2);assert.deepEqual(f.shown(),['ok-by-server']);f.$('data-language').onchange();assert.deepEqual(f.shown(),['ok-by-server']);
});

test('an unsaved import preview is not a stored display or persist grant',async t=>{
 const f=fixture(t,{dataRecords:[row('old')]});await f.open();
 f.$('data-file').files=[{name:'fixture.json',size:10,text:async()=>JSON.stringify([row('preview',{privateUseConfirmed:false,sourceId:'no-reviewed-policy'})])}];
 await f.$('data-file').onchange();assert.deepEqual(f.shown(),['preview']);f.$('data-language').onchange();assert.deepEqual(f.shown(),['preview']);
 await f.$('data-save').onclick();assert.deepEqual(f.state.profile.dataRecords.map(r=>r.id),['old']);assert.deepEqual(f.downloads,[]);
});

test('country controls immediately narrow the open local batch; broadening requires a fresh load',async t=>{
 const stored=[row('au',{}, {countries:['AU']}),row('nz',{}, {countries:['NZ']}),row('global')];
 const f=fixture(t,{dataRecords:stored});f.$('source-country').value='';await f.open();assert.deepEqual(f.shown(),['au','nz','global']);
 f.$('source-country').value='NZ';f.$('source-country').onchange();assert.deepEqual(f.shown(),['nz','global']);
 f.$('source-global').onclick();assert.deepEqual(f.shown(),['nz','global']);
 f.state.profile.country='AU';f.$('source-use-profile').onclick();assert.deepEqual(f.shown(),['global']);
 await f.open();assert.deepEqual(f.shown(),['au','global']);assert.equal(stored.length,3);assert.equal(f.state.persists,0);
});

test('a detached local recipe button cannot deliver a row to a replaced view or different owner',async t=>{
 const f=fixture(t,{dataRecords:[row('recipe',{}, {kind:'recipe'})]});await f.open();
 const first=nodes(f.$('data-results')).find(n=>n.tag==='button');f.$('data-language').onchange();
 first.onclick();assert.deepEqual(f.recipes,[]);
 const current=nodes(f.$('data-results')).find(n=>n.tag==='button');current.onclick();assert.deepEqual(f.recipes.map(r=>r.id),['recipe']);
 const saved=nodes(f.$('data-results')).find(n=>n.tag==='button');f.state.user={id:'other'};f.ui.reset();
 saved.onclick();assert.deepEqual(f.recipes.map(r=>r.id),['recipe']);assert.deepEqual(f.shown(),[]);
});
