import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {mkdtempSync,readFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import handler from '../cloud/handler.mjs';
import {validateState} from '../cloud/state.mjs';
import {createLotConsumptionConsumer,reduceLotConsumption} from '../cloud/lot-consumption-owner21.mjs';

const at='2026-10-14T10:16:13.000Z';
const lot=()=>({id:'source-lot',barcode:'12345678',name:'Milk',ingredient:'milk',quantity:0.3,
  unit:'ml',amountBasis:'manual',expires:null,needsReview:true,
  location:{area:'Fridge',shelf:'Top'},openedAt:'2026-10-12',frozenAt:null,
  provenance:{sourceId:'synthetic-label',rights:'unknown',consent:'private'},
  unitProvenance:{observedUnit:'ml',basis:'user-observation'},allergens:null});
const initial=()=>({inventory:[lot()],products:{},recipes:[],selections:[],
  profile:{country:'AU',units:'metric',servings:2}});
const command=(action='consume',overrides={})=>({action,operationId:'operation-1',lotId:'source-lot',
  expectedVersion:1,expectedLot:lot(),confirmed:true,
  amount:{value:0.1,unit:'ml',provenance:{sourceId:'measured-1',method:'user-measured'}},
  ...(action==='decant'?{destination:{id:'decanted-lot',containerId:'jar-1',location:{area:'Fridge',shelf:'Bottom'}}}:{}),...overrides});
const req=(who='alice',origin='https://offmenu.aldous.info')=>new Request('https://offmenu.aldous.info/api/lot-consumption',
  {method:'POST',headers:{Authorization:'Bearer '+who,Origin:origin}});

function fixture(t){
  const dir=mkdtempSync(join(tmpdir(),'offmenu-owner21-'));
  const a=new DatabaseSync(join(dir,'state.sqlite')),b=new DatabaseSync(join(dir,'state.sqlite'));
  a.exec(readFileSync(new URL('../cloud/schema.sql',import.meta.url),'utf8'));
  // Test-only grant/ledger tables. No production migration or session issuer implied.
  a.exec('CREATE TABLE test_grants(subject TEXT PRIMARY KEY,active INTEGER); CREATE TABLE test_operations(subject TEXT,id TEXT,digest TEXT,result_json TEXT,PRIMARY KEY(subject,id))');
  for(const who of ['alice','bob']){
    a.prepare('INSERT INTO user_state VALUES(?,1,?,?)').run(who,JSON.stringify(initial()),at);
    a.prepare('INSERT INTO test_grants VALUES(?,1)').run(who);
  }
  t.after(()=>{a.close();b.close();rmSync(dir,{recursive:true,force:true});});
  const state=(who='alice')=>JSON.parse(a.prepare('SELECT state_json FROM user_state WHERE user_id=?').get(who).state_json);
  function make(database=a,{breakRecord=false,staleWrite=false,beforeTransaction=()=>{}}={}){
    return createLotConsumptionConsumer({
      authenticate:async request=>{const who=request.headers.get('Authorization')?.slice(7);return ['alice','bob'].includes(who)?{id:who}:null;},
      authorizeRequest:async request=>request.method==='POST'&&request.headers.get('Origin')===new URL(request.url).origin,
      clock:()=>at,
      async transact({accountId},work){
        beforeTransaction(); database.exec('BEGIN IMMEDIATE');
        try{
          const result=work({
            admit:()=>database.prepare('SELECT active FROM test_grants WHERE subject=?').get(accountId)?.active===1,
            state:()=>database.prepare('SELECT revision,state_json FROM user_state WHERE user_id=?').get(accountId),
            operation:id=>database.prepare('SELECT digest,result_json FROM test_operations WHERE subject=? AND id=?').get(accountId,id),
            write(version,json,time){const changed=database.prepare('UPDATE user_state SET revision=revision+1,state_json=?,updated_at=? WHERE user_id=? AND revision=?').run(json,time,accountId,staleWrite?version+1:version);assert.equal(changed.changes,1);},
            record(id,digest,result){if(breakRecord)throw Error('Ledger unavailable');database.prepare('INSERT INTO test_operations VALUES(?,?,?,?)').run(accountId,id,digest,JSON.stringify(result));}
          });
          assert.ok(!(result instanceof Promise));database.exec('COMMIT');return result;
        }catch(e){database.exec('ROLLBACK');throw e;}
      }
    });
  }
  return {a,b,state,make};
}

test('partial consume is exact, preserves source metadata and isolates private accounts',async t=>{
  const f=fixture(t),input=command(),before=structuredClone(input);
  const receipt=await f.make()(req(),input);
  assert.equal(receipt.revision,2);assert.equal(receipt.acknowledged,true);
  const source=f.state().inventory[0];assert.equal(source.quantity,0.2);
  assert.deepEqual({...source,quantity:0.3,quantityObservation21:undefined},{...lot(),quantityObservation21:undefined});
  assert.deepEqual(source.quantityObservation21.amount.provenance,input.amount.provenance);
  assert.deepEqual(f.state('bob'),initial());assert.deepEqual(input,before);
});

test('partial/full decant conserves observed unit and records source lot lineage',async t=>{
  const f=fixture(t);await f.make()(req(),command('decant'));
  const [source,dest]=f.state().inventory;
  assert.equal(source.quantity,0.2);assert.equal(dest.quantity,0.1);
  assert.equal(dest.lotLineage21.rootLotId,'source-lot');assert.equal(dest.lotLineage21.containerId,'jar-1');
  assert.deepEqual(dest.provenance,lot().provenance);assert.deepEqual(dest.unitProvenance,lot().unitProvenance);
  assert.equal(dest.openedAt,lot().openedAt);assert.equal(dest.expires,null);
  assert.equal(dest.location.shelf,'Bottom');
  const full=reduceLotConsumption(initial(),command('decant',{amount:{...command().amount,value:0.3}}),at);
  assert.equal(full.state.inventory.length,1);assert.equal(full.state.inventory[0].id,'decanted-lot');
});

test('lost acknowledgement replay returns immutable receipt without deducting again',async t=>{
  const f=fixture(t),c=f.make(),first=await c(req(),command());
  assert.deepEqual(await c(req(),command()),first);assert.equal(f.state().inventory[0].quantity,0.2);
  await assert.rejects(c(req(),command('consume',{amount:{...command().amount,value:0.2}})),/OPERATION_ID_REUSED/);
  f.a.prepare('UPDATE test_grants SET active=0 WHERE subject=?').run('alice');
  await assert.rejects(c(req(),command()),/SESSION_DENIED/);
});

test('two SQLite connections reject stale version and rolled-back ledger/CAS failures',async t=>{
  const f=fixture(t);await f.make(f.a)(req(),command());
  await assert.rejects(f.make(f.b)(req(),command('consume',{operationId:'operation-2'})),/VERSION_CONFLICT/);
  const next=command('consume',{operationId:'operation-2',expectedVersion:2,expectedLot:f.state().inventory[0]});
  await assert.rejects(f.make(f.b,{breakRecord:true})(req(),next),/Ledger unavailable/);
  assert.equal(f.state().inventory[0].quantity,0.2);
  await assert.rejects(f.make(f.b,{staleWrite:true})(req(),next));
  assert.equal(f.a.prepare('SELECT revision FROM user_state WHERE user_id=?').get('alice').revision,2);
  assert.equal(f.a.prepare('SELECT COUNT(*) AS n FROM test_operations').get().n,1);
});

test('revocation after async policy but before transaction denies mutation',async t=>{
  const f=fixture(t);await assert.rejects(f.make(f.b,{beforeTransaction:()=>f.a.prepare('UPDATE test_grants SET active=0 WHERE subject=?').run('alice')})(req(),command()),/SESSION_DENIED/);
  assert.deepEqual(f.state(),initial());
  await assert.rejects(f.make()(req('invalid'),command()),/UNAUTHENTICATED/);
  await assert.rejects(f.make()(req('alice','https://other.example'),command()),/REQUEST_DENIED/);
  await assert.rejects(f.make()(req(),command('consume',{accountId:'bob'})),/UNSUPPORTED_COMMAND_FIELD/);
});

test('quantity/unit/source snapshot/provenance and cooked batch guards',()=>{
  const checks=[
    command('consume',{amount:{...command().amount,value:0.4}}),
    command('consume',{amount:{...command().amount,unit:'g'}}),
    command('consume',{amount:{...command().amount,value:1e-10}}),
    command('consume',{amount:{value:0.1,unit:'ml'}}),
    command('consume',{expectedLot:{...lot(),openedAt:null}}),
    command('decant',{destination:{...command('decant').destination,id:'source-lot'}}),
    command('consume',{confirmed:false})
  ];
  for(const c of checks)assert.throws(()=>reduceLotConsumption(initial(),c,at));
  const cooked=initial();cooked.inventory[0].cookBatchId='batch-1';
  assert.throws(()=>reduceLotConsumption(cooked,command('consume',{expectedLot:cooked.inventory[0]}),at),/COOKED_BATCH/);
  const full=reduceLotConsumption(initial(),command('consume',{amount:{...command().amount,value:0.3}}),at);
  assert.deepEqual(full.state.inventory,[]);assert.equal(full.observation.sourceLotId,'source-lot');
  assert.deepEqual(full.observation.sourceSnapshot,lot());
  assert.throws(()=>reduceLotConsumption(initial(),command(),'2026-02-30T00:00:00.000Z'),/CLOCK/);
});

test('inputs are captured before async hooks and hostile JSON hooks never execute',async t=>{
  const f=fixture(t),c=command(),promise=f.make()(req(),c);c.amount.value=0.2;
  await promise;assert.equal(f.state().inventory[0].quantity,0.2);
  const hostile=command();let calls=0;Object.defineProperty(hostile,'action',{enumerable:true,get(){calls++;return 'consume';}});
  assert.throws(()=>reduceLotConsumption(initial(),hostile,at),/ACCESSOR/);assert.equal(calls,0);
  const sparse=initial();sparse.inventory=Array(1);assert.throws(()=>reduceLotConsumption(sparse,command(),at),/DENSE_ARRAY/);
});

test('actual handler GET reads committed state; existing PUT projection proves remaining adoption gap',async t=>{
  const f=fixture(t);await f.make()(req(),command('decant'));
  const original=globalThis.fetch;
  globalThis.fetch=async()=>Response.json({id:'alice'});
  t.after(()=>{globalThis.fetch=original;});
  const env={DB:{prepare(sql){
    return {bind(...args){
      return {async first(){return f.a.prepare(sql).get(...args)||null;}};
    }};
  }}};
  const result=await handler.fetch(new Request('https://offmenu.aldous.info/api/state',
    {headers:{Authorization:'Bearer synthetic-only'}}),env);
  assert.equal(result.status,200);const actual=await result.json();
  assert.equal(actual.revision,2);assert.equal(actual.state.inventory[1].lotLineage21.sourceLotId,'source-lot');
  const projected=validateState(actual.state);
  assert.equal(projected.inventory[1].lotLineage21,undefined);
  assert.equal(projected.inventory[0].quantityObservation21,undefined);
});
