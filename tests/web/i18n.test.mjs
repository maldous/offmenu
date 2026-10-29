import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {resolveLanguage,setLanguage,getLanguage,t,hasTranslation,formatNumber,formatDate,formatCurrency,translateUI,setupLanguage,LANGUAGE_KEY,apiError,setLocalizedText} from '../../apps/web/src/i18n.js';
import {localizedField,localizedRecipe,localizedLotName,multilingualSearchText,normalizeSearchText,configureCorpusResolver,showLocalized,showUserText} from '../../apps/web/src/content-locale.js';
import {matchRecipeStock} from '../../apps/web/src/recipe-library-model.js';
import {buildDocument,documentHTML,documentEPUB} from '../../apps/web/src/documents.js';
import {validateState} from '../../apps/web/server/state.mjs';

test('locale negotiation respects explicit supported preferences and language subtags',()=>{
  assert.equal(resolveLanguage(['ja-JP','ar-EG','en']), 'ar');
  assert.equal(resolveLanguage('ar_SA'), 'ar');
  assert.equal(resolveLanguage(['en-AU','ar']), 'en');
  assert.equal(resolveLanguage('invalid'), 'en');
});
test('dynamic accessible text retains translated language and declares English fallback',()=>{
  const node={};setLanguage('ar');
  try {setLocalizedText(node,t('Breakfast'));assert.equal(node.textContent,'الفطور');assert.equal(node.lang,'ar');assert.equal(node.dir,'auto');setLocalizedText(node,'Untranslated dynamic message');assert.equal(node.lang,'en');}
  finally {setLanguage('en');}
});
test('Arabic messages use six plural categories, formatted numbers and safe plain-text parameters',()=>{
  setLanguage('ar');
  try {
    assert.equal(t('Breakfast'),'الفطور');
    assert.match(t('Recipes indexed: {count}',{count:0}),/لا وصفات/);
    assert.match(t('Recipes indexed: {count}',{count:1}),/واحدة/);
    assert.match(t('Recipes indexed: {count}',{count:2}),/وصفتان/);
    assert.equal(t('Recipes indexed: {count}',{count:3}),formatNumber(3)+' وصفات مفهرسة');
    assert.equal(t('Recipes indexed: {count}',{count:11}),formatNumber(11)+' وصفة مفهرسة');
    assert.ok(t('Recipes indexed: {count}',{count:100}).includes(formatNumber(100))); 
    assert.equal(t('{name}',{name:'<img src=x>'}),'<img src=x>');
    assert.equal(t('No translation exists'),'No translation exists');
    assert.equal(t('toString'),'toString');
    assert.equal(hasTranslation('Breakfast','fr'),false);
    assert.equal(formatNumber(1234.5),new Intl.NumberFormat('ar').format(1234.5));
    assert.equal(formatDate('2026-10-14'),new Intl.DateTimeFormat('ar').format(new Date('2026-10-14T12:00:00')));
    assert.equal(formatCurrency(2.99,'AUD'),new Intl.NumberFormat('ar',{style:'currency',currency:'AUD',maximumFractionDigits:20}).format(2.99));
  } finally { setLanguage('en'); }
});
test('static UI and accessibility labels translate without changing form values or markup',()=>{
  const translated={textContent:'Breakfast',value:'Breakfast',getAttribute:()=> 'Breakfast'};
  const fallback={textContent:'Unknown source sentence',getAttribute:()=> 'Unknown source sentence'};
  const input={value:'00000123',getAttribute:()=> 'Interface language',setAttribute(name,value){this[name]=value;}};
  const root={documentElement:{},querySelectorAll(selector){return selector==='[data-i18n]'?[translated,fallback]:selector==='[data-i18n-aria-label]'?[input]:[];}};
  setLanguage('ar');
  try {translateUI(root);assert.deepEqual(root.documentElement,{lang:'ar',dir:'rtl'});assert.equal(translated.textContent,'الفطور');assert.equal(translated.value,'Breakfast');assert.equal(fallback.lang,'en');assert.equal(input.value,'00000123');assert.equal(input['aria-label'],'لغة الواجهة');}
  finally {setLanguage('en');}
});
test('saved language persists separately from pantry profiles and works via URL when storage is blocked',()=>{
  const old=globalThis.location;
  let callback,assigned;
  const select={value:'',addEventListener(event,fn){callback=fn;}};
  const root={documentElement:{},querySelector(){return null;},querySelectorAll(selector){return selector==='[data-ui-language]'?[select]:[];}};
  const storage={getItem(key){assert.equal(key,LANGUAGE_KEY);return 'ar';},setItem(){throw Error('blocked');}};
  globalThis.location={href:'https://offmenu.test/?country=AU#workspace',assign(value){assigned=value;}};
  try {setupLanguage(root,storage,{languages:['en-AU']});assert.equal(getLanguage(),'ar');select.value='en';callback();const url=new URL(assigned);assert.equal(url.searchParams.get('uiLanguage'),'en');assert.equal(url.searchParams.get('country'),'AU');assert.equal(url.hash,'#workspace');}
  finally {globalThis.location=old;setLanguage('en');}
});
test('multilingual fields resolve requested text and retain original language, identity and citations',()=>{
  const record={id:'recipe:42',provenance:{url:'https://source.test/recipe'},data:{name:'Soupe',languages:['fr'],names:{en:'Soup',ar:'حساء'},ingredients:[{ingredientId:'water',name:'Eau',names:{en:'Water'},amount:100,unit:'ml'}],directions:['Faire bouillir.'],directionsByLanguage:{en:['Bring to a boil.']}}};
  const original=structuredClone(record),view=localizedRecipe(record,'en-AU');
  assert.equal(view.title.value,'Soup');assert.equal(view.title.language,'en');assert.equal(view.title.original,'Soupe');assert.equal(view.ingredients[0].name.value,'Water');assert.equal(view.ingredients[0].source.ingredientId,'water');assert.deepEqual(view.directions.value,['Bring to a boil.']);
  assert.deepEqual(record,original);
  const missing=localizedField(record,'name','ja');assert.equal(missing.value,'Soupe');assert.equal(missing.language,'fr');assert.equal(missing.missingTranslation,true);
  assert.equal(localizedField(record,'name','native').missingTranslation,false);
  const node={dataset:{}};showLocalized(node,missing);assert.equal(node.dir,'auto');assert.equal(node.lang,'fr');assert.equal(node.dataset.translationFallback,'true');
});
test('corpus adapter can supply universally represented text without imposing a corpus schema',()=>{
  const record={identity:'food:water',citation:'source:1'};
  configureCorpusResolver((r,field,locale)=>({value:locale==='ar'?'ماء':'Water',original:'Eau',language:locale,requested:locale,missingTranslation:false,sourceId:r.citation,conceptId:r.identity}));
  try {assert.equal(localizedField(record,'name','ar').value,'ماء');assert.equal(localizedField(record,'name','en').sourceId,'source:1');assert.deepEqual(record,{identity:'food:water',citation:'source:1'});}
  finally {configureCorpusResolver(null);}
});
test('search covers available translations while preserving significant non-Latin characters',()=>{
  const record={name:'Soupe',names:{en:'Soup',ar:'حساء',ja:'が'},ingredients:[{name:'Eau',names:{en:'Water'}}]};
  const index=multilingualSearchText(record);
  for(const query of ['Soupe','Soup','Water','حساء','が'])assert.ok(index.includes(normalizeSearchText(query)));
  assert.equal(normalizeSearchText('Crème'),'creme');assert.notEqual(normalizeSearchText('が'),normalizeSearchText('か'));
  assert.equal(normalizeSearchText('চাল'),'চাল');
});
test('locale changes cannot alter quantity matching or canonical ingredients',()=>{
  const recipe={ingredients:[{ingredientId:'rice',name:'Riz',names:{ar:'أرز'},amount:100,unit:'g'}]};
  const stock=[{ingredient:'rice',quantity:100,unit:'g'}],before=matchRecipeStock(recipe,stock);
  setLanguage('ar');try {localizedRecipe(recipe);assert.deepEqual(matchRecipeStock(recipe,stock),before);assert.equal(before.quantitiesAvailable,true);}finally{setLanguage('en');}
});
test('food display preferences accept Arabic, Japanese and UI locale without changing units',()=>{
  for(const dataLanguage of ['ui','ar','ja','native','fr','ru']){
    const state={inventory:[],products:{},recipes:[],profile:{country:'AU',units:'metric',servings:2,dataLanguage},selections:[]};
    assert.deepEqual(validateState(state),state);
  }
});
test('HTML and EPUB exports declare the selected language and retain safe source content',()=>{
  setLanguage('ar');
  try {
    const doc=buildDocument('kitchen',{inventory:[{id:'a',name:'<script>alert(1)</script>',ingredient:'rice',quantity:2,unit:'g'}],profile:{country:'AU'},recipes:[],products:{},date:'2026-10-14',usePantry:true});
    const html=documentHTML(doc);assert.match(html,/lang="ar" dir="rtl"/);assert.match(html,/&lt;script&gt;/);assert.doesNotMatch(html,/<script>/);
    const epub=new TextDecoder().decode(documentEPUB(doc));assert.match(epub,/<dc:language>ar<\/dc:language>/);assert.match(epub,/lang="ar" dir="rtl"/);
  } finally {setLanguage('en');}
});
test('static meal-slot options have explicit canonical values in a translated page',async()=>{
  const html=await readFile(new URL('../../apps/web/assets/index.html',import.meta.url),'utf8');
  for(const slot of ['Breakfast','Lunch','Dinner','Snack'])assert.match(html,new RegExp('<option[^>]*value="'+slot+'"[^>]*data-i18n="'+slot+'"'));
});
test('personal text does not become a UI translation and API decisions retain source messages',()=>{
  setLanguage('ar');
  try {
    const node={dataset:{}};showUserText(node,'Breakfast');assert.equal(node.textContent,'Breakfast');assert.equal(node.dir,'auto');
    showLocalized(node,localizedField({name:'Breakfast'},'name','ar'));assert.equal(node.textContent,'Breakfast');
    const error=apiError({error:'Cloud operation failed.',errorCode:'retry'});assert.equal(error.message,'فشلت العملية السحابية.');assert.equal(error.sourceMessage,'Cloud operation failed.');assert.equal(error.code,'retry');
  } finally {setLanguage('en');}
});
test('pantry publisher labels can localize without overwriting personal renames or canonical stock',()=>{
  const product={name:'Rice',sourceName:'Riz',language:'fr',names:{en:'Rice',ar:'أرز'}},products={'0001':product},lot={barcode:'0001',name:'Rice',ingredient:'rice',quantity:100,unit:'g'},before=structuredClone(lot);
  assert.equal(localizedLotName(lot,products,'ar').value,'أرز');assert.equal(localizedLotName(lot,products,'native').value,'Riz');
  assert.equal(localizedLotName({...lot,name:'My personal rice'},products,'ar').value,'My personal rice');assert.deepEqual(lot,before);
});
