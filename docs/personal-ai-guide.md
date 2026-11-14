# Set up your personal assistant preferences

Personal AI lets you save an assistant name and instructions for a connected
assistant to read with your permission. Saving these preferences does not send a
question or start a conversation. You use a separate MCP-compatible client for
that interaction.

## Open Personal AI

Sign in to your own OffMenu account, leave demo mode, and choose **Me → Help &
community**. Look for **Personal AI** in the dialog, below the community section.
The form appears after your account's preferences load successfully. A missing
form can mean that sign-in or the preference service is unavailable.

Personal AI is separate from **AI community review**, which is an administrator
panel. For support requests, community posts and notification choices, use the
[support and preferences guide](support-preferences-guide.md).

## Save a name and instructions

1. In **Assistant name**, enter a name of up to 80 characters. A name is required;
   spaces alone are not accepted. Leading and trailing spaces are removed from
   the saved name.
2. In **Private instructions**, enter any preferences you want the connected
   assistant to read, up to 5,000 characters. For example: “Use my saved recipes
   first and ask before changing a meal plan.” You can leave this field empty.
   Use a single paragraph without line breaks: this version rejects line breaks
   and other control characters.
3. Choose **Save personal AI preferences**. Wait for **Saved for your personal
   assistant.** before treating the save as successful.

The save updates preferences for your signed-in account. It is separate from
saving the kitchen to cloud and does not change your inventory, recipes or plan.
When no saved preferences are found, the form starts with both fields empty.
A connected client with permission to read AI preferences can receive these
instructions; the word “Private” does not hide them from that authorised client.
Saving instructions does not establish that a client has read or followed them.

If a connected client separately submits a reviewed AI-attributed recipe for
community review, the saved assistant name is used in that contribution's
attribution. Saving a name alone submits no recipe.

## Keep unsaved edits and account changes straight

Copy any unfinished instructions before reloading the page, reopening Help &
community or changing accounts. Opening the dialog loads preferences again;
unsaved form text is not a saved draft.

If you see **Preferences changed elsewhere. Refresh and review them again.**,
preserve your edits, reload the saved values and compare them before saving
again. Another tab or connected client may have updated the account's
preferences. The failed save does not overwrite that newer version.

Signing out, entering demo mode or switching accounts clears the displayed
personal preferences and ignores delayed responses from the earlier account.
That display reset does not delete saved account preferences. This panel has no
preference-delete button. To remove saved instructions, empty **Private
instructions** and save while keeping a valid **Assistant name**.

## Choose what a connected client can do

In **Me → Connections & developers**, open **Developer API & MCP access**. For a
personal token, select **MCP connector** as **Token destination** and review
**Allow this connection to…** before creating access. Select only the permissions
you intend that client to use; the initially selected kitchen-read permissions
do not include AI preference access.

| Permission shown | Personal AI preference access it enables |
| --- | --- |
| **Ask the private AI to analyse selected kitchen data** | Read the saved assistant name and instructions through the AI-preference tool. This permission alone does not run a model. |
| **Ask the private AI to prepare a confirmed private change** | Save reviewed assistant preferences using the current preference revision and an explicit confirmation. |

Profile, recipes, inventory, plans and provider access have their own
permissions. A preference permission does not grant all of them. Review changes
proposed by your client before confirming a write. Follow the
[developer interface reference](developer-interfaces.md) for connection details;
client setup and model operation depend on the client you choose.

Food-provider connections use the separate **Add my credentials / Manage my
connection** controls in the food-data catalogue. Personal AI's provider tools
can list connection metadata and request a lookup through an implemented
adapter when the client has the appropriate permissions. They do not return
stored provider credentials. A listed connection or saved preference does not
establish that a provider lookup works, and food-provider access does not select
an AI model. Manage a client's grant with **Revoke access** in the connection
list; hiding a displayed token does not revoke it.

## If you cannot continue

| What happens | What to do |
| --- | --- |
| Personal AI is missing | Check that you are signed in to your own account and outside demo mode, then reopen Help & community. A failed preference load can hide the form without a dedicated error message. |
| Invalid personal AI preferences | Check the name, field lengths and single-line instructions before saving again. |
| Preferences changed elsewhere | Preserve your text, reload and review the latest saved preferences before another save. |
| Account changed | Return to the intended account and reopen the dialog before continuing. |
| Storage or preferences unavailable, or a save fails | Preserve your text and check the service with support. A visible form or attempted save is not confirmation that preferences were stored. |
| Your client cannot read or save preferences | Review that connection's AI permissions and current account. Preference settings alone do not connect an external client. |

## Source and maintenance

This guide describes source `59496c6cf006c16b6ac4859580d0e91374682756`, checked
against source only. Live account storage, encryption configuration, external
clients, providers and device/accessibility behavior remain unverified. OffMenu's
documentation owner maintains it when these controls or permissions change.

- [Personal AI form and display reset](../apps/web/src/personal-ai-ui.js).
- [Preference validation, persistence and scoped tools](../apps/web/server/personal-ai.mjs).
- [Help dialog and account wiring](../apps/web/src/app.js).
- [Connection controls](../apps/web/src/access-ui.js) and [MCP routes](../apps/web/server/integrations.mjs).
