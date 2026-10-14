# Native care client

`setupCare({root,getUser,authFetch})` renders the care interface inside the
provided root. `refresh()` reads public topics and locale-matched updates, then
loads owner data only for the account captured at the start of the refresh.
`reset()` advances that account epoch and removes rendered private text.
`report(context)` sanitises selected report context and opens the request view.

All user-supplied text is rendered with `textContent` and `dir=auto`. Reviewed
mutations use a fresh idempotency key; a 409 asks the person to reload and
review the current revision and never retries with a new revision. Owner case
detail contains its initial message and public staff thread. The staff UI is
shown only after `/api/admin/session` confirms administrator authority.

The client uses native case, community, update, preference, notification, and
moderation routes. It has no embedded vendor board, iframe, external popup, or
email delivery path. `emailUpdates` is only the server-backed preference.

Case inboxes use the opaque server cursor returned with each page. The
localized **Load more cases** control appends the next owner or staff page only
while the same signed-in account and render epoch remain current. Account reset
clears both cursors and removes the controls with the private interface.

Staff list records do not expose a case body or action controls. A staff member
must explicitly open a case through the staff-only detail route before viewing
its selected context, visible thread, and staff internal notes or taking a case
action. The same account/epoch guard drops delayed staff detail responses after
logout, account change, or reset.

A staff member records bounded proposal source, digest, and reference before
moving a case to `proposed` or `reviewed`. A release requires its own bounded
release reference and only records the case disposition; the interface states
explicitly that it does not publish a catalogue change. Existing staff-detail
proposal and release values are prefilled for review. Each status change needs
an explicit confirmation and is still protected by the case revision and the
account epoch.
