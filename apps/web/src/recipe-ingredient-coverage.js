import {matchMeals,normalize,eligibleStock} from './model.js';
import {quantified} from './ingredients.js';
import {allocateIngredients} from './cooking-model.js';
import {nutrientBasisCompatible} from './menu-model.js';

const dateKnown=value=>typeof value==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(value)&&
 Number.isFinite(Date.parse(value+'T00:00:00Z'))&&new Date(value+'T00:00:00Z').toISOString().slice(0,10)===value;
const locationOf=lot=>typeof lot.location?.area==='string'&&lot.location.area.trim()&&
 typeof lot.location.shelf==='string'&&lot.location.shelf.trim()
 ?{area:lot.location.area,shelf:lot.location.shelf}:null;
const finiteSum=rows=>rows.reduce((sum,row)=>sum+row.quantity,0);

/** Presentation over an already admitted, caller-selected kitchen snapshot.
 * Existing vocabulary, matching, FEFO allocation and nutrient-basis checks own
 * their decisions. This never admits a recipe/product or consumes real stock.
 * Allocation retains the existing allocator's binary64 and 1e-7 cutoff.
 */
export function recipeIngredientCoverage({recipe,inventory,products={},servings,date}={}){
 if(!recipe||!Array.isArray(recipe.ingredients)||!recipe.ingredients.length||recipe.ingredients.length>1000||
  !Array.isArray(inventory)||inventory.length>10000||!products||typeof products!=='object'||Array.isArray(products)||!dateKnown(date))
  throw new TypeError('Recipe, bounded inventory, product map and explicit date required.');
 const r=structuredClone(recipe),stock=structuredClone(inventory),p=structuredClone(products),ids=new Set();
 if(r.ingredients.some(i=>!i||typeof i.ingredient!=='string'||!i.ingredient.trim()))
  throw new TypeError('Recipe ingredient names must be explicit.');
 for(const lot of stock){
  if(!lot||typeof lot.id!=='string'||!lot.id||ids.has(lot.id)||
   lot.expires!=null&&!dateKnown(lot.expires))throw new TypeError('Unique lot IDs and valid declared expiry dates required.');
  ids.add(lot.id);
 }
 const matching=matchMeals(stock,[r],servings,date)[0];
 const required=r.ingredients.map((ingredient,index)=>({ingredient,index})).filter(x=>!x.ingredient.optional);
 const demandKnown=quantified(r)&&required.length>0&&required.every(({ingredient})=>{
  const amount=ingredient.quantity*servings/r.servings;return Number.isFinite(amount)&&amount>0;
 });
 // The allocator expects admitted measured stock. Unknown stock is retained as
 // uncertainty, never coerced to zero or allowed into its deduction loop.
 let remaining=stock.filter(lot=>eligibleStock(lot,date));
 const requirements=required.map(({ingredient,index})=>{
  const base={index,ingredient:ingredient.ingredient,canonicalIngredient:normalize(ingredient.ingredient),
   unit:ingredient.unit??null,requiredQuantity:demandKnown?ingredient.quantity*servings/r.servings:null};
  if(!demandKnown)return {...base,status:'unknown',reason:'unresolved-recipe-demand',coveredQuantity:null,
   uncoveredQuantity:null,unallocatedKnownDemand:null,allocations:[],nutritionBasisEligible:null};
  // Carry actual deductions into the next source line. The allocator's final
  // returned inventory filters tiny lots, including unrelated later demand;
  // preserve those rows here as a whole-recipe allocation would do internally.
  const allocated=allocateIngredients({...r,ingredients:[ingredient]},remaining,servings,date);
  const used=new Map(allocated.deductions.map(d=>[d.lotId,d.quantity]));
  remaining=remaining.map(lot=>({...lot,quantity:lot.quantity-(used.get(lot.id)??0)}));
  const allocations=allocated.deductions.map(d=>{
   const product=Object.hasOwn(p,d.barcode)?p[d.barcode]:null;
   return {lotId:d.lotId,barcode:d.barcode,quantity:d.quantity,unit:d.unit,
    location:locationOf(d.original),expires:d.original.expires??null,
    nutritionBasisEligible:nutrientBasisCompatible(product,d.unit)===true};
  });
  const coveredQuantity=finiteSum(allocations),unallocatedKnownDemand=finiteSum(allocated.missing);
  const uncertainStock=unallocatedKnownDemand>0&&stock.some(lot=>{
   if(lot.needsReview||lot.expires&&lot.expires<date)return false;
   const name=typeof lot.ingredient==='string'?normalize(lot.ingredient):'';
   if(name&&name!==base.canonicalIngredient)return false;
   return !name||!Number.isFinite(lot.quantity)||lot.quantity<0||!['g','ml','count'].includes(lot.unit);
  });
  const unknown=uncertainStock||!Number.isFinite(coveredQuantity)||!Number.isFinite(unallocatedKnownDemand);
  const status=unknown?'unknown':allocated.missing.length?'uncovered':'covered';
  return {...base,status,reason:unknown?'unresolved-inventory-quantity-or-identity-or-unit':
   status==='covered'?'existing-allocation-covered':'existing-allocation-uncovered',
   coveredQuantity:Number.isFinite(coveredQuantity)?coveredQuantity:null,
   uncoveredQuantity:unknown?null:unallocatedKnownDemand,
   unallocatedKnownDemand:Number.isFinite(unallocatedKnownDemand)?unallocatedKnownDemand:null,allocations,
   nutritionBasisEligible:status==='unknown'?null:status==='covered'&&allocations.length>0&&allocations.every(a=>a.nutritionBasisEligible)};
 });
 const allCovered=requirements.length>0&&requirements.every(i=>i.status==='covered');
 // Existing matching uses exact comparisons while allocation has a cutoff.
 // Keep both observations; don't invent a tolerance or present a zero-gap
 // extra-item choice when those existing contracts disagree.
 const classificationAgreement=matching.status==='ready'?allCovered:
  matching.status==='missing'?!allCovered:true;
 // Matching rounds its displayed deficits independently of allocation. A
 // zero/nonfinite reported gap cannot support a definitive extra-item choice.
 const missingQuantitiesKnown=matching.missing.every(i=>Number.isFinite(i.quantity)&&i.quantity>0);
 const unknown=!demandKnown||requirements.some(i=>i.status==='unknown')||!classificationAgreement||!missingQuantitiesKnown;
 const readyNow=!unknown&&matching.status==='ready'&&requirements.every(i=>i.status==='covered');
 const oneExtraItem=!unknown&&matching.status==='missing'&&matching.demandKnown&&
  matching.unknown.length===0&&matching.reviewReasons.length===0&&matching.missing.length===1;
 const datedLots=new Map();
 for(const row of requirements)for(const a of row.allocations)if(a.expires&&!datedLots.has(a.lotId))
  datedLots.set(a.lotId,{lotId:a.lotId,expires:a.expires,location:a.location});
 // An expiry-order hint from actual allocations, without a freshness threshold,
 // safety assertion, or an inferred location for an unlocated lot.
 const useFirstLots=[...datedLots.values()].sort((a,b)=>a.expires.localeCompare(b.expires)||a.lotId.localeCompare(b.lotId));
 return {recipeId:r.id??null,servings,date,
  matching:{status:matching.status,demandKnown:matching.demandKnown,coverage:matching.coverage,
   missing:matching.missing,unknown:matching.unknown,reviewReasons:matching.reviewReasons},
  requirements,classificationAgreement,choices:{readyNow,oneExtraItem,unknown},useFirstLots,
  nutritionBasisEligible:!unknown&&readyNow&&requirements.every(i=>i.nutritionBasisEligible===true),
  scope:'Selected admitted snapshot only; inherited vocabulary/matching/allocation. Basis eligibility is not nutrient completeness, food safety, recipe admission or cooking/serving evidence.'};
}
