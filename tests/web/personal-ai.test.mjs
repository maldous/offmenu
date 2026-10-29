import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {callPersonalAITool,PERSONAL_AI_TOOLS,personalAIRoutes} from '../../apps/web/server/personal-ai.mjs';
import {setupPersonalAI} from '../../apps/web/src/personal-ai-ui.js';

const db=new DatabaseSync(':memory:');
db.exec(readFileSync(new URL('../../apps/web/server/schema.sql',import.meta.url),'utf8'));
db.exec(readFileSync(new URL('../../apps/web/server/personal-ai-schema.sql',import.meta.url),'utf8'));
const env={
 PROVIDER_VAULT_KEY:'a'.repeat(64),
 DB:{prepare(sql){
  const bound=args=>({
   async first(){return db.prepare(sql).get(...args)||null;},
   async all(){return {results:db.prepare(sql).all(...args)};},
   async run(){return db.prepare(sql).run(...args);}
  });
  return {...bound([]),bind(...args){return bound(args);}};
 }}
};
const state={inventory:[],recipes:[],profile:{units:'metric',servings:1,locations:[{id:'private-location',area:'Pantry',shelf:'Top'}],plan:[{id:'private-plan',recipeId:'r',date:'2026-10-14',slot:'Dinner',servings:1}],members:[{id:'private-member',name:'Sam',portion:1,avoid:[],advisors:[]}],history:[{id:'private-history',title:'Dinner',recipeId:'r',date:'2026-10-14',slot:'Dinner',servings:1,memberId:'private-member',source:'Manual',createdAt:'2026-10-14T00:00:00Z',totals:{}}]},selections:['private-selection']};
db.prepare('INSERT INTO user_state(user_id,revision,state_json,updated_at) VALUES(?,?,?,?)').run('alice',1,JSON.stringify(state),'today');
db.prepare('INSERT INTO user_state(user_id,revision,state_json,updated_at) VALUES(?,?,?,?)').run('bob',1,JSON.stringify({...state,profile:{units:'imperial',servings:2}}),'today');
const request=new Request('https://example.test/mcp');
const user=(scopes=['profile:read','profile:write','recipes:read','recipes:write','plans:write','inventory:write','providers:read','providers:lookup','ai:read','ai:write'])=>({user_id:'alice',id:'grant-1',name:'Alice AI',scopes});
const call=async(name,args,u=user())=>{const output=await callPersonalAITool({name,args,user:u,request,env,verifiedUser:async()=>({id:'alice'}),boundedJSON:r=>r.json()});return output.structuredContent;};

test('personal AI descriptors declare explicit scopes and do not include owner input',()=>{
 assert.ok(PERSONAL_AI_TOOLS.some(tool=>tool.name==='get_profile'&&tool.scope==='profile:read'));
 assert.ok(PERSONAL_AI_TOOLS.some(tool=>tool.name==='contribute_recipe'&&tool.scope==='community:contribute'));
 assert.equal(JSON.stringify(PERSONAL_AI_TOOLS).includes('owner_id'),false);
});
test('profile reads are grant-owner scoped and owner payloads are rejected',async()=>{
 const profile=await call('get_profile',{});assert.equal(profile.profile.units,'metric');
 const rejected=await call('get_profile',{owner:'bob'});assert.equal(rejected.status,400);
});
test('CAS mutation preserves unrelated private state',async()=>{
 const saved=await call('update_inventory',{confirmed:true,revision:1,inventory:[{id:'local:rice',barcode:'local:rice',name:'Rice',ingredient:'rice',quantity:1,unit:'g'}]});assert.equal(saved.revision,2);
 const stored=JSON.parse(db.prepare('SELECT state_json FROM user_state WHERE user_id=?').get('alice').state_json);assert.equal(stored.profile.locations[0].id,'private-location');assert.deepEqual(stored.selections,['private-selection']);assert.equal(stored.inventory[0].name,'Rice');
 const stale=await call('update_inventory',{confirmed:true,revision:1,inventory:[]});assert.equal(stale.status,409);
 assert.equal(JSON.parse(db.prepare('SELECT state_json FROM user_state WHERE user_id=?').get('bob').state_json).profile.units,'imperial');
});
test('profile settings merge without replacing private profile canaries',async()=>{
 const saved=await call('update_profile',{confirmed:true,revision:2,profile:{units:'imperial',servings:2}});assert.equal(saved.revision,3);
 const profile=JSON.parse(db.prepare('SELECT state_json FROM user_state WHERE user_id=?').get('alice').state_json).profile;
 assert.equal(profile.units,'imperial');assert.equal(profile.servings,2);assert.equal(profile.locations[0].id,'private-location');assert.equal(profile.plan[0].id,'private-plan');assert.equal(profile.members[0].id,'private-member');assert.equal(profile.history[0].id,'private-history');
 const rejected=await call('update_profile',{confirmed:true,revision:3,profile:{units:'metric',servings:1,locations:[]}});assert.equal(rejected.status,400);
});
test('MCP writes require confirmed true before reading or mutating owner state',async()=>{
 const before=db.prepare('SELECT revision,state_json FROM user_state WHERE user_id=?').get('alice');
 const denied=await call('update_inventory',{confirmed:false,revision:3,inventory:[]});assert.equal(denied.status,400);
 const after=db.prepare('SELECT revision,state_json FROM user_state WHERE user_id=?').get('alice');assert.deepEqual(after,before);
});
test('preferences are encrypted, bounded, and scoped to their owner',async()=>{
 const saved=await call('save_ai_preferences',{confirmed:true,revision:0,preferences:{agentName:'Kitchen twin',rules:'Use my saved recipes.'}});assert.equal(saved.revision,1);
 const raw=db.prepare('SELECT sealed FROM personal_ai_preferences WHERE owner_id=?').get('alice').sealed;assert.equal(raw.includes('saved recipes'),false);
 assert.equal((await call('get_ai_preferences',{})).preferences.agentName,'Kitchen twin');
 const unsafe=await call('save_ai_preferences',{confirmed:true,revision:1,preferences:{agentName:'ok',rules:'x'.repeat(5001)}});assert.equal(unsafe.status,400);
});
test('a personal AI identity must be selected before public AI attribution',async()=>{
 const freshDb=new DatabaseSync(':memory:');freshDb.exec(readFileSync(new URL('../../apps/web/server/schema.sql',import.meta.url),'utf8'));freshDb.exec(readFileSync(new URL('../../apps/web/server/personal-ai-schema.sql',import.meta.url),'utf8'));
 const freshEnv={...env,DB:{prepare(sql){const bound=args=>({async first(){return freshDb.prepare(sql).get(...args)||null;},async all(){return {results:freshDb.prepare(sql).all(...args)};},async run(){return freshDb.prepare(sql).run(...args);}});return {...bound([]),bind(...args){return bound(args);}}}}};
 const output=await callPersonalAITool({name:'contribute_recipe',args:{idempotencyKey:'abcdefghijklmnop',confirmed:true,rightsConfirmed:true,alias:'Alice',license:'CC0-1.0',recipe:{license:'CC0-1.0'}},user:{...user(['community:contribute']),name:'Private token label'},request,env:freshEnv,verifiedUser:async()=>({id:'alice'}),boundedJSON:r=>r.json()});assert.equal(output.structuredContent.status,400);assert.match(output.structuredContent.error,/assistant name/);
});
test('missing scope is denied before owner state is read',async()=>{
 const denied=await call('get_profile',{},user(['recipes:read']));assert.equal(denied.status,403);
});
test('an administrator-shaped grant cannot enter the personal AI surface',async()=>{
 const denied=await call('get_profile',{},user(['profile:read','admin:community:read']));assert.equal(denied.status,403);
});
test('an unsupported provider adapter makes no credential or network path available',async()=>{
 const denied=await call('lookup_provider',{sourceId:'spoonacular',query:'rice'});assert.equal(denied.status,410);assert.match(denied.error,/not implemented/);
});
test('browser preference writes require same-origin authenticated requests',async()=>{
 const cross=new Request('https://example.test/api/care/ai/preferences',{method:'PUT',headers:{Origin:'https://evil.example','Content-Type':'application/json'},body:JSON.stringify({revision:1,preferences:{agentName:'x',rules:''}})});
 const response=await personalAIRoutes(cross,env,{verifiedUser:async()=>({id:'alice'}),boundedJSON:r=>r.json()});assert.equal(response.status,403);
});
test('personal AI UI drops delayed preference data after logout reset',async()=>{
 class Element {constructor(tag){this.tagName=tag;this.children=[];this.hidden=false;}append(...items){this.children.push(...items);}replaceChildren(...items){this.children=[...items];}}
 const document={createElement:tag=>new Element(tag),createTextNode:text=>({text})},root=new Element('section');root.ownerDocument=document;let resolve;const pending=new Promise(done=>{resolve=done;});let account={id:'alice'};
 const ui=setupPersonalAI({root,getUser:()=>account,authFetch:async()=>pending});const load=ui.refresh();ui.reset();account=null;resolve(Response.json({revision:1,preferences:{agentName:'Leaked',rules:'private'}}));await load;assert.equal(root.hidden,true);assert.equal(root.children.length,0);
});
