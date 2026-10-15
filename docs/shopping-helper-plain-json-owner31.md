# Worker31 PR18 direct-helper correction — pending independent review

Managing Morgan selected discussion_r4283439849:
https://github.com/maldous/offmenu/pull/18#discussion_r4283439849
PR18 merged as 15762b3ab1ff5f03356f2eed21a722257ebcf6b6; reviewed source head
was d840ea79f928341d69de875439b8664f94c00946. The merged public helper still
used JSON.stringify on caller data before the replacer checked value types.

Dedup: inspected the PR18 discussion/current PR record, local shopping task refs
and a scoped provider PR search for shopping/accessor fixes. No identical fix
was found in that evidence. This does not claim a global requirements audit.
Original Worker31 branch feature/shopping-destination-owner31-20261015 at
82721a960fa05c053b5103a5b2ebebe2f1562f9d was clean and remains preserved.
New local branch bugfix/shopping-helper-plain-json-owner31-20261016 starts from
the exact PR18 merge above. No shared fetch/tracking-ref repair was performed;
this is a correction candidate, not a newly qualified current-develop integration.

## Root cause and before/after

Direct imported helper calls against the merged helper reproduced:
- root scope getter: called once, accepted changed scope;
- nested quantity getter: called once, accepted quantity 999;
- root toJSON: called once, synthesized/accepted changed scope;
- nested toJSON: called once, synthesized/accepted quantity 999.

The two initial rejection regression groups failed (0 pass, 2 fail), because
JSON serialization calls getters/toJSON before the replacer receives the values.
The existing createShoppingHandoff adapter guarded its own input, but callers
of the exported helper bypassed that guard. Adapter source was not changed.

The helper now walks own property descriptors before serialization and builds
a detached plain-data copy. Enumerable data properties on ordinary or null-
prototype objects and dense ordinary arrays are allowed. Accessors, functions,
symbols/keys, bigint, undefined, non-enumerable extra properties, custom object
prototypes, sparse/custom arrays and cycles reject. Finite numbers and null
unknowns retain their original contract. Repeated noncyclic references serialize
as independent copies as before. Literal __proto__ JSON fields remain inert
source data rather than triggering a prototype setter. Null-prototype copies,
including arrays, prevent inherited toJSON execution on those copies.

Bounds: 10,000 visited nodes, 20 levels and existing 65,536-character serialized
proposal limit. Individual oversize strings/arrays reject early. Serialization
runs only on the validated copy. The rest of proposal/confirmation validation,
source rights, quantity semantics and retailer/calendar/substitute kinds are
unchanged. This is not a Proxy trap sandbox or protection against replacement
of JavaScript intrinsics; reflective operations on proxies can themselves run
traps. This correction covers the stated ordinary-object getter/toJSON boundary,
not authentication or all options/consent producer inputs.

Final focused command:
node --test tests-web/shopping-handoff-plain-json-owner31.test.mjs tests-web/shopping-handoff-owner31.test.mjs tests-web/shopping-destination-owner31.test.mjs
Result: 19 passed, 0 failed (5 new direct-helper groups + 14 packaged consumer
checks). New probes cover root/nested getters and toJSON (zero calls), changed
draft accessor during confirm, cycles/non-JSON/sparse/prototype/depth/size bounds,
and detached valid/null-prototype/alias/__proto__ data with successful confirmation.
Existing guarded adapter/destination tests prove no bypass was introduced and
preserve null quantities, source identities, rights and fresh confirmation.
No broad suite, provider actions, browser or production call was run.

## Handoff and holds

Only public/shopping-handoff-model.js, the new focused test and this note change.
The packaged provenance manifest remains the historical PR18 byte-identical
source receipt; its original helper hash must NOT be described as the correction's
hash. The correction receipt binds the new helper hash and immutable delta.
Any final-current-base composition/generated inventory update belongs to the
existing single writer and requires its exact review; no old PASS is borrowed.

Existing Worker24 is the selected independent reviewer. Candidate review is
pending; this note does not self-accept the fix or mark the provider discussion
resolved. No PR/comment retry, alternate actor, external publication/backup,
calendar activation, merge, main change, deployment or central wiring occurred.
The calendar PR action-specific denial and production STOP remain binding.
All prior task refs, source/review evidence and main/index custody are preserved.
Checkpoint is local-only under current holds.
