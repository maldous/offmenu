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

export {selection,environment,deferred};
