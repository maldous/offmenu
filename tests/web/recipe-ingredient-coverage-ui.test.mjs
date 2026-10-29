// Generated native-DOM harness, not browser/profile/corpus/API evidence.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
import {parse} from 'acorn';
import {appendRecipeIngredientCoverage} from '../../apps/web/src/recipe-ingredient-coverage-ui.js';
import {recipeIngredientCoverage} from '../../apps/web/src/recipe-ingredient-coverage.js';
import {rankedMenus} from '../../apps/web/src/household-model.js';
import {quantified,displayAmount} from '../../apps/web/src/ingredients.js';
import {normalize} from '../../apps/web/src/model.js';
import {locationKey} from '../../apps/web/src/checkout-model.js';
import {planSummary,NUTRIENTS} from '../../apps/web/src/menu-model.js';
import {t,setLocalizedText,getLanguage} from '../../apps/web/src/i18n.js';
import {normalizeSearchText,multilingualSearchText,showLocalized,localizedField,displayName} from '../../apps/web/src/content-locale.js';
const date='2026-10-26';
class Element{
 constructor(tag,document){this.tagName=tag;this.ownerDocument=document;this.children=[];this.dataset={};this.style={};this.className='';this.ownText='';this.value='';this.checked=false;this.attributes={};this.classList={toggle:(name,on)=>{this.classes??=new Set();on?this.classes.add(name):this.classes.delete(name);}};}
 set textContent(v){this.ownText=String(v);this.children=[];}get textContent(){return this.ownText+this.children.map(n=>n.textContent).join('');}
 set innerHTML(v){throw Error('Untrusted markup must never be parsed.');}
 append(...nodes){for(const n of nodes){const v=typeof n==='string'?this.ownerDocument.createTextNode(n):n;v.parentNode=this;this.children.push(v);}}
 replaceChildren(...nodes){this.children=[];this.ownText='';this.append(...nodes);}setAttribute(k,v){this.attributes[k]=v;}
}
const document=()=>{const d={created:[],createElement(tag){d.created.push(tag);return new Element(tag,d);},createTextNode(value){return {textContent:String(value),ownerDocument:d};}};return d;};
const ingredient=(name='rice',quantity=100,unit='g')=>({ingredient:name,quantity,unit});
const recipe=(ingredients=[ingredient()])=>({id:'generated-recipe',title:'Generated meal',servings:1,ingredients,instructions:['Generated instruction.'],source:'Generated fixture',license:'generated-only'});
const lot=(id,quantity=100,extra={})=>({id,barcode:'generated-'+id,name:'Generated rice',ingredient:'rice',quantity,unit:'g',...extra});
const freeze=v=>{if(v&&typeof v==='object'){Object.values(v).forEach(freeze);Object.freeze(v);}return v;};
const all=(node,predicate)=>[...(predicate(node)?[node]:[]),...(node.children||[]).flatMap(n=>all(n,predicate))];
const choice=element=>element.children.find(n=>n.dataset?.coverageChoice);
function render({r=recipe(),inventory=[],products={},members=[],status}={}){
 const admitted=rankedMenus([r],inventory,products,members,1,date)[0];if(status)admitted.status=status;
 const doc=document(),card=doc.createElement('article'),input={recipe:admitted,inventory,products,servings:1,date};
 const before=structuredClone(input);freeze(input);const result=appendRecipeIngredientCoverage(card,input);assert.deepEqual(input,before);
 return {...result,card,doc,input};
}
const source=readFileSync(new URL('../../apps/web/src/app.js',import.meta.url),'utf8');
const findMeals=parse(source,{ecmaVersion:'latest',sourceType:'module'}).body.find(n=>n.type==='FunctionDeclaration'&&n.id.name==='findMeals');

test('actual proposed findMeals card append uses the same admitted context and two allocated locations',()=>{
 const r=recipe(),inventory=[lot('later',50,{expires:'2026-10-29',location:{area:'Pantry',shelf:'B'}}),lot('first',50,{expires:'2026-10-27',location:{area:'Fridge <script>',shelf:'A'}})],products={'generated-later':{nutrition_data_per:'100g'},'generated-first':{nutrition_data_per:'100g'}};
 const before=structuredClone({r,inventory,products});freeze(inventory);freeze(products);const doc=document(),nodes=new Map(),$=id=>{if(!nodes.has(id))nodes.set(id,doc.createElement('div'));return nodes.get(id);};
 $('servings').value='1';$('plan-date').value=date;let calls=0,result,observedContext;
 const context={document:doc,$,recipeLibrary:{refresh(){}},recipes:[r],products,profile:{members:[],units:'metric'},selections:[],absentDiners:new Set(),menuInventory:()=>inventory,renderDinnerMembers(){},rankedMenus,quantified,today:()=>date,setLocalizedText,t,getLanguage,normalizeSearchText,multilingualSearchText,showLocalized,localizedField,displayName,displayAmount,normalize,locationKey,planSummary,NUTRIENTS,renderPlan(){},appendRecipeIngredientCoverage(card,input){calls++;observedContext=input;assert.equal(input.inventory,inventory);assert.equal(input.products,products);assert.equal(input.servings,1);assert.equal(input.date,date);result=appendRecipeIngredientCoverage(card,input);}};
 vm.createContext(context);vm.runInContext(source.slice(findMeals.start,findMeals.end),context);context.findMeals();
 assert.equal(calls,1);const card=$('meals').children[0],i=card.children.indexOf(result.element);assert.match(card.children[i-1].textContent,/All measured ingredients/);assert.equal(choice(result.element).textContent,'Ready now');
 assert.match(result.element.textContent,/50 g · Fridge <script> \/ A/);assert.match(result.element.textContent,/50 g · Pantry \/ B/);assert.equal(doc.created.includes('script'),false);
 assert.deepEqual(result.coverage,recipeIngredientCoverage(observedContext));assert.deepEqual({r,inventory,products},before);
});
test('positive inherited shortfall shows exact units and one-item choice only for missing card',()=>{
 const out=render({r:recipe([ingredient('rice',120)]),inventory:[lot('rice',100)]});assert.equal(choice(out.element).textContent,'One item to add');assert.match(out.element.textContent,/Covered 100 g \/ required 120 g/);assert.match(out.element.textContent,/Still needed: 20 g/);
});
test('rounded-zero matching disagreement stays reviewable without a zero-gap extra-item claim',()=>{
 const out=render({r:recipe([ingredient('rice',1)]),inventory:[lot('rice',.99999999)]});assert.equal(out.coverage.classificationAgreement,false);assert.equal(choice(out.element).dataset.coverageChoice,'unknown');assert.match(out.element.textContent,/no positive shortfall is confirmed/);assert.doesNotMatch(out.element.textContent,/One item to add|Still needed: 0/);assert.match(out.element.textContent,/0\.99999999 g/);
});
test('unresolved stock keeps uncovered quantity and absent location explicitly unknown',()=>{
 const out=render({inventory:[lot('known',20),lot('unknown',null)]});assert.equal(out.coverage.requirements[0].uncoveredQuantity,null);assert.match(out.element.textContent,/Uncovered quantity is unknown/);assert.match(out.element.textContent,/20 g · Location unknown/);assert.equal(choice(out.element).dataset.coverageChoice,'unknown');assert.doesNotMatch(out.element.textContent,/Still needed: 80 g|Ready now|One item to add/);
});
test('existing source-review, blocked-diet and package-check decisions withhold definitive choices',()=>{
 const sourceReview=render({inventory:[lot('rice')],status:'needs_review'});assert.equal(sourceReview.coverage.choices.readyNow,true);assert.notEqual(choice(sourceReview.element).dataset.coverageChoice,'ready');
 const vegan={id:'generated-member',name:'Generated',portion:1,advisors:['vegan'],avoid:[],restrictions:[]};
 const blocked=render({r:recipe([ingredient('milk',100,'ml')]),inventory:[lot('milk',100,{ingredient:'milk',unit:'ml'})],members:[vegan]});assert.equal(blocked.coverage.choices.readyNow,true);assert.equal(blocked.input.recipe.group.compatible,false);assert.equal(choice(blocked.element).dataset.coverageChoice,'review');
 const checked=render({inventory:[lot('rice')],members:[{...vegan,advisors:[],restrictions:[{type:'allergy',term:'peanut'}]}]});assert.equal(checked.input.recipe.group.compatible,true);assert.equal(checked.input.recipe.group.automaticSelection,false);assert.equal(choice(checked.element).dataset.coverageChoice,'review');
});
test('duplicate required lines retain source order and source allocations; optional line is omitted',()=>{
 const out=render({r:recipe([{...ingredient('salt',null),optional:true},ingredient('rice',60),ingredient('rice',60)]),inventory:[lot('rice',100)]});const rows=all(out.element,n=>n.dataset?.requirementIndex!==undefined);assert.deepEqual(rows.map(n=>n.dataset.requirementIndex),['1','2']);assert.equal(out.coverage.requirements.flatMap(r=>r.allocations).reduce((n,a)=>n+a.quantity,0),100);assert.match(rows[0].textContent,/Covered 60 g \/ required 60 g/);assert.match(rows[1].textContent,/Covered 40 g \/ required 60 g/);assert.match(rows[1].textContent,/Still needed: 20 g/);
});
test('nutrition basis is a separate per-lot status and never a total or health claim',()=>{
 const out=render({inventory:[lot('a',50),lot('b',50)],products:{'generated-a':{nutrition_data_per:'100g',nutriments:{proteins_100g:8}},'generated-b':{nutrition_data_per:'100ml'}}});assert.match(out.element.textContent,/Nutrition basis compatible; nutrient values may still be missing/);assert.match(out.element.textContent,/Nutrition basis unsupported or unknown/);assert.match(out.element.textContent,/Nutrient completeness is not established/);assert.doesNotMatch(out.element.textContent,/Protein|kcal|allergen.free|safe to eat/);
});
test('an unavailable coverage calculation appends an unknown-only native panel without changing the card',()=>{
 const doc=document(),card=doc.createElement('article'),old=doc.createElement('p');old.textContent='Existing review remains';card.append(old);const input={recipe:{...recipe(),status:'ready',group:{compatible:true,automaticSelection:true}},inventory:[lot('same'),lot('same')],products:{},servings:1,date};const before=structuredClone(input),out=appendRecipeIngredientCoverage(card,input);assert.equal(out.coverage,null);assert.equal(card.children[0],old);assert.match(out.element.textContent,/coverage is unavailable/);assert.doesNotMatch(out.element.textContent,/Ready now|One item to add/);assert.deepEqual(input,before);
});
