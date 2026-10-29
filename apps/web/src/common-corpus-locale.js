import {getLanguage,t} from './i18n.js';

const languageKey=value=>String(value||'und').replaceAll('_','-').toLowerCase();
const property=name=>'urn:offmenu:property:'+name;
const relation=name=>'urn:offmenu:relation:'+name;
const STATUS_LABELS={
  'source-scoped':'Source-specific identity','candidate-join':'Candidate identity link','curated-concept':'Curated concept',identified:'Identified resource',
  'source-asserted':'Source assertion',candidate:'Candidate','editor-authored':'Editor authored',reviewed:'Reviewed',verified:'Verified',unknown:'Unknown',
  conflicting:'Conflicting',superseded:'Superseded','needs-transcription':'Needs transcription',
};
export const commonStatusLabel=(status,locale=getLanguage())=>t(STATUS_LABELS[status]||status,{},locale);
const digest=async value=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value))),byte=>byte.toString(16).padStart(2,'0')).join('');

// Read-only adapter for the corpus owner's offmenu-common/1 contract. It never
// joins candidate identities, converts units or changes the source graph.
export async function createCommonCorpus(graph,{userId=null,allowLocalRestricted=false}={}) {
  if(graph?.schemaVersion!=='offmenu-common/1'||!['resources','assertions','relations','citations','translations'].every(key=>Array.isArray(graph[key])))throw Error('Unsupported common corpus graph.');
  graph=structuredClone(graph);
  const freeze=value=>{if(value&&typeof value==='object'&&!Object.isFrozen(value)){Object.freeze(value);Object.values(value).forEach(freeze);}};
  freeze(graph);
  const accessible=scope=>scope?.visibility==='public'||scope?.visibility==='private'&&userId!=null&&scope.ownerId===userId||scope?.visibility==='local-restricted'&&allowLocalRestricted;
  const index=(rows,name)=>{const map=new Map();for(const row of rows){if(typeof row.id!=='string'||map.has(row.id))throw Error('Duplicate or missing '+name+' identity.');map.set(row.id,row);}return map;};
  const allCitations=index(graph.citations,'citation'),citations=new Map([...allCitations].filter(([,row])=>accessible(row.scope)));
  const cited=ids=>Array.isArray(ids)&&ids.length>0&&ids.every(id=>citations.has(id));
  const allResources=index(graph.resources,'resource'),resources=new Map([...allResources].filter(([,row])=>accessible(row.scope)&&cited(row.citationIds)));
  index(graph.assertions,'assertion');index(graph.relations,'relation');index(graph.translations,'translation');
  const assertions=graph.assertions.filter(row=>accessible(row.scope)&&cited(row.citationIds)&&resources.has(row.subjectId)&&row.status!=='superseded');
  const relations=graph.relations.filter(row=>accessible(row.scope)&&cited(row.citationIds)&&resources.has(row.subjectId)&&(!allResources.has(row.objectId)||resources.has(row.objectId))&&row.status!=='superseded');
  const texts=new Map();
  function collect(value){if(!value||typeof value!=='object')return;if(value.kind==='text'){
    if(typeof value.id!=='string'||typeof value.value!=='string'||!cited(value.citationIds)||value.status==='superseded')return;
    const previous=texts.get(value.id);if(previous&&(previous.value!==value.value||previous.sourceTextSha256!==value.sourceTextSha256))throw Error('Conflicting source text identity.');texts.set(value.id,value);
  }else if(value.kind==='list')value.items?.forEach(collect);else if(value.kind==='structure')Object.values(value.fields||{}).forEach(collect);else if(value.kind==='quantity'&&value.sourceNotation)collect(value.sourceNotation);}
  for(const resource of resources.values())for(const name of resource.names||[])collect(name);
  for(const assertion of assertions)collect(assertion.value);
  const validTexts=new Set();
  await Promise.all([...texts].map(async([id,text])=>{if(await digest(text.value)!==text.sourceTextSha256)throw Error('Source text fingerprint does not match.');validTexts.add(id);}));
  const translations=new Map();
  for(const item of graph.translations){const source=texts.get(item.textId);
    if(!source||!validTexts.has(source.id)||source.sourceTextSha256!==item.sourceTextSha256||!['published-source','reviewed'].includes(item.status)||typeof item.value!=='string'||!cited(item.citationIds))continue;
    const key=source.id+'|'+languageKey(item.language);if(!translations.has(key))translations.set(key,[]);translations.get(key).push(item);
  }
  function projectText(text,locale=getLanguage()){
    if(!text||!validTexts.has(text.id))return null;
    const cached=texts.get(text.id);
    if(text.value!==cached.value||text.sourceTextSha256!==cached.sourceTextSha256)return null;
    text=cached;
    const requested=languageKey(locale),sourceLanguage=languageKey(text.language),languages=[requested,requested.split('-')[0]];
    const native=requested==='native'||requested.split('-')[0]===sourceLanguage.split('-')[0];
    let selected;
    if(!native)for(const language of languages){const choices=translations.get(text.id+'|'+language)||[];const reviewed=choices.filter(item=>item.status==='reviewed');const eligible=reviewed.length?reviewed:choices;
      // Conflicting reviewed translations require a decision; never pick one by
      // arrival order or treat one source edition as another's translation.
      if(eligible.length&&new Set(eligible.map(item=>item.value)).size===1){selected=eligible[0];break;}
    }
    const citationIds=[...new Set([...text.citationIds,...(selected?.citationIds||[])])];
    const unavailable=graph.translations.filter(item=>item.textId===text.id&&languages.includes(languageKey(item.language)));
    const fallbackReason=native||selected?null:unavailable.some(item=>item.status==='stale'||item.sourceTextSha256!==text.sourceTextSha256)?'stale':unavailable.some(item=>item.status==='draft')?'draft':unavailable.length?'conflicting-or-unavailable':'missing';
    return {value:selected?.value??text.value,original:text.value,language:selected?languageKey(selected.language):sourceLanguage,sourceLanguage,
      requested,translated:!!selected,missingTranslation:!native&&!selected,textId:text.id,sourceTextSha256:text.sourceTextSha256,
      translationId:selected?.id||null,translationMethod:selected?.method||null,translationStatus:selected?.status||null,
      fallbackReason,citationIds,citations:citationIds.map(id=>citations.get(id)),status:text.status};
  }
  const aliases=new Map();
  for(const row of assertions)if(row.propertyId===property('originalSourceRecord')&&row.value?.kind==='identifier'){
    if(!aliases.has(row.value.value))aliases.set(row.value.value,new Set());aliases.get(row.value.value).add(row.subjectId);
  }
  function resourceFor(record){
    if(typeof record==='object'&&!record.commonResourceId&&(record.provenance?.personalReview||record.provenance?.visibility==='private'))return null;
    const id=typeof record==='string'?record:record?.commonResourceId||record?.id||record?.ingredientId;
    if(resources.has(id))return resources.get(id);const found=aliases.get(id);return found?.size===1?resources.get([...found][0]):null;
  }
  const factsFor=(id,name)=>assertions.filter(row=>row.subjectId===id&&row.propertyId===property(name));
  function nameFor(resource,locale){const sourceNames=(resource.names||[]).filter(name=>validTexts.has(name.id));
    const requested=languageKey(locale),languages=[requested,requested.split('-')[0]];
    const exact=sourceNames.find(name=>languages.includes(languageKey(name.language)));
    if(exact)return {...projectText(exact,locale),resourceId:resource.id,identityStatus:resource.identityStatus};
    const projections=sourceNames.map(name=>projectText(name,locale));const chosen=projections.find(value=>value.translated)||projections[0];
    return chosen?{...chosen,resourceId:resource.id,identityStatus:resource.identityStatus}:null;
  }
  function resolveField(record,field,locale=getLanguage()){
    const resource=resourceFor(record);if(!resource)return null;
    if(['name','title','ingredient'].includes(field))return nameFor(resource,locale);
    if(['directions','instructions'].includes(field)){
      const steps=relations.filter(row=>row.subjectId===resource.id&&row.predicateId===relation('hasStep'))
        .map(row=>({id:row.objectId,position:factsFor(row.objectId,'position').find(f=>f.value.kind==='number')?.value.value}));
      if(!steps.length)return null;
      steps.sort((a,b)=>(a.position??Infinity)-(b.position??Infinity));
      const items=steps.map(step=>projectText(factsFor(step.id,'instruction').find(row=>row.value.kind==='text')?.value,locale));
      if(items.some(item=>!item))return null;
      return {value:items.map(item=>item.value),original:items.map(item=>item.original),language:items.every(item=>item.language===items[0].language)?items[0].language:'mul',requested:languageKey(locale),
        missingTranslation:items.some(item=>item.missingTranslation),translated:items.some(item=>item.translated),items,resourceId:resource.id};
    }
    const fact=factsFor(resource.id,field).find(row=>row.value.kind==='text');return fact?projectText(fact.value,locale):null;
  }
  function displayValue(value,locale=getLanguage(),seen=new Set()){
    if(value.kind==='text')return projectText(value,locale)?.value??t('Unavailable source text',{},locale==='native'?getLanguage():locale);
    if(value.kind==='reference'){if(seen.has(value.id))return value.id;return nameFor(resources.get(value.id)||{names:[]},locale)?.value||value.id;}
    if(value.kind==='list')return value.items.map(item=>displayValue(item,locale,seen)).join(' · ');
    if(value.kind==='structure')return Object.entries(value.fields).map(([key,item])=>t(key,{},locale==='native'?getLanguage():locale)+': '+displayValue(item,locale,seen)).join(' · ');
    if(locale==='native')locale=getLanguage();
    if(value.kind==='number')return new Intl.NumberFormat(locale,{maximumFractionDigits:20}).format(value.value);
    if(value.kind==='boolean')return t(value.value?'Yes':'No',{},locale);
    if(value.kind==='null')return t('Unknown',{},locale);
    if(['identifier','uri','expression'].includes(value.kind))return value.value;
    if(['date','datetime'].includes(value.kind)){try{return new Intl.DateTimeFormat(locale,value.kind==='datetime'?{dateStyle:'medium',timeStyle:'short'}:{}).format(new Date(value.kind==='date'?value.value+'T12:00:00':value.value));}catch{return value.value;}}
    if(value.kind==='quantity'){
      const amount=value.value==null?t('Unknown',{},locale):new Intl.NumberFormat(locale,{maximumFractionDigits:20}).format(value.value);
      const unit=value.unitId?displayIdentifier(value.unitId,locale):value.sourceUnit||t('Unknown unit',{},locale);
      return amount+' '+unit;
    }
    return t('Unknown',{},locale);
  }
  function displayIdentifier(id,locale=getLanguage()) {
    const name=resources.has(id)?nameFor(resources.get(id),locale):null;
    if(name)return name.value;
    const token=/^urn:offmenu:(?:type|property|relation|unit):(.+)$/.exec(id)?.[1];
    return token?t(token.replace(/([a-z])([A-Z])/g,'$1 $2').replaceAll('_',' '),{},locale):id;
  }
  return {schemaVersion:graph.schemaVersion,resolveField,projectText,resourceFor,displayValue,displayIdentifier,
    resources:[...resources.values()],assertions,relations,citations:[...citations.values()]};
}
