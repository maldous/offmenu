import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {parse} from 'acorn';
import {ARABIC} from '../../apps/web/src/locales/ar.js';
import {getLanguage,setLanguage,t,hasTranslation,setLocalizedText} from '../../apps/web/src/i18n.js';
import {matchRecipeStock,recipeJSONLD} from '../../apps/web/src/recipe-library-model.js';
import {cleanCommunityRecipe,cleanCommunityProfile} from '../../apps/web/src/recipe-community-model.js';
import {cleanAdminSettings,previewAdminChanges,credentialPatch} from '../../apps/web/src/admin-model.js';
import {localizedField} from '../../apps/web/src/content-locale.js';
import {checkGeneratedExtension} from '../../scripts/check-generated-extension.mjs';

// Finite display/validation cohort at 931dde7f, not a claim about every UI string.
// UI modules below are parsed as text only: never import/mount administration or
// community UI, authenticate, invoke an API, or translate user/provenance data.
const sourceFiles=['recipe-library-ui.js','recipe-community-ui.js','admin-ui.js',
  'recipe-library-model.js','recipe-community-model.js','admin-model.js'];
const moderationLabels=['approve','hide','reject','restore'];
const canonicalUnits=['g','ml','count'];
const read=path=>readFile(new URL('../../'+path,import.meta.url),'utf8');
const placeholders=text=>[...text.matchAll(/\{(\w+)\}/g)].map(match=>match[1]).sort();
const sorted=values=>[...values].sort();
const expectedCohort={
  "{v0} shown from {v1} loaded search results · {v2} published recipes, including OCR candidates. Continue browsing for later results; this list keeps the latest 200. Language and pantry filters apply to loaded results. Pantry matches are hints needing review; quantities compare the source batch.":["apps/web/src/recipe-library-ui.js"],
  "Administration":["apps/web/src/admin-ui.js"],
  "Administrative settings are incomplete.":["apps/web/src/admin-model.js"],
  "AI agent name":["apps/web/src/recipe-community-ui.js"],
  "AI-assisted by":["apps/web/src/recipe-community-ui.js"],
  "AI-assisted recipe":["apps/web/src/recipe-community-ui.js"],
  "All languages":["apps/web/src/recipe-library-ui.js"],
  "approve":["apps/web/src/recipe-community-ui.js"],
  "Bio":["apps/web/src/recipe-community-ui.js"],
  "Choose a JSON recipe file under 20 KB.":["apps/web/src/recipe-community-ui.js"],
  "Choose unit":["apps/web/src/recipe-library-ui.js"],
  "Clear vote":["apps/web/src/recipe-community-ui.js"],
  "Comment":["apps/web/src/recipe-community-ui.js"],
  "Comment already submitted.":["apps/web/src/recipe-community-ui.js"],
  "Comment submitted for review.":["apps/web/src/recipe-community-ui.js"],
  "Comments":["apps/web/src/recipe-community-ui.js"],
  "Community moderation":["apps/web/src/recipe-community-ui.js"],
  "Community recipes":["apps/web/src/recipe-community-ui.js"],
  "Confirm publication rights before submitting.":["apps/web/src/recipe-community-ui.js"],
  "Confirm your ingredient matches, measurements and instructions.":["apps/web/src/recipe-library-model.js"],
  "Default country":["apps/web/src/admin-ui.js"],
  "Default interface language":["apps/web/src/admin-ui.js"],
  "Default servings":["apps/web/src/admin-ui.js"],
  "Default units":["apps/web/src/admin-ui.js"],
  "Diagnostics hourly limit":["apps/web/src/admin-ui.js"],
  "Disable value":["apps/web/src/admin-ui.js"],
  "Document email":["apps/web/src/admin-ui.js"],
  "Document hourly limit":["apps/web/src/admin-ui.js"],
  "Down vote":["apps/web/src/recipe-community-ui.js"],
  "Enter a positive yield and at least one required ingredient.":["apps/web/src/recipe-library-model.js"],
  "Global settings":["apps/web/src/admin-ui.js"],
  "hide":["apps/web/src/recipe-community-ui.js"],
  "Historical OCR candidate: the ingredient list is incomplete. Read the source text; pantry matching and personal recipe saving are disabled until complete transcription.":["apps/web/src/recipe-library-ui.js"],
  "Historical source; measurements and text may require correction.":["apps/web/src/recipe-library-ui.js"],
  "Human recipe":["apps/web/src/recipe-community-ui.js"],
  "I confirm this is an original recipe and I have rights to publish it under the recipe license.":["apps/web/src/recipe-community-ui.js"],
  "Ingredient in my kitchen":["apps/web/src/recipe-library-ui.js"],
  "Ingredients":["apps/web/src/recipe-community-ui.js"],
  "Keep existing value":["apps/web/src/admin-ui.js"],
  "License":["apps/web/src/recipe-community-ui.js"],
  "Measure every required ingredient in g, ml or count.":["apps/web/src/recipe-library-model.js"],
  "Moderation reason":["apps/web/src/recipe-community-ui.js"],
  "Name the AI agent for public attribution.":["apps/web/src/recipe-community-ui.js"],
  "New value":["apps/web/src/admin-ui.js"],
  "No changes to save.":["apps/web/src/admin-ui.js"],
  "Open recipe details":["apps/web/src/recipe-community-ui.js"],
  "Optional":["apps/web/src/recipe-library-ui.js"],
  "Original source":["apps/web/src/recipe-library-ui.js"],
  "Pending comments":["apps/web/src/recipe-community-ui.js"],
  "Pending recipes":["apps/web/src/recipe-community-ui.js"],
  "Post comment":["apps/web/src/recipe-community-ui.js"],
  "Preview recipe":["apps/web/src/recipe-community-ui.js"],
  "Public alias":["apps/web/src/recipe-community-ui.js"],
  "Public community profile":["apps/web/src/recipe-community-ui.js"],
  "Publish this profile":["apps/web/src/recipe-community-ui.js"],
  "Rate recipe":["apps/web/src/recipe-community-ui.js"],
  "Rating":["apps/web/src/recipe-community-ui.js"],
  "Read recipe & review quantities":["apps/web/src/recipe-library-ui.js"],
  "Recent recipes":["apps/web/src/recipe-community-ui.js"],
  "Recipe already submitted.":["apps/web/src/recipe-community-ui.js"],
  "Recipe attribution":["apps/web/src/recipe-community-ui.js"],
  "Recipe is no longer in this search; search again.":["apps/web/src/recipe-library-ui.js"],
  "Recipe JSON":["apps/web/src/recipe-community-ui.js"],
  "Recipe JSON file":["apps/web/src/recipe-community-ui.js"],
  "Recipe page repeats an earlier result":["apps/web/src/recipe-library-ui.js"],
  "Recipe submitted for review.":["apps/web/src/recipe-community-ui.js"],
  "reject":["apps/web/src/recipe-community-ui.js"],
  "Reload settings":["apps/web/src/admin-ui.js"],
  "Replace value":["apps/web/src/admin-ui.js"],
  "Reported protein per serving":["apps/web/src/recipe-community-ui.js"],
  "restore":["apps/web/src/recipe-community-ui.js"],
  "Review changes":["apps/web/src/admin-ui.js"],
  "Review the comment before submitting.":["apps/web/src/recipe-community-ui.js"],
  "Review the public profile.":["apps/web/src/recipe-community-model.js"],
  "Review the recipe before submitting.":["apps/web/src/recipe-community-model.js"],
  "Reviewed quantity":["apps/web/src/recipe-library-ui.js"],
  "Reviewed unit":["apps/web/src/recipe-library-ui.js"],
  "Save community profile":["apps/web/src/recipe-community-ui.js"],
  "Save confirmed settings":["apps/web/src/admin-ui.js"],
  "Save these reviewed administrative settings?":["apps/web/src/admin-ui.js"],
  "Searching shared recipes…":["apps/web/src/recipe-library-ui.js"],
  "Secure request delivery is unavailable.":["apps/web/src/recipe-community-ui.js"],
  "Self-reported; not a validated health claim.":["apps/web/src/recipe-community-ui.js"],
  "Service settings":["apps/web/src/admin-ui.js"],
  "Settings changed elsewhere. Refresh and review again.":["apps/web/src/admin-ui.js"],
  "Shared recipe search failed. {reason}":["apps/web/src/recipe-library-ui.js"],
  "Show next recipes":["apps/web/src/recipe-library-ui.js"],
  "Sign in as an administrator.":["apps/web/src/admin-ui.js"],
  "Source scaling: {rule}. Your personal recipe uses linear quantities.":["apps/web/src/recipe-library-ui.js"],
  "Steps":["apps/web/src/recipe-community-ui.js"],
  "Submit recipe for review":["apps/web/src/recipe-community-ui.js"],
  "Support email":["apps/web/src/admin-ui.js"],
  "Support hourly limit":["apps/web/src/admin-ui.js"],
  "Support retention days":["apps/web/src/admin-ui.js"],
  "Top recipes":["apps/web/src/recipe-community-ui.js"],
  "Transcribe the complete historical OCR ingredient list before creating a kitchen recipe.":["apps/web/src/recipe-library-model.js"],
  "Up vote":["apps/web/src/recipe-community-ui.js"],
  "Your reviewed recipe is saved in this kitchen.":["apps/web/src/recipe-library-ui.js"]
};

// Proposed meaning-pair fixture is independent of the runtime catalogue;
// language acceptance is a separate review, not established by this test.
const newArabic={
  "{v0} shown from {v1} loaded search results · {v2} published recipes, including OCR candidates. Continue browsing for later results; this list keeps the latest 200. Language and pantry filters apply to loaded results. Pantry matches are hints needing review; quantities compare the source batch.": "يُعرض {v0} من أصل {v1} من نتائج البحث المحمّلة · {v2} وصفات منشورة، بما فيها الوصفات المرشّحة من التعرّف الضوئي على الحروف (OCR). تابع التصفّح لرؤية النتائج التالية؛ تحتفظ هذه القائمة بأحدث 200 نتيجة. تنطبق مرشّحات اللغة ومخزون المطبخ على النتائج المحمّلة. مطابقات المخزون إرشادات تحتاج إلى مراجعة؛ وتُقارن الكميات على أساس دفعة الوصفة في المصدر.",
  "Administration": "الإدارة",
  "Administrative settings are incomplete.": "إعدادات الإدارة غير مكتملة.",
  "AI agent name": "اسم وكيل الذكاء الاصطناعي",
  "AI-assisted by": "بمساعدة وكيل الذكاء الاصطناعي",
  "AI-assisted recipe": "وصفة بمساعدة الذكاء الاصطناعي",
  "approve": "اعتماد",
  "Bio": "نبذة تعريفية",
  "Choose a JSON recipe file under 20 KB.": "اختر ملف وصفة بصيغة JSON حجمه أقل من 20 KB.",
  "Choose unit": "اختر الوحدة",
  "Clear vote": "إزالة تصويتي",
  "Comment": "تعليق",
  "Comment already submitted.": "أُرسل التعليق من قبل.",
  "Comment submitted for review.": "أُرسل التعليق للمراجعة.",
  "Comments": "التعليقات",
  "Community moderation": "الإشراف على محتوى المجتمع",
  "Community recipes": "وصفات المجتمع",
  "Confirm publication rights before submitting.": "أكّد امتلاك حقوق النشر قبل الإرسال.",
  "Confirm your ingredient matches, measurements and instructions.": "أكّد اختيارات مطابقة المكوّنات والقياسات والتعليمات التي راجعتها.",
  "Default country": "البلد الافتراضي",
  "Default interface language": "لغة الواجهة الافتراضية",
  "Default servings": "عدد الحصص الافتراضي",
  "Default units": "الوحدات الافتراضية",
  "Diagnostics hourly limit": "الحدّ الساعي للتشخيص",
  "Disable value": "تعطيل القيمة",
  "Document email": "إرسال المستندات بالبريد الإلكتروني",
  "Document hourly limit": "الحدّ الساعي للمستندات",
  "Down vote": "تصويت معارض",
  "Enter a positive yield and at least one required ingredient.": "أدخل عدد حصص موجبًا ومكوّنًا مطلوبًا واحدًا على الأقل.",
  "Global settings": "الإعدادات العامة",
  "hide": "إخفاء",
  "Historical OCR candidate: the ingredient list is incomplete. Read the source text; pantry matching and personal recipe saving are disabled until complete transcription.": "وصفة تاريخية مرشّحة من التعرّف الضوئي على الحروف (OCR): قائمة المكوّنات غير مكتملة. اقرأ نص المصدر؛ لا تتاح مطابقة مخزون المطبخ أو حفظ وصفة شخصية حتى يكتمل النسخ النصّي.",
  "Historical source; measurements and text may require correction.": "مصدر تاريخي؛ قد تحتاج القياسات والنص إلى تصحيح.",
  "Human recipe": "وصفة أعدّها شخص",
  "I confirm this is an original recipe and I have rights to publish it under the recipe license.": "أؤكّد أن هذه وصفة أصلية وأن لديّ الحق في نشرها بموجب ترخيص الوصفة.",
  "Ingredient in my kitchen": "المكوّن في مطبخي",
  "Keep existing value": "الإبقاء على القيمة الحالية",
  "License": "الترخيص",
  "Measure every required ingredient in g, ml or count.": "حدّد قياس كل مكوّن مطلوب بوحدة g أو ml أو count.",
  "Moderation reason": "سبب الإجراء الإشرافي",
  "Name the AI agent for public attribution.": "اذكر اسم وكيل الذكاء الاصطناعي لإسناد المساهمة إليه علنًا.",
  "New value": "القيمة الجديدة",
  "No changes to save.": "لا توجد تغييرات لحفظها.",
  "Open recipe details": "فتح تفاصيل الوصفة",
  "Pending comments": "تعليقات قيد المراجعة",
  "Pending recipes": "وصفات قيد المراجعة",
  "Post comment": "إرسال تعليق",
  "Preview recipe": "معاينة الوصفة",
  "Public alias": "الاسم المستعار الظاهر للجميع",
  "Public community profile": "الملف الشخصي العام في المجتمع",
  "Publish this profile": "إتاحة هذا الملف الشخصي للجميع",
  "Rate recipe": "تقييم الوصفة",
  "Rating": "التقييم",
  "Recent recipes": "أحدث الوصفات",
  "Recipe already submitted.": "أُرسلت الوصفة من قبل.",
  "Recipe attribution": "إسناد الوصفة",
  "Recipe is no longer in this search; search again.": "لم تعد الوصفة ضمن نتائج هذا البحث؛ ابحث مجددًا.",
  "Recipe JSON": "الوصفة بصيغة JSON",
  "Recipe JSON file": "ملف الوصفة بصيغة JSON",
  "Recipe page repeats an earlier result": "تكرّر صفحة الوصفات نتيجة سابقة",
  "Recipe submitted for review.": "أُرسلت الوصفة للمراجعة.",
  "reject": "رفض",
  "Reload settings": "إعادة تحميل الإعدادات",
  "Replace value": "استبدال القيمة",
  "Reported protein per serving": "البروتين المبلّغ عنه لكل حصة",
  "restore": "إظهار مجددًا",
  "Review changes": "مراجعة التغييرات",
  "Review the comment before submitting.": "راجع التعليق قبل إرساله.",
  "Review the public profile.": "راجع الملف الشخصي العام.",
  "Review the recipe before submitting.": "راجع الوصفة قبل إرسالها.",
  "Reviewed quantity": "الكمية التي راجعتها",
  "Reviewed unit": "الوحدة التي راجعتها",
  "Save community profile": "حفظ الملف الشخصي في المجتمع",
  "Save confirmed settings": "حفظ الإعدادات المؤكَّدة",
  "Save these reviewed administrative settings?": "هل تريد حفظ إعدادات الإدارة هذه بعد مراجعتها؟",
  "Searching shared recipes…": "جارٍ البحث في الوصفات المشتركة…",
  "Secure request delivery is unavailable.": "تسليم الطلب بأمان غير متاح.",
  "Self-reported; not a validated health claim.": "بيانات يبلّغ عنها صاحبها؛ وليست ادعاءً صحيًا جرى التحقّق منه.",
  "Service settings": "إعدادات الخدمات",
  "Settings changed elsewhere. Refresh and review again.": "تغيّرت الإعدادات في مكان آخر. أعد تحميل الإعدادات وراجعها مجددًا.",
  "Shared recipe search failed. {reason}": "تعذّر البحث في الوصفات المشتركة. {reason}",
  "Show next recipes": "عرض الوصفات التالية",
  "Sign in as an administrator.": "سجّل الدخول بحساب مسؤول.",
  "Source scaling: {rule}. Your personal recipe uses linear quantities.": "قاعدة تغيير الكميات في المصدر: {rule}. تستخدم وصفتك الشخصية كميات تتغيّر بالتناسب الخطي.",
  "Steps": "الخطوات",
  "Submit recipe for review": "إرسال الوصفة للمراجعة",
  "Support email": "البريد الإلكتروني للدعم",
  "Support hourly limit": "الحدّ الساعي للدعم",
  "Support retention days": "أيام الاحتفاظ ببيانات الدعم",
  "Top recipes": "الوصفات المتصدّرة",
  "Transcribe the complete historical OCR ingredient list before creating a kitchen recipe.": "انسخ قائمة المكوّنات التاريخية المستخرَجة بالتعرّف الضوئي على الحروف (OCR) كاملةً قبل إنشاء وصفة للمطبخ.",
  "Up vote": "تصويت مؤيّد",
  "Your reviewed recipe is saved in this kitchen.": "حُفظت الوصفة التي راجعتها في هذا المطبخ."
};

const existingArabic={
  "All languages": "جميع اللغات",
  "Ingredients": "المكوّنات",
  "Optional": "اختياري",
  "Original source": "المصدر الأصلي",
  "Read recipe & review quantities": "اقرأ الوصفة وراجع الكميات"
};

function nodes(root){
  const result=[];
  function visit(node){
    if(!node||typeof node!=='object')return;
    if(typeof node.type==='string')result.push(node);
    for(const value of Object.values(node)){
      if(Array.isArray(value))value.forEach(visit);
      else if(value&&typeof value==='object')visit(value);
    }
  }
  visit(root);return result;
}
const literals=node=>node?.type==='Literal'&&typeof node.value==='string'?[node.value]:
  node?.type==='ConditionalExpression'?[...literals(node.consequent),...literals(node.alternate)]:[];
const isCall=(node,name)=>['CallExpression','NewExpression'].includes(node.type)&&
  node.callee?.type==='Identifier'&&node.callee.name===name;

async function sourceCohort(){
  const entries=new Map();let moderationBindings=0;
  for(const name of sourceFiles){
    const file='apps/web/src/'+name;
    const tree=parse(await read(file),{ecmaVersion:'latest',sourceType:'module'});
    const record=node=>{for(const key of literals(node))if(key.trim()){
      if(!entries.has(key))entries.set(key,new Set());entries.get(key).add(file);
    }};
    for(const node of nodes(tree)){
      for(const [callee,index] of [['t',0],['setLocalizedText',1]])if(isCall(node,callee))record(node.arguments[index]);
      const helpers=name==='recipe-library-ui.js'?[['el',1]]:
        name==='recipe-community-ui.js'?[['e',2],['field',1]]:
        name==='admin-ui.js'?[['el',2],['field',0]]:[['Error',0]];
      for(const [callee,index] of helpers)if(isCall(node,callee))record(node.arguments[index]);
      if(node.type==='ArrayExpression'&&['recipe-library-ui.js','recipe-community-ui.js'].includes(name)&&
        node.elements.length&&node.elements.every(pair=>pair?.type==='ArrayExpression'&&pair.elements.length===2&&
          pair.elements.every(value=>value?.type==='Literal'&&typeof value.value==='string'))){
        for(const pair of node.elements)if(!canonicalUnits.includes(pair.elements[1].value))record(pair.elements[1]);
      }
      if(name==='recipe-community-ui.js'&&node.type==='ForOfStatement'&&
        node.left.type==='VariableDeclaration'&&node.left.declarations.length===1&&
        node.left.declarations[0].id.name==='action'&&node.right.type==='ArrayExpression'&&
        JSON.stringify(node.right.elements.map(value=>value?.value))===JSON.stringify(moderationLabels)){
        const body=nodes(node.body);
        // The actual finite variable reaches the localizing button helper AND
        // remains the canonical request action; no generic literal-array guess.
        assert.ok(body.some(child=>isCall(child,'e')&&child.arguments[1]?.value==='button'&&
          child.arguments[2]?.type==='Identifier'&&child.arguments[2].name==='action'));
        assert.ok(body.some(child=>child.type==='Property'&&child.key.name==='action'&&
          child.value.type==='Identifier'&&child.value.name==='action'));
        moderationBindings++;node.right.elements.forEach(record);
      }
    }
  }
  return {entries:Object.fromEntries([...entries].map(([key,files])=>[key,sorted(files)])),moderationBindings};
}

test('dynamic_ar_vocabulary_source_cohort_and_moderation_binding',async()=>{
  const actual=await sourceCohort();
  assert.equal(actual.moderationBindings,1);
  assert.equal(Object.keys(expectedCohort).length,98);
  assert.equal(Object.keys(newArabic).length,93);
  assert.deepEqual(actual.entries,expectedCohort);
  for(const unit of canonicalUnits)assert.equal(Object.hasOwn(actual.entries,unit),false);
  // Opaque IDs/paths, credential names and user/provenance expressions are not
  // display keys. No dynamic concatenation/template is promoted to a message.
  for(const excluded of ['SENTRY_DSN','BREVO_API_KEY','CC BY 4.0','CC0-1.0','human','ai',
    'keep','replace','disable','top','recent','/api/admin/settings','Changes: ',
    'Enter a replacement value for ',' · historical',' · source quantities available']){
    assert.equal(Object.hasOwn(actual.entries,excluded),false,excluded);
  }
});

test('dynamic_ar_vocabulary_exact_new_arabic_and_placeholder_interpolation',()=>{
  const missing=Object.keys(newArabic).filter(key=>!Object.hasOwn(ARABIC,key));
  assert.deepEqual(missing,[],'new finite-cohort Arabic mappings must all exist');
  for(const [key,translation] of Object.entries(newArabic)){
    assert.equal(ARABIC[key],translation,key);
    assert.deepEqual(placeholders(translation),placeholders(key),key);
    assert.equal(t(key,{},'ar'),translation,key);
    const values=Object.fromEntries(placeholders(key).map(name=>[name,'<plain-'+name+'>']));
    const expected=translation.replace(/\{(\w+)\}/g,(match,name)=>values[name]??match);
    assert.equal(t(key,values,'ar'),expected,key);
  }
});

test('dynamic_ar_vocabulary_english_fallback_and_plain_text_controls',()=>{
  assert.deepEqual(sorted([...Object.keys(existingArabic),...Object.keys(newArabic)]),sorted(Object.keys(expectedCohort)));
  for(const [key,translation] of Object.entries(existingArabic)){
    assert.equal(ARABIC[key],translation,key);assert.equal(t(key,{},'ar'),translation,key);
  }
  for(const key of Object.keys(expectedCohort))assert.equal(t(key,{},'en'),key);
  for(const [key,translation] of Object.entries(newArabic))assert.deepEqual(placeholders(translation),placeholders(key),key);
  const unknown='Synthetic unmapped vocabulary contract message';
  assert.equal(hasTranslation(unknown,'ar'),false);assert.equal(t(unknown,{},'ar'),unknown);
  assert.equal(t('Shared recipe search failed. {reason}',{reason:'<img src=x>'},'en'),
    'Shared recipe search failed. <img src=x>');
  const element={value:'approve',id:'synthetic-id',set innerHTML(_){throw Error('HTML assignment is forbidden');}};
  setLocalizedText(element,'All languages',{},'ar');
  assert.equal(element.textContent,existingArabic['All languages']);assert.equal(element.lang,'ar');
  setLocalizedText(element,unknown,{},'ar');
  assert.equal(element.textContent,unknown);assert.equal(element.lang,'en');assert.equal(element.dir,'auto');
  assert.equal(element.value,'approve');assert.equal(element.id,'synthetic-id');
});

test('dynamic_ar_vocabulary_display_changes_preserve_model_identity',()=>{
  const recipe={ingredients:canonicalUnits.map((unit,index)=>({ingredientId:'synthetic-'+index,
    name:'Original ingredient '+index,amount:2,unit}))};
  const stock=canonicalUnits.map((unit,index)=>({ingredient:'synthetic-'+index,quantity:1,unit}));
  const record={id:'recipe:synthetic',kind:'recipe',data:{name:'Original title',names:{ar:'عنوان تجريبي'},
    languages:['fr'],ingredients:[{name:'Original ingredient',originalText:'Original measured text',amount:2,unit:'g'}],
    directions:['Original instruction'],yield:{value:2}},provenance:{url:'https://source.example/recipe',
    licenseUrl:'https://source.example/license',attribution:'Original attribution',historyUrl:'https://source.example/history'}};
  const community={title:'  All languages  ',description:' Original user text ',servings:2,
    ingredients:[{name:' Optional ',quantity:2,unit:'g'}],steps:[' Original step '],language:'fr',license:'CC BY 4.0'};
  const profile={alias:' approve ',bio:' Original personal bio ',published:true};
  const settings={services:{synthetic:{label:'Original service'}},global:{defaults:{country:'AU',units:'metric',uiLanguage:'en'}}};
  const inputs={recipe,stock,record,community,profile,settings},before=structuredClone(inputs),previous=getLanguage();
  const project=()=>({match:matchRecipeStock(recipe,stock,{today:'2026-11-17'}),jsonld:recipeJSONLD(record),
    community:cleanCommunityRecipe(community),profile:cleanCommunityProfile(profile),settings:cleanAdminSettings(settings),
    preview:previewAdminChanges(settings,settings,credentialPatch({}))});
  try{
    setLanguage('en');const english=project();setLanguage('ar');const arabic=project();
    assert.deepEqual(arabic,english);assert.deepEqual(inputs,before);
    assert.deepEqual(arabic.match.missing.map(item=>item.unit),canonicalUnits);
    assert.deepEqual(arabic.match.missing.map(item=>item.ingredient),['synthetic-0','synthetic-1','synthetic-2']);
    assert.equal(arabic.community.title,'All languages');assert.equal(arabic.profile.alias,'approve');
    assert.equal(arabic.jsonld['@id'],record.id);assert.equal(arabic.jsonld.creditText,record.provenance.attribution);
    assert.deepEqual(arabic.jsonld.recipeIngredient,['Original measured text']);
    assert.equal(localizedField(record,'name','ar').value,'عنوان تجريبي');assert.deepEqual(record,before.record);
  }finally{setLanguage(previous);}
});

test('dynamic_ar_vocabulary_generated_catalogues_report_partial_coverage',async()=>{
  const english=JSON.parse(await read('apps/web/assets/locales/en.json'));
  const report=JSON.parse(await read('docs/i18n-coverage.json'));
  const keys=Object.keys(english),entries=Object.keys(report.entries);
  assert.equal(report.schema,'offmenu-ui-catalogue/1');assert.equal(report.sourceLanguage,'en');
  assert.deepEqual(keys,entries);assert.equal(report.messages,keys.length);
  const translated=keys.filter(key=>Object.hasOwn(ARABIC,key));
  assert.equal(report.arabicTranslated,translated.length);assert.equal(report.arabicMissing,keys.length-translated.length);
  assert.equal(report.arabicComplete,false);assert.ok(report.arabicMissing>0);
  // These are conservative extraction candidates, not a count of reviewed UI.
  for(const key of keys){assert.equal(english[key],key);assert.equal(report.entries[key].arabic,Object.hasOwn(ARABIC,key));}
  const missing=Object.keys(expectedCohort).filter(key=>!Object.hasOwn(english,key)||!report.entries[key]?.arabic);
  assert.deepEqual(missing,[],'generated files must include the newly mapped finite cohort');
  for(const key of Object.keys(expectedCohort))assert.ok(report.entries[key].sources.includes('apps/web/src/locales/ar.js'),key);
  // The global extractor does not follow the moderation action variable. Its
  // actual display binding is established by the bounded AST test above, not
  // by requiring fabricated explicit-ui classification or source attribution.
});

test('dynamic_ar_vocabulary_generated_extension_is_current_without_writes',async()=>{
  const path='apps/retailer-extension/popup.js',before=await read(path);
  const result=await checkGeneratedExtension(new URL('../../',import.meta.url).pathname);
  assert.equal(await read(path),before,'read-only extension check must not modify committed bytes');
  assert.equal(result.status,'current',JSON.stringify(result));
  assert.equal(result.generated.sha256,result.committed?.sha256);
});
