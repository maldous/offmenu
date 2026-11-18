import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import {parse} from 'acorn';
import {ingredientUnlocks} from '../../apps/web/src/household-model.js';
import {setLocalizedText} from '../../apps/web/src/i18n.js';
import {matchMeals} from '../../apps/web/src/model.js';

const date='2026-11-18';
const recipe=(id,quantity,unit='g')=>({
  id,title:id,servings:1,
  ingredients:[{ingredient:'rice',unit,quantity}]
});
const lot=(quantity,unit='g')=>({ingredient:'rice',quantity,unit});

for(const [name,demand,onHand] of [
  ['sub-milligram',0.0004,0],
  ['four decimal places',1.2344,0],
  ['existing stock and a binary rounding boundary',0.21,0.05],
  ['no unnecessary rounding up',1.2356,0],
]){
  test('the suggested '+name+' shortfall actually unlocks the measured recipe',()=>{
    const recipes=[recipe('One menu',demand)];
    const inventory=Object.freeze([Object.freeze(lot(onHand))]);
    assert.equal(matchMeals(inventory,recipes,1,date)[0].status,'missing');
    const [unlock]=ingredientUnlocks(recipes,inventory,1,date);
    assert.deepEqual(unlock.recipes,['One menu']);
    assert.equal(unlock.unit,'g');
    assert.ok(unlock.quantity>0);
    if(!onHand)assert.equal(unlock.quantity,Math.max(0.001,demand));
    const received=[...inventory,lot(unlock.quantity,unlock.unit)];
    assert.equal(matchMeals(received,recipes,1,date)[0].status,'ready');
    assert.equal(inventory[0].quantity,onHand);
  });
}

test('one quantity unlocks each listed alternative separately, not an incompatible unit',()=>{
  const recipes=[recipe('Smaller',0.0004),recipe('Larger',1.2344),recipe('Liquid',0.9,'ml')];
  const [grams,volume]=ingredientUnlocks(recipes,[],1,date);
  assert.deepEqual(grams.recipes,['Smaller','Larger']);
  assert.equal(grams.quantity,1.2344);
  assert.equal(volume.unit,'ml');
  const matches=matchMeals([lot(grams.quantity,grams.unit)],recipes,1,date);
  assert.deepEqual(matches.filter(r=>r.status==='ready').map(r=>r.id),grams.recipes);
  assert.equal(matches.find(r=>r.id==='Liquid').status,'missing');
  assert.deepEqual(ingredientUnlocks(recipes,[],1,date,[{avoid:['rice']}]),[]);
});

test('an unrepresentable restocked total stays unknown instead of promising an unlock',()=>{
  const recipes=[recipe('Limit',Number.MAX_VALUE)];
  // At this boundary the two neighboring quantities land just below the
  // requirement or at Infinity. Neither is a valid finite restock.
  for(const onHand of [2**970,3*(2**970)]){
    const stock=[lot(onHand)];
    assert.equal(matchMeals(stock,recipes,1,date)[0].status,'missing');
    assert.equal(matchMeals(stock,recipes,1,date,{forRestock:true})[0].status,'needs_review');
    assert.deepEqual(ingredientUnlocks(recipes,stock,1,date),[]);
  }
});

test('My week renders an actionable quantity and removes the suggestion after restocking',()=>{
  // Exercise the shipped route and translator with isolated DOM/stock; no real account writes.
  const source=readFileSync(new URL('../../apps/web/src/app.js',import.meta.url),'utf8');
  const nodes=parse(source,{ecmaVersion:'latest',sourceType:'module'}).body;
  const renderer=nodes.find(n=>n.type==='FunctionDeclaration'&&n.id.name==='renderUnlocks');
  const plan=nodes.find(n=>n.type==='FunctionDeclaration'&&n.id.name==='renderPlan');
  assert.ok(plan.body.body.some(n=>n.expression?.callee?.name==='renderUnlocks'));
  const element=()=>({children:[],append(...x){this.children.push(...x);},replaceChildren(){this.children=[];}});
  const output=element(),stock=[];
  const fields={'ingredient-unlocks':output,servings:{value:'1'}};
  const context={document:{createElement:element},$:id=>fields[id],today:()=>date,
    recipes:[recipe('Synthetic rice',0.0004)],unexpiredInventory:()=>stock,
    profile:{members:[]},ingredientUnlocks,setLocalizedText};
  const render=runInNewContext('('+source.slice(renderer.start,renderer.end)+')',context);
  render();
  assert.equal(output.children[0].children[0].textContent,'rice → 1 more menu choices');
  const details=output.children[0].children[1].textContent;
  assert.equal(details,'At least 0.001 g for any one recipe: Synthetic rice');
  assert.equal(stock.length,0);
  stock.push(lot(Number(details.split(' ')[2])));
  render();
  assert.equal(output.children.length,1);
  assert.match(output.children[0].textContent,/No single-ingredient unlocks/);
});

test('unlock identity retains separators and excludes unusable stock identities',()=>{
  const named=name=>({...recipe('Test menu',1),ingredients:[{ingredient:name,unit:'g',quantity:1}]});
  const [hint]=ingredientUnlocks([named('rice|grain')],[],1,date);
  assert.equal(hint.ingredient,'rice|grain');
  assert.equal(hint.unit,'g');
  assert.deepEqual(ingredientUnlocks([named('rice|grain')],[{...lot(hint.quantity),ingredient:hint.ingredient}],1,date),[]);
  for(const name of ['  ',' REVIEW:rice '])
    assert.deepEqual(ingredientUnlocks([named(name)],[],1,date),[]);
});

test('ingredient unlock recommendations respect the actual manual stock form floor',()=>{
  const html=readFileSync(new URL('../../apps/web/assets/index.html',import.meta.url),'utf8');
  const input=html.match(/<input\b[^>]*\bid="food-quantity"[^>]*>/)[0];
  assert.match(input,/\bstep="any"/);
  const min=Number(input.match(/\bmin="([^"]+)"/)[1]);
  const recipes=[recipe('Tiny',0.0004)];
  assert.equal(matchMeals([],recipes,1,date,{forRestock:true})[0].missing[0].quantity,0.0004);
  assert.equal(ingredientUnlocks(recipes,[],1,date)[0].quantity,min);
});
