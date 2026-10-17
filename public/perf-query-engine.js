/** Pure JSON-in/JSON-out bounded retained-display query engine. No I/O or runtime custody. */
export const VERSION = 'offmenu-bounded-query/1';
export const LIMITS = Object.freeze({requestBytes:8192,inputBytes:8388608,outputBytes:4194304,rowsPerPage:25,totalRows:50,selectPaths:12,treeNodes:200000,depth:20});
const own=(o,k)=>o!==null&&typeof o==='object'&&Object.hasOwn(o,k);
const forbidden=new Set(['__proto__','prototype','constructor']);
const encoder=new TextEncoder();
const common=['id','stableid','label','country','dataType','recordClass','sourceId'];
const nutrients=['energyKJ','fat','carbohydrate','protein','sugars','fibre','fineli:ALC'];
const definitions={
 'recipes:body':{type:'recipes',cls:'body-record-reference',fields:['values.ingredientCount','values.directionsPresent','values.sourceBodyAvailable','values.yield']},
 'recipes:titles':{type:'recipes',cls:'title-only-discovery',fields:['values.sourceBodyAvailable','values.recordScope']},
 'ingredients:occurrences':{type:'ingredients',cls:'recipe-ingredient-occurrence',fields:['values.ingredientId','values.optional','values.quantityStatus','values.sourceQuantityStatus','values.sourceValue','values.sourceUnit','values.sourceRange','values.retainedAmount','values.retainedUnit']},
 'nutrition:fineli':{type:'nutrition',fields:['values.basis','values.nutrients',...nutrients.flatMap(k=>['values.nutrients.'+k,'values.nutrients.'+k+'.value'])]},
 'nutrition:mext':{type:'nutrition',fields:['values.basis','values.nutrients',...nutrients.filter(k=>!k.startsWith('fineli:')).flatMap(k=>['values.nutrients.'+k,'values.nutrients.'+k+'.value'])]}
};
const mandatory=['id','stableid','dataType','recordClass','country','countries','sourceCountries','sourceId','collectionSourceId','sourceURL','sourceDate','sourceReleaseId','attribution','license','rights','rightsEvidenceURL','localOnly','qualification','qualificationStatus','reviewStatus','valuesStatus','basis','provenance','sourceManifest','sourceContext','recordFormat','projectionVersion','originalRecord'];
class Refusal extends Error {constructor(code,message,status=400){super(message);this.code=code;this.status=status;}}
const refuse=(c,m,s=400)=>{throw new Refusal(c,m,s)};
function object(v){return v!==null&&typeof v==='object'&&!Array.isArray(v)&&(Object.getPrototypeOf(v)===Object.prototype||Object.getPrototypeOf(v)===null);}
function shape(v,required,optional=[]){if(!object(v)||required.some(k=>!own(v,k))||Object.keys(v).some(k=>!required.includes(k)&&!optional.includes(k)))refuse('INVALID_SHAPE','Unknown or missing object fields');}
function integer(v,min,max){if(!Number.isSafeInteger(v)||v<min||v>max)refuse('INVALID_BOUNDS','Bounds must be safe integers within the contract');}
function jsonBudget(value,maxBytes,maxNodes=LIMITS.treeNodes,maxDepth=LIMITS.depth){
 let nodes=0,chars=0;const seen=new Set();
 function visit(v,d){
  if(++nodes>maxNodes||d>maxDepth)refuse('INPUT_LIMIT','JSON structure exceeds bound',413);
  if(v===null||typeof v==='boolean')return;
  if(typeof v==='string'){chars+=v.length;if(chars>maxBytes)refuse('INPUT_LIMIT','String data exceeds bound',413);return;}
  if(typeof v==='number'){if(!Number.isFinite(v))refuse('INVALID_JSON','Non-finite number');return;}
  if(!object(v)&&!Array.isArray(v))refuse('INVALID_JSON','Only plain JSON data is accepted');
  if(seen.has(v))refuse('INVALID_JSON','Cyclic input');seen.add(v);
  const desc=Object.getOwnPropertyDescriptors(v);if(Reflect.ownKeys(v).some(k=>typeof k!=='string'))refuse('INVALID_JSON','Symbol properties are not accepted');
  if(Object.keys(desc).length>4096)refuse('INPUT_LIMIT','Object width exceeds bound',413);
  if(Array.isArray(v)&&v.length>4096)refuse('INPUT_LIMIT','Array length exceeds bound',413);
  for(const [k,descriptor] of Object.entries(desc)){
   if(Array.isArray(v)&&k==='length')continue;
   if(forbidden.has(k)||!('value' in descriptor)||!descriptor.enumerable)refuse('INVALID_JSON','Unsafe object property');
   chars+=k.length;visit(descriptor.value,d+1);
  }
  if(Array.isArray(v)&&Object.keys(v).length!==v.length)refuse('INVALID_JSON','Sparse arrays are not accepted');
  seen.delete(v);
 }
 visit(value,0);const bytes=encoder.encode(JSON.stringify(value)).byteLength;if(bytes>maxBytes)refuse('INPUT_LIMIT','Serialized input exceeds byte bound',413);return bytes;
}
const missing=Symbol('missing');
function get(row,path){let v=row;for(const k of path.split('.')){if(!own(v,k))return missing;v=v[k];}return v;}
function field(collection,path){if(typeof path!=='string'||path.length>80||!common.concat(definitions[collection].fields).includes(path))refuse('UNKNOWN_PATH','Path is not allowlisted',422);}
function prepare(query){
 jsonBudget(query,LIMITS.requestBytes,256,8);
 shape(query,['collection','window','select'],['filter','sort','page','include']);
 if(typeof query.collection!=='string'||!own(definitions,query.collection))refuse('UNKNOWN_COLLECTION','Collection is not allowlisted',422);
 shape(query.window,['offset','limit']);integer(query.window.offset,0,Number.MAX_SAFE_INTEGER);integer(query.window.limit,1,25);
 if(!Array.isArray(query.select)||!query.select.length||query.select.length>12||new Set(query.select).size!==query.select.length)refuse('INVALID_SELECT','Select must contain1..12 unique allowlisted paths');
 query.select.forEach(p=>field(query.collection,p));
 if(own(query,'filter')){shape(query.filter,['field','op','value']);field(query.collection,query.filter.field);if(!['eq','contains','gte','lte'].includes(query.filter.op))refuse('UNKNOWN_OPERATOR','Operator is not supported',422);const v=query.filter.value;if(!(v===null||['string','number','boolean'].includes(typeof v)))refuse('INVALID_FILTER','Filter value must be a JSON scalar');if(typeof v==='string'&&v.length>128)refuse('INPUT_LIMIT','Filter text too long',413);if(query.filter.op==='contains'&&(typeof v!=='string'||!v.length))refuse('INVALID_FILTER','contains requires a nonempty string');if(['gte','lte'].includes(query.filter.op)&&typeof v!=='number')refuse('INVALID_FILTER','Ordered numeric filter requires a finite number');}
 if(own(query,'sort')){shape(query.sort,['field','direction']);field(query.collection,query.sort.field);if(!['asc','desc'].includes(query.sort.direction))refuse('INVALID_SORT','Unknown sort direction');}
 const page=query.page??{offset:0,limit:25};shape(page,['offset','limit']);integer(page.offset,0,25);integer(page.limit,1,25);
 const include=query.include??[];if(!Array.isArray(include)||include.length>1||new Set(include).size!==include.length||include.some(k=>k!=='recipeParent')||(include.length&&query.collection!=='ingredients:occurrences'))refuse('UNSUPPORTED_RELATION','Only ingredient occurrence recipeParent is supported',422);
 return {...query,page,include};
}
function checkPage(page,collection){
 if(!object(page)||!Array.isArray(page.records)||!object(page.pagination)||!object(page.scope))refuse('INVALID_PAGE','Caller must supply a retained adapter page');
 if(page.collection!==collection||page.scope.collection!==collection||typeof page.snapshot!=='string'||!/^[a-f0-9]{64}$/.test(page.snapshot)||page.scope.snapshot!==page.snapshot||typeof page.scope.projectionVersion!=='string'||!/^[a-f0-9]{64}$/.test(page.scope.sourceManifestSHA256??''))refuse('PAGE_SCOPE_MISMATCH','Collection/snapshot/projection/source scope must be pinned',409);
 const pg=page.pagination;integer(pg.offset,0,Number.MAX_SAFE_INTEGER);integer(pg.limit,1,25);integer(pg.total,0,Number.MAX_SAFE_INTEGER);
 if(pg.offset>pg.total||page.records.length!==Math.min(pg.limit,pg.total-pg.offset)||pg.returned!==page.records.length)refuse('INVALID_PAGE','Incomplete or mismatched page');
 const ids=new Set();const d=definitions[collection];
 for(const row of page.records){
  if(!object(row)||row.dataType!==d.type||(d.cls&&row.recordClass!==d.cls)||!object(row.originalRecord))refuse('INVALID_RECORD','Retained row type or lineage missing');
  const id=row.stableid??row.id;if(typeof id!=='string'||!id.length||id.length>512||ids.has(id)||(own(row,'id')&&own(row,'stableid')&&row.id!==row.stableid))refuse('INVALID_RECORD','Stable row IDs must be unique and consistent');ids.add(id);
 }
}
function compareScalar(a,b){if(a===b||(a===missing||a===null)&&(b===missing||b===null))return 0;if(a===missing||a===null)return 1;if(b===missing||b===null)return -1;const rank={boolean:0,number:1,string:2};if(!(typeof a in rank)||!(typeof b in rank))refuse('NONSCALAR_SORT','Sort field must hold scalars',422);return typeof a===typeof b?(a<b?-1:1):rank[typeof a]-rank[typeof b];}
function passes(row,f){const v=get(row,f.field);if(v===missing)return false;if(f.op==='eq')return v===f.value;if(f.op==='contains')return typeof v==='string'&&v.includes(f.value);return typeof v==='number'&&(f.op==='gte'?v>=f.value:v<=f.value);}
function project(row,q){
 const out={};for(const k of mandatory)if(own(row,k))out[k]=row[k];
 out.selected={};out.missingSelected=[];
 for(const p of q.select){const v=get(row,p);if(v===missing)out.missingSelected.push(p);else out.selected[p]=v;}
 if(q.collection.startsWith('nutrition:')){
  if(own(row.values??{},'basis'))out.basis=row.values.basis;
  const paths=[...q.select,q.filter?.field,q.sort?.field].filter(Boolean);out.observationContext={};
  for(const p of paths){const parts=p.split('.');if(parts[0]==='values'&&parts[1]==='nutrients'&&parts.length>2&&own(row.values?.nutrients??{},parts[2]))out.observationContext[parts[2]]=row.values.nutrients[parts[2]];}
 }
 return out;
}
/** executeQuery(query, {page, relations?: {recipeParent: adapterPage}}) returns QueryResult. */
export function executeQuery(query,input){
 let cost={scannedRows:0,relationRows:0,filterComparisons:0,sortComparisons:0,relationLookups:0,returnedRows:0,inputBytes:0,outputBytes:0};
 try{
  const q=prepare(query);shape(input,['page'],['relations']);cost.inputBytes=jsonBudget(input,LIMITS.inputBytes);checkPage(input.page,q.collection);
  if(input.page.pagination.offset!==q.window.offset||input.page.pagination.limit!==q.window.limit)refuse('WINDOW_MISMATCH','Hydrated page must exactly match query window',409);
  const relations=input.relations??{};shape(relations,[],['recipeParent']);if(own(relations,'recipeParent')&&!q.include.includes('recipeParent'))refuse('UNREQUESTED_RELATION','Do not supply unused relation rows');
  let parents=new Map();if(own(relations,'recipeParent')){const p=relations.recipeParent;checkPage(p,'recipes:body');if(p.snapshot!==input.page.snapshot||p.scope.sourceManifestSHA256!==input.page.scope.sourceManifestSHA256)refuse('RELATION_SCOPE_MISMATCH','Parent snapshot and manifest must match',409);cost.relationRows=p.records.length;parents=new Map(p.records.map(r=>[r.stableid??r.id,r]));}
  cost.scannedRows=input.page.records.length;if(cost.scannedRows+cost.relationRows>50)refuse('INPUT_LIMIT','At most two25-row pages',413);
  let rows=input.page.records.map((row,ordinal)=>({row,ordinal}));if(q.filter)rows=rows.filter(({row})=>{cost.filterComparisons++;return passes(row,q.filter);});
  if(q.sort){for(const {row} of rows){const v=get(row,q.sort.field);if(v!==missing&&v!==null&&!['string','number','boolean'].includes(typeof v))refuse('NONSCALAR_SORT','Sort field must hold scalars',422);}
   rows.sort((a,b)=>{cost.sortComparisons++;const av=get(a.row,q.sort.field),bv=get(b.row,q.sort.field),cmp=compareScalar(av,bv);const nullish=av===missing||av===null||bv===missing||bv===null;return (nullish?cmp:cmp*(q.sort.direction==='desc'?-1:1))||a.ordinal-b.ordinal;});}
  const matched=rows.length;rows=rows.slice(q.page.offset,q.page.offset+q.page.limit);const resultRows=rows.map(({row})=>{
   const out=project(row,q);
   if(q.include.includes('recipeParent')){
    cost.relationLookups++;const id=row.stableid??row.id,match=/^(.*):ingredient:(0|[1-9]\d*)$/.exec(id),parentId=row.originalRecord.recordID;
    if(!match||match[1]!==parentId)refuse('RELATION_LINEAGE_MISMATCH','Occurrence ID and retained parent pointer disagree',409);
    const parent=parents.get(parentId);out.relations={recipeParent:{status:'not-supplied',parentId}};
    if(parent){const a=row.originalRecord,b=parent.originalRecord;if(a.file!==b.file||a.recordID!==b.recordID||a.jsonPointer!==(b.jsonPointer??'')+'/data/ingredients/'+match[2]||row.sourceId!==parent.sourceId||row.collectionSourceId!==parent.collectionSourceId||row.sourceReleaseId!==parent.sourceReleaseId)refuse('RELATION_LINEAGE_MISMATCH','Parent source and exact pointer must agree',409);
     out.relations.recipeParent={status:'matched-exact-retained-id',parentId,record:project(parent,{collection:'recipes:body',select:['label','values.ingredientCount','values.sourceBodyAvailable']})};}
   }
   return out;
  });cost.returnedRows=resultRows.length;
  const response={ok:true,version:VERSION,records:resultRows,scope:{kind:'bounded-fetched-window-only',collection:q.collection,snapshot:input.page.snapshot,window:{...q.window,returned:cost.scannedRows},sourceExtentTotal:input.page.pagination.total,matchedInWindow:matched,sourceScope:input.page.scope,notGlobalSearch:true,notSourceAdmission:true},pagination:{offset:q.page.offset,limit:q.page.limit,returned:resultRows.length,nextOffset:q.page.offset+resultRows.length<matched?q.page.offset+resultRows.length:null},cost};
  for(let i=0;i<4;i++){const bytes=encoder.encode(JSON.stringify(response)).byteLength;if(bytes>LIMITS.outputBytes)refuse('OUTPUT_LIMIT','Projected result exceeds byte bound',413);if(bytes===cost.outputBytes)break;cost.outputBytes=bytes;}
  // Detach all returned JSON, including lineage/qualifiers; caller cannot mutate retained input.
  return JSON.parse(JSON.stringify(response));
 }catch(error){if(!(error instanceof Refusal))throw error;return {ok:false,version:VERSION,error:{code:error.code,message:error.message,status:error.status},cost};}
}
export const CONTRACT=Object.freeze({version:VERSION,limits:LIMITS,collections:Object.fromEntries(Object.entries(definitions).map(([k,v])=>[k,Object.freeze({fields:Object.freeze(common.concat(v.fields)),include:Object.freeze(k==='ingredients:occurrences'?['recipeParent']:[])})]))});
