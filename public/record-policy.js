// Private use does not remove upstream restrictions. Unknown sources need a
// reviewed server policy; a checkbox cannot grant a commercial provider's rights.
export const RECORD_POLICY_VERSION='offmenu-record-use/1';
const openSources=new Set(['off','prices','usda','usda-files','afcd','ciqual','cofid','germany-bls','fineli','wikibooks','world-recipes','fsa-alerts','fsa-ratings','openfda']);
export const SENSITIVE_KINDS=new Set(['healthObservation','activity','intakeRecord']);
const ownSources=new Set(['personal-import','retailer-browser']);
export function recordPermission(record,{action='display',confirmed=false,policy,now=Date.now(),market=''}={}){
 const p=record.provenance||{},deny=reason=>({allowed:false,reason});
 if(SENSITIVE_KINDS.has(record.kind))return deny('Use the separately consented private health/history workflow');
 for(const key of ['retainUntil','accessExpiresAt'])if(p[key]&&(!Number.isFinite(Date.parse(p[key]))||Date.parse(p[key])<=now))return deny('Record retention or access expired');
 if(['withdrawn','quarantined'].includes(p.status))return deny('Source record unavailable');
 if(p.dependencies?.some(d=>d.allowed!==true||d.retainUntil&&Date.parse(d.retainUntil)<=now))return deny('An input dependency does not permit reuse');
 if(policy){
  if(policy.active!==true||policy.expiresAt&&(!Number.isFinite(Date.parse(policy.expiresAt))||Date.parse(policy.expiresAt)<=now))return deny('Source policy inactive or expired');
  if(!policy.actions?.includes(action)||!policy.audiences?.includes('private'))return deny('Source policy does not permit this private action');
  if(policy.countries?.length&&(!market||!policy.countries.includes(market)))return deny('Source policy does not permit this market');
  if(p.policyVersion&&p.policyVersion!==policy.version)return deny('Source policy changed; review the record again');
  return {allowed:true,version:policy.version};
 }
 if(openSources.has(p.sourceId))return {allowed:true,version:RECORD_POLICY_VERSION};
 if(ownSources.has(p.sourceId)&&(confirmed||p.privateUseConfirmed===true))return {allowed:true,version:RECORD_POLICY_VERSION,notice:'User-confirmed private import; no shared publication rights established'};
 return deny('Storage, export and derived reuse require a reviewed source policy. This provider response remains transient');
}
