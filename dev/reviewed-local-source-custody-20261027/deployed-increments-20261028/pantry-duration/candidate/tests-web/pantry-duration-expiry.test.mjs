import test from 'node:test';
import assert from 'node:assert/strict';
const {pantryDuration}=await import(process.env.HOUSEHOLD_MODEL_URL||'../public/household-model.js');
const recipe={id:'user-rice',title:'User rice',servings:1,ingredients:[{ingredient:'rice',quantity:100,unit:'g'}],instructions:[],source:'user',license:'private'};
const lot=(id,quantity,expires)=>({id,ingredient:'rice',quantity,unit:'g',expires,needsReview:false});
const run=(inventory,date='2026-10-28',mealsPerDay=3)=>pantryDuration([recipe],inventory,[],1,date,mealsPerDay);
test('today expiry cannot support future complete days',()=>{
 const inventory=[lot('today',900,'2026-10-28')],before=structuredClone(inventory);
 const result=run(inventory);assert.equal(result.meals,3);assert.equal(result.days,1);assert.deepEqual(inventory,before);
});
test('expiry remains usable on its date and unavailable on next simulated day',()=>{
 assert.equal(run([lot('tomorrow',900,'2026-10-29')]).meals,6);
 assert.equal(run([lot('expired',900,'2026-10-27')]).meals,0);
});
test('expiry-first allocation preserves long-lived lots despite input order',()=>{
 const inventory=[lot('later',300,'2026-11-01'),lot('today',300,'2026-10-28')];
 assert.equal(run(inventory).meals,6);assert.deepEqual(run(inventory),run([...inventory].reverse()));
});
test('UTC simulated days cross month/year and leap boundaries',()=>{
 assert.equal(run([lot('year',900,'2027-01-01')],'2026-12-31').meals,6);
 assert.equal(run([lot('leap',900,'2028-02-29')],'2028-02-28').meals,6);
});
test('undated stock retains quantity-only estimate and caller frequency',()=>{
 assert.equal(run([lot('undated',900,null)]).meals,9);
 assert.equal(run([lot('today',900,'2026-10-28')],'2026-10-28',2).meals,2);
});
