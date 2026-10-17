# OffMenu foo runner setup and bounded job queue

This package lets the repository owner install a dedicated GitHub Actions runner on foo, then submit small named command batches through GitHub. The setup script defaults to a read-only preflight. Nothing here has been installed, registered, or run on foo during preparation.

## Scope and security boundary

- Repository: private, personally owned `maldous/offmenu` (repository ID `1416253963`), default branch `main`.
- Runtime account: `offmenu-runner`, with no extra groups, sudo, Docker socket, personal SSH keys, GitHub CLI login, cloud credentials, or deployment credentials.
- The service has read-only access to one explicitly selected dataset directory, exposed as `/srv/offmenu-refresh/cache`. It writes its own runner state, checkout, temporary files, and `/srv/offmenu-refresh/outputs`.
- Profiles: `readiness`, `inventory`, `offline-replay`, the consolidated `smoke` batch, and the reviewed `delivery-diagnostics` extension described below. No arbitrary shell command field, network acquisition, deployment, schedule, or pull-request trigger.
- Registration creates persistent access. Any trusted writer who can change this repository's workflows could run code as this account. Labels, actor checks, pinned code, and manifest schemas reduce mistakes in this queue; they do not impose a repository-wide workflow allowlist. The user-owned repository cannot rely on organization runner-group policies.
- The systemd sandbox hides ordinary home directories and constrains filesystem writes. It is not a VM or a network isolation boundary. World-readable host files and reachable local/network services remain relevant risks. Do not use this host arrangement if such services expose credentials or privileged operations to untrusted local users.

GitHub's [runner setup documentation](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners) and [security guidance](https://docs.github.com/en/actions/reference/security/secure-use) explain these trust assumptions. [Runner groups](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/manage-access) apply to organization-level runners.

## One-command initial bootstrap (recommended)

Run from the reviewed checkout as your ordinary account in an interactive terminal:

```sh
python3 -B scripts/bootstrap-foo-runner.py --apply --publish --issue 30 \
  --accept-github-agreement \
  --expected-head-sha 784ba35b000b54a7443094133e22cfc3f7ca5301 \
  --expected-run-id 39043749665 \
  --expected-job-id foo-bootstrap-smoke-20261017-001
```

This runs all three diagnostics, validates the exact queued smoke request, requests local sudo when needed, creates the dedicated account/directories/service, downloads and checksum-verifies the repository-offered runner v2.337.0, registers only if needed, verifies effective systemd properties, starts the service without enabling it at boot, waits up to 20 minutes for that exact queued run, and posts one sanitized combined result to PR #30. Dependencies stop on failure, with completed stages and real command exit codes retained. Reruns reuse recognized installations and matching registration; conflicts fail closed without deleting or replacing unrelated state.

The `--accept-github-agreement` flag records your acceptance of the [GitHub Customer Agreement](https://github.com/customer-terms) before download/configuration. Registration uses GitHub's original interactive terminal prompt, without capturing its input or output. Obtain a **fresh** short-lived token in your own browser when prompted. Never reuse a token shared in chat, and never put one in command arguments or reports. Existing owner `GH_TOKEN`/`GITHUB_TOKEN` authentication is passed only to `gh` transport, never to admin commands, tests, or runner processes.

Until an actual dataset-only cache has been selected, the bootstrap creates `/srv/offmenu-bootstrap-input` as an empty root-owned 0755 directory. It refuses a pre-existing nonempty or unsafe path. The service exposes that empty directory read-only; the smoke job inventories it and replays repository fixtures. **Success establishes runner transport and fixture execution, not access to the real dataset cache.** A real cache can be configured later after reviewing its exact path. No source file permissions are broadened.

Omit `--apply` for diagnostics only. Omit `--publish` to keep results local. Raw diagnostic logs stay private and bounded locally; registration/sudo prompts are never logged. If publication is uncertain, inspect PR #30 before requesting another post. Read-only GitHub polling retries transient reads within the deadline; mutation and publication failures are never blindly retried. If interrupted after service start, it may remain running; the final report does not claim rollback. Stop it locally with `sudo systemctl stop offmenu-runner.service` if desired.

If a prior attempt completed registration but stopped at identity validation, rerun the same complete bootstrap from the corrected checkout. It reads GitHub's UTF-8 BOM-formatted settings safely, validates the same repository/name/work folder/numeric runner ID, reuses the matching registration without asking for another token, then continues to service verification and the queued smoke. A mismatch still stops; the report includes only allowlisted presence/type/match booleans, never settings values or credential files. Root-installed helpers remain unchanged by this parser correction.

The sections below document individual stages for inspection and troubleshooting. They are not extra commands required after the complete bootstrap.

## 1. Check the host from your normal account

Check out the reviewed setup branch/commit on foo. Inspect the scripts before running them.

```sh
python3 -B scripts/check-foo-setup.py --publish --issue 30
```

This single command runs preflight, the runner setup/batch tests, and the refresh tests independently, then posts one combined sanitized report to OffMenu PR #30 through your existing `gh` login. A failing earlier check does not prevent the other test group from running. Every step includes its real exit code, duration, and status. Raw test output stays in a private local temporary directory, limited to 1 MiB per output stream per step; its location is printed only locally. The GitHub report contains no raw logs, credentials, source paths, or dataset contents. An uncertain publication is not retried automatically; inspect PR #30 before repeating `--publish`.

Omit `--publish` to keep the report entirely local. The command does not run admin steps, register a runner, log into GitHub, or create tokens. Existing `gh` login is required only for publication. The process exits nonzero if any check fails or publication is not verified. The older `setup-foo-runner.sh preflight` remains available for a quick standalone inspection.

The report identifies OS, CPU architecture, Python, systemd, required tools, and existing setup state. It does not claim to have verified the host alias, a running service, registration correctness, or dataset readability. `null` means a private directory was not visible from this account. No source contents, original source paths, environment variables, tokens, or credentials enter the report.

Supported by this script: Linux x86-64 or ARM64, CPython 3.10+, systemd 247+, curl, Git, and sha256sum. It checks a conservative list of GitHub-supported Linux distributions. An unsupported host stops before installation. Install missing system packages through the host's normal administration process; jobs never install them.

## 2. Review and run the explicit administrative plan

Supply the actual canonical, dataset-only cache directory. Do not select a whole home directory, repository containing private configuration, or a directory with credentials. The selected source is never modified by this setup.

```sh
bash scripts/setup-foo-runner.sh admin-plan \
  --cache-root /actual/canonical/dataset-cache > /tmp/offmenu-runner-admin-plan.sh
less /tmp/offmenu-runner-admin-plan.sh
bash /tmp/offmenu-runner-admin-plan.sh
```

The generated plan creates only the dedicated account, dedicated directories, two root-owned setup helpers, and the named systemd service. It refuses existing conflicting paths, symlinks, unexpected ownership or modes, nonempty cache-view placeholders, unrelated helper files, and differing installed helpers/service instead of replacing them. Existing runner-home/output directories must already be 0700; data-root/cache-view directories must be 0755. Review any conflict manually; do not delete an existing runner to retry. Review the generated plan again if the checkout changes.

The account must already be able to traverse/read the selected source through ordinary permissions or a narrowly scoped dataset-only grant. The plan checks top-level readability but does not recursively grant permissions. If it fails, stop and decide how to expose only the dataset. Do not add the runner to your personal groups, copy your credentials, or broadly relax home-directory permissions. A root-managed dataset copy or narrowly scoped bind/ACL arrangement may be appropriate after inspecting the real host.

The plan installs the service but neither starts it nor enables it at boot. The service uses the runner's required `runsvc.sh` entry point. Its sandbox is specific to this service; it makes no firewall, SSH, VPN, or global OS security changes.

## 3. Download and verify the runner as the dedicated account

```sh
sudo -u offmenu-runner -H env -i \
  HOME=/srv/offmenu-runner PATH=/usr/bin:/bin \
  /usr/bin/python3 -B /usr/local/lib/offmenu-runner/runner_host_setup.py install
```

The script chooses the architecture from the actual host, downloads from `github.com/actions/runner`, and verifies the entire archive before extracting it. It copies the verified `bin/runsvc.sh` into the runner root as the dedicated account, matching the official service layout without invoking privileged `svc.sh` or enabling boot. Pinned initial release: [v2.337.0](https://github.com/actions/runner/releases/tag/v2.337.0), verified against official release-asset digests on 2026-10-17:

| Architecture | Official archive | SHA-256 |
|---|---|---|
| x86-64 | actions-runner-linux-x64-2.337.0.tar.gz | `70920811a4f8ad4328818682bca5c6469c1c942fab52448868071d0063816613` |
| ARM64 | actions-runner-linux-arm64-2.337.0.tar.gz | `9b1dc70626422526e3c94767cf024896beb15da5342a3f4819bf2feac13e0393` |

An identical recognized installation is left in place. A partial or unrecognized installation is not destroyed or overwritten. Upstream runner auto-updates remain enabled; rerunning this installer never downgrades an auto-updated installation. If installation happens substantially later, review GitHub's then-current supported runner release and its exact official checksum before updating these pins.

If the official runner reports missing system libraries later, review and install only those prerequisites as administrator. Do not add runtime sudo. The script does not run `installdependencies.sh` automatically.

## 4. Register locally, without sharing the token

Open the repository's [new-runner settings](https://github.com/maldous/offmenu/settings/actions/runners/new) in your own authenticated browser. Choose Linux and the verified architecture. Keep its short-lived registration token local.

```sh
sudo -u offmenu-runner -H env -i \
  HOME=/srv/offmenu-runner PATH=/usr/bin:/bin \
  /usr/bin/python3 -B /usr/local/lib/offmenu-runner/runner_host_setup.py register
```

The official runner prompts for its registration token in your local terminal. The wrapper neither requests, generates, receives, nor prints the token. Do not put it in shell history, a command-line argument, chat, an issue, the repository, or the diagnostic report. Do not use a personal access token. Credentials created by registration stay under the dedicated runner directory. Your normal account's existing GitHub CLI credentials are not copied to it.

If a registration already exists, the script leaves it alone and asks you to check its repository/name in GitHub. Expected name: `foo-offmenu`; custom label: `offmenu-foo`. Default `self-hosted`, Linux, and architecture labels remain present. Registration does not start the listener.

## 5. Verify the service, then start explicitly

```sh
sudo systemd-analyze verify /etc/systemd/system/offmenu-runner.service
sudo systemctl start offmenu-runner.service
systemctl is-active offmenu-runner.service
systemctl show offmenu-runner.service \
  -p User -p Group -p NoNewPrivileges -p ProtectSystem -p ProtectHome \
  -p BindReadOnlyPaths -p ReadWritePaths -p PrivateTmp
```

Check GitHub's runner page for `foo-offmenu` becoming idle. Inspect service errors locally if it does not. Do not upload `journalctl` output, runner `_diag` logs, `.runner`, `.credentials*`, shell history, or the entire runner directory. The script's preflight alone does not prove the sandbox is effective; the actual service and first job must be checked on foo.

Leave the service unenabled at boot for the initial pilot. If continuous restart after reboot is desired, the repository owner can explicitly run `sudo systemctl enable offmenu-runner.service` after verifying it. To stop accepting work, use `sudo systemctl stop offmenu-runner.service`. Stopping the service does not revoke the stored GitHub registration. Remove the runner through GitHub's documented removal flow when decommissioning; do not post its removal token anywhere.

GitHub documents [service configuration](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/configure-the-application) and [outbound HTTPS/runner update requirements](https://docs.github.com/en/actions/reference/runners/self-hosted-runners). No inbound listener/firewall opening is required for this design.

## 6. Activate reviewed code and the GitHub submission route

The workflow is deliberately inactive until `TRUSTED_CODE_SHA` is replaced with the full immutable commit SHA containing the independently reviewed refresh module, fixtures, dispatcher, and setup tests. Publishing the execution code and then pinning that earlier commit in a later workflow commit avoids a self-referential commit hash. Do not pin the workflow's own mutable branch tip.

Refresh base prepared for this work: `78378c174bb7ad68b6f5e6492194cb54ddd89ba6`. It does not yet contain this dispatcher, so it is not by itself the activation SHA.

The repository owner must approve publication/activation of the reviewed workflow. No merge to `main` or creation of the live control branch is implicit in preparing these files.

For the initial manual smoke, the workflow must exist on default branch `main`; GitHub requires that for manual dispatch. Then, from your normal account's existing GitHub CLI login:

```sh
gh workflow run foo-runner.yml --repo maldous/offmenu --ref main -f profile=smoke
gh run list --repo maldous/offmenu --workflow foo-runner.yml --limit 5
gh run watch --repo maldous/offmenu RUN_ID
```

The [manual-dispatch documentation](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow) describes the equivalent Actions UI flow. A feature-branch workflow alone is not enough for this manual path.

For subsequent assistant-submitted batches, create the dedicated branch `offmenu-runner-jobs` with the exact reviewed workflow. The GitHub connector can create/update `.github/offmenu-runner/request.json` there. That narrowly filtered push is the supported submission mechanism; the current connector has no direct workflow-dispatch tool. It does not require a manual copy/paste per job.

```json
{"schemaVersion":1,"jobId":"foo-smoke-20261017-001","profile":"smoke"}
```

Only these three keys are accepted. Use a new 8–64 character lowercase letter/digit/hyphen job ID for a new request. Updating the example file does nothing: the live path is specifically `request.json`. Each push reads its own immutable commit, so a newer request does not replace an older job's input.

The workflow currently permits only verified owner actor ID `6347545`. A connector push may use a different GitHub App actor. The first submission must be checked through the run API, and any different actual actor ID reviewed before adding it. A claimed commit author is not an authenticated actor. Unknown actors fail closed. Do not broaden the predicate to every contributor to make a skipped run work.

There is no shared GitHub concurrency group that could discard an older pending job. Submit one compatible batch and wait for its receipt before the next. A single registered runner processes jobs serially; a kernel lock adds protection against concurrent manual coordinators. IDs are protected by durable receipts: the same ID/profile/code returns its existing result, and the same ID with different contents is rejected. A new ID is needed to intentionally retry a completed failed batch. Interrupted batches can retry the same ID and resume a matching incomplete refresh checkpoint.

## Batch behavior and reports

`smoke` runs readiness, a bounded metadata-only inventory, focused refresh tests, fixture-only offline replay, and a second replay that must prove `verified-no-op`. Inventory failure does not suppress independent tests; failed prerequisites skip dependent replay. Mutating replay stages are serial. Each step reports status, exit code, duration, dependency/skipping reason, and bounded non-content evidence. Timeout, cancellation, output-limit, failure, and skipped states are distinct. Overall failure cannot be hidden by a later successful command.

Each child has a 240-second deadline and at most 1 MiB captured stdout plus 1 MiB stderr before termination. Raw stdout/stderr are never uploaded by the dispatcher. Only allowlisted numeric/boolean inventory fields, replay status, output byte counts, and output digests appear. The complete report is limited to 32 KiB. The service has a 3 GiB memory/2-CPU/256-task ceiling; the refresh worker separately enforces its tighter bounds. System logs and machine-wide disk usage are not covered by a quota, so monitor available space and retain only needed output receipts/releases locally.

Results appear once as `OFFMENU_JOB_REPORT {...}` in the workflow job log and in its step summary. This read-only execution job does not commit, comment, upload the dataset, or obtain a write token. The connected GitHub tools can list runs/jobs and retrieve those logs; correlate the request commit, real run ID, job ID, trusted code SHA, and final conclusion before claiming success. If setup/checkout fails before dispatch, there may be no receipt; treat the run failure as a blocker rather than inventing a result. Run retention limits apply to GitHub logs.

For one optional setup preflight comment after local setup, use your normal account and an explicitly chosen existing issue or PR:

```sh
bash scripts/setup-foo-runner.sh publish-report --issue EXISTING_ISSUE_OR_PR_NUMBER
```

This uses your existing `gh` login only. It creates a fresh fixed-field report rather than accepting an arbitrary file, and posts only to `maldous/offmenu`. It does not authenticate, create tokens, grant access, or copy credentials. Run it once after the compatible setup/diagnostic steps; do not publish one comment per command.

## Preparation validation and remaining host checks

The package's unit tests cover default read-only operation, exact pins, safe extraction, conflicting-install preservation, interactive-only registration, scrubbed environments, schema/injection rejection, bounded profiles, dependency behavior, exit/timeout/cancel reporting, receipt replay protection, and kernel-lock release. Synthetic local integration ran the real refresh tests and the complete five-step smoke batch successfully, including idempotent replay. These are preparation checks, not evidence of a working foo runner.

Remaining verification: actual OS/architecture/dependencies and cache permissions; dedicated account/service sandbox; local registration and idle runner; published trusted SHA and workflow; actual connector actor; real first-batch report and conclusion. No live foo data, runner registration, GitHub workflow execution, or deployment was used in the preparation tests.

## Delivery diagnostics extension (reviewed execution code required)

The existing transport is proven by the completed [smoke run 39043749665](https://github.com/maldous/offmenu/actions/runs/39043749665), request commit `784ba35b000b54a7443094133e22cfc3f7ca5301`, execution SHA `5722ca925e0c8543a8dc58f40d94e7f1768f475b`, job `foo-bootstrap-smoke-20261017-001`, and runner ID 21. The preserved sanitized receipt is `tests/fixtures/foo-runner/prior-smoke-receipt.json`. Its inventory explicitly did not establish source coverage or asset hashes. This result does not prove access to the real Norway or CIQUAL assets.

The new allowlisted `delivery-diagnostics` profile adds a substantial, restartable batch while retaining the existing exact three-field request schema. It runs:

1. Python/runtime readiness.
2. Bounded cache inventory.
3. Ledger structural-audit tests, followed by the pinned ledger audit.
4. Selected-data metadata tests, followed by the fixed Norway/CIQUAL metadata inspector.
5. Existing refresh tests, fixture-only offline replay, then replay idempotency.

At most two child processes run concurrently. Ledger, dataset metadata and fixture-replay branches are independent: unavailable dataset files cannot suppress the ledger audit or fixture replay. Failed tests suppress only their dependent operation. The two fixture replay stages remain ordered. Each child retains the 240-second deadline and 1 MiB per-output-stream limit. A cancelled batch terminates active child process groups before releasing the inherited kernel lock. There is no arbitrary command, path, source revision, concurrency, timeout or download option in the request.

### Separate immutable evidence checkout

The workflow checks out only the following eight tracked files into sibling `ledger-source`, from commit `8c25c6d76088c958d17f7adc4a3c0af7aab5c298`:

- `docs/handover/2026-10-17/operational-ledger/authority.json`
- `docs/handover/2026-10-17/operational-ledger/base-initial-copy.json`
- `docs/handover/2026-10-17/operational-ledger/interim-obligation-index.json`
- `docs/handover/2026-10-17/operational-ledger/handover.json`
- `docs/handover/2026-10-17/operational-ledger/management-summary.json`
- `docs/handover/2026-10-17/operational-ledger/events.jsonl`
- `docs/handover/2026-10-17/morgan-batches-20261017/current-checkpoint.json`
- `docs/handover/2026-10-17/morgan-batches-20261017/transport-checkpoint-current.json`

This checkout alone has `continue-on-error` so an input checkout failure does not suppress unrelated diagnostics. The ledger audit independently verifies its fixed source revision and all file byte counts, SHA-256 and Git blob pins from `scripts/offmenu-ledger-source-pins.json`. Missing or invalid inputs fail the ledger step and overall job. The audit streams the complete 9,647,254-byte journal, reports JSON/object/newline structure and bounded top-level field/type counts, and compares the 5,269-record prefix and retained 5,271/5,105 lineage cuts. It does not reconstruct semantic state, current ownership, current worker capacity or sequence semantics.

### Selected-cache boundaries

The inspector uses only its reviewed six Norway/CIQUAL asset paths and five small receipt paths under the existing cache view. It hashes bounded source bytes and reads recognized receipt metadata, without parsing source bodies, downloading, copying data, changing permissions, reconfiguring mounts, restarting the service or refreshing a source. The currently mounted empty bootstrap cache is expected to produce missing-asset blockers. File metadata from that view must not be represented as dataset acceptance. The script and its documentation define the exact view layout; changing the real dataset mount requires a separately authorized, reviewed host operation.

### Receipt status and compatibility

Report schema version 1 retains all existing fields and statuses, and adds the terminal status `incomplete` for a diagnostics batch whose required metadata is unavailable but whose other stages passed. The metadata step is `blocked` only when its recognized report says `incomplete` and the child exits 2. A failed test, bad ledger pin, malformed report, timeout, output-limit or launch failure remains an overall failure. Both `failed` and `incomplete` return nonzero from the dispatcher. The report always states `corpusAcceptanceEstablished: false`; a successful metadata check is readiness for adapter design only.

Each new child report is rebound through its pinned strict-schema sanitizer and limited to 12 KiB. The complete consolidated receipt remains limited to 32 KiB. It contains no raw logs, source rows, workbook cells, credential values or private source paths. The JSON schemas allow only bounded static labels, typed counters/booleans and validated hashes (plus bounded ledger field names). Receipts are durable and scoped to the exact request and execution SHA. A completed `incomplete` receipt is returned without re-execution for the same job ID; use a new ID after changing the available inputs. An interrupted coordinator can retry the same ID.

### Publication and queue order

1. Publish the reviewed scripts, pins, tests and documentation as a new immutable execution commit. The source workflow deliberately retains the unconfigured execution-SHA placeholder.
2. In a later control-branch commit, copy the reviewed workflow and replace only `TRUSTED_CODE_SHA` with that published execution SHA. Preserve the repository/actor checks, exact action pin, read-only token and fixed evidence commit.
3. Update `.github/offmenu-runner/request.json` with one fresh ID and `profile: "delivery-diagnostics"` in that control commit or a subsequent commit. Read the exact immutable request and workflow run until the consolidated terminal receipt is available.

No runner registration, initial version pin, runtime user/privilege, boot setting, schedule or host service configuration changes are part of this extension.
