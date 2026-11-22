import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
const web=new URL('../../apps/web/',import.meta.url);
const app=readFileSync(new URL('src/app.js',web),'utf8');
const html=readFileSync(new URL('assets/index.html',web),'utf8');

test('a coverage note supplements visible matches without hiding results or repeating empty copy',()=>{
 const note={dataset:{},hidden:true}, sets=[];
 const c={$:id=>{assert.equal(id,'recipe-availability-note');return note;},setLocalizedText:(target,message)=>{assert.equal(target,note);sets.push(message);}};
 const start=app.indexOf('function renderRecipeAvailabilityNote('),end=app.indexOf('function findMeals(', start);
 runInNewContext('let recipeAvailability;'+app.slice(start,end)+'globalThis.render=(availability,matches)=>{recipeAvailability=availability;renderRecipeAvailabilityNote(matches)};',c);
 assert.match(html,/id="recipe-availability-note"[^>]*role="status" hidden/);
 assert.match(app,/renderRecipeAvailabilityNote\(rows.length>0\);if\(!rows.length\)/);
 c.render('partial',true);assert.equal(note.hidden,false);assert.match(sets.at(-1),/Some recipes did not load/);
 c.render('partial',true);assert.equal(sets.length,1);
 c.render('unavailable',true);assert.match(sets.at(-1),/already available to this kitchen/);
 c.render('partial',false);assert.equal(note.hidden,true);
 c.render('loaded',true);assert.equal(note.hidden,true);
 c.render('local-only',true);assert.equal(note.hidden,true);
});
