import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createIntakeHistory} from '../cloud/intake-history-owner25.mjs';
import {validateState} from '../cloud/state.mjs';
const pin = '59d8bca52cc3281741862d17f2579668d6e6140d';
const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('GIT_')));
const source = execFileSync('git', ['show', `${pin}:public/intake-entry-model.js`], {env, encoding: 'utf8'});
const entryModel = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
const consent = {id:'c1',purpose:'intake-recording',granted:true};
const input = (id, state='unknown-consumed') => ({id,accountId:'a',memberId:'m',date:'2026-10-14',kind:'restaurant',state,
  quantity:{value:state==='unknown-consumed'?null:20,unit:'g'},consent,
  food:{id:'dish',label:'Synthetic dish',source:{id:'manual',recordId:'dish-1',rights:'unknown'}}});
function fixture() {
  const db = new Map(); let tail = Promise.resolve(); let permitted = true, granted = true;
  const store = {transaction(account, fn) {
    const work = tail.then(async () => {
      const {state,result} = await fn(structuredClone(db.get(account)));
      db.set(account, structuredClone(state)); return structuredClone(result);
    }); tail = work.catch(()=>{}); return work;
  }};
  const api = createIntakeHistory({store,entryModel,clock:()=> '2026-10-14T10:00:00.000Z',
    authorize:async ({session,accountId,action,consentId,memberId}) => ({allowed:session==='verified' && accountId==='a' && (!memberId||memberId==='m'),accountId,
      consent:{...consent,id:consentId||'c1',granted:action==='revoke'?false:granted}}),
    sourceAllowed:async()=>permitted});
  return {api,db,permission:v=>permitted=v,consent:v=>granted=v};
}
test('actual state entrypoint drops typed history: owner integration is still required',()=>{
  const state=validateState({inventory:[],profile:{servings:1,intakeHistory:{version:1,entries:[input('x')]}}});
  assert.equal(state.profile.intakeHistory,undefined);
});
test('adapter persists and reloads lineage, plans and unknown amounts distinctly',async()=>{
  const {api,db}=fixture();
  for(const state of ['planned','consumed','unknown-consumed']) await api.append({session:'verified',accountId:'a',input:input(state,state)});
  const buckets=await api.read({session:'verified',accountId:'a'});
  assert.equal(buckets.unknownConsumed[0].quantity.value,null); assert.equal(buckets.consumed[0].quantity.value,20);
  assert.equal(buckets.planned.length,1);assert.deepEqual(buckets.unknownConsumed[0].food,input('x').food);
  buckets.consumed[0].food.label='changed';assert.equal(db.get('a').entries[1].food.label,'Synthetic dish');
});
test('forged account, member, consent and unverified session cannot persist or read',async()=>{
  const {api,db,consent:withdraw}=fixture();
  await assert.rejects(api.append({session:'unverified',accountId:'a',input:input('x')}));
  await assert.rejects(api.append({session:'verified',accountId:'a',input:{...input('x'),accountId:'b'}}));
  await assert.rejects(api.append({session:'verified',accountId:'a',input:{...input('x'),memberId:'other'}}));
  withdraw(false);await assert.rejects(api.append({session:'verified',accountId:'a',input:input('x')}));
  await assert.rejects(api.read({session:'unverified',accountId:'a'}));assert.equal(db.size,0);
});
test('revocation deletes matching private history and tombstone prevents reintroduction',async()=>{
  const {api,db}=fixture();await api.append({session:'verified',accountId:'a',input:input('x')});
  assert.equal((await api.revoke({session:'verified',accountId:'a',consentId:'c1'})).removed,1);
  assert.equal(db.get('a').entries.length,0);
  await assert.rejects(api.append({session:'verified',accountId:'a',input:input('x')}));
  assert.equal((await api.revoke({session:'verified',accountId:'a',consentId:'c1'})).removed,0);
});
test('source permission is checked on writes and reads, not inferred from rights text',async()=>{
  const {api,permission}=fixture();permission(false);
  await assert.rejects(api.append({session:'verified',accountId:'a',input:input('x')}));
  permission(true);await api.append({session:'verified',accountId:'a',input:input('x')});permission(false);
  assert.equal((await api.read({session:'verified',accountId:'a'})).unknownConsumed.length,0);
});
test('linearizable store serializes duplicate events with no lost update',async()=>{
  const {api,db}=fixture();const results=await Promise.allSettled([1,2].map(()=>api.append({session:'verified',accountId:'a',input:input('same')})));
  assert.equal(results.filter(r=>r.status==='fulfilled').length,1);assert.equal(db.get('a').entries.length,1);
});
