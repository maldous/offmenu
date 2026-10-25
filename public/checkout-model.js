import {validateLot} from './model.js';
import {SCANNER_COMPLETION,copyPublicProductReference} from './scanner-kitchen-handoff.js';
import {t} from './i18n.js';
export function locationKey(location){return `${location?.area||'Unassigned'} / ${location?.shelf||'Unsorted'}`;}
export function finishInventory(existing,session){
 if(!session||!['shelf','shopping','waste'].includes(session.mode)||typeof session.area!=='string'||!session.area.trim()||session.area.length>60||!String(session.shelf||'').trim()||!Array.isArray(session.items)||!session.items.length)throw Error(t('Scan at least one item and choose its shelf.'));
 if(session.mode==='waste'){const ids=new Set();for(const item of session.items){const source=existing.find(l=>l.id===item.id);if(!source||(source.location?.area||'Unassigned')!==session.area||(source.location?.shelf||'Unsorted')!==session.shelf||source.barcode!==item.barcode||source.quantity!==item.quantity||source.unit!==item.unit||ids.has(item.id))throw Error(t('Cleanup stock changed. Review and rescan the source location.'));const amount=item.discardQuantity??item.quantity;if(!Number.isFinite(amount)||amount<=0||amount>source.quantity)throw Error(t('Discard amount exceeds recorded stock.'));ids.add(item.id);}return existing.flatMap(l=>{const item=session.items.find(i=>i.id===l.id);if(!item)return [l];const remaining=l.quantity-(item.discardQuantity??item.quantity);return remaining>0?[{...l,quantity:remaining}]:[];});}
 const location={area:session.area,shelf:session.shelf.trim()};
 const items=session.items.map(item=>({...item,location,checkedAt:session.startedAt}));
 if(new Set(items.map(i=>i.id)).size!==items.length)throw Error(t('Duplicate checkout items.'));
 const replayed=new Set();
 if(session.scannerCompletion?.schema===SCANNER_COMPLETION){
  for(const item of items){const prior=existing.find(l=>l.id===item.id);if(!prior)continue;if(JSON.stringify(validateLot(prior))!==JSON.stringify(validateLot(item)))throw Error('Scanner completion conflicts with saved inventory. Review the receipt.');replayed.add(item.id);}
  if(replayed.size===items.length)return existing;
  if(replayed.size)throw Error('Scanner completion conflicts with partially changed stock. Review the receipt.');
 }
 const retained=session.mode==='shelf'?existing.filter(item=>item.location?.area!==location.area||item.location?.shelf!==location.shelf):existing;
 const updated=[...retained,...items.filter(item=>!replayed.has(item.id))];
 if(new Set(updated.map(i=>i.id)).size!==updated.length)throw Error(t('Duplicate checkout items.'));
 return updated;
}
export function nutritionRows(product){
 const n=product?.nutriments||{};
 return [['Energy','energy-kcal_100g','kcal'],['Protein','proteins_100g','g'],['Sugars','sugars_100g','g'],['Salt','salt_100g','g']].map(([label,key,unit])=>({label,value:typeof n[key]==='number'&&Number.isFinite(n[key])?Number(n[key].toPrecision(3)):null,unit}));
}
export function packAmount(product){
 let amount=Number(product?.product_quantity),unit=String(product?.product_quantity_unit||'').toLowerCase();
 if(!(amount>0&&Number.isFinite(amount))||!['g','kg','ml','l'].includes(unit)){const m=String(product?.quantity||'').match(/^\s*([\d.]+)\s*(g|kg|ml|l)\s*$/i);if(!m)return {quantity:1,unit:'count',amountBasis:'package'};amount=Number(m[1]);unit=m[2].toLowerCase();}
 if(unit==='kg'){amount*=1000;unit='g';}if(unit==='l'){amount*=1000;unit='ml';}
 return amount>0&&Number.isFinite(amount)?{quantity:amount,unit,amountBasis:'full-pack'}:{quantity:1,unit:'count',amountBasis:'package'};
}
export function makeAutoLot(code,product,ingredient='unmapped'){
 if(!/^\d{4,32}$/.test(code))throw Error(t('Invalid barcode.'));
 return {id:crypto.randomUUID(),barcode:code,name:product?.name||'Unknown product · '+code,ingredient:ingredient||'unmapped',...packAmount(product),expires:null,needsReview:!product?.name||!ingredient||ingredient==='unmapped',...(product?.sourceObservationReference?{sourceObservationReference:product.sourceObservationReference}:{}),...(product?.publicProductReference?{publicProductReference:copyPublicProductReference(product.publicProductReference,code)}:{})};
}
// A code held in view counts once; removing it from view re-arms the scanner.
export function createScanGate(gap=800){let code='',lastSeen=0;return {read(next,now){const duplicate=next===code&&now-lastSeen<gap;code=next;lastSeen=now;return !duplicate;},miss(now){if(now-lastSeen>=gap)code='';},reset(){code='';lastSeen=0;}};}
