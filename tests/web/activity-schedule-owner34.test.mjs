import test from 'node:test';
import assert from 'node:assert/strict';
import {createActivitySchedule, validateActivityEntry, transitionActivitySchedule, resolveActivityStart, expandActivitySchedule, summarizeActivitySchedule} from '../../public/activity-schedule-model.js';

const provenance = {kind: 'user-entered', source: 'My activity notes', sourceRecordId: null, recordedAt: '2026-10-14T12:00:00Z'};
const consent = {granted: true, scope: 'activity-schedule', recordedAt: '2026-10-14T12:00:00Z'};
function entry(overrides = {}) { return {id: 'walk', subjectId: 'me', label: 'Walk to station', date: '2026-10-15', time: '08:00', timeZone: 'Australia/Melbourne', durationMinutes: 30, intensity: null, recurrence: null, provenance: {...provenance}, consent: {...consent}, ...overrides}; }
const range = {from: '2026-10-15', to: '2026-10-16'};

test('strict civil dates, times, named zone and explicit timestamp provenance', () => {
  for (const changes of [{date: '2026-02-30'}, {date: '2026-2-01'}, {time: '24:00'}, {timeZone: 'Invalid/Zone'}, {timeZone: '+11:00'}, {provenance: {...provenance, recordedAt: '2026-10-14T12:00:00'}}, {provenance: {...provenance, recordedAt: '2026-02-30T12:00:00Z'}}]) assert.throws(() => validateActivityEntry(entry(changes)));
  assert.equal(validateActivityEntry(entry({date: '2028-02-29'})).date, '2028-02-29');
});

test('consent and descriptive source/intensity remain explicit', () => {
  assert.throws(() => validateActivityEntry(entry({consent: {...consent, granted: false}})), /consent/);
  assert.throws(() => validateActivityEntry(entry({provenance: null})), /provenance/);
  const row = validateActivityEntry(entry({durationMinutes: null, intensity: 'Felt easy', provenance: {...provenance, source: 'Original Unicode 徒歩'}}));
  assert.equal(row.durationMinutes, null);
  assert.equal(row.intensity, 'Felt easy');
  assert.equal(row.provenance.source, 'Original Unicode 徒歩');
  assert.equal(validateActivityEntry(entry({durationMinutes: undefined, intensity: undefined})).intensity, null);
  for (const durationMinutes of [0, -1, NaN, Infinity, '30', 10081, 1e-10]) assert.throws(() => validateActivityEntry(entry({durationMinutes})));
  assert.throws(() => validateActivityEntry(entry({provenance: {...provenance, recordedAt: '2026-10-14T24:00:00Z'}})));
});

test('Melbourne gap rejects, fold requires an explicit choice', () => {
  assert.throws(() => resolveActivityStart('2026-10-04', '02:30', 'Australia/Melbourne', 'later'), /does not exist/);
  assert.throws(() => resolveActivityStart('2026-04-05', '02:30', 'Australia/Melbourne'), /Ambiguous/);
  assert.equal(resolveActivityStart('2026-04-05', '02:30', 'Australia/Melbourne', 'earlier'), '2026-04-04T15:30:00.000Z');
  assert.equal(resolveActivityStart('2026-04-05', '02:30', 'Australia/Melbourne', 'later'), '2026-04-04T16:30:00.000Z');
});

test('non-hour DST and extreme civil offset remain explicit', () => {
  assert.throws(() => resolveActivityStart('2026-10-04', '02:15', 'Australia/Lord_Howe'), /does not exist/);
  const early = Date.parse(resolveActivityStart('2026-04-05', '01:45', 'Australia/Lord_Howe', 'earlier'));
  const late = Date.parse(resolveActivityStart('2026-04-05', '01:45', 'Australia/Lord_Howe', 'later'));
  assert.equal(late - early, 30 * 60000);
  assert.equal(resolveActivityStart('2026-10-15', '00:15', 'Pacific/Kiritimati'), '2026-10-14T10:15:00.000Z');
});

test('daily recurrence retains wall time through DST instead of adding 24 hours', () => {
  const state = createActivitySchedule('owner', [entry({date: '2026-10-03', time: '08:00', recurrence: {frequency: 'daily', interval: 1, until: '2026-10-05'}})]);
  const rows = expandActivitySchedule(state, {from: '2026-10-03', to: '2026-10-07'});
  assert.deepEqual(rows.map(row => row.date), ['2026-10-03', '2026-10-04', '2026-10-05']);
  assert.equal(Date.parse(rows[1].startAt) - Date.parse(rows[0].startAt), 23 * 3600000);
  assert(rows.every(row => row.time === '08:00'));
  assert(rows.every(row => row.endAt && Date.parse(row.endAt) - Date.parse(row.startAt) === 30 * 60000));
});

test('weekly interval is anchored to ISO Monday weeks, not query start', () => {
  const state = createActivitySchedule('owner', [entry({date: '2026-10-14', recurrence: {frequency: 'weekly', interval: 2, weekdays: [5, 3], until: '2026-10-30'}})]);
  const rows = expandActivitySchedule(state, {from: '2026-10-15', to: '2026-11-02'});
  assert.deepEqual(rows.map(row => row.date), ['2026-10-16', '2026-10-28', '2026-10-30']);
  assert.deepEqual(rows[0].recurrence.weekdays, [3, 5]);
});

test('daily interval and year boundary use actual Gregorian dates', () => {
  const state = createActivitySchedule('owner', [entry({date: '2026-12-30', recurrence: {frequency: 'daily', interval: 2}})]);
  assert.deepEqual(expandActivitySchedule(state, {from: '2026-12-31', to: '2027-01-04'}).map(row => row.date), ['2027-01-01', '2027-01-03']);
});

test('recurrence refuses unsupported rules, inconsistent weekday and early end', () => {
  for (const recurrence of [{frequency: 'monthly', interval: 1}, {frequency: 'daily', interval: 1, count: 2}, {frequency: 'daily', interval: 0}, {frequency: 'weekly', interval: 1, weekdays: [1]}, {frequency: 'weekly', interval: 1, weekdays: [4, 4]}, {frequency: 'daily', interval: 1, until: '2026-10-14'}]) assert.throws(() => validateActivityEntry(entry({recurrence})));
});

test('recurrence crossing a gap refuses the range instead of silently moving or skipping', () => {
  const state = createActivitySchedule('owner', [entry({date: '2026-10-03', time: '02:30', recurrence: {frequency: 'daily', interval: 1}})]);
  assert.throws(() => expandActivitySchedule(state, {from: '2026-10-03', to: '2026-10-05'}), /does not exist/);
});

test('known overlapping intervals union per subject without cross-person summation', () => {
  const state = createActivitySchedule('owner', [entry({durationMinutes: 60}), entry({id: 'import', time: '08:30', durationMinutes: 60, provenance: {...provenance, kind: 'calendar-import', sourceRecordId: 'external-1'}}), entry({id: 'other', subjectId: 'other', durationMinutes: 60}), entry({id: 'contained', time: '08:40', durationMinutes: 10})]);
  const summary = summarizeActivitySchedule(state, range);
  const me = summary.subjects.find(row => row.subjectId === 'me');
  assert.equal(me.knownCoveredMinutes, 90);
  assert.equal(me.overlappingKnownMinutes, 40);
  assert.equal(summary.subjects.find(row => row.subjectId === 'other').knownCoveredMinutes, 60);
  assert.equal(summary.occurrences.length, 4);
  assert.equal(summary.occurrences.find(row => row.id === 'import').provenance.sourceRecordId, 'external-1');
});

test('same instant in different zones is unioned; unknown duration never becomes zero', () => {
  const state = createActivitySchedule('owner', [entry(), entry({id: 'utc', time: '21:00', date: '2026-10-14', timeZone: 'UTC'}), entry({id: 'unknown', durationMinutes: null, time: '08:10'})]);
  const summary = summarizeActivitySchedule(state, {from: '2026-10-14', to: '2026-10-16'});
  assert.equal(summary.subjects[0].knownCoveredMinutes, 30);
  assert.equal(summary.subjects[0].overlappingKnownMinutes, 30);
  assert.equal(summary.subjects[0].completeDurationKnown, false);
  assert.equal(summary.subjects[0].unknownDurationOccurrences.length, 1);
  assert.equal(summary.occurrences.find(row => row.id === 'unknown').endAt, null);
});

test('midnight-crossing duration is elapsed time; start-date selection is explicit', () => {
  const state = createActivitySchedule('owner', [entry({time: '23:45', durationMinutes: 45}), entry({id: 'next', date: '2026-10-16', time: '00:00', durationMinutes: 45})]);
  assert.equal(summarizeActivitySchedule(state, {from: '2026-10-15', to: '2026-10-17'}).subjects[0].knownCoveredMinutes, 60);
  assert.equal(expandActivitySchedule(state, range).length, 1);
  assert.equal(expandActivitySchedule(state, {from: '2026-10-17', to: '2026-10-18'}).length, 0);
});

test('range and occurrence bounds refuse partial results', () => {
  const state = createActivitySchedule('owner', [entry({recurrence: {frequency: 'daily', interval: 1}})]);
  assert.throws(() => expandActivitySchedule(state, {from: '2026-10-15', to: '2026-10-18', maxOccurrences: 2}), /bound/);
  assert.throws(() => expandActivitySchedule(state, {from: '2026-10-15', to: '2028-01-01'}), /366/);
  assert.throws(() => expandActivitySchedule(state, {from: '2026-10-16', to: '2026-10-15'}));
});

test('transitions are copied, deeply immutable and revision/owner checked', () => {
  const original = entry();
  const state = createActivitySchedule('owner', [original]);
  original.provenance.source = 'caller mutation';
  assert.equal(state.entries[0].provenance.source, provenance.source);
  assert.throws(() => state.entries[0].consent.granted = false, TypeError);
  assert.throws(() => transitionActivitySchedule(state, {type: 'remove', id: 'walk'}, {ownerId: 'other', expectedRevision: 0}), /owner/);
  assert.throws(() => transitionActivitySchedule(state, {type: 'remove', id: 'walk'}, {ownerId: 'owner', expectedRevision: 1}), /Stale/);
  const next = transitionActivitySchedule(state, {type: 'replace', id: 'walk', entry: entry({durationMinutes: null})}, {ownerId: 'owner', expectedRevision: 0});
  assert.equal(state.entries[0].durationMinutes, 30);
  assert.equal(next.entries[0].durationMinutes, null);
  assert.equal(next.revision, 1);
  const removed = transitionActivitySchedule(next, {type: 'remove', id: 'walk'}, {ownerId: 'owner', expectedRevision: 1});
  assert.equal(removed.entries.length, 0);
  assert.equal(next.entries.length, 1);
  assert.equal(removed.revision, 2);
});

test('add/replace identity and bounded schedule validation', () => {
  const state = createActivitySchedule('owner');
  const added = transitionActivitySchedule(state, {type: 'add', entry: entry()}, {ownerId: 'owner', expectedRevision: 0});
  assert.equal(added.entries.length, 1);
  assert.throws(() => transitionActivitySchedule(added, {type: 'add', entry: entry()}, {ownerId: 'owner', expectedRevision: 1}), /Duplicate/);
  assert.throws(() => transitionActivitySchedule(added, {type: 'replace', id: 'walk', entry: entry({id: 'new'})}, {ownerId: 'owner', expectedRevision: 1}), /ID mismatch/);
  assert.throws(() => createActivitySchedule('owner', Array.from({length: 501}, (_, i) => entry({id: String(i)}))), /500/);
});

test('sparse entry and weekday arrays reject every missing slot', () => {
  assert.throws(() => createActivitySchedule('owner', new Array(1)), /dense own data/);
  const weekdays = new Array(2); weekdays[0] = 4;
  assert.throws(() => validateActivityEntry(entry({recurrence: {frequency: 'weekly', interval: 1, weekdays}})), /dense own data/);
  const inherited = new Array(1);
  Object.setPrototypeOf(inherited, {0: entry()});
  assert.throws(() => createActivitySchedule('owner', inherited), /dense own data/);
  assert.throws(() => createActivitySchedule('owner', [null]));
  assert.throws(() => validateActivityEntry(entry({recurrence: {frequency: 'weekly', interval: 1, weekdays: [4, undefined]}})));
});

test('array accessors reject without invocation and overridden map is never called', () => {
  let calls = 0;
  const accessor = [];
  Object.defineProperty(accessor, '0', {get() { calls++; return entry(); }});
  assert.throws(() => createActivitySchedule('owner', accessor), /data slots/);
  const weekdays = [4];
  Object.defineProperty(weekdays, '0', {get() { calls++; return 4; }});
  assert.throws(() => validateActivityEntry(entry({recurrence: {frequency: 'weekly', interval: 1, weekdays}})), /data slots/);
  const entries = [entry()];
  Object.defineProperty(entries, 'map', {get() { calls++; throw Error('must not run'); }});
  assert.equal(createActivitySchedule('owner', entries).entries.length, 1);
  assert.equal(calls, 0);
});

test('entry and nested records capture own data without invoking getters', () => {
  let calls = 0;
  for (const key of ['label', 'timeZone', 'durationMinutes', 'provenance', 'consent', 'recurrence']) {
    const value = entry();
    Object.defineProperty(value, key, {get() { calls++; return 'unsafe'; }});
    assert.throws(() => validateActivityEntry(value), /accessors/);
  }
  for (const [key, field] of [['provenance', 'source'], ['consent', 'granted'], ['recurrence', 'weekdays']]) {
    const nested = key === 'recurrence' ? {frequency: 'weekly', interval: 1, weekdays: [4]} : {...entry()[key]};
    Object.defineProperty(nested, field, {get() { calls++; return null; }});
    assert.throws(() => validateActivityEntry(entry({[key]: nested})), /accessors/);
  }
  const inherited = Object.create(entry());
  assert.throws(() => validateActivityEntry(inherited));
  assert.equal(calls, 0);
});

test('state, action and option accessors reject before side effects', () => {
  let calls = 0;
  const state = createActivitySchedule('owner', [entry()]);
  const fake = {...state};
  Object.defineProperty(fake, 'entries', {get() { calls++; return []; }});
  assert.throws(() => expandActivitySchedule(fake, range), /accessors/);
  const options = {ownerId: 'owner', expectedRevision: 0};
  Object.defineProperty(options, 'ownerId', {get() { calls++; return 'owner'; }});
  assert.throws(() => transitionActivitySchedule(state, {type: 'remove', id: 'walk'}, options), /accessors/);
  const action = {id: 'walk'};
  Object.defineProperty(action, 'type', {get() { calls++; return 'remove'; }});
  assert.throws(() => transitionActivitySchedule(state, action, {ownerId: 'owner', expectedRevision: 0}), /accessors/);
  const window = {to: range.to};
  Object.defineProperty(window, 'from', {get() { calls++; return range.from; }});
  assert.throws(() => summarizeActivitySchedule(state, window), /accessors/);
  assert.equal(calls, 0);
  assert.equal(state.entries.length, 1);
});
