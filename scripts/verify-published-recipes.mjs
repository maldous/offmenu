import {createReadStream,readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {createGunzip} from 'node:zlib';
import {StringDecoder} from 'node:string_decoder';
import {assertCurated} from '../corpus/assert-curated.mjs';
import {matchRecipeStock,personallyReviewedRecipe,recipeJSONLD} from '../public/recipe-library-model.js';
const [manifestPath,file,evidencePath]=process.argv.slice(2);if(!manifestPath||!file||!evidencePath)throw Error('Usage: node scripts/verify-published-recipes.mjs manifest.json recipes.jsonl.gz evidence.json');
const manifest=JSON.parse(readFileSync(manifestPath));
const descriptor=manifest.library.downloads.find(x=>x.key==='recipes.jsonl.gz');
const bytes=readFileSync(file);
if(bytes.length!==descriptor.bytes||createHash('sha256').update(bytes).digest('hex')!==descriptor.sha256)throw Error('Published download checksum mismatch');
const ids=new Set();let complete=0,partial=0,unknownYield=0,unknownQuantities=0;
function verify(line){
 if(!line)return;const r=JSON.parse(line);assertCurated(r);
 if(ids.has(r.id))throw Error('Duplicate published recipe ID');ids.add(r.id);
 if(r.kind!=='recipe'||!r.data.name||!r.data.ingredients.length||!r.data.directions.length||!r.provenance.license||!r.provenance.attribution||r.data.automaticPlanningEligible)throw Error('Invalid or automatically qualified recipe');
 const d=r.data;const jsonld=recipeJSONLD(r);
 if(jsonld['@type']!=='Recipe'||jsonld.recipeInstructions.length!==d.directions.length||jsonld.recipeIngredient.length!==d.ingredients.length)throw Error('Portable recipe mismatch');
 const stock=d.ingredients.map((i,n)=>({id:String(n),ingredient:i.ingredientId||i.name,quantity:Math.max(1,i.amount||0)*100000,unit:i.unit||'g'}));
 const match=matchRecipeStock(d,stock);
 if(d.ingredientExtractionComplete===false){partial++;if(match.coverage!==0||match.quantitiesAvailable!==false||!match.incomplete)throw Error('Incomplete OCR admitted for planning');let refused=false;try{personallyReviewedRecipe(r,{servings:1,confirmed:true,ingredients:d.ingredients.map(i=>({name:i.name,amount:1,unit:'g',optional:!!i.optional}))});}catch{refused=true;}if(!refused)throw Error('Incomplete OCR became a kitchen recipe');}
 else complete++;
 if(!d.yield?.value)unknownYield++;
 if(match.unknown.length)unknownQuantities++;
}
const decoder=new StringDecoder('utf8');let buffer='';
for await(const chunk of createReadStream(file).pipe(createGunzip())){buffer+=decoder.write(chunk);let cut;while((cut=buffer.indexOf('\n'))>=0){verify(buffer.slice(0,cut));buffer=buffer.slice(cut+1);}}
buffer+=decoder.end();if(buffer.trim())verify(buffer);
if(ids.size!==manifest.records||complete!==manifest.library.fullRecipes||partial!==manifest.library.historicalOcrCandidates)throw Error('Published count reconciliation failed');
const evidence={schema:'offmenu-live-recipe-acceptance/1',checkedAt:new Date().toISOString(),releaseId:manifest.releaseId,manifestSha256:manifest.manifestSha256,downloadSha256:descriptor.sha256,records:ids.size,fullSourceRecipes:complete,incompleteHistoricalOcrCandidates:partial,unknownYield,recordsWithUnknownQuantities:unknownQuantities,portableExports:'all source ingredient/direction counts preserved',ocrGate:'all incomplete OCR withheld from stock matching and personally reviewed recipe conversion',status:'published-download-and-consumer-gates-verified',independentCulinaryOrDietaryAcceptance:false,limitation:'Complete source text does not establish complete measurements, reviewed culinary identities or dietary suitability.'};
writeFileSync(evidencePath,JSON.stringify(evidence,null,2)+'\n');console.log(JSON.stringify(evidence));
