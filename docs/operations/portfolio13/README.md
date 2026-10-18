# MQ/MR/MS/MT metadata staging bindings

Base: accepted develop snapshot `abecb99ee1125730ccbc2824b6ec49ffc5cc4302`.
This package supplies portfolio configuration, a deterministic metadata binding
hook, and authored fixtures. It does not add a country parser, an admission,
rights decision, network transport or source-body handler. Pending PR42 is not
used. Shared core is unchanged.

## Run

From this checkout, with the existing Python runtime:

```sh
python3 -m unittest tests.test_portfolio13_bindings -v
python3 -m offmenu.refresh.portfolio13_bindings --describe
python3 -m offmenu.refresh.portfolio13_bindings --metadata-root /home/user --now 2026-10-18T08:00:00Z
```

The last command reads only four exact, bounded, pinned JSON receipts. It returns
exit 2 and four **held** source reports. That is the expected real-source result,
not a failed dataset run or a reason to download anything. Each source has an
independent fixed-code diagnostic; one missing/malformed/held source does not
hide a valid peer. The CLI cannot install alternate bindings or remove holds.
The committed `source-bindings.json` records pins, selectors and native-context
evidence for review; it is documentation, not an executable permission file.

## Shared interfaces

- `core.strict_json`, `verify_source`, `safe_path`, `timestamp` and canonical
  fingerprints supply bounded metadata validation. Duplicate keys/nonfinite
  numbers, pin drift, invalid source/release and missing selectors fail closed.
- `field_provenance.datum_pointers` and `field_origin_errors` cover every projected
  metadata scalar, including null and array values. The source fields are exact
  receipt JSON pointers, not newly observed dataset cells.
- `verification_handler(binding, root, clock=...)` implements the existing
  `StageContext -> StageResult` interface for **verify only**. Source/stage mismatch
  fails. The result reports zero source observations. The caller still owns the
  reviewed resource/isolation boundary and registration. This does not mark a
  `Binding` reviewed or install `execution.ADMISSIONS`.
- `global_run.write_report` publishes optional valid metadata artifacts using its
  existing atomic exclusive writer. Identical canonical output is a no-op;
  differing output is refused. There is no raw payload copy. Fixture artifact
  scope is explicitly `authored-fixture`, never accepted country data.

No shared-interface change is requested. Integrator00 should review/register only
the portfolio metadata hook through existing interfaces if independently approved.
Actual acquire/parse/normalize/qualify/accept handlers remain absent. A metadata
artifact is not `candidate.jsonl` under a production `SourceContract`; real
source candidate schemas, operations and per-field semantic acceptance still
require exact reviewed contracts. Do not reinterpret valid metadata as valid data.

## Acquisition, validation and replay

Integrator00 result5798 confirms there is no generic pure cache planner at this
base. `core.cache_policy` is Wikibooks-specific and `plan_fixture` is registry-only;
neither is used or impersonated. `CachedAcquirer` is operational and may read
bodies/fetch, so it is never invoked. This portfolio check reports offline
metadata freshness only. A shared pure planner remains a separate proposal;
real acquisition and source-body staging are unsupported here.

The shared `acquisition.MIN_TTL` is 2,592,000 seconds. An explicitly evidenced
original acquisition time controls this metadata freshness gate. At less than
30 days a valid fixture reuses the retained input; at exactly 30 days it returns
`stale-input` and emits no new artifact. No outcome can initiate an HTTP request.
Validation time is diagnostic only and is excluded from artifact identity; it
never resets acquisition time or changes the content fingerprint. There are no
force-download or revalidation switches in this interface.

The four real profiles deliberately leave `acquired_pointer` unset. Their
receipt capture/request timestamps are evidence with their own meaning, not an
independently reviewed acquisition-completion/cache contract. This is an explicit
missing dimension, not authority to reacquire or reset the clock. The fixture
contains a separately authored original-acquisition field to test the boundary.

Optional `--output DIRECTORY` is private metadata output only. Real held profiles
write nothing. Replayed identical valid fixture output retains its bytes and
mtime; conflicting artifacts and symlink paths are refused. Artifact fingerprints
and validation-age diagnostics are distinct. No persistent source scheduler,
automatic refresh, shared cache mutation or background job is introduced.

Metadata and existing replay bytes use the same owned regular-file reader:
no-follow directory-descriptor traversal, nonblocking final open, regular-file
and size checks before reading, bounded reads from that single descriptor, and
post-read identity/size/time checks. FIFO and replaced-path refusals return typed
diagnostics and preserve later peer progress; no existing replay is overwritten.
This is a local file-ingress guard, not a new shared cache engine or OS sandbox.

## Evidence and remaining source blockers

| Country | Retained input role | Required next evidence |
| --- | --- | --- |
| MQ | Agreste catalogue receipt; not original tables | Recognized source custody, lawful complete release and MQ selector. Certificate barrier remains no-retry. |
| MR | FEWS CSV acquisition/structure receipt; not a new CSV parse | Dataset-specific historical denomination/rescaling and package/value basis; recognized custody; exact operation/semantic acceptance. |
| MS | SDM table-index receipt; not linked workbook | Complete workbook manifest, version, EOF, sheet/range/row extent, base/month/unit/use and actual custody. |
| MT | Kusksu page receipt; not copied recipe content | Yield/servings, ingredient identities/basis and Taste.com.mt use evidence. Booklet403 and restricted thesis stay held. |

MR literal currency/unit tokens in `source-bindings.json` reference the already
frozen validation metadata. They are not approved currency/unit identities or
conversion factors. The earlier 20-row private literal review does not accept
the other package/unit groups. Unknown values remain explicit; no names, numbers,
dates, country membership or semantic equivalence are repaired.

All six applicable country data types remain obligations. These metadata roles
cover only the listed source/type relationships; they do not assert complete
ingredients, recipes, nutrition, providers, prices/baskets or dietary references.
Per-datum source fidelity, source-specific rights/operation decisions, complete
input manifests, semantic/schema qualification and independent review are still
required before real staging. Golden admission is later.

Finland/Frida, native NO/FR crash restrictions, private/credential/action denials,
production/CIX pauses and the separate DEV7645 custodian remain unchanged. Raw
data stays on Foo. The tests use a small authored JSON fixture and temporary
metadata directories; they do not open actual original bodies or use the network.
