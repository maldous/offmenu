# Administrative client

`setupAdministration` asks the same-origin server for `/api/admin/session` before rendering anything. Browser metadata is never treated as authority. It operates only global service and application settings, configured-status credential metadata and audit paths; it has no user, private-record, profile, credential-export or role-elevation controls.

Credential fields start as blank password inputs. Only an explicit replace or disable choice is submitted. The review step lists changed paths and credential names, never secret values. A 409 requires refresh and a new review.

After a submitted save succeeds or fails, credential inputs are cleared. Cancelling the confirmation sends no request, but leaves any typed replacement in the current form. Choose `Keep existing value` to clear that replacement without sending it.
