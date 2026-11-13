# Worker09 BH/KI/RE metadata staging bindings

This portfolio package stages pinned **retained metadata references**. It does
not parse a recipe, CPI table, nutrient release or other publisher payload, and
does not install source admission, a GLOBAL handler, canonical mapping or gold.
The base is accepted develop snapshot
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`; pending PR42/handover code is not used.

## Run privately on the selected local executor

```sh
python3 -m offmenu.portfolio_worker09 \
  --metadata-root /home/user \
  --output /tmp/worker09-metadata-staging \
  --now 2026-10-18T00:00:00Z
```

The output directory must be exclusive and separate from every selected input's
directory. The root is a prefix for exact relative JSON pins in
`offmenu/portfolio_worker09_sources.py`; no inventory, glob, URL access,
archive extraction or publisher-body path inside a receipt is followed. No
third-party packages, credentials, AI calls or network are required.

the product integrator's baseline/interface receipt5798 confirms there is no generic pure
cache planner at this base. These age fields are portfolio metadata diagnostics,
not a new shared planner. Neither the Wikibooks-specific `core.cache_policy`,
registry-only `plan_fixture` nor operational/body-reading `CachedAcquirer` is
called or spoofed. A source-neutral shared planner remains an unimplemented
proposal owned by00; it does not block this metadata binding package.

`--now` is the explicit UTC evaluation time. `--validated-at` optionally records
a distinct observation time. Neither mtime nor validation time changes
`originalAcquiredAt`. Under30days the policy performs no download; at30days it
returns `stale-input` and requires separate conditional review, still with no
download implementation or force override. `retentionQualified=false` is
preserved for the actual portfolio: the scheduling threshold does not supply
missing source-specific retention/use entitlement or promise30day legal reuse.

## Exact applicability and provenance

| Binding | Input representation | Outcome extent |
| --- | --- | --- |
| BH BFM catalogue | Prior private seven-link candidate plus acquisition and lineage receipts | Seven discovery/reference observations; indexes, submission, certificates and cookbook link keep separate roles |
| KI NSO September2025 CPI | Acquisition receipt metadata only | One historical release-reference observation; no CPI values, item prices, currency or basket |
| BH recipe body | Held descriptor, scoped41 NOT_HELD response | No file opened; exact lawful body/use/selector missing |
| KI recipe body | Held403 descriptor | No file opened; no recipe source or reuse grant inferred |
| RE INSEE issue299 | Held ALTCHA/zero-good-bytes descriptor | No original existence asserted, read or retried |

The local `retained-*` source IDs and `*-as-recorded` release labels are explicit
portfolio binding identities, not additions to the shared discovery registry or
proof of publisher release equivalence. All six required domains remain
unaccepted for every country; metadata in a recipe/price discovery category is
not category coverage. Native units and bases are explicit nulls with code-policy
origins because these records establish no quantitative observation.

Each emitted `sourceMetadataReference` uses the shared singleton-array JSONL
serialization. `provenance.fieldOrigins` covers every scalar under `data` using
the shared `field_origin_errors` validator. Source origins address exact input
JSON pointers and hashes, with original record IDs retained inside `sourceRecord`.
Unknown-unit/basis constants cite the binding-policy digest rather than invented
source cells. BH's upstream publisher hash and anchor provenance are declared
through the previously verified, pinned lineage receipt; this code does not
repeat that source-body comparison. The manifest pins original acquisition
evidence separately from the content candidate and from validation age.

## Replay and diagnostics interface

`build(config, metadata_root, now=..., validated_at=...)` returns a result per
binding. Supported outcomes are `metadata-candidate`, `missing-input`,
`held-input`, `malformed-input` and `stale-input`; fixed diagnostic codes preserve
independent results. Source holds return before any file read. Duplicate JSON
keys, nonfinite JSON, pin drift, unsafe paths/symlinks, unsupported profiles,
wrong country/source/flags and acquisition mismatch fail explicitly.

`publish_report` uses a portfolio-owned, nontruncating flock inode and the shared
atomic JSON helper. Existing lock/report/partial/candidate files must be regular,
single-link files owned by the current effective user; the output directory must
also be owned. Guards run before output-slot mutation and again under the lock.
The opened lock descriptor is checked against its current path/inode. Its
contents are never written or truncated. This corrects W09-R05-P2-001 without
changing the shared `writer_lock` implementation. The output namespace remains
exclusive to this invocation family; this is not an OS sandbox against other
processes running as the same user.
Candidate filenames contain their canonical SHA256; identical bytes are a
no-op without rewriting the candidate. Later failed/held/stale inputs do not
delete or activate old artifacts: only candidates referenced by the **current
successful invocation's** `report.json` are eligible for further review.
Always bind the process exit status and current report bytes. A terminal CLI
configuration/filesystem failure prints a fixed JSON diagnostic on stderr and
exits2; a previous report is not evidence of that failed invocation's success.

CLI exit0 means every descriptor returned metadata-candidate or an explicit
hold; it does **not** mean all sources are usable. Missing/malformed/stale inputs
exit2 after writing all independent binding diagnostics. Global config/output
errors also exit2. No country/source acceptance receipt is produced.

Malformed descriptor IDs remain null diagnostic identities with their stable
`bindingIndex`; only validated string IDs enter the duplicate index. Multiple
malformed descriptors keep one fixed failure each and cannot abort a valid
following binding (W09-R05-P2-002).

Tests use small authored JSON objects and temporary directories, including
valid, missing, held-with-no-read, malformed/duplicate/nonfinite JSON, stale and
exact30day boundary, acquisition/validation separation, unknown retention,
field-origin coverage, lineage mismatch, independent-error continuation,
immutable replay/no-op, URL/path restrictions and typed CLI failures:

```sh
python3 -m unittest discover -s tests -p test_portfolio_worker09.py -v
```

## PR43 catalogue and metadata-reader correction

The fixed catalogue is now an inert Python declaration, included by existing
`offmenu*` package discovery. `configuration()` returns a defensive copy; no
checkout `config/` directory is needed at runtime. Exact JSON-to-AST literal
comparison preserves every prior source pin, selector, clock, scope and hold,
and the canonical policy hash remains unchanged. No shared packaging file changed.
Offline wheel and sdist extraction checks run outside the checkout with no site
packages or corpus. Both load the catalogue and produce two missing-input plus
three held-input diagnostics against an empty metadata root, rather than failing
to find the fixed catalogue (PR43 comment4305926950, owned Worker09 scope).

The metadata reader rejects a nonregular path before open, then uses
`O_NOFOLLOW | O_NONBLOCK` and checks regular type, inode identity and bounded size
on the opened descriptor. It reads at most MAX_METADATA+1 bytes through that same
descriptor and authenticates the exact byte count/hash before parsing. A FIFO or
replacement file returns an isolated fixed diagnostic; a valid following binding
still runs (PR43 comment4305926954). Authored probes cover the CLI FIFO timeout
regression, replacement between lstat/open, directory/oversize rejection and
normal reads. Prior output-lock and malformed-ID fixes remain intact. This is
not a new grant to inspect source bodies or a sandbox against same-user changes
to parent directories.

## Integration and remaining blockers

Only the portfolio module/config/tests/document are owned here. Shared helpers
are imported unchanged: `refresh.core`, `refresh.field_provenance`,
`refresh.national_tabular.valid_input_name` and `refresh.serialization`.
No existing generic payload adapter claims compatibility with BFM HTML or CPI
PDF; this package does not misroute them into national/reference engines.

No shared-interface change is required to run this direct metadata CLI. To use
it in GLOBAL, the product integrator must separately select/review an explicit generic
metadata-reference candidate schema/handler and trusted scope/rights contract;
no source manifest or CLI flag may construct a `SourceContract` grant. That
future shared registration is a proposed integration dependency, not edited
core or activated execution. Independent review and develop integration of
the owned portfolio paths remain required before the next request.

Actual BH/KI content extraction, recipe rights/body selectors, KI CPI reuse and
table/unit/base selectors, all other six-domain inputs, and30day retention terms
remain missing/held. RE keeps zero valid original bytes and ALTCHA. Preserve
Finland/Frida/native NO-FR restrictions, original source custody, production/CIX
pause and DEV7645's separate owner. Golden promotion is later.
