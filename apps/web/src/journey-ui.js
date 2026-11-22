import {showLocalized,localizedField} from './content-locale.js';
import {t,renderedLanguage,setLocalizedText,getLanguage} from './i18n.js';
import {groupSuitability} from './household-model.js';
import {INGREDIENTS,ingredientIdentity,canonicalAmount,canonicalIngredient,displayAmount} from './ingredients.js';
import {cookMeal,serveBatch,undoCook} from './cooking-model.js';
import {validateLot} from './model.js';
const $=id=>document.getElementById(id),el=(tag,text)=>{const e=document.createElement(tag);e.textContent=text;if(renderedLanguage(text))e.lang=renderedLanguage(text);e.dir='auto';return e;};
export function setupJourney({getData,commit,today,view}){let selectedRecipe=null,selectedPlan=null,selectedBatch=null,completedBatchId='',wake=null,timer=null,cookSubmitting=false;
for(const i of INGREDIENTS){const o=el('option',i.id);o.value=i.id;$('produce-options').append(o);}
let findAfterSaving = false;
let ingredientEdited = false;
$('food-name').oninput = () => {
  const suggestedIngredient = ingredientIdentity($('food-name').value)?.id || '';
  if (!ingredientEdited) $('food-ingredient').value = suggestedIngredient;
};
$('food-ingredient').oninput = () => { ingredientEdited = true; };
function showFoodRecipes(term) {
  $('menu-search').value = term;
  $('menu-ready').value = '';
  $('menu-location').value = '';
  view('meals');
  const notice = $('menu-notice');
  notice.tabIndex = -1;
  return notice;
}
$('food-browse').onclick = () => {
  const nameInput = $('food-name');
  nameInput.value = nameInput.value.trim();
  if (!nameInput.reportValidity()) return;
  const term = $('food-ingredient').value.trim() || $('food-name').value.trim();
  $('food-dialog').close();
  const notice = showFoodRecipes(term);
  setLocalizedText(notice, 'Finding recipes for {food}. Your stock has not changed.', {food:term});
  notice.focus();
};
function openFood(forMeals = false) {
  findAfterSaving = forMeals;
  ingredientEdited = false;
  $('food-form').reset();
  $('food-form').querySelector('details').open = false;
  setLocalizedText($('food-save'), forMeals ? 'Save and find meals' : 'Add to my kitchen');
  $('food-location').replaceChildren();const data=getData(),known=[...(data.profile.locations||[]),...data.inventory.map(l=>l.location).filter(Boolean)];if(!known.length)known.push({area:'Pantry',shelf:'Shelf 1'});const seen=new Set;for(const l of known){if(!l?.area||!l?.shelf)continue;const key=JSON.stringify([l.area,l.shelf]);if(seen.has(key))continue;seen.add(key);const o=el('option',l.area+' / '+l.shelf);o.value=JSON.stringify({area:l.area,shelf:l.shelf});$('food-location').append(o);}setLocalizedText($('food-notice'),'');$('food-dialog').showModal();}
$('quick-add').onclick = () => openFood();
$('food-form').onsubmit = event => {
  event.preventDefault();
  try {
    const d = getData();
    const name = $('food-name').value.trim();
    const amount = canonicalAmount(Number($('food-quantity').value), $('food-unit').value);
    const ingredient = canonicalIngredient($('food-ingredient').value) || 'unmapped';
    const id = crypto.randomUUID();
    const lot = validateLot({id, barcode:'local:'+id, name, ingredient, ...amount,
      expires:$('food-date').value || null, dateType:$('food-date-type').value,
      location:JSON.parse($('food-location').value), needsReview:ingredient === 'unmapped', amountBasis:'manual'});
    commit({inventory:[...d.inventory, lot]});
    $('food-dialog').close();
    if (findAfterSaving) {
      const notice = showFoodRecipes(ingredient === 'unmapped' ? name : ingredient);
      setLocalizedText(notice, ingredient === 'unmapped'
        ? 'Saved {food}. Confirm its ingredient in Kitchen before counting it toward a recipe.'
        : 'Saved {food} in {place}. Showing meals with {ingredient}.',
        {food:name, place:lot.location.area+' / '+lot.location.shelf, ingredient});
      notice.focus();
    } else {
      view('shelves');
    }
  } catch (error) {
    setLocalizedText($('food-notice'), error.message);
  }
};
function renderCookIngredients(){
 const target=$('cook-ingredients');target.replaceChildren();
 const portions=Number($('cook-servings').value),base=selectedRecipe?.servings;
 if(!Number.isFinite(portions)||portions<=0||!Number.isFinite(base)||base<=0){target.append(el('li',t('Enter a valid number of portions.')));return;}
 for(const item of selectedRecipe.ingredients){
  const amount=Number.isFinite(item.quantity)?displayAmount(item.quantity*portions/base,item.unit,getData().profile.units):t('Quantity not specified');
  target.append(el('li',amount+' '+item.ingredient+(item.optional?' ('+t('Optional')+', '+t('not allocated')+')':'')));
 }
}
$('cook-servings').oninput=renderCookIngredients;
$('cook-servings').onchange=renderCookIngredients;
function resetCookResult() {
  cookSubmitting = false;
  completedBatchId = '';
  $('cook-workflow').hidden = false;
  $('cook-result').hidden = true;
  $('cook-result-notice').textContent = '';
}
function showCookResult(batch, inventory, duplicate = false) {
  const stock = inventory.find(lot => lot.cookBatchId === batch.id);
  const place = stock?.location && [stock.location.area, stock.location.shelf].filter(Boolean).join(' / ');
  const portions = Number(batch.remaining.toFixed(2));
  $('cook-workflow').hidden = true;
  $('cook-result').hidden = false;
  setLocalizedText($('cook-result-title'), duplicate ? 'Cooking already recorded' : 'Cooking recorded');
  if (!portions) {
    setLocalizedText($('cook-result-summary'), 'No portions remain in this batch.');
  } else if (!place) {
    setLocalizedText($('cook-result-summary'), 'Portions remaining: {count}. Storage location unknown.', {count:portions});
  } else {
    setLocalizedText($('cook-result-summary'), portions === 1
      ? 'One cooked portion is stored in {place}.'
      : '{v0} cooked portions are stored in {v1}.', {place, v0:portions, v1:place});
  }
  setLocalizedText($('cook-result-notice'), duplicate ? 'No ingredients were deducted again.' : 'Raw ingredients were deducted once.');
  $('cook-result-actions').hidden = false;
  $('cook-result-done').hidden = true;
  $('cook-result-serve').disabled = batch.remaining <= 0;
  $('cook-result-undo').disabled = batch.events.length > 0;
  $('cook-result-undo-note').hidden = batch.events.length === 0;
  $('cook-result').focus();
}
function undoBatch(batch,notice){const d=getData(),current=d.profile.batches.find(b=>b.id===batch.id);if(!current)throw Error(t('Cooked batch is no longer available.'));const inventory=undoCook(current,d.inventory);current.undone=true;for(const plan of d.profile.plan||[])if(plan.cookBatchId===current.id)delete plan.cookBatchId;commit({inventory});renderBatches();if(notice)setLocalizedText(notice,'Cooking undone. Raw ingredients are available again.');return current;}
function openCook(recipe,plan=null){selectedRecipe=recipe;selectedPlan=plan;resetCookResult();showLocalized($('cook-title'),localizedField(recipe,"title"));$('cook-servings').value=plan?.servings||getData().profile.servings||2;$('cook-date').value=plan?.date||today();$('cook-ingredients').replaceChildren();$('cook-steps').replaceChildren();renderCookIngredients();for(const step of recipe.instructions)$('cook-steps').append(el('li',step));setLocalizedText($('cook-notice'),'Confirm the ingredient amounts and cooking date. This consumes raw stock once and creates a cooked batch. Optional ingredients are omitted; edit the recipe to include substitutions.');const members=getData().profile.members||[],fit=groupSuitability(recipe,plan?.memberIds?.length?members.filter(m=>plan.memberIds.includes(m.id)):members);$('cook-checks').hidden=!fit.checks.length;$('cook-reviewed').checked=false;$('cook-confirm').disabled=!fit.compatible||fit.checks.length>0;if(fit.checks.length)$('cook-notice').textContent+=t(' '+[...new Set(fit.checks)].join('; '));$('cook-dialog').showModal();}
$('cook-reviewed').onchange=()=>{$('cook-confirm').disabled=$('cook-checks').hidden?false:!$('cook-reviewed').checked;};
$('cook-confirm').onclick=()=>{if(cookSubmitting)return;cookSubmitting=true;$('cook-confirm').disabled=true;try{const d=getData();if(!$('cook-checks').hidden&&!$('cook-reviewed').checked)throw Error(t('Review the selected household restrictions and actual packages before cooking'));const result=cookMeal({recipe:selectedRecipe,inventory:d.inventory,products:d.products,servings:Number($('cook-servings').value),date:$('cook-date').value,planId:selectedPlan?.id||'',batches:d.profile.batches||[]});if(!result.duplicate){d.profile.batches=[...(d.profile.batches||[]),result.batch];if(selectedPlan)selectedPlan.cookBatchId=result.batch.id;commit({inventory:result.inventory});}completedBatchId=result.batch.id;showCookResult(result.batch,result.inventory,result.duplicate);renderBatches();}catch(e){cookSubmitting=false;$('cook-confirm').disabled=false;setLocalizedText($('cook-notice'),e.message);}};
$('cook-result-serve').onclick=()=>{const batch=getData().profile.batches.find(b=>b.id===completedBatchId&&!b.undone);if(!batch){setLocalizedText($('cook-result-notice'),'Cooked batch is no longer available.');return;}$('cook-dialog').close();openServe(batch);};
$('cook-result-view').onclick=()=>{const batch=getData().profile.batches.find(b=>b.id===completedBatchId&&!b.undone);if(!batch){setLocalizedText($('cook-result-notice'),'Cooked batch is no longer available.');return;}$('cook-dialog').close();view('shelves');queueMicrotask(()=>document.querySelector(`[data-batch-id="${CSS.escape(batch.id)}"]`)?.focus());};
$('cook-result-undo').onclick = () => {
  try {
    const batch = getData().profile.batches.find(item => item.id === completedBatchId && !item.undone);
    if (!batch) throw Error(t('Cooked batch is no longer available.'));
    undoBatch(batch, $('cook-result-notice'));
    setLocalizedText($('cook-result-title'), 'Cooking undone');
    $('cook-result-summary').textContent = '';
    $('cook-result-undo').disabled = true;
    $('cook-result-actions').hidden = true;
    $('cook-result-undo-note').hidden = true;
    $('cook-result-done').hidden = false;
    $('cook-result').focus();
  } catch (error) {
    setLocalizedText($('cook-result-notice'), error.message);
  }
};
$('cook-awake').onchange=async()=>{try{if($('cook-awake').checked){if(!navigator.wakeLock)throw Error(t('Keep-awake is unavailable in this browser.'));wake=await navigator.wakeLock.request('screen');}else{await wake?.release();wake=null;}}catch(e){setLocalizedText($('cook-notice'),e.message);$('cook-awake').checked=false;}};
$('cook-dialog').addEventListener('close',()=>{void wake?.release();wake=null;$('cook-awake').checked=false;});
$('timer-start').onclick=()=>{clearInterval(timer);const minutes=Number($('timer-minutes').value);if(!Number.isFinite(minutes)||minutes<=0||minutes>240)return;const end=Date.now()+minutes*60000;timer=setInterval(()=>{const sec=Math.max(0,Math.ceil((end-Date.now())/1000));setLocalizedText($('timer-status'),Math.floor(sec/60)+':'+String(sec%60).padStart(2,'0'));if(sec===0){clearInterval(timer);setLocalizedText($('timer-status'),'Timer finished. Check your food.');}},1000);};$('timer-stop').onclick=()=>{clearInterval(timer);setLocalizedText($('timer-status'),'Timer stopped');};
function servingPortions(raw, remaining){
 const normalized=raw.trim().replace(/[٠-٩۰-۹]/g,d=>String((d.codePointAt(0)-(d<='٩'?0x660:0x6f0)))).replace(/[٫,]/g,'.');
 const portions=/^(?:\d+(?:\.\d)?|\.\d)$/.test(normalized)?Number(normalized):NaN;
 if(!Number.isFinite(portions)||portions<0.1||portions>remaining+1e-7)throw Error(t('Choose portions within the cooked amount remaining.'));
 return portions;
}
function openServe(batch){selectedBatch=batch;showLocalized($('serve-title'),localizedField(batch,"title"));$('serve-portions').value=String(Math.min(1,Math.floor((batch.remaining+1e-7)*10)/10)||'');$('serve-completion').value='';$('serve-member').replaceChildren();const all=el('option',t('Unassigned household'));all.value='';$('serve-member').append(all);for(const m of getData().profile.members||[]){const o=el('option',m.name);o.value=m.id;$('serve-member').append(o);}$('serve-date').value=today();setLocalizedText($('serve-notice'),'Record one serving at a time. Unserved portions remain cooked stock. Completion is optional; blank means unknown.');$('serve-remainder').value='unspecified';$('serve-dialog').showModal();}
for(const b of document.querySelectorAll('[data-completion]'))b.onclick=()=>{$('serve-completion').value=b.dataset.completion;};
$('serve-form').onsubmit=e=>{e.preventDefault();try{const d=getData(),batch=d.profile.batches.find(b=>b.id===selectedBatch.id),r=serveBatch({batch,inventory:d.inventory,portions:servingPortions($('serve-portions').value,batch.remaining),completion:$('serve-completion').value===''?null:Number($('serve-completion').value),remainder:$('serve-remainder').value,memberId:$('serve-member').value,date:$('serve-date').value});d.profile.batches=d.profile.batches.map(b=>b.id===r.batch.id?r.batch:b);d.profile.history=[...(d.profile.history||[]),r.log];commit({inventory:r.inventory});$('serve-dialog').close();renderBatches();}catch(e){setLocalizedText($('serve-notice'),e.message);}};
function renderBatches(){const d=getData();$('cooked-batches').replaceChildren();for(const batch of [...(d.profile.batches||[])].reverse().filter(b=>!b.undone)){const box=document.createElement('article');box.dataset.batchId=batch.id;box.tabIndex=-1;box.append(el('h3',batch.title),el('p',t("{v0} · {v1} / {v2} cooked portions remain", {v0:(batch.date),v1:(Number(batch.remaining.toFixed(2))),v2:(batch.servings)})));const stock=d.inventory.find(l=>l.cookBatchId===batch.id);if(stock)box.append(el('p',t("Stored: {v0} / {v1}{v2}", {v0:(stock.location.area),v1:(stock.location.shelf),v2:(stock.expires?' · entered '+stock.dateType+' '+stock.expires:' · date not entered')})));if(batch.remaining>0){const serve=el('button',t('Serve / after meal'));serve.onclick=()=>openServe(batch);box.append(serve);}const undo=el('button',t('Undo cooking'));undo.className='outline';undo.disabled=batch.events.length>0;undo.onclick=()=>{try{undoBatch(batch,$('journey-notice'));}catch(e){setLocalizedText($('journey-notice'),e.message);}};box.append(undo);const storage=el('button',t('Edit cooked storage / date'));storage.className='outline';storage.onclick=()=>{const lot=d.inventory.find(l=>l.cookBatchId===batch.id);if(!lot)return;$('cooked-date').value=lot.expires||'';$('cooked-date-dialog').showModal();$('cooked-date-save').onclick=()=>{lot.expires=$('cooked-date').value||null;lot.dateType='use-by';commit({inventory:d.inventory});$('cooked-date-dialog').close();renderBatches();};};box.append(storage);$('cooked-batches').append(box);}if(!$('cooked-batches').children.length)$('cooked-batches').append(el('p',t('Cook a recipe to turn raw ingredients into a batch. Leftovers stay here as usable cooked portions.')));}
$('large-type').onchange=()=>{const d=getData();d.profile.accessibility={...d.profile.accessibility,large:$('large-type').checked};applyPreferences();commit({});};$('quiet-mode').onchange=()=>{const d=getData();d.profile.accessibility={...d.profile.accessibility,quiet:$('quiet-mode').checked};if($('quiet-mode').checked)d.profile.feedback={sound:false,vibration:false,screen:false,light:false,speech:false};applyPreferences();commit({});};
function applyPreferences(){const p=getData().profile.accessibility||{};document.documentElement.classList.toggle('large-type',!!p.large);$('large-type').checked=!!p.large;$('quiet-mode').checked=!!p.quiet;}
return {openFood,openCook,openServe,renderBatches,applyPreferences};}
