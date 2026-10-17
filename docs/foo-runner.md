# OffMenu foo runner setup and bounded job queue

This package lets the repository owner install a dedicated GitHub Actions runner on foo, then submit small named command batches through GitHub. The setup script defaults to a read-only preflight. Nothing here has been installed, registered, or run on foo during preparation.

## Scope and security boundary

- Repository: private, personally owned `maldous/offmenu` (repository ID `1416253963`), default branch `main`.
- Runtime account: `offmenu-runner`, with no extra groups, sudo, Docker socket, personal SSH keys, GitHub CLI login, cloud credentials, or deployment credentials.
- The service has read-only access to one explicitly selected dataset directory, exposed as `/srv/offmenu-refresh/cache`. It writes its own runner state, checkout, temporary files, and `/srv/offmenu-refresh/outputs`.
- Initial profiles: `readiness`, `inventory`, `offline-replay`, and the consolidated `smoke` batch. No arbitrary shell command field, network acquisition, deployment, schedule, or pull-request trigger.
- Registration creates persistent access. Any trusted writer who can change this repository's workflows could run code as this account. Labels, actor checks, pinned code, and manifest schemas reduce mistakes in this queue; they do not impose a repository-wide workflow allowlist. The user-owned repository cannot rely on organization runner-group policies.
- The systemd sandbox hides ordinary home directories and constrains filesystem writes. It is not a VM or a network isolation boundary. World-readable host files and reachable local/network services remain relevant risks. Do not use this host arrangement if such services expose credentials or privileged operations to untrusted local users.

GitHub's [runner setup documentation](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners) and [security guidance](https://docs.github.com/en/actions/reference/security/secure-use) explain these trust assumptions. [Runner groups](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/manage-access) apply to organization-level runners.

## 1. Check the host from your normal account

Check out the reviewed setup branch/commit on foo. Inspect the scripts before running them.

```sh
bash scripts/setup-foo-runner.sh
python3 -B -m unittest discover -s tests -p test_foo_runner.py -v
```

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

The script chooses the architecture from the actual host, downloads from `github.com/actions/runner`, and verifies the entire archive before extracting it. Pinned initial release: [v2.338.0](https://github.com/actions/runner/releases/tag/v2.338.0), verified against official release-asset digests on 2026-10-17:

| Architecture | Official archive | SHA-256 |
|---|---|---|
| x86-64 | actions-runner-linux-x64-2.338.0.tar.gz | `af4b794c1bc41d73d40535e3fe092a39f9679cd8d965954c2aca25a05ca41d32` |
| ARM64 | actions-runner-linux-arm64-2.338.0.tar.gz | `628b4a7258487b80c1d3c221095a7ded349f5ae0175fd3dfab708d07428f041b` |

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
