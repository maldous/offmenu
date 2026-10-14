# Worker 12 lifecycle command correction re-review

Date:2026-10-15, Australia/Melbourne. **PASS - L12-01 resolved at `2c9b15bbd828de95752fa32343a4f5fb43ed147e`. No new reportable finding in this narrow correction.** Review applies to disposable lease/control command custody, not production-wide reset/deletion/backup replay, corpus/source transport, all-eight or whole105 acceptance. Source transport remains ASSIGNED-WAITING. Production STOP.

Exact parent `27169ac47167a456e6d0f46572af66500069d01e`, binary correction SHA256 `bc95be17a538cbfbbeea5f9c832191f86da9a8627ce24cc6bceb5a6a1a3098d2`, correction.diff. Source606/271 reports and packets remain preserved; original434bindingPASS unchanged. Only the new lease guard/test/probe/positive/doc paths change. No carried434 helpers retested or modified.

## Resolution and checks

The corrected live guard requires exactly two actual cmdline entries, runner at argv[1], resolved argv[0] equal to the selected Node executable and the /proc executable, alongside existing cwd/boot/birth/namespace checks. This matches the fixed spawn(process.execPath,[runner]) contract. A runner tag anywhere else in argv no longer substitutes for an executable entry point.

- Focused immutable snapshot tests:2/2pass,2-tests.log. Includes a genuinely unrelated Node process with inert runner tag; no producer/server starts.
- Unchanged original exploit script run against corrected source: expected nonzero exit at exact-entrypoint refusal, original-probe-after.log/.json. Not misreported as a passing suite; original script unchanged.
- Corrected independent probe using the same original input: live lease and stop admission refuse; wrong birth/lease refuse; no control executed (independent-command-probe.mjs/.log and command-boundary-probe.json).

Actual owner positive packet add80ee4e9a1e805e5f4d6dbe5bc790212e406f4050d5eac1fc43394e0291b79 independently hashed/read: genuine Node+runner argv, source2c9, four recorded HTTP checks, valid reset+graceful stop, stopped snapshot equal to current-run, exit0, PID1456363absent and18809currently refused. stdout hash retained in positive-packet-readback.json. These are owner-performed operations; reviewer performed none. Feedback receipt hash remains unchanged.

Snapshot source hashes are bound to2c9 in snapshot-manifest.json; dependencies referenced, no copies. All subprocesses remove inherited GIT_*. Only own harmless Node probes and readonly evidence/files/proc/refused-readiness checks executed.

## Composition of evidence and limits

Retained606packet53af5741 records44checks/12HTTP for two distinct exclusive leases/state/births: bounded user_state reset, foreign control refusal, graceful stop/readiness refusal, fresh empty restart and stale control refusal. Additive271 preservation packet c1d18f5a records a separate four-request reset/stop window with19durable receipt/SQLite-WALfiles3002768bytes equal before/after, -shm excluded. No raw data copied or old operations rerun. The later feedbackSQLite digest drift recorded by the reviewer is a separate later observation with no actor/cause attribution; no continuous immutability assertion.

The command-fix positive supports current corrected valid-control behavior; unchanged lifecycle logic and historical operations remain labelled with their actual606/271source pins, not re-stamped2c9. Reset scope remains only user_state rows within a qualification-created exclusive disposable D1. Real deletion/restore and source-policy withdrawal are not implemented by that reset.

PDF-backed requirement mapping/readability evidence is in the retained readiness directory (04pp1-10,02pp8-9 exactabe0hashes). Original434 producer/source/callback acceptance was not repeated or widened. Existing58 may consume this exact scoped control review and retained real operation evidence; any new source/runtime selection, live operation or transport admission needs its own exact current custody and authorized scope. No invented store/CAS/graph or permission grant.

## Preservation

Main/own HEAD/index stable; dataset branch not advanced/switched. Original report/probes and606/271packets untouched. First local recovery checkpoint ff9690f19a4869d187ba95ccaf84337c5980dcee remains reachable by refs/checkpoints/worker12-preview-lifecycle-20261015. Latest correction checkpoint/remote exceptions are recorded separately. Origin was verified private through existing GitHub connector. Managed workflow refused Worker12enrollment; no remote push/merge/security/trigger bypass.

Review complete for this narrow defect. Source transport ASSIGNED-WAITING; Morgan owns final qualification/integration. Same Worker12 available.
