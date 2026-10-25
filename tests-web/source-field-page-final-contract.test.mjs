import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const modulePath=new URL('../public/source-field-page-presenter.js',import.meta.url);
assert.equal(createHash('sha256').update(readFileSync(modulePath)).digest('hex'),'347a6ce9c7ae1963465113af583aabaa6ce31978d10bc3b166c572c8a540b9c3');
const {mountSourceFieldPagePresenter}=await import(modulePath);
const {cases}=JSON.parse(readFileSync(new URL('./fixtures/full-field-paging/final-node-presenter-fixtures.json',import.meta.url)));
// Minimal text-only DOM fixture matching the frozen presenter's supported surface.
class Node {
  constructor(tag,doc){this.tagName=tag;this.ownerDocument=doc;this.children=[];this._text='';this.hidden=false;this.disabled=false;}
  set textContent(x){this._text=String(x);this.children=[];}
  get textContent(){return this._text+this.children.map(x=>x.textContent).join('');}
  append(...x){this.children.push(...x);}
  replaceChildren(...x){this._text='';this.children=[...x];}
  set innerHTML(_){throw Error('HTML insertion forbidden');}
}
function dom(){const doc={createElement:tag=>new Node(tag,doc)};return new Node('root',doc);}
function buttons(root){const out=[];function visit(node){if(node.tagName==='button')out.push(node);node.children.forEach(visit);}visit(root);return out;}
const tick=()=>new Promise(resolve=>setImmediate(resolve));

for(const fixture of cases) test('actual final reader → frozen presenter: '+fixture.name,async()=>{
  const root=dom(),calls=[];
  const presenter=mountSourceFieldPagePresenter(root,{generation:fixture.first.binding.generation,readPage:async request=>{
    assert.deepEqual(request.binding,fixture.first.binding);
    assert.equal(request.generation,fixture.first.binding.generation);
    assert.equal(typeof request.opaqueCursor,'string');
    assert(Object.hasOwn(fixture.replies,request.opaqueCursor));
    calls.push(request.opaqueCursor);
    return fixture.replies[request.opaqueCursor];
  }});
  presenter.show(fixture.first);
  for(let count=0;count<500;count++){
    const action=buttons(root).find(button=>!button.hidden&&!button.disabled&&
      (button.textContent==='Load next field page'||button.textContent.startsWith('Load child ')));
    if(!action)break;
    action.onclick();await tick();
    if(count===499)assert.fail('bounded synthetic UI traversal did not terminate');
  }
  if(['held','unknown'].includes(fixture.name)){
    assert.equal(presenter.isComplete(),false);
    assert.equal(calls.length,0);
    assert.match(root.textContent,/incomplete/);
  }else{
    assert.equal(presenter.isComplete(),true);
    assert.equal(calls.length,Object.keys(fixture.replies).length);
    assert.equal(new Set(calls).size,calls.length);
    if(fixture.name==='unicode'){
      const spans=[];function visit(node){if(node.tagName==='p'&&node.children[0]?.textContent==='Source text: ')spans.push(node.children[1].textContent);node.children.forEach(visit);}visit(root);
      assert.equal(spans.join(''),fixture.original);
    }else{
      assert.match(root.textContent,/unknown\/extension~/);
      assert.match(root.textContent,/9007199254740993/);
      assert.match(root.textContent,/inert https:\/\/invalid.test\//);
    }
  }
  presenter.destroy();
});
