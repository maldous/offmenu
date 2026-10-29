import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {catalogueRows} from '../../cloud/catalogue.mjs';
import {normalizeOFF,asOffNutriments} from '../../public/unified-data.js';
import {sourceById} from '../../public/sources.js';

test('source country filtering keeps documented global routes and excludes other countries',async()=>{
 const db=new DatabaseSync(':memory:');
 db.exec(readFileSync(new URL('../../cloud/catalogue-schema.sql',import.meta.url),'utf8'));
 for(const [id,country]of [['a','AU'],['b','GB'],['c','']]){
  db.prepare('INSERT INTO catalogue VALUES(?,?,?,?,?,?)').run('source',id,'',JSON.stringify({id}),id,'1');
  db.prepare('INSERT INTO catalogue_source_countries VALUES(?,?)').run(id,country);
 }
 const env={DB:{prepare(sql){return {bind(...args){return {async all(){return {results:db.prepare(sql).all(...args)}}}}}}}};
 assert.deepEqual((await catalogueRows(env,{kind:'source',country:'AU'})).rows.map(r=>r.id),['a','c']);
 assert.equal((await catalogueRows(env,{kind:'source'})).rows.length,3);
});

test('Vitamin C normalization preserves mg and enforces mass versus volume basis',()=>{
 const rows=normalizeOFF({product:{code:'00012345',nutriments:{'vitamin-c_100g':.03}}},sourceById('off'));
 assert.equal(rows[1].data.nutrients.vitaminC.value,30);
 assert.equal(asOffNutriments(rows[1],'g')['vitamin-c_100g'],.03);
 assert.throws(()=>asOffNutriments(rows[1],'ml'));
});
