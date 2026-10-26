import {normalize,eligibleStock} from './model.js';
import {measuredIngredient} from './ingredients.js';
export const NUTRIENTS=[['energy-kcal_100g','Energy','kcal'],['proteins_100g','Protein','g'],['carbohydrates_100g','Carbs','g'],['fat_100g','Fat','g'],['sugars_100g','Sugars','g'],['salt_100g','Salt','g'],['sodium_mg_100g','Sodium','mg'],['saturated-fat_100g','Saturated fat','g'],['fiber_100g','Fibre','g'],['calcium_100g','Calcium','mg'],['iron_100g','Iron','mg'],['potassium_100g','Potassium','mg'],['vitamin-c_100g','Vitamin C','mg']];
export function nutrientValue(n,key){if(key==='sodium_mg_100g')return Number.isFinite(n?.sodium_100g)?n.sodium_100g*1000:Number.isFinite(n?.salt_100g)?n.salt_100g*400:undefined;if(['calcium_100g','iron_100g','potassium_100g','vitamin-c_100g'].includes(key))return Number.isFinite(n?.[key])?n[key]*1000:undefined;return n?.[key];}
// A package amount is not a nutrient denominator; mass/volume need explicit evidence.
export function nutrientBasisCompatible(product,unit){
 if(!['g','ml'].includes(unit)||!product)return false;
 const provenance=product.nutritionProvenance;
 if(provenance){const basis=provenance.nutrientProfile?.basis;return basis?.amount===100&&basis.unit===unit;}
 return product.nutrition_data_per===(unit==='g'?'100g':'100ml');
}
export function weekDates(date){const base=new Date(date+'T12:00:00Z');const day=(base.getUTCDay()+6)%7;base.setUTCDate(base.getUTCDate()-day);return Array.from({length:7},(_,i)=>{const d=new Date(base);d.setUTCDate(d.getUTCDate()+i);return d.toISOString().slice(0,10);});}
export function planSummary(plan,recipes,inventory,products,dates){
 const selected=plan.filter(p=>dates.includes(p.date)).sort((a,b)=>a.date.localeCompare(b.date));
 // Match cooking's expiry/id order and carry deductions across planned meals.
 const remaining=inventory.map(l=>({...l})).sort((a,b)=>(a.expires||'9999').localeCompare(b.expires||'9999')||String(a.id||'').localeCompare(String(b.id||'')));
 const gaps=new Map(),requirements=new Map();
 const totals=Object.fromEntries(NUTRIENTS.map(([k])=>[k,{value:0,known:0,total:0}]));
 const unknown=()=>{for(const [key]of NUTRIENTS)totals[key].total++;};
 let portions=0,unresolved=0;
 for(const meal of selected){
  const recipe=recipes.find(r=>r.id===meal.recipeId);
  if(!recipe){unresolved++;continue;}
  portions+=meal.servings;
  for(const ingredient of recipe.ingredients){
   if(ingredient.optional)continue;
   const demandKnown=!recipe.needsReview&&!recipe.servingsUnknown&&Number.isFinite(recipe.servings)&&recipe.servings>0&&Number.isFinite(meal.servings)&&meal.servings>0;
   const scale=demandKnown?meal.servings/recipe.servings:null;
   const valid=demandKnown&&measuredIngredient(ingredient);
   if(!valid){unknown();unresolved++;continue;}
   const amount=ingredient.quantity*scale,key=normalize(ingredient.ingredient)+'|'+ingredient.unit;
   const need=requirements.get(key)||{ingredient:ingredient.ingredient,unit:ingredient.unit,quantity:0};
   need.quantity+=amount;requirements.set(key,need);
   // Already-cooked plans do not draw raw stock or infer its nutrient profile.
   if(meal.cookBatchId){unknown();continue;}
   let unallocated=amount;
   for(const stock of remaining){
    if(!eligibleStock(stock,meal.date)||normalize(stock.ingredient)!==normalize(ingredient.ingredient)||stock.unit!==ingredient.unit)continue;
    const take=Math.min(stock.quantity,unallocated);
    if(take>0){
     const product=products[stock.barcode];
     const compatible=nutrientBasisCompatible(product,stock.unit);
     for(const [nutrient]of NUTRIENTS){
      const total=totals[nutrient],value=nutrientValue(product?.nutriments,nutrient);
      total.total++;
      if(compatible&&Number.isFinite(value)){total.value+=value*take/100;total.known++;}
     }
     stock.quantity-=take;unallocated-=take;
    }
    if(unallocated<1e-7)break;
   }
   if(unallocated>1e-7){
    const gap=gaps.get(key)||{...need,quantity:0};
    gap.quantity+=unallocated;gaps.set(key,gap);
    // Uncovered demand is an unknown contribution, never a known zero.
    unknown();
   }
  }
 }
 const missing=[...gaps.values()].map(x=>({...x,quantity:Math.round(x.quantity*1000)/1000}));
 return {meals:selected.length,portions,unresolved,totals,requirements:[...requirements.values()],missing};
}
