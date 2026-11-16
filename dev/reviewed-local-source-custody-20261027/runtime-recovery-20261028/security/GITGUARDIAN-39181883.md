# GitGuardian incident 39181883: narrow static triage

Verdict: **not actionable / false positive**, high confidence, for all four cited occurrences. No credential value is reproduced in this report.

The bot comment was retrieved directly at https://github.com/maldous/offmenu/pull/140#issuecomment-6458068359. Its latest body lists four Generic Password occurrences under the same incident, spanning the two custody commits.

| Commit | Path relative to dev/reviewed-local-source-custody-20261027/ | Line |
|---|---|---:|
| d7d9ed78d63dbaa7170624f849a359f8fe2e374b | corpus-recovery-20261028/access/combined_core.py | 341 |
| d7d9ed78d63dbaa7170624f849a359f8fe2e374b | corpus-recovery-20261028/access/offmenu_corpus_readonly_acl_mount.py | 348 |
| 062210db932a67f9d4f374c12fb577ce61579d07 | corpus-input-access-20261028/incremental_core.py | 401 |
| 062210db932a67f9d4f374c12fb577ce61579d07 | corpus-input-access-20261028/offmenu_input_readonly_acl_mount.py | 409 |

Each exact flagged line assigns the result of standard-library `pwd.getpwnam` for the established restricted operating-system account name. The argument is an account identifier, not a password. The module is explicitly imported as Python `pwd`. Static consumers inspect only UID, GID, account name, home directory and login shell; no `pw_passwd` field is accessed. Generated standalone copies reproduce the same source lookup.

Exact remote files were fetched at the cited immutable commits. Their Git blob hashes match the reviewed local source bytes. No `SECURITY.md` exists in the complete first-commit tree; the second additive custody snapshot introduces none. Installer documentation and source establish the fixed-account validation purpose. The result does not rely on repository privacy to dismiss a real credential exposure.

No rotation, history rewrite, code alteration, suppression or external comment is warranted/performed by this triage. If incident management is separately authorized, the incident can be classified as a false positive with these exact locations and explanation. Keep secret scanning enabled; do not change immutable reviewed installer bytes merely to evade a detector heuristic.

Limits: narrow static inspection only, not an exhaustive secret scan or runtime validation. The GitGuardian dashboard's internal matched substring was not opened; the bot's exact locations and remote source were available and sufficient to establish their non-secret semantics. No credential value was encountered or reproduced at the cited lines.
