export const HEALTH_IMPORT_SCHEMA = 'offmenu-health-import/1';
const units = {weight:'kg',height:'cm',steps:'count',activityMinutes:'min',sleepMinutes:'min',energyIntake:'kcal',proteinIntake:'g',sodiumIntake:'mg'};
const id = x => typeof x === 'string' && /^[\w.:/-]{1,200}$/.test(x);
const instant = x => typeof x === 'string' && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{3})?Z$/.test(x) && Number.isFinite(Date.parse(x)) && new Date(Date.parse(x)).toISOString().replace('.000Z','Z') === x.replace('.000Z','Z');
const keys = (x, allowed) => x && typeof x === 'object' && !Array.isArray(x) && Object.keys(x).every(k => allowed.includes(k));

// Portable private preview only. Trusted current account/consent/revision are
// supplied by the owner service. Uploaded claims cannot grant permissions.
export function validateHealthImport(serialized, context = {}) {
  const deny = reason => ({status:'blocked',reason,records:[],rejected:[],writes:false});
  if (typeof serialized !== 'string' || new TextEncoder().encode(serialized).length > 65536) return deny('Envelope must be JSON within 64 KiB');
  let e; try {e=JSON.parse(serialized);} catch {return deny('Invalid JSON');}
  const {owner, memberId, revision, consent, now} = context ?? {};
  if (!id(owner) || !id(memberId) || !Number.isSafeInteger(revision) || revision < 0 || !Number.isFinite(now)) return deny('Trusted account context required');
  if (!keys(e,['schemaVersion','owner','memberId','revision','source','records']) || e.schemaVersion !== HEALTH_IMPORT_SCHEMA || e.owner !== owner || e.memberId !== memberId || e.revision !== revision) return deny('Schema, account or revision mismatch');
  if (!keys(e.source,['kind','sourceId','exportId']) || !id(e.source.sourceId) || !id(e.source.exportId)) return deny('Source identity required');
  if (!['manual-export','vendor-export'].includes(e.source.kind)) return deny('Native Health Connect/HealthKit requires separately qualified device bridge; browser OAuth is insufficient');
  if (consent?.status !== 'active' || consent.owner !== owner || consent.memberId !== memberId || !id(consent.id) || !instant(consent.expiresAt) || Date.parse(consent.expiresAt) <= now || !Array.isArray(consent.purposes) || !consent.purposes.includes('health-import') || !Array.isArray(consent.sources) || !consent.sources.includes(e.source.sourceId) || !Array.isArray(consent.types)) return deny('Current scoped private consent required');
  if (!Array.isArray(e.records) || e.records.length > 100) return deny('At most 100 records per preview');
  const records=[], rejected=[], seen=new Set();
  for (const [index,r] of e.records.entries()) {
    let reason;
    if (!keys(r,['id','sourceRecordId','type','unit','value','observedAt']) || !id(r.id) || !id(r.sourceRecordId)) reason='Invalid record identity or fields';
    else if (!Object.hasOwn(units,r.type)) reason='Unsupported record type';
    else if (!consent.types.includes(r.type)) reason='Record type not consented';
    else if (r.unit !== units[r.type] || typeof r.value !== 'number' || !Number.isFinite(r.value) || r.value < 0 || (r.type==='steps' && !Number.isSafeInteger(r.value))) reason='Unsupported unit or value';
    else if (!instant(r.observedAt) || Date.parse(r.observedAt) > now) reason='Unambiguous nonfuture UTC timestamp required';
    else if ((r.type==='weight' && r.value>1000) || (r.type==='height' && r.value>300)) reason='Check measurement units';
    const identity=JSON.stringify([e.source.sourceId,r?.sourceRecordId,r?.type]);
    if (!reason && (seen.has(identity) || records.some(x=>x.id===r.id))) reason='Duplicate source identity or record ID';
    if (reason) {rejected.push({index,reason});continue;}
    seen.add(identity);
    records.push({...r,owner,memberId,source:e.source.sourceId,exportId:e.source.exportId,importMode:e.source.kind,consentId:consent.id,status:'imported-unverified'});
  }
  return {status:rejected.length?'needs-review':'preview',records,rejected,revision,writes:false,visibility:'private',overlap:'Separate sources retained; never sum overlapping observations',clinicalQualification:false};
}
