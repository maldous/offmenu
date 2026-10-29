// Descriptive, owner-scoped civil schedules. No prescription or energy inference.
const DAY = 86400000;
const MAX_ENTRIES = 500;
const formatters = new Map();
function fail(message) { throw new Error(message); }
function text(value, name, max = 200) {
  if (typeof value !== 'string' || !value.trim() || value.length > max) fail(`Invalid ${name}`);
  return value;
}
function integer(value, min, max, name) {
  if (!Number.isInteger(value) || value < min || value > max) fail(`Invalid ${name}`);
  return value;
}
// Read only own data descriptors. Never invoke input getters or array methods.
function record(value, fields, name) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail(`Invalid ${name}`);
  const keys = Reflect.ownKeys(value);
  if (keys.length > fields.length || keys.some(key => !fields.includes(key))) fail(`Unsupported ${name} fields`);
  const captured = {};
  for (const key of keys) {
    const descriptor = Object.getOwnPropertyDescriptor(value, key);
    if (!descriptor || !Object.hasOwn(descriptor, 'value')) fail(`${name} must contain own data fields, not accessors`);
    captured[key] = descriptor.value;
  }
  return captured;
}
function denseArray(value, max, name) {
  if (!Array.isArray(value)) fail(`Invalid ${name}`);
  const length = Object.getOwnPropertyDescriptor(value, 'length')?.value;
  integer(length, 0, max, `${name} length`);
  const captured = [];
  for (let i = 0; i < length; i++) {
    const descriptor = Object.getOwnPropertyDescriptor(value, String(i));
    if (!descriptor || !Object.hasOwn(descriptor, 'value')) fail(`${name} must be dense own data slots, not holes or accessors`);
    captured.push(descriptor.value);
  }
  return captured;
}
function utc(year, month, day, hour = 0, minute = 0) {
  const date = new Date(0);
  date.setUTCFullYear(year, month - 1, day);
  date.setUTCHours(hour, minute, 0, 0);
  return date.getTime();
}
function civilDate(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) fail('Use an explicit civil date YYYY-MM-DD');
  const [year, month, day] = value.split('-').map(Number);
  if (year < 1900 || year > 9998) fail('Civil date outside supported years 1900..9998');
  const stamp = utc(year, month, day);
  if (new Date(stamp).toISOString().slice(0, 10) !== value) fail('Invalid civil date');
  return stamp;
}
function civilTime(value) {
  if (typeof value !== 'string' || !/^([01]\d|2[0-3]):[0-5]\d$/.test(value)) fail('Use an explicit civil time HH:mm');
  return value.split(':').map(Number);
}
function formatter(zone) {
  text(zone, 'time zone', 100);
  // Reject numeric offsets: recurrence needs a named civil-time zone.
  if (/^[+-]/.test(zone)) fail('Use a named time zone');
  if (!formatters.has(zone)) {
    let value;
    try { value = new Intl.DateTimeFormat('en-GB', {timeZone: zone, calendar: 'gregory', numberingSystem: 'latn', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23'}); }
    catch { fail('Invalid time zone'); }
    if (formatters.size >= 64) formatters.clear();
    formatters.set(zone, value);
  }
  return formatters.get(zone);
}
function parts(stamp, zone) {
  return Object.fromEntries(formatter(zone).formatToParts(stamp).filter(p => p.type !== 'literal').map(p => [p.type, Number(p.value)]));
}
function localStamp(stamp, zone) {
  const p = parts(stamp, zone);
  return utc(p.year, p.month, p.day, p.hour, p.minute) + p.second * 1000;
}
/** Resolves wall time without adopting the machine's time zone or shifting DST gaps. */
export function resolveActivityStart(date, time, timeZone, disambiguation = 'reject') {
  const midnight = civilDate(date);
  const [hour, minute] = civilTime(time);
  formatter(timeZone);
  if (!['reject', 'earlier', 'later'].includes(disambiguation)) fail('Invalid DST disambiguation');
  const wall = midnight + (hour * 60 + minute) * 60000;
  const offsets = new Set();
  for (let hours = -36; hours <= 36; hours += 6) {
    const sample = wall + hours * 3600000;
    offsets.add(localStamp(sample, timeZone) - sample);
  }
  const candidates = [...offsets].map(offset => wall - offset).filter(stamp => localStamp(stamp, timeZone) === wall).sort((a, b) => a - b);
  if (!candidates.length) fail('Civil time does not exist in this time zone');
  if (candidates.length > 1 && disambiguation === 'reject') fail('Ambiguous civil time requires earlier or later');
  return new Date(disambiguation === 'later' ? candidates.at(-1) : candidates[0]).toISOString();
}
function instant(value, name) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,3})?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/.test(value) || !Number.isFinite(Date.parse(value))) fail(`Explicit offset timestamp required for ${name}`);
  civilDate(value.slice(0, 10));
  return value;
}
function freeze(value) {
  if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
  return value;
}
function provenance(value) {
  value = record(value, ['kind', 'source', 'sourceRecordId', 'recordedAt'], 'activity provenance');
  if (!value || !['user-entered', 'calendar-import'].includes(value.kind)) fail('Activity provenance required');
  return {kind: value.kind, source: text(value.source, 'source', 500), sourceRecordId: value.sourceRecordId == null ? null : text(value.sourceRecordId, 'source record ID', 500), recordedAt: instant(value.recordedAt, 'provenance')};
}
function consent(value) {
  value = record(value, ['granted', 'scope', 'recordedAt'], 'consent');
  if (!value || value.granted !== true || value.scope !== 'activity-schedule') fail('Explicit activity-schedule consent required');
  return {granted: true, scope: 'activity-schedule', recordedAt: instant(value.recordedAt, 'consent')};
}
function recurrence(value, startDate) {
  if (value == null) return null;
  value = record(value, ['frequency', 'interval', 'weekdays', 'until'], 'recurrence');
  if (!['daily', 'weekly'].includes(value.frequency)) fail('Only explicit daily/weekly recurrence supported');
  const until = value.until == null ? null : value.until;
  if (until !== null && civilDate(until) < civilDate(startDate)) fail('Recurrence end precedes start');
  let weekdays = null;
  if (value.frequency === 'weekly') {
    weekdays = denseArray(value.weekdays, 7, 'weekly weekdays').map(day => integer(day, 1, 7, 'weekday'));
    if (!weekdays.length) fail('Weekly recurrence needs ISO weekdays');
    if (new Set(weekdays).size !== weekdays.length) fail('Duplicate recurrence weekday');
    weekdays.sort((a, b) => a - b);
    const startWeekday = new Date(civilDate(startDate)).getUTCDay() || 7;
    if (!weekdays.includes(startWeekday)) fail('Start date must be a selected weekday');
  } else if (value.weekdays != null) fail('Daily recurrence cannot specify weekdays');
  return {frequency: value.frequency, interval: integer(value.interval, 1, 52, 'recurrence interval'), weekdays, until};
}
export function validateActivityEntry(value) {
  value = record(value, ['id', 'subjectId', 'label', 'date', 'time', 'timeZone', 'disambiguation', 'durationMinutes', 'intensity', 'recurrence', 'provenance', 'consent'], 'activity entry');
  const date = value.date; civilDate(date); civilTime(value.time); formatter(value.timeZone);
  const disambiguation = value.disambiguation ?? 'reject';
  resolveActivityStart(date, value.time, value.timeZone, disambiguation);
  let durationMinutes = null;
  if (value.durationMinutes != null) {
    if (typeof value.durationMinutes !== 'number' || !Number.isFinite(value.durationMinutes) || value.durationMinutes <= 0 || value.durationMinutes > 10080 || !Number.isInteger(value.durationMinutes * 60000)) fail('Duration must be positive minutes at millisecond precision, at most seven days, or unknown');
    durationMinutes = value.durationMinutes;
  }
  return freeze({id: text(value.id, 'activity ID'), subjectId: text(value.subjectId, 'subject ID'), label: text(value.label, 'activity label', 500), date, time: value.time, timeZone: value.timeZone, disambiguation, durationMinutes, intensity: value.intensity == null ? null : text(value.intensity, 'user intensity label', 200), recurrence: recurrence(value.recurrence, date), provenance: provenance(value.provenance), consent: consent(value.consent)});
}
export function createActivitySchedule(ownerId, entries = []) {
  text(ownerId, 'owner ID');
  const validated = denseArray(entries, MAX_ENTRIES, 'schedule entries (at most 500)').map(validateActivityEntry);
  if (new Set(validated.map(entry => entry.id)).size !== validated.length) fail('Duplicate activity ID');
  return freeze({ownerId, revision: 0, entries: validated});
}
/** Complete replacement edits with revision checks; adapters own authorization/storage. */
export function transitionActivitySchedule(state, action, context = {}) {
  state = record(state, ['ownerId', 'revision', 'entries'], 'schedule state');
  action = record(action, ['type', 'id', 'entry'], 'transition');
  const {ownerId, expectedRevision} = record(context, ['ownerId', 'expectedRevision'], 'transition context');
  if (!state || ownerId !== state.ownerId) fail('Schedule owner mismatch');
  integer(state.revision, 0, Number.MAX_SAFE_INTEGER - 1, 'revision');
  if (expectedRevision !== state.revision) fail('Stale schedule revision');
  const entries = createActivitySchedule(state.ownerId, state.entries).entries.slice();
  if (!action || !['add', 'replace', 'remove'].includes(action.type)) fail('Invalid schedule transition');
  if (action.type === 'add') entries.push(validateActivityEntry(action.entry));
  else {
    const index = entries.findIndex(entry => entry.id === action.id);
    if (index < 0) fail('Activity not found');
    if (action.type === 'remove') entries.splice(index, 1);
    else {
      const replacement = validateActivityEntry(action.entry);
      if (replacement.id !== action.id) fail('Replacement ID mismatch');
      entries[index] = replacement;
    }
  }
  const validated = createActivitySchedule(state.ownerId, entries);
  return freeze({...validated, revision: state.revision + 1});
}
/** Start-date window [from,to), bounded to 366 civil days and 2,000 occurrences. */
export function expandActivitySchedule(state, range = {}) {
  state = record(state, ['ownerId', 'revision', 'entries'], 'schedule state');
  const {from, to, maxOccurrences = 2000} = record(range, ['from', 'to', 'maxOccurrences'], 'expansion range');
  const start = civilDate(from), stop = civilDate(to);
  if (stop <= start || stop - start > 366 * DAY) fail('Use a positive civil range of at most 366 days');
  integer(maxOccurrences, 1, 2000, 'occurrence bound');
  const entries = createActivitySchedule(state.ownerId, state.entries).entries;
  const occurrences = [];
  for (const entry of entries) {
    const first = civilDate(entry.date), rule = entry.recurrence;
    const firstWeekday = new Date(first).getUTCDay() || 7;
    const firstMonday = first - (firstWeekday - 1) * DAY;
    for (let day = Math.max(start, first); day < stop; day += DAY) {
      const date = new Date(day).toISOString().slice(0, 10);
      if (rule?.until && date > rule.until) break;
      if (!rule && day !== first) break;
      if (rule?.frequency === 'daily' && ((day - first) / DAY) % rule.interval !== 0) continue;
      if (rule?.frequency === 'weekly' && (!rule.weekdays.includes(new Date(day).getUTCDay() || 7) || Math.floor((day - firstMonday) / (7 * DAY)) % rule.interval !== 0)) continue;
      if (occurrences.length >= maxOccurrences) fail('Occurrence bound exceeded; narrow the range');
      const startAt = resolveActivityStart(date, entry.time, entry.timeZone, entry.disambiguation);
      occurrences.push({...entry, occurrenceId: JSON.stringify([entry.id, date]), date, startAt, endAt: entry.durationMinutes === null ? null : new Date(Date.parse(startAt) + entry.durationMinutes * 60000).toISOString()});
    }
  }
  occurrences.sort((a, b) => a.startAt.localeCompare(b.startAt) || a.occurrenceId.localeCompare(b.occurrenceId));
  return freeze(occurrences);
}
/** Union of known intervals per subject; unknown duration never becomes zero. */
export function summarizeActivitySchedule(state, range) {
  const occurrences = expandActivitySchedule(state, range);
  const subjects = [...new Set(occurrences.map(row => row.subjectId))];
  const summaries = subjects.map(subjectId => {
    const rows = occurrences.filter(row => row.subjectId === subjectId);
    const known = rows.filter(row => row.endAt !== null).map(row => [Date.parse(row.startAt), Date.parse(row.endAt)]).sort((a, b) => a[0] - b[0]);
    const union = [];
    let summed = 0;
    for (const [start, end] of known) {
      summed += end - start;
      const previous = union.at(-1);
      if (previous && start <= previous[1]) previous[1] = Math.max(previous[1], end);
      else union.push([start, end]);
    }
    const covered = union.reduce((total, [start, end]) => total + end - start, 0);
    const unknownDurationOccurrences = rows.filter(row => row.endAt === null).map(row => row.occurrenceId);
    return {subjectId, knownCoveredMinutes: covered / 60000, overlappingKnownMinutes: (summed - covered) / 60000, completeDurationKnown: unknownDurationOccurrences.length === 0, unknownDurationOccurrences, intervals: union.map(([start, end]) => ({startAt: new Date(start).toISOString(), endAt: new Date(end).toISOString()}))};
  });
  return freeze({occurrences, subjects: summaries, scope: 'Descriptive planned intervals only; no actual exercise, energy, prescription or clinical inference'});
}
