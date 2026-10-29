import {canonicalIngredient} from './ingredients.js';
export const normalize = canonicalIngredient;
export function validateLot(value) {
  const lot = {id: String(value.id || crypto.randomUUID()), barcode: String(value.barcode || ''),name: String(value.name||'').trim(),ingredient: normalize(value.ingredient||''),quantity: Number(value.quantity),unit: value.unit,expires: value.expires || null};
  if(!(/^[0-9]{4,32}$/.test(lot.barcode)||/^local:[a-zA-Z0-9-]{1,100}$/.test(lot.barcode)) || !lot.name || !lot.ingredient || !Number.isFinite(lot.quantity) || lot.quantity<0 || !['g','ml','count'].includes(lot.unit)) throw Error('Check barcode, name, ingredient, quantity and unit.');
  if(lot.expires && (!/^\d{4}-\d{2}-\d{2}$/.test(lot.expires) || !Number.isFinite(Date.parse(lot.expires)))) throw Error('Invalid expiry date.');
  if(value.location){
    if(typeof value.location.area!=='string'||!value.location.area.trim()||value.location.area.length>60||typeof value.location.shelf!=='string'||!value.location.shelf.trim()||value.location.shelf.length>60)throw Error('Choose a valid storage area and shelf.');
    lot.location={area:value.location.area,shelf:value.location.shelf.trim()};
  }
  if(value.checkedAt&&typeof value.checkedAt==='string')lot.checkedAt=value.checkedAt.slice(0,40);
  if(['full-pack','package','manual'].includes(value.amountBasis))lot.amountBasis=value.amountBasis;
  if(typeof value.needsReview==='boolean')lot.needsReview=value.needsReview;
  if(value.freshnessReminder){if(!/^\d{4}-\d{2}-\d{2}$/.test(value.freshnessReminder)||!Number.isFinite(Date.parse(value.freshnessReminder)))throw Error('Invalid freshness reminder.');lot.freshnessReminder=value.freshnessReminder;if(Number.isInteger(value.freshnessDays)&&value.freshnessDays>0&&value.freshnessDays<=3650)lot.freshnessDays=value.freshnessDays;lot.freshnessNote=typeof value.freshnessNote==='string'?value.freshnessNote.slice(0,200):'';}
  if(value.discardQuantity!=null){if(!Number.isFinite(value.discardQuantity)||value.discardQuantity<=0||value.discardQuantity>lot.quantity)throw Error('Invalid discard amount.');lot.discardQuantity=value.discardQuantity;}
  if(value.cookBatchId)lot.cookBatchId=String(value.cookBatchId).slice(0,100);
  if(value.dateType)lot.dateType=value.dateType==='best-before'?'best-before':'use-by';
  return lot;
}
export function matchMeals(inventory,recipes,servings,today) {
  if(!Number.isFinite(servings)||servings<=0)throw Error('Enter a positive serving count.');
  const stock=new Map();for(const item of inventory){if(item.needsReview)continue;if(item.expires && item.expires<today)continue;const key=normalize(item.ingredient)+'|'+item.unit;stock.set(key,(stock.get(key)||0)+Number(item.quantity));}
  return recipes.map(recipe=>{const needs=new Map(),unknown=[];for(const item of recipe.ingredients){if(item.optional)continue;if(item.quantity==null||!item.unit){unknown.push(item.ingredient);continue}const key=normalize(item.ingredient)+'|'+item.unit;needs.set(key,(needs.get(key)||0)+item.quantity*servings/recipe.servings)}const missing=[];let met=0;for(const [key,required]of needs){const available=stock.get(key)||0;if(available>=required)met++;else{const [ingredient,unit]=key.split('|');missing.push({ingredient,unit,quantity:Math.round((required-available)*1000)/1000})}}return {...recipe,missing,unknown,coverage:needs.size?met/needs.size:0,status:missing.length?'missing':unknown.length||!recipe.ingredients.length?'needs_review':'ready'};}).sort((a,b)=>({ready:0,needs_review:1,missing:2}[a.status]-{ready:0,needs_review:1,missing:2}[b.status])||b.coverage-a.coverage||a.missing.length-b.missing.length);
}
export function validateRecipes(value){if(!Array.isArray(value)||value.length>10000)throw Error('Import a JSON array of up to 10,000 recipes.');return value.map(r=>{if(!r.id||!r.title||!r.source||!r.license||!Number.isFinite(r.servings)||r.servings<=0||!Array.isArray(r.ingredients)||!r.ingredients.length)throw Error('Recipes need id, title, source, license, servings and ingredients.');for(const i of r.ingredients){if(!i.ingredient||(i.quantity!=null&&(!Number.isFinite(i.quantity)||i.quantity<0))||(i.unit!=null&&!['g','ml','count'].includes(i.unit)))throw Error('Invalid recipe ingredient.');}if(!Array.isArray(r.instructions)||r.instructions.some(x=>typeof x!=='string'))throw Error('Instructions must be a list of strings.');return r;});}
