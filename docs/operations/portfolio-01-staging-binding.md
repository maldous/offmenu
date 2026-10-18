# Worker 01 retained portfolio binding

Assignment `M-STAGING-BIND-20261018-W01`, authored on accepted develop
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. The source package is a metadata
planner plus an authored synthetic CPI adapter. It does not register handlers,
process retained source bodies, create an acquisition client, or grant admission.
Independent review and integration remain required.

## Interfaces

`offmenu.refresh.portfolio_01.plan(country, metadata, now=..., previous_key=None,
fetch_policy='reuse')` returns a shared `StageResult` receipt plus bounded
metadata diagnostics. `plan_portfolio(metadata_by_country, now=...)` isolates
the four country outcomes. Missing metadata is held, malformed or mismatching
metadata is quarantined, and matching real metadata remains source-use held.
The caller cannot supply rights booleans or replace pinned receipts. Diagnostics
contain fixed codes, counts and hashes, never input values, URLs or local paths.

The trusted declarations in `portfolio_01_contract.py` identify exact retained
reports, AI acquisition receipt, immutable archive/output claims and prior
review. They are code-reviewed declarations, not a live ledger or a body
integrity check. The existing ledger remains authoritative. All 24 country/type
cells remain required and unfulfilled. CPI progress is additive to the earlier
selected-closure gap: 16 existing observations, 16 period/scope rows reviewed,
3 source values sampled, zero new source records processed or admitted here.

To exercise the bounded CLI without source files:

```sh
python3 -B - <<'PY' | python3 -B -m offmenu.refresh.portfolio_01 --country AI --now 2026-10-18T00:00:00Z
import json
from offmenu.refresh.portfolio_01_contract import CONTRACT
c = CONTRACT['countries']['AI']
print(json.dumps({'metadata': {'receiptPins': c['receiptPins'],
    'acquiredAt': c['acquiredAt'], 'lastValidatedAt': None},
    'previousKey': None, 'fetchPolicy': 'reuse'}))
PY
```

CLI input is at most 64 KiB from stdin, parsed with shared strict JSON (duplicate
keys rejected); stdout is shared canonical JSON. Exit 0 means a successfully
assessed **held metadata plan**, not successful source processing; exit 2 means
invalid/unsupported assessment. An explicit UTC clock makes replay deterministic.

## CPI binding and synthetic validation

`cpi_origins` declares Table 2.7-4 columns D:S, period row 9, value row 13,
publisher code B13, publisher label C13, definition B6 and unit B7. The retained
source ID is `6da4880fe235645f4c26`; the release is identified by the exact
recorded workbook SHA, separately from publisher last-modified and acquisition
time. The scalar numeric lexical and numeric value remain distinct. Units are
index points, basis March 2010 quarter = 100; currency and physical quantity
remain explicit nulls. CPI is not a current offer, item price or basket quantity.
The 2017 Table 2.7-4 / Table 2.7-8 disagreement remains held and unblended.

`stage_authored_fixture` accepts only `authored-portfolio01-cpi/synthetic-1`.
Its tiny fixture is authored in `tests/test_portfolio_01.py`; its synthetic input
pin identifies a fixture contract marker, not a retained workbook or measured
source asset. The adapter checks exact source selectors as well as shared
`field_origin_errors`, validates native semantics, then uses shared
`encode_records` singleton-array JSONL. Wrong source identity, omitted origins,
changed coordinates, imputed units/basis/nulls and lexical/numeric disagreements
fail. Source nulls stay null. A valid fixture proves only this authored fixture
scope. No real-body parser, `SourceContract`, acceptance call or gold promotion
is installed by this package.

## Cache and replay meaning

The planner uses the shared `MIN_TTL` of 30 days, shared UTC timestamps and
canonical hashes. Acquisition age comes from the exact original receipt;
validation age is separate and never resets acquisition. AI acquisition is
2026-10-14T21:17:45.188626+00:00; other original acquisition times are deliberately
null in this bounded declaration. Publisher release dates are not substituted.
Under 30 days every fetch policy yields a no-download plan, including explicit
revalidate/force-download requests. At 30 days the plan requests conditional
review; existing holds still prohibit download. This module never performs I/O
against a body or network, even for stale entries.

The metadata key includes the trusted portfolio declarations, source/release
pins, policy version/selectors/constants and shared serialization policy. A
matching prior key is a metadata-plan no-op across changed validation times;
changed declarations/policy invalidate it. It is not source-content equality,
cached-body verification or proof an output exists. Future authorized real
processing must use shared acquisition/acceptance APIs with byte verification,
source-specific reviewed contracts, output checks and bounded isolation. Changes
to adapter semantics require a policy version bump and independent review.

## Remaining dependencies and ownership

* AD: catalogue unacquired; restrictive viewing/copying terms. Custodian 52's
  exact metadata return did not grant use or establish global absence. Morgan
  must select any further source-use route before acquisition/derivatives.
* AG: exact selectors/use contract remain with custodian 12 under existing
  `B01-W01-AG12-EXACT`. Do not duplicate acquisition or retry denied merchant
  sources. Menu/trade documents do not supply item-price/basket acceptance.
* AI: custodian 50's retained acquisition and reviewer 11's scoped prior result
  are linked only. Rights, full-value verification, 2017 conflict and missing
  item/basket coverage remain. The personal register stays excluded.
* AL: private originals do not establish derivative permission, structured
  record selectors or nutrient composition. Existing composition 403 hold stays.
  Morgan owns selection of any exact custody/use resolution.

Existing integrator 00 owns the bounded independent review/integration route.
Existing 25 review, 57 NL adapter and 64 assessment are separate lanes; no shared
core or country engines were copied or edited here. Source custodian labels are
historical ownership evidence, not proof of current execution. Production, CIX,
DEV7645, source-denial and actual-permission holds remain unchanged.

## Validation

```sh
python3 -B -m unittest discover -s tests -p test_portfolio_01.py -v
```

Tests cover valid authored mapping, explicit nulls, exact origins, real-source
rejection, held/missing/malformed/stale metadata, immutable pins, clock ordering,
30-day boundary across fetch policies, independent country errors, replay,
bounded/redacted CLI and deterministic output. They access no retained bodies.
