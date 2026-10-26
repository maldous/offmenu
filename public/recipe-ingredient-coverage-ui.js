import {recipeIngredientCoverage} from './recipe-ingredient-coverage.js';
import {t,setLocalizedText} from './i18n.js';

// Display the accepted allocator's quantities verbatim; never round a gap to zero
// or convert the source unit/location into another basis.
function amount(quantity,unit){
 if(!Number.isFinite(quantity)||quantity<0)return unit?t('Unknown quantity ({unit})',{unit}):t('Unknown quantity and unit');
 return unit?String(quantity)+' '+unit:t('{quantity} · unit unknown',{quantity:String(quantity)});
}
export function appendRecipeIngredientCoverage(card,{recipe,inventory,products,servings,date}={}){
 const document=card.ownerDocument,details=document.createElement('details'),summary=document.createElement('summary');
 details.className='menu-ingredient-coverage';setLocalizedText(summary,'Ingredient coverage');details.append(summary);
 const state=document.createElement('p');state.className='menu-location-note';details.append(state);
 let coverage;
 try{coverage=recipeIngredientCoverage({recipe,inventory,products,servings,date});}
 catch{setLocalizedText(state,'Ingredient coverage is unavailable. Keep the existing meal review.');card.append(details);return {element:details,coverage:null};}
 // These are existing card decisions, not a new dietary/allergy classifier.
 const existingReviewClear=recipe.group?.compatible===true&&recipe.group?.automaticSelection===true;
 if(existingReviewClear&&recipe.status==='ready'&&coverage.choices.readyNow){setLocalizedText(state,'Ready now');state.dataset.coverageChoice='ready';}
 else if(existingReviewClear&&recipe.status==='missing'&&coverage.choices.oneExtraItem){setLocalizedText(state,'One item to add');state.dataset.coverageChoice='one-extra';}
 else if(coverage.choices.unknown||recipe.status==='needs_review'){setLocalizedText(state,'Coverage needs review.');state.dataset.coverageChoice='unknown';}
 else if(!existingReviewClear){setLocalizedText(state,'Check the existing dietary review before choosing this meal.');state.dataset.coverageChoice='review';}
 else{setLocalizedText(state,'Additional ingredients are needed.');state.dataset.coverageChoice='additional';}
 const list=document.createElement('ul');list.className='menu-ingredients';details.append(list);
 for(const requirement of coverage.requirements){
  const line=document.createElement('li');line.dataset.requirementIndex=String(requirement.index);
  const name=document.createElement('strong');setLocalizedText(name,requirement.ingredient);line.append(name);
  const quantities=document.createElement('p');setLocalizedText(quantities,'Covered {covered} / required {required}',{
   covered:amount(requirement.coveredQuantity,requirement.unit),required:amount(requirement.requiredQuantity,requirement.unit)});line.append(quantities);
  const shortfall=document.createElement('p');
  if(requirement.status==='unknown'||requirement.uncoveredQuantity===null)setLocalizedText(shortfall,'Uncovered quantity is unknown.');
  else if(Number.isFinite(requirement.uncoveredQuantity)&&requirement.uncoveredQuantity>0)setLocalizedText(shortfall,'Still needed: {amount}',{amount:amount(requirement.uncoveredQuantity,requirement.unit)});
  else if(!coverage.classificationAgreement)setLocalizedText(shortfall,'Availability needs review; no positive shortfall is confirmed.');
  else setLocalizedText(shortfall,'No positive shortfall reported by the allocation.');
  line.append(shortfall);
  if(requirement.allocations.length){
   const lots=document.createElement('ul');lots.className='menu-ingredients';
   for(const allocation of requirement.allocations){
    const lot=document.createElement('li');lot.dataset.lotId=allocation.lotId;
    if(allocation.location)setLocalizedText(lot,'{amount} · {area} / {shelf}',{amount:amount(allocation.quantity,allocation.unit),area:allocation.location.area,shelf:allocation.location.shelf});
    else setLocalizedText(lot,'{amount} · Location unknown',{amount:amount(allocation.quantity,allocation.unit)});
    const basis=document.createElement('small');
    if(allocation.nutritionBasisEligible===true)setLocalizedText(basis,'Nutrition basis compatible; nutrient values may still be missing.');
    else setLocalizedText(basis,'Nutrition basis unsupported or unknown.');
    lot.append(document.createTextNode(' · '),basis);lots.append(lot);
   }
   line.append(lots);
  }else{const basis=document.createElement('small');setLocalizedText(basis,'Nutrition basis unknown without an allocated lot.');line.append(basis);}
  list.append(line);
 }
 const basisNote=document.createElement('p');basisNote.className='recipe-food-data';setLocalizedText(basisNote,'Nutrition basis is shown per allocated lot. Nutrient completeness is not established.');details.append(basisNote);
 card.append(details);return {element:details,coverage};
}
