import test from 'node:test';
import assert from 'node:assert/strict';
import {Miniflare} from 'miniflare';

test('built Worker localizes the landing response with headers, hints, RTL and safe cache policy',async()=>{
  const worker=new Miniflare({modules:true,scriptPath:'dist/worker.mjs',compatibilityDate:'2026-08-06',cf:{country:'EG'}});
  try{
    const geo=await worker.dispatchFetch('https://offmenu.test/');const arabic=await geo.text();
    assert.equal(geo.status,200);assert.equal(geo.headers.get('content-language'),'ar');assert.equal(geo.headers.get('x-offmenu-locale-source'),'geoip');
    assert.match(arabic,/<html[^>]*lang="ar"[^>]*dir="rtl"/);assert.match(arabic,/data-offmenu-country="EG"/);assert.match(arabic,/يبدأ العشاء/);assert.match(arabic,/manifest-ar.webmanifest/);
    assert.match(arabic,/<option[^>]*value="ar"[^>]*selected/);assert.match(arabic,/<option[^>]*value="Dinner"[^>]*>العشاء<\/option>/);
    assert.equal(geo.headers.get('cache-control'),'private, no-store');assert.equal(geo.headers.get('vary'),'Accept-Language, Cookie');
    const english=await worker.dispatchFetch('https://offmenu.test/',{headers:{'Accept-Language':'ar;q=0,en-GB;q=1'}});
    assert.equal(english.headers.get('content-language'),'en');assert.match(await english.text(),/Dinner starts/);
    const excluded=await worker.dispatchFetch('https://offmenu.test/',{headers:{'Accept-Language':'fr,ar;q=0'}});assert.equal(excluded.headers.get('content-language'),'en');
    const saved=await worker.dispatchFetch('https://offmenu.test/',{headers:{Cookie:'offmenu_ui_language=en','Accept-Language':'ar'}});assert.equal(saved.headers.get('content-language'),'en');
    const explicit=await worker.dispatchFetch('https://offmenu.test/?uiLanguage=ar',{headers:{Cookie:'offmenu_ui_language=en'}});assert.equal(explicit.headers.get('content-language'),'ar');
    const account=await worker.dispatchFetch('https://offmenu.test/',{headers:{Cookie:'offmenu_account_language=profile:ar','Accept-Language':'en'}});assert.equal(account.headers.get('content-language'),'ar');assert.match(account.headers.get('set-cookie'),/offmenu_account_language=profile:ar/);
    const data=await worker.dispatchFetch('https://offmenu.test/data-workspace.html',{headers:{'Accept-Language':'ar'}});assert.equal(data.headers.get('content-language'),'ar');assert.match(await data.text(),/مساحة عمل بيانات الطعام/);
    const staticAsset=await worker.dispatchFetch('https://offmenu.test/style.css');assert.equal(staticAsset.headers.get('content-language'),null);
  }finally{await worker.dispose();}
});
