import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createCommonCorpus} from '../public/common-corpus-locale.js';
import {configureCorpusResolver,localizedRecipe} from '../public/content-locale.js';

const sha=value=>createHash('sha256').update(value).digest('hex');
const scope={visibility:'public'};
const citation={id:'urn:citation:1',sourceId:'publisher',originalRecordId:'42',originalUrl:'https://source.test/42',license:'CC BY-SA 4.0',attribution:'Source author',scope};
const text=(id,value,language='fr')=>({kind:'text',id,language,value,sourceTextSha256:sha(value),status:'source-asserted',citationIds:[citation.id]});
function graph(){
 const name=text('urn:text:name','Soupe'),step=text('urn:text:step','Faire bouillir.');
 const translation=(id,base,value,language='en',status='published-source')=>({id,textId:base.id,language,value,sourceTextSha256:base.sourceTextSha256,translator:'publisher',method:'source-published',status,citationIds:[citation.id],terminologyResourceIds:[]});
 const fact=(id,subjectId,propertyId,value)=>({id,subjectId,propertyId:'urn:offmenu:property:'+propertyId,value,status:'source-asserted',citationIds:[citation.id],sourcePath:'data',scope});
 return {schemaVersion:'offmenu-common/1',resources:[{id:'urn:recipe:1',type:'urn:offmenu:type:RecipeVariant',identityStatus:'source-scoped',names:[name],citationIds:[citation.id],scope},{id:'urn:step:1',type:'urn:offmenu:type:RecipeStep',identityStatus:'source-scoped',names:[],citationIds:[citation.id],scope}],
  assertions:[fact('urn:assertion:1','urn:recipe:1','originalSourceRecord',{kind:'identifier',value:'legacy:recipe:42'}),fact('urn:assertion:2','urn:step:1','instruction',step),fact('urn:assertion:3','urn:step:1','position',{kind:'number',value:1})],
  relations:[{id:'urn:relation:1',subjectId:'urn:recipe:1',predicateId:'urn:offmenu:relation:hasStep',objectId:'urn:step:1',status:'source-asserted',citationIds:[citation.id],scope,sourcePath:'data.directions.0'}],citations:[citation],translations:[translation('urn:translation:1',name,'Soup'),translation('urn:translation:2',step,'Bring to a boil.')]};
}
test('common graph resolves English text and ordered steps with exact source citations and fingerprints',async()=>{
 const source=graph(),before=structuredClone(source),reader=await createCommonCorpus(source);
 const name=reader.resolveField({id:'legacy:recipe:42'},'name','en-AU');
 assert.equal(name.value,'Soup');assert.equal(name.original,'Soupe');assert.equal(name.translationMethod,'source-published');assert.equal(name.sourceLanguage,'fr');assert.deepEqual(name.citations,[citation]);
 assert.deepEqual(reader.resolveField('urn:recipe:1','instructions','en').value,['Bring to a boil.']);
 assert.equal(reader.displayValue(source.resources[0].names[0],'native'),'Soupe');
 configureCorpusResolver(reader.resolveField);
 try {const view=localizedRecipe({id:'legacy:recipe:42',data:{name:'Soupe',directions:['Faire bouillir.'],ingredients:[]}},'en');assert.equal(view.title.value,'Soup');assert.deepEqual(view.directions.value,['Bring to a boil.']);}
 finally {configureCorpusResolver(null);}
 assert.deepEqual(source,before);source.resources[0].names[0].value='Edited later';assert.equal(reader.resolveField('urn:recipe:1','name','en').original,'Soupe');
 assert.throws(()=>{reader.resources[0].names[0].value='mutated';},TypeError);
 assert.equal(reader.projectText({...before.resources[0].names[0],value:'Unverified edit'},'en'),null);
 assert.equal(reader.resolveField({id:'legacy:recipe:42',title:'My edited soup',provenance:{visibility:'private',personalReview:{}}},'title','en'),null);
});
test('missing, stale and draft translations fall back explicitly; conflicting approved translations do not win by order',async()=>{
 for(const status of ['draft','stale']){const source=graph();source.translations[0].status=status;const reader=await createCommonCorpus(source),value=reader.resolveField('urn:recipe:1','name','en');assert.equal(value.value,'Soupe');assert.equal(value.fallbackReason,status);assert.equal(value.missingTranslation,true);}
 const source=graph();source.translations.push({...source.translations[0],id:'urn:translation:conflict',value:'Stew'});
 const reader=await createCommonCorpus(source);assert.equal(reader.resolveField('urn:recipe:1','name','en').value,'Soupe');assert.equal(reader.resolveField('urn:recipe:1','name','ja').fallbackReason,'missing');
});
test('translation is bound to current source digest and source digest is checked against actual UTF-8 text',async()=>{
 const source=graph();source.resources[0].names[0].value='Nouvelle soupe';source.resources[0].names[0].sourceTextSha256=sha('Nouvelle soupe');
 const reader=await createCommonCorpus(source);assert.equal(reader.resolveField('urn:recipe:1','name','en').value,'Nouvelle soupe');assert.equal(reader.resolveField('urn:recipe:1','name','en').fallbackReason,'stale');
 source.resources[0].names[0].value='Undigested edit';await assert.rejects(createCommonCorpus(source),/fingerprint/);
});
test('private resource and citation scopes must both be available to the current reader',async()=>{
 const source=graph();source.resources[0].scope={visibility:'private',ownerId:'alice'};source.citations[0]={...citation,scope:{visibility:'private',ownerId:'alice'}};
 for(const userId of [null,'bob']){const reader=await createCommonCorpus(source,{userId});assert.equal(reader.resolveField('urn:recipe:1','name','en'),null);assert.equal(reader.citations.length,0);}
 const reader=await createCommonCorpus(source,{userId:'alice'});assert.equal(reader.resolveField('urn:recipe:1','name','en').value,'Soup');
 const nested=graph();nested.citations.push({...citation,id:'private-evidence',scope:{visibility:'private',ownerId:'alice'}});nested.assertions[1].value.citationIds=['private-evidence'];
 const publicReader=await createCommonCorpus(nested);assert.equal(publicReader.displayValue(nested.assertions[1].value,'en'),'Unavailable source text');assert.equal(publicReader.resolveField('urn:recipe:1','instructions','en'),null);
});
test('generic typed values retain dimensions, unknowns, identifiers and source quantities without conversions',async()=>{
 const reader=await createCommonCorpus(graph());
 assert.equal(reader.displayValue({kind:'identifier',value:'0000123456789'},'ar'),'0000123456789');
 const quantity={kind:'quantity',value:null,unitId:null,dimension:'volume',sourceValue:'one cup',sourceUnit:'cup',qualifiers:['unresolved']},before=structuredClone(quantity);
 assert.equal(reader.displayValue(quantity,'en'),'Unknown cup');assert.deepEqual(quantity,before);
 assert.equal(reader.displayValue({kind:'boolean',value:false},'en'),'No');
 assert.equal(reader.displayValue({kind:'list',items:[{kind:'number',value:0},{kind:'identifier',value:'0001'}]},'en'),'0 · 0001');
});
test('duplicate graph identities and ambiguous legacy aliases are not silently reconciled',async()=>{
 const source=graph();source.resources.push(source.resources[0]);await assert.rejects(createCommonCorpus(source),/Duplicate/);
 const other=graph();other.resources.push({...other.resources[0],id:'urn:recipe:2'});other.assertions.push({...other.assertions[0],id:'urn:assertion:another',subjectId:'urn:recipe:2'});
 const reader=await createCommonCorpus(other);assert.equal(reader.resolveField('legacy:recipe:42','name','en'),null);
});
