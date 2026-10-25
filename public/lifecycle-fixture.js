// Explicit same-origin DEV fixture only. No Identity SDK, shared storage enumeration or resets.
export function selectLifecycleFixture(url) {
  const u=new URL(url);
  if(u.searchParams.get('fixture')!=='lifecycle31')return null;
  if(u.protocol!=='http:'||u.hostname!=='127.0.0.1'||u.port!=='7645'||u.pathname!=='/kitchen.html')throw Error('Lifecycle fixture is available only on the existing local DEV kitchen.');
  const run=u.searchParams.get('run');
  if(!/^[a-z0-9][a-z0-9-]{7,63}$/.test(run||''))throw Error('Use a unique 8–64 character lowercase fixture run ID.');
  const prefix='offmenu-fixture-lifecycle31:'+run+':';
  return Object.freeze({run,prefix,storage(backing){return Object.freeze({getItem:key=>backing.getItem(prefix+key),setItem:(key,value)=>backing.setItem(prefix+key,String(value)),removeItem:key=>backing.removeItem(prefix+key)});}});
}
export function lifecycleFixtureState() {
  const foods=[['Rice','rice',500,'g'],['Eggs','egg',6,'count'],['Peas','peas',500,'g'],['Carrots','carrot',500,'g'],['Olive oil','olive oil',250,'ml']];
  const inventory=foods.map(([name,ingredient,quantity,unit],i)=>({id:'fixture-food-'+i,barcode:'local:fixture-food-'+i,name:name+' (synthetic fixture)',ingredient,quantity,unit,expires:null,location:{area:'Pantry',shelf:'Fixture shelf'},needsReview:false,amountBasis:'manual'}));
  const recipes=[['rice-peas','Rice and peas',[['rice',100,'g'],['peas',100,'g']]],['egg-carrot','Eggs and carrots',[['egg',2,'count'],['carrot',100,'g']]],['rice-carrot','Rice and carrots',[['rice',100,'g'],['carrot',100,'g'],['olive oil',10,'ml']]]].map(([id,title,items])=>({id:'fixture-'+id,title:title+' (synthetic)',servings:2,ingredients:items.map(([ingredient,quantity,unit])=>({ingredient,quantity,unit})),instructions:['Prepare these synthetic example ingredients.','Cook and portion for the fixture journey.'],source:'OffMenu local synthetic lifecycle fixture',license:'Synthetic test data; no external source or nutrition claim.'}));
  return {inventory,recipes,products:{},profile:{country:'AU',units:'metric',servings:2,members:[],feedback:{sound:false,vibration:false,screen:false,light:false,speech:false}},selections:[]};
}
export const fixtureIdentity=Object.freeze(Object.fromEntries(['getSettings','getUser','login','signup','logout','oauthLogin','handleAuthCallback','requestPasswordRecovery','updateUser','acceptInvite','refreshSession'].map(name=>[name,async()=>{throw Error('Account operations are unavailable in this synthetic fixture.');}])));
