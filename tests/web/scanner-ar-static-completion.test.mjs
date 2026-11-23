import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {ARABIC} from '../../apps/web/src/locales/ar.js';
import {setLanguage,t,hasTranslation,translateUI} from '../../apps/web/src/i18n.js';

// New regression pins, not independent linguistic or rendered-device certification.
const remaining = {
  "OffMenu · Continuous scanner": "OffMenu · ماسح مستمر",
  "Allow camera access if asked, then centre a barcode in the frame. If you prefer, type the code.": "اسمح باستخدام الكاميرا عند الطلب، ثم ضع الباركود في وسط الإطار. يمكنك أيضًا كتابة الرمز.",
  "Ready · loaded retained barcode identifiers": "جاهز · تم تحميل معرّفات الرموز الشريطية المحتفَظ بها",
  "Brand": "العلامة التجارية",
  "— · unmapped / missing evidence": "— · غير مربوط / الأدلة مفقودة",
  "Barcode · original": "الرمز الشريطي · الأصلي",
  "OffMenu": "OffMenu",
  "Interpreted source status": "حالة المصدر بحسب التفسير",
  "Category: Not yet identified": "الفئة: لم تُحدَّد بعد",
  "Not yet identified": "لم تُحدَّد بعد",
  "Ingredient match: Not yet identified": "مطابقة المكوّن: لم تُحدَّد بعد",
  "Pack size: Unknown": "حجم العبوة: غير معروف",
  "Selected Balanced Final OffMenu logo": "شعار OffMenu المختار «Balanced Final»",
  "Review selected source in kitchen ↗": "مراجعة المصدر المحدّد في المطبخ ↗",
  "Product readouts": "عروض بيانات المنتج",
  "Ingredients": "المكوّنات",
  "Nutrition": "التغذية",
  "Source": "المصدر",
  "Readout pages": "صفحات عرض البيانات",
  "Explore · Ready": "استكشاف · جاهز",
  "Session ·": "الجلسة ·",
  "Product readout": "عرض بيانات المنتج",
  "Source information and explicit unknowns. Inspection does not resolve identity or mutate inventory.": "معلومات المصدر وما هو غير معروف صراحةً. لا يحسم الاطّلاع الهوية ولا يغيّر المخزون.",
  "Configure here. The running scanner keeps its camera and readouts in fixed positions.": "اضبط الإعدادات هنا. يحافظ الماسح أثناء التشغيل على مواضع ثابتة للكاميرا وعروض البيانات.",
  "Data connection": "اتصال البيانات",
  "Real · loaded retained barcode identifiers": "فعلي · معرّفات الرموز الشريطية المحتفَظ بها والمحمّلة",
  "Real source records remain unresolved where evidence is missing.": "تبقى سجلات المصدر الفعلية غير محسومة حيث تغيب الأدلة.",
  "Explore · information only": "استكشاف · معلومات فقط",
  "Buy · shopping intent, not payment": "شراء · نية تسوّق، لا دفع",
  "Stock · unpacking intake": "تخزين · استقبال الأصناف عند تفريغها",
  "Audit · reconcile existing stock": "جرد · مطابقة المخزون الموجود",
  "Discard · stock outflow": "تخلّص · إخراج من المخزون",
  "Private saved-result connection": "اتصال خاص بنتيجة محفوظة",
  "Select the exact reviewed USDA result on this device. It stays in this tab’s memory. No upload, persistence or live fallback.": "اختر نتيجة USDA المحفوظة نفسها التي خضعت للمراجعة على هذا الجهاز. تبقى في ذاكرة علامة التبويب هذه. لا رفع ولا حفظ دائم ولا رجوع إلى مصدر مباشر.",
  "Import reviewed USDA saved result": "استيراد نتيجة USDA محفوظة خضعت للمراجعة",
  "Not loaded. Only the pinned reviewed file is eligible.": "لم يُحمَّل الملف. الملف المُراجع المثبّت بمرجع محدّد وحده مؤهّل.",
  "Enter Explore": "الدخول إلى الاستكشاف",
  "Inventory changes are unavailable until product eligibility and the existing pantry action binding are verified.": "تغييرات المخزون غير متاحة حتى يتم التحقّق من أهلية المنتج ومن الارتباط الحالي بإجراء مخزون المطبخ.",
  "Next identical pack": "العبوة المطابقة التالية",
  "Original characters and leading zeros are preserved. Choose the source namespace explicitly. A UPC-E hint is used only when you select it; eight digits alone do not imply UPC-E. No inventory changes or inferred product identity.": "تُحفَظ المحارف الأصلية والأصفار البادئة. اختر نطاق معرّفات المصدر صراحةً. لا يُستخدم تلميح UPC-E إلا عند اختياره؛ وجود ثمانية أرقام وحده لا يعني UPC-E. لا تغييرات في المخزون ولا استنتاج لهوية المنتج.",
  "Uses the bundled ZXing worker when native detection is unavailable. Image stays on this device. The camera resumes automatically after local photo decoding. A decoded code is not product qualification.": "يستخدم عامل ZXing المضمّن عندما لا يتوفر الكشف الأصلي. تبقى الصورة على هذا الجهاز. تُستأنف الكاميرا تلقائيًا بعد فك الرمز من الصورة محليًا. فك الرمز لا يعني تأهيل المنتج.",
  "Source namespace": "نطاق معرّفات المصدر",
  "Barcode · printed code": "رمز شريطي · رمز مطبوع",
  "USDA-FDC · source identifier, not a printed barcode": "USDA-FDC · معرّف مصدر، وليس رمزًا شريطيًا مطبوعًا",
  "Barcode representation hint": "تلميح صيغة الرمز الشريطي",
  "No hint · exact lexical lookup": "بلا تلميح · بحث مطابق للمحارف تمامًا",
  "UPC-E · explicitly known format": "UPC-E · صيغة معروفة صراحةً",
  "UPC-A · explicitly known format": "UPC-A · صيغة معروفة صراحةً",
  "EAN-13 · explicitly known format": "EAN-13 · صيغة معروفة صراحةً",
  "EAN-8 · explicitly known format": "EAN-8 · صيغة معروفة صراحةً",
  "GTIN-14 · only when known, not inferred from ITF": "GTIN-14 · فقط عند معرفته، ولا يُستنتَج من ITF",
  "Matching source records": "سجلات المصادر المطابقة",
  "Retry camera": "أعِد محاولة الكاميرا"
};
const scannerURL = new URL('../../apps/web/assets/shelf-scanner.html',import.meta.url);
function staticKeys(html) {
  const decode = value => value.replace(/&quot;/g,'"').replace(/&#39;/g,"'")
    .replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');
  return [...new Set([...html.matchAll(/data-i18n(?:-[\w-]+)?="([^"]*)"/g)]
    .map(match=>decode(match[1])))];
}

test('remaining static scanner Arabic pairs preserve English and identifier spellings',()=>{
  assert.equal(Object.keys(remaining).length,53);
  for (const [key,expected] of Object.entries(remaining)) {
    assert.equal(ARABIC[key],expected,key);
    assert.equal(hasTranslation(key,'ar'),true,key);
    assert.equal(t(key,{},'ar'),expected,key);
    assert.equal(t(key,{},'en'),key,key);
  }
  assert.equal(t('OffMenu',{},'ar'),'OffMenu','proper brand is preserved intentionally');
  for (const key of ['USDA-FDC:0000123','0000123456789','UPC-E','Unreviewed source statement']) {
    assert.equal(t(key,{},'ar'),key,'unreviewed identities/source statements remain untouched');
  }
});

const retiredPublicCopy=new Set([
 'Ready · loaded retained barcode identifiers','Data connection','Real · loaded retained barcode identifiers',
 'Real source records remain unresolved where evidence is missing.',
]);
const activeScannerKeys=Object.keys(remaining).filter(key=>!retiredPublicCopy.has(key));

test('remaining static scanner scope is actual decoded HTML with no static fallback',async()=>{
  const keys=staticKeys(await readFile(scannerURL,'utf8'));
  assert.equal(keys.length,108,'selected static inventory only, not dynamic runtime text');
  assert.ok(keys.includes('Lookup unavailable.'));
  for(const key of retiredPublicCopy)assert.ok(!keys.includes(key),key);
  for (const key of activeScannerKeys) assert.ok(keys.includes(key),key);
  for (const key of keys) assert.equal(hasTranslation(key,'ar'),true,key);
});

test('remaining scanner text and accessible-label translation leaves form identity unchanged',()=>{
  const text={textContent:'Source',getAttribute:()=> 'Source'};
  const input={id:'saved-file',value:'unchanged-file-reference',namespace:'usda-fdc',
    getAttribute:()=> 'Import reviewed USDA saved result',setAttribute(name,value){this[name]=value;}};
  const root={documentElement:{},querySelectorAll(selector){
    return selector==='[data-i18n]'?[text]:selector==='[data-i18n-aria-label]'?[input]:[];
  }};
  setLanguage('ar');
  try {
    translateUI(root);
    assert.equal(text.textContent,remaining.Source);
    assert.equal(input['aria-label'],remaining['Import reviewed USDA saved result']);
    assert.deepEqual([input.id,input.value,input.namespace],['saved-file','unchanged-file-reference','usda-fdc']);
    assert.deepEqual(root.documentElement,{lang:'ar',dir:'rtl'});
  } finally {setLanguage('en');}
});

test('remaining scanner catalogue evidence is source-bound without whole-language completeness',async()=>{
  const report=JSON.parse(await readFile(new URL('../../docs/i18n-coverage.json',import.meta.url),'utf8'));
  for (const key of activeScannerKeys) {
    const entry=report.entries[key];
    assert.equal(entry?.arabic,true,key);
    assert.equal(entry.classification,'explicit-ui',key);
    assert.ok(entry.sources.includes('apps/web/assets/shelf-scanner.html'),key);
  }
  assert.equal(report.arabicComplete,false);
  assert.ok(report.arabicMissing>0,'static scanner coverage is not the full dynamic/product catalogue');
});
