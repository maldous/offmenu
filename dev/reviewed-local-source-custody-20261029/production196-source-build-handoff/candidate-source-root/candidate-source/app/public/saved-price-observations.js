import {recordPermission} from './record-policy.js';
import {validateRecords} from './unified-data.js';
import {t} from './i18n.js';

// Match only the supplied lexical barcode. A product match does not establish
// pack, promotion, tax, delivery or comparison equivalence.
export function selectSavedPriceObservations(records,{barcode,country='',serverAuthorized=false}={}){
 if(typeof barcode!=='string'||!/^\d{4,32}$/.test(barcode)||!Array.isArray(records))return [];
 return records.filter(record=>{
  try{
   validateRecords([record]);
   return record.kind==='priceObservation'&&
    Array.isArray(record.data.identifiers)&&record.data.identifiers.some(id=>id.system==='barcode'&&id.value===barcode)&&
    (!country||record.countries.includes(country))&&
    (serverAuthorized||recordPermission(record,{action:'display',market:country}).allowed);
  }catch{return false;}
 });
}

// request must be the application's existing account-bound sessionFetch.
// Account records are authorized by privateRecordsPage's current display policy;
// local profile imports must independently pass the existing browser policy.
export async function loadPriceObservations({barcode,country='',profile,getIdentity,request}){
 const started=getIdentity(),check=()=>{if(getIdentity()!==started)throw Error(t('Account changed. Retry from your current account.'));};
 if(!/^\d{4,32}$/.test(barcode))throw Error(t('Enter a numeric barcode.'));
 const local=selectSavedPriceObservations(profile?.dataRecords,{barcode,country});
 const cloud=[];let savedError=null,upstreamError=null,upstream={items:[]};
 async function read(path){const response=await request(path,{signal:AbortSignal.timeout(15000)});check();const value=await response.json();check();if(!response.ok)throw Error(t('Price lookup unavailable'));if(!value||typeof value!=='object'||Array.isArray(value))throw Error('Invalid price response');return value;}
 await Promise.all([
  (async()=>{if(!started?.owner)return;try{let cursor='';const seen=new Set();do{
   const page=await read('/api/data/records?'+new URLSearchParams({kind:'priceObservation',country,limit:'100',cursor}));
   if(!Array.isArray(page.records))throw Error('Invalid saved records response');
   cloud.push(...selectSavedPriceObservations(page.records,{barcode,country,serverAuthorized:true}));
   cursor=page.nextCursor||'';if(cursor&&seen.has(cursor))throw Error('Repeated saved records cursor');seen.add(cursor);
  }while(cursor);}catch(error){savedError=error;}})(),
  (async()=>{try{const value=await read('/api/prices?barcode='+encodeURIComponent(barcode));if(!Array.isArray(value.items||value.results||[]))throw Error('Invalid price observations');upstream=value;}catch(error){upstreamError=error;}})()
 ]);
 check();
 // The account copy takes precedence over a local copy of the same observation.
 const saved=[...new Map([...selectSavedPriceObservations(local,{barcode,country}),...cloud].map(row=>[row.id,row])).values()];
 const observations=upstream.items||upstream.results||[];
 return {saved,savedError,upstreamError,upstream:{...upstream,items:Array.isArray(observations)?observations.filter(r=>!country||(r.location?.osm_address_country_code||'').toUpperCase()===country):[]}};
}

export function renderSavedPriceObservations(target,records){
 const text=(tag,value)=>{const n=document.createElement(tag);n.textContent=value;n.dir='auto';return n;};
 for(const record of records){const d=record.data,p=record.provenance,box=document.createElement('article');
  box.append(text('h3',d.retailer?.name||t('Store not supplied')),
   text('strong',(d.currency||t('Currency unknown'))+' '+(d.amount??t('Unknown amount'))),
   text('p',(d.observedAt||t('Date unknown'))+' · '+(d.retailer?.location||record.countries.join(', ')||t('Country unknown'))),
   text('small',t('Saved observation · dated observation, not verified current stock')),
   text('p',p.attribution+' · '+p.sourceId+' · '+(p.recordId??record.id)));
  const details=document.createElement('details');details.append(text('summary',t('Unified record, provenance & licence')),text('pre',JSON.stringify(record,null,2)));box.append(details);target.append(box);
 }
}
