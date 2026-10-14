import test from 'node:test';
import assert from 'node:assert/strict';
import {createPrivateCollections} from '../public/private-collections-owner25.mjs';
import {kitchenProjection} from '../public/sync-model.js';
const reference={sourceId:'manual-source',recipeId:'recipe-one',version:'v1',rightsVersion:'policy1',sourceUrl:'https://example.test/recipe'};
function fixture() {
  let state={version:1,accountId:'a',revision:0,collections:[]},live=true,sourceStatus='available',copyAllowed=true,authBarrier,commitBarrier,lost=false,afterLoad,resolverPatch={},afterResolve,beforeAuth,commitNull=false;
  const auth={allowed:true,accountId:'a',sessionId:'session',epoch:1,realm:'realm',resource:'/private-collections',consent:{id:'consent',revision:1,granted:true,purpose:'private-recipe-collections'}};
  const resolved=()=>({status:sourceStatus,reference,provenance:{sourceId:reference.sourceId,license:'explicit-unknown',rightsVersion:'policy1'},privateCopyAllowed:copyAllowed,
    privateCopy:{accountId:'a',review:{id:'review1',status:'personally-reviewed',sourceId:'manual-source',rightsVersion:'policy1',sourceRecipeId:'recipe-one',sourceVersion:'v1'},recipe:{title:'Family recipe',ingredients:[],instructions:['Private note']}},...resolverPatch});
  const api=createPrivateCollections({authorize:async session=>{if(authBarrier)await authBarrier;if(beforeAuth){const fn=beforeAuth;beforeAuth=null;fn();}if(session!=='verified'||!live)return {...auth,allowed:false};return structuredClone(auth);},
    authorizeRelease:async(session,{binding,sources})=>({allowed:session==='verified'&&live&&sources.every(s=>!s.privateCopyIncluded||(sourceStatus==='available'&&copyAllowed)),binding}),
    load:async()=>{if(afterLoad)afterLoad();return structuredClone(state);},resolveRecipe:async()=>{const result=resolved();if(afterResolve)beforeAuth=afterResolve;return result;},clock:()=> '2026-10-15T00:00:00Z',
    commit:async request=>{
      if(commitBarrier)await commitBarrier;
      if(!live||request.binding.accountId!=='a')throw Error('Atomic admission denied');
      if(request.expectedVersion!==state.revision)return {status:'conflict'};
      state={...structuredClone(request.state),revision:state.revision+1};
      if(commitNull)return null;
      if(lost)throw Error('Lost acknowledgment');
      return {status:'committed',acknowledged:true,operationId:request.operationId,revision:state.revision,binding:request.binding};
    }});
  let seq=0;
  const mutate=(type,extra={})=>api.mutate({session:'verified',accountId:'a',command:{type,operationId:'op'+(++seq),expectedVersion:state.revision,collectionId:'family',...extra}});
  return {api,mutate,state:()=>structuredClone(state),revoke:()=>live=false,status:v=>sourceStatus=v,copy:v=>copyAllowed=v,authWait:p=>authBarrier=p,commitWait:p=>commitBarrier=p,lose:()=>lost=true,afterLoad:f=>afterLoad=f,restore:s=>state=structuredClone(s),patch:p=>resolverPatch=p,afterResolve:f=>afterResolve=f,nullAck:()=>commitNull=true};
}
test('exported consumer add/bookmark/rename/unbookmark/remove/reset with revision receipts',async()=>{
  const f=fixture();assert.equal((await f.mutate('add',{name:'Family'})).revision,1);
  await f.mutate('bookmark',{bookmarkId:'b1',reference});await f.mutate('rename',{name:'Weekends'});
  let read=await f.api.read({session:'verified',accountId:'a'});assert.equal(read.collections[0].name,'Weekends');assert.deepEqual(read.collections[0].bookmarks[0].reference,reference);
  assert.equal(read.collections[0].bookmarks[0].privateCopy.review.id,'review1');
  await f.mutate('unbookmark',{bookmarkId:'b1'});await f.mutate('remove');await f.mutate('add',{name:'Again'});await f.mutate('reset');assert.deepEqual(f.state().collections,[]);
});
test('duplicate collection/bookmark IDs and same source/version fail without mutation',async()=>{
  const f=fixture();await f.mutate('add',{name:'Family'});await assert.rejects(f.mutate('add',{name:'Duplicate'}));
  await f.mutate('bookmark',{bookmarkId:'b1',reference});const before=f.state();
  await assert.rejects(f.mutate('bookmark',{bookmarkId:'b1',reference:{...reference,recipeId:'different'}}));
  await assert.rejects(f.mutate('bookmark',{bookmarkId:'b2',reference}));assert.deepEqual(f.state(),before);
});
test('unavailable/withdrawn are explicit; private copy withheld without current rights',async()=>{
  const f=fixture();await f.mutate('add',{name:'Family'});await f.mutate('bookmark',{bookmarkId:'b1',reference});
  f.status('withdrawn');let read=await f.api.read({session:'verified',accountId:'a'});assert.equal(read.collections[0].bookmarks[0].status,'withdrawn');assert.equal(Object.hasOwn(read.collections[0].bookmarks[0],'privateCopy'),false);
  f.status('unavailable');read=await f.api.read({session:'verified',accountId:'a'});assert.equal(read.collections[0].bookmarks[0].status,'unavailable');
  f.status('available');f.copy(false);read=await f.api.read({session:'verified',accountId:'a'});assert.equal(Object.hasOwn(read.collections[0].bookmarks[0],'privateCopy'),false);
});
test('cross-account, client consent flags and revoked session fail closed',async()=>{
  const f=fixture();await assert.rejects(f.api.read({session:'verified',accountId:'b'}));
  await assert.rejects(f.api.read({session:{allowed:true,consent:{granted:true}},accountId:'a'}));f.revoke();
  await assert.rejects(f.mutate('add',{name:'Family'}));assert.equal(f.state().revision,0);
});
test('command snapshot captured before authorization await; getters rejected without invocation',async()=>{
  const f=fixture();let release;f.authWait(new Promise(r=>release=r));
  const command={type:'add',name:'Family',collectionId:'family',operationId:'op',expectedVersion:0};
  const pending=f.api.mutate({session:'verified',accountId:'a',command});command.name='Injected';release();await pending;assert.equal(f.state().collections[0].name,'Family');
  let calls=0;const evil={...command};Object.defineProperty(evil,'name',{enumerable:true,get(){calls++;return 'bad';}});
  await assert.rejects(f.api.mutate({session:'verified',accountId:'a',command:evil}));assert.equal(calls,0);
});
test('atomic commit admission rejects revocation after precommit await',async()=>{
  const f=fixture();let release;f.commitWait(new Promise(r=>release=r));
  const pending=f.mutate('add',{name:'Family'});await new Promise(r=>setImmediate(r));f.revoke();release();
  assert.equal((await pending).status,'unknown');assert.equal(f.state().revision,0);
});
test('stale expectedVersion conflicts; lost ack remains unknown after applied commit',async()=>{
  const f=fixture();await f.mutate('add',{name:'Family'});assert.equal((await f.mutate('rename',{name:'New',expectedVersion:0})).status,'conflict');
  f.lose();assert.equal((await f.mutate('rename',{name:'Applied'})).status,'unknown');assert.equal(f.state().collections[0].name,'Applied');
});
test('actual kitchen projection omits collection names, private copies and bookmark lineage',async()=>{
  const f=fixture();await f.mutate('add',{name:'Family'});await f.mutate('bookmark',{bookmarkId:'b1',reference});
  const projected=kitchenProjection({inventory:[],products:{},recipes:[],profile:{privateCollections:f.state(),servings:2}});
  assert.equal(Object.hasOwn(projected.profile,'privateCollections'),false);assert.equal(JSON.stringify(projected).includes('Private note'),false);assert.deepEqual(projected.recipes,[]);
});
test('W20-C1 command and restored references reject embedded source content',async()=>{
  for(const status of ['withdrawn','unavailable','available']) {
    const f=fixture();await f.mutate('add',{name:'Family'});f.status(status);f.copy(false);
    const bad={...reference,privateCopy:{instructions:['CALLER_SOURCE_BODY_MARKER']}};
    await assert.rejects(f.mutate('bookmark',{bookmarkId:'b1',reference:bad}),/identifiers only/);
    const state=f.state();state.collections[0].bookmarks.push({id:'restored',reference:bad,status});f.restore(state);
    await assert.rejects(f.api.read({session:'verified',accountId:'a'}),/identifiers only/);
  }
});
test('W20-C1 rebuilt projection and mutation remove old copy/provenance/extra content',async()=>{
  const f=fixture();await f.mutate('add',{name:'Family'});await f.mutate('bookmark',{bookmarkId:'b1',reference});
  const state=f.state();state.collections[0].bookmarks[0].provenance={instructions:['OLD_BODY']};state.collections[0].bookmarks[0].unknownBody=['EXTRA_BODY'];f.restore(state);
  f.status('withdrawn');f.patch({provenance:{instructions:['RESOLVER_BODY']}});
  const read=await f.api.read({session:'verified',accountId:'a'});
  assert.deepEqual(Object.keys(read.collections[0].bookmarks[0]).sort(),['id','reference','status']);
  await f.mutate('rename',{name:'New'});assert.deepEqual(Object.keys(f.state().collections[0].bookmarks[0]).sort(),['id','reference','status']);
});
test('W20-C2 load revocation suppresses conflict metadata; live conflict still works',async()=>{
  const f=fixture();await f.mutate('add',{name:'Family'});
  assert.equal((await f.mutate('rename',{name:'ignored',expectedVersion:0})).revision,1);
  f.afterLoad(()=>f.revoke());await assert.rejects(f.mutate('rename',{name:'ignored',expectedVersion:0}),/access denied/);
});
test('W20-C3 source namespace and rights review/provenance mismatches reject',async()=>{
  for(const field of ['sourceId','rightsVersion']) {
    const f=fixture();await f.mutate('add',{name:'Family'});
    const copy={accountId:'a',review:{id:'r',status:'personally-reviewed',sourceRecipeId:'recipe-one',sourceVersion:'v1',sourceId:'manual-source',rightsVersion:'policy1'},recipe:{provenance:{sourceId:'manual-source',rightsVersion:'policy1'},instructions:['Content']}};
    copy.review[field]='OTHER';f.patch({privateCopy:copy});await assert.rejects(f.mutate('bookmark',{bookmarkId:'b',reference}),/mismatch/);
    copy.review[field]=reference[field];copy.recipe.provenance[field]='OTHER';await assert.rejects(f.mutate('bookmark',{bookmarkId:'b',reference}),/lineage/);
  }
});
test('PR9 source withdrawal during final account check denies stale private copy release',async()=>{
  const f=fixture();await f.mutate('add',{name:'Family'});await f.mutate('bookmark',{bookmarkId:'b',reference});
  f.afterResolve(()=>f.status('withdrawn'));
  await assert.rejects(f.api.read({session:'verified',accountId:'a'}),/release denied/);
});
test('PR9 null response after applied commit remains unknown, never throws or implies rollback',async()=>{
  const f=fixture();f.nullAck();const result=await f.mutate('add',{name:'Family'});
  assert.equal(result.status,'unknown');assert.equal(result.operationId,'op1');assert.equal(f.state().revision,1);
});
