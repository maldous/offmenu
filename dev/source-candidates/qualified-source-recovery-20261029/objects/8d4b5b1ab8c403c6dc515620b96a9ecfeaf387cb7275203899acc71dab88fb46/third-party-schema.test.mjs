import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { DatabaseSync } from 'node:sqlite';

const path=name=>new URL('../cloud/'+name,import.meta.url);
const features=['admin-schema.sql','admin-operations-schema.sql','admin-mcp-schema.sql','services-schema.sql','care-cases-schema.sql','care-community-schema.sql','care-updates-schema.sql','recipe-community-schema.sql','community-ai-schema.sql','personal-ai-schema.sql'];
const normalizeSql=sql=>sql?.replace(/--[^\n]*/g,'').replace(/\s+/g,' ').replace(/\(\s+/g,'(').replace(/\s+\)/g,')').replace(/\s*,\s*/g,',').trim();
const rows=db=>db.prepare("SELECT type,name,sql FROM sqlite_master WHERE type IN ('table','index') AND name NOT LIKE 'sqlite_%' ORDER BY type,name").all().map(row=>({...row,sql:normalizeSql(row.sql)}));

test('canonical schema structurally equals parent schema plus every additive feature migration',()=>{
 const parent=readFileSync(new URL('./fixtures/pre-care-schema.sql',import.meta.url),'utf8'),migrated=new DatabaseSync(':memory:'),canonical=new DatabaseSync(':memory:');
 migrated.exec(parent);for(const file of features)migrated.exec(readFileSync(path(file),'utf8'));
 canonical.exec(readFileSync(path('schema.sql'),'utf8'));
 assert.deepEqual(rows(canonical),rows(migrated));
});

test('feature migrations replay and preserve existing private sentinel records',()=>{
 const db=new DatabaseSync(':memory:'),parent=readFileSync(new URL('./fixtures/pre-care-schema.sql',import.meta.url),'utf8');
 db.exec(parent);db.prepare('INSERT INTO user_state(user_id,revision,state_json,updated_at) VALUES(?,?,?,?)').run('private-owner',1,'{"private":true}','2026-10-14T00:00:00.000Z');
 for(const file of features){const sql=readFileSync(path(file),'utf8');db.exec(sql);db.exec(sql);}
 assert.deepEqual({...db.prepare('SELECT user_id,state_json FROM user_state WHERE user_id=?').get('private-owner')},{user_id:'private-owner',state_json:'{"private":true}'});
 for(const file of features)for(const match of readFileSync(path(file),'utf8').matchAll(/CREATE TABLE IF NOT EXISTS\s+([a-z_]+)/gi))assert(rows(db).some(row=>row.type==='table'&&row.name===match[1]));
});
