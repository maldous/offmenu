import {t,renderedLanguage,apiError} from './i18n.js';
import {setupSync} from './sync-ui.js';
import {kitchenProjection,applyKitchen} from './sync-model.js';
const $=id=>document.getElementById(id),el=(tag,text)=>{const e=document.createElement(tag);e.textContent=text;if(renderedLanguage(text))e.lang=renderedLanguage(text);e.dir='auto';return e;};
export function setupSharing({getUser,isDemo,getKey,snapshot,apply,refreshSession,status,onScopeChange}){let selected=null,notice='',pollFailures=0,nextPoll=0,generation=0,selectionContext=null,renderGeneration=0;
// Contexts bind every continuation and detached control to its initiating scope.
const context=()=>({generation,user:getUser()?.id,key:getKey(),demo:isDemo()});
const current=ctx=>!!ctx&&ctx.generation===generation&&ctx.user===getUser()?.id&&ctx.key===getKey()&&ctx.demo===isDemo()&&!!ctx.user&&!ctx.demo;
const stale=new DOMException('Stale sharing scope','AbortError');
function guard(ctx){if(!current(ctx))throw stale;}
const active=()=>!!selected&&current(selectionContext);
async function action(ctx,run){if(!current(ctx))return;try{return await run();}catch(e){if(!current(ctx)||e===stale)return;notice=e.message;await render();}}
const memoryKey=()=>getKey()+'-shared-session';
async function request(path,method='GET',body,ctx=context()){
guard(ctx);await refreshSession();guard(ctx);
const r=await fetch('/api/kitchens'+path,{method,headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(15000)});
guard(ctx);const v=await r.json();guard(ctx);if(!r.ok)throw apiError(v,'Kitchen request failed');return v;}

const sync=setupSync({getUser:()=>active()&&selected.role!=='viewer'?getUser():null,isDemo,getKey:()=>getKey()+'-kitchen-'+(selected?.id||'none'),snapshot:()=>kitchenProjection(snapshot()),apply:state=>apply(applyKitchen(snapshot(),state)),request:(method,body)=>{guard(selectionContext);return request('/'+selected.id+'/state',method,body,selectionContext);},onStatus:status});
function stored(){try{return JSON.parse(localStorage.getItem(memoryKey())||'null');}catch{return null;}}
async function select(k){
const ctx=context();guard(ctx);ctx.generation=++generation;
return action(ctx,async()=>{
if(selected){selectionContext=ctx;if(!await close(false,ctx))return;}guard(ctx);
void render();const original=structuredClone(snapshot()),remote=await request('/'+k.id+'/state','GET',undefined,ctx);guard(ctx);
selected=k;selectionContext=ctx;localStorage.setItem(memoryKey(),JSON.stringify({selected,original}));
apply(applyKitchen(original,remote.state));sync.reset(remote.state,remote.revision);onScopeChange();
if(k.role==='viewer')status('Shared kitchen · view only','synced');await render();});}
async function close(force=false,ctx){
if(!ctx){ctx=context();guard(ctx);ctx.generation=++generation;selectionContext=ctx;}
if(!force&&selected?.role!=='viewer'&&sync.pending()){await sync.run();guard(ctx);if(sync.pending()){notice='This kitchen has unsynced changes. Stay here until sync completes, or export a backup before resolving a conflict.';status(notice,'pending');await render();guard(ctx);return false;}}
guard(ctx);const m=stored();selected=null;selectionContext=null;
if(m?.original){const current=snapshot(),restored={...m.original,profile:{...current.profile,locations:m.original.profile.locations,plan:m.original.profile.plan,shopping:m.original.profile.shopping,shoppingChecked:m.original.profile.shoppingChecked,batches:m.original.profile.batches}};apply(restored);}
localStorage.removeItem(memoryKey());onScopeChange();await render();guard(ctx);return true;}

async function render(){if(selected&&!active()){generation++;selected=null;selectionContext=null;notice='';}const ctx=context(),view=++renderGeneration,valid=()=>current(ctx)&&view===renderGeneration;const box=$('household-sharing');box.replaceChildren();if(!getUser()||isDemo()){box.append(el('p',t('Sign in with your own account to create or join a shared kitchen. Demo data is separate.')));return;}try{const list=await request('','GET',undefined,ctx);if(!valid())return;box.append(el('p',selected?t("Open: {v0} · {v1}", {v0:(selected.name),v1:(selected.role)}):t('Your private account kitchen is open.')));if(notice)box.append(el('p',notice));for(const k of list.kitchens){const row=el('div',''),open=el('button',k.name+' · '+k.role);open.className='outline';open.disabled=selected?.id===k.id;open.onclick=()=>action(ctx,()=>select(k));row.append(open);box.append(row);}if(selected){const closeButton=el('button',t('Return to my private kitchen'));closeButton.className='outline';closeButton.onclick=()=>action(ctx,()=>close());box.append(closeButton);const kitchen=selected;const members=await request('/'+kitchen.id+'/members','GET',undefined,ctx);if(!valid())return;for(const m of members.members){const row=el('p',(m.self?'You':'Account '+m.user_id.slice(0,8))+' · '+m.role);if(m.role!=='owner'&&(selected.role==='owner'||m.self)){const remove=el('button',m.self?t('Leave kitchen'):t('Remove access'));remove.className='text-button';remove.onclick=()=>action(ctx,async()=>{await request('/'+kitchen.id+'/members','DELETE',{userId:m.user_id},ctx);guard(ctx);if(m.self)await close(true);else await render();});row.append(remove);}box.append(row);}if(selected.role==='owner'){const role=document.createElement('select');role.setAttribute('aria-label',t('Invitation role'));for(const r of ['editor','viewer']){const o=el('option',r==='editor'?t('Editor · change inventory, plans and shopping'):t('Viewer · read kitchen only'));o.value=r;role.append(o);}const invite=el('button',t('Create a private invitation code'));invite.onclick=()=>action(ctx,async()=>{const v=await request('/'+kitchen.id+'/invites','POST',{role:role.value},ctx);if(!valid())return;const code=el('textarea',v.token);code.readOnly=true;code.setAttribute('aria-label',t('Private invitation code'));box.append(el('p',t('Single use · expires in 48 hours. Share privately with the intended person. No message has been sent.')),code);});box.append(role,invite);}}
const name=document.createElement('input');name.placeholder=t('Shared kitchen name');name.setAttribute('aria-label',t('Shared kitchen name'));name.maxLength=100;const create=el('button',t('Create a shared kitchen from this inventory'));create.onclick=()=>action(ctx,async()=>{const k=await request('','POST',{name:name.value,state:kitchenProjection(snapshot())},ctx);guard(ctx);await select(k);});box.append(name,create);const token=document.createElement('input');token.placeholder=t('Paste invitation code');token.setAttribute('aria-label',t('Kitchen invitation code'));const join=el('button',t('Join an invited kitchen'));join.onclick=()=>action(ctx,async()=>{await request('/join','POST',{token:token.value},ctx);guard(ctx);token.value='';notice='Joined. Open the kitchen above to use it.';await render();});box.append(token,join);}catch(e){if(valid()&&e!==stale)box.append(el('p',e.message));}}
async function resume(){const saved=stored();if(!saved||!getUser()||isDemo())return;
const ctx=context();ctx.generation=++generation;
return action(ctx,async()=>{selected=saved.selected;selectionContext=ctx;onScopeChange();const list=await request('','GET',undefined,ctx);guard(ctx);const k=list.kitchens.find(x=>x.id===selected.id);
if(!k){await close(true);status('Shared access removed. Returned to your private kitchen.','local');return;}
selected=k;if(k.role==='viewer'){const remote=await request('/'+k.id+'/state','GET',undefined,ctx);guard(ctx);apply(applyKitchen(snapshot(),remote.state));}else await sync.run();});}

setInterval(async()=>{if(!active()||document.hidden||!navigator.onLine||Date.now()<nextPoll)return;
const ctx=context(),kitchen=selected;
try{const list=await request('','GET',undefined,ctx);guard(ctx);const k=list.kitchens.find(k=>k.id===kitchen.id);
if(!k){await close(true);status('Kitchen membership revoked','local');}
else if(k.role==='viewer'){const remote=await request('/'+k.id+'/state','GET',undefined,ctx);guard(ctx);apply(applyKitchen(snapshot(),remote.state));}
if(current(ctx)){pollFailures=0;nextPoll=0;}
}catch(e){if(!current(ctx)||e===stale)return;pollFailures++;nextPoll=Date.now()+Math.min(300000,60000*2**Math.min(pollFailures-1,3));}},60000);
return {render,resume,schedule:()=>{if(!active())return;if(selected.role==='viewer'){notice='This kitchen is read-only. Local edits are not shared.';status(notice,'conflict');}else sync.schedule();},active,canWrite:()=>!active()||selected.role!=='viewer',reset:()=>{generation++;renderGeneration++;selected=null;selectionContext=null;notice='';pollFailures=0;nextPoll=0;}};}
