// Independent structural and consumer-model exercise over EVERY normalized row.
import {createReadStream} from 'node:fs';
import {readFile,writeFile} from 'node:fs/promises';
import {createGunzip} from 'node:zlib';
import {gzipLines} from './gzip-jsonl.mjs';
import {validateRecords,asOffNutriments} from '../apps/web/src/unified-data.js';
import {planSummary,NUTRIENTS} from '../apps/web/src/menu-model.js';
import {recipeForReview} from '../apps/web/src/recipe-review.js';
import {quantified} from '../apps/web/src/ingredients.js';
const [directory,output]=process.argv.slice(2);
if(!directory||!output)throw Error('Usage: node scripts/exercise-collection.mjs release-directory evidence.json');
const manifest=JSON.parse(await readFile(directory+'/manifest.json','utf8'));
if(manifest.status!=='normalized')throw Error('Reconciled normalized release required');
const files=manifest.partitions?.map(p=>p.key)||['normalized.jsonl.gz'];
const result={source:manifest.sourceId,release:manifest.releaseId||directory.split('/').pop(),records:0,
 profiles:0,planningExercises:0,reviewableRecipes:0,recipesWithoutIngredients:0,unreviewedDietAssertions:0,prices:0,
 missingPriceAmount:0,missingCurrency:0,missingPriceDate:0,negativePriceAmount:0,retailerReferences:0,siteReferences:0,
 knownMetrics:Object.fromEntries(NUTRIENTS.map(([k])=>[k,0])),errors:[],status:'running',
 limitation:'Synthetic per-100-unit model checks verify data paths, not food identity, dietary suitability or independent nutrition accuracy'};
const recipe={id:'exercise',title:'Synthetic source-basis exercise',servings:1,ingredients:[{ingredient:'source-food',quantity:100,unit:'g'}]};
for(const file of files){
 for await(const line of gzipLines(directory+'/'+file)){
  const rows=validateRecords(JSON.parse(line));result.records+=rows.length;
  for(const r of rows){
   if(r.kind==='nutrientProfile'){
    result.profiles++;
    const unit=r.data.basis?.unit;
    if(!['g','ml'].includes(unit)||r.data.basis.amount!==100)continue;
    const nutriments=asOffNutriments(r,unit),id='source-food';recipe.ingredients[0].unit=unit;
    const products={[id]:{product_quantity:100,product_quantity_unit:unit,nutriments}},inventory=[{id,barcode:id,ingredient:id,quantity:100,unit}];
    const summary=planSummary([{recipeId:'exercise',date:'2026-10-13',servings:1}],[recipe],inventory,products,['2026-10-13']);
    for(const [key] of NUTRIENTS){const n=summary.totals[key];if(n.known===1){if(!Number.isFinite(n.value)||n.value<0)throw Error('Invalid consumer quantity '+r.id);result.knownMetrics[key]++;}}
    if(summary.missing.length||summary.unresolved)throw Error('Source-basis model exercise failed '+r.id);
    result.planningExercises++;
   }else if(r.kind==='recipe'){
    if(!r.data.ingredients?.length){result.recipesWithoutIngredients++;continue;}
    const review=recipeForReview(r);if(quantified(review))throw Error('Unreviewed source recipe became automatic');result.reviewableRecipes++;
   }else if(r.kind==='sourceAssertion'&&r.provenance.sourceId==='fineli'){
    if(r.data.qualificationStatus!=='unknown'||r.data.automaticDietQualification!==false)throw Error('Source diet tag became a verified qualification');result.unreviewedDietAssertions++;
   }else if(['retailer','site'].includes(r.kind)&&r.provenance.sourceId==='overture-food-places'){
    if(r.data.inventoryAvailability!=='unknown'||r.data.ownershipVerified!==false||r.data.dietQualification!=='unknown')throw Error('Place reference invented inventory, ownership or diet qualification');
    if(r.kind==='retailer')result.retailerReferences++;else result.siteReferences++;
   }else if(r.kind==='priceObservation'){
    result.prices++;const d=r.data;
    if(d.amount==null)result.missingPriceAmount++;else if(!Number.isFinite(d.amount))throw Error('Non-finite price '+r.id);else if(d.amount<0)result.negativePriceAmount++;
    if(!d.currency)result.missingCurrency++;if(!d.observedAt)result.missingPriceDate++;
    if(d.availability!=='unknown')throw Error('Observation invented stock availability');
   }
  }
  if(result.records%100000===0)console.log(JSON.stringify({records:result.records,profiles:result.profiles}));
 }
}
const expected=manifest.normalizedRows??manifest.counts.records;
if(result.records!==expected)throw Error('Exercise count disagrees with reconciliation');
result.status='all normalized records structurally exercised';result.completedAt=new Date().toISOString();
await writeFile(output,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
