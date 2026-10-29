const $=id=>document.getElementById(id);
const stages=['discovered','acquired','normalized','gold-reviewed','translated'];
const labels={discovered:'Discovered',acquired:'Retained',normalized:'Normalized','gold-reviewed':'Gold-reviewed',translated:'Translated'};
const fmt=value=>value==null?'Unknown':Number(value).toLocaleString();
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const date=value=>value?String(value).slice(0,16).replace('T',' ')+' UTC':'Date not recorded';
const safeLink=value=>{try{const u=new URL(value);return ['http:','https:'].includes(u.protocol)?u.href:null;}catch{return null;}};
const link=(url,text)=>safeLink(url)?`<a href="${esc(safeLink(url))}" target="_blank" rel="noopener noreferrer">${esc(text)} ↗</a>`:esc(text);
let data,filtered=[],limit=25,preset='all';
function stageLabel(e){const yes=stages.filter(s=>e.stages?.[s]===true);return yes.filter(s=>s!=='discovered'||yes.length===1).map(s=>`<span class="stage-badge yes">${labels[s]}</span>`).join('');}
function sample(s){return `<article class="sample"><p class="sample-date">${esc(s.subtitle)}</p><h4>${esc(s.title)}</h4><dl class="sample-fields">${s.fields.map(f=>`<div><dt>${esc(f.label)}</dt><dd>${esc(f.value)}</dd></div>`).join('')}</dl>${s.issue?`<p class="specific-issue">${esc(s.issue)}</p>`:''}<details class="source-details"><summary>Record source</summary><p>${link(s.sourceURL,s.attribution||'Retained source')}</p><p>${esc(s.recordId)}${s.sourceHash?' · SHA256 '+esc(s.sourceHash.slice(0,12)):''}</p></details></article>`;}
function holding(e){return `<article class="evidence"><p class="category">${esc(e.category)}</p><h4>${esc(e.title)}</h4><div class="stage-row">${stageLabel(e)}</div><div class="metrics">${(e.metrics||[]).slice(0,4).map(m=>`<div class="metric"><strong>${fmt(m.value)}</strong>${esc(m.unit)}</div>`).join('')}</div><p class="holding-date">${date(e.asOf)}</p><details class="source-details"><summary>Source details</summary><p>${link(e.url,e.title)} · ${esc(e.dataType)}</p><p>${esc(e.scope)}</p>${e.units?.length?`<p>Units: ${e.units.map(esc).join(', ')}</p>`:''}<p>${esc(e.evidenceLabel)}${e.evidenceHash?' · SHA256 '+esc(e.evidenceHash.slice(0,12)):''}</p>${e.gap?`<p>${esc(e.gap)}</p>`:''}${e.review?`<p>Review: ${esc(e.review)}</p>`:''}</details></article>`;}
function detail(c){
 const category=$('category').value,ev=c.evidence.filter(e=>!category||e.category===category),samples=c.samples.filter(s=>!category||s.category===category);
 const notes=c.categories.filter(a=>a.note&&(!category||a.name===category));
 return `<section class="work-panel"><div><p class="section-label">Working on</p><h3>${esc(c.work.now)}</h3></div><div><p class="section-label">Next</p><p>${esc(c.work.next)}</p></div></section><h3 class="section-label">What we have</h3><div class="evidence-grid">${ev.slice(0,4).map(holding).join('')||'<p class="empty">No holdings summary connected yet.</p>'}</div>${ev.length>4?`<details class="more-holdings"><summary>More holdings (${ev.length-4})</summary><div class="evidence-grid">${ev.slice(4).map(holding).join('')}</div></details>`:''}<h3 class="section-label">Actual records</h3><div class="sample-grid">${samples.map(sample).join('')||'<p class="sample-absence">No record sample exported yet.</p>'}</div>${notes.length?`<details class="supporting"><summary>Category progress notes</summary>${notes.map(a=>`<p><strong>${esc(a.name)}</strong><br>${esc(a.note)}</p>`).join('')}</details>`:''}<details class="supporting"><summary>Sources &amp; history · ${fmt(c.registeredSourceCount)} discovery leads</summary><div class="source-list">${c.sources.map(s=>`<article class="source">${link(s.url,s.name)}<p>${esc(s.dataType)} · ${esc(s.id)}</p></article>`).join('')}</div><details class="receipt-list"><summary>Historical receipts (${c.receipts.length})</summary>${c.receipts.map(r=>`<article class="receipt"><strong>${esc(r.sourceName||r.sourceId||'Source join pending')}</strong><p>${esc(r.status||'Status not recorded')} · ${date(r.asOf)}<br>Reported bytes: ${fmt(r.reportedBytes)} · ${esc(r.rights||'Rights not recorded')}</p></article>`).join('')}</details><p class="meta">Portfolio ${esc(c.assignment==='unassigned'?'queued':c.assignment)}${c.owner!=null?' · owner '+esc(c.owner):''}. Work update ${date(c.work.asOf)}.</p></details><button type="button" class="back-directory">↑ All countries</button>`;
}
function shortHoldings(c){const items=c.evidence.filter(e=>e.metrics?.length).slice(0,2);return items.length?items.map(e=>`${fmt(e.metrics[0].value)} ${e.metrics[0].unit} · ${e.title}`).join(' / '):'Holdings summary pending';}
function render(){
 $('result-count').textContent=`${filtered.length} of ${data.countries.length} countries`;$('countries').replaceChildren();
 for(const c of filtered.slice(0,limit)){
  const d=document.createElement('details');d.className='country';d.id='country-'+c.code;
  d.innerHTML=`<summary><span class="code">${esc(c.code)}</span><span class="country-cover"><span class="country-name">${esc(c.name)}<span class="tag ${c.assignment==='assigned'?'assigned':''}">${esc(c.work.label)}</span></span><span class="country-summary">${esc(shortHoldings(c))}</span><span class="country-next">Next · ${esc(c.work.next)}</span>${c.samples.length?`<span class="sample-teaser">Sample · ${esc(c.samples[0].title)}</span>`:''}</span></summary>`;
  d.addEventListener('toggle',()=>{if(d.open&&!d.querySelector('.country-body')){const body=document.createElement('div');body.className='country-body';body.innerHTML=detail(c);d.append(body);}});$('countries').append(d);
 }
 if(!filtered.length)$('countries').innerHTML='<p class="empty">No matches. Tap All countries to reset.</p>';
 $('more').hidden=limit>=filtered.length;$('more').textContent=`Show next ${Math.min(25,filtered.length-limit)} countries`;
 document.querySelectorAll('[data-preset]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.preset===preset?'true':'false'));
}
function filter(){
 const q=$('search').value.trim().toLowerCase(),category=$('category').value,stage=$('stage').value,assignment=$('assignment').value;
 filtered=data.countries.filter(c=>{
  if(preset==='samples'&&!c.samples.length)return false;
  if(preset==='queued'&&c.assignment!=='unassigned')return false;
  if(assignment&&c.assignment!==assignment)return false;
  if(q&&!`${c.name} ${c.code} ${c.sources.map(s=>s.name+' '+s.dataType).join(' ')} ${c.evidence.map(e=>e.title+' '+e.category).join(' ')} ${c.samples.map(s=>s.title).join(' ')}`.toLowerCase().includes(q))return false;
  const relevant=c.evidence.filter(e=>!category||e.category===category);
  if(stage==='discovered')return c.sources.length>0;
  if(stage==='unknown')return !relevant.some(e=>e.stages.acquired||e.stages.normalized);
  return !stage||relevant.some(e=>e.stages[stage]===true);
 });limit=25;render();
}
function reset(){for(const id of ['search','category','stage','assignment','country-picker'])$(id).value='';preset='all';filter();}
function openCountry(code){reset();$('country-picker').value=code;$('search').value=code;filter();const target=$('country-'+code);if(target){target.open=true;target.scrollIntoView({block:'start'});}}
async function init(){
 const response=await fetch('/country-progress.json',{cache:'no-store'});if(!response.ok)throw Error('Metadata '+response.status);data=await response.json();
 $('snapshot').textContent=`Allocation ${date(data.allocationAsOf)} · Samples compiled ${date(data.generatedUTC)}`;
 $('stats').innerHTML=[['249','countries & territories'],[fmt(data.counts.assigned),'assigned'],[fmt(data.counts.unassigned),'queued']].map(([n,label])=>`<div class="stat"><strong>${n}</strong><span>${label}</span></div>`).join('');
 $('overview').innerHTML=`<div><p class="eyebrow">UNDERWAY</p><ul>${data.currentWork.map(w=>`<li>${esc(w.task)}</li>`).join('')}</ul></div><div><p class="eyebrow">NEXT UP</p><ul>${data.nextSteps.map(esc).map(t=>`<li>${t}</li>`).join('')}</ul></div>`;
 $('featured').innerHTML=['LY','JE'].map(code=>{const c=data.countries.find(c=>c.code===code);return `<div><div class="feature-heading"><h3>${esc(c.name)}</h3><button type="button" data-country="${code}">Country details ↗</button></div>${sample(c.samples[0])}</div>`;}).join('');
 $('featured').addEventListener('click',e=>{const target=e.target.closest('[data-country]');if(target)openCountry(target.dataset.country);});
 $('country-picker').innerHTML='<option value="">Choose any country…</option>'+data.countries.map(c=>`<option value="${esc(c.code)}">${esc(c.name)} · ${esc(c.code)}</option>`).join('');
 $('country-picker').addEventListener('change',()=>{if($('country-picker').value)openCountry($('country-picker').value);else reset();});
 $('quick-browse').addEventListener('click',e=>{const b=e.target.closest('[data-preset]');if(b){reset();preset=b.dataset.preset;filter();}});
 $('countries').addEventListener('click',e=>{if(e.target.closest('.back-directory')){reset();$('quick-browse').scrollIntoView({block:'start'});}});
 $('shared').innerHTML=`<details><summary>Global sources &amp; country-unassigned records</summary><div class="source-list">${data.shared.map(s=>`<article class="source">${link(s.url,s.title)}<p>${esc(s.scope)}</p></article>`).join('')}</div></details>`;
 $('method').innerHTML=`<p>${esc(data.method)}</p><ul>${data.inputs.map(i=>`<li>${esc(i.label)} · ${date(i.asOf)} · ${esc(i.sha256.slice(0,12))}</li>`).join('')}</ul>`;
 $('filters').addEventListener('submit',e=>e.preventDefault());for(const id of ['search','category','stage','assignment'])$(id).addEventListener(id==='search'?'input':'change',filter);
 $('filters').addEventListener('reset',()=>setTimeout(reset,0));$('more').addEventListener('click',()=>{limit+=25;render();});filter();
 const code=new URLSearchParams(location.search).get('country')?.toUpperCase();if(code)openCountry(code);
}
init().catch(e=>{$('snapshot').textContent='Snapshot unavailable';$('countries').innerHTML=`<p class="empty">Could not load the metadata snapshot. ${esc(e.message)}</p>`;});
