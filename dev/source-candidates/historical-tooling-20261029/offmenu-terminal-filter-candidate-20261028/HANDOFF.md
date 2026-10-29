# Explicit local terminal output filter — review candidate

Usable stdlib Python tool in this isolated directory; not installed, globally
activated, wired to any provider/production caller, or related to the held live
metrics deployment. No provider/model calls, package installation, service or
source-data/credential/session-store access occurred. The live deployment hold
was neither retried nor bypassed.

## Explicit invocation

```bash
python /home/user/src/offmenu-terminal-filter-candidate-20261028/terminal_filter.py saved ai-reuse-r2 --max-bytes 1536
```

This reads only the named, SHA-pinned, non-sensitive saved synthetic AI tooling
unittest log. It does not rerun it. `ai-reuse-r1` is the other named saved log.
Arbitrary filenames, stdin logs and arbitrary command arguments are not accepted.
Changed saved input fails closed until its source classification/hash is reviewed.

The only registered executable command is this tool's own focused tests:

```bash
python /home/user/src/offmenu-terminal-filter-candidate-20261028/terminal_filter.py run filter-tests --max-bytes 1536
```

This runs the source-reviewed argv tuple `sys.executable -m unittest discover -s
<this-directory> -p test_terminal_filter.py -v` directly, shell=False, in this
directory. It does not run the prior accepted product/dataset/provider checks.
No positional argv extension or shell interpolation is possible. New named
commands/inputs require explicit source review; do not add arbitrary user commands
or private inputs. The focused tests contain synthetic subprocess fixtures only.
The tool itself captures no process environment, credentials or external data.

## Evidence and output contract

Every finalized invocation preserves a byte-exact original `.bin` and capture
receipt under an owned non-symlink 0700 artifacts directory; files become 0400
after finalization. SHA-256 and byte length are recorded. For a subprocess, these
are the exact observed combined stdout/stderr bytes, not a reconstruction of
independent stream ordering. No UTF-8 replacement, line stripping or redaction
is applied to the original. Partial captures remain private after tool failure,
without a fabricated finalized receipt. Existing artifacts are retained, including
the exploratory captures used during development.

Only a complete recognized verbose unittest-success grammar is compressible:
every test line must match, test count must agree, and the trailer must be OK.
The summary retains the trailer, count and exact omitted byte/record counts.
It never infers subprocess success from text: saved-log process status is null
and execution_outcome is not_observed. Captured child exit status is retained
numerically; the CLI returns the child's status, or 128+signal for signal death.
A nonzero child status prevents success-grammar compression even if text says OK.

Unknown lines, failure output, Unicode, binary bytes, terminal escapes, oversized
input and long lines use bounded raw head/tail chunks, base64 encoded with exact
byte offsets. Every omitted byte is explicitly counted and possible diagnostic
omission is flagged. There is no generic error-detection, redaction or security
claim. All error/failure bytes are preserved in the full original artifact;
a bounded summary can omit diagnostics and must not be used as full evidence.
Small failure/unknown outputs fit in full raw chunks. The tool never labels an
unknown line harmless or reports success because it shortened output.

JSON output includes original/receipt pointers, SHA, original length, raw child
status, cancellation state, execution outcome and summary_is_full_evidence=false.
Budgets are 1024..16384 bytes, default 1536. Metadata that cannot fit fails closed
rather than exceed the limit or lose artifact/status identifiers. Tool errors use
125 unless a known nonzero child/cancellation status must be preserved. A saved
mode CLI zero only indicates successful capture/summary, not test execution.

## Cancellation and cleanup

Commands are explicit noninteractive local profiles (stdin is DEVNULL). Each gets
its own process group. Ctrl-C and scoped SIGTERM cancellation are forwarded to the
group, with bounded INT/TERM/KILL escalation and leader reaping. The parent's prior
SIGTERM handler is restored; no shell hook or permanent handler is installed.
Cancellation returns 130/143 even if the child catches the signal and exits zero;
its actual return code and cancellation signal stay in the private receipt.
Background members of the managed group are killed when the leader exits, before
finalization. Commands which deliberately detach into another session are outside
these reviewed profiles; this tool does not claim containment of arbitrary trees.
SIGKILL of the wrapper cannot guarantee cleanup or a final receipt. If normal
cleanup cannot be confirmed, the capture fails closed. This is a POSIX/main-thread
CLI tool, not a Windows runner or a general process supervision service.

## Actual illustration

See `ai-reuse-r1.summary.json`, `ai-reuse-r2.summary.json` and `measurements.json`.
The final-source illustrations read existing non-sensitive logs, without rerunning
them. Emitted sizes include the complete JSON metadata and artifact pointers:

| Saved log | Original bytes | Summary bytes | Reduction |
| --- | ---: | ---: | ---: |
| ai-reuse-r1 | 1608 | 783 | 825 bytes (51.31%) |
| ai-reuse-r2 | 2591 | 785 | 1806 bytes (69.70%) |

For R2 the actual summary says mode=strict_unittest_ok,
recognized_test_records=15, omitted_bytes=2565, omitted_records=18,
retained_text="Ran 15 tests in 1.446s\nOK\n", process_returncode=null,
execution_outcome=not_observed and summary_is_full_evidence=false. Its full
artifact pointer/hash are in the delivered JSON. Omissions from original text
and net emitted reduction differ because the summary adds evidence metadata.
These figures are terminal-byte reduction for these two samples, not token,
provider-latency, production, storage or general workload savings. Exact local
wall times are recorded in measurements.json; no speedup comparison is claimed.

## Review and rollback

Nine focused deterministic tests passed; `focused-tests.log` is the recorded
result. Cases cover exact bytes/private modes, omission accounting, unknown
messages, long lines, Unicode/binary data, nonzero exit and unchanged argv,
public-entry status propagation, rejected arbitrary profiles/changed inputs,
pre-launch cancellation, and real SIGINT/SIGTERM cancellation with synthetic child cleanup. No prior
accepted checks were repeated. Inspect source, tests and example receipts for
independent review. FILE-INVENTORY.json freezes all files except itself/bytecode.

Adoption is only an explicit invocation of a reviewed named profile. Rollback is
to stop invoking this standalone tool; retain originals/receipts for evidence.
No environment, caller, service or production rollback is required. No global
activation is proposed or authorized by this handoff.
