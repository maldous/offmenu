import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {parse} from 'acorn';
import vm from 'node:vm';
import {mountScannerProductVisual} from '../../public/scanner-product-visuals.js';
import {sourceObservationReference} from '../../public/scanner-identity-v2.js';
import {photoFixture} from './fixtures/off-photos/context.mjs';

class Element {
  constructor(tag,doc){this.tagName=tag;this.ownerDocument=doc;this.children=[];this.dataset={};this.text='';}
  set textContent(value){this.text=String(value);this.children=[];}
  get textContent(){return this.text+this.children.map(child=>child.textContent).join('');}
  get firstChild(){return this.children[0]??null;}
  append(...children){this.children.push(...children);}
  replaceChildren(...children){this.text='';this.children=[...children];}
  setAttribute(name,value){(this.attributes??={})[name]=value;}
  set innerHTML(_){throw Error('HTML insertion forbidden');}
}
function dom(){const doc={documentElement:{dataset:{theme:'light'}},createElement:tag=>new Element(tag,doc)};
  const thumbnail=new Element('div',doc),caption=new Element('div',doc);
  return {doc,thumbnail,caption,presenter:mountScannerProductVisual(thumbnail,caption)};}

test('real photo renderer supplies alt, accessible native credit details and safe source/licence links without theme-logo rewriting',()=>{
  const {thumbnail,caption,presenter}=dom();const fixture=photoFixture();
  const result=presenter.show({...fixture,name:'Source flour',entryId:'one',generation:1});
  assert.equal(result.tier,'product-photo');assert.match(thumbnail.firstChild.src,/^\/api\/off-photos\/flour-/);
  assert.match(thumbnail.firstChild.alt,/Source flour/);assert.equal(thumbnail.firstChild.dataset.offmenuLogo,undefined);
  assert.match(caption.textContent,/foodless/);assert.match(caption.textContent,/retained snapshot is unverified/);
  const details=caption.children.find(node=>node.tagName==='details');assert.ok(details);
  assert.equal(details.firstChild.tagName,'summary');assert.match(details.firstChild.textContent,/source and licence/);
  const links=details.children.filter(node=>node.tagName==='a');assert.equal(links.length,4);
  for(const link of links){assert.match(link.href,/^https:\/\//);assert.equal(link.rel,'noopener noreferrer');}
});

test('broken photo falls back to app icon and a broken icon to text without a retry loop',()=>{
  const {thumbnail,caption,presenter}=dom();presenter.show({...photoFixture(),entryId:'one',generation:1});
  thumbnail.firstChild.onerror();assert.equal(presenter.current().tier,'app-fallback');
  assert.equal(thumbnail.firstChild.src,'/scanner-balanced-final.svg');assert.match(caption.textContent,/unavailable/);
  thumbnail.firstChild.onerror();assert.equal(presenter.current().kind,'text');assert.equal(thumbnail.textContent,'OffMenu');
});

test('previous selection callbacks cannot replace a newly selected source view',()=>{
  const {thumbnail,presenter}=dom();presenter.show({...photoFixture(),entryId:'one',generation:1});
  const previous=thumbnail.firstChild.onerror;
  presenter.show({entryId:'other',generation:2,theme:'dark'});const current=thumbnail.firstChild;
  previous();assert.equal(thumbnail.firstChild,current);assert.equal(presenter.current().tier,'app-fallback');
});

test('actual offline state or invalid source reference stays on the app fallback',()=>{
  const {thumbnail,presenter}=dom();const fixture=photoFixture();
  assert.equal(presenter.show({...fixture,entryId:'one',generation:1,offline:true}).tier,'app-fallback');
  assert.equal(presenter.show({...fixture,reference:{...fixture.reference,matchType:'invented'},entryId:'two',generation:2}).tier,'app-fallback');
  assert.equal(thumbnail.firstChild.src,'/scanner-balanced-final.svg');
});

test('actual scanner render sends its current selected observation and detail to the photo renderer',async()=>{
  const source=await readFile(new URL('../../public/shelf-scanner.js',import.meta.url),'utf8');
  const ast=parse(source,{ecmaVersion:'latest',sourceType:'module'});
  const node=ast.body.find(node=>node.type==='FunctionDeclaration'&&node.id.name==='render');assert.ok(node);
  const fixture=photoFixture(),nodes=new Map(),{doc,thumbnail,caption}=dom();let passed;
  const presenter=mountScannerProductVisual(thumbnail,caption);
  const selected={identifier:fixture.detail.sourceObservation,detail:fixture.detail,name:'Source flour',
    matchContext:{originalLexicalValue:fixture.reference.originalLexicalValue,symbology:'UPC-A',
      matchType:'representation-alias',equivalence:'upc-a-as-leading-zero-ean-13'}};
  const current={id:'one',original:fixture.reference.originalLexicalValue,raw:fixture.reference.originalLexicalValue,
    databaseSha256:fixture.reference.databaseSha256,runId:fixture.reference.runId,namespace:'barcode',status:'source-match'};
  const context=vm.createContext({selected,current,connection:'live',generation:9,mode:'Explore',finished:false,
    active:true,paused:false,streaming:false,queue:[],saved:null,document:doc,navigator:{onLine:true},
    sourceObservationReference,productVisual:{show:input=>{passed=input;return presenter.show(input);}},
    $:id=>{if(!nodes.has(id))nodes.set(id,new Element('div',doc));return nodes.get(id);},
    displayValue(){},renderConsumerSummary(){},message(){},renderData(){},detailQueryUnavailable:()=>false,
    projectedField:()=>null,projectedValue:()=>null,humanValue:value=>String(value)});
  vm.runInContext(source.slice(node.start,node.end),context);context.render();
  assert.equal(passed.detail,fixture.detail);assert.equal(passed.generation,9);assert.equal(passed.entryId,'one');
  assert.equal(passed.reference.sourceLexicalValue,'0078742003986');
  assert.equal(presenter.current().tier,'product-photo');
});
