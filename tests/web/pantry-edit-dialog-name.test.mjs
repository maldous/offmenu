import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import vm from 'node:vm';
const app=readFileSync(new URL('../../apps/web/src/app.js',import.meta.url),'utf8');
const start=app.indexOf('function editInventoryLot('),end=app.indexOf('function pantry()',start);
assert.ok(start>=0&&end>start);
function fixture(){
 const nodes=new Map(),opens=[],writes=[],renders=[];
 const first={id:'first',name:'First',ingredient:'rice',quantity:10,unit:'g',location:{area:'Pantry',shelf:'Top'}};
 const second={...first,id:'second',name:'Second'};
 const document={body:{append(dialog){
  nodes.set(dialog.id,dialog);
  for(const m of dialog.innerHTML.matchAll(/<([a-z0-9]+)\b[^>]*\bid="([^"]+)"[^>]*>([^<]*)/g)){
   assert.ok(!nodes.has(m[2]),'duplicate lazy element id: '+m[2]);
   nodes.set(m[2],{tag:m[1],textContent:m[3]});
  }
  nodes.get('inventory-edit-form').elements=Object.fromEntries([...dialog.innerHTML.matchAll(/\bname="([^"]+)"/g)].map(m=>[m[1],{}]));
 }},createElement(tag){
  assert.equal(tag,'dialog');
  return {attrs:new Map(),setAttribute(k,v){this.attrs.set(k,v);},showModal(){this.open=true;opens.push(this);},close(){this.open=false;}};
 }};
 const c=vm.createContext({document,$:id=>nodes.get(id),lots:[first,second],canEditCheckout:()=>true,validateLot:x=>x,
  save:rows=>writes.push(JSON.parse(JSON.stringify(rows))),pantry:()=>renders.push('pantry'),findMeals:()=>renders.push('meals')});
 vm.runInContext(app.slice(start,end),c);
 return {nodes,opens,writes,renders,first,second,open:c.editInventoryLot};
}
test('lazy Pantry edit dialog has one stable visible heading association on first open and reuse',()=>{
 const f=fixture();assert.equal(f.nodes.size,0);
 f.open(f.first);
 const dialog=f.nodes.get('inventory-edit-dialog'),id=dialog.attrs.get('aria-labelledby');
 assert.equal(id,'inventory-edit-title');
 const title=f.nodes.get(id);assert.equal(title.tag,'h2');assert.equal(title.textContent,'Edit pantry item');
 f.nodes.get('inventory-edit-cancel').onclick();f.open(f.second);
 assert.deepEqual(f.opens,[dialog,dialog]);assert.equal(f.nodes.get(id),title);
 assert.equal(dialog.attrs.get('aria-labelledby'),id);
});
test('cancel writes nothing and a later submit updates only the selected lot',()=>{
 const f=fixture();f.open(f.first);
 const dialog=f.nodes.get('inventory-edit-dialog'),form=f.nodes.get('inventory-edit-form');
 f.nodes.get('inventory-edit-cancel').onclick();assert.equal(dialog.open,false);assert.deepEqual(f.writes,[]);
 f.open(f.second);assert.equal(form.elements.name.value,'Second');form.elements.quantity.value='14';
 let prevented=false;form.onsubmit({preventDefault(){prevented=true;}});
 assert.ok(prevented);assert.equal(dialog.open,false);
 assert.deepEqual(f.writes,[[f.first,{...f.second,quantity:14,expires:null,amountBasis:'manual',needsReview:false}]]);
 assert.deepEqual(f.renders,['pantry','meals']);
});
