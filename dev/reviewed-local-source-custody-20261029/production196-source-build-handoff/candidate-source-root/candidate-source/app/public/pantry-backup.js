import {validateState} from '../cloud/state.mjs';
import {validateAccountMealState} from '../cloud/meal-preference-owner20.mjs';
import {validateLot} from './model.js';

// Ordinary pantry backups contain application state, never identity/service stores.
// Remove these reserved credential fields even in permissive product/recipe metadata.
export const BACKUP_EXCLUDED_KEYS=Object.freeze(['auth','authentication','authorization','credentials',
  'password','passphrase','token','accesstoken','refreshtoken','idtoken','apikey','secret','clientsecret',
  'privatekey','cookie','setcookie','session','authsession','sealedcredentials']);
function withoutCredentials(value){
  if(value===null||typeof value!=='object')return value;
  if(Array.isArray(value))return value.map(withoutCredentials);
  return Object.fromEntries(Object.entries(value)
    .filter(([key])=>!BACKUP_EXCLUDED_KEYS.includes(key.toLowerCase().replace(/[-_]/g,'')))
    .map(([key,item])=>[key,withoutCredentials(item)]));
}
function portableState(value,accountId){
  const scoped=Array.isArray(value.profile?.members)&&value.profile.members.some(member=>member&&Object.hasOwn(member,'mealPreferences'));
  // Existing account scope is checked, never inferred from the backup or remapped.
  if(scoped||accountId!==undefined&&accountId!==null)return validateAccountMealState(value,accountId);
  return validateState(value);
}
export function createPantryBackup(value,{accountId}={}){
  return {version:1,...portableState(withoutCredentials(value),accountId)};
}
export function restorePantryBackup(value,{accountId}={}){
  if(!value||value.version!==1||!Array.isArray(value.inventory)||value.inventory.length>10000)
    throw Error('Invalid pantry backup.');
  const clean=withoutCredentials(value),inventory=clean.inventory.map(validateLot);
  if(new Set(inventory.map(item=>item.id)).size!==inventory.length)throw Error('Backup has duplicate item IDs.');
  // Preserve the existing inventory-only v1 restore behavior and current profile.
  const state=clean.profile?portableState({...clean,inventory},accountId):null;
  return {inventory,state};
}
