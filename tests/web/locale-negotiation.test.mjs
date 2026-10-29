import test from 'node:test';
import assert from 'node:assert/strict';
import {acceptLanguages,excludedLocales,negotiateLocale,providerLocale,cookieValue,LOCALE_COOKIE,ACCOUNT_LOCALE_COOKIE} from '../../public/locale-negotiation.js';
import {requestLocale} from '../../cloud/locale.mjs';
import {browserLocaleDecision,applyAccountLanguage,setLanguage,onLanguagePreference} from '../../public/i18n.js';
import {validateState} from '../../cloud/state.mjs';
import {kitchenProjection} from '../../public/sync-model.js';

test('request languages respect quality, exclusions, subtags and invalid preferences',()=>{
  assert.deepEqual(acceptLanguages('ar;q=0,en-GB;q=0.8,fr;q=1,ar-EG;q=0.4'),['fr','en-GB','ar-EG']);
  assert.deepEqual(negotiateLocale({explicit:'fr',accepted:acceptLanguages('fr,en;q=0.8,ar;q=0.2'),country:'EG'}),{locale:'en',source:'accept-language'});
  assert.deepEqual(negotiateLocale({accepted:acceptLanguages('ar;q=0,fr;q=0.5'),country:'AU'}),{locale:'en',source:'default'});
  assert.deepEqual(acceptLanguages('ar;q=2,en;q=nope,*;q=0.2'),[]);
  assert.deepEqual(negotiateLocale({accepted:['fr'],excluded:excludedLocales('fr,ar;q=0'),country:'EG'}),{locale:'en',source:'default'});
});
test('explicit, device and profile selections outrank browser and weak country hints',()=>{
  const hints={explicit:'en',device:'ar',profile:'ar',provider:'ar',accepted:['ar'],country:'EG'};
  assert.deepEqual(negotiateLocale(hints),{locale:'en',source:'url'});
  delete hints.explicit;assert.equal(negotiateLocale(hints).source,'device');
  delete hints.device;assert.equal(negotiateLocale(hints).source,'profile');
  assert.deepEqual(negotiateLocale({accepted:['fr'],country:'EG'}),{locale:'ar',source:'geoip'});
  assert.deepEqual(negotiateLocale({accepted:['en'],country:'EG'}),{locale:'en',source:'accept-language'});
  assert.equal(providerLocale({user_metadata:{locale:'ar-EG'}}),'ar');
  assert.equal(providerLocale({userMetadata:{locale:'fr',language:'en-GB'}}),'en');
  assert.equal(providerLocale({email:'someone@arabic.example',name:'علي',timeZone:'Asia/Riyadh'}),null);
  assert.equal(cookieValue('offmenu_ui_language=%ZZ',LOCALE_COOKIE),null);
});
test('edge uses only verified account metadata and Cloudflare country; explicit choices avoid account I/O',async()=>{
  const request=new Request('https://offmenu.test/',{headers:{Cookie:'nf_jwt=test','Accept-Language':'en'}});Object.defineProperty(request,'cf',{value:{country:'EG'}});
  const db={prepare(sql){assert.match(sql,/user_id=\?/);return {bind(id){assert.equal(id,'alice');return {first:async()=>({state_json:JSON.stringify({profile:{uiLanguage:'ar'}})})};}};}};
  assert.equal((await requestLocale(request,{DB:db},async()=>({id:'alice',user_metadata:{locale:'en'}}))).source,'profile');
  assert.equal((await requestLocale(request,{},async()=>({id:'alice',user_metadata:{locale:'ar'}}))).source,'provider');
  assert.equal((await requestLocale(request,{},async()=>{throw Error('offline');})).locale,'en');
  const explicit=new Request('https://offmenu.test/?uiLanguage=en',{headers:{Cookie:'nf_jwt=test', 'X-Locale':'ar','CF-IPCountry':'EG'}});
  assert.equal((await requestLocale(explicit,{},async()=>{assert.fail('explicit preference must not trigger authentication');})).source,'url');
  const spoofed=new Request('https://offmenu.test/',{headers:{'X-Locale':'ar','CF-IPCountry':'EG'}});assert.equal((await requestLocale(spoofed)).locale,'en');
});
function browserRoot(){
  const cookies=new Map();return {documentElement:{dataset:{offmenuLocale:'ar',offmenuLocaleSource:'profile',offmenuCountry:'EG'}},get cookie(){return [...cookies].map(([k,v])=>k+'='+v).join('; ');},set cookie(value){const [pair]=value.split(';'),index=pair.indexOf('=');if(value.includes('Max-Age=0'))cookies.delete(pair.slice(0,index));else cookies.set(pair.slice(0,index),pair.slice(index+1));}};
}
test('browser uses current preferences, mirrors account hints and clears stale account hints on logout',()=>{
  const original=globalThis.location;globalThis.location={href:'https://offmenu.test/',protocol:'https:'};setLanguage('en');
  try{
    const root=browserRoot(),browser={languages:['en']},storage={getItem:()=>null};let reloads=0;
    // Cached HTML account metadata alone must not resurrect a logged-out account.
    assert.equal(browserLocaleDecision(root,storage,browser).locale,'en');
    assert.equal(applyAccountLanguage({user:{user_metadata:{locale:'ar'}},profile:{},root,storage,browser,reload:()=>reloads++}),true);
    assert.equal(cookieValue(root.cookie,ACCOUNT_LOCALE_COOKIE),'provider:ar');assert.equal(reloads,1);
    setLanguage('ar');assert.equal(applyAccountLanguage({user:{},profile:{uiLanguage:'ar'},root,storage,browser,reload:()=>reloads++}),false);
    assert.equal(cookieValue(root.cookie,ACCOUNT_LOCALE_COOKIE),'profile:ar');
    assert.equal(applyAccountLanguage({user:null,root,storage,browser,reload:()=>reloads++}),true);assert.equal(cookieValue(root.cookie,ACCOUNT_LOCALE_COOKIE),null);
    root.cookie=LOCALE_COOKIE+'=en';assert.equal(browserLocaleDecision(root,{getItem:()=> 'ar'},browser).locale,'ar');
  }finally{globalThis.location=original;setLanguage('en');onLanguagePreference(null);}
});
test('account interface locale survives validation and is excluded from shared kitchen projection',()=>{
  const state={inventory:[],products:{},recipes:[],profile:{country:'AU',units:'metric',servings:2,uiLanguage:'ar'},selections:[]};
  assert.equal(validateState(state).profile.uiLanguage,'ar');assert.equal(kitchenProjection(state).profile.uiLanguage,undefined);
  assert.throws(()=>validateState({...state,profile:{...state.profile,uiLanguage:'invalid'}}),/interface language/);
});
test('configured defaults never choose an explicitly excluded locale when another supported locale is available',async()=>{
 for(const [defaultLocale,header,wanted] of [['ar','fr, ar;q=0','en'],['en','fr, en;q=0','ar'],['ar','fr','ar']]){
  const request=new Request('https://offmenu.test/',{headers:{'Accept-Language':header}});
  const decision=await requestLocale(request,{SERVICE_GLOBAL_SETTINGS:JSON.stringify({defaults:{uiLanguage:defaultLocale}})});
  assert.equal(decision.locale,wanted);assert.equal(decision.source,'default');
 }
 assert.deepEqual(negotiateLocale({explicit:'ar',excluded:['ar'],defaultLocale:'en'}),{locale:'ar',source:'url'});
});
