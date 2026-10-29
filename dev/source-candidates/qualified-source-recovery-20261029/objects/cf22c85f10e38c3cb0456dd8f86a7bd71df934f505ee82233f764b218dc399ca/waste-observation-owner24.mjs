// Owner 02/04 must bind storage and atomic session authorization; no provider calls.
const text = (v, max=200) => typeof v === 'string' && v.trim() && v.length <= max;
const date = v => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(v) && Number.isFinite(Date.parse(v)) && new Date(v).toISOString() === v;
export function validateWasteObservation(input, context) {
  if (!text(context?.accountId) || !text(context?.sessionEpoch) || context.consent !== true) throw Error('Account/session consent required');
  if (!input || input.accountId !== context.accountId || !text(input.id) || !text(input.receiptId) || !text(input.sourceId)) throw Error('Observation identity mismatch');
  if (!date(input.observedAt)) throw Error('Exact observation timestamp required');
  if (!text(input.provenance?.sourceRef,1000) || !text(input.provenance?.method)) throw Error('Observation provenance required');
  const quantity = input.quantity ?? null, unit = input.unit ?? null;
  if (quantity !== null && (!Number.isFinite(quantity) || quantity < 0 || !text(unit,30) || input.provenance.method !== 'measured')) throw Error('Measured quantity/unit required');
  if (unit !== null && !text(unit,30)) throw Error('Invalid observed unit');
  if (input.reason != null && !text(input.reason)) throw Error('Invalid reason');
  return {id:input.id,accountId:input.accountId,receiptId:input.receiptId,sourceId:input.sourceId,
    observedAt:input.observedAt,quantity,unit,reason:input.reason??null,
    provenance:{sourceRef:input.provenance.sourceRef,method:input.provenance.method}};
}
export function wasteObservationCoverage(records, context) {
  if (!Array.isArray(records) || records.length > 1000) throw Error('Bounded observation array required');
  const seen = new Set(), validated=records.map(row=>{
    const v=validateWasteObservation(row,context);if(seen.has(v.id))throw Error('Duplicate observation ID');seen.add(v.id);return v;
  });
  const known=validated.filter(v=>v.quantity!==null), quantities=new Map();
  for (const row of known) {
    const total=(quantities.get(row.unit)??0)+row.quantity;
    if (!Number.isFinite(total)) throw Error('Quantity total overflow');
    quantities.set(row.unit,total);
  }
  return {records:validated,coverage:{total:validated.length,knownQuantity:known.length,unknownQuantity:validated.length-known.length},
    quantities:[...quantities].map(([unit,quantity])=>({unit,quantity}))};
}
export async function persistWasteObservation({store,context,observation,expectedRevision}) {
  const row=validateWasteObservation(observation,context);
  if (!Number.isSafeInteger(expectedRevision) || expectedRevision<0) throw Error('Revision required');
  // read/CAS use a trusted context, never an account/session supplied in observation.
  const current=await store.read(context);
  if (current.accountId!==context.accountId || current.sessionEpoch!==context.sessionEpoch) throw Error('Storage scope mismatch');
  if (current.revision!==expectedRevision) throw Error('Revision conflict');
  const receipt=current.wasteReceipts?.find(r=>r.id===row.receiptId);
  const source=receipt?.items?.find(i=>i.id===row.sourceId);
  if (!source) throw Error('Confirmed receipt/source binding required');
  if (row.quantity!==null && (source.unit!==row.unit || !Number.isFinite(source.discardQuantity) || row.quantity>source.discardQuantity)) throw Error('Observation exceeds confirmed discard');
  const records=wasteObservationCoverage(current.observations??[],context).records;
  if (records.some(r=>r.id===row.id)) throw Error('Duplicate observation ID');
  const next=wasteObservationCoverage([...records,row],context).records;
  // CAS must recheck epoch, consent and revision atomically with the write (Owner 04).
  const saved=await store.compareAndSwap(context,expectedRevision,next);
  if (saved!==true) throw Error('Write conflict or authorization revoked');
  return {revision:expectedRevision+1,observation:row};
}
