import {acceptLanguages,excludedLocales,cookieValue,LOCALE_COOKIE,ACCOUNT_LOCALE_COOKIE,negotiateLocale,providerLocale,supportedLocale} from '../src/locale-negotiation.js';
import {parseGlobalSettings} from './global-settings.mjs';
import {t,hasTranslation,languageDirection} from '../src/i18n.js';

export async function requestLocale(request,env={},verifyUser) {
  const url=new URL(request.url),cookie=request.headers.get('Cookie')||'';
  const explicit=url.searchParams.get('uiLanguage'),saved=cookieValue(cookie,LOCALE_COOKIE);
  let profile,provider;
  // Avoid an Identity/DB round trip for public visitors or an explicit choice.
  if(!supportedLocale(explicit)&&!supportedLocale(saved)&&verifyUser&&(request.headers.has('Authorization')||/(?:^|;\s*)nf_jwt=/.test(cookie))){
    try{const user=await verifyUser(request);if(user){provider=providerLocale(user);if(env.DB){const row=await env.DB.prepare('SELECT state_json FROM user_state WHERE user_id=?').bind(user.id).first();profile=JSON.parse(row?.state_json||'null')?.profile?.uiLanguage;}}}catch{/* Authentication/storage outages must not break the public landing page. */}
  }
  // This cookie carries only a language hint, never identity or authorization.
  const accountHint=cookieValue(cookie,ACCOUNT_LOCALE_COOKIE)?.split(':');
  if(!profile&&!provider&&['profile','provider'].includes(accountHint?.[0])){
    if(accountHint[0]==='profile')profile=accountHint[1];else provider=accountHint[1];
  }
  const country=/^[A-Z]{2}$/.test(request.cf?.country||'')?request.cf.country:null;
  const accepted=request.headers.get('Accept-Language'),excluded=excludedLocales(accepted);
  const defaultLocale=parseGlobalSettings(JSON.parse(env.SERVICE_GLOBAL_SETTINGS||'{}')).defaults.uiLanguage;
  return {...negotiateLocale({explicit,cookie:saved,profile,provider,accepted:acceptLanguages(accepted),excluded,country,defaultLocale}),country,excluded,defaultLocale};
}

export function localizedHTML(response,decision) {
  const {locale,source,country}=decision,headers=new Headers(response.headers);
  headers.set('Content-Language',locale);
  headers.set('X-OffMenu-Locale-Source',source);
  headers.set('Vary','Accept-Language, Cookie');
  // Per-request geography/account choices must never enter a shared HTML cache.
  headers.set('Cache-Control','private, no-store');
  if(['profile','provider'].includes(source))headers.append('Set-Cookie',ACCOUNT_LOCALE_COOKIE+'='+source+':'+locale+'; Path=/; SameSite=Lax; Secure; Max-Age=31536000');
  const localized=new Response(response.body,{status:response.status,headers});
  const rewrite=new HTMLRewriter().on('html',{element(element){
    element.setAttribute('lang',locale);element.setAttribute('dir',languageDirection(locale));
    element.setAttribute('data-offmenu-locale',locale);element.setAttribute('data-offmenu-locale-source',source);
    element.setAttribute('data-offmenu-default-locale',decision.defaultLocale||locale);
    element.setAttribute('data-offmenu-excluded-locales',(decision.excluded||[]).join(','));
    if(country)element.setAttribute('data-offmenu-country',country);
  }}).on('[data-i18n]',{element(element){
    const key=element.getAttribute('data-i18n');element.setInnerContent(t(key,{},locale));
    element.setAttribute('lang',hasTranslation(key,locale)?locale:'en');
  }}).on('link[rel="manifest"]',{element(element){element.setAttribute('href',locale==='ar'?'/manifest-ar.webmanifest':'/manifest.webmanifest');}});
  rewrite.on('select[data-ui-language] option',{element(element){if(element.getAttribute('value')===locale)element.setAttribute('selected','');else element.removeAttribute('selected');}});
  for(const attribute of ['aria-label','placeholder','title','alt','content'])rewrite.on('[data-i18n-'+attribute+']',{element(element){element.setAttribute(attribute,t(element.getAttribute('data-i18n-'+attribute),{},locale));}});
  return rewrite.transform(localized);
}
