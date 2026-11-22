import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
import {NUTRIENTS,planSummary,weekDates} from '../../apps/web/src/menu-model.js';

const source=readFileSync(new URL('../../apps/web/src/app.js',import.meta.url),'utf8');
const html=readFileSync(new URL('../../apps/web/assets/index.html',import.meta.url),'utf8');
const start=source.indexOf('function renderPlan(){');
const end=source.indexOf("\n$('plan-date').value=today();",start);
assert.ok(start>=0&&end>start,'load actual Plan renderer');
const binding=source.split('\n').find(line=>line.startsWith("$('plan-date').value=today();"));
const clickStart=binding.indexOf("for(const period of ['daily','weekly'])");
assert.ok(clickStart>=0,'load actual nutrition range bindings');
const initial=/\blet statisticsPeriod='(daily|weekly)'/.exec(source)?.[1];
assert.equal(initial,'daily');

test('Plan exposes the active nutrition range while the existing totals and focus remain intact',()=>{
 const nodes=new Map(), document={createElement:node,activeElement:null};
 let focusMoves=0,writes=0,dirty=0;
 function node(tag){
  const el={tag,children:[],textContent:'',attributes:new Map(),
   classList:{toggle(name,enabled){
    const classes=new Set((el.getAttribute('class')||'').split(/\s+/).filter(Boolean));
    if(enabled)classes.add(name);else classes.delete(name);
    el.setAttribute('class',[...classes].join(' '));
   }},
   append(...items){el.children.push(...items);},replaceChildren(...items){el.children=items;},
   setAttribute(name,value){el.attributes.set(name,String(value));},
   getAttribute(name){return el.attributes.get(name)??null;},
   focus(){focusMoves++;document.activeElement=el;}
  };
  return el;
 }
 const $=id=>{
  if(!nodes.has(id))nodes.set(id,node('div'));
  return nodes.get(id);
 };
 for(const period of ['daily','weekly']){
  const id='stats-'+period;
  const markup=new RegExp('<button([^>]*\\bid="'+id+'"[^>]*)>([^<]*)<\\/button>').exec(html);
  assert.ok(markup,id);
  const button=node('button');
  for(const [,k,v] of markup[1].matchAll(/([a-z-]+)="([^"]*)"/g))button.setAttribute(k,v);
  button.textContent=markup[2]; nodes.set(id,button);
 }
 $('stats-heading').textContent='Daily totals';
 $('plan-date').value='2026-11-25'; $('use-pantry').checked=true;
 const profile={units:'metric',plan:[
  {id:'today',date:'2026-11-25',recipeId:'recipe',slot:'Dinner',servings:2},
  {id:'tomorrow',date:'2026-11-26',recipeId:'recipe',slot:'Dinner',servings:3},
  {id:'next-week',date:'2026-12-02',recipeId:'recipe',slot:'Dinner',servings:8}
 ]};
 const recipes=[{id:'recipe',title:'Fixture recipe',servings:1,ingredients:[{ingredient:'rice',quantity:50,unit:'g'}]}];
 const lots=[{id:'fixture',barcode:'fixture',ingredient:'rice',quantity:300,unit:'g'}];
 const products={fixture:{nutrition_data_per:'100g',nutriments:{'energy-kcal_100g':120}}};
 const t=(message,values={})=>String(message).replace(/\{(v\d+)\}/g,(old,key)=>values[key]??old);
 const context=vm.createContext({$,document,profile,recipes,lots,products,weekDates,planSummary,NUTRIENTS,t,
  today:()=> '2026-11-25',getLanguage:()=> 'en-AU',requestIdentity:{owner:null},PROFILE:'fixture',planScopeEpoch:1,
  setLocalizedText:(el,message,values)=>{el.textContent=t(message,values);},
  showLocalized:(el,result)=>{el.textContent=result.value;},localizedField:(item,key)=>({value:item[key]}),
  displayAmount:(amount,unit)=>amount+' '+unit,renderUnlocks(){},markDirty(){dirty++;},
  localStorage:{setItem(){writes++;},removeItem(){writes++;},clear(){writes++;}},
 });
 vm.runInContext("let statisticsPeriod='"+initial+"';\n"+source.slice(start,end)+'\n'+binding.slice(clickStart),context);
 const buttons=[$('stats-daily'),$('stats-weekly')],pressed=[];
 const stats=label=>$('plan-statistics').children.find(n=>n.children[1].textContent===label)?.children[0].textContent;
 const stockBefore=JSON.stringify({profile,lots,products});
 function observe(focused,period,meals,portions,energy,heading){
  assert.equal(document.activeElement,focused,'focus remains on the activated control in the test DOM');
  assert.deepEqual(buttons.map(n=>n.textContent),['Selected day','Whole week']);
  assert.deepEqual(buttons.map(n=>(n.getAttribute('class')||'').split(/\s+/).includes('selected')),
    period==='daily'?[true,false]:[false,true]);
  assert.equal($('stats-heading').textContent,heading);
  assert.deepEqual(['Planned meals','Planned portions','Energy'].map(stats),[meals,portions,energy]);
  assert.equal($('week-menu').children.length,7);
  assert.equal($('plan-date').value,'2026-11-25');
  pressed.push(buttons.map(n=>n.getAttribute('aria-pressed')));
 }
 context.renderPlan();
 observe(null,'daily','1','2','120 kcal','Daily totals · 2026-11-25');
 document.activeElement=buttons[1]; buttons[1].onclick();
 observe(buttons[1],'weekly','2','5','300 kcal','Weekly totals · 2026-11-23 to 2026-11-29');
 document.activeElement=buttons[0]; buttons[0].onclick();
 observe(buttons[0],'daily','1','2','120 kcal','Daily totals · 2026-11-25');
 assert.equal(focusMoves,0);
 assert.equal(writes,0); assert.equal(dirty,0);
 assert.equal(JSON.stringify({profile,lots,products}),stockBefore);
 assert.deepEqual(pressed,[['true','false'],['false','true'],['true','false']],
  'initial selected day, whole week, and return to selected day must expose pressed state');
});
