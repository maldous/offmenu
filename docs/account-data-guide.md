# Keep account data, backups and connections separate

This guide describes OffMenu source version
`284f2ce5b369c5b1a5bd57b9f79386e14993e3dc`. It is checked against source, not a
running installation. Account sign-in, cloud services, provider access, downloads,
device behavior and accessibility have not been verified by this guide.

## Choose the copy you mean

Open **Me → Account & backup** for the current account and kitchen backup
controls. Check the displayed account and whether you are using a private or
shared kitchen before saving, exporting or restoring anything.

| Control or copy | What this source describes |
| --- | --- |
| **Export kitchen backup** | Downloads the current kitchen state as `offmenu-pantry.json`. It is ordinary JSON, not the encrypted account package. |
| **Save kitchen to cloud ↑** | Saves the private kitchen to its cloud copy; when a shared kitchen is active, it schedules shared-kitchen sync instead. |
| **Restore cloud copy ↓** | Replaces the private browser copy from its cloud save after the displayed confirmation. Return from a shared kitchen first. |
| **Download encrypted account backup** | A separate control that is unavailable in the accepted application binding described here. Its presence does not establish a usable encrypted backup or restore workflow. |
| **Export unified JSON ↓** | Exports the currently loaded food-data batch, subject to record rights. It is not an account or kitchen backup. |

**Saved on this device** and **sync pending** do not establish that cloud storage
has received the latest changes. Preserve pending work before loading another
copy or clearing local data. Signing in can restore an existing cloud copy when
there are no pending local changes; review the status in the account panel.

## Export and restore a kitchen backup

1. Open **Backups & recipe imports** in the account panel.
2. Choose **Export kitchen backup** and retain the downloaded file privately.
   Kitchen state can include personal profile, recipes and inventory information.
   Reserved credential fields are filtered, but the file is not an encrypted
   account archive or a complete export of every account service.
3. Before restoring another backup, export the kitchen currently open so you
   have a separate copy of its unsaved work.
4. Use **Restore backup** to select a compatible kitchen JSON file. The source
   accepts files up to 20,000,000 bytes and validates their state. A version-one
   inventory-only backup restores inventory; a backup with profile state also
   replaces the corresponding products, recipes, profile and saved selections.
5. If prompted to replace the pantry, review that choice before accepting it.
   This is replacement, not a general merge of the two kitchens.
6. A success message says the backup was restored in this browser. Check the
   kitchen and sync status before treating it as a completed cloud backup.

Account-scoped backup data is validated against the current account; a file
does not grant access to another account. If the account changes during a
restore, retry only from the intended current account. If the source reports
that browser storage could not be fully restored after a failure, keep the
backup and reload before making further changes.

The encrypted-account-backup control is separate. In this source version it
has no selected package supplied by the application, so signing in alone does
not make it available. No encrypted restore procedure is offered by this guide.

## Clear this device's copy

In **Me → Trust, privacy & support**, **Clear this device’s account data** asks
for confirmation before removing the current account namespace from browser
storage and clearing its pending queue. Export pending work first. The source
says cloud data remains available; this action is not account deletion, cloud
erasure, provider revocation or deletion of previously downloaded files.

## Review and retain food-data records

Open **Me → Connections & developers** to expand **Connections, public data &
developer tools** in Shop. The food-data catalogue distinguishes public sources,
your own provider connections and services whose adapters or access are pending.
A catalogue entry or saved credential is not proof that a provider lookup works.

To inspect a batch:

1. Choose a **Source**, then enter a **Food / business search** or a barcode in
   **Explore & enrich your food data.** Keep barcode leading zeroes.
2. Choose **Explore normalized records**. Review source identifiers, quantities,
   nutrition basis, country, date, attribution and licence in **Unified record,
   provenance & licence**. Missing values remain unknown. Public feed results
   can be samples; they do not establish a recall match or food safety.
3. For a local file, select its **Original source** and a **Data file (under
   2 MB per batch)** in **Bring your files, too.** Supported inputs include
   unified JSON, USDA food JSON, Open Food Facts product JSON and mapped CSV.
4. For CSV, map the food/product name and other supplied columns, then confirm
   nutrient basis, units and source context before normalization. A parsed or
   normalized record has not automatically been saved.
5. Select **My source licence or personal provider plan permits this storage /
   export.** only when that statement is true. Choose **Save batch to my
   profile** or **Export unified JSON ↓** for the intended operation.

The checkbox cannot grant rights the source or provider does not allow. Expired,
withdrawn, quarantined or otherwise ineligible records can remain blocked.
Private storage is not permission to publish records or reuse them for another
audience. Sensitive health/history records use their separately consented
workflow, not this generic record importer.

Signed-in saving requests private cloud record storage. Without sign-in, eligible
records are retained in the current browser profile within its size limits. Use
**Load my private records** to inspect that profile's retained records. Loading
the next public collection page replaces the displayed batch; export applies to
the batch in memory, not every page of the source collection.

**Food-name display language** selects supplied source text and fallbacks; it
does not promise a translation of every record. A common-corpus graph preview
is a separate read-only preview: the save and export controls are disabled for
that preview, and its load message says nothing is saved.

## Manage provider credentials and application access

These are different connections:

- **Add my credentials / Manage my connection** configures your own supported
  provider connection. Sign in with the intended profile. Saving credentials
  configures them; a provider search is the separate access check. Do not share
  credentials in help requests or exported examples.
- Removing a provider connection in OffMenu does not invalidate its external
  credential. Revoke the key at the provider too when that is your intent.
- **Developer API & MCP access** grants another application selected access to
  your saved cloud copy. Save the intended local changes to cloud before
  expecting that application to see them. Demo data is not exposed by these
  account controls.

For a personal application token, review **Token destination** and every selected
permission before choosing **Create scoped access token**. Available permissions include writes and public contribution; do not assume
the token is read-only.
Administrative options are separately restricted and cannot be mixed with the
ordinary scopes in this form. A visible option does not grant an administrator
role.

Copy a newly displayed token only to the intended application and treat it as a
password. **Hide token** clears the displayed secret; it does not revoke access.
Use **Revoke access** on the connection to request revocation. The list shows
active, expired or revoked state and the recorded expiry date.

For an OAuth request, check the displayed client, redirect destination and
requested permissions. Sign in to the intended account before allowing it.
Declining closes the request without granting access. A consent screen or a
configured connection does not establish that the client, provider or hosted
integration has been functionally qualified.

## If you cannot continue

| Message or condition | Next step |
| --- | --- |
| Account or profile changed | Return to the intended current account and review the action again. |
| Credential vault or encrypted backup unavailable | The installation lacks a qualified available capability; adding another credential or retrying a download does not configure it. |
| Source policy prevents storage or export | Review the actual source terms and permitted operation; do not treat a checkbox as an override. |
| Import or backup too large | Use a compatible file within the stated limit. Preserve the original separately. |
| Local record storage limit reached | The source offers sign-in for cloud records or export of the current batch; neither establishes new source rights. |
| No cloud copy yet | Preserve the browser copy, then save the intended kitchen when its account service is available. |

## Source and maintenance

The OffMenu documentation owner maintains this guide when account scopes,
backup formats, record rights or connection controls change. In-app contextual
help, complete account portability and device/accessibility qualification remain
separate work.

- [Account navigation, backup and local-clear handlers](../apps/web/src/app.js).
- [Backup state validation and credential filtering](../apps/web/src/pantry-backup.js).
- [Encrypted-backup control and unavailable selection](../apps/web/src/owned-backup-account-ui.js).
- [Food-data import, save, export and provider controls](../apps/web/src/data-ui.js).
- [Record reuse policy](../apps/web/src/record-policy.js).
- [Integration token and OAuth consent controls](../apps/web/src/access-ui.js).
- [Control labels and account/data panels](../apps/web/assets/index.html).
