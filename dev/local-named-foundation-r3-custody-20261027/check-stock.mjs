import fs from 'node:fs';import path from 'node:path';import vm from 'node:vm';import assert from 'node:assert/strict';import{webcrypto}from'node:crypto';
import * as foundation from './compact-composition-r3/consumer/foundation-scanner-handoff.mjs';
const R=path.join(import.meta.dirname,'compact-composition-r3'),P=path.dirname(import.meta.dirname),SOURCE=path.join(P,'local7645-foundation-root14-r1/confirmed-handoff-r1');
const context=vm.createContext({crypto:webcrypto,TextEncoder,URL,Date}),modules=new Map();
async function synthetic(name,exports){const mod=new vm.SyntheticModule(Object.keys(exports),function(){for(const[k,v]of Object.entries(exports))this.setExport(k,v);},{context});modules.set(name,mod);}
await synthetic('./foundation-scanner-handoff.mjs',foundation);
await synthetic('./i18n.js',{t:x=>x});await synthetic('./ingredients.js',{canonicalIngredient:x=>String(x).trim().toLowerCase(),measuredIngredient:()=>false});
await synthetic('./scanner-identity-v2.js',{validSourceObservationReference:()=>false});await synthetic('./typed-identifier-contract.mjs',{analyzeIdentifier:()=>({status:'unresolved',labelledEquivalents:[]})});
async function load(name){if(modules.has(name))return modules.get(name);const mod=new vm.SourceTextModule(fs.readFileSync(path.join(SOURCE,name),'utf8'),{context});modules.set(name,mod);await mod.link(load);return mod;}
const legacy=await load('./scanner-kitchen-handoff.js');await legacy.evaluate();const model=await load('./model.js');await model.evaluate();const checkout=await load('./checkout-model.js');await checkout.evaluate();
const id='00000000-0000-4000-8000-000000000001',plain=x=>JSON.parse(JSON.stringify(x)),refs=[];
refs.push(JSON.parse(fs.readFileSync(path.join(R,'response-off-4061464939738.json'))).records[0].foundationSourceReference);
for(const source of['off','usda-files'])refs.push(JSON.parse(fs.readFileSync(path.join(SOURCE,'reference-example-'+source+'.json'))).records[0].foundationSourceReference);
for(const ref of refs){
 const draft=checkout.namespace.makeAutoLot(ref.lexicalValue,{name:'Explicit manual stock',foundationSourceReference:ref},'unmapped');draft.id=id;
 assert.equal(draft.quantity,null);assert.throws(()=>model.namespace.validateLot(draft));
 const lot=model.namespace.validateLot({...draft,quantity:250,unit:'g',amountBasis:'manual',ingredient:'explicit-manual-food',needsReview:false});
 assert.deepEqual(plain(model.namespace.validateLot(JSON.parse(JSON.stringify(lot))).foundationSourceReference),ref);
 const session={mode:'shopping',area:'Pantry',shelf:'Top',items:[lot],startedAt:'2026-10-27T00:00:00Z',scannerCompletion:{schema:legacy.namespace.SCANNER_COMPLETION}};
 const stock=checkout.namespace.finishInventory([],session);assert.deepEqual(plain(stock[0].foundationSourceReference),ref);assert.equal(checkout.namespace.finishInventory(stock,session),stock);
 assert.throws(()=>checkout.namespace.finishInventory(stock,{...session,items:[{...lot,quantity:251}]}));
 const item={operationId:id,barcode:ref.lexicalValue,namespace:'barcode',symbology:null,name:'Explicit manual stock',brand:null,userSelected:true,foundationSourceReference:ref},fp=foundation.foundationHandoffFingerprint(item);
 assert.equal(legacy.namespace.validateScannerHandoffReceipts({[id]:fp},[id])[id],fp);
 assert.equal(foundation.validFoundationSourceReference({...ref,manifestSha256:'0'.repeat(64)},ref.lexicalValue),false);
}
const result={atUTC:new Date().toISOString(),status:'PASS_ACTUAL_UNCHANGED_MODEL_RECEIPT_CHECKOUT_WITH_NEW_AND_RETAINED_PUBLIC_REFS',testedReferences:3,newNamedReference:1,retainedOldReferences:2,manualPositiveAmountRequired:true,unknownRefused:true,JSONRoundtripPreserved:true,receiptFingerprintPreserved:true,replayPreserved:true,differentAmountRefused:true,unknownCutRefused:true,effects:'VM of actual unchanged functions, generated manual stock and alreadyqualified public source references only; no userprofile/account/state DB/network/currentapp/runtime.'};
fs.writeFileSync(path.join(R,'stock-reference-compatibility-check-result.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(result));
