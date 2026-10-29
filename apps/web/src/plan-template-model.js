// Pure proposal only. Callers own authentication, current evidence and persistence.
const MAX_MEALS = 100;
const slots = ['Breakfast', 'Lunch', 'Dinner', 'Snack'];
const id = value => typeof value === 'string' && value.length > 0 && value.length <= 200;
const ids = value => Array.isArray(value) && value.length <= 100 && value.every(id) && new Set(value).size === value.length;
function dateNumber(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) throw Error('Invalid date');
  const number = Date.parse(value + 'T12:00:00Z');
  if (!Number.isFinite(number) || new Date(number).toISOString().slice(0, 10) !== value) throw Error('Invalid date');
  return number;
}
function monday(value) {
  const number = dateNumber(value);
  if (new Date(number).getUTCDay() !== 1) throw Error('Week must start Monday');
  return number;
}

/**
 * source: {accountId, reviewed: true, weekStart, entries}.
 * target: {accountId, weekStart, attendance: {'date|slot': memberIds}, equipmentIds,
 *          lunchboxPortability: {sourceEntryId: true|false}}.
 * requirements: {sourceEntryId: {equipmentIds, lunchbox: boolean}}.
 * newIds: one caller-supplied unique ID per source entry, checked against existingIds.
 * Missing bounds block the whole proposal; quantities are never scaled implicitly.
 */
export function copyReviewedWeek({source, target, requirements, newIds, existingIds = []}) {
  if (!source || !target || !id(source.accountId) || source.accountId !== target.accountId) throw Error('Account scope mismatch');
  if (source.reviewed !== true) throw Error('Reviewed source week required');
  const from = monday(source.weekStart), to = monday(target.weekStart);
  if (from === to) throw Error('Choose a new week');
  if (!Array.isArray(source.entries) || !source.entries.length || source.entries.length > MAX_MEALS) throw Error('Invalid template size');
  if (!ids(newIds) || newIds.length !== source.entries.length || !Array.isArray(existingIds) || existingIds.length > 10000 || !existingIds.every(id)) throw Error('Invalid target IDs');
  const used = new Set([...existingIds, ...source.entries.map(entry => entry?.id)]);
  if (newIds.some(value => used.has(value))) throw Error('Target ID collision');
  const sourceIds = new Set(), candidates = [], blockers = [];
  for (const [index, entry] of source.entries.entries()) {
    if (!entry || !id(entry.id) || sourceIds.has(entry.id) || !id(entry.recipeId) || !slots.includes(entry.slot) || !Number.isFinite(entry.servings) || entry.servings <= 0 || !ids(entry.memberIds) || !entry.memberIds.length) throw Error('Invalid template entry');
    sourceIds.add(entry.id);
    const offset = (dateNumber(entry.date) - from) / 86400000;
    if (offset < 0 || offset > 6) throw Error('Entry outside source week');
    const date = new Date(to + offset * 86400000).toISOString().slice(0, 10);
    dateNumber(date);
    const bounds = Object.hasOwn(requirements ?? {}, entry.id) ? requirements[entry.id] : undefined;
    const attendanceKey = `${date}|${entry.slot}`;
    const attendance = Object.hasOwn(target.attendance ?? {}, attendanceKey) ? target.attendance[attendanceKey] : undefined;
    const block = code => blockers.push({sourceEntryId: entry.id, date, code});
    if (!ids(attendance)) block('attendance-unknown');
    else if (entry.memberIds.some(member => !attendance.includes(member))) block('attendee-unavailable');
    if (!bounds || !ids(bounds.equipmentIds) || typeof bounds.lunchbox !== 'boolean') block('requirements-unknown');
    else {
      if (!ids(target.equipmentIds)) block('equipment-unknown');
      else if (bounds.equipmentIds.some(equipment => !target.equipmentIds.includes(equipment))) block('equipment-unavailable');
      if (bounds.lunchbox && (!Object.hasOwn(target.lunchboxPortability ?? {}, entry.id) || target.lunchboxPortability[entry.id] !== true)) block('lunchbox-portability-unconfirmed');
    }
    const candidate = structuredClone(entry);
    delete candidate.cookBatchId; // Existing cooked stock cannot travel to another week.
    candidate.id = newIds[index];
    candidate.date = date;
    candidates.push(candidate);
  }
  return {accountId: source.accountId, status: blockers.length ? 'blocked' : 'needs-target-review', entries: blockers.length ? [] : candidates, blockers};
}
