// Source rights and quality are independent. All permissions default to denied.
export const POLICY_VERSION='offmenu-policy/1';
export function admission(policy,assertion,{owner,action='display',audience='private',market='',now=Date.now(),consent=false}={}){
 const no=reason=>({allowed:false,reason});
 if(!policy||policy.active!==true)return no('source policy unavailable');
 if(policy.expiresAt&&Date.parse(policy.expiresAt)<=now)return no('source policy expired');
 if(!policy.actions?.includes(action)||!policy.audiences?.includes(audience))return no('use not permitted');
 if(policy.countries?.length&&(!market||!policy.countries.includes(market)))return no('territory not permitted');
 if(audience==='private'&&assertion.owner!==owner)return no('owner mismatch');
 if(assertion.retainUntil&&Date.parse(assertion.retainUntil)<=now)return no('retention expired');
 if(['withdrawn','quarantined'].includes(assertion.status))return no('evidence unavailable');
 if(audience==='public'&&(assertion.personal===true||assertion.matchStatus!=='verified'))return no('privacy or identity review required');
 if(action==='promote'&&(!consent||!policy.sharedFields?.includes(assertion.predicate)))return no('contribution not admitted');
 if(assertion.dependencies?.some(d=>d.allowed!==true))return no('dependency not permitted');
 return {allowed:true,reason:'permitted',stale:!!assertion.freshUntil&&Date.parse(assertion.freshUntil)<=now};
}
export function canonicalGTIN(input){const s=String(input);if(!/^(\d{8}|\d{12}|\d{13}|\d{14})$/.test(s))return null;let sum=0;for(let i=s.length-2,j=0;i>=0;i--,j++)sum+=Number(s[i])*(j%2?1:3);return (10-sum%10)%10===Number(s.at(-1))?s.padStart(14,'0'):null;}
export function parseIdentifier(input){const original=String(input).trim();let gtin=canonicalGTIN(original),lot=null,expiry=null;try{const u=new URL(original);const parts=u.pathname.split('/').filter(Boolean),i=parts.indexOf('01');if(i>=0)gtin=canonicalGTIN(parts[i+1]);lot=u.searchParams.get('10');expiry=u.searchParams.get('17');const l=parts.indexOf('10');if(l>=0)lot=parts[l+1];}catch{}const m=original.match(/^\(01\)(\d{14})(?:\(17\)(\d{6}))?(?:\(10\)([^\x1d]+))?$/);if(m){gtin=canonicalGTIN(m[1]);expiry=m[2]||null;lot=m[3]||null;}return {original,gtin,lot,expiry,kind:gtin?'GTIN':'local-or-unresolved',origin:null};}
export function qualify(rule,evidence,{now=Date.now(),market='',subject=''}={}){
 if(!rule||!rule.predicate)return {status:'not_applicable',reason:'No rule selected'};
 const rows=evidence.filter(e=>e.predicate===rule.predicate&&(!subject||e.subject===subject)&&(!market||!e.market||e.market===market)&&e.status!=='withdrawn'&&e.matchStatus==='verified'&&(!e.validFrom||Date.parse(e.validFrom)<=now)&&(!e.validUntil||Date.parse(e.validUntil)>now)&&(!e.freshUntil||Date.parse(e.freshUntil)>now));
 if(!rows.length)return {status:'unknown',reason:'Current scoped evidence not established',automaticSelection:false};
 const values=rows.map(e=>JSON.stringify(e.value));if(new Set(values).size>1)return {status:'conflict',reason:'Sources disagree',evidenceIds:rows.map(e=>e.id),automaticSelection:false};
 if(rule.certifiedOnly&&rows.every(e=>e.evidenceClass!=='certified'))return {status:'unknown',reason:'Certification not established',automaticSelection:false};
 const value=rows[0].value,match=Array.isArray(value)?value.includes(rule.value):value===rule.value;
 const pass=rule.operator==='exclude'?!match:match;
 return {status:pass?'pass':'fail',reason:'Evaluated against current scoped assertions',evidenceIds:rows.map(e=>e.id),automaticSelection:pass};
}
export function ownershipPath(edges,start,target,{now=Date.now(),includeMinority=false}={}){const queue=[[start,[]]],seen=new Set();while(queue.length){const [id,path]=queue.shift();if(id===target)return {status:'matched',path};if(seen.has(id))continue;seen.add(id);for(const e of edges){if(e.subject!==id||e.matchStatus!=='verified'||!['control','accounting-parent',...(includeMinority?['minority']:[])].includes(e.predicate)||e.status==='withdrawn'||e.validFrom&&Date.parse(e.validFrom)>now||e.validUntil&&Date.parse(e.validUntil)<=now||e.freshUntil&&Date.parse(e.freshUntil)<=now)continue;queue.push([e.value,[...path,e.id]]);}}return {status:'unknown',path:[],reason:'No current evidenced control path; absence is not independence'};}
export function matchRecall(notice,lot){if(notice.market&&lot.market&&notice.market!==lot.market)return 'not-matched';if(!notice.gtin||canonicalGTIN(notice.gtin)!==canonicalGTIN(lot.barcode)||!canonicalGTIN(lot.barcode))return 'not-matched';if(notice.allBatches===true)return 'matched';if(!lot.lotCode)return 'possible';return notice.lots?.includes(lot.lotCode)?'matched':'not-matched';}
