import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {DatabaseSync} from 'node:sqlite';
import {mkdtempSync,rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
const env=Object.fromEntries(Object.entries(process.env).filter(([k])=>!k.startsWith('GIT_')));
async function pinned(pin,path){const b=execFileSync('git',['show',`${pin}:${path}`],{env});return import('data:text/javascript;base64,'+b.toString('base64'));}
const {createIntakeHistory}=await pinned('53853acd35226ca7af591b978b72a92473c0b075','cloud/intake-history-owner25.mjs');
const entryModel=await pinned('59d8bca52cc3281741862d17f2579668d6e6140d','public/intake-entry-model.js');
const food=id=>({id,label:id,source:{id:'synthetic',recordId:id,rights:'unknown'}});
const input=(id,consentId='c1',state='unknown-consumed')=>({id,accountId:'a',memberId:'m',date:'2026-10-15',kind:'snack',state,
 quantity:{value:state==='unknown-consumed'?null:10,unit:'g'},consent:{id:consentId,purpose:'intake-recording',granted:true},food:food('snack')});
function fixture(t){
 const dir=mkdtempSync(join(tmpdir(),'owner21-review25-')),db=new DatabaseSync(join(dir,'test.sqlite'));
 db.exec('CREATE TABLE states(account TEXT PRIMARY KEY,revision INTEGER,doc TEXT); CREATE TABLE grants(account TEXT PRIMARY KEY,allowed INTEGER)');
 for(const account of ['a','b'])db.prepare('INSERT INTO grants VALUES(?,1)').run(account);
 t.after(()=>{db.close();rmSync(dir,{recursive:true,force:true});});
 let tail=Promise.resolve(),denySource=null,breakWrite=false;
 const store={transaction(account,fn){const p=tail.then(async()=>{
  db.exec('BEGIN IMMEDIATE');try{
   const row=db.prepare('SELECT * FROM states WHERE account=?').get(account);
   const result=await fn(row?JSON.parse(row.doc):null);
   if(breakWrite)throw Error('write-failure');
   const update=row?db.prepare('UPDATE states SET revision=revision+1,doc=? WHERE account=? AND revision=?').run(JSON.stringify(result.state),account,row.revision):
    db.prepare('INSERT INTO states VALUES(?,1,?)').run(account,JSON.stringify(result.state));
   assert.equal(update.changes,1);db.exec('COMMIT');return structuredClone(result.result);
  }catch(e){db.exec('ROLLBACK');throw e;}
 });tail=p.catch(()=>{});return p;}};
 const api=createIntakeHistory({store,entryModel,clock:()=> '2026-10-15T00:00:00.000Z',
 authorize:async({session,accountId,consentId,memberId})=>({accountId,allowed:session==='verified'&&db.prepare('SELECT allowed FROM grants WHERE account=?').get(accountId)?.allowed===1&&(!memberId||memberId==='m'),consent:{id:consentId,purpose:'intake-recording',granted:true}}),
 sourceAllowed:async ref=>ref.id!==denySource});
 return {api,db,deny:v=>denySource=v,break:v=>breakWrite=v};
}
const args=input=>({session:'verified',accountId:'a',input});
test('SQLite scoped CAS reload, duplicate serialization and unknown/planned distinction',async t=>{
 const f=fixture(t);
 const r=await Promise.allSettled([1,2].map(()=>f.api.append(args(input('same')))));
 assert.equal(r.filter(x=>x.status==='fulfilled').length,1);
 await f.api.append(args(input('plan','c1','planned')));
 const v=await f.api.read({session:'verified',accountId:'a'});
 assert.equal(v.planned.length,1);assert.equal(v.unknownConsumed[0].quantity.value,null);assert.equal(v.consumed.length,0);
 assert.equal(f.db.prepare('SELECT COUNT(*) AS n FROM states WHERE account=?').get('b').n,0);
});
test('SQLite failed persistence rolls back; revoked consent tombstone survives fresh read and regrant',async t=>{
 const f=fixture(t);await f.api.append(args(input('first')));f.break(true);
 await assert.rejects(f.api.revoke({session:'verified',accountId:'a',consentId:'c1'}),/write-failure/);f.break(false);
 assert.equal((await f.api.read({session:'verified',accountId:'a'})).unknownConsumed.length,1);
 await f.api.revoke({session:'verified',accountId:'a',consentId:'c1'});
 await assert.rejects(f.api.append(args(input('blocked'))),/revoked/);
 await f.api.append(args(input('regrant','c2')));
 const saved=JSON.parse(f.db.prepare('SELECT doc FROM states WHERE account=?').get('a').doc);
 assert.deepEqual(saved.revokedConsentIds,['c1']);assert.equal(saved.entries[0].consent.id,'c2');
});
test('substitution independently checks planned and actual source; authority withdrawal denies read',async t=>{
 const f=fixture(t),entry={...input('sub'),kind:'substitution',food:food('actual'),substitution:{planned:food('planned'),actual:food('actual')}};
 f.deny('planned');await assert.rejects(f.api.append(args(entry)),/source permission/);
 f.deny(null);await f.api.append(args(entry));f.deny('actual');
 assert.equal((await f.api.read({session:'verified',accountId:'a'})).unknownConsumed.length,0);
 f.db.prepare('UPDATE grants SET allowed=0 WHERE account=?').run('a');
 await assert.rejects(f.api.read({session:'verified',accountId:'a'}),/access denied/);
});
test('foreign persisted records fail closed on read without deleting evidence',async t=>{
 const f=fixture(t);await f.api.append(args(input('one')));
 const row=f.db.prepare('SELECT doc FROM states WHERE account=?').get('a');const value=JSON.parse(row.doc);value.entries[0].accountId='b';
 f.db.prepare('UPDATE states SET doc=? WHERE account=?').run(JSON.stringify(value),'a');
 await assert.rejects(f.api.read({session:'verified',accountId:'a'}),/Foreign intake record/);
 assert.equal(f.db.prepare('SELECT doc FROM states WHERE account=?').get('a').doc,JSON.stringify(value));
});
