import {COUNTRY_CODES} from '../public/countries.js';

// These are application defaults and service controls, never personal profiles.
export function defaultGlobalSettings(){
  return {defaults:{country:'',units:'metric',servings:2,uiLanguage:'en'},
    features:{supportEmail:true,documentEmail:true},
    limits:{supportRetentionDays:30,diagnosticsHourlyLimit:30,supportHourlyLimit:10,documentHourlyLimit:5}};
}
function exact(value,allowed,label){
  if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).some(key=>!allowed.includes(key)))throw Error('Invalid '+label+'.');
}
function integer(value,min,max,label){if(!Number.isSafeInteger(value)||value<min||value>max)throw Error('Invalid '+label+'.');return value;}
export function parseGlobalSettings(value = {}){
  exact(value,['defaults','features','limits'],'global settings');
  const result=defaultGlobalSettings();
  const defaults=value.defaults===undefined?{}:value.defaults,features=value.features===undefined?{}:value.features,limits=value.limits===undefined?{}:value.limits;
  exact(defaults,['country','units','servings','uiLanguage'],'application defaults');
  exact(features,['supportEmail','documentEmail'],'service features');
  exact(limits,Object.keys(result.limits),'service limits');
  Object.assign(result.defaults,defaults);
  const d=result.defaults;
  if(typeof d.country!=='string'||(d.country!==''&&!COUNTRY_CODES.includes(d.country)))throw Error('Invalid default country.');
  if(!['metric','imperial'].includes(d.units))throw Error('Invalid default units.');
  if(!['en','ar'].includes(d.uiLanguage))throw Error('Invalid default language.');
  if(typeof d.servings!=='number'||!Number.isFinite(d.servings)||d.servings<0.1||d.servings>100)throw Error('Invalid default servings.');
  for(const key of Object.keys(result.features)){if(features[key]!==undefined){if(typeof features[key]!=='boolean')throw Error('Invalid service feature.');result.features[key]=features[key];}}
  for(const key of Object.keys(result.limits))if(limits[key]!==undefined)result.limits[key]=integer(limits[key],1,key==='supportRetentionDays'?365:100,key);
  return result;
}
