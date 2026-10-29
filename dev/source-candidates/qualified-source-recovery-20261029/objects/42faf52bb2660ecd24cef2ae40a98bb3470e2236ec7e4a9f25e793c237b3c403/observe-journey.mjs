// One fabricated local model journey and three observed contract inconsistencies.
// Not a browser/device/provider/clinical/content test or release gate.
import vm from 'node:vm';
import {execFileSync} from 'node:child_process';
import {writeFileSync} from 'node:fs';
import {posix} from 'node:path';
import {createHash,webcrypto} from 'node:crypto';
const [repo,revision,out]=process.argv.slice(2);
if(!repo||!revision||!out)throw Error('Supply repo, immutable revision and external output');
const env=Object.fromEntries(Object.entries(process.env).filter(([k])=>!k.startsWith('GIT_')));
env.GIT_OPTIONAL_LOCKS='0';
const rev=execFileSync('git',['rev-parse','--verify',revision+'^{commit}'],{cwd:repo,env,encoding:'utf8'}).trim();
const context=vm.createContext({structuredClone,crypto:webcrypto,URL});
const modules=new Map(),pins=[];
function load(name) {
  if(modules.has(name))return modules.get(name);
  if(name==='public/i18n.js') {
    const module=new vm.SyntheticModule(['t','getLanguage'],function(){
      this.setExport('t',(s,values={})=>String(s).replace(/\{([^}]+)\}/g,(m,k)=>values[k]??m));
      this.setExport('getLanguage',()=> 'en');
    },{context,identifier:name});modules.set(name,module);return module;
  }
  const source=execFileSync('git',['show',rev+':'+name],{cwd:repo,env,encoding:'utf8',maxBuffer:4*1024*1024,timeout:10000});
  pins.push({path:name,sha256:createHash('sha256').update(source).digest('hex')});
  const module=new vm.SourceTextModule(source,{context,identifier:name});modules.set(name,module);return module;
}
const roots=['public/household-model.js','public/cooking-model.js','public/integrations.js','cloud/state.mjs'];
for(const name of roots) {
  const module=load(name);
  if(module.status==='unlinked')await module.link((specifier,from)=>{
    if(!specifier.startsWith('.'))throw Error('External dependency refused');
    return load(posix.normalize(posix.join(posix.dirname(from.identifier),specifier)));
  });
  if(module.status!=='evaluated')await module.evaluate({timeout:1000});
}
for(const name of roots)for(const [key,value]of Object.entries(load(name).namespace))context[key]=value;
context.matchMeals=load('public/model.js').namespace.matchMeals;
context.validateLot=load('public/model.js').namespace.validateLot;
const observation=vm.runInContext(`(() => {
  const date='2026-10-17';
  const makeLot=(ingredient,quantity,unit,index,expires=null)=>validateLot({id:'lot-'+index,barcode:'local:synthetic-'+index,name:'Synthetic '+ingredient,ingredient,quantity,unit,expires,needsReview:false});
  const stock=[makeLot('rice',500,'g',1),makeLot('peas',300,'g',2),makeLot('carrot',200,'g',3),makeLot('egg',4,'count',4),makeLot('olive oil',50,'ml',5)];
  const ingredient=(ingredient,quantity,unit='g')=>({ingredient,quantity,unit});
  const recipe=(id,ingredients)=>({id,title:'Synthetic '+id,servings:2,ingredients,instructions:['Fabricated model fixture; not cooking guidance.'],source:'synthetic:lifecycle',license:'synthetic-fixture-only'});
  const recipes=[recipe('rice-peas',[ingredient('rice',100),ingredient('peas',100)]),recipe('rice-carrot',[ingredient('rice',100),ingredient('carrot',100)]),recipe('egg-rice',[ingredient('rice',100),ingredient('egg',2,'count'),ingredient('olive oil',10,'ml')])];
  const ready=rankedMenus(recipes,stock,{},[],2,date).map(r=>({id:r.id,status:r.status}));
  const profile={servings:2,country:'',units:'metric',plan:[{id:'synthetic-plan',recipeId:recipes[0].id,date,slot:'Dinner',servings:2}],shopping:[{id:'synthetic-extra',name:'Synthetic extra',amount:'choose quantity',checked:false}]};
  const shopping=shoppingItems(profile,recipes,stock,{},date,true);
  const cooked=cookMeal({recipe:recipes[0],inventory:stock,products:{},servings:2,date,planId:'synthetic-plan',batches:[],mutationId:'synthetic-cook'});
  const served=serveBatch({batch:cooked.batch,inventory:cooked.inventory,portions:1,completion:50,remainder:'saved',memberId:'',date,eventId:'synthetic-serve'});
  const state=validateState({inventory:served.inventory,products:{},recipes,profile:{...profile,batches:[served.batch],history:[served.log]},selections:[]});
  const duplicate=serveBatch({batch:served.batch,inventory:served.inventory,portions:1,completion:50,remainder:'saved',memberId:'',date,eventId:'synthetic-serve'});
  const zeroLot=makeLot('rice',null,'g','unknown');
  const reviewRecipe={...recipes[0],servingsUnknown:true,needsReview:true};
  const reviewStatus=matchMeals(stock,[reviewRecipe],2,date)[0];
  const onlyRice=[recipe('only-rice',[ingredient('rice',100)])];
  const validOnly=[makeLot('rice',100,'g','live')];
  const expiredFirst=[makeLot('rice',1000,'g','expired','2026-10-16'),...validOnly];
  const expected=pantryDuration(onlyRice,validOnly,[],2,date);
  const actual=pantryDuration(onlyRice,expiredFirst,[],2,date);
  return {fixture:'Five fabricated food lots, three fabricated recipe choices, one plan/list/cook/serve/validated-save path',
    journey:{ready,shopping,cook:{duplicate:cooked.duplicate,remaining:cooked.batch.remaining,rawRice:cooked.inventory.find(l=>l.id==='lot-1').quantity},
      serve:{remaining:served.batch.remaining,eaten:served.log.servings,saved:served.batch.events[0].saved},
      validatedSave:{inventoryCount:state.inventory.length,historyCount:state.profile.history.length,shoppingExtraCount:state.profile.shopping.length,batches:state.profile.batches.length},duplicateServe:{duplicate:duplicate.duplicate,unchangedRemaining:duplicate.batch.remaining}},
    observations:[
      {id:'LH31-Q01',case:'Null quantity enters validateLot',inputQuantity:null,actualQuantity:zeroLot.quantity,problem:'Missing amount coerced to known zero'},
      {id:'LH31-Q02',case:'Review-only recipe with unknown servings enters matchMeals',servingsUnknown:reviewRecipe.servingsUnknown,needsReview:reviewRecipe.needsReview,actualStatus:reviewStatus.status,unknownIngredients:reviewStatus.unknown.length,problem:'Ready status ignores unknown recipe yield/review flag; app show-review path can expose this'},
      {id:'LH31-Q03',case:'Expired rice precedes enough live rice for exactly one meal',liveRice:100,expiredRice:1000,validOnlyMeals:expected.meals,withExpiredFirstMeals:actual.meals,problem:'Duration deduction consumes expired stock despite readiness excluding it; coverage is inflated'}]};
})()`,context,{timeout:3000});
const result={kind:'Proportionate observation of actual pure-model code, not broad tests or acceptance',revision:rev,sourcePins:pins,
  presentationStub:'Only i18n t/getLanguage replaced by deterministic text functions; no DOM/account/provider/real private data',
  scope:'Model functions exercised; browser persistence, sync transport, cameras and provider runtime not executed',...JSON.parse(JSON.stringify(observation))};
writeFileSync(out,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
