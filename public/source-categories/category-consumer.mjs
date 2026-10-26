// Generic data-only consumer. No actual category inventory, fetch, storage,
// icon taxonomy or product observation construction is embedded here.
export const CATEGORY_CONSUMER='offmenu-current-source-category-consumer/1';
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const text=x=>typeof x==='string'&&x.length>0;
const ptr=x=>'/'+x.replaceAll('~','~0').replaceAll('/','~1');
const reason='NO_APPROVED_CATEGORY_TYPE_ICON_CROSSWALK';
export function compileCategoryConsumer({crosswalk,taxonomy}){
 // Isolate the verified input snapshot without mutating or freezing caller data.
 ({crosswalk,taxonomy}=structuredClone({crosswalk,taxonomy}));
 if(crosswalk?.schema!=='offmenu-off-current-category-label-crosswalk/1'||!Array.isArray(crosswalk.rows)||!object(taxonomy))throw Error('Exact source-local crosswalk and taxonomy required');
 const source=crosswalk.sourceEvidence?.['official-category-snapshot-0'];
 if(!source?.raw?.sha256||!source.url)throw Error('Pinned taxonomy source required');
 const rows=new Map();
 for(const row of crosswalk.rows){
  if(!text(row.sourceNamespace)||!text(row.exactCategoryID)||row.iconType!==null)throw Error('Exact category key and unresolved icon required');
  const key=JSON.stringify([row.sourceNamespace,row.exactCategoryID]);
  if(rows.has(key))throw Error('Duplicate source category key');rows.set(key,structuredClone(row));
 }
 return Object.freeze({
  resolve(namespace,id,{language='en'}={}){
   const row=rows.get(JSON.stringify([namespace,id]));
   const empty={schema:CATEGORY_CONSUMER,sourceNamespace:namespace,exactCategoryID:id,status:'unresolved',displayLabel:null,displayLanguage:null,sourceLabels:null,EnglishDisplayLabel:null,sourceLocalTypeCandidates:[],iconType:null,visualAction:'retain-existing-shared-resolver-fallback',unresolvedReasons:[],provenance:{sourceSnapshot:source.raw,sourceURL:source.url,currentToHistoricalDefinitionEquivalence:false}};
   if(!row){empty.unresolvedReasons=['CATEGORY_NOT_IN_SELECTED_6392_INVENTORY',reason];return structuredClone(empty);}
   if(row.mappingDisposition!=='exact-current-source-category-id'){
    empty.unresolvedReasons=[...row.unresolvedReasons,reason];return structuredClone(empty);
   }
   const node=taxonomy[id];
   if(namespace!=='off'||!object(node)||!object(node.name)||JSON.stringify(row.sourceLabels)!==JSON.stringify(node.name)||row.EnglishDisplayLabel!==(node.name.en??null))throw Error('Crosswalk/source category label binding mismatch');
   const labels=structuredClone(node.name),requested=text(labels[language])?language:text(labels.en)?'en':null;
   const parents=Array.isArray(node.parents)?node.parents:[];
   const candidates=[];const gaps=[];
   parents.forEach((parent,index)=>{
    const definition=taxonomy[parent];
    if(!text(parent)||!object(definition)||!object(definition.name)){gaps.push('SOURCE_PARENT_DEFINITION_UNAVAILABLE');return;}
    candidates.push({sourceNamespace:'off',sourceCategoryID:parent,sourceLabels:structuredClone(definition.name),EnglishDisplayLabel:definition.name.en??null,relation:'declared-source-category-parent',status:'source-local-type-candidate-not-admitted',evidence:{childPointer:ptr(id)+'/parents/'+index,parentPointer:ptr(parent),taxonomySnapshot:source.raw},identityEquivalence:false});
   });
   return structuredClone({...empty,status:'exact-current-source-category',displayLabel:requested?labels[requested]:null,displayLanguage:requested,sourceLabels:labels,EnglishDisplayLabel:row.EnglishDisplayLabel,sourceLocalTypeCandidates:candidates,parentMultiplicity:candidates.length>1?'multiple-preserved':candidates.length===1?'single':'none',unresolvedReasons:[...new Set([...row.unresolvedReasons,...gaps,...(!requested?['REQUESTED_OR_ENGLISH_LABEL_NOT_SUPPLIED']:[])])],provenance:{...empty.provenance,categoryPointer:ptr(id),census:crosswalk.census,relation:'exact-source-local-ID-lookup-current-taxonomy-only'}});
  },
  inventoryCount:rows.size,
  semanticAdmission:false,
  approvedIconMappings:0
 });
}
