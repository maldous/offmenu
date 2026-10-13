import {validateRecipes} from './model.js';
import {recordPermission} from './record-policy.js';

export function recipeForReview(record){
 if(record.kind!=='recipe')throw Error('Select a recipe record');
 if(!recordPermission(record,{action:'derive'}).allowed)throw Error('Source rights do not permit recipe reuse');
 const d=record.data,yieldValue=d.yield?.value;
 return validateRecipes([{id:record.id,title:d.name,source:record.provenance.url,
  license:record.provenance.license,attribution:record.provenance.attribution,
  provenance:record.provenance,servings:yieldValue>0?yieldValue:1,
  servingsUnknown:!(yieldValue>0),needsReview:true,
  ingredients:(d.ingredients||[]).map(i=>({ingredient:i.ingredientId||i.name,quantity:i.amount??null,unit:i.unit||null,
   raw:i.originalText||i.name,optional:!!i.optional,foodMatchStatus:i.foodMatchStatus||'unreviewed'})),
  instructions:d.directions||[],time:d.time||null,originalTextLines:d.originalTextLines||[]}])[0];
}
