import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {preparedMenuComposition} from '../public/prepared-menu-owner22.mjs';
import {recipeForReview} from '../public/recipe-review.js';

// Portable source-shape regression fixture, not a source recipe or admission.
const actual={kind:'recipe',id:'synthetic:prepared-menu-null-yield',
  provenance:{sourceId:'world-recipes',revisionId:'synthetic-revision-1',
    url:'https://example.invalid/portable-fixture',license:'CC0-1.0',attribution:'Synthetic test fixture'},
  data:{name:'Portable unknown-yield fixture',yield:{value:null,unit:'portion'},
    ingredients:[{name:'Synthetic ingredient',ingredientId:null,amount:null,unit:null,
      originalText:'1 cup synthetic ingredient',quantityStatus:'source-measure-needs-review',
      sourceQuantity:{value:1,unit:'cup',original:'1 cup synthetic ingredient',status:'synthetic'},scaling:'linear'}],
    directions:['Synthetic instruction; not a cooking recommendation.']}};
const clone=x=>structuredClone(x);
function syntheticContext() {
  const r=clone(actual);r.data.ingredients=[{ingredientId:'synthetic-original',name:'Synthetic ingredient',amount:100,unit:'g',
    form:'cooked',basis:'recipe-batch',quantityStatus:'synthetic',nutrients:{protein_g:{value:10,unit:'g'}},
    sourceQuantity:{value:100,unit:'g',original:'100 g synthetic ingredient'}}];
  return r;
}
function proposal() {return {lineIndex:0,replacement:{id:'synthetic-replacement',version:'1',name:'Synthetic replacement',
  form:'cooked',basis:'recipe-batch',quantity:{value:80,unit:'g'},provenance:{sourceId:'synthetic-only'}}};}
const scoped=({kind,binding})=>({status:'supported',scope:kind==='serving'?'portion-fraction':'culinary-function',
  binding,provenance:{sourceId:'synthetic-owner-evidence',url:'https://example.invalid/synthetic-only'}});

test('portable source-shape fixture: actual caller gap preserves unknown yield and units',()=>{
  assert.equal(actual.id,'synthetic:prepared-menu-null-yield');
  const old=recipeForReview(actual);assert.equal(old.servings,1);assert.equal(old.servingsUnknown,true);
  assert.equal(old.ingredients[0].sourceQuantity,undefined);
  const view=preparedMenuComposition(actual);
  assert.equal(view.sourceYield.value,null);
  assert.equal(view.lines[0].sourceQuantity.unit,'cup');
  assert.equal(view.lines[0].sourceQuantity.value,1);
  assert.equal(view.lines[0].parsedQuantity.value,null);
  assert.equal(view.lines[0].parsedQuantity.basis,null);
  assert.equal(view.finalBatchYield,null);
  assert.equal(view.cookingEligible,false);
  assert.equal(view.nutrientComposition,null);
});

test('existing authored source quantities are not prepared serving mass or retention evidence',()=>{
  const starter=JSON.parse(readFileSync(new URL('../public/recipes.json',import.meta.url),'utf8'))[0];
  // Explicit source-shape bridge, no claim that recipe.servings is measured mass.
  const record={kind:'recipe',id:starter.id,version:starter.version,provenance:{sourceId:'offmenu-original',
    attribution:starter.attribution,license:starter.license},data:{yield:{value:starter.servings,unit:'portion'},
    ingredients:starter.ingredients.map(i=>({...i,amount:i.quantity})),directions:starter.instructions}};
  const view=preparedMenuComposition(record);
  assert.equal(view.sourceYield.value,2);
  assert.equal(view.lines.find(l=>l.original.ingredient==='water').parsedQuantity.unit,'ml');
  assert.equal(view.finalBatchYield,null);
  assert.ok(view.lines.every(l=>l.compositionAfterSubstitution===null));
});

test('source ranges, methods, qualifiers and custody are detached without conversion',()=>{
  const r=clone(actual);r.data.ingredients[0].sourceQuantity.range={min:1,max:2};
  r.provenance.accountScope='synthetic-private';r.provenance.consent={export:false};
  const before=clone(r), view=preparedMenuComposition(r);
  assert.deepEqual(view.sourceSnapshot,before);
  assert.deepEqual(view.lines[0].sourceQuantity.range,{min:1,max:2});
  view.sourceSnapshot.provenance.consent.export=true;view.lines[0].sourceQuantity.range.min=0;
  assert.deepEqual(r,before);
});

test('client substitution support flags never qualify scope or transfer original nutrients',()=>{
  const r=syntheticContext(), p={...proposal(),status:'supported',scope:'culinary-function'};
  const view=preparedMenuComposition(r,{substitutions:[p]});
  assert.equal(view.lines[0].substitution.status,'unknown');assert.equal(view.lines[0].selected,null);
  assert.equal(view.lines[0].original.nutrients.protein_g.value,10);
  assert.equal(view.lines[0].compositionAfterSubstitution,null);
});

test('exact qualified culinary scope selects replacement but never nutrition/identity equivalence',()=>{
  const r=syntheticContext(), p=proposal(), before=clone({r,p});
  const view=preparedMenuComposition(r,{substitutions:[p],resolveScope:scoped});
  assert.equal(view.lines[0].substitution.status,'supported');
  assert.equal(view.lines[0].substitution.scope,'culinary-function');
  assert.equal(view.lines[0].selected.id,'synthetic-replacement');
  assert.equal(view.lines[0].selected.nutrients,undefined);
  assert.equal(view.lines[0].compositionAfterSubstitution,null);
  assert.equal(view.cookingEligible,false);
  assert.deepEqual({r,p},before);
});

test('unknown versions, preparation/basis, wrong evidence binding and broad scope remain unknown',()=>{
  for(const edit of [r=>delete r.provenance.revisionId,r=>r.data.ingredients[0].form=null,
    r=>r.data.ingredients[0].basis=null,r=>r.data.ingredients[0].ingredientId=null]) {
    const r=syntheticContext();edit(r);
    assert.equal(preparedMenuComposition(r,{substitutions:[proposal()],resolveScope:scoped}).lines[0].substitution.status,'unknown');
  }
  for(const resolveScope of [x=>({...scoped(x),scope:'nutrition-equivalent'}),
    x=>({...scoped(x),binding:{...x.binding,recipeVersion:'wrong'}}),
    x=>({...scoped(x),binding:{...x.binding,replacementQuantity:{value:100,unit:'g'}}})]) {
    assert.equal(preparedMenuComposition(syntheticContext(),{substitutions:[proposal()],resolveScope}).lines[0].substitution.status,'unknown');
  }
});

test('source-bound portion is unknown by default; exact qualified fraction remains non-nutritional',()=>{
  const r=syntheticContext(), serving={recipeId:r.id,recipeVersion:r.provenance.revisionId,fraction:0.25,form:'cooked',basis:'recipe-batch'};
  assert.equal(preparedMenuComposition(r,{serving}).serving.qualifiedFraction,null);
  const v=preparedMenuComposition(r,{serving,resolveScope:scoped});
  assert.equal(v.serving.qualifiedFraction,0.25);assert.equal(v.nutrientComposition,null);
  assert.equal(v.lines[0].parsedQuantity.value,100,'Do not silently scale ingredient amounts');
  assert.equal(preparedMenuComposition(r,{serving:{...serving,recipeVersion:'wrong'},resolveScope:scoped}).serving.status,'unknown');
});

test('bounded unique proposals, synchronous evidence and resolver mutation isolation',()=>{
  const r=syntheticContext(), p=proposal();
  assert.throws(()=>preparedMenuComposition(r,{substitutions:[p,p]}),/Unique/);
  assert.throws(()=>preparedMenuComposition(r,{substitutions:[{...p,lineIndex:99}]}),/Unique/);
  assert.throws(()=>preparedMenuComposition(r,{substitutions:[p],resolveScope:async()=>null}),/synchronous/);
  const before=clone(r);preparedMenuComposition(r,{substitutions:[p],resolveScope:x=>{x.candidate.replacement.name='mutated';return null;}});
  assert.deepEqual(r,before);
});

test('provider P2: binding ignores key order but never equates NaN with null',()=>{
  const reordered=preparedMenuComposition(syntheticContext(),{substitutions:[proposal()],resolveScope:x=>({
    ...scoped(x),binding:{...x.binding,replacementQuantity:{unit:'g',value:80}}})});
  assert.equal(reordered.lines[0].substitution.status,'supported');
  const p=proposal();p.replacement.quantity.value=NaN;
  const invalid=preparedMenuComposition(syntheticContext(),{substitutions:[p],resolveScope:x=>({
    ...scoped(x),binding:{...x.binding,replacementQuantity:{value:null,unit:'g'}}})});
  assert.equal(invalid.lines[0].substitution.status,'unknown');
});

test('provider P2: conflict needs the exact scope, binding and provenance',()=>{
  const conflict=x=>({...scoped(x),status:'conflict'});
  assert.equal(preparedMenuComposition(syntheticContext(),{substitutions:[proposal()],resolveScope:conflict}).lines[0].substitution.status,'conflict');
  for(const resolver of [x=>({...conflict(x),binding:{...x.binding,recipeId:'other'}}),
    x=>({...conflict(x),scope:'unrelated'}),x=>({...conflict(x),provenance:null})]) {
    assert.equal(preparedMenuComposition(syntheticContext(),{substitutions:[proposal()],resolveScope:resolver}).lines[0].substitution.status,'unknown');
  }
  const r=syntheticContext(), serving={recipeId:r.id,recipeVersion:r.provenance.revisionId,fraction:0.25,form:'cooked',basis:'recipe-batch'};
  assert.equal(preparedMenuComposition(r,{serving,resolveScope:conflict}).serving.status,'conflict');
  assert.equal(preparedMenuComposition(r,{serving,resolveScope:x=>({...conflict(x),binding:{...x.binding,fraction:0.5}})}).serving.status,'unknown');
});
