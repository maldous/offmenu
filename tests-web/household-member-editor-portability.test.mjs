import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {parse} from 'acorn';
import {householdPortions} from '../public/household-model.js';

test('editing a household member preserves stored typed and scoped preferences',()=>{
 const source=readFileSync(new URL('../public/app.js',import.meta.url),'utf8');
 const ast=parse(source,{ecmaVersion:'latest',sourceType:'module'});
 const matches=ast.body.filter(n=>n.type==='ExpressionStatement'&&n.expression.type==='AssignmentExpression'&&source.slice(n.expression.left.start,n.expression.left.end)==="$('member-form').onsubmit");
 assert.equal(matches.length,1);
 const preferences={version:1,scope:{accountId:'generated-owner',memberId:'generated-a'},likes:['rice'],textures:['soft'],spice:'mild'};
 const member={id:'generated-a',name:'Generated A',portion:.5,advisors:['vegan'],avoid:[],restrictions:[{type:'preference',term:'peanut'},{type:'allergy',term:'milk'}],mealPreferences:preferences};
 const other={id:'generated-b',name:'Generated B',portion:1.5,advisors:['balanced'],avoid:['carrot'],restrictions:[]};
 const otherBefore=JSON.stringify(other),nodes=new Map();let stored;
 const values={'member-name':'Generated A renamed','member-portion':'.75','member-avoid':'coriander','member-allergies':'milk','member-intolerances':'','member-religious':'','member-age':'','member-height':'','member-weight':''};
 const $=id=>{if(!nodes.has(id))nodes.set(id,{value:values[id]??'',close(){}});return nodes.get(id);};
 const context={$,Object,Number,crypto:globalThis.crypto,editingMemberId:member.id,profile:{members:[member,other]},document:{querySelectorAll:()=>[{dataset:{advisor:'vegan'}}]},householdPortions,persistProfile(){stored=JSON.stringify(context.profile);},renderHousehold(){},findMeals(){}};
 vm.createContext(context);vm.runInContext(source.slice(matches[0].start,matches[0].end),context);
 $('member-form').onsubmit({preventDefault(){}});
 const saved=JSON.parse(stored),edited=saved.members.find(x=>x.id===member.id);
 assert.deepEqual(edited.mealPreferences,preferences);
 assert.ok(edited.restrictions.some(x=>x.type==='preference'&&x.term==='peanut'));
 assert.ok(edited.restrictions.some(x=>x.type==='allergy'&&x.term==='milk'));
 assert.equal(edited.name,'Generated A renamed');assert.equal(edited.portion,.75);assert.equal(saved.servings,2.25);
 assert.equal(JSON.stringify(saved.members.find(x=>x.id===other.id)),otherBefore);
});
