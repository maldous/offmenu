import test from 'node:test';
import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
import vm from 'node:vm';

test('deferred lookup reconciles once on visible return or native dialog close, preserving newer input and review',async()=>{
 const source=readFileSync(new URL('../../apps/web/src/app.js',import.meta.url),'utf8');
 const isolate=(a,b)=>source.slice(source.indexOf(a),source.indexOf(b,source.indexOf(a)));
 const messaging=isolate('let scannerMessageRevision=0','function canEditCheckout');
 const apply=isolate('function autoAccept(','async function lookup(');
 const display=isolate('function displayAccepted(','$(\'lookup\').onclick');
 const setView=isolate('function setView(','function openWorkspace(');
 const close=source.split('\n').find(line=>line.startsWith("document.addEventListener('close',"));
 const scopeChange=source.match(/onScopeChange:\(\)=>\{(scannerMessageRevision\+\+;settledLookupAnnouncement=null;)/)[1];
 for(const scenario of ['visible','away','receipt','account','still-modal','input','error','new-item','editing','review-dismissed','void','scope','ended']){
  class HTMLDialogElement {}
  const nodes=new Map(),el=id=>{if(!nodes.has(id))nodes.set(id,Object.assign(id.endsWith('-dialog')?new HTMLDialogElement():{},
   {hidden:false,open:false,value:'',addEventListener(event,cb){this[event]=cb}}));return nodes.get(id)};
  let closeEvent;
  const closeDialog=id=>{el(id).open=false;closeEvent({target:el(id)});};
  let release, speech=0;const deferred=new Promise(r=>release=r),current={items:[],mode:'shelf'};
  let seq=0;
  const context={$:el,KEY:'fictional',requestIdentity:{},editingId:null,session:current,
   // Today heading focus is scheduled by the surrounding UI and covered in Chromium.
   requestAnimationFrame:()=>1,
   HTMLDialogElement,document:{
    querySelector(){return [...nodes.values()].find(n=>n instanceof HTMLDialogElement&&n.open)||null},
    querySelectorAll(){return []},
    addEventListener(type,cb,capture){assert.equal(type,'close');assert.equal(capture,true);closeEvent=cb},
   },
   canEditCheckout:()=>true,scannerScopeMatches:()=>true,scannerHandoffOperations:[],scannerHandoffReceipts:{},
   makeAutoLot:(code,p)=>({id:String(++seq),barcode:code,name:p?.name||'Pending'}),mappedIngredient:()=>null,trustedIngredient:()=>false,
   saveDraft:()=>{},renderBasket:()=>{},scanFeedback:()=>{},getProduct:()=>deferred,t:x=>x,feedback:{speech:true},
   setLocalizedText(node,text){node.textContent=text},showLocalized(node,text){node.textContent=text},
   localizedLotName:lot=>lot.name,products:{},foodIcon:()=>'',renderNutrition:()=>{},pulseRegister:()=>{},
   renderFinalReceipt:()=>{},speakProduct:()=>speech++,stop:()=>{},findMeals:()=>{},
  };
  const api=vm.runInNewContext([messaging,apply,display,setView,close,'({autoAccept,msg,setView})'].join('\n'),context);
  api.autoAccept('0001');const pending=el('message').textContent;
  assert.equal(el('barcode').value,'0001','real displayAccepted wrote original code');
  if(scenario==='away')api.setView('meals');
  if(scenario==='receipt')el('finish-dialog').open=true;
  if(scenario==='account'||scenario==='still-modal')el('account-dialog').open=true;
  if(scenario==='still-modal')el('care-dialog').open=true;
  if(scenario==='input'){el('barcode').value='0123'; el('barcode').input();}
  if(scenario==='error')api.msg('New error');
  if(scenario==='new-item')api.autoAccept('0002',{name:'New review'});
  if(scenario==='editing'){context.editingId='fictional edit';el('product-heading').textContent='User review';}
  if(scenario==='review-dismissed')el('item-review').hidden=true;
  if(scenario==='void'){current.items.pop();api.msg('Voided');}
  if(scenario==='scope')vm.runInNewContext(scopeChange,context);
  if(scenario==='ended')context.session=null;
  const expectedCode=el('barcode').value,expectedReview=el('product-heading').textContent,expectedMessage=el('message').textContent;
  release({name:'Synthetic settled item'});await Promise.resolve();await Promise.resolve();
  assert.equal(el('barcode').value,expectedCode,scenario);
  assert.equal(el('message').textContent,scenario==='visible'?'Accepted. Next item, please.':expectedMessage,scenario);
  assert.equal(speech,scenario==='visible'?1:0,scenario);
  if(!['visible'].includes(scenario))assert.equal(el('product-heading').textContent,expectedReview,scenario);
  if(['away','receipt','account','still-modal'].includes(scenario)){
   assert.equal(el('message').textContent,pending);
   if(scenario==='away')api.setView('checkout');
   else{
    closeEvent({target:el('barcode')});
    assert.equal(el('message').textContent,pending,'non-dialog close cannot consume completion');
    closeDialog(scenario==='receipt'?'finish-dialog':'account-dialog');
    if(scenario==='still-modal'){assert.equal(el('message').textContent,pending);closeDialog('care-dialog');}
   }
   assert.equal(el('message').textContent,'Accepted. Next item, please.');
   assert.equal(el('product-heading').textContent,'Synthetic settled item');
   assert.equal(speech,0);
   api.msg('A later status');api.setView('checkout');
   assert.equal(el('message').textContent,'A later status');
  }
  if(scenario==='void')assert.equal(current.items.length,0);
 }
});
