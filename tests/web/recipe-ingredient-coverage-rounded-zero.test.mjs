import test from 'node:test';
import assert from 'node:assert/strict';
import {recipeIngredientCoverage} from '../../apps/web/src/recipe-ingredient-coverage.js';
import {matchMeals} from '../../apps/web/src/model.js';
import {allocateIngredients} from '../../apps/web/src/cooking-model.js';

test('W06-RECIPE-COVERAGE-ROUNDED-ZERO-01: zero/nonfinite matching gaps withhold the choice while core evidence stays exact',()=>{
 const date='2026-10-26',recipe={id:'generated-rounding-recipe',servings:1,
  ingredients:[{ingredient:'rice',quantity:1,unit:'g'}]};
 const inventory=[{id:'generated-lot',barcode:'generated-product',ingredient:'rice',quantity:.9999,unit:'g'}];
 const products={'generated-product':{nutrition_data_per:'100g'}};
 const before=structuredClone({recipe,inventory,products});
 const out=recipeIngredientCoverage({recipe,inventory,products,servings:1,date});
 const matched=matchMeals(inventory,[recipe],1,date)[0];
 const allocated=allocateIngredients(recipe,inventory,1,date);
 assert.equal(out.matching.status,'missing');assert.equal(out.matching.missing[0].quantity,0);
 assert.equal(out.classificationAgreement,true,'Both existing categories remain missing.');
 assert.deepEqual(out.matching,{status:matched.status,demandKnown:matched.demandKnown,coverage:matched.coverage,
  missing:matched.missing,unknown:matched.unknown,reviewReasons:matched.reviewReasons});
 assert.equal(out.requirements[0].coveredQuantity,allocated.deductions[0].quantity);
 assert.equal(out.requirements[0].uncoveredQuantity,allocated.missing[0].quantity);
 assert.equal(out.requirements[0].uncoveredQuantity,0.00009999999999998899);
 assert.equal(out.requirements[0].status,'uncovered');
 assert.equal(out.requirements[0].allocations[0].nutritionBasisEligible,true);
 assert.equal(out.requirements[0].nutritionBasisEligible,false);
 assert.deepEqual(out.choices,{readyNow:false,oneExtraItem:false,unknown:true});
 assert.deepEqual({recipe,inventory,products},before);

 // Positive, representable displayed shortfall keeps the existing choice.
 const supported=recipeIngredientCoverage({recipe,inventory:[{...inventory[0],quantity:.9}],products,servings:1,date});
 assert.equal(supported.matching.missing[0].quantity,.1);
 assert.deepEqual(supported.choices,{readyNow:false,oneExtraItem:true,unknown:false});

 // Each demand is finite; the existing matcher's grouped sum can overflow.
 // The shared matcher now withholds unrepresentable arithmetic explicitly.
 const huge={...recipe,ingredients:[{ingredient:'rice',quantity:1e308,unit:'g'},{ingredient:'rice',quantity:1e308,unit:'g'}]};
 const nonfinite=recipeIngredientCoverage({recipe:huge,inventory:[],products:{},servings:1,date});
 assert.deepEqual(nonfinite.matching.missing,[]);
 assert.equal(nonfinite.matching.status,'needs_review');
 assert.equal(nonfinite.matching.coverage,null);
 assert.ok(nonfinite.matching.reviewReasons.includes('arithmetic_unrepresentable'));
 assert.deepEqual(nonfinite.choices,{readyNow:false,oneExtraItem:false,unknown:true});
 assert.deepEqual(nonfinite.requirements.map(r=>r.uncoveredQuantity),[1e308,1e308]);
});
