# Administrative client

`setupAdministration` asks the same-origin server for `/api/admin/session` before rendering anything. Browser metadata is never treated as authority. It operates only global service and application settings, configured-status credential metadata and audit paths; it has no user, private-record, profile, credential-export or role-elevation controls.

Credential fields are blank password inputs. Only an explicit replace or disable choice is submitted; values are cleared after every save outcome. The review step lists changed paths and credential names, never secret values. A 409 requires refresh and a new review.
