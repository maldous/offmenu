# P2-07 descriptive activity schedule: Owner 34 adoption candidate

Actual pickup: 15 October 2026 Melbourne, existing Worker 34 thread `01a13997-947d-7ce1-bb6a-a6c1dc9d8aa3`. Fresh locked `origin/develop` fetch resolved to `5f5bdb6ae716cbf80fab1e174d1af2e354468ead`; branch `feature/activity-schedule-owner34-20261014` retains the requested assignment name. Prior corpus/PR4/recovery evidence and refs remain intact. Production STOP applies.

The source-linked canonical 105-ID register describes P2-07 as “Exercise schedules and consented dated body metrics”, Product Review and Plan, expansion opportunities, page 6. Worker 17's `worker17-current-deliverable-coverage-update.json#/requirements/18` identifies the missing behavior: exercise scheduling is absent and overlapping measurements are only warned about. Its original acceptance criterion is **“Private dated schedule and metrics retain source and consent; overlapping activity cannot be double summed.”** Dependencies remain TRUST-02 and DATA-14. This scoped change implements the schedule model; it does not certify the whole requirement.

Owned delta only: `public/activity-schedule-model.js`, `tests-web/activity-schedule-owner34.test.mjs`, and this document. No shared app, database schema, health statistics, calendar parser, provider, production or dependency changes.

## Contract and example

```js
import {
  createActivitySchedule, transitionActivitySchedule,
  expandActivitySchedule, summarizeActivitySchedule
} from './activity-schedule-model.js';

const schedule = createActivitySchedule('owner-123', [{
  id: 'my-walk', subjectId: 'member-123', label: 'Walk to station',
  date: '2026-10-15', time: '08:00', timeZone: 'Australia/Melbourne',
  disambiguation: 'reject', durationMinutes: null, intensity: null,
  recurrence: {frequency: 'weekly', interval: 1, weekdays: [4], until: '2026-12-31'},
  provenance: {kind: 'user-entered', source: 'My notes', sourceRecordId: null,
    recordedAt: '2026-10-14T13:00:00Z'},
  consent: {scope: 'activity-schedule', granted: true,
    recordedAt: '2026-10-14T13:00:00Z'}
}]);
const summary = summarizeActivitySchedule(schedule, {
  from: '2026-10-15', to: '2026-10-22'
});
// Unknown duration: occurrence.endAt=null; completeDurationKnown=false.
// knownCoveredMinutes describes only the union of known planned intervals.
const next = transitionActivitySchedule(schedule, {type: 'remove', id: 'my-walk'}, {
  ownerId: 'owner-123', expectedRevision: 0
});
```

Every entry has a caller-supplied ID and subject, exact source label and source record ID, explicit consent scope/date, date, time and named zone. Consent/provenance timestamps require explicit offsets; the module never consults the device's local zone, generates a timestamp, or infers consent. Source labels and user intensity text are retained as entered. Durations are positive elapsed minutes at millisecond precision, bounded to seven days, or `null`/omitted for unknown. Unknown intensity is also `null`. No inferred intensity, recommended routine, calorie, nutritional, clinical or body-metric conversion is produced. Labels are plain text; consumers must render with text nodes.

Civil dates use strict Gregorian YYYY-MM-DD (1900..9998), civil times HH:mm. Recurrence is only explicit daily/weekly, with interval 1..52; weekly ISO weekdays are Monday=1 through Sunday=7 and the start day must be selected. Weeks are anchored to the start date's ISO Monday week. Optional `until` is an inclusive civil date. Unsupported recurrence fields (including count, exceptions, monthly rules) are rejected so imports cannot silently broaden a schedule.

DST gaps reject the entry or expansion; no shifting, skipping or guessed time. Folds require explicit `earlier` or `later`, otherwise reject. Recurrence retains the civil wall time; durations are elapsed time. Conversion uses the executing runtime's Intl time-zone database, including non-hour offsets; cross-runtime tzdata differences remain an adoption qualification point.

Expansion requires a `[from,to)` **civil start-date window**, at most 366 days and 2,000 occurrences. Dates are interpreted in each entry's declared zone. It is not an instant-clipped reporting window: midnight-crossing durations include their full elapsed interval, and earlier-starting activities outside the selected date window are excluded. Adapters needing clipped instant/day reporting must supply a separately reviewed window policy rather than present these totals as that report. Over-limit or unresolvable expansions fail as a whole without partial results.

Summaries union overlapping or adjacent known intervals **per subject**, across activity labels and sources, while retaining every occurrence and its provenance. `knownCoveredMinutes` avoids double-summing overlapping known activity; `overlappingKnownMinutes` reports the duplicate known-duration excess. Unknown durations remain separately listed and make `completeDurationKnown=false`; they do not become zero, or establish an upper bound/complete total. A schedule is planned activity, not evidence it happened. Different subjects are never summed together.

The model returns copied, deeply frozen values. All schedule arrays and weekly weekday arrays are captured as dense, bounded, own data slots: holes, inherited slots and index accessors reject. Input records (entry, recurrence, provenance, consent, state, action and range/context) are captured through own data descriptors before validation; accessors and unsupported fields reject without getter invocation. Caller-defined array methods are not called. This boundary supports ordinary data objects/arrays, not hostile JavaScript Proxies whose reflection traps can execute code. Adapters must first admit trusted parsed data rather than pass arbitrary executable objects. Add/replace/remove transitions require owner identity and exact expected revision, increment the revision, reject duplicate IDs, and leave the previous snapshot intact. Replace accepts a complete validated entry, preserving the old snapshot's provenance rather than mutating it. These are local consistency checks, not server authentication or authorization.

## Scoped Owner 02/03/31 adoption boundary

The candidate is ready for independent review; no owner is assumed to have adopted it, and no coordination message or publication was sent by this worker.

* Owner 02 app consumer: import the four functions above in its owned integration delta. Add a private activity-schedule view with explicit date/time/named zone, optional duration/intensity, provenance and consent confirmation. Store schedules under the authenticated owner and check subject access on the server. Use expected revision/CAS, retain history as required, and apply revocation/delete/export policy. Present known covered intervals and unknown duration separately. Never insert planned minutes into `healthStatistics` or combine them with actual device measurements as completed exercise. Keep body metrics' source/consent and descriptive statistics unchanged.
* Owner 03 portable calendar boundary: keep parser/serialization ownership separate. Map only explicitly timed, owner-confirmed events into the documented neutral entry contract; preserve original UID/source and user consent. Missing duration maps to null. Date-only/floating or missing-zone events require explicit user date/time/zone decisions before adoption, never guessed midnight or host time zone. Map only supported recurrence after a preview; reject unsupported count/exception/monthly semantics. Preserve the original calendar representation outside this normalized model for roundtrip/source text. Runtime timezone equivalence and import preview/consent acceptance remain required.
* Owner 31 consumer boundary: use neutral validated entries/occurrences for private calendar handoff only after Owner 03's parser contract is agreed and independently reviewed. Keep source IDs, explicit zone/fold choice and unknown values; do not substitute calendar duration, calories or device activity automatically. Use relative source IDs with visible source/consent provenance. Shared shopping/calendar consumer and parser files are outside this delta.

Independent review must pin the exact three-file commit and assess the relevant owner-owned adoption delta separately. No shared schema, storage/identity contract or calendar format is silently changed by this module.

## Validation and remaining original acceptance

Run `node --test tests-web/activity-schedule-owner34.test.mjs tests-web/global-data.test.mjs tests-web/continuation.test.mjs`. The 19 focused schedule tests cover civil validation, consent/source unknowns, Melbourne DST gaps/folds, Lord Howe half-hour DST, UTC+14, wall-time daily recurrence, ISO weekly anchoring, interval/year boundaries, unsupported recurrence refusal, interval unions, per-subject separation, unknown durations, midnight spans, range limits, immutable owner/revision transitions, sparse/inherited arrays and getter-free own-data capture. Existing health/continuation tests exercise retained measurement behavior. Run the focused schedule tests under `TZ=UTC` and `TZ=America/Los_Angeles` to verify host-zone independence.

Worker 11's independent review of initial commit `bef64e4256c3b904b0901274a129a68f8fa4231d` found sparse entries/weekdays bypassing `Array.map` validation. Both triggers were reproduced before this correction. This successor changes only the three owned files and must return to the same reviewer for exact-pin re-review; passing author tests is not independent acceptance. The review directly checked original PDF02 pages 5, 6 and 8 with retained PDF SHA-256 `2d1ec141bf3694f7dd1305b1dec9a78197bcf16ba156bfab7c4dfb2aebd44d9c`; this correction relies on that source-linked scope and does not reinterpret it as exercise prescription.

Remaining P2-07 acceptance: independent exact-code review; Owner 02 private app/storage adoption and source/consent lifecycle; Owner 03/31 portable calendar preview, roundtrip and timezone adoption; consented dated metrics/schedule integrated acceptance; accessible UI/localization; protection against double summation in actual app reporting; actual privacy/access/revocation qualification. Clinical advice, exercise prescription, provider/device integration and production deployment remain outside this scope. No whole-requirement or production acceptance is claimed.
