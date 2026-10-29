import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,readFile,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import vm from 'node:vm';
import {parse} from 'acorn';
import {createIdentifierAdapter} from '../../cloud/identifier-host.mjs';
import * as shim from '../../public/scanner-identifiers.js';
import {IDENTIFIER_DB,IDENTIFIER_RUN} from '../../public/scanner-identity-v2.js';

test('actual queue callbacks retain bound continuation across another capture, pause and a failed lane',async t=>{
 const dir=await mkdtemp(join(tmpdir(),'offmenu-queue-cursor-'));
 t.after(()=>rm(dir,{recursive:true,force:true}));
 const script=join(dir,'identity.py'),failure=join(dir,'fail-unresolved');
 const original='036000291452';
 const rows=Array.from({length:31},(_,i)=>({assertion_id:i+1,run_id:IDENTIFIER_RUN,input_id:'generated-only',record_ordinal:i,
  namespace:'barcode',lexical_value:original,disposition:i===30?'unresolved':'source-asserted',source_id:'fixture',release_id:'generated',source_record_id:String(i),native_record_id:'fixture:'+i}));
 await writeFile(failure,'generated-only');
 await writeFile(script,`import sys,json,os
q=json.load(sys.stdin)
if q['action']=='status':
 print(json.dumps({'databaseLoaded':True,'queryAvailable':True,'databaseSha256':'${IDENTIFIER_DB}','loadComplete':True,'runId':'${IDENTIFIER_RUN}'}));sys.exit(0)
if q['disposition']=='unresolved' and os.path.exists(${JSON.stringify(failure)}):sys.exit(3)
records=json.loads(${JSON.stringify(JSON.stringify(rows))})
rows=[r for r in records if r['namespace']==q['namespace'] and r['lexical_value']==q['lexical_value'] and r['disposition']==q['disposition'] and r['assertion_id']>q['after']]
more=len(rows)>q['limit'];rows=rows[:q['limit']]
print(json.dumps({'databaseSha256':'${IDENTIFIER_DB}','rows':rows,'hasMore':more,'nextAssertionId':rows[-1]['assertion_id'] if more else None}))
`);
 const adapter=createIdentifierAdapter({scriptPath:script}),previousFetch=globalThis.fetch;
 globalThis.fetch=(path,options)=>adapter(new Request('https://offmenu-identifiers.invalid'+path,options));
 t.after(()=>{globalThis.fetch=previousFetch;});
 const source=await readFile(new URL('../../public/shelf-scanner.js',import.meta.url),'utf8'),nodes=parse(source,{ecmaVersion:'latest',sourceType:'module'}).body;
 const functions=['el','btn','capture','showMatches','renderQueue'].map(name=>{const node=nodes.find(n=>n.type==='FunctionDeclaration'&&n.id.name===name);assert.ok(node,name);return source.slice(node.start,node.end);});
 const formats=nodes.find(n=>n.type==='VariableDeclaration'&&n.declarations.some(d=>d.id.name==='CAPTURE_FORMATS'));
 const pause=nodes.find(n=>n.type==='ExpressionStatement'&&n.expression.type==='AssignmentExpression'&&n.expression.left.type==='MemberExpression'&&n.expression.left.property.name==='onclick'&&n.expression.left.object.type==='CallExpression'&&n.expression.left.object.arguments[0]?.value==='pause');
 const handoff=nodes.find(n=>n.type==='ExpressionStatement'&&n.expression.type==='AssignmentExpression'&&n.expression.left.type==='MemberExpression'&&n.expression.left.property.name==='onclick'&&n.expression.left.object.type==='CallExpression'&&n.expression.left.object.arguments[0]?.value==='kitchen-handoff');
 class Element{constructor(){this.children=[];this.dataset={};this.textContent='';}append(...children){this.children.push(...children);}replaceChildren(...children){this.children=children;}}
 const elements=new Map(),$=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
 let hold=false,entered,release;const requestGenerations=[];
 const ctx={$,document:{createElement:()=>new Element()},sheetTouched:false,setSheetSnap(){},innerWidth:900,active:true,paused:false,processed:new Set(),generation:0,queue:[],current:null,selected:null,mode:'Explore',connection:'live',requestedSourceReference:null,crypto,
  render(){},readTone(){},close(){},open(){},scanner:{noteAccepted(){},start(){}},mergeIdentifierPages:shim.mergeIdentifierPages,
  async lookupIdentifiers(raw,generation,cursor,symbology){requestGenerations.push({raw,generation,cursor});const response=await shim.lookupIdentifiers(raw,generation,cursor,symbology);if(cursor&&hold){entered();await new Promise(resolve=>{release=resolve;});}return response;},message(value){ctx.lastMessage=value;}};
 vm.createContext(ctx);vm.runInContext([source.slice(formats.start,formats.end),...functions,source.slice(pause.start,pause.end),source.slice(handoff.start,handoff.end)].join('\n'),ctx);
 await ctx.capture(original,'manual lexical barcode',null,'first');const first=ctx.queue[0],cursor=first.nextCursor;assert.equal(first.matches.length,25);assert.equal(first.hasMore,true);
 await ctx.capture('012345678905','manual lexical barcode',null,'second');ctx.renderQueue();$('queue-list').children[0].children[2].onclick();
 assert.equal(ctx.generation,3);ctx.showMatches();hold=true;const started=new Promise(resolve=>{entered=resolve;}),pending=$('match-list').children.at(-1).onclick();await started;
 $('pause').onclick();release();await pending;assert.equal(first.matches.length,25,'a cancelled UI response cannot overwrite the retained entry');$('pause').onclick();hold=false;
 ctx.renderQueue();$('queue-list').children[0].children[2].onclick();ctx.showMatches();await $('match-list').children.at(-1).onclick();assert.equal(first.matches.length,30);assert.equal(first.status,'partial');assert.equal(first.hasMore,true);
 await rm(failure);ctx.renderQueue();$('queue-list').children[0].children[2].onclick();ctx.showMatches();await $('match-list').children.at(-1).onclick();
 assert.equal(first.matches.length,31);assert.equal(new Set(first.matches.map(m=>m.identifier.assertion_id)).size,31);assert.equal(first.hasMore,false);assert.equal(first.matches.at(-1).identifier.disposition,'unresolved');
 assert.ok(requestGenerations.filter(q=>q.cursor).every(q=>q.generation===1));
 const wrong=await shim.lookupIdentifiers(original,2,cursor);assert.equal(wrong.status,'unavailable');assert.match(wrong.error,/CURSOR_BINDING_MISMATCH/);
 const staged=[];ctx.current=first;ctx.selected=first.matches[0];ctx.sourceObservationReference=shim.sourceObservationReference;ctx.sessionStorage={setItem(key,value){staged.push(JSON.parse(value));}};ctx.KITCHEN_HANDOFF='generated-handoff';ctx.location={assign(path){assert.equal(path,'/kitchen.html?scan=staged');}};
 $('kitchen-handoff').onclick();$('kitchen-handoff').onclick();assert.equal(staged.length,2);assert.match(staged[0].operationId,/^[0-9a-f-]{36}$/);assert.notEqual(staged[0].operationId,staged[1].operationId);assert.deepEqual(staged[0].sourceObservationReference,staged[1].sourceObservationReference);
});
