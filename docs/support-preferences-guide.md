# Ask for help and choose your preferences

This guide describes OffMenu source version
`284f2ce5b369c5b1a5bd57b9f79386e14993e3dc`. It has been checked against source,
not a running installation. Support delivery, staff response, notification email,
optional-provider operation and device/accessibility behavior remain unverified.

## Open help for the right kind of message

Choose **Me → Help & community**. The panel separates **My requests**,
**Community**, **What's new** and **Preferences**. A support request and a public
community post are different actions; choose the intended audience before
entering information. Sign in with your own account to submit a request or save
account preferences. Demo mode does not act as a signed-in account here.

### Send a support request

1. In **My requests → New request**, select **Category**: support, recipe,
   translation or feature.
2. Enter a **Title** and **Message**. Describe the action, what you expected and
   what you observed. Do not include passwords, invitation codes or provider
   credentials. The form accepts a title up to 160 characters and a message up
   to 10,000 characters.
3. Use **Review request** to preview the text and any selected source context.
   Review is not submission and does not establish a saved draft. Preserve your
   own copy of unfinished text before closing or reloading the page.
4. Choose **Send request** and review its confirmation. Only confirmed sending
   requests creation of the account-linked case. A successful creation starts
   with submitted status; it does not mean staff have reviewed or resolved it.
5. Open the entry in **My requests** to read its messages and status. Use
   **Load more cases** when offered. To add information, enter **Reply**, choose
   **Send reply** and review that confirmation.

The server source restricts ordinary case access to the owning account, with a
separate administrator route for staff. Cases are not Community posts. This
source distinction is not a guarantee of live encryption, retention, response
time or deployment availability. Do not rely on the case list as your permanent
copy: case content can expire.

If a request says **This request is still being sent**, wait for its result.
An error does not prove a submission succeeded. Check the existing request list
before creating another copy of the same request. A newer-version message means
the case changed; reopen it and review the current messages before replying.

### Report a recipe or translation issue

**Report a recipe correction** opens Help & community with selected recipe
context, such as its source identifier and version. It does not modify the
recipe, source collection or catalogue. Complete the new request, choose the
appropriate category and review its context before sending.

In **Report a translation error**, enter **Wording to review** and choose
**Review translation report**. This opens a new request with the observed
wording and current interface locale attached as context. It does not send the
report automatically or apply a translation. Add a useful title/message and
review the request before sending. Text or context selected on the page is not
proof of a durable draft.

### Keep public discussion separate

In **Community**, **Start a discussion** asks for a **Public name**, title,
message and discussion/suggestion category. Use **Preview public post** before
**Submit for review**. The confirmation describes public text for review; do
not put private support details into it or assume submission means immediate
publication.

Published topic views can offer **Follow**, **Flag** and a public **Reply** form.
Replies also require review confirmation; a locked topic may not offer the
reply form. **Flag** requests a reason and submits it for moderation. Following
or flagging a topic is not a private support case or a guarantee of staff action.
This guide does not cover staff moderation or administrator controls.

## Choose support notifications

In Help & community, open **Preferences**. Review **Case notifications**,
**Community notifications**, **Update notifications** and **Email updates**,
then choose **Save preferences**. These are account preferences, separate from
the optional-service choices described below.

The source defaults the three notification categories on and Email updates off
when no saved preferences exist. The panel also lists available notifications.
Changing a preference records a choice; it does not establish that an email
was sent, that a provider is configured or that all older notifications were
deleted. If preferences changed elsewhere, reload and review the current values
before saving again.

**What's new** shows available published updates for the selected interface
locale. An empty update list or a **No requests yet** message is not proof that
every service request succeeded; check account and service errors too.

## Choose interface language and scan feedback

Open **Me → Account & backup → Interface language** for the current English or
Arabic interface options. The source stores the device choice and reloads the
page when the language changes. Copy any unfinished support message first.
Recipes and food names retain their source language; the interface selector
does not translate every record or guarantee complete Arabic coverage. Some
interface messages can fall back to English.

In Me, **Large text** changes the application's text presentation.
**Quiet mode · disable scan effects** turns off sound, vibration, screen, light
and speech feedback in the saved feedback settings. Turning Quiet mode off does
not restore those earlier feedback choices automatically; review them in the
scan-feedback controls if you want them again. These settings do not establish
that a particular browser, camera, speech engine or assistive technology works.

## Review optional services independently

In **Me → Account & backup**, find **Services, privacy & support**. Review the
separate **Privacy**, **Analytics**, **Diagnostics**, **Support** and
**Advertising** choices, then select **Save service choices**. Without a saved
choice, the source defaults these optional categories off. A saved choice and a
listed **Available** service are not proof that its provider is functioning.
Configuration and, for advertising, additional vendor-consent conditions still
apply. The external privacy panel can use a different language from the app;
the panel displays that language when known.

In this application binding, **Help & community** opens OffMenu's native help
panel rather than an external support form. You do not need to enable the
optional Support category merely to submit a native case. Document-email and
other optional-service actions have their own consent and availability checks;
a native support case does not authorize them.

Choose **Revoke all optional services** to reset these local service choices.
The source deactivates its optional-service handling and says to reload if a
provider panel remains open. Revocation does not erase information previously
sent, delete an existing support case, revoke an integration token or undo a
separate provider-side choice. It also does not change the account's support
notification preferences. Review choices again if browser storage is unavailable
or you are using another device; this source does not promise account-wide
propagation of optional-service consent.

## When a request cannot continue

| Message or condition | Next step |
| --- | --- |
| Sign in to continue | Check the intended account; demo mode cannot submit as that account. |
| Review the request before sending | Supply a valid category, title and message, then review the preview. |
| Care storage or private-case encryption unavailable | The installation needs service attention. A form preview is not a submitted case. Preserve the message separately. |
| Item changed or newer revision exists | Reopen/reload the current item and review it before a new update. |
| Case content expired | Keep any copy you already retained; the source does not promise indefinite case storage. |
| Service setup required or optional panel remains open | Review the selected service state; reload when instructed. Enabling a choice does not configure the provider. |

## Source and maintenance

The OffMenu documentation owner maintains this guide when request forms,
notifications, language behavior or service choices change. Complete help search,
staff operations, AI administration and device/accessibility qualification remain
separate work.

- [Help forms, previews, reports and preferences](../apps/web/src/care-ui.js).
- [Request/context and preference validation](../apps/web/src/care-model.js).
- [Case access, submission and expiry](../apps/web/server/care-cases.mjs).
- [Notification preferences and updates](../apps/web/server/care-updates.mjs).
- [Optional-service choices and revocation](../apps/web/src/services-ui.js).
- [Service defaults and activation conditions](../apps/web/src/services-model.js).
- [Language changes and English fallback](../apps/web/src/i18n.js).
- [Quiet and large-text preferences](../apps/web/src/journey-ui.js).
- [Native support wiring and selected report context](../apps/web/src/app.js).
- [Navigation and visible labels](../apps/web/assets/index.html).
