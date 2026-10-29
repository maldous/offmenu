# Candidate v197: shopping unresolved demand — local build handoff

Status: exact focused correction integrated on the frozen v196 source closure,
128 combined tests passed, one approved browser build completed. Candidate only;
independent review, full Worker-module asset splice and Cloudflare served
verification remain with the sole native integrator. No live deployment, Git push,
provider call, credential read/change, package install or unrelated corpus check.

## Source and preimages

Input Library archives were transferred once successfully outside the command
sandbox and verified before safe extraction:

* production196 source/build ZIP: 826674 bytes,
  SHA256 0bba79fe1587170595d1ba50dc1bbd179b0f4e7c87555e95aed442b26076ca18.
  All 192 exact paths verified; original ALLOWLIST SHA256
  36ce221c17dd14452b09ed5524578c14bb71f5df3434668f8b946030a2b07c50.
  Custodian pointer supplied by parent: maldous/offmenu commit
  92a0463b3f4ef48fa96ec2fe5adc65a3c513700a.
* shopping correction ZIP: 10577 bytes,
  SHA256 97701e6069bad8509312f0bf985c90cb82117e9b162bc8c66e48b26b7185afac.
  Exact author patch SHA256
  9e3f8226e96581d9b6d2c3d3d49716d9cf33fdd67638d1e90906bb7d6b904746.

Actual v196 integrations.js matched required preimage
c2267eae3fe78e1d7c457af0e325e95bef90828b9fe7919c883b3db128ce63f9.
After the exact two replacements it matches the author candidate
fbe3f4efc7131e2a318858671acf18cc29f48949ccf731d99c37577e1590a6ee.
The new focused test matches
4f30d4d9a26fc0ab4540b1c905354ab1e316cab1a6e0e1a07161463a40dc9b8c.

The v196 menu helper has newer hash
f3d33960451af9e0676489b324ec7f8af05f4f59c261661fad349ae2323e9c3e,
not the author's v195 baseline. This was reconciled before source mutation:
reversing only the two included reviewed v196 lot-nutrition hunks IN MEMORY
reproduces exact baseline
71a4f4f4e05d8c62a49ac55233448be42346427e528c485ecc76b7a7cbaeec16.
Actual helper and all lot-nutrition/model/cooking/server parity files remain
byte-exact v196. ingredients.js matches the author's pin unchanged.

Only integrations.js and the new focused test change app source. The normalized
source manifest updates the target hash/length and records this correction. All
other 189 existing allowlisted payload paths remain byte-exact. Original v196
ALLOWLIST is retained separately as evidence; root ALLOWLIST describes this new
handoff's actual bytes.

## Behavior and verification

Required ingredient demand whose recipe yield/review status or measured amount is
unresolved stays visible as Review source quantity, without a numeric purchase
quantity. Measured deficits still come from planSummary. Optional ingredients,
source wording, checked/custom rows, prior v195 lifecycle corrections and v196
lot-specific nutrition behavior remain intact.

The eight author cases passed on the actual v196-overlay candidate. The approved
combined Node test suite passed 128/128, zero failed/skipped/cancelled. Exact log
and argv/elapsed receipt are in handoff-evidence/. Only this changed caller and
its existing combined focused checks were run; no source/corpus qualification or
live authenticated acceptance is implied.

The command sandbox interferes with Node process-isolated test reporting (it
reported only a file wrapper); those wrapper passes are NOT evidence of the eight
cases. An in-process diagnostic and the same focused command outside the sandbox
both reported the eight actual cases. The authoritative combined run used the
normal recipe outside that process sandbox and reported all 128 cases. The initial
file-wrapper-only log is retained and explicitly labeled diagnostic.

## Build and artifact use

Frozen build-browser.mjs is unchanged, SHA256
58f213558f86e84e35b57417b7e005722e6fd552f8446e517ec0adaa8d0a6d8b.
It verifies every current normalized source pin and the two official auth-entry
pins, rejects unpinned inputs/external imports, and used existing esbuild 0.25.12.
No installation occurred. A local-only toolchain/node_modules/esbuild symlink
bound the expected recipe path to the existing installation; the symlink and
binaries are excluded from this source handoff.

One build invocation from source/:

    node build-browser.mjs candidate-source-root candidate-build

The actual local output candidate-build/app.js is 468716 bytes, SHA256
8baa2f039eacbe6abcabed5df59ec7a18c1981901a789045e2ad41133e627814.
It has zero external imports. The scanner and guest groups were unchanged source;
the frozen recipe's outputs/metafiles are included for custody, not instructions
to replace production's custom guest graph. The prior v196 app was 468574 bytes;
this is an observed 142-byte increase, not a performance/savings claim.

The input package intentionally excludes the full production Worker runtime
module. Therefore no full generated Worker/main server module is fabricated here.
The sole integrator must splice only this app asset into its exact reviewed v196
runtime module (input module SHA256
965d7eaff351e9aec7278fdd5db0f6ab6ccfbcf3748a30611a57ce47772c4a6d),
keep custom guest/scanner assets and server parity invariant, and perform its
existing independent review/served checks. Do not run a generic whole-server or
guest replacement build from this package. Existing v196 evidence in source/
is historical input provenance, not v197 deployment evidence.

## Transfer correction and placement

Your Foo host DNS was healthy. The earlier DNS/download failures occurred inside
my command sandbox. A supported unsandboxed DNS check and Library helper transfer
succeeded; no host networking/authentication was changed. Two exact Library
archives were the necessary remote source transfer, with zero GitHub per-file
source reads and zero Git fetches/clones. Local reads/tests/builds stayed in this
isolated directory; no token, latency or production-gain claim is made.

Rollback for this candidate: stop using it; retain original v196 source and
integrator's current live v196 version. No live state was changed by this executor.
Original shared checkout was not overwritten, reset or checked out.
