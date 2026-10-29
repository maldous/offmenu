import {pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
const root='/tmp/offmenu-lifecycle2337-localized-20261017';
const {validateLot,matchMeals}=await import(pathToFileURL(root+'/public/model.js'));
const {pantryDuration}=await import(pathToFileURL(root+'/public/household-model.js'));
const {validateState}=await import(pathToFileURL(root+'/cloud/state.mjs'));
const lot={id:'live',barcode:'local:rice',name:'Rice',ingredient:'rice',quantity:100,unit:'g',expires:'2026-10-20'};
const recipe={id:'rice-meal',title:'Rice meal',source:'Synthetic focused fixture',license:'CC0',instructions:['Cook rice.'],servings:1,ingredients:[{ingredient:'rice',quantity:100,unit:'g'}]};
const date='2026-10-17';
const attempt=fn=>{try{return {accepted:true,value:fn()};}catch(e){return {accepted:false,error:e.message};}};
const qty={};for(const [name,value] of Object.entries({null:null,missing:undefined,blank:'',spaces:'   ',zero:0,stringZero:'0',positive:100,stringPositive:'100',boolean:false,negative:-1})){const r=attempt(()=>validateLot({...lot,quantity:value}));qty[name]={accepted:r.accepted,...(r.accepted?{quantity:r.value.quantity}:{error:r.error})};}
const match=r=>{const v=matchMeals([lot],[r],1,date)[0];return {status:v.status,unknown:v.unknown,missing:v.missing,coverage:v.coverage,demandKnown:v.demandKnown??null,reviewReasons:v.reviewReasons??null};};
const matching={unknownYieldAndReview:match({...recipe,servingsUnknown:true,needsReview:true}),unknownYieldOnly:match({...recipe,servingsUnknown:true}),absentYield:match({...recipe,servings:null}),reviewKnownYield:match({...recipe,needsReview:true}),knownYield:match(recipe),knownYieldMissing:match({...recipe,ingredients:[{ingredient:'rice',quantity:200,unit:'g'}]}),unknownIngredientQuantity:match({...recipe,ingredients:[{ingredient:'rice',quantity:null,unit:'g'}]})};
const duration=inventory=>pantryDuration([recipe],inventory,[],1,date,1).meals;
const durationCases={liveOnly:duration([lot]),expiredFirst:duration([{...lot,id:'expired',quantity:1000,expires:'2026-10-01'},lot]),expiredLast:duration([lot,{...lot,id:'expired',quantity:1000,expires:'2026-10-01'}]),reviewFirst:duration([{...lot,id:'review',quantity:1000,needsReview:true},lot]),invalidQuantityFirst:duration([{...lot,id:'unknown',quantity:null},lot]),differentUnitFirst:duration([{...lot,id:'milk',quantity:1000,unit:'ml'},lot]),zeroFirst:duration([{...lot,id:'zero',quantity:0},lot]),knownThreeMeals:duration([{...lot,quantity:300}])};
const state=quantity=>attempt(()=>validateState({inventory:[{...lot,quantity}],products:{},recipes:[],selections:[],profile:{country:'AU',units:'metric',servings:1}}));
const stateNull=state(null),stateZero=state(0),savedState={nullAccepted:stateNull.accepted,nullError:stateNull.error??null,zeroAccepted:stateZero.accepted,zeroQuantity:stateZero.value?.inventory[0]?.quantity??null};
const result={mode:process.argv[2],quantity:qty,matching,duration:durationCases,savedState,inputInventoryUnchanged:lot.quantity===100};
console.log(JSON.stringify(result,null,2));
if(process.argv[2]==='after'){
 for(const name of ['null','missing','blank','spaces','boolean','negative'])assert.equal(qty[name].accepted,false,name+' rejected');
 for(const name of ['zero','stringZero']){assert.equal(qty[name].accepted,true);assert.equal(qty[name].quantity,0);}
 for(const name of ['positive','stringPositive'])assert.equal(qty[name].quantity,100);
 for(const name of ['unknownYieldAndReview','unknownYieldOnly','absentYield']){assert.equal(matching[name].status,'needs_review');assert.equal(matching[name].demandKnown,false);assert.equal(matching[name].coverage,null);assert.deepEqual(matching[name].missing,[]);assert.ok(matching[name].unknown.length);assert.ok(matching[name].reviewReasons.includes('yield_unknown'));}
 assert.equal(matching.reviewKnownYield.status,'needs_review');assert.equal(matching.reviewKnownYield.demandKnown,false);assert.equal(matching.reviewKnownYield.coverage,null);assert.deepEqual(matching.reviewKnownYield.missing,[]);assert.ok(matching.reviewKnownYield.reviewReasons.includes('source_review_required'));
 assert.equal(matching.knownYield.status,'ready');assert.equal(matching.knownYield.coverage,1);assert.equal(matching.knownYield.demandKnown,true);
 assert.equal(matching.knownYieldMissing.status,'missing');assert.deepEqual(matching.knownYieldMissing.missing,[{ingredient:'rice',unit:'g',quantity:100}]);
 assert.equal(matching.unknownIngredientQuantity.status,'needs_review');
 for(const [name,count]of Object.entries(durationCases))assert.equal(count,name==='knownThreeMeals'?3:1,name);
 assert.equal(savedState.nullAccepted,false);assert.equal(savedState.zeroAccepted,true);assert.equal(savedState.zeroQuantity,0);assert.equal(result.inputInventoryUnchanged,true);
 console.log('PASS: Q01/Q02/Q03 focused regressions, saved-state boundary and affected valid controls.');
}
