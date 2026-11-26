# OffMenu native runtime release runbook

This runbook covers the existing OffMenu owner-local package and protected
Windmill replacement path. It does not grant release rights, enable workers,
or change the product release workflow.

1. **Pin the source.** Record the accepted OffMenu head and Git tree. Keep
   source review, a detached verifier shelf or staged build, production package
   acceptance, installed runtime, and normal delivery as separate outcomes.
2. **Bind the package in existing custody.** Preserve the qualified runtime
   owner and publisher configuration as separate authorities. Use the exact
   source-qualified configuration, dependency projection and Python/Node
   custody, preserving applicable catalogue authority. The independent
   reviewer must be distinct from both the package owner and source author.
   Bind that actual verdict as the typed `PackageAcceptance` for the exact
   head and tree.
   - Where one qualified non-root custodian already has all three authorized
     owner-local references, the existing
     `native_harness_package.prepare_owner_local_package` remains supported.
   - Where custody is split, the existing runtime owner (UID 1000) supplies
     the source/dependency snapshot, `owner_current` and `owner_catalog`.
     The existing publisher principal (UID 984) supplies only the authorized
     `publisher_config` snapshot. In its verified protected release context,
     a trusted root caller may use
     `native_harness_package.prepare_split_role_package` to join these
     separately authenticated byte snapshots into the same canonical v1
     package for the original operation. Do not treat UID 0, a typed object,
     or a caller-supplied hash as proof of either role or of the review.
     The helper is in-process, not a new Windmill action, and cannot discover
     or read a role's private configuration on its behalf.
   Both paths use the [canonical composer](native-harness-package.md) and
   require independently established config pins. Retain the private package
   in custody. Share only permitted receipt metadata: head, tree, manifest hash
   and hashes for the five role closures. Do not send paths, configuration
   contents or credential material in Git, chat or Linear.
3. **Reconcile the original.** The authorized rollout owner uses the existing
   protected Windmill binding in the current `foo` workspace, as described by
   the [native upgrade ingress](offmenu-native-upgrade-ingress.md). The historical
   `offmenu` workspace is not required. Generic Windmill/root shell access is
   transport, not the producer, reviewer or a package receipt. Verify the
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

Use one accountable release handoff from **producer wired** through **package
accepted**, **original reconciled**, and **installed (revision verified)**.
Report **source accepted** separately. If the producer binding or its inputs
are not evidenced, report **pre-install blocked** with the exact missing item,
not **waiting for transport approval** or **not installed** by inference.

To verify the existing builder without production inputs, run this synthetic
fixtures from a checked-out revision containing #344, as a non-root user:

```sh
PYTHONPATH=tools/delivery python3 -B -m unittest discover -s tests/delivery \
  -p test_native_harness_package.py
```

The fixtures compare both preparation routes against a disposable canonical
five-role package. They do not verify production wiring, acceptance or
installation.

## UIF-1313 snapshot

[OffMenu #340](https://github.com/maldous/offmenu/pull/340) introduced
the owner-local composer. [OffMenu #343](https://github.com/maldous/offmenu/pull/343)
extended the upgrade to preserve saved runtime state across its policy and
configuration transition. [OffMenu #344](https://github.com/maldous/offmenu/pull/344)
added the split-custody helper at head
`f40db673ac8d1c39d6b32146198210a09b6ef309`, tree
`1880f68de14946f5dd66fe231ae943e2abb77598`.
[UIF #145](https://github.com/maldous/uif/pull/145) repinned the protected
release source to that exact OffMenu pair; repinning does not deploy it.

Independent detached source tests passed. An existing Foo read-only transition
check for #344 preserved 6 bindings and 75 task records in its projected state;
it did not replace files or start a service. These results are not a production
package receipt. The protected caller's binding of both role snapshots, the
typed production package acceptance and its original installation operation,
and the exact installed #344 readback remain unverified. Historical route,
shelf and package evidence are not substitutes; reconcile a newer original
with the actual owner before acting.
