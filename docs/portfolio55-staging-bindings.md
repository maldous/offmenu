# Worker55 retained portfolio metadata binding

M-STAGING-BIND-20261018-W55 owns BW/GA/KH/MY configuration and authored tests.
This package checks retained metadata and proposed field-origin declarations with
the accepted shared `acceptance.fingerprint` and `field_provenance.field_origin_errors`.
It does not read, parse or qualify source bodies, convert the legacy MY JSONL,
register admissions or claim full-country completeness. No shared core changes.

Run the deterministic metadata interface from repository root:

```
python3 -m offmenu.refresh.portfolio55 < tests/fixtures/portfolio55/valid-metadata.json
python3 -m unittest discover -s tests -p test_portfolio55.py -v
```

The bundled metadata fixture repeats retained pins, not dataset observations.
The envelope fixture is small authored data, explicitly not a real retained row.
The CLI opens only its packaged configuration and stdin; neither module opens
paths named by the source pins. Output is one isolated diagnostic per country.
`valid-metadata` means exact configuration equality, not current body validation.
Country holds precede candidate checks. Missing metadata, malformed clocks,
changed source/release/acquisition/pins and exact selectors fail separately.

MY is only DOSM `cpi_2d` statistical index data: monthly, 2010=100, 13 divisions
and overall. Source date/division/index declarations bind the retained CSV column
names; publisher labels bind their exact embedded JSON pointers. Currency, item
prices, quantities, weights, exact formula and expenditure-weight reference period
remain unknown. No canonical field or nutrient/food equivalence is inferred.
Retained 7,840 normalized rows (6,376 numeric, 1,464 missing) were not re-counted.
Review24's scoped integrity pass does not replace pending normalization20 review.
Dictionary/schema56 custody and caller adoption remain independent.

Original acquisition is the retained receipt's `utc` value, not the publisher
release literal, index reference month or later validation time. Publisher release
timezone is unknown. The binding key includes source/release/pins, field policy,
basis, acquisition and contract version. A matching previous key yields no-op.
Validation age is reported separately and cannot renew acquisition age. Before
30 days the only plan is reuse; at 30 days conditional refresh still requires
custodian/source-use qualification. This package performs no download and creates
no cache-retention guarantee, scheduler or acquisition permission.

BW/GA/KH retain their exact frozen gap evidence. BW requires receipt conflict
resolution and CPI use/selector mapping. GA requires IHPC derivative-use/mapping
and national applicability, with GNI export held. KH requires CAS aggregate
use/selectors/units/basis and approved composition export. All six requested
country categories remain open. Existing source custodians own those inputs;
Morgan owns scheduling. No duplicate acquisition is selected.

## Integration dependency

Base is verified accepted develop `abecb99ee1125730ccbc2824b6ec49ffc5cc4302`.
Fresh `origin develop` fetch failed on a broken existing Codex checkpoint ref;
the failure is frozen in Worker55's pickup receipt. No ref deletion or repair was
attempted. Integrator00 result5798 subsequently confirms the exact isolated
snapshot lifecycle is selected; no further fetch or checkpoint repair is needed
for this proposal. A read-only live provider check at delivery again resolved
develop to this exact SHA. This is not future freshness or release acceptance.
Integrator00 must independently review/integrate the bounded commit.

There is no generic pure cache planner at this base. The output's refresh field
is metadata intent only, explicitly reporting that unsupported shared capability.
It does not invoke Wikibooks-specific policy, spoof a registered fixture or run
the operational body-reading CachedAcquirer. Shared strict JSON, canonical output
and UTC timestamp validation are reused. A shared planner extension stays a
proposal for Morgan/00; this module is portfolio binding configuration glue.

Proposed shared caller interface (no shared edit implemented): supply exact
reviewed `sourceId`, immutable `releaseId`, input pins and physical source-row ID
to a legacy-to-shared envelope conversion, preserving original source citations,
decimal lexemes/nulls and source-specific schema. Its output must pass full schema,
source-coordinate/semantic checks and the shared field-origin validator. Merely
passing these authored selector tests does not validate real coordinates or values.
The metadata CLI is usable now; real MY staging conversion requires independent
review of that caller and normalization20/source-use scope. Source bodies remain
on Foo. Finland/Frida, native NO/FR, explicit denial, production and CIX holds stay.

## Reviewer44 correction delta

W55-R44-01: request, observations and optional previousKeys containers are checked
before country iteration; missing clock and malformed JSON produce fixed structured
diagnostics without traceback. Invalid request-level inputs block metadata intent
while retaining the four-country response and existing holds. A malformed individual
country observation remains isolated from its peers.

W55-R44-02: the three source-column declarations must share one nonempty physical
sourceRecordId. This rejects mixed-row splices without guessing the correct real
row or validating values. Coherent authored declarations and existing wrong-column,
wrong-pin controls retain their prior outcomes. Only narrow authored regressions
are executed for this correction; SAME reviewer44 owns independent delta review.
