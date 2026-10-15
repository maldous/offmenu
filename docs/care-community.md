# Care community

The community API is a separate text-only public domain. New topics and replies are pending until a trusted Identity administrator publishes them. Public endpoints never return pending or hidden material, except that an authenticated author may read their own pending topic and pending replies.

Administrators can moderate existing community rows, restrict a person already observed as a community author, and read sealed flag messages. The API does not query profile, kitchen, private-document, provider, or credential tables. Moderation actions use revision CAS, a nonce guard, and a value-free audit record.

An author with an active restriction can submit one or more sealed appeals. Administrators can read and resolve those appeals, then lift the restriction through the separate, audited restriction action.

Flags and appeals retain their encrypted text for 30 days. Their queue projection refuses to decrypt expired payloads even before scheduled cleanup erases the ciphertext and reporter/owner identifier. Expired restrictions are removed by the same community-only cleanup routine.

Cleanup replaces an expired report's idempotency mapping with an HMAC-only tombstone before erasure. Retrying that key returns an expiry result and cannot recreate the private payload; the tombstone contains no account identifier, key, or report text.

Posting requires a same-origin authenticated request, an explicit public confirmation, an idempotency key, and both account and global monthly community budgets. Text is stored and returned as text only; clients must render it as text, never HTML.

Private flags and restriction appeals share separate atomic limits of ten accepted reports per account and one hundred globally per calendar month. One open flag per reporter/topic and one open appeal per account are allowed. Moderation audit entries retain a bounded rationale, never a report or profile payload.

`listCommunityCandidates` and `moderateCommunityCandidate` are server-only worker helpers for an independently authorised management worker. Candidate output contains only pending submitted text, type, identifier, and revision; moderation retains the same CAS and audit rules as the administrator route.
