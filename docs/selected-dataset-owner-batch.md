# One owner-operated selected-data batch

Use the exact reviewed checkout commit supplied with the release. Keep the GitHub
runner queue quiet until the resulting grant receipt has been reviewed. In a normal
owner terminal, run this one command with the supplied full 40-character commit:

```sh
/usr/bin/python3 -I -B scripts/run-selected-dataset-grant.py --expected-commit FULL_REVIEWED_COMMIT
```

The wrapper requires normal-user execution, isolated Python, `/usr/bin/git`,
`/usr/bin/gh` and `/usr/bin/sudo`. It uses the owner's existing standard GitHub CLI
authentication, including existing `GH_TOKEN`/`GITHUB_TOKEN` or supported gh config
overrides only for fixed gh subprocesses, and checks both login `maldous` and immutable user ID `6347545`.
It does not create credentials or read credentials into a report. Custom GitHub
hosts, repository settings and Git configuration paths are ignored. Existing gh
auth/config environment values never reach sudo, the projector or other children,
and are never printed, captured or serialized into reports. No automatic checkout, pull, package install or helper retry
occurs. The sudo password prompt remains on the owner's terminal.

Before privilege, it verifies Git HEAD equals the supplied commit, the wrapper and
three dependency files equal that exact Git tree, and each dependency matches its
fixed SHA-256. The root invocation is `/usr/bin/sudo -n /usr/bin/python3 -I -B -c`
with a fixed loader, the exact helper filename/digest, and `--apply`. That loader
bounds the file read, checks the hash and executes those same bytes. The helper
independently pins and executes only its already-verified inspector dependency.
The source-only snapshot, permission checks, limits, rollback and dedicated service
scope are described in [selected-dataset-access.md](selected-dataset-access.md).

Before the grant, an independent unprivileged child inventories six fixed historical
projector Python files. It checks their known hashes and reports only bounded
identifier-level static syntax for exact matches. It never executes or uploads
those six source bodies. This child is capped at 90 seconds wall-clock, 60 seconds
CPU and 256 MiB address space. Missing projector files do not block the grant; a blocked
grant does not discard the projector result. There are no arbitrary source-path,
report-file, repository, PR or privilege options.

Grant/projector stdout/stderr is captured incrementally into a new private mode-0700
temporary directory, with mode-0600 files and at most 64 KiB retained per stream
(less for the projector). Raw grant/projector output remains local. Raw gh streams
are never saved to disk: the bounded owner response stays in memory until identity
validation, and comment output/errors are discarded after determining the outcome. The stdout
grant receipt must be at most 16 KiB and pass the closed schema, version, enums,
bounds and nested inspector sanitizer. The projector receipt passes its separate
fixed schema and 12 KiB bound. Invalid output is marked `unverified`; arbitrary
content and raw exception text are never posted.

The wrapper makes one comment attempt on `https://github.com/maldous/offmenu`,
PR 30, containing a sanitized JSON envelope no larger than 32 KiB:

- schemaVersion: `offmenu-owner-dataset-batch/1`
- reportKind: `owner-dataset-grant-batch`; batchVersion: 1
- expectedCommit and fixed artifact hashes
- grant: reported receipt, unverified, unknown-outcome, or not-started
- projector: independently reported receipt or unverified/not-started
- a fixed local blocker code when preflight cannot proceed

A failed or timed-out comment is `uncertain-no-retry`: it may already exist remotely.
The helper is never automatically repeated. The actual helper exit status is
preserved even if posting fails; pre-helper blockers use 2, an unknown timed-out
helper uses 124, and signal exits use 128 plus the signal number. Consequently,
exit 0 alone is insufficient to establish a verified grant: check the emitted
`grantStatus` and the posted receipt. No queued job is authorized by this wrapper.

The root loader sets a 15-minute interrupt timer, allowing the helper's controlled
rollback handler to run. The wrapper waits up to 20 minutes; if the result is still
unknown, it does not claim to kill the root child or restore the service. Keep the
queue quiet and review the private local records before any retry. The wrapper
prints their local directory to stderr but never adds that path to GitHub.

## Cloud fixture checks

```sh
python3 -B -m unittest discover -s tests -p test_selected_dataset_owner_batch.py
```

Tests replace authentication, sudo, GitHub and actual host grants with fixtures.
Only small unprivileged subprocesses test capture limits and the verified-byte
loader. These tests do not establish foo readiness or authorize a live grant.
