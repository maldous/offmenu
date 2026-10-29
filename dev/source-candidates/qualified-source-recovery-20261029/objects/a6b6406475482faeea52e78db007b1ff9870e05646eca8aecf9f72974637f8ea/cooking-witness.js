// Detached cooking-time provenance, not an upstream identity or source-use grant.
export const COOKING_WITNESS_SCHEMA='offmenu-cooking-witness/1';
const recipeKeys=['id','title','servings','servingsUnknown','needsReview','source','license','attribution','version','revision','authoredRevision','sourceRecipeId','sourceVariantId','variantId','releaseId','manifestSha256','sourceDocumentSha256'];
const ingredientKeys=['ingredient','ingredientId','quantity','unit','optional','raw','originalText','sourceQuantity','sourceUnit','scaling','sourceScaling','foodMatchStatus','sourceIngredientId'];
const provenanceKeys=['sourceId','recordId','releaseId','version','revision','manifestSha256','sourceDocumentSha256','originalSha256','inputAssetSha256','recordSha256','url','historyUrl','licenseUrl','license','attribution','sourceDate','fetchedAt','visibility','status','citationIds'];
const versionKeys=['version','revision','authoredRevision'];
const hasDeclaredVersion=r=>versionKeys.some(k=>r[k]!==undefined&&r[k]!==null)||['version','revision'].some(k=>r.provenance?.[k]!==undefined&&r.provenance[k]!==null)||['version','revision'].some(k=>r.provenance?.personalReview?.[k]!==undefined&&r.provenance.personalReview[k]!==null);
const nutrientKeys=['energy-kcal_100g','proteins_100g','carbohydrates_100g','fat_100g','sugars_100g','salt_100g','sodium_100g','saturated-fat_100g','fiber_100g','calcium_100g','iron_100g','potassium_100g','vitamin-c_100g'];
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const text=(v,max=300)=>typeof v==='string'&&v.length>0&&v.length<=max;
function requireThat(v){if(!v)throw Error('Cooking witness does not match the recorded batch and recipe.');}
function clone(value){
 function check(v,depth=0){requireThat(depth<=16);if(typeof v==='number')requireThat(Number.isFinite(v));if(typeof v==='string')requireThat(v.length<=16000);if(v&&typeof v==='object')for(const[k,x]of Object.entries(v)){requireThat(!['__proto__','constructor','prototype','credentials','password','token','apiKey','secret'].includes(k));check(x,depth+1);}}
 check(value);const encoded=JSON.stringify(value);requireThat(typeof encoded==='string'&&new TextEncoder().encode(encoded).length<=262144);return JSON.parse(encoded);
}
const pick=(v,keys)=>Object.fromEntries(keys.filter(k=>Object.hasOwn(v||{},k)&&v[k]!==undefined).map(k=>[k,clone(v[k])]));
function provenance(p){
 const out=pick(p,provenanceKeys);
 if(object(p?.personalReview))out.personalReview=pick(p.personalReview,['reviewedAt','sourceRecipeId','revision','version']);
 if(Array.isArray(p?.citations))out.citations=p.citations.map(c=>pick(c,['id',...provenanceKeys]));
 return out;
}
function freeze(v){if(v&&typeof v==='object'){Object.values(v).forEach(freeze);Object.freeze(v);}return v;}
export function captureNutrientInput(allocation,product){
 const p=product?.nutritionProvenance,profile=p?.nutrientProfile;
 const selected=allocation.original?.nutritionSelection;
 const sourceContext=p?.relationship==='user-selected-for-this-lot'&&selected?.sourceProfile?.id===profile?.id?selected.sourceProfile.nutrients:null;
 return clone({lotId:allocation.lotId,quantity:allocation.quantity,unit:allocation.unit,
  profileState:product?'supplied-input':'unknown',profileReference:profile?pick(profile,['id','basis','status']):null,
  provenance:provenance(p),declaredBasisLabel:product?.nutrition_data_per??null,
  sourceNutrientContext:sourceContext,
  nutriments:pick(product?.nutriments,nutrientKeys),relationship:p?.relationship??null,
  canonicalIdentityAsserted:false});
}
export function createCookingWitness(recipe,batchId,allocations,nutrientInputs){
 const snapshot={...pick(recipe,recipeKeys),provenance:provenance(recipe.provenance),
  ingredients:recipe.ingredients.map(i=>pick(i,ingredientKeys)),
  ...(Array.isArray(recipe.instructions)?{instructions:recipe.instructions.map(x=>clone(x))}:{})};
 const hasVersion=hasDeclaredVersion(snapshot);
 const inputs=allocations.map(a=>({lotId:a.lotId,barcode:a.barcode,ingredient:a.ingredient,quantity:a.quantity,unit:a.unit,
  sourceReferences:pick(a.original,['publicProductReference','sourceObservationReference','foundationSourceReference','sourceIdentityReference'])}));
 const states=[recipe.provenance?.visibility,...nutrientInputs.map(n=>n.provenance.visibility),...inputs.flatMap(a=>Object.values(a.sourceReferences).map(r=>r?.provenance?.visibility??r?.visibility))];
 const visibility=states.includes('private')?'private':states.every(s=>s==='public')?'public':'unknown';
 return copyCookingWitness({schema:COOKING_WITNESS_SCHEMA,batchId,recipeId:recipe.id,recipe:snapshot,
  sourceVersionState:hasVersion?'supplied':'unknown',allocations:inputs,nutrientInputs,visibility,canonicalIdentityAsserted:false},{batchId,recipeId:recipe.id});
}
export function copyCookingWitness(value,{batchId,recipeId}={}){
 requireThat(value?.schema===COOKING_WITNESS_SCHEMA&&text(value.batchId,100)&&text(value.recipeId,200)&&value.recipe?.id===value.recipeId);
 requireThat(batchId===undefined||value.batchId===batchId);requireThat(recipeId===undefined||value.recipeId===recipeId);
 requireThat(['supplied','unknown'].includes(value.sourceVersionState)&&['public','private','unknown'].includes(value.visibility)&&value.canonicalIdentityAsserted===false);
 requireThat(Array.isArray(value.recipe.ingredients)&&value.recipe.ingredients.length<=1000&&Array.isArray(value.allocations)&&value.allocations.length<=1000&&Array.isArray(value.nutrientInputs)&&value.nutrientInputs.length===value.allocations.length);
 const recipe={...pick(value.recipe,recipeKeys),provenance:provenance(value.recipe.provenance),ingredients:value.recipe.ingredients.map(i=>pick(i,ingredientKeys)),
  ...(Array.isArray(value.recipe.instructions)?{instructions:value.recipe.instructions.map(x=>{requireThat(typeof x==='string');return clone(x);})}:{})};
 requireThat(value.sourceVersionState===(hasDeclaredVersion(recipe)?'supplied':'unknown'));
 const allocations=value.allocations.map((a,index)=>{
  const n=value.nutrientInputs[index];requireThat(text(a.lotId,300)&&text(a.barcode,512)&&text(a.ingredient,300)&&Number.isFinite(a.quantity)&&a.quantity>0&&['g','ml','count'].includes(a.unit));
  requireThat(n.lotId===a.lotId&&n.quantity===a.quantity&&n.unit===a.unit&&['supplied-input','unknown'].includes(n.profileState)&&n.canonicalIdentityAsserted===false);
  return {...pick(a,['lotId','barcode','ingredient','quantity','unit']),sourceReferences:pick(a.sourceReferences,['publicProductReference','sourceObservationReference','foundationSourceReference','sourceIdentityReference'])};
 });
 const nutrientInputs=value.nutrientInputs.map(n=>({...pick(n,['lotId','quantity','unit','profileState','declaredBasisLabel','relationship']),
  profileReference:n.profileReference===null?null:pick(n.profileReference,['id','basis','status']),sourceNutrientContext:n.sourceNutrientContext===null?null:clone(n.sourceNutrientContext),provenance:provenance(n.provenance),nutriments:pick(n.nutriments,nutrientKeys),canonicalIdentityAsserted:false}));
 // Public visibility must be explicit on every retained source; no default grant.
 const states=[recipe.provenance.visibility,...nutrientInputs.map(n=>n.provenance.visibility),...allocations.flatMap(a=>Object.values(a.sourceReferences).map(r=>r?.provenance?.visibility??r?.visibility))];
 requireThat(value.visibility!=='public'||states.every(s=>s==='public'));
 return freeze(clone({schema:COOKING_WITNESS_SCHEMA,batchId:value.batchId,recipeId:value.recipeId,recipe,
  sourceVersionState:value.sourceVersionState,allocations,nutrientInputs,visibility:value.visibility,canonicalIdentityAsserted:false}));
}
export function sharedCookingBatch(batch){
 const {cookingWitness,...rest}=batch;
 return cookingWitness?.visibility==='public'?{...rest,cookingWitness:copyCookingWitness(cookingWitness,{batchId:batch.id,recipeId:batch.recipeId})}:rest;
}
export function historyCookingWitness(row){
 requireThat(text(row?.batchId,100)&&text(row.recipeId,200));
 return copyCookingWitness(row.cookingWitness,{batchId:row.batchId,recipeId:row.recipeId});
}
// Server integration seam: call after existing state validation, using its input
// and output. Only this additive field is copied; normalized values stay intact.
export function preserveCookingWitnesses(input,normalized){
 const out={...normalized};
 for(const key of ['batches','history'])if(Array.isArray(normalized[key])){
  const supplied=new Map((input?.[key]||[]).map(row=>[row.id,row]));
  out[key]=normalized[key].map(row=>{const original=supplied.get(row.id);if(!original?.cookingWitness)return row;
   const batchId=key==='batches'?row.id:row.batchId;requireThat(text(batchId,100));
   return {...row,cookingWitness:copyCookingWitness(original.cookingWitness,{batchId,recipeId:row.recipeId})};});
 }
 return out;
}
