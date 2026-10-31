# Coding child confinement: source-only operator handoff

UIF-106, base `6bda06295cb0f0e11ddc6c9311306587b769f537` (PR187).
This candidate is **not deployed**. Runtime adoption belongs to the sole publisher
AFTER independent exact-source review and actual service-context proof. No App or
key exists according to the retained owner evidence. App creation must wait for
true coder confinement AND native-auth/service-context proof. Compatibility is
**COMPATIBILITY_UNPROVEN**; native authentication interoperability is **UNOBSERVED**.
Requested native model/effort are `gpt-6.1-sol`/`medium`; observed model is unknown.

The exact private approval/context record is
`/home/user/src/offmenu/.delivery/stokowski/uif119-coding-child-confinement-20261031/launch-context-evidence.json`.
It records host UID/GID 1000, supplementary groups
`4,24,27,30,46,101,126,130,982,994,996,1000,1001,64045`, NNP 0,
effective/inheritable/permitted/ambient capabilities 0 and bounding set
`000001ffffffffff`. Publisher UID 984/GID 976 exists; four reported nonsecret
DAC denials are prior evidence, not this candidate's runtime proof. The retained
namespace probe failed; it was not retried and no alternate namespace route is
part of this proposal. An environment allowlist and workspace-write/approval-never
alone cannot prevent sudo or daemon IPC.

The [kernel NNP contract](https://docs.kernel.org/userspace-api/no_new_privs.html)
prevents set-ID/file-capability elevation across exec, but does not prevent
privileged socket IPC. Clearing supplementary groups requires
[CAP_SETGID](https://man7.org/linux/man-pages/man2/setgroups.2.html); UID 1000 cannot
clear these host groups itself. The
[seccomp contract](https://man7.org/linux/man-pages/man2/seccomp.2.html)
provides inherited syscall filtering, architecture checks and scalar argument
inspection. These are the primary semantics used here; pointer/string inspection
is not attempted.

## Proposed fixed installed binding

The root-controlled control plane must be separate from writable source. Proposed
targets (no installation, grant or policy read was performed here):

| Target | Proposed owner/mode | Source or content |
| --- | --- | --- |
| `/usr/local/libexec/offmenu-coding-dropper` | root:root 0755 | `deploy/stokowski/offmenu-coding-dropper.sh` |
| `/usr/local/libexec/offmenu-coding-guard` | root:root 0755, never SUID | Compiled `tools/delivery/coding_child_guard.c` |
| `/etc/offmenu/coding-confinement.json` | root:root 0644, nonsecret | Exact schema and three executable hashes below |

Every parent must be root-owned, non-symlink and without group/world write.
The existing fixed native binary is
`/usr/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex`.
It and its parents must meet the same root-control checks. No source-tree
executable, Python module, user-selected program, UID or arbitrary command runs
in the root phase. Worker command is only `/usr/bin/sudo -n --` followed by the
fixed installed dropper and five constrained native arguments. No sudoers change
or new grant is included. Existing host passwordless sudo is unusable for
set-ID elevation after NNP, subject to actual service proof.

The fixed shell dropper only execs fixed `/usr/bin/setpriv` with UID/GID 1000,
`--clear-groups --bounding-set=-all --inh-caps=-all --ambient-caps=-all
--no-new-privs --reset-env`, followed by the fixed compiled guard and quoted args.
All untrusted input validation occurs AFTER that drop. The guard checks all real,
effective and saved IDs, empty groups, every capability set including ambient and
bounding, NNP 1, and rejects unknown kernel capability growth. It refuses socket
stdio and closes **all** descriptors >=3 through close_range, failing closed if
unavailable. No publisher or daemon descriptor may cross native exec.

Only canonical UID-1000-owned paths beneath
`/home/user/src/offmenu/.delivery/stokowski/` are accepted. Workspace is beneath a
`workspaces/` component. Output is `final-message.txt`, auth home is `codex-home-*`
(mode 0700), state is `codex-state`, all in the same `attempts/` directory.
`auth.json` must be a symlink to existing `/home/user/.codex/auth.json`.
Only link metadata is checked; auth bytes are never read or copied by this source.
The guard clears inherited environment, reconstructing fixed nonsecret
HOME/USER/LANG/PATH, CODEX_HOME/SQLITE path references, disabled tracing and Git
config count. No inherited App, Linear, agent, LD_* or PYTHONPATH survives.

Native argv is constructed in the guard: fixed exec/json/config flags,
`gpt-6.1-sol`, medium effort, approval never, and only workspace-write or read-only.
The helper validates the exact argv and root policy/hashes; no JSON path or
executable override interface exists. Every BINARY launch through worker
`supervise` (coding, native read-only review and qualification callers) uses this
binding. Finite Python fixtures keep the existing supervisor. Missing/invalid
policy returns a failed `confinement-prelaunch-refusal`, `child_started:false`,
`child_tree_gone:true`, unknown resolved model; admitted Pool resources are released
through the existing failure path, with immutable intent/receipt retained. It
never silently falls back to the host route or retries that immutable attempt.

The filter is Linux x86_64 only. It kills wrong architectures, tagged x32 and
untagged syscall numbers >=512. It denies socketpair, all io_uring entries,
ptrace, process_vm_readv/writev and pidfd_getfd. Socket creation permits only
AF_INET/AF_INET6; AF_UNIX, netlink and packet sockets are denied. With inherited
FDs closed, an AF_UNIX connection has no socket creation/import path. TCP connect
remains permitted. No pointer-string magic or silent filter relaxation is used.

This is not global isolation: same-UID host processes and writable files remain
shared, local TCP daemons could expose privileged routes, and kernel vulnerabilities
are outside this filter. UID 984 separates publisher DAC/process access from UID
1000; usernames and historical denials alone are insufficient proof. Parent
control-source custody, actual local TCP exposure, same-UID interference and
provider/DNS reachability require service-owner review. Native sandbox IPC may
require AF_UNIX/socketpair; if so this candidate stays held. Do not weaken the
filter to manufacture a compatibility pass.

## Build and policy proposal; no automatic installation

Build only reviewed source with the existing compiler, for example the non-root
build recipe `cc -Wall -Wextra -Werror -O2 -DNATIVE_SHA256='"REVIEWED_NATIVE_SHA256"'
 tools/delivery/coding_child_guard.c -o PRIVATE_BUILD_PATH` (one command, replace
placeholders after review). The native digest must match the root-controlled
binary and the policy. No libseccomp package or runtime installation is needed.
An unconfigured build deliberately cannot exec native Codex.

Proposed nonsecret policy shape (placeholders are not valid activation values):

```json
{
  "schema": "coding-confinement-v1",
  "sha256": {
    "/usr/local/libexec/offmenu-coding-dropper": "REVIEWED_DROPPER_SHA256",
    "/usr/local/libexec/offmenu-coding-guard": "REVIEWED_COMPILED_GUARD_SHA256",
    "/usr/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex": "REVIEWED_NATIVE_SHA256"
  }
}
```

Source-only build evidence on 2026-10-31, existing compiler
`cc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0`:

| Artifact | SHA256 |
| --- | --- |
| Guard source | `3a8f2d1403313f0148ce80f23f8aaa7e65a7c57a7049ad90a9ad28989cfd5fc5` |
| Dropper source | `64f8152a07d50cc2994f89f0956df2009aebc2394c25eeae4cb05fc3d0856646` |
| Unconfigured temporary compile, `-Wall -Wextra -Werror -O2` | `da44edbbca30fddcd1c98b704c62380c5b62570432916254a28dcd9a57d9db0b` |

The temporary compile is a test artifact, not an installable/pinned production
build. Source changes invalidate these hashes. The sole publisher must retain
exact reviewed source, configured build/native/policy hashes and actual installed
readback before adoption. Proposed reversible sequence: keep worker admission
held; retain existing service/source binding; independently review; build outside
root; have the sole publisher install the fixed root-owned artifacts and nonsecret
policy with verified parents; then conduct separately authorized service-context
qualification. No source-tree program may run as root. No executable installer,
new service, restart, key or sudoers change is supplied. Rollback proposal: stop
new admission through the existing owner, reconcile active trees, restore the
retained reviewed source/binding and disable candidate policy; keep the unsafe
host coding route and App creation held. Removing policy must fail closed.
Leave offmenu-runner, CIX and historical units unchanged.

## Source proof and runtime hold

Focused tests compile under temporary directories and interpret the **actual
compiled** BPF offline. Mock descriptor syscalls prove socket-stdio rejection,
close_range arguments and close failure refusal. SHA256 vectors, exact argv,
root/symlink/hash/environment/path contracts and worker hook/Pool failure behavior
are tested without sudo/setpriv or model execution. Existing resource sampling,
affinity, memory/process/log limits, cancellation and cleanup remain in place.

The production compiled guard was invoked only in a proven unsafe nonroot tool
context and returned 126 before security mutation or exec. Exact selected context:
UID/GID real/effective/saved/fs all 1000; supplementary groups as reported in
`/proc/self/status`: eleven 65534 entries, 1000, then two 65534 entries;
NNP 1; CapInh/Prm/Eff/Bnd/Amb all zero; Seccomp 2. `id` reports the distinct groups
1000 and 65534. This is the ordinary remapped tool jail, **not** publisher or host
native service proof. No filter, groups, capabilities or security settings were
changed by the production guard test.

Activation remains held until independent source review and nonsecret evidence
from the exact adopted service/workspace/output/auth context establishes: all
IDs/groups/capabilities/NNP and filter inheritance; set-ID/file-cap refusal;
privileged AF_UNIX and inherited-FD denial; publisher file/process denial under
UID 984; reviewed local TCP exposure; Codex initialization and existing native
authentication without copying credentials; actual provider/DNS compatibility;
resource/cancellation/tree cleanup. Bind exact source/build/policy/service hashes
and requested versus observed model separately. Do not infer runtime success from
these tests, an existing account, a merge, a mock filter or the four prior DAC
checks. No namespace execution was attempted. No App access/key, credential read,
new grant or live privilege change is authorized by this source handoff.

Final local verification: 11 confinement contracts and 23 affected worker
regressions passed using `/home/user/src/offmenu/.venv-delivery/bin/python` with
`PYTHONPATH=src`; `offmenu.delivery discover`, `offmenu.delivery check`,
`scripts/check_final_layout.py` and `git diff --check` passed. Check/layout examined
2185 paths with zero violations. No full regression suite or bootstrap ran.
Repository HEAD remains the base above; no commit/branch/push/merge was performed.
Changed source is limited to the eight manifest paths: `stokowski_worker.py`,
`coding_child_launch.py`, `coding_child_guard.c` under `tools/delivery/`, the fixed
`deploy/stokowski/offmenu-coding-dropper.sh`,
`tests/delivery/test_coding_child_confinement.py`,
`tests/delivery/test_stokowski_worker_regressions.py`, this handoff, and
`tools/delivery/README.md`. No local validation failures remain. Next step is
independent exact-source review; all runtime boundaries listed above remain
unobserved and adoption/App creation remain held.
