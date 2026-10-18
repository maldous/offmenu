# P2-01 — explicit meal context, Worker 33

Review candidate only; no app, schema, preference store, plan caller or production
change. P2-01 is partially implemented here, not accepted as a whole product flow.

Pickup: existing Worker33, preserved measurement commit
`6328ef598cf6df3cdb8b1c32b1d5381358bd9782` and cache review/re-review reports.
Fresh origin/develop fetched under `/tmp/offmenu-develop-fetch.lock`, exit0, to
`5f5bdb6ae716cbf80fab1e174d1af2e354468ead`; new branch
`feature/meal-context-owner33-20261014` (requested name retained on October15).

Source requirements: `worker17-current-deliverable-coverage-update.json`, P2-01
and G-P2-01, and exact Owner03 map
`6f3ae8827732ba3dd612f5851ca57c7718f196a2:docs/production-integration-owner03.json`.
These trace the original105 requirement to
`02-OffMenu_Product_Review_and_Plan-1-.pdf`, Expansion opportunities, page6;
retained PDF SHA256
`2d1ec141bf3694f7dd1305b1dec9a78197bcf16ba156bfab7c4dfb2aebd44d9c`.
This pickup read the retained requirement/source mapping, not a new PDF extraction.
Acceptance: move a plan between explicit homes with scoped carer permissions;
windows cross midnight/timezone; culture never infers restrictions. Later local
delivery and production STOP directions remain. P0-04/TRUST-02, account/session
authority, owner review and integrated acceptance remain dependencies.

## Model contract

`public/meal-context-model.js` has no imports, storage, transport or side effects.
It exports `emptyMealContext(accountId)`,
`validateMealContext(value, accountId)`,
`transitionMealContext(value, {accountId, actorId, permit}, action)` and
`mealContextAt(value, {accountId, at})`. Inputs are ordinary parsed JSON; accessors,
class objects, custom/sparse arrays and unsupported fields reject. Proxies are
unsupported and cannot be authenticated by an in-process JavaScript validator.
Output is deeply frozen, independently captured and does not mutate source facts.
Bounds:128 declarations,32 qualifier strings each,64 carer home IDs,10,000 capture
nodes,12 levels,65,536 total string characters per capture.

Version1 shape:

```js
{
  version: 1, accountId: 'verified-account',
  declarations: [{
    id: 'home-1', kind: 'home', label: 'Original label',
    source: {label: 'As declared by user', reference: null},
    qualifiers: ['unknown suitability'], status: 'declared'
  }],
  selection: {homeId: null, carerId: null}
}
```

Kinds are home/carer/taste/culture/fasting; statuses are declared/unknown/withdrawn.
Labels, source spelling, source reference and qualifier strings are retained exactly.
Missing source labels/references are explicit null, never fabricated attribution.
Carers require `homeIds: ['home-1']` or null for unknown; IDs refer to existing home
declarations. These are declared context scopes, not server grants. Unknown or
withdrawn carers/homes cannot be selected. Withdrawing a selected home clears both
selections; a withdrawn/changed carer clears only its selection. No alternate home
or carer is automatically chosen. Withdrawal preserves source facts and labels.

Fasting requires `window: null` for unknown or an explicit dated interval:

```js
window: {
  start: '2026-10-14T23:00:00+11:00',
  end: '2026-10-15T05:00:00+11:00',
  timeZone: 'Australia/Melbourne'
}
```

Endpoints require explicit offsets, valid dates and a supported named time zone
whose wall times match those offsets. End must follow start. Midnight/DST are
handled as explicit instants, with start inclusive and end exclusive. A nonexistent
local wall time or a mismatched offset rejects. DST's repeated hour remains
disambiguated by the user's explicit offset. No ambiguous local-time conversion,
recurrence, timezone guessing or automatic home-zone conversion is supplied.
Runtime Intl/timezone data must be qualified by the adopter on each supported
platform. `mealContextAt` emits only inside-declared-window,
outside-declared-window, unknown or withdrawn for fasting declarations. All source
declarations remain in the projection; it does not claim which member/home a window
should apply to. That additional applicability requires explicit owner-designed scope.

Actions: `{type:'declare', declaration}`, `{type:'withdraw', id}` or
`{type:'choose', homeId, carerId}`. Explicit null deselects. `permit` is a synchronous,
trusted, nonmutating callback returning `{allowed:true}` only after current
authenticated account/actor/home/carer/consent checks. It receives frozen exact
action/account/actor/home/carer intent. Promise or missing/false decision denies.
Equality with accountId and declaration labels never proves authentication or
authority. This pure helper cannot fence revocation or persist an acknowledgment;
the owner must reauthorize at the durable write/CAS boundary. Exceptions leave the
input unchanged. The model emits no religious/dietary identity, health restriction,
nutrition, suitability, ranking, safety or consent inference.

## Read-only adoption reconciliation; minimal Owner02 delta

Owner03's exact map traces the criterion but does not establish acceptance; its
suggested worker34 was only a candidate, superseded by this explicit Worker33 task.
Owner20's persisted preference contract owns P1-03 member taste envelopes, likes,
textures and spice plus preserving restrictions. Meal context is an account-private
descriptive context, not another member preference store. Keep Owner20 envelope
and actual save validator intact; map a taste declaration to it only through a
separately reviewed explicit user action, never by culture inference.

Owner19's read-only plan contract permits copy/edit date,slot,servings,memberIds,
adjustments and requires review. It does not accept home/context fields yet.
Do not smuggle this context into adjustments or treat selecting a home as a committed
plan move. Owner19/02 must design an explicit reviewed context association and
transfer intent, retaining source evidence and target attendance/equipment review.
No coordination acknowledgment, shared path reservation or integration acceptance
is claimed from inspecting those owner contracts.

After independent exact-candidate review, Owner02's minimal isolated integration is:

1. Import validateMealContext/transitionMealContext in the account-private caller.
   Obtain accountId and actorId from the reviewed Owner04 session/auth contract.
2. Explicit user controls declare/withdraw labels and dated windows and choose a
   home/carer. Pass current scoped authorization via permit. Keep unknown qualifiers
   visible; require explicit target carer choice instead of carrying one automatically.
3. Add a separately reviewed, bounded account-private context field/slot to the
   account validator/restore/save boundary. Current shared validators must not drop
   it silently. Never spread arbitrary client metadata into authorization state.
   Reauthorize at actual revision/CAS commit and require an exact acknowledgment.
4. Coordinate the reviewed Owner19 plan-transfer action and Owner20 preference
   boundary. Review the target plan before cooking; selecting descriptive context
   alone changes neither a meal plan nor member restrictions.
5. Omit account-private home/carer/taste/culture/fasting declarations from public or
   kitchen sharing until separately explicit consent/projection is reviewed.
   No store/schema/sharing projection edit is part of this candidate.

Remaining acceptance: independent review of the immutable candidate; Owner04
authority and revocation/write fencing; Owner02 persistence and UI adoption;
Owner19 actual plan move/review/acknowledgment; Owner20 preference coexistence;
privacy projection; supported-runtime timezone behavior; integrated/browser exercise
against original105 acceptance. Production STOP remains active.

Focused tests exercise explicit home transfer and carer scope, rights denial,
source/label/unknown preservation, midnight and DST windows, unknown/withdrawal,
account separation, frozen intent, accessor/sparse/bounds rejection. No source
acquisition, installs, full suite, providers or production changes. Primary main,
HEAD and index and prior branch/report custody are checked by the external receipt.
