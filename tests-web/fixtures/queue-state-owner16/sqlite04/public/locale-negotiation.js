// Shared browser/edge policy. Geography is a hint, never a profile preference.
export const SUPPORTED_LOCALES = Object.freeze(['en','ar']);
export const LOCALE_COOKIE = 'offmenu_ui_language';
export const ACCOUNT_LOCALE_COOKIE = 'offmenu_account_language';
const ARABIC_COUNTRIES = new Set(['AE','BH','DZ','EG','IQ','JO','KW','LB','LY','MA','MR','OM','PS','QA','SA','SD','SY','TN','YE']);

export function supportedLocale(value) {
  if(typeof value!=='string'||value.length>80)return null;
  const tag=value.trim().replaceAll('_','-').toLowerCase();
  if(!/^[a-z]{2,3}(?:-[a-z0-9]{2,8})*$/.test(tag))return null;
  const base=tag.split('-')[0];return SUPPORTED_LOCALES.includes(base)?base:null;
}
function languageRanges(header='') {
  return String(header).slice(0,4096).split(',').map((part,index)=>{
    const match=/^\s*([a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8})*|\*)(?:\s*;\s*q=(0(?:\.\d{0,3})?|1(?:\.0{0,3})?))?\s*$/.exec(part);
    return match?{tag:match[1],quality:match[2]===undefined?1:Number(match[2]),index}:null;
  }).filter(Boolean);
}
export const acceptLanguages=header=>languageRanges(header).filter(item=>item.quality>0&&item.tag!=='*').sort((a,b)=>b.quality-a.quality||a.index-b.index).map(item=>item.tag);
export const excludedLocales=header=>languageRanges(header).filter(item=>item.quality===0&&SUPPORTED_LOCALES.includes(item.tag.toLowerCase())).map(item=>item.tag.toLowerCase());
export function cookieValue(header,name) {
  const entry=String(header||'').split(';').map(part=>part.trim()).find(part=>part.startsWith(name+'='));
  try{return entry?decodeURIComponent(entry.slice(name.length+1)):null;}catch{return null;}
}
export function providerLocale(user) {
  // Identity may retain Google/OIDC locale under either metadata spelling.
  // Missing claims are normal; email, name and time zone do not define language.
  for(const metadata of [user?.user_metadata,user?.userMetadata,user]){
    for(const key of ['locale','language','preferred_language']){const locale=supportedLocale(metadata?.[key]);if(locale)return locale;}
  }
  return null;
}
export function negotiateLocale({explicit,device,cookie,profile,provider,accepted=[],excluded=[],country}={}) {
  for(const [source,value] of [['url',explicit],['device',device],['cookie',cookie],['profile',profile],['provider',provider]]){
    const locale=supportedLocale(value);if(locale)return {locale,source};
  }
  for(const value of accepted){const locale=supportedLocale(value);if(locale)return {locale,source:'accept-language'};}
  if(!excluded.includes('ar')&&ARABIC_COUNTRIES.has(String(country||'').toUpperCase()))return {locale:'ar',source:'geoip'};
  return {locale:'en',source:'default'};
}
