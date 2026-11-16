import {t,setLocalizedText} from './i18n.js';

const defaults=()=>({enabled:false,automaticActions:false,provider:'mcp',endpoint:null,model:null,dailyLimit:3,threshold:.98});
const set=(node,value)=>{node.textContent=value;return node;};
// Keep this explicit catalogue so this isolated administration panel participates
// in the normal translation extraction pass.
const catalogue=()=>({
 enabled:t('Enable AI review'),quarantine:t('Allow reversible automatic quarantine'),endpoint:t('Qualified HTTPS endpoint'),model:t('Model name'),provider:t('Provider'),endpointLabel:t('Endpoint'),modelLabel:t('Model'),limit:t('Daily review limit'),threshold:t('Automatic-action threshold'),save:t('Save reviewed AI settings'),run:t('Run review'),title:t('AI community review')
});

export function setupCommunityAI({root=null,getUser=()=>null,authFetch=globalThis.fetch?.bind(globalThis)}={}){
 const document=root?.ownerDocument||globalThis.document;let state=null,epoch=0;
 const identity=()=>{const user=getUser?.();return typeof user==='string'?user:user?.id||null;};
 const request=async(path,init)=>{const response=await authFetch(path,init),body=await response.json().catch(()=>({}));if(!response.ok){const error=Error(t(body.error||'AI administration unavailable.'));error.status=response.status;throw error;}return body;};
 const render=()=>{
  if(!root)return;root.replaceChildren();if(!state){root.hidden=true;return;}root.hidden=false;
  const form=document.createElement('form'),notice=document.createElement('p'),settings=state.settings||defaults(),words=catalogue();
  const check=(key,value)=>{const input=document.createElement('input'),label=document.createElement('label');input.type='checkbox';input.checked=!!settings[value];set(label,key);label.prepend(input);form.append(label);return input;};
  const enabled=check(words.enabled,'enabled'),automatic=check(words.quarantine,'automaticActions');
  const provider=document.createElement('select');for(const item of ['mcp','self-hosted'])provider.append(new Option(item,item));provider.value=settings.provider;
  const endpoint=document.createElement('input');endpoint.type='url';endpoint.value=settings.endpoint||'';endpoint.placeholder=words.endpoint;
  const model=document.createElement('input');model.value=settings.model||'';model.placeholder=words.model;
  const limit=document.createElement('input');limit.type='number';limit.min='1';limit.max='20';limit.value=settings.dailyLimit;
  const threshold=document.createElement('input');threshold.type='number';threshold.step='.01';threshold.min='.9';threshold.max='1';threshold.value=settings.threshold;
  const field=(key,input)=>{const label=document.createElement('label');set(label,key);label.append(input);form.append(label);};
  field(words.provider,provider);field(words.endpointLabel,endpoint);field(words.modelLabel,model);field(words.limit,limit);field(words.threshold,threshold);
  const save=set(document.createElement('button'),words.save),run=set(document.createElement('button'),words.run);run.type='button';form.append(save,run,notice);
  form.onsubmit=async event=>{event.preventDefault();const turn=epoch,userId=identity(),next={enabled:enabled.checked,automaticActions:automatic.checked,provider:provider.value,endpoint:provider.value==='self-hosted'?endpoint.value||null:null,model:provider.value==='self-hosted'?model.value||null:null,dailyLimit:Number(limit.value),threshold:Number(threshold.value)};try{if(!userId)throw Error(t('Sign in as an administrator.'));if(!confirm(t('Save these reviewed AI settings?')))return;await request('/api/admin/community/ai/settings',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirmed:true,revision:state.revision,settings:next})});if(turn!==epoch||identity()!==userId)return;await refresh();}catch(error){if(turn===epoch&&identity()===userId)setLocalizedText(notice,error.status===409?'Settings changed elsewhere. Reload and review again.':error.message);}};
  run.onclick=async()=>{const turn=epoch,userId=identity();try{if(!userId)throw Error(t('Sign in as an administrator.'));if(!confirm(t('Run the configured community review now?')))return;const result=await request('/api/admin/community/ai/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirmed:true})});if(turn===epoch&&identity()===userId){setLocalizedText(notice,result.ran?t('Reviewed {v0} public contributions: {v1}.',{v0:result.processed,v1:(result.outcomes||[]).map(item=>item.state).join(', ')}):t('Review did not run: {v0}',{v0:result.reason}));await refresh();}}catch(error){if(turn===epoch&&identity()===userId)setLocalizedText(notice,error.message);}};
  const decisions=document.createElement('ul');for(const item of state.decisions||[]){const row=document.createElement('li');row.textContent=[item.kind,item.decision,item.state,item.reason].filter(Boolean).join(' · ');decisions.append(row);}root.append(set(document.createElement('h4'),words.title),form,decisions);
 };
 const refresh=async()=>{const turn=++epoch,userId=identity();state=null;render();if(!userId)return null;try{const [settings,decisions]=await Promise.all([request('/api/admin/community/ai/settings'),request('/api/admin/community/ai/decisions')]);if(turn!==epoch||identity()!==userId)return null;state={...settings,decisions:decisions.decisions||[]};render();return state;}catch{return null;}};
 const reset=()=>{epoch++;state=null;render();};return {refresh,reset,render};
}
