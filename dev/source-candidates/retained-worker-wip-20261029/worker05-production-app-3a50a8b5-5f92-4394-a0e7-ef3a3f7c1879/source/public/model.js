import {canonicalIngredient} from './ingredients.js';
export const normalize = canonicalIngredient;
export function validSourceObservationReference(ref,barcode){
 const bounded=(value,max)=>typeof value==='string'&&value.length>0&&value.length<=max;
 const key=ref?.observationKey;
 return ref?.schema==='offmenu-identifier-observation/1'&&/^[a-f0-9]{64}$/.test(ref.databaseSha256||'')&&bounded(ref.runId,100)&&ref.namespace==='barcode'&&ref.lexicalValue===barcode&&bounded(ref.sourceId,40)&&bounded(ref.releaseId,80)&&(ref.sourceRecordId===null||bounded(ref.sourceRecordId,200))&&key&&key.run_id===ref.runId&&bounded(key.input_id,250)&&Number.isSafeInteger(key.record_ordinal)&&key.record_ordinal>=0&&Number.isSafeInteger(key.assertion_id)&&key.assertion_id>0&&(ref.detailSelectionSha256===null||/^[a-f0-9]{64}$/.test(ref.detailSelectionSha256||''));
}
export function validateLot(value) {
  if(value.quantity==null||!['number','string'].includes(typeof value.quantity)||typeof value.quantity==='string'&&!value.quantity.trim())throw Error('Enter a known quantity. Missing stock amounts need review.');
  const lot = {id: String(value.id || crypto.randomUUID()), barcode: String(value.barcode || ''),name: String(value.name||'').trim(),ingredient: normalize(value.ingredient||''),quantity: Number(value.quantity),unit: value.unit,expires: value.expires || null};
  if(!(/^[0-9]{4,32}$/.test(lot.barcode)||/^local:[a-zA-Z0-9-]{1,100}$/.test(lot.barcode)) || !lot.name || !lot.ingredient || !Number.isFinite(lot.quantity) || lot.quantity<0 || !['g','ml','count'].includes(lot.unit)) throw Error('Check barcode, name, ingredient, quantity and unit.');
  if(lot.expires && (!/^\d{4}-\d{2}-\d{2}$/.test(lot.expires) || !Number.isFinite(Date.parse(lot.expires)))) throw Error('Invalid expiry date.');
  if(value.location){
    if(typeof value.location.area!=='string'||!value.location.area.trim()||value.location.area.length>60||typeof value.location.shelf!=='string'||!value.location.shelf.trim()||value.location.shelf.length>60)throw Error('Choose a valid storage area and shelf.');
    lot.location={area:value.location.area,shelf:value.location.shelf.trim()};
  }
  if(value.checkedAt&&typeof value.checkedAt==='string')lot.checkedAt=value.checkedAt.slice(0,40);
  if(['full-pack','package','manual'].includes(value.amountBasis))lot.amountBasis=value.amountBasis;
  if(value.sourceObservationReference){if(!validSourceObservationReference(value.sourceObservationReference,lot.barcode))throw Error('Retained source reference is incomplete or does not match the barcode.');lot.sourceObservationReference=value.sourceObservationReference;}
  if(typeof value.needsReview==='boolean')lot.needsReview=value.needsReview;
  if(value.freshnessReminder){if(!/^\d{4}-\d{2}-\d{2}$/.test(value.freshnessReminder)||!Number.isFinite(Date.parse(value.freshnessReminder)))throw Error('Invalid freshness reminder.');lot.freshnessReminder=value.freshnessReminder;if(Number.isInteger(value.freshnessDays)&&value.freshnessDays>0&&value.freshnessDays<=3650)lot.freshnessDays=value.freshnessDays;lot.freshnessNote=typeof value.freshnessNote==='string'?value.freshnessNote.slice(0,200):'';}
  if(value.discardQuantity!=null){if(!Number.isFinite(value.discardQuantity)||value.discardQuantity<=0||value.discardQuantity>lot.quantity)throw Error('Invalid discard amount.');lot.discardQuantity=value.discardQuantity;}
  if(value.cookBatchId)lot.cookBatchId=String(value.cookBatchId).slice(0,100);
  if(value.dateType)lot.dateType=value.dateType==='best-before'?'best-before':'use-by';
  return lot;
}
// Shared by readiness and consumption: only usable, measured stock can fund a meal.
export function eligibleStock(item,today) {
  return !item.needsReview&&!(item.expires&&item.expires<today)&&Number.isFinite(item.quantity)&&item.quantity>0&&['g','ml','count'].includes(item.unit)&&typeof item.ingredient==='string'&&!!normalize(item.ingredient)&&!normalize(item.ingredient).startsWith('review:');
}
export function matchMeals(inventory,recipes,servings,today) {
  if(!Number.isFinite(servings)||servings<=0)throw Error('Enter a positive serving count.');
  const stock=new Map();for(const item of inventory){if(!eligibleStock(item,today))continue;const key=normalize(item.ingredient)+'|'+item.unit;stock.set(key,(stock.get(key)||0)+item.quantity);}return recipes.map(recipe=>{const needs=new Map(),unknown=[],reviewReasons=[];const yieldKnown=!recipe.servingsUnknown&&Number.isFinite(recipe.servings)&&recipe.servings>0;if(!yieldKnown)reviewReasons.push('yield_unknown');if(recipe.needsReview)reviewReasons.push('source_review_required');const demandResolved=yieldKnown&&!recipe.needsReview;for(const item of recipe.ingredients){if(item.optional)continue;if(!demandResolved||item.quantity==null||!item.unit){unknown.push(item.ingredient);continue;}const key=normalize(item.ingredient)+'|'+item.unit;needs.set(key,(needs.get(key)||0)+item.quantity*servings/recipe.servings);}const missing=[];let met=0;for(const [key,required]of needs){const available=stock.get(key)||0;if(available>=required)met++;else{const [ingredient,unit]=key.split('|');missing.push({ingredient,unit,quantity:Math.round((required-available)*1000)/1000});}}return {...recipe,missing,unknown,reviewReasons,demandKnown:demandResolved&&!unknown.length,coverage:demandResolved?(needs.size?met/needs.size:0):null,status:reviewReasons.length?'needs_review':missing.length?'missing':unknown.length||!recipe.ingredients.length?'needs_review':'ready'};}).sort((a,b)=>({ready:0,needs_review:1,missing:2}[a.status]-{ready:0,needs_review:1,missing:2}[b.status])||b.coverage-a.coverage||a.missing.length-b.missing.length);
}
export function validateRecipes(value){if(!Array.isArray(value)||value.length>10000)throw Error('Import a JSON array of up to 10,000 recipes.');return value.map(r=>{if(!r.id||!r.title||!r.source||!r.license||!Number.isFinite(r.servings)||r.servings<=0||!Array.isArray(r.ingredients)||!r.ingredients.length)throw Error('Recipes need id, title, source, license, servings and ingredients.');for(const i of r.ingredients){if(!i.ingredient||(i.quantity!=null&&(!Number.isFinite(i.quantity)||i.quantity<0))||(i.unit!=null&&!['g','ml','count'].includes(i.unit)))throw Error('Invalid recipe ingredient.');}if(!Array.isArray(r.instructions)||r.instructions.some(x=>typeof x!=='string'))throw Error('Instructions must be a list of strings.');return r;});}
