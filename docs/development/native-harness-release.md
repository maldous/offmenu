# Frozen release qualification

UIF-128 implements the bounded release-cut and aggregation seam from ADR 0009.
`tools/delivery/release_qualification.py` consumes UIF-122's shared validator;
it does not copy that schema, dispatch work, grant admission, promote `main`,
create tags, or activate installed code. Legacy evidence readers remain unchanged.

## Profiles and acceptance

`config/release-validation-profile.json` contains reviewed command arrays:

- `integration`: affected delivery harness behavior using `tests/delivery`.
  This is routine scoped evidence. Owners still select affected checks for other
  changed seams. It cannot qualify a release candidate.
- `release`: the existing `npm run validate:release` baseline and explicit
  delivery harness tests. The baseline retains configuration/generated checks,
  web tests, build, edge tests, Python and explicit receipt OCR checks, in its
  existing order. Parallelism is between the two independent checks; dependencies
  within the baseline remain sequential.

A release candidate must require `release`. It may require additional reviewed
catalog profiles. Each check requires successful exit, complete coverage and
exact output hashes. Missing, partial, failed, cancelled, unknown, timed out,
unreconciled or unstopped-child results never pass. A timeout is failure evidence,
not permission to shorten a suite or silently mark coverage complete.
`qualified` means these declared local checks passed; hosted required contexts,
independent source/release review, canonical promotion/tree/tag readback and real
runtime/product acceptance remain separate owner gates.

## Cut, finite plan and native execution

Use the pinned delivery Python and the coherent checkout, with
`PYTHONPATH=src:tools/delivery`. The CLI writes JSON to standard output so the
existing graph owner can persist it in its private checkpoint custody. It does
not create another queue, manager or tracker. Input JSON is bounded to 1 MiB;
extra manifest fields and duplicate JSON object fields fail closed.

```sh
python tools/delivery/release_qualification.py cut \
  --source .delivery/release/source.json --artifacts .delivery/release/artifacts.json
python tools/delivery/release_qualification.py plan \
  --candidate .delivery/release/candidate.json
python tools/delivery/release_qualification.py request \
  --plan .delivery/release/plan.json --check release:local-baseline
python tools/delivery/release_qualification.py aggregate \
  --plan .delivery/release/plan.json --results .delivery/release/results.json \
  --evidence-root .delivery/release/evidence
```

The release owner explicitly selects accepted develop source. `source.json` is
the common `{repository,branch,base,head,tree,target,policy_sha256}` object, with
branch `develop`, target `main` and canonical `fingerprint(release_policy)`.
Artifacts are nonempty canonical relative `{path,sha256}` references with known
accepted bytes. The common candidate contains only version, kind, source,
required profiles and artifacts. `fingerprint(candidate)` is its identity.
No moving develop observation is stored inside it. A source, policy, profile
selection or artifact repair requires a new candidate and new qualification.
A changed execution catalog or runner/capacity policy requires a new plan and
invalidates previous result reuse even if the candidate stays unchanged.

The plan freezes catalog identity, runner file-byte SHA-256, capacity-policy
file-byte SHA-256 and every command/resource declaration. It gives each check
its own `/offmenu/data/release-candidates/<candidate-hash>/<profile>/<check>`
workspace. The execution owner must stage the exact immutable checkout and
qualified dependency/runtime closure there before submission, including the
pinned delivery Python where required. Do not use a moving shared checkout or
assume an installed editable package refers to this source. Commands explicitly
select candidate `src` and delivery tools through `PYTHONPATH`. Pre/post guards
check exact Git HEAD, committed tree and unchanged tracked bytes. The staging
owner must also exclude untracked source shadows and qualify dependencies;
Git guards alone do not prove dependency or runtime isolation.

`bridge_request(plan, check_key, policy, catalog)` yields the existing Windmill
bridge arguments `{action,job_id,command,mode,timeout_seconds,resources}`. Jobs
have stable identities bound to the plan and check. Unknown results reconcile
that original ID through native status before retry; regenerating a different
job ID is not recovery. The finite graph can submit independent requests
concurrently, subject to the existing runner's fresh shared aggregate CPU, RAM,
I/O, disk/process and logical read/write-root admission. Disjoint roots avoid
cross-check writer conflicts. The plan itself does not reserve capacity or
assert available resources. Declared resources are requests, not observed usage
or hard OS isolation. This component's focused local tests do not execute the
release baseline or consume a Windmill admission.

The old dispatcher permits only its reviewed read/180-second profiles. Do not
feed these release write requests through it or relax its legacy reader. The
new graph/dispatcher owner must consume the reconciled release seam and preserve
all original operation/job/lease identities. No bridge deployment is performed
by this component.

## Results, aggregation and reuse

A per-check result is exactly:

```json
{
  "check": "release:local-baseline",
  "plan_sha256": "<fingerprint of exact plan>",
  "coverage": "complete",
  "handoff": "<completed-native-validation-v1 shared handoff object>"
}
```

The handoff keeps its real issue/project/owner and origin evidence, exact
candidate source and artifact outputs. Its Windmill operation carries the
original operation ID, deterministic check job ID, terminal status, exact
command/runner/capacity-policy pins and a raw runner receipt reference. No coding
attempt is fabricated. Historical receipts remain opaque references consumed by
their existing readers; this aggregator reads only the declared runner result.

The evidence owner stages canonical relative receipt/output/evidence references
under one bounded local evidence root. The aggregator verifies actual bytes,
rejects escaping/symlink references, checks the raw runner receipt's job, command,
runner, capacity policy, mode, timeout and resources. It recomputes the original
runner `request_sha256` using that historical producer’s default-spaced
`json.dumps(spec, sort_keys=True)` bytes, rather than the new canonical
fingerprint. Success requires an explicit Boolean false `reconcile_required`,
successful exit and stopped children. It verifies all outputs, origin evidence and declared evidence bytes.
Coverage means the full declared command actually ran; planning output such as
`--plan` must never be substituted for the reviewed executable command.
This is trusted local custody, not a cryptographic attestation service or a
sandbox against a concurrently malicious evidence writer.

`aggregate(plan, results, policy, catalog, evidence_root)` returns a summary with
`candidate_sha256`, `plan_sha256`, `source_sha256`, `outputs_sha256`,
`required_profiles`, `results_sha256`, `accepted`, `missing`, `incomplete` and
`status` (`qualified` or `incomplete`). It rejects duplicate/unexpected checks
and source/profile/command/output mismatches. CLI exits 0 for qualified, 1 for
incomplete and 2 for rejected input/evidence. Accepted output order is the exact
candidate artifact order, as required by the common fingerprint contract.

The publisher calls
`validate_qualification(summary, plan, results, policy, catalog, evidence_root)`
to recompute and require exact complete evidence rather than trust a success
label. Independent reviewer acceptance is a separate publisher check bound to
`source_sha256` and `outputs_sha256`; this aggregator cannot accept its author's
source or waive hosted contexts. `reusable_result(...)` only permits an exact
plan/check cache hit after revalidating all evidence/output bytes. It does not
relabel reuse as a fresh run or bypass a required provider context.

## Local verification and adoption boundary

Focused tests cover actual Git guards, candidate repairs, complete/partial and
uncertain outcomes, exact native runner resource declarations, byte-tampered
cache evidence, mismatched execution identities, duplicate checks, path escape,
profile downgrade, and CLI exit behavior. Run:

```sh
PYTHONPATH=src:tools/delivery /path/to/pinned/python -m unittest discover \
  -s tests/delivery -p test_release_qualification.py -v
```

Component evidence is synthetic and local. Root must obtain independent exact
source review and verify cross-component compatibility, coherent staging,
aggregate admission, real backend receipts and final publisher gates before
adopting this source. CIX, production, Actions and installed runtime changes
remain held. A local component commit is not parent UIF-120 completion.
