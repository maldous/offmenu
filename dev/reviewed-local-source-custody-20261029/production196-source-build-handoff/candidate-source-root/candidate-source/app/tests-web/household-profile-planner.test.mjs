import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {randomUUID} from 'node:crypto';
const app=process.env.OFFMENU_APP_SOURCE||new URL('../public/app.js',import.meta.url);
const source=fs.readFileSync(app,'utf8');
const piece=(from,to)=>{const start=source.indexOf(from),end=source.indexOf(to,start);assert.ok(start>=0&&end>start);return source.slice(start,end);};
const open=piece('function openMember(', '\nfor(const [id,title]of ADVISORS)');
const submit=piece("$('add-member').onclick=", "\n$('generate-day').onclick=");
const persist=piece('function persistProfile(){','\nfunction renderLocations');
const current=piece('function currentState(){','\nfunction applySynced');
function member(id='member-a',accountId='account-a') {return {id,name:'Synthetic '+id,portion:1,age:30,height:null,weight:null,avoid:[],advisors:['balanced'],restrictions:[{type:'preference',term:'mushroom'}],mealPreferences:{version:1,scope:{accountId,memberId:id},likes:['rice'],textures:['soft'],spice:'mild'}};}
function fixture(){
 const nodes=Object.fromEntries(['add-member','member-form','member-dialog','servings',...['name','age','height','weight','portion','avoid','allergies','intolerances','religious'].map(x=>'member-'+x)].map(id=>[id,{value:''}]));
 const advisors=['balanced','vegan','gluten-free','weight-loss'].map(advisor=>({dataset:{advisor},checked:false}));
 let writes=0,renders=0;const storage=new Map(),messages=[];
 nodes['member-form'].reset=()=>{for(const [id,node]of Object.entries(nodes))if(id.startsWith('member-')&&'value'in node)node.value='';for(const a of advisors)a.checked=false;};
 nodes['member-dialog'].showModal=()=>{nodes['member-dialog'].open=true;};nodes['member-dialog'].close=()=>{nodes['member-dialog'].open=false;};
 const ctx={editingMemberId:null,editingMemberScope:null,requestIdentity:{owner:'account-a'},PROFILE:'profile-a',profile:{country:'AU',units:'metric',servings:1,members:[member()],plan:[]},lots:[],recipes:[],products:{},selections:[],crypto:{randomUUID},$:id=>nodes[id],document:{querySelectorAll:selector=>selector.endsWith(':checked')?advisors.filter(a=>a.checked):advisors},localStorage:{setItem:(key,value)=>{writes++;storage.set(key,value);}},markDirty:()=>{},householdPortions:members=>members.reduce((n,m)=>n+m.portion,0),renderHousehold:()=>renders++,findMeals:()=>renders++,syncStatus:(...m)=>messages.push(m)};
 vm.runInNewContext(open+'\n'+submit+'\n'+persist+'\n'+current,ctx,{filename:String(app)});
 return {ctx,nodes,storage,messages,open:()=>ctx.openMember(ctx.profile.members[0]),add:()=>ctx.openMember(),submit:()=>nodes['member-form'].onsubmit({preventDefault(){}}),writes:()=>writes,renders:()=>renders};
}

test('same-account edit preserves scoped preferences and preference restrictions in serialized account snapshot',()=>{
 const f=fixture(),before=structuredClone(f.ctx.profile.members[0]);f.open();f.nodes['member-name'].value='Synthetic revised';f.nodes['member-avoid'].value='egg';f.nodes['member-portion'].value='2';f.submit();
 const state=JSON.parse(JSON.stringify(f.ctx.currentState()));assert.deepEqual(state.profile.members[0].mealPreferences,before.mealPreferences);assert.deepEqual(state.profile.members[0].restrictions,[{type:'preference',term:'mushroom'}]);assert.deepEqual(state.profile.members[0].avoid,['egg']);assert.equal(state.profile.servings,2);assert.equal(f.writes(),2);assert.equal(f.nodes['member-dialog'].open,false);
});
test('old-account editor must not append a member to newly selected account',()=>{
 const f=fixture();f.open();f.ctx.requestIdentity={owner:'account-b'};f.ctx.PROFILE='profile-b';f.ctx.profile={country:'AU',units:'metric',servings:1,members:[member('member-b','account-b')]};const before=JSON.stringify(f.ctx.profile);f.submit();
 assert.equal(JSON.stringify(f.ctx.profile),before);assert.equal(f.writes(),0);assert.equal(f.nodes['member-dialog'].open,false);
});
test('same ID in another account must not acquire former account form values',()=>{
 const f=fixture();f.open();f.nodes['member-name'].value='Synthetic stale edit';f.ctx.requestIdentity={owner:'account-b'};f.ctx.PROFILE='profile-b';f.ctx.profile={country:'AU',units:'metric',servings:1,members:[{...member('member-a','account-b'),name:'Synthetic account B member'}]};const before=JSON.stringify(f.ctx.profile);f.submit();assert.equal(JSON.stringify(f.ctx.profile),before);assert.equal(f.writes(),0);
});
test('same-account snapshot replacement must not resurrect removed household member',()=>{
 const f=fixture();f.open();f.ctx.profile={...f.ctx.profile,members:[]};const before=JSON.stringify(f.ctx.profile);f.submit();assert.equal(JSON.stringify(f.ctx.profile),before);assert.equal(f.writes(),0);
});
test('identity generation reset invalidates editor even for same account ID',()=>{
 const f=fixture();f.open();f.ctx.requestIdentity={owner:'account-a'};const before=JSON.stringify(f.ctx.profile);f.submit();assert.equal(JSON.stringify(f.ctx.profile),before);assert.equal(f.writes(),0);
});
test('new member editor also remains bound to account where it opened',()=>{
 const f=fixture();f.add();f.nodes['member-name'].value='Synthetic new member';f.ctx.requestIdentity={owner:'account-b'};f.ctx.PROFILE='profile-b';f.ctx.profile={country:'AU',units:'metric',servings:1,members:[]};f.submit();assert.equal(f.ctx.profile.members.length,0);assert.equal(f.writes(),0);
});
test('reopening after snapshot replacement permits current account edit',()=>{
 const f=fixture();f.open();f.ctx.requestIdentity={owner:'account-b'};f.ctx.PROFILE='profile-b';f.ctx.profile={country:'AU',units:'metric',servings:1,members:[member('member-b','account-b')]};f.open();f.nodes['member-name'].value='Synthetic current edit';f.submit();assert.equal(f.ctx.profile.members[0].name,'Synthetic current edit');assert.equal(f.writes(),2);assert.ok(f.storage.has('profile-b'));
});
test('cancelled editor cannot submit retained form values',()=>{const f=fixture();f.open();f.nodes['member-dialog'].close();const before=JSON.stringify(f.ctx.profile);f.submit();assert.equal(JSON.stringify(f.ctx.profile),before);assert.equal(f.writes(),0);});
test('duplicate submission after successful save does not write twice',()=>{const f=fixture();f.open();f.submit();const before=JSON.stringify(f.ctx.profile);f.submit();assert.equal(JSON.stringify(f.ctx.profile),before);assert.equal(f.writes(),2);});
test('rejected stale editor is cleared and can be reopened from current snapshot',()=>{const f=fixture();f.open();f.ctx.profile={...f.ctx.profile,members:[{...member(),name:'Synthetic replacement'}]};f.submit();assert.equal(f.nodes['member-name'].value,'');f.open();assert.equal(f.nodes['member-name'].value,'Synthetic replacement');f.submit();assert.equal(f.writes(),2);});

const {generateHouseholdDay,groupSuitability,rankedMenus}=await import('../public/household-model.js');
const {planSummary}=await import('../public/menu-model.js');
const {validateAccountMealState}=await import('../cloud/meal-preference-owner20.mjs');
const {kitchenProjection,applyKitchen}=await import('../public/sync-model.js');
const recipe=(id,ingredient,quantity=100)=>({id,title:'Synthetic '+id,source:'synthetic test',license:'synthetic fixture',servings:1,instructions:['Synthetic instruction.'],ingredients:[{ingredient,quantity,unit:'g'}]});
const stock=(quantity=150)=>({id:'synthetic-rice-lot',barcode:'local:rice',name:'Synthetic rice',ingredient:'rice',quantity,unit:'g',needsReview:false});
const date='2026-10-28';

test('actual edit-to-plan caller preserves account custody and creates honest cumulative shopping gaps without consuming stock',()=>{
 const f=fixture();f.ctx.recipes=[recipe('rice','rice'),recipe('egg','egg')];f.ctx.lots=[stock()];f.open();f.nodes['member-avoid'].value='egg';f.submit();
 const saved=validateAccountMealState(JSON.parse(JSON.stringify(f.ctx.currentState())),'account-a');assert.deepEqual(saved.profile.members[0].mealPreferences,member().mealPreferences);assert.deepEqual(saved.profile.members[0].avoid,['egg']);
 f.ctx.profile=saved.profile;f.ctx.generateHouseholdDay=generateHouseholdDay;f.ctx.unexpiredInventory=()=>f.ctx.lots;f.ctx.renderPlan=()=>{};f.ctx.setLocalizedText=()=>{};Object.assign(f.nodes,{'generate-day':{},'plan-date':{value:date},'plan-slot':{value:'Dinner'},'household-plan-note':{}});
 vm.runInNewContext(piece("$('generate-day').onclick=", "\n$('use-pantry').onchange="),f.ctx);const before=JSON.stringify(f.ctx.lots);f.nodes['generate-day'].onclick();f.nodes['generate-day'].onclick();
 const plan=JSON.parse(JSON.stringify(f.ctx.profile.plan));assert.equal(plan.length,2);assert.ok(plan.every(p=>p.recipeId==='rice'&&p.memberIds[0]==='member-a'));
 const summary=planSummary(plan,f.ctx.recipes,f.ctx.lots,{},[date]);assert.deepEqual(summary.missing,[{ingredient:'rice',unit:'g',quantity:50}]);assert.equal(summary.requirements[0].quantity,200);assert.equal(summary.totals.proteins_100g.known,0);assert.ok(summary.totals.proteins_100g.total>0);assert.equal(JSON.stringify(f.ctx.lots),before);
 const cloud=validateAccountMealState(JSON.parse(JSON.stringify(f.ctx.currentState())),'account-a');assert.equal(cloud.profile.plan.length,2);assert.deepEqual(cloud.profile.members[0].mealPreferences,member().mealPreferences);assert.throws(()=>validateAccountMealState(JSON.parse(JSON.stringify(f.ctx.currentState())),'account-b'),/scope\/version mismatch/);
});
test('existing shared projection excludes private household preferences and apply preserves private membership',()=>{
 const state={inventory:[stock()],products:{},recipes:[recipe('rice','rice')],selections:[],profile:{country:'AU',units:'metric',servings:1,members:[member()],plan:[{id:'p',recipeId:'rice',date,slot:'Dinner',servings:1,memberIds:['member-a'],adjustments:['Synthetic preference note']}]}};
 const projected=kitchenProjection(state);assert.equal(projected.profile.members,undefined);assert.deepEqual(projected.profile.plan[0].memberIds,[]);assert.deepEqual(projected.profile.plan[0].adjustments,[]);assert.equal(JSON.stringify(projected).includes('mealPreferences'),false);assert.deepEqual(applyKitchen(state,projected).profile.members,state.profile.members);
});
test('separate existing avoidance conflicts yield individually assigned household meals',()=>{
 const members=[{...member('a'),avoid:['egg']},{...member('b'),avoid:['rice']}],plan=generateHouseholdDay([recipe('rice','rice'),recipe('egg','egg')],[stock(300)],{},members,date);assert.equal(plan.length,2);assert.deepEqual(plan.map(p=>[p.recipeId,p.memberIds,p.servings]),[['rice',['a'],1],['egg',['b'],1]]);
});
test('unknown ingredient, package restriction and minor or missing-age weight-loss holds remain unrelaxed',()=>{
 assert.equal(groupSuitability(recipe('unqualified','synthetic unknown ingredient'),[member()]).automaticSelection,false);
 assert.equal(groupSuitability(recipe('rice','rice'),[{...member(),restrictions:[{type:'allergy',term:'peanut'}]}]).automaticSelection,false);
 for(const age of [null,17])assert.equal(groupSuitability(recipe('rice','rice'),[{...member(),age,advisors:['weight-loss']}]).automaticSelection,false);
 assert.equal(groupSuitability(recipe('egg','egg'),[{...member(),advisors:['vegan']}]).compatible,false);
});
test('unqualified positive taste metadata is retained but not silently turned into planner evidence',()=>{
 const recipes=[recipe('rice','rice'),recipe('egg','egg')],a=member(),b={...member(),mealPreferences:{...member().mealPreferences,likes:['egg'],textures:['crisp'],spice:'hot'}};
 const rank=m=>rankedMenus(recipes,[],{},[m],1,date).map(r=>({id:r.id,score:r.score}));assert.deepEqual(rank(a),rank(b));
});
