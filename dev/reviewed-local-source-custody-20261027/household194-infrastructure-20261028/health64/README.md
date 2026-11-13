# Health contract correction for64-slot Foo supervisor

Live supported source read confirmed client marker count limit2, findings limit110. Metadata-only confined host read `01a180f6-9784-6567-381a-203ebe6990b8` confirmed exact retained host SHA03f61831f020fdbb5152d1ffbfd656966768559225b3fe1c72b24b2a91aa2957 and actual `range(2)` marker loop.

Small correction: scan64 fixed markers, allow64marker counts, raise bounded findings cap110→172 (64marker findings+100recent-job findings+8headroom). Preserve same64MiB/8second/100recent-item bounds and all old v1/v3 status semantics. No marker deletion, replay, cancellation or admission change. No credentials/logs/raw dataset reads.

Install new `platform_check_capacity64.py` create-only with exact old/new hashes and no-follow regular-file checks. Existing checker and active runner remain unchanged. This new file is not referenced by any current execution until shared checker caller is updated. It does not modify data, receipts, current markers or checkpoints; no need to acquire runner execution lock for this uniquely named metadata helper. Shared client path stays `u/admin/offmenu_platform_check`; schedules retainsameidentity/args/cron/privateACL.

38 focused offline checks pass, including high slot63 and64metadata marker fixtures+100selectedjob findings; no64process or load test. After independentreview, verify exact newfile/client readback and routine metadata-only health result, not full corpus verification.

## Live status — 2026-10-28 05:56 UTC

Following exact user approval, the one deployment retry succeeded. The deployed private client matches reviewed SHA `4d48d4ab293771fae9ad830ddf0c0d5e3e8535d1b7bc9dbdb8d83347b13fddc8`; its draft is removed. The installed helper matches `ca919ab491685c9b60bad9ff827b8da3e77ae5d3ec06424c160a8c386e2b2334`. Existing checker, schedules and permissions are unchanged.

Actual routine health run `01a18115-44d1-9a4a-a6f9-1c101450c921` succeeded: 93 recent jobs checked, selected metadata scope complete, one existing in-flight marker checked. The exact installed source scans all 64 fixed slot positions; this does not mean 64 markers/jobs were present or stress-tested. It is not full corpus integrity verification. See `DEPLOYMENT-STATUS.json` and `ACTUAL-HEALTH-READBACK.json` for sanitized evidence.
