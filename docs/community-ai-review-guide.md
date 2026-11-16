# Review the community AI settings

Use **AI community review** to configure an optional moderation aid and request a
small review batch. It handles pending public recipes, recipe comments, topics
and replies. Its decisions support moderation; they do not certify recipe rights,
nutrition, allergens or safety.

## Open the administrator panel

Sign in with an administrator account, leave demo mode, and choose **Me → Help &
community**. Look for **AI community review** below the member-facing sections.
Both its settings and decision list must load before the panel appears. A missing
panel can mean that permission or a service request failed; there is no dedicated
load-error message inside a hidden panel.

Personal assistant preferences and ordinary support requests are separate. See
the [support guide](support-preferences-guide.md) for member requests and the
[technical community AI reference](community-ai.md) for deployment and integration
requirements.

## Review and save settings

When no settings have been saved, the defaults are:

| Control | Default and meaning |
| --- | --- |
| **Enable AI review** | Off. Runs return `disabled` until enabled settings are saved. |
| **Allow reversible automatic quarantine** | Off. Enabling review alone does not permit an automatic moderation action. |
| **Provider** | `mcp`. Queue items for an authorised administrator's external MCP agent. This mode does not run a model in OffMenu. |
| **Daily review limit** | 3. Choose a whole number from 1 to 20. |
| **Automatic-action threshold** | 0.98. Choose a value from 0.90 to 1.00. |

For **Provider → mcp**, leave **Endpoint** and **Model** unused. Saving this mode
clears their stored values, even though the fields remain visible. Completing
queued reviews needs the separate authorised administrator integration; pressing
**Run review** does not complete an agent's work.

Choose **self-hosted** only with the review endpoint qualified by your deployment
owner. Enter its approved HTTPS URL in **Endpoint**. Typing a URL does not qualify
or configure the service. **Model** supplies the name recorded for self-hosted
decisions; changing that field does not install or select a model at the endpoint.
This panel has no provider-key entry or connection-test control.

The daily limit counts reserved reviews, including failed provider attempts and
items queued for an MCP agent, by UTC day. Each run processes at most three items,
even if the daily limit is higher. The panel does not show a remaining-budget
meter.

Choose **Save reviewed AI settings**, review **Save these reviewed AI settings?**,
and confirm only the intended settings. The panel reloads after a successful
save. Check the reloaded values; saving settings and running a review are
separate actions.

If you see **Settings changed elsewhere. Reload and review again.**, preserve
any unsaved choices, reopen the panel and compare the latest saved settings
before another save. A failed conflicting save does not overwrite the newer
settings. Reopening Help & community or switching accounts also discards the
current unsaved form.

## Understand automatic quarantine

Automatic action requires all of these conditions: saved review enabled, saved
automatic quarantine enabled, a valid self-hosted decision of `reject`, and
confidence at or above the saved threshold. Its automatic action can hide a
public topic or reply reversibly. It does not automatically approve content.
Recipes and recipe comments remain for separate moderator review, including when
the model recommends rejection above the threshold.

A model's confidence is not proof that its recommendation is correct. Review the
underlying contribution and moderation record when deciding what should remain
published. Turning automatic quarantine off does not undo previous moderation.

## Run a small batch

1. Save and check the intended settings first. **Run review** uses saved settings,
   not unsaved fields currently on screen.
2. Choose **Run review** and review **Run the configured community review now?**.
3. Confirm the request, then inspect the refreshed decision list.

The run response can describe processed items or a no-run reason, but the panel
immediately refreshes and replaces its temporary notice. There is no durable run
summary or automatic “continue all” control here. Reopen Help & community to
reload settings and decisions if needed.

A run processing zero items does not establish that every pending contribution
has been reviewed. There may be no eligible item, an existing claim or decision,
or no available daily budget. A new run is a new explicit request, not a way to
undo a previous result or force an uncertain item through again.

## Read the decision list

The panel shows up to the latest 100 recorded decisions. Each entry contains its
contribution kind, decision, state and reason. It does not display the full
submission, a confidence score, model details or moderation action buttons.

| State | What to understand before continuing |
| --- | --- |
| `awaiting_agent` | Queued for the authorised MCP administrator workflow. No model or moderation completion is implied. |
| `held` | Needs separate moderator attention. An AI `approve` recommendation can still be held; it does not publish the item. An uncertain interrupted operation can also become held. |
| `applied` | A moderation operation was recorded as applied. Check the underlying contribution and moderation record for what actually changed. |
| `failed` | No valid provider decision was obtained. It is not an approval or proof that another run should resend the same item. |
| `claimed` or `applying` | Work is reserved or its outcome is being recorded. Do not treat it as complete or manually bypass that state. |

`finalization_failed` can appear in a run response when recording the final state
fails. The saved list may still show `applying`. The system can later retain an
expired ambiguous operation as `held` with an uncertain reason; it does not
attribute a person's later moderation change to the AI. Use the existing
moderation record to establish what happened rather than repeatedly running the
same request.

## If review cannot continue

| Message or condition | Next step |
| --- | --- |
| Sign-in or administrator permission required | Check the intended administrator account, then reopen Help & community. Ordinary member access is insufficient. |
| `disabled` | Check whether enabling review is intended, then save the reviewed setting before requesting a run. |
| Invalid or unqualified AI settings, or `endpoint-unqualified` | Review field limits and the deployment owner's qualified endpoint. Changing a displayed URL does not grant backend access. |
| `storage-unavailable`, `settings-invalid`, or settings/decisions unavailable | Ask the deployment owner to check the service. A visible form does not establish that storage and the configured endpoint work. |
| Conflict or uncertain result | Reload current settings and decisions, preserve the existing moderation history, and resolve the specific item through the authorised moderator workflow. |

## Source and maintenance

This guide describes source `59496c6cf006c16b6ac4859580d0e91374682756`, checked
against source only. Administrator access, model/endpoint operation, moderation
results and browser/device behavior have not been verified on a live installation.
OffMenu's documentation owner maintains it when controls or review rules change.

- [Panel controls, confirmations and refreshed list](../apps/web/src/community-ai-ui.js).
- [Settings, limits, decisions and moderation rules](../apps/web/server/community-ai.mjs).
- [Help entry and account wiring](../apps/web/src/app.js).
- [Technical integration and recovery details](community-ai.md).
