import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {setupData} from '../public/data-ui.js';
import {loadCommonCorpusPackage} from '../public/common-corpus-transport.js';
import {configureCorpusResolver,localizedField} from '../public/content-locale.js';
import {setLanguage} from '../public/i18n.js';

const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const base='https://selected.test/package/';
const deferred=()=>{let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};};
function selection({gzip,limits,permission={}}={}){
  const scope={visibility:'public'},id='https://مثال.test/عدس';
  const citation={id:'urn:citation:selected',sourceId:'synthetic',originalRecordId:'0001',originalUrl:'https://مثال.test/مصدر',license:'CC0',attribution:'المصدر الأصلي',scope};
  const name={kind:'text',id:'urn:text:selected',language:'ar',value:'عدس',sourceTextSha256:sha('عدس'),status:'source-asserted',citationIds:[citation.id]};
  const resource={id,type:'urn:offmenu:type:Ingredient',identityStatus:'source-scoped',names:[name],citationIds:[citation.id],scope};
  const graph={schemaVersion:'offmenu-common/1',resources:[resource,{...resource,id:'urn:private',scope:{visibility:'private',ownerId:'alice'},names:[{...name,id:'urn:text:private',value:'خاص',sourceTextSha256:sha('خاص')}]}],
    assertions:[{id:'urn:assertion:iri',subjectId:id,propertyId:'urn:offmenu:property:sourceIRI',value:{kind:'uri',value:'https://例.test/餡'},status:'source-asserted',citationIds:[citation.id],sourcePath:'original.iri',scope},{id:'urn:assertion:expression',subjectId:id,propertyId:'urn:offmenu:property:expression',value:{kind:'expression',syntax:'rdf/xml',value:'<rdf:Description>餡</rdf:Description>'},status:'candidate',citationIds:[citation.id],sourcePath:'original.expression',scope}],
    relations:[{id:'urn:relation:unresolved',subjectId:id,predicateId:'urn:offmenu:relation:candidateIdentity',objectId:'urn:external:unresolved',status:'candidate',citationIds:[citation.id],sourcePath:'source.join',scope}],citations:[citation],
    translations:[{id:'urn:translation:en',textId:name.id,language:'en',value:'Lentils',sourceTextSha256:name.sourceTextSha256,translator:'source',method:'source-published',status:'published-source',citationIds:[citation.id],terminologyResourceIds:[]}]};
  const compressed=gzip??gzipSync(JSON.stringify(graph)+'\n',{mtime:0}),key='terminology/part-0000.jsonl.gz';
  const file={key,sha256:sha(compressed),bytes:compressed.length,packets:1};
  const manifest=Buffer.from(JSON.stringify({schemaVersion:'offmenu-common-package/1',contractVersion:'offmenu-common-contract/1',releaseId:'synthetic-caller/1',status:'all-packets-schema-identity-citation-and-scope-checked',files:[file]}));
  const manifestSha256=sha(manifest),calls=[];
  const descriptor={transport:{manifestUrl:base+'manifest.json',manifestSha256,acceptedReleases:[{releaseId:'synthetic-caller/1',manifestSha256}],files:[{key,sha256:file.sha256,bytes:file.bytes,packetIndexes:[0]}],allowedOrigins:['https://selected.test'],...(limits?{limits}:{})},qualification:{releaseId:'synthetic-caller/1',schemaSha256:sha('synthetic fixture schema'),contractSha256:sha('synthetic fixture contract')}};
  // Independent fixture policy is retained separately from the selected descriptor.
  // It grants no producer admission outside this bounded synthetic test.
  const policy={allowed:true,accountKey:'guest',policyId:'synthetic-caller-display-only/1',selection:structuredClone(descriptor),scope:{privateOwnerId:null},...permission};
  const authorize=async()=>structuredClone(policy);
  const load=options=>loadCommonCorpusPackage({...options,fetchImpl:async(url,init)=>{
    calls.push({url,init});assert.equal(init.redirect,'error');assert.equal(init.credentials,'omit');
    if(url===base+'manifest.json')return new Response(manifest);
    if(url===base+key)return new Response(compressed);
    throw Error('Unselected fetch');
  }});
  return {descriptor,load,authorize,policy,calls,graph,id,citation};
}
function environment(t,fixture,load=fixture.load){
  class Element {
    constructor(tag='div'){this.tagName=tag.toUpperCase();this.children=[];this.dataset={};this.value='';this.disabled=false;this.hidden=false;this.checked=false;this.attributes={};this._text='';}
    set textContent(value){this._text=String(value??'');this.children=[];}
    get textContent(){return this._text+this.children.map(child=>child.textContent??String(child)).join('');}
    append(...children){this.children.push(...children);}
    replaceChildren(...children){this._text='';this.children=[...children];}
    setAttribute(key,value){this.attributes[key]=value;}
    close(){} focus(){}
  }
  const priorDocument=globalThis.document,priorFetch=globalThis.fetch,elements=new Map(),sideEffects=[];
  const $=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
  globalThis.document={getElementById:$,createElement:tag=>new Element(tag),createTextNode:value=>({textContent:String(value)})};
  globalThis.fetch=async()=>{sideEffects.push('ambient-fetch');throw Error('Ambient network forbidden in caller tests');};
  setLanguage('ar');
  const state={user:null,demo:false,profile:{dataLanguage:'native'},inventory:[]};
  const ui=setupData({getData:()=>state,getUser:()=>state.user,isDemo:()=>state.demo,refreshSession:async()=>sideEffects.push('session-refresh'),persist:()=>sideEffects.push('persist'),download:()=>sideEffects.push('download'),applyNutrition:()=>sideEffects.push('apply'),addRecipe:()=>sideEffects.push('add'),selectedCommonPackage:fixture.descriptor,commonPackageLoader:{load,authorize:fixture.authorize}});
  t.after(()=>{ui.reset();configureCorpusResolver(null);setLanguage('en');globalThis.document=priorDocument;globalThis.fetch=priorFetch;});
  const descendants=node=>node.children.flatMap(child=>[child,...(child.children?descendants(child):[])]);
  return {ui,$,state,sideEffects,descendants};
}
test('setupData exposes an explicit selected-package action without automatic I/O; real loader reaches existing rendering',async t=>{
  const f=selection(),before=structuredClone(f.descriptor),e=environment(t,f);
  assert.equal(f.calls.length,0);assert.deepEqual(e.sideEffects,[]);
  const {receipt}=await e.ui.loadSelectedCommonPackage();
  assert.equal(f.calls.length,2);assert.equal(receipt.manifestSha256,f.descriptor.transport.manifestSha256);
  const articles=e.$('data-results').children;assert.equal(articles.length,1);
  const nodes=e.descendants(articles[0]),title=nodes.find(node=>node.tagName==='H3');
  assert.equal(title.textContent,'عدس');assert.equal(title.lang,'ar');assert.equal(title.dir,'auto');
  assert.ok(nodes.some(node=>node.textContent==='https://例.test/餡'&&node.lang==='und'));
  assert.ok(nodes.some(node=>node.tagName==='CODE'&&node.dir==='ltr'&&node.textContent==='<rdf:Description>餡</rdf:Description>'));
  assert.ok(nodes.some(node=>node.tagName==='A'&&node.href===new URL(f.citation.originalUrl).href));
  assert.ok(articles[0].textContent.includes(f.citation.attribution+' · '+f.citation.license));
  const projection=localizedField({commonResourceId:f.id},'name','en');
  assert.equal(projection.value,'Lentils');assert.equal(projection.original,'عدس');assert.equal(projection.sourceTextSha256,f.graph.resources[0].names[0].sourceTextSha256);assert.deepEqual(projection.citations,[f.citation]);
  e.$('data-language').value='en';e.$('data-language').onchange();
  const english=e.descendants(e.$('data-results')).find(node=>node.tagName==='H3');assert.equal(english.textContent,'Lentils');assert.equal(english.lang,'en');
  e.$('data-rights').checked=true;await e.$('data-save').onclick();e.$('data-export').onclick();
  assert.equal(e.$('data-save').disabled,true);assert.equal(e.$('data-export').disabled,true);assert.deepEqual(e.sideEffects,[]);assert.deepEqual(f.descriptor,before);
});
test('bad manifest/file pins, permission, gzip and budgets reject at caller boundary before common rendering',async t=>{
  for(const kind of ['manifest','file','permission','account','policy','gzip','budget'])await t.test(kind,async t=>{
    const f=selection(kind==='gzip'?{gzip:Buffer.from('invalid gzip')}:kind==='budget'?{limits:{compressedBytes:1}}:{});
    if(kind==='manifest'){f.descriptor.transport.manifestSha256='0'.repeat(64);f.descriptor.transport.acceptedReleases[0].manifestSha256='0'.repeat(64);f.policy.selection=structuredClone(f.descriptor);}
    if(kind==='file'){f.descriptor.transport.files[0].sha256='0'.repeat(64);f.policy.selection=structuredClone(f.descriptor);}
    if(kind==='permission')f.policy.allowed=false;
    if(kind==='account')f.policy.accountKey='user:alice';
    if(kind==='policy')f.policy.selection.qualification.schemaSha256='0'.repeat(64);
    const e=environment(t,f);
    await assert.rejects(e.ui.loadSelectedCommonPackage());
    assert.equal(e.$('data-results').children.length,0);assert.equal(e.$('data-save').disabled,true);assert.equal(e.$('data-export').disabled,true);
    e.$('data-rights').checked=true;await e.$('data-save').onclick();e.$('data-export').onclick();
    assert.deepEqual(e.sideEffects,[]);
    if(['permission','account','policy'].includes(kind))assert.equal(f.calls.length,0);
  });
});
test('account reset aborts a pending selected load; an injector ignoring abort cannot render stale results',async t=>{
  const f=selection(),gate=deferred(),entered=deferred();let request;
  const e=environment(t,f,async options=>{request=options;const value=await f.load(options);entered.resolve();await gate.promise;return value;});
  const pending=e.ui.loadSelectedCommonPackage();await entered.promise;
  const cancelled=assert.rejects(pending);
  e.state.user={id:'alice'};e.ui.reset();assert.equal(request.signal.aborted,true);
  await cancelled;gate.resolve();
  assert.equal(e.$('data-results').children.length,0);assert.equal(e.$('data-save').disabled,true);assert.equal(e.$('data-export').disabled,true);assert.deepEqual(e.sideEffects,[]);
});
test('a changed account is checked after await even if its host omitted reset',async t=>{
  const f=selection(),gate=deferred(),entered=deferred();let request;
  const e=environment(t,f,async options=>{request=options;const result=await f.load(options);entered.resolve();await gate.promise;return result;});
  const pending=e.ui.loadSelectedCommonPackage();await entered.promise;e.state.user={id:'alice'};gate.resolve();
  await assert.rejects(pending);assert.equal(request.signal.aborted,true);assert.equal(e.$('data-results').children.length,0);assert.deepEqual(e.sideEffects,[]);
});
test('a newer explicit load cancels the prior generation and stale completion never replaces its reader/notice',async t=>{
  const f=selection(),first=deferred(),entered=deferred(),rendered=[];let attempt=0,signal;
  const e=environment(t,f,async options=>{
    const id=++attempt,result=await f.load(options),reader=result.corpus;
    if(id===1){signal=options.signal;entered.resolve();await first.promise;}
    return {...result,corpus:{...reader,resolveField(...args){rendered.push(id);return reader.resolveField(...args);}}};
  });
  const one=e.ui.loadSelectedCommonPackage();await entered.promise;const cancelled=assert.rejects(one);await e.ui.loadSelectedCommonPackage();assert.equal(signal.aborted,true);
  const notice=e.$('data-notice').textContent,content=e.$('data-results').textContent;
  first.resolve();await cancelled;assert.deepEqual([...new Set(rendered)],[2]);
  assert.equal(e.$('data-notice').textContent,notice);assert.equal(e.$('data-results').textContent,content);assert.deepEqual(e.sideEffects,[]);
});
test('account identity namespaces cannot collide with guest/demo and reader privileges come from current account',async t=>{
  const f=selection({permission:{accountKey:'user:alice',scope:{privateOwnerId:'alice'}}});let received;
  f.descriptor.transport.readerOptions={userId:'other',allowLocalRestricted:true};
  f.policy.selection=structuredClone(f.descriptor);
  const e=environment(t,f,options=>{received=options.readerOptions;return f.load(options);});e.state.user={id:'alice'};
  await e.ui.loadSelectedCommonPackage();assert.deepEqual(received,{userId:'alice',allowLocalRestricted:false});assert.equal(e.$('data-results').children.length,2);
  e.state.user={id:'guest'};e.ui.reset();await assert.rejects(e.ui.loadSelectedCommonPackage());assert.equal(e.$('data-results').children.length,0);
});
test('descriptor permission self-assertion and a loader alone never establish independent admission',async t=>{
  const f=selection();f.descriptor.permission={allowed:true};f.authorize=undefined;
  const e=environment(t,f);await assert.rejects(e.ui.loadSelectedCommonPackage(),/independently authorized/);
  assert.equal(f.calls.length,0);assert.equal(e.$('data-results').children.length,0);assert.deepEqual(e.sideEffects,[]);
});
test('permission revocation and scope change during loading reject before render',async t=>{
  for(const kind of ['denied','scope','selection'])await t.test(kind,async t=>{
    const f=selection(),gate=deferred(),entered=deferred();
    const e=environment(t,f,async options=>{const value=await f.load(options);entered.resolve();await gate.promise;return value;});
    const pending=e.ui.loadSelectedCommonPackage();await entered.promise;
    if(kind==='denied')f.policy.allowed=false;
    if(kind==='scope')f.policy.scope={privateOwnerId:'alice'};
    if(kind==='selection')f.descriptor.transport.files[0].packetIndexes=[1];
    gate.resolve();await assert.rejects(pending);assert.equal(e.$('data-results').children.length,0);assert.deepEqual(e.sideEffects,[]);
  });
});
test('a pending authorization is cancelled by account reset before it can call the loader',async t=>{
  const f=selection(),gate=deferred(),entered=deferred();let signal;
  f.authorize=async options=>{signal=options.signal;entered.resolve();await gate.promise;return structuredClone(f.policy);};
  const e=environment(t,f),pending=e.ui.loadSelectedCommonPackage();await entered.promise;const cancelled=assert.rejects(pending);
  e.state.demo=true;e.ui.reset();assert.equal(signal.aborted,true);await cancelled;gate.resolve();
  assert.equal(f.calls.length,0);assert.equal(e.$('data-results').children.length,0);
});
test('loader receipt must match selected release, manifest, file bytes and packet indexes',async t=>{
  for(const kind of ['release','manifest','bytes','indexes'])await t.test(kind,async t=>{
    const f=selection(),e=environment(t,f,async options=>{
      const result=await f.load(options);
      if(kind==='release')result.receipt.releaseId='different-release';
      if(kind==='manifest')result.receipt.manifestSha256='0'.repeat(64);
      if(kind==='bytes')result.receipt.files[0].compressedBytes++;
      if(kind==='indexes')result.receipt.files[0].packetIndexes=[1];
      return result;
    });
    await assert.rejects(e.ui.loadSelectedCommonPackage(),/receipt/);assert.equal(e.$('data-results').children.length,0);assert.deepEqual(e.sideEffects,[]);
  });
});
test('signed-in public-only permission does not automatically unlock private rows',async t=>{
  const f=selection({permission:{accountKey:'user:alice'}}),e=environment(t,f);e.state.user={id:'alice'};
  await e.ui.loadSelectedCommonPackage();assert.equal(e.$('data-results').children.length,1);
  f.policy.scope={privateOwnerId:'bob'};await assert.rejects(e.ui.loadSelectedCommonPackage(),/permission/);assert.equal(e.$('data-results').children.length,0);
});
test('legacy common-graph import still uses the existing renderer and stays read-only without package I/O',async t=>{
  const f=selection(),e=environment(t,f);e.$('data-language').value='native';
  e.$('data-file').files=[{name:'fixture.json',size:4096,text:async()=>JSON.stringify(f.graph)}];
  await e.$('data-file').onchange();
  assert.equal(e.$('data-results').children.length,1);assert.equal(e.descendants(e.$('data-results')).find(node=>node.tagName==='H3').textContent,'عدس');
  assert.equal(e.$('data-save').disabled,true);assert.equal(e.$('data-export').disabled,true);assert.equal(f.calls.length,0);assert.deepEqual(e.sideEffects,[]);
});
test('selecting a local graph file cancels an older package request before the file finishes reading',async t=>{
  const f=selection(),gate=deferred(),entered=deferred(),file=deferred();let signal;
  const e=environment(t,f,async options=>{signal=options.signal;const result=await f.load(options);entered.resolve();await gate.promise;return result;});
  const pending=e.ui.loadSelectedCommonPackage();await entered.promise;const cancelled=assert.rejects(pending);
  e.$('data-file').files=[{name:'fixture.json',size:4096,text:()=>file.promise}];
  const importing=e.$('data-file').onchange();assert.equal(signal.aborted,true);await cancelled;
  file.resolve(JSON.stringify(f.graph));await importing;const content=e.$('data-results').textContent;
  gate.resolve();await new Promise(resolve=>setImmediate(resolve));assert.equal(e.$('data-results').textContent,content);assert.equal(e.$('data-results').children.length,1);assert.deepEqual(e.sideEffects,[]);
});
