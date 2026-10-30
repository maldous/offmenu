# Credential staging operator procedure — source review candidate

This is finite source preparation for UIF-106, not privilege, transfer, credential,
service association or start approval. No operational commands in this document
were executed. Independent review of the exact helper/test/guide bytes and a new
exact action-time operator approval are required. Do not automatically associate,
start, retry or dispatch anything after staging.

The adopted original helper/test/guide remain unchanged in their private source
locations. The candidate source is `tools/delivery/stokowski_credential_stage.py`
on `feature/stokowski-credential-file-input`, base
`8453046747139ccd1d6e93e451bcedead3822780`. Its final SHA256 is
`c7b02333707c4791bf4a6ad3c8f4ed677e87aa8941afc60484df3a5eb8ec6c35`. The maintained test is
`tests/delivery/test_stokowski_credential_stage.py`. Review binds their exact output
hashes and this guide's hash from the private evidence packet; no mutable branch
name alone establishes acceptance.

## Storage and route conditions

Use only the native operator UID1000 route on the approved host. The sender reads
only its already exported `LINEAR_API_KEY` in its own process and clears its
inherited environment immediately after capture. It never parses shell files,
uses aliases, looks up credentials or prints a value. Export presence is unknown.
Missing/empty/oversize input refuses. Disable shell tracing and verbose input
before the future operation; never echo or expand the key in commands/history.

The fixed temporary source is
`/run/user/1000/offmenu-stokowski-credential-input/frame`. This is a NEW secret
storage exposure: the framed file contains the entire secret, not an encryption.
It is readable by the operator UID and root; same-UID process isolation is not
established. The sender exclusively creates a new 0700 operator-owned directory
and a new nofollow 0600 UID1000 regular single-link file. Preexisting objects,
including symlinks, are refused, never reused. No fallback directory is allowed.

Coordinator read-only metadata recorded `/run/user/1000` as existing UID1000,
0700, nonsymlink and an exact tmpfs mount. This is historical metadata, not an
action-time guarantee. Both modes re-open every fixed directory component using
nofollow directory descriptors and recheck owner/mode/path identity and exact
writable tmpfs mount/device semantics at action time. Unknown metadata or storage
semantics means HOLD. Mount changes and hostile same-UID concurrent writers cannot
be prevented by this helper; no operation is authorized in a hostile concurrent
namespace. The receiver checks exact bounds, regular type, UID1000, 0600, nlink1,
frame length/digest/trailer/EOF, stable inode metadata before/after reading and
file/directory path identity. Changed, replaced, oversize or malformed input refuses
before target creation. Maximum payload is 16 KiB; each process has a 15-second
deadline. The deadline is NOT a source-file lifetime or expiry.

## Exact future action, only after independent review and approval

A host administrator must bind the host, operator, reviewed hashes, absolute
candidate location, system interpreter and privileged command to the approval.
Verify `/run` is canonical root-owned runtime storage and the protected helper and
target directories do not already exist. Unknown runtime volatility means HOLD.
No policy, sudo logging, plugin or session capture settings may be disabled,
weakened or bypassed. This route supplies no secret to sudo stdin, environment or
arguments. Logging configuration is not changed by the route.

The following uses the final candidate workspace location. If source is published
elsewhere, review and bind that exact absolute source path and hash first. Check
code hashes only, never a secret file hash or secret contents. A trusted admin
must prepare an exclusive root-owned helper directory and copy verified code into
it as root:root0500; bind recorded dev/inode identities and recheck the protected
copy hash before capture. STOP on a collision, failure or uncertain effect. Do not
reuse an old directory or blindly rerun preparation. All sudo invocations,
including preparation and later cleanup, must start with an already cleared
environment and stdin `/dev/null`. The admin's separately approved noninteractive
privilege route must already be available; this guide does not grant it.

These are future commands for review, not an executable automation. Each must
succeed and be recorded before the next is considered:

```bash
set +x
set +v
/usr/bin/sha256sum -- /home/user/src/offmenu/.delivery/stokowski/uif106-credential-file-input-84530467-20261030/workspaces/UIF-106/tools/delivery/stokowski_credential_stage.py
/usr/bin/env -i PATH=/usr/bin:/bin LANG=C.UTF-8 /usr/bin/sudo -n /usr/bin/mkdir -m 0700 -- /run/offmenu-stokowski-credential-stage </dev/null
/usr/bin/env -i PATH=/usr/bin:/bin LANG=C.UTF-8 /usr/bin/sudo -n /usr/bin/install -o root -g root -m 0500 -- /home/user/src/offmenu/.delivery/stokowski/uif106-credential-file-input-84530467-20261030/workspaces/UIF-106/tools/delivery/stokowski_credential_stage.py /run/offmenu-stokowski-credential-stage/receiver.py </dev/null
/usr/bin/env -i PATH=/usr/bin:/bin LANG=C.UTF-8 /usr/bin/sudo -n /usr/bin/sha256sum -- /run/offmenu-stokowski-credential-stage/receiver.py </dev/null
```

Both code hashes must equal `c7b02333707c4791bf4a6ad3c8f4ed677e87aa8941afc60484df3a5eb8ec6c35`; bind code identities as well.
After successful preparation and exact action-time transfer approval, run sender
as ordinary UID1000, with its existing export, without sudo or environment clearing
in the shell. The sender alone captures and then clears its own environment:

```bash
/usr/bin/python3 -I /home/user/src/offmenu/.delivery/stokowski/uif106-credential-file-input-84530467-20261030/workspaces/UIF-106/tools/delivery/stokowski_credential_stage.py send-file </dev/null
```

Require exit0 and fixed `status=source_ready` with nonsecret directory/file
dev:inode identities. Record those identities, owner, modes and fixed paths in a
private operator receipt. Do not print/read/hash the framed source. Reconcile any
failure or uncertain outcome before proceeding. Only then invoke the approved
root receiver with its environment cleared BEFORE sudo, again before Python, and
sudo stdin from `/dev/null`:

```bash
/usr/bin/env -i PATH=/usr/bin:/bin LANG=C.UTF-8 /usr/bin/sudo -n /usr/bin/env -i PATH=/usr/bin:/bin LANG=C.UTF-8 /usr/bin/python3 -I /run/offmenu-stokowski-credential-stage/receiver.py receive-file </dev/null
```

There is no pipe from the sender to sudo. Original `send`/`receive` pipe modes
remain source compatible but are not this approved candidate procedure. Receiver
also clears its own inherited environment. Neither mode starts subprocesses or
emits secrets. Require exit0 and fixed `status=staged` metadata. Verify target
metadata only: fixed path, root ownership, 0600 regular file under root:root0700,
and exact dev/inode identities recorded by the administrator. NEVER read target
contents for verification. Receiver uses exclusive nofollow creation, fsync and
atomic nonoverwriting publication; collisions refuse. No service control follows.

## Lifetime, cleanup and uncertainty

The temporary framed source persists after success until explicit attributable
normal-user cleanup or loss of its tmpfs. The protected target
`/run/offmenu-stokowski-current-credential/linear-api-key` persists until explicit
root cleanup or runtime-storage loss. Helper code remains until explicit cleanup.
There is no timer, renewal, guaranteed crash cleanup or automatic expiry. Later
service-manager copies would have a separate lifetime and need separate approval.

On confirmed outcomes, the normal user cleans up ONLY the exact recorded source
file identity and then its exact recorded empty directory. The administrator
cleans up ONLY the exact recorded root target file and empty target directory,
and the exact recorded helper file and empty helper directory, after the outcome
and any authorized consumer lifetime have been confirmed. Recheck identity,
owner, type and mode using nofollow directory descriptors immediately before each
unlink/rmdir. Never follow a replacement path or use recursive deletion. Do not
clean up by name alone. No cleanup commands are supplied that could blindly
remove preexisting objects. Retain receipts privately without secret bytes.

Ordinary failure cleanup attempts only identities created by that invocation.
Abrupt death, failed fsync/unlink, partial preparation, or replacement can leave
secret remnants. A fixed failure status does not prove absence. Unknown, partial,
replaced, preexisting or unattributable objects require owner/admin reconciliation
and a confirmed outcome before cleanup or another attempt; no blind rerun. If
identities were not durably recorded, hold and reconcile rather than infer them.
Never remove operation journals, change shell configuration, revoke credentials
or delete unrelated data as rollback.

The helper is source-only and confers no transfer authority. No new-unit
`LoadCredential` association, installation, activation, historical worker resume,
Actions, CIX or held work is authorized. Any later association/start requires its
own exact source/runtime/admission packet and explicit approval.
