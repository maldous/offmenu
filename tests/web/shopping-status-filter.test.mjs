import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const app=readFileSync(new URL('../../apps/web/src/insights-ui.js',import.meta.url),'utf8');
const html=readFileSync(new URL('../../apps/web/assets/index.html',import.meta.url),'utf8');
const actual=app.slice(app.indexOf('function items(){'),app.indexOf("$('shopping-add-form').onsubmit"));
function fixture(){
  let actor={}, writes=0,date='2026-11-22',usePantry=true;
  const document={activeElement:null};
  class Element{
    constructor(tag){this.tag=tag;this.children=[];this.value='all';}
    append(...children){this.children.push(...children)}
    replaceChildren(){this.children=[];}
    focus(){document.activeElement=this;}
  }
  document.createElement=tag=>new Element(tag);
  const list=new Element('div'),filter=new Element('select'),outside=new Element('button');
  const rows=[{id:'planned',name:'Planned',amount:'2',checked:false}];
  let profile={shopping:[{id:'manual',name:'Manual',amount:'1',checked:true}],shoppingChecked:[]};
  const data=()=>({profile,date,usePantry});
  const shoppingItems=()=>[...rows.map(r=>({...r,checked:profile.shoppingChecked.includes(r.id)})),...profile.shopping];
  const f=vm.runInNewContext(actual+'\n({items,renderShopping})',{
    $:id=>({'shopping-status-filter':filter,'shopping-checklist':list})[id],
    document,data,getIdentity:()=>actor,t:(key,values)=>values?key.replace('{v0}',values.v0):key,
    text:(tag,content)=>Object.assign(new Element(tag),{textContent:content}),
    shoppingItems,persist:()=>writes++,
  });
  const names=()=>list.children.filter(row=>row.tag==='label').map(row=>row.children[1].textContent);
  const select=value=>{filter.value=value;filter.onchange();};
  const check=()=>list.children.find(row=>row.tag==='label').children[0];
  return {...f,document,list,filter,select,check,names,outside,rows,profile,writes:()=>writes,switchActor:()=>{actor={};},replaceProfile:next=>{profile=next;},changeWeek:()=>{date="2026-11-29";},changePantry:()=>{usePantry=false;}};
}
test('labelled shopping filter defaults to All and does not change all-row data',()=>{
  assert.match(html,/<label for="shopping-status-filter"[^>]*>/);
  assert.match(html,/<select id="shopping-status-filter">\s*<option value="all" selected/);
  const f=fixture(); f.renderShopping();
  assert.deepEqual(f.names(),['Planned','Manual']);
  f.select('uncollected');assert.deepEqual(f.names(),['Planned']);
  f.select('collected');assert.deepEqual(f.names(),['Manual']);
  assert.deepEqual(Array.from(f.items(),item=>item.id),['planned','manual']);
  assert.equal(f.writes(),0);
  f.switchActor(); f.renderShopping();
  assert.equal(f.filter.value,'all');assert.deepEqual(f.names(),['Planned','Manual']);
});
test('a filtered toggle keeps focus usable and separates no matches from a truly empty list',()=>{
  const f=fixture();f.renderShopping();f.select('uncollected');
  let check=f.check();check.focus();check.checked=true;check.onchange();
  assert.equal(f.document.activeElement,f.filter);
  assert.equal(f.writes(),1);
  assert.equal(f.list.children[0].textContent,'No uncollected shopping items.');
  f.select('collected');assert.deepEqual(f.names(),['Planned','Manual']);
  check=f.check();f.outside.focus();check.checked=false;check.onchange();
  assert.equal(f.document.activeElement,f.outside);
  assert.deepEqual(f.names(),['Manual']);
  f.rows.length=0;f.profile.shopping.length=0;f.renderShopping();
  assert.equal(f.list.children[0].textContent,'Plan a meal in My week, or add a shopping item below.');
});

const paired=()=>[{id:'left',name:'Same label',amount:'1',checked:false},{id:'right',name:'Same label',amount:'2',checked:false}];
const firstManual=f=>{
 const row=f.list.children.find(node=>node.tag==='label'&&node.children[1].textContent==='Same label');
 return {check:row.children[0],remove:f.list.children[f.list.children.indexOf(row)+1]};
};
for(const boundary of ['actor','profile','rerender'])test('retained Shopping row actions cannot mutate after '+boundary+' changes',()=>{
 const f=fixture(), previous=paired(), replacement={shopping:paired(),shoppingChecked:[]};
 f.profile.shopping=previous;
 f.renderShopping();
 const old=firstManual(f);
 if(boundary==='actor')f.switchActor();
 if(boundary==='profile')f.replaceProfile(replacement);
 if(boundary==='rerender')f.renderShopping();
 old.check.checked=true;
 old.check.onchange();
 old.remove.onclick();
 assert.deepEqual(f.profile.shopping,paired());
 assert.deepEqual(replacement.shopping,paired());
 assert.deepEqual(f.profile.shoppingChecked,[]);
 assert.deepEqual(replacement.shoppingChecked,[]);
 assert.equal(f.writes(),0);
});
test('current Shopping check and remove affect only the selected stable ID when labels match',()=>{
 const f=fixture();
 f.profile.shopping=paired();
 f.renderShopping();
 const first=firstManual(f);
 first.check.checked=true;
 first.check.onchange();
 assert.deepEqual(f.profile.shopping,paired().map(item=>item.id==='left'?{...item,checked:true}:item));
 first.remove.onclick();
 assert.deepEqual(Array.from(f.profile.shopping),[paired()[1]]);
 assert.equal(f.writes(),2);
});

for(const change of ['amount','checked','week','pantry'])test('retained derived Shopping checkbox rejects the same ID after '+change+' changes',()=>{
 const f=fixture();f.renderShopping();
 const old=f.check();
 if(change==='amount')f.rows[0].amount='3';
 if(change==='checked')f.profile.shoppingChecked=['planned'];
 if(change==='week')f.changeWeek();
 if(change==='pantry')f.changePantry();
 const before=[...f.profile.shoppingChecked];
 old.checked=change!=='checked';old.onchange();
 assert.deepEqual(f.profile.shoppingChecked,before);
 assert.equal(f.writes(),0);
});
test('fresh regenerated derived row supports deliberate repeated check and uncheck',()=>{
 const f=fixture();f.renderShopping();f.rows[0].amount='3';f.renderShopping();
 const current=f.check();current.checked=true;current.onchange();
 assert.deepEqual(Array.from(f.profile.shoppingChecked),['planned']);
 current.checked=false;current.onchange();
 assert.deepEqual(Array.from(f.profile.shoppingChecked),[]);
 assert.equal(f.writes(),2);
});
