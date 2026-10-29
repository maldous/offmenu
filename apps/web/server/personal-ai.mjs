import {validateState} from './state.mjs';
import {validateRecipes} from '../src/model.js';
import {sealCredentials,openCredentials} from './provider-data.mjs';
import {providerDataRoutes} from './provider-data.mjs';
import {recipeCommunityRoutes} from './recipe-community.mjs';
import {isCommunityRestricted} from './care-community.mjs';

const reply=(data,status=200)=>Response.json(data,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
const object=value=>!!value&&typeof value==='object'&&!Array.isArray(value);
const exact=(value,keys)=>object(value)&&Object.keys(value).every(key=>keys.includes(key));
const scope=(name,description,inputSchema,write=false,destructive=false)=>({name,description,scope:write?name==='update_profile'?'profile:write':name==='save_recipe'?'recipes:write':name==='save_plan'?'plans:write':name==='update_inventory'?'inventory:write':name==='contribute_recipe'?'community:contribute':'ai:write':name==='get_profile'?'profile:read':name==='get_recipes'?'recipes:read':name==='get_providers'?'providers:read':name==='lookup_provider'?'providers:lookup':'ai:read',inputSchema,annotations:{readOnlyHint:!write,destructiveHint:destructive,idempotentHint:!write,openWorldHint:name==='lookup_provider'}});
const noOwner=value=>object(value)&&!Object.hasOwn(value,'owner')&&!Object.hasOwn(value,'owner_id')&&!Object.hasOwn(value,'userId')&&!Object.hasOwn(value,'user_id');
const safeText=(value,max)=>typeof value==='string'&&value.length<=max&&!/[\u0000-\u001f\u007f-\u009f]/.test(value);
const preferenceDefault=()=>({agentName:'',rules:''});
const key=env=>env.PERSONAL_AI_VAULT_KEY||env.PROVIDER_VAULT_KEY;
const ownerFrom=user=>{
 const owner=user?.user_id;
 if(typeof owner!=='string'||!owner||owner.length>200)throw Error('A validated personal integration grant is required.');
 return owner;
};
const stateDefault=()=>({inventory:[],recipes:[],profile:{units:'metric',servings:1},selections:[]});
async function loadState(env,owner){
 const row=await env.DB.prepare('SELECT state_json,revision,updated_at FROM user_state WHERE user_id=?').bind(owner).first();
 const state=row?JSON.parse(row.state_json):stateDefault();
 return {state,revision:row?.revision||0,updatedAt:row?.updated_at||null};
}
async function saveState(env,owner,revision,state){
 // validateState deliberately projects known state. Retain fields from the current
 // owner profile only after the reconstructed state has been validated; callers
 // can mutate only the narrowly validated fields above.
 const validated=validateState(state);validated.profile={...(state.profile||{}),...validated.profile};const stamp=new Date().toISOString();
 if(revision===0){
  const created=await env.DB.prepare('INSERT INTO user_state(user_id,revision,state_json,updated_at) VALUES(?,1,?,?) ON CONFLICT(user_id) DO NOTHING RETURNING revision').bind(owner,JSON.stringify(validated),stamp).first();
  if(!created)throw Object.assign(Error('A newer personal state revision exists.'),{status:409});
  return 1;
 }
 const updated=await env.DB.prepare('UPDATE user_state SET revision=revision+1,state_json=?,updated_at=? WHERE user_id=? AND revision=? RETURNING revision').bind(JSON.stringify(validated),stamp,owner,revision).first();
 if(!updated)throw Object.assign(Error('A newer personal state revision exists.'),{status:409});
 return updated.revision;
}
function requireArgs(args,keys){if(!exact(args,keys)||!noOwner(args))throw Error('Invalid tool arguments.');}
function requireRevision(value){if(!Number.isSafeInteger(value)||value<0)throw Error('A state revision is required.');}
function requireConfirmed(value){if(value!==true)throw Error('A reviewed write confirmation is required.');}
function result(value,isError=false){return {content:[{type:'text',text:JSON.stringify(value)}],structuredContent:value,isError};}
export const PERSONAL_AI_TOOLS=[
 scope('get_profile','Read the authorised owner’s private profile snapshot.',{type:'object',properties:{},additionalProperties:false}),
 scope('get_recipes','Read the authorised owner’s saved private recipes.',{type:'object',properties:{},additionalProperties:false}),
 scope('get_providers','List metadata for the authorised owner’s connected providers. Credentials are never returned.',{type:'object',properties:{},additionalProperties:false}),
 scope('lookup_provider','Use a connected personal provider adapter without exposing its credentials.',{type:'object',properties:{sourceId:{type:'string',maxLength:100},query:{type:'string',maxLength:100}},required:['sourceId','query'],additionalProperties:false}),
 scope('update_profile','Save reviewed country, units, servings, or interface language using the owner’s current state revision.',{type:'object',properties:{confirmed:{const:true},revision:{type:'integer',minimum:0},profile:{type:'object',properties:{country:{type:'string',maxLength:2},units:{enum:['metric','imperial']},servings:{type:'number',exclusiveMinimum:0},uiLanguage:{enum:['en','ar']}},additionalProperties:false}},required:['confirmed','revision','profile'],additionalProperties:false},true),
 scope('save_recipe','Save one private recipe using the owner’s current state revision.',{type:'object',properties:{confirmed:{const:true},revision:{type:'integer',minimum:0},recipe:{type:'object'}},required:['confirmed','revision','recipe'],additionalProperties:false},true),
 scope('save_plan','Replace a reviewed meal plan using the owner’s current state revision.',{type:'object',properties:{confirmed:{const:true},revision:{type:'integer',minimum:0},plan:{type:'array'}},required:['confirmed','revision','plan'],additionalProperties:false},true,true),
 scope('update_inventory','Replace reviewed inventory using the owner’s current state revision.',{type:'object',properties:{confirmed:{const:true},revision:{type:'integer',minimum:0},inventory:{type:'array'}},required:['confirmed','revision','inventory'],additionalProperties:false},true,true),
 scope('get_ai_preferences','Read the owner’s encrypted personal AI preferences.',{type:'object',properties:{},additionalProperties:false}),
 scope('save_ai_preferences','Save reviewed personal AI preferences.',{type:'object',properties:{confirmed:{const:true},revision:{type:'integer',minimum:0},preferences:{type:'object'}},required:['confirmed','revision','preferences'],additionalProperties:false},true),
 scope('contribute_recipe','Submit a personally reviewed AI-attributed recipe for public moderation.',{type:'object',properties:{idempotencyKey:{type:'string',minLength:16,maxLength:128},confirmed:{const:true},rightsConfirmed:{const:true},alias:{type:'string',maxLength:40},recipe:{type:'object'},license:{enum:['CC BY 4.0','CC0-1.0']}},required:['idempotencyKey','confirmed','rightsConfirmed','alias','recipe','license'],additionalProperties:false},true)
];
function allowed(user,name){const descriptor=PERSONAL_AI_TOOLS.find(tool=>tool.name===name),scopes=user?.scopes;return descriptor&&Array.isArray(scopes)&&!scopes.some(scope=>typeof scope==='string'&&scope.startsWith('admin:'))&&scopes.includes(descriptor.scope);}
function profileSettings(value){
 if(!exact(value,['country','units','servings','uiLanguage']))throw Error('Profile updates may only set country, units, servings and interface language.');
 const next={};
 if(value.country!==undefined){if(typeof value.country!=='string'||value.country!==''&&!/^[A-Z]{2}$/.test(value.country))throw Error('Invalid country.');next.country=value.country;}
 if(value.units!==undefined){if(!['metric','imperial'].includes(value.units))throw Error('Invalid units.');next.units=value.units;}
 if(value.servings!==undefined){if(!Number.isFinite(value.servings)||value.servings<=0)throw Error('Invalid servings.');next.servings=value.servings;}
 if(value.uiLanguage!==undefined){if(!['en','ar'].includes(value.uiLanguage))throw Error('Invalid interface language.');next.uiLanguage=value.uiLanguage;}
 return next;
}
function preferenceValid(value){
 if(!exact(value,['agentName','rules'])||!safeText(value.agentName,80)||!value.agentName.trim()||!safeText(value.rules,5000))throw Error('Invalid personal AI preferences.');
 return {agentName:value.agentName.trim(),rules:value.rules};
}
async function loadPreferences(env,owner){
 const row=await env.DB.prepare('SELECT sealed,revision,updated_at FROM personal_ai_preferences WHERE owner_id=?').bind(owner).first().catch(()=>null);
 if(!row)return {preferences:preferenceDefault(),revision:0,updatedAt:null};
 return {preferences:preferenceValid(await openCredentials(row.sealed,key(env),owner+'|personal-ai')),revision:row.revision,updatedAt:row.updated_at};
}
async function savePreferences(env,owner,revision,preferences){
 preferences=preferenceValid(preferences);const sealed=await sealCredentials(preferences,key(env),owner+'|personal-ai'),stamp=new Date().toISOString();
 const row=revision===0?await env.DB.prepare('INSERT INTO personal_ai_preferences(owner_id,sealed,revision,updated_at) VALUES(?,?,1,?) ON CONFLICT(owner_id) DO NOTHING RETURNING revision').bind(owner,sealed,stamp).first():await env.DB.prepare('UPDATE personal_ai_preferences SET sealed=?,revision=revision+1,updated_at=? WHERE owner_id=? AND revision=? RETURNING revision').bind(sealed,stamp,owner,revision).first();
 if(!row)throw Object.assign(Error('A newer personal AI preference revision exists.'),{status:409});return row.revision;
}
async function providerLookup({args,owner,request,env,verifiedUser,boundedJSON}){
 requireArgs(args,['sourceId','query']);if(!safeText(args.sourceId,100)||!safeText(args.query,100)||!args.query.trim())throw Error('Invalid provider lookup.');
 const url=new URL(request.url);const proxied=new Request(url.origin+'/api/data/lookup',{method:'POST',headers:{'Content-Type':'application/json','Origin':url.origin},body:JSON.stringify({sourceId:args.sourceId,query:args.query.trim()})});
 const response=await providerDataRoutes(proxied,env,{verifiedUser:async()=>({id:owner}),boundedJSON,assets:{}});
 const body=await response.json();if(!response.ok)throw Object.assign(Error(body.error||'Provider lookup unavailable.'),{status:response.status===400&&body.error==='This provider adapter is not implemented yet.'?410:response.status});return body;
}
export async function callPersonalAITool({name,args={},user,request,env,verifiedUser,boundedJSON}){
 try{
  const owner=ownerFrom(user);if(!allowed(user,name))throw Object.assign(Error('Personal AI scope is required.'),{status:403});
  if(name==='get_profile'){requireArgs(args,[]);const loaded=await loadState(env,owner);return result({revision:loaded.revision,updatedAt:loaded.updatedAt,profile:loaded.state.profile||{}});}
  if(name==='get_recipes'){requireArgs(args,[]);const loaded=await loadState(env,owner);return result({revision:loaded.revision,updatedAt:loaded.updatedAt,recipes:loaded.state.recipes||[]});}
  if(name==='get_providers'){requireArgs(args,[]);const rows=await env.DB.prepare('SELECT source_id,label FROM provider_connections WHERE user_id=? ORDER BY source_id').bind(owner).all();return result({providers:(rows.results||[]).map(row=>({sourceId:row.source_id,label:row.label}))});}
  if(name==='lookup_provider')return result(await providerLookup({args,owner,request,env,verifiedUser,boundedJSON}));
  if(name==='get_ai_preferences'){requireArgs(args,[]);return result(await loadPreferences(env,owner));}
  if(name==='save_ai_preferences'){requireArgs(args,['confirmed','revision','preferences']);requireConfirmed(args.confirmed);requireRevision(args.revision);return result({revision:await savePreferences(env,owner,args.revision,args.preferences)});}
  if(['update_profile','save_recipe','save_plan','update_inventory'].includes(name)){
   const field=name==='update_profile'?'profile':name==='save_recipe'?'recipe':name==='save_plan'?'plan':'inventory';requireArgs(args,['confirmed','revision',field]);requireConfirmed(args.confirmed);requireRevision(args.revision);const loaded=await loadState(env,owner);if(loaded.revision!==args.revision)throw Object.assign(Error('A newer personal state revision exists.'),{status:409});let next={...loaded.state,profile:{...(loaded.state.profile||{})}};
   if(name==='update_profile'){next.profile={...(loaded.state.profile||{}),...profileSettings(args.profile)};}
   if(name==='save_recipe'){validateRecipes([args.recipe]);const recipes=[...(loaded.state.recipes||[])];const index=recipes.findIndex(recipe=>recipe.id===args.recipe.id);if(index<0)recipes.push(args.recipe);else recipes[index]=args.recipe;next.recipes=recipes;}
   if(name==='save_plan')next.profile.plan=args.plan;
   if(name==='update_inventory')next.inventory=args.inventory;
   return result({revision:await saveState(env,owner,args.revision,next)});
  }
  if(name==='contribute_recipe'){
   requireArgs(args,['idempotencyKey','confirmed','rightsConfirmed','alias','recipe','license']);if(args.confirmed!==true||args.rightsConfirmed!==true||!['CC BY 4.0','CC0-1.0'].includes(args.license)||args.recipe?.license!==args.license)throw Error('Explicit confirmation and a supported public license are required.');
   const prefs=await loadPreferences(env,owner);if(!prefs.preferences.agentName)throw Error('Choose a personal assistant name before contributing an AI-attributed recipe.');if(await isCommunityRestricted(env,owner))throw Object.assign(Error('Community participation is restricted.'),{status:403});const url=new URL(request.url);const body={idempotencyKey:args.idempotencyKey,confirmed:true,rightsConfirmed:true,alias:args.alias,recipe:args.recipe,attribution:{kind:'ai',agentName:prefs.preferences.agentName}};
   const proxied=new Request(url.origin+'/api/community/recipes',{method:'POST',headers:{'Content-Type':'application/json','Origin':url.origin},body:JSON.stringify(body)});
   const response=await recipeCommunityRoutes(proxied,env,{verifiedUser:async()=>({id:owner}),boundedJSON,reply});const payload=await response.json();if(!response.ok)throw Object.assign(Error(payload.error||'Contribution unavailable.'),{status:response.status});return result(payload);
  }
  throw Error('Unknown personal AI tool.');
 }catch(error){return result({error:error.message||'Personal AI operation unavailable.',status:error.status||400},true);}
}
export async function personalAIRoutes(request,env,{verifiedUser,boundedJSON,reply:respond=reply}={}){
 const url=new URL(request.url),path=url.pathname;if(!path.startsWith('/api/care/ai'))return null;if(!env.DB)return respond({error:'Personal AI storage unavailable.'},503);const user=await verifiedUser(request);if(!user?.id)return respond({error:'Sign in required.'},401);if(request.method!=='GET'&&request.headers.get('Origin')!==url.origin)return respond({error:'Origin mismatch'},403);
 if(path==='/api/care/ai/preferences'&&request.method==='GET'){try{return respond(await loadPreferences(env,user.id));}catch{return respond({error:'Personal AI preferences unavailable.'},503);}}
 if(path==='/api/care/ai/preferences'&&request.method==='PUT'){try{const body=await boundedJSON(request,10000);if(!exact(body,['revision','preferences'])||!Number.isSafeInteger(body.revision)||body.revision<0)throw Error();return respond({revision:await savePreferences(env,user.id,body.revision,body.preferences)});}catch(error){return respond({error:error.message||'Invalid personal AI preferences.'},error.status||400);}}
 return respond({error:'Not found'},404);
}
