import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import {mountHelp} from '../../apps/web/assets/help.js';

function fixture(){
 const html=readFileSync(new URL('../../apps/web/assets/help.html',import.meta.url),'utf8');
 const matches=[...html.matchAll(/<article id="([^"]+)" data-alias="([^"]+)">([\s\S]*?)<\/article>/g)];
 const text=html=>html.replace(/<[^>]+>/g,' ').replaceAll('&amp;','&').replace(/\s+/g,' ').trim();
 function node(fields={}){
  return {children:[],listeners:{},textContent:'',value:'',hidden:true,
   replaceChildren(){this.children=[];},append(...next){this.children.push(...next);},
   addEventListener(name,subscriber){this.listeners[name]=subscriber;},
   focus(){this.focused=true;},setAttribute(){},...fields};
 }
 const articles=matches.map(([,id,alias,body])=>node({id,dataset:{alias},textContent:text(body),
  querySelector(tag){
   assert(['h2','p'].includes(tag));
   const value=body.match(new RegExp('<'+tag+'(?: [^>]*)?>(.*?)</'+tag+'>','s'))[1];
   return node({textContent:text(value)});
  }}));
 assert.deepEqual(articles.map(x=>x.id),['account-backup','recipe-import', 'scanner-options']);
 const elements=Object.fromEntries(['matches','feedback','finder','query','back','clear','topics','skip'].map(id=>[id,node()]));
 elements.topics.querySelectorAll=selector=>{assert.equal(selector,'article');return articles;};
 const d={createElement:()=>node(),querySelector(selector){return elements[selector.startsWith('#')?selector.slice(1):'skip'];}};
 const w={location:{hash:'',pathname:'/help.html'},addEventListener(){}};
 mountHelp(d,w);
 const resultLinks=()=>elements.matches.children[0].children.map(li=>li.children[0].href);
 const query=(value)=>{elements.query.value=value;elements.query.listeners.input();return resultLinks();};
 return {elements,resultLinks,query};
}

test('no-result suggestions from the mounted help search lead to the real bundled backup article',()=>{
 const {elements,resultLinks,query}=fixture();
 assert.deepEqual(query('unrelated fictional phrase'),[]);
 const help=elements.feedback.textContent;
 assert.match(help,/^No matching help topics[.]/);
 const next=[...help.matchAll(/“([^”]+)”/gu)].map(x=>x[1]);
 assert(next.length>0,'no-result guidance should offer a supported query');
 for(const term of next)assert.equal(query(term)[0],'#account-backup','Suggested term does not rank the backup article first: '+term);
 assert.equal(query('restore kitchen')[0],'#account-backup');
 assert.deepEqual(query('shopping list export'),[]);
 assert.deepEqual(query('print'),[]);
 elements.clear.listeners.click();
 assert.deepEqual(resultLinks(),['#account-backup','#recipe-import', '#scanner-options']);assert.equal(elements.query.value,'');assert.equal(elements.query.focused,true);
});

test('Account links directly to searchable English recipe-import recovery and exact notices',()=>{
 const account=readFileSync(new URL('../../apps/web/assets/index.html',import.meta.url),'utf8');
 const help=readFileSync(new URL('../../apps/web/assets/help.html',import.meta.url),'utf8');
 assert.match(account,/<label for="recipe-import"[^>]*>Import recipes \(offmenu JSON\)<\/label>[\s\S]*?<a href="\/help\.html#recipe-import" lang="en">Recipe import help \(English\)<\/a>/);
 assert.match(help,/<html lang="en" dir="ltr">/);
 const article=help.match(/<article id="recipe-import"[^>]*>([\s\S]*?)<\/article>/)?.[1];
 assert(article);
 assert.match(article,/<h2 tabindex="-1">/);
 for(const error of ['Choose a valid JSON file and try again.','File must be under 2 MB.','Import stopped: recipes with a matching ID contain different details. Existing recipes were kept.']){
  assert(article.includes(error));
 }
 const {query}=fixture();
 assert.equal(query('recipe import')[0],'#recipe-import');
 assert.equal(query('file must be under 2 mb')[0],'#recipe-import');
});


test('Scanner tools opens real English scanner Help without requiring the camera, a lookup, or a save',()=>{
 const scanner=readFileSync(new URL('../../apps/web/assets/shelf-scanner.html',import.meta.url),'utf8');
 const help=readFileSync(new URL('../../apps/web/assets/help.html',import.meta.url),'utf8');
 const dialog=scanner.match(/<dialog id="tools-dialog"[^>]*>([\s\S]*?)<\/dialog>/)?.[1];
 assert(dialog);
 const openers=[...scanner.matchAll(/<button id="scanner-options-help" type="button" aria-haspopup="dialog" aria-controls="scanner-options-help-dialog" lang="en" dir="ltr">Scanner options help \(English\)<\/button>/g)];
 assert.equal(openers.length,1);
 assert(dialog.includes(openers[0][0]));
 const preview=scanner.match(/<dialog id="scanner-options-help-dialog"[^>]*aria-labelledby="scanner-options-help-heading" lang="en" dir="ltr">([\s\S]*?)<\/dialog>/)?.[1];
 assert.match(preview,/<h2 id="scanner-options-help-heading" tabindex="-1" autofocus>Scanner options and camera recovery<\/h2>/);
 assert.match(preview,/<form method="dialog"><button id="scanner-options-help-close" type="submit">Back to scanner options<\/button><\/form>/);
 const anchors=[...scanner.matchAll(/<a href="\/help\.html#scanner-options">Read the full Scanner options guide \(English\)<\/a>/g)];
 assert.equal(anchors.length,1);
 assert(preview.includes(anchors[0][0]));
 assert.match(preview,/<b>Lookup unavailable<\/b> means OffMenu could not check the code[.] It does not mean the product was not found[.]/);
 assert.equal(dialog.includes('<button id="tools-close"'),true);
 assert.match(help,/<html lang="en" dir="ltr">/);
 const text=help.match(/<article id="scanner-options"[^>]*>([\s\S]*?)<\/article>/)?.[1];
 assert.match(text,/<h2 tabindex="-1">Scanner options and camera recovery<\/h2>/);
 assert.match(text,/keeping any leading zeros/);
 assert.match(text,/Lookup unavailable<\/b>, OffMenu could not check the code[.] This does not mean the product was not found[.] Nothing is added to your pantry[.]/);
 assert.match(text,/Choose <b>Cancel<\/b> to close the form without submitting[.]/);
 const {elements,query}=fixture();
 for(const value of ['scanner options','camera denied','type code','retry camera','lookup unavailable']){
   assert.deepEqual(query(value),['#scanner-options'],value);
   assert.equal(elements.feedback.textContent,'1 matching help topic.');
 }
 assert.deepEqual(query('shopping list export'),[]);
 assert.deepEqual(query('search by unknown invented topic'),[]);
 assert.equal(query('recipe import')[0],'#recipe-import');
});
