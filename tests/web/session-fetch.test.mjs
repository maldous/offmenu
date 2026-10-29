import test from 'node:test';
import assert from 'node:assert/strict';
import {sessionFetch} from '../../public/session-fetch.js';
test('account switch during refresh prevents pending write submission',async()=>{
 let identity={owner:'alice'},calls=0;
 const run=sessionFetch({identity:()=>identity,refresh:async()=>{identity={owner:'bob'};},currentUser:async()=>({id:'bob'}),request:async()=>{calls++;}});
 await assert.rejects(run('/api/care/cases',{method:'POST'}),/Account changed/);assert.equal(calls,0);
});
test('identity provider account mismatch prevents submission',async()=>{
 const identity={owner:'alice'};let calls=0;
 const run=sessionFetch({identity:()=>identity,refresh:async()=>{},currentUser:async()=>({id:'bob'}),request:async()=>{calls++;}});
 await assert.rejects(run('/api/care/cases',{method:'POST'}),/Account changed/);assert.equal(calls,0);
});
test('response from previous account is discarded',async()=>{
 let identity={owner:'alice'};
 const run=sessionFetch({identity:()=>identity,refresh:async()=>{},currentUser:async()=>({id:'alice'}),request:async()=>{identity={owner:'bob'};return new Response('{}');}});
 await assert.rejects(run('/api/care/cases'),/Account changed/);
});
test('account switch while a response body is delayed cannot apply old private data',async()=>{
 let identity={owner:'alice'},release;
 const body=new Promise(resolve=>{release=resolve;});
 const run=sessionFetch({identity:()=>identity,refresh:async()=>{},currentUser:async()=>({id:'alice'}),request:async()=>({json:async()=>body})});
 const response=await run('/api/state'),reading=response.json();identity={owner:'bob'};release({state:{private:'alice'}});
 await assert.rejects(reading,/Account changed/);
});
test('guarded Response retains status, headers and clone but refuses body reads after logout',async()=>{
 let identity={owner:'alice'};
 const run=sessionFetch({identity:()=>identity,refresh:async()=>{},currentUser:async()=>({id:'alice'}),request:async()=>Response.json({owner:'alice'})});
 const response=await run('/api/state');assert.equal(response.status,200);assert.match(response.headers.get('Content-Type'),/json/);assert.deepEqual(await response.clone().json(),{owner:'alice'});
 identity={owner:null};await assert.rejects(response.json(),/Account changed/);assert.throws(()=>response.clone(),/Account changed/);
});
