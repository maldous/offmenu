import {validFoundationSourceReference,copyFoundationSourceReference} from '../foundation-scanner-handoff.mjs';
// Local, source-admitted foundation view. No legacy full-product projection.
export const FOUNDATION_CONTRACT='offmenu-barcode-foundation-phase/2';
export const FOUNDATION_SELECTION={releaseId:'offmenu-reviewed-foundation-r2-20261027-v1',manifestSha256:'9fe0cb763cec1e8b4afee9c77d508f98f15788f1ad4400fb2ecb659b14730acc'};
const SOURCES=['off','usda-files'],CURSOR='offmenu-local-foundation-scanner/1';
const SUBJECT=['sourceId','releaseId','recordId','sourceObservationSha256','sourceDocumentSha256','inputDatabaseSha256','sourceQualificationSha256'];
export const AXES=['baseMaterial','milkBase','fatClass','sugarStatus','saltStatus','lactoseStatus','processing','form','flavour','scent','colour','material','size','netAmount','packageCount','concentration','strength','dimensions','capacity','compatibility','finish','grade','originVariant','otherQualifiedVariant'];
const SHA=/^[a-f0-9]{64}$/,obj=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const text=x=>typeof x==='string'&&x.length>0&&x.length<=1024&&!/[\x00-\x1f\x7f]/.test(x);
const stable=x=>Array.isArray(x)?'['+x.map(stable).join(',')+']':obj(x)?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+stable(x[k])).join(',')+'}':JSON.stringify(x);
const same=(a,b)=>stable(a)===stable(b);
const key=r=>JSON.stringify(SUBJECT.map(k=>r.provenance[k]).concat(r.id));
function validRecord(r,source,barcode){
 const p=r?.provenance,d=r?.data,c=r?.curation;
 return r?.schemaVersion==='1.0'&&r.kind==='product'&&text(r.id)&&obj(p)&&p.sourceId===source&&p.visibility==='public'&&SUBJECT.every(k=>text(p[k]))&&SUBJECT.slice(3).every(k=>SHA.test(p[k]))&&text(p.license)&&text(p.attribution)&&
 c?.schema==='offmenu-foundation-curation/2'&&c.phaseContract===FOUNDATION_CONTRACT&&c.rawSourcePayloadPublished===false&&c.legacyCuratedAdmission===false&&
 obj(d)&&text(d.name)&&text(d.canonicalEnglishKey)&&text(d.canonicalConceptId)&&['ingredient','noningredient'].includes(d.classification)&&
 d.identifiers?.some(i=>i.system==='barcode'&&i.value===barcode)&&d.foundationComplete===true&&['fullProductComplete','normalizationComplete','goldAdmitted','automaticPlanningEligible','recipeNutritionJoinsAccepted'].every(k=>d[k]===false)&&
 d.meaningfulType?.state==='reviewed'&&text(d.meaningfulType.canonicalEnglishLabel)&&d.meaningfulType.subjectConceptId===d.canonicalConceptId&&
 obj(d.variantParameters)&&Object.keys(d.variantParameters).length===24&&AXES.every(k=>obj(d.variantParameters[k])&&['known','unknown'].includes(d.variantParameters[k].state))&&
 (!Object.hasOwn(r,'foundationSourceReference')||validFoundationSourceReference(r.foundationSourceReference,barcode)&&r.foundationSourceReference.recordId===r.id&&r.foundationSourceReference.namespace==='barcode'&&r.foundationSourceReference.lexicalValue===barcode&&SUBJECT.every(k=>r.foundationSourceReference.sourceBinding[k]===p[k]));
}
function project(record){const r=structuredClone(record);return {id:key(r),name:'Canonical base · '+r.data.name,brand:null,provenance:structuredClone(r.provenance),foundationRecord:r,...(validFoundationSourceReference(r.foundationSourceReference,r.data.identifiers[0]?.value)?{foundationSourceReference:copyFoundationSourceReference(r.foundationSourceReference,r.data.identifiers[0].value)}:{}),sourceObservationReference:null};}
function union(a,b){const map=new Map();for(const m of [...a,...b]){const k=key(m.foundationRecord),old=map.get(k);if(old&&!same(old.foundationRecord,m.foundationRecord))throw Error('FOUNDATION_OBSERVATION_CHANGED');if(!old)map.set(k,m);}return [...map.values()];}
function output(raw,generation,symbology,requestCursor,matches,lanes){
 const hasMore=lanes.some(l=>l.pending),failed=lanes.some(l=>l.error);
 return {original:raw,namespace:'barcode',symbology,generation,requestCursor,foundationLookup:true,matches,providerStates:lanes.map(l=>({...l})),status:failed?(matches.length?'partial':'unavailable'):matches.length>1||matches.length&&hasMore?'ambiguous':matches.length?'source-match':'unavailable',hasMore,
 nextCursor:hasMore?JSON.stringify({schema:CURSOR,raw,generation,symbology,selection:FOUNDATION_SELECTION,lanes}):null,
 fullProductComplete:false,goldAdmitted:false,automaticPlanningEligible:false,physicalProductEquivalenceAsserted:false,externalFallback:false};
}
export function createFoundationScannerLookup({fetchImpl=globalThis.fetch}={}){
 return async function lookup(raw,generation,cursor=null,symbology=null,namespace='barcode'){
  const empty=(reason)=>({...output(raw,generation,symbology,cursor,[],SOURCES.map(source=>({source,pending:false,cursor:null,error:reason,status:null}))),error:reason});
  if(namespace!=='barcode'||typeof raw!=='string'||!/^\d{4,32}$/.test(raw)||!Number.isSafeInteger(generation)||symbology!==null&&typeof symbology!=='string')return empty('UNSUPPORTED_EXACT_BARCODE');
  let lanes=SOURCES.map(source=>({source,pending:true,cursor:null,error:null,status:null}));
  if(cursor!==null){try{if(typeof cursor!=='string'||cursor.length>6000)throw Error();const c=JSON.parse(cursor);if(c.schema!==CURSOR||c.raw!==raw||c.generation!==generation||c.symbology!==symbology||!same(c.selection,FOUNDATION_SELECTION)||!Array.isArray(c.lanes)||c.lanes.length!==2)throw Error();lanes=c.lanes.map((l,i)=>{if(l.source!==SOURCES[i]||typeof l.pending!=='boolean'||l.cursor!==null&&(typeof l.cursor!=='string'||l.cursor.length>700)||l.error!==null&&typeof l.error!=='string')throw Error();return {...l};});}catch{return empty('FOUNDATION_CURSOR_MISMATCH');}}
  const matches=[];
  for(const lane of lanes){
   if(!lane.pending)continue;lane.pending=false;lane.error=null;
   const url=new URL('/api/corpus/foundation','http://offmenu.invalid');url.searchParams.set('source',lane.source);url.searchParams.set('barcode',raw);url.searchParams.set('limit','20');if(lane.cursor)url.searchParams.set('cursor',lane.cursor);
   try{
    const response=await fetchImpl(url.pathname+url.search,{method:'GET',credentials:'omit',cache:'no-store',redirect:'error',mode:'same-origin',headers:{Accept:'application/json'}});lane.status=response.status;
    if(response.status!==200){lane.error=response.status===503?'OWN_DATA_UNAVAILABLE':response.status===401||response.status===403?'FOUNDATION_ACCESS_UNAVAILABLE':'FOUNDATION_QUERY_UNAVAILABLE';continue;}
    const body=await response.text();if(new TextEncoder().encode(body).byteLength>2097152)throw Error('FOUNDATION_RESPONSE_BOUND');const data=JSON.parse(body);
    if(data.schemaVersion!=='1.0'||data.fieldContract!==FOUNDATION_CONTRACT||data.source!==lane.source||data.barcode!==raw||data.releaseId!==FOUNDATION_SELECTION.releaseId||data.manifestSha256!==FOUNDATION_SELECTION.manifestSha256||data.externalFallback!==false||data.physicalProductEquivalenceAsserted!==false||data.goldAdmitted!==false||data.fullProductComplete!==false||data.httpStatus!==200||data.status!=='phase-qualified-own-data'||!Array.isArray(data.records)||data.records.length<1||data.records.length>20||!Number.isSafeInteger(data.qualifiedSourceObservationCount)||data.qualifiedSourceObservationCount<data.records.length||data.nextCursor!==null&&(typeof data.nextCursor!=='string'||data.nextCursor.length>700||!data.nextCursor.length)||data.records.some(r=>!validRecord(r,lane.source,raw)))throw Error('FOUNDATION_RESPONSE_MISMATCH');
    if(new Set(data.records.map(key)).size!==data.records.length)throw Error('FOUNDATION_DUPLICATE_OBSERVATION');
    matches.push(...data.records.map(project));lane.cursor=data.nextCursor;lane.pending=data.nextCursor!==null;lane.observationCount=data.qualifiedSourceObservationCount;
   }catch{lane.error='FOUNDATION_RESPONSE_UNAVAILABLE';lane.pending=false;}
  }
  return output(raw,generation,symbology,cursor,union([],matches),lanes);
 };
}
export const lookupIdentifiers=createFoundationScannerLookup();
export function mergeIdentifierPages(previous,next){
 if(!previous.foundationLookup||!next.foundationLookup||previous.original!==next.original||previous.generation!==next.generation||previous.symbology!==next.symbology||previous.nextCursor!==next.requestCursor)throw Error('FOUNDATION_PAGE_CONTEXT_CHANGED');
 const matches=union(previous.matches,next.matches);return {...next,matches,status:next.providerStates.some(l=>l.error)?(matches.length?'partial':'unavailable'):matches.length>1||matches.length&&next.hasMore?'ambiguous':matches.length?'source-match':'unavailable'};
}
const show=x=>x===null||x===undefined?'Unknown':typeof x==='object'?JSON.stringify(x):String(x);
export function foundationReadout(selected,entry,tab='overview'){
 const rows=[{label:'Foundation observations',text:'Source-qualified base and type only. Full product, nutrition/recipe joins, normalization, Gold and automatic inventory/planning remain unaccepted. Distinct observations are not physical-product equivalence.'}];
 for(const lane of entry?.providerStates||[])rows.push({label:'Source · '+lane.source,text:lane.error?lane.error+' · selected representation unavailable, not global absence':show(lane.observationCount)+' selected source observations'+(lane.pending?' · more pages remain':'')});
 const r=selected?.foundationRecord;if(!r){rows.push({label:'Source choice',text:'Inspect the separate source observations. No product identity is inferred from the code alone.'});return rows;}
 const d=r.data,p=r.provenance;
 rows.push({label:'Canonical English base',text:d.name},{label:'Meaningful type',text:d.meaningfulType.canonicalEnglishLabel},{label:'Ingredient eligibility',text:d.classification},{label:'Source notice',text:p.attribution+' · '+p.license},{label:'Source observation',text:p.sourceId+' · '+p.releaseId+' · '+p.recordId});
 if(tab==='nutrition')rows.push({label:'Nutrition',text:'Not joined or accepted by this foundation response. Unknown, not zero.'});
 if(tab==='overview'||tab==='ingredients')for(const [axis,value]of Object.entries(d.variantParameters))rows.push({label:axis+' · '+value.state,text:value.state==='unknown'?'Unknown · '+show(value.reason)+' · '+show(value.qualificationDisposition):show(value.value)});
 if(tab==='source'){rows.push({label:'Exact source binding',text:JSON.stringify(p)},{label:'Reviewed type relation',text:JSON.stringify(d.meaningfulType)},{label:'All parameter states and evidence',text:JSON.stringify(d.variantParameters)},{label:'Complete supplied foundation observation',text:JSON.stringify(r)});}
 return rows;
}
