import {validateBatches} from '../public/cooking-model.js';
import {validateRecords} from '../public/unified-data.js';
import {validateInsights} from '../public/insights-model.js';
import {validateLot, validateRecipes} from '../public/model.js';
export function validateState(value) {
  if (!value || !Array.isArray(value.inventory) || value.inventory.length > 10000) throw Error('Invalid inventory.');
  const inventory=value.inventory.map(validateLot);
  if(new Set(inventory.map(x=>x.id)).size!==inventory.length)throw Error('Duplicate inventory IDs.');
  const profile=value.profile||{};
  if(profile.country && !/^[A-Z]{2}$/.test(profile.country))throw Error('Invalid country.');
  if(!['metric','imperial'].includes(profile.units||'metric'))throw Error('Invalid units.');
  if(!Number.isFinite(Number(profile.servings))||Number(profile.servings)<=0)throw Error('Invalid servings.');
  const selections=value.selections||[];
  if(!Array.isArray(selections)||selections.length>10000||selections.some(x=>typeof x!=='string'||x.length>200))throw Error('Invalid selections.');
  const products=value.products||{};
  if(typeof products!=='object'||Array.isArray(products)||Object.keys(products).length>10000)throw Error('Invalid barcode list.');
  for(const [code,p]of Object.entries(products))if(!(/^[0-9]{4,32}$/.test(code)||/^local:[a-zA-Z0-9-]{1,100}$/.test(code))||!p||typeof p.name!=='string'||p.name.length>1000)throw Error('Invalid product.');
  if(profile.dataLanguage&&!['ui','en','native','fr','de','zh','hi','id','ru','ar','ja'].includes(profile.dataLanguage))throw Error('Invalid data display language.');
  const settings={...(profile.dataLanguage?{dataLanguage:profile.dataLanguage}:{}),country:profile.country||'',units:profile.units||'metric',servings:Number(profile.servings)};
  if(profile.locations){if(!Array.isArray(profile.locations)||profile.locations.length>1000)throw Error('Invalid locations.');settings.locations=profile.locations.map(l=>{if(typeof l.id!=='string'||typeof l.area!=='string'||!l.area.trim()||l.area.length>60||typeof l.shelf!=='string'||!l.shelf.trim()||l.shelf.length>60)throw Error('Invalid location.');return {id:l.id,area:l.area.trim(),shelf:l.shelf.trim()};});}
  if(profile.batches)settings.batches=validateBatches(profile.batches);
  if(profile.accessibility){settings.accessibility={large:!!profile.accessibility.large,quiet:!!profile.accessibility.quiet};}
  if(profile.members){if(!Array.isArray(profile.members)||profile.members.length>100)throw Error('Invalid household.');settings.members=profile.members.map(m=>{if(typeof m.id!=='string'||typeof m.name!=='string'||!m.name.trim()||m.name.length>100||!Number.isFinite(m.portion)||m.portion<=0||!Array.isArray(m.avoid)||m.avoid.some(x=>typeof x!=='string'||x.length>100)||!Array.isArray(m.advisors)||m.advisors.some(x=>!['balanced','high-protein','low-carb','weight-loss','gluten-free','dairy-free','vegetarian','vegan'].includes(x)))throw Error('Invalid household member.');for(const key of ['age','height','weight'])if(m[key]!=null&&(!Number.isFinite(m[key])||m[key]<0))throw Error('Invalid member metric.');return {id:m.id,name:m.name.trim(),portion:m.portion,age:m.age??null,height:m.height??null,weight:m.weight??null,avoid:m.avoid,advisors:m.advisors,...(m.restrictions?{restrictions:m.restrictions.map(r=>{if(!['allergy','intolerance','religious','preference'].includes(r.type)||typeof r.term!=='string'||r.term.length>100)throw Error('Invalid restriction.');return {type:r.type,term:r.term};})}:{})};});}
  if(profile.plan){if(!Array.isArray(profile.plan)||profile.plan.length>10000)throw Error('Invalid meal plan.');settings.plan=profile.plan.map(p=>{if(typeof p.id!=='string'||typeof p.recipeId!=='string'||p.recipeId.length>200||!/^\d{4}-\d{2}-\d{2}$/.test(p.date)||!Number.isFinite(Date.parse(p.date))||!['Breakfast','Lunch','Dinner','Snack'].includes(p.slot)||!Number.isFinite(p.servings)||p.servings<=0)throw Error('Invalid planned meal.');return {id:p.id,recipeId:p.recipeId,date:p.date,slot:p.slot,servings:p.servings,...(typeof p.cookBatchId==='string'?{cookBatchId:p.cookBatchId.slice(0,100)}:{}),...(Array.isArray(p.memberIds)?{memberIds:p.memberIds.filter(x=>typeof x==='string').slice(0,100)}:{}),...(Array.isArray(p.adjustments)?{adjustments:p.adjustments.filter(x=>typeof x==='string').slice(0,100)}:{})};});}
  if(profile.feedback){settings.feedback={};for(const key of ['sound','vibration','screen','light','speech']){if(typeof profile.feedback[key]!=='boolean')throw Error('Invalid feedback setting.');settings.feedback[key]=profile.feedback[key];}}
  if(profile.lastReceipt){const r=profile.lastReceipt;if(!['shelf','shopping','waste'].includes(r.mode)||typeof r.area!=='string'||!r.area.trim()||r.area.length>60||typeof r.shelf!=='string'||!r.shelf.trim()||r.shelf.length>60||!Array.isArray(r.items)||r.items.length>10000||typeof r.startedAt!=='string'||typeof r.finishedAt!=='string')throw Error('Invalid saved receipt.');settings.lastReceipt={mode:r.mode,area:r.area,shelf:r.shelf,startedAt:r.startedAt.slice(0,40),finishedAt:r.finishedAt.slice(0,40),items:r.items.map(validateLot)};}
  if(profile.waste){if(!Array.isArray(profile.waste)||profile.waste.length>1000)throw Error('Invalid cleanup history.');settings.waste=profile.waste.map(r=>{if(r.mode!=='waste'||typeof r.area!=='string'||r.area.length>60||typeof r.shelf!=='string'||r.shelf.length>60||typeof r.startedAt!=='string'||typeof r.finishedAt!=='string'||!Array.isArray(r.items)||r.items.length>10000)throw Error('Invalid waste receipt.');return {mode:'waste',area:r.area,shelf:r.shelf,startedAt:r.startedAt.slice(0,40),finishedAt:r.finishedAt.slice(0,40),items:r.items.map(validateLot)};});}
  if(profile.dataRecords){if(profile.dataRecords.length>500)throw Error('Too many local data records. Use the dedicated cloud record store.');settings.dataRecords=validateRecords(profile.dataRecords,{privateOnly:true});}
  Object.assign(settings,validateInsights(profile));
  return {inventory,products,recipes:validateRecipes(value.recipes||[]),profile:settings,selections};
}
