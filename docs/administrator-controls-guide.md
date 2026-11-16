# Use the application administrator controls

The **Administration** and **Public source operations** panels manage shared
application settings and existing public source policies. Their changes can
affect other people using the installation. Check the intended installation and
account before making a change.

## Open the panels

Sign in with an administrator account, leave demo mode, then choose **Me →
Account & backup**. Look for **Administration** and **Public source operations**
in the account dialog. Opening the dialog asks the server to check your current
administrator access before loading either panel.

An ordinary account or shared-kitchen owner role does not grant this access.
These panels cannot create administrator roles. If a panel is missing, check the
account with the installation owner: a denied session or failed settings/source
load can hide the panel without a dedicated load-error message.

## Review application settings

In **Administration**, inspect the existing values before editing:

| Group or controls | What to review |
| --- | --- |
| **Service settings** | The structured JSON service configuration. Use the installation owner's reviewed settings and preserve valid JSON; the server rejects unknown or unsupported settings. This is not a field for service credentials. |
| **Default country**, **Default units**, **Default servings**, **Default interface language** | Application defaults. Country may be empty or a supported uppercase country code; units are `metric` or `imperial`; servings must be 0.1–100; interface language is `en` or `ar`. These are separate from a person's saved profile. |
| **Support retention days** | A whole number from 1 to 365. Review the intended retention policy before changing it. |
| **Diagnostics hourly limit**, **Support hourly limit**, **Document hourly limit** | Whole numbers from 1 to 100. These are service limits, not a display of usage remaining. |
| **Support email**, **Document email** | Application-wide feature choices. Enabling one does not configure a sender, deliver an email or grant a person's optional-service consent. |

Use the [administrative settings reference](admin-settings.md) for the service
contract and deployment requirements. Saving a valid service configuration does
not establish that the external service is operational.

## Keep or change a configured credential

Credential sections show a name, **configured** or **not configured**, and the
configuration source. Their password fields start blank; the existing secret
value is not displayed.

| Choice | Effect of a confirmed save |
| --- | --- |
| **Keep existing value** | Leave that credential unchanged. A blank password field with this choice does not erase the saved value. |
| **Replace value** | Enable **New value** and submit the replacement you enter. An empty replacement is rejected. |
| **Disable value** | Save a disabled override for that credential, including suppression of a fallback environment value. |

**Keep existing value** also keeps a previously disabled override; it does not
restore an older value. Review the intended replacement or disable operation
with the service owner. The configuration badge is metadata, not a credential
validation or connection test.

Once a save request succeeds or fails, replacement password fields are cleared.
If you cancel the confirmation, no request is sent and the form can retain its
unsaved entries. Reopening the account dialog reloads the form; switching
accounts clears its displayed state. Neither action deletes saved settings.

## Review and confirm a save

1. Choose **Review changes**. Check the listed setting paths and credential
   names. The preview describes which items will change; it does not reveal
   replacement secret values or test the services.
2. Choose **Save confirmed settings**. The form checks the current entries and
   lists their changes again. If it says **No changes to save.**, no update is
   submitted.
3. Review **Save these reviewed administrative settings?** and confirm only the
   intended change.
4. After a successful request, the panel reloads. Check the saved values,
   credential badges and audit entries rather than relying on a form click as
   proof of success.

If you see **Settings changed elsewhere. Refresh and review again.**, use
**Reload settings**. Preserve any non-secret draft changes separately, then
compare the latest settings and review a new update. The failed conflicting
save does not overwrite the newer version. Reloading discards unsaved form
entries.

The audit list shows the actor, resulting revision, changed paths and time. It
records settings changes, not email delivery, provider availability or a
successful deployment. See the [client reference](admin-client.md) for its
metadata and credential-handling boundaries.

## Suspend or reactivate an existing public source

In **Public source operations**, each listed source shows its identifier,
licence, revision and **active** or **suspended** state. The list contains only
policies accepted by this administration surface's public-policy checks. An
unlisted source is not evidence that its data or policy is absent everywhere.

1. Identify the source and read its displayed state and licence.
2. Choose **Suspend source** or **Reactivate source** for the intended change.
3. Review **Suspend this reviewed public source?** or **Reactivate this reviewed
   public source?** before confirming.
4. Check the refreshed state, revision and audit entry after the request.

This operation changes only the existing policy's active state. It cannot edit
the policy document, licence, audiences, permitted actions or source identifier,
add a new source, publish a person's records or grant administrator access.
Reactivation does not extend an expired policy or create new rights.
Suspension is not deletion or recall of copies already obtained.

If you see **Source changed elsewhere. Reload and review it again.**, choose
**Reload source policies**, inspect the current state and decide again. The
panel has no bulk operation or policy-document editor. The source audit shows
source identifier, action, revision and time; the
[public source administration reference](admin-operations.md) explains the
underlying contract.

## If a change cannot continue

| Message or condition | Next step |
| --- | --- |
| Sign-in or administrator permission required | Check the intended account with the installation owner. A visible browser control cannot grant a role. |
| Invalid administrative settings | Check JSON syntax, supported fields and the numeric/default choices. A preview lists changes but does not replace server validation. |
| Credential vault or administrative storage unavailable | Preserve non-secret draft notes and ask the service owner to check the installation. Repeatedly entering a replacement cannot configure the missing backend. |
| Source is not an administrable public policy | Use the existing source owner's policy-review process. Changing browser fields cannot bypass it. |
| An update fails or its result is uncertain | Reload the current revision and audit before deciding on another change. Keep an uncertain result distinct from a confirmed save. |

## Source and maintenance

This guide describes source `59496c6cf006c16b6ac4859580d0e91374682756`, checked
against source only. Live administrator access, storage, encryption configuration,
service effects and browser/device behavior remain unverified. OffMenu's
documentation owner maintains it when these controls or permissions change.

- [Administration form](../apps/web/src/admin-ui.js) and [change preview](../apps/web/src/admin-model.js).
- [Public source controls](../apps/web/src/admin-operations-ui.js).
- [Settings and access checks](../apps/web/server/admin-settings.mjs), [global limits](../apps/web/server/global-settings.mjs) and [source operations](../apps/web/server/admin-operations.mjs).
