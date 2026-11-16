import {recordPermission} from './record-policy.js';
import {asOffNutriments} from './nutrient-profile.js';

// A user's explicit source-profile selection applies to one reviewed pantry lot.
// It is not a canonical product/ingredient join or a new source-use grant.
export const LOT_NUTRITION_SCHEMA='offmenu-lot-nutrition-selection/1';
const keys=new Set(['energy-kcal_100g','proteins_100g','carbohydrates_100g','fat_100g','sugars_100g','salt_100g','sodium_100g','saturated-fat_100g','fiber_100g','calcium_100g','iron_100g','potassium_100g','vitamin-c_100g']);
const provenanceKeys=['sourceId','recordId','releaseId','url','licenseUrl','license','attribution','fetchedAt','sourceDate','transform','visibility','privateUseConfirmed','recordUseVersion','policyVersion','retainUntil','accessExpiresAt','status','dependencies','sourceDocumentSha256'];
const text=(v,n)=>typeof v==='string'&&v.length>0&&v.length<=n;
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
function requireThat(value){if(!value)throw Error('Selected nutrition needs a complete lot, source profile and compatible per-100 basis.');}
function jsonCopy(value){
 function check(v,depth=0){requireThat(depth<=20);if(typeof v==='number')requireThat(Number.isFinite(v));if(v&&typeof v==='object')for(const[k,item]of Object.entries(v)){requireThat(!['__proto__','constructor','prototype'].includes(k));check(item,depth+1);}}
 check(value);const encoded=JSON.stringify(value);requireThat(typeof encoded==='string'&&new TextEncoder().encode(encoded).length<=65536);
 return JSON.parse(encoded);
}
function permitted(selection,now){
 const record={kind:'nutrientProfile',provenance:selection.provenance};
 return recordPermission(record,{action:'derive',confirmed:selection.provenance.privateUseConfirmed===true,now}).allowed&&recordPermission(record,{action:'persist',confirmed:selection.provenance.privateUseConfirmed===true,now}).allowed;
}
export function copyLotNutritionSelection(value){
 requireThat(value?.schema===LOT_NUTRITION_SCHEMA&&value.relationship==='user-selected-for-this-lot'&&value.canonicalIdentityAsserted===false);
 const s=value.scope,p=value.sourceProfile,b=p?.basis,provenance=value.provenance;
 requireThat(object(s)&&text(s.lotId,300)&&text(s.barcode,128)&&text(s.ingredient,300)&&['g','ml'].includes(s.unit));
 requireThat(p?.kind==='nutrientProfile'&&text(p.id,300)&&b?.amount===100&&b.unit===s.unit&&object(p.nutrients));
 requireThat(object(provenance)&&text(provenance.sourceId,100)&&text(provenance.license,1000)&&text(provenance.attribution,1000));
 requireThat(object(value.nutriments)&&Object.entries(value.nutriments).every(([k,v])=>keys.has(k)&&typeof v==='number'&&Number.isFinite(v)&&v>=0));
 for(const n of Object.values(p.nutrients))if(typeof n?.value==='number'&&Object.hasOwn(n,'basis')){
  requireThat(n.basis?.amount===100&&n.basis.unit===s.unit);
  if(n.basis.state&&b.state)requireThat(n.basis.state===b.state);
 }
 const expected=asOffNutriments({kind:'nutrientProfile',data:p},s.unit);
 const ordered=x=>JSON.stringify(Object.entries(x).sort(([a],[b])=>a.localeCompare(b)));
 requireThat(ordered(value.nutriments)===ordered(expected));
 return jsonCopy({schema:LOT_NUTRITION_SCHEMA,scope:s,sourceProfile:p,provenance,nutriments:value.nutriments,relationship:'user-selected-for-this-lot',canonicalIdentityAsserted:false});
}
export function createLotNutritionSelection(lot,record,nutriments,{confirmed=false,now=Date.now()}={}){
 requireThat(confirmed===true&&record?.kind==='nutrientProfile'&&record.data?.basis?.amount===100&&record.data.basis.unit===lot?.unit);
 for(const n of Object.values(record.data.nutrients||{}))if(typeof n?.value==='number'&&Object.hasOwn(n,'basis')){
  requireThat(n.basis?.amount===100&&n.basis.unit===lot.unit);
  if(n.basis.state&&record.data.basis.state)requireThat(n.basis.state===record.data.basis.state);
 }
 const provenance=Object.fromEntries(provenanceKeys.filter(k=>Object.hasOwn(record.provenance||{},k)).map(k=>[k,record.provenance[k]]));
 if(['personal-import','retailer-browser'].includes(provenance.sourceId))provenance.privateUseConfirmed=true;
 const selection=copyLotNutritionSelection({schema:LOT_NUTRITION_SCHEMA,scope:{lotId:lot.id,barcode:lot.barcode,ingredient:lot.ingredient,unit:lot.unit},
  sourceProfile:{kind:'nutrientProfile',id:record.id,basis:record.data.basis,nutrients:record.data.nutrients||{},status:record.status??record.data.status??null},
  provenance,nutriments,relationship:'user-selected-for-this-lot',canonicalIdentityAsserted:false});
 if(!permitted(selection,now))throw Error('The selected source does not permit retaining and using this nutrient profile.');
 return selection;
}
export function nutritionForLot(lot,products,{now=Date.now()}={}){
 if(!lot?.nutritionSelection)return products?.[lot?.barcode];
 try{
  const selected=copyLotNutritionSelection(lot.nutritionSelection),s=selected.scope;
  if(s.lotId!==lot.id||s.barcode!==lot.barcode||s.ingredient!==lot.ingredient||s.unit!==lot.unit||!permitted(selected,now))return null;
  return {name:lot.name,nutriments:selected.nutriments,nutritionProvenance:{...selected.provenance,
   nutrientProfile:{id:selected.sourceProfile.id,basis:selected.sourceProfile.basis,status:selected.sourceProfile.status},
   relationship:selected.relationship,canonicalIdentityAsserted:false}};
 }catch{return null;}
}
