import test from 'node:test';
import assert from 'node:assert/strict';
import {memberSuitability,generateHouseholdDay} from '../public/household-model.js';

test('an unknown ingredient stays review-required for an unrestricted household member',()=>{
 const members=[
  {id:'synthetic-a',name:'Synthetic A',portion:.5,advisors:['vegan'],avoid:[],restrictions:[]},
  {id:'synthetic-b',name:'Synthetic B',portion:1.5,advisors:['balanced'],avoid:[],restrictions:[]}
 ];
 const before=JSON.stringify(members);
 const recipe={id:'synthetic-unmapped',title:'Generated unmapped ingredient',servings:1,ingredients:[{ingredient:'unmapped sauce W62',quantity:20,unit:'g'}]};
 const fit=memberSuitability(recipe,members[1]);
 assert.equal(fit.status,'needs-check');
 assert.equal(fit.automaticSelection,false);
 assert.ok(fit.checks.some(x=>x.includes('Unknown ingredient evidence: unmapped sauce W62')));
 assert.deepEqual(generateHouseholdDay([recipe],[],{},members,'2026-10-26'),[]);
 const known={...recipe,id:'synthetic-known',ingredients:[{ingredient:'rice',quantity:20,unit:'g'}]};
 assert.equal(memberSuitability(known,members[1]).automaticSelection,true);
 assert.equal(JSON.stringify(members),before);
});
