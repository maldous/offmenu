import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {catalogueRoutes,catalogueRows} from '../../apps/web/server/catalogue.mjs';

test('stale catalogue still hides retired sources before filtering, count and pagination, without deleting history',async()=>{
 const db=new DatabaseSync(':memory:');
 db.exec(readFileSync(new URL('../../apps/web/server/catalogue-schema.sql',import.meta.url),'utf8'));
 db.exec('CREATE TABLE unified_records(source_id TEXT,owner TEXT)');
 const direct=['discovery:S042','discovery:S043','src-dc7480cf5666'], map='https://www.openstreetmap.org/copyright';
 const provenance={attribution:'© OpenStreetMap contributors',map};
 const write=(kind,id,data)=>db.prepare('INSERT INTO catalogue VALUES(?,?,?,?,?,?)').run(kind,id,'',JSON.stringify(data),'food','old');
 for(const id of [...direct,'S042','z-overture','b-other']){
  write('source',id,{id,...provenance});
  db.prepare('INSERT INTO catalogue_source_countries VALUES(?,?)').run(id,'');
 }
 write('specification','global-providers',{providers:[{name:'direct',source_ids:['S042','S043']},{name:'mixed',source_ids:['S042','other']},{name:'Overture',source_ids:['other'],...provenance}]});
 write('specification','enrichment-recommendations',{globalSources:[{source_id:direct[2]},{source_id:'overture',...provenance}]});
 const prepare=sql=>{const stmt=db.prepare(sql);const bind=(...args)=>({all:async()=>({results:stmt.all(...args)})});return {bind,all:bind().all};};
 const env={DB:{prepare}};
 const first=await catalogueRows(env,{kind:'source',country:'AU',query:'food',limit:1});
 assert.deepEqual(first.rows.map(r=>r.id),['b-other']);assert.equal(first.nextCursor,'b-other');
 const last=await catalogueRows(env,{kind:'source',country:'AU',cursor:first.nextCursor,limit:1});
 assert.deepEqual(last.rows.map(r=>r.id),['z-overture']);assert.equal(last.nextCursor,null);
 assert.equal(last.rows[0].data.map,map);assert.equal(last.rows[0].data.attribution,provenance.attribution);
 const specs=Object.fromEntries((await catalogueRows(env,{kind:'specification'})).rows.map(r=>[r.id,r.data]));
 assert.deepEqual(specs['global-providers'].providers,[{name:'mixed',source_ids:['other']},{name:'Overture',source_ids:['other'],...provenance}]);
 assert.deepEqual(specs['enrichment-recommendations'].globalSources,[{source_id:'overture',...provenance}]);
 const coverage=await (await catalogueRoutes(new Request('https://offmenu.example/api/catalogue/coverage'),env,{})).json();
 assert.equal(coverage.catalogue.find(r=>r.kind==='source').records,2);
 assert.deepEqual(coverage.research.families.find(r=>r.kind==='source'),{kind:'source',expected:1300,actual:2,complete:false});
 assert.equal(db.prepare("SELECT count(*) AS n FROM catalogue WHERE kind='source'").get().n,6);
 db.close();
});
