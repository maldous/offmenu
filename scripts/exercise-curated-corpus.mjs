import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {join} from 'node:path';
import {assertCurated,createEngine} from '../corpus/engine.mjs';
import {asOffNutriments} from '../public/unified-data.js';
import {planSummary} from '../public/menu-model.js';
const [release,evidence]=process.argv.slice(2);if(!release||!evidence)throw Error('Usage: node scripts/exercise-curated-corpus.mjs release-directory evidence.json');
const root=join(release,'blobs'),engine=await createEngine(key=>readFile(join(root,key))),manifest=engine.manifest;
const result={status:'running',releaseId:manifest.releaseId,records:0,profiles:0,planningExercises:0,recipeReferences:0,prices:0,rawSourcePayloadPublished:false,independentlyAccepted:false,limitation:'All-record structural and synthetic consumer checks do not establish independently reviewed food matches or dietary qualification.'};
for(const file of manifest.files){const bytes=await readFile(join(root,file.key));if(bytes.length!==file.bytes||createHash('sha256').update(bytes).digest('hex')!==file.sha256)throw Error('Release checksum failed');
 if(!file.key.startsWith('records/'))continue;
 for(const line of gunzipSync(bytes,{maxOutputLength:80*1024*1024}).toString('utf8').split('\n')){if(!line)continue;const [key,rows]=JSON.parse(line),ids=new Set(rows.map(r=>r.id));
  for(const row of rows){assertCurated(row);result.records++;const d=row.data;
   if(row.kind==='product'&&d.nutritionId&&!ids.has(d.nutritionId))throw Error('Dangling curated composition join');
   if(row.kind==='nutrientProfile'){result.profiles++;const unit=d.basis.unit,recipe={id:key,title:'Curation basis exercise',servings:1,ingredients:[{ingredient:key,quantity:100,unit}]};
    const nutrients=asOffNutriments(row,unit),products={[key]:{product_quantity:100,product_quantity_unit:unit,nutriments:nutrients}},inventory=[{id:key,barcode:key,ingredient:key,quantity:100,unit}];
    const summary=planSummary([{recipeId:key,date:'2026-10-13',servings:1}],[recipe],inventory,products,['2026-10-13']);if(summary.missing.length||summary.unresolved)throw Error('Curated consumer exercise failed');result.planningExercises++;
   }else if(row.kind==='recipe'){if(d.automaticPlanningEligible||d.ingredients.length||d.directions.length)throw Error('Source recipe body entered discovery projection');result.recipeReferences++;}
   else if(row.kind==='priceObservation')result.prices++;
  }
 }
 if(result.records%100000<1000)console.log(JSON.stringify({records:result.records}));
}
if(result.records!==manifest.records)throw Error('Curated record reconciliation failed');
result.status='all-curated-records-exercised';result.completedAt=new Date().toISOString();await writeFile(evidence,JSON.stringify(result,null,2)+'\n');
manifest.curatedAcceptance=result;delete manifest.manifestSha256;manifest.manifestSha256=createHash('sha256').update(JSON.stringify(manifest)).digest('hex');await writeFile(join(root,'manifest.json'),JSON.stringify(manifest)+'\n');console.log(JSON.stringify(result));
