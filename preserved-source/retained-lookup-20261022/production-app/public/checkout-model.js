export function locationKey(location){return `${location?.area||'Unassigned'} / ${location?.shelf||'Unsorted'}`;}
export function finishInventory(existing,session){
 if(!session||!['shelf','shopping','waste'].includes(session.mode)||typeof session.area!=='string'||!session.area.trim()||session.area.length>60||!String(session.shelf||'').trim()||!Array.isArray(session.items)||!session.items.length)throw Error('Scan at least one item and choose its shelf.');
 if(session.mode==='waste'){const ids=new Set();for(const item of session.items){const source=existing.find(l=>l.id===item.id);if(!source||(source.location?.area||'Unassigned')!==session.area||(source.location?.shelf||'Unsorted')!==session.shelf||source.barcode!==item.barcode||source.quantity!==item.quantity||source.unit!==item.unit||ids.has(item.id))throw Error('Cleanup stock changed. Review and rescan the source location.');const amount=item.discardQuantity??item.quantity;if(!Number.isFinite(amount)||amount<=0||amount>source.quantity)throw Error('Discard amount exceeds recorded stock.');ids.add(item.id);}return existing.flatMap(l=>{const item=session.items.find(i=>i.id===l.id);if(!item)return [l];const remaining=l.quantity-(item.discardQuantity??item.quantity);return remaining>0?[{...l,quantity:remaining}]:[];});}
 const location={area:session.area,shelf:session.shelf.trim()};
 const items=session.items.map(item=>({...item,location,checkedAt:session.startedAt}));
 if(new Set(items.map(i=>i.id)).size!==items.length)throw Error('Duplicate checkout items.');
 const retained=session.mode==='shelf'?existing.filter(item=>item.location?.area!==location.area||item.location?.shelf!==location.shelf):existing;
 return [...retained,...items];
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
 if(!/^\d{4,32}$/.test(code))throw Error('Invalid barcode.');
 return {id:crypto.randomUUID(),barcode:code,name:product?.name||'Unknown product · '+code,ingredient:ingredient||'unmapped',...packAmount(product),expires:null,needsReview:!product?.name||!ingredient||ingredient==='unmapped'};
}
// A code held in view counts once; removing it from view re-arms the scanner.
export function createScanGate(gap=800){let code='',lastSeen=0;return {read(next,now){const duplicate=next===code&&now-lastSeen<gap;code=next;lastSeen=now;return !duplicate;},miss(now){if(now-lastSeen>=gap)code='';},reset(){code='';lastSeen=0;}};}
