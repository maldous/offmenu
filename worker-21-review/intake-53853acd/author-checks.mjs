import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createIntakeHistory} from 'data:text/javascript;base64,Ly8gQWNjb3VudC1wcml2YXRlIHBlcnNpc3RlbmNlIGFkYXB0ZXIuIENlbnRyYWwgaGFuZGxlci9zdG9yYWdlIHdpcmluZyBpcyBvd25lcjAyLzAzLgpleHBvcnQgZnVuY3Rpb24gY3JlYXRlSW50YWtlSGlzdG9yeSh7c3RvcmUsIGVudHJ5TW9kZWwsIGF1dGhvcml6ZSwgc291cmNlQWxsb3dlZCwgY2xvY2t9KSB7CiAgaWYgKHR5cGVvZiBzdG9yZT8udHJhbnNhY3Rpb24gIT09ICdmdW5jdGlvbicgfHwgdHlwZW9mIGVudHJ5TW9kZWw/LmNyZWF0ZUludGFrZUVudHJ5ICE9PSAnZnVuY3Rpb24nIHx8CiAgICAgIHR5cGVvZiBlbnRyeU1vZGVsPy5wYXJ0aXRpb25JbnRha2VFbnRyaWVzICE9PSAnZnVuY3Rpb24nIHx8IHR5cGVvZiBhdXRob3JpemUgIT09ICdmdW5jdGlvbicgfHwKICAgICAgdHlwZW9mIHNvdXJjZUFsbG93ZWQgIT09ICdmdW5jdGlvbicgfHwgdHlwZW9mIGNsb2NrICE9PSAnZnVuY3Rpb24nKSB0aHJvdyBFcnJvcignSW50YWtlIGRlcGVuZGVuY2llcyByZXF1aXJlZCcpOwogIGZ1bmN0aW9uIGlkKHZhbHVlKSB7CiAgICBpZiAodHlwZW9mIHZhbHVlICE9PSAnc3RyaW5nJyB8fCAhdmFsdWUudHJpbSgpIHx8IHZhbHVlLmxlbmd0aCA+IDIwMCkgdGhyb3cgRXJyb3IoJ0ludmFsaWQgaW50YWtlIHNjb3BlIElEJyk7CiAgICByZXR1cm4gdmFsdWU7CiAgfQogIGFzeW5jIGZ1bmN0aW9uIGFjY2VzcyhzZXNzaW9uLCBhY2NvdW50SWQsIGFjdGlvbiwgY29uc2VudElkLCBtZW1iZXJJZCkgewogICAgY29uc3QgcmVzdWx0ID0gYXdhaXQgYXV0aG9yaXplKHtzZXNzaW9uLCBhY2NvdW50SWQsIGFjdGlvbiwgY29uc2VudElkLCBtZW1iZXJJZH0pOwogICAgaWYgKHJlc3VsdD8uYWxsb3dlZCAhPT0gdHJ1ZSB8fCByZXN1bHQuYWNjb3VudElkICE9PSBhY2NvdW50SWQpIHRocm93IEVycm9yKCdJbnRha2UgYWNjZXNzIGRlbmllZCcpOwogICAgaWYgKGFjdGlvbiAhPT0gJ3Jldm9rZScgJiYgY29uc2VudElkICYmCiAgICAgICAgKHJlc3VsdC5jb25zZW50Py5pZCAhPT0gY29uc2VudElkIHx8IHJlc3VsdC5jb25zZW50Py5wdXJwb3NlICE9PSAnaW50YWtlLXJlY29yZGluZycgfHwgcmVzdWx0LmNvbnNlbnQ/LmdyYW50ZWQgIT09IHRydWUpKSB7CiAgICAgIHRocm93IEVycm9yKCdDdXJyZW50IGludGFrZSBjb25zZW50IHJlcXVpcmVkJyk7CiAgICB9CiAgICByZXR1cm4gcmVzdWx0OwogIH0KICBhc3luYyBmdW5jdGlvbiBzb3VyY2VzKGVudHJ5LCBhdXRoKSB7CiAgICBjb25zdCByZWZzID0gW2VudHJ5LmZvb2QsIC4uLihlbnRyeS5raW5kID09PSAnc3Vic3RpdHV0aW9uJyA/IFtlbnRyeS5zdWJzdGl0dXRpb24ucGxhbm5lZCwgZW50cnkuc3Vic3RpdHV0aW9uLmFjdHVhbF0gOiBbXSldOwogICAgZm9yIChjb25zdCByZWYgb2YgcmVmcykgewogICAgICBpZiAoYXdhaXQgc291cmNlQWxsb3dlZChzdHJ1Y3R1cmVkQ2xvbmUocmVmKSwgc3RydWN0dXJlZENsb25lKGF1dGgpKSAhPT0gdHJ1ZSkgcmV0dXJuIGZhbHNlOwogICAgfQogICAgcmV0dXJuIHRydWU7CiAgfQogIGZ1bmN0aW9uIHN0YXRlKHZhbHVlKSB7CiAgICBjb25zdCByZXN1bHQgPSB2YWx1ZSA9PSBudWxsID8ge3ZlcnNpb246IDEsIGVudHJpZXM6IFtdLCByZXZva2VkQ29uc2VudElkczogW119IDogc3RydWN0dXJlZENsb25lKHZhbHVlKTsKICAgIGlmIChyZXN1bHQudmVyc2lvbiAhPT0gMSB8fCAhQXJyYXkuaXNBcnJheShyZXN1bHQuZW50cmllcykgfHwgcmVzdWx0LmVudHJpZXMubGVuZ3RoID4gMTAwMCB8fAogICAgICAgICFBcnJheS5pc0FycmF5KHJlc3VsdC5yZXZva2VkQ29uc2VudElkcykgfHwgcmVzdWx0LnJldm9rZWRDb25zZW50SWRzLmxlbmd0aCA+IDEwMDApIHRocm93IEVycm9yKCdJbnZhbGlkIGludGFrZSBzdG9yZScpOwogICAgcmVzdWx0LnJldm9rZWRDb25zZW50SWRzLmZvckVhY2goaWQpOwogICAgcmV0dXJuIHJlc3VsdDsKICB9CiAgcmV0dXJuIHsKICAgIGFzeW5jIGFwcGVuZCh7c2Vzc2lvbiwgYWNjb3VudElkLCBpbnB1dH0pIHsKICAgICAgaWQoYWNjb3VudElkKTsKICAgICAgLy8gQ2FwdHVyZSByZXF1ZXN0IGJlZm9yZSBhd2FpdHM7IGFjY291bnQvY29uc2VudCBhcmUgcmVzb2x2ZWQgYnkgdHJ1c3RlZCBhdXRoLgogICAgICBjb25zdCBkcmFmdCA9IHN0cnVjdHVyZWRDbG9uZShpbnB1dCk7CiAgICAgIGlmIChkcmFmdC5hY2NvdW50SWQgIT09IGFjY291bnRJZCkgdGhyb3cgRXJyb3IoJ0ludGFrZSBhY2NvdW50IG1pc21hdGNoJyk7CiAgICAgIGlkKGRyYWZ0LmNvbnNlbnQ/LmlkKTsKICAgICAgcmV0dXJuIHN0b3JlLnRyYW5zYWN0aW9uKGFjY291bnRJZCwgYXN5bmMgY3VycmVudCA9PiB7CiAgICAgICAgY29uc3QgbmV4dCA9IHN0YXRlKGN1cnJlbnQpOwogICAgICAgIGNvbnN0IGF1dGggPSBhd2FpdCBhY2Nlc3Moc2Vzc2lvbiwgYWNjb3VudElkLCAnYXBwZW5kJywgZHJhZnQuY29uc2VudC5pZCwgZHJhZnQubWVtYmVySWQpOwogICAgICAgIGlmIChuZXh0LnJldm9rZWRDb25zZW50SWRzLmluY2x1ZGVzKGRyYWZ0LmNvbnNlbnQuaWQpKSB0aHJvdyBFcnJvcignSW50YWtlIGNvbnNlbnQgcmV2b2tlZCcpOwogICAgICAgIGNvbnN0IGVudHJ5ID0gZW50cnlNb2RlbC5jcmVhdGVJbnRha2VFbnRyeSh7Li4uZHJhZnQsIGFjY291bnRJZCwgY29uc2VudDogYXV0aC5jb25zZW50fSwge2FjY291bnRJZCwgY2xvY2t9KTsKICAgICAgICBpZiAoIWF3YWl0IHNvdXJjZXMoZW50cnksIGF1dGgpKSB0aHJvdyBFcnJvcignSW50YWtlIHNvdXJjZSBwZXJtaXNzaW9uIHJlcXVpcmVkJyk7CiAgICAgICAgaWYgKG5leHQuZW50cmllcy5zb21lKGUgPT4gZS5pZCA9PT0gZW50cnkuaWQpKSB0aHJvdyBFcnJvcignRHVwbGljYXRlIGludGFrZSBldmVudCcpOwogICAgICAgIGlmIChuZXh0LmVudHJpZXMubGVuZ3RoID49IDEwMDApIHRocm93IEVycm9yKCdJbnRha2UgaGlzdG9yeSBmdWxsJyk7CiAgICAgICAgbmV4dC5lbnRyaWVzLnB1c2goZW50cnkpOwogICAgICAgIHJldHVybiB7c3RhdGU6IG5leHQsIHJlc3VsdDogc3RydWN0dXJlZENsb25lKGVudHJ5KX07CiAgICAgIH0pOwogICAgfSwKICAgIGFzeW5jIHJlYWQoe3Nlc3Npb24sIGFjY291bnRJZH0pIHsKICAgICAgaWQoYWNjb3VudElkKTsKICAgICAgcmV0dXJuIHN0b3JlLnRyYW5zYWN0aW9uKGFjY291bnRJZCwgYXN5bmMgY3VycmVudCA9PiB7CiAgICAgICAgYXdhaXQgYWNjZXNzKHNlc3Npb24sIGFjY291bnRJZCwgJ3JlYWQnKTsKICAgICAgICBjb25zdCBuZXh0ID0gc3RhdGUoY3VycmVudCksIHZpc2libGUgPSBbXTsKICAgICAgICAvLyBWYWxpZGF0ZSBhbGwgcmVjb3JkcyBiZWZvcmUgc2VsZWN0aW5nOyBuZXZlciBzaWxlbnRseSBkcm9wIGZvcmVpZ24gZGF0YS4KICAgICAgICBpZiAobmV4dC5lbnRyaWVzLnNvbWUoZSA9PiBlLmFjY291bnRJZCAhPT0gYWNjb3VudElkKSkgdGhyb3cgRXJyb3IoJ0ZvcmVpZ24gaW50YWtlIHJlY29yZCBpbiBhY2NvdW50IHN0b3JlJyk7CiAgICAgICAgZW50cnlNb2RlbC5wYXJ0aXRpb25JbnRha2VFbnRyaWVzKG5leHQuZW50cmllcywge2FjY291bnRJZH0pOwogICAgICAgIGZvciAoY29uc3QgZW50cnkgb2YgbmV4dC5lbnRyaWVzKSB7CiAgICAgICAgICBpZiAobmV4dC5yZXZva2VkQ29uc2VudElkcy5pbmNsdWRlcyhlbnRyeS5jb25zZW50LmlkKSkgY29udGludWU7CiAgICAgICAgICBjb25zdCBhdXRoID0gYXdhaXQgYWNjZXNzKHNlc3Npb24sIGFjY291bnRJZCwgJ3JlYWQnLCBlbnRyeS5jb25zZW50LmlkLCBlbnRyeS5tZW1iZXJJZCk7CiAgICAgICAgICBpZiAoYXdhaXQgc291cmNlcyhlbnRyeSwgYXV0aCkpIHZpc2libGUucHVzaChlbnRyeSk7CiAgICAgICAgfQogICAgICAgIHJldHVybiB7c3RhdGU6IG5leHQsIHJlc3VsdDogZW50cnlNb2RlbC5wYXJ0aXRpb25JbnRha2VFbnRyaWVzKHZpc2libGUsIHthY2NvdW50SWR9KX07CiAgICAgIH0pOwogICAgfSwKICAgIGFzeW5jIHJldm9rZSh7c2Vzc2lvbiwgYWNjb3VudElkLCBjb25zZW50SWR9KSB7CiAgICAgIGlkKGFjY291bnRJZCk7IGlkKGNvbnNlbnRJZCk7CiAgICAgIHJldHVybiBzdG9yZS50cmFuc2FjdGlvbihhY2NvdW50SWQsIGFzeW5jIGN1cnJlbnQgPT4gewogICAgICAgIGF3YWl0IGFjY2VzcyhzZXNzaW9uLCBhY2NvdW50SWQsICdyZXZva2UnLCBjb25zZW50SWQpOwogICAgICAgIGNvbnN0IG5leHQgPSBzdGF0ZShjdXJyZW50KTsKICAgICAgICBpZiAoIW5leHQucmV2b2tlZENvbnNlbnRJZHMuaW5jbHVkZXMoY29uc2VudElkKSkgewogICAgICAgICAgaWYgKG5leHQucmV2b2tlZENvbnNlbnRJZHMubGVuZ3RoID49IDEwMDApIHRocm93IEVycm9yKCdSZXZvY2F0aW9uIGxlZGdlciBmdWxsJyk7CiAgICAgICAgICBuZXh0LnJldm9rZWRDb25zZW50SWRzLnB1c2goY29uc2VudElkKTsKICAgICAgICB9CiAgICAgICAgY29uc3Qgb2xkTGVuZ3RoID0gbmV4dC5lbnRyaWVzLmxlbmd0aDsKICAgICAgICBuZXh0LmVudHJpZXMgPSBuZXh0LmVudHJpZXMuZmlsdGVyKGUgPT4gZS5jb25zZW50LmlkICE9PSBjb25zZW50SWQpOwogICAgICAgIHJldHVybiB7c3RhdGU6IG5leHQsIHJlc3VsdDoge3JlbW92ZWQ6IG9sZExlbmd0aCAtIG5leHQuZW50cmllcy5sZW5ndGh9fTsKICAgICAgfSk7CiAgICB9LAogIH07Cn0K';
import {validateState} from 'file:///home/user/src/offmenu-workers/worker-21/cloud/state.mjs';
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
