# AO / IL / PM metadata-to-staging bindings

Base: verified develop snapshot `abecb99ee1125730ccbc2824b6ec49ffc5cc4302`.
These portfolio-owned modules reuse shared `refresh.core` strict JSON, canonical
serialization, hashing and UTC parsing, and `field_provenance.field_origin_errors`.
They add no source parser, downloader, shared core patch or SourceContract.
The pending PR42/28a5 handover tree is not an accepted implementation baseline.

Run from this checkout with an explicit validation clock:

```sh
python3 -m offmenu.portfolio_owner02 --now 2026-10-18T05:00:00Z
python3 -m offmenu.portfolio_owner02 --now 2026-10-18T05:00:00Z --format metadata-jsonl
python3 -m unittest tests.test_portfolio_owner02 -v
```

The CLI reads only the eight exact catalogued receipt JSON files, bounded to2MiB
each. It never opens `opaqueSourceAssets`, a PDF, menu HTML, archive or a source
URL. The Python API accepts already-supplied metadata bytes; it performs no
acquisition. Each source independently returns `METADATA_READY`, `MISSING`,
`HELD`, `MALFORMED` or `STALE_INPUT`. A bad source does not erase peer results.
`METADATA_READY` means a metadata candidate is structurally reproducible; even
this result always has `sourceProcessingAllowed=false` and `countryAccepted=false`.
The optional metadata JSONL uses the existing shared singleton-array serializer.
The report pins its exact bytes and metadata input inventory in an explicitly
unadmitted metadata manifest. Its records include held source references and are
not parsed/normalized recipe, nutrient, price or other source-body data.

## Exact retained scope

`portfolio_owner02_catalog.py` pins metadata paths, byte extents and SHA256s;
source/release literals; receipt-relative field pointers; opaque original asset
references; explicitly unknown units/bases/selectors; and remaining source holds.
`EVIDENCE_REFERENCES` pins existing country manifests and addressed custodian
responses, with exact selectors. They are evidence references, not runtime rights
grants. No config or manifest is turned into a trusted shared SourceContract.

| Country / source | Lead type and remaining boundary |
|---|---|
| AO Sabores6911 | Recipe/ingredient lead; recipe scope and private extraction use NOT_HELD by addressed metadata respondent18. |
| AO EPIC SANA0eec | One merchant/menu lead; exact section and structured use unqualified, not a provider register or item-price dataset. |
| AO CIPRAedc7 | Historical production context; not an item-price/basket schedule; table/use unqualified. |
| AO MINAGRIFe7de | Recorded timeout, original absent; no retry. |
| AO INE IPCNJune2024 | Landing metadata only; explicit rights barrier, report/table absent. |
| PM IEDOM1853 | Economic-reference lead; caption/page/row/column and private extraction/attribution decision NOT_HELD by respondent33. Index/rate/base/unit unknown. |
| PM Feu3e31 | Named menu snapshot; not a measured recipe corpus or qualified structured-price export. |
| IL CBS HES2023/1994 | Report absent; licence-acceptance authorization held. No data acquisition or terms acceptance. |

All eighteen country/type requirements are explicit in the CLI's `requiredCells`.
Source leads are not reviewed applicability/completeness. Nutrition and dietary
reference inputs remain missing; no country defaults, proxies or equivalence are
invented. Each source value in a metadata candidate has a receipt pointer/hash;
each null unknown has a declaration-identity constant origin. The shared origin
validator checks every data scalar. Pointer resolution and expected literals are
also checked by this portfolio adapter; it cannot verify source-body semantics.

## Acquisition, validation, replay and cache seam

Original acquisition is read from its exact receipt pointer or left null.
`validatedAt` is the caller's UTC clock and never resets acquisition age. The
binding key includes the declaration, candidate and portfolio/shared-validator
source hashes; it excludes validation time. The same source/declaration/code
therefore yields `no-op` when supplied its previous key. Changed metadata bytes
produce `STALE_INPUT`, never silent repinning or an automatic fetch.

Under30days the cache intent is zero download. At or over30days the intent is
conditional **review** only, also zero download. Unknown acquisition time remains
unknown. This is not a cache writer, actual retention authorization, a dispatch
handler or acceptance of30day reusable dataset content. No force-download mode
exists. Unresolved rights/actual source holds remain independent gates.

The existing `core.cache_policy` hardcodes Wikibooks identity, while
`policy.plan_fixture` accepts a registered fixture. Neither is called with a fake
identity. Integration00 should supply/select a reviewed source-neutral planner
before wiring this metadata intent into the real refresh runner. Requested seam:
explicit source/release/content key, original acquisition, validation events and
injected UTC clock in; source-neutral age/reuse/conditional-review intent out;
no transport, repinning or rights decisions. No shared-interface edit is included.

Diagnostics contain fixed codes, source-local status and no raw payloads. The
small authored tests cover valid origins, absent metadata, held/missing scope,
pin drift, malformed/duplicate/nonfinite JSON, wrong literal/pointer, original
versus validation age, exact30day boundary, replay identity and isolated peer
errors. Positive fixtures are authored metadata only, not source admission.

## Official CBS documentation delta

On18October2026 the official [CBS End-User License](https://www.cbs.gov.il/en/Pages/Enduser-license.aspx)
was read as documentation, without accessing the held report. Its English
v2.1 is dated3January2016. The section `Use of information under this License`
links use to acceptance to the extent required by law; `Permitted Uses`,
`Acknowledgement of source` and `Scope of this license` retain conditions and
exclusions, including personal data, unauthorized access and third-party rights.
The page says the access-time terms govern. This resolves the earlier missing
clause-documentation gap only; it does not accept terms or establish report-specific
applicability or release the existing authorization hold. Exact lookup provenance
is frozen in the external task receipt's CBS documentation evidence artifact.

## Integration and remaining work

Reviewer05 corrections W02-R05-P2-001/002 preserve malformed-source isolation:
replay lookup only uses string source IDs. CLI metadata reads isolate each
source, reject symlinks and nonregular or multiply linked files, and enforce
the size bound on one nonblocking descriptor. Directory descriptors reject
parent symlink replacement; parsed and pinned bytes come from the same read.
Missing metadata still reports `MISSING`; invalid paths report `MALFORMED`.
Authored regressions cover list/dict IDs with a valid sibling, FIFO, symlink,
hardlink, directory, oversized/missing/wrong-suffix paths and deterministic
final/parent symlink replacement. No retained source bodies are test inputs.

Only portfolio modules, tests and this document are owned here. No raw data,
shared adapter registration or core/schema/CLI change is made. Submit the immutable
commit and evidence to existing integration00 through Morgan's selected route.
Independent review and develop integration are required. Later real STAGING needs
exact permitted body/selector inputs, reviewed schemas/semantic callback, asset
inventory and original units/bases, using shared SourceContract/qualification
interfaces. Golden promotion remains later. Finland/Frida/source/no-read holds,
nativeNO/FR crash restrictions, production/CIX pause and DEV7645 custody remain.
