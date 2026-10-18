# Worker37 portfolio metadata/staging binding proposal

Base: accepted develop `abecb99ee1125730ccbc2824b6ec49ffc5cc4302`, tree `cc06fde03b4f4b8d074e72aeb3e040a91e01dfc5`. Scope: NP, PK, PS, SK configuration and metadata interface. Independent review and integrator00 integration remain pending. Shared core is unchanged.

`offmenu.refresh.portfolio37` produces deterministic authored binding metadata with shared `serialization.encode_records`, `field_provenance.field_origin_errors`, strict JSON, timestamp and byte-pin verification. Its metadata records trace every scalar to the exact authored configuration JSON pointer, not to unobserved raw cells. Separate `nativeFieldOriginDeclarations` retain only evidenced native selectors; unresolved fields are explicit nulls. Exact retained validation, original-acquisition and review manifests remain distinct.

The four primary bindings cover NP archival appendix reference, PK undated merchant schedule locators, PS World Bank P507164/2025 context reference, and SK pinned CP01 JSON-stat2 index/rate slice. PK also retains the separately returned PBS SPI week-ended2026-02-26 metadata binding. Local binding IDs/content-addressed release aliases are explicitly not publisher identifiers or proof of current editions. All24 required country/type cells remain partial or missing. No food datasets, source admissions, complete categories or gold records are created.

## Use

```sh
python3 -m offmenu.refresh.portfolio37 --now 2026-10-18T05:00:00Z
python3 -m offmenu.refresh.portfolio37 --now 2026-10-18T05:00:00Z --verify-retained-metadata --output-metadata /absolute/approved/existing/directory/metadata.json
python3 -m unittest discover -s tests -p test_portfolio37_bindings.py -v
```

The explicit clock is metadata validation time. The first command performs no retained-receipt reads. The second reads only two allowlisted, bounded metadata documents per primary source, never original paths or retained candidate bodies. Its output is an exclusive authored-metadata JSON report. Identical replay is a no-op preserving inode/mtime; a changed frozen output conflicts and requires another caller-selected path. The shared singleton-packet JSONL representation is available through `encode_records(metadata_records())`, and its content hash is reported separately. A completed assessment is not source qualification; malformed assessments return exit2, while explicitly reported missing/held/stale states remain typed results.

No generic source-neutral pure cache planner exists at this base. `core.cache_policy` is Wikibooks-specific and `plan_fixture` is registry-only; neither is invoked or spoofed. `CachedAcquirer` is never instantiated or run. The local four-binding metadata intent uses the shared minimum30day constant only: an established original acquisition below30days yields reuse/no-download intent; at or above30days it yields conditional-refresh-review/no-download intent. A metadata check does not reset original age. NP/PK/PS receipt timestamps do not establish transport completion, so original acquisition age remains unknown. SK uses pinned `finishedUTC`. No intent verifies original bytes, lifts source holds or enables a download. Integrator00 result5798 describes a possible central pure helper; any shared extension remains proposal-only, not implemented here.

## Evidence and limitations

NP12-column units and per100g-edible basis remain author assertions, with independent reference-consistency review only; no numeric-cell map is invented. PK has28 private page/week/day locators and no established price/currency/effective-date or complete recipe fields. PBS is a distinct statistical lead with no table dictionary/measure/unit/currency/market mapping or current native custodian established. Missing custody is not a legal prohibition. PS has one attributed context reference and positive retained work-level notice; tables/figures/images remain component-specific, and WFP403 remains no-retry. SK selected1845coordinates (1749numeric,96absent,18true zeros) retain native index/rate units, bases, presence/status and last-dimension-fastest declaration. No currency or basket-quantity equivalence is inferred. These are retained evidence counts, not rows processed in this assignment.

Current official documentation read on2026-10-18:

- [Eurostat API Statistics](https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-detailed-guidelines/api-statistics) confirms JSON-stat2 and dimension filtering. No API data request was made.
- [Eurostat copyright/reuse notice](https://ec.europa.eu/eurostat/en/help/copyright-notice) supports reuse with attribution, change indication and exceptions; it does not remove current assignment or component restrictions. The older `/about-us/policies/copyright` URL returned404; no rights inference was drawn from that failure.
- [World Bank OKR terms](https://www.worldbank.org/ext/en/legal/terms-conditions/open-knowledge-repository) retain per-work terms, attribution/adaptation conditions and third-party component review. The actual retained report notice remains the exact work-level evidence, rather than replacing it with a generic licence.
- [PBS dissemination policy page](https://www.pbs.gov.pk/data-dissemination/) states Tier1/2 reuse with attribution. The linked policy PDF timed out once; its consultation-draft/adoption status and exact-release applicability remain unconfirmed. [PBS price-statistics documentation](https://www.pbs.gov.pk/price-statistics/) describes weekly SPI51items/50markets/17cities, without supplying this retained release’s table dictionary. No current dataset link was opened.
- Bounded official-domain searches did not establish a current NAST book numeric-derivative grant or Pakwan reusable-corpus licence. Absence from that search is missing evidence, not an explicit denial or a claim of global nonexistence. Search-discovered source PDF bodies were not opened.

All raw bodies stay on Foo. Explicit source-use/private/credential/403/Finland/Frida/NO-FR crash/denied-action holds and mandatory auto_review remain. Production, CIX and DEV7645 are unchanged. No shared acquisition, runtime dispatch, curation, graph, accepted pointer, scheduler or source-body engine is installed.

## Review/integration packet

Owned additions only: this document, `offmenu/refresh/portfolio37.py`, `offmenu/refresh/portfolio37_bindings.json`, `tests/test_portfolio37_bindings.py`. Authored fixtures cover valid/missing/held/malformed/stale states, all-datum config pointers, independent peer diagnostics, timestamp identity and30day boundary, bounded receipt integrity, deterministic replay and tampered-output refusal. The shared qualifier test grants only authored fixture scope and explicitly rejects production acceptance and metadata tampering.

No shared-interface code change is proposed for this package to work. Future source-neutral cache-helper consolidation is integrator00-owned and separately reviewed. Source-body adapters and real-source `SourceContract` admissions remain unsupported until an exact scoped assignment, applicable use evidence, native field mapping and independent acceptance exist.

Gateway is the human-authorized handoff route in this session. Direct00 messaging has no human-origin authorization here, so the immutable packet is supplied to Gateway for the existing00 review/integration route. Transport is separate from acknowledgment, independent review and develop integration. Worker37 retains correction ownership while waiting; no finished test is rerun without a relevant change or failure.
