# One owner-operated selected-data batch

Use the exact reviewed checkout commit supplied with the release. Keep the GitHub
runner queue quiet until the resulting grant receipt has been reviewed. In a normal
owner terminal, run this one command with the supplied full 40-character commit:

```sh
/usr/bin/python3 -I -B scripts/run-selected-dataset-grant.py --expected-commit FULL_REVIEWED_COMMIT
```

This is a single self-diagnosing batch; no separate manual pre-auth probe is needed.
It records runtime/terminal availability, fixed tool availability, checkout evidence,
independent projector inventory, owner authentication, grant outcome and publication
outcome. A later failure does not discard completed evidence. It performs no automatic
checkout, pull, package install or helper retry.

## Tool and authorization gates

Normal-user execution and isolated Python remain required. Tool preflight checks
`/usr/bin/git`, `/usr/bin/python3`, `/usr/bin/sudo`, then the two supported GitHub CLI
locations in deterministic order: `/usr/bin/gh`, `/usr/local/bin/gh`. The first safe
candidate is selected; arbitrary `PATH` entries are never searched. A gh executable
and every directory in its full ancestry must be root-owned, not group/other-writable
and not a symlink. The file must be a regular executable, singly linked, and have no
setuid/setgid bits. These checks repeat immediately before each credential-bearing
child. An unsafe or absent candidate is reported without running it.

The wrapper reuses existing GitHub CLI authentication, including existing
`GH_TOKEN`/`GITHUB_TOKEN` and supported gh config overrides, only in those verified gh
children. It fixes the host to `github.com` and requires both login `maldous` and
immutable user ID `6347545`. Tokens/config overrides never reach sudo, the projector,
git or other children. Custom host/repository/Git environment overrides are ignored.
No credentials or raw exception messages are put in diagnostics or reports. Raw gh
stdout/stderr is bounded in memory and never saved to disk.

Before privilege, Git HEAD must equal the supplied commit. The wrapper and three
dependencies must equal that exact Git tree; each dependency must also match its
unchanged fixed SHA-256. Only after this checkout validation, an independent
unprivileged child inventories six fixed historical projector Python files. It runs
even if gh is missing, owner authentication fails, or sudo is unavailable. An invalid
checkout never runs the inventory. Missing/invalid projector evidence does not
block an otherwise authorized grant. Ctrl-C during the inventory cancels the batch
before owner authentication or sudo. The inventory checks known hashes and reports
bounded identifier-level static syntax for exact matches, never executing or
uploading the six source bodies. Limits are 90 seconds wall-clock, 60 seconds CPU
and 256 MiB address space. If standard Python is unavailable, this is explicitly
reported without inventing an inventory result.

The grant still requires verified owner authentication, an interactive terminal and
successful `/usr/bin/sudo -v`. The password prompt remains on the owner's terminal.
The root invocation is `/usr/bin/sudo -n /usr/bin/python3 -I -B -c` with the unchanged
fixed loader, exact helper filename/digest, and `--apply`. The loader bounds the file
read, checks the hash and executes those same bytes. The helper independently pins
and executes only its already-verified inspector dependency. Source access,
permission checks, snapshot limits, rollback and dedicated service scope remain as
described in [selected-dataset-access.md](selected-dataset-access.md).

## Reports and terminal diagnosis

Every invocation attempts to save `sanitized-report.json` in a new mode-0700 private
`/tmp/offmenu-owner-batch-*` directory, including invalid arguments, runtime failures,
checkout failures and pre-auth failures. It saves before privilege, before publication,
and again with the final publication outcome. JSON updates are atomic, mode 0600,
and bounded to 32 KiB. The terminal prints the private directory; that path is never
included in the GitHub receipt. If local storage cannot be created or written, the
terminal explicitly says `localReportStatus: write-failed`, includes a fixed diagnosis
and the sanitized report itself. Failure to save the pre-grant snapshot blocks the
grant. A previously saved report can be stale after a final write failure; use the
terminal's publication and grant outcomes in that case.

Terminal JSON includes:

- `phase`, fixed `errorCode`, numeric `errno` or null, and fixed `recovery` guidance
- `grantStatus`, `helperExitCode`, `helperReportStatus`, `helperErrorCode`
- `projectorStatus` and any separate projector diagnosis
- `publication`, plus a separate publication diagnosis when necessary
- `localReportStatus`, plus a separate local-storage diagnosis when necessary
- runtime/interactive-terminal checks and fixed tool/candidate statuses
- the preflight `batchBlocker` where applicable

Unknown exception text is never copied into these fields. A reported blocked helper
has `errorCode: grant-blocked` and its sanitized helper error, rather than a misleading
success-like terminal summary. A non-TTY runtime is visible even if authentication
fails first. Read the saved JSON for complete independent inventory/grant evidence.

Grant/projector stdout/stderr stays local, captured incrementally into mode-0600
files with at most 64 KiB per stream (less for the projector). The grant receipt must
be at most 16 KiB and pass the closed schema, fixed enums, numeric bounds and nested
inspector sanitizer. The projector receipt passes its separate fixed schema and
12 KiB bound. Invalid evidence is `unverified`; arbitrary output is never posted.

The pinned inspector's national file-list matches include the bounded
`pinned-receipt-content` basis and schema/ambiguity reason enums in nested snapshot
evidence. File labels and URLs are never exported. The wrapper's helper/inspector
pins move together; the projector pin and all authentication, publication, and
service boundaries remain unchanged. The helper's content-addressed private
inspector leaf allows retry after the old unsupported-schema stage without
overwriting its earlier private inspector file.

## Single publication and honest outcomes

After owner authentication, the wrapper prepares one sanitized comment on
`https://github.com/maldous/offmenu`, PR 30. Its snapshot has:

- schemaVersion: `offmenu-owner-dataset-batch/1`
- reportKind: `owner-dataset-grant-batch`; batchVersion: 1
- expected commit and fixed dependency hashes
- independently sanitized grant/projector evidence and fixed diagnoses

No comment is attempted without verified owner authentication. A failure preparing
its local body or a proven failure to launch gh is `not-attempted`. Once gh launches,
a failed/ambiguous response or timeout is `uncertain-no-retry`: a comment may already
exist remotely. The final local JSON records that outcome; the posted snapshot
necessarily predates its own publication result. No comment/helper retry is automatic.

The actual helper exit is preserved even if publication or final local persistence
fails. Pre-helper blockers use 2; a launched helper with unknown outcome uses 124;
signals use 128 plus the signal number. A malformed receipt with real exit 0 stays
exit 0 and `unverified`, requiring review before any retry. Consequently exit 0 alone
never establishes a verified grant. A proven process-launch failure is `not-started`,
while post-launch capture failure stays `unknown-outcome`.

The root loader retains its 15-minute interrupt timer for controlled rollback. The
wrapper waits up to 20 minutes. If the outcome remains unknown, it never claims to
kill the root child, restore service, or authorize the job queue. Keep the queue quiet
and review the local evidence before retrying. When publication alone is uncertain,
check PR 30 before any later publication attempt.

## Cloud fixture checks

```sh
python3 -B -m unittest discover -s tests
```

Fixtures replace owner authentication, sudo, GitHub publication and real host grants.
Only small unprivileged subprocesses test bounded capture and the verified-byte
loader. Tests do not establish host readiness or authorize a live grant.

## Service evidence from the pinned helper

The helper pin covers bounded post-start readiness and sanitized diagnostic
sampling. The owner wrapper independently validates serviceDiagnostics against
fixed property names, boolean shapes, state/result enums, path hashes and numeric
ranges. Arbitrary fields, paths, command output, exception strings and oversized
records are rejected. The existing 16 KiB helper-report and 32 KiB batch-report
limits remain in force.

The receipt distinguishes the first grant failure from the rollback result. It
also records whether a failure sample is fresh, last-observed or unavailable, and
keeps a failed diagnostic-read code separately. A restored original service does
not imply the dataset view was applied or verified. The helper's 20-second
post-start convergence budget does not retry the batch or start the service a
second time; rollback retains its existing separately scoped start when needed.
Operator queue, replay and downstream admission gates remain unchanged.
