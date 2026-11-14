# Use a shared kitchen

This guide describes OffMenu source version
`284f2ce5b369c5b1a5bd57b9f79386e14993e3dc`. It has been checked against browser
and server source, not a running installation. Account sign-in, cloud storage,
sync, device behavior and accessibility have not been verified by this guide.

## Before you share

Open **People sharing this kitchen** in Me. Sign in with your own account;
demo data is separate and cannot create or join a shared kitchen through these
controls. The installation must provide working account and cloud-storage
services. A visible control does not establish that those services are available.

A shared kitchen includes inventory, recipes, selected product details, locations,
plans, shopping lists and cooking batches. It is not a complete account backup.
The source omits personal plan member selections and adjustments from the shared
projection, and filters certain private nutrition metadata. Do not assume every
account field or every sensitive value has been excluded: review the kitchen
information you intend to share before creating it.

## Create a shared kitchen

1. Enter a **Shared kitchen name**.
2. Choose **Create a shared kitchen from this inventory**. The source sends the
   shared projection of the current kitchen to the server and opens the new
   shared kitchen when that succeeds.
3. Check the displayed kitchen name and your role before making changes.

The source keeps a local snapshot when opening a shared kitchen so it can return
to the previous private kitchen. That snapshot is not a verified backup or a
guarantee that pending changes have reached the server.

## Invite someone or join an invitation

Only the owner can create invitations. In the open shared kitchen, choose an
**Invitation role**:

| Role | Intended access in this source |
| --- | --- |
| Editor | Change shared kitchen inventory, plans and shopping. |
| Viewer | Read the shared kitchen. The server rejects state updates from viewers. |

Choose **Create a private invitation code**. The displayed code grants kitchen
access, is single-use and expires after 48 hours. Share it privately with the
intended person. Creating the code sends no email or other message.

To join, sign in, paste the code into **Kitchen invitation code**, and choose
**Join an invited kitchen**. After success, open the kitchen in the list to use
it; joining alone does not switch the current kitchen.

An expired or already-used code cannot be reused. If the server says you have
already joined, check the kitchen list. Ask the owner for another invitation
when the invitation is no longer available and you have not joined.

## Work in the intended kitchen

Select the kitchen's name and role in the list. Confirm the **Open:** status
before editing. Viewers should treat the kitchen as read-only; local edits do
not become shared edits merely because controls appear on the page.

For an editable shared kitchen, the source queues changes locally and attempts
sync while signed in and online. **Saved on this device** or **sync pending**
does not mean another person or device has received the changes. Do not treat
an offline queue as an independently verified backup.

If a conflict message says edits are retained locally, preserve a backup before
choosing how to resolve the conflict. This sharing panel does not provide a
field-by-field conflict resolver. The guide does not establish that any separate
backup or restore workflow has been qualified on your installation.

## Return, leave or remove access

**Return to my private kitchen** switches out of the shared kitchen. It does
not remove your membership. If an editable kitchen has unsynced changes, the
source first attempts sync and can refuse the switch while changes remain
pending. Follow the displayed instruction to stay until sync completes or
preserve a backup before resolving a conflict.

**Leave kitchen** removes a non-owner's own membership. It is different from
returning to the private kitchen: leaving does not wait for pending sync.
Check and preserve any unsynced work before choosing it; the pending-sync guard
on **Return to my private kitchen** does not protect the leave action.
An owner can use **Remove access** for a
non-owner member. The current server does not allow removal of the owner;
ownership transfer is not offered by these controls.

The source checks membership periodically while an active shared kitchen is
visible and online, with backoff after failures. Access removal is not a promise
of immediate detection on every device or deletion of already-held local copies.

## When something is unavailable

| Message or state | Next step |
| --- | --- |
| Sign in to share a kitchen | Sign in with your own account rather than using demo mode. |
| Cloud storage unavailable | The installation's storage service needs attention; creating another kitchen or invitation does not configure it. |
| Kitchen access unavailable | Check that you are using the intended account and ask the owner about membership. |
| Kitchen is read-only | Your viewer membership cannot save shared state. Ask the owner if a different role is intended; this guide grants no role change. |
| Sync pending or newer save exists | Keep local edits and inspect the sync status. Do not assume they have reached the shared kitchen. |
| Conflict retained locally | Preserve a backup and review the conflict before restoring or discarding anything. |

## Source and maintenance

The OffMenu documentation owner maintains this guide when sharing roles,
projection fields, invitations or sync messages change. In-app contextual help,
search-index integration and device/accessibility qualification remain separate.

- [Sharing controls and scope transitions](../apps/web/src/sharing-ui.js).
- [Shared projection and account-state restoration](../apps/web/src/sync-model.js).
- [Sync queue and conflict messages](../apps/web/src/sync-ui.js).
- [Server membership, role and invitation rules](../apps/web/server/kitchens.mjs).
- [People sharing this kitchen panel](../apps/web/assets/index.html).
