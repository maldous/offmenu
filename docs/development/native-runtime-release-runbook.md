# OffMenu native runtime release runbook

This runbook covers the existing OffMenu owner-local package and protected
Windmill replacement path. It does not grant release rights, enable workers,
or change the product release workflow.

1. **Pin the source.** Record the accepted OffMenu head and Git tree. Keep
   source review, a detached verifier shelf or staged build, production package
   acceptance, installed runtime, and normal delivery as separate outcomes.
2. **Bind the package in existing custody.** The actual qualified non-root
   package custodian supplies `owner_current`, `owner_catalog` and
   `publisher_config` as authorized owner-local references with independently
   established SHA-256 pins. Use the exact source-qualified configuration,
   dependency projection and Python/Node custody, preserving applicable
   catalogue authority. The independent reviewer must be distinct from the
   package owner and source author. The custodian binds the actual verdict as
   the typed `PackageAcceptance` and uses the
   [canonical composer](native-harness-package.md). Retain the private package
   in custody. Share only permitted receipt metadata: head, tree, manifest hash
   and hashes for the five role closures. Do not send paths, configuration
   contents or credential material in Git, chat or Linear.
3. **Reconcile the original.** The authorized rollout owner uses the existing
   protected Windmill binding described by the
   [native upgrade ingress](offmenu-native-upgrade-ingress.md). Verify the
   exact original operation and its release, package and protected request
   pins. Keep existing live custody, quiescence, lock and rollback checks.
   A tool login or historical job is not evidence of the current custodian or
   reviewer; use the actual recorded owner/recipient and original receipt.
   If those are unknown, ask for the existing custodian or original reference,
   not the protected inputs. An interrupted or uncertain operation must be
   reconciled against its original, not replaced with a new request.
4. **Read back the installation.** Record the original operation and its
   canonical installed receipt, and verify the active role closures and
   installed source head/tree against the reviewed package. A stopped
   installation is not service health or proof of issue intake, publication
   or refill. Record those outcomes separately from the install.

## UIF-1313 snapshot

[OffMenu #340](https://github.com/maldous/offmenu/pull/340) landed the
owner-local composer at head `ce5b0943f4c8d4e9b110ac1c5f864043e4b486b7`,
tree `42abc1cbf160faf8744b2ee8ca6db0b4f555aeb1`.
[UIF #140](https://github.com/maldous/uif/pull/140) updated the fixed
source pair for that release. These are source results. The protected
source-bound config references and their independently established pins,
the typed production package acceptance and its original Windmill operation,
and exact installed #340 readback have not been verified. An older accepted
source/shelf receipt is not a substitute. Reconcile any newer original with
the actual owner before acting.
