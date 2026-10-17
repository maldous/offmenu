import test from 'node:test';
import assert from 'node:assert/strict';
import {sessionFetch} from '../public/session-fetch.js';
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
