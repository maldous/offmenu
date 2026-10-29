import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {localRetainedCategorySelected,lookupLocalRetainedCategory} from '../../public/production-scanner/local-retained-category-client.js';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const {parse}=createRequire(import.meta.url)('acorn');
const root=process.env.OFFMENU_SCANNER_SOURCE_ROOT||path.resolve(new URL('../..',import.meta.url).pathname);
const sourcePath=path.join(root,'public/production-scanner/shelf-scanner.js'),source=fs.readFileSync(sourcePath,'utf8');
const nodes=parse(source,{ecmaVersion:'latest',sourceType:'module'}).body;
let attemptedNetwork=0;const originalFetch=globalThis.fetch;globalThis.fetch=async()=>{attemptedNetwork++;throw Error('Network disabled in generated scanner checks');};
const lookup=await import(pathToFileURL(path.join(root,'public/production-scanner/scanner-production-lookup.js')));globalThis.fetch=originalFetch;
const handoff=await import(pathToFileURL(path.join(root,'public/scanner-kitchen-handoff.js')));
class Element{constructor(){this.children=[];this.dataset={};this.value='';this.textContent='';this.hidden=false;this.open=false;}append(...xs){this.children.push(...xs);}replaceChildren(...xs){this.children=[...xs];}setAttribute(k,v){this[k]=v;}showModal(){this.open=true;}close(){this.open=false;}}
function harness(query=lookup.lookupIdentifiers){
 const elements=new Map(),$=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};let storageWrites=0;
 const storage={getItem:()=>null,setItem(){storageWrites++;},removeItem(){storageWrites++;}};
 const context={...handoff,$,crypto,document:{documentElement:{dataset:{theme:'light'}},createElement:()=>new Element()},window:{},navigator:{onLine:true},innerWidth:900,performance,
 localRetainedCategorySelected,lookupLocalRetainedCategory,active:true,paused:false,finished:false,processed:new Set(),generation:0,queue:[],current:null,selected:null,mode:'Explore',sheetTouched:false,streaming:false,sound:false,audio:null,
 productVisual:{show(){}},projectedField:()=>null,projectedValue:()=>null,humanValue:String,renderConsumerSummary(){},renderData(){},setSheetSnap(){},cancelPendingSpeech(){},readTone:()=>false,showReadCue(){},
 scanner:{start(){},stop(){},noteAccepted(){}},localStorage:storage,sessionStorage:storage,lookupIdentifiers:query,mergeIdentifierPages:lookup.mergeIdentifierPages};
 const wanted=['el','btn','message','open','close','displayValue','render','capture','showMatches','renderQueue','selectedQueueRecord'];
 const selectedNodes=nodes.filter(n=>n.type==='FunctionDeclaration'&&wanted.includes(n.id.name));
 const constants=nodes.filter(n=>n.type==='VariableDeclaration'&&n.declarations.some(d=>d.id.name==='CAPTURE_FORMATS'));
 const ids=['manual-namespace','manual','manual-open','manual-cancel','session-button','pause','undo','finish'];
 const handlers=nodes.filter(n=>n.type==='ExpressionStatement'&&n.expression.type==='AssignmentExpression'&&n.expression.left.type==='MemberExpression'&&n.expression.left.object.type==='CallExpression'&&ids.includes(n.expression.left.object.arguments[0]?.value));
 vm.createContext(context);vm.runInContext([...constants,...selectedNodes,...handlers].map(n=>source.slice(n.start,n.end)).join('\n'),context);
 return {ctx:context,$,storageWrites:()=>storageWrites};
}
const nextTick=()=>new Promise(resolve=>setImmediate(resolve));
async function manual(h,raw){h.$('manual-open').onclick();h.$('barcode').value=raw;h.$('manual-namespace').value='barcode';h.$('manual-representation').value='';h.$('manual').onsubmit({preventDefault(){}});await nextTick();}
function positiveQuery(raw,generation){const match={id:'generated-source:'+raw,name:'Generated source '+raw,provenance:{sourceId:'off',releaseId:'generated-only'},detail:{fields:{},sourceBinding:{sourceId:'off'}}};return Promise.resolve({generation,status:'source-match',matches:[match],hasMore:false,nextCursor:null,original:raw,namespace:'barcode',releaseId:'generated-only',manifestSha256:'a'.repeat(64)});}
test('reviewed public lookup fails closed when unavailable; Finish does not stage an unqualified record',async()=>{
 const h=harness();await manual(h,'0000000013131');assert.equal(h.ctx.current.status,'unavailable');assert.equal(h.ctx.current.error,'PUBLIC_LOOKUP_UNAVAILABLE');assert.equal(h.ctx.selected,null);assert.equal(h.$('kitchen-handoff').hidden,true);
 h.$('pause').onclick();assert.equal(h.$('session-dialog').open,true);assert.equal(h.$('queue-list').children.length,1);
 h.$('finish').onclick();assert.equal(h.ctx.active,true);assert.equal(h.ctx.finished,false);assert.match(h.$('lookup-status').textContent,/Finish needs review/);assert.equal(h.storageWrites(),0);assert.equal(harness().ctx.queue.length,0);assert.equal(attemptedNetwork,1);
});
test('List Inspect preserves the exact previously selected record without a new lookup or guessed match',async()=>{
 let calls=0;const h=harness((...args)=>{calls++;return positiveQuery(...args);});await manual(h,'0000000013131');const original=h.ctx.selected;
 h.$('pause').onclick();h.$('queue-list').children[0].children[2].onclick();assert.equal(h.ctx.selected,original);assert.equal(h.$('product-name').textContent,original.name);assert.equal(calls,1);assert.equal(h.storageWrites(),0);
});
test('Undo restores the preceding explicit source selection and Finish retains it without adding inventory',async()=>{
 let calls=0;const h=harness((...args)=>{calls++;return positiveQuery(...args);});await manual(h,'0000000013131');const original=h.ctx.selected;await manual(h,'0000000013132');
 h.$('undo').onclick();assert.equal(h.ctx.queue.length,1);assert.equal(h.ctx.selected,original);h.$('finish').onclick();assert.equal(h.ctx.selected,original);assert.equal(h.$('product-name').textContent,original.name);assert.equal(calls,2);assert.equal(h.storageWrites(),0);
});
test('ambiguous entry is never auto-selected; a remembered choice outside its own matches is rejected',async()=>{
 const h=harness(async(raw,generation)=>{const p=await positiveQuery(raw,generation);p.matches.push({...p.matches[0],id:'other-generated-source',name:'Other generated choice'});p.status='ambiguous';return p;});await manual(h,'0000000013133');assert.equal(h.ctx.selected,null);
 h.$('pause').onclick();h.$('queue-list').children[0].children[2].onclick();assert.equal(h.ctx.selected,null);
 h.ctx.showMatches();h.$('match-list').children[1].children[2].onclick();const chosen=h.ctx.selected;assert.equal(chosen.id,'other-generated-source');h.$('pause').onclick();h.$('queue-list').children[0].children[2].onclick();assert.equal(h.ctx.selected,chosen);
 h.ctx.current.selectedRecord={id:'foreign-generated-record'};h.ctx.selected=null;h.$('pause').onclick();h.$('queue-list').children[0].children[2].onclick();assert.equal(h.ctx.selected,null);assert.equal(h.storageWrites(),0);
});
