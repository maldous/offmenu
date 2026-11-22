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
 assert.deepEqual(articles.map(x=>x.id),['account-backup']);
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
 for(const term of next)assert.deepEqual(query(term),['#account-backup'],'Suggested term has no relevant help result: '+term);
 assert.deepEqual(query('restore kitchen'),['#account-backup']);
 assert.deepEqual(query('shopping'),[]);
 assert.deepEqual(query('print'),[]);
 elements.clear.listeners.click();
 assert.deepEqual(resultLinks(),['#account-backup']);assert.equal(elements.query.value,'');assert.equal(elements.query.focused,true);
});
