import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {parse} from 'acorn';
import {updateAccountMealPreferences,validateMealPreferences} from '../../apps/web/server/meal-preference-owner20.mjs';
import {householdPortions} from '../../apps/web/src/household-model.js';

const source=readFileSync(new URL('../../apps/web/src/app.js',import.meta.url),'utf8');
const html=readFileSync(new URL('../../apps/web/assets/index.html',import.meta.url),'utf8');
const ast=parse(source,{ecmaVersion:'latest',sourceType:'module'});
const plain=value=>JSON.parse(JSON.stringify(value));
const preferences=()=>({version:1,scope:{accountId:'owner',memberId:'member'},likes:['Rice'],textures:['crunchy'],spice:'mild'});
function fixture({taste=true,user={id:'owner'},shared=false,demo=false}={}){
 const nodes=new Map(),writes=[],calls=[];
 const $=id=>{if(!nodes.has(id))nodes.set(id,{value:'',hidden:false,disabled:false,textContent:'',reset(){},showModal(){this.open=true;},close(){this.open=false;}});return nodes.get(id);};
 const member={id:'member',name:'Alex',portion:1,avoid:['cilantro'],advisors:['balanced'],age:30,height:170,weight:60,
  restrictions:[{type:'allergy',term:'peanut',certainty:'declared',source:{note:'keep'}},{type:'preference',term:'mushrooms',unknown:true}],unknown:{nested:['retain']},...(taste?{mealPreferences:preferences()}:{})};
 const other={...plain(member),id:'other'};delete other.mealPreferences;
 const profile={country:'AU',units:'metric',servings:2,members:[member,other],unknown:{keep:true}};
 const advisors=[{dataset:{advisor:'balanced'},checked:false}];
 $('member-close').dataset={close:'member-dialog'};
 const context={$,profile,user,demoMode:demo,requestIdentity:{owner:user?.id??null},editingMemberId:null,
  sharing:{active:()=>shared},document:{querySelectorAll:selector=>selector==='[data-close]'?[$('member-close')]:selector.includes(':checked')?advisors.filter(x=>x.checked):advisors},
  t:x=>x,setLocalizedText:(node,text)=>{node.textContent=text;},crypto:{randomUUID:()=> 'new-member'},householdPortions,
  currentState:()=>({inventory:[],products:{},recipes:[],selections:[],profile:context.profile}),
  // Browser and imported modules share a realm. Marshal synthetic VM inputs to
  // that realm so the real validator's plain-JSON checks stay meaningful.
  updateAccountMealPreferences:(state,scope,action)=>{calls.push(plain({scope,action}));return updateAccountMealPreferences(plain(state),plain(scope),plain(action));},
  persistProfile:()=>writes.push(plain(context.profile)),renderHousehold(){},findMeals(){}};
 vm.createContext(context);
 for(const node of ast.body){
  const text=source.slice(node.start,node.end);
  if(node.type==='ForOfStatement'&&text.startsWith("for(const b of document.querySelectorAll('[data-close]'))")||
     node.type==='VariableDeclaration'&&node.declarations.some(d=>d.id.name==='memberEditor')||
     node.type==='FunctionDeclaration'&&node.id.name==='openMember'||
     node.type==='ExpressionStatement'&&(text.startsWith("$('member-reset-taste').onclick=")||text.startsWith("$('add-member').onclick=")||text.startsWith("$('member-form').onsubmit=")))vm.runInContext(text,context);
 }
 const open=()=>context.openMember(context.profile.members.find(m=>m.id==='member'));
 const save=()=>$('member-form').onsubmit({preventDefault(){}});
 return {context,$,member,other,profile,writes,calls,open,save,setShared:value=>{shared=value;},taste:()=>context.profile.members.find(m=>m.id==='member')?.mealPreferences};
}

test('real member Save validates explicit taste scope and preserves unrelated metadata and restrictions',()=>{
 const f=fixture();f.open();assert.equal(f.$('member-taste').disabled,false);
 f.$('member-likes').value='Rice, noodles';f.$('member-textures').value='soft, crisp';f.$('member-spice').value='hot';f.save();
 assert.equal(f.calls.length,1);assert.deepEqual(f.calls[0].scope,{accountId:'owner',memberId:'member',consent:true});
 assert.deepEqual(f.taste(),validateMealPreferences({...preferences(),likes:['Rice','noodles'],textures:['soft','crisp'],spice:'hot'},'owner','member'));
 const member=f.context.profile.members.find(m=>m.id==='member');
 assert.deepEqual(member.unknown,f.member.unknown);assert.deepEqual(member.restrictions,f.member.restrictions);
 assert.deepEqual(plain(member.avoid),f.member.avoid);assert.deepEqual(plain(member.advisors),f.member.advisors);
 assert.equal(f.context.profile.unknown,f.profile.unknown);assert.equal(f.context.profile.members.find(m=>m.id==='other'),f.other);
 assert.equal(f.writes.length,2);assert.equal(f.$('member-dialog').open,false);
});

test('Reset only changes draft; subsequent Save clears taste while keeping restrictions and metadata',()=>{
 const f=fixture();f.open();const before=plain(f.profile);f.$('member-reset-taste').onclick();
 assert.deepEqual(f.profile,before);assert.equal(f.writes.length,0);assert.equal(f.calls.length,0);
 for(const key of ['likes','textures','spice'])assert.equal(f.$('member-'+key).value,'');
 f.save();assert.deepEqual(f.taste(),{version:1,scope:{accountId:'owner',memberId:'member'},likes:[],textures:[],spice:null});
 assert.deepEqual(f.context.profile.members.find(m=>m.id==='member').restrictions,f.member.restrictions);
 assert.deepEqual(f.context.profile.members.find(m=>m.id==='member').unknown,f.member.unknown);
});

test('closing or cancelling edited/reset drafts leaves persisted taste unchanged and reopen reloads it',()=>{
 for(const reset of [false,true]){
  const f=fixture();f.open();const before=plain(f.profile);
  f.$('member-likes').value='changed';if(reset)f.$('member-reset-taste').onclick();
  f.$('member-close').onclick();assert.deepEqual(f.profile,before);assert.equal(f.writes.length,0);assert.equal(f.calls.length,0);
  f.open();assert.equal(f.$('member-likes').value,'Rice');assert.equal(f.$('member-spice').value,'mild');
 }
});

test('partial field edits keep other tastes; unknown null and explicit none stay distinct',()=>{
 for(const [key,value]of [['likes','pasta'],['textures','chewy'],['spice','none'],['spice','']]){
  const f=fixture();f.open();f.$('member-'+key).value=value;f.save();
  const expected={...preferences(),[key]:key==='spice'?value||null:[value]};assert.deepEqual(f.taste(),expected);
 }
});

test('partial Save preserves untouched comma-containing terms and source spelling exactly',()=>{
 for(const [key,value,patch]of [['spice','hot',{spice:'hot'}],['likes','pasta',{likes:['pasta']}],['textures','chewy',{textures:['chewy']}],['name','Renamed',null]]){
  const f=fixture();Object.assign(f.member.mealPreferences,{likes:['rice, noodles'],textures:[' crisp, soft ']});
  const before=plain(f.taste());f.open();f.$('member-'+key).value=value;f.save();
  assert.deepEqual(f.taste(),{...before,...patch});assert.equal(f.writes.length,2);
  assert.deepEqual(f.calls.map(call=>call.action),patch?[{type:'edit',patch}]:[]);
 }
});

test('Reset clears comma-containing terms and subsequent deliberate draft edits still Save',()=>{
 for(const editAfterReset of [false,true]){
  const f=fixture();Object.assign(f.member.mealPreferences,{likes:['rice, noodles'],textures:['crisp, soft']});
  const before=plain(f.taste());f.open();f.$('member-reset-taste').onclick();
  assert.deepEqual(f.taste(),before);assert.equal(f.writes.length,0);assert.equal(f.calls.length,0);
  if(editAfterReset){f.$('member-likes').value='rice, noodles';f.$('member-spice').value='hot';}
  f.save();const patch={likes:editAfterReset?['rice','noodles']:[],textures:[],spice:editAfterReset?'hot':null};
  assert.deepEqual(f.taste(),{...before,...patch});assert.equal(f.writes.length,2);
  assert.deepEqual(f.calls[0].action,{type:'edit',patch});
 }
});

test('ordinary Save keeps legacy absence and existing fields; no safety field becomes taste',()=>{
 for(const taste of [false,true]){
  const f=fixture({taste});f.open();f.$('member-name').value='Renamed';f.$('member-age').value='31';f.$('member-avoid').value='onion';f.$('member-allergies').value='egg';f.save();
  const member=f.context.profile.members.find(m=>m.id==='member');
  assert.equal(member.name,'Renamed');assert.equal(member.age,31);assert.deepEqual(plain(member.avoid),['onion']);
  assert.deepEqual(plain(member.restrictions).filter(r=>r.type==='allergy'),[{type:'allergy',term:'egg'}]);
  assert.equal(Object.hasOwn(member,'mealPreferences'),taste);assert.equal(f.calls.length,0);
  if(taste)assert.deepEqual(f.taste(),preferences());
 }
});

test('intentional reset of legacy absence creates an empty scoped taste only on Save',()=>{
 const f=fixture({taste:false});f.open();f.$('member-reset-taste').onclick();assert.equal(f.taste(),undefined);f.save();
 assert.equal(f.calls.length,1);assert.deepEqual(f.taste().likes,[]);assert.equal(f.taste().spice,null);
});

test('term limits and invalid spice reject before writes, including unrelated draft changes',()=>{
 for(const [key,value]of [['likes',Array(33).fill('rice').join(',')],['textures',Array(33).fill('soft').join(',')],['likes','x'.repeat(101)],['textures','x'.repeat(101)],['spice','fiery']]){
  const f=fixture();f.open();const before=plain(f.profile);f.$('member-'+key).value=value;f.$('member-name').value='Not saved';f.save();
  assert.deepEqual(f.profile,before);assert.equal(f.writes.length,0);assert.match(f.$('member-notice').textContent,/Invalid/);assert.equal(f.$('member-dialog').open,true);
 }
 const f=fixture();f.open();for(const key of ['likes','textures'])f.$('member-'+key).value=Array(32).fill('x'.repeat(100)).join(',');f.save();
 assert.equal(f.taste().likes.length,32);assert.equal(f.taste().textures[0].length,100);assert.equal(f.writes.length,2);
});

test('stale account, member and scope reject Save and Reset without writes',()=>{
 const changes=[
  f=>{f.context.requestIdentity={owner:'owner'};},
  f=>{f.context.user={id:'different'};},
  f=>{f.context.requestIdentity.owner='different';},
  f=>{f.context.profile.members=f.context.profile.members.filter(m=>m.id!=='member');},
  f=>{f.context.profile.members=f.context.profile.members.map(m=>m.id==='member'?plain(m):m);},
  f=>{f.context.editingMemberId='other';},
  f=>{f.member.id='renamed';},
  f=>{f.context.demoMode=true;},
  f=>f.setShared(true),
  f=>{f.context.user=null;},
 ];
 for(const change of changes)for(const action of ['save','reset','ordinary']){
  const f=fixture();f.open();if(action!=='ordinary')f.$('member-likes').value='pasta';change(f);const before=plain(f.context.profile);
  if(action!=='reset')f.save();else f.$('member-reset-taste').onclick();
  assert.deepEqual(f.context.profile,before);assert.equal(f.writes.length,0);assert.equal(f.calls.length,0);assert.ok(f.$('member-notice').textContent);
 }
});

test('new member, guest, shared and demo keep ordinary behavior and cannot create tastes',()=>{
 for(const options of [{user:null},{shared:true},{demo:true},{user:{id:'owner'},newMember:true}]){
  const f=fixture({...options,taste:false});if(options.newMember)f.$('add-member').onclick();else f.open();
  assert.equal(f.$('member-taste').hidden,true);assert.equal(f.$('member-taste').disabled,true);
  f.$('member-reset-taste').onclick();assert.equal(f.calls.length,0);assert.equal(f.writes.length,0);
  f.$('member-name').value='Ordinary member';f.save();assert.equal(f.writes.length,2);assert.equal(f.calls.length,0);
  assert.ok(f.context.profile.members.every(m=>!Object.hasOwn(m,'mealPreferences')));
 }
 for(const options of [{user:null},{shared:true},{demo:true},{newMember:true}]){
  const f=fixture({...options,taste:false});if(options.newMember)f.$('add-member').onclick();else f.open();
  f.$('member-likes').value='tampered';f.save();assert.equal(f.writes.length,0);assert.equal(f.calls.length,0);
 }
});

test('scope change invalidates an open editor and controls remain in existing localized dialog',()=>{
 const sharingSetup=ast.body.find(n=>n.type==='VariableDeclaration'&&n.declarations.some(d=>d.id.name==='sharing'));
 const callback=sharingSetup.declarations[0].init.arguments[0].properties.find(p=>p.key.name==='onScopeChange').value;
 const f=fixture();f.open();
 Object.assign(f.context,{autoSync:{resume(){}},sharing:{active:()=>false,canWrite:()=>true}});
 f.$('workspace').classList={toggle(){}};
 vm.runInContext('('+source.slice(callback.start,callback.end)+')()',f.context);
 f.save();assert.equal(f.writes.length,0);assert.match(f.$('member-notice').textContent,/changed/);
 const dialog=html.slice(html.indexOf('<dialog id="member-dialog"'),html.indexOf('</dialog>',html.indexOf('<dialog id="member-dialog"')));
 for(const id of ['member-likes','member-textures','member-spice','member-reset-taste'])assert.ok(dialog.includes('id="'+id+'"'));
 assert.match(dialog,/<button id="member-reset-taste" type="button"/);
 assert.match(dialog,/data-i18n="Reset taste preferences"/);assert.match(dialog,/option value=""/);assert.match(dialog,/option value="none"/);
});
