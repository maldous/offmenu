import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeOFF,normalizeUSDA,normalizePrices,normalizeCSV} from '../public/unified-data.js';
import {sourceById} from '../public/sources.js';
import {recipeForReview} from '../public/recipe-review.js';
import {quantified} from '../public/ingredients.js';
import {cookMeal} from '../public/cooking-model.js';
import {generateHouseholdDay,pantryDuration} from '../public/household-model.js';
import {corpusLookup} from '../cloud/corpus.mjs';

test('bulk price fields retain discount and unit semantics',()=>{
 const [r]=normalizePrices({items:[{id:1,price:'1.25',price_is_discounted:true,price_without_discount:'2.50',price_per:'KILOGRAM',proof_id:12,duplicate_of:null,location:{osm_address_country_code:'fr'}}]},sourceById('prices'));
 assert.equal(r.data.promotion,true);assert.equal(r.data.regularAmount,2.5);
 assert.equal(r.data.unit,'KILOGRAM');assert.equal(r.data.unitPrice,null);
 assert.equal(r.data.proofId,12);assert.deepEqual(r.countries,['FR']);
});
test('USDA retains unmapped observations and derivation; volume pack does not change nutrient basis',()=>{
 const rows=normalizeUSDA({fdcId:1,foodNutrients:[{nutrient:{id:999,name:'New analyte',unitName:'MG'},amount:0,foodNutrientDerivation:{description:'analytical'},dataPoints:3}]},sourceById('usda-files'));
 assert.equal(rows[1].data.nutrients['usda:999'].value,0);
 assert.equal(rows[1].data.nutrients['usda:999'].sourceName,'New analyte');
 assert.equal(rows[1].data.nutrients['usda:999'].method,'analytical');
 assert.equal(normalizeOFF({code:'00012345',product_quantity_unit:'ml',nutrition_data_per:'100g'},sourceById('off'))[1].data.basis.unit,'g');
});
test('CSV processing does not silently truncate at 1000 source rows',()=>{
 const csv='name,id\n'+Array.from({length:1001},(_,i)=>'Food '+i+','+i).join('\n');
 assert.equal(normalizeCSV(csv,sourceById('personal-import'),{name:'name',id:'id'}).length,1001);
});
test('a source recipe remains blocked for cooking and automatic selection until reviewed',()=>{
 const r=recipeForReview({schemaVersion:'1.0',kind:'recipe',id:'wikibooks:recipe:test',countries:[],provenance:{sourceId:'wikibooks',url:'https://en.wikibooks.org/wiki/Cookbook:Rice',license:'CC BY-SA 4.0',attribution:'Wikibooks contributors'},data:{name:'Rice',yield:{value:2},ingredients:[{name:'rice',amount:100,unit:'g'}],directions:['Cook']}});
 assert.equal(quantified(r),false);
 assert.throws(()=>cookMeal({recipe:r,inventory:[],products:{},servings:2,date:'2026-10-13'}),/quantities/);
 assert.deepEqual(generateHouseholdDay([r],[],{},[],'2026-10-13'),[]);
 assert.equal(pantryDuration([r],[{ingredient:'rice',quantity:1000,unit:'g'}],[],2,'2026-10-13').meals,0);
});
test('corpus paging binds filters and reads only the dedicated public database',async()=>{
 const calls=[],records=[{id:'a',countries:['FR'],document:JSON.stringify({countries:['FR'],kind:'product',data:{name:'A'}})},{id:'b',countries:['US'],document:JSON.stringify({countries:['US'],kind:'product',data:{name:'B'}})},{id:'c',document:'unused'}];
 const database={prepare(sql){return {bind(...args){calls.push({sql,args});return {first:async()=>({release_id:'r1',document:JSON.stringify({scope:'complete named release',license:'ODbL',publishedRecords:3})}),all:async()=>({results:records})};}}}};
 const env={PRODUCT_CORPUS:database,DB:{prepare(){throw Error('Private DB touched');}}};
 const result=await corpusLookup(env,{source:'off',country:'FR',query:"a%_'",limit:2});
 assert.equal(result.records.length,1);assert.equal(result.nextCursor,'b');assert.equal(result.withheld,1);
 assert.equal(calls[1].sql.includes("a%_'"),false);assert.equal(calls[1].args[3],"%a\\%\\_'%");
 assert.equal(await corpusLookup({}, {source:'off'}),null);
});
