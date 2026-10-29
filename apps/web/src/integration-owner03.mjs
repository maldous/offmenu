import {analyzeWaste} from './waste-analysis-model.js';
import {setLocalizedText} from './i18n.js';

const named=v=>typeof v==='string' && v.trim().length>0;
const instant=v=>typeof v==='string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(v) && Number.isFinite(Date.parse(v)) && new Date(v).toISOString()===v;

// Read only the current profile supplied by setupInsights. This is not an access
// grant. Observation context must come from the authenticated caller, not profile.
export function wasteInsight(profile, {dates, context=null}={}) {
  if (!Array.isArray(dates) || dates.length>366 || dates.some(day=>typeof day!=='string' || !/^\d{4}-\d{2}-\d{2}$/.test(day))) throw TypeError('Bounded explicit insight dates required.');
  const receipts=Array.isArray(profile?.waste)?profile.waste:[];
  const selected=receipts.filter(r=>typeof r?.finishedAt==='string' && dates.includes(r.finishedAt.slice(0,10)));
  const legacyItems=selected.reduce((n,r)=>n+(Array.isArray(r.items)?r.items.length:0),0);
  const view={status:'legacy-unqualified',receiptCount:selected.length,legacyItems,
    quantityTotals:null,valueTotals:null,observations:null,unqualifiedQuantityItems:legacyItems,
    unknownValueItems:legacyItems,diagnostics:['Stock removal is not a measured-waste or cost observation.']};
  const rows=profile?.wasteObservations;
  if (!Array.isArray(rows)) {view.diagnostics.push('Observation history is unavailable; missing history does not mean zero waste.');return view;}
  if (!named(context?.accountId) || !named(context?.sessionEpoch) || context.consent!==true || context.canReadWasteObservations!==true) {
    view.diagnostics.push('Authoritative observation read context unavailable.');return view;
  }
  try {
    if (rows.length>1000) throw Error('Observation history exceeds bounded consumer limit.');
    const ids=new Set(),sources=new Set();
    const observations=[];
    for (const row of rows) {
      if (!instant(row?.observedAt)) throw Error('Observation time is invalid.');
      if (!dates.includes(row.observedAt.slice(0,10))) continue;
      if (row.accountId!==context.accountId || !named(row.id) || !named(row.receiptId) || !named(row.sourceId) ||
          !named(row.provenance?.sourceRef) || !named(row.provenance?.method)) throw Error('Observation scope/provenance incomplete.');
      if (ids.has(row.id)) throw Error('Duplicate observation identity.');
      ids.add(row.id);
      const binding=JSON.stringify([row.receiptId,row.sourceId]);
      if (sources.has(binding)) throw Error('Overlapping observations require owner reconciliation.');
      sources.add(binding);
      const candidates=selected.filter(r=>r.id===row.receiptId);
      const items=candidates.length===1 && Array.isArray(candidates[0].items)?candidates[0].items.filter(i=>i.id===row.sourceId):[];
      if (items.length!==1) throw Error('Stable confirmed receipt/source binding unavailable.');
      if (row.quantity!==null && (!Number.isFinite(row.quantity) || row.quantity<0 || !named(row.unit) ||
          row.provenance.method!=='measured' || items[0].unit!==row.unit || !Number.isFinite(items[0].discardQuantity) ||
          row.quantity>items[0].discardQuantity)) throw Error('Measured quantity exceeds confirmed source or is unsupported.');
      // Helper contract is positive-only. Preserve explicit zero, but withhold the
      // combined analysis rather than silently reclassify it as missing or fake 0.
      if (row.quantity===0) throw Error('Explicit measured zero preserved; positive-only analysis helper cannot aggregate it.');
      observations.push(structuredClone(row));
    }
    const result=analyzeWaste(observations.map(row=>({accountId:row.accountId,receiptId:row.receiptId,sourceId:row.sourceId,
      quantity:row.quantity,unit:row.unit,measured:row.quantity!==null,reason:row.reason,
      costSnapshot:null})),{accountId:context.accountId});
    view.status='observation-quantities';view.observations=observations;
    view.quantityTotals=result.quantities.length?result.quantities:null;
    // Cost/season/offer data are not part of the qualified observation contract.
    // No current product price, country, inferred pack size or cost join is used.
    view.diagnostics=['Partial recorded observations only; not all waste or person-level attribution.',
      'Cost snapshots are not admitted by this observation contract; waste value remains unknown.'];
    const measured=result.records.filter(r=>r.quantity!==null).length;
    view.unqualifiedQuantityItems=Math.max(0,legacyItems-measured);
  } catch(error) {
    view.status='analysis-unavailable';view.diagnostics=[error.message];
  }
  return view;
}

export function renderWasteInsight(target, data, dates) {
  const view=wasteInsight(data.profile,{dates,context:data.wasteContext});
  const doc=target.ownerDocument || globalThis.document;
  const panel=doc.createElement('article');panel.dataset.owner03='waste-insight';
  const add=(tag,message,values={})=>{const el=doc.createElement(tag);setLocalizedText(el,message,values);panel.append(el);};
  add('strong','Recorded cleanup evidence');
  add('p','{receipts} cleanup receipts · {items} recorded stock-removal items',{receipts:view.receiptCount,items:view.legacyItems});
  add('p','{unqualified} items without usable measured-waste coverage · {unknown} items with unknown waste value',{unqualified:view.unqualifiedQuantityItems,unknown:view.unknownValueItems});
  if (view.quantityTotals) for (const total of view.quantityTotals) add('p','{quantity} {unit} · partial measured observations',{quantity:total.quantity,unit:total.unit});
  for (const notice of view.diagnostics) add('small',notice);
  target.append(panel);
  return view;
}
