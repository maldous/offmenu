export const SERVICES_PREFERENCE_KEY = 'offmenu-third-party-consent-v1';
export const SERVICES_PREFERENCE_VERSION = 1;
export const CONSENT_CATEGORIES = Object.freeze(['privacy','analytics','diagnostics','support','advertising']);
export const COARSE_EVENTS = Object.freeze(['account_opened','backup_exported','recipe_opened','scan_completed','support_opened']);
export const DIAGNOSTIC_CODES = Object.freeze(['browser_error','browser_rejection','service_load_failed']);

export function defaultServicePreferences(){
  return {schemaVersion:SERVICES_PREFERENCE_VERSION,preferences:Object.fromEntries(CONSENT_CATEGORIES.map(category=>[category,false]))};
}

export function normaliseServicePreferences(value){
  const base=defaultServicePreferences();
  if(!value||typeof value!=='object'||value.schemaVersion!==SERVICES_PREFERENCE_VERSION||!value.preferences||typeof value.preferences!=='object')return base;
  for(const category of CONSENT_CATEGORIES)base.preferences[category]=value.preferences[category]===true;
  return base;
}

export function loadServicePreferences(storage=globalThis.localStorage){
  try{return normaliseServicePreferences(JSON.parse(storage?.getItem(SERVICES_PREFERENCE_KEY)||'null'));}catch{return defaultServicePreferences();}
}

export function saveServicePreferences(preferences,storage=globalThis.localStorage){
  const next=normaliseServicePreferences(preferences);
  try{storage?.setItem(SERVICES_PREFERENCE_KEY,JSON.stringify(next));}catch{/* Consent remains in memory when storage is unavailable. */}
  return next;
}

export function revokeServicePreferences(storage=globalThis.localStorage){
  const next=defaultServicePreferences();
  try{storage?.removeItem(SERVICES_PREFERENCE_KEY);}catch{/* Private browsing can deny storage access. */}
  return next;
}

const numeric=value=>typeof value==='number'&&Number.isSafeInteger(value)&&value>0||typeof value==='string'&&/^[1-9]\d{0,19}$/.test(value);
const numericString=value=>numeric(value)?String(value):null;
const adsClient=value=>typeof value==='string'&&/^ca-pub-\d{16}$/.test(value)?value:null;
const policyLanguage=value=>['en','en-GB','it','es','nl','fr','de','ru','pt','pt-BR','da'].includes(value)?value:'en';
export function validatedServiceConfig(value){
  if(!value||typeof value!=='object'||value.schemaVersion!==1)return null;
  const client=value.client&&typeof value.client==='object'?value.client:{};
  const consent=client.consent&&typeof client.consent==='object'?client.consent:{};
  const feedback=client.feedback&&typeof client.feedback==='object'?client.feedback:{};
  const ads=client.ads&&typeof client.ads==='object'?client.ads:{};
  const cleanUrl=url=>typeof url==='string'&&/^https:\/\/[a-z0-9.-]+(?:\/|$)/i.test(url)?url:null;
  const purposeId=typeof client.analytics?.purposeId==='string'&&/^[A-Za-z0-9_-]{1,100}$/.test(client.analytics.purposeId)?client.analytics.purposeId:null;
  return {schemaVersion:1,
    client:{diagnostics:{enabled:client.diagnostics?.enabled===true},analytics:{enabled:client.analytics?.enabled===true&&client.analytics?.provider==='zaraz',provider:'zaraz',purposeId},
      consent:{siteId:numericString(consent.siteId),cookiePolicyId:numericString(consent.cookiePolicyId),tcfEnabled:consent.tcfEnabled===true,policyLanguage:policyLanguage(consent.policyLanguage)},
      feedback:{productId:numericString(feedback.productId),boardUrl:cleanUrl(feedback.boardUrl)},
      ads:{client:adsClient(ads.client),slot:numericString(ads.slot),approved:ads.approved===true,personalized:ads.personalized===true}},
    services:Array.isArray(value.services)?value.services.filter(item=>item&&typeof item.id==='string').map(item=>({id:item.id,name:String(item.name||item.id),category:String(item.category||'other'),status:String(item.status||'setup-required'),reason:String(item.reason||'')})):[],
    links:{status:cleanUrl(value.links?.status),privacy:cleanUrl(value.links?.privacy),source:cleanUrl(value.links?.source)}};
}

export function tcfAdvertisingAllowed(tcData,ads={}){
  const event=tcData?.eventStatus, purpose=tcData?.purpose?.consents,vendor=tcData?.vendor?.consents;
  return ['tcloaded','useractioncomplete'].includes(event)&&purpose?.[1]===true&&vendor?.[755]===true&&(!ads.personalized||(purpose?.[3]===true&&purpose?.[4]===true));
}

export function vendorPlan(config,preferences,{tcfAdvertisingConsent=false}={}){
  const safe=validatedServiceConfig(config),choice=normaliseServicePreferences(preferences).preferences;
  if(!safe)return [];
  const plan=[];
  if(choice.privacy&&safe.client.consent.siteId&&safe.client.consent.cookiePolicyId)plan.push({vendor:'iubenda',category:'privacy',src:'https://cdn.iubenda.com/cs/iubenda_cs.js',siteId:safe.client.consent.siteId,cookiePolicyId:safe.client.consent.cookiePolicyId,policyLanguage:safe.client.consent.policyLanguage});
  if(choice.support&&safe.client.feedback.productId)plan.push({vendor:'sleekplan',category:'support',src:'https://client.sleekplan.com/sdk/e.js',productId:safe.client.feedback.productId});
  if(choice.advertising&&tcfAdvertisingConsent&&safe.client.consent.tcfEnabled&&safe.client.ads.approved&&safe.client.ads.client&&safe.client.ads.slot)plan.push({vendor:'adsense',category:'advertising',src:'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client='+safe.client.ads.client,client:safe.client.ads.client,slot:safe.client.ads.slot});
  return plan;
}

export function permittedCoarseEvent(name){return COARSE_EVENTS.includes(name)?name:null;}
export function permittedDiagnosticCode(code){return DIAGNOSTIC_CODES.includes(code)?code:null;}
