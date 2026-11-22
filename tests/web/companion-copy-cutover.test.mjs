import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync as read} from 'node:fs';
const source=read(new URL('../../apps/web/src/insights-ui.js',import.meta.url),'utf8');
const start=source.indexOf('const shoppingText='), end=source.indexOf('\n};',source.indexOf("$('copy-shopping').onclick=",start))+3;
assert.ok(start>=0&&end>start);
function bound({share,clipboard}){
 const nodes=new Map(['share-shopping','copy-shopping','integration-notice'].map(k=>[k,{}]));
 const $=id=>nodes.get(id),navigator={share,clipboard},setLocalizedText=(el,msg)=>el.text=msg;
 const items=()=>[{name:'Synthetic rice',amount:'2 kg',checked:false},{name:'Skip me',amount:'1',checked:true}];
 eval(source.slice(start,end));
 return {share:$('share-shopping'),copy:$('copy-shopping'),notice:$('integration-notice')};
}
test('share is hidden without API; clipboard is only called on explicit copy',async()=>{
 const writes=[],f=bound({clipboard:{writeText:async text=>writes.push(text)}});
 assert.equal(f.share.hidden,true);assert.equal(f.copy.hidden,false);assert.deepEqual(writes,[]);
 await f.copy.onclick();assert.equal(writes.length,1);assert.match(writes[0],/Synthetic rice/);assert.doesNotMatch(writes[0],/Skip me/);
});
test('cancelled share does not fall back to clipboard; absent clipboard hides only copy',async()=>{
 const writes=[],share=async()=>{throw {name:'AbortError'};};
 const f=bound({share,clipboard:{writeText:async x=>writes.push(x)}});await f.share.onclick();
 assert.deepEqual(writes,[]);assert.equal(f.notice.text,undefined);
 assert.equal(bound({share}).copy.hidden,true);
});

test('separate native buttons name only their explicit action',()=>{
 const html=read(new URL('../../apps/web/assets/index.html',import.meta.url),'utf8');
 const share=html.match(/<button[^>]*id="share-shopping"[^>]*>[^<]*<\/button>/)?.[0];
 const copy=html.match(/<button[^>]*id="copy-shopping"[^>]*>[^<]*<\/button>/)?.[0];
 assert.match(share, /data-i18n="Share shopping list">Share shopping list<\/button>/);
 assert.match(copy, /data-i18n="Copy shopping list">Copy shopping list<\/button>/);
 assert.match(html, /id="integration-notice" role="status"/);
});
