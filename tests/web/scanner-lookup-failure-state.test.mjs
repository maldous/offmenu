import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {createRequire} from 'node:module';
const {parse}=createRequire(import.meta.url)('acorn');

for(const path of ['../../apps/web/src/shelf-scanner.js','../../apps/web/src/production-scanner/shelf-scanner.js']){
 const source=readFileSync(new URL(path,import.meta.url),'utf8');
 const render=parse(source,{ecmaVersion:'latest',sourceType:'module'}).body.find(n=>n.type==='FunctionDeclaration'&&n.id.name==='render');
 function draw({status='unavailable',selected=null}={}){
  const elements=new Map(),$=id=>{if(!elements.has(id))elements.set(id,{textContent:'',dataset:{},setAttribute(){}});return elements.get(id);};
  const context={$,...{selected,current:{id:'captured',raw:'4088700055496',namespace:'barcode',status,matches:selected?[selected]:[]},active:true,connection:'live',generation:1,queue:[],mode:'Explore',finished:false,paused:false,streaming:false,saved:null},
   productVisual:{show(){}},document:{documentElement:{dataset:{theme:'light'}}},navigator:{onLine:true},displayValue:(id,value)=>$(id).textContent=value||'—',
   projectedField:()=>null,projectedValue:()=>null,humanValue:String,renderConsumerSummary(){},renderData(){},message:value=>$('lookup-status').textContent=value,detailQueryUnavailable:()=>false,detailFailureText:()=>''};
  vm.createContext(context);vm.runInContext(source.slice(render.start,render.end)+'\nrender();',context);return $;
 }
 test(path+' reports unavailable lookup without implying unidentified classification',()=>{
  const $=draw();assert.equal($('current-barcode').textContent,'4088700055496');assert.equal($('category-value').textContent,'Lookup unavailable');assert.equal($('ingredient-value').textContent,'Lookup unavailable');
 });
 test(path+' keeps known qualified fields during incomplete source coverage',()=>{
  const selected={name:'Authored source name',detail:{canonicalCategory:{status:'qualified',preferredLabel:'Beverage'},canonicalIngredient:{status:'qualified',preferredLabel:'Coffee'}}};
  const $=draw({status:'partial',selected});assert.equal($('product-name').textContent,selected.name);assert.equal($('category-value').textContent,'Beverage');assert.equal($('ingredient-value').textContent,'Coffee');
 });
}
