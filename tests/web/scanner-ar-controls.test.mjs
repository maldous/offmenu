import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {ARABIC} from '../../apps/web/src/locales/ar.js';
import {setLanguage,t,hasTranslation,translateUI} from '../../apps/web/src/i18n.js';

const controls = {
  "Back to scanner": "العودة إلى الماسح",
  "Barcode image": "صورة الرمز الشريطي",
  "Bench · front camera": "سطح عمل · الكاميرا الأمامية",
  "Camera": "الكاميرا",
  "Camera & sound settings": "إعدادات الكاميرا والصوت",
  "Camera connects automatically": "تعمل الكاميرا تلقائيًا",
  "Camera diagnostics not requested.": "لم يُطلب تشخيص الكاميرا.",
  "Check camera support": "التحقق من دعم الكاميرا",
  "Choose mode": "اختيار الوضع",
  "Choose your scanner mode": "اختر وضع الماسح",
  "Confirm identifier": "تأكيد المعرّف",
  "Connecting camera… Manual entry stays available.": "جارٍ تشغيل الكاميرا… يبقى الإدخال اليدوي متاحًا.",
  "Contrast": "التباين",
  "Current scan": "المسح الحالي",
  "Current session": "الجلسة الحالية",
  "Enter an identifier": "إدخال معرّف",
  "Expand": "توسيع",
  "Expand current product readout": "توسيع عرض بيانات المنتج الحالي",
  "Expand scanner options": "توسيع خيارات الماسح",
  "Exposure": "التعريض الضوئي",
  "Finish": "إنهاء",
  "Finish scanning": "إنهاء المسح",
  "Focus": "التركيز البؤري",
  "Focus distance": "مسافة التركيز البؤري",
  "Front camera": "الكاميرا الأمامية",
  "Live barcode camera": "كاميرا مباشرة لمسح الرموز الشريطية",
  "Live camera preview": "معاينة مباشرة للكاميرا",
  "Mirror": "عكس الصورة",
  "Mode": "الوضع",
  "Next": "التالي",
  "Next detail page": "صفحة التفاصيل التالية",
  "No items captured.": "لم تُلتقط أي أصناف.",
  "Original identifier": "المعرّف الأصلي",
  "Overview": "نظرة عامة",
  "Overview readout": "عرض النظرة العامة",
  "Pause": "إيقاف مؤقت",
  "Photo": "صورة",
  "Previous": "السابق",
  "Previous detail page": "صفحة التفاصيل السابقة",
  "Product details": "تفاصيل المنتج",
  "Product information": "معلومات المنتج",
  "Read a barcode image locally": "قراءة صورة رمز شريطي على هذا الجهاز",
  "Rear camera": "الكاميرا الخلفية",
  "Resume": "استئناف",
  "Rotate": "تدوير",
  "Scanner options": "خيارات الماسح",
  "Scanner tools": "أدوات الماسح",
  "Scanning setup": "إعداد المسح",
  "Sound off": "الصوت متوقف",
  "Stand · rear camera": "حامل · الكاميرا الخلفية",
  "Switch light and dark mode": "التبديل بين الوضعين الفاتح والداكن",
  "Type code": "إدخال الرمز",
  "Undo last": "التراجع عن الأخير",
  "Zoom": "التكبير"
};

test('selected scanner controls have explicit Arabic translations and unchanged English keys',()=>{
  for (const [key,expected] of Object.entries(controls)) {
    assert.equal(ARABIC[key],expected,key);
    assert.equal(hasTranslation(key,'ar'),true,key);
    assert.equal(t(key,{},'ar'),expected,key);
    assert.equal(t(key,{},'en'),key,key);
  }
});

test('selected controls remain bound to actual scanner source, not an invented text inventory',async()=>{
  const report=JSON.parse(await readFile(new URL('../../docs/i18n-coverage.json',import.meta.url),'utf8'));
  const scannerFiles=['apps/web/assets/shelf-scanner.html','apps/web/src/shelf-scanner.js'];
  for (const key of Object.keys(controls)) {
    const entry=report.entries[key];
    assert.equal(entry?.arabic,true,key);
    assert.equal(entry?.classification,'explicit-ui',key);
    assert.ok(entry.sources.some(file=>scannerFiles.includes(file)),key);
  }
  assert.equal(report.arabicComplete,false,'bounded keys do not complete the Arabic preview');
});

test('scanner accessible labels translate without changing identifiers, namespace or form values',()=>{
  const button={textContent:'Type code',getAttribute:()=> 'Type code'};
  const input={value:'0000123456789',id:'barcode',namespace:'barcode',
    getAttribute:()=> 'Original identifier',setAttribute(name,value){this[name]=value;}};
  const root={documentElement:{},querySelectorAll(selector){
    return selector==='[data-i18n]'?[button]:selector==='[data-i18n-aria-label]'?[input]:[];
  }};
  setLanguage('ar');
  try {
    translateUI(root);
    assert.deepEqual(root.documentElement,{lang:'ar',dir:'rtl'});
    assert.equal(button.textContent,controls['Type code']);
    assert.equal(input['aria-label'],controls['Original identifier']);
    assert.deepEqual([input.id,input.namespace,input.value],['barcode','barcode','0000123456789']);
    assert.equal(t('USDA-FDC:0000123'),'USDA-FDC:0000123');
    assert.equal(t('Unreviewed source statement'),'Unreviewed source statement');
  } finally {setLanguage('en');}
});
