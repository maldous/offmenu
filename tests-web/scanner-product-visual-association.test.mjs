import test from 'node:test';
import assert from 'node:assert/strict';
import {mountScannerProductVisual} from '../public/scanner-product-visuals.js';
import {photoFixture} from './fixtures/off-photos/context.mjs';

class Element {
  constructor(tag,doc){this.tagName=tag;this.ownerDocument=doc;this.children=[];this.dataset={};this.text='';}
  set textContent(value){this.text=String(value);this.children=[];}
  get textContent(){return this.text+this.children.map(node=>node.textContent).join('');}
  get firstChild(){return this.children[0]??null;}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this.text='';this.children=nodes;}
  set innerHTML(_){throw Error('HTML insertion forbidden');}
}
function dom(theme='light') {
  const doc={documentElement:{dataset:{theme}},createElement:tag=>new Element(tag,doc)};
  const thumbnail=new Element('div',doc),caption=new Element('div',doc),changes=[];
  const presenter=mountScannerProductVisual(thumbnail,caption,{onChange:value=>changes.push(value)});
  return {thumbnail,caption,presenter,changes};
}
const selected=()=>({...photoFixture(),entryId:'one',generation:1,name:'Authored source label'});

test('actual caller uses the shared typed association and preserves photo credit DOM',()=>{
  const {thumbnail,caption,presenter,changes}=dom();const input=selected();
  input.reference.privateProfile='DO NOT COPY';input.reference.observationKey.privateToken='DO NOT COPY';
  const value=presenter.show(input);
  assert.equal(value.tier,'product-photo');assert.equal(thumbnail.dataset.visualTier,'product-photo');
  assert.equal(thumbnail.firstChild.src,'/api/off-photos/flour-front-en-rev5.jpg');
  assert.equal(thumbnail.firstChild.referrerPolicy,'no-referrer');
  assert.equal(value.identity.sourceObservationReference.originalLexicalValue,'078742003986');
  assert.equal(value.identity.sourceObservationReference.sourceLexicalValue,'0078742003986');
  assert.ok(!JSON.stringify(value).includes('DO NOT COPY')); // proves the shared typed snapshot is used
  assert.match(caption.textContent,/foodless/);assert.match(caption.textContent,/CC BY-SA 3.0/);
  assert.match(caption.textContent,/membership in the retained snapshot is unverified/);
  const links=caption.children.filter(node=>node.tagName==='a');assert.equal(links.length,3);
  for(const link of links){assert.equal(link.target,'_blank');assert.equal(link.rel,'noopener noreferrer');}
  assert.equal(changes.length,0);assert.equal(presenter.current(),value);
});

test('missing or invalid reference preserves document dark theme, legacy alt and one failure callback',()=>{
  for(const input of [{}, {...selected(),reference:{...selected().reference,matchType:'invented'}}]) {
    const {thumbnail,presenter,changes}=dom('dark');
    const visual=presenter.show(input);
    assert.equal(visual.src,'/scanner-balanced-final-dark.svg');
    assert.equal(visual.alt,'OffMenu app icon; product photo unavailable');
    const failed=thumbnail.firstChild.onerror;failed();failed();assert.equal(presenter.current().kind,'text');
    assert.equal(thumbnail.textContent,'OffMenu');assert.equal(changes.length,1);
  }
});

test('valid-reference unavailable detail keeps explicit caller theme rather than document theme',()=>{
  const {thumbnail,presenter}=dom('dark');
  presenter.show({...selected(),detail:null});
  assert.equal(thumbnail.firstChild.src,'/scanner-balanced-final.svg');
  presenter.show({...selected(),offline:true,theme:'dark'});
  assert.equal(thumbnail.firstChild.src,'/scanner-balanced-final-dark.svg');
});

test('current photo failure uses shared failure selection and one callback per fallback',()=>{
  const {thumbnail,presenter,changes}=dom();
  presenter.show({...selected(),theme:'dark'});
  const failed=thumbnail.firstChild.onerror;failed();failed();assert.equal(changes.length,1);
  assert.equal(presenter.current().tier,'app-fallback');
  assert.equal(thumbnail.firstChild.src,'/scanner-balanced-final-dark.svg');
  thumbnail.firstChild.onerror();assert.equal(changes.length,2);
  assert.equal(presenter.current().kind,'text');assert.equal(thumbnail.textContent,'OffMenu');
});

test('stale image callback cannot replace a new selection or notify it',()=>{
  const {thumbnail,presenter,changes}=dom('dark');presenter.show(selected());
  const stale=thumbnail.firstChild.onerror;
  presenter.show({entryId:'two',generation:2});const current=thumbnail.firstChild;
  stale();assert.equal(thumbnail.firstChild,current);assert.equal(changes.length,0);
});

test('failed history survives same key and resets for new entry or generation',()=>{
  const {thumbnail,presenter,changes}=dom();const input=selected();presenter.show(input);
  thumbnail.firstChild.onerror();assert.equal(presenter.current().tier,'app-fallback');
  presenter.show(input);assert.equal(presenter.current().tier,'app-fallback');
  presenter.show({...input,entryId:'two'});assert.equal(presenter.current().tier,'product-photo');
  thumbnail.firstChild.onerror();presenter.show({...input,entryId:'two',generation:2});
  assert.equal(presenter.current().tier,'product-photo');assert.equal(changes.length,2);
});

test('destroy retains the epoch guard and clears DOM without stale notifications',()=>{
  const {thumbnail,caption,presenter,changes}=dom();presenter.show(selected());
  const stale=thumbnail.firstChild.onerror;presenter.destroy();stale();
  assert.equal(thumbnail.children.length,0);assert.equal(caption.children.length,0);
  assert.equal(changes.length,0);
});
